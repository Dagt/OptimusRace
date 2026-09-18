"""Normalize explicit time entry formats to the station's stored seconds."""
import re
from decimal import Decimal
from django.core.exceptions import ValidationError


def supports_time_input(test):
    return test.get('unit', '').lower() in ('seg', 's', 'sec', 'segundos')


def time_seconds(value, time_format='seconds'):
    text = str(value).strip().replace(',', '.')
    decimal = r'[0-9]+(?:\.[0-9]+)?'
    if time_format == 'minutes_seconds':
        match = re.fullmatch(r'([0-9]+):(' + decimal + r')', text)
        if not match or Decimal(match[2]) >= 60:
            raise ValidationError('Usa minutos:segundos, por ejemplo 5:36.5. Los segundos deben ser menores a 60.')
        result = Decimal(match[1]) * 60 + Decimal(match[2])
    elif time_format in ('seconds', 'minutes'):
        if not re.fullmatch(decimal, text):
            raise ValidationError('Introduce un tiempo numérico en el formato seleccionado.')
        result = Decimal(text) * (60 if time_format == 'minutes' else 1)
    else:
        raise ValidationError('Formato de tiempo inválido.')
    if not result.is_finite() or result <= 0 or result > Decimal('1e12'):
        raise ValidationError('El tiempo debe ser mayor a cero y estar dentro del rango permitido.')
    return float(result)
