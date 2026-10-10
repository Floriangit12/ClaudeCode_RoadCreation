# -*- coding: utf-8 -*-
"""Construit obs_web.json (agent DOC-LOCALE) : observations tirées de documents web
(panneaux et magazines de Meylan, Métropole, carte Chronovélo 2026), d'OpenStreetMap
(éditions postérieures aux travaux 2025) et de l'inventaire arboré de la Métropole (2023).

Lancement : python -I recon/out/paquet_jardin/v2/enrichi/recensement/web/construire_obs_web.py
Entrées : preuves/osm_extrait_site_2026-05-31.json, preuves/patrimoine_arbore_gam2023_site.json,
          description v2 (base/surfaces, base/marquages), objets du paquet (mobilier, arbres),
          relief/relief_zones_2026.geojson. Sortie : obs_web.json (tableau d'observations).
"""
import json, math, os

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 7))
W = "recon/out/paquet_jardin/v2/enrichi/recensement/web"
P = W + "/preuves/"
O = (917279.43, 6460289.98)
Z0 = 216.30


def chemin(rel):
    return os.path.join(RACINE, rel)


def charge(rel):
    with open(chemin(rel), encoding="utf-8") as f:
        return json.load(f)


def loc(x, y):
    return [round(x - O[0], 2), round(y - O[1], 2)]


def pip(x, y, poly):
    """point dans polygone (anneau extérieur, lancer de rayon)"""
    dedans = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i][0], poly[i][1]
        x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                dedans = not dedans
    return dedans


