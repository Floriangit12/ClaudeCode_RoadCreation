"""Choix automatique de 6 à 12 photos Panoramax récentes et variées autour d'un tronçon fabriqué.

1. Recherche par emprise (emprise du modèle ancré + 60 m) dans l'API publique, réponse en cache.
2. Filtres : distance à l'emprise du modèle ≤ 60 m, date ≥ `depuis`, soleil ≥ 3° au-dessus de l'horizon (nuit et
   crépuscule écartés), statut « ready », précision annoncée ≤ 15 m, champ connu pour les photos à plat, photo hors
   bâtiment OSM.
3. Vues candidates : 360° -> 8 directions (tous les 45° autour de l'axe du tronçon) + la direction du point d'intérêt
   (passage, milieu du tronçon) ; photo plane -> sa direction. Chaque vue est notée sur les arêtes du modèle qu'elle
   voit (3 à 40 m, dans le champ, hors porteur, sans bâtiment OSM entre la caméra et le point), pondérées par la
   distance (1 jusqu'à 12 m, 0 à 35 m) ; une photo hors de l'emprise du modèle est pénalisée (− 0,4 à 15 m) ; une
   vue où le modèle n'occupe qu'une bande mince (emprise verticale < 3,5 % de l'image : vu en rasant) est écartée.
4. Netteté et exposition sur l'image SD (2 048 px) des meilleures candidates : variance du laplacien rapportée au
   contraste, luminance moyenne ; les photos floues (< 45 % de la médiane) ou sombres sont écartées.
5. Choix glouton : utilité = couverture du modèle + récence + point d'intérêt, plus des primes de diversité
   (nouveau quadrant de visée, nouvelle position le long du tronçon, nouvelle position en travers : chaussée,
   trottoir, piste…) et des pénalités (même point de prise de vue, même séquence). Une vue par photo.
Tout est déterministe une fois la recherche en cache (aucun tirage aléatoire, tris stables).
"""
import math

import numpy as np
from PIL import Image

import api_panoramax as AP
import geo
import vues as V

DIST_MAX = 60.0
SOLEIL_MIN = 3.0
PRECISION_MAX = 15.0
TANGAGE_360 = -10.0
PROF_MIN, PROF_MAX = 3.0, 40.0
N_MIN, N_MAX = 6, 12
EMPRISE_MIN = 0.035          # emprise verticale minimale du modèle dans la vue (fraction de la hauteur de l'image)
QUADRANTS = ("+x", "gauche", "-x", "droite")
LIBELLE_Q = {"+x": "dans le sens du tronçon (+s)", "-x": "à contre-sens du tronçon (−s)",
             "gauche": "en travers vers la gauche (+t)", "droite": "en travers vers la droite (−t)"}
CLASSES_POSITION = {"voie_circulation": "chaussée", "zone_neutralisee": "chaussée", "terre_plein": "terre-plein",
                    "trottoir": "trottoir", "chemin_pieton": "trottoir", "piste_cyclable": "piste",
                    "bande_plantee": "accotement", "bande_enherbee": "accotement", "berme": "accotement",
                    "accotement": "accotement", "sous_bordure": "bordure", "hors_modele": "hors modèle"}


def quadrant(lacet):
    a = (lacet + 180.0) % 360.0 - 180.0
    if abs(a) <= 45.0:
        return "+x"
    if abs(a) >= 135.0:
        return "-x"
    return "gauche" if a > 0 else "droite"


def est_360(p):
    io = p["proprietes"].get("pers:interior_orientation") or {}
    if io.get("field_of_view") == 360:
        return True
    if (p["proprietes"].get("exif") or {}).get("Xmp.GPano.ProjectionType") == "equirectangular":
        return True
    dims = io.get("sensor_array_dimensions") or []
    return len(dims) == 2 and abs(dims[0] - 2 * dims[1]) <= 2


def largeur_source(p):
    io = p["proprietes"].get("pers:interior_orientation") or {}
    dims = io.get("sensor_array_dimensions") or []
    return int(dims[0]) if dims else 5760


