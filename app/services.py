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


def calculer_moyenne_matiere_periode(eleve_id, matiere_id, date_debut, date_fin):
    """Moyenne d'une matière pour un élève sur un intervalle de dates.

    Gère les deux styles de notes :
    - ancienne façon : Note.matiere_id + Note.date (controle_id IS NULL)
    - nouvelle façon : Note.controle_id → Controle.matiere_id + Controle.date
      (poids = Controle.coefficient)
    """
    from app.models import Controle

    notes_directes = Note.query.filter(
        Note.eleve_id == eleve_id,
        Note.matiere_id == matiere_id,
        Note.controle_id.is_(None),
        Note.date >= date_debut,
        Note.date <= date_fin,
    ).all()

    notes_controle = (
        Note.query
        .join(Controle, Note.controle_id == Controle.id)
        .filter(
            Note.eleve_id == eleve_id,
            Controle.matiere_id == matiere_id,
            Controle.date >= date_debut,
            Controle.date <= date_fin,
        )
        .all()
    )

    total_pondere = sum(n.valeur for n in notes_directes)
    total_coeff = float(len(notes_directes))

    for n in notes_controle:
        coeff = n.controle.coefficient
        total_pondere += n.valeur * coeff
        total_coeff += coeff

    if total_coeff == 0:
        return None
    return round(total_pondere / total_coeff, 2)


def calculer_moyenne_generale_periode(eleve_id, matieres, date_debut, date_fin):
    """Moyenne générale pondérée par coefficient de matière, sur un intervalle de dates.

    Prend une liste de Matiere explicite pour permettre le filtrage par rôle.
    """
    total_pondere = 0.0
    total_coeff = 0.0
    for matiere in matieres:
        moy = calculer_moyenne_matiere_periode(eleve_id, matiere.id, date_debut, date_fin)
        if moy is None:
            continue
        total_pondere += moy * matiere.coefficient
        total_coeff += matiere.coefficient
    if total_coeff == 0:
        return None
    return round(total_pondere / total_coeff, 2)
