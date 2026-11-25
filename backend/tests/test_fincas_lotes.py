"""Pruebas dirigidas a los hallazgos de la Fase 5 sobre fincas y lotes:
F5-03 (recursos inactivos), F5-04 (dominios positivos) y F5-05 (código de
lote único por finca)."""


def _crear_finca(client, headers, **overrides):
    payload = {"nombre": "Finca de prueba", "area_hectareas": 10}
    payload.update(overrides)
    resp = client.post("/api/fincas", json=payload, headers=headers)
    return resp


def test_area_negativa_rechazada(client, auth_header):
    headers = auth_header(client, "palmicultor")
    resp = _crear_finca(client, headers, area_hectareas=-5)
    assert resp.status_code == 400


def test_area_cero_rechazada(client, auth_header):
    headers = auth_header(client, "palmicultor")
    resp = _crear_finca(client, headers, area_hectareas=0)
    assert resp.status_code == 400


def test_codigo_de_lote_duplicado_en_la_misma_finca_rechazado(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = _crear_finca(client, headers).get_json()["id"]

    primero = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "DUP-1"}, headers=headers
    )
    assert primero.status_code == 201

    segundo = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "DUP-1"}, headers=headers
    )
    assert segundo.status_code == 409


def test_codigo_de_lote_repetido_en_otra_finca_si_se_permite(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_1 = _crear_finca(client, headers, nombre="Finca 1").get_json()["id"]
    finca_2 = _crear_finca(client, headers, nombre="Finca 2").get_json()["id"]

    r1 = client.post(f"/api/fincas/{finca_1}/lotes", json={"codigo": "A1"}, headers=headers)
    r2 = client.post(f"/api/fincas/{finca_2}/lotes", json={"codigo": "A1"}, headers=headers)
    assert r1.status_code == 201
    assert r2.status_code == 201


def test_lote_con_area_negativa_rechazado(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = _crear_finca(client, headers).get_json()["id"]
    resp = client.post(
        f"/api/fincas/{finca_id}/lotes",
        json={"codigo": "L1", "area_hectareas": -2},
        headers=headers,
    )
    assert resp.status_code == 400


def test_no_se_pueden_crear_lotes_en_finca_inactiva(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = _crear_finca(client, headers).get_json()["id"]
    client.delete(f"/api/fincas/{finca_id}", headers=headers)  # desactiva

    resp = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "L1"}, headers=headers
    )
    assert resp.status_code == 409


def test_no_se_pueden_crear_ciclos_en_lote_inactivo(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = _crear_finca(client, headers).get_json()["id"]
    lote_id = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "L1"}, headers=headers
    ).get_json()["id"]
    client.delete(f"/api/lotes/{lote_id}", headers=headers)  # desactiva

    resp = client.post(
        f"/api/lotes/{lote_id}/ciclos",
        json={"duracion_dias": 10, "dias_anticipacion_alerta": 3},
        headers=headers,
    )
    assert resp.status_code == 409


def test_finca_inactiva_sigue_siendo_consultable(client, auth_header):
    """F5-03: solo se bloquean operaciones nuevas, no la lectura."""
    headers = auth_header(client, "palmicultor")
    finca_id = _crear_finca(client, headers).get_json()["id"]
    client.delete(f"/api/fincas/{finca_id}", headers=headers)

    resp = client.get(f"/api/fincas/{finca_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "inactiva"
