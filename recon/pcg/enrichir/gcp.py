"""Points d'appui (GCP) pour le calage des photos Panoramax, et pointage automatique.

Familles de GCP (repère local, z = sol 2026 du paquet) :
- `mat`   : mâts verticaux (lampadaires, supports de feux, poteaux de panneaux, potelets, poteaux
            réseau, mâts de caméra) du paquet v1 (`objets/mobilier.geojson`), statut « existant
            (inchangé) » et confiance haute/moyenne ; segment pied -> sommet ; observation = axe ;
- `tronc` : troncs d'arbres levés par le GAM (`objets/arbres.geojson`, source levé topo) ;
- `sol`   : coins de bandes de passages piétons (`marquages/marquages_2026.geojson`, bandes
            « conserve » relevées par le GAM ou l'ortho 2022 ; bandes refaites en 2025 : valides
            seulement après les travaux) et points texturés de l'ortho PCRS 2022 tirés à la volée
            (`ORTHO-…`, valides seulement avant les travaux de 2025, hors zones construites ou
            modifiées après 2022).

Validité : chaque GCP porte [valide_de, valide_a] (dates ISO) ; une photo ne voit que les GCP
valides à sa date (un objet posé en 2025 ne prouve rien sur une photo de 2024, et réciproquement).

Pointage automatique :
- mâts / troncs : fenêtre (azimut, élévation) du repère local autour de la projection, où toute
  verticale est une colonne ; détecteur de barre = paires de gradients horizontaux de signes opposés
  à la largeur attendue, moyennées sur la hauteur du mât ; pic dans la fenêtre de recherche ;
- sol : vue perspective virtuelle centrée sur le point, rendu de l'ortho 2022 (ou des polygones de
  marquage) dans la même vue, corrélation normalisée (NCC) sur images passe-haut, pic distinct.
Chaque observation garde ses pixels HD, son score et la fenêtre utilisée (preuve vérifiable).
"""
import functools
import hashlib
import math

import numpy as np
from PIL import Image, ImageDraw

from camera import (DONNEES, O, echantillonner, image_rgb, lire_json, mnt, z_sol)
from projection import (azel_vers_pixel, camera_virtuelle, fenetre_azel, occulte_par_batiments,
                        ortho_valeur, reechantillonner, rendu_ortho, intersection_sol)

DATE_MIN, DATE_MAX = "2000-01-01", "2100-01-01"
DEBUT_TRAVAUX_2025 = "2025-06-01"     # phase 1 des travaux (la série 2025-05-18 est l'état avant)
FIN_TRAVAUX_2025 = "2026-01-31"       # finitions jusqu'au 30/01/2026
ORTHO_DATE = "2022-05-10"

DIAMETRES = {"lampadaire": 0.15, "support_feux": 0.11, "panneau": 0.07, "potelet": 0.12,
             "poteau_reseau": 0.24, "mat_camera": 0.15, "poteau_arret": 0.08}
POIDS = {"lampadaire": 1.0, "support_feux": 1.0, "panneau": 0.8, "potelet": 0.5,
         "poteau_reseau": 1.0, "mat_camera": 1.0, "poteau_arret": 0.7, "tronc": 0.5}
SIGMA_POS = {"haute": 0.25, "moyenne": 0.6}
BANDE_MIN_DEG = 2.5          # hauteur angulaire minimale d'un mât pour le pointer


# --------------------------------------------------------------------------- catalogue
def _id_court(*xs):
    return hashlib.sha1("|".join(map(str, xs)).encode()).hexdigest()[:6]


