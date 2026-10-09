"""Éléments communs aux spécifications mobilier / bordures / végétation / CARLA (lot
« mobilier_vegetation_carla » de la librairie graphique). Données du site lues dans le dépôt."""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ASSETS = REPO / "assets"
SPECS = ASSETS / "specs"
QA = ASSETS / "qa" / "mobilier_vegetation_carla"
OBJETS = REPO / "recon" / "out" / "paquet_jardin" / "objets"
RELIEF = REPO / "recon" / "out" / "paquet_jardin" / "relief"
VECT = REPO / "data" / "sites" / "paquet_jardin" / "vector"
TILES = REPO / "data" / "raw" / "panoramax" / "paquet_jardin" / "tiles"
O_L93 = (917279.43, 6460289.98, 216.30)
DATE = "2026-10-09"


def tuile(stem: str, rc: str) -> str:
    """Chemin (relatif au dépôt) d'une tuile Panoramax 1000x1000 : tuile('2025-05-18_bc579b89-...', 'r01_c03')."""
    return f"data/raw/panoramax/paquet_jardin/tiles/{stem}_hd/{stem}_hd_{rc}.jpg"


def srgb_lin(hexa: str):
    h = hexa.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(round(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4, 4))
    return out


def couleur(hexa, ral=None, rugosite=0.6, metallique=0.0, note=None):
    d = {"srgb": hexa, "lineaire": srgb_lin(hexa), "rugosite": rugosite, "metallique": metallique}
    if ral:
        d["ral"] = ral
    if note:
        d["note"] = note
    return d


# Couleurs de référence (sRGB approximatives des teintes RAL ; valeurs PBR indicatives, à
# recaler sur les photos du site dans Unreal). « metallique » = 1 pour le métal nu (galvanisé).
COULEURS = {
    "galvanise_vieilli": couleur("#A3A7A4", "aspect galvanisé (zinc patiné, ≈ RAL 9006/9007)", 0.55, 1.0,
                                 "acier galvanisé brut des candélabres, arceaux et mâts : gris clair mat, marbrures"),
    "gris_aluminium": couleur("#A5A8A6", "RAL 9006", 0.45, 0.8, "lanternes, capots"),
    "gris_clair_7035": couleur("#CBD0CC", "RAL 7035", 0.55, 0.0, "armoire de commande des feux"),
    "anthracite_7016": couleur("#383E42", "RAL 7016", 0.5, 0.0, "abri, poteau d'arrêt, mât caméra"),
    "noir_9005": couleur("#141414", "RAL 9005", 0.45, 0.0, "potelets, totem, plaques"),
    "blanc_9016": couleur("#F1F0EA", "RAL 9016", 0.4, 0.0, "tête de potelet, lisse, bandes"),
    "blanc_retro": couleur("#E8E8E2", "film rétroréfléchissant blanc (classe 1/2)", 0.3, 0.0,
                           "bandes des potelets ; dans Unreal : Specular 0.5 + léger Emissive si phares"),
    "jaune_1023": couleur("#F6C700", "RAL 1023", 0.45, 0.0, "couvercle de corbeille, disque C1"),
    "rouge_3000": couleur("#AF2B1E", "RAL 3000", 0.45, 0.0, "poteau d'incendie"),
    "bleu_5010": couleur("#0E4C92", "RAL 5010", 0.4, 0.0, "fût de barrière levante"),
    "bleu_pr_smmag": couleur("#1D63B3", None, 0.4, 0.0, "bandeau « P+R » du totem (lu sur photo 2025-05-18)"),
    "beige_1015": couleur("#E6D2B5", "RAL 1015", 0.6, 0.0, "armoire technique beige (réseaux)"),
    "brun_8023": couleur("#8A4F2E", "≈ RAL 8023 (brun orangé, rouille)", 0.6, 0.2,
                         "mâts acier bruns porte-câbles (peinture vieillie, coulures de rouille)"),
    "bois_creosote": couleur("#6E4E36", None, 0.85, 0.0, "poteau bois de réseau (brun, fendillé)"),
    "bois_banc": couleur("#8A5A33", None, 0.7, 0.0, "lattes de banc (pin/chêne lasuré, brun moyen)"),
    "chataignier_grise": couleur("#8C7A62", None, 0.85, 0.0, "ganivelle de châtaignier grisée"),
    "vert_6005": couleur("#114232", "RAL 6005", 0.5, 0.0, "clôtures en panneaux rigides (variante grise RAL 7016)"),
    "verre_abri": couleur("#C9D3D6", None, 0.05, 0.0,
                          "verre feuilleté clair : opacité 0.15-0.25, transmission ; bandes sérigraphiées blanches"),
    "beton_clair": couleur("#BDBBB3", None, 0.85, 0.0, "béton des bordures, socles, dalles podotactiles"),
    "granit_clair": couleur("#A9A7A1", None, 0.75, 0.0, "pavés de granit"),
    "rouge_k": couleur("#C8102E", None, 0.5, 0.0, "rouge des équipements de chantier (K2/K16)"),
}

# Repère et orientation (rappel de assets/CONVENTIONS.md + écart relevé dans l'atelier objets).
ORIENTATION = {
    "asset": "mètres, Z vers le haut, pivot au pied sur le sol fini (z = 0), FACE AVANT VERS +Y",
    "atelier_objets": ("recon/out/paquet_jardin/objets/instances.json et mobilier.geojson : yaw_deg tourne l'axe +X "
                       "du prototype (face, ouverture d'abri, crosse) vers la direction voulue (yaw = 90 − azimut)"),
    "conversion": "yaw_asset_deg = yaw_atelier_deg − 90 (asset face +Y) ; les positions ci-dessous donnent les deux",
    "repere_site": "repère local du site : X = E − 917279.43, Y = N − 6460289.98, Z = alt − 216.30 (m)",
}


def charger(path: Path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None


def r2(v, n=2):
    return None if v is None else round(float(v), n)


def yaw_asset(yaw_atelier):
    if yaw_atelier is None:
        return None
    return round(((float(yaw_atelier) - 90.0 + 180.0) % 360.0) - 180.0, 1)


def ecrire_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return path


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])
