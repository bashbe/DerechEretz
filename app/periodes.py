"""Résolution des vues par période (cycle / mois / trimestre / année) partagée
par tous les onglets de liste (présences, notes, vie scolaire, rapports)."""

import calendar
from datetime import date

from app.models import AnneeScolaire, CycleDiscipline, Trimestre

PRESETS_PERIODE = ("cycle", "mois", "trimestre", "annee")


def resoudre_periode(preset, reference=None):
    reference = reference or date.today()

    if preset == "cycle":
        cycle = (
            CycleDiscipline.query.filter_by(date_cloture=None)
            .order_by(CycleDiscipline.date_debut.desc())
            .first()
        )
        if not cycle:
            raise ValueError("Aucun cycle de discipline actif.")
        return cycle.date_debut, cycle.date_fin

    if preset == "mois":
        premier_jour = reference.replace(day=1)
        dernier_jour_numero = calendar.monthrange(reference.year, reference.month)[1]
        dernier_jour = reference.replace(day=dernier_jour_numero)
        return premier_jour, dernier_jour

    if preset == "trimestre":
        trimestre = Trimestre.query.filter(
            Trimestre.date_debut <= reference, Trimestre.date_fin >= reference
        ).first()
        if not trimestre:
            raise ValueError("Aucun trimestre ne couvre cette date.")
        return trimestre.date_debut, trimestre.date_fin

    if preset == "annee":
        annee = AnneeScolaire.query.filter_by(active=True).first()
        if not annee:
            raise ValueError("Aucune année scolaire active.")
        return annee.date_debut, annee.date_fin

    raise ValueError(f"Période inconnue : {preset}")
