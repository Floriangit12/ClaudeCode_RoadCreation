"""Rendus de contrôle d'une scène du lot L2 (hython) : scène USD (route fabriquée route_l2.usda + décor : fond herbeux,
arbres aux points du modèle, ciel, soleil), caméras générales et propres à la scène, Karma XPU, tuiles natives.

Sorties : <sortie>/<scene>/rendus/{<vue>.png, tuiles/<vue>/, scene_rendu.usda, ciel.exr, manifest_rendus.json}.
Les caméras sont posées en coordonnées de route (s, t, hauteur au-dessus du sol fabriqué) : la même vue se relit sur
le modèle. Une vue de dessus quasi orthographique couvre toute la scène (5 cm/px au plus, PLAN § 5.2).
"""
import json
import math
import time
from pathlib import Path

import numpy as np

import hou
import decor
import rendre_l2 as RL

RES = (1600, 1000)

# vues propres aux scènes : nom -> ((s, t, h) œil, (s, t, h) cible, focale mm) ; s en fraction de L si < 1.5
VUES = {
    "S01": {"conducteur": ((8, -1.5, 1.25), (70, -1.5, 0.4), 28)},
    "S02": {"detail_bordure": ((26, -1.6, 0.9), (32, -3.4, 0.0), 30)},
    "S03": {"avancees": ((14, -10.5, 2.4), (30, -3.8, 0.4), 28),
            "avancees_trottoir": ((40, -6.2, 1.65), (55, -3.6, 0.4), 24),
            "angle_avancee": ((24.6, -1.4, 0.75), (22.5, -3.0, 0.05), 35)},
    "S04": {"bande_cyclable": ((10, -4.0, 1.4), (55, -3.5, 0.3), 28)},
    "S05": {"pistes": ((12, 5.6, 1.65), (45, 4.4, 0.4), 26)},
    "S06": {"terre_plein": ((6, -4.5, 1.65), (45, 0.0, 0.8), 26)},
    "S07": {"sens_unique": ((8, 0.0, 1.3), (70, 0.0, 0.4), 28)},
    "S08": {"passage_dos_d_ane": ((34, -6.4, 1.7), (54, 0.5, 0.1), 26),
            "abaisse_bev": ((44, 6.3, 1.4), (48.5, 3.6, 0.0), 30)},
    "S09": {"rabattement": ((28, -8.5, 3.2), (78, 1.0, 0.0), 26)},
    "S10": {"plateau": ((38, -6.4, 1.6), (51, 0.5, 0.1), 26),
            "plateau_bordure": ((47, 6.3, 1.0), (49.5, 3.4, 0.05), 32)},
    "S11": {"courbe": ((4, -1.5, 1.3), (45, 8.0, 0.5), 24)},
    "S12": {"couloir_bus": ((10, -1.6, 1.3), (70, -1.6, 0.4), 28)},
}


class Route:
    """Référence échantillonnée (rg::graphe, sortie 1) : (s, t) -> (x, y) local, interpolation des échantillons."""

    def __init__(self, geo):
        pr = geo.prims()[0]
        pts = pr.points()
        self.s = np.array([p.attribValue("s") for p in pts])
        self.P = np.array([(p.position()[0], -p.position()[2]) for p in pts])
        self.G = np.array([(p.attribValue("gauche")[0], -p.attribValue("gauche")[2]) for p in pts])
        self.L = float(self.s[-1])

    def xy(self, s, t):
        s = min(max(s, 0.0), self.L)
        i = int(np.clip(np.searchsorted(self.s, s, side="right") - 1, 0, len(self.s) - 2))
        a = (s - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-12)
        P = self.P[i] + a * (self.P[i + 1] - self.P[i])
        G = self.G[i] + a * (self.G[i + 1] - self.G[i])
        G = G / np.linalg.norm(G)
        return P + t * G


def z_sol(sol_geo, x, y):
    pos, n, uvw = hou.Vector3(), hou.Vector3(), hou.Vector3()
    pr = sol_geo.intersect(hou.Vector3(x, 50.0, -y), hou.Vector3(0, -1, 0), pos, n, uvw, None, 0, 1e9, 1e-6)
    return float(pos[1]) if pr >= 0 else 0.0


