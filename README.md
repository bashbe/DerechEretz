# Gestion École — Flask

## Installation

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Base de données

```bash
set FLASK_APP=run.py
flask db upgrade
flask seed-directeur directeur@mon-ecole.fr motdepasse123 --nom "Nom du directeur"
```

Note : évitez les domaines réservés (`.test`, `.example`, `.invalid`, `.localhost`) pour les emails, ils sont rejetés par le validateur.

## Lancer l'application

```bash
python run.py
```

Puis se connecter sur http://127.0.0.1:5000 avec le compte créé par `seed-directeur`.

## Tests

```bash
pytest
```
