"""Catalogue des matériaux UE du sol V2 : source unique pour la préparation des textures (hors éditeur),
la construction des matériaux et l'étalonnage (dans l'éditeur). Python pur, sans numpy.

Chaque materiau_id de assets/specs/materiaux_sol.json donne /Game/PJ/Materials/MI_<id> (maître M_PJ_Sol,
M_PJ_Bordure ou M_PJ_Remplissage), plus les variantes MI_<id>__carla (CARLA, CC-BY 4.0) et MI_<id>__citysample
(City Sample, réservé à Unreal). La peinture routière donne MI_PJ_Peinture_<couleur>_u<usure> (M_PJ_Peinture).
L'albédo est calé sur albedo_cible_lineaire : Luminosite (rapport de luminance Y) × Teinte (chromie), à partir
de la moyenne linéaire mesurée de la texture (mesures_textures.json), puis corrigé par la mesure dans UE
(capture « base color » vue de dessus, etalonnage.json).
"""
from __future__ import annotations

import json
import os

ICI = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
DEPOT = os.path.abspath(os.path.join(ICI, '..', '..', '..', '..')).replace('\\', '/')
SPEC = f'{DEPOT}/assets/specs/materiaux_sol.json'
SPEC_PEINTURE = f'{DEPOT}/assets/specs/peinture.json'
SPEC_BORDURES = f'{DEPOT}/assets/specs/bordures.json'
SPEC_RENDU = f'{DEPOT}/assets/specs/materiaux_rendu_v2.json'
CC0_DIR = f'{DEPOT}/assets/lib/materiaux'
CACHE_CC0 = f'{DEPOT}/data/raw/assets_src/cc0'
DERIVE_DIR = f'{DEPOT}/data/raw/assets_src/cc0_derive'          # hauteurs, bruit, masque (non versionné)
CS_DIR = f'{DEPOT}/recon/pc/citysample/textures'                 # PNG City Sample (non versionné, UE seul)
MESURES = f'{ICI}/mesures_textures.json'
ETALONNAGE = f'{ICI}/etalonnage.json'
OUT = f'{DEPOT}/recon/out/paquet_jardin/v2/ue_materiaux'

UE_TEX_CC0 = '/Game/PJ/Textures/CC0'
UE_TEX_CS = '/Game/PJ/Textures/CitySample'
UE_TEX_PJ = '/Game/PJ/Textures/PJ'
UE_MAT = '/Game/PJ/Materials'
UE_MAITRES = '/Game/PJ/Materials/Maitres'
MAITRES = {'sol': f'{UE_MAITRES}/M_PJ_Sol', 'bordure': f'{UE_MAITRES}/M_PJ_Bordure', 'eclat': f'{UE_MAITRES}/M_PJ_Eclat',
           'touffe': f'{UE_MAITRES}/M_PJ_Touffe',
           'remplissage': f'{UE_MAITRES}/M_PJ_Remplissage', 'peinture': f'{UE_MAITRES}/M_PJ_Peinture'}
T_BRUIT = f'{UE_TEX_PJ}/T_PJ_BruitMacro'
T_MASQUE_PEINTURE = f'{UE_TEX_PJ}/T_PJ_MasqueUsurePeinture'

# ------------------------------------------------------------------ affectation des maîtres
BORDURES = ('beton_bordure_gris', 'beton_bordure_clair', 'granit_bordure', 'calcaire_bordure', 'caniveau_beton')
REMPLISSAGES = ('brf_bois_concasse', 'brf_bois_gris', 'gravier_concasse_6_10', 'gravillons_ilot', 'galets_20_40',
                'paillage_mineral')
# amplitude du déplacement Nanite (cm, crête à crête) : ~ taille des éléments de la couche (materiaux_sol.json couche.elements_m) ;
# BRF : copeaux couchés à plat (4 cm étiraient la texture sur les flancs des copeaux de la tuile de 4 m)
DEPLACEMENT_CM = {'brf_bois_concasse': 2.5, 'brf_bois_gris': 3.5, 'gravier_concasse_6_10': 2.5, 'gravillons_ilot': 1.8,
                  'galets_20_40': 2.5, 'paillage_mineral': 2.5}
