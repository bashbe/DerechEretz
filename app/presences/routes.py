import calendar
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import role_required
from app.extensions import db
from app.models import Classe, Eleve, Presence
from app.periodes import resoudre_periode

presences_bp = Blueprint("presences", __name__)


@presences_bp.before_request
@login_required
@role_required("directeur", "surveillant")
def guard():
    pass


@presences_bp.route("/presences")
def liste():
    preset = request.args.get("periode", "mois")
    classe_id = request.args.get("classe_id", type=int)

    try:
        date_debut, date_fin = resoudre_periode(preset)
    except ValueError:
        preset = "mois"
        today = date.today()
        date_debut = today.replace(day=1)
        date_fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    classes = Classe.query.order_by(Classe.nom).all()
    classe = db.session.get(Classe, classe_id) if classe_id else None

    if classe:
        eleve_ids = [e.id for e in classe.eleves]
        presences = (
            Presence.query
            .filter(
                Presence.eleve_id.in_(eleve_ids),
                Presence.date >= date_debut,
                Presence.date <= date_fin,
            )
            .order_by(Presence.date.desc())
            .all()
        )
    else:
        presences = (
            Presence.query
            .filter(Presence.date >= date_debut, Presence.date <= date_fin)
            .order_by(Presence.date.desc())
            .all()
        )

    nb_absences = sum(1 for p in presences if p.statut == "absent")
    nb_retards = sum(1 for p in presences if p.statut == "retard")
    nb_injustifies = sum(1 for p in presences if p.statut != "present" and not p.justifie)

    return render_template(
        "presences/liste.html",
        presences=presences,
        classes=classes,
        classe=classe,
        classe_id=classe_id,
        preset=preset,
        date_debut=date_debut,
        date_fin=date_fin,
        nb_absences=nb_absences,
        nb_retards=nb_retards,
        nb_injustifies=nb_injustifies,
    )


@presences_bp.route("/presences/appel")
def appel():
    classe_id = request.args.get("classe_id", type=int)
    date_str = request.args.get("date", date.today().isoformat())
    try:
        date_appel = date.fromisoformat(date_str)
    except ValueError:
        date_appel = date.today()

    classes = Classe.query.order_by(Classe.nom).all()
    classe = db.session.get(Classe, classe_id) if classe_id else None
    eleves = []
    presences_par_eleve = {}

    if classe:
        eleves = sorted(classe.eleves, key=lambda e: e.nom)
        for p in Presence.query.filter(
            Presence.eleve_id.in_([e.id for e in eleves]),
            Presence.date == date_appel,
        ).all():
            presences_par_eleve[p.eleve_id] = p

    return render_template(
        "presences/appel.html",
        classes=classes,
        classe=classe,
        classe_id=classe_id,
        date_appel=date_appel,
        eleves=eleves,
        presences_par_eleve=presences_par_eleve,
    )


@presences_bp.route("/presences/appel/enregistrer", methods=["POST"])
def appel_enregistrer():
    classe_id = request.form.get("classe_id", type=int)
    date_str = request.form.get("date", date.today().isoformat())
    try:
        date_appel = date.fromisoformat(date_str)
    except ValueError:
        date_appel = date.today()

    eleves = Eleve.query.filter_by(classe_id=classe_id).all()
    nb = 0

    for eleve in eleves:
        statut = request.form.get(f"statut_{eleve.id}")
        if not statut:
            continue
        justifie = request.form.get(f"justifie_{eleve.id}") == "1"
        motif = request.form.get(f"motif_{eleve.id}", "").strip() or None
        heure_str = request.form.get(f"heure_{eleve.id}", "").strip()
        heure_arrivee = None
        if heure_str:
            try:
                h, m = heure_str.split(":")
                from datetime import time as dtime
                heure_arrivee = dtime(int(h), int(m))
            except (ValueError, AttributeError):
                pass

        existing = Presence.query.filter_by(eleve_id=eleve.id, date=date_appel).first()
        if existing:
            existing.statut = statut
            existing.justifie = justifie
            existing.motif = motif
            existing.heure_arrivee = heure_arrivee
            existing.saisi_par_id = current_user.id
        else:
            db.session.add(Presence(
                eleve_id=eleve.id,
                date=date_appel,
                statut=statut,
                justifie=justifie,
                motif=motif,
                heure_arrivee=heure_arrivee,
                saisi_par_id=current_user.id,
            ))
        nb += 1

    db.session.commit()
    flash(f"{nb} entrée(s) de présence enregistrée(s).", "success")
    return redirect(url_for("presences.appel", classe_id=classe_id, date=date_appel.isoformat()))
