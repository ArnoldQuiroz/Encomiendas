from django.core.exceptions import ValidationError

def validar_peso_positivo(value):
    if float(value) <= 0:
        raise ValidationError(f'El peso debe ser mayor a 0. Recibió: {value} kg')

def validar_codigo_encomienda(value):
    if not str(value).startswith('ENC-'):
        raise ValidationError('El código de encomienda debe comenzar con ENC-')