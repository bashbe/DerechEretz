import calendar
import os
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from app import evenements
from app.decorators import role_required
from app.extensions import db
from app.models import AnneeScolaire, Classe, CycleDiscipline, Eleve, RapportGenere, Trimestre

rapports_bp = Blueprint("rapports", __name__)


@rapports_bp.before_request
@login_required
@role_required("directeur", "surveillant")
def guard():
    pass


@rapports_bp.route("/rapports")
def liste():
    rapports = RapportGenere.query.order_by(RapportGenere.date_creation.desc()).all()
    classes = Classe.query.order_by(Classe.nom).all()
    eleves = Eleve.query.join(Classe).order_by(Classe.nom, Eleve.nom).all()
    annees = AnneeScolaire.query.order_by(AnneeScolaire.date_debut.desc()).all()
    trimestres = Trimestre.query.order_by(Trimestre.date_debut).all()
    cycles = CycleDiscipline.query.order_by(CycleDiscipline.date_debut.desc()).all()
    return render_template(
        "rapports/liste.html",
        rapports=rapports,
        classes=classes,
        eleves=eleves,
        annees=annees,
        trimestres=trimestres,
        cycles=cycles,
        types_evenements=evenements.TYPES_EVENEMENTS,
        libelles_types=evenements.LIBELLES,
    )


def _parser_date(valeur):
    try:
        return date.fromisoformat(valeur) if valeur else None
    except ValueError:
        return None


def _resoudre_portee():
    """Retourne la liste d'élèves visée par le formulaire (école / classe(s) /
    élève(s) spécifiques), ou None si la sélection est invalide/vide."""
    portee = request.form.get("portee", "ecole")
    if portee == "ecole":
        return Eleve.query.join(Classe).order_by(Classe.nom, Eleve.nom).all()
    if portee == "classe":
        classe_ids = request.form.getlist("classe_ids", type=int)
        if not classe_ids:
            return None
        return (
            Eleve.query.join(Classe)
            .filter(Eleve.classe_id.in_(classe_ids))
            .order_by(Classe.nom, Eleve.nom)
            .all()
        )
    # "eleves"
    eleve_ids = request.form.getlist("eleve_ids", type=int)
    if not eleve_ids:
        return None
    return (
        Eleve.query.join(Classe)
        .filter(Eleve.id.in_(eleve_ids))
        .order_by(Classe.nom, Eleve.nom)
        .all()
    )


def _resoudre_periode_rapport():
    """Retourne (date_debut, date_fin, libelle) depuis le type de période choisi
    (mois / trimestre / année / cycle / plage personnalisée), ou None si invalide."""
    periode_type = request.form.get("periode_type", "mois")

    if periode_type == "personnalise":
        date_debut = _parser_date(request.form.get("date_debut"))
        date_fin = _parser_date(request.form.get("date_fin"))
        if not date_debut or not date_fin or date_debut > date_fin:
            return None
        return date_debut, date_fin, "Période personnalisée"

    if periode_type == "annee":
        annee = db.session.get(AnneeScolaire, request.form.get("annee_id", type=int) or 0)
        if not annee:
            return None
        return annee.date_debut, annee.date_fin, f"Année scolaire {annee.libelle}"

    if periode_type == "trimestre":
        trimestre = db.session.get(Trimestre, request.form.get("trimestre_id", type=int) or 0)
        if not trimestre:
            return None
        return trimestre.date_debut, trimestre.date_fin, f"Trimestre {trimestre.code}"

    if periode_type == "cycle":
        cycle = db.session.get(CycleDiscipline, request.form.get("cycle_id", type=int) or 0)
        if not cycle:
            return None
        return cycle.date_debut, cycle.date_fin, "Cycle de discipline"

    # "mois"
    mois_valeur = request.form.get("mois", "")
    try:
        annee_int, mois_int = (int(x) for x in mois_valeur.split("-"))
        date_debut = date(annee_int, mois_int, 1)
        date_fin = date(annee_int, mois_int, calendar.monthrange(annee_int, mois_int)[1])
    except (ValueError, AttributeError):
        return None
    return date_debut, date_fin, f"Mois {mois_int:02d}/{annee_int}"


@rapports_bp.route("/rapports/generer", methods=["POST"])
def generer():
    from app.reports.generation import generer_rapport_evenements

    eleves = _resoudre_portee()
    if not eleves:
        flash("Sélectionnez au moins un élève, une ou plusieurs classes, ou l'école entière.", "danger")
        return redirect(url_for("rapports.liste"))

    resolu = _resoudre_periode_rapport()
    if not resolu:
        flash("Période invalide ou introuvable.", "danger")
        return redirect(url_for("rapports.liste"))
    date_debut, date_fin, libelle_periode = resolu

    types_choisis = [t for t in request.form.getlist("types") if t in evenements.TYPES_EVENEMENTS]
    if not types_choisis:
        types_choisis = list(evenements.TYPES_EVENEMENTS)

    generer_rapport_evenements(eleves, date_debut, date_fin, types_choisis, libelle_periode)
    flash(f"Rapport généré pour {len(eleves)} élève(s).", "success")
    return redirect(url_for("rapports.liste"))


@rapports_bp.route("/rapports/<int:rapport_id>/telecharger/<format>")
def telecharger(rapport_id, format):
    rapport = db.session.get(RapportGenere, rapport_id) or abort(404)
    chemin = rapport.fichier_pdf if format == "pdf" else rapport.fichier_excel
    if not chemin:
        abort(404)
    return send_file(chemin, as_attachment=True)


@rapports_bp.route("/rapports/<int:rapport_id>/supprimer", methods=["POST"])
def supprimer(rapport_id):
    rapport = db.session.get(RapportGenere, rapport_id) or abort(404)
    for chemin in (rapport.fichier_pdf, rapport.fichier_excel):
        if chemin and os.path.exists(chemin):
            os.remove(chemin)
    db.session.delete(rapport)
    db.session.commit()
    flash("Rapport supprimé.", "success")
    return redirect(url_for("rapports.liste"))
