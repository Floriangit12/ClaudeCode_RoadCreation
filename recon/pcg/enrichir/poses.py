"""Calage des poses des photos Panoramax par points d'appui (GCP) : vote grossier puis RANSAC + LM.

Étapes par photo :
1. pose brute (GNSS -> Lambert-93 -> local, lacet = azimut + gamma, z = MNT 2026 + h a priori) ;
2. recalage grossier (x, y, lacet) par vote sur les mâts : chaque mât/tronc donne un profil
   d'évidence de barre verticale en fonction de l'azimut ; on cherche la translation et la
   rotation qui alignent le plus de mâts (insensible à la hauteur, au tangage et au roulis) ;
3. trois passes « pointer puis ajuster » à fenêtres décroissantes : mâts (axe), coins de bandes
   de passages piétons et points texturés de l'ortho 2022 (corrélation avec l'ortho drapée) ;
   ajustement 6 ddl (x, y, z, lacet, tangage, roulis [+ focale pour les photos à plat sans
   métadonnée]) par moindres carrés robustes (Huber) sur les erreurs ANGULAIRES, avec a priori
   (GNSS, hauteur, assiette) ; RANSAC sur les GCP à la première passe ;
4. qualité : n GCP, résidus moyen/max (deg et px), écart au GNSS, correction de lacet ;
   acceptation si moyenne ≤ 0,5° (360°) ou ≤ 8 px (à plat), avec au moins 6 GCP inliers dont
   4 points au sol ou 6 mâts (et 2 secteurs de 45° en 360°).

Sorties : recon/out/paquet_jardin/v2/enrichi/poses/{par_photo/<id8>.json, poses.json, gcp.json}.
Usage : python poses.py [--cibles | --toutes | --photos id8 ...] [--planches] [--assembler]
"""
import argparse
import json
import math
import sys
import time

import numpy as np

from camera import (CENTRE, SORTIE, arrondi, camera, catalogue, ecrire_json, image_gris,
                    intrinseques, lire_json, matrice_rotation, photo, pose_brute)
import gcp as G

SCHEMA = "pj_poses_panoramax/0.1"
PAR_PHOTO = SORTIE / "par_photo"
SEUIL_360_DEG = 0.5
SEUIL_PLAT_PX = 8.0
TANGAGES_PLAT_GRILLE = (-8.0, -5.0, -2.0, 1.0, 4.0, 7.0)
VOTE = True              # vote en espace de pose avant la première passe RANSAC
HORIZON_NCC_MIN = 0.12   # corrélation minimale du paysage lointain avec la 360° de référence
TANGAGES_PLAT = {}       # date -> tangages calés de la série (a priori de séquence, rempli en 2e passe)
FORCE_MIN = 4.0          # réponse de barre (35e centile, rapportée au fond de chaque ligne)
COHERENCE_MIN = 0.65     # part des lignes de la bande où le mât répond


# --------------------------------------------------------------------------- sélection des photos
def cibles():
    """Photos 360° à moins de 60 m du centre + série à plat du 2025-08-31."""
    out = []
    for pid, ph in catalogue().items():
        xy = pose_brute(ph)["pose"][:2]
        d = float(np.hypot(*(xy - CENTRE)))
        if (ph.is360 and d < 60) or ph.date == "2025-08-31":
            out.append(pid)
    return sorted(out)


# --------------------------------------------------------------------------- vote grossier
def recalage_grossier(ph, cam0, img, mats, R, Y, pas=0.08, n_hyp=3):
    """Vote (dx, dy, dlacet) sur les mâts : maximise la somme des évidences de barre aux azimuts
    prédits. R : demi-étendue en position (m), Y : demi-étendue en lacet (deg).
    Renvoie jusqu'à n_hyp hypothèses distinctes [dict(dx, dy, dlacet, score, n)], la meilleure d'abord."""
    C0 = cam0.C
    prof = []
    pxdeg = cam0.px_par_rad * math.pi / 180
    for g in mats:
        P0 = np.array(g["pied"])
        d0 = math.hypot(P0[0] - C0[0], P0[1] - C0[1])
        if d0 < 1.6 * R + 2.0 or d0 > 42:
            continue
        if math.degrees(g["diametre_m"] / d0) * pxdeg < 1.2:
            continue
        az0 = math.degrees(math.atan2(P0[0] - C0[0], P0[1] - C0[1]))
        dA = math.degrees(math.asin(min(1.0, 1.42 * R / d0))) + Y + 1.0
        el0, el1 = G.bande_elevation(cam0, g, d0 - 1.42 * R, d0 + 1.42 * R, G.lat_min_cam(ph))
        if el1 - el0 < G.BANDE_MIN_DEG:
            continue
        diam = math.degrees(g["diametre_m"] / d0)
        A, S, _ = G.profil_barre(cam0, img, az0 - dA, az0 + dA, el0, el1, diam, pas)
        if np.count_nonzero(S > 0) < 20:
            continue
        ev = np.clip((S - 2.0) / 10.0, 0, 1)
        if ev.max() <= 0:
            continue
        ev = np.max(np.stack([np.roll(ev, k) for k in (-2, -1, 0, 1, 2)]), axis=0)
        w = g["poids"] * min(1.0, (el1 - el0) / 8.0)
        prof.append((g, P0, A[0], ev, w))
    if len(prof) < 3:
        return []
    st = 0.25 if R <= 2.5 else 0.5
    grille = np.arange(-R, R + 1e-9, st)
    deltas = np.arange(-Y, Y + 1e-9, pas)
    sw = sum(p[4] for p in prof)
    sig_xy = max(R / 2.5, 0.5)
    cellules = []
    for dx in grille:
        for dy in grille:
            tot = np.zeros(len(deltas))
            for g, P0, a0, ev, w in prof:
                az = math.degrees(math.atan2(P0[0] - C0[0] - dx, P0[1] - C0[1] - dy))
                az = a0 + ((az - a0) % 360.0)
                idx = np.round((az - deltas - a0) / pas).astype(int)
                okk = (idx >= 0) & (idx < len(ev))
                tot += w * np.where(okk, ev[np.clip(idx, 0, len(ev) - 1)], 0.0)
            tot -= 0.05 * sw * ((dx * dx + dy * dy) / sig_xy ** 2 + (deltas / max(Y / 2.5, 1.0)) ** 2) / 2
            k = int(np.argmax(tot))
            cellules.append((float(tot[k]), float(dx), float(dy), float(deltas[k])))
    cellules.sort(key=lambda c: -c[0])
    hyp = []
    for s, dx, dy, dl in cellules:
        if all(math.hypot(dx - h["dx"], dy - h["dy"]) > 1.0 or abs(dl - h["dlacet"]) > 1.5 for h in hyp):
            hyp.append(dict(dx=dx, dy=dy, dlacet=dl, score=s / sw, n=len(prof)))
        if len(hyp) >= n_hyp:
            break
    return hyp


# --------------------------------------------------------------------------- recalage global au sol
def recalage_sol(ph, cam, img, tangage_max=10.0, roulis_max=6.0, dz_max=0.6, dlacet_max=3.0,
                 reduction=8):
    """Assiette (tangage, roulis), hauteur et lacet par corrélation globale entre la photo
    (réduite, passe-haut) et l'ortho 2022 drapée sur le MNT rendue dans la même vue.
    Descente par coordonnées sur une grille ; renvoie (pose, ncc)."""
    from projection import intersection_sol, ortho_valeur
    H, W = img.shape
    hr, wr = H // reduction, W // reduction
    petit = img[: hr * reduction, : wr * reduction].reshape(hr, reduction, wr, reduction).mean((1, 3))
    jj, ii = np.mgrid[0:hr, 0:wr]
    uv = np.c_[(ii.ravel() + 0.5) * reduction, (jj.ravel() + 0.5) * reduction]
    ph_hp = G.passe_haut(petit, 3).ravel()
    lat_min = G.lat_min_cam(ph)

    def score(p):
        c = camera(ph, p[:6], dict(intrinseques(ph), f=cam.f) if cam.modele == "stenope" else None)
        bc = c.pixel_vers_cam(uv)
        lat = np.degrees(np.arcsin(np.clip(bc[:, 2], -1, 1)))
        d = bc @ c.R
        t = intersection_sol(c.C, d, n_iter=2)
        dist = t * np.hypot(d[:, 0], d[:, 1])
        ok = np.isfinite(t) & (dist > 2.5) & (dist < 25) & (lat > lat_min + 1.0)
        if ok.sum() < 200:
            return -1.0
        X = c.C + np.nan_to_num(t)[:, None] * d
        v = np.where(ok, ortho_valeur(X[:, 0], X[:, 1]), np.nan)
        ok &= np.isfinite(v)
        img_r = np.where(ok, v, np.nanmean(v[ok]) if ok.any() else 0).reshape(hr, wr)
        r_hp = G.passe_haut(img_r, 3).ravel()
        a, b = ph_hp[ok], r_hp[ok]
        a = a - a.mean()
        b = b - b.mean()
        return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))

    p = np.array(cam.pose, float)
    s0 = score(p)
    best = s0
    grilles = [(4, np.arange(-tangage_max, tangage_max + 1e-9, 1.0)),
               (5, np.arange(-roulis_max, roulis_max + 1e-9, 1.0)),
               (2, np.arange(-dz_max, dz_max + 1e-9, 0.15)),
               (3, np.arange(-dlacet_max, dlacet_max + 1e-9, 0.5))]
    for tour in range(2):
        for j, g in grilles:
            base = cam.pose[j] if tour == 0 else p[j]
            vals = (base + g) if tour == 0 else (p[j] + g / 4)
            sc = []
            for v in vals:
                q = p.copy()
                q[j] = v
                sc.append(score(q))
            k = int(np.argmax(sc))
            if sc[k] > best:
                best = sc[k]
                p[j] = vals[k]
    return p, best, s0


