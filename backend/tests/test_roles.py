"""MOD-08: matriz mínima de autorización por rol (role_required). Verifica
que el control de acceso se aplique de verdad en el backend, no solo que
el frontend oculte botones."""

TEL_PALMICULTOR = "3001234567"
PASSWORD_PALMICULTOR = "palma123"

TEL_COMPRADOR = "3002345678"
PASSWORD_COMPRADOR = "compra123"

TEL_ADMIN = "3000000000"
PASSWORD_ADMIN = "admin123"


def _token(client, identifier, password):
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_palmicultor_no_accede_a_endpoint_admin(client):
    token = _token(client, TEL_PALMICULTOR, PASSWORD_PALMICULTOR)
    resp = client.get("/api/admin/usuarios", headers=_auth(token))
    assert resp.status_code == 403


def test_comprador_no_accede_a_endpoint_de_palmicultor(client):
    token = _token(client, TEL_COMPRADOR, PASSWORD_COMPRADOR)
    resp = client.get("/api/fincas", headers=_auth(token))
    assert resp.status_code == 403


def test_palmicultor_no_accede_a_endpoint_de_comprador(client):
    token = _token(client, TEL_PALMICULTOR, PASSWORD_PALMICULTOR)
    resp = client.get("/api/precios/mios", headers=_auth(token))
    assert resp.status_code == 403


def test_admin_accede_a_endpoint_admin(client):
    token = _token(client, TEL_ADMIN, PASSWORD_ADMIN)
    resp = client.get("/api/admin/usuarios", headers=_auth(token))
    assert resp.status_code == 200


def test_admin_accede_a_endpoint_nuevo_de_compradores(client):
    token = _token(client, TEL_ADMIN, PASSWORD_ADMIN)
    resp = client.get("/api/admin/compradores", headers=_auth(token))
    assert resp.status_code == 200


def test_palmicultor_no_puede_gestionar_puntos_comercializacion(client):
    token = _token(client, TEL_PALMICULTOR, PASSWORD_PALMICULTOR)
    resp = client.post(
        "/api/admin/puntos-comercializacion",
        json={"nombre": "Punto no autorizado"},
        headers=_auth(token),
    )
    assert resp.status_code == 403