@functools.lru_cache(maxsize=1)
def catalogue_gcp():
    """Catalogue des GCP fixes (liste de dicts triée par id)."""
    out = []
    # ---- mâts
    mats = []
    for f in lire_json(DONNEES / "objets/mobilier.geojson")["features"]:
        p = f["properties"]
        t = p.get("type")
        if t not in DIAMETRES or p.get("x_local") is None:
            continue
        st = str(p.get("statut_2026") or "")
        conf = p.get("confiance")
        if conf not in SIGMA_POS:
            continue
        if st.startswith("existant"):
            de, a = DATE_MIN, DATE_MAX
        elif st.startswith("2026 confirm"):
            de, a = FIN_TRAVAUX_2025, DATE_MAX      # peut avoir été posé pendant les travaux
        else:
            continue
        h = float(p.get("hauteur_m") or 0)
        if h < 0.8:
            continue
        mats.append(dict(ids=[p["id"]], type=t, x=p["x_local"], y=p["y_local"], z=p["z_local"],
                         h=h, conf=conf, de=de, a=a, src=str(p.get("source") or "")[:160]))
    # fusion des objets portés par un même mât (panneaux sur lampadaire, doublons)
    mats.sort(key=lambda m: (-m["h"], m["ids"][0]))
    fus = []
    for m in mats:
        for g in fus:
            if math.hypot(m["x"] - g["x"], m["y"] - g["y"]) < 0.4:
                g["ids"].append(m["ids"][0])
                break
        else:
            fus.append(m)
    # mâts triangulés sur les photos calées (amorçage) : position et σ remplacent celles du paquet
    tri = _mats_triangules()
    for oid, t in sorted(tri.items()):
        if any(oid in m["ids"] for m in fus):
            continue
        p = t["prop"]
        voisin = next((m for m in fus if math.hypot(m["x"] - p["x_local"], m["y"] - p["y_local"]) < 0.4), None)
        if voisin is not None:            # même support (doublon du paquet) : un seul GCP
            voisin["ids"].append(oid)
            continue
        h = float(p.get("hauteur_m") or 2.0)
        fus.append(dict(ids=[oid], type=p["type"], x=p["x_local"], y=p["y_local"], z=p["z_local"], h=h,
                        conf="moyenne", de=DATE_MIN, a=DATE_MAX, src=str(p.get("source") or "")[:160]))
    for m in fus:
        t = next((tri[i] for i in m["ids"] if i in tri), None)
        if t is not None:
            m["src_tri"] = t
        ht = m["h"] - (0.8 if m["type"] == "panneau" else 0.4)
        x, y, sig, src = m["x"], m["y"], SIGMA_POS[m["conf"]], "paquet v1 objets/mobilier.geojson (" + m["src"] + ")"
        if "src_tri" in m:
            t = m["src_tri"]
            x, y = t["xy"]
            sig = t["sigma"]
            src = (f"triangulation Panoramax ({t['n']} photos calées, σ {t['sigma']:.2f} m, écart au paquet "
                   f"{t['ecart']:.2f} m) ; paquet : " + m["src"])
        z = z_sol(x, y)
        out.append(dict(
            id="MAT-" + m["ids"][0], famille="mat", type=m["type"], objets=sorted(m["ids"]),
            pied=[x, y, z], sommet=[x, y, z + max(ht, 0.6)],
            hauteur_m=m["h"], diametre_m=DIAMETRES[m["type"]], sigma_m=sig,
            poids=POIDS[m["type"]], valide_de=m["de"], valide_a=m["a"],
            source=src, confiance=m["conf"], triangule="src_tri" in m))
    # ---- troncs (arbres levés GAM)
    for f in lire_json(DONNEES / "objets/arbres.geojson")["features"]:
        p = f["properties"]
        if "GAM" not in str(p.get("source")) or p.get("x_local") is None:
            continue
        st = str(p.get("statut_2026") or "")
        if st.startswith("existant"):
            de, a = DATE_MIN, DATE_MAX
        elif st.startswith("absent"):
            de, a = DATE_MIN, "2025-05-31"
        else:
            continue
        hm = float(p.get("hauteur_m") or 0)
        if hm < 6:
            continue
        circ = p.get("circonference_cm")
        dia = float(circ) / math.pi / 100 if circ else 0.30
        z = p["z_local"]
        out.append(dict(
            id="TRONC-" + p["id"], famille="tronc", type="tronc", objets=[p["id"]],
            pied=[p["x_local"], p["y_local"], z], sommet=[p["x_local"], p["y_local"], z + 2.0],
            hauteur_m=hm, diametre_m=round(min(max(dia, 0.15), 0.8), 3), sigma_m=0.15,
            poids=POIDS["tronc"], valide_de=de, valide_a=a,
            source="paquet v1 objets/arbres.geojson (levé GAM, tronc)", confiance="haute"))
    # ---- coins de bandes de passages piétons
    for f in lire_json(DONNEES / "marquages/marquages_2026.geojson")["features"]:
        p = f["properties"]
        if p.get("type") != "passage_pieton_bande":
            continue
        zone = p.get("zone")
        if zone == "conserve":
            de, a = DATE_MIN, DATE_MAX
        elif zone in ("refait_2025", "resurface_2025"):
            de, a = FIN_TRAVAUX_2025, DATE_MAX
        else:
            continue
        r = np.asarray(f["geometry"]["coordinates"][0], dtype=np.float64)[:-1, :2] - np.array(O[:2])
        if len(r) != 4:
            continue
        for k, q in enumerate(r):
            z = z_sol(*q) + 0.003
            out.append(dict(
                id=f"ZEB-{p['id']}-c{k}", famille="sol", type="coin_zebra", objets=[p["id"]],
                point=[float(q[0]), float(q[1]), z], sigma_m=0.05 if "GAM" in p["source"] else 0.10,
                poids=1.0, valide_de=de, valide_a=a,
                source=f"paquet v1 marquages_2026 ({p['source'][:60]}, zone {zone})",
                confiance=p.get("confiance")))
    # ---- coins des autres marquages (tirets, lignes, flèches, damiers, symboles)
    for f in lire_json(DONNEES / "marquages/marquages_2026.geojson")["features"]:
        p = f["properties"]
        if p.get("type") not in TYPES_COINS or f["geometry"]["type"] != "Polygon":
            continue
        de, a = _validite_marquage(p)
        if de is None:
            continue
        zone = p.get("zone")
        r = np.asarray(f["geometry"]["coordinates"][0], dtype=np.float64)[:-1, :2] - np.array(O[:2])
        if len(r) < 3 or len(r) > 24:
            continue
        if p.get("type") in TYPES_LIGNES and len(r) == 4:
            out += _echantillons_ligne(p, r, de, a)
        for k in _sommets_vifs(r):
            q = r[k]
            out.append(dict(
                id=f"MQC-{p['id']}-c{k}", famille="sol", type="coin_marquage", objets=[p["id"]],
                point=[float(q[0]), float(q[1]), z_sol(*q) + 0.003],
                sigma_m=0.05 if "GAM" in str(p.get("source")) else 0.08, poids=0.8,
                valide_de=de, valide_a=a,
                source=f"paquet v1 marquages_2026 ({p['type']}, {str(p.get('source'))[:50]}, zone {zone})",
                confiance=p.get("confiance")))
    out.sort(key=lambda g: g["id"])
    return out


TYPES_COINS = ("ligne_discontinue", "ligne_continue", "fleche", "ligne_effet_feux", "hachures",
               "damier", "symbole", "symbole_velo", "chevrons", "fantome")
TYPES_LIGNES = ("ligne_discontinue", "ligne_continue", "ligne_effet_feux", "fantome")


