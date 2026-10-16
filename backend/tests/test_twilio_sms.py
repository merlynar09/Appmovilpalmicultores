"""Pruebas del servicio de Twilio (app/services/twilio_sms.py).

Nunca hacen una llamada de red real: el cliente de Twilio se mockea con
unittest.mock. Cubren: inicialización segura sin credenciales, envío
exitoso/erróneo mockeado, y validación de firma de webhook (con una firma
real calculada con la misma librería, para probar el algoritmo de verdad).
"""

from unittest.mock import MagicMock, patch

from app.services import twilio_sms


def _reset_cliente():
    twilio_sms._client = None
    twilio_sms._client_intentado = False


def test_deshabilitado_por_defecto(monkeypatch):
    monkeypatch.delenv("TWILIO_ENABLED", raising=False)
    assert twilio_sms.twilio_habilitado() is False

    resultado = twilio_sms.enviar_sms("+573001234567", "hola")
    assert resultado == {"ok": False, "sid": None, "error": "Twilio deshabilitado (TWILIO_ENABLED=false).", "estado": "deshabilitado"}


def test_habilitado_pero_sin_credenciales(monkeypatch):
    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    _reset_cliente()

    resultado = twilio_sms.enviar_sms("+573001234567", "hola")
    assert resultado["ok"] is False
    assert resultado["estado"] == "sin_credenciales"


def test_habilitado_sin_remitente(monkeypatch):
    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACfake0000000000000000000000000")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso")
    monkeypatch.delenv("TWILIO_PHONE_NUMBER", raising=False)
    _reset_cliente()

    with patch("twilio.rest.Client"):
        resultado = twilio_sms.enviar_sms("+573001234567", "hola")

    assert resultado["ok"] is False
    assert resultado["estado"] == "sin_remitente"
    _reset_cliente()


def test_envio_exitoso_mockeado(monkeypatch):
    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACfake0000000000000000000000000")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550001111")
    _reset_cliente()

    fake_message = MagicMock(sid="SMfake123", status="queued")
    with patch("twilio.rest.Client") as MockClient:
        MockClient.return_value.messages.create.return_value = fake_message
        resultado = twilio_sms.enviar_sms("+573001234567", "Prueba de SMS de Palma Viva.")

    assert resultado == {"ok": True, "sid": "SMfake123", "error": None, "estado": "queued"}
    MockClient.return_value.messages.create.assert_called_once_with(
        to="+573001234567", from_="+15550001111", body="Prueba de SMS de Palma Viva."
    )
    _reset_cliente()


def test_envio_error_del_proveedor_no_lanza(monkeypatch):
    """Ej.: número no verificado en cuenta trial (error 21608 de Twilio) —
    debe devolverse como resultado controlado, nunca como excepción."""
    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACfake0000000000000000000000000")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550001111")
    _reset_cliente()

    with patch("twilio.rest.Client") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception(
            "21608: The number +573009999999 is unverified"
        )
        resultado = twilio_sms.enviar_sms("+573009999999", "hola")

    assert resultado["ok"] is False
    assert resultado["estado"] == "error"
    assert "21608" in resultado["error"]
    _reset_cliente()


def test_normalizacion_telefono_colombia():
    assert twilio_sms.a_e164_co("3001234567") == "+573001234567"
    assert twilio_sms.a_e164_co("+573001234567") == "+573001234567"
    assert twilio_sms.a_e164_co("573001234567") == "+573001234567"

    assert twilio_sms.desde_e164_co("+573001234567") == "3001234567"
    assert twilio_sms.desde_e164_co("573001234567") == "3001234567"


def test_validar_firma_correcta(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso123")
    from twilio.request_validator import RequestValidator

    url = "http://localhost/api/sms/webhook/twilio"
    params = {"From": "+573001234567", "Body": "AYUDA", "MessageSid": "SM123"}
    firma = RequestValidator("tokenfalso123").compute_signature(url, params)

    assert twilio_sms.validar_firma(url, params, firma) is True


def test_validar_firma_incorrecta(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso123")
    assert twilio_sms.validar_firma("http://localhost/x", {"a": "1"}, "firma-que-no-es") is False


def test_validar_firma_sin_auth_token(monkeypatch):
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    assert twilio_sms.validar_firma("http://localhost/x", {}, "cualquier-firma") is False
