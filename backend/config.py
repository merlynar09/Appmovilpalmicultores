import logging
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger("palma_viva.config")

# Modo desarrollo explícito: FLASK_ENV=development (o no estar definido, para no
# romper flujos locales existentes). Cualquier otro valor se trata como no-dev,
# y ahí los secretos SON obligatorios — nunca se arranca con un valor por
# defecto conocido fuera de desarrollo.
_ES_DESARROLLO = os.environ.get("FLASK_ENV", "development") == "development"

_SECRETOS_DEV_POR_DEFECTO = {
    "SECRET_KEY": "dev-secret-key-no-usar-en-produccion",
    "JWT_SECRET_KEY": "dev-jwt-secret-no-usar-en-produccion",
    "DATABASE_URL": "postgresql+psycopg2://postgres:postgres@localhost:5432/palma_viva",
}


def _requerido(nombre):
    valor = os.environ.get(nombre)
    if valor:
        return valor
    if _ES_DESARROLLO:
        logger.warning(
            "%s no está definida en el entorno — usando un valor de desarrollo. "
            "Esto NO debe pasar fuera de FLASK_ENV=development.",
            nombre,
        )
        return _SECRETOS_DEV_POR_DEFECTO[nombre]
    raise RuntimeError(
        f"La variable de entorno {nombre} es obligatoria fuera de FLASK_ENV=development "
        "y no tiene un valor seguro por defecto. Defínela en backend/.env antes de arrancar."
    )


def _normalizar_db_url(url):
    # DEV-F2-03: fuerza el driver psycopg2 explícitamente en vez de depender de
    # la resolución por defecto de SQLAlchemy para el esquema "postgresql://".
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    return url


class Config:
    SECRET_KEY = _requerido("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = _normalizar_db_url(_requerido("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = _requerido("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    JSON_SORT_KEYS = False

    # MOD-04: orígenes permitidos por CORS, configurables por ambiente.
    # Por defecto (desarrollo) se permite todo para no romper Expo Go/tunel/ngrok,
    # que cambian de origen constantemente durante las pruebas locales.
    _cors_env = os.environ.get("CORS_ORIGINS")
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else "*"
