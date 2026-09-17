from copy import deepcopy
from unittest.mock import patch
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from . import test_cash_participants as cash_fixtures
from .models import Participant,Registration,Profile
from .forms import BirthDateField,EventForm,ParticipantPhotoForm
from .policy_forms import PolicyForm
from .services import change_phase,capture,board
from .test_portraits import picture
from unittest import skipUnless
from pathlib import Path
from tempfile import TemporaryDirectory
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.test import override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .portrait import model_path,sports_photo


class ReceptionUXTests(TestCase):
    setUp=cash_fixtures.CashParticipantTests.setUp
    data=cash_fixtures.CashParticipantTests.data

    def test_small_portrait_is_enlarged_and_aligned_near_top(self):
        cutout=Image.new('RGBA',(100,125),(200,80,40,255));source=BytesIO();cutout.save(source,'PNG')
        with patch('race.portrait.portrait_cutout',return_value=source.getvalue()),patch('race.portrait.sports_photo',sports_photo):
            result=Image.open(BytesIO(sports_photo(picture())))
        self.assertEqual(result.size,(600,750))
        self.assertGreater(result.getpixel((300,60))[0],180)
        self.assertLess(result.getpixel((300,10))[0],60)

    def test_event_fields_benefits_visible_and_dates_day_first(self):
        response=self.client.get('/events/new/')
        self.assertContains(response,'name="benefits"')
        self.assertNotContains(response,'name="judging_standard"')
        self.assertNotContains(response,'name="registration_channels"')
        self.assertContains(response,'dd/mm/aaaa HH:MM')
        self.assertNotContains(response,'type="datetime-local"')
        field=BirthDateField();self.assertEqual(field.clean('04/05/1990'),date(1990,5,4))
        self.assertEqual(field.clean('02032000'),date(2000,3,2))
        with self.assertRaises(ValidationError):field.clean('31022000')
        with self.assertRaises(ValidationError):field.clean('31/02/1990')
        self.assertIn('04/05/1990',field.widget.render('birth_date',date(1990,5,4)))
        form=EventForm({'name':'Nuevo','location':'Sede','date':'18/10/2026 09:00','registration_end':'17/10/2026 18:00','price':'450','capacity':'100'})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['date'].day,18)
        rules=deepcopy(self.event.rules);rules['judging_standard']='Criterio histórico'
        policy=PolicyForm({'minimum_age':16,'benefits':'Playera y medalla'},rules=rules)
        self.assertTrue(policy.is_valid(),policy.errors)
        updated=policy.apply(rules)
        self.assertEqual(updated['benefits'],'Playera y medalla')
        self.assertEqual(updated['judging_standard'],'Criterio histórico')

    def test_capture_uses_separate_dialog_without_timer_or_original_choice(self):
        response=self.client.get(self.url)
        for text in ['data-camera-capture','Foto con acabado deportivo','Pesaje y pago']:self.assertContains(response,text)
        for text in ['data-photo-dialog','data-photo-use','data-photo-open']:self.assertContains(response,text)
        for text in ['data-camera-timer','data-use-original','data-photo-accept','data-photo-zoom']:self.assertNotContains(response,text)
        self.assertNotContains(self.client.get('/profile/'),'Ir al panel')

    def test_failed_processing_cannot_save_raw_photo_or_registration(self):
        with patch('race.portrait.sports_photo',side_effect=ValidationError('Modelo no disponible')):
            response=self.client.post(self.url,self.data())
        self.assertContains(response,'Modelo no disponible')
        self.assertFalse(Participant.objects.exists());self.assertFalse(Registration.objects.exists())
        profile=Profile.objects.create(user=self.admin,sex='')
        with patch('race.portrait.sports_photo',side_effect=ValidationError('Modelo no disponible')):
            form=ParticipantPhotoForm({}, {'photo':picture()},instance=profile)
            self.assertFalse(form.is_valid());self.assertIn('photo',form.errors)

    def test_public_profiles_linked_and_tv_has_photos_even_after_closing(self):
        self.client.post(self.url,self.data());entry=Registration.objects.get()
        change_phase(self.event.pk,self.admin,'live')
        capture(entry.pk,self.scoring_coach,0,42,None,'done',0,'')
        self.client.logout()
        path=f'/results/participants/{entry.participant_id}/'
        response=self.client.get('/')
        self.assertContains(response,'Primeros de cada categoría');self.assertContains(response,path)
        self.assertContains(self.client.get('/results/'),entry.participant.full_name)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/'),path)
        row=self.client.get(f'/events/{self.event.pk}/live/').json()['board'][0]
        self.assertEqual(row['photo_url'],entry.participant.photo.url);self.assertEqual(row['profile_url'],path)
        self.assertNotIn('capacity_results',row)
        self.assertIn('Potencia',row['capacities'])
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        stored=deepcopy(self.event.final_board)
        person=entry.participant;person.photo='athletes/new-photo.jpg';person.save()
        self.assertEqual(board(self.event)[0]['photo_url'],person.photo.url)
        self.event.refresh_from_db();self.assertEqual(self.event.final_board,stored)

    def test_empty_profile_keeps_radar_without_invented_scores(self):
        person=Participant.objects.create(name='Sin marcas',paternal='Prueba',sex='M')
        response=self.client.get(f'/results/participants/{person.pk}/')
        self.assertContains(response,'empty-radar-title')
        self.assertContains(response,'Sin marcas registradas')
        for capacity in ['Fuerza','Resistencia','Velocidad','Potencia']:self.assertContains(response,capacity)
        self.assertNotContains(response,'id="capacity-chart"')
        self.client.logout()
        self.assertEqual(self.client.get(f'/results/participants/{person.pk}/').status_code,404)

    def test_exact_participant_number_selects_existing_record(self):
        person=Participant.objects.create(name='Ana',paternal='Prueba',sex='M')
        response=self.client.get(self.url,{'q':f'p{person.pk}'})
        self.assertRedirects(response,f'{self.url}?participant={person.pk}')
        selected=self.client.get(response.url)
        self.assertEqual(selected.context['form'].instance.pk,person.pk)
        self.assertContains(selected,'value="Ana"')
        self.assertEqual(Participant.objects.count(),1)

    def test_search_marks_existing_registration_instead_of_offering_payment(self):
        self.client.post(self.url,self.data());person=Participant.objects.get()
        response=self.client.get(self.url,{'q':f'P{person.pk}'})
        self.assertContains(response,'Ya inscrito · Ver perfil')
        self.assertNotContains(response,f'href="?participant={person.pk}"')

    def test_closed_or_full_event_cannot_offer_a_new_cash_registration(self):
        self.event.capacity=1;self.event.save()
        self.client.post(self.url,self.data())
        for path in [self.url,f'/events/{self.event.pk}/operations/','/participants/']:
            self.assertContains(self.client.get(path),'Cupo agotado')
        response=self.client.get(self.url)
        self.assertContains(response,'class="button full" disabled')
        self.event.capacity=2;self.event.status='closed';self.event.save()
        response=self.client.get(self.url)
        self.assertContains(response,'Evento cerrado')
        self.assertContains(response,'class="button full" disabled')
        self.assertNotContains(self.client.get('/participants/'),f'href="{self.url}"')

    def test_key_pages_have_unique_ids_and_no_nested_forms(self):
        from html.parser import HTMLParser
        class FormsParser(HTMLParser):
            def __init__(self):
                super().__init__();self.ids=[];self.form_depth=0;self.errors=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if attrs.get('id'):self.ids.append(attrs['id'])
                if tag=='form':
                    if self.form_depth:self.errors.append('Nested form')
                    self.form_depth+=1
            def handle_endtag(self,tag):
                if tag=='form':self.form_depth-=1
        self.client.post(self.url,self.data());person=Participant.objects.get()
        paths=['/','/profile/','/team/','/catalog/','/participants/','/results/','/events/new/',self.url,
               f'/participants/{person.pk}/edit/',f'/results/participants/{person.pk}/',
               f'/events/{self.event.pk}/',f'/events/{self.event.pk}/operations/',f'/events/{self.event.pk}/tv/']
        for path in paths:
            with self.subTest(path=path):
                response=self.client.get(path);self.assertEqual(response.status_code,200)
                parser=FormsParser();parser.feed(response.content.decode())
                self.assertEqual(parser.errors,[]);self.assertEqual(parser.form_depth,0)
                self.assertEqual(len(parser.ids),len(set(parser.ids)),[x for x in parser.ids if parser.ids.count(x)>1])


