"""Upgrade stored viewing copies once; safe to repeat on subsequent deploys."""
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from race.gallery import WATERMARK_OPACITY, cleanup_files, prepare_photo
from race.models import EventPhoto


class Command(BaseCommand):
    help = 'Aumenta la opacidad de las marcas de agua existentes sin duplicar la marca.'

    def handle(self, *args, **options):
        count = 0
        ids = EventPhoto.objects.filter(watermark_opacity__lt=WATERMARK_OPACITY).values_list('pk', flat=True)
        for pk in list(ids):
            stored = []
            try:
                with transaction.atomic():
                    photo = EventPhoto.objects.select_for_update().get(pk=pk)
                    if photo.watermark_opacity >= WATERMARK_OPACITY:
                        continue
                    old = [(field.storage, field.name) for field in (photo.image, photo.thumbnail)]
                    with photo.image.open('rb') as source:
                        image, thumbnail = prepare_photo(source, previous_opacity=photo.watermark_opacity)
                    name = f'{uuid.uuid4().hex}.jpg'
                    for field, content in [(photo.image, image), (photo.thumbnail, thumbnail)]:
                        field.save(name, content, save=False)
                        stored.append((field.storage, field.name))
                    photo.watermark_opacity = WATERMARK_OPACITY
                    photo.save(update_fields=['image', 'thumbnail', 'watermark_opacity'])
                    transaction.on_commit(lambda files=old: cleanup_files(files))
                count += 1
            except Exception:
                cleanup_files(stored)
                raise
        self.stdout.write(f'Fotos actualizadas a {WATERMARK_OPACITY}% de opacidad: {count}.')
