from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import role_required
from app.extensions import db
from app.models import Absence, Classe, Eleve, IncidentMajeur, TypeInfractionMineure
from app.services import appliquer_infraction_mineure
from app.surveillant.forms import IncidentMajeurForm, InfractionMineureForm

surveillant_bp = Blueprint("surveillant", __name__)


@surveillant_bp.before_request
@login_required
@role_required("surveillant")
def guard():
    pass


@surveillant_bp.route("/absences")
def absences_du_jour():
    classe_id = request.args.get("classe_id", type=int)
    classes = Classe.query.order_by(Classe.nom).all()
    eleves = []
    absences_existantes = {}
    if classe_id:
        classe = db.session.get(Classe, classe_id) or abort(404)
        eleves = sorted(classe.eleves, key=lambda e: e.nom)
        for absence in Absence.query.filter_by(date=date.today()).all():
            if absence.eleve_id in [e.id for e in eleves]:
                absences_existantes[absence.eleve_id] = absence

    return render_template(
        "surveillant/absences.html",
        classes=classes,
        classe_id=classe_id,
        eleves=eleves,
        absences_existantes=absences_existantes,
        today=date.today().isoformat(),
    )


@surveillant_bp.route("/absences/enregistrer", methods=["POST"])
def absences_enregistrer():
    classe_id = request.form.get("classe_id", type=int)
    nb = 0
    for eleve in Eleve.query.filter_by(classe_id=classe_id).all():
        type_ = request.form.get(f"type_{eleve.id}")
        if not type_:
            continue
        statut = request.form.get(f"statut_{eleve.id}", "injustifie")
        motif = request.form.get(f"motif_{eleve.id}", "").strip()
        absence = Absence(
            eleve_id=eleve.id,
            date=date.today(),
            type=type_,
            statut=statut,
            motif=motif or None,
            saisi_par_id=current_user.id,
        )
        db.session.add(absence)
        nb += 1
    db.session.commit()
    flash(f"{nb} absence(s)/retard(s) enregistré(s) pour aujourd'hui.", "success")
    return redirect(url_for("surveillant.absences_du_jour", classe_id=classe_id))


@surveillant_bp.route("/infractions", methods=["GET", "POST"])
def infractions():
    form = InfractionMineureForm()
    form.eleve_id.choices = [
        (e.id, f"{e.nom_complet} ({e.classe.nom})") for e in Eleve.query.join(Classe).order_by(Classe.nom, Eleve.nom)
    ]
    form.type_infraction_id.choices = [
        (t.id, f"{t.libelle} (-{t.points_deduits} pts)")
        for t in TypeInfractionMineure.query.filter_by(actif=True).order_by(TypeInfractionMineure.libelle)
    ]

    if form.validate_on_submit():
        eleve = db.session.get(Eleve, form.eleve_id.data) or abort(404)
        type_infraction = db.session.get(TypeInfractionMineure, form.type_infraction_id.data) or abort(404)
        appliquer_infraction_mineure(eleve, type_infraction, current_user)
        flash(
            f"Infraction enregistrée pour {eleve.nom_complet} : solde {eleve.points_vie_scolaire}/20.",
            "success",
        )
        return redirect(url_for("surveillant.infractions"))

    return render_template("surveillant/infractions.html", form=form)


@surveillant_bp.route("/incidents", methods=["GET", "POST"])
def incidents():
    form = IncidentMajeurForm()
    form.eleve_id.choices = [
        (e.id, f"{e.nom_complet} ({e.classe.nom})") for e in Eleve.query.join(Classe).order_by(Classe.nom, Eleve.nom)
    ]

    if form.validate_on_submit():
        eleve = db.session.get(Eleve, form.eleve_id.data) or abort(404)
        incident = IncidentMajeur(
            eleve=eleve,
            description=form.description.data,
            gravite=form.gravite.data,
            sanction=form.sanction.data or None,
            saisi_par_id=current_user.id,
        )
        db.session.add(incident)
        db.session.commit()
        flash(f"Incident enregistré pour {eleve.nom_complet}.", "success")
        return redirect(url_for("surveillant.incidents"))

    liste = IncidentMajeur.query.order_by(IncidentMajeur.date.desc()).limit(20).all()
    return render_template("surveillant/incidents.html", form=form, incidents=liste)
