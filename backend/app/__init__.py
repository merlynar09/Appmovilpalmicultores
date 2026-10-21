from flask import Flask
from flask_cors import CORS
from config import Config
from app.extensions import db, migrate, jwt


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.market import market_bp
    from app.routes.logistics import logistics_bp
    from app.routes.fincas import fincas_bp
    from app.routes.produccion import produccion_bp
    from app.routes.pronosticos import pronosticos_bp
    from app.routes.alertas import alertas_bp
    from app.routes.balance import balance_bp
    from app.routes.admin import admin_bp
    from app.routes.sms import sms_bp
    from app.routes.ussd import ussd_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(market_bp, url_prefix="/api")
    app.register_blueprint(logistics_bp, url_prefix="/api")
    app.register_blueprint(fincas_bp, url_prefix="/api")
    app.register_blueprint(produccion_bp, url_prefix="/api")
    app.register_blueprint(pronosticos_bp, url_prefix="/api")
    app.register_blueprint(alertas_bp, url_prefix="/api")
    app.register_blueprint(balance_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(sms_bp, url_prefix="/api")
    app.register_blueprint(ussd_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
