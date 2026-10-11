"""Détecteur de pied de mât par l'ombre portée (solveur de cohérence v2, correctif P10 de la revue v1).

Les règles ne contraignent que la distance à la bordure (t) : une erreur le long de la bordure (s) reste
invisible (lamp_9514825221, mat_camera_9831317323, lamp_12668578865 à ≈ 1 m de leur vrai pied). Sur une
ortho, le haut d'un mât est déversé (perspective) mais son OMBRE est au sol : elle part du pied, dans la
direction opposée au soleil. Le pied est donc le début d'un trait sombre fin, de direction connue.

Orthos : PCRS 5 cm du 2022-05-10 (projection.ortho_mosaique) et IGN BD ORTHO 2024 du 2024-08-09 (20 cm,
data/raw/ortho_recentes/ign_bdortho_2024_rvb_20cm, recalage négligeable sur le PCRS : +0,04 ; +0,03 m).

1. Soleil : la direction des ombres est CALÉE sur des mâts de référence (axes triangulés sur photos
   calées, enrichi/recensement/mapillary/triangulation_mixte.json : ≥ 4 vues, angle ≥ 30°, stabilité
   ≤ 0,3 m) : balayage de l'azimut d'un trait partant du pied connu, médiane circulaire ; l'élévation
   solaire s'en déduit par la position du soleil (formules NOAA) à la date de prise de vue, ce qui fixe la
   longueur d'ombre L = h / tan(élévation).
2. Pied : dans un rayon de 2,5 m autour de la position décrite, chaque pied candidat q est noté par le
   contraste d'un trait de 0,20 m à min(L, 2,5) m dans la direction de l'ombre (centre plus sombre que les
   flancs à 0,25-0,45 m ; 0,4-0,8 m à 20 cm) moins l'assombrissement en arrière du pied (le trait doit
   commencer en q). Sommes cumulées sur un patch ré-échantillonné dans le repère (travers, ombre).
3. Qualité : contraste (centre plus sombre que CHACUN des deux flancs) ≥ seuil, pic unique (meilleur
   autre trait, décalé de plus de 0,3 m en travers, ≤ 0,85 × le pic), z-score du pic ≥ 3,5 (PCRS) ou 3
   (IGN), pic à plus de 0,3 m du bord de la fenêtre ; validation sur les mâts de référence (chacun cherché
   dans une fenêtre centrée à 1 m à côté de son pied, 4 départs) -> biais et σ le long de l'ombre et en
   travers, médiane, p90 ; le p90 (≈ 1 m, autre mât voisin pris pour la cible) impose une corroboration :
   une détection seule est un INDICE, elle devient une preuve si les deux orthos s'accordent à 0,5 m ou
   si une mesure indépendante (photo) ou la revue la confirme (coherence_mesures).
4. Anisotropie : le trait d'ombre est net en travers (σ ≈ 0,15 m) mais son début peut être masqué par
   l'image déversée du mât (lanterne claire posée sur l'ombre, vu sur les planches) : le long de l'ombre
   σ ≥ 0,6 m. La preuve est donc surtout une contrainte « le pied est sur cette droite » ; l'ombre étant
   orientée à 334° (2022), elle fixe surtout l'abscisse s le long des bordures de Verdun (cap ≈ 40°).
Sortie : coherence/ombres.json (déterministe), consommée comme preuve « ortho_ombre » (s, t) par le canal
de mesures (coherence_mesures, P3).
"""
import functools
import json
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image

from coherence_carte import COHERENCE
from commun import O, RACINE, arrondi, ecrire_json, lire_json, repere

LAT, LON = 45.2077, 5.7682
ORTHOS = {
    "pcrs2022": dict(date="2022-05-10", pas=0.05, largeur=1, flanc=(0.25, 0.45), arriere=(-0.70, -0.15),
                     debut=0.20, amorce=0.45, seuil=0.030, zmin=3.5, libelle="PCRS 5 cm 2022-05-10"),
    "ign2024": dict(date="2024-08-09", pas=0.20, largeur=0, flanc=(0.40, 0.80), arriere=(-0.80, -0.20),
                    debut=0.20, amorce=0.60, seuil=0.025, zmin=3.0, libelle="IGN BD ORTHO 20 cm 2024-08-09"),
}
TYPES_MATS = ("lampadaire", "mat_camera", "poteau_reseau", "support_feux", "panneau", "poteau_arret")
TRIANG_MIXTE = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/triangulation_mixte.json"
SORTIE = COHERENCE / "ombres.json"