@skipUnless(model_path().exists(),'Integration requires the downloaded local portrait model.')
class PortraitIntegrationTests(TestCase):
    def test_real_preview_and_profile_save_use_sports_background(self):
        admin=User.objects.create_superuser('portrait-integration','portrait@example.test','test-password')
        self.client.force_login(admin)
        source=(settings.BASE_DIR/'static/images/campaign.png').read_bytes()
        with TemporaryDirectory() as media,override_settings(MEDIA_ROOT=Path(media)):
            response=self.client.post('/profile/portrait-preview/',{'photo':SimpleUploadedFile('photo.png',source,content_type='image/png')})
            self.assertEqual(response.status_code,200)
            with Image.open(BytesIO(response.content)) as preview:
                self.assertEqual(preview.size,(600,750));self.assertEqual(preview.format,'JPEG')
                self.assertLess(max(preview.getpixel((0,0))),50)
            response=self.client.post('/profile/',{'photo':SimpleUploadedFile('photo.png',source,content_type='image/png')})
            self.assertRedirects(response,'/profile/')
            profile=Profile.objects.get(user=admin)
            with Image.open(profile.photo.path) as saved:self.assertEqual(saved.size,(600,750))
            self.assertTrue(profile.original_photo)
            old_photo=profile.photo.name;original=profile.original_photo.name
            response=self.client.post('/profile/',{'action':'refresh_photo'})
            self.assertRedirects(response,'/profile/')
            profile.refresh_from_db()
            self.assertNotEqual(profile.photo.name,old_photo)
            self.assertEqual(profile.original_photo.name,original)
            with Image.open(profile.photo.path) as saved:self.assertEqual(saved.size,(600,750))
