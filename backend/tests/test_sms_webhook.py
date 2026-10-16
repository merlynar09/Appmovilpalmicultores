"""Pruebas del webhook real de Twilio y de la regresión del simulador mock.

No se envía ningún SMS real: el envío de Twilio está deshabilitado por
defecto (TWILIO_ENABLED no se activa aquí) y estas pruebas solo ejercitan la
RECEPCIÓN (webhook entrante), que no depende de TWILIO_ENABLED. La firma se
calcula con la misma librería de Twilio contra un Auth Token de prueba fijo
— no se usa ningún secreto real.

Usa al palmicultor del seed (3001234567, lote "Lote-A1") y limpia los datos
que crea cada prueba.
"""

import uuid

from twilio.request_validator import RequestValidator

from app.extensions import db
from app.models import RegistroProduccion, SmsUssdLog, Usuario, SolicitudTransporte

AUTH_TOKEN_PRUEBA = "auth-token-de-pruebas-no-real"
WEBHOOK_URL = "http://localhost/api/sms/webhook/twilio"
TELEFONO_SEED = "3001234567"  # palmicultor del seed, con lote Lote-A1


def _firmar(params):
    return RequestValidator(AUTH_TOKEN_PRUEBA).compute_signature(WEBHOOK_URL, params)


def _post_webhook(client, params, firma=None):
    headers = {}
    if firma is not None:
        headers["X-Twilio-Signature"] = firma
    return client.post("/api/sms/webhook/twilio", data=params, headers=headers)


def test_firma_invalida_se_rechaza(client, app, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN_PRUEBA)
    monkeypatch.setenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost")

    params = {"From": f"+57{TELEFONO_SEED}", "Body": "AYUDA", "MessageSid": f"SM{uuid.uuid4().hex[:16]}"}
    resp = _post_webhook(client, params, firma="firma-incorrecta")

    assert resp.status_code == 403
    with app.app_context():
        assert SmsUssdLog.query.filter_by(twilio_sid=params["MessageSid"]).first() is None


def test_sin_firma_se_rechaza(client, app, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN_PRUEBA)
    monkeypatch.setenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost")

    params = {"From": f"+57{TELEFONO_SEED}", "Body": "AYUDA", "MessageSid": f"SM{uuid.uuid4().hex[:16]}"}
    resp = _post_webhook(client, params, firma=None)
    assert resp.status_code == 403


def test_firma_valida_comando_ayuda(client, app, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN_PRUEBA)
    monkeypatch.setenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost")

    message_sid = f"SM{uuid.uuid4().hex[:16]}"
    params = {"From": f"+57{TELEFONO_SEED}", "Body": "AYUDA", "MessageSid": message_sid}
    resp = _post_webhook(client, params, firma=_firmar(params))

    assert resp.status_code == 200
    assert resp.content_type.startswith("text/xml")
    assert b"Comandos disponibles" in resp.data

    with app.app_context():
        log = SmsUssdLog.query.filter_by(twilio_sid=message_sid).first()
        assert log is not None
        assert log.proveedor == "twilio"
        assert log.direccion == "entrante"
        assert log.canal == "sms"
        db.session.delete(log)
        db.session.commit()


def test_numero_no_registrado(client, app, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN_PRUEBA)
    monkeypatch.setenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost")

    message_sid = f"SM{uuid.uuid4().hex[:16]}"
    params = {"From": "+573009999999", "Body": "AYUDA", "MessageSid": message_sid}
    resp = _post_webhook(client, params, firma=_firmar(params))

    assert resp.status_code == 200
    assert b"no registrado" in resp.data

    with app.app_context():
        log = SmsUssdLog.query.filter_by(twilio_sid=message_sid).first()
        assert log is not None
        assert log.usuario_id is None
        db.session.delete(log)
        db.session.commit()


def test_dedup_mismo_message_sid_no_duplica(client, app, monkeypatch):
    """Simula un reintento de Twilio del mismo mensaje: no debe crear un
    segundo registro de producción ni un segundo log."""
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN_PRUEBA)
    monkeypatch.setenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost")

    message_sid = f"SM{uuid.uuid4().hex[:16]}"
    params = {
        "From": f"+57{TELEFONO_SEED}",
        "Body": "REGISTRO Lote-A1 40 2 80 16",
        "MessageSid": message_sid,
    }
    firma = _firmar(params)

    resp1 = _post_webhook(client, params, firma=firma)
    resp2 = _post_webhook(client, params, firma=firma)  # mismo SID: reintento de Twilio

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.data == resp2.data

    with app.app_context():
        logs = SmsUssdLog.query.filter_by(twilio_sid=message_sid).all()
        assert len(logs) == 1

        registros = RegistroProduccion.query.filter_by(peso_promedio_racimo=16.0, fuente="sms").all()
        # Solo debió crearse UN censo (el del primer POST), no dos.
        creados_por_esta_prueba = registros
        assert len(creados_por_esta_prueba) == 1

        for r in creados_por_esta_prueba:
            db.session.delete(r)
        for l in logs:
            db.session.delete(l)
        db.session.commit()


def test_webhook_transporte_crea_solicitud(client, app, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", AUTH_TOKEN_PRUEBA)
    monkeypatch.setenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost")

    message_sid = f"SM{uuid.uuid4().hex[:16]}"
    params = {
        "From": f"+57{TELEFONO_SEED}",
        "Body": "TRANSPORTE Lote-A1 7",
        "MessageSid": message_sid,
    }
    resp = _post_webhook(client, params, firma=_firmar(params))

    assert resp.status_code == 200
    assert b"Solicitud de transporte" in resp.data

    with app.app_context():
        log = SmsUssdLog.query.filter_by(twilio_sid=message_sid).first()
        assert log is not None
        usuario = Usuario.query.filter_by(telefono=TELEFONO_SEED).first()
        solicitud = (
            SolicitudTransporte.query.filter_by(palmicultor_id=usuario.id, cantidad_estimada=7)
            .filter(SolicitudTransporte.observaciones == "Solicitud creada vía SMS/USSD")
            .order_by(SolicitudTransporte.id.desc())
            .first()
        )
        assert solicitud is not None
        db.session.delete(solicitud)
        db.session.delete(log)
        db.session.commit()


def test_mock_endpoint_sigue_funcionando(client):
    """Regresión: el simulador interno (JSON, sin firma) no debió verse
    afectado por agregar el webhook real de Twilio."""
    resp = client.post("/api/sms/entrante", json={"telefono": TELEFONO_SEED, "canal": "sms", "mensaje": "AYUDA"})
    assert resp.status_code == 200
    assert "Comandos disponibles" in resp.get_json()["respuesta"]


def test_mock_endpoint_canal_ussd_sigue_funcionando(client):
    """El USSD simulado se conserva intacto y separado de Twilio (que solo
    atiende SMS)."""
    resp = client.post("/api/sms/entrante", json={"telefono": TELEFONO_SEED, "canal": "ussd", "mensaje": "AYUDA"})
    assert resp.status_code == 200
    assert "Comandos disponibles" in resp.get_json()["respuesta"]
