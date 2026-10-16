# -*- coding: utf-8 -*-
"""Table des assets « route_fr » (static meshes) : cotes sourcées, paramètres des HDA, matériaux.

Seule source de vérité des cotes pour la fabrication Houdini (recon/pcg/assets_route/fabriquer_assets_route.py) et
pour le catalogue versionné assets/specs/route/catalogue_assets_route.json. Ce module ne fait AUCUNE géométrie 3D :
il décrit des sections 2D (contours de profils, cotes) lues sur les documents ; les volumes sont fabriqués par les
HDA route::* (réseaux SOP/VEX, recon/pcg/assets_route/hda/).

Conventions (identiques à assets/specs/bordures_elements.json « repere ») :
- profils de bordure : (u, v) en m, u = 0 sur la face vue (côté chaussée), positif vers l'arrière (trottoir) ;
  v = 0 au dessous du bloc ; contour fermé, premier point = coin avant bas ;
- caniveaux : u = 0 au bord côté chaussée (côté haut, chanfrein 15 × 15), u = largeur contre la face de la bordure ;
- USD (Z haut, m) : X = long de l'élément, Y = u (vers l'arrière), Z = v ; feux et supports : optiques vers +Y ;
  pivot des éléments droits au milieu de la longueur, sur l'arête avant basse ; pivot des pièces d'angle et des
  courbes au point d'angle de la face vue.

Chaque cote porte sa source : clé de SOURCES + page (+ figure). confiance : haute (cote lue sur un document coté),
moyenne (source secondaire ou cote déduite), estimation (aucune source : valeur de pratique à vérifier).
"""
import math

# ---------------------------------------------------------------------------------------------- sources
DOCROUTE = "D:/DocRoute"   # copie de travail sur D: (l'ancienne copie du Bureau n'est plus utilisée)
SRC14 = DOCROUTE + "/14_Assets_Route_Statics/sources"
SOURCES = {
    "alkern2026": dict(doc="Alkern, « Toutes les solutions pour aménager les villes et les territoires » — catalogue Voirie 2026",
                       fichier=SRC14 + "/catalogues_bordures/alkern_catalogue_voirie_2026.pdf",
                       url="https://www.alkern.fr/wp-content/uploads/2026/06/CATALOGUE-VOIRIE-2026.pdf",
                       statut="catalogue fabricant public ; profils certifiés NF (NF EN 1340 + NF P 98-340/CN, p. 56)"),
    "celtys": dict(doc="Celtys, catalogue « Bordures – Travaux publics » (8 p.)",
                   fichier=SRC14 + "/catalogues_bordures/celtys_catalogue_bordures_tp_hellopro.pdf",
                   url="https://www.hellopro.fr//documentation/pdf_prod/0/4/0/36050_9cb0dc8651512a6c9ced73c97a4dac56_6058040.pdf",
                   statut="catalogue fabricant public (hébergé par hellopro)"),
    "sepa_T": dict(doc="Sepa (groupe Leonhart), fiches techniques bordures T1, T2, T2 basse, T3 (éd. 01/01/2017)",
                   fichier=SRC14 + "/catalogues_bordures/sepa_fiche_bordures_trottoir_T1_T2_T3.pdf",
                   url="https://www.sepa-alsace.com/media/8622/Fiche_technique_bordures_monobeton_trottoir_T1_T2_T2coller_T2_basse_T3_T3_ba.pdf",
                   statut="fiche fabricant publique"),
    "sepa_CS": dict(doc="Sepa, fiches techniques caniveaux CS1, CS2, CS3 (éd. 01/01/2017)",
                    fichier=SRC14 + "/catalogues_bordures/sepa_fiche_caniveaux_CS1_CS2_CS3_hellopro.pdf",
                    url="https://www.hellopro.fr//documentation/pdf_prod/8/0/1/1590519_0f3b266202a9e5e84c6b1229e21e1fa9_6058108.pdf",
                    statut="fiche fabricant publique"),
    "angers_cpu": dict(doc="Ville d'Angers, Cahier de prescriptions urbaines (cpu.angers.fr), fiches produit",
                       fichier=SRC14 + "/collectivites/angers_cpu_<fiche>.pdf", url="https://cpu.angers.fr/product/<fiche>",
                       statut="document public de collectivité"),
    "grandlyon_barriere": dict(doc="Métropole de Lyon, fiche Réflexe « Les barrières » (2019), p. 2",
                               fichier="D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/grandlyon_RFX_barriere_2019.pdf",
                               statut="document public de collectivité (déjà dans le dépôt)"),
    "iisr1": dict(doc="IISR 1re partie « Généralités » (version consolidée 04/09/2025)",
                  fichier=DOCROUTE + "/01_IISR_Signalisation_Officielle/IISR_1ere_Partie_Generalites_20250904.pdf",
                  statut="texte réglementaire (arrêté du 24/11/1967 modifié)"),
    "iisr6": dict(doc="IISR 6e partie « Feux de circulation permanents » (version consolidée 04/09/2025)",
                  fichier=DOCROUTE + "/01_IISR_Signalisation_Officielle/IISR_6e_Partie_Feux_Circulation_20250904.pdf",
                  statut="texte réglementaire"),
    "trafic_feux": dict(doc="Trafic (Norroy-le-Veneur), fiches produit feux D200 : 160983 tricolore « SCE », 1603XX feu simple, "
                            "160874 feu de passage, 160880 bicolore (2023)",
                        fichier=SRC14 + "/catalogues_feux/hellopro_feu_[1-4].pdf",
                        url="https://www.hellopro.fr//documentation/pdf_prod/0/2/1/1483473_928a9ec7f047e944be8a00828af0b669_6821120.pdf",
                        statut="fiches fabricant publiques (feux de chantier / accès privés : ordres de grandeur des boîtiers D200)"),
    "setra_gc": dict(doc="Setra, Guide technique GC « Garde-corps » (avril 1997)",
                     fichier=SRC14 + "/cerema_setra/setra_guide_technique_GC_garde_corps_1997.pdf",
                     url="https://piles.cerema.fr/IMG/pdf/garde_corps_guide_technique_gc_1997_cle24ec8b.pdf",
                     statut="guide technique public (Setra / Cerema)"),
    "cerema_gc_cycles": dict(doc="Cerema (piles), « Hauteurs de garde-corps en présence de cycles ou cavaliers »",
                             fichier=SRC14 + "/cerema_setra/cerema_hauteurs_garde_corps_cycles.pdf",
                             url="https://piles.cerema.fr/IMG/pdf/4-Hauteurs_de_garde-corps_en_presence_de_cycles_ou_cavaliers_cle71135e-2.pdf",
                             statut="fiche publique Cerema"),
    "certu_bev": dict(doc="Certu / Cerema, fiche n° 03 « Bandes d'éveil de vigilance (BEV) – Implantation » (juillet 2010)",
                      fichier="D:/ClaudeCode_RoadCreation/data/raw/normes/cerema/certu_cerema_fiche03_bev_implantation_2010.pdf",
                      statut="fiche publique (déjà dans le dépôt)"),
    "samse_bev": dict(doc="Samse / CRP, fiche « Dalles podotactiles Tactilgrip » (NF EN 1339)",
                      fichier=SRC14 + "/catalogues_mobilier/samse_fiche_1057291.pdf",
                      url="https://medias.groupe-samse.fr/Fiche_technique/Fiche_technique_1057291.pdf", statut="fiche fabricant"),
    "passage_bev": dict(doc="Passage SAS (Trenois), fiche « Bandes d'éveil à la vigilance en extérieur » (BEV 5/6/7)",
                        fichier=SRC14 + "/catalogues_mobilier/trenois_dalle_podotactile_paa030.pdf",
                        url="https://media.trenois.com/static/dalle-podotactile-interieureexterieure_paa030_fiche-technique.pdf",
                        statut="fiche fabricant"),
    "hellopro_bev_guide": dict(doc="Hellopro, « Tout savoir sur les dalles podotactiles » (conseil d'expert)",
                               url="https://conseils.hellopro.fr/tout-savoir-sur-les-dalles-podotactiles-normes-reglementation-dimensions-prix-1287.html",
                               statut="source secondaire (résumé de NF P 98-351, non vérifié sur la norme)"),
    "arrete2007": dict(doc="Arrêté du 15 janvier 2007 (accessibilité de la voirie), art. 1er 6° b et c",
                       fichier="D:/ClaudeCode_RoadCreation/data/raw/normes/accessibilite/arrete_15janvier2007_voirie_prescriptions_cantal.pdf",
                       statut="texte réglementaire (copie publiée par la préfecture du Cantal)"),
    "noblema": dict(doc="Noblema, « Bordures granit type, profil et caniveaux normés » (page web)",
                    url="https://www.noblema.com/blog/non-classifiee/bordures-granit-type-normees",
                    statut="page fabricant (granit) ; cotes T1 12 × 20, A1 20 × 25, A2 15 × 20, P1 8 × 20, P3 6 × 20"),
    "fabemi_I2": dict(doc="Fabemi TP, fiche technique produit « Bordure I2 0,5 m » (10/07/2012, éd. 1)",
                      fichier=SRC14 + "/catalogues_bordures/sepa_hellopro_6057591.pdf",
                      url="https://www.hellopro.fr/bordure-d-ilot-directionnel-i2-longueur-0-50m-grise-2000585-6057591-produit.html",
                      statut="fiche fabricant publique (NF EN 1340, NF P 98-340/CN) ; tolérances dimensionnelles"),
    "sfac_p4": dict(doc="SFAC (vente au détail, Bricomarché), « Bordurette P4 5 × 20 × 50 cm » (fiche produit, réf. 3760377543681)",
                    url="https://www.bricomarche.com/p/bordurette-p4-5x20x50-cm-rouge/3760377543681",
                    statut="fiche de vente au détail (page non lisible par robot : intitulé relevé dans un moteur de recherche le "
                           "16/10/2026) ; aucune fiche NF du profil P4 trouvée"),
    "feux_json": dict(doc="assets/specs/feux.json (observations Panoramax 2024-2025 du carrefour Paquet Jardin)",
                      fichier="D:/ClaudeCode_RoadCreation/assets/specs/feux.json", statut="observation du site (non normatif)"),
}


