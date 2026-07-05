from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from app.decorators import role_required
from app.directeur.forms import (
    AffectationForm,
    ClasseForm,
    CompteForm,
    EleveForm,
    MatiereForm,
    TypeInfractionForm,
)
from app.extensions import db
from app.models import (
    AffectationProf,
    Classe,
    CycleDiscipline,
    Eleve,
    Matiere,
    RapportGenere,
    TypeInfractionMineure,
    User,
)
from app.services import cloturer_cycle

directeur_bp = Blueprint("directeur", __name__)


@directeur_bp.before_request
@login_required
@role_required("directeur")
def guard():
    pass


# --- Classes -----------------------------------------------------------

@directeur_bp.route("/classes")
def classes():
    liste = Classe.query.order_by(Classe.nom).all()
    return render_template("directeur/classes.html", classes=liste)


@directeur_bp.route("/classes/nouvelle", methods=["GET", "POST"])
def classe_nouvelle():
    form = ClasseForm()
    if form.validate_on_submit():
        classe = Classe(nom=form.nom.data, annee_scolaire=form.annee_scolaire.data)
        db.session.add(classe)
        db.session.commit()
        flash("Classe créée.", "success")
        return redirect(url_for("directeur.classes"))
    return render_template("directeur/classe_form.html", form=form, titre="Nouvelle classe")


@directeur_bp.route("/classes/<int:classe_id>/modifier", methods=["GET", "POST"])
def classe_modifier(classe_id):
    classe = db.session.get(Classe, classe_id) or abort(404)
    form = ClasseForm(obj=classe)
    if form.validate_on_submit():
        form.populate_obj(classe)
        db.session.commit()
        flash("Classe modifiée.", "success")
        return redirect(url_for("directeur.classes"))
    return render_template("directeur/classe_form.html", form=form, titre="Modifier la classe")


@directeur_bp.route("/classes/<int:classe_id>/supprimer", methods=["POST"])
def classe_supprimer(classe_id):
    classe = db.session.get(Classe, classe_id) or abort(404)
    db.session.delete(classe)
    db.session.commit()
    flash("Classe supprimée.", "success")
    return redirect(url_for("directeur.classes"))


# --- Matières ------------------------------------------------------------

@directeur_bp.route("/matieres")
def matieres():
    liste = Matiere.query.order_by(Matiere.nom).all()
    return render_template("directeur/matieres.html", matieres=liste)


@directeur_bp.route("/matieres/nouvelle", methods=["GET", "POST"])
def matiere_nouvelle():
    form = MatiereForm()
    if form.validate_on_submit():
        matiere = Matiere(nom=form.nom.data, coefficient=form.coefficient.data)
        db.session.add(matiere)
        db.session.commit()
        flash("Matière créée.", "success")
        return redirect(url_for("directeur.matieres"))
    return render_template("directeur/matiere_form.html", form=form, titre="Nouvelle matière")


@directeur_bp.route("/matieres/<int:matiere_id>/modifier", methods=["GET", "POST"])
def matiere_modifier(matiere_id):
    matiere = db.session.get(Matiere, matiere_id) or abort(404)
    form = MatiereForm(obj=matiere)
    if form.validate_on_submit():
        form.populate_obj(matiere)
        db.session.commit()
        flash("Matière modifiée.", "success")
        return redirect(url_for("directeur.matieres"))
    return render_template("directeur/matiere_form.html", form=form, titre="Modifier la matière")


@directeur_bp.route("/matieres/<int:matiere_id>/supprimer", methods=["POST"])
def matiere_supprimer(matiere_id):
    matiere = db.session.get(Matiere, matiere_id) or abort(404)
    db.session.delete(matiere)
    db.session.commit()
    flash("Matière supprimée.", "success")
    return redirect(url_for("directeur.matieres"))


# --- Élèves ----------------------------------------------------------------

@directeur_bp.route("/eleves")
def eleves():
    classe_id = request.args.get("classe_id", type=int)
    query = Eleve.query
    if classe_id:
        query = query.filter_by(classe_id=classe_id)
    liste = query.join(Classe).order_by(Classe.nom, Eleve.nom).all()
    toutes_classes = Classe.query.order_by(Classe.nom).all()
    return render_template(
        "directeur/eleves.html", eleves=liste, classes=toutes_classes, classe_id=classe_id
    )


