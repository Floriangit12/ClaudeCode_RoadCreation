"""Sélection v2 : photos Panoramax (d'abord) puis Mapillary (en complément) choisies pour MAXIMISER LA COUVERTURE des
zones d'intérêt du site (zones.py : zone centrale de conflit, anneau et îlot central d'un giratoire, îlots, passages,
approches ; cases de 20 m d'un tronçon courant) sous plusieurs directions, avec plusieurs vues par photo 360°.

1. Recherche par emprise (zones + 55 m) : Panoramax (api_panoramax, cache), Mapillary (api_mapillary, cache ; seulement
   si le jeton est présent).
2. Filtres de la v1 (date ≥ depuis et ≤ jusqu_au, soleil ≥ 3°, statut, précision ≤ 15 m, champ connu, hors bâtiment
   OSM) + distance ≤ 55 m d'une zone ; une photo Mapillary prise au même endroit (< 2,5 m) et au même instant (< 5 s)
   qu'une photo Panoramax est le doublon de celle-ci (même prise publiée deux fois) et n'est pas gardée.
3. Vues candidates : photo 360° -> une vue vers le centre de chaque zone à moins de 55 m (zones les plus lourdes
   d'abord) + les 8 directions à 45° des axes, fusionnées à moins de 25° ; photo à plat -> sa direction. Chaque vue est
   évaluée sur chaque zone (zones.Visibilite) : part pondérée des points vus, secteur d'observation (8 × 45°).
4. Netteté et luminance (image SD de 2 048 px) des 220 photos les plus utiles ; floues (< 45 % de la médiane) et
   sombres (< 0,18) écartées, comme en v1. Périodes exclues (`exclure` : travaux, état transitoire) écartées d'office.
5. Mouvements : pour un carrefour ou un giratoire, chaque passage d'une séquence dans le cœur (zone centrale, anneau,
   à 3 m près) est rattaché à sa branche d'entrée et à sa branche de sortie (approches parcourues dans les 60 s
   avant et après) : « B-entree -> B-sortie » (tout droit, tourne-à-gauche, tourne-à-droite, demi-tour).
6. Choix glouton en quatre phases (Panoramax seul, puis Panoramax + Mapillary, dans la fenêtre d'état [depuis,
   jusqu_au] ; puis, en COMPLÉMENT seulement, les mêmes avec les photos plus anciennes, depuis `complement_depuis`,
   malus 0,1, marquées « hors_fenetre_etat ») : gain d'une photo = Σ zones poids × [Σ cases (g(c + Δ) − g(c))
   + 2 (h(C + Δ) − h(C))], une case = secteur d'observation (8 × 45°) × distance (≤ 20 m / au-delà), g(c) =
   1 − exp(−c / 0,5) par case (deux bonnes vues suffisent), h(C) = 1 − exp(−C / 2) toutes cases confondues ; les vues
   d'une photo s'ajoutent tant que chacune apporte au moins 25 % du gain de la meilleure (4 au plus) ; toute photo
   360° garde en plus une vue vers le centre et vers chaque branche qu'elle voit (≥ 20 % de la zone, zone visée par
   la vue), 6 vues au plus si elle est prise dans le cœur ou à son bord, 4 ailleurs ; après le choix (sans influer
   sur lui), une photo 360° restée à une seule vue reçoit un contrechamp (vue à 90° ou plus de la première) qui
   montre le mieux le cœur ou une approche (sur une approche : la branche derrière la caméra) ; primes : photo dans le cœur ou à son bord (+ 0,4),
   nouveau mouvement (+ 0,6), récence (+ 0,15), netteté (± 0,1) ; pénalité de séquence (− 0,05 par photo déjà prise).
   Doublons quasi identiques écartés : même séquence à moins de 5 m, même jour à moins de 2,5 m. Objectif : 40 à 60
   photos pour un carrefour ou un giratoire (240 vues au plus), 12 à 20 pour une section courante (50 vues au plus) ;
   arrêt au maximum ; sous le minimum, toute photo non
   doublon qui apporte une vue nouvelle (gain > 0,001) est prise ; au-delà du minimum, arrêt quand le gain d'une photo
   tombe sous 0,05 (0,10 en phase 1).
Tout est déterministe une fois les recherches en cache.
"""
import math

import numpy as np
from PIL import Image

import api_mapillary as AM
import api_panoramax as AP
import geo
import selection as SE
import vues as V
import zones as Z

