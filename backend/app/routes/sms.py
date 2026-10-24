"""Puente SMS/USSD.

Dos orígenes totalmente separados que comparten la MISMA lógica de negocio
(comandos, validaciones, operaciones):

1. `/sms/entrante` — MOCK interno (JSON, sin firma). Lo usa el simulador
   SMS/USSD de la app (pantalla "Simulador SMS/USSD") para probar los
   comandos sin depender de un operador real. Sirve tanto para "sms" como
   para "ussd" simulados — el USSD real sigue sin proveedor conectado.

2. `/sms/webhook/twilio` — webhook REAL de Twilio (form-urlencoded, firma
   X-Twilio-Signature validada). Solo atiende el canal SMS: Twilio no provee
   USSD, así que esto nunca toca el flujo "ussd" simulado.

Comandos soportados (separados por espacios):
  REGISTRO <codigo_lote> <palmas_evaluadas> <palmas_improductivas> <racimos_totales> <peso_promedio_kg>
  TRANSPORTE <codigo_lote> <cantidad_toneladas> <fecha AAAA-MM-DD>
  AYUDA
"""

import logging
import os
from datetime import date

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Usuario, Lote, Finca, RegistroProduccion, SolicitudTransporte, SmsUssdLog
from app.utils import role_required
from app.services.twilio_sms import (
    a_e164_co,
    desde_e164_co,
    enviar_sms,
    twilio_habilitado,
    validar_firma,
)
from app.services.contenido import obtener_contenido

sms_bp = Blueprint("sms", __name__)
logger = logging.getLogger("palma_viva.sms")

AYUDA_TEXTO_DEFECTO = (
    "Comandos disponibles:\n"
    "REGISTRO <lote> <palmasEvaluadas> <palmasImproductivas> <racimos> <pesoPromedioKg>\n"
    "TRANSPORTE <lote> <toneladas> <fechaAAAA-MM-DD>\n"
    "AYUDA"
)

# Ver nota en app/services/ussd_engine.py: este nombre se reasigna en cada
# llamada a _procesar_mensaje() para reflejar ediciones del administrador
# (CU17) sin reiniciar el servidor, con fallback seguro al texto de arriba.
AYUDA_TEXTO = AYUDA_TEXTO_DEFECTO


# ------------------------------------------------------- mock interno ----

@sms_bp.post("/sms/entrante")
def sms_entrante():
    data = request.get_json(force=True) or {}
    telefono = (data.get("telefono") or "").strip()
    canal = data.get("canal") if data.get("canal") in ("sms", "ussd") else "sms"
    mensaje = (data.get("mensaje") or "").strip()

    if not telefono or not mensaje:
        return jsonify({"message": "telefono y mensaje son obligatorios."}), 400

    respuesta, _estado, _usuario = _procesar_mensaje(telefono, mensaje, canal, proveedor="mock")
    return jsonify({"respuesta": respuesta}), 200


# -------------------------------------------------- webhooks de Twilio ---

@sms_bp.post("/sms/webhook/twilio")
def sms_webhook_twilio():
    """Webhook real de SMS entrante de Twilio. Responde con TwiML (Twilio
    envía ese contenido como la respuesta SMS automáticamente, sin gastar
    una llamada REST aparte). Siempre responde 200 con TwiML válido —
    incluso ante errores internos— para evitar que Twilio reintente la
    entrega y duplique el procesamiento."""
    if not _firma_valida(request.form.to_dict()):
        logger.warning("Firma de Twilio inválida en webhook entrante.")
        return ("Firma inválida.", 403)

    message_sid = request.form.get("MessageSid") or request.form.get("SmsMessageSid")
    desde = request.form.get("From", "")
    mensaje = (request.form.get("Body") or "").strip()
    telefono = desde_e164_co(desde)

    # Idempotencia: si Twilio reintenta la entrega del mismo mensaje
    # (MessageSid repetido), no se vuelve a procesar ni a duplicar efectos
    # (p. ej. un segundo censo de producción) — se responde lo mismo que la
    # primera vez.
    if message_sid:
        previo = SmsUssdLog.query.filter_by(twilio_sid=message_sid).first()
        if previo:
            return _twiml(previo.respuesta or "")

    respuesta, _estado, _usuario = _procesar_mensaje(
        telefono, mensaje, canal="sms", proveedor="twilio", twilio_sid=message_sid
    )
    return _twiml(respuesta)


