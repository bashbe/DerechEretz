from app.extensions import db
from app.models import AffectationProf, Classe, Matiere, User
from app.permissions import (
    peut_gerer_controle,
    peut_gerer_presences,
    peut_gerer_vie_scolaire,
    peut_generer_rapports,
    peut_voir_admin,
)


def _make_user(role):
    user = User(nom=role.capitalize(), email=f"{role}@ecole.test", role=role)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def test_peut_voir_admin_seulement_directeur(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_voir_admin(directeur) is True
    assert peut_voir_admin(surveillant) is False
    assert peut_voir_admin(professeur) is False


def test_peut_gerer_presences_directeur_et_surveillant(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_gerer_presences(directeur) is True
    assert peut_gerer_presences(surveillant) is True
    assert peut_gerer_presences(professeur) is False


def test_peut_gerer_vie_scolaire_directeur_et_surveillant(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_gerer_vie_scolaire(directeur) is True
    assert peut_gerer_vie_scolaire(surveillant) is True
    assert peut_gerer_vie_scolaire(professeur) is False


def test_peut_generer_rapports_directeur_et_surveillant(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_generer_rapports(directeur) is True
    assert peut_generer_rapports(surveillant) is True
    assert peut_generer_rapports(professeur) is False


def test_peut_gerer_controle_professeur_seulement_ses_affectations(app):
    professeur = _make_user("professeur")
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    maths = Matiere(nom="Maths", coefficient=3)
    sport = Matiere(nom="Sport", coefficient=1)
    db.session.add_all([classe, maths, sport])
    db.session.commit()
    db.session.add(
        AffectationProf(professeur_id=professeur.id, matiere_id=maths.id, classe_id=classe.id)
    )
    db.session.commit()

    assert peut_gerer_controle(professeur, maths.id, classe.id) is True
    assert peut_gerer_controle(professeur, sport.id, classe.id) is False


def test_peut_gerer_controle_directeur_toujours_vrai(app):
    directeur = _make_user("directeur")
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    maths = Matiere(nom="Maths", coefficient=3)
    db.session.add_all([classe, maths])
    db.session.commit()

    assert peut_gerer_controle(directeur, maths.id, classe.id) is True


def test_peut_gerer_controle_surveillant_toujours_faux(app):
    surveillant = _make_user("surveillant")
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    maths = Matiere(nom="Maths", coefficient=3)
    db.session.add_all([classe, maths])
    db.session.commit()

    assert peut_gerer_controle(surveillant, maths.id, classe.id) is False
