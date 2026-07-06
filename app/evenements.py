"""Couche « événement » unifiée au-dessus des tables typées.

Le schéma reste typé (Note, Notice, InfractionMineure, IncidentMajeur, Presence) ;
ce module présente ces lignes comme un flux homogène d'événements (feed) et
centralise création / chargement / modification / suppression par (type, id).
Toute l'UI événementielle (fiche élève, onglet Vie scolaire) passe par ici —
aucun autre endroit ne doit fusionner les tables à la main.
"""

from datetime import date as date_cls

from sqlalchemy import func

from app.extensions import db
from app.models import (
    Controle,
    CycleDiscipline,
    Eleve,
    IncidentMajeur,
    InfractionMineure,
    Note,
    Notice,
    Presence,
    TypeInfractionMineure,
)
from app.permissions import peut_voir_presences
from app.services import recalculer_points

TYPES_EVENEMENTS = ("note", "observation", "infraction_mineure", "infraction_majeure", "presence")

LIBELLES = {
    "note": "Note",
    "observation": "Observation",
    "infraction_mineure": "Infraction mineure",
    "infraction_majeure": "Infraction majeure",
    "presence": "Absence / Retard",
}

GRAVITES = ("mineure_grave", "moyenne", "majeure")
LIBELLES_GRAVITE = {
    "mineure_grave": "Mineure grave",
    "moyenne": "Moyenne",
    "majeure": "Majeure",
}

_MODELES = {
    "note": Note,
    "observation": Notice,
    "infraction_mineure": InfractionMineure,
    "infraction_majeure": IncidentMajeur,
    "presence": Presence,
}


class EvenementView:
    """Adaptateur : présente une ligne typée sous une interface commune.

    Utilisé par les templates (macro `ligne_evenement`) et la fiche d'activité,
    quel que soit le modèle sous-jacent.
    """

    def __init__(self, type_evt, obj):
        self.type = type_evt
        self.obj = obj

    @property
    def id(self):
        return self.obj.id

    @property
    def eleve(self):
        return self.obj.eleve

    @property
    def saisi_par(self):
        return self.obj.saisi_par

    @property
    def date(self):
        if self.type == "note" and self.obj.controle:
            return self.obj.controle.date
        return self.obj.date

    @property
    def heure(self):
        if self.type == "presence":
            return self.obj.heure_arrivee
        return None

    @property
    def matiere(self):
        if self.type == "presence":
            return None
        if self.type == "note" and self.obj.controle:
            return self.obj.controle.matiere
        return self.obj.matiere

    @property
    def libelle_type(self):
        if self.type == "presence":
            return "Absence" if self.obj.statut == "absent" else "Retard"
        return LIBELLES[self.type]

    @property
    def badge(self):
        """Classes CSS Bootstrap du badge de type."""
        if self.type == "note":
            return "bg-primary"
        if self.type == "observation":
            return "bg-info text-dark"
        if self.type == "infraction_mineure":
            return "bg-warning text-dark"
        if self.type == "infraction_majeure":
            return "bg-danger" if self.obj.gravite == "majeure" else "bg-danger bg-opacity-75"
        # presence
        return "bg-danger" if self.obj.statut == "absent" else "bg-warning text-dark"

    @property
    def points_deduits(self):
        if self.type == "infraction_mineure":
            return self.obj.type_infraction.points_deduits
        return None

    @property
    def resume(self):
        """Libellé court affiché dans les feeds."""
        o = self.obj
        if self.type == "note":
            base = f"{o.valeur:g}/20"
            if o.controle:
                return f"{base} — {o.controle.intitule}"
            return base
        if self.type == "observation":
            return o.titre
        if self.type == "infraction_mineure":
            return o.type_infraction.libelle
        if self.type == "infraction_majeure":
            texte = o.description or ""
            return texte[:90] + ("…" if len(texte) > 90 else "")
        # presence
        morceaux = []
        if o.statut == "retard" and o.heure_arrivee:
            morceaux.append(f"arrivé à {o.heure_arrivee.strftime('%H:%M')}")
        morceaux.append("justifié" if o.justifie else "injustifié")
        if o.motif:
            morceaux.append(o.motif)
        return " · ".join(morceaux)

    @property
    def complement(self):
        """Second niveau de détail (affiché en petit sous le résumé)."""
        o = self.obj
        if self.type == "observation":
            texte = o.contenu or ""
            return texte[:90] + ("…" if len(texte) > 90 else "")
        if self.type == "infraction_majeure" and o.sanction:
            return f"Sanction : {o.sanction}"
        return None


def _vue(type_evt, obj):
    return EvenementView(type_evt, obj)


