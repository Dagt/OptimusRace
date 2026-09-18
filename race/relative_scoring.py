"""Relative scoring is derived from valid marks in the same event/category."""
import hashlib,json
from collections import defaultdict
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Event,TieBreak,Audit

def is_relative(event):
    return any(t.get('scoring')=='relative' for t in event.rules.get('tests',[]))

def relative_points(value,values,maximum,higher):
    if not values:return None
    low,high=min(values),max(values)
    if high==low:return round(maximum,6)
    fraction=(value-low)/(high-low) if higher else (high-value)/(high-low)
    return round(maximum*max(0,min(1,fraction)),6)

def category_fingerprint(rows):
    evidence=[{key:r.get(key) for key in ['id','category','attendance','total','marks']} for r in sorted(rows,key=lambda r:r['id'])]
    return hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def tie_groups(rows,scope="general"):
    categories=defaultdict(list);clusters=defaultdict(list)
    for r in rows:
        categories[r['category']].append(r)
        if r['rank'] is not None:clusters[(r['category'],r['total'])].append(r)
    groups=[]
    for (category,total),members in clusters.items():
        if len(members)<2 or min(r['rank'] for r in members)!=1:continue
        groups.append({'scope':scope,'category':category,'total':total,'members':members,'rank':min(r['rank'] for r in members),
                       'fingerprint':category_fingerprint(categories[category])})
    return groups

def apply_tiebreaks(event,rows,scope="general"):
    groups=tie_groups(rows,scope)
    decisions=list(TieBreak.objects.filter(event=event,scope=scope).order_by('-id'))
    for group in groups:
        ids={r['id'] for r in group['members']}
        decision=next((d for d in decisions if d.category==group['category'] and d.total==group['total'] and d.fingerprint==group['fingerprint'] and set(d.order)==ids and len(d.order)==len(ids)),None)
        for r in group['members']:
            r['tie_pending']=decision is None
            if decision:
                r['rank']=group['rank']+(min(1,decision.order.index(r['id'])) if decision.winner_only else decision.order.index(r['id']))
                r['tiebreak']={'challenge':decision.challenge,'judge':decision.judge,'place':r['rank'],'decision_id':decision.pk}
        group['resolved']=bool(decision)
    return groups

@transaction.atomic
def resolve_tie(event_id,actor,category,total,order,fingerprint,challenge,details,judge,scope="general"):
    from .services import board
    event=Event.objects.select_for_update().get(pk=event_id)
    if not actor.is_superuser or event.status!='live':raise ValidationError('El desempate requiere administrador y evento en competencia.')
    if not all(str(x).strip() for x in [challenge,details,judge]):raise ValidationError('Indica destreza, resultado y juez del desempate.')
    if len(challenge)>150 or len(judge)>150 or len(details)>3000:raise ValidationError('El texto del desempate supera el límite permitido.')
    rows=board(event)
    if scope!="general":raise ValidationError('Solo se desempata el primer lugar de la clasificación general de cada categoría.')
    group=next((g for g in tie_groups(rows) if g['category']==category and g['total']==total),None)
    if not group or group['fingerprint']!=fingerprint:raise ValidationError('Las marcas o la categoría cambiaron. Recarga y revisa el empate antes de resolverlo.')
    expected={r['id'] for r in group['members']}
    if len(order)!=len(expected) or set(order)!=expected:raise ValidationError('Asigna una posición distinta a cada participante empatado.')
    decision=TieBreak.objects.create(event=event,scope=scope,category=category,total=total,order=order,fingerprint=fingerprint,challenge=challenge.strip(),details=details.strip(),judge=judge.strip(),actor=actor)
    Audit.objects.create(event=event,actor=actor,action='tiebreak',details={'scope':scope,'decision':decision.pk,'category':category,'total':total,'order':order,'challenge':decision.challenge,'judge':decision.judge,'result':decision.details})
    return decision
