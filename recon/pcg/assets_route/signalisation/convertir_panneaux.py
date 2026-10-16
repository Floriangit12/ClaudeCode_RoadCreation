"""Conversion des signaux routiers officiels (PDF vectoriels « détourés » du Cerema) en PNG RGBA
détourés, et catalogue machine des panneaux français.

Source : Cerema, site « Équipements des routes et des rues »,
  https://equipementsdelaroute.cerema.fr/format-pdf-detoures-a640.html
  archive IMG/zip/pdfdetoures_cle6bb17e.zip (publiée le 18/10/2023, 5 629 115 octets,
  sha256 f884788604d905689b1d347b71806035109be1d7da90377db4da1ad77b6610af),
  copie locale : D:/DocRoute/01_IISR_Signalisation_Officielle/Signaux_Vectoriels_PDF/PDFdetoures
Licence : pied de page du site « Sauf mention contraire, tous les contenus de ce site sont sous licence
  etalab-2.0 » (Licence Ouverte 2.0) ; la page « Mentions légales » (mise à jour 2014) dit l'inverse
  (droit d'auteur, reprise soumise à accord). Voir DocRoute/09_Signalisation_Verticale_Feux/sources/SOURCES.md.
  Les modèles eux-mêmes sont ceux de l'annexe de l'arrêté du 24 novembre 1967 (acte réglementaire publié).

Ce que fait le script
  1. Chaque page PDF (LibreOffice Draw + pdfcpu) commence par un rectangle blanc pleine page (fond de la
     page Draw) : on le neutralise dans le flux de contenu (peinture « f » -> « n »), sans toucher au reste.
  2. Le contour extérieur des panneaux à listel blanc est tracé par un filet de dessin gris foncé
     (#1B1918, 0,23 pt) qui n'existe pas sur un vrai panneau : il est recoloré dans la couleur du listel
     (option --garder-filet pour le conserver).
  3. Rendu PyMuPDF avec canal alpha, rognage sur l'emprise opaque, deuxième rendu au zoom exact pour que
     le grand côté fasse --taille px (1024 par défaut), mise au format exact par bourrage transparent.
  4. Contrôle : coins transparents pour les formes non rectangulaires, taux de couverture cohérent avec la
     forme (disque ≈ 0,785, octogone ≈ 0,83, triangle ≈ 0,43-0,50, carré/rectangle ≈ 1).
  5. Catalogue JSON : code, nom (annexe de l'arrêté de 1967, version consolidée septembre 2025), famille,
     forme, dimensions par gamme (IISR 1re partie art. 5-3 et 9-1 D), fichier, licence / source, contrôle.

Commandes
  python recon/pcg/assets_route/signalisation/convertir_panneaux.py                 # tout convertir
  python recon/pcg/assets_route/signalisation/convertir_panneaux.py --codes AB4,AB3a,B14_50
  python recon/pcg/assets_route/signalisation/convertir_panneaux.py --planches      # + planches de contrôle

Les PDF sont des fichiers téléchargés : ce script ne fait que les lire (PyMuPDF) et n'exécute rien d'eux.
Dépendances : pymupdf, numpy, Pillow, scipy (site utilisateur) : lancer avec « python -P » depuis la racine du dépôt
(« python -I » masque le site utilisateur). Durée : ≈ 3 min pour les 863 PDF (16/10/2026).
Le catalogue enregistre des chemins relatifs à la racine du dépôt (champ « fichier ») et un champ « usage ».
"""
import argparse
import hashlib
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

RACINE = Path(__file__).resolve().parents[4]
DOCROUTE = Path("D:/DocRoute")
SOURCE_DEF = DOCROUTE / "01_IISR_Signalisation_Officielle/Signaux_Vectoriels_PDF/PDFdetoures"
ANNEXE_DEF = DOCROUTE / "01_IISR_Signalisation_Officielle/Annexe_Panneaux_IISR_Septembre_2025.pdf"
SORTIE_DEF = RACINE / "assets/lib/route_fr/panneaux"
CATALOGUE_DEF = RACINE / "assets/specs/route/panneaux_fr_catalogue.json"

ZIP_URL = "https://equipementsdelaroute.cerema.fr/IMG/zip/pdfdetoures_cle6bb17e.zip"
ZIP_SHA256 = "f884788604d905689b1d347b71806035109be1d7da90377db4da1ad77b6610af"
LICENCE = {
    "licence": "Licence Ouverte / Open Licence 2.0 (etalab-2.0) — présumée",
    "fondement": "pied de page de equipementsdelaroute.cerema.fr : « Sauf mention contraire, tous les contenus "
                 "de ce site sont sous licence etalab-2.0 » (consulté le 16/10/2026)",
    "reserve": "la page « Mentions légales » du même site (mise à jour le 24/09/2014) indique que les contenus "
               "sont couverts par le droit d'auteur et que toute reprise est soumise à l'accord de l'auteur "
               "(art. L.122-4 CPI) : contradiction non levée, confiance moyenne",
    "attribution": "Signaux routiers : Cerema / DSR — equipementsdelaroute.cerema.fr, « Signaux au format PDF "
                   "détourés » (18/10/2023), Licence Ouverte 2.0 ; PNG dérivés (fond retiré, filet de dessin "
                   "recoloré, rendu 1024 px)",
    "source_url": "https://equipementsdelaroute.cerema.fr/format-pdf-detoures-a640.html",
    "archive": ZIP_URL,
    "archive_sha256": ZIP_SHA256,
    "modeles_reglementaires": "annexe de l'arrêté du 24 novembre 1967 modifié (version consolidée septembre 2025)",
    "diffusion": "PNG non versionnés (assets/lib/route_fr/panneaux/.gitignore) ; réutilisation dans le simulateur "
                 "avec l'attribution ci-dessus",
}

