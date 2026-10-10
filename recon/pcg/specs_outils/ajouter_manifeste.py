# -*- coding: utf-8 -*-
"""Ajoute au manifeste CC0 les matériaux V2 (BRF, gravier concassé, calcaire) au schéma exact des entrées existantes.
Écriture identique au format d'origine (json indent=1, ensure_ascii=False, fins de ligne CRLF)."""
import json
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/ClaudeCode_RoadCreation/assets")
import telecharger_cc0 as T  # noqa: E402  (fonctions couleur du dépôt, sans effet de bord)

MAN = "D:/ClaudeCode_RoadCreation/assets/manifeste_cc0.json"
API = json.load(open("api_nouveaux.json", encoding="utf-8"))
PREV = "previews/"


def stats(p):
    a = np.asarray(Image.open(p).convert("RGB").resize((1024, 1024), Image.LANCZOS), np.float64) / 255.0
    lab = T.rgb_vers_lab(a[::4, ::4].reshape(-1, 3))
    return lab.mean(0), float(lab[:, 0].std())


def lab_lin(lin):
    s = T.lin_vers_srgb(np.array(lin, float))
    return T.rgb_vers_lab(s.reshape(1, 3))[0], [int(round(v * 255)) for v in s]


def de(a, b):
    return round(float(np.linalg.norm(np.asarray(a) - np.asarray(b))), 1)


def correction(src, cib, gL, gab):
    return {"espace": "CIE L*a*b* (D65), sur l'albédo sRGB",
            "formule": "L' = gain_L·L + decalage_L ; a' = gain_ab·a + decalage_a ; b' = gain_ab·b + decalage_b",
            "gain_L": gL, "decalage_L": round(cib[0] - gL * src[0], 2), "gain_ab": gab,
            "decalage_a": round(cib[1] - gab * src[1], 2), "decalage_b": round(cib[2] - gab * src[2], 2),
            "lab_moyen_source": [round(float(v), 2) for v in src], "lab_cible": [round(float(v), 2) for v in cib],
            "delta_E_avant": de(src, cib), "delta_E_apres": 0.0,
            "mode_script": "'cible' : le script recalcule les décalages sur la texture téléchargée pour que la moyenne atteigne lab_cible avec ces gains ; 'manifeste' applique les valeurs telles quelles"}


def cible(lin, mesure):
    lab, s8 = lab_lin(lin)
    return {"albedo_lineaire": lin, "srgb8": s8, "lab": [round(float(v), 2) for v in lab], "mesure": mesure}


LIC = {"nom": "CC0 1.0 Universal (transfert dans le domaine public)", "url": "https://creativecommons.org/publicdomain/zero/1.0/",
       "attribution_requise": False}
UV = {"primvar": "st1", "repere": "UV en mètres de la scène (st1) ; UsdTransform2d scale = 1/tile_m"}
ZIP = {"albedo": "*_Color.jpg", "normale": "*_NormalGL.jpg", "rugosite": "*_Roughness.jpg", "ao": "*_AmbientOcclusion.jpg",
       "hauteur": "*_Displacement.jpg", "opacite": "*_Opacity.jpg", "metal": "*_Metalness.jpg"}
RUG = {"gain": 1.0, "decalage": 0.0, "motif": None}
QA_NOTE = None


def acg(nom, idd, libelle, prio, classes, tile, tile_src, corr, cib, photos, alts, notes):
    a = API[idd]
    return {"nom": nom, "categorie": "materiaux", "type": "sol_tuilable", "libelle": libelle, "priorite": prio,
            "usage_scene": {"classes": classes, "looks": []}, "source": "ambientCG", "id": idd, "page": a["page"],
            "auteur": "Lennart Demes (ambientCG)", "type_source": "Material", "methode": a["methode"],
            "cartes_disponibles": a["maps"], "telechargements": {k: a["dl"][k] for k in ("1K", "2K", "4K")},
            "cartes_zip": dict(ZIP), "licence": dict(LIC), "tile_m": tile, "tile_m_source": tile_src, "uv": dict(UV),
            "correction_teinte": corr, "cible": cib, "rugosite": dict(RUG), "photos_reference": photos,
            "qa": {"validation": [], "selection": QA_NOTE}, "alternatives_examinees": alts, "notes": notes}


