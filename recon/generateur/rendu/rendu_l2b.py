"""Rendus soignés d'une scène (lot L2b, corrigé après contrôle ; hython) : route fabriquée (L2) et marquages (L2b) en
USD, matériaux PBR de la bibliothèque recalés sur les photos de Meylan (sols en MaterialX, Karma XPU : détail de la
bibliothèque recoloré × carte macro × bruit fractal en coordonnées du monde, aucune répétition visible), ciel physique
(Preetham) et soleil à 42°, arbres procéduraux aux dimensions du modèle (essence, hauteur, houppier, fût au gabarit
RF-OSM-VEG-001), prolongements de la route hors de l'emprise, sol de décor sans couture, fond de relief ; caméras
standard (dessus, oblique 3/4 à ~25 m, conducteur 1,20 m, piéton 1,60 m), vues de détail et vues ciblées aux points
singuliers ; Karma XPU (husk), développement à exposition fixe, tuiles natives, planche catalogue (≤ 1092 px), mesures :
dynamique p99 − p1 (critère L1), part des maillages texturés (critère M1), dimensions des arbres posés.

Sorties : <sortie>/<scene>/rendus/{<vue>.png, tuiles/<vue>/, planche_<scene>.png, scene_rendu.usda, ciel.exr,
manifest_rendus.json (avec l'empreinte sha256 de l2/route_l2.usda et l2b/route_l2b.usda rendus)}. Textures du
rendu : <sortie>/_rendu_commun/textures/ (rendu/textures.py, rendu/textures_sol.py).
Rien ici ne fabrique la route : le décor est déclaré comme tel dans le manifeste.

ÉTAPE 1 — ROUTE SEULE (défaut ; décision de l'utilisateur du 17/10/2026 : « il ne doit pas générer la montagne : il doit
générer les routes, la chaussée, etc. dans un premier temps ; la végétation, c'est dans un deuxième temps ») :
- rien en dehors de l'emprise de la route : ni arbres (même ceux du modèle : fosses et terre-plein restent des surfaces),
  ni montagnes, ni prairie, ni prolongements ; les abords du modèle (« pelouse 6 ») ne sont pas rendus (sous-ensemble
  de faces lié à un matériau invisible, la couche l2/route_l2.usda reste référencée telle quelle) ;
- la route repose sur un socle : jupe verticale sous la limite extérieure du profil et coupe nette en s = 0 et s = L
  (fin de tronçon propre), sol plat, neutre et uni (gris-beige clair, mat) ; ciel physique clair sans nuage, soleil ;
- les accotements enherbés et le terre-plein gardent leur matériau, en aspect sobre (sans cartes méso ni macro) ;
- toute l'attention va à la route : enrobé gris chaud à usure légère et reprises discrètes, bordures de la valeur du
  trottoir, caniveaux, BEV en dalles jointées, passages piétons un peu grisés.
Le décor de l'étape 2 (arbres aux dimensions du modèle, prolongements, sol de décor, fond de relief, nuages) reste dans
decor_l2b.py et ce module, désactivé : `rendre_scene(..., decor_etape2=True)` (pilote : --decor-etape2).
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

import hou
import ciel as CI
import decor_l2b as DC
import rendre_l2 as RL
import textures as TX
import textures_sol as TS

RES = (1600, 1000)
RES_DESSUS = (1092, 1092)
SOLEIL = 4.2                       # éclairement normal du soleil (unités UsdLux, DistantLight normalisée)
# soleil à 42° (correction après contrôle : à 25°, les faces des bordures recevaient 2,1 fois l'éclairement du sol et
# se lisaient comme des rives peintes ; la relecture demandait 40-50°)
SOLEIL_ELEVATION = 42.0
SOLEIL_AZIMUT = -118.0             # depuis +x (est), sens trigonométrique : sud-sud-ouest (ombres vers le nord-est)
PART_CIEL = 0.17                   # éclairement horizontal du ciel / celui du soleil (ciel clair, 0,15 à 0,25)
TURBIDITE = 2.8
# exposition : albédo a d'une surface horizontale sous le soleil et le ciel -> valeur linéaire a (gain 1 ; 1,30 avant
# la correction, qui éclaircissait l'enrobé à 0,55 en vue de dessus contre 0,33 dans la référence de l'utilisateur)
EXPO_GAIN = 1.0
# courbe en S après l'encodage sRGB (extrémités fixes ; pentes 1 − c aux extrémités, 1 + c au milieu) : 0,50 au lieu de
# 0,30 (correction après contrôle : lisibilité en vue de dessus, contraste d'un développement photographique)
CONTRASTE = 0.50
CIEL_FOND = 2.2                    # ciel vu en image : radiance × 2,2 (le ciel physique clair vaut ~0,2 × un blanc au soleil)
ECHANTILLONS = 128
CLIP_LOIN = 20000.0                # fond de relief jusqu'à 12 km

# aspect des sols (MaterialX) : materiau_id -> (bibliothèque, matériau source, albédo moyen visé (RGB linéaire),
# contraste du motif, part de chroma d'origine, carte macro, amplitude et échelle (m) du bruit fractal, rugosité).
# Cibles (rapport RAPPORT_correction.md § 3) : enrobé ancien 0,11 gris chaud (photos M20, M24, M27 : teinte 25-29°,
# saturation 0,03-0,08 ; relecture : 0,10-0,14) ; béton balayé 0,35 ; enrobé de trottoir clair (granulats clairs,
# vieilli) 0,35 : écart trottoir − enrobé de la référence de l'utilisateur en vue de dessus (0,318 ; à 0,24 il ne valait
# que 0,21) ; dalles 0,32 gris (et non sable) ; herbe : teinte 75-80° (photos I10, I11, M24 : 72-80°), saturation
# modérée (0,23-0,25 en vue de dessus ; photo M24 0,14, référence 0,21 ; 0,39 avant : vert « citron »), albédo 0,11 ×
# cartes macro et méso (σY ≥ 0,10 en vue de dessus).
# Correction après le second contrôle : teintes calées sur le RENDU (et non sur l'albédo seul). L'éclairage (soleil
# chaud + ciel bleu) rend un albédo neutre à (1,00 ; 1,00 ; 1,035) en vue de dessus : un enrobé visé à 29° sortait à
# 17-19°. Albédos recalculés pour une teinte rendue d'environ 30° en vue de dessus et en vue conducteur (photos
# Panoramax M20, M24, M27 : 27,7-33,3°, saturation 0,08-0,11 ; essais tmp/second_controle/iter_enrobe.py : 32-33° en vue
# de dessus, 30° en vue conducteur, saturation 0,09-0,11 ; critère C-19), luminance inchangée (0,115).
SOLS = {
    "enrobe_bbsg_ancien": ("route", "enrobe_bbsg_use", (0.1235, 0.1140, 0.1005), 1.0, 0.0, "enrobe", 0.06, 7.0, 0.90),
    "enrobe_bbsg_use": ("route", "enrobe_bbsg_use", (0.1235, 0.1140, 0.1005), 1.0, 0.0, "enrobe", 0.06, 7.0, 0.90),
    "enrobe_bbsg_neuf": ("route", "enrobe_bbsg_use", (0.0634, 0.0612, 0.0590), 1.0, 0.0, None, 0.03, 7.0, 0.85),
    "enrobe_bbsg_neuf_2025": ("route", "enrobe_bbsg_use", (0.0634, 0.0612, 0.0590), 1.0, 0.0, None, 0.03, 7.0, 0.85),
    "enrobe_reprise_tranchee": ("route", "enrobe_bbsg_use", (0.0800, 0.0760, 0.0720), 1.0, 0.0, None, 0.04, 7.0, 0.85),
    "enrobe_trottoir": ("site", "enrobe_trottoir", (0.3680, 0.3470, 0.3260), 0.6, 0.0, None, 0.05, 5.0, 0.90),
    # piste (RF-MA-PIS-009 : enrobé de couleur différente de la chaussée) : recalée sur les photos Panoramax de Meylan
    # (correction après le second contrôle ; avant : gris-vert de l'ortho, plus clair que la chaussée) : piste de M24
    # (f877235a) et Chronovélo de M29 (737f941f) plus sombres que la chaussée (0,04 à 0,09 en luminance) et chaudes
    # (22-44°) : rendu visé 0,05 sous l'enrobé, environ 30°, saturation 0,09 (essais tmp/second_controle/iter_sol.py sur
    # S_M27 : ΔY − 0,052, 30°, saturation 0,087)
    "enrobe_piste_cyclable": ("site", "enrobe_piste_cyclable", (0.0920, 0.0860, 0.0780), 1.0, 0.0, None, 0.05, 5.0, 0.90),
    "beton_balaye": ("route", "beton_balaye", (0.3595, 0.3490, 0.3316), 1.0, 0.0, None, 0.05, 6.0, 0.85),
    "beton_desactive": ("route", "beton_desactive", (0.3300, 0.3200, 0.3000), 1.0, 0.2, None, 0.05, 6.0, 0.90),
    "dalles_beton": ("route", "dalles_beton_40", (0.3260, 0.3196, 0.3068), 1.0, 0.0, None, 0.04, 6.0, 0.85),
    # fosses des avancées (S03) : paillage minéral gris-beige (rendu visé 40°, saturation 0,14 ; correction après le
    # second contrôle : la texture de la bibliothèque, verdâtre à 80°, se lisait comme de la mousse ou de l'herbe)
    "paillage_mineral": ("site", "paillage_mineral", (0.2379, 0.2219, 0.1851), 1.0, 0.0, None, 0.05, 3.0, 0.95),
    "gazon_tondu": ("site", "gazon_tondu", (0.0960, 0.1165, 0.0600), 1.0, 0.35, "herbe", 0.10, 15.0, 0.95),
    "herbe_haute": ("site", "herbe_haute", (0.0975, 0.1175, 0.0550), 1.0, 0.35, "herbe", 0.10, 15.0, 0.95),
}
# cartes méso (facteur, deux lectures de périodes incommensurables, m) : touffes, creux, trèfle, brins secs de l'herbe
# (correction après contrôle : herbe 4 fois trop uniforme en vue de dessus, σY 0,02-0,03 contre 0,11-0,16 sur photos)
MESO = {"gazon_tondu": (("meso_herbe_touffes", 4.7), ("meso_herbe_plaques", 11.3)),
        "herbe_haute": (("meso_herbe_touffes", 4.7), ("meso_herbe_plaques", 11.3))}
# bordures et caniveaux : béton préfabriqué vibré gris à peau lisse de la bibliothèque (route_fr:beton_prefa_lisse,
# « bordures et caniveaux neufs ou récents », albédo 0,242 ; la texture du site beton_bordure, granuleuse et verdâtre,
# se lisait comme du granit). Étape 1 : bordures × 1,44 = 0,35, la valeur du trottoir (0,35-0,37 ; relecture, photos M24
# et I11 : « bordures en béton gris de la même valeur que le trottoir ») ; caniveaux × 1,10 = 0,265 (béton sali au fil
# d'eau, un ton sous la bordure : il ne se lit plus comme une rive peinte)
# Correction après le second contrôle : le béton lisse de la bibliothèque est parfaitement neutre ; rendu à côté des
# trottoirs chauds, il paraissait bleuté (240°, saturation 0,01-0,02). Échelle par canal pour un gris chaud rendu
# (bordure 30°, caniveau 35° ; saturation 0,075 ; photos M24 : bordures 28-33°, saturation 0,07-0,10, caniveau 40°) à
# luminance inchangée (bordure 0,349 = × 1,44 ; caniveau 0,267 = × 1,10 ; critère C-18 inchangé).
ECHELLE_ALBEDO = {"beton_bordure_gris": (1.5288, 1.4279, 1.2934), "beton_bordure_clair": (1.5288, 1.4279, 1.2934),
                  "beton_bordure": (1.5288, 1.4279, 1.2934), "caniveau_beton": (1.151, 1.0962, 0.9909)}

# relief de la carte de normales du béton lisse (bibliothèque : × 2 en x, y) atténué à 35 % sur les bordures et les
# caniveaux : à la lumière rasante d'une face verticale, le « bullage fin » se lisait en stries de béton bouchardé
ATTENUER_NORMALE = {"beton_bordure_gris": 0.35, "beton_bordure_clair": 0.35, "beton_bordure": 0.35, "caniveau_beton": 0.35}

# ÉTAPE 1 (route seule) : sol de présentation et aspects sobres
SOL_NEUTRE = (0.50, 0.485, 0.445)  # albédo linéaire du socle et du sol plat : gris-beige clair, mat, uni
VOILE_ROUTE_SEULE = (0.90, 0.97, 1.08)   # teinte du voile d'horizon du ciel clair (blanc bleuté)
# accotements enherbés (S01) et terre-plein engazonné (S06) : surfaces de la route, aspect sobre (texture de la
# bibliothèque recolorée, contraste 0,55, sans cartes macro ni méso ni « touffes »), teinte d'herbe 75-80°
SOLS_ROUTE_SEULE = {
    "gazon_tondu": ("site", "gazon_tondu", (0.0900, 0.1100, 0.0580), 0.55, 0.15, None, 0.03, 9.0, 0.95),
    "herbe_haute": ("site", "herbe_haute", (0.0920, 0.1100, 0.0560), 0.55, 0.15, None, 0.03, 9.0, 0.95),
}
# béton balayé (trottoirs de Meylan) : joints sciés transversaux tous les 2,00 m (routes du catalogue et de Meylan
# selon x ; carte lue en coordonnées du monde)
JOINTS = {"beton_balaye": (("joints_beton", 2.0),)}
# passages piétons « un peu grisés » (relecture, photo M24 : bandes nettement grisées par le passage des roues) :
# albédo de la peinture × GRIS_PASSAGE sur les faces de classe « passage » (sous-ensemble de faces, couche L2b
# inchangée). Correction après le second contrôle : × 0,78 laissait le passage seul à 0,361 (S_M24, usure u2) et 0,390
# (S_M27) au-dessus de l'enrobé en vue de dessus, sous la référence de l'utilisateur (0,406) ; × 0,90 essayé : 0,410
# pour S_M24 (usure u2), marge trop mince ; × 0,93 (passage seul mesuré sur les 15 scènes, critère L2b-16 / C-8 par
# classe de peinture ; la référence de l'utilisateur mesurée par le contrôle : 0,422)
GRIS_PASSAGE = 0.93
TUILE_MASQUE = 9.7                 # période (m) du masque d'usure de la peinture (incommensurable avec les modulations)

# aspect de rendu (materiau_id du modèle -> matériau de bibliothèque) pour les autres matériaux
LOOKS = {
    "beton_bordure_gris": ("route", "beton_prefa_lisse"),
    "beton_bordure_clair": ("route", "beton_prefa_lisse"),
    "beton_bordure": ("route", "beton_prefa_lisse"),
    "caniveau_beton": ("route", "beton_prefa_lisse"),
}
GENERES = {   # matériaux à texture procédurale : (texture, rugosité, alpha, tuile (m) en u, en v, primvar)
    "ecorce": ("ecorce", 0.85, False, 0.5, 0.5, "st"),
    "mortier_joint": ("mortier", 0.9, False, 0.4, 0.4, "st1"),
    "mortier_clair": ("mortier", 0.9, False, 0.4, 0.4, "st1"),
    "PJ_Neutre": ("mortier", 0.8, False, 1.0, 1.0, "st1"),
    "herbe_brin": ("herbe_brin", 0.6, False, 1.0, 1.0, "st"),
    "bev_podotactile": ("bev_dalles", 0.75, False, 0.40, 1.0, "st"),
    "bev_podotactile_sombre": ("bev_dalles_sombre", 0.75, False, 0.40, 1.0, "st"),
    "bev_podotactile_claire": ("bev_dalles_claire", 0.75, False, 0.40, 1.0, "st"),
    "grille_caniveau": ("grille", 0.55, False, 0.5, 0.5, "st1"),
    "grille_avaloir": ("grille", 0.55, False, 1.0, 1.0, "st"),
    "montagne": ("montagne", 1.0, False, 1.0, 1.0, "st"),
    "sol_neutre": ("sol_neutre", 0.95, False, 4.0, 4.0, "st"),
}

# BEV en contraste avec le revêtement voisin (RF-MA-OBS-003, arrêté du 15/01/2007 annexe 1 : contraste de luminance
# recherché 0,70, durable acceptable 0,40 ; correction après le second contrôle : BEV gris clair sur trottoir clair,
# contraste 0,13 à 0,16) : anthracite (albédo 0,10) sur un revêtement clair (albédo visé ≥ SEUIL_BEV_CLAIR), gris clair
# (0,43) sur un enrobé ; (dalle, joint) en albédo linéaire. La photo M24 montre une BEV claire sur béton clair (peu
# contrastée) : la règle est préférée à la photo (choix déclaré, à trancher par l'utilisateur).
BEV_TEINTES = {"sombre": ((0.1043, 0.1016, 0.0954), (0.22, 0.215, 0.205)),
               "claire": ((0.4365, 0.4221, 0.3888), (0.10, 0.10, 0.095))}
SEUIL_BEV_CLAIR = 0.20


def variante_bev(materiau_voisin):
    """« sombre » sur un revêtement clair, « claire » sur un revêtement sombre (luminance de l'albédo visé de SOLS)."""
    s = SOLS.get(materiau_voisin)
    y = 0.2126 * s[2][0] + 0.7152 * s[2][1] + 0.0722 * s[2][2] if s else 0.35
    return "sombre" if y >= SEUIL_BEV_CLAIR else "claire"


def decalage_scene(scene, periode=64.0):
    """Décalage (m) propre à la scène, tiré du hachage de son identifiant (sha256) : les cartes d'usure de l'enrobé
    (reprises, tranchées, fissures, taches) et le masque d'usure de la peinture ne reviennent plus au même endroit
    d'une scène à l'autre (correction après le second contrôle : corrélation 0,67 à 0,80 entre S01, S02, S03, S07, S12)."""
    h = hashlib.sha256(str(scene).encode("utf-8")).digest()
    return (round(int.from_bytes(h[:4], "big") / 2 ** 32 * periode, 4),
            round(int.from_bytes(h[4:8], "big") / 2 ** 32 * periode, 4))


# vues propres aux scènes : nom -> ((s, t, h) œil, (s, t, h) cible, focale mm) ; abscisse du sujet pour les vues
# standard (dessus, oblique, conducteur, piéton). Vues ciblées aux points singuliers (correction après contrôle :
# coudes de bordure, ralentisseurs au droit du caniveau, fin de route, angle d'avancée)
SUJET = {"S01": 50.0, "S02": 50.0, "S03": 38.0, "S04": 25.0, "S05": 25.0, "S06": 50.0, "S07": 40.0, "S08": 51.0,
         "S09": 62.0, "S10": 50.0, "S11": 51.4, "S12": 50.0, "S_M24": 40.0, "S_M27": 45.0, "S_M20": 30.0}
VUES = {
    # S01 : flèche de rabattement RAB_D (s = 49) sur l'axe T3, rive T2, surlargeur et accotement enherbé
    "S01": {"detail": ((42.5, -2.4, 2.2), (49.5, 0.3, 0.0), 30)},
    "S02": {"detail": ((26, -1.6, 0.9), (32, -3.4, 0.0), 30)},
    "S03": {"detail": ((24.6, -1.4, 1.2), (31, -3.6, 0.3), 30), "cible_angle_avancee": ((30.0, -1.0, 1.6), (34.5, -4.0, 0.0), 35)},
    "S04": {"detail": ((14, -4.0, 1.4), (26, -4.0, 0.0), 30)},
    "S05": {"detail": ((14, 4.5, 1.6), (26, 4.5, 0.0), 30)},
    "S06": {"detail": ((30, -4.5, 1.6), (50, 0.0, 0.8), 28)},
    "S07": {"detail": ((10, 1.5, 1.2), (22, 1.5, 0.0), 30)},
    "S08": {"detail": ((40, -1.6, 1.3), (52, 0.0, 0.0), 28), "cible_caniveau_dos_ane": ((50.5, -1.9, 1.4), (56.0, -3.0, 0.0), 35),
            "cible_abaisse_bev": ((41.5, -4.6, 1.5), (48.0, -3.2, 0.0), 30)},
    "S09": {"detail": ((22, 1.5, 1.4), (60, 1.5, 0.0), 30), "cible_coude_bordure": ((57.0, 0.6, 1.6), (64.5, 3.0, 0.0), 35)},
    "S10": {"detail": ((40, -1.6, 1.3), (51, 0.0, 0.0), 28), "cible_caniveau_plateau": ((44.0, -1.9, 1.4), (50.0, -3.1, 0.0), 35)},
    "S11": {"detail": ((30, -1.5, 1.3), (60, 6.0, 0.4), 28), "cible_fin_de_route": ((80.0, -1.5, 1.4), (110.0, 2.0, 0.5), 24)},
    "S12": {"detail": ((40, -1.6, 1.3), (52, -1.65, 0.0), 30)},
}
DEPOT = Path(__file__).resolve().parents[3]


class Route:
    """Référence échantillonnée (rg::graphe, sortie 1) : (s, t) -> (x, y) local ; prolongée par ses tangentes."""

    def __init__(self, geo):
        pr = geo.prims()[0]
        pts = pr.points()
        self.s = np.array([p.attribValue("s") for p in pts])
        self.P = np.array([(p.position()[0], -p.position()[2]) for p in pts])
        self.G = np.array([(p.attribValue("gauche")[0], -p.attribValue("gauche")[2]) for p in pts])
        self.L = float(self.s[-1])

    def xy(self, s, t):
        i = int(np.clip(np.searchsorted(self.s, s, side="right") - 1, 0, len(self.s) - 2))
        a = (s - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-12)
        P = self.P[i] + a * (self.P[i + 1] - self.P[i])
        G = self.G[i] + a * (self.G[i + 1] - self.G[i])
        return P + t * G / np.linalg.norm(G)


def bandes_t(sol, s_f, demi=2.0):
    """Bornes en t, au voisinage de s_f, des bandes du sol fabriqué (classe des faces) : chaussée (voies), voie de
    circulation la plus à droite (centre), trottoir de droite (centre ; sinon accotement de droite)."""
    S = np.array(sol.pointFloatAttribValues("s"))
    T = np.array(sol.pointFloatAttribValues("t"))
    par = {}
    for pr in sol.prims():
        c = pr.attribValue("classe")
        if c in ("mur", "sous_element", "abord", ""):
            continue
        b = pr.attribValue("bande_id")
        idx = [v.point().number() for v in pr.vertices()]
        if not any(abs(S[i] - s_f) < demi for i in idx):
            continue
        lo, hi = par.get((c, b), (1e9, -1e9))
        ts = T[idx]
        par[(c, b)] = (min(lo, float(ts.min())), max(hi, float(ts.max())))
    voies = [(v[0], v[1]) for (c, b), v in par.items() if c in ("voie_circulation", "voie_bus")]
    vc = [(v[0], v[1]) for (c, b), v in par.items() if c == "voie_circulation"]
    tr = [(v[0], v[1]) for (c, b), v in par.items() if c == "trottoir"]
    acc = [(v[0], v[1]) for (c, b), v in par.items() if c in ("bande_derasee", "accotement_revetu")]
    chaussee = (min(v[0] for v in voies), max(v[1] for v in voies)) if voies else (-3.0, 3.0)
    vd = min(vc, key=lambda v: v[0]) if vc else (chaussee[0], chaussee[0] + 3.0)
    pt = min(tr, key=lambda v: v[0]) if tr else (min(acc, key=lambda v: v[0]) if acc else (chaussee[0] - 2, chaussee[0]))
    return {"chaussee": chaussee, "voie_droite": 0.5 * (vd[0] + vd[1]), "pieton": 0.5 * (pt[0] + pt[1])}


def z_sol(geo, x, y):
    pos, n, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
    pr = geo.intersect(hou.Vector3(x, 50.0, -y), hou.Vector3(0, -1, 0), pos, n, uvw, None, 0, 1e9, 1e-6)
    return float(pos[1]) if pr >= 0 else 0.0


def materiaux_abords(sol):
    """materiau_id des abords gauche et droit du sol fabriqué (le sol de décor prend le même : aucune couture) ; à
    défaut, celui de la bande la plus extérieure de chaque côté."""
    mats = {"abord_gauche": {}, "abord_droit": {}}
    T = np.array(sol.pointFloatAttribValues("t"))
    ext = {"g": (-1e9, None), "d": (1e9, None)}
    for pr in sol.prims():
        b, m = pr.attribValue("bande_id"), pr.attribValue("materiau_id")
        if b in mats:
            mats[b][m] = mats[b].get(m, 0) + 1
        if pr.attribValue("visible") and pr.attribValue("classe") not in ("mur", "sous_element", "caniveau_releve"):
            ts = T[[v.point().number() for v in pr.vertices()]]
            if ts.max() > ext["g"][0]:
                ext["g"] = (float(ts.max()), m)
            if ts.min() < ext["d"][0]:
                ext["d"] = (float(ts.min()), m)
    g = max(mats["abord_gauche"], key=mats["abord_gauche"].get) if mats["abord_gauche"] else ext["g"][1]
    d = max(mats["abord_droit"], key=mats["abord_droit"].get) if mats["abord_droit"] else ext["d"][1]
    herbes = ("gazon_tondu", "herbe_haute", "gazon_sec", "terre_nue")
    return (g if g in herbes else "gazon_tondu"), (d if d in herbes else "gazon_tondu")


# ------------------------------------------------------------------------------------------- matériaux (aspect)
def _fichier_bib(lib, nom):
    base = RL.LIB_ROUTE if lib == "route" else RL.LIB_SITE
    f = base / nom / f"{nom}.usda"
    return f if f.exists() else None


def _materiau_texture(stage, chemin, png, rugosite, alpha, tuile=(1.0, 1.0), varname="st1", albedo_gain=1.0):
    from pxr import Gf, Sdf, UsdShade
    if not isinstance(tuile, (tuple, list)):
        tuile = (tuile, tuile)
    m = UsdShade.Material.Define(stage, chemin)
    sh = UsdShade.Shader.Define(stage, chemin + "/Surface")
    sh.CreateIdAttr("UsdPreviewSurface")
    rd = UsdShade.Shader.Define(stage, chemin + "/LecteurUV")
    rd.CreateIdAttr("UsdPrimvarReader_float2")
    rd.CreateInput("varname", Sdf.ValueTypeNames.String).Set(varname)
    tx = UsdShade.Shader.Define(stage, chemin + "/Albedo")
    tx.CreateIdAttr("UsdUVTexture")
    tx.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(Path(png).as_posix()))
    tx.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    for w in ("wrapS", "wrapT"):
        tx.CreateInput(w, Sdf.ValueTypeNames.Token).Set("repeat")
    tx.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(albedo_gain, albedo_gain, albedo_gain, 1))
    if tuile != (1.0, 1.0):
        tr = UsdShade.Shader.Define(stage, chemin + "/EchelleUV")
        tr.CreateIdAttr("UsdTransform2d")
        tr.CreateInput("in", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
        tr.CreateInput("scale", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(1.0 / tuile[0], 1.0 / tuile[1]))
        tx.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(tr.ConnectableAPI(), "result")
    else:
        tx.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
    rd.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    tx.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tx.ConnectableAPI(), "rgb")
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rugosite)
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    if alpha:
        tx.CreateOutput("a", Sdf.ValueTypeNames.Float)
        sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(tx.ConnectableAPI(), "a")
        sh.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
    m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return m