def porteur(p, vitesses, table=None):
    """Type de porteur : table des séquences (sites_meylan.json `porteurs_sequences`, constaté sur les photos), sinon
    sémantique « transport » de la séquence, sinon vitesse médiane de la séquence (> 32 km/h voiture, < 20 km/h vélo
    ou piéton, entre les deux inconnu : une voiture au ralenti et un vélo rapide se recouvrent ; essais du 17/10/2026,
    médianes de 4 à 49 km/h selon les séquences)."""
    base, source = None, None
    for cle, val in (table or {}).items():
        if cle != "note" and str(p.get("collection") or "").startswith(cle):
            base, source = val, "table des séquences"
    sem = ((p["proprietes"].get("collection") or {}).get("semantics")) or []
    tr = next((s.get("value") for s in sem if s.get("key") == "transport"), None)
    if base is None and tr:
        t = str(tr).lower()
        base = "voiture" if t in ("car", "bus", "truck", "motorbike", "van") else             "velo" if t in ("bike", "bicycle", "cycle", "scooter") else "pieton" if t in ("foot", "walk", "pedestrian") else None
        source = "sémantique transport" if base else None
    v_seq = vitesses.get("sequence", {}).get(p["collection"])
    v = vitesses.get("photo", {}).get(p["id"])
    if base is None and v_seq is not None:
        base = "voiture" if v_seq > 32.0 else "velo" if v_seq >= 7.0 and v_seq < 20.0 else "pieton" if v_seq < 7.0 else None
        source = "vitesse médiane de la séquence" if base else "vitesse ambiguë"
    return (base or "inconnu") + ("_360" if est_360(p) else "_plan"), tr, v, v_seq, source


def vitesses_sequences(photos):
    """Vitesses (km/h) d'après les voisines de la même séquence dans la réponse (Δt ≤ 15 s) : par photo et médiane
    par séquence."""
    par = {}
    for p in photos:
        par.setdefault(p["collection"], []).append(p)
    out, seq = {}, {}
    for col, lst in par.items():
        lst = sorted(lst, key=lambda q: q["proprietes"].get("datetime") or "")
        tps = [geo.lire_date(q["proprietes"]["datetime"]).timestamp() for q in lst]
        xy = [geo.l93(q["lon"], q["lat"]) for q in lst]
        toutes = []
        for i, q in enumerate(lst):
            vs = []
            for j in (i - 1, i + 1):
                if 0 <= j < len(lst) and 0 < abs(tps[j] - tps[i]) <= 15.0:
                    vs.append(math.hypot(xy[j][0] - xy[i][0], xy[j][1] - xy[i][1]) / abs(tps[j] - tps[i]) * 3.6)
            if vs:
                out[q["id"]] = float(np.median(vs))
                toutes += vs
        if len(toutes) >= 3:
            seq[col] = float(np.median(toutes))
    return {"photo": out, "sequence": seq}


def emprise_l93(modele, ancrage, marge=0.0):
    s = [modele.s_min - marge, modele.s_max + marge]
    t = [modele.t_min - marge, modele.t_max + marge]
    return np.array([ancrage.vers_l93(a, b) for a in s for b in t])


def distance_emprise(modele, s, t):
    ds = max(modele.s_min - s, 0.0, s - modele.s_max)
    dt = max(modele.t_min - t, 0.0, t - modele.t_max)
    return math.hypot(ds, dt)


def camera_nominale(p, ancrage, modele, az_vrai_vue, tangage, W, H, fov, por):
    x, y = geo.l93(p["lon"], p["lat"])
    s, t = ancrage.vers_modele(x, y)
    s, t = float(s), float(t)
    z = modele.z_sol(s, t)
    az_g = geo.az_vrai_vers_grille(az_vrai_vue, p["lon"], p["lat"])
    h = V.PORTEURS[por]["h"]
    return V.Camera(W, H, fov, np.array([s, t, z + h]), ancrage.lacet(az_g), tangage, 0.0)


