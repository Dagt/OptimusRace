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

def staff(view):
    @wraps(view)
    @login_required
    def wrapped(request,*args,**kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name='Coach').exists()): return denied(request)
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
    own={r.event_id:r for r in Registration.objects.filter(user=request.user)} if request.user.is_authenticated else {}
    for e in events:
        e.taken=Registration.objects.filter(event=e,state__in=['reserved','confirmed']).count()
        e.remaining=max(0,e.capacity-e.taken);e.fill=round(e.taken/e.capacity*100) if e.capacity else 0;e.entry=own.get(e.id)
    summary={'events':len(events),'athletes':Registration.objects.filter(state='confirmed').count(),'present':Registration.objects.filter(attendance='present',event__status='live').count(),'income':Registration.objects.filter(state='confirmed').aggregate(total=Sum('amount'))['total'] or 0}
    return render(request,'home.html',{'events':events,'summary':summary,'own_count':len(own)})

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
            if user:
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
                Profile.objects.create(user=user,sex=d['sex'])
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
    occupied=Registration.objects.filter(event=e,state__in=['reserved','confirmed']).count()
    return render(request,'event.html',{'event':e,'entry':entry,'board':board(e),'occupied':occupied,'remaining':max(0,e.capacity-occupied),'can_enroll':e.status=='open' and timezone.now()<=e.registration_end,'stripe_ready':bool(settings.STRIPE_SECRET_KEY),'payment_mode':settings.STRIPE_MODE})

@login_required
@require_POST
def enroll(request,pk):
    try: return redirect(checkout(pk,request.user))
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
    rules=e.rules if e else default_rules()
    if request.method=='POST' and form.is_valid():
        try:
            rules=json.loads(request.POST['rules'])
            validate_rules(rules,False)
            if e: e=configure(e.id,request.user,{**form.cleaned_data,'rules':rules})
            else:
                e=form.save(commit=False); e.rules=rules; e.save(); audit(e,request.user,'created',{'rules':rules})
            messages.success(request,'Configuración guardada.'); return redirect('operations',pk=e.id)
        except (ValidationError,ValueError,KeyError) as exc: error(request,exc)
    return render(request,'configure.html',{'form':form,'event':e,'rules':rules,'locked':bool(e and e.status!='draft'),'catalog':list(Exercise.objects.values('name','unit','capacity','higher','base','elite'))})

def default_rules():
    names=['Sentadilla','Press banca','1000 m','Burpees 5 min','50 m','Shuttle 10x10','Salto horizontal','Salto vertical']
    catalog={x['name']:x for x in Exercise.objects.values('name','unit','capacity','higher','base','elite')}
    return {'tests':[catalog[n] for n in names if n in catalog],'categories':[{'name':'Hombres · abierta','sex':'M','min':0,'max':None},{'name':'Mujeres · abierta','sex':'F','min':0,'max':None}],'bar':0,'rounding':0,'round_mode':'none'}

