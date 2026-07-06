# Refonte visuelle complète en Tailwind — Design

Date : 2026-07-06
Statut : approuvé

## Contexte

L'utilisateur a fourni un export Google Stitch (`stitch_scholartrack_admin_suite.zip`) contenant
une charte de design complète (`administrative_excellence/DESIGN.md`) et 4 écrans HTML/Tailwind
statiques : `admin_dashboard`, `student_directory`, `student_profile_alex_johnson`,
`infraction_records`. L'app actuelle (`app/templates/`) utilise Bootstrap 5 (navbar en haut,
classes `btn`/`card`/`badge`/`table`/`form-select`, JS `data-bs-*`) sur ~31 templates.

Décision : conversion complète de l'app vers Tailwind, en reprenant les tokens de la maquette,
plutôt qu'un simple rafraîchissement CSS par-dessus Bootstrap.

## Objectifs

1. Une coquille (`base.html`) fidèle à la maquette : sidebar fixe + topbar, sans dépendance à
   Bootstrap JS.
2. Un kit de composants Tailwind réutilisable dans `_macros.html` pour éviter de dupliquer les
   classes dans chacun des ~31 templates.
3. Les 4 pages ayant un équivalent direct dans la maquette adoptent sa mise en page ; les autres
   pages réutilisent le même kit de composants pour rester cohérentes visuellement.
4. Aucune régression fonctionnelle : la suite de tests (48 tests, logique métier/routes) doit
   rester au vert — seuls les templates et, pour le nouveau tableau de bord, une route sont
   modifiés.

## Hors scope