@directeur_bp.route("/eleves/nouveau", methods=["GET", "POST"])
def eleve_nouveau():
    form = EleveForm()
    form.classe_id.choices = [(c.id, c.nom) for c in Classe.query.order_by(Classe.nom)]
    if form.validate_on_submit():
        eleve = Eleve(nom=form.nom.data, prenom=form.prenom.data, classe_id=form.classe_id.data)
        db.session.add(eleve)
        db.session.commit()
        flash("Élève ajouté.", "success")
        return redirect(url_for("directeur.eleves"))
    return render_template("directeur/eleve_form.html", form=form, titre="Nouvel élève")


@directeur_bp.route("/eleves/<int:eleve_id>/modifier", methods=["GET", "POST"])
def eleve_modifier(eleve_id):
    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    form = EleveForm(obj=eleve)
    form.classe_id.choices = [(c.id, c.nom) for c in Classe.query.order_by(Classe.nom)]
    if form.validate_on_submit():
        form.populate_obj(eleve)
        db.session.commit()
        flash("Élève modifié.", "success")
        return redirect(url_for("directeur.eleves"))
    return render_template("directeur/eleve_form.html", form=form, titre="Modifier l'élève")


@directeur_bp.route("/eleves/<int:eleve_id>/supprimer", methods=["POST"])
def eleve_supprimer(eleve_id):
    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    db.session.delete(eleve)
    db.session.commit()
    flash("Élève supprimé.", "success")
    return redirect(url_for("directeur.eleves"))


# --- Comptes utilisateurs ----------------------------------------------

@directeur_bp.route("/comptes")
def comptes():
    liste = User.query.order_by(User.role, User.nom).all()
    return render_template("directeur/comptes.html", comptes=liste)


