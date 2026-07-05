from datetime import date

import pytest

from app.extensions import db
from app.models import AnneeScolaire, CycleDiscipline, Trimestre
from app.periodes import resoudre_periode


def test_resoudre_periode_cycle_utilise_le_cycle_ouvert(app):
    cycle_ferme = CycleDiscipline(
        date_debut=date(2025, 12, 1),
        date_fin=date(2025, 12, 15),
        date_cloture=date(2025, 12, 16),
    )
    cycle_ouvert = CycleDiscipline(date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 15))
    db.session.add_all([cycle_ferme, cycle_ouvert])
    db.session.commit()

    debut, fin = resoudre_periode("cycle")

    assert (debut, fin) == (date(2026, 1, 1), date(2026, 1, 15))


def test_resoudre_periode_cycle_sans_cycle_ouvert_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("cycle")


def test_resoudre_periode_mois_utilise_le_mois_de_reference(app):
    debut, fin = resoudre_periode("mois", reference=date(2026, 2, 10))

    assert (debut, fin) == (date(2026, 2, 1), date(2026, 2, 28))


def test_resoudre_periode_trimestre_trouve_le_trimestre_couvrant(app):
    annee = AnneeScolaire(
        libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30)
    )
    db.session.add(annee)
    db.session.commit()
    t1 = Trimestre(annee=annee, code="T1", date_debut=date(2025, 9, 1), date_fin=date(2025, 12, 19))
    t2 = Trimestre(annee=annee, code="T2", date_debut=date(2026, 1, 5), date_fin=date(2026, 3, 20))
    db.session.add_all([t1, t2])
    db.session.commit()

    debut, fin = resoudre_periode("trimestre", reference=date(2026, 2, 1))

    assert (debut, fin) == (date(2026, 1, 5), date(2026, 3, 20))


def test_resoudre_periode_trimestre_sans_couverture_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("trimestre", reference=date(2026, 2, 1))


def test_resoudre_periode_annee_utilise_lannee_active(app):
    inactive = AnneeScolaire(
        libelle="2024-2025", date_debut=date(2024, 9, 1), date_fin=date(2025, 6, 30)
    )
    active = AnneeScolaire(
        libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True
    )
    db.session.add_all([inactive, active])
    db.session.commit()

    debut, fin = resoudre_periode("annee")

    assert (debut, fin) == (date(2025, 9, 1), date(2026, 6, 30))


def test_resoudre_periode_annee_sans_annee_active_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("annee")


def test_resoudre_periode_preset_inconnu_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("semaine")
