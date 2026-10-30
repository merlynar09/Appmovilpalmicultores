"""MOD-08: cobertura mínima de los CRUD agregados en la sesión anterior
(puntos de comercialización CU6/CU14, compradores admin CU13) — antes no
tenían ningún test automatizado."""

from app.extensions import db
from app.models import PuntoComercializacion

TEL_ADMIN = "3000000000"
PASSWORD_ADMIN = "admin123"

TEL_COMPRADOR = "3002345678"
PASSWORD_COMPRADOR = "compra123"


def _token(client, identifier, password):
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_puntos_comercializacion_crud_completo(client, app_ctx):
    token = _token(client, TEL_ADMIN, PASSWORD_ADMIN)

    creado = client.post(
        "/api/admin/puntos-comercializacion",
        json={"nombre": "Punto de prueba automatizada", "ubicacion": "Tumaco"},
        headers=_auth(token),
    )
    assert creado.status_code == 201
    punto_id = creado.get_json()["id"]

    try:
        publico = client.get("/api/puntos-comercializacion")
        assert publico.status_code == 200
        assert any(p["id"] == punto_id for p in publico.get_json())

        editado = client.put(
            f"/api/admin/puntos-comercializacion/{punto_id}",
            json={"descripcion": "Editado por test"},
            headers=_auth(token),
        )
        assert editado.status_code == 200
        assert editado.get_json()["descripcion"] == "Editado por test"

        desactivado = client.patch(
            f"/api/admin/puntos-comercializacion/{punto_id}/estado",
            json={"estado": "inactivo"},
            headers=_auth(token),
        )
        assert desactivado.status_code == 200

        publico_tras_desactivar = client.get("/api/puntos-comercializacion")
        assert not any(p["id"] == punto_id for p in publico_tras_desactivar.get_json())
    finally:
        punto = PuntoComercializacion.query.get(punto_id)
        if punto:
            db.session.delete(punto)
            db.session.commit()


def test_puntos_comercializacion_nombre_obligatorio(client):
    token = _token(client, TEL_ADMIN, PASSWORD_ADMIN)
    resp = client.post("/api/admin/puntos-comercializacion", json={}, headers=_auth(token))
    assert resp.status_code == 400


def test_admin_lista_y_edita_comprador(client):
    token = _token(client, TEL_ADMIN, PASSWORD_ADMIN)

    listado = client.get("/api/admin/compradores", headers=_auth(token))
    assert listado.status_code == 200
    compradores = listado.get_json()
    assert len(compradores) >= 1
    comprador_id = compradores[0]["id"]

    descripcion_original = compradores[0]["descripcion"]
    try:
        editado = client.put(
            f"/api/admin/compradores/{comprador_id}",
            json={"descripcion": "Descripción editada por test"},
            headers=_auth(token),
        )
        assert editado.status_code == 200
        assert editado.get_json()["descripcion"] == "Descripción editada por test"
    finally:
        client.put(
            f"/api/admin/compradores/{comprador_id}",
            json={"descripcion": descripcion_original},
            headers=_auth(token),
        )


def test_admin_publica_precio_de_comprador(client):
    token_admin = _token(client, TEL_ADMIN, PASSWORD_ADMIN)
    token_comprador = _token(client, TEL_COMPRADOR, PASSWORD_COMPRADOR)

    compradores = client.get("/api/admin/compradores", headers=_auth(token_admin)).get_json()
    comprador = next(c for c in compradores if c["telefono"] == TEL_COMPRADOR or c["nombre_usuario"])
    comprador_id = comprador["id"]

    resp = client.post(
        f"/api/admin/compradores/{comprador_id}/precios",
        json={"valor_moneda": 1234567},
        headers=_auth(token_admin),
    )
    assert resp.status_code == 201
    assert float(resp.get_json()["valor_moneda"]) == 1234567.0

    # El propio comprador sigue pudiendo ver/publicar su precio sin romperse.
    propio = client.get("/api/precios/mios", headers=_auth(token_comprador))
    assert propio.status_code == 200
