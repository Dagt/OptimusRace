from django import forms
from django.core.files.uploadedfile import UploadedFile
from .models import Participant
from .forms import OriginalPhotoMixin,BirthDateField
from .photos import validate_photo

class PersonForm(OriginalPhotoMixin,forms.ModelForm):
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    class Meta:
        model=Participant
        fields=['name','paternal','maternal','sex','birth_date','email','photo']
        labels={'name':'Nombre(s)','paternal':'Apellido paterno','maternal':'Apellido materno','sex':'Género','email':'Correo de contacto (opcional, privado)','photo':'Foto'}
        widgets={'photo':forms.ClearableFileInput(attrs={'accept':'image/jpeg,image/png,image/webp'})}
    def clean_photo(self):
        photo=self.cleaned_data.get('photo')
        return validate_photo(photo) if isinstance(photo,UploadedFile) else photo

class DeskForm(PersonForm):
    weight=forms.FloatField(label='Peso medido al inscribirse · kg',min_value=.01)
    batch=forms.IntegerField(label='Lote / grupo',min_value=1,initial=1)
    discount_code=forms.CharField(label='Código de descuento (opcional)',max_length=40,required=False)
    amount=forms.DecimalField(label='Importe cobrado en efectivo · MXN',min_value=0,max_digits=9,decimal_places=2)
    def clean(self):
        data=super().clean()
        if not data.get('photo'):self.add_error('photo','Toma o selecciona la foto del participante para completar la inscripción.')
        return data
