from flask import Blueprint, redirect, url_for
from flask_login import current_user, login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    if current_user.is_directeur():
        return redirect(url_for("eleves.liste"))
    if current_user.is_professeur():
        return redirect(url_for("vie_scolaire.index"))
    if current_user.is_surveillant():
        return redirect(url_for("vie_scolaire.index"))
    return redirect(url_for("auth.login"))
