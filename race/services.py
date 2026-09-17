import math, uuid
from collections import Counter
from datetime import timedelta
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
import stripe
from .event_policy import current_price, validate_eligibility,validate_policies,quote_price,registration_open,instant
from .exercise_parameters import validate_parameters,validate_mark,needs_load,load_for
from .relative_scoring import relative_points,is_relative,apply_tiebreaks
from .models import Event, Registration, Result, Audit, Payment, Webhook

CAPACITIES = ['Fuerza','Resistencia','Velocidad','Potencia']

def number(value, minimum=0):
    try: value = float(value)
    except (ValueError, TypeError): raise ValidationError('Introduce un número válido.')
    if not math.isfinite(value) or value < minimum: raise ValidationError('Número fuera de rango.')
    return value

def validate_rules(rules, complete=True):
    try:
        tests, cats = rules['tests'], rules['categories']
        modern = rules.get('schema_version',1)==2
        if modern:
            if len(tests)>32 or (complete and not tests):raise ValidationError('Configura entre 1 y 32 estaciones.')
            if any(t['capacity'] not in CAPACITIES for t in tests):raise ValidationError('Capacidad inválida.')
            if complete and abs(sum(number(t.get('max_points'),.01) for t in tests)-100)>.000001:raise ValidationError('Los máximos por estación deben sumar 100 puntos.')
            for t in tests:
                number(t.get('max_points'),.01);validate_parameters(t.get('parameters',{}))
            validate_policies(rules)
        elif len(tests) != 8 or Counter(t['capacity'] for t in tests) != Counter({c:2 for c in CAPACITIES}):
            raise ValidationError('Se requieren ocho pruebas: dos por capacidad.')
        if len({t['name'] for t in tests}) != len(tests): raise ValidationError('Las pruebas deben ser distintas.')
        for t in tests:
            if not t['name'].strip() or not t['unit'].strip() or not isinstance(t['higher'],bool): raise ValidationError('Nombre, unidad y dirección obligatorios.')
            method=t.get('scoring','linear')
            if method not in ['pending','linear','judge','relative']:raise ValidationError('Método de puntuación inválido.')
            if method=='pending':
                if complete:raise ValidationError(f"Confirma la escala de puntuación de {t['name']}.")
                continue
            if method=='relative':
                if not modern:raise ValidationError('La puntuación relativa requiere un evento con reglas versión 2.')
                continue
            if method=='judge':
                if complete and not rules.get('judging_standard','').strip():raise ValidationError('Describe la escala acordada con los jueces antes de publicar.')
                continue
            if t.get('base') is None or t.get('elite') is None:
                if complete: raise ValidationError(f"Faltan benchmarks de {t['name']}.")
                continue
            base, elite = number(t['base']), number(t['elite'])
            t['base'],t['elite']=base,elite
            if (elite <= base if t['higher'] else elite >= base): raise ValidationError('El benchmark élite debe mejorar al base.')
        if any(c['sex'] not in ['M','F'] for c in cats):raise ValidationError('Categoría por sexo inválida.')
        if complete and not cats:raise ValidationError('Agrega al menos una categoría de participantes.')
        if not modern and set(c['sex'] for c in cats)!={'M','F'}:raise ValidationError('Configura categorías para hombres y mujeres.')
        if len({c['name'] for c in cats}) != len(cats): raise ValidationError('Nombres de categoría únicos.')
        for sex in ['M','F']:
            previous = 0
            for c in sorted([c for c in cats if c['sex']==sex],key=lambda c:number(c['min'])):
                low = number(c['min']); high = number(c['max']) if c['max'] is not None else math.inf
                if low < previous or high <= low: raise ValidationError('Categorías solapadas o límites inválidos. El mínimo se incluye y el máximo se excluye.')
                c['min']=low; c['max']=None if high==math.inf else high
                if not c['name'].strip(): raise ValidationError('Cada categoría requiere nombre.')
                previous = high
        if modern:
            age=number(rules.get('minimum_age',0))
            if not age.is_integer() or age>120:raise ValidationError('Edad mínima inválida.')
            rules['minimum_age']=int(age)
            if rules.get('attempts',1)!=1:raise ValidationError('El motor actual registra una marca final por estación; las correcciones requieren motivo.')
        rules['bar']=number(rules.get('bar',0)); rules['rounding']=number(rules.get('rounding',0))
        if rules.get('round_mode','none') not in ['none','nearest','down','up']: raise ValidationError('Redondeo inválido.')
    except (KeyError,TypeError,AttributeError,ValueError): raise ValidationError('Configuración incompleta.')
    return rules