# salissure des bordures (bordures_elements.json aspect.salissure : neuf 0,15 / ancien 0,45 ; caniveau 0,5-0,8)
SALISSURE_BORDURE = {'beton_bordure_gris': 0.45, 'beton_bordure_clair': 0.15, 'granit_bordure': 0.3,
                     'calcaire_bordure': 0.15, 'caniveau_beton': 0.65}
# assombrissement des bordures à salissure s : x (1 - K_SAL * s * w), w = 1 au pied, SALISSURE_HAUT sur la tête
K_SAL = 0.35
SALISSURE_HAUT = 0.25
TEINTE_SALISSURE_BORDURE = (0.85, 0.80, 0.72)   # teinte de la salissure (multiplicatif à s = 1)

# réglages d'aspect par famille (surchargés par id) : macro = variation lente de luminance, anti-répétition =
# second échantillonnage tourné de 37° et mis à l'échelle EchelleB, mélangé par un bruit lent.
REGLAGES_FAMILLE = {
    'enrobe': dict(AntiRepetition=0.6, MacroForce=0.10, MacroEchelleM=9.0, NormalForce=1.0, Salissure=0.0),
    'resine': dict(AntiRepetition=0.5, MacroForce=0.08, MacroEchelleM=7.0, NormalForce=0.8),
    'beton': dict(AntiRepetition=0.5, MacroForce=0.08, MacroEchelleM=6.0, NormalForce=1.0),
    'mineral': dict(AntiRepetition=0.6, MacroForce=0.10, MacroEchelleM=5.0, NormalForce=1.0),
    'vegetal': dict(AntiRepetition=0.7, MacroForce=0.22, MacroEchelleM=4.0, NormalForce=1.0),
    'bordure': dict(MacroForce=0.08, MacroEchelleM=1.3, NormalForce=1.0, VariationTeinte=0.04, JointLargeurCm=0.5),
}
FAMILLE = {
    **{k: 'enrobe' for k in ('enrobe_bbsg_ancien', 'enrobe_bbsg_neuf_2025', 'enrobe_reprise_tranchee', 'enrobe_piste_cyclable',
                             'enrobe_trottoir', 'enrobe_clair_granulats', 'enrobe_colore_ocre')},
    **{k: 'resine' for k in ('resine_verte', 'resine_cyan')},
    **{k: 'beton' for k in ('beton_balaye', 'beton_desactive', 'dalles_beton', 'paves_beton', 'paves_granit', 'bev_podotactile',
                            'beton_galets')},
    **{k: 'mineral' for k in REMPLISSAGES + ('stabilise_beige',)},
    **{k: 'vegetal' for k in ('gazon_tondu', 'herbe_haute', 'gazon_sec', 'noue_plantee', 'terre_nue', 'feuilles_mortes')},
    **{k: 'bordure' for k in BORDURES},
}
REGLAGES_ID = {
    # le BEV et les pavés ont un motif régulier : pas d'anti-répétition tournée (le motif doit rester aligné)
    'bev_podotactile': dict(AntiRepetition=0.0, MacroForce=0.05),
    'paves_granit': dict(AntiRepetition=0.0),
    'paves_beton': dict(AntiRepetition=0.0),
    'dalles_beton': dict(AntiRepetition=0.0),
    'enrobe_bbsg_ancien': dict(Salissure=0.12),
    # trottoir : grain d'Asphalt031 resserré (source remplacée, voir SOURCE_UE)
    # trottoir : source, tuile et albédo de la revue Karma (RENDU_UE : Asphalt015 à 1,6 m, 0,15)
    'enrobe_trottoir': dict(Salissure=0.10, Contraste=0.9),
    # bordures préfabriquées : Concrete037 (béton à gros granulats roulés) resserré et adouci -> béton fin de
    # bordure des photos 1 à 3 (mouchetures de 2-5 mm, taches lentes) ; réglé sur captures (vues v1 à v3)
    # (revue UE du 10/10 : Concrete037 = béton désactivé à granulats de 5-15 mm en gros plan) : béton fin City Sample
    # (BETON_BORDURE_UE), moucheté de 1-3 mm comme les photos 2 et 3
    # (gros plans des joints : a TileM 1,5 et normale 0,6, pores de 5-10 mm et relief de crepi) : TileM 1,0, normale 0,25
    'beton_bordure_gris': dict(TileM=1.0, Contraste=0.7, NormalForce=0.25, MacroForce=0.08, AOForce=0.0),
    'beton_bordure_clair': dict(TileM=1.0, Contraste=0.7, NormalForce=0.25, MacroForce=0.08, AOForce=0.0),
    'caniveau_beton': dict(TileM=0.7, Contraste=0.6, NormalForce=0.55, MacroForce=0.08, BasHauteurCm=10.0),
    'granit_bordure': dict(TileM=0.4, Contraste=1.0, NormalForce=0.6, MacroForce=0.06),
    'calcaire_bordure': dict(Contraste=0.8, NormalForce=0.6),
    # remplissages : éléments agrandis vers les photos 2 (BRF 3-8 cm, allongés) et 3 (gravier ~2 cm), contraste relevé
    # BRF et concassé : fond sous les éclats 3D (tuile et albédo de la revue Karma, RENDU_UE)
    'brf_bois_concasse': dict(Contraste=1.4),
    'brf_bois_gris': dict(TileM=2.6, Contraste=1.3),
    'gravier_concasse_6_10': dict(Contraste=1.35, NormalForce=1.2),
    'gravillons_ilot': dict(TileM=2.6, Contraste=1.2),
}
# second lit mêlé au premier (M_PJ_Remplissage, switch statique Melange) : vieillissement du BRF (materiaux_sol.json
# couche.vieillissement : brf_bois_gris par masque de bruit). Masque = bruit lent (T_PJ_BruitMacro R, uniforme) décalé par
# la hauteur du lit 2 (bords qui suivent les copeaux) ; taux = part de surface. La cible est celle du lit vu (mélange) :
# le lit 2 garde sa couleur propre x gain (albédo final), le lit 1 (Luminosite x Teinte) complète (calage_melange).
MELANGE = {
    'brf_bois_concasse': dict(dossier='brf_bois_gris', taux=0.2, gain=0.7, tile_m=2.8, contraste=1.0, echelle_m=2.0,
                              transition=0.2, hauteur=0.8),
}
# texture CC0 utilisée dans UE quand la source déclarée par materiaux_sol.json rend mal (proxy déclaré ; Karma inchangé)
SOURCE_UE = {
    'granit_bordure': ('beton_bordure', "PavingStones119 dessine des pavés (joints) sur la bordure ; Concrete037 à 0,4 m "
                                        "donne le moucheté d'un granit bouchardé"),
}

