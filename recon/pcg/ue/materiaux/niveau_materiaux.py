"""[éditeur] Niveau d'essai /Game/PJ/Maps/PJ_Materiaux : plaques de 2 x 2 m par MI (grille étiquetée) et maquettes.

Préalable (materiaux.py niveau) : tests_phase0/ue/t1_niveau.py (éclairage de PJ_Phase0 : soleil az. 220° corrigé
de la convergence, élévation 27,6°, SkyAtmosphere, SkyLight temps réel, exposition manuelle) et import des USD de
generer_meshes.py (pj_tools.import_usd, /Game/PJ/Essais/Materiaux/USD). Ce script :
- active Nanite sur les maillages d'essai (déplacement des remplissages) ;
- retire les acteurs créés par l'import USD et tout acteur PJM_* précédent (rejouable) ; abaisse P0_Sol de 1 cm ;
- pose la grille : une plaque par MI (catalogue.instances + peintures, la peinture sur une plaque d'enrobé), étiquette
  à plat au sud de chaque plaque ; grille à x >= 20 m (repère local), lignes vers le nord ;
- pose les maquettes : file de 6 bordures T2 (0,994 m, joints de 6 mm) entre chaussée et trottoir en enrobé
  (photo 1) ; deux îlots de 3,0 x 2,0 m ceinturés de T2 à onglets, remplis de BRF et de gravier concassé, 3 cm sous
  le dessus des bordures au pourtour, bombés de 1,5 cm (photos 2 et 3).
ARGS : ev100 (exposition du PostProcessVolume, défaut pj_tools.eclairage.EV100 = 14).
Renvoie (RESULT) la liste des plaques {nom, centre local, materiau} et des poses de maquettes (materiaux.py s'en sert).
"""
import importlib
import json
import math
import os
import sys

import unreal

ICI = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else 'D:/ClaudeCode_RoadCreation/recon/pcg/ue/materiaux'
if ICI not in sys.path:
    sys.path.insert(0, ICI)
import catalogue as C  # noqa: E402
importlib.reload(C)
from pj_tools import toolset as T  # noqa: E402
from pj_tools import repere  # noqa: E402
from pj_tools import eclairage  # noqa: E402

A = dict(ev100=eclairage.EV100)
A.update(globals().get('ARGS') or {})
ACT = T._acteurs()
EAL = unreal.EditorAssetLibrary
USD = '/Game/PJ/Essais/Materiaux/USD'
GRILLE_X0, GRILLE_Y0, PAS, COLS = 20.0, 0.0, 2.7, 8
J = 0.006
D0 = 0.003 * math.sqrt(2.0)             # retrait de l'onglet au coin (joint de 6 mm sur la bissectrice)


def sm(nom):
    """StaticMesh importé depuis l'USD <nom>.usda (composant <nom> -> SM_<nom>)."""
    r = unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(USD, recursive=True)
    for a in r:
        if str(a.asset_name) == f'SM_{nom}':
            return unreal.load_asset(f'{a.package_name}.{a.asset_name}')
    raise RuntimeError(f'maillage absent : SM_{nom} sous {USD}')


def nanite(m):
    ns = m.get_editor_property('nanite_settings')
    if not ns.get_editor_property('enabled'):
        ns.set_editor_property('enabled', True)
        m.set_editor_property('nanite_settings', ns)
        EAL.save_loaded_asset(m, False)


def poser(label, mesh, x, y, z, yaw=0.0, materiau=None):
    loc = unreal.Vector(*repere.local_vers_ue(x, y, z))
    rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=repere.yaw_local_vers_ue(yaw))
    a = ACT.spawn_actor_from_object(mesh, loc, rot)
    a.set_actor_label(label)
    a.set_folder_path('PJM')
    smc = a.static_mesh_component
    smc.set_mobility(unreal.ComponentMobility.STATIC)
    if materiau:
        mi = unreal.load_asset(materiau)
        if mi is None:
            raise RuntimeError(f'MI absent : {materiau}')
        smc.set_material(0, mi)
    return a


