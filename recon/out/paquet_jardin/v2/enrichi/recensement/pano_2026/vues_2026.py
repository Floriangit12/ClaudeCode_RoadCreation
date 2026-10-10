"""vues_2026.py : découpes perspective des photos Panoramax du 2026-07-28 avec la description v2 projetée.

Pose : poses/poses_2026-07-28.json (calage_sequence.py ; acceptée = « calee », sinon « approchee » :
pose refusée par les critères, usage qualitatif seulement). Superposition (couleurs) :
- marquages de la description (base/marquages.geojson) : blanc -> magenta, jaune -> orange, id court ;
- bordures (base/bordures.geojson, arête avant à +vue) : cyan ; îlots (base/ilots.geojson) : bleu ;
- objets du paquet (objets/mobilier.geojson) : supports en rouge (pied -> hauteur), arbres en vert ;
- levé GAM 2026 brut (SH marquages, BO bordures) en jaune pâle pointillé (option --gam).
Chaque vue produit <id8>_<nom>_ov.jpg, <id8>_<nom>_brut.jpg et <id8>_<nom>_proj.json (pixels des
entités dans la découpe : centre / pied / sommet, distance) pour citer les preuves.

  python vues_2026.py <id8> <nom> <lacet> <tangage> <fov> [--taille 1200x800] [--dmax 45] [--gam]
  python vues_2026.py --pixel <id8> <proj.json> u v     (pixel de découpe -> point au sol local et L93)
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[6]
sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
sys.dont_write_bytecode = True
import numpy as np  # noqa: E402
from PIL import ImageDraw  # noqa: E402

from camera import DONNEES, O, lire_json, photo, z_sol  # noqa: E402
from projection import camera_virtuelle, decoupe_perspective, intersection_sol  # noqa: E402
import calage_sequence as CS  # noqa: E402

DESC = RACINE / "recon/out/paquet_jardin/v2/description/base"
POSES = ICI / "poses/poses_2026-07-28.json"
VUES = ICI / "vues"


def camera_2026(pid):
    """(camera, statut) : statut 'calee' si acceptée, 'approchee' si pose refusée, 'brute' sinon."""
    cam, st = CS.camera_sequence(pid, POSES, accepte_seulement=False)
    return cam, {"calee": "calee", "calee_refusee": "approchee"}.get(st, st)


def _anneaux(g):
    t = g["type"]
    if t == "Polygon":
        return [g["coordinates"][0]]
    if t == "MultiPolygon":
        return [p[0] for p in g["coordinates"]]
    if t == "LineString":
        return [g["coordinates"]]
    if t == "MultiLineString":
        return list(g["coordinates"])
    if t == "Point":
        return [[g["coordinates"]]]
    if t == "MultiPoint":
        return [g["coordinates"]]
    return []


def entites(C, dmax):
    """Entités de la description à moins de dmax m de C (repère local)."""
    out = []
    for fam, fichier in (("marquages", "marquages.geojson"), ("bordures", "bordures.geojson"),
                         ("ilots", "ilots.geojson"), ("ponctuels_sol", "ponctuels_sol.geojson")):
        for f in lire_json(DESC / fichier)["features"]:
            p = f["properties"]
            for r in _anneaux(f["geometry"]):
                a = np.asarray(r, dtype=np.float64)[:, :2] - np.array(O[:2])
                if len(a) and np.min(np.hypot(a[:, 0] - C[0], a[:, 1] - C[1])) <= dmax:
                    out.append(dict(fam=fam, id=p.get("id"), p=p, xy=a))
    for fichier, fam in (("objets/mobilier.geojson", "mobilier"), ("objets/arbres.geojson", "arbres")):
        for f in lire_json(DONNEES / fichier)["features"]:
            p = f["properties"]
            if p.get("x_local") is None:
                continue
            a = np.array([[p["x_local"], p["y_local"]]])
            if np.hypot(a[0, 0] - C[0], a[0, 1] - C[1]) <= dmax:
                out.append(dict(fam=fam, id=p["id"], p=p, xy=a))
    return out


def vue(pid, nom, lacet, tangage, fov, taille=(1200, 800), dmax=45.0, gam=False):
    cam, statut = camera_2026(pid)
    img, cv = decoupe_perspective(photo(pid).id8, lacet, tangage, fov, taille, cam=cam)
    VUES.mkdir(parents=True, exist_ok=True)
    base = VUES / f"{photo(pid).id8}_{nom}"
    img.save(str(base) + "_brut.jpg", quality=92)
    d = ImageDraw.Draw(img)
    proj = dict(id8=photo(pid).id8, vue=nom, lacet=lacet, tangage=tangage, fov=fov, taille=list(taille),
                pose=cam.pose.round(4).tolist(), statut_pose=statut, entites=[])

    def px(P):
        uv, ok, dist = cv.projeter(np.atleast_2d(P))
        return uv, ok, dist

    def trace(P, col, w=1):
        uv, ok, dist = px(P)
        for k in range(len(P) - 1):
            if ok[k] and ok[k + 1] and dist[k] < dmax + 10:
                d.line([tuple(uv[k]), tuple(uv[k + 1])], fill=col, width=w)
        return uv, ok, dist

    def dens(a, z_add, pas=0.25):
        Q = []
        for k in range(len(a) - 1):
            n = max(1, int(np.hypot(*(a[k + 1] - a[k])) / pas))
            for t in np.linspace(0, 1, n, endpoint=False):
                q = a[k] + t * (a[k + 1] - a[k])
                Q.append([q[0], q[1], z_sol(*q) + z_add])
        q = a[-1]
        Q.append([q[0], q[1], z_sol(*q) + z_add])
        return np.array(Q)

    for e in entites(cam.C, dmax):
        fam, p, a = e["fam"], e["p"], e["xy"]
        if fam == "marquages":
            col = (255, 150, 0) if p.get("couleur") == "jaune" else (255, 0, 255)
            Q = dens(a, 0.01) if len(a) > 1 else np.array([[a[0, 0], a[0, 1], z_sol(*a[0])]])
            uv, ok, dist = trace(Q, col)
            c = a.mean(0)
        elif fam == "bordures":
            vue_m = 0.12
            Q = dens(a, vue_m)
            uv, ok, dist = trace(Q, (0, 230, 255), 2)
            c = a[len(a) // 2]
        elif fam == "ilots":
            Q = dens(a, 0.15)
            uv, ok, dist = trace(Q, (60, 120, 255), 1)
            c = a.mean(0)
        elif fam == "ponctuels_sol":
            c = a.mean(0)
            Q = np.array([[c[0], c[1], z_sol(*c)]])
            uv, ok, dist = px(Q)
            if ok[0]:
                d.ellipse([uv[0, 0] - 5, uv[0, 1] - 5, uv[0, 0] + 5, uv[0, 1] + 5], outline=(100, 200, 255), width=2)
        else:
            c = a[0]
            z = z_sol(*c)
            h = float(p.get("hauteur_m") or 3.0)
            if fam == "arbres":
                h = min(h, 4.0)
            Q = np.array([[c[0], c[1], z], [c[0], c[1], z + h]])
            uv, ok, dist = px(Q)
            if ok.all():
                d.line([tuple(uv[0]), tuple(uv[1])], fill=(255, 40, 40) if fam == "mobilier" else (40, 220, 40), width=2)
        Pc = np.array([[c[0], c[1], z_sol(*c)]])
        uvc, okc, dc = px(Pc)
        if okc[0] and 0 <= uvc[0, 0] < taille[0] and 0 <= uvc[0, 1] < taille[1]:
            lab = str(e["id"])
            d.text((uvc[0, 0] + 3, uvc[0, 1] - 11), lab, fill=(255, 255, 255))
            rec = dict(fam=fam, id=e["id"], centre_px=[round(float(uvc[0, 0]), 1), round(float(uvc[0, 1]), 1)],
                       distance_m=round(float(dc[0]), 2), centre_local=[round(float(c[0]), 3), round(float(c[1]), 3)])
            if fam in ("mobilier", "arbres") and ok.all():
                rec["pied_px"] = [round(float(uv[0, 0]), 1), round(float(uv[0, 1]), 1)]
                rec["sommet_px"] = [round(float(uv[1, 0]), 1), round(float(uv[1, 1]), 1)]
            proj["entites"].append(rec)
    if gam:
        for pre in ("SH", "BO"):
            for i, f in enumerate(CS._gam(pre)):
                a = CS._sommets(f["geometry"]) - np.array(O[:2])
                if np.min(np.hypot(a[:, 0] - cam.C[0], a[:, 1] - cam.C[1])) > dmax:
                    continue
                uv, ok, dist = px(dens(a, 0.01 if pre == "SH" else 0.12))
                for k in range(0, len(uv) - 1, 2):
                    if ok[k] and ok[k + 1]:
                        d.line([tuple(uv[k]), tuple(uv[k + 1])], fill=(255, 255, 160), width=1)
    d.text((8, 8), f"{photo(pid).id8} {nom} lacet {lacet} tangage {tangage} fov {fov} pose {statut}",
           fill=(255, 255, 0))
    img.save(str(base) + "_ov.jpg", quality=92)
    proj["entites"].sort(key=lambda r: (r["fam"], str(r["id"])))
    (Path(str(base) + "_proj.json")).write_text(json.dumps(proj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(str(base) + "_ov.jpg", statut, len(proj["entites"]), "entités")
    return proj


def pixel_sol(pid, fichier_proj, u, v):
    """Pixel d'une découpe -> rayon -> intersection avec le MNT 2026 : (local, L93, distance)."""
    pr = json.loads(Path(fichier_proj).read_text(encoding="utf-8"))
    cam, statut = camera_2026(pid)
    cv = camera_virtuelle(cam, pr["lacet"], pr["tangage"], pr["fov"], tuple(pr["taille"]))
    dd = cv.rayons(np.array([[u, v]], float))
    t = intersection_sol(cam.C, dd)
    X = cam.C + t[0] * dd[0]
    return dict(local=[round(float(X[0]), 3), round(float(X[1]), 3), round(float(X[2]), 3)],
                l93=[round(float(X[0] + O[0]), 2), round(float(X[1] + O[1]), 2)],
                distance_m=round(float(t[0]), 2), statut_pose=statut)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("args", nargs="*")
    ap.add_argument("--taille", default="1200x800")
    ap.add_argument("--dmax", type=float, default=45.0)
    ap.add_argument("--gam", action="store_true")
    ap.add_argument("--pixel", action="store_true")
    ap.add_argument("--cible", action="store_true", help="args : id8 nom x y fov (vue centrée sur un point local)")
    a = ap.parse_args()
    if a.cible:
        from projection import visee
        pid, nom, x, y, fov = a.args
        cam, _ = camera_2026(pid)
        x, y = float(x), float(y)
        lac, tan = visee(cam, [x, y, z_sol(x, y)])
        w, h = (int(v) for v in a.taille.split("x"))
        vue(pid, nom, round(lac, 2), round(tan, 2), float(fov), (w, h), a.dmax, a.gam)
        return
    if a.pixel:
        pid, fp, u, v = a.args
        print(json.dumps(pixel_sol(pid, fp, float(u), float(v)), ensure_ascii=False))
        return
    pid, nom, lacet, tangage, fov = a.args
    w, h = (int(x) for x in a.taille.split("x"))
    vue(pid, nom, float(lacet), float(tangage), float(fov), (w, h), a.dmax, a.gam)


if __name__ == "__main__":
    main()
