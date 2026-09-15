import math, uuid
from collections import Counter
from datetime import timedelta
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
import stripe
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
        if len(tests) != 8 or Counter(t['capacity'] for t in tests) != Counter({c:2 for c in CAPACITIES}):
            raise ValidationError('Se requieren ocho pruebas: dos por capacidad.')
        if len({t['name'] for t in tests}) != 8: raise ValidationError('Las pruebas deben ser distintas.')
        for t in tests:
            if not t['name'].strip() or not t['unit'].strip() or not isinstance(t['higher'],bool): raise ValidationError('Nombre, unidad y dirección obligatorios.')
            if t.get('base') is None or t.get('elite') is None:
                if complete: raise ValidationError(f"Faltan benchmarks de {t['name']}.")
                continue
            base, elite = number(t['base']), number(t['elite'])
            t['base'],t['elite']=base,elite
            if (elite <= base if t['higher'] else elite >= base): raise ValidationError('El benchmark élite debe mejorar al base.')
        if not cats or set(c['sex'] for c in cats) != {'M','F'}: raise ValidationError('Configura categorías para hombres y mujeres.')
        if len({c['name'] for c in cats}) != len(cats): raise ValidationError('Nombres de categoría únicos.')
        for sex in ['M','F']:
            previous = 0
            for c in sorted([c for c in cats if c['sex']==sex],key=lambda c:number(c['min'])):
                low = number(c['min']); high = number(c['max']) if c['max'] is not None else math.inf
                if low < previous or high <= low: raise ValidationError('Categorías solapadas o límites inválidos. El mínimo se incluye y el máximo se excluye.')
                c['min']=low; c['max']=None if high==math.inf else high
                if not c['name'].strip(): raise ValidationError('Cada categoría requiere nombre.')
                previous = high
        rules['bar']=number(rules.get('bar',0)); rules['rounding']=number(rules.get('rounding',0))
        if rules.get('round_mode','none') not in ['none','nearest','down','up']: raise ValidationError('Redondeo inválido.')
    except (KeyError,TypeError,AttributeError): raise ValidationError('Configuración incompleta.')
    return rules

def score(value, test):
    value = number(value)
    if test.get('base') is None or test.get('elite') is None: raise ValidationError('Configura los benchmarks antes de capturar.')
    return round(max(0,min(100,50+50*(value-test['base'])/(test['elite']-test['base']))),6)

def category(rules, sex, weight):
    weight = number(weight,0.01)
    for c in rules['categories']:
        if c['sex']==sex and c['min'] <= weight and (c['max'] is None or weight < c['max']): return c['name']
    raise ValidationError('El peso no corresponde a una categoría. Revisa los rangos del evento.')

def suggested_load(event, weight):
    if weight is None: return None
    value = weight*.75
    step, mode, bar = event.rules.get('rounding',0),event.rules.get('round_mode','none'),event.rules.get('bar',0)
    if step and mode != 'none':
        fn = {'nearest':lambda x: math.floor(x+.5),'down':math.floor,'up':math.ceil}[mode]
        value = bar + fn(max(0,value-bar)/step)*step
        value = max(bar,value)
    return round(value,3)

def audit(event,actor,action,details):
    Audit.objects.create(event=event,actor=actor,action=action,details=details)

def board(event):
    if event.status == 'closed': return event.final_board
    rows=[]
    for r in Registration.objects.filter(event=event,state='confirmed').order_by('bib').prefetch_related('result_set'):
        marks = {m.test:m for m in r.result_set.all()}
        done = [m for m in marks.values() if m.status=='done']
        capacities = {c:round(sum((marks[i].points or 0) for i,t in enumerate(event.rules['tests']) if t['capacity']==c and i in marks)/2,2) for c in CAPACITIES}
        details = [{'test':t['name'],'unit':t['unit'],'capacity':t['capacity'],'value':marks[i].value if i in marks else None,'points':marks[i].points if i in marks else None,'status':marks[i].status if i in marks else 'pending','load':marks[i].load if i in marks else None} for i,t in enumerate(event.rules['tests'])]
        rows.append({'id':r.id,'user_id':r.user_id,'name':r.name,'bib':r.bib,'category':r.category or 'Sin pesaje','batch':r.batch,'attendance':r.attendance,'total':round(sum(m.points for m in done)/8,4),'completed':len(done),'capacities':capacities,'marks':details,'rank':None})
    rows.sort(key=lambda r:(-r['total'],r['bib']))
    for row in rows:
        if row['category']!='Sin pesaje' and row['completed']:
            row['rank']=1+sum(other['category']==row['category'] and other['completed']>0 and other['total']>row['total'] for other in rows)
    return rows

