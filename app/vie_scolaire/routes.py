import calendar
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import role_required
from app.extensions import db
from app.models import (
    Classe,
    CycleDiscipline,
    Eleve,
    IncidentMajeur,
    InfractionMineure,
    Matiere,
    Notice,
    TypeInfractionMineure,
)
from app.periodes import resoudre_periode
from app.services import appliquer_infraction_mineure

vie_scolaire_bp = Blueprint("vie_scolaire", __name__)


@vie_scolaire_bp.before_request
@login_required
@role_required("directeur", "surveillant")
def guard():
    pass


def _periode_fallback(preset):
    try:
        return resoudre_periode(preset), preset
    except ValueError:
        today = date.today()
        d = (today.replace(day=1), today.replace(day=calendar.monthrange(today.year, today.month)[1]))
        return d, "mois"


@vie_scolaire_bp.route("/vie-scolaire")
def liste():
    preset = request.args.get("periode", "mois")
    eleve_id = request.args.get("eleve_id", type=int)
    classe_id = request.args.get("classe_id", type=int)

    (date_debut, date_fin), preset = _periode_fallback(preset)

    classes = Classe.query.order_by(Classe.nom).all()
    eleves_query = Eleve.query.join(Classe).order_by(Classe.nom, Eleve.nom)
    if classe_id:
        eleves_query = eleves_query.filter(Eleve.classe_id == classe_id)
    eleves = eleves_query.all()

    infraction_q = InfractionMineure.query.filter(
        InfractionMineure.date >= date_debut, InfractionMineure.date <= date_fin
    )
    incident_q = IncidentMajeur.query.filter(
        IncidentMajeur.date >= date_debut, IncidentMajeur.date <= date_fin
    )
    notice_q = Notice.query.filter(
        Notice.date >= date_debut, Notice.date <= date_fin
    )

    if eleve_id:
        infraction_q = infraction_q.filter_by(eleve_id=eleve_id)
        incident_q = incident_q.filter_by(eleve_id=eleve_id)
        notice_q = notice_q.filter_by(eleve_id=eleve_id)
    elif classe_id:
        ids = [e.id for e in eleves]
        infraction_q = infraction_q.filter(InfractionMineure.eleve_id.in_(ids))
        incident_q = incident_q.filter(IncidentMajeur.eleve_id.in_(ids))
        notice_q = notice_q.filter(Notice.eleve_id.in_(ids))

    infractions = infraction_q.order_by(InfractionMineure.date.desc()).all()
    incidents = incident_q.order_by(IncidentMajeur.date.desc()).all()
    notices = notice_q.order_by(Notice.date.desc()).all()

    events = (
        [("infraction", i) for i in infractions]
        + [("incident", i) for i in incidents]
        + [("notice", n) for n in notices]
    )
    events.sort(key=lambda x: x[1].date, reverse=True)

    types_infractions = TypeInfractionMineure.query.filter_by(actif=True).order_by(TypeInfractionMineure.libelle).all()
    matieres = Matiere.query.order_by(Matiere.nom).all()
    cycle_actif = CycleDiscipline.query.filter_by(date_cloture=None).first()

    return render_template(
        "vie_scolaire/liste.html",
        events=events,
        classes=classes,
        eleves=eleves,
        types_infractions=types_infractions,
        matieres=matieres,
        cycle_actif=cycle_actif,
        preset=preset,
        date_debut=date_debut,
        date_fin=date_fin,
        classe_id=classe_id,
        eleve_id=eleve_id,
        nb_infractions=len(infractions),
        nb_incidents=len(incidents),
        nb_notices=len(notices),
    )


@vie_scolaire_bp.route("/vie-scolaire/infraction", methods=["POST"])
def infraction_ajouter():
    eleve_id = request.form.get("eleve_id", type=int)
    type_id = request.form.get("type_infraction_id", type=int)
    matiere_id = request.form.get("matiere_id", type=int) or None

    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    type_infraction = db.session.get(TypeInfractionMineure, type_id) or abort(404)

    infraction = appliquer_infraction_mineure(eleve, type_infraction, current_user)
    if matiere_id:
        infraction.matiere_id = matiere_id
        db.session.commit()

    flash(f"Infraction enregistrée pour {eleve.nom_complet}. Solde : {eleve.points_vie_scolaire}/20.", "success")
    return redirect(url_for("vie_scolaire.liste"))


@vie_scolaire_bp.route("/vie-scolaire/incident", methods=["POST"])
def incident_ajouter():
    eleve_id = request.form.get("eleve_id", type=int)
    description = request.form.get("description", "").strip()
    gravite = request.form.get("gravite", "moyenne")
    sanction = request.form.get("sanction", "").strip() or None
    matiere_id = request.form.get("matiere_id", type=int) or None

    if gravite not in ("mineure_grave", "moyenne", "majeure"):
        gravite = "moyenne"

    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    if not description:
        flash("La description est obligatoire.", "danger")
        return redirect(url_for("vie_scolaire.liste"))

    incident = IncidentMajeur(
        eleve=eleve,
        description=description,
        gravite=gravite,
        sanction=sanction,
        matiere_id=matiere_id,
        saisi_par_id=current_user.id,
    )
    db.session.add(incident)
    db.session.commit()
    flash(f"Incident enregistré pour {eleve.nom_complet}.", "success")
    return redirect(url_for("vie_scolaire.liste"))


@vie_scolaire_bp.route("/vie-scolaire/notice", methods=["POST"])
def notice_ajouter():
    eleve_id = request.form.get("eleve_id", type=int)
    titre = request.form.get("titre", "").strip()
    contenu = request.form.get("contenu", "").strip()
    matiere_id = request.form.get("matiere_id", type=int) or None

    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    if not titre or not contenu:
        flash("Le titre et le contenu sont obligatoires.", "danger")
        return redirect(url_for("vie_scolaire.liste"))

    notice = Notice(
        eleve=eleve,
        titre=titre,
        contenu=contenu,
        matiere_id=matiere_id,
        saisi_par_id=current_user.id,
    )
    db.session.add(notice)
    db.session.commit()
    flash(f"Notice enregistrée pour {eleve.nom_complet}.", "success")
    return redirect(url_for("vie_scolaire.liste"))
