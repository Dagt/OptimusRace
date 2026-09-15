from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Profile, Event

class BirthDateField(forms.DateField):
    def validate(self,value):
        super().validate(value)
        from django.utils import timezone
        if value and value>timezone.localdate():raise forms.ValidationError('La fecha de nacimiento no puede estar en el futuro.')

class SignupForm(forms.Form):
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'}),help_text='Necesaria para eventos con edad mínima.')
    name=forms.CharField(label='Nombre completo',max_length=150)
    email=forms.EmailField(label='Correo electrónico')
    sex=forms.ChoiceField(label='Categoría por sexo',choices=Profile._meta.get_field('sex').choices)
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
        if not self.is_bound and self.instance and not self.instance.capacity:self.initial['capacity']=''
        if not self.is_bound: self.initial['price']=self.instance.price/100 if self.instance and self.instance.pk else ''
    def clean_price(self): return int(self.cleaned_data['price']*100)
    class Meta:
        model=Event
        fields=['name','description','location','date','registration_end','price','capacity','allow_onsite','demo']
        labels={'name':'Nombre del evento','description':'Descripción del desafío','location':'Sede','date':'Fecha del evento','registration_end':'Cierre de inscripciones en línea','price':'Precio · MXN','capacity':'Cupo de participantes','allow_onsite':'Permitir inscripción presencial durante competencia','demo':'Evento de pruebas (sin cobros reales)'}
        widgets={'description':forms.Textarea(attrs={'rows':3}),'date':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M'),'registration_end':forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M')}
    def clean(self):
        data=super().clean()
        data['capacity']=data.get('capacity') or 0
        if data.get('date') and data.get('registration_end') and data['registration_end']>data['date']: self.add_error('registration_end','Debe ser anterior al evento.')
        return data

class PhotoForm(forms.ModelForm):
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    class Meta:
        model=Profile
        fields=['photo','sex','birth_date']
        labels={'photo':'Foto de perfil','sex':'Sexo para nuevas inscripciones'}
    def clean_photo(self):
        image=self.cleaned_data['photo']
        if image and image.size>5*1024*1024: raise forms.ValidationError('La foto debe pesar menos de 5 MB.')
        return image
