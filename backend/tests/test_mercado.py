"""Pruebas dirigidas a los hallazgos de Fase 5 sobre mercado: F5-06 (interés
de compra) y F5-07 (distancia nula sin coordenadas)."""


def _publicacion_del_palmicultor(client, auth_header):
    headers = auth_header(client, "palmicultor")
    resp = client.post(
        "/api/mercado/publicaciones",
        json={"cantidad_toneladas": 5, "descripcion": "Fruto fresco"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.get_json()["id"]


def test_comprador_manifiesta_interes(client, auth_header):
    publicacion_id = _publicacion_del_palmicultor(client, auth_header)
    headers_comprador = auth_header(client, "comprador")

    resp = client.post(
        f"/api/mercado/publicaciones/{publicacion_id}/interes",
        json={"mensaje": "Me interesa, ¿cuándo se puede recoger?"},
        headers=headers_comprador,
    )
    assert resp.status_code == 201
    assert resp.get_json()["publicacion_id"] == publicacion_id

    headers_palmicultor = auth_header(client, "palmicultor")
    listado = client.get(
        f"/api/mercado/publicaciones/{publicacion_id}/intereses", headers=headers_palmicultor
    )
    assert listado.status_code == 200
    assert len(listado.get_json()) == 1


def test_manifestar_interes_dos_veces_no_duplica(client, auth_header):
    publicacion_id = _publicacion_del_palmicultor(client, auth_header)
    headers_comprador = auth_header(client, "comprador")

    client.post(f"/api/mercado/publicaciones/{publicacion_id}/interes", json={}, headers=headers_comprador)
    client.post(f"/api/mercado/publicaciones/{publicacion_id}/interes", json={}, headers=headers_comprador)

    headers_palmicultor = auth_header(client, "palmicultor")
    listado = client.get(
        f"/api/mercado/publicaciones/{publicacion_id}/intereses", headers=headers_palmicultor
    )
    assert len(listado.get_json()) == 1


def test_palmicultor_no_puede_ver_intereses_de_publicacion_ajena(client, auth_header, app_ctx):
    publicacion_id = _publicacion_del_palmicultor(client, auth_header)

    from werkzeug.security import generate_password_hash
    from app.extensions import db
    from app.models import Usuario

    otro = Usuario(
        nombre_completo="Otro Palmicultor",
        telefono="3219990030",
        password_hash=generate_password_hash("clave123"),
        rol="palmicultor",
        estado="activo",
    )
    db.session.add(otro)
    db.session.commit()
    token = client.post(
        "/api/auth/login", json={"identifier": "3219990030", "password": "clave123"}
    ).get_json()["token"]

    resp = client.get(
        f"/api/mercado/publicaciones/{publicacion_id}/intereses",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_distancia_nula_sin_coordenadas(client):
    resp = client.get("/api/compradores/cercanos")
    assert resp.status_code == 200
    for comprador in resp.get_json():
        assert comprador["distanciaKm"] is None


def test_distancia_calculada_con_coordenadas(client, app_ctx):
    from app.extensions import db
    from app.models import Comprador

    comprador = Comprador.query.first()
    comprador.latitud = 1.7912
    comprador.longitud = -78.7813
    db.session.commit()

    # Punto cercano en Tumaco (unos pocos km de diferencia).
    resp = client.get("/api/compradores/cercanos?lat=1.80&lon=-78.78")
    assert resp.status_code == 200
    distancias = [c["distanciaKm"] for c in resp.get_json() if c["id"] == comprador.id]
    assert distancias and distancias[0] is not None
    assert distancias[0] < 50


def test_comprador_sin_ubicacion_no_se_puede_registrar(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Comprador Sin Ubicacion",
            "telefono": "3219990031",
            "password": "clave123",
            "rol": "comprador",
        },
    )
    assert resp.status_code == 400
