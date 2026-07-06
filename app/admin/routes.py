from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.admin.forms import (
    AffectationForm,
    AnneeScolaireForm,
    ClasseForm,
    CompteForm,
    EleveForm,
    MatiereForm,
    TrimestreForm,
    TypeInfractionForm,
)
from app.decorators import role_required
from app.extensions import db
from app.models import (
    AffectationProf,
    AnneeScolaire,
    Classe,
    CycleDiscipline,
    Eleve,
    Matiere,
    Trimestre,
    TypeInfractionMineure,
    User,
)
from app.services import cloturer_cycle

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
@role_required("directeur")
def guard():
    pass


# --- Classes -----------------------------------------------------------

@admin_bp.route("/admin/classes")
def classes():
    liste = Classe.query.order_by(Classe.nom).all()
    return render_template("admin/classes.html", classes=liste)


@admin_bp.route("/admin/classes/nouvelle", methods=["GET", "POST"])
def classe_nouvelle():
    form = ClasseForm()
    if form.validate_on_submit():
        db.session.add(Classe(nom=form.nom.data, annee_scolaire=form.annee_scolaire.data))
        db.session.commit()
        flash("Classe créée.", "success")
        return redirect(url_for("admin.classes"))
    return render_template("admin/classe_form.html", form=form, titre="Nouvelle classe")


@admin_bp.route("/admin/classes/<int:classe_id>/modifier", methods=["GET", "POST"])
def classe_modifier(classe_id):
    classe = db.session.get(Classe, classe_id) or abort(404)
    form = ClasseForm(obj=classe)
    if form.validate_on_submit():
        form.populate_obj(classe)
        db.session.commit()
        flash("Classe modifiée.", "success")
        return redirect(url_for("admin.classes"))
    return render_template("admin/classe_form.html", form=form, titre="Modifier la classe")


@admin_bp.route("/admin/classes/<int:classe_id>/supprimer", methods=["POST"])
def classe_supprimer(classe_id):
    classe = db.session.get(Classe, classe_id) or abort(404)
    db.session.delete(classe)
    db.session.commit()
    flash("Classe supprimée.", "success")
    return redirect(url_for("admin.classes"))


# --- Matières ------------------------------------------------------------

@admin_bp.route("/admin/matieres")
def matieres():
    liste = Matiere.query.order_by(Matiere.nom).all()
    return render_template("admin/matieres.html", matieres=liste)


@admin_bp.route("/admin/matieres/nouvelle", methods=["GET", "POST"])
def matiere_nouvelle():
    form = MatiereForm()
    if form.validate_on_submit():
        db.session.add(Matiere(nom=form.nom.data, coefficient=form.coefficient.data))
        db.session.commit()
        flash("Matière créée.", "success")
        return redirect(url_for("admin.matieres"))
    return render_template("admin/matiere_form.html", form=form, titre="Nouvelle matière")


@admin_bp.route("/admin/matieres/<int:matiere_id>/modifier", methods=["GET", "POST"])
def matiere_modifier(matiere_id):
    matiere = db.session.get(Matiere, matiere_id) or abort(404)
    form = MatiereForm(obj=matiere)
    if form.validate_on_submit():
        form.populate_obj(matiere)
        db.session.commit()
        flash("Matière modifiée.", "success")
        return redirect(url_for("admin.matieres"))
    return render_template("admin/matiere_form.html", form=form, titre="Modifier la matière")


@admin_bp.route("/admin/matieres/<int:matiere_id>/supprimer", methods=["POST"])
def matiere_supprimer(matiere_id):
    matiere = db.session.get(Matiere, matiere_id) or abort(404)
    db.session.delete(matiere)
    db.session.commit()
    flash("Matière supprimée.", "success")
    return redirect(url_for("admin.matieres"))


# --- Élèves ---------------------------------------------------------------

@admin_bp.route("/admin/eleves")
def eleves():
    classe_id = request.args.get("classe_id", type=int)
    query = Eleve.query
    if classe_id:
        query = query.filter_by(classe_id=classe_id)
    liste = query.join(Classe).order_by(Classe.nom, Eleve.nom).all()
    toutes_classes = Classe.query.order_by(Classe.nom).all()
    return render_template("admin/eleves.html", eleves=liste, classes=toutes_classes, classe_id=classe_id)


@admin_bp.route("/admin/eleves/nouveau", methods=["GET", "POST"])
def eleve_nouveau():
    form = EleveForm()
    form.classe_id.choices = [(c.id, c.nom) for c in Classe.query.order_by(Classe.nom)]
    if form.validate_on_submit():
        db.session.add(Eleve(nom=form.nom.data, prenom=form.prenom.data, classe_id=form.classe_id.data))
        db.session.commit()
        flash("Élève ajouté.", "success")
        return redirect(url_for("admin.eleves"))
    return render_template("admin/eleve_form.html", form=form, titre="Nouvel élève")


