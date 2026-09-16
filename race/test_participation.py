from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from pathlib import Path
from PIL import Image
from django.test import TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event,Profile,Registration,Audit
from .availability import availability,set_capacity
from .services import cash_register,fulfill

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ParticipationTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('admin','admin@example.test','password-valid')
        self.user=User.objects.create_user('person','person@example.test','password-valid')
        Profile.objects.create(user=self.user,sex='F')
        self.event=Event.objects.create(name='Próxima edición',date=timezone.now()+timedelta(days=5),registration_end=timezone.now()+timedelta(days=4),capacity=2,price=10000,status='open',rules={'tests':[]})
    def picture(self):
        b=BytesIO();Image.new('RGB',(1200,600),'yellow').save(b,'PNG');return SimpleUploadedFile('foto.png',b.getvalue(),content_type='image/png')
    def test_availability_counts_confirmed_reserved_not_expired(self):
        r=Registration.objects.create(event=self.event,user=self.user,name='Participante',sex='F',bib=1,state='reserved')
        data=availability(self.event);self.assertEqual(data['remaining'],1);self.assertEqual(data['reserved'],1)
        r.state='confirmed';r.save();self.assertEqual(availability(self.event)['confirmed'],1)
        r.state='expired';r.save();self.assertEqual(availability(self.event)['remaining'],2)
        response=self.client.get(f'/events/{self.event.pk}/availability/')
        self.assertEqual(response.json()['remaining'],2);self.assertEqual(response['Cache-Control'],'no-store')
        self.assertNotIn('person',response.content.decode())
    def test_capacity_changes_cannot_displace_existing_places(self):
        cash_register(self.event.pk,self.user,self.admin,10000)
        second=User.objects.create_user('second');Profile.objects.create(user=second,sex='M')
        Registration.objects.create(event=self.event,user=second,name='Reserva',sex='M',bib=2,state='reserved')
        with self.assertRaises(ValidationError):set_capacity(self.event.pk,self.admin,1,'Reducir')
        event=set_capacity(self.event.pk,self.admin,3,'Ampliar logística')
        self.assertEqual(availability(event)['remaining'],1)
        self.assertEqual(Audit.objects.filter(action='capacity_changed').count(),1)
        with self.assertRaises(ValidationError):set_capacity(event.pk,self.user,4,'Sin permiso')
        event.status='closed';event.save()
        with self.assertRaises(ValidationError):set_capacity(event.pk,self.admin,5,'Cerrado')
    def test_full_capacity_rejects_next_registration(self):
        self.event.capacity=1;self.event.save();cash_register(self.event.pk,self.user,self.admin,10000)
        extra=User.objects.create_user('extra');Profile.objects.create(user=extra,sex='M')
        with self.assertRaises(ValidationError):cash_register(self.event.pk,extra,self.admin,10000)
        self.assertEqual(availability(self.event)['remaining'],0)
    def test_upcoming_uses_nearest_published_future_event(self):
        Event.objects.create(name='Borrador oculto',date=timezone.now()+timedelta(days=1),registration_end=timezone.now(),status='draft')
        Event.objects.create(name='Evento pasado',date=timezone.now()-timedelta(days=1),registration_end=timezone.now(),status='open')
        response=self.client.get('/')
        self.assertEqual(response.context['upcoming'].pk,self.event.pk)
        self.assertContains(response,'data-countdown=')
        self.assertNotContains(response,'Borrador oculto')
        self.event.status='closed';self.event.save()
        response=self.client.get('/');self.assertIsNone(response.context['upcoming']);self.assertNotContains(response,'data-countdown=')
    def test_draft_availability_is_private(self):
        self.event.status='draft';self.event.save()
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/availability/').status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/availability/').status_code,200)
    def test_photo_upload_authorization_and_normalization(self):
        with TemporaryDirectory() as tmp,override_settings(MEDIA_ROOT=Path(tmp)):
            self.client.force_login(self.user)
            self.assertEqual(self.client.post(f'/participants/{self.user.pk}/photo/',{'photo':self.picture()}).status_code,403)
            self.client.force_login(self.admin)
            response=self.client.post(f'/participants/{self.user.pk}/photo/',{'photo':self.picture(),'next':'/team/'})
            self.assertRedirects(response,'/team/')
            self.user.profile.refresh_from_db()
            with Image.open(self.user.profile.photo.path) as image:
                self.assertEqual(image.format,'JPEG');self.assertEqual(image.size,(1000,500));self.assertFalse(image.getexif())
            self.assertContains(self.client.get('/team/'),self.user.profile.photo.url)
            self.client.post(f'/participants/{self.user.pk}/photo/',{'photo-clear':'on','next':'/team/'})
            self.user.profile.refresh_from_db();self.assertFalse(self.user.profile.photo)
    def test_invalid_photo_and_safe_return(self):
        self.client.force_login(self.admin)
        response=self.client.post(f'/participants/{self.user.pk}/photo/',{'photo':SimpleUploadedFile('bad.jpg',b'not-an-image',content_type='image/jpeg')})
        self.assertEqual(response.status_code,200);self.assertTrue(response.context['form'].errors)
        response=self.client.post(f'/participants/{self.user.pk}/photo/',{'next':'https://external.example/'})
        self.assertRedirects(response,'/')
    def test_photo_camera_is_explicit_and_available_in_both_flows(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/profile/'),'data-camera-open')
        self.client.force_login(self.admin)
        response=self.client.get(f'/participants/{self.user.pk}/photo/')
        self.assertContains(response,'data-camera-capture');self.assertContains(response,'multipart/form-data')
