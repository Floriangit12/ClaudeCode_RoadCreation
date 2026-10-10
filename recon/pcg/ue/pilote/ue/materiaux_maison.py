"""[editeur] MI des materiaux maison du pilote (ids hors materiaux_sol.json, contrat/verifier_usd.MATERIAUX_MAISON) et
du sol de contexte, derives des MI etalonnes de materiaux/ (memes maitres, memes textures CC0) :

- MI_mortier_joint (joint en retrait de 4 mm, bordures neuves) et MI_mortier_clair (joint a fleur, bordures anciennes,
  photo utilisateur 1) : enfants de MI_beton_bordure_gris, mortier gris clair (albedo 0,28 / 0,30 ; Karma 0,055 / 0,27 :
  la revue des materiaux demande un mortier gris clair, pas des fentes noires ; revue UE du 10/10 : joint a 0,20 lu
  comme un sillon sombre) ;
- MI_bitume_pontage : enfant de MI_enrobe_bbsg_ancien, bitume (albedo 0,035), mat (rugosite ~0,75 comme Karma :
  a 0,5 les rubans reflechissaient le ciel en blanc en vue rasante) ;
- MI_herbe_touffe : M_PJ_Touffe (feuillage deux faces, transmission), vert terne d'octobre du pied a la pointe, 15 % de
  touffes seches (albedo <= 0,25) ;
- MI_eclat_brf, MI_eclat_gravier : M_PJ_Eclat (palette par instance de recon/pcg/houdini/pj_ilot.py, comme Karma ;
  detail et normale des textures de MI_brf_bois_concasse et MI_gravier_concasse_6_10, fibres du bois) ;
- MI_PJ_Contexte : enfant de MI_gazon_tondu en UV monde (switch UV_Monde) pour le plan de contexte du niveau.
Albedo : produit Luminosite x Teinte mis a l'echelle de la cible effective du parent (materiaux/catalogue.cible_effective :
materiaux_sol.json ou surcharge de rendu Karma). Rejouable.
ARGS : aucun. RESULT : {mi: {parent, parametres}}.
"""
import importlib
import os
import sys

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MAT = '/Game/PJ/Materials'
DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(DEPOT, 'recon', 'pcg', 'ue', 'materiaux'))
import catalogue as C  # noqa: E402
importlib.reload(C)


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def mi(nom, parent):
    chemin = f'{MAT}/{nom}'
    m = unreal.load_asset(chemin) if EAL.does_asset_exist(chemin) else \
        AT.create_asset(nom, MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    m.set_editor_property('parent', unreal.load_asset(parent))
    MEL.clear_all_material_instance_parameters(m)
    return m


def recolorer(m, parent, cible_parent, cible):
    """Luminosite x Teinte du parent mis a l'echelle : albedo cible (par canal) a partir de la cible du parent."""
    L0 = MEL.get_material_instance_scalar_parameter_value(parent, 'Luminosite')
    t0 = MEL.get_material_instance_vector_parameter_value(parent, 'Teinte')
    k = lum(cible) / lum(cible_parent)
    r = [cible[i] / cible_parent[i] / k for i in range(3)]
    MEL.set_material_instance_scalar_parameter_value(m, 'Luminosite', L0 * k)
    MEL.set_material_instance_vector_parameter_value(m, 'Teinte', unreal.LinearColor(t0.r * r[0], t0.g * r[1], t0.b * r[2], 1.0))
    return {'Luminosite': round(L0 * k, 5), 'Teinte': [round(t0.r * r[0], 5), round(t0.g * r[1], 5), round(t0.b * r[2], 5)]}


def scalaires(m, **kv):
    for k, v in kv.items():
        MEL.set_material_instance_scalar_parameter_value(m, k, float(v))
    return kv


def copier(m, source, textures, scal, vecs):
    """Parametres d'un MI etalonne (textures, scalaires, vecteurs) recopies sur un MI d'un autre maitre."""
    out = {}
    for t in textures:
        tex = MEL.get_material_instance_texture_parameter_value(source, t)
        if tex:
            MEL.set_material_instance_texture_parameter_value(m, t, tex)
            out[t] = tex.get_path_name()
    for s in scal:
        v = MEL.get_material_instance_scalar_parameter_value(source, s)
        MEL.set_material_instance_scalar_parameter_value(m, s, v)
        out[s] = round(v, 5)
    for s in vecs:
        v = MEL.get_material_instance_vector_parameter_value(source, s)
        MEL.set_material_instance_vector_parameter_value(m, s, v)
        out[s] = [round(v.r, 5), round(v.g, 5), round(v.b, 5)]
    return out


def finir(m):
    MEL.update_material_instance(m)
    EAL.save_loaded_asset(m, False)


cible = {k: C.cible_effective(k) for k in ('beton_bordure_gris', 'enrobe_bbsg_ancien', 'gazon_tondu')}
R = {}

# ---- mortiers de joint (bouchons pj_bordure_prototypes joint_* / jointf_*)
p = unreal.load_asset(f'{MAT}/MI_beton_bordure_gris')
for nom, a in (('MI_mortier_joint', 0.28), ('MI_mortier_clair', 0.30)):
    m = mi(nom, p.get_path_name())
    d = recolorer(m, p, cible['beton_bordure_gris'], (a, a * 1.0, a * 0.95))
    d.update(scalaires(m, Salissure=0.15, SalissureHaut=1.0, Contraste=0.35, TileM=0.35, NormalForce=0.3,
                       VariationTeinte=0.02, MacroForce=0.04, RugositeAjout=0.45))
    finir(m)
    R[nom] = {'parent': p.get_path_name(), **d}

# ---- bitume de pontage
p = unreal.load_asset(f'{MAT}/MI_enrobe_bbsg_ancien')
m = mi('MI_bitume_pontage', p.get_path_name())
d = recolorer(m, p, cible['enrobe_bbsg_ancien'], (0.036, 0.035, 0.033))
d.update(scalaires(m, Contraste=0.45, RugositeMul=0.3, RugositeAjout=0.55, NormalForce=0.35, Salissure=0.0))
finir(m)
R['MI_bitume_pontage'] = {'parent': p.get_path_name(), **d}

# ---- touffes d'herbe (pj_decals : joints des bordures anciennes, limites gazon / dur) : M_PJ_Touffe, feuillage deux
# faces ; vert du gazon d'octobre de la revue Karma un peu plus clair a la pointe, pied sombre, touffes seches <= 0,25
g = cible['gazon_tondu']
m = mi('MI_herbe_touffe', C.MAITRES['touffe'])
d = {}
for k, v in (('Couleur', (g[0] * 1.3, g[1] * 1.15, g[2] * 1.15)), ('CouleurPied', (g[0] * 0.6, g[1] * 0.6, g[2] * 0.6)),
             ('CouleurSeche', (0.21, 0.18, 0.10))):
    MEL.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(*v, 1.0))
    d[k] = [round(x, 4) for x in v]