# --------------------------------------------------------------------------- a priori de séquence
def a_priori_sequence(ph, p_brut, n_voisins=4):
    """Pose a priori tirée des photos ACCEPTÉES de la même séquence les plus proches dans le temps :
    même monture (biais de lacet), même GNSS (décalage le long / en travers de la marche).
    Renvoie dict(pose, sigma, voisins) ou None (moins de 2 voisins)."""
    from datetime import datetime
    t = datetime.fromisoformat(ph.datetime)
    vs = []
    for f in sorted(PAR_PHOTO.glob("*.json")):
        r = lire_json(f)
        if (not r.get("accepte") or r.get("date") != ph.date or r["id8"] == ph.id8
                or not r.get("pose") or r.get("source_pose") == "a_priori_sequence"):
            continue
        dt = abs((datetime.fromisoformat(r["datetime"]) - t).total_seconds())
        vs.append((dt, r))
    if len(vs) < 2:
        return None
    vs.sort(key=lambda x: (x[0], x[1]["id8"]))
    vs = vs[:n_voisins]
    dl, av, tr, tg, rl, dz = [], [], [], [], [], []
    for _, r in vs:
        a, b = r["pose"], r["pose_brute"]
        cap = math.radians(b["lacet"])
        ex, ey = a["x"] - b["x"], a["y"] - b["y"]
        av.append(ex * math.sin(cap) + ey * math.cos(cap))
        tr.append(ex * math.cos(cap) - ey * math.sin(cap))
        dl.append(((a["lacet"] - b["lacet"] + 180) % 360) - 180)
        tg.append(a["tangage"])
        rl.append(a["roulis"])
        dz.append(r["qualite"]["hauteur_sol_m"])
    med = {k: float(np.median(v)) for k, v in dict(av=av, tr=tr, dl=dl, tg=tg, rl=rl, dz=dz).items()}
    disp = {k: float(np.median(np.abs(np.array(v) - med[k]))) * 1.4826
            for k, v in dict(av=av, tr=tr, dl=dl, tg=tg, rl=rl).items()}
    cap = math.radians(p_brut[3])
    q = p_brut.copy()
    q[0] += med["av"] * math.sin(cap) + med["tr"] * math.cos(cap)
    q[1] += med["av"] * math.cos(cap) - med["tr"] * math.sin(cap)
    q[3] += med["dl"]
    q[4], q[5] = med["tg"], med["rl"]
    from camera import z_sol
    q[2] = z_sol(q[0], q[1]) + med["dz"]
    acc = float(ph.meta.get("horizontal_accuracy_m") or 5.0)
    sigma = dict(xy=float(np.clip(max(2 * max(disp["av"], disp["tr"]), 0.5), 0.5, max(acc, 1.0))),
                 z=0.3, lacet=float(np.clip(2 * disp["dl"], 1.5, 6.0)),
                 tangage=float(np.clip(2 * disp["tg"], 1.0, 4.0)), roulis=float(np.clip(2 * disp["rl"], 1.0, 3.0)))
    return dict(pose=q, sigma=sigma, voisins=[r["id8"] for _, r in vs],
                decalage=dict(long_m=med["av"], travers_m=med["tr"], lacet_deg=med["dl"],
                              tangage_deg=med["tg"], roulis_deg=med["rl"], hauteur_m=med["dz"]))


# --------------------------------------------------------------------------- orientation par l'horizon
def reference_360(ph, p_brut, dmax=120.0):
    """Photo 360° déjà calée et acceptée la plus proche (par_photo/*.json) : (rec, distance) ou None."""
    meilleur = None
    for f in sorted(PAR_PHOTO.glob("*.json")):
        r = lire_json(f)
        if not r.get("accepte") or r.get("modele") != "equirect" or not r.get("pose"):
            continue
        d = float(np.hypot(r["pose"]["x"] - p_brut[0], r["pose"]["y"] - p_brut[1]))
        if d <= dmax and (meilleur is None or d < meilleur[1]):
            meilleur = (r, d)
    return meilleur


def orientation_par_horizon(ph, intr, p_brut, img, ref, pas=0.2):
    """Lacet, tangage et roulis d'une photo à plat par corrélation de son paysage lointain
    (montagnes, bâtiments, lignes d'arbres : parallaxe négligeable) avec une photo 360° calée,
    dans une grille (azimut, élévation) du repère local : le lacet n'y est qu'un décalage de
    colonnes. Renvoie (pose, ncc)."""
    q = ref["pose"]
    rph = photo(ref["id8"])
    rcam = camera(rph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]])
    from projection import fenetre_azel
    hf = math.degrees(math.atan2(intr["W"] / 2, intr["f"]))
    az0, az1 = p_brut[3] - hf - 16, p_brut[3] + hf + 16
    el0, el1 = -4.0, 24.0
    Rv, _, _, okr = fenetre_azel(rcam, G._flou_boite(image_gris(rph.id8), 2), az0, az1, el0, el1, pas)

    def grad(V):
        gy, gx = np.gradient(V)
        return np.hypot(gx, gy)

    Rg = grad(Rv)
    Rg = Rg / (np.percentile(Rg, 99) + 1e-6)
    fl = G._flou_boite(img, 4)
    nmax = int(round(15.0 / pas))

    def evaluer(tg, rl, decalages):
        c = camera(ph, [p_brut[0], p_brut[1], p_brut[2], p_brut[3], tg, rl], intr)
        F, _, _, ok = fenetre_azel(c, fl, az0, az1, el0, el1, pas)
        if ok.sum() < 5000:
            return []
        Fg = grad(F)
        Fg = Fg / (np.percentile(Fg[ok], 99) + 1e-6)
        ok = ok & np.roll(ok, 1, 1) & np.roll(ok, -1, 1) & np.roll(ok, 1, 0) & np.roll(ok, -1, 0)
        out = []
        for s in decalages:
            Fs = np.roll(Fg, s, axis=1)
            ms = np.roll(ok, s, axis=1).copy()
            if s > 0:
                ms[:, :s] = False
            elif s < 0:
                ms[:, s:] = False
            a, b = Fs[ms], Rg[ms]
            if a.size < 5000:
                continue
            a = a - a.mean()
            b = b - b.mean()
            out.append((float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12)), tg, rl, s))
        return out

    res = []
    for tg in np.arange(-8.0, 8.01, 1.0):
        for rl in np.arange(-4.0, 4.01, 1.0):
            res += evaluer(tg, rl, range(-nmax, nmax + 1))
    if not res:
        return None, 0.0
    v, tg0, rl0, s0 = max(res)
    res = []
    for tg in np.arange(tg0 - 0.75, tg0 + 0.76, 0.25):
        for rl in np.arange(rl0 - 0.75, rl0 + 0.76, 0.25):
            res += evaluer(tg, rl, range(s0 - 5, s0 + 6))
    v, tg, rl, s = max(res)
    p = p_brut.copy()
    p[3] = p_brut[3] - s * pas
    p[4], p[5] = tg, rl
    return p, v


