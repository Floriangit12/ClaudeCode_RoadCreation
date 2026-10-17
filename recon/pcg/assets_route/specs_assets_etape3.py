# -*- coding: utf-8 -*-
"""Table des assets de l'étape 3 de la bibliothèque « route_fr » : cotes sourcées, descriptions de pièces, phases.

Seule source de vérité des cotes de l'étape 3 (fabrication : recon/pcg/assets_route/fabriquer_assets_etape3.py).
Ce module ne fait AUCUNE géométrie 3D : il écrit des descriptions (profils 2D, listes de pièces cotées en texte, au
format de l'HDA route::assemblage) que les HDA route::* fabriquent à la cuisson (wrangles VEX).

Repère (USD, Z haut, m) — complète les conventions de l'étape 1 (catalogue « conventions ») :
- objets posés au sol (mobilier, balises, candélabres, mâts, abris) : pivot au pied, sol à Z = 0, face principale vers
  +Y (côté chaussée pour les feux et les panneaux, comme les optiques des feux de l'étape 1) ;
- dispositifs de retenue et bordures : X le long, face côté circulation vers −Y à Y = 0 (comme les bordures) ;
  modules linéaires centrés sur X (pivot au milieu de la longueur), longueur = pas de répétition ;
- affleurants (tampons, grilles, bouches à clé) : dessus au niveau Z = 0 (niveau fini), corps sous le sol ;
- panneaux : face vers +Y dans le plan Y = 0, pivot au milieu du bord inférieur de la plaque principale.

Chaque asset porte : sources (clé de SOURCES_E3 ou de specs_assets_route.SOURCES + page), confiance (haute / moyenne /
estimation), phase_chantier (ordre de construction, PHASES), regles (identifiants de assets/specs/route/
regles_route_fr.json qui contraignent la pose), pose (pas de répétition, accroches, hauteurs).
"""
import math

import specs_assets_route as SP

src = SP.src
D10 = "D:/DocRoute/10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources"
SRCE3 = "D:/ClaudeCode_RoadCreation/assets/lib/route_fr/_sources_etape3"

# ---------------------------------------------------------------------------------------------- phases de chantier
PHASES = [
    ("P01_reseaux", "terrassement, réseaux enterrés, regards et chambres (corps sous chaussée)"),
    ("P02_bordures", "bordures, caniveaux, éléments d'îlots et de giratoires préfabriqués (posés sur béton de calage)"),
    ("P03_chaussee", "couches de chaussée et couche de roulement (enrobés, matériaux de surface)"),
    ("P04_trottoirs", "revêtements des trottoirs, îlots, terre-pleins (béton, dalles, pavés, résine, galets, gravillons)"),
    ("P05_affleurants", "mise à niveau des affleurants : tampons, grilles, bouches à clé, avaloirs"),
    ("P06_retenue", "dispositifs de retenue : GBA/DBA/MVL coulés en place, glissières, extrémités, atténuateurs"),
    ("P07_eclairage", "candélabres et luminaires"),
    ("P08_signalisation", "supports, panneaux, panonceaux, potences, portiques, balises"),
    ("P09_feux", "mâts, têtes de feux, répétiteurs, boîtiers d'appel, armoires"),
    ("P10_marquage", "marquage au sol et plots rétroréfléchissants J15a (dossier 08)"),
    ("P11_mobilier", "potelets, barrières, arceaux, bancs, corbeilles, abris"),
]

# ---------------------------------------------------------------------------------------------- sources nouvelles
SOURCES_E3 = {
    "cerema_dr": dict(doc="Cerema, « Dispositifs de retenue en section courante – Guide d'installation »",
                      fichier=D10 + "/Cerema_Guide_Dispositifs_Retenue_Routiers.pdf",
                      statut="guide technique public (droits réservés : cotes citées seulement) ; reprend NF P98-426"),
    "setra_bvl": dict(doc="Setra, « Barrières de sécurité pour la retenue des véhicules légers » (niveau N, TPC), 2001",
                      fichier=D10 + "/SETRA_Barrieres_VL_Niveau_N_TPC_2001.pdf", statut="guide technique public"),
    "aximum_gs2": dict(doc="Aximum, fiche « Glissière métal simple file GS2 » (04/2022)",
                       url="https://aximum.com/sites/default/files/pdf-documentation/glissiere-metal-simple-file-gs2.pdf",
                       fichier=SRCE3 + "/retenue/glissiere-metal-simple-file-gs2.pdf", statut="fiche fabricant publique"),
    "aximum_gs4p": dict(doc="Aximum, fiche « GS4+ » (04/2022)",
                        url="https://www.aximum.com/sites/default/files/pdf-documentation/gs4-plus.pdf",
                        fichier=SRCE3 + "/retenue/gs4-plus.pdf", statut="fiche fabricant publique"),
    "aximum_de2": dict(doc="Aximum, fiche « DE2+R4 glissière métal double file »",
                       url="https://www.aximum.com/sites/default/files/pdf-documentation/glissiere-metal-double-file-de2-plus-r4.pdf.pdf",
                       fichier=SRCE3 + "/retenue/glissiere-metal-double-file-de2-plus-r4.pdf.pdf", statut="fiche fabricant publique"),
    "aximum_tau": dict(doc="Aximum, fiches « Tau Tube P50 », « Tau Tube 80 » et plaquette « Atténuateurs de choc » (2025)",
                       url="https://www.aximum.com/sites/default/files/pdf-documentation/attenuateur-choc-tau-tube-80.pdf",
                       fichier=SRCE3 + "/retenue/attenuateur-choc-tau-tube-80.pdf", statut="fiches fabricant publiques"),
    "pam": dict(doc="Saint-Gobain PAM (pamline.com) : regard PAMREX 600 D400 cadre rond (CDPA60EF, 20/10/2025), grille plate "
                    "à cadre C250 750 × 300 (ECML30ZF), bouche à clé TOTALE trottoir",
                url="https://www.pamline.com/fr-fr/", statut="fiches fabricant publiques ; cotes relevées dans les résultats de "
                                                         "recherche du 17/10/2026 (PDF non téléchargés) : confiance moyenne"),
    "angers_mob": dict(doc="Ville d'Angers, Cahier de prescriptions urbaines, fiches produit (banc lames de bois, corbeilles "
                           "béton et Vigipirate, abribus, abri tramway, arceau vélo, lanternes)",
                       url="https://cpu.angers.fr/product/<fiche>",
                       fichier=SRCE3 + "/mobilier/fiche-arceau.pdf", statut="document public de collectivité"),
    "gam_f16": dict(doc="Grenoble-Alpes Métropole, Guide métropolitain des espaces publics et de la voirie, fiche n° 16 "
                        "« Pour un meilleur partage de l'espace public : les nouveaux réflexes », p. 4",
                    fichier="D:/ClaudeCode_RoadCreation/data/raw/docs_web/grenoblealpesmetropole/",
                    statut="document public de collectivité (Meylan est dans le périmètre GAM)"),
    "paris_rvc": dict(doc="Ville de Paris, référentiel aménagements cyclables (1re partie), annexe 3 p. 66 : fiche fabricant "
                          "reproduite (balise PU Ø 80, borne Ø 200)", statut="cité par DocRoute 11 CYCLES.md § 10 (RF-MA-SEP-011)"),
    "odyssee": dict(doc="Odyssée Lumière Export, mâts d'éclairage aluminium 3-6 m (Ø base 120-140) et 9,3-12,8 m (Ø base "
                        "176, crosse cintrée 1,5-2,5 m, embout Ø 60, semelle 400 entraxe 300) — fiches Hellopro",
                    url="https://www.hellopro.fr/mat-d-eclairage-public-hauteur-9-3-12-8-m-en-aluminium-diametre-base-176-mm-2008383-5819902-produit.html",
                    statut="fiches fabricant publiques (pages web)"),
    "obs_isere": dict(doc="DocRoute 13, OBSERVATIONS_ISERE.md (Panoramax) : OBS-ECL-01 candélabres simple ou double crosse "
                          "8-11 m ; DBA de 2,6 m en voie rapide ; armoires de commande",
                      fichier="D:/DocRoute/13_Observations_Panoramax_Isere/OBSERVATIONS_ISERE.md", statut="observation"),
    "feux_doc": dict(doc="DocRoute 09, FEUX_IMPLANTATION.md § 7 et § 12 (hauteurs [G]/[M], tête R11v de Meylan)",
                     fichier="D:/DocRoute/09_Signalisation_Verticale_Feux/FEUX_IMPLANTATION.md", statut="synthèse sourcée"),
    "panneaux_cat": dict(doc="assets/specs/route/panneaux_fr_catalogue.json : 870 faces officielles (Cerema, PDF détourés) ; "
                             "gammes IISR 1re partie art. 5-3 p. 10 ; panonceaux art. 9-1 D p. 22 ; échelle des dessins 1:4,99",
                         fichier="D:/ClaudeCode_RoadCreation/assets/specs/route/panneaux_fr_catalogue.json", statut="catalogue du dépôt"),
    "iisr4": dict(doc="IISR 4e partie (prescription), art. 61 : hauteurs libres < 4,30 m à signaler",
                  fichier="D:/DocRoute/01_IISR_Signalisation_Officielle/IISR_4e_Partie_Prescription_20220613.pdf",
                  statut="texte réglementaire"),
    "estimation": dict(doc="estimation", statut="aucune source : valeur de pratique à vérifier"),
}
SOURCES_TOUTES = dict(SP.SOURCES, **SOURCES_E3)


