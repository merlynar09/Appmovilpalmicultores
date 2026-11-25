"""DEV-F3-07: cobertura mínima de alertas de cosecha (RN03) — antes solo se
ejercitaban indirectamente a través del motor USSD."""
from datetime import date, timedelta


def _lote_con_ciclo_proximo(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = client.post("/api/fincas", json={"nombre": "Finca Alertas"}, headers=headers).get_json()["id"]
    lote_id = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "ALERTA-1"}, headers=headers
    ).get_json()["id"]
    fecha_ultima = date.today().isoformat()
    client.post(
        f"/api/lotes/{lote_id}/ciclos",
        json={"duracion_dias": 3, "dias_anticipacion_alerta": 3, "fecha_ultima_cosecha": fecha_ultima},
        headers=headers,
    )
    return lote_id, headers


def test_listar_alertas_genera_alerta_de_cosecha_proxima(client, auth_header):
    _lote_id, headers = _lote_con_ciclo_proximo(client, auth_header)
    resp = client.get("/api/alertas", headers=headers)
    assert resp.status_code == 200
    alertas = resp.get_json()
    assert any(a["tipo"] == "cosecha" for a in alertas)


def test_listar_alertas_no_duplica_en_llamadas_repetidas(client, auth_header):
    _lote_id, headers = _lote_con_ciclo_proximo(client, auth_header)
    client.get("/api/alertas", headers=headers)
    segunda = client.get("/api/alertas", headers=headers).get_json()
    alertas_cosecha = [a for a in segunda if a["tipo"] == "cosecha"]
    assert len(alertas_cosecha) == 1


def test_marcar_alerta_leida(client, auth_header):
    _lote_id, headers = _lote_con_ciclo_proximo(client, auth_header)
    alerta = client.get("/api/alertas", headers=headers).get_json()[0]
    resp = client.patch(f"/api/alertas/{alerta['id']}/leida", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["leida"] is True


def test_marcar_todas_leidas(client, auth_header):
    _lote_id, headers = _lote_con_ciclo_proximo(client, auth_header)
    client.get("/api/alertas", headers=headers)
    resp = client.post("/api/alertas/leer-todas", headers=headers)
    assert resp.status_code == 200

    no_leidas = client.get("/api/alertas?no_leidas=true", headers=headers).get_json()
    assert no_leidas == []


def test_alertas_aisladas_por_usuario(client, auth_header, app_ctx):
    _lote_id, headers = _lote_con_ciclo_proximo(client, auth_header)
    propias = client.get("/api/alertas", headers=headers).get_json()
    assert len(propias) >= 1

    from werkzeug.security import generate_password_hash
    from app.extensions import db
    from app.models import Usuario

    otro = Usuario(
        nombre_completo="Otro Palmicultor Alertas",
        telefono="3219990041",
        password_hash=generate_password_hash("clave123"),
        rol="palmicultor",
        estado="activo",
    )
    db.session.add(otro)
    db.session.commit()
    token = client.post(
        "/api/auth/login", json={"identifier": "3219990041", "password": "clave123"}
    ).get_json()["token"]

    ajenas = client.get("/api/alertas", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert ajenas == []