def src(cle, page=None, figure=None, article=None, note=None):
    d = {"doc": cle}
    if page is not None:
        d["page"] = page
    if figure:
        d["figure"] = figure
    if article:
        d["article"] = article
    if note:
        d["note"] = note
    return d


# ---------------------------------------------------------------------------------------------- géométrie 2D
def _arrondir(pts, i, r, n=6):
    """Remplace le sommet i d'un contour fermé par un arc de rayon r tangent aux deux côtés (n segments)."""
    p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
    a = (p0[0] - p1[0], p0[1] - p1[1])
    b = (p2[0] - p1[0], p2[1] - p1[1])
    la, lb = math.hypot(*a), math.hypot(*b)
    a, b = (a[0] / la, a[1] / la), (b[0] / lb, b[1] / lb)
    cosang = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    ang = math.acos(cosang)
    t = r / math.tan(ang / 2.0)
    t = min(t, 0.999 * la, 0.999 * lb)
    r = t * math.tan(ang / 2.0)
    q0 = (p1[0] + a[0] * t, p1[1] + a[1] * t)
    q1 = (p1[0] + b[0] * t, p1[1] + b[1] * t)
    bis = (a[0] + b[0], a[1] + b[1])
    lbis = math.hypot(*bis)
    d = r / math.sin(ang / 2.0)
    c = (p1[0] + bis[0] / lbis * d, p1[1] + bis[1] / lbis * d)
    a0 = math.atan2(q0[1] - c[1], q0[0] - c[0])
    a1 = math.atan2(q1[1] - c[1], q1[0] - c[0])
    da = a1 - a0
    while da > math.pi:
        da -= 2 * math.pi
    while da < -math.pi:
        da += 2 * math.pi
    arc = [(c[0] + r * math.cos(a0 + da * k / n), c[1] + r * math.sin(a0 + da * k / n)) for k in range(n + 1)]
    return pts[:i] + arc + pts[i + 1:]


def contour(pts, conges=()):
    """pts : coins du contour ; conges : [(indice du coin, rayon)] appliqués du dernier au premier."""
    out = [tuple(p) for p in pts]
    for i, r in sorted(conges, key=lambda x: -x[0]):
        out = _arrondir(out, i, r)
    return [(round(u, 5), round(v, 5)) for u, v in out]


def arc_pts(c, r, a0, a1, n):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def chaine(pts):
    return " ".join(f"{u:.5f} {v:.5f}" for u, v in pts)


# ---------------------------------------------------------------------------------------------- profils
# Coins lus sur les dessins cotés Alkern 2026 (pages PDF = pages imprimées). « face » : partie verticale de la face
# vue ; « pas » : petit ressaut de 2 mm au départ de la face inclinée ; « tête » : largeur de la tête mesurée depuis
# l'arrière jusqu'au coin fictif face inclinée / dessus ; le dessus descend vers l'avant (pente du dessus).
def _T(base, H, face, tete, pente, r=0.02, pas=0.002, chanfrein_arriere=0.0):
    uc = base - tete - chanfrein_arriere
    pts = [(0.0, 0.0), (0.0, face), (pas, face), (uc, H - pente)]
    ic = 3
    if chanfrein_arriere:
        pts += [(base - chanfrein_arriere, H), (base, H - chanfrein_arriere), (base, 0.0)]
    else:
        pts += [(base, H), (base, 0.0)]
    return contour(pts, [(ic, r)])


def _I(base, H, chute, plat, face_droite, r=0.02, pas=0.002):
    """Bordure d'îlot Alkern : plat arrière, pente vers l'avant, coin fictif à H − chute, face droite courte."""
    vc = H - chute
    pts = [(0.0, 0.0), (0.0, face_droite), (pas, face_droite), (pas, vc), (base - plat, H), (base, H), (base, 0.0)]
    return contour(pts, [(3, r)])


def _CC2():
    # arc de cercle passant par (0,05 ; 0,14), (0,25 ; 0,11), (0,45 ; 0,14) : flèche 0,03 sur 0,40 -> R = 0,6817 m
    R = (0.2 ** 2 + 0.03 ** 2) / (2 * 0.03)
    c = (0.25, 0.11 + R)
    a = math.degrees(math.asin(0.2 / R))
    arc = arc_pts(c, R, 270 - a, 270 + a, 12)
    return [(0.0, 0.0), (0.0, 0.14)] + [(round(u, 5), round(v, 5)) for u, v in arc] + [(0.5, 0.14), (0.5, 0.0)]


def _P1(face, plat, H, base=0.08, r=0.03, pas=0.002):
    uc = base - plat
    a0 = 180.0 - math.degrees(math.asin(max(-1.0, min(1.0, (face - (H - r)) / r))))
    arc = arc_pts((uc, H - r), r, a0, 90, 6)
    return [(0.0, 0.0), (0.0, face), (pas, face)] + [(round(u, 5), round(v, 5)) for u, v in arc[1:]] + [(base, H), (base, 0.0)]


def _P2():
    arc = arc_pts((0.03, 0.22), 0.03, 180, 0, 10)
    return [(0.0, 0.0)] + [(round(u, 5), round(v, 5)) for u, v in arc] + [(0.06, 0.0)]


def _rect_arrondi(base, H, r):
    return contour([(0.0, 0.0), (0.0, H), (base, H), (base, 0.0)], [(1, r)])


