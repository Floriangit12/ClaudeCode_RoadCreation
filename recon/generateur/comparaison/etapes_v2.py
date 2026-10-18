"""Étapes de la comparaison v2 (comparer_multivues.py --v2) : un DOSSIER DE COMPRÉHENSION que le modèle (Claude) lit
lui-même — sélection guidée par la couverture des zones d'intérêt (selection_v2.py), kit multi-orthos datées
(orthos.py), plusieurs vues par photo 360°, poses en parallèle (pose_lot.py), rendus Karma groupés et repris quand
rien n'a changé (rendu_hython.py), vue de dessus rendu | ortho (dessus.py), planches, carte de couverture, grille
d'écarts avec une section « centre / zone de conflit », index de lecture (dossier.py). Voir README.md.

Dossiers (sous <sortie>/<site>/) : selection.json, zones.json, couverture.json, poses.json, ecarts.json, rapport.json,
plan_site.png, plan_couverture.png, plan_couverture_centre.png, orthos/, rendus_v2/, dessus/, comprehension/
(diffusables) ; photos_non_versionnees/{brut, v2/vues, v2/planches, v2/comprehension} (photos de tiers). Une sélection
v1 déjà présente est archivée dans v1/ (copie des JSON et du plan) avant d'être remplacée ; les fichiers de vues d'une
sélection v2 précédente sont retirés (menage), aucun dossier n'est effacé.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import api_mapillary as AM
import api_panoramax as AP
import comparer_multivues as CM
import dessus as DS
import geo
import modele as MO
import planches as PL
import pose as PO
import selection_v2 as S2
import vues as V
import zones as Z
import orthos as OR
import dossier as DO

ICI = Path(__file__).resolve().parent
PAIRES_PAR_PAGE = 15
COUL_SOURCE = {"panoramax": (30, 90, 220), "mapillary": (230, 120, 0)}


def journal(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------------------------------------ site
class SiteV2(CM.Site):
    def __init__(self, nom, conf):
        super().__init__(nom, conf)
        v2 = self.pnv / "v2"
        self.dossiers.update({"vues": v2 / "vues", "planches": v2 / "planches", "tuiles": v2 / "tuiles",
                              "rendus": self.dos / "rendus_v2", "dessus": self.dos / "dessus"})
        self.genre, self.zones = Z.zones_site(self.modele, self.ancrage, CM.DEPOT / conf["modele"])

    def zones_par_id(self):
        return {z.id: z for z in self.zones}


def archiver_v1(site):
    """Copie (sans rien effacer) des sorties v1 du site dans v1/ avant leur remplacement par la v2."""
    sel = CM.lire(site.dos / "selection.json")
    if not sel or sel.get("version") == 2:
        return None
    d = site.dos / "v1"
    if (d / "selection.json").exists():
        return d
    d.mkdir(parents=True, exist_ok=True)
    for n in ("selection.json", "poses.json", "ecarts.json", "rapport.json", "plan_site.png"):
        if (site.dos / n).exists():
            shutil.copy2(site.dos / n, d / n)
    journal(f"  sorties v1 archivées dans {d}")
    return d


def menage(site, sel):
    """Retire les FICHIERS de vues d'une sélection précédente (rendus, vues, planches dont la clé n'est plus dans la
    sélection), pour qu'un dossier ne mélange pas deux sélections. Aucun dossier n'est effacé."""
    cles = {p["cle"] for p in sel["photos"]}
    n = 0
    for d, prefixes in ((site.dossiers["rendus"], ("rendu_",)), (site.dossiers["vues"], ("vue_",)),
                        (site.dossiers["planches"], ("planche_", "vue_", "superposition_", "aretes_"))):
        if not Path(d).is_dir():
            continue
        for f in Path(d).glob("*.png"):
            for pre in prefixes:
                if f.name.startswith(pre) and not f.name.startswith("planche_synthese") and \
                        f.stem[len(pre):] not in cles and f.stem[len(pre):] not in ("dessus",):
                    f.unlink()
                    n += 1
                    break
    if n:
        journal(f"  ménage : {n} fichiers de vues d'une sélection précédente retirés")


def selection_v1(site):
    for f in (site.dos / "v1" / "selection.json", site.dos / "selection.json"):
        s = CM.lire(f)
        if s and s.get("version") != 2:
            return s
    return None


# ------------------------------------------------------------------------------------------------ sélection
def etape_selection(site, conf, args):
    archiver_v1(site)
    conf_sel = dict(conf, porteurs_sequences=args.porteurs)
    sel = S2.choisir(site.nom, conf_sel, site.modele, site.ancrage, site.zones, site.genre, site.dossiers,
                     rafraichir=args.rafraichir, depuis=args.depuis, jusqu_au=args.jusqu_au,
                     complement_depuis=getattr(args, "complement_depuis", None),
                     exclure=getattr(args, "exclure_periodes", None),
                     mapillary=not args.sans_mapillary, journal=journal)
    sel["ancrage"] = site.ancrage.dict() | {"diagnostic": site.diag_ancrage}
    sel["point_interet"] = conf.get("point_interet")
    CM.ecrire(site.dos / "selection.json", sel)
    menage(site, sel)
    CM.ecrire(site.dos / "zones.json", {"schema": "comparaison_zones/0.1", "site": site.nom, "genre": site.genre,
                                        "repere": "modèle (s, t) ; sites de Meylan : L93 − origine",
                                        "ancrage": site.ancrage.dict(), "zones": [z.dict() for z in site.zones]})
    # couverture avant (sélection v1, mêmes zones, même visibilité) et après
    cv = {"schema": "comparaison_couverture/0.1", "site": site.nom, "seuil_voit_zone": Z.SEUIL_VOIT,
          "apres_v2": {"photos": sel["statistiques"]["photos"], "vues": sel["statistiques"]["vues"],
                       "zones": sel["couverture"]}}
    s1 = selection_v1(site)
    if s1:
        ev = S2.evaluer_selection_v1(s1, site.zones, site.modele, site.ancrage)
        cv["avant_v1"] = {"photos": len(s1["photos"]), "vues": len(s1["photos"]), "zones": Z.couverture(site.zones, ev)}
    CM.ecrire(site.dos / "couverture.json", cv)
    dessiner_couverture(site, sel, cv)
    return sel


# ------------------------------------------------------------------------------------------------ travailleurs
def _lancer(taches, processus, dossier):
    """Lance un sous-processus pose_lot.py par tâche (au plus `processus` à la fois) ; renvoie les résultats."""
    dossier.mkdir(parents=True, exist_ok=True)
    res, encours, attente = [None] * len(taches), [], list(enumerate(taches))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    while attente or encours:
        while attente and len(encours) < processus:
            k, t = attente.pop(0)
            f = dossier / f"tache_{t['mode']}_{k:02d}.json"
            t["resultat"] = str(dossier / f"resultat_{t['mode']}_{k:02d}.json")
            CM.ecrire(f, t)
            log = open(dossier / f"tache_{t['mode']}_{k:02d}.log", "w", encoding="utf-8")
            p = subprocess.Popen([sys.executable, str(ICI / "pose_lot.py"), str(f)], stdout=log, stderr=subprocess.STDOUT,
                                 env=env)
            encours.append((k, t, p, log))
        time.sleep(1.0)
        for e in list(encours):
            k, t, p, log = e
            if p.poll() is not None:
                log.close()
                if p.returncode != 0:
                    raise RuntimeError(f"travailleur {t['mode']} {k} : code {p.returncode} (journal "
                                       f"{dossier / ('tache_%s_%02d.log' % (t['mode'], k))})")
                res[k] = json.loads(Path(t["resultat"]).read_text(encoding="utf-8"))
                encours.remove(e)
    return res


def _morceaux(lst, n):
    n = max(1, min(n, len(lst)))
    return [lst[i::n] for i in range(n)]


# ------------------------------------------------------------------------------------------------ poses
def photo_cache(site):
    out = {p["id"]: dict(p, source="panoramax") for p in (CM.lire(site.dossiers["cache"] / "recherche_v2.json", {}) or {}).get("photos", [])}
    for p in (CM.lire(site.dossiers["cache"] / "mapillary_recherche.json", {}) or {}).get("photos", []):
        out[p["id"]] = p
    return out


def telecharger(photo, qualite, dossier):
    return (AM.telecharger if photo.get("source") == "mapillary" else AP.telecharger)(photo, qualite, dossier)


def etape_pose(site, sel, processus):
    cache = photo_cache(site)
    jpgs = {}
    ids = []
    for ph in sel["photos"]:
        if ph["id"] in jpgs:
            continue
        photo = cache.get(ph["id"])
        if photo is None:
            raise RuntimeError(f"photo {ph['id']} absente du cache de recherche : relancer l'étape selection")
        jpgs[ph["id"]] = str(telecharger(photo, "hd", site.dossiers["brut"]))
        ids.append(ph["id"])
    journal(f"  images HD : {len(jpgs)} photos")
    t0 = time.time()
    d_tr = site.dos / "_travail"
    a360 = [i for i in ids if next(p for p in sel["photos"] if p["id"] == i)["type"] == "360"]
    vert = {}
    for r in _lancer([{"mode": "verticales", "photos": {i: jpgs[i] for i in lot}} for lot in _morceaux(a360, processus)],
                     processus, d_tr):
        vert.update(r)
    journal(f"  verticales des {len(a360)} photos 360° : {time.time() - t0:.0f} s")
    distinctes = {"photos": [next(p for p in sel["photos"] if p["id"] == i) for i in ids]}
    verticales = {i: (np.asarray(v[0]), v[1], v[2]) for i, v in vert.items() if v is not None}
    coherence = CM.coherence_verticales(distinctes, verticales)
    vues = [{"ph": ph, "jpg": jpgs[ph["id"]], "verticale": vert.get(ph["id"]), "coherence": coherence.get(ph["id"], {})}
            for ph in sel["photos"]]
    base = {"mode": "poses", "modele": str(CM.DEPOT / site.conf["modele"]), "ancrage": site.ancrage.dict(),
            "dossier_vues": str(site.dossiers["vues"])}
    morceaux = _morceaux(list(range(len(vues))), processus)
    res = _lancer([dict(base, vues=[vues[i] for i in m]) for m in morceaux], processus, d_tr)
    par = {}
    for m, r in zip(morceaux, res):
        for i, rec in zip(m, r):
            par[i] = rec
    poses = [par[i] for i in range(len(vues))]
    return poses, CM.diagnostic_poses(poses)


# ------------------------------------------------------------------------------------------------ rendus
def lancer_rendu(site, vues_job, echantillons, limite_s, nom_travail):
    scene_usda = CM.DEPOT / site.conf["modele"] / "rendus" / "scene_rendu.usda"
    if not scene_usda.exists():
        raise RuntimeError(f"{scene_usda} absent : fabriquer la scène avec --rendus")
    d = Path(vues_job[0]["sortie_png"]).parent
    tmp = CM.SORTIE / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    travail, resultat = d / f"travail_{nom_travail}.json", d / f"resultat_{nom_travail}.json"
    CM.ecrire(travail, {"scene_usda": str(scene_usda), "manifest_rendus": str(scene_usda.parent / "manifest_rendus.json"),
                        "dossier": str(d), "vues": vues_job, "echantillons": echantillons, "limite_s": limite_s,
                        "resultat": str(resultat), "par_lots": True})
    env = dict(os.environ, TEMP=str(tmp), TMP=str(tmp), HOUDINI_TEMP_DIR=str(tmp), HOUDINI_VEX_DISABLE_JIT="1")
    r = subprocess.run([str(CM.HYTHON), str(ICI / "rendu_hython.py"), str(travail)], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("hython : " + r.stdout[-2000:] + r.stderr[-2000:])
    res = CM.lire(resultat, [])
    for f in d.glob("ciel*.exr*"):
        f.unlink()
    return {"scene_usda": str(scene_usda.relative_to(CM.DEPOT)), "scene_usda_sha256": CM.sha256(scene_usda),
            "sous_couches_sha256": {n: CM.sha256(scene_usda.parent.parent / n) for n in ("l2/route_l2.usda", "l2b/route_l2b.usda")
                                    if (scene_usda.parent.parent / n).exists()},
            "echantillons": echantillons, "vues": res}


def etape_rendu(site, sel, poses, echantillons, limite_s):
    """Rendus des vues ; une vue déjà rendue est reprise telle quelle si sa caméra, son soleil, le nombre
    d'échantillons et la scène (empreinte de scene_rendu.usda et des couches L2/L2b) sont identiques au rendu
    précédent (travail_rendu.json + rapport.json) : seules les vues nouvelles ou changées sont rendues."""
    d = site.dossiers["rendus"]
    d.mkdir(parents=True, exist_ok=True)
    vues_job = []
    for ph, po in zip(sel["photos"], poses):
        cam = CM.cam_depuis(po.get("camera_affinee") or po["camera_initiale"])
        el, az_v = geo.soleil(ph["date"], ph["lon"], ph["lat"])
        az_g = geo.az_vrai_vers_grille(az_v, ph["lon"], ph["lat"])
        vues_job.append({"nom": ph["cle"], "camera": cam.usd(), "soleil_hauteur_deg": el,
                         "soleil_azimut_modele_deg": site.ancrage.lacet(az_g), "sortie_png": str(d / f"rendu_{ph['cle']}.png")})
    # reprise des rendus identiques
    anc_job = CM.lire(d / "travail_rendu.json", {}) or {}
    anc_rr = (CM.lire(site.dos / "rapport.json", {}) or {}).get("rendu") or {}
    anc_res = {v.get("nom"): v for v in anc_rr.get("vues", []) if not v.get("erreur")}
    scene_usda = CM.DEPOT / site.conf["modele"] / "rendus" / "scene_rendu.usda"
    empreinte = {"scene": CM.sha256(scene_usda) if scene_usda.exists() else None,
                 "sous": {n: CM.sha256(scene_usda.parent.parent / n) for n in ("l2/route_l2.usda", "l2b/route_l2b.usda")
                          if (scene_usda.parent.parent / n).exists()}}
    meme_scene = (anc_rr.get("scene_usda_sha256") == empreinte["scene"] and
                  (anc_rr.get("sous_couches_sha256") or {}) == empreinte["sous"] and
                  anc_rr.get("echantillons") == echantillons and anc_job.get("echantillons") == echantillons)
    anc_vues = {v["nom"]: v for v in anc_job.get("vues", [])} if meme_scene else {}
    repris, a_rendre = [], []
    for v in vues_job:
        a = anc_vues.get(v["nom"])
        if a is not None and a == v and Path(v["sortie_png"]).exists() and v["nom"] in anc_res:
            repris.append(anc_res[v["nom"]])
        else:
            a_rendre.append(v)
    if repris:
        journal(f"  rendu : {len(repris)} vues reprises (caméra, soleil et scène identiques), {len(a_rendre)} à rendre")
    rr = lancer_rendu(site, a_rendre, echantillons, limite_s, "rendu_lot") if a_rendre else \
        {"scene_usda": str(scene_usda.relative_to(CM.DEPOT)), "scene_usda_sha256": empreinte["scene"],
         "sous_couches_sha256": empreinte["sous"], "echantillons": echantillons, "vues": []}
    par = {v["nom"]: v for v in repris + rr["vues"]}
    rr["vues"] = [par[v["nom"]] for v in vues_job if v["nom"] in par]
    rr["vues_reprises"] = len(repris)
    CM.ecrire(d / "travail_rendu.json", {"echantillons": echantillons, "vues": vues_job,
                                         "note": "toutes les vues de la sélection (référence de la reprise)"})
    return rr


# ------------------------------------------------------------------------------------------------ planches
def gabarit(site_nom, ph, po, m, st, genre):
    """Grille d'écarts d'une vue (structure de la v1 + zones vues et rubriques du centre si la vue le voit)."""
    g = PL.gabarit_ecarts(site_nom, ph, po, m, st)
    g = {"cle": ph["cle"], **g, "source": ph.get("source", "panoramax"), "lien": ph.get("lien"),
         "zones_vues": ph.get("zones_vues"), "mouvement": ph.get("mouvement")}
    if genre != "section":
        g["profil_modele_vise"] = None
        g["note_profil"] = ("scène de réseau : le profil « visé » de la v1 (première route du sol) serait faux (besoin G6) ;"
                            " voir zones_vues et la description")
        g["grille"]["geometrie"]["nombre_de_voies"]["modele"] = "voir la description (branche vue)"
        g["grille"]["geometrie"]["largeurs_relatives"]["modele"] = "voir la description (branche vue)"
        g["grille"]["geometrie"]["terre_plein"]["modele"] = "voir la description"
        g["grille"]["geometrie"]["bordures"]["modele"] = "voir la description"
        g["grille"]["materiaux"]["modele"] = "voir la description"
    zv = ph.get("zones_vues") or {}
    if any(k.startswith(("centre", "anneau")) and v["part"] >= Z.SEUIL_VOIT for k, v in zv.items()):
        g["grille"]["centre"] = {k: {"modele": "voir centre_zone_conflit (niveau du site)", "constat": None, "detail": None}
                                 for k in RUBRIQUES_CENTRE}
    return g


def planche_vue(site_nom, ph, po, m, P, T, typ, dossiers, ancien, genre):
    """Planche d'une vue (4 panneaux, comme la v1) + vues natives ; renvoie le gabarit d'écarts (et ce que l'agent a
    déjà rempli) et les chemins des vignettes."""
    dossiers = {k: Path(v) for k, v in dossiers.items()}
    cle = ph["cle"]
    vue = Image.open(dossiers["vues"] / po["fichier_vue"]).convert("RGB")
    f_r = dossiers["rendus"] / f"rendu_{cle}.png"
    rendu = Image.open(f_r).convert("RGB") if f_r.exists() else None
    cam0 = CM.cam_depuis(po["camera_initiale"])
    cam1 = CM.cam_depuis(po.get("camera_affinee") or po["camera_initiale"])
    masque = V.masque_porteur(cam0, po["porteur"])
    segs, _ = PO.segments_photo(vue, masque, cam0)
    a = np.asarray(vue).copy()
    for x0, y0, x1, y1, _ in segs:
        cv2.line(a, (int(x0), int(y0)), (int(x1), int(y1)), (0, 230, 255), 1)
    a = PO.dessiner_points(Image.fromarray(a), cam0, P, (255, 220, 0), 1)
    a = PO.dessiner_points(Image.fromarray(a), cam1, P, (40, 255, 90), 1)
    aretes = Image.fromarray(a)
    dp = dossiers["planches"]
    dp.mkdir(parents=True, exist_ok=True)
    aretes.save(dp / f"aretes_{cle}.png")
    vue.save(dp / f"vue_{cle}.png")
    st = None
    if rendu is not None:
        sup, st = PL.superposition(vue, rendu, masque)
        sup.save(dp / f"superposition_{cle}.png")
    else:
        sup = Image.new("RGB", vue.size, (40, 0, 0))
    mi, mf = po["mesures_initiales"], po["mesures_affinees"]
    zv = ph.get("zones_vues") or {}
    zones_txt = ", ".join(f"{k} {v['part']:.2f}" for k, v in sorted(zv.items(), key=lambda x: -x[1]["part"])[:3])
    titre = (f"{site_nom} | {'HORS FENÊTRE D ÉTAT | ' if ph.get('hors_fenetre_etat') else ''}"
             f"{ph.get('source', 'panoramax').capitalize()} {cle} {ph['date'][:10]} © {ph['auteur']} "
             f"({ph['licence']}) | {ph['type']} {ph['porteur']} | vers {ph['vue'].get('cible', '')} | "
             f"recouvr. {mi.get('recouvrement_3px', 0):.2f}→{mf.get('recouvrement_3px', 0):.2f} | "
             f"conf. {po['confiance']['niveau']} | zones {zones_txt}")
    PL.planche_photo(dp / f"planche_{cle}.png", titre,
                     [vue, rendu or Image.new("RGB", vue.size, (40, 0, 0)), sup, aretes],
                     ["photo (vue tirée de la photo, natif 1092 px réduit de moitié)",
                      "rendu Karma depuis la pose affinée", "contours : photo cyan, rendu magenta, communs blanc",
                      "arêtes modèle : initiale jaune, affinée verte ; segments photo cyan"])
    g = gabarit(site_nom, ph, po, m, st, genre)
    if ancien:
        for k in ("grille", "visibilite", "synthese"):
            if ancien.get(k) is not None:
                if k == "grille" and "centre" in g["grille"] and "centre" not in ancien["grille"]:
                    g[k] = dict(ancien[k], centre=g["grille"]["centre"])
                else:
                    g[k] = ancien[k]
    return {"gabarit": g, "vue": str(dp / f"vue_{cle}.png"), "rendu": str(f_r) if f_r.exists() else None,
            "legende": f"{cle} {ph['date'][:10]}{' HF' if ph.get('hors_fenetre_etat') else ''} {ph.get('source', '')[:3]} "
                       f"→ {str(ph['vue'].get('cible', ''))[:22]}"}


def etape_planches(site, sel, poses, processus):
    m = site.modele
    ancien = {e.get("cle"): e for e in (CM.lire(site.dos / "ecarts.json", {}) or {}).get("photos", []) if e.get("cle")}
    vues = [{"ph": ph, "po": po} for ph, po in zip(sel["photos"], poses)]
    base = {"mode": "planches", "modele": str(CM.DEPOT / site.conf["modele"]), "ancrage": site.ancrage.dict(),
            "site": site.nom, "genre": site.genre, "dossiers": {k: str(v) for k, v in site.dossiers.items()},
            "ancien": {k: v for k, v in ancien.items() if k}}
    morceaux = _morceaux(list(range(len(vues))), processus)
    res = _lancer([dict(base, vues=[vues[i] for i in mm]) for mm in morceaux], processus, site.dos / "_travail")
    par = {}
    for mm, r in zip(morceaux, res):
        for i, x in zip(mm, r):
            par[i] = x
    sorties = [par[i] for i in range(len(vues))]
    # synthèses paginées (15 paires par page)
    dp = site.dossiers["planches"]
    pages = []
    for k in range(0, len(sorties), PAIRES_PAR_PAGE):
        lot = sorties[k:k + PAIRES_PAR_PAGE]
        paires = [(Image.open(x["vue"]).convert("RGB"), Image.open(x["rendu"]).convert("RGB") if x["rendu"] else None,
                   x["legende"]) for x in lot]
        f = PL.planche_synthese(dp / f"planche_synthese_{k // PAIRES_PAR_PAGE + 1:02d}.png",
                                f"{site.nom} — vues {k + 1} à {k + len(lot)} sur {len(sorties)} : photo (gauche) | rendu Karma "
                                "(droite) ; photos © auteurs, licences dans selection.json", paires)
        pages.append(f.name)
    plan_poses(site, sel, poses)
    return [x["gabarit"] for x in sorties], pages


# ------------------------------------------------------------------------------------------------ plans (sans photo)
def fond_classes(modele, e_loc, pas, eclaircir=0.0):
    """Plan des faces du modèle colorées par classe (repère du modèle), raster rapide (cv2.fillPoly)."""
    x0, y0, x1, y1 = e_loc
    W, H = int(math.ceil((x1 - x0) / pas)), int(math.ceil((y1 - y0) / pas))
    img = np.full((H, W, 3), 245, np.uint8)
    off = modele._off
    for n in np.unique(modele.C):
        sel = np.nonzero((modele.C == n) & modele.utile)[0]
        if not len(sel):
            continue
        pts = np.stack([modele.P[modele.F[off[sel] + k], :2] for k in range(int(n))], 1)
        px = np.stack([(pts[..., 0] - x0) / pas, (y1 - pts[..., 1]) / pas], -1)
        dedans = (px[..., 0].max(1) >= 0) & (px[..., 0].min(1) < W) & (px[..., 1].max(1) >= 0) & (px[..., 1].min(1) < H)
        cls = modele.classe_face[sel]
        for c in np.unique(cls[dedans]):
            col = MO.COULEURS_CLASSES.get(str(c), (180, 180, 180))
            if str(c).startswith("carrefour_chaussee"):
                col = MO.COULEURS_CLASSES["voie_circulation"]
            elif str(c).startswith(("carrefour_ilot", "giratoire_ilot")):
                col = (110, 160, 90)
            elif str(c).startswith("carrefour_trottoir"):
                col = MO.COULEURS_CLASSES["trottoir"]
            elif str(c).startswith("voie_tourne"):
                col = MO.COULEURS_CLASSES["voie_circulation"]
            if eclaircir:
                col = tuple(int(v + (255 - v) * eclaircir) for v in col)
            q = np.round(px[dedans & (cls == c)] * 4).astype(np.int32)
            cv2.fillPoly(img, list(q), col, lineType=cv2.LINE_8, shift=2)
    return Image.fromarray(img)


def _cadre(e_loc, max_px=1060):
    x0, y0, x1, y1 = e_loc
    pas = max((x1 - x0) / max_px, (y1 - y0) / (max_px - 60), 0.02)
    return pas


def _vers_px(e_loc, pas, haut=60):
    x0, y0, x1, y1 = e_loc

    def f(x, y):
        return ((x - x0) / pas, haut + (y1 - y) / pas)
    return f


def _rose(d, cx, cy, r, secteurs_n, couleur):
    """Rose de 8 secteurs (N en haut) : secteur rempli si couvert (intensité selon le nombre de vues)."""
    for k in range(8):
        n = secteurs_n[k]
        a0, a1 = k * 45 - 22.5 - 90, k * 45 + 22.5 - 90        # PIL : angle 0 = est, sens horaire
        if n > 0:
            f = min(1.0, 0.35 + 0.2 * n)
            col = tuple(int(255 - (255 - c) * f) for c in couleur)
            d.pieslice((cx - r, cy - r, cx + r, cy + r), a0, a1, fill=col, outline=(60, 60, 60))
        else:
            d.pieslice((cx - r, cy - r, cx + r, cy + r), a0, a1, fill=(255, 255, 255), outline=(170, 170, 170))


def dessiner_couverture(site, sel, cv):
    """Carte de couverture (site entier et zoom sur le cœur) : zones, nombre de vues qui voient chaque zone, rose
    des directions d'observation, zones aveugles en rouge, positions des photos (Panoramax bleu, Mapillary orange)."""
    zones = site.zones
    bil = {b["zone"]: b for b in cv["apres_v2"]["zones"]}
    avant = {b["zone"]: b for b in (cv.get("avant_v1") or {}).get("zones", [])}
    secteurs = {z.id: [0] * 8 for z in zones}
    for b in cv["apres_v2"]["zones"]:
        for v in b["vues"]:
            secteurs[b["zone"]][Z.SECTEURS.index(v["secteur"])] += 1
    emp = DS.emprises(zones)
    sorties = []
    for nom, e in (("plan_couverture", emp["site"]), ("plan_couverture_centre", emp.get("centre"))):
        if e is None:
            continue
        if nom == "plan_couverture":
            xs = [p["position_modele"]["s"] for p in sel["photos"]]
            ys = [p["position_modele"]["t"] for p in sel["photos"]]
            e = (min([e[0]] + xs) - 4, min([e[1]] + ys) - 4, max([e[2]] + xs) + 4, max([e[3]] + ys) + 4)
        pas = _cadre(e)
        fond = fond_classes(site.modele, e, pas, eclaircir=0.45)
        W, H = fond.size
        im = Image.new("RGB", (W, H + 60), (250, 250, 247))
        im.paste(fond, (0, 60))
        d = ImageDraw.Draw(im, "RGBA")
        px = _vers_px(e, pas)
        zoom = nom.endswith("centre")
        for z in zones:
            if zoom and z.type in ("approche",):
                continue
            col = Z.COULEURS[z.type]
            b = bil.get(z.id, {})
            geoms = getattr(z.poly, "geoms", [z.poly])
            for g in geoms:
                pts = [px(*c) for c in g.exterior.coords]
                if b.get("aveugle"):
                    d.polygon(pts, fill=(255, 0, 0, 90), outline=(200, 0, 0, 255))
                else:
                    d.polygon(pts, fill=col + (40,), outline=col + (255,))
        for p in sel["photos"]:
            if p["vue"].get("rang_dans_la_photo", 1) != 1 and not zoom:
                pass
            x, y = px(p["position_modele"]["s"], p["position_modele"]["t"])
            col = COUL_SOURCE.get(p.get("source", "panoramax"))
            a = math.radians(p["vue"]["lacet_modele_deg"])
            L = 22 if zoom else 14
            d.line((x, y, x + L * math.cos(a), y - L * math.sin(a)), fill=col + (200,), width=1)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col + (255,), outline=(0, 0, 0, 255))
        for z in zones:
            if zoom and z.type == "approche":
                continue
            b = bil.get(z.id, {})
            cx, cy = px(*z.centre)
            r = 15 if zoom else 11
            _rose(d, cx, cy, r, secteurs[z.id], (200, 30, 30) if z.type in ("centre", "anneau") else (40, 40, 160))
            t1 = f"{z.id} : {b.get('n_vues', 0)} vues / {b.get('n_photos', 0)} ph."
            if z.id in avant:
                t1 += f" (v1 : {avant[z.id]['n_vues']})"
            d.text((cx + r + 3, cy - 8), t1, fill=(0, 0, 0, 255), font=PL.police(12 if zoom else 11),
                   stroke_width=2, stroke_fill=(255, 255, 255, 255))
        st = sel["statistiques"]
        avg = [b["zone"] for b in cv["apres_v2"]["zones"] if b["aveugle"]]
        d.text((6, 4), f"{site.nom} — couverture des zones d'intérêt : {st['photos']} photos ({st['photos_panoramax']} Panoramax, "
                       f"{st['photos_mapillary']} Mapillary), {st['vues']} vues ; 1 px = {pas:.3f} m ; nord en haut",
               fill=(0, 0, 0), font=PL.police(13))
        d.text((6, 22), "rose : directions d'observation (8 secteurs, N en haut ; plein = vu, foncé = plusieurs vues) ; "
                        "« n vues / n ph. » : vues voyant ≥ 20 % de la zone (v1 entre parenthèses)",
               fill=(40, 40, 40), font=PL.police(12))
        d.text((6, 40), "points : position des photos (bleu Panoramax, orange Mapillary), trait = visée de chaque vue ; "
                        f"zones aveugles en rouge : {', '.join(avg) if avg else 'aucune'}", fill=(40, 40, 40), font=PL.police(12))
        f = site.dos / f"{nom}.png"
        if im.size[0] * im.size[1] > 1092 * 1092 or max(im.size) > 1568:
            k = min(math.sqrt(1092 * 1092 / (im.size[0] * im.size[1])), 1568 / max(im.size))
            im = im.resize((int(im.size[0] * k), int(im.size[1] * k)), Image.LANCZOS)
        im.save(f)
        sorties.append(f.name)
    return sorties