def noter_vue(cam, P, typ, visible_bat, por, poi):
    """Arêtes vues (3 à 40 m, dans l'image, hors porteur, sans bâtiment entre) ; point d'intérêt dans l'image."""
    uv, prof, devant = cam.projeter(P)
    ok = devant & (prof >= PROF_MIN) & (prof <= PROF_MAX) & visible_bat
    ok &= (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)
    if ok.any():
        r = cam.rayons(uv[ok])
        el = np.degrees(np.arcsin(np.clip(r[:, 2], -1, 1)))
        p = V.PORTEURS[por]
        bon = el > p["el_min"]
        if p["bas_masque"] > 0:
            bon &= uv[ok][:, 1] < cam.H * (1 - p["bas_masque"])
        idx = np.nonzero(ok)[0]
        ok[idx[~bon]] = False
    # poids de proximité : 1 jusqu'à 12 m, 0 à 35 m (une vue qui ne voit le modèle qu'en rasant, au loin, derrière
    # la végétation, n'apprend rien ; essais S_M20)
    w = np.clip((35.0 - prof) / 23.0, 0.0, 1.0)
    n = float((w * ok).sum())
    s_vus = P[ok & (w > 0.3), 0]
    etendue = float(np.ptp(s_vus)) if len(s_vus) else 0.0
    q, pr, dv = cam.projeter(np.atleast_2d(poi))
    voit_poi = bool(dv[0] and PROF_MIN <= pr[0] <= PROF_MAX and 0 <= q[0, 0] < cam.W and 0 <= q[0, 1] < cam.H)
    par_type = {k: int((ok & (typ == k)).sum()) for k in range(4)}
    # emprise verticale du modèle dans l'image (écart interquartile des lignes / hauteur) : une vue qui ne voit le
    # modèle qu'en bande mince, en rasant (rue voisine, giratoire), ne permet ni l'alignement ni la comparaison
    emprise = float(np.subtract(*np.percentile(uv[ok, 1], [75, 25]))) / cam.H if ok.sum() > 10 else 0.0
    return n, etendue, voit_poi, par_type, emprise