A26 = "alkern2026"
PROFILS = {
    # --- type T (trottoir)
    "T1": dict(pts=_T(0.12, 0.20, 0.100, 0.100, 0.004), H=0.20, base=0.12, famille="T", vue=[0.10, 0.14],
               sources=[src(A26, 9, "Bordure T1 (coupe cotée)"), src("celtys", 7, note="T1 12 × 20, 54 kg/ml"),
                        src("sepa_T", 1, note="longueur réelle 994 mm")], confiance="haute",
               lecture="120 × 200 ; face verticale 100 ; ressaut 2 ; tête 100 ; dessus en pente de 4 mm ; congé R20"),
    "T2": dict(pts=_T(0.15, 0.25, 0.100, 0.118, 0.005), H=0.25, base=0.15, famille="T", vue=[0.12, 0.16],
               sources=[src(A26, 10, "Bordure T2 (coupe cotée)"), src("celtys", 7, note="T2 15 × 25, 83 kg/ml"),
                        src("sepa_T", 2, note="longueur réelle 992 mm")], confiance="haute",
               lecture="150 × 250 ; face verticale 100 ; ressaut 2 ; tête 118 ; pente 5 ; R20"),
    "T3": dict(pts=_T(0.17, 0.28, 0.110, 0.138, 0.006), H=0.28, base=0.17, famille="T", vue=[0.16, 0.20],
               sources=[src(A26, 12, "Bordure T3 (coupe cotée)"),
                        src("celtys", 7, note="le tableau imprime « T3 15 × 25 » : coquille (108 kg/ml = section 17 × 28)")],
               confiance="haute", lecture="170 × 280 ; face 110 ; ressaut 2 ; tête 138 ; pente 6 ; R20"),
    "T4": dict(pts=_T(0.20, 0.30, 0.160, 0.165, 0.007, chanfrein_arriere=0.005), H=0.30, base=0.20, famille="T",
               vue=[0.18, 0.22], sources=[src(A26, 13, "Bordure T4 (coupe cotée, réf. 520048)")], confiance="haute",
               lecture="200 × 300 ; face 160 ; ressaut 2 ; tête 165 depuis un chanfrein arrière 5 × 5 ; pente 7 ; R20"),
    "T2_basse": dict(pts=contour([(0, 0), (0, 0.125), (0.002, 0.125), (0.002, 0.145), (0.151, 0.150), (0.151, 0)], [(3, 0.02)]),
                     H=0.15, base=0.151, famille="T", vue=[0.06, 0.10],
                     sources=[src(A26, 11, "T2 basse (réf. 520029)"), src("sepa_T", 4, note="T2 taille basse")],
                     confiance="haute", lecture="151 × 150 ; face verticale 125 ; ressaut 2 ; tête 149 ; pente 5 ; R20"),
    "T2_surbaissee": dict(pts=_T(0.151, 0.15, 0.020, 0.121, 0.005), H=0.15, base=0.151, famille="T", vue=[0.0, 0.04],
                          sources=[src(A26, 11, "T2 surbaissée (réf. 520034)")], confiance="haute",
                          lecture="151 × 150 ; face verticale 20 ; ressaut 2 ; tête 121 ; pente 5 ; R20 ; élément de bateau "
                                  "(vue ≤ 2 cm imposée par l'arrêté du 15/01/2007 aux traversées)"),
    "T3_basse": dict(pts=_T(0.17, 0.20, 0.130, 0.148, 0.006), H=0.20, base=0.17, famille="T", vue=[0.08, 0.12],
                     sources=[src(A26, 12, "T3 basse (réf. 520248)")], confiance="haute",
                     lecture="170 × 200 ; face 130 ; ressaut 2 ; tête 148 ; pente 6 ; R20"),
    "T3_surbaissee": dict(pts=_T(0.17, 0.20, 0.065, 0.100, 0.006), H=0.20, base=0.17, famille="T", vue=[0.0, 0.04],
                          sources=[src(A26, 12, "T3 surbaissée (réf. 520252)")], confiance="haute",
                          lecture="170 × 200 ; face 65 ; ressaut 2 ; tête 100 ; pente 6 ; R20"),
    # --- type A (franchissable)
    "A1": dict(pts=contour([(0, 0), (0, 0.19), (0.08, 0.25), (0.20, 0.25), (0.20, 0)]), H=0.25, base=0.20, famille="A",
               vue=[0.06, 0.12], sources=[src(A26, 15, "Bordure A1"), src("celtys", 7, note="A1 20 × 25, 112 kg/ml")],
               confiance="haute", lecture="200 × 250 ; face 190 ; chanfrein 80 × 60 ; plat 120"),
    "A2": dict(pts=contour([(0, 0), (0, 0.14), (0.08, 0.20), (0.15, 0.20), (0.15, 0)]), H=0.20, base=0.15, famille="A",
               vue=[0.04, 0.10], sources=[src(A26, 15, "Bordure A2"), src("celtys", 7, note="A2 15 × 20, 67 kg/ml")],
               confiance="haute", lecture="150 × 200 ; face 140 ; chanfrein 80 × 60 ; plat 70"),
    # --- type I (îlot)
    "I1": dict(pts=_I(0.25, 0.13, 0.07, 0.05, 0.046), H=0.13, base=0.25, famille="I", vue=[0.06, 0.06],
               sources=[src(A26, 27, "Bordure I1 100 (994 × 250 × 130)"), src("celtys", 3, note="I1 25 × 13, face vue 6")],
               confiance="haute", lecture="250 × 130 ; plat arrière 50 ; chute 70 jusqu'au coin fictif ; face droite 46 ; ressaut 2 ; R20"),
    "I2": dict(pts=_I(0.25, 0.18, 0.07, 0.05, 0.096), H=0.18, base=0.25, famille="I", vue=[0.11, 0.11],
               sources=[src(A26, 28, "Bordure I2 100"), src("celtys", 3, note="I2 25 × 18, face vue 11"),
                        src("fabemi_I2", 1, note="I2 0,5 m : 500 × 250 × 180, chanfrein 5 × 5, classe U (6,0 MPa)")], confiance="haute",
               lecture="250 × 180 ; plat 50 ; chute 70 ; face droite 96 (déduite : même tête que I1) ; R20"),
    "I3": dict(pts=_I(0.30, 0.13, 0.07, 0.10, 0.046), H=0.13, base=0.30, famille="I", vue=[0.06, 0.06],
               sources=[src(A26, 29, "Bordure I3 100 (994 × 300 × 130)")], confiance="haute",
               lecture="300 × 130 ; plat 100 ; chute 70 ; face droite 46 ; R20 ; posée collée sur chaussée"),
    "I4": dict(pts=_I(0.30, 0.18, 0.07, 0.10, 0.096), H=0.18, base=0.30, famille="I", vue=[0.11, 0.11],
               sources=[src(A26, 30, "Bordure I4 100 (994 × 300 × 180)")], confiance="haute",
               lecture="300 × 180 ; plat 100 ; chute 70 ; R20 ; encastrée"),
    # --- type P (bordurettes)
    "P1": dict(pts=_P1(0.175, 0.048, 0.20), H=0.20, base=0.08, famille="P", vue=[0.0, 0.06],
               sources=[src(A26, 21, "Bordure P1"), src("celtys", 4, note="P1 8 × 20")], confiance="haute",
               lecture="80 × 200 ; face 175 ; ressaut 2 ; arrondi R30 ; plat 48"),
    "P1_basse": dict(pts=_P1(0.090, 0.047, 0.12, pas=0.003), H=0.12, base=0.08, famille="P", vue=[0.0, 0.04],
                     sources=[src(A26, 21, "Bordure P1 basse")], confiance="haute", lecture="80 × 120 ; face 90 ; ressaut 3 ; R30 ; plat 47"),
    "P2": dict(pts=_P2(), H=0.25, base=0.06, famille="P", vue=[0.0, 0.08],
               sources=[src(A26, 21, "Bordure P2 (60 × 250, tête ronde R30)"),
                        src("celtys", 4, note="Celtys : P2 6 × 28 (autre hauteur)")], confiance="haute",
               lecture="60 × 250 à tête demi-ronde R30"),
    "P3": dict(pts=contour([(0, 0), (0, 0.20), (0.06, 0.20), (0.06, 0)]), H=0.20, base=0.06, famille="P", vue=[0.0, 0.06],
               sources=[src(A26, 21, "Bordure P3 (60 × 200)"), src("noblema", note="P3 6 × 20 en granit")], confiance="haute",
               lecture="60 × 200 rectangulaire (profil fabricant, hors liste NF : A1-A2, P1-P2-P4, T1-T4, I1-I4, CS1-CS4, CC1-CC2) ; "
                       "la masse annoncée (36 kg) correspond plutôt à 80 × 200 (Celtys : P3 8 × 20)"),
    "P4": dict(pts=_rect_arrondi(0.05, 0.20, 0.008), H=0.20, base=0.05, famille="P", vue=[0.0, 0.05],
               sources=[src(A26, 56, note="liste des profils NF P 98-340/CN (extrait du guide CERIB 206E) : type P = P1, P2, P4 ; "
                                         "type I = I1 à I4 (pas d'I5 ni d'I6)"),
                        src("sfac_p4", note="bordurette P4 5 × 20 × 50 cm")], confiance="estimation",
               lecture="50 × 200 rectangulaire, arête avant haute R8 (forme non cotée) ; seule source : intitulé d'une fiche de vente "
                       "au détail ; à remplacer par le profil NF P 98-340/CN"),
    # --- quai bus
    "ACCESBUS": dict(pts=contour([(0, 0), (0, 0.090), (0.002, 0.090), (0.050, 0.289), (0.195, 0.295), (0.200, 0.290), (0.200, 0)],
                                 [(3, 0.010)]), H=0.295, base=0.20, famille="quai_bus", vue=[0.18, 0.21],
                     sources=[src(A26, 33, "Bordure Accesbus (réf. 520021)")], confiance="haute",
                     lecture="200 × 295 ; face 90 ; ressaut 2 ; tête 145 depuis un chanfrein arrière 5 × 5 ; pente 6 ; R10"),
    # --- granit (même famille de profils, faces flammées ou bouchardées, arête arrondie R 1-2 cm)
    "GR_T2": dict(pts=_rect_arrondi(0.15, 0.25, 0.015), H=0.25, base=0.15, famille="granit", vue=[0.12, 0.16],
                  sources=[src("angers_cpu", note="fiche « bordures-en-granit » (27/06/2018) : L 15 × H 25 cm, flammée ou bouchardée "
                                                  "sur 2 faces, autres faces sciées, arête arrondie R 1 à 2 cm, gris bleu clair")],
                  confiance="haute", lecture="150 × 250 rectangulaire, arête avant haute R15 (milieu de 1-2 cm)"),
    "GR_T1": dict(pts=_rect_arrondi(0.12, 0.20, 0.015), H=0.20, base=0.12, famille="granit", vue=[0.10, 0.14],
                  sources=[src("noblema", note="granit type T1 12 × 20 × 100"),
                           src("angers_cpu", note="arête arrondie R 1-2 cm (fiche bordures-en-granit)")],
                  confiance="moyenne", lecture="120 × 200 rectangulaire, R15 (section rectangulaire supposée comme GR_T2)"),
    "GR_P1": dict(pts=_rect_arrondi(0.08, 0.20, 0.010), H=0.20, base=0.08, famille="granit", vue=[0.0, 0.06],
                  sources=[src("noblema", note="granit type P1 8 × 20 × 100")], confiance="moyenne",
                  lecture="80 × 200, arête R10 (estimée)"),
    # --- caniveaux (u = 0 côté chaussée)
    "CS1": dict(pts=contour([(0, 0), (0, 0.105), (0.015, 0.120), (0.200, 0.100), (0.200, 0)]), H=0.12, base=0.20,
                famille="caniveau", sources=[src(A26, 17, "CS1"), src("sepa_CS", 1)], confiance="haute",
                lecture="200 de large ; 120 côté chaussée (105 + chanfrein 15 × 15) ; 100 côté bordure (fil d'eau)"),
    "CS2": dict(pts=contour([(0, 0), (0, 0.120), (0.015, 0.135), (0.250, 0.110), (0.250, 0)]), H=0.135, base=0.25,
                famille="caniveau", sources=[src(A26, 17, "CS2"), src("sepa_CS", 1)], confiance="haute",
                lecture="250 ; 135 côté chaussée (120 + 15) ; 110 côté bordure"),
    "CS3": dict(pts=contour([(0, 0), (0, 0.150), (0.015, 0.165), (0.250, 0.110), (0.250, 0)]), H=0.165, base=0.25,
                famille="caniveau", sources=[src(A26, 17, "CS3")], confiance="haute", lecture="250 ; 165 (150 + 15) ; 110"),
    "CS4": dict(pts=contour([(0, 0), (0, 0.175), (0.015, 0.190), (0.300, 0.160), (0.300, 0)]), H=0.19, base=0.30,
                famille="caniveau", sources=[src(A26, 17, "CS4")], confiance="haute", lecture="300 ; 190 (175 + 15) ; 160"),
    "CC1": dict(pts=contour([(0, 0), (0, 0.106), (0.014, 0.120), (0.200, 0.100), (0.386, 0.120), (0.400, 0.106), (0.400, 0)]),
                H=0.12, base=0.40, famille="caniveau", sources=[src(A26, 18, "CC1"), src("celtys", 7, note="CC1 40 × 12")],
                confiance="haute", lecture="400 × 120 ; bords 106 + chanfrein 14 × 14 ; creux central à 100"),
    "CC2": dict(pts=_CC2(), H=0.14, base=0.50, famille="caniveau", sources=[src(A26, 18, "CC2"), src("celtys", 7, note="CC2 50 × 14")],
                confiance="haute", lecture="500 × 140 ; plats de 50 ; fond circulaire à 110 (R ≈ 0,68 m déduit)"),
}

