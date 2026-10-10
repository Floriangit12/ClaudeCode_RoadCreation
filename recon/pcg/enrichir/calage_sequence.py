"""Calage d'une séquence 360° dont l'azimut GNSS est faux : pose grossière, poses.caler, ajustement commun.

Cas d'usage : série Panoramax du 2026-07-28 (GoPro Max sur voiture, allée des Mitaillères, ≈ 135 m au
sud du carrefour, seules photos postérieures aux travaux). L'azimut des métadonnées vient de la trace
GNSS et se trompe de 30 à 54° dans le virage (constat p2026_07_ign-02), la position de 5 à 6 m : hors
de portée du vote de poses.py (± 12° en lacet, ± 2,5 m en position).

Chaîne par photo (_caler_un) :
1. pose grossière :
   - si des pointages visuels existent (--pointages, {id8: {lacet_depart, observations}}) : résection
     sur des points d'appui nommés du levé GAM 2026 (gcp_reference : « GAM:SH359:2 » sommet d'une
     entité, « GAML:SH339 » axe d'une ligne, « MOB:<id> » mât du paquet), ajustement robuste de
     poses.py (erreurs angulaires), a priori lâche (xy 8 m, lacet 20°, hauteur selon « h_a_priori ») ;
     les identités ambiguës (tirets répétitifs) se testent par hypothèses : seule la bonne laisse des
     résidus < 0,5° ;
   - sinon : recherche par contraste des marquages valides à la date (paires intérieur/extérieur le
     long des bords, grille x, y, lacet autour d'un lacet de départ --lacets ou sur 360°) ;
2. poses.caler(a_priori=...) : vote, RANSAC + LM sur les GCP datés du catalogue gcp.py ;
3. ajustement commun (combiner) : inliers automatiques + pointages visuels, sélection des inliers et
   acceptation par poses._qualite (résidu moyen ≤ 0,5°, contraintes indépendantes, leave-one-out,
   répartition, écart GNSS) ; refus explicite possible (« refus » du pointage) après relecture.
assembler() vérifie en plus la cohérence de séquence (même monture) : hauteur d'objectif à ± 0,3 m et
assiette à ± 3° de la médiane des photos acceptées.

Les sorties (par_photo/, grossier/, poses_<date>.json, planches/) vont dans le dossier --sortie ;
enrichi/poses/ (poses.json partagé) n'est pas modifié. Déterministe.

  python calage_sequence.py --date 2026-07-28 --sortie <dossier> --pointages <p.json> [--lacets <l.json>]
                            [--proc 7] [--planches]
  python calage_sequence.py --date 2026-07-28 --sortie <dossier> --grossier-seul
  python calage_sequence.py --date 2026-07-28 --sortie <dossier> --assembler [--planches]
"""
import argparse
import functools
import math
import sys
import time
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
if str(ICI) not in sys.path:
    sys.path.insert(0, str(ICI))
from camera import (camera, catalogue, ecrire_json, echantillonner, image_gris,  # noqa: E402
                    intrinseques, lire_json, photo, pose_brute, z_sol)
import gcp as G  # noqa: E402

SCHEMA = "pj_calage_sequence/0.1"
MASQUES_LON = {"2026-07-28": [(-92.0, -78.0)]}   # salissure fixe de l'objectif (longitudes caméra, deg)


# --------------------------------------------------------------------------- score de contraste
@functools.lru_cache(maxsize=4)
def paires(date):
    """Paires (intérieur, extérieur) le long des bords des marquages valides à la date : (A (N,3), B (N,3))."""
    A, B = [], []
    for r, de, a in G._marquages_polygones():
        if not de <= date <= a or len(r) < 3:
            continue
        x, y = r[:, 0], r[:, 1]
        aire = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        sens = 1.0 if aire > 0 else -1.0             # anneau direct : l'intérieur est à gauche
        for p, q in zip(r, np.roll(r, -1, axis=0)):
            L = float(np.linalg.norm(q - p))
            if L < 0.08:
                continue
            t = (q - p) / L
            n_ext = sens * np.array([t[1], -t[0]])   # normale extérieure
            for s in np.arange(0.05, L - 0.02, 0.12):
                c = p + t * s
                A.append(c - 0.04 * n_ext)
                B.append(c + 0.18 * n_ext)
    A, B = np.array(A), np.array(B)
    zA = np.array([z_sol(*c) for c in A]) + 0.01
    zB = np.array([z_sol(*c) for c in B]) + 0.01
    return np.c_[A, zA], np.c_[B, zB]


