"""[editeur] Materiaux du contexte v1 (batiments, bordures v1) : maitre M_PJ_Facade et ses MI, MI_bordure_v1.

- M_PJ_Facade (/Game/PJ/Materials/Maitres) : enduit (texture CC0 de beton_bordure, contraste reduit, teinte par MI) et
  fenetres procedurales (noeud Custom HLSL) lues sur les UV des murs de preparer_usd.py : UV0 = (u le long du mur,
  hauteur au-dessus du sol du batiment) en m (UE ecrit v' = 1 - v a l'import), UV1 = (hauteur a l'egout, alea du
  batiment). Par etage (EtageM) une fenetre tous les PasM (LargeurM x HauteurM sur une allege AllegeM), cadre PVC,
  appui, embrasure assombrie, volets roulants baisses au hasard (VoletProba), vitrage sombre peu rugueux (reflets
  Lumen) ; pas de fenetre au-dessus de egout - MargeHautM ; Vitrine = rez-de-chaussee commercial (baies) ;
  Fenetres = 0 : mur aveugle (annexes, garages).
- MI_PJ_Facade_{enduit_blanc, enduit_beige, enduit_gris, enduit_ocre, commerce, annexe} : albedo moyen cible
  (Teinte = cible / moyenne de la texture), reglages de baies.
- MI_bordure_v1 (enfant de MI_beton_bordure_gris) : faces de bordure v1 d'un seul tenant (maillage en coordonnees du
  site) : salissure uniforme (SalissureHaut = 1 : pas de bande de pied a altitude fixe), ni mousse.
- M_PJ_Relief + MI_PJ_Relief (relief lointain, contexte/relief_usd.py ; revue UE du 10/10) : foret d'octobre (feuillus
  roux et resineux sombres melanges par un bruit monde de 600 et 150 m), prairies et alpages au-dessus de 1 200 m,
  falaises calcaires claires (Chartreuse, Saint-Eynard) selon la pente (normale du sommet) ; la perspective aerienne
  de SkyAtmosphere voile le tout selon la distance.
ARGS : aucun. RESULT : {maitre, instances}.
"""
import importlib
import os
import sys

import unreal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'materiaux'))
import catalogue as C  # noqa: E402
importlib.reload(C)

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
ST = unreal.MaterialSamplerType
MAT = '/Game/PJ/Materials'
MAITRE = f'{MAT}/Maitres/M_PJ_Facade'
TEX = '/Game/PJ/Textures/CC0/beton_bordure/T_beton_bordure_{}'

HLSL = r'''
float pas = P1.x; float larg = P1.y; float allege = P1.z; float haut = P1.w;
float etage = P2.x; float rdc = P2.y; float marge = P2.z; float cadre = P2.w;
float vitrine = P3.x; float vitH = P3.y; float voletP = P3.z; float actif = P3.w;
float H = UV1.x; float rb = UV1.y;
float u = UV.x + rb * 37.0; float v = 1.0 - UV.y;
float4 r0 = float4(0, 0, 0, 0); float4 r1 = float4(0, 0, 0, 0);
if (actif > 0.5 && v > 0.0)
{
    float ix = floor(u / pas); float cx = (frac(u / pas) - 0.5) * pas;
    float fz = (v - rdc) / etage; float iz = floor(fz); float cz = frac(fz) * etage;
    float hw = larg * 0.5;
    bool en_vitrine = (vitrine > 0.5) && (v < vitH);
    bool niveau_ok = (v > rdc) && (rdc + iz * etage + allege + haut < H - marge) && !(vitrine > 0.5 && v < vitH + 0.2);
    float rnd = frac(sin(dot(float3(ix, iz, rb * 101.0), float3(12.9898, 78.233, 37.719))) * 43758.5453);
    float z0 = allege; float z1 = allege + haut; float zc = cz;
    if (en_vitrine) { hw = pas * 0.42; z0 = 0.25; z1 = vitH - 0.3; zc = v; }
    if (en_vitrine || niveau_ok)
    {
        float ax = abs(cx);
        float dz0 = zc - z0; float dz1 = z1 - zc;
        if (ax < hw && dz0 > 0.0 && dz1 > 0.0)
        {
            float bord = min(hw - ax, min(dz0, dz1));
            float c = bord < cadre ? 1.0 : 0.0;
            if (!en_vitrine && larg > 1.0 && ax < cadre * 0.5) c = 1.0;
            float t = dz0 / (z1 - z0);
            float f = (rnd < voletP) ? frac(rnd * 17.31) : 0.0;
            float volet = (!en_vitrine && c < 0.5 && t > 1.0 - f) ? 1.0 : 0.0;
            r0 = float4((c < 0.5 && volet < 0.5) ? 1.0 : 0.0, c, volet, rnd);
        }
        else
        {
            float autour = (ax < hw + 0.12 && dz0 > -0.07 && dz1 > -0.12) ? 1.0 : 0.0;
            float appui = (!en_vitrine && ax < hw + 0.05 && dz0 <= 0.0 && dz0 > -0.07) ? 1.0 : 0.0;
            r1 = float4(autour * (1.0 - appui), appui, 0, 0);
        }
    }
}
return Mode > 0.5 ? r1 : r0;
'''


