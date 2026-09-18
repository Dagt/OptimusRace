from .account_names import name_parts,save_name
import json, hashlib, secrets
from datetime import timedelta
from functools import wraps
from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse,HttpResponseForbidden,HttpResponse
from django.contrib import messages
from django.contrib.auth import login,logout,authenticate
from django.contrib.auth.views import PasswordResetView
from smtplib import SMTPException
import logging
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction,IntegrityError
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Sum,Q
from decimal import Decimal, InvalidOperation
import stripe
from .models import *
from .forms import SignupForm,EventForm,PhotoForm
from .services import *
from .event_policy import blank_rules,validate_policies,registration_open,quote_price
from .policy_forms import PolicyForm
from .forms import BirthDateField,ParticipantPhotoForm
from .photos import save_photo
from .availability import availability,set_capacity
from .capacity_results import capacity_boards,all_ties
from .relative_scoring import is_relative,tie_groups,resolve_tie
from .progress import comparison_key,comparison_label

def next_url(request):
    target=request.POST.get('next',request.GET.get('next','/'))
    return target if url_has_allowed_host_and_scheme(target,{request.get_host()},require_https=request.is_secure()) else '/'

class RecoveryView(PasswordResetView):
    template_name='registration/password_reset_form.html'

    def form_valid(self,form):
        # Independent key from login attempts; generic response for every account.
        key=hashlib.sha256(('reset:'+form.cleaned_data['email'].strip().lower()).encode()).hexdigest()
        with transaction.atomic():
            attempt,_=LoginAttempt.objects.get_or_create(key=key,defaults={'until':timezone.now()+timedelta(minutes=15)})
            if attempt.until<timezone.now(): attempt.count=0;attempt.until=timezone.now()+timedelta(minutes=15)
            attempt.count+=1;attempt.save()
        if attempt.count>3:return redirect('password_reset_done')
        try:return super().form_valid(form)
        except (SMTPException,OSError):
            logging.getLogger(__name__).error('Password recovery delivery failed; check mail service configuration.')
            return redirect('password_reset_done')

def denied(request):
    return render(request,'error.html',{'code':'403','title':'Este espacio es para tu equipo.','detail':'Ingresa con una cuenta que tenga permisos para esta sección.'},status=403)

def coach_only(view):
    @wraps(view)
    @login_required
    def wrapped(request,*args,**kwargs):
        if request.user.is_superuser or not request.user.groups.filter(name='Coach').exists(): return denied(request)
        return view(request,*args,**kwargs)
    return wrapped

def administrator(view):
    @wraps(view)
    @login_required
    def wrapped(request,*args,**kwargs):
        if not request.user.is_superuser: return denied(request)
        return view(request,*args,**kwargs)
    return wrapped

def error(request,exc):
    messages.error(request,' '.join(exc.messages) if isinstance(exc,ValidationError) else 'Revisa los datos e inténtalo de nuevo.')

def home(request):
    events=list((Event.objects.all() if request.user.is_superuser else Event.objects.exclude(status='draft')).order_by('-date'))
    if not request.user.is_authenticated:
        competitive=[e for e in events if e.status in ['live','closed']]
        selected=next((e for e in competitive if str(e.pk)==request.GET.get('event')),competitive[0] if competitive else None)
        leaders=[row for row in board(selected) if row.get('rank')==1 and row.get('completed') and row.get('participant_id')] if selected else []
        from .participant_views import search_people
        for event in events:event.seats=availability(event)
        return render(request,'public_home.html',{'events':events,'competitive_events':competitive,'selected_event':selected,'leaders':leaders[:12],'people':search_people('',True).order_by('-pk')[:8],'upcoming':next(iter(sorted([e for e in events if e.status=='open' and e.date>timezone.now()],key=lambda e:e.date)),None),'server_now':timezone.now().isoformat()})
    own={r.event_id:r for r in Registration.objects.filter(user=request.user)} if request.user.is_authenticated else {}
    for e in events:
        e.seats=availability(e);e.taken=e.seats['occupied'];e.remaining=e.seats['remaining']
        e.fill=round(e.taken/e.capacity*100) if e.capacity else 0;e.entry=own.get(e.id)
    summary={'events':len(events),'athletes':Registration.objects.filter(state='confirmed').count(),'present':Registration.objects.filter(attendance='present',event__status='live').count(),'income':Registration.objects.filter(state='confirmed').aggregate(total=Sum('amount'))['total'] or 0}
    return render(request,'home.html',{'events':events,'summary':summary,'own_count':len(own),'upcoming':next(iter(sorted([e for e in events if e.status=='open' and e.date>timezone.now()],key=lambda e:e.date)),None),'server_now':timezone.now().isoformat()})

