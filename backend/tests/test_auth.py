"""MOD-08: cobertura mínima de autenticación (registro, login, JWT) — antes
no existía ningún test fuera de SMS/USSD."""

from app.extensions import db
from app.models import Usuario

TEL_PALMICULTOR = "3001234567"
PASSWORD_PALMICULTOR = "palma123"


def _borrar_usuario(telefono):
    usuario = Usuario.query.filter_by(telefono=telefono).first()
    if usuario:
        db.session.delete(usuario)
        db.session.commit()


def test_registro_exitoso(client, app_ctx):
    telefono = "3219990001"
    _borrar_usuario(telefono)
    try:
        resp = client.post(
            "/api/auth/register",
            json={
                "nombre_completo": "Usuario de Prueba",
                "telefono": telefono,
                "password": "clave123",
                "rol": "palmicultor",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["token"]
        assert data["usuario"]["telefono"] == telefono
        assert data["usuario"]["rol"] == "palmicultor"
    finally:
        _borrar_usuario(telefono)


def test_registro_telefono_duplicado_rechazado(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Otro Usuario",
            "telefono": TEL_PALMICULTOR,  # ya existe en el seed
            "password": "clave123",
            "rol": "palmicultor",
        },
    )
    assert resp.status_code == 409


def test_registro_rol_invalido_rechazado(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Usuario Rol Invalido",
            "telefono": "3219990002",
            "password": "clave123",
            "rol": "superadmin",
        },
    )
    assert resp.status_code == 400


def test_login_exitoso(client):
    resp = client.post(
        "/api/auth/login",
        json={"identifier": TEL_PALMICULTOR, "password": PASSWORD_PALMICULTOR},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["token"]
    assert data["usuario"]["telefono"] == TEL_PALMICULTOR


def test_login_password_incorrecta(client):
    resp = client.post(
        "/api/auth/login",
        json={"identifier": TEL_PALMICULTOR, "password": "password-incorrecta"},
    )
    assert resp.status_code == 401


def test_login_usuario_inexistente(client):
    resp = client.post(
        "/api/auth/login",
        json={"identifier": "3009999999", "password": "lo-que-sea"},
    )
    assert resp.status_code == 401


def test_login_cuenta_suspendida_rechazado(client, app_ctx):
    telefono = "3219990003"
    _borrar_usuario(telefono)
    try:
        client.post(
            "/api/auth/register",
            json={
                "nombre_completo": "Usuario Suspendido",
                "telefono": telefono,
                "password": "clave123",
                "rol": "palmicultor",
            },
        )
        usuario = Usuario.query.filter_by(telefono=telefono).first()
        usuario.estado = "suspendido"
        db.session.commit()

        resp = client.post("/api/auth/login", json={"identifier": telefono, "password": "clave123"})
        assert resp.status_code == 403
    finally:
        _borrar_usuario(telefono)


def test_endpoint_protegido_sin_token_rechazado(client):
    resp = client.get("/api/fincas")
    assert resp.status_code == 401


def test_endpoint_protegido_con_token_valido(client):
    login = client.post(
        "/api/auth/login",
        json={"identifier": TEL_PALMICULTOR, "password": PASSWORD_PALMICULTOR},
    )
    token = login.get_json()["token"]
    resp = client.get("/api/fincas", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_endpoint_protegido_con_token_invalido_rechazado(client):
    resp = client.get("/api/fincas", headers={"Authorization": "Bearer token-invalido"})
    assert resp.status_code in (401, 422)
