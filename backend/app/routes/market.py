import math

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Precio, Comprador, PublicacionMercado, Lote, Finca, InteresComprador, Notificacion, Usuario
from app.utils import role_required, current_user_id, paginate_args, jwt_required_activo
from app.validators import validar_numero_positivo

market_bp = Blueprint("market", __name__)


@market_bp.get("/precios/vigente")
def precio_vigente():
    precio = (
        Precio.query.filter_by(estado="activo")
        .order_by(Precio.fecha_publicacion.desc())
        .first()
    )
    if not precio:
        return jsonify({"valor": None, "unidad": "Tonelada", "fecha": None}), 200

    return jsonify(
        {
            "valor": float(precio.valor_moneda),
            "unidad": precio.unidad,
            "fecha": precio.fecha_publicacion.strftime("%d/%m/%Y"),
        }
    )


@market_bp.get("/compradores/cercanos")
def compradores_cercanos():
    # F5-07: antes `distanciaKm` era siempre 0 (placeholder). Si el cliente
    # envía su posición (lat/lon) y el comprador tiene coordenadas propias,
    # se calcula la distancia real (Haversine); si falta cualquiera de los
    # dos datos, se devuelve null en vez de un 0 engañoso, y no se ordena por
    # una distancia que no existe.
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)

    compradores = Comprador.query.filter_by(estado="activo").limit(10).all()
    resultados = []
    for c in compradores:
        distancia = None
        if lat is not None and lon is not None and c.latitud is not None and c.longitud is not None:
            distancia = round(_haversine_km(lat, lon, c.latitud, c.longitud), 1)
        resultados.append(
            {
                "id": c.id,
                "nombre": c.empresa,
                "distanciaKm": distancia,
                "verificado": True,
                "logoUrl": None,
            }
        )

    if lat is not None and lon is not None:
        resultados.sort(key=lambda r: (r["distanciaKm"] is None, r["distanciaKm"]))
    return jsonify(resultados)


@market_bp.get("/precios/mios")
@role_required("comprador")
def mis_precios():
    """Historial de precios publicados por el comprador autenticado.
    Solo el comprador fija precios — el palmicultor nunca pone precio en sus
    publicaciones; revisa el precio vigente de cada comprador y decide a
    quién vender."""
    comprador = _get_own_comprador()
    if not comprador:
        return jsonify({"message": "Perfil de comprador no encontrado."}), 404
    precios = (
        Precio.query.filter_by(comprador_id=comprador.id)
        .order_by(Precio.fecha_publicacion.desc())
        .all()
    )
    return jsonify([_serialize_precio(p) for p in precios])


@market_bp.post("/precios/mios")
@role_required("comprador")
def publicar_precio():
    comprador = _get_own_comprador()
    if not comprador:
        return jsonify({"message": "Perfil de comprador no encontrado."}), 404

    data = request.get_json(force=True) or {}
    valor, error = validar_numero_positivo(data.get("valor_moneda"), "El valor del precio")
    if error or valor is None:
        return jsonify({"message": error or "El valor del precio es obligatorio."}), 400
    # F5-11: un `producto` desmedido llegaba sin chequeo hasta Postgres y
    # producía un 500 en vez de un 400 controlado.
    if len(data.get("producto") or "") > 100:
        return jsonify({"message": "El nombre del producto es demasiado largo (máx. 100 caracteres)."}), 400

    precio = crear_precio(comprador, valor, data.get("producto"), data.get("unidad"))
    return jsonify(_serialize_precio(precio)), 201


def crear_precio(comprador, valor, producto=None, unidad=None):
    """Publica un precio nuevo para `comprador` y desactiva el anterior.
    Reutilizada por el propio comprador (arriba) y por el administrador
    (`admin.py`, CU12 ampliado: el admin también puede publicar/editar el
    precio de cualquier comprador) — misma lógica, un solo lugar."""
    # Solo un precio activo por comprador: el nuevo reemplaza al anterior.
    Precio.query.filter_by(comprador_id=comprador.id, estado="activo").update({"estado": "inactivo"})

    precio = Precio(
        comprador_id=comprador.id,
        producto=(producto or "Fruto de palma de aceite").strip(),
        valor_moneda=float(valor),
        unidad=(unidad or "Tonelada").strip(),
        fuente=comprador.empresa,
        estado="activo",
    )
    db.session.add(precio)
    db.session.commit()
    return precio