# --------------------------------------------------------------------------- problème d'ajustement
class Ajustement:
    """Moindres carrés robustes sur erreurs angulaires + a priori. Paramètres :
    [x, y, z, lacet, tangage, roulis] (+ f pour les photos à plat si `focale_libre`)."""

    def __init__(self, ph, intr, pose0, sigma, obs, gcps, focale_libre=False, sig_det_deg=None):
        self.ph, self.intr = ph, dict(intr)
        self.p0 = np.asarray(pose0, float)
        self.sigma = sigma
        self.focale_libre = focale_libre and intr["modele"] == "stenope"
        self.f0 = intr["f"]
        self.obs = obs
        if sig_det_deg is None:
            sig_det_deg = 0.08 if ph.is360 else math.degrees(1.5 / intr["f"])
        self.sig_det = math.radians(sig_det_deg)
        lignes, points = [], []
        for k, o in enumerate(obs):
            g = gcps[o["gcp"]]
            if o["type"] == "ligne":
                for uv in o["uv"]:
                    lignes.append((k, uv, g["pied"], g["sommet"], g))
            else:
                points.append((k, o["uv"], g["point"], g))
        self.lignes, self.points = lignes, points
        self.n_par = 7 if self.focale_libre else 6
        # écarts types angulaires par ligne d'observation (détection + position du GCP)
        self.sig_l = np.array([self._sig(g, A) for (_, _, A, _, g) in lignes])
        self.sig_p = np.array([self._sig(g, P) for (_, _, P, g) in points])
        self.LA = np.array([l[2] for l in lignes], float).reshape(-1, 3)
        self.LB = np.array([l[3] for l in lignes], float).reshape(-1, 3)
        self.Luv = np.array([l[1] for l in lignes], float).reshape(-1, 2)
        self.PP = np.array([p[2] for p in points], float).reshape(-1, 3)
        self.Puv = np.array([p[1] for p in points], float).reshape(-1, 2)
        self.obs_l = np.array([l[0] for l in lignes], int)
        self.obs_p = np.array([p[0] for p in points], int)

    def _sig(self, g, P):
        d = max(float(np.hypot(*(np.asarray(P)[:2] - self.p0[:2]))), 1.0)
        return math.hypot(self.sig_det, g["sigma_m"] / d)

    def camera(self, p):
        intr = dict(self.intr)
        if self.focale_libre:
            intr["f"] = p[6]
        return camera(self.ph, p[:6], intr)

    def residus_obs(self, p):
        """Résidus angulaires (rad) : lignes (nl,), points (np, 2)."""
        cam = self.camera(p)
        R, C = cam.R, cam.C
        rl = np.zeros(len(self.LA))
        if len(self.LA):
            b = cam.pixel_vers_cam(self.Luv)
            n = np.cross(self.LA - C, self.LB - C)
            n /= np.linalg.norm(n, axis=1, keepdims=True)
            nc = n @ R.T
            rl = np.arcsin(np.clip(np.sum(nc * b, axis=1), -1, 1))
        rp = np.zeros((len(self.PP), 2))
        if len(self.PP):
            b = cam.pixel_vers_cam(self.Puv)
            q = (self.PP - C) @ R.T
            q /= np.linalg.norm(q, axis=1, keepdims=True)
            haut = np.array([0.0, 0.0, 1.0])
            e1 = np.cross(b, haut)
            nn = np.linalg.norm(e1, axis=1, keepdims=True)
            e1 = np.where(nn > 1e-6, e1 / np.maximum(nn, 1e-12), np.array([1.0, 0, 0]))
            e2 = np.cross(e1, b)
            # angle exact entre b et q, réparti sur la base tangente
            dq = q - b * np.sum(q * b, axis=1, keepdims=True)
            ang = np.arctan2(np.linalg.norm(np.cross(b, q), axis=1), np.sum(b * q, axis=1))
            nd = np.linalg.norm(dq, axis=1)
            fac = np.where(nd > 1e-12, ang / np.maximum(nd, 1e-12), 1.0)
            rp = np.c_[np.sum(dq * e1, 1) * fac, np.sum(dq * e2, 1) * fac]
        return rl, rp

    def vecteur(self, p, wl, wp):
        rl, rp = self.residus_obs(p)
        s = self.sigma
        pri = [(p[0] - self.p0[0]) / s["xy"], (p[1] - self.p0[1]) / s["xy"], (p[2] - self.p0[2]) / s["z"],
               (((p[3] - self.p0[3] + 180) % 360) - 180) / s["lacet"],
               (p[4] - self.p0[4]) / s["tangage"], (p[5] - self.p0[5]) / s["roulis"]]
        if self.focale_libre:
            pri.append((p[6] - self.f0) / (self.f0 * s.get("focale_rel", 0.12)))
        return np.r_[rl / self.sig_l * np.sqrt(wl), (rp / self.sig_p[:, None] * np.sqrt(wp)[:, None]).ravel(), pri]

    def lm(self, p, wl=None, wp=None, n_iter=25, huber=2.0):
        """Levenberg-Marquardt avec repondération de Huber (IRLS)."""
        p = np.array(p, float)
        if self.focale_libre and len(p) == 6:
            p = np.r_[p, self.f0]
        wl0 = np.ones(len(self.LA)) if wl is None else np.asarray(wl, float)
        wp0 = np.ones(len(self.PP)) if wp is None else np.asarray(wp, float)
        pas = np.array([1e-3, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3, 0.5])[: self.n_par]
        lam = 1e-3
        for it in range(n_iter):
            rl, rp = self.residus_obs(p)
            hl = np.abs(rl) / self.sig_l
            hp = np.linalg.norm(rp, axis=1) / self.sig_p
            wl = wl0 * np.where(hl <= huber, 1.0, huber / np.maximum(hl, 1e-9))
            wp = wp0 * np.where(hp <= huber, 1.0, huber / np.maximum(hp, 1e-9))
            r = self.vecteur(p, wl, wp)
            J = np.empty((len(r), self.n_par))
            for j in range(self.n_par):
                q = p.copy()
                q[j] += pas[j]
                J[:, j] = (self.vecteur(q, wl, wp) - r) / pas[j]
            A = J.T @ J
            g = J.T @ r
            c0 = r @ r
            ok = False
            for _ in range(8):
                dp = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
                q = p + dp
                c1 = self.vecteur(q, wl, wp) @ self.vecteur(q, wl, wp)
                if c1 < c0:
                    p, lam, ok = q, max(lam / 3, 1e-7), True
                    break
                lam *= 5
            if not ok or np.max(np.abs(dp[:6])) < 1e-5:
                break
        self._J, self._r = J, r
        return p

    def covariance(self, p):
        """Covariance a posteriori des paramètres (à partir du dernier jacobien)."""
        J, r = self._J, self._r
        dof = max(len(r) - self.n_par, 1)
        s2 = max(float(r @ r) / dof, 1.0)
        try:
            return np.linalg.inv(J.T @ J) * s2
        except np.linalg.LinAlgError:
            return np.full((self.n_par, self.n_par), np.nan)

    def erreurs_groupes(self, p):
        """Erreur angulaire (deg) par observation (max sur ses lignes / norme du point)."""
        rl, rp = self.residus_obs(p)
        err = np.zeros(len(self.obs))
        for k, e in zip(self.obs_l, np.abs(rl)):
            err[k] = max(err[k], e)
        for k, e in zip(self.obs_p, np.linalg.norm(rp, axis=1)):
            err[k] = max(err[k], e)
        return np.degrees(err)

    def sig_groupes(self):
        s = np.zeros(len(self.obs))
        for k, v in zip(self.obs_l, self.sig_l):
            s[k] = max(s[k], v)
        for k, v in zip(self.obs_p, self.sig_p):
            s[k] = max(s[k], v)
        return np.degrees(s)

    def taus(self):
        """Seuils d'inlier (deg) par observation : 3 σ bornés (0,25–0,6° en 360°, 6–15 px à plat)."""
        sig = self.sig_groupes()
        if self.ph.is360:
            lo, hi = 0.25, 0.6
        else:
            lo, hi = math.degrees(6 / self.f0), math.degrees(15 / self.f0)
        return np.clip(3.0 * sig, lo, hi)

    def poids_inliers(self, inl):
        return inl[self.obs_l].astype(float), inl[self.obs_p].astype(float)


