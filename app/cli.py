import sys

import click

from app.extensions import db
from app.models import User

# Sur Windows, la console utilise par défaut l'encodage cp1252 (PowerShell,
# cmd.exe), qui ne sait pas encoder les symboles (✓, ⚠...) utilisés dans les
# messages de ces commandes. On force stdout/stderr en UTF-8 pour que
# les commandes CLI ne plantent pas sur `click.echo` après avoir déjà
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
            click.echo("La base est vierge. Créez un compte directeur :")
            click.echo("  flask seed-directeur <email> <motdepasse>")

    @app.cli.command("seed-demo")
    @click.option(
        "--reset",
        is_flag=True,
        help="Efface et régénère entièrement la base de démo, même si elle est déjà peuplée.",
    )
    def seed_demo(reset):
        """Peuple la base de démonstration (3 classes de 20 élèves fictifs).

        N'affecte jamais la base réelle : ces données ne sont visibles que
        sur le sous-domaine de démo (config DEMO_SUBDOMAIN, "demo" par défaut).
        """
        from app.demo import DEMO_DIRECTEUR_EMAIL, DEMO_PASSWORD, seed_demo_data

        cree = seed_demo_data(app, reset=reset)
        if not cree:
            click.echo("La base de démo est déjà peuplée (utilisez --reset pour la régénérer).")
            return
        click.echo("✓ Base de démo peuplée : 3 classes, 60 élèves fictifs.")
        click.echo(f"  Compte directeur démo : {DEMO_DIRECTEUR_EMAIL} / {DEMO_PASSWORD}")
        click.echo(
            f"  (accès automatique, sans connexion, via le sous-domaine "
            f"{app.config.get('DEMO_SUBDOMAIN', 'demo')}.<votre-domaine>)"
        )
