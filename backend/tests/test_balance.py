"""DEV-F3-07: cobertura mínima de balance industrial (RN05) — antes sin
ninguna prueba automatizada."""


def test_calcular_balance_con_entrada_directa(client, auth_header):
    headers = auth_header(client, "palmicultor")
    resp = client.post("/api/balance/calcular", json={"entrada_kg": 1000}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["entrada_kg"] == 1000
    assert data["aceite_crudo_kg"] == 220  # 22% de 1000 (RN05)
    assert "desglose" in data


def test_calcular_balance_entrada_negativa_rechazada(client, auth_header):
    resp = client.post(
        "/api/balance/calcular", json={"entrada_kg": -5}, headers=auth_header(client, "palmicultor")
    )
    assert resp.status_code == 400


def test_calcular_balance_sin_datos_rechazado(client, auth_header):
    resp = client.post("/api/balance/calcular", json={}, headers=auth_header(client, "palmicultor"))
    assert resp.status_code == 400


def test_historial_balance_lista_lo_propio(client, auth_header):
    headers = auth_header(client, "palmicultor")
    client.post("/api/balance/calcular", json={"entrada_kg": 500}, headers=headers)
    resp = client.get("/api/balance/historial", headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 1


def test_comprador_no_puede_calcular_balance(client, auth_header):
    resp = client.post(
        "/api/balance/calcular", json={"entrada_kg": 500}, headers=auth_header(client, "comprador")
    )
    assert resp.status_code == 403