def ransac(aj, p_init, graine, n_iter=150):
    """RANSAC sur les observations (échantillons de 3), puis LM robuste sur les inliers."""
    n = len(aj.obs)
    tau = aj.taus()
    poids = np.array([o.get("poids", 1.0) for o in aj.obs])
    rng = np.random.default_rng(graine)
    meilleur = (-1.0, None, None)
    if n < 4:
        p = aj.lm(p_init)
        e = aj.erreurs_groupes(p)
        return p, e < tau
    # premier essai : toutes les observations, robuste
    candidats = [None] + [rng.choice(n, size=3, replace=False) for _ in range(n_iter)]
    for ech in candidats:
        if ech is None:
            p = aj.lm(p_init, n_iter=15)
        else:
            m = np.zeros(n, bool)
            m[ech] = True
            wl, wp = aj.poids_inliers(m)
            p = aj.lm(p_init, wl, wp, n_iter=8)
        e = aj.erreurs_groupes(p)
        inl = e < tau
        sc = float(poids[inl].sum() - 0.01 * np.sum(np.minimum(e, tau) / tau))
        if sc > meilleur[0]:
            meilleur = (sc, p, inl)
    _, p, inl = meilleur
    for _ in range(3):
        wl, wp = aj.poids_inliers(inl)
        p = aj.lm(p, wl, wp, n_iter=25)
        e = aj.erreurs_groupes(p)
        inl2 = e < tau
        if np.array_equal(inl2, inl):
            break
        inl = inl2
    return p, inl


# --------------------------------------------------------------------------- vote en espace de pose
class VotePose:
    """Vote dans l'espace des poses autour d'une pose de départ.

    Chaque point de sol fournit sa carte NCC (photo / rendu de l'ortho) calculée UNE fois à la pose
    de départ, dans une vue virtuelle fixe ; chaque mât fournit son profil d'évidence de barre en
    azimut. Pour une pose candidate, la position prédite de chaque point dans sa vue virtuelle est
    calculée analytiquement et la carte y est lue (bilinéaire) ; le score est la somme des NCC
    positives et des évidences de mâts. Robuste aux motifs répétitifs (zébras) : seule la pose qui
    aligne simultanément la plupart des points obtient un fort score."""

    def __init__(self, ph, intr, cam, img_src, sols, S, ech, mats_prof=None, sig_xy=1.0, sig_y=3.0):
        self.ph, self.intr, self.cam0 = ph, intr, cam
        self.S = S
        self.sig_xy, self.sig_y = sig_xy, sig_y
        P, cartes, B, fv, w = [], [], [], [], []
        Rr = cam.R
        for g in sols:
            o = G.apparier_sol(ph, cam, img_src, g, S, echelle=ech, carte=True)
            if o is None or "carte" not in o:
                continue
            cv = o["vue"]
            P.append(g["point"])
            cartes.append(np.maximum(o["carte"], 0.0))
            B.append(Rr @ cv.R.T)        # c (repère photo) -> repère de la vue virtuelle
            fv.append((cv.f, cv.cx, cv.cy))
            w.append(g["poids"])
        self.n = len(P)
        self.P = np.array(P, float).reshape(-1, 3)
        self.cartes = np.array(cartes, float) if cartes else np.zeros((0, 2 * S + 1, 2 * S + 1))
        self.B = np.array(B, float).reshape(-1, 3, 3)
        self.fv = np.array(fv, float).reshape(-1, 3)
        self.w = np.array(w, float)
        self.mats = mats_prof or []
        # pénalité d'a priori : 0,5 « élément » par σ² d'écart au départ (évite la dérive sur bruit)
        self.lam = 0.02 * max(self.n + len(self.mats), 1) / 2

    def score_sol(self, C, R):
        """Scores (n_R,) pour un centre C et une pile de rotations R (n_R, 3, 3)."""
        if self.n == 0:
            return np.zeros(len(R))
        d = self.P - C                                   # (N, 3)
        c = np.einsum("rij,nj->rni", R, d)               # repère photo (n_R, N, 3)
        v = np.einsum("rni,nij->rnj", c, self.B)         # repère de la vue (n_R, N, 3)
        a = v[..., 1]
        ok = a > 1e-6
        a = np.where(ok, a, 1.0)
        f, cx, cy = self.fv[:, 0], self.fv[:, 1], self.fv[:, 2]
        u = cx + f * v[..., 0] / a
        vv = cy - f * v[..., 2] / a
        S = self.S
        ii = u - cx + S                                  # indices dans la carte (décalage + S)
        jj = vv - cy + S
        m = 2 * S
        ok &= (ii >= 0) & (ii <= m) & (jj >= 0) & (jj <= m)
        i0 = np.clip(np.floor(ii).astype(int), 0, m - 1)
        j0 = np.clip(np.floor(jj).astype(int), 0, m - 1)
        ti, tj = np.clip(ii - i0, 0, 1), np.clip(jj - j0, 0, 1)
        k = np.broadcast_to(np.arange(self.n), i0.shape)
        Cm = self.cartes
        val = ((Cm[k, j0, i0] * (1 - ti) + Cm[k, j0, i0 + 1] * ti) * (1 - tj)
               + (Cm[k, j0 + 1, i0] * (1 - ti) + Cm[k, j0 + 1, i0 + 1] * ti) * tj)
        return np.sum(np.where(ok, val, 0.0) * self.w, axis=1)

    def score_mats(self, C, dlac):
        """Évidence des mâts (n_lacets,) pour le centre C et des écarts de lacet dlac (deg)."""
        tot = np.zeros(len(dlac))
        for P0, a0, ev, w, pas in self.mats:
            az = math.degrees(math.atan2(P0[0] - C[0], P0[1] - C[1]))
            az = a0 + ((az - a0) % 360.0)
            idx = np.round((az - dlac - a0) / pas).astype(int)
            okk = (idx >= 0) & (idx < len(ev))
            tot += w * np.where(okk, ev[np.clip(idx, 0, len(ev) - 1)], 0.0)
        return tot

    def chercher(self, p0, R_xy, pas_xy, Y, pas_y, dz=0.45, assiette=2.0, pas_a=0.5, tours=2):
        """Recherche par blocs : (x, y, lacet) puis (z, tangage, roulis), deux tours (le 2e plus fin)."""
        p = np.array(p0, float)

        def sym(r, s):
            return s * np.arange(-int(round(r / s)), int(round(r / s)) + 1)

        for t in range(tours):
            best = -1.0
            r, sx = (R_xy, pas_xy) if t == 0 else (max(2 * pas_xy, 0.3), pas_xy / 2.5)
            yy, sy = (Y, pas_y) if t == 0 else (max(4 * pas_y, 0.3), pas_y / 2)
            grille = sym(r, sx)
            dl = sym(yy, sy)
            Rs = np.array([matrice_rotation(p[3] + d, p[4], p[5]) for d in dl])
            pen_l = self.lam * ((p[3] + dl - self.cam0.pose[3] + 180) % 360 - 180) ** 2 / self.sig_y ** 2
            for dx in grille:
                for dy in grille:
                    C = np.array([p[0] + dx, p[1] + dy, p[2]])
                    pen = self.lam * ((C[0] - self.cam0.pose[0]) ** 2 + (C[1] - self.cam0.pose[1]) ** 2) / self.sig_xy ** 2
                    sc = (self.score_sol(C, Rs) + self.score_mats(C, dl + (p[3] - self.cam0.pose[3]))
                          - pen - pen_l)
                    k = int(np.argmax(sc))
                    if sc[k] > best:
                        best, bx, by, bl = float(sc[k]), dx, dy, dl[k]
            p[0] += bx
            p[1] += by
            p[3] += bl
            if self.n:
                a_ = assiette if t == 0 else assiette / 3
                pa = pas_a if t == 0 else pas_a / 3
                zz = sym(dz, 0.15 if t == 0 else 0.05)
                tt = sym(a_, pa)
                best2 = -1.0
                for dzz in zz:
                    C = np.array([p[0], p[1], p[2] + dzz])
                    Rs, cles = [], []
                    for dt in tt:
                        for dr in tt:
                            Rs.append(matrice_rotation(p[3], p[4] + dt, p[5] + dr))
                            cles.append((dt, dr))
                    sc = self.score_sol(C, np.array(Rs))
                    k = int(np.argmax(sc))
                    if sc[k] > best2:
                        best2, bz, bt = float(sc[k]), dzz, cles[k]
                p[2] += bz
                p[4] += bt[0]
                p[5] += bt[1]
                dz = max(dz / 3, 0.1)
        sc = self.score_sol(p[:3], np.array([matrice_rotation(*p[3:6])]))[0]
        return p, float(sc + self.score_mats(p[:3], np.array([p[3] - self.cam0.pose[3]]))[0])


