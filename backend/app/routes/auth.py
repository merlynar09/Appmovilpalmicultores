import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from app.extensions import db, limiter
from app.models import Usuario, Comprador, Transportador, PasswordResetToken
from app.utils import current_user_id, jwt_required_activo
from app.validators import telefono_valido, correo_valido

auth_bp = Blueprint("auth", __name__)

# DEV-F4-01: el registro público NUNCA puede crear una cuenta administrador —
# antes "administrador" estaba en la misma lista que los roles de autoservicio
# y cualquiera podía autoasignárselo. ROLES_VALIDOS se conserva para el resto
# del código que sí necesita conocer el universo completo de roles.
ROLES_VALIDOS = {"palmicultor", "comprador", "transportador", "administrador"}
ROLES_AUTOSERVICIO = {"palmicultor", "comprador", "transportador"}
CODE_TTL_MINUTES = 15


@auth_bp.post("/register")
@limiter.limit("10 per minute")
def register():
    data = request.get_json(force=True) or {}

    nombre_completo = (data.get("nombre_completo") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    ubicacion = (data.get("ubicacion") or "").strip()
    password = data.get("password") or ""
    rol = (data.get("rol") or "").strip().lower()

    if not nombre_completo or not telefono or not password:
        return jsonify({"message": "Nombre, teléfono y contraseña son obligatorios."}), 400

    if rol not in ROLES_AUTOSERVICIO:
        return jsonify({"message": "Rol inválido."}), 400

    if not telefono_valido(telefono):
        return jsonify({"message": "El teléfono no tiene un formato válido."}), 400

    if len(password) < 6:
        return jsonify({"message": "La contraseña debe tener al menos 6 caracteres."}), 400

    # F5-12: un comprador sin ubicación no se puede ni contactar ni ubicar en
    # "compradores cercanos" — se exige desde el registro, no solo en el alta
    # administrativa.
    if rol == "comprador" and not ubicacion:
        return jsonify({"message": "La ubicación es obligatoria para una cuenta de comprador."}), 400

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

    token = _emitir_token(usuario)
    return jsonify({"token": token, "usuario": _serialize(usuario)}), 201


@auth_bp.post("/login")
@limiter.limit("10 per minute")
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

    token = _emitir_token(usuario)
    return jsonify({"token": token, "usuario": _serialize(usuario)}), 200


@auth_bp.post("/logout")
@jwt_required_activo
def logout():
    """DEV-F4-03: revocación real de sesión a petición del propio usuario —
    antes "cerrar sesión" solo borraba el token en el dispositivo (AsyncStorage/
    SecureStore); el mismo token, si alguien más lo tenía, seguía funcionando
    contra el backend hasta expirar (hasta 7 días). Incrementar
    `token_version` invalida este y cualquier otro token emitido antes."""
    usuario = db.session.get(Usuario, current_user_id())
    if usuario:
        usuario.token_version += 1
        db.session.commit()
    return jsonify({"message": "Sesión cerrada."}), 200


@auth_bp.patch("/perfil")
@jwt_required_activo
def editar_perfil():
    """CU9: cualquier usuario autenticado edita sus propios datos básicos.
    El rol NUNCA se puede cambiar por esta vía, aunque venga en el body —
    requisito explícito del caso de uso (un usuario común no puede
    autoasignarse otro rol)."""
    usuario = db.session.get(Usuario, current_user_id())
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
        if not telefono_valido(telefono):
            return jsonify({"message": "El teléfono no tiene un formato válido."}), 400
        existente = Usuario.query.filter(Usuario.telefono == telefono, Usuario.id != usuario.id).first()
        if existente:
            return jsonify({"message": "Ya existe una cuenta con ese teléfono."}), 409
        usuario.telefono = telefono

    if "correo" in data:
        correo = (data.get("correo") or "").strip() or None
        if correo:
            if not correo_valido(correo):
                return jsonify({"message": "El correo no tiene un formato válido."}), 400
            existente = Usuario.query.filter(Usuario.correo == correo, Usuario.id != usuario.id).first()
            if existente:
                return jsonify({"message": "Ya existe una cuenta con ese correo."}), 409
        usuario.correo = correo

    db.session.commit()
    return jsonify(_serialize(usuario))


@auth_bp.post("/forgot-password")
@limiter.limit("10 per minute")
def forgot_password():
    """Genera un código de recuperación (RN: recuperar contraseña).

    DEV-F4-04: el código se guarda con hash (igual que la contraseña) y NUNCA
    viaja en la respuesta HTTP fuera de FLASK_ENV=development — antes salía
    en texto plano como `dev_codigo` siempre, también en producción. Cada
    código nuevo invalida los anteriores sin usar del mismo usuario.
    """
    data = request.get_json(force=True) or {}
    identifier = (data.get("identifier") or "").strip()

    usuario = Usuario.query.filter(
        (Usuario.telefono == identifier) | (Usuario.correo == identifier)
    ).first()

    # Por seguridad respondemos 200 exista o no la cuenta.
    if not usuario:
        return jsonify({"message": "Si la cuenta existe, se envió un código de verificación."}), 200

    # Invalida cualquier código previo sin usar — nunca deben quedar varios
    # códigos simultáneamente válidos para la misma cuenta.
    PasswordResetToken.query.filter_by(usuario_id=usuario.id, usado=False).update({"usado": True})

    codigo = f"{secrets.randbelow(1_000_000):06d}"
    token = PasswordResetToken(
        usuario_id=usuario.id,
        codigo=generate_password_hash(codigo),
        expira_en=datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES),
    )
    db.session.add(token)
    db.session.commit()

    respuesta = {
        "message": "Si la cuenta existe, se envió un código de verificación.",
        "expira_minutos": CODE_TTL_MINUTES,
    }
    # Sin proveedor real de SMS/correo conectado todavía: en desarrollo se
    # expone el código para poder probar el flujo de punta a punta. Fuera de
    # FLASK_ENV=development esto nunca se incluye.
    if current_app.config.get("ENV_ES_DESARROLLO"):
        respuesta["dev_codigo"] = codigo
    return jsonify(respuesta), 200