# --------------------------------------------------------------------------- dimensions réglementaires
SRC_53 = {"doc": "IISR 1re partie (VC 20250904)", "page": 10, "article": "5-3, 1) tableau des sept gammes"}
GAMMES = {  # mm — IISR 1re partie art. 5-3 1), p. 10 (tableau lu sur tuiles)
    "triangle": {"tres_grande": 1500, "grande": 1250, "normale": 1000, "petite": 700, "miniature": 500},
    "disque": {"tres_grande": 1250, "grande": 1050, "normale": 850, "petite": 650, "miniature": 450},
    "octogone": {"tres_grande": 1200, "grande": 1000, "normale": 800, "petite": 600, "miniature": 400},
    "carre": {"exceptionnelle": 1500, "superieure": 1200, "tres_grande": 1050, "grande": 900, "normale": 700,
              "petite": 500, "miniature": 350},
}
NOTE_GAMMES = ("côté nominal entre sommets théoriques (angles arrondis) ; triangle et disque miniatures : 400 mm "
               "admis exceptionnellement (ouvrage contraint) ; gammes exceptionnelle et supérieure réservées aux "
               "C et CE de présignalisation des aires annexes ; règle générale : gamme normale (IISR 1 art. 5-3 p. 10-11)")
SPECIFIQUES = {  # longueur x hauteur mm — IISR 1re partie art. 5-3 1), p. 10, second tableau
    "B30": {"petite": [500, 650], "normale": [700, 900], "grande": [900, 1150]},
    "B51": {"petite": [500, 650], "normale": [700, 900], "grande": [900, 1150]},
    "B56": {"petite": [600, 900], "normale": [1200, 1800], "grande": [1600, 2400]},
    "B58": {"petite": [600, 900], "normale": [1200, 1800], "grande": [1600, 2400]},
    "C3": {"normale": [600, 800]},
    "C14": {"normale": [900, 1300]},
    "C25a": {"normale": [1600, 2400]},
    "C25b": {"normale": [1600, 2400], "grande": [2400, 3600]},
    "C117": {"normale": [900, 120], "grande": [1050, 1500],
             "_note": "valeur imprimée « 900 x 120 » (probable coquille pour 900 x 1200, non vérifiable)"},
}
PANONCEAUX_LXH = [  # IISR 1re partie art. 9-1 D, p. 22 (tableau lu sur tuiles) — longueur x hauteur mm
    [350, 150], [500, 150], [500, 200], [700, 200], [350, 250], [900, 250], [500, 300], [1000, 300],
    [350, 350], [500, 350], [700, 350], [1200, 400], [500, 500], [900, 500], [1500, 500], [1000, 600],
    [1200, 600], [700, 700]]
VARIABLE_D = ("dimensions fonction des inscriptions : longueurs 800 à 3500 mm, hauteurs 250 à 1200 mm (pas de "
              "100 ou 150 mm au-delà) — IISR 1 art. 5-3 2) p. 11 ; hauteur de caractères selon la vitesse "
              "(IISR 5 art. 83 p. 48)")
BALISES = {  # IISR 1re partie art. 9-2, p. 23-30
    "J1": {"diametre_mm": 200, "hauteur_hors_sol_mm": 1300, "bande_retro_mm": 200, "bande_sous_tete_mm": 300, "p": 23},
    "J3": {"diametre_mm": 200, "hauteur_hors_sol_mm": 1300, "bande_retro_rouge_mm": 200, "p": 24},
    "J4": {"hauteurs_mm": [400, 600, 800, 1000], "hauteur_bord_inferieur_m": 1.0, "p": 24},
    "J5": {"cote_mm": GAMMES["carre"], "hauteur_bord_inferieur_m": 1.0, "p": 25},
    "J6": {"hauteur_hors_sol_mm": 1000, "largeur_mm": 150, "p": 25},
    "J10": {"hauteur_mm": 1000, "largeur_mm": 200, "p": 26},
    "J11": {"hauteur_mm": [700, 850], "hauteur_min_agglo_mm": 500, "largeur_mm": [150, 200], "p": 26},
    "J12": {"hauteur_mm": [700, 850], "hauteur_min_agglo_mm": 500, "largeur_mm": [150, 200], "p": 27},
    "J13": {"hauteur_hors_sol_mm": 1200, "largeur_mm": 250, "p": 27},
    "J14a": {"diametre_m": [1.0, 2.0], "p": 28},
    "J14b": {"elements_hauteur_m": [[0.71, 1.66], [0.95, 2.20]], "largeur_m": [0.32, 0.40], "p": 28},
    "J15a": {"hauteur_max_mm": 20, "surface_max_cm2": 150, "p": 29},
    "J16": {"carre_mm": 130, "hauteur_hors_sol_m": [0.5, 1.0], "p": 29},
}
FEUX = {  # IISR 6e partie art. 109-4 p. 10 et 111 p. 35-36
    "R11": {"diametre_mm": [200, 300], "note": "rouge 300 + jaune/vert 200 admis"},
    "R13": {"diametre_mm": [200, 300]}, "R14": {"diametre_mm": [300], "note": "« le plus souvent 300 mm »"},
    "R15": {"diametre_mm": [200, 300]}, "R16": {"diametre_mm": [200, 300]},
    "R17": {"diametre_mm": [200, 300], "note": "assimilés aux feux circulaires"},
    "R18": {"diametre_mm": [200, 300]}, "R19": {"diametre_mm": [90, 200]},
    "R22": {"diametre_mm": [200, 300], "repetiteur_mm": 90}, "R23": {"diametre_mm": [200, 300], "repetiteur_mm": 90},
    "R24": {"diametre_min_mm": 160, "diametre_min_traversee_tc_mm": 200},
}

