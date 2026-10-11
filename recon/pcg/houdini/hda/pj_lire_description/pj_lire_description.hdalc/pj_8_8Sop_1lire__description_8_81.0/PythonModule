"""pj::lire_description : module Python embarqué (section PythonModule de l'HDA).

Seul code Python de conversion de la fabrication (README_HDA.md) : description v2 (GeoJSON L93 / NGF, nivellement.json,
nivellement_grille.npz) -> géométrie Houdini Y haut, (x, y, z) local -> (x, z, -y), avec attributs. Aucune opération
géométrique ici : abscisses, profils, Z, orientation des faces et comblement du HeightField sont faits par les nœuds
VEX / SOP de l'HDA.

Deux points d'entrée, appelés par les Python SOP internes :
    lire_entites(sop)     sortie 1 : courbes et polygones (une ou plusieurs primitives par entité)
    lire_nivellement(sop) sortie 2 : volumes 2D height / r0 / z1 / r1 / z2 / r2 (+ poids, zpond pour le comblement)
Les paramètres sont lus sur l'HDA (parent du Python SOP). Les fichiers lus sont mis en cache (chemin, mtime, taille).
"""
import fnmatch
import hashlib
import json
import os

import hou
import numpy as np

O = (917279.43, 6460289.98, 216.30)
VERSION_GRAINE = "pj_fabrique/0.1"                 # pj_commun.graine : sha256(id | pj_fabrique/0.1)
FAMILLES = ("bordures", "surfaces", "ilots", "ponctuels_sol", "marquages")
EMPRISES = {"site": (-150.0, -150.0, 150.0, 150.0),   # carré local du site (sol_site.py)
            "pilote": (-11.0, -28.0, 60.0, 72.0)}     # ZP-01 (recon/pcg/README.md)
MAT_BORDURE = {"beton_gris": "beton_bordure_gris", "beton_clair": "beton_bordure_clair",
               "granit": "granit_bordure", "calcaire": "calcaire_bordure"}
USURE_MARQUAGE = {"0": 0.0, "1": 1.0 / 3.0, "2": 2.0 / 3.0, "3": 1.0, "F": 1.0}
BRANCHE_MARQUAGE = {"ligne": "marquages_lignes", "transversale": "marquages_lignes", "passage": "passages",
                    "fleche": "symboles", "symbole": "symboles", "zone": "zones"}
# attributs normalisés (README_HDA.md § 2) : une propriété brute de même nom et de même sens est ignorée,
# une propriété brute de sens différent est gardée sous <nom>_desc
NORMALISES = {"id", "famille", "classe", "materiau_id", "src", "conf", "usure", "salissure", "couverture", "graine",
              "region_niveau", "region_haute", "anneau", "partie", "props", "niv_s", "niv_z_pied", "niv_z_tete",
              "niv_z_arriere"}
MEME_SENS = {"id", "famille", "classe", "materiau_id", "src", "couverture", "region_niveau"}

_CACHE = {}


# ----------------------------------------------------------------------------------------------- utilitaires
def graine(ident):
    t = f"{ident}|{VERSION_GRAINE}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(t).digest()[:4], "little") & 0x7FFFFFFF


def _cache(chemin, lire):
    st = os.stat(chemin)
    cle = (st.st_mtime_ns, st.st_size)
    e = _CACHE.get(chemin)
    if e is None or e[0] != cle:
        with open(chemin, "rb") as f:
            b = f.read()
        e = (cle, lire(b), hashlib.sha256(b).hexdigest())
        _CACHE[chemin] = e
    return e[1], e[2]


def _local_xy(p):
    return [round(p[0] - O[0], 4), round(p[1] - O[1], 4)]


def _localiser(obj):
    """Copie d'une propriété avec les coordonnées L93 doublées en local (clés *_l93 -> *_local ; primitives de
    geometrie_reguliere : x0, y0 locaux, x0_l93 / y0_l93 gardés ; nez.position -> position_local)."""
    if isinstance(obj, list):
        return [_localiser(v) for v in obj]
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        out[k] = _localiser(v)
        if k.endswith("_l93") and isinstance(v, list) and v:
            base = k[:-4] + "_local"
            if isinstance(v[0], (int, float)) and len(v) >= 2:
                out[base] = _local_xy(v)
            elif isinstance(v[0], list) and v[0] and isinstance(v[0][0], (int, float)):
                out[base] = [_local_xy(q) for q in v]
    if "x0" in obj and "y0" in obj and "cap0_rad" in obj:        # primitive droite / arc / clothoïde
        out["x0_l93"], out["y0_l93"] = obj["x0"], obj["y0"]
        out["x0"], out["y0"] = _local_xy([obj["x0"], obj["y0"]])
    if "position" in obj and "rayon_m" in obj and isinstance(obj["position"], list):   # ilots.nez
        out["position_local"] = _local_xy(obj["position"])
    return out


