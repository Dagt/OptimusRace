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
                if image.width*image.height>MAX_PIXELS:raise ValidationError('La foto es demasiado grande. Usa una versiÃ³n de hasta 25 megapÃ­xeles.')
                image.verify()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValidationError('No se pudo leer la foto. Elige una imagen JPG, PNG o WebP vÃ¡lida.')
    finally:upload.seek(0)
    return upload

def normalized_photo(upload,limit=1000):
    validate_photo(upload)
    with Image.open(upload) as source:
        image=ImageOps.exif_transpose(source).convert('RGB')
        if limit:image.thumbnail((limit,limit))
        out=BytesIO();image.save(out,format='JPEG',quality=92)
    upload.seek(0)
    return ContentFile(out.getvalue())

def save_photo(profile,upload,original=None):
    if upload is False:
        profile.photo='';profile.original_photo='';profile.save(update_fields=['photo','original_photo']);return
    if not upload:return
    # Validate both before storing either; preserve photographic content without EXIF metadata.
    photo=normalized_photo(upload);source=normalized_photo(original or upload,limit=None)
    profile.original_photo.save(f'{uuid.uuid4()}.jpg',source,save=False)
    profile.photo.save(f'{uuid.uuid4()}.jpg',photo,save=False)
    profile.save(update_fields=['photo','original_photo'])
