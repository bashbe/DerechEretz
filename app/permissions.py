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


# --- Visibilité des onglets de navigation --------------------------------

def peut_voir_tab_presences(user):
    return user.is_directeur() or user.is_surveillant()


def peut_voir_tab_notes(user):
    return user.is_directeur() or user.is_professeur()


def peut_voir_tab_vie_scolaire(user):
    return user.is_directeur() or user.is_surveillant()


def peut_voir_tab_rapports(user):
    return user.is_directeur() or user.is_surveillant()
