import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .gallery import MAX_BATCH_BYTES, MAX_PHOTO_BYTES, prepare_photo
from .gallery_forms import GalleryUploadForm
from .models import Audit, Event, EventPhoto


def upload(name='race.jpg', size=(1000, 700), format='JPEG', **kwargs):
    output = BytesIO()
    Image.new('RGB', size, (110, 150, 180)).save(output, format, **kwargs)
    return SimpleUploadedFile(name, output.getvalue(), content_type=f'image/{format.lower()}')


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class GalleryTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.temp.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.admin = User.objects.create_superuser('gallery-admin', 'admin@example.test', 'secret')
        self.coach = User.objects.create_user('gallery-coach')
        self.coach.groups.add(Group.objects.get_or_create(name='Coach')[0])
        self.athlete = User.objects.create_user('gallery-athlete')
        self.event = self.make_event('Competencia pública', 'closed')
        self.draft = self.make_event('Evento privado', 'draft')
        self.manage = reverse('gallery_manage', args=[self.event.pk])
        self.album = reverse('event_gallery', args=[self.event.pk])

    def make_event(self, name, status):
        return Event.objects.create(name=name, status=status, date=timezone.now(),
                                    registration_end=timezone.now(), location='Appex',
                                    rules={'tests': [], 'categories': []})

    def photo(self, event=None, **kwargs):
        return EventPhoto.objects.create(event=event or self.event, image=upload(),
                                         uploaded_by=self.admin, **kwargs)

    def test_admin_uploads_multiple_photos_public_can_view_without_login(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.manage, {'photos': [upload(), upload('second.png', format='PNG')],
                                                  'caption': 'Momentos de la meta'})
        self.assertRedirects(response, self.manage)
        photos = list(EventPhoto.objects.all())
        self.assertEqual(len(photos), 2)
        self.assertTrue(all(p.uploaded_by == self.admin and p.caption == 'Momentos de la meta' for p in photos))
        self.assertEqual(Audit.objects.get(action='gallery_uploaded').details, {'count': 2})
        self.client.logout()
        response = self.client.get(self.album)
        self.assertContains(response, 'Momentos de la meta')
        self.assertContains(response, photos[0].image.url)
        self.assertContains(response, photos[0].thumbnail.url)
        self.assertNotContains(response, 'Confirmar eliminación')
        self.assertNotContains(response, 'Abrir foto completa')
        self.assertNotContains(response, 'data-gallery-original')
        self.assertNotContains(response, f'href="{photos[0].image.url}"')
        self.assertContains(response, 'draggable="false"')
        self.assertContains(self.client.get(reverse('gallery')), self.event.name)

    def test_watermark_is_in_both_saved_files_and_original_is_not_stored(self):
        photo = self.photo()
        for field in (photo.image, photo.thumbnail):
            with field.open('rb') as file, Image.open(file) as image:
                self.assertEqual(image.format, 'JPEG')
                self.assertFalse(image.getexif())
                # The source was a solid color: the center must contain translucent logo pixels.
                center = image.crop((image.width * .1, image.height * .35, image.width * .9, image.height * .65))
                self.assertGreater(center.getextrema()[0][1], 210)
                self.assertLess(center.getextrema()[0][1], 255)
                self.assertAlmostEqual(image.getpixel((image.width-10, image.height-10))[0], 110, delta=5)
                self.assertLess(max(image.getpixel((10, 10))), 190)
        self.assertEqual(len(list(Path(self.temp.name).rglob('*.jpg'))), 2)
        self.assertNotEqual(photo.image.name, photo.thumbnail.name)

    def test_saving_caption_does_not_reapply_watermark(self):
        photo = self.photo()
        with photo.image.open('rb') as file:
            before = file.read()
        photo.caption = 'Nueva descripción'
        photo.save(update_fields=['caption'])
        with photo.image.open('rb') as file:
            self.assertEqual(file.read(), before)

    def test_existing_watermarks_upgrade_once_to_match_new_uploads(self):
        from django.core.management import call_command
        from io import StringIO
        with patch('race.gallery.WATERMARK_OPACITY', 45):
            existing = self.photo()
        self.assertEqual(existing.watermark_opacity, 45)
        old = [(field.storage, field.name) for field in (existing.image, existing.thumbnail)]
        expected = self.photo()
        with self.captureOnCommitCallbacks(execute=True):
            call_command('update_gallery_watermarks', stdout=StringIO())
        existing.refresh_from_db()
        self.assertEqual(existing.watermark_opacity, 85)
        self.assertEqual(existing.watermark_version, 2)
        self.assertTrue(all(not storage.exists(name) for storage, name in old))
        for field in ['image', 'thumbnail']:
            with getattr(existing, field).open('rb') as first, getattr(expected, field).open('rb') as second:
                with Image.open(first) as actual, Image.open(second) as target:
                    region = (actual.width*.1, actual.height*.35, actual.width*.9, actual.height*.65)
                    self.assertAlmostEqual(actual.crop(region).getextrema()[0][1],
                                           target.crop(region).getextrema()[0][1], delta=5)
        names = (existing.image.name, existing.thumbnail.name)
        output = StringIO()
        call_command('update_gallery_watermarks', stdout=output)
        existing.refresh_from_db()
        self.assertEqual(names, (existing.image.name, existing.thumbnail.name))
        self.assertIn('Fotos actualizadas a 85% de opacidad: 0.', output.getvalue())

    def test_diagonal_logos_cover_five_regions_in_both_photo_orientations(self):
        for size in [(600, 1500), (1500, 600)]:
            full, _ = prepare_photo(upload(size=size))
            with Image.open(full) as image:
                for cx, cy in ((.25,.18),(.75,.18),(.5,.5),(.25,.82),(.75,.82)):
                    region = image.crop((int((cx-.20)*size[0]), int((cy-.12)*size[1]),
                                         int((cx+.20)*size[0]), int((cy+.12)*size[1])))
                    self.assertGreater(region.getextrema()[0][1], 220)

    def test_previous_single_logo_gets_diagonal_pattern_once(self):
        from django.core.management import call_command
        from django.core.files.base import ContentFile
        from django.conf import settings
        from .gallery import branded_logo
        from io import StringIO
        photo = self.photo()
        legacy = Image.new('RGBA', (1000, 700), (110, 150, 180, 255))
        with Image.open(settings.BASE_DIR/'static/images/partners/appex-dark.jpg') as source:
            with patch('race.gallery.WATERMARK_OPACITY', 75):
                logo = branded_logo(source.crop((237, 474, 943, 655)).convert('RGBA'), 780)
        legacy.alpha_composite(logo, ((1000-logo.width)//2, (700-logo.height)//2))
        buffer = BytesIO()
        legacy.convert('RGB').save(buffer, 'JPEG')
        storage, name = photo.image.storage, photo.image.name
        storage.delete(name)
        self.assertEqual(storage.save(name, ContentFile(buffer.getvalue())), name)
        EventPhoto.objects.filter(pk=photo.pk).update(watermark_opacity=75, watermark_version=1)
        before = photo.image.name
        call_command('update_gallery_watermarks', stdout=StringIO())
        photo.refresh_from_db()
        self.assertNotEqual(photo.image.name, before)
        self.assertEqual(photo.watermark_opacity, 85)
        self.assertEqual(photo.watermark_version, 2)
        with photo.image.open('rb') as file, Image.open(file) as updated:
            for cx, cy in ((.25,.18),(.75,.18),(.5,.5),(.25,.82),(.75,.82)):
                region = updated.crop((int((cx-.2)*1000), int((cy-.12)*700),
                                       int((cx+.2)*1000), int((cy+.12)*700)))
                self.assertGreater(region.getextrema()[0][1], 220)
        after = photo.image.name
        call_command('update_gallery_watermarks', stdout=StringIO())
        photo.refresh_from_db()
        self.assertEqual(photo.image.name, after)

    def test_old_pattern_is_upgraded_even_with_current_opacity(self):
        from django.core.management import call_command
        from io import StringIO
        photo = self.photo()
        EventPhoto.objects.filter(pk=photo.pk).update(watermark_version=1)
        before = photo.image.name
        call_command('update_gallery_watermarks', stdout=StringIO())
        photo.refresh_from_db()
        self.assertNotEqual(photo.image.name, before)
        self.assertEqual(photo.watermark_version, 2)

    def test_failed_existing_watermark_upgrade_keeps_current_files(self):
        from django.core.management import call_command
        from .simulation_storage import SimulationMediaStorage
        with patch('race.gallery.WATERMARK_OPACITY', 45):
            photo = self.photo()
        old = [(field.storage, field.name) for field in (photo.image, photo.thumbnail)]
        original = SimulationMediaStorage._save

        def fail_thumbnail(storage, name, content):
            if 'thumbnails/' in name:
                raise OSError('Storage unavailable')
            return original(storage, name, content)

        with patch.object(SimulationMediaStorage, '_save', fail_thumbnail):
            with self.assertRaises(OSError):
                call_command('update_gallery_watermarks')
        photo.refresh_from_db()
        self.assertEqual(photo.watermark_opacity, 45)
        self.assertEqual(photo.image.name, old[0][1])
        self.assertEqual(photo.thumbnail.name, old[1][1])
        self.assertTrue(all(storage.exists(name) for storage, name in old))
        self.assertEqual(len(list(Path(self.temp.name).rglob('*.jpg'))), 2)

    def test_camera_orientation_is_corrected_and_metadata_removed(self):
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = 'private camera description'
        full, _ = prepare_photo(upload(size=(800, 500), exif=exif))
        with Image.open(full) as image:
            self.assertEqual(image.size, (500, 800))
            self.assertFalse(image.getexif())

    def test_large_images_are_resized_and_small_images_not_enlarged(self):
        for size, expected in [((3000, 1500), (1600, 800)), ((120, 80), (120, 80))]:
            full, preview = prepare_photo(upload(size=size))
            with Image.open(full) as image:
                self.assertEqual(image.size, expected)
            with Image.open(preview) as image:
                self.assertLessEqual(max(image.size), 720)

    def test_transparent_photo_and_webp_are_supported(self):
        output = BytesIO()
        Image.new('RGBA', (1000, 700), (0, 0, 0, 0)).save(output, 'PNG')
        full, _ = prepare_photo(SimpleUploadedFile('alpha.png', output.getvalue()))
        with Image.open(full) as image:
            self.assertEqual(image.getpixel((10, 10)), (255, 255, 255))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(self.manage, {'photos': upload('race.webp', format='WEBP')}), self.manage)

    def test_invalid_file_rejects_entire_batch_without_storing_any_files(self):
        self.client.force_login(self.admin)
        invalid = SimpleUploadedFile('fake.jpg', b'<script>bad</script>', content_type='image/jpeg')
        response = self.client.post(self.manage, {'photos': [upload(), invalid]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(EventPhoto.objects.exists())
        self.assertFalse(Audit.objects.filter(action='gallery_uploaded').exists())
        self.assertFalse(list(Path(self.temp.name).rglob('*.jpg')))

    def test_formats_pixels_sizes_and_batch_limits_are_validated(self):
        data = {'caption': ''}
        for files in [[], [upload(format='GIF')], [upload(size=(5100, 5000))],
                      [upload() for _ in range(21)]]:
            self.assertFalse(GalleryUploadForm(data, {'photos': files}).is_valid())
        file = upload()
        file.size = MAX_PHOTO_BYTES + 1
        self.assertFalse(GalleryUploadForm(data, {'photos': [file]}).is_valid())
        files = [upload() for _ in range(8)]
        for file in files:
            file.size = MAX_PHOTO_BYTES
        self.assertGreater(sum(f.size for f in files), MAX_BATCH_BYTES)
        self.assertFalse(GalleryUploadForm(data, {'photos': files}).is_valid())

    def test_storage_failure_rolls_back_entire_batch_and_cleans_files(self):
        self.client.force_login(self.admin)
        original = EventPhoto.save
        calls = 0

        def fail_on_second(photo, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('Storage unavailable')
            return original(photo, *args, **kwargs)

        with patch.object(EventPhoto, 'save', fail_on_second):
            response = self.client.post(self.manage, {'photos': [upload(), upload()]})
        self.assertContains(response, 'No se pudieron guardar las fotos')
        self.assertFalse(EventPhoto.objects.exists())
        self.assertFalse(list(Path(self.temp.name).rglob('*.jpg')))

    def test_thumbnail_failure_removes_full_photo(self):
        self.client.force_login(self.admin)
        from .simulation_storage import SimulationMediaStorage
        original = SimulationMediaStorage._save

        def fail_thumbnail(storage, name, content):
            if 'thumbnails/' in name:
                raise OSError('Storage unavailable')
            return original(storage, name, content)

        with patch.object(SimulationMediaStorage, '_save', fail_thumbnail):
            response = self.client.post(self.manage, {'photos': upload()})
        self.assertContains(response, 'No se pudieron guardar las fotos')
        self.assertFalse(EventPhoto.objects.exists())
        self.assertFalse(list(Path(self.temp.name).rglob('*.jpg')))

    def test_only_admins_can_upload_or_delete(self):
        photo = self.photo()
        delete = reverse('gallery_delete', args=[self.event.pk, photo.pk])
        for user in [self.coach, self.athlete, None]:
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            expected = 403 if user else 302
            self.assertEqual(self.client.get(self.manage).status_code, expected)
            self.assertEqual(self.client.post(self.manage, {'photos': upload()}).status_code, expected)
            self.assertEqual(self.client.post(delete).status_code, expected)
        self.assertEqual(EventPhoto.objects.count(), 1)

    def test_draft_album_is_hidden_from_public_including_direct_urls(self):
        self.photo(self.draft)
        draft_url = reverse('event_gallery', args=[self.draft.pk])
        for user in [None, self.coach]:
            if user:
                self.client.force_login(user)
            self.assertNotContains(self.client.get(reverse('gallery')), self.draft.name)
            self.assertEqual(self.client.get(draft_url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('gallery')), self.draft.name)
        self.assertContains(self.client.get(draft_url), 'BORRADOR')

    def test_admin_can_find_empty_albums_and_public_gets_empty_state(self):
        self.assertContains(self.client.get(reverse('gallery')), 'Los recuerdos están por llegar')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('gallery')), self.event.name)
        self.assertContains(self.client.get(self.manage), 'Aún no hay fotos')

    def test_delete_requires_post_csrf_and_matching_event_then_removes_files(self):
        photo = self.photo()
        files = [(field.storage, field.name) for field in (photo.image, photo.thumbnail)]
        self.client.force_login(self.admin)
        url = reverse('gallery_delete', args=[self.event.pk, photo.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        wrong_url = reverse('gallery_delete', args=[self.draft.pk, photo.pk])
        self.assertEqual(self.client.post(wrong_url).status_code, 404)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post(url).status_code, 403)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertRedirects(self.client.post(url), self.manage)
        self.assertFalse(EventPhoto.objects.exists())
        self.assertTrue(all(not storage.exists(name) for storage, name in files))
        self.assertTrue(Audit.objects.filter(action='gallery_deleted').exists())

    def test_gallery_pagination_and_caption_escaping(self):
        first = self.photo(caption='<script>alert(1)</script>')
        EventPhoto.objects.bulk_create([EventPhoto(event=self.event, image=first.image.name,
            thumbnail=first.thumbnail.name, caption=f'Photo {i}') for i in range(25)])
        response = self.client.get(self.album)
        self.assertEqual(len(response.context['page']), 24)
        response = self.client.get(self.album, {'page': 2})
        self.assertEqual(len(response.context['page']), 2)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_navigation_links_expose_gallery_and_management(self):
        self.assertContains(self.client.get('/'), 'href="/gallery/"')
        self.assertContains(self.client.get(reverse('event', args=[self.event.pk])), self.album)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('operations', args=[self.event.pk])), self.manage)

    def test_simulation_gallery_upload_and_deletion_leave_real_photos_untouched(self):
        from .simulation_runtime import create, database
        real = self.photo()
        self.client.force_login(self.admin)
        with override_settings(SIMULATION_ROOT=Path(self.temp.name) / 'simulations'):
            meta = create(self.event.pk, self.admin)
            prefix = meta['prefix']
            self.assertContains(self.client.get(prefix + self.album), real.image.name)
            response = self.client.post(prefix + self.manage, {'photos': upload()})
            self.assertEqual(response.status_code, 302)
            with database(meta):
                self.assertEqual(EventPhoto.objects.count(), 2)
                practice = EventPhoto.objects.exclude(pk=real.pk).get()
                practice_path = Path(practice.image.path)
                self.assertTrue(practice_path.is_relative_to(Path(self.temp.name) / 'simulations'))
                self.assertTrue(practice_path.exists())
            real_delete = reverse('gallery_delete', args=[self.event.pk, real.pk])
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.client.post(prefix + real_delete).status_code, 302)
            self.assertEqual(EventPhoto.objects.count(), 1)
            self.assertTrue(real.image.storage.exists(real.image.name))
            self.assertTrue(real.thumbnail.storage.exists(real.thumbnail.name))