class Score:
    """Score de contraste des marquages pour une photo (voir docstring du module)."""

    def __init__(self, ph, centre, rayon=25.0):
        self.ph = ph
        self.img = image_gris(ph.id8)
        self.intr = intrinseques(ph)
        A, B = paires(ph.date)
        d = np.hypot(A[:, 0] - centre[0], A[:, 1] - centre[1])
        k = d < rayon + 8.0
        self.A, self.B = A[k], B[k]
        self.rayon = rayon
        self.lat_min = math.radians(G.lat_min_cam(ph) + 1.0)
        self.masques = [(math.radians(a0), math.radians(a1)) for a0, a1 in MASQUES_LON.get(ph.date, [])]

    def __call__(self, p, detail=False):
        c = camera(self.ph, p, self.intr)
        ca, cb = c.monde_vers_cam(self.A), c.monde_vers_cam(self.B)
        dist = np.hypot(self.A[:, 0] - p[0], self.A[:, 1] - p[1])
        lat = np.arctan2(ca[:, 2], np.hypot(ca[:, 0], ca[:, 1]))
        lon = np.arctan2(ca[:, 0], ca[:, 1])
        ok = (dist > 3.0) & (dist < self.rayon) & (lat > self.lat_min)
        for a0, a1 in self.masques:
            ok &= ~((lon >= a0) & (lon <= a1))
        if ok.sum() < 50:
            return (-1.0, 0, 0.0) if detail else -1.0
        ua, _ = c.cam_vers_pixel(ca[ok])
        ub, _ = c.cam_vers_pixel(cb[ok])
        ia = echantillonner(self.img, ua[:, 0], ua[:, 1], boucle=True)
        ib = echantillonner(self.img, ub[:, 0], ub[:, 1], boucle=True)
        dd = np.clip(ia - ib, -0.25, 0.25)
        w = 1.0 / (1.0 + dist[ok] / 10.0)
        s = float((dd * w).sum() / w.sum())
        if detail:
            return s, int(ok.sum()), float((dd > 0.03).mean())
        return s


def _grille(score, p0, dxy, nxy, dl, nl):
    """Recherche exhaustive (x, y, lacet) autour de p0 (z suit le MNT à hauteur constante)."""
    best = (score(p0), p0.copy())
    h = p0[2] - z_sol(p0[0], p0[1])
    for dx in np.arange(-nxy, nxy + 1) * dxy:
        for dy in np.arange(-nxy, nxy + 1) * dxy:
            q = p0.copy()
            q[0] += dx
            q[1] += dy
            q[2] = z_sol(q[0], q[1]) + h
            for da in np.arange(-nl, nl + 1) * dl:
                q2 = q.copy()
                q2[3] = (q2[3] + da) % 360.0
                s = score(q2)
                if s > best[0]:
                    best = (s, q2)
    return best


def _affiner(score, p, pas_angle=0.25, pas_z=0.1):
    """Descente par coordonnées sur tangage, roulis, hauteur et lacet."""
    best = score(p)
    for _ in range(2):
        for j, pas, n in ((4, pas_angle, 6), (5, pas_angle, 6), (2, pas_z, 4), (3, 0.1, 5)):
            for v in p[j] + np.arange(-n, n + 1) * pas:
                q = p.copy()
                q[j] = v
                s = score(q)
                if s > best:
                    best, p = s, q
    return best, p


