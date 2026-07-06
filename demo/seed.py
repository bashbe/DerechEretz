"""Jeu de données de démonstration : 3 classes × 20 élèves + historique complet,
généré de manière « organique » (profils par élève, tendances dans le temps,
vacances scolaires, cycles de discipline de ~15 jours) plutôt que par tirages
uniformes indépendants.

Commande : flask seed-demo
Comptes créés :
  bmerets@gmail.com      — directeur (mot de passe : 12345678)
  prof.maths@demo.fr     — professeur (mot de passe : demo123, Mathématiques, Sciences, Sport)
  prof.lettres@demo.fr   — professeur (mot de passe : demo123, Français, Histoire-Géo)
  surveillant@demo.fr    — surveillant (mot de passe : demo123)

Réinitialiser la base avant de relancer ce script (PowerShell, depuis la
racine du projet, serveur Flask arrêté) :

    Remove-Item ecole.db -Force
    flask db upgrade
    flask seed-demo

(bash : `rm -f ecole.db && flask db upgrade && flask seed-demo`)
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

PRENOMS_PARENTS = ["Jean", "Marie", "Paul", "Anne", "Pierre", "Sylvie", "Luc", "Isabelle"]

RUES = [
    "rue des Lilas", "rue de la République", "avenue Victor Hugo", "rue Pasteur",
    "rue Jean Jaurès", "allée des Tilleuls", "rue de la Gare", "impasse des Fleurs",
    "avenue Charles de Gaulle", "rue du Moulin", "rue de la Paix", "chemin des Vignes",
]
VILLES = ["Vernon", "Gaillon", "Saint-Marcel", "Pacy-sur-Eure", "Douains"]

# Vacances scolaires 2025-2026 (zone B, approx.) : aucune activité pédagogique
# n'y est générée — les cycles de discipline qui les recouvrent restent creux.
VACANCES = [
    (date(2025, 10, 18), date(2025, 11, 2)),   # Toussaint
    (date(2025, 12, 20), date(2026, 1, 4)),    # Noël
    (date(2026, 2, 14), date(2026, 3, 1)),     # Hiver
    (date(2026, 4, 11), date(2026, 4, 26)),    # Printemps
]


def _en_vacances(jour):
    return any(debut <= jour <= fin for debut, fin in VACANCES)


def _jour_ecole(jour):
    return jour.weekday() < 5 and not _en_vacances(jour)


def _jours_ecole_entre(debut, fin):
    jours = []
    cur = debut
    while cur <= fin:
        if _jour_ecole(cur):
            jours.append(cur)
        cur += timedelta(days=1)
    return jours


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

        jours_cycle = app.config.get("CYCLE_DISCIPLINE_JOURS", 15)

        # ------------------------------------------------------------------ #
        # Comptes
        # ------------------------------------------------------------------ #
        directeur = User(nom="Benoit Mérets", email="bmerets@gmail.com", role="directeur", actif=True)
        directeur.set_password("12345678")

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
        # Classes (niveau -> année de naissance dominante pour 2025-2026)
        # ------------------------------------------------------------------ #
        classes_def = [("6ème A", 2014), ("5ème B", 2013), ("4ème C", 2012)]
        classes = []
        for nom_classe, _ in classes_def:
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
        # Barème infractions mineures (poids = fréquence relative organique)
        # ------------------------------------------------------------------ #
        bareme = [
            ("Bavardage",         1, 35),
            ("Travail non fait",  1, 25),
            ("Retard répété",     2, 20),
            ("Téléphone sorti",   2, 15),
            ("Insolence",         3, 5),
        ]
        types_infraction = []
        poids_infraction = []
        for libelle, pts, poids in bareme:
            t = TypeInfractionMineure(libelle=libelle, points_deduits=pts, actif=True)
            db.session.add(t)
            types_infraction.append(t)
            poids_infraction.append(poids)
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
        # Cycles de discipline — enchaînés sur toute l'année, ~15 jours chacun
        # (cf. config.CYCLE_DISCIPLINE_JOURS). Le dernier reste ouvert.
        # ------------------------------------------------------------------ #
        cycles = []
        cur = annee.date_debut
        while cur <= annee.date_fin:
            fin_cycle = min(cur + timedelta(days=jours_cycle - 1), annee.date_fin)
            cycles.append(CycleDiscipline(date_debut=cur, date_fin=fin_cycle))
            cur = fin_cycle + timedelta(days=1)
        db.session.add_all(cycles)
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Élèves — 20 par classe, noms/prénoms distincts, âge et adresse
        # cohérents avec le niveau de classe.
        # ------------------------------------------------------------------ #
        noms_pool    = list(NOMS)
        prenoms_pool = list(PRENOMS)
        rng.shuffle(noms_pool)
        rng.shuffle(prenoms_pool)

        all_eleves = []
        for i, (classe, (_, annee_naissance)) in enumerate(zip(classes, classes_def)):
            for j in range(20):
                idx = i * 20 + j
                # Une poignée de redoublants/élèves avancés brouille l'âge « pile »
                decalage = rng.choices([-1, 0, 0, 0, 1], weights=[8, 40, 40, 40, 12])[0]
                naissance = date(
                    annee_naissance + decalage,
                    rng.randint(1, 12),
                    rng.randint(1, 28),
                )
                eleve = Eleve(
                    nom=noms_pool[idx % len(noms_pool)],
                    prenom=prenoms_pool[idx % len(prenoms_pool)],
                    classe=classe,
                    points_vie_scolaire=20,
                    date_naissance=naissance,
                    adresse=f"{rng.randint(1, 145)} {rng.choice(RUES)}, {rng.choice(VILLES)}",
                )
                db.session.add(eleve)
                all_eleves.append(eleve)
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Profils par élève (stables sur l'année) :
        #  - niveau scolaire (0=difficulté .. 3=excellent)
        #  - profil de discipline (0=calme, 1=normal, 2=difficile), corrélé
        #    faiblement au niveau scolaire (organique, pas déterministe)
        #  - tendance de progression sur l'année (+/-)
        # ------------------------------------------------------------------ #
        niveau_scolaire = [rng.choices([0, 1, 2, 3], weights=[12, 33, 38, 17])[0] for _ in all_eleves]
        poids_discipline_par_niveau = {
            0: [15, 35, 50], 1: [30, 45, 25], 2: [50, 40, 10], 3: [70, 25, 5],
        }
        profil_discipline = [
            rng.choices([0, 1, 2], weights=poids_discipline_par_niveau[niveau_scolaire[i]])[0]
            for i in range(len(all_eleves))
        ]
        tendance = [rng.uniform(-1.2, 1.6) for _ in all_eleves]  # points de moyenne / trimestre

        ranges = {0: (4.0, 9.0), 1: (9.0, 13.0), 2: (12.5, 17.0), 3: (15.5, 20.0)}

        def note_aleatoire(idx_eleve, tri_index):
            lo, hi = ranges[niveau_scolaire[idx_eleve]]
            derive = tendance[idx_eleve] * tri_index
            v = rng.uniform(lo, hi) + derive + rng.uniform(-1.0, 1.0)
            return round(max(0.0, min(20.0, v)) * 2) / 2  # demi-point

        # ------------------------------------------------------------------ #
        # Notes — 3 trimestres, 2-3 notes par matière, dérive de niveau
        # (progression ou décrochage) au fil de l'année.
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
            for tri_index, (tri_code, tri_start, tri_end) in enumerate(tri_info):
                jours_disponibles = _jours_ecole_entre(tri_start, tri_end) or [tri_start]
                for mat_nom, matiere in matieres.items():
                    nb_notes = 1 if mat_nom == "Sport" else rng.randint(2, 3)
                    for _ in range(nb_notes):
                        db.session.add(Note(
                            eleve=eleve,
                            matiere_id=matiere.id,
                            valeur=note_aleatoire(idx, tri_index),
                            trimestre=tri_code,
                            date=rng.choice(jours_disponibles),
                            saisi_par=prof_par_mat[mat_nom],
                        ))
        db.session.flush()

        # ------------------------------------------------------------------ #
        # Présences — absences/retards organiques : plus fréquents pour les
        # profils « difficile », en début de semaine et au retour de vacances.
        # ------------------------------------------------------------------ #
        jours_annee = _jours_ecole_entre(annee.date_debut, date(2026, 3, 28))

        def _poids_jour(jour):
            poids = 1.0
            if jour.weekday() in (0, 4):  # lundi / vendredi
                poids *= 1.6
            for _, fin_vacances in VACANCES:
                if fin_vacances < jour <= fin_vacances + timedelta(days=5):
                    poids *= 2.2
            return poids

        poids_jours = [_poids_jour(j) for j in jours_annee]

        for idx, eleve in enumerate(all_eleves):
            base_nb = {0: 2, 1: 4, 2: 8}[profil_discipline[idx]]
            nb = max(0, round(rng.gauss(base_nb, 2)))
            if nb and jours_annee:
                nb = min(nb, len(jours_annee))
                jours_absence = rng.choices(jours_annee, weights=poids_jours, k=nb)
                for j in set(jours_absence):
                    statut = rng.choices(["absent", "retard"], weights=[60, 40])[0]
                    heure_arr = None
                    if statut == "retard":
                        heure_arr = time(rng.randint(8, 9), rng.choice([5, 10, 15, 20, 30, 45]))
                    justifie = rng.random() < (0.5 if profil_discipline[idx] == 0 else 0.3)
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
        # Infractions mineures — un tirage par cycle (~15 jours), pondéré par
        # le profil de discipline et réduit sur les cycles chevauchant les
        # vacances. Chaque cycle sauf le dernier est ensuite clôturé (snapshot
        # des points + remise à 20), comme le ferait un CPE en fin de période.
        # ------------------------------------------------------------------ #
        poids_discipline_tirage = {0: 1, 1: 4, 2: 10}
        poids_eleves = [poids_discipline_tirage[profil_discipline[i]] for i in range(len(all_eleves))]

        for i, cycle in enumerate(cycles):
            jours_actifs = _jours_ecole_entre(cycle.date_debut, cycle.date_fin)
            duree_totale = (cycle.date_fin - cycle.date_debut).days + 1
            ratio_scolaire = len(jours_actifs) / duree_totale if duree_totale else 0

            nb_infractions = round(rng.uniform(0.8, 1.3) * len(all_eleves) * 0.09 * ratio_scolaire)
            for _ in range(nb_infractions):
                eleve = rng.choices(all_eleves, weights=poids_eleves)[0]
                ti = rng.choices(types_infraction, weights=poids_infraction)[0]
                mat = rng.choice([None, None, None, matieres["Mathématiques"],
                                  matieres["Français"], matieres["Sciences"]])
                jour = rng.choice(jours_actifs) if jours_actifs else cycle.date_debut
                db.session.add(InfractionMineure(
                    eleve=eleve,
                    type_infraction=ti,
                    date=jour,
                    saisi_par=surveillant,
                    cycle=cycle,
                    matiere=mat,
                ))
                eleve.points_vie_scolaire = max(0, eleve.points_vie_scolaire - ti.points_deduits)
            db.session.flush()

            est_dernier_cycle = i == len(cycles) - 1
            if not est_dernier_cycle:
                for eleve in all_eleves:
                    db.session.add(SnapshotPointsEleve(
                        cycle=cycle, eleve=eleve, points_finaux=eleve.points_vie_scolaire
                    ))
                    eleve.points_vie_scolaire = 20
                cycle.date_cloture = datetime.combine(
                    cycle.date_fin + timedelta(days=1), time(17, 0)
                )
                db.session.flush()

        cycle1, dernier_cycle = cycles[0], cycles[-1]

        # ------------------------------------------------------------------ #
        # Incidents majeurs (rares — davantage chez les profils « difficile »)
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
            eleve = rng.choices(all_eleves, weights=poids_eleves)[0]
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
        # Notices — les positives ciblent plutôt les bons profils, les
        # négatives les profils en difficulté ou indisciplinés.
        # ------------------------------------------------------------------ #
        notices_positives = [
            ("Félicitations",           "Excellent comportement et résultats en nette hausse ce trimestre. Bravo !"),
            ("Encouragements",          "Des progrès notables sont observés. Continuez sur cette lancée."),
            ("Participation exemplaire","L'élève fait preuve d'une participation active et enrichissante en classe."),
        ]
        notices_negatives = [
            ("Avertissement travail",    "Les résultats sont insuffisants et ne correspondent pas aux capacités de l'élève."),
            ("Oubli de matériel répété", "L'élève oublie régulièrement son matériel (cahier, trousse). Merci d'y remédier."),
            ("Bavardages en classe",     "Les bavardages perturbent le bon déroulement des cours et pénalisent la classe."),
            ("Résultats en baisse",      "Les résultats du trimestre sont en baisse par rapport au trimestre précédent."),
            ("Assiduité insuffisante",   "Le nombre d'absences injustifiées est préoccupant. Un rattrapage s'impose."),
        ]
        poids_bons = [3 if niveau_scolaire[i] >= 2 else 1 for i in range(len(all_eleves))]
        poids_faibles = [3 if niveau_scolaire[i] <= 1 or profil_discipline[i] == 2 else 1
                          for i in range(len(all_eleves))]

        for titre, contenu in notices_positives:
            eleve = rng.choices(all_eleves, weights=poids_bons)[0]
            mat = rng.choice([None, None, matieres["Mathématiques"], matieres["Français"]])
            db.session.add(Notice(
                eleve=eleve, titre=titre, contenu=contenu, matiere=mat,
                date=date(2025, 9, 1) + timedelta(days=rng.randint(0, 300)),
                saisi_par=directeur,
            ))
        for titre, contenu in notices_negatives:
            eleve = rng.choices(all_eleves, weights=poids_faibles)[0]
            mat = rng.choice([None, None, matieres["Mathématiques"], matieres["Français"]])
            db.session.add(Notice(
                eleve=eleve, titre=titre, contenu=contenu, matiere=mat,
                date=date(2025, 9, 1) + timedelta(days=rng.randint(0, 300)),
                saisi_par=directeur,
            ))

        # ------------------------------------------------------------------ #
        # Contacts parents (30 élèves sur 60) — le nom de famille du contact
        # correspond le plus souvent à celui de l'élève (foyer non recomposé).
        # ------------------------------------------------------------------ #
        for eleve in rng.sample(all_eleves, 30):
            liens = rng.sample(["pere", "mere"], k=rng.randint(1, 2))
            for lien in liens:
                nom_famille = eleve.nom if rng.random() < 0.7 else rng.choice(noms_pool)
                db.session.add(ContactParent(
                    eleve=eleve,
                    lien=lien,
                    nom=f"{rng.choice(PRENOMS_PARENTS)} {nom_famille}",
                    telephone=f"06{rng.randint(10_000_000, 99_999_999)}",
                    email=f"{nom_famille.lower()}.{lien}{rng.randint(1, 99)}@example.com",
                ))

        # ------------------------------------------------------------------ #
        # Rapports générés (entrées historiques, sans fichier)
        # ------------------------------------------------------------------ #
        rapports_def = [
            ("notes",      "Notes 6ème A — T1",              datetime(2025, 12, 22, 10, 0)),
            ("notes",      "Notes 5ème B — T1",              datetime(2025, 12, 22, 10, 5)),
            ("notes",      "Notes 4ème C — T1",              datetime(2025, 12, 22, 10, 10)),
            ("absences",   "Absences 6ème A — T1",           datetime(2025, 12, 22, 11, 0)),
            (
                "discipline",
                f"Discipline du {cycle1.date_debut.isoformat()} au {cycle1.date_fin.isoformat()}",
                datetime.combine(cycle1.date_fin, time(18, 0)),
            ),
        ]
        for rtype, titre, created in rapports_def:
            db.session.add(RapportGenere(
                type=rtype, titre=titre, date_creation=created,
                cycle_id=cycle1.id if rtype == "discipline" else None,
            ))

        db.session.commit()

        nb_eleves = len(all_eleves)
        nb_cloturés = len(cycles) - 1
        return (
            f"✓ Démo créée : {nb_eleves} élèves dans {len(classes)} classes, "
            f"3 trimestres, {len(cycles)} cycles de discipline de ~{jours_cycle} jours "
            f"({nb_cloturés} clôturés, le dernier actif). "
            f"Compte directeur : bmerets@gmail.com / 12345678. "
            f"Autres comptes (mot de passe demo123) : prof.maths@demo.fr / prof.lettres@demo.fr / surveillant@demo.fr"
        )
