"""Onglet Vie scolaire : hub central des événements.

Création unifiée (tous types), liste filtrable par période et type, fiche
d'activité avec modification/suppression, raccourcis « appel du jour » et
« notes par contrôle ». L'accès est ouvert à tous les rôles connectés ;
chaque action est gardée par les prédicats de app/permissions.py.
"""

import calendar
from datetime import date, time

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import evenements
from app.extensions import db
from app.models import (
    Classe,
    Controle,
    Eleve,
    Matiere,
    Note,
    Presence,
    Trimestre,
    TypeInfractionMineure,
)
from app.periodes import resoudre_periode
from app.permissions import (
    peut_gerer_presences,
    peut_modifier_evenement,
    types_evenements_creables,
)

vie_scolaire_bp = Blueprint("vie_scolaire", __name__)


@vie_scolaire_bp.before_request
@login_required
def guard():
    pass


def _periode(preset):
    try:
        return resoudre_periode(preset), preset
    except ValueError:
        today = date.today()
        debut = today.replace(day=1)
        fin = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        return (debut, fin), "mois"


def _contexte_formulaire():
    """Données communes du formulaire unifié de création d'événement."""
    return {
        "classes": Classe.query.order_by(Classe.nom).all(),
        "matieres": Matiere.query.order_by(Matiere.nom).all(),
        "types_infractions": TypeInfractionMineure.query.filter_by(actif=True)
        .order_by(TypeInfractionMineure.libelle)
        .all(),
        "types_creables": types_evenements_creables(current_user),
        "libelles_types": evenements.LIBELLES,
        "today": date.today().isoformat(),
    }


def _parser_date(valeur, defaut=None):
    try:
        return date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return defaut or date.today()


def _parser_heure(valeur):
    if not valeur:
        return None
    try:
        h, m = valeur.split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        return None


def _donnees_depuis_form(form):
    """Extrait du POST unifié les données attendues par evenements.creer()."""
    valeur = form.get("valeur", "").strip().replace(",", ".")
    try:
        valeur = float(valeur) if valeur else None
    except ValueError:
        valeur = None
    return {
        "date": _parser_date(form.get("date")),
        "heure": _parser_heure(form.get("heure", "").strip()),
        "matiere_id": form.get("matiere_id", type=int) or None,
        # note
        "valeur": valeur,
        # observation
        "titre": form.get("titre", ""),
        "contenu": form.get("contenu", ""),
        # infraction mineure
        "type_infraction_id": form.get("type_infraction_id", type=int),
        # infraction majeure
        "gravite": form.get("gravite"),
        "description": form.get("description", ""),
        "sanction": form.get("sanction", ""),
        # présence
        "statut": form.get("statut"),
        "justifie": form.get("justifie") == "1",
        "motif": form.get("motif", ""),
    }


# ---------------------------------------------------------------------------
# Hub + création unifiée
# ---------------------------------------------------------------------------

@vie_scolaire_bp.route("/vie-scolaire")
def index():
    ctx = _contexte_formulaire()
    type_prefill = request.args.get("type")
    if type_prefill not in ctx["types_creables"]:
        type_prefill = None
    eleve_prefill = None
    eleve_id = request.args.get("eleve_id", type=int)
    if eleve_id:
        eleve_prefill = db.session.get(Eleve, eleve_id)
    return render_template(
        "vie_scolaire/index.html",
        type_prefill=type_prefill,
        eleve_prefill=eleve_prefill,
        peut_faire_appel=peut_gerer_presences(current_user),
        **ctx,
    )