@sms_bp.post("/sms/webhook/estado")
def sms_webhook_estado():
    """StatusCallback de Twilio: actualiza el estado de entrega
    (queued/sent/delivered/undelivered/failed) de un SMS ya enviado o
    recibido, identificado por MessageSid."""
    if not _firma_valida(request.form.to_dict()):
        logger.warning("Firma de Twilio inválida en webhook de estado.")
        return ("Firma inválida.", 403)

    message_sid = request.form.get("MessageSid")
    nuevo_estado = request.form.get("MessageStatus")
    if message_sid and nuevo_estado:
        log = SmsUssdLog.query.filter_by(twilio_sid=message_sid).first()
        if log:
            log.estado_entrega = nuevo_estado
            db.session.commit()
    return ("", 204)


# -------------------------------------------------------- notificaciones -

def notificar_por_sms(usuario: Usuario, titulo: str, mensaje: str):
    """Envío best-effort de una notificación YA creada (alerta de cosecha o
    de logística) también por SMS real, cuando Twilio está configurado y
    habilitado. No es una regla de negocio nueva: solo agrega un canal de
    entrega a notificaciones que el sistema ya genera para ese usuario
    puntual — nunca se envía en bloque a todos los usuarios.

    Nunca lanza excepción: si Twilio falla o está deshabilitado, el flujo
    que llama a esta función (crear una alerta, aceptar un transporte,
    etc.) continúa normalmente."""
    if not usuario or not usuario.telefono or not twilio_habilitado():
        return
    try:
        cuerpo = f"Palma Viva - {titulo}: {mensaje}"[:300]
        resultado = enviar_sms(a_e164_co(usuario.telefono), cuerpo)
        _log(
            telefono=usuario.telefono,
            canal="sms",
            comando="ALERTA",
            payload=cuerpo,
            respuesta=cuerpo,
            estado="procesado" if resultado["ok"] else "error",
            usuario_id=usuario.id,
            direccion="saliente",
            proveedor="twilio",
            twilio_sid=resultado.get("sid"),
        )
    except Exception as e:
        logger.warning("No se pudo enviar SMS de alerta a usuario %s: %s", usuario.id, e)


# ----------------------------------------------------------- admin -------

@sms_bp.get("/sms/logs")
@role_required("administrador")
def listar_logs():
    logs = SmsUssdLog.query.order_by(SmsUssdLog.creado_en.desc()).limit(200).all()
    return jsonify(
        [
            {
                "id": l.id,
                "telefono": l.telefono,
                "canal": l.canal,
                "comando": l.comando,
                "payload": l.payload,
                "respuesta": l.respuesta,
                "estado": l.estado,
                "usuario_id": l.usuario_id,
                "creado_en": l.creado_en.isoformat() if l.creado_en else None,
                "direccion": l.direccion,
                "proveedor": l.proveedor,
                "twilio_sid": l.twilio_sid,
                "estado_entrega": l.estado_entrega,
            }
            for l in logs
        ]
    )


# --------------------------------------------------------- lógica común --

def _procesar_mensaje(telefono, mensaje, canal, proveedor, twilio_sid=None):
    """Lógica compartida por el mock interno y el webhook real de Twilio:
    busca el usuario, valida el rol y ejecuta el comando. Devuelve
    (respuesta, estado, usuario)."""
    global AYUDA_TEXTO
    AYUDA_TEXTO = obtener_contenido("sms_ayuda", AYUDA_TEXTO_DEFECTO)
    comando = mensaje.split()[0].upper() if mensaje.split() else ""
    usuario = Usuario.query.filter_by(telefono=telefono).first()

    if not usuario:
        respuesta = "Número no registrado. Descarga la app Palma Viva o regístrate con un agente para usar SMS/USSD."
        _log(telefono, canal, comando, mensaje, respuesta, "error", None, proveedor=proveedor, twilio_sid=twilio_sid)
        return respuesta, "error", None

    if usuario.rol != "palmicultor":
        respuesta = "Esta función solo está disponible para cuentas de palmicultor."
        _log(telefono, canal, comando, mensaje, respuesta, "error", usuario.id, proveedor=proveedor, twilio_sid=twilio_sid)
        return respuesta, "error", usuario

    try:
        if comando == "AYUDA" or not comando:
            respuesta = AYUDA_TEXTO
            estado = "procesado"
        elif comando == "REGISTRO":
            respuesta = _procesar_registro(usuario, mensaje.split()[1:], canal)
            estado = "procesado"
        elif comando == "TRANSPORTE":
            respuesta = _procesar_transporte(usuario, mensaje.split()[1:])
            estado = "procesado"
        else:
            respuesta = f"Comando no reconocido: {comando}. Envía AYUDA para ver las opciones."
            estado = "error"
    except ValueError as e:
        respuesta = f"Error: {e}"
        estado = "error"

    _log(telefono, canal, comando, mensaje, respuesta, estado, usuario.id, proveedor=proveedor, twilio_sid=twilio_sid)
    return respuesta, estado, usuario