# masses par élément de 1 m (Alkern 2026 ; Celtys p. 7 entre parenthèses dans les notes) : contrôle des sections
MASSES_KG = {"T1": (53, A26, 9), "T2": (83, A26, 10), "T3": (107, A26, 12), "T4": (133, A26, 13), "T2_basse": (52, A26, 11),
             "T2_surbaissee": (50, A26, 11), "T3_basse": (80, A26, 12), "A1": (117, A26, 15), "A2": (66.5, A26, 15),
             "I1": (63, A26, 27), "I3": (78, A26, 29), "I4": (113, A26, 30), "CS1": (53, A26, 17), "CS2": (73, A26, 17),
             "CS3": (90, A26, 17), "CS4": (126, A26, 17), "CC1": (106, A26, 18), "CC2": (149, A26, 18), "P1": (38, A26, 21),
             "P1_basse": (23, A26, 21), "P2": (37, A26, 21), "P3": (36, A26, 21), "ACCESBUS": (122.5, A26, 33)}
MASSES_PIECES_KG = {"bordure_T2_quart_rond_ext_R020": (15, A26, 10), "bordure_T2_quart_rond_int_R020": (15, A26, 10),
                    "bordure_T1_quart_rond_ext_R020": (12, A26, 9), "bordure_T2_angle_sortant": (41, A26, 10),
                    "bordure_T2_angle_rentrant": (41, A26, 10), "bordure_T1_angle_sortant": (12, A26, 9),
                    "bordure_T1_angle_rentrant": (12, A26, 9), "bordure_T2_angle_50_50": (90, A26, 10),
                    "bordure_T3_angle_rentrant": (100, A26, 12), "bordure_T3_angle_sortant": (100, A26, 12),
                    "bordure_T2_courbe_ext_R050": (50, A26, 10), "bordure_I1_quart_rond_R025": (12, A26, 27)}
# Explication des écarts > 8 % (relecture des dessins cotés sur tuiles natives, 16/10/2026) : la géométrie suit les cotes
# dessinées ; c'est la masse imprimée qui est incohérente avec ces cotes.
NOTES_MASSES = {
    "bordure_T1_angle_sortant": "Alkern p. 9 : 325 × 325 × 200 annoncé à 12 kg (même masse que la « T1 courbe R20 » voisine) ; "
                                "un L de 325 × 325 en section T1 pèse ≈ 28 kg : masse catalogue probablement recopiée",
    "bordure_T1_angle_rentrant": "idem T1 angle sortant (Alkern p. 9 : 12 kg pour 325 × 325 × 200, branches de 205 sur la face)",
    "bordure_T2_angle_50_50": "Alkern p. 10 : dessin coté 500 sur la face, 350 + 350 au dos (500 − 150 = 350, cohérent) ; un L de "
                              "ces cotes en section T2 pèse ≈ 69 kg, le catalogue annonce 90 kg",
    "bordure_T3_angle_rentrant": "Alkern p. 12 : 490 × 490 au dos (320 sur la face) annoncé à 100 kg comme l'angle sortant 500 × 500 "
                                 "(330 + 170) : masse commune arrondie ; le calcul sur les cotes donne ≈ 85-89 kg",
    "bordure_T3_angle_sortant": "Alkern p. 12 : cotes 330 + 170 = 500 ; même remarque que l'angle rentrant",
    "bordure_T2_quart_rond_int_R020": "forme non cotée (« D × H 20 × 250 ») : modèle concentrique estimé, à remplacer",
    "bordure_I1_quart_rond_R025": "Alkern p. 27 : nez d'îlot R50 / R250 ; forme exacte du nez non cotée (modèle : profil I1 tourné)",
    "bordure_CS3_L100": "Alkern p. 17 (relu sur tuile) : 250 de large, 110 côté bordure, 150 + chanfrein 15 côté chaussée → "
                        "≈ 0,0345 m²/m soit ≈ 81 kg ; le catalogue annonce 90 kg",
    "bordure_P3_L100": "Alkern p. 21 : dessin 60 × 200 mais 36 kg (≈ 80 × 200, cf. Celtys p. 7 « P3 8 × 20 », 38 kg) : profil "
                       "dessiné conservé, P3 hors liste NF (p. 56)",
}
# Tolérances dimensionnelles des bordures et caniveaux béton (NF EN 1340 / NF P 98-340/CN, fiche Fabemi I2 p. 1)
TOLERANCES = {"longueur": {"< 0,40 m": "± 4 mm", "0,40 à 1,00 m": "± 1 %", "> 1,00 m": "± 10 mm"},
              "faces_vues": {"< 100 mm": "± 3 mm", "100 à 170 mm": "± 3 %", "> 170 mm": "± 5 mm"},
              "faces_cachees": {"< 60 mm": "± 3 mm", "60 à 200 mm": "± 5 %", "> 200 mm": "± 10 mm"},
              "source": {"doc": "fabemi_I2", "page": 1}}
DENSITE_BETON = 2350.0      # kg/m³ (béton préfabriqué vibré ; estimation pour le contrôle des sections)

