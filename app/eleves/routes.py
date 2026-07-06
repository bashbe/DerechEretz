import calendar
from datetime import date

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from app import evenements
from app.extensions import db
from app.models import Classe, Eleve, Matiere
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

    # Feed d'activités unifié (le filtrage par rôle est centralisé dans evenements.feed)
    activites = evenements.feed(date_debut, date_fin, eleve_id=eleve_id, user=current_user)

    return render_template(
        "eleves/fiche.html",
        eleve=eleve,
        preset=preset,
        date_debut=date_debut,
        date_fin=date_fin,
        matieres=matieres,
        moyennes=moyennes,
        moyenne_generale=moyenne_generale,
        activites=activites,
        types_creables=types_evenements_creables(current_user),
    )
