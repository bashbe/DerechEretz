from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import role_required
from app.extensions import db
from app.models import Classe, Matiere, Note

professeur_bp = Blueprint("professeur", __name__)


@professeur_bp.before_request
@login_required
@role_required("professeur")
def guard():
    pass


@professeur_bp.route("/notes")
def saisie_notes():
    matiere_id = request.args.get("matiere_id", type=int)
    classe_id = request.args.get("classe_id", type=int)
    trimestre = request.args.get("trimestre", "T1")

    if not matiere_id or not classe_id:
        return redirect(url_for("main.dashboard_professeur"))

    if not current_user.peut_saisir(matiere_id, classe_id):
        abort(403)

    classe = db.session.get(Classe, classe_id) or abort(404)
    matiere = db.session.get(Matiere, matiere_id) or abort(404)

    eleves = sorted(classe.eleves, key=lambda e: e.nom)
    notes_par_eleve = {
        eleve.id: Note.query.filter_by(
            eleve_id=eleve.id, matiere_id=matiere_id, trimestre=trimestre
        ).order_by(Note.date).all()
        for eleve in eleves
    }

    return render_template(
        "professeur/saisie_notes.html",
        classe=classe,
        matiere=matiere,
        trimestre=trimestre,
        eleves=eleves,
        notes_par_eleve=notes_par_eleve,
        today=date.today().isoformat(),
    )


@professeur_bp.route("/notes/enregistrer", methods=["POST"])
def notes_enregistrer():
    matiere_id = request.form.get("matiere_id", type=int)
    classe_id = request.form.get("classe_id", type=int)
    trimestre = request.form.get("trimestre", "T1")

    if not current_user.peut_saisir(matiere_id, classe_id):
        abort(403)

    nb_ajoutees = 0
    for cle, valeur in request.form.items():
        if not cle.startswith("note_") or not valeur.strip():
            continue
        eleve_id = int(cle.removeprefix("note_"))
        try:
            valeur_note = float(valeur.replace(",", "."))
        except ValueError:
            continue
        if not (0 <= valeur_note <= 20):
            continue
        note = Note(
            eleve_id=eleve_id,
            matiere_id=matiere_id,
            valeur=valeur_note,
            trimestre=trimestre,
            saisi_par_id=current_user.id,
        )
        db.session.add(note)
        nb_ajoutees += 1

    db.session.commit()
    flash(f"{nb_ajoutees} note(s) enregistrée(s).", "success")
    return redirect(
        url_for(
            "professeur.saisie_notes",
            matiere_id=matiere_id,
            classe_id=classe_id,
            trimestre=trimestre,
        )
    )


@professeur_bp.route("/notes/<int:note_id>/supprimer", methods=["POST"])
def note_supprimer(note_id):
    note = db.session.get(Note, note_id) or abort(404)
    if not current_user.peut_saisir(note.matiere_id, note.eleve.classe_id):
        abort(403)
    matiere_id, classe_id, trimestre = note.matiere_id, note.eleve.classe_id, note.trimestre
    db.session.delete(note)
    db.session.commit()
    flash("Note supprimée.", "success")
    return redirect(
        url_for(
            "professeur.saisie_notes",
            matiere_id=matiere_id,
            classe_id=classe_id,
            trimestre=trimestre,
        )
    )
