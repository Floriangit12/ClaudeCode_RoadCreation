# Générateur procédural de routes françaises : architecture et plan d'implémentation

*`recon/generateur/PLAN_GENERATEUR.md` — 16/10/2026, corrigé le 17/10/2026 après la relecture adverse
(`D:\DocRoute\15_Relecture_Adverse`, corrections listées dans `D:\DocRoute\00_ERRATA_DOCUMENTS_EXISTANTS.md` § 10).
Plan de construction du générateur Houdini 22 (Indie) → USD (Unreal 5.8.3), OpenDRIVE (simulation ADAS, CARLA) et
graphe de voies (ZoneGraph), à partir de données de type OSM ou d'une scène décrite par Claude. Il reprend
l'architecture du dossier `D:\DocRoute\12_Modele_Voie_OSM_Generateurs\ARCHITECTURE_GENERATEUR_HOUDINI.md` (« 12A ») et
la complète par les règles fusionnées (`assets/specs/route/regles_route_fr.json`), les scènes de test, les critères
mesurables et la validation visuelle.*

## 0. Pourquoi ce générateur, et ce qui change

La reconstruction actuelle du site part de relevés et d'images, élément par élément ; l'utilisateur la juge « toujours
très mal faite ». Le générateur inverse l'ordre : il sait d'abord **construire une route française juste** à partir
d'une description abstraite (profil de voies, régimes, îlots…) et des règles de conception, comme MetaRoad (une voie
porte ses attributs le long de son abscisse) et City Sample (des données, Houdini fabrique, Unreal assemble et
peuple). Il est mis au point sur six scènes synthétiques ; ensuite seulement, on lui décrit une scène réelle (Meylan).

Ce qui existe et sert tel quel :

| Existant | Où | Usage |
|---|---|---|
| Règles de conception fusionnées (857 règles, 34 paramètres par défaut, 20 arbitrages) | `assets/specs/route/regles_route_fr.json` | toute valeur du générateur vient d'un attribut décrit ou d'une règle nommée `RF-*` / `DEF-*` / `ARB-*` |
| Synthèse humaine des règles | `D:\DocRoute\00_SYNTHESE_CONCEPTION_ROUTES_FR.md` | référence de lecture, renvois aux volets |
| Modèle de données `modele_voie/0.1` (schéma, 2 exemples, validateur C01-C11) | `D:\DocRoute\12_…\modele_voie.schema.json`, `exemples/`, `outils/valider_modele.py` | entrée unique du générateur. Le validateur a été corrigé le 17/10/2026 (il refusait tout identifiant `RF-*` et ne lisait pas `regles_route_fr.json`) ; les 2 exemples citent encore les anciens identifiants (`OSM-LAR-020`, `GA-RAY-001`…) : migration au lot L0 |
| 80 règles d'inférence OSM → modèle | `D:\DocRoute\12_…\inference_osm_profil.json` (= familles `inference_osm` de la base) | étape 0 |
| HDA `pj::*` (lecteur, sol, bordure, caniveau, îlot, 4 HDA de marquage, export USD et points) | `recon/pcg/houdini/hda/` (README_HDA) | réutilisées sans modification en aval, **sauf `pj::symbole_iisr`** qui passe en version 2 au lot L4 (gabarits PMR, IRVE, glyphes du dossier 08, champ `axe_longitudinal` des zigzags) |
| Gabarits et motifs IISR (42 polygones, 72 glyphes, fonctions en Python pur) | `D:\DocRoute\08_…\marquages_iisr7.json`, `outils/geometrie_gabarits.py` | prototypes de symboles, contrôle des motifs |
| 120 static meshes `route_fr` + 27 matériaux CC0 ; 870 faces de panneaux | `assets/specs/route/catalogue_assets_route.json`, `panneaux_fr_catalogue.json`, `assets/lib/route_fr/` | instances (bordures, feux, supports, garde-corps, panneaux) |
| Observations de 72 sites de l'Isère | `D:\DocRoute\13_…\observations.json`, `regles_pratiques_locales.json` | pratiques locales et cas de comparaison visuelle |
| Découpe en tuiles natives | `recon/pcg/vision/decoupe.py` | toute analyse visuelle |

## 1. Contraintes à respecter (héritées du dépôt)

| Contrainte | Conséquence pour le générateur | Source |
|---|---|---|
| Python seulement dans le lecteur, de petits Python SOP d'entrées-sorties, les scripts de construction et le pilote | l'**inférence OSM → modèle** est un script Python hors Houdini ; dans Houdini, toute géométrie passe par SOP / VEX / LOP | `recon/pcg/houdini/hda/README_HDA.md` (préambule) |
| HDA en `.hdalc` développées, signature de construction, une bibliothèque à une définition pour Unreal | même outillage (`commun/pj_hda_outils.py`) pour les HDA `rg::*` | README_HDA § 1 |
| VEX sans `#include "opdef:"` ni `struct` | bibliothèques `commun/vex/*.h` recopiées en tête des wrangles | README_HDA § 1 |
| Repère : L93 / NGF → local O → Houdini `(x, z, −y)` une seule fois ; Houdini → USD Z haut une seule fois | `rg::lire_modele` convertit ; `pj::preparer_export` exporte | README_HDA § 2 |
| Un seul modèle de Z (HeightField `height`, `r0`, `z1`, `r1`, `z2`, `r2`, pas 0,10 m) | `rg::nivellement` produit ce HeightField | README_HDA § 2 ; règle TQ-SOL-013 |
| Contrat de branche : entrée 1 entités, entrée 2 HeightField, entrée 3 contexte ; sortie 1 maillages Y haut, sortie 2 points, sortie 3 prototypes | `rg::vers_entites` sort exactement les ENTITÉS de `pj::lire_description` | README_HDA § 4 |
| Déterminisme : graine = hash(id), JIT VEX coupé en batch, `.usdc` canonisés | contrôle à chaque étape | README_HDA § 9.2 |
| HAPI direct refusé en Indie ; Houdini Engine seulement dans UE | fabrication en batch (hython) ; Unreal lit USD + points | README_HDA § 1, § 9.4 |
| Karma XPU / USD 26 : `DistantLight` sans `inputs:normalize = 1` → éclairage 15 000 fois trop faible | toutes les scènes de rendu de contrôle posent `normalize = 1` | `D:\DocRoute\14_…\ASSETS_ROUTE.md` § 3 |
| Photos de tiers jamais versionnées ; City Sample jamais hors d'Unreal ; Street View interdit | toute tuile ou planche contenant une photo Panoramax ou Mapillary va dans `recon/out/generateur/<scene>/photos_non_versionnees/{tuiles,planches}/` (`CLAUDE.md` l'impose ; `decoupe.py` refuse d'écrire ailleurs les tuiles d'une source dont le chemin contient `panoramax`, `mapillary` ou `photos_non_versionnees`, `controle_tiers` l. 85-90) ; rendus seuls dans `recon/out/generateur/<scene>/rendus/` | `CLAUDE.md` du dépôt ; `recon/pcg/vision/decoupe.py` |
| Specs de l'autre équipe intouchables | compléments dans de nouveaux fichiers (`assets/specs/route/*`) | `CLAUDE.md` |