def _look_sol(stage, chemin, detail, tuile, macro, etendue, amp, echelle, rugosite, meso=(), coord="monde",
              decalage=(0.0, 0.0)):
    """Sol en MaterialX (Karma XPU) : couleur = détail recoloré (tuile `tuile` m) × carte macro × 2 (étendue m) ×
    Π cartes méso × 4 (meso : [(fichier, tuile m)]) × (1 + amp × bruit fractal 3D de la position / échelle).
    Coordonnées des cartes : coord = « route » (étape 1, correction après le second contrôle) : (s, t) de la route en
    mètres, primvar st_route écrite par le rendu sur les maillages du sol (reprises, tranchées, joints alignés sur la
    route quel que soit le tracé) ; « monde » (décor de l'étape 2) : (x, y) du monde, le même matériau sur deux
    maillages voisins (abord, sol de décor, prolongement) sans couture. decalage : (ds, dt) propre à la scène
    (decalage_scene) ajouté aux coordonnées des cartes et du bruit : l'usure ne revient pas au même endroit d'une
    scène à l'autre."""
    from pxr import Gf, Sdf, UsdShade
    m = UsdShade.Material.Define(stage, chemin)

    def sh(nom, nid):
        s = UsdShade.Shader.Define(stage, f"{chemin}/{nom}")
        s.CreateIdAttr(nid)
        return s

    def out(s, typ):
        return s.CreateOutput("out", typ)

    pos0 = sh("Position", "ND_position_vector3")
    pos0.CreateInput("space", Sdf.ValueTypeNames.String).Set("world")
    out(pos0, Sdf.ValueTypeNames.Vector3f)
    pos = sh("Position_decalee", "ND_add_vector3")
    pos.CreateInput("in1", Sdf.ValueTypeNames.Vector3f).ConnectToSource(pos0.ConnectableAPI(), "out")
    pos.CreateInput("in2", Sdf.ValueTypeNames.Vector3f).Set(Gf.Vec3f(float(decalage[0]), float(decalage[1]), 0.0))
    out(pos, Sdf.ValueTypeNames.Vector3f)
    if coord == "route":
        st = sh("ST_route", "ND_geompropvalue_vector2")
        st.CreateInput("geomprop", Sdf.ValueTypeNames.String).Set("st_route")
        st.CreateInput("default", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(0.0, 0.0))
        out(st, Sdf.ValueTypeNames.Float2)
    else:
        st = sh("XY_monde", "ND_convert_vector3_vector2")
        st.CreateInput("in", Sdf.ValueTypeNames.Vector3f).ConnectToSource(pos0.ConnectableAPI(), "out")
        out(st, Sdf.ValueTypeNames.Float2)
    xy = sh("XY", "ND_add_vector2")
    xy.CreateInput("in1", Sdf.ValueTypeNames.Float2).ConnectToSource(st.ConnectableAPI(), "out")
    xy.CreateInput("in2", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(float(decalage[0]), float(decalage[1])))
    out(xy, Sdf.ValueTypeNames.Float2)

    def image(nom, fic, ech, espace):
        sc = sh(f"Echelle_{nom}", "ND_divide_vector2FA")
        sc.CreateInput("in1", Sdf.ValueTypeNames.Float2).ConnectToSource(xy.ConnectableAPI(), "out")
        sc.CreateInput("in2", Sdf.ValueTypeNames.Float).Set(float(ech))
        out(sc, Sdf.ValueTypeNames.Float2)
        im = sh(f"Image_{nom}", "ND_image_color3")
        a = im.CreateInput("file", Sdf.ValueTypeNames.Asset)
        a.Set(Sdf.AssetPath(Path(fic).as_posix()))
        a.GetAttr().SetColorSpace(espace)
        im.CreateInput("texcoord", Sdf.ValueTypeNames.Float2).ConnectToSource(sc.ConnectableAPI(), "out")
        for k in ("uaddressmode", "vaddressmode"):
            im.CreateInput(k, Sdf.ValueTypeNames.String).Set("periodic")
        out(im, Sdf.ValueTypeNames.Color3f)
        return im

    col = image("detail", detail, tuile, "srgb_texture")
    if macro is not None:
        mc = image("macro", macro, etendue, "raw")
        m2 = sh("Macro_x2", "ND_multiply_color3FA")
        m2.CreateInput("in1", Sdf.ValueTypeNames.Color3f).ConnectToSource(mc.ConnectableAPI(), "out")
        m2.CreateInput("in2", Sdf.ValueTypeNames.Float).Set(2.0)
        out(m2, Sdf.ValueTypeNames.Color3f)
        mu = sh("Detail_x_macro", "ND_multiply_color3")
        mu.CreateInput("in1", Sdf.ValueTypeNames.Color3f).ConnectToSource(col.ConnectableAPI(), "out")
        mu.CreateInput("in2", Sdf.ValueTypeNames.Color3f).ConnectToSource(m2.ConnectableAPI(), "out")
        out(mu, Sdf.ValueTypeNames.Color3f)
        col = mu
    for k, (fic, tu) in enumerate(meso or ()):
        mi = image(f"meso{k}", fic, tu, "raw")
        mx = sh(f"Meso{k}_x2", "ND_multiply_color3FA")
        mx.CreateInput("in1", Sdf.ValueTypeNames.Color3f).ConnectToSource(mi.ConnectableAPI(), "out")
        mx.CreateInput("in2", Sdf.ValueTypeNames.Float).Set(4.0)
        out(mx, Sdf.ValueTypeNames.Color3f)
        mm = sh(f"Detail_x_meso{k}", "ND_multiply_color3")
        mm.CreateInput("in1", Sdf.ValueTypeNames.Color3f).ConnectToSource(col.ConnectableAPI(), "out")
        mm.CreateInput("in2", Sdf.ValueTypeNames.Color3f).ConnectToSource(mx.ConnectableAPI(), "out")
        out(mm, Sdf.ValueTypeNames.Color3f)
        col = mm
    if amp > 0:
        pe = sh("Position_ech", "ND_divide_vector3FA")
        pe.CreateInput("in1", Sdf.ValueTypeNames.Vector3f).ConnectToSource(pos.ConnectableAPI(), "out")
        pe.CreateInput("in2", Sdf.ValueTypeNames.Float).Set(float(echelle))
        out(pe, Sdf.ValueTypeNames.Vector3f)
        fr = sh("Fractal", "ND_fractal3d_float")
        fr.CreateInput("position", Sdf.ValueTypeNames.Vector3f).ConnectToSource(pe.ConnectableAPI(), "out")
        fr.CreateInput("octaves", Sdf.ValueTypeNames.Int).Set(3)
        fr.CreateInput("amplitude", Sdf.ValueTypeNames.Float).Set(float(amp))
        out(fr, Sdf.ValueTypeNames.Float)
        un = sh("Un_plus", "ND_add_float")
        un.CreateInput("in1", Sdf.ValueTypeNames.Float).ConnectToSource(fr.ConnectableAPI(), "out")
        un.CreateInput("in2", Sdf.ValueTypeNames.Float).Set(1.0)
        out(un, Sdf.ValueTypeNames.Float)
        mf = sh("Fractal_x", "ND_multiply_color3FA")
        mf.CreateInput("in1", Sdf.ValueTypeNames.Color3f).ConnectToSource(col.ConnectableAPI(), "out")
        mf.CreateInput("in2", Sdf.ValueTypeNames.Float).ConnectToSource(un.ConnectableAPI(), "out")
        out(mf, Sdf.ValueTypeNames.Color3f)
        col = mf
    srf = sh("Surface", "ND_standard_surface_surfaceshader")
    srf.CreateInput("base", Sdf.ValueTypeNames.Float).Set(1.0)
    srf.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).ConnectToSource(col.ConnectableAPI(), "out")
    srf.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(0.4)
    srf.CreateInput("specular_roughness", Sdf.ValueTypeNames.Float).Set(float(rugosite))
    srf.CreateOutput("out", Sdf.ValueTypeNames.Token)
    m.CreateOutput("mtlx:surface", Sdf.ValueTypeNames.Token).ConnectToSource(srf.ConnectableAPI(), "out")
    return m


