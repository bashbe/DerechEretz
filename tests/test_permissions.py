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


# --- Événements (couche unifiée) ------------------------------------------

from datetime import date

from app.models import Eleve, Notice
from app.permissions import peut_modifier_evenement, peut_voir_presences, types_evenements_creables


def test_types_evenements_creables_par_role(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert types_evenements_creables(directeur) == {
        "note", "observation", "infraction_mineure", "infraction_majeure", "presence"
    }
    assert types_evenements_creables(surveillant) == {
        "observation", "infraction_mineure", "infraction_majeure", "presence"
    }
    assert types_evenements_creables(professeur) == {"note", "observation"}


def test_peut_voir_presences_pas_professeur(app):
    assert peut_voir_presences(_make_user("directeur")) is True
    assert peut_voir_presences(_make_user("surveillant")) is True
    assert peut_voir_presences(_make_user("professeur")) is False


def test_peut_modifier_evenement_selon_role_et_auteur(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")
    autre_prof = User(nom="Autre prof", email="prof2@ecole.test", role="professeur")
    autre_prof.set_password("password123")
    db.session.add(autre_prof)
    db.session.commit()

    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    db.session.add_all([classe, eleve])
    db.session.commit()

    observation_prof = Notice(
        eleve=eleve, titre="Obs", contenu="x", date=date(2026, 1, 5), saisi_par_id=professeur.id
    )
    db.session.add(observation_prof)
    db.session.commit()

    # directeur : toujours
    assert peut_modifier_evenement(directeur, "presence", observation_prof) is True
    # surveillant : vie scolaire/présences oui, observation d'autrui non
    assert peut_modifier_evenement(surveillant, "infraction_mineure", observation_prof) is True
    assert peut_modifier_evenement(surveillant, "observation", observation_prof) is False
    # professeur : ses propres notes/observations seulement
    assert peut_modifier_evenement(professeur, "observation", observation_prof) is True
    assert peut_modifier_evenement(autre_prof, "observation", observation_prof) is False
    assert peut_modifier_evenement(professeur, "presence", observation_prof) is False
