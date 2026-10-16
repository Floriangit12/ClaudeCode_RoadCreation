
---

## 8. Marquage au sol coté (IISR 7e partie)
Dossier : [`08_Marquages_Geometrie_IISR7/`](08_Marquages_Geometrie_IISR7)

| Fichier | Contenu |
|---|---|
| [`MARQUAGES_IISR7_COMPLET.md`](08_Marquages_Geometrie_IISR7/MARQUAGES_IISR7_COMPLET.md) | Référence complète et cotée du marquage : unité u, modulations, choix des lignes (tableau 113-2), section courante, points singuliers (Δ, L), flèches directionnelles (une seule taille de 4,00 m, × 4/3, × ½) et de rabattement, STOP, cédez, lignes d'effet, guidage en carrefour, zone centrale, hachures et chevrons, giratoires, passages piétons (formule de répartition), cycles, stationnement, TC (zigzag), inscriptions, ralentisseurs ; incohérences de l'IISR ; erreurs des documents existants. |
| [`marquages_iisr7.json`](08_Marquages_Geometrie_IISR7/marquages_iisr7.json) | 195 règles, 42 gabarits polygonaux (flèches, triangles, figurine vélo, PMR, IRVE, MRE, zigzag…), 72 glyphes vectorisés, 15 motifs paramétriques, 22 pratiques locales (Paris, Nantes, Lyon), paramètres par défaut. |
| [`gabarits_svg/`](08_Marquages_Geometrie_IISR7/gabarits_svg), [`planches_controle/`](08_Marquages_Geometrie_IISR7/planches_controle), [`outils/`](08_Marquages_Geometrie_IISR7/outils) | 44 SVG cotés + 7 exemples de motifs ; superpositions gabarit / figure de l'IISR ; scripts (`geometrie_gabarits.py` importable dans hython, `verifier_json.py` : 1143 contrôles). |

## 9. Signalisation verticale et feux
Dossier : [`09_Signalisation_Verticale_Feux/`](09_Signalisation_Verticale_Feux)

| Fichier | Contenu |
|---|---|
| [`SIGNALISATION_IMPLANTATION.md`](09_Signalisation_Verticale_Feux/SIGNALISATION_IMPLANTATION.md) + [`signalisation_implantation.json`](09_Signalisation_Verticale_Feux/signalisation_implantation.json) | Gammes et dimensions, supports, dégagement latéral (bord du panneau à 0,70 m), hauteurs (1,00 m en rase campagne, jusqu'à 2,30 m en agglomération éclairée), régimes de priorité (AB1 à AB25), distances des panneaux avancés, prescription, indication, direction, balises, giratoire, algorithme de pose ; 98 règles. |
| [`FEUX_IMPLANTATION.md`](09_Signalisation_Verticale_Feux/FEUX_IMPLANTATION.md) + [`feux.json`](09_Signalisation_Verticale_Feux/feux.json) | Feux R11 à R25 et M12 : ligne d'effet, position (au droit ou à l'aval de la ligne), nombre et côtés par couloir, hauteurs (gabarit 2,00 m, axe < 4,20 m), optiques, R12, durées, supports, algorithme en 9 étapes ; 48 règles. |
| [`schemas/`](09_Signalisation_Verticale_Feux/schemas) | Schémas cotés : STOP, cédez, giratoire, carrefour à feux. |
| Dépôt : `assets/specs/route/panneaux_fr_catalogue.json` | 870 faces de panneaux tirées des 863 PDF officiels (licence présumée Licence Ouverte 2.0, non levée : ne pas diffuser les PNG). |

