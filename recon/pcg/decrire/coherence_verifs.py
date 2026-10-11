"""Orchestration des vérifications image du solveur de cohérence v3 : Q1 (mesures avant la résolution, candidats
après), Q2 (validation locale des poses, mémorisée par photo et objet) et Q4 (présence 2026 sur les photos
calées postérieures aux travaux, vignettes de présence). Les tests eux-mêmes sont dans coherence_photos
(image) et coherence_accord (décision)."""
import math

import numpy as np

import coherence_accord as AC
import coherence_photos as PH
import coherence_poses as PO

HAUTEUR_DEFAUT = {"lampadaire": 6.0, "mat_camera": 6.0, "poteau_reseau": 6.0, "support_feux": 3.0, "panneau": 2.3,
                  "balise_J11": 1.0, "potelet": 0.9, "poteau_arret": 2.5, "arbre": 2.5, "barriere_levante": 1.0,
                  "boite_aux_lettres": 1.2, "stationnement_velos": 0.8, "corbeille": 0.9}
RAYON_PRESENCE = 25.0
Q2 = {}                   # {(photo, objet): résultat de la validation locale}


def hauteur_bande(o):
    """Hauteur de la bande « pied -> h » du test d'axe (tronc pour un arbre)."""
    if o["type"] == "arbre":
        return 2.5
    h = o.get("hauteur")
    try:
        h = float(h) if h is not None else HAUTEUR_DEFAUT.get(o["type"], 2.5)
    except (TypeError, ValueError):
        h = HAUTEUR_DEFAUT.get(o["type"], 2.5)
    return float(np.clip(h, 0.8, 12.0))


def diametre(o):
    return PH.DIAMETRES.get(o["type"], max(2 * float(o.get("rayon") or 0.06), 0.06))


MATS_PORTEURS = ("lampadaire", "support_feux", "mat_camera", "poteau_reseau", "poteau_arret")


def dims_test(o, groupes=None):
    """(hauteur de bande, diamètre) du fût vu par le test d'axe : le mât porteur du groupe rigide s'il existe
    (candélabre, support de feux...), sinon le poteau du panneau jusqu'en haut de la plaque, la balise J5 / J11
    (≈ 1 m, 0,2 m de large), ou l'objet lui-même."""
    membres = (groupes or {}).get(o.get("groupe"), [o])
    mats = sorted([m for m in membres if m["type"] in MATS_PORTEURS],
                  key=lambda m: (-float(m.get("hauteur") or HAUTEUR_DEFAUT.get(m["type"], 3.0)), m["id"]))
    if mats:
        m = mats[0]
        return hauteur_bande(m), diametre(m)
    code = str(o.get("code") or "")
    if o["type"] == "balise_J11" or code.startswith(("J5", "J11", "J13")):
        return float(np.clip(float(o.get("hauteur") or 1.0), 0.8, 1.5)), 0.20
    if o["type"] == "panneau":
        try:
            hb = float(o.get("hauteur") or 1.8)
        except (TypeError, ValueError):
            hb = 1.8
        return float(np.clip(hb + 0.5, 1.8, 3.5)), PH.DIAMETRES["panneau"]
    return hauteur_bande(o), diametre(o)


def groupes_de(objets):
    g = {}
    for o in objets:
        g.setdefault(o.get("groupe"), []).append(o)
    return g


def photos_objet(P3, h, valide, dmax=40.0, apres_seulement=False):
    out = []
    for p in PO.catalogue():
        if not p["decisive"] or not valide(p["date"]):
            continue
        if apres_seulement and not PH.apres_travaux(p["date"]):
            continue
        d = PO.voit(p, P3, h, dmax=dmax)
        if d is not None:
            out.append(p)
    return out


def executer(taches, faire_vignettes=True):
    """Exécute les tâches en sautant les validations Q2 déjà faites ; complète la mémoire Q2."""
    a_faire = [t for t in taches if not (t["nature"] == "q2" and (t["pid"], t["cle"]) in Q2)]
    vus = set()
    uniq = []
    for t in a_faire:
        k = (t["nature"], str(t["cle"]), t["pid"])
        if k not in vus:
            vus.add(k)
            uniq.append(t)
    R = PH.executer(uniq, faire_vignettes=faire_vignettes)
    for (nat, cle, pid), r in R.items():
        if nat == "q2":
            Q2[(pid, cle)] = r
    return R