def _peinture(stage, chemin, mid, png_albedo, masques=None, gain=1.0, decalage_masque=(0.0, 0.0)):
    """Peinture : albédo texturé (peinture_usee.png : blanc sali 0,66 × facteur de la classe d'usure : u1 0,66, u2 0,58,
    u3 0,52) ; usure = masque d'opacité (textures_sol.masque_usure : granulats affleurants et plages usées, couverture
    de la classe ; st1 au 1/4, seuil 0,5) : l'enrobé apparaît dans les parties usées."""
    from pxr import Gf, Sdf, UsdShade
    cls = mid.rsplit("_u", 1)[-1] if "_u" in mid else "1"
    couleur = mid.split("_")[1] if mid.count("_") >= 2 else "blanc"
    masque = Path((masques or {}).get(cls) or RL.LIB_ROUTE / "peinture_routiere" / "textures" / f"masque_peinture_u{cls}.png")
    k = TS.BLANC_USURE.get(cls, 0.66) / 0.66 * gain
    m = _materiau_texture(stage, chemin, png_albedo, 0.5, False, tuile=1.0, albedo_gain=k)
    sh = UsdShade.Shader(stage.GetPrimAtPath(chemin + "/Surface"))
    if couleur != "blanc":
        teinte = {"jaune": (1.0, 0.78, 0.15), "ocre": (0.85, 0.55, 0.25), "vert": (0.3, 0.7, 0.3),
                  "rouge": (0.85, 0.2, 0.15), "bleu": (0.2, 0.35, 0.8), "cyan": (0.2, 0.7, 0.75)}.get(couleur, (1, 1, 1))
        tx = UsdShade.Shader(stage.GetPrimAtPath(chemin + "/Albedo"))
        tx.GetInput("scale").Set(Gf.Vec4f(teinte[0] * k, teinte[1] * k, teinte[2] * k, 1))
    if masque.exists():
        rd = UsdShade.Shader(stage.GetPrimAtPath(chemin + "/LecteurUV"))
        tr = UsdShade.Shader.Define(stage, chemin + "/EchelleMasque")
        tr.CreateIdAttr("UsdTransform2d")
        tr.CreateInput("in", Sdf.ValueTypeNames.Float2).ConnectToSource(rd.ConnectableAPI(), "result")
        # masque lu sur 9,7 m (étape 1 ; 4 m avant : période voisine de celle des tirets T3 de 4,33 m, la même plage
        # d'usure revenait dans chaque trait)
        tr.CreateInput("scale", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(1.0 / TUILE_MASQUE, 1.0 / TUILE_MASQUE))
        # décalage propre à la scène (fraction de tuile ; correction après le second contrôle)
        tr.CreateInput("translation", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(*[float(x) for x in decalage_masque]))
        mk = UsdShade.Shader.Define(stage, chemin + "/Masque")
        mk.CreateIdAttr("UsdUVTexture")
        mk.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(masque.as_posix()))
        mk.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("raw")
        for w in ("wrapS", "wrapT"):
            mk.CreateInput(w, Sdf.ValueTypeNames.Token).Set("repeat")
        mk.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(tr.ConnectableAPI(), "result")
        mk.CreateOutput("r", Sdf.ValueTypeNames.Float)
        sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(mk.ConnectableAPI(), "r")
        sh.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
    return m, (f"peinture : albédo {Path(png_albedo).name} × {k:.3f} (blanc {TS.BLANC_USURE.get(cls, 0.66)}"
               + (f", passage × {gain}" if gain != 1.0 else "") + f") ; usure : {masque.relative_to(DEPOT).as_posix()}")