FAMILLES = {
    "Feux_R": "feux", "Ideogrammes_ID": "ideogramme", "Panneaux_A": "danger_A",
    "Panneaux_AB": "intersection_priorite_AB", "Panneaux_B": "prescription_B", "Panneaux_C": "indication_C",
    "Panneaux_CE": "services_CE", "Panneaux_D": "reperage_direction_D", "Panneaux_E_EB": "localisation_E_EB",
    "Panneaux_G_balises_J": "passage_niveau_G_balises_J", "Panneaux_H": "touristique_H",
    "Panneaux_SR": "securite_routiere_SR", "panneaux_K": "temporaire_K", "Panonceaux_M": "panonceau_M",
    "Symboles_SC": "symbole_SC", "Symboles_SI": "symbole_SI", "Symboles_SU_SE": "symbole_SU_SE",
}
PREFIXES = ["AB", "AK", "CE", "Da", "Dc", "Dp", "Dv", "EB", "ID", "KC", "KD", "KM", "KR", "KS", "KX", "SC", "SE",
            "SI", "SR", "SU", "XA", "A", "B", "C", "D", "E", "G", "H", "J", "K", "M", "R"]
FILET_SOMBRE = re.compile(rb"0\.10588\d*\s+0\.09803\d*\s+0\.09411\d*\s+RG")
FOND = re.compile(rb"(1 1 1 rg|/\w+ cs 1 1 1 sc)\s+((?:[-\d.]+\s+){2}m\s+(?:(?:[-\d.]+\s+){2}l\s+)+h\s+)(f\*?)")
PREMIER_RG = re.compile(rb"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+rg")
# Textes d'annotation laissés dans certains PDF source (zones de texte LibreOffice en police DejaVuSans / Arial :
# légendes, cotes, « exemple », doublon de mot) — ils ne font pas partie du signal. Les inscriptions réelles des
# panneaux sont des contours vectorisés ou en polices « Caracteres L1/L2/L4 », jamais retirées.
TEXTES_PARASITES = {
    "M11a": r"^(autor|is.s)$", "SR4": r".", "Dp1a": r"mm, Hc", "Dp1b": r"mm, Hc", "Dp2a": r"mm, Hc",
    "Dp2b": r"mm, Hc", "D44": r"(Ensemble|exemple)", "D45": r"(Ensemble|exemple)", "G2": r"panonceau associ",
    "G3": r"panonceau associ", "KM": r"exemple", "K2_ex1": r"^(Avers|Envers)$", "SU1": r".", "SU3": r".",
    "E41-42-43-44-45": r".", "ID15a33": r"Mai 1997",
}


# Dessins où l'enclave transparente est du fond (entre deux poteaux et une ligne de sol, cadre de portique) :
# pas de bouchage (vérifié sur planches de contrôle).
SANS_BOUCHAGE = re.compile(r"^(Dc29_ex|Dc43_ex|E37[ab]|K15_ex|G3$)")


def retirer_textes_parasites(page, stem):
    motif = TEXTES_PARASITES.get(stem)
    if not motif:
        return []
    retires = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s["text"].strip() and s["font"] in ("DejaVuSans", "ArialMT") and re.search(motif, s["text"].strip()):
                    page.add_redact_annot(pymupdf.Rect(s["bbox"]), fill=False)
                    retires.append(s["text"].strip())
    if retires:
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                              text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    return retires