def profils_mats(ph, cam, img, mats, R, Y, pas=0.08):
    """Profils d'évidence de barre des mâts (pour VotePose) autour de la pose cam."""
    C0 = cam.C
    out = []
    pxdeg = cam.px_par_rad * math.pi / 180
    for g in mats:
        P0 = np.array(g["pied"])
        d0 = math.hypot(P0[0] - C0[0], P0[1] - C0[1])
        if d0 < 1.6 * R + 2.0 or d0 > 42 or math.degrees(g["diametre_m"] / d0) * pxdeg < 1.2:
            continue
        az0 = math.degrees(math.atan2(P0[0] - C0[0], P0[1] - C0[1]))
        dA = math.degrees(math.asin(min(1.0, 1.42 * R / d0))) + Y + 1.0
        el0, el1 = G.bande_elevation(cam, g, d0 - 1.42 * R, d0 + 1.42 * R, G.lat_min_cam(ph))
        if el1 - el0 < 3.0:
            continue
        A, S, _ = G.profil_barre(cam, img, az0 - dA, az0 + dA, el0, el1, math.degrees(g["diametre_m"] / d0), pas)
        if np.count_nonzero(S > 0) < 20:
            continue
        ev = np.clip((S - 2.0) / 10.0, 0, 1)
        if ev.max() <= 0:
            continue
        ev = np.max(np.stack([np.roll(ev, k) for k in (-2, -1, 0, 1, 2)]), axis=0)
        out.append((P0, A[0], ev, g["poids"] * min(1.0, (el1 - el0) / 8.0), pas))
    return out


# --------------------------------------------------------------------------- pointage
def pointer(ph, cam, img, img_flou, gcps_fixes, dyn_sol, fen_mat, rech_sol, echelle_sol, n_sol_max=140,
            consensus=False):
    """Observations automatiques de tous les GCP visibles à la pose `cam`."""
    obs = []
    for g in gcps_fixes:
        if g["famille"] in ("mat", "tronc"):
            o = G.detecter_mat(ph, cam, img, g, fen_mat(g))
            if o is None:
                continue
            if (o["force"] < FORCE_MIN or o["coherence"] < COHERENCE_MIN
                    or o["bande_deg"][1] - o["bande_deg"][0] < 3.0):
                continue
            o["poids"] = g["poids"] * min(1.0, o["force"] / 10.0) * o["coherence"]
            obs.append(o)
    dmax = 16.0 if ph.is360 else 30.0
    sols = []
    for g in [g for g in gcps_fixes if g["famille"] == "sol"] + dyn_sol:
        d = float(np.linalg.norm(np.array(g["point"]) - cam.C))
        if 2.0 <= d <= dmax:
            sols.append((d, g))
    # éclaircissement : au plus n_sol_max points espacés d'au moins 0,6 m, les plus proches d'abord
    sols.sort(key=lambda t: (t[0], t[1]["id"]))
    garde = []
    for d, g in sols:
        P = np.array(g["point"][:2])
        if all(np.hypot(*(P - np.array(h["point"][:2]))) >= 0.6 for h in garde):
            garde.append(g)
        if len(garde) >= n_sol_max:
            break
    imgs = img if echelle_sol >= 1 else img_flou
    if consensus:
        # décalage commun de l'image (erreur de lacet / tangage) : somme des cartes NCC
        tot, n = None, 0
        for g in garde:
            o = G.apparier_sol(ph, cam, imgs, g, rech_sol, echelle=echelle_sol, carte=True)
            if o is None or "carte" not in o:
                continue
            c = np.maximum(o["carte"], 0.0)
            tot = c if tot is None else tot + c
            n += 1
        if tot is None or n < 4:
            return obs
        j, i = np.unravel_index(int(np.argmax(tot)), tot.shape)
        du, dv = i - rech_sol, j - rech_sol
        for g in garde:
            o = G.apparier_sol(ph, cam, imgs, g, rech_sol, echelle=echelle_sol, contrainte=(du, dv, 6))
            if o is None or o["ncc"] < 0.4:
                continue
            o["consensus_px"] = [int(du), int(dv)]
            o["poids"] = g["poids"] * min(1.0, max(o["ncc"] - 0.3, 0.05) / 0.4)
            obs.append(o)
        return obs
    for g in garde:
        o = G.apparier_sol(ph, cam, imgs, g, rech_sol, echelle=echelle_sol)
        if o is None or o["bord"]:
            continue
        if o["ncc"] < (0.6 if o["type"] == "ligne" else 0.55) or o["distinction"] < 0.05:
            continue
        o["poids"] = g["poids"] * min(1.0, (o["ncc"] - 0.4) / 0.4)
        obs.append(o)
    return obs


def passe(ph, intr, p_brut, sigma, p, img, img_flou, gidx, cfg, graine, focale_libre):
    """Une passe « pointer puis ajuster » depuis la pose p. Renvoie dict ou None."""
    f = p[6] if len(p) > 6 else intr["f"]
    cam = camera(ph, p[:6], {**intr, "f": f})
    fixes = G.selection(ph, cam, dmax=40.0)
    dyn = G.points_sol_ortho(ph, cam, dmax=14.0 if ph.is360 else 25.0, dmin=2.5 if ph.is360 else 3.0)
    for g in fixes + dyn:
        gidx[g["id"]] = g
    obs = pointer(ph, cam, img, img_flou, fixes, dyn, lambda g: cfg["fen"](g, cam), cfg["rech"], cfg["ech"],
                  consensus=cfg.get("consensus", False))
    if len(obs) < 3:
        return None
    aj = Ajustement(ph, intr, p_brut, sigma, obs, gidx, focale_libre=focale_libre)
    if cfg["ransac"]:
        p2, inl = ransac(aj, p, graine)
    else:
        p2 = aj.lm(p)
        inl = aj.erreurs_groupes(p2) < aj.taus()
        for _ in range(2):
            wl, wp = aj.poids_inliers(inl)
            p2 = aj.lm(p2, wl, wp)
            inl = aj.erreurs_groupes(p2) < aj.taus()
    e = aj.erreurs_groupes(p2)
    tau = aj.taus()
    poids = np.array([o.get("poids", 1.0) for o in obs])
    sc = float(np.sum(poids[inl] * (1 - 0.5 * (e[inl] / tau[inl]) ** 2)))
    return dict(p=p2, obs=obs, inl=inl, aj=aj, score=sc,
                moy=float(e[inl].mean()) if inl.any() else 99.0, n_inl=int(inl.sum()))


