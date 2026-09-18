from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import Profile,Exercise
from .forms import BirthDateField
import math

class TeamForm(forms.Form):
    name=forms.CharField(label='Nombre(s)',max_length=150)
    paternal=forms.CharField(label='Apellido paterno',max_length=74,required=False)
    maternal=forms.CharField(label='Apellido materno',max_length=74,required=False)
    email=forms.EmailField(label='Correo electrónico')
    role=forms.ChoiceField(label='Rol',choices=[('athlete','Participante'),('coach','Coach'),('admin','Administrador')])
    sex=forms.ChoiceField(label='Género',required=False,choices=[('', 'Selecciona el género')]+[('M','Hombre'),('F','Mujer')],help_text='Dato personal. La categoría de competencia se determina en el evento.')
    birth_date=BirthDateField(label='Fecha de nacimiento',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),help_text='Para participantes: necesaria al inscribirse a eventos con edad mínima.')
    active=forms.BooleanField(label='Acceso activo',required=False,initial=True)
    password=forms.CharField(label='Contraseña',required=False,strip=False,widget=forms.PasswordInput,help_text='Al editar, déjala vacía para conservar la contraseña actual.')
    password_confirm=forms.CharField(label='Confirmar contraseña',required=False,strip=False,widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))
    def __init__(self,*args,account=None,participant=False,**kwargs):
        self.account=account
        super().__init__(*args,**kwargs)
        self.order_fields(['role','name','paternal','maternal','email','sex','birth_date','active','password','password_confirm'])
        self.fields['password'].widget.attrs['autocomplete']='new-password'
        self.participant=participant
        self.fields['role'].choices=[('athlete','Participante')] if participant else [('admin','Administrador'),('coach','Coach')]
        if participant:
            self.fields['role'].initial='athlete'
            self.fields['role'].widget=forms.HiddenInput()
        else:
            self.fields.pop('sex');self.fields.pop('birth_date')
        if account is None:
            self.fields.pop('active')
            self.fields['password'].required=True
            self.fields['password_confirm'].required=True
            self.fields['password'].help_text='Mínimo 8 caracteres. Evita contraseñas comunes o solo numéricas.'
        else:
            self.fields['password'].label='Nueva contraseña'
            self.fields['password_confirm'].label='Confirmar nueva contraseña'
            self.fields['password'].help_text='Deja ambos campos vacíos para conservar la contraseña actual.'
        if participant:self.fields['sex'].required=True
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
    measurement=forms.ChoiceField(label='Resultado que registra el juez',required=False,choices=[('repetitions','Repeticiones'),('time','Tiempo · Segundos'),('time_minutes','Tiempo · Minutos'),('distance_cm','Distancia o altura en centímetros'),('distance_m','Distancia en metros'),('weight','Peso levantado en kg'),('custom','Otra medida')])
    measurement_defaults={'repetitions':('repetitions','reps',True),'time':('time','seg',False),'time_minutes':('time','seg',False),'distance_cm':('distance','cm',True),'distance_m':('distance','m',True),'weight':('weight','kg',True)}
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
    instructions=forms.CharField(label='Indicaciones para el juez (opcional)',required=False,widget=forms.Textarea(attrs={'rows':4}))
    parameter_fields=['metric','duration_seconds','distance_meters','laps','load_mode','load_value','bar_weight','load_step','round_mode','precision','min_value','max_value','equipment','instructions']
    def __init__(self,*args,**kwargs):
        instance=kwargs.get('instance')
        if args and args[0] is not None:
            data=args[0].copy()
            params=instance.parameters if instance else {}
            # Fields retired from the editor retain saved values; new exercises need none.
            for key in ['bar_weight','load_step','round_mode','precision','min_value','max_value','equipment']:
                if key not in data:data[key]=params.get(key) if params.get(key) is not None else ('none' if key=='round_mode' else '')
            for key in ['base','elite']:
                if key not in data:data[key]=getattr(instance,key,None) if instance else ''
            if data.get('measurement') in self.measurement_defaults:
                metric,unit,higher=self.measurement_defaults[data['measurement']]
                data['metric']=metric;data['unit']=unit
                if 'higher' not in data:data['higher']=str(higher)
            elif data.get('measurement')=='custom':data['metric']='custom'
            if data.get('load_mode')=='none':
                for key in ['load_value','bar_weight','load_step']:data[key]=''
                data['round_mode']='none'
            args=(data,*args[1:])
        super().__init__(*args,**kwargs)
        if not self.is_bound:
            self.initial.update(self.instance.parameters or {})
            self.initial.setdefault('load_mode','none');self.initial.setdefault('round_mode','none')
            self.initial['measurement']=next((key for key,(_,unit,_) in self.measurement_defaults.items() if unit==self.instance.unit),'custom') if self.instance.pk else 'repetitions'
            if self.instance.parameters.get('time_entry')=='minutes_seconds_dot':self.initial['measurement']='time_minutes'
            if not self.instance.pk:self.initial.update(unit='reps',higher=True)
        measurement=self.data.get('measurement') if self.is_bound else self.initial.get('measurement')
        if measurement in self.measurement_defaults:self.fields['unit'].widget.attrs['readonly']=True
    def sections(self):
        groups=[('La prueba', 'Elige qué medirá el juez. La unidad se obtiene del resultado seleccionado.', ['name','capacity','measurement','unit','higher']),
                ('Condiciones del ejercicio · opcionales', 'Deja vacío lo que no aplique. Duración y recorrido describen el ejercicio; no son la marca que se calificará.', ['duration_seconds','distance_meters','laps','load_mode','load_value','instructions'])]
        return [{'title':title,'help':help_text,'fields':[self[name] for name in names]} for title,help_text,names in groups]

    def save(self,commit=True):
        instance=super().save(commit=False)
        instance.parameters={**(instance.parameters or {}),**{key:self.cleaned_data.get(key) for key in self.parameter_fields}}
        if self.cleaned_data.get('measurement') in ['time','time_minutes']:
            instance.parameters['time_entry']='minutes_seconds_dot' if self.cleaned_data['measurement']=='time_minutes' else 'seconds'
        else:instance.parameters.pop('time_entry',None)
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
