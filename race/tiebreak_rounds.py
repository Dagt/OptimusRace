"""Separate, catalog-backed first-place playoffs; never write normal Results."""
import math
from itertools import combinations
from copy import deepcopy
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Event, Exercise, Registration, TieBreak, TieBreakRound, TieBreakMark, TieBreakMatch, Audit
from .relative_scoring import tie_groups
from .exercise_parameters import validate_parameters, validate_mark, load_for, needs_load
from .time_marks import supports_time_input, time_seconds


def current_group(event, category, fingerprint):
    from .services import board
    group = next((g for g in tie_groups(board(event)) if g['category'] == category and g['fingerprint'] == fingerprint), None)
    if event.status != 'live' or not group or not any(r.get('tie_pending') for r in group['members']):
        raise ValidationError('Este empate cambió o ya fue resuelto. Actualiza la página.')
    return group


def require_coach(actor):
    if not actor.is_active or actor.is_superuser or not actor.groups.filter(name='Coach').exists():
        raise ValidationError('Solo los coaches pueden capturar y finalizar la prueba de desempate.')


@transaction.atomic
def start_round(event_id, actor, category, fingerprint, exercise_id):
    if not actor.is_active or not actor.is_superuser:
        raise ValidationError('Solo administración puede elegir la prueba de desempate.')
    event = Event.objects.select_for_update().get(pk=event_id)
    group = current_group(event, category, fingerprint)
    previous = TieBreakRound.objects.filter(event=event, category=category, fingerprint=fingerprint).order_by('-pk').first()
    if previous and previous.status == 'open':
        raise ValidationError('Ya hay una prueba de desempate abierta para esta categoría.')
    exercise = Exercise.objects.filter(pk=exercise_id).first()
    if not exercise:
        raise ValidationError('Selecciona una prueba del catálogo.')
    validate_parameters(exercise.parameters)
    test = {key: deepcopy(getattr(exercise, key)) for key in ['name', 'unit', 'capacity', 'parameters', 'higher']}
    contenders = previous.finalists if previous and previous.status == 'tied' else [r['id'] for r in group['members']]
    rnd = TieBreakRound.objects.create(event=event, category=category, total=group['total'], fingerprint=fingerprint,
        exercise=exercise, test=test, contenders=contenders, actor=actor)
    if test['parameters'].get('metric')=='duel':
        TieBreakMatch.objects.bulk_create([TieBreakMatch(round=rnd,first_id=a,second_id=b) for a,b in combinations(contenders,2)])
    Audit.objects.create(event=event, actor=actor, action='tiebreak_round_started', details={'round':rnd.pk, 'test':test, 'contenders':contenders})
    return rnd


@transaction.atomic
def save_mark(round_id, actor, registration_id, value, load=None, revision=0):
    require_coach(actor)
    initial = TieBreakRound.objects.get(pk=round_id)
    event = Event.objects.select_for_update().get(pk=initial.event_id)
    rnd = TieBreakRound.objects.select_for_update().get(pk=round_id)
    current_group(event, rnd.category, rnd.fingerprint)
    if rnd.status != 'open':
        raise ValidationError('La ronda está cerrada.')
    if rnd.test['parameters'].get('metric')=='duel':
        raise ValidationError('Registra cada victoria en el marcador del enfrentamiento.')
    if registration_id not in rnd.contenders:
        raise ValidationError('El participante no pertenece a este desempate.')
    registration = Registration.objects.get(pk=registration_id, event=event, state='confirmed')
    old = rnd.marks.filter(registration=registration).first()
    if revision != (old.revision if old else 0):
        raise ValidationError('Otro coach actualizó esta marca. Recarga antes de corregirla.')
    try:
        number = time_seconds(value, rnd.test['parameters'].get('time_entry', 'seconds')) if supports_time_input(rnd.test) else float(str(value).replace(',', '.'))
        if not math.isfinite(number) or number < 0 or number > 1e12:
            raise ValueError()
        validate_mark(number, rnd.test)
        used_load = float(str(load).replace(',', '.')) if needs_load(rnd.test) else None
        expected = load_for(rnd.test, registration.weight)
        if used_load is not None and (not math.isfinite(used_load) or expected is None or abs(used_load-expected) > .01):
            raise ValidationError('La carga debe coincidir con la regla de la prueba y el peso registrado.')
    except (TypeError, ValueError):
        raise ValidationError('Introduce una marca y una carga válidas.')
    mark, _ = TieBreakMark.objects.update_or_create(round=rnd, registration=registration,
        defaults={'value':number, 'load':used_load, 'actor':actor, 'revision':revision+1})
    Audit.objects.create(event=event, actor=actor, action='tiebreak_mark', details={'round':rnd.pk,'registration':registration_id,'value':number,'load':used_load,'revision':mark.revision})
    return mark