# --------------------------------------------------------------------------- outils
def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def normaliser(stem):
    """Nom de fichier -> (code canonique, variante). Ex. 'B14_50' -> ('B14', '50'), 'DA31A' -> ('Da31a', '')."""
    s = stem.replace("E_46", "E46")
    if s.startswith("R11_greque"):
        return "R11v", "croix_grecque_arriere"
    if s.startswith("E41-42-43-44-45"):
        return "E41-E45", "cartouches"
    low = s.lower()
    pre = next((p for p in PREFIXES if low.startswith(p.lower()) and len(s) > len(p) and
                (s[len(p)].isdigit() or s[len(p)] in "_-")), None)
    if pre is None:
        return s, ""
    reste = s[len(pre):].lstrip("_")
    m = re.match(r"(\d+)([A-Za-z]*\d*)(.*)", reste)
    if not m:
        return pre + reste, ""
    num, suf, var = m.group(1), m.group(2).lower(), m.group(3).strip("_-")
    if pre == "B" and num == "21" and var[:1].isdigit():          # B21-1, B21-2
        return f"B21-{var[0]}", var[1:].strip("_-")
    if "ex" in suf:                                               # J4ex2, M9zex1cdr, KR42ex2_dc
        i = suf.index("ex")
        var, suf = suf[i:] + ("_" + var if var else ""), suf[:i]
    if suf.endswith("ex") and len(suf) > 2:
        var, suf = "ex" + var, suf[:-2]
    if pre == "M" and num == "10" and suf == "bl":
        suf, var = "b", "L" + var
    return f"{pre}{num}{suf}", var


def forme_de(code, famille, ratio):
    c = code
    if famille == "feux":
        return "feu_boitier"
    if famille.startswith("symbole") or famille == "ideogramme":
        return "symbole"
    if c in ("AB4",):
        return "octogone"
    if c in ("AB6", "AB7"):
        return "carre_sur_pointe"
    if c in ("AB3a",):
        return "triangle_pointe_en_bas"
    if c in ("AB3b", "AB5"):
        return "triangle_pointe_en_bas+panonceau"
    if c.startswith("M12"):
        return "carre" if abs(ratio - 1) < 0.03 else "triangle_pointe_en_bas"  # _C : subjectile carré foncé
    if re.match(r"^(A\d|AB[12]|AB25|AK\d|XA)", c):
        return "triangle"
    if c == "B1j" or c.startswith(("B6b", "B30", "B50", "B51", "B52", "B53", "B54", "B55", "B56", "B57", "B58", "B59")):
        return "carre" if abs(ratio - 1) < 0.04 else "rectangle"
    if re.match(r"^B\d", c):
        return "disque"
    if c in ("J1", "J3", "J1bis"):
        return "balise_cylindrique"
    if c == "J5":
        return "carre"
    if re.match(r"^(D21|Dv21|Dp\d|Dc29|D29|H22|H31|H32)", c):
        return "rectangle_a_pointe"
    return "carre" if abs(ratio - 1) < 0.04 else "rectangle"


def dimensions_de(code, forme, famille):
    """Dimensions réglementaires (mm) par gamme, avec leur source."""
    base = re.sub(r"[-_].*$", "", code)
    if base in SPECIFIQUES:
        d = dict(SPECIFIQUES[base])
        return {"type": "longueur_x_hauteur_mm", "gammes": {k: v for k, v in d.items() if not k.startswith("_")},
                "note": d.get("_note", ""), "source": {**SRC_53, "article": "5-3, 1) second tableau"}}
    if famille == "feux":
        k = re.match(r"R\d+", code).group(0) if re.match(r"R\d+", code) else code
        return {"type": "optiques", "valeurs": FEUX.get(k, {}),
                "source": {"doc": "IISR 6e partie (VC 20250904)", "page": "10 ; 35-36", "article": "109-4 ; 111"}}
    if famille == "panonceau_M":
        if code.startswith("M12"):
            return {"type": "cote_nominal_mm", "plage": [150, 300], "exceptionnel": 500,
                    "note": "500 mm seulement en l'absence de panneau AB et si lisibilité insuffisante",
                    "source": {"doc": "IISR 1re partie", "page": 22, "article": "9-1 D"}}
        return {"type": "longueur_x_hauteur_mm", "admissibles": PANONCEAUX_LXH,
                "regle": "longueur égale (ou la plus proche) à la largeur du panneau complété ; ex. : sous un "
                         "triangle normal 1000 -> 1000 x 300 ; sous un disque normal 850 -> 900 x 250 ; sous un carré "
                         "normal 700 -> 700 x 200/350",
                "source": {"doc": "IISR 1re partie", "page": 22, "article": "9-1 D (tableau lu sur tuiles)"},
                "confiance_regle": "moyenne (association largeur panneau/panonceau déduite du tableau)"}
    if code in BALISES or base in BALISES:
        b = BALISES.get(code, BALISES.get(base))
        return {"type": "balise", "valeurs": {k: v for k, v in b.items() if k != "p"},
                "source": {"doc": "IISR 1re partie", "page": b["p"], "article": "9-2"}}
    if forme in ("triangle", "triangle_pointe_en_bas", "triangle_pointe_en_bas+panonceau"):
        return {"type": "cote_nominal_mm", "gammes": GAMMES["triangle"], "note": NOTE_GAMMES, "source": SRC_53}
    if forme == "disque":
        return {"type": "diametre_mm", "gammes": GAMMES["disque"], "note": NOTE_GAMMES, "source": SRC_53}
    if forme == "octogone":
        return {"type": "entre_cotes_opposes_mm", "gammes": GAMMES["octogone"], "note": NOTE_GAMMES, "source": SRC_53}
    if forme == "carre_sur_pointe" or (forme == "carre" and famille in (
            "indication_C", "services_CE", "prescription_B", "intersection_priorite_AB")):
        g = dict(GAMMES["carre"])
        if famille not in ("indication_C", "services_CE"):
            g.pop("exceptionnelle"); g.pop("superieure")
        return {"type": "cote_nominal_mm", "gammes": g, "note": NOTE_GAMMES, "source": SRC_53}
    if code.startswith("B1j"):
        return {"type": "regle", "regle": "encart de la gamme du B1 remplacé ; carré de deux gammes au-dessus",
                "source": SRC_53}
    if famille in ("reperage_direction_D", "localisation_E_EB", "touristique_H"):
        return {"type": "variable", "regle": VARIABLE_D,
                "source": {"doc": "IISR 1re partie", "page": "11-13", "article": "5-3, 2) à 6)"}}
    if famille == "securite_routiere_SR":
        return {"type": "variable", "regle": "IISR 1 art. 5-3 7) p. 13-14 (SR3 : 1200x1800 / 1600x2400 / 2400x3600)",
                "source": {"doc": "IISR 1re partie", "page": "13-14", "article": "5-3, 7)"}}
    if famille == "temporaire_K":
        return {"type": "hors_perimetre", "regle": "signalisation temporaire : IISR 8e partie (non traitée ici)"}
    return {"type": "non_defini", "regle": "voir l'article correspondant de l'IISR"}


