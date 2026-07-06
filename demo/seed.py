"""Jeu de données de démonstration : 3 classes × 20 élèves + historique complet.

Commande : flask seed-demo
Comptes créés (mot de passe : demo123) :
  demo@ecole.fr          — directeur
  prof.maths@demo.fr     — professeur (Mathématiques, Sciences, Sport)
  prof.lettres@demo.fr   — professeur (Français, Histoire-Géo)
  surveillant@demo.fr    — surveillant
"""

import random
from datetime import date, datetime, time, timedelta

SEED = 42

NOMS = [
    "MARTIN", "BERNARD", "DUPONT", "THOMAS", "ROBERT",
    "RICHARD", "PETIT", "DURAND", "LEROY", "MOREAU",
    "SIMON", "LAURENT", "LEFEBVRE", "MICHEL", "GARCIA",
    "DAVID", "BERTRAND", "ROUX", "VINCENT", "FOURNIER",
    "BLANC", "GUERIN", "MULLER", "HENRY", "ROUSSEAU",
    "GIRARD", "ANDRE", "MERCIER", "DUPUIS", "LAMBERT",
    "BONNET", "FRANCOIS", "MARTINEZ", "LEGRAND", "GARNIER",
    "FAURE", "ROUSSEL", "BLANCHARD", "COLIN", "MORIN",
    "RENARD", "GIRAUD", "CLEMENT", "MOREL", "CHEVALIER",
    "FONTAINE", "PERRIN", "ROBIN", "MASSON", "PICARD",
    "GILLES", "BARBIER", "ARNAUD", "BESSON", "GAUTHIER",
    "LEGER", "VIDAL", "CARON", "AUBERT", "MAILLARD",
]

PRENOMS = [
    "Lucas", "Emma", "Noah", "Léa", "Louis",
    "Chloé", "Gabriel", "Manon", "Raphaël", "Inès",
    "Hugo", "Camille", "Tom", "Océane", "Nathan",
    "Jade", "Théo", "Zoé", "Ethan", "Alice",
    "Mathis", "Lucie", "Arthur", "Clara", "Liam",
    "Sarah", "Antoine", "Eva", "Maxime", "Lisa",
    "Enzo", "Anaïs", "Baptiste", "Élise", "Romain",
    "Laura", "Alexis", "Julie", "Pierre", "Marion",
    "Tristan", "Amélia", "Victor", "Charlotte", "Axel",
    "Pauline", "Nicolas", "Sophie", "Julien", "Émilie",
    "Dylan", "Margaux", "Dorian", "Clémentine", "Florian",
    "Roxane", "Clément", "Noémie", "Fiona", "Yanis",
]

NOMS_PARENTS = [
    "MARTIN", "DUPONT", "BERNARD", "SIMON", "ROBERT",
    "MICHEL", "LEROY", "PETIT", "DURAND", "MOREAU",
]
PRENOMS_PARENTS = ["Jean", "Marie", "Paul", "Anne", "Pierre", "Sylvie", "Luc", "Isabelle"]


