"""[editeur] Collisions du pilote et de son contexte dans le niveau courant (revue UE du 10/10 : tous les maillages du
projet et tous les ISM issus du PCG en NoCollision ; un rayon vers le bas ne touchait que le plan de contexte, d'ou
lidar / radar par rayons, physique des vehicules et verite terrain inoperants).

- StaticMesh (sol v2, contexte v1 : sol, bordures v1, batiments ; batiments lointains ; relief et sol lointain ;
  bibliotheque des bordures) : collision complexe utilisee comme simple (CTF_USE_COMPLEX_AS_SIMPLE : les triangles exacts
  du maillage, profils de bordure compris, sans convexes approches), cuisson du maillage de collision reactivee
  (bNeverNeedsCookedCollisionData pose par l'import USD) et repli Nanite a pleine resolution (fallback_relative_error 0 :
  la collision est cuite sur le repli ; 4,5 cm d'ecart avec le repli simplifie par defaut) ; composants des acteurs
  importes : profil BlockAll.
- Exclus (NoCollision) : eclats des remplissages (copeaux, concasse : le remplissage du sol est dessous), touffes,
  dalles BEV 3D (sol BEV dessous), pontages, marquages v1, bouchons de joint, zones d'echantillonnage PCG.
- Instances PCG (volumes PJ_PCG_Bordures, _Arbres, _Arbres_Lointains, _Clotures, _Mobilier) : profil BlockAll sur les
  ISM generes (les graphes posent le meme profil dans le descripteur du Static Mesh Spawner : pg_bordures.py,
  contexte/ue/pg_points.py) ; PJ_PCG_Herbe reste sans collision.

ARGS : etape = 'appliquer' | 'verifier' ; points_sol (verifier : [[x, y, z_attendu], ...] en m locaux, sol v2 USD,
acteur PJ_Sol) ; points_bordures (verifier : [[x, y, z_tete], ...], PJ_PCG_Bordures). RESULT : comptes (appliquer) ou
ecarts des rayons sur l'acteur attendu (verifier).
"""
import unreal
from pj_tools import repere

A = dict(etape='appliquer', points_sol=None, points_bordures=None)
A.update(globals().get('ARGS') or {})
EAL = unreal.EditorAssetLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DOSSIERS = ('/Game/PJ/Import/Sol', '/Game/PJ/Import/Contexte', '/Game/PJ/Import/Lointain', '/Game/PJ/Import/Relief',
            '/Game/PJ/Lib/Bordures')
EXCLUS = ('SM_copeau', 'SM_gravier_6_10', 'SM_touffe', 'SM_dalle_bev', 'SM_pontages', 'SM_Marquages', 'SM_joint')
VOLUMES = ('PJ_PCG_Bordures', 'PJ_PCG_Arbres', 'PJ_PCG_Arbres_Lointains', 'PJ_PCG_Clotures', 'PJ_PCG_Mobilier')
PROFIL = 'BlockAll'


def avec_collision(chemin):
    nom = chemin.split('.')[-1]
    return not nom.startswith(EXCLUS)


def maillages():
    out = []
    for d in DOSSIERS:
        for a in EAL.list_assets(d, recursive=True):
            if EAL.find_asset_data(a).asset_class_path.asset_name == 'StaticMesh' and avec_collision(a):
                out.append(a.split('.')[0])
    return out


def appliquer():
    R = {'maillages': 0, 'composants': 0, 'ism': 0, 'refus': []}
    sms = set()
    for chemin in maillages():
        sm = unreal.load_asset(chemin)
        bs = sm.get_editor_property('body_setup')
        if bs is None:
            R['refus'].append(f'{chemin} : body_setup absent')
            continue
        ns = sm.get_editor_property('nanite_settings')
        a_faire = (bs.get_editor_property('collision_trace_flag') != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
                   or bs.get_editor_property('never_needs_cooked_collision_data')
                   or (ns.get_editor_property('enabled') and ns.get_editor_property('fallback_relative_error') > 0.0))
        if a_faire:
            sm.modify()
            # l'import USD pose bNeverNeedsCookedCollisionData : aucun maillage de collision n'etait cuit (rayons sans
            # impact, meme en trace complexe) ; collision cuite sur le maillage de repli de Nanite, a pleine resolution
            # (erreur relative 0 : sinon ecart de 4,5 cm mesure sur le trottoir avec le repli simplifie par defaut)
            bs.set_editor_property('never_needs_cooked_collision_data', False)
            bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            if ns.get_editor_property('enabled'):
                ns.set_editor_property('fallback_target', unreal.NaniteFallbackTarget.RELATIVE_ERROR)
                ns.set_editor_property('fallback_relative_error', 0.0)
                sm.set_editor_property('nanite_settings', ns)
            EAL.save_loaded_asset(sm, False)
            R['cuits'] = R.get('cuits', 0) + 1
        sms.add(sm.get_path_name())
        R['maillages'] += 1
    for a in ACT.get_all_level_actors():
        lab = a.get_actor_label()
        if lab in VOLUMES:
            for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
                c.set_collision_profile_name(PROFIL)
                c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                R['ism'] += 1
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                continue                                    # eclats, touffes, dalles (HISM des PointInstancers USD)
            sm = c.get_editor_property('static_mesh')
            if sm is not None and sm.get_path_name() in sms:
                c.set_collision_profile_name(PROFIL)
                c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)          # etat physique recree
                c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
                R['composants'] += 1
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return R


def rayons(points, nom, attendu):
    """Rayon vertical (de z + 3 m a z - 3 m) en chaque point local (x, y, z attendu) : premier impact bloquant ; ecart
    (mm) compte sur les impacts de l'acteur attendu."""
    monde = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ecarts, rates, acteurs = [], 0, {}
    for x, y, z in points:
        X, Y, Z = repere.local_vers_ue(x, y, z)
        hit = unreal.SystemLibrary.line_trace_single(monde, unreal.Vector(X, Y, Z + 300.0), unreal.Vector(X, Y, Z - 300.0),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                     unreal.DrawDebugTrace.NONE, True)
        if hit is None:
            rates += 1
            continue
        t = (hit[-1] if isinstance(hit, tuple) else hit).to_tuple()
        if not t[0]:
            rates += 1
            continue
        imp = t[5]                                          # (bBlockingHit, ..., Location, ImpactPoint, ..., HitActor)
        act = t[9]
        lab = act.get_actor_label() if act else '?'
        if lab == attendu:
            ecarts.append((imp.z - Z) * 10.0)               # mm
        acteurs[lab] = acteurs.get(lab, 0) + 1
    ab = [abs(e) for e in ecarts]
    return {'famille': nom, 'points': len(points), 'touches_attendu': len(ecarts), 'rates': rates, 'attendu': attendu,
            'ecart_mm_max': round(max(ab), 2) if ab else None,
            'ecart_mm_moyen': round(sum(ab) / len(ab), 2) if ab else None,
            'acteurs': dict(sorted(acteurs.items(), key=lambda kv: -kv[1])[:8])}


if A['etape'] == 'appliquer':
    RESULT = appliquer()
else:
    RESULT = {k: rayons(A[k], k, at) for k, at in (('points_sol', 'PJ_Sol'), ('points_bordures', 'PJ_PCG_Bordures'))
              if A.get(k)}
