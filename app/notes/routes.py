from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from app.decorators import role_required
from app.extensions import db
from app.models import Classe, Controle, Eleve, Matiere, Note, Trimestre

notes_bp = Blueprint("notes", __name__)


@notes_bp.before_request
@login_required
@role_required("directeur", "professeur")
def guard():
    pass


@notes_bp.route("/notes")
def liste():
    classe_id = request.args.get("classe_id", type=int)
    matiere_id = request.args.get("matiere_id", type=int)
    trimestre_id = request.args.get("trimestre_id", type=int)

    classes = Classe.query.order_by(Classe.nom).all()
    trimestres = Trimestre.query.order_by(Trimestre.date_debut).all()

    if current_user.is_professeur():
        paires = current_user.matieres_classes_autorisees()
        matiere_ids = {mid for mid, _ in paires}
        matieres = Matiere.query.filter(Matiere.id.in_(matiere_ids)).order_by(Matiere.nom).all()
    else:
        matieres = Matiere.query.order_by(Matiere.nom).all()

    query = Controle.query
    if classe_id:
        query = query.filter_by(classe_id=classe_id)
    if matiere_id:
        query = query.filter_by(matiere_id=matiere_id)
    if trimestre_id:
        query = query.filter_by(trimestre_id=trimestre_id)

    if current_user.is_professeur():
        paires = current_user.matieres_classes_autorisees()
        if paires:
            query = query.filter(
                or_(*[and_(Controle.matiere_id == mid, Controle.classe_id == cid) for mid, cid in paires])
            )
        else:
            query = query.filter(Controle.id == -1)

    controles = query.order_by(Controle.date.desc()).all()

    return render_template(
        "notes/liste.html",
        controles=controles,
        classes=classes,
        matieres=matieres,
        trimestres=trimestres,
        classe_id=classe_id,
        matiere_id=matiere_id,
        trimestre_id=trimestre_id,
    )


@notes_bp.route("/notes/controle/nouveau", methods=["GET", "POST"])
def controle_nouveau():
    classes = Classe.query.order_by(Classe.nom).all()
    trimestres = Trimestre.query.order_by(Trimestre.date_debut).all()

    if current_user.is_professeur():
        paires = current_user.matieres_classes_autorisees()
        matiere_ids = {mid for mid, _ in paires}
        matieres = Matiere.query.filter(Matiere.id.in_(matiere_ids)).order_by(Matiere.nom).all()
    else:
        matieres = Matiere.query.order_by(Matiere.nom).all()

    if request.method == "POST":
        matiere_id = request.form.get("matiere_id", type=int)
        classe_id = request.form.get("classe_id", type=int)
        intitule = request.form.get("intitule", "").strip()
        date_str = request.form.get("date", date.today().isoformat())
        coefficient = request.form.get("coefficient", type=float) or 1.0
        trimestre_id = request.form.get("trimestre_id", type=int) or None

        if not current_user.peut_saisir(matiere_id, classe_id):
            abort(403)
        if not intitule:
            flash("L'intitulé est obligatoire.", "danger")
        else:
            try:
                d = date.fromisoformat(date_str)
            except ValueError:
                d = date.today()
            controle = Controle(
                matiere_id=matiere_id,
                classe_id=classe_id,
                intitule=intitule,
                date=d,
                coefficient=coefficient,
                trimestre_id=trimestre_id,
                saisi_par_id=current_user.id,
            )
            db.session.add(controle)
            db.session.commit()
            flash(f"Contrôle « {intitule} » créé.", "success")
            return redirect(url_for("notes.controle_saisie", controle_id=controle.id))

    return render_template(
        "notes/controle_form.html",
        classes=classes,
        matieres=matieres,
        trimestres=trimestres,
        today=date.today().isoformat(),
    )


@notes_bp.route("/notes/controle/<int:controle_id>/saisie", methods=["GET", "POST"])
def controle_saisie(controle_id):
    controle = db.session.get(Controle, controle_id) or abort(404)
    if not current_user.peut_saisir(controle.matiere_id, controle.classe_id):
        abort(403)

    eleves = sorted(controle.classe.eleves, key=lambda e: e.nom)
    notes_par_eleve = {
        n.eleve_id: n for n in Note.query.filter_by(controle_id=controle_id).all()
    }

    if request.method == "POST":
        for eleve in eleves:
            valeur_str = request.form.get(f"note_{eleve.id}", "").strip()
            if not valeur_str:
                continue
            try:
                valeur = float(valeur_str.replace(",", "."))
            except ValueError:
                continue
            if not (0 <= valeur <= 20):
                continue

            existing = notes_par_eleve.get(eleve.id)
            if existing:
                existing.valeur = valeur
            else:
                db.session.add(Note(
                    eleve_id=eleve.id,
                    controle_id=controle_id,
                    valeur=valeur,
                    saisi_par_id=current_user.id,
                ))
        db.session.commit()
        flash("Notes enregistrées.", "success")
        return redirect(url_for("notes.controle_saisie", controle_id=controle_id))

    notes_par_eleve = {
        n.eleve_id: n for n in Note.query.filter_by(controle_id=controle_id).all()
    }
    return render_template(
        "notes/saisie.html",
        controle=controle,
        eleves=eleves,
        notes_par_eleve=notes_par_eleve,
    )


@notes_bp.route("/notes/controle/<int:controle_id>/supprimer", methods=["POST"])
def controle_supprimer(controle_id):
    controle = db.session.get(Controle, controle_id) or abort(404)
    if not current_user.peut_saisir(controle.matiere_id, controle.classe_id):
        abort(403)
    db.session.delete(controle)
    db.session.commit()
    flash("Contrôle supprimé.", "success")
    return redirect(url_for("notes.liste"))
