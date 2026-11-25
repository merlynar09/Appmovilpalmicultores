from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from app.extensions import db, migrate, jwt, limiter


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # DEV-F4-05: Render corre detrás de un proxy inverso — sin esto, el
    # rate limiter vería siempre la IP del proxy en vez de la del cliente
    # real y limitaría a todo el tráfico como si fuera un solo usuario.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

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
    from app.routes.puntos import puntos_bp

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
    app.register_blueprint(puntos_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        # El keep-alive de GitHub Actions le pega a esta ruta para evitar que
        # Render y Supabase se duerman por inactividad — antes solo
        # respondía "ok" sin tocar la base, así que no evitaba que Supabase
        # (que se pausa por inactividad de la BASE, no del backend) se
        # pausara igual. Una consulta mínima mantiene la conexión real viva.
        try:
            db.session.execute(db.text("SELECT 1"))
            estado_bd = "ok"
        except Exception:
            estado_bd = "error"
        return {"status": "ok", "database": estado_bd}

    # DEV-F4-08 / F5-11: antes, cualquier excepción no controlada (una
    # entrada que rompe un float(), una violación de restricción de BD, un
    # 404/405 de Flask) devolvía la página HTML de error por defecto en vez
    # de JSON, lo que un cliente que solo sabe leer JSON no puede interpretar.
    @app.errorhandler(HTTPException)
    def _manejar_error_http(err):
        return jsonify({"message": err.description or err.name}), err.code

    @app.errorhandler(Exception)
    def _manejar_error_inesperado(err):
        db.session.rollback()
        app.logger.exception("Error no controlado")
        return jsonify({"message": "Ocurrió un error interno. Intenta de nuevo."}), 500

    return app
