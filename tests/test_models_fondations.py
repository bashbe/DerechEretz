from datetime import date

from app.extensions import db
from app.models import AnneeScolaire


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
