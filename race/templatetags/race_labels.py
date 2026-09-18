from django import template
from django.utils.html import format_html
register=template.Library()
@register.simple_tag
def icon(name):
    return format_html('<svg class="icon" aria-hidden="true"><use href="/static/icons.svg#{}"></use></svg>',name)
@register.filter
def initials(name):return ''.join(part[0] for part in str(name).split()[:2]).upper() or 'OR'
@register.filter
def numeric(value):return '' if value is None else str(value)
@register.filter
def money(value):
    return f'{value/100:,.2f}'
@register.filter
def money_input(value):return f'{value/100:.2f}'
@register.filter
def state_label(value):
    return {'disqualified':'Descalificado','confirmed':'Confirmada','reserved':'Reservada · pago pendiente','expired':'Histórico sin inscripción','pending':'Pendiente','present':'Presente','absent':'Ausente','withdrawn':'Retirado','done':'Realizada','creating':'Creando Checkout','paid':'Pagado'}.get(value,value)

@register.filter
def capture_value(value,test):
    if value is None or value=='':return ''
    if test.get('parameters',{}).get('time_entry')=='minutes_seconds_dot':
        minutes,seconds=divmod(int(value),60)
        return f'{minutes}.{seconds:02d}'
    return str(value)
