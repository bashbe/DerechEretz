import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ecole.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CYCLE_DISCIPLINE_JOURS = 15
    POINTS_VIE_SCOLAIRE_DEPART = 20

    # Démo : quand une requête arrive sur le sous-domaine DEMO_SUBDOMAIN
    # (ex. demo.monecole.fr), toute la session bascule sur cette base à
    # part, entièrement isolée des données réelles (voir app/demo.py).
    DEMO_SUBDOMAIN = os.environ.get("DEMO_SUBDOMAIN", "demo")
    SQLALCHEMY_BINDS = {
        "demo": os.environ.get(
            "DEMO_DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'demo.db')}"
        )
    }


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_BINDS = {"demo": "sqlite:///:memory:"}
    WTF_CSRF_ENABLED = False
