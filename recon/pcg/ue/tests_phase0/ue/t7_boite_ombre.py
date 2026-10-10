"""[editeur] Essai 7 : scene de non-regression de la capture (ombre portee d'une boite haute sur le sol neutre).

ARGS : niveau, centre [x, y] (m locaux, loin des autres essais), cote_m, hauteur_m, cam_dist_m, cam_haut_m,
       ecart_soleil_m (decalage des points au soleil, perpendiculaire a l'ombre, vers la camera).
Pose (ou met a jour) P0_Boite_Ombre (Cube moteur, MI_PJ_Neutre), lit la direction du soleil P0_Soleil,
calcule l'ombre au sol (axe de la boite -> pointe), des points d'echantillonnage a l'ombre et au soleil
(m locaux) et une pose de camera perpendiculaire a l'ombre, qui regarde le milieu de l'ombre.
"""
import math

import unreal
from pj_tools import toolset as T
from pj_tools import repere

A = dict(niveau='/Game/PJ/Maps/PJ_Phase0', centre=[-300.0, 300.0], cote_m=4.0, hauteur_m=12.0,
         cam_dist_m=16.0, cam_haut_m=10.0, ecart_soleil_m=6.0)
A.update(ARGS)  # noqa: F821
ACT = T._acteurs()

if T._monde().get_path_name().split('.')[0] != A['niveau']:
    T._preparer_changement_niveau(True)
    T._niveaux().load_level(A['niveau'])

cx, cy = A['centre']
c, hb = A['cote_m'], A['hauteur_m']
boite = T._trouver_acteur('P0_Boite_Ombre')
if boite is None:
    boite = ACT.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    boite.set_actor_label('P0_Boite_Ombre')
smc = boite.static_mesh_component
smc.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
smc.set_material(0, unreal.load_asset('/Game/PJ/Materials/MI_PJ_Neutre'))
boite.set_actor_location_and_rotation(T._vec_ue(cx, cy, hb / 2.0), unreal.Rotator(0, 0, 0), False, False)
boite.set_actor_scale3d(unreal.Vector(c, c, hb))          # Cube moteur : 1 m, pivot au centre

soleil = T._trouver_acteur('P0_Soleil')
f = soleil.get_actor_rotation().get_forward_vector()       # sens de propagation de la lumiere (UE)
d = repere.ue_vers_local(f.x, f.y, f.z)                     # meme vecteur en local (m -> /100 sans effet de norme)
n = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
d = (d[0] / n, d[1] / n, d[2] / n)
if d[2] >= -0.05:
    raise RuntimeError(f'soleil trop bas ou sous l horizon : {d}')
long_ombre = hb / -d[2] * math.hypot(d[0], d[1])           # longueur au sol de l'ombre du sommet
u = (d[0] / math.hypot(d[0], d[1]), d[1] / math.hypot(d[0], d[1]))   # direction horizontale de l'ombre
perp = (-u[1], u[0])                                       # perpendiculaire (gauche de l'ombre)
milieu = (cx + u[0] * (c / 2 + 0.5 * long_ombre), cy + u[1] * (c / 2 + 0.5 * long_ombre))
cam = (milieu[0] + perp[0] * A['cam_dist_m'], milieu[1] + perp[1] * A['cam_dist_m'], A['cam_haut_m'])
yaw_cam = math.degrees(math.atan2(-perp[1], -perp[0]))     # cap local de la camera (vers le milieu de l'ombre)
pitch_cam = -math.degrees(math.atan2(A['cam_haut_m'], A['cam_dist_m']))
ombre, soleil_pts = [], []
for k in (0.30, 0.45, 0.60):                               # le long de l'axe, dans l'ombre propre de la boite
    s = c / 2 + k * long_ombre
    p = (cx + u[0] * s, cy + u[1] * s)
    ombre.append([p[0], p[1], 0.0])
    soleil_pts.append([p[0] + perp[0] * A['ecart_soleil_m'], p[1] + perp[1] * A['ecart_soleil_m'], 0.0])
T._niveaux().save_current_level()
RESULT = {'boite': boite.get_path_name(), 'centre': [cx, cy], 'cote_m': c, 'hauteur_m': hb,
          'soleil_propagation_local': d, 'soleil_elev_deg': math.degrees(math.asin(-d[2])),
          'ombre_longueur_m': long_ombre, 'ombre_direction_local': u,
          'camera': {'p': cam, 'yaw_deg': yaw_cam, 'pitch_deg': pitch_cam},
          'points_ombre': ombre, 'points_soleil': soleil_pts}