NOMS_FEUX = {  # arrêté du 24/11/1967 art. 7 (p. 62-68) et IISR 6e partie art. 109-3 (p. 5-9)
    "R13c": "Signal tricolore modal pour cycles", "R14": "Signal tricolore directionnel (flèches)",
    "R16": "Signal d'anticipation directionnel (jaune clignotant, associé à un R11v)",
    "R17": "Signal pour véhicules des services réguliers de transport en commun",
    "R18": "Signal directionnel pour véhicules des services réguliers de transport en commun",
    "R19": "Signal d'autorisation conditionnelle de franchissement pour cycles",
    "R22": "Signal tricolore de contrôle de flot",
}


def nom_de(code, noms):
    """Signification du code : annexe de l'arrêté, sinon code générique, sinon code voisin (signalé)."""
    if code in noms:
        return noms[code], "annexe 1967 (sept. 2025)"
    base = re.match(r"^([A-Za-z]+\d+)", code)
    base = base.group(1) if base else code
    for k in (code, code[:4], base):
        if k in NOMS_FEUX:
            return NOMS_FEUX[k], "arrêté 1967 art. 7 / IISR 6 art. 109-3"
    if code.split("-")[0] in noms:
        return noms[code.split("-")[0]], "annexe 1967 (code générique)"
    if base in noms:
        return noms[base], "annexe 1967 (code générique " + base + ")"
    voisins = sorted(k for k in noms if k.startswith(base) and not k[len(base):len(base) + 1].isdigit())
    if voisins:
        return noms[voisins[0]], "annexe 1967 (code voisin " + voisins[0] + ", à vérifier)"
    return "", ""


def noms_annexe(chemin):
    """Code -> signification, lus dans les tableaux de l'annexe de l'arrêté de 1967 (consolidée sept. 2025)."""
    noms = {}
    if not chemin.exists():
        return noms
    doc = pymupdf.open(chemin)
    for page in doc:
        try:
            tabs = page.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            for row in t.extract():
                if not row or not row[0]:
                    continue
                code = re.sub(r"\s+", "", row[0])
                if not re.match(r"^[A-Z][A-Za-z]{0,2}\d", code):
                    continue
                txt = next((c for c in reversed(row) if c and c.strip() and c is not row[0]), "")
                lignes = [l.strip() for l in (txt or "").split("\n")
                          if l.strip() and not re.match(r"^(Modifi|Cr[ée]{1,2}|Abrog|Remplac|Ajout)", l.strip())]
                sig = " ".join(lignes).strip()
                if sig and code not in noms:
                    noms[code] = sig
    return noms


CHEMIN = rb"((?:[-\d.]+\s+){2}m\s+(?:(?:[-\d.]+\s+){2}(?:l|c)\s+|(?:[-\d.]+\s+){6}c\s+)+h\s+)"
CHEMIN_BLANC_SUIVANT = re.compile(rb"\s*" + CHEMIN + rb"(f\*?)")
CONTOUR_SEUL = re.compile(rb"\s*(0\.10588\d*\s+0\.09803\d*\s+0\.09411\d*)\s+RG\s+q\s+([\d.]+)\s+w([^\n]*)\n"
                          + CHEMIN + rb"S\s+Q")


def _emprise(chemin):
    nums = [float(x) for x in re.findall(rb"-?[\d.]+", chemin)]
    xs, ys = nums[0::2], nums[1::2]
    return max(xs) - min(xs), max(ys) - min(ys)


