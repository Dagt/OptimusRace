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
WATERMARK_OPACITY = 85
WATERMARK_VERSION = 2


def logo_alpha(mask, previous_opacity=0, legacy=False):
    alpha = []
    for value in range(256):
        coverage = max(0, min(1, (value-25)/230))
        target = coverage * WATERMARK_OPACITY/100
        previous = (max(0, min(115, round((value-25)*.5))) / 255
                    if legacy and previous_opacity == 45 else coverage * previous_opacity/100)
        added = max(0, min(1, (target-previous)/(1-previous))) if previous < 1 else 0
        alpha.append(round(added*255))
    return mask.point(alpha)


def branded_logo(source, width, previous_opacity=0, legacy=False):
    logo = source.resize((width, max(1, round(width * 181 / 706))), Image.Resampling.LANCZOS)
    red, green, blue, _ = logo.split()
    mask = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    logo.putalpha(logo_alpha(mask, previous_opacity, legacy))
    return logo


def prepare_photo(upload, previous_opacity=0, previous_version=0):
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
        artwork = source.crop((237, 474, 943, 655)).convert('RGBA')
    if previous_opacity and previous_version < 2:
        # The former central mark is baked into older viewing copies. Retain and
        # strengthen it, then add the diagonal pattern; never try to erase photo content.
        width = max(1, min(round(image.width*.78), round(image.height*1.7)))
        logo = branded_logo(artwork, width, previous_opacity, legacy=True)
        image.alpha_composite(logo, ((image.width-logo.width)//2, (image.height-logo.height)//2))

    # Five inclined logos form two diagonals across the full photo. Fit the
    # rotated footprint to both orientations without clipping or black padding.
    width = max(1, round(image.width*.58))
    footprint = branded_logo(artwork, width).rotate(30, Image.Resampling.BICUBIC, expand=True)
    scale = min(1, image.height*.28/footprint.height, image.width*.49/footprint.width)
    width = max(1, round(width*scale))
    logo = branded_logo(artwork, width, previous_opacity if previous_version >= 2 else 0)
    logo = logo.rotate(30, Image.Resampling.BICUBIC, expand=True)
    for cx, cy in ((.25,.18),(.75,.18),(.5,.5),(.25,.82),(.75,.82)):
        x = max(0, min(image.width-logo.width, round(image.width*cx-logo.width/2)))
        y = max(0, min(image.height-logo.height, round(image.height*cy-logo.height/2)))
        image.alpha_composite(logo, (x, y))
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
