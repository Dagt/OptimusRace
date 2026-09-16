from django.shortcuts import render,redirect,get_object_or_404
import uuid
from django.core import signing
from django.db import transaction,IntegrityError
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from .models import Participant,Event,Registration
from .views import administrator
from .participant_forms import PersonForm,DeskForm
from .photos import save_photo
from .services import register_person_cash,board
from .progress import comparison_key,comparison_label
from .relative_scoring import is_relative
from .availability import availability


def search_people(query,public=False,event=None):
    people=Participant.objects.all()
    entries=Registration.objects.filter(event__status__in=['open','live','closed'])
    if public:entries=entries.filter(state='confirmed')
    if event:entries=entries.filter(event_id=event)
    if public or event:people=people.filter(pk__in=entries.values('participant_id'))
    if query:
        numeric=query.upper().removeprefix('P').removeprefix('#')
        if numeric.isdigit():
            predicate=Q(pk=int(numeric))
            if not query.upper().startswith('P'):predicate|=Q(pk__in=entries.filter(bib=int(numeric)).values('participant_id'))
            people=people.filter(predicate)
        else:
            for word in query.split():people=people.filter(Q(name__icontains=word)|Q(paternal__icontains=word)|Q(maternal__icontains=word))
    return people.distinct().order_by('name','paternal')

@require_GET
def public_search(request):
    query=request.GET.get('q','').strip()[:150];event=request.GET.get('event','')
    if not event.isdigit():event=None
    people=search_people(query,True,event)[:50]
    return render(request,'public_search.html',{'people':people,'query':query,'events':Event.objects.exclude(status='draft').order_by('-date'),'selected_event':int(event) if event else None})

@require_GET
def public_profile(request,pk):
    person=get_object_or_404(Participant,pk=pk)
    entries=Registration.objects.filter(participant=person,state='confirmed').exclude(event__status='draft').select_related('event').order_by('-event__date')
    if not entries.exists() and not request.user.is_superuser:
        from django.http import Http404
        raise Http404
    history=[]
    for entry in entries:
        row=next((item for item in board(entry.event) if item['id']==entry.pk),None)
        history.append({'entry':entry,'row':row})
    selected=next((h for h in history if str(h['entry'].event_id)==request.GET.get('event')),history[0] if history else None)
    chart_history=[{'id':h['entry'].event_id,'name':h['entry'].event.name,'date':h['entry'].event.date.isoformat(),'label':timezone.localtime(h['entry'].event.date).strftime('%d %b %Y'),'version':h['entry'].event.version,'demo':h['entry'].event.demo,'rules':[{**test,'comparison_key':comparison_key(test),'comparison_label':comparison_label(test)} for test in h['entry'].event.rules['tests']],'row':h['row'],'relative':is_relative(h['entry'].event),'closed':h['entry'].event.status=='closed'} for h in reversed(history)]
    return render(request,'public_profile.html',{'participant':person,'profile':person,'history':history,'selected':selected,'chart_history':chart_history})

@administrator
def participants(request):
    query=request.GET.get('q','').strip()[:150]
    people=list(search_people(query)[:100])
    public_ids=set(Registration.objects.filter(participant__in=people,state='confirmed').exclude(event__status='draft').values_list('participant_id',flat=True))
    for person in people:person.is_public=person.pk in public_ids
    events=list(Event.objects.filter(status__in=['open','live']).order_by('date'))
    for event in events:event.seats=availability(event)
    return render(request,'participants.html',{'people':people,'query':query,'events':events})

