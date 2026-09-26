from django.test import TestCase
from django.contrib.auth.models import User,Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Event,Profile,Registration,Exercise,Participant
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
        self.assertContains(response,'Resultado que registra el juez')
        self.assertNotContains(response,'name="precision"')
        self.assertNotContains(response,'<details')
        self.assertEqual(Exercise.objects.count(),0)

    def test_upper_inclusive_weight_categories(self):
        from .services import category
        from .event_policy import blank_rules
        rules=blank_rules()
        rules['categories']=[{'name':'70–80','sex':'M','min':70,'max':80},{'name':'60–70','sex':'M','min':60,'max':70}]
        for weight,expected in [(60,'60–70'),(70,'60–70'),(70.001,'70–80'),(80,'70–80')]:
            self.assertEqual(category(rules,'M',weight),expected)
        with self.assertRaises(ValidationError):category(rules,'M',80.001)

    def test_separate_names_round_trip_and_search(self):
        from .account_names import name_parts
        admin=User.objects.create_superuser('owner','owner@example.test','test-password')
        self.client.force_login(admin)
        data={'name':'María José','paternal':'De la Cruz','maternal':'López','role':'admin','email':'new@example.test','password':'safe-password-1957','password_confirm':'safe-password-1957'}
        self.assertEqual(self.client.post('/team/new/',data).status_code,302)
        account=User.objects.get(email=data['email'])
        self.assertEqual(account.first_name,'María José')
        self.assertEqual(account.get_full_name(),'María José De la Cruz López')
        self.assertEqual(name_parts(account)['paternal'],'De la Cruz')
        self.assertContains(self.client.get(f'/team/{account.pk}/'),'value="López"')
        self.assertContains(self.client.get('/team/?q=López'),'María José De la Cruz López')
    def test_legacy_name_is_not_guessed_or_split(self):
        from .account_names import name_parts
        account=User.objects.create_user('legacy',first_name='José Luis De la Cruz')
        self.assertEqual(name_parts(account),{'name':'José Luis De la Cruz','paternal':'','maternal':''})
    def test_simple_catalog_derives_measurement_and_preserves_old_settings(self):
        from .management_forms import CatalogForm
        data={'name':'Carrera nueva','capacity':'Velocidad','measurement':'time','higher':'False','load_mode':'none'}
        form=CatalogForm(data);self.assertTrue(form.is_valid(),form.errors)
        exercise=form.save();self.assertEqual(exercise.unit,'seg');self.assertFalse(exercise.higher)
        exercise.parameters.update(precision=3,equipment='Equipo previo',extra_protocol='Conservar');exercise.base=30;exercise.elite=10;exercise.save()
        form=CatalogForm(data,instance=exercise);self.assertTrue(form.is_valid(),form.errors)
        exercise=form.save();self.assertEqual(exercise.parameters['precision'],3);self.assertEqual(exercise.parameters['extra_protocol'],'Conservar');self.assertEqual(exercise.base,30)
    def test_event_editor_is_visible_and_not_a_wizard(self):
        admin=User.objects.create_superuser('owner','owner@example.test','test-password')
        self.client.force_login(admin)
        response=self.client.get('/events/new/')
        self.assertContains(response,'id="event-info"');self.assertContains(response,'id="event-tests"');self.assertContains(response,'id="event-pricing"')
        self.assertNotContains(response,'data-event-page');self.assertNotContains(response,'<details')

    def test_edit_draft_does_not_require_closed_results(self):
        from .services import configure
        from .event_policy import blank_rules
        admin=User.objects.create_superuser('owner','owner@example.test','test-password')
        event=Event.objects.create(name='Draft',location='Sede',date=timezone.now(),registration_end=timezone.now()-timezone.timedelta(hours=1),rules=blank_rules())
        data={'name':'Editado','location':event.location,'date':event.date,'registration_end':event.registration_end,'price':0,'capacity':20,'demo':False,'rules':blank_rules()}
        configure(event.pk,admin,data)
        event.refresh_from_db();self.assertEqual(event.name,'Editado');self.assertIsNone(event.closed_at)

    def test_team_and_participant_lists_are_isolated(self):
        admin=User.objects.create_superuser('owner','owner@example.test','test-password')
        athlete=User.objects.create_user('runner',email='runner@example.test',first_name='Solo participante')
        Participant.objects.create(name='Solo participante',sex='M')
        self.client.force_login(admin)
        self.assertNotContains(self.client.get('/team/'),'Solo participante')
        self.assertContains(self.client.get('/participants/'),'Solo participante')
        self.assertNotContains(self.client.get('/participants/'),'owner@example.test')
        form=self.client.get('/team/new/').context['form']
        self.assertEqual(list(form.fields['role'].choices),[('admin','Administrador'),('coach','Coach')])
        for path in ['/participants/','/participants/new/']:
            self.client.force_login(athlete)
            self.assertEqual(self.client.get(path).status_code,403)

    def test_participant_home_is_not_promotional_landing(self):
        self.assertContains(self.client.get('/'),'action="/results/"')
        athlete=User.objects.create_user('runner',first_name='Laura')
        self.client.force_login(athlete)
        response=self.client.get('/')
        self.assertContains(response,'Mis inscripciones')
        self.assertNotContains(response,'campaign-photo')
        self.assertContains(response,'Aún no tienes inscripciones')

    def test_staff_can_upload_and_remove_profile_photo_without_sports_fields(self):
        import tempfile
        from unittest.mock import patch
        from .test_portraits import picture
        processor=patch('race.portrait.sports_photo',side_effect=lambda upload:picture(size=(600,750)).read());processor.start();self.addCleanup(processor.stop)
        from io import BytesIO
        from PIL import Image
        from django.test import override_settings
        from django.core.files.uploadedfile import SimpleUploadedFile
        for role in ['admin','coach']:
            user=User.objects.create_user(role,is_superuser=role=='admin')
            if role=='coach':user.groups.add(Group.objects.get_or_create(name='Coach')[0])
            self.client.force_login(user)
            with tempfile.TemporaryDirectory() as media,override_settings(MEDIA_ROOT=media):
                data=BytesIO();Image.new('RGB',(30,30),'red').save(data,format='PNG')
                response=self.client.post('/profile/',{'photo':SimpleUploadedFile('face.png',data.getvalue(),content_type='image/png')})
                self.assertRedirects(response,'/profile/')
                person=Profile.objects.get(user=user)
                self.assertTrue(person.photo);self.assertEqual(person.sex,'')
                response=self.client.get('/profile/')
                self.assertContains(response,person.photo.url)
                self.assertNotContains(response,'name="sex"')
                self.assertNotContains(response,'DORSAL')
                self.client.post('/profile/',{'photo-clear':'on'})
                person.refresh_from_db();self.assertFalse(person.photo)
