import random
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required

from app.extensions import db
from app.models import Usuario, Comprador, Transportador, PasswordResetToken
from app.utils import current_user_id

auth_bp = Blueprint("auth", __name__)

ROLES_VALIDOS = {"palmicultor", "comprador", "transportador", "administrador"}
CODE_TTL_MINUTES = 15


@auth_bp.post("/register")
def register():
    data = request.get_json(force=True) or {}

    nombre_completo = (data.get("nombre_completo") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    ubicacion = (data.get("ubicacion") or "").strip()
    password = data.get("password") or ""
    rol = (data.get("rol") or "").strip().lower()

    if not nombre_completo or not telefono or not password:
        return jsonify({"message": "Nombre, teléfono y contraseña son obligatorios."}), 400

    if rol not in ROLES_VALIDOS:
        return jsonify({"message": "Rol inválido."}), 400

    if len(password) < 6:
        return jsonify({"message": "La contraseña debe tener al menos 6 caracteres."}), 400

    if Usuario.query.filter_by(telefono=telefono).first():
        return jsonify({"message": "Ya existe una cuenta con ese teléfono."}), 409

    usuario = Usuario(
        nombre_completo=nombre_completo,
        telefono=telefono,
        password_hash=generate_password_hash(password),
        rol=rol,
        estado="activo",
    )
    db.session.add(usuario)
    db.session.flush()  # obtiene usuario.id antes del commit

    # Crea el perfil específico según el rol (ubicacion se guarda como referencia inicial)
    if rol == "comprador":
        db.session.add(Comprador(usuario_id=usuario.id, empresa=nombre_completo, ubicacion=ubicacion))
    elif rol == "transportador":
        # Los transportadores quedan "pendiente" hasta validación del administrador.
        db.session.add(Transportador(usuario_id=usuario.id, ubicacion=ubicacion, estado="pendiente"))

    db.session.commit()

    token = create_access_token(identity=str(usuario.id), additional_claims={"rol": usuario.rol})
    return jsonify({"token": token, "usuario": _serialize(usuario)}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    identifier = (data.get("identifier") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"message": "Ingresa tu teléfono/correo y tu contraseña."}), 400

    usuario = Usuario.query.filter(
        (Usuario.telefono == identifier) | (Usuario.correo == identifier)
    ).first()

    if not usuario or not check_password_hash(usuario.password_hash, password):
        return jsonify({"message": "Credenciales incorrectas."}), 401

    if usuario.estado != "activo":
        return jsonify({"message": "Tu cuenta no está activa. Contacta al administrador."}), 403

    token = create_access_token(identity=str(usuario.id), additional_claims={"rol": usuario.rol})
    return jsonify({"token": token, "usuario": _serialize(usuario)}), 200


@auth_bp.patch("/perfil")
@jwt_required()
def editar_perfil():
    """CU9: cualquier usuario autenticado edita sus propios datos básicos.
    El rol NUNCA se puede cambiar por esta vía, aunque venga en el body —
    requisito explícito del caso de uso (un usuario común no puede
    autoasignarse otro rol)."""
    usuario = Usuario.query.get(current_user_id())
    if not usuario:
        return jsonify({"message": "Usuario no encontrado."}), 404

    data = request.get_json(force=True) or {}

    if "nombre_completo" in data:
        nombre_completo = (data.get("nombre_completo") or "").strip()
        if not nombre_completo:
            return jsonify({"message": "El nombre no puede quedar vacío."}), 400
        usuario.nombre_completo = nombre_completo

    if "telefono" in data:
        telefono = (data.get("telefono") or "").strip()
        if not telefono:
            return jsonify({"message": "El teléfono no puede quedar vacío."}), 400
        existente = Usuario.query.filter(Usuario.telefono == telefono, Usuario.id != usuario.id).first()
        if existente:
            return jsonify({"message": "Ya existe una cuenta con ese teléfono."}), 409
        usuario.telefono = telefono

    if "correo" in data:
        correo = (data.get("correo") or "").strip() or None
        if correo:
            existente = Usuario.query.filter(Usuario.correo == correo, Usuario.id != usuario.id).first()
            if existente:
                return jsonify({"message": "Ya existe una cuenta con ese correo."}), 409
        usuario.correo = correo

    db.session.commit()
    return jsonify(_serialize(usuario))


@auth_bp.post("/forgot-password")
def forgot_password():
    """Genera un código de recuperación (RN: recuperar contraseña).

    MOCK: no hay proveedor real de SMS/correo conectado todavía, así que el
    código se devuelve directamente en la respuesta (`dev_codigo`) para que el
    flujo se pueda probar de extremo a extremo. Cuando se conecte un
    proveedor real (Twilio, SES, etc.) basta con enviar `codigo` por ese canal
    en vez de incluirlo en la respuesta HTTP.
    """
    data = request.get_json(force=True) or {}
    identifier = (data.get("identifier") or "").strip()

    usuario = Usuario.query.filter(
        (Usuario.telefono == identifier) | (Usuario.correo == identifier)
    ).first()

    # Por seguridad respondemos 200 exista o no la cuenta.
    if not usuario:
        return jsonify({"message": "Si la cuenta existe, se envió un código de verificación."}), 200

    codigo = f"{random.randint(0, 999999):06d}"
    token = PasswordResetToken(
        usuario_id=usuario.id,
        codigo=codigo,
        expira_en=datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES),
    )
    db.session.add(token)
    db.session.commit()

    return jsonify(
        {
            "message": "Si la cuenta existe, se envió un código de verificación.",
            "dev_codigo": codigo,  # MOCK — remover al conectar proveedor SMS/correo real
            "expira_minutos": CODE_TTL_MINUTES,
        }
    ), 200