## 10. Carrefours, îlots, terre-pleins, giratoires, ponts
Dossier : [`10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts)

| Fichier | Contenu |
|---|---|
| [`CONCEPTION_CARREFOURS.md`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/CONCEPTION_CARREFOURS.md) | Choix du type, îlot central et TAG, goutte d'eau (construction ACI pas à pas), îlot directionnel, carrefour à feux et à îlot central, zone de conflit, trajectoires et épures, refuges, signalisation dépendant de la géométrie. |
| [`GIRATOIRES.md`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/GIRATOIRES.md) | Typologie (mini, compact, moyen, grand), îlot central, anneau, déflexion, entrées / sorties (ACI tableau 1), îlots séparateurs (tableau 2), piétons, cycles, signalisation. |
| [`TERRE_PLEINS_SEPARATEURS.md`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/TERRE_PLEINS_SEPARATEURS.md), [`PONTS_OUVRAGES.md`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/PONTS_OUVRAGES.md), [`PROFILS_EN_TRAVERS.md`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/PROFILS_EN_TRAVERS.md) | TPC par contexte, ouvertures, traitements (planté, minéral, peint, franchissable) ; ponts (profil, trottoirs, garde-corps, joints, gabarits, épaisseur de tablier) ; largeurs de voies, voies de TAG, rayons, surlargeurs, dévers, ralentisseurs, visibilité. |
| [`regles_geometrie_voirie.json`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/regles_geometrie_voirie.json), épures `EPURE_*.svg` | 174 règles ; trois épures cotées (croix à îlots, giratoire urbain, ouverture de TPC). |
| [`sources/`](10_Carrefours_Ilots_TerrePleins_Giratoires_Ponts/sources) | 39 guides téléchargés (ACI, ARP, Carrefours urbains, Voirie urbaine, carrefours à feux, VSA 70, ICTAVRU, ponts, garde-corps, mini-giratoires…) et `SOURCES.md`. |

## 11. Cycles, piétons, accessibilité, transports collectifs
Dossier : [`11_Cycles_Pietons_Accessibilite_TC/`](11_Cycles_Pietons_Accessibilite_TC)

| Fichier | Contenu |
|---|---|
| [`README.md`](11_Cycles_Pietons_Accessibilite_TC/README.md) | Contenu, mode d'emploi, contrôles, erreurs relevées, lacunes. |
| [`CYCLES.md`](11_Cycles_Pietons_Accessibilite_TC/CYCLES.md) | Choix de l'aménagement, pistes, séparateurs, bandes, voies vertes, double-sens, chaucidou, vélorue, sas, M12, traversées, giratoires, **Chronovélo**, stationnement vélo, Isère. |
| [`PIETONS_ACCESSIBILITE.md`](11_Cycles_Pietons_Accessibilite_TC/PIETONS_ACCESSIBILITE.md), [`TRANSPORTS_COMMUN_STATIONNEMENT.md`](11_Cycles_Pietons_Accessibilite_TC/TRANSPORTS_COMMUN_STATIONNEMENT.md) | Cheminement 1,40 m, obstacles (abaque 2012), abaissés, BEV (0,5875 m à 0,50 m du nez), passages, refuges, ralentisseurs ; quais bus, zigzag, couloirs, stationnement. |
| [`regles_modes_actifs.json`](11_Cycles_Pietons_Accessibilite_TC/regles_modes_actifs.json), [`profils/`](11_Cycles_Pietons_Accessibilite_TC/profils) | 189 règles et 3 chaînes d'application (passage piéton, voie cyclable, arrêt de bus OSM) ; 4 profils en travers cotés. |

## 12. Modèle de voie, inférence OSM, architecture du générateur
Dossier : [`12_Modele_Voie_OSM_Generateurs/`](12_Modele_Voie_OSM_Generateurs)

| Fichier | Contenu |
|---|---|
| [`ETAT_DE_L_ART_GENERATEURS.md`](12_Modele_Voie_OSM_Generateurs/ETAT_DE_L_ART_GENERATEURS.md) | MetaRoad, City Sample (documentation publique), SideFX Labs, osm2streets / osm2lanes, OpenDRIVE 1.8.1, CityEngine, RoadRunner, CARLA ; vérification des dossiers 04 et 05 (24 erreurs). |
| [`MODELE_VOIE_ROUTE_CARREFOUR.md`](12_Modele_Voie_OSM_Generateurs/MODELE_VOIE_ROUTE_CARREFOUR.md) + [`modele_voie.schema.json`](12_Modele_Voie_OSM_Generateurs/modele_voie.schema.json) | Modèle de données du générateur : routes, profils (bandes et limites), objets le long des voies, carrefours (branches, frontière, zone de conflit, trajectoires, conflits), îlots et terre-pleins, ouvrages, signaux, graphe de voies (ZoneGraph) ; correspondances OpenDRIVE et MetaRoad. |
| [`INFERENCE_OSM_VERS_PROFIL.md`](12_Modele_Voie_OSM_Generateurs/INFERENCE_OSM_VERS_PROFIL.md) + [`inference_osm_profil.json`](12_Modele_Voie_OSM_Generateurs/inference_osm_profil.json) | 80 règles de passage des tags OSM au profil, aux carrefours et à la signalisation, avec défauts français sourcés et pièges. |
| [`ARCHITECTURE_GENERATEUR_HOUDINI.md`](12_Modele_Voie_OSM_Generateurs/ARCHITECTURE_GENERATEUR_HOUDINI.md), [`exemples/`](12_Modele_Voie_OSM_Generateurs/exemples), [`outils/valider_modele.py`](12_Modele_Voie_OSM_Generateurs/outils/valider_modele.py) | Chaîne de 15 HDA `rg::*` branchée en amont des HDA `pj::*` du dépôt, solveur de carrefours en 10 étapes, exports USD / OpenDRIVE / graphe ; deux exemples valides ; validateur. |

## 13. Observations d'aménagements réels en Isère (Panoramax, ortho IGN)
Dossier : [`13_Observations_Panoramax_Isere/`](13_Observations_Panoramax_Isere)

| Fichier | Contenu |
|---|---|
| [`OBSERVATIONS_ISERE.md`](13_Observations_Panoramax_Isere/OBSERVATIONS_ISERE.md) | 72 sites (Meylan 34, métropole 27, reste de l'Isère 11), 108 photos regardées en tuiles natives, 284 constats, comparaison avec l'IISR (56 conformes, 11 différents). |
| [`regles_pratiques_locales.json`](13_Observations_Panoramax_Isere/regles_pratiques_locales.json), [`observations.json`](13_Observations_Panoramax_Isere/observations.json), [`carte/`](13_Observations_Panoramax_Isere/carte) | 40 règles de pratique locale observée (nombre d'exemples calculé) ; observations structurées ; carte des sites. |
| `photos_tiers_locales/` | photos Panoramax (CC-BY-SA / Etalab) **locales, jamais diffusées ni versionnées**. |

## 14. Bibliothèque d'assets de la route française (static meshes, matériaux)
Dossier : [`14_Assets_Route_Statics/`](14_Assets_Route_Statics)

| Fichier | Contenu |
|---|---|
| [`ASSETS_ROUTE.md`](14_Assets_Route_Statics/ASSETS_ROUTE.md) | 120 static meshes paramétriques (bordures, caniveaux, supports, feux, garde-corps, potelets, pavés, dalles, BEV) fabriqués par 6 HDA `route::*`, 33 profils lus sur les dessins cotés, contrôle par la masse, 27 matériaux PBR CC0, rendus de contrôle, erreurs relevées. |
| [`regles_assets_route.json`](14_Assets_Route_Statics/regles_assets_route.json), [`controle/`](14_Assets_Route_Statics/controle) | 55 règles de cotes ; planches de rendu Karma. |
| Dépôt : `assets/specs/route/catalogue_assets_route.json`, `assets/lib/route_fr/` | catalogue versionné ; meshes et matériaux (non versionnés). |
