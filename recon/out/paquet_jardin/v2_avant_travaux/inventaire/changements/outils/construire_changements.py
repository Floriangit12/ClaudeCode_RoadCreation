"""Inventaire des changements du site Paquet Jardin entre le PCRS 5 cm (10/05/2022) et la veille des travaux
(22/06/2025) -> changements_2022_2025.geojson (L93), planches/zones/<id>.png (ortho 2022 | 2024 | 2025),
donnees/changements_resume.json.

Chaque entité a été revue à l'œil sur les planches ortho et, quand des photos existent, sur les vues
perspectives tirées des photos Panoramax / Mapillary (outils chrono.py, paires.py, sequences.py,
photo_ortho.py, planche_360.py ; images dans photos_non_versionnees/, non versionnées).
Géométries saisies en coordonnées locales (grille des planches) puis converties : L93 = local + O.

python construire_changements.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import (DONNEES, ICI, LIB, O, PLANCHES, RACINE, Vue, assembler, boite_locale,  # noqa: E402
                        ecrire_json, lire_json, police, rel)
from pyproj import Transformer  # noqa: E402

TR = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
PNX = "https://panoramax.openstreetmap.fr/#focus=pic&pic="
MLY = "https://www.mapillary.com/app/?pKey="
WMS_P25 = "https://data.geopf.fr/wms-r (ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025)"
P = {  # preuves récurrentes
    "pcrs": {"source": "ortho PCRS 5 cm Grenoble-Alpes Métropole / CRAIG", "ref": "data/sites/paquet_jardin/ortho5cm_2022", "date": "2022-05-10"},
    "ign24": {"source": "IGN BD ORTHO 20 cm (ORTHOIMAGERY.ORTHOPHOTOS2024), recalée (+0,035 ; +0,029) m sur le PCRS",
              "ref": "data/raw/ortho_recentes/ign_bdortho_2024_rvb_20cm", "date": "2024-08-09"},
    "irc24": {"source": "IGN BD ORTHO IRC 20 cm 2024", "ref": "data/raw/ortho_recentes/ign_bdortho_2024_irc_20cm", "date": "2024-08-09"},
    "p25": {"source": "Pléiades 50 cm 2025 (CNES / IGN), recalée (+0,47 ; +1,17) m", "ref": "data/raw/ortho_recentes/ign_pleiades_2025_50cm",
            "date": "2025 (printemps-été, avant le 23/06 : estimation)", "url": WMS_P25},
    "spot23": {"source": "SPOT 1,5 m 2023 (ORTHOIMAGERY.ORTHO-SAT.SPOT.2023)", "ref": "data/raw/ortho_recentes/ign_spot_2023_150cm", "date": "2023"},
    "bdtopo": {"source": "BD TOPO bâtiment (date_creation 2025-07-04)", "ref": "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson"},
}


_PNX_IDS = {}


def _ids_panoramax():
    if not _PNX_IDS:
        for js in (RACINE / "data/raw/panoramax/paquet_jardin").glob("*_hd.json"):
            m = json.loads(js.read_text(encoding="utf-8"))
            _PNX_IDS[m["id"][:8]] = (m["id"], m["datetime"][:10], m.get("producer"))
    return _PNX_IDS


def pnx(court, note=""):
    """Photo Panoramax par ses 8 premiers caractères -> preuve avec id complet, date, auteur, lien."""
    id_, date, auteur = _ids_panoramax()[court]
    return {"source": "panoramax", "id": id_, "date": date, "auteur": auteur, "licence": "CC-BY-SA 4.0", "url": PNX + id_, "note": note}


def mly(id_, date, note=""):
    return {"source": "mapillary", "id": str(id_), "date": date, "licence": "CC-BY-SA 4.0", "url": MLY + str(id_), "note": note}


def osm(ref, date, note=""):
    return {"source": "openstreetmap (Overpass [date:] 2022-05-10 vs 2025-06-20)", "id": ref, "date": date, "note": note,
            "ref": "donnees/osm_diff_2022-05-10_2025-06-20.json"}


def planche_ref(nom):
    return {"source": "planche", "ref": rel(PLANCHES / nom)}


def bande(p0, p1, largeur):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / L * largeur / 2, (x1 - x0) / L * largeur / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def l93(pts):
    return [[round(x + O[0], 2), round(y + O[1], 2)] for x, y in pts]


def anneau(pts):
    a = l93(pts)
    return a + [a[0]] if a[0] != a[-1] else a


def poly(pts):
    return {"type": "Polygon", "coordinates": [anneau(pts)]}


def multipoly(liste):
    return {"type": "MultiPolygon", "coordinates": [[anneau(p)] for p in liste]}


def point(x, y):
    return {"type": "Point", "coordinates": [round(x + O[0], 2), round(y + O[1], 2)]}


def multipoint(pts):
    return {"type": "MultiPoint", "coordinates": [[round(x + O[0], 2), round(y + O[1], 2)] for x, y in pts]}


# --------------------------------------------------------------------------- géométries lues dans le dépôt
def batiments_bdtopo(depuis="2025"):
    out = {}
    for f in lire_json(RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson")["features"]:
        p = f["properties"]
        if str(p.get("date_creation") or "") < depuis:
            continue
        g = f["geometry"]
        for k, pp in enumerate([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            pts = [TR.transform(c[0], c[1]) for c in pp[0]]
            out[p["cleabs"] + (f"_{k}" if k else "")] = [(x - O[0], y - O[1]) for x, y in pts]
    return out


def batiment(cleabs):
    for f in lire_json(RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson")["features"]:
        if f["properties"]["cleabs"] == cleabs:
            g = f["geometry"]
            pp = g["coordinates"] if g["type"] == "Polygon" else g["coordinates"][0]
            return [(TR.transform(c[0], c[1])[0] - O[0], TR.transform(c[0], c[1])[1] - O[1]) for c in pp[0]]
    raise KeyError(cleabs)


def _dans(x, y, pts):
    a = np.asarray(pts)
    xi, yi = a[:, 0], a[:, 1]
    xj, yj = np.roll(xi, 1), np.roll(yi, 1)
    c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / np.where(yj - yi == 0, 1e-12, yj - yi) + xi)
    return bool(c.sum() % 2)


def surfaces_construites():
    """Polygones « construit_2023_2024 » de surfaces_2026 (paquet v1, L93) : emprise du quartier neuf.
    Sont écartés ceux dont le centre tombe dans un bâtiment BD TOPO antérieur à 2025 (le v1 range à tort le
    bâtiment commercial SE de 2012 et son abord, surf_0421 et surf_0447, dans « construit_2023_2024 »)."""
    anciens = []
    for f in lire_json(RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson")["features"]:
        if str(f["properties"].get("date_creation") or "") >= "2025":
            continue
        g = f["geometry"]
        for pp in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            anciens.append([(TR.transform(c[0], c[1])[0] - O[0], TR.transform(c[0], c[1])[1] - O[1]) for c in pp[0]])
    out = []
    d = lire_json(RACINE / "recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson")
    for f in d["features"]:
        if f["properties"].get("etat") != "construit_2023_2024":
            continue
        g = f["geometry"]
        for pp in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
            pts = [(c[0] - O[0], c[1] - O[1]) for c in pp[0]]
            xm, ym = float(np.mean([q[0] for q in pts])), float(np.mean([q[1] for q in pts]))
            if any(_dans(xm, ym, an) for an in anciens):
                continue
            out.append(pts)
    return out


# --------------------------------------------------------------------------- inventaire
def inventaire():
    neufs = batiments_bdtopo()
    neufs = {k: v for k, v in neufs.items() if not k.startswith("BATIMENT0000002490985537")}   # 537 : aucun changement visible
    F = []

    F.append(dict(
        id="CHG-001", nature="batiment_construit", secteur="est",
        description=("Quartier neuf à l'est du Vercors et au sud-est de Verdun : 11 emprises BD TOPO créées le 04/07/2025 "
                     "(immeubles R+5 à R+9 et un bâtiment bas). PCRS 2022 : chantier (grue, voiles en élévation pour 925 et "
                     "929-931, terrain nu ailleurs) ; SPOT 2023 : immeubles déjà élevés ; IGN 09/08/2024 : construits, toits "
                     "terrasses et panneaux PV ; Panoramax 24/08/2024 : façades finies. Hauteurs absentes de la BD TOPO "
                     "(hauteur = null) et du LiDAR HD 2021 (antérieur)."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="invalide (chantier en 2022)", interet_adas="masques de visibilité, ombres, façades et entrées de parking du quartier",
        source_recommandee="emprises BD TOPO + IGN 2024 ; hauteurs à estimer par les ombres IGN 2024 (soleil connu) et les photos 2024-08",
        geometry=multipoly(list(neufs.values())),
        preuve=[P["pcrs"], P["spot23"], P["ign24"], P["p25"], dict(P["bdtopo"], id=", ".join(sorted(k[-3:] for k in neufs))),
                osm("way/1305757335, way/1305757336, way/1305757337, way/1305757338, way/1310886479, way/1310886480, way/1150232943 (building=apartments)", "2025-02-25 .. 2025-04-08"),
                osm("way/1150232941 (building=yes, bâtiment bas 928)", "2025-04-07"),
                pnx("f4066194", "façade de l'immeuble 923 finie (vue 344°)"),
                mly("349342869428", "2024-08-24", "même vue, pose calée sur bordures"),
                planche_ref("batiments_bdtopo_2025.jpg"), planche_ref("spot_secteur_est.jpg")],
        planche_boite=(20, -150, 160, 110)))

    F.append(dict(
        id="CHG-002", nature="amenagement_quartier_neuf", secteur="est",
        description=("Espaces extérieurs du quartier neuf : voies de desserte et parkings (rangées de places, x 55..75, y -110..-80), "
                     "cheminements béton et stabilisé, parc et noue enherbée avec lits minéraux, jeunes plantations. 2022 : terrain "
                     "de chantier ; août 2024 : achevés pour l'essentiel (finitions jusqu'au printemps 2025). Emprise = surfaces "
                     "« construit_2023_2024 » du paquet v1."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="invalide", interet_adas="voies et parkings riverains, entrées / sorties de véhicules, piétons",
        source_recommandee="levé topo GAM (hors emprise des travaux 2025) + IGN 2024 + photos calées 2024-08-24 (31 Mapillary calées sur bordures)",
        geometry=multipoly(surfaces_construites()),
        preuve=[P["pcrs"], P["ign24"], P["p25"],
                osm("way/1305757332, way/1362808248 (highway=service)", "2025-02-25 / 2025-04-03"),
                osm("way/1305757333 (amenity=parking)", "2025-02-12"), osm("way/1306122973, way/1311446075, way/1362808249 (footway)", "2024-08-27 .. 2025-02-25"),
                mly("1057665449081914", "2024-08-24", "rue nouvelle, pose calée sur bordures"),
                mly("807740837881423", "2024-08-24", "parkings, pose calée sur bordures"),
                planche_ref("revue_75m/zone_C3.jpg"), planche_ref("revue_75m/zone_D3.jpg")],
        planche_boite=(30, -150, 155, 120)))

    F.append(dict(
        id="CHG-003", nature="carrefour_modifie", secteur="vercors_sud",
        description=("Carrefour avenue du Vercors / allée des Mitaillères : la branche est (accès de chantier en 2022) devient une rue "
                     "définitive avec îlot central planté et paillé, bordures neuves, jeunes arbres, traversée ; STOP en janvier 2025."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="invalide (branche est)", interet_adas="nouvelle branche de carrefour, îlot, STOP, traversée cyclable",
        source_recommandee="IGN 2024 + 22 photos Mapillary 2024-08-24 calées sur bordures autour du carrefour + levé GAM",
        geometry=poly([(18, -143), (78, -143), (78, -112), (45, -117), (30, -121), (18, -125)]),
        preuve=[P["pcrs"], P["ign24"], mly("380284891996", "2024-08-24", "îlot planté, bordures neuves"),
                mly("3802848919960200", "2024-08-24", "pose calée sur bordures"),
                pnx("bce7b48a", "îlot paillé, jeunes arbres, bordures neuves"), pnx("b482b367", "STOP, traversée"),
                osm("way/1305902498, way/1305757331 (highway=service, branche est)", "2024-08-07"),
                planche_ref("revue_zoom/jonction_mitailleres.jpg")],
        planche_boite=(5, -150, 85, -100)))

    F.append(dict(
        id="CHG-004", nature="trottoir_bordure_neufs", secteur="vercors_est",
        description=("Rive est de l'avenue du Vercors au droit du quartier neuf (y -62..-33) : en 2022 bord de chantier en terre avec "
                     "clôture ; en août 2024 bordure neuve, trottoir / parvis clair et allée vers les immeubles (OSM footway 2025-02-25)."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="invalide (rive est)", interet_adas="bordure et trottoir le long de la chaussée, piétons",
        source_recommandee="IGN 2024 + photos Panoramax 2025-01-12 (vélo, rive ouest) + levé GAM si hors emprise des travaux",
        geometry=poly([(22.3, -33), (31.8, -33), (40.0, -40), (38.8, -62), (29.3, -62)]),
        preuve=[P["pcrs"], P["ign24"], osm("way/1311524320, way/1311524321 (footway)", "2025-02-25"),
                pnx("a1ffea74", "rive est vue depuis la piste ouest (az 90)"), pnx("29fb102d"),
                planche_ref("revue_zoom/vercors_bande_ouest.jpg")],
        planche_boite=(5, -75, 50, -15)))

    F.append(dict(
        id="CHG-005", nature="installation_chantier_temporaire", secteur="vercors_est",
        description=("Base vie de chantier (bungalows bleus empilés, clôtures) à l'angle SE du carrefour, sur un terrain nu en 2022 ; "
                     "présente en août 2024, en janvier 2025 et sur Pléiades 2025."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="objet absent en 2022 (à ajouter pour un état 2025)", interet_adas="objet en bord de chaussée (masque de visibilité au carrefour)",
        source_recommandee="IGN 2024 (emprise) + photos 2025-01-12 (aspect)",
        geometry=poly([(16.5, -32.5), (30.5, -32.5), (30.5, -17.5), (16.5, -17.5)]),
        preuve=[P["pcrs"], P["ign24"], P["p25"],
                pnx("a1ffea74", "bungalows bleus et clôture (az 90)"),
                planche_ref("revue_zoom/base_vie_vercors.jpg")],
        planche_boite=(0, -45, 45, -5)))

    F.append(dict(
        id="CHG-006", nature="abords_reamenages", secteur="verdun_ne",
        description=("Rive SE de l'avenue de Verdun NE (façade du quartier neuf, bande de 3 à 24 m au SE de la chaussée) : 2022 rangée d'arbres, palissade blanche et ancienne voie de service ; 01/05/2024 pelles, "
                     "barrières ; 24/08/2024 clôtures Heras, bungalows, portail de chantier ; 18/05/2025 haies taillées, parkings "
                     "riverains, plus aucune clôture. Chaussée et marquages de Verdun inchangés entre août 2024 et mai 2025."),
        date_min="2024-08-24", date_max="2025-05-18", confiance="haute",
        effet_pcrs_2022="invalide (abords) ; chaussée valide", interet_adas="rive de chaussée (clôtures -> haies), entrées de véhicules",
        source_recommandee="photos Panoramax/Mapillary 2025-05-18 (8 calées) + Pléiades 2025",
        geometry=poly([(20.1, 9.9), (110.1, 99.9), (125.0, 85.0), (35.0, -5.0)]),
        preuve=[P["pcrs"], P["ign24"], P["p25"],
                pnx("c2284fa6", "pelle, barrières"), pnx("27861f06", "barrières jaunes"),
                pnx("97890c75", "clôtures, bungalows"), pnx("4407962b", "clôtures, bungalows"), pnx("050fff48", "clôtures"),
                pnx("7a182db7", "haie, plus de clôture"), pnx("e081167a", "haie, parking"), pnx("9fc8ba46", "entrée de parking"),
                mly("166959789222", "2022-06-10", "palissade blanche"), planche_ref("carte_auto_2024_2025.png")],
        planche_boite=(10, 0, 120, 105)))

    F.append(dict(
        id="CHG-007", nature="acces_riverain_nouveau", secteur="verdun_ne",
        description=("Entrée de parking riverain sur la rive SE de Verdun NE (≈ (72 ; 62) local) : palissade en 2022, portail de "
                     "chantier en août 2024, entrée de parking entre deux haies en mai 2025 (abaissé de bordure probable)."),
        date_min="2024-08-24", date_max="2025-05-18", confiance="moyenne",
        effet_pcrs_2022="invalide", interet_adas="véhicules entrant / sortant, abaissé de bordure",
        source_recommandee="photos 2025-05-18 (Mapillary 322561262092, Panoramax 9fc8ba46)",
        geometry=point(72.0, 62.0),
        preuve=[mly("166959789222", "2022-06-10"), mly("105872602225", "2024-08-24", "pose calée sur bordures"),
                mly("322561262092", "2025-05-18"),
                pnx("9fc8ba46", "entrée de parking entre deux haies")],
        planche_boite=(52, 42, 92, 82)))

    F.append(dict(
        id="CHG-008", nature="marquage_modifie", secteur="verdun_ne",
        description=("Approche NE du carrefour sur Verdun (x 10..60) : en 2022 deux voies vers le SO avec flèches de tourne-à-gauche "
                     "et cercle « 50 » ; depuis 2024, large zone hachurée blanche centrale et nouvelle répartition des voies (bandes "
                     "continues), identiques en août 2024 et en mai 2025. Bordures inchangées."),
        date_min="2023-03-18", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="marquages invalides ; bordures valides", interet_adas="configuration des voies et marquages (détection de voie)",
        source_recommandee="IGN 2024 + ortho-photo des 360° calées 2024-08-24 / 2025-05-18 (photo_ortho.py) ; levé GAM à confronter",
        geometry=poly([(1.25, 12.72), (51.25, 65.92), (65.83, 52.22), (15.83, -0.98)]),
        preuve=[P["pcrs"], P["ign24"], P["p25"],
                pnx("d7279ab8", "pas de hachures"), pnx("e005e86b", "pas de hachures, flèches"),
                pnx("79a18815", "zone hachurée (pose calée)"), pnx("eeb2f8f1", "zone hachurée (pose calée)"), pnx("35a02e70", "zone hachurée"),
                planche_ref("revue_zoom/verdun_NE_marquage.jpg")],
        planche_boite=(5, 5, 65, 65)))

    F.append(dict(
        id="CHG-009", nature="reprise_enrobe", secteur="coeur",
        description=("Cœur du carrefour : chantier de tranchées le 01/05/2024 (pelles Komatsu, clôtures Heras, enrobé découpé à "
                     "l'angle NE) ; le 09/08/2024 grandes reprises d'enrobé plus sombres au centre et sur la voie SO. Zébras, "
                     "traversées cyclables jaunes et vertes, îlots et bordures aux mêmes places en 2022, 2024 et mai 2025. Cohérent "
                     "avec la 1re phase du réseau de chaleur urbain de Meylan (démarrée en avril 2024, MMV-166)."),
        date_min="2023-03-18", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="texture de chaussée seulement (géométrie valide)", interet_adas="aspect du revêtement (patchs sombres, joints)",
        source_recommandee="IGN 2024 (emprise des patchs) + photos 360° calées 2024-08-24 et 2025-05-18 (aspect)",
        geometry=multipoly([[(-16, -12), (10, -12), (10, 18), (-16, 18)], bande((-33, -31), (-17, -16), 4.5)]),
        preuve=[P["pcrs"], P["ign24"],
                pnx("1149e115", "pelles, clôtures Heras, enrobé découpé"), pnx("3fc0ff2e", "pelle, barrières"),
                pnx("a896d871", "pelles"), pnx("b4013696", "pelles"),
                pnx("5c0d1d39", "reprises d'enrobé (pose calée)"), pnx("2ab4efbc", "pose calée"),
                {"source": "document", "ref": "data/raw/docs_web/meylan_fr/MMV-166-decembre25-janvier26.pdf", "note": "RCU : 1re phase démarrée en avril 2024"},
                planche_ref("revue_zoom/coeur_3dates.jpg"), planche_ref("revue_zoom/enrobe_coeur.jpg")],
        planche_boite=(-40, -40, 30, 30)))

    F.append(dict(
        id="CHG-010", nature="tranchee_refermee", secteur="verdun_so",
        description=("Bande d'enrobé neuf (≈ 3,5 m) dans la chaussée NO de Verdun SO, de l'allée (-131 ; -128) jusqu'à l'arrêt La "
                     "Revirée (-45 ; -44) : absente en 2022, nette le 09/08/2024 et sur les photos d'août 2024 et de mai 2025."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="haute",
        effet_pcrs_2022="texture de chaussée seulement", interet_adas="aspect du revêtement (bande sombre longitudinale)",
        source_recommandee="IGN 2024 (emprise) + photos 2024-08-24 / 2025-05-18 (aspect)",
        geometry=poly(bande((-131, -128), (-45, -44), 3.5)),
        preuve=[P["pcrs"], P["ign24"], pnx("6a93db6e", "bande sombre"), pnx("6d922988"), pnx("034cb578", "bande sombre"), pnx("e27153f2"),
                planche_ref("revue_zoom/enrobe_verdun_SO.jpg")],
        planche_boite=(-140, -140, -35, -35)))

    F.append(dict(
        id="CHG-011", nature="tranchee_refermee", secteur="reviree_nord",
        description=("Bande d'enrobé neuf (≈ 2,5 m) côté NE de la chaussée du chemin de la Revirée, de (-60 ; 105) à (-22 ; 37) : "
                     "absente en 2022 et sur les vues Mapillary du 24/02/2024 (pose a priori), nette le 09/08/2024."),
        date_min="2024-02-24", date_max="2024-08-09", confiance="moyenne",
        effet_pcrs_2022="texture de chaussée seulement", interet_adas="aspect du revêtement",
        source_recommandee="IGN 2024",
        geometry=poly(bande((-60, 105), (-22, 37), 2.5)),
        preuve=[P["pcrs"], P["ign24"], mly("175815200802", "2024-02-24", "chaussée uniforme (pose a priori)"),
                mly("749823196860", "2024-02-24"), planche_ref("revue_zoom/enrobe_reviree.jpg")],
        planche_boite=(-80, 30, 0, 115)))

    F.append(dict(
        id="CHG-012", nature="renovation_batiment", secteur="nord",
        description=("Immeuble au nord du carrefour (BD TOPO BATIMENT0000000301570452, h 20,5 m) : échafaudages et filets le "
                     "10/06/2022, toiture gris foncé en 2022 devenue blanche en 2024 et 2025, façade blanche à volets bruns en mai 2025."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="moyenne",
        effet_pcrs_2022="apparence (toit, façade) ; emprise valide", interet_adas="apparence d'un bâtiment visible depuis le carrefour",
        source_recommandee="IGN 2024 (toit) + photos 2025-05-18 (façade)",
        geometry=poly(batiment("BATIMENT0000000301570452")),
        preuve=[P["pcrs"], P["ign24"], P["p25"], mly("176900834736", "2022-06-10", "échafaudages et filets"),
                mly("386821389914", "2022-06-10"), planche_ref("ombres/tour_nord_zoom.jpg")],
        planche_boite=(-30, 30, 25, 85)))

    # arbres (revue antérieure orthos_recentes : observations OR-V-003 à OR-V-011, revérifiées sur zone_C3 / zone_D3)
    obs = "recon/out/paquet_jardin/v2/enrichi/recensement/ortho_recentes/saisie/observations.json"
    for i, (x, y, conf, ov, txt) in enumerate([
            (139.25, -53.25, "haute", "OR-V-003", "grand feuillu (houppier ≈ 15 m) abattu ; pelouse et lits minéraux en 2024"),
            (84.1, -73.2, "moyenne", "OR-V-011", "grand arbre (houppier ≈ 12 m) abattu ; pelouse et allée en 2024"),
            (84.2, -77.3, "faible", "OR-V-010", "bosquet abattu"),
            (76.3, -102.6, "faible", "OR-V-009", "massif arboré (≈ 7 m) remplacé par des places de stationnement et une jardinière")]):
        F.append(dict(
            id=f"CHG-{13 + i:03d}", nature="arbre_abattu", secteur="est", description=txt,
            date_min="2022-05-10", date_max="2024-08-09", confiance=conf,
            effet_pcrs_2022="invalide (arbre présent en 2022 et au LiDAR 2021)", interet_adas="masque de visibilité, ombre",
            source_recommandee="IGN 2024 + IRC 2024", geometry=point(x, y),
            preuve=[P["pcrs"], P["ign24"], {"source": "revue antérieure", "id": ov, "ref": obs}],
            planche_boite=(x - 15, y - 15, x + 15, y + 15)))
    F.append(dict(
        id="CHG-017", nature="arbres_plantes", secteur="est",
        description="Jeunes arbres de la plantation 2023-2024 du parc est (houppiers 1 à 1,5 m en août 2024).",
        date_min="2022-05-10", date_max="2024-08-09", confiance="moyenne",
        effet_pcrs_2022="absents en 2022", interet_adas="faible (petits sujets)", source_recommandee="IGN 2024 + photos 2024-08",
        geometry=multipoint([(138.305, -57.947), (142.842, -55.065), (146.345, -55.935), (149.183, -57.507), (143.928, -50.686)]),
        preuve=[P["ign24"], {"source": "revue antérieure", "id": "OR-V-004 à OR-V-008", "ref": obs}],
        planche_boite=(120, -75, 155, -35)))
    F.append(dict(
        id="CHG-018", nature="amenagement_paysager_modifie", secteur="est",
        description=("Deux bandes de galets / gravier (≈ 2 et 2,5 m) dans la noue du parc est, visibles le 09/08/2024 mais plus sur "
                     "Pléiades 2025 (enherbées ou recouvertes ?)."),
        date_min="2024-08-09", date_max="2025-06-22", confiance="faible",
        effet_pcrs_2022="invalide (chantier en 2022) ; état 2025 incertain", interet_adas="nul (hors chaussée)",
        source_recommandee="Pléiades 2025 ; à confirmer par photo",
        geometry=multipoly([bande((128.5, -45), (147, -41), 2.5), bande((118.5, -50.5), (147, -46), 2.5)]),
        preuve=[P["ign24"], P["p25"], {"source": "revue antérieure", "id": "OR-V-020", "ref": obs}],
        planche_boite=(110, -65, 155, -25)))
    F.append(dict(
        id="CHG-019", nature="travaux_annonces_non_observes", secteur="vercors",
        description=("Avenue du Vercors : panneau de chantier C1 « Avenue du Vercors, avril à novembre 2025 » (traversées piétonnes "
                     "sécurisées, regroupement d'arrêts) et trottoirs refaits jusqu'au 30/01/2026. Le 18/05/2025, l'entrée du Vercors "
                     "(≈ 40 premiers mètres, Panoramax 119d9094, azimuts 152-168) ne montre aucun chantier ; au-delà, aucune photo entre "
                     "le 12/01/2025 et le 23/06/2025 : l'état du Vercors au printemps 2025 n'est pas observé. Zone de risque, pas un "
                     "changement constaté."),
        date_min="2025-04-01", date_max="2025-11-30", confiance="faible", observe=False,
        effet_pcrs_2022="à vérifier pour une date cible postérieure au 01/04/2025", interet_adas="traversées piétonnes, arrêts",
        source_recommandee="état du 12/01/2025 (photos vélo) et Pléiades 2025 ; viser une date cible ≤ fin mars 2025 sur le Vercors si besoin",
        geometry=multipoly([bande((4, -11), (15, -34), 30), bande((15, -34), (38, -129), 30), bande((38, -129), (41, -150), 30)]),
        preuve=[{"source": "document", "ref": "data/raw/docs_web/meylan_fr/Panneau-generique-travaux-d-amelioration-ligne-C1.pdf",
                 "note": "1 Carrefour Verdun/Vercors juillet-octobre 2025 ; 3 Avenue du Vercors avril-novembre 2025"},
                {"source": "code", "ref": "recon/pcg/enrichir/orthos_recentes.py:47", "note": "FIN_TROTTOIRS_VERCORS = 2026-01-30"},
                {"source": "document", "ref": "data/raw/docs_web/meylan_fr/MMV-165.pdf", "note": "point travaux C1 oct.-nov. 2025"},
                pnx("119d9094", "entrée du Vercors sans chantier le 18/05/2025 (azimuts 152-168)"),
                pnx("a1ffea74", "dernière vue du Vercors avant travaux (12/01/2025)")],
        planche_boite=(-15, -150, 70, 0)))
    F.append(dict(
        id="CHG-020", nature="renovation_batiment", secteur="nord_ouest",
        description=("Toiture du bâtiment commercial au NO (BD TOPO BATIMENT0000000301570441, x -123..-97, y 88..124) : membrane "
                     "gris foncé en 2022, claire en 2024 et sur Pléiades 2025 (le toit voisin, clair aux deux dates, sert de témoin "
                     "radiométrique)."),
        date_min="2022-05-10", date_max="2024-08-09", confiance="moyenne",
        effet_pcrs_2022="apparence du toit ; emprise valide", interet_adas="faible (toit, vu de loin)",
        source_recommandee="IGN 2024", geometry=poly(batiment("BATIMENT0000000301570441")),
        preuve=[P["pcrs"], P["ign24"], P["p25"], planche_ref("revue_zoom/nord_ouest_gymnase.jpg")],
        planche_boite=(-140, 75, -80, 135)))
    F.append(dict(
        id="CHG-021", nature="amenagement_paysager_modifie", secteur="est",
        description=("Cœurs d'îlot du quartier est encore en terre nue de chantier le 09/08/2024 (cour x 100..150, y 5..35 ; abords "
                     "nord x 115..142, y 62..95), aménagés (végétal, cheminements) sur Pléiades 2025 : finitions paysagères "
                     "postérieures à l'IGN 2024."),
        date_min="2024-08-09", date_max="2025-06-22", confiance="moyenne",
        effet_pcrs_2022="invalide (chantier en 2022) ; l'IGN 2024 n'est pas l'état 2025 ici", interet_adas="faible (cœurs d'îlot, peu visibles des voies)",
        source_recommandee="Pléiades 2025 + levé GAM (à vérifier) ; photo à rechercher",
        geometry=multipoly([[(100, 5), (150, 5), (150, 35), (100, 35)], [(115, 62), (142, 62), (142, 95), (115, 95)]]),
        preuve=[P["ign24"], P["p25"], planche_ref("revue_zoom/cour_est.jpg"), planche_ref("revue_zoom/est_nord.jpg")],
        planche_boite=(90, 0, 155, 100)))
    return F


def carte_ensemble(feats):
    """Carte de tous les changements sur PCRS 2022 | IGN 2024 (étiquettes CHG-xxx)."""
    b = boite_locale(-150, -150, 160, 150)
    cols = {"haute": (255, 0, 255, 235), "moyenne": (255, 170, 0, 235), "faible": (0, 230, 255, 235)}
    pans = []
    for k in ("2022", "2024"):
        v = Vue(k, b, 900)
        for f in feats:
            p, g = f["properties"], f["geometry"]
            col = cols[p["confiance"]] if p.get("observe", True) else (255, 255, 255, 200)
            lab = p["id"][4:]
            if g["type"] in ("Polygon", "MultiPolygon"):
                polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
                tous = []
                for pp in polys:
                    q = [(c[0] - O[0], c[1] - O[1]) for c in pp[0]]
                    v.poly(q, col, 2, ferme=False)
                    tous += q
                u, w = v.P(float(np.mean([q[0] for q in tous])), float(np.mean([q[1] for q in tous])))
                v.d.rectangle([u - 2, w - 9, u + 30, w + 8], fill=(0, 0, 0, 190))
                v.d.text((u + 1, w - 8), lab, fill=col, font=police(14))
            else:
                pts = [g["coordinates"]] if g["type"] == "Point" else g["coordinates"]
                for n, c in enumerate(pts):
                    v.point(c[0] - O[0], c[1] - O[1], col, r=6, etiquette=lab if n == 0 else None)
        pans.append(v.grille(10, 50).im)
    im = assembler(pans, "Changements 2022-05-10 -> 2025-06-22 (numéros CHG-xxx) : magenta confiance haute, orange moyenne, cyan faible, blanc = annoncé non observé")
    s = PLANCHES / "carte_changements_2022_2025.png"
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(s, optimize=True)
    return rel(s)


def planche_zone(f):
    x0, y0, x1, y1 = f.pop("planche_boite")
    L = max(x1 - x0, y1 - y0, 30.0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, x1, y0, y1 = cx - L / 2, cx + L / 2, cy - L / 2, cy + L / 2
    b = boite_locale(x0, y0, x1, y1)
    px = 560
    pas = 5.0 if L <= 80 else 10.0
    g = f["geometry"]
    pans = []
    for k in ("2022", "2024", "2025"):
        v = Vue(k, b, px)
        col = (255, 0, 255, 230)
        if g["type"] in ("Polygon", "MultiPolygon"):
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for pp in polys:
                v.poly([(c[0] - O[0], c[1] - O[1]) for c in pp[0]], col, 2, ferme=False)
        else:
            pts = [g["coordinates"]] if g["type"] == "Point" else g["coordinates"]
            for c in pts:
                v.point(c[0] - O[0], c[1] - O[1], col, r=7)
        pans.append(v.grille(pas, 10 if pas == 5 else 50).im)
    s = PLANCHES / "zones" / f"{f['id']}.png"
    s.parent.mkdir(parents=True, exist_ok=True)
    titre = f"{f['id']} {f['nature']} ({f['date_min']} -> {f['date_max']}, confiance {f['confiance']}) : PCRS 2022 | IGN 2024 | Pléiades 2025"
    im = assembler(pans, titre)
    # palette adaptative 256 couleurs (diffusion d'erreur) : PNG ~3 fois plus léger, lisible pour la revue
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(s, optimize=True)
    return rel(s)


def aire(g):
    def a(r):
        r = np.asarray(r)
        return 0.5 * abs(float(np.dot(r[:, 0], np.roll(r[:, 1], -1)) - np.dot(r[:, 1], np.roll(r[:, 0], -1))))
    if g["type"] == "Polygon":
        return a(g["coordinates"][0])
    if g["type"] == "MultiPolygon":
        return sum(a(p[0]) for p in g["coordinates"])
    return 0.0


def main():
    F = inventaire()
    feats = []
    for f in F:
        f.setdefault("observe", True)
        f["planche"] = planche_zone(f)
        g = f.pop("geometry")
        f["surface_m2"] = round(aire(g), 1)
        feats.append({"type": "Feature", "geometry": g, "properties": f})
    fc = {"type": "FeatureCollection", "name": "changements_2022_2025",
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
          "meta": {"site": "Paquet Jardin (Meylan, 38)", "fenetre": ["2022-05-10", "2025-06-22"],
                   "repere": "L93 (EPSG:2154) ; local = L93 − (917279.43, 6460289.98)",
                   "genere": "recon/out/paquet_jardin/v2_avant_travaux/inventaire/changements/outils/construire_changements.py",
                   "proprietes": {"nature": "type de changement", "date_min": "dernière date où l'état ancien est observé",
                                  "date_max": "première date où l'état nouveau est observé", "preuve": "liste de sources (source, id, date, url / ref)",
                                  "confiance": "haute | moyenne | faible", "observe": "false = risque annoncé, non constaté",
                                  "effet_pcrs_2022": "validité de la géométrie / apparence PCRS 2022 pour un état 2025"},
                   "photos": "les vignettes tirées de Panoramax / Mapillary (CC-BY-SA 4.0) sont dans photos_non_versionnees/ (non versionné)"},
          "features": feats}
    fc["meta"]["carte"] = carte_ensemble(feats)
    out = ICI / "changements_2022_2025.geojson"
    out.write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
    res = {"n": len(feats), "par_nature": {}, "surface_totale_m2_polygones_observes": 0.0}
    for ft in feats:
        p = ft["properties"]
        res["par_nature"].setdefault(p["nature"], 0)
        res["par_nature"][p["nature"]] += 1
        if p["observe"]:
            res["surface_totale_m2_polygones_observes"] += p["surface_m2"]
        print(p["id"], p["nature"], p["date_min"], p["date_max"], p["confiance"], p["surface_m2"], p["planche"])
    res["surface_totale_m2_polygones_observes"] = round(res["surface_totale_m2_polygones_observes"], 1)
    ecrire_json(DONNEES / "changements_resume.json", res)
    print(rel(out), res)


if __name__ == "__main__":
    main()