# surcharges de rendu de la revue de réalisme Karma (assets/specs/materiaux_rendu_v2.json, pj_commun.materiau_rendu)
# reportées dans UE (revue UE du 10/10 : enrobé ancien à 0,26 plus clair que le trottoir, gazon saturé, gravier à 0,31) :
# source CC0 (textures), tuile, albédo = moyenne de la texture source x facteur_albedo (ou albedo_cible / moyenne)
# x gain_rvb, exactement comme Karma
RENDU_UE = ('enrobe_bbsg_ancien', 'enrobe_trottoir', 'gazon_tondu', 'brf_bois_concasse', 'gravier_concasse_6_10',
            'bev_podotactile')
# béton des bordures neuves et anciennes : texture City Sample (Unreal seulement, EULA) au lieu de Concrete037
BETON_BORDURE_UE = {'beton_bordure_gris': 'concrete_rough_2x2', 'beton_bordure_clair': 'concrete_rough_2x2'}
# éclats 3D des remplissages (M_PJ_Eclat) : palette par instance reprise de recon/pcg/houdini/pj_ilot.py (BRF_COULEURS,
# GRAVIER_COULEURS : albédo par éclat [min, max] x gain RVB, parts), détail de texture et fibres
ECLATS = {
    'MI_eclat_brf': dict(source='MI_brf_bois_concasse', classes=[(0.48, (0.26, 0.40), (1.0, 0.80, 0.58)),
                                                                 (0.40, (0.045, 0.085), (1.0, 0.70, 0.50)),
                                                                 (0.12, (0.18, 0.28), (1.0, 0.88, 0.74))],
                         TileM=0.35, DetailForce=0.6, FibreForce=0.55, FibreU=6.0, FibreV=90.0, NormalForce=0.8, Rugosite=0.8),
    'MI_eclat_gravier': dict(source='MI_gravier_concasse_6_10', classes=[(0.55, (0.14, 0.21), (1.0, 0.98, 0.93)),
                                                                         (0.32, (0.22, 0.30), (1.0, 0.98, 0.93)),
                                                                         (0.13, (0.32, 0.40), (1.0, 0.98, 0.93))],
                             TileM=0.05, DetailForce=0.8, FibreForce=0.0, FibreU=1.0, FibreV=1.0, NormalForce=1.5, Rugosite=0.75),
}


