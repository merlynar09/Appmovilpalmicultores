from datetime import date, timedelta

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Finca, Lote, CicloCosecha
from app.utils import role_required, current_user_id
from app.validators import validar_numero_positivo

fincas_bp = Blueprint("fincas", __name__)


# ---------------------------------------------------------------- fincas ---

@fincas_bp.get("/fincas")
@role_required("palmicultor")
def listar_fincas():
    fincas = Finca.query.filter_by(usuario_id=current_user_id(), estado="activa").all()
    return jsonify([_serialize_finca(f) for f in fincas])


@fincas_bp.post("/fincas")
@role_required("palmicultor")
def crear_finca():
    data = request.get_json(force=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"message": "El nombre de la finca es obligatorio."}), 400

    # F5-04: antes se podía guardar un área negativa o cero sin aviso.
    area, error = validar_numero_positivo(data.get("area_hectareas"), "El área en hectáreas")
    if error:
        return jsonify({"message": error}), 400

    finca = Finca(
        usuario_id=current_user_id(),
        nombre=nombre,
        ubicacion=(data.get("ubicacion") or "").strip() or None,
        municipio=(data.get("municipio") or "Tumaco").strip(),
        vereda=(data.get("vereda") or "").strip() or None,
        coordenadas_lat=data.get("coordenadas_lat"),
        coordenadas_long=data.get("coordenadas_long"),
        area_hectareas=area,
    )
    db.session.add(finca)
    db.session.commit()
    return jsonify(_serialize_finca(finca)), 201


@fincas_bp.get("/fincas/<int:finca_id>")
@role_required("palmicultor")
def obtener_finca(finca_id):
    finca = _get_own_finca(finca_id)
    if not finca:
        return jsonify({"message": "Finca no encontrada."}), 404
    return jsonify(_serialize_finca(finca, detalle=True))


@fincas_bp.put("/fincas/<int:finca_id>")
@role_required("palmicultor")
def editar_finca(finca_id):
    finca = _get_own_finca(finca_id)
    if not finca:
        return jsonify({"message": "Finca no encontrada."}), 404

    data = request.get_json(force=True) or {}
    if "area_hectareas" in data:
        area, error = validar_numero_positivo(data["area_hectareas"], "El área en hectáreas")
        if error:
            return jsonify({"message": error}), 400
        data["area_hectareas"] = area
    for campo in ("nombre", "ubicacion", "municipio", "vereda", "area_hectareas", "coordenadas_lat", "coordenadas_long"):
        if campo in data:
            setattr(finca, campo, data[campo])

    db.session.commit()
    return jsonify(_serialize_finca(finca))


@fincas_bp.delete("/fincas/<int:finca_id>")
@role_required("palmicultor")
def desactivar_finca(finca_id):
    finca = _get_own_finca(finca_id)
    if not finca:
        return jsonify({"message": "Finca no encontrada."}), 404
    finca.estado = "inactiva"
    db.session.commit()
    return jsonify({"message": "Finca desactivada."})


# ----------------------------------------------------------------- lotes ---

@fincas_bp.get("/fincas/<int:finca_id>/lotes")
@role_required("palmicultor")
def listar_lotes(finca_id):
    finca = _get_own_finca(finca_id)
    if not finca:
        return jsonify({"message": "Finca no encontrada."}), 404
    lotes = Lote.query.filter_by(finca_id=finca.id, estado="activo").all()
    return jsonify([_serialize_lote(l) for l in lotes])


@fincas_bp.post("/fincas/<int:finca_id>/lotes")
@role_required("palmicultor")
def crear_lote(finca_id):
    finca = _get_own_finca(finca_id)
    if not finca:
        return jsonify({"message": "Finca no encontrada."}), 404
    # F5-03: una finca desactivada no debe admitir lotes nuevos.
    if finca.estado != "activa":
        return jsonify({"message": "La finca está inactiva; no se pueden crear nuevos lotes."}), 409

    data = request.get_json(force=True) or {}
    # RN02: nomenclatura flexible — se admite cualquier código no vacío
    # (programa de siembra, bloque, sector o plano cartesiano).
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        return jsonify({"message": "El código del lote es obligatorio."}), 400
    # F5-05: el código debe ser único dentro de la misma finca.
    if Lote.query.filter_by(finca_id=finca.id, codigo=codigo).first():
        return jsonify({"message": "Ya existe un lote con ese código en esta finca."}), 409

    area, error = validar_numero_positivo(data.get("area_hectareas"), "El área en hectáreas")
    if error:
        return jsonify({"message": error}), 400

    lote = Lote(
        finca_id=finca.id,
        codigo=codigo,
        nombre=(data.get("nombre") or "").strip() or None,
        bloque=(data.get("bloque") or "").strip() or None,
        sector=(data.get("sector") or "").strip() or None,
        area_hectareas=area,
        anio_siembra=data.get("anio_siembra"),
        numero_palmas=data.get("numero_palmas"),
        material_sembrado=(data.get("material_sembrado") or "").strip() or None,
        topografia=(data.get("topografia") or "").strip() or None,
        drenaje=(data.get("drenaje") or "").strip() or None,
        estado_sanitario=(data.get("estado_sanitario") or "").strip() or None,
        numero_lineas=data.get("numero_lineas"),
    )
    db.session.add(lote)
    db.session.commit()
    return jsonify(_serialize_lote(lote)), 201


