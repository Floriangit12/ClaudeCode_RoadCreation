"""[editeur] Essai 4 : verification d'un import USD (echelle m -> cm, Z haut, Y inverse, materiaux).

ARGS : usd (fichier), dossier (contenu importe), prims=[chemins USD de Mesh a controler].
Pour chaque prim : boite et centroide des sommets (repere monde USD, m) -> attendu UE
(X = 100x, Y = -100y, Z = 100z) compare a la boite / au centroide des sommets du StaticMesh importe
(transformes par le composant) ; presence des sommets extremes ; materiau(x) du composant.
"""
import math

import unreal
from pxr import Usd, UsdGeom
from pj_tools import toolset as T
from pj_tools import repere

A = ARGS  # noqa: F821
res = {'prims': []}
st = Usd.Stage.Open(A['usd'])
res['stage'] = {'metersPerUnit': UsdGeom.GetStageMetersPerUnit(st), 'upAxis': str(UsdGeom.GetStageUpAxis(st))}


def points_usd(prim):
    m = UsdGeom.Mesh(prim)
    xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    return [tuple(xf.Transform(p)) for p in m.GetPointsAttr().Get()]


def stats(pts):
    n = len(pts)
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    c = [sum(p[i] for p in pts) / n for i in range(3)]
    return n, mn, mx, c


def extremes(pts):
    cles = {'xmin': lambda p: p[0], 'xmax': lambda p: -p[0], 'ymin': lambda p: p[1], 'ymax': lambda p: -p[1],
            'zmin': lambda p: p[2], 'zmax': lambda p: -p[2], 'x+y': lambda p: -(p[0] + p[1]),
            'x-y': lambda p: -(p[0] - p[1])}
    return {k: min(pts, key=f) for k, f in cles.items()}


# acteurs StaticMesh issus de l'import (mesh sous le dossier cible)
comps = []
for a in T._acteurs().get_all_level_actors():
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.static_mesh
        if sm and sm.get_path_name().startswith(A['dossier']):
            comps.append((a, c, sm))
res['composants'] = [[a.get_actor_label(), c.get_name(), sm.get_path_name()] for a, c, sm in comps]


def sommets_ue(c, sm):
    tr = c.get_world_transform()
    out = []
    for s in range(sm.get_num_sections(0)):
        v = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, s)[0]
        out.extend(tr.transform_location(p) for p in v)
    return [(p.x, p.y, p.z) for p in out]


for chemin in A['prims']:
    prim = st.GetPrimAtPath(chemin)
    pu = points_usd(prim)
    n, mn, mx, cen = stats(pu)
    att_min = [mn[0] * 100, -mx[1] * 100, mn[2] * 100]
    att_max = [mx[0] * 100, -mn[1] * 100, mx[2] * 100]
    att_c = list(repere.local_vers_ue(*cen))
    d = {'prim': chemin, 'usd': {'n_sommets': n, 'min_m': mn, 'max_m': mx, 'centroide_m': cen},
         'attendu_ue_cm': {'min': att_min, 'max': att_max, 'centroide': att_c}}
    nom = chemin.rsplit('/', 1)[-1]
    cand = [x for x in comps if nom.lower() in (x[2].get_name().lower() + x[0].get_actor_label().lower())]
    if not cand:
        cand = comps if len(comps) == 1 else []
    if not cand:
        d['erreur'] = 'composant importe introuvable'
        res['prims'].append(d)
        continue
    a, c, sm = cand[0]
    pv = sommets_ue(c, sm)
    n2, mn2, mx2, c2 = stats(pv)
    d['ue'] = {'acteur': a.get_actor_label(), 'mesh': sm.get_path_name(), 'n_sommets_rendu': n2,
               'min_cm': mn2, 'max_cm': mx2, 'centroide_cm': c2,
               'transform_composant': str(c.get_world_transform()),
               'materiaux': [m.get_path_name() if m else None for m in c.get_materials()],
               'nanite': bool(sm.get_editor_property('nanite_settings').get_editor_property('enabled'))}
    d['ecart_boite_cm'] = max(max(abs(u - v) for u, v in zip(mn2, att_min)),
                              max(abs(u - v) for u, v in zip(mx2, att_max)))
    # centroide : le rendu duplique les sommets aux aretes vives -> indicatif seulement
    d['ecart_centroide_cm'] = math.dist(c2, att_c)
    # sommets extremes USD retrouves dans le mesh UE (grille 1 cm)
    grille = {}
    for p in pv:
        grille.setdefault(tuple(round(v) for v in p), []).append(p)
    ext = {}
    for k, p in extremes(pu).items():
        q = repere.local_vers_ue(*p)
        best = 1e9
        cle = tuple(round(v) for v in q)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for r in grille.get((cle[0] + dx, cle[1] + dy, cle[2] + dz), []):
                        best = min(best, math.dist(r, q))
        ext[k] = {'usd_m': list(p), 'attendu_ue_cm': list(q), 'ecart_cm': None if best > 1e8 else round(best, 4)}
    d['sommets_extremes'] = ext
    d['ecart_extremes_max_cm'] = max((e['ecart_cm'] if e['ecart_cm'] is not None else 1e9) for e in ext.values())
    res['prims'].append(d)

RESULT = res