@vie_scolaire_bp.route("/vie-scolaire/evenement", methods=["POST"])
def evenement_creer():
    type_evt = request.form.get("type")
    if type_evt not in types_evenements_creables(current_user):
        abort(403)

    cible = request.form.get("cible", "selection")
    if cible == "global":
        eleves = Eleve.query.all()
    elif cible == "classe":
        classe = db.session.get(Classe, request.form.get("classe_id", type=int) or 0)
        eleves = list(classe.eleves) if classe else []
    else:
        ids = request.form.getlist("eleves_ids", type=int)
        eleves = Eleve.query.filter(Eleve.id.in_(ids)).all() if ids else []

    if not eleves:
        flash("Sélectionnez au moins un élève (ou une classe).", "danger")
        return redirect(url_for("vie_scolaire.index", type=type_evt))

    donnees = _donnees_depuis_form(request.form)

    # Professeur : matière obligatoire, et affectation vérifiée pour chaque élève ciblé
    if current_user.is_professeur():
        if not donnees["matiere_id"]:
            flash("La matière est obligatoire.", "danger")
            return redirect(url_for("vie_scolaire.index", type=type_evt))
        for eleve in eleves:
            if not current_user.peut_saisir(donnees["matiere_id"], eleve.classe_id):
                abort(403)

    try:
        crees = evenements.creer(type_evt, eleves, current_user, donnees)
    except ValueError as erreur:
        flash(str(erreur), "danger")
        return redirect(url_for("vie_scolaire.index", type=type_evt))

    flash(
        f"{len(crees)} événement(s) « {evenements.LIBELLES[type_evt]} » enregistré(s).",
        "success",
    )
    return redirect(url_for("vie_scolaire.evenements_liste"))


# ---------------------------------------------------------------------------
# Liste des événements + fiche d'activité
# ---------------------------------------------------------------------------

@vie_scolaire_bp.route("/vie-scolaire/evenements")
def evenements_liste():
    preset = request.args.get("periode", "mois")
    (date_debut, date_fin), preset = _periode(preset)

    type_filtre = request.args.get("type")
    if type_filtre not in evenements.TYPES_EVENEMENTS:
        type_filtre = None
    classe_id = request.args.get("classe_id", type=int)
    eleve_id = request.args.get("eleve_id", type=int)

    vues = evenements.feed(
        date_debut,
        date_fin,
        eleve_id=eleve_id,
        classe_id=classe_id,
        types=[type_filtre] if type_filtre else None,
        user=current_user,
    )

    classes = Classe.query.order_by(Classe.nom).all()
    eleves_query = Eleve.query.join(Classe).order_by(Classe.nom, Eleve.nom)
    if classe_id:
        eleves_query = eleves_query.filter(Eleve.classe_id == classe_id)

    compte_par_type = {}
    for vue in vues:
        compte_par_type[vue.type] = compte_par_type.get(vue.type, 0) + 1

    return render_template(
        "vie_scolaire/evenements.html",
        vues=vues,
        preset=preset,
        date_debut=date_debut,
        date_fin=date_fin,
        type_filtre=type_filtre,
        classe_id=classe_id,
        eleve_id=eleve_id,
        classes=classes,
        eleves=eleves_query.all(),
        libelles_types=evenements.LIBELLES,
        compte_par_type=compte_par_type,
    )


@vie_scolaire_bp.route("/evenements/<type_evt>/<int:evt_id>")
def evenement_fiche(type_evt, evt_id):
    vue = evenements.charger(type_evt, evt_id) or abort(404)
    if not evenements.visible_pour(vue, current_user):
        abort(403)
    return render_template(
        "vie_scolaire/evenement_fiche.html",
        vue=vue,
        peut_modifier=peut_modifier_evenement(current_user, type_evt, vue.obj),
    )


@vie_scolaire_bp.route("/evenements/<type_evt>/<int:evt_id>/modifier", methods=["GET", "POST"])
def evenement_modifier(type_evt, evt_id):
    vue = evenements.charger(type_evt, evt_id) or abort(404)
    if not peut_modifier_evenement(current_user, type_evt, vue.obj):
        abort(403)

    if request.method == "POST":
        donnees = _donnees_depuis_form(request.form)
        try:
            evenements.modifier(type_evt, evt_id, donnees)
        except ValueError as erreur:
            flash(str(erreur), "danger")
            return redirect(
                url_for("vie_scolaire.evenement_modifier", type_evt=type_evt, evt_id=evt_id)
            )
        flash("Événement modifié.", "success")
        return redirect(url_for("vie_scolaire.evenement_fiche", type_evt=type_evt, evt_id=evt_id))

    return render_template(
        "vie_scolaire/evenement_modifier.html",
        vue=vue,
        matieres=Matiere.query.order_by(Matiere.nom).all(),
        types_infractions=TypeInfractionMineure.query.filter_by(actif=True)
        .order_by(TypeInfractionMineure.libelle)
        .all(),
    )


