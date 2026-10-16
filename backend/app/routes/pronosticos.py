from datetime import datetime

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Lote, Finca, RegistroProduccion, PronosticoProduccion
from app.utils import role_required, current_user_id

pronosticos_bp = Blueprint("pronosticos", __name__)

# RN04 — distribución mensual histórica de producción en el Pacífico nariñense.
DISTRIBUCION_MENSUAL_PACIFICO = [
    ("Julio", 14),
    ("Agosto", 16),
    ("Septiembre", 20),
    ("Octubre", 25),
    ("Noviembre", 13),
    ("Diciembre", 12),
]


@pronosticos_bp.get("/pronosticos")
@role_required("palmicultor")
def listar_pronosticos():
    lote_id = request.args.get("lote_id", type=int)
    query = PronosticoProduccion.query.join(Lote).join(Finca).filter(Finca.usuario_id == current_user_id())
    if lote_id:
        query = query.filter(PronosticoProduccion.lote_id == lote_id)
    pronosticos = query.order_by(PronosticoProduccion.fecha_calculo.desc()).all()
    return jsonify([_serialize(p) for p in pronosticos])


@pronosticos_bp.get("/pronosticos/<int:pronostico_id>")
@role_required("palmicultor")
def obtener_pronostico(pronostico_id):
    pronostico = _get_own_pronostico(pronostico_id)
    if not pronostico:
        return jsonify({"message": "Pronóstico no encontrado."}), 404
    return jsonify(_serialize(pronostico, detalle=True))


@pronosticos_bp.post("/pronosticos")
@role_required("palmicultor")
def calcular_pronostico():
    """Implementa exactamente la lógica RN04 (pronóstico oficial a 6 meses)."""
    data = request.get_json(force=True) or {}

    lote = Lote.query.get(data.get("lote_id"))
    if not lote or not Finca.query.filter_by(id=lote.finca_id, usuario_id=current_user_id()).first():
        return jsonify({"message": "El lote indicado no existe o no te pertenece."}), 400

    registro = None
    registro_id = data.get("registro_produccion_id")
    if registro_id:
        registro = RegistroProduccion.query.filter_by(id=registro_id, lote_id=lote.id).first()
    else:
        registro = (
            RegistroProduccion.query.filter_by(lote_id=lote.id)
            .order_by(RegistroProduccion.fecha.desc(), RegistroProduccion.id.desc())
            .first()
        )
    if not registro:
        return jsonify({"message": "Este lote no tiene un censo de producción registrado todavía."}), 400

    palmas_totales = data.get("palmas_totales") or lote.numero_palmas
    if not palmas_totales:
        return jsonify({"message": "Registra el número total de palmas del lote antes de calcular el pronóstico."}), 400
    palmas_totales = int(palmas_totales)

    palmas_improductivas_muestra = int(registro.palmas_improductivas or 0)
    palmas_productivas_muestreadas = int(registro.palmas_evaluadas or 0) - palmas_improductivas_muestra
    if palmas_productivas_muestreadas <= 0:
        return jsonify({"message": "El censo no tiene palmas productivas en la muestra; revisa los datos."}), 400

    peso_promedio = data.get("peso_promedio_racimo") or registro.peso_promedio_racimo
    if not peso_promedio or float(peso_promedio) <= 0:
        return jsonify({"message": "Falta el peso promedio histórico del racimo (kg)."}), 400
    peso_promedio = float(peso_promedio)

    # 1. Palmas Productivas = Palmas Totales - Palmas Improductivas en muestra
    palmas_productivas = palmas_totales - palmas_improductivas_muestra

    # 2. Promedio de Estructuras = Racimos en muestra / Palmas Productivas Muestreadas
    estructuras_muestra = int(registro.racimos_totales or 0)
    promedio_estructuras = estructuras_muestra / palmas_productivas_muestreadas

    # 3. Total de Racimos en Lote = Palmas Productivas × Promedio de Estructuras
    racimos_estimados = palmas_productivas * promedio_estructuras

    # 4. Producción Estimada = Total Racimos × Peso Promedio Histórico del Racimo
    produccion_estimada_kg = racimos_estimados * peso_promedio
    produccion_estimada_ton = produccion_estimada_kg / 1000

    # 5. Distribución mensual histórica del Pacífico nariñense.
    distribucion_mensual = [
        {
            "mes": mes,
            "porcentaje": pct,
            "produccion_kg": round(produccion_estimada_kg * pct / 100, 2),
            "produccion_ton": round(produccion_estimada_ton * pct / 100, 3),
        }
        for mes, pct in DISTRIBUCION_MENSUAL_PACIFICO
    ]

    pronostico = PronosticoProduccion(
        lote_id=lote.id,
        registro_produccion_id=registro.id,
        fecha_calculo=datetime.utcnow(),
        palmas_totales=palmas_totales,
        palmas_improductivas_muestra=palmas_improductivas_muestra,
        palmas_productivas=palmas_productivas,
        palmas_productivas_muestreadas=palmas_productivas_muestreadas,
        promedio_estructuras=round(promedio_estructuras, 4),
        racimos_estimados=round(racimos_estimados, 2),
        peso_promedio=peso_promedio,
        produccion_estimada_kg=round(produccion_estimada_kg, 2),
        produccion_estimada_ton=round(produccion_estimada_ton, 3),
        distribucion_mensual=distribucion_mensual,
        observaciones=(data.get("observaciones") or "").strip() or None,
    )
    db.session.add(pronostico)
    db.session.commit()
    return jsonify(_serialize(pronostico, detalle=True)), 201


def _get_own_pronostico(pronostico_id):
    pronostico = PronosticoProduccion.query.get(pronostico_id)
    if not pronostico:
        return None
    lote = Lote.query.get(pronostico.lote_id)
    if not lote or not Finca.query.filter_by(id=lote.finca_id, usuario_id=current_user_id()).first():
        return None
    return pronostico


def _serialize(p: PronosticoProduccion, detalle=False):
    data = {
        "id": p.id,
        "lote_id": p.lote_id,
        "fecha_calculo": p.fecha_calculo.isoformat() if p.fecha_calculo else None,
        "produccion_estimada_kg": p.produccion_estimada_kg,
        "produccion_estimada_ton": p.produccion_estimada_ton,
        "distribucion_mensual": p.distribucion_mensual,
    }
    if detalle:
        data.update(
            {
                "registro_produccion_id": p.registro_produccion_id,
                "palmas_totales": p.palmas_totales,
                "palmas_improductivas_muestra": p.palmas_improductivas_muestra,
                "palmas_productivas": p.palmas_productivas,
                "palmas_productivas_muestreadas": p.palmas_productivas_muestreadas,
                "promedio_estructuras": p.promedio_estructuras,
                "racimos_estimados": p.racimos_estimados,
                "peso_promedio": p.peso_promedio,
                "metodologia": p.metodologia,
                "observaciones": p.observaciones,
                "formula": {
                    "paso_1": "Palmas Productivas = Palmas Totales - Palmas Improductivas en muestra",
                    "paso_2": "Promedio de Estructuras = Racimos en muestra / Palmas Productivas Muestreadas",
                    "paso_3": "Total de Racimos en Lote = Palmas Productivas × Promedio de Estructuras",
                    "paso_4": "Producción Estimada = Total Racimos × Peso Promedio Histórico del Racimo",
                    "paso_5": "Distribución mensual histórica del Pacífico nariñense (jul-dic)",
                },
            }
        )
    return data
