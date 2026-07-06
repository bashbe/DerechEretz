import calendar
from datetime import date

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Classe,
    Eleve,
    IncidentMajeur,
    InfractionMineure,
    Matiere,
    Notice,
    Presence,
)
from app.periodes import resoudre_periode
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
    try:
        date_debut, date_fin = resoudre_periode(preset)
    except ValueError:
        preset = "mois"
        today = date.today()
        date_debut = today.replace(day=1)
        date_fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])

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

    # Présences uniquement pour directeur et surveillant
    if matieres_autorisees_ids is None:
        presences = (
            Presence.query.filter(
                Presence.eleve_id == eleve_id,
                Presence.date >= date_debut,
                Presence.date <= date_fin,
            )
            .order_by(Presence.date.desc())
            .all()
        )
    else:
        presences = []

    # Vie scolaire : filtrer par matière pour les professeurs
    q_infractions = InfractionMineure.query.filter(
        InfractionMineure.eleve_id == eleve_id,
        InfractionMineure.date >= date_debut,
        InfractionMineure.date <= date_fin,
    )
    q_incidents = IncidentMajeur.query.filter(
        IncidentMajeur.eleve_id == eleve_id,
        IncidentMajeur.date >= date_debut,
        IncidentMajeur.date <= date_fin,
    )
    q_notices = Notice.query.filter(
        Notice.eleve_id == eleve_id,
        Notice.date >= date_debut,
        Notice.date <= date_fin,
    )

    if matieres_autorisees_ids is not None:
        q_infractions = q_infractions.filter(
            InfractionMineure.matiere_id.in_(matieres_autorisees_ids)
        )
        q_incidents = q_incidents.filter(
            IncidentMajeur.matiere_id.in_(matieres_autorisees_ids)
        )
        q_notices = q_notices.filter(
            Notice.matiere_id.in_(matieres_autorisees_ids)
        )

    infractions = q_infractions.order_by(InfractionMineure.date.desc()).all()
    incidents = q_incidents.order_by(IncidentMajeur.date.desc()).all()
    notices = q_notices.order_by(Notice.date.desc()).all()

    return render_template(
        "eleves/fiche.html",
        eleve=eleve,
        preset=preset,
        date_debut=date_debut,
        date_fin=date_fin,
        matieres=matieres,
        moyennes=moyennes,
        moyenne_generale=moyenne_generale,
        presences=presences,
        infractions=infractions,
        incidents=incidents,
        notices=notices,
        matieres_autorisees_ids=matieres_autorisees_ids,
    )
