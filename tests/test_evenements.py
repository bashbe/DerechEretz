from datetime import date, time

import pytest

from app import evenements
from app.extensions import db
from app.models import (
    AffectationProf,
    Classe,
    CycleDiscipline,
    Eleve,
    IncidentMajeur,
    InfractionMineure,
    Matiere,
    Note,
    Notice,
    Presence,
    TypeInfractionMineure,
    User,
)


def _make_user(role, email=None):
    user = User(nom=role.capitalize(), email=email or f"{role}@ecole.test", role=role)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def _base(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = _make_user("directeur")
    db.session.add_all([classe, eleve, matiere])
    db.session.commit()
    return classe, eleve, matiere, user


def test_feed_fusionne_et_trie_tous_les_types(app):
    classe, eleve, matiere, user = _base(app)
    type_inf = TypeInfractionMineure(libelle="Bavardage", points_deduits=1)
    db.session.add(type_inf)
    db.session.commit()

    db.session.add_all([
        Note(eleve=eleve, matiere=matiere, valeur=15, date=date(2026, 1, 10), saisi_par=user),
        Notice(eleve=eleve, titre="Bravo", contenu="Progrès.", date=date(2026, 1, 12), saisi_par=user),
        InfractionMineure(eleve=eleve, type_infraction=type_inf, date=date(2026, 1, 14), saisi_par=user),
        IncidentMajeur(eleve=eleve, description="Bagarre", gravite="moyenne", date=date(2026, 1, 16), saisi_par=user),
        Presence(eleve=eleve, date=date(2026, 1, 18), statut="absent", saisi_par=user),
    ])
    db.session.commit()

    vues = evenements.feed(date(2026, 1, 1), date(2026, 1, 31), eleve_id=eleve.id)

    assert [v.type for v in vues] == [
        "presence", "infraction_majeure", "infraction_mineure", "observation", "note",
    ]
    assert [v.date for v in vues] == sorted([v.date for v in vues], reverse=True)


def test_feed_masque_les_presents_par_defaut(app):
    classe, eleve, matiere, user = _base(app)
    db.session.add_all([
        Presence(eleve=eleve, date=date(2026, 1, 5), statut="present", saisi_par=user),
        Presence(eleve=eleve, date=date(2026, 1, 6), statut="retard",
                 heure_arrivee=time(8, 15), saisi_par=user),
    ])
    db.session.commit()

    vues = evenements.feed(date(2026, 1, 1), date(2026, 1, 31), eleve_id=eleve.id)
    assert len(vues) == 1
    assert vues[0].libelle_type == "Retard"

    toutes = evenements.feed(
        date(2026, 1, 1), date(2026, 1, 31), eleve_id=eleve.id, inclure_presents=True
    )
    assert len(toutes) == 2


def test_feed_filtre_par_periode_et_type(app):
    classe, eleve, matiere, user = _base(app)
    db.session.add_all([
        Notice(eleve=eleve, titre="Dedans", contenu="x", date=date(2026, 2, 10), saisi_par=user),
        Notice(eleve=eleve, titre="Dehors", contenu="x", date=date(2026, 3, 10), saisi_par=user),
        Note(eleve=eleve, matiere=matiere, valeur=12, date=date(2026, 2, 15), saisi_par=user),
    ])
    db.session.commit()

    vues = evenements.feed(date(2026, 2, 1), date(2026, 2, 28), eleve_id=eleve.id)
    assert {v.type for v in vues} == {"observation", "note"}
    assert all(v.date.month == 2 for v in vues)

    seulement_notes = evenements.feed(
        date(2026, 2, 1), date(2026, 2, 28), eleve_id=eleve.id, types=["note"]
    )
    assert [v.type for v in seulement_notes] == ["note"]


def test_feed_professeur_restreint_a_ses_matieres_et_sans_presences(app):
    classe, eleve, maths, directeur = _base(app)
    sport = Matiere(nom="Sport", coefficient=1)
    prof = _make_user("professeur")
    db.session.add(sport)
    db.session.commit()
    db.session.add(AffectationProf(professeur_id=prof.id, matiere_id=maths.id, classe_id=classe.id))
    db.session.add_all([
        Note(eleve=eleve, matiere=maths, valeur=15, date=date(2026, 1, 10), saisi_par=prof),
        Note(eleve=eleve, matiere=sport, valeur=9, date=date(2026, 1, 11), saisi_par=directeur),
        Notice(eleve=eleve, titre="Taguée maths", contenu="x", matiere=maths,
               date=date(2026, 1, 12), saisi_par=directeur),
        Notice(eleve=eleve, titre="Sans matière", contenu="x", date=date(2026, 1, 13),
               saisi_par=directeur),
        Presence(eleve=eleve, date=date(2026, 1, 14), statut="absent", saisi_par=directeur),
    ])
    db.session.commit()

    vues = evenements.feed(date(2026, 1, 1), date(2026, 1, 31), eleve_id=eleve.id, user=prof)

    assert {(v.type, v.resume) for v in vues} == {
        ("note", "15/20"),
        ("observation", "Taguée maths"),
    }


def test_creer_infraction_mineure_multi_eleves_decremente_les_points(app):
    classe, eleve1, matiere, user = _base(app)
    eleve2 = Eleve(nom="Martin", prenom="Alice", classe=classe)
    type_inf = TypeInfractionMineure(libelle="Téléphone", points_deduits=2)
    cycle = CycleDiscipline(date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 31))
    db.session.add_all([eleve2, type_inf, cycle])
    db.session.commit()

    crees = evenements.creer(
        "infraction_mineure",
        [eleve1, eleve2],
        user,
        {"type_infraction_id": type_inf.id, "date": date(2026, 1, 10)},
    )

    assert len(crees) == 2
    assert eleve1.points_vie_scolaire == 18
    assert eleve2.points_vie_scolaire == 18
    assert all(v.obj.cycle_id == cycle.id for v in crees)


