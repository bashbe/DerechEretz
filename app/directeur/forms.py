from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FloatField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, NumberRange, Optional


class ClasseForm(FlaskForm):
    nom = StringField("Nom de la classe", validators=[DataRequired()])
    annee_scolaire = StringField(
        "Année scolaire", validators=[DataRequired()], default="2025-2026"
    )
    submit = SubmitField("Enregistrer")


class MatiereForm(FlaskForm):
    nom = StringField("Nom de la matière", validators=[DataRequired()])
    coefficient = FloatField("Coefficient", validators=[DataRequired(), NumberRange(min=0.1)])
    submit = SubmitField("Enregistrer")


class EleveForm(FlaskForm):
    nom = StringField("Nom", validators=[DataRequired()])
    prenom = StringField("Prénom", validators=[DataRequired()])
    classe_id = SelectField("Classe", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Enregistrer")


class CompteForm(FlaskForm):
    nom = StringField("Nom complet", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email(check_deliverability=False)])
    role = SelectField(
        "Rôle",
        choices=[
            ("professeur", "Professeur"),
            ("surveillant", "Surveillant"),
            ("directeur", "Directeur"),
        ],
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Mot de passe (laisser vide pour ne pas modifier)", validators=[Optional()]
    )
    actif = BooleanField("Compte actif", default=True)
    submit = SubmitField("Enregistrer")


class AffectationForm(FlaskForm):
    professeur_id = SelectField("Professeur", coerce=int, validators=[DataRequired()])
    matiere_id = SelectField("Matière", coerce=int, validators=[DataRequired()])
    classe_id = SelectField("Classe", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Affecter")


class TypeInfractionForm(FlaskForm):
    libelle = StringField("Libellé de l'infraction", validators=[DataRequired()])
    points_deduits = IntegerField(
        "Points déduits", validators=[DataRequired(), NumberRange(min=1, max=20)]
    )
    actif = BooleanField("Actif", default=True)
    submit = SubmitField("Enregistrer")
