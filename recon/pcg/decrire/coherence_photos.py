"""Tests image automatiques du solveur de cohérence v3 (correctifs Q1, Q2 et Q4 de la revue adverse v2).

Toutes les mesures se font sur les photos à pose calée du catalogue (coherence_poses), une photo chargée
une seule fois par lot (tâches triées par photo : exécution déterministe).

Q1 — axe vertical. Pour une photo et des hypothèses de position (A origine, C corrigée, M mesures), la
photo est rééchantillonnée sur une grille (azimut, élévation) du repère local (une verticale du monde y est
une colonne). Pour chaque largeur de barre s (0,5 à 2 fois le diamètre apparent du fût), le contraste de
barre d'une colonne est le MINIMUM des contrastes entre le cœur [a − s/2, a + s/2] et chacun des deux flancs,
s'ils ont le même signe (un bord simple — façade, haie — ne répond pas) ; il est normalisé par le bruit de la
ligne (écart médian entre pixels voisins). Le profil d'une hypothèse X est le 70e centile de ce contraste sur
les lignes comprises entre le pied et la hauteur de l'objet en X (le fût doit occuper au moins 30 % de la
bande) : c'est le « profil de gradient horizontal entre le pied et h ». L'axe retenu pour X est le maximum du
profil dans ±3σ autour de l'azimut de X (σ : pose à cette distance) ; le résidu r(X) = (axe − az(X)) / σ.
X est « soutenu » si le maximum dépasse SEUIL_SUPPORT ; deux maxima de même force séparés de plus de 2
largeurs rendent X « ambigu ».

Q2 — validation locale d'une pose. Une photo n'est décisive pour un objet que si au moins 2 éléments levés
(arêtes de bordure de la description v2 issues du levé GAM 2026 ou du PCRS, marquages GAM 2026) situés à
moins de 15 m de l'objet et à ±30° de son azimut se reprojettent à moins de 2σ. Pour chaque élément, le
gradient de l'image projeté sur la normale image de l'élément est moyenné sur ses échantillons (tous les
0,2 m) en fonction du décalage j (±4σ) : l'élément est aligné si le maximum du profil dans ±2σ vaut au moins
80 % du maximum dans ±4σ et 1,8 fois la médiane du profil ; la photo est validée si ≥ 2 éléments sont alignés
et forment au moins la moitié des éléments à structure nette. Une photo antérieure aux travaux n'utilise que
les bordures non modifiées en 2025 et les marquages GAM « conservés » (les autres ont changé).

Q4 — présence 2026. Pour un objet à moins de 25 m d'une photo calée postérieure aux travaux : vignette de
présence (boîte projetée de l'objet : pied, sommet, emprise) et test automatique dans la boîte : structure
verticale (Q1 sur une seule hypothèse) pour un mât, végétation (indice ExG) et tronc pour un arbre.
"""
import functools
import math
import sys

import numpy as np

import coherence_poses as PO
from commun import RACINE

sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
from camera import echantillonner  # noqa: E402

FIN_TRAVAUX_2025 = "2025-12-05"
SEUIL_SUPPORT = 3.0             # contraste de barre / bruit (70e centile de la bande pied -> h)
SEUIL_PIED = 1.8                # même contraste dans le tiers bas de la bande (la structure atteint le pied de X)
RAPPORT_AMBIGU = 0.85
N_LIGNES = 48
RAYON_Q2 = 15.0
SECTEUR_Q2 = 30.0
N_ELEMENTS_MIN = 2
PROMINENCE_Q2 = 1.8
REL_Q2 = 0.8
DIAMETRES = {"lampadaire": 0.20, "mat_camera": 0.20, "poteau_reseau": 0.24, "support_feux": 0.114, "panneau": 0.07,
             "poteau_arret": 0.09, "potelet": 0.09, "balise_J11": 0.20, "arbre": 0.35, "poteau_incendie": 0.24,
             "barriere_levante": 0.30, "boite_aux_lettres": 0.40, "stationnement_velos": 0.10, "corbeille": 0.45}

_CARTE = None


