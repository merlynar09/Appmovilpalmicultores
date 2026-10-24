"""Puntos de comercialización (CU6: consulta pública; CU14: gestión admin)."""

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import PuntoComercializacion
from app.utils import role_required

puntos_bp = Blueprint("puntos", __name__)


@puntos_bp.get("/puntos-comercializacion")
def listar_puntos():
    puntos = PuntoComercializacion.query.filter_by(estado="activo").order_by(PuntoComercializacion.nombre).all()
    return jsonify([_serialize(p) for p in puntos])


@puntos_bp.post("/admin/puntos-comercializacion")
@role_required("administrador")
def crear_punto():
    data = request.get_json(force=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"message": "El nombre es obligatorio."}), 400

    punto = PuntoComercializacion(
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
        ubicacion=(data.get("ubicacion") or "").strip() or None,
        latitud=data.get("latitud"),
        longitud=data.get("longitud"),
        contacto=(data.get("contacto") or "").strip() or None,
        estado="activo",
    )
    db.session.add(punto)
    db.session.commit()
    return jsonify(_serialize(punto)), 201


@puntos_bp.put("/admin/puntos-comercializacion/<int:punto_id>")
@role_required("administrador")
def editar_punto(punto_id):
    punto = PuntoComercializacion.query.get(punto_id)
    if not punto:
        return jsonify({"message": "Punto de comercialización no encontrado."}), 404

    data = request.get_json(force=True) or {}
    if "nombre" in data:
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return jsonify({"message": "El nombre no puede quedar vacío."}), 400
        punto.nombre = nombre
    for campo in ("descripcion", "ubicacion", "contacto"):
        if campo in data:
            setattr(punto, campo, (data[campo] or "").strip() or None)
    for campo in ("latitud", "longitud"):
        if campo in data:
            setattr(punto, campo, data[campo])

    db.session.commit()
    return jsonify(_serialize(punto))


@puntos_bp.patch("/admin/puntos-comercializacion/<int:punto_id>/estado")
@role_required("administrador")
def cambiar_estado_punto(punto_id):
    punto = PuntoComercializacion.query.get(punto_id)
    if not punto:
        return jsonify({"message": "Punto de comercialización no encontrado."}), 404

    data = request.get_json(force=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("activo", "inactivo"):
        return jsonify({"message": "Estado inválido."}), 400

    punto.estado = nuevo_estado
    db.session.commit()
    return jsonify(_serialize(punto))


@puntos_bp.get("/admin/puntos-comercializacion")
@role_required("administrador")
def listar_puntos_admin():
    """Igual que la pública pero incluye los inactivos, para gestión (CU14)."""
    puntos = PuntoComercializacion.query.order_by(PuntoComercializacion.nombre).all()
    return jsonify([_serialize(p) for p in puntos])


def _serialize(p: PuntoComercializacion):
    return {
        "id": p.id,
        "nombre": p.nombre,
        "descripcion": p.descripcion,
        "ubicacion": p.ubicacion,
        "latitud": p.latitud,
        "longitud": p.longitud,
        "contacto": p.contacto,
        "estado": p.estado,
    }