DIST_MAX = 55.0
FUSION_DEG = 25.0
MAX_VUES_PHOTO = 4
MAX_VUES_PHOTO_COEUR = 6     # photo 360° prise dans le cœur ou à son bord : vers le centre et vers chaque branche
PART_MIN_VUE = 0.25          # une vue supplémentaire d'une photo doit apporter au moins 25 % du gain de la meilleure
N_NETTETE = 220
OBJECTIFS = {"carrefour": (40, 60, 240), "giratoire": (40, 60, 240), "section": (12, 20, 50)}
SEUIL_GAIN = 0.05
SEUIL_PHASE1 = 0.10
SEUIL_SOUS_MIN = 0.001       # sous le minimum de l'objectif : toute photo non doublon qui apporte une vue nouvelle
TAU_SECTEUR, TAU_TOTAL = 0.5, 2.0
D_PROCHE = 20.0              # classes de distance de la couverture : vue proche (≤ 20 m) / lointaine
MALUS_HORS_FENETRE = 0.10
NOYAU = ("centre", "anneau")


def _g(c):
    return 1.0 - np.exp(-np.asarray(c) / TAU_SECTEUR)


def _h(c):
    return 1.0 - np.exp(-np.asarray(c) / TAU_TOTAL)


class Couverture:
    """État de la couverture : cumul par zone, secteur d'observation (8 × 45°) et classe de distance (proche ≤ 20 m,
    lointaine) des parts vues."""

    def __init__(self, zones):
        self.w = np.array([z.poids for z in zones])
        self.c = np.zeros((len(zones), 16))

    @staticmethod
    def delta(ev, n):
        d = np.zeros((n, 16))
        for k, e in ev.items():
            d[k, e["secteur"] + (8 if e["distance_m"] > D_PROCHE else 0)] += e["part"]
        return d

    def gain(self, d):
        c = self.c
        g = (_g(c + d) - _g(c)).sum(axis=1) + 2.0 * (_h((c + d).sum(axis=1)) - _h(c.sum(axis=1)))
        return float((self.w * g).sum())

    def ajouter(self, d):
        self.c = self.c + d


def _lacet_vers(cam_C, cible):
    return math.degrees(math.atan2(cible[1] - cam_C[1], cible[0] - cam_C[0]))


def _cle(id8, est360, lacet_image):
    return f"{id8}_{lacet_image:+04.0f}" if est360 else id8


def _id8(p):
    return AM.id8(p["id"]) if p.get("source") == "mapillary" else p["id"][:8]


