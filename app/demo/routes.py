from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_user, logout_user

from app.models import User

demo_bp = Blueprint("demo", __name__)

# Comptes démo et leur description
COMPTES_DEMO = [
    {
        "role_key": "directeur",
        "email": "demo@ecole.fr",
        "nom": "Diane Directeur",
        "role": "directeur",
        "description": "Accès complet : élèves, notes, présences, vie scolaire, rapports et administration.",
        "couleur": "primary",
        "icone": "🏫",
    },
    {
        "role_key": "professeur_maths",
        "email": "prof.maths@demo.fr",
        "nom": "Pierre Mathieu",
        "role": "professeur",
        "description": "Professeur de Mathématiques, Sciences et Sport. Accès aux notes de ses matières.",
        "couleur": "success",
        "icone": "📐",
    },
    {
        "role_key": "professeur_lettres",
        "email": "prof.lettres@demo.fr",
        "nom": "Laurence Lelièvre",
        "role": "professeur",
        "description": "Professeure de Français et Histoire-Géo. Accès aux notes de ses matières.",
        "couleur": "success",
        "icone": "📖",
    },
    {
        "role_key": "surveillant",
        "email": "surveillant@demo.fr",
        "nom": "Samuel Souchard",
        "role": "surveillant",
        "description": "Accès aux présences, à la vie scolaire et aux rapports. Pas d'accès admin.",
        "couleur": "warning",
        "icone": "👁",
    },
]

EMAILS_DEMO = {c["email"] for c in COMPTES_DEMO}


@demo_bp.route("/demo")
def landing():
    """Page d'accueil de la démo — choisir un compte."""
    return render_template("demo/landing.html", comptes=COMPTES_DEMO)


@demo_bp.route("/demo/as/<role_key>")
def entrer_comme(role_key):
    """Connexion automatique en tant qu'un compte démo."""
    compte = next((c for c in COMPTES_DEMO if c["role_key"] == role_key), None)
    if compte is None:
        flash("Compte démo inconnu.", "danger")
        return redirect(url_for("demo.landing"))

    user = User.query.filter_by(email=compte["email"]).first()
    if user is None:
        flash(
            "Les données démo ne sont pas chargées. Lancez d'abord : flask seed-demo",
            "warning",
        )
        return redirect(url_for("demo.landing"))

    login_user(user)
    return redirect(url_for("eleves.liste"))


@demo_bp.route("/demo/quitter")
def quitter():
    """Déconnexion et retour à la page démo."""
    logout_user()
    return redirect(url_for("demo.landing"))