def sols(route_seule):
    """Table des aspects de sol du mode de rendu (étape 1 : herbes sobres)."""
    return {**SOLS, **SOLS_ROUTE_SEULE} if route_seule else SOLS


def textures_rendu(commun, saisons_essences, route_seule=False):
    """Textures du rendu (procédurales et recolorées), {nom: chemin} + statistiques des sols recolorés. route_seule
    (étape 1) : ni écorce, ni feuillage, ni relief, ni cartes de l'herbe ; enrobé à usure légère (macro sobre) ; sol
    neutre et joints du béton balayé."""
    tex = TX.generer(commun)
    stats = {}
    tex["peinture_albedo"] = TS.peinture_usee(commun / "peinture_usee.png")
    tex["bev_dalles"], _ = TS.bev_dalles(commun / "bev_dalles.png")
    for v, (dalle, joint) in BEV_TEINTES.items():
        tex[f"bev_dalles_{v}"], stats[f"bev_dalles_{v}"] = TS.bev_dalles(commun / f"bev_dalles_{v}.png", base=dalle,
                                                                         joint_c=joint)
    tex["grille"], _ = TS.grille(commun / "grille.png")
    if route_seule:
        tex["macro_enrobe"], stats["macro_enrobe"] = TS.macro_enrobe(commun / "macro_enrobe_sobre.png", reprises=10,
                                                                     fissures=24, sobre=True)
        tex["sol_neutre"], stats["sol_neutre"] = TS.sol_neutre(commun / "sol_neutre.png", SOL_NEUTRE)
        tex["joints_beton"], stats["joints_beton"] = TS.joints_beton(commun / "joints_beton.png")
    else:
        tex["ecorce"] = TS.ecorce(commun / "ecorce_v2.png")
        tex["montagne"] = TS.montagne(commun / "montagne.png")
        tex["macro_enrobe"], stats["macro_enrobe"] = TS.macro_enrobe(commun / "macro_enrobe.png")
        tex["macro_herbe"], stats["macro_herbe"] = TS.macro_herbe(commun / "macro_herbe.png")
        for g in ("touffes", "plaques"):
            tex[f"meso_herbe_{g}"], stats[f"meso_herbe_{g}"] = TS.meso_herbe(commun / f"meso_herbe_{g}.png", g)
    for c in TS.COUVERTURE_USURE:
        tex[f"masque_u{c}"], stats[f"masque_u{c}"] = TS.masque_usure(commun / f"masque_usure_u{c}_2048.png", c, cote=2048)
    for mid, (lib, src, cible, contraste, chroma, *_r) in sols(route_seule).items():
        base = RL.LIB_ROUTE if lib == "route" else RL.LIB_SITE
        f = base / src / "textures" / f"{src}_albedo.jpg"
        suffixe = "_sobre" if route_seule and mid in SOLS_ROUTE_SEULE else ""
        if f.exists():
            tex[f"sol_{mid}"], stats[mid] = TS.detail_recolore(f, commun / f"sol_{mid}{suffixe}.jpg", cible, cote=2048,
                                                               contraste=contraste, chroma=chroma)
    for (asset, sai) in sorted(saisons_essences):
        fi = DC.fiche(asset)
        coul = fi["automne"] if sai == "automne" else fi["ete"]
        tex[f"feuillage_{asset}_{sai}"] = TS.feuilles(commun / f"feuilles_{asset}_{sai}.png", coul,
                                                      graine=7 + sum(map(ord, asset)) % 101)
    return tex, stats


def _tuile_bib(lib, nom):
    base = RL.LIB_ROUTE if lib == "route" else RL.LIB_SITE
    try:
        return float(json.loads((base / nom / "meta.json").read_text(encoding="utf-8")).get("tile_m", 2.0))
    except (OSError, ValueError):
        return 2.0


