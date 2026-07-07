from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import evenements
from app.models import Classe, Eleve, InfractionMineure, User

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    if current_user.is_directeur() or current_user.is_surveillant():
        return redirect(url_for("main.tableau_de_bord"))
    if current_user.is_professeur():
        return redirect(url_for("vie_scolaire.index"))
    return redirect(url_for("auth.login"))


@main_bp.route("/tableau-de-bord")
@login_required
def tableau_de_bord():
    aujourdhui = date.today()
    il_y_a_7_jours = aujourdhui - timedelta(days=7)
    il_y_a_30_jours = aujourdhui - timedelta(days=30)

    total_eleves = Eleve.query.count()
    total_classes = Classe.query.count()
    infractions_recentes = InfractionMineure.query.filter(
        InfractionMineure.date >= il_y_a_7_jours
    ).count()
    comptes_actifs = User.query.filter_by(actif=True).count()

    activite_recente = evenements.feed(
        il_y_a_30_jours, aujourdhui, user=current_user
    )[:8]

    return render_template(
        "main/dashboard.html",
        total_eleves=total_eleves,
        total_classes=total_classes,
        infractions_recentes=infractions_recentes,
        comptes_actifs=comptes_actifs,
        activite_recente=activite_recente,
    )