def surcharge_rendu(mid):
    """Spec de rendu Karma d'un materiau_id de RENDU_UE (même calcul que recon/pcg/houdini/pj_commun.materiau_rendu) :
    {dossier, tile_m, cible, source} ; None hors RENDU_UE."""
    if mid not in RENDU_UE:
        return None
    sp = spec()
    m = dict(sp[mid])
    s = (charger_json(SPEC_RENDU) or {}).get('surcharges', {}).get(mid) or {}
    fa = m.get('facteur_albedo')
    if s.get('source'):
        src = sp[s['source']]
        for k in ('source_cc0', 'tile_m', 'texture_mesuree'):
            m[k] = src[k]
        fa = None
    tile = float(s.get('tile_m', m['tile_m']))
    moy = (m.get('texture_mesuree') or {}).get('albedo_moyen_lineaire') or [0.3, 0.3, 0.3]
    if 'facteur_albedo' in s:
        fa = s['facteur_albedo']
    if 'albedo_cible' in s:
        f = float(s['albedo_cible']) / max(sum(moy) / 3.0, 1e-3)
        fa = [f, f, f]
    if 'gain_rvb' in s:
        fa = [float(a) * float(g) for a, g in zip(fa or [1.0, 1.0, 1.0], s['gain_rvb'])]
    fa = fa or [1.0, 1.0, 1.0]
    return {'dossier': m['source_cc0']['nom'], 'tile_m': tile, 'cible': [round(moy[i] * fa[i], 4) for i in range(3)],
            'source': s.get('source') or mid, 'raison': s.get('raison')}


def cible_effective(mid):
    """Albédo visé dans UE : surcharge de rendu (RENDU_UE) sinon materiaux_sol.json."""
    sr = surcharge_rendu(mid)
    return sr['cible'] if sr else spec()[mid].get('albedo_cible_lineaire')


# ------------------------------------------------------------------ variantes CARLA (CC-BY 4.0, CARLA Team / CVC)
# MI enfant du MI CARLA (aspect CARLA conservé) ; seul le paramètre de luminosité est étalonné sur la cible.
# 'pebbles' : textures seules (dh = albédo + hauteur en alpha, ORM) sur M_PJ_Remplissage.
GM = '/Game/Carla/Static/GenericMaterials'
CARLA = {
    'enrobe_bbsg_ancien': dict(mi=f'{GM}/Asphalt/MI_Asphalt08'),
    'enrobe_bbsg_neuf_2025': dict(mi=f'{GM}/Asphalt/MI_Asphalt08'),
    'enrobe_piste_cyclable': dict(mi=f'{GM}/Asphalt/MI_Asphalt08'),
    'enrobe_trottoir': dict(mi=f'{GM}/Sidewalk/MI_Sidewalk_02'),
    'enrobe_clair_granulats': dict(mi=f'{GM}/Concrete/MI_Concrete_03'),
    'beton_balaye': dict(mi=f'{GM}/Concrete/MI_Concrete_01'),
    'beton_desactive': dict(mi=f'{GM}/Concrete/MI_Concrete_05'),
    'dalles_beton': dict(mi=f'{GM}/Sidewalk/MI_Sidewalk_Residential'),
    'paves_beton': dict(mi=f'{GM}/Sidewalk/MI_Sidewalk_11'),
    'paves_granit': dict(mi=f'{GM}/Brick/MI_Brick05'),
    'beton_bordure_gris': dict(mi=f'{GM}/Gutters_Curbs/Curb/MI_dirtyCurb'),
    'beton_bordure_clair': dict(mi=f'{GM}/LargeMap_materials/largeM_curb/MI_largeM_curb01_2'),
    'caniveau_beton': dict(mi=f'{GM}/Gutters_Curbs/Gutter/MI_dirtyGutter'),
    'brf_bois_concasse': dict(mi=f'{GM}/Ground/MI_Dirt'),
    'stabilise_beige': dict(mi=f'{GM}/Ground/MI_Dirt'),
    'terre_nue': dict(mi=f'{GM}/Ground/MI_Dirt'),
    'gazon_tondu': dict(mi=f'{GM}/Ground/MI_Grass_Cutted_2'),
    'herbe_haute': dict(mi=f'{GM}/Ground/MI_Grass_Park'),
    'gazon_sec': dict(mi=f'{GM}/Ground/MI_LargeLandscape_Grass_2'),
    'noue_plantee': dict(mi=f'{GM}/Ground/MI_Grass_Park_2'),
    'gravier_concasse_6_10': dict(textures='T_Pebbles_01', tile_m=1.5),
    'gravillons_ilot': dict(textures='T_Pebbles_02', tile_m=1.5),
    'galets_20_40': dict(textures='T_Pebbles_01', tile_m=2.0),
}
CARLA_HD = f'{GM}/Ground/Textures/HD'
# paramètre de luminosité par maître CARLA (multiplicatif sur l'albédo) et type
CARLA_LUMINOSITE = {
    'M_MaterialMaster': ('Brightness', 'scalaire'),
    'M_GenericMaterialMaster': ('Brightness', 'scalaire'),
    'M_TileTextureMaster': ('MaterialColor', 'vecteur'),
    'M_BuildingMaterial': ('Color Adjustement', 'vecteur'),
}