def pose_grossiere(pid, lacet0=None, rayon=25.0, rxy=6.0, verbeux=True):
    """Pose grossière par contraste des marquages. lacet0 : lacet initial (deg, grille) ou None (360°).
    Renvoie dict(pose, score, unicite, ...)."""
    t0 = time.time()
    ph = photo(pid)
    pb = pose_brute(ph)
    p0 = pb["pose"].copy()
    p0[2] = z_sol(p0[0], p0[1]) + ph.seq["h"]
    if lacet0 is not None:
        p0[3] = float(lacet0) % 360.0
    sc = Score(ph, p0[:2], rayon)
    if lacet0 is None:                                   # 360° : pas de 3°, grille de 1 m
        s, p = _grille(sc, p0, 1.0, int(round(rxy)), 3.0, 60)
    else:                                                # lacet visuel ± 10°
        s, p = _grille(sc, p0, 0.5, int(round(rxy / 0.5)), 1.0, 10)
    s, p = _affiner(sc, p, 0.5, 0.15)
    s, p = _grille(sc, p, 0.1, 5, 0.25, 4)
    s, p = _affiner(sc, p, 0.2, 0.05)
    s_fin, n_pts, frac = sc(p, detail=True)
    # unicité : meilleur score hors d'un voisinage de 1,5 m / 4° (lacets à ± 30°, grille de 1 m)
    alt = -1.0
    h = p[2] - z_sol(p[0], p[1])
    for dl in np.arange(-30.0, 30.1, 2.0):
        for dx in np.arange(-3.0, 3.1, 1.0):
            for dy in np.arange(-3.0, 3.1, 1.0):
                if abs(dl) < 4.0 and math.hypot(dx, dy) < 1.5:
                    continue
                q = p.copy()
                q[0] += dx
                q[1] += dy
                q[2] = z_sol(q[0], q[1]) + h
                q[3] = (q[3] + dl) % 360.0
                alt = max(alt, sc(q))
    rec = dict(id8=ph.id8, lacet_depart=None if lacet0 is None else round(float(lacet0), 2),
               pose=[round(float(v), 4) for v in p[:6]], score=round(s_fin, 4), n_paires=n_pts,
               part_positive=round(frac, 3), score_alternatif=round(alt, 4),
               unicite=round(s_fin / alt, 3) if alt > 0 else None,
               ecart_gnss_m=round(float(math.hypot(p[0] - pb["pose"][0], p[1] - pb["pose"][1])), 2),
               correction_lacet_deg=round(float(((p[3] - pb["pose"][3] + 180) % 360) - 180), 2),
               duree_s=round(time.time() - t0, 1))
    if verbeux:
        print(f"[{ph.id8}] grossier : {rec}", flush=True)
    return rec


def a_priori(ph, grossier, sig_xy=1.0, sig_lacet=2.0):
    """A priori externe pour poses.caler à partir de la pose grossière (contraste ou résection)."""
    p = np.array(grossier["pose"], float)
    src = grossier.get("methode") or "contraste des marquages"
    return dict(pose=p, sigma=dict(xy=sig_xy, z=0.3, lacet=sig_lacet, tangage=1.5, roulis=1.5),
                source=f"pose grossière ({src}, {ph.date}, calage_sequence.py) : score {grossier.get('score')}, "
                       f"résidu moyen {grossier.get('residu_moy_deg')}°, lacet de départ {grossier.get('lacet_depart')}")


# --------------------------------------------------------------------------- points d'appui GAM 2026 nommés
GAM_DIR = Path(__file__).resolve().parents[3] / "data/sites/paquet_jardin/etat_2026"
GAM_FICHIERS = {"SH": "signalisation_horizontale_lin_L93.geojson", "SP": "signalisation_horizontale_pct_L93.geojson",
                "BO": "bordure_lin_L93.geojson", "LR": "limite_revetement_lin_L93.geojson"}


@functools.lru_cache(maxsize=8)
def _gam(prefixe):
    return lire_json(GAM_DIR / GAM_FICHIERS[prefixe])["features"]


def _sommets(g):
    out = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            out.append(c[:2])
        else:
            for q in c:
                walk(q)
    walk(g["coordinates"])
    return np.asarray(out, dtype=np.float64)