@fincas_bp.get("/lotes/<int:lote_id>")
@role_required("palmicultor")
def obtener_lote(lote_id):
    lote = _get_own_lote(lote_id)
    if not lote:
        return jsonify({"message": "Lote no encontrado."}), 404
    return jsonify(_serialize_lote(lote, detalle=True))


@fincas_bp.put("/lotes/<int:lote_id>")
@role_required("palmicultor")
def editar_lote(lote_id):
    lote = _get_own_lote(lote_id)
    if not lote:
        return jsonify({"message": "Lote no encontrado."}), 404

    data = request.get_json(force=True) or {}

    if "codigo" in data:
        nuevo_codigo = (data.get("codigo") or "").strip()
        if not nuevo_codigo:
            return jsonify({"message": "El código del lote no puede quedar vacío."}), 400
        existente = Lote.query.filter(
            Lote.finca_id == lote.finca_id, Lote.codigo == nuevo_codigo, Lote.id != lote.id
        ).first()
        if existente:
            return jsonify({"message": "Ya existe un lote con ese código en esta finca."}), 409
        data["codigo"] = nuevo_codigo

    if "area_hectareas" in data:
        area, error = validar_numero_positivo(data["area_hectareas"], "El área en hectáreas")
        if error:
            return jsonify({"message": error}), 400
        data["area_hectareas"] = area

    campos = (
        "codigo", "nombre", "bloque", "sector", "area_hectareas", "anio_siembra",
        "numero_palmas", "material_sembrado", "topografia", "drenaje",
        "estado_sanitario", "numero_lineas",
    )
    for campo in campos:
        if campo in data:
            setattr(lote, campo, data[campo])

    db.session.commit()
    return jsonify(_serialize_lote(lote))


@fincas_bp.delete("/lotes/<int:lote_id>")
@role_required("palmicultor")
def desactivar_lote(lote_id):
    lote = _get_own_lote(lote_id)
    if not lote:
        return jsonify({"message": "Lote no encontrado."}), 404
    lote.estado = "inactivo"
    db.session.commit()
    return jsonify({"message": "Lote desactivado."})


# ---------------------------------------------------------- ciclos cosecha

@fincas_bp.get("/lotes/<int:lote_id>/ciclos")
@role_required("palmicultor")
def listar_ciclos(lote_id):
    lote = _get_own_lote(lote_id)
    if not lote:
        return jsonify({"message": "Lote no encontrado."}), 404
    ciclos = CicloCosecha.query.filter_by(lote_id=lote.id).order_by(CicloCosecha.id.desc()).all()
    return jsonify([_serialize_ciclo(c) for c in ciclos])


@fincas_bp.post("/lotes/<int:lote_id>/ciclos")
@role_required("palmicultor")
def crear_ciclo(lote_id):
    lote = _get_own_lote(lote_id)
    if not lote:
        return jsonify({"message": "Lote no encontrado."}), 404
    # F5-03: un lote (o su finca) inactivo no debe admitir ciclos nuevos.
    if lote.estado != "activo" or lote.finca.estado != "activa":
        return jsonify({"message": "El lote o la finca están inactivos; no se pueden crear nuevos ciclos."}), 409

    data = request.get_json(force=True) or {}
    duracion_dias = data.get("duracion_dias")
    if not duracion_dias or not (1 <= int(duracion_dias) <= 60):
        return jsonify({"message": "La duración del ciclo (días) es obligatoria y debe ser razonable."}), 400

    dias_anticipacion = data.get("dias_anticipacion_alerta", 3)
    if not (1 <= int(dias_anticipacion) <= 7):
        return jsonify({"message": "La anticipación de la alerta debe estar entre 1 y 7 días (RN03)."}), 400

    fecha_ultima = _parse_date(data.get("fecha_ultima_cosecha")) or date.today()
    proxima = fecha_ultima + timedelta(days=int(duracion_dias))

    ciclo = CicloCosecha(
        lote_id=lote.id,
        fecha_ultima_cosecha=fecha_ultima,
        fecha_inicio=_parse_date(data.get("fecha_inicio")) or fecha_ultima,
        duracion_dias=int(duracion_dias),
        dias_anticipacion_alerta=int(dias_anticipacion),
        proxima_fecha_estimada=proxima,
        observaciones=(data.get("observaciones") or "").strip() or None,
        estado="Programado",
    )
    db.session.add(ciclo)
    db.session.commit()
    return jsonify(_serialize_ciclo(ciclo)), 201