def _parties(geom):
    """[(partie, anneau, coordonnées, fermé)] d'une géométrie GeoJSON."""
    if not geom:
        return []
    t, c = geom["type"], geom["coordinates"]
    if t == "LineString":
        return [(0, 0, c, False)]
    if t == "MultiLineString":
        return [(k, 0, l, False) for k, l in enumerate(c)]
    if t == "Polygon":
        return [(0, a, r, True) for a, r in enumerate(c)]
    if t == "MultiPolygon":
        return [(k, a, r, True) for k, p in enumerate(c) for a, r in enumerate(p)]
    if t == "Point":
        return [(0, 0, [c], False)]
    return []


def _texte(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# ----------------------------------------------------------------------------------------------- normalisation
def _normaliser(fam, p, niv_surf, niv_bord):
    """Attributs normalisés d'une entité (README_HDA.md § 2)."""
    prov = p.get("prov") or {}
    pg = prov.get("geometrie") or {}
    n = {"id": p["id"], "famille": fam, "graine": graine(p["id"]), "usure": 0.0, "salissure": 0.0,
         "couverture": 1.0, "region_niveau": -1, "region_haute": -1, "src": str(p.get("src") or pg.get("src") or ""),
         "conf": str(p.get("confiance") or pg.get("conf") or "")}
    groupes = [f"f_{fam}"]
    if fam == "bordures":
        n["classe"] = "bordure"
        n["materiau_id"] = MAT_BORDURE.get(p.get("materiau"), "beton_bordure_gris")
        a = p.get("aspect") or {}
        n["usure"] = float(a.get("epaufrures") or 0.0)
        n["salissure"] = float(a.get("salissure") or 0.0)
        b = niv_bord.get(p["id"])
        if b:
            n["region_niveau"], n["region_haute"] = int(b["region_basse"]), int(b["region_haute"])
            n["niv_s"], n["niv_z_pied"] = b["s"], b["z_pied"]
            n["niv_z_tete"], n["niv_z_arriere"] = b["z_tete"], b["z_arriere"]
        groupes.append("b_bordures")
        if p.get("caniveau"):
            groupes += ["b_caniveaux", "avec_caniveau"]
    elif fam == "surfaces":
        n["classe"] = str(p.get("classe") or "")
        r = p.get("revetement") or {}
        n["materiau_id"] = str(r.get("materiau_id") or "")
        n["salissure"] = float(r.get("salissure") or 0.0)
        reg = p.get("region_niveau")
        n["region_niveau"] = int(reg if reg is not None else niv_surf.get(p["id"], -1))
        groupes.append("b_sol")
    elif fam == "ilots":
        n["classe"] = str(p.get("type") or "")
        n["materiau_id"] = str((p.get("remplissage") or {}).get("materiau_id") or "")
        surf = p.get("surface") or []
        n["region_niveau"] = int(niv_surf.get(surf[0], -1)) if surf else -1
        groupes.append("b_ilots")
    elif fam == "ponctuels_sol":
        n["classe"] = str(p.get("type") or "")
        n["materiau_id"] = str(p.get("materiau_id") or "")
        groupes.append("b_sol")
    elif fam == "marquages":
        n["classe"] = str(p.get("classe") or "")
        u = str(p.get("usure") if p.get("usure") is not None else "1")
        n["materiau_id"] = f"PJ_Peinture_{p.get('couleur') or 'blanc'}_u{u}"
        n["usure"] = USURE_MARQUAGE.get(u, 1.0 / 3.0)
        n["couverture"] = float(p.get("couverture") if p.get("couverture") is not None else 1.0)
        fab = p.get("fabrication") or {}
        if fab.get("statut") == "non_fabrique":
            groupes.append("non_fabrique")
        else:
            groupes.append("b_" + BRANCHE_MARQUAGE.get(n["classe"], "zones"))
        if p.get("a_verifier"):
            groupes.append("a_verifier")
    return n, groupes


def _preparer_famille(chemin, fam, niv_surf, niv_bord, cle_niv):
    """Entités d'une famille, prêtes à poser (mis en cache avec le fichier et le nivellement)."""
    def lire(b):
        fc = json.loads(b)
        ents = []
        for f in fc["features"]:
            p = f["properties"]
            parts = []
            xs, ys = [], []
            for partie, anneau, coords, ferme in _parties(f.get("geometry")):
                pts = [tuple(c) for c in coords]
                if ferme and len(pts) > 1 and pts[0][:2] == pts[-1][:2]:
                    pts = pts[:-1]
                if len(pts) < (3 if ferme else 1):
                    continue
                P = np.array([[c[0] - O[0], c[1] - O[1], (c[2] - O[2]) if len(c) > 2 else np.nan] for c in pts])
                xs += [P[:, 0].min(), P[:, 0].max()]
                ys += [P[:, 1].min(), P[:, 1].max()]
                parts.append((partie, anneau, ferme, P))
            if not parts:
                continue
            n, groupes = _normaliser(fam, p, niv_surf, niv_bord)
            brut = {}
            for k, v in p.items():
                if k in NORMALISES:
                    if k in MEME_SENS:
                        continue
                    k = k + "_desc"
                brut[k] = _localiser(v)
            ents.append({"id": p["id"], "bbox": (min(xs), min(ys), max(xs), max(ys)), "parts": parts, "n": n,
                         "groupes": groupes, "brut": brut, "props": _texte(p)})
        meta = fc.get("description_v2") or {}
        return {"entites": ents, "schema": meta.get("schema", "")}
    cle = f"{chemin}|{cle_niv}"
    st = os.stat(chemin)
    e = _CACHE.get(cle)
    if e is None or e[0] != (st.st_mtime_ns, st.st_size):
        with open(chemin, "rb") as f:
            b = f.read()
        e = ((st.st_mtime_ns, st.st_size), lire(b), hashlib.sha256(b).hexdigest())
        _CACHE[cle] = e
    return e[1], e[2]


# ----------------------------------------------------------------------------------------------- paramètres
def _hda(sop):
    n = sop.parent()
    return n


def emprise(hda):
    """(xmin, ymin, xmax, ymax) locaux de l'emprise demandée, marge comprise."""
    mode = hda.parm("emprise").evalAsString()
    if mode in EMPRISES:
        e = EMPRISES[mode]
    elif mode == "boite":
        a, b = hda.evalParmTuple("boite_min"), hda.evalParmTuple("boite_max")
        e = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
    else:                                                    # tuile : carré du site découpé en tuiles
        t = max(hda.evalParm("tuile_taille"), 1.0)
        i, j = hda.evalParmTuple("tuile_index")
        x0, y0 = EMPRISES["site"][:2]
        e = (x0 + i * t, y0 + j * t, x0 + (i + 1) * t, y0 + (j + 1) * t)
    m = hda.evalParm("marge")
    return (e[0] - m, e[1] - m, e[2] + m, e[3] + m)


def _dossier(hda):
    return hou.text.expandString(hda.evalParm("dossier")).replace("\\", "/").rstrip("/")


def _nivellement_meta(dossier):
    chemin = f"{dossier}/nivellement.json"
    if not os.path.exists(chemin):
        return {}, {}, ""
    meta, h = _cache(chemin, lambda b: json.loads(b))
    surf = {s["id"]: int(s["region"]) for s in meta.get("surfaces", [])}
    bord = {b["id"]: b for b in meta.get("bordures", [])}
    return surf, bord, h


# ----------------------------------------------------------------------------------------------- types d'attributs
def _genre(v):
    if v is None:
        return "n"
    if isinstance(v, bool):
        return "b"
    if isinstance(v, int):
        return "i"
    if isinstance(v, float):
        return "f"
    if isinstance(v, str):
        return "s"
    if isinstance(v, dict):
        return "d"
    if isinstance(v, list):
        if not v:
            return "l0"
        g = {_genre(x) for x in v}
        if g == {"d"}:
            return "ld"
        if g == {"s"}:
            return "ls"
        if g <= {"i", "f"}:
            return "lf"
        return "x"
    return "x"


def _type_attribut(genres):
    g = set(genres) - {"n"}
    if not g:
        return None
    if g <= {"b"} or g == {"i"} or g == {"b", "i"}:
        return "int"
    if g <= {"i", "f", "b"}:
        return "float"
    if g == {"s"}:
        return "str"
    if g == {"d"}:
        return "dict"
    if g <= {"ld", "l0"} and "ld" in g:
        return "dicts"
    if g <= {"ls", "l0"}:
        return "strs"
    if g <= {"lf", "l0"} and "lf" in g:
        return "floats"
    return "json"


# ----------------------------------------------------------------------------------------------- sortie 1
def lire_entites(sop):
    hda = _hda(sop)
    geo = sop.geometry()
    dossier = _dossier(hda)
    xmin, ymin, xmax, ymax = emprise(hda)
    motifs = hda.evalParm("filtre_ids").split()
    garder_nf = hda.evalParm("marquages_non_fabriques")
    garder_props = hda.evalParm("garder_props")
    niv_surf, niv_bord, h_niv = _nivellement_meta(dossier)

    ents, hashes, schemas = [], {}, {}
    for fam in FAMILLES:
        if not hda.evalParm(f"fam_{fam}"):
            continue
        chemin = f"{dossier}/{fam}.geojson"
        if not os.path.exists(chemin):
            sop.addWarning(f"{chemin} absent")
            continue
        donnees, h = _preparer_famille(chemin, fam, niv_surf, niv_bord, h_niv)
        hashes[fam] = h
        schemas[fam] = donnees["schema"]
        for e in donnees["entites"]:
            b = e["bbox"]
            if b[2] < xmin or b[0] > xmax or b[3] < ymin or b[1] > ymax:
                continue
            if motifs and not any(fnmatch.fnmatchcase(e["id"], m) for m in motifs):
                continue
            if not garder_nf and "non_fabrique" in e["groupes"]:
                continue
            ents.append(e)

    # --- points et primitives (ordre : familles, puis entités triées par id dans les fichiers, puis parties)
    pos, zdec, az, polys, fermes, prim_ent, prim_part = [], [], [], [], [], [], []
    for k, e in enumerate(ents):
        for partie, anneau, ferme, P in e["parts"]:
            i0 = len(pos)
            for x, y, z in P:
                a = not np.isnan(z)
                pos.append((float(x), float(z) if a else 0.0, float(-y)))
                zdec.append(float(z) if a else 0.0)
                az.append(1 if a else 0)
            polys.append(list(range(i0, len(pos))))
            fermes.append(ferme)
            prim_ent.append(k)
            prim_part.append((partie, anneau))
    if not pos:
        geo.addAttrib(hou.attribType.Prim, "id", "")
        return
    geo.createPoints(pos)
    geo.addAttrib(hou.attribType.Point, "z_decrit", 0.0)
    geo.addAttrib(hou.attribType.Point, "a_z", 0)
    geo.setPointFloatAttribValues("z_decrit", zdec)
    geo.setPointIntAttribValues("a_z", az)
    # polygones fermés et courbes ouvertes, dans l'ordre des primitives
    prims = []
    for pts, f in zip(polys, fermes):
        prims.append(geo.createPolygons([pts], f)[0] if len(pts) >= 2 or f else None)
    if any(p is None for p in prims):                          # point isolé (géométrie Point) : polyligne d'un point
        for q, (pts, f) in enumerate(zip(polys, fermes)):
            if prims[q] is None:
                pl = geo.createPolygon(is_closed=False)
                pl.addVertex(geo.point(pts[0]))
                prims[q] = pl
    nprim = len(prims)

    # --- attributs normalisés
    def ajout(nom, defaut, valeurs, fonction):
        geo.addAttrib(hou.attribType.Prim, nom, defaut)
        fonction(nom, valeurs)
    E = [ents[k] for k in prim_ent]
    for nom in ("id", "famille", "classe", "materiau_id", "src", "conf"):
        ajout(nom, "", [e["n"].get(nom, "") for e in E], geo.setPrimStringAttribValues)
    for nom in ("usure", "salissure", "couverture"):
        ajout(nom, 0.0, [float(e["n"][nom]) for e in E], geo.setPrimFloatAttribValues)
    for nom in ("graine", "region_niveau", "region_haute"):
        ajout(nom, 0, [int(e["n"][nom]) for e in E], geo.setPrimIntAttribValues)
    ajout("partie", 0, [pp[0] for pp in prim_part], geo.setPrimIntAttribValues)
    ajout("anneau", 0, [pp[1] for pp in prim_part], geo.setPrimIntAttribValues)
    if garder_props:
        ajout("props", "", [e["props"] for e in E], geo.setPrimStringAttribValues)
    for nom in ("niv_s", "niv_z_pied", "niv_z_tete", "niv_z_arriere"):
        geo.addArrayAttrib(hou.attribType.Prim, nom, hou.attribData.Float)
    for pr, e in zip(prims, E):
        if "niv_s" in e["n"]:
            for nom in ("niv_s", "niv_z_pied", "niv_z_tete", "niv_z_arriere"):
                pr.setAttribValue(nom, [float(v) for v in e["n"][nom]])

    # --- propriétés brutes : un attribut par clé, typé sur l'ensemble des entités chargées
    genres = {}
    for e in ents:
        for kk, v in e["brut"].items():
            genres.setdefault(kk, set()).add(_genre(v))
    for kk in sorted(genres):
        t = _type_attribut(genres[kk])
        if t is None:
            continue
        nom = kk if t != "json" else kk + "_json"
        if geo.findPrimAttrib(nom) is not None:
            nom = nom + "_desc"
        vals = [e["brut"].get(kk) for e in E]
        if t == "int":
            ajout(nom, 0, [int(v) if v is not None else 0 for v in vals], geo.setPrimIntAttribValues)
        elif t == "float":
            ajout(nom, 0.0, [float(v) if v is not None else 0.0 for v in vals], geo.setPrimFloatAttribValues)
        elif t == "str":
            ajout(nom, "", [v if v is not None else "" for v in vals], geo.setPrimStringAttribValues)
        elif t == "json":
            ajout(nom, "", [_texte(v) if v is not None else "" for v in vals], geo.setPrimStringAttribValues)
        else:
            if t == "dict":
                geo.addAttrib(hou.attribType.Prim, nom, {})
            else:
                geo.addArrayAttrib(hou.attribType.Prim, nom, {"dicts": hou.attribData.Dict,
                                                             "strs": hou.attribData.String,
                                                             "floats": hou.attribData.Float}[t])
            for pr, v in zip(prims, vals):
                if v is None or v == [] or v == {}:
                    continue
                if t == "floats":
                    v = [float(x) for x in v]
                try:
                    pr.setAttribValue(nom, v)
                except Exception:                                    # structure non représentable : texte JSON
                    if geo.findPrimAttrib(nom + "_json") is None:
                        geo.addAttrib(hou.attribType.Prim, nom + "_json", "")
                    pr.setAttribValue(nom + "_json", _texte(v))

    # --- groupes de primitives
    noms_groupes = sorted({g for e in ents for g in e["groupes"]} | {"trou"})
    groupes = {g: geo.createPrimGroup(g) for g in noms_groupes}
    for pr, e, pp in zip(prims, E, prim_part):
        for g in e["groupes"]:
            groupes[g].add(pr)
        if pp[1] > 0:
            groupes["trou"].add(pr)

    # --- détail
    manifeste = os.path.join(os.path.dirname(dossier), "description_scene_v2.json")
    h_desc = ""
    if os.path.exists(manifeste):
        m, _ = _cache(manifeste, lambda b: json.loads(b))
        h_desc = m.get("hash_description", "")
    if h_niv:
        hashes["nivellement"] = h_niv
    comptes = {}
    for e in ents:
        c = comptes.setdefault(e["n"]["famille"], {"entites": 0, "primitives": 0, "points": 0})
        c["entites"] += 1
        c["primitives"] += len(e["parts"])
        c["points"] += sum(len(P) for _, _, _, P in e["parts"])
    geo.addAttrib(hou.attribType.Global, "pj_hash_description", "")
    geo.setGlobalAttribValue("pj_hash_description", h_desc)
    geo.addAttrib(hou.attribType.Global, "pj_hash_fichiers", {})
    geo.setGlobalAttribValue("pj_hash_fichiers", hashes)
    geo.addAttrib(hou.attribType.Global, "pj_schemas", {})
    geo.setGlobalAttribValue("pj_schemas", schemas)
    geo.addAttrib(hou.attribType.Global, "pj_comptes", {})
    geo.setGlobalAttribValue("pj_comptes", comptes)
    geo.addAttrib(hou.attribType.Global, "pj_emprise", (0.0, 0.0, 0.0, 0.0))
    geo.setGlobalAttribValue("pj_emprise", (xmin, ymin, xmax, ymax))
    geo.addAttrib(hou.attribType.Global, "pj_dossier", "")
    geo.setGlobalAttribValue("pj_dossier", dossier)
    geo.addAttrib(hou.attribType.Global, "pj_altitude", "")
    geo.setGlobalAttribValue("pj_altitude", hda.parm("altitude").evalAsString())
    return nprim


# ----------------------------------------------------------------------------------------------- sortie 2
def _grille(chemin):
    def lire(b):
        import io
        g = np.load(io.BytesIO(b))
        return {k: g[k] for k in g.files}
    return _cache(chemin, lire)


def lire_nivellement(sop):
    """Volumes 2D du modèle de nivellement recadrés sur l'emprise (+ marge), au pas 0,10 m x sous-échantillonnage."""
    hda = _hda(sop)
    geo = sop.geometry()
    if not hda.evalParm("charger_nivellement"):
        return
    dossier = _dossier(hda)
    chemin = f"{dossier}/nivellement_grille.npz"
    if not os.path.exists(chemin):
        sop.addWarning(f"{chemin} absent")
        return
    g, h = _grille(chemin)
    x0, y0, pas = float(g["x0"]), float(g["y0"]), float(g["pas"])
    nj, ni = g["z0"].shape
    xmin, ymin, xmax, ymax = emprise(hda)
    m = hda.evalParm("niv_marge")
    k = max(1, int(hda.evalParm("niv_pas")))
    i0 = max(0, int(np.floor((xmin - m - x0) / pas)))
    i1 = min(ni - 1, int(np.ceil((xmax + m - x0) / pas)))
    j0 = max(0, int(np.floor((ymin - m - y0) / pas)))
    j1 = min(nj - 1, int(np.ceil((ymax + m - y0) / pas)))
    if i1 <= i0 or j1 <= j0:
        return
    sl = (slice(j0, j1 + 1, k), slice(i0, i1 + 1, k))
    r0 = g["r0"][sl].astype(np.float32)
    z0 = g["z0"][sl].astype(np.float32)
    couches = {"height": np.where(r0 >= 0, np.nan_to_num(z0, nan=0.0), 0.0).astype(np.float32),
               "r0": r0,
               "z1": np.nan_to_num(g["z1"][sl].astype(np.float32), nan=0.0),
               "r1": g["r1"][sl].astype(np.float32),
               "z2": np.nan_to_num(g["z2"][sl].astype(np.float32), nan=0.0),
               "r2": g["r2"][sl].astype(np.float32)}
    w = (r0 >= 0).astype(np.float32)
    couches["poids"] = w                                       # poids et z pondéré : comblement par flou normalisé
    couches["zpond"] = (couches["height"] * w).astype(np.float32)
    nnj, nni = r0.shape
    p = pas * k
    gx0, gy0 = x0 + i0 * pas, y0 + j0 * pas
    # rangement HeightField : axe 0 -> Z monde (= -y), axe 1 -> X monde ; voxel (nnj - 1 - j, i)
    X0, X1 = gx0 - p / 2, gx0 + (nni - 1) * p + p / 2
    Z0, Z1 = -(gy0 + (nnj - 1) * p) - p / 2, -gy0 + p / 2
    xf = hou.Matrix4(((0, 0, (Z1 - Z0) / 2, 0), ((X1 - X0) / 2, 0, 0, 0), (0, p / 2, 0, 0),
                      ((X0 + X1) / 2, 0, (Z0 + Z1) / 2, 1)))
    geo.addAttrib(hou.attribType.Prim, "name", "")
    for nom in ("height", "r0", "z1", "r1", "z2", "r2", "poids", "zpond"):
        v = geo.createVolume(nnj, nni, 1, hou.BoundingBox(X0, -p / 2, Z0, X1, p / 2, Z1))
        v.setTransform(xf)
        a = np.ascontiguousarray(couches[nom][::-1, :].T, dtype=np.float32)   # [i, k], axe 0 (k) le plus rapide
        v.setAllVoxelsFromString(a.tobytes())
        v.setAttribValue("name", nom)
        v.setIntrinsicValue("volumevisualmode", "heightfield")   # reconnu par les outils HeightField
    for nom, val in (("niv_x0", gx0), ("niv_y0", gy0), ("niv_pas", p)):
        geo.addAttrib(hou.attribType.Global, nom, 0.0)
        geo.setGlobalAttribValue(nom, float(val))
    for nom, val in (("niv_ni", nni), ("niv_nj", nnj), ("niv_i0", i0), ("niv_j0", j0), ("niv_sous_ech", k)):
        geo.addAttrib(hou.attribType.Global, nom, 0)
        geo.setGlobalAttribValue(nom, int(val))
    geo.addAttrib(hou.attribType.Global, "niv_hash", "")
    geo.setGlobalAttribValue("niv_hash", h)