def gcp_reference(ref, hauteur=None):
    """GCP à partir d'une référence nommée :
    - « GAM:SH359:2 » : sommet 2 de l'entité 359 du levé GAM 2026 (SH signalisation horizontale lin,
      SP ponctuelle, BO bordures, LR limites de revêtement), au sol (MNT 2026 + 3 mm), σ 0,05 m
      (SP : point d'insertion du bloc, σ 0,25 m) ;
    - « MOB:<id> » : mât du paquet (objets/mobilier.geojson), axe pied -> pied + hauteur (σ 0,25/0,6 m) ;
    - « LOC:x,y[,σ] » : point au sol local explicite (σ par défaut 0,3 m)."""
    from camera import DONNEES, O
    t, a = ref.split(":", 1)
    if t == "GAM":
        pre_i, _, k = a.partition(":")
        pre, i = pre_i[:2], int(pre_i[2:])
        S = _sommets(_gam(pre)[i]["geometry"]) - np.array(O[:2])
        q = S[int(k or 0)]
        return dict(id=ref, famille="sol", type="gam_2026", point=[float(q[0]), float(q[1]), z_sol(*q) + 0.003],
                    sigma_m=0.25 if pre == "SP" else 0.05, poids=1.0,
                    source=f"levé GAM 2026 {GAM_FICHIERS[pre]} entité {i} sommet {k or 0}")
    if t == "GAML":                                   # axe d'une ligne levée : observation 1D (pixels sur l'axe)
        pre_i, _, ks = a.partition(":")
        pre, i = pre_i[:2], int(pre_i[2:])
        S = _sommets(_gam(pre)[i]["geometry"]) - np.array(O[:2])
        k0, k1 = (int(x) for x in ks.split("-")) if ks else (0, len(S) - 1)
        A, B = S[k0], S[k1]
        za, zb = z_sol(*A) + 0.003, z_sol(*B) + 0.003
        m = (A + B) / 2
        return dict(id=ref, famille="sol", type="ligne_marquage", point=[float(m[0]), float(m[1]), z_sol(*m) + 0.003],
                    pied=[float(A[0]), float(A[1]), za], sommet=[float(B[0]), float(B[1]), zb], sigma_m=0.05,
                    poids=0.5, source=f"levé GAM 2026 {GAM_FICHIERS[pre]} entité {i}, axe sommets {k0}-{k1}")
    if t == "MOB":
        f = next(x for x in lire_json(DONNEES / "objets/mobilier.geojson")["features"] if x["properties"]["id"] == a)
        p = f["properties"]
        x, y = p["x_local"], p["y_local"]
        z = z_sol(x, y)
        h = float(hauteur or p.get("hauteur_m") or 3.0)
        return dict(id=ref, famille="mat", type=p.get("type"), pied=[x, y, z], sommet=[x, y, z + h],
                    sigma_m=0.25 if p.get("confiance") == "haute" else 0.6, poids=1.0,
                    source=f"paquet objets/mobilier.geojson {a} ({str(p.get('source'))[:80]})")
    if t == "LOC":
        v = [float(s) for s in a.split(",")]
        return dict(id=ref, famille="sol", type="local", point=[v[0], v[1], z_sol(v[0], v[1]) + 0.003],
                    sigma_m=v[2] if len(v) > 2 else 0.3, poids=1.0, source="point local explicite")
    raise ValueError(ref)


