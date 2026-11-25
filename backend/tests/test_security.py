"""Pruebas dirigidas a los hallazgos de la Fase 4 (API/autenticación/permisos)
de la segunda auditoría del profesor."""
import subprocess
import sys

from app.extensions import db
from app.models import Usuario, PasswordResetToken

# Las dos pruebas de "fuera de desarrollo" (CORS, dev_codigo) dependen de
# lógica evaluada al IMPORTAR config.py (FLASK_ENV leído una sola vez al
# cargar el módulo) — por eso corren en un proceso Python aparte en vez de
# monkeypatchear el proceso de pytest, que ya tiene `config` cargado con
# FLASK_ENV=development y contaminaría las demás pruebas de este archivo.
_BACKEND_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent


def _preparar_db_aislada():
    import psycopg2

    conn = psycopg2.connect("postgresql://postgres:123@localhost:5432/postgres")
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'palma_viva_test_aislado'")
            if not cur.fetchone():
                cur.execute('CREATE DATABASE "palma_viva_test_aislado"')
    finally:
        conn.close()


def _correr_en_proceso_aislado(codigo_python, env_extra):
    import os as _os

    env = _os.environ.copy()
    env.update(env_extra)
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_python],
        cwd=str(_BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return resultado

TEL_PALMICULTOR = "3001234567"
PASSWORD_PALMICULTOR = "palma123"


# --------------------------------------------------- DEV-F4-01 (crítica) ----

def test_registro_publico_no_puede_crear_administrador(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Intento de admin",
            "telefono": "3219990010",
            "password": "clave123",
            "rol": "administrador",
        },
    )
    assert resp.status_code == 400


