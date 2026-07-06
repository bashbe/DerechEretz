from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from app.decorators import role_required
from app.extensions import db
from app.models import Classe, CycleDiscipline, RapportGenere

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
    cycles = CycleDiscipline.query.order_by(CycleDiscipline.date_debut.desc()).all()
    return render_template("rapports/liste.html", rapports=rapports, classes=classes, cycles=cycles)


@rapports_bp.route("/rapports/notes", methods=["POST"])
def rapport_notes():
    from app.reports.generation import generer_rapport_notes

    classe_id = request.form.get("classe_id", type=int)
    trimestre = request.form.get("trimestre", "T1")
    classe = db.session.get(Classe, classe_id) or abort(404)
    generer_rapport_notes(classe, trimestre)
    flash("Rapport de notes généré.", "success")
    return redirect(url_for("rapports.liste"))


@rapports_bp.route("/rapports/absences", methods=["POST"])
def rapport_absences():
    from app.reports.generation import generer_rapport_absences

    classe_id = request.form.get("classe_id", type=int)
    classe = db.session.get(Classe, classe_id) or abort(404)
    generer_rapport_absences(classe)
    flash("Rapport d'absences généré.", "success")
    return redirect(url_for("rapports.liste"))


@rapports_bp.route("/rapports/discipline", methods=["POST"])
def rapport_discipline():
    from app.reports.generation import generer_rapport_discipline

    cycle_id = request.form.get("cycle_id", type=int)
    cycle = db.session.get(CycleDiscipline, cycle_id) or abort(404)
    if not cycle.est_cloture:
        flash("Ce cycle n'est pas encore clôturé.", "warning")
        return redirect(url_for("rapports.liste"))
    generer_rapport_discipline(cycle)
    flash("Rapport de discipline généré.", "success")
    return redirect(url_for("rapports.liste"))


@rapports_bp.route("/rapports/<int:rapport_id>/telecharger/<format>")
def telecharger(rapport_id, format):
    rapport = db.session.get(RapportGenere, rapport_id) or abort(404)
    chemin = rapport.fichier_pdf if format == "pdf" else rapport.fichier_excel
    if not chemin:
        abort(404)
    return send_file(chemin, as_attachment=True)
