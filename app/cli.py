import sys

import click

from app.extensions import db
from app.models import User

# Sur Windows, la console utilise par défaut l'encodage cp1252 (PowerShell,
# cmd.exe), qui ne sait pas encoder les symboles (✓, ⚠...) utilisés dans les
# messages de ces commandes. On force stdout/stderr en UTF-8 pour que
# `flask seed-demo` etc. ne plantent pas sur `click.echo` après avoir déjà
# committé leurs données.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def register_cli(app):
    @app.cli.command("seed-directeur")
    @click.argument("email")
    @click.argument("password")
    @click.option("--nom", default="Directeur")
    def seed_directeur(email, password, nom):
        """Crée le premier compte directeur (email + mot de passe)."""
        if User.query.filter_by(email=email.lower().strip()).first():
            click.echo("Un compte avec cet email existe déjà.")
            return
        user = User(nom=nom, email=email.lower().strip(), role="directeur", actif=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Compte directeur créé : {email}")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Charge 3 classes × 20 élèves avec un historique complet (notes, présences,
        infractions, incidents, notices, contacts parents).

        Comptes créés (mot de passe demo123) :
          demo@ecole.fr         — directeur
          prof.maths@demo.fr    — professeur (Mathématiques, Sciences, Sport)
          prof.lettres@demo.fr  — professeur (Français, Histoire-Géo)
          surveillant@demo.fr   — surveillant
        """
        from demo.seed import run_seed

        msg = run_seed(app)
        click.echo(msg)

    @app.cli.command("reset-db")
    @click.option(
        "--confirm",
        is_flag=True,
        help="Confirmer la suppression des données sans demander",
    )
    def reset_db(confirm):
        """Réinitialise la base de données (supprime toutes les données)."""
        if not confirm:
            click.echo("⚠️  Cela va SUPPRIMER toutes les données de la base.")
            if not click.confirm("Êtes-vous sûr ?"):
                click.echo("Annulation.")
                return

        import os
        from app.extensions import db

        db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)
            click.echo(f"✓ Base de données supprimée : {db_path}")
        else:
            click.echo("Base de données inexistante, création d'une nouvelle...")

        with app.app_context():
            from flask_migrate import upgrade

            upgrade()
            click.echo("✓ Migrations appliquées")
            click.echo("")
            click.echo("La base est vierge. Choisissez :")
            click.echo("  flask seed-directeur <email> <motdepasse>")
            click.echo("  flask seed-demo")