def etiquette(label, texte, x, y, z=0.002, taille=10.0):
    a = ACT.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*repere.local_vers_ue(x, y, z)))
    a.set_actor_label(label)
    a.set_folder_path('PJM/Etiquettes')
    # texte à plat, face vers le haut, lecture vers l'est, haut du texte vers le nord (vue de dessus cap 90°)
    a.set_actor_rotation(unreal.MathLibrary.make_rot_from_xy(unreal.Vector(0, 0, 1), unreal.Vector(-1, 0, 0)), False)
    tr = a.text_render
    tr.set_text(texte)
    tr.set_world_size(taille)
    tr.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    tr.set_text_render_color(unreal.Color(r=235, g=235, b=235, a=255))
    return a


# ---- maillages d'essai : Nanite
mesh = {n: sm(n) for n in ('PJ_Plaque_2x2', 'PJ_Plaque_Chaussee_7x3', 'PJ_Plaque_Trottoir_6x2', 'PJ_Plaque_Ilot_2p72x1p72',
                           'PJ_Plaque_Sol_16x12', 'PJ_Bordure_T2_L994_Droit', 'PJ_Bordure_T2_L993_OngletDebut',
                           'PJ_Bordure_T2_L993_OngletFin')}
for m in mesh.values():
    nanite(m)

# ---- nettoyage (rejouable) : tout sauf l'éclairage P0_* (t1_niveau.py)
retires = 0
for a in list(ACT.get_all_level_actors()):
    lab = a.get_actor_label()
    if lab.startswith('P0_') or isinstance(a, (unreal.WorldSettings,)):
        continue
    if isinstance(a, (unreal.StaticMeshActor, unreal.TextRenderActor)) or lab.startswith('PJM_') or isinstance(a, unreal.Actor) and a.get_class().get_name() in ('Actor',):
        ACT.destroy_actor(a)
        retires += 1
sol = T._trouver_acteur('P0_Sol')
if sol:
    v = sol.get_actor_location()
    sol.set_actor_location(unreal.Vector(v.x, v.y, -1.0), False, False)
ppv = T._trouver_acteur('P0_PostProcess')
if ppv:
    pp = ppv.get_editor_property('settings')
    pp.set_editor_property('auto_exposure_bias', -float(A['ev100']))
    ppv.set_editor_property('settings', pp)

# ---- grille de plaques
mesures = C.charger_json(C.MESURES)
defs = C.instances(mesures) + C.peintures(mesures)
blocs = [('cc0', [d for d in defs if d.get('variante') == 'cc0']),
         ('citysample', [d for d in defs if d.get('variante') == 'citysample']),
         ('carla', [d for d in defs if d.get('variante') == 'carla']),
         ('peinture', [d for d in defs if d['maitre'] == 'peinture'])]