@market_bp.get("/compradores/<int:comprador_id>")
@jwt_required_activo
def detalle_comprador(comprador_id):
    comprador = Comprador.query.filter_by(id=comprador_id, estado="activo").first()
    if not comprador:
        return jsonify({"message": "Comprador no encontrado."}), 404
    precio_actual = (
        Precio.query.filter_by(comprador_id=comprador.id, estado="activo")
        .order_by(Precio.fecha_publicacion.desc())
        .first()
    )
    return jsonify(
        {
            "id": comprador.id,
            "empresa": comprador.empresa,
            "descripcion": comprador.descripcion,
            "telefono": comprador.telefono,
            "correo": comprador.correo,
            "ubicacion": comprador.ubicacion,
            "precio_vigente": float(precio_actual.valor_moneda) if precio_actual else None,
            "unidad": precio_actual.unidad if precio_actual else None,
        }
    )


# ---------------------------------------------------------- publicaciones --

@market_bp.get("/mercado/publicaciones")
@role_required("palmicultor")
def mis_publicaciones():
    publicaciones = (
        PublicacionMercado.query.filter_by(palmicultor_id=current_user_id())
        .order_by(PublicacionMercado.fecha_publicacion.desc())
        .all()
    )
    return jsonify([_serialize(p) for p in publicaciones])


@market_bp.post("/mercado/publicaciones")
@role_required("palmicultor")
def crear_publicacion():
    data = request.get_json(force=True) or {}

    cantidad = data.get("cantidad_toneladas")
    if not cantidad or float(cantidad) <= 0:
        return jsonify({"message": "La cantidad en toneladas es obligatoria."}), 400

    lote_id = data.get("lote_id")
    if lote_id:
        lote = db.session.get(Lote, lote_id)
        if not lote or not Finca.query.filter_by(id=lote.finca_id, usuario_id=current_user_id()).first():
            return jsonify({"message": "El lote indicado no existe o no te pertenece."}), 400

    publicacion = PublicacionMercado(
        palmicultor_id=current_user_id(),
        lote_id=lote_id,
        cantidad_toneladas=float(cantidad),
        unidad=data.get("unidad") or "Tonelada",
        # RN01: nunca se guarda ubicación exacta de la finca en la publicación pública, solo el municipio.
        municipio=(data.get("municipio") or "Tumaco").strip(),
        descripcion=(data.get("descripcion") or "").strip() or None,
        estado="activa",
    )
    db.session.add(publicacion)
    db.session.commit()
    return jsonify(_serialize(publicacion)), 201


@market_bp.put("/mercado/publicaciones/<int:publicacion_id>")
@role_required("palmicultor")
def editar_publicacion(publicacion_id):
    publicacion = _get_own_publicacion(publicacion_id)
    if not publicacion:
        return jsonify({"message": "Publicación no encontrada."}), 404

    data = request.get_json(force=True) or {}
    for campo in ("cantidad_toneladas", "unidad", "municipio", "descripcion"):
        if campo in data:
            setattr(publicacion, campo, data[campo])

    db.session.commit()
    return jsonify(_serialize(publicacion))


@market_bp.patch("/mercado/publicaciones/<int:publicacion_id>/estado")
@role_required("palmicultor")
def cambiar_estado_publicacion(publicacion_id):
    publicacion = _get_own_publicacion(publicacion_id)
    if not publicacion:
        return jsonify({"message": "Publicación no encontrada."}), 404

    data = request.get_json(force=True) or {}
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("activa", "vendida", "cancelada"):
        return jsonify({"message": "Estado inválido."}), 400

    publicacion.estado = nuevo_estado
    db.session.commit()
    return jsonify(_serialize(publicacion))


@market_bp.get("/mercado/vitrina")
@role_required("comprador", "administrador")
def vitrina_publica():
    """Vitrina pública para compradores. RN01: nunca expone ubicación exacta,
    coordenadas ni información privada de producción — solo cantidad,
    unidad, municipio, descripción y fecha. El precio no aplica aquí: lo fija
    cada comprador (ver /precios/mios y /compradores/<id>), no la publicación."""
    limit, offset = paginate_args(request)
    municipio = request.args.get("municipio")

    query = PublicacionMercado.query.filter_by(estado="activa")
    if municipio:
        query = query.filter(PublicacionMercado.municipio.ilike(f"%{municipio}%"))

    total = query.count()
    publicaciones = (
        query.order_by(PublicacionMercado.fecha_publicacion.desc()).offset(offset).limit(limit).all()
    )
    # DEV-F4-09: antes devolvía una lista plana sin metadatos de paginación.
    return jsonify(
        {"items": [_serialize(p) for p in publicaciones], "limit": limit, "offset": offset, "total": total}
    )