def score(value, test, judged_points=None):
    value = number(value)
    maximum=number(test.get('max_points',100),.01)
    if test.get('scoring')=='relative':return None
    if test.get('scoring')=='pending':raise ValidationError('La escala de jueces todavía está pendiente.')
    if test.get('scoring')=='judge':
        points=number(judged_points)
        if points>maximum:raise ValidationError(f'El puntaje debe estar entre 0 y {maximum:g}.')
        return round(points,6)
    if test.get('base') is None or test.get('elite') is None: raise ValidationError('Configura los benchmarks antes de capturar.')
    return round(maximum*max(0,min(1,.5+.5*(value-test['base'])/(test['elite']-test['base']))),6)

def category(rules, sex, weight):
    weight = number(weight,0.01)
    categories=sorted((c for c in rules['categories'] if c['sex']==sex),key=lambda c:c['min'])
    for index,c in enumerate(categories):
        if rules.get('category_bounds')=='upper_inclusive':
            above=weight>c['min'] or (index==0 and weight==c['min'])
            if above and (c['max'] is None or weight<=c['max']):return c['name']
        elif c['min']<=weight and (c['max'] is None or weight<c['max']):return c['name']
    raise ValidationError('El peso no corresponde a una categoría. Revisa los rangos del evento.')

def suggested_load(event, weight):
    if weight is None: return None
    value = weight*event.rules.get('load_percent',75)/100
    step, mode, bar = event.rules.get('rounding',0),event.rules.get('round_mode','none'),event.rules.get('bar',0)
    if step and mode != 'none':
        fn = {'nearest':lambda x: math.floor(x+.5),'down':math.floor,'up':math.ceil}[mode]
        value = bar + fn(max(0,value-bar)/step)*step
        value = max(bar,value)
    return round(value,3)

def audit(event,actor,action,details):
    Audit.objects.create(event=event,actor=actor,action=action,details=details)

def board(event):
    if event.status == 'closed':
        from copy import deepcopy
        return attach_participant_links(event,deepcopy(event.final_board))
    rows=[];modern=event.rules.get('schema_version',1)==2
    entries=list(Registration.objects.filter(event=event,state='confirmed').order_by('bib').prefetch_related('result_set'))
    marks_by_entry={r.pk:{m.test:m for m in r.result_set.all()} for r in entries}
    pools={}
    for r in entries:
        if not r.category or r.attendance=='disqualified':continue
        for i,m in marks_by_entry[r.pk].items():
            if m.status=='done' and m.value is not None:pools.setdefault((r.category,i),[]).append(m.value)
    ranges={key:[min(values),max(values)] for key,values in pools.items()}
    for r in entries:
        marks=marks_by_entry[r.pk];details=[]
        for i,t in enumerate(event.rules['tests']):
            m=marks.get(i);maximum=t.get('max_points',100);points=m.points if m and m.status=='done' else None
            relative=t.get('scoring')=='relative'
            if relative:
                points=relative_points(m.value,ranges.get((r.category,i),[]),maximum,t['higher']) if m and m.status=='done' and m.value is not None and r.category and r.attendance!='disqualified' else None
            details.append({'test':t['name'],'unit':t['unit'],'capacity':t['capacity'],'value':m.value if m else None,'points':points,'max_points':maximum,
                            'normalized_points':round(100*points/maximum,4) if points is not None else None,'status':m.status if m else 'pending','load':m.load if m else None,
                            'revision':m.revision if m else 0,'relative':relative,'provisional':relative,'sample_size':len(pools.get((r.category,i),[])) if relative else None})
        capacities={c:round(100*sum(m['points'] or 0 for m in details if m['capacity']==c)/(sum(m['max_points'] for m in details if m['capacity']==c) or 1),2) for c in CAPACITIES}
        done=sum(m['status']=='done' for m in details)
        rows.append({'id':r.id,'participant_id':r.participant_id,'user_id':r.user_id,'name':r.name,'bib':r.bib,'category':r.category or 'Sin pesaje','batch':r.batch,'attendance':r.attendance,
                     'total':round(sum(m['points'] or 0 for m in details)/(1 if modern else (len(details) or 1)),4),'completed':done,'test_count':len(details),
                     'capacities':capacities,'marks':details,'rank':None,'relative':is_relative(event),'provisional':is_relative(event),'tie_pending':False,'champion':False})
    rows.sort(key=lambda r:(r['attendance']=='disqualified',-r['total'],r['bib']))
    for row in rows:
        if row['category']!='Sin pesaje' and row['completed'] and row['attendance']!='disqualified':
            row['rank']=1+sum(other['attendance']!='disqualified' and other['category']==row['category'] and other['completed']>0 and other['total']>row['total'] for other in rows)
    apply_tiebreaks(event,rows)
    from .capacity_results import attach_capacity_results
    attach_capacity_results(event,rows)
    rows.sort(key=lambda r:(r['attendance']=='disqualified',-r['total'],r['rank'] if r['rank'] is not None else float('inf'),r['bib']))
    return attach_participant_links(event,rows)

