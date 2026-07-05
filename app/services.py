"""Logique métier centrale : moyennes, points de vie scolaire, cycles de discipline."""

from datetime import datetime

from app.extensions import db
from app.models import (
    AffectationProf,
    CycleDiscipline,
    Eleve,
    Matiere,
    Note,
    SnapshotPointsEleve,
)

POINTS_DEPART = 20


def calculer_moyenne_matiere(eleve_id, matiere_id, trimestre):
    notes = Note.query.filter_by(
        eleve_id=eleve_id, matiere_id=matiere_id, trimestre=trimestre
    ).all()
    if not notes:
        return None
    return round(sum(n.valeur for n in notes) / len(notes), 2)


def calculer_moyenne_generale(eleve_id, trimestre):
    matieres = Matiere.query.all()
    total_pondere = 0.0
    total_coeff = 0.0
    for matiere in matieres:
        moyenne = calculer_moyenne_matiere(eleve_id, matiere.id, trimestre)
        if moyenne is None:
            continue
        total_pondere += moyenne * matiere.coefficient
        total_coeff += matiere.coefficient
    if total_coeff == 0:
        return None
    return round(total_pondere / total_coeff, 2)


def appliquer_infraction_mineure(eleve, type_infraction, saisi_par):
    from app.models import InfractionMineure

    cycle_actif = CycleDiscipline.query.filter_by(date_cloture=None).first()

    infraction = InfractionMineure(
        eleve=eleve, type_infraction=type_infraction, saisi_par=saisi_par, cycle=cycle_actif
    )
    db.session.add(infraction)
    eleve.points_vie_scolaire = max(0, eleve.points_vie_scolaire - type_infraction.points_deduits)
    db.session.commit()
    return infraction


def cloturer_cycle(cycle: CycleDiscipline):
    if cycle.est_cloture:
        raise ValueError("Ce cycle de discipline est déjà clôturé.")

    for eleve in Eleve.query.all():
        snapshot = SnapshotPointsEleve(
            cycle=cycle, eleve=eleve, points_finaux=eleve.points_vie_scolaire
        )
        db.session.add(snapshot)
        eleve.points_vie_scolaire = POINTS_DEPART

    cycle.date_cloture = datetime.utcnow()
    db.session.commit()
    return cycle


def matieres_autorisees_pour_professeur(user):
    """Retourne les (matiere, classe) qu'un professeur peut saisir."""
    affectations = AffectationProf.query.filter_by(professeur_id=user.id).all()
    return [(a.matiere, a.classe) for a in affectations]
