from django import forms
from django.utils import timezone
from .event_policy import instant

class PolicyForm(forms.Form):
    minimum_age=forms.IntegerField(label='Edad mínima al día del evento',min_value=0,max_value=120,initial=0)
    maximum_age=forms.IntegerField(label='Edad máxima (vacío = sin límite)',min_value=0,max_value=120,required=False)
    registration_start=forms.DateTimeField(label='Apertura de inscripciones',required=False)
    reception_start=forms.DateTimeField(label='Apertura de recepción',required=False)
    reception_end=forms.DateTimeField(label='Cierre de recepción',required=False)
    event_end=forms.DateTimeField(label='Fin del evento',required=False)
    ordered_stations=forms.BooleanField(label='Exigir el orden de estaciones',required=False)
    online_payments=forms.BooleanField(label='Permitir inscripción y pago en línea',required=False)
    judging_standard=forms.CharField(label='Criterios de evaluación acordados con los jueces',required=False,widget=forms.Textarea(attrs={'rows':3}))
    regulations=forms.CharField(label='Reglamento',required=False,widget=forms.Textarea(attrs={'rows':4}))
    benefits=forms.CharField(label='La inscripción incluye',required=False,widget=forms.Textarea(attrs={'rows':3}))
    registration_channels=forms.CharField(label='Canales de inscripción y contacto',required=False,widget=forms.Textarea(attrs={'rows':2}))
    def __init__(self,*args,rules=None,**kwargs):
        rules=rules or {};initial={key:rules.get(key) for key in self.base_fields if key in rules}
        initial.setdefault('minimum_age',0)
        for key in ['registration_start','reception_start','reception_end','event_end']:
            if initial.get(key):initial[key]=timezone.localtime(instant(initial[key]))
        super().__init__(*args,initial=initial,**kwargs)
        for field in self.fields.values():
            if isinstance(field,forms.DateTimeField):field.widget=forms.DateTimeInput(attrs={'type':'datetime-local'},format='%Y-%m-%dT%H:%M')
    def apply(self,rules):
        for key,value in self.cleaned_data.items():rules[key]=value.isoformat() if hasattr(value,'isoformat') else value
        return rules
