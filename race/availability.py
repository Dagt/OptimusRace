from django.db import transaction
from django.db.models import Count
from django.core.exceptions import ValidationError
from .models import Event,Registration,Audit
from .event_policy import registration_open

def availability(event):
    confirmed=Registration.objects.filter(event=event,state='confirmed').count()
    return {'capacity':event.capacity,'confirmed':confirmed,'occupied':confirmed,
            'remaining':max(0,event.capacity-confirmed),'full':confirmed>=event.capacity,
            'registration_open':registration_open(event,onsite=True),'status':event.status,'date':event.date.isoformat()}

@transaction.atomic
def set_capacity(event_id,actor,capacity,reason):
    event=Event.objects.select_for_update().get(pk=event_id)
    if not actor.is_superuser:raise ValidationError('Solo el administrador puede modificar el cupo.')
    if event.status=='closed':raise ValidationError('El evento cerrado conserva su cupo.')
    if not isinstance(capacity,int) or isinstance(capacity,bool) or not 1<=capacity<=1000000:raise ValidationError('El cupo debe ser un entero entre 1 y 1,000,000.')
    occupied=availability(event)['occupied']
    if capacity<occupied:raise ValidationError(f'El cupo no puede ser menor a los {occupied} lugares ocupados por inscripciones confirmadas.')
    if not reason.strip():raise ValidationError('Escribe el motivo del ajuste de cupo.')
    previous=event.capacity;event.capacity=capacity;event.save(update_fields=['capacity'])
    Audit.objects.create(event=event,actor=actor,action='capacity_changed',details={'before':previous,'after':capacity,'occupied':occupied,'reason':reason})
    return event