def run_seed(app):
    from app.extensions import db
    from app.models import (
        AffectationProf,
        AnneeScolaire,
        Classe,
        ContactParent,
        CycleDiscipline,
        Eleve,
        IncidentMajeur,
        InfractionMineure,
        Matiere,
        Note,
        Notice,
        Presence,
        RapportGenere,
        SnapshotPointsEleve,
        Trimestre,
        TypeInfractionMineure,
        User,
    )

    rng = random.Random(SEED)

    with app.app_context():
        if User.query.filter_by(email="demo@ecole.fr").first():
            return "⚠  Données démo déjà présentes (demo@ecole.fr existe)."

        # ------------------------------------------------------------------ #
        # Comptes
        # ------------------------------------------------------------------ #
        directeur = User(nom="Diane Directeur", email="demo@ecole.fr", role="directeur", actif=True)
        directeur.set_password("demo123")

        prof_maths = User(nom="Pierre Mathieu", email="prof.maths@demo.fr", role="professeur", actif=True)
        prof_maths.set_password("demo123")

        prof_lettres = User(nom="Laurence Lelièvre", email="prof.lettres@demo.fr", role="professeur", actif=True)
        prof_lettres.set_password("demo123")

        surveillant = User(nom="Samuel Souchard", email="surveillant@demo.fr", role="surveillant", actif=True)
        surveillant.set_password("demo123")

        db.session.add_all([directeur, prof_maths, prof_lettres, surveillant])
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Matières
        # ------------------------------------------------------------------ #
        matieres_def = [
            ("Mathématiques", 4.0),
            ("Français",       4.0),
            ("Histoire-Géo",   3.0),
            ("Sciences",       3.0),
            ("Sport",          2.0),
        ]
        matieres = {}
        for nom, coef in matieres_def:
            m = Matiere(nom=nom, coefficient=coef)
            db.session.add(m)
            matieres[nom] = m
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Classes
        # ------------------------------------------------------------------ #
        classes = []
        for nom_classe in ("6ème A", "5ème B", "4ème C"):
            c = Classe(nom=nom_classe, annee_scolaire="2025-2026")
            db.session.add(c)
            classes.append(c)
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Affectations
        # ------------------------------------------------------------------ #
        for classe in classes:
            for mat_nom in ("Mathématiques", "Sciences", "Sport"):
                db.session.add(AffectationProf(
                    professeur_id=prof_maths.id,
                    matiere_id=matieres[mat_nom].id,
                    classe_id=classe.id,
                ))
            for mat_nom in ("Français", "Histoire-Géo"):
                db.session.add(AffectationProf(
                    professeur_id=prof_lettres.id,
                    matiere_id=matieres[mat_nom].id,
                    classe_id=classe.id,
                ))
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Barème infractions mineures
        # ------------------------------------------------------------------ #
        bareme = [
            ("Bavardage",         1),
            ("Travail non fait",  1),
            ("Retard répété",     2),
            ("Téléphone sorti",   2),
            ("Insolence",         3),
        ]
        types_infraction = []
        for libelle, pts in bareme:
            t = TypeInfractionMineure(libelle=libelle, points_deduits=pts, actif=True)
            db.session.add(t)
            types_infraction.append(t)
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Année scolaire + trimestres
        # ------------------------------------------------------------------ #
        annee = AnneeScolaire(
            libelle="2025-2026",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 27),
            active=True,
        )
        db.session.add(annee)
        db.session.flush()

        t1 = Trimestre(annee=annee, code="T1", date_debut=date(2025, 9, 1),  date_fin=date(2025, 12, 19))
        t2 = Trimestre(annee=annee, code="T2", date_debut=date(2026, 1, 5),  date_fin=date(2026, 3, 28))
        t3 = Trimestre(annee=annee, code="T3", date_debut=date(2026, 4, 6),  date_fin=date(2026, 6, 27))
        db.session.add_all([t1, t2, t3])
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Cycles de discipline
        # ------------------------------------------------------------------ #
        cycle1 = CycleDiscipline(date_debut=date(2025, 9, 1),  date_fin=date(2025, 12, 19))
        cycle2 = CycleDiscipline(date_debut=date(2026, 1, 5),  date_fin=date(2026, 6, 27))
        db.session.add_all([cycle1, cycle2])
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Élèves — 20 par classe, noms/prénoms distincts
        # ------------------------------------------------------------------ #
        noms_pool    = list(NOMS)
        prenoms_pool = list(PRENOMS)
        rng.shuffle(noms_pool)
        rng.shuffle(prenoms_pool)

        all_eleves = []
        for i, classe in enumerate(classes):
            for j in range(20):
                idx = i * 20 + j
                eleve = Eleve(
                    nom=noms_pool[idx % len(noms_pool)],
                    prenom=prenoms_pool[idx % len(prenoms_pool)],
                    classe=classe,
                    points_vie_scolaire=20,
                )
                db.session.add(eleve)
                all_eleves.append(eleve)
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Profils de niveau (stable par élève)
        # ------------------------------------------------------------------ #
        # 0=en difficulté (4-9), 1=passable (9-13), 2=bien (13-17), 3=excellent (16-20)
        profiles = [rng.choices([0, 1, 2, 3], weights=[12, 33, 38, 17])[0] for _ in all_eleves]
        ranges = {0: (4.0, 9.0), 1: (9.0, 13.0), 2: (12.5, 17.0), 3: (15.5, 20.0)}

        def note_aleatoire(profile):
            lo, hi = ranges[profile]
            v = rng.uniform(lo, hi) + rng.uniform(-1.0, 1.0)
            return round(max(0.0, min(20.0, v)) * 2) / 2  # demi-point

        # ------------------------------------------------------------------ #
        # Notes — 3 trimestres, 2-3 notes par matière
        # ------------------------------------------------------------------ #
        tri_info = [
            ("T1", date(2025, 9, 10),  date(2025, 12, 12)),
            ("T2", date(2026, 1, 12),  date(2026, 3, 25)),
            ("T3", date(2026, 4, 10),  date(2026, 6, 20)),
        ]
        prof_par_mat = {
            "Mathématiques": prof_maths,
            "Sciences":       prof_maths,
            "Sport":          prof_maths,
            "Français":       prof_lettres,
            "Histoire-Géo":   prof_lettres,
        }

        for idx, eleve in enumerate(all_eleves):
            profile = profiles[idx]
            for tri_code, tri_start, tri_end in tri_info:
                jours_disponibles = (tri_end - tri_start).days
                for mat_nom, matiere in matieres.items():
                    nb_notes = 1 if mat_nom == "Sport" else rng.randint(2, 3)
                    for _ in range(nb_notes):
                        note_date = tri_start + timedelta(days=rng.randint(0, jours_disponibles))
                        db.session.add(Note(
                            eleve=eleve,
                            matiere_id=matiere.id,
                            valeur=note_aleatoire(profile),
                            trimestre=tri_code,
                            date=note_date,
                            saisi_par=prof_par_mat[mat_nom],
                        ))
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Présences — quelques absences et retards sur T1 et T2
        # ------------------------------------------------------------------ #
        # Générer la liste des jours d'école (lun-ven) sur T1+T2
        jours_t1_t2 = []
        cur = date(2025, 9, 1)
        while cur <= date(2026, 3, 28):
            if cur.weekday() < 5:
                jours_t1_t2.append(cur)
            cur += timedelta(days=1)

        for eleve in all_eleves:
            nb = rng.randint(3, 8)
            for j in rng.sample(jours_t1_t2, nb):
                statut = rng.choices(["absent", "retard"], weights=[60, 40])[0]
                heure_arr = None
                if statut == "retard":
                    heure_arr = time(rng.randint(8, 9), rng.choice([5, 10, 15, 20, 30, 45]))
                justifie = rng.random() < 0.35
                db.session.add(Presence(
                    eleve=eleve,
                    date=j,
                    statut=statut,
                    heure_arrivee=heure_arr,
                    justifie=justifie,
                    motif="Certificat médical" if justifie and statut == "absent" else None,
                    saisi_par=surveillant,
                ))
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Infractions mineures — cycle 1 (cloturé) + cycle 2 (actif)
        # ------------------------------------------------------------------ #
        def _infractions_sur_cycle(nb, cycle, date_debut_cycle, jours_cycle):
            for _ in range(nb):
                eleve = rng.choice(all_eleves)
                ti    = rng.choice(types_infraction)
                mat   = rng.choice([None, None, None, matieres["Mathématiques"],
                                    matieres["Français"], matieres["Sciences"]])
                inf_date = date_debut_cycle + timedelta(days=rng.randint(0, jours_cycle))
                db.session.add(InfractionMineure(
                    eleve=eleve,
                    type_infraction=ti,
                    date=inf_date,
                    saisi_par=surveillant,
                    cycle=cycle,
                    matiere=mat,
                ))
                eleve.points_vie_scolaire = max(0, eleve.points_vie_scolaire - ti.points_deduits)

        _infractions_sur_cycle(28, cycle1, date(2025, 9, 1),  109)
        db.session.flush()

        # Clôture cycle 1 : snapshot + reset
        for eleve in all_eleves:
            db.session.add(SnapshotPointsEleve(
                cycle=cycle1, eleve=eleve, points_finaux=eleve.points_vie_scolaire
            ))
            eleve.points_vie_scolaire = 20
        cycle1.date_cloture = datetime(2025, 12, 20, 17, 0, 0)
        db.session.flush()

        _infractions_sur_cycle(22, cycle2, date(2026, 1, 5), 172)
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Incidents majeurs (rares — 6 au total)
        # ------------------------------------------------------------------ #
        incidents_def = [
            ("Bagarre dans la cour de récréation",  "moyenne",       "Retenue 2 heures + convocation des parents"),
            ("Vol d'un téléphone portable",          "majeure",       "Conseil de discipline — exclusion 3 jours"),
            ("Dégradation volontaire de matériel",   "mineure_grave", "Réparation du matériel + excuse écrite"),
            ("Menaces répétées envers un camarade",  "moyenne",       "Convocation parents + suivi par le CPE"),
            ("Fraude lors d'un contrôle de maths",   "mineure_grave", "Note annulée — avertissement écrit"),
            ("Propos injurieux envers un professeur","majeure",       "Exclusion temporaire 2 jours"),
        ]
        for desc, gravite, sanction in incidents_def:
            eleve = rng.choice(all_eleves)
            mat = matieres.get("Mathématiques") if "maths" in desc.lower() else None
            inc_date = date(2025, 9, 1) + timedelta(days=rng.randint(0, 300))
            db.session.add(IncidentMajeur(
                eleve=eleve,
                description=desc,
                gravite=gravite,
                sanction=sanction,
                date=inc_date,
                saisi_par=surveillant,
                matiere=mat,
            ))

        # ------------------------------------------------------------------ #
        # Notices (8 au total)
        # ------------------------------------------------------------------ #
        notices_def = [
            ("Félicitations",            "Excellent comportement et résultats en nette hausse ce trimestre. Bravo !"),
            ("Avertissement travail",     "Les résultats sont insuffisants et ne correspondent pas aux capacités de l'élève."),
            ("Oubli de matériel répété", "L'élève oublie régulièrement son matériel (cahier, trousse). Merci d'y remédier."),
            ("Encouragements",           "Des progrès notables sont observés. Continuez sur cette lancée."),
            ("Bavardages en classe",      "Les bavardages perturbent le bon déroulement des cours et pénalisent la classe."),
            ("Résultats en baisse",       "Les résultats du trimestre sont en baisse par rapport au trimestre précédent."),
            ("Participation exemplaire",  "L'élève fait preuve d'une participation active et enrichissante en classe."),
            ("Assiduité insuffisante",    "Le nombre d'absences injustifiées est préoccupant. Un rattrapage s'impose."),
        ]
        for titre, contenu in notices_def:
            eleve = rng.choice(all_eleves)
            mat = rng.choice([None, None, matieres["Mathématiques"], matieres["Français"]])
            n_date = date(2025, 9, 1) + timedelta(days=rng.randint(0, 300))
            db.session.add(Notice(
                eleve=eleve,
                titre=titre,
                contenu=contenu,
                matiere=mat,
                date=n_date,
                saisi_par=directeur,
            ))

        # ------------------------------------------------------------------ #
        # Contacts parents (30 élèves sur 60)
        # ------------------------------------------------------------------ #
        for eleve in rng.sample(all_eleves, 30):
            liens = rng.sample(["pere", "mere"], k=rng.randint(1, 2))
            for lien in liens:
                db.session.add(ContactParent(
                    eleve=eleve,
                    lien=lien,
                    nom=f"{rng.choice(NOMS_PARENTS)} {rng.choice(PRENOMS_PARENTS)}",
                    telephone=f"06{rng.randint(10_000_000, 99_999_999)}",
                    email=f"parent{rng.randint(100, 999)}@example.com",
                ))

        # ------------------------------------------------------------------ #
        # Rapports générés (entrées historiques, sans fichier)
        # ------------------------------------------------------------------ #
        rapports_def = [
            ("notes",      f"Notes 6ème A — T1",              datetime(2025, 12, 22, 10, 0)),
            ("notes",      f"Notes 5ème B — T1",              datetime(2025, 12, 22, 10, 5)),
            ("notes",      f"Notes 4ème C — T1",              datetime(2025, 12, 22, 10, 10)),
            ("absences",   f"Absences 6ème A — T1",           datetime(2025, 12, 22, 11, 0)),
            ("discipline", f"Discipline du 2025-09-01 au 2025-12-19", datetime(2025, 12, 20, 18, 0)),
        ]
        for rtype, titre, created in rapports_def:
            db.session.add(RapportGenere(
                type=rtype, titre=titre, date_creation=created,
                cycle_id=cycle1.id if rtype == "discipline" else None,
            ))

        db.session.commit()

        nb_eleves = len(all_eleves)
        return (
            f"✓ Démo créée : {nb_eleves} élèves dans {len(classes)} classes, "
            f"3 trimestres, 2 cycles discipline (1 cloturé), "
            f"comptes : demo@ecole.fr / prof.maths@demo.fr / prof.lettres@demo.fr / surveillant@demo.fr "
            f"(mot de passe : demo123)"
        )
