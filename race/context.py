from .models import Event

def navigation(request):
    user = request.user
    role = 'visitor'
    if user.is_authenticated:
        role = 'admin' if user.is_superuser else 'coach' if user.groups.filter(name='Coach').exists() else 'athlete'
    active = Event.objects.filter(status='live').order_by('-date').first() if role in ['admin','coach'] else None
    return {'role':role, 'role_name':{'admin':'Administración','coach':'Coach','athlete':'Atleta','visitor':'Visitante'}[role], 'active_event':active}


def site_brand(request):
    from django.conf import settings
    from django.templatetags.static import static
    return {
        'brand_share_image': settings.PUBLIC_URL + static('images/brand/share.png'),
        'brand_page_url': settings.PUBLIC_URL + request.path,
    }
