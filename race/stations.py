"""Independent capture windows and one current station per coach/event."""
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Event,EventStation,CoachAssignment,Audit,Result


def ensure_stations(event):
    obsolete=event.stations.filter(test__gte=len(event.rules.get('tests',[])))
    CoachAssignment.objects.filter(station__in=obsolete).update(station=None,revision=F("revision")+1)
    obsolete.delete()
    existing=set(event.stations.values_list('test',flat=True))
    for index in range(len(event.rules.get('tests',[]))):
        if index not in existing:
            EventStation.objects.get_or_create(event=event,test=index,defaults={'is_open':event.status=='live' and index==event.active_test and not event.station_capture_closed,'opened':event.status=='closed' or (event.status=='live' and index<=event.active_test)})


def assignment(event,coach):
    return CoachAssignment.objects.filter(event=event,coach=coach,station__isnull=False).select_related('station').first()


@transaction.atomic
def switch_station(event_id,actor,test,opened,revision):
    from .services import station_pending
    event=Event.objects.select_for_update().get(pk=event_id)
    if not actor.is_active or not actor.is_superuser:raise ValidationError('Solo administración puede abrir o cerrar estaciones.')
    if event.status not in ['open','live']:raise ValidationError('Publica el evento antes de abrir las estaciones.')
    station=event.stations.filter(test=test).first()
    if station is None:raise ValidationError('Estación inválida.')
    if station.revision!=revision:raise ValidationError('Otra pantalla cambió esta estación. Actualiza e intenta de nuevo.')
    if opened and event.status=='open':
        from .services import validate_rules,validate_policies
        validate_rules(event.rules);validate_policies(event.rules,event)
        event.status='live';event.save(update_fields=['status'])
    station.is_open=opened;station.opened=station.opened or opened;station.revision+=1
    station.save()
    if test==event.active_test:
        event.station_capture_closed=not opened
        event.save(update_fields=["station_capture_closed"])
    Audit.objects.create(event=event,actor=actor,action='station_opened' if opened else 'station_closed',details={'test':test,'pending':station_pending(event,test).count(),'revision':station.revision})
    return station


@transaction.atomic
def assign_coach(event_id,actor,coach_id,test,revision):
    event=Event.objects.select_for_update().get(pk=event_id)
    if not actor.is_active or not actor.is_superuser:raise ValidationError('Solo administración puede asignar coaches.')
    if event.status=='closed':raise ValidationError('El evento está cerrado.')
    coach=User.objects.filter(pk=coach_id,is_active=True,is_superuser=False,groups__name='Coach').first()
    if not coach:raise ValidationError('Selecciona un coach activo.')
    station=event.stations.filter(test=test).first() if test is not None else None
    if test is not None and station is None:raise ValidationError('Estación inválida.')
    current=CoachAssignment.objects.filter(event=event,coach=coach).first()
    if (current.revision if current else 0)!=revision:raise ValidationError('La asignación cambió. Actualiza antes de continuar.')
    previous=current.station.test if current and current.station else None
    current,_=CoachAssignment.objects.update_or_create(event=event,coach=coach,defaults={'station':station,'revision':revision+1})
    Audit.objects.create(event=event,actor=actor,action='coach_assignment',details={'coach':coach.pk,'before':previous,'test':test,'revision':current.revision})
    return current


def station_rows(event):
    from .services import station_pending
    rows=[]
    for station in event.stations.order_by('test').prefetch_related('assignments__coach'):
        if station.test>=len(event.rules.get('tests',[])):continue
        pending=station_pending(event,station.test)
        station.name=event.rules['tests'][station.test]['name']
        station.pending=pending.count()
        station.done=Result.objects.filter(registration__event=event,registration__state='confirmed',test=station.test,status='done').count()
        station.label='Abierta' if station.is_open else 'Sin abrir' if not station.opened else 'Pausada' if station.pending else 'Cerrada'
        rows.append(station)
    return rows
