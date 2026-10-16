"""notificar_por_sms() es el punto de integración entre las alertas ya
existentes (cosecha, logística) y Twilio. Debe:
- no hacer nada si Twilio está deshabilitado (comportamiento por defecto),
- no lanzar ninguna excepción aunque el envío falle (p. ej. número no
  verificado en cuenta trial), para no tumbar el endpoint que la llama,
- registrar el intento en SmsUssdLog como saliente/twilio.
"""

from unittest.mock import patch

from app.extensions import db
from app.models import SmsUssdLog, Usuario
from app.routes.sms import notificar_por_sms
from app.services import twilio_sms

TELEFONO_SEED = "3001234567"


def _reset_cliente():
    twilio_sms._client = None
    twilio_sms._client_intentado = False


def test_no_hace_nada_si_twilio_deshabilitado(app_ctx, monkeypatch):
    monkeypatch.delenv("TWILIO_ENABLED", raising=False)
    usuario = Usuario.query.filter_by(telefono=TELEFONO_SEED).first()

    antes = SmsUssdLog.query.filter_by(usuario_id=usuario.id, comando="ALERTA").count()
    notificar_por_sms(usuario, "Prueba", "mensaje de prueba sin Twilio habilitado")
    despues = SmsUssdLog.query.filter_by(usuario_id=usuario.id, comando="ALERTA").count()

    assert despues == antes  # no se intentó nada, ni se registró nada


def test_no_rompe_el_flujo_si_twilio_falla(app_ctx, monkeypatch):
    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACfake0000000000000000000000000")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550001111")
    _reset_cliente()

    usuario = Usuario.query.filter_by(telefono=TELEFONO_SEED).first()

    with patch("twilio.rest.Client") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception(
            "21608: The number is unverified (cuenta trial)"
        )
        # No debe lanzar, aunque Twilio rechace el envío.
        notificar_por_sms(usuario, "Próxima cosecha", "El lote X está listo en 2 días.")

    log = (
        SmsUssdLog.query.filter_by(usuario_id=usuario.id, comando="ALERTA", proveedor="twilio")
        .order_by(SmsUssdLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.estado == "error"
    assert log.direccion == "saliente"

    db.session.delete(log)
    db.session.commit()
    _reset_cliente()


def test_registra_envio_exitoso(app_ctx, monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.setenv("TWILIO_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACfake0000000000000000000000000")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tokenfalso")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550001111")
    _reset_cliente()

    usuario = Usuario.query.filter_by(telefono=TELEFONO_SEED).first()
    fake_message = MagicMock(sid="SMalerta123", status="queued")

    with patch("twilio.rest.Client") as MockClient:
        MockClient.return_value.messages.create.return_value = fake_message
        notificar_por_sms(usuario, "Transporte aceptado", "Un transportador aceptó tu solicitud #1.")

    log = SmsUssdLog.query.filter_by(twilio_sid="SMalerta123").first()
    assert log is not None
    assert log.estado == "procesado"
    assert log.direccion == "saliente"
    assert log.proveedor == "twilio"

    db.session.delete(log)
    db.session.commit()
    _reset_cliente()