def _mouvements(photos_ok, zones, ancrage):
    """Passages des séquences dans le cœur : {id photo: (mouvement, libellé)} et liste des mouvements disponibles."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    noyau = [z for z in zones if z.type in NOYAU]
    appr = [z for z in zones if z.type == "approche"]
    if not noyau or len(appr) < 2:
        return {}, {}
    coeur = unary_union([z.poly for z in noyau]).buffer(3.0)
    par = {}
    for p in photos_ok:
        par.setdefault(p["collection"], []).append(p)
    out, dispo = {}, {}
    for col, lst in par.items():
        lst = sorted(lst, key=lambda q: q["proprietes"]["datetime"])
        tps = [geo.lire_date(q["proprietes"]["datetime"]).timestamp() for q in lst]
        st = [tuple(float(v) for v in ancrage.vers_modele(*geo.l93(q["lon"], q["lat"]))) for q in lst]
        dedans = [coeur.contains(Point(*x)) for x in st]
        k = 0
        while k < len(lst):
            if not dedans[k]:
                k += 1
                continue
            j = k
            while j + 1 < len(lst) and dedans[j + 1] and tps[j + 1] - tps[j] <= 20.0:
                j += 1

            def branche(indices):
                for i in indices:
                    if not (0 <= i < len(lst)) or abs(tps[i] - tps[k if i < k else j]) > 60.0:
                        return None
                    if dedans[i]:
                        continue
                    P = Point(*st[i])
                    z = min(appr, key=lambda a: a.poly.distance(P))
                    if z.poly.distance(P) <= 8.0:
                        return z
                return None
            e = branche(range(k - 1, k - 8, -1))
            s = branche(range(j + 1, j + 8))
            if e is not None and s is not None:
                ae = (z_az(e) + 180.0) % 360.0
                virage = geo.ecart_angle(z_az(s), ae)
                lib = ("demi-tour" if abs(virage) > 150 else "tout droit" if abs(virage) <= 35
                       else "tourne-à-droite" if virage > 0 else "tourne-à-gauche")
                mv = f"{e.meta.get('branche', e.id)} -> {s.meta.get('branche', s.id)}"
                dispo.setdefault(mv, {"libelle": lib, "photos": []})
                for i in range(k, j + 1):
                    out[lst[i]["id"]] = (mv, lib)
                    dispo[mv]["photos"].append(lst[i]["id"])
            k = j + 1
    return out, dispo


def z_az(z):
    return float(z.meta.get("azimut_grille_deg") or 0.0)


def choisir(site, conf, modele, ancrage, zones, genre, dossiers, rafraichir=False, depuis="2019-01-01",
            jusqu_au=None, mapillary=True, journal=print, complement_depuis=None, exclure=None):
    """Sélection v2 complète ; renvoie le document selection.json (dict, schema comparaison_selection/0.2).
    Fenêtre d'état [depuis, jusqu_au] : photos de l'état décrit. complement_depuis (< depuis) : photos plus anciennes
    admises en COMPLÉMENT (phases 3 et 4, après toutes celles de la fenêtre, avec un malus), marquées
    « hors_fenetre_etat » : elles montrent un état antérieur, à lire avec leur date (le kit multi-orthos dit ce qui a
    changé entre les dates)."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    n_min, n_max, vues_max = OBJECTIFS[genre]
    union = unary_union([z.poly for z in zones])
    x0, y0, x1, y1 = union.bounds
    coins = [ancrage.vers_l93(a, b) for a in (x0 - DIST_MAX, x1 + DIST_MAX) for b in (y0 - DIST_MAX, y1 + DIST_MAX)]
    lons, lats = zip(*[geo.wgs(float(x), float(y)) for x, y in coins])
    bbox = (min(lons), min(lats), max(lons), max(lats))
    photos, doc = AP.rechercher(bbox, dossiers["cache"] / "recherche_v2.json", rafraichir=rafraichir)
    for p in photos:
        p.setdefault("source", "panoramax")
    journal(f"  recherche Panoramax : {len(photos)} photos dans l'emprise des zones + {DIST_MAX:.0f} m "
            f"(requête du {doc['date_requete']})")
    mly, doc_m = [], {"n": 0, "note": "désactivé"}
    if mapillary:
        try:
            mly, doc_m = AM.rechercher(bbox, dossiers["cache"] / "mapillary_recherche.json", rafraichir=rafraichir)
            journal(f"  recherche Mapillary : {len(mly)} images ({doc_m.get('note') or 'requête du ' + doc_m['date_requete']})")
        except RuntimeError as e:
            doc_m = {"n": 0, "note": f"échec : {e}"}
            journal(f"  recherche Mapillary : échec ({e}) ; sans Mapillary")
    tout = photos + mly
    vit = SE.vitesses_sequences(tout)
    cx, cy = ancrage.vers_l93(*union.centroid.coords[0])
    rayon = max(x1 - x0, y1 - y0) / 2 + 2 * DIST_MAX
    bat = geo.Batiments(float(cx), float(cy), rayon)
    vis = Z.Visibilite(zones, ancrage, bat)
    maintenant = geo.lire_date(conf.get("date_reference") or doc["date_requete"][:10] + "T12:00:00+00:00")
    noyau = [z for z in zones if z.type in NOYAU]
    coeur = unary_union([z.poly for z in noyau]) if noyau else None
    pnx_pos = [(geo.l93(p["lon"], p["lat"]), geo.lire_date(p["proprietes"]["datetime"]).timestamp())
               for p in photos if p["proprietes"].get("datetime")]
    ecartees, cands, ok_photos = {}, {}, []
    for p in tout:
        pr = p["proprietes"]
        x, y = geo.l93(p["lon"], p["lat"])
        s, t = (float(v) for v in ancrage.vers_modele(x, y))
        d = float(union.distance(Point(s, t)))
        dt = pr.get("datetime")
        raison = None
        hors_fenetre = False
        if not dt:
            raison = "sans date"
        elif d > DIST_MAX:
            raison = f"trop loin ({d:.0f} m des zones)"
        elif any(a <= dt[:10] <= b for a, b in (exclure or ())):
            raison = f"période exclue ({dt[:10]} : travaux ou état transitoire déclarés)"
        elif dt[:10] < depuis:
            if complement_depuis and complement_depuis < depuis and dt[:10] >= complement_depuis:
                hors_fenetre = True
            else:
                raison = f"trop ancienne ({dt[:10]} < {complement_depuis if complement_depuis and complement_depuis < depuis else depuis})"
        elif jusqu_au and dt[:10] > jusqu_au:
            raison = f"postérieure à l'état décrit ({dt[:10]} > {jusqu_au})"
        elif pr.get("geovisio:status", "ready") != "ready":
            raison = "statut " + str(pr.get("geovisio:status"))
        elif (pr.get("quality:horizontal_accuracy") or 0) > SE.PRECISION_MAX:
            raison = f"position imprécise ({pr['quality:horizontal_accuracy']} m)"
        if raison is None:
            el, _ = geo.soleil(dt, p["lon"], p["lat"])
            if el < SE.SOLEIL_MIN:
                raison = f"nuit ou crépuscule (soleil à {el:.1f}°)"
        e360 = SE.est_360(p)
        fov_plan = (pr.get("pers:interior_orientation") or {}).get("field_of_view")
        if raison is None and not e360 and not (fov_plan and 20 <= fov_plan <= 150):
            raison = "photo à plat sans champ connu"
        if raison is None and p.get("source") == "mapillary" and (p.get("mly") or {}).get("camera_type") not in (
                "spherical", "equirectangular", "perspective", "fisheye"):
            raison = "modèle de caméra Mapillary inconnu"
        if raison is None and bat.contient(x, y):
            raison = "position dans un bâtiment OSM"
        if raison is None and vis.dans_ilot_opaque(s, t):
            raison = "prise dans l'îlot central du giratoire (parc : la chaussée y est masquée)"
        if raison is None and p.get("source") != "mapillary" and not p["assets"].get("sd"):
            raison = "pas d'image SD"
        if raison is None and p.get("source") == "mapillary":
            tp = geo.lire_date(dt).timestamp()
            for (xx, yy), tt in pnx_pos:
                if abs(tt - tp) <= 5.0 and math.hypot(xx - x, yy - y) <= 2.5:
                    raison = "doublon d'une photo Panoramax (même prise)"
                    break
        if raison:
            ecartees[p["id"]] = raison
            continue
        ok_photos.append(p)
        por, transport, v, v_seq, src_por = SE.porteur(p, vit, conf.get("porteurs_sequences"))
        az0 = float(pr.get("view:azimuth") or 0.0)
        g = geo.gamma(p["lon"], p["lat"])
        z_sol = modele.z_sol(s, t)
        vues_c = []
        if e360:
            W = SE.largeur_source(p)
            fov = V.fov_equirect(W)
            lacets = []
            for z in sorted(zones, key=lambda z: (-z.poids, z.id)):
                c = z.centre
                if math.hypot(c[0] - s, c[1] - t) <= DIST_MAX and not z.poly.contains(Point(s, t)):
                    lacets.append((_lacet_vers((s, t), c), z.id))
                elif z.poly.contains(Point(s, t)) and z.type in NOYAU:   # dans le cœur : vers son centre de gravité
                    if math.hypot(c[0] - s, c[1] - t) > 3.0:
                        lacets.append((_lacet_vers((s, t), c), z.id))
            lacets += [(k * 45.0, f"azimut {ancrage.az_grille(k * 45.0):.0f}°") for k in range(8)]
            gardes = []
            for lac, cible in lacets:
                if all(abs(geo.ecart_angle(lac, l2)) >= FUSION_DEG for l2, _ in gardes):
                    gardes.append((lac, cible))
            for lac, cible in gardes:
                az_v = (ancrage.az_grille(lac) - g) % 360.0
                li = round(geo.ecart_angle(az_v, az0), 2)
                cam = SE.camera_nominale(p, ancrage, modele, az0 + li, SE.TANGAGE_360, V.TAILLE, V.TAILLE, fov, por)
                vues_c.append((cam, li, SE.TANGAGE_360, fov, cible))
        else:
            cam = SE.camera_nominale(p, ancrage, modele, az0, float(pr.get("pers:pitch") or 0.0), V.TAILLE,
                                     int(round(V.TAILLE * 0.75)), float(fov_plan), por)
            vues_c.append((cam, 0.0, float(pr.get("pers:pitch") or 0.0), float(fov_plan), "visée de la photo"))
        age = (maintenant - geo.lire_date(dt)).days / 365.25
        recence = float(np.clip(1.0 - age / 8.0, 0.0, 1.0))
        classe, bande = modele.bande_sous(s, t)
        au_coeur = bool(coeur is not None and coeur.distance(Point(s, t)) <= 3.0)
        vv = []
        for cam, li, tg, fov, cible in vues_c:
            ev = vis.evaluer(cam, por)
            if sum(zones[k].poids * e["part"] for k, e in ev.items()) < 0.05:
                continue
            vv.append({"cam": cam, "lacet_image": li, "tangage": tg, "fov": fov, "cible": cible, "eval": ev,
                       "delta": Couverture.delta(ev, len(zones))})
        if not vv:
            ecartees[p["id"]] = "ne voit aucune zone (bâtiments, distance, porteur)"
            continue
        cands[p["id"]] = {"photo": p, "vues": vv, "s": s, "t": t, "z": z_sol, "d_zones": d, "classe": classe,
                          "bande": bande, "porteur": por, "transport": transport, "vitesse": v, "vitesse_seq": v_seq,
                          "source_porteur": src_por, "e360": e360, "recence": recence, "au_coeur": au_coeur,
                          "source": p.get("source", "panoramax"), "date": dt, "hors_fenetre": hors_fenetre,
                          "t_s": geo.lire_date(dt).timestamp()}
    journal(f"  filtres : {len(ecartees)} photos écartées, {len(cands)} gardées "
            f"({sum(1 for c in cands.values() if c['source'] == 'mapillary')} Mapillary, "
            f"{sum(1 for c in cands.values() if c['hors_fenetre'])} hors fenêtre d'état), "
            f"{sum(len(c['vues']) for c in cands.values())} vues candidates")
    mouv, dispo = _mouvements([c["photo"] for c in cands.values()], zones, ancrage)
    # ---- netteté (image SD) des photos les plus utiles
    vide = Couverture(zones)
    for c in cands.values():
        c["gain0"] = max(vide.gain(v["delta"]) for v in c["vues"])
    top = sorted(cands.values(), key=lambda c: (-c["gain0"], c["photo"]["id"]))[:N_NETTETE]
    mesures = {}
    for c in top:
        p = c["photo"]
        try:
            f = (AM.telecharger(p, "sd", dossiers["brut"]) if c["source"] == "mapillary"
                 else AP.telecharger(p, "sd", dossiers["brut"]))
            im = Image.open(f)
            im.load()
        except Exception as e:  # image illisible ou réseau
            ecartees[p["id"]] = f"image SD indisponible ({str(e)[:80]})"
            continue
        best = max(c["vues"], key=lambda v: vide.gain(v["delta"]))
        fov = V.fov_equirect(SE.largeur_source(p)) if c["e360"] else best["fov"]
        if not c["e360"] and c["source"] == "mapillary":
            im, _ = V.redresser_mapillary(im.convert("RGB"), p.get("mly") or {})
        mesures[p["id"]] = SE.nettete(im, c["e360"], best["lacet_image"], best["tangage"], fov, c["porteur"])
    med = float(np.median([m[0] for m in mesures.values()])) if mesures else None
    for pid, (n_, lum) in mesures.items():
        if n_ < 0.45 * med:
            ecartees[pid] = f"floue (netteté {n_:.3f} < 45 % de la médiane {med:.3f})"
        elif lum < 0.18:
            ecartees[pid] = f"sombre (luminance moyenne {lum:.2f})"
    pool = {pid: c for pid, c in cands.items() if pid in mesures and pid not in ecartees}
    # ---- choix glouton en deux phases
    cov = Couverture(zones)
    choisies, seq_n, mv_vus, n_vues = [], {}, set(), 0
    doublons = {}

    def doublon(c):
        for o in choisies:
            dd = math.hypot(c["s"] - o["s"], c["t"] - o["t"])
            if c["photo"]["collection"] == o["photo"]["collection"] and dd < 5.0:
                return o
            if c["date"][:10] == o["date"][:10] and dd < 2.5:
                return o
        return None

    def evaluer(c):
        vv = sorted(c["vues"], key=lambda v: (-cov.gain(v["delta"]), v["lacet_image"]))
        prises, d_tot, gains = [], np.zeros_like(cov.c), []
        g_best = None
        n_max_v = MAX_VUES_PHOTO_COEUR if (c["au_coeur"] and c["e360"]) else MAX_VUES_PHOTO
        for v in vv:
            if len(prises) >= n_max_v:
                break
            g1 = cov.gain(d_tot + v["delta"]) - cov.gain(d_tot)
            if g_best is None:
                g_best = g1
            elif g1 < max(0.02, PART_MIN_VUE * g_best):
                continue
            prises.append(v)
            gains.append(g1)
            d_tot = d_tot + v["delta"]
        if c["e360"]:
            # photo 360° : PLUSIEURS vues, une vers le centre et vers CHAQUE branche qu'elle voit, même si la couverture
            # de cette direction est déjà acquise (dans le cœur : c'est la lecture du carrefour depuis son centre ; sur
            # une approche : le centre devant, la branche derrière) ; 6 vues au plus dans le cœur, 4 ailleurs
            for v in sorted(c["vues"], key=lambda v: (-sum(e["part"] for e in v["eval"].values()), v["lacet_image"])):
                if len(prises) >= n_max_v or any(v is q for q in prises):
                    continue
                cz = next((k for k, z in enumerate(zones) if z.id == v["cible"]), None)
                if cz is not None and zones[cz].type in ("approche",) + NOYAU and \
                        v["eval"].get(cz, {}).get("part", 0.0) >= Z.SEUIL_VOIT:
                    g1 = cov.gain(d_tot + v["delta"]) - cov.gain(d_tot)
                    prises.append(v)
                    gains.append(g1)
                    d_tot = d_tot + v["delta"]
        gain_vues = cov.gain(d_tot)
        bonus = {"coeur": 0.4 if c["au_coeur"] else 0.0,
                 "mouvement": 0.6 if (c["photo"]["id"] in mouv and mouv[c["photo"]["id"]][0] not in mv_vus) else 0.0,
                 "recence": 0.15 * c["recence"],
                 "sequence": -0.05 * seq_n.get(c["photo"]["collection"], 0)}
        if c["hors_fenetre"]:
            bonus["hors_fenetre"] = -MALUS_HORS_FENETRE
        m = mesures.get(c["photo"]["id"])
        if m and med:
            bonus["nettete"] = 0.1 * float(np.clip(m[0] / med - 1.0, -1, 1))
        return gain_vues + sum(bonus.values()), gain_vues, prises, gains, d_tot, bonus

    phases = ((1, ("panoramax",), False), (2, ("panoramax", "mapillary"), False),
              (3, ("panoramax",), True), (4, ("panoramax", "mapillary"), True))
    for phase, sources, complement in phases:
        if complement and not any(c["hors_fenetre"] for c in pool.values()):
            break
        while len(choisies) < n_max and n_vues < vues_max:
            best = None
            for pid in sorted(pool):
                c = pool[pid]
                if c["source"] not in sources or (c["hors_fenetre"] and not complement):
                    continue
                o = doublon(c)
                if o is not None:
                    doublons[pid] = o["photo"]["id"]
                    continue
                val, gv, prises, gains, d_tot, bonus = evaluer(c)
                if best is None or (val, pid) > (best[0], best[1]):
                    best = (val, pid, gv, prises, gains, d_tot, bonus)
            for pid in doublons:
                pool.pop(pid, None)
            if best is None:
                break
            val, pid, gv, prises, gains, d_tot, bonus = best
            seuil = SEUIL_PHASE1 if phase == 1 else (SEUIL_SOUS_MIN if len(choisies) < n_min else SEUIL_GAIN)
            if gv + bonus["coeur"] + bonus["mouvement"] < seuil:
                break
            c = pool.pop(pid)
            c.update({"valeur": val, "gain_vues": gv, "prises": prises, "gains": gains, "bonus": bonus,
                      "phase": phase, "rang": len(choisies) + 1})
            choisies.append(c)
            cov.ajouter(d_tot)
            n_vues += len(prises)
            seq_n[c["photo"]["collection"]] = seq_n.get(c["photo"]["collection"], 0) + 1
            if pid in mouv:
                mv_vus.add(mouv[pid][0])
    for pid, oid in doublons.items():
        ecartees.setdefault(pid, f"doublon quasi identique de {oid[:8]} (même séquence < 5 m ou même jour < 2,5 m)")
    # complément après le choix (n'influe pas sur le choix) : une photo 360° retenue avec UNE seule vue reçoit un
    # CONTRECHAMP (vue à 90° ou plus de la première) qui montre le mieux le cœur ou une approche (≥ 20 % de la zone) :
    # sur une approche, c'est la branche derrière la caméra ; jamais une seule vue par photo 360° quand une autre
    # direction montre le carrefour
    n_compl = 0
    for c in choisies:
        if not c["e360"] or len(c["prises"]) != 1:
            continue
        best_v, best_s = None, 0.0
        for v in sorted(c["vues"], key=lambda v: v["lacet_image"]):
            if v is c["prises"][0] or abs(geo.ecart_angle(v["lacet_image"], c["prises"][0]["lacet_image"])) < 90.0:
                continue
            nouv = sum(e["part"] * zones[k].poids for k, e in v["eval"].items()
                       if e["part"] >= Z.SEUIL_VOIT and zones[k].type in ("approche",) + NOYAU)
            if nouv > best_s:
                best_v, best_s = v, nouv
        if best_v is not None:
            c["prises"].append(best_v)
            c["gains"].append(cov.gain(best_v["delta"]))
            cov.ajouter(best_v["delta"])
            n_vues += 1
            n_compl += 1
    if n_compl:
        journal(f"  complément : {n_compl} photos 360° à une seule vue reçoivent un contrechamp (cœur ou branche)")
    journal(f"  choix : {len(choisies)} photos ({sum(1 for c in choisies if c['source'] == 'mapillary')} Mapillary, "
            f"{sum(1 for c in choisies if c['hors_fenetre'])} hors fenêtre d'état), "
            f"{n_vues} vues ; objectif {n_min}-{n_max} photos")
    # ---- document
    sel, vues_eval = [], []
    for c in choisies:
        p, pr = c["photo"], c["photo"]["proprietes"]
        x, y = geo.l93(p["lon"], p["lat"])
        i8 = _id8(p)
        nm = mesures.get(p["id"])
        for j, (v, gj) in enumerate(zip(c["prises"], c["gains"])):
            cle = _cle(i8, c["e360"], v["lacet_image"])
            zv = {zones[k].id: {"part": e["part"], "secteur": Z.SECTEURS[e["secteur"]], "distance_m": e["distance_m"]}
                  for k, e in sorted(v["eval"].items()) if e["part"] >= 0.05}
            vues_eval.append((cle, p["id"], v["eval"]))
            raisons = [f"{'360°' if c['e360'] else 'photo à plat'} {c['source'].capitalize()} du {pr['datetime'][:10]}"
                       + (f" (HORS FENÊTRE D'ÉTAT : antérieure au {depuis}, complément)" if c["hors_fenetre"] else ""),
                       f"prise {'dans le cœur ou à son bord' if c['au_coeur'] else 'en ' + SE.CLASSES_POSITION.get(c['classe'], c['classe'])} "
                       f"(s = {c['s']:.1f} m, t = {c['t']:.1f} m)",
                       f"vue {j + 1}/{len(c['prises'])} vers {v['cible']} (gain {gj:.2f})",
                       "zones vues : " + ", ".join(f"{k} {e['part']:.2f} {e['secteur']}" for k, e in
                                                   sorted(zv.items(), key=lambda x: -x[1]["part"])[:4])]
            if p["id"] in mouv:
                raisons.append(f"mouvement {mouv[p['id']][0]} ({mouv[p['id']][1]})")
            sel.append({
                "rang": c["rang"], "cle": cle, "id": p["id"], "id8": i8, "source": c["source"],
                "hors_fenetre_etat": c["hors_fenetre"],
                "collection": p["collection"], "date": pr["datetime"], "date_locale": pr.get("datetimetz"),
                "lon": round(p["lon"], 7), "lat": round(p["lat"], 7), "l93": [round(x, 2), round(y, 2)],
                "cap_vrai_deg": pr.get("view:azimuth"), "type": "360" if c["e360"] else "plan",
                "largeur_source_px": SE.largeur_source(p) if c["e360"] else None,
                "auteur": pr.get("geovisio:producer"), "licence": pr.get("license"), "instance": p.get("instance"),
                "lien": (p.get("mly") or {}).get("lien"), "mly": p.get("mly"),
                "precision_m": pr.get("quality:horizontal_accuracy"), "porteur": c["porteur"],
                "transport_declare": c["transport"], "vitesse_kmh": None if c["vitesse"] is None else round(c["vitesse"], 1),
                "vitesse_mediane_sequence_kmh": None if c["vitesse_seq"] is None else round(c["vitesse_seq"], 1),
                "source_porteur": c["source_porteur"],
                "position_modele": {"s": round(c["s"], 2), "t": round(c["t"], 2), "classe": c["classe"],
                                    "bande": c["bande"], "distance_zones_m": round(c["d_zones"], 1),
                                    "dans_le_coeur": c["au_coeur"]},
                "vue": {"lacet_image_deg": v["lacet_image"], "tangage_deg": v["tangage"], "champ_deg": round(v["fov"], 3),
                        "lacet_modele_deg": round(v["cam"].lacet, 2), "quadrant": SE.quadrant(v["cam"].lacet),
                        "azimut_grille_deg": round(ancrage.az_grille(v["cam"].lacet), 2), "cible": v["cible"],
                        "rang_dans_la_photo": j + 1, "vues_de_la_photo": len(c["prises"])},
                "zones_vues": zv,
                "mouvement": None if p["id"] not in mouv else {"mouvement": mouv[p["id"]][0], "type": mouv[p["id"]][1]},
                "notes": {"phase": c["phase"], "valeur_gloutonne": round(c["valeur"], 3),
                          "gain_couverture_photo": round(c["gain_vues"], 3), "gain_vue": round(gj, 3),
                          "primes": {k2: round(v2, 3) for k2, v2 in c["bonus"].items()},
                          "recence": round(c["recence"], 3), "nettete": None if not nm else round(nm[0], 4),
                          "luminance": None if not nm else round(nm[1], 3)},
                "soleil": dict(zip(("hauteur_deg", "azimut_vrai_deg"),
                                   (round(vv_, 2) for vv_ in geo.soleil(pr["datetime"], p["lon"], p["lat"])))),
                "raison": " ; ".join(raisons),
            })
    bilan_z = Z.couverture(zones, vues_eval)
    stats = {"photos_trouvees": len(photos), "images_mapillary_trouvees": len(mly), "ecartees": len(ecartees),
             "raisons_ecart": {}, "photos_candidates": len(cands),
             "vues_candidates": sum(len(c["vues"]) for c in cands.values()), "nettete_mediane": med,
             "photos": len(choisies), "photos_panoramax": sum(1 for c in choisies if c["source"] == "panoramax"),
             "photos_mapillary": sum(1 for c in choisies if c["source"] == "mapillary"), "vues": len(sel),
             "photos_hors_fenetre_etat": sum(1 for c in choisies if c["hors_fenetre"]),
             "vues_hors_fenetre_etat": sum(1 for s_ in sel if s_["hors_fenetre_etat"]),
             "candidates_dans_la_fenetre": sum(1 for c in cands.values() if not c["hors_fenetre"]),
             "photos_360": sum(1 for c in choisies if c["e360"]),
             "photos_dans_le_coeur": sum(1 for c in choisies if c["au_coeur"]),
             "quadrants": sorted({s_["vue"]["quadrant"] for s_ in sel}),
             "positions": sorted({SE.CLASSES_POSITION.get(s_["position_modele"]["classe"], "?") for s_ in sel}),
             "sequences": len({s_["collection"] for s_ in sel}), "dates": sorted({s_["date"][:10] for s_ in sel}),
             "objectif_photos": [n_min, n_max], "vues_max": vues_max,
             "zones_aveugles": [b["zone"] for b in bilan_z if b["aveugle"]],
             "mouvements_disponibles": {k: {"type": v["libelle"], "photos": len(v["photos"])} for k, v in sorted(dispo.items())},
             "mouvements_couverts": sorted(mv_vus)}
    for r in ecartees.values():
        k = r.split(" (")[0]
        stats["raisons_ecart"][k] = stats["raisons_ecart"].get(k, 0) + 1
    return {"schema": "comparaison_selection/0.2", "version": 2, "site": site, "genre": genre,
            "recherche": {"bbox": list(bbox), "date": doc["date_requete"], "cle_cache": doc["cle"], "n": doc["n"],
                          "mapillary": {k: doc_m.get(k) for k in ("date_requete", "cle", "n", "note") if k in doc_m}},
            "criteres": {"distance_max_zones_m": DIST_MAX, "depuis": depuis, "jusqu_au": jusqu_au,
                         "complement_depuis": complement_depuis if complement_depuis and complement_depuis < depuis else None,
                         "periodes_exclues": [list(p) for p in (exclure or ())],
                         "malus_hors_fenetre": MALUS_HORS_FENETRE, "vues_par_photo_coeur_max": MAX_VUES_PHOTO_COEUR,
                         "classes_distance_m": [D_PROCHE], "seuil_sous_minimum": SEUIL_SOUS_MIN,
                         "soleil_min_deg": SE.SOLEIL_MIN, "precision_max_m": SE.PRECISION_MAX,
                         "objectif_photos": [n_min, n_max], "vues_max": vues_max, "vues_par_photo_max": MAX_VUES_PHOTO,
                         "fusion_directions_deg": FUSION_DEG, "tangage_vues_360_deg": SE.TANGAGE_360,
                         "seuil_voit_zone": Z.SEUIL_VOIT, "seuil_gain": SEUIL_GAIN, "seuil_phase_panoramax": SEUIL_PHASE1},
            "statistiques": stats, "couverture": bilan_z, "photos": sel,
            "ecartees": [{"id": k, "raison": v} for k, v in sorted(ecartees.items())]}


def evaluer_selection_v1(sel_v1, zones, modele, ancrage, porteurs=None):
    """Évaluation, avec la même visibilité, des vues d'une sélection v1 (une vue par photo, caméra nominale) :
    [(cle, id, éval)] pour zones.couverture."""
    cx, cy = ancrage.vers_l93(*zones[0].centre) if zones else (0.0, 0.0)
    bat = geo.Batiments(float(cx), float(cy), 250.0)
    vis = Z.Visibilite(zones, ancrage, bat)
    out = []
    for ph in sel_v1.get("photos", []):
        p = {"lon": ph["lon"], "lat": ph["lat"]}
        v = ph["vue"]
        if ph["type"] == "360":
            W = H = V.TAILLE
        else:
            W, H = V.TAILLE, int(round(V.TAILLE * 0.75))
        cam = SE.camera_nominale(p, ancrage, modele, float(ph["cap_vrai_deg"] or 0.0) + v["lacet_image_deg"],
                                 v["tangage_deg"], W, H, v["champ_deg"], ph["porteur"])
        out.append((ph.get("cle") or ph["id8"], ph["id"], vis.evaluer(cam, ph["porteur"])))
    return out
