from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from .models import Profile
from .forms import ParticipantPhotoForm
from .photos import save_photo


def picture(color='red',size=(640,480)):
    out=BytesIO();Image.new('RGB',size,color).save(out,'PNG')
    return SimpleUploadedFile('portrait.png',out.getvalue(),content_type='image/png')

class PortraitTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_superuser('portrait',email='portrait@example.test',password='test-password')
        self.profile=Profile.objects.create(user=self.user,sex='M')
        self.client.force_login(self.user)

    def test_original_and_processed_are_distinct_and_clear_together(self):
        with TemporaryDirectory() as media,override_settings(MEDIA_ROOT=media):
            save_photo(self.profile,picture('yellow',(600,750)),picture('red',(1200,900)))
            with Image.open(self.profile.photo.path) as processed,Image.open(self.profile.original_photo.path) as original:
                self.assertEqual(processed.size,(600,750));self.assertEqual(original.size,(1200,900))
                self.assertGreater(original.getpixel((0,0))[0],240)
                self.assertFalse(original.getexif())
            self.assertNotEqual(self.profile.photo.name,self.profile.original_photo.name)
            save_photo(self.profile,False);self.profile.refresh_from_db()
            self.assertFalse(self.profile.photo);self.assertFalse(self.profile.original_photo)

    def test_invalid_original_rejected_before_save(self):
        form=ParticipantPhotoForm({}, {'photo':picture(),'original_photo':SimpleUploadedFile('bad.png',b'bad')},instance=self.profile)
        self.assertFalse(form.is_valid());self.assertIn('original_photo',form.errors)
        self.profile.refresh_from_db();self.assertFalse(self.profile.photo)

    def test_profile_form_saves_both_uploaded_files(self):
        with TemporaryDirectory() as media,override_settings(MEDIA_ROOT=media):
            self.assertRedirects(self.client.post('/profile/',{'sex':'M','photo':picture('yellow'),'original_photo':picture('blue')}),'/profile/')
            self.profile.refresh_from_db()
            with Image.open(self.profile.original_photo.path) as original:self.assertGreater(original.getpixel((0,0))[2],240)

    def test_preview_needs_authentication_and_post(self):
        self.assertEqual(self.client.get('/profile/portrait-preview/').status_code,405)
        self.client.logout();self.assertEqual(self.client.post('/profile/portrait-preview/',{'photo':picture()}).status_code,302)

    def test_preview_does_not_save_profile(self):
        with patch('race.portrait.portrait_cutout',return_value=b'preview'):
            response=self.client.post('/profile/portrait-preview/',{'photo':picture()})
        self.assertEqual(response.status_code,200);self.assertEqual(response['Cache-Control'],'no-store')
        self.profile.refresh_from_db();self.assertFalse(self.profile.photo)

    def test_invalid_preview_returns_actionable_error(self):
        response=self.client.post('/profile/portrait-preview/',{'photo':SimpleUploadedFile('bad.png',b'bad')})
        self.assertEqual(response.status_code,400);self.assertIn('error',response.json())

    def test_busy_processor_rejects_without_queueing(self):
        from .portrait import processing
        processing.acquire()
        try:self.assertEqual(self.client.post('/profile/portrait-preview/',{'photo':picture()}).status_code,429)
        finally:processing.release()

    def test_missing_model_preserves_original_option(self):
        from .portrait import session
        session.cache_clear()
        with TemporaryDirectory() as directory,override_settings(PORTRAIT_MODEL_PATH=directory+'/missing.onnx'):
            response=self.client.post('/profile/portrait-preview/',{'photo':picture()})
        self.assertEqual(response.status_code,400);self.assertIn('original',response.json()['error'])
        session.cache_clear()