def attach_participant_links(event,rows):
    """Hydrate current photos without changing a closed event's stored standings."""
    from django.urls import reverse
    people={r.pk:r.participant for r in Registration.objects.filter(event=event,state='confirmed').select_related('participant')}
    for row in rows:
        person=people.get(row['id'])
        identity={'participant_id':person.pk if person else None,'photo_url':person.photo.url if person and person.photo else '', 'profile_url':reverse('public_participant',args=[person.pk]) if person else ''}
        row.update(identity)
        for result in row.get('capacity_results',{}).values():result.update(identity)
    return rows

@transaction.atomic
def configure(event_id, actor, data):
    e=Event.objects.select_for_update().get(pk=event_id)
    if Registration.objects.filter(event=e).exists() or e.status!='draft': raise ValidationError('Las reglas se bloquean al publicar o inscribir. Crea otro evento para nuevas reglas.')
    validate_rules(data['rules'],False)
    e.name=data['name']; e.location=data['location']; e.rules=data['rules']; e.capacity=data['capacity']; e.price=data['price']; e.date=data['date']; e.registration_end=data['registration_end']; e.demo=data['demo']; e.description=data.get('description',''); e.allow_onsite=data.get('allow_onsite',False)
    validate_policies(e.rules,e)
    e.version+=1; e.full_clean(); e.save()
    audit(e,actor,'configuration',{'version':e.version,'rules':e.rules})
    return e

@transaction.atomic
def change_phase(event_id, actor, phase, test=0,batch=1):
    e=Event.objects.select_for_update().get(pk=event_id)
    allowed={'draft':['open'],'open':['live'],'live':['live','closed'],'closed':[]}
    if phase not in allowed[e.status]: raise ValidationError('Transición de evento no permitida.')
    validate_rules(e.rules)
    validate_policies(e.rules,e)
    if phase=='open' and e.capacity<1:raise ValidationError('Confirma el cupo del evento antes de publicar.')
    if phase=='live':
        if e.rules.get('ordered_stations') and test not in ([0] if e.status=='open' else [e.active_test,e.active_test+1]):raise ValidationError('Debes seguir el orden de estaciones: conserva la actual o avanza a la siguiente.')
        if not 0<=test<len(e.rules['tests']) or batch<1: raise ValidationError('Prueba o lote inválido.')
        e.active_test=test; e.active_batch=batch
    if phase=='closed':
        frozen=board(e)
        for row in frozen:
            if any(result['tie_pending'] and result['rank'] is not None and result['rank']<=3 for result in row.get('capacity_results',{}).values()):raise ValidationError('Resuelve los empates del podio por capacidad antes de cerrar.')
        if is_relative(e) and any(r['tie_pending'] and r['rank']<=3 for r in frozen if r['rank'] is not None):raise ValidationError('Resuelve los empates del podio por categoría antes de cerrar el evento.')
        for row in frozen:
            for result in row.get('capacity_results',{}).values():
                result['provisional']=False;result['winner']=result['rank']==1 and not result['tie_pending']
                for mark in result['marks']:mark['provisional']=False
            row['provisional']=False;row['champion']=row['rank']==1 and not row['tie_pending']
            for index,mark in enumerate(row['marks']):
                mark['provisional']=False
                if mark['relative']:Result.objects.filter(registration_id=row['id'],test=index).update(points=mark['points'])
        e.final_board=frozen; e.closed_at=timezone.now()
    e.status=phase; e.save(); audit(e,actor,'phase',{'phase':phase,'test':test,'batch':batch})

