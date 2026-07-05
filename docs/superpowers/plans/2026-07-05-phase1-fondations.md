# Phase 1 — Fondations — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the new data-model foundations (models, permission predicates, period-resolution
helper) required by the interface refonte described in
`docs/superpowers/specs/2026-07-05-refonte-interface-design.md`, without changing any visible
behavior of the running application.

**Architecture:** Purely additive ("expand") database changes: new tables
(`AnneeScolaire`, `Trimestre`, `Controle`, `Presence`, `Notice`, `ContactParent`) and new
**nullable** columns on existing tables (`Note.controle_id`, `InfractionMineure.matiere_id`,
`IncidentMajeur.matiere_id`). Nothing existing is renamed, dropped, or made non-nullable in
this phase — `Absence`, `Note.matiere_id/trimestre/date`, and the three role blueprints stay
exactly as they are and keep working unmodified. This is intentional and matches the
project's request to ship each phase independently: later phases (3 "Présences", 4 "Notes")
wire the new tables into routes/templates, and phase 8 "Nettoyage" is what finally drops the
old columns/tables once nothing reads them anymore. A fresh reviewer running the full test
suite after this phase should see every existing test still pass, plus new tests for the
added pieces.

**Tech Stack:** Flask 3.0.3, Flask-SQLAlchemy 3.1.1, Flask-Migrate 4.0.7 (Alembic
autogenerate), SQLite, pytest 8.3.3.

## Global Constraints

- Python environment: use the project's existing venv (`venv/Scripts/python.exe` on Windows) —
  do not install packages globally.
- Follow existing model style in `app/models.py`: classic `db.Column`/`db.relationship`
  declarations (not the newer `Mapped[]` typed style), `__tablename__` in French snake_case
  plural (e.g. `annees_scolaires`), `back_populates` for relationships that are traversed both
  ways in existing code, plain one-directional `db.relationship(...)` for the rest (matches
  `Note.matiere`, `Note.saisi_par` today).
  matiere/classe/saisi_par).
- Test database: in-memory SQLite created via `db.create_all()` in `tests/conftest.py` — no
  Alembic migration is needed for tests to pass, only for the real `instance`/`ecole.db`
  database.
- Real database migration: generate via `flask db migrate -m "..."`, review the generated
  file by hand before applying, then `flask db upgrade`. Set `FLASK_APP=run.py` first
  (`set FLASK_APP=run.py` on Windows cmd, `$env:FLASK_APP="run.py"` in PowerShell,
  `export FLASK_APP=run.py` in bash).
- No task in this phase may modify `app/directeur/`, `app/professeur/`, `app/surveillant/`,
  or any file under `app/templates/` — this phase is model/helper layer only.
- Run the full suite with `venv/Scripts/python.exe -m pytest -q` after every task; all
  previously-passing tests must remain green.

---

### Task 1: `AnneeScolaire` model

**Files:**
- Modify: `app/models.py` (add class after `RapportGenere`, at end of file)
- Test: `tests/test_models_fondations.py` (new file)

**Interfaces:**
- Produces: `app.models.AnneeScolaire` with columns `id`, `libelle` (str), `date_debut` (date),
  `date_fin` (date), `active` (bool, default `False`). Table name `annees_scolaires`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_models_fondations.py`:

```python
from datetime import date

from app.extensions import db
from app.models import AnneeScolaire


def test_annee_scolaire_creation(app):
    annee = AnneeScolaire(
        libelle="2025-2026",
        date_debut=date(2025, 9, 1),
        date_fin=date(2026, 6, 30),
        active=True,
    )
    db.session.add(annee)
    db.session.commit()

    recuperee = db.session.get(AnneeScolaire, annee.id)
    assert recuperee.libelle == "2025-2026"
    assert recuperee.date_debut == date(2025, 9, 1)
    assert recuperee.date_fin == date(2026, 6, 30)
    assert recuperee.active is True


def test_annee_scolaire_active_par_defaut_false(app):
    annee = AnneeScolaire(
        libelle="2024-2025", date_debut=date(2024, 9, 1), date_fin=date(2025, 6, 30)
    )
    db.session.add(annee)
    db.session.commit()

    assert annee.active is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `ImportError: cannot import name 'AnneeScolaire' from 'app.models'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/models.py`:

```python
class AnneeScolaire(db.Model):
    __tablename__ = "annees_scolaires"

    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(20), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)

    trimestres = db.relationship(
        "Trimestre", back_populates="annee", cascade="all, delete-orphan"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add AnneeScolaire model"
```

---

### Task 2: `Trimestre` model

**Files:**
- Modify: `app/models.py`
- Test: `tests/test_models_fondations.py`

**Interfaces:**
- Consumes: `AnneeScolaire` (Task 1), `TRIMESTRES` tuple already defined at top of
  `app/models.py` (`("T1", "T2", "T3")`).
- Produces: `app.models.Trimestre` with columns `id`, `annee_id` (FK), `code` (str, one of
  `TRIMESTRES`), `date_debut` (date), `date_fin` (date). Table name `trimestres`. Relationship
  `Trimestre.annee` (back_populates `AnneeScolaire.trimestres`). Relationship
  `Trimestre.controles` (back_populates `Controle.trimestre`, added in Task 5).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_fondations.py`:

```python
from app.models import Trimestre


def test_trimestre_lie_a_annee_scolaire(app):
    annee = AnneeScolaire(
        libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30)
    )
    db.session.add(annee)
    db.session.commit()

    trimestre = Trimestre(
        annee=annee, code="T1", date_debut=date(2025, 9, 1), date_fin=date(2025, 12, 19)
    )
    db.session.add(trimestre)
    db.session.commit()

    assert trimestre.annee_id == annee.id
    assert annee.trimestres == [trimestre]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `ImportError: cannot import name 'Trimestre' from 'app.models'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/models.py` (after `AnneeScolaire`):

```python
class Trimestre(db.Model):
    __tablename__ = "trimestres"

    id = db.Column(db.Integer, primary_key=True)
    annee_id = db.Column(db.Integer, db.ForeignKey("annees_scolaires.id"), nullable=False)
    code = db.Column(db.String(2), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)

    annee = db.relationship("AnneeScolaire", back_populates="trimestres")
    controles = db.relationship("Controle", back_populates="trimestre")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (3 tests). Note: this will fail again at collection once Task 5 doesn't exist
yet — that's fine, `controles` relationship just points to a model that will exist by the end
of Task 5; SQLAlchemy resolves relationship strings lazily so having it reference `Controle`
before that class is defined in the same module is safe as long as `Controle` exists by the
time the app is fully imported (it will, after Task 5 in this same file).

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add Trimestre model"
```

---

### Task 3: `ContactParent` model

**Files:**
- Modify: `app/models.py` (add class; add `contacts_parents` relationship to `Eleve`)
- Test: `tests/test_models_fondations.py`

**Interfaces:**
- Consumes: `Eleve` (existing).
- Produces: `app.models.ContactParent` with columns `id`, `eleve_id` (FK), `lien` (str, one of
  `"pere"`, `"mere"`, `"autre"`), `nom` (str), `telephone` (str, nullable), `email` (str,
  nullable). Table name `contacts_parents`. `Eleve.contacts_parents` relationship
  (cascade delete-orphan).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_fondations.py`:

```python
from app.models import Classe, ContactParent, Eleve