class Graphe:
    """Construction compacte (meme principe que materiaux/construire_materiaux.py)."""

    def __init__(self, m):
        self.m, self.n = m, 0
        for ex in list(MEL.get_material_expressions(m)):
            MEL.delete_material_expression(m, ex)
        m.set_editor_property('use_material_attributes', True)
        self.mma = self.e('MakeMaterialAttributes')
        MEL.connect_material_property(self.mma, '', unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)

    def e(self, cls, **props):
        self.n += 1
        ex = MEL.create_material_expression(self.m, getattr(unreal, 'MaterialExpression' + cls),
                                            -400 - 260 * (self.n % 10), 120 * (self.n // 10))
        for k, v in props.items():
            ex.set_editor_property(k, v)
        return ex

    def src(self, v):
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
        ex, s = self.src(v)
        if not MEL.connect_material_expressions(ex, s, dst, entree):
            raise RuntimeError(f'connexion {ex.get_class().get_name()}.{s} -> {dst.get_class().get_name()}.{entree}')

    def op(self, cls, **e):
        ex = self.e(cls)
        for k, v in e.items():
            self.c(v, ex, '' if k == 'x' else k)
        return ex

    def mul(self, a, b): return self.op('Multiply', A=a, B=b)
    def add(self, a, b): return self.op('Add', A=a, B=b)
    def lerp(self, a, b, t): return self.op('LinearInterpolate', A=a, B=b, Alpha=t)
    def div(self, a, b): return self.op('Divide', A=a, B=b)
    def sat(self, a): return self.op('Saturate', x=a)

    def masque(self, a, canaux):
        ex = self.e('ComponentMask', r='R' in canaux, g='G' in canaux, b='B' in canaux, a='A' in canaux)
        self.c(a, ex, '')
        return ex

    def scal(self, nom, d, grp):
        return self.e('ScalarParameter', parameter_name=nom, default_value=float(d), group=grp)

    def vec(self, nom, d, grp):
        d = list(d) + [1.0] * (4 - len(d))
        return (self.e('VectorParameter', parameter_name=nom, default_value=unreal.LinearColor(*d), group=grp), 'RGB')

    def vec4(self, noms, defauts, grp):
        """float4 assemble de 4 scalaires nommes."""
        s = [self.scal(n, d, grp) for n, d in zip(noms, defauts)]
        return self.op('AppendVector', A=self.op('AppendVector', A=self.op('AppendVector', A=s[0], B=s[1]), B=s[2]), B=s[3])

    def tex(self, nom, chemin):
        return self.e('TextureObjectParameter', parameter_name=nom, texture=unreal.load_asset(chemin), group='Textures')

    def ech(self, t, uv, typ):
        ex = self.e('TextureSample', sampler_type=typ, sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        self.c(t, ex, 'Tex')
        self.c(uv, ex, 'UVs')
        return ex

    def sortie(self, nom, v):
        self.c(v, self.mma, nom)


def custom(g, entrees, mode):
    ex = g.e('Custom', code=HLSL, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, description='Fenetres')
    ins = []
    for nom in ('UV', 'UV1', 'P1', 'P2', 'P3', 'Mode'):
        ci = unreal.CustomInput()
        ci.set_editor_property('input_name', nom)
        ins.append(ci)
    ex.set_editor_property('inputs', ins)
    for nom, v in list(entrees.items()) + [('Mode', float(mode))]:
        g.c(v, ex, nom)
    return ex


def maitre():
    m = unreal.load_asset(MAITRE) if EAL.does_asset_exist(MAITRE) else \
        AT.create_asset('M_PJ_Facade', f'{MAT}/Maitres', unreal.Material, unreal.MaterialFactoryNew())
    g = Graphe(m)
    for k in ('used_with_nanite', 'used_with_static_mesh', 'used_with_instanced_static_meshes'):
        m.set_editor_property(k, True)
    uv0 = g.e('TextureCoordinate', coordinate_index=0)
    uv1 = g.e('TextureCoordinate', coordinate_index=1)
    tile = g.scal('TileM', 1.6, 'Enduit')
    uvt = g.div(uv0, tile)
    ta, tn, tr = g.tex('T_Albedo', TEX.format('albedo')), g.tex('T_Normale', TEX.format('normale')), \
        g.tex('T_Rugosite', TEX.format('rugosite'))
    alb = (g.ech(ta, uvt, ST.SAMPLERTYPE_COLOR), 'RGB')
    alb = g.lerp(g.vec('MoyenneTexture', (0.35, 0.35, 0.35), 'Enduit'), alb, g.scal('Contraste', 0.35, 'Enduit'))
    # salissure macro : coulures douces (bruit etire en hauteur)
    tb = g.tex('T_Bruit', '/Game/PJ/Textures/PJ/T_PJ_BruitMacro')
    nb = g.ech(tb, g.mul(uv0, (0.08, 0.02)), ST.SAMPLERTYPE_MASKS)
    macro = g.add(1.0, g.mul(g.scal('MacroForce', 0.12, 'Enduit'), g.add((nb, 'G'), -0.5)))
    mur = g.mul(g.mul(g.mul(alb, g.vec('Teinte', (1, 1, 1), 'Enduit')), g.scal('Luminosite', 1.0, 'Enduit')), macro)
    E = {'UV': uv0, 'UV1': uv1,
         'P1': g.vec4(('PasM', 'LargeurM', 'AllegeM', 'HauteurM'), (3.1, 1.25, 0.95, 1.35), 'Baies'),
         'P2': g.vec4(('EtageM', 'RdcM', 'MargeHautM', 'CadreM'), (2.8, 0.2, 0.55, 0.06), 'Baies'),
         'P3': g.vec4(('Vitrine', 'VitrineHautM', 'VoletProba', 'Fenetres'), (0.0, 3.2, 0.55, 1.0), 'Baies')}
    f0 = custom(g, E, 0)
    f1 = custom(g, E, 1)
    vitre, cadre, volet, rnd = (g.masque(f0, c) for c in 'RGBA')
    embr, appui = g.masque(f1, 'R'), g.masque(f1, 'G')
    c_vitre = g.mul(g.vec('CouleurVitre', (0.035, 0.04, 0.045), 'Baies'), g.add(0.5, g.mul(rnd, 1.6)))
    col = g.lerp(mur, g.mul(mur, g.scal('Embrasure', 0.55, 'Baies')), embr)
    col = g.lerp(col, g.vec('CouleurAppui', (0.55, 0.54, 0.52), 'Baies'), appui)
    col = g.lerp(col, g.vec('CouleurCadre', (0.72, 0.72, 0.70), 'Baies'), cadre)
    col = g.lerp(col, g.vec('CouleurVolet', (0.52, 0.50, 0.47), 'Baies'), volet)
    col = g.lerp(col, c_vitre, vitre)
    g.sortie('BaseColor', col)
    rug_mur = g.sat(g.add(g.mul((g.ech(tr, uvt, ST.SAMPLERTYPE_MASKS), 'G'), 0.3), 0.65))
    rug = g.lerp(rug_mur, 0.45, g.sat(g.add(cadre, volet)))
    rug = g.lerp(rug, g.scal('RugositeVitre', 0.04, 'Baies'), vitre)
    g.sortie('Roughness', rug)
    g.sortie('Specular', g.lerp(0.5, 0.6, vitre))
    nrm = (g.ech(tn, uvt, ST.SAMPLERTYPE_NORMAL), 'RGB')
    plat = g.sat(g.add(g.add(vitre, cadre), volet))
    nf = g.scal('NormalForce', 0.35, 'Enduit')
    n_m = g.op('Normalize', VectorInput=g.op('AppendVector', A=g.mul(g.masque(nrm, 'RG'), nf), B=g.masque(nrm, 'B')))
    g.sortie('Normal', g.lerp(n_m, (0.0, 0.0, 1.0), plat))
    MEL.layout_material_expressions(m)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    st = MEL.get_statistics(m)
    return {'chemin': MAITRE, 'noeuds': MEL.get_num_material_expressions(m), 'instructions_ps': st.num_pixel_shader_instructions}


def maitre_relief():
    chemin = f'{MAT}/Maitres/M_PJ_Relief'
    m = unreal.load_asset(chemin) if EAL.does_asset_exist(chemin) else \
        AT.create_asset('M_PJ_Relief', f'{MAT}/Maitres', unreal.Material, unreal.MaterialFactoryNew())
    g = Graphe(m)
    for k in ('used_with_nanite', 'used_with_static_mesh'):
        m.set_editor_property(k, True)
    G = 'Relief'
    wp = g.e('WorldPosition')
    xy = g.masque(wp, 'RG')
    tb = g.tex('T_Bruit', '/Game/PJ/Textures/PJ/T_PJ_BruitMacro')
    n1 = g.masque(g.ech(tb, g.div(xy, g.mul(g.scal('EchelleForetM', 600.0, G), 100.0)),
                        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS), 'R')
    n2 = g.masque(g.ech(tb, g.div(xy, g.mul(g.scal('EchelleDetailM', 150.0, G), 100.0)),
                        unreal.MaterialSamplerType.SAMPLERTYPE_MASKS), 'G')
    foret = g.lerp(g.vec('Resineux', (0.035, 0.045, 0.030), G), g.vec('Feuillus', (0.085, 0.065, 0.035), G),
                   g.sat(g.add(g.mul(g.add(n1, -0.5), 3.0), 0.5)))
    foret = g.mul(foret, g.add(0.8, g.mul(n2, 0.4)))
    z = g.masque(wp, 'B')
    alpage = g.sat(g.div(g.add(z, g.mul(g.scal('AlpageZm', 1200.0, G), -100.0)), 30000.0))
    base = g.lerp(foret, g.vec('Alpage', (0.10, 0.10, 0.065), G), alpage)
    nz = g.masque(g.e('VertexNormalWS'), 'B')
    roche = g.sat(g.div(g.add(g.scal('RocheNz', 0.45, G), g.mul(nz, -1.0)), 0.15))
    roche = g.mul(roche, g.add(0.3, g.mul(n2, 0.7)))
    base = g.lerp(base, g.vec('Roche', (0.30, 0.29, 0.26), G), g.sat(roche))
    g.sortie('BaseColor', base)
    g.sortie('Roughness', 0.9)
    g.sortie('Specular', 0.3)
    MEL.layout_material_expressions(m)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return chemin


def mi(nom, parent):
    chemin = f'{MAT}/{nom}'
    m = unreal.load_asset(chemin) if EAL.does_asset_exist(chemin) else \
        AT.create_asset(nom, MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    m.set_editor_property('parent', unreal.load_asset(parent))
    MEL.clear_all_material_instance_parameters(m)
    return m


# albedo moyen cible (lineaire) des enduits ; reglages des baies
FACADES = {
    'enduit_blanc': ((0.56, 0.55, 0.51), {}),
    'enduit_beige': ((0.50, 0.44, 0.35), {'PasM': 2.9}),
    'enduit_gris': ((0.40, 0.40, 0.39), {'PasM': 3.4, 'LargeurM': 1.5}),
    'enduit_ocre': ((0.52, 0.40, 0.27), {'PasM': 3.0, 'LargeurM': 1.1, 'HauteurM': 1.45}),
    'commerce': ((0.36, 0.37, 0.38), {'Vitrine': 1.0, 'PasM': 4.2, 'LargeurM': 2.4, 'AllegeM': 1.0, 'HauteurM': 1.1,
                                      'EtageM': 3.4, 'VoletProba': 0.15, 'VitrineHautM': 3.3}),
    'annexe': ((0.38, 0.36, 0.33), {'Fenetres': 0.0}),
}

R = {'maitre': maitre(), 'instances': {}}
# moyenne de la texture d'enduit du maitre (Concrete037 de beton_bordure ; MI_beton_bordure_gris est passe au beton City
# Sample, revue UE du 10/10)
moy = C.charger_json(C.MESURES)['cc0']['beton_bordure']['albedo_moyen_lin']
moy = tuple(max(x, 1e-3) for x in moy)
for nom, (cible, regl) in FACADES.items():
    m = mi(f'MI_PJ_Facade_{nom}', MAITRE)
    MEL.set_material_instance_vector_parameter_value(m, 'MoyenneTexture', unreal.LinearColor(*moy, 1.0))
    t = [cible[i] / moy[i] for i in range(3)]
    MEL.set_material_instance_vector_parameter_value(m, 'Teinte', unreal.LinearColor(*t, 1.0))
    for k, v in regl.items():
        MEL.set_material_instance_scalar_parameter_value(m, k, float(v))
    MEL.update_material_instance(m)
    EAL.save_loaded_asset(m, False)
    R['instances'][m.get_name()] = {'albedo_cible': cible, **regl}

# plan de contexte au-dela du carre v1 (3 km) : gazon en UV monde (MI_PJ_Contexte) attenue vers un vert olive desature
# (melange lointain de pelouses, friches, jardins et toitures : albedo ~0,06 / 0,075 / 0,045 au lieu de 0,035 / 0,083 / 0,017)
p = unreal.load_asset(f'{MAT}/MI_PJ_Contexte')
m = mi('MI_PJ_Contexte_Lointain', p.get_path_name())
t0 = MEL.get_material_instance_vector_parameter_value(p, 'Teinte')
gaz = tuple(C.cible_effective('gazon_tondu'))         # cible du parent (surcharge de rendu Karma)
cib = (0.060, 0.075, 0.045)
MEL.set_material_instance_vector_parameter_value(m, 'Teinte', unreal.LinearColor(
    t0.r * cib[0] / gaz[0], t0.g * cib[1] / gaz[1], t0.b * cib[2] / gaz[2], 1.0))
MEL.set_material_instance_scalar_parameter_value(m, 'MacroForce', 0.45)
MEL.set_material_instance_scalar_parameter_value(m, 'MacroEchelleM', 40.0)
MEL.update_material_instance(m)
EAL.save_loaded_asset(m, False)
R['instances']['MI_PJ_Contexte_Lointain'] = {'parent': 'MI_PJ_Contexte', 'albedo_cible': cib}

R['instances']['MI_PJ_Relief'] = {'parent': maitre_relief()}
m = mi('MI_PJ_Relief', R['instances']['MI_PJ_Relief']['parent'])
MEL.update_material_instance(m)
EAL.save_loaded_asset(m, False)

m = mi('MI_bordure_v1', f'{MAT}/MI_beton_bordure_gris')
for k, v in (('SalissureHaut', 1.0), ('Salissure', 0.25), ('Mousse', 0.0)):
    MEL.set_material_instance_scalar_parameter_value(m, k, v)
MEL.update_material_instance(m)
EAL.save_loaded_asset(m, False)
R['instances']['MI_bordure_v1'] = {'parent': 'MI_beton_bordure_gris', 'SalissureHaut': 1.0, 'Salissure': 0.25}
RESULT = R