d.update(scalaires(m, PartSeche=0.12, VariationTeinte=0.15, GainTransmission=0.8, Rugosite=0.7))
finir(m)
R['MI_herbe_touffe'] = {'parent': C.MAITRES['touffe'], **d}

# ---- eclats (couverture des remplissages, epars) : M_PJ_Eclat, palette par instance (catalogue.ECLATS)
for nom, e in C.ECLATS.items():
    src = unreal.load_asset(f"{MAT}/{e['source']}")
    m = mi(nom, C.MAITRES['eclat'])
    d = copier(m, src, ('T_Albedo', 'T_Normale'), (), ('MoyenneTexture',))
    acc = 0.0
    for k, (part, (a0, a1), gain) in enumerate(e['classes'], 1):
        for suf, a in (('A', a0), ('B', a1)):
            MEL.set_material_instance_vector_parameter_value(m, f'Couleur{k}{suf}', unreal.LinearColor(
                a * gain[0], a * gain[1], a * gain[2], 1.0))
            d[f'Couleur{k}{suf}'] = [round(a * x, 4) for x in gain]
        if k < 3:
            d[f'Part{k}'] = part
            MEL.set_material_instance_scalar_parameter_value(m, f'Part{k}', float(part))
        acc += part
    d.update(scalaires(m, **{k: v for k, v in e.items() if k not in ('source', 'classes')}))
    finir(m)
    R[nom] = {'parent': C.MAITRES['eclat'], 'source': e['source'], **d}

# ---- sol de contexte du niveau (plan de 3 km) : gazon en UV monde
p = unreal.load_asset(f'{MAT}/MI_gazon_tondu')
m = mi('MI_PJ_Contexte', p.get_path_name())
MEL.set_material_instance_static_switch_parameter_value(m, 'UV_Monde', True)
d = scalaires(m, MacroForce=0.3, MacroEchelleM=25.0)
finir(m)
R['MI_PJ_Contexte'] = {'parent': p.get_path_name(), 'UV_Monde': True, **d}

RESULT = R