def _procesar_registro(usuario: Usuario, args, canal):
    if len(args) < 5:
        raise ValueError("faltan datos. Formato: REGISTRO lote palmasEvaluadas palmasImproductivas racimos pesoPromedio")

    codigo_lote, palmas_evaluadas, palmas_improductivas, racimos, peso_promedio = args[:5]

    lote = (
        Lote.query.join(Finca)
        .filter(Finca.usuario_id == usuario.id, Lote.codigo == codigo_lote)
        .first()
    )
    if not lote:
        raise ValueError(f"no se encontró el lote '{codigo_lote}' en tus fincas")

    try:
        palmas_evaluadas = int(palmas_evaluadas)
        palmas_improductivas = int(palmas_improductivas)
        racimos = int(racimos)
        peso_promedio = float(peso_promedio)
    except ValueError:
        raise ValueError("los valores numéricos no son válidos")

    registro = RegistroProduccion(
        lote_id=lote.id,
        fecha=date.today(),
        palmas_evaluadas=palmas_evaluadas,
        palmas_improductivas=palmas_improductivas,
        racimos_totales=racimos,
        peso_promedio_racimo=peso_promedio,
        fuente=canal,
    )
    db.session.add(registro)
    db.session.commit()
    return f"Censo registrado para el lote {codigo_lote}. ID #{registro.id}. Gracias."


def _procesar_transporte(usuario: Usuario, args):
    if len(args) < 2:
        raise ValueError("faltan datos. Formato: TRANSPORTE lote toneladas [fecha AAAA-MM-DD]")

    codigo_lote = args[0]
    try:
        cantidad = float(args[1])
    except ValueError:
        raise ValueError("la cantidad de toneladas no es válida")

    fecha_servicio = None
    if len(args) >= 3:
        try:
            fecha_servicio = date.fromisoformat(args[2])
        except ValueError:
            raise ValueError("la fecha debe tener formato AAAA-MM-DD")

    lote = (
        Lote.query.join(Finca)
        .filter(Finca.usuario_id == usuario.id, Lote.codigo == codigo_lote)
        .first()
    )
    if not lote:
        raise ValueError(f"no se encontró el lote '{codigo_lote}' en tus fincas")

    finca = Finca.query.get(lote.finca_id)
    solicitud = SolicitudTransporte(
        palmicultor_id=usuario.id,
        finca_id=finca.id,
        lote_id=lote.id,
        cantidad_estimada=cantidad,
        origen=f"{finca.municipio}" + (f", {finca.vereda}" if finca.vereda else ""),
        fecha_servicio=fecha_servicio,
        observaciones="Solicitud creada vía SMS/USSD",
        estado="Pendiente",
    )
    db.session.add(solicitud)
    db.session.commit()
    return f"Solicitud de transporte #{solicitud.id} creada para el lote {codigo_lote}. Te avisaremos cuando un transportador la acepte."


def _firma_valida(form_params: dict) -> bool:
    url = _url_firmada()
    firma = request.headers.get("X-Twilio-Signature", "")
    return validar_firma(url, form_params, firma)


def _url_firmada() -> str:
    """URL que Twilio usó para firmar la petición. Si el servidor corre
    detrás de un túnel/proxy (ngrok, etc.) cuyo host externo difiere del que
    Flask ve internamente, se puede fijar TWILIO_WEBHOOK_BASE_URL con el
    origen público exacto (ej. https://abcd1234.ngrok-free.app)."""
    base = os.environ.get("TWILIO_WEBHOOK_BASE_URL")
    if base:
        qs = f"?{request.query_string.decode()}" if request.query_string else ""
        return base.rstrip("/") + request.path + qs
    return request.url


def _twiml(mensaje: str):
    from twilio.twiml.messaging_response import MessagingResponse

    resp = MessagingResponse()
    if mensaje:
        resp.message(mensaje)
    return str(resp), 200, {"Content-Type": "text/xml"}


def _log(telefono, canal, comando, payload, respuesta, estado, usuario_id, direccion="entrante", proveedor="mock", twilio_sid=None):
    db.session.add(
        SmsUssdLog(
            telefono=telefono,
            canal=canal,
            comando=comando,
            payload=payload,
            respuesta=respuesta,
            estado=estado,
            usuario_id=usuario_id,
            direccion=direccion,
            proveedor=proveedor,
            twilio_sid=twilio_sid,
        )
    )
    db.session.commit()