def test_admin_crea_administrador_por_el_canal_correcto(client, token_for):
    token = token_for(client, "administrador")
    resp = client.post(
        "/api/admin/usuarios",
        json={"nombre_completo": "Nuevo Admin", "telefono": "3219990011", "password": "clave123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["rol"] == "administrador"


def test_no_admin_no_puede_crear_administrador(client, token_for):
    token = token_for(client, "palmicultor")
    resp = client.post(
        "/api/admin/usuarios",
        json={"nombre_completo": "Intento", "telefono": "3219990012", "password": "clave123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# --------------------------------------------- DEV-F4-02 / DEV-F4-03 --------

def test_token_de_usuario_suspendido_deja_de_funcionar(client, token_for, app_ctx):
    token = token_for(client, "palmicultor")
    resp_ok = client.get("/api/fincas", headers={"Authorization": f"Bearer {token}"})
    assert resp_ok.status_code == 200

    admin_token = token_for(client, "administrador")
    usuario = Usuario.query.filter_by(telefono=TEL_PALMICULTOR).first()
    client.patch(
        f"/api/admin/usuarios/{usuario.id}/estado",
        json={"estado": "suspendido"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp_tras_suspender = client.get("/api/fincas", headers={"Authorization": f"Bearer {token}"})
    assert resp_tras_suspender.status_code == 401


def test_token_anterior_deja_de_funcionar_tras_reset_password(client, app_ctx):
    telefono = "3219990013"
    client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Usuario Reset",
            "telefono": telefono,
            "password": "clave123",
            "rol": "palmicultor",
        },
    )
    login = client.post("/api/auth/login", json={"identifier": telefono, "password": "clave123"})
    token_viejo = login.get_json()["token"]
    assert client.get("/api/fincas", headers={"Authorization": f"Bearer {token_viejo}"}).status_code == 200

    usuario = Usuario.query.filter_by(telefono=telefono).first()
    codigo = "123456"
    db.session.add(
        PasswordResetToken(
            usuario_id=usuario.id,
            codigo=__import__("werkzeug.security", fromlist=["generate_password_hash"]).generate_password_hash(codigo),
            expira_en=__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(minutes=15),
        )
    )
    db.session.commit()

    reset = client.post(
        "/api/auth/reset-password",
        json={"identifier": telefono, "codigo": codigo, "password": "claveNueva123"},
    )
    assert reset.status_code == 200

    resp_token_viejo = client.get("/api/fincas", headers={"Authorization": f"Bearer {token_viejo}"})
    assert resp_token_viejo.status_code == 401

    login_nuevo = client.post(
        "/api/auth/login", json={"identifier": telefono, "password": "claveNueva123"}
    )
    assert login_nuevo.status_code == 200


def test_logout_revoca_el_token_actual(client, token_for):
    token = token_for(client, "palmicultor")
    assert client.get("/api/fincas", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200

    resp = client.get("/api/fincas", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ------------------------------------------------------------ DEV-F4-04 -----

def test_forgot_password_no_expone_el_codigo_fuera_de_desarrollo():
    script = """
import json
from app import create_app
from app.extensions import db

app = create_app()
app.config.update(TESTING=True)
with app.app_context():
    db.create_all()
    client = app.test_client()
    client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Usuario Prod",
            "telefono": "3219990014",
            "password": "clave123",
            "rol": "palmicultor",
        },
    )
    resp = client.post("/api/auth/forgot-password", json={"identifier": "3219990014"})
    assert resp.status_code == 200, resp.get_json()
    assert "dev_codigo" not in resp.get_json(), resp.get_json()
    print("OK")
"""
    env_extra = {
        "FLASK_ENV": "testing",
        "SECRET_KEY": "test-secret",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "CORS_ORIGINS": "https://example.test",
        "DATABASE_URL": "postgresql+psycopg2://postgres:123@localhost:5432/palma_viva_test_aislado",
    }
    _preparar_db_aislada()
    resultado = _correr_en_proceso_aislado(script, env_extra)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "OK" in resultado.stdout


def test_codigo_de_recuperacion_se_guarda_con_hash_no_en_claro(client, app_ctx):
    telefono = "3219990015"
    client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Usuario Codigo",
            "telefono": telefono,
            "password": "clave123",
            "rol": "palmicultor",
        },
    )
    resp = client.post("/api/auth/forgot-password", json={"identifier": telefono})
    codigo_plano = resp.get_json().get("dev_codigo")
    assert codigo_plano  # en desarrollo (default de los tests) sí viene, para poder probar el flujo

    usuario = Usuario.query.filter_by(telefono=telefono).first()
    token_guardado = (
        PasswordResetToken.query.filter_by(usuario_id=usuario.id).order_by(PasswordResetToken.id.desc()).first()
    )
    assert token_guardado.codigo != codigo_plano


def test_segundo_codigo_invalida_el_primero(client, app_ctx):
    telefono = "3219990016"
    client.post(
        "/api/auth/register",
        json={
            "nombre_completo": "Usuario Dos Codigos",
            "telefono": telefono,
            "password": "clave123",
            "rol": "palmicultor",
        },
    )
    primero = client.post("/api/auth/forgot-password", json={"identifier": telefono}).get_json()["dev_codigo"]
    client.post("/api/auth/forgot-password", json={"identifier": telefono})  # segundo código

    resp = client.post("/api/auth/verify-code", json={"identifier": telefono, "codigo": primero})
    assert resp.status_code == 400


# ------------------------------------------------------------ DEV-F4-05 -----

def test_rate_limit_en_login():
    # El resto de la suite corre con RATELIMIT_ENABLED=false (ver conftest.py,
    # fijado por variable de entorno ANTES de crear la app) para que los
    # contadores en memoria de Flask-Limiter no se acumulen entre pruebas no
    # relacionadas y empiecen a devolver 429 donde se esperaba 200/201.
    # Flask-Limiter, cuando arranca deshabilitado, ni siquiera inicializa su
    # backend de almacenamiento — no hay forma de "reactivarlo" después sobre
    # la misma app ya creada. Por eso esta única prueba corre en un proceso
    # aparte, con el rate limiting en su estado real (habilitado, como en
    # producción) desde que arranca la app.
    script = """
from app import create_app
from app.extensions import db

app = create_app()
app.config.update(TESTING=True)
with app.app_context():
    db.create_all()
client = app.test_client()
for _ in range(10):
    client.post("/api/auth/login", json={"identifier": "3001234567", "password": "incorrecta"})
resp = client.post("/api/auth/login", json={"identifier": "3001234567", "password": "incorrecta"})
assert resp.status_code == 429, resp.get_json()
print("OK")
"""
    env_extra = {
        "RATELIMIT_ENABLED": "true",
        "FLASK_ENV": "development",
        "DATABASE_URL": "postgresql+psycopg2://postgres:123@localhost:5432/palma_viva_test_aislado",
    }
    _preparar_db_aislada()
    resultado = _correr_en_proceso_aislado(script, env_extra)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "OK" in resultado.stdout


# ------------------------------------------------------------ DEV-F4-06 -----

def test_cors_cerrado_por_defecto_fuera_de_desarrollo(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("FLASK_ENV", "testing")
    import config

    monkeypatch.setattr(config, "_ES_DESARROLLO", False)
    try:
        import importlib

        with __import__("pytest").raises(RuntimeError):
            importlib.reload(config)
    finally:
        monkeypatch.setenv("FLASK_ENV", "development")
        import importlib

        importlib.reload(config)
