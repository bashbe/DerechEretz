from flask import Flask

from app.extensions import db, login_manager, migrate
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.directeur.routes import directeur_bp
    from app.professeur.routes import professeur_bp
    from app.surveillant.routes import surveillant_bp
    from app.eleves.routes import eleves_bp
    from app.demo.routes import demo_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(directeur_bp, url_prefix="/directeur")
    app.register_blueprint(professeur_bp, url_prefix="/professeur")
    app.register_blueprint(surveillant_bp, url_prefix="/surveillant")
    app.register_blueprint(eleves_bp)
    app.register_blueprint(demo_bp)

    from app.cli import register_cli

    register_cli(app)

    from app.errors import register_error_handlers

    register_error_handlers(app)

    return app