@vie_scolaire_bp.route("/evenements/<type_evt>/<int:evt_id>/supprimer", methods=["POST"])
def evenement_supprimer(type_evt, evt_id):
    vue = evenements.charger(type_evt, evt_id) or abort(404)
    if not peut_modifier_evenement(current_user, type_evt, vue.obj):
        abort(403)
    evenements.supprimer(type_evt, evt_id)
    flash("Événement supprimé.", "success")
    return redirect(url_for("vie_scolaire.evenements_liste"))


# ---------------------------------------------------------------------------
# Raccourci : appel du jour (grille de présence par classe)
# ---------------------------------------------------------------------------

@vie_scolaire_bp.route("/vie-scolaire/appel")
def appel():
    if not peut_gerer_presences(current_user):
        abort(403)
    classe_id = request.args.get("classe_id", type=int)
    date_appel = _parser_date(request.args.get("date"))

    classes = Classe.query.order_by(Classe.nom).all()
    classe = db.session.get(Classe, classe_id) if classe_id else None
    eleves = []
    presences_par_eleve = {}

    if classe:
        eleves = sorted(classe.eleves, key=lambda e: e.nom)
        for presence in Presence.query.filter(
            Presence.eleve_id.in_([e.id for e in eleves]),
            Presence.date == date_appel,
        ).all():
            presences_par_eleve[presence.eleve_id] = presence

    return render_template(
        "vie_scolaire/appel.html",
        classes=classes,
        classe=classe,
        classe_id=classe_id,
        date_appel=date_appel,
        eleves=eleves,
        presences_par_eleve=presences_par_eleve,
    )


@vie_scolaire_bp.route("/vie-scolaire/appel/enregistrer", methods=["POST"])
def appel_enregistrer():
    if not peut_gerer_presences(current_user):
        abort(403)
    classe_id = request.form.get("classe_id", type=int)
    date_appel = _parser_date(request.form.get("date"))

    nb = 0
    for eleve in Eleve.query.filter_by(classe_id=classe_id).all():
        statut = request.form.get(f"statut_{eleve.id}")
        if not statut:
            continue
        justifie = request.form.get(f"justifie_{eleve.id}") == "1"
        motif = request.form.get(f"motif_{eleve.id}", "").strip() or None
        heure_arrivee = _parser_heure(request.form.get(f"heure_{eleve.id}", "").strip())

        existante = Presence.query.filter_by(eleve_id=eleve.id, date=date_appel).first()
        if existante:
            existante.statut = statut
            existante.justifie = justifie
            existante.motif = motif
            existante.heure_arrivee = heure_arrivee
            existante.saisi_par_id = current_user.id
        else:
            db.session.add(
                Presence(
                    eleve_id=eleve.id,
                    date=date_appel,
                    statut=statut,
                    justifie=justifie,
                    motif=motif,
                    heure_arrivee=heure_arrivee,
                    saisi_par_id=current_user.id,
                )
            )
        nb += 1

    db.session.commit()
    flash(f"{nb} entrée(s) de présence enregistrée(s).", "success")
    return redirect(url_for("vie_scolaire.appel", classe_id=classe_id, date=date_appel.isoformat()))


# ---------------------------------------------------------------------------
# Raccourci : notes par contrôle (grille de saisie pour une classe entière)
# ---------------------------------------------------------------------------

def _matieres_pour_saisie():
    if current_user.is_professeur():
        matiere_ids = {mid for mid, _ in current_user.matieres_classes_autorisees()}
        return Matiere.query.filter(Matiere.id.in_(matiere_ids)).order_by(Matiere.nom).all()
    return Matiere.query.order_by(Matiere.nom).all()