def reserve_locked(e,user, onsite=False,discount_code=""):
    raise ValidationError('No se permiten reservas. La inscripción se confirma al registrar el pago en mostrador.')

@transaction.atomic
def cash_register(event_id,user,actor,amount,discount_code=""):
    """Compatibility for existing participant accounts: payment and entry are atomic."""
    if not actor.is_superuser:raise ValidationError('Solo administración puede registrar pagos.')
    e=Event.objects.select_for_update().get(pk=event_id)
    if user.is_superuser or user.groups.filter(name='Coach').exists():raise ValidationError('Solo participantes pueden inscribirse.')
    if not hasattr(user,'profile'):raise ValidationError('Completa el perfil del participante.')
    validate_eligibility(e,user.profile.birth_date)
    if not registration_open(e,onsite=True):raise ValidationError('Las inscripciones están cerradas.')
    r=Registration.objects.filter(event=e,user=user).first()
    if r and r.state=='confirmed':raise ValidationError('La inscripción ya está confirmada. No se registró otro cobro.')
    if r and Payment.objects.filter(registration=r,state__in=['creating','pending']).exists():raise ValidationError('Concilia el pago histórico antes de cobrar efectivo.')
    if Registration.objects.filter(event=e,state='confirmed').count()>=e.capacity:raise ValidationError('Cupo agotado.')
    quote=quote_price(e,discount_code,exclude_registration=r.pk if r else None)
    if int(amount)!=quote['amount']:raise ValidationError('El importe debe coincidir con la tarifa y descuento calculados.')
    if not r:
        bib=(Registration.objects.filter(event=e).aggregate(m=Max('bib'))['m'] or 0)+1
        r=Registration(event=e,user=user,name=user.get_full_name() or user.username,sex=user.profile.sex,bib=bib,birth_date=user.profile.birth_date)
    r.amount=quote['amount'];r.pricing_code=quote['discount_code'];r.pricing_snapshot=quote
    r.state='confirmed';r.method='cash';r.paid_by=actor;r.paid_at=timezone.now();r.save()
    audit(e,actor,'cash',{'registration':r.id,'amount':r.amount})
    return r


def payment_mode():
    key=settings.STRIPE_SECRET_KEY
    if not key: raise ValidationError('El pago en línea aún no está disponible. No se ha realizado ningún cobro.')
    live=settings.STRIPE_MODE=='live'
    if settings.STRIPE_MODE not in ['test','live']: raise ValidationError('Configuración de pago no válida.')
    if live and (not settings.ALLOW_LIVE_PAYMENTS or settings.DEBUG or not settings.PUBLIC_URL.startswith('https://') or not settings.STRIPE_WEBHOOK_SECRET):
        raise ValidationError('Los pagos reales no están habilitados. Revisa la configuración del servidor.')
    if not key.startswith('sk_live_' if live else 'sk_test_'): raise ValidationError('La clave Stripe no coincide con el modo configurado.')
    return live

def checkout(event_id,user,discount_code=""):
    raise ValidationError('El registro requiere pago confirmado en mostrador. No se crean reservas ni nuevos pagos en línea.')

@transaction.atomic
def fulfill(payload):
    if Webhook.objects.filter(stripe_id=payload['id']).exists(): return
    kind=payload['type']; s=payload['data']['object']
    if kind not in ['checkout.session.completed','checkout.session.expired','checkout.session.async_payment_succeeded']: return
    p=Payment.objects.select_for_update().get(pk=s['metadata']['payment_id'])
    r=Registration.objects.select_for_update().get(pk=p.registration_id)
    event=Event.objects.select_for_update().get(pk=r.event_id)
    if bool(s.get('livemode',False))!=p.livemode or (p.session_id and p.session_id!=s['id']) or s.get('client_reference_id')!=str(r.id): raise ValidationError('Identidad de pago inválida.')
    if kind=='checkout.session.expired':
        if p.state!='paid':
            p.state='expired'
            # A late duplicate expiration belongs to this payment, not a newer reservation.
            if r.state=='reserved' and not Payment.objects.filter(registration=r,state__in=['creating','pending','paid']).exclude(pk=p.id).exists(): r.state='expired'
    elif s.get('payment_status')=='paid':
        if s.get('amount_total')!=p.amount or s.get('currency')!='mxn': raise ValidationError('Monto o moneda no coincide.')
        if p.state=='expired': raise ValidationError('Pago de reserva expirada: requiere conciliación.')
        if r.state!='confirmed' and (event.status=='closed' or Registration.objects.filter(event=event,state='confirmed').count()>=event.capacity):raise ValidationError('Pago histórico: requiere conciliación; evento cerrado o sin cupo.')
        p.state='paid'; r.state='confirmed'; r.method='stripe'; r.paid_at=r.paid_at or timezone.now()
    p.session_id=s['id']; p.save(); r.save()
    Webhook.objects.create(stripe_id=payload['id'])
    audit(r.event,None,'stripe',{'payment':p.id,'state':p.state,'stripe_event':payload['id']})

