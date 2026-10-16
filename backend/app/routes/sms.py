"""Puente SMS/USSD (MOCK).

No hay un proveedor real (Twilio u otro) conectado todavía porque requiere
credenciales externas que no están disponibles en este entorno. Este módulo
simula el extremo receptor de un gateway SMS/USSD: un operador móvil
entregaría el mensaje del usuario a este mismo endpoint. La autenticación es
por número de teléfono registrado (igual que un USSD real, donde el operador
ya verificó la línea), no por JWT, porque el escenario objetivo es un
palmicultor SIN datos móviles ni sesión abierta en la app.

Comandos soportados (separados por espacios):
  REGISTRO <codigo_lote> <palmas_evaluadas> <palmas_improductivas> <racimos_totales> <peso_promedio_kg>
  TRANSPORTE <codigo_lote> <cantidad_toneladas> <fecha AAAA-MM-DD>
  AYUDA
"""

from datetime import date

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Usuario, Lote, Finca, RegistroProduccion, SolicitudTransporte, SmsUssdLog
from app.utils import role_required

sms_bp = Blueprint("sms", __name__)

AYUDA_TEXTO = (
    "Comandos disponibles:\n"
    "REGISTRO <lote> <palmasEvaluadas> <palmasImproductivas> <racimos> <pesoPromedioKg>\n"
    "TRANSPORTE <lote> <toneladas> <fechaAAAA-MM-DD>\n"
    "AYUDA"
)


@sms_bp.post("/sms/entrante")
def sms_entrante():
    data = request.get_json(force=True) or {}
    telefono = (data.get("telefono") or "").strip()
    canal = data.get("canal") if data.get("canal") in ("sms", "ussd") else "sms"
    mensaje = (data.get("mensaje") or "").strip()

    if not telefono or not mensaje:
        return jsonify({"message": "telefono y mensaje son obligatorios."}), 400

    usuario = Usuario.query.filter_by(telefono=telefono).first()
    comando = mensaje.split()[0].upper() if mensaje.split() else ""

    if not usuario:
        respuesta = "Número no registrado. Descarga la app Palma Viva o regístrate con un agente para usar SMS/USSD."
        _log(telefono, canal, comando, mensaje, respuesta, "error", None)
        return jsonify({"respuesta": respuesta}), 200

    if usuario.rol != "palmicultor":
        respuesta = "Esta función solo está disponible para cuentas de palmicultor."
        _log(telefono, canal, comando, mensaje, respuesta, "error", usuario.id)
        return jsonify({"respuesta": respuesta}), 200

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

    _log(telefono, canal, comando, mensaje, respuesta, estado, usuario.id)
    return jsonify({"respuesta": respuesta}), 200


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
            }
            for l in logs
        ]
    )


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


def _log(telefono, canal, comando, payload, respuesta, estado, usuario_id):
    db.session.add(
        SmsUssdLog(
            telefono=telefono,
            canal=canal,
            comando=comando,
            payload=payload,
            respuesta=respuesta,
            estado=estado,
            usuario_id=usuario_id,
        )
    )
    db.session.commit()
