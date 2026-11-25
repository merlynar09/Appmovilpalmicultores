"""DEV-F3-07: cobertura mínima de pronósticos de producción (CU9/RN04) —
antes no tenía ninguna prueba automatizada."""


def _lote_con_censo(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = client.post(
        "/api/fincas", json={"nombre": "Finca Pronostico"}, headers=headers
    ).get_json()["id"]
    lote_id = client.post(
        f"/api/fincas/{finca_id}/lotes",
        json={"codigo": "PRON-1", "numero_palmas": 100},
        headers=headers,
    ).get_json()["id"]
    client.post(
        "/api/produccion",
        json={
            "lote_id": lote_id,
            "palmas_evaluadas": 20,
            "palmas_improductivas": 2,
            "racimos_totales": 40,
            "peso_promedio_racimo": 15,
        },
        headers=headers,
    )
    return lote_id, headers


def test_calcular_pronostico_exitoso(client, auth_header):
    lote_id, headers = _lote_con_censo(client, auth_header)
    resp = client.post("/api/pronosticos", json={"lote_id": lote_id}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["lote_id"] == lote_id
    assert data["produccion_estimada_kg"] > 0


def test_calcular_pronostico_lote_ajeno_rechazado(client, auth_header):
    _lote_id, _headers = _lote_con_censo(client, auth_header)
    otro_lote_id, _ = _lote_con_censo(client, auth_header)  # mismo usuario, pero probamos uno inexistente
    resp = client.post(
        "/api/pronosticos", json={"lote_id": 999999}, headers=auth_header(client, "palmicultor")
    )
    assert resp.status_code == 400


def test_calcular_pronostico_sin_censo_rechazado(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = client.post("/api/fincas", json={"nombre": "Finca Sin Censo"}, headers=headers).get_json()["id"]
    lote_id = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "SIN-CENSO"}, headers=headers
    ).get_json()["id"]
    resp = client.post("/api/pronosticos", json={"lote_id": lote_id}, headers=headers)
    assert resp.status_code == 400


def test_listar_y_obtener_pronostico_propio(client, auth_header):
    lote_id, headers = _lote_con_censo(client, auth_header)
    creado = client.post("/api/pronosticos", json={"lote_id": lote_id}, headers=headers).get_json()

    listado = client.get("/api/pronosticos", headers=headers)
    assert listado.status_code == 200
    assert any(p["id"] == creado["id"] for p in listado.get_json())

    detalle = client.get(f"/api/pronosticos/{creado['id']}", headers=headers)
    assert detalle.status_code == 200
    assert "formula" in detalle.get_json()


def test_pronostico_no_visible_para_otro_palmicultor(client, auth_header, app_ctx):
    lote_id, headers = _lote_con_censo(client, auth_header)
    creado = client.post("/api/pronosticos", json={"lote_id": lote_id}, headers=headers).get_json()

    from werkzeug.security import generate_password_hash
    from app.extensions import db
    from app.models import Usuario

    otro = Usuario(
        nombre_completo="Otro Palmicultor Pronostico",
        telefono="3219990040",
        password_hash=generate_password_hash("clave123"),
        rol="palmicultor",
        estado="activo",
    )
    db.session.add(otro)
    db.session.commit()
    token = client.post(
        "/api/auth/login", json={"identifier": "3219990040", "password": "clave123"}
    ).get_json()["token"]

    resp = client.get(
        f"/api/pronosticos/{creado['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


def test_comprador_no_puede_calcular_pronostico(client, auth_header):
    resp = client.post(
        "/api/pronosticos", json={"lote_id": 1}, headers=auth_header(client, "comprador")
    )
    assert resp.status_code == 403