def signin(request):
    if request.method=='POST':
        email=request.POST.get('email','').lower().strip()
        key=hashlib.sha256(email.encode()).hexdigest()
        with transaction.atomic():
            attempt,_=LoginAttempt.objects.get_or_create(key=key,defaults={'until':timezone.now()+timedelta(minutes=15)})
            if attempt.until<timezone.now(): attempt.count=0; attempt.until=timezone.now()+timedelta(minutes=15)
            attempt.count+=1; attempt.save()
        if attempt.count>10: messages.error(request,'Demasiados intentos. Espera 15 minutos.')
        else:
            # createsuperuser/admin may store a username different from the email.
            # Reject ambiguous identities rather than choosing somebody's account.
            candidates=list(User.objects.filter(Q(username__iexact=email)|Q(email__iexact=email))[:2])
            user=authenticate(request,username=candidates[0].username,password=request.POST.get('password')) if len(candidates)==1 else None
            if user and (user.is_superuser or user.groups.filter(name='Coach').exists()):
                LoginAttempt.objects.filter(key=key).delete(); login(request,user); return redirect(next_url(request))
            messages.error(request,'Correo o contraseña incorrectos.')
    return render(request,'login.html',{'next':next_url(request),'email':request.POST.get('email','')})

def signup(request):
    form=SignupForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                d=form.cleaned_data
                user=User.objects.create_user(username=d['email'],email=d['email'],first_name=d['name'],password=d['password'])
                save_name(user,d)
                Profile.objects.create(user=user,sex=d['sex'],birth_date=d.get('birth_date'))
            login(request,user); messages.success(request,'Tu cuenta está lista. Bienvenido a Optimus Race.');return redirect(next_url(request))
        except IntegrityError: form.add_error('email','La cuenta ya existe.')
    return render(request,'signup.html',{'form':form,'next':next_url(request)})

@require_POST
def signout(request):
    logout(request); return redirect('home')

