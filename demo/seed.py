"""Initialisation de la base de données avec le compte directeur uniquement.

Commande : flask seed-demo
Crée :
  - Compte directeur : bmerets@gmail.com (mot de passe : 12345678)
  - Année scolaire 2025-2026 (vide — prête pour saisir les données)
  - Matières, classes et barème des infractions (structure de base)

Réinitialiser la base avant de relancer ce script (PowerShell) :
    Remove-Item ecole.db -Force
    flask db upgrade
    flask seed-demo

(bash : `rm -f ecole.db && flask db upgrade && flask seed-demo`)
"""

from datetime import date, timedelta


def run_seed(app):
    from app.extensions import db
    from app.models import (
        AnneeScolaire,
        Classe,
        Matiere,
        Trimestre,
        TypeInfractionMineure,
        User,
    )

    with app.app_context():
        if User.query.filter_by(email="bmerets@gmail.com").first():
            return "⚠  Compte directeur déjà présent (bmerets@gmail.com existe)."

        # Créer le compte directeur
        directeur = User(nom="Benoit Mérets", email="bmerets@gmail.com", role="directeur", actif=True)
        directeur.set_password("12345678")
        db.session.add(directeur)
        db.session.flush()

        # Matières de base
        matieres_def = [
            ("Mathématiques", 4.0),
            ("Français",       4.0),
            ("Histoire-Géo",   3.0),
            ("Sciences",       3.0),
            ("Sport",          2.0),
        ]
        for nom, coef in matieres_def:
            db.session.add(Matiere(nom=nom, coefficient=coef))
        db.session.flush()

        # Classes vides
        for nom_classe in ["6ème A", "5ème B", "4ème C"]:
            db.session.add(Classe(nom=nom_classe, annee_scolaire="2025-2026"))
        db.session.flush()

        # Année scolaire
        annee = AnneeScolaire(
            libelle="2025-2026",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 27),
            active=True,
        )
        db.session.add(annee)
        db.session.flush()

        # Trimestres
        db.session.add_all([
            Trimestre(annee=annee, code="T1", date_debut=date(2025, 9, 1),  date_fin=date(2025, 12, 19)),
            Trimestre(annee=annee, code="T2", date_debut=date(2026, 1, 5),  date_fin=date(2026, 3, 28)),
            Trimestre(annee=annee, code="T3", date_debut=date(2026, 4, 6),  date_fin=date(2026, 6, 27)),
        ])
        db.session.flush()

        # Barème des infractions mineures
        bareme = [
            ("Bavardage",         1),
            ("Travail non fait",  1),
            ("Retard répété",     2),
            ("Téléphone sorti",   2),
            ("Insolence",         3),
        ]
        for libelle, pts in bareme:
            db.session.add(TypeInfractionMineure(libelle=libelle, points_deduits=pts, actif=True))

        db.session.commit()

        return "✓ Base initialisée. Compte directeur : bmerets@gmail.com / 12345678"