def _appliquer_filtre_professeur(vues, user):
    """Restreint le feed d'un professeur : pas de présences, et uniquement les
    événements dont la matière fait partie de ses affectations pour la classe
    de l'élève concerné (une note sans matière reste invisible)."""
    paires = user.matieres_classes_autorisees()

    def visible(vue):
        if vue.type == "presence":
            return False
        matiere = vue.matiere
        if matiere is None:
            return False
        return (matiere.id, vue.eleve.classe_id) in paires

    return [v for v in vues if visible(v)]


def feed(date_debut, date_fin, eleve_id=None, classe_id=None, types=None, user=None,
         inclure_presents=False):
    """Feed unifié : liste d'`EvenementView` triée par date décroissante.

    - `types` : sous-ensemble de TYPES_EVENEMENTS (None = tous).
    - `user` : applique le filtrage par compétence (professeur restreint).
    - `inclure_presents` : par défaut les entrées « présent » sont masquées
      (seuls absences et retards sont des événements signifiants).
    """
    types_actifs = set(types) if types else set(TYPES_EVENEMENTS)
    if user is not None and not peut_voir_presences(user):
        types_actifs.discard("presence")

    vues = []

    def _filtrer(query, modele):
        if eleve_id:
            query = query.filter(modele.eleve_id == eleve_id)
        elif classe_id:
            query = query.join(Eleve, modele.eleve_id == Eleve.id).filter(
                Eleve.classe_id == classe_id
            )
        return query

    if "note" in types_actifs:
        date_effective = func.coalesce(Controle.date, Note.date)
        q = Note.query.outerjoin(Controle, Note.controle_id == Controle.id).filter(
            date_effective >= date_debut, date_effective <= date_fin
        )
        q = _filtrer(q, Note)
        vues.extend(_vue("note", o) for o in q.all())

    if "observation" in types_actifs:
        q = Notice.query.filter(Notice.date >= date_debut, Notice.date <= date_fin)
        q = _filtrer(q, Notice)
        vues.extend(_vue("observation", o) for o in q.all())

    if "infraction_mineure" in types_actifs:
        q = InfractionMineure.query.filter(
            InfractionMineure.date >= date_debut, InfractionMineure.date <= date_fin
        )
        q = _filtrer(q, InfractionMineure)
        vues.extend(_vue("infraction_mineure", o) for o in q.all())

    if "infraction_majeure" in types_actifs:
        q = IncidentMajeur.query.filter(
            IncidentMajeur.date >= date_debut, IncidentMajeur.date <= date_fin
        )
        q = _filtrer(q, IncidentMajeur)
        vues.extend(_vue("infraction_majeure", o) for o in q.all())

    if "presence" in types_actifs:
        q = Presence.query.filter(Presence.date >= date_debut, Presence.date <= date_fin)
        if not inclure_presents:
            q = q.filter(Presence.statut != "present")
        q = _filtrer(q, Presence)
        vues.extend(_vue("presence", o) for o in q.all())

    if user is not None and user.is_professeur():
        vues = _appliquer_filtre_professeur(vues, user)

    vues.sort(key=lambda v: (v.date or date_cls.min, v.id), reverse=True)
    return vues


def charger(type_evt, evt_id):
    """Retourne l'`EvenementView` (type, id), ou None si type/ligne inconnus."""
    modele = _MODELES.get(type_evt)
    if modele is None:
        return None
    obj = db.session.get(modele, evt_id)
    if obj is None:
        return None
    return _vue(type_evt, obj)


