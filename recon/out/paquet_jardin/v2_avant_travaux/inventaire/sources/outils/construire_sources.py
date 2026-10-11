#!/usr/bin/env python
"""Assemble sources.json : inventaire chronologique des sources utilisables pour l'état d'avant travaux
(2021 -> 22/06/2025) du carrefour Paquet Jardin, à partir des analyses de ce dossier :
gam_datation.json, lidar_dates.json, osm_comparaison.json, photos_inventaire.json
et du catalogue des orthos (recon/out/paquet_jardin/v2/enrichi/recensement/ortho_recentes/catalogue_orthos.json, 2026-10-10).

Usage : python -I construire_sources.py <racine_depot>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(sys.argv[1]).resolve()
D = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources"


def lire(n):
    return json.loads((D / n).read_text(encoding="utf-8"))


gam, lid, osm, ph = lire("gam_datation.json"), lire("lidar_dates.json"), lire("osm_comparaison.json"), lire("photos_inventaire.json")
pp = ph["par_periode"]


def nph(per, src="total", k="n"):
    return pp.get(per, {}).get(src, {}).get(k, 0)


ETALAB = "Licence Ouverte Etalab 2.0"
S = []


def src(**k):
    S.append(k)


# ------------------------------------------------------------------ imagerie aérienne et satellite
src(id="ign_bdortho_2018", famille="ortho_aerienne", nom="BD ORTHO IGN 2018 (Isère)", fournisseur="IGN", date="2018-08-21",
    precision_date="jour (graphe de mosaïquage WFS ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2016-2020, 9 points du site)",
    resolution="20 cm", couverture_site=1.0, licence=ETALAB, acces="WMS https://data.geopf.fr/wms-r, couche ORTHOIMAGERY.ORTHOPHOTOS2018",
    fichiers_locaux=None, etat="2018 (antérieur à la période cible)", usage="contexte, évolution", dans_periode=False)
src(id="gam_ortho_2018", famille="ortho_aerienne", nom="Ortho GAM 2018 (ref_metro_ortho:ortho_2018)", fournisseur="Grenoble-Alpes Métropole / IGN",
    date="2018-07-02", precision_date="jour (résumé de la couche WMS geoflux)", resolution="25 cm", couverture_site=1.0,
    licence="Licence Ouverte", acces="WMS https://geoflux.grenoblealpesmetropole.fr/geoserver/wms", fichiers_locaux=None,
    etat="2018", usage="contexte", dans_periode=False)
src(id="ign_bdortho_2021", famille="ortho_aerienne", nom="BD ORTHO IGN 2021 (Isère) et doublons (OI.OrthoimageCoverage.HR, ORTHO-ASP_PAC2022, ortho_gam2021)",
    fournisseur="IGN", date="2021-08-13", precision_date="jour (graphe ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2021-2023, 6 points du site)",
    resolution="20 cm", couverture_site=1.0, licence=ETALAB, acces="WMS https://data.geopf.fr/wms-r, ORTHOIMAGERY.ORTHOPHOTOS2021",
    fichiers_locaux=None, etat="été 2021", usage="contrôle 2021 (même été que le LiDAR), végétation feuillée", dans_periode=True)
src(id="pcrs_raster_2022", famille="ortho_aerienne", nom="PCRS image 5 cm Grenoble-Alpes Métropole, campagne grenoble_alpes_2022",
    fournisseur="CRAIG / GAM (partenariat PCRS)", date="2022-05-10", precision_date="jour (index des dalles CRAIG, 9 dalles du site)",
    resolution="5 cm", couverture_site=1.0, licence="Licence Ouverte (Partenariat PCRS sur Grenoble Alpes Métropole – CRAIG – 2022)",
    acces="WebDAV https://drive.opendata.craig.fr/public.php/webdav/ortho/PCRS_5cm/2022/grenoble_alpes/",
    fichiers_locaux="data/sites/paquet_jardin/ortho5cm_2022 ; data/sites/paquet_jardin/marquages", etat="2022 (référence géométrique)",
    usage="géométrie de référence de l'état 2022 : marquages, bordures, revêtements, mobilier au sol", dans_periode=True)
for an, dates, n in (("2022", ["2022-05-29", "2022-06-17"], None), ("2023", ["2023-07-19", "2023-09-02"], None),
                     ("2024", ["2024-07-15", "2024-07-17"], None), ("2025", ["2025-06-25"], None)):
    src(id=f"spot_{an}", famille="ortho_satellite", nom=f"ORTHO-SAT SPOT 6/7 {an}", fournisseur="IGN / Airbus DS (couverture nationale DINAMIS)",
        date=dates, precision_date=("scènes SPOT 6/7 de la couverture nationale couvrant le site (STAC https://api.stac.teledetection.fr, "
                                    "collection dinamis-openspot-6-7) ; la scène retenue dans la mosaïque IGN n'est pas publiée"),
        resolution="1,5 m", couverture_site=1.0, licence=ETALAB, acces=f"WMS https://data.geopf.fr/wms-r, ORTHOIMAGERY.ORTHO-SAT.SPOT.{an}",
        fichiers_locaux=f"data/raw/ortho_recentes/ign_spot_{an}_150cm", etat=an,
        usage="trop grossière pour les marquages ; repère de chantier / bâti" + (" ; 2025-06-25 = 2 jours après le début des travaux" if an == "2025" else ""),
        dans_periode=an != "2025")
src(id="ign_bdortho_2024", famille="ortho_aerienne",
    nom="BD ORTHO IGN 2024 (Isère) RVB et IRC, et doublons (ORTHO-EXPRESS 2024, ORTHO-ASP_PAC2025, CRAIG ortho_2024, HR.ORTHOIMAGERY)",
    fournisseur="IGN", date="2024-08-09", precision_date="jour (graphe ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE, 9 points du site ; "
                                                        "le graphe contient aussi 2024-07-30 et 2024-08-10 en bordure d'emprise)",
    resolution="20 cm", couverture_site=1.0, licence=ETALAB, acces="WMS https://data.geopf.fr/wms-r, ORTHOIMAGERY.ORTHOPHOTOS2024",
    fichiers_locaux="data/raw/ortho_recentes/ign_bdortho_2024_rvb_20cm (recalée à 4 cm sur le PCRS 2022)", etat="été 2024",
    usage="image aérienne la plus récente avant travaux (10,5 mois avant) : contrôle des marquages et du secteur est construit", dans_periode=True)
src(id="pleiades_2025", famille="ortho_satellite", nom="ORTHO-SAT Pléiades 2025", fournisseur="IGN / CNES",
    date=None, date_estimee="fin avril – 22 juin 2025",
    precision_date=("non publiée : couche WMS non interrogeable (LayerNotQueryable), aucun graphe de mosaïquage Pléiades dans le WFS IGN, "
                    "fiche CSW IGNF_ORTHO-SAT sans date d'image (étendue temporelle 2010–2026), catalogue STAC DINAMIS public limité à SPOT ; "
                    "estimation : feuillage complet, carrefour encore dans son état 2024 sans emprise de chantier, secteur est achevé ; "
                    "estimation par les ombres non concluante (toits déversés de 3 à 7 m, ombre et façades confondues à 0,5 m)"),
    resolution="50 cm", couverture_site=1.0, licence=ETALAB, acces="WMS https://data.geopf.fr/wms-r, ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025 (FORMAT=image/png)",
    fichiers_locaux="data/raw/ortho_recentes/ign_pleiades_2025_50cm", etat="printemps 2025 (probable)",
    usage="seule vue aérienne de 2025 : confirmation de l'état d'avant travaux à grande échelle (îlots, zébras, bâti, arbres) ; "
          "insuffisante pour la géométrie fine", dans_periode=True)
src(id="pcrs_raster_2025", famille="ortho_aerienne", nom="PCRS image 5 cm GAM 2025 (RVB + IRC)", fournisseur="CRAIG / GAM",
    date="juin–juillet 2025 (jour non publié)", precision_date="catalogue orthos 2026-10-10", resolution="5 cm", couverture_site=1.0,
    licence="accès restreint (flux RTGE https://tiles.rtge.craig.fr, HTTP 401) ; absent du WebDAV open data (années 2017–2024 seulement)",
    acces=None, fichiers_locaux=None, etat="inconnu : avant ou au tout début des travaux selon le jour du vol",
    usage="non utilisable sans convention ; si le vol est antérieur au 23/06/2025, ce serait la meilleure source de l'état juste avant travaux",
    dans_periode=None)
src(id="ortho_sans_couverture", famille="ortho_aerienne", nom="Couches sans donnée sur le site",
    fournisseur="IGN / CRAIG", date=None,
    precision_date="couverture < 50 % de l'emprise (catalogue_orthos.json)",
    detail=["ORTHOIMAGERY.ORTHOPHOTOS2022 / 2023 (Isère non volée)", "ORTHO-SAT PLEIADES 2022 / 2023 / 2024 / 2026",
            "ORTHO-EXPRESS 2023 / 2025 / RVB-EXPRESS 2026 / IRC-EXPRESS 2023 / 2025 / 2026", "ORTHO-ASP_PAC2024 / 2026", "THR.ORTHOIMAGERY.ORTHOPHOTOS",
            "PCRS.LAMB93", "CRAIG ortho_2022 / 2023 / 2025 (autres départements)", "PVA IGN (pva:image) : dernière mission sur le site P18000282 du 2018-08-21"],
    resolution=None, couverture_site=0.0, licence=None, acces=None, fichiers_locaux=None, etat=None, usage=None, dans_periode=None)

# ------------------------------------------------------------------ altimétrie
src(id="lidar_hd_2021", famille="lidar", nom="LiDAR HD IGN, nuage classé COPC, dalle LHD_FXX_0917_6461 (mission 21LHD6PM)",
    fournisseur="IGN (acquisition Sintegra, RIEGL VQ-780 II-S)",
    date=["2021-08-12", "2021-09-06"],
    precision_date=("temps GPS des points : sur le site, %s du 2021-08-12 (4 lignes 7208–7211, 12:03–12:17 UTC) et %s du 2021-09-06 "
                    "(ligne 7020, 05:11–05:12 UTC) ; cœur ± 80 m : %s / %s ; sol (classe 2) : %s / %s ; 0,3 %% de points à horodatage aberrant"
                    % (lid["parts_par_jour_site"].get("2021-08-12"), lid["parts_par_jour_site"].get("2021-09-06"),
                       lid["parts_par_jour_coeur80"].get("2021-08-12"), lid["parts_par_jour_coeur80"].get("2021-09-06"),
                       lid["parts_par_jour_sol_classe2"].get("2021-08-12"), lid["parts_par_jour_sol_classe2"].get("2021-09-06"))),
    resolution="≈ 24 pts/m² (sol ≈ 12 pts/m²) ; rasters 15 et 25 cm dérivés", couverture_site=1.0, licence=ETALAB,
    acces=lid["source"], fichiers_locaux="data/sites/paquet_jardin/lidar (rasters) ; data/sites/paquet_jardin/avant_travaux/lidar_hd (COPC 151 Mo, non versionné)",
    etat="été 2021 (édition 2025-03-25)", usage="relief, fil d'eau, hauteurs vues des bordures, hauteurs bâti / arbres ; valable 2021–2025 hors secteur est construit",
    dans_periode=True)

# ------------------------------------------------------------------ vecteurs
m = gam["marquages_topo_vs_ortho2022"]["par_zone"]
c = gam["bordures_topo_vs_pcrs2019"]["concordance_pcrs_vers_topo"]
src(id="gam_pcrs_vecteur_2019", famille="vecteur", nom="PCRS vecteur Grenoble-Alpes Métropole (limite_voirie, changement_revetements, accotement, mur, seuil, façade)",
    fournisseur="Grenoble-Alpes Métropole (producteur Geofit)", date="2019", precision_date="attribut date_leve = 2019-01-01 (année du levé) sur 100 % des objets",
    resolution="précision planimétrique 10 cm, altimétrique 20 cm", couverture_site="voirie publique seulement (111 lignes de bordure, 35 changements de revêtement)",
    licence="Licence Ouverte", acces="WFS https://geoflux.grenoblealpesmetropole.fr/geoserver/wfs, d_ref_pcrs_vecteur:*",
    fichiers_locaux="data/sites/paquet_jardin/vector/gam_*_pcrs.geojson ; data/sites/paquet_jardin/avant_travaux/gam_geoflux_2026-10-11",
    etat="2019 (avant travaux ; avant les voies nouvelles du secteur est)",
    usage="bordures de l'état d'avant travaux au cœur (ancienne bretelle SE, contre-allée et quais de Verdun SO)", dans_periode=False)
src(id="gam_leve_topo_meylan_topo_dwg", famille="vecteur",
    nom="Levé topographique GAM « Meylan_Topo.dwg » (PLAN_GLOBAL), couches topo_sol_* ; data/sites/paquet_jardin/etat_2026 en est la reprojection",
    fournisseur="Grenoble-Alpes Métropole", date=None,
    precision_date=("aucun attribut de date ; compilation de plans (Z = 0) ; extraite le 2026-10-06 (commits 42ee3af et b4a8384) ; "
                    "vector/gam_topo_sol_* et etat_2026/* identiques (7 couches, 1 807 objets, écart 0,000 m) ; WFS du 2026-10-11 identique à 97–100 %"),
    resolution="levé de géomètre (cm), Z non renseigné", couverture_site="site entier, domaine public et privé",
    licence="Licence Ouverte", acces="WFS geoflux donnees_referentielles_topo:topo_sol_*",
    fichiers_locaux="data/sites/paquet_jardin/vector/gam_topo_sol_*.geojson = data/sites/paquet_jardin/etat_2026/*_L93.geojson",
    etat="mosaïque de dates : hors zone des travaux ≈ état 2019–2022 ; secteur est mis à jour après 2023 ; zone des travaux = géométrie du projet C1 (2025)",
    preuves=dict(
        marquages_presents_2022_hors_travaux=m.get("hors_travaux|tout", {}).get("part_longueur_presente_2022"),
        marquages_presents_2022_travaux_35_80m=m.get("travaux|35<r<=80", {}).get("part_longueur_presente_2022"),
        concordance_pcrs2019_hors_travaux_35_80m=c.get("hors_travaux|35<r<=80"),
        concordance_pcrs2019_hors_travaux_80_150m=c.get("hors_travaux|80<r<=150"),
        concordance_pcrs2019_zone_travaux=c.get("travaux|tout")),
    usage="hors zone des travaux seulement (bordures, marquages, arbres) ; NE PAS utiliser au cœur pour l'état d'avant travaux",
    dans_periode=None)
cmp_ = osm["comparaisons"]
src(id="osm_2022_05_10", famille="vecteur", nom="OpenStreetMap, état au 2022-05-10 (Overpass attic)", fournisseur="contributeurs OSM",
    date="2022-05-10", precision_date="exacte (historique des versions)", resolution="variable (≈ 1 m)",
    couverture_site=f"{osm['n_elements']['2022-05-10']} éléments ; {cmp_['2022-05-10_vs_2025-06-01']['n_a']} objets tagués des couches routières",
    licence="ODbL", acces='https://overpass-api.de/api/interpreter, [date:"2022-05-10T00:00:00Z"]',
    fichiers_locaux="data/sites/paquet_jardin/avant_travaux/osm_2022-05-10/overpass_2022-05-10T00Z.json",
    etat="2022", usage="topologie, sens, voies, arrêts, feux au jour du PCRS 2022", dans_periode=True)
src(id="osm_2025_06_01", famille="vecteur", nom="OpenStreetMap, état au 2025-06-01 (et au 2025-06-22T22Z)", fournisseur="contributeurs OSM",
    date="2025-06-01", precision_date="exacte", resolution="variable (≈ 1 m)",
    couverture_site=(f"{osm['n_elements']['2025-06-01']} éléments ; {cmp_['2025-06-01_vs_actuel']['n_a']} objets tagués ; "
                     f"au 2025-06-22 : {cmp_['2025-06-01_vs_2025-06-22']['n_b']} objets (+{cmp_['2025-06-01_vs_2025-06-22']['n_ajoutes']} lampadaires)"),
    licence="ODbL", acces='https://overpass-api.de/api/interpreter, [date:"2025-06-01T00:00:00Z"]',
    fichiers_locaux=("data/sites/paquet_jardin/avant_travaux/osm_2025-06-01/*.json (brut) ; "
                     "recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources/osm_2025-06-01/osm_*.geojson (couches)"),
    etat="juste avant travaux (137 des 214 objets édités entre 2024-08 et 2025-05)",
    usage="topologie et attributs juste avant travaux : bretelle SE, contre-allée, quais La Revirée, traversées à feux",
    ecarts_avec_actuel={k: cmp_["2025-06-01_vs_actuel"][k] for k in cmp_["2025-06-01_vs_actuel"] if k.startswith("n_")},
    dans_periode=True)
src(id="bdtopo_editions", famille="vecteur", nom="BD TOPO IGN, éditions trimestrielles D038 (2021-03-15, 2022-03-15, 2023-03-15, 2024-03-15, 2025-03-15)",
    fournisseur="IGN", date=["2022-03-15", "2025-03-15"], precision_date="date d'édition (pas de levé)", resolution="métrique (1,5–2,5 m)",
    couverture_site=1.0, licence=ETALAB, acces="https://data.geopf.fr/telechargement/resource/BDTOPO (GPKG D038, 472 Mo pour 2025-03-15)",
    fichiers_locaux=None, etat="éditions avant travaux (la BD TOPO du dépôt est postérieure : tronçons modifiés de 2025-08 à 2026-06)",
    usage="contrôle des tronçons, bâtiments, haies (non téléchargée)", dans_periode=True)
src(id="gam_canopee_cosia", famille="vecteur", nom="Canopée GAM (COSIA) 2018 / 2021 / 2024 et évolutions 18-24, 21-24", fournisseur="Grenoble-Alpes Métropole",
    date=["2018", "2021", "2024"], precision_date="millésime de l'ortho source", resolution="polygones de houppiers (m²)", couverture_site=1.0,
    licence="Licence Ouverte", acces="WFS geoflux indice_canopee_public_opendata:*",
    fichiers_locaux="data/sites/paquet_jardin/avant_travaux/gam_geoflux_2026-10-11/indice_canopee_*.geojson",
    etat="2021 et 2024", usage="emprise des houppiers avant travaux (arbres abattus / plantés)", dans_periode=True)
src(id="gam_arretes_travaux", famille="document", nom="Arrêtés de travaux de voirie GAM (open data)", fournisseur="Grenoble-Alpes Métropole",
    date=["2014-01-20", "2022-06-06"], precision_date="le jeu s'arrête en juin 2022", resolution=None, couverture_site="16 arrêtés à ± 180 m (2019–2022)",
    licence="Licence Ouverte", acces="https://data.metropolegrenoble.fr (arretes_de_travaux_metropole_epsg4326.csv)",
    fichiers_locaux="data/context/arretes_travaux_metropole.csv", etat="2019–2022",
    usage="âge des enrobés (réfection de chaussée COLAS mars–avril 2019 sur Verdun SO et NE)", dans_periode=False)

# ------------------------------------------------------------------ photos de rue
for per, nom, jours in (("2022", "Mapillary 2022", "2022-03-05 (Vercors), 2022-06-10 (Verdun NE, centre, Verdun SO), 2022-11-03 (Revirée, parkings)"),
                        ("2023", "Panoramax + Mapillary 2023 (mêmes prises de vue)", "2023-03-18 (Verdun NE → SO, centre)"),
                        ("2024", "Mapillary + Panoramax 2024", "2024-02-24 (parkings NO, Revirée), 2024-05-01 (360°, Verdun, centre), 2024-08-24 (360°, Verdun, secteur est, Vercors)"),
                        ("2025-S1", "Panoramax + Mapillary 2025, 1er semestre", "2025-01-12 (360°, Vercors), 2025-05-18 (360°, Verdun NE → SO, centre)")):
    t = pp.get(per, {}).get("total", {})
    src(id=f"photos_{per}", famille="photos_rue", nom=nom, fournisseur="Panoramax (api.panoramax.xyz) / Mapillary (graph.mapillary.com)",
        date=jours, precision_date="horodatage EXIF (Mapillary et Panoramax diffèrent parfois d'une heure entière : fuseau)",
        resolution="perspective 2048 px (vignettes Mapillary) à 360° 5760 × 2880",
        couverture_site=dict(photos=t.get("n"), uniques=t.get("uniques"),
                             par_secteur={k.split(":")[1]: v for k, v in t.items() if k.startswith("uniques_sect:")},
                             coeur80=t.get("uniques_coeur80"), voient_le_centre=t.get("uniques_voit_centre"),
                             posees=t.get("posees"), poses_acceptees=t.get("poses_acceptees")),
        licence="CC-BY-SA 4.0 (photos de tiers : jamais versionnées)", acces=None,
        fichiers_locaux="data/raw/panoramax/paquet_jardin ; data/raw/mapillary/paquet_jardin",
        etat=per, usage="aspect (matériaux, usure, mobilier, végétation) et validation des poses", dans_periode=True)

# ------------------------------------------------------------------ documents
src(id="doc_panneau_carrefour", famille="document", nom="Panneau « Aménagement carrefour Verdun/Vercors » (meylan.fr, PDF du 2025-04-03)",
    fournisseur="Ville de Meylan", date="2025-04-03", precision_date="date de création du PDF", resolution="plan géoréférencé à 4 cm (RMSE 3 cm)",
    couverture_site="carrefour + Verdun SO jusqu'à u ≈ −114 m", licence="document public", acces="https://www.meylan.fr",
    fichiers_locaux="data/raw/docs_web/meylan_fr/Panneau-Amenagement-carrefour-Verdun-Vercors.pdf ; data/sites/paquet_jardin/plan_projet_2025",
    etat="fond = ortho PCRS 2022 (état existant) ; dessin = projet", usage="délimite la zone transformée par les travaux", dans_periode=True)
src(id="doc_reunion_2025_04_03", famille="document", nom="Présentation de la réunion publique du 3 avril 2025 (phase 2 Vercors–Granier)",
    fournisseur="Ville de Meylan / GAM / SMMAG", date="2025-04-02", precision_date="PDF", resolution=None, couverture_site=None,
    licence="document public", acces="https://www.meylan.fr", fichiers_locaux="data/raw/docs_web/meylan_fr/presentation-reunion-C1-03-04-25.pdf",
    etat="planning : avenue du Vercors par secteurs d'avril à novembre 2025 ; carrefour Verdun/Vercors de juillet à octobre 2025",
    usage="borne la validité de l'état « avant travaux » : sur l'avenue du Vercors, des travaux ont pu commencer dès avril 2025", dans_periode=True)
src(id="doc_reunion_2024_05_14", famille="document", nom="Présentation de la réunion publique du 14 mai 2024", fournisseur="Ville de Meylan",
    date="2024-05-14", precision_date="PDF", resolution=None, couverture_site=None, licence="document public", acces="https://www.meylan.fr",
    fichiers_locaux="data/raw/docs_web/meylan_fr/Presentation-reunion-publique-14-05-24.pdf",
    etat="historique : décision de décembre 2022, études 2023 ; début prévisionnel du carrefour Verdun/Vercors à l'été 2025",
    usage="aucune description de l'existant du carrefour Verdun/Vercors (la « situation existante » décrite concerne Granier/Taillefer)", dans_periode=True)

res = dict(
    schema="inventaire_sources_avant_travaux/0.1", genere="outils/construire_sources.py", date="2026-10-11",
    site=dict(id="paquet_jardin", origine_l93=[917279.43, 6460289.98], z0_ngf=216.30, emprise="carré ± 150 m", coeur="carré ± 80 m",
              repere="local = L93 − O ; z = NGF − 216,30 ; UE : X = x·100, Y = −y·100, Z = z·100"),
    periode_cible=dict(debut="2021-01-01", fin="2025-06-22"),
    travaux=dict(carrefour=["2025-06-23", "2025-12-05"], trottoirs_vercors_fin="2026-01-30",
                 avenue_vercors_planning="avril à novembre 2025, par secteurs (réunion publique du 3 avril 2025)",
                 secteur_est="constructions 2023–2024 (chantier sur le PCRS 2022, achevé sur l'IGN 2024 et Pléiades 2025)"),
    sources=S,
    conclusions=dict(
        etat_juste_avant_travaux_printemps_2025=[
            "photos 2025-05-18 (Panoramax = Mapillary, 24 vues 360° de Verdun NE → SO, 5 au centre) : seule preuve photographique du cœur au printemps 2025",
            "photos 2025-01-12 (Panoramax, 12 vues 360° de l'avenue du Vercors) : seule preuve du Vercors en 2025 (hiver)",
            "OSM au 2025-06-01 / 2025-06-22 (topologie, arrêts, feux, traversées) : récemment mis à jour (137 des 214 objets, 64 %, ont leur dernière version entre août 2024 et mai 2025)",
            "Pléiades 2025 (50 cm, date probable fin avril – juin 2025) : confirme l'absence de chantier au cœur",
            "BD ORTHO IGN 2024-08-09 (20 cm) : image aérienne détaillée la plus proche (10,5 mois avant les travaux), à compléter par les photos 2025",
            "BD TOPO édition 2025-03-15 (non téléchargée)",
            "levé topo GAM uniquement hors zone des travaux",
        ],
        etat_2022=[
            "PCRS image 5 cm du 2022-05-10 (référence géométrique)",
            "PCRS vecteur (levé 2019) pour les bordures de la voirie publique",
            "LiDAR HD 2021-08-12 / 2021-09-06 pour le relief et les hauteurs de bordures",
            "OSM au 2022-05-10",
            "Mapillary 2022-06-10 (37 photos dont 7 au centre) et 2022-03-05 (11, Vercors) ; 2023-03-18 (35) comme complément proche",
            "BD ORTHO 2021-08-13 (20 cm) en contrôle",
        ],
        non_utilisables=["levé topo GAM au cœur (géométrie du projet C1)", "PCRS image 2025 (accès restreint)", "Street View (licence)",
                         "SPOT (1,5 m)", "orthos 2022/2023 IGN, Pléiades 2022–2024, ortho-express 2025 (pas de données sur le site)"],
    ),
)
(D / "sources.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(S), "sources")