plaques = []
y = GRILLE_Y0
for bloc, liste in blocs:
    for i, d in enumerate(liste):
        cx = GRILLE_X0 + PAS * (i % COLS) + 1.0
        cy = y + PAS * (i // COLS) + 1.0
        if bloc == 'peinture':                            # enrobé dessous, peinture masquée à +3 mm
            poser(f'PJM_Fond_{d["nom"]}', mesh['PJ_Plaque_2x2'], cx, cy, 0.0, 0.0, f'{C.UE_MAT}/MI_{C.PEINTURE_SOL}')
            poser(f'PJM_Plaque_{d["nom"]}', mesh['PJ_Plaque_2x2'], cx, cy, 0.003, 0.0, d['chemin'])
        else:
            poser(f'PJM_Plaque_{d["nom"]}', mesh['PJ_Plaque_2x2'], cx, cy, 0.0, 0.0, d['chemin'])
        etiquette(f'PJM_Etiquette_{d["nom"]}', d['nom'][3:], cx, cy - 1.18)
        plaques.append({'nom': d['nom'], 'bloc': bloc, 'centre': [round(cx, 3), round(cy, 3)], 'maitre': d['maitre']})
    y += PAS * math.ceil(len(liste) / COLS) + 1.0

# ---- maquette 1 : file de bordures entre chaussée et trottoir (photo 1)
poses = {}
poser('PJM_Chaussee_File', mesh['PJ_Plaque_Chaussee_7x3'], 3.0, -1.5, 0.0, 0.0, f'{C.UE_MAT}/MI_enrobe_bbsg_ancien')
for k in range(6):
    poser(f'PJM_Bordure_File_{k + 1}', mesh['PJ_Bordure_T2_L994_Droit'], k * (0.994 + J), 0.0, 0.0, 0.0,
          f'{C.UE_MAT}/MI_beton_bordure_gris')
poser('PJM_Trottoir_File', mesh['PJ_Plaque_Trottoir_6x2'], 0.997 * 3, 0.15 + 1.0, 0.14, 0.0, f'{C.UE_MAT}/MI_enrobe_trottoir')

# ---- maquette 2 : îlots ceinturés (BRF, gravier), chaussée commune
poser('PJM_Chaussee_Ilots', mesh['PJ_Plaque_Sol_16x12'], 4.0, 10.0, 0.0, 0.0, f'{C.UE_MAT}/MI_enrobe_bbsg_ancien')


def ilot(nom, x0, y0, lx, ly, mi_bordure, mi_remplissage, retrait):
    coins = [(x0, y0), (x0 + lx, y0), (x0 + lx, y0 + ly), (x0, y0 + ly)]
    k = 0
    for c in range(4):                                     # sens trigo : intérieur à gauche (+Y du prototype)
        (xa, ya), (xb, yb) = coins[c], coins[(c + 1) % 4]
        L = math.hypot(xb - xa, yb - ya)
        th = math.degrees(math.atan2(yb - ya, xb - xa))
        ux, uy = (xb - xa) / L, (yb - ya) / L
        n = round((L - 2 * D0 + J) / (0.993 + J))
        elems = ['PJ_Bordure_T2_L993_OngletDebut'] + ['PJ_Bordure_T2_L994_Droit'] * (n - 2) + ['PJ_Bordure_T2_L993_OngletFin']
        s = D0
        for e in elems:
            k += 1
            poser(f'PJM_Bordure_{nom}_{k:02d}', mesh[e], xa + ux * s, ya + uy * s, 0.0, th, mi_bordure)
            s += (0.994 if 'Droit' in e else 0.993) + J
    z = 0.14 - retrait
    poser(f'PJM_Remplissage_{nom}', mesh['PJ_Plaque_Ilot_2p72x1p72'], x0 + lx / 2, y0 + ly / 2, z, 0.0, mi_remplissage)
    return {'coins': coins, 'z_remplissage': z, 'elements': k}


poses['ilot_brf'] = ilot('BRF', 0.0, 6.0, 3.0, 2.0, f'{C.UE_MAT}/MI_beton_bordure_clair', f'{C.UE_MAT}/MI_brf_bois_concasse', 0.03)
poses['ilot_gravier'] = ilot('Gravier', 5.0, 6.0, 3.0, 2.0, f'{C.UE_MAT}/MI_beton_bordure_clair',
                             f'{C.UE_MAT}/MI_gravier_concasse_6_10', 0.03)
poses['file'] = {'x': [0.0, 6.0], 'y_face_vue': 0.0, 'vue_m': 0.14}

T._niveaux().save_current_level()
RESULT = {'plaques': plaques, 'maquettes': poses, 'acteurs_retires': retires,
          'grille': {'x0': GRILLE_X0, 'y0': GRILLE_Y0, 'pas': PAS, 'colonnes': COLS, 'y_fin': y}}
with open(f'{C.OUT}/niveau.json', 'w', encoding='utf-8') as f:
    json.dump(RESULT, f, ensure_ascii=False, indent=1)