@fincas_bp.put("/ciclos/<int:ciclo_id>")
@role_required("palmicultor")
def editar_ciclo(ciclo_id):
    ciclo = db.session.get(CicloCosecha, ciclo_id)
    if not ciclo or not _get_own_lote(ciclo.lote_id):
        return jsonify({"message": "Ciclo no encontrado."}), 404

    data = request.get_json(force=True) or {}

    if "duracion_dias" in data:
        ciclo.duracion_dias = int(data["duracion_dias"])
    if "dias_anticipacion_alerta" in data:
        dias = int(data["dias_anticipacion_alerta"])
        if not (1 <= dias <= 7):
            return jsonify({"message": "La anticipación de la alerta debe estar entre 1 y 7 días (RN03)."}), 400
        ciclo.dias_anticipacion_alerta = dias
    if "fecha_ultima_cosecha" in data:
        ciclo.fecha_ultima_cosecha = _parse_date(data["fecha_ultima_cosecha"])
    if "observaciones" in data:
        ciclo.observaciones = data["observaciones"]
    if "estado" in data:
        ciclo.estado = data["estado"]

    if ciclo.fecha_ultima_cosecha and ciclo.duracion_dias:
        ciclo.proxima_fecha_estimada = ciclo.fecha_ultima_cosecha + timedelta(days=ciclo.duracion_dias)

    db.session.commit()
    return jsonify(_serialize_ciclo(ciclo))


@fincas_bp.post("/ciclos/<int:ciclo_id>/registrar-cosecha")
@role_required("palmicultor")
def registrar_cosecha(ciclo_id):
    """Marca el ciclo actual como completado y programa el siguiente automáticamente."""
    ciclo = db.session.get(CicloCosecha, ciclo_id)
    lote = _get_own_lote(ciclo.lote_id) if ciclo else None
    if not ciclo or not lote:
        return jsonify({"message": "Ciclo no encontrado."}), 404
    # F5-03: un lote (o su finca) inactivo no debe admitir nuevas cosechas.
    if lote.estado != "activo" or lote.finca.estado != "activa":
        return jsonify({"message": "El lote o la finca están inactivos."}), 409

    hoy = date.today()
    ciclo.estado = "Completado"
    db.session.flush()

    nuevo_ciclo = CicloCosecha(
        lote_id=ciclo.lote_id,
        fecha_ultima_cosecha=hoy,
        fecha_inicio=hoy,
        duracion_dias=ciclo.duracion_dias,
        dias_anticipacion_alerta=ciclo.dias_anticipacion_alerta,
        proxima_fecha_estimada=hoy + timedelta(days=ciclo.duracion_dias or 10),
        estado="Programado",
    )
    db.session.add(nuevo_ciclo)
    db.session.commit()
    return jsonify(_serialize_ciclo(nuevo_ciclo)), 201


# --------------------------------------------------------------- helpers ---

def _get_own_finca(finca_id):
    return Finca.query.filter_by(id=finca_id, usuario_id=current_user_id()).first()


def _get_own_lote(lote_id):
    lote = db.session.get(Lote, lote_id)
    if not lote:
        return None
    if not _get_own_finca(lote.finca_id):
        return None
    return lote


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _serialize_finca(f: Finca, detalle=False):
    data = {
        "id": f.id,
        "nombre": f.nombre,
        "municipio": f.municipio,
        "vereda": f.vereda,
        "area_hectareas": f.area_hectareas,
        "estado": f.estado,
        "total_lotes": len(f.lotes) if detalle else None,
    }
    if detalle:
        # La ubicación exacta solo se expone al propio dueño (RN01/RN06).
        data.update(
            {
                "ubicacion": f.ubicacion,
                "coordenadas_lat": f.coordenadas_lat,
                "coordenadas_long": f.coordenadas_long,
            }
        )
    return data


def _serialize_lote(l: Lote, detalle=False):
    data = {
        "id": l.id,
        "finca_id": l.finca_id,
        "codigo": l.codigo,
        "nombre": l.nombre,
        "bloque": l.bloque,
        "sector": l.sector,
        "area_hectareas": l.area_hectareas,
        "numero_palmas": l.numero_palmas,
        "anio_siembra": l.anio_siembra,
        "estado": l.estado,
    }
    if detalle:
        data.update(
            {
                "material_sembrado": l.material_sembrado,
                "topografia": l.topografia,
                "drenaje": l.drenaje,
                "estado_sanitario": l.estado_sanitario,
                "numero_lineas": l.numero_lineas,
            }
        )
    return data


def _serialize_ciclo(c: CicloCosecha):
    return {
        "id": c.id,
        "lote_id": c.lote_id,
        "fecha_ultima_cosecha": c.fecha_ultima_cosecha.isoformat() if c.fecha_ultima_cosecha else None,
        "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
        "duracion_dias": c.duracion_dias,
        "dias_anticipacion_alerta": c.dias_anticipacion_alerta,
        "proxima_fecha_estimada": c.proxima_fecha_estimada.isoformat() if c.proxima_fecha_estimada else None,
        "observaciones": c.observaciones,
        "estado": c.estado,
    }
