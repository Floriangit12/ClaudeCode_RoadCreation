"""Comparaison multivues d'un tronçon fabriqué par le générateur avec des photos Panoramax (sous plusieurs angles et
depuis plusieurs positions) : choix des photos, pose affinée, rendu Karma depuis la même pose, planches, grille
d'écarts. Voir README.md.

    python recon/generateur/comparaison/comparer_multivues.py S_M20 S_M24 S_M27
           [--etapes selection,pose,rendu,planches] [--rafraichir] [--depuis 2019-01-01] [--echantillons 128]
           [--sites-conf recon/generateur/comparaison/sites_meylan.json]
    v2 (dossier de compréhension à LIRE PAR LE MODÈLE : kit multi-orthos datées, sélection guidée par la couverture
    des zones d'intérêt, 40 à 60 photos pour un carrefour ou un giratoire, plusieurs vues par photo 360°, Mapillary en
    complément, vue de dessus rendu | ortho, carte de couverture, index des vues, grille du centre ; etapes_v2.py) :
    python recon/generateur/comparaison/comparer_multivues.py meylan_paquet_jardin --v2
           --sites-conf recon/generateur/meylan/paquet_jardin/comparaison_site.json
           [--sortie recon/out/generateur/meylan_paquet_jardin/comparaison] [--depuis 2024-08-24] [--jusqu-au 2025-06-22]
           [--complement-depuis 2019-01-01 | non] [--etapes selection,orthos,pose,rendu,dessus,planches,dossier]
           [--processus 4] [--sans-mapillary] [--couches-orthos pcrs2022,ign2024,...]

Entrées (lecture seule) : recon/out/generateur/<scène>/ (modèle fabriqué, l2, l2b, rendus/scene_rendu.usda), la
configuration des sites (ancrage), OSM local (data/vector_gz/osm), API publique Panoramax.
Sorties : recon/out/generateur/comparaison/<scène>/ (non versionné) :
  selection.json, poses.json, ecarts.json, rapport.json, plan_site.png, rendus/rendu_<id8>.png, cache/ (réponses de
  l'API), photos_non_versionnees/{brut, vues, planches, tuiles}/ (photos de tiers et planches qui en contiennent).
Python système (numpy, scipy, OpenCV, pyproj, shapely, Pillow) ; le rendu passe par hython (rendu_hython.py).
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import api_panoramax as AP  # noqa: E402
import geo  # noqa: E402
import modele as MO  # noqa: E402
import planches as PL  # noqa: E402
import pose as PO  # noqa: E402
import selection as SE  # noqa: E402
import vues as V  # noqa: E402

DEPOT = ICI.parents[2]
SORTIE = DEPOT / "recon" / "out" / "generateur" / "comparaison"
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
ETAPES = ("selection", "pose", "rendu", "planches")
ETAPES_V2 = ("selection", "orthos", "pose", "rendu", "dessus", "planches", "dossier")
SEUIL_VALIDATION = 0.03       # amélioration relative minimale du score sur les segments de validation


def journal(*a):
    print(*a, flush=True)


def ecrire(f, d):
    Path(f).parent.mkdir(parents=True, exist_ok=True)
    Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def lire(f, defaut=None):
    f = Path(f)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else defaut


def sha256(f):
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Site:
    def __init__(self, nom, conf):
        self.nom = nom
        self.conf = conf
        self.dos = SORTIE / nom
        self.pnv = self.dos / "photos_non_versionnees"
        self.dossiers = {"cache": self.dos / "cache", "brut": self.pnv / "brut", "vues": self.pnv / "vues",
                         "planches": self.pnv / "planches", "tuiles": self.pnv / "tuiles", "rendus": self.dos / "rendus"}
        self.modele = MO.Modele(DEPOT / conf["modele"])
        ids = [r["id"] for r in conf["ancrage"].get("photos_reference", [])]
        refs = AP.par_identifiants(ids, self.dossiers["cache"] / "photos_reference.json") if ids else {}
        self.refs = {i: {"lon": r["lon"], "lat": r["lat"], "azimut_vrai": float(r["proprietes"].get("view:azimuth") or 0)}
                     for i, r in refs.items()}
        self.ancrage, self.diag_ancrage = geo.calculer_ancrage(conf, self.modele.s_max, self.refs)
        pi = conf.get("point_interet") or {"s": (self.modele.s_min + self.modele.s_max) / 2, "t": 0.0}
        self.poi = (float(pi["s"]), float(pi["t"]))


# ------------------------------------------------------------------------------------------------ étape pose
def cam_depuis(d):
    return V.Camera(d["W"], d["H"], d["champ_h_deg"], np.array(d["C_modele"], dtype=np.float64), d["lacet_deg"],
                    d["tangage_deg"], d["roulis_deg"])


def poser_vue(ph, jpg, r_vert, coh, m, A, P, T, typ, dossier_vues, cle=None):
    """Pose d'une vue (redressement par les verticales, affinage validé, mesures) : enregistrement de poses.json.
    r_vert : résultat de vues.verticale_360 de la photo (360°) ou None ; coh : cohérence de séquence de la photo ;
    cle : nom des fichiers de la vue (v1 : id8 ; v2 : id8 + lacet de la vue)."""
    t0 = time.time()
    cle = cle or ph["id8"]
    est360 = ph["type"] == "360"
    img, (W, H, fov) = V.extraire_vue(jpg, est360, ph["vue"]["lacet_image_deg"], ph["vue"]["tangage_deg"],
                                      None if est360 else ph["vue"]["champ_deg"], mly=ph.get("mly"))
    vue_png = Path(dossier_vues) / f"vue_{cle}.png"
    vue_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(vue_png)
    x, y = ph["l93"]
    s, t = (float(v) for v in A.vers_modele(x, y))
    por = ph["porteur"]
    z = m.z_sol(s, t)
    az_v = ph["cap_vrai_deg"] + ph["vue"]["lacet_image_deg"]
    az_g = geo.az_vrai_vers_grille(az_v, ph["lon"], ph["lat"])
    cam0 = V.Camera(W, H, fov, np.array([s, t, z + V.PORTEURS[por]["h"]]), A.lacet(az_g), ph["vue"]["tangage_deg"], 0.0)
    masque = V.masque_porteur(cam0, por)
    sig = float(ph.get("precision_m") or 4.0)
    # redressement par les verticales (photos 360° : la caméra portée ou fixée de travers n'est pas de niveau)
    cam_dep, redr = cam0, None
    r = r_vert
    if est360 and r is not None:
        u, n_seg, res_deg = r
        incl = math.degrees(math.acos(min(1.0, float(u[2]))))
        lac_c = A.lacet(geo.az_vrai_vers_grille(ph["cap_vrai_deg"], ph["lon"], ph["lat"]))
        lac, tg, rl = V.orientation_redressee(lac_c, u, ph["vue"]["lacet_image_deg"], ph["vue"]["tangage_deg"])
        # appliqué seulement si : inclinaison ≥ 3° (en deçà, l'imprécision du redressement, résidu 0,5 à 1° soit 7 à
        # 14 px dans la vue, dépasse ce qu'il corrige), ≥ 30 segments, résidu ≤ 1°, et cohérent avec les autres
        # photos de la même séquence (même support de caméra : à 4° de leur verticale médiane). Essais du
        # 18/10/2026 : les scènes boisées (troncs penchés) donnaient des inclinaisons de 6 à 23° dans une même
        # séquence, fausses (ef372e02) ; la séquence au casque du 12/01/2025 donne 16 à 20°, stable et juste.
        applique = incl >= 3.0 and n_seg >= 30 and res_deg <= 1.0 and coh.get("coherent", False)
        if applique:
            cam_dep = V.Camera(W, H, fov, cam0.C.copy(), lac, tg, rl)
        redr = {"inclinaison_deg": round(incl, 2), "applique": applique, "segments": n_seg,
                "residu_deg": round(res_deg, 2), "verticale_photo": [round(float(v), 5) for v in u],
                "sequence": coh, "correction_vue": {"dlacet": round(lac - cam0.lacet, 3),
                                                    "dtangage": round(tg - cam0.tangage, 3),
                                                    "droulis": round(rl - cam0.roulis, 3)}}
    al = PO.Alignement(cam_dep, P, T, typ, img, masque, porteur=por, sigma_xy=max(2.0, min(sig, 6.0)), modele=m,
                       cam_meta=cam0)
    m0 = al.mesures(None, cam=cam0)
    res = al.affiner(SEUIL_VALIDATION)
    rec = {"id": ph["id"], "id8": ph["id8"], **({"cle": cle} if cle != ph["id8"] else {}), "vue": ph["vue"], "porteur": por, "fichier_vue": vue_png.name,
           "camera_initiale": cam0.dict(), "mesures_initiales": m0, "points_modele_vus": al.n,
           "segments_photo": {"retenus": int(len(al.segments)), "ecartes": al.ecart_segments},
           "garde_fous": al.bornes | {"deplacement_m": PO.DEPLACEMENT_MAX}, "a_priori_sigma": al.sigma,
           "redressement_verticales": redr, "emprise_verticale_modele": round(al.emprise_verticale(), 3)}
    if res is None:
        rec.update({"camera_affinee": None, "statut": "non affinée : trop peu d'arêtes du modèle ou de segments",
                    "mesures_affinees": m0, "confiance": {"indice": 0.0, "niveau": "faible"},
                    "score_ameliore": False, "validation_amelioree": False})
    else:
        x6 = res["x"]
        m1 = al.mesures(x6)
        conf = PO.confiance(m0, m1, x6, al.n, res["stabilite"], res["validation"], al.bornes, al.emprise_verticale())
        niveau = res["niveau"]
        rec.update({"validation": res["validation"], "confiance": conf, "niveau_affinage": niveau,
                    "validation_amelioree": niveau is not None})
        if niveau is not None and m1["score_tau10"] < m0["score_tau10"]:
            cam1 = al.camera(x6)
            corr = {"ds": cam1.C[0] - cam0.C[0], "dt": cam1.C[1] - cam0.C[1], "dlacet": cam1.lacet - cam0.lacet,
                    "dtangage": cam1.tangage - cam0.tangage, "droulis": cam1.roulis - cam0.roulis,
                    "dh": cam1.C[2] - cam0.C[2]}
            rec.update({"camera_affinee": cam1.dict(), "mesures_affinees": m1,
                        "statut": "affinée (" + {"complete": "pose complète", "orientation": "orientation seule",
                                                 "redressement": "redressement par les verticales"}[niveau] + ")",
                        "correction": {k: round(float(v), 3) for k, v in corr.items()}
                        | {"deplacement_m": round(float(math.hypot(corr["ds"], corr["dt"])), 3)},
                        "amelioration_score_relative": round((m0["score_tau10"] - m1["score_tau10"])
                                                             / max(m0["score_tau10"], 1e-6), 4),
                        "etalement": round(al.etalement(x6), 3), "score_ameliore": True})
        else:
            rec.update({"camera_affinee": None, "mesures_affinees": m0, "score_ameliore": False,
                        "statut": "affinage rejeté (validation, garde-fou ou écrasement) : pose des métadonnées"})
    rec["duree_s"] = round(time.time() - t0, 1)
    journal(f"    pose {cle} ({ph['vue']['quadrant']:6s}) : {al.n:5d} points, {len(al.segments):4d} segments ; "
            f"recouvrement 3 px {m0.get('recouvrement_3px', 0):.3f} -> {rec['mesures_affinees'].get('recouvrement_3px', 0):.3f} ; "
            f"écart moyen {m0.get('ecart_moyen_px', 0):.2f} -> {rec['mesures_affinees'].get('ecart_moyen_px', 0):.2f} px ; "
            f"redr. {(rec.get('redressement_verticales') or {}).get('inclinaison_deg', 0):4.1f}° "
            f"val. redr. {rec.get('validation', {}).get('redressement', {}).get('amelioration_relative', 0):+.3f} "
            f"orient. {rec.get('validation', {}).get('orientation', {}).get('amelioration_relative', 0):+.3f} "
            f"compl. {rec.get('validation', {}).get('complete', {}).get('amelioration_relative', 0):+.3f} ; "
            f"{rec['statut'][:40]} ; confiance {rec['confiance']['niveau']} ; {rec['duree_s']} s")
    return rec


def etape_pose(site, sel):
    m, A = site.modele, site.ancrage
    P, T, typ = m.aretes()
    poses = []
    cache = {p["id"]: p for p in lire(site.dossiers["cache"] / "recherche.json", {}).get("photos", [])}
    jpgs, verticales = {}, {}
    for ph in sel["photos"]:
        photo = cache.get(ph["id"])
        if photo is None:
            raise RuntimeError(f"photo {ph['id']} absente du cache de recherche : relancer l'étape selection")
        jpgs[ph["id"]] = AP.telecharger(photo, "hd", site.dossiers["brut"])
        if ph["type"] == "360":
            im_r = Image.open(jpgs[ph["id"]]).convert("RGB")
            im_r = im_r.resize((2880, 1440), Image.LANCZOS) if im_r.size[0] > 2880 else im_r
            verticales[ph["id"]] = V.verticale_360(im_r)
    coherence = coherence_verticales(sel, verticales)
    for ph in sel["photos"]:
        rec = poser_vue(ph, jpgs[ph["id"]], verticales.get(ph["id"]), coherence.get(ph["id"], {}), m, A, P, T, typ,
                        site.dossiers["vues"], cle=ph["id8"])
        poses.append(rec)
    return poses, diagnostic_poses(poses)


def diagnostic_poses(poses):
    """Diagnostic du site : correction médiane des poses de confiance au moins moyenne (décalage systématique du modèle
    par rapport aux photos, si toutes les photos le voient).
    (contrôle du 18/10/2026 : ds et dt ne se lisent que sur les poses complètes ; une pose « orientation seule » a
    ds = dt = 0 par construction, ce qui tirait la médiane vers 0)"""
    bonnes = [p for p in poses if p.get("correction") and p["confiance"]["niveau"] in ("haute", "moyenne")]
    completes = [p for p in bonnes if p.get("niveau_affinage") == "complete"]
    diag = None
    if bonnes:
        diag = {k: (round(float(np.median([p["correction"][k] for p in completes])), 3) if completes else None)
                for k in ("ds", "dt")}
        diag["dlacet"] = round(float(np.median([p["correction"]["dlacet"] for p in bonnes])), 3)
        diag["n_poses"] = len(bonnes)
        diag["n_poses_completes"] = len(completes)
    return diag


def coherence_verticales(sel, verticales, tol=4.0):
    """Cohérence du redressement au sein d'une séquence (même support de caméra) : une photo est cohérente si sa
    verticale est à moins de `tol` degrés de celle d'au moins la moitié des AUTRES photos de la séquence (vote, robuste
    à une photo aberrante ; au moins une autre). Une photo seule dans sa séquence n'est pas jugée cohérente."""
    par = {}
    for ph in sel["photos"]:
        r = verticales.get(ph["id"])
        if r is not None:
            par.setdefault(ph["collection"], []).append((ph["id"], np.asarray(r[0], dtype=np.float64)))
    out = {}
    for col, lst in par.items():
        for pid, u in lst:
            autres = [v for q, v in lst if q != pid]
            if not autres:
                out[pid] = {"coherent": False, "motif": "seule photo de sa séquence"}
                continue
            ecarts = [math.degrees(math.acos(float(np.clip(u @ v, -1.0, 1.0)))) for v in autres]
            proches = sum(1 for e in ecarts if e <= tol)
            out[pid] = {"coherent": proches >= max(1, math.ceil(len(autres) / 2)), "proches": proches,
                        "n_autres": len(autres), "ecarts_deg": [round(e, 2) for e in ecarts]}
    return out