def resection(pid, entree, verbeux=True):
    """Pose par pointage visuel de points d'appui nommés (GAM 2026, mâts) : entree = dict(lacet_depart,
    [xy_depart], observations=[dict(ref, uv | uvs (axe d'un mât), note)]). Ajustement robuste de poses.py
    (erreurs angulaires, a priori lâche : xy 8 m, lacet 20°) ; qualité et acceptation par poses._qualite
    (mêmes critères que le calage automatique). Renvoie l'enregistrement (dict)."""
    import poses as PS
    ph = photo(pid)
    intr = intrinseques(ph)
    pb = pose_brute(ph)
    p_brut = pb["pose"].copy()
    p0 = p_brut.copy()
    if entree.get("xy_depart"):
        p0[0], p0[1] = entree["xy_depart"]
    p0[2] = z_sol(p0[0], p0[1]) + float(entree.get("h_a_priori") or ph.seq["h"])
    p0[3] = float(entree["lacet_depart"]) % 360.0
    sigma = dict(xy=8.0, z=float(entree.get("sigma_h") or 0.6), lacet=20.0, tangage=3.0, roulis=3.0)
    gidx, obs = {}, []
    for o in entree["observations"]:
        g = gcp_reference(o["ref"], o.get("hauteur_m"))
        gidx[g["id"]] = g
        if "uvs" in o:
            obs.append(dict(gcp=g["id"], type="ligne", uv=[list(map(float, x)) for x in o["uvs"]], poids=1.0,
                            pointage="visuel", note=o.get("note", "")))
        else:
            obs.append(dict(gcp=g["id"], type="point", uv=list(map(float, o["uv"])), poids=1.0,
                            pointage="visuel", note=o.get("note", "")))
    aj = PS.Ajustement(ph, intr, p0, sigma, obs, gidx, focale_libre=False, sig_det_deg=0.12)  # visuel ≈ 2 px
    p = aj.lm(p0, n_iter=60)
    inl = aj.erreurs_groupes(p) < aj.taus()
    for _ in range(3):
        p = aj.lm(p, *aj.poids_inliers(inl), n_iter=40)
        inl = aj.erreurs_groupes(p) < aj.taus()
    q = PS._qualite(ph, aj, p, inl, p_brut, intr, gidx)
    rec = dict(id8=ph.id8, methode="résection sur pointage visuel (GAM 2026, mâts)", lacet_depart=entree["lacet_depart"],
               pose=[round(float(v), 4) for v in p[:6]], residu_moy_deg=q["qualite"]["residu_moy_deg"],
               score=None, accepte_criteres_poses=q["accepte"], raison=q["raison"], qualite=q["qualite"],
               ecart_type=q["ecart_type"], observations=q["observations"],
               gcp={k: {kk: v for kk, v in g.items()} for k, g in gidx.items()})
    if verbeux:
        print(f"[{ph.id8}] résection : pose {rec['pose']} moy {q['qualite']['residu_moy_deg']}° max "
              f"{q['qualite']['residu_max_deg']}° n {q['qualite']['n_gcp']} accepte {q['accepte']} ({q['raison']})",
              flush=True)
    return rec


# --------------------------------------------------------------------------- calage complet
def combiner(pid, rec_auto, entree, p_depart, sigma):
    """Ajustement final commun : observations automatiques inliers de poses.caler (GCP du catalogue
    gcp.py) + pointages visuels nommés (levé GAM 2026), LM robuste et sélection des inliers (seuils de
    poses.py), qualité et acceptation par poses._qualite. Renvoie (pose (6,), qualite dict)."""
    import poses as PS
    ph = photo(pid)
    intr = intrinseques(ph)
    p_brut = pose_brute(ph)["pose"].copy()
    cat = G.gcp_par_id()
    gidx, obs = {}, []
    for o in (rec_auto or {}).get("observations", []):
        if not o.get("inlier"):
            continue
        g = cat.get(o["gcp"])
        if g is None:
            continue
        gidx[g["id"]] = g
        obs.append({k: v for k, v in o.items() if k not in ("residu_deg", "residu_px", "inlier", "gcp_def")})
    for o in (entree or {}).get("observations", []):
        g = gcp_reference(o["ref"], o.get("hauteur_m"))
        gidx[g["id"]] = g
        if "uvs" in o:
            obs.append(dict(gcp=g["id"], type="ligne", uv=[list(map(float, x)) for x in o["uvs"]], poids=1.0,
                            pointage="visuel", note=o.get("note", "")))
        else:
            obs.append(dict(gcp=g["id"], type="point", uv=list(map(float, o["uv"])), poids=1.0,
                            pointage="visuel", note=o.get("note", "")))
    if len(obs) < 4:
        return None, None
    aj = PS.Ajustement(ph, intr, np.asarray(p_depart, float), sigma, obs, gidx, focale_libre=False)
    p = aj.lm(np.asarray(p_depart, float), n_iter=60)
    inl = aj.erreurs_groupes(p) < aj.taus()
    for _ in range(3):
        p = aj.lm(p, *aj.poids_inliers(inl), n_iter=40)
        inl = aj.erreurs_groupes(p) < aj.taus()
    q = PS._qualite(ph, aj, p, inl, p_brut, intr, gidx)
    for o in q["observations"]:                     # définitions des GCP nommés (planches, requalification)
        g = gidx.get(o["gcp"])
        if g is not None and ":" in o["gcp"]:
            o["gcp_def"] = {k: g[k] for k in ("point", "pied", "sommet", "sigma_m", "source", "type") if k in g}
    q["n_obs_auto"] = sum(1 for o in obs if o.get("pointage") != "visuel")
    q["n_obs_visuel"] = sum(1 for o in obs if o.get("pointage") == "visuel")
    q["gcp_defs_visuels"] = {k: {kk: g[kk] for kk in ("point", "pied", "sommet", "sigma_m", "source") if kk in g}
                             for k, g in gidx.items() if ":" in k}
    return p[:6], q