def ph(nom, idd, libelle, prio, classes, corr, cib, photos, alts, notes):
    f, inf = API[idd]["files"], API[idd]["info"]
    tel = {}
    for R, r in (("1K", "1k"), ("2K", "2k"), ("4K", "4k")):
        fi = {"albedo": f["Diffuse"][r]["jpg"], "normale": f["nor_gl"][r]["png"], "rugosite": f["Rough"][r]["jpg"],
              "ao": f["AO"][r]["jpg"], "hauteur": f["Displacement"][r]["png"]}
        fi = {k: {"url": v["url"], "taille_o": v["size"], "md5": v["md5"]} for k, v in fi.items()}
        tel[R] = {"format": "fichiers", "fichiers": fi, "taille_o": sum(v["taille_o"] for v in fi.values())}
    aut = ", ".join(f"{n} ({r})" for n, r in sorted(inf["authors"].items(), key=lambda kv: kv[1] != "Processing"))
    dim = inf["dimensions"][0] / 1000.0
    return {"nom": nom, "categorie": "materiaux", "type": "sol_tuilable", "libelle": libelle, "priorite": prio,
            "usage_scene": {"classes": classes, "looks": []}, "source": "Poly Haven", "id": idd,
            "page": f"https://polyhaven.com/a/{idd}", "auteur": aut, "type_source": "texture",
            "cartes_disponibles": [k for k in f if k not in ("blend", "gltf", "mtlx")], "telechargements": tel,
            "licence": dict(LIC), "tile_m": round(dim, 2), "tile_m_source": f"API ({dim:.2f} m)", "uv": dict(UV),
            "correction_teinte": corr, "cible": cib, "rugosite": dict(RUG), "photos_reference": photos,
            "qa": {"validation": [], "selection": QA_NOTE}, "alternatives_examinees": alts, "notes": notes}


# ---------------------------------------------------------------- mesures (aperçus API, 1024 px)
S = {k: stats(PREV + p) for k, p in [("WoodChips001", "WoodChips001.jpg"), ("WoodChips002", "WoodChips002.jpg"),
                                      ("WoodChips003", "WoodChips003.jpg"), ("Travertine009", "Travertine009.jpg"),
                                      ("gravel_floor_02", "ph_gravel_floor_02_1k.jpg"), ("Gravel035", "Gravel035.jpg"),
                                      ("Rocks006", "Rocks006.jpg"), ("bicolour_gravel", "ph_bicolour_gravel_1k.jpg"),
                                      ("gravel_stones", "ph_gravel_stones_1k.jpg"), ("wood_chip_path", "ph_wood_chip_path_1k.jpg"),
                                      ("Travertine001", "Travertine001.img"), ("Concrete034", "Concrete034.jpg")]}
for k, (m, sd) in S.items():
    print(f"{k:18s} Lab {np.round(m, 2)}  sigma_L {sd:.2f}")

# ---------------------------------------------------------------- cibles
C_BRF = cible([0.062, 0.047, 0.038], "photo utilisateur 2.png (Heinrich & Bock, hors site, 2026-10-10) : rapport linéaire BRF / enrobé voisin = 0,206 (médianes de zones éclairées de la même façon) × albédo d'enrobé vieilli 0,24 (a priori, entre enrobe_trottoir 0,21 et enrobe_bbsg_ancien 0,26) ; confiance faible (photo de catalogue retouchée possible)")
C_GRAV = cible([0.311, 0.311, 0.292], "reprise de la cible de gravillons_ilot (ortho 2022, îlot effilé gravillonné du Vercors) : même matériau en place, texture concassée plus fidèle")
C_CALC = cible([0.46, 0.43, 0.36], "a priori : calcaire clair beige (photo utilisateur 4.webp, bordures calcaire autour d'un îlot pavé ; non mesurable : pas de référence d'albédo dans l'image) ; confiance faible")


def alt(src, idd, cib_lab):
    m, sd = S[idd]
    return {"source": src, "id": idd, "delta_E_brut": de(m, cib_lab), "ecart_type_L": round(sd, 2)}


