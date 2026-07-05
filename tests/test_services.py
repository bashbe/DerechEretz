from datetime import date

from app.extensions import db
from app.models import (
    Classe,
    CycleDiscipline,
    Eleve,
    InfractionMineure,
    Matiere,
    Note,
    TypeInfractionMineure,
    User,
)
from app.services import (
    calculer_moyenne_generale,
    calculer_moyenne_matiere,
    appliquer_infraction_mineure,
    cloturer_cycle,
)


def _make_eleve(classe_nom="6A"):
    classe = Classe(nom=classe_nom, annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe, points_vie_scolaire=20)
    db.session.add_all([classe, eleve])
    db.session.commit()
    return eleve


def _make_user(role="directeur"):
    user = User(nom="Admin", email=f"{role}@ecole.test", role=role)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def test_moyenne_matiere_simple_average(app):
    eleve = _make_eleve()
    matiere = Matiere(nom="Maths", coefficient=3)
    user = _make_user()
    db.session.add(matiere)
    db.session.commit()

    db.session.add_all(
        [
            Note(eleve=eleve, matiere=matiere, valeur=10, trimestre="T1", saisi_par=user),
            Note(eleve=eleve, matiere=matiere, valeur=14, trimestre="T1", saisi_par=user),
        ]
    )
    db.session.commit()

    assert calculer_moyenne_matiere(eleve.id, matiere.id, "T1") == 12.0


def test_moyenne_matiere_sans_notes_retourne_none(app):
    eleve = _make_eleve()
    matiere = Matiere(nom="Maths", coefficient=3)
    db.session.add(matiere)
    db.session.commit()

    assert calculer_moyenne_matiere(eleve.id, matiere.id, "T1") is None


def test_moyenne_generale_ponderee_par_coefficient(app):
    eleve = _make_eleve()
    user = _make_user()
    maths = Matiere(nom="Maths", coefficient=3)
    sport = Matiere(nom="Sport", coefficient=1)
    db.session.add_all([maths, sport])
    db.session.commit()

    db.session.add_all(
        [
            Note(eleve=eleve, matiere=maths, valeur=10, trimestre="T1", saisi_par=user),
            Note(eleve=eleve, matiere=sport, valeur=18, trimestre="T1", saisi_par=user),
        ]
    )
    db.session.commit()

    # (10*3 + 18*1) / (3+1) = 48/4 = 12.0
    assert calculer_moyenne_generale(eleve.id, "T1") == 12.0


def test_moyenne_generale_ignore_matieres_sans_notes(app):
    eleve = _make_eleve()
    user = _make_user()
    maths = Matiere(nom="Maths", coefficient=3)
    sport = Matiere(nom="Sport", coefficient=1)
    db.session.add_all([maths, sport])
    db.session.commit()

    db.session.add(Note(eleve=eleve, matiere=maths, valeur=10, trimestre="T1", saisi_par=user))
    db.session.commit()

    assert calculer_moyenne_generale(eleve.id, "T1") == 10.0


def test_appliquer_infraction_mineure_deduit_points(app):
    eleve = _make_eleve()
    user = _make_user("surveillant")
    type_infraction = TypeInfractionMineure(libelle="Retard répété", points_deduits=2)
    db.session.add(type_infraction)
    db.session.commit()

    appliquer_infraction_mineure(eleve, type_infraction, user)

    assert eleve.points_vie_scolaire == 18


def test_appliquer_infraction_mineure_ne_descend_pas_sous_zero(app):
    eleve = _make_eleve()
    eleve.points_vie_scolaire = 1
    db.session.commit()
    user = _make_user("surveillant")
    type_infraction = TypeInfractionMineure(libelle="Grosse infraction", points_deduits=5)
    db.session.add(type_infraction)
    db.session.commit()

    appliquer_infraction_mineure(eleve, type_infraction, user)

    assert eleve.points_vie_scolaire == 0


def test_cloturer_cycle_fige_les_points_et_reinitialise(app):
    eleve = _make_eleve()
    eleve.points_vie_scolaire = 14
    user = _make_user("surveillant")
    cycle = CycleDiscipline(date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 15))
    db.session.add(cycle)
    db.session.commit()

    cloturer_cycle(cycle)

    assert cycle.est_cloture
    assert len(cycle.snapshots) == 1
    assert cycle.snapshots[0].points_finaux == 14
    assert eleve.points_vie_scolaire == 20


def test_cloturer_cycle_deja_cloture_leve_erreur(app):
    cycle = CycleDiscipline(
        date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 15)
    )
    db.session.add(cycle)
    db.session.commit()
    cloturer_cycle(cycle)

    import pytest

    with pytest.raises(ValueError):
        cloturer_cycle(cycle)