# ---------------------------------------------------------------------------------------------- éléments
JOINT = 0.006          # joint entre éléments de 1 m (Sepa : T1 994 mm, T2 992 mm ; bordures_elements.json : 6 mm)
MAT_BETON = "beton_bordure"          # assets/lib/materiaux (CC0 Concrete037, étalonné sur le site)
MAT_GRANIT = "granit_gris_flamme"    # route_fr
MAT_PREFA = "beton_prefa_lisse"      # route_fr (CC0 Concrete006) : béton vibré lisse des éléments unitaires (pavés, dalles)
# Règle : un élément UNITAIRE (pavé, dalle, bordure) porte un matériau de MATIÈRE (béton, granit) ; les matériaux
# d'APPAREILLAGE (paves_*, dalles_*, textures de surfaces pavées avec joints) sont réservés aux sols tuilables.
MATERIAUX_ALTERNATIFS = {"beton_bordure": ["beton_prefa_lisse"], "beton_prefa_lisse": ["beton_bordure"]}


def _elem(pid, mode, L=None, R=None, angle=90.0, profil_b=None, suffixe=None, sources_sup=(), confiance=None, note=None,
          materiau=None, centrer=1):
    p = PROFILS[pid]
    params = dict(contour_a=chaine(p["pts"]), mode=mode, longueur=L or 0.0, rayon=R or 0.0, angle_deg=angle, centrer=centrer)
    if profil_b:
        params["contour_b"] = chaine(profil_b)
    nom = {0: "droit", 1: "rampant", 2: "quart_rond_ext", 3: "quart_rond_int", 4: "angle_sortant", 5: "angle_rentrant"}[mode]
    fam = p["famille"]
    mat = materiau or (MAT_GRANIT if fam == "granit" else MAT_BETON)
    dims = dict(base_m=p["base"], H_m=p["H"])
    if L:
        dims["longueur_m"] = L
    if R:
        dims["rayon_face_m"] = R
        dims["angle_deg"] = angle
    return dict(id=f"bordure_{pid}_{suffixe or nom}", famille="bordures" if fam != "caniveau" else "caniveaux",
                type=f"bordure {pid} – {nom}", hda="route::extrusion_profil", params=params, dimensions=dims,
                profil=pid, lecture_profil=p.get("lecture"), vue_nominale_m=p.get("vue"),
                sources=list(p["sources"]) + list(sources_sup), confiance=confiance or p["confiance"], materiau=mat, note=note)


def _rampant(pa, pb, vue_a, vue_b, L=1.0 - JOINT, cote="droite"):
    """Élément de raccord (rampant) : profil A (bordure courante posée à vue_a) vers B (abaissé posé à vue_b), dessous commun."""
    A, B = PROFILS[pa], PROFILS[pb]
    # pose : v_pose = v − (H − vue) ; dessous commun = le plus profond des deux
    da, db = A["H"] - vue_a, B["H"] - vue_b
    fond = max(da, db)
    def poser(pts, d):
        # v' = v − d + fond ; les points du dessous (v = 0) restent au fond commun (v' = 0)
        return [(u, 0.0 if v <= 1e-9 else round(v - d + fond, 5)) for u, v in pts]
    a = poser(A["pts"], da)
    b = poser(B["pts"], db)
    if len(a) != len(b):
        raise ValueError(f"rampant {pa}->{pb} : contours de tailles différentes")
    if cote == "gauche":
        a, b = b, a
    params = dict(contour_a=chaine(a), contour_b=chaine(b), mode=1, longueur=L, rayon=0.0, angle_deg=90.0, centrer=1)
    return dict(id=f"bordure_raccord_{pa}_{pb}_{cote}", famille="bordures", type=f"raccord (rampant) {pa} → {pb} ({cote})",
                hda="route::extrusion_profil", params=params,
                dimensions=dict(longueur_m=L, base_m=max(A["base"], B["base"]), H_m=round(fond + max(vue_a, vue_b), 4),
                                vue_debut_m=vue_a if cote == "droite" else vue_b, vue_fin_m=vue_b if cote == "droite" else vue_a),
                profil=f"{pa}->{pb}", sources=[src(A26, 11 if pa.startswith("T2") else 13,
                                                   f"Raccord {pa.replace('_', ' ')} / {pb.replace('_', ' ')} (1000 mm, droite et gauche)"),
                                               src("arrete2007", note="ressaut ≤ 2 cm aux traversées (vue de l'abaissé)")],
                confiance="moyenne", note="forme interpolée linéairement entre les deux profils cotés (le dessin du raccord n'est "
                                          "coté qu'en longueur) ; dessous commun au plus profond des deux",
                materiau=MAT_BETON)


ASSETS = []
L1, L05 = 1.0 - JOINT, 0.5 - JOINT
for pid in ("T1", "T2", "T3", "T4", "T2_basse", "T2_surbaissee", "T3_basse", "T3_surbaissee", "A1", "A2", "I1", "I2", "I3",
            "I4", "P1", "P1_basse", "P2", "P3", "ACCESBUS", "GR_T2", "GR_T1", "GR_P1", "CS1", "CS2", "CS3", "CS4", "CC1", "CC2"):
    ASSETS.append(_elem(pid, 0, L1, suffixe="L100",
                        sources_sup=[src("sepa_T", 1, note="pas de pose 1,00 m, élément de 992-994 mm (joint 6-8 mm)")],
                        note="élément de 1 m au pas de pose (longueur réelle 0,994 m, joint 6 mm)"))
    if PROFILS[pid]["famille"] in ("T", "A", "I", "caniveau", "granit"):
        ASSETS.append(_elem(pid, 0, L05, suffixe="L050",
                            sources_sup=[src("celtys", 2, note="T2 « existe aussi en 0,50 ml »"),
                                         src(A26, 27, "Bordure I1 50 (497 mm)")],
                            note="élément de 0,50 m (courbes de rayon 3 à 12 m : bordures_elements.json regle_pas_rayon)"))
ASSETS.append(_elem("P4", 0, L05, suffixe="L050", note="bordurette P4 de 0,50 m (format de la seule source trouvée) ; profil estimé"))
# pièces d'angle et quarts de rond (Alkern p. 9, 10, 12)
for pid, L, page in (("T1", 0.325, 9), ("T2", 0.325, 10)):
    for mode in (4, 5):
        Lf = L if mode == 4 else round(L - PROFILS[pid]["base"], 4)      # rentrant : 325 au dos, 205 (T1) / 175 (T2) sur la face
        ASSETS.append(_elem(pid, mode, Lf, centrer=0, sources_sup=[src(A26, page, f"{pid} angle {'sortant' if mode == 4 else 'rentrant'} "
                                                                                   f"{int(L * 1000)} × {int(L * 1000)}"
                                                                                   + ("" if mode == 4 else f" (branches de {int(Lf * 1000)} sur la face)"))]))
ASSETS.append(_elem("T2", 4, 0.50, suffixe="angle_50_50", centrer=0, sources_sup=[src(A26, 10, "T2 angle 50+50 (500 × 500)")]))
ASSETS.append(_elem("T3", 5, 0.32, centrer=0, sources_sup=[src(A26, 12, "T3 angle rentrant 490 × 490 (dos) : 320 sur la face")]))
ASSETS.append(_elem("T3", 4, 0.50, centrer=0, sources_sup=[src(A26, 12, "T3 angle sortant 500 × 500")]))
for pid, page, lib in (("T1", 9, "T1 courbe R20 (D × H 150 × 200, 12 kg)"), ("T2", 10, "T2 angle extérieur R20 (15 kg)")):
    ASSETS.append(_elem(pid, 2, R=0.20, suffixe="quart_rond_ext_R020", centrer=0,
                        sources_sup=[src(A26, page, lib, note="R20 = rayon de 0,20 m de la face (contrôle par la masse : "
                                                                "≈ 13-15 kg pour un quart de cercle)")], confiance="moyenne"))
ASSETS.append(_elem("T2", 3, R=0.20, suffixe="quart_rond_int_R020", centrer=0,
                    sources_sup=[src(A26, 10, "T2 angle intérieur R20 (D × H 20 × 250, 15 kg)")], confiance="estimation",
                    note="forme du catalogue non cotée : modélisé en quart de rond concentrique (36 kg) alors que le catalogue "
                         "annonce 15 kg ; à remplacer par un dessin coté"))
ASSETS.append(_elem("T2", 2, R=0.50, suffixe="courbe_ext_R050", centrer=0,
                    sources_sup=[src(A26, 10, "T2 courbe 50 (50 kg)", note="R = 0,50 m déduit de la masse : quart de cercle → 46 kg")],
                    confiance="moyenne"))
