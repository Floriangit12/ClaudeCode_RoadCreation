"""Dossier de compréhension de la comparaison v2 : l'index des images que le modèle (Claude) lit pour comprendre la
scène et la comparer au rendu (principe de l'utilisateur, 18/10/2026 : « l'outil de comparaison, c'est directement toi
qui passes les images dans ton modèle et essaies de comprendre la scène » ; la fusion des orthos et des photos se fait
dans le modèle, pas par un algorithme).

Écrit sous <site>/comprehension/ (aucune photo de tiers) :
- `LISEZMOI.md` : ordre de lecture (orthos de plusieurs dates → plans d'index → vue de dessus rendu | ortho → vues du
  centre par direction d'observation → vues de chaque branche → îlots et passages → mouvements), et pour chaque vue :
  numéro sur le plan, clé, date (DANS / HORS de la fenêtre d'état), source, porteur, position, visée, zones vues et
  fichiers à lire (vue native 1 092 px, planche photo | rendu, rendu seul) ;
- `index.json` : la même chose, structurée ;
- `plan_vues_centre.png`, `plan_vues_site.png` : la meilleure ortho du kit (même cadrage que le kit) avec les zones
  d'intérêt et la position de chaque photo (numéro P01…, traits de visée de ses vues ; bleu Panoramax, orange
  Mapillary, magenta hors fenêtre d'état) : c'est le plan qui relie chaque vue au terrain.
Sous <site>/photos_non_versionnees/v2/comprehension/ (photos de tiers) : `centre_pNN.png`, planches 2 × 2 de quatre
vues du centre (une par direction d'observation si possible), pour voir le centre sous plusieurs angles d'un coup ;
les vues natives restent la référence pour un détail.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

import orthos as OR
import planches as PL
import zones as Z

COUL = {"panoramax": (30, 110, 255), "mapillary": (255, 140, 0), "hors": (230, 0, 200)}
NOYAU = ("centre", "anneau", "ilot_central")


def _num(sel, zones):
    """Numéros des photos : celles du cœur d'abord, puis par distance au cœur ; {id photo: « P01 »}."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    noyau = [z for z in zones if z.type in NOYAU]
    ref = unary_union([z.poly for z in noyau]) if noyau else unary_union([z.poly for z in zones])
    vus, ordre = set(), []
    for p in sel["photos"]:
        if p["id"] in vus:
            continue
        vus.add(p["id"])
        d = ref.distance(Point(p["position_modele"]["s"], p["position_modele"]["t"]))
        ordre.append((round(d, 1), p["date"], p["id"]))
    ordre.sort()
    return {pid: f"P{k + 1:02d}" for k, (_, _, pid) in enumerate(ordre)}


def _lettre(ph):
    return "abcdefgh"[max(0, ph["vue"].get("rang_dans_la_photo", 1) - 1)]