def init(carte):
    """Carte du solveur (bordures v2 avec drapeaux de travaux, MNT)."""
    global _CARTE
    _CARTE = carte
    elements_leves.cache_clear()


def apres_travaux(date):
    return str(date) > FIN_TRAVAUX_2025


# --------------------------------------------------------------------------- éléments levés (Q2)
def _densifier(P, pas=0.2):
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.hypot(*(b - a)))
        n = max(1, int(math.ceil(L / pas)))
        out.append(a + (b - a) * (np.arange(1, n + 1)[:, None] / n))
    return np.vstack(out)


@functools.lru_cache(maxsize=2)
def elements_leves(apres):
    """[(id, type, P densifié (N, 2), z (N,))] : bordures v2 levées (GAM 2026 ; PCRS 2019 hors tronçons refaits en
    2025) et marquages GAM. Avant travaux : bordures non modifiées en 2025 et marquages GAM « conservés » seulement."""
    from coherence_carte import BASE_V2
    from commun import lire_geojson, repere
    out = []
    for kb in _CARTE.bordures:
        if kb.get("source") not in ("gam", "pcrs2019"):
            continue
        change = bool(kb.get("modifiee_2025") or kb.get("zone_travaux_2025"))
        if apres and kb.get("source") != "gam" and change:
            continue                      # PCRS 2019 : seulement hors des tronçons refaits en 2025
        if not apres and change:
            continue
        Q = _densifier(np.asarray(kb["P"], float))
        out.append((kb["id"], "bordure", Q, _CARTE.z_sol(Q)))
    for f in lire_geojson(BASE_V2 / "marquages.geojson"):
        p, g = f["properties"], f["geometry"]
        if p.get("src") != "gam" or g is None or (not apres and p.get("etat") != "conserve"):
            continue
        if g["type"] == "Polygon":
            rings = [g["coordinates"][0]]
        elif g["type"] == "MultiPolygon":
            rings = [q[0] for q in g["coordinates"]]
        elif g["type"] == "LineString":
            rings = [g["coordinates"]]
        elif g["type"] == "MultiLineString":
            rings = g["coordinates"]
        else:
            rings = []
        for k, r in enumerate(rings):
            P = repere(np.asarray(r, float)[:, :2])
            if len(P) >= 2:
                Q = _densifier(P)
                out.append((f"{p['id']}:{k}", "marquage", Q, _CARTE.z_sol(Q)))
    out.sort(key=lambda e: e[0])
    return out


# --------------------------------------------------------------------------- images (une à la fois)
class Image1:
    """Photo chargée : gris float32 (0..1), gradients (Q2), RVB (vignettes)."""

    def __init__(self, p):
        self.p = p
        self.rgb = np.asarray(PO.image_rgb(p))
        a = self.rgb.astype(np.float32)
        self.gris = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255.0
        self._g = None

    @property
    def gradients(self):
        if self._g is None:
            gy, gx = np.gradient(self.gris)
            self._g = (gx.astype(np.float32), gy.astype(np.float32))
        return self._g


def fenetre(cam, img, az0, az1, el0, el1, pas_az, n_el):
    """Grille (élévation décroissante, azimut croissant) du repère local : (valeurs, az, el)."""
    az = np.arange(az0, az1 + 1e-9, pas_az)
    el = np.linspace(el1, el0, n_el)
    A, E = np.meshgrid(np.radians(az), np.radians(el))
    d = np.stack([np.cos(E) * np.sin(A), np.cos(E) * np.cos(A), np.sin(E)], -1).reshape(-1, 3)
    uv, ok = cam.cam_vers_pixel(d @ cam.R.T)
    v = echantillonner(img, uv[:, 0], uv[:, 1], boucle=cam.modele == "equirect")
    if img.ndim == 3:
        return v.reshape(len(el), len(az), img.shape[2]), az, el
    return v.reshape(len(el), len(az)), az, el