@auth_bp.post("/verify-code")
def verify_code():
    data = request.get_json(force=True) or {}
    identifier = (data.get("identifier") or "").strip()
    codigo = (data.get("codigo") or "").strip()

    usuario = Usuario.query.filter(
        (Usuario.telefono == identifier) | (Usuario.correo == identifier)
    ).first()
    if not usuario:
        return jsonify({"message": "Código inválido o expirado."}), 400

    token = (
        PasswordResetToken.query.filter_by(usuario_id=usuario.id, codigo=codigo, usado=False)
        .order_by(PasswordResetToken.creado_en.desc())
        .first()
    )
    if not token or token.expira_en < datetime.utcnow():
        return jsonify({"message": "Código inválido o expirado."}), 400

    return jsonify({"message": "Código válido.", "valido": True}), 200


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(force=True) or {}
    identifier = (data.get("identifier") or "").strip()
    codigo = (data.get("codigo") or "").strip()
    nueva_password = data.get("password") or ""

    if len(nueva_password) < 6:
        return jsonify({"message": "La contraseña debe tener al menos 6 caracteres."}), 400

    usuario = Usuario.query.filter(
        (Usuario.telefono == identifier) | (Usuario.correo == identifier)
    ).first()
    if not usuario:
        return jsonify({"message": "Código inválido o expirado."}), 400

    token = (
        PasswordResetToken.query.filter_by(usuario_id=usuario.id, codigo=codigo, usado=False)
        .order_by(PasswordResetToken.creado_en.desc())
        .first()
    )
    if not token or token.expira_en < datetime.utcnow():
        return jsonify({"message": "Código inválido o expirado."}), 400

    usuario.password_hash = generate_password_hash(nueva_password)
    token.usado = True
    db.session.commit()

    return jsonify({"message": "Contraseña actualizada correctamente."}), 200


def _serialize(usuario: Usuario):
    return {
        "id": usuario.id,
        "nombre_completo": usuario.nombre_completo,
        "telefono": usuario.telefono,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "estado": usuario.estado,
    }
