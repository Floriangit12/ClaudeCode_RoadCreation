"""[editeur] Correctif de la COPIE projet du maitre de feuillage CARLA (/Game/Carla/.../M_treeLeaves_master ; jamais
D:/CARLA_Assets) : teinte d'automne par arbre (revue UE du 10/10 : octobre ne se lisait que sur quelques variantes v2).

Insere avant la sortie BaseColor : couleur x lerp(1, GainAutomne, a), a = AutomneBase + (1 - AutomneBase) x saturate((r -
(1 - PartAutomne)) / PartAutomne) avec r = PerInstanceRandom (aleatoire par instance ISM : arbres poses par PG_Arbres)
-> jaunissement leger de tous les feuillus (AutomneBase) et 35 % des sujets franchement jaunes a roux. Les MI CARLA
heritent des parametres (valeurs par defaut ci-dessous) ; les resineux (M_TreePine_1, M_Foliage) ne sont pas touches.
Idempotent : les noeuds marques « PJ_Automne » sont retires puis reconstruits ; la liaison d'origine est conservee
(sortie BaseColor rebranchee sur le noeud source d'origine). ARGS : part (0,35), base (0,25), gain ([1,9, 0,95, 0,35]).
RESULT : {maitre, source, noeuds, instructions_ps}.
"""
import unreal

A = dict(maitre='/Game/Carla/Static/GenericMaterials/00_MastersOpt/M_treeLeaves_master', part=0.35, base=0.25,
         gain=[1.9, 0.95, 0.35])
A.update(globals().get('ARGS') or {})
MEL = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty.MP_BASE_COLOR
MARQUE = 'PJ_Automne'

m = unreal.load_asset(A['maitre'])
# retrait d'un correctif precedent : la source d'origine est memorisee dans la description du noeud de sortie
src, sortie = MEL.get_material_property_input_node(m, MP), MEL.get_material_property_input_node_output_name(m, MP)
origine = None
for ex in list(MEL.get_material_expressions(m)):
    if ex.get_editor_property('desc').startswith(MARQUE):
        if ex.get_editor_property('desc').startswith(MARQUE + ' sortie'):
            origine = ex
if origine is not None:
    # la sortie est un Multiply (A = couleur d'origine) : on remonte a la source de A
    src = MEL.get_inputs_for_material_expression(m, origine)[0]
    sortie = ''
    for ex in list(MEL.get_material_expressions(m)):
        if ex.get_editor_property('desc').startswith(MARQUE):
            MEL.delete_material_expression(m, ex)
n = [0]


def e(cls, **kv):
    n[0] += 1
    ex = MEL.create_material_expression(m, getattr(unreal, 'MaterialExpression' + cls), -900, 800 + 90 * n[0])
    ex.set_editor_property('desc', f'{MARQUE} {n[0]}')
    for k, v in kv.items():
        ex.set_editor_property(k, v)
    return ex


def c(a, sa, b, pin):
    if not MEL.connect_material_expressions(a, sa, b, pin):
        raise RuntimeError(f'connexion {a.get_class().get_name()}.{sa} -> {b.get_class().get_name()}.{pin}')


r = e('PerInstanceRandom')
part = e('ScalarParameter', parameter_name='PJ_PartAutomne', default_value=float(A['part']), group='PJ_Automne')
base = e('ScalarParameter', parameter_name='PJ_AutomneBase', default_value=float(A['base']), group='PJ_Automne')
gain = e('VectorParameter', parameter_name='PJ_GainAutomne', default_value=unreal.LinearColor(*A['gain'], 1.0), group='PJ_Automne')
un = e('Constant', r=1.0)
s1 = e('Subtract')                       # 1 - part
c(un, '', s1, 'A'); c(part, '', s1, 'B')
s2 = e('Subtract')                       # r - (1 - part)
c(r, '', s2, 'A'); c(s1, '', s2, 'B')
d = e('Divide')
c(s2, '', d, 'A'); c(part, '', d, 'B')
sat = e('Saturate')
c(d, '', sat, '')
a = e('LinearInterpolate')               # a = lerp(base, 1, sat)
c(base, '', a, 'A'); c(un, '', a, 'B'); c(sat, '', a, 'Alpha')
k = e('LinearInterpolate')               # k = lerp(1, gain, a)
c(un, '', k, 'A'); c(gain, '', k, 'B'); c(a, '', k, 'Alpha')
mul = e('Multiply')
mul.set_editor_property('desc', f'{MARQUE} sortie')
c(src, sortie, mul, 'A'); c(k, '', mul, 'B')
MEL.connect_material_property(mul, '', MP)
MEL.recompile_material(m)
unreal.EditorAssetLibrary.save_loaded_asset(m, False)
RESULT = {'maitre': A['maitre'], 'source': f'{src.get_class().get_name()}.{sortie}', 'noeuds': MEL.get_num_material_expressions(m),
          'instructions_ps': MEL.get_statistics(m).num_pixel_shader_instructions}