def plan_poses(site, sel, poses):
    """Plan des poses (sans photo) : position GNSS (cercle) et retenue (disque) de chaque photo, visée de chaque vue
    colorée par source, identifiant court une fois par photo."""
    zones = site.zones
    emp = DS.emprises(zones)["site"]
    xs = [p["camera_initiale"]["C_modele"][0] for p in poses]
    ys = [p["camera_initiale"]["C_modele"][1] for p in poses]
    e = (min([emp[0]] + xs) - 4, min([emp[1]] + ys) - 4, max([emp[2]] + xs) + 4, max([emp[3]] + ys) + 4)
    pas = _cadre(e)
    fond = fond_classes(site.modele, e, pas, eclaircir=0.3)
    W, H = fond.size
    im = Image.new("RGB", (W, H + 60), (250, 250, 247))
    im.paste(fond, (0, 60))
    d = ImageDraw.Draw(im, "RGBA")
    px = _vers_px(e, pas)
    vus = set()
    for ph, po in zip(sel["photos"], poses):
        col = COUL_SOURCE.get(ph.get("source", "panoramax"))
        ci, cf = po["camera_initiale"], po.get("camera_affinee") or po["camera_initiale"]
        xi, yi = px(*ci["C_modele"][:2])
        x, y = px(*cf["C_modele"][:2])
        d.line((xi, yi, x, y), fill=(0, 0, 0, 255), width=1)
        for s in (-1, 1):
            a = math.radians(cf["lacet_deg"] + s * cf["champ_h_deg"] / 2)
            d.line((x, y, x + 12 * math.cos(a), y - 12 * math.sin(a)), fill=col + (150,), width=1)
        a = math.radians(cf["lacet_deg"])
        d.line((x, y, x + 18 * math.cos(a), y - 18 * math.sin(a)), fill=col + (255,), width=2)
        d.ellipse((xi - 3, yi - 3, xi + 3, yi + 3), outline=col + (255,), width=1)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=col + (255,))
        if ph["id"] not in vus:
            vus.add(ph["id"])
            d.text((x + 4, y + 2), ph["id8"], fill=(0, 0, 0, 255), font=PL.police(10), stroke_width=2,
                   stroke_fill=(255, 255, 255, 255))
    d.text((6, 4), f"{site.nom} : poses des {len(poses)} vues ({len(vus)} photos) ; 1 px = {pas:.3f} m ; nord en haut",
           fill=(0, 0, 0), font=PL.police(13))
    d.text((6, 22), "cercle : position GNSS ; disque : position retenue ; traits : visée et champ de chaque vue "
                    "(bleu Panoramax, orange Mapillary)", fill=(40, 40, 40), font=PL.police(12))
    if im.size[0] * im.size[1] > 1092 * 1092 or max(im.size) > 1568:
        k = min(math.sqrt(1092 * 1092 / (im.size[0] * im.size[1])), 1568 / max(im.size))
        im = im.resize((int(im.size[0] * k), int(im.size[1] * k)), Image.LANCZOS)
    im.save(site.dos / "plan_site.png")


