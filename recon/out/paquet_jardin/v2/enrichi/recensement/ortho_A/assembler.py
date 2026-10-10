#!/usr/bin/env python
"""Assemble les observations ortho_A -> ../obs_ortho_A.json (agent VISION-ORTHO-A).

Entrées : saisie/obs_<tuile>.py (observations lues à l'œil sur les dalles brutes, les superpositions
et les découpes zoomées ; positions L93 relevées sur les graduations), plus des confirmations
automatiques de marquages (contraste_marquages.analyser : peinture nette à la position décrite).
Re-lie chaque identifiant de marquage à la description courante (base/marquages.geojson, schéma
≥ 0.3) via marquages_hypotheses.geojson quand l'identifiant v0.2 a disparu. Écrit les preuves
(découpe brut | superposition) dans preuves/ pour les observations marquées preuve=True.

  python assembler.py            (déterministe ; relancer après une régénération de la description)
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "saisie"))
import overlay as ov  # noqa: E402
import contraste_marquages as cm  # noqa: E402
import obs_lib  # noqa: E402

SORTIE = ICI.parent / "obs_ortho_A.json"
AGENT = "ORTHO_A"
CLASSES = {"bordure", "surface", "ilot", "marquage", "panneau", "feu", "candelabre", "potelet", "mobilier", "arbre",
           "massif", "haie", "tampon", "avaloir", "bev", "abri_bus", "cloture", "batiment", "autre"}
STATUTS = {"confirme", "attribut_corrige", "position_corrigee", "absent_de_description", "absent_sur_image", "incertain"}


def charger_saisie():
    for f in sorted((ICI / "saisie").glob("obs_*.py")):
        code = f.read_text(encoding="utf-8")
        exec(compile(code, str(f), "exec"), {"__name__": "saisie"})
    return list(obs_lib.OBS)


def table_v03():
    base = ov.DESC / "base"
    ids = {f["properties"]["id"]: f for f in ov._feats(base / "marquages.geojson")}
    hyp = {}
    for h in ov._feats(base / "marquages_hypotheses.geojson"):
        p = h["properties"]
        hyp.setdefault(p.get("hypothese"), []).append((p.get("decision"), p.get("entite")))
    schema = None
    try:
        schema = ov._lire(base / "marquages.geojson")["description_v2"]["schema"]
    except Exception:
        pass
    return ids, hyp, schema


def autres_ids():
    C = ov.couches()
    s = set()
    for k in ("bordures", "surfaces", "ilots", "ponctuels", "mobilier", "arbres", "bordures_site", "surfaces_v1"):
        s |= {f["properties"].get("id") for f in C[k]}
    return s


def relier(o, ids, hyp, autres):
    lien = o["lien"]
    if not lien or lien in ids or lien in autres:
        return
    a = o["attributs"]
    a["lien_v02"] = lien
    for dec, ent in hyp.get(lien, []):
        a["decision_description_v03"] = dec
        if ent and ent.split(",")[0] in ids:
            o["lien"] = ent.split(",")[0]
            return
    o["lien"] = None


def confirmations_auto(deja, ids):
    """Marquages conservés (ou refaits à l'identique) dont la peinture est nette à la position décrite."""
    out = []
    boites = [(float(t.split("_")[0]), float(t.split("_")[1])) for t in ov.TUILES_A]
    for mid, f in sorted(ids.items()):
        p = f["properties"]
        if mid in deja or p.get("etat") not in ("conserve", "refait_2025_identique"):
            continue
        polys, _ = cm.anneaux(f["geometry"])
        pts = [c for pp in polys for r in pp for c in r]
        if not pts:
            continue
        cx, cy = sum(c[0] for c in pts) / len(pts), sum(c[1] for c in pts) / len(pts)
        t = next((f"{int(x)}_{int(y)}" for x, y in boites if x <= cx < x + 50 and y <= cy < y + 50), None)
        if t is None:
            continue
        r = cm.analyser(f)
        if not r or r["contraste"] < 20 or abs(r["dx_m"]) > 0.1 or abs(r["dy_m"]) > 0.1 or r["part_claire"] < 0.3:
            continue
        # point de l'entité le plus proche du centre (une ligne courbe n'a pas son centre sur elle)
        q = min(pts, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
        b = ov.etat_travaux(q[0], q[1], 0.3)
        out.append({"tuile": t, "classe": "marquage", "sous_type": f"{p.get('classe')}_{p.get('type')}", "xy": [q[0], q[1]],
                    "statut": "confirme", "lien": mid,
                    "attributs": {"observe": "peinture nette à la position décrite sur l'ortho 2022 (contrôle automatique)",
                                  "contraste": r["contraste"], "part_claire": r["part_claire"], "decalage_m": [r["dx_m"], r["dy_m"]],
                                  "couleur": p.get("couleur"), "etat_description": p.get("etat"), "src_description": p.get("src"),
                                  "methode_controle": "contraste_marquages.py (empreinte vs anneau 0,15-0,45 m, recherche ±0,6 m)"},
                    "conf": "moyenne", "prec": 0.1, "methode": "pixel_ortho",
                    "valide": True if (p.get("etat") == "conserve" and not b & (1 | 2 | 8)) else "incertain",
                    "raison": ("marquage conservé hors zone de travaux 2025" if (p.get("etat") == "conserve" and not b & (1 | 2 | 8))
                               else f"{ov.libelle_travaux(b)} ; état {p.get('etat')} : géométrie 2022 supposée reprise à l'identique"),
                    "preuve": False, "cote": 6.0, "auto": True})
    return out


def valide_norm(o):
    v = o["valide"]
    x, y = o["xy"]
    b = ov.etat_travaux(x, y, 0.3)
    if v is None:
        v = True if not b else "incertain"
    raison = o["raison"] or ov.libelle_travaux(b)
    return {"valeur": v, "raison": raison, "zone_travaux_2025": ov.libelle_travaux(b)}


def preuve(o, oid):
    t = o["tuile"]
    x, y = o["xy"]
    u, v = ov.l932px(t, x, y)
    pr = {"overlay": f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_A/overlays/{t}_overlay.jpg",
          "dalle": f"data/sites/paquet_jardin/ortho5cm_2022/pcrs5cm_{t}.jpg", "pixels": [round(u, 1), round(v, 1)]}
    if o["preuve"]:
        c = max(6.0, min(float(o.get("cote") or 10.0), 20.0))
        if o["prec"] >= 5:
            c = 25.0
        zoom = 2.5 if c <= 10 else (1.5 if c <= 16 else 1.0)
        A = ov.Rendu(x - c / 2, y - c / 2, x + c / 2, y + c / 2, ppm=20 * zoom, brut=True).grille()
        B = ov.Rendu(x - c / 2, y - c / 2, x + c / 2, y + c / 2, ppm=20 * zoom).dessiner().grille()
        A.marques([(x, y)])
        B.marques([(x, y)])
        W, H = A.im.size
        im = Image.new("RGB", (2 * W + 6, H + 22), (255, 255, 255))
        im.paste(A.im, (0, 22))
        im.paste(B.im, (W + 6, 22))
        d = ImageDraw.Draw(im)
        d.text((4, 3), f"{oid}  {o['classe']}/{o['sous_type']}  {o['statut']}  lien={o['lien']}  ortho 2022-05-10  "
                       f"L93 {x:.2f} {y:.2f}", fill=(0, 0, 0), font=ov._police(13))
        f = ICI / "preuves" / f"{oid}.jpg"
        f.parent.mkdir(exist_ok=True)
        im.save(f, quality=88)
        pr["fichier"] = f"recon/out/paquet_jardin/v2/enrichi/recensement/ortho_A/preuves/{oid}.jpg"
        h = c / 2
        pr["bbox_l93"] = [round(x - h, 2), round(y - h, 2), round(x + h, 2), round(y + h, 2)]
    else:
        pr["fichier"] = pr["overlay"]
    return pr


def main():
    obs = charger_saisie()
    ids, hyp, schema = table_v03()
    autres = autres_ids()
    for o in obs:
        relier(o, ids, hyp, autres)
    deja = {o["lien"] for o in obs if o["lien"]}
    obs += confirmations_auto(deja, ids)
    obs.sort(key=lambda o: (ov.TUILES_A.index(o["tuile"]) if o["tuile"] in ov.TUILES_A else 99, bool(o.get("auto"))))
    for p in (ICI / "preuves").glob("ORTHO_A-*.jpg"):
        p.unlink()
    res = []
    for n, o in enumerate(obs, 1):
        oid = f"{AGENT}-{n:04d}"
        cl = o["classe"]
        assert cl in CLASSES, (cl, o)
        assert o["statut"] in STATUTS, o["statut"]
        x, y = o["xy"]
        res.append({
            "id": oid,
            "source": f"ortho2022:{o['tuile']}",
            "date_image": ov.DATE_ORTHO,
            "classe": cl,
            "sous_type": o["sous_type"],
            "attributs": o["attributs"],
            "position": {"l93": [round(x, 2), round(y, 2)], "local": [round(x - ov.O[0], 2), round(y - ov.O[1], 2)],
                         "precision_m": o["prec"], "methode": o["methode"]},
            "lien_description": o["lien"],
            "statut": o["statut"],
            "valide_2026": valide_norm(o),
            "confiance": o["conf"],
            "preuve": preuve(o, oid),
            "controle": "automatique" if o.get("auto") else "visuel",
        })
    meta = {"agent": "VISION-ORTHO-A", "image": "PCRS 5 cm Grenoble-Alpes Métropole, prise de vue du 2022-05-10 (avant travaux 2025)",
            "description_lue": {"marquages_schema": schema, "sol": "base/{bordures,surfaces,ilots,ponctuels_sol}.geojson (zone pilote) + coherence/carte/bordures_site.geojson + surfaces_2026 v1"},
            "n": len(res)}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (ICI / "meta_obs.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(len(res), Counter(r["classe"] for r in res), Counter(r["statut"] for r in res), Counter(r["controle"] for r in res))


if __name__ == "__main__":
    main()
