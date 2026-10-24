from datetime import datetime, date, time

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt

from app.extensions import db
from app.models import (
    Vehiculo,
    SolicitudTransporte,
    Transportador,
    Finca,
    Lote,
    Comprador,
    EstadoVia,
    Notificacion,
    Usuario,
)
from app.utils import role_required, current_user_id
from app.routes.sms import notificar_por_sms

logistics_bp = Blueprint("logistics", __name__)

ESTADOS_VALIDOS = {
    "Pendiente",
    "Aceptada",
    "Rechazada",
    "En preparación",
    "En tránsito",
    "Entregada",
    "Cancelada",
}


@logistics_bp.get("/logistica/estado")
def estado_logistica():
    disponibles = Vehiculo.query.filter_by(disponible=True, estado="activo").count()
    ultimo = SolicitudTransporte.query.order_by(SolicitudTransporte.fecha_solicitud.desc()).first()
    via_afectada = EstadoVia.query.filter(EstadoVia.estado != "habilitada").first()
    return jsonify(
        {
            "vehiculosDisponibles": disponibles,
            "estadoVias": "Sin novedades en las rutas" if not via_afectada else f"{via_afectada.via}: {via_afectada.estado}",
            "ultimoDespacho": ultimo.estado if ultimo else "Sin despachos recientes",
        }
    )


# -------------------------------------------------------- transportador ---

@logistics_bp.get("/transportador/perfil")
@role_required("transportador")
def perfil_transportador():
    t = _get_own_transportador()
    if not t:
        return jsonify({"message": "Perfil de transportador no encontrado."}), 404
    return jsonify(_serialize_transportador(t))


@logistics_bp.put("/transportador/perfil")
@role_required("transportador")
def actualizar_perfil_transportador():
    t = _get_own_transportador()
    if not t:
        return jsonify({"message": "Perfil de transportador no encontrado."}), 404
    data = request.get_json(force=True) or {}
    if "ubicacion" in data:
        t.ubicacion = data["ubicacion"]
    if "disponible" in data:
        t.disponible = bool(data["disponible"])
    db.session.commit()
    return jsonify(_serialize_transportador(t))


@logistics_bp.get("/vehiculos")
@role_required("transportador")
def listar_vehiculos():
    t = _get_own_transportador()
    if not t:
        return jsonify({"message": "Perfil de transportador no encontrado."}), 404
    return jsonify([_serialize_vehiculo(v) for v in t.vehiculos])


@logistics_bp.post("/vehiculos")
@role_required("transportador")
def crear_vehiculo():
    t = _get_own_transportador()
    if not t:
        return jsonify({"message": "Perfil de transportador no encontrado."}), 404
    data = request.get_json(force=True) or {}
    placa = (data.get("placa") or "").strip().upper()
    if not placa:
        return jsonify({"message": "La placa es obligatoria."}), 400
    if Vehiculo.query.filter_by(placa=placa).first():
        return jsonify({"message": "Ya existe un vehículo con esa placa."}), 409

    vehiculo = Vehiculo(
        transportador_id=t.id,
        placa=placa,
        tipo_vehiculo=data.get("tipo_vehiculo"),
        capacidad_toneladas=data.get("capacidad_toneladas"),
        disponible=data.get("disponible", True),
    )
    db.session.add(vehiculo)
    db.session.commit()
    return jsonify(_serialize_vehiculo(vehiculo)), 201


@logistics_bp.put("/vehiculos/<int:vehiculo_id>")
@role_required("transportador")
def editar_vehiculo(vehiculo_id):
    t = _get_own_transportador()
    vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, transportador_id=t.id if t else -1).first()
    if not vehiculo:
        return jsonify({"message": "Vehículo no encontrado."}), 404
    data = request.get_json(force=True) or {}
    for campo in ("tipo_vehiculo", "capacidad_toneladas", "disponible", "estado"):
        if campo in data:
            setattr(vehiculo, campo, data[campo])
    db.session.commit()
    return jsonify(_serialize_vehiculo(vehiculo))


@logistics_bp.delete("/vehiculos/<int:vehiculo_id>")
@role_required("transportador")
def eliminar_vehiculo(vehiculo_id):
    t = _get_own_transportador()
    vehiculo = Vehiculo.query.filter_by(id=vehiculo_id, transportador_id=t.id if t else -1).first()
    if not vehiculo:
        return jsonify({"message": "Vehículo no encontrado."}), 404
    vehiculo.estado = "inactivo"
    db.session.commit()
    return jsonify({"message": "Vehículo desactivado."})


# ------------------------------------------------------ solicitudes ------

