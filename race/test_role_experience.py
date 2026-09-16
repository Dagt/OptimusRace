from django.test import TestCase
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event,Profile,Registration,Exercise
from .services import reserve_locked

class RoleExperienceTests(TestCase):
    def test_staff_account_has_no_sports_profile_or_enrollment(self):
        event=Event.objects.create(name='Evento',date=timezone.now(),registration_end=timezone.now(),status='open',rules={'tests':[],'categories':[]},capacity=10)
        for role in ['admin','coach']:
            user=User.objects.create_user(role,email=role+'@example.test',is_superuser=role=='admin')
            if role=='coach':user.groups.add(Group.objects.get_or_create(name='Coach')[0])
            self.client.force_login(user)
            response=self.client.get('/profile/')
            self.assertContains(response,'Datos de acceso')
            for text in ['DORSAL','PESO EVENTO','TU TRAYECTORIA','Mi rendimiento']:self.assertNotContains(response,text)
            self.assertFalse(Profile.objects.filter(user=user).exists())
            response=self.client.get(f'/events/{event.pk}/')
            self.assertNotContains(response,'Inscribirme')
            Profile.objects.create(user=user,sex='M')
            with self.assertRaises(ValidationError):reserve_locked(event,user)
            self.assertEqual(Registration.objects.count(),0)
    def test_catalog_guides_measurement_and_scoring(self):
        user=User.objects.create_superuser('admin','admin@example.test','test-password')
        self.client.force_login(user)
        response=self.client.get('/catalog/new/')
        self.assertContains(response,'¿Qué va a registrar el coach?')
        self.assertContains(response,'Límites de captura')
        self.assertContains(response,'DE LA MARCA A LOS PUNTOS')
        self.assertEqual(Exercise.objects.count(),0)