def creer_looks(stage, ids, tex, racine="/Looks", route_seule=False, scene=""):
    """Un matériau par materiau_id (aspect de rendu) ; renvoie ({id: Material}, {id: source}). Identifiants propres
    au rendu : « invisible » (abords non rendus à l'étape 1 : opacité 0), « peinture_..._passage » (bandes de passage
    piéton un peu grisées)."""
    from pxr import Gf, Sdf, UsdShade
    liaisons, sources = {}, {}
    table = sols(route_seule)
    dec = decalage_scene(scene) if scene else (0.0, 0.0)
    dec_m = tuple(round((x / 64.0 * TUILE_MASQUE) % TUILE_MASQUE / TUILE_MASQUE, 4) for x in dec)
    coord = "route" if route_seule else "monde"
    for mid in sorted(ids):
        nom = "".join(c if c.isalnum() else "_" for c in mid)
        chemin = f"{racine}/{nom}"
        if mid == "invisible":
            m = UsdShade.Material.Define(stage, chemin)
            sh = UsdShade.Shader.Define(stage, chemin + "/Surface")
            sh.CreateIdAttr("UsdPreviewSurface")
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.5, 0.5, 0.5))
            sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.0)
            sh.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
            m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
            src = "rendu : opacité 0 (faces non rendues : abords du modèle hors de l'emprise de la route, étape 1)"
        elif mid.startswith("peinture_"):
            base_mid = mid[:-len("_passage")] if mid.endswith("_passage") else mid
            m, src = _peinture(stage, chemin, base_mid, tex["peinture_albedo"],
                               {c: tex[f"masque_u{c}"] for c in TS.COUVERTURE_USURE if f"masque_u{c}" in tex},
                               gain=GRIS_PASSAGE if mid.endswith("_passage") else 1.0, decalage_masque=dec_m)
            src += f" ; masque décalé de {list(dec_m)} (scène)"
        elif mid in table and f"sol_{mid}" in tex:
            lib, nb, cible, _c, _ch, macro, amp, ech, rug = table[mid]
            tuile = _tuile_bib(lib, nb)
            mac = tex.get(f"macro_{macro}") if macro else None
            meso = [(tex[t], tu) for t, tu in (JOINTS.get(mid, ()) if route_seule else MESO.get(mid, ())) if t in tex]
            m = _look_sol(stage, chemin, tex[f"sol_{mid}"], tuile, mac, 64.0, amp, ech, rug, meso=meso, coord=coord,
                          decalage=dec)
            src = (f"MaterialX : détail {lib}:{nb} recoloré (albédo visé {cible}, tuile {tuile} m)"
                   + f" ; coordonnées {'(s, t) de la route' if coord == 'route' else '(x, y) du monde'} + décalage {list(dec)}"
                   + (f" × macro {Path(mac).name} (64 m)" if mac else "")
                   + "".join(f" × méso {Path(f).name} ({tu} m)" for f, tu in meso)
                   + f" × (1 + {amp} fractal 3D / {ech} m)")
        elif mid.startswith("feuillage_") and mid in tex:
            m = _materiau_texture(stage, chemin, tex[mid], 0.85, True, tuile=1.0, varname="st")
            src = f"procédural : {Path(tex[mid]).name} (couleur de l'essence, assets/specs/vegetation.json)"
        elif mid in GENERES:
            t, rug, alpha, tu, tv, var = GENERES[mid]
            m = _materiau_texture(stage, chemin, tex[t], rug, alpha, tuile=(tu, tv), varname=var)
            src = f"procédural : {Path(tex[t]).name} (tuile {tu} × {tv} m, {var})"
        else:
            lib, nom_bib = LOOKS.get(mid, (None, mid))
            f = _fichier_bib(lib, nom_bib) if lib else (_fichier_bib("route", mid) or _fichier_bib("site", mid))
            if f is None:
                f = _fichier_bib("site", "enrobe_trottoir")
                src = f"repli : {f.relative_to(DEPOT).as_posix()} (materiau_id sans fichier)"
            else:
                src = f.relative_to(DEPOT).as_posix()
            m = UsdShade.Material.Define(stage, chemin)
            m.GetPrim().GetReferences().AddReference(f.as_posix())
            if f.stem in RL.INVERSER_RUGOSITE:
                rug = stage.OverridePrim(chemin + "/Rugosite")
                rug.CreateAttribute("inputs:scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 1))
                rug.CreateAttribute("inputs:bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(1, 1, 1, 0))
                src += " (rugosité inversée au rendu)"
            if mid in ECHELLE_ALBEDO:
                k = ECHELLE_ALBEDO[mid]
                k3 = tuple(k) if isinstance(k, (tuple, list)) else (k, k, k)
                alb = stage.OverridePrim(chemin + "/Albedo")
                alb.CreateAttribute("inputs:scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(k3[0], k3[1], k3[2], 1))
                src += f" (albédo × {list(k3) if len(set(k3)) > 1 else k3[0]} par canal)"
            if mid in ATTENUER_NORMALE and stage.GetPrimAtPath(chemin + "/Normale"):
                a = ATTENUER_NORMALE[mid]
                nm = stage.OverridePrim(chemin + "/Normale")
                nm.CreateAttribute("inputs:scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2 * a, 2 * a, 2, 1))
                nm.CreateAttribute("inputs:bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-a, -a, -1, 0))
                src += f" (relief des normales × {a})"
        liaisons[mid] = UsdShade.Material(stage.GetPrimAtPath(chemin))
        sources[mid] = src
    return liaisons, sources


def uv_secours(prim):
    """Maillage sans coordonnées de texture : primvars st et st1 = (x, y) en mètres, par sommet (projection de
    dessus), écrites dans la couche de rendu seulement."""
    from pxr import Sdf, UsdGeom, Vt, Gf
    pv = UsdGeom.PrimvarsAPI(prim)
    if pv.HasPrimvar("st1"):
        return False
    pts = UsdGeom.Mesh(prim).GetPointsAttr().Get()
    uv = Vt.Vec2fArray([Gf.Vec2f(p[0], p[1]) for p in pts])
    for nom in ("st", "st1"):
        pv.CreatePrimvar(nom, Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(uv)
    return True


def ecrire_instances(stage, chemin, protos, gpos, liaisons):
    """Arbres en PointInstancer : prototypes v0, v1, v2 (maillages Z haut, double face) ; une instance par point
    (position, lacet autour de Z, échelle, prototype = variante)."""
    from pxr import Gf, UsdGeom, Vt
    inst = UsdGeom.PointInstancer.Define(stage, chemin)
    UsdGeom.Scope.Define(stage, chemin + "/Prototypes")
    cibles = []
    for v in ("v0", "v1", "v2"):
        pc = f"{chemin}/Prototypes/{v}"
        RL.ecrire_couche(stage, pc, protos[v], liaisons)
        for mid in protos[v]:
            UsdGeom.Mesh(stage.GetPrimAtPath(pc + "/" + "".join(c if c.isalnum() else "_" for c in mid))
                         ).CreateDoubleSidedAttr(True)
        cibles.append(stage.GetPrimAtPath(pc).GetPath())
    inst.CreatePrototypesRel().SetTargets(cibles)
    pos, rot, ech, idx = [], [], [], []
    for p in gpos.points():
        P = p.position()
        pos.append(Gf.Vec3f(P[0], -P[2], P[1]))
        a = 0.5 * float(p.attribValue("lacet"))
        rot.append(Gf.Quath(math.cos(a), 0.0, 0.0, math.sin(a)))       # lacet Houdini (Y) = lacet autour de Z
        e = float(p.attribValue("pscale"))
        ech.append(Gf.Vec3f(e, e, e))
        idx.append(int(p.attribValue("variante")[1:]))
    inst.CreatePositionsAttr(Vt.Vec3fArray(pos))
    inst.CreateOrientationsAttr(Vt.QuathArray(rot))
    inst.CreateScalesAttr(Vt.Vec3fArray(ech))
    inst.CreateProtoIndicesAttr(Vt.IntArray(idx))
    return len(idx)


def _materiau_de(prim):
    from pxr import UsdShade
    b = UsdShade.MaterialBindingAPI(prim).GetDirectBinding()
    p = b.GetMaterialPath()
    return p.name if p else ""


def texture_m1(stage):
    """Critère M1 : chaque maillage (Mesh) lié à un matériau dont la couleur diffuse vient d'une texture : en
    UsdPreviewSurface (diffuseColor <- UsdUVTexture, primvar lue présente) ou en MaterialX (base_color <- ND_image_*,
    coordonnées = position du monde : aucune primvar nécessaire). Renvoie (texturés, total, liste des non texturés)."""
    from pxr import Usd, UsdGeom, UsdShade
    ok, tot, nok = 0, 0, []
    for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        im = UsdGeom.Imageable(prim)
        if im.ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        tot += 1
        mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        texture, varname, mtlx = False, None, False
        if mat:
            for p in Usd.PrimRange(mat.GetPrim()):
                sh = UsdShade.Shader(p)
                if not sh:
                    continue
                ident = sh.GetIdAttr().Get() or ""
                if ident == "UsdPreviewSurface":
                    inp = sh.GetInput("diffuseColor")
                    if inp and inp.HasConnectedSource():
                        src = inp.GetConnectedSource()[0]
                        texture = UsdShade.Shader(src.GetPrim()).GetIdAttr().Get() == "UsdUVTexture"
                elif ident == "UsdPrimvarReader_float2":
                    varname = sh.GetInput("varname").Get()
                elif ident.startswith("ND_image_color"):
                    mtlx = True
            if mtlx:
                texture = True
        pv = UsdGeom.PrimvarsAPI(prim)
        a_uv = mtlx or (varname is not None and pv.HasPrimvar(varname))
        if texture and a_uv:
            ok += 1
        else:
            nok.append(f"{prim.GetPath()} ({'sans texture' if not texture else 'sans ' + str(varname)})")
    return ok, tot, nok


# ------------------------------------------------------------------------------------------- caméras
def _camera(stage, nom, oeil, cible, focale, res):
    from pxr import Gf, UsdGeom
    cam = UsdGeom.Camera.Define(stage, f"/Cameras/{nom}")
    W, H = res
    cam.CreateFocalLengthAttr(focale)
    cam.CreateHorizontalApertureAttr(36.0)
    cam.CreateVerticalApertureAttr(36.0 * H / W)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, CLIP_LOIN))
    m4 = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*oeil), Gf.Vec3d(*cible), Gf.Vec3d(0, 0, 1)).GetInverse()
    UsdGeom.Xformable(cam).AddTransformOp().Set(m4)


def camera_photo(stage, nom, oeil, lacet_deg, tangage_deg, fov_deg, res):
    """Caméra au champ et au tangage d'une tuile de photo (decoupe.py equirect : fov_deg, tangage_deg) : œil (x, y, z),
    lacet = cap de visée depuis +x (sens trigonométrique)."""
    from pxr import Gf, UsdGeom
    cam = UsdGeom.Camera.Define(stage, f"/Cameras/{nom}")
    W, H = res
    f = 18.0 / math.tan(math.radians(fov_deg) / 2.0)
    cam.CreateFocalLengthAttr(f)
    cam.CreateHorizontalApertureAttr(36.0)
    cam.CreateVerticalApertureAttr(36.0 * H / W)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, CLIP_LOIN))
    la, ta = math.radians(lacet_deg), math.radians(tangage_deg)
    d = Gf.Vec3d(math.cos(ta) * math.cos(la), math.cos(ta) * math.sin(la), math.sin(ta))
    m4 = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*oeil), Gf.Vec3d(*oeil) + d, Gf.Vec3d(0, 0, 1)).GetInverse()
    UsdGeom.Xformable(cam).AddTransformOp().Set(m4)


def _dessus(stage, centre, z, largeur, res):
    """Vue de dessus quasi orthographique (perspective depuis 2 000 m : la caméra orthographique de Karma XPU 22.0.459
    ne lance aucun rayon, rapport L2)."""
    from pxr import Gf, UsdGeom
    alt = 2000.0
    cam = UsdGeom.Camera.Define(stage, "/Cameras/dessus")
    cam.CreateProjectionAttr(UsdGeom.Tokens.perspective)
    cam.CreateHorizontalApertureAttr(36.0)
    cam.CreateVerticalApertureAttr(36.0 * res[1] / res[0])
    cam.CreateFocalLengthAttr(36.0 * alt / largeur)
    cam.CreateClippingRangeAttr(Gf.Vec2f(alt - 200.0, alt + 200.0))
    UsdGeom.Xformable(cam).AddTranslateOp().Set(Gf.Vec3d(centre[0], centre[1], z + alt))
    return {"quasi_orthographique": True, "altitude_m": alt, "largeur_m": largeur, "m_par_px": round(largeur / res[0], 4),
            "centre_xy": [round(float(centre[0]), 4), round(float(centre[1]), 4)], "z_sol": round(float(z), 4)}


def lumieres(stage, ciel_exr, ciel_fond=None, sol_sans_ombre=None):
    """Soleil (DistantLight normalisée), ciel (dôme éclairant) et fond (dôme vu). sol_sans_ombre (étape 1, chemin du sol
    plat neutre) : le sol de présentation est éclairé par un soleil et un ciel identiques, liés à lui seul et sans
    ombre portée (liens de lumière et d'ombre UsdLux, Karma XPU) ; soleil et ciel principaux l'excluent. Correction
    après le second contrôle : la route, posée sur son socle au-dessus du sol plat, y portait au nord un trait d'ombre de
    4 à 8 px en vue de dessus (luminance 0,12-0,16) qui soulignait le bord du profil ; l'éclairage est inchangé."""
    from pxr import Gf, Sdf, UsdGeom, UsdLux
    e, a = math.radians(SOLEIL_ELEVATION), math.radians(SOLEIL_AZIMUT)
    d = Gf.Vec3d(math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))
    m = Gf.Matrix4d().SetLookAt(d, Gf.Vec3d(0, 0, 0), Gf.Vec3d(0, 0, 1)).GetInverse()
    m.SetTranslateOnly(Gf.Vec3d(0, 0, 0))
    soleils = [("Soleil", None)] + ([("Soleil_sol", sol_sans_ombre)] if sol_sans_ombre else [])
    for nom, seul in soleils:
        sun = UsdLux.DistantLight.Define(stage, f"/Lumieres/{nom}")
        sun.CreateIntensityAttr(SOLEIL)
        sun.CreateAngleAttr(0.53)
        sun.CreateNormalizeAttr(True)            # Karma / USD 26 : sans normalisation, éclairage 15 000 fois trop faible
        sun.CreateColorAttr(Gf.Vec3f(1.0, 0.955, 0.89))
        UsdGeom.Xformable(sun).AddTransformOp().Set(m)
        _lier(sun.GetPrim(), seul, sol_sans_ombre)
    domes = [("Ciel", 1.0, False, ciel_exr, None), ("Ciel_fond", CIEL_FOND, True, ciel_fond or ciel_exr, None)]
    if sol_sans_ombre:
        domes.insert(1, ("Ciel_sol", 1.0, False, ciel_exr, sol_sans_ombre))
    for nom, inten, visible, tex, seul in domes:
        dome = UsdLux.DomeLight.Define(stage, f"/Lumieres/{nom}")
        dome.CreateIntensityAttr(inten)
        UsdGeom.Xformable(dome).AddRotateXOp().Set(90.0)
        dome.CreateTextureFileAttr(Sdf.AssetPath(Path(tex).name))
        dome.CreateTextureFormatAttr(UsdLux.Tokens.latlong)
        dome.GetPrim().CreateAttribute("karma:light:renderlightgeo", Sdf.ValueTypeNames.Bool).Set(visible)
        if visible:
            dome.CreateDiffuseAttr(0.0)
            dome.CreateSpecularAttr(0.0)
        elif nom == "Ciel":
            _lier(dome.GetPrim(), None, sol_sans_ombre)
        else:
            _lier(dome.GetPrim(), seul, sol_sans_ombre)


