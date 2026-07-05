from datetime import date, datetime, time

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

ROLES = ("directeur", "professeur", "surveillant")
TRIMESTRES = ("T1", "T2", "T3")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    actif = db.Column(db.Boolean, nullable=False, default=True)

    affectations = db.relationship(
        "AffectationProf", back_populates="professeur", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_directeur(self):
        return self.role == "directeur"

    def is_professeur(self):
        return self.role == "professeur"

    def is_surveillant(self):
        return self.role == "surveillant"

    def matieres_classes_autorisees(self):
        """Retourne la liste des (matiere_id, classe_id) qu'un professeur peut saisir."""
        return {(a.matiere_id, a.classe_id) for a in self.affectations}

    def peut_saisir(self, matiere_id, classe_id):
        if self.is_directeur():
            return True
        if not self.is_professeur():
            return False
        return (matiere_id, classe_id) in self.matieres_classes_autorisees()


class Classe(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    annee_scolaire = db.Column(db.String(20), nullable=False)

    eleves = db.relationship("Eleve", back_populates="classe", cascade="all, delete-orphan")
    affectations = db.relationship(
        "AffectationProf", back_populates="classe", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"{self.nom} ({self.annee_scolaire})"


class Eleve(db.Model):
    __tablename__ = "eleves"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    prenom = db.Column(db.String(120), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    points_vie_scolaire = db.Column(db.Integer, nullable=False, default=20)

    classe = db.relationship("Classe", back_populates="eleves")
    notes = db.relationship("Note", back_populates="eleve", cascade="all, delete-orphan")
    absences = db.relationship("Absence", back_populates="eleve", cascade="all, delete-orphan")
    infractions_mineures = db.relationship(
        "InfractionMineure", back_populates="eleve", cascade="all, delete-orphan"
    )
    incidents_majeurs = db.relationship(
        "IncidentMajeur", back_populates="eleve", cascade="all, delete-orphan"
    )
    contacts_parents = db.relationship(
        "ContactParent", back_populates="eleve", cascade="all, delete-orphan"
    )
    notices = db.relationship("Notice", back_populates="eleve", cascade="all, delete-orphan")
    presences = db.relationship(
        "Presence", back_populates="eleve", cascade="all, delete-orphan"
    )

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


class Matiere(db.Model):
    __tablename__ = "matieres"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    coefficient = db.Column(db.Float, nullable=False, default=1.0)

    affectations = db.relationship(
        "AffectationProf", back_populates="matiere", cascade="all, delete-orphan"
    )


class AffectationProf(db.Model):
    """Lie un professeur à une matière pour une classe donnée."""

    __tablename__ = "affectations_prof"
    __table_args__ = (
        db.UniqueConstraint("professeur_id", "matiere_id", "classe_id", name="uq_affectation"),
    )

    id = db.Column(db.Integer, primary_key=True)
    professeur_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)

    professeur = db.relationship("User", back_populates="affectations")
    matiere = db.relationship("Matiere", back_populates="affectations")
    classe = db.relationship("Classe", back_populates="affectations")


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)
    valeur = db.Column(db.Float, nullable=False)
    trimestre = db.Column(db.String(2), nullable=True)
    date = db.Column(db.Date, nullable=True, default=date.today)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    controle_id = db.Column(db.Integer, db.ForeignKey("controles.id"), nullable=True)

    eleve = db.relationship("Eleve", back_populates="notes")
    matiere = db.relationship("Matiere")
    saisi_par = db.relationship("User")
    controle = db.relationship("Controle", back_populates="notes")


class Absence(db.Model):
    __tablename__ = "absences"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    type = db.Column(db.String(20), nullable=False)  # 'absence' ou 'retard'
    statut = db.Column(db.String(20), nullable=False)  # 'justifie' ou 'injustifie'
    motif = db.Column(db.String(255))
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    eleve = db.relationship("Eleve", back_populates="absences")
    saisi_par = db.relationship("User")


class TypeInfractionMineure(db.Model):
    __tablename__ = "types_infractions_mineures"

    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(150), nullable=False)
    points_deduits = db.Column(db.Integer, nullable=False)
    actif = db.Column(db.Boolean, nullable=False, default=True)


class InfractionMineure(db.Model):
    __tablename__ = "infractions_mineures"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    type_infraction_id = db.Column(
        db.Integer, db.ForeignKey("types_infractions_mineures.id"), nullable=False
    )
    date = db.Column(db.Date, nullable=False, default=date.today)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    cycle_id = db.Column(db.Integer, db.ForeignKey("cycles_discipline.id"), nullable=True)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)

    eleve = db.relationship("Eleve", back_populates="infractions_mineures")
    type_infraction = db.relationship("TypeInfractionMineure")
    saisi_par = db.relationship("User")
    cycle = db.relationship("CycleDiscipline", back_populates="infractions")
    matiere = db.relationship("Matiere")