@transaction.atomic
def configure(event_id, actor, data):
    e=Event.objects.select_for_update().get(pk=event_id)
    if Registration.objects.filter(event=e).exists() or e.status!='draft': raise ValidationError('Las reglas se bloquean al publicar o inscribir. Crea otro evento para nuevas reglas.')
    validate_rules(data['rules'],False)
    e.name=data['name']; e.location=data['location']; e.rules=data['rules']; e.capacity=data['capacity']; e.price=data['price']; e.date=data['date']; e.registration_end=data['registration_end']; e.demo=data['demo']; e.description=data.get('description',''); e.allow_onsite=data.get('allow_onsite',False)
    e.version+=1; e.full_clean(); e.save()
    audit(e,actor,'configuration',{'version':e.version,'rules':e.rules})
    return e

@transaction.atomic
def change_phase(event_id, actor, phase, test=0,batch=1):
    e=Event.objects.select_for_update().get(pk=event_id)
    allowed={'draft':['open'],'open':['live'],'live':['live','closed'],'closed':[]}
    if phase not in allowed[e.status]: raise ValidationError('Transición de evento no permitida.')
    validate_rules(e.rules)
    if phase=='live':
        if not 0<=test<8 or batch<1: raise ValidationError('Prueba o lote inválido.')
        e.active_test=test; e.active_batch=batch
    if phase=='closed':
        if Registration.objects.filter(event=e,state='reserved').exists(): raise ValidationError('Resuelve las reservas de pago antes de cerrar.')
        e.final_board=board(e); e.closed_at=timezone.now()
    e.status=phase; e.save(); audit(e,actor,'phase',{'phase':phase,'test':test,'batch':batch})

def reserve_locked(e,user, onsite=False):
    if not hasattr(user,'profile'): raise ValidationError('Completa tu perfil antes de inscribirte.')
    regular=e.status=='open' and timezone.now()<=e.registration_end
    if not regular and not (onsite and e.status=='live' and e.allow_onsite): raise ValidationError('Las inscripciones están cerradas.')
    r=Registration.objects.filter(event=e,user=user).first()
    if r and r.state in ['confirmed','reserved']: return r
    if Registration.objects.filter(event=e,state__in=['reserved','confirmed']).count()>=e.capacity: raise ValidationError('Cupo agotado.')
    if not r:
        bib=(Registration.objects.filter(event=e).aggregate(m=Max('bib'))['m'] or 0)+1
        r=Registration.objects.create(event=e,user=user,name=user.first_name or user.username,sex=user.profile.sex,bib=bib,amount=e.price)
    else:
        r.state='reserved'; r.amount=e.price; r.save()
    return r

@transaction.atomic
def cash_register(event_id,user,actor,amount):
    e=Event.objects.select_for_update().get(pk=event_id)
    r=reserve_locked(e,user,onsite=True)
    if r.state=='confirmed': raise ValidationError('La inscripción ya está confirmada. No se registró otro cobro.')
    if Payment.objects.filter(registration=r,state__in=['creating','pending']).exists(): raise ValidationError('Hay un Checkout activo. Expíralo y concilia antes de cobrar efectivo.')
    if int(amount)!=e.price: raise ValidationError('El monto debe coincidir con el precio del evento, en centavos.')
    r.state='confirmed'; r.method='cash'; r.paid_by=actor; r.paid_at=timezone.now(); r.save()
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

def checkout(event_id,user):
    live=payment_mode()
    with transaction.atomic():
        e=Event.objects.select_for_update().get(pk=event_id)
        if live and e.demo: raise ValidationError('Los eventos de demostración no aceptan cobros reales.')
        r=reserve_locked(e,user)
        if r.state=='confirmed': raise ValidationError('Ya estás inscrito.')
        p=Payment.objects.filter(registration=r,state__in=['creating','pending']).first()
        if p and p.livemode!=live: raise ValidationError('Hay una reserva en otro modo de pago. Resuélvela antes de continuar.')
        if p and p.url: return p.url
        if not p: p=Payment.objects.create(registration=r,key=str(uuid.uuid4()),amount=e.price,expires_at=timezone.now()+timedelta(minutes=40),livemode=live)
    # Stable request and key survive a lost response; a timeout never releases inventory.
    s=stripe.checkout.Session.create(api_key=settings.STRIPE_SECRET_KEY,idempotency_key=p.key,mode='payment',payment_method_types=['card'],client_reference_id=str(r.id),metadata={'payment_id':str(p.id)},line_items=[{'price_data':{'currency':'mxn','unit_amount':p.amount,'product_data':{'name':e.name}},'quantity':1}],expires_at=int(p.expires_at.timestamp()),success_url=settings.PUBLIC_URL+'/profile/?payment=returned',cancel_url=settings.PUBLIC_URL+f'/events/{e.id}/?payment=cancelled')
    with transaction.atomic():
        p=Payment.objects.select_for_update().get(pk=p.id)
        p.session_id=s.id; p.url=s.url
        if p.state=='creating': p.state='pending'
        p.save()
    return s.url