@transaction.atomic
def check_in(reg_id,actor,weight,batch,attendance,reason='',revision=None):
    r=Registration.objects.select_for_update().select_related('event').get(pk=reg_id)
    e=Event.objects.select_for_update().get(pk=r.event_id)
    if e.status=='closed' or r.state!='confirmed': raise ValidationError('La inscripción debe estar pagada y el evento abierto.')
    if r.attendance=='disqualified':raise ValidationError('Resuelve la descalificación antes de modificar la recepción.')
    if attendance not in ['present','absent','withdrawn']: raise ValidationError('Asistencia inválida.')
    if revision is not None and revision!=r.revision: raise ValidationError('La recepción cambió en otra pantalla. Recarga antes de guardar.')
    changed_weight=r.weight != number(weight,.01)
    if r.result_set.exists() and changed_weight and (not actor.is_superuser or not reason.strip()): raise ValidationError('Corregir un peso con marcas requiere administrador y motivo. Las cargas usadas se conservan.')
    old={'weight':r.weight,'category':r.category,'batch':r.batch,'attendance':r.attendance}
    r.weight=number(weight,.01); r.category=category(e.rules,r.sex,r.weight); r.batch=int(batch)
    if r.batch<1: raise ValidationError('El lote comienza en 1.')
    r.attendance=attendance; r.revision+=1; r.save()
    audit(e,actor,'weight_correction' if changed_weight and r.result_set.exists() else 'reception',{'registration':r.id,'before':old,'after':{'weight':r.weight,'category':r.category,'batch':r.batch,'attendance':r.attendance},'reason':reason})

@transaction.atomic
def capture(reg_id,actor,test,value,load,status,revision,reason,administrative=False,judged_points=None):
    if not actor.is_active or actor.is_superuser or not actor.groups.filter(name='Coach').exists():
        raise ValidationError('Solo los coaches pueden capturar o corregir marcas.')
    r=Registration.objects.select_for_update().select_related('event').get(pk=reg_id)
    e=Event.objects.select_for_update().get(pk=r.event_id)
    if r.attendance=='disqualified':raise ValidationError('El participante está descalificado.')
    if administrative:raise ValidationError('La corrección administrativa de marcas no está permitida.')
    if not 0<=test<len(e.rules['tests']): raise ValidationError('Prueba inválida.')
    if e.status!='live' or test!=e.active_test: raise ValidationError('La prueba activa cambió. Actualiza la pantalla.')
    if r.state!='confirmed' or r.attendance!='present': raise ValidationError('El atleta debe tener recepción confirmada y estar presente.')
    if status not in ['done','absent','withdrawn','pending']: raise ValidationError('Estado inválido.')
    existing=Result.objects.filter(registration=r,test=test).first()
    if (existing.revision if existing else 0)!=revision: raise ValidationError('Otra persona guardó esta marca. Recarga antes de corregir.')
    if existing and not reason.strip(): raise ValidationError('Escribe el motivo de la corrección.')
    before={'value':existing.value,'points':existing.points,'load':existing.load,'status':existing.status,'revision':existing.revision} if existing else None
    t=e.rules['tests'][test]
    v=number(value) if status=='done' else None
    if status=='done':validate_mark(v,t)
    if status=='done' and t['unit']=='reps' and not v.is_integer(): raise ValidationError('Las repeticiones deben ser enteras.')
    if status=='done' and not t['higher'] and v<=0: raise ValidationError('El tiempo debe ser mayor a cero.')
    kg=number(load,.01) if status=='done' and needs_load(t) else None
    mark=existing or Result(registration=r,test=test,revision=0)
    mark.value=v; mark.load=kg; mark.points=score(v,t,judged_points) if v is not None else None; mark.status=status; mark.revision+=1; mark.save()
    audit(e,actor,'correction' if existing else 'capture',{'registration':r.id,'test':test,'before':before,'after':{'value':v,'load':kg,'points':mark.points,'status':status,'revision':mark.revision},'reason':reason})
    if t.get('scoring')=='relative':
        row=next(item for item in board(e) if item['id']==r.id)
        mark.points=row['marks'][test]['points']
    return mark

