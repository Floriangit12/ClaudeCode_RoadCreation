"""[editeur] Feuilles mortes d'octobre sous les feuillus : decalques projetes (DBuffer) au pied de chaque feuillu existant.

- Maitre M_PJ_Feuilles_Decal (/Game/PJ/Materials/Maitres, Deferred Decal, DBuffer couleur + normale + rugosite) : textures
  CC0 ScatteredLeaves009 (overlay_feuilles_mortes, tuile TileM en coordonnees monde : pas d'etirement d'un decalque a
  l'autre) ; texture couvrante : opacite = hauteur de la texture > seuil, seuil qui monte du tronc (SeuilCentre) au bord
  du decalque (1,05) et module par un bruit lent (amas) : feuilles eparses en peripherie, sans fondu transparent.
  Les arbres et les buissons ne recoivent pas les decalques (receives_decals faux, pg_herbe.py / recevoir_decalques).
  Revue UE du 10/10 (taches orange uniformes couleur peinture, decalques etires sur les faces des bordures) : opacite
  nulle sur les faces raides (normale de la surface receptrice tiree de ddx / ddy de la position monde : |Nz| < 0,6 ->
  0, pleine des 0,85), feuilles brun-jaune (albedo moyen ~0,15, quelques jaunes : Teinte du MI), seuil de hauteur plus franc
  (feuilles entieres du dessus de la texture plutot que des fragments), rayon 0,45 x couronne, densite 0,9.
- MI_PJ_Feuilles_Decal ; acteurs DecalActor « PJ_Feuilles_<id> » (dossier PJ_Feuilles) depuis ue_pilote/points/arbres_ue.json :
  feuillus (familles Oak, Maple, WhiteAsh, Jeune), rayon = 0,6 x couronne posee (2 m au moins), profondeur 0,6 m,
  lacet tire de la graine de l'arbre ; idempotent (decalques precedents detruits).
ARGS : points (arbres_ue.json), densite (0,85), facteur_rayon (0,6). RESULT : {maitre, decalques}.
"""
import json
import math

import unreal
from pj_tools import repere

A = dict(points=None, densite=0.9, facteur_rayon=0.45, prof_m=0.6)
A.update(globals().get('ARGS') or {})
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ST = unreal.MaterialSamplerType
MAITRE = '/Game/PJ/Materials/Maitres/M_PJ_Feuilles_Decal'
MI = '/Game/PJ/Materials/MI_PJ_Feuilles_Decal'
TEX = '/Game/PJ/Textures/CC0/overlay_feuilles_mortes/T_overlay_feuilles_mortes_{}'