def _lier(prim, seul, sol):
    """Liens UsdLux : seul = chemin -> la lumière n'éclaire que ce chemin et aucune géométrie n'y porte d'ombre ;
    seul = None et sol donné -> la lumière éclaire tout sauf le sol."""
    from pxr import Sdf, UsdLux
    if not sol:
        return
    api = UsdLux.LightAPI(prim)
    lien = api.GetLightLinkCollectionAPI()
    if seul:
        lien.CreateIncludeRootAttr(False)
        lien.CreateIncludesRel().AddTarget(Sdf.Path(seul))
        api.GetShadowLinkCollectionAPI().CreateIncludeRootAttr(False)
    else:
        lien.CreateExcludesRel().AddTarget(Sdf.Path(sol))


def exposition():
    """Exposition fixe : albédo 1 sous le soleil (hauteur SOLEIL_ELEVATION) et le ciel -> EXPO_GAIN."""
    e = SOLEIL * math.sin(math.radians(SOLEIL_ELEVATION)) * (1.0 + PART_CIEL)
    return math.pi / e * EXPO_GAIN


# ------------------------------------------------------------------------------------------- rendu et mesures
def developper(exr, png, expo):
    """EXR linéaire -> PNG sRGB : exposition fixe, épaule douce au-dessus de 0,8 (pas de saturation brutale)."""
    import OpenImageIO as oiio
    from PIL import Image
    buf = oiio.ImageBuf(str(exr))
    a = buf.get_pixels(oiio.FLOAT)[..., :3] * expo
    ep = 0.80
    y = np.where(a <= ep, a, ep + (1 - ep) * (1 - np.exp(-(a - ep) / (1 - ep))))
    v = RL.srgb(y)
    v = np.clip(v - CONTRASTE / (2 * math.pi) * np.sin(2 * math.pi * v), 0.0, 1.0)
    Image.fromarray((v * 255 + 0.5).astype(np.uint8)).save(png)


def dynamique(png):
    """Critère L1 : luminance (Rec. 709) des valeurs sRGB normalisées ; p1, p50, p99 et p99 − p1."""
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255.0
    Y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    p1, p50, p99 = np.percentile(Y, [1, 50, 99])
    return {"p1": round(float(p1), 4), "p50": round(float(p50), 4), "p99": round(float(p99), 4),
            "dynamique": round(float(p99 - p1), 4)}


def rendre(usd, cameras, dossier, limite_s=200, echantillons=None):
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    tmp = Path(dossier) / "_exr"
    tmp.mkdir(parents=True, exist_ok=True)
    out = {}
    for nom, res in cameras.items():
        exr = tmp / f"{nom}.exr"
        cmd = [RL.husk(), "-R", "BRAY_HdKarmaXPU", "--engine", "xpu", "--settings", "/Render/reglages", "--camera",
               f"/Cameras/{nom}", "--res", str(res[0]), str(res[1]), "--frame", "1", "-p", str(echantillons or ECHANTILLONS),
               "--output", exr.as_posix(), "--make-output-path", "--timelimit", str(limite_s), "--verbose", "1",
               Path(usd).as_posix()]
        for essai in range(2):                       # husk peut échouer sans message (pilote GPU) : un nouvel essai
            r = subprocess.run(cmd, env=env, cwd=str(Path(usd).parent), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=limite_s + 300)
            if r.returncode == 0 and exr.exists():
                break
        if r.returncode != 0 or not exr.exists():
            raise RuntimeError(f"rendu {nom} en échec (code {r.returncode}) : {r.stdout[-1500:]} {r.stderr[-1500:]}")
        png = Path(dossier) / f"{nom}.png"
        developper(exr, png, exposition())
        exr.unlink()
        out[nom] = png
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def _cuire(n, quoi):
    """Cuisson d'un nœud du décor ; erreur explicite (jamais de décor manquant en silence)."""
    try:
        n.cook(force=True)
    except hou.OperationFailed:
        pass
    err = [f"{c.path()} : {e}" for c in (n,) + tuple(n.inputAncestors()) for e in c.errors()]
    if err:
        raise RuntimeError(f"décor {quoi} : " + " | ".join(err[:6]))
    return n.geometry()


def _sortie(parent, noeud, k, nom=None):
    nom = nom or f"{noeud.name()}_sortie_{k}"
    n = parent.node(nom) or parent.createNode("null", nom)
    n.setInput(0, noeud, k)
    return n


def mesurer_arbre(geo, spec):
    """Dimensions d'un prototype d'arbre construit (Y haut, pied à l'origine) : cartes de feuilles (côté), plus bas
    point des feuilles et des branches (hors tronc), rayon horizontal et hauteur maximaux."""
    P = np.array(geo.pointFloatAttribValues("P")).reshape(-1, 3)
    cotes, ybas_f, rad_f, ybas_b, haut = [], 1e9, 0.0, 1e9, 0.0
    r0 = spec["rayon_tronc"]
    for pr in geo.prims():
        idx = [v.point().number() for v in pr.vertices()]
        Q = P[idx]
        mid = pr.attribValue("materiau_id")
        haut = max(haut, float(Q[:, 1].max()))
        if mid.startswith("feuillage"):
            cotes.append(float(np.linalg.norm(Q[1] - Q[0])))
            ybas_f = min(ybas_f, float(Q[:, 1].min()))
            rad_f = max(rad_f, float(np.hypot(Q[:, 0], Q[:, 2]).max()))
        else:
            c = Q.mean(axis=0)
            if math.hypot(c[0], c[2]) > 3.0 * r0 + 0.1:          # branche (hors du tronc)
                ybas_b = min(ybas_b, float(Q[:, 1].min()))
    return {"cartes": len(cotes), "carte_min_m": round(min(cotes), 4) if cotes else None,
            "carte_max_m": round(max(cotes), 4) if cotes else None,
            "feuilles_bas_m": round(ybas_f, 3) if cotes else None, "branches_bas_m": round(ybas_b, 3),
            "rayon_feuillage_m": round(rad_f, 3), "hauteur_m": round(haut, 3)}


# caméras calées sur les tuiles des photos de comparaison (scènes de Meylan) : scène -> [(nom, s, t, h, lacet relatif à
# la tangente de la référence (°, sens trigonométrique), tangage (°), champ (°), résolution)] ; champ et tangage des
# tuiles de decoupe.py equirect (68,25° ; − 12° pour les vues « vise ») ; hauteur de la caméra Panoramax ≈ 2 m
# (dossier 13) ; position estimée sur la photo (rapport § 4)
VUES_PHOTO = {
    # M24 : f877235a (photographe sur la piste du côté droit, 7 m avant le passage, regard vers le passage et l'îlot) ;
    # 9badc00e (sur le trottoir droit au bord du passage, regard en travers de la chaussée)
    "S_M24": [("photo_f877235a", 33.0, -8.4, 2.0, 40.0, -12.0, 68.25, (1092, 1092)),
              ("photo_9badc00e", 38.0, -5.6, 2.0, 80.0, -12.0, 68.25, (1092, 1092))],
    # M27 : 176f9ab0 (caméra sur le toit d'une voiture dans la voie de droite, 20 m avant le passage)
    "S_M27": [("photo_176f9ab0", 25.0, -3.0, 2.0, 6.0, -12.0, 68.25, (1092, 1092))],
    # M20 : 30b80a7b (caméra sur le toit d'une voiture dans la voie de droite, 25 m avant le passage)
    "S_M20": [("photo_30b80a7b", 5.0, -1.5, 2.0, 2.0, -12.0, 68.25, (1092, 1092))],
}


def faces_par_materiau(geo, garder):
    """Indices de faces, dans chaque maillage USD écrit par rendre_l2.maillages (une face par primitive d'au moins 3
    sommets, regroupées par materiau_id dans l'ordre des primitives), des primitives pour lesquelles garder(pr) est
    vrai : {materiau_id: [indices]}."""
    cpt, out = {}, {}
    for pr in geo.prims():
        if len(pr.vertices()) < 3:
            continue
        try:
            mid = pr.attribValue("materiau_id") or "PJ_Neutre"
        except Exception:  # noqa: BLE001
            mid = "PJ_Neutre"
        k = cpt.get(mid, 0)
        cpt[mid] = k + 1
        if garder(pr):
            out.setdefault(mid, []).append(k)
    return out


def lier_sous_ensemble(stage, chemin_maillage, nom, indices, materiau):
    """GeomSubset de faces (famille materialBind) sous un maillage référencé, lié à un matériau du rendu : la couche
    fabriquée (l2/route_l2.usda, l2b/route_l2b.usda) n'est pas modifiée."""
    from pxr import UsdGeom, UsdShade, Vt
    prim = stage.GetPrimAtPath(chemin_maillage)
    if not prim or not indices:
        return 0
    mesh = UsdGeom.Mesh(prim)
    sub = UsdGeom.Subset.CreateGeomSubset(mesh, nom, UsdGeom.Tokens.face, Vt.IntArray(indices), "materialBind",
                                          UsdGeom.Tokens.nonOverlapping)
    UsdShade.MaterialBindingAPI.Apply(sub.GetPrim())
    UsdShade.MaterialBindingAPI(sub.GetPrim()).Bind(materiau)
    return len(indices)


def _nom_usd(mid):
    return "".join(c if c.isalnum() else "_" for c in mid)


def st_route(stage, sol, chemin="/Monde/Sol"):
    """Primvar st_route = (s, t) de la route (m), par sommet de face, sur les maillages du sol fabriqué (opinion du
    rendu : la couche l2/route_l2.usda n'est pas modifiée) ; même ordre que rendre_l2.maillages (faces d'au moins
    3 sommets, regroupées par materiau_id). Les cartes d'usure et les joints des sols y sont lus (étape 1)."""
    from pxr import Gf, Sdf, UsdGeom, Vt
    S = sol.pointFloatAttribValues("s")
    T = sol.pointFloatAttribValues("t")
    par = {}
    for pr in sol.prims():
        vs = pr.vertices()
        if len(vs) < 3:
            continue
        try:
            mid = pr.attribValue("materiau_id") or "PJ_Neutre"
        except Exception:  # noqa: BLE001
            mid = "PJ_Neutre"
        lst = par.setdefault(mid, [])
        for v in vs:
            n = v.point().number()
            lst.append(Gf.Vec2f(S[n], T[n]))
    out = {}
    for mid, lst in sorted(par.items()):
        prim = stage.GetPrimAtPath(f"{chemin}/{_nom_usd(mid)}")
        if not prim:
            continue
        n_fv = len(UsdGeom.Mesh(prim).GetFaceVertexIndicesAttr().Get() or [])
        if n_fv != len(lst):
            raise RuntimeError(f"st_route : {mid} : {len(lst)} sommets de face pour {n_fv} dans le maillage USD")
        UsdGeom.PrimvarsAPI(prim).CreatePrimvar("st_route", Sdf.ValueTypeNames.TexCoord2fArray,
                                                UsdGeom.Tokens.faceVarying).Set(Vt.Vec2fArray(lst))
        out[mid] = n_fv
    return out


def _cap_route(route, s):
    i = int(np.clip(np.searchsorted(route.s, s, side="right") - 1, 0, len(route.s) - 2))
    d = route.P[i + 1] - route.P[i]
    return math.degrees(math.atan2(d[1], d[0]))