def _barres(I, pas, w):
    """Contraste de barre normalisé (n_el, n_az, n_largeurs) et largeurs (deg)."""
    n = I.shape[1]
    bruit = np.median(np.abs(np.diff(I, axis=1)), axis=1, keepdims=True) * math.sqrt(2.0) + 0.004
    out, larg = [], []
    for f in (0.5, 0.75, 1.0, 1.5, 2.0):
        s = max(w * f, 0.05)
        k = max(1, int(round(s / 2 / pas)))
        g = max(1, int(round(max(s / 2, 0.06) / pas)))
        off = k + g + 1
        c = np.cumsum(np.pad(I, ((0, 0), (off, off)), mode="edge"), axis=1)
        idx = np.arange(n) + off
        coeur = (c[:, idx + k] - c[:, idx - k - 1]) / (2 * k + 1)
        gauche = (c[:, idx - k - 1] - c[:, idx - k - 1 - g]) / g
        droite = (c[:, idx + k + g] - c[:, idx + k]) / g
        c1, c2 = coeur - gauche, coeur - droite
        b = np.where(np.sign(c1) == np.sign(c2), np.minimum(np.abs(c1), np.abs(c2)), 0.0)
        out.append(b / bruit)
        larg.append(s)
    return np.stack(out, -1), larg


def geometrie(p, hyps, h, zs):
    """Azimut, distance, élévations du pied et du sommet de chaque hypothèse vue de la photo p."""
    C = p["cam"].C
    out = []
    ref = None
    for (cle, xy), z in zip(hyps, zs):
        dx, dy = float(xy[0] - C[0]), float(xy[1] - C[1])
        d = math.hypot(dx, dy)
        az = math.degrees(math.atan2(dx, dy))
        if ref is None:
            ref = az
        az = ref + ((az - ref + 180.0) % 360.0 - 180.0)
        hp = min(max(0.3 * h, 0.6), h)
        out.append(dict(cle=cle, xy=np.asarray(xy, float), az=az, d=d,
                        ef=math.degrees(math.atan2(z - C[2], d)), et=math.degrees(math.atan2(z + h - C[2], d)),
                        ep=math.degrees(math.atan2(z + hp - C[2], d)), sigma=PO.sigma_deg(p, d)))
    return out


def detecter_axes(im, hyps, h, diam, zs, bande=(0.05, 1.0)):
    """Q1 : axe vertical autour de chaque hypothèse. hyps : [(cle, xy)] ; zs : z du sol de chaque hypothèse.
    Renvoie dict(par_hyp={cle: dict(az, d, sigma, support, valeur, axe_az, residu, ambigu)}, fenetre=…)."""
    p = im.p
    cam = p["cam"]
    G = geometrie(p, hyps, h, zs)
    dm = float(np.mean([g["d"] for g in G]))
    w = max(math.degrees(diam / dm), 0.06)
    az0 = min(g["az"] - 3 * g["sigma"] - 3 * w for g in G)
    az1 = max(g["az"] + 3 * g["sigma"] + 3 * w for g in G)
    if az1 - az0 > 40.0:
        return dict(par_hyp={}, motif="fenêtre trop large (> 40°)")
    el0 = min(g["ef"] for g in G)
    el1 = max(g["et"] for g in G)
    el1 = min(el1, el0 + 70.0)
    pas = float(np.clip(w / 4, 0.01, 0.03))
    I, az, el = fenetre(cam, im.gris, az0, az1, el0, el1, pas, N_LIGNES)
    B, larg = _barres(I, pas, w)
    out = {}
    for g in G:
        lo = g["ef"] + bande[0] * (g["et"] - g["ef"])
        hi = g["ef"] + bande[1] * (g["et"] - g["ef"])
        lignes = (el >= lo - 1e-9) & (el <= hi + 1e-9)
        if lignes.sum() < 4:
            out[g["cle"]] = dict(az=g["az"], d=g["d"], sigma=g["sigma"], support=False, valeur=0.0, axe_az=None,
                                 residu=None, ambigu=False, motif="bande trop étroite")
            continue
        prof = np.percentile(B[lignes], 70, axis=0).max(axis=-1)
        m = np.abs(az - g["az"]) <= 3 * g["sigma"] + 1e-9
        if not m.any():
            continue
        idx = np.nonzero(m)[0]
        i = int(idx[np.argmax(prof[idx])])
        v = float(prof[i])
        a = float(az[i])
        if 0 < i < len(az) - 1:
            y0, y1, y2 = prof[i - 1], prof[i], prof[i + 1]
            den = y0 - 2 * y1 + y2
            if abs(den) > 1e-9:
                a += float(np.clip(0.5 * (y0 - y2) / den, -0.5, 0.5)) * pas
        loin = idx[np.abs(az[idx] - a) > 2 * w]
        v2 = float(prof[loin].max()) if len(loin) else 0.0
        # pied : la structure doit descendre jusqu'au pied de X (une structure plus lointaine à la même visée
        # s'arrête plus haut dans l'image) ; 70e centile de la bande [pied, pied + max(0,3 h ; 0,6 m)], colonne de l'axe ± 1
        bas = (el >= g["ef"] - 1e-9) & (el <= g["ep"] + 1e-9)
        if bas.sum() >= 3:
            j0, j1 = max(i - 1, 0), min(i + 2, len(az))
            pied = float(np.percentile(B[bas][:, j0:j1], 70, axis=0).max())
        else:
            pied = v
        out[g["cle"]] = dict(az=g["az"], d=g["d"], sigma=g["sigma"], support=bool(v >= SEUIL_SUPPORT), valeur=round(v, 2),
                             axe_az=a, residu=(a - g["az"]) / g["sigma"], pied=round(pied, 2),
                             pied_ok=bool(pied >= SEUIL_PIED),
                             ambigu=bool(v >= SEUIL_SUPPORT and v2 >= RAPPORT_AMBIGU * v), valeur_2=round(v2, 2))
    return dict(par_hyp=out, w_deg=w, fenetre=(az0, az1, el0, el1))