# --------------------------------------------------------------------------- orthos
@functools.lru_cache(maxsize=2)
def ortho(nom):
    """(img float32 0..1 niveaux de gris, x0_local du bord gauche, y1_local du bord haut, pas)."""
    if nom == "pcrs2022":
        import sys
        sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
        from projection import ortho_mosaique
        img, x0, y1 = ortho_mosaique()
        return img, float(x0), float(y1), 0.05
    dos = RACINE / "data/raw/ortho_recentes/ign_bdortho_2024_rvb_20cm"
    tuiles = sorted(dos.glob("*.jpg"))
    geo = []
    for t in tuiles:
        a, _, _, e, cx, cy = [float(v) for v in t.with_suffix(".jgw").read_text().split()]
        geo.append((t, a, cx - a / 2, cy - e / 2))          # bord gauche, bord haut (L93)
    pas = geo[0][1]
    xs = sorted({g[2] for g in geo})
    ys = sorted({g[3] for g in geo}, reverse=True)
    n = 1000
    img = np.zeros((n * len(ys), n * len(xs)), np.float32)
    for t, _, xl, yh in geo:
        a = np.asarray(Image.open(t).convert("L"), np.float32) / 255.0
        i, j = ys.index(yh), xs.index(xl)
        img[i * n:(i + 1) * n, j * n:(j + 1) * n] = a[:n, :n]
    return img, xs[0] - O[0], ys[0] - O[1], pas


def echantillonner(nom, P):
    img, x0, y1, pas = ortho(nom)
    P = np.asarray(P, np.float64)
    u = (P[..., 0] - x0) / pas - 0.5
    v = (y1 - P[..., 1]) / pas - 0.5
    H, W = img.shape
    ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
    u = np.clip(u, 0, W - 1.001)
    v = np.clip(v, 0, H - 1.001)
    i0, j0 = np.floor(v).astype(int), np.floor(u).astype(int)
    tv, tu = v - i0, u - j0
    val = (img[i0, j0] * (1 - tu) * (1 - tv) + img[i0, j0 + 1] * tu * (1 - tv)
           + img[i0 + 1, j0] * (1 - tu) * tv + img[i0 + 1, j0 + 1] * tu * tv)
    return np.where(ok, val, np.nan)


