"""[éditeur] Construit les matériaux du sol V2 dans D:/ClaudeADAS : textures, maîtres, instances.

    MCP pj_tools.run_python_file(path, '{"etapes": ["textures", "maitres", "instances"], "forcer_textures": false}')
    (ou python recon/pcg/ue/materiaux/materiaux.py construire)

Déterministe et rejouable : les textures absentes sont importées (toutes si forcer_textures), les réglages
d'import sont réappliqués ; chaque maître est vidé puis reconstruit nœud par nœud (MaterialEditingLibrary) ;
chaque MI est créée ou mise à jour. Données : catalogue.py, mesures_textures.json, etalonnage.json.
- Textures : /Game/PJ/Textures/CC0/<dossier>/T_<dossier>_<role> (albédo sRGB « Default », normales
  « Normalmap » avec Flip Green Channel (sources OpenGL), rugosité et AO « Masks » linéaires, hauteur
  « Grayscale » 16 bits linéaire), /Game/PJ/Textures/CitySample/T_CS_<fichier>, /Game/PJ/Textures/PJ/T_PJ_*.
  Virtual texturing désactivé (2K, peu de textures : le streaming classique suffit).
- Maîtres (/Game/PJ/Materials/Maitres) : M_PJ_Sol, M_PJ_Remplissage (+ déplacement Nanite, tessellation, second lit
  mêlé par bruit : switch Melange),
  M_PJ_Bordure (instances : aléa et données d'instance cd), M_PJ_Peinture (masqué, recette peinture.json),
  M_PJ_Eclat (éclats 3D des remplissages : palette par instance, détail, fibres), M_PJ_Touffe (touffes d'herbe 3D,
  feuillage deux faces).
- Instances : /Game/PJ/Materials/MI_<materiau_id>[__carla|__citysample], MI_PJ_Peinture_<couleur>_u<usure>.
"""
import importlib
import json
import os
import sys
import time

import unreal

ICI = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else 'D:/ClaudeCode_RoadCreation/recon/pcg/ue/materiaux'
if ICI not in sys.path:
    sys.path.insert(0, ICI)
import catalogue as C  # noqa: E402
importlib.reload(C)

A = dict(etapes=['textures', 'maitres', 'instances'], forcer_textures=False, seulement=None)
A.update(globals().get('ARGS') or {})
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
TCS = unreal.TextureCompressionSettings
ST = unreal.MaterialSamplerType
MAG_DEPLACEMENT_CM = 10.0          # displacement_scaling.magnitude du maître de remplissage (DeplacementCm s'y rapporte)
journal = {'textures': [], 'maitres': {}, 'instances': [], 'erreurs': []}

# ======================================================================= textures
REGLAGES_TEX = {   # role -> (compression, sRGB, flip vert, groupe)
    'albedo': (TCS.TC_DEFAULT, True, False, unreal.TextureGroup.TEXTUREGROUP_WORLD),
    'normale': (TCS.TC_NORMALMAP, False, True, unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP),
    'rugosite': (TCS.TC_MASKS, False, False, unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR),
    'ao': (TCS.TC_MASKS, False, False, unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR),
    'hauteur': (TCS.TC_GRAYSCALE, False, False, unreal.TextureGroup.TEXTUREGROUP_WORLD),
    'bruit': (TCS.TC_MASKS, False, False, unreal.TextureGroup.TEXTUREGROUP_WORLD),
    'masque': (TCS.TC_VECTOR_DISPLACEMENTMAP, False, False, unreal.TextureGroup.TEXTUREGROUP_WORLD),
}


def importer_texture(src, dossier, nom, role):
    chemin = f'{dossier}/{nom}'
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    nouveau = not EAL.does_asset_exist(chemin)
    if nouveau or A['forcer_textures']:
        t = unreal.AssetImportTask()
        for k, v in dict(filename=src, destination_path=dossier, destination_name=nom, automated=True,
                         replace_existing=True, save=False).items():
            t.set_editor_property(k, v)
        AT.import_asset_tasks([t])
    tex = unreal.load_asset(chemin)
    if not isinstance(tex, unreal.Texture2D):
        raise RuntimeError(f'import échoué : {src} -> {chemin}')
    comp, srgb, flip, grp = REGLAGES_TEX[role]
    for k, v in dict(compression_settings=comp, srgb=srgb, flip_green_channel=flip, lod_group=grp,
                     virtual_texture_streaming=False).items():
        if tex.get_editor_property(k) != v:
            tex.set_editor_property(k, v)
    EAL.save_loaded_asset(tex, False)
    journal['textures'].append({'asset': chemin, 'role': role, 'source': src.replace('\\', '/'), 'importe': nouveau or A['forcer_textures'],
                                'taille': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()]})
    return tex


def etape_textures(mesures):
    for d in C.dossiers_cc0():
        meta = json.load(open(f'{C.CC0_DIR}/{d}/meta.json', encoding='utf-8'))
        for t in meta['textures']:
            if t['role'] in REGLAGES_TEX:
                importer_texture(f'{C.CC0_DIR}/{d}/{t["fichier"]}', f'{C.UE_TEX_CC0}/{d}', f'T_{d}_{t["role"]}', t['role'])
        h = mesures['cc0'][d].get('hauteur')
        if h:
            importer_texture(f'{C.DEPOT}/{h["fichier"]}', f'{C.UE_TEX_CC0}/{d}', f'T_{d}_hauteur', 'hauteur')
    vus = set()
    for cs in C.CITYSAMPLE.values():
        for role, f in cs.items():
            if f not in vus:
                vus.add(f)
                importer_texture(f'{C.CS_DIR}/{f}.png', C.UE_TEX_CS, f'T_CS_{f}', role)
    importer_texture(f'{C.DERIVE_DIR}/pj/pj_bruit_macro.png', C.UE_TEX_PJ, 'T_PJ_BruitMacro', 'bruit')
    importer_texture(f'{C.DERIVE_DIR}/pj/masque_usure_peinture.png', C.UE_TEX_PJ, 'T_PJ_MasqueUsurePeinture', 'masque')


