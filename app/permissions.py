"""Prédicats de capacité utilisés par les routes (garde 403) et les templates
(affichage conditionnel des actions). Aucune règle de permission ne doit être
dupliquée ailleurs dans l'application.
"""


def peut_voir_admin(user):
    return user.is_directeur()


def peut_gerer_presences(user):
    return user.is_directeur() or user.is_surveillant()


def peut_gerer_vie_scolaire(user):
    return user.is_directeur() or user.is_surveillant()


def peut_generer_rapports(user):
    return user.is_directeur() or user.is_surveillant()


def peut_gerer_controle(user, matiere_id, classe_id):
    return user.peut_saisir(matiere_id, classe_id)


# --- Événements (couche unifiée, voir app/evenements.py) ------------------

def types_evenements_creables(user):
    """Types d'événements que l'utilisateur peut créer via le formulaire unifié."""
    if user.is_directeur():
        return {"note", "observation", "infraction_mineure", "infraction_majeure", "presence"}
    if user.is_surveillant():
        return {"observation", "infraction_mineure", "infraction_majeure", "presence"}
    if user.is_professeur():
        return {"note", "observation"}
    return set()


def peut_voir_presences(user):
    """Les entrées de présence sont invisibles pour un professeur."""
    return user.is_directeur() or user.is_surveillant()


def peut_modifier_evenement(user, type_evt, obj):
    """Droit de modifier/supprimer une ligne d'événement existante."""
    if user.is_directeur():
        return True
    if user.is_surveillant():
        return type_evt in ("infraction_mineure", "infraction_majeure", "presence") or (
            type_evt == "observation" and obj.saisi_par_id == user.id
        )
    if user.is_professeur():
        return type_evt in ("note", "observation") and obj.saisi_par_id == user.id
    return False


# --- Visibilité des onglets de navigation --------------------------------

def peut_voir_tab_presences(user):
    return user.is_directeur() or user.is_surveillant()


def peut_voir_tab_notes(user):
    return user.is_directeur() or user.is_professeur()


def peut_voir_tab_vie_scolaire(user):
    return user.is_directeur() or user.is_surveillant()


def peut_voir_tab_rapports(user):
    return user.is_directeur() or user.is_surveillant()
