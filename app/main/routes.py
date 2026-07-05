from datetime import date

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Absence, CycleDiscipline, Eleve
from app.services import matieres_autorisees_pour_professeur

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    if current_user.is_directeur():
        return redirect(url_for("main.dashboard_directeur"))
    if current_user.is_professeur():
        return redirect(url_for("main.dashboard_professeur"))
    if current_user.is_surveillant():
        return redirect(url_for("main.dashboard_surveillant"))
    return redirect(url_for("auth.login"))


@main_bp.route("/directeur")
@login_required
def dashboard_directeur():
    nb_eleves = Eleve.query.count()
    absences_non_justifiees = Absence.query.filter_by(statut="injustifie").count()
    cycle_actif = CycleDiscipline.query.filter_by(date_cloture=None).order_by(
        CycleDiscipline.date_debut.desc()
    ).first()
    return render_template(
        "main/dashboard_directeur.html",
        nb_eleves=nb_eleves,
        absences_non_justifiees=absences_non_justifiees,
        cycle_actif=cycle_actif,
    )


@main_bp.route("/professeur")
@login_required
def dashboard_professeur():
    affectations = matieres_autorisees_pour_professeur(current_user)
    return render_template("main/dashboard_professeur.html", affectations=affectations)


@main_bp.route("/surveillant")
@login_required
def dashboard_surveillant():
    absences_aujourdhui = Absence.query.filter_by(date=date.today()).count()
    return render_template(
        "main/dashboard_surveillant.html", absences_aujourdhui=absences_aujourdhui
    )