def _caler_un(args):
    """Chaîne par photo : pose grossière (résection sur pointages visuels si présents, sinon contraste
    des marquages), poses.caler avec cet a priori, puis ajustement commun (auto + visuel)."""
    pid, sortie, lacet0, source_lacet, entree = args
    import poses as PS
    sortie = Path(sortie)
    PS.PAR_PHOTO = sortie / "par_photo"            # n'écrit pas dans enrichi/poses/
    ph = photo(pid)
    if entree and entree.get("observations"):
        gr = resection(pid, entree)
        gr["source_lacet_depart"] = entree.get("source_lacet", "")
        sig = dict(xy=0.6, z=0.3, lacet=1.5, tangage=1.5, roulis=1.5)
    else:
        gr = pose_grossiere(pid, lacet0)
        gr["source_lacet_depart"] = source_lacet
        sig = dict(xy=1.0, z=0.3, lacet=2.0, tangage=1.5, roulis=1.5)
    ecrire_json(sortie / "grossier" / f"{ph.id8}.json", gr)
    ap = a_priori(ph, gr, sig_xy=sig["xy"], sig_lacet=sig["lacet"])
    rec = PS.caler(pid, verbeux=True, a_priori=ap)
    rec["pose_grossiere"] = {k: v for k, v in gr.items() if k not in ("observations", "gcp")}
    rec["calage_automatique"] = dict(accepte=rec.get("accepte"), raison=rec.get("raison"), pose=rec.get("pose"),
                                    qualite=rec.get("qualite"))
    if entree and entree.get("observations"):
        q0 = rec.get("pose")
        depart = ([q0["x"], q0["y"], q0["z"], q0["lacet"], q0["tangage"], q0["roulis"]] if q0 else gr["pose"])
        p, q = combiner(pid, rec, entree, depart, sig)
        if p is not None:
            rec.update(q)
            rec["pose"] = {k: round(float(v), 4) for k, v in zip(("x", "y", "z", "lacet", "tangage", "roulis"),
                                                                 [p[0], p[1], p[2], p[3] % 360.0, p[4], p[5]])}
            rec["methode_finale"] = "ajustement commun : GCP pointés automatiquement + pointages visuels GAM 2026"
    if entree and entree.get("refus"):                # ambiguïté constatée à la relecture : pose approchée seulement
        rec["accepte"] = False
        rec["raison"] = "refus après relecture : " + entree["refus"]
    PS._ecrire(rec)
    q = rec.get("qualite") or {}
    return ph.id8, rec.get("accepte"), rec.get("raison"), q.get("residu_moy_deg"), q.get("n_gcp")


