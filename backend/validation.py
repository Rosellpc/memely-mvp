from datetime import date
from decimal import Decimal, InvalidOperation

from flask import request
from werkzeug.exceptions import BadRequest


def body():
    data = request.get_json()
    if not isinstance(data, dict):
        raise BadRequest('Envía un objeto JSON.')
    return data


def text_value(data, key, minimum=1, maximum=100):
    value = data.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise BadRequest(f'{key}: escribe entre {minimum} y {maximum} caracteres.')
    return value.strip()


def email_value(data):
    value = text_value(data, 'email', 3, 254).lower()
    parts = value.split('@')
    if len(parts) != 2 or not all(parts) or any(c.isspace() for c in value) or '.' not in parts[1]:
        raise BadRequest('Escribe un correo válido, por ejemplo ana@example.com.')
    return value


def password_value(data):
    value = data.get('password')
    if not isinstance(value, str) or not 15 <= len(value) <= 128:
        raise BadRequest('La contraseña debe tener entre 15 y 128 caracteres.')
    return value


def choice(data, key, options):
    value = data.get(key)
    if value not in options:
        raise BadRequest(f'{key}: selecciona una opción válida.')
    return value


def date_value(data, key):
    try:
        value = data.get(key)
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise BadRequest(f'{key}: usa una fecha válida con formato AAAA-MM-DD.') from None


def decimal_value(data, key, maximum):
    value = data.get(key)
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError
        number = Decimal(str(value))
        if not number.is_finite() or not 0 < number <= Decimal(maximum):
            raise ValueError
        if number != number.quantize(Decimal('0.01')):
            raise ValueError
        return number
    except (InvalidOperation, ValueError):
        raise BadRequest(f'{key}: usa un valor positivo, hasta {maximum}, con máximo dos decimales.') from None