# ------------------------------------------------------------------------------------------------ vue de dessus
def etape_dessus(site, echantillons, limite_s):
    """Rendus de dessus (site, centre), orthos, contours, planches en tuiles ; dessus/dessus.json."""
    dd = site.dossiers["dessus"]
    dd.mkdir(parents=True, exist_ok=True)
    org = site.ancrage.dict()["origine_l93"]
    if abs(site.ancrage.alpha - 90.0) > 1e-6:
        journal("  dessus : repère du modèle tourné par rapport au Lambert-93 (tronçon) : orthos non superposables, "
                "étape sautée")
        return None
    emp = DS.emprises(site.zones)
    cache_o = CM.SORTIE / "_orthos"
    plans = []
    for nom, e in emp.items():
        e_l93 = (e[0] + org[0], e[1] + org[1], e[2] + org[0], e[3] + org[1])
        orthos = []
        o = DS.ortho_pcrs(e_l93)
        if o:
            orthos.append(o)
        try:
            orthos.append(DS.ortho_ign(e_l93, cache_o))
        except Exception as ex:  # service indisponible
            journal(f"  dessus {nom} : ortho IGN indisponible ({str(ex)[:120]})")
        if not orthos:
            continue
        # 5 cm avec le PCRS ; 10 cm sinon (centre : l'ortho IGN de 20 cm agrandie ×4 n'apporte rien et multiplie les
        # tuiles), 10 cm aussi pour le site
        pas_rendu = 0.05 if orthos[0]["nom"] == "pcrs2022" else 0.10
        plans.append({"nom": nom, "emprise_locale": e, "emprise_l93": e_l93, "pas_rendu": pas_rendu, "orthos": orthos})
    if not plans:
        return None
    # rendus de dessus (Karma, quasi orthographique), soleil à la date de l'ortho principale, 10 h 30 UTC
    vues_job = []
    for p in plans:
        x0, y0, x1, y1 = p["emprise_locale"]
        W, H = int(round((x1 - x0) / p["pas_rendu"])), int(round((y1 - y0) / p["pas_rendu"]))
        z = float(np.median(site.modele.centres[site.modele.utile, 2]))
        date = (p["orthos"][0].get("date") or "2024-08-09") + "T10:30:00+00:00"
        lon, lat = geo.wgs((p["emprise_l93"][0] + p["emprise_l93"][2]) / 2, (p["emprise_l93"][1] + p["emprise_l93"][3]) / 2)
        el, az_v = geo.soleil(date, lon, lat)
        az_g = geo.az_vrai_vers_grille(az_v, lon, lat)
        p["soleil"] = {"date": date, "hauteur_deg": round(el, 2), "azimut_vrai_deg": round(az_v, 2)}
        vues_job.append({"nom": f"dessus_{p['nom']}", "camera": DS.camera_dessus((x0 + x1) / 2, (y0 + y1) / 2, z, x1 - x0, W, H),
                         "soleil_hauteur_deg": el, "soleil_azimut_modele_deg": site.ancrage.lacet(az_g),
                         "sortie_png": str(dd / f"rendu_dessus_{p['nom']}.png")})
    t0 = time.time()
    rr = lancer_rendu(site, vues_job, echantillons, max(limite_s, 600), "rendu_dessus")
    journal(f"  dessus : {len(vues_job)} rendus de dessus ({time.time() - t0:.0f} s)")
    man = {"schema": "comparaison_dessus/0.1", "site": site.nom, "origine_l93": org,
           "note": "images diffusables (rendu du modèle, orthos sous licence ouverte) ; tuiles de 740 px, recouvrement 20 %",
           "rendu": rr, "emprises": []}
    for p in plans:
        rendu = Image.open(dd / f"rendu_dessus_{p['nom']}.png").convert("RGB")
        x0, y0, x1, y1 = p["emprise_locale"]
        ent = {"nom": p["nom"], "emprise_locale": list(p["emprise_locale"]), "emprise_l93": [round(v, 2) for v in p["emprise_l93"]],
               "pas_rendu_m": p["pas_rendu"], "soleil_rendu": p["soleil"], "orthos": []}
        for o in p["orthos"]:
            pas = min(o["pas"], p["pas_rendu"]) if p["nom"] == "centre" else o["pas"]
            W, H = int(round((x1 - x0) / pas)), int(round((y1 - y0) / pas))
            r_img = rendu.resize((W, H), Image.LANCZOS) if rendu.size != (W, H) else rendu
            o_img = o["image"].resize((W, H), Image.BICUBIC) if o["image"].size != (W, H) else o["image"]
            agrandie = o["image"].size[0] < W
            ct = DS.dessiner_contours(o_img, site.modele, p["emprise_locale"], pas, epaisseur=1 if pas <= 0.06 else 1)
            tag = f"{p['nom']}_{o['nom']}"
            for f_anc in list(dd.glob(f"planche_dessus_{tag}_t*.png")) + list(dd.glob(f"contours_{tag}_t*.png")):
                f_anc.unlink()                     # tuiles d'un passage précédent (le découpage peut changer)
            r_img.save(dd / f"rendu_{tag}.png")
            o_img.save(dd / f"ortho_{tag}.png")
            ct.save(dd / f"contours_{tag}.png")
            titre = (f"{site.nom} — {p['nom']} — {o['libelle']}" + (f" (agrandie de {o['pas'] * 100:.0f} à {pas * 100:.0f} cm/px)"
                                                                    if agrandie else ""))
            tu = DS.planches_tuiles(dd, tag, r_img, o_img, ct, p["emprise_locale"], pas, org, titre)
            DS.apercu(dd / f"apercu_{tag}.png", r_img, o_img, titre)
            ent["orthos"].append({"nom": o["nom"], "libelle": o["libelle"], "date": o.get("date"), "licence": o["licence"],
                                  "source": o["source"], "pas_m": pas, "pas_natif_m": o["pas"], "agrandie": agrandie,
                                  "taille_px": [W, H], "images": {"rendu": f"rendu_{tag}.png", "ortho": f"ortho_{tag}.png",
                                                                  "contours": f"contours_{tag}.png",
                                                                  "apercu": f"apercu_{tag}.png"},
                                  "tuiles": tu})
        man["emprises"].append(ent)
    CM.ecrire(dd / "dessus.json", man)
    return man