@transaction.atomic
def finish_round(round_id, actor):
    require_coach(actor)
    initial = TieBreakRound.objects.get(pk=round_id)
    event = Event.objects.select_for_update().get(pk=initial.event_id)
    rnd = TieBreakRound.objects.select_for_update().get(pk=round_id)
    group = current_group(event, rnd.category, rnd.fingerprint)
    if rnd.status != 'open':
        raise ValidationError('Esta ronda ya está cerrada.')
    if rnd.test['parameters'].get('metric')=='duel':
        matches=list(rnd.matches.all())
        wins={key:0 for key in rnd.contenders}
        if len(matches)!=len(rnd.contenders)*(len(rnd.contenders)-1)//2 or not matches:
            raise ValidationError('Los enfrentamientos están incompletos.')
        for match in matches:
            winner=match_winner(match,rnd.test['parameters']['wins_required'])
            if winner is None:raise ValidationError('Termina todos los enfrentamientos antes de finalizar.')
            wins[winner]+=1
        for registration_id,value in wins.items():
            TieBreakMark.objects.create(round=rnd,registration_id=registration_id,value=value,actor=actor)
    marks = list(rnd.marks.all())
    if {m.registration_id for m in marks} != set(rnd.contenders):
        raise ValidationError('Faltan marcas de participantes en esta ronda.')
    best = (max if rnd.test['higher'] else min)(m.value for m in marks)
    rnd.finalists = [m.registration_id for m in marks if m.value == best]
    if len(rnd.finalists) > 1:
        rnd.status = 'tied'
    else:
        winner = rnd.finalists[0]
        order = [winner] + [r['id'] for r in group['members'] if r['id'] != winner]
        rnd.decision = TieBreak.objects.create(event=event, category=rnd.category, total=rnd.total,
            fingerprint=rnd.fingerprint, order=order, winner_only=True, challenge=rnd.test['name'],
            details=f'Ronda {rnd.pk}; ganador inscripción {winner}; marca {best} {rnd.test["unit"]}.',
            judge=actor.get_full_name() or actor.username, actor=actor)
        rnd.status = 'resolved'
    rnd.save(update_fields=['status', 'finalists', 'decision'])
    Audit.objects.create(event=event, actor=actor, action='tiebreak_round_finished', details={'round':rnd.pk,'status':rnd.status,'finalists':rnd.finalists})
    return rnd


def rounds_for(event, standings=None):
    from .services import board
    if standings is None:standings=board(event)
    current = {g['category']:g['fingerprint'] for g in tie_groups(standings)}
    frozen_decisions={r.get('tiebreak',{}).get('decision_id') for r in standings} if event.status=='closed' else set()
    rounds = list(TieBreakRound.objects.filter(event=event).prefetch_related('marks','matches__first__participant','matches__second__participant').order_by('-pk'))
    for rnd in rounds:
        rnd.stale = current.get(rnd.category) != rnd.fingerprint and not (rnd.decision_id and rnd.decision_id in frozen_decisions)
        marks = {m.registration_id:m for m in rnd.marks.all()}
        rnd.rows = [{'entry':r,'mark':marks.get(r.pk),'load':load_for(rnd.test,r.weight)} for r in Registration.objects.filter(pk__in=rnd.contenders).select_related('participant').order_by('bib')]
        rnd.complete = len(marks) == len(rnd.contenders)
        rnd.requires_load = needs_load(rnd.test)
        rnd.duel = rnd.test['parameters'].get('metric')=='duel'
        rnd.editable = event.status=='live' and rnd.status=='open' and not rnd.stale
        rnd.label = 'Sin vigencia' if rnd.stale else {'open':'En captura','tied':'Nueva prueba necesaria','resolved':'Resuelto'}.get(rnd.status,rnd.status)
        rnd.unit = 'min.seg' if rnd.test['parameters'].get('time_entry')=='minutes_seconds_dot' else rnd.test['unit']
        rnd.match_rows = list(rnd.matches.all())
        for match in rnd.match_rows:
            match.first_score=match.games.count(match.first_id)
            match.second_score=match.games.count(match.second_id)
            match.winner_id=match_winner(match,rnd.test['parameters'].get('wins_required',1))
            match.game_rows=[{'number':i+1,'winner':match.first if key==match.first_id else match.second} for i,key in enumerate(match.games)]
        if rnd.duel:rnd.complete=bool(rnd.match_rows) and all(m.winner_id for m in rnd.match_rows)
        rnd.winner=next((r['entry'] for r in rnd.rows if r['entry'].pk in rnd.finalists),None) if rnd.status=='resolved' else None
    return rounds