for R in (1.2, 3.0, 6.0):
    ASSETS.append(_elem("T2", 2, R=R, angle=math.degrees((1.0 - JOINT) / R), suffixe=f"courbe_ext_R{int(R * 100):03d}", centrer=0,
                        sources_sup=[{"doc": "bordures_elements.json", "note": "regle_pas_rayon.pieces_courbes : rayons catalogue "
                                                                               "0,5 ; 1,2-2,0 ; 3-9 m (hellopro Aumusse)"}],
                        confiance="moyenne", note="élément courbe de 1 m mesuré sur la face"))
    ASSETS.append(_elem("T2", 3, R=R, angle=math.degrees((1.0 - JOINT) / R), suffixe=f"courbe_int_R{int(R * 100):03d}", centrer=0,
                        sources_sup=[{"doc": "bordures_elements.json", "note": "regle_pas_rayon.pieces_courbes"}],
                        confiance="moyenne", note="élément courbe de 1 m (face concave)"))
ASSETS.append(_elem("I1", 2, R=0.25, suffixe="quart_rond_R025", centrer=0,
                    sources_sup=[src(A26, 27, "Quart de rond I1 (R50 / R250, 500 × 250 × 130)")], confiance="moyenne",
                    note="nez d'îlot : profil I1 tourné d'un quart de tour, face sur le rayon 0,25 m"))
# raccords (rampants) des bateaux
for pa, pb, va, vb in (("T2", "T2_surbaissee", 0.14, 0.02), ("T2", "T2_basse", 0.14, 0.10), ("T3", "T3_surbaissee", 0.18, 0.02)):
    for cote in ("droite", "gauche"):
        ASSETS.append(_rampant(pa, pb, va, vb, cote=cote))

# ---------------------------------------------------------------------------------------------- dalles, pavés, BEV
def _dalle(id_, L, l, e, chanfrein, mat, sources, confiance, plots=None, note=None, famille="dalles"):
    params = dict(longueur=L, largeur=l, epaisseur=e, chanfrein=chanfrein, plots=1 if plots else 0)
    if plots:
        params.update(plots)
    return dict(id=id_, famille=famille, type=id_.replace("_", " "), hda="route::dalle", params=params,
                dimensions=dict(longueur_m=L, largeur_m=l, epaisseur_m=e), sources=sources, confiance=confiance,
                materiau=mat, note=note)


PLOTS_BEV = dict(plot_diam_base=0.035, plot_diam_haut=0.025, plot_hauteur=0.005, plot_entraxe=0.075, plot_marge=0.0375)
ASSETS += [
    _dalle("bev_dalle_beton_600x420x60", 0.60, 0.42, 0.06, 0.003, "beton_bordure",
           [src("samse_bev", 1, note="Tactilgrip 6 : 60 × 42 cm, épaisseur 6 cm, NF EN 1339"),
            src("hellopro_bev_guide", note="plots : dôme Ø 25 mm, hauteur 5 mm, entraxe 75 mm en quinconce (source secondaire)"),
            src("certu_bev", 3, note="largeur standard de la BEV 587,5 mm ; pas de freinage 500 mm")], "moyenne",
           plots=PLOTS_BEV, note="dalle béton blanche ou grise (Angers CPU : contraste blanc sur sol foncé, gris foncé sur sol clair)"),
    _dalle("bev_resine_820x420", 0.82, 0.42, 0.004, 0.001, "bev_blanc",
           [src("passage_bev", 2, note="BEV 5 : 820 × 420 mm (résine méthacrylate, NF P 98-351 août 2010)"),
            src("hellopro_bev_guide", note="plots Ø 25 / h 5 / entraxe 75 en quinconce")], "moyenne", plots=PLOTS_BEV,
           note="épaisseur de semelle 4 mm estimée"),
    _dalle("bev_resine_820x607", 0.82, 0.607, 0.004, 0.001, "bev_blanc",
           [src("passage_bev", 2, note="BEV 6 : 820 × 607 mm (largeur standard ≈ 587,5 mm + bords)"),
            src("certu_bev", 3, note="largeur standard 587,5 mm")], "moyenne", plots=PLOTS_BEV),
    _dalle("pave_beton_200x100x80", 0.20, 0.10, 0.08, 0.005, MAT_PREFA,
           [src("angers_cpu", note="pavés béton gris foncé 10 × 20 cm (ép. 10) et gris clair 12 × 24 (ép. 8) ; format 20 × 10 × 8 "
                                   "courant (NF EN 1338)"), {"doc": "estimation", "note": "chanfrein 5 mm"}], "moyenne", famille="paves"),
    _dalle("pave_beton_200x100x100", 0.20, 0.10, 0.10, 0.005, MAT_PREFA,
           [src("angers_cpu", note="fiche paves-beton-gris-fonce (25/06/2018) : 10 × 20 cm, épaisseur 10 cm (RG4)")], "haute",
           famille="paves"),
    _dalle("pave_beton_240x120x80", 0.24, 0.12, 0.08, 0.005, MAT_PREFA,
           [src("angers_cpu", note="fiche paves-en-beton-gris-clair (25/06/2018) : 12 × 24 cm, épaisseur 8 cm")], "haute",
           famille="paves"),
    _dalle("pave_granit_140x140x140", 0.14, 0.14, 0.14, 0.008, MAT_GRANIT,
           [{"doc": "assets/specs/bordures.json", "note": "PAVES_GRANIT : pavés de granit 14 × 14 estimés sur photo 2025-05-18"},
            src("angers_cpu", note="pavés granit : dimensions variables, sciés pour l'accessibilité PMR")], "estimation",
           famille="paves", note="rangées d'anneaux d'îlots ; arêtes arrondies par chanfrein 8 mm"),
    _dalle("dalle_beton_240x240x80", 0.24, 0.24, 0.08, 0.003, MAT_PREFA,
           [src("angers_cpu", note="fiche dalles-beton-gris-clair (25/06/2018) : 24 × 24 cm, épaisseur 8 cm")], "haute"),
    _dalle("dalle_granit_300x300x80", 0.30, 0.30, 0.08, 0.003, MAT_GRANIT,
           [src("angers_cpu", note="fiche dalles-en-granit (27/06/2018) : 30 × 30 cm, épaisseur 8 cm")], "haute"),
]

# ---------------------------------------------------------------------------------------------- potelets, bornes
def _revol(id_, famille, profil, bandes, sources, confiance, dims, mat_defaut, note=None, divisions=24):
    return dict(id=id_, famille=famille, type=id_.replace("_", " "), hda="route::revolution",
                params=dict(profil=chaine(profil), bandes=bandes, divisions=divisions, materiau=mat_defaut),
                dimensions=dims, sources=sources, confiance=confiance, materiau=mat_defaut, note=note)


def _potelet_gorge(H, tete_blanche):
    r = 0.1016 / 2
    g0, g1, gp = H - 0.16, H - 0.13, 0.008         # gorge (estimée : 30 mm de haut, 8 mm de creux, 13-16 cm sous le sommet)
    prof = [(0.0, -0.30), (r, -0.30), (r, g0), (r - gp, g0 + 0.01), (r - gp, g1 - 0.01), (r, g1), (r, H - 0.012)] + \
        [(round(r - 0.012 + 0.012 * math.cos(math.radians(a)), 5), round(H - 0.012 + 0.012 * math.sin(math.radians(a)), 5))
         for a in (60, 30)] + [(r * 0.6, H), (0.0, H)]
    bandes = f"{g1:.3f} {H + 0.01:.3f} blanc_ral9010" if tete_blanche else ""
    return prof, bandes


for H in (1.00, 1.20):
    for tb in (False, True):
        prof, bandes = _potelet_gorge(H, tb)
        ASSETS.append(_revol(
            f"potelet_gorge_D102_H{int(H * 100)}{'_tete_blanche' if tb else ''}", "potelets", prof, bandes,
            [src("angers_cpu", note="fiche potelet-a-gorge (27/06/2018) : Ø 10,16 cm, tube 3,65 mm, H 1 m hors sol (1,20 m aux "
                                    "traversées), RAL 7016 sablé-givré, tête blanche RAL 9010 aux passages piétons"),
             src("arrete2007", note="partie contrastée d'au moins 10 cm en partie haute des bornes et poteaux de H ≤ 1,30 m")],
            "moyenne", dict(diametre_m=0.1016, hauteur_hors_sol_m=H, scellement_modele_m=0.30), "acier_thermolaque_7016",
            note="forme et position de la gorge estimées (non cotées) ; 0,30 m de fût sous le sol pour le scellement"))
_r0, _r1 = 0.04, 0.03
ASSETS.append(_revol("potelet_fonte_conique_H100", "potelets",
                     [(0.0, -0.25), (_r0, -0.25), (_r0, 0.0), (_r0, 0.02), (_r1 + 0.002, 0.97), (_r1, 0.985), (0.02, 1.0), (0.0, 1.0)],
                     "0.88 1.01 blanc_ral9010",
                     [src("angers_cpu", note="fiche potelets-2 « potelet à motifs ligneux » : fonte GS RAL 7016, H 1 m hors sol, "
                                             "embase Ø 8 cm, extrémité haute Ø 6 cm"),
                      src("arrete2007", note="partie haute contrastée ≥ 10 cm")], "moyenne",
                     dict(diametre_base_m=0.08, diametre_haut_m=0.06, hauteur_hors_sol_m=1.0), "acier_thermolaque_7016",
                     note="motifs ligneux non modélisés (fût conique lisse) ; tête blanche de 12 cm"))