def cancel_checkout(reg_id,actor):
    r=Registration.objects.get(pk=reg_id)
    if r.user_id!=actor.id and not actor.is_superuser: raise ValidationError('No puedes modificar esta inscripción.')
    if r.state not in ['reserved','expired']: raise ValidationError('Esta inscripción no tiene un pago histórico por conciliar.')
    live=payment_mode()
    p=Payment.objects.filter(registration=r,state__in=['creating','pending']).first()
    if not p or not p.session_id: raise ValidationError('La creación aún no está confirmada. Reintenta el pago o solicita conciliación en recepción.')
    if p.livemode!=live: raise ValidationError('La reserva pertenece a otro modo Stripe.')
    s=stripe.checkout.Session.expire(p.session_id,api_key=settings.STRIPE_SECRET_KEY)
    if s.status!='expired': raise ValidationError('Stripe todavía no confirmó la cancelación. No se ha liberado el lugar.')
    fulfill({'id':f'cancel:{s.id}','type':'checkout.session.expired','data':{'object':s}})
    audit(r.event,actor,'checkout_cancelled',{'registration':r.id,'payment':p.id})


@transaction.atomic
def discipline(reg_id, actor, disqualified, reason, revision):
    r=Registration.objects.select_for_update().select_related('event').get(pk=reg_id)
    e=Event.objects.select_for_update().get(pk=r.event_id)
    if not actor.is_superuser or not reason.strip():raise ValidationError('La decisión requiere administrador y motivo.')
    if e.status not in ['open','live'] or r.state!='confirmed':raise ValidationError('Solo se puede resolver disciplina en eventos abiertos con inscripción confirmada.')
    if r.revision!=revision:raise ValidationError('La inscripción cambió. Recarga antes de continuar.')
    before=r.attendance
    if not disqualified and before!='disqualified':raise ValidationError('El participante no está descalificado.')
    r.attendance='disqualified' if disqualified else 'pending';r.revision+=1;r.save()
    audit(e,actor,'disqualification' if disqualified else 'disqualification_correction',{'registration':r.pk,'before':before,'after':r.attendance,'reason':reason})


@transaction.atomic
def register_person_cash(event_id,person,actor,weight,discount_code='',request_key=None):
    """One atomic cash transaction, category and measured weight at registration."""
    from .models import Participant
    if not actor.is_superuser:raise ValidationError('Solo administración puede registrar pagos.')
    event=Event.objects.select_for_update().get(pk=event_id)
    person=Participant.objects.select_for_update().get(pk=person.pk)
    if not registration_open(event,onsite=True):raise ValidationError('Las inscripciones están cerradas.')
    validate_eligibility(event,person.birth_date)
    existing=Registration.objects.filter(event=event,participant=person).first()
    if existing and existing.state=='confirmed':raise ValidationError('Este participante ya tiene una inscripción en el evento. Revisa su registro; no se cobró de nuevo.')
    if existing and Payment.objects.filter(registration=existing,state__in=['creating','pending']).exists():raise ValidationError('Concilia el pago histórico antes de cobrar de nuevo.')
    if Registration.objects.filter(event=event,state='confirmed').count()>=event.capacity:raise ValidationError('Cupo agotado.')
    weight=number(weight,.01);category_name=category(event.rules,person.sex,weight)
    quote=quote_price(event,discount_code)
    amount=quote['amount']
    bib=(Registration.objects.filter(event=event).aggregate(m=Max('bib'))['m'] or 0)+1
    batch=1  # Historical field only; capture includes every confirmed participant.
    entry=existing or Registration(event=event,participant=person,bib=bib)
    values=dict(request_key=request_key,name=person.full_name,sex=person.sex,birth_date=person.birth_date,state='confirmed',weight=weight,category=category_name,batch=batch,attendance='present',amount=amount,method='cash',paid_by=actor,paid_at=timezone.now(),pricing_code=quote['discount_code'],pricing_snapshot=quote)
    for key,value in values.items():setattr(entry,key,value)
    entry.save()
    audit(event,actor,'cash_registration',{'registration':entry.pk,'participant':person.pk,'amount':amount,'weight':weight,'category':category_name})
    return entry