@vie_scolaire_bp.route("/vie-scolaire/controles")
def controles():
    if not (current_user.is_directeur() or current_user.is_professeur()):
        abort(403)
    classe_id = request.args.get("classe_id", type=int)
    matiere_id = request.args.get("matiere_id", type=int)
    trimestre_id = request.args.get("trimestre_id", type=int)

    query = Controle.query
    if classe_id:
        query = query.filter_by(classe_id=classe_id)
    if matiere_id:
        query = query.filter_by(matiere_id=matiere_id)
    if trimestre_id:
        query = query.filter_by(trimestre_id=trimestre_id)

    if current_user.is_professeur():
        paires = current_user.matieres_classes_autorisees()
        controles_visibles = [
            c for c in query.order_by(Controle.date.desc()).all()
            if (c.matiere_id, c.classe_id) in paires
        ]
    else:
        controles_visibles = query.order_by(Controle.date.desc()).all()

    return render_template(
        "vie_scolaire/controles.html",
        controles=controles_visibles,
        classes=Classe.query.order_by(Classe.nom).all(),
        matieres=_matieres_pour_saisie(),
        trimestres=Trimestre.query.order_by(Trimestre.date_debut).all(),
        classe_id=classe_id,
        matiere_id=matiere_id,
        trimestre_id=trimestre_id,
    )


@vie_scolaire_bp.route("/vie-scolaire/controle/nouveau", methods=["GET", "POST"])
def controle_nouveau():
    if not (current_user.is_directeur() or current_user.is_professeur()):
        abort(403)

    if request.method == "POST":
        matiere_id = request.form.get("matiere_id", type=int)
        classe_id = request.form.get("classe_id", type=int)
        intitule = request.form.get("intitule", "").strip()
        coefficient = request.form.get("coefficient", type=float) or 1.0
        trimestre_id = request.form.get("trimestre_id", type=int) or None

        if not current_user.peut_saisir(matiere_id, classe_id):
            abort(403)
        if not intitule:
            flash("L'intitulé est obligatoire.", "danger")
        else:
            controle = Controle(
                matiere_id=matiere_id,
                classe_id=classe_id,
                intitule=intitule,
                date=_parser_date(request.form.get("date")),
                coefficient=coefficient,
                trimestre_id=trimestre_id,
                saisi_par_id=current_user.id,
            )
            db.session.add(controle)
            db.session.commit()
            flash(f"Contrôle « {intitule} » créé.", "success")
            return redirect(url_for("vie_scolaire.controle_saisie", controle_id=controle.id))

    return render_template(
        "vie_scolaire/controle_form.html",
        classes=Classe.query.order_by(Classe.nom).all(),
        matieres=_matieres_pour_saisie(),
        trimestres=Trimestre.query.order_by(Trimestre.date_debut).all(),
        today=date.today().isoformat(),
    )


@vie_scolaire_bp.route("/vie-scolaire/controle/<int:controle_id>/saisie", methods=["GET", "POST"])
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

            existante = notes_par_eleve.get(eleve.id)
            if existante:
                existante.valeur = valeur
            else:
                db.session.add(
                    Note(
                        eleve_id=eleve.id,
                        controle_id=controle_id,
                        valeur=valeur,
                        saisi_par_id=current_user.id,
                    )
                )
        db.session.commit()
        flash("Notes enregistrées.", "success")
        return redirect(url_for("vie_scolaire.controle_saisie", controle_id=controle_id))

    return render_template(
        "vie_scolaire/saisie.html",
        controle=controle,
        eleves=eleves,
        notes_par_eleve=notes_par_eleve,
    )


@vie_scolaire_bp.route("/vie-scolaire/controle/<int:controle_id>/supprimer", methods=["POST"])
def controle_supprimer(controle_id):
    controle = db.session.get(Controle, controle_id) or abort(404)
    if not current_user.peut_saisir(controle.matiere_id, controle.classe_id):
        abort(403)
    db.session.delete(controle)
    db.session.commit()
    flash("Contrôle supprimé.", "success")
    return redirect(url_for("vie_scolaire.controles"))
