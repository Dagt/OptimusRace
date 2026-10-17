"""Event photos: permanent Appex branding, metadata removal and small previews."""
import logging
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageOps

from .photos import validate_photo

MAX_PHOTO_BYTES = 15 * 1024 * 1024
MAX_BATCH_FILES = 20
MAX_BATCH_BYTES = 100 * 1024 * 1024
WATERMARK_OPACITY = 75


def prepare_photo(upload, previous_opacity=0):
    validate_photo(upload, max_bytes=MAX_PHOTO_BYTES)
    with Image.open(upload) as source:
        # Composite transparency onto white, honor camera orientation, discard EXIF/GPS.
        oriented = ImageOps.exif_transpose(source)
        # Public viewing copy only; never publish a full-resolution source.
        oriented.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        oriented = oriented.convert('RGBA')
        image = Image.new('RGBA', oriented.size, 'white')
        image.alpha_composite(oriented)

    # Crop the same official logo region used by partner-brand.css.
    with Image.open(settings.BASE_DIR / 'static/images/partners/appex-dark.jpg') as source:
        logo = source.crop((237, 474, 943, 655)).convert('RGBA')
    width = max(1, min(round(image.width * .78), round(image.height * 1.7)))
    logo = logo.resize((width, max(1, round(width * 181 / 706))), Image.Resampling.LANCZOS)
    # Remove the JPEG's dark background, retaining the official white/yellow artwork.
    # The translucent logo spans the center, including the photographic subject.
    red, green, blue, _ = logo.split()
    mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    alpha = []
    for value in range(256):
        target = max(0, min(1, (value-25)/230)) * WATERMARK_OPACITY/100
        # Existing photos already contain the former 45% mark. Composite only
        # the missing opacity, rather than applying a second full-strength mark.
        previous = (max(0, min(115, round((value-25)*.5))) / 255
                    if previous_opacity == 45 else
                    max(0, min(1, (value-25)/230)) * previous_opacity/100)
        added = max(0, min(1, (target-previous)/(1-previous))) if previous < 1 else 0
        alpha.append(round(added*255))
    logo.putalpha(mask.point(alpha))
    image.alpha_composite(logo, ((image.width-logo.width)//2, (image.height-logo.height)//2))
    image = image.convert('RGB')
    full = BytesIO()
    image.save(full, 'JPEG', quality=90, optimize=True)
    image.thumbnail((720, 720), Image.Resampling.LANCZOS)
    preview = BytesIO()
    image.save(preview, 'JPEG', quality=85, optimize=True)
    upload.seek(0)
    return ContentFile(full.getvalue()), ContentFile(preview.getvalue())


def cleanup_files(files):
    for storage, name in files:
        try:
            storage.delete(name)
        except Exception:
            logging.getLogger(__name__).exception('Could not remove gallery file %s', name)
