"""hython : cree l'HDA d'essai pj::test_boite::1.0 (SOP, une boite parametree) en .hdalc (licence Indie).

Usage : hython creer_hda_boite.py [sortie.hdalc]
Parametres exposes : taille (x, y, z en m) et divisions ; la boite est posee sur le sol (base a z = 0
dans le repere Houdini Z-haut du projet ; Houdini est Y-haut par defaut : on oriente via 'orient').
"""
import os
import sys

import hou

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, 'pj_test_boite.hdalc')

hou.hipFile.clear(suppress_save_prompt=True)
geo = hou.node('/obj').createNode('geo', 'pj_hda')
sub = geo.createNode('subnet', 'pj_test_boite')
box = sub.createNode('box', 'boite')
out = sub.createNode('output', 'sortie')
out.setInput(0, box)
for c in 'xyz':
    box.parm(f'size{c}').setExpression(f'ch("../taille{c}")')
box.parm('divrate1').setExpression('ch("../divisions")') if box.parm('divrate1') else None
# base de la boite a 0 sur l'axe vertical Houdini (Y) : centre a taille_y / 2
box.parm('ty').setExpression('ch("../tailley") / 2')

hda_node = sub.createDigitalAsset(name='pj::test_boite::1.0', hda_file_name=SORTIE,
                                  description='PJ test boite (phase 0)', min_num_inputs=0, max_num_inputs=0)
defn = hda_node.type().definition()
ptg = defn.parmTemplateGroup()
ptg.append(hou.FloatParmTemplate('taille', 'Taille (m)', 3, default_value=(2.0, 1.0, 0.5)))
ptg.append(hou.IntParmTemplate('divisions', 'Divisions', 1, default_value=(1,), min=1, max=20))
defn.setParmTemplateGroup(ptg)
defn.save(SORTIE)
print('HDA', SORTIE, os.path.getsize(SORTIE), 'octets ; licence', hou.licenseCategory())