def anneaux(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [p[0] for p in geom["coordinates"]]
    return []


surfaces = charge("recon/out/paquet_jardin/v2/description/base/surfaces.geojson")["features"]
marquages = charge("recon/out/paquet_jardin/v2/description/base/marquages.geojson")["features"]
mobilier = charge("recon/out/paquet_jardin/package/donnees/objets/mobilier.geojson")["features"]
arbres = charge("recon/out/paquet_jardin/package/donnees/objets/arbres.geojson")["features"]
zones = charge("recon/out/paquet_jardin/package/donnees/relief/relief_zones_2026.geojson")["features"]
osm = charge(P + "osm_extrait_site_2026-05-31.json")
inv = charge(P + "patrimoine_arbore_gam2023_site.json")["arbres"]
ZONES_TRAVAUX = {"ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee",
                 "ancienne_chaussee_trottoir_par_defaut", "chaussee_2026"}


def zone_travaux(x, y):
    for f in zones:
        if f["properties"].get("zone") in ZONES_TRAVAUX:
            for a in anneaux(f["geometry"]):
                if pip(x, y, a):
                    return f["properties"]["zone"]
    return None


def surface_en(x, y):
    for f in surfaces:
        for a in anneaux(f["geometry"]):
            if pip(x, y, a):
                p = f["properties"]
                return p["id"], p.get("classe"), (p.get("revetement") or {}).get("materiau_id")
    return None


def osm_el(typ, i):
    for e in osm["elements"]:
        if e["type"] == typ and e["id"] == i:
            return e
    raise KeyError((typ, i))


def milieu(pts):
    """point au milieu de la polyligne (abscisse curviligne)"""
    if len(pts) == 1:
        return pts[0]
    L = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    s = sum(L) / 2
    for i, l in enumerate(L):
        if s <= l:
            t = s / l if l else 0
            return [pts[i][0] + t * (pts[i + 1][0] - pts[i][0]), pts[i][1] + t * (pts[i + 1][1] - pts[i][1])]
        s -= l
    return pts[-1]


def echantillons(pts, pas=2.0):
    out = []
    for i in range(len(pts) - 1):
        l = math.dist(pts[i], pts[i + 1])
        n = max(1, int(l / pas))
        for k in range(n):
            t = k / n
            out.append((pts[i][0] + t * (pts[i + 1][0] - pts[i][0]), pts[i][1] + t * (pts[i + 1][1] - pts[i][1])))
    out.append(tuple(pts[-1]))
    return out


def surfaces_le_long(pts):
    cpt = {}
    for x, y in echantillons(pts):
        s = surface_en(x, y)
        if s:
            cpt[s] = cpt.get(s, 0) + 1
    return sorted(cpt.items(), key=lambda kv: -kv[1])


def plus_proche(features, x, y, filtre=lambda p: True, cle_xy=None):
    best = None
    for f in features:
        p = f["properties"]
        if not filtre(p):
            continue
        if cle_xy:
            fx, fy = cle_xy(f)
        else:
            g = f["geometry"]
            if g["type"] != "Point":
                continue
            fx, fy = g["coordinates"][:2]
        d = math.dist((fx, fy), (x, y))
        if best is None or d < best[0]:
            best = (d, p["id"], p)
    return best


def xy_marquage(f):
    p = f["properties"]
    if p.get("pose") and p["pose"].get("point_l93"):
        return p["pose"]["point_l93"][:2]
    g = f["geometry"]
    if g["type"] == "Point":
        return g["coordinates"][:2]
    if g["type"] == "Polygon":
        r = g["coordinates"][0]
    elif g["type"] == "MultiPolygon":
        r = g["coordinates"][0][0]
    elif g["type"] == "LineString":
        r = g["coordinates"]
    else:
        r = g["coordinates"][0]
    return [sum(c[0] for c in r) / len(r), sum(c[1] for c in r) / len(r)]


obs = []


def ajoute(**k):
    k["id"] = "DOC-LOCALE-%03d" % (len(obs) + 1)
    ordre = ["id", "source", "date_image", "classe", "sous_type", "attributs", "position", "lien_description",
             "statut", "valide_2026", "confiance", "preuve"]
    obs.append({c: k.get(c) for c in ordre})


def pos(x, y, prec, methode, note=None):
    d = {"l93": [round(x, 2), round(y, 2)], "local": loc(x, y), "precision_m": prec, "methode": methode}
    if note:
        d["note"] = note
    return d


# ---------------------------------------------------------------- 1. documents web (Ville, Métropole)
ajoute(source="web:meylan_panneau_carrefour_verdun_vercors_2025",
       date_image="2025-04-03 (PDF du panneau ; plan sur fond PCRS 2022)",
       classe="autre", sous_type="programme_travaux_carrefour",
       attributs={"elements_annonces": [
           "suppression de la voie de tourne-à-droite Verdun -> Vercors",
           "déplacement et mutualisation des quais de bus « La Revirée » (un quai par sens, en ligne)",
           "sécurisation de la traversée piétonne et cycle (branche SO, refuge sur TPC planté)",
           "déplacement de l'entrée du parking relais P+R",
           "création d'un cheminement piéton le long du domaine « Les Saules Blancs » (rive E du Vercors)",
           "plantations d'arbres et d'arbustes, gestion alternative des eaux pluviales"],
           "justification": "carrefour plus compact, végétalisation, traversées sécurisées « notamment pour les scolaires »",
           "lecture_legende_plan": "orange = identité Chronovélo (rives, pavés de traversée, barrettes) ; bleu turquoise = bande sous le zébra qui traverse la piste ; vert clair = espaces plantés ; vert foncé = TPC planté ; tiretés violets = bordures d'îlots",
           "maitrise_ouvrage": "Grenoble-Alpes Métropole (délégation SMMAG et Ville), marché 2024-TX-ACP-0331 en 3 lots"},
       position=pos(O[0], O[1], 80.0, "projection_description", "programme du carrefour entier"),
       lien_description=None, statut="confirme",
       valide_2026={"valeur": True, "raison": "projet réalisé de juin à décembre 2025 (meylan.fr ; Meylan ma ville n°165 à 167) ; écarts entre plan et réalisation possibles et non vérifiables sans photo postérieure"},
       confiance="haute",
       preuve={"fichier": P + "panneau_carrefour_entier.jpg", "zooms": [P + "panneau_carrefour_zoom_centre.png", P + "panneau_carrefour_zoom_vercors.png"],
               "document": "data/raw/docs_web/meylan_fr/Panneau-Amenagement-carrefour-Verdun-Vercors.pdf"})

xT, yT = (917232.5 + 917260.7) / 2, (6460238.2 + 6460267.4) / 2
ajoute(source="web:meylan_ma_ville_165_p12+166_p7",
       date_image="2025-10 (n°165, oct.-nov. 2025) et 2025-12 (n°166, déc. 2025-janv. 2026)",
       classe="arbre", sous_type="jeunes_plantations_2025",
       attributs={"calendrier": "fin des travaux du carrefour annoncée en décembre 2025 ; avenue du Vercors (trottoirs, végétalisation) jusqu'au 30/01/2026 ; avenue du Granier jusqu'en février 2026",
                  "plantations": "arbres et arbustes plantés en fin de chantier (saison automne-hiver 2025-2026)",
                  "etat_octobre_2026_deduit": "première saison de végétation : tiges de 3 à 4 m (force 16/18 à 20/25), tuteurage tripode ou quadripode d'environ 2 m, cuvette d'arrosage, pied d'arbre végétalisé ou paillé, couronne peu fournie",
                  "zones": "TPC de Verdun SO (5 arbres), bande plantée NO (5), angle NO (1), noue SE (4) selon le plan 2025"},
       position=pos(xT, yT, 30.0, "projection_description", "centre du TPC planté de Verdun SO (plan 2025, hist-10)"),
       lien_description=None, statut="confirme",
       valide_2026={"valeur": True, "raison": "documents municipaux postérieurs au démarrage du chantier ; règle de plantation de la charte de l'arbre (LOC-VEG-003)"},
       confiance="moyenne",
       preuve={"fichier": P + "mmv165_p12_c1_ou_en_est_on.png", "complement": P + "mmv166_p7_travaux.png",
               "documents": ["data/raw/docs_web/meylan_fr/MMV-165.pdf", "data/raw/docs_web/meylan_fr/MMV-166-decembre25-janvier26.pdf"]})

ajoute(source="web:meylan_presentation_reunion_2025-04-03_p7",
       date_image="2025-04-03",
       classe="surface", sous_type="bilan_surfaces_phase2",
       attributs={"perimetre": "phase 2 Vercors-Granier, carrefour Verdun/Vercors compris (plus large que le site)",
                  "surface_vegetalisee_m2": {"avant": 1700, "apres": 2400},
                  "trottoir_m2": {"avant": 1800, "apres": 2300},
                  "chaussee_et_ilots_bitumes_m2": {"avant": 7350, "apres": 6130},
                  "arbres_objectif_n": 94, "traversees_reamenagees_n": 11,
                  "reduction_chaussee_annoncee_pct": 11,
                  "note": "7350 -> 6130 m² donne -16,6 % et non -11 % : écart interne au document ; contrôle global de tendance seulement (moins d'enrobé, plus de vert et de trottoir)"},
       position=pos(O[0], O[1], 600.0, "projection_description", "bilan agrégé de l'opération"),
       lien_description=None, statut="incertain",
       valide_2026={"valeur": True, "raison": "objectifs du projet réalisé ; valeurs non ventilées par site"},
       confiance="moyenne",
       preuve={"fichier": P + "presentation_2025-04-03_p7_bilan.png", "document": "data/raw/docs_web/meylan_fr/presentation-reunion-C1-03-04-25.pdf"})

# cheminement E du Vercors (panneau Vercors, segment 1) + confirmation OSM 2026
e = osm_el("way", 1488785305)
pts_site = [p for p in e["l93"] if abs(p[0] - O[0]) < 160 and abs(p[1] - O[1]) < 160]
xm, ym = milieu(pts_site)
ajoute(source="web:meylan_panneau_avenue_vercors_2025 ; web:osm:way/1488785305@2026-05-14",
       date_image="2025-04-03 (panneau) ; 2026-05-14 (édition OSM)",
       classe="surface", sous_type="cheminement_pieton_neuf_rive_E_Vercors",
       attributs={"programme_segment_1": "création d'un cheminement piéton côté Est reliant le chemin des Sources ; création d'une noue paysagère d'infiltration des eaux pluviales ; réaménagement et sécurisation des traversées piétonnes",
                  "osm": {"footway": "sidewalk", "surface": "compacted", "smoothness": "good", "lit": "yes"},
                  "materiau_propose": "stabilisé compacté clair (sablé), et non enrobé ; à confirmer sur photo",
                  "longueur_dans_site_m": round(sum(math.dist(pts_site[i], pts_site[i + 1]) for i in range(len(pts_site) - 1)), 1),
                  "trace_l93": pts_site},
       position=pos(xm, ym, 5.0, "projection_description", "milieu de la portion OSM dans le site"),
       lien_description=None, statut="absent_de_description",
       valide_2026={"valeur": True, "raison": "objet créé par les travaux 2025-2026 (Vercors jusqu'au 30/01/2026), cartographié en mai 2026"},
       confiance="moyenne",
       preuve={"fichier": P + "panneau_vercors_segment1_revire.jpg", "osm": P + "osm_extrait_site_2026-05-31.json", "osm_id": "way/1488785305"})

ajoute(source="web:gam_carte_chronovelo_2026-01",
       date_image="2026-01 (carte « Axes Chronovélo », copie Wayback du 2026-03-08)",
       classe="autre", sous_type="itineraire_chronovelo",
       attributs={"chronovelo_1": "existant (jaune) : arrive de Grenoble par Verdun SO, tourne au carrefour vers le Vercors (baïonnette), continue vers Buclos et Béalières",
                  "verdun_NE": "Chronovélo 1 « planifié » (tireté bleu) vers Montbonnot : l'identité Chronovélo n'y est pas encore obligatoire",
                  "station": "une station Chronovélo figurée sur Verdun SO en amont du carrefour (position cartographique imprécise, 100 à 400 m)",
                  "consequence": "identité Chronovélo (rives et pavés jaunes, axe • • — •, bandes turquoise) attendue sur la piste NO de Verdun SO, la traversée de la branche SO et la piste du Vercors"},
       position=pos(O[0], O[1], 50.0, "projection_description"),
       lien_description=None, statut="confirme",
       valide_2026={"valeur": True, "raison": "carte de janvier 2026, postérieure aux travaux"},
       confiance="moyenne",
       preuve={"fichier": P + "carte_chronovelo_2026_meylan.png", "legende": P + "carte_chronovelo_2026_legende.png",
               "document": "data/raw/docs_web/grenoblealpesmetropole/Carte-Chronovelo-janvier-2026.pdf"})

ajoute(source="web:gam_chronovelo_reunion_publique_2018-12-04_p26",
       date_image="2018 (photos « La Tronche - Meylan (2018) »)",
       classe="marquage", sous_type="identite_chronovelo_2018",
       attributs={"photo_b": "piste bidirectionnelle au niveau de la chaussée ; côté chaussée, file de pavés jaunes transversaux (environ 0,9 × 0,2 m) au droit d'un débouché ; côté trottoir, barrettes jaunes courtes ; logo vélo blanc ; zébra blanc continu sur la voie et la piste ; îlot à panneau carré bleu à flèche oblique ; rive jaune continue au-delà",
                  "photo_a": "piste en enrobé sombre entre chaussée et trottoir, file de pavés jaunes côté chaussée, rive jaune côté trottoir, trottoir en enrobé avec bordure béton, clôture en panneaux de treillis vert",
                  "usage": "pratique d'identité antérieure à 2022 sur la Chronovélo 1 de Meylan ; sert de repli typologique seulement"},
       position=pos(O[0] - 600.0, O[1] - 600.0, 1500.0, "projection_description", "section Chronovélo La Tronche - Meylan (av. de Verdun), non localisée"),
       lien_description=None, statut="incertain",
       valide_2026={"valeur": False, "raison": "photos de 2018, antérieures à l'harmonisation de 2021-2022 et aux travaux 2025 ; lieu non identifié"},
       confiance="faible",
       preuve={"fichier": P + "chronovelo2018_p26_photo_b.jpg", "complement": P + "chronovelo2018_p26_photo_a.jpg",
               "document": "data/raw/docs_web/cluq/Projet-Chronovelo-GAM-reunion-publique-04122018-V2.pdf"})

# ---------------------------------------------------------------- 2. OpenStreetMap, éditions postérieures aux travaux
def mob(i):
    for f in mobilier:
        if f["properties"]["id"] == i:
            return f["properties"]
    return None


q = osm_el("way", 185326915)
xm, ym = milieu(q["l93"])
abri = mob("abri_NO_0021")
ajoute(source="web:osm:way/185326915@2026-04-01",
       date_image="2026-04-01 (édition OSM ; non une image)",
       classe="abri_bus", sous_type="quai_bus_equipement",
       attributs={"quai": "La Revirée, sens Grenoble (réf. TAG 396)",
                  "afficheur_temps_reel": True, "passenger_information_display": "yes", "departures_board": "realtime",
                  "abri": "séparé (shelter=separate)", "banc": "séparé", "corbeille": "séparée", "eclaire": True,
                  "autres_objets_proches_osm": ["distributeur de titres M réso (node/12321482421)", "plan de quartier (node/12507625760)", "arceaux 10 places (node/8360665117)", "zone de stationnement Dott (node/10265340447)", "corbeille (node/1959017517)"],
                  "photo_mapillary_citee": "4411579125519625 (non consultée : API à jeton)",
                  "attribut_absent_de_la_description": "afficheur temps réel (borne ou écran intégré à l'abri)"},
       position=pos(xm, ym, 3.0, "projection_description", "milieu du quai OSM ; position latérale OSM restée sur l'ancienne bordure (hist-21)"),
       lien_description="abri_NO_0021" if abri else None, statut="attribut_corrige",
       valide_2026={"valeur": True, "raison": "édition OSM du 2026-04-01, après les travaux ; attributs d'équipement plausibles pour un arrêt de ligne Chrono"},
       confiance="moyenne",
       preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": "way/185326915"})

q = osm_el("way", 185326913)
xm, ym = milieu(q["l93"])
ajoute(source="web:osm:way/185326913@2025-09-21",
       date_image="2025-09-21 (attributs) ; géométrie reprise le 2025-10-27",
       classe="abri_bus", sous_type="quai_bus_equipement",
       attributs={"quai": "La Revirée, sens Montbonnot (réf. TAG 21 ; C1, 42, 80, 82, 164)",
                  "bande_podotactile": True, "accessible_fauteuil": True, "eclaire": True,
                  "abri": "séparé", "banc": "séparé (node/12321340512 : bois, dossier et accoudoirs)", "corbeille": "séparée",
                  "hauteur_quai_deduite_m": 0.18, "raison_hauteur": "quai partagé avec des lignes périurbaines (80, 82, 164), probablement en cars : 18 cm (GAM fiche 3 : 18 à 21 cm selon le matériel ; LOC-TC-001) ; la vue mesurée prime"},
       position=pos(xm, ym, 2.0, "projection_description", "milieu du quai OSM (coïncide avec le plan à 0,3 m près, hist-14)"),
       lien_description="abri_SE_0396", statut="confirme",
       valide_2026={"valeur": True, "raison": "quai repositionné dans OSM le 2025-10-27, en même temps que l'abri"},
       confiance="moyenne",
       preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": "way/185326913"})

q = osm_el("way", 1445374292)
xm, ym = milieu(q["l93"])
ajoute(source="web:osm:way/1445374292@2026-04-13",
       date_image="2026-04-13 (édition OSM)",
       classe="mobilier", sous_type="arret_bus_sans_abri",
       attributs={"arret": "La Revirée, chemin de la Revirée (Flexo 42, GTFS 0397)", "abri": False, "banc": False, "corbeille": False,
                  "information": "horaires papier (departures_board=timetable)"},
       position=pos(xm, ym, 3.0, "projection_description"),
       lien_description="poteau_REV_ligne42", statut="confirme",
       valide_2026={"valeur": True, "raison": "édition du 2026-04-13, hors zone des travaux 2025"},
       confiance="moyenne",
       preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": "way/1445374292"})

zebras = [f for f in marquages if f["properties"].get("type") == "zebra"]
for nid, extra, statut, conf in [
        (1959022964, "BEV présentes (tactile_paving=yes)", "confirme", "moyenne"),
        (1959022961, "BEV absentes selon OSM (tactile_paving=no) alors que le projet prévoit des bandes podotactiles à toutes les traversées", "incertain", "faible")]:
    n = osm_el("node", nid)
    x, y = n["l93"][0]
    b = plus_proche(zebras, x, y, cle_xy=xy_marquage)
    ajoute(source="web:osm:node/%d@%s" % (nid, n["timestamp"][:10]),
           date_image="%s (vérification sur place indiquée par check_date:traffic_signals:sound)" % n["timestamp"][:10],
           classe="feu", sous_type="traversee_pietonne_a_feux",
           attributs={"bouton_appel": False, "signal_sonore": False, "vibreur": False, "bev": extra,
                      "consequence_modelisation": "aucun boîtier de bouton d'appel ni répéteur sonore sur les supports de feux piétons de cette traversée"},
           position=pos(x, y, 3.0, "projection_description", "nœud OSM de traversée (branche Vercors)"),
           lien_description=b[1] if b and b[0] < 8 else None, statut=statut,
           valide_2026={"valeur": True, "raison": "vérifié en 2026 (check_date) après la fin des travaux"},
           confiance=conf,
           preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": "node/%d" % nid,
                   "distance_zebra_m": round(b[0], 2) if b else None})

n = osm_el("node", 9592546348)
x, y = n["l93"][0]
ajoute(source="web:osm:node/9592546348@2026-03-16",
       date_image="2026-03-16 (édition OSM)",
       classe="marquage", sous_type="passage_pieton",
       attributs={"marque": True, "bordure": "abaissée (kerb=lowered)", "bev": False},
       position=pos(x, y, 3.0, "projection_description", "chemin de la Revirée, accès parking"),
       lien_description=None, statut="incertain",
       valide_2026={"valeur": True, "raison": "hors zone des travaux 2025 ; édition 2026"},
       confiance="faible",
       preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": "node/9592546348"})

# voies et trottoirs : revêtements neufs (smoothness=excellent, check_date:surface)
groupes = [
    ([1412130596], "surface", "cheminement_beton_Saules_Blancs",
     {"revetement": "béton (surface=concrete), clair", "etat": "neuf (smoothness=excellent)", "eclaire": True,
      "programme": "« Création d'un cheminement piéton le long du domaine Les Saules Blancs » (panneau du carrefour)"},
     "moyenne", "ffiJo, 2026-05-14"),
    ([185327130, 699599900, 759539695, 1445374294, 1445374295, 1488785306], "surface", "trottoirs_enrobe_neuf_Verdun_SO",
     {"revetement": "enrobé (surface=asphalt)", "etat": "neuf (smoothness=excellent ; check_date:surface=2026-04-13)", "eclaire": True,
      "usure_proposee": 0},
     "moyenne", "Maxkam38, 2026-04-13"),
    ([698843233, 398052317], "surface", "piste_chronovelo_4m",
     {"revetement": "enrobé (surface=asphalt)", "etat": "neuf (smoothness=excellent)", "largeur_m": 4.0, "pente_pct": 0.0, "eclaire": True,
      "reserve": "le tracé OSM de way/398052317 reste sur l'ancienne traversée (hist-21) : attributs utilisables, géométrie non"},
     "moyenne", "Maxkam38, 2026-04-13"),
]
for ids, classe, st, attrs, conf, qui in groupes:
    pts = []
    for i in ids:
        pts += osm_el("way", i)["l93"]
    xm, ym = milieu(osm_el("way", ids[0])["l93"])
    lst = []
    for i in ids:
        lst += surfaces_le_long(osm_el("way", i)["l93"])
    voulu = {"cheminement_beton_Saules_Blancs": ("trottoir", "autre", "acces_riverain"),
             "trottoirs_enrobe_neuf_Verdun_SO": ("trottoir", "quai_bus"),
             "piste_chronovelo_4m": ("piste_cyclable",)}[st]
    cible = [r for r in lst if r[0][1] in voulu]
    lien = (cible[0] if cible else (lst[0] if lst else None))
    lien = lien[0][0] if lien else None
    a = dict(attrs)
    a["osm_ways"] = ["way/%d" % i for i in ids]
    a["surfaces_description_traversees"] = [{"id": s[0], "classe": s[1], "materiau": s[2], "n_echantillons": c} for s, c in lst[:6]]
    if cible:
        m = cible[0][0][2] or ""
        attendu = "beton" if "béton" in attrs["revetement"] else "enrob"
        statut = "confirme" if attendu in m else "attribut_corrige"
        a["materiau_description"] = m
    else:
        statut = "absent_de_description"
    ajoute(source="web:osm:" + ",".join("way/%d" % i for i in ids) + "@" + qui.split(", ")[1],
           date_image=qui.split(", ")[1] + " (édition OSM, contributeur " + qui.split(", ")[0] + ")",
           classe=classe, sous_type=st, attributs=a,
           position=pos(xm, ym, 4.0, "projection_description", "milieu du premier tronçon OSM"),
           lien_description=lien, statut=statut,
           valide_2026={"valeur": True, "raison": "état décrit après les travaux (édition 2026, revêtement noté neuf)"},
           confiance=conf,
           preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": a["osm_ways"]})

# Vercors : lane_markings=no (contradiction avec le plan)
for wid in (185326635, 169866973):
    w = osm_el("way", wid)
    xm, ym = milieu(w["l93"])
    tg = w["tags"]
    ajoute(source="web:osm:way/%d@%s" % (wid, w["timestamp"][:10]),
           date_image=w["timestamp"][:10] + " (édition OSM)",
           classe="marquage", sous_type="lignes_de_voie_vercors",
           attributs={"sens": "entrée vers le carrefour" if wid == 185326635 else "sortie du carrefour (vers le S)",
                      "voies": tg.get("lanes"), "lane_markings": tg.get("lane_markings"), "revetement": tg.get("surface"),
                      "etat": tg.get("smoothness"), "vitesse_osm": tg.get("maxspeed") + " (source:maxspeed=FR:urban, valeur par défaut et non relevée ; règle locale 30 km/h : LOC-VIT-001)",
                      "conflit": "le plan 2025 et le levé GAM portent des flèches et une ligne de délimitation sur l'entrée à 2 voies : lane_markings=no peut signifier « pas de marquage axial » ou une saisie à distance"},
           position=pos(xm, ym, 5.0, "projection_description"),
           lien_description=None, statut="incertain",
           valide_2026={"valeur": "incertain", "raison": "édition 2026 mais attribut contradictoire avec le levé GAM 2026"},
           confiance="faible",
           preuve={"fichier": P + "osm_extrait_site_2026-05-31.json", "osm_id": "way/%d" % wid})

# ---------------------------------------------------------------- 3. inventaire arboré de la Métropole (2023)
arb_pts = [(f["properties"]["id"], f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1], f["properties"]) for f in arbres]
# appariement un pour un (glouton par distance croissante, seuil 9 m) : une rangée de peupliers
# peut avoir moins de couronnes LiDAR que de troncs inventoriés
paires = sorted((math.dist((t["x"], t["y"]), (p[1], p[2])), t["id"], p[0], p[3]) for t in inv for p in arb_pts
                if math.dist((t["x"], t["y"]), (p[1], p[2])) < 9.0)
appar, pris = {}, set()
for d, tid, aid, p in paires:
    if tid in appar or aid in pris:
        continue
    appar[tid] = (d, aid, p)
    pris.add(aid)
for t in sorted(inv, key=lambda t: t["id"]):
    x, y = t["x"], t["y"]
    cand = appar.get(t["id"])
    ess = ("%s %s" % (t["genre"], t["espece"])) if t["genre"] else None
    if cand is None:
        statut, lien, conf, note = "absent_de_description", None, "faible", "aucun arbre de la description à moins de 9 m (ou rangée de peupliers fusionnée en une seule couronne LiDAR)"
    else:
        d, aid, p = cand
        lien = aid
        if p.get("essence") and ess and p["essence"].split(" (")[0].lower().startswith(ess.lower()):
            statut, conf, note = "confirme", "haute", "essence déjà portée par la description"
        elif ess is None:
            statut, conf, note = "confirme", "faible", "arbre présent à l'inventaire sans essence"
        else:
            statut = "attribut_corrige"
            conf = "moyenne" if d < 5 else "faible"
            note = "essence absente de la description (%s) ; écart de position %.1f m" % (p.get("source", "")[:40], d)
    z = zone_travaux(x, y)
    ajoute(source="web:data.gouv:patrimoine_arbore_gam:%s" % t["id"],
           date_image="2023-09-11 (mise à jour du jeu de données ; pas d'image)",
           classe="arbre", sous_type="arbre_inventaire_metropole",
           attributs={"id_metro": t["id"], "essence": ess, "nom_commun": t["nom"], "adresse": t["adresse"],
                      "forme_probable": "peuplier noir d'Italie (fastigié, 20-29 m d'après le LiDAR 2021)" if t["genre"] == "Populus" else None,
                      "note": note},
           position=pos(x, y, 3.0, "projection_description", "coordonnées de l'inventaire (WGS84 converties) ; écarts de 2 à 4 m constatés avec le levé"),
           lien_description=lien, statut=statut,
           valide_2026={"valeur": True if z is None else "incertain",
                        "raison": "hors zones de travaux 2025 (relief_zones_2026) : arbre présumé conservé" if z is None else "dans la zone %s" % z},
           confiance=conf,
           preuve={"fichier": P + "patrimoine_arbore_gam2023_site.json", "id_metro": t["id"],
                   "distance_arbre_description_m": round(cand[0], 2) if cand else None})

with open(chemin(W + "/obs_web.json"), "w", encoding="utf-8") as f:
    json.dump(obs, f, ensure_ascii=False, indent=1)
print(len(obs), "observations ->", W + "/obs_web.json")
import collections
print(collections.Counter(o["statut"] for o in obs))