nouveaux = [
    acg("brf_bois_concasse", "WoodChips003",
        "BRF / bois concassé brun (plaquettes et broyat de 2-5 cm) en couche de 7-10 cm, 3-5 cm sous le dessus des bordures",
        2, ["ilot/remplissage brf_bois_concasse", "massifs et pieds d'arbres paillés (a priori 2025)"],
        1.6, "API (1.60 m)", correction(S["WoodChips003"][0], C_BRF["lab"], 0.9, 0.6), C_BRF,
        ["photo utilisateur 2.png (référence d'aspect, hors site ; non versionnée)"],
        [alt("acg", "WoodChips001", C_BRF["lab"]), alt("acg", "WoodChips002", C_BRF["lab"]), alt("ph", "wood_chip_path", C_BRF["lab"])],
        "Choix par comparaison à échelle égale (0,6 m) avec la photo utilisateur 2 : copeaux et broyat mêlés, bruns, comme le BRF en place. WoodChips002 écarté : texture 2:1 (1024 x 512 en 1K, incompatible avec le contrôle carré de telecharger_cc0.py) et copeaux de pin frais trop clairs. Teinte : brun foncé humide d'octobre ; gain_ab 0,6 pour désaturer l'orangé de la source."),
    acg("brf_bois_gris", "WoodChips001",
        "BRF / plaquettes de bois vieillies, grisées (gris argent après environ 1 an)",
        3, ["ilot/remplissage brf_bois_concasse (variante vieillie)", "massifs paillés anciens"],
        1.8, "estimé d'après la taille des copeaux (3-5 cm, comme WoodChips002 à 1,80 m) ; API sans dimension",
        None, None, [], [alt("acg", "WoodChips003", lab_lin([0.16, 0.15, 0.13])[0])],
        "Variante vieillie du BRF, couleur propre de la texture (pas de cible mesurée) ; à mélanger avec brf_bois_concasse par masque de bruit pour les îlots plantés avant 2025."),
    ph("gravier_concasse_6_10", "gravel_floor_02",
       "Gravier concassé anguleux 6/10-10/14 gris (îlots et pieds de mâts gravillonnés), 5-10 cm sur géotextile",
       2, ["ilot/remplissage gravier_concasse_6_10", "îlots gravillonnés du Vercors (constat coeur-31)", "pieds de mâts"],
       correction(S["gravel_floor_02"][0], C_GRAV["lab"], 1.0, 0.8), C_GRAV,
       ["photo utilisateur 3.png et 4.webp (aspect concassé anguleux ; hors site, non versionnées)",
        "data/raw/panoramax/paquet_jardin/tiles/2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd/2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg"],
       [alt("acg", "Gravel035", C_GRAV["lab"]), alt("acg", "Rocks006", C_GRAV["lab"]), alt("ph", "bicolour_gravel", C_GRAV["lab"]),
        alt("ph", "gravel_stones", C_GRAV["lab"])],
       "Gravel035 (gravillons_ilot) est un gravier roulé de rivière : arêtes arrondies, peu crédible de près pour un concassé. gravel_floor_02 montre des grains anguleux de 8-15 mm à 2,00 m, comme les photos utilisateur 3 et 4. Même cible que gravillons_ilot."),
    acg("calcaire_bordure", "Travertine009",
        "Pierre calcaire claire (bordures et pavés calcaire sciés), beige pâle à fins lits",
        3, ["bordures calcaire (materiau calcaire de bordures_elements.json)", "photo utilisateur 4"],
        1.2, "API (1.20 m)", correction(S["Travertine009"][0], C_CALC["lab"], 0.6, 0.6), C_CALC,
        ["photo utilisateur 4.webp (référence d'aspect, hors site ; non versionnée)"],
        [alt("acg", "Travertine001", C_CALC["lab"]), alt("acg", "Concrete034", C_CALC["lab"])],
        "Aucune bordure calcaire CC0 ; travertin clair (calcaire) scié, lits orientés le long de l'élément (U le long de la bordure). gain_L 0,6 atténue le veinage poli trop marqué. Usage : matériau 'calcaire' des éléments de bordure, pas de bordure calcaire relevée sur le site (a priori)."),
]

raw = open(MAN, "rb").read()
man = json.loads(raw.decode("utf-8"))
assert json.dumps(man, ensure_ascii=False, indent=1).replace("\n", "\r\n").encode("utf-8") == raw, "format du manifeste inattendu"
noms = {m["nom"] for m in man["materiaux"]}
for e in nouveaux:
    if e["nom"] in noms:
        sys.exit(f"déjà présent : {e['nom']}")
ref_acg = list(next(m for m in man["materiaux"] if m["nom"] == "gravillons_ilot").keys())
ref_ph = list(next(m for m in man["materiaux"] if m["nom"] == "paillage_mineral").keys())
for e in nouveaux:
    ref = ref_ph if e["source"] == "Poly Haven" else ref_acg
    assert list(e.keys()) == ref, (e["nom"], list(e.keys()), ref)
man["materiaux"].extend(nouveaux)
out = json.dumps(man, ensure_ascii=False, indent=1).replace("\n", "\r\n").encode("utf-8")
open(MAN, "wb").write(out)
print("manifeste :", len(man["materiaux"]), "matériaux ;", len(raw), "->", len(out), "octets")
for e in nouveaux:
    c = e["correction_teinte"]
    print(e["nom"], e["id"], e["tile_m"], (c or {}).get("lab_moyen_source"), "->", (c or {}).get("lab_cible"), "dE", (c or {}).get("delta_E_avant"))
