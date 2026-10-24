from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import (
    Usuario,
    Transportador,
    Finca,
    Lote,
    PublicacionMercado,
    SolicitudTransporte,
    Comprador,
    Precio,
    ContenidoMensaje,
)
from app.utils import role_required, current_user_id
from app.routes.market import crear_precio, _serialize_precio
from app.services.contenido import obtener_contenido, CLAVES_CONTENIDO
from app.services.ussd_engine import MENU_PRINCIPAL_TEXTO_DEFECTO, AYUDA_TEXTO_DEFECTO
from app.routes.sms import AYUDA_TEXTO_DEFECTO as SMS_AYUDA_TEXTO_DEFECTO

admin_bp = Blueprint("admin", __name__)

_TEXTOS_POR_DEFECTO = {
    "ussd_menu_principal": MENU_PRINCIPAL_TEXTO_DEFECTO,
    "ussd_ayuda": AYUDA_TEXTO_DEFECTO,
    "sms_ayuda": SMS_AYUDA_TEXTO_DEFECTO,
}


@admin_bp.get("/admin/usuarios")
@role_required("administrador")
def listar_usuarios():
    rol = request.args.get("rol")
    query = Usuario.query
    if rol:
        query = query.filter_by(rol=rol)
    usuarios = query.order_by(Usuario.fecha_registro.desc()).all()
    return jsonify([_serialize_usuario(u) for u in usuarios])


