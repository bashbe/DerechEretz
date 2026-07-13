"""Mode démonstration : sous-domaine servant des données 100 % fictives.

Quand une requête arrive avec un nom d'hôte dont le premier label correspond
à `DEMO_SUBDOMAIN` (ex. ``demo.monecole.fr``), `g.is_demo` est levé pour
toute la durée de la requête. `app.extensions._DemoAwareSession` redirige
alors automatiquement toutes les requêtes SQLAlchemy vers la base "demo"
(`SQLALCHEMY_BINDS["demo"]`), une base physiquement distincte de la base de
production. Aucune route n'a besoin d'être modifiée : le même code et les
mêmes modèles servent simplement une autre base selon le nom d'hôte.

Les visiteurs du sous-domaine de démo sont connectés automatiquement avec le
compte directeur fictif créé par `flask seed-demo`, pour permettre une
visite sans identifiants. Les données de démo se peuplent avec
`flask seed-demo` (voir app/cli.py) et n'affectent jamais la base réelle.
"""

import random
import string
from datetime import date, timedelta

from flask import g, request
from flask_login import current_user, login_user

from app.extensions import db
from app.models import (
    AffectationProf,
    Absence,
    AnneeScolaire,
    Classe,
    Controle,
    ContactParent,
    CycleDiscipline,
    Eleve,
    IncidentMajeur,
    InfractionMineure,
    Matiere,
    Note,
    Notice,
    Presence,
    Trimestre,
    TypeInfractionMineure,
    User,
)

DEMO_DIRECTEUR_EMAIL = "directeur@demo.ecole"
DEMO_PASSWORD = "demo1234"

CLASSES_INFO = [("6ème A", 11), ("5ème A", 12), ("4ème A", 13)]
ELEVES_PAR_CLASSE = 20

PRENOMS_F = [
    "Léa", "Emma", "Chloé", "Manon", "Camille", "Inès", "Sarah", "Jade",
    "Yasmine", "Zoé", "Nour", "Lina", "Sofia", "Rebecca", "Anna", "Maya",
    "Rachel", "Noa", "Eva", "Lucie",
]
PRENOMS_M = [
    "Lucas", "Gabriel", "Noah", "David", "Samuel", "Ethan", "Adam", "Raphaël",
    "Simon", "Nathan", "Yossef", "Eliott", "Mathis", "Jules", "Ilan", "Élie",
    "Tom", "Aaron", "Daniel", "Léo",
]
NOMS_FAMILLE = [
    "Cohen", "Lévy", "Amar", "Bensimon", "Attias", "Azoulay", "Benhamou",
    "Cohen-Zana", "Dahan", "Elbaz", "Fitoussi", "Guez", "Hadad", "Illouz",
    "Journo", "Knafo", "Lasry", "Malka", "Nahmias", "Ohana", "Partouche",
    "Ruimy", "Sabbah", "Tapiro", "Uzan", "Vaknin", "Zerbib", "Halimi",
]
RUES = [
    "rue de la République", "avenue Victor Hugo", "rue des Écoles",
    "allée des Tilleuls", "rue Jean Jaurès", "boulevard de la Gare",
    "rue du Commerce", "impasse des Lilas", "avenue de la Paix",
]
VILLES = [
    ("75011", "Paris"), ("69003", "Lyon"), ("13006", "Marseille"),
    ("31000", "Toulouse"), ("06000", "Nice"), ("67000", "Strasbourg"),
]

MATIERES = [
    ("Mathématiques", 1.0),
    ("Français", 1.0),
    ("Histoire-Géographie", 0.5),
    ("Anglais", 1.0),
    ("Sciences", 1.0),
    ("EPS", 0.5),
]

TYPES_INFRACTIONS = [
    ("Bavardage", 3),
    ("Retard en cours", 2),
    ("Oubli de matériel", 2),
    ("Insolence", 5),
    ("Chewing-gum en classe", 1),
]


def _demo_host_prefix(app):
    return app.config.get("DEMO_SUBDOMAIN", "demo").lower()


def _est_sous_domaine_demo(app, host):
    premier_label = host.split(":")[0].split(".")[0].lower()
    return premier_label == _demo_host_prefix(app)


def register_demo(app):
    """Enregistre la détection du sous-domaine de démo et l'auto-connexion."""

    @app.before_request
    def _detecter_demo_et_connecter():
        g.is_demo = app.config.get("FORCE_DEMO_MODE", False) or _est_sous_domaine_demo(
            app, request.host
        )
        if g.is_demo and not current_user.is_authenticated:
            demo_user = User.query.filter_by(email=DEMO_DIRECTEUR_EMAIL).first()
            if demo_user is not None:
                login_user(demo_user)


