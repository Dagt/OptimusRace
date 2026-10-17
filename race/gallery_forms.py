from django import forms
from django.core.exceptions import ValidationError

from .gallery import MAX_BATCH_BYTES, MAX_BATCH_FILES, MAX_PHOTO_BYTES
from .photos import validate_photo


class MultiplePhotoInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplePhotoField(forms.FileField):
    widget = MultiplePhotoInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else [data] if data else []
        if not files:
            raise ValidationError('Selecciona al menos una foto.')
        if len(files) > MAX_BATCH_FILES:
            raise ValidationError('Puedes subir hasta 20 fotos por envío.')
        if sum(file.size for file in files) > MAX_BATCH_BYTES:
            raise ValidationError('El envío completo debe pesar menos de 100 MB.')
        errors = []
        for file in files:
            try:
                super().clean(file, initial)
                validate_photo(file, max_bytes=MAX_PHOTO_BYTES)
            except ValidationError as exc:
                errors.append(f'{file.name}: {" ".join(exc.messages)}')
        if errors:
            raise ValidationError(errors)
        return files


class GalleryUploadForm(forms.Form):
    photos = MultiplePhotoField(
        label='Selecciona las fotos',
        widget=MultiplePhotoInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        help_text='JPG, PNG o WebP. Hasta 20 fotos por envío, 15 MB por foto y 100 MB en total.')
    caption = forms.CharField(label='Descripción (opcional)', max_length=200, required=False,
                              help_text='Se aplicará a todas las fotos de este envío.')