# ------------------------------------------------------------------ variantes City Sample (UE seul, EULA Unreal)
# fichiers de recon/pc/citysample/textures (préparés en 2048 px, normales OpenGL) ; tuile 2 m (Megascans 2x2)
CITYSAMPLE = {
    'enrobe_bbsg_ancien': dict(albedo='asphalt_road_03_albedo', normale='asphalt_road_03_normal', rugosite='asphalt_road_03_roughness'),
    'enrobe_piste_cyclable': dict(albedo='asphalt_road_02_albedo', normale='asphalt_road_02_normal', rugosite='asphalt_road_02_roughness'),
    'enrobe_bbsg_neuf_2025': dict(albedo='asphalt_fresh_00_albedo', normale='asphalt_road_02_normal', rugosite='asphalt_road_02_roughness'),
    'enrobe_reprise_tranchee': dict(albedo='asphalt_road_02_albedo', normale='asphalt_road_02_normal', rugosite='asphalt_road_02_roughness'),
    'enrobe_trottoir': dict(albedo='asphalt_dried01_albedo', normale='asphalt_dried01_normal', rugosite='asphalt_dried01_aomrd_rugosite'),
    'dalles_beton': dict(albedo='concrete_rough_2x2_albedo', normale='concrete_rough_2x2_normal', rugosite='concrete_rough_2x2_aomrd_rugosite'),
    'beton_balaye': dict(albedo='concrete_rough_2x2_albedo', normale='concrete_rough_2x2_normal', rugosite='concrete_rough_2x2_aomrd_rugosite'),
    'beton_bordure_gris': dict(albedo='concrete_dirty_albedo', normale='concrete_dirty_normal', rugosite='concrete_dirty_aormd_rugosite'),
    'beton_bordure_clair': dict(albedo='concrete_dirty_albedo', normale='concrete_dirty_normal', rugosite='concrete_dirty_aormd_rugosite'),
    'caniveau_beton': dict(albedo='concrete_dirty_albedo', normale='concrete_dirty_normal', rugosite='concrete_dirty_aormd_rugosite'),
}
CITYSAMPLE_TILE_M = 2.0

# ------------------------------------------------------------------ peinture (assets/specs/peinture.json)
PEINTURE_COULEURS = ('blanc', 'jaune')
PEINTURE_USURES = ('0', '1', '2', '3', 'F')
PEINTURE_SOL = 'enrobe_bbsg_ancien'          # enrobé sous la peinture (grain et relief transmis)


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def charger_json(p, defaut=None):
    if not os.path.exists(p):
        return defaut
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def spec():
    return charger_json(SPEC)['materiaux']