@auth_bp.post("/verify-code")
@limiter.limit("10 per minute")
def verify_code():
    data = request.get_json(force=True) or {}
    identifier = (data.get("identifier") or "").strip()
    codigo = (data.get("codigo") or "").strip()

    usuario = Usuario.query.filter(
        (Usuario.telefono == identifier) | (Usuario.correo == identifier)
    ).first()
    if not usuario or not _codigo_vigente(usuario, codigo):
        return jsonify({"message": "Código inválido o expirado."}), 400

    return jsonify({"message": "Código válido.", "valido": True}), 200


@auth_bp.post("/reset-password")
@limiter.limit("10 per minute")
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

    token = _codigo_vigente(usuario, codigo)
    if not token:
        return jsonify({"message": "Código inválido o expirado."}), 400

    usuario.password_hash = generate_password_hash(nueva_password)
    usuario.token_version += 1  # DEV-F4-03: invalida cualquier JWT emitido antes del reset
    # Invalida también cualquier otro código sin usar que haya quedado activo.
    PasswordResetToken.query.filter_by(usuario_id=usuario.id, usado=False).update({"usado": True})
    db.session.commit()

    return jsonify({"message": "Contraseña actualizada correctamente."}), 200


def _codigo_vigente(usuario, codigo):
    """Busca entre los códigos sin usar y no expirados del usuario uno cuyo
    hash coincida con `codigo`. Ya no se puede filtrar por igualdad directa
    en la consulta porque el valor almacenado es un hash (DEV-F4-04)."""
    if not codigo:
        return None
    candidatos = (
        PasswordResetToken.query.filter_by(usuario_id=usuario.id, usado=False)
        .filter(PasswordResetToken.expira_en >= datetime.utcnow())
        .order_by(PasswordResetToken.creado_en.desc())
        .all()
    )
    for token in candidatos:
        if check_password_hash(token.codigo, codigo):
            return token
    return None


def _emitir_token(usuario: Usuario):
    return create_access_token(
        identity=str(usuario.id),
        additional_claims={"rol": usuario.rol, "ver": usuario.token_version},
    )


def _serialize(usuario: Usuario):
    return {
        "id": usuario.id,
        "nombre_completo": usuario.nombre_completo,
        "telefono": usuario.telefono,
        "correo": usuario.correo,
        "rol": usuario.rol,
        "estado": usuario.estado,
    }
