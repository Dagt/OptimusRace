"""Configurable event policies. No event-specific data or templates."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.utils import timezone

def blank_rules():
    return {'schema_version':2,'category_bounds':'upper_inclusive','capacity_podiums':True,'tests':[],'categories':[],'bar':0,'rounding':0,'round_mode':'none',
            'minimum_age':0,'ordered_stations':False,'online_payments':False,'price_tiers':[],'discounts':[]}

def instant(value):
    try:
        result=datetime.fromisoformat(value)
        if timezone.is_naive(result):raise ValueError()
        return result
    except (ValueError,TypeError):raise ValidationError('Las fechas deben incluir hora y zona horaria.')

def in_period(item,at):
    return (not item.get('start') or at>=instant(item['start'])) and (not item.get('end') or at<instant(item['end']))

def cents(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=999999999 or int(value)!=value:
        raise ValidationError('El importe debe ser un número entero de centavos no negativo.')
    return int(value)

def validate_policies(rules,event=None):
    size=rules.get('group_size',10)
    if isinstance(size,bool) or not isinstance(size,int) or not 1<=size<=1000:
        raise ValidationError('El tamaño de grupo debe ser un entero entre 1 y 1000.')
    for key in ['minimum_age','maximum_age']:
        age=rules.get(key)
        if age is not None and (isinstance(age,bool) or not isinstance(age,int) or not 0<=age<=120):raise ValidationError('La edad debe ser un entero entre 0 y 120.')
    if rules.get('maximum_age') is not None and rules['maximum_age']<rules.get('minimum_age',0):raise ValidationError('La edad máxima debe ser mayor o igual que la mínima.')
    tiers=rules.get('price_tiers',[]);discounts=rules.get('discounts',[])
    if not isinstance(tiers,list) or not isinstance(discounts,list):raise ValidationError('Tarifas o descuentos inválidos.')
    for items in [tiers,discounts]:
        if len(items)>50:raise ValidationError('Máximo 50 tarifas o descuentos por evento.')
        for item in items:
            start=instant(item['start']) if item.get('start') else None
            end=instant(item['end']) if item.get('end') else None
            if start and end and start>=end:raise ValidationError('Cada vigencia debe terminar después de comenzar.')
    intervals=[]
    for tier in tiers:
        if not tier.get('name','').strip() or not tier.get('start') or not tier.get('end'):raise ValidationError('Cada tarifa requiere nombre, inicio y fin.')
        cents(tier.get('amount'))
        intervals.append((instant(tier['start']),instant(tier['end'])))
    intervals.sort()
    if any(a[1]>b[0] for a,b in zip(intervals,intervals[1:])):raise ValidationError('Las vigencias de las tarifas no pueden solaparse.')
    codes=[]
    for discount in discounts:
        code=discount.get('code','').strip().upper()
        if not code or len(code)>40:raise ValidationError('Cada descuento necesita un código de hasta 40 caracteres.')
        discount['code']=code;codes.append(code)
        if discount.get('kind') not in ['percent','fixed']:raise ValidationError('Tipo de descuento inválido.')
        value=discount.get('value')
        if discount['kind']=='fixed':
            if cents(value)<=0:raise ValidationError('El descuento fijo debe ser positivo.')
        elif not isinstance(value,(int,float)) or not 0<value<=100:raise ValidationError('El descuento porcentual debe ser mayor que 0 y hasta 100.')
        limit=discount.get('limit')
        if limit is not None and (not isinstance(limit,int) or isinstance(limit,bool) or limit<1):raise ValidationError('El límite de usos debe ser un entero positivo.')
    if len(set(codes))!=len(codes):raise ValidationError('No repitas códigos de descuento.')
    for key in ['registration_start','reception_start','reception_end','event_end']:
        if rules.get(key):instant(rules[key])
    if rules.get('reception_start') and rules.get('reception_end') and instant(rules['reception_start'])>=instant(rules['reception_end']):raise ValidationError('El cierre de recepción debe ser posterior a la apertura.')
    if event:
        if rules.get('registration_start') and instant(rules['registration_start'])>=event.registration_end:raise ValidationError('El inicio de inscripciones debe ser anterior al cierre.')
        if event.registration_end>event.date:raise ValidationError('El cierre de inscripciones no puede ser posterior al inicio del evento.')
        if rules.get('event_end') and instant(rules['event_end'])<=event.date:raise ValidationError('El evento debe terminar después de comenzar.')
        for start,end in intervals:
            if end>event.registration_end:raise ValidationError('Las tarifas por fecha deben terminar a más tardar al cerrar inscripciones.')

def current_price(event,at=None):
    at=at or timezone.now()
    return next((t['amount'] for t in event.rules.get('price_tiers',[]) if in_period(t,at)),event.price)

def quote_price(event,code='',at=None,exclude_registration=None):
    from .models import Registration
    at=at or timezone.now();base=current_price(event,at);code=code.strip().upper()
    snapshot={'base_amount':base,'amount':base,'discount_code':'','discount_amount':0,'quoted_at':at.isoformat()}
    if not code:return snapshot
    discount=next((d for d in event.rules.get('discounts',[]) if d['code']==code),None)
    if not discount or not in_period(discount,at):raise ValidationError('El código de descuento no existe o está fuera de vigencia.')
    uses=Registration.objects.filter(event=event,pricing_code=code,state__in=['reserved','confirmed'])
    if exclude_registration:uses=uses.exclude(pk=exclude_registration)
    if discount.get('limit') and uses.count()>=discount['limit']:raise ValidationError('El descuento agotó sus usos disponibles.')
    reduction=Decimal(base)*Decimal(str(discount['value']))/100 if discount['kind']=='percent' else Decimal(discount['value'])
    reduction=min(base,int(reduction.quantize(Decimal('1'),rounding=ROUND_HALF_UP)))
    return {**snapshot,'amount':base-reduction,'discount_code':code,'discount_amount':reduction}

def registration_open(event,at=None,onsite=False):
    at=at or timezone.now()
    start=event.rules.get('registration_start')
    if start and at<instant(start):return False
    if event.rules.get('event_end') and at>=instant(event.rules['event_end']):return False
    return (event.status=='open' and at<=event.registration_end) or (
        onsite and event.status in ['open','live'] and event.allow_onsite
        and (event.status=='live' or at>=event.date))

def registration_message(event,at=None):
    at=at or timezone.now()
    if event.status=='draft':return 'Evento sin publicar'
    if event.status=='closed':return 'Evento cerrado'
    if registration_open(event,at,onsite=True):return 'Inscripciones abiertas'
    if event.rules.get('event_end') and at>=instant(event.rules['event_end']):return 'Finalizó el horario del evento'
    if event.rules.get('registration_start') and at<instant(event.rules['registration_start']):return 'Inscripciones aún no abiertas'
    return 'Inscripciones cerradas'

def validate_eligibility(event,birth_date):
    minimum=event.rules.get('minimum_age',0);maximum=event.rules.get('maximum_age')
    if not minimum and maximum is None:return
    if not birth_date:raise ValidationError('Completa la fecha de nacimiento del participante para comprobar la edad permitida.')
    day=timezone.localtime(event.date).date()
    age=day.year-birth_date.year-((day.month,day.day)<(birth_date.month,birth_date.day))
    if age<minimum or (maximum is not None and age>maximum):raise ValidationError(f'La edad al día del evento debe estar entre {minimum} y {maximum if maximum is not None else "sin límite máximo"} años.')
