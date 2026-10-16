"""Essai des HDA route::* : cuisson de quelques instances, bilan (points, faces, boîte, volume signé, erreurs).

    hython recon/pcg/assets_route/hda/essai_hda_route.py
"""
import sys
from pathlib import Path
import hou
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI)); sys.path.insert(0, str(ICI.parent))
import hda_route_outils as O  # noqa: E402
import specs_assets_route as SP  # noqa: E402


def volume(geo):
    v = 0.0
    for pr in geo.prims():
        pts = [p.position() for p in pr.points()]
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            v += a.dot(b.cross(c)) / 6.0
    return v


def essai(ids):
    O.installer_tout()
    g = hou.node("/obj").createNode("geo", "essai_route")
    par_id = {a["id"]: a for a in SP.ASSETS}
    for i in ids:
        a = par_id[i]
        n = g.createNode(a["hda"].replace("::1.0", "") + "::1.0" if not a["hda"].endswith("1.0") else a["hda"], i[:60])
        for k, v in a["params"].items():
            pa = n.parm(k)
            if pa is None:
                print("  parm absent", k); continue
            pa.set(v)
        try:
            geo = n.geometry()
        except hou.OperationFailed as e:
            print(i, "ERREUR", e); continue
        errs = list(n.errors()) + [f"{c.name()}: {e}" for c in n.allSubChildren() for e in c.errors()]
        bb = geo.boundingBox()
        mats = sorted(set(geo.primStringAttribValues("materiau"))) if geo.findPrimAttrib("materiau") else []
        print(f"{i}: {len(geo.points())} pts {len(geo.prims())} faces  min {tuple(round(x,4) for x in bb.minvec())} "
              f"max {tuple(round(x,4) for x in bb.maxvec())}  vol {volume(geo):.6f}  uv {bool(geo.findVertexAttrib('uv'))} "
              f"N {bool(geo.findVertexAttrib('N'))} mats {mats} {errs[:2]}")


if __name__ == "__main__":
    ids = sys.argv[1:] or ["bordure_T2_L100", "bordure_T2_angle_sortant", "bordure_T2_angle_rentrant", "bordure_T2_quart_rond_ext_R020",
                           "bordure_T2_quart_rond_int_R020", "bordure_raccord_T2_T2_surbaissee_droite", "bordure_CS2_L100",
                           "potelet_gorge_D102_H100_tete_blanche", "support_rond_D60_H30", "bev_dalle_beton_600x420x60",
                           "feu_R11v_D200", "garde_corps_pont_S8_L30", "barriere_croix_st_andre_L150", "barriere_lyon_1530"]
    essai(ids)
