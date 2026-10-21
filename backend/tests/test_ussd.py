"""Pruebas del menú USSD (motor + adaptadores). Usa el palmicultor del seed
(3001234567, lote "Lote-A1"), el comprador del seed (3002345678) para el
caso "rol no permitido", y limpia todo lo que crea.

No depende de ningún proveedor real ni hace llamadas de red: el motor
(`app.services.ussd_engine`) es puro Python + base de datos.
"""

import uuid

from app.extensions import db
from app.models import (
    RegistroProduccion,
    SolicitudTransporte,
    Usuario,
    UssdSesion,
)
from app.services import ussd_engine

TEL_PALMICULTOR = "3001234567"
TEL_COMPRADOR = "3002345678"
TEL_NO_REGISTRADO = "3009999999"


def _sid():
    return f"test-{uuid.uuid4().hex[:10]}"


def _paso(telefono, sid, entrada, **kwargs):
    return ussd_engine.procesar_entrada(telefono=telefono, entrada=entrada, session_id=sid, proveedor="test", **kwargs)


def _limpiar_sesion(sid):
    s = UssdSesion.query.filter_by(session_id=sid).first()
    if s:
        db.session.delete(s)
        db.session.commit()


# 1-2: inicio de sesión / menú principal ----------------------------------

def test_inicia_sesion_y_muestra_menu_principal(app_ctx):
    sid = _sid()
    r = _paso(TEL_PALMICULTOR, sid, "")
    assert r["continuar"] is True
    assert "Palma Viva" in r["respuesta"]
    assert "1 Precio de palma" in r["respuesta"]

    sesion = UssdSesion.query.filter_by(session_id=sid).first()
    assert sesion is not None
    assert sesion.estado == "MENU_PRINCIPAL"
    assert sesion.usuario_id == Usuario.query.filter_by(telefono=TEL_PALMICULTOR).first().id
    _limpiar_sesion(sid)


# 3: navegación entre opciones ---------------------------------------------