# ------------------------------------------------------------------------------------------------ grille du centre
RUBRIQUES_CENTRE = ("ilots", "guidage", "traversees_cyclables", "paves", "zebras", "passages", "refuges", "autres_marquages")


def _peinture_dans(dossier_modele, poly):
    """Aire (m²) et nombre d'entités des marquages l2b par classe dont le centre de face est dans le polygone."""
    import shapely
    d = Path(dossier_modele) / "l2b"
    if not (d / "peinture_points.npy").exists():
        return {}
    voc = json.loads((d / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
    PP, FF, CC, AA = (np.load(d / f"peinture_{n}.npy") for n in ("points", "faces", "comptes", "attributs"))
    off = np.concatenate([[0], np.cumsum(CC)[:-1]])
    ic, ie = voc["colonnes"].index("classe"), voc["colonnes"].index("pj_entite")
    out = {}
    for n in np.unique(CC):
        sel = np.nonzero(CC == n)[0]
        pts = np.stack([PP[FF[off[sel] + k], :2] for k in range(int(n))], 1)
        c = pts.mean(1)
        x, y = pts[..., 0], pts[..., 1]
        aire = 0.5 * np.abs((x * np.roll(y, -1, 1) - np.roll(x, -1, 1) * y).sum(1))
        dedans = shapely.contains_xy(poly, c[:, 0], c[:, 1])
        for cl, a_, e_ in zip(AA[sel[dedans], ic], aire[dedans], AA[sel[dedans], ie]):
            k = voc["classe"][cl]
            o = out.setdefault(k, {"aire_m2": 0.0, "entites": set()})
            o["aire_m2"] += float(a_)
            o["entites"].add(int(e_))
    return {k: {"aire_m2": round(v["aire_m2"], 1), "entites": len(v["entites"])} for k, v in out.items()}


def bloc_centre(site, sel, ancien, dessus_man):
    """Section « centre / zone de conflit » de la grille d'écarts (niveau du site) : ce que dit le modèle (rempli
    automatiquement) et rubriques à remplir d'après la vue de dessus et les vues du centre."""
    from shapely.ops import unary_union
    zones = site.zones
    noyau = [z for z in zones if z.type in ("centre", "anneau", "ilot_central")]
    if not noyau:
        return None
    u = unary_union([z.poly for z in noyau])
    voisins = [z for z in zones if z.type in ("ilot", "passage") and z.poly.distance(u) <= 15.0]
    zone_c = unary_union([u] + [z.poly for z in voisins]).buffer(1.0)
    dm = CM.DEPOT / site.conf["modele"]
    mv = CM.lire(dm / "modele_voie.json", {}) or {}
    peint = _peinture_dans(dm, zone_c)
    gu = CM.lire(dm / "l4" / "guidage.json", {}) or {}
    # matériaux du sol dans la zone
    m = site.modele
    import shapely
    c = m.centres[m.utile]
    dedans = shapely.contains_xy(zone_c, c[:, 0], c[:, 1])
    mats = {}
    for mat in np.unique(m.mat_face[m.utile][dedans]):
        mats[str(mat)] = int((m.mat_face[m.utile][dedans] == mat).sum())
    ilots = [z for z in zones if z.type in ("ilot", "ilot_central") and z.poly.distance(u) <= 15.0]
    passages = [z for z in voisins if z.type == "passage"]
    trav_cycl = [mk for mk in mv.get("marquages", []) if "cycl" in str(mk.get("type", ""))]
    modele_dit = {
        "ilots": [f"{z.id} : {z.meta.get('type', z.type)}, {z.meta.get('remplissage') or ''}, "
                  f"{'franchissable ' + str(z.meta.get('franchissable')) if z.meta.get('franchissable') else ''}, "
                  f"{z.poly.area:.0f} m²" for z in ilots] or "aucun îlot dans le cœur",
        "guidage": (f"{len(gu.get('lignes', []))} ligne(s) de guidage (l4/guidage.json) ; marquages « ligne » dans la "
                    f"zone : {peint.get('ligne', {}).get('entites', 0)} entités, {peint.get('ligne', {}).get('aire_m2', 0)} m²"),
        "traversees_cyclables": ([f"{mk['id']} ({mk['type']})" for mk in trav_cycl] or
                                 "aucune : pas de mot pour une traversée cyclable peinte ou à pavés dans le format (besoins A2 / G4)"),
        "paves": ({k: v for k, v in mats.items() if "pave" in k} or "aucun pavé (matériaux du sol de la zone : "
                  + ", ".join(sorted(mats)) + ")"),
        "zebras": (f"hachures : {peint['hachure']['aire_m2']} m² ({peint['hachure']['entites']} entités)"
                   if "hachure" in peint else "aucune zone hachurée dans le cœur"),
        "passages": [f"{z.id} : {z.nom}, {z.poly.area:.0f} m²" for z in passages] or "aucun passage à moins de 15 m du cœur",
        "refuges": [z.id for z in ilots if z.meta.get("refuge")] or "aucun refuge",
        "autres_marquages": {k: v for k, v in peint.items() if k not in ("hachure", "ligne")} or "aucun",
    }
    if site.genre == "giratoire":
        an = next((cc.get("anneau") for cc in mv.get("carrefours", []) if cc.get("anneau")), {}) or {}
        modele_dit["anneau_couronne"] = (f"anneau {an.get('largeur_anneau_m')} m, rayon extérieur {an.get('rayon_exterieur_m')} m, "
                                         f"îlot central {an.get('rayon_ilot_central_m')} m, bande franchissable "
                                         f"{an.get('bande_franchissable_m')} m")
    rub = {k: {"modele": v, "constat": None, "detail": None} for k, v in modele_dit.items()}
    vues_c = []
    for ph in sel["photos"]:
        zv = ph.get("zones_vues") or {}
        p = max([v["part"] for k, v in zv.items() if any(k == z.id for z in noyau)] or [0.0])
        if p >= Z.SEUIL_VOIT:
            vues_c.append((p, ph["cle"]))
    tuiles_c = []
    for e in (dessus_man or {}).get("emprises", []):
        if e["nom"] == "centre":
            for o in e["orthos"]:
                tuiles_c += [t["planche"] for t in o["tuiles"]] + [t["contours"] for t in o["tuiles"]]
    orthos_c = []
    kit_man = CM.lire(site.dos / "orthos" / "kit.json") or {}
    for e in kit_man.get("emprises", []):
        if e["nom"] == "centre":
            orthos_c = [f"orthos/{c['image']} ({c['date']})" for c in e["couches"]] + \
                       [f"orthos/{p}" for p in e.get("planches_dates", [])]
    bloc = {"zones": [z.id for z in noyau] + [z.id for z in voisins],
            "consigne": ("constat par rubrique : conforme | différent | absent | en trop | non visible ; detail : ce qui est "
                         "vu, sur quelle image : zoom du centre des orthos datées (orthos/centre_<couche>.png), tuile de "
                         "dessus (dessus/planche_dessus_centre_*.png, contours_centre_*.png) ou vue du centre "
                         "(photos_non_versionnees/v2/vues/vue_<cle>.png, planches/planche_<cle>.png) ; ordre de lecture : "
                         "comprehension/LISEZMOI.md"),
            "sources": {"orthos_centre": orthos_c, "tuiles_dessus_centre": tuiles_c,
                        "vues_du_centre": [c for _, c in sorted(vues_c, key=lambda x: (-x[0], x[1]))]},
            "rubriques": rub, "elements_manquants": [], "elements_en_trop": [], "synthese": None}
    if ancien:
        for k in ("elements_manquants", "elements_en_trop", "synthese"):
            if ancien.get(k):
                bloc[k] = ancien[k]
        for k, r in (ancien.get("rubriques") or {}).items():
            if k in bloc["rubriques"]:
                for kk in ("constat", "detail"):
                    if r.get(kk) is not None:
                        bloc["rubriques"][k][kk] = r[kk]
    return bloc


# ------------------------------------------------------------------------------------------------ pilote v2
def traiter(nom, conf, etapes, args):
    t_site = time.time()
    site = SiteV2(nom, conf)
    durees = {}
    journal(f"== {nom} (v2, {site.genre}, {len(site.zones)} zones) : ancrage {site.ancrage.dict()}")
    rapport = CM.lire(site.dos / "rapport.json", {}) or {}
    if rapport.get("version") != 2:
        rapport = {}
    t0 = time.time()
    if "selection" in etapes:
        sel = etape_selection(site, conf, args)
        durees["selection_s"] = round(time.time() - t0, 1)
        st = sel["statistiques"]
        journal(f"  sélection : {st['photos']} photos ({st['photos_panoramax']} Panoramax, {st['photos_mapillary']} "
                f"Mapillary), {st['vues']} vues, {st['photos_dans_le_coeur']} dans le cœur ; zones aveugles "
                f"{st['zones_aveugles']} ({durees['selection_s']} s)")
    sel = CM.lire(site.dos / "selection.json")
    if sel is None or sel.get("version") != 2:
        raise RuntimeError("selection.json v2 absent : lancer l'étape selection")
    t0 = time.time()
    kit_man = CM.lire(site.dos / "orthos" / "kit.json")
    if "orthos" in etapes:
        journal("  kit multi-orthos (même emprise, même cadrage, plusieurs dates) :")
        kit_man = OR.kit(nom, site.zones, site.ancrage, site.dos / "orthos", CM.SORTIE / "_orthos",
                         couches=getattr(args, "couches_orthos", None), journal=journal)
        durees["orthos_s"] = round(time.time() - t0, 1)
        journal(f"  orthos : {sum(len(e['couches']) for e in kit_man['emprises'])} extraits, "
                f"{len(kit_man['couches_absentes'])} couches absentes ({durees['orthos_s']} s)")
    t0 = time.time()
    if "pose" in etapes:
        poses, diag = etape_pose(site, sel, args.processus)
        CM.ecrire(site.dos / "poses.json", {"schema": "comparaison_poses/0.2", "site": nom, "version": 2,
                                            "ancrage": site.ancrage.dict(),
                                            "garde_fous": PO.BORNES | {"deplacement_m": PO.DEPLACEMENT_MAX},
                                            "correction_mediane_du_site": diag, "poses": poses})
        durees["pose_s"] = round(time.time() - t0, 1)
        journal(f"  poses : {len(poses)} vues ({durees['pose_s']} s)")
    pdoc = CM.lire(site.dos / "poses.json")
    poses = pdoc["poses"] if pdoc and pdoc.get("version") == 2 else None
    if poses is not None and [p.get("cle") or p["id8"] for p in poses] != [p["cle"] for p in sel["photos"]]:
        if any(e in etapes for e in ("rendu", "planches")):
            raise RuntimeError("poses.json ne correspond pas à selection.json : relancer l'étape pose")
        journal("  poses.json ne correspond plus à selection.json : relancer les étapes pose, rendu, planches")
        poses = None
    t0 = time.time()
    if "rendu" in etapes and poses:
        rr = etape_rendu(site, sel, poses, args.echantillons, args.limite)
        rapport["rendu"] = rr
        durees["rendu_s"] = round(time.time() - t0, 1)
        err = [v for v in rr["vues"] if v.get("erreur")]
        journal(f"  rendu : {len(rr['vues']) - len(err)} vues rendues, {len(err)} erreurs ({durees['rendu_s']} s)")
    t0 = time.time()
    man = CM.lire(site.dossiers["dessus"] / "dessus.json")
    if "dessus" in etapes:
        man = etape_dessus(site, args.echantillons, args.limite)
        durees["dessus_s"] = round(time.time() - t0, 1)
    t0 = time.time()
    if "planches" in etapes and poses:
        ecarts, pages = etape_planches(site, sel, poses, args.processus)
        anc = CM.lire(site.dos / "ecarts.json", {}) or {}
        centre = bloc_centre(site, sel, anc.get("centre_zone_conflit") if anc.get("version") == 2 else None, man)
        CM.ecrire(site.dos / "ecarts.json", {
            "schema": "comparaison_ecarts/0.2", "version": 2, "site": nom, "description": conf["description"],
            "modele": conf["modele"],
            "consigne": "constat par rubrique : conforme | différent | absent | en trop | non visible ; detail : ce qui est "
                        "vu, sur quelle planche ou vue native (photos_non_versionnees/v2/planches/{planche,vue,superposition,"
                        "aretes}_<cle>.png, rendus_v2/rendu_<cle>.png) ; centre_zone_conflit : d'après la vue de dessus "
                        "(dessus/) et les vues du centre",
            "correction_mediane_du_site": (pdoc or {}).get("correction_mediane_du_site"),
            "centre_zone_conflit": centre, "planches_synthese": pages, "photos": ecarts})
        durees["planches_s"] = round(time.time() - t0, 1)
    # rapport
    cv = CM.lire(site.dos / "couverture.json", {}) or {}
    t0 = time.time()
    if "dossier" in etapes:
        idx = DO.ecrire(site, sel, poses, kit_man, man, cv)
        durees["dossier_s"] = round(time.time() - t0, 1)
        journal(f"  dossier de compréhension : {idx['photos']} photos, {idx['n_vues']} vues dont "
                f"{len(idx['vues_du_centre'])} du centre ; comprehension/LISEZMOI.md ({durees['dossier_s']} s)")

    def resume_coeur(bloc):
        if not bloc:
            return None
        zz = [b for b in bloc["zones"] if b["type"] in ("centre", "anneau", "ilot_central")]
        return {b["zone"]: {"vues": b["n_vues"], "photos": b["n_photos"], "secteurs": b["n_secteurs"],
                            "part_max": b["part_max"]} for b in zz}
    st = sel["statistiques"]
    rapport.update({"version": 2, "site": nom, "genre": site.genre, "ancrage": site.ancrage.dict(),
                    "photos": st["photos"], "photos_panoramax": st["photos_panoramax"],
                    "photos_mapillary": st["photos_mapillary"], "vues": st["vues"],
                    "photos_dans_le_coeur": st["photos_dans_le_coeur"], "sequences": st["sequences"], "dates": st["dates"],
                    "quadrants": st["quadrants"], "positions": st["positions"],
                    "zones_aveugles": st["zones_aveugles"], "mouvements_disponibles": st["mouvements_disponibles"],
                    "mouvements_couverts": st["mouvements_couverts"],
                    "fenetre_etat": [sel["criteres"].get("depuis"), sel["criteres"].get("jusqu_au")],
                    "complement_depuis": sel["criteres"].get("complement_depuis"),
                    "photos_hors_fenetre_etat": st.get("photos_hors_fenetre_etat", 0),
                    "vues_hors_fenetre_etat": st.get("vues_hors_fenetre_etat", 0),
                    "orthos": None if not kit_man else {e["nom"]: [f"{c['nom']} {c['date']}" for c in e["couches"]]
                                                        for e in kit_man.get("emprises", [])},
                    "couverture_coeur": {"avant_v1": resume_coeur(cv.get("avant_v1")), "apres_v2": resume_coeur(cv.get("apres_v2"))}})
    if poses:
        aff = [p for p in poses if str(p.get("statut", "")).startswith("affinée")]
        rapport.update({
            "poses_affinees": len(aff), "confiance": {k: sum(1 for p in poses if p["confiance"]["niveau"] == k)
                                                      for k in ("haute", "moyenne", "faible")},
            "recouvrement_3px_median": [round(float(np.median([p["mesures_initiales"].get("recouvrement_3px", 0) for p in poses])), 4),
                                        round(float(np.median([p["mesures_affinees"].get("recouvrement_3px", 0) for p in poses])), 4)],
            "ecart_moyen_px_median": [round(float(np.median([p["mesures_initiales"].get("ecart_moyen_px", 0) for p in poses])), 3),
                                      round(float(np.median([p["mesures_affinees"].get("ecart_moyen_px", 0) for p in poses])), 3)],
            "correction_mediane_du_site": (pdoc or {}).get("correction_mediane_du_site")})
    rapport.setdefault("durees", {}).update(durees)
    rapport["durees"]["total_derniere_execution_s"] = round(time.time() - t_site, 1)
    CM.ecrire(site.dos / "rapport.json", rapport)
    journal(f"  {nom} : {rapport['durees']}")
    return rapport