@admin_bp.route("/admin/eleves/<int:eleve_id>/modifier", methods=["GET", "POST"])
def eleve_modifier(eleve_id):
    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    form = EleveForm(obj=eleve)
    form.classe_id.choices = [(c.id, c.nom) for c in Classe.query.order_by(Classe.nom)]
    if form.validate_on_submit():
        form.populate_obj(eleve)
        db.session.commit()
        flash("Élève modifié.", "success")
        return redirect(url_for("admin.eleves"))
    return render_template("admin/eleve_form.html", form=form, titre="Modifier l'élève")


@admin_bp.route("/admin/eleves/<int:eleve_id>/supprimer", methods=["POST"])
def eleve_supprimer(eleve_id):
    eleve = db.session.get(Eleve, eleve_id) or abort(404)
    db.session.delete(eleve)
    db.session.commit()
    flash("Élève supprimé.", "success")
    return redirect(url_for("admin.eleves"))


# --- Comptes ---------------------------------------------------------------

@admin_bp.route("/admin/comptes")
def comptes():
    liste = User.query.order_by(User.role, User.nom).all()
    return render_template("admin/comptes.html", comptes=liste)


@admin_bp.route("/admin/comptes/nouveau", methods=["GET", "POST"])
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
            return redirect(url_for("admin.comptes"))
    return render_template("admin/compte_form.html", form=form, titre="Nouveau compte")


@admin_bp.route("/admin/comptes/<int:user_id>/modifier", methods=["GET", "POST"])
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
        return redirect(url_for("admin.comptes"))
    return render_template("admin/compte_form.html", form=form, titre="Modifier le compte")


# --- Affectations -----------------------------------------------------------

@admin_bp.route("/admin/affectations", methods=["GET", "POST"])
def affectations():
    form = AffectationForm()
    form.professeur_id.choices = [
        (u.id, u.nom) for u in User.query.filter_by(role="professeur").order_by(User.nom)
    ]
    form.matiere_id.choices = [(m.id, m.nom) for m in Matiere.query.order_by(Matiere.nom)]
    form.classe_id.choices = [(c.id, c.nom) for c in Classe.query.order_by(Classe.nom)]

    if form.validate_on_submit():
        if AffectationProf.query.filter_by(
            professeur_id=form.professeur_id.data,
            matiere_id=form.matiere_id.data,
            classe_id=form.classe_id.data,
        ).first():
            flash("Cette affectation existe déjà.", "warning")
        else:
            db.session.add(AffectationProf(
                professeur_id=form.professeur_id.data,
                matiere_id=form.matiere_id.data,
                classe_id=form.classe_id.data,
            ))
            db.session.commit()
            flash("Affectation créée.", "success")
        return redirect(url_for("admin.affectations"))

    liste = AffectationProf.query.all()
    return render_template("admin/affectations.html", form=form, affectations=liste)


@admin_bp.route("/admin/affectations/<int:affectation_id>/supprimer", methods=["POST"])
def affectation_supprimer(affectation_id):
    affectation = db.session.get(AffectationProf, affectation_id) or abort(404)
    db.session.delete(affectation)
    db.session.commit()
    flash("Affectation supprimée.", "success")
    return redirect(url_for("admin.affectations"))


# --- Barème ----------------------------------------------------------------

@admin_bp.route("/admin/bareme")
def bareme():
    liste = TypeInfractionMineure.query.order_by(TypeInfractionMineure.libelle).all()
    return render_template("admin/bareme.html", types_infractions=liste)


@admin_bp.route("/admin/bareme/nouveau", methods=["GET", "POST"])
def bareme_nouveau():
    form = TypeInfractionForm()
    if form.validate_on_submit():
        db.session.add(TypeInfractionMineure(
            libelle=form.libelle.data,
            points_deduits=form.points_deduits.data,
            actif=form.actif.data,
        ))
        db.session.commit()
        flash("Type d'infraction créé.", "success")
        return redirect(url_for("admin.bareme"))
    return render_template("admin/bareme_form.html", form=form, titre="Nouveau type d'infraction")


@admin_bp.route("/admin/bareme/<int:type_id>/modifier", methods=["GET", "POST"])
def bareme_modifier(type_id):
    type_infraction = db.session.get(TypeInfractionMineure, type_id) or abort(404)
    form = TypeInfractionForm(obj=type_infraction)
    if form.validate_on_submit():
        form.populate_obj(type_infraction)
        db.session.commit()
        flash("Type d'infraction modifié.", "success")
        return redirect(url_for("admin.bareme"))
    return render_template("admin/bareme_form.html", form=form, titre="Modifier le type d'infraction")


# --- Cycles de discipline --------------------------------------------------

@admin_bp.route("/admin/cycles")
def cycles():
    liste = CycleDiscipline.query.order_by(CycleDiscipline.date_debut.desc()).all()
    return render_template("admin/cycles.html", cycles=liste)


