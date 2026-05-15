# envios/validators.py
import re
from django.core.exceptions import ValidationError


def validar_peso_positivo(value):
    """El peso debe ser mayor a 0"""
    if value <= 0:
        raise ValidationError(f'El peso debe ser mayor a 0. Recibió: {value} kg')


def validar_codigo_encomienda(value):
    """El código debe empezar con ENC-"""
    if not value.startswith('ENC-'):
        raise ValidationError('El código de encomienda debe comenzar con ENC-')


def validar_nro_doc_dni(value):
    """El DNI debe tener exactamente 8 dígitos numéricos"""
    if not value.isdigit() or len(value) != 8:
        raise ValidationError('El DNI debe contener exactamente 8 dígitos numéricos')


def validar_telefono_peru(value):
    """Valida que sea un teléfono peruano: 9 dígitos comenzando con 9 (móvil) o 7 dígitos (fijo Lima)."""
    if not value:
        return
    cleaned = re.sub(r'[\s\-]', '', value)
    if not cleaned.isdigit():
        raise ValidationError('El teléfono solo debe contener dígitos')
    if len(cleaned) == 9:
        if not cleaned.startswith('9'):
            raise ValidationError('Los celulares peruanos comienzan con 9 (Ej: 999888777)')
    elif len(cleaned) == 7:
        if not cleaned[0] in '12345':
            raise ValidationError('Teléfono fijo de Lima inválido')
    else:
        raise ValidationError('Debe tener 9 dígitos (celular) o 7 dígitos (fijo Lima)')


def validar_ruc(value):
    """Valida formato de RUC peruano: 11 dígitos comenzando con 10 (persona) o 20 (empresa)."""
    if not value.isdigit() or len(value) != 11:
        raise ValidationError('El RUC debe tener exactamente 11 dígitos')
    if not value[:2] in ('10', '15', '17', '20'):
        raise ValidationError('El RUC debe comenzar con 10, 15, 17 o 20')