# ---------------------------------------------------------------------------------------------- descriptions (texte)
def f(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") if abs(x) > 1e-12 else "0"


def B(c, s, mat, rz=0.0):
    return f"B {f(c[0])} {f(c[1])} {f(c[2])} {f(s[0])} {f(s[1])} {f(s[2])} {f(rz)} {mat}"


def T(pts, mat, nc=16, caps=1):
    """pts : [(x, y, z, r), ...] ; tube à rayon variable le long de la polyligne."""
    return f"T {len(pts)} {nc} {caps} {mat} " + " ".join(f"{f(x)} {f(y)} {f(z)} {f(r)}" for x, y, z, r in pts)


def CYL(p0, p1, r0, mat, r1=None, nc=16, caps=1):
    return T([(*p0, r0), (*p1, r0 if r1 is None else r1)], mat, nc, caps)


def Q(path, prof, mat, up=(0, 0, 1), caps=1):
    return (f"Q {len(path)} {len(prof)} {caps} {mat} {f(up[0])} {f(up[1])} {f(up[2])} "
            + " ".join(f"{f(x)} {f(y)} {f(z)}" for x, y, z in path) + " " + " ".join(f"{f(u)} {f(v)}" for u, v in prof))


def E(c, r, mat, ns=16):
    return f"E {f(c[0])} {f(c[1])} {f(c[2])} {f(r[0])} {f(r[1])} {f(r[2])} {ns} {mat}"


def FACE(c, n, up, w, h, mat):
    return f"F {f(c[0])} {f(c[1])} {f(c[2])} {f(n[0])} {f(n[1])} {f(n[2])} {f(up[0])} {f(up[1])} {f(up[2])} {f(w)} {f(h)} {mat}"


def DISQUE(c, n, r, mat, ns=32):
    return f"G {f(c[0])} {f(c[1])} {f(c[2])} {f(n[0])} {f(n[1])} {f(n[2])} {f(r)} {ns} {mat}"


def arc(c, R, a0, a1, n, plan="xz", rayon=None):
    """Points d'un arc (degrés) dans le plan donné ; rayon optionnel de section (tuples à 4 valeurs)."""
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        if plan == "xz":
            p = (c[0] + R * math.cos(a), c[1], c[2] + R * math.sin(a))
        elif plan == "yz":
            p = (c[0], c[1] + R * math.cos(a), c[2] + R * math.sin(a))
        else:
            p = (c[0] + R * math.cos(a), c[1] + R * math.sin(a), c[2])
        out.append(p if rayon is None else (*p, rayon))
    return out


def pieces(*morceaux):
    out = []
    for m in morceaux:
        if isinstance(m, (list, tuple)):
            out += [x for x in m if x]
        elif m:
            out.append(m)
    return ";\n".join(out)


# ---------------------------------------------------------------------------------------------- matériaux simples
MATERIAUX_SIMPLES_E3 = {
    "revers_panneau": dict(couleur_srgb=[0xA7, 0xAA, 0xA9], rugosite=0.45, metal=0.6,
                           note="revers et bord tombé des panneaux : aluminium brut / gris neutre (IISR 1 art. 10 : couleur "
                                "neutre, non rétroréfléchissante)"),
    "face_panneau": dict(couleur_srgb=[0xF0, 0xF0, 0xF0], rugosite=0.35, metal=0.0,
                         note="face de panneau sans image (remplacée par la face officielle dans chaque asset de panneau)"),
    "blanc_balise": dict(couleur_srgb=[0xEE, 0xEE, 0xEA], rugosite=0.45, metal=0.0, note="corps blanc des balises J1, J3, J11"),
    "vert_balise_J12": dict(couleur_srgb=[0x00, 0x6B, 0x3F], rugosite=0.45, metal=0.0, note="J12 : couleur verte (IISR 1 art. 9-2 J)"),
    "retro_blanc": dict(couleur_srgb=[0xF4, 0xF4, 0xF0], rugosite=0.2, metal=0.0,
                        note="bande rétroréfléchissante blanche classe 2 (vue de jour : blanc légèrement brillant)"),
    "retro_rouge": dict(couleur_srgb=[0xC4, 0x12, 0x1A], rugosite=0.2, metal=0.0, note="bande rétroréfléchissante rouge (J3)"),
    "retro_bleu": dict(couleur_srgb=[0x00, 0x4B, 0x9B], rugosite=0.25, metal=0.0, note="bandes bleues des balises J13"),
    "noir_mat": dict(couleur_srgb=[0x1C, 0x1C, 0x1C], rugosite=0.6, metal=0.0, note="noir mat (feux.json face_visiere_noir)"),
    "boitier_noir": dict(couleur_srgb=[0x20, 0x20, 0x20], rugosite=0.55, metal=0.0, note="feux.json boitier_noir"),
    "fourreau_jaune": dict(couleur_srgb=[0xF7, 0xB5, 0x00], rugosite=0.5, metal=0.0, note="feux.json fourreau_jaune (≈ RAL 1023)"),
    "gris_armoire": dict(couleur_srgb=[0x9C, 0xA1, 0x9C], rugosite=0.55, metal=0.0,
                         note="armoire de commande : polyester gris clair (≈ RAL 7032) — estimation"),
    "fonte_noire": dict(couleur_srgb=[0x2A, 0x2A, 0x28], rugosite=0.7, metal=0.3, note="fonte ductile revêtue noire (tampons, grilles)"),
    "cavite_noire": dict(couleur_srgb=[0x08, 0x08, 0x08], rugosite=0.9, metal=0.0, note="intérieur d'avaloir ou de regard (ombre)"),
    "verre_abri": dict(couleur_srgb=[0xC8, 0xD4, 0xD6], rugosite=0.05, metal=0.0, opacite=0.25,
                       note="verre trempé des abris (UsdPreviewSurface opacity 0,25)"),
    "plastique_gris_clair": dict(couleur_srgb=[0xD5, 0xD6, 0xD2], rugosite=0.5, metal=0.0, note="RAL 7035 (corps des modules R11v de Meylan, feux.json)"),
    "luminaire_verre": dict(couleur_srgb=[0xE8, 0xEC, 0xEE], rugosite=0.1, metal=0.0, emission_srgb=[0xFF, 0xF1, 0xD8],
                            note="vasque des luminaires LED (émission 3000 K allumée : customData)"),
    "jaune_attenuateur": dict(couleur_srgb=[0xF2, 0xC2, 0x00], rugosite=0.45, metal=0.0, note="jaune des nez d'atténuateurs (estimation)"),
    "chevrons_attenuateur": dict(couleur_srgb=[0xF2, 0xC2, 0x00], rugosite=0.35, metal=0.0,
                                 note="face avant à chevrons noir/jaune (couleur moyenne jaune ; motif à faire en décalque)"),
    "acier_corten": dict(couleur_srgb=[0x6E, 0x3E, 0x26], rugosite=0.8, metal=0.0, note="non utilisé (réserve)"),
    "affichage_abri": dict(couleur_srgb=[0xE6, 0xE8, 0xEA], rugosite=0.15, metal=0.0, emission_srgb=[0xF0, 0xF4, 0xFF],
                           note="caisson d'affichage rétroéclairé (émission allumée en customData)"),
}
SP.MATERIAUX_SIMPLES.update({k: v for k, v in MATERIAUX_SIMPLES_E3.items() if k not in SP.MATERIAUX_SIMPLES})


# ---------------------------------------------------------------------------------------------- assets
ASSETS = []


def ajouter(id_, famille, hda, params, dims, sources, confiance, materiau, phase, regles=(), pose=None, note=None, type_=None):
    ASSETS.append(dict(id=id_, famille=famille, type=type_ or id_.replace("_", " "), hda=hda, params=params, dimensions=dims,
                       sources=list(sources), confiance=confiance, materiau=materiau, phase_chantier=phase,
                       regles=list(regles), pose=pose or {}, note=note, etape=3))


def assemblage(id_, famille, desc, dims, sources, confiance, materiau, phase, regles=(), pose=None, note=None, type_=None, cusp=40.0):
    ajouter(id_, famille, "route::assemblage", dict(pieces=desc, materiau=materiau, cusp=cusp), dims, sources, confiance,
            materiau, phase, regles, pose, note, type_)


# ============================================================================================== 1. RETENUE
def _profil_GBA(double=False):
    t = math.tan(math.radians(36.0))
    u1 = 0.25 * t                                      # 0,1816 : pied du talon à la cassure
    if double:
        pts = [(0, 0), (0, 0.09), (u1, 0.34), (0.225, 0.81), (0.375, 0.81), (0.60 - u1, 0.34), (0.60, 0.09), (0.60, 0)]
        return SP.contour(pts, [(2, 0.25), (3, 0.01), (4, 0.01), (5, 0.25)])
    ub = 0.48 - 0.81 * math.tan(math.radians(6.0))     # arête arrière haute (dos incliné de 6°)
    pts = [(0, 0), (0, 0.09), (u1, 0.34), (ub - 0.15, 0.81), (ub, 0.81), (0.48, 0)]
    return SP.contour(pts, [(2, 0.25), (3, 0.01), (4, 0.01)])


PROF_E3 = {
    "GBA": dict(pts=_profil_GBA(), H=0.81, base=0.48,
                lecture="talon 9 cm vertical ; face à 36° de la verticale sur 25 cm (cassure en congé r = 25 cm) ; face haute "
                        "jusqu'à 72 cm au-dessus du talon ; sommet 15 cm ; base 48 cm ; dos incliné de 6°"),
    "DBA": dict(pts=_profil_GBA(True), H=0.81, base=0.60,
                lecture="profil symétrique : talons 9 cm, faces à 36° sur 25 cm (r = 25 cm), 72 cm au-dessus du talon, "
                        "sommet 15 cm, base 60 cm"),
    "MVL": dict(pts=SP.contour([(0, 0), (0.06, 0.60), (0.30, 0.60), (0.36, 0)], [(1, 0.01), (2, 0.01)]), H=0.60, base=0.36,
                lecture="muret trapézoïdal : hauteur hors sol 60 cm, base 36 cm, sommet 24 cm"),
    "LBA": dict(pts=SP.contour([(0, 0), (0, 0.15), (0.25 * math.tan(math.radians(36)), 0.40), (0.297, 1.50), (0.497, 1.50),
                                (0.85, 0)], [(2, 0.25), (3, 0.01), (4, 0.01)]), H=1.50, base=0.85,
                lecture="talon 15 cm ; 36° sur 25 cm (r = 25) ; 135 cm au-dessus du talon ; sommet 20 cm ; base 85 cm ; "
                        "pentes de la face haute (6°) et du dos déduites de la base et du sommet (non cotées)"),
}
S_DR16 = src("cerema_dr", 32, "Tableaux 15 et 16 (coupes types et dimensions, NF P98-426)",
             note="GBA 72 + talon 9, base 48, sommet 15 ; DBA base 60 ; LBA 135 + 15, base 85, sommet 20 ; MVL 60, base 36, "
                  "sommet 24 ; tolérances +2/−1 cm")
for nom, p in PROF_E3.items():
    for L in (1.0, 4.0):
        ajouter(f"retenue_{nom}_L{int(L * 100):03d}", "retenue", "route::extrusion_profil",
                dict(contour_a=SP.chaine(p["pts"]), mode=0, longueur=L, rayon=0.0, angle_deg=90.0, centrer=1, chanfrein=0.0),
                dict(base_m=p["base"], H_m=p["H"], longueur_m=L), [S_DR16, src("cerema_dr", 31, note="ouvrages coulés en place, "
                                                                                                  "fers filants")],
                "haute" if nom in ("GBA", "DBA", "MVL") else "moyenne", "beton_prefa_lisse", "P06_retenue",
                ["RF-GV-TPC-003", "RF-GV-TPC-004", "RF-GV-PON-009"],
                dict(pas_m=L, continu=True, face_circulation="−Y (Y = 0)", note="ouvrage coulé en place : modules jointifs sans "
                                                                                 "joint visible (joint de retrait tous les 4-6 m en texture)"),
                note=p["lecture"], type_=f"séparateur béton {nom} coulé en place – module de {L:g} m")
    if nom in ("GBA", "DBA"):
        bas = [(u, 0.0 if v < 1e-9 else round(min(v, 0.04) + 0.0001 * k, 5)) for k, (u, v) in enumerate(p["pts"])]
        for L, page, quand in ((1.65, 49, "fin de file (abaissement sur 1,65 m)"), (20.0, 51, "origine de file (abaissement sur 20 m)")):
            ajouter(f"retenue_{nom}_extremite_abaissee_L{int(round(L * 100)):04d}", "retenue", "route::extrusion_profil",
                    dict(contour_a=SP.chaine(p["pts"]), contour_b=SP.chaine(bas), mode=1, longueur=L, rayon=0.0, angle_deg=90.0,
                         centrer=0, sections=24 if L > 2 else 8, chanfrein=0.0),
                    dict(base_m=p["base"], H_debut_m=p["H"], H_fin_m=0.04, longueur_m=L),
                    [S_DR16, src("cerema_dr", page, "§ 4.1.2.2-4.1.2.3, fig. 30-31", note=quand)], "moyenne", "beton_prefa_lisse",
                    "P06_retenue", ["RF-GV-TPC-003"], dict(raccord="à la suite d'un module de même profil, X = 0 côté plein"),
                    note="rampant linéaire du profil plein vers un profil réduit à 4 cm (forme exacte non cotée)",
                    type_=f"extrémité de {nom} abaissée sur {L:g} m")

# --- glissières métalliques : lisse profil A, supports C100, écarteurs, boulons
def _lisse_A(ep=0.003, h=0.312, p=0.083, n=24):
    """Lisse profil A (2 ondes) : u = 0 sur les crêtes côté circulation, u = p au creux (fixation) ; v centré."""
    front, back = [], []
    for k in range(n + 1):
        v = -h / 2 + h * k / n
        u = p - p * abs(math.sin(math.pi * v / (h / 2)))
        front.append((round(u, 5), round(v, 5)))
    back = [(round(u + ep, 5), v) for u, v in front]
    return front + back[::-1]


LISSE_A = _lisse_A()
C100 = [(0, -0.025), (0.10, -0.025), (0.10, 0.025), (0.08, 0.025), (0.08, -0.020), (0.005, -0.020), (0.005, 0.025), (0, 0.025)]


def _glissiere(Lmod, ent, h_haut, double=False, entretoise=0.636, extremite=0.0):
    """Module de glissière : lisse(s) de Lmod (pas de 4 m ; éclisse de recouvrement de 0,315 m en bout), supports C100 tous
    les `ent` m derrière la lisse (+Y), écarteurs, boulons ; double = DE (deux files dos à dos, entretoise).
    extremite > 0 : extrémité abaissée et enterrée sur cette longueur (la lisse descend vers +X jusqu'à −0,20 m)."""
    zc = h_haut - 0.156
    out = []
    y2 = entretoise + 2 * 0.086
    files = [(0.0, 1)] if not double else [(0.0, 1), (y2, -1)]
    ys = 0.086 + 0.15 + 0.05 if not double else y2 / 2
    if extremite <= 0:
        for y0, s in files:
            prof = [(y0 + s * u, v) for u, v in LISSE_A]
            out.append(Q([(-Lmod / 2, 0, zc), (Lmod / 2, 0, zc)], prof, "acier_galvanise"))
            ecl = [(y0 + s * (u - 0.0035), v) for u, v in LISSE_A]           # éclisse (recouvrement de la lisse suivante)
            out.append(Q([(Lmod / 2 - 0.315, 0, zc), (Lmod / 2, 0, zc)], ecl, "acier_galvanise"))
        xs = [-Lmod / 2 + ent / 2 + k * ent for k in range(int(round(Lmod / ent)))]
        zx = {x: (h_haut, zc) for x in xs}
    else:
        L = extremite
        zf = -0.20
        chemin = [(L * k / 8, 0, zc + (zf - zc) * k / 8) for k in range(9)]
        out.append(Q(chemin, LISSE_A, "acier_galvanise"))
        xs = [ent / 2 + k * ent for k in range(int(L / ent))]
        zx = {x: (zc + (zf - zc) * x / L + 0.156, zc + (zf - zc) * x / L) for x in xs}
        xs = [x for x in xs if zx[x][0] - 0.08 > 0.15]                   # pas de support sous une lisse presque enterrée
    for x in xs:
        hz, ze = zx[x]
        out.append(Q([(x, ys, -0.30), (x, ys, hz - 0.08)], [(v, u - 0.05) for u, v in C100], "acier_galvanise", up=(1, 0, 0)))
        for y0, s in files:
            yb = y0 + s * 0.086
            ya, yb2 = sorted((yb, ys - s * 0.05))
            out.append(B((x, (ya + yb2) / 2, ze), (0.07, yb2 - ya, 0.20), "acier_galvanise"))
            out.append(CYL((x, y0 + s * 0.074, ze), (x, y0 + s * 0.086, ze), 0.012, "acier_galvanise", nc=8))
    return out


S_GS = src("setra_bvl", 30, "§ 3.3.4.3 a", note="GS4 : C 100 ou U 100 tous les 4 m ; GS2 : tous les 2 m ; lisse profil A ou B "
                                                 "(NF P 98-411) ; niveau N2")
S_H70 = src("setra_bvl", 73, "fig. 47", note="hauteur de l'élément de glissement 70 cm sans bordure (graphe H = f(D))")
S_LISSE = src("aximum_gs2", 2, note="lisse profil A 4,315 m (recouvrement 0,315 : pas de 4 m) ; support C100 de 1,50 m ; "
                                     "supports tous les 2 m ; hauteur de pose 700 mm (+0/−50)")
NOTE_LISSE = ("section de la lisse profil A : 312 × 83 × 3 mm ESTIMÉE (profil européen courant à 2 ondes ; profil B : "
              "296 × 2,5 mm d'après une fiche Hellopro) ; écarteurs 70 × 150 × 200 et C100 100 × 50 × 5 estimés")
for nom, ent, h, srcs in (("GS2", 2.0, 0.70, [S_GS, S_H70, S_LISSE]),
                          ("GS4", 4.0, 0.70, [S_GS, S_H70, S_LISSE, src("aximum_gs4p", 2, note="GS4+ : supports tous les 4 m, "
                                                                                                 "hauteur de pose 720 mm")])):
    assemblage(f"retenue_glissiere_{nom}_module_L400", "retenue", pieces(_glissiere(4.0, ent, h)),
               dict(longueur_m=4.0, hauteur_lisse_m=h, entraxe_supports_m=ent), srcs, "moyenne", "acier_galvanise", "P06_retenue",
               ["RF-GV-PON-010"], dict(pas_m=4.0, continu=True, face_circulation="−Y", hauteur_haut_lisse_m=h,
                                       supports="C100 tous les %g m (derrière la lisse, côté +Y)" % ent),
               note=NOTE_LISSE, type_=f"glissière métallique {nom} – module de 4 m (lisse + supports + écarteurs)")
    assemblage(f"retenue_glissiere_{nom}_extremite_abaissee_L1200", "retenue",
               pieces(_glissiere(4.0, ent, h, extremite=12.0)), dict(longueur_m=12.0, hauteur_depart_m=h),
               srcs + [src("aximum_gs2", 2, note="extrémités : éléments enterrés à hauteur constante ou abaissés sur 12 ml"),
                       src("cerema_dr", 49, "§ 4.1.1.2, photos 11-13", note="extrémités déportées, abaissées et enterrées")],
               "moyenne", "acier_galvanise", "P06_retenue", [], dict(raccord="X = 0 contre l'extrémité d'un module (lisse à pleine "
                                                                             "hauteur), la lisse descend vers +X"),
               note=NOTE_LISSE + " ; abaissement linéaire jusqu'à −5 cm (enterrée)",
               type_=f"glissière {nom} – extrémité abaissée et enterrée sur 12 m")
assemblage("retenue_glissiere_DE2_module_L400", "retenue", pieces(_glissiere(4.0, 2.0, 0.80, double=True)),
           dict(longueur_m=4.0, hauteur_lisse_m=0.80, entretoise_m=0.636),
           [S_GS, src("aximum_de2", 2, note="deux files de lisses profil A 4,315 ml liées par entretoises de 0,636 ml, supports "
                                            "C100 de 1,50 m tous les 2 m, hauteur de pose 800 mm (± 25)")],
           "moyenne", "acier_galvanise", "P06_retenue", ["RF-GV-TPC-003"],
           dict(pas_m=4.0, continu=True, largeur_m=0.636 + 2 * 0.089, implantation="axe du TPC"),
           note=NOTE_LISSE, type_="glissière double DE2 (terre-plein central) – module de 4 m")

# --- atténuateurs de choc (musoirs)
def _attenuateur(L, l, H):
    out = []
    n = max(2, int(round(L / 0.95)))
    for k in range(n):                                         # cartouches tubulaires (absorbeurs)
        x = -L / 2 + 0.25 + (L - 0.5) * (k + 0.5) / n
        out.append(CYL((x, 0, 0.08), (x, 0, H - 0.12), min(0.30, l * 0.32), "plastique_noir_feux", nc=20))
    for s in (-1, 1):                                          # panneaux latéraux télescopiques (lisses en écailles)
        for k in range(n):
            x0 = -L / 2 + 0.25 + (L - 0.5) * k / n
            x1 = x0 + (L - 0.5) / n + 0.08
            out.append(Q([(x0, s * (l / 2 - 0.01 * k), 0.47), (x1, s * (l / 2 - 0.01 * k), 0.47)],
                         [(-s * u, v) for u, v in LISSE_A], "acier_galvanise"))
    out.append(B((-L / 2 + 0.1, 0, H / 2), (0.2, l, H), "chevrons_attenuateur"))       # nez (face avant à chevrons)
    out.append(B((L / 2 - 0.1, 0, H / 2), (0.2, l * 0.9, H * 0.9), "acier_galvanise"))  # butoir arrière
    out.append(B((0, 0, 0.03), (L, 0.3, 0.06), "acier_galvanise"))                      # rail d'ancrage
    return out


for nom, L, l, page, note in (("P50", 1.90, 0.85, "Tau Tube P50 : 1,90 × 0,85 × 0,82 m (50 km/h)", "voies ≤ 50 km/h"),
                              ("P80", 3.82, 0.85, "Tau Tube P80 : 3,82 × 0,85 × 0,82 m (80-90 km/h)", "voies ≤ 90 km/h"),
                              ("M80", 3.82, 1.50, "Tau Tube M80 : 3,82 × 1,50 × 0,82 m", "musoir large ≤ 1,50 m"),
                              ("P110", 4.82, 0.85, "gamme : 4,82 m pour 110 km/h, hauteur 0,82 m", "voies ≤ 110 km/h")):
    assemblage(f"retenue_attenuateur_{nom}", "retenue", pieces(_attenuateur(L, l, 0.82)), dict(longueur_m=L, largeur_m=l, hauteur_m=0.82),
               [src("aximum_tau", 2, note=page)], "moyenne", "acier_galvanise", "P06_retenue", [],
               dict(implantation="nez de musoir, axe X vers l'obstacle (nez à −X)", usage=note),
               note="forme générique (cartouches et panneaux latéraux télescopiques) aux dimensions hors tout de la fiche ; "
                    "décor de chevrons du nez en couleur moyenne", type_=f"atténuateur de choc redirectif {nom}")

# ============================================================================================== 2. BALISES
S_J = src("iisr1", 23, "art. 9-2", note="balises J1 à J16 (p. 23-30)")
assemblage("balise_J1", "balises", pieces(
    CYL((0, 0, -0.25), (0, 0, 0.80), 0.10, "blanc_balise", nc=24, caps=2),
    CYL((0, 0, 0.80), (0, 0, 1.00), 0.1005, "retro_blanc", nc=24, caps=0),
    CYL((0, 0, 1.00), (0, 0, 1.30), 0.10, "blanc_balise", nc=24, caps=3)),
    dict(diametre_m=0.20, hauteur_hors_sol_m=1.30, bande_m=[0.80, 1.00]),
    [src("iisr1", 23, "art. 9-2 B", note="J1 cylindrique Ø 200, 1300 hors sol, blanche, bande rétroréfléchissante blanche de "
                                         "200 placée à 300 de la tête")], "haute", "blanc_balise", "P08_signalisation",
    ["RF-SV-J1"], dict(implantation="extérieur des virages, limite de la zone de récupération ; intervalle ≥ 8 m"))
assemblage("balise_J3", "balises", pieces(
    CYL((0, 0, -0.25), (0, 0, 0.80), 0.10, "blanc_balise", nc=24, caps=2),
    CYL((0, 0, 0.80), (0, 0, 1.00), 0.1005, "retro_rouge", nc=24, caps=0),
    CYL((0, 0, 1.00), (0, 0, 1.30), 0.10, "blanc_balise", nc=24, caps=3)),
    dict(diametre_m=0.20, hauteur_hors_sol_m=1.30), [src("iisr1", 24, "art. 9-2 C", note="J3 : Ø 200, 1300, blanche, bande "
                                                                                       "rouge de 200 à 300 de la tête")],
    "haute", "blanc_balise", "P08_signalisation", [], dict(implantation="à chaque angle d'une intersection (hors agglomération)"))


def _J6():
    # section triangulaire (pointe vers la chaussée −Y), petite base verticale 1,00 m hors sol, largeur 0,15 ; sommet en biseau
    prof = [(-0.075, 0.0), (0.075, 0.0), (0.0, -0.07)]
    out = [Q([(0, 0, -0.2), (0, 0, 1.0)], [(u, v) for u, v in prof], "blanc_balise", up=(0, 1, 0))]
    out.append(B((0, -0.045, 0.80), (0.10, 0.004, 0.20), "noir_mat", rz=0))                  # bande noire (simplifiée)
    out.append(B((0, -0.048, 0.80), (0.08, 0.004, 0.12), "retro_blanc"))                     # catadioptre 80 × 120
    return out


assemblage("balise_J6", "balises", pieces(_J6()), dict(hauteur_hors_sol_m=1.0, largeur_m=0.15),
           [src("iisr1", 25, "art. 9-2 F", note="J6 trapézoïdale à section triangulaire, petite base 1000 hors sol, largeur 150 ; "
                                               "bande noire oblique à 30° de 200 ; rétroréflecteur 80 × 120")],
           "moyenne", "blanc_balise", "P08_signalisation", [], dict(implantation="des deux côtés de la chaussée, guidage continu"),
           note="bande noire modélisée horizontale (l'oblique à 30° est à faire en décalque)")
for nom, coul, h, larg in (("J11", "blanc_balise", 0.85, 0.20), ("J11", "blanc_balise", 0.70, 0.15), ("J11", "blanc_balise", 0.50, 0.15),
                           ("J12", "vert_balise_J12", 0.85, 0.20)):
    r = larg / 2
    b1 = h - 0.10 - 0.06
    assemblage(f"balise_{nom}_H{int(h * 100):03d}", "balises", pieces(
        CYL((0, 0, 0), (0, 0, 0.03), r * 1.6, "noir_mat", nc=24),                              # embase
        CYL((0, 0, 0.03), (0, 0, b1 - 0.10 - 0.06), r, coul, nc=20, caps=2),
        CYL((0, 0, b1 - 0.16), (0, 0, b1 - 0.06), r * 1.01, "retro_blanc", nc=20, caps=0),
        CYL((0, 0, b1 - 0.06), (0, 0, b1), r, coul, nc=20, caps=0),
        CYL((0, 0, b1), (0, 0, b1 + 0.10), r * 1.01, "retro_blanc", nc=20, caps=0),
        CYL((0, 0, b1 + 0.10), (0, 0, h), r, coul, nc=20, caps=3)),
        dict(hauteur_m=h, largeur_apparente_m=larg), [src("iisr1", 26 if nom == "J11" else 27, f"art. 9-2 {'I' if nom == 'J11' else 'J'}",
                                                          note=f"{nom} : hauteur 700-850 (500 en agglomération), largeur apparente "
                                                               "150-200, deux bandes blanches rétroréfléchissantes de 100 espacées de "
                                                               "50-100 dans les deux tiers supérieurs")],
        "haute", coul, "P10_marquage", [], dict(implantation="≈ 0,50 m au-delà de la ligne continue ; pas 3-5 m (pistes)"),
        note="profil fermé circulaire ; embase noire Ø estimé")
assemblage("balise_J13", "balises", pieces(
    Q([(0, 0, -0.1), (0, 0, 1.2)], [(-0.125, 0.0), (0.125, 0.0), (0.10, 0.06), (-0.10, 0.06)], "blanc_balise", up=(0, 1, 0)),
    [B((0, -0.003, 0.10 + 0.40 * k), (0.25, 0.004, 0.20), "retro_bleu") for k in range(3)]),
    dict(hauteur_hors_sol_m=1.2, largeur_m=0.25),
    [src("iisr1", 27, "art. 9-2 K", note="J13 trapézoïdale, 1200 hors sol, largeur 250 ; bandes obliques bleues et blanches à "
                                         "30° de 200")], "moyenne", "blanc_balise", "P08_signalisation", ["RF-SV-J13"],
    dict(implantation="obstacle à < 1 m de la surface revêtue"), note="bandes bleues modélisées horizontales (décalque oblique à faire)")
assemblage("balise_J15a_plot", "balises", pieces(
    B((0, 0, 0.009), (0.10, 0.10, 0.018), "blanc_balise"), B((0, -0.051, 0.009), (0.06, 0.003, 0.012), "retro_blanc")),
    dict(hauteur_m=0.018, emprise_m=[0.10, 0.10]),
    [src("iisr1", 29, "art. 9-2 N", note="J15a : hauteur ≤ 20 mm, surface au sol ≤ 150 cm², rétroréflecteurs blancs")],
    "moyenne", "blanc_balise", "P10_marquage", [], dict(implantation="coaxial au marquage", pas_m="variable"),
    note="corps 100 × 100 × 18 mm (100 cm² ≤ 150) estimé")
assemblage("balise_quille_PU_D80_H100", "balises", pieces(
    CYL((0, 0, 0), (0, 0, 0.02), 0.10, "noir_mat", nc=24), CYL((0, 0, 0.02), (0, 0, 0.80), 0.04, "blanc_balise", nc=16, caps=2),
    CYL((0, 0, 0.80), (0, 0, 0.90), 0.0405, "retro_blanc", nc=16, caps=0), CYL((0, 0, 0.90), (0, 0, 1.0), 0.04, "blanc_balise", nc=16, caps=3)),
    dict(diametre_m=0.08, hauteur_m=1.0, embase_m=0.20),
    [src("paris_rvc", 66, "annexe 3", note="balise polyuréthane Ø 80, hauteur 750 ou 1000, embase Ø 200, film blanc")],
    "moyenne", "blanc_balise", "P11_mobilier", ["RF-MA-SEP-011"], dict(pas_m=[3, 5], implantation="séparateur de piste tactique"))
assemblage("balise_borne_PU_D200_H66", "balises", pieces(
    CYL((0, 0, 0), (0, 0, 0.60), 0.10, "blanc_balise", nc=24, caps=2), E((0, 0, 0.60), (0.10, 0.10, 0.06), "blanc_balise", 24),
    CYL((0, 0, 0.45), (0, 0, 0.52), 0.1005, "retro_blanc", nc=24, caps=0)),
    dict(diametre_m=0.20, hauteur_m=0.66), [src("paris_rvc", 66, "annexe 3", note="borne Ø 200, hauteur 660")], "moyenne",
    "blanc_balise", "P11_mobilier", ["RF-MA-SEP-011"])

# ============================================================================================== 3. ASSAINISSEMENT
def _cadre_rect(L, l, ep, h, mat, z0=0.0, yc=0.0):
    return [B((0, yc + (l - ep) / 2, z0 - h / 2), (L, ep, h), mat), B((0, yc - (l - ep) / 2, z0 - h / 2), (L, ep, h), mat),
            B(((L - ep) / 2, yc, z0 - h / 2), (ep, l - 2 * ep, h), mat), B((-(L - ep) / 2, yc, z0 - h / 2), (ep, l - 2 * ep, h), mat)]


def _grille(L, l, h, nb, mat="fonte_noire"):
    out = _cadre_rect(L, l, 0.013, h, mat)
    o = [B((0, 0, -h - 0.15), (L - 0.03, l - 0.03, 0.30), "cavite_noire")]
    pas = (L - 0.04) / nb
    for k in range(nb):                                      # barreaux transversaux (fentes perpendiculaires au fil d'eau)
        x = -L / 2 + 0.02 + pas * (k + 0.5)
        o.append(B((x, 0, -0.012), (pas * 0.55, l - 0.026, 0.024), mat))
    o.append(B((0, 0, -0.012), (L - 0.03, 0.03, 0.024), mat))   # longeron central
    return out + o


assemblage("assainissement_grille_plate_750x300_C250", "assainissement",
           pieces(_grille(0.776, 0.345, 0.041, 14)),
           dict(cadre_m=[0.776, 0.345], ouverture_m=[0.75, 0.30], hauteur_m=0.041),
           [src("pam", note="grille plate à cadre C250 750 × 300 (ECML30ZF) : cadre 776 × 345, ouverture 750 × 300, H 41, "
                            "absorption 746 × 241 (7,5 dm²)")], "moyenne", "fonte_noire", "P05_affleurants",
           [], dict(implantation="dans le caniveau, grand côté le long du fil d'eau", dessus="Z = 0"),
           note="cadre, barreaux et fentes modélisés (le décalque decal_grille_avaloir du site, photo d'une autre grille, a été "
                "retiré après la 1re planche : il doublait les barreaux)")


def _regard_rond(Dext, Dt, h, mat="fonte_noire"):
    return [CYL((0, 0, -h), (0, 0, 0), Dext / 2, mat, nc=48), CYL((0, 0, -0.9), (0, 0, -h), Dt / 2 - 0.02, "cavite_noire", nc=32, caps=2),
            DISQUE((0, 0, 0.0005), (0, 0, 1), Dt / 2, "decal_tampon_fonte", 48)]


assemblage("assainissement_regard_D600_cadre_rond_850", "assainissement", pieces(_regard_rond(0.85, 0.673, 0.10)),
           dict(cadre_diametre_m=0.85, tampon_diametre_m=0.673, passage_m=0.61, hauteur_m=0.10),
           [src("pam", note="PAMREX 600 D400 cadre rond (CDPA60EF) : cadre Ø ext 850, passage 610, hauteur 100, tampon 53 kg ; "
                            "tampon ≈ Ø 673")], "moyenne", "fonte_noire", "P05_affleurants", [],
           dict(dessus="Z = 0 (niveau fini)", corps="cheminée sous le sol jusqu'à −0,9 m"),
           note="dessus du tampon : décalque decal_tampon_fonte (site) à UV 0-1")
assemblage("assainissement_regard_D600_cadre_carre_840", "assainissement", pieces(
    B((0, 0, -0.05), (0.84, 0.84, 0.10), "fonte_noire"), DISQUE((0, 0, 0.0005), (0, 0, 1), 0.3365, "decal_tampon_fonte", 48)),
    dict(cadre_m=[0.84, 0.84], hauteur_m=0.10), [src("pam", note="PAMREX 600 cadre carré 840 × 840")], "moyenne", "fonte_noire",
    "P05_affleurants", [], dict(dessus="Z = 0"))
assemblage("assainissement_bouche_a_cle_trottoir", "assainissement", pieces(
    CYL((0, 0, -0.16), (0, 0, 0), 0.075, "fonte_noire", nc=24), DISQUE((0, 0, 0.0005), (0, 0, 1), 0.06, "fonte_noire", 24),
    CYL((0, 0, -0.6), (0, 0, -0.16), 0.051, "fonte_noire", nc=16)),
    dict(tete_diametre_m=0.15, hauteur_m=0.16, tube_diametre_m=0.102),
    [src("pam", note="bouche à clé TOTALE trottoir : 150 (tête), H 160, DI 102")], "moyenne", "fonte_noire", "P05_affleurants",
    [], dict(dessus="Z = 0"))


def _avaloir_T2():
    p = SP.PROFILS["T2"]["pts"]
    vue = 0.14
    dz = -(0.25 - vue)
    prof = [(u, v + dz) for u, v in p]
    linteau = [(0.0, 0.165 + dz)] + [(u, v) for u, v in prof if v >= 0.165 + dz] + [(0.15, 0.165 + dz)]
    out = []
    for x0, x1 in ((-0.497, -0.345), (0.345, 0.497)):
        out.append(Q([(x0, 0, 0), (x1, 0, 0)], prof, "beton_bordure"))
    out.append(Q([(-0.345, 0, 0), (0.345, 0, 0)], linteau, "beton_bordure"))
    out.append(B((0, 0.075, dz + 0.0825), (0.69, 0.15, 0.165), "cavite_noire"))              # gueule
    out.append(B((0, 0.45, -0.385), (0.66, 0.46, 0.67), "cavite_noire"))                     # chambre (bouche d'égout)
    out += _cadre_rect(0.80, 0.60, 0.04, 0.08, "fonte_noire", yc=0.45)
    out.append(B((0, 0.45, -0.01), (0.72, 0.52, 0.02), "fonte_noire"))                       # plaque de couverture
    out.append(FACE((0, 0.45, 0.0006), (0, 0, 1), (0, 1, 0), 0.72, 0.52, "decal_tampon_fonte_carre"))
    return out


assemblage("assainissement_avaloir_T2_bouche_egout", "assainissement", pieces(_avaloir_T2()),
           dict(longueur_m=1.0, ouverture_m=[0.69, 0.165], plaque_m=[0.80, 0.60]),
           [src("alkern2026", 11, "T2 Avaloir (réf. 520159)", note="1000 × 150 × 250 ; ouverture 690 de large, 165 de haut, "
                                                                 "retours de 135"),
            src("estimation", note="chambre 0,70 × 0,50 × 0,70 et plaque fonte 0,80 × 0,60 en arrière (trottoir)")],
           "moyenne", "beton_bordure", "P02_bordures", ["RF-MA-BUS-016"],
           dict(pas_m=1.0, pose="à la place d'une bordure T2 de 1 m, vue 14 cm", face_circulation="−Y"),
           note="bordure T2 à gueule de 690 × 165 (arc du dessin approché par un linteau droit) ; bouche d'égout derrière")

# ============================================================================================== 4. ÉCLAIRAGE
def _candelabre(H, d_pied, d_tete, saillie, crosse_double=False, luminaire=(0.70, 0.30, 0.10), inclinaison=10.0):
    out = [B((0, 0, -0.01), (0.40, 0.40, 0.02), "acier_galvanise"),                          # semelle 400
           CYL((0, 0, -0.01), (0, 0, H - 0.5), d_pied / 2, "acier_galvanise", r1=d_tete / 2, nc=24),
           B((0, -d_pied / 2 + 0.005, 0.60), (0.09, 0.012, 0.40), "acier_galvanise")]        # porte de visite
    for s in ((1,) if not crosse_double else (1, -1)):
        R = 0.8
        pts = [(0, 0, H - 0.5, d_tete / 2)]
        for k in range(1, 9):                                 # crosse cintrée (quart de cercle de rayon 0,8 m) puis droite
            a = math.radians(90 * k / 8)
            pts.append((0, s * R * (1 - math.cos(a)), H - 0.5 + R * math.sin(a), 0.03))
        y_fin = s * max(saillie, R + 0.1)
        pts.append((0, y_fin, H - 0.5 + R + (abs(y_fin) - R) * math.tan(math.radians(inclinaison)), 0.03))
        out.append(T(pts, "acier_galvanise", nc=12))
        lx, ly, lz = luminaire
        yc = y_fin + s * (lx / 2 - 0.05)
        zc = pts[-1][2] + 0.01
        out.append(B((0, yc, zc), (ly, lx, lz), "acier_thermolaque_7016"))
        out.append(B((0, yc, zc - lz / 2 - 0.002), (ly * 0.85, lx * 0.6, 0.004), "luminaire_verre", rz=0))
    return out


for H, dp, dt, sa, dbl in ((8.0, 0.160, 0.076, 1.5, False), (10.0, 0.176, 0.076, 1.5, False), (10.0, 0.176, 0.076, 1.5, True),
                           (12.0, 0.190, 0.089, 2.0, False)):
    nom = f"candelabre_routier_H{int(H * 10):03d}_{'double' if dbl else 'simple'}_crosse"
    assemblage(nom, "eclairage", pieces(_candelabre(H, dp, dt, sa, dbl)),
               dict(hauteur_feu_m=H, diametre_pied_m=dp, diametre_tete_m=dt, saillie_crosse_m=sa),
               [src("odyssee", note="9,3-12,8 m : Ø base 176, crosse cintrée 1,5-2,5 m, embout Ø 60 ; semelle 400"),
                src("obs_isere", note="OBS-ECL-01 : candélabres simple ou double crosse 8 à 11 m (M01, M23, G07, G12)"),
                src("estimation", note="luminaire LED 0,70 × 0,30 × 0,10 ; Ø en pied du 8 m et du 12 m interpolés")],
               "moyenne" if H == 10.0 else "estimation", "acier_galvanise", "P07_eclairage", ["RF-OBS-ECL-01"],
               dict(implantation="bande technique ou terre-plein, crosse vers la chaussée (+Y)", interdistance_m="3 à 4 × H (pratique)"),
               type_=f"candélabre routier {H:g} m {'à double crosse' if dbl else 'à simple crosse'}")


def _candelabre_urbain(H, d_pied, d_tete, top=True):
    out = [B((0, 0, -0.01), (0.30, 0.30, 0.02), "acier_thermolaque_7016"),
           CYL((0, 0, -0.01), (0, 0, H - 0.35), d_pied / 2, "acier_thermolaque_7016", r1=d_tete / 2, nc=24),
           B((0, -d_pied / 2 + 0.004, 0.50), (0.08, 0.01, 0.30), "acier_thermolaque_7016")]
    if top:                                                    # lanterne « top » : chapeau + vasque
        out += [CYL((0, 0, H - 0.35), (0, 0, H - 0.20), 0.05, "acier_thermolaque_7016", r1=0.20, nc=32),
                CYL((0, 0, H - 0.20), (0, 0, H - 0.12), 0.24, "acier_thermolaque_7016", nc=32),
                CYL((0, 0, H - 0.12), (0, 0, H), 0.24, "acier_thermolaque_7016", r1=0.06, nc=32),
                CYL((0, 0, H - 0.204), (0, 0, H - 0.200), 0.22, "luminaire_verre", nc=32)]
    else:                                                      # crosse courte + lanterne
        pts = [(0, 0, H - 0.35, d_tete / 2)] + [(0, 0.5 * (1 - math.cos(math.radians(90 * k / 6))), H - 0.35 + 0.5 * math.sin(math.radians(90 * k / 6)), 0.03)
                                                 for k in range(1, 7)] + [(0, 0.9, H + 0.2, 0.03)]
        out.append(T(pts, "acier_thermolaque_7016", nc=12))
        out += [B((0, 1.05, H + 0.17), (0.28, 0.45, 0.09), "acier_thermolaque_7016"),
                B((0, 1.05, H + 0.122), (0.22, 0.35, 0.004), "luminaire_verre")]
    return out


for H, dp, dt, top in ((4.0, 0.120, 0.060, True), (5.0, 0.130, 0.076, True), (6.0, 0.140, 0.076, False), (8.0, 0.160, 0.076, False)):
    nom = f"candelabre_urbain_H{int(H * 10):03d}_{'top' if top else 'crosse'}"
    assemblage(nom, "eclairage", pieces(_candelabre_urbain(H, dp, dt, top)), dict(hauteur_m=H, diametre_pied_m=dp),
               [src("odyssee", note="mâts 3-6 m : Ø base 120-140"),
                src("angers_mob", note="lanternes LED en fonte d'aluminium « top » ou sur crosse, mâts de 4 à 8 m, RAL 7016"),
                src("estimation", note="lanterne Ø 0,48 m ou 0,45 × 0,28 m ; crosse courte 0,9 m")],
               "estimation", "acier_thermolaque_7016", "P07_eclairage", [],
               dict(implantation="bande technique du trottoir, hors cheminement de 1,40 m"),
               type_=f"candélabre urbain {H:g} m ({'lanterne top' if top else 'crosse et lanterne'})")

# ============================================================================================== 5. MOBILIER
S_GAM = src("gam_f16", 4)
for H in (1.20, 1.40):
    ajouter(f"potelet_GAM_acier_D89_H{int(H * 100)}", "potelets", "route::revolution",
            dict(profil=SP.chaine([(0.0, -0.30), (0.04445, -0.30), (0.04445, H - 0.12), (0.04445, H - 0.02), (0.04445, H - 0.01),
                                   (0.040, H), (0.0, H)]),
                 bandes=f"{H - 0.12:.3f} {H - 0.02:.3f} blanc_ral9010", divisions=24, materiau="acier_thermolaque_7024"),
            dict(diametre_m=0.0889, hauteur_hors_sol_m=H),
            [dict(S_GAM, note="potelet acier monobloc Ø 88,9, RAL 7024, hauteur 1200 ou 1400, marquage en peinture blanche non "
                              "réfléchissante"), src("arrete2007", note="contraste ≥ 10 cm")],
            "haute", "acier_thermolaque_7024", "P11_mobilier", ["RF-MA-SEP-014", "RF-MA-OBS-002", "RF-MA-OBS-006"],
            dict(ecartement_m=[1.40, 1.60], note="Ø 0,089 : h ≥ 0,83 m (abaque 2012)"),
            note="bande blanche de 10 cm en partie haute (position exacte non cotée)")
ajouter("potelet_GAM_memoire_forme_D90_H90", "potelets", "route::revolution",
        dict(profil=SP.chaine([(0.0, -0.20), (0.045, -0.20), (0.045, 0.75), (0.045, 0.85), (0.045, 0.89), (0.040, 0.90), (0.0, 0.90)]),
             bandes="0.75 0.85 retro_blanc", divisions=24, materiau="acier_thermolaque_7024"),
        dict(diametre_m=0.09, hauteur_hors_sol_m=0.90), [dict(S_GAM, note="potelet à mémoire de forme Ø 90, RAL 7024, 900 hors sol")],
        "haute", "acier_thermolaque_7024", "P11_mobilier", ["RF-MA-SEP-014"], note="bande blanche haute estimée")
assemblage("borne_bois_GAM_150x150_H130", "potelets", pieces(
    Q([(0, 0, -0.30), (0, 0, 1.30)], SP.contour([(-0.075, -0.075), (0.075, -0.075), (0.075, 0.075), (-0.075, 0.075)]),
      "bois_brut_grise", up=(0, 1, 0)), E((0, 0, 1.30), (0.075, 0.075, 0.02), "bois_brut_grise", 16)),
    dict(section_m=[0.15, 0.15], hauteur_m=1.30), [dict(S_GAM, note="borne bois de mélèze, section 150 × 150 chanfreinée, 1300")],
    "haute", "bois_brut_grise", "P11_mobilier", ["RF-MA-SEP-014"], note="chanfreins non modélisés (arêtes vives)")
for L in (0.8, 1.2, 1.5):
    ajouter(f"barriere_GAM_croix_st_andre_L{int(L * 100):03d}", "barrieres", "route::ossature",
            dict(modele=2, longueur=L, hauteur=1.2, entraxe_montants=L, entraxe_barreaux=0.0, lisse_basse=0.10,
                 materiau="acier_thermolaque_7024"),
            dict(longueur_m=L, hauteur_m=1.2), [dict(S_GAM, note="barrières à croix de Saint-André RAL 7024, hauteur 1200, "
                                                                 "longueurs 0,8 / 1,2 / 1,5 ml")],
            "haute", "acier_thermolaque_7024", "P11_mobilier", ["RF-MA-SEP-014"], note="sections des tubes reprises de l'étape 1")


def _arceau_U(l=0.60, h=0.90, d=0.0483, emb=0.25, platines=False):
    r = 0.15
    pts = [(-l / 2, 0, -emb if not platines else 0.0, d / 2), (-l / 2, 0, h - r, d / 2)]
    pts += [(-(l / 2 - r) - r * math.cos(math.radians(a)), 0, h - r + r * math.sin(math.radians(a)), d / 2) for a in range(15, 90, 15)]
    pts += [(0.0, 0, h, d / 2)]
    pts += [((l / 2 - r) + r * math.cos(math.radians(a)), 0, h - r + r * math.sin(math.radians(a)), d / 2) for a in range(75, 0, -15)]
    pts += [(l / 2, 0, h - r, d / 2), (l / 2, 0, -emb if not platines else 0.0, d / 2)]
    out = [T(pts, "acier_thermolaque_7024", nc=16)]
    if platines:
        out += [B((s * l / 2, 0, 0.004), (0.12, 0.12, 0.008), "acier_thermolaque_7024") for s in (-1, 1)]
    return out


assemblage("arceau_velo_GAM_a_sceller", "mobilier", pieces(_arceau_U()), dict(largeur_m=0.60, longueur_tube_m=1.15, hauteur_hors_sol_m=0.90),
           [dict(S_GAM, note="arceau à sceller en U renversé : largeur 600, longueur 1150"),
            src("estimation", note="tube Ø 48,3 ; 0,25 m scellés (1150 − 900)")], "moyenne", "acier_thermolaque_7024",
           "P11_mobilier", ["RF-MA-SVE-004", "RF-MA-SVE-001"], dict(pas_m=1.0, distance_bordure_m=0.5, nb_min=4))
assemblage("arceau_velo_GAM_a_cheviller", "mobilier", pieces(_arceau_U(platines=True)), dict(largeur_m=0.60, hauteur_m=0.90),
           [dict(S_GAM, note="arceau à cheviller en U renversé : largeur 600, longueur 900"),
            src("estimation", note="platines 120 × 120 × 8")], "moyenne", "acier_thermolaque_7024", "P11_mobilier",
           ["RF-MA-SVE-004"], dict(pas_m=1.0, distance_bordure_m=0.5))


def _arceau_angers():
    out = [CYL((0, 0, -0.30), (0, 0, 1.20), 0.03, "acier_thermolaque_7016", nc=16)]
    a, b, zc = 0.23, 0.425, 0.775                              # demi-largeur 460/2, demi-hauteur (1200 − 350)/2, centre
    for s in (-1, 1):
        pts = [(s * a * math.sin(math.radians(t)), 0, zc + b * math.cos(math.radians(t)), 0.015) for t in range(0, 181, 12)]
        out.append(T(pts, "acier_thermolaque_7016", nc=10))
    out.append(CYL((-a, 0, zc), (a, 0, zc), 0.015, "acier_thermolaque_7016", nc=10))
    out.append(B((0, 0, zc), (0.14, 0.07, 0.07), "acier_thermolaque_7016"))
    return out


assemblage("arceau_velo_angers", "mobilier", pieces(_arceau_angers()), dict(hauteur_m=1.20, largeur_m=0.46),
           [src("angers_mob", note="fiche arceau vélo type Ville d'Angers : poteau Ø 60, H 1200, arceaux Ø 30 sur 460 de large, "
                                   "à partir de 350 du sol ; RAL 7016")], "haute", "acier_thermolaque_7016", "P11_mobilier",
           ["RF-MA-SVE-001"], dict(pas_m=0.75))


def _banc(L=1.80, dossier=True):
    out = []
    n_lames = 4
    for k in range(n_lames):                                  # assise : lames 100 × 27
        y = -0.21 + 0.05 + k * 0.107
        out.append(B((0, y, 0.50 - 0.0135), (L, 0.10, 0.027), "bois_brut_grise"))
    if dossier:
        for k in range(3):
            z = 0.62 + k * 0.13
            out.append(B((0, 0.23 + 0.03 * k, z), (L, 0.027, 0.10), "bois_brut_grise", rz=0))
    nb = max(2, int(math.floor(L / 2.0)) + 1)
    for k in range(nb):                                       # piétements / accoudoirs plats 80 × 8 tous les 2 m
        x = -L / 2 + 0.10 + (L - 0.20) * k / (nb - 1)
        out.append(Q([(x, -0.20, 0.0), (x, -0.20, 0.47), (x, 0.20, 0.47), (x, 0.22, 0.0)] if not dossier else
                     [(x, -0.20, 0.0), (x, -0.20, 0.47), (x, 0.22, 0.47), (x, 0.25, 1.02)],
                     [(-0.04, -0.004), (0.04, -0.004), (0.04, 0.004), (-0.04, 0.004)], "acier_thermolaque_7016", up=(1, 0, 0)))
        out.append(B((x, 0.22 if not dossier else 0.10, 0.12), (0.008, 0.08, 0.24), "acier_thermolaque_7016"))
    return out


for L, dos in ((1.80, True), (1.80, False), (2.40, True)):
    assemblage(f"banc_lames_bois_L{int(L * 100)}_{'dossier' if dos else 'sans_dossier'}", "mobilier", pieces(_banc(L, dos)),
               dict(longueur_m=L, profondeur_m=0.42, hauteur_assise_m=0.50 if dos else 0.49, hauteur_dossier_m=0.52 if dos else 0),
               [src("angers_mob", note="banc en lames de bois : profondeur 0,42, assise 0,50 (0,49 sans dossier), dossier 0,52, "
                                       "lames 100 × 27, accoudoirs plats 80 × 8 tous les 2 m, structure RAL 7016 ; longueur variable")],
               "haute", "bois_brut_grise", "P11_mobilier", [], dict(implantation="bande de mobilier, hors cheminement", interdistance_m="≤ 300 (GAM)"),
               note="longueur choisie (variable au catalogue) ; piétement simplifié")


def _corbeille_vigipirate():
    out = [CYL((0, 0, 0), (0, 0, 0.03), 0.235, "acier_thermolaque_7016", nc=32)]
    for k in range(28):                                       # 28 tiges cintrées Ø 10
        a = 360.0 * k / 28
        if 150 < a < 210:
            continue                                          # ouverture latérale
        x, y = 0.23 * math.cos(math.radians(a)), 0.23 * math.sin(math.radians(a))
        out.append(CYL((x, y, 0.03), (x, y, 0.78), 0.005, "acier_thermolaque_7016", nc=6, caps=0))
    out += [T([(0.235 * math.cos(math.radians(a)), 0.235 * math.sin(math.radians(a)), z, 0.008) for a in range(0, 361, 15)],
              "acier_thermolaque_7016", nc=8, caps=0) for z in (0.30, 0.78)]
    out.append(CYL((0, 0, 0.78), (0, 0, 0.828), 0.24, "acier_thermolaque_7016", r1=0.20, nc=32))
    out.append(CYL((0, 0, 0.10), (0, 0, 0.70), 0.21, "verre_abri", nc=24))   # sac transparent (vigipirate)
    return out


assemblage("corbeille_vigipirate_110L", "mobilier", pieces(_corbeille_vigipirate()), dict(diametre_m=0.47, hauteur_m=0.828),
           [src("angers_mob", note="corbeille Vigipirate : Ø 470, H 828, 28 tiges cintrées Ø 10, ouverture latérale 486, 110 L, RAL 7016")],
           "haute", "acier_thermolaque_7016", "P11_mobilier", [], dict(implantation="bande de mobilier, près des arrêts et traversées"),
           note="ouverture latérale de 60° ; sac représenté par un cylindre translucide")
assemblage("corbeille_beton_60L", "mobilier", pieces(
    B((0, 0, 0.36), (0.50, 0.50, 0.72), "beton_prefa_lisse"), B((0, 0, 0.735), (0.46, 0.46, 0.03), "inox_brosse"),
    B((0, -0.251, 0.40), (0.30, 0.004, 0.40), "acier_galvanise")),
    dict(dimensions_m=[0.50, 0.50, 0.75]), [src("angers_mob", note="corbeille béton 0,50 × 0,50 × 0,75, couvercle inox, porte latérale")],
    "haute", "beton_prefa_lisse", "P11_mobilier", [])


def _abri(L, P, H):
    out = []
    for x in (-L / 2 + 0.05, L / 2 - 0.05):                   # poteaux
        for y in (P / 2 - 0.05,):
            out.append(B((x, y, H / 2), (0.08, 0.08, H), "acier_thermolaque_7016"))
    out.append(B((0, P / 2 - 0.05, H / 2), (0.08, 0.08, H), "acier_thermolaque_7016"))
    out.append(B((0, 0, H - 0.05), (L + 0.10, P + 0.10, 0.10), "acier_thermolaque_7016"))  # toiture
    out.append(B((0, 0, H - 0.105), (L, P, 0.01), "verre_abri"))
    out.append(B((0, P / 2 - 0.05, 1.20), (L - 0.12, 0.012, 2.0), "verre_abri"))           # paroi arrière vitrée
    out.append(B((-L / 2 + 0.05, 0.10, 1.20), (0.012, P - 0.30, 2.0), "verre_abri"))        # joue latérale
    out.append(B((L / 2 - 0.40, 0.0, 1.10), (1.20, 0.15, 1.76), "acier_thermolaque_7016"))  # caisson d'affichage
    out.append(B((L / 2 - 0.40, -0.076, 1.10), (1.10, 0.004, 1.66), "affichage_abri"))
    out.append(B((-0.3, P / 2 - 0.25, 0.46), (1.6, 0.35, 0.04), "bois_brut_grise"))          # banc
    out += [B((x, P / 2 - 0.25, 0.22), (0.05, 0.30, 0.44), "acier_thermolaque_7016") for x in (-0.95, 0.35)]
    return out


assemblage("abri_bus_L411", "mobilier", pieces(_abri(4.11, 1.50, 2.38)), dict(longueur_m=4.11, profondeur_m=1.50, hauteur_m=2.38),
           [src("angers_mob", note="abribus modulaire : hauteur 2,38, largeur 4,11, RAL 7016, verre trempé, affichage"),
            src("estimation", note="profondeur 1,50 (exemple « albatros » 150 × 340, SMT p. 14 cité par RF-MA-BUS-012)")],
           "moyenne", "acier_thermolaque_7016", "P11_mobilier", ["RF-MA-BUS-012", "RF-MA-BUS-007"],
           dict(implantation="tête de quai, ≥ 0,90 m (1,40 m) entre le nez de bordure et l'abri ; face ouverte vers la chaussée (−Y)"))
assemblage("abri_bus_L340", "mobilier", pieces(_abri(3.40, 1.50, 2.38)), dict(longueur_m=3.40, profondeur_m=1.50, hauteur_m=2.38),
           [src("estimation", note="modèle 150 × 340 (« albatros », SMT p. 14, cité par RF-MA-BUS-012) ; hauteur reprise d'Angers")],
           "moyenne", "acier_thermolaque_7016", "P11_mobilier", ["RF-MA-BUS-012"])
assemblage("borne_fontaine_angers", "mobilier", pieces(
    B((0, 0, 0.005), (0.30, 0.30, 0.01), "fonte_noire"), CYL((0, 0, 0.01), (0, 0, 0.90), 0.11, "acier_thermolaque_7016", r1=0.09, nc=24),
    E((0, 0, 0.90), (0.10, 0.10, 0.09), "acier_thermolaque_7016", 20), CYL((0.09, 0, 0.75), (0.16, 0, 0.75), 0.02, "inox_brosse", nc=10),
    CYL((0, -0.10, 0.45), (0, -0.16, 0.40), 0.012, "inox_brosse", nc=10)),
    dict(hauteur_hors_sol_m=0.99), [src("angers_mob", note="borne fontaine fonte, H hors sol 0,99, RAL 7016, bouton latéral, platine")],
    "moyenne", "acier_thermolaque_7016", "P11_mobilier", [], note="forme générique (diamètres estimés)")

# ============================================================================================== 6. FEUX (site et compléments)
def _module_pot(zc, couleur, picto="", d=0.2, corps="plastique_gris_clair"):
    """Module « pot » de Meylan : corps gris Ø 0,32 profondeur 0,25 vers −Y (dos), face noire, visière tubulaire 0,22 vers +Y."""
    mat_l = f"feu_lentille_{couleur}" + (f"_{picto}" if picto else "")
    return [CYL((0, -0.25, zc), (0, 0.0, zc), 0.16, corps, nc=32),
            CYL((0, 0.0, zc), (0, 0.012, zc), 0.165, "noir_mat", nc=32),
            DISQUE((0, 0.0125, zc), (0, 1, 0), d / 2, mat_l, 32),
            T([(0, 0.012, zc, 0.135), (0, 0.23, zc, 0.15)], "noir_mat", nc=32, caps=0)]


def _tete_pots(couleurs, picto=""):
    out = []
    n = len(couleurs)
    for k, c in enumerate(couleurs):
        out += _module_pot(0.16 + 0.37 * (n - 1 - k), c, picto)
    out.append(B((0, -0.29, 0.37 * (n - 1) / 2 + 0.16), (0.06, 0.08, 0.37 * (n - 1) + 0.1), "acier_galvanise"))   # console
    return out


assemblage("feu_R11v_meylan_pots", "feux", pieces(_tete_pots(["rouge", "jaune", "vert"])),
           dict(hauteur_tete_m=1.1, pas_vertical_m=0.37, diametre_module_m=0.32, profondeur_avec_visiere_m=0.5, diametre_optique_m=0.2),
           [src("feux_json", note="3 modules cylindriques séparés gris clair Ø 300-330, profondeur 250, collerette et visière "
                                  "tubulaire noires 200-250 ; hauteur de tête 1,10, pas 0,37"),
            src("feux_doc", note="§ 12 : tête R11v de Meylan, 3 modules ronds gris clair, aucun écran de contraste")],
           "moyenne", "plastique_gris_clair", "P09_feux", ["RF-FEU.HAUTEUR.GENERATEUR", "RF-FEU.HAUTEUR.TROTTOIR"],
           dict(pivot="bas du module inférieur au centre de la face", hauteur_bas_m=2.3, optiques="+Y"),
           note="lentilles éteintes ; émission allumée dans customData (route:emission_allumee_lineaire)")
assemblage("feu_R13c_meylan_pots", "feux", pieces(_tete_pots(["rouge", "jaune", "vert"], "cycle")),
           dict(hauteur_tete_m=1.1, diametre_optique_m=0.2),
           [src("feux_json", note="R13c : même corps que feu_R11v (modules) ; pictogramme cycle"),
            src("iisr6", 6, figure="fig. 3")], "moyenne", "plastique_gris_clair", "P09_feux", ["RF-FEU.HAUTEUR.GENERATEUR"],
           note="pictogramme non dessiné (matériau de lentille nommé « _cycle »)")
assemblage("feu_R11j_meylan_pots", "feux", pieces(_tete_pots(["rouge", "jaune", "jaune"])), dict(hauteur_tete_m=1.1),
           [src("iisr6", 5, note="R11j : le vert est remplacé par un jaune clignotant (exceptionnel)"), src("feux_json")],
           "moyenne", "plastique_gris_clair", "P09_feux", [], note="module bas jaune clignotant")


def _repetiteur():
    out = [B((0, -0.075, 0.25), (0.15, 0.15, 0.50), "boitier_noir")]
    for k, c in enumerate(("rouge", "jaune", "vert")):
        z = 0.25 + (1 - k) * 0.15
        out += [DISQUE((0, 0.0005, z), (0, 1, 0), 0.045, f"feu_lentille_{c}", 24),
                T([(0, 0.0, z, 0.055), (0, 0.06, z, 0.058)], "boitier_noir", nc=20, caps=0)]
    return out


assemblage("feu_repetiteur_R11v_meylan", "feux", pieces(_repetiteur()), dict(largeur_m=0.15, hauteur_m=0.50, profondeur_m=0.15, optique_m=0.09),
           [src("feux_json", note="répétiteur : caisson monobloc noir 0,15 × 0,50 × 0,15 à 3 petites visières, centre ≈ 1,40 m"),
            src("iisr6", 35, note="répétiteurs généralement Ø 90 mm")], "moyenne", "boitier_noir", "P09_feux",
           ["RF-FEU.HAUTEUR.GENERATEUR"], dict(hauteur_centre_m=1.40, pivot="bas du caisson, face à Y = 0"))


def _r12_boitier():
    out = [B((0, -0.09, 0.15), (0.33, 0.18, 0.30), "boitier_noir")]
    # vu de face (observateur en +Y regardant −Y), sa gauche est en +X : rouge à gauche (+X), vert à droite (−X)
    for s, c, p in ((1, "pieton_rouge", "pieton_arret"), (-1, "pieton_vert", "pieton_marche")):
        x = s * 0.08
        out += [FACE((x, 0.0006, 0.15), (0, 1, 0), (0, 0, 1), 0.13, 0.20, f"feu_lentille_{c}_{p}"),
                B((x, 0.06, 0.26), (0.15, 0.12, 0.006), "boitier_noir")]
    return out


assemblage("feu_R12_meylan_boitier_horizontal", "feux", pieces(_r12_boitier()), dict(largeur_m=0.33, hauteur_m=0.30, profondeur_m=0.18, casquette_m=0.12),
           [src("feux_json", note="R12 boîtier bi-figurine horizontal 0,33 × 0,30 × 0,18, casquette 0,12 ; centre ≈ 2,10 m"),
            src("iisr6", 5, article="art. 109-3 A", note="rouge à gauche, vert à droite pour le piéton qui fait face")],
           "moyenne", "boitier_noir", "P09_feux", ["RF-FEU.HAUTEUR.GENERATEUR"], dict(hauteur_centre_m=2.10))
assemblage("feu_boitier_appel_pieton", "feux", pieces(
    B((0, -0.05, 0.08), (0.12, 0.10, 0.16), "boitier_noir"), CYL((0, 0.0, 0.06), (0, 0.012, 0.06), 0.025, "inox_brosse", nc=20),
    DISQUE((0, 0.0005, 0.125), (0, 1, 0), 0.012, "feu_lentille_rouge", 16), B((0, -0.11, 0.08), (0.06, 0.02, 0.10), "acier_galvanise")),
    dict(largeur_m=0.12, hauteur_m=0.16, profondeur_m=0.10),
    [src("feux_json", note="boîtier noir de demande piétons avec voyant d'attente rouge 0,12 × 0,16 × 0,10, collier sur le mât, "
                           "centre ≈ 1,0 m"), src("feux_doc", note="§ 9 : dispositifs tactiles ou sonores associés au R12 (NF S32-002)")],
    "moyenne", "boitier_noir", "P09_feux", ["RF-FEU.HAUTEUR.GENERATEUR"], dict(hauteur_centre_m=1.0))
assemblage("feu_armoire_commande", "feux", pieces(
    B((0, 0, 0.10), (0.85, 0.40, 0.20), "beton_prefa_lisse"), B((0, 0, 0.20 + 0.65), (0.80, 0.35, 1.30), "gris_armoire"),
    B((0, 0, 1.52), (0.84, 0.39, 0.04), "gris_armoire"), B((-0.2, -0.176, 0.85), (0.36, 0.004, 1.20), "gris_armoire"),
    B((0.2, -0.176, 0.85), (0.36, 0.004, 1.20), "gris_armoire")),
    dict(dimensions_m=[0.80, 0.35, 1.54]), [src("obs_isere", note="armoires de commande observées (G10)"),
                                             src("estimation", note="armoire polyester 0,80 × 0,35 × 1,30 sur socle béton 0,20")],
    "estimation", "gris_armoire", "P09_feux", [], dict(implantation="trottoir, hors cheminement, près d'un mât"))


def _ecran_contraste():
    out = [B((0, -0.02, 0.43), (0.56, 0.01, 0.98), "noir_mat")]
    return out


assemblage("feu_ecran_contraste_R11v_D200", "feux", pieces(_ecran_contraste()), dict(largeur_m=0.56, hauteur_m=0.98),
           [src("iisr6", 11, note="écran de contraste noir obligatoire hors agglomération (p. 11-12)"),
            src("estimation", note="écran 0,56 × 0,98 (boîtier 0,265 + 2 × 0,15 de bordure)")], "estimation", "noir_mat", "P09_feux",
           [], dict(pose="derrière la tête R11v D200 de l'étape 1, même pivot"))

assemblage("feu_bras_court_L033", "feux", pieces(
    CYL((0, 0, 0), (0, 0.33, 0), 0.03, "acier_galvanise", nc=16),
    CYL((0, 0, -0.04), (0, 0, 0.04), 0.062, "acier_galvanise", nc=24, caps=0), B((0, 0.31, 0), (0.08, 0.04, 0.12), "acier_galvanise")),
    dict(longueur_m=0.33, diametre_m=0.06),
    [src("feux_json", note="têtes montées latéralement par bras courts ≈ 0,15-0,25 m sur le mât"),
     src("estimation", note="tube Ø 60, collier Ø 124 sur mât Ø 114, platine de console 80 × 120")], "moyenne", "acier_galvanise",
    "P09_feux", [], dict(pivot="axe du mât à la hauteur du centre de la tête ; bras vers +Y (face de la tête)"))

# --- mâts de feux du site, colliers, potences
for H in (3.4, 4.2):
    ajouter(f"mat_feux_D114_H{int(H * 10):02d}", "supports", "route::poteau",
            dict(section="rond", d1=0.114, d2=0.114, hauteur=H, platine=0, serrage=0, bande_contrastee=0, bouchon=1,
                 materiau="acier_galvanise"),
            dict(hauteur_m=H, diametre_m=0.114),
            [src("feux_json", note="mât de feux rond acier Ø ≈ 100-114 (Ø 114 retenu), 3,4 m (4,2 m sur l'îlot axial), "
                                   "galvanisé clair, pied scellé, bouchon"),
             src("feux_doc", note="§ 12 [M] ; ARB-05")], "moyenne", "acier_galvanise", "P09_feux",
            ["RF-FEU.HAUTEUR.GENERATEUR"], dict(accroches="têtes sur bras courts 0,15-0,25 m ; plusieurs têtes par mât"),
            note="sans bande contrastée (non vue sur le site) ; variante à fourreau jaune : mat_feux_D114_H34_fourreau")
assemblage("mat_feux_D114_H34_fourreau", "supports", pieces(
    CYL((0, 0, -0.3), (0, 0, 3.4), 0.057, "acier_galvanise", nc=24), CYL((0, 0, 0.58), (0, 0, 0.93), 0.0595, "fourreau_jaune", nc=24, caps=0),
    CYL((0, 0, 3.4), (0, 0, 3.425), 0.063, "plastique_noir_feux", r1=0.058, nc=24)),
    dict(hauteur_m=3.4, diametre_m=0.114), [src("feux_json", note="manchon (fourreau) jaune ≈ 0,35 m entre ≈ 0,58 et 0,93 m")],
    "moyenne", "acier_galvanise", "P09_feux", ["RF-FEU.HAUTEUR.GENERATEUR"])


def _collier(dpole):
    r = dpole / 2
    return [CYL((0, 0, -0.02), (0, 0, 0.02), r + 0.004, "acier_galvanise", nc=24, caps=0),
            CYL((0, 0, -0.02), (0, 0, 0.02), r + 0.0001, "acier_galvanise", nc=24, caps=0),
            B((0, r + 0.015, 0), (0.05, 0.03, 0.04), "acier_galvanise"),
            CYL((0, r + 0.006, 0), (0, r + 0.045, 0), 0.006, "inox_brosse", nc=8),
            B((0, -(r + 0.010), 0), (0.03, 0.02, 0.03), "acier_galvanise")]


for dp in (0.0483, 0.0603, 0.076, 0.089, 0.114):
    assemblage(f"collier_panneau_D{int(round(dp * 1000)):03d}", "supports", pieces(_collier(dp)),
               dict(diametre_poteau_m=dp, hauteur_m=0.04, saillie_m=dp / 2 + 0.045),
               [src("iisr1", 15, article="art. 6 B 1°", note="diamètres des supports et mâts"),
                src("estimation", note="bride 40 mm de haut, patte 50 × 30, boulon M12 vers le rail du panneau (+Y)")],
               "estimation", "acier_galvanise", "P08_signalisation", [],
               dict(pose="axe du poteau en (0, 0) ; centre à la hauteur d'un rail du panneau ; patte vers la face (+Y)"))


def _potence_signalisation(portee, H_bas, Hpan=1.5, d_mat=0.219):
    zc = H_bas + Hpan / 2
    out = [B((0, 0, -0.01), (0.50, 0.50, 0.03), "acier_galvanise"),
           CYL((0, 0, 0), (0, 0, zc + Hpan / 2 + 0.3), d_mat / 2, "acier_galvanise", nc=24)]
    for dz in (-Hpan / 2 + 0.15, Hpan / 2 - 0.15):            # deux poutres horizontales (console)
        out.append(CYL((0, 0, zc + dz), (portee, 0, zc + dz), 0.057, "acier_galvanise", nc=16))
    for k in range(int(portee / 1.0)):                        # diagonales (treillis)
        x0, x1 = k * 1.0, min(portee, (k + 1) * 1.0)
        z0, z1 = (zc - Hpan / 2 + 0.15, zc + Hpan / 2 - 0.15) if k % 2 == 0 else (zc + Hpan / 2 - 0.15, zc - Hpan / 2 + 0.15)
        out.append(CYL((x0, 0, z0), (x1, 0, z1), 0.025, "acier_galvanise", nc=8))
    return out


assemblage("potence_signalisation_L600", "supports", pieces(_potence_signalisation(6.0, 5.0)),
           dict(portee_m=6.0, bas_panneau_m=5.0, hauteur_panneau_max_m=1.5, diametre_mat_m=0.219),
           [src("iisr1", 19, article="art. 9 c", note="au-dessus de la chaussée : gabarit + 0,10 (entretien) + 0,50 (protection)"),
            src("iisr4", note="art. 61 : 4,30 m (hauteur libre à signaler en deçà)"),
            src("estimation", note="mât Ø 219, console à deux tubes Ø 114 et treillis Ø 50, portée 6 m")],
           "estimation", "acier_galvanise", "P08_signalisation", ["RF-SV-GEN.HAUTEUR.SURPLOMB"],
           dict(accroche_panneaux="console de X = 0,5 à 6,0 m, Y = +0,10 (panneaux face +Y), bas des panneaux à 5,00 m (≥ 4,30 + 0,60)"))
assemblage("portique_signalisation_L1600", "supports", pieces(
    [CYL((x, 0, 0), (x, 0, 7.6), 0.16, "acier_galvanise", nc=24) for x in (0.0, 16.0)],
    [B((x, 0, -0.02), (0.8, 0.8, 0.04), "acier_galvanise") for x in (0.0, 16.0)],
    [CYL((0, y, z), (16.0, y, z), 0.07, "acier_galvanise", nc=12) for y in (-0.4, 0.4) for z in (5.6, 7.4)],
    [CYL((x, y, 5.6), (x + 1.0, y, 7.4), 0.03, "acier_galvanise", nc=8) for x in [k * 1.0 for k in range(16)] for y in (-0.4, 0.4)],
    [CYL((x, -0.4, z), (x, 0.4, z), 0.03, "acier_galvanise", nc=8) for x in [k * 2.0 for k in range(9)] for z in (5.6, 7.4)]),
    dict(portee_m=16.0, hauteur_poutre_m=[5.6, 7.4], bas_panneau_m=5.5),
    [src("iisr1", 19, article="art. 9 c", note="gabarit + 0,10 + 0,50"), src("estimation", note="portique à poutre treillis 0,8 × 1,8 m, "
                                                                                              "poteaux Ø 320, portée 16 m (2 × 2 voies + BAU)")],
    "estimation", "acier_galvanise", "P08_signalisation", ["RF-SV-GEN.HAUTEUR.SURPLOMB", "RF-SV-GEN.REPETITION_GAUCHE_2X2"],
    dict(accroche_panneaux="face +Y de la poutre (Y = +0,45), bas des panneaux à 5,50 m (autoroute : gabarit 4,75 + 0,60 = 5,35)"))


def _potence_feux(portee, H, d_mat=0.168):
    out = [B((0, 0, -0.01), (0.45, 0.45, 0.03), "acier_galvanise"), CYL((0, 0, 0), (0, 0, H), d_mat / 2, "acier_galvanise", nc=24)]
    pts = [(0, 0, H - 0.4, 0.057)] + [(0.3 * k, 0, H - 0.4 + 0.02 * k, 0.057 - 0.001 * k) for k in range(1, int(portee / 0.3) + 1)]
    out.append(T(pts, "acier_galvanise", nc=16))
    out.append(CYL((0, 0, H - 1.3), (portee * 0.45, 0, H - 0.45), 0.03, "acier_galvanise", nc=10))
    return out


for portee in (4.0, 6.0, 8.0):
    assemblage(f"potence_feux_L{int(portee * 100):03d}", "supports", pieces(_potence_feux(portee, 6.2)),
               dict(portee_m=portee, hauteur_mat_m=6.2, diametre_mat_m=0.168),
               [src("feux_doc", note="§ 12 : potence portée 3 à 8 m, bas du boîtier ≈ 5,0 m [G]"),
                src("estimation", note="mât Ø 168, crosse Ø 114 légèrement montante, tirant Ø 60")], "estimation", "acier_galvanise",
               "P09_feux", ["RF-FEU.HAUTEUR.SURPLOMB"],
               dict(accroche_tete="extrémité de la crosse, bas du boîtier à 5,0 m (tête R11v D300 de l'étape 1 sous la crosse)"))

# ============================================================================================== 7. BORDURES, ÎLOTS, GIRATOIRES
def _elem_e3(pid, mode, L=None, R=None, angle=90.0, suffixe=None, materiau=None, sources_sup=(), confiance=None, note=None,
             profil=None, famille=None, centrer=1, H=None, base=None, vue=None, lecture=None):
    if profil is None:
        p = SP.PROFILS[pid]
        pts, H, base, vue, lecture, sources, conf = p["pts"], p["H"], p["base"], p.get("vue"), p.get("lecture"), p["sources"], p["confiance"]
        fam = "caniveaux" if p["famille"] == "caniveau" else "bordures"
    else:
        pts, sources, conf, fam = profil, [], "moyenne", famille or "bordures"
    params = dict(contour_a=SP.chaine(pts), mode=mode, longueur=L or 0.0, rayon=R or 0.0, angle_deg=angle, centrer=centrer)
    nom = {0: "droit", 1: "rampant", 2: "courbe_ext", 3: "courbe_int", 4: "angle_sortant", 5: "angle_rentrant"}[mode]
    dims = dict(base_m=base, H_m=H)
    if L:
        dims["longueur_m"] = L
    if R:
        dims.update(rayon_face_m=R, angle_deg=round(angle, 3))
    ajouter(f"bordure_{pid}_{suffixe or nom}", fam, "route::extrusion_profil", params, dims, list(sources) + list(sources_sup),
            confiance or conf, materiau or ("granit_gris_flamme" if pid.startswith("GR_") else "beton_bordure"), "P02_bordures",
            ["RF-GV-RAY-006"], dict(pas_m=L if L else round(R * math.radians(angle), 4), vue_m=vue), note=note,
            type_=f"bordure {pid} – {nom}")
    ASSETS[-1]["profil"] = pid
    ASSETS[-1]["lecture_profil"] = lecture
    ASSETS[-1]["vue_nominale_m"] = vue


JOINT = SP.JOINT
S_PAS_R = {"doc": "bordures_elements.json", "note": "regle_pas_rayon.pieces_courbes : rayons catalogue 0,5 ; 1,2-2,0 ; 3-9 m"}
for pid in ("T1", "T3", "A2", "I2", "CS2", "CC1", "GR_T2"):
    for R in (1.2, 3.0, 6.0):
        ang = math.degrees((1.0 - JOINT) / R)
        modes = (2, 3) if pid not in ("CS2", "CC1") else (2, 3)
        for mode in modes:
            _elem_e3(pid, mode, R=R, angle=ang, suffixe=f"courbe_{'ext' if mode == 2 else 'int'}_R{int(R * 100):03d}", centrer=0,
                     sources_sup=[S_PAS_R], confiance="moyenne",
                     note="élément courbe de 1 m mesuré sur la face (vue) ; complète les courbes T2 de l'étape 1")
# granit : profils A et P3 (Noblema), en granit
GR_E3 = {
    "GR_A2": dict(pts=SP.PROFILS["A2"]["pts"], H=0.20, base=0.15, vue=[0.04, 0.10],
                  lecture="profil A2 (Alkern p. 15) en granit (Noblema : A2 15 × 20)"),
    "GR_A1": dict(pts=SP.PROFILS["A1"]["pts"], H=0.25, base=0.20, vue=[0.06, 0.12],
                  lecture="profil A1 (Alkern p. 15) en granit (Noblema : A1 20 × 25)"),
    "GR_P3": dict(pts=SP.PROFILS["P3"]["pts"], H=0.20, base=0.06, vue=[0.0, 0.06], lecture="P3 6 × 20 en granit (Noblema)"),
}
for pid, p in GR_E3.items():
    for L, suf in ((1.0 - JOINT, "L100"), (0.5 - JOINT, "L050")):
        _elem_e3(pid, 0, L=L, suffixe=suf, profil=p["pts"], H=p["H"], base=p["base"], vue=p["vue"], lecture=p["lecture"],
                 materiau="granit_gris_flamme", sources_sup=[src("noblema", note=p["lecture"]), src("alkern2026", 15 if "A" in pid else 21)],
                 confiance="moyenne", note="section du profil béton correspondant (le granit est taillé à la même section)")
# rampants complémentaires (bordures en pente)
for pa, pb, va, vb in (("T3", "T3_basse", 0.18, 0.12), ("T2_basse", "T2_surbaissee", 0.10, 0.02)):
    if len(SP.PROFILS[pa]["pts"]) == len(SP.PROFILS[pb]["pts"]):
        for cote in ("droite", "gauche"):
            r = SP._rampant(pa, pb, va, vb, cote=cote)
            ajouter(r["id"], "bordures", r["hda"], r["params"], r["dimensions"], r["sources"], r["confiance"], r["materiau"],
                    "P02_bordures", [], dict(pas_m=0.994), note=r["note"], type_=r["type"])
# bordure franchissable de giratoire « Ariane » (Alkern p. 51) : courbes pour Ø extérieur 6, 10, 16 m
ARIANE = SP.contour([(0.0, 0.0), (0.0, 0.123), (0.36, 0.242), (0.36, 0.252), (0.43, 0.263), (0.52, 0.29), (0.60, 0.30), (0.60, 0.0)],
                    [(5, 0.06)])
for Dext in (6.0, 10.0, 16.0):
    R = Dext / 2
    n = round(12 + (44 - 12) * (Dext - 3.0) / (16.0 - 3.0))
    ang = 360.0 / n
    ajouter(f"giratoire_ariane_D{int(Dext * 100):04d}_element", "ilots", "route::extrusion_profil",
            dict(contour_a=SP.chaine(ARIANE), mode=2, longueur=0.0, rayon=R, angle_deg=ang, centrer=0, sections=8),
            dict(diametre_ext_m=Dext, nb_elements=n, angle_deg=round(ang, 3), largeur_m=0.60, hauteur_m=0.30),
            [src("alkern2026", 51, "Giratoire Ariane", note="profil 600 × 300 encastré, face en pente vers l'extérieur ; Ø ext 3 à 16 m, "
                                                            "12 à 44 éléments"),
             src("estimation", note="profil relu sur un dessin non à l'échelle : pied au niveau fini à 123 mm du dessous, ressaut à "
                                    "0,36 m, sommet 300 ; nombre d'éléments interpolé linéairement entre 12 (Ø 3) et 44 (Ø 16)")],
            "moyenne", "beton_prefa_lisse", "P02_bordures", [],
            dict(pose=f"{n} éléments en couronne, pivot sur le rayon extérieur {R:g} m, dessous à −0,123 m sous le niveau fini"),
            note="face vue côté anneau (extérieur, u = 0) ; dessus blanc cassé ou gris (Alkern)",
            type_=f"bordure franchissable de giratoire Ariane – élément pour Ø {Dext:g} m")
for nom, D, h, prof, page, note in (
        ("giratoire_franchissable_D300", 3.0, 0.14, [(0.0, 0.0), (1.46, 0.0), (1.50, 0.04), (1.10, 0.10), (0.5, 0.135), (0.0, 0.14)], 52,
         "Ø 3,00, 7 éléments, hauteur 0,14, 1,19 t ; pour carrefours de Ø 15 à 24 m"),
        ("giratoire_franchissable_D400", 4.0, 0.23, [(0.0, 0.0), (2.00, 0.0), (2.00, 0.16), (1.93, 0.23), (0.0, 0.23)], 53,
         "Ø 4,00 (386 au sommet), 4 éléments, hauteur 0,23, chanfrein 7 × 7, 6,86 t")):
    ajouter(nom, "ilots", "route::revolution", dict(profil=SP.chaine(prof), bandes="", divisions=64, materiau="beton_prefa_lisse"),
            dict(diametre_m=D, hauteur_m=h), [src("alkern2026", page, note=note)], "moyenne", "beton_prefa_lisse", "P02_bordures", [],
            dict(pose="posé ou collé sur dalle de fondation, centre du carrefour"),
            note="monolithe de révolution (joints des éléments non modélisés) ; profil du Ø 3 m estimé (dôme bas)")
for nom, L, l, h, page, note in (("ilot_separateur_100x50x25", 1.0, 0.5, 0.25, 49, "îlot séparateur droit 100 × 50 × 25, 268 kg"),
                                 ("ilot_separateur_60x60x25_arrondi", 0.6, 0.6, 0.25, 49, "îlot séparateur arrondi 60 × 60 × 25, 203 kg"),
                                 ("ilot_monobloc_120x60x13", 1.2, 0.6, 0.13, 50, "îlot monobloc 120 × 60 × 13, 172 kg"),
                                 ("ilot_monobloc_120x60x18", 1.2, 0.6, 0.18, 50, "îlot monobloc 120 × 60 × 18, 250 kg")):
    ajouter(nom, "ilots", "route::dalle", dict(longueur=L, largeur=l, epaisseur=h, chanfrein=0.03, plots=0),
            dict(longueur_m=L, largeur_m=l, hauteur_m=h), [src("alkern2026", page, note=note)], "moyenne", "beton_prefa_lisse",
            "P02_bordures", [], dict(pose="posé sur la chaussée (séparateur de piste, îlot provisoire)"),
            note="biseaux et arrondis approchés par un chanfrein de 3 cm")

# ============================================================================================== 8. DALLES, PAVÉS, GALETS
S_FMT = src("estimation", note="format courant du commerce (NF EN 1338 pavés / NF EN 1339 dalles), à confirmer par un catalogue")
for nom, L, l, e, ch, mat, srcs, conf in (
        ("dalle_beton_300x300x50", 0.30, 0.30, 0.05, 0.003, "beton_prefa_lisse", [S_FMT], "estimation"),
        ("dalle_beton_400x400x50", 0.40, 0.40, 0.05, 0.003, "beton_prefa_lisse", [S_FMT], "estimation"),
        ("dalle_beton_500x500x60", 0.50, 0.50, 0.06, 0.003, "beton_prefa_lisse", [S_FMT], "estimation"),
        ("dalle_granit_600x400x80", 0.60, 0.40, 0.08, 0.003, "granit_gris_flamme", [S_FMT], "estimation"),
        ("dalle_reperage_porte_bus_600x600", 0.60, 0.60, 0.06, 0.003, "beton_prefa_lisse",
         [src("estimation", note="dalle de repérage de la porte avant 60 × 60 (RF-MA-BUS-009)")], "moyenne"),
        ("pave_granit_100x100x100", 0.10, 0.10, 0.10, 0.006, "granit_gris_flamme", [S_FMT], "estimation"),
        ("pave_granit_200x100x100_scie", 0.20, 0.10, 0.10, 0.003, "granit_gris_flamme",
         [src("angers_cpu", note="pavés granit sciés pour l'accessibilité PMR"), S_FMT], "estimation"),
        ("pave_beton_200x200x80", 0.20, 0.20, 0.08, 0.005, "beton_prefa_lisse", [S_FMT], "estimation")):
    ajouter(nom, "dalles" if nom.startswith("dalle") else "paves", "route::dalle",
            dict(longueur=L, largeur=l, epaisseur=e, chanfrein=ch, plots=0), dict(longueur_m=L, largeur_m=l, epaisseur_m=e),
            srcs, conf, mat, "P04_trottoirs", ["RF-MA-BUS-009"] if "porte_bus" in nom else [],
            dict(joint_m=0.005, appareillage="à joints croisés (pose par instances) ou texture d'appareillage pour les grandes surfaces"))
for nom, r in (("galet_couronne_60", (0.035, 0.028, 0.020)), ("galet_couronne_90", (0.050, 0.040, 0.028)),
               ("galet_couronne_120", (0.065, 0.050, 0.035))):
    assemblage(nom, "paves", pieces(E((0, 0, r[2] * 0.6), r, "galets_roules", 14)), dict(longueur_m=2 * r[0], largeur_m=2 * r[1], hauteur_m=2 * r[2]),
               [src("estimation", note="galets roulés 6 à 12 cm scellés en couronne d'îlot ou de giratoire (calade) ; matériau "
                                       "galets_scelles pour les surfaces")], "estimation", "galets_roules", "P04_trottoirs", [],
               dict(pose="semis dense dans un mortier (enfoncé de 40 %), surface au matériau galets_scelles"))

# ============================================================================================== 9. SUPPORTS COMPLÉMENTAIRES (panneaux montés)
for d, H in ((0.0603, 4.0), (0.076, 4.0), (0.076, 4.5)):
    ajouter(f"support_rond_D{int(round(d * 1000))}_H{int(H * 10):02d}", "supports", "route::poteau",
            dict(section="rond", d1=d, d2=d, hauteur=H, platine=0, serrage=1 if abs(d - 0.0603) < 1e-3 else 0,
                 bande_contrastee=1, bouchon=1, materiau="acier_galvanise", serrage_diam=0.155, serrage_ep=0.0027),
            dict(hauteur_m=H, section="rond", d1_m=d, d2_m=d),
            [src("iisr1", 15, article="art. 6 B 1°", note="supports ronds Ø 48,3 - 60,3 - 76 mm"),
             src("arrete2007", note="bande contrastée entre 1,20 et 1,40 m"),
             src("iisr1", 19, article="art. 9 b", note="hauteur sous panneau jusqu'à 2,30 m en agglomération")],
            "haute", "acier_galvanise", "P08_signalisation", ["RF-SV-D.HAUTEURS"],
            dict(usage="panneau + panonceau au-dessus de 2,30 m (hauteur totale > 3,5 m)"),
            note="longueur hors sol ; complète les supports de 3,0 et 3,5 m de l'étape 1")

# ============================================================================================== 10. ENSEMBLES (compositions USD)
# (id, support (étape 1 ou 3), [(panneau, gamme, contexte)], hauteur du bord inférieur le plus bas, sources)
S_H230 = src("iisr1", 19, article="art. 9 b", note="en agglomération éclairée, hauteur jusqu'à 2,30 m (bord inférieur du "
                                                   "panneau le plus bas)")
S_H100 = src("iisr1", 19, article="art. 9 a", note="rase campagne : 1,00 m (sauf cas particuliers)")
S_EXCL = src("iisr1", 16, article="art. 6", note="supports des AB3a et AB4 exclusifs de tout autre panneau (panonceaux admis)")
ENSEMBLES_PANNEAUX = [
    ("ensemble_AB3a_agglo", "support_rond_D60_H40", [("AB3a", "normale")], 2.30, [S_H230, S_EXCL]),
    ("ensemble_AB3a_campagne", "support_rond_D76_H30", [("AB3a", "normale")], 1.00, [S_H100, S_EXCL]),
    ("ensemble_AB4_agglo", "support_rond_D60_H35", [("AB4", "normale")], 2.30, [S_H230, S_EXCL]),
    ("ensemble_AB4_campagne", "support_rond_D76_H30", [("AB4", "normale")], 1.00, [S_H100, S_EXCL]),
    ("ensemble_AB25_agglo", "support_rond_D60_H35", [("AB25", "normale")], 2.30, [S_H230]),
    ("ensemble_AB6_agglo", "support_rond_D60_H40", [("AB6", "normale")], 2.30, [S_H230]),
    ("ensemble_AB2_campagne", "support_rond_D76_H30", [("AB2", "normale")], 1.00, [S_H100]),
    ("ensemble_A13b_agglo", "support_rond_D60_H35", [("A13b", "petite")], 2.30, [S_H230]),
    ("ensemble_A13a_campagne", "support_rond_D76_H30", [("A13a", "normale")], 1.00, [S_H100]),
    ("ensemble_B1_agglo", "support_rond_D60_H35", [("B1", "normale")], 2.30, [S_H230]),
    ("ensemble_B2a_agglo", "support_rond_D60_H35", [("B2a", "petite")], 2.30, [S_H230]),
    ("ensemble_B6a1_agglo", "support_rond_D60_H35", [("B6a1", "petite")], 2.30, [S_H230]),
    ("ensemble_B14_30_agglo", "support_rond_D60_H35", [("B14_30", "petite")], 2.30, [S_H230]),
    ("ensemble_B14_50_agglo", "support_rond_D60_H35", [("B14_50", "normale")], 2.30, [S_H230]),
    ("ensemble_B14_70_campagne", "support_rond_D76_H30", [("B14_70", "normale")], 1.00, [S_H100]),
    ("ensemble_B14_90_campagne", "support_rond_D76_H30", [("B14_90", "normale")], 1.00, [S_H100]),
    ("ensemble_B21_1_ilot", "support_rond_D60_H30", [("B21-1", "petite")], 1.00,
     [src("iisr1", 19, note="sur îlot : 1,00 m courant (visibilité, gabarit)")]),
    ("ensemble_B22a_agglo", "support_rond_D60_H35", [("B22a", "petite")], 2.30, [S_H230]),
    ("ensemble_C12_agglo", "support_rond_D60_H35", [("C12", "petite")], 2.30, [S_H230]),
    ("ensemble_C20a_agglo", "support_rond_D60_H35", [("C20a", "petite")], 2.30, [S_H230]),
    ("ensemble_C13a_agglo", "support_rond_D60_H35", [("C13a", "petite")], 2.30, [S_H230]),
    ("ensemble_C1a_agglo", "support_rond_D60_H35", [("C1a", "petite")], 2.30, [S_H230]),
    ("ensemble_J5_nez_ilot", "support_rond_D60_H30", [("J5", "normale")], 1.00,
     [src("iisr1", 25, "art. 9-2 E", note="J5 sur le nez d'îlot, bord inférieur à 1 m")]),
    ("ensemble_B6a1_M6h_agglo", "support_rond_D60_H40", [("M6h", "normale"), ("B6a1", "petite")], 2.30,
     [S_H230, src("iisr1", 19, article="art. 9-1 A", note="panonceau placé sous le panneau, sur le même support et dans le même plan")]),
]
ENSEMBLES_FEUX = [
    ("ensemble_feux_meylan_mat_principal", "mat_feux_D114_H34_fourreau",
     [("feu_R11v_meylan_pots", 2.30, 0), ("feu_repetiteur_R11v_meylan", 1.15, 0), ("feu_R12_meylan_boitier_horizontal", 1.95, 90),
      ("feu_boitier_appel_pieton", 0.92, 90)],
     [src("feux_json", note="feu_NE_droite : tête R11v 2,37-3,47 m, répétiteur 1,14-1,65, R12 1,98-2,28, bouton 0,93-1,08, "
                            "mât 3,4 m, fourreau jaune 0,58-0,93"), src("feux_doc", note="§ 7 : valeurs [G] 2,30 / 1,40 / 2,10 / 1,00")]),
    ("ensemble_feux_meylan_ilot_axial", "mat_feux_D114_H42",
     [("feu_R11v_meylan_pots", 2.90, 0), ("feu_repetiteur_R11v_meylan", 1.15, 0)],
     [src("feux_json", note="mât 4,2 m sur l'îlot axial, tête 4,0-4,1 m en haut")]),
    ("ensemble_feux_R11v_D200_mat_D90", "mat_feux_D90_H34", [("feu_R11v_D200", 2.30, 0), ("feu_repetiteur_R11v_D90", 1.20, 0)],
     [src("feux_doc", note="§ 7 [G] : bas du boîtier 2,30, répétiteur centré 1,40")]),
]

# ============================================================================================== 11. VOCABULAIRE DES DESCRIPTIONS
# Mots des descriptions simples (recon/generateur/description/FORMAT_DESCRIPTION.md § 5-6, § 9-10) -> assets et matériaux de
# la bibliothèque. Proposition au générateur (étape 2) ; le premier élément est le choix par défaut, « meylan » = gamme de
# Grenoble-Alpes Métropole ou relevés du site.
CORRESPONDANCES = {
    "separateurs": {
        "glissière": ["retenue_glissiere_GS2_module_L400", "retenue_glissiere_GS4_module_L400",
                      "retenue_glissiere_GS2_extremite_abaissee_L1200"],
        "glissière double / DE2": ["retenue_glissiere_DE2_module_L400"],
        "GBA": ["retenue_GBA_L400", "retenue_GBA_L100", "retenue_GBA_extremite_abaissee_L0165", "retenue_GBA_extremite_abaissee_L2000"],
        "DBA": ["retenue_DBA_L400", "retenue_DBA_L100", "retenue_DBA_extremite_abaissee_L0165", "retenue_DBA_extremite_abaissee_L2000"],
        "muret": ["retenue_MVL_L400", "retenue_MVL_L100"],
        "atténuateur / musoir": ["retenue_attenuateur_P80", "retenue_attenuateur_P50", "retenue_attenuateur_M80", "retenue_attenuateur_P110"],
        "potelets": ["potelet_GAM_acier_D89_H120", "potelet_GAM_memoire_forme_D90_H90", "potelet_gorge_D102_H100"],
        "bornes": ["borne_bois_GAM_150x150_H130", "balise_borne_PU_D200_H66"],
        "balises": ["balise_J11_H085", "balise_J11_H070", "balise_J11_H050", "balise_quille_PU_D80_H100"],
        "plots": ["balise_J15a_plot"],
        "barrières": ["barriere_GAM_croix_st_andre_L120", "barriere_GAM_croix_st_andre_L150", "barriere_GAM_croix_st_andre_L080"],
    },
    "bordures": {
        "bordure granit": ["bordure_GR_T2_L100", "bordure_GR_A2_L100", "bordure_GR_P3_L100", "bordure_GR_T2_courbe_ext_R300"],
        "giratoire franchissable": ["giratoire_ariane_D1000_element", "giratoire_franchissable_D400", "giratoire_franchissable_D300"],
        "îlot préfabriqué": ["ilot_separateur_100x50x25", "ilot_monobloc_120x60x13"],
        "avaloir": ["assainissement_avaloir_T2_bouche_egout"],
    },
    "materiaux": {
        "enrobé neuf": ["enrobe_neuf"], "enrobé usé": ["enrobe_bbsg_use"], "enrobé ancien": ["enrobe_bbsg_ancien"],
        "BBTM": ["enrobe_bbtm"], "enduit / gravillonné": ["enrobe_esu_gravillonne"],
        "rapiécé": ["enrobe_pelade_rapiece", "enrobe_reprise"], "fissuré": ["enrobe_fissure", "enrobe_faience"],
        "granulats clairs": ["enrobe_granulats_clairs"], "rouge": ["enrobe_colore_rouge", "resine_rouge"],
        "ocre": ["enrobe_colore_ocre"], "béton désactivé": ["beton_desactive", "beton_desactive_moyen", "beton_desactive_gros"],
        "béton balayé": ["beton_balaye"], "résine": ["resine_gravillonnee_beige", "resine_rouge"],
        "galets": ["galets_scelles", "galets_roules"], "pavés": ["paves_granit_carres", "paves_beton_chevrons", "paves_beton_rect"],
        "dalles": ["dalles_beton_grises", "dalles_beton_40", "dalles_beton_ocre"], "dalles gazon": ["dalles_beton_gazon"],
        "gravier / gravillons": ["gravillons_roules_gris", "gravillons_stabilises"], "BRF": ["brf_copeaux_frais"],
        "terre": ["terre_vegetale", "terre_battue"],
    },
    "objets": {
        "candélabre (avenue, voie rapide)": ["candelabre_routier_H100_simple_crosse", "candelabre_routier_H100_double_crosse",
                                             "candelabre_routier_H080_simple_crosse", "candelabre_routier_H120_simple_crosse"],
        "candélabre (rue)": ["candelabre_urbain_H050_top", "candelabre_urbain_H060_crosse", "candelabre_urbain_H040_top"],
        "abri bus": ["abri_bus_L411", "abri_bus_L340"], "arceaux": ["arceau_velo_GAM_a_sceller", "arceau_velo_GAM_a_cheviller"],
        "banc": ["banc_lames_bois_L180_dossier", "banc_lames_bois_L180_sans_dossier"],
        "corbeille": ["corbeille_vigipirate_110L", "corbeille_beton_60L"],
        "regard / tampon": ["assainissement_regard_D600_cadre_rond_850", "assainissement_regard_D600_cadre_carre_840"],
        "grille / avaloir": ["assainissement_grille_plate_750x300_C250", "assainissement_avaloir_T2_bouche_egout"],
        "bouche à clé": ["assainissement_bouche_a_cle_trottoir"],
    },
    "signalisation": {
        "STOP": ["ensemble_AB4_agglo", "ensemble_AB4_campagne", "panneau_AB4"],
        "cédez le passage": ["ensemble_AB3a_agglo", "ensemble_AB3a_campagne", "panneau_AB3a"],
        "giratoire": ["ensemble_AB25_agglo"], "sens interdit": ["ensemble_B1_agglo"], "sens unique": ["ensemble_C12_agglo"],
        "passage piéton (panneau)": ["ensemble_C20a_agglo"], "limitation 30 / 50": ["ensemble_B14_30_agglo", "ensemble_B14_50_agglo"],
        "nez d'îlot": ["ensemble_J5_nez_ilot", "ensemble_B21_1_ilot"],
        "feux (Meylan)": ["ensemble_feux_meylan_mat_principal", "ensemble_feux_meylan_ilot_axial"],
        "feux (générique)": ["ensemble_feux_R11v_D200_mat_D90"],
        "potence / portique": ["potence_signalisation_L600", "portique_signalisation_L1600", "potence_feux_L600"],
    },
}
