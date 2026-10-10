"""[editeur] Correctif de la COPIE projet des arbres CARLA (/Game/Carla/Static/Vegetation ; jamais D:/CARLA_Assets) :
Nanite sur les maillages d'arbres et de buissons poses par le PCG (revue UE du 10/10 : ShadowDepths dominant, 2 a 5,3 ms,
du aux feuillages non Nanite dans les ombres virtuelles ; 60,1 i/s au pire sur cam4).

Feuillage masque en Nanite (UE 5.8) avec preservation de l'aire (shape_preservation PRESERVE_AREA : pas
d'amincissement des feuilles au loin). Les LOD imposteurs (correctifs/carla_imposteurs.py) ne servent plus en Nanite. ARGS : points (fichiers pj_points
dont on prend les assets), actif (vrai ; faux = retour au maillage classique). RESULT : {maillages, deja, refus}.
"""
import json

import unreal

A = dict(points=[], actif=True)
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
assets = set()
for f in A['points']:
    for p in json.load(open(f, encoding='utf-8'))['points']:
        a = p['asset'].split('.')[0]
        if a.startswith('/Game/Carla/Static/Vegetation/'):
            assets.add(a)
R = {'maillages': 0, 'deja': 0, 'refus': []}
for a in sorted(assets):
    sm = unreal.load_asset(a)
    if sm is None:
        R['refus'].append(a)
        continue
    ns = sm.get_editor_property('nanite_settings')
    forme = unreal.NaniteShapePreservation.PRESERVE_AREA if A['actif'] else unreal.NaniteShapePreservation.NONE
    if ns.get_editor_property('enabled') == bool(A['actif']) and ns.get_editor_property('shape_preservation') == forme:
        R['deja'] += 1
        continue
    sm.modify()
    ns.set_editor_property('enabled', bool(A['actif']))
    ns.set_editor_property('shape_preservation', forme)
    sm.set_editor_property('nanite_settings', ns)
    EAL.save_loaded_asset(sm, False)
    R['maillages'] += 1
RESULT = R
