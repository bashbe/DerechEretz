# Refonte de l'interface — Gestion École

Date : 2026-07-05

## Contexte

L'application existante (Flask + Bootstrap 5 + htmx + SQLite) fonctionne mais son interface
est cloisonnée par rôle : trois tableaux de bord et trois barres de navigation distincts
(`directeur`, `professeur`, `surveillant`), chacun avec ses propres routes. Cette refonte vise
une interface **unique, cohérente et intuitive**, organisée par fonctionnalité (onglets),
où l'accès aux données et aux actions est déterminé par des **capacités** liées au rôle plutôt
que par des zones d'application séparées.

## Objectifs

- Une seule navigation, les mêmes URLs pour tous les rôles.
- Le directeur voit et modifie tout.
- Le surveillant voit tout, mais ne modifie que présences et vie scolaire.
- Le professeur ne voit/modifie que les notes de ses matières affectées, et dans la fiche
  élève ne voit que ses notes et les événements de vie scolaire tagués sa matière.
- Chaque onglet de liste (Présences, Notes, Vie scolaire, Rapports) propose plusieurs **vues
  par période** (cycle actuel, mois, trimestre, année scolaire) filtrant les événements affichés.
- Une zone Admin réservée au directeur pour les comptes, les élèves, les classes/matières/
  affectations, le barème, les périodes (années/trimestres) et les cycles de discipline.

## Modèle de données

### Modèles conservés sans changement
`User`, `Classe`, `Matiere`, `AffectationProf`, `TypeInfractionMineure`, `CycleDiscipline`,
`SnapshotPointsEleve`.

### Nouveaux modèles

**AnneeScolaire**
- `libelle` (ex. "2025-2026"), `date_debut`, `date_fin`, `active` (bool, une seule active à la fois)

**Trimestre**
- `annee_id` (FK AnneeScolaire), `code` (T1/T2/T3), `date_debut`, `date_fin`

**Controle**
- `matiere_id`, `classe_id`, `intitule`, `date`, `coefficient` (float), `trimestre_id`, `saisi_par_id`
- Remplace le trio `matiere_id/trimestre/date` qui était porté directement par `Note`.

**Presence**
- `eleve_id`, `date`, `statut` (`present`/`absent`/`retard`), `heure_arrivee` (nullable, requis
  si `retard`), `justifie` (bool), `motif` (nullable), `saisi_par_id`