def _validite_marquage(p):
    """[de, a] de validité d'un marquage du paquet v1 : conservé -> toujours ; refait ou resurfacé
    en 2025 -> après les travaux ; fantôme (présent en 2022, effacé en 2025) -> avant les travaux."""
    zone, etat = p.get("zone"), p.get("etat")
    if etat == "fantome" or p.get("type") == "fantome":
        return DATE_MIN, "2025-05-31"
    if zone == "conserve":
        return DATE_MIN, DATE_MAX
    if zone in ("refait_2025", "resurface_2025"):
        return FIN_TRAVAUX_2025, DATE_MAX
    return None, None


def _echantillons_ligne(p, r, de, a, pas=1.5):
    """Échantillons de l'axe d'un marquage linéaire rectangulaire (4 sommets) : GCP `ligne_marquage`
    (observation 1D : le pixel doit tomber sur l'axe ; résidu = angle au plan caméra-axe)."""
    e = [np.linalg.norm(r[(k + 1) % 4] - r[k]) for k in range(4)]
    k = int(np.argmin(e))                    # petit côté
    m0 = (r[k] + r[(k + 1) % 4]) / 2
    m1 = (r[(k + 2) % 4] + r[(k + 3) % 4]) / 2
    L = float(np.linalg.norm(m1 - m0))
    if L < 1.5:
        return []
    A = np.r_[m0, z_sol(*m0) + 0.003]
    B = np.r_[m1, z_sol(*m1) + 0.003]
    n = max(1, int(L // pas))
    out = []
    for j in range(n):
        t = (j + 0.5) / n
        q = m0 + t * (m1 - m0)
        out.append(dict(
            id=f"MQL-{p['id']}-s{j}", famille="sol", type="ligne_marquage", objets=[p["id"]],
            point=[float(q[0]), float(q[1]), z_sol(*q) + 0.003], pied=A.tolist(), sommet=B.tolist(),
            sigma_m=0.05 if "GAM" in str(p.get("source")) else 0.08, poids=0.5, valide_de=de, valide_a=a,
            source=f"paquet v1 marquages_2026 (axe de {p['type']}, {str(p.get('source'))[:50]})",
            confiance=p.get("confiance")))
    return out


def _sommets_vifs(r, seuil_deg=50.0):
    """Indices des sommets d'un anneau où la direction tourne d'au moins seuil_deg."""
    a = np.roll(r, 1, axis=0) - r
    b = np.roll(r, -1, axis=0) - r
    na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    ok = (na > 0.05) & (nb > 0.05)
    cosang = np.sum(a * b, axis=1) / np.maximum(na * nb, 1e-12)
    interieur = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    return [int(k) for k in np.nonzero(ok & (interieur <= 180 - seuil_deg))[0]]


def _mats_triangules():
    """Mâts triangulés de façon fiable (triangulation.json, vérification du mobilier) :
    {id objet: dict(xy, sigma, n, ecart, prop)}. Vide si le fichier n'existe pas (1re passe).
    Désactivable par la variable d'environnement PJ_SANS_TRIANGULATION=1."""
    import os
    f = DONNEES.parents[1] / "v2/enrichi/poses/triangulation.json"
    if os.environ.get("PJ_SANS_TRIANGULATION") or not f.exists():
        return {}
    mob = {x["properties"]["id"]: x["properties"]
           for x in lire_json(DONNEES / "objets/mobilier.geojson")["features"]}
    out = {}
    for r in lire_json(f).get("verification_mobilier", {}).get("resultats", []):
        if (not r.get("fiable") or r.get("n_inliers", 0) < 3
                or r.get("decision") not in ("garder", "affiner", "deplacer")):
            continue
        if r.get("decision") == "garder" and (r.get("revue_visuelle") or {}).get("verdict") == "correction_rejetee":
            continue                       # la triangulation s'est trompée de support : on garde le paquet
        oid = r["objets"][0]
        p = mob.get(oid)
        if p is None or p.get("x_local") is None or p.get("type") not in DIAMETRES:
            continue
        sig = max(0.08, float(np.hypot(*r["ecart_type_m"])))
        out[oid] = dict(xy=r["position_triangulee"], sigma=sig, n=r["n_inliers"], ecart=r["ecart_m"], prop=p)
    return out


def valide(g, date):
    return g["valide_de"] <= date <= g["valide_a"]


def gcp_par_id():
    return {g["id"]: g for g in catalogue_gcp()}


# --------------------------------------------------------------------------- zones exclues (ortho)
@functools.lru_cache(maxsize=1)
def _zones_changees():
    """Polygones locaux où l'ortho 2022 ne montre pas l'état de la photo :
    (construit_2023_2024, modifie_2025 + zones de chaussée reprises en 2025)."""
    c23, m25 = [], []
    for f in lire_json(DONNEES / "surfaces/surfaces_2026.geojson")["features"]:
        e = f["properties"].get("etat")
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            r = np.asarray(poly[0], dtype=np.float64)[:, :2] - np.array(O[:2])
            if e == "construit_2023_2024":
                c23.append(r)
            elif e == "modifie_2025":
                m25.append(r)
    for f in lire_json(DONNEES / "relief/relief_zones_2026.geojson")["features"]:
        z = f["properties"].get("zone")
        if z in ("ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee",
                 "ancienne_chaussee_trottoir_par_defaut"):
            g = f["geometry"]
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for poly in polys:
                m25.append(np.asarray(poly[0], dtype=np.float64)[:, :2] - np.array(O[:2]))
    return c23, m25


def _dans(Q, anneaux):
    Q = np.atleast_2d(Q)
    m = np.zeros(len(Q), bool)
    for r in anneaux:
        lo, hi = r.min(0), r.max(0)
        c = np.all((Q >= lo) & (Q <= hi), axis=1)
        if not c.any():
            continue
        x, y = Q[c, 0][:, None], Q[c, 1][:, None]
        xa, ya = r[:, 0][None], r[:, 1][None]
        xb, yb = np.roll(r[:, 0], -1)[None], np.roll(r[:, 1], -1)[None]
        cond = (ya > y) != (yb > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = xa + (y - ya) * (xb - xa) / (yb - ya)
        m[np.nonzero(c)[0]] |= (np.count_nonzero(cond & (x < xi), axis=1) % 2).astype(bool)
    return m


@functools.lru_cache(maxsize=1)
def _zones_non_revetues():
    """Polygones locaux où le sol de l'ortho n'est pas un revêtement visible et stable
    (espaces verts, bâti, parkings, « autre ») et couronnes d'arbres (disques)."""
    polys = []
    for f in lire_json(DONNEES / "surfaces/surfaces_2026.geojson")["features"]:
        if f["properties"].get("classe") not in ("espace_vert", "terre_plein_vegetal", "batiment",
                                                  "parking", "autre"):
            continue
        g = f["geometry"]
        for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            polys.append(np.asarray(poly[0], dtype=np.float64)[:, :2] - np.array(O[:2]))
    cour = []
    for f in lire_json(DONNEES / "objets/arbres.geojson")["features"]:
        p = f["properties"]
        if p.get("x_local") is None:
            continue
        dc = float(p.get("diametre_couronne_m") or 4.0)
        cour.append((p["x_local"], p["y_local"], 0.5 * dc + 0.3))
    return polys, np.array(cour, dtype=np.float64).reshape(-1, 3)


def sol_revetu(Q):
    """Vrai pour les points (N, 2) sur revêtement dégagé (hors espaces verts, bâti, parkings,
    couronnes d'arbres)."""
    Q = np.atleast_2d(Q)
    polys, cour = _zones_non_revetues()
    ok = ~_dans(Q, polys)
    if len(cour):
        d = np.hypot(Q[:, None, 0] - cour[None, :, 0], Q[:, None, 1] - cour[None, :, 1])
        ok &= ~np.any(d < cour[None, :, 2], axis=1)
    return ok


def ortho_utilisable(Q, date):
    """Vrai où l'ortho 2022 peut représenter le sol à la date de la photo (approché) :
    jamais après la fin des travaux ; hors surfaces construites en 2023-2024 pour les photos
    postérieures à 2022. Pendant les travaux 2025 (juin 2025 - janvier 2026) les zones reprises
    restent candidates : le chantier avance par phases et la corrélation (NCC + distinction + RANSAC)
    rejette ce qui a changé."""
    if date >= FIN_TRAVAUX_2025:
        return np.zeros(len(np.atleast_2d(Q)), bool)
    c23, _ = _zones_changees()
    ok = np.ones(len(np.atleast_2d(Q)), bool)
    if date >= "2023-01-01":
        ok &= ~_dans(Q, c23)
    return ok


# --------------------------------------------------------------------------- filtres
def _flou_boite(a, r):
    """Moyenne glissante (2r+1)² (bords répliqués)."""
    if r <= 0:
        return a
    p = np.pad(a, r + 1, mode="edge")
    c = p.cumsum(0).cumsum(1)
    n = 2 * r + 1
    s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    return (s / (n * n))[: a.shape[0], : a.shape[1]]


def passe_haut(a, r=6):
    return a - _flou_boite(a, r)


def ncc_carte(I, T):
    """NCC de T (t×t) sur toutes les positions valides de I (n×n) : carte (n−t+1)²."""
    t = T.shape[0]
    Tz = T - T.mean()
    nt = np.sqrt((Tz * Tz).sum()) + 1e-9
    W = np.lib.stride_tricks.sliding_window_view(I, T.shape)
    num = np.einsum("ijkl,kl->ij", W, Tz, optimize=True)
    p = np.pad(I, ((1, 0), (1, 0)))
    c1 = p.cumsum(0).cumsum(1)
    c2 = (p * p).cumsum(0).cumsum(1)
    s1 = c1[t:, t:] - c1[:-t, t:] - c1[t:, :-t] + c1[:-t, :-t]
    s2 = c2[t:, t:] - c2[:-t, t:] - c2[t:, :-t] + c2[:-t, :-t]
    var = np.maximum(s2 - s1 * s1 / (t * t), 1e-12)
    return num / (np.sqrt(var) * nt)


# --------------------------------------------------------------------------- sélection
def lat_min_cam(ph):
    return ph.seq.get("lat_min", -89.0) if ph.is360 else -89.0


def selection(ph, cam, dmax=40.0, marge=0.0, troncs=False):
    """GCP fixes valides à la date de la photo, à moins de dmax (+ marge) m, dans le champ,
    au-dessus du porteur (capot), non occultés par les bâtiments. Les troncs sont exclus par
    défaut : haies, voitures et feuillage font accrocher le détecteur sur un mât voisin."""
    out = []
    for g in catalogue_gcp():
        if not valide(g, ph.date) or (g["famille"] == "tronc" and not troncs):
            continue
        P = np.array(g["pied"] if g["famille"] != "sol" else g["point"], dtype=np.float64)
        d = math.hypot(P[0] - cam.C[0], P[1] - cam.C[1])
        if d > dmax + marge or d < 1.5:
            continue
        if g["famille"] == "sol":
            Pm = P
        else:
            Pm = (P + np.array(g["sommet"])) / 2
        uv, ok, _ = cam.projeter(Pm[None])
        if not ph.is360 and marge == 0 and not ok[0]:
            continue
        if occulte_par_batiments(cam.C, Pm[None])[0]:
            continue
        out.append(g)
    return out


# --------------------------------------------------------------------------- mâts
def bande_elevation(cam, g, d_lo=None, d_hi=None, lat_min=-89.0):
    """Bande d'élévation (deg) sûrement couverte par le mât pour des distances dans [d_lo, d_hi]."""
    P0, P1 = np.array(g["pied"]), np.array(g["sommet"])
    d = math.hypot(P0[0] - cam.C[0], P0[1] - cam.C[1])
    d_lo = d if d_lo is None else max(d_lo, 0.8)
    d_hi = d if d_hi is None else d_hi
    zc = cam.C[2]
    zb, zt = P0[2] + 0.35 - zc, P1[2] - 0.25 - zc
    lo = max(math.degrees(math.atan2(zb, d_hi)), math.degrees(math.atan2(zb, d_lo)))
    hi = min(math.degrees(math.atan2(zt, d_hi)), math.degrees(math.atan2(zt, d_lo)))
    lo = max(lo, lat_min + 1.5 + _assiette(cam), -60.0)
    hi = min(hi, 65.0)
    return lo, hi


def _assiette(cam):
    return abs(cam.pose[4]) + abs(cam.pose[5])


def profil_barre(cam, img, az0, az1, el0, el1, diam_deg, pas, avec_coherence=False):
    """Profil de détection de barre verticale sur [az0, az1] (deg) dans la bande [el0, el1].

    Réponse de barre par ligne : √max(0, −gx(c−k)·gx(c+k)) (deux bords de signes opposés à la
    largeur attendue, quelle que soit la polarité), normalisée par la médiane de la ligne (fond :
    ciel lisse ou feuillage texturé). Score de colonne = 35e centile sur les lignes de la bande :
    un mât doit répondre sur la plus grande partie de sa hauteur (une pelle, une grille ou une
    branche ne répondent que localement). Cohérence = part des lignes où la réponse dépasse 3× le fond.
    Renvoie (az, score, k) ou (az, score, k, coherence) si avec_coherence."""
    V, A, E, ok = fenetre_azel(cam, img, az0, az1, el0, el1, pas)
    vide = (A, np.zeros(len(A)), 1) + ((np.zeros(len(A)),) if avec_coherence else ())
    if V.shape[0] < 5 or V.shape[1] < 9:
        return vide
    V = np.where(ok, V, np.nan)
    Vs = V.copy()
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4
    gx = np.full_like(Vs, np.nan)
    gx[:, 1:-1] = (Vs[:, 2:] - Vs[:, :-2]) / 2
    hw = max(1.0, 0.5 * diam_deg / pas)
    meilleur = None
    nl = V.shape[0]
    for k in sorted({max(1, int(round(hw * f))) for f in (0.7, 1.0, 1.5)}):
        if 2 * k + 1 >= V.shape[1]:
            continue
        b = np.sqrt(np.maximum(0.0, -gx[:, :-2 * k] * gx[:, 2 * k:]))
        with np.errstate(all="ignore"):
            m = np.nanmedian(b, axis=1)
            mg = np.nanmedian(m) if np.any(np.isfinite(m)) else 0.0
            m = np.maximum(np.nan_to_num(m), 0.25 * mg + 2e-4)
            r = b / m[:, None]
            n = np.isfinite(r).sum(0)
            S = np.nanpercentile(np.where(np.isfinite(r), r, np.nan), 35, axis=0)
            coh = np.nansum(r > 3.0, axis=0) / np.maximum(n, 1)
        S = np.where(n > 0.6 * nl, np.nan_to_num(S), 0.0)
        coh = np.where(n > 0.6 * nl, coh, 0.0)
        S = np.r_[np.zeros(k), S, np.zeros(k)]
        coh = np.r_[np.zeros(k), coh, np.zeros(k)]
        if meilleur is None or S.max() > meilleur[1].max():
            meilleur = (k, S, coh)
    if meilleur is None:
        return vide
    k, S, coh = meilleur
    return (A, S, k, coh) if avec_coherence else (A, S, k)


def normaliser_profil(S):
    """Évidence 0..1 : excès sur la médiane rapporté à 5 MAD."""
    v = S[S > 0]
    if len(v) < 10:
        return np.zeros_like(S)
    med = np.median(v)
    mad = np.median(np.abs(v - med)) * 1.4826 + 1e-6
    return np.clip((S - med) / (5 * mad), 0, 1)


def detecter_mat(ph, cam, img, g, recherche_deg, pas=None, prior_deg=None, n_pics=1):
    """Pointe l'axe du mât/tronc g autour de sa projection (± recherche_deg en azimut).
    Renvoie une observation dict(type='ligne', uv=[[u,v],[u,v]], az, el, score, distinction) ou None ;
    avec n_pics > 1, la liste des n meilleurs pics distincts (candidats pour la vérification)."""
    P0 = np.array(g["pied"], dtype=np.float64)
    d = math.hypot(P0[0] - cam.C[0], P0[1] - cam.C[1])
    az_p = math.degrees(math.atan2(P0[0] - cam.C[0], P0[1] - cam.C[1])) % 360
    el0, el1 = bande_elevation(cam, g, lat_min=lat_min_cam(ph))
    if el1 - el0 < BANDE_MIN_DEG:
        return None
    if math.degrees(g["diametre_m"] / max(d, 0.5)) * cam.px_par_rad * math.pi / 180 < 1.5:
        return None        # mât de moins de 1,5 px de large : pointage non fiable
    if pas is None:
        pas = min(0.06, 0.5 / (cam.px_par_rad * math.pi / 180) * 2)   # ≈ 1 px natif
        pas = max(pas, 0.02)
    diam_deg = math.degrees(g["diametre_m"] / max(d, 0.5))
    A, S, k, coh = profil_barre(cam, img, az_p - recherche_deg, az_p + recherche_deg, el0, el1, diam_deg,
                                pas, avec_coherence=True)
    if not np.any(S > 0):
        return None
    da_all = ((A - az_p + 180) % 360) - 180
    crit = S * np.exp(-0.5 * (da_all / prior_deg) ** 2) if prior_deg else S
    excl = max(3 * k, int(round(0.6 / pas)))
    v = S[S > 0]
    med = float(np.median(v)) if len(v) else 0.0
    els = [el0 + 0.25 * (el1 - el0), el0 + 0.75 * (el1 - el0)]
    pics = []
    reste = crit.copy()
    for _ in range(max(1, n_pics)):
        i = int(np.argmax(reste))
        if reste[i] <= 0:
            break
        reste[max(0, i - excl): i + excl + 1] = 0
        if i <= 0 or i >= len(S) - 1:
            continue
        s_pic = S[i]
        s2 = S.copy()
        s2[max(0, i - excl): i + excl + 1] = 0
        second = s2.max() if s2.size else 0.0
        a_, b_, c_ = S[i - 1], S[i], S[i + 1]
        den = a_ - 2 * b_ + c_
        di = 0.5 * (a_ - c_) / den if abs(den) > 1e-12 else 0.0
        az = A[i] + float(np.clip(di, -0.5, 0.5)) * (A[1] - A[0])
        uv, ok = azel_vers_pixel(cam, [az, az], els)
        if not ok.all():
            continue
        pics.append(dict(gcp=g["id"], type="ligne", uv=uv.tolist(), az=float(az), el=els,
                         score=float(s_pic / (med + 1e-6)), distinction=float(s_pic / (second + 1e-9)),
                         coherence=float(coh[i]), force=float(s_pic), bande_deg=[float(el0), float(el1)],
                         ecart_prediction_deg=float(((az - az_p + 180) % 360) - 180),
                         recherche_deg=float(recherche_deg), distance_m=float(d), auto=True))
    if n_pics > 1:
        return pics
    return pics[0] if pics else None


# --------------------------------------------------------------------------- sol
def points_sol_ortho(ph, cam, dmin=3.0, dmax=14.0, pas=0.6, n_max=90):
    """Points texturés (coins plutôt qu'arêtes) de l'ortho 2022 autour de la caméra, utilisables
    à la date de la photo. Renvoie une liste de GCP dynamiques `ORTHO-x_y`."""
    if ph.date >= FIN_TRAVAUX_2025:
        return []
    C = cam.C
    xs = np.arange(C[0] - dmax, C[0] + dmax + 1e-9, pas)
    ys = np.arange(C[1] - dmax, C[1] + dmax + 1e-9, pas)
    X, Y = np.meshgrid(xs, ys)
    Q = np.c_[X.ravel(), Y.ravel()]
    r = np.hypot(Q[:, 0] - C[0], Q[:, 1] - C[1])
    Q = Q[(r >= dmin) & (r <= dmax)]
    if not ph.is360:
        P = np.c_[Q, mnt()(Q[:, 0] + O[0], Q[:, 1] + O[1]) - O[2]]
        _, ok, _ = cam.projeter(P)
        Q = Q[ok]
    Q = Q[ortho_utilisable(Q, ph.date)]
    if len(Q) == 0:
        return []
    Q = Q[sol_revetu(Q)]
    if len(Q) == 0:
        return []
    # structure de l'ortho dans une fenêtre de 0,8 m (pixels 5 cm)
    off = np.arange(-8, 9) * 0.05
    OX, OY = np.meshgrid(off, off)
    sc = []
    for q in Q:
        v = ortho_valeur(q[0] + OX, q[1] + OY)
        if not np.all(np.isfinite(v)) or np.percentile(v, 95) - np.percentile(v, 5) < 0.18:
            sc.append(0.0)
            continue
        gy, gx = np.gradient(v)
        a, b, c = (gx * gx).mean(), (gx * gy).mean(), (gy * gy).mean()
        tr, det = a + c, a * c - b * b
        lmin = tr / 2 - math.sqrt(max(tr * tr / 4 - det, 0))
        sc.append(lmin)
    sc = np.array(sc)
    ordre = np.argsort(-sc)
    garde = []
    for i in ordre:
        if sc[i] < 2e-4 or len(garde) >= n_max:
            break
        if all(math.hypot(*(Q[i] - Q[j])) > 1.2 for j in garde):
            garde.append(i)
    out = []
    for i in garde:
        q = Q[i]
        z = float(mnt()(q[0] + O[0], q[1] + O[1])) - O[2]
        out.append(dict(id=f"ORTHO-{q[0]:.1f}_{q[1]:.1f}", famille="sol", type="texture_ortho",
                        point=[float(q[0]), float(q[1]), z], sigma_m=0.08, poids=0.7,
                        valide_de=DATE_MIN, valide_a=FIN_TRAVAUX_2025,
                        source="ortho PCRS 5 cm 2022 + MNT 2026 (point de texture)", confiance="moyenne",
                        coinitude=float(sc[i])))
    return out


@functools.lru_cache(maxsize=1)
def _marquages_polygones():
    out = []
    for f in lire_json(DONNEES / "marquages/marquages_2026.geojson")["features"]:
        p, g = f["properties"], f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
        for poly in polys:
            r = np.asarray(poly[0], dtype=np.float64)[:, :2] - np.array(O[:2])
            de, a = _validite_marquage(p)
            if de is not None:
                out.append((r, de, a))
    return out


def rendu_vecteur(cam, uv, date):
    """Rendu synthétique des marquages (polygones v1/GAM) valides à la date : 0,85 dans le
    marquage, 0,25 ailleurs (chaussée). Sert de gabarit après travaux (pas d'ortho)."""
    d = cam.rayons(uv)
    t = intersection_sol(cam.C, d)
    X = cam.C + t[:, None] * d
    val = np.full(len(uv), 0.25)
    val[~np.isfinite(t)] = np.nan
    ok = np.isfinite(t)
    lo, hi = np.nanmin(X[ok, :2], 0) if ok.any() else (0, 0), np.nanmax(X[ok, :2], 0) if ok.any() else (0, 0)
    anneaux = []
    for r, de, a in _marquages_polygones():
        if not de <= date <= a:
            continue
        if np.all(r.max(0) >= lo) and np.all(r.min(0) <= hi):
            anneaux.append(r)
    if anneaux and ok.any():
        m = _dans(X[ok, :2], anneaux)
        v = val[ok]
        v[m] = 0.85
        val[ok] = v
    return val


def apparier_sol(ph, cam, img, g, recherche_px, t=41, gabarit="auto", echelle=1.0, diag=False,
                 carte=False, contrainte=None):
    """Pointe le point de sol g par corrélation entre la photo et le rendu du sol (ortho 2022 ou
    marquages vectoriels) dans une vue virtuelle native centrée sur le point.
    Renvoie dict(type='point', uv=[u, v], ncc, distinction) ou None."""
    P = np.array(g["point"], dtype=np.float64)
    d3 = P - cam.C
    dist = float(np.linalg.norm(d3))
    lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
    tan = math.degrees(math.atan2(d3[2], math.hypot(d3[0], d3[1])))
    # au-dessus du porteur ?
    c = cam.monde_vers_cam(P[None])[0]
    lat_c = math.degrees(math.atan2(c[2], math.hypot(c[0], c[1])))
    if lat_c < lat_min_cam(ph) + 1.5:
        return dict(gcp=g["id"], rejet="sous le porteur") if diag else None
    S = int(recherche_px)
    n = t + 2 * S
    f = cam.px_par_rad * echelle
    fov = math.degrees(2 * math.atan((n / 2) / f))
    cv = camera_virtuelle(cam, lac, tan, fov, n)
    I = reechantillonner(cam, img, cv)
    jj, ii = np.mgrid[0:t, 0:t]
    uvt = np.c_[ii.ravel() + S + 0.5, jj.ravel() + S + 0.5]
    if gabarit == "auto":
        # points de texture : ortho 2022 ; marquages : rendu vectoriel (insensible aux couronnes et
        # aux ombres de l'ortho) ET ortho quand elle est utilisable à la date -> meilleur des deux
        if g["type"] == "texture_ortho":
            gabarit = "ortho"
        elif ph.date < FIN_TRAVAUX_2025 and ortho_utilisable(P[None, :2], ph.date)[0]:
            kw = dict(t=t, echelle=echelle, diag=diag, carte=carte, contrainte=contrainte)
            ov = apparier_sol(ph, cam, img, g, recherche_px, gabarit="vecteur", **kw)
            oo = apparier_sol(ph, cam, img, g, recherche_px, gabarit="ortho", **kw)
            bons = [o for o in (ov, oo) if o is not None and "rejet" not in o]
            if not bons:
                return ov if ov is not None else oo
            o = max(bons, key=lambda x: x["ncc"])
            if carte and len(bons) == 2:
                o = dict(o, carte=np.maximum(ov["carte"], oo["carte"]))
            return o
        else:
            gabarit = "vecteur"
    if gabarit == "ortho":
        Tv, _ = rendu_ortho(cv, uvt)
    else:
        Tv = rendu_vecteur(cv, uvt, ph.date)
    Tv = Tv.reshape(t, t)
    if gabarit == "vecteur" and np.all(np.isfinite(Tv)):
        Tv = _flou_boite(Tv, 1)
    est_ligne = g["type"] == "ligne_marquage"
    rejet = (lambda m: dict(gcp=g["id"], rejet=m) if diag else None)
    if not np.all(np.isfinite(Tv)) or np.std(Tv) < 0.02:
        return rejet("gabarit vide ou plat")
    # le gabarit doit avoir de la structure 2D (pas une simple arête)
    gy, gx = np.gradient(Tv)
    a, b, c_ = (gx * gx).mean(), (gx * gy).mean(), (gy * gy).mean()
    tr, det = a + c_, a * c_ - b * b
    l1 = tr / 2 + math.sqrt(max(tr * tr / 4 - det, 0))
    l2 = tr / 2 - math.sqrt(max(tr * tr / 4 - det, 0))
    if l2 < 0.05 * l1 and not est_ligne:
        return rejet("gabarit sans coin (arête seule)")
    # même résolution effective : la photo est floutée à l'empreinte d'un pixel d'ortho (5 cm)
    rb = int(round(0.4 * 0.05 / max(dist, 0.5) * f)) if gabarit == "ortho" else 1
    if rb > 0:
        I = _flou_boite(I, rb)
    rh = max(5, 2 * rb + 3)
    Ih = passe_haut(I, rh)
    Th = passe_haut(Tv, rh)
    Ncc = ncc_carte(Ih, Th)
    Ncc_brute = Ncc
    if contrainte is not None:
        # pic cherché seulement à ±r du décalage (du, dv) imposé (consensus de toute la photo)
        cu, cv_, r = contrainte
        i0, j0 = int(round(cu + S)), int(round(cv_ + S))
        Nm = np.full_like(Ncc, -1.0)
        sl = (slice(max(0, j0 - r), max(0, j0 + r + 1)), slice(max(0, i0 - r), max(0, i0 + r + 1)))
        Nm[sl] = Ncc[sl]
        Ncc = Nm
    j, i = np.unravel_index(int(np.argmax(Ncc)), Ncc.shape)
    pic = float(Ncc[j, i])
    N2 = Ncc.copy()
    N2[max(0, j - 4): j + 5, max(0, i - 4): i + 5] = -1
    second = float(N2.max())
    if 0 < i < Ncc.shape[1] - 1:
        a_, b_, c2 = Ncc[j, i - 1], Ncc[j, i], Ncc[j, i + 1]
        den = a_ - 2 * b_ + c2
        di = 0.5 * (a_ - c2) / den if abs(den) > 1e-9 else 0.0
    else:
        di = 0.0
    if 0 < j < Ncc.shape[0] - 1:
        a_, b_, c2 = Ncc[j - 1, i], Ncc[j, i], Ncc[j + 1, i]
        den = a_ - 2 * b_ + c2
        dj = 0.5 * (a_ - c2) / den if abs(den) > 1e-9 else 0.0
    else:
        dj = 0.0
    # centre du gabarit apparié dans la vue virtuelle
    uc = i + float(np.clip(di, -0.5, 0.5)) + t / 2
    vc = j + float(np.clip(dj, -0.5, 0.5)) + t / 2
    dirw = cv.rayons(np.array([[uc, vc]]))
    uv, ok = cam.cam_vers_pixel(dirw @ cam.R.T)
    if not ok[0]:
        return None
    if est_ligne:
        # le long de l'axe, le pic est une crête : seule la position transverse est observée
        return dict(gcp=g["id"], type="ligne", uv=[uv[0].tolist()], ncc=pic, distinction=1.0,
                    decalage_px=[float(uc - n / 2), float(vc - n / 2)], recherche_px=S, echelle=echelle,
                    distance_m=dist, gabarit=gabarit, auto=True,
                    bord=bool(i == 0 or j == 0 or i == Ncc.shape[1] - 1 or j == Ncc.shape[0] - 1),
                    **({"carte": Ncc_brute, "vue": cv, "n_vue": n} if carte else {}))
    return dict(gcp=g["id"], type="point", uv=uv[0].tolist(), ncc=pic, distinction=pic - second,
                decalage_px=[float(uc - n / 2), float(vc - n / 2)], recherche_px=S, echelle=echelle,
                distance_m=dist, gabarit=gabarit, auto=True,
                bord=bool(i == 0 or j == 0 or i == Ncc.shape[1] - 1 or j == Ncc.shape[0] - 1),
                **({"carte": Ncc_brute, "vue": cv, "n_vue": n} if carte else {}))


# --------------------------------------------------------------------------- planches de contrôle
def vignette(ph, cam, P, taille=200, fov=None, segment=None, obs_uv=None, titre="", couleur=(255, 0, 255)):
    """Vignette perspective centrée sur P (3D) : croix magenta = projection de P (ou segment),
    cercle vert = pixel observé (obs_uv, liste de pixels HD). Renvoie PIL.Image."""
    P = np.asarray(P, dtype=np.float64)
    d3 = P - cam.C
    dist = float(np.linalg.norm(d3))
    if fov is None:
        fov = float(np.clip(math.degrees(2 * math.atan(2.0 / max(dist, 0.5))), 4.0, 40.0))
    lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
    tan = math.degrees(math.atan2(d3[2], math.hypot(d3[0], d3[1])))
    cv = camera_virtuelle(cam, lac, tan, fov, taille)
    img = reechantillonner(cam, image_rgb(ph.id8).astype(np.float32), cv)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    if segment is not None:
        A, B = np.asarray(segment[0], float), np.asarray(segment[1], float)
        pts = A + np.linspace(0, 1, 30)[:, None] * (B - A)
        uv, ok, _ = cv.projeter(pts)
        uv = uv[ok]
        if len(uv) > 1:
            dr.line([tuple(p) for p in uv], fill=couleur, width=1)
    uv, ok, _ = cv.projeter(P[None])
    if ok[0]:
        u, v = uv[0]
        dr.line([(u - 7, v), (u - 2, v)], fill=couleur, width=1)
        dr.line([(u + 2, v), (u + 7, v)], fill=couleur, width=1)
        dr.line([(u, v - 7), (u, v - 2)], fill=couleur, width=1)
        dr.line([(u, v + 2), (u, v + 7)], fill=couleur, width=1)
    if obs_uv is not None:
        for q in np.atleast_2d(obs_uv):
            dirw = cam.rayons(np.asarray(q, float)[None])
            uvv, okv = cv.cam_vers_pixel(dirw @ cv.R.T)
            if okv[0]:
                u, v = uvv[0]
                dr.ellipse([u - 4, v - 4, u + 4, v + 4], outline=(0, 255, 0))
    if titre:
        dr.rectangle([0, 0, taille, 12], fill=(0, 0, 0))
        dr.text((2, 0), titre[:40], fill=(255, 255, 255))
    return im


__all__ = ["catalogue_gcp", "valide", "gcp_par_id", "selection", "detecter_mat", "profil_barre",
           "normaliser_profil", "bande_elevation", "points_sol_ortho", "apparier_sol",
           "ortho_utilisable", "sol_revetu", "vignette", "lat_min_cam", "passe_haut", "ncc_carte"]
