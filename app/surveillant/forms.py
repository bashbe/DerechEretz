from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class InfractionMineureForm(FlaskForm):
    eleve_id = SelectField("Élève", coerce=int, validators=[DataRequired()])
    type_infraction_id = SelectField("Infraction", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Enregistrer l'infraction")


class IncidentMajeurForm(FlaskForm):
    eleve_id = SelectField("Élève", coerce=int, validators=[DataRequired()])
    gravite = SelectField(
        "Gravité",
        choices=[("moyenne", "Moyenne"), ("grave", "Grave"), ("tres_grave", "Très grave")],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description de l'incident", validators=[DataRequired(), Length(min=5)])
    sanction = StringField("Sanction (optionnel)")
    submit = SubmitField("Enregistrer l'incident")