# --------------------------------------------------------------------------- Q2
def valider_pose_locale(im, xy):
    """Q2 : la pose de im est-elle localement juste autour de xy ? dict(valide, n_elements, n_alignes, ...)."""
    p = im.p
    cam = p["cam"]
    C = cam.C
    W = cam.W
    xy = np.asarray(xy, float)
    az_o = math.degrees(math.atan2(xy[0] - C[0], xy[1] - C[1]))
    gx, gy = im.gradients
    res = []
    for eid, typ, Q, z in elements_leves(apres_travaux(p["date"])):
        dQ = np.hypot(*(Q - xy).T)
        if dQ.min() > RAYON_Q2:
            continue
        azq = np.degrees(np.arctan2(Q[:, 0] - C[0], Q[:, 1] - C[1]))
        e = np.abs((azq - az_o + 180) % 360 - 180)
        dc = np.hypot(*(Q - C[:2]).T)
        m = (dQ <= RAYON_Q2) & (e <= SECTEUR_Q2) & (dc >= 3.0) & (dc <= 40.0)
        if m.sum() < 5:
            continue
        P3 = np.c_[Q[m], z[m]]
        uv, ok, dist = cam.projeter(P3)
        c = cam.monde_vers_cam(P3)
        lat = np.degrees(np.arctan2(c[:, 2], np.hypot(c[:, 0], c[:, 1])))
        ok &= lat > p["lat_min"] + 1.0
        idx = np.nonzero(ok)[0]
        if len(idx) < 5:
            continue
        t = np.gradient(uv, axis=0)
        t[:, 0] = np.where(np.abs(t[:, 0]) > W / 2, t[:, 0] - np.sign(t[:, 0]) * W, t[:, 0])
        n = np.c_[-t[:, 1], t[:, 0]] / np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-9)[:, None]
        L_img = float(np.sum(np.hypot(*np.diff(uv[idx], axis=0).T)))
        if L_img < 25.0:
            continue
        dm = float(np.median(dist[idx]))
        sg = math.sqrt(PO.sigma_deg(p, dm) ** 2 + math.degrees(0.08 / dm) ** 2)
        spx = sg * W / 360.0
        J = max(4.0 * spx, 8.0)
        j = np.arange(-J, J + 1e-9, 0.5)
        U = uv[idx, 0][:, None] + j[None, :] * n[idx, 0][:, None]
        V = uv[idx, 1][:, None] + j[None, :] * n[idx, 1][:, None]
        a = echantillonner(gx, U.ravel(), V.ravel(), boucle=True).reshape(U.shape)
        b = echantillonner(gy, U.ravel(), V.ravel(), boucle=True).reshape(U.shape)
        M = np.abs(a * n[idx, 0][:, None] + b * n[idx, 1][:, None]).mean(axis=0)
        med = float(np.median(M)) + 1e-6
        dans = np.abs(j) <= 2.0 * spx
        m2, m4 = float(M[dans].max()), float(M.max())
        k = int(np.argmax(np.where(dans, M, -1.0)))
        res.append(dict(id=eid, type=typ, n=int(len(idx)), prominence=round(m4 / med, 2), rel=round(m2 / m4, 3),
                        a2=round(m2 / med, 2), decalage_sigma=round(float(j[k] / spx), 2)))
    nets = [r for r in res if r["prominence"] >= PROMINENCE_Q2]
    alignes = [r for r in nets if r["rel"] >= REL_Q2 and r["a2"] >= PROMINENCE_Q2]
    frac = len(alignes) / max(len(nets), 1)
    valide = len(alignes) >= N_ELEMENTS_MIN and frac >= 0.5
    motif = ("validée" if valide else
             f"{len(res)} élément(s) levé(s) dans le secteur (≥ {N_ELEMENTS_MIN} requis)" if len(res) < N_ELEMENTS_MIN else
             f"{len(alignes)} élément(s) aligné(s) sur {len(nets)} nets")
    return dict(valide=bool(valide), n_elements=len(res), n_nets=len(nets), n_alignes=len(alignes),
                part_alignes=round(frac, 2), motif=motif,
                alignes=[r["id"] for r in alignes][:12], detail=res[:40])