def validations(oid):
    """{photo: validation Q2} connues pour l'objet."""
    return {pid: r for (pid, cle), r in sorted(Q2.items()) if cle == oid}


def _accord_depuis(R, cle_axe, oid, A, X, cle_hyp, photos, apres_seulement=False):
    lignes = []
    for p in photos:
        if apres_seulement and not PH.apres_travaux(p["date"]):
            continue
        r = R.get(("axe", cle_axe, p["id"]))
        if r is None or not r.get("par_hyp"):
            continue
        ph = r["par_hyp"]
        if "A" not in ph or cle_hyp not in ph:
            continue
        q = Q2.get((p["id"], oid)) or {}
        lignes.append(dict(pid=p["id"], cam_c=p["cam"].C, decisive=bool(p["decisive"] and q.get("valide")),
                           motif_q2=q.get("motif"), par_hyp={"A": ph["A"], "C": ph[cle_hyp]}))
    return AC.accord(A, X, lignes)


# --------------------------------------------------------------------------- Q1 : mesures
def q1_mesures(objets, carte, valide_pour_photo):
    """Test d'accord image de chaque mesure candidate valide (probante ou hypothèse) : {(objet, k): résultat}."""
    taches, plans = [], []
    groupes = groupes_de(objets)
    for o in objets:
        if str(o["statut"]).startswith("absent"):
            continue
        A = np.asarray(o["p_source"], float)
        ms = [(k, m) for k, m in enumerate(o.get("mesures") or []) if m["valide"] and m["statut"] in ("probante", "hypothese")
              and float(np.hypot(*(m["xy"] - A))) > 0.05]
        if not ms:
            continue
        hyps = [("A", A)] + [(f"M{k}", np.asarray(m["xy"], float)) for k, m in ms]
        zs = [float(z) for z in carte.z_sol(np.array([q for _, q in hyps]))]
        h, diam = dims_test(o, groupes)
        P3 = [np.r_[q, z] for (_, q), z in zip(hyps, zs)]
        phs = photos_objet(P3, h, lambda d, o=o: valide_pour_photo(o, d))
        if not phs:
            phs = photos_objet(P3[:1], h, lambda d, o=o: valide_pour_photo(o, d))
        for p in phs:
            taches.append(dict(pid=p["id"], nature="q2", cle=o["id"], args=dict(xy=A)))
            taches.append(dict(pid=p["id"], nature="axe", cle=("mes", o["id"]), args=dict(hyps=hyps, h=h, diam=diam, zs=zs)))
        plans.append((o, A, ms, phs))
    R = executer(taches)
    out = {}
    for o, A, ms, phs in plans:
        for k, m in ms:
            apres = bool(m.get("date") and PH.apres_travaux(m["date"]))
            out[(o["id"], k)] = _accord_depuis(R, ("mes", o["id"]), o["id"], A, m["xy"], f"M{k}", phs, apres_seulement=apres)
    return out


# --------------------------------------------------------------------------- Q1 : candidats de la résolution
def q1_candidats(objets, carte, positions, valide_pour_photo, seuil=0.30):
    """Test d'accord image de la position résolue C contre l'a priori p0 (déplacement > seuil)."""
    taches, plans = [], []
    groupes = groupes_de(objets)
    for o in objets:
        if o["id"] not in positions or str(o["statut"]).startswith("absent"):
            continue
        A = np.asarray(o["p0"], float)
        C = np.asarray(positions[o["id"]], float)
        if float(np.hypot(*(C - A))) <= seuil:
            continue
        hyps = [("A", A), ("C", C)]
        zs = [float(z) for z in carte.z_sol(np.array([A, C]))]
        h, diam = dims_test(o, groupes)
        phs = photos_objet([np.r_[A, zs[0]], np.r_[C, zs[1]]], h, lambda d, o=o: valide_pour_photo(o, d))
        for p in phs:
            taches.append(dict(pid=p["id"], nature="q2", cle=o["id"], args=dict(xy=np.asarray(o["p_source"], float))))
            taches.append(dict(pid=p["id"], nature="axe", cle=("cand", o["id"]), args=dict(hyps=hyps, h=h, diam=diam, zs=zs)))
        plans.append((o, A, C, phs))
    R = executer(taches)
    return {o["id"]: _accord_depuis(R, ("cand", o["id"]), o["id"], A, C, "C", phs) for o, A, C, phs in plans}


