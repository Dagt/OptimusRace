from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from race.catalog import seed_catalog

class Command(BaseCommand):
    help='Prepara el grupo Coach; deja el catálogo vacío.'
    def handle(self,*args,**options):
        seed_catalog()
        Group.objects.get_or_create(name='Coach')
        self.stdout.write('Grupo Coach preparado. No se crean pruebas ni datos operativos.')