def _plan(site, sel, num, kit_man, emprise, dst):
    """Plan d'index : ortho du kit + zones + positions des photos (numéros) et visées des vues."""
    c, e = OR.meilleure(kit_man, emprise)
    if c is None:
        return None
    b = e["emprise_l93"]
    pas = e["pas_commun_m"]
    Wc, Hc = e["taille_commune_px"]
    im = Image.open(Path(site.dos) / "orthos" / c["brut"]).convert("RGB").resize((Wc, Hc), Image.LANCZOS)
    im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.25)
    out = Image.new("RGB", (Wc, Hc + 44), (250, 250, 247))
    out.paste(im, (0, 44))
    d = ImageDraw.Draw(out, "RGBA")
    A = site.ancrage

    def px(s, t):
        x, y = A.vers_l93(s, t)
        return (float(x) - b[0]) / pas, 44 + (b[3] - float(y)) / pas
    for z in site.zones:
        col = Z.COULEURS[z.type]
        for g in getattr(z.poly, "geoms", [z.poly]):
            d.polygon([px(*q) for q in g.exterior.coords], outline=col + (230,), fill=col + (28,))
        cx, cy = px(*z.centre)
        if 0 <= cx < Wc and 44 <= cy < Hc + 44:
            d.text((cx - 10, cy - 6), z.id, fill=col + (255,), font=PL.police(11), stroke_width=2,
                   stroke_fill=(255, 255, 255, 230))
    deja = set()
    for p in sel["photos"]:
        x, y = px(p["position_modele"]["s"], p["position_modele"]["t"])
        if not (-20 <= x < Wc + 20 and 24 <= y < Hc + 64):
            continue
        col = COUL["hors"] if p.get("hors_fenetre_etat") else COUL.get(p.get("source", "panoramax"))
        a = math.radians(p["vue"]["lacet_modele_deg"] + (90.0 - site.ancrage.alpha))
        L = 26 if emprise == "centre" else 16
        d.line((x, y, x + L * math.cos(a), y - L * math.sin(a)), fill=col + (220,), width=2)
        if p["id"] not in deja:
            deja.add(p["id"])
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=col + (255,), outline=(0, 0, 0, 255))
            d.text((x + 5, y + 1), num[p["id"]], fill=(0, 0, 0, 255), font=PL.police(12 if emprise == "centre" else 11),
                   stroke_width=2, stroke_fill=(255, 255, 255, 255))
    d.text((5, 3), f"{site.nom} — index des vues ({emprise}) sur {c['nom']} ({c['date']}), nord en haut, "
                   f"{pas * 100:.1f} cm/px — P.. = photo (numéros du LISEZMOI), trait = visée d'une vue",
           fill=(0, 0, 0), font=PL.police(13))
    d.text((5, 22), "bleu Panoramax, orange Mapillary, magenta : hors fenêtre d'état (état antérieur) ; zones : "
                    "rouge centre/anneau, orange îlots, bleu passages, violet approches", fill=(40, 40, 40),
           font=PL.police(12))
    out.save(dst)
    return {"fichier": Path(dst).name, "fond": c["nom"], "date_fond": c["date"], "pas_m": pas}