# --------------------------------------------------------------------------- calage d'une photo
def caler(pid, verbeux=True, planche=False, sequence=False):
    """Calage complet d'une photo ; écrit par_photo/<id8>.json et renvoie l'enregistrement."""
    t0 = time.time()
    ph = photo(pid)
    intr = intrinseques(ph)
    pb = pose_brute(ph)
    sigma = dict(pb["sigma"])
    p_brut = pb["pose"].copy()
    cam0 = camera(ph, p_brut, intr)
    img = image_gris(ph.id8)
    img_flou = G._flou_boite(img, 2 if ph.is360 else 3)
    focale_libre = (not ph.is360) and not ph.meta.get("field_of_view")
    rec = dict(id8=ph.id8, id=ph.id, date=ph.date, datetime=ph.datetime, fichier=ph.jpg.name,
               modele=intr["modele"], porteur=ph.seq["porteur"],
               intrinseques=dict(f=intr["f"], cx=intr["cx"], cy=intr["cy"], k1=intr["k1"],
                                 source=intr["source"]),
               gps=dict(lon=ph.meta["lon"], lat=ph.meta["lat"], azimut_vrai=ph.meta["azimuth"],
                        gamma_deg=pb["gamma"], precision_m=ph.meta.get("horizontal_accuracy_m")),
               pose_brute=_pose_dict(p_brut), sigma_a_priori=sigma)
    gidx = {}
    # ---- 0. a priori de séquence (2e passe : voisins acceptés de la même série)
    p_ap = p_brut
    seq = a_priori_sequence(ph, p_brut) if sequence else None
    if seq is not None:
        p_ap = seq["pose"]
        sigma = dict(seq["sigma"])
        rec["a_priori_sequence"] = dict(voisins=seq["voisins"], pose=_pose_dict(p_ap), sigma=sigma,
                                        decalage=arrondi(seq["decalage"], 3))
        if verbeux:
            print(f"[{ph.id8}] a priori de séquence {seq['voisins']} d={np.round(p_ap[:6] - p_brut[:6], 2)} "
                  f"sigma={sigma}", flush=True)
    # ---- 1. hypothèses : pose brute + vote grossier sur les mâts
    R = float(np.clip(2.5 * sigma["xy"], 1.0, 9.0))
    fixes = G.selection(ph, cam0, dmax=40.0, marge=R)
    mats = [g for g in fixes if g["famille"] in ("mat", "tronc")]
    Y = 12.0 if ph.is360 else 25.0
    hyps = recalage_grossier(ph, cam0, img, mats, R, Y)
    rec["recalage_grossier"] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items()}
                                for h in hyps]
    departs = [("brute", p_brut.copy())]
    if seq is not None:
        departs = [("sequence", p_ap.copy())] + departs
    for k, h in enumerate(hyps):
        q = p_brut.copy()
        q[0] += h["dx"]
        q[1] += h["dy"]
        q[3] += h["dlacet"]
        departs.append((f"vote{k}", q))
    if verbeux:
        hh = [(h["dx"], h["dy"], round(h["dlacet"], 2), round(h["score"], 2)) for h in hyps]
        print(f"[{ph.id8}] {ph.date} {intr['modele']} hypothèses {hh} ({time.time() - t0:.0f} s)", flush=True)
    # ---- 2. assiette : 360° -> corrélation globale au sol (ortho 2022) ; à plat -> multi-départs
    #         en tangage (téléphone tenu à la main : le tangage est l'inconnue dominante)
    horizon = None
    if not ph.is360:
        ref = reference_360(ph, p_brut)
        if ref is not None:
            ph_h, ncc_h = orientation_par_horizon(ph, intr, p_brut, img, ref[0])
            rec["orientation_horizon"] = dict(reference=ref[0]["id8"], distance_m=round(ref[1], 1),
                                              ncc=round(ncc_h, 3),
                                              pose=_pose_dict(ph_h) if ph_h is not None else None)
            if verbeux:
                print(f"[{ph.id8}] horizon (réf. {ref[0]['id8']} à {ref[1]:.0f} m) ncc {ncc_h:.3f} -> "
                      f"{np.round(ph_h[3:6] - p_brut[3:6], 2) if ph_h is not None else None}", flush=True)
            if ph_h is not None and ncc_h >= HORIZON_NCC_MIN:
                horizon = ph_h
    if horizon is not None:
        nd = [("horizon", horizon.copy())] + ([("sequence", p_ap.copy())] if seq is not None else [])
        for nom, q in departs:
            if nom in ("sequence", "brute"):
                continue
            q2 = horizon.copy()
            q2[0], q2[1] = q[0], q[1]
            nd.append((nom + "+horizon", q2))
        departs = nd
    elif not ph.is360:
        t0p = float(np.median(TANGAGES_PLAT.get(ph.date, [0.0])))
        grille_t = TANGAGES_PLAT_GRILLE if ph.date not in TANGAGES_PLAT else (-2.0, 0.0, 2.0)
        nd = []
        for nom, q in departs:
            for dt in grille_t:
                q2 = q.copy()
                q2[4] = t0p + dt
                nd.append((f"{nom}/t{t0p + dt:+.0f}", q2))
        departs = nd
    elif ph.date < G.FIN_TRAVAUX_2025:
        nd = []
        for nom, q in departs:
            c = camera(ph, q, intr)
            q2, s1, s0 = recalage_sol(ph, c, img, tangage_max=3.0 if ph.is360 else 10.0,
                                      roulis_max=3.0 if ph.is360 else 6.0)
            if s1 > s0 + 0.02:
                nd.append((nom + "+sol", q2))
            if verbeux:
                print(f"[{ph.id8}]   {nom}: ncc sol {s0:.3f} -> {s1:.3f} d={np.round(q2 - q, 2)}", flush=True)
        departs += nd
    # ---- 3. passes pointer / ajuster
    px_deg = (cam0.px_par_rad if ph.is360 else intr["f"]) * math.pi / 180
    if ph.is360:
        p0cfg = dict(fen=lambda g, c: max(1.2, math.degrees(math.atan2(1.0, _dist(g, c)))),
                     rech=30, ech=0.5, ransac=True)
    else:
        p0cfg = dict(fen=lambda g, c: max(2.0, math.degrees(math.atan2(2.0, _dist(g, c)))),
                     rech=40, ech=0.2, ransac=True, consensus=True)
    graine = int(ph.id8, 16) % (2 ** 31)
    best, journal = None, []
    for nom, q in departs:
        if VOTE:
            q = voter(ph, intr, q, img, img_flou, sigma, verbeux, nom, t0)
            cfg = dict(fen=lambda g, c: 1.5, rech=24 if ph.is360 else 30, ech=0.5 if ph.is360 else 0.25,
                       ransac=True)
        else:
            cfg = p0cfg
        r = passe(ph, intr, p_ap, sigma, q, img, img_flou, gidx, cfg, graine, focale_libre)
        if r is None:
            journal.append(dict(depart=nom, n_obs=0))
            continue
        journal.append(dict(depart=nom, n_obs=len(r["obs"]), n_inliers=r["n_inl"],
                            score=round(r["score"], 2), moy_deg=round(r["moy"], 3)))
        if verbeux:
            print(f"[{ph.id8}] départ {nom}: {len(r['obs'])} obs, {r['n_inl']} inl, score {r['score']:.1f}, "
                  f"moy {r['moy']:.3f}° ({time.time() - t0:.0f} s)", flush=True)
        if best is None or r["score"] > best["score"]:
            best = r
            best["depart"] = nom
    rec["departs"] = journal
    if best is not None:
        for k in range(3):
            m = best["moy"]
            fen = float(np.clip(3 * m, 0.5, 1.5))
            rech = int(np.clip(3 * m * px_deg, 6, 30))
            ech = 1.0
            if not ph.is360 and k == 0 and 3 * m * px_deg > 24:
                ech = 0.5
                rech = int(np.clip(3 * m * px_deg * ech, 6, 30))
            cfg = dict(fen=lambda g, c, fen=fen: fen, rech=rech, ech=ech, ransac=k == 0)
            r = passe(ph, intr, p_ap, sigma, best["p"], img, img_flou, gidx, cfg, graine + k + 1, focale_libre)
            if r is None:
                break
            if verbeux:
                print(f"[{ph.id8}] passe {k + 1} (fen {fen:.2f}°, rech {rech}px x{ech}): {len(r['obs'])} obs, "
                      f"{r['n_inl']} inl, score {r['score']:.1f}, moy {r['moy']:.3f}° ({time.time() - t0:.0f} s)",
                      flush=True)
            if r["score"] >= 0.9 * best["score"]:
                r["depart"] = best["depart"]
                best = r
            else:
                break
    # ---- 4. qualité
    if best is None or not best["inl"].any():
        rec.update(accepte=False, raison="pas assez d'observations", pose=None, observations=[],
                   duree_s=round(time.time() - t0, 1))
        _ecrire(rec)
        return rec
    rec["depart_retenu"] = best["depart"]
    rec.update(_qualite(ph, best["aj"], best["p"], best["inl"], p_brut, intr, gidx))
    rec["duree_s"] = round(time.time() - t0, 1)
    if verbeux:
        q = rec["qualite"]
        print(f"[{ph.id8}] => accepte={rec['accepte']} ({rec['raison']}) n_gcp={q['n_gcp']} "
              f"(mats {q['n_mats']}, sol {q['n_sol']}) moy={q['residu_moy_deg']}° max={q['residu_max_deg']}° "
              f"moy_px={q['residu_moy_px']} gps={q['decalage_gps_m']} m dlacet={q['correction_lacet_deg']}°",
              flush=True)
    _ecrire(rec)
    if planche:
        import planche as PL
        PL.planche_controle(rec)
    return rec


def voter(ph, intr, q, img, img_flou, sigma, verbeux, nom, t0):
    """Vote en espace de pose autour du départ q (cartes NCC du sol + profils des mâts), itéré :
    cartes larges à basse résolution, puis cartes recalculées à la pose votée, plus fines."""
    etapes = ([(0.25, 40, float(np.clip(2.5 * sigma["xy"], 1.0, 2.5)), 0.25, 5.0, 0.1),
               (0.5, 30, 0.75, 0.15, 1.5, 0.05)] if ph.is360 else
              [(0.12, 50, float(np.clip(sigma["xy"], 2.0, 5.0)), 0.5, 4.0, 0.15),
               (0.25, 40, 1.5, 0.25, 1.5, 0.05)])
    p = np.array(q, float)
    img_q = G._flou_boite(img, 4)
    for k, (ech, S, R, pas_r, Y, pas_y) in enumerate(etapes):
        cam = camera(ph, p[:6], intr)
        fixes = G.selection(ph, cam, dmax=40.0, marge=R)
        dyn = G.points_sol_ortho(ph, cam, dmax=14.0 if ph.is360 else 25.0, dmin=2.5 if ph.is360 else 3.0)
        dmax = 16.0 if ph.is360 else 30.0
        sols = []
        for g in [g for g in fixes if g["famille"] == "sol"] + dyn:
            d = float(np.linalg.norm(np.array(g["point"]) - cam.C))
            if 2.0 <= d <= dmax:
                sols.append((d, g))
        sols.sort(key=lambda t: (t[0], t[1]["id"]))
        garde = []
        for d, g in sols:
            P = np.array(g["point"][:2])
            if all(np.hypot(*(P - np.array(h["point"][:2]))) >= 0.6 for h in garde):
                garde.append(g)
            if len(garde) >= 140:
                break
        mats = [g for g in fixes if g["famille"] == "mat"]
        src = img_q if ech <= 0.25 else img_flou
        vp = VotePose(ph, intr, cam, src, garde, S, ech, profils_mats(ph, cam, img, mats, R, Y),
                      sig_xy=max(R / 2, 0.3), sig_y=max(Y / 2, 0.5))
        if ph.is360:
            p, sc = vp.chercher(p, R, pas_r, Y, pas_y, dz=0.45 if k == 0 else 0.2,
                                assiette=2.0 if k == 0 else 1.0, pas_a=0.5 if k == 0 else 0.25)
        else:
            p, sc = vp.chercher(p, R, pas_r, Y, pas_y, dz=0.45 if k == 0 else 0.2,
                                assiette=4.0 if k == 0 else 1.5, pas_a=0.5 if k == 0 else 0.25)
        if verbeux:
            print(f"[{ph.id8}] vote {nom} étape {k}: {vp.n} points, {len(vp.mats)} mâts, score {sc:.1f} "
                  f"({sc / max(vp.n + len(vp.mats), 1):.2f}/élément), d={np.round(p[:6] - q[:6], 2)} "
                  f"({time.time() - t0:.0f} s)", flush=True)
    return p