- Mode sombre (validé avec l'utilisateur : clair uniquement).
- Recherche globale et notifications réellement fonctionnelles (UI seulement, non branchées).
- Graphique JS externe (Chart.js etc.) — pas de nouvelle dépendance JS.
- Redesign des PDF générés par `app/reports/generation.py` (hors périmètre visuel web).

## Tokens de design (source : `DESIGN.md` de la maquette)

Repris tels quels dans la config Tailwind CDN de `base.html` :

- **Couleurs clés** : `primary #0057cd` (actions/liens actifs), `primary-container #0d6efd`
  (accent secondaire), `secondary #535d7e`, `tertiary #405f8d`, `error #ba1a1a`,
  `success-green #198754`, `warning-amber #FFC107`, `surface #fcf8ff` (fond),
  `surface-container-low #f5f2ff` (sidebar), `on-surface #1a1a2e` (texte), `on-surface-variant
  #424655` (texte secondaire), `border-subtle #DEE2E6`, `surface-muted #F8F9FA` (fond d'en-têtes
  de tableau).
- **Typo** : Open Sans partout. Échelles `headline-xl` (32px/700), `headline-lg` (24px/600),
  `headline-md` (20px/600), `body-lg` (16px/400), `body-md` (14px/400, taille par défaut des
  tableaux/formulaires), `label-sm` (12px/600, majuscules, tracking large — utilisé pour les
  en-têtes de colonnes et métadonnées).
- **Rayons** : `DEFAULT 0.125rem`, `lg 0.25rem`, `xl 0.5rem`, `full 0.75rem` (repris de la config
  Tailwind du mockup, qui diffère légèrement des valeurs `rounded` du DESIGN.md — on garde la
  config Tailwind car c'est elle qui est réellement appliquée dans le HTML des 4 écrans).
- **Élévation** : pas d'ombre par défaut ; `hover:shadow-md` sur les cartes interactives
  uniquement. Bordure 1px `border-subtle` partout ailleurs.
- **Icônes** : Google *Material Symbols Outlined* (police, via `<link>`), pas de Bootstrap Icons.

## `base.html` — nouvelle coquille

- `<head>` : Tailwind CDN (`?plugins=forms`) + bloc `<script id="tailwind-config">` avec les
  tokens ci-dessus ; polices Open Sans + Material Symbols Outlined ; suppression du CDN
  Bootstrap (CSS et JS).
- **Sidebar** (`<aside>` fixe, 280px, `bg-surface-container-low`, `border-r border-border-subtle`) :
  - En-tête : logo (icône `school` dans un carré `bg-primary`), nom **« דרך ארץ »**, sous-titre =
    libellé du rôle courant (`current_user.role`).
  - Nav principale, items identiques à l'actuelle (adaptés aux permissions déjà en place dans
    `base.html`) : Élèves, Vie scolaire, Rapports (directeur/surveillant), section Admin
    (directeur uniquement, sous-liste dépliée directement dans la sidebar plutôt qu'un dropdown
    topbar — plus fidèle au patron « sidebar contient toute la nav » de la maquette).
  - État actif déterminé côté serveur via `request.blueprint` (comme aujourd'hui), pas de JS pour
    ça (le mockup simule l'état actif en JS parce que c'est une page statique isolée ; ici on a
    déjà l'info côté serveur).
  - Pied de sidebar : nom + rôle de l'utilisateur, lien Déconnexion.
- **Topbar** (`<header>` sticky, `h-16`, `border-b`) : nom de la page courante (`{% block
  page_title %}`, optionnel), champ de recherche non fonctionnel (cosmétique, comme la maquette),
  badge rôle, avatar (initiales dans un cercle `bg-primary/10 text-primary`, pas de vraie photo).
- **Bannière démo** et **flashs** : réhabillés avec les couleurs de la charte (`warning-amber` /
  `error` / `success-green` / `primary`) au lieu des classes `alert-*` Bootstrap, mais gardent la
  même info (catégorie de flash → couleur).
- **Mobile (< 1024px)** : sidebar masquée par défaut (`-translate-x-full`), un bouton hamburger
  dans la topbar la fait apparaître en tiroir (JS vanilla : `classList.toggle`), overlay semi-
  transparent pour fermer au clic.
- Zone de contenu : `<main class="lg:ml-72">`, padding `p-8` (`margin-edge`), fond `bg-surface`.

## Kit de composants (`_macros.html`)

Macros ajoutées/réécrites (signatures) :

- `bouton(label, variant='primary', type='button', href=None, icone=None, attrs='')` → rend soit
  un `<a>` soit un `<button>` selon `href`. Variantes : `primary` (fond `bg-primary` texte blanc),
  `ghost` (bordure `border-primary` texte `text-primary`, fond transparent), `danger` (fond
  `bg-error` texte blanc), `outline-danger` (bordure `border-error` texte `text-error`).
- `badge(texte, couleur='neutral')` → couleurs : `neutral` (gris), `success`, `warning`, `danger`,
  `primary`. Fond faible saturation + texte contrasté, `rounded-full px-3 py-1 text-label-sm`.
- `carte(titre=None)` → conteneur `bg-surface border border-border-subtle rounded-xl`, en-tête
  optionnel avec `border-b`, corps `p-6`.
- `champ(field)` (remplace l'actuelle version Bootstrap) → même usage (`{{ champ(form.nom) }}`),
  rendu Tailwind : label au-dessus (`text-label-sm font-semibold`), input/select
  `border border-border-subtle rounded-lg px-3 py-2 text-body-md focus:ring-2
  focus:ring-primary/20`, erreurs en `text-error text-label-sm`.
- `bouton_supprimer(action, label='Supprimer')` (déjà existant) → réhabillé avec le nouveau
  `bouton(variant='outline-danger')`.
- `tableau_debut()` / classes zébrées : pas une macro à part, mais une classe utilitaire
  `.zebra-stripe` (comme le mockup) + gabarit d'en-tête `bg-surface-muted text-label-sm
  uppercase tracking-wider text-on-surface-variant` documenté en commentaire dans
  `_macros.html` pour que chaque template l'applique à son `<thead>`.
- `selecteur_periode` / `navigation_periode` (déjà existants, ajoutés lors des sessions
  précédentes) : conservés fonctionnellement, juste réhabillés en boutons du nouveau kit.

## Nouveau tableau de bord (mapping `admin_dashboard`)

- Nouvelle route `GET /tableau-de-bord` dans `app/main/routes.py`, template
  `app/templates/main/dashboard.html`.
- `main.dashboard` (route `/`) : le directeur et le surveillant sont redirigés vers ce nouveau
  tableau de bord au lieu d'atterrir directement sur `eleves.liste` ; le professeur continue
  d'atterrir sur `vie_scolaire.index` (son usage réel n'est pas un tableau de bord global).
- 4 cartes bento avec de **vraies données**, pas les placeholders du mockup :
  - Total élèves : `Eleve.query.count()`.
  - Nombre de classes : `Classe.query.count()`.
  - Infractions mineures (7 derniers jours) : `InfractionMineure` dont `date` dans les 7 derniers
    jours glissants.
  - Comptes actifs : `User.query.filter_by(actif=True).count()`.
  - (Le mockup a une carte « Avg. Attendance » ; on ne dispose pas d'un taux de présence fiable
    sans inventer une formule — remplacée par « Infractions mineures » ci-dessus pour rester
    honnête sur les données disponibles.)
- Bloc « Activité récente » : les 8 derniers événements tous types confondus via
  `evenements.feed()` sur une fenêtre glissante de 30 jours, réutilisant `ligne_evenement`-style
  mais en version compacte (liste, pas tableau), avec lien vers la fiche de l'événement.
- Pas de graphique de tendance (hors scope, pas de donnée équivalente propre à afficher sans
  fabriquer un algorithme d'assiduité).

## Mapping écrans maquette → pages de l'app

| Écran maquette | Page app | Traitement |
|---|---|---|
| `admin_dashboard` | nouveau `main/dashboard.html` | nouvelle page, cf. ci-dessus |
| `student_directory` | `eleves/liste.html` | restylée : recherche/filtre classe existants gardés, table zébrée, avatar initiales |
| `student_profile_alex_johnson` | `eleves/fiche.html` | restylée : cartes identité/points/moyennes déjà en place, juste réhabillées ; logique période/cycle **inchangée** |
| `infraction_records` | `vie_scolaire/evenements.html` | restylée : filtres période/type/classe/élève gardés, table zébrée |

Toutes les autres pages (`admin/*`, `rapports/liste.html`, `vie_scolaire/index.html`,
`vie_scolaire/appel.html`, `vie_scolaire/saisie.html`, `vie_scolaire/controles.html`,
`vie_scolaire/controle_form.html`, `vie_scolaire/evenement_fiche.html`,
`vie_scolaire/evenement_modifier.html`, `auth/login.html`, `demo/landing.html`,
`errors/403.html`, `errors/404.html`) gardent leur structure et logique actuelles, mais consomment
le nouveau kit de composants (`bouton`, `badge`, `carte`, `champ`) à la place des classes
Bootstrap. Aucun de ces gabarits n'a de mockup dédié à reproduire pixel pour pixel.

## JS nécessaire (vanilla, pas de nouvelle dépendance)

- Toggle sidebar mobile (tiroir + overlay).
- Dropdown/`<details>` natif pour les rares menus déroulants qui existent déjà (ex. Admin en
  version desktop, si on garde un sous-menu repliable au lieu de tout déplier) — à trancher au
  moment de l'implémentation selon ce qui rend le mieux dans la sidebar.
- Les `confirm()` inline existants sur les boutons de suppression sont conservés tels quels (déjà
  vanilla JS, ne dépendent pas de Bootstrap).

## Vérification

- La suite de tests existante (48 tests) ne doit pas régresser — elle ne teste pas le rendu HTML
  en détail, donc le risque principal est la nouvelle route `main.dashboard` (à couvrir par un
  test si le temps le permet) et les routes existantes qui ne changent pas de comportement.
- Vérification visuelle via le serveur de preview (`preview_start`/`preview_screenshot`/
  `preview_snapshot`) sur au minimum : login, tableau de bord, liste élèves, fiche élève, liste
  événements, un formulaire admin (élève), rapports. Cohérence responsive (mobile/desktop) sur au
  moins la sidebar/topbar.

## Plan de rollout (pour la phase plan/implémentation)

Étant donné le volume (31 templates), l'implémentation se fera en plusieurs lots :
1. `base.html` + config Tailwind + kit de composants `_macros.html` (fondations, bloquant pour
   tout le reste).
2. Nouveau tableau de bord (`main/dashboard.html` + route).
3. Les 3 pages avec mockup dédié (`eleves/liste.html`, `eleves/fiche.html`,
   `vie_scolaire/evenements.html`).
4. Le reste des templates (admin/*, rapports, vie_scolaire restants, auth, demo, erreurs),
   convertis en série en réutilisant le kit de l'étape 1 — candidats à la parallélisation par
   sous-agents une fois le kit stabilisé, car ce sont des conversions mécaniques répétitives.