def test_contact_parent_plusieurs_par_eleve(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    db.session.add_all([classe, eleve])
    db.session.commit()

    pere = ContactParent(eleve=eleve, lien="pere", nom="Paul Dupont", telephone="0600000000")
    mere = ContactParent(eleve=eleve, lien="mere", nom="Marie Dupont", email="marie@mail.fr")
    db.session.add_all([pere, mere])
    db.session.commit()

    assert len(eleve.contacts_parents) == 2
    assert {c.lien for c in eleve.contacts_parents} == {"pere", "mere"}


def test_contact_parent_supprime_avec_eleve(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    db.session.add_all([classe, eleve])
    db.session.commit()
    contact = ContactParent(eleve=eleve, lien="pere", nom="Paul Dupont")
    db.session.add(contact)
    db.session.commit()
    contact_id = contact.id

    db.session.delete(eleve)
    db.session.commit()

    assert db.session.get(ContactParent, contact_id) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `ImportError: cannot import name 'ContactParent' from 'app.models'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/models.py` (after `Trimestre`):

```python
class ContactParent(db.Model):
    __tablename__ = "contacts_parents"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    lien = db.Column(db.String(10), nullable=False)  # 'pere', 'mere' ou 'autre'
    nom = db.Column(db.String(120), nullable=False)
    telephone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)

    eleve = db.relationship("Eleve", back_populates="contacts_parents")
```

Modify the `Eleve` class in `app/models.py` to add the relationship (insert next to the
`incidents_majeurs` relationship line):

```python
    contacts_parents = db.relationship(
        "ContactParent", back_populates="eleve", cascade="all, delete-orphan"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add ContactParent model"
```

---

### Task 4: `Notice` model

**Files:**
- Modify: `app/models.py` (add class; add `notices` relationship to `Eleve`)
- Test: `tests/test_models_fondations.py`

**Interfaces:**
- Consumes: `Eleve` (existing), `Matiere` (existing), `User` (existing).
- Produces: `app.models.Notice` with columns `id`, `eleve_id` (FK), `titre` (str), `contenu`
  (text), `matiere_id` (FK, nullable), `date` (date, default today), `saisi_par_id` (FK).
  Table name `notices`. `Eleve.notices` relationship (cascade delete-orphan).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_fondations.py`:

```python
from app.models import Matiere, Notice, User


def test_notice_sans_matiere(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    user = User(nom="Surveillant", email="surv@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, user])
    db.session.commit()

    notice = Notice(
        eleve=eleve, titre="Oubli de carnet", contenu="A répétition.", saisi_par=user
    )
    db.session.add(notice)
    db.session.commit()

    assert notice.matiere_id is None
    assert eleve.notices == [notice]


def test_notice_avec_matiere(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Prof", email="prof@ecole.test", role="professeur")
    user.set_password("password123")
    db.session.add_all([classe, eleve, matiere, user])
    db.session.commit()

    notice = Notice(
        eleve=eleve,
        titre="Matériel oublié",
        contenu="Calculatrice",
        matiere=matiere,
        saisi_par=user,
    )
    db.session.add(notice)
    db.session.commit()

    assert notice.matiere_id == matiere.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `ImportError: cannot import name 'Notice' from 'app.models'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/models.py` (after `ContactParent`):

```python
class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    titre = db.Column(db.String(150), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    eleve = db.relationship("Eleve", back_populates="notices")
    matiere = db.relationship("Matiere")
    saisi_par = db.relationship("User")
```

Modify the `Eleve` class to add the relationship (next to `contacts_parents`):

```python
    notices = db.relationship("Notice", back_populates="eleve", cascade="all, delete-orphan")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add Notice model"
```

---

### Task 5: `Controle` model + `Note.controle_id` column

**Files:**
- Modify: `app/models.py` (add `Controle` class; add nullable `controle_id` + `controle`
  relationship to `Note`)
- Test: `tests/test_models_fondations.py`

**Interfaces:**
- Consumes: `Matiere`, `Classe`, `Trimestre` (Task 2), `User` (existing).
- Produces: `app.models.Controle` with columns `id`, `matiere_id` (FK), `classe_id` (FK),
  `intitule` (str), `date` (date), `coefficient` (float), `trimestre_id` (FK, **nullable** —
  see note below), `saisi_par_id` (FK). Table name `controles`. Relationship
  `Controle.notes` (back_populates `Note.controle`). `Note.controle_id` is added as a
  **nullable** column on the existing `Note` model — existing `Note` rows and existing code
  that creates `Note(matiere_id=..., trimestre=..., date=...)` (in
  `app/professeur/routes.py`) are completely unaffected; this column sits unused until Phase 4
  wires up the new Notes tab.

Note on `trimestre_id` nullability: `Trimestre` rows don't exist for any real period yet (that
UI is Phase 7 / Admin). Making `Controle.trimestre_id` nullable now keeps this phase
non-breaking; the Notes-tab form built in Phase 4 can still require it via a WTForms validator
even though the DB column allows null.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_fondations.py`:

```python
from app.models import Controle, Note


def test_controle_regroupe_les_notes(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve1 = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    eleve2 = Eleve(nom="Martin", prenom="Alice", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Prof", email="prof2@ecole.test", role="professeur")
    user.set_password("password123")
    db.session.add_all([classe, eleve1, eleve2, matiere, user])
    db.session.commit()

    controle = Controle(
        matiere=matiere,
        classe=classe,
        intitule="Contrôle chapitre 1",
        date=date(2026, 1, 10),
        coefficient=2.0,
        saisi_par=user,
    )
    db.session.add(controle)
    db.session.commit()

    note1 = Note(eleve=eleve1, controle=controle, valeur=15, saisi_par=user)
    note2 = Note(eleve=eleve2, controle=controle, valeur=9, saisi_par=user)
    db.session.add_all([note1, note2])
    db.session.commit()

    assert controle.trimestre_id is None
    assert {n.id for n in controle.notes} == {note1.id, note2.id}
    assert note1.controle.intitule == "Contrôle chapitre 1"


def test_note_existante_sans_controle_reste_valide(app):
    """Les Note créées à l'ancienne façon (sans controle_id) continuent de fonctionner."""
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Prof", email="prof3@ecole.test", role="professeur")
    user.set_password("password123")
    db.session.add_all([classe, eleve, matiere, user])
    db.session.commit()

    note = Note(
        eleve=eleve, matiere=matiere, valeur=12, trimestre="T1", saisi_par=user
    )
    db.session.add(note)
    db.session.commit()

    assert note.controle_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `ImportError: cannot import name 'Controle' from 'app.models'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/models.py` (after `Notice`):

```python
class Controle(db.Model):
    __tablename__ = "controles"

    id = db.Column(db.Integer, primary_key=True)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    intitule = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    coefficient = db.Column(db.Float, nullable=False, default=1.0)
    trimestre_id = db.Column(db.Integer, db.ForeignKey("trimestres.id"), nullable=True)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    matiere = db.relationship("Matiere")
    classe = db.relationship("Classe")
    trimestre = db.relationship("Trimestre", back_populates="controles")
    saisi_par = db.relationship("User")
    notes = db.relationship("Note", back_populates="controle")
```

Modify the `Note` class in `app/models.py` — add the new column and relationship without
touching the existing `matiere_id`, `trimestre`, or `date` columns:

```python
    controle_id = db.Column(db.Integer, db.ForeignKey("controles.id"), nullable=True)
```

(insert this line right after `saisi_par_id` in `Note`), and add below the existing
`saisi_par = db.relationship("User")` line in `Note`:

```python
    controle = db.relationship("Controle", back_populates="notes")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Run the full existing suite to confirm no regression**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: all tests pass (8 previously-existing + 9 new = 17)

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add Controle model and Note.controle_id column"
```

---

### Task 6: `Presence` model

**Files:**
- Modify: `app/models.py` (add class; add `presences` relationship to `Eleve`)
- Test: `tests/test_models_fondations.py`

**Interfaces:**
- Consumes: `Eleve`, `User` (existing).
- Produces: `app.models.Presence` with columns `id`, `eleve_id` (FK), `date` (date), `statut`
  (str: `"present"`/`"absent"`/`"retard"`), `heure_arrivee` (time, nullable), `justifie` (bool,
  default `False`), `motif` (str, nullable), `saisi_par_id` (FK). Table name `presences`.
  Unique constraint `uq_presence_eleve_date` on `(eleve_id, date)`. `Eleve.presences`
  relationship (cascade delete-orphan). The existing `Absence` model and
  `app/surveillant/routes.py` (which reads/writes `Absence`) are untouched and keep working.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_fondations.py`:

```python
from datetime import time

from sqlalchemy.exc import IntegrityError

from app.models import Presence


def test_presence_creation(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    user = User(nom="Surveillant", email="surv2@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, user])
    db.session.commit()

    presence = Presence(
        eleve=eleve,
        date=date(2026, 1, 12),
        statut="retard",
        heure_arrivee=time(8, 15),
        saisi_par=user,
    )
    db.session.add(presence)
    db.session.commit()

    assert eleve.presences == [presence]
    assert presence.justifie is False


def test_presence_unique_par_eleve_et_date(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    user = User(nom="Surveillant", email="surv3@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, user])
    db.session.commit()

    db.session.add(
        Presence(eleve=eleve, date=date(2026, 1, 12), statut="present", saisi_par=user)
    )
    db.session.commit()

    db.session.add(
        Presence(eleve=eleve, date=date(2026, 1, 12), statut="absent", saisi_par=user)
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
```

Add `import pytest` to the top of `tests/test_models_fondations.py` if not already present.

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `ImportError: cannot import name 'Presence' from 'app.models'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/models.py` (after `Controle`):

```python
class Presence(db.Model):
    __tablename__ = "presences"
    __table_args__ = (
        db.UniqueConstraint("eleve_id", "date", name="uq_presence_eleve_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    statut = db.Column(db.String(20), nullable=False)  # 'present', 'absent' ou 'retard'
    heure_arrivee = db.Column(db.Time, nullable=True)
    justifie = db.Column(db.Boolean, nullable=False, default=False)
    motif = db.Column(db.String(255), nullable=True)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    eleve = db.relationship("Eleve", back_populates="presences")
    saisi_par = db.relationship("User")
```

Modify the `Eleve` class to add the relationship (next to `notices`):

```python
    presences = db.relationship(
        "Presence", back_populates="eleve", cascade="all, delete-orphan"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add Presence model"
```

---

### Task 7: `matiere_id` tagging on `InfractionMineure` and `IncidentMajeur`

**Files:**
- Modify: `app/models.py`
- Test: `tests/test_models_fondations.py`

**Interfaces:**
- Consumes: `Matiere` (existing), `InfractionMineure`, `IncidentMajeur` (existing).
- Produces: `InfractionMineure.matiere_id` (FK, nullable) + `InfractionMineure.matiere`
  relationship; `IncidentMajeur.matiere_id` (FK, nullable) + `IncidentMajeur.matiere`
  relationship. Existing rows and existing code in `app/surveillant/routes.py` that creates
  these without a `matiere` keep working unchanged (column defaults to `NULL`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models_fondations.py`:

```python
from app.models import IncidentMajeur, InfractionMineure, TypeInfractionMineure


def test_infraction_mineure_matiere_optionnelle(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    type_infraction = TypeInfractionMineure(libelle="Bavardage", points_deduits=1)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Surveillant", email="surv4@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, type_infraction, matiere, user])
    db.session.commit()

    sans_matiere = InfractionMineure(
        eleve=eleve, type_infraction=type_infraction, saisi_par=user
    )
    avec_matiere = InfractionMineure(
        eleve=eleve, type_infraction=type_infraction, matiere=matiere, saisi_par=user
    )
    db.session.add_all([sans_matiere, avec_matiere])
    db.session.commit()

    assert sans_matiere.matiere_id is None
    assert avec_matiere.matiere_id == matiere.id


def test_incident_majeur_matiere_optionnelle(app):
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    eleve = Eleve(nom="Dupont", prenom="Jean", classe=classe)
    matiere = Matiere(nom="Maths", coefficient=3)
    user = User(nom="Surveillant", email="surv5@ecole.test", role="surveillant")
    user.set_password("password123")
    db.session.add_all([classe, eleve, matiere, user])
    db.session.commit()

    incident = IncidentMajeur(
        eleve=eleve,
        description="Conflit en classe",
        gravite="moyenne",
        matiere=matiere,
        saisi_par=user,
    )
    db.session.add(incident)
    db.session.commit()

    assert incident.matiere_id == matiere.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: FAIL with `TypeError: 'matiere' is an invalid keyword argument for InfractionMineure`

- [ ] **Step 3: Write minimal implementation**

In `app/models.py`, modify `InfractionMineure` — add after `cycle_id`:

```python
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)
```

and after `cycle = db.relationship(...)`:

```python
    matiere = db.relationship("Matiere")
```

In `app/models.py`, modify `IncidentMajeur` — add after `saisi_par_id`:

```python
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)
```

and after `saisi_par = db.relationship("User")`:

```python
    matiere = db.relationship("Matiere")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_models_fondations.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Run the full existing suite to confirm no regression**

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: all tests pass (8 previously-existing + 13 new = 21)

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/test_models_fondations.py
git commit -m "feat: add optional matiere tagging to InfractionMineure and IncidentMajeur"
```

---

### Task 8: `app/permissions.py` — capacity predicates

**Files:**
- Create: `app/permissions.py`
- Test: `tests/test_permissions.py` (new file)

**Interfaces:**
- Consumes: `User.is_directeur()`, `User.is_surveillant()`, `User.is_professeur()`,
  `User.peut_saisir(matiere_id, classe_id)` (all existing on `app.models.User`).
- Produces (used by later phases' routes/templates):
  - `peut_voir_admin(user) -> bool`
  - `peut_gerer_presences(user) -> bool`
  - `peut_gerer_vie_scolaire(user) -> bool`
  - `peut_generer_rapports(user) -> bool`
  - `peut_gerer_controle(user, matiere_id, classe_id) -> bool`

- [ ] **Step 1: Write the failing test**

Create `tests/test_permissions.py`:

```python
from app.extensions import db
from app.models import AffectationProf, Classe, Matiere, User
from app.permissions import (
    peut_gerer_controle,
    peut_gerer_presences,
    peut_gerer_vie_scolaire,
    peut_generer_rapports,
    peut_voir_admin,
)


def _make_user(role):
    user = User(nom=role.capitalize(), email=f"{role}@ecole.test", role=role)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def test_peut_voir_admin_seulement_directeur(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_voir_admin(directeur) is True
    assert peut_voir_admin(surveillant) is False
    assert peut_voir_admin(professeur) is False


def test_peut_gerer_presences_directeur_et_surveillant(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_gerer_presences(directeur) is True
    assert peut_gerer_presences(surveillant) is True
    assert peut_gerer_presences(professeur) is False


def test_peut_gerer_vie_scolaire_directeur_et_surveillant(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_gerer_vie_scolaire(directeur) is True
    assert peut_gerer_vie_scolaire(surveillant) is True
    assert peut_gerer_vie_scolaire(professeur) is False


def test_peut_generer_rapports_directeur_et_surveillant(app):
    directeur = _make_user("directeur")
    surveillant = _make_user("surveillant")
    professeur = _make_user("professeur")

    assert peut_generer_rapports(directeur) is True
    assert peut_generer_rapports(surveillant) is True
    assert peut_generer_rapports(professeur) is False


def test_peut_gerer_controle_professeur_seulement_ses_affectations(app):
    professeur = _make_user("professeur")
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    maths = Matiere(nom="Maths", coefficient=3)
    sport = Matiere(nom="Sport", coefficient=1)
    db.session.add_all([classe, maths, sport])
    db.session.commit()
    db.session.add(
        AffectationProf(professeur_id=professeur.id, matiere_id=maths.id, classe_id=classe.id)
    )
    db.session.commit()

    assert peut_gerer_controle(professeur, maths.id, classe.id) is True
    assert peut_gerer_controle(professeur, sport.id, classe.id) is False


def test_peut_gerer_controle_directeur_toujours_vrai(app):
    directeur = _make_user("directeur")
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    maths = Matiere(nom="Maths", coefficient=3)
    db.session.add_all([classe, maths])
    db.session.commit()

    assert peut_gerer_controle(directeur, maths.id, classe.id) is True


def test_peut_gerer_controle_surveillant_toujours_faux(app):
    surveillant = _make_user("surveillant")
    classe = Classe(nom="6A", annee_scolaire="2025-2026")
    maths = Matiere(nom="Maths", coefficient=3)
    db.session.add_all([classe, maths])
    db.session.commit()

    assert peut_gerer_controle(surveillant, maths.id, classe.id) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_permissions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.permissions'`

- [ ] **Step 3: Write minimal implementation**

Create `app/permissions.py`:

```python
"""Prédicats de capacité utilisés par les routes (garde 403) et les templates
(affichage conditionnel des actions). Aucune règle de permission ne doit être
dupliquée ailleurs dans l'application.
"""


def peut_voir_admin(user):
    return user.is_directeur()


def peut_gerer_presences(user):
    return user.is_directeur() or user.is_surveillant()


def peut_gerer_vie_scolaire(user):
    return user.is_directeur() or user.is_surveillant()


def peut_generer_rapports(user):
    return user.is_directeur() or user.is_surveillant()


def peut_gerer_controle(user, matiere_id, classe_id):
    return user.peut_saisir(matiere_id, classe_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_permissions.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add app/permissions.py tests/test_permissions.py
git commit -m "feat: add app/permissions.py capacity predicates"
```

---

### Task 9: `app/periodes.py` — `resoudre_periode` helper

**Files:**
- Create: `app/periodes.py`
- Test: `tests/test_periodes.py` (new file)

**Interfaces:**
- Consumes: `CycleDiscipline` (existing), `Trimestre` (Task 2), `AnneeScolaire` (Task 1).
- Produces (used by later phases' list routes for every period filter selector):
  - `PRESETS_PERIODE = ("cycle", "mois", "trimestre", "annee")`
  - `resoudre_periode(preset, reference=None) -> tuple[date, date]` — raises `ValueError` with
    a French message if `preset` is not one of `PRESETS_PERIODE`, or if the data needed to
    resolve it doesn't exist yet (no open cycle / no trimestre covering the date / no active
    année scolaire).

- [ ] **Step 1: Write the failing test**

Create `tests/test_periodes.py`:

```python
from datetime import date

import pytest

from app.extensions import db
from app.models import AnneeScolaire, CycleDiscipline, Trimestre
from app.periodes import resoudre_periode


def test_resoudre_periode_cycle_utilise_le_cycle_ouvert(app):
    cycle_ferme = CycleDiscipline(
        date_debut=date(2025, 12, 1),
        date_fin=date(2025, 12, 15),
        date_cloture=date(2025, 12, 16),
    )
    cycle_ouvert = CycleDiscipline(date_debut=date(2026, 1, 1), date_fin=date(2026, 1, 15))
    db.session.add_all([cycle_ferme, cycle_ouvert])
    db.session.commit()

    debut, fin = resoudre_periode("cycle")

    assert (debut, fin) == (date(2026, 1, 1), date(2026, 1, 15))


def test_resoudre_periode_cycle_sans_cycle_ouvert_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("cycle")


def test_resoudre_periode_mois_utilise_le_mois_de_reference(app):
    debut, fin = resoudre_periode("mois", reference=date(2026, 2, 10))

    assert (debut, fin) == (date(2026, 2, 1), date(2026, 2, 28))


def test_resoudre_periode_trimestre_trouve_le_trimestre_couvrant(app):
    annee = AnneeScolaire(
        libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30)
    )
    db.session.add(annee)
    db.session.commit()
    t1 = Trimestre(annee=annee, code="T1", date_debut=date(2025, 9, 1), date_fin=date(2025, 12, 19))
    t2 = Trimestre(annee=annee, code="T2", date_debut=date(2026, 1, 5), date_fin=date(2026, 3, 20))
    db.session.add_all([t1, t2])
    db.session.commit()

    debut, fin = resoudre_periode("trimestre", reference=date(2026, 2, 1))

    assert (debut, fin) == (date(2026, 1, 5), date(2026, 3, 20))


def test_resoudre_periode_trimestre_sans_couverture_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("trimestre", reference=date(2026, 2, 1))


def test_resoudre_periode_annee_utilise_lannee_active(app):
    inactive = AnneeScolaire(
        libelle="2024-2025", date_debut=date(2024, 9, 1), date_fin=date(2025, 6, 30)
    )
    active = AnneeScolaire(
        libelle="2025-2026", date_debut=date(2025, 9, 1), date_fin=date(2026, 6, 30), active=True
    )
    db.session.add_all([inactive, active])
    db.session.commit()

    debut, fin = resoudre_periode("annee")

    assert (debut, fin) == (date(2025, 9, 1), date(2026, 6, 30))


def test_resoudre_periode_annee_sans_annee_active_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("annee")


def test_resoudre_periode_preset_inconnu_leve_erreur(app):
    with pytest.raises(ValueError):
        resoudre_periode("semaine")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_periodes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.periodes'`

- [ ] **Step 3: Write minimal implementation**

Create `app/periodes.py`:

```python
"""Résolution des vues par période (cycle / mois / trimestre / année) partagée
par tous les onglets de liste (présences, notes, vie scolaire, rapports)."""

import calendar
from datetime import date

from app.models import AnneeScolaire, CycleDiscipline, Trimestre

PRESETS_PERIODE = ("cycle", "mois", "trimestre", "annee")


def resoudre_periode(preset, reference=None):
    reference = reference or date.today()

    if preset == "cycle":
        cycle = (
            CycleDiscipline.query.filter_by(date_cloture=None)
            .order_by(CycleDiscipline.date_debut.desc())
            .first()
        )
        if not cycle:
            raise ValueError("Aucun cycle de discipline actif.")
        return cycle.date_debut, cycle.date_fin

    if preset == "mois":
        premier_jour = reference.replace(day=1)
        dernier_jour_numero = calendar.monthrange(reference.year, reference.month)[1]
        dernier_jour = reference.replace(day=dernier_jour_numero)
        return premier_jour, dernier_jour

    if preset == "trimestre":
        trimestre = Trimestre.query.filter(
            Trimestre.date_debut <= reference, Trimestre.date_fin >= reference
        ).first()
        if not trimestre:
            raise ValueError("Aucun trimestre ne couvre cette date.")
        return trimestre.date_debut, trimestre.date_fin

    if preset == "annee":
        annee = AnneeScolaire.query.filter_by(active=True).first()
        if not annee:
            raise ValueError("Aucune année scolaire active.")
        return annee.date_debut, annee.date_fin

    raise ValueError(f"Période inconnue : {preset}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_periodes.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add app/periodes.py tests/test_periodes.py
git commit -m "feat: add resoudre_periode helper for period-based filtering"
```

---

### Task 10: Real-database migration + full regression check

**Files:**
- Create: `migrations/versions/<auto-generated-hash>_fondations_refonte.py` (via
  `flask db migrate`, then hand-reviewed)
- No test file — this task verifies the real SQLite database (`ecole.db`) and the full
  existing test suite, it doesn't add new pytest tests.

**Interfaces:**
- Consumes: every model added/modified in Tasks 1–7.
- Produces: an applied Alembic migration bringing `instance`/`ecole.db`'s schema in sync with
  `app/models.py`, so `flask db upgrade` (documented in `README.md`) works for anyone pulling
  this branch.

- [ ] **Step 1: Generate the migration**

Set the Flask app env var and autogenerate (Windows cmd shown; adapt per shell as noted in
Global Constraints):

```bash
set FLASK_APP=run.py
venv\Scripts\flask db migrate -m "Fondations refonte : nouveaux modeles et colonnes additives"
```

- [ ] **Step 2: Review the generated migration file**

Open the new file under `migrations/versions/`. Confirm it contains, and only contains:
- `op.create_table` for `annees_scolaires`, `trimestres`, `contacts_parents`, `notices`,
  `controles`, `presences`
- `op.add_column` for `notes.controle_id`, `infractions_mineures.matiere_id`,
  `incidents_majeurs.matiere_id`
- The unique constraint `uq_presence_eleve_date` on `presences`
- No `op.drop_table` or `op.drop_column` anywhere (this phase is additive-only — if Alembic
  proposes dropping or altering anything on `absences` or existing `notes` columns, that's a
  bug in this task: stop and re-check the model diffs from Tasks 1–7 before proceeding)

- [ ] **Step 3: Apply the migration**

```bash
venv\Scripts\flask db upgrade
```

Expected: command exits without error.

- [ ] **Step 4: Verify the app still boots**

```bash
venv/Scripts/python.exe -c "from app import create_app; app = create_app(); print('OK')"
```

Expected output: `OK` (no import or app-factory errors).

- [ ] **Step 5: Run the full test suite**

```bash
venv/Scripts/python.exe -m pytest -q
```

Expected: all tests pass (8 original + 13 in `test_models_fondations.py` + 7 in
`test_permissions.py` + 8 in `test_periodes.py` = 36 total).

- [ ] **Step 6: Commit**

```bash
git add migrations/versions/
git commit -m "chore: apply Fondations refonte migration to ecole.db schema"
```

---

## End-of-phase checklist

- [ ] All 10 tasks committed individually.
- [ ] `venv/Scripts/python.exe -m pytest -q` passes with 36 tests, 0 failures.
- [ ] `app/directeur/`, `app/professeur/`, `app/surveillant/`, and every file under
  `app/templates/` are untouched (`git diff main --stat` shows no changes there).
- [ ] The application still runs and behaves identically for all three roles
  (`python run.py`, log in as each role, confirm existing dashboards/forms work as before).