def match_winner(match, required):
    for key in [match.first_id,match.second_id]:
        if match.games.count(key)>=required:return key
    return None


@transaction.atomic
def record_victory(round_id,actor,match_id,revision,winner_id):
    require_coach(actor)
    initial=TieBreakRound.objects.get(pk=round_id)
    event=Event.objects.select_for_update().get(pk=initial.event_id)
    rnd=TieBreakRound.objects.select_for_update().get(pk=round_id)
    current_group(event,rnd.category,rnd.fingerprint)
    if rnd.status!='open' or rnd.test['parameters'].get('metric')!='duel':
        raise ValidationError('Este enfrentamiento no admite capturas.')
    match=rnd.matches.filter(pk=match_id).first()
    if not match:raise ValidationError('El enfrentamiento no pertenece a esta ronda.')
    if revision!=match.revision:raise ValidationError('Otro coach actualizó el marcador. Recarga antes de continuar.')
    before=list(match.games)
    if winner_id is None:
        if not match.games:raise ValidationError('No hay victorias que corregir.')
        match.games=match.games[:-1]
    else:
        if winner_id not in [match.first_id,match.second_id]:raise ValidationError('Selecciona uno de los dos competidores.')
        if match_winner(match,rnd.test['parameters']['wins_required']):raise ValidationError('El enfrentamiento ya tiene ganador.')
        match.games=[*match.games,winner_id]
    match.revision+=1;match.actor=actor
    match.save(update_fields=['games','revision','actor','updated_at'])
    Audit.objects.create(event=event,actor=actor,action='tiebreak_victory',details={'round':rnd.pk,'match':match.pk,'before':before,'after':match.games,'revision':match.revision})
    return match


def broadcast_playoffs(event, standings):
    """Public broadcast cards contain sporting results only, never account data."""
    from .templatetags.race_labels import capture_value
    by_id={r['id']:r for r in standings}
    rounds=rounds_for(event,standings)
    cards=[]
    def person(key,value=None):
        row=by_id[key]
        return {field:row.get(field) for field in ['id','name','bib','photo_url']} | {'value':value}
    for group in tie_groups(standings):
        rnd=next((r for r in rounds if r.category==group['category'] and not r.stale),None)
        common={'category':group['category'],'total':group['total'],'status':rnd.status if rnd else 'pending',
                'test':rnd.test['name'] if rnd else 'Empate por el primer lugar','winner':rnd.winner.pk if rnd and rnd.winner else None}
        if rnd and rnd.duel:
            for match in rnd.match_rows:
                cards.append({**common,'key':f'match-{match.pk}','unit':'victorias','target':rnd.test['parameters']['wins_required'],
                    'match_winner':match.winner_id,'players':[person(match.first_id,match.first_score),person(match.second_id,match.second_score)]})
        else:
            members=[r['id'] for r in group['members']] if not rnd else rnd.contenders
            marks={r['entry'].pk:r['mark'] for r in rnd.rows} if rnd else {}
            for offset in range(0,len(members),2):
                cards.append({**common,'key':f"category-{group['category']}-{offset}",'unit':rnd.unit if rnd else 'pts generales','target':None,
                    'players':[person(key,capture_value(marks[key].value,rnd.test) if marks.get(key) else None) for key in members[offset:offset+2]]})
    return cards