@transaction.atomic
def fulfill(payload):
    if Webhook.objects.filter(stripe_id=payload['id']).exists(): return
    kind=payload['type']; s=payload['data']['object']
    if kind not in ['checkout.session.completed','checkout.session.expired','checkout.session.async_payment_succeeded']: return
    p=Payment.objects.select_for_update().get(pk=s['metadata']['payment_id'])
    r=Registration.objects.select_for_update().get(pk=p.registration_id)
    Event.objects.select_for_update().get(pk=r.event_id)
    if bool(s.get('livemode',False))!=p.livemode or (p.session_id and p.session_id!=s['id']) or s.get('client_reference_id')!=str(r.id): raise ValidationError('Identidad de pago inválida.')
    if kind=='checkout.session.expired':
        if p.state!='paid':
            p.state='expired'
            # A late duplicate expiration belongs to this payment, not a newer reservation.
            if r.state=='reserved' and not Payment.objects.filter(registration=r,state__in=['creating','pending','paid']).exclude(pk=p.id).exists(): r.state='expired'
    elif s.get('payment_status')=='paid':
        if s.get('amount_total')!=p.amount or s.get('currency')!='mxn': raise ValidationError('Monto o moneda no coincide.')
        if p.state=='expired': raise ValidationError('Pago de reserva expirada: requiere conciliación.')
        p.state='paid'; r.state='confirmed'; r.method='stripe'; r.paid_at=r.paid_at or timezone.now()
    p.session_id=s['id']; p.save(); r.save()
    Webhook.objects.create(stripe_id=payload['id'])
    audit(r.event,None,'stripe',{'payment':p.id,'state':p.state,'stripe_event':payload['id']})

@transaction.atomic
def check_in(reg_id,actor,weight,batch,attendance,reason='',revision=None):
    r=Registration.objects.select_for_update().select_related('event').get(pk=reg_id)
    e=Event.objects.select_for_update().get(pk=r.event_id)
    if e.status=='closed' or r.state!='confirmed': raise ValidationError('La inscripción debe estar pagada y el evento abierto.')
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
def capture(reg_id,actor,test,value,load,status,revision,reason,administrative=False):
    r=Registration.objects.select_for_update().select_related('event').get(pk=reg_id)
    e=Event.objects.select_for_update().get(pk=r.event_id)
    correction=administrative and actor.is_superuser and reason.strip()
    if not 0<=test<8: raise ValidationError('Prueba inválida.')
    if e.status!='live' or (not correction and (test!=e.active_test or r.batch!=e.active_batch)): raise ValidationError('La prueba o el lote activo cambió. Actualiza la pantalla.')
    if r.state!='confirmed' or (r.attendance!='present' and not correction): raise ValidationError('El atleta debe tener recepción confirmada y estar presente.')
    if status not in ['done','absent','withdrawn','pending']: raise ValidationError('Estado inválido.')
    existing=Result.objects.filter(registration=r,test=test).first()
    if administrative and (not correction or not existing): raise ValidationError('La corrección administrativa requiere una marca existente y un motivo.')
    if (existing.revision if existing else 0)!=revision: raise ValidationError('Otra persona guardó esta marca. Recarga antes de corregir.')
    if existing and not reason.strip(): raise ValidationError('Escribe el motivo de la corrección.')
    before={'value':existing.value,'points':existing.points,'load':existing.load,'status':existing.status,'revision':existing.revision} if existing else None
    t=e.rules['tests'][test]
    v=number(value) if status=='done' else None
    if status=='done' and t['unit']=='reps' and not v.is_integer(): raise ValidationError('Las repeticiones deben ser enteras.')
    if status=='done' and not t['higher'] and v<=0: raise ValidationError('El tiempo debe ser mayor a cero.')
    kg=number(load,.01) if status=='done' and t['capacity']=='Fuerza' else None
    mark=existing or Result(registration=r,test=test,revision=0)
    mark.value=v; mark.load=kg; mark.points=score(v,t) if v is not None else None; mark.status=status; mark.revision+=1; mark.save()
    audit(e,actor,'correction' if existing else 'capture',{'registration':r.id,'test':test,'before':before,'after':{'value':v,'load':kg,'points':mark.points,'status':status,'revision':mark.revision},'reason':reason})
    return mark

def cancel_checkout(reg_id,actor):
    r=Registration.objects.get(pk=reg_id)
    if r.user_id!=actor.id and not actor.is_superuser: raise ValidationError('No puedes modificar esta inscripción.')
    if r.state!='reserved': raise ValidationError('Esta inscripción no tiene un pago pendiente.')
    live=payment_mode()
    p=Payment.objects.filter(registration=r,state__in=['creating','pending']).first()
    if not p or not p.session_id: raise ValidationError('La creación aún no está confirmada. Reintenta el pago o solicita conciliación en recepción.')
    if p.livemode!=live: raise ValidationError('La reserva pertenece a otro modo Stripe.')
    s=stripe.checkout.Session.expire(p.session_id,api_key=settings.STRIPE_SECRET_KEY)
    if s.status!='expired': raise ValidationError('Stripe todavía no confirmó la cancelación. No se ha liberado el lugar.')
    fulfill({'id':f'cancel:{s.id}','type':'checkout.session.expired','data':{'object':s}})
    audit(r.event,actor,'checkout_cancelled',{'registration':r.id,'payment':p.id})
