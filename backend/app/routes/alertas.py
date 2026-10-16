from datetime import date

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import CicloCosecha, Lote, Finca, Notificacion, Usuario
from app.utils import role_required, current_user_id
from app.routes.sms import notificar_por_sms

alertas_bp = Blueprint("alertas", __name__)


@alertas_bp.get("/alertas")
@role_required("palmicultor", "comprador", "transportador", "administrador")
def listar_alertas():
    _generar_alertas_cosecha(current_user_id())

    query = Notificacion.query.filter_by(usuario_id=current_user_id())
    solo_no_leidas = request.args.get("no_leidas") == "true"
    if solo_no_leidas:
        query = query.filter_by(leida=False)
    alertas = query.order_by(Notificacion.fecha.desc()).all()
    return jsonify([_serialize(a) for a in alertas])


@alertas_bp.patch("/alertas/<int:alerta_id>/leida")
@role_required("palmicultor", "comprador", "transportador", "administrador")
def marcar_leida(alerta_id):
    alerta = Notificacion.query.filter_by(id=alerta_id, usuario_id=current_user_id()).first()
    if not alerta:
        return jsonify({"message": "Alerta no encontrada."}), 404
    alerta.leida = True
    db.session.commit()
    return jsonify(_serialize(alerta))


@alertas_bp.post("/alertas/leer-todas")
@role_required("palmicultor", "comprador", "transportador", "administrador")
def marcar_todas_leidas():
    Notificacion.query.filter_by(usuario_id=current_user_id(), leida=False).update({"leida": True})
    db.session.commit()
    return jsonify({"message": "Alertas marcadas como leídas."})


def _generar_alertas_cosecha(usuario_id):
    """RN03: genera una alerta por cada ciclo próximo a cosechar (dentro de su
    ventana de anticipación configurada, 1-7 días) que todavía no la tenga."""
    hoy = date.today()

    ciclos = (
        CicloCosecha.query.join(Lote)
        .join(Finca)
        .filter(Finca.usuario_id == usuario_id, CicloCosecha.estado.in_(["Programado", "Próximo"]))
        .all()
    )

    for ciclo in ciclos:
        if not ciclo.proxima_fecha_estimada:
            continue
        dias_restantes = (ciclo.proxima_fecha_estimada - hoy).days
        anticipacion = ciclo.dias_anticipacion_alerta or 3

        if dias_restantes < 0:
            ciclo.estado = "Retrasado"
        elif dias_restantes <= anticipacion:
            ciclo.estado = "Próximo"

        ya_existe = Notificacion.query.filter_by(ciclo_cosecha_id=ciclo.id, tipo="cosecha").first()
        if ya_existe:
            continue

        if 0 <= dias_restantes <= anticipacion or dias_restantes < 0:
            lote = Lote.query.get(ciclo.lote_id)
            if dias_restantes < 0:
                titulo = f"Cosecha retrasada — {lote.codigo}"
                mensaje = f"El lote {lote.codigo} debió cosecharse el {ciclo.proxima_fecha_estimada.strftime('%d/%m/%Y')}."
            else:
                titulo = f"Próxima cosecha — {lote.codigo}"
                mensaje = f"El lote {lote.codigo} estará listo para cosechar el {ciclo.proxima_fecha_estimada.strftime('%d/%m/%Y')} (en {dias_restantes} días)."
            db.session.add(
                Notificacion(
                    usuario_id=usuario_id,
                    ciclo_cosecha_id=ciclo.id,
                    lote_id=lote.id,
                    tipo="cosecha",
                    titulo=titulo,
                    mensaje=mensaje,
                    enlace="Pronosticos",
                )
            )
            # Mismo aviso también por SMS real (si Twilio está habilitado):
            # es el mismo usuario y la misma alerta que ya se generó, solo
            # un canal de entrega adicional — no un envío masivo nuevo.
            notificar_por_sms(Usuario.query.get(usuario_id), titulo, mensaje)

    db.session.commit()


def _serialize(a: Notificacion):
    return {
        "id": a.id,
        "tipo": a.tipo,
        "titulo": a.titulo,
        "mensaje": a.mensaje,
        "enlace": a.enlace,
        "leida": a.leida,
        "fecha": a.fecha.isoformat() if a.fecha else None,
        "lote_id": a.lote_id,
        "ciclo_cosecha_id": a.ciclo_cosecha_id,
    }
