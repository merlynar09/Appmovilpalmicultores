"""USSD — dos endpoints separados, ambos sobre el mismo motor de menús
(`app.services.ussd_engine`), pero con formatos y autenticación distintos:

1. `POST /ussd/simular` — simulador interno (JSON, sin firma), para la
   pantalla de pruebas de la app y para este propio backend. Claramente
   identificado como simulación, nunca se presenta como sesión real.

2. `POST /ussd/webhook` — adaptador genérico para un proveedor USSD real.
   Interpreta el formato de solicitud común a la mayoría de gateways USSD
   (sessionId, phoneNumber/msisdn, text/input, flag de sesión nueva,
   requestId opcional para idempotencia) y responde en ese mismo formato
   genérico. NINGÚN proveedor de USSD para Colombia fue confirmado durante
   la investigación de este proyecto (ver docs/USSD.md) — este adaptador
   está listo para conectarse en cuanto se contrate uno, ajustando solo los
   nombres de campo exactos si difieren.

Exige un secreto compartido (`USSD_PROVIDER_SHARED_SECRET`) en el webhook
real — si no está configurado, el webhook rechaza TODO (fail-closed): nunca
se activa "por accidente" sin que alguien haya configurado explícitamente
una credencial del proveedor real. El simulador no la necesita, igual que
el simulador SMS existente.

Este módulo es independiente de app/routes/sms.py (Twilio/SMS) y del
simulador SMS/USSD de un solo comando que ya existía en `/sms/entrante`:
ese sigue intacto para comandos de una sola línea; este es el menú USSD
real, con sesión y navegación.
"""

import hmac
import os

from flask import Blueprint, request, jsonify

from app.services import ussd_engine

ussd_bp = Blueprint("ussd", __name__)


@ussd_bp.post("/ussd/simular")
def ussd_simular():
    """Simulador interno — lo usa la pantalla "Simulador SMS/USSD" de la
    app. NO es una sesión USSD real de un operador móvil."""
    data = request.get_json(force=True) or {}
    telefono = (data.get("telefono") or "").strip()
    session_id = (data.get("session_id") or "").strip()
    texto = data.get("texto", "")

    if not telefono or not session_id:
        return jsonify({"message": "telefono y session_id son obligatorios."}), 400

    resultado = ussd_engine.procesar_entrada(
        telefono=telefono,
        entrada=texto,
        session_id=session_id,
        proveedor="simulador",
    )
    return jsonify(resultado), 200


@ussd_bp.post("/ussd/webhook")
def ussd_webhook():
    """Webhook genérico para un proveedor USSD real. Requiere
    USSD_PROVIDER_SHARED_SECRET configurado y una cabecera X-Ussd-Secret
    que coincida — si no, se rechaza (fail-closed, nunca se simula éxito)."""
    if not _autenticacion_valida():
        return jsonify({"message": "No autorizado."}), 403

    payload = request.get_json(silent=True) or request.form.to_dict() or {}

    session_id = str(payload.get("sessionId") or payload.get("session_id") or "").strip()
    telefono = str(payload.get("phoneNumber") or payload.get("msisdn") or payload.get("telefono") or "").strip()
    texto_crudo = str(payload.get("text") or payload.get("input") or payload.get("texto") or "").strip()
    request_id = payload.get("requestId") or payload.get("request_id")

    if not session_id or not telefono:
        return jsonify({"message": "sessionId y phoneNumber son obligatorios."}), 400

    # Algunos proveedores (estilo Africa's Talking) acumulan todo el
    # recorrido separado por "*" (ej. "1*2"); como la sesión ya vive en
    # nuestra base de datos, solo necesitamos el último dato digitado.
    entrada = texto_crudo.split("*")[-1] if texto_crudo else ""

    resultado = ussd_engine.procesar_entrada(
        telefono=_normalizar_telefono(telefono),
        entrada=entrada,
        session_id=session_id,
        proveedor=os.environ.get("USSD_PROVIDER_NOMBRE", "proveedor_real"),
        request_id=str(request_id) if request_id else None,
    )

    return jsonify(
        {
            "sessionId": session_id,
            "text": resultado["respuesta"],
            "continueSession": resultado["continuar"],
        }
    ), 200


def _autenticacion_valida() -> bool:
    secreto_esperado = os.environ.get("USSD_PROVIDER_SHARED_SECRET")
    if not secreto_esperado:
        return False
    recibido = request.headers.get("X-Ussd-Secret", "")
    return hmac.compare_digest(secreto_esperado, recibido)


def _normalizar_telefono(telefono: str) -> str:
    """Los proveedores suelen entregar el MSISDN en E.164 (+573001234567);
    Usuario.telefono se guarda sin indicativo. Reutiliza la misma
    normalización de Colombia que ya usa el canal SMS/Twilio."""
    from app.services.twilio_sms import desde_e164_co

    return desde_e164_co(telefono)