def nettoyer_flux(page, garder_filet):
    """Neutralise le fond blanc pleine page (et un éventuel second rectangle blanc au cadre du signal) ;
    recolore le filet de dessin extérieur ; donne un corps blanc aux panonceaux dessinés par leur seul
    contour. Retourne un journal des opérations."""
    journal = {"fond_retire": False, "cadre_blanc_retire": False, "filet_recolore": False,
               "corps_blanc_ajoute": False}
    mb, r = page.mediabox, page.rect
    for xref in page.get_contents():
        data = page.parent.xref_stream(xref)
        nouveau = data
        m = None
        for m in FOND.finditer(data[:4000]):
            w, h = _emprise(m.group(2))
            if w >= 0.98 * mb.width and h >= 0.98 * mb.height:
                nouveau = data[:m.start(3)] + b"n" + data[m.end(3):]
                journal["fond_retire"] = True
                break
        if not journal["fond_retire"]:
            continue
        pos = m.start(3) + 1
        # second rectangle blanc au cadre exact du signal (ex. B14_50), encore peint en blanc 1 1 1
        s2 = CHEMIN_BLANC_SUIVANT.match(nouveau, pos)
        if s2:
            w, h = _emprise(s2.group(1))
            if w >= 0.98 * r.width and h >= 0.98 * r.height:
                nouveau = nouveau[:s2.start(2)] + b"n" + nouveau[s2.end(2):]
                journal["cadre_blanc_retire"] = True
                pos = s2.start(2) + 1
        if garder_filet:
            break
        # panonceau dessiné par son seul contour (ex. M9c) : corps et contour blancs (pas de listel, IISR 1 art. 9-1 C)
        c0 = CONTOUR_SEUL.match(nouveau, pos)
        if c0:
            w, h = _emprise(c0.group(4))
            if w >= 0.97 * r.width and h >= 0.97 * r.height:
                rempl = (b"\n0.9961 0.9961 0.9961 rg 0.9961 0.9961 0.9961 RG\nq " + c0.group(2) + b" w"
                         + c0.group(3) + b"\n" + c0.group(4) + b"B\nQ")
                nouveau = nouveau[:c0.start()] + rempl + nouveau[c0.end():]
                journal["corps_blanc_ajoute"] = True
                journal["filet_recolore"] = True
                break
        apres = nouveau[pos:]
        rg = PREMIER_RG.search(apres)
        filet = FILET_SOMBRE.search(apres)
        if rg and filet and rg.start() < filet.start():
            vals = [float(v) for v in rg.groups()]
            autre_rg = PREMIER_RG.search(apres, rg.end())
            if min(vals) >= 0.95 and (autre_rg is None or filet.start() < autre_rg.start()):
                rgb = " ".join(f"{v:.4f}" for v in vals).encode()
                nouveau = nouveau[:pos + filet.start()] + rgb + b" RG" + nouveau[pos + filet.end():]
                journal["filet_recolore"] = True
        if nouveau is not data:
            page.parent.update_stream(xref, nouveau)
        break
    else:
        return journal
    if nouveau is not data:
        page.parent.update_stream(xref, nouveau)
    return journal


def boucher_trous(img):
    """Rend opaques (blanc) les zones transparentes entièrement enclavées dans le signal (corps de panonceau
    non peint dans le PDF, qui comptait sur le fond blanc de page). Retourne (image, nb_px_bouches)."""
    from scipy import ndimage
    a = np.asarray(img).copy()
    transp = a[:, :, 3] <= 8
    lab, n = ndimage.label(transp)
    bord = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    trous = transp & ~np.isin(lab, list(bord))
    k = int(trous.sum())
    if k:
        a[trous] = (254, 254, 254, 255)
        # pixels d'antialiasing au bord des trous : composer sur blanc
        alpha = a[:, :, 3:4].astype(np.float32) / 255.0
        voisin = ndimage.binary_dilation(trous, iterations=2) & ~trous
        comp = (a[:, :, :3].astype(np.float32) * alpha + 254 * (1 - alpha)).astype(np.uint8)
        a[voisin, :3] = comp[voisin]
        a[voisin, 3] = 255
    return Image.fromarray(a, "RGBA"), k


def composantes(img, seuil=0.02):
    """Nombre d'éléments opaques disjoints représentant plus de `seuil` de l'image (planches d'exemples)."""
    from scipy import ndimage
    a = np.asarray(img)[:, :, 3] > 8
    lab, n = ndimage.label(a)
    if n == 0:
        return 0
    tailles = ndimage.sum(a, lab, range(1, n + 1))
    return int((np.asarray(tailles) > seuil * a.size).sum())


def rendre(page, taille):
    """Rendu RGBA rogné sur l'emprise opaque, grand côté = taille px exactement."""
    r = page.rect
    zoom = taille / max(r.width, r.height)
    for _ in range(3):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=True)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        ys, xs = np.nonzero(a[:, :, 3] > 8)
        if len(xs) == 0:
            return None
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        grand = max(x1 - x0, y1 - y0)
        if grand == taille:
            break
        zoom *= taille / grand
    a = a[y0:y1, x0:x1].astype(np.float32)
    # MuPDF rend en couleurs prémultipliées par alpha : on repasse en alpha « droit » (PNG / PIL / UE)
    al = a[:, :, 3:4]
    a[:, :, :3] = np.where(al > 0, np.minimum(255.0, a[:, :, :3] * 255.0 / np.maximum(al, 1.0)), 0.0)
    img = Image.fromarray(np.round(a).astype(np.uint8), "RGBA")
    w, h = img.size
    if max(w, h) != taille:  # écart résiduel de 1 px : recadrage ou bourrage transparent
        cw, ch = (taille, round(h * taille / w)) if w >= h else (round(w * taille / h), taille)
        fond = Image.new("RGBA", (max(cw, 1), max(ch, 1)), (0, 0, 0, 0))
        fond.paste(img.crop((0, 0, min(w, cw), min(h, ch))), (0, 0))
        img = fond
    return img