## 2. Architecture

### 2.1 Chaîne

```
 [0] DÉCRIRE (Python hors Houdini, déterministe)
     OSM (.osm/.pbf) + BD TOPO + contexte ─► recon/generateur/inference/osm_vers_modele.py ─┐
     scène décrite par Claude (même schéma) ───────────────────────────────────────────────┼─► modele_voie.json
     règles : regles_route_fr.json (RF-OSM-*, DEF-*)                                        │   + valider_modele.py (0 erreur)
                                                                                            ▼
 [1] FABRIQUER (hython 22, HDA rg::* puis pj::*)
     rg::lire_modele ─► rg::graphe ─► rg::profils ─► rg::carrefours ─► rg::vers_entites ─► ENTITES ─┐
                                          │                 │               rg::nivellement ─► NIVEAU ─┤
                                          │                 │                                          ▼
                                          │                 │        pj::sol · pj::bordure · pj::caniveau · pj::ilot
                                          │                 │        pj::marquage_ligne · pj::passage_pieton · pj::symbole_iisr · pj::marquage_zone
                                          │                 ├──────► rg::signalisation (panneaux, feux, balises)  ─► points
                                          │                 ├──────► rg::terre_pleins (remplissages, plantations) ─► pj::ilot / points
                                          ├────────────────────────► rg::ouvrages (tablier, piles, garde-corps)   ─► maillages / points
                                          └────────────────────────► rg::vegetation_bati (alignements, zones, bâti) ─► points / zones
     rg::exporter_opendrive ─► .xodr      rg::exporter_graphe ─► graphe_voies.json      pj::preparer_export ─► USD
 [2] PLACER (UE 5.8.3) : import USD, PCG sur points et zones, ZoneGraph depuis graphe_voies.json
 [3] VALIDER : contrôles géométriques, chargement OpenDRIVE, rendus Karma en tuiles comparés à Panoramax (§ 5)
```

Principe tenu partout : **Houdini n'invente rien**. Chaque cote vient d'un attribut du modèle, et chaque attribut
inféré porte sa provenance `prov[<chemin>] = {src: "defaut:DEF-011" | "inference:RF-OSM-CAR-040" | "mesure:…",
regle, conf}` (12M § 1).

### 2.2 Le modèle `modele_voie` (rappel, détail : 12M)

- **Route** : nœuds de début et de fin, catégorie, vitesse, agglomération, ligne de référence (polyligne et
  géométrie régulière droite / arc / clothoïde), **sections** de profil `[s0, s1]`.
- **Profil** : bandes de gauche à droite (31 types : voie, voie bus, bande ou piste cyclable, stationnement,
  trottoir, terre-plein, séparateur, BAU…) avec largeur (constante ou loi de s), niveau (dz, dévers), matériau,
  **objets le long** (à la MetaRoad : figurines, arbres, candélabres, potelets ; mode pas / points / continu,
  exclusions) ; et n + 1 **limites** portant marquages (modulation IISR, largeur en u, phase, interruptions),
  bordure (profil NF, vue, abaissés, caniveau) et séparateur.
- **Carrefour** : branches (régime, ligne d'arrêt, axe d'approche, passage, sas, îlot, coin, flèches), frontière
  (segments `voie` / `joint`, OpenDRIVE 1.8.1 § 12.10), zone de conflit, anneau (giratoire), **trajectoires** voie à
  voie (avec `guidage.materialise`), **conflits**.
- **Îlot / terre-plein** : type (séparateur, directionnel, refuge, central de giratoire, goutte d'eau, TPC, îlot
  peint…), polygone, `terre_plein {franchissable, ceinture, remplissage, plantation, marquage_contour, hachures,
  objets_portes}` : les cinq genres (planté, BRF, gravier, hachuré, franchissable) se décrivent avec ces champs.
- **Ouvrage**, **signal** (code IISR, support, hauteur, applicabilité), **contrôleur** (phases), **objet**, **zone**
  (bâti, espaces verts…), **graphe de voies** (≤ 32 tags, zones spline / polygone).

### 2.3 Les HDA `rg::*` (« route générée »)