def test_navega_a_submenu_precios(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r = _paso(TEL_PALMICULTOR, sid, "1")
    assert r["continuar"] is True
    assert "Precio" in r["respuesta"] or "precio" in r["respuesta"]
    _limpiar_sesion(sid)


def test_navega_a_submenu_compradores(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r = _paso(TEL_PALMICULTOR, sid, "2")
    assert r["continuar"] is True
    assert "Comprador" in r["respuesta"]
    _limpiar_sesion(sid)


# 4: regreso al menú anterior ----------------------------------------------

def test_vuelve_al_menu_principal_con_cero(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "2")
    r = _paso(TEL_PALMICULTOR, sid, "0")
    assert "1 Precio de palma" in r["respuesta"]
    sesion = UssdSesion.query.filter_by(session_id=sid).first()
    assert sesion.estado == "MENU_PRINCIPAL"
    _limpiar_sesion(sid)


# 5: salida correcta ---------------------------------------------------------

def test_salir_termina_sesion(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r = _paso(TEL_PALMICULTOR, sid, "0")
    assert r["continuar"] is False
    sesion = UssdSesion.query.filter_by(session_id=sid).first()
    assert sesion.activa is False
    assert sesion.resultado_final == "completada"

    # una entrada posterior a una sesión ya cerrada no revive el menú
    r2 = _paso(TEL_PALMICULTOR, sid, "1")
    assert r2["continuar"] is False
    _limpiar_sesion(sid)


# 6: opción inválida ----------------------------------------------------------

def test_opcion_invalida_no_rompe_la_sesion(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r = _paso(TEL_PALMICULTOR, sid, "xyz")
    assert r["continuar"] is True
    assert "invalida" in r["respuesta"].lower()
    # la sesión sigue en el menú principal, no se corrompió
    r2 = _paso(TEL_PALMICULTOR, sid, "8")
    assert "Palma Viva USSD" in r2["respuesta"]
    _limpiar_sesion(sid)


# 7: sesión expirada -----------------------------------------------------------

def test_sesion_expirada(app_ctx):
    from datetime import datetime, timedelta

    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    sesion = UssdSesion.query.filter_by(session_id=sid).first()
    sesion.expira_en = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()

    r = _paso(TEL_PALMICULTOR, sid, "1")
    assert r["continuar"] is False
    assert "expir" in r["respuesta"].lower()

    sesion = UssdSesion.query.filter_by(session_id=sid).first()
    assert sesion.resultado_final == "expirada"
    _limpiar_sesion(sid)


# 8-10: identificación / autorización ------------------------------------------

def test_usuario_no_registrado(app_ctx):
    sid = _sid()
    r = _paso(TEL_NO_REGISTRADO, sid, "")
    assert r["continuar"] is False
    assert "no registrado" in r["respuesta"].lower()
    _limpiar_sesion(sid)


def test_usuario_suspendido(app_ctx):
    usuario = Usuario.query.filter_by(telefono=TEL_PALMICULTOR).first()
    estado_original = usuario.estado
    usuario.estado = "suspendido"
    db.session.commit()

    sid = _sid()
    try:
        r = _paso(TEL_PALMICULTOR, sid, "")
        assert r["continuar"] is False
        assert "no esta activa" in r["respuesta"].lower() or "no está activa" in r["respuesta"].lower()
    finally:
        usuario.estado = estado_original
        db.session.commit()
        _limpiar_sesion(sid)


def test_usuario_con_rol_no_permitido(app_ctx):
    sid = _sid()
    r = _paso(TEL_COMPRADOR, sid, "")
    assert r["continuar"] is False
    assert "palmicultor" in r["respuesta"].lower()
    _limpiar_sesion(sid)


# 11-13: consultas de solo lectura ----------------------------------------------

def test_consulta_precios(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r = _paso(TEL_PALMICULTOR, sid, "1")
    assert "0 Volver" in r["respuesta"]
    _limpiar_sesion(sid)


def test_consulta_compradores(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r = _paso(TEL_PALMICULTOR, sid, "2")
    assert "Extractora" in r["respuesta"] or "Compradores" in r["respuesta"]
    _limpiar_sesion(sid)


def test_consulta_logistica_y_vias(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r_transporte = _paso(TEL_PALMICULTOR, sid, "3")
    assert r_transporte["continuar"] is True
    _paso(TEL_PALMICULTOR, sid, "0")
    r_vias = _paso(TEL_PALMICULTOR, sid, "4")
    assert r_vias["continuar"] is True
    assert "via" in r_vias["respuesta"].lower()
    _limpiar_sesion(sid)


def test_consulta_avisos_no_duplica_notificaciones(app_ctx):
    from app.models import Notificacion

    usuario = Usuario.query.filter_by(telefono=TEL_PALMICULTOR).first()
    antes = Notificacion.query.filter_by(usuario_id=usuario.id).count()

    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "5")
    despues_1 = Notificacion.query.filter_by(usuario_id=usuario.id).count()

    sid2 = _sid()
    _paso(TEL_PALMICULTOR, sid2, "")
    _paso(TEL_PALMICULTOR, sid2, "5")
    despues_2 = Notificacion.query.filter_by(usuario_id=usuario.id).count()

    # Pudo crear alertas nuevas la PRIMERA vez (si había ciclos pendientes),
    # pero consultarlo de nuevo no debe seguir sumando.
    assert despues_2 == despues_1
    _limpiar_sesion(sid)
    _limpiar_sesion(sid2)


# 14: registro de producción (flujo completo + confirmación) -------------------

def test_registro_produccion_flujo_completo(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "6")
    _paso(TEL_PALMICULTOR, sid, "Lote-A1")
    _paso(TEL_PALMICULTOR, sid, "40")
    _paso(TEL_PALMICULTOR, sid, "2")
    _paso(TEL_PALMICULTOR, sid, "80")
    r = _paso(TEL_PALMICULTOR, sid, "16.5")
    assert "Confirmar" in r["respuesta"]

    r_final = _paso(TEL_PALMICULTOR, sid, "1")
    assert r_final["continuar"] is False
    assert "Censo guardado" in r_final["respuesta"]

    registro = (
        RegistroProduccion.query.filter_by(fuente="ussd", peso_promedio_racimo=16.5)
        .order_by(RegistroProduccion.id.desc())
        .first()
    )
    assert registro is not None
    assert registro.palmas_evaluadas == 40
    db.session.delete(registro)
    db.session.commit()
    _limpiar_sesion(sid)


# 15: solicitud de transporte (flujo completo + confirmación) ------------------

def test_solicitud_transporte_flujo_completo(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "7")
    _paso(TEL_PALMICULTOR, sid, "Lote-A1")
    _paso(TEL_PALMICULTOR, sid, "6")
    r = _paso(TEL_PALMICULTOR, sid, "9")  # omitir fecha
    assert "Confirmar" in r["respuesta"]

    r_final = _paso(TEL_PALMICULTOR, sid, "1")
    assert r_final["continuar"] is False
    assert "Solicitud de transporte" in r_final["respuesta"]

    usuario = Usuario.query.filter_by(telefono=TEL_PALMICULTOR).first()
    solicitud = (
        SolicitudTransporte.query.filter_by(palmicultor_id=usuario.id, cantidad_estimada=6)
        .filter(SolicitudTransporte.observaciones == "Solicitud creada vía SMS/USSD")
        .order_by(SolicitudTransporte.id.desc())
        .first()
    )
    assert solicitud is not None
    db.session.delete(solicitud)
    db.session.commit()
    _limpiar_sesion(sid)


# 16: cancelación antes de confirmar --------------------------------------------

def test_cancelar_antes_de_confirmar_produccion(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "6")
    _paso(TEL_PALMICULTOR, sid, "Lote-A1")
    _paso(TEL_PALMICULTOR, sid, "40")
    _paso(TEL_PALMICULTOR, sid, "2")
    _paso(TEL_PALMICULTOR, sid, "80")
    _paso(TEL_PALMICULTOR, sid, "16.5")
    r = _paso(TEL_PALMICULTOR, sid, "2")  # cancelar

    assert r["continuar"] is True
    assert "cancelado" in r["respuesta"].lower()
    assert RegistroProduccion.query.filter_by(fuente="ussd", peso_promedio_racimo=16.5).first() is None
    _limpiar_sesion(sid)


def test_cancelar_a_mitad_de_flujo_con_cero(app_ctx):
    """0 en cualquier paso de captura de datos cancela y vuelve al menú,
    sin dejar la sesión en un estado intermedio."""
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "7")
    r = _paso(TEL_PALMICULTOR, sid, "0")
    assert "1 Precio de palma" in r["respuesta"]
    sesion = UssdSesion.query.filter_by(session_id=sid).first()
    assert sesion.estado == "MENU_PRINCIPAL"
    _limpiar_sesion(sid)


# 18: solicitudes duplicadas (reintento del proveedor) --------------------------

def test_reintento_con_mismo_request_id_no_duplica(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "", request_id="req-0")
    _paso(TEL_PALMICULTOR, sid, "6", request_id="req-1")
    _paso(TEL_PALMICULTOR, sid, "Lote-A1", request_id="req-2")
    _paso(TEL_PALMICULTOR, sid, "40", request_id="req-3")
    _paso(TEL_PALMICULTOR, sid, "2", request_id="req-4")
    _paso(TEL_PALMICULTOR, sid, "80", request_id="req-5")
    _paso(TEL_PALMICULTOR, sid, "16.5", request_id="req-6")

    # El proveedor reintenta la confirmación con el MISMO request_id dos veces.
    r1 = _paso(TEL_PALMICULTOR, sid, "1", request_id="req-confirmar")
    r2 = _paso(TEL_PALMICULTOR, sid, "1", request_id="req-confirmar")

    assert r1["respuesta"] == r2["respuesta"]

    registros = RegistroProduccion.query.filter_by(fuente="ussd", peso_promedio_racimo=16.5).all()
    assert len(registros) == 1  # no se duplicó
    for r in registros:
        db.session.delete(r)
    db.session.commit()
    _limpiar_sesion(sid)


def test_reintento_sin_request_id_en_confirmacion_no_duplica(app_ctx):
    """Algunos proveedores no mandan un id de solicitud estable: el
    resguardo sin ese id solo actúa sobre pasos de CONFIRMACIÓN (los
    únicos con efectos reales en la base de datos) — repetir la misma
    entrada ahí se trata como reintento, no se vuelve a crear el registro."""
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "7")
    _paso(TEL_PALMICULTOR, sid, "Lote-A1")
    _paso(TEL_PALMICULTOR, sid, "3")
    _paso(TEL_PALMICULTOR, sid, "9")

    r1 = _paso(TEL_PALMICULTOR, sid, "1")  # confirma
    r2 = _paso(TEL_PALMICULTOR, sid, "1")  # reintento sin request_id

    assert r1["respuesta"] == r2["respuesta"]

    usuario = Usuario.query.filter_by(telefono=TEL_PALMICULTOR).first()
    solicitudes = SolicitudTransporte.query.filter_by(palmicultor_id=usuario.id, cantidad_estimada=3).all()
    assert len(solicitudes) == 1
    for s in solicitudes:
        db.session.delete(s)
    db.session.commit()
    _limpiar_sesion(sid)


def test_navegacion_repetida_sin_request_id_se_reprocesa(app_ctx):
    """Fuera de una confirmación, repetir la misma entrada (ej. volver a
    pulsar la misma opción de un menú de solo lectura) NO debe tratarse
    como duplicado — debe reprocesarse normalmente."""
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    r1 = _paso(TEL_PALMICULTOR, sid, "1")  # MENU_PRINCIPAL -> MENU_PRECIOS
    r2 = _paso(TEL_PALMICULTOR, sid, "1")  # se queda en MENU_PRECIOS, se reprocesa
    assert r1["continuar"] is True
    assert r2["continuar"] is True
    _limpiar_sesion(sid)


# 19: autenticación del webhook real ---------------------------------------------

def test_webhook_real_sin_secreto_configurado_rechaza(client, monkeypatch):
    monkeypatch.delenv("USSD_PROVIDER_SHARED_SECRET", raising=False)
    resp = client.post(
        "/api/ussd/webhook",
        json={"sessionId": "abc", "phoneNumber": "+573001234567", "text": ""},
    )
    assert resp.status_code == 403


def test_webhook_real_con_secreto_incorrecto_rechaza(client, monkeypatch):
    monkeypatch.setenv("USSD_PROVIDER_SHARED_SECRET", "secreto-correcto")
    resp = client.post(
        "/api/ussd/webhook",
        json={"sessionId": "abc", "phoneNumber": "+573001234567", "text": ""},
        headers={"X-Ussd-Secret": "secreto-incorrecto"},
    )
    assert resp.status_code == 403


def test_webhook_real_con_secreto_correcto_funciona(client, app, monkeypatch):
    monkeypatch.setenv("USSD_PROVIDER_SHARED_SECRET", "secreto-correcto")
    sid = _sid()
    resp = client.post(
        "/api/ussd/webhook",
        json={"sessionId": sid, "phoneNumber": f"+57{TEL_PALMICULTOR}", "text": ""},
        headers={"X-Ussd-Secret": "secreto-correcto"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Palma Viva" in data["text"]
    assert data["continueSession"] is True
    with app.app_context():
        _limpiar_sesion(sid)


# 20: datos inválidos / "errores" controlados ------------------------------------

def test_lote_inexistente_reprompt_sin_romper(app_ctx):
    sid = _sid()
    _paso(TEL_PALMICULTOR, sid, "")
    _paso(TEL_PALMICULTOR, sid, "6")
    r = _paso(TEL_PALMICULTOR, sid, "Lote-Que-No-Existe")
    assert r["continuar"] is True
    assert "no se encontro" in r["respuesta"].lower()
    # la sesión sigue viva y puede intentar de nuevo
    r2 = _paso(TEL_PALMICULTOR, sid, "0")
    assert "1 Precio de palma" in r2["respuesta"]
    _limpiar_sesion(sid)


# 21-22: compatibilidad con el simulador SMS/USSD existente ----------------------

def test_endpoint_sms_entrante_sigue_funcionando(client):
    resp = client.post("/api/sms/entrante", json={"telefono": TEL_PALMICULTOR, "canal": "sms", "mensaje": "AYUDA"})
    assert resp.status_code == 200
    assert "Comandos disponibles" in resp.get_json()["respuesta"]


def test_comandos_sms_de_una_linea_siguen_funcionando(client):
    resp = client.post(
        "/api/sms/entrante",
        json={"telefono": TEL_PALMICULTOR, "canal": "sms", "mensaje": "REGISTRO Lote-A1 40 2 80 16"},
    )
    assert resp.status_code == 200
    assert "Censo registrado" in resp.get_json()["respuesta"]


# 23: la simulación USSD de un solo comando (canal=ussd) se conserva ------------

def test_simulacion_ussd_antigua_de_un_comando_se_conserva(client, app):
    resp = client.post("/api/sms/entrante", json={"telefono": TEL_PALMICULTOR, "canal": "ussd", "mensaje": "AYUDA"})
    assert resp.status_code == 200
    assert "Comandos disponibles" in resp.get_json()["respuesta"]


# nuevo simulador de sesión (para la pantalla de pruebas del frontend) ----------

def test_simulador_ussd_nuevo_via_endpoint(client, app):
    sid = _sid()
    resp = client.post("/api/ussd/simular", json={"telefono": TEL_PALMICULTOR, "session_id": sid, "texto": ""})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "Palma Viva" in data["respuesta"]
    assert data["continuar"] is True
    with app.app_context():
        _limpiar_sesion(sid)
