"""Exercise execution parameters; independent of points and event prices."""
import math
from django.core.exceptions import ValidationError

def validate_parameters(p):
    if not isinstance(p,dict):raise ValidationError('Parámetros de ejercicio inválidos.')
    if p.get('metric','custom') not in ['time','repetitions','distance','weight','custom']:raise ValidationError('Tipo de resultado inválido.')
    if p.get('load_mode','none') not in ['none','fixed','body_percent']:raise ValidationError('Tipo de carga inválido.')
    for key in ['duration_seconds','distance_meters','laps','load_value','load_step','bar_weight','min_value','max_value','precision']:
        value=p.get(key)
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0):raise ValidationError(f'Valor inválido: {key}.')
    for key in ['duration_seconds','distance_meters','load_step']:
        if p.get(key) is not None and p[key]<=0:raise ValidationError('Duración, distancia e incrementos deben ser positivos cuando se especifican.')
    if p.get('laps') is not None and (p['laps']<1 or int(p['laps'])!=p['laps']):raise ValidationError('Los recorridos deben ser enteros positivos.')
    if p.get('precision') is not None and (int(p['precision'])!=p['precision'] or p['precision']>6):raise ValidationError('La precisión debe ser de 0 a 6 decimales.')
    if p.get('min_value') is not None and p.get('max_value') is not None and p['min_value']>=p['max_value']:raise ValidationError('El máximo válido debe superar al mínimo.')
    if p.get('load_mode','none')!='none' and not p.get('load_value'):raise ValidationError('Especifica el peso fijo o porcentaje de carga.')
    if p.get('round_mode','none') not in ['none','nearest','down','up']:raise ValidationError('Redondeo de carga inválido.')
    if p.get('round_mode','none')!='none' and not p.get('load_step'):raise ValidationError('El redondeo requiere un incremento de carga positivo.')
    return p

def load_for(test,weight):
    p=test.get('parameters',{});mode=p.get('load_mode','none')
    if mode=='none':return None
    if mode=='body_percent' and weight is None:return None
    value=p['load_value'] if mode=='fixed' else weight*p['load_value']/100
    step=p.get('load_step') or 0;bar=p.get('bar_weight') or 0;round_mode=p.get('round_mode','none')
    if step and round_mode!='none':
        fn={'nearest':lambda n:math.floor(n+.5),'down':math.floor,'up':math.ceil}[round_mode]
        value=max(bar,bar+fn(max(0,value-bar)/step)*step)
    return round(value,6)

def needs_load(test):
    return test.get('parameters',{}).get('load_mode','none')!='none' if 'parameters' in test else test['capacity']=='Fuerza'

def validate_mark(value,test):
    p=test.get('parameters',{})
    if p.get('metric')=='repetitions' or test['unit']=='reps':
        if not value.is_integer():raise ValidationError('Las repeticiones deben ser enteras.')
    if p.get('metric')=='time' and value<=0:raise ValidationError('El tiempo debe ser mayor a cero.')
    if p.get('min_value') is not None and value<p['min_value']:raise ValidationError('La marca es menor al mínimo permitido.')
    if p.get('max_value') is not None and value>p['max_value']:raise ValidationError('La marca supera el máximo permitido.')
    if p.get('precision') is not None and abs(value-round(value,p['precision']))>1e-8:raise ValidationError(f"La marca admite hasta {p['precision']} decimales.")
