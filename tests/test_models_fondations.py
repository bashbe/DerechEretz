from datetime import date

from app.extensions import db
from app.models import AnneeScolaire, Classe, ContactParent, Eleve, Matiere, Notice, Trimestre, User


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