@administrator
def edit_person(request,pk):
    person=get_object_or_404(Participant,pk=pk)
    if request.method=='POST' and request.POST.get('action')=='refresh_photo':
        from .portrait import refresh_saved_portrait
        try:
            refresh_saved_portrait(person)
            messages.success(request,'Foto mejorada desde el original. Revisa el nuevo retrato.')
        except (ValidationError,OSError) as exc:
            messages.error(request,' '.join(exc.messages) if isinstance(exc,ValidationError) else 'No se pudo leer la foto original. Toma una foto nueva.')
        return redirect('participant_edit',pk=pk)
    form=PersonForm(request.POST or None,request.FILES or None,instance=person)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            saved=form.save(commit=False)
            if request.FILES.get('photo'):saved.photo=Participant.objects.get(pk=person.pk).photo
            saved.save()
            if request.FILES.get('photo') or form.cleaned_data.get('photo') is False:save_photo(person,form.cleaned_data['photo'],form.cleaned_data.get('original_photo'))
        messages.success(request,'Ficha actualizada. Los datos de inscripciones anteriores se conservan.')
        return redirect('participants')
    return render(request,'person_form.html',{'form':form,'profile':person})

@administrator
def desk_register(request,pk):
    event=get_object_or_404(Event,pk=pk)
    token=request.POST.get('request_token','') if request.method=='POST' else signing.dumps({'key':uuid.uuid4().hex,'event':pk,'actor':request.user.pk},salt='desk-registration')
    if request.method=='POST':
        try:
            payload=signing.loads(token,salt='desk-registration')
            if payload['event']!=pk or payload['actor']!=request.user.pk:raise signing.BadSignature
        except (signing.BadSignature,KeyError,TypeError):
            return HttpResponse('Formulario no válido. Vuelve a abrir la inscripción desde el evento.',status=400)
        if Registration.objects.filter(request_key=payload['key']).exists():
            messages.info(request,'Esta inscripción ya fue guardada. No se duplicó el registro de efectivo.')
            return redirect('operations',pk=pk)
    person_id=request.POST.get('participant') if request.method=='POST' else request.GET.get('participant')
    if person_id and not person_id.isdigit():return HttpResponse('Número de participante no válido.',status=400)
    person=get_object_or_404(Participant,pk=person_id) if person_id else None
    form=DeskForm(request.POST or None,request.FILES or None,instance=person)
    query=request.GET.get('q','').strip()[:150]
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                saved=form.save(commit=False)
                # File writes happen after business validation, never for rejected registrations.
                photo=form.cleaned_data.get('photo')
                if request.FILES.get('photo'):saved.photo=Participant.objects.get(pk=person.pk).photo if person else ''
                saved.save()
                entry=register_person_cash(event.pk,saved,request.user,form.cleaned_data['weight'],form.cleaned_data.get('discount_code',''),payload['key'])
                if request.FILES.get('photo'):save_photo(saved,photo,form.cleaned_data.get('original_photo'))
            messages.success(request,f'Inscripción confirmada: P{saved.pk} · número de participante #{entry.bib}. Foto, peso y efectivo registrados. Consulta su historial sin cuenta ni contraseña.')
            return redirect('operations',pk=event.pk)
        except ValidationError as exc:form.add_error(None,exc)
        except IntegrityError:
            if Registration.objects.filter(request_key=payload['key']).exists():return redirect('operations',pk=pk)
            raise
    matches=list(search_people(query)[:25]) if query else []
    registered_ids=set(Registration.objects.filter(event=event,participant__in=matches,state='confirmed').values_list('participant_id',flat=True))
    for match in matches:match.already_registered=match.pk in registered_ids
    if request.method=='GET' and not person and len(matches)==1 and query.upper()==f'P{matches[0].pk}' and not matches[0].already_registered:
        return redirect(f'{request.path}?participant={matches[0].pk}')
    seats=availability(event)
    return render(request,'desk_register.html',{'seats':seats,'can_register':seats['registration_open'] and not seats['full'],'request_token':token,'event':event,'form':form,'profile':person,'person':person,'query':query,'matches':matches})

def retired(request,*args,**kwargs):
    return HttpResponse('Los participantes ya no necesitan cuenta. Inscripción presencial con efectivo. Consulta pública en /results/.',status=410,content_type='text/plain; charset=utf-8')