# ---------------------------------------------------------------------------------------------- supports de signalisation
def _poteau(id_, section, d1, d2, H, platine=None, serrage=None, bande=True, bouchon=True, sources=(), confiance="haute",
            note=None, mat="acier_galvanise"):
    params = dict(section=section, d1=d1, d2=d2, hauteur=H, platine=1 if platine else 0, serrage=1 if serrage else 0,
                  bande_contrastee=1 if bande else 0, bouchon=1 if bouchon else 0, materiau=mat)
    if platine:
        params.update(platine_cote=platine[0], platine_ep=platine[1])
    if serrage:
        params.update(serrage_diam=serrage[0], serrage_ep=serrage[1])
    dims = dict(hauteur_m=H, section=section, d1_m=d1, d2_m=d2)
    return dict(id=id_, famille="supports", type=id_.replace("_", " "), hda="route::poteau", params=params, dimensions=dims,
                sources=list(sources), confiance=confiance, materiau=mat, note=note)


S_IISR1_6 = src("iisr1", 15, article="art. 6 B 1°", note="supports d'accotement : rectangulaires 40 × 27, 40 × 40, 80 × 40, 80 × 80 mm ; "
                                                          "ronds Ø 48,3 - 60,3 - 76 mm ; mâts directionnels Ø 76-89-114-140-168 mm")
S_ARR_BANDE = src("arrete2007", note="bande contrastée ≥ 10 cm entre 1,20 et 1,40 m sur les poteaux des cheminements")
for d in (0.0483, 0.0603, 0.076):
    for H in (3.0, 3.5):
        ASSETS.append(_poteau(f"support_rond_D{int(round(d * 1000))}_H{int(H * 10):02d}", "rond", d, d, H,
                              serrage=(0.155, 0.0027) if abs(d - 0.0603) < 1e-3 else None,
                              sources=[S_IISR1_6, S_ARR_BANDE,
                                       src("angers_cpu", note="poteau Ø 60 galvanisé ou RAL 7016, platine de serrage Ø 155 × 2,7 mm")
                                       if abs(d - 0.0603) < 1e-3 else src("iisr1", 19, article="art. 9 b",
                                                                          note="hauteur sous panneau jusqu'à 2,30 m en agglomération")],
                              note="longueur hors sol ; hauteur sous panneau 2,30 m max en agglomération (IISR 1 art. 9 b, p. 19)"))
for (a, b) in ((0.040, 0.027), (0.040, 0.040), (0.080, 0.040), (0.080, 0.080)):
    ASSETS.append(_poteau(f"support_rect_{int(a * 1000)}x{int(b * 1000)}_H30", "rect", a, b, 3.0, sources=[S_IISR1_6, S_ARR_BANDE]))
for d in (0.089, 0.114):
    ASSETS.append(_poteau(f"mat_directionnel_D{int(d * 1000)}_H40", "rond", d, d, 4.0, platine=(0.30, 0.02),
                          sources=[S_IISR1_6, {"doc": "estimation", "note": "platine 300 × 300 × 20 mm"}], confiance="moyenne"))
ASSETS.append(_poteau("support_rond_D60_platine_H30", "rond", 0.0603, 0.0603, 3.0, platine=(0.20, 0.003),
                      sources=[S_IISR1_6, {"doc": "Virages, fourreau platine (usinenouvelle.com)",
                                           "url": "https://www.usinenouvelle.com/expo/fourreau-platine-p99370678.html",
                                           "note": "platine 200 × 200 × 3 mm, 4 trous Ø 20, pour rond Ø 60"}], confiance="moyenne"))
ASSETS.append(_poteau("mat_feux_D90_H34", "rond", 0.090, 0.090, 3.4, platine=(0.30, 0.015),
                      sources=[src("trafic_feux", 1, note="fiche 160983 : option « poteau acier galvanisé D90 mm »"),
                               src("feux_json", note="mâts de 3,4 m observés au carrefour (bas de tête ≈ 2,35 m)"),
                               src("iisr6", 11, figure="fig. 16", note="gabarit 2,00 m sous les feux sur trottoir ; axe du feu supérieur < 4,20 m")],
                      confiance="moyenne", note="platine 300 × 300 × 15 estimée"))

# ---------------------------------------------------------------------------------------------- feux
def _feu(id_, n, disposition, diam, couleurs, boitier, visiere, sources, confiance, note=None, pictos="", diam_haut=0.0, carre=0):
    params = dict(nb_feux=n, disposition=disposition, diametre=diam, diametre_haut=diam_haut, optique_carree=carre,
                  couleurs=couleurs, pictos=pictos,
                  boitier_l=boitier[0], boitier_h=boitier[1], boitier_p=boitier[2], visiere=visiere)
    return dict(id=id_, famille="feux", type=id_.replace("_", " "), hda="route::feu", params=params,
                dimensions=dict(diametre_optique_m=diam, module_l_m=boitier[0], module_h_m=boitier[1], module_p_m=boitier[2],
                                visiere_m=visiere, nb_feux=n),
                sources=sources, confiance=confiance, materiau="plastique_noir_feux", note=note)


S_DIAM = src("iisr6", 10, article="art. 109-4", note="feux circulaires principaux pour véhicules : Ø 200 ou 300 mm ; ensemble mixte "
                                                       "rouge 300 + jaune et vert 200 admis ; directionnels le plus souvent 300")
S_TRAFIC = src("trafic_feux", 1, note="feu simple D200 : 240 (h) × 265 (l) mm, visière 200 mm ; tricolore D200 : 865 × 265 × 250 "
                                      "(+ 200 avec visière)")
ASSETS += [
    _feu("feu_R11v_D200", 3, 0, 0.20, "rouge jaune vert", (0.265, 0.24, 0.25), 0.20, [S_DIAM, S_TRAFIC,
         src("iisr6", 5, figure="fig. 1", note="R11v : trois feux circulaires rouge, jaune, vert (vert en bas)")], "moyenne"),
    _feu("feu_R11v_D300", 3, 0, 0.30, "rouge jaune vert", (0.38, 0.35, 0.30), 0.28, [S_DIAM,
         {"doc": "estimation", "note": "boîtier Ø 300 extrapolé du D200 (+ 115 mm)"}], "estimation"),
    _feu("feu_R11v_mixte_R300", 3, 0, 0.20, "rouge jaune vert", (0.265, 0.24, 0.25), 0.20, [S_DIAM, S_TRAFIC], "moyenne",
         diam_haut=0.30, note="ensemble mixte : module rouge Ø 300 (module 200 mis à l'échelle × 1,5 : 0,40 × 0,36 × 0,375 m, "
                              "visière 0,30) sur jaune et vert Ø 200"),
    _feu("feu_R12_D200_horizontal", 2, 1, 0.20, "pieton_rouge pieton_vert", (0.265, 0.24, 0.25), 0.20, [S_TRAFIC,
         src("iisr6", 5, article="art. 109-3 A", figure="fig. 2",
             note="R12 : deux feux vert et rouge, « normalement disposés dans cet ordre de droite à gauche » (vert à droite, "
                  "rouge à gauche pour le piéton qui fait face) ; éventuellement l'un au-dessus de l'autre, le vert en bas")],
         "moyenne", pictos="pieton_arret pieton_marche", carre=1,
         note="couleurs listées de gauche à droite vu de face : rouge à gauche, vert à droite (corrigé le 16/10/2026 : la "
              "1re fabrication inversait les côtés) ; optiques carrées 200 × 200 (fig. 2) ; figurines non modélisées"),
    _feu("feu_R12_D200_vertical", 2, 0, 0.20, "pieton_rouge pieton_vert", (0.265, 0.24, 0.25), 0.20, [S_TRAFIC,
         src("iisr6", 5, figure="fig. 2")], "moyenne", pictos="pieton_arret pieton_marche", carre=1,
         note="disposition verticale admise (vert en bas) ; optiques carrées ; figurines non modélisées"),
    _feu("feu_R13c_D200", 3, 0, 0.20, "rouge jaune vert", (0.265, 0.24, 0.25), 0.20, [S_TRAFIC,
         src("iisr6", 6, figure="fig. 3", note="R13 : trois feux vert, jaune, rouge de bas en haut, munis d'un même pictogramme "
                                               "(cycle R13c, BUS R13b)")], "moyenne", pictos="cycle cycle cycle"),
    _feu("feu_R13b_D200", 3, 0, 0.20, "rouge jaune vert", (0.265, 0.24, 0.25), 0.20, [S_TRAFIC, src("iisr6", 6, figure="fig. 3")],
         "moyenne", pictos="bus bus bus"),
    _feu("feu_repetiteur_R11v_D90", 3, 0, 0.09, "rouge jaune vert", (0.12, 0.115, 0.10), 0.06, [
        src("iisr6", 35, note="feux répétiteurs de dimension réduite, généralement 90 mm (R22 ; même valeur pour R23 p. 36)"),
        src("iisr6", 10, figure="fig. 13-14", note="signaux répétés en partie basse du même support, orientés vers les premiers "
                                                   "véhicules arrêtés")], "moyenne", note="boîtier 120 × 115 × 100 estimé"),
]