def dossiers_cc0():
    """Dossiers de assets/lib/materiaux utilisés par un materiau_id (ordre trié)."""
    return sorted({m['source_cc0']['nom'] for m in spec().values() if m.get('source_cc0')})


def maitre(mid):
    if mid in BORDURES:
        return 'bordure'
    if mid in REMPLISSAGES:
        return 'remplissage'
    return 'sol'


def asset_texture_cc0(dossier, role):
    return f'{UE_TEX_CC0}/{dossier}/T_{dossier}_{role}'


def asset_texture_cs(fichier):
    return f'{UE_TEX_CS}/T_CS_{fichier}'


def textures_cc0(dossier, mesures):
    """{role: asset UE} des cartes disponibles (bibliothèque + hauteur dérivée)."""
    m = mesures['cc0'][dossier]
    roles = [r for r in m['roles'] if r in ('albedo', 'normale', 'rugosite', 'ao')]
    if 'hauteur' in m:
        roles.append('hauteur')
    return {r: asset_texture_cc0(dossier, r) for r in roles}


def reglages(mid):
    r = dict(REGLAGES_FAMILLE.get(FAMILLE.get(mid, 'beton'), {}))
    r.update(REGLAGES_ID.get(mid, {}))
    return r


def calage_albedo(moyenne, cible, facteur=(1.0, 1.0, 1.0)):
    """(Luminosite, Teinte) tels que Luminosite × Teinte × moyenne = cible × facteur (Y(Teinte) = 1)."""
    if cible is None:
        cible = moyenne
    c = [cible[i] * facteur[i] for i in range(3)]
    L = lum(c) / max(lum(moyenne), 1e-6)
    t = [c[i] / max(moyenne[i], 1e-6) / L for i in range(3)]
    y = lum(t)
    return round(L * y, 5), [round(x / y, 5) for x in t]


def calage_melange(m1, m2, cible, taux, gain2, facteur=(1.0, 1.0, 1.0)):
    """Mélange (1 - f)·L·T·m1 + f·L·R2·m2 = cible × facteur (moyennes des textures m1, m2 ; f = taux), le lit 2 à sa
    couleur propre × gain2 (L·R2 = gain2) et Y(T) = 1 : renvoie (Luminosite, Teinte, R2 = Melange2Rapport)."""
    c = [cible[i] * facteur[i] for i in range(3)]
    x = [(c[i] - taux * gain2 * m2[i]) / ((1 - taux) * m1[i]) for i in range(3)]       # L·T par canal
    if min(x) <= 0:
        raise ValueError(f'mélange impossible : lit 2 plus clair que la cible ({x})')
    L = lum(x)
    return round(L, 5), [round(v / L, 5) for v in x], round(gain2 / L, 5)


def rugosite_calee(moyenne_tex, cible, mul=0.7):
    """Remappage r' = r × Mul + Ajout : moyenne visée, contraste de la carte réduit à Mul."""
    if moyenne_tex is None:
        return 0.0, cible
    return mul, round(cible - mul * moyenne_tex, 4)


def facteur_etalonnage(nom_mi, etal):
    e = (etal or {}).get('mi', {}).get(nom_mi)
    return tuple(e['facteur']) if e and e.get('facteur') else (1.0, 1.0, 1.0)


