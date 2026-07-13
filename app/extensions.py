from flask import g, has_app_context
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.session import Session as _FlaskSQLAlchemySession
from flask_migrate import Migrate
from flask_login import LoginManager


class _DemoAwareSession(_FlaskSQLAlchemySession):
    """Session qui redirige toutes les requêtes vers la base "demo" quand la
    requête HTTP courante vient du sous-domaine de démonstration.

    Cela permet à tout le code applicatif (routes, services) d'utiliser les
    mêmes modèles et les mêmes `Model.query` sans aucune modification : seule
    la base physique interrogée change, selon le nom d'hôte de la requête.
    Voir `app/demo.py` pour la détection du sous-domaine (`g.is_demo`).
    """

    def get_bind(self, mapper=None, clause=None, bind=None, **kwargs):
        if bind is None and has_app_context() and g.get("is_demo", False):
            demo_engine = self._db.engines.get("demo")
            if demo_engine is not None:
                return demo_engine
        return super().get_bind(mapper=mapper, clause=clause, bind=bind, **kwargs)


db = SQLAlchemy(session_options={"class_": _DemoAwareSession})
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