- Contrainte unique `(eleve_id, date)` — une seule entrée d'appel par élève et par jour.
- Remplace `Absence` (qui ne stockait que les exceptions, sans notion d'appel complet ni d'heure
  d'arrivée).

**Notice**
- `eleve_id`, `titre`, `contenu` (text), `matiere_id` (nullable), `date`, `saisi_par_id`
- Notice d'information de vie scolaire, sans impact sur les points.

**ContactParent**
- `eleve_id`, `lien` (`pere`/`mere`/`autre`), `nom`, `telephone` (nullable), `email` (nullable)
- Plusieurs contacts par élève.

### Modèles modifiés

**Note**
- Retrait de `matiere_id`, `trimestre`, `date`.
- Ajout de `controle_id` (FK Controle, nullable=False), contrainte unique `(eleve_id, controle_id)`.
- Matière, date et trimestre sont désormais dérivés du `Controle` lié.

**InfractionMineure**, **IncidentMajeur**
- Ajout de `matiere_id` (nullable) — permet de taguer un événement de vie scolaire à une
  matière ; `null` = événement général non lié à un cours.

**CycleDiscipline**
- Dates (`date_debut`, `date_fin`) rendues modifiables depuis l'admin.
- Création et clôture restent des actions manuelles (pas de +15 jours automatique) ; un seul
  cycle ouvert (`date_cloture IS NULL`) à la fois.
- Comportement de clôture inchangé : snapshot des points de chaque élève dans
  `SnapshotPointsEleve`, puis reset à `POINTS_DEPART` (20).

### Deux coefficients distincts (coexistent)

- `Matiere.coefficient` : poids de la matière dans la moyenne générale de l'élève (inchangé).
- `Controle.coefficient` : poids d'un contrôle donné dans la moyenne de sa matière (nouveau).

Calcul : moyenne matière = moyenne pondérée des notes de la matière par coefficient de
contrôle ; moyenne générale = moyenne pondérée des moyennes de matière par coefficient de
matière.

### Résolution des périodes

Fonction unique `resoudre_periode(preset, reference=None)` → `(date_debut, date_fin)` :

- `cycle` → dates du `CycleDiscipline` ouvert (ou du cycle explicitement sélectionné dans le filtre)
- `mois` → premier/dernier jour du mois calendaire courant
- `trimestre` → dates du `Trimestre` contenant la date de référence (par défaut aujourd'hui),
  sélectionnable manuellement
- `annee` → dates de l'`AnneeScolaire` active

Ce même intervalle filtre uniformément `Presence.date`, `InfractionMineure.date`,
`IncidentMajeur.date`, `Notice.date`, `Controle.date` (et donc les notes qui en dépendent).
Un composant Jinja partagé (`_macros.html`) affiche le sélecteur de période et est réutilisé
sur tous les onglets de liste.

## Permissions

Module unique `app/permissions.py` : fonctions pures `peut_xxx(user, ...)`, utilisées à la
fois comme garde serveur (403 si refusé) et côté template pour l'affichage conditionnel des
actions (boutons Ajouter/Modifier/Supprimer). Aucune règle de permission dupliquée ailleurs.

| Capacité | Directeur | Surveillant | Professeur |
|---|---|---|---|
| Onglets visibles | Tous | Tous sauf Admin | Élèves, Notes uniquement |
| Voir liste élèves / fiche élève | ✅ | ✅ complète | ✅ limitée (voir détail ci-dessous) |
| Voir/créer/modifier présences | ✅ | ✅ | ❌ |
| Voir/créer/modifier vie scolaire | ✅ | ✅ | ❌ (sauf lecture filtrée dans la fiche élève) |
| Voir/créer/modifier contrôles & notes | ✅ | ❌ | ✅ — ses `(matière, classe)` affectées uniquement |
| Générer rapports | ✅ | ✅ | ❌ |
| Admin | ✅ | ❌ | ❌ |

**Fiche élève — vue professeur** : uniquement les notes de sa matière affectée, et les
événements de vie scolaire (`InfractionMineure`, `IncidentMajeur`, `Notice`) dont
`matiere_id` correspond à sa matière. Pas d'accès aux présences ni aux notes/événements
d'autres matières.

## Onglets

Navigation unique, mêmes URLs pour tous, contenu adapté par capacité.

### Élèves (`/eleves`)
Lecture seule. Liste groupée par classe ; ligne cliquable → fiche élève.

**Fiche élève** — identité (nom, prénom, classe, contacts parents), moyennes par matière +
moyenne générale (période sélectionnée), timeline présences/retards, timeline vie scolaire,
solde de points actuel. Contenu réduit pour un professeur (voir Permissions). Bouton
**« Générer un rapport »** déclenchant le flux de rapport **individuel** décrit dans l'onglet
Rapports ci-dessous, avec cet élève et cette période pré-sélectionnés.

Aucune création/modification d'élève ici — déplacé en Admin.

### Présences (`/presences`)
Vue par défaut : table en lecture seule des entrées de la période filtrée (élève, statut,
heure d'arrivée, classe), + vue récapitulative des cumuls par élève sur la période (absences,
retards, minutes cumulées).

Bouton **« Faire l'appel »** → formulaire par classe + date : grille de tous les élèves de la
classe avec statut/heure d'arrivée. Sert à la fois de création et de mise à jour (si une
entrée existe déjà pour eleve+date, elle est pré-remplie et mise à jour à la sauvegarde) —
permet la mise à jour au fil de la journée. Cliquer une ligne existante dans la liste rouvre
ce même formulaire pré-rempli.

### Notes (`/notes`)
Vue par défaut : liste des contrôles de la période filtrée (matière, classe, coefficient,
date), restreinte aux `(matière, classe)` affectées pour un professeur.

Bouton **« Nouveau contrôle »** → formulaire (matière, classe, intitulé, date, coefficient)
puis redirection vers la grille de saisie des notes élève par élève. Cliquer un contrôle
existant rouvre sa grille de saisie.

### Vie scolaire (`/vie-scolaire`)
Vue par défaut : liste des événements (infractions mineures / incidents majeurs / notices) de
la période filtrée, avec sous-filtre par type.

Bouton **« Ajouter »** → formulaire à 3 choix selon le type (mineure : élève + type
d'infraction du barème + matière optionnelle ; majeure : élève + description + gravité +
sanction + matière optionnelle ; notice : élève + titre + contenu + matière optionnelle).

### Rapports (`/rapports`)
Vue par défaut : historique des rapports générés dans la période filtrée.

Bouton **« Générer »** → formulaire à deux modes :
- **Général** : classe (ou toute l'école) + période → PDF/Excel avec, par élève : moyenne
  générale, cumul présences/retards, solde de points. Fusionne les trois générateurs
  existants (`generer_rapport_notes/absences/discipline`) en un seul rapport multi-sections
  filtré par période.
- **Individuel** : élève + période + types cochés (notes/présences/vie scolaire) → PDF avec
  les sections correspondantes seulement. Accessible aussi directement depuis la fiche élève.

`RapportGenere.type` passe de `('notes','absences','discipline')` à `('general','individuel')`,
avec un champ `filtre_json` (types inclus + période résolue) pour traçabilité et ré-affichage
dans l'historique.

### Admin (`/admin`, directeur uniquement)
- Comptes utilisateurs (repris tel quel)
- Élèves : création/modification, affectation à une classe, gestion des contacts parents
  (déplacé depuis l'ancien onglet directeur)
- Classes, Matières, Affectations professeur↔matière↔classe (repris tel quel)
- Barème des infractions mineures (repris tel quel)
- **Années scolaires & Trimestres** (nouveau) : création/modification des dates
- Cycles de discipline : création/clôture, dates modifiables (repris et adapté)

## Architecture technique

Remplacement des blueprints par rôle (`directeur`, `professeur`, `surveillant`) par des
blueprints par fonctionnalité : `eleves`, `presences`, `notes`, `vie_scolaire`, `rapports`,
`admin`. Toutes les routes sont accessibles à tous les rôles authentifiés ; c'est
`app/permissions.py` qui détermine ce qui est affiché/autorisé, pas le blueprint.

## Phasage d'implémentation

Chaque phase ci-dessous est **indépendante et livrée séparément** (sessions de travail
distinctes, pas un plan unique) :

1. **Fondations** — nouveaux modèles, migrations (`Absence`→`Presence`, `Note`→`Controle`),
   `app/permissions.py`, helper `resoudre_periode`. Aucun changement visible pour l'utilisateur.
2. **Nav unique + onglet Élèves** (lecture seule, fiche élève, génération de rapport individuel).
3. **Onglet Présences** (liste + formulaire d'appel par classe).
4. **Onglet Notes** (liste contrôles + grille de saisie).
5. **Onglet Vie scolaire** (liste + formulaire à 3 types).
6. **Onglet Rapports** (génération fusionnée + historique).
7. **Admin** (ajout Élèves + Années/Trimestres ; reprise Comptes/Classes/Matières/
   Affectations/Barème/Cycles).
8. **Nettoyage** — suppression des anciens blueprints par rôle (`directeur`, `professeur`,
   `surveillant`) une fois toutes les fonctionnalités migrées et vérifiées.

## Hors périmètre (YAGNI)

- Gestion simultanée de plusieurs années scolaires actives.
- Appel par demi-journée ou par créneau de cours (emploi du temps) — l'appel reste au
  grain de la journée.
- Notifications automatiques aux parents (les contacts sont stockés mais aucun envoi n'est
  implémenté dans cette refonte).
