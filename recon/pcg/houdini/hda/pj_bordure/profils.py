"""Module Python embarqué des HDA pj::bordure et pj::caniveau (section PythonModule) : table des profils.

Seul usage de Python dans ces HDA (entrée-sortie JSON, README_HDA.md) : le nœud « lire_profils » (Python SOP) convertit
la table des profils en contours Houdini (un polygone fermé par profil dans le plan XY : x = u, y = v), avec :
  - primitive : profil, famille (bordure | caniveau), base, H, i_top (début de la tête), k_back (arête arrière haute),
    h_fil_eau (caniveaux : hauteur côté bordure, fil d'eau) ;
  - point : u_cs, v_cs, chaine (0 = face vue et tête jusqu'à l'arête arrière haute, 1 = arrière et dessous), rang,
    p_cs (abscisse sur le périmètre), perim (périmètre) ;
  - détail : pj_profils_noms[], pj_profils_base[], pj_profils_H[], pj_profils_hfe[] (h côté bordure des caniveaux),
    pj_profils_source.
Les caniveaux sont posés devant la face vue : leurs contours sont décalés de −largeur en u.

La table est figée dans le module de l'HDA à la construction (TABLE_EMBARQUEE, autonome dans Unreal) ; le paramètre
« Dossier des specs » permet de la relire depuis assets/specs (bordures.json, bordures_elements.json).

Règles appliquées (assets/specs/bordures_elements.json) :
  - profils_complementaires (TU, AC1, CS3) ;
  - corrections_profils.*.remplace_sommets (CS1, CS2 : chanfrein 15 x 15 côté chaussée, fiches Sepa) ;
  - aretes.<profil>.arete_arriere_haute : chanfrein 5 x 5 mm (T1, T2, T3, T2_bateau, TU, QUAI_BUS) ou 3 x 3 mm (P1,
    P3) ajouté au contour quand l'arête arrière haute est vive ;
  - MURET_TALUS (bordures.json regles_affectation : « muret, soutènement ou talus ») : section rectangulaire de 0,20 m,
    hauteur unitaire (mise à la hauteur de chaque section par la pose).
"""
import hashlib
import json
from pathlib import Path

CHANFREIN_ARRIERE = {"T1": 0.005, "T2": 0.005, "T3": 0.005, "T2_bateau": 0.005, "TU": 0.005, "QUAI_BUS": 0.005,
                     "P1": 0.003, "P3": 0.003, "PAVES_GRANIT": 0.0}
CANIVEAUX = ("CS1", "CS2", "CS3", "CC1", "CC2")
MURET = {"contour": [[0.0, 0.0], [0.0, 1.0], [0.2, 1.0], [0.2, 0.0]], "base": 0.2, "H": 1.0}


def _chanfrein_arriere(c, base, H, e):
    """Remplace le coin vif (base, H) du contour par deux sommets (base − e, H) et (base, H − e)."""
    out = []
    for u, v in c:
        if e > 0 and abs(u - base) < 1e-9 and abs(v - H) < 1e-9:
            out += [[round(base - e, 6), H], [base, round(H - e, 6)]]
        else:
            out.append([u, v])
    return out


def construire_table(dossier_specs):
    """Table {profil: {contour, base, H, famille, h_fil_eau?}} depuis assets/specs ; renvoie (table, source)."""
    d = Path(dossier_specs)
    b = json.loads((d / "bordures.json").read_text(encoding="utf-8"))
    e = json.loads((d / "bordures_elements.json").read_text(encoding="utf-8"))
    prof = {k: dict(v) for k, v in b["profils"].items() if v.get("contour")}
    for k, v in (e.get("profils_complementaires") or {}).items():
        if v.get("contour"):
            prof[k] = dict(v)
    for k, corr in (e.get("corrections_profils") or {}).items():
        rs = corr.get("remplace_sommets")
        if k in prof and rs:
            c = [list(p) for p in prof[k]["contour"]]
            for de, par in zip(rs["de"], rs["par"]):
                for i, p in enumerate(c):
                    if abs(p[0] - de[0]) < 1e-9 and abs(p[1] - de[1]) < 1e-9:
                        c[i] = list(par)
            prof[k]["contour"] = c
    table = {}
    for k in sorted(prof):
        v = prof[k]
        c = [[float(x), float(y)] for x, y in v["contour"]]
        base = max(p[0] for p in c)
        H = max(p[1] for p in c)
        fam = "caniveau" if k in CANIVEAUX else "bordure"
        ent = {"base": round(base, 6), "H": round(H, 6), "famille": fam}
        if fam == "bordure":
            c = _chanfrein_arriere(c, base, H, CHANFREIN_ARRIERE.get(k, 0.0))
        else:
            # fil d'eau côté bordure : dessus du caniveau en u = largeur (bordures_elements.caniveaux.pose)
            ent["h_fil_eau"] = round(max(p[1] for p in c if abs(p[0] - base) < 1e-9), 6)
        ent["contour"] = [[round(x, 6), round(y, 6)] for x, y in c]
        table[k] = ent
    table["MURET_TALUS"] = dict(MURET, famille="bordure")
    src = {f: hashlib.sha256((d / f).read_bytes()).hexdigest()[:16] for f in ("bordures.json", "bordures_elements.json")}
    return table, src