def _slug(texte):
    autorises = string.ascii_lowercase + string.digits
    sans_accents = (
        texte.lower()
        .replace("é", "e").replace("è", "e").replace("ê", "e")
        .replace("à", "a").replace("ç", "c").replace("î", "i")
    )
    return "".join(c if c in autorises else "" for c in sans_accents)


def _adresse_aleatoire(rng):
    code_postal, ville = rng.choice(VILLES)
    return f"{rng.randint(1, 150)} {rng.choice(RUES)}, {code_postal} {ville}"


def _telephone_aleatoire(rng):
    return "06" + "".join(str(rng.randint(0, 9)) for _ in range(8))


def _cree_utilisateurs_et_matieres(rng):
    directeur = User(nom="Sarah Lévy", email=DEMO_DIRECTEUR_EMAIL, role="directeur", actif=True)
    directeur.set_password(DEMO_PASSWORD)
    surveillant = User(nom="David Amar", email="surveillant@demo.ecole", role="surveillant", actif=True)
    surveillant.set_password(DEMO_PASSWORD)
    db.session.add_all([directeur, surveillant])

    professeurs_par_matiere = {}
    for nom_matiere, coeff in MATIERES:
        matiere = Matiere(nom=nom_matiere, coefficient=coeff)
        db.session.add(matiere)
        prof = User(
            nom=f"Prof. {rng.choice(NOMS_FAMILLE)} ({nom_matiere})",
            email=f"prof.{_slug(nom_matiere)}@demo.ecole",
            role="professeur",
            actif=True,
        )
        prof.set_password(DEMO_PASSWORD)
        db.session.add(prof)
        professeurs_par_matiere[nom_matiere] = (prof, matiere)

    db.session.flush()
    return directeur, surveillant, professeurs_par_matiere


def _cree_classes_et_eleves(rng, today):
    classes = []
    for nom_classe, age in CLASSES_INFO:
        classe = Classe(nom=nom_classe, annee_scolaire=f"{today.year - 1}-{today.year}")
        db.session.add(classe)
        db.session.flush()

        for _ in range(ELEVES_PAR_CLASSE):
            prenom = rng.choice(PRENOMS_F if rng.random() < 0.5 else PRENOMS_M)
            nom = rng.choice(NOMS_FAMILLE)
            naissance = date(today.year - age, rng.randint(1, 12), rng.randint(1, 28))
            eleve = Eleve(
                nom=nom,
                prenom=prenom,
                classe=classe,
                points_vie_scolaire=20,
                date_naissance=naissance,
                adresse=_adresse_aleatoire(rng),
            )
            db.session.add(eleve)
            db.session.flush()
            lien = rng.choice(["pere", "mere"])
            db.session.add(
                ContactParent(
                    eleve=eleve,
                    lien=lien,
                    nom=f"{'M.' if lien == 'pere' else 'Mme'} {nom}",
                    telephone=_telephone_aleatoire(rng),
                    email=f"{_slug(prenom)}.{_slug(nom)}.parent@example-demo.fr",
                )
            )
        classes.append(classe)
    return classes


def _cree_annee_et_trimestres(today):
    date_debut = today - timedelta(days=120)
    date_fin = today + timedelta(days=245)
    annee = AnneeScolaire(
        libelle=f"{date_debut.year}-{date_fin.year}",
        date_debut=date_debut,
        date_fin=date_fin,
        active=True,
    )
    db.session.add(annee)
    db.session.flush()

    segment = (date_fin - date_debut).days // 3
    bornes = [
        date_debut,
        date_debut + timedelta(days=segment),
        date_debut + timedelta(days=2 * segment),
        date_fin,
    ]
    trimestres = []
    for i, code in enumerate(("T1", "T2", "T3")):
        trimestre = Trimestre(
            annee=annee, code=code, date_debut=bornes[i], date_fin=bornes[i + 1]
        )
        db.session.add(trimestre)
        trimestres.append(trimestre)
    db.session.flush()
    return annee, trimestres


def _affecte_professeurs(professeurs_par_matiere, classes):
    for prof, matiere in professeurs_par_matiere.values():
        for classe in classes:
            db.session.add(
                AffectationProf(professeur=prof, matiere=matiere, classe=classe)
            )


def _cree_controles_et_notes(rng, professeurs_par_matiere, classes, trimestre_courant):
    for classe in classes:
        for prof, matiere in professeurs_par_matiere.values():
            for numero in (1, 2):
                controle_date = trimestre_courant.date_debut + timedelta(
                    days=rng.randint(1, max(1, (trimestre_courant.date_fin - trimestre_courant.date_debut).days - 1))
                )
                controle = Controle(
                    matiere=matiere,
                    classe=classe,
                    intitule=f"Devoir {numero}",
                    date=controle_date,
                    coefficient=1.0,
                    trimestre=trimestre_courant,
                    saisi_par=prof,
                )
                db.session.add(controle)
                db.session.flush()
                for eleve in classe.eleves:
                    valeur = max(4.0, min(20.0, round(rng.gauss(13, 3) * 2) / 2))
                    db.session.add(
                        Note(
                            eleve=eleve,
                            controle=controle,
                            valeur=valeur,
                            date=controle_date,
                            saisi_par=prof,
                        )
                    )


