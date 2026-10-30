import os
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request


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


def role_required(*roles):
    """Exige JWT válido y que el rol del usuario esté en `roles`."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("rol") not in roles:
                return jsonify({"message": "No tienes permiso para realizar esta acción."}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_user_id():
    return int(get_jwt_identity())


def paginate_args(request, default_limit=50, max_limit=200):
    try:
        limit = min(int(request.args.get("limit", default_limit)), max_limit)
    except (TypeError, ValueError):
        limit = default_limit
    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0
    return limit, offset
