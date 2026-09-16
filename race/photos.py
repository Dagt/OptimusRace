"""Validate uploads and normalize profile photos without preserving metadata."""
import uuid,warnings
from io import BytesIO
from PIL import Image,ImageOps,UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

MAX_BYTES=5*1024*1024
MAX_PIXELS=25000000

def validate_photo(upload):
    if not upload or upload is False:return upload
    if upload.size>MAX_BYTES:raise ValidationError('La foto debe pesar menos de 5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as image:
                if image.format not in ['JPEG','PNG','WEBP']:raise ValidationError('Usa una imagen JPG, PNG o WebP.')
                if image.width*image.height>MAX_PIXELS:raise ValidationError('La foto es demasiado grande. Usa una versión de hasta 25 megapíxeles.')
                image.verify()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValidationError('No se pudo leer la foto. Elige una imagen JPG, PNG o WebP válida.')
    finally:upload.seek(0)
    return upload

def save_photo(profile,upload):
    if upload is False:
        profile.photo='';profile.save(update_fields=['photo']);return
    if not upload:return
    validate_photo(upload)
    with Image.open(upload) as source:
        image=ImageOps.exif_transpose(source).convert('RGB');image.thumbnail((1000,1000));out=BytesIO();image.save(out,format='JPEG',quality=88)
    profile.photo.save(f'{uuid.uuid4()}.jpg',ContentFile(out.getvalue()))
