from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Profile, Event

class BirthDateField(forms.DateField):
    def __init__(self,*args,**kwargs):
        kwargs['widget']=forms.DateInput(format='%d/%m/%Y',attrs={'placeholder':'dd/mm/aaaa','inputmode':'numeric','maxlength':10})
        kwargs['input_formats']=['%d/%m/%Y','%Y-%m-%d']
        super().__init__(*args,**kwargs)
    def to_python(self,value):
        if isinstance(value,str) and value.isdigit() and len(value)==8:value=f'{value[:2]}/{value[2:4]}/{value[4:]}'
        return super().to_python(value)
    def validate(self,value):
        super().validate(value)
        from django.utils import timezone
        if value and value>timezone.localdate():raise forms.ValidationError('La fecha de nacimiento no puede estar en el futuro.')

class SignupForm(forms.Form):
    field_order=['name','paternal','maternal','email','sex','birth_date','password','password_confirm']
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'}),help_text='Necesaria para eventos con edad mínima.')
    name=forms.CharField(label='Nombre(s)',max_length=150)
    paternal=forms.CharField(label='Apellido paterno',max_length=74,required=False)
    maternal=forms.CharField(label='Apellido materno',max_length=74,required=False)
    email=forms.EmailField(label='Correo electrónico')
    sex=forms.ChoiceField(label='Género',choices=[('M','Hombre'),('F','Mujer')])
    password=forms.CharField(label='Contraseña',strip=False,widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}),validators=[validate_password])
    password_confirm=forms.CharField(label='Confirmar contraseña',strip=False,widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))
    def clean(self):
        data=super().clean()
        if data.get('password','')!=data.get('password_confirm',''):
            self.add_error('password_confirm','Las contraseñas no coinciden. Escríbelas de nuevo.')
        return data
    def clean_email(self):
        email=self.cleaned_data['email'].lower()
        if User.objects.filter(username=email).exists(): raise forms.ValidationError('Este correo ya tiene cuenta. Inicia sesión o recupera tu contraseña.')
        return email

class EventForm(forms.ModelForm):
    capacity=forms.IntegerField(label='Cupo de participantes',required=False,min_value=1,help_text='Déjalo vacío mientras lo confirma el organizador. Es obligatorio para publicar.')
    price=forms.DecimalField(label='Precio de inscripción · MXN',min_value=0,max_digits=9,decimal_places=2)
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for key in ['date','registration_end']:
            self.fields[key].widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M',attrs={'placeholder':'dd/mm/aaaa HH:MM'})
            self.fields[key].input_formats=['%d/%m/%Y %H:%M',*self.fields[key].input_formats]
        if not self.is_bound and self.instance and not self.instance.capacity:self.initial['capacity']=''
        if not self.is_bound: self.initial['price']=self.instance.price/100 if self.instance and self.instance.pk else ''
    def clean_price(self): return int(self.cleaned_data['price']*100)
    class Meta:
        model=Event
        fields=['name','description','location','date','registration_end','price','capacity','allow_onsite']
        labels={'name':'Nombre del evento','description':'Descripción del desafío','location':'Sede','date':'Fecha del evento','registration_end':'Cierre de inscripciones','price':'Precio · MXN','capacity':'Cupo de participantes','allow_onsite':'Permitir inscripción presencial durante competencia','demo':'Evento de pruebas (datos no oficiales)'}
        widgets={'description':forms.Textarea(attrs={'rows':3}),'date':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M'),'registration_end':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M')}
    def clean(self):
        data=super().clean()
        data['capacity']=data.get('capacity') or 0
        if data.get('date') and data.get('registration_end') and data['registration_end']>data['date']: self.add_error('registration_end','Debe ser anterior al evento.')
        return data

class OriginalPhotoMixin(forms.Form):
    original_photo=forms.FileField(required=False,widget=forms.FileInput(attrs={'hidden':True,'accept':'image/jpeg,image/png,image/webp'}))
    def clean_original_photo(self):
        from .photos import validate_photo
        return validate_photo(self.cleaned_data.get('original_photo'))
    def clean(self):
        data=super().clean()
        from django.core.files.uploadedfile import UploadedFile,SimpleUploadedFile
        from .portrait import sports_photo
        photo=data.get('photo')
        if isinstance(photo,UploadedFile) and not self.errors:
            original=data.get('original_photo') or photo
            try:
                data['photo']=SimpleUploadedFile('retrato-deportivo.jpg',sports_photo(original),content_type='image/jpeg')
                data['original_photo']=original
            except forms.ValidationError as exc:self.add_error('photo',exc)
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Portrait processing failed during save')
                self.add_error('photo','No se pudo preparar la foto. Intenta de nuevo; no se guardó una foto sin acabado deportivo.')
        return data

class PhotoForm(OriginalPhotoMixin,forms.ModelForm):
    sex=forms.ChoiceField(label='Género',choices=[('M','Hombre'),('F','Mujer')])
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    class Meta:
        model=Profile
        fields=['photo','sex','birth_date']
        labels={'photo':'Foto de perfil','sex':'Género'}
        widgets={'photo':forms.ClearableFileInput(attrs={'accept':'image/jpeg,image/png,image/webp'})}
    def clean_photo(self):
        from .photos import validate_photo
        from django.core.files.uploadedfile import UploadedFile
        photo=self.cleaned_data['photo']
        return validate_photo(photo) if isinstance(photo,UploadedFile) else photo

class ParticipantPhotoForm(OriginalPhotoMixin,forms.ModelForm):
    class Meta:
        model=Profile
        fields=['photo']
        labels={'photo':'Foto de perfil'}
        widgets={'photo':forms.ClearableFileInput(attrs={'accept':'image/jpeg,image/png,image/webp'})}
    def clean_photo(self):
        from .photos import validate_photo
        from django.core.files.uploadedfile import UploadedFile
        photo=self.cleaned_data['photo']
        return validate_photo(photo) if isinstance(photo,UploadedFile) else photo