class G:
    def __init__(self, m):
        self.m, self.n = m, 0
        for ex in list(MEL.get_material_expressions(m)):
            MEL.delete_material_expression(m, ex)

    def e(self, cls, **kv):
        self.n += 1
        ex = MEL.create_material_expression(self.m, getattr(unreal, 'MaterialExpression' + cls), -300 - 240 * (self.n % 8), 110 * (self.n // 8))
        for k, v in kv.items():
            ex.set_editor_property(k, v)
        return ex

    def s(self, v):
        if isinstance(v, (int, float)):
            return (self.e('Constant', r=float(v)), '')
        if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], (int, float)):
            return (self.e('Constant2Vector', r=float(v[0]), g=float(v[1])), '')
        return v if isinstance(v, tuple) else (v, '')

    def c(self, v, dst, pin):
        ex, o = self.s(v)
        if not MEL.connect_material_expressions(ex, o, dst, pin):
            raise RuntimeError(f'connexion {ex.get_class().get_name()} -> {dst.get_class().get_name()}.{pin}')

    def op(self, cls, **kv):
        ex = self.e(cls)
        for k, v in kv.items():
            self.c(v, ex, '' if k == 'x' else k)
        return ex

    def scal(self, n, d):
        return self.e('ScalarParameter', parameter_name=n, default_value=float(d), group='Feuilles')

    def tex(self, n, role):
        return self.e('TextureObjectParameter', parameter_name=n, texture=unreal.load_asset(TEX.format(role)), group='Textures')

    def ech(self, t, uv, typ):
        ex = self.e('TextureSample', sampler_type=typ, sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        self.c(t, ex, 'Tex')
        self.c(uv, ex, 'UVs')
        return ex

    def mask(self, a, ch):
        ex = self.e('ComponentMask', r='R' in ch, g='G' in ch, b='B' in ch, a='A' in ch)
        self.c(a, ex, '')
        return ex


def maitre():
    m = unreal.load_asset(MAITRE) if EAL.does_asset_exist(MAITRE) else \
        AT.create_asset('M_PJ_Feuilles_Decal', '/Game/PJ/Materials/Maitres', unreal.Material, unreal.MaterialFactoryNew())
    g = G(m)
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    try:
        m.set_editor_property('decal_blend_mode', unreal.DecalBlendMode.DBM_DBUFFER_COLOR_NORMAL_ROUGHNESS)
    except Exception:  # noqa: BLE001  (5.8 : mode deduit des sorties connectees)
        pass
    wp = g.mask(g.e('WorldPosition'), 'RG')
    uvm = g.op('Divide', A=g.op('Multiply', A=wp, B=(0.01, -0.01)), B=g.scal('TileM', 1.7))
    alb = g.ech(g.tex('T_Albedo', 'albedo'), uvm, ST.SAMPLERTYPE_COLOR)
    nrm = g.ech(g.tex('T_Normale', 'normale'), uvm, ST.SAMPLERTYPE_NORMAL)
    rug = g.ech(g.tex('T_Rugosite', 'rugosite'), uvm, ST.SAMPLERTYPE_MASKS)
    hau = g.ech(g.tex('T_Hauteur', 'hauteur'), uvm, ST.SAMPLERTYPE_LINEAR_GRAYSCALE)
    # feuilles eparses : seuil de hauteur (texture couvrante ScatteredLeaves009) qui monte du tronc (SeuilCentre) vers
    # le bord du decalque (1,05 : plus rien) et module par un bruit lent (amas) : seules les feuilles « du dessus »
    # restent en peripherie, pas de transparence en fondu
    uv = g.e('TextureCoordinate', coordinate_index=0)
    d = g.op('Multiply', A=g.op('Distance', A=uv, B=(0.5, 0.5)), B=2.0)
    tb = g.e('TextureObjectParameter', parameter_name='T_Bruit', texture=unreal.load_asset('/Game/PJ/Textures/PJ/T_PJ_BruitMacro'), group='Textures')
    nb = g.ech(tb, g.op('Divide', A=uvm, B=g.scal('AmasEchelleM', 1.5)), ST.SAMPLERTYPE_MASKS)
    t = g.op('LinearInterpolate', A=g.scal('SeuilCentre', 0.42), B=1.05, Alpha=g.op('SmoothStep', Min=0.15, Max=1.0, Value=d))
    t = g.op('Add', A=t, B=g.op('Multiply', A=g.op('Subtract', A=g.mask(nb, 'R'), B=0.5), B=g.scal('AmasForce', 0.5)))
    h = g.mask(hau, 'R')
    op = g.op('Multiply', A=g.op('SmoothStep', Min=t, Max=g.op('Add', A=t, B=0.03), Value=h), B=g.scal('Densite', 1.0))
    # faces raides (faces de bordure, murets) : pas de feuilles collees a la verticale
    wpd = g.e('WorldPosition')
    nrm = g.op('Normalize', VectorInput=g.op('CrossProduct', A=g.op('DDX', Value=wpd), B=g.op('DDY', Value=wpd)))
    nz = g.op('Abs', x=g.mask(nrm, 'B'))
    plat = g.op('Saturate', x=g.op('Multiply', A=g.op('Subtract', A=nz, B=g.scal('NzMin', 0.6)), B=4.0))
    op = g.op('Saturate', x=g.op('Multiply', A=op, B=plat))
    teinte = g.e('VectorParameter', parameter_name='Teinte', default_value=unreal.LinearColor(1, 1, 1, 1), group='Feuilles')
    bc = g.op('Multiply', A=g.op('Multiply', A=g.mask(alb, 'RGB'), B=(teinte, 'RGB')), B=g.scal('Luminosite', 0.9))
    MEL.connect_material_property(bc, '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nrm, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(g.op('Saturate', x=g.op('Add', A=g.mask(rug, 'G'), B=0.1)), '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(op, '', unreal.MaterialProperty.MP_OPACITY)
    MEL.layout_material_expressions(m)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    mi = unreal.load_asset(MI) if EAL.does_asset_exist(MI) else \
        AT.create_asset('MI_PJ_Feuilles_Decal', '/Game/PJ/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', m)
    MEL.clear_all_material_instance_parameters(mi)
    MEL.set_material_instance_scalar_parameter_value(mi, 'Densite', float(A['densite']))
    # feuilles d'octobre a terre : brun-jaune, quelques jaunes (ScatteredLeaves009 tres orangee : moyenne 0,30 / 0,16 / 0,05 ;
    # visee ~0,21 / 0,15 / 0,08 : lisibles sur l'enrobe a l'ombre, sans le ton peinture orange)
    MEL.set_material_instance_vector_parameter_value(mi, 'Teinte', unreal.LinearColor(0.50, 0.68, 1.15, 1.0))
    MEL.set_material_instance_scalar_parameter_value(mi, 'Luminosite', 1.4)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    return {'maitre': MAITRE, 'mi': MI, 'instructions_ps': MEL.get_statistics(m).num_pixel_shader_instructions}


R = {'materiau': maitre()}
nr = 0
for v in ACT.get_all_level_actors():
    if v.get_actor_label() in ('PJ_PCG_Arbres', 'PJ_PCG_Herbe', 'PJ_PCG_Clotures', 'PJ_PCG_Mobilier'):
        for c in v.get_components_by_class(unreal.InstancedStaticMeshComponent):
            sm = c.get_editor_property('static_mesh')
            nom = sm.get_name() if sm else ''
            if not nom.startswith(('SM_Grass', 'SM_SmallGrass', 'SM_Leaf')):
                c.set_editor_property('receives_decals', False)
                nr += 1
R['ism_sans_decalques'] = nr
for a in list(ACT.get_all_level_actors()):
    if a.get_actor_label().startswith('PJ_Feuilles_'):
        ACT.destroy_actor(a)
n = 0
if A['points']:
    mi = unreal.load_asset(MI)
    pts = json.load(open(A['points'], encoding='utf-8'))['points']
    for p in pts:
        if p['x']['famille'] not in ('Oak', 'Maple', 'WhiteAsh', 'Jeune'):
            continue
        c = p['x'].get('couronne_data') or 0.0
        r = max(2.0, A['facteur_rayon'] * max(c, 2.0) * 1.0)
        X, Y, Z = repere.local_vers_ue(*p['p'])
        yaw = (p['graine'] % 360)
        d = ACT.spawn_actor_from_class(unreal.DecalActor, unreal.Vector(X, Y, Z + 20.0),
                                       unreal.Rotator(roll=0.0, pitch=-90.0, yaw=float(yaw)))
        d.set_actor_label(f"PJ_Feuilles_{p['id']}")
        d.set_folder_path('PJ_Feuilles')
        dc = d.get_component_by_class(unreal.DecalComponent)
        dc.set_decal_material(mi)
        dc.set_editor_property('decal_size', unreal.Vector(100.0 * A['prof_m'], 100.0 * r, 100.0 * r))
        dc.set_editor_property('sort_order', n % 7)
        n += 1
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
R['decalques'] = n
RESULT = R