def controler(img, forme):
    a = np.asarray(img)[:, :, 3]
    h, w = a.shape
    cov = float((a > 127).mean())
    coins = [int(a[0, 0]), int(a[0, w - 1]), int(a[h - 1, 0]), int(a[h - 1, w - 1])]
    attendu = {"disque": (0.74, 0.80), "octogone": (0.78, 0.86), "triangle": (0.42, 0.60),
               "triangle_pointe_en_bas": (0.42, 0.60), "carre_sur_pointe": (0.45, 0.56),
               "carre": (0.93, 1.0), "rectangle": (0.85, 1.0)}.get(forme)
    ok = True
    notes = []
    if forme in ("disque", "octogone", "triangle", "triangle_pointe_en_bas", "carre_sur_pointe"):
        if max(coins) > 0:
            ok = False
            notes.append("coin non transparent")
    if attendu and not (attendu[0] <= cov <= attendu[1]):
        ok = False
        notes.append(f"couverture {cov:.3f} hors [{attendu[0]}, {attendu[1]}]")
    return {"ok": ok, "couverture_alpha": round(cov, 4), "alpha_coins": coins, "notes": notes}


def planches(entrees, sortie, par_ligne=4, case=250):
    """Planches de contrôle sur damier (pour voir la transparence) ; 4 x 4 cases de 250 px + légende :
    1000 x 1072 px, lisibles sans réduction (règle des tuiles natives ≤ 1092 px, CLAUDE.md)."""
    sortie.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for n0 in range(0, len(entrees), par_ligne * par_ligne):
        lot = entrees[n0:n0 + par_ligne * par_ligne]
        lignes = (len(lot) + par_ligne - 1) // par_ligne
        W, H = par_ligne * case, lignes * (case + 18)
        dam = np.indices((H // 16 + 1, W // 16 + 1)).sum(0) % 2
        dam = np.kron(dam, np.ones((16, 16)))[:H, :W]
        fond = Image.fromarray((150 + 60 * dam).astype(np.uint8)).convert("RGBA")
        from PIL import ImageDraw
        dr = ImageDraw.Draw(fond)
        for i, e in enumerate(lot):
            im = Image.open(e["fichier"]).convert("RGBA")
            im.thumbnail((case - 8, case - 8))
            x, y = (i % par_ligne) * case, (i // par_ligne) * (case + 18)
            fond.alpha_composite(im, (x + (case - im.width) // 2, y + (case - im.height) // 2))
            dr.rectangle([x, y + case, x + case - 1, y + case + 17], fill=(255, 255, 255, 255))
            dr.text((x + 4, y + case + 3), e["id"][:30] + ("" if e["controle"]["ok"] else " !"), fill=(0, 0, 0, 255))
        f = sortie / f"planche_{n0 // (par_ligne * par_ligne):02d}.png"
        fond.convert("RGB").save(f)
        fichiers.append(str(f))
    return fichiers


# --------------------------------------------------------------------------- principal
def chemin_depot(chemin):
    """Chemin relatif à la racine du dépôt (posix) si possible, sinon absolu : le catalogue est versionné."""
    chemin = Path(chemin).resolve()
    try:
        return chemin.relative_to(RACINE).as_posix()
    except ValueError:
        return chemin.as_posix()


def usage_de(famille, exemple):
    """Usage du PNG dans le simulateur (aide au générateur)."""
    if famille == "feux":
        return ("illustration réglementaire (états lumineux dessinés, rayons de clignotement) : référence de "
                "forme et de pictogramme, pas une texture d'état ; le feu est modélisé en 3D et ses optiques animées")
    if exemple:
        return "exemple de composition de l'annexe : ne pas poser tel quel, recomposer (texte, cartouches) pour la scène"
    return "texture de face du panneau (face avant, sans revers ni bord tombé)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=SOURCE_DEF)
    ap.add_argument("--annexe", type=Path, default=ANNEXE_DEF)
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEF)
    ap.add_argument("--catalogue", type=Path, default=CATALOGUE_DEF)
    ap.add_argument("--taille", type=int, default=1024)
    ap.add_argument("--codes", default="", help="liste de noms de fichiers (sans .pdf) à traiter, séparés par des virgules")
    ap.add_argument("--garder-filet", action="store_true")
    ap.add_argument("--planches", action="store_true")
    args = ap.parse_args()

    pdfs = sorted(args.source.rglob("*.pdf"))
    if args.codes:
        voulus = {c.strip() for c in args.codes.split(",")}
        pdfs = [p for p in pdfs if p.stem in voulus]
    noms = noms_annexe(args.annexe)
    args.sortie.mkdir(parents=True, exist_ok=True)
    (args.sortie / ".gitignore").write_text("# PNG dérivés régénérables (convertir_panneaux.py) : non versionnés\n*\n",
                                            encoding="utf-8")
    entrees, echelles = [], []
    for pdf in pdfs:
        rel = pdf.relative_to(args.source)
        dossier = rel.parts[0]
        famille = FAMILLES.get(dossier, dossier)
        sous = "/".join(rel.parts[1:-1])
        doc = pymupdf.open(pdf)
        for ip, page in enumerate(doc):
            rect = page.rect
            journal = nettoyer_flux(page, args.garder_filet)
            journal["textes_parasites_retires"] = retirer_textes_parasites(page, pdf.stem)
            img = rendre(page, args.taille)
            if img is None:
                print("VIDE", rel, file=sys.stderr)
                continue
            trous = 0
            if famille not in ("ideogramme", "feux") and not famille.startswith("symbole")                     and not SANS_BOUCHAGE.match(pdf.stem):
                img, trous = boucher_trous(img)
            journal["px_enclaves_bouches"] = trous
            ncomp = composantes(img)
            code, variante = normaliser(pdf.stem)
            ident = pdf.stem + (f"_p{ip + 1}" if doc.page_count > 1 else "")
            nom, nom_src = nom_de(code, noms)
            ratio = img.width / img.height
            forme = forme_de(code, famille, ratio)
            fichier = args.sortie / dossier / (ident + ".png")
            fichier.parent.mkdir(parents=True, exist_ok=True)
            img.save(fichier, optimize=True)
            ctl = controler(img, forme)
            ctl["elements_disjoints"] = ncomp
            if ncomp > 1:
                ctl["notes"].append(f"{ncomp} éléments disjoints : planche d'exemples ou ensemble composé")
            dims = dimensions_de(code, forme, famille)
            dims_pdf_mm = [round(rect.width * 25.4 / 72, 1), round(rect.height * 25.4 / 72, 1)]
            # échelle du dessin : comparaison avec la gamme normale quand elle est définie
            g = dims.get("gammes", {})
            if forme in ("disque", "octogone", "carre") and "normale" in g and isinstance(g["normale"], int):
                echelles.append(g["normale"] / max(dims_pdf_mm))
            e = {
                "id": ident, "code": code, "variante": variante,
                "nom": nom, "nom_source": nom_src,
                "famille": famille, "sous_famille": sous, "forme": forme, "dimensions": dims,
                "exemple_de_composition": ("ex" in variante.lower()) or ncomp > 1,
                "fichier": chemin_depot(fichier),
                "usage": usage_de(famille, ("ex" in variante.lower()) or ncomp > 1),
                "png_px": [img.width, img.height],
                "pdf_source": str(rel).replace("\\", "/"), "pdf_page": ip + 1, "pdf_sha256": sha256(pdf),
                "pdf_cadre_mm": dims_pdf_mm, "traitement": journal, "controle": ctl,
            }
            if forme in ("disque", "octogone", "carre", "carre_sur_pointe", "triangle", "triangle_pointe_en_bas") \
                    and "normale" in g and isinstance(g["normale"], int):
                e["px_par_mm_gamme_normale"] = round(max(img.size) / (g["normale"] * (1.414 if forme == "carre_sur_pointe" else 1.0)), 4)
            entrees.append(e)
            print(("OK " if ctl["ok"] else "?? ") + ident, forme, ctl["couverture_alpha"], ctl["notes"])
    ech = round(statistics.median(echelles), 2) if echelles else None
    catalogue = {
        "meta": {
            "titre": "Catalogue des signaux routiers français — faces PNG RGBA détourées",
            "date": date.today().isoformat(),
            "script": "recon/pcg/assets_route/signalisation/convertir_panneaux.py",
            "png": f"{args.taille} px sur le grand côté, sRGB, fond transparent, rogné sur l'emprise du panneau",
            "conventions": "face avant ; bord inférieur du PNG = bord inférieur du panneau ; taille physique = gamme "
                           "choisie (champ dimensions) ; pas de revers ni de bord tombé (à modéliser)",
            "licence_source": LICENCE,
            "noms": "annexe de l'arrêté du 24 novembre 1967, version consolidée septembre 2025 (tableaux code / "
                    "signification), extraction automatique",
            "echelle_dessin_pdf_estimee": f"1:{ech} (médiane gamme normale / cadre PDF, disques-octogones-carrés) — "
                                          "observation, non documentée par le Cerema" if ech else None,
            "gammes_iisr": {"valeurs_mm": GAMMES, "specifiques": SPECIFIQUES, "panonceaux": PANONCEAUX_LXH,
                            "source": SRC_53},
            "nombre": len(entrees),
            "controle_echecs": [e["id"] for e in entrees if not e["controle"]["ok"]],
        },
        "signaux": entrees,
    }
    if args.planches:
        catalogue["meta"]["planches"] = [chemin_depot(Path(f)) for f in planches(entrees, args.sortie / "_planches")]
    args.catalogue.parent.mkdir(parents=True, exist_ok=True)
    if args.codes and args.catalogue.exists():
        print("(--codes : catalogue existant non écrasé ; écrit à côté)")
        args.catalogue = args.catalogue.with_name(args.catalogue.stem + "_partiel.json")
    args.catalogue.write_text(json.dumps(catalogue, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(entrees)} signaux -> {args.sortie} ; catalogue {args.catalogue} ; échecs de contrôle : "
          f"{len(catalogue['meta']['controle_echecs'])}")


if __name__ == "__main__":
    main()