# ---------------------------------------------------------------------------------------------- ossatures (garde-corps, barrières, potence)
def _ossature(id_, famille, modele, params, dims, sources, confiance, mat, note=None):
    p = dict(modele=modele, **params)
    return dict(id=id_, famille=famille, type=id_.replace("_", " "), hda="route::ossature", params=p, dimensions=dims,
                sources=sources, confiance=confiance, materiau=mat, note=note)


S_S8 = src("setra_gc", 68, note="modèle S8 : main courante 120 × 55 × 4, montants 80 × 40 × 4 tous les 1,50 m, lisse inférieure "
                                "60 × 30 × 2,7, barreaux 30 × 30 × 1,5 ; hauteur des montants 1,0 m (note de calcul p. 73)")
S_GC_ESP = src("setra_gc", 13, note="espacement entre barreaux : 15 cm maximum (XP P 98-405), 11 cm dans les normes bâtiment")
for L in (1.5, 3.0):
    ASSETS.append(_ossature(f"garde_corps_pont_S8_L{int(L * 10):02d}", "garde_corps", 0,
                            dict(longueur=L, hauteur=1.0, entraxe_montants=1.5, entraxe_barreaux=0.14, lisse_basse=0.10),
                            dict(longueur_m=L, hauteur_m=1.0), [S_S8, S_GC_ESP,
                                                                src("cerema_gc_cycles", 1, note="1 m suffit pour les piétons ; "
                                                                                               "1,20 m à 1,40 m en présence de cycles")],
                            "haute", "acier_galvanise", note="vide entre barreaux 0,11 m ; hauteur de la lisse basse (0,10 m) estimée"))
ASSETS.append(_ossature("garde_corps_pont_S8_cycles_L30", "garde_corps", 0,
                        dict(longueur=3.0, hauteur=1.2, entraxe_montants=1.5, entraxe_barreaux=0.14, lisse_basse=0.10),
                        dict(longueur_m=3.0, hauteur_m=1.2), [S_S8, S_GC_ESP, src("cerema_gc_cycles", 1)], "moyenne",
                        "acier_galvanise", note="variante 1,20 m (pistes cyclables) : sections S8 conservées"))
ASSETS.append(_ossature("garde_corps_urbain_L20", "garde_corps", 1,
                        dict(longueur=2.0, hauteur=1.0, entraxe_montants=1.0, entraxe_barreaux=0.13, lisse_basse=0.10),
                        dict(longueur_m=2.0, hauteur_m=1.0),
                        [src("angers_cpu", note="fiche garde-corps : montants fer plat 40 × 15, barreaux ronds Ø 20, main courante "
                                                "fer plat 40 × 10 sur carré 20 × 20, acier galvanisé thermolaqué RAL 7016"),
                         src("cerema_gc_cycles", 1, note="hauteur 1 m pour les piétons")], "moyenne", "acier_thermolaque_7016",
                        note="entraxe des montants (1,0 m) et des barreaux (0,13 m) estimés"))
for L in (1.0, 1.5):
    ASSETS.append(_ossature(f"barriere_croix_st_andre_L{int(L * 100)}", "barrieres", 2,
                            dict(longueur=L, hauteur=1.0, entraxe_montants=L, entraxe_barreaux=0.0, lisse_basse=0.10),
                            dict(longueur_m=L, hauteur_m=1.0),
                            [src("angers_cpu", note="fiche barriere-croix-saint-andre (12/10/2018) : H 1 m, L 1 m et 1,50 m, acier "
                                                    "galvanisé RAL 7016 sablé-givré, 23 kg"),
                             src("grandlyon_barriere", 2, note="barrière à croix : cadre 1325 × 900, montants 50, croix 25"),
                             src("arrete2007", note="élément bas à 0,40 m du sol au plus")], "moyenne", "acier_thermolaque_7016",
                            note="cadre de 0,90 m entre 0,10 et 1,00 m (Lyon) ; section des montants 50 × 50 supposée carrée"))
ASSETS.append(_ossature("barriere_lyon_1530", "barrieres", 3,
                        dict(longueur=1.53, hauteur=0.90, entraxe_montants=1.53, entraxe_barreaux=0.0, lisse_basse=0.10),
                        dict(longueur_m=1.53, hauteur_m=0.90),
                        [src("grandlyon_barriere", 2, note="barrière 1530 × 900, montants Ø 60, anneau central Ø 140, main courante "
                                                           "débordante de 140")], "moyenne", "acier_thermolaque_7016",
                        note="hauteur hors sol 0,90 m + main courante ; diamètres des croisillons estimés à 20 mm"))
ASSETS.append(_ossature("potence_feux_L45", "supports", 4,
                        dict(longueur=4.5, hauteur=6.0, entraxe_montants=0.0, entraxe_barreaux=0.0, lisse_basse=0.0),
                        dict(portee_m=4.5, hauteur_mat_m=6.0, diametre_mat_m=0.168, diametre_crosse_m=0.114),
                        [S_IISR1_6, src("iisr1", 19, article="art. 9 c", note="au-dessus de la chaussée : gabarit de la route + 0,10 m "
                                                                              "(entretien) + 0,50 m (protection)"),
                         {"doc": "estimation", "note": "mât Ø 168, crosse Ø 114, portée 4,5 m, hauteur 6,0 m : à sourcer (catalogue)"}],
                        "estimation", "acier_galvanise", note="potence de feux : géométrie de principe, cotes à sourcer"))

# ---------------------------------------------------------------------------------------------- matériaux simples (maison)
MATERIAUX_SIMPLES = {
    "blanc_ral9010": dict(couleur_srgb=[0xF1, 0xEC, 0xE1], rugosite=0.45, metal=0.0, note="RAL 9010 blanc pur (tête de potelet)"),
    "bev_blanc": dict(couleur_srgb=[0xEE, 0xEE, 0xE8], rugosite=0.6, metal=0.0, note="résine méthacrylate blanche (Angers CPU)"),
    "feu_lentille_rouge": dict(couleur_srgb=[0x4A, 0x0F, 0x0C], emission_srgb=[0xFF, 0x24, 0x10], rugosite=0.15, metal=0.0,
                               note="feux.json couleurs.lentille_eteinte_rouge / emission.rouge"),
    "feu_lentille_jaune": dict(couleur_srgb=[0x4D, 0x3A, 0x0E], emission_srgb=[0xFF, 0xA8, 0x00], rugosite=0.15, metal=0.0),
    "feu_lentille_vert": dict(couleur_srgb=[0x0E, 0x3A, 0x30], emission_srgb=[0x00, 0xE0, 0xA8], rugosite=0.15, metal=0.0),
    "feu_lentille_pieton_rouge": dict(couleur_srgb=[0x4A, 0x0F, 0x0C], emission_srgb=[0xFF, 0x24, 0x10], rugosite=0.15, metal=0.0),
    "feu_lentille_pieton_vert": dict(couleur_srgb=[0x0E, 0x3A, 0x30], emission_srgb=[0x00, 0xE0, 0xA8], rugosite=0.15, metal=0.0),
    "feu_corps_gris": dict(couleur_srgb=[0xD5, 0xD6, 0xD2], rugosite=0.5, metal=0.0, note="RAL 7035 (modules observés, feux.json)"),
}
# matériaux de bibliothèque (USD) : route_fr ou assets/lib/materiaux
MATERIAUX_LIB_EXISTANTS = {"beton_bordure", "paves_granit", "bev_podotactile", "calcaire_bordure"}


def assets():
    return ASSETS


if __name__ == "__main__":
    import collections
    c = collections.Counter(a["famille"] for a in ASSETS)
    print(len(ASSETS), "assets :", dict(c))
    ids = [a["id"] for a in ASSETS]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    for k, p in PROFILS.items():
        print(f"{k:14s} {len(p['pts']):3d} pts  base {p['base']:.3f}  H {p['H']:.3f}")
