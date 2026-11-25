import os
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.extensions import db


def simulador_sms_ussd_habilitado():
    """MOD-05: puerta por ambiente para los endpoints de simulación SMS/USSD
    (/sms/entrante, /ussd/simular). No pueden exigir JWT — simulan justamente
    a alguien SIN la app ni sesión, por un canal de texto — así que en vez de
    autenticación se protegen apagándolos por completo cuando no se necesitan
    (ej. un despliegue real), vía SMS_USSD_SIMULATOR_ENABLED. Por defecto
    quedan encendidos para no romper las pruebas/demo actuales."""
    return os.environ.get("SMS_USSD_SIMULATOR_ENABLED", "true").lower() != "false"


def simulador_deshabilitado_response():
    return jsonify({"message": "El simulador SMS/USSD está deshabilitado en este ambiente."}), 404


_SESION_INVALIDA = {"message": "Tu sesión ya no es válida. Vuelve a iniciar sesión."}


def _usuario_vigente():
    """DEV-F4-02 / DEV-F4-03: el claim "rol" del JWT por sí solo no basta —
    un usuario suspendido después de emitido su token, o uno que cambió su
    contraseña, seguía pudiendo usar ese mismo token hasta que expirara (hasta
    7 días). Esta función revalida contra la BD en cada petición protegida:
    que el usuario siga existiendo y activo, y que el claim "ver" (versión de
    token al momento de emitirlo) coincida con Usuario.token_version actual —
    que se incrementa al suspender una cuenta o al cambiar la contraseña,
    invalidando de inmediato cualquier token ya emitido antes de ese momento.
    """
    from app.models import Usuario  # import tardío: evita ciclos de import al cargar el paquete

    claims = get_jwt()
    try:
        usuario_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario or usuario.estado != "activo":
        return None
    if claims.get("ver", 0) != usuario.token_version:
        return None
    return usuario


def role_required(*roles):
    """Exige JWT válido, que el rol del usuario esté en `roles`, y que el
    usuario siga vigente (activo y con el token aún no invalidado)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("rol") not in roles:
                return jsonify({"message": "No tienes permiso para realizar esta acción."}), 403
            if _usuario_vigente() is None:
                return jsonify(_SESION_INVALIDA), 401
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def jwt_required_activo(fn):
    """Igual que @jwt_required() pero además revalida estado/token_version —
    para endpoints que no exigen un rol específico (ej. PATCH /auth/perfil)
    pero sí deben rechazar un token de una cuenta ya suspendida."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if _usuario_vigente() is None:
            return jsonify(_SESION_INVALIDA), 401
        return fn(*args, **kwargs)

    return wrapper


def current_user_id():
    return int(get_jwt_identity())


def paginate_args(request, default_limit=50, max_limit=200):
    try:
        limit = min(int(request.args.get("limit", default_limit)), max_limit)
    except (TypeError, ValueError):
        limit = default_limit
    limit = max(limit, 1)  # DEV-F4-09: un límite <= 0 no debe anular el tope
    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0
    return limit, offset
