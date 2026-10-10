"""Copie le toolset pj_tools dans le projet UE (D:/ClaudeADAS/Content/Python).

Usage : python installer.py [racine_projet_ue]
Puis, editeur ouvert : outil MCP pj_tools.reload_pj_tools (ou redemarrer l'editeur).
"""
import os
import shutil
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
PROJET = sys.argv[1] if len(sys.argv) > 1 else 'D:/ClaudeADAS'
DEST = os.path.join(PROJET, 'Content', 'Python')

os.makedirs(DEST, exist_ok=True)
cible = os.path.join(DEST, 'init_unreal.py')
if os.path.exists(cible):
    ancien = open(cible, encoding='utf-8').read()
    if 'pj_tools' not in ancien:
        shutil.copy2(cible, cible + '.bak_v2')   # init_unreal tiers : sauvegarde
shutil.copy2(os.path.join(ICI, 'init_unreal.py'), cible)
src_pkg = os.path.join(ICI, 'pj_tools')
dst_pkg = os.path.join(DEST, 'pj_tools')
os.makedirs(dst_pkg, exist_ok=True)
for f in os.listdir(src_pkg):
    if f.endswith('.py'):
        shutil.copy2(os.path.join(src_pkg, f), os.path.join(dst_pkg, f))
print('installe dans', DEST, sorted(os.listdir(dst_pkg)))
