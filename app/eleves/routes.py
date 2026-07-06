import calendar
from datetime import date, timedelta

from flask import Blueprint, abort, flash, render_template, request
from flask_login import current_user, login_required

from app import evenements
from app.extensions import db
from app.models import Classe, CycleDiscipline, Eleve, Matiere, SnapshotPointsEleve
from app.periodes import resoudre_periode
from app.permissions import types_evenements_creables
from app.services import calculer_moyenne_generale_periode, calculer_moyenne_matiere_periode

eleves_bp = Blueprint("eleves", __name__)


@eleves_bp.before_request
@login_required
def guard():
    pass


@eleves_bp.route("/eleves")
def liste():
    classes = Classe.query.order_by(Classe.nom).all()
    return render_template("eleves/liste.html", classes=classes)


@eleves_bp.route("/eleves/<int:eleve_id>")
def fiche(eleve_id):
    eleve = db.session.get(Eleve, eleve_id) or abort(404)

    preset = request.args.get("periode", "mois")
    reference_arg = request.args.get("reference")
    try:
        reference = date.fromisoformat(reference_arg) if reference_arg else None
    except ValueError:
        reference = None
    try:
        date_debut, date_fin = resoudre_periode(preset, reference)
    except ValueError as erreur:
        flash(str(erreur), "warning")
        preset = "mois"
        today = date.today()
        date_debut = today.replace(day=1)
        date_fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    reference_precedent = date_debut - timedelta(days=1)
    reference_suivant = date_fin + timedelta(days=1)

    # Points de discipline : uniquement pertinents en vue « cycle ». Un cycle
    # clôturé a remis le compteur à zéro (cf. services.cloturer_cycle) — son
    # solde final est donc lu depuis l'instantané plutôt que depuis le live.
    cycle = None
    points_cycle = None
    if preset == "cycle":
        cycle = CycleDiscipline.query.filter_by(
            date_debut=date_debut, date_fin=date_fin
        ).first()
        if cycle and cycle.est_cloture:
            snapshot = SnapshotPointsEleve.query.filter_by(
                cycle_id=cycle.id, eleve_id=eleve_id
            ).first()
            points_cycle = snapshot.points_finaux if snapshot else None
        else:
            points_cycle = eleve.points_vie_scolaire

    # Pour un professeur : restreindre aux matières qu'il enseigne dans cette classe
    if current_user.is_professeur():
        matieres_autorisees_ids = {
            mid
            for mid, cid in current_user.matieres_classes_autorisees()
            if cid == eleve.classe_id
        }
    else:
        matieres_autorisees_ids = None  # pas de restriction

    toutes_matieres = Matiere.query.order_by(Matiere.nom).all()
    matieres = (
        toutes_matieres
        if matieres_autorisees_ids is None
        else [m for m in toutes_matieres if m.id in matieres_autorisees_ids]
    )

    moyennes = {
        m: calculer_moyenne_matiere_periode(eleve_id, m.id, date_debut, date_fin)
        for m in matieres
    }
    moyenne_generale = calculer_moyenne_generale_periode(eleve_id, matieres, date_debut, date_fin)

    # Feed d'activités unifié (le filtrage par rôle est centralisé dans evenements.feed)
    activites = evenements.feed(date_debut, date_fin, eleve_id=eleve_id, user=current_user)

    return render_template(
        "eleves/fiche.html",
        eleve=eleve,
        preset=preset,
        date_debut=date_debut,
        date_fin=date_fin,
        reference_precedent=reference_precedent,
        reference_suivant=reference_suivant,
        cycle=cycle,
        points_cycle=points_cycle,
        matieres=matieres,
        moyennes=moyennes,
        moyenne_generale=moyenne_generale,
        activites=activites,
        types_creables=types_evenements_creables(current_user),
    )
