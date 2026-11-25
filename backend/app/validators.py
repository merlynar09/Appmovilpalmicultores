"""DEV-F4-07 / F5-04: validadores simples compartidos por las rutas.

No hay librería de validación instalada en el proyecto — estas son
expresiones y chequeos mínimos, suficientes para rechazar entradas
claramente inválidas (y los desbordes de longitud que hoy llegan sin
filtro hasta Postgres) antes de persistir nada.
"""
import re

_TELEFONO_RE = re.compile(r"^[0-9+][0-9\s-]{6,19}$")
_CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def telefono_valido(telefono):
    return bool(telefono) and bool(_TELEFONO_RE.match(telefono.strip()))


def correo_valido(correo):
    return bool(correo) and bool(_CORREO_RE.match(correo.strip()))


def validar_numero_positivo(valor, nombre_campo):
    """Valida que `valor` (si viene) sea un número mayor que cero.

    Devuelve (valor_float, None) si es válido o ausente (None, None);
    devuelve (None, mensaje_de_error) si viene pero es inválido.
    """
    if valor is None or valor == "":
        return None, None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None, f"{nombre_campo} debe ser un número."
    if numero <= 0:
        return None, f"{nombre_campo} debe ser mayor que cero."
    return numero, None
