"""Contrôles de chaîne d'export et de rendu mesurables dans les fichiers (TQ-REF-003, TQ-OMB-002, TQ-MQR-001) :
couches USD (manifeste du cache d'extraction), matériaux materiaux_ue.usda, fichiers de points. Les réglages faits
dans l'éditeur UE (Nanite, ombres, collisions, PCG) ne sont pas lisibles ici (voir rapport.NON_IMPLEMENTEES).
"""
import re

import numpy as np

import ctl_commun as K
from ctl_commun import regle, r4

COUCHES_UE = ("sol", "bordures", "caniveaux", "ilots", "marquages_lignes", "passages", "symboles", "zones")


@regle("TQ-REF-003", "fabrication", "info",
       "Architecture d'instanciation à grande échelle (principe City Sample) : les éléments répétés passent par des "
       "nuages de points pj_points/0.1 (bordures, caniveaux, îlots, symboles) et aucune couche destinée à UE ne "
       "contient de PointInstancer (E7). Unité : couche USD et fichier de points.", "implemente")
def tq_ref_003(ctx, R):
    for c in COUCHES_UE:
        m = ctx.cache["couches"].get(c, {})
        pi = m.get("point_instancers") or []
        R.tester(not pi, entite=m.get("source", c), valeur=len(pi), seuil="aucun PointInstancer",
                 detail=f"{len(pi)} PointInstancer(s) : {pi[:3]}")
    for fam in ("bordures", "caniveaux", "ilots", "symboles"):
        doc = ctx.points(fam)
        ok = doc.get("schema") == "pj_points/0.1" and len(doc.get("points", [])) > 0
        R.tester(ok, entite=f"points/{fam}.json", valeur=len(doc.get("points", [])), seuil="pj_points/0.1 non vide")


@regle("TQ-OMB-002", "fabrication", "info",
       "Lumen et ray tracing : tuiles de sol de 64 m au plus (qualité des distance fields), lues dans sol.usdc "
       "(emprise de chaque component T_ii_jj). Unité : tuile.", "partiel",
       "réglages Lumen, Hit Lighting, fallback Nanite et r.RayTracing.Nanite.Mode : côté UE")
def tq_omb_002(ctx, R):
    prims = ctx.cache["couches"]["sol"]["prims"]
    comp = {}
    for p in prims:
        comp.setdefault(p["composant"], []).append(p)
    for c in sorted(comp):
        ps = comp[c]
        lo = np.min([p["extent"][0] for p in ps], axis=0)
        hi = np.max([p["extent"][1] for p in ps], axis=0)
        taille = float(max(hi[0] - lo[0], hi[1] - lo[1]))
        R.tester(taille <= 64.0, entite=c.split("/")[-1], xy=(lo + hi)[:2] / 2, valeur=r4(taille, 2), seuil="≤ 64 m")


@regle("TQ-MQR-001", "fabrication", "mineur",
       "Matériau des marques opaque (ni Masked ni Translucent) : dans materiaux_ue.usda, les matériaux PJ_Peinture_* "
       "n'ont ni opacity < 1 ni opacityThreshold > 0 sur leur UsdPreviewSurface et pointent un MI_PJ_Peinture_* "
       "(contexte unreal). Unité : matériau de peinture.", "partiel",
       "mode de mélange du matériau maître M_Marquage : côté UE")
def tq_mqr_001(ctx, R):
    txt = (ctx.fab / "materiaux_ue.usda").read_text(encoding="utf-8")
    blocs = re.split(r'\n\s*def Material "', txt)[1:]
    for b in blocs:
        nom = b.split('"', 1)[0]
        if not nom.startswith("PJ_Peinture"):
            continue
        corps = b[:4000]
        m_op = re.search(r"inputs:opacity\s*=\s*([0-9.]+)", corps)
        m_th = re.search(r"inputs:opacityThreshold\s*=\s*([0-9.]+)", corps)
        op = float(m_op.group(1)) if m_op else 1.0
        th = float(m_th.group(1)) if m_th else 0.0
        mi = f"MI_{nom}" in corps
        R.tester(op >= 1.0 and th <= 0.0 and mi, entite=nom, valeur=op, seuil="opaque, MI_PJ_Peinture_*",
                 detail=f"opacity {op}, opacityThreshold {th}, MI {'présent' if mi else 'absent'}")