def _indices(c, base, H):
    """i_top : premier sommet de la tête (v = H) ; k_back : arête arrière haute (premier u = base)."""
    i_top = next(i for i, p in enumerate(c) if p[1] >= H - 1e-9)
    k_back = next(i for i, p in enumerate(c) if abs(p[0] - base) < 1e-9)
    return i_top, k_back


TABLE_EMBARQUEE = None          # remplacé à la construction de l'HDA (table figée : {"profils": ..., "source": ...})


def table_embarquee(node):
    """Table figée dans le module de l'HDA (TABLE_EMBARQUEE), ou relue depuis le dossier de specs (paramètre)."""
    hda = node.parent()
    dossier = hda.parm("dossier_specs").evalAsString().strip() if hda.parm("dossier_specs") else ""
    if dossier or TABLE_EMBARQUEE is None:
        dossier = dossier or str(Path(__file__).resolve().parents[5] / "assets" / "specs")
        table, src = construire_table(dossier)
        return table, json.dumps({"dossier": Path(dossier).as_posix(), "sha256": src}, sort_keys=True)
    d = json.loads(TABLE_EMBARQUEE)
    return d["profils"], json.dumps(d["source"], sort_keys=True)


def lire_profils(node):
    """Python SOP : contours des profils (plan XY, x = u, y = v), attributs décrits dans l'en-tête du module."""
    import hou
    geo = node.geometry()
    geo.clear()
    table, source = table_embarquee(node)
    for nom, t in (("profil", ""), ("famille", "")):
        geo.addAttrib(hou.attribType.Prim, nom, t)
    for nom in ("base", "H", "h_fil_eau"):
        geo.addAttrib(hou.attribType.Prim, nom, 0.0)
    for nom in ("i_top", "k_back", "n_pts"):
        geo.addAttrib(hou.attribType.Prim, nom, 0)
    for nom in ("u_cs", "v_cs"):
        geo.addAttrib(hou.attribType.Point, nom, 0.0)
    geo.addAttrib(hou.attribType.Point, "chaine", 0)
    geo.addAttrib(hou.attribType.Point, "rang", 0)
    geo.addAttrib(hou.attribType.Point, "p_cs", 0.0)
    geo.addAttrib(hou.attribType.Point, "perim", 0.0)
    noms = sorted(table)
    for nom in noms:
        t = table[nom]
        c = t["contour"]
        i_top, k_back = _indices(c, t["base"], t["H"])
        pts = []
        # caniveau : section posée devant la face vue de la bordure (u de −largeur à 0 dans le repère de la bordure ;
        # bordures_elements.json caniveaux.pose : u = 0 côté chaussée, u = largeur contre la face vue)
        du = -float(t["base"]) if t["famille"] == "caniveau" else 0.0
        acc, cum = 0.0, []                     # abscisse sur le périmètre du contour (UV en mètres : v des bordures)
        for i in range(len(c)):
            cum.append(acc)
            j = (i + 1) % len(c)
            acc += ((c[j][0] - c[i][0]) ** 2 + (c[j][1] - c[i][1]) ** 2) ** 0.5
        for i, (u, v) in enumerate(c):
            u = u + du
            p = geo.createPoint()
            p.setPosition((u, v, 0.0))
            p.setAttribValue("u_cs", u)
            p.setAttribValue("v_cs", v)
            p.setAttribValue("chaine", 0 if i <= k_back else 1)
            p.setAttribValue("rang", i)
            p.setAttribValue("p_cs", cum[i])
            p.setAttribValue("perim", acc)
            pts.append(p)
        pr = geo.createPolygon()
        for p in pts:
            pr.addVertex(p)
        pr.setAttribValue("profil", nom)
        pr.setAttribValue("famille", t["famille"])
        pr.setAttribValue("base", float(t["base"]))
        pr.setAttribValue("H", float(t["H"]))
        pr.setAttribValue("h_fil_eau", float(t.get("h_fil_eau", 0.0)))
        pr.setAttribValue("i_top", int(i_top))
        pr.setAttribValue("k_back", int(k_back))
        pr.setAttribValue("n_pts", len(c))
    geo.addArrayAttrib(hou.attribType.Global, "pj_profils_noms", hou.attribData.String)
    geo.addArrayAttrib(hou.attribType.Global, "pj_profils_base", hou.attribData.Float)
    geo.addArrayAttrib(hou.attribType.Global, "pj_profils_H", hou.attribData.Float)
    geo.addArrayAttrib(hou.attribType.Global, "pj_profils_hfe", hou.attribData.Float)
    geo.addAttrib(hou.attribType.Global, "pj_profils_source", "")
    geo.setGlobalAttribValue("pj_profils_hfe", [float(table[n].get("h_fil_eau", 0.0)) for n in noms])
    geo.setGlobalAttribValue("pj_profils_noms", noms)
    geo.setGlobalAttribValue("pj_profils_base", [float(table[n]["base"]) for n in noms])
    geo.setGlobalAttribValue("pj_profils_H", [float(table[n]["H"]) for n in noms])
    geo.setGlobalAttribValue("pj_profils_source", source)
