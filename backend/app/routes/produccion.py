from datetime import date

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Lote, Finca, RegistroProduccion
from app.utils import role_required, current_user_id

produccion_bp = Blueprint("produccion", __name__)


@produccion_bp.get("/produccion")
@role_required("palmicultor")
def listar_produccion():
    lote_id = request.args.get("lote_id", type=int)
    query = RegistroProduccion.query.join(Lote).join(Finca).filter(Finca.usuario_id == current_user_id())
    if lote_id:
        query = query.filter(RegistroProduccion.lote_id == lote_id)
    registros = query.order_by(RegistroProduccion.fecha.desc()).all()
    return jsonify([_serialize(r) for r in registros])


@produccion_bp.post("/produccion")
@role_required("palmicultor")
def crear_registro():
    data = request.get_json(force=True) or {}
    usuario_id = current_user_id()
    registro, error = _build_registro(data, usuario_id)
    if error:
        return jsonify({"message": error}), 400
    registro.creado_por_id = usuario_id
    db.session.add(registro)
    db.session.commit()
    return jsonify(_serialize(registro)), 201


@produccion_bp.post("/produccion/sync")
@role_required("palmicultor")
def sync_produccion():
    """Recibe un lote de censos guardados offline (AsyncStorage) y los persiste.

    Devuelve, por cada item enviado (identificado por `_local_id` generado en
    el cliente), si se guardó correctamente o el motivo del error, para que
    el cliente pueda limpiar su cola local únicamente de los que sí se
    sincronizaron.

    F5-01: antes un reintento del mismo envío (ej. el cliente no recibió la
    respuesta a tiempo y reintenta) insertaba el censo por segunda vez, sin
    ninguna forma de detectar que ya se había guardado. Ahora, si el item
    trae `_local_id`, se busca primero un registro ya sincronizado con ese
    mismo id para este usuario — si existe, se devuelve tal cual (idempotente)
    en vez de duplicarlo.
    """
    data = request.get_json(force=True) or {}
    items = data.get("items") or []
    usuario_id = current_user_id()
    resultados = []
    for item in items:
        local_id = item.get("_local_id")
        if local_id:
            existente = RegistroProduccion.query.filter_by(
                creado_por_id=usuario_id, client_local_id=str(local_id)
            ).first()
            if existente:
                resultados.append({"_local_id": local_id, "ok": True, "id": existente.id})
                continue

        registro, error = _build_registro(item, usuario_id)
        if error:
            resultados.append({"_local_id": local_id, "ok": False, "message": error})
            continue
        registro.creado_por_id = usuario_id
        if local_id:
            registro.client_local_id = str(local_id)
        db.session.add(registro)
        db.session.flush()
        resultados.append({"_local_id": local_id, "ok": True, "id": registro.id})
    db.session.commit()
    return jsonify({"resultados": resultados})


def _build_registro(data, usuario_id):
    """Construye (sin persistir) un RegistroProduccion validado para
    `usuario_id`. Recibe el usuario explícito en vez de leerlo de
    current_user_id() porque también lo invoca el motor USSD, que no tiene
    contexto JWT."""
    lote_id = data.get("lote_id")
    lote = db.session.get(Lote, lote_id) if lote_id else None
    finca = Finca.query.filter_by(id=lote.finca_id, usuario_id=usuario_id).first() if lote else None
    if not lote or not finca:
        return None, "El lote indicado no existe o no te pertenece."
    # F5-03: un lote o finca inactivos no deben admitir censos nuevos.
    if finca.estado != "activa" or lote.estado != "activo":
        return None, "El lote o la finca están inactivos; no se pueden registrar nuevos censos."

    palmas_evaluadas = data.get("palmas_evaluadas")
    palmas_improductivas = data.get("palmas_improductivas") or 0
    if not palmas_evaluadas or int(palmas_evaluadas) <= 0:
        return None, "Las palmas evaluadas en el censo son obligatorias."
    if int(palmas_improductivas) > int(palmas_evaluadas):
        return None, "Las palmas improductivas no pueden ser más que las evaluadas."

    # RN04: la muestra recomendada es del 4-5% del total de palmas del lote.
    if lote.numero_palmas:
        porcentaje_muestra = (int(palmas_evaluadas) / lote.numero_palmas) * 100
    else:
        porcentaje_muestra = None

    racimos_totales = data.get("racimos_totales")
    if racimos_totales is None:
        pequenos = data.get("racimos_pequenos") or 0
        medianos = data.get("racimos_medianos") or 0
        maduros = data.get("racimos_maduros") or 0
        racimos_totales = int(pequenos) + int(medianos) + int(maduros)

    fecha = data.get("fecha")
    try:
        fecha = date.fromisoformat(str(fecha)[:10]) if fecha else date.today()
    except ValueError:
        fecha = date.today()

    registro = RegistroProduccion(
        lote_id=lote.id,
        fecha=fecha,
        palmas_evaluadas=int(palmas_evaluadas),
        racimos_pequenos=int(data.get("racimos_pequenos") or 0),
        racimos_medianos=int(data.get("racimos_medianos") or 0),
        racimos_maduros=int(data.get("racimos_maduros") or 0),
        racimos_totales=int(racimos_totales),
        palmas_improductivas=int(palmas_improductivas),
        peso_promedio_racimo=data.get("peso_promedio_racimo"),
        fruto_suelto=data.get("fruto_suelto"),
        observaciones=(data.get("observaciones") or "").strip() or None,
        fuente=data.get("fuente") or "app",
    )
    registro._porcentaje_muestra = porcentaje_muestra  # solo para la respuesta serializada
    return registro, None


def _serialize(r: RegistroProduccion):
    return {
        "id": r.id,
        "lote_id": r.lote_id,
        "fecha": r.fecha.isoformat() if r.fecha else None,
        "palmas_evaluadas": r.palmas_evaluadas,
        "palmas_improductivas": r.palmas_improductivas,
        "racimos_pequenos": r.racimos_pequenos,
        "racimos_medianos": r.racimos_medianos,
        "racimos_maduros": r.racimos_maduros,
        "racimos_totales": r.racimos_totales,
        "peso_promedio_racimo": r.peso_promedio_racimo,
        "fruto_suelto": r.fruto_suelto,
        "observaciones": r.observaciones,
        "fuente": r.fuente,
        "creado_en": r.creado_en.isoformat() if r.creado_en else None,
        "porcentaje_muestra": getattr(r, "_porcentaje_muestra", None),
    }