def assembler(sortie, date=None):
    """par_photo/*.json -> poses_<date>.json (en-tête + photos, format de poses.json)."""
    sortie = Path(sortie)
    recs = [lire_json(f) for f in sorted((sortie / "par_photo").glob("*.json"))]
    if date:
        recs = [r for r in recs if r.get("date") == date]
    # cohérence de séquence (même monture) : hauteur d'objectif et assiette des poses acceptées
    ok = [r for r in recs if r.get("accepte") and r.get("qualite")]
    if len(ok) >= 3:
        med = {k: float(np.median([r["qualite"]["hauteur_sol_m"] if k == "h" else r["pose"][k] for r in ok]))
               for k in ("h", "tangage", "roulis")}
        for r in ok:
            dh = abs(r["qualite"]["hauteur_sol_m"] - med["h"])
            da = max(abs(r["pose"]["tangage"] - med["tangage"]), abs(r["pose"]["roulis"] - med["roulis"]))
            r["coherence_sequence"] = dict(ecart_hauteur_m=round(dh, 3), ecart_assiette_deg=round(da, 2),
                                           mediane=dict((k, round(v, 3)) for k, v in med.items()))
            if dh > 0.3 or da > 3.0:
                r["accepte"] = False
                r["raison"] = "incohérent avec la séquence (hauteur d'objectif ou assiette)"
    photos = [{k: v for k, v in r.items() if k not in ("observations", "duree_s")} for r in recs]
    n_ok = sum(1 for r in recs if r.get("accepte"))
    out = dict(schema=SCHEMA, generateur="recon/pcg/enrichir/calage_sequence.py",
               repere="local = Lambert-93 − O (917279.43, 6460289.98), z = NGF − 216,30",
               convention_pose="identique à enrichi/poses/poses.json (lacet grille, tangage, roulis)",
               methode="pose grossière par contraste des marquages valides à la date (lacet de départ visuel ou "
                       "360°), puis poses.caler (GCP datés : coins de bandes de zébra, coins et axes de "
                       "marquages, mâts ; vote, RANSAC + LM)",
               criteres="ceux de poses.py : résidu moyen ≤ 0,5° (360°), ≥ 6 contraintes indépendantes, "
                        "leave-one-out ≤ 1°, ≥ 2 secteurs de 45° ou profondeur, écart GNSS ≤ 3·préc + 1 m",
               n_photos=len(recs), n_acceptees=n_ok, photos=photos)
    ecrire_json(sortie / f"poses_{date or 'sequence'}.json", out)
    print(f"poses_{date or 'sequence'}.json : {len(recs)} photos, {n_ok} acceptées")
    return out


def camera_sequence(pid, fichier_poses, accepte_seulement=True):
    """Camera à la pose calée par ce module (fichier poses_<date>.json) : (camera, statut)."""
    ph = photo(pid)
    d = lire_json(fichier_poses)
    p = next((x for x in d["photos"] if x["id8"] == ph.id8), None)
    if p and p.get("pose") and (p.get("accepte") or not accepte_seulement):
        q = p["pose"]
        intr = {**intrinseques(ph), **{k: v for k, v in (p.get("intrinseques") or {}).items()
                                         if k in ("f", "cx", "cy", "k1")}}
        return camera(ph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]], intr), \
            ("calee" if p.get("accepte") else "calee_refusee")
    return camera(ph), "brute"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", default=None)
    ap.add_argument("--photos", nargs="*")
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--lacets", default=None, help="JSON {id8: {lacet, source}} : lacets de départ relevés")
    ap.add_argument("--pointages", default=None, help="JSON {id8: {lacet_depart, observations}} : pointages visuels")
    ap.add_argument("--proc", type=int, default=1)
    ap.add_argument("--grossier-seul", action="store_true")
    ap.add_argument("--assembler", action="store_true")
    ap.add_argument("--planches", action="store_true")
    a = ap.parse_args(argv)
    sortie = Path(a.sortie)
    ids = [photo(p).id8 for p in a.photos] if a.photos else \
        sorted(k for k, ph in catalogue().items() if a.date and ph.date == a.date)
    lacets = lire_json(a.lacets) if a.lacets else {}
    pointages = lire_json(a.pointages) if a.pointages else {}
    args = [(pid, str(sortie), (lacets.get(pid) or {}).get("lacet"), (lacets.get(pid) or {}).get("source", "360°"),
             pointages.get(pid)) for pid in ids]
    if a.grossier_seul:
        for pid, _, l0, src, _e in args:
            g = pose_grossiere(pid, l0)
            g["source_lacet_depart"] = src
            ecrire_json(sortie / "grossier" / f"{pid}.json", g)
        return None
    if ids and not a.assembler:
        if a.proc > 1:
            from multiprocessing import Pool
            with Pool(a.proc) as pool:
                res = pool.map(_caler_un, args)
        else:
            res = [_caler_un(x) for x in args]
        for r in res:
            print(r)
    out = assembler(sortie, a.date)
    if a.planches:
        import planche as PL
        (sortie / "planches").mkdir(parents=True, exist_ok=True)
        for f in sorted((sortie / "par_photo").glob("*.json")):
            rec = lire_json(f)
            if rec.get("pose") and (not a.date or rec.get("date") == a.date):
                PL.planche_controle(rec, chemin=sortie / "planches" / f"controle_{rec['id8']}.jpg")
    return out


if __name__ == "__main__":
    main()