@directeur_bp.route("/comptes/nouveau", methods=["GET", "POST"])
def compte_nouveau():
    form = CompteForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash("Le mot de passe est obligatoire à la création.", "danger")
        elif User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("Cet email est déjà utilisé.", "danger")
        else:
            user = User(
                nom=form.nom.data,
                email=form.email.data.lower().strip(),
                role=form.role.data,
                actif=form.actif.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Compte créé.", "success")
            return redirect(url_for("directeur.comptes"))
    return render_template("directeur/compte_form.html", form=form, titre="Nouveau compte")


@directeur_bp.route("/comptes/<int:user_id>/modifier", methods=["GET", "POST"])
def compte_modifier(user_id):
    user = db.session.get(User, user_id) or abort(404)
    form = CompteForm(obj=user)
    if form.validate_on_submit():
        user.nom = form.nom.data
        user.email = form.email.data.lower().strip()
        user.role = form.role.data
        user.actif = form.actif.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash("Compte modifié.", "success")
        return redirect(url_for("directeur.comptes"))
    return render_template("directeur/compte_form.html", form=form, titre="Modifier le compte")


# --- Affectations professeur -> matière/classe --------------------------

@directeur_bp.route("/affectations", methods=["GET", "POST"])
def affectations():
    form = AffectationForm()
    form.professeur_id.choices = [
        (u.id, u.nom) for u in User.query.filter_by(role="professeur").order_by(User.nom)
    ]
    form.matiere_id.choices = [(m.id, m.nom) for m in Matiere.query.order_by(Matiere.nom)]
    form.classe_id.choices = [(c.id, c.nom) for c in Classe.query.order_by(Classe.nom)]

    if form.validate_on_submit():
        existe = AffectationProf.query.filter_by(
            professeur_id=form.professeur_id.data,
            matiere_id=form.matiere_id.data,
            classe_id=form.classe_id.data,
        ).first()
        if existe:
            flash("Cette affectation existe déjà.", "warning")
        else:
            db.session.add(
                AffectationProf(
                    professeur_id=form.professeur_id.data,
                    matiere_id=form.matiere_id.data,
                    classe_id=form.classe_id.data,
                )
            )
            db.session.commit()
            flash("Affectation créée.", "success")
        return redirect(url_for("directeur.affectations"))

    liste = AffectationProf.query.all()
    return render_template("directeur/affectations.html", form=form, affectations=liste)


@directeur_bp.route("/affectations/<int:affectation_id>/supprimer", methods=["POST"])
def affectation_supprimer(affectation_id):
    affectation = db.session.get(AffectationProf, affectation_id) or abort(404)
    db.session.delete(affectation)
    db.session.commit()
    flash("Affectation supprimée.", "success")
    return redirect(url_for("directeur.affectations"))


# --- Barème des infractions mineures ------------------------------------

@directeur_bp.route("/bareme")
def bareme():
    liste = TypeInfractionMineure.query.order_by(TypeInfractionMineure.libelle).all()
    return render_template("directeur/bareme.html", types_infractions=liste)


@directeur_bp.route("/bareme/nouveau", methods=["GET", "POST"])
def bareme_nouveau():
    form = TypeInfractionForm()
    if form.validate_on_submit():
        type_infraction = TypeInfractionMineure(
            libelle=form.libelle.data,
            points_deduits=form.points_deduits.data,
            actif=form.actif.data,
        )
        db.session.add(type_infraction)
        db.session.commit()
        flash("Type d'infraction créé.", "success")
        return redirect(url_for("directeur.bareme"))
    return render_template("directeur/bareme_form.html", form=form, titre="Nouveau type d'infraction")


@directeur_bp.route("/bareme/<int:type_id>/modifier", methods=["GET", "POST"])
def bareme_modifier(type_id):
    type_infraction = db.session.get(TypeInfractionMineure, type_id) or abort(404)
    form = TypeInfractionForm(obj=type_infraction)
    if form.validate_on_submit():
        form.populate_obj(type_infraction)
        db.session.commit()
        flash("Type d'infraction modifié.", "success")
        return redirect(url_for("directeur.bareme"))
    return render_template(
        "directeur/bareme_form.html", form=form, titre="Modifier le type d'infraction"
    )


# --- Cycles de discipline ------------------------------------------------

@directeur_bp.route("/discipline/cycles")
def discipline_cycles():
    liste = CycleDiscipline.query.order_by(CycleDiscipline.date_debut.desc()).all()
    return render_template("directeur/cycles.html", cycles=liste)


@directeur_bp.route("/discipline/cycles/nouveau", methods=["POST"])
def cycle_nouveau():
    cycle_existant = CycleDiscipline.query.filter_by(date_cloture=None).first()
    if cycle_existant:
        flash("Un cycle est déjà en cours ; clôturez-le avant d'en créer un nouveau.", "warning")
        return redirect(url_for("directeur.discipline_cycles"))

    aujourdhui = date.today()
    cycle = CycleDiscipline(date_debut=aujourdhui, date_fin=aujourdhui + timedelta(days=15))
    db.session.add(cycle)
    db.session.commit()
    flash("Nouveau cycle de discipline créé.", "success")
    return redirect(url_for("directeur.discipline_cycles"))


@directeur_bp.route("/discipline/cycles/<int:cycle_id>/cloturer", methods=["POST"])
def cycle_cloturer(cycle_id):
    cycle = db.session.get(CycleDiscipline, cycle_id) or abort(404)
    try:
        cloturer_cycle(cycle)
        from app.reports.generation import generer_rapport_discipline

        generer_rapport_discipline(cycle)
        flash("Cycle clôturé et rapport généré.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("directeur.discipline_cycles"))


# --- Rapports ------------------------------------------------------------

@directeur_bp.route("/rapports")
def rapports():
    liste = RapportGenere.query.order_by(RapportGenere.date_creation.desc()).all()
    classes_dispo = Classe.query.order_by(Classe.nom).all()
    return render_template("directeur/rapports.html", rapports=liste, classes=classes_dispo)


@directeur_bp.route("/rapports/notes", methods=["POST"])
def rapport_notes_generer():
    from app.reports.generation import generer_rapport_notes

    classe_id = request.form.get("classe_id", type=int)
    trimestre = request.form.get("trimestre", "T1")
    classe = db.session.get(Classe, classe_id) or abort(404)
    generer_rapport_notes(classe, trimestre)
    flash("Rapport de notes généré.", "success")
    return redirect(url_for("directeur.rapports"))


@directeur_bp.route("/rapports/absences", methods=["POST"])
def rapport_absences_generer():
    from app.reports.generation import generer_rapport_absences

    classe_id = request.form.get("classe_id", type=int)
    classe = db.session.get(Classe, classe_id) or abort(404)
    generer_rapport_absences(classe)
    flash("Rapport d'absences généré.", "success")
    return redirect(url_for("directeur.rapports"))


@directeur_bp.route("/rapports/<int:rapport_id>/telecharger/<format>")
def rapport_telecharger(rapport_id, format):
    rapport = db.session.get(RapportGenere, rapport_id) or abort(404)
    chemin = rapport.fichier_pdf if format == "pdf" else rapport.fichier_excel
    if not chemin:
        abort(404)
    return send_file(chemin, as_attachment=True)