def _planches_centre(site, vues_c, num, dossier):
    """Planches 2 × 2 de vues du centre (photos de tiers : sous photos_non_versionnees/)."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    # une vue par secteur d'abord (tour d'horizon), puis les autres
    par_s = {}
    for v in vues_c:
        par_s.setdefault(v["secteur_centre"], []).append(v)
    ordre = []
    while any(par_s.values()):
        for s in Z.SECTEURS:
            if par_s.get(s):
                ordre.append(par_s[s].pop(0))
    pages = []
    c = 528
    for k in range(0, len(ordre), 4):
        lot = ordre[k:k + 4]
        pl = Image.new("RGB", (2 * c, 24 + 2 * (18 + c)), (22, 22, 26))
        d = ImageDraw.Draw(pl)
        d.text((6, 4), f"{site.nom} — vues du CENTRE {k + 1} à {k + len(lot)} sur {len(ordre)} (réduites de moitié ; "
                       "vue native : photos_non_versionnees/v2/vues/vue_<clé>.png) — photos © auteurs (selection.json)",
               fill=(235, 235, 235), font=PL.police(12))
        for q, v in enumerate(lot):
            x, y = (q % 2) * c, 24 + (q // 2) * (18 + c)
            f = Path(site.dossiers["vues"]) / f"vue_{v['cle']}.png"
            hf = " HORS FENÊTRE" if v["hors_fenetre_etat"] else ""
            d.text((x + 4, y + 2), f"{v['numero']} {v['cle']} {v['date'][:10]}{hf} — vise {v['secteur_centre']} "
                                   f"— centre à {v['distance_centre_m']:.0f} m", fill=(255, 230, 120) if not hf else (255, 120, 230),
                   font=PL.police(12))
            if f.exists():
                im = Image.open(f).convert("RGB")
                pl.paste(im.resize((c, int(round(im.size[1] * c / im.size[0]))), Image.LANCZOS), (x, y + 18))
        dst = dossier / f"centre_p{k // 4 + 1:02d}.png"
        pl.save(dst)
        pages.append(dst.name)
    return pages


def ecrire(site, sel, poses, kit_man, dessus_man, couverture):
    """Écrit le dossier de compréhension ; renvoie index.json (dict)."""
    dc = Path(site.dos) / "comprehension"
    dc.mkdir(parents=True, exist_ok=True)
    zones = site.zones
    zid = {z.id: z for z in zones}
    num = _num(sel, zones)
    pnv = "photos_non_versionnees/v2"
    rel_vues = f"{pnv}/vues"
    rel_pl = f"{pnv}/planches"
    poses_par = {(p.get("cle") or p["id8"]): p for p in (poses or [])}
    vues = []
    for ph in sel["photos"]:
        zv = ph.get("zones_vues") or {}
        noy = {k: v for k, v in zv.items() if zid.get(k) is not None and zid[k].type in NOYAU}
        po = poses_par.get(ph["cle"]) or {}
        vues.append({
            "numero": num[ph["id"]] + _lettre(ph), "photo": num[ph["id"]], "cle": ph["cle"], "id": ph["id"],
            "source": ph.get("source", "panoramax"), "date": ph["date"], "hors_fenetre_etat": bool(ph.get("hors_fenetre_etat")),
            "type": ph["type"], "porteur": ph["porteur"], "auteur": ph.get("auteur"), "licence": ph.get("licence"),
            "position_site_m": [ph["position_modele"]["s"], ph["position_modele"]["t"]],
            "dans_le_coeur": ph["position_modele"].get("dans_le_coeur"),
            "vise_azimut_grille_deg": ph["vue"].get("azimut_grille_deg"), "vers": ph["vue"].get("cible"),
            "zones_vues": {k: f"{v['part']:.2f} {v['secteur']} {v['distance_m']:.0f} m" for k, v in
                           sorted(zv.items(), key=lambda x: -x[1]["part"])},
            "secteur_centre": max(noy.items(), key=lambda x: x[1]["part"])[1]["secteur"] if noy else None,
            "part_centre": max([v["part"] for v in noy.values()] or [0.0]),
            "distance_centre_m": min([v["distance_m"] for v in noy.values()] or [0.0]),
            "mouvement": (ph.get("mouvement") or {}).get("mouvement"), "sequence": ph.get("collection"),
            "pose": po.get("statut"), "confiance_pose": (po.get("confiance") or {}).get("niveau"),
            "fichiers": {"vue_native": f"{rel_vues}/vue_{ph['cle']}.png", "planche": f"{rel_pl}/planche_{ph['cle']}.png",
                         "superposition": f"{rel_pl}/superposition_{ph['cle']}.png",
                         "rendu": f"rendus_v2/rendu_{ph['cle']}.png"}})
    vues_c = sorted([v for v in vues if v["part_centre"] >= Z.SEUIL_VOIT],
                    key=lambda v: (Z.SECTEURS.index(v["secteur_centre"]), v["distance_centre_m"], v["cle"]))
    plans = {}
    for e in ("centre", "site"):
        r = _plan(site, sel, num, kit_man or {}, e, dc / f"plan_vues_{e}.png")
        if r:
            plans[e] = r
    pages_c = _planches_centre(site, vues_c, num, Path(site.pnv) / "v2" / "comprehension")
    # vues par zone (hors cœur)
    par_zone = {}
    for z in zones:
        if z.type in NOYAU:
            continue
        lst = []
        for v in vues:
            ph = next(p for p in sel["photos"] if p["cle"] == v["cle"])
            e = (ph.get("zones_vues") or {}).get(z.id)
            if e and e["part"] >= Z.SEUIL_VOIT:
                lst.append((Z.SECTEURS.index(e["secteur"]), -e["part"], v["numero"], v["cle"], e))
        par_zone[z.id] = [{"numero": n, "cle": c, "part": e["part"], "secteur": e["secteur"], "distance_m": e["distance_m"]}
                          for _, _, n, c, e in sorted(lst)]
    mouvements = {}
    for v in sorted(vues, key=lambda v: (v["date"], v["cle"])):
        if v["mouvement"]:
            cle_mv = f"{v['mouvement']} — séquence {str(v['sequence'])[:12]} du {v['date'][:10]}"
            mouvements.setdefault(cle_mv, []).append(v["numero"] + " " + v["cle"])
    idx = {"schema": "comparaison_comprehension/0.1", "site": site.nom, "genre": site.genre,
           "fenetre_etat": [sel["criteres"].get("depuis"), sel["criteres"].get("jusqu_au")],
           "complement_depuis": sel["criteres"].get("complement_depuis"),
           "photos": len(num), "n_vues": len(vues), "vues_du_centre": [v["numero"] for v in vues_c],
           "plans": plans, "planches_centre": [f"{pnv}/comprehension/{p}" for p in pages_c],
           "vues": vues, "vues_par_zone": par_zone, "mouvements": mouvements}
    (dc / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    (dc / "LISEZMOI.md").write_text(_lisezmoi(site, sel, idx, kit_man, dessus_man, couverture, vues_c), encoding="utf-8")
    return idx


def _ligne_vue(v):
    hf = " **HORS FENÊTRE**" if v["hors_fenetre_etat"] else ""
    zv = ", ".join(f"{k} {t}" for k, t in list(v["zones_vues"].items())[:3])
    return (f"| {v['numero']} | `{v['cle']}` | {v['date'][:10]}{hf} | {v['source'][:3]} {v['type']} {v['porteur']} | "
            f"({v['position_site_m'][0]:.0f} ; {v['position_site_m'][1]:.0f}){' cœur' if v['dans_le_coeur'] else ''} | "
            f"{v['vise_azimut_grille_deg']:.0f}° → {str(v['vers'])[:22]} | {zv} | `{v['fichiers']['vue_native']}` |")


def _lisezmoi(site, sel, idx, kit_man, dessus_man, couverture, vues_c):
    st = sel["statistiques"]
    L = [f"# Dossier de compréhension — {site.nom} ({site.genre})", "",
         "*Généré par `recon/generateur/comparaison` (v2). À LIRE PAR LE MODÈLE, image par image, dans l'ordre ci-dessous : "
         "chaque image citée entre sans réduction (sinon ses tuiles sont citées). C'est en croisant ces images (orthos de "
         "plusieurs dates + photos sous plusieurs angles + rendu) que la scène est comprise : aucune fusion n'est faite par "
         "un algorithme. Chemins relatifs au dossier du site (celui de `selection.json`).*", "",
         f"- Fenêtre d'état : {idx['fenetre_etat'][0]} → {idx['fenetre_etat'][1] or 'aujourd hui'} ; "
         f"{st['photos'] - st.get('photos_hors_fenetre_etat', 0)} photos dedans, {st.get('photos_hors_fenetre_etat', 0)} "
         f"hors fenêtre (antérieures, depuis {idx['complement_depuis']}) : un élément vu seulement sur une photo hors "
         "fenêtre doit être confirmé par une photo de la fenêtre ou par l'ortho la plus proche de la date d'état.",
         f"- {st['photos']} photos ({st['photos_panoramax']} Panoramax, {st['photos_mapillary']} Mapillary), {st['vues']} vues "
         f"(photos 360° : plusieurs vues par photo), {st['photos_dans_le_coeur']} photos prises dans le cœur ou à son bord ; "
         f"{len(vues_c)} vues voient le centre ; zones aveugles : {', '.join(st['zones_aveugles']) or 'aucune'}.", ""]
    # 1. orthos
    L += ["## 1. Vue générale : orthos de plusieurs dates, même emprise, même cadrage (`orthos/`)", ""]
    if kit_man:
        for e in kit_man.get("emprises", []):
            L.append(f"**{e['nom']}** (x {e['emprise_site'][0]:.0f} à {e['emprise_site'][2]:.0f} m, y {e['emprise_site'][1]:.0f} "
                     f"à {e['emprise_site'][3]:.0f} m du repère du site ; {e['pas_commun_m'] * 100:.1f} cm/px commun) :")
            L.append(f"- dates côte à côte : " + ", ".join(f"`orthos/{p}`" for p in e.get("planches_dates", [])))
            for c in e["couches"]:
                t = f"- `orthos/{c['image']}` — {c['libelle']}, prise de vue {c['date'] or 'inconnue'}"
                if c.get("dates_emprise") and len(c["dates_emprise"]) > 1:
                    t += f" (mosaïque : {', '.join(c['dates_emprise'])})"
                if c["tuiles_natives"]:
                    t += f" ; tuiles natives : {len(c['tuiles_natives'])} (`orthos/{c['tuiles_natives'][0]['fichier']}` …)"
                L.append(t)
            L.append("")
        if kit_man.get("contexte"):
            cx = kit_man["contexte"]
            L += [f"Contexte : `orthos/{cx['image']}` — {cx['libelle']} (x {cx['emprise_site'][0]} à {cx['emprise_site'][2]} m, "
                  f"y {cx['emprise_site'][1]} à {cx['emprise_site'][3]} m), à lire en premier pour les noms des voies.", ""]
        if kit_man.get("couches_absentes"):
            L.append("Couches absentes : " + "; ".join(f"{a['nom']} ({', '.join(f'{k} : {v}' for k, v in a['motifs'].items())})"
                                                      for a in kit_man["couches_absentes"]))
            L.append("")
    else:
        L += ["(kit absent : lancer l'étape `orthos`)", ""]
    # 2. plans
    L += ["## 2. Index des vues sur le plan", ""]
    for e, r in idx["plans"].items():
        L.append(f"- `comprehension/{r['fichier']}` — {e}, fond {r['fond']} ({r['date_fond']}) : position de chaque photo "
                 "(P01…) et visée de ses vues")
    L += ["- `plan_couverture_centre.png`, `plan_couverture.png` — nombre de vues par zone et directions d'observation "
          "(roses), zones aveugles en rouge", "- `plan_site.png` — poses retenues (GNSS → retenue) et champs de vue", ""]
    # 3. dessus
    L += ["## 3. Vue de dessus : rendu du modèle | ortho (`dessus/`)", ""]
    if dessus_man:
        for e in dessus_man.get("emprises", []):
            for o in e["orthos"]:
                L.append(f"- {e['nom']} / {o['libelle']} : {len(o['tuiles'])} tuiles `dessus/{o['tuiles'][0]['planche']}` … "
                         f"(rendu | ortho) et `dessus/{o['tuiles'][0]['contours']}` … (contours du modèle sur l'ortho : "
                         "bordures rouges, limites de matériau jaunes, marquages cyan)")
    else:
        L.append("(vue de dessus absente : étape `dessus`)")
    L.append("")
    # 4. centre
    L += [f"## 4. Vues du CENTRE (zone de conflit), par direction d'observation ({len(vues_c)} vues)", "",
          "Planches 2 × 2 (tour d'horizon) : " + ", ".join(f"`{p}`" for p in idx["planches_centre"]), "",
          "| n° | clé | date | source | prise (x ; y) m | visée → cible | zones vues (part, secteur, distance) | vue native |",
          "|---|---|---|---|---|---|---|---|"]
    L += [_ligne_vue(v) for v in vues_c]
    L += ["", "Pour chaque vue : planche photo | rendu | contours | arêtes = `photos_non_versionnees/v2/planches/planche_<clé>.png` ; "
          "rendu seul = `rendus_v2/rendu_<clé>.png`.", ""]
    # 5. branches
    vv = {v["numero"]: v for v in idx["vues"]}
    L += ["## 5. Vues de chaque branche, îlot et passage", ""]
    for zid_, lst in idx["vues_par_zone"].items():
        z = next(z for z in site.zones if z.id == zid_)
        L.append(f"**{zid_}** — {z.nom} : {len(lst)} vues" + (" — **ZONE AVEUGLE**" if not lst else ""))
        if lst:
            L.append("  " + " ; ".join(f"{x['numero']} `{x['cle']}` ({x['secteur']}, {x['distance_m']:.0f} m"
                                       f"{', HF' if vv[x['numero']]['hors_fenetre_etat'] else ''})" for x in lst[:24])
                     + (" …" if len(lst) > 24 else ""))
        L.append("")
    # 6. mouvements
    L += ["## 6. Mouvements (séquences qui traversent le cœur, dans l'ordre de prise)", ""]
    if idx["mouvements"]:
        for mv, lst in idx["mouvements"].items():
            L.append(f"- {mv} : " + " → ".join(f"`{x}`" for x in lst))
    else:
        L.append("- aucun passage de séquence dans le cœur parmi les photos retenues")
    L += ["", "## 7. Après lecture", "",
          "Remplir `ecarts.json` : `centre_zone_conflit.rubriques` (îlots, guidage, traversées cyclables, pavés, zébras, "
          "passages, refuges, autres marquages : conforme | différent | absent | en trop | non visible + détail et images "
          "qui le montrent), puis la grille de chaque vue utile. Écrire la compréhension de la scène (ce qu'il y a où, "
          "images qui le montrent, contradictions entre dates résolues, incertitudes) dans le dossier du site.", ""]
    return "\n".join(L)
