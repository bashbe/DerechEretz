# Gestion École

Application web de gestion scolaire développée avec Flask. Elle couvre le suivi quotidien des élèves : présences, notes, vie scolaire et rapports, avec trois rôles distincts (directeur, professeur, surveillant).

---

## Fonctionnalités

### Élèves
- Liste de tous les élèves groupée par classe
- **Fiche élève** : identité, contacts parents, solde de points de vie scolaire, moyennes par matière et générale, timeline des présences, timeline de la vie scolaire
- Sélecteur de période (mois courant, trimestre, année scolaire, cycle de discipline) filtrant toutes les données affichées

### Notes
- Saisie par matière, classe et trimestre
- Calcul automatique des moyennes par matière (pondérées par coefficient du contrôle) et de la moyenne générale (pondérée par coefficient de matière)
- Chaque contrôle porte son propre coefficient, indépendant du coefficient de la matière

### Présences
- Appel par classe et par date
- Statuts : présent, absent, retard (avec heure d'arrivée)
- Justification et motif facultatif
- Contrainte : une seule entrée par élève et par jour

### Vie scolaire — système de points
- Chaque élève démarre avec **20 points**
- **Infractions mineures** : déduisent des points selon un barème configurable (bavardage, téléphone, insolence…)
- **Incidents majeurs** : enregistrement de la description, de la gravité et de la sanction
- **Notices** : observations libres (félicitations, avertissements, encouragements)
- Tous les événements peuvent être rattachés à une matière (optionnel)
- **Cycles de discipline** : période ouverte/clôturée ; à la clôture, les points finaux sont figés dans un snapshot et remis à 20

### Rapports
- Génération de rapports PDF et Excel pour les notes, les absences et la discipline
- Historique des rapports générés avec téléchargement

### Administration (directeur uniquement)
- Gestion des comptes utilisateurs (directeur, professeurs, surveillants)
- Gestion des classes, matières et coefficients
- Affectations professeur ↔ matière ↔ classe
- Barème des infractions mineures
- Années scolaires et trimestres (dates de début/fin)
- Cycles de discipline (création, clôture)

---

## Rôles et permissions

| Fonctionnalité | Directeur | Surveillant | Professeur |
|---|:---:|:---:|:---:|
| Fiche élève complète | ✅ | ✅ | ✅ (ses matières) |
| Présences | ✅ | ✅ | — |
| Notes & contrôles | ✅ | — | ✅ (ses affectations) |
| Vie scolaire | ✅ | ✅ | — (lecture partielle) |
| Rapports | ✅ | ✅ | — |
| Administration | ✅ | — | — |

Un professeur ne voit dans la fiche élève que les notes de ses propres matières et les événements de vie scolaire taggués à ces matières.

---

## Stack technique

- **Backend** : Python 3, Flask 3.0, Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-Login, Flask-WTF
- **Base de données** : SQLite (fichier `ecole.db`)
- **Frontend** : Bootstrap 5, htmx
- **Rapports** : openpyxl (Excel), xhtml2pdf (PDF)
- **Tests** : pytest (36 tests unitaires couvrant modèles, services, permissions et résolution de périodes)

---

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

## Initialisation de la base de données

```bash
flask db upgrade
flask seed-directeur directeur@mon-ecole.fr motdepasse123 --nom "Directeur"
```

> Évitez les domaines réservés (`.test`, `.example`, `.invalid`, `.localhost`) pour les emails.

## Lancer l'application

```bash
python run.py
```

Puis ouvrir http://127.0.0.1:5000 et se connecter avec le compte créé.

---

## Démonstration

Un jeu de données fictif est inclus pour explorer toutes les fonctionnalités sans saisie manuelle.

```bash
flask db upgrade
flask seed-demo
python run.py
```

Puis visiter **http://127.0.0.1:5000/demo** pour accéder à la page d'accueil de la démo.

Quatre profils sont disponibles (mot de passe `demo123`) :

| Compte | Rôle |
|---|---|
| `demo@ecole.fr` | Directeur |
| `prof.maths@demo.fr` | Professeur (Mathématiques, Sciences, Sport) |
| `prof.lettres@demo.fr` | Professeure (Français, Histoire-Géo) |
| `surveillant@demo.fr` | Surveillant |

Le jeu de données comprend 3 classes, 60 élèves, ~2 000 notes sur 3 trimestres, ~325 présences, 50 infractions, 6 incidents majeurs, 8 notices et 2 cycles de discipline (un clôturé, un en cours).

---

## Tests

```bash
pytest
```
