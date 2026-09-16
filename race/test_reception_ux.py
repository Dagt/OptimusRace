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
        capture(entry.pk,self.admin,0,42,None,'done',0,'')
        self.client.logout()
        path=f'/results/participants/{entry.participant_id}/'
        response=self.client.get('/')
        self.assertContains(response,'Primeros de cada categoría');self.assertContains(response,path)
        self.assertContains(self.client.get('/results/'),entry.participant.full_name)
        self.assertContains(self.client.get(f'/events/{self.event.pk}/'),path)
        row=self.client.get(f'/events/{self.event.pk}/live/').json()['board'][0]
        self.assertEqual(row['photo_url'],entry.participant.photo.url);self.assertEqual(row['profile_url'],path)
        self.assertEqual(row['capacity_results']['Potencia']['photo_url'],entry.participant.photo.url)
        change_phase(self.event.pk,self.admin,'closed');self.event.refresh_from_db()
        stored=deepcopy(self.event.final_board)
        person=entry.participant;person.photo='athletes/new-photo.jpg';person.save()
        self.assertEqual(board(self.event)[0]['photo_url'],person.photo.url)
        self.event.refresh_from_db();self.assertEqual(self.event.final_board,stored)


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
