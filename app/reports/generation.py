import os
from datetime import datetime

from flask import current_app
from openpyxl import Workbook
from xhtml2pdf import pisa

from app import evenements
from app.extensions import db
from app.models import InfractionMineure, RapportGenere


def _dossier_rapports():
    dossier = os.path.join(current_app.instance_path, "rapports")
    os.makedirs(dossier, exist_ok=True)
    return dossier


def _horodatage():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _ecrire_pdf(html, chemin):
    with open(chemin, "wb") as fichier:
        pisa.CreatePDF(html, dest=fichier)


def generer_rapport_evenements(eleves, date_debut, date_fin, types_evenements, libelle_periode):
    """Rapport générique : une page PDF par élève, listant ses événements
    (notes, observations, infractions, présences — selon `types_evenements`)
    sur `date_debut`..`date_fin`. `eleves` peut être un ou plusieurs élèves,
    une classe entière ou l'école entière — l'appelant filtre déjà la liste.
    """
    eleves_tries = sorted(eleves, key=lambda e: (e.classe.nom, e.nom))
    periode_str = f"{date_debut.strftime('%d/%m/%Y')} → {date_fin.strftime('%d/%m/%Y')}"
    titre = f"Rapport d'événements — {libelle_periode} ({periode_str})"
    horodatage = _horodatage()

    pages_html = []
    lignes_excel = []
    for i, eleve in enumerate(eleves_tries):
        vues = evenements.feed(
            date_debut, date_fin, eleve_id=eleve.id, types=types_evenements
        )
        if vues:
            corps = "".join(
                f"<tr><td>{v.date.strftime('%d/%m/%Y') if v.date else '-'}</td>"
                f"<td>{v.libelle_type}</td>"
                f"<td>{v.matiere.nom if v.matiere else '-'}</td>"
                f"<td>{v.resume}{' — ' + v.complement if v.complement else ''}</td></tr>"
                for v in vues
            )
        else:
            corps = '<tr><td colspan="4"><i>Aucun événement sur cette période.</i></td></tr>'

        rupture = "page-break-before: always;" if i > 0 else ""
        pages_html.append(f"""
        <div style="{rupture}">
          <h2>{eleve.nom_complet}</h2>
          <div>{eleve.classe.nom} — {libelle_periode} ({periode_str})</div>
          <table border="1" cellpadding="4" cellspacing="0" width="100%">
            <tr><th>Date</th><th>Type</th><th>Matière</th><th>Détail</th></tr>
            {corps}
          </table>
        </div>
        """)

        for v in vues:
            lignes_excel.append([
                eleve.nom_complet,
                eleve.classe.nom,
                v.date.strftime("%d/%m/%Y") if v.date else "",
                v.libelle_type,
                v.matiere.nom if v.matiere else "",
                v.resume,
            ])

    html = f"<html><body>{''.join(pages_html)}</body></html>"
    chemin_pdf = os.path.join(_dossier_rapports(), f"evenements_{horodatage}.pdf")
    _ecrire_pdf(html, chemin_pdf)

    chemin_excel = os.path.join(_dossier_rapports(), f"evenements_{horodatage}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(["Élève", "Classe", "Date", "Type", "Matière", "Détail"])
    for ligne in lignes_excel:
        ws.append(ligne)
    wb.save(chemin_excel)

    rapport = RapportGenere(
        type="evenements", titre=titre, fichier_pdf=chemin_pdf, fichier_excel=chemin_excel
    )
    db.session.add(rapport)
    db.session.commit()
    return rapport


def generer_rapport_discipline(cycle):
    lignes = []
    for snapshot in cycle.snapshots:
        infractions = InfractionMineure.query.filter_by(
            cycle_id=cycle.id, eleve_id=snapshot.eleve_id
        ).all()
        lignes.append((snapshot.eleve, snapshot.points_finaux, infractions))

    titre = f"Discipline du {cycle.date_debut} au {cycle.date_fin}"
    horodatage = _horodatage()

    lignes_html = ""
    for eleve, points, infractions in lignes:
        details = "; ".join(f"{i.type_infraction.libelle} (-{i.type_infraction.points_deduits})" for i in infractions)
        lignes_html += f"<tr><td>{eleve.nom_complet}</td><td>{points}/20</td><td>{details or '-'}</td></tr>"

    html = f"""
    <html><body>
    <h2>Rapport de discipline — {titre}</h2>
    <table border="1" cellpadding="4" cellspacing="0" width="100%">
      <tr><th>Élève</th><th>Points finaux</th><th>Infractions de la période</th></tr>
      {lignes_html}
    </table>
    </body></html>
    """
    chemin_pdf = os.path.join(_dossier_rapports(), f"discipline_{cycle.id}_{horodatage}.pdf")
    _ecrire_pdf(html, chemin_pdf)

    chemin_excel = os.path.join(_dossier_rapports(), f"discipline_{cycle.id}_{horodatage}.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(["Élève", "Points finaux", "Infractions"])
    for eleve, points, infractions in lignes:
        details = "; ".join(f"{i.type_infraction.libelle} (-{i.type_infraction.points_deduits})" for i in infractions)
        ws.append([eleve.nom_complet, points, details])
    wb.save(chemin_excel)

    rapport = RapportGenere(
        type="discipline",
        titre=titre,
        fichier_pdf=chemin_pdf,
        fichier_excel=chemin_excel,
        cycle_id=cycle.id,
    )
    db.session.add(rapport)
    db.session.commit()
    return rapport
