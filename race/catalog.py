def seed_catalog():
    """Backward-compatible bootstrap: never create exercises automatically."""
    from django.contrib.auth.models import Group
    Group.objects.get_or_create(name='Coach')