@logistics_bp.post("/transporte/solicitudes")
@role_required("palmicultor")
def crear_solicitud():
    data = request.get_json(force=True) or {}

    finca = Finca.query.filter_by(id=data.get("finca_id"), usuario_id=current_user_id()).first()
    if not finca:
        return jsonify({"message": "La finca indicada no existe o no te pertenece."}), 400

    lote_id = data.get("lote_id")
    if lote_id and not Lote.query.filter_by(id=lote_id, finca_id=finca.id).first():
        return jsonify({"message": "El lote indicado no pertenece a la finca seleccionada."}), 400

    fecha_servicio = _parse_date(data.get("fecha_servicio"))
    hora_servicio = _parse_time(data.get("hora_servicio"))

    solicitud = SolicitudTransporte(
        palmicultor_id=current_user_id(),
        finca_id=finca.id,
        lote_id=lote_id,
        comprador_id=data.get("comprador_id"),
        cantidad_estimada=data.get("cantidad_estimada"),
        # RN06: antes de la aceptación solo se comparte el municipio/vereda, nunca coordenadas exactas.
        origen=f"{finca.municipio}" + (f", {finca.vereda}" if finca.vereda else ""),
        destino=data.get("destino"),
        fecha_servicio=fecha_servicio,
        hora_servicio=hora_servicio,
        tarifa_sugerida=data.get("tarifa_sugerida"),
        observaciones=data.get("observaciones"),
        estado="Pendiente",
    )
    db.session.add(solicitud)
    db.session.commit()

    return jsonify(_serialize_solicitud(solicitud)), 201


@logistics_bp.get("/transporte/solicitudes")
@role_required("palmicultor", "transportador")
def listar_solicitudes():
    rol = get_jwt().get("rol")
    estado = request.args.get("estado")

    if rol == "palmicultor":
        query = SolicitudTransporte.query.filter_by(palmicultor_id=current_user_id())
    else:
        t = _get_own_transportador()
        if not t:
            return jsonify({"message": "Perfil de transportador no encontrado."}), 404
        if t.estado != "aprobado":
            return jsonify({"message": "Tu perfil de transportador está pendiente de validación por el administrador."}), 403
        pendientes = request.args.get("pendientes") == "true"
        if pendientes:
            query = SolicitudTransporte.query.filter_by(estado="Pendiente", transportador_id=None)
        else:
            query = SolicitudTransporte.query.filter_by(transportador_id=t.id)

    if estado:
        query = query.filter(SolicitudTransporte.estado == estado)

    solicitudes = query.order_by(SolicitudTransporte.fecha_solicitud.desc()).all()
    return jsonify([_serialize_solicitud(s) for s in solicitudes])


@logistics_bp.get("/transporte/solicitudes/<int:solicitud_id>")
@role_required("palmicultor", "transportador")
def obtener_solicitud(solicitud_id):
    solicitud = _get_visible_solicitud(solicitud_id)
    if not solicitud:
        return jsonify({"message": "Solicitud no encontrada."}), 404
    return jsonify(_serialize_solicitud(solicitud, detalle=True))


@logistics_bp.patch("/transporte/solicitudes/<int:solicitud_id>/aceptar")
@role_required("transportador")
def aceptar_solicitud(solicitud_id):
    t = _get_own_transportador()
    if not t or t.estado != "aprobado":
        return jsonify({"message": "Tu perfil de transportador está pendiente de validación."}), 403

    solicitud = SolicitudTransporte.query.get(solicitud_id)
    if not solicitud or solicitud.estado != "Pendiente" or solicitud.transportador_id is not None:
        return jsonify({"message": "La solicitud ya no está disponible."}), 409

    data = request.get_json(silent=True) or {}
    vehiculo_id = data.get("vehiculo_id")
    if vehiculo_id and not Vehiculo.query.filter_by(id=vehiculo_id, transportador_id=t.id).first():
        return jsonify({"message": "El vehículo indicado no te pertenece."}), 400

    solicitud.transportador_id = t.id
    solicitud.vehiculo_id = vehiculo_id
    solicitud.estado = "Aceptada"
    solicitud.fecha_aceptacion = datetime.utcnow()  # a partir de aquí se revela la ubicación exacta (RN06)
    if data.get("tarifa_acordada") is not None:
        solicitud.tarifa_acordada = data["tarifa_acordada"]

    titulo = "Transporte aceptado"
    mensaje = f"Un transportador aceptó tu solicitud #{solicitud.id}."
    db.session.add(
        Notificacion(
            usuario_id=solicitud.palmicultor_id,
            tipo="logistica",
            titulo=titulo,
            mensaje=mensaje,
            enlace="HistorialDespachos",
        )
    )
    notificar_por_sms(Usuario.query.get(solicitud.palmicultor_id), titulo, mensaje)
    db.session.commit()
    return jsonify(_serialize_solicitud(solicitud, detalle=True))