def instances(mesures, etal=None):
    """Liste des MI à construire : dict(nom, chemin, maitre|parent_carla, materiau_id, variante, textures,
    scalaires, vecteurs, switches, cible, attendu (albédo prévu), mesure_plaque)."""
    sp = spec()
    out = []
    for mid, m in sp.items():
        sr = surcharge_rendu(mid)
        cible = sr['cible'] if sr else m.get('albedo_cible_lineaire')
        rug_cible = (m.get('rugosite') or {}).get('valeur', 0.8)
        mt = maitre(mid)
        dossier = sr['dossier'] if sr else SOURCE_UE.get(mid, (m['source_cc0']['nom'],))[0]
        mtx = mesures['cc0'][dossier]
        r = reglages(mid)
        tile = float(r.pop('TileM', m['tile_m']))
        if sr:
            tile = sr['tile_m']
        # ---- principal (CC0)
        nom = f'MI_{mid}'
        tex, vec, sw = textures_cc0(dossier, mesures), dict(MoyenneTexture=mtx['albedo_moyen_lin']), {}
        if mid in BETON_BORDURE_UE:
            b = BETON_BORDURE_UE[mid]
            mtx = dict(mtx, albedo_moyen_lin=mesures['citysample'][f'{b}_albedo.png']['albedo_moyen_lin'],
                       rugosite_moyenne=mesures['citysample'].get(f'{b}_aomrd_rugosite.png', {}).get('moyenne'))
            tex = {'albedo': asset_texture_cs(f'{b}_albedo'), 'normale': asset_texture_cs(f'{b}_normal'),
                   'rugosite': asset_texture_cs(f'{b}_aomrd_rugosite')}
            vec = dict(MoyenneTexture=mtx['albedo_moyen_lin'])
            dossier = f'citysample:{b}'
        mel = MELANGE.get(mid) if mt == 'remplissage' else None
        if mel:                                               # le masque a pour moyenne le taux (bruit uniforme)
            m2 = mesures['cc0'][mel['dossier']]
            L, T, r2 = calage_melange(mtx['albedo_moyen_lin'], m2['albedo_moyen_lin'], cible, mel['taux'], mel['gain'],
                                      facteur_etalonnage(nom, etal))
            tex.update({f'{role}2': t for role, t in textures_cc0(mel['dossier'], mesures).items() if role != 'ao'})
            vec.update(MoyenneTexture2=m2['albedo_moyen_lin'], Melange2Rapport=[r2, r2, r2])
            sw['Melange'] = True
        else:
            L, T = calage_albedo(mtx['albedo_moyen_lin'], cible, facteur_etalonnage(nom, etal))
        mul, aj = rugosite_calee(mtx.get('rugosite_moyenne'), rug_cible)
        sc = dict(TileM=tile, Luminosite=L, RugositeMul=mul, RugositeAjout=aj, **r)
        if mt == 'remplissage':
            h = mtx.get('hauteur', {})
            sc.update(DeplacementCm=DEPLACEMENT_CM[mid], HauteurCentre=h.get('moyenne', 0.5))
            if mel:
                sc.update(TileM2=mel['tile_m'], MelangeTaux=mel['taux'], MelangeEchelleM=mel['echelle_m'],
                          MelangeTransition=mel['transition'], MelangeHauteur=mel['hauteur'], Contraste2=mel['contraste'],
                          HauteurCentre2=m2.get('hauteur', {}).get('moyenne', 0.5))
        if mt == 'bordure':
            sc.update(Salissure=SALISSURE_BORDURE[mid], SalissureHaut=SALISSURE_HAUT)
        out.append(dict(nom=nom, chemin=f'{UE_MAT}/{nom}', maitre=mt, materiau_id=mid, variante='cc0',
                        textures=tex, scalaires=sc, vecteurs=dict(Teinte=T, **vec), switches=sw,
                        cible=cible or mtx['albedo_moyen_lin'], cible_source='spec' if cible else 'texture',
                        moyenne_texture=mtx['albedo_moyen_lin'], dossier_cc0=dossier,
                        statut_source=m['source_cc0'].get('statut'), source_ue=SOURCE_UE.get(mid, (None, None))[1],
                        tile_spec=float(m['tile_m'])))
        # ---- City Sample
        cs = CITYSAMPLE.get(mid)
        if cs:
            moy = mesures['citysample'][cs['albedo'] + '.png']['albedo_moyen_lin']
            rmoy = mesures['citysample'].get(cs['rugosite'] + '.png', {}).get('moyenne')
            nom = f'MI_{mid}__citysample'
            L, T = calage_albedo(moy, cible, facteur_etalonnage(nom, etal))
            mul, aj = rugosite_calee(rmoy, rug_cible)
            sc = dict(sc, TileM=CITYSAMPLE_TILE_M, Luminosite=L, RugositeMul=mul, RugositeAjout=aj, AOForce=0.0, Contraste=1.0,
                      NormalForce=REGLAGES_FAMILLE[FAMILLE[mid]].get('NormalForce', 1.0))
            out.append(dict(nom=nom, chemin=f'{UE_MAT}/{nom}', maitre=mt, materiau_id=mid, variante='citysample',
                            textures={'albedo': asset_texture_cs(cs['albedo']), 'normale': asset_texture_cs(cs['normale']),
                                      'rugosite': asset_texture_cs(cs['rugosite'])},
                            scalaires=sc, vecteurs=dict(Teinte=T, MoyenneTexture=moy), switches={}, cible=cible or moy,
                            cible_source='spec' if cible else 'texture', moyenne_texture=moy))
        # ---- CARLA
        ca = CARLA.get(mid)
        if ca:
            nom = f'MI_{mid}__carla'
            base = dict(nom=nom, chemin=f'{UE_MAT}/{nom}', materiau_id=mid, variante='carla', cible=cible,
                        cible_source='spec' if cible else 'aucune', facteur=facteur_etalonnage(nom, etal))
            if 'mi' in ca:
                out.append(dict(base, parent_carla=ca['mi'], maitre='carla'))
            else:
                t = f'{CARLA_HD}/{ca["textures"]}'
                sc = dict(TileM=ca['tile_m'], Luminosite=1.0, RugositeMul=0.7, RugositeAjout=round(rug_cible - 0.7 * 0.6, 4),
                          AOForce=1.0, **r, DeplacementCm=DEPLACEMENT_CM.get(mid, 1.5), HauteurCentre=0.5)
                f = base['facteur']                   # moyenne des textures CARLA inconnue hors UE : tout vient de la mesure
                L = lum(f)
                T = [round(x / L, 5) for x in f]
                sc['Luminosite'] = round(L, 5)
                out.append(dict(base, maitre='remplissage', textures={'albedo': f'{t}_dh', 'normale': f'{t}_n',
                                                                       'rugosite': f'{t}_ORM', 'ao': f'{t}_ORM'},
                                scalaires=sc, vecteurs=dict(Teinte=T), switches=dict(HauteurCanalA=True)))
    return out