@admin_bp.route("/admin/cycles/nouveau", methods=["POST"])
def cycle_nouveau():
    if CycleDiscipline.query.filter_by(date_cloture=None).first():
        flash("Un cycle est déjà en cours ; clôturez-le avant d'en créer un nouveau.", "warning")
        return redirect(url_for("admin.cycles"))
    aujourdhui = date.today()
    db.session.add(CycleDiscipline(
        date_debut=aujourdhui,
        date_fin=aujourdhui + timedelta(days=15),
    ))
    db.session.commit()
    flash("Nouveau cycle de discipline créé.", "success")
    return redirect(url_for("admin.cycles"))


@admin_bp.route("/admin/cycles/<int:cycle_id>/cloturer", methods=["POST"])
def cycle_cloturer(cycle_id):
    cycle = db.session.get(CycleDiscipline, cycle_id) or abort(404)
    try:
        cloturer_cycle(cycle)
        from app.reports.generation import generer_rapport_discipline
        generer_rapport_discipline(cycle)
        flash("Cycle clôturé et rapport généré.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.cycles"))


# --- Années scolaires ------------------------------------------------------

@admin_bp.route("/admin/annees")
def annees():
    liste = AnneeScolaire.query.order_by(AnneeScolaire.date_debut.desc()).all()
    return render_template("admin/annees.html", annees=liste)


@admin_bp.route("/admin/annees/nouvelle", methods=["GET", "POST"])
def annee_nouvelle():
    form = AnneeScolaireForm()
    if form.validate_on_submit():
        if form.active.data:
            AnneeScolaire.query.update({"active": False})
        db.session.add(AnneeScolaire(
            libelle=form.libelle.data,
            date_debut=form.date_debut.data,
            date_fin=form.date_fin.data,
            active=form.active.data,
        ))
        db.session.commit()
        flash("Année scolaire créée.", "success")
        return redirect(url_for("admin.annees"))
    return render_template("admin/annee_form.html", form=form, titre="Nouvelle année scolaire")


@admin_bp.route("/admin/annees/<int:annee_id>/modifier", methods=["GET", "POST"])
def annee_modifier(annee_id):
    annee = db.session.get(AnneeScolaire, annee_id) or abort(404)
    form = AnneeScolaireForm(obj=annee)
    if form.validate_on_submit():
        if form.active.data:
            AnneeScolaire.query.update({"active": False})
        form.populate_obj(annee)
        db.session.commit()
        flash("Année scolaire modifiée.", "success")
        return redirect(url_for("admin.annees"))
    return render_template("admin/annee_form.html", form=form, titre="Modifier l'année scolaire")


# --- Trimestres ------------------------------------------------------------

@admin_bp.route("/admin/trimestres")
def trimestres():
    liste = Trimestre.query.join(AnneeScolaire).order_by(
        AnneeScolaire.date_debut.desc(), Trimestre.code
    ).all()
    return render_template("admin/trimestres.html", trimestres=liste)


@admin_bp.route("/admin/trimestres/nouveau", methods=["GET", "POST"])
def trimestre_nouveau():
    form = TrimestreForm()
    form.annee_id.choices = [
        (a.id, a.libelle) for a in AnneeScolaire.query.order_by(AnneeScolaire.date_debut.desc())
    ]
    if form.validate_on_submit():
        db.session.add(Trimestre(
            annee_id=form.annee_id.data,
            code=form.code.data,
            date_debut=form.date_debut.data,
            date_fin=form.date_fin.data,
        ))
        db.session.commit()
        flash("Trimestre créé.", "success")
        return redirect(url_for("admin.trimestres"))
    return render_template("admin/trimestre_form.html", form=form, titre="Nouveau trimestre")


@admin_bp.route("/admin/trimestres/<int:trimestre_id>/modifier", methods=["GET", "POST"])
def trimestre_modifier(trimestre_id):
    trimestre = db.session.get(Trimestre, trimestre_id) or abort(404)
    form = TrimestreForm(obj=trimestre)
    form.annee_id.choices = [
        (a.id, a.libelle) for a in AnneeScolaire.query.order_by(AnneeScolaire.date_debut.desc())
    ]
    if form.validate_on_submit():
        form.populate_obj(trimestre)
        db.session.commit()
        flash("Trimestre modifié.", "success")
        return redirect(url_for("admin.trimestres"))
    return render_template("admin/trimestre_form.html", form=form, titre="Modifier le trimestre")


@admin_bp.route("/admin/trimestres/<int:trimestre_id>/supprimer", methods=["POST"])
def trimestre_supprimer(trimestre_id):
    trimestre = db.session.get(Trimestre, trimestre_id) or abort(404)
    db.session.delete(trimestre)
    db.session.commit()
    flash("Trimestre supprimé.", "success")
    return redirect(url_for("admin.trimestres"))
