"""Integración real con Twilio (SMS).

Separado a propósito del puente SMS/USSD simulado (`app/routes/sms.py`):
este módulo SOLO habla con la API/SDK de Twilio (enviar, validar firmas de
webhook, normalizar números). La lógica de negocio (comandos REGISTRO,
TRANSPORTE, AYUDA, validaciones) sigue viviendo en `app/routes/sms.py` y es
compartida entre el simulador interno (JSON, `/sms/entrante`) y el webhook
real de Twilio (`/sms/webhook/twilio`) — el USSD simulado no se toca ni se
mezcla con esto: Twilio aquí es exclusivamente el canal SMS.

Controlado por la variable de entorno TWILIO_ENABLED (por defecto "false").
Con TWILIO_ENABLED=false, `enviar_sms()` no hace ninguna llamada de red y
devuelve de inmediato ok=False — así el resto de la app (alertas de cosecha,
logística) puede invocarlo siempre, sin condicionales dispersos, y sin que
falle nada mientras no haya credenciales reales configuradas.

Nunca se leen ni se registran credenciales en logs. El Auth Token solo se
lee desde variables de entorno (`backend/.env`, que está en .gitignore).
"""

import logging
import os

logger = logging.getLogger("palma_viva.twilio")

_client = None
_client_intentado = False


def twilio_habilitado() -> bool:
    return os.environ.get("TWILIO_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def credenciales_configuradas() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID")) and bool(os.environ.get("TWILIO_AUTH_TOKEN"))


def remitente_configurado():
    return os.environ.get("TWILIO_PHONE_NUMBER") or None


def _get_client():
    """Crea el cliente de Twilio de forma perezosa y segura: si falta algo
    (no habilitado, sin credenciales, SDK no disponible) devuelve None en
    vez de lanzar, para que el resto de la app nunca se caiga por esto."""
    global _client, _client_intentado
    if _client is not None:
        return _client
    if _client_intentado:
        return None
    _client_intentado = True

    if not twilio_habilitado() or not credenciales_configuradas():
        return None

    try:
        from twilio.rest import Client

        _client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        return _client
    except Exception as e:
        logger.error("No se pudo inicializar el cliente de Twilio: %s", e)
        return None


def enviar_sms(to_e164: str, body: str) -> dict:
    """Envía un SMS real vía Twilio. NUNCA lanza excepción: siempre devuelve
    {"ok": bool, "sid": str|None, "error": str|None, "estado": str}."""
    if not twilio_habilitado():
        return {"ok": False, "sid": None, "error": "Twilio deshabilitado (TWILIO_ENABLED=false).", "estado": "deshabilitado"}

    if not credenciales_configuradas():
        return {"ok": False, "sid": None, "error": "Faltan TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN.", "estado": "sin_credenciales"}

    client = _get_client()
    if client is None:
        return {"ok": False, "sid": None, "error": "No se pudo inicializar el cliente de Twilio.", "estado": "error_cliente"}

    remitente = remitente_configurado()
    if not remitente:
        return {"ok": False, "sid": None, "error": "Falta TWILIO_PHONE_NUMBER.", "estado": "sin_remitente"}

    if not to_e164:
        return {"ok": False, "sid": None, "error": "Número de destino inválido.", "estado": "destino_invalido"}

    try:
        mensaje = client.messages.create(to=to_e164, from_=remitente, body=body)
        return {"ok": True, "sid": mensaje.sid, "error": None, "estado": mensaje.status or "queued"}
    except Exception as e:
        # Cubre TwilioRestException (número no verificado en cuenta trial,
        # remitente inválido, saldo, geo-permisos, etc.) y errores de red.
        logger.warning("Error enviando SMS a %s: %s", to_e164, e)
        return {"ok": False, "sid": None, "error": str(e), "estado": "error"}


def validar_firma(url: str, params: dict, signature: str) -> bool:
    """Valida la cabecera X-Twilio-Signature de una petición entrante
    (webhook o status callback). Devuelve False ante cualquier problema
    (sin auth token, SDK no disponible, firma ausente o inválida) — nunca
    lanza, y el llamador debe tratar False como "rechazar la petición"."""
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token or not signature:
        return False
    try:
        from twilio.request_validator import RequestValidator

        return RequestValidator(auth_token).validate(url, params, signature)
    except Exception as e:
        logger.warning("Error validando firma de Twilio: %s", e)
        return False


# --- Normalización de números para Colombia (+57) -----------------------
# El proyecto es específico para Tumaco, Nariño (Colombia); los teléfonos se
# guardan en Usuario.telefono sin indicativo (ej. "3001234567"). Twilio
# entrega/espera formato E.164 (ej. "+573001234567").

def a_e164_co(telefono_local: str) -> str:
    t = (telefono_local or "").strip().replace(" ", "").replace("-", "")
    if t.startswith("+"):
        return t
    if t.startswith("57") and len(t) == 12:
        return f"+{t}"
    return f"+57{t}"


def desde_e164_co(telefono_e164: str) -> str:
    t = (telefono_e164 or "").strip()
    if t.startswith("+57") and len(t) == 13:
        return t[3:]
    if t.startswith("57") and len(t) == 12:
        return t[2:]
    return t.lstrip("+")
