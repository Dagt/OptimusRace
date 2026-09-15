from .models import Event

def navigation(request):
    user = request.user
    role = 'visitor'
    if user.is_authenticated:
        role = 'admin' if user.is_superuser else 'coach' if user.groups.filter(name='Coach').exists() else 'athlete'
    active = Event.objects.filter(status='live').order_by('-date').first() if role in ['admin','coach'] else None
    return {'role':role, 'role_name':{'admin':'Administración','coach':'Coach','athlete':'Atleta','visitor':'Visitante'}[role], 'active_event':active}
