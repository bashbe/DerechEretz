# Gestion École

Application web de gestion scolaire développée avec Flask. Tout le suivi quotidien des élèves
(présences, notes, infractions, observations) est présenté comme un **flux d'événements
unifié**, avec trois rôles distincts (directeur, professeur, surveillant).

L'interface tient en quatre onglets : **Élèves · Vie scolaire · Rapports · Admin**.

---

## Fonctionnalités

### Élèves
- Liste des élèves (nom, prénom) groupée par classe, cliquable
- **Fiche élève** : identité, contacts parents, solde de points de vie scolaire, moyennes par
  matière et générale, et un **rapport d'activités** unifié (notes, absences/retards,
  infractions, observations) où chaque activité est cliquable vers sa fiche
- Sélecteur de période (mois courant, trimestre, année scolaire, cycle de discipline) filtrant
  toutes les données affichées
- Bouton « Ajouter un événement » pré-rempli avec l'élève (selon la permission)

### Vie scolaire — hub central des événements
- **Formulaire unifié « nouvel événement »** : type (infraction mineure/majeure, note,
  observation, absence/retard — filtré selon le rôle), cible (toute l'école, une classe, une
  sélection d'élèves), jour, matière optionnelle, éditeur ; les champs affichés s'adaptent au
  type choisi
- **Liste des événements** filtrable par période, type, classe et élève ; chaque ligne ouvre
  une **fiche d'activité** avec modification/suppression selon les compétences
- Raccourci **carnet de présence du jour** : appel par classe et par date (une seule entrée
  par élève et par jour, mise à jour au fil de la journée)
- Raccourci **entrer des notes** : contrôles avec coefficient et grille de saisie par classe

### Système de points
- Chaque élève démarre avec **20 points** ; les infractions mineures déduisent des points
  selon un barème configurable, et le solde est recalculé si une infraction est modifiée ou
  supprimée
- Moyennes calculées à part : par matière (pondérées par coefficient du contrôle) et générale
  (pondérée par coefficient de matière)
- **Cycles de discipline** : période ouverte/clôturée ; à la clôture, les points finaux sont
  figés dans un snapshot et remis à 20

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
| Créer absences/retards, appel | ✅ | ✅ | — |
| Créer infractions (mineures/majeures) | ✅ | ✅ | — |
| Créer notes & contrôles | ✅ | — | ✅ (ses affectations) |
| Créer observations | ✅ | ✅ | ✅ (ses matières) |
| Modifier/supprimer un événement | ✅ tous | ✅ vie scolaire | ✅ les siens |
| Rapports | ✅ | ✅ | — |
| Administration | ✅ | — | — |

Un professeur ne voit dans les feeds que les notes de ses propres matières et les événements
tagués à ces matières ; il ne voit pas les présences.

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

## Initialisation minimaliste

La commande `seed-demo` initialise la base vierge avec :
- Compte directeur : `bmerets@gmail.com` / `12345678`
- Matières, classes, année scolaire et trimestres (structure vide)

```bash
flask db upgrade
flask seed-demo
python run.py
```

Visitez **http://127.0.0.1:5000** et connectez-vous avec :
- Email : `bmerets@gmail.com`
- Mot de passe : `12345678`

Puis créez les classes, élèves et données scolaires depuis l'interface (onglet Admin pour la directrice).

Le jeu de données comprend 3 classes, 60 élèves, ~2 000 notes sur 3 trimestres, ~325 présences, 50 infractions, 6 incidents majeurs, 8 notices et 2 cycles de discipline (un clôturé, un en cours).

---

## Tests

```bash
pytest
```