# --------------------------------------------------------------------------- Q4
def test_presence(im, xy, z, h, typ, rayon):
    """Test automatique de présence dans la boîte projetée : dict(auto, structure, vegetation, ...)."""
    p = im.p
    diam = DIAMETRES.get(typ, 0.15)
    if typ == "arbre":
        tr = detecter_axes(im, [("X", xy)], min(h, 2.2), diam, [z], bande=(0.1, 1.0))["par_hyp"].get("X") or {}
        G = geometrie(p, [("X", xy)], h, [z])[0]
        rc = max(rayon, 1.5)
        dw = math.degrees(math.atan2(rc, G["d"]))
        e_bas = math.degrees(math.atan2(z + 2.0 - p["cam"].C[2], G["d"]))
        e_haut = math.degrees(math.atan2(z + max(h, 4.0) - p["cam"].C[2], G["d"]))
        V, _, _ = fenetre(p["cam"], im.rgb.astype(np.float32), G["az"] - dw, G["az"] + dw, e_bas, e_haut,
                          max(dw / 40, 0.02), 40)
        s = V.sum(-1) + 1e-6
        exg = (2 * V[..., 1] - V[..., 0] - V[..., 2]) / s
        lum = s / 3.0
        veg = (exg > 0.06) & (lum < 200)
        frac = float(veg.mean())
        tronc = bool(tr.get("support") and tr.get("pied_ok") and abs(tr.get("residu") or 9) < 2.0)
        # la végétation du fond (arbres plus lointains dans la boîte) trompe l'indice : « présent » exige de la
        # végétation ET un tronc ; « absent » : ni l'un ni l'autre ; sinon indéterminé (revue obligatoire)
        if frac >= 0.25 and tronc:
            auto = "present"
        elif frac < 0.10 and not tr.get("support"):
            auto = "absent"
        else:
            auto = "indetermine"
        return dict(auto=auto, vegetation=round(frac, 3), tronc=tronc, tronc_valeur=tr.get("valeur"),
                    tronc_residu=None if tr.get("residu") is None else round(tr["residu"], 2), d_m=round(G["d"], 1))
    ax = detecter_axes(im, [("X", xy)], h, diam, [z])["par_hyp"].get("X") or {}
    G = geometrie(p, [("X", xy)], h, [z])[0]
    sup = bool(ax.get("support") and abs(ax.get("residu") or 9) < 2.0)
    auto = "present" if sup else ("absent" if (ax.get("valeur") or 0) < 1.5 else "indetermine")
    return dict(auto=auto, structure=sup, valeur=ax.get("valeur"),
                residu=None if ax.get("residu") is None else round(ax["residu"], 2), d_m=round(G["d"], 1))