def creer(type_evt, eleves, user, donnees):
    """Crée une ligne typée par élève de `eleves` (une transaction).

    `donnees` : dict issu du formulaire unifié — champs communs `date`,
    `heure`, `matiere_id`, plus les champs propres au type. Retourne la liste
    des `EvenementView` créées. Lève ValueError pour données invalides.
    """
    if type_evt not in TYPES_EVENEMENTS:
        raise ValueError(f"Type d'événement inconnu : {type_evt}")
    if not eleves:
        raise ValueError("Aucun élève ciblé.")

    date_evt = donnees.get("date") or date_cls.today()
    matiere_id = donnees.get("matiere_id") or None
    crees = []

    if type_evt == "infraction_mineure":
        type_infraction = db.session.get(
            TypeInfractionMineure, donnees.get("type_infraction_id") or 0
        )
        if type_infraction is None:
            raise ValueError("Type d'infraction du barème obligatoire.")
        cycle_actif = CycleDiscipline.query.filter_by(date_cloture=None).first()
        for eleve in eleves:
            obj = InfractionMineure(
                eleve=eleve,
                type_infraction=type_infraction,
                date=date_evt,
                matiere_id=matiere_id,
                cycle=cycle_actif,
                saisi_par_id=user.id,
            )
            db.session.add(obj)
            eleve.points_vie_scolaire = max(
                0, eleve.points_vie_scolaire - type_infraction.points_deduits
            )
            crees.append(_vue(type_evt, obj))

    elif type_evt == "infraction_majeure":
        description = (donnees.get("description") or "").strip()
        gravite = donnees.get("gravite") or "moyenne"
        if gravite not in GRAVITES:
            gravite = "moyenne"
        if not description:
            raise ValueError("La description est obligatoire.")
        sanction = (donnees.get("sanction") or "").strip() or None
        for eleve in eleves:
            obj = IncidentMajeur(
                eleve=eleve,
                description=description,
                gravite=gravite,
                sanction=sanction,
                date=date_evt,
                matiere_id=matiere_id,
                saisi_par_id=user.id,
            )
            db.session.add(obj)
            crees.append(_vue(type_evt, obj))

    elif type_evt == "observation":
        titre = (donnees.get("titre") or "").strip()
        contenu = (donnees.get("contenu") or "").strip()
        if not titre or not contenu:
            raise ValueError("Le titre et le contenu sont obligatoires.")
        for eleve in eleves:
            obj = Notice(
                eleve=eleve,
                titre=titre,
                contenu=contenu,
                date=date_evt,
                matiere_id=matiere_id,
                saisi_par_id=user.id,
            )
            db.session.add(obj)
            crees.append(_vue(type_evt, obj))

    elif type_evt == "note":
        valeur = donnees.get("valeur")
        if valeur is None or not (0 <= valeur <= 20):
            raise ValueError("Une note entre 0 et 20 est obligatoire.")
        if not matiere_id:
            raise ValueError("La matière est obligatoire pour une note.")
        for eleve in eleves:
            obj = Note(
                eleve=eleve,
                matiere_id=matiere_id,
                valeur=valeur,
                date=date_evt,
                saisi_par_id=user.id,
            )
            db.session.add(obj)
            crees.append(_vue(type_evt, obj))

    elif type_evt == "presence":
        statut = donnees.get("statut")
        if statut not in ("absent", "retard"):
            raise ValueError("Le statut doit être « absent » ou « retard ».")
        heure = donnees.get("heure")
        justifie = bool(donnees.get("justifie"))
        motif = (donnees.get("motif") or "").strip() or None
        for eleve in eleves:
            # une seule entrée par élève et par jour : mise à jour si existante
            obj = Presence.query.filter_by(eleve_id=eleve.id, date=date_evt).first()
            if obj is None:
                obj = Presence(eleve=eleve, date=date_evt, saisi_par_id=user.id)
                db.session.add(obj)
            obj.statut = statut
            obj.heure_arrivee = heure if statut == "retard" else None
            obj.justifie = justifie
            obj.motif = motif
            obj.saisi_par_id = user.id
            crees.append(_vue(type_evt, obj))

    db.session.commit()
    return crees


def modifier(type_evt, evt_id, donnees):
    """Met à jour la ligne (type, id) depuis le formulaire d'édition."""
    vue = charger(type_evt, evt_id)
    if vue is None:
        return None
    o = vue.obj

    if "date" in donnees and donnees["date"]:
        o.date = donnees["date"]
    if "matiere_id" in donnees and type_evt != "presence":
        o.matiere_id = donnees["matiere_id"] or None

    if type_evt == "note":
        valeur = donnees.get("valeur")
        if valeur is not None:
            if not (0 <= valeur <= 20):
                raise ValueError("La note doit être entre 0 et 20.")
            o.valeur = valeur
    elif type_evt == "observation":
        if donnees.get("titre"):
            o.titre = donnees["titre"].strip()
        if donnees.get("contenu"):
            o.contenu = donnees["contenu"].strip()
    elif type_evt == "infraction_mineure":
        type_infraction_id = donnees.get("type_infraction_id")
        if type_infraction_id:
            type_infraction = db.session.get(TypeInfractionMineure, type_infraction_id)
            if type_infraction is None:
                raise ValueError("Type d'infraction inconnu.")
            o.type_infraction = type_infraction
        recalculer_points(o.eleve)
    elif type_evt == "infraction_majeure":
        if donnees.get("description"):
            o.description = donnees["description"].strip()
        if donnees.get("gravite") in GRAVITES:
            o.gravite = donnees["gravite"]
        if "sanction" in donnees:
            o.sanction = (donnees.get("sanction") or "").strip() or None
    elif type_evt == "presence":
        statut = donnees.get("statut")
        if statut in ("absent", "retard", "present"):
            o.statut = statut
        o.heure_arrivee = donnees.get("heure") if o.statut == "retard" else None
        if "justifie" in donnees:
            o.justifie = bool(donnees["justifie"])
        if "motif" in donnees:
            o.motif = (donnees.get("motif") or "").strip() or None

    db.session.commit()
    return vue


def supprimer(type_evt, evt_id):
    """Supprime la ligne (type, id) ; recalcule les points si nécessaire."""
    vue = charger(type_evt, evt_id)
    if vue is None:
        return False
    eleve = vue.obj.eleve
    db.session.delete(vue.obj)
    db.session.flush()
    if type_evt == "infraction_mineure":
        recalculer_points(eleve)
    db.session.commit()
    return True
