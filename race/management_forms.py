from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import Profile,Exercise
import math

class TeamForm(forms.Form):
    name=forms.CharField(label='Nombre completo',max_length=150)
    email=forms.EmailField(label='Correo electrónico')
    role=forms.ChoiceField(label='Rol',choices=[('athlete','Participante'),('coach','Coach'),('admin','Administrador')])
    sex=forms.ChoiceField(label='Categoría por sexo',required=False,choices=[('', 'Selecciona una categoría')]+Profile._meta.get_field('sex').choices,help_text='Solo para participantes. El peso y la categoría de peso se registran en cada evento.')
    active=forms.BooleanField(label='Acceso activo',required=False,initial=True)
    password=forms.CharField(label='Contraseña',required=False,strip=False,widget=forms.PasswordInput,help_text='Al editar, déjala vacía para conservar la contraseña actual.')
    password_confirm=forms.CharField(label='Confirmar contraseña',required=False,strip=False,widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))
    def __init__(self,*args,account=None,**kwargs):
        self.account=account
        super().__init__(*args,**kwargs)
        self.order_fields(['role','name','email','sex','active','password','password_confirm'])
        self.fields['password'].widget.attrs['autocomplete']='new-password'
        self.participant=(self.data.get('role') if self.is_bound else self.initial.get('role','athlete'))=='athlete'
        if account is None:
            self.fields.pop('active')
            self.fields['password'].required=True
            self.fields['password_confirm'].required=True
            self.fields['password'].help_text='Mínimo 8 caracteres. Evita contraseñas comunes o solo numéricas.'
        else:
            self.fields['password'].label='Nueva contraseña'
            self.fields['password_confirm'].label='Confirmar nueva contraseña'
            self.fields['password'].help_text='Deja ambos campos vacíos para conservar la contraseña actual.'
        self.fields['sex'].required=self.participant
    def clean(self):
        d=super().clean()
        if d.get('role')!='athlete':d['sex']=''
        if d.get('password','')!=d.get('password_confirm',''):
            self.add_error('password_confirm','Las contraseñas no coinciden. Escríbelas de nuevo.')
        return d
    def clean_email(self):
        email=self.cleaned_data['email'].strip().lower()
        existing=User.objects.filter(Q(email__iexact=email)|Q(username__iexact=email))
        if self.account:existing=existing.exclude(pk=self.account.pk)
        if existing.exists():raise forms.ValidationError('Este correo ya pertenece a otra cuenta.')
        return email
    def clean_password(self):
        value=self.cleaned_data.get('password')
        if value:validate_password(value,user=self.account)
        return value

class CatalogForm(forms.ModelForm):
    higher=forms.TypedChoiceField(label='Mejor resultado',choices=[('True','Mayor marca'),('False','Menor marca / tiempo')],coerce=lambda v:v=='True')
    class Meta:
        model=Exercise
        fields=['name','unit','capacity','higher','base','elite']
        labels={'name':'Nombre de la prueba','unit':'Unidad','capacity':'Capacidad','base':'Base · 50 puntos','elite':'Élite · 100 puntos'}
        help_texts={'unit':'Por ejemplo: reps, seg, m o cm.','base':'Puedes dejar ambas referencias vacías y definirlas en el evento.'}
    def clean(self):
        d=super().clean();base=d.get('base');elite=d.get('elite')
        if (base is None)!=(elite is None):raise forms.ValidationError('Completa ambas referencias o deja ambas vacías.')
        if base is not None and elite is not None:
            if not all(math.isfinite(x) and x>=0 for x in [base,elite]):raise forms.ValidationError('Las referencias deben ser números finitos no negativos.')
            if (d.get('higher') and elite<=base) or (not d.get('higher') and elite>=base):raise forms.ValidationError('La referencia élite debe ser mejor que la base según la dirección elegida.')
        return d