# ------------------------------------------------------------------------------------------------ étape rendu
def etape_rendu(site, sel, poses, echantillons, limite_s):
    scene_usda = DEPOT / site.conf["modele"] / "rendus" / "scene_rendu.usda"
    if not scene_usda.exists():
        raise RuntimeError(f"{scene_usda} absent : fabriquer la scène avec --rendus")
    d = site.dossiers["rendus"]
    vues_job = []
    for ph, po in zip(sel["photos"], poses):
        cam = cam_depuis(po.get("camera_affinee") or po["camera_initiale"])
        el, az_v = geo.soleil(ph["date"], ph["lon"], ph["lat"])
        az_g = geo.az_vrai_vers_grille(az_v, ph["lon"], ph["lat"])
        vues_job.append({"nom": ph["id8"], "camera": cam.usd(), "soleil_hauteur_deg": el,
                         "soleil_azimut_modele_deg": site.ancrage.lacet(az_g), "sortie_png": str(d / f"rendu_{ph['id8']}.png")})
    tmp = SORTIE / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    travail = d / "travail_rendu.json"
    resultat = d / "resultat_rendu.json"
    ecrire(travail, {"scene_usda": str(scene_usda), "manifest_rendus": str(scene_usda.parent / "manifest_rendus.json"),
                     "dossier": str(d), "vues": vues_job, "echantillons": echantillons, "limite_s": limite_s,
                     "resultat": str(resultat)})
    env = dict(os.environ, TEMP=str(tmp), TMP=str(tmp), HOUDINI_TEMP_DIR=str(tmp))
    r = subprocess.run([str(HYTHON), str(ICI / "rendu_hython.py"), str(travail)], env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("hython : " + r.stdout[-2000:] + r.stderr[-2000:])
    res = lire(resultat, [])
    for f in d.glob("ciel*.exr*"):
        f.unlink()
    return {"scene_usda": str(scene_usda.relative_to(DEPOT)), "scene_usda_sha256": sha256(scene_usda),
            "echantillons": echantillons, "vues": res}


# ------------------------------------------------------------------------------------------------ étape planches
def etape_planches(site, sel, poses):
    import decoupe
    m = site.modele
    P, T, typ = m.aretes()
    ancien = {e["id"]: e for e in (lire(site.dos / "ecarts.json", {}) or {}).get("photos", [])}
    ecarts, paires = [], []
    for ph, po in zip(sel["photos"], poses):
        vue = Image.open(site.dossiers["vues"] / po["fichier_vue"]).convert("RGB")
        f_r = site.dossiers["rendus"] / f"rendu_{ph['id8']}.png"
        rendu = Image.open(f_r).convert("RGB") if f_r.exists() else None
        cam0 = cam_depuis(po["camera_initiale"])
        cam1 = cam_depuis(po.get("camera_affinee") or po["camera_initiale"])
        masque = V.masque_porteur(cam0, po["porteur"])
        segs, _ = PO.segments_photo(vue, masque, cam0)
        a = np.asarray(vue).copy()
        for x0, y0, x1, y1, _ in segs:                 # segments de la photo retenus pour l'alignement (cyan)
            cv2.line(a, (int(x0), int(y0)), (int(x1), int(y1)), (0, 230, 255), 1)
        a = PO.dessiner_points(Image.fromarray(a), cam0, P, (255, 220, 0), 1)
        a = PO.dessiner_points(Image.fromarray(a), cam1, P, (40, 255, 90), 1)
        aretes = Image.fromarray(a)
        dp = site.dossiers["planches"]
        dp.mkdir(parents=True, exist_ok=True)
        aretes.save(dp / f"aretes_{ph['id8']}.png")
        vue.save(dp / f"vue_{ph['id8']}.png")
        st = None
        if rendu is not None:
            sup, st = PL.superposition(vue, rendu, masque)
            sup.save(dp / f"superposition_{ph['id8']}.png")
        else:
            sup = Image.new("RGB", vue.size, (40, 0, 0))
        mi, mf = po["mesures_initiales"], po["mesures_affinees"]
        titre = (f"{site.nom} | Panoramax {ph['id8']} {ph['date'][:10]} © {ph['auteur']} ({ph['licence']}) | "
                 f"{ph['type']} {ph['porteur']} | vue {ph['vue']['quadrant']} | recouvr. 3 px {mi.get('recouvrement_3px', 0):.2f}"
                 f"→{mf.get('recouvrement_3px', 0):.2f} | écart {mi.get('ecart_moyen_px', 0):.1f}→{mf.get('ecart_moyen_px', 0):.1f} px | "
                 f"confiance {po['confiance']['niveau']}")
        f_pl = PL.planche_photo(dp / f"planche_{ph['id8']}.png", titre,
                                [vue, rendu or Image.new("RGB", vue.size, (40, 0, 0)), sup, aretes],
                                ["photo (vue tirée de la photo, natif 1092 px réduit de moitié)",
                                 "rendu Karma depuis la pose affinée", "contours : photo cyan, rendu magenta, communs blanc",
                                 "arêtes modèle : initiale jaune, affinée verte ; segments photo cyan"])
        decoupe.decouper_image(f_pl, site.dossiers["tuiles"] / f_pl.stem)
        paires.append((vue, rendu, f"{ph['id8']} {ph['date'][:10]} {ph['vue']['quadrant']} s={ph['position_modele']['s']:.0f}"))
        g = PL.gabarit_ecarts(site.nom, ph, po, m, st)
        if ph["id"] in ancien:                       # on garde ce que l'agent a déjà rempli
            for k in ("grille", "visibilite", "synthese"):
                if ancien[ph["id"]].get(k) is not None:
                    g[k] = ancien[ph["id"]][k]
        ecarts.append(g)
    f_syn = PL.planche_synthese(site.dossiers["planches"] / "planche_synthese.png",
                                f"{site.nom} — {len(paires)} photos Panoramax (gauche) | rendus Karma depuis les poses affinées (droite) ; "
                                "photos © auteurs, licences dans selection.json", paires)
    decoupe.decouper_image(f_syn, site.dossiers["tuiles"] / f_syn.stem)
    PL.plan_site(site.dos / "plan_site.png", m, [dict(po, vue=ph["vue"]) for ph, po in zip(sel["photos"], poses)],
                 f"{site.nom} : modèle fabriqué et poses des {len(poses)} photos")
    return ecarts


# ------------------------------------------------------------------------------------------------ pilote
def traiter(nom, conf, etapes, args):
    t_site = time.time()
    site = Site(nom, conf)
    durees = {}
    journal(f"== {nom} : ancrage {site.ancrage.dict()} ; {site.diag_ancrage['methode']}")
    rapport = lire(site.dos / "rapport.json", {}) or {}
    # sélection
    t0 = time.time()
    if "selection" in etapes:
        conf_sel = dict(conf, porteurs_sequences=args.porteurs)
        sel = SE.choisir(nom, conf_sel, site.modele, site.ancrage, site.poi, site.dossiers, rafraichir=args.rafraichir,
                         depuis=args.depuis, journal=journal, jusqu_au=args.jusqu_au)
        sel["ancrage"] = site.ancrage.dict() | {"diagnostic": site.diag_ancrage}
        sel["point_interet"] = conf.get("point_interet")
        ecrire(site.dos / "selection.json", sel)
        durees["selection_s"] = round(time.time() - t0, 1)
        journal(f"  sélection : {len(sel['photos'])} photos, quadrants {sel['statistiques']['quadrants']}, positions "
                f"{sel['statistiques']['positions']} ({durees['selection_s']} s)")
    sel = lire(site.dos / "selection.json")
    if sel is None:
        raise RuntimeError("selection.json absent : lancer l'étape selection")
    # pose
    t0 = time.time()
    if "pose" in etapes:
        poses, diag = etape_pose(site, sel)
        ecrire(site.dos / "poses.json", {"schema": "comparaison_poses/0.1", "site": nom, "ancrage": site.ancrage.dict(),
                                         "garde_fous": PO.BORNES | {"deplacement_m": PO.DEPLACEMENT_MAX},
                                         "correction_mediane_du_site": diag, "poses": poses})
        durees["pose_s"] = round(time.time() - t0, 1)
    pdoc = lire(site.dos / "poses.json")
    poses = pdoc["poses"] if pdoc else None
    # rendu
    t0 = time.time()
    if "rendu" in etapes and poses:
        rr = etape_rendu(site, sel, poses, args.echantillons, args.limite)
        rapport["rendu"] = rr
        durees["rendu_s"] = round(time.time() - t0, 1)
        err = [v for v in rr["vues"] if v.get("erreur")]
        journal(f"  rendu : {len(rr['vues']) - len(err)} vues rendues, {len(err)} erreurs ({durees['rendu_s']} s)")
    # planches
    t0 = time.time()
    if "planches" in etapes and poses:
        ecarts = etape_planches(site, sel, poses)
        ecrire(site.dos / "ecarts.json", {"schema": "comparaison_ecarts/0.1", "site": nom,
                                          "description": conf["description"], "modele": conf["modele"],
                                          "consigne": "constat par rubrique : conforme | différent | absent | en trop | "
                                                      "non visible ; detail : ce qui est vu, sur quelle planche ou vue native "
                                                      "(photos_non_versionnees/planches/{planche,vue,superposition,aretes}_<id8>.png, rendus/rendu_<id8>.png)",
                                          "correction_mediane_du_site": (pdoc or {}).get("correction_mediane_du_site"),
                                          "photos": ecarts})
        durees["planches_s"] = round(time.time() - t0, 1)
    # rapport
    if poses:
        aff = [p for p in poses if str(p.get("statut", "")).startswith("affinée")]
        amel = [p for p in aff if p.get("score_ameliore") and p.get("amelioration_score_relative", 0) > 0]
        rapport.update({
            "site": nom, "ancrage": site.ancrage.dict() | {"diagnostic": site.diag_ancrage},
            "photos": len(sel["photos"]), "quadrants": sel["statistiques"]["quadrants"],
            "positions": sel["statistiques"]["positions"], "sequences": sel["statistiques"]["sequences"],
            "poses_affinees": len(aff), "poses_ameliorees": len(amel),
            "poses_validation_amelioree": sum(1 for p in poses if p.get("validation_amelioree")),
            "part_poses_ameliorees": round(len(amel) / max(1, len(poses)), 3),
            "confiance": {k: sum(1 for p in poses if p["confiance"]["niveau"] == k) for k in ("haute", "moyenne", "faible")},
            "recouvrement_3px_median": [round(float(np.median([p["mesures_initiales"].get("recouvrement_3px", 0) for p in poses])), 4),
                                        round(float(np.median([p["mesures_affinees"].get("recouvrement_3px", 0) for p in poses])), 4)],
            "ecart_moyen_px_median": [round(float(np.median([p["mesures_initiales"].get("ecart_moyen_px", 0) for p in poses])), 3),
                                      round(float(np.median([p["mesures_affinees"].get("ecart_moyen_px", 0) for p in poses])), 3)],
            "correction_mediane_du_site": (pdoc or {}).get("correction_mediane_du_site"),
        })
    rapport.setdefault("durees", {}).update(durees)
    rapport["durees"]["total_derniere_execution_s"] = round(time.time() - t_site, 1)
    ecrire(site.dos / "rapport.json", rapport)
    journal(f"  {nom} : {rapport['durees']}")
    return rapport


def main():
    global SORTIE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sites", nargs="+")
    ap.add_argument("--sites-conf", default=str(ICI / "sites_meylan.json"))
    ap.add_argument("--etapes", default=None, help="v1 : selection,pose,rendu,planches ; v2 : + dessus")
    ap.add_argument("--rafraichir", action="store_true", help="rejouer les recherches Panoramax et Mapillary (sinon : cache)")
    ap.add_argument("--depuis", default="2019-01-01", help="date minimale des photos")
    ap.add_argument("--jusqu-au", dest="jusqu_au", default=None, help="date maximale des photos (état décrit)")
    ap.add_argument("--echantillons", type=int, default=128)
    ap.add_argument("--limite", type=int, default=240, help="limite de temps d'un rendu (s)")
    ap.add_argument("--sortie", default=None, help="racine des sorties (défaut : recon/out/generateur/comparaison)")
    ap.add_argument("--v2", action="store_true", help="comparaison v2 (sélection guidée par la couverture)")
    ap.add_argument("--selection", choices=("v1", "couverture"), default=None,
                    help="« couverture » = --v2 ; « v1 » (défaut) : sélection de 6 à 12 photos de la v1")
    ap.add_argument("--processus", type=int, default=4, help="v2 : processus parallèles pour les poses et les planches")
    ap.add_argument("--sans-mapillary", dest="sans_mapillary", action="store_true", help="v2 : Panoramax seul")
    ap.add_argument("--complement-depuis", dest="complement_depuis", default="2019-01-01",
                    help="v2 : photos antérieures à --depuis admises en complément depuis cette date (marquées hors "
                         "fenêtre d'état) ; « non » pour s'en passer")
    ap.add_argument("--exclure-periodes", dest="exclure_periodes", default=None,
                    help="v2 : périodes de photos écartées (travaux, état transitoire), AAAA-MM-JJ:AAAA-MM-JJ[,...]")
    ap.add_argument("--couches-orthos", dest="couches_orthos", default=None,
                    help="v2 : couches du kit multi-orthos (défaut : toutes ; ex. pcrs2022,ign2024,ign2021)")
    args = ap.parse_args()
    if args.sortie:
        p = Path(args.sortie)
        SORTIE = (p if p.is_absolute() else DEPOT / p).resolve()
    v2 = args.v2 or args.selection == "couverture"
    if str(args.complement_depuis).lower() in ("non", "aucun", "none", ""):
        args.complement_depuis = None
    args.couches_orthos = [c.strip() for c in args.couches_orthos.split(",")] if args.couches_orthos else None
    args.exclure_periodes = [tuple(p.strip().split(":")) for p in args.exclure_periodes.split(",")] \
        if args.exclure_periodes else None
    doc_sites = lire(args.sites_conf)
    confs = doc_sites["sites"]
    args.porteurs = doc_sites.get("porteurs_sequences", {})
    etapes = [e.strip() for e in (args.etapes or ",".join(ETAPES_V2 if v2 else ETAPES)).split(",") if e.strip()]
    bilan = {}
    for s in args.sites:
        if v2:
            import etapes_v2 as E2
            E2.CM.SORTIE = SORTIE        # lancé comme script : etapes_v2 importe une seconde instance du module
            bilan[s] = E2.traiter(s, confs[s], etapes, args)
        else:
            bilan[s] = traiter(s, confs[s], etapes, args)
    tout = lire(SORTIE / "bilan.json", {}) or {}
    tout.update({k: {kk: v.get(kk) for kk in ("version", "photos", "vues", "photos_panoramax", "photos_mapillary",
                                              "photos_hors_fenetre_etat", "fenetre_etat",
                                              "quadrants", "positions", "poses_ameliorees", "part_poses_ameliorees",
                                              "confiance", "recouvrement_3px_median", "ecart_moyen_px_median",
                                              "correction_mediane_du_site", "couverture_coeur", "zones_aveugles", "durees")
                     if kk in v}
                 for k, v in bilan.items()})
    ecrire(SORTIE / "bilan.json", tout)


if __name__ == "__main__":
    main()
