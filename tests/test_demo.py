from app.demo import DEMO_DIRECTEUR_EMAIL, seed_demo_data
from app.models import Classe, Eleve


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