def vignette_presence(im, xy, z, h, rayon, titre, taille=300):
    """Vignette perspective de la boîte projetée (pied, sommet, emprise) : PIL.Image."""
    from PIL import Image, ImageDraw
    from projection import camera_virtuelle, reechantillonner
    from coherence_preuves import POLICE_P
    p = im.p
    cam = p["cam"]
    pied = np.r_[xy, z]
    som = pied + [0, 0, h]
    M = (pied + som) / 2
    d3 = M - cam.C
    dist = float(np.linalg.norm(d3))
    fov = math.degrees(2 * math.atan((max(h, 2 * rayon) * 0.75 + 1.0) / max(dist, 1.0)))
    fov = float(np.clip(fov, 12.0, 90.0))
    lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
    tan = math.degrees(math.atan2(d3[2], math.hypot(d3[0], d3[1])))
    cv = camera_virtuelle(cam, lac, tan, fov, taille)
    img = reechantillonner(cam, im.rgb.astype(np.float32), cv)
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(out)
    ang = np.linspace(0, 2 * np.pi, 25)
    for zz, col in ((0.0, (255, 0, 255)), (h, (255, 0, 255))):
        ring = np.c_[xy[0] + rayon * np.cos(ang), xy[1] + rayon * np.sin(ang), np.full(25, z + zz)]
        uv, ok, _ = cv.projeter(ring)
        pts = [tuple(q) for q, k in zip(uv, ok) if k]
        if len(pts) > 1:
            dr.line(pts, fill=col, width=1)
    seg = np.array([pied, som])
    uv, ok, _ = cv.projeter(seg)
    if ok.all():
        dr.line([tuple(uv[0]), tuple(uv[1])], fill=(0, 230, 255), width=1)
    dr.rectangle([0, 0, taille, 13], fill=(0, 0, 0))
    dr.text((2, 0), titre[:60], fill=(255, 255, 255), font=POLICE_P)
    dr.rectangle([0, taille - 13, taille, taille], fill=(0, 0, 0))
    dr.text((2, taille - 13), f"{p['id']} {p['date']} d={dist:.1f} m", fill=(255, 255, 255), font=POLICE_P)
    return out


# --------------------------------------------------------------------------- lots
def executer(taches, faire_vignettes=True):
    """taches : [dict(pid, nature ('q2' | 'axe' | 'presence'), cle, args)] -> {(nature, cle, pid): résultat}.
    Une photo chargée une seule fois ; ordre déterministe (photo, nature, clé)."""
    cat = {p["id"]: p for p in PO.catalogue()}
    out = {}
    par = {}
    for t in taches:
        par.setdefault(t["pid"], []).append(t)
    for pid in sorted(par):
        im = Image1(cat[pid])
        for t in sorted(par[pid], key=lambda t: (t["nature"], str(t["cle"]))):
            a = t["args"]
            if t["nature"] == "q2":
                r = valider_pose_locale(im, a["xy"])
            elif t["nature"] == "axe":
                r = detecter_axes(im, a["hyps"], a["h"], a["diam"], a["zs"])
            elif t["nature"] == "presence":
                r = test_presence(im, a["xy"], a["z"], a["h"], a["type"], a["rayon"])
                if faire_vignettes:
                    r["_vignette"] = vignette_presence(im, a["xy"], a["z"], a["h"], a["rayon"], a["titre"])
            else:
                continue
            out[(t["nature"], t["cle"], pid)] = r
        del im
    return out