def event_detail(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if e.status=='draft' and not request.user.is_superuser: return HttpResponseForbidden()
    entry=Registration.objects.filter(event=e,user=request.user).first() if request.user.is_authenticated else None
    seats=availability(e);occupied=seats['occupied']
    return render(request,'event.html',{'event':e,'seats':seats,'server_now':timezone.now().isoformat(),'entry':entry,'board':board(e),'capacity_boards':capacity_boards(board(e)),'relative_scoring':is_relative(e),'occupied':occupied,'remaining':max(0,e.capacity-occupied),'can_enroll':registration_open(e),'online_enrollment':False,'stripe_ready':bool(settings.STRIPE_SECRET_KEY),'payment_mode':settings.STRIPE_MODE})

@login_required
@require_POST
def enroll(request,pk):
    try: return redirect(checkout(pk,request.user,request.POST.get('discount_code','')))
    except (ValidationError,stripe.StripeError) as exc:
        error(request,exc if isinstance(exc,ValidationError) else ValidationError('Stripe no respondió. Tu reserva se conserva; puedes reintentar sin duplicar el pago.'))
        return redirect('event',pk=pk)

@csrf_exempt
@require_POST
def webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET: return HttpResponse(status=503)
    try:
        payload=stripe.Webhook.construct_event(request.body,request.headers.get('Stripe-Signature',''),settings.STRIPE_WEBHOOK_SECRET)
        fulfill(payload)
    except (ValueError,KeyError,ValidationError,stripe.SignatureVerificationError): return HttpResponse(status=400)
    except Payment.DoesNotExist: return HttpResponse(status=409)
    return JsonResponse({'received':True})

@administrator
def event_edit(request,pk=None):
    e=get_object_or_404(Event,pk=pk) if pk else None
    form=EventForm(request.POST or None,instance=e)
    rules=e.rules if e else blank_rules()
    if not e or (e.status=='draft' and not e.registration_set.exists()):rules={**rules,'category_bounds':'upper_inclusive','capacity_podiums':False}
    policy=PolicyForm(request.POST or None,rules=rules)
    if request.method=='POST':
        try:rules=json.loads(request.POST.get('rules','{}'))
        except ValueError:pass
    if request.method=='POST' and form.is_valid() and policy.is_valid():
        try:
            rules=json.loads(request.POST['rules'])
            policy.apply(rules)
            if not e or (e.status=='draft' and not e.registration_set.exists()):rules['category_bounds']='upper_inclusive';rules['capacity_podiums']=False
            validate_policies(rules,form.instance)
            validate_rules(rules,False)
            if e: e=configure(e.id,request.user,{**form.cleaned_data,'rules':rules})
            else:
                e=form.save(commit=False); e.rules=rules; e.save(); audit(e,request.user,'created',{'rules':rules})
            if request.POST.get('intent')=='publish':
                try:change_phase(e.id,request.user,'open')
                except ValidationError as exc:
                    messages.warning(request,'El borrador se guardó, pero falta completar lo siguiente para publicar:')
                    error(request,exc)
                    return redirect('configure',pk=e.id)
                messages.success(request,'Evento publicado. Ya aparece en la lista de eventos para participantes.')
            else:messages.success(request,'Borrador guardado. Puedes seguir editándolo o publicarlo cuando esté listo.')
            return redirect('operations',pk=e.id)
        except (ValidationError,ValueError,KeyError) as exc: error(request,exc)
    return render(request,'configure.html',{'form':form,'policy_form':policy,'event':e,'rules':rules,'locked':bool(e and (e.status!='draft' or e.registration_set.exists())),'catalog':list(Exercise.objects.values('name','unit','capacity','higher','base','elite','parameters'))})

def default_rules():
    names=['Sentadilla','Press banca','1000 m','Burpees 5 min','50 m','Shuttle 10x10','Salto horizontal','Salto vertical']
    catalog={x['name']:x for x in Exercise.objects.values('name','unit','capacity','higher','base','elite')}
    preferred=[catalog[n] for n in names if n in catalog]
    remaining=[t for name,t in catalog.items() if name not in names]
    tests=[]
    for capacity in ['Fuerza','Resistencia','Velocidad','Potencia']:
        tests.extend([t for t in preferred+remaining if t['capacity']==capacity][:2])
    return {'tests':tests,'categories':[{'name':'Hombres · abierta','sex':'M','min':0,'max':None},{'name':'Mujeres · abierta','sex':'F','min':0,'max':None}],'bar':0,'rounding':0,'round_mode':'none'}

@administrator
def operations(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if request.method=='POST':
        try:
            action=request.POST['action']
            if action=='phase':
                selected_test=int(request.POST.get('test',0))
                change_phase(pk,request.user,request.POST['phase'],selected_test,1,expected_test=int(request.POST['expected_test']) if request.POST.get('expected_test') is not None else None)
                if request.POST['phase']=='live':
                    prefix='Competencia iniciada.' if e.status=='open' else 'La estación ya estaba activa.' if selected_test==e.active_test else 'Estación activada.'
                    messages.success(request,'La estación ya está activa. Las marcas se conservan.' if e.status=='live' and selected_test==e.active_test else f'{prefix} Los coaches pueden capturar: {e.rules["tests"][selected_test]["name"]}. Si tenían la captura abierta, deben actualizarla.')
                elif request.POST['phase']=='closed':messages.success(request,'Evento finalizado. Los resultados quedaron fijados y la captura está cerrada.')
                else:messages.success(request,'Evento publicado. Cuando estén listos los coaches, inicia la competencia desde Resumen.')
            elif action in ['close_station','reopen_station']:
                close_station(pk,request.user,int(request.POST['test']),reopen=action=='reopen_station')
            elif action=='cash':
                raise ValidationError('Usa Inscribir en mostrador para registrar participante, foto, peso y efectivo juntos.')
            elif action=='reception':
                r=get_object_or_404(Registration,pk=request.POST['registration'],event=e)
                check_in(r.id,request.user,request.POST['weight'],r.batch,request.POST['attendance'],request.POST.get('reason',''),int(request.POST['revision']))
            elif action=='correct':
                return denied(request)
            elif action=='tiebreak':
                ids=[int(value) for value in request.POST.getlist('member')]
                places=[int(value) for value in request.POST.getlist('place')]
                if len(ids)!=len(places) or set(places)!=set(range(1,len(ids)+1)):raise ValidationError('Asigna una posición distinta a cada participante empatado.')
                order=[member for place,member in sorted(zip(places,ids))]
                resolve_tie(pk,request.user,request.POST['category'],float(request.POST['total']),order,request.POST['fingerprint'],request.POST.get('challenge',''),request.POST.get('details',''),request.POST.get('judge',''),scope=request.POST.get('scope','general'))
            elif action=='capacity':
                set_capacity(pk,request.user,int(request.POST['capacity']),request.POST.get('reason',''))
            elif action=='discipline':
                r=get_object_or_404(Registration,pk=request.POST['registration'],event=e)
                discipline(r.pk,request.user,request.POST.get('disqualified')=='1',request.POST.get('reason',''),int(request.POST['revision']))
            elif action=='onsite':
                with transaction.atomic():
                    e=Event.objects.select_for_update().get(pk=pk)
                    if e.status=='closed': raise ValidationError('El evento está cerrado.')
                    e.allow_onsite=request.POST.get('enabled')=='1';e.save(update_fields=['allow_onsite']);audit(e,request.user,'onsite_setting',{'enabled':e.allow_onsite})
            elif action=='duplicate':
                from copy import deepcopy
                clone=Event.objects.create(name=e.name+' · nueva edición',date=e.date,registration_end=e.registration_end,location=e.location,price=e.price,capacity=e.capacity,demo=e.demo,rules=deepcopy(e.rules),description=e.description,allow_onsite=e.allow_onsite)
                return redirect('configure',pk=clone.id)
            else: raise ValidationError('Acción desconocida.')
            if action!='phase':messages.success(request,'Cambios guardados.')
        except (ValidationError,ValueError,InvalidOperation,IntegrityError,KeyError) as exc: error(request,exc)
        return redirect(f'/events/{pk}/operations/?tab='+request.POST.get('tab','overview'))
    entries=list(Registration.objects.filter(event=e,state='confirmed').select_related('user','user__profile','participant').prefetch_related('result_set').order_by('bib'))
    for r in entries:
        r.done=sum(m.status=='done' for m in r.result_set.all());r.suggested=suggested_load(e,r.weight)
        r.marks=[{'mark':m,'test_name':e.rules['tests'][m.test]['name'],'unit':e.rules['tests'][m.test]['unit'],'strength':needs_load(e.rules['tests'][m.test]),'scoring':e.rules['tests'][m.test].get('scoring'),'max_points':e.rules['tests'][m.test].get('max_points',100)} for m in r.result_set.all()]
    confirmed=[r for r in entries if r.state=='confirmed']
    summary={'registered':len(confirmed),'present':sum(r.attendance=='present' for r in confirmed),'pending':sum(r.attendance=='pending' for r in confirmed),'remaining':max(0,e.capacity-sum(r.state=='confirmed' for r in entries)),'cash':sum(r.amount for r in confirmed if r.method=='cash'),'stripe':sum(r.amount for r in confirmed if r.method=='stripe')}
    standings=board(e)
    ties=all_ties(standings) if e.status!='closed' else []
    for group in ties:
        group['positions']=range(1,len(group['members'])+1)
        group['resolved']=not any(row.get('tie_pending') for row in group['members'])
    publish_issues=[]
    if e.status=='draft':
        try:validate_rules(e.rules);validate_policies(e.rules,e)
        except ValidationError as exc:publish_issues.extend(exc.messages)
        if not e.capacity:publish_issues.append('Define el cupo de participantes.')
    ties.sort(key=lambda group:(group['resolved'],group['category'],group['scope']))
    pending_ties=sum(not group['resolved'] for group in ties)
    station_options=[{'index':i,'name':t['name'],'allowed':not e.rules.get('ordered_stations') or i in ([0] if e.status=='open' else [e.active_test,e.active_test+1])} for i,t in enumerate(e.rules['tests'])]
    active_station=next((t for i,t in enumerate(e.rules['tests']) if i==e.active_test),None)
    station_done=sum(any(m.test==e.active_test and m.status=='done' for m in r.result_set.all()) for r in confirmed)
    seats=availability(e)
    return render(request,'operations.html',{'event':e,'station_options':station_options,'active_station':active_station,'station_done':station_done,'station_pending_count':station_pending(e).count(),'station_pending_entries':station_pending(e).order_by('bib'),'seats':seats,'registration_notice':'Cupo agotado' if seats['full'] else e.registration_label,'publish_issues':publish_issues,'can_cash':seats['registration_open'] and not seats['full'],'entries':entries,'summary':summary,'board':standings,'capacity_boards':capacity_boards(standings),'ties':ties,'pending_ties':pending_ties,'relative_scoring':is_relative(e),'audits':Audit.objects.filter(event=e).select_related('actor').order_by('-created_at')[:100],'tests':list(enumerate(e.rules['tests'])),'payments':Payment.objects.filter(registration__event=e).select_related('registration')})

@coach_only
def coach(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if request.method=='POST':
        try:
            reg=get_object_or_404(Registration,pk=request.POST['registration'],event=e)
            m=capture(reg.id,request.user,int(request.POST['test']),request.POST.get('value'),request.POST.get('load'),request.POST['status'],int(request.POST['revision']),request.POST.get('reason',''),judged_points=request.POST.get('judged_points'))
            return JsonResponse({'ok':True,'points':m.points,'revision':m.revision,'status':m.status,'provisional':e.rules['tests'][int(request.POST['test'])].get('scoring')=='relative'})
        except (ValidationError,ValueError,KeyError) as exc: return JsonResponse({'ok':False,'error':' '.join(exc.messages) if isinstance(exc,ValidationError) else 'Datos inválidos.'},status=400)
    if not e.rules.get('tests'):
        messages.info(request,'Agrega estaciones antes de abrir la captura.');return redirect('home')
    rows=[]
    for r in Registration.objects.filter(event=e,state='confirmed').select_related('participant').prefetch_related('result_set').order_by('bib'):
        rows.append({'entry':r,'mark':next((mark for mark in r.result_set.all() if mark.test==e.active_test),None),'suggested':load_for(e.rules['tests'][e.active_test],r.weight) if e.rules.get('schema_version')==2 else suggested_load(e,r.weight)})
    if e.rules['tests'][e.active_test].get('scoring')=='relative':
        computed={item['id']:item for item in board(e)}
        for row in rows:
            if row['mark']:row['mark'].points=computed[row['entry'].pk]['marks'][e.active_test]['points']
    complete=sum(1 for row in rows if (row['mark'] and row['mark'].status in ['done','absent','withdrawn']) or row['entry'].attendance in ['withdrawn','disqualified'])
    return render(request,'coach.html',{'event':e,'test':e.rules['tests'][e.active_test],'requires_load':needs_load(e.rules['tests'][e.active_test]),'rows':rows,'complete':complete,'performed':sum(1 for row in rows if row['mark'] and row['mark'].status=='done'),'pending':len(rows)-complete})

def tv(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if e.status=='draft': return HttpResponseForbidden()
    return render(request,'tv.html',{'event':e})

def live_data(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if e.status=='draft': return HttpResponseForbidden()
    if request.GET.get('view')=='standings':
        rows=board(e)
        response=render(request,'event_results.html',{'event':e,'board':rows,'capacity_boards':capacity_boards(rows)})
        response['Cache-Control']='no-store'
        return response
    standings=board(e)
    pending_ties=sum(any(row.get('tie_pending') for row in group['members']) for group in all_ties(standings)) if e.status=='live' else 0
    response=JsonResponse({'station_closed':e.station_capture_closed,'station_pending':station_pending(e).count(),'pending_ties':pending_ties,'status':e.phase_label,'phase':e.status,'test':e.rules.get('tests',[])[e.active_test]['name'] if 0<=e.active_test<len(e.rules.get('tests',[])) else 'Sin estación activa','test_index':e.active_test,'relative_scoring':is_relative(e),'batch':e.active_batch,'board':standings,'updated':timezone.now().isoformat()})
    response['Cache-Control']='no-store'
    return response

@login_required
def profile(request):
    if request.user.is_superuser or request.user.groups.filter(name='Coach').exists():
        person=Profile.objects.filter(user=request.user).first() or Profile(user=request.user,sex='')
        if request.method=='POST' and request.POST.get('action')=='refresh_photo':
            from .portrait import refresh_saved_portrait
            try:
                refresh_saved_portrait(person)
                messages.success(request,'Foto mejorada desde el original.')
            except (ValidationError,OSError) as exc:
                messages.error(request,' '.join(exc.messages) if isinstance(exc,ValidationError) else 'No se pudo leer el original. Toma una foto nueva.')
            return redirect('profile')
        form=ParticipantPhotoForm(request.POST or None,request.FILES or None,instance=person)
        if request.method=='POST' and form.is_valid():
            if not person.pk:person.save()
            if form.cleaned_data['photo'] is False or request.FILES.get('photo'):save_photo(person,form.cleaned_data['photo'],form.cleaned_data.get('original_photo'))
            messages.success(request,'Foto de perfil actualizada.')
            return redirect('profile')
        return render(request,'staff_profile.html',{'profile':person,'form':form})
    return redirect('public_search')

@administrator
def participant_lookup(request):
    u=User.objects.filter(username=request.GET.get('email','').strip().lower()).first()
    return JsonResponse({'found':bool(u),'name':u.get_full_name() if u else '', 'name_parts':name_parts(u) if u else {}, 'sex':u.profile.sex if u and hasattr(u,'profile') else '', 'birth_date':u.profile.birth_date.isoformat() if u and hasattr(u,'profile') and u.profile.birth_date else ''})

@login_required
def registration_status(request,pk):
    r=Registration.objects.filter(event_id=pk,user=request.user).first()
    response=JsonResponse({'state':r.state if r else None,'bib':r.bib if r else None});response['Cache-Control']='no-store';return response

@login_required
@require_POST
def cancel_payment(request,pk):
    r=get_object_or_404(Registration,event_id=pk,user=request.user)
    try: cancel_checkout(r.id,request.user);messages.success(request,'Reserva cancelada. Puedes volver a inscribirte si hay cupo.')
    except (ValidationError,stripe.StripeError) as exc:error(request,exc)
    return redirect('event',pk=pk)

def not_found(request,exception):return render(request,'error.html',{'code':'404','title':'Esta ruta no está en el recorrido.','detail':'Vuelve a los eventos para continuar.'},status=404)
def server_error(request):return render(request,'error.html',{'code':'500','title':'No pudimos completar esta acción.','detail':'Intenta otra vez. Si guardabas una marca o un pago, verifica su estado antes de repetirlo.'},status=500)


@administrator
def price_quote(request,pk):
    e=get_object_or_404(Event,pk=pk)
    try:
        result=quote_price(e,request.GET.get('code',''))
        return JsonResponse({**result,'locked':False})
    except ValidationError as exc:return JsonResponse({'error':' '.join(exc.messages)},status=400)


def event_availability(request,pk):
    event=get_object_or_404(Event,pk=pk)
    if event.status=='draft' and not request.user.is_superuser:return denied(request)
    response=JsonResponse({**availability(event),'server_now':timezone.now().isoformat()})
    response['Cache-Control']='no-store'
    return response

@administrator
def participant_photo(request,pk):
    participant=get_object_or_404(User,pk=pk)
    person=get_object_or_404(Profile,user=participant)
    form=ParticipantPhotoForm(request.POST or None,request.FILES or None,instance=person)
    target=next_url(request)
    if request.method=='POST' and form.is_valid():
        if form.cleaned_data['photo'] is False or request.FILES.get('photo'):
            save_photo(person,form.cleaned_data['photo'],form.cleaned_data.get('original_photo'))
            messages.success(request,'Foto de participante actualizada.')
        return redirect(target)
    return render(request,'participant_photo.html',{'participant':participant,'profile':person,'form':form,'next':target})


@login_required
@require_POST
def portrait_preview(request):
    from .portrait import sports_photo
    if not request.FILES.get('photo'):return JsonResponse({'error':'Selecciona una foto.'},status=400)
    try:
        response=HttpResponse(sports_photo(request.FILES['photo']),content_type='image/jpeg')
        response['Cache-Control']='no-store';return response
    except ValidationError as exc:return JsonResponse({'error':' '.join(exc.messages)},status=400)
    except Exception:
        logging.getLogger(__name__).exception('Local portrait processing failed')
        return JsonResponse({'error':'No se pudo generar el acabado deportivo. Vuelve a intentar o toma otra foto.'},status=503)