@administrator
def operations(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if request.method=='POST':
        try:
            action=request.POST['action']
            if action=='phase': change_phase(pk,request.user,request.POST['phase'],int(request.POST.get('test',0)),int(request.POST.get('batch',1)))
            elif action=='cash':
                with transaction.atomic():
                    email=request.POST['email'].lower().strip(); validate_email(email)
                    user=User.objects.filter(username=email).first()
                    if not user:
                        name=request.POST.get('name','').strip(); sex=request.POST.get('sex')
                        if not name or sex not in ['M','F']: raise ValidationError('Nombre y sexo son obligatorios para un participante nuevo.')
                        user=User.objects.create_user(username=email,email=email,first_name=name,password=secrets.token_urlsafe(32))
                        Profile.objects.create(user=user,sex=sex)
                    elif not Profile.objects.filter(user=user).exists():
                        if request.POST.get('sex') not in ['M','F']: raise ValidationError('Selecciona el sexo del participante.')
                        Profile.objects.create(user=user,sex=request.POST['sex'])
                    amount=Decimal(request.POST['amount'])*100
                    if amount!=amount.to_integral_value(): raise ValidationError('El monto admite máximo dos decimales.')
                    cash_register(pk,user,request.user,int(amount))
                messages.success(request,'Inscripción y cobro efectivo registrados. La cuenta puede recuperar su contraseña con su correo.')
            elif action=='reception':
                r=get_object_or_404(Registration,pk=request.POST['registration'],event=e)
                check_in(r.id,request.user,request.POST['weight'],request.POST['batch'],request.POST['attendance'],request.POST.get('reason',''),int(request.POST['revision']))
            elif action=='correct':
                r=get_object_or_404(Registration,pk=request.POST['registration'],event=e)
                capture(r.id,request.user,int(request.POST['test']),request.POST.get('value'),request.POST.get('load'),request.POST['status'],int(request.POST['revision']),request.POST.get('reason',''),administrative=True)
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
            messages.success(request,'Cambios guardados.')
        except (ValidationError,ValueError,InvalidOperation,IntegrityError,KeyError) as exc: error(request,exc)
        return redirect(f'/events/{pk}/operations/?tab='+request.POST.get('tab','overview'))
    entries=list(Registration.objects.filter(event=e).select_related('user').prefetch_related('result_set').order_by('bib'))
    for r in entries:
        r.done=sum(m.status=='done' for m in r.result_set.all());r.suggested=suggested_load(e,r.weight)
        r.marks=[{'mark':m,'test_name':e.rules['tests'][m.test]['name'],'unit':e.rules['tests'][m.test]['unit'],'strength':e.rules['tests'][m.test]['capacity']=='Fuerza'} for m in r.result_set.all()]
    confirmed=[r for r in entries if r.state=='confirmed']
    summary={'registered':len(confirmed),'present':sum(r.attendance=='present' for r in confirmed),'pending':sum(r.attendance=='pending' for r in confirmed),'remaining':max(0,e.capacity-sum(r.state in ['confirmed','reserved'] for r in entries)),'cash':sum(r.amount for r in confirmed if r.method=='cash'),'stripe':sum(r.amount for r in confirmed if r.method=='stripe')}
    return render(request,'operations.html',{'event':e,'can_cash':(e.status=='open' and timezone.now()<=e.registration_end) or (e.status=='live' and e.allow_onsite),'entries':entries,'summary':summary,'board':board(e),'audits':Audit.objects.filter(event=e).select_related('actor').order_by('-created_at')[:100],'tests':list(enumerate(e.rules['tests'])),'payments':Payment.objects.filter(registration__event=e).select_related('registration')})

@staff
def coach(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if request.method=='POST':
        try:
            reg=get_object_or_404(Registration,pk=request.POST['registration'],event=e)
            m=capture(reg.id,request.user,int(request.POST['test']),request.POST.get('value'),request.POST.get('load'),request.POST['status'],int(request.POST['revision']),request.POST.get('reason',''))
            return JsonResponse({'ok':True,'points':m.points,'revision':m.revision,'status':m.status})
        except (ValidationError,ValueError,KeyError) as exc: return JsonResponse({'ok':False,'error':' '.join(exc.messages) if isinstance(exc,ValidationError) else 'Datos inválidos.'},status=400)
    rows=[]
    for r in Registration.objects.filter(event=e,state='confirmed',batch=e.active_batch).order_by('bib'):
        rows.append({'entry':r,'mark':Result.objects.filter(registration=r,test=e.active_test).first(),'suggested':suggested_load(e,r.weight)})
    complete=sum(1 for row in rows if row['mark'] and row['mark'].status=='done')
    return render(request,'coach.html',{'event':e,'test':e.rules['tests'][e.active_test],'rows':rows,'complete':complete,'pending':len(rows)-complete})

def tv(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if e.status=='draft': return HttpResponseForbidden()
    return render(request,'tv.html',{'event':e})

def live_data(request,pk):
    e=get_object_or_404(Event,pk=pk)
    if e.status=='draft': return HttpResponseForbidden()
    response=JsonResponse({'status':e.get_status_display(),'phase':e.status,'test':e.rules['tests'][e.active_test]['name'],'test_index':e.active_test,'batch':e.active_batch,'board':board(e),'updated':timezone.now().isoformat()})
    response['Cache-Control']='no-store'
    return response

@login_required
def profile(request):
    p,_=Profile.objects.get_or_create(user=request.user,defaults={'sex':'M'})
    form=PhotoForm(request.POST or None,request.FILES or None,instance=p)
    if request.method=='POST' and form.is_valid():
        # Re-encode image to remove metadata and unexpected file payloads.
        from PIL import Image,ImageOps
        from io import BytesIO
        from django.core.files.base import ContentFile
        upload=form.cleaned_data['photo']
        p.sex=form.cleaned_data['sex'];p.save(update_fields=['sex'])
        if upload is False:
            p.photo='';p.save(update_fields=['photo'])
        elif request.FILES.get('photo'):
            im=ImageOps.exif_transpose(Image.open(upload)).convert('RGB'); im.thumbnail((1000,1000)); out=BytesIO(); im.save(out,format='JPEG',quality=88)
            p.photo.save(f'{uuid.uuid4()}.jpg',ContentFile(out.getvalue()))
        messages.success(request,'Perfil actualizado.');return redirect('profile')
    history=[]
    for r in Registration.objects.filter(user=request.user).select_related('event').order_by('-event__date'):
        row=next((x for x in board(r.event) if x['id']==r.id),None)
        history.append({'entry':r,'row':row})
    selected=next((h for h in history if str(h['entry'].event_id)==request.GET.get('event')),history[0] if history else None)
    chart_history=[{'id':h['entry'].event_id,'name':h['entry'].event.name,'date':h['entry'].event.date.isoformat(),'label':timezone.localtime(h['entry'].event.date).strftime('%d %b %Y'),'version':h['entry'].event.version,'demo':h['entry'].event.demo,'rules':h['entry'].event.rules['tests'],'row':h['row']} for h in reversed(history)]
    return render(request,'profile.html',{'profile':p,'form':form,'history':history,'selected':selected,'chart_history':chart_history})

@administrator
def participant_lookup(request):
    u=User.objects.filter(username=request.GET.get('email','').strip().lower()).first()
    return JsonResponse({'found':bool(u),'name':u.first_name if u else '', 'sex':u.profile.sex if u and hasattr(u,'profile') else ''})

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