# --------------------------------------------------------------------------- soleil (NOAA, simplifié)
def soleil(dt_utc, lat=LAT, lon=LON):
    """(azimut, élévation) du soleil en degrés (azimut depuis le nord vrai, horaire)."""
    jd = dt_utc.timestamp() / 86400.0 + 2440587.5
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    Mr = math.radians(M)
    C = (math.sin(Mr) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * Mr) * (0.019993 - 0.000101 * T)
         + math.sin(3 * Mr) * 0.000289)
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * T))
    eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * T))
    decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    y = math.tan(math.radians(eps / 2)) ** 2
    L0r = math.radians(L0)
    eqt = 4 * math.degrees(y * math.sin(2 * L0r) - 2 * e * math.sin(Mr) + 4 * e * y * math.sin(Mr) * math.cos(2 * L0r)
                           - 0.5 * y * y * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    minutes = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60
    tst = (minutes + eqt + 4 * lon) % 1440
    ha = tst / 4 - 180
    lr, dr, har = math.radians(lat), math.radians(decl), math.radians(ha)
    cz = math.sin(lr) * math.sin(dr) + math.cos(lr) * math.cos(dr) * math.cos(har)
    zen = math.degrees(math.acos(max(-1, min(1, cz))))
    az = math.degrees(math.atan2(math.sin(har), math.cos(har) * math.sin(lr) - math.tan(dr) * math.cos(lr))) + 180
    return az % 360, 90 - zen


def soleil_par_azimut(date, az_soleil_vrai):
    """Instant (UTC) du jour `date` où le soleil a l'azimut donné (matinée et après-midi), et son élévation."""
    best = None
    t0 = datetime.fromisoformat(date + "T04:00:00").replace(tzinfo=timezone.utc)
    for k in range(0, 16 * 60):
        t = t0 + timedelta(minutes=k)
        az, el = soleil(t)
        if el <= 5:
            continue
        e = abs((az - az_soleil_vrai + 180) % 360 - 180)
        if best is None or e < best[0]:
            best = (e, t, az, el)
    return best


def gamma_grille():
    """Azimut grille du nord vrai au centre du site (deg)."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    a = np.array(t.transform(LON, LAT))
    b = np.array(t.transform(LON, LAT + 1e-4))
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


# --------------------------------------------------------------------------- patch et scores
def _patch(nom, p0, az_ombre, rayon, b_max):
    """Patch ré-échantillonné dans le repère (a = travers à droite de l'ombre, b = le long de l'ombre)."""
    cfg = ORTHOS[nom]
    s = cfg["pas"]
    u = np.array([math.sin(math.radians(az_ombre)), math.cos(math.radians(az_ombre))])
    e = np.array([u[1], -u[0]])
    a = np.arange(-rayon - cfg["flanc"][1] - s, rayon + cfg["flanc"][1] + s + 1e-9, s)
    b = np.arange(-rayon + cfg["arriere"][0] - s, rayon + b_max + s + 1e-9, s)
    A, B = np.meshgrid(a, b)
    P = p0 + A[..., None] * e + B[..., None] * u
    return echantillonner(nom, P), a, b, u, e


def _somme_boite(I, r0, r1, c0, c1):
    """Somme de boîtes [r0, r1[ × [c0, c1[ sur l'image intégrale I (indices vectorisés)."""
    return I[r1, c1] - I[r0, c1] - I[r1, c0] + I[r0, c0]


def scores_pieds(nom, p0, az_ombre, L, rayon=2.5):
    """Score de chaque pied candidat de la fenêtre : (Q (N, 2), score, contraste, arriere)."""
    cfg = ORTHOS[nom]
    s = cfg["pas"]
    b1 = max(min(L, 4.0), cfg["debut"] + 4 * s)
    V, a, b, u, e = _patch(nom, p0, az_ombre, rayon, b1)
    ok = np.isfinite(V)
    V = np.where(ok, V, np.nanmedian(V) if ok.any() else 0.5)
    I = np.zeros((V.shape[0] + 1, V.shape[1] + 1))
    I[1:, 1:] = np.cumsum(np.cumsum(V, 0), 1)
    ca = np.nonzero(np.abs(a) <= rayon + 1e-9)[0]
    cb = np.nonzero(np.abs(b) <= rayon + 1e-9)[0]
    CA, CB = np.meshgrid(ca, cb)
    CA, CB = CA.ravel(), CB.ravel()
    keep = np.hypot(a[CA], b[CB]) <= rayon + 1e-9
    CA, CB = CA[keep], CB[keep]
    w = cfg["largeur"]
    f0, f1 = int(round(cfg["flanc"][0] / s)), int(round(cfg["flanc"][1] / s))
    d0, d1 = int(round(cfg["debut"] / s)), int(round(b1 / s))
    def contraste_trait(r0, r1):
        """min(flanc gauche, flanc droit) − centre : un bord (un seul flanc clair) ne compte pas."""
        n_l = (r1 - r0) * (2 * w + 1)
        lig = _somme_boite(I, r0, r1, CA - w, CA + w + 1) / n_l
        n_f = (r1 - r0) * (f1 - f0 + 1)
        fd = _somme_boite(I, r0, r1, CA + f0, CA + f1 + 1) / n_f
        fg = _somme_boite(I, r0, r1, CA - f1, CA - f0 + 1) / n_f
        return np.minimum(fd, fg) - lig, np.maximum(fd, fg) - lig
    contraste, _ = contraste_trait(CB + d0, CB + d1 + 1)
    # amorce : le trait doit commencer AU pied (0 à 0,45 m), pas seulement plus loin sur la même ombre
    a1 = int(round(cfg["amorce"] / s))
    amorce, _ = contraste_trait(CB, CB + a1 + 1)
    k0, k1 = int(round(cfg["arriere"][0] / s)), int(round(cfg["arriere"][1] / s))
    _, arriere = contraste_trait(CB + k0, CB + k1 + 1)
    score = np.minimum(contraste, 1.3 * amorce) - np.maximum(arriere, 0.0)
    Q = p0 + a[CA][:, None] * e + b[CB][:, None] * u
    return Q, score, contraste, arriere


def detecter_pied(nom, p0, az_ombre, L, rayon=2.5, biais_long=0.0):
    """Pied le plus probable dans la fenêtre : dict(xy, score, contraste, unicite, unicite_long, z) ou None.
    unicite : meilleur score d'un AUTRE trait (décalé de plus de 0,3 m en travers de l'ombre) / pic ;
    unicite_long : meilleur score sur le même trait à plus de 0,6 m le long de l'ombre / pic.
    biais_long : correction calée sur les références (début d'ombre masqué par l'image déversée du mât)."""
    p0 = np.asarray(p0, float)
    Q, sc, co, ar = scores_pieds(nom, p0, az_ombre, L, rayon)
    if not len(sc):
        return None
    i = int(np.argmax(sc))
    u = np.array([math.sin(math.radians(az_ombre)), math.cos(math.radians(az_ombre))])
    e = np.array([u[1], -u[0]])
    dq = Q - Q[i]
    lon, tra = dq @ u, dq @ e
    autre = np.abs(tra) > 0.3
    meme = (~autre) & (np.abs(lon) > 0.6)
    second = float(sc[autre].max()) if autre.any() else 0.0
    second_l = float(sc[meme].max()) if meme.any() else 0.0
    med = float(np.median(sc))
    mad = float(np.median(np.abs(sc - med))) * 1.4826 + 1e-6
    xy = Q[i] - biais_long * u
    return dict(xy=[round(float(xy[0]), 3), round(float(xy[1]), 3)], xy_brut=[round(float(Q[i][0]), 3), round(float(Q[i][1]), 3)],
                score=round(float(sc[i]), 4), contraste=round(float(co[i]), 4), arriere=round(float(ar[i]), 4),
                unicite=round(second / max(float(sc[i]), 1e-6), 3), unicite_long=round(second_l / max(float(sc[i]), 1e-6), 3),
                z=round((float(sc[i]) - med) / mad, 2), d_p0=round(float(np.hypot(*(xy - p0))), 3),
                d_fenetre=round(float(np.hypot(*(Q[i] - p0))), 3))


def azimut_ombre_mesure(nom, pied, L=2.0, pas_deg=1.0):
    """Azimut (grille) du trait sombre le plus contrasté partant du pied connu : (az, contraste)."""
    cfg = ORTHOS[nom]
    s = cfg["pas"]
    pied = np.asarray(pied, float)
    best = (None, -1.0)
    b = np.arange(cfg["debut"], L + 1e-9, s / 2)
    for az in np.arange(0, 360, pas_deg):
        u = np.array([math.sin(math.radians(az)), math.cos(math.radians(az))])
        e = np.array([u[1], -u[0]])
        lig = echantillonner(nom, pied + b[:, None] * u)
        fl = np.concatenate([echantillonner(nom, pied + b[:, None] * u + sgn * f * e)
                             for sgn in (-1, 1) for f in np.linspace(*cfg["flanc"], 3)])
        c = float(np.nanmean(fl) - np.nanmean(lig))
        if c > best[1]:
            best = (float(az), c)
    return best


# --------------------------------------------------------------------------- références et calage
def references(objets_par_id):
    """Mâts de référence : axes triangulés sur photos calées (≥ 4 vues, angle ≥ 30°, stabilité ≤ 0,3 m)."""
    if not TRIANG_MIXTE.exists():
        return []
    out = []
    for r in lire_json(TRIANG_MIXTE)["resultats"]:
        if r["n_inliers"] < 4 or (r.get("angle_intersection_deg") or 0) < 30 or (r.get("stabilite_loo_m") or 9) > 0.3:
            continue
        o = objets_par_id.get(r["entite"])
        if o is None or str(o.get("statut") or "").startswith(("déduit", "2026")):
            continue                    # objet posé après l'ortho : pas une référence
        out.append(dict(id=r["entite"], xy=np.array(r["xy"], float), hauteur=float(o.get("hauteur") or 3.0),
                        type=o["type"], source="triangulation_mixte"))
    out.sort(key=lambda r: r["id"])
    return out


def caler_soleil(nom, refs):
    """Azimut grille des ombres (médiane circulaire des références) et élévation solaire déduite."""
    mes = []
    for r in refs:
        az, c = azimut_ombre_mesure(nom, r["xy"], L=min(2.0, 0.5 * r["hauteur"]))
        mes.append(dict(id=r["id"], az=az, contraste=round(c, 4)))
    bons = [m for m in mes if m["contraste"] >= ORTHOS[nom]["seuil"]]
    if len(bons) < 3:
        return None
    ang = np.radians([m["az"] for m in bons])
    m0 = math.degrees(math.atan2(np.mean(np.sin(ang)), np.mean(np.cos(ang)))) % 360
    ecarts = np.array([((m["az"] - m0 + 180) % 360) - 180 for m in bons])
    inl = np.abs(ecarts) <= 25
    ang = np.radians([m["az"] for m, k in zip(bons, inl) if k])
    az_g = math.degrees(math.atan2(np.median(np.sin(ang)), np.median(np.cos(ang)))) % 360
    gam = gamma_grille()
    az_sol_vrai = (az_g + 180 - gam) % 360          # azimut vrai du soleil
    e, t, az_v, el = soleil_par_azimut(ORTHOS[nom]["date"], az_sol_vrai)
    return dict(az_ombre_grille=round(az_g, 2), dispersion_deg=round(float(np.median(np.abs(ecarts[inl]))) * 1.4826, 2),
                n_refs=int(inl.sum()), n_mesures=len(mes), heure_utc=t.strftime("%H:%M"), elevation_deg=round(el, 2),
                azimut_soleil_vrai=round(az_v, 2), gamma_deg=round(gam, 4), mesures=mes)


def longueur_ombre(h, el):
    return float(h) / max(math.tan(math.radians(el)), 0.2)


def valider(nom, refs, sol):
    """Validation : chaque référence est cherchée dans une fenêtre centrée à 1,0 m de son pied (4
    directions, déterministe). Erreurs décomposées le long de l'ombre (biais : début d'ombre masqué par
    l'image déversée du mât) et en travers ; le biais médian est retiré, σ = 1,4826 × MAD par axe."""
    u = np.array([math.sin(math.radians(sol["az_ombre_grille"])), math.cos(math.radians(sol["az_ombre_grille"]))])
    e = np.array([u[1], -u[0]])
    det = []
    for r in refs:
        L = longueur_ombre(r["hauteur"], sol["elevation_deg"])
        for k, ang in enumerate((45.0, 135.0, 225.0, 315.0)):
            c = r["xy"] + 1.0 * np.array([math.sin(math.radians(ang)), math.cos(math.radians(ang))])
            d = detecter_pied(nom, c, sol["az_ombre_grille"], L, rayon=2.5)
            if d is None:
                continue
            dv = np.array(d["xy"]) - r["xy"]
            det.append(dict(id=r["id"], depart=k, erreur_m=round(float(np.hypot(*dv)), 3), long_m=round(float(dv @ u), 3),
                            travers_m=round(float(dv @ e), 3), accepte=accepte(nom, d),
                            **{x: d[x] for x in ("score", "unicite", "unicite_long", "z")}))
    ok = [x for x in det if x["accepte"]]
    if len(ok) < 6:
        return dict(n=len(ok), n_essais=len(det), essais=det)
    lon = np.array([x["long_m"] for x in ok])
    tra = np.array([x["travers_m"] for x in ok])
    biais = float(np.median(lon))
    s_l = float(np.median(np.abs(lon - biais))) * 1.4826
    s_t = float(np.median(np.abs(tra - np.median(tra)))) * 1.4826
    err = np.hypot(lon - biais, tra)
    return dict(n=len(ok), n_essais=len(det), n_objets=len({x["id"] for x in ok}), biais_long_m=round(biais, 3),
                sigma_long_m=round(s_l, 3), sigma_travers_m=round(s_t, 3),
                mediane_m=round(float(np.median(err)), 3), p90_m=round(float(np.percentile(err, 90)), 3),
                part_sous_05_m=round(float(np.mean(err <= 0.5)), 3), essais=det)


def accepte(nom, d, rayon=2.5):
    cfg = ORTHOS[nom]
    return bool(d["contraste"] >= cfg["seuil"] and d["unicite"] <= 0.85 and d["z"] >= cfg["zmin"]
                and d.get("d_fenetre", 0.0) <= rayon - 0.3)


# --------------------------------------------------------------------------- exécution
def executer(objets, ecrire=True):
    """Calage, validation et détection sur tous les mâts dont la position vient d'OSM (et sur les références
    pour mémoire). Renvoie dict(par_ortho, detections {id: {ortho: det}})."""
    par_id = {o["id"]: o for o in objets}
    refs = references(par_id)
    res = dict(schema="pj_coherence_ombres/0.1", methode=__doc__.strip().split("\n\n")[0], references=[r["id"] for r in refs],
               par_ortho={}, detections={})
    cibles = [o for o in objets if o["type"] in TYPES_MATS and not o["statut"].startswith("absent")
              and ("OSM" in o["source"] or o.get("preuve_propre") == "osm")]
    cibles.sort(key=lambda o: o["id"])
    for nom in ORTHOS:
        sol = caler_soleil(nom, refs)
        if sol is None:
            res["par_ortho"][nom] = dict(statut="calage impossible (moins de 3 références contrastées)")
            continue
        val = valider(nom, refs, sol)
        sig = None
        if val.get("n", 0) >= 6:
            plancher = 0.15 if nom == "pcrs2022" else 0.25
            # le long de l'ombre, l'image déversée du mât (lanterne claire) masque souvent le début de l'ombre
            # des candélabres (vu sur les planches) : σ_long ≥ 0,6 m ; en travers, le trait est net
            sig = dict(long=round(max(0.6, val["sigma_long_m"]), 3), travers=round(max(plancher, val["sigma_travers_m"]), 3))
        res["par_ortho"][nom] = dict(soleil={k: v for k, v in sol.items() if k != "mesures"}, mesures_soleil=sol["mesures"],
                                     validation={k: v for k, v in val.items() if k != "essais"}, essais_validation=val.get("essais"),
                                     sigma_preuve_m=sig, libelle=ORTHOS[nom]["libelle"], date=ORTHOS[nom]["date"])
        for o in cibles:
            h = float(o.get("hauteur") or 4.0)
            L = longueur_ombre(h, sol["elevation_deg"])
            d = detecter_pied(nom, o["p0"], sol["az_ombre_grille"], L, rayon=2.5,
                              biais_long=(val.get("biais_long_m") or 0.0) if sig else 0.0)
            if d is None:
                continue
            d["accepte"] = accepte(nom, d) and sig is not None
            d["sigma_long_m"] = sig["long"] if sig else None
            d["sigma_travers_m"] = sig["travers"] if sig else None
            d["az_ombre_grille"] = sol["az_ombre_grille"]
            d["longueur_ombre_m"] = round(L, 2)
            res["detections"].setdefault(o["id"], {})[nom] = d
    for oid, dd in res["detections"].items():
        a, b = dd.get("pcrs2022"), dd.get("ign2024")
        if a and b:
            dd["accord_2022_2024_m"] = round(float(np.hypot(*(np.array(a["xy"]) - np.array(b["xy"])))), 3)
    if ecrire:
        ecrire_json(SORTIE, arrondi(res, 4))
    return res


def charger():
    return lire_json(SORTIE) if SORTIE.exists() else None


if __name__ == "__main__":
    import sys
    import time
    sys.stdout.reconfigure(encoding="utf-8")
    from coherence_carte import REGLES
    from coherence_objets import charger as charger_objets
    t0 = time.time()
    objets, _ = charger_objets(lire_json(REGLES))
    r = executer(objets)
    for nom, v in r["par_ortho"].items():
        print(nom, json.dumps(v.get("soleil"), ensure_ascii=False), json.dumps(v.get("validation"), ensure_ascii=False),
              v.get("sigma_preuve_m"))
        for e in v.get("essais_validation") or []:
            print("   ", e)
    n = sum(1 for d in r["detections"].values() for x in d.values() if isinstance(x, dict) and x["accepte"])
    print(f"{len(r['detections'])} mâts, {n} détections acceptées ({time.time() - t0:.1f} s)")