def _dist(g, cam):
    P = np.array(g["pied"] if "pied" in g else g["point"])
    return max(float(np.hypot(*(P[:2] - cam.C[:2]))), 0.5)


def _pose_dict(p):
    d = dict(x=p[0], y=p[1], z=p[2], lacet=p[3] % 360.0, tangage=p[4], roulis=p[5])
    return {k: round(float(v), 4) for k, v in d.items()}


def _qualite(ph, aj, p, inl, p_brut, intr, gidx):
    cam = aj.camera(p)
    e = aj.erreurs_groupes(p)
    # résidus en pixels
    epx = np.zeros(len(aj.obs))
    for k, o in enumerate(aj.obs):
        g = gidx[o["gcp"]]
        if o["type"] == "point":
            uv, _, _ = cam.projeter(np.array(g["point"])[None])
            dd = uv[0] - np.array(o["uv"])
            if cam.modele == "equirect":
                dd[0] = (dd[0] + cam.W / 2) % cam.W - cam.W / 2
            epx[k] = float(np.hypot(*dd))
        else:
            # observation sur un axe (mât ou ligne au sol) : écart transverse = angle × px/rad
            epx[k] = math.radians(e[k]) * cam.px_par_rad
    gi = sorted({aj.obs[k]["gcp"] for k in np.nonzero(inl)[0]})
    fam = [gidx[i]["famille"] for i in gi]
    n_mat = sum(f in ("mat", "tronc") for f in fam)
    n_sol = sum(f == "sol" for f in fam)
    # répartition en azimut des inliers
    azs = []
    for i in gi:
        g = gidx[i]
        P = np.array(g["pied"] if "pied" in g else g["point"])
        azs.append(math.degrees(math.atan2(P[0] - p[0], P[1] - p[1])) % 360)
    secteurs = len({int(a // 45) for a in azs})
    # étendue en profondeur des points de sol inliers (un seul secteur suffit si elle est forte)
    ds = [float(np.hypot(*(np.array(gidx[i]["point"][:2]) - p[:2]))) for i in gi if gidx[i]["famille"] == "sol"]
    profondeur = (max(ds) / max(min(ds), 0.5)) if len(ds) >= 2 else 1.0
    cov = aj.covariance(p)
    sd = np.sqrt(np.clip(np.diag(cov), 0, None))
    em = float(e[inl].mean())
    emax = float(e[inl].max())
    pm = float(epx[inl].mean())
    pmax = float(epx[inl].max())
    if ph.is360:
        ok_res = em <= SEUIL_360_DEG
    else:
        ok_res = pm <= SEUIL_PLAT_PX
    # contraintes réellement indépendantes : les échantillons d'une même ligne au sol (même
    # direction, même décalage) ne comptent qu'une fois ; il faut des points ou des mâts
    n_pts = sum(1 for i in gi if gidx[i]["famille"] == "sol" and gidx[i].get("type") != "ligne_marquage")
    lignes = []
    for i in gi:
        g = gidx[i]
        if g.get("type") != "ligne_marquage":
            continue
        A, B = np.array(g["pied"][:2]), np.array(g["sommet"][:2])
        u = (B - A) / max(np.linalg.norm(B - A), 1e-9)
        if u[0] < 0 or (u[0] == 0 and u[1] < 0):
            u = -u
        off = float(u[0] * A[1] - u[1] * A[0])
        if not any(abs(math.degrees(math.acos(min(1.0, abs(float(u @ v)))))) < 3 and abs(off - o) < 0.3
                   for v, o in lignes):
            lignes.append((u, off))
    n_lig = len(lignes)
    ok_n = (n_pts + n_mat + n_lig >= 6) and (n_pts >= 3 or n_mat >= 4) and (n_pts + n_mat >= 4)
    # redondance : nombre d'équations d'observation (point 2, ligne 1 par pixel) des inliers
    n_eq = int(sum(2 if aj.obs[k]["type"] == "point" else len(aj.obs[k]["uv"]) for k in np.nonzero(inl)[0]))
    # validation croisée (leave-one-out) : chaque GCP inlier prédit par une pose calée sans lui ;
    # une solution sur-ajustée (peu de points, faux appariements cohérents) y explose
    loo = []
    idx_in = list(np.nonzero(inl)[0])
    gid_in = sorted({aj.obs[k]["gcp"] for k in idx_in})
    if len(gid_in) > 25:
        pas_l = len(gid_in) / 25.0
        gid_in = [gid_in[int(j * pas_l)] for j in range(25)]
    for gid in gid_in:
        m = inl.copy()
        ks = [k for k in idx_in if aj.obs[k]["gcp"] == gid]
        m[ks] = False
        if m.sum() < 3:
            continue
        wl, wp = aj.poids_inliers(m)
        p_l = aj.lm(p, wl, wp, n_iter=8)
        loo.append(float(aj.erreurs_groupes(p_l)[ks].max()))
    aj.lm(p, *aj.poids_inliers(inl), n_iter=1)          # rétablit le jacobien à la pose finale
    loo_moy = float(np.mean(loo)) if loo else 99.0
    if ph.is360:
        ok_loo = loo_moy <= 2 * SEUIL_360_DEG
    else:
        ok_loo = math.radians(loo_moy) * aj.f0 <= 2 * SEUIL_PLAT_PX
    ok_n = ok_n and n_eq >= 14
    # étendue angulaire des observations inliers (repère caméra) : un amas d'observations dans un
    # petit angle solide se comporte comme un seul point, quelle que soit sa taille
    uvs = []
    for k in np.nonzero(inl)[0]:
        o = aj.obs[k]
        uvs += o["uv"] if o["type"] == "ligne" else [o["uv"]]
    dirs = cam.pixel_vers_cam(np.array(uvs, float))
    lon = np.degrees(np.arctan2(dirs[:, 0], dirs[:, 1]))
    lat = np.degrees(np.arcsin(np.clip(dirs[:, 2], -1, 1)))
    etendue_az = float(np.ptp(lon)) if not ph.is360 else float(min(360.0, secteurs * 45.0))
    etendue_el = float(np.ptp(lat))
    if ph.is360:
        ok_geo = secteurs >= 2 or (n_sol >= 8 and profondeur >= 1.8)
    else:
        ok_geo = etendue_az >= 20.0 and etendue_el >= 3.0
    dgps = float(np.hypot(p[0] - p_brut[0], p[1] - p_brut[1]))
    ok_gps = dgps <= 3 * max(float(ph.meta.get("horizontal_accuracy_m") or 5.0), 1.0) + 1.0
    raisons = []
    if not ok_res:
        raisons.append("résidu moyen trop fort")
    if not ok_n:
        raisons.append("trop peu de GCP inliers")
    if not ok_geo:
        raisons.append("GCP mal répartis")
    if not ok_gps:
        raisons.append("écart au GNSS invraisemblable")
    if not ok_loo:
        raisons.append("validation croisée (leave-one-out) défavorable")
    observations = []
    for k, o in enumerate(aj.obs):
        oo = {kk: v for kk, v in o.items()}
        oo["residu_deg"] = round(float(e[k]), 4)
        oo["residu_px"] = round(float(epx[k]), 2)
        oo["inlier"] = bool(inl[k])
        g = gidx[o["gcp"]]
        if g["id"].startswith("ORTHO-"):
            oo["gcp_def"] = {kk: g[kk] for kk in ("point", "sigma_m", "source", "type")}
        observations.append(arrondi(oo, 4))
    intr_out = dict(f=float(p[6]) if len(p) > 6 else intr["f"], cx=intr["cx"], cy=intr["cy"],
                    k1=intr["k1"], source=intr["source"] + (" ; focale calée" if len(p) > 6 else ""))
    return dict(
        pose=_pose_dict(p), intrinseques=arrondi(intr_out, 3),
        ecart_type=arrondi(dict(x=sd[0], y=sd[1], z=sd[2], lacet=sd[3], tangage=sd[4], roulis=sd[5]), 4),
        qualite=arrondi(dict(
            n_gcp=len(gi), n_mats=n_mat, n_sol=n_sol, n_points_sol=n_pts, n_lignes_distinctes=n_lig,
            n_obs=len(aj.obs), n_inliers=int(inl.sum()), n_equations=n_eq, residu_loo_moy_deg=loo_moy,
            secteurs_45=secteurs, rapport_profondeur_sol=profondeur, etendue_azimut_deg=etendue_az,
            etendue_elevation_deg=etendue_el, residu_moy_deg=em, residu_max_deg=emax, residu_moy_px=pm,
            residu_max_px=pmax, decalage_gps_m=dgps,
            correction_lacet_deg=((p[3] - p_brut[3] + 180) % 360) - 180,
            hauteur_sol_m=float(p[2] - _z_sol(p))), 3),
        accepte=bool(ok_res and ok_n and ok_geo and ok_gps and ok_loo),
        raison="ok" if not raisons else " ; ".join(raisons),
        gcp_utilises=gi, observations=observations)


def _z_sol(p):
    from camera import z_sol
    return z_sol(p[0], p[1])


def _ecrire(rec):
    PAR_PHOTO.mkdir(parents=True, exist_ok=True)
    ecrire_json(PAR_PHOTO / f"{rec['id8']}.json", arrondi(rec, 4))


def requalifier(pid):
    """Recalcule qualité et acceptation d'un enregistrement par_photo existant (mêmes observations,
    même pose) avec les critères courants ; réécrit le fichier. Renvoie l'enregistrement."""
    rec = lire_json(PAR_PHOTO / f"{photo(pid).id8}.json")
    if not rec.get("pose") or not rec.get("observations"):
        return rec
    ph = photo(pid)
    intr = {**intrinseques(ph), **{k: v for k, v in rec["intrinseques"].items() if k in ("f", "cx", "cy", "k1")}}
    cat = G.gcp_par_id()
    gidx, obs = {}, []
    for o in rec["observations"]:
        g = cat.get(o["gcp"])
        if g is None and "gcp_def" in o:
            g = {"id": o["gcp"], "famille": "sol", **o["gcp_def"]}
        if g is None:
            continue
        gidx[o["gcp"]] = g
        obs.append({k: v for k, v in o.items() if k not in ("residu_deg", "residu_px", "inlier", "gcp_def")})
    inl = np.array([o["inlier"] for o in rec["observations"] if o["gcp"] in gidx])
    pb = rec["pose_brute"]
    p_brut = np.array([pb["x"], pb["y"], pb["z"], pb["lacet"], pb["tangage"], pb["roulis"]])
    ap = rec.get("a_priori_sequence", {}).get("pose") or pb
    p_ap = np.array([ap["x"], ap["y"], ap["z"], ap["lacet"], ap["tangage"], ap["roulis"]])
    q = rec["pose"]
    pp = np.array([q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]])
    aj = Ajustement(ph, intr, p_ap, rec["sigma_a_priori"], obs, gidx,
                    focale_libre=(not ph.is360) and not ph.meta.get("field_of_view"))
    if aj.focale_libre:
        pp = np.r_[pp, rec["intrinseques"]["f"]]
    aj.lm(pp, *aj.poids_inliers(inl), n_iter=1)
    rec.update(_qualite(ph, aj, pp, inl, p_brut, intr, gidx))
    _ecrire(rec)
    return rec


# --------------------------------------------------------------------------- assemblage
def assembler():
    """par_photo/*.json -> poses.json (poses + qualité) et gcp.json (catalogue + observations)."""
    recs = [lire_json(f) for f in sorted(PAR_PHOTO.glob("*.json"))]
    photos = []
    obs = {}
    for r in recs:
        photos.append({k: v for k, v in r.items() if k not in ("observations", "duree_s")})
        obs[r["id8"]] = r.get("observations", [])
    n_ok = sum(1 for r in recs if r.get("accepte"))
    entete = dict(
        schema=SCHEMA,
        repere="local = Lambert-93 − O (917279.43, 6460289.98), z = NGF − 216,30 (decrire/commun.py repere)",
        convention_pose="lacet = azimut grille de l'axe avant (deg, de +Y vers +X) ; tangage + = relevé ; "
                        "roulis + = côté droit relevé ; R = matrice_rotation(lacet, tangage, roulis), "
                        "c = R·(P − C) en (droite, avant, haut)",
        modeles={"equirect": "u = W(0,5 + lon/2π), v = H(0,5 − lat/π)",
                 "stenope": "u = cx + f·x(1+k1 r²), v = cy − f·y(1+k1 r²)"},
        criteres=dict(seuil_360_deg=SEUIL_360_DEG, seuil_plat_px=SEUIL_PLAT_PX,
                      gcp_inliers_min=6, validation_croisee="résidu leave-one-out moyen ≤ 2 × seuil", equations_min=14,
                      etendue_plat="observations inliers étalées sur ≥ 20° en azimut et ≥ 3° en élévation",
                      condition="points + mâts + lignes distinctes ≥ 6, dont ≥ 3 points au sol ou ≥ 4 mâts, et points + mâts ≥ 4 ; 360° : ≥ 2 secteurs de 45° ou ≥ 8 points de sol étagés en profondeur (rapport ≥ 1,8)"),
        n_photos=len(recs), n_acceptees=n_ok)
    ecrire_json(SORTIE / "poses.json", {**entete, "photos": photos})
    cat = G.catalogue_gcp()
    ecrire_json(SORTIE / "gcp.json", dict(
        schema="pj_gcp_panoramax/0.1", repere=entete["repere"],
        familles={"mat": "segment pied -> sommet, observation = axe (résidu = angle au plan C-pied-sommet)",
                  "tronc": "idem, tronc levé GAM (pied -> +2 m)",
                  "sol": "point au sol, observation = pixel (résidu angulaire 2D)"},
        catalogue=cat, observations=obs))
    print(f"poses.json : {len(recs)} photos, {n_ok} acceptées")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--photos", nargs="*")
    ap.add_argument("--cibles", action="store_true")
    ap.add_argument("--toutes", action="store_true")
    ap.add_argument("--planches", action="store_true")
    ap.add_argument("--assembler", action="store_true")
    ap.add_argument("--requalifier", action="store_true", help="recalcule l'acceptation des par_photo existants")
    ap.add_argument("--part", type=str, default=None, help="k/n : ne traiter que la part k sur n")
    ap.add_argument("--sequence", action="store_true",
                    help="a priori de séquence (voisins acceptés) ; ne traite que les photos non acceptées")
    a = ap.parse_args(argv)
    ids = []
    if a.photos:
        ids = [photo(p).id8 for p in a.photos]
    elif a.cibles:
        ids = cibles()
    elif a.toutes:
        ids = sorted(catalogue())
    if a.requalifier:
        for f in sorted(PAR_PHOTO.glob("*.json")):
            r = requalifier(f.stem)
            print(f.stem, r.get("accepte"), r.get("raison"))
        ids = []
    if a.sequence:
        acc = {f.stem for f in PAR_PHOTO.glob("*.json")
               if lire_json(f).get("accepte") and not lire_json(f).get("a_priori_sequence")}
        ids = [i for i in ids if i not in acc]       # refait aussi les photos calées avec a priori
    if a.part:
        k, n = map(int, a.part.split("/"))
        ids = ids[k::n]
    for pid in ids:
        try:
            caler(pid, planche=a.planches, sequence=a.sequence)
        except Exception as ex:  # une photo en échec ne bloque pas les autres
            import traceback
            traceback.print_exc()
            _ecrire(dict(id8=photo(pid).id8, id=photo(pid).id, date=photo(pid).date, accepte=False,
                         raison=f"erreur : {ex!r}", pose=None, observations=[]))
    if a.assembler or (ids and not a.part):
        assembler()


if __name__ == "__main__":
    main()
