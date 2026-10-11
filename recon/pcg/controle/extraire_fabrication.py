"""Extraction des couches USD fabriquées (fabrique_hda) en tableaux numpy pour le vérificateur de règles.

    hython recon/pcg/controle/extraire_fabrication.py [--fabrique DIR] [--cache DIR] [--forcer]

Lecture seule des USD (pxr). Pour chaque couche, écrit <cache>/<couche>.npz :
    T    (n, 3, 3) float32  triangles (repère local, m, Z haut ; faces triangulées en éventail)
    ent  (n,) int32         indice du component (entité : tuile de sol, K_xxxx, MF_xxxx...) dans `ents`
    mat  (n,) int16         indice du matériau (nom du Mesh = materiau_id) dans `mats`
    ents, mats              noms
    pour le sol seulement : N (n, 3, 3) float16, normales des coins de chaque triangle (TQ-SOL-008)
et <cache>/manifeste_cache.json : empreinte sha256 de chaque source, comptes, métadonnées de couche et de prim
(kinds, extents, interpolations, transformations) lues par les contrôles TQ-* (contrat d'export, TQ-SOL-010, TQ-MQG-008).
Une couche dont la source n'a pas changé (même sha256) n'est pas réextraite (sauf --forcer).
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from pxr import Usd, UsdGeom

RACINE = Path(__file__).resolve().parents[3]
FABRIQUE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
CACHE = RACINE / "recon/out/paquet_jardin/v2/controle/cache"
COUCHES = {
    "sol": "sol.usdc", "bordures": "bordures.usdc", "caniveaux": "caniveaux.usda", "ilots": "ilots.usda",
    "marquages_lignes": "marquages_lignes.usda", "passages": "passages.usda", "symboles": "symboles.usda",
    "zones": "zones.usda", "proto_symboles": "prototypes/symboles.usda",
}
TUILE_M = 50.0          # TQ-SOL-010 / TQ-SOL-008 : coutures de tuiles
VERSION = 2


def sha256(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def trianguler(counts, indices):
    """Éventail : (indices de sommets (m, 3), indices de coins faceVarying (m, 3), indice de face (m,))."""
    counts = np.asarray(counts, np.int64)
    indices = np.asarray(indices, np.int64)
    debut = np.concatenate([[0], np.cumsum(counts)[:-1]])
    tri, coins, faces = [], [], []
    for c in np.unique(counts):
        if c < 3:
            continue
        f = np.nonzero(counts == c)[0]
        d = debut[f]
        for k in range(c - 2):
            cc = np.stack([d, d + k + 1, d + k + 2], 1)
            coins.append(cc)
            tri.append(indices[cc])
            faces.append(f)
    if not tri:
        return np.zeros((0, 3), np.int64), np.zeros((0, 3), np.int64), np.zeros(0, np.int64)
    tri, coins, faces = np.concatenate(tri), np.concatenate(coins), np.concatenate(faces)
    o = np.lexsort((coins[:, 1], faces))          # ordre stable : face puis coin
    return tri[o], coins[o], faces[o]


def composant(prim):
    p = prim.GetParent()
    while p and p.IsValid() and not p.IsPseudoRoot():
        if Usd.ModelAPI(p).GetKind() == "component":
            return p
        p = p.GetParent()
    return prim.GetParent()


def extraire(nom, chemin, cache):
    t0 = time.time()
    st = Usd.Stage.Open(str(chemin))
    lay = st.GetRootLayer()
    cx = UsdGeom.XformCache(Usd.TimeCode.Default())
    T, ENT, MAT, seam_i, seam_n = [], [], [], [], []
    ents, mats = {}, {}
    prims, n_off = [], 0
    instanceurs = []
    for prim in st.Traverse():
        if prim.GetTypeName() == "PointInstancer":
            instanceurs.append(str(prim.GetPath()))
        if prim.GetTypeName() != "Mesh":
            continue
        m = UsdGeom.Mesh(prim)
        P = m.GetPointsAttr().Get()
        if P is None or len(P) == 0:
            continue
        P = np.array(P, np.float64)
        M = np.array(cx.GetLocalToWorldTransform(prim), np.float64)
        ident = bool(np.allclose(M, np.eye(4)))
        if not ident:
            P = P @ M[:3, :3] + M[3, :3]
        tri, coins, _ = trianguler(m.GetFaceVertexCountsAttr().Get(), m.GetFaceVertexIndicesAttr().Get())
        comp = composant(prim)
        e = comp.GetName()
        mat_nom = prim.GetName()
        ie = ents.setdefault(e, len(ents))
        im = mats.setdefault(mat_nom, len(mats))
        V = P[tri]
        T.append(V.astype(np.float32))
        ENT.append(np.full(len(tri), ie, np.int32))
        MAT.append(np.full(len(tri), im, np.int16))
        nrm = m.GetNormalsAttr()
        ninterp = m.GetNormalsInterpolation() if nrm.HasAuthoredValue() else None
        st_pv = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
        ext = m.GetExtentAttr().Get()
        prims.append({"chemin": str(prim.GetPath()), "composant": str(comp.GetPath()), "kind_composant":
                      Usd.ModelAPI(comp).GetKind(), "materiau": mat_nom, "faces": len(m.GetFaceVertexCountsAttr().Get()),
                      "triangles": int(len(tri)), "identite": ident,
                      "subdivision": m.GetSubdivisionSchemeAttr().Get(), "double_face": bool(m.GetDoubleSidedAttr().Get()),
                      "normales": ninterp, "st": st_pv.GetInterpolation() if st_pv and st_pv.HasValue() else None,
                      "extent": [list(map(float, ext[0])), list(map(float, ext[1]))] if ext else None,
                      "pivot_composant": [float(x) for x in np.array(cx.GetLocalToWorldTransform(comp))[3, :3]]})
        if nom == "sol":
            # normales des coins de tous les triangles (faceVarying ; vertex -> par sommet), pour TQ-SOL-008
            if ninterp == "faceVarying":
                N = np.array(nrm.Get(), np.float32)[coins]
            elif ninterp == "vertex":
                N = np.array(nrm.Get(), np.float32)[tri]
            else:
                N = np.zeros((len(tri), 3, 3), np.float32)
            seam_n.append(N.astype(np.float16))
        n_off += len(tri)
    T = np.concatenate(T) if T else np.zeros((0, 3, 3), np.float32)
    out = {"T": T, "ent": np.concatenate(ENT) if ENT else np.zeros(0, np.int32),
           "mat": np.concatenate(MAT) if MAT else np.zeros(0, np.int16),
           "ents": np.array(sorted(ents, key=ents.get)), "mats": np.array(sorted(mats, key=mats.get))}
    if nom == "sol":
        out["N"] = np.concatenate(seam_n) if seam_n else np.zeros((0, 3, 3), np.float16)
    np.savez(cache / f"{nom}.npz", **out)
    meta = {"source": chemin.relative_to(RACINE).as_posix(), "sha256": sha256(chemin), "triangles": int(len(T)),
            "meshes": len(prims), "composants": len(ents), "materiaux": sorted(mats),
            "metres_par_unite": UsdGeom.GetStageMetersPerUnit(st), "axe_haut": UsdGeom.GetStageUpAxis(st),
            "custom_layer_data": {k: (v if isinstance(v, (str, int, float, bool)) else str(v))
                                  for k, v in sorted(dict(lay.customLayerData).items())},
            "point_instancers": instanceurs, "prims": prims, "duree_s": round(time.time() - t0, 1)}
    return meta


def principal():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fabrique", default=str(FABRIQUE))
    ap.add_argument("--cache", default=str(CACHE))
    ap.add_argument("--forcer", action="store_true")
    a = ap.parse_args()
    fab, cache = Path(a.fabrique), Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    fm = cache / "manifeste_cache.json"
    ancien = json.loads(fm.read_text(encoding="utf-8")) if fm.exists() else {}
    man = {"schema": "pj_controle_cache/0.1", "version": VERSION, "fabrique": fab.relative_to(RACINE).as_posix(),
           "couches": {}}
    for nom, rel in COUCHES.items():
        f = fab / rel
        if not f.exists():
            man["couches"][nom] = {"source": rel, "absente": True}
            continue
        h = sha256(f)
        prec = (ancien.get("couches") or {}).get(nom)
        if (not a.forcer and prec and prec.get("sha256") == h and ancien.get("version") == VERSION
                and (cache / f"{nom}.npz").exists()):
            man["couches"][nom] = prec
            print(f"  {nom} : inchangé")
            continue
        meta = extraire(nom, f, cache)
        man["couches"][nom] = meta
        print(f"  {nom} : {meta['triangles']} triangles, {meta['composants']} composants ({meta['duree_s']} s)")
    fm.write_text(json.dumps(man, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