def rendre_scene(noeuds, scene, dossier_scene, parent, vues=None, res=RES):
    t0 = time.time()
    d = Path(dossier_scene) / "rendus"
    d.mkdir(parents=True, exist_ok=True)
    sol = noeuds["sol"].geometry(0)
    graphe = noeuds["sol"].inputs()[0]
    route = Route(graphe.geometry())
    niv = noeuds["nivellement"].geometry()
    secs = [p for p in niv.points() if p.attribValue("profil")]
    abord = secs[0].attribValue("abord_g_mat") or secs[0].attribValue("abord_d_mat") or "gazon_tondu"
    # contour : t max / min sur la scène (profil et abords), depuis le sol fabriqué
    T = np.array(sol.pointFloatAttribValues("t"))
    tmax, tmin = float(T.max()), float(T.min())
    # arbres (décor) aux points du modèle
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdRender
    arb = decor.construire_arbres(parent, _sortie(parent, noeuds["vers_entites"], 1), noeuds["sol"])
    arb_geo = arb.geometry()
    usd = d / "scene_rendu.usda"
    if usd.exists():
        usd.unlink()
    stage = Usd.Stage.CreateNew(str(usd))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    monde = stage.DefinePrim("/Monde", "Xform")
    monde.GetReferences().AddReference("../l2/route_l2.usda")
    ids = {"feuillage", "feuillage_clair", "ecorce", abord}
    dec = RL.maillages(arb_geo, "Arbres") if len(arb_geo.prims()) else {}
    ids |= set(dec)
    liaisons, sources = RL.materiaux(stage, ids, d)
    if dec:
        RL.ecrire_couche(stage, "/Decor/Arbres", dec, liaisons)
    zmin = float(np.array(sol.pointFloatAttribValues("P")).reshape(-1, 3)[:, 1].min())
    cx, cy = route.xy(route.L / 2, 0.5 * (tmax + tmin))
    RL.fond(stage, (cx, cy), _z_contour(sol) - 0.001, liaisons[abord], demi=2500.0)
    ciel = d / "ciel.exr"
    RL.ciel_exr(ciel)
    RL.lumieres(stage, -35.0, "ciel.exr")
    # caméras
    cams = {}
    L = route.L

    def cam(nom, oeil, cible, focale):
        (s0, t0_, h0), (s1, t1, h1) = oeil, cible
        x0, y0 = route.xy(s0, t0_)
        x1, y1 = route.xy(s1, t1)
        z0 = z_sol(sol, x0, y0) + h0
        z1 = z_sol(sol, x1, y1) + h1
        RL.camera(stage, nom, (x0, y0, z0), (x1, y1, z1), focale=focale, res=res)
        cams[nom] = {"oeil_st_h": oeil, "cible_st_h": cible, "focale_mm": focale,
                     "oeil_xyz": [round(x0, 3), round(y0, 3), round(z0, 3)], "cible_xyz": [round(x1, 3), round(y1, 3), round(z1, 3)]}

    cam("oblique", (0.12 * L, tmin - 16.0, 11.0), (0.58 * L, 0.0, 0.0), 30)
    cam("pieton", (0.28 * L, tmax - 7.0 if tmax - 7.0 > 0 else 0.5 * tmax, 1.65), (0.28 * L + 30.0, 0.0, 0.5), 24)
    for nom, (o, c, f) in VUES.get(scene, {}).items():
        cam(nom, o, c, f)
    # vue de dessus : toute la scène (boîte du sol fabriqué + 4 m), 5 cm/px au plus. Caméra perspective quasi
    # orthographique (2 000 m d'altitude, focale ajustée au cadre) : avec Karma XPU 22.0.459, une caméra USD
    # orthographique ne lance aucun rayon et husk ne rend pas la main (mémoire > 20 Go). Parallaxe au bord du cadre :
    # relief × demi-largeur / altitude, soit 5 mm pour 15 cm de relief à 64 m du centre (sous le dixième du pixel).
    Ps = np.array(sol.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)
    xs, ys = Ps[:, 0], -Ps[:, 2]
    larg = float(xs.max() - xs.min()) + 8.0
    haut = float(ys.max() - ys.min()) + 8.0
    px = max(0.05, larg / 3000.0, haut / 3000.0)
    res_d = (int(round(larg / px)), int(round(haut / px)))
    xc, yc = 0.5 * float(xs.max() + xs.min()), 0.5 * float(ys.max() + ys.min())
    alt = 2000.0
    zc = float(np.median(Ps[:, 1]))
    camd = UsdGeom.Camera.Define(stage, "/Cameras/dessus")
    camd.CreateProjectionAttr(UsdGeom.Tokens.perspective)
    camd.CreateHorizontalApertureAttr(36.0)
    camd.CreateVerticalApertureAttr(36.0 * haut / larg)
    camd.CreateFocalLengthAttr(36.0 * alt / larg)
    camd.CreateClippingRangeAttr(Gf.Vec2f(alt - 100.0, alt + 100.0))
    xf = UsdGeom.Xformable(camd)
    xf.AddTranslateOp().Set(Gf.Vec3d(xc, yc, zc + alt))
    cams["dessus"] = {"quasi_orthographique": True, "altitude_m": alt, "largeur_m": round(larg, 3),
                      "hauteur_m": round(haut, 3), "m_par_px": round(px, 4), "res": res_d,
                      "parallaxe_max_m_pour_0_15": round(0.15 * 0.5 * math.hypot(larg, haut) / alt, 4)}
    rs = UsdRender.Settings.Define(stage, "/Render/reglages")
    rs.CreateResolutionAttr(Gf.Vec2i(*res))
    stage.SetDefaultPrim(monde)
    stage.GetRootLayer().Save()
    noms = [n for n in cams if n != "dessus"]
    vues = vues or noms
    pngs = RL.rendre(usd, [n for n in noms if n in vues], d, res, limite_s=60)
    pngs.update(RL.rendre(usd, ["dessus"], d, res_d, limite_s=90))
    tu = {}
    for nom, png in pngs.items():
        m = RL.tuiles(png, d / "tuiles" / nom)
        tu[nom] = [x["fichier"] for x in m.get("tuiles", [])]
    RL.nettoyer_rat()
    man = {"schema": "rg_rendus_l2/0.1", "scene": scene, "moteur": "Karma XPU (husk)",
           "eclairage": {"soleil_intensite": RL.SOLEIL, "soleil_elevation_deg": 40.0, "soleil_azimut_deg": -35.0,
                         "soleil_normalize": True, "ciel": "dégradé lat-long (zénith, horizon, sol lointain)",
                         "exposition_fixe": round(RL.exposition(), 5)},
           "decor": {"fond": f"plan herbeux ({abord}) 1 mm sous le bord de la scène, au-delà des abords du modèle",
                     "arbres": f"{len(_sortie(parent, noeuds['vers_entites'], 1).geometry().points())} arbres procéduraux "
                               "(rendu/decor.py) aux points du modèle (objets_le_long)"},
           "materiaux": sources, "cameras": cams, "images": {k: v.name for k, v in pngs.items()}, "tuiles": tu,
           "duree_s": round(time.time() - t0, 1)}
    (d / "manifest_rendus.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{scene} : {len(pngs)} rendus ({round(time.time() - t0)} s) -> {d}")
    return man


def _z_contour(sol):
    """Z le plus bas du contour extérieur du sol (arêtes de bord) : le fond de décor passe juste dessous."""
    zs = []
    for pr in sol.prims():
        vs = pr.vertices()
        for i in range(len(vs)):
            a, b = vs[i].point(), vs[(i + 1) % len(vs)].point()
            if len(a.prims()) and len([e for e in a.prims() if b in e.points()]) == 1:
                zs.append(min(a.position()[1], b.position()[1]))
    if not zs:
        P = np.array(sol.pointFloatAttribValues("P")).reshape(-1, 3)
        return float(P[:, 1].min())
    return float(min(zs))


def _sortie(parent, noeud, k):
    """Nœud Null branché sur la sortie k d'un nœud (pour l'entrée d'un réseau de décor)."""
    nom = f"{noeud.name()}_sortie_{k}"
    n = parent.node(nom) or parent.createNode("null", nom)
    n.setInput(0, noeud, k)
    return n