@admin_bp.patch("/admin/usuarios/<int:usuario_id>/estado")
@role_required("administrador")
def cambiar_estado_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"message": "Usuario no encontrado."}), 404

    data = request.get_json(force=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("activo", "suspendido"):
        return jsonify({"message": "Estado inválido."}), 400

    usuario.estado = nuevo_estado
    db.session.commit()
    return jsonify(_serialize_usuario(usuario))


@admin_bp.get("/admin/transportadores/pendientes")
@role_required("administrador")
def transportadores_pendientes():
    pendientes = Transportador.query.filter_by(estado="pendiente").all()
    return jsonify([_serialize_transportador(t) for t in pendientes])


@admin_bp.get("/admin/transportadores")
@role_required("administrador")
def listar_transportadores():
    transportadores = Transportador.query.all()
    return jsonify([_serialize_transportador(t) for t in transportadores])


@admin_bp.patch("/admin/transportadores/<int:transportador_id>/validar")
@role_required("administrador")
def validar_transportador(transportador_id):
    t = Transportador.query.get(transportador_id)
    if not t:
        return jsonify({"message": "Transportador no encontrado."}), 404

    data = request.get_json(force=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("aprobado", "rechazado", "pendiente"):
        return jsonify({"message": "Estado inválido."}), 400

    t.estado = nuevo_estado
    db.session.commit()
    return jsonify(_serialize_transportador(t))


@admin_bp.get("/admin/reportes")
@role_required("administrador")
def reportes_generales():
    """Estadísticas agregadas — nunca información personal ni ubicaciones exactas."""
    total_usuarios = Usuario.query.count()
    por_rol = {
        rol: Usuario.query.filter_by(rol=rol).count()
        for rol in ("palmicultor", "comprador", "transportador", "administrador")
    }
    total_fincas = Finca.query.filter_by(estado="activa").count()
    total_lotes = Lote.query.filter_by(estado="activo").count()
    total_hectareas = db.session.query(db.func.coalesce(db.func.sum(Finca.area_hectareas), 0)).scalar()

    publicaciones_activas = PublicacionMercado.query.filter_by(estado="activa").count()
    publicaciones_vendidas = PublicacionMercado.query.filter_by(estado="vendida").count()
    toneladas_publicadas = (
        db.session.query(db.func.coalesce(db.func.sum(PublicacionMercado.cantidad_toneladas), 0))
        .filter(PublicacionMercado.estado == "activa")
        .scalar()
    )

    solicitudes_por_estado = {}
    for (estado,) in db.session.query(SolicitudTransporte.estado).distinct():
        solicitudes_por_estado[estado] = SolicitudTransporte.query.filter_by(estado=estado).count()

    transportadores_pendientes_count = Transportador.query.filter_by(estado="pendiente").count()
    compradores_activos = Comprador.query.filter_by(estado="activo").count()

    return jsonify(
        {
            "usuarios": {"total": total_usuarios, "por_rol": por_rol},
            "produccion": {
                "total_fincas": total_fincas,
                "total_lotes": total_lotes,
                "total_hectareas": float(total_hectareas or 0),
            },
            "mercado": {
                "publicaciones_activas": publicaciones_activas,
                "publicaciones_vendidas": publicaciones_vendidas,
                "toneladas_publicadas": float(toneladas_publicadas or 0),
            },
            "logistica": {
                "solicitudes_por_estado": solicitudes_por_estado,
                "transportadores_pendientes": transportadores_pendientes_count,
            },
            "compradores_activos": compradores_activos,
        }
    )


# ------------------------------------------------- compradores (CU13) ----

@admin_bp.get("/admin/compradores")
@role_required("administrador")
def listar_compradores_admin():
    compradores = Comprador.query.order_by(Comprador.id.desc()).all()
    return jsonify([_serialize_comprador(c) for c in compradores])


@admin_bp.post("/admin/compradores")
@role_required("administrador")
def crear_comprador_admin():
    """Crea el perfil `Comprador` para un usuario con rol comprador que no
    tenga uno todavía (en el registro normal ya se crea automáticamente —
    esto cubre solo el caso borde de un usuario sin perfil asociado)."""
    data = request.get_json(force=True) or {}
    usuario_id = data.get("usuario_id")
    usuario = Usuario.query.get(usuario_id) if usuario_id else None
    if not usuario or usuario.rol != "comprador":
        return jsonify({"message": "El usuario indicado no existe o no tiene rol comprador."}), 400
    if Comprador.query.filter_by(usuario_id=usuario.id).first():
        return jsonify({"message": "Ese usuario ya tiene un perfil de comprador."}), 409

    empresa = (data.get("empresa") or usuario.nombre_completo).strip()
    comprador = Comprador(
        usuario_id=usuario.id,
        empresa=empresa,
        descripcion=(data.get("descripcion") or "").strip() or None,
        telefono=(data.get("telefono") or "").strip() or None,
        correo=(data.get("correo") or "").strip() or None,
        ubicacion=(data.get("ubicacion") or "").strip() or None,
        estado="activo",
    )
    db.session.add(comprador)
    db.session.commit()
    return jsonify(_serialize_comprador(comprador)), 201


@admin_bp.put("/admin/compradores/<int:comprador_id>")
@role_required("administrador")
def editar_comprador_admin(comprador_id):
    comprador = Comprador.query.get(comprador_id)
    if not comprador:
        return jsonify({"message": "Comprador no encontrado."}), 404

    data = request.get_json(force=True) or {}
    for campo in ("empresa", "descripcion", "telefono", "correo", "ubicacion"):
        if campo in data:
            setattr(comprador, campo, (data[campo] or "").strip() or None)

    db.session.commit()
    return jsonify(_serialize_comprador(comprador))


@admin_bp.patch("/admin/compradores/<int:comprador_id>/estado")
@role_required("administrador")
def cambiar_estado_comprador_admin(comprador_id):
    comprador = Comprador.query.get(comprador_id)
    if not comprador:
        return jsonify({"message": "Comprador no encontrado."}), 404

    data = request.get_json(force=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("activo", "inactivo"):
        return jsonify({"message": "Estado inválido."}), 400

    comprador.estado = nuevo_estado
    db.session.commit()
    return jsonify(_serialize_comprador(comprador))


@admin_bp.post("/admin/compradores/<int:comprador_id>/precios")
@role_required("administrador")
def publicar_precio_admin(comprador_id):
    """CU12 ampliado: el administrador también puede publicar/editar el
    precio de cualquier comprador — el palmicultor sigue sin poder fijar
    precios, eso no cambia. Reutiliza exactamente la misma lógica que usa
    el comprador para su propio precio (`market.crear_precio`)."""
    comprador = Comprador.query.get(comprador_id)
    if not comprador:
        return jsonify({"message": "Comprador no encontrado."}), 404

    data = request.get_json(force=True) or {}
    valor = data.get("valor_moneda")
    if not valor or float(valor) <= 0:
        return jsonify({"message": "El valor del precio es obligatorio."}), 400

    precio = crear_precio(comprador, valor, data.get("producto"), data.get("unidad"))
    return jsonify(_serialize_precio(precio)), 201


# ---------------------------------------- contenido SMS/USSD (CU17) ------

@admin_bp.get("/admin/contenido-sms-ussd")
@role_required("administrador")
def listar_contenido_sms_ussd():
    return jsonify(
        [
            {
                "clave": clave,
                "canal": canal,
                "texto": obtener_contenido(clave, _TEXTOS_POR_DEFECTO[clave]),
                "texto_por_defecto": _TEXTOS_POR_DEFECTO[clave],
                "personalizado": ContenidoMensaje.query.filter_by(clave=clave).first() is not None,
            }
            for clave, canal in CLAVES_CONTENIDO.items()
        ]
    )


@admin_bp.put("/admin/contenido-sms-ussd/<clave>")
@role_required("administrador")
def editar_contenido_sms_ussd(clave):
    if clave not in CLAVES_CONTENIDO:
        return jsonify({"message": "Clave de contenido inválida."}), 400

    data = request.get_json(force=True) or {}
    texto = (data.get("texto") or "").strip()
    if not texto:
        return jsonify({"message": "El texto es obligatorio."}), 400

    fila = ContenidoMensaje.query.filter_by(clave=clave).first()
    if fila:
        fila.texto = texto
        fila.actualizado_por = current_user_id()
    else:
        fila = ContenidoMensaje(
            clave=clave,
            canal=CLAVES_CONTENIDO[clave],
            texto=texto,
            actualizado_por=current_user_id(),
        )
        db.session.add(fila)
    db.session.commit()
    return jsonify({"clave": clave, "texto": fila.texto, "personalizado": True})


@admin_bp.delete("/admin/contenido-sms-ussd/<clave>")
@role_required("administrador")
def restaurar_contenido_sms_ussd(clave):
    if clave not in CLAVES_CONTENIDO:
        return jsonify({"message": "Clave de contenido inválida."}), 400

    ContenidoMensaje.query.filter_by(clave=clave).delete()
    db.session.commit()
    return jsonify({"clave": clave, "texto": _TEXTOS_POR_DEFECTO[clave], "personalizado": False})


def _serialize_usuario(u: Usuario):
    return {
        "id": u.id,
        "nombre_completo": u.nombre_completo,
        "telefono": u.telefono,
        "correo": u.correo,
        "rol": u.rol,
        "estado": u.estado,
        "fecha_registro": u.fecha_registro.isoformat() if u.fecha_registro else None,
    }


def _serialize_comprador(c: Comprador):
    usuario = Usuario.query.get(c.usuario_id)
    precio_activo = Precio.query.filter_by(comprador_id=c.id, estado="activo").first()
    return {
        "id": c.id,
        "usuario_id": c.usuario_id,
        "nombre_usuario": usuario.nombre_completo if usuario else None,
        "empresa": c.empresa,
        "descripcion": c.descripcion,
        "telefono": c.telefono,
        "correo": c.correo,
        "ubicacion": c.ubicacion,
        "estado": c.estado,
        "precio_vigente": float(precio_activo.valor_moneda) if precio_activo else None,
        "precio_unidad": precio_activo.unidad if precio_activo else None,
    }


def _serialize_transportador(t: Transportador):
    usuario = Usuario.query.get(t.usuario_id)
    return {
        "id": t.id,
        "usuario_id": t.usuario_id,
        "nombre_completo": usuario.nombre_completo if usuario else None,
        "telefono": usuario.telefono if usuario else None,
        "ubicacion": t.ubicacion,
        "disponible": t.disponible,
        "estado": t.estado,
        "total_vehiculos": len(t.vehiculos),
    }