def peintures(mesures):
    """MI de peinture : recette de peinture.json (couleurs, usures, seuils du masque de la graine 1967)."""
    sp = charger_json(SPEC_PEINTURE)
    sol = spec()[PEINTURE_SOL]
    dossier = sol['source_cc0']['nom']
    moy_tex = mesures['cc0'][dossier]['albedo_moyen_lin']
    moy_sol = sol['albedo_cible_lineaire']
    seuils = sp['usure']['seuils_score']['valeurs']
    out = []
    for c in PEINTURE_COULEURS:
        cd = sp['couleurs'][c]
        for u in PEINTURE_USURES:
            nv = sp['usure']['niveaux'][u]
            nom = f'MI_PJ_Peinture_{c}_u{u}'
            rug = sp['rugosite']['peinture_par_usure'].get(u) or 0.75
            w = nv['poids_RGA']
            sc = dict(TileMasqueM=float(sp['usure']['masque']['tile_m']), Seuil=float(seuils[u]),
                      FissureB=float(nv['fissure_B']) if nv['fissure_B'] is not None else 2.0,
                      FissureA=float(nv['fissure_A']) if nv['fissure_A'] is not None else 2.0,
                      Salete=float(nv['salete']), Transparence=float(nv['transparence']),
                      Chroma=float((cd.get('chroma_par_usure') or {}).get(u, 1.0)), Rugosite=float(rug),
                      TileSol=float(sol['tile_m']), SolGain=round(lum(moy_sol) / lum(moy_tex), 4),
                      NormaleSolForce=0.6 if u in ('0', '1') else 0.8)
            out.append(dict(nom=nom, chemin=f'{UE_MAT}/{nom}', maitre='peinture', couleur=c, usure=u,
                            textures={'masque': T_MASQUE_PEINTURE, 'sol_albedo': asset_texture_cc0(dossier, 'albedo'),
                                      'sol_normale': asset_texture_cc0(dossier, 'normale')},
                            scalaires=sc, vecteurs=dict(CouleurNeuve=list(cd['neuf']['albedo_lineaire']),
                                                        PoidsRGA=list(w), MoyenneSol=list(moy_sol)),
                            switches={}, couverture_visee=nv['couverture_effective']))
    return out