def test_creer_presence_upsert_par_eleve_et_jour(app):
    classe, eleve, matiere, user = _base(app)

    evenements.creer("presence", [eleve], user,
                     {"statut": "absent", "date": date(2026, 1, 10)})
    evenements.creer("presence", [eleve], user,
                     {"statut": "retard", "heure": time(8, 30), "date": date(2026, 1, 10)})

    lignes = Presence.query.filter_by(eleve_id=eleve.id).all()
    assert len(lignes) == 1
    assert lignes[0].statut == "retard"
    assert lignes[0].heure_arrivee == time(8, 30)


def test_creer_note_exige_matiere_et_valeur_valide(app):
    classe, eleve, matiere, user = _base(app)

    with pytest.raises(ValueError):
        evenements.creer("note", [eleve], user, {"valeur": 25, "matiere_id": matiere.id})
    with pytest.raises(ValueError):
        evenements.creer("note", [eleve], user, {"valeur": 12, "matiere_id": None})

    crees = evenements.creer("note", [eleve], user, {"valeur": 12.5, "matiere_id": matiere.id})
    assert crees[0].obj.valeur == 12.5


def test_supprimer_infraction_recalcule_les_points(app):
    classe, eleve, matiere, user = _base(app)
    type_inf = TypeInfractionMineure(libelle="Insolence", points_deduits=3)
    cycle = CycleDiscipline(date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 31))
    db.session.add_all([type_inf, cycle])
    db.session.commit()

    (vue,) = evenements.creer(
        "infraction_mineure", [eleve], user,
        {"type_infraction_id": type_inf.id, "date": date(2026, 1, 10)},
    )
    assert eleve.points_vie_scolaire == 17

    assert evenements.supprimer("infraction_mineure", vue.id) is True
    assert eleve.points_vie_scolaire == 20


def test_charger_et_modifier_observation(app):
    classe, eleve, matiere, user = _base(app)
    (vue,) = evenements.creer(
        "observation", [eleve], user, {"titre": "Avant", "contenu": "Texte."}
    )

    evenements.modifier("observation", vue.id, {"titre": "Après"})

    recharge = evenements.charger("observation", vue.id)
    assert recharge.obj.titre == "Après"
    assert evenements.charger("type_inconnu", vue.id) is None
    assert evenements.charger("observation", 99999) is None