@logistics_bp.patch("/transporte/solicitudes/<int:solicitud_id>/rechazar")
@role_required("transportador")
def rechazar_solicitud(solicitud_id):
    t = _get_own_transportador()
    solicitud = SolicitudTransporte.query.get(solicitud_id)
    if not solicitud or solicitud.estado != "Pendiente":
        return jsonify({"message": "La solicitud ya no está disponible."}), 409

    data = request.get_json(silent=True) or {}
    solicitud.estado = "Rechazada"
    solicitud.motivo_rechazo = data.get("motivo")
    db.session.commit()
    return jsonify(_serialize_solicitud(solicitud))


@logistics_bp.patch("/transporte/solicitudes/<int:solicitud_id>/estado")
@role_required("transportador")
def actualizar_estado_solicitud(solicitud_id):
    t = _get_own_transportador()
    solicitud = SolicitudTransporte.query.filter_by(id=solicitud_id, transportador_id=t.id if t else -1).first()
    if not solicitud:
        return jsonify({"message": "Solicitud no encontrada."}), 404

    data = request.get_json(force=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("En preparación", "En tránsito", "Entregada", "Cancelada"):
        return jsonify({"message": "Estado inválido."}), 400

    solicitud.estado = nuevo_estado
    titulo = "Actualización de transporte"
    mensaje = f"Tu solicitud #{solicitud.id} cambió a: {nuevo_estado}."
    db.session.add(
        Notificacion(
            usuario_id=solicitud.palmicultor_id,
            tipo="logistica",
            titulo=titulo,
            mensaje=mensaje,
            enlace="HistorialDespachos",
        )
    )
    notificar_por_sms(Usuario.query.get(solicitud.palmicultor_id), titulo, mensaje)
    db.session.commit()
    return jsonify(_serialize_solicitud(solicitud))


@logistics_bp.get("/transporte/historial")
@role_required("palmicultor", "transportador")
def historial_transporte():
    rol = get_jwt().get("rol")
    if rol == "palmicultor":
        query = SolicitudTransporte.query.filter_by(palmicultor_id=current_user_id())
    else:
        t = _get_own_transportador()
        if not t:
            return jsonify({"message": "Perfil de transportador no encontrado."}), 404
        query = SolicitudTransporte.query.filter_by(transportador_id=t.id)

    query = query.filter(SolicitudTransporte.estado.in_(["Entregada", "Cancelada", "Rechazada"]))
    solicitudes = query.order_by(SolicitudTransporte.fecha_solicitud.desc()).all()
    return jsonify([_serialize_solicitud(s) for s in solicitudes])


# -------------------------------------------------------------- vías -----

@logistics_bp.get("/vias")
def listar_vias():
    municipio = request.args.get("municipio")
    query = EstadoVia.query
    if municipio:
        query = query.filter(EstadoVia.municipio.ilike(f"%{municipio}%"))
    vias = query.order_by(EstadoVia.fecha_actualizacion.desc()).all()
    return jsonify([_serialize_via(v) for v in vias])


@logistics_bp.post("/vias")
@role_required("transportador", "administrador")
def reportar_via():
    data = request.get_json(force=True) or {}
    via_nombre = (data.get("via") or "").strip()
    if not via_nombre:
        return jsonify({"message": "El nombre de la vía es obligatorio."}), 400

    estado = data.get("estado", "habilitada")
    if estado not in ("habilitada", "precaucion", "restringida", "cerrada"):
        return jsonify({"message": "Estado de vía inválido."}), 400

    via = EstadoVia(
        via=via_nombre,
        municipio=(data.get("municipio") or "Tumaco").strip(),
        estado=estado,
        observaciones=(data.get("observaciones") or "").strip() or None,
        origen=(data.get("origen") or "").strip() or None,
        destino=(data.get("destino") or "").strip() or None,
        distancia_km=data.get("distancia_km"),
        actualizado_por=current_user_id(),
    )
    db.session.add(via)
    db.session.commit()
    return jsonify(_serialize_via(via)), 201


@logistics_bp.put("/vias/<int:via_id>")
@role_required("transportador", "administrador")
def actualizar_via(via_id):
    via = EstadoVia.query.get(via_id)
    if not via:
        return jsonify({"message": "Vía no encontrada."}), 404
    data = request.get_json(force=True) or {}
    if "estado" in data:
        if data["estado"] not in ("habilitada", "precaucion", "restringida", "cerrada"):
            return jsonify({"message": "Estado de vía inválido."}), 400
        via.estado = data["estado"]
    if "observaciones" in data:
        via.observaciones = data["observaciones"]
    if "via" in data:
        via_nombre = (data.get("via") or "").strip()
        if not via_nombre:
            return jsonify({"message": "El nombre de la vía no puede quedar vacío."}), 400
        via.via = via_nombre
    if "municipio" in data:
        via.municipio = (data.get("municipio") or "Tumaco").strip()
    for campo in ("origen", "destino"):
        if campo in data:
            setattr(via, campo, (data[campo] or "").strip() or None)
    if "distancia_km" in data:
        via.distancia_km = data["distancia_km"]
    via.actualizado_por = current_user_id()
    db.session.commit()
    return jsonify(_serialize_via(via))


# --------------------------------------------------------------- helpers --

def _get_own_transportador():
    return Transportador.query.filter_by(usuario_id=current_user_id()).first()


def _get_visible_solicitud(solicitud_id):
    solicitud = SolicitudTransporte.query.get(solicitud_id)
    if not solicitud:
        return None
    rol = get_jwt().get("rol")
    uid = current_user_id()
    if rol == "palmicultor" and solicitud.palmicultor_id == uid:
        return solicitud
    if rol == "transportador":
        t = _get_own_transportador()
        if t and (solicitud.transportador_id == t.id or (solicitud.estado == "Pendiente" and solicitud.transportador_id is None)):
            return solicitud
    return None


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_time(value):
    if not value:
        return None
    try:
        return time.fromisoformat(str(value)[:8])
    except ValueError:
        return None


def _serialize_transportador(t: Transportador):
    return {
        "id": t.id,
        "ubicacion": t.ubicacion,
        "disponible": t.disponible,
        "estado": t.estado,
    }


def _serialize_vehiculo(v: Vehiculo):
    return {
        "id": v.id,
        "placa": v.placa,
        "tipo_vehiculo": v.tipo_vehiculo,
        "capacidad_toneladas": v.capacidad_toneladas,
        "disponible": v.disponible,
        "estado": v.estado,
    }


def _serialize_via(v: EstadoVia):
    return {
        "id": v.id,
        "via": v.via,
        "municipio": v.municipio,
        "estado": v.estado,
        "observaciones": v.observaciones,
        "origen": v.origen,
        "destino": v.destino,
        "distancia_km": v.distancia_km,
        "fecha_actualizacion": v.fecha_actualizacion.isoformat() if v.fecha_actualizacion else None,
    }


def _serialize_solicitud(s: SolicitudTransporte, detalle=False):
    rol = get_jwt().get("rol")
    uid = current_user_id()

    revelar_ubicacion = False
    if rol == "palmicultor" and s.palmicultor_id == uid:
        revelar_ubicacion = True  # el dueño siempre ve su propia finca
    elif rol == "transportador" and s.fecha_aceptacion is not None:
        t = _get_own_transportador()
        if t and s.transportador_id == t.id:
            revelar_ubicacion = True  # RN06: solo tras aceptar formalmente

    data = {
        "id": s.id,
        "finca_id": s.finca_id,
        "lote_id": s.lote_id,
        "comprador_id": s.comprador_id,
        "transportador_id": s.transportador_id,
        "vehiculo_id": s.vehiculo_id,
        "fecha_solicitud": s.fecha_solicitud.isoformat() if s.fecha_solicitud else None,
        "fecha_servicio": s.fecha_servicio.isoformat() if s.fecha_servicio else None,
        "hora_servicio": s.hora_servicio.isoformat() if s.hora_servicio else None,
        "cantidad_estimada": s.cantidad_estimada,
        "destino": s.destino,
        "tarifa_sugerida": float(s.tarifa_sugerida) if s.tarifa_sugerida is not None else None,
        "tarifa_acordada": float(s.tarifa_acordada) if s.tarifa_acordada is not None else None,
        "estado": s.estado,
        "motivo_rechazo": s.motivo_rechazo,
        # Zona general siempre visible (municipio/vereda); nunca coordenadas exactas hasta aceptar.
        "origen_zona": s.origen,
    }

    if revelar_ubicacion:
        finca = Finca.query.get(s.finca_id)
        data["ubicacion_exacta"] = {
            "direccion": finca.ubicacion if finca else None,
            "lat": finca.coordenadas_lat if finca else None,
            "long": finca.coordenadas_long if finca else None,
        }

    # El destino (comprador/planta) no es información privada de finca (RN06
    # solo protege el origen), así que sus coordenadas siempre se incluyen
    # cuando existen — sirven para el mapa de ruta.
    if s.comprador_id:
        comprador = Comprador.query.get(s.comprador_id)
        if comprador and comprador.latitud is not None and comprador.longitud is not None:
            data["destino_coords"] = {
                "lat": comprador.latitud,
                "long": comprador.longitud,
                "etiqueta": comprador.empresa,
            }

    if detalle:
        data["observaciones"] = s.observaciones

    return data
