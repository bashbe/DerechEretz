from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.test import Client

from app import create_app
from app.demo import DEMO_DIRECTEUR_EMAIL, seed_demo_data
from app.models import Classe, Eleve
from config import TestConfig


def test_seed_demo_data_ne_touche_pas_la_base_reelle(app):
    assert Eleve.query.count() == 0

    cree = seed_demo_data(app)

    assert cree is True
    assert Eleve.query.count() == 0
    assert Classe.query.count() == 0


def test_seed_demo_data_peuple_trois_classes_de_vingt_eleves(app):
    seed_demo_data(app)

    from app.extensions import db
    from flask import g

    g.is_demo = True
    try:
        assert Classe.query.count() == 3
        assert Eleve.query.count() == 60
        for classe in Classe.query.all():
            assert len(classe.eleves) == 20
    finally:
        db.session.remove()


def test_seed_demo_data_est_idempotente(app):
    assert seed_demo_data(app) is True
    assert seed_demo_data(app) is False


def test_sous_domaine_demo_isole_et_autologin(app):
    seed_demo_data(app)
    client = app.test_client()

    reel = client.get("/", headers={"Host": "mon-ecole.test"})
    assert reel.status_code == 302
    assert "/login" in reel.headers["Location"]

    demo = client.get("/", headers={"Host": "demo.mon-ecole.test"})
    assert demo.status_code == 302
    assert demo.headers["Location"].endswith("/tableau-de-bord")

    tableau = client.get(demo.headers["Location"], headers={"Host": "demo.mon-ecole.test"})
    assert tableau.status_code == 200
    assert "Mode démonstration" in tableau.get_data(as_text=True)


def test_demo_accessible_via_prefixe_chemin_demo(tmp_path):
    """Pour les hébergements sans sous-domaine configurable, /demo doit servir
    exactement la même démo (mêmes routes, liens toujours préfixés /demo)."""
    demo_db_uri = f"sqlite:///{tmp_path / 'demo_test.db'}"

    class RealConfig(TestConfig):
        SQLALCHEMY_BINDS = {"demo": demo_db_uri}

    class DemoPathConfig(TestConfig):
        FORCE_DEMO_MODE = True
        SQLALCHEMY_BINDS = {"demo": demo_db_uri}

    real_app = create_app(RealConfig)
    demo_app = create_app(DemoPathConfig)
    seed_demo_data(real_app)

    client = Client(DispatcherMiddleware(real_app, {"/demo": demo_app}))

    reel = client.get("/")
    assert reel.status_code == 302
    assert "/login" in reel.headers["Location"]

    demo = client.get("/demo/")
    assert demo.status_code == 302
    assert demo.headers["Location"] == "/demo/tableau-de-bord"

    tableau = client.get(demo.headers["Location"])
    assert tableau.status_code == 200
    body = tableau.get_data(as_text=True)
    assert "Mode démonstration" in body
    assert 'href="/demo/eleves"' in body


def test_compte_demo_directeur_existe(app):
    from app.extensions import db
    from flask import g
    from app.models import User

    seed_demo_data(app)

    g.is_demo = True
    try:
        demo_user = User.query.filter_by(email=DEMO_DIRECTEUR_EMAIL).first()
        assert demo_user is not None
        assert demo_user.is_directeur()
    finally:
        db.session.remove()