# ======================================================================= graphe
class Graphe:
    """Construction compacte d'un graphe de matériau (sorties via MakeMaterialAttributes)."""

    def __init__(self, m):
        self.m = m
        self.n = 0
        MEL.delete_all_material_expressions(m)            # ne retire pas tout en 5.8 : purge nœud par nœud
        for ex in list(MEL.get_material_expressions(m)):
            MEL.delete_material_expression(m, ex)
        if MEL.get_num_material_expressions(m):
            raise RuntimeError(f'{m.get_name()} : {MEL.get_num_material_expressions(m)} nœuds non supprimés')
        m.set_editor_property('use_material_attributes', True)
        self.mma = self.e('MakeMaterialAttributes')
        MEL.connect_material_property(self.mma, '', unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)

    def e(self, cls, **props):
        self.n += 1
        x = -400 - 260 * (self.n % 12)
        y = 120 * (self.n // 12)
        ex = MEL.create_material_expression(self.m, getattr(unreal, 'MaterialExpression' + cls), x, y)
        for k, v in props.items():
            ex.set_editor_property(k, v)
        return ex

    def _src(self, v):
        """v : expression | (expression, sortie) | nombre | tuple de 2-4 nombres."""
        if isinstance(v, tuple) and len(v) == 2 and not isinstance(v[0], (int, float)):
            return v
        if isinstance(v, (int, float)):
            return (self.e('Constant', r=float(v)), '')
        if isinstance(v, (tuple, list)):
            if len(v) == 2:
                return (self.e('Constant2Vector', r=float(v[0]), g=float(v[1])), '')
            if len(v) == 3:
                return (self.e('Constant3Vector', constant=unreal.LinearColor(*[float(x) for x in v], 1.0)), '')
            return (self.e('Constant4Vector', constant=unreal.LinearColor(*[float(x) for x in v])), '')
        return (v, '')

    def c(self, v, dst, entree):
        ex, sortie = self._src(v)
        if not MEL.connect_material_expressions(ex, sortie, dst, entree):
            raise RuntimeError(f'connexion impossible : {ex.get_class().get_name()}.{sortie} -> '
                               f'{dst.get_class().get_name()}.{entree}')

    def op(self, cls, **entrees):
        ex = self.e(cls)
        for k, v in entrees.items():
            self.c(v, ex, {'x': '', 'ap': 'A > B', 'ae': 'A == B', 'al': 'A < B'}.get(k, k))
        return ex

    # opérations
    def mul(self, a, b): return self.op('Multiply', A=a, B=b)
    def add(self, a, b): return self.op('Add', A=a, B=b)
    def sub(self, a, b): return self.op('Subtract', A=a, B=b)
    def div(self, a, b): return self.op('Divide', A=a, B=b)
    def lerp(self, a, b, t): return self.op('LinearInterpolate', A=a, B=b, Alpha=t)
    def sat(self, a): return self.op('Saturate', x=a)
    def frac(self, a): return self.op('Frac', x=a)
    def sin(self, a): return self.op('Sine', x=a)
    def dot(self, a, b): return self.op('DotProduct', A=a, B=b)
    def app(self, a, b): return self.op('AppendVector', A=a, B=b)
    def mini(self, a, b): return self.op('Min', A=a, B=b)
    def maxi(self, a, b): return self.op('Max', A=a, B=b)
    def pow(self, a, b): return self.op('Power', Base=a, Exp=b)
    def norm(self, a): return self.op('Normalize', VectorInput=a)
    def smooth(self, lo, hi, v): return self.op('SmoothStep', Min=lo, Max=hi, Value=v)
    def step(self, bord, x): return self.op('Step', Y=bord, X=x)          # 1 si x >= bord

    def clamp(self, a, lo, hi):
        return self.op('Clamp', x=a, Min=lo, Max=hi)

    def si_sup(self, a, b, alors, sinon):
        return self.op('If', A=a, B=b, ap=alors, ae=sinon, al=sinon)

    def masque(self, a, canaux):
        ex = self.e('ComponentMask', r='R' in canaux, g='G' in canaux, b='B' in canaux, a='A' in canaux)
        self.c(a, ex, '')
        return ex

    # paramètres
    def scal(self, nom, defaut, groupe):
        return self.e('ScalarParameter', parameter_name=nom, default_value=float(defaut), group=groupe)

    def vec(self, nom, defaut, groupe):
        d = list(defaut) + [1.0] * (4 - len(defaut))
        return (self.e('VectorParameter', parameter_name=nom, default_value=unreal.LinearColor(*d), group=groupe), 'RGB')

    def switch(self, nom, vrai, faux, defaut, groupe='Options'):
        ex = self.e('StaticSwitchParameter', parameter_name=nom, default_value=bool(defaut), group=groupe)
        self.c(vrai, ex, 'True')
        self.c(faux, ex, 'False')
        return ex

    def texobj(self, nom, defaut, groupe='Textures'):
        return self.e('TextureObjectParameter', parameter_name=nom, texture=unreal.load_asset(defaut), group=groupe)

    def ech(self, tex, uv, type_):
        ex = self.e('TextureSample', sampler_type=type_,
                    sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        self.c(tex, ex, 'Tex')
        self.c(uv, ex, 'UVs')
        return ex

    def sortie(self, nom, v):
        self.c(v, self.mma, nom)


C37, S37 = 0.79864, 0.60182        # rotation de 37° du second échantillonnage (anti-répétition)


def uv_metres(g):
    """UV0 (= primvars:st, mètres) ou, en repli, position monde XY (cm -> m ; même sens que l'UV0 importé)."""
    uv0 = g.e('TextureCoordinate', coordinate_index=0)
    wp = (g.e('WorldPosition'), 'XY')
    return g.switch('UV_Monde', g.mul(wp, (0.01, 0.01)), uv0, False, 'UV')


def normale_force(g, n, force):
    return g.norm(g.app(g.mul(g.masque(n, 'RG'), force), g.masque(n, 'B')))


def graphe_sol(g, remplissage, defauts):
    P = 'Couleur'
    tile = g.scal('TileM', 2.0, 'Tuilage')
    echB = g.scal('EchelleB', 1.37, 'Tuilage')
    anti = g.scal('AntiRepetition', 0.5, 'Tuilage')
    m_ech = g.scal('MacroEchelleM', 8.0, 'Macro')
    m_force = g.scal('MacroForce', 0.1, 'Macro')
    lumi = g.scal('Luminosite', 1.0, P)
    teinte = g.vec('Teinte', (1, 1, 1), P)
    r_mul = g.scal('RugositeMul', 0.7, 'Rugosite')
    r_aj = g.scal('RugositeAjout', 0.2, 'Rugosite')
    spec = g.scal('Specular', 0.5, 'Rugosite')
    n_force = g.scal('NormalForce', 1.0, 'Relief')
    ao_force = g.scal('AOForce', 1.0, 'Relief')
    sal = g.scal('Salissure', 0.0, 'Salissure')
    sal_cav = g.scal('SalissureCavite', 0.5, 'Salissure')
    t_sal = g.vec('TeinteSalissure', (0.55, 0.50, 0.45), 'Salissure')
    # couleur de sommet : R usure, G salissure, B graine (CONTRAT_EXPORT.md § 3)
    vc = g.e('VertexColor')
    cs = g.switch('CouleurSommet', (vc, ''), (0.0, 0.0, 0.0), False, 'UV')
    uvm = g.add(uv_metres(g), g.mul(g.masque(cs, 'B'), (37.13, 17.71)))
    uvA = g.div(uvm, tile)
    uvR = g.app(g.dot(uvm, (C37, -S37)), g.dot(uvm, (S37, C37)))
    uvB = g.add(g.div(uvR, g.mul(tile, echB)), (0.37, 0.71))
    tb = g.texobj('T_Bruit', C.T_BRUIT)
    n1 = g.ech(tb, g.div(uvm, m_ech), ST.SAMPLERTYPE_MASKS)
    n2 = g.ech(tb, g.add(g.div(uvm, g.mul(m_ech, 3.7)), (0.5, 0.25)), ST.SAMPLERTYPE_MASKS)
    mrep = g.mul(g.sat(g.add(g.mul(g.sub((n1, 'R'), 0.5), 4.0), 0.5)), anti)
    ta = g.texobj('T_Albedo', defauts['albedo'])
    tn = g.texobj('T_Normale', defauts['normale'])
    tr = g.texobj('T_Rugosite', defauts['rugosite'])
    tao = g.texobj('T_AO', defauts['ao'])
    aA, aB = g.ech(ta, uvA, ST.SAMPLERTYPE_COLOR), g.ech(ta, uvB, ST.SAMPLERTYPE_COLOR)
    alb = g.lerp((aA, 'RGB'), (aB, 'RGB'), mrep)
    # contraste de l'albédo autour de la moyenne mesurée de la texture (moyenne conservée)
    alb = g.lerp(g.vec('MoyenneTexture', (0.25, 0.25, 0.25), P), alb, g.scal('Contraste', 1.0, P))
    nA, nB = g.ech(tn, uvA, ST.SAMPLERTYPE_NORMAL), g.ech(tn, uvB, ST.SAMPLERTYPE_NORMAL)
    nBrg = g.masque(nB, 'RG')                          # normale de B ramenée dans le repère des UV (rotation inverse)
    nBt = g.app(g.app(g.dot(nBrg, (C37, S37)), g.dot(nBrg, (-S37, C37))), (nB, 'B'))
    nrm = g.lerp((nA, 'RGB'), nBt, mrep)
    rgh = g.lerp((g.ech(tr, uvA, ST.SAMPLERTYPE_MASKS), 'G'), (g.ech(tr, uvB, ST.SAMPLERTYPE_MASKS), 'G'), mrep)
    ao = g.lerp((g.ech(tao, uvA, ST.SAMPLERTYPE_MASKS), 'R'), (g.ech(tao, uvB, ST.SAMPLERTYPE_MASKS), 'R'), mrep)
    if remplissage:
        th = g.texobj('T_Hauteur', defauts['hauteur'])
        hA = g.switch('HauteurCanalA', (aA, 'A'), (g.ech(th, uvA, ST.SAMPLERTYPE_LINEAR_GRAYSCALE), 'R'), False, 'Deplacement')
        hB = g.switch('HauteurCanalA', (aB, 'A'), (g.ech(th, uvB, ST.SAMPLERTYPE_LINEAR_GRAYSCALE), 'R'), False, 'Deplacement')
        h = g.sub(g.lerp(hA, hB, mrep), g.scal('HauteurCentre', 0.5, 'Deplacement'))      # hauteur centrée
        alb, nrm, rgh, h = melange(g, uvm, tb, alb, nrm, rgh, h, teinte, defauts)
    # variation macro de luminance (deux échelles)
    mv = g.add(1.0, g.mul(m_force, g.add(g.sub((n1, 'G'), 0.5), g.mul(g.sub((n2, 'G'), 0.5), 0.7))))
    alb = g.mul(alb, mv)
    usure = g.masque(cs, 'R')
    alb = g.mul(alb, g.add(1.0, g.mul(usure, 0.12)))
    # salissure : paramètre + couleur de sommet G, par plaques (bruit lent), concentrée dans les creux (AO)
    s_tot = g.sat(g.add(sal, g.masque(cs, 'G')))
    cav = g.lerp(1.0, g.mul(g.sub(1.0, ao), 2.5), sal_cav)
    s_m = g.sat(g.mul(g.mul(s_tot, g.add(0.4, g.mul((n2, 'R'), 1.2))), cav))
    alb = g.lerp(alb, g.mul(alb, t_sal), s_m)
    g.sortie('BaseColor', g.mul(g.mul(alb, teinte), lumi))
    g.sortie('Roughness', g.sat(g.add(g.add(g.mul(rgh, r_mul), r_aj), g.add(g.mul(usure, 0.05), g.mul(s_m, 0.04)))))
    g.sortie('Specular', spec)
    g.sortie('Normal', normale_force(g, nrm, n_force))
    g.sortie('AmbientOcclusion', g.lerp(1.0, ao, ao_force))
    if remplissage:
        dep = g.scal('DeplacementCm', 3.0, 'Deplacement')
        g.sortie('Displacement', g.add(0.5, g.mul(h, g.div(dep, MAG_DEPLACEMENT_CM))))


def melange(g, uvm, tb, alb, nrm, rgh, h, teinte, defauts):
    """Second lit (switch statique Melange, catalogue.MELANGE : BRF vieilli) mêlé au premier par un masque de bruit lent
    (T_Bruit R, uniforme : seuil 1 - MelangeTaux, moyenne du masque = MelangeTaux) décalé par la hauteur du lit 2.
    Albédo du lit 2 : contraste autour de MoyenneTexture2, x Melange2Rapport / Teinte (Teinte ne teinte que le lit 1,
    Luminosite s'applique aux deux : albédo final du lit 2 = Luminosite x Melange2Rapport x texture)."""
    M = 'Melange'
    uv2 = g.add(g.div(uvm, g.scal('TileM2', 2.0, M)), (0.21, 0.53))
    a2 = g.ech(g.texobj('T_Albedo2', defauts['albedo2']), uv2, ST.SAMPLERTYPE_COLOR)
    alb2 = g.mul(g.lerp(g.vec('MoyenneTexture2', (0.25, 0.25, 0.25), M), (a2, 'RGB'), g.scal('Contraste2', 1.0, M)),
                 g.div(g.vec('Melange2Rapport', (1, 1, 1), M), teinte))
    n2 = (g.ech(g.texobj('T_Normale2', defauts['normale2']), uv2, ST.SAMPLERTYPE_NORMAL), 'RGB')
    r2 = (g.ech(g.texobj('T_Rugosite2', defauts['rugosite2']), uv2, ST.SAMPLERTYPE_MASKS), 'G')
    h2 = g.sub((g.ech(g.texobj('T_Hauteur2', defauts['hauteur2']), uv2, ST.SAMPLERTYPE_LINEAR_GRAYSCALE), 'R'),
               g.scal('HauteurCentre2', 0.5, M))
    nb = g.ech(tb, g.add(g.div(uvm, g.scal('MelangeEchelleM', 2.0, M)), (0.13, 0.61)), ST.SAMPLERTYPE_MASKS)
    x = g.sub(g.add((nb, 'R'), g.mul(h2, g.scal('MelangeHauteur', 0.6, M))), g.sub(1.0, g.scal('MelangeTaux', 0.0, M)))
    m = g.sat(g.add(g.div(x, g.scal('MelangeTransition', 0.12, M)), 0.5))
    return (g.switch(M, g.lerp(alb, alb2, m), alb, False, M), g.switch(M, g.lerp(nrm, n2, m), nrm, False, M),
            g.switch(M, g.lerp(rgh, r2, m), rgh, False, M), g.switch(M, g.lerp(h, h2, m), h, False, M))


def graphe_bordure(g, defauts):
    tile = g.scal('TileM', 2.0, 'Tuilage')
    m_ech = g.scal('MacroEchelleM', 1.3, 'Macro')
    m_force = g.scal('MacroForce', 0.08, 'Macro')
    lumi = g.scal('Luminosite', 1.0, 'Couleur')
    teinte = g.vec('Teinte', (1, 1, 1), 'Couleur')
    var = g.scal('VariationTeinte', 0.04, 'Couleur')
    r_mul = g.scal('RugositeMul', 0.7, 'Rugosite')
    r_aj = g.scal('RugositeAjout', 0.3, 'Rugosite')
    spec = g.scal('Specular', 0.5, 'Rugosite')
    n_force = g.scal('NormalForce', 1.0, 'Relief')
    ao_force = g.scal('AOForce', 1.0, 'Relief')
    sal_p = g.scal('Salissure', 0.3, 'Salissure')
    sal_haut = g.scal('SalissureHaut', C.SALISSURE_HAUT, 'Salissure')
    bas_h = g.scal('BasHauteurCm', 6.0, 'Salissure')
    bas_d = g.scal('BasDecalageCm', 0.0, 'Salissure')
    t_sal = g.vec('TeinteSalissure', C.TEINTE_SALISSURE_BORDURE, 'Salissure')
    joint_l = g.scal('JointLargeurCm', 1.2, 'Joints')
    mousse_p = g.scal('Mousse', 0.0, 'Joints')
    c_mousse = g.vec('CouleurMousse', (0.045, 0.060, 0.025), 'Joints')
    usure_p = g.scal('Usure', 0.0, 'Salissure')
    # aléa par élément : PerInstanceRandom (ISM/PCG) + hachage de la position de l'objet (acteurs isolés)
    op = g.e('ObjectPositionWS')
    hsh = g.frac(g.mul(g.sin(g.dot(g.frac(g.mul(op, 0.01371)), (12.9898, 78.233, 37.719))), 43758.5453))
    rnd = g.frac(g.add(g.e('PerInstanceRandom'), hsh))
    # données d'instance (points/bordures.json cd = [usure, salissure, mousse_joints, herbe_joints, teinte]) ;
    # absentes = valeur par défaut négative -> paramètre du MI (teinte : aléa)
    cd = [g.e('PerInstanceCustomData', data_index=i, const_default_value=-9.0) for i in range(7)]
    # cd5 = fil d'eau dans le repère de l'élément (cm ; pilote/points_ue.py : z_pied des points, pivot des prototypes
    # Houdini sous le bloc) ; absent -> BasDecalageCm du MI. cd6 = demi-longueur de l'élément (cm, pivot au milieu) :
    # distance aux abouts sans ObjectLocalBounds (bornes du composant, pas de l'instance, sur un ISM)
    bas_d = g.si_sup(cd[5], -0.5, cd[5], bas_d)
    usure = g.si_sup(cd[0], -0.5, cd[0], usure_p)
    sal = g.si_sup(cd[1], -0.5, cd[1], sal_p)
    mousse = g.si_sup(cd[2], -0.5, cd[2], mousse_p)
    # teinte : gain par élément (cd4 = teinte des points, 0,88-1,12) ; absent -> alea ±VariationTeinte
    gain_t = g.si_sup(cd[4], -1.5, cd[4], g.add(1.0, g.mul(var, g.sub(g.mul(rnd, 2.0), 1.0))))
    uv = g.add(g.e('TextureCoordinate', coordinate_index=0), g.mul(g.app(rnd, g.frac(g.mul(rnd, 7.31))), 5.0))
    uvT = g.div(uv, tile)
    ta, tn = g.texobj('T_Albedo', defauts['albedo']), g.texobj('T_Normale', defauts['normale'])
    tr, tao = g.texobj('T_Rugosite', defauts['rugosite']), g.texobj('T_AO', defauts['ao'])
    tb = g.texobj('T_Bruit', C.T_BRUIT)
    alb = (g.ech(ta, uvT, ST.SAMPLERTYPE_COLOR), 'RGB')
    alb = g.lerp(g.vec('MoyenneTexture', (0.35, 0.35, 0.35), 'Couleur'), alb, g.scal('Contraste', 1.0, 'Couleur'))
    nrm = (g.ech(tn, uvT, ST.SAMPLERTYPE_NORMAL), 'RGB')
    rgh = (g.ech(tr, uvT, ST.SAMPLERTYPE_MASKS), 'G')
    ao = (g.ech(tao, uvT, ST.SAMPLERTYPE_MASKS), 'R')
    nm = g.ech(tb, g.div(uv, m_ech), ST.SAMPLERTYPE_MASKS)
    alb = g.mul(alb, g.add(1.0, g.mul(m_force, g.sub((nm, 'G'), 0.5))))
    alb = g.mul(alb, gain_t)
    # salissure : x (1 - K_SAL·s·w), w = 1 au pied (fil d'eau, z local <= BasDecalageCm) -> SalissureHaut au-dessus
    lp = g.e('LocalPosition')
    bas = g.sat(g.div(g.sub(bas_h, g.sub((lp, 'Z'), bas_d)), bas_h))
    w = g.lerp(sal_haut, 1.0, bas)
    s = g.sat(g.mul(g.mul(sal, w), g.add(0.6, g.mul((nm, 'R'), 0.8))))
    # joints : abouts (x local près des bornes de l'objet) plus sales, mousse
    lb = g.e('ObjectLocalBounds')
    x = g.masque((lp, 'XYZ'), 'R')
    dx_b = g.mini(g.sub(x, g.masque((lb, 'Min'), 'R')), g.sub(g.masque((lb, 'Max'), 'R'), x))
    dx = g.si_sup(cd[6], -0.5, g.sub(cd[6], g.maxi(x, g.mul(x, -1.0))), dx_b)
    jm = g.sat(g.sub(1.0, g.div(dx, joint_l)))
    s = g.sat(g.add(s, g.mul(g.mul(jm, sal), 0.6)))
    alb = g.mul(alb, g.lerp(1.0, t_sal, s))
    alb = g.mul(alb, g.sub(1.0, g.mul(s, C.K_SAL)))
    alb = g.mul(alb, g.add(1.0, g.mul(usure, 0.06)))
    base = g.mul(g.mul(alb, teinte), lumi)
    mo = g.sat(g.mul(g.mul(mousse, jm), g.add(0.5, (nm, 'B'))))
    g.sortie('BaseColor', g.lerp(base, c_mousse, mo))
    g.sortie('Roughness', g.sat(g.add(g.add(g.mul(rgh, r_mul), r_aj), g.add(g.mul(s, 0.05), g.mul(mo, 0.2)))))
    g.sortie('Specular', spec)
    g.sortie('Normal', normale_force(g, nrm, n_force))
    g.sortie('AmbientOcclusion', g.lerp(1.0, ao, ao_force))


def alea_instance(g):
    """Aléa par instance (PerInstanceRandom des ISM / HISM + hachage de la position de l'objet) et deux dérivés."""
    op = g.e('ObjectPositionWS')
    hsh = g.frac(g.mul(g.sin(g.dot(g.frac(g.mul(op, 0.01371)), (12.9898, 78.233, 37.719))), 43758.5453))
    rnd = g.frac(g.add(g.e('PerInstanceRandom'), hsh))
    return rnd, g.frac(g.add(g.mul(rnd, 7.31), 0.13)), g.frac(g.add(g.mul(rnd, 13.71), 0.57))


def graphe_eclat(g, defauts):
    """M_PJ_Eclat (revue UE du 10/10 : éclats sur M_PJ_Bordure à tuile de 30 m = une tache de texture par éclat, copeaux
    bleutés ou blancs, BRF presque noir à 10 m) : couleur par éclat tirée dans une palette de 3 classes (parts Part1,
    Part2, reste ; albédo de Couleur<k>A à Couleur<k>B : palette de recon/pcg/houdini/pj_ilot.py, comme Karma) ; détail
    de luminance de la texture du lit (UV boîte du prototype en m, TileM, décalage par instance) ; fibres du bois
    (bruit étiré le long du copeau, FibreU x FibreV) ; normale du lit ; sans salissure ni joint."""
    P = 'Palette'
    rnd, r2, r3 = alea_instance(g)
    p1, p2 = g.scal('Part1', 0.5, P), g.scal('Part2', 0.4, P)
    c = [g.lerp(g.vec(f'Couleur{k}A', (0.2, 0.2, 0.2), P), g.vec(f'Couleur{k}B', (0.3, 0.3, 0.3), P), r2) for k in (1, 2, 3)]
    c23 = g.si_sup(rnd, g.add(p1, p2), c[2], c[1])
    col = g.si_sup(rnd, p1, c23, c[0])
    uv = g.add(g.e('TextureCoordinate', coordinate_index=0), g.mul(g.app(rnd, r3), 5.0))
    uvT = g.div(uv, g.scal('TileM', 0.3, 'Tuilage'))
    ta, tn = g.texobj('T_Albedo', defauts['albedo']), g.texobj('T_Normale', defauts['normale'])
    tb = g.texobj('T_Bruit', C.T_BRUIT)
    alb = (g.ech(ta, uvT, ST.SAMPLERTYPE_COLOR), 'RGB')
    w = (0.2126, 0.7152, 0.0722)
    ratio = g.clamp(g.div(g.dot(alb, w), g.maxi(g.dot(g.vec('MoyenneTexture', (0.2, 0.2, 0.2), 'Couleur'), w), 0.01)), 0.2, 2.5)
    detail = g.lerp(1.0, ratio, g.scal('DetailForce', 0.6, 'Couleur'))
    fib_uv = g.mul(uv, g.app(g.scal('FibreU', 6.0, 'Fibres'), g.scal('FibreV', 90.0, 'Fibres')))
    nf = (g.ech(tb, fib_uv, ST.SAMPLERTYPE_MASKS), 'G')
    fib = g.lerp(1.0, g.add(0.55, g.mul(nf, 0.9)), g.scal('FibreForce', 0.0, 'Fibres'))
    base = g.mul(g.mul(col, detail), fib)
    nrm = (g.ech(tn, uvT, ST.SAMPLERTYPE_NORMAL), 'RGB')
    g.sortie('BaseColor', base)
    g.sortie('Roughness', g.scal('Rugosite', 0.8, 'Rugosite'))
    g.sortie('Specular', g.scal('Specular', 0.4, 'Rugosite'))
    g.sortie('Normal', normale_force(g, nrm, g.scal('NormalForce', 1.0, 'Relief')))


def graphe_touffe(g, defauts):
    """M_PJ_Touffe (revue UE du 10/10 : franges de touffes noires, herbe sèche blanche) : brins de touffe (prototypes
    pj_decals, hauteur unitaire = 100 cm locaux), modèle d'ombrage feuillage deux faces (transmission) : couleur du pied
    (CouleurPied) à la pointe (Couleur), part PartSeche de touffes sèches (CouleurSeche, albédo <= 0,25), teinte par
    instance ±VariationTeinte, transmission = couleur x GainTransmission."""
    P = 'Couleur'
    rnd, r2, _ = alea_instance(g)
    h = g.sat(g.div(g.masque(g.e('LocalPosition'), 'B'), 100.0))
    base = g.lerp(g.vec('CouleurPied', (0.035, 0.045, 0.02), P), g.vec('Couleur', (0.07, 0.085, 0.035), P),
                  g.smooth(0.0, 0.6, h))
    seche = g.step(g.sub(1.0, g.scal('PartSeche', 0.15, P)), rnd)
    col = g.lerp(base, g.mul(g.vec('CouleurSeche', (0.2, 0.17, 0.09), P), g.lerp(0.6, 1.0, h)), seche)
    col = g.mul(col, g.add(1.0, g.mul(g.scal('VariationTeinte', 0.15, P), g.sub(g.mul(r2, 2.0), 1.0))))
    g.sortie('BaseColor', col)
    g.sortie('SubsurfaceColor', g.mul(col, g.scal('GainTransmission', 0.8, P)))
    g.sortie('Roughness', g.scal('Rugosite', 0.7, 'Rugosite'))
    g.sortie('Specular', g.scal('Specular', 0.35, 'Rugosite'))


def graphe_peinture(g, defauts):
    """Recette de assets/specs/peinture.json (usure par masque RGBA, seuils de la graine 1967) ; les manques
    laissent voir l'enrobé réel sous la marque (matériau masqué, posé à +3 mm)."""
    uvm = uv_metres(g)
    tile_m = g.scal('TileMasqueM', 4.0, 'Usure')
    seuil = g.scal('Seuil', 0.065, 'Usure')
    poids = g.vec('PoidsRGA', (0.7, 0.0, 0.3), 'Usure')
    fb = g.scal('FissureB', 2.0, 'Usure')
    fa = g.scal('FissureA', 2.0, 'Usure')
    salete = g.scal('Salete', 0.02, 'Usure')
    transp = g.scal('Transparence', 0.15, 'Usure')
    chroma = g.scal('Chroma', 1.0, 'Couleur')
    coul = g.vec('CouleurNeuve', (0.78, 0.78, 0.76), 'Couleur')
    rug = g.scal('Rugosite', 0.5, 'Couleur')
    spec = g.scal('Specular', 0.55, 'Couleur')
    tile_sol = g.scal('TileSol', 2.0, 'Sol')
    gain_sol = g.scal('SolGain', 1.0, 'Sol')
    moy_sol = g.vec('MoyenneSol', (0.26, 0.269, 0.247), 'Sol')
    n_sol = g.scal('NormaleSolForce', 0.6, 'Sol')
    tm = g.texobj('T_Masque', C.T_MASQUE_PEINTURE)
    M = g.ech(tm, g.div(uvm, tile_m), ST.SAMPLERTYPE_LINEAR_COLOR)
    rga = g.app(g.app((M, 'R'), (M, 'G')), (M, 'A'))
    score = g.dot(rga, poids)
    fis = g.mul(g.step(fb, (M, 'B')), g.step(fa, (M, 'A')))
    peint = g.mul(g.smooth(g.sub(seuil, 0.004), g.add(seuil, 0.004), score), g.sub(1.0, fis))
    s = g.sat(g.mul(salete, g.add(0.6, g.mul((M, 'A'), 0.8))))
    gris = g.dot(coul, (0.2126, 0.7152, 0.0722))
    coul_u = g.lerp(gris, coul, chroma)
    uvs = g.div(uvm, tile_sol)
    sol = g.mul((g.ech(g.texobj('T_SolAlbedo', defauts['albedo']), uvs, ST.SAMPLERTYPE_COLOR), 'RGB'), gain_sol)
    rel = g.pow(g.clamp(g.div(sol, moy_sol), 0.2, 3.0), transp)
    g.sortie('BaseColor', g.lerp(g.mul(coul_u, rel), sol, s))
    g.sortie('OpacityMask', peint)
    g.sortie('Roughness', g.sat(g.add(rug, g.mul(s, 0.15))))
    g.sortie('Specular', spec)
    nsol = (g.ech(g.texobj('T_SolNormale', defauts['normale']), uvs, ST.SAMPLERTYPE_NORMAL), 'RGB')
    g.sortie('Normal', normale_force(g, nsol, n_sol))


def creer_ou_charger(chemin, classe, fabrique):
    if EAL.does_asset_exist(chemin):
        return unreal.load_asset(chemin)
    d, n = chemin.rsplit('/', 1)
    return AT.create_asset(n, d, classe, fabrique)


def etape_maitres():
    d0 = 'enrobe_bbsg_ancien'
    defauts = {r: C.asset_texture_cc0(d0, r) for r in ('albedo', 'normale', 'rugosite', 'ao')}
    defauts['hauteur'] = C.asset_texture_cc0('brf_bois_concasse', 'hauteur')
    defauts.update({f'{r}2': C.asset_texture_cc0('brf_bois_gris', r) for r in ('albedo', 'normale', 'rugosite', 'hauteur')})
    for cle, chemin in C.MAITRES.items():
        if A['seulement'] and cle not in A['seulement']:
            continue
        t0 = time.time()
        m = creer_ou_charger(chemin, unreal.Material, unreal.MaterialFactoryNew())
        g = Graphe(m)
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if cle == 'peinture' else unreal.BlendMode.BLEND_OPAQUE)
        for k in ('used_with_nanite', 'used_with_instanced_static_meshes', 'used_with_static_mesh'):
            m.set_editor_property(k, True)
        if cle in ('sol', 'remplissage'):
            graphe_sol(g, cle == 'remplissage', defauts)
        elif cle == 'bordure':
            graphe_bordure(g, defauts)
        elif cle == 'eclat':
            graphe_eclat(g, {r: C.asset_texture_cc0('brf_bois_concasse', r) for r in ('albedo', 'normale')})
        elif cle == 'touffe':
            graphe_touffe(g, defauts)
            m.set_editor_property('two_sided', True)
            m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        else:
            graphe_peinture(g, defauts)
            m.set_editor_property('opacity_mask_clip_value', 0.5)
        if cle == 'remplissage':
            m.set_editor_property('enable_tessellation', True)
            ds = m.get_editor_property('displacement_scaling')
            ds.set_editor_property('magnitude', MAG_DEPLACEMENT_CM)
            ds.set_editor_property('center', 0.5)
            m.set_editor_property('displacement_scaling', ds)
        MEL.layout_material_expressions(m)
        MEL.recompile_material(m)
        EAL.save_loaded_asset(m, False)
        st = MEL.get_statistics(m)
        journal['maitres'][cle] = {'chemin': chemin, 'noeuds': MEL.get_num_material_expressions(m),
                                   'instructions_ps': st.num_pixel_shader_instructions,
                                   'echantillonneurs': st.num_samplers, 'duree_s': round(time.time() - t0, 2)}


# ======================================================================= instances
def appliquer_mi(mi, d):
    for role, chemin in d.get('textures', {}).items():
        nom = {'albedo': 'T_Albedo', 'normale': 'T_Normale', 'rugosite': 'T_Rugosite', 'ao': 'T_AO',
               'hauteur': 'T_Hauteur', 'masque': 'T_Masque', 'sol_albedo': 'T_SolAlbedo', 'sol_normale': 'T_SolNormale',
               'albedo2': 'T_Albedo2', 'normale2': 'T_Normale2', 'rugosite2': 'T_Rugosite2', 'hauteur2': 'T_Hauteur2'}[role]
        tex = unreal.load_asset(chemin)
        if tex is None:
            raise RuntimeError(f'{d["nom"]} : texture absente {chemin}')
        MEL.set_material_instance_texture_parameter_value(mi, nom, tex)
    if d['maitre'] in ('sol', 'remplissage') and 'ao' not in d.get('textures', {}):
        d['scalaires']['AOForce'] = 0.0                    # pas de carte d'AO : la texture par défaut ne doit pas assombrir
    for k, v in d.get('scalaires', {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in d.get('vecteurs', {}).items():
        v = list(v) + [1.0] * (4 - len(v))
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*[float(x) for x in v]))
    for k, v in d.get('switches', {}).items():
        MEL.set_material_instance_static_switch_parameter_value(mi, k, bool(v))


def mi_carla(d):
    """MI enfant du MI CARLA : aspect CARLA, luminosité étalonnée (facteur de luminance seulement)."""
    parent = unreal.load_asset(d['parent_carla'])
    if parent is None:
        raise RuntimeError(f'MI CARLA absent : {d["parent_carla"]}')
    mi = creer_ou_charger(d['chemin'], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', parent)
    MEL.clear_all_material_instance_parameters(mi)
    base = parent.get_base_material().get_name()
    nom_p, typ = C.CARLA_LUMINOSITE.get(base, (None, None))
    f = C.lum(d.get('facteur', (1, 1, 1)))
    applique = None
    if nom_p and typ == 'scalaire':
        v0 = MEL.get_material_instance_scalar_parameter_value(parent, nom_p)
        MEL.set_material_instance_scalar_parameter_value(mi, nom_p, v0 * f)
        applique = {nom_p: [v0, round(v0 * f, 5)]}
    elif nom_p:
        c0 = MEL.get_material_instance_vector_parameter_value(parent, nom_p)
        MEL.set_material_instance_vector_parameter_value(mi, nom_p, unreal.LinearColor(c0.r * f, c0.g * f, c0.b * f, c0.a))
        applique = {nom_p: [[c0.r, c0.g, c0.b, c0.a], f]}
    return mi, {'maitre_carla': base, 'luminosite': applique}


def etape_instances(mesures, etal):
    defs = C.instances(mesures, etal) + C.peintures(mesures)
    for d in defs:
        if A['seulement'] and d['nom'] not in A['seulement'] and d['maitre'] not in A['seulement']:
            continue
        try:
            if d['maitre'] == 'carla':
                mi, info = mi_carla(d)
            else:
                mi = creer_ou_charger(d['chemin'], unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
                mi.set_editor_property('parent', unreal.load_asset(C.MAITRES[d['maitre']]))
                MEL.clear_all_material_instance_parameters(mi)
                appliquer_mi(mi, d)
                info = {}
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi, False)
            journal['instances'].append({'nom': d['nom'], 'maitre': d['maitre'], 'variante': d.get('variante'), **info})
        except Exception as e:  # noqa: BLE001
            journal['erreurs'].append(f'{d["nom"]} : {type(e).__name__}: {e}')


# ======================================================================= principal
mesures = C.charger_json(C.MESURES)
etal = C.charger_json(C.ETALONNAGE, {})
t0 = time.time()
if 'textures' in A['etapes']:
    etape_textures(mesures)
if 'maitres' in A['etapes']:
    etape_maitres()
if 'instances' in A['etapes']:
    etape_instances(mesures, etal)
journal['duree_s'] = round(time.time() - t0, 1)
journal['nb_textures'] = len(journal['textures'])
journal['nb_instances'] = len(journal['instances'])
os.makedirs(C.OUT, exist_ok=True)
with open(f'{C.OUT}/construction.json', 'w', encoding='utf-8') as f:
    json.dump(journal, f, ensure_ascii=False, indent=1)
RESULT = {k: journal[k] for k in ('maitres', 'erreurs', 'duree_s', 'nb_textures', 'nb_instances')}
