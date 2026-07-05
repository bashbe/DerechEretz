from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AnneeScolaire,
    Classe,
    ContactParent,
    Controle,
    Eleve,
    IncidentMajeur,
    InfractionMineure,
    Matiere,
    Note,
    Notice,
    Presence,
    Trimestre,
    TypeInfractionMineure,
    User,
)


def test_annee_scolaire_creation(app):
    annee = AnneeScolaire(
        libelle="2025-2026",
        date_debut=date(2025, 9, 1),
        date_fin=date(2026, 6, 30),
        active=True,
    )
    db.session.add(annee)
    db.session.commit()

    recuperee = db.session.get(AnneeScolaire, annee.id)
    assert recuperee.libelle == "2025-2026"
    assert recuperee.date_debut == date(2025, 9, 1)
    assert recuperee.date_fin == date(2026, 6, 30)
    assert recuperee.active is True


def test_annee_scolaire_active_par_defaut_false(app):
    annee = AnneeScolaire(
        libelle="2024-2025", date_debut=date(2024, 9, 1), date_fin=date(2025, 6, 30)
    )
    db.session.add(annee)
    db.session.commit()

    assert annee.active is False


def test_trimestre_lie_a_annee_scolaire(app):
    annee = AnneeScolaire(
        libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30)
    )
    db.session.add(annee)
    db.session.commit()

    trimestre = Trimestre(
        annee=annee, code="T1", date_debut=date(2025, 9, 1), date_fin=date(2025, 12, 19)
    )
    db.session.add(trimestre)
    db.session.commit()

    assert trimestre.annee_id == annee.id
    assert annee.trimestres == [trimestre]


def test_contact_parent_plusieurs_par_eleve(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    db.session.add_all([classe, eleve])
    db.session.commit()

    pere = ContactParent(eleve=eleve, lien="pere", nom="Paul Dupont", telephone="0600000000")
    mere = ContactParent(eleve=eleve, lien="mere", nom="Marie Dupont", email="marie@mail.fr")
    db.session.add_all([pere, mere])
    db.session.commit()

    assert len(eleve.contacts_parents) == 2
    assert {c.lien for c in eleve.contacts_parents} == {"pere", "mere"}


def test_contact_parent_supprime_avec_eleve(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    db.session.add_all([classe, eleve])
    db.session.commit()
    contact = ContactParent(eleve=eleve, lien="pere", nom="Paul Dupont")
    db.session.add(contact)
    db.session.commit()
    contact_id = contact.id

    db.session.delete(eleve)
    db.session.commit()

    assert db.session.get(ContactParent, contact_id) is None


def test_notice_sans_matiere(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    user = User(nom="Surveillant", email="surv@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, user])
    db.session.commit()

    notice = Notice(
        eleve=eleve, titre="Oubli de carnet", contenu="A répétition.", saisi_par=user
    )
    db.session.add(notice)
    db.session.commit()

    assert notice.matiere_id is None
    assert eleve.notices == [notice]


def test_notice_avec_matiere(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Prof", email="prof@ecole.test", role="professeur")
    user.set_password("password123")
    db.session.add_all([classe, eleve, matiere, user])
    db.session.commit()

    notice = Notice(
        eleve=eleve,
        titre="Matériel oublié",
        contenu="Calculatrice",
        matiere=matiere,
        saisi_par=user,
    )
    db.session.add(notice)
    db.session.commit()

    assert notice.matiere_id == matiere.id


def test_controle_regroupe_les_notes(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve1 = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    eleve2 = Eleve(nom="Martin", prenom="Alice", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Prof", email="prof2@ecole.test", role="professeur")
    user.set_password("password123")
    db.session.add_all([classe, eleve1, eleve2, matiere, user])
    db.session.commit()

    controle = Controle(
        matiere=matiere,
        classe=classe,
        intitule="Contrôle chapitre 1",
        date=date(2026, 1, 10),
        coefficient=2.0,
        saisi_par=user,
    )
    db.session.add(controle)
    db.session.commit()

    note1 = Note(eleve=eleve1, controle=controle, valeur=15, saisi_par=user)
    note2 = Note(eleve=eleve2, controle=controle, valeur=9, saisi_par=user)
    db.session.add_all([note1, note2])
    db.session.commit()

    assert controle.trimestre_id is None
    assert {n.id for n in controle.notes} == {note1.id, note2.id}
    assert note1.controle.intitule == "Contrôle chapitre 1"


def test_note_existante_sans_controle_reste_valide(app):
    """Les Note créées à l'ancienne façon (sans controle_id) continuent de fonctionner."""
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Prof", email="prof3@ecole.test", role="professeur")
    user.set_password("password123")
    db.session.add_all([classe, eleve, matiere, user])
    db.session.commit()

    note = Note(
        eleve=eleve, matiere=matiere, valeur=12, trimestre="T1", saisi_par=user
    )
    db.session.add(note)
    db.session.commit()

    assert note.controle_id is None


def test_presence_creation(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    user = User(nom="Surveillant", email="surv2@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, user])
    db.session.commit()

    presence = Presence(
        eleve=eleve,
        date=date(2026, 1, 12),
        statut="retard",
        heure_arrivee=time(8, 15),
        saisi_par=user,
    )
    db.session.add(presence)
    db.session.commit()

    assert eleve.presences == [presence]
    assert presence.justifie is False


def test_presence_unique_par_eleve_et_date(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    user = User(nom="Surveillant", email="surv3@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, user])
    db.session.commit()

    db.session.add(
        Presence(eleve=eleve, date=date(2026, 1, 12), statut="present", saisi_par=user)
    )
    db.session.commit()

    db.session.add(
        Presence(eleve=eleve, date=date(2026, 1, 12), statut="absent", saisi_par=user)
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_infraction_mineure_matiere_optionnelle(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    type_infraction = TypeInfractionMineure(libelle="Bavardage", points_deduits=1)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Surveillant", email="surv4@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, type_infraction, matiere, user])
    db.session.commit()

    sans_matiere = InfractionMineure(
        eleve=eleve, type_infraction=type_infraction, saisi_par=user
    )
    avec_matiere = InfractionMineure(
        eleve=eleve, type_infraction=type_infraction, matiere=matiere, saisi_par=user
    )
    db.session.add_all([sans_matiere, avec_matiere])
    db.session.commit()

    assert sans_matiere.matiere_id is None
    assert avec_matiere.matiere_id == matiere.id


def test_incident_majeur_matiere_optionnelle(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Surveillant", email="surv5@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, matiere, user])
    db.session.commit()

    incident = IncidentMajeur(
        eleve=eleve,
        description="Conflit en classe",
        gravite="moyenne",
        matiere=matiere,
        saisi_par=user,
    )
    db.session.add(incident)
    db.session.commit()

    assert incident.matiere_id == matiere.id
