"""DEV-F3-02: aislamiento real de las pruebas.

Antes, `conftest.py` reutilizaba la base configurada en el entorno (en la
práctica, la misma base de desarrollo) sin crear esquema, sin sembrar datos y
sin limpiar nada entre pruebas — dependía de que alguien ya hubiera corrido
`seed.py` a mano. Ahora cada prueba corre contra una base Postgres local
dedicada (`palma_viva_test`, nunca `palma_viva` ni Supabase), que se
reconstruye desde cero (drop_all + create_all + un seed mínimo) antes de
cada prueba — así cualquier prueba puede ejecutarse sola o en cualquier
orden sin depender de lo que dejó otra.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_NAME = "palma_viva_test"
# Credenciales del Postgres local de desarrollo por defecto; en CI
# (.github/workflows/tests.yml) se sobreescriben con las del servicio
# postgres de ese job — nunca apuntan a Supabase/producción.
_PG_HOST = os.environ.get("TEST_DB_HOST", "localhost")
_PG_PORT = os.environ.get("TEST_DB_PORT", "5432")
_PG_USER = os.environ.get("TEST_DB_USER", "postgres")
_PG_PASSWORD = os.environ.get("TEST_DB_PASSWORD", "123")
_PG_ADMIN_URL = f"postgresql://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/postgres"
_TEST_DB_URL = f"postgresql+psycopg2://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{TEST_DB_NAME}"

# Se fijan ANTES de importar `app` — config.py los lee al cargar el módulo.
os.environ.setdefault("FLASK_ENV", "development")
os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ.setdefault("SMS_USSD_SIMULATOR_ENABLED", "true")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("TWILIO_ENABLED", "false")
os.environ.setdefault("USSD_PROVIDER_SHARED_SECRET", "secreto-de-prueba")

import psycopg2
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Usuario, Comprador, Transportador, Finca, Lote

CREDENCIALES_SEED = [
    ("Carlos Quiñonez", "3001234567", "palma123", "palmicultor"),
    ("Extractora del Pacífico S.A.S.", "3002345678", "compra123", "comprador"),
    ("Jhon Caicedo", "3003456789", "transp123", "transportador"),
    ("Administrador Palma Viva", "3000000000", "admin123", "administrador"),
]


def _crear_base_de_prueba_si_no_existe():
    conn = psycopg2.connect(_PG_ADMIN_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        conn.close()


def _seed_basico():
    for nombre, telefono, password, rol in CREDENCIALES_SEED:
        usuario = Usuario.query.filter_by(telefono=telefono).first()
        if not usuario:
            usuario = Usuario(
                nombre_completo=nombre,
                telefono=telefono,
                password_hash=generate_password_hash(password),
                rol=rol,
                estado="activo",
            )
            db.session.add(usuario)
            db.session.flush()
        if rol == "comprador" and not Comprador.query.filter_by(usuario_id=usuario.id).first():
            db.session.add(
                Comprador(usuario_id=usuario.id, empresa=nombre, ubicacion="Tumaco", estado="activo")
            )
        if rol == "transportador" and not Transportador.query.filter_by(usuario_id=usuario.id).first():
            db.session.add(Transportador(usuario_id=usuario.id, ubicacion="Tumaco", estado="aprobado"))
    db.session.commit()

    # Finca + Lote-A1 del palmicultor del seed: varias pruebas de SMS/USSD
    # (heredadas de la suite original) asumen que este lote ya existe.
    palmicultor = Usuario.query.filter_by(telefono="3001234567").first()
    finca = Finca.query.filter_by(usuario_id=palmicultor.id).first()
    if not finca:
        finca = Finca(
            usuario_id=palmicultor.id,
            nombre="Finca La Esperanza",
            ubicacion="Vía Tumaco - Llorente, km 12",
            municipio="Tumaco",
            vereda="El Pital",
            coordenadas_lat=1.7986,
            coordenadas_long=-78.7896,
            area_hectareas=25,
            estado="activa",
        )
        db.session.add(finca)
        db.session.flush()
    if not Lote.query.filter_by(finca_id=finca.id, codigo="Lote-A1").first():
        db.session.add(
            Lote(
                finca_id=finca.id,
                codigo="Lote-A1",
                nombre="Sector norte",
                bloque="A",
                sector="1",
                area_hectareas=8,
                anio_siembra=2016,
                numero_palmas=960,
                material_sembrado="Híbrido OxG",
                topografia="Plano",
                drenaje="Bueno",
                estado_sanitario="Sano",
                numero_lineas=32,
                estado="activo",
            )
        )
    db.session.commit()


@pytest.fixture(scope="session")
def _flask_app_sesion():
    """Una sola app/engine/pool de conexiones para toda la sesión de pytest.

    Antes, `create_app()` se llamaba en un fixture de función (una vez por
    test): cada llamada crea un motor SQLAlchemy nuevo, y como nada
    desechaba el anterior, las conexiones Postgres de los motores viejos se
    iban acumulando test tras test hasta agotar `max_connections` a mitad de
    la suite completa (quedaba colgada, sin avisar con un error). Reusar la
    misma app/engine y solo recrear el esquema (`drop_all`/`create_all`) por
    test evita el problema de raíz.
    """
    _crear_base_de_prueba_si_no_existe()
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    yield flask_app
    with flask_app.app_context():
        db.engine.dispose()


@pytest.fixture()
def app(_flask_app_sesion):
    with _flask_app_sesion.app_context():
        db.drop_all()
        db.create_all()
        _seed_basico()
    yield _flask_app_sesion


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield app


_CREDENCIALES_POR_ROL = {
    "palmicultor": ("3001234567", "palma123"),
    "comprador": ("3002345678", "compra123"),
    "transportador": ("3003456789", "transp123"),
    "administrador": ("3000000000", "admin123"),
}


@pytest.fixture()
def token_for():
    """Evita repetir en cada archivo de test el patrón login + extraer token
    (antes duplicado entre test_auth.py, test_roles.py, test_crud_basico.py)."""

    def _token_for(client, rol):
        identifier, password = _CREDENCIALES_POR_ROL[rol]
        resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
        assert resp.status_code == 200, resp.get_json()
        return resp.get_json()["token"]

    return _token_for


@pytest.fixture()
def auth_header(token_for):
    def _auth_header(client, rol):
        return {"Authorization": f"Bearer {token_for(client, rol)}"}

    return _auth_header