def rendre_scene(noeuds_l2, noeuds_l2b, scene, dossier_scene, parent, vues=None, decor_etape2=False, seulement=None,
                 echantillons=None):
    """Rendus d'une scène. decor_etape2 = False (défaut, étape 1) : route seule sur son socle (voir l'en-tête) ; True :
    décor de l'étape 2 (arbres, prolongements, sol de décor, relief, nuages). seulement : liste de caméras (essais)."""
    from pxr import Gf, Usd, UsdGeom, UsdRender, UsdShade
    import planches as PL
    t0 = time.time()
    route_seule = not decor_etape2
    dossier_scene = Path(dossier_scene).resolve()
    d = dossier_scene / "rendus"
    if d.exists():                                   # rendus précédents (dont ceux du lot L2) remplacés
        for f in d.glob("*.png"):
            f.unlink()
        shutil.rmtree(d / "tuiles", ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    commun = Path(dossier_scene).parent / "_rendu_commun" / "textures"
    try:                                              # modèle fabriqué (chemin noté par le lot L1)
        cc = json.loads((Path(dossier_scene) / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
        f_mod = Path(cc["modele"]["fichier"])
        modele = json.loads((f_mod if f_mod.is_absolute() else DEPOT / f_mod).read_text(encoding="utf-8"))
    except (OSError, KeyError, ValueError):
        modele = {}
    sai = DC.saison((modele.get("meta") or {}).get("date"))
    routes = modele.get("routes") or [{}]
    rural = routes[0].get("agglomeration") is False
    sol = noeuds_l2["sol"].geometry(0)
    graphe = noeuds_l2["sol"].inputs()[0]
    route = Route(graphe.geometry())
    T = np.array(sol.pointFloatAttribValues("t"))
    tmax, tmin = float(T.max()), float(T.min())
    if route_seule:                                  # emprise de la route : abords du modèle exclus (non rendus)
        # (murs exclus aussi : une marche entre deux abords de sections voisines s'étend hors de l'emprise)
        pts = {v.point().number() for pr, c in zip(sol.prims(), sol.primStringAttribValues("classe"))
               if c not in ("abord", "mur") for v in pr.vertices()}
        Tr = T[sorted(pts)]
        tmax, tmin = float(Tr.max()), float(Tr.min())
    sol_n = _sortie(parent, noeuds_l2["sol"], 0, "sol_fabrique_rendu")
    if route_seule:
        # ---- étape 1 : socle (jupe sous la limite extérieure du profil et aux deux bouts) et sol plat neutre
        z_socle = socle_niveau(sol)
        jupe = DC.socle_jupe(parent, sol_n, z_socle, t_route=(tmin, tmax))
        xm, ym = route.xy(route.L / 2, 0.5 * (tmax + tmin))
        plat = DC.sol_plat(parent, (float(xm), z_socle, float(-ym)), z_socle)
        decor = {"Socle_jupe": _cuire(jupe, "jupe du socle"), "Socle_sol": _cuire(plat, "sol plat"), "z_socle": z_socle}
        groupes = []
        mg = md = None
    else:
        # ---- décor de l'étape 2 : prolongements, sol de décor (matériau des abords), fond de relief
        bor_n = _sortie(parent, noeuds_l2["bordures"], 0, "bordures_rendu")
        can_n = _sortie(parent, noeuds_l2["caniveaux"], 0, "caniveaux_rendu")
        prol = DC.prolongements(parent, sol_n, bor_n, can_n, graphe)
        mg, md = materiaux_abords(sol)
        sol_dec = DC.sol_decor(parent, sol_n, graphe, prol, mg, md)
        xm, ym = route.xy(route.L / 2, 0.0)
        mont = DC.montagnes(parent, (float(xm), 0.0, float(-ym)))
        groupes = decor_arbres(parent, noeuds_l2, sol_n, sol_dec, route, scene, tmax, tmin, rural, sai, graphe)
        decor = {"Sol": _cuire(sol_dec, "sol de décor"), "Prolongements": _cuire(prol, "prolongements"),
                 "Montagnes": _cuire(mont, "fond de relief")}
    bandes = bandes_t(sol, SUJET.get(scene, route.L / 2))
    # ---- scène USD
    usd = d / "scene_rendu.usda"
    if usd.exists():
        usd.unlink()
    stage = Usd.Stage.CreateNew(str(usd))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    monde = stage.DefinePrim("/Monde", "Xform")
    refs = monde.GetReferences()
    refs.AddReference("../l2/route_l2.usda")
    if (Path(dossier_scene) / "l2b" / "route_l2b.usda").exists():
        refs.AddReference("../l2b/route_l2b.usda")
    dec_m = {k: RL.maillages(g, k) for k, g in decor.items() if isinstance(g, hou.Geometry) and len(g.prims())}
    instances, mesures_arbres = mesurer_groupes(groupes, sai)
    ids = set()
    maill = []
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            mid = _materiau_de(prim)
            maill.append((prim, mid))
            ids.add(mid)
    ids_dec = set()
    for v in dec_m.values():
        ids_dec |= set(v)
    for protos, _ in instances.values():
        for v in protos.values():
            ids_dec |= set(v)
    # sous-ensembles du rendu : abords du modèle non rendus (étape 1), bandes de passage un peu grisées
    sous = {}
    if route_seule:
        def hors_emprise(pr):
            """Abord du modèle, ou mur entièrement hors de l'emprise de la route (marche entre deux abords)."""
            c = pr.attribValue("classe")
            if c == "abord":
                return True
            if c != "mur":
                return False
            tc = float(np.mean(T[[v.point().number() for v in pr.vertices()]]))
            return tc > tmax + 1e-3 or tc < tmin - 1e-3
        sous["abords"] = ("/Monde/Sol", faces_par_materiau(sol, hors_emprise), lambda mid: "invisible")
    gbev = noeuds_l2["sol"].geometry(1)
    if len(gbev.prims()) and gbev.findPrimAttrib("materiau_voisin"):
        # BEV en contraste avec son revêtement voisin (RF-MA-OBS-003 ; correction après le second contrôle)
        for v in BEV_TEINTES:
            sous[f"bev_{v}"] = ("/Monde/BEV", faces_par_materiau(gbev, lambda pr, v=v: variante_bev(
                pr.attribValue("materiau_voisin")) == v), lambda mid, v=v: f"{mid}_{v}")
    gp = noeuds_l2b["peinture"].geometry() if noeuds_l2b and "peinture" in noeuds_l2b else None
    if gp is not None and len(gp.prims()):
        sous["passages"] = ("/Monde/Marquages", faces_par_materiau(gp, lambda pr: pr.attribValue("classe") == "passage"),
                            lambda mid: mid + "_passage")
    for _k, (_c, par_mid, f_mat) in sous.items():
        ids_dec |= {f_mat(m) for m in par_mid}
    ess = {(m.split("_", 1)[1].rsplit("_", 1)[0], sai) for m in ids_dec if m.startswith("feuillage_")}
    tex, stats_tex = textures_rendu(commun, ess, route_seule=route_seule)
    liaisons, sources = creer_looks(stage, ids | ids_dec, tex, route_seule=route_seule, scene=scene)
    st_ecrits = st_route(stage, sol) if route_seule else {}
    for prim, mid in maill:
        UsdShade.MaterialBindingAPI.Apply(prim)
        UsdShade.MaterialBindingAPI(prim).Bind(liaisons[mid])
        uv_secours(prim)
    faces_sous = {}
    for k, (chemin, par_mid, f_mat) in sous.items():
        for mid, idx in sorted(par_mid.items()):
            n = lier_sous_ensemble(stage, f"{chemin}/{_nom_usd(mid)}", f"rendu_{k}", idx, liaisons[f_mat(mid)])
            faces_sous[f"{k}/{mid}"] = n
    for k, v in dec_m.items():
        RL.ecrire_couche(stage, f"/Decor/{k}", v, liaisons)
        for mid in v:
            UsdGeom.Mesh(stage.GetPrimAtPath(f"/Decor/{k}/" + _nom_usd(mid))).CreateDoubleSidedAttr(True)
    for k, (protos, gpos) in instances.items():
        ecrire_instances(stage, f"/Decor/{k}", protos, gpos, liaisons)
    # ---- ciel et soleil
    ciel = d / "ciel.exr"
    ciel_fond = None
    if route_seule:
        # ciel clair sans nuage ; voile d'horizon blanc bleuté (le modèle de Preetham y est rosé) ; le fond vu sous
        # l'horizon (au-delà du sol plat) a la radiance du sol neutre : aucune bande entre le sol et le ciel
        info_ciel = CI.ciel_exr(ciel, SOLEIL_ELEVATION, SOLEIL_AZIMUT, TURBIDITE, PART_CIEL, SOLEIL, nuages=0.0,
                                voile=0.92, teinte_voile=VOILE_ROUTE_SEULE)
        e_tot = SOLEIL * math.sin(math.radians(SOLEIL_ELEVATION)) * (1.0 + PART_CIEL)
        l_sol = [c * e_tot / math.pi / CIEL_FOND * t for c, t in zip(SOL_NEUTRE, (0.985, 0.965, 0.93))]
        ciel_fond = d / "ciel_fond.exr"
        CI.ciel_exr(ciel_fond, SOLEIL_ELEVATION, SOLEIL_AZIMUT, TURBIDITE, PART_CIEL, SOLEIL, nuages=0.0,
                    sol_radiance=l_sol, voile=0.92, teinte_voile=VOILE_ROUTE_SEULE)
    else:
        info_ciel = CI.ciel_exr(ciel, SOLEIL_ELEVATION, SOLEIL_AZIMUT, TURBIDITE, PART_CIEL, SOLEIL)
    lumieres(stage, ciel, ciel_fond, sol_sans_ombre="/Decor/Socle_sol" if route_seule else None)
    return _cameras_et_rendu(stage, usd, monde, d, scene, route, sol, bandes, tmax, tmin, instances, mesures_arbres,
                             vues, seulement, echantillons, dossier_scene, info_ciel, sai, tex, stats_tex, sources, mg,
                             md, route_seule, faces_sous, decor, t0, PL)


def socle_niveau(sol):
    """Niveau du sol plat du socle (étape 1) : 5 cm sous le point le plus bas des surfaces visibles de la route (bandes
    et caniveaux relevés ; ni abords, ni murs, ni sols cachés sous les éléments)."""
    exclus = {"abord", "mur", "sous_bordure", "sous_element", ""}
    P = np.array(sol.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    zmin = 1e9
    for pr, c in zip(sol.prims(), sol.primStringAttribValues("classe")):
        if c in exclus:
            continue
        zmin = min(zmin, min(P[v.point().number(), 1] for v in pr.vertices()))
    return round(float(zmin) - 0.05, 4)


def mesurer_groupes(groupes, sai):
    """Prototypes et positions des groupes d'arbres (étape 2) cuits, mesures des prototypes."""
    instances, mesures_arbres = {}, []
    for nom, proto, pos, spec in groupes:
        gpos = _cuire(pos, f"positions {nom}")
        if not len(gpos.points()):
            continue
        gp = _cuire(proto, f"prototypes {nom}")
        protos = {v: RL.maillages(gp, nom, filtre=lambda pr, v=v: pr.attribValue("name") == v) for v in ("v0", "v1", "v2")}
        instances[nom] = (protos, gpos)
        mes = []
        for v in ("v0", "v1", "v2"):
            g1 = hou.Geometry()
            g1.merge(gp)
            g1.deletePrims([pr for pr in g1.prims() if pr.attribValue("name") != v])
            mes.append(mesurer_arbre(g1, spec))
        mesures_arbres.append({"groupe": nom, "gabarit": spec, "instances": len(gpos.points()), "saison": sai,
                               "prototypes": mes})
    return instances, mesures_arbres


def decor_arbres(parent, noeuds_l2, sol_n, sol_dec, route, scene, tmax, tmin, rural, sai, graphe):
    """Étape 2 : arbres du modèle (un jeu de prototypes par gabarit : essence, hauteur, fût, houppier du modèle) et
    arbres de décor hors emprise (feuillu générique de la fiche)."""
    pts_modele = _sortie(parent, noeuds_l2["vers_entites"], 1)
    gpm = _cuire(pts_modele, "points des arbres du modèle")
    noms_attr = [a.name() for a in gpm.pointAttribs()]
    gabarits = {}
    for p in gpm.points():
        asset = p.attribValue("asset_id") if "asset_id" in noms_attr else ""
        fi = DC.fiche(asset or "arbre_feuillu_generique_moyen")
        H = p.attribValue("hauteur_m") if "hauteur_m" in noms_attr else 0.0
        F = p.attribValue("fut_m") if "fut_m" in noms_attr else 0.0
        R = p.attribValue("houppier_rayon_m") if "houppier_rayon_m" in noms_attr else 0.0
        spec = {"asset": fi["asset"], "hauteur": round(H or fi["hauteur"], 4), "fut": round(F or fi["fut"], 4),
                "houppier": round(R or fi["houppier"], 4), "rayon_tronc": fi["rayon_tronc"],
                "carte_feuilles": fi["carte_feuilles"],
                "source": "modèle (objets_le_long : asset_id, hauteur_m, fut_m, houppier_rayon_m)" if H else "fiche"}
        cle = f"m{len(gabarits)}"
        for k, v in gabarits.items():
            if all(v[x] == spec[x] for x in ("asset", "hauteur", "fut", "houppier")):
                cle = k
                break
        gabarits.setdefault(cle, spec)
    groupes = []
    for cle, spec in sorted(gabarits.items()):
        f = DC._wrangle(parent, f"arbres_modele_{cle}_tri", r"""
if (s@asset_id != chs("asset") || abs(f@hauteur_m - chf("h")) > 1e-3 || abs(f@fut_m - chf("f")) > 1e-3
    || abs(f@houppier_rayon_m - chf("r")) > 1e-3) removepoint(0, @ptnum);
""", "point", pts_modele)
        DC._parms(f, flottants=(("h", spec["hauteur"]), ("f", spec["fut"]), ("r", spec["houppier"])),
                  chaines=(("asset", spec["asset"]),))
        proto = DC.prototypes_arbre(parent, f"modele_{cle}", spec, sai)
        pos = DC.poser(parent, f, sol_n, f"modele_{cle}", True)
        groupes.append((f"Arbres_modele_{cle}", proto, pos, spec))
    # ---- arbres de décor (hors emprise) : feuillu générique de la fiche
    fd = DC.fiche("arbre_feuillu_generique_moyen")
    spec_d = {"asset": fd["asset"], "hauteur": fd["hauteur"], "fut": fd["fut"], "houppier": fd["houppier"],
              "rayon_tronc": fd["rayon_tronc"], "carte_feuilles": fd["carte_feuilles"], "source": "fiche (décor)"}
    nom_dec = "decor_points"
    if parent.node(f"decor_{nom_dec}") is not None:
        for n in [c for c in parent.children() if nom_dec in c.name()]:
            n.destroy()
    pts_dec = DC.points_decor(parent, nom_dec, route.L, tmax, tmin, 3.0, rural, graphe,
                              s_libre=SUJET.get(scene, route.L / 2) - 14.5)
    groupes.append(("Arbres_decor", DC.prototypes_arbre(parent, "decor", spec_d, sai),
                    DC.poser(parent, pts_dec, sol_dec, "decor", False), spec_d))
    return groupes


def _cameras_et_rendu(stage, usd, monde, d, scene, route, sol, bandes, tmax, tmin, instances, mesures_arbres, vues,
                      seulement, echantillons, dossier_scene, info_ciel, sai, tex, stats_tex, sources, mg, md,
                      route_seule, faces_sous, decor, t0, PL):
    from pxr import Gf, UsdRender
    # ---- caméras
    cams, res = {}, {}
    s_f = min(SUJET.get(scene, route.L / 2), route.L - 5)

    def cam(nom, oeil, cible, focale, r=RES):
        (s0, t0_, h0), (s1, t1, h1) = oeil, cible
        x0, y0 = route.xy(s0, t0_)
        x1, y1 = route.xy(s1, t1)
        z0 = z_sol(sol, x0, y0) + h0 if 0 <= s0 <= route.L else h0
        z1 = z_sol(sol, x1, y1) + h1 if 0 <= s1 <= route.L else h1
        _camera(stage, nom, (x0, y0, z0), (x1, y1, z1), focale, r)
        cams[nom] = {"oeil_st_h": list(oeil), "cible_st_h": list(cible), "focale_mm": focale,
                     "oeil_xyz": [round(float(x0), 3), round(float(y0), 3), round(float(z0), 3)],
                     "cible_xyz": [round(float(x1), 3), round(float(y1), 3), round(float(z1), 3)]}
        res[nom] = r

    xc, yc = route.xy(s_f, 0.5 * (tmax + tmin))
    larg_dessus = min(max(tmax - tmin + 6.0, 26.0), 40.0)
    cams["dessus"] = _dessus(stage, (xc, yc), z_sol(sol, xc, yc), larg_dessus, RES_DESSUS)
    res["dessus"] = RES_DESSUS
    n_arb_m = sum(len(g[1].points()) for k, g in instances.items() if k.startswith("Arbres_modele"))
    dist, inc = (28.0, math.radians(40.0)) if n_arb_m else (26.0, math.radians(34.0 if route_seule else 28.0))
    dh = dist * math.cos(inc)
    t_c = 0.5 * (bandes["chaussee"][0] + bandes["chaussee"][1])
    cam("oblique", (s_f - dh * math.cos(math.radians(45)), t_c - dh * math.sin(math.radians(45)), dist * math.sin(inc)),
        (s_f, t_c, 0.0), 26)
    t_cond = bandes["voie_droite"]
    cam("conducteur", (max(0.5, s_f - 32.0), t_cond, 1.20), (s_f + 8.0, t_cond, 0.75), 24)
    t_piet = bandes["pieton"]
    cam("pieton", (max(0.5, s_f - 14.0), t_piet, 1.60), (s_f + 6.0, t_c, 0.4), 24)
    for nom, (o, c, f) in (vues or VUES.get(scene, {})).items():
        cam(nom, o, c, f)
    for (nom, s, t, h, lacet, tangage, fov, r) in VUES_PHOTO.get(scene, []):
        x0, y0 = route.xy(s, t)
        z0 = z_sol(sol, x0, y0) + h
        cap = _cap_route(route, s) + lacet
        camera_photo(stage, nom, (float(x0), float(y0), z0), cap, tangage, fov, r)
        cams[nom] = {"oeil_st_h": [s, t, h], "lacet_deg": round(cap, 3), "tangage_deg": tangage, "champ_deg": fov,
                     "oeil_xyz": [round(float(x0), 3), round(float(y0), 3), round(float(z0), 3)]}
        res[nom] = r
    rs = UsdRender.Settings.Define(stage, "/Render/reglages")
    rs.CreateResolutionAttr(Gf.Vec2i(*RES))
    stage.SetDefaultPrim(monde)
    stage.GetRootLayer().Save()
    m1 = texture_m1(stage)
    # ---- rendu, mesures, tuiles, planche
    if seulement:
        res = {k: v for k, v in res.items() if k in seulement}
    pngs = rendre(usd, res, d, echantillons=echantillons)
    dyn = {k: dynamique(v) for k, v in pngs.items()}
    tu = {}
    for nom, png in pngs.items():
        m = RL.tuiles(png, d / "tuiles" / nom)
        tu[nom] = [x["fichier"] for x in m.get("tuiles", [])]
    planche = PL.planche_scene(scene, pngs, d / f"planche_{scene}.png")
    RL.nettoyer_rat()
    geo_rendue = {}
    for lot, f in (("l2", Path(dossier_scene) / "l2" / "route_l2.usda"), ("l2b", Path(dossier_scene) / "l2b" / "route_l2b.usda")):
        if f.exists():
            geo_rendue[f"{lot}/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()
    if route_seule:
        info_decor = {"mode": "route seule (étape 1, décision de l'utilisateur du 17/10/2026)",
                      "socle": "jupe verticale sous la limite extérieure du profil et coupe nette en s = 0 et s = L, "
                               f"jusqu'au sol plat (z = {decor['z_socle']} m : 5 cm sous la surface visible la plus basse)",
                      "sol": f"plat, neutre et uni (albédo linéaire {list(SOL_NEUTRE)}), mailles de 2 à 512 m jusqu'à 16 km",
                      "abords_du_modele": "non rendus (sous-ensemble de faces lié à un matériau invisible)",
                      "faces_sous_ensembles": faces_sous,
                      "arbres_modele": 0, "arbres_decor": 0, "montagnes": False, "prolongements": False,
                      "nuages": False,
                      "ombre_de_la_route_sur_le_sol": "aucune : soleil et ciel du sol neutre liés à lui seul, sans "
                                                      "ombre portée (liens UsdLux) ; éclairage inchangé",
                      "usure_des_sols": {"coordonnees": "(s, t) de la route (primvar st_route)",
                                         "decalage_scene_m": list(decalage_scene(scene))}}
    else:
        info_decor = {"mode": "décor de l'étape 2",
                      "sol": f"anneau triangulé raccordé au bord du sol fabriqué et de ses prolongements (gauche {mg}, "
                             f"droite {md} : matériaux et UV des abords)",
                      "prolongements": f"profil d'extrémité extrudé sur {DC.PROLONGEMENT_M:.0f} m de chaque côté, sans marquage",
                      "fond": "anneau de relief de 4,5 à 12 km (300-1 600 m), procédural",
                      "arbres_modele": sum(m["instances"] for m in mesures_arbres if m["groupe"].startswith("Arbres_modele")),
                      "arbres_decor": sum(m["instances"] for m in mesures_arbres if m["groupe"] == "Arbres_decor"),
                      "instances": "PointInstancer, trois prototypes par gabarit", "faces_sous_ensembles": faces_sous}
    man = {"schema": "rg_rendus_l2b/0.3", "scene": scene, "moteur": "Karma XPU (husk)",
           "echantillons": echantillons or ECHANTILLONS, "etape": 1 if route_seule else 2,
           "geometrie_rendue_sha256": geo_rendue,
           "eclairage": {"soleil_intensite": SOLEIL, "soleil_elevation_deg": SOLEIL_ELEVATION,
                         "soleil_azimut_deg": SOLEIL_AZIMUT, "soleil_normalize": True, "ciel": info_ciel,
                         "exposition_fixe": round(exposition(), 5), "gain": EXPO_GAIN,
                         "courbe": f"linéaire, épaule au-dessus de 0,80, sRGB, courbe en S {CONTRASTE}"},
           "saison": sai, "decor": info_decor,
           "arbres": mesures_arbres,
           "textures": {k: str(Path(v).relative_to(DEPOT)).replace("\\", "/") for k, v in sorted(tex.items())},
           "textures_sha256": TS.empreintes(tex), "sols_recolores": stats_tex,
           "materiaux": sources, "cameras": cams, "resolutions": {k: list(v) for k, v in res.items()},
           "images": {k: v.name for k, v in pngs.items()}, "tuiles": tu, "planche": planche.name,
           "M1": {"textures": m1[0], "maillages": m1[1], "non_textures": m1[2]},
           "L1": dyn, "duree_s": round(time.time() - t0, 1)}
    (d / "manifest_rendus.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{scene} : {len(pngs)} rendus, M1 {m1[0]}/{m1[1]}, dynamique min "
          f"{min(v['dynamique'] for v in dyn.values()):.3f} ({round(time.time() - t0)} s) -> {d}")
    return man
