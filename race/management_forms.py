from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import Profile,Exercise
from .forms import BirthDateField
import math

class TeamForm(forms.Form):
    name=forms.CharField(label='Nombre completo',max_length=150)
    email=forms.EmailField(label='Correo electrónico')
    role=forms.ChoiceField(label='Rol',choices=[('athlete','Participante'),('coach','Coach'),('admin','Administrador')])
    sex=forms.ChoiceField(label='Categoría por sexo',required=False,choices=[('', 'Selecciona una categoría')]+Profile._meta.get_field('sex').choices,help_text='Solo para participantes. El peso y la categoría de peso se registran en cada evento.')
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),help_text='Para participantes: necesaria al inscribirse a eventos con edad mínima.')
    active=forms.BooleanField(label='Acceso activo',required=False,initial=True)
    password=forms.CharField(label='Contraseña',required=False,strip=False,widget=forms.PasswordInput,help_text='Al editar, déjala vacía para conservar la contraseña actual.')
    password_confirm=forms.CharField(label='Confirmar contraseña',required=False,strip=False,widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))
    def __init__(self,*args,account=None,**kwargs):
        self.account=account
        super().__init__(*args,**kwargs)
        self.order_fields(['role','name','email','sex','birth_date','active','password','password_confirm'])
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
    metric=forms.ChoiceField(label='Tipo de resultado',choices=[('time','Tiempo'),('repetitions','Repeticiones'),('distance','Distancia / altura'),('weight','Peso levantado'),('custom','Otro (unidad libre)')])
    duration_seconds=forms.FloatField(label='Duración del esfuerzo · segundos',required=False,min_value=.01,help_text='Opcional. Ejemplo: 60 para un minuto de burpees.')
    distance_meters=forms.FloatField(label='Distancia por recorrido · metros',required=False,min_value=.01)
    laps=forms.IntegerField(label='Número de recorridos',required=False,min_value=1,help_text='Ejemplo: distancia 10 y recorridos 10 para shuttle 10 × 10.')
    load_mode=forms.ChoiceField(label='Carga',choices=[('none','Sin carga prescrita'),('body_percent','Porcentaje del peso corporal'),('fixed','Peso fijo en kg')])
    load_value=forms.FloatField(label='Carga · porcentaje o kg según modalidad',required=False,min_value=.01)
    bar_weight=forms.FloatField(label='Peso de barra · kg',required=False,min_value=0)
    load_step=forms.FloatField(label='Incremento total de carga · kg',required=False,min_value=.01)
    round_mode=forms.ChoiceField(label='Redondeo de carga',choices=[('none','Sin redondeo'),('nearest','Más cercano'),('down','Hacia abajo'),('up','Hacia arriba')])
    precision=forms.IntegerField(label='Decimales permitidos en la marca',required=False,min_value=0,max_value=6)
    min_value=forms.FloatField(label='Marca mínima válida (opcional)',required=False,min_value=0)
    max_value=forms.FloatField(label='Marca máxima válida (opcional)',required=False,min_value=0)
    equipment=forms.CharField(label='Equipo permitido / necesario',required=False,widget=forms.Textarea(attrs={'rows':2}))
    instructions=forms.CharField(label='Protocolo y criterio de repetición válida',required=False,widget=forms.Textarea(attrs={'rows':4}))
    parameter_fields=['metric','duration_seconds','distance_meters','laps','load_mode','load_value','bar_weight','load_step','round_mode','precision','min_value','max_value','equipment','instructions']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not self.is_bound:
            self.initial.update(self.instance.parameters or {})
            self.initial.setdefault('metric','custom');self.initial.setdefault('load_mode','none');self.initial.setdefault('round_mode','none')
        self.order_fields(['name','capacity','metric','unit','higher',*self.parameter_fields[1:],'base','elite'])
    def sections(self):
        groups=[('1. ¿Qué va a registrar el coach?', 'La marca es el resultado medido. Por ejemplo: 24 repeticiones, 12.4 segundos o 180 centímetros.', ['name','capacity','metric','unit','higher'], False),
                ('2. ¿Cómo se realiza el ejercicio?', 'Opcional. La duración y el recorrido son condiciones de ejecución, no puntos. Puedes combinar ambas cuando el ejercicio lo requiera.', ['duration_seconds','distance_meters','laps','instructions','equipment'], True),
                ('3. ¿Debe utilizar una carga?', 'Opcional. Define el peso que debe usar el participante. El resultado a calificar sigue siendo la marca elegida en el paso 1.', ['load_mode','load_value','bar_weight','load_step','round_mode'], True),
                ('4. Límites de captura', 'Opcional. Evitan errores del coach; no determinan los puntos. Repeticiones siempre admite enteros.', ['precision','min_value','max_value'], True),
                ('5. Referencias para evaluación lineal', 'Solo si usarás una escala fija en el evento. Déjalas vacías para puntuación relativa al mejor y peor de cada categoría. Base equivale al 50% y élite al 100% del máximo.', ['base','elite'], True)]
        return [{'title':title,'help':help_text,'fields':[self[name] for name in names],'collapsed':collapsed and not any(self[name].errors for name in names)} for title,help_text,names,collapsed in groups]

    def save(self,commit=True):
        instance=super().save(commit=False)
        instance.parameters={key:self.cleaned_data.get(key) for key in self.parameter_fields}
        if commit:instance.save()
        return instance

    higher=forms.TypedChoiceField(label='Mejor resultado',choices=[('True','Mayor marca'),('False','Menor marca / tiempo')],coerce=lambda v:v=='True')
    class Meta:
        model=Exercise
        fields=['name','unit','capacity','higher','base','elite']
        labels={'name':'Nombre de la prueba','unit':'Unidad','capacity':'Capacidad','base':'Referencia base · 50%','elite':'Referencia élite · 100%'}
        help_texts={'unit':'Unidad de captura: seg, reps, cm, m, kg u otra. No se convierten unidades automáticamente.','base':'Referencias opcionales para evaluación lineal: base = 50% y élite = 100% del máximo de la estación. La puntuación se elige en cada evento.'}
    def clean(self):
        d=super().clean();base=d.get('base');elite=d.get('elite')
        if (base is None)!=(elite is None):raise forms.ValidationError('Completa ambas referencias o deja ambas vacías.')
        if base is not None and elite is not None:
            if not all(math.isfinite(x) and x>=0 for x in [base,elite]):raise forms.ValidationError('Las referencias deben ser números finitos no negativos.')
            if (d.get('higher') and elite<=base) or (not d.get('higher') and elite>=base):raise forms.ValidationError('La referencia élite debe ser mejor que la base según la dirección elegida.')
        from .exercise_parameters import validate_parameters
        if not self.errors:validate_parameters({key:d.get(key) for key in self.parameter_fields})
        return d
