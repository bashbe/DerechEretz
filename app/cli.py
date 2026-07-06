import click

from app.extensions import db
from app.models import User


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
