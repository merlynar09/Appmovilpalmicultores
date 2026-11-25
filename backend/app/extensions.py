from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# DEV-F4-05: almacenamiento en memoria — suficiente para la única instancia
# del plan gratuito de Render; evita depender de Redis solo para esto.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