# --------------------------------------------------------------------------- Q2 : photos des planches
def q2_planches(jobs, faire=True):
    """jobs : [(objet id, xy, [photos])] : validations Q2 manquantes pour les photos des planches."""
    taches = []
    for oid, xy, phs in jobs:
        for p in phs:
            taches.append(dict(pid=p["id"], nature="q2", cle=oid, args=dict(xy=np.asarray(xy, float))))
    if taches:
        executer(taches, faire_vignettes=faire)


# --------------------------------------------------------------------------- Q4 : présence 2026
def q4_presence(objets, carte, positions, faire_vignettes=True):
    """Objets à moins de 25 m d'une photo calée postérieure aux travaux qui les voit : test automatique et
    vignettes. Renvoie {objet: dict(photos=[...], auto, vignettes)}."""
    import sys
    from commun import RACINE
    sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
    from projection import occulte_par_batiments
    post = [p for p in PO.catalogue() if PH.apres_travaux(p["date"])]
    taches, plans = [], []
    groupes = groupes_de(objets)
    for o in objets:
        if o["id"] not in positions or o.get("couche") not in ("mobilier", "arbres"):
            continue
        xy = np.asarray(positions[o["id"]], float)
        z = float(carte.z_sol(xy[None])[0])
        if o["type"] == "arbre":
            h = float(o.get("hauteur") or 8.0)
            rayon = float(np.clip(h / 4.0, 1.0, 3.0))
        else:
            h, _ = dims_test(o, groupes)
            rayon = max(float(o.get("rayon") or 0.1), 0.15)
        P3 = np.r_[xy, z]
        phs = []
        for p in post:
            d = float(np.hypot(*(xy - p["cam"].C[:2])))
            if d > RAYON_PRESENCE:
                continue
            if PO.voit(p, [P3], min(h, 6.0), dmax=RAYON_PRESENCE) is None:
                continue
            occ = occulte_par_batiments(p["cam"].C, np.array([P3 + [0, 0, 0.3], P3 + [0, 0, min(h, 6.0)]]))
            phs.append((p, d, bool(occ.all())))
        if not phs:
            continue
        for p, d, occ in phs:
            taches.append(dict(pid=p["id"], nature="q2", cle=o["id"], args=dict(xy=np.asarray(o["p_source"], float))))
            taches.append(dict(pid=p["id"], nature="presence", cle=o["id"],
                               args=dict(xy=xy, z=z, h=h, type=o["type"], rayon=rayon, titre=f"{o['id']} ({o['type']})")))
        plans.append((o, xy, phs))
    R = executer(taches, faire_vignettes=faire_vignettes)
    out = {}
    for o, xy, phs in plans:
        lignes = []
        for p, d, occ in phs:
            r = dict(R.get(("presence", o["id"], p["id"])) or {})
            vig = r.pop("_vignette", None)
            r.pop("d_m", None)
            q = Q2.get((p["id"], o["id"])) or {}
            lignes.append(dict(photo=p["id"], date=p["date"], d_m=round(d, 1), occulte_batiment=occ,
                               pose_validee_q2=bool(q.get("valide")), motif_q2=q.get("motif"), **r, _vignette=vig))
        autos = [l["auto"] for l in lignes if not l["occulte_batiment"]]
        if "present" in autos:
            auto = "present"
        elif autos and all(a == "absent" for a in autos) and any(l["pose_validee_q2"] for l in lignes if l["auto"] == "absent"):
            auto = "absent"
        else:
            auto = "indetermine"
        out[o["id"]] = dict(position=[round(float(v), 3) for v in xy], photos=lignes, auto=auto)
    return out