@market_bp.get("/mercado/publicaciones/<int:publicacion_id>/detalle")
@role_required("comprador", "administrador")
def detalle_publicacion_publica(publicacion_id):
    publicacion = PublicacionMercado.query.filter_by(id=publicacion_id, estado="activa").first()
    if not publicacion:
        return jsonify({"message": "Publicación no encontrada."}), 404
    return jsonify(_serialize(publicacion))


# -------------------------------------------------------------- interés ----

@market_bp.post("/mercado/publicaciones/<int:publicacion_id>/interes")
@role_required("comprador")
def manifestar_interes(publicacion_id):
    """F5-06: antes no existía ningún endpoint ni tabla para que un comprador
    manifestara interés en una publicación — solo podía verla. Esto crea un
    registro formal (único por comprador/publicación) y notifica al
    palmicultor, igual que cualquier otra notificación del sistema."""
    comprador = _get_own_comprador()
    if not comprador:
        return jsonify({"message": "Perfil de comprador no encontrado."}), 404

    publicacion = PublicacionMercado.query.filter_by(id=publicacion_id, estado="activa").first()
    if not publicacion:
        return jsonify({"message": "Publicación no encontrada."}), 404

    existente = InteresComprador.query.filter_by(
        publicacion_id=publicacion.id, comprador_id=comprador.id
    ).first()
    if existente:
        return jsonify(_serialize_interes(existente)), 200

    data = request.get_json(silent=True) or {}
    mensaje_comprador = (data.get("mensaje") or "").strip() or None
    if mensaje_comprador and len(mensaje_comprador) > 500:
        return jsonify({"message": "El mensaje es demasiado largo (máx. 500 caracteres)."}), 400

    interes = InteresComprador(
        publicacion_id=publicacion.id,
        comprador_id=comprador.id,
        mensaje=mensaje_comprador,
    )
    db.session.add(interes)

    titulo = "Interés de compra"
    mensaje = f"{comprador.empresa} mostró interés en tu publicación #{publicacion.id}."
    db.session.add(
        Notificacion(
            usuario_id=publicacion.palmicultor_id,
            tipo="mercado",
            titulo=titulo,
            mensaje=mensaje,
            enlace="MisPublicaciones",
        )
    )
    db.session.commit()

    from app.routes.sms import notificar_por_sms

    notificar_por_sms(db.session.get(Usuario, publicacion.palmicultor_id), titulo, mensaje)
    return jsonify(_serialize_interes(interes)), 201


@market_bp.get("/mercado/publicaciones/<int:publicacion_id>/intereses")
@role_required("palmicultor")
def listar_intereses(publicacion_id):
    publicacion = _get_own_publicacion(publicacion_id)
    if not publicacion:
        return jsonify({"message": "Publicación no encontrada."}), 404
    intereses = (
        InteresComprador.query.filter_by(publicacion_id=publicacion.id)
        .order_by(InteresComprador.fecha.desc())
        .all()
    )
    return jsonify([_serialize_interes(i) for i in intereses])


def _get_own_publicacion(publicacion_id):
    return PublicacionMercado.query.filter_by(id=publicacion_id, palmicultor_id=current_user_id()).first()


def _get_own_comprador():
    return Comprador.query.filter_by(usuario_id=current_user_id()).first()


def _haversine_km(lat1, lon1, lat2, lon2):
    radio_tierra_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radio_tierra_km * math.asin(math.sqrt(a))


def _serialize(p: PublicacionMercado):
    return {
        "id": p.id,
        "cantidad_toneladas": p.cantidad_toneladas,
        "unidad": p.unidad,
        "municipio": p.municipio,
        "descripcion": p.descripcion,
        "estado": p.estado,
        "fecha_publicacion": p.fecha_publicacion.isoformat() if p.fecha_publicacion else None,
    }


def _serialize_precio(p: Precio):
    return {
        "id": p.id,
        "producto": p.producto,
        "valor_moneda": float(p.valor_moneda),
        "unidad": p.unidad,
        "estado": p.estado,
        "fecha_publicacion": p.fecha_publicacion.isoformat() if p.fecha_publicacion else None,
    }


def _serialize_interes(i: InteresComprador):
    return {
        "id": i.id,
        "publicacion_id": i.publicacion_id,
        "comprador_id": i.comprador_id,
        "empresa": i.comprador.empresa if i.comprador else None,
        "telefono": i.comprador.telefono if i.comprador else None,
        "mensaje": i.mensaje,
        "estado": i.estado,
        "fecha": i.fecha.isoformat() if i.fecha else None,
    }
