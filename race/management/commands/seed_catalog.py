from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from race.catalog import seed_catalog

class Command(BaseCommand):
    help='Instala catálogo técnico y grupo Coach, sin usuarios ni eventos.'
    def handle(self,*args,**options):
        seed_catalog()
        Group.objects.get_or_create(name='Coach')
        self.stdout.write('Catálogo y grupo Coach preparados. No se crean datos operativos.')