class IncidentMajeur(db.Model):
    __tablename__ = "incidents_majeurs"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    gravite = db.Column(db.String(20), nullable=False)  # 'mineure_grave', 'moyenne', 'majeure'
    sanction = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False, default=date.today)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)

    eleve = db.relationship("Eleve", back_populates="incidents_majeurs")
    saisi_par = db.relationship("User")
    matiere = db.relationship("Matiere")


class CycleDiscipline(db.Model):
    __tablename__ = "cycles_discipline"

    id = db.Column(db.Integer, primary_key=True)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    date_cloture = db.Column(db.DateTime, nullable=True)

    infractions = db.relationship("InfractionMineure", back_populates="cycle")
    snapshots = db.relationship(
        "SnapshotPointsEleve", back_populates="cycle", cascade="all, delete-orphan"
    )
    rapports = db.relationship("RapportGenere", back_populates="cycle")

    @property
    def est_cloture(self):
        return self.date_cloture is not None


class SnapshotPointsEleve(db.Model):
    """Points finaux d'un élève figés à la clôture d'un cycle de discipline."""

    __tablename__ = "snapshots_points_eleve"

    id = db.Column(db.Integer, primary_key=True)
    cycle_id = db.Column(db.Integer, db.ForeignKey("cycles_discipline.id"), nullable=False)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    points_finaux = db.Column(db.Integer, nullable=False)

    cycle = db.relationship("CycleDiscipline", back_populates="snapshots")
    eleve = db.relationship("Eleve")


class RapportGenere(db.Model):
    __tablename__ = "rapports_generes"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'notes', 'absences', 'discipline'
    titre = db.Column(db.String(255), nullable=False)
    fichier_pdf = db.Column(db.String(255))
    fichier_excel = db.Column(db.String(255))
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    cycle_id = db.Column(db.Integer, db.ForeignKey("cycles_discipline.id"), nullable=True)

    cycle = db.relationship("CycleDiscipline", back_populates="rapports")


class AnneeScolaire(db.Model):
    __tablename__ = "annees_scolaires"

    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(20), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)

    trimestres = db.relationship(
        "Trimestre", back_populates="annee", cascade="all, delete-orphan"
    )


class Trimestre(db.Model):
    __tablename__ = "trimestres"

    id = db.Column(db.Integer, primary_key=True)
    annee_id = db.Column(db.Integer, db.ForeignKey("annees_scolaires.id"), nullable=False)
    code = db.Column(db.String(2), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)

    annee = db.relationship("AnneeScolaire", back_populates="trimestres")
    controles = db.relationship("Controle", back_populates="trimestre")


class Controle(db.Model):
    __tablename__ = "controles"

    id = db.Column(db.Integer, primary_key=True)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    intitule = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    coefficient = db.Column(db.Float, nullable=False, default=1.0)
    trimestre_id = db.Column(db.Integer, db.ForeignKey("trimestres.id"), nullable=True)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    matiere = db.relationship("Matiere")
    classe = db.relationship("Classe")
    trimestre = db.relationship("Trimestre", back_populates="controles")
    saisi_par = db.relationship("User")
    notes = db.relationship("Note", back_populates="controle")


class Presence(db.Model):
    __tablename__ = "presences"
    __table_args__ = (
        db.UniqueConstraint("eleve_id", "date", name="uq_presence_eleve_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    statut = db.Column(db.String(20), nullable=False)  # 'present', 'absent' ou 'retard'
    heure_arrivee = db.Column(db.Time, nullable=True)
    justifie = db.Column(db.Boolean, nullable=False, default=False)
    motif = db.Column(db.String(255), nullable=True)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    eleve = db.relationship("Eleve", back_populates="presences")
    saisi_par = db.relationship("User")


class ContactParent(db.Model):
    __tablename__ = "contacts_parents"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    lien = db.Column(db.String(10), nullable=False)  # 'pere', 'mere' ou 'autre'
    nom = db.Column(db.String(120), nullable=False)
    telephone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)

    eleve = db.relationship("Eleve", back_populates="contacts_parents")


class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey("eleves.id"), nullable=False)
    titre = db.Column(db.String(150), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey("matieres.id"), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    saisi_par_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    eleve = db.relationship("Eleve", back_populates="notices")
    matiere = db.relationship("Matiere")
    saisi_par = db.relationship("User")