def nettete(img_sd, est360, lacet_image, tangage, fov, por):
    """Netteté (écart type du laplacien / écart type des niveaux) et luminance moyenne sur une vue de 512 px tirée
    de l'image SD, hors porteur."""
    import cv2
    a = np.asarray(img_sd.convert("RGB"))
    if est360:
        vue = np.asarray(V.decoupe.vue_equirect(a, lacet_image, tangage, fov, 512))
        cam = V.Camera(512, 512, fov, np.zeros(3), 0.0, tangage, 0.0)
        m = V.masque_porteur(cam, por)
    else:
        k = 512 / max(a.shape[:2])
        vue = cv2.resize(a, (int(a.shape[1] * k), int(a.shape[0] * k)), interpolation=cv2.INTER_AREA)
        m = np.ones(vue.shape[:2], bool)
        b = V.PORTEURS[por]["bas_masque"]
        if b > 0:
            m[int(vue.shape[0] * (1 - b)):, :] = False
    g = cv2.cvtColor(vue, cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
    m2 = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return float(lap[m2].std() / (g[m2].std() + 1.0)), float(g[m2].mean() / 255.0)


def choisir(site, conf, modele, ancrage, poi, dossiers, rafraichir=False, depuis="2019-01-01", journal=print):
    """Sélection complète ; renvoie le document selection.json (dict)."""
    marge = DIST_MAX
    coins = emprise_l93(modele, ancrage, marge)
    lons, lats = zip(*[geo.wgs(x, y) for x, y in coins])
    bbox = (min(lons), min(lats), max(lons), max(lats))
    photos, doc = AP.rechercher(bbox, dossiers["cache"] / "recherche.json", rafraichir=rafraichir)
    journal(f"  recherche Panoramax : {len(photos)} photos dans l'emprise + {marge:.0f} m (requête du {doc['date_requete']})")
    vit = vitesses_sequences(photos)
    P, _, typ = modele.aretes()
    pas = max(1, len(P) // 900)
    Ps, typs = P[::pas], typ[::pas]
    cx, cy = ancrage.vers_l93((modele.s_min + modele.s_max) / 2, 0.0)
    bat = geo.Batiments(float(cx), float(cy), modele.longueur / 2 + 2 * DIST_MAX)
    XY = np.c_[ancrage.vers_l93(Ps[:, 0], Ps[:, 1])]
    # date de référence de la récence : celle de la requête en cache (déterministe hors appel réseau)
    maintenant = geo.lire_date(conf.get("date_reference") or doc["date_requete"][:10] + "T12:00:00+00:00")
    ecartees, cands = {}, []
    for p in photos:
        pr = p["proprietes"]
        x, y = geo.l93(p["lon"], p["lat"])
        s, t = (float(v) for v in ancrage.vers_modele(x, y))
        d = distance_emprise(modele, s, t)
        raison = None
        dt = pr.get("datetime")
        if not dt:
            raison = "sans date"
        elif d > DIST_MAX:
            raison = f"trop loin ({d:.0f} m de l'emprise)"
        elif dt[:10] < depuis:
            raison = f"trop ancienne ({dt[:10]} < {depuis})"
        elif pr.get("geovisio:status", "ready") != "ready":
            raison = "statut " + str(pr.get("geovisio:status"))
        elif (pr.get("quality:horizontal_accuracy") or 0) > PRECISION_MAX:
            raison = f"position imprécise ({pr['quality:horizontal_accuracy']} m)"
        if raison is None:
            el, _ = geo.soleil(dt, p["lon"], p["lat"])
            if el < SOLEIL_MIN:
                raison = f"nuit ou crépuscule (soleil à {el:.1f}°)"
        e360 = est_360(p)
        io = pr.get("pers:interior_orientation") or {}
        fov_plan = io.get("field_of_view")
        if raison is None and not e360 and not (fov_plan and 20 <= fov_plan <= 150):
            raison = "photo à plat sans champ connu"
        if raison is None and bat.contient(x, y):
            raison = "position dans un bâtiment OSM"
        if raison is None and not p["assets"].get("sd"):
            raison = "pas d'image SD"
        if raison:
            ecartees[p["id"]] = raison
            continue
        por, transport, v, v_seq, src_por = porteur(p, vit, conf.get("porteurs_sequences"))
        vis_bat = bat.visibles(x, y, XY)
        az0 = float(pr.get("view:azimuth") or 0.0)
        g = geo.gamma(p["lon"], p["lat"])
        vues_c = []
        if e360:
            W = largeur_source(p)
            fov = V.fov_equirect(W)
            azs = [ancrage.az_grille(k * 45.0) for k in range(8)]       # 8 directions autour de l'axe du tronçon
            sp, tp = poi
            if math.hypot(sp - s, tp - t) > 3.0:                         # + la direction du point d'intérêt
                xp, yp = ancrage.vers_l93(sp, tp)
                azs.append(math.degrees(math.atan2(float(xp) - x, float(yp) - y)) % 360.0)
            for az_g in azs:
                az_v = (az_g - g) % 360.0
                lacet_img = round(geo.ecart_angle(az_v, az0), 2)
                cam = camera_nominale(p, ancrage, modele, az0 + lacet_img, TANGAGE_360, V.TAILLE, V.TAILLE, fov, por)
                vues_c.append((cam, lacet_img, TANGAGE_360, fov))
        else:
            cam = camera_nominale(p, ancrage, modele, az0, float(pr.get("pers:pitch") or 0.0), V.TAILLE,
                                  int(round(V.TAILLE * 0.75)), float(fov_plan), por)
            vues_c.append((cam, 0.0, float(pr.get("pers:pitch") or 0.0), float(fov_plan)))
        age = (maintenant - geo.lire_date(dt)).days / 365.25
        recence = float(np.clip(1.0 - age / 8.0, 0.0, 1.0))
        classe, bande = modele.bande_sous(s, t)
        for cam, li, tg, fov in vues_c:
            n, etendue, voit_poi, par_type, emprise = noter_vue(cam, Ps, typs, vis_bat, por,
                                                                np.array([poi[0], poi[1], modele.z_sol(*poi)]))
            if n < 20 or emprise < EMPRISE_MIN:
                continue
            couv = min(1.0, n / 150.0) * (0.6 + 0.4 * min(1.0, etendue / 25.0)) * min(1.0, emprise / 0.08)
            u = couv + 0.5 * recence + (0.3 if voit_poi else 0.0) + (0.15 if e360 else 0.0) - 0.4 * min(1.0, d / 15.0)
            cands.append({"photo": p, "cam": cam, "lacet_image": li, "tangage": tg, "fov": fov, "n": int(round(n * pas)),
                          "etendue": etendue, "voit_poi": voit_poi, "u": u, "recence": recence, "s": s, "t": t,
                          "d_emprise": d, "classe": classe, "bande": bande, "porteur": por, "transport": transport,
                          "vitesse": v, "vitesse_seq": v_seq, "source_porteur": src_por, "emprise": emprise, "e360": e360, "q": quadrant(cam.lacet), "par_type": par_type})
    journal(f"  filtres : {len(ecartees)} photos écartées, {len({c['photo']['id'] for c in cands})} retenues pour la suite, "
            f"{len(cands)} vues candidates")
    # ---- netteté sur l'image SD des meilleures candidates (meilleure vue de chaque photo, 30 photos)
    meilleure = {}
    for c in sorted(cands, key=lambda c: (-c["u"], c["photo"]["id"], c["lacet_image"])):
        meilleure.setdefault(c["photo"]["id"], c)
    top = sorted(meilleure.values(), key=lambda c: (-c["u"], c["photo"]["id"]))[:30]
    mesures = {}
    for c in top:
        p = c["photo"]
        f = AP.telecharger(p, "sd", dossiers["brut"])
        try:
            im = Image.open(f)
            im.load()
        except Exception as e:  # image illisible
            ecartees[p["id"]] = f"image SD illisible ({e})"
            continue
        fov = V.fov_equirect(largeur_source(p)) if c["e360"] else c["fov"]
        mesures[p["id"]] = nettete(im, c["e360"], c["lacet_image"], c["tangage"], fov, c["porteur"])
    if mesures:
        med = float(np.median([m[0] for m in mesures.values()]))
        for pid, (n_, lum) in mesures.items():
            if n_ < 0.45 * med:
                ecartees[pid] = f"floue (netteté {n_:.3f} < 45 % de la médiane {med:.3f})"
            elif lum < 0.18:
                ecartees[pid] = f"sombre (luminance moyenne {lum:.2f})"
    else:
        med = None
    pool = [c for c in cands if c["photo"]["id"] in mesures and c["photo"]["id"] not in ecartees]
    # ---- choix glouton
    choisies, quad, cellules, positions, sequences = [], set(), set(), set(), {}
    while len(choisies) < N_MAX and pool:
        best, best_v, best_det = None, -1e9, None
        for c in pool:
            cell = (int(np.clip((c["s"] - modele.s_min) // 20, -1, 6)), CLASSES_POSITION.get(c["classe"], c["classe"]))
            pos = CLASSES_POSITION.get(c["classe"], c["classe"])
            bonus = {"quadrant": 0.8 if c["q"] not in quad else 0.0, "cellule": 0.4 if cell not in cellules else 0.0,
                     "position": 0.4 if pos not in positions else 0.0,
                     "sequence": -0.15 * sequences.get(c["photo"]["collection"], 0)}
            dmin = min([math.hypot(c["s"] - o["s"], c["t"] - o["t"]) for o in choisies] or [99.0])
            bonus["proximite"] = -0.6 if dmin < 6.0 else -0.25 if dmin < 12.0 else 0.0
            if mesures.get(c["photo"]["id"]) and med:
                bonus["nettete"] = 0.1 * float(np.clip(mesures[c["photo"]["id"]][0] / med - 1.0, -1, 1))
            val = c["u"] + sum(bonus.values())
            cle = (val, c["photo"]["id"], -c["lacet_image"])
            if best is None or cle > (best_v, best["photo"]["id"], -best["lacet_image"]):
                best, best_v, best_det = c, val, (bonus, cell, pos)
        if len(choisies) >= N_MIN and best_v < 0.9:
            break
        bonus, cell, pos = best_det
        best["valeur"], best["bonus"] = best_v, bonus
        choisies.append(best)
        quad.add(best["q"])
        cellules.add(cell)
        positions.add(pos)
        sequences[best["photo"]["collection"]] = sequences.get(best["photo"]["collection"], 0) + 1
        pool = [c for c in pool if c["photo"]["id"] != best["photo"]["id"]]
    # ---- document
    sel = []
    for k, c in enumerate(choisies):
        p, pr = c["photo"], c["photo"]["proprietes"]
        x, y = geo.l93(p["lon"], p["lat"])
        raisons = [f"{'360°' if c['e360'] else 'photo à plat'} du {pr['datetime'][:10]}",
                   f"prise {('sur la ' if CLASSES_POSITION.get(c['classe']) in ('chaussée', 'piste') else 'sur le ' if CLASSES_POSITION.get(c['classe']) in ('trottoir', 'terre-plein') else 'en ')}{CLASSES_POSITION.get(c['classe'], c['classe'])} (s = {c['s']:.1f} m, t = {c['t']:.1f} m)",
                   f"vue {LIBELLE_Q[c['q']]}", f"{c['n']} points d'arêtes du modèle vus (pondérés par la distance) sur {c['etendue']:.0f} m"]
        if c["voit_poi"]:
            raisons.append("voit le point d'intérêt")
        if c["bonus"]["quadrant"] > 0:
            raisons.append("nouvelle direction de vue")
        if c["bonus"]["position"] > 0:
            raisons.append("nouvelle position en travers")
        if c["bonus"]["cellule"] > 0:
            raisons.append("nouvelle position le long du tronçon")
        nm = mesures.get(p["id"])
        sel.append({
            "rang": k + 1, "id": p["id"], "id8": p["id"][:8], "collection": p["collection"], "date": pr["datetime"],
            "date_locale": pr.get("datetimetz"), "lon": round(p["lon"], 7), "lat": round(p["lat"], 7),
            "l93": [round(x, 2), round(y, 2)], "cap_vrai_deg": pr.get("view:azimuth"),
            "type": "360" if c["e360"] else "plan", "largeur_source_px": largeur_source(p) if c["e360"] else None,
            "auteur": pr.get("geovisio:producer"), "licence": pr.get("license"), "instance": p.get("instance"),
            "precision_m": pr.get("quality:horizontal_accuracy"), "porteur": c["porteur"],
            "transport_declare": c["transport"], "vitesse_kmh": None if c["vitesse"] is None else round(c["vitesse"], 1),
            "vitesse_mediane_sequence_kmh": None if c["vitesse_seq"] is None else round(c["vitesse_seq"], 1),
            "source_porteur": c["source_porteur"],
            "position_modele": {"s": round(c["s"], 2), "t": round(c["t"], 2), "classe": c["classe"],
                                "bande": c["bande"], "distance_emprise_m": round(c["d_emprise"], 1)},
            "vue": {"lacet_image_deg": c["lacet_image"], "tangage_deg": c["tangage"], "champ_deg": round(c["fov"], 3),
                    "lacet_modele_deg": round(c["cam"].lacet, 2), "quadrant": c["q"],
                    "azimut_grille_deg": round(ancrage.az_grille(c["cam"].lacet), 2)},
            "notes": {"utilite": round(c["u"], 3), "valeur_gloutonne": round(c["valeur"], 3),
                      "primes": {k2: round(v2, 3) for k2, v2 in c["bonus"].items()},
                      "points_visibles": c["n"], "etendue_s_m": round(c["etendue"], 1), "recence": round(c["recence"], 3),
                      "emprise_verticale": round(c["emprise"], 3),
                      "nettete": None if not nm else round(nm[0], 4), "luminance": None if not nm else round(nm[1], 3)},
            "soleil": dict(zip(("hauteur_deg", "azimut_vrai_deg"), (round(v, 2) for v in geo.soleil(pr["datetime"], p["lon"], p["lat"])))),
            "raison": " ; ".join(raisons),
        })
    stats = {"photos_trouvees": len(photos), "ecartees": len(ecartees),
             "raisons_ecart": {}, "vues_candidates": len(cands), "nettete_mediane": med,
             "quadrants": sorted({s["vue"]["quadrant"] for s in sel}),
             "positions": sorted({CLASSES_POSITION.get(s["position_modele"]["classe"], "?") for s in sel}),
             "sequences": len({s["collection"] for s in sel})}
    for r in ecartees.values():
        k = r.split(" (")[0]
        stats["raisons_ecart"][k] = stats["raisons_ecart"].get(k, 0) + 1
    return {"schema": "comparaison_selection/0.1", "site": site, "recherche": {"bbox": list(bbox), "date": doc["date_requete"],
            "cle_cache": doc["cle"], "n": doc["n"]}, "criteres": {"distance_max_m": DIST_MAX, "depuis": depuis,
            "soleil_min_deg": SOLEIL_MIN, "precision_max_m": PRECISION_MAX, "n_min": N_MIN, "n_max": N_MAX,
            "profondeur_m": [PROF_MIN, PROF_MAX], "tangage_vues_360_deg": TANGAGE_360},
            "statistiques": stats, "photos": sel,
            "ecartees": [{"id": k, "raison": v} for k, v in sorted(ecartees.items())]}
