"""Separate, catalog-backed first-place playoffs; never write normal Results."""
import math
from copy import deepcopy
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Event, Exercise, Registration, TieBreak, TieBreakRound, TieBreakMark, Audit
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


def rounds_for(event):
    from .services import board
    current = {g['category']:g['fingerprint'] for g in tie_groups(board(event))}
    rounds = list(TieBreakRound.objects.filter(event=event).prefetch_related('marks').order_by('-pk'))
    for rnd in rounds:
        rnd.stale = current.get(rnd.category) != rnd.fingerprint
        marks = {m.registration_id:m for m in rnd.marks.all()}
        rnd.rows = [{'entry':r,'mark':marks.get(r.pk),'load':load_for(rnd.test,r.weight)} for r in Registration.objects.filter(pk__in=rnd.contenders).select_related('participant').order_by('bib')]
        rnd.complete = len(marks) == len(rnd.contenders)
        rnd.requires_load = needs_load(rnd.test)
    return rounds