| # | HDA | Rôle | Nœuds principaux | Règles principales |
|---|---|---|---|---|
| 1 | `rg::lire_modele` | JSON → géométrie à attributs (routes, nœuds, îlots, ponctuels) ; L93 → Houdini une fois | Python SOP (seul Python géométrique), VEX `pj_repere.h` | — |
| 2 | `rg::graphe` | abscisses, tangentes, courbure ; branches triées par azimut ; échantillonnage adaptatif des géométries régulières à **flèche ≤ 0,5 mm** (écart maximal entre la corde et l'arc ; pour un arc de rayon R, pas = √(8 R × 0,0005), soit 0,63 m pour R = 100 m et 0,20 m pour R = 10 m) | VEX, Resample, Orientation along Curve | RF-OSM-CAR-001 |
| 3 | `rg::profils` | déroule chaque profil : limites décalées (lois de s), rubans de bandes, profils d'extrémité | VEX, Sweep, PolyExpand2D | RF-OSM-PRF-*, RF-OSM-LAR-*, RF-OSM-NIV-*, DEF-002 à DEF-009 |
| 4 | `rg::carrefours` | solveur (§ 2.4) : coins, coupes, frontière, îlots générés, lignes transversales, passages, sas, trajectoires, conflits, guidage, zone de conflit | VEX, Intersection Analysis, Boolean, PolyExpand2D, arcs VEX | familles `carrefour_plan`, `giratoire`, `lignes_transversales` |
| 5 | `rg::vers_entites` | modèle → ENTITÉS au contrat de `pj::lire_description` (bordures + intervalles + abaissés, surfaces, îlots, marquages ML/MP/MF/MS/MZ, ponctuels de sol), identifiants stables dérivés | VEX, Attribute Copy | — |
| 6 | `rg::nivellement` | HeightField unique : profil en long + dévers, trottoirs (vue + dévers), carrefour (grille raccordée), îlots (bombement) | Volume Wrangle, HeightField | DEF-005, DEF-006 ; TQ-SOL-013 |
| 7 | `pj::sol`, `pj::bordure`, `pj::caniveau`, `pj::ilot` | maillages, éléments de bordure, remplissages | existants | GA-*, TQ-SOL-*, TQ-BOR-* |
| 8 | `pj::marquage_ligne`, `pj::passage_pieton`, `pj::symbole_iisr` **v2**, `pj::marquage_zone` | peinture drapée, symboles instanciés (gabarits du dossier 08), hachures, chevrons, zigzags, damiers | existants, sauf `pj::symbole_iisr` v2 (lot L4, ci-dessous) : gabarits PMR, IRVE, 72 glyphes du dossier 08, lecture de `axe_longitudinal` (les zigzags ont x le long de la bordure, les autres gabarits y dans le sens de circulation) | famille `generalites`, `marquage_longitudinal`, `fleches`… |
| 9 | `rg::signalisation` | panneaux, supports, feux (têtes, répétiteurs, R12, M12, potences), balises : côté, recul, hauteur, orientation, regroupement, refus sur surface circulée ou îlot peint | VEX (projection sur le sol fabriqué) | familles `signalisation_verticale`, `feux` ; DEF-025 à DEF-028 |
| 10 | `rg::terre_pleins` | genre → fabrication (remplissage par `pj::ilot`, hachures par `pj::marquage_zone`, semis de plantations avec plafond de 0,60 m dans les triangles de visibilité) | VEX, Scatter | famille `ilots_terre_pleins` ; DEF-020, DEF-029 |
| 11 | `rg::ouvrages` | tablier (balayage d'une section), corniches, piles, culées, garde-corps et barrières en instances, joints, HeightField abaissé sous l'ouvrage | Sweep, Copy to Points, Boolean, HeightField Mask | famille `pont` ; DEF-033 |
| 12 | `rg::vegetation_bati` | alignements au pas (exclusions : visibilité, passages, abaissés, cheminement), zones vertes en points pour le PCG, bâti simple (extrusion BD TOPO ; Labs Building Generator si Labs 22 installé) | Scatter and Align, VEX | DEF-030 ; RF-OBS-VEG-* |
| 13 | `rg::exporter_opendrive` | **deux exports** : `.xodr` 1.8.1 complet (frontière de carrefour § 12.10, segments `joint` / `voie`) et `.xodr` 1.4 restreint (sans ces éléments) pour CARLA, dont les cartes livrées sont en OpenDRIVE 1.4 (`D:\CARLA_Assets\Maps\OpenDrive\Town01.xodr` : `revMajor="1" revMinor="4"`) | Python SOP (sérialisation) | 12A § 6 |
| 14 | `rg::exporter_graphe` | `graphe_voies.json` pour ZoneGraph et le routage piétons / vélos | Python SOP | 12M § 7 |
| 15 | `pj::preparer_export`, `pj::exporter_points` | USD Z haut, points `pj_points/0.1` | existants | contrat E1-E9 |

### 2.4 Le solveur de carrefours (`rg::carrefours`)

Ordre des opérations (12A § 4, complété par les règles fusionnées) :

1. **Coins** : intersection des limites extérieures de deux branches consécutives ; congé de rayon `coin_droit.rayon_m`
   (DEF-010 : 5 / 8 / 12 m ; 6-8 m aux feux) ou forme à trois centres ; contrôle du balayage du véhicule de projet
   (RF-GV-RAY-005 à -007).
2. **Coupes** des routes là où leur profil complet sort du carrefour ; routes trop courtes absorbées (osm2streets).
3. **Frontière** fermée, segments `joint` et `voie` dans le sens trigonométrique.
4. **Îlots** décrits ou générés par gabarit :
   - goutte d'eau de la voie secondaire, **selon le contexte** : en interurbain (régimes STOP / cédez), construction
     ACI tableau 8 (H = 4 l, B = 2 l, b1 = 0,55 l, b2 = 1,45 l, pointe à 1 m, saillie à 0,50 m de l'enveloppe peinte,
     retrait de 1,50 m sur la rive ; RF-GV-ILO-001 à -004) ; en agglomération, îlot urbain compact (espace roulable
     minimal, VU p. 83 ; CU) ou, à défaut, « [G] gabarit ACI réduit » déclaré comme tel, avec contrôles refuge ≥ 2,00 m
     au droit du passage et traversée ≤ 12 m hors refuge ;
   - îlot central de route principale (déport 1/15, nez 1,60-2,00 m, présignalisation L/2 ; RF-GV-CAR-010 à -016) ;
   - îlot de TAG d'artère à 70 km/h : largeurs VSA70 **entre rives, BDG comprises** ; la partie bordée vaut
     0,60 m de moins (champs `largeur_entre_rives` / `largeur_bordee`, RF-GV-CAR-017) ;
   - îlot directionnel de tourne-à-droite (bord concave, ≥ 5 m², avec J5 : largeur entre rives ≥ gamme + 2 × 0,70,
     soit 1,90 m pour une J5 de 500 et 2,10 m pour une J5 de 700 ; RF-GV-ILO-008, -013 à -015) ;
   - giratoire (anneau, îlot central, bande franchissable, îlots séparateurs ACI tableaux 1 et 2 ; déflexion < 100 m ;
     RF-GV-GIR-003 à -014) ;
   - refuge (2,00 m ; 2,50 m aux feux si la chaussée fait ≥ 12 m ; coupé à niveau au passage ; DEF-022).
5. **Lignes transversales** : cédez / STOP à la limite de la chaussée prioritaire (DEF-012) ; ligne d'effet des feux
   selon ARB-01 (DEF-015) ; sas de 4 m si bande cyclable (DEF-016) ; continue axiale d'approche de 15 m sur double
   sens sans îlot (DEF-013) ; jamais de ligne cédez sur une branche à feux (RF-MQ-CED-03).
6. **Passages piétons** : 2 m en amont de la ligne (2-5 m en giratoire), bandes et marges e = (W − 0,5 n)/(n + 1)
   (DEF-011), interruption des lignes à 0,50 m, abaissés et BEV (DEF-031).
7. **Trajectoires** pour chaque couple (bande entrante, bande sortante) autorisé (`turn:lanes`, restrictions, sens
   uniques) : droite – arc tangent – droite le long des axes de voie, rayon ≥ véhicule de projet (RF-GV-TRJ-006).
8. **Conflits** : intersections deux à deux des trajectoires (croisement, convergence, divergence), trajectoire
   prioritaire déduite des régimes.
9. **Trajectoires matérialisées** seulement si `guidage.materialise` (décrit ou observé, jamais inféré ni généralisé,
   ARB-08) et seulement dans les cas de l'art. 117-1 : T'2 0,10 (TAG à l'indonésienne **avec phase spéciale**,
   baïonnette) ou T'2 0,15 + continue 0,15 à 2u (carrefour complexe à TC), sur le bord intérieur de la trajectoire
   (DEF-021).
10. **Zone de conflit** : polygone entre lignes d'arrêt / d'effet, nez d'îlots et bords de chaussée ; contrôles :
    traversée piétonne ≤ 12 m hors refuge **bloquant** (« incontournable », CF p. 19) ; zone de conflit ≤ 40 m
    **avertissement** seulement (« ne devrait pas dépasser … très difficile à respecter strictement », CF p. 19) ;
    aucun marquage longitudinal dedans sauf guidage, damier TC et trajectoires cyclables (RF-MQ-CAR-02,
    RF-MQ-CAR-04). Les points de conflit sont comptés sur la liste complète des mouvements autorisés, liste rapportée
    avec le nombre (une croix complète sans feux : 16 croisements VL/VL, CU p. 122 ; 32 avec convergences et
    divergences, CU p. 120).

### 2.5 Lien avec les règles : `recon/generateur/regles.py`

Petit module Python (lecture seule de `regles_route_fr.json`) utilisé par l'inférence et par les scripts de
construction des HDA : `regle(id)` (résout aussi les anciens identifiants par `index_alias`), `defaut(DEF-id)`,
`valeur(id, chemin)`. Les HDA ne lisent pas le JSON : les valeurs leur arrivent comme attributs du modèle (avec
`prov`), ou comme paramètres d'HDA dont le défaut est écrit par le script de construction depuis `DEF-*` (et la règle
citée dans l'aide du paramètre).

### 2.6 Arborescence prévue

```
recon/generateur/
  PLAN_GENERATEUR.md                 ce document
  regles.py                          accès aux règles fusionnées (§ 2.5)
  outils/                            fusion et contrôle des règles (fait), mise à jour de l'index DocRoute (fait)
  schema/modele_voie.schema.json     copie versionnée du schéma du dossier 12 (+ valider_modele.py corrigé : motifs
                                     RF-…, DEF-nnn, ARB-nn ; lecture de regles_route_fr.json et de index_alias)
  vehicules/vehicules_projet.json    modèles de véhicules sourcés (lot L3a)
  inference/osm_vers_modele.py       étape 0 ; inference/tests/ (cas de tags et profils attendus)
  scenes_test/A_carrefour_ilots.json … F_regimes.json   six scènes synthétiques (§ 4)
  scenes/meylan_paquet_jardin.json   scène réelle décrite par Claude (§ 6)
  hda/rg_*/construire.py + rg_*.hdalc/   HDA développées (versionnées)
  fabriquer_generateur.py            pilote hython (ou option --modele de recon/pcg/houdini/fabriquer_hda.py)
  validation/                        contrôles (Python) et rapports JSON sans photo (versionnés)
  tmp/                               travail (ignoré : .gitignore local)
recon/out/generateur/<scene>/        sorties lourdes et rendus (non versionnés)
recon/out/generateur/<scene>/photos_non_versionnees/{tuiles,planches}/   tuiles de photos Panoramax et planches
                                     rendu | photo (seul emplacement accepté par CLAUDE.md et par decoupe.py)
```

## 3. Étapes livrables et critères mesurables

Chaque étape se termine par un livrable versionné, un rapport de contrôle (`validation/rapport_<etape>.json`) et, à
partir de L2, des rendus Karma regardés en tuiles natives. Une étape n'est close que si **tous** ses critères passent.

| Lot | Livrable | Critères de réussite (mesurables) | Dépend de |
|---|---|---|---|
| **L0** Inférence OSM → modèle | `inference/osm_vers_modele.py`, `regles.py` ; `schema/` : copie du schéma et de `valider_modele.py` corrigé (motifs `RF-…`, `DEF-\d{3}`, `ARB-\d{2}` ; lecture de `regles_route_fr.json` et résolution par `index_alias`) ; **migration** des identifiants des 2 exemples du dossier 12 (`OSM-LAR-020` → `RF-OSM-LAR-020`, `GA-RAY-001` → règle `RF-*` ou `DEF-*` correspondante) ; ≥ 32 cas de test de tags (rue 1 + 1, sens unique, bandes, pistes séparées, stationnement, `turn:lanes` avec et sans affectation, giratoire, chaussées séparées, `crossing`, `traffic_signals`, `give_way`, `bridge`…), dont **`highway=stop` seul → régime `stop_a_verifier`, ni AB4 ni ligne (ARB-19)** et `highway=stop` + `traffic_sign=FR:AB4` → `stop` | 100 % des cas de test donnent le profil attendu ; `valider_modele.py` (copie corrigée) : 0 erreur sur les 2 exemples migrés et sur les sorties ; chaque valeur posée porte `prov` avec une règle `RF-*`, `DEF-*` ou `ARB-*` existante (contrôle C11) ; un test prouve que C11 rejette un identifiant inconnu (`RF-OSM-LAR-999`) ; deux exécutions donnent des fichiers identiques à l'octet | ce plan |
| **L1** Lecture, graphe, profils | `rg::lire_modele`, `rg::graphe`, `rg::profils` ; scène E (§ 4) en courbes de contrôle | échantillonnage à flèche ≤ 0,5 mm ; écart des limites décalées à la position analytique ≤ 1 mm, **mesuré au milieu des cordes** (droite, arc, clothoïde) ; 0 bande de largeur négative ou nulle, 0 chevauchement ; sections contiguës de 0 à L ; transitions de profil continues (écart ≤ 1 mm) | L0 |
| **L2** Entités et nivellement → sol et bordures | `rg::vers_entites`, `rg::nivellement` ; passage par `pj::sol`, `pj::bordure`, `pj::caniveau` sur la scène E | surfaces étanches (0 arête libre intérieure, jointure entre surfaces ≤ 1 mm) ; vue des bordures = modèle ± 5 mm ; dévers trottoir ≤ 2 % et pente < 5 % hors rampants (A2007) ; rampants d'abaissé ≥ 1,50 m (8 %) ou ≥ 2,40 m (5 %) ; contrôles TQ-SOL-* et TQ-BOR-* du dépôt : 0 échec ; rendu Karma regardé en tuiles | L1 |
| **L3a** Modèles de véhicules | `vehicules/vehicules_projet.json` : VL, bus standard 12 m, bus articulé 18 m, PL porteur, semi-remorque, autocar 15 m ; longueur, largeur, empattements, porte-à-faux, rayons de braquage, chacun avec sa source (CU p. 78 ; VU p. 144 ; CF p. 22 ; N05 p. 4 pour l'autocar de 15,00 × 2,55 m et le semi-remorque ; fiches constructeurs pour les empattements, absents des guides lus) ; module de balayage (enveloppe de caisse le long d'un axe) | 100 % des dimensions sourcées ; balayage d'un virage du cercle homologué reproduit Rext 12,50 / Rint 5,30 (CU p. 78) à ± 0,10 m ; balayage du bus standard reproduit 4,80 / 11,50 (VU p. 144) à ± 0,10 m | L2 |
| **L3** Solveur de carrefours (géométrie) | `rg::carrefours` étapes 1 à 6 ; scènes A (plan) et F | coins tangents (rupture ≤ 0,5°) et rayon = consigne ± 1 cm ; frontière fermée ; lignes cédez à 0 ± 0,05 m de la limite prioritaire, passages à 2,0 ± 0,05 m ; goutte d'eau ACI (interurbain) : pointe à 1,00 ± 0,05 m du bord, saillie à 0,50 ± 0,02 m ; îlot urbain : refuge ≥ 2,00 m au droit du passage ; aucune ligne cédez sur une branche à feux ; contrôle bloquant « traversée > 12 m hors refuge → refuge » ; têtes d'îlots et nez au « premier contact des balayages + 0,30 m » calculés avec les véhicules du lot L3a | L2, L3a |
| **L4** Marquages, trajectoires, graphe | marquages par les HDA `pj::marquage_*` ; **`pj::symbole_iisr` v2** (gabarits PMR, IRVE, glyphes, `axe_longitudinal`) ; trajectoires, conflits, guidage ; `rg::exporter_graphe` ; scène A complète | modulations : période et trait ± 1 cm sur 100 m ; largeurs ± 2 mm ; nombre de bandes de passage = n = floor(W − 0,5) et dans la plage du tableau IISR (100 %) ; interruptions 0,50 ± 0,02 m ; **flèches** : sommets identiques à ceux du gabarit du dossier 08 (± 1 mm), centrées dans la voie à ± 2 cm, orientées à ± 0,5°, pointe de la dernière à 1,50 ± 0,02 m de la ligne, interdistance 20 ± 0,05 m, 3 par voie (2 si voie courte en agglomération) ; symboles v2 : boîte orientée de chaque instance = boîte du gabarit ± 1 mm (zigzags compris) ; hachures à 26,565 ± 0,1° et pas perpendiculaire 1,85 ± 0,01 m ; peinture à +2-3 mm du sol fabriqué (TQ-MQG-005) ; 0 ligne longitudinale dans la zone de conflit hors guidage demandé ; trajectoires de rayon ≥ véhicule de projet (L3a) ; points de conflit comptés et rapportés avec la liste des mouvements ; graphe : chaque voie entrante a ≥ 1 successeur, ≤ 32 tags | L3 |
| **L5** Giratoires et terre-pleins | îlots générés, anneau, bande franchissable ; `rg::terre_pleins` (cinq genres) ; scènes B et C | anneau uniforme ± 1 cm ; déflexion calculée < 100 m sur chaque couple de branches ; îlots séparateurs conformes au tableau 2 de l'ACI (H, B, d, r ± 1 cm ; d = 0 et r = 0,25 si Rg < 15 m) ; refuge ≥ 2,00 m au passage ; TPC : ouverture dont les nez sont au premier contact des balayages (L3a) + 0,30 m ; aucune plantation > 0,60 m dans les triangles de visibilité ; îlot central hors agglomération sans arbre ni obstacle agressif (ACI p. 84). **Par genre** : *planté* — bordure T2 ou I2, terre végétale, arbre seulement si une fosse de 3 × 3 m tient dans l'îlot hors couronne de 2 m ; *BRF* — bordure I2 ou A2, matériau BRF, densité d'arbustes = paramètre ± 10 % ; *gravier* — bordure A2, matériau gravier ou galets ; *hachuré* — contour continue 3u, espace 2u, hachures 0,50 / 1,35 à 26,565 ± 0,1°, aplat sous 0,30 m ; *franchissable* — vue ≤ 0,03 m (couronne) ou ≤ 0,06 m, pente de la bande 4-6 %, matériau contrasté | L3, L3a |
| **L6** Signalisation et feux | `rg::signalisation` + assets du dossier 14 et faces du dossier 09 ; scènes A, B, E, F | 100 % des branches à régime ont leurs panneaux (AB3a + M9c, AB4, AB25, B21-1…) ; **0 AB4 sur une branche `stop_a_verifier`** (ARB-19) ; placement selon ARB-20 : bord de panneau ≥ 0,70 m de la rive, sauf cas « contrainte » signalé dans `prov` ; **0 support dans le cheminement de 1,40 m** ; panneau ou boîtier au-dessus du cheminement à ≥ 2,20 m ; aucun support sur surface circulée, îlot peint ou abaissé ; hauteurs 2,30 / 1,00 m ± 2 cm ; **branches à voies affectées** (voies en amont > voies du mouvement direct) : panneau C24a/b, ou Da30, présent sur 100 % d'entre elles dès qu'il y a des flèches d'affectation (IISR7 p. 23) ; nez d'îlot : J5 1,00 m, prescription 0,60 m [G] contrôlés à ± 0,20 m seulement (valeur de confiance faible, ARB-04) ; feux : R11 à droite de chaque couloir, au droit ou à l'aval de la ligne d'effet, bas ≥ 2,00 m, axe du feu supérieur < 4,20 m, ≤ 2 ensembles juxtaposés, R12 sur le trottoir de destination ; TAG en phase spéciale : voie séparée par un îlot portant ses R11 (sinon R14), R11 et R14 jamais sur le même couloir (IISR6 p. 23) | L3 |
| **L7** OpenDRIVE | `rg::exporter_opendrive` (exports 1.8.1 complet et 1.4 restreint). **Prérequis à installer** (absent au 17/10/2026 : pas de module `carla`, `D:\CARLA_Assets` ne contient que des assets) : CARLA dans une version précise (paquet Windows et API Python `carla` de la même version, sur D:), choisie et notée avec sa date au début du lot ; ou, à défaut, un validateur autonome (libOpenDRIVE, esmini ou ASAM Quality Checker) | export 1.4 : se charge dans CARLA (`client.generate_opendrive_world`) sans erreur ; export 1.8.1 : 0 erreur au validateur autonome ; waypoints continus (pas de saut > 0,1 m) ; nombre de jonctions = nombre de carrefours ; landmarks = signaux du modèle ; largeurs des voies = modèle ± 1 cm | L4 + prérequis |
| **L8** Ouvrages et végétation | `rg::ouvrages`, `rg::vegetation_bati` ; scène D, puis végétation sur A-E | hauteur libre ≥ 4,30 + 0,10 m sous le pont ; garde-corps de hauteur h ∈ [0,90 + 0,005 Hc ; min(1,00 + 0,005 Hc ; 1,20)], défaut min(0,95 + 0,005 Hc ; 1,20) (GC97 p. 16, DEF-033 ; scène D : Hc ≈ 5 m → 0,975 m, bande 0,925-1,025), 1,20 m le long d'une piste cyclable ; pont dalle PSIDA : e = l/28 de la travée principale et rapport travée de rive / travée adjacente ∈ [0,6 ; 0,85] (GPOA p. 212) ; joints aux abouts ; arbres : 0 dans les triangles de visibilité, les passages, les abaissés, le cheminement de 1,40 m et les pistes ; fosses dans une bande plantée ou entre places (DEF-030) ; entraxe 7,5 m ± jitter | L2 |
| **L9** Scène réelle (Meylan) | `scenes/meylan_paquet_jardin.json` décrite par Claude (§ 6) ; fabrication complète ; export UE | voir § 6.3 | L0-L8 |

Contrôle de déterminisme à chaque lot : deux fabrications successives donnent des USD et des points identiques à
l'octet (`--verifier-determinisme`, README_HDA § 9.2).

## 4. Scènes de test synthétiques

Six instances `modele_voie` écrites à la main (valeurs fictives, règles réelles), dans `recon/generateur/scenes_test/`.
Chacune a une liste de contrôles propres en plus des critères du lot.

| Scène | Contenu | Ce qu'elle éprouve | Contrôles propres |
|---|---|---|---|
| **A — carrefour complexe à îlots** | croix entre une artère 2 × 2 voies à 50 km/h avec voies de tourne-à-gauche et une rue 1 + 1 ; régime **feux** à **3 phases** décrit dans le contrôleur : P1 artère, mouvements directs et TAD (piétons parallèles) ; P2 **phase spéciale des TAG de l'artère**, en conflit avec aucun autre mouvement (CF p. 43) ; P3 rue 1 + 1 ; durées DEF-028 (vert ≥ 6 s, jaune 3 s, dégagement à 10 m/s et 1 m/s). Chaque voie de TAG de l'artère est **séparée des voies directes par un îlot qui porte ses R11** (IISR6 art. 110-1 3°, p. 23 ; à défaut seulement, R14) ; dans la phase spéciale, les TAG opposés se croisent à l'indonésienne et leurs **trajectoires sont matérialisées en pointillés T'2 0,10** (IISR7 p. 36) — jamais en cycle à 2 phases (CF p. 40). Sur la rue : îlots séparateurs **urbains compacts** (espace roulable minimal, VU p. 83 ; refuge ≥ 2,00 m au passage), et non la goutte d'eau interurbaine de l'ACI (tableau 8, régimes STOP / cédez) ; à défaut, gabarit ACI réduit déclaré « [G] » avec les mêmes contrôles. Îlot directionnel de tourne-à-droite avec voie directe sur une branche (en cédez, AB3a sur son support, IISR3 art. 42-9) ; sas vélos ; passages avec refuges ; **zone centrale de conflit** calculée | solveur complet, phasage, guidage, zone de conflit, conflits, feux | plan de feux présent et cohérent (3 phases, aucun TAG à l'indonésienne dans une phase partagée avec le direct opposé) ; R11 de chaque phase sur son îlot, **R11 et R14 jamais sur le même couloir** ; guidage seulement sur les trajectoires de la phase spéciale ; aucune autre ligne dans la zone ; surface de zone de conflit, nombre de points de conflit et liste des mouvements rapportés, comparés au décompte combinatoire attendu pour ces mouvements (CU p. 120-122 pour une croix complète : 16 croisements, 32 conflits) ; refuges ≥ 2,00 m ; traversées ≤ 12 m hors refuge (bloquant), zone ≤ 40 m (avertissement). *Variante si le plan de feux ne peut pas comporter de phase spéciale* : baïonnette (guidage T'2 0,10 autorisé) ou TAG classique contourné par la droite, sans guidage |
| **B — giratoire** | giratoire urbain Rg = 20 m, anneau 7 m, 4 branches à gouttes d'eau, couronne franchissable de 1,5 m en pavés, îlot central planté (gazon + arbres), passages à 5 m de la ligne cédez, une branche avec bande cyclable interrompue 20 m avant | géométrie ACI, déflexion, signalisation de giratoire | déflexion < 100 m ; ligne cédez sur chaque entrée ; AB25 ; B21-1 face à chaque entrée ; pas d'AB3a en agglomération par défaut ; couronne sans masque de 2 m |
| **C — chaussées séparées par terre-plein planté avec ouverture** | boulevard 2 × 2 voies, TPC planté de 5 m (gazon + alignement d'arbres), ouverture pour un tourne-à-gauche vers une rue latérale (évidement : TAG 3 m + refuge 2 m), puis TPC hachuré et TPC franchissable | TPC, ouverture, genres de terre-plein | nez par les balayages ; refuge résiduel ≥ 2 m ; arbres hors visibilité ; continue 3u de TPC ; hachures conformes |
| **D — pont** | route 1 + 1 avec trottoirs franchissant une voie 2 × 1 par un pont dalle PSIDA à 3 travées continues **12 + 15 + 12 m** (rapport travée de rive / travée adjacente 0,8, dans [0,6 ; 0,85], GPOA p. 212) ; garde-corps de type S8 ; joints aux abouts | ouvrage, nivellement, sous-ouvrage | hauteur libre ≥ 4,40 m ; épaisseur 15/28 ≈ 0,54 m ; garde-corps à h = 0,95 + 0,005 Hc avec Hc ≈ 4,40 + 0,54 ≈ 5 m, soit 0,975 m (bande 0,925-1,025 m, GC97 p. 16 ; l'asset S8 de 1,00 m y entre), 1,20 m si une piste cyclable passe sur l'ouvrage ; profil courant conservé sur l'ouvrage ; trottoirs ≥ 1,25 m ; terrain abaissé sous l'ouvrage sans trou |
| **E — rue avec piste cyclable et trottoirs** | rue 50 km/h, 1 + 1 voies de 3,00 m ; de chaque côté, de la chaussée vers la façade : stationnement longitudinal de 2,00 m, **bande plantée de 3,00 m** (arbres d'alignement à 7,5 m, fosses de 3,00 × 3,00 m, VU p. 98-100 ; axe des arbres à 1,50 m de la bordure, DEF-030 ; la bande tient aussi lieu de tampon contre les portières, ≥ 0,50 m), piste unidirectionnelle de 2,00 m au niveau intermédiaire, trottoir de 2,00 m ; une traversée piétonne avec **bateaux à rampants latéraux** (parallèles à la bordure : 2 × 1,50 m à 8 % ou 2 × 2,40 m à 5 %) — un rampant perpendiculaire de 1,50 m + le passage horizontal de 0,80 m (2,30 m) ne tient pas dans 2,00 m, et ce passage n'est exigé que « si la largeur du trottoir le permet » (A2007 art. 1, 4°, p. 2) ; abaissés et BEV ; un C20a sur le trottoir de 2,00 m (cas de placement ARB-20) ; un arrêt de bus en alignement (le quai interrompt stationnement et bande plantée) | profil, objets le long, accessibilité, placement des supports, TC | profil exact ; abaissés 1,20 m, BEV 0,5875 m à 0,50 m du nez ; cheminement de 1,40 m continu sur tout le trottoir (0 arbre, 0 support, 0 rampant dedans) ; C20a placé selon ARB-20 (support côté façade, panneau en surplomb à ≥ 2,20 m) ; neutralisation du stationnement 5 m avant le passage ; quai de 14 m à 0,21 m ; zigzag de 30 m ; figurines vélo au pas de 50 m |
| **F — STOP, cédez, feux** | trois carrefours en T : (1) branche en **STOP** confirmé (`traffic_sign=FR:AB4` ou description) avec AB4 et continue d'approche, plus une branche voisine portant seulement `highway=stop` (régime `stop_a_verifier`, ARB-19) ; (2) branche en **cédez** avec îlot séparateur, AB3a + M9c et triangle facultatif ; (3) carrefour à **feux** 1 voie par branche, ligne d'effet peinte à 3 m du passage, R11 + répétiteur, R12, bouton d'appel, M12 sur une branche ; trottoirs de 2,00 m (cas de placement ARB-20 pour l'AB3a, l'AB4 et les mâts de feux) | régimes et signalisation | une seule ligne transversale par branche, du bon type ; **ni AB4 ni ligne sur la branche `stop_a_verifier`**, carrefour signalé « à vérifier » ; panneau au droit de la ligne, bord ≥ 0,70 m sauf cas « contrainte » signalé ; aucun support dans le cheminement de 1,40 m ; pas de continue d'approche sur la branche à îlot ; feu au droit ou à l'aval de la ligne d'effet ; AB4 absent de la branche à feux |

Toutes les scènes sont aussi exportées en OpenDRIVE (L7) et en graphe de voies (L4).

## 5. Validation visuelle : rendus en tuiles natives comparés à des photos Panoramax de cas semblables

Les scènes synthétiques ne reproduisent aucun lieu : on compare donc des **cas semblables** (même typologie, mêmes
éléments), pas des pixels. Les photos sont celles du dossier 13 (déjà téléchargées, `D:\DocRoute\13_…\photos_tiers_locales\`,
locales et jamais diffusées) ; de nouvelles photos peuvent être tirées de Panoramax par l'API publique si un cas manque,
dans le même dossier local.

### 5.1 Cas de comparaison retenus (dossier 13)

| Scène | Sites de comparaison (identifiants du dossier 13) | Ce qu'on compare |
|---|---|---|
| A | M15 (tirets suivant la courbe du TAG ; la ligne droite de tirets du mouvement direct est un écart à l'IISR, à ne pas reproduire), M11 (tirets courts + flèche de TAG), M17 et M27 (îlots refuges, séquence îlot bordé → îlot peint), G05 et I05 (feux, potences), I02 (shunt de tourne-à-droite séparé par un îlot planté) | forme et pas des tirets de guidage ; proportions des îlots ; position des mâts et des lignes d'effet |
| B | M03 (Ø 47 m, couronne pavée rouge + galets), M04 (Ø 29 m), G01 (Ø 55,5 m), I01 (Ø 40 m, B21-1 bas), M02 (Ø 65 m) | proportion îlot / anneau, couronne, B21-1, lignes cédez, végétation de l'îlot |
| C | I11 (TPC engazonné planté 3,5 m, Crolles), G06 (TPC revêtu 2,6 m), M27 (îlots discontinus) | largeur du TPC, plantation, nez, marquage |
| D | M32 (passage supérieur béton), G19 (garde-corps barreaudé, trottoir ~1,5 m), M33 (passerelle) | garde-corps, trottoir, corniche, joints |
| E | M24 (piste unidirectionnelle au niveau du trottoir), G16 (Chronovélo à niveau intermédiaire), G20 (séparateur béton bas), M10 (bande, figurine + double chevron) | séparateurs, niveaux, figurines, BEV |
| F | M19 et M20 (STOP), M22 et G09 (cédez), M14, M16, M18 (feux sur trottoir), M10 (potence) | position et hauteur des panneaux et des feux, lignes |

### 5.2 Protocole

1. **Rendu** Karma XPU de chaque scène : vue du piéton ou du conducteur à 1,5-2,0 m de hauteur (comme la caméra
   Panoramax, hauteur supposée ≈ 2 m dans le dossier 13), **au même champ de vision et au même tangage que la tuile
   de la photo de comparaison** : relire `fov_deg`, `tangage_deg` et `lacet_image_deg` dans le `tuiles.json` de la
   photo (`decoupe.py equirect` règle le champ automatiquement sur la résolution de la source, l. 230-238 : 1092 /
   (W/360°), borné à [40° ; 90°] ; 68,25° pour les photos de 5 760 px du dossier 13, 1 960 tuiles relues dans 149
   manifestes ; jamais 90° par défaut), soleil `normalize = 1`, exposition fixe ; plus une vue orthographique de
   dessus à 5 cm/px. Sorties : `recon/out/generateur/<scene>/rendus/`.
2. **Découpe** de chaque rendu et de chaque photo de comparaison avec `recon/pcg/vision/decoupe.py` (`image` pour les
   rendus, `equirect` ou vues ciblées pour les 360°), tuiles ≤ 1092 × 1092 px, recouvrement ≥ la taille du plus grand
   objet cherché. Aucune conclusion sur une image réduite.
3. **Planches** rendu | photo, un fichier par paire (jamais de planche haute à 6 panneaux), dans
   `recon/out/generateur/<scene>/photos_non_versionnees/planches/` ; tuiles des photos dans
   `recon/out/generateur/<scene>/photos_non_versionnees/tuiles/` (ou laissées dans le dossier du dossier 13) :
   `CLAUDE.md` et `decoupe.py` (`controle_tiers`) refusent tout autre emplacement.
4. **Grille de comparaison** par scène (critères de la scène, § 4) : pour chaque critère, un constat (« conforme »,
   « différent », « absent ») avec l'identifiant de tuile ; pas de photo dans le rapport. Rapport versionné :
   `recon/generateur/validation/comparaison_<scene>.json` (critère, constat, tuiles, règle, identifiant de photo
   Panoramax).
5. **Revue indépendante** (comme `recon/pcg/ARCHITECTURE.md` § 1.7) : un agent qui n'a vu ni le code ni le modèle
   reçoit les paires dans un ordre aléatoire et note de 0 à 3 : géométrie des îlots, marquages, bordures et
   trottoirs, signalisation, végétation, matériaux, lumière. **Seuil : moyenne ≥ 2 et aucun 0** ; l'utilisateur
   valide ensuite.
6. Les écarts deviennent des corrections du générateur ou des règles (avec leur source), jamais des retouches à la
   main d'une scène.

## 6. Étape « description d'une scène réelle » : Meylan

### 6.1 Cible

La cible actuelle du dépôt est l'**état avant travaux** du carrefour Paquet Jardin (avenue de Verdun / avenue du
Vercors / chemin de la Revirée), sorties dans `recon/out/paquet_jardin/v2_avant_travaux/` (`CLAUDE.md` du dépôt). Le
générateur y est appliqué d'abord à l'emprise du site (carré de 300 m), puis à d'autres secteurs de Meylan.

### 6.2 Méthode

1. **Inférence** depuis OSM et BD TOPO (L0) → `modele_voie` brut, avec `prov` « inference » ou « defaut ».
2. **Description par Claude** : Claude complète et corrige le modèle à partir des preuves déjà réunies dans le dépôt
   (levés GAM et PCRS, ortho 5 cm, LiDAR, photos Panoramax et Mapillary d'avant travaux, règles locales
   `regles_locales_meylan.json`, observations du dossier 13) : géométrie régulière des routes, profils mesurés,
   régimes, îlots, trajectoires matérialisées observées, signaux. Chaque valeur porte sa preuve (`prov.src` =
   `mesure:pcrs`, `photo:<id>`, `ortho2022`…). Les valeurs mesurées priment sur les règles ; les règles comblent le
   reste et contrôlent les mesures. Les pratiques locales non conformes à l'IISR (damier, Chronovélo, ocre, anneau
   vert) ne s'appliquent qu'aux éléments ainsi relevés ou photographiés (priorité 1), jamais comme style par défaut ;
   un régime STOP n'est posé que s'il est confirmé (ARB-19).
3. **Fabrication** complète (L1-L8) et export USD, OpenDRIVE, graphe.
4. **Comparaison au réel** : poses Panoramax recalées par PnP (chaîne `recon/pcg/enrichir/`), vues de contrôle aux
   mêmes intrinsèques, planches photo | rendu | arêtes projetées, découpées en tuiles.

### 6.3 Critères

| Critère | Seuil |
|---|---|
| Arêtes de bordure fabriquées / levé (GAM, PCRS) | médiane ≤ 0,05 m, 95e centile ≤ 0,15 m |
| Marquages : correspondance avec les marquages relevés | 100 % des marquages relevés présents ; position ≤ 0,10 m ; 0 marquage inventé sans règle ni preuve |
| Signaux : position des supports relevés | ≤ 0,50 m |
| OpenDRIVE | export 1.4 : chargement CARLA sans erreur (CARLA à installer, lot L7) ; export 1.8.1 : 0 erreur au validateur autonome ; voies continues |
| Reprojection des arêtes sur les photos recalées | erreur moyenne ≤ 8 px à plat (critère de `recon/pcg/ARCHITECTURE.md` § 1.7) |
| Revue indépendante | moyenne ≥ 2, aucun 0, puis validation de l'utilisateur |

## 7. Placement dans Unreal (à la manière de City Sample)

- Import des USD (sol, bordures, marquages, îlots, ouvrages) ; matériaux remappés par `materiau_id`.
- Points d'instances (`pj_points/0.1`) → graphes PCG (`PG_Bordures`, `PG_Symboles`, `PG_Arbres`, `PG_Massifs`,
  `PG_Herbe`…) avec la bibliothèque (`DT_Bibliotheque`), comme prévu dans `recon/pcg/ARCHITECTURE.md` § 1.5.
- **ZoneGraph** : un script Python d'éditeur (`recon/pcg/ue/zonegraph_depuis_graphe.py`, à écrire) crée les
  `ZoneShapeComponent` depuis `graphe_voies.json` (une forme spline par section de profil, une forme polygone par
  carrefour et à chaque changement de profil ; ≤ 32 tags). Ni MetaRoad ni City Sample ne sont nécessaires ; City
  Sample n'est étudié que par sa documentation publique et ne fournit aucun asset hors d'Unreal.

## 8. Risques et parades

| Risque | Parade |
|---|---|
| Carrefours très obliques ou branches très proches (frontière et coins faux) | fusion de carrefours (osm2streets), contrôle « rayon impossible » signalé dans `rg_carrefours_controles`, description explicite par Claude |
| Nivellement des carrefours (marches fausses) | grille raccordée aux branches, contrôle des pentes et des vues ; une seule source de Z |
| Données OSM incomplètes (largeurs, régimes absents) | provenance et confiance par attribut ; carrefour « à vérifier » non peint (RF-OSM-CAR-012) ; `highway=stop` seul → régime `stop_a_verifier`, ni AB4 ni ligne, tant que `traffic_sign=FR:AB4`, une photo, un relevé ou la description ne le confirment pas (ARB-19 ; RF-OSM-CAR-011 ramenée à une confiance faible pour le régime) |
| Règles absentes des textes (distances panneau → ligne, guidage, damier…) | valeurs `DEF-*` et arbitrages documentés, surchargeables par la scène |
| Construction de la goutte d'eau interprétée (confiance faible) ; gabarit ACI interurbain mal adapté à la ville | épure PL au lot L3 ; en agglomération, îlot urbain compact ou gabarit ACI réduit déclaré « [G] » ; paramètres exposés |
| Empattements des véhicules de référence absents des guides | lot **L3a** « modèles de véhicules » (dimensions sourcées, fiches constructeurs) avant toute épure de balayage ; tant qu'il n'est pas fait, les critères « premier contact des balayages + 0,30 m » ne sont pas calculables |
| CARLA non installé (pas de module `carla` ; `D:\CARLA_Assets` ne contient que des assets) ; les cartes CARLA livrées sont en OpenDRIVE 1.4 (`Maps/OpenDrive/Town01.xodr`), les éléments propres à la 1.8.1 ne sont pas garantis | prérequis du lot L7 : installer une version précise de CARLA (paquet Windows + API Python) sur D:, ou valider avec un outil autonome (libOpenDRIVE, esmini, ASAM Quality Checker) ; deux exports (1.4 restreint, 1.8.1 complet) |
| Valeurs de confiance faible prises pour des cibles précises (hauteur au nez d'îlot, retrait des mâts, guidage) | tolérances des critères à la mesure de l'incertitude (± 0,20 m pour une valeur [G] issue de photos), jamais ± 2 cm ; aucune généralisation d'une observation n = 2 |
| Houdini Engine Indie (entrée PCG non scriptable) | fabrication en batch ; UE lit USD et points |
| Licence des faces de panneaux non levée | PNG non diffusés ; confirmation à demander au Cerema avant toute publication |
| SideFX Labs 21 ne se charge pas sous Houdini 22 | ne pas en dépendre ; Labs 22 (préversions publiées) seulement pour le bâti, après accord |

## 9. Décisions à prendre par l'utilisateur

1. Lancer L0-L2 sur la scène E avant tout le reste (recommandé) ou commencer par la scène A.
2. Installer ou non une préversion de SideFX Labs 22 (bâti, lots) ; sans elle, le bâti est une extrusion BD TOPO.
3. Pratiques locales non conformes à l'IISR (traversées cyclables en damier, identité Chronovélo, îlots peints ocre,
   anneau vert) : **pas de style par défaut**, ce qui contredirait l'ordre de priorité (règle réglementaire jamais
   enfreinte, README de `assets/specs/route` § 5 ; synthèse § 0.1) ; elles ne s'appliquent qu'aux éléments relevés
   ou photographiés sur le site (provenance `mesure:` ou `photo:`). Décision à prendre : faut-il un mode « relevé
   partiel » qui étende un style relevé sur un tronçon à tout l'itinéraire (Chronovélo) ?
3 bis. Installer CARLA (version à fixer) sur D: pour le lot L7, ou se contenter d'un validateur OpenDRIVE autonome.
4. Écrire au Cerema pour la licence des PDF de panneaux.
5. Report des corrections dans les specs du dépôt (`marquages_geometrie.json`, `feux.json` ; `bordures_elements.json`
   et `bordures.json` sont à l'autre équipe) : liste dans `D:\DocRoute\00_ERRATA_DOCUMENTS_EXISTANTS.md` § 7.