def _cree_vie_scolaire(rng, classes, cycle, types_infraction, surveillant, professeurs_par_matiere, today):
    professeur_quelconque = next(iter(professeurs_par_matiere.values()))[0]

    for classe in classes:
        for eleve in classe.eleves:
            if rng.random() < 0.35:
                nb_infractions = rng.randint(1, 2)
                total_points = 0
                for _ in range(nb_infractions):
                    type_infraction = rng.choice(types_infraction)
                    db.session.add(
                        InfractionMineure(
                            eleve=eleve,
                            type_infraction=type_infraction,
                            saisi_par=surveillant,
                            cycle=cycle,
                            date=today - timedelta(days=rng.randint(0, 9)),
                        )
                    )
                    total_points += type_infraction.points_deduits
                eleve.points_vie_scolaire = max(0, 20 - total_points)

            if rng.random() < 0.08:
                db.session.add(
                    IncidentMajeur(
                        eleve=eleve,
                        description=rng.choice([
                            "Conflit avec un camarade de classe.",
                            "Perturbation répétée du cours.",
                            "Sortie du cours sans autorisation.",
                        ]),
                        gravite=rng.choice(["mineure_grave", "moyenne", "majeure"]),
                        sanction="Convocation des parents.",
                        date=today - timedelta(days=rng.randint(0, 20)),
                        saisi_par=surveillant,
                    )
                )

            for jour_offset in range(7, -1, -1):
                jour = today - timedelta(days=jour_offset)
                if jour.weekday() >= 5:
                    continue
                statut = "present"
                justifie = False
                motif = None
                if rng.random() < 0.06:
                    statut = "absent"
                    justifie = rng.random() < 0.5
                    motif = "Rendez-vous médical" if justifie else None
                elif rng.random() < 0.05:
                    statut = "retard"
                db.session.add(
                    Presence(
                        eleve=eleve,
                        date=jour,
                        statut=statut,
                        justifie=justifie,
                        motif=motif,
                        saisi_par=surveillant,
                    )
                )
                if statut in ("absent", "retard"):
                    db.session.add(
                        Absence(
                            eleve=eleve,
                            date=jour,
                            type="absence" if statut == "absent" else "retard",
                            statut="justifie" if justifie else "injustifie",
                            motif=motif,
                            saisi_par=surveillant,
                        )
                    )

            if rng.random() < 0.1:
                db.session.add(
                    Notice(
                        eleve=eleve,
                        titre="Observation",
                        contenu="Bonne participation en classe ce trimestre.",
                        saisi_par=professeur_quelconque,
                        date=today - timedelta(days=rng.randint(0, 15)),
                    )
                )


def seed_demo_data(app, reset=False):
    """Crée le schéma et peuple la base de démo avec 3 classes de 20 élèves.

    Idempotent : si la base de démo contient déjà des utilisateurs, ne fait
    rien sauf si `reset=True` (auquel cas tout est effacé et régénéré).
    Retourne True si des données ont été (re)générées, False si déjà peuplée.
    """
    with app.app_context():
        g.is_demo = True
        demo_engine = db.engines["demo"]

        if reset:
            db.metadata.drop_all(bind=demo_engine)
        db.metadata.create_all(bind=demo_engine)

        if not reset and User.query.first() is not None:
            return False

        rng = random.Random(42)
        today = date.today()

        directeur, surveillant, professeurs_par_matiere = _cree_utilisateurs_et_matieres(rng)
        classes = _cree_classes_et_eleves(rng, today)
        _affecte_professeurs(professeurs_par_matiere, classes)
        annee, trimestres = _cree_annee_et_trimestres(today)

        trimestre_courant = next(
            (t for t in trimestres if t.date_debut <= today <= t.date_fin), trimestres[-1]
        )

        cycle = CycleDiscipline(
            date_debut=today - timedelta(days=10), date_fin=today + timedelta(days=5)
        )
        db.session.add(cycle)

        types_infraction = []
        for libelle, points in TYPES_INFRACTIONS:
            type_infraction = TypeInfractionMineure(
                libelle=libelle, points_deduits=points, actif=True
            )
            db.session.add(type_infraction)
            types_infraction.append(type_infraction)

        db.session.flush()

        _cree_controles_et_notes(rng, professeurs_par_matiere, classes, trimestre_courant)
        _cree_vie_scolaire(
            rng, classes, cycle, types_infraction, surveillant, professeurs_par_matiere, today
        )

        db.session.commit()
        return True
