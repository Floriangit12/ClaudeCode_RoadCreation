# recon/pcg : description sémantique v2 (« Claude décrit, Houdini fabrique, UE 5.8 place »)

La v2 remplace la scène v1 (faces de bordure verticales, marquages vectorisés depuis le raster,
couleurs à plat) par une **description vectorielle paramétrique** : chaque bordure, surface, îlot ou
ponctuel est décrit par des attributs sourcés, et la géométrie n'est fabriquée qu'ensuite, de façon
déterministe, par Houdini (HDA `pj_*`), puis placée dans Unreal 5.8 par PCG. Ce dossier contient le
schéma, les convertisseurs et la zone pilote de la phase 1 (architecture : `architecture_v2.md`).

```
recon/pcg/
  README.md                       ce fichier
  zone_pilote.geojson             emprise de la zone pilote ZP-01 (L93) + justification
  schema/
    description_scene_v2.schema.json   JSON Schema 2020-12, version description_scene_v2/0.1
    materiaux_description.json         materiau_id autorisés -> librairie CC0 (assets/lib/materiaux)
  decrire/                        convertisseurs (Python 3.11 + numpy + Pillow + pyproj, sans shapely)
    commun.py      repère (fonction unique `repere`), GeoJSON déterministe, MNT 2026, géométrie
    contexte.py    lecture des données du dépôt (paquet v1, GAM, OSM, constats) en repère local
    bordures.py    famille bordures (+ candidats BEV)
    surfaces.py    famille surfaces
    ilots.py       famille ilots (+ bordures synthétiques de fermeture)
    composer.py    enchaîne tout, écrit les couches et le manifeste, lance la validation
    valider.py     validateur JSON Schema minimal + contrôles géométriques et de cohérence
    apercu.py      planche PNG de contrôle sur l'ortho 2022
recon/out/paquet_jardin/v2/description/
  description_scene_v2.json       manifeste (site, O, date 2026-10, saison, références sha256,
                                  couches, comptes, statistiques, preuves, a priori, règles PCG)
  base/bordures.geojson  base/surfaces.geojson  base/ilots.geojson  base/ponctuels_sol.geojson
```

Les couches `enrichi/` (Panoramax, vérifiées deux fois) et `arbitre/` viendront s'empiler sur
`base/` (priorité arbitré > enrichi > base) sans changer le schéma.

## Repère et conventions

- **Fichiers** : Lambert-93 (EPSG:2154), altitudes NGF-IGN69, mètres. Coordonnées arrondies au mm.
- **Repère local** (Houdini, USD, points PCG) : `local = L93 − O`, `O = (917279.43, 6460289.98)`,
  `z = NGF − 216.30` ; X est, Y nord, Z haut. Unreal : `X = x·100, Y = −y·100, Z = z·100`, `yaw_UE = −yaw`.
  Une seule conversion : `decrire/commun.py: repere(pts, "local" | "l93")`.
- **Z** : toujours le MNT « sol nu octobre 2026 » (`donnees/relief/heightmap_3025_10cm.png` + `.json`)
  ou les mesures de bordure, **jamais les maillages v1** (jusqu'à +1,77 m au-dessus du MNT sur les
  classes 2025).
- **Identifiants stables** : `K-<ligne GAM>[a-z]` (bordures ; `K-…z` et `K-9…` = bordures ajoutées),
  `S-<surface v1>[a-z]`, `I-<anneau ou surface v1>`, `A-<bordure>-<n>` (abaissés), `BEV-<abaissé>`.
- **Provenance** : chaque entité porte `prov {attribut: {src, ref, conf}}` ;
  `src` ∈ `gam | pcrs2019 | lidar2021 | xodr | ortho2022 | plan2025 | terrain2026 | photo_utilisateur |
  panoramax:<id8>/<tuile> | constat:<id> | norme:<réf> | a_priori:<règle> | osm[:node/<n>] | regle:<spec>`,
  `conf` ∈ `haute | moyenne | faible`. Le manifeste indexe les preuves citées et liste chaque règle
  a priori avec les entités concernées : ce qui n'est pas observé reste visible comme tel.
- **Déterminisme** : pas d'horodatage, entités triées par id, une entité par ligne ; deux exécutions
  donnent des fichiers identiques à l'octet (`hash_description` = sha256 des quatre couches).

## Familles (schéma 0.1)

**bordures** : `LineString` 3D de l'**arête avant** (u = 0 des contours de `assets/specs/bordures.json`),
Z des sommets = **fil d'eau** NGF (MNT 2026 à 0,30 m devant la face). Toutes les bordures sont orientées
**côté haut à gauche, face vue à droite**.
- double arête GAM dédoublonnée (traits parallèles à 0,10 m, 0,15 m aux Saules Blancs ; on garde le côté bas) ;
- `intervalles [{s0, s1, profil, vue_m, vue_m_fin?, role}]` : partition exacte de `[0, longueur_m]` ;
  `role` = `courant | bateau | chartiere` (vue linéaire de `vue_m` à `vue_m_fin`) ; profils NF par
  `regles_affectation` (h_vue lissée sur 7 m, changements de moins de 5 m fusionnés) ;
- `abaisses [{id, type: traversee|charretiere, s0, s1, vue_m, profil, raccords, bev, sources}]` :
  traversée à 0,02 m (arrêté du 15/01/2007), charretière 0,02-0,04 m, chartières de 1 m, largeur ≥ 1,20 m,
  extrémités recalées sur les blocs CHARTIERE GAM ; une bordure n'est abaissée que si elle coupe la marche ;
- `materiau` (`beton_gris` existant, `beton_clair` posé après 2021 ou constat), `aspect`
  (épaufrures, mousse et herbe des joints, salissure), `element_m: auto` (1,00 m si R ≥ 12 m,
  0,50 m sinon, pièces courbes sous 3 m : voir `courbes`), `joint_mm: 6`, `caniveau` (CS2 si ligne GAM).

**surfaces** : polygones v1 découpés par la zone, `classe`, `revetement {materiau_id, age, salissure,
appareillage…}`, `niveau {z_med_ngf, devers_pct, dz_bordure_m, dz_fil_eau_m, arasement}` (MNT 2026),
`bords [{bordure, cote: arriere|avant}]`, `ilots`, `limite_raster` (limite v1 issue d'un raster : à
recaler sur l'arête arrière des bordures à la fabrication). Les îlots priment sur les surfaces qu'ils
recouvrent.

**ilots** : polygone = anneau de l'arête avant de la ceinture (anneau GAM fermé, ou polygone v1 recalé
sur les bordures). `remplissage {materiau_id, epaisseur_m, retrait_sous_bordure_m, retrait_bordure_m,
granulometrie_mm, bombement_m, debordement}` : le remplissage commence à `retrait_bordure_m` (largeur
du profil) à l'intérieur et affleure `retrait_sous_bordure_m` sous le dessus de bordure (BRF 0,04 m,
gravier 0,03 m). `ceinture` (bordures), `nez {rayon_m, position, peint}`, `objets_portes`, `plantation`.

**ponctuels_sol** : BEV (dalles 0,40 × 0,40, profondeur 0,40 m, à 0,50 m du nez) derrière les bateaux
de traversée qui donnent sur la chaussée, sauf OSM `tactile_paving=no` ; tampons et avaloirs absents
des vecteurs GAM (à enrichir).

Matériaux : `schema/materiaux_description.json` résout chaque `materiau_id` vers la librairie CC0
(`disponible`, `substitut`, `derive`, `a_telecharger` : BRF à télécharger, gravier → `gravillons_ilot`).
Pas de matériau City Sample côté Houdini / Karma.

## Marquages (schéma 0.3 : GAM d'abord, détection, règles ; v1 = indice)

Famille `marquages` sur tout le carré de 300 m (`decrire/marquages.py`, appelé par `composer.py`). Aucune géométrie v1 n'est
posée : le paquet v1 n'est qu'un **indice** (existence, type, couleur, usure, fenêtre de recherche). Priorité par élément
(FUS-SRC-001, `decrire/marquages_sources.py`) :

1. **levé GAM 2026** (`etat_2026/signalisation_horizontale_lin/pct`) : polylignes chaînées puis classées
   (`marquages_gam_classer.py` : bandes de zébra, flèches ajustées aux gabarits IISR, chevrons, dents, zigzags, hachures,
   axes et tirets, pictogrammes dessinés ; blocs VELO / PMR / FLECHE) -> entités normatives (`marquages_gam_entites.py`) ;
2. **plan projet 2025** calé, dans la zone des travaux, pour ce que le GAM n'a pas : détecteurs `detection_fleches.py`
   (DET-FLE-004), `detection_zebras.py` (DET-ZEB-009), `detection_lignes.py` (DET-PLN-016) et détection guidée des indices
   v1 (`detection_indices.py`) ;
3. **ortho 2022** hors des zones refaites ou construites (raster des états de zone `marquages_sources.zones()`) : mêmes
   détecteurs (DET-FLE-003, DET-LIG-010/011) ; une marque supprimée par les travaux n'est jamais un « fantôme » sans
   preuve postérieure (aucune photo après 08/2025) : retirée, justifiée ;
4. **règles** `deduire_si_absent` (`marquages_inference.py`) : lignes d'arrêt virtuelles et hypothèses (MQ-LEF-002/011),
   flèches par voie (INF-FLE-004, MQ-FLE-003 à 006), passages par groupe R12 (MQ-DET-004), traversées cyclables
   (MQ-CYC-007), zigzags de bus (MQ-DET-009), files (MQ-DET-002) ;
5. **v1** seul (zone sans image admissible) : posé `a_verifier`.

Fusion (`marquages_fusion.py`) : appariement FUS-ASS-003 (portes + hongrois), score FUS-SCO-002, accrochage normatif
FUS-SNP-004, conflits FUS-CON-005 ; contraintes (`marquages_contraintes.py`) : interruptions aux passages, marques et
bordures GAM (MQ-LIG-002, MQ-DET-010). Chaque entité porte `src`, `confiance`, `score`, `sources [{src, ref, c, S}]`,
`regles`, `lien_v1`. Sorties `description/base/` : `marquages.geojson` (fabriqué), `marquages_correspondance.geojson`
(devenir justifié des 996 v1), `marquages_hypotheses.geojson` (toutes les hypothèses et leur décision),
`marquages_indices_v1.geojson` (indices, non fabriqués). Contrôles 0.3 : `decrire/marquages_verifier.py` (via `valider.py`).

```
python recon/pcg/decrire/marquages.py [--sortie DOSSIER] [--rapport R.json]   # famille marquages seule
python recon/pcg/decrire/marquages_couverture.py                            # couverture_marquages*.png (source par couleur)
python recon/pcg/decrire/detection_evaluation.py                            # précision / rappel des détecteurs contre le GAM
```

## Zone pilote ZP-01

Rectangle local x ∈ [−11, 60], y ∈ [−28, 72] (71 × 100 m ; L93 917268.43-917339.43 / 6460261.98-6460361.98) :
refuge et TPC NE, traversée NE (blocs CHARTIERE, BEV), trottoir + piste + accotement de Verdun NE sur
≈ 65 m, entrée charretière de l'accès riverain (K-0182), îlot BRF (goutte NE, I-0297), îlots gravier du
Vercors (I-0390, I-0629), traversée du Vercors. 50 photos Panoramax dans l'emprise, dont 9 en 360° du
18/05/2025 (précision 0,1-0,4 m). Justification détaillée dans `zone_pilote.geojson`.

## Commandes

Depuis la racine du dépôt, avec l'interpréteur système (Python 3.11, numpy, Pillow, pyproj) :

```
python recon/pcg/decrire/composer.py                       # description + validation
python recon/pcg/decrire/composer.py --png planche.png     # + planche de contrôle
python recon/pcg/decrire/valider.py [DOSSIER]              # validation seule
python recon/pcg/decrire/apercu.py SORTIE.png --etiquettes [--emprise x0 y0 x1 y1] [--res 0.025]
```

`composer.py --sortie DOSSIER` écrit ailleurs (essais) ; le code de sortie est 1 si la validation échoue.

## Limites connues (0.1)

- Aucune photo après les travaux 2025 : matériaux, remplissages et bordures neuves sont `a_priori`
  (listés dans `description_scene_v2.json: a_priori`) ; les îlots du Vercors reprennent le gravier
  observé avant travaux (constats coeur-31, p2025_01_vercors-26), le BRF de la goutte NE suit la photo
  de référence de l'utilisateur.
- Les limites de surfaces v1 d'origine raster ne sont pas encore recalées (drapeau `limite_raster`).
- Les refuges à niveau (TPC NE coupé par la traversée) n'ont pas de BEV décrite (pas de bordure où l'ancrer).
- Le MNT 2026 garde par endroits un relief 2021 disparu (prolongement de l'ancien TPC NE : S-0344,
  `niveau.arasement`) : la fabrication doit araser ces surfaces au niveau indiqué.

## Sol 0.3 : site complet et nivellement unique (bordures, surfaces, îlots, ponctuels_sol)

Le schéma 0.3 étend les familles de sol au carré de 300 m (`decrire/sol_site.py`, local [-150, 150]²) ;
`composer.py` appelle `sol_composer.familles_sol` (une ligne). Aucune géométrie v1 n'est reprise : le v1 ne
donne que des indices de classe et de matériau (carte d'indices à 0,10 m).

```
decrire/
  sol_site.py        contexte du site (levé GAM 2026 et calques SOL_* du même DWG, OpenDRIVE, passages, cartes d'indices)
  sol_partition.py   arrangement plan exact (numpy) : polylignes -> faces avec trous, arêtes étiquetées (TQ-SOL-001)
  sol_geometrie.py   arête arrière et emprise des bordures (largeur de base du profil, bordures.json)
  sol_lacunes.py     bouts de file libres : ponts K-95nn (bateau déduit GA-ABA-001), fermetures de bout
  surfaces.py        partition vectorielle : bordures (avant, arrière, bouts), bâtiments, rampes (GA-ABA-003/005,
                     GA-CHR-002), bords OpenDRIVE, limites GAM (revêtement, végétation, talus), fermetures signalées
  nivellement.py     modèle de nivellement unique (TQ-SOL-013, CF-26), contrôles « verifier », écriture
  nivellement_xodr.py  Z OpenDRIVE elevation + superelevation + shape (TQ-SOL-004)
  nivellement_requete.py  requête autonome (numpy seul) : Nivellement(base).z(x, y, surface_id), z_bordure(id, s)
  sol_controles.py   contrôles appelés par valider.py (GA-ABA-*, GA-BEV-*, GA-TRO-*, GA-BOR-005, VAL-SOL-009...)
  sol_apercu.py      planches PNG : site complet + 4 zooms, et ombrage / pentes du nivellement
recon/out/paquet_jardin/v2/description/base/
  nivellement.json         régions, modèle par surface, lignes de contrainte des bordures (pied, tête, arrière tous
                           les 0,5 m), descentes de fin de file, contrôles
  nivellement_grille.npz   z0/r0 (nœud et région propriétaire), z1/r1 et z2/r2 (prolongements de 2 nœuds des
                           régions voisines), grille de 0,10 m, nœud (i, j) = (x0 + i·pas, y0 + j·pas), z LOCAL
```

Règles de fabrication pour Houdini (les deux agents de fabrication) :
- **surfaces** : partition exacte du carré, trous = bâtiments ; `emprise_bordure` = sol sous l'élément, au niveau
  du pied (caché) ; `rampe` = plan incliné derrière un abaissé ; `limite_raster` + `fermetures_m` = limites sans
  source vectorielle (bords de chaussée et limites vert / revêtu des grandes faces mêlées), simplifiées et signalées ;
- **Z de tout sommet de sol** : `Nivellement(base).z(x, y, surface_id)` (jamais le MNT ni les maillages v1) ; la
  requête n'interpole qu'à l'intérieur de la région de nivellement de la surface : les marches de bordure ne
  sont jamais lissées ;
- **bordures** : Z des sommets = pied de face (fil d'eau du caniveau CS2 au contact, sinon chaussée), `z_ref`
  `nivellement_2026` ; tête = pied + vue décrite ; sol du côté haut = tête − 4 mm (trottoir), − retrait (îlot
  rempli), − 2 cm (espace vert) ;
- **marquages** : drapés sur `z(x, y, surface_id)` de la chaussée.

Limites de la partition, par priorité (TQ-SOL-001) : bordures (avant, arrière, bouts), bâtiments, rampes,
bords OpenDRIVE, levé GAM 2026 (limites de revêtement, végétation, talus), aires de stationnement OSM
(`osm_parking`, retirées à < 0,6 m d'une limite déjà présente), puis fermetures signalées (`limite_raster`).
Les éclats (< 0,01 m² ou < 4 mm de large) sont fusionnés avec leur voisine par une limite continue.
Nivellement des cheminements (GA-TRO-003) : bande de 4 m derrière chaque bordure de chaussée calée sur
tête − 4 mm + 1,5 % · d ; le raccord au terrain (MNT lissé) se fait au-delà, dans les espaces verts.

## Régularisation géométrique 0.3 : un plan de VRD professionnel (GQ-*)

Règles : `assets/specs/regles_qualite_geometrique.json` (33 règles GQ-*, sources PCRS v2.0, ASAM OpenDRIVE 1.9,
arrêté du 16/09/2003, IISR 7e partie, Cerema, Lyon, Paris ; `REGLES_QUALITE_GEOMETRIQUE.md` est généré par
`decrire/regulariser_regles.py`). Les polylignes levées (GAM, PCRS, plan 2025, fermetures raster) ne sont plus que
des mesures : bordures, contours d'îlots, limites de surfaces et axes de lignes de marquage sont des suites de
**droites et d'arcs tangents (G1)**, coins voulus seulement, dans la tolérance de la source (99 % ≤ T, tous ≤ 1,5 T ;
T = 3 cm GAM, 5 cm plan 2025, 10 cm PCRS / ortho / v1, 25 cm fermetures raster).

```
decrire/
  regulariser_geometrie.py  cœur numérique : chaîne intrinsèque (x0, y0, cap, pièces L/k : G1 par construction),
                            découpage initial droite/arc, Levenberg-Marquardt à jacobien analytique (Huber),
                            découpe / fusion / rayons normalisés, coins voulus, densification (flèche ≤ 2 mm)
  regulariser.py            crochets : bordures (orientation GQ-ORI-001/002, nœuds GQ-TOP-001/002/003, ajustement,
                            remappage des abscisses GQ-TOP-005), lignes_partition (limites GAM, OSM, fermetures ;
                            largeur constante GQ-LAR-001), marquages (axes GQ-PRI-002), archive des sources
  regulariser_controles.py  règles « verifier » (appelées par valider.py) : primitives relues, G1, écarts, cassures,
                            nœuds, partition sans lacune, orientation, rayons, quais, abaissés, zébras, marquages
  regulariser_apercu.py     planches avant / après (6 zooms), peignes de courbure, carte des écarts
  regulariser_regles.py     REGLES_QUALITE_GEOMETRIQUE.md depuis le JSON
```

Ordre dans `composer.py` : `bordures.construire` → **`regulariser.bordures`** → `ilots.construire` (anneaux de
bordures régularisées) → `surfaces.construire` (limites **régularisées** par `regulariser.lignes_partition`, partition
reconstruite) → `regulariser.decrire_ajouts` (ponts K-95nn et ceintures, primitives relues sans déplacement) →
nivellement → marquages → **`regulariser.marquages`** → `regulariser.ecrire_sources`.

Description (schéma 0.3, additif) : `geometrie_reguliere` sur chaque bordure et chaque ligne / transversale de
marquage : `statut` (regularise | hors_tolerance | source_gardee), `primitives [{type droite|arc|clothoide, s0, s1, x0,
y0 (L93), cap0_rad, k0, k1?, rayon_m?, coin?}]` (fait foi), `ecart_max_m`, `ecart_p99_m`, `tolerance_m`, `coins`,
`noeuds {debut, fin : noeud|t|anneau|libre, avec, g1}` ; `prov.regularisation` ; la polyligne est la densification des
primitives (flèche ≤ 2 mm, pas ≤ 0,5 m sur les bordures). `base/regularisation_sources.geojson` archive les
géométries avant régularisation (contrôles, planches ; non fabriqué). Statistiques : manifeste
`statistiques.regularisation` (orientation retournée et conflits journalisés, nœuds, statuts, limites).

Pour Houdini : construire les bordures, les rubans de marquage et les limites depuis la polyligne (déjà densifiée)
ou, pour une pose exacte, depuis `primitives` (arcs : pas des éléments selon `rayon_m`, `courbes` recalculées sur les
arcs : pièce courbe si R < 3 m, éléments de 0,50 m si R < 12 m).

```
python recon/pcg/decrire/regulariser_apercu.py [--dossier DESCRIPTION]     # planches dans <description>/regularisation
python recon/pcg/decrire/regulariser_regles.py                             # REGLES_QUALITE_GEOMETRIQUE.md
```

## Vérification des règles de conception (recon/pcg/controle)

Contrôle automatique de la description et de la fabrication Houdini (`fabrique_hda`) contre
`assets/specs/regles_conception.json` : un contrôle par règle « verifier » et par règle « contraindre » mesurable,
avec cas testés, violations (entité, coordonnées, valeur, seuil) et sévérité. Détail : `recon/pcg/controle/README.md`.

```
python recon/pcg/controle/verifier_regles.py          # -> recon/out/paquet_jardin/v2/controle/{rapport_regles.json, RAPPORT_REGLES.md}
hython recon/pcg/controle/rendre_controle.py          # rendus Karma de la fabrication v2 seule -> recon/pc/rendus/v2_site
```

## Corrections après revues (11/10/2026, agent corrections)

Description (composer.py, hash_description `222b11f5…`) :
- `ilots.py` : contour v1 d'îlot rogné au-delà d'une bordure levée qui le traverse (GQ-TOP-004) ; aucune bordure
  synthétique sur une lacune déjà fermée par une bordure levée hors ceinture (≤ 0,6 m, GA-ILO-003 : K-9339a supprimée) ;
  bordure synthétique coupée aux croisements des bordures levées (K-9333a supprimée) et de la vue des bordures levées
  adjacentes ; corde d'anneau comblée par une bordure parallèle à 0,3-0,6 m (K-0628z supprimée).
- `sol_lacunes.py` : pont de Hermite refusé sous R 1 m ou en S avec plus de 0,10 m de décalage (GQ-RAY-001,
  GA-BOR-005 : ancien K-9514 devant le zébra de Verdun SO) ; 14 ponts au lieu de 17.
- `nivellement.py` : pas de descente de fin de file sur un MURET_TALUS (K-0098 « en tente ») ; les raccords de
  contact entre bordures restent.
- `surfaces.py` : face plantée dont la moitié de l'aire est à ≤ 2 m d'une marque levée GAM 2026 reclassée revêtue
  (chaussée, ou piste si un vélo GAM y est levé ; MQ-DET-010, TQ-SOL-001).
- `marquages.py` : indice v1 seul (P = 0,30) gardé en hypothèse mais `fabrication.statut = non_fabrique`
  (MP-0370, MS-0262..0265 ; aucune géométrie v1 fabriquée) ; `marquages_supports.py` : flèche non levée à contresens ou
  sur l'axe d'une chaussée à double sens non fabriquée (VAL-FLE-001 : MF-0286), marque surfacique non levée traversée
  hors abaissé par une bordure GAM 2026 non fabriquée (MQ-DET-010, FUS-CON-005 : MP-0333) ;
  `marquages_chronovelo.py` : traversées Chronovélo aux crosswalk « bicycle » 1/1010 et 2/1011 du .xodr sans marque,
  pavés orange du plan projet 2025 détectés par couleur et régularisés sur PAVE_CHRONOVELO / CARRE_TRAVERSEE_CYCLABLE
  (MQ-CHR-001, MQ-CYC-007, VAL-XOD-008 ; MP-8200, MP-8201, confiance faible, à vérifier).

Fabrication : `recon/pcg/houdini/hda/README_HDA.md` § 10. Vérificateur (`recon/pcg/controle`) : rastérisation exacte
des surfaces (pair-impair, plus de faux trous TQ-SOL-009), recouvrements de sol comptés quel que soit l'écart,
GA-ILO-001 étendue aux îlots typés refuge sans zébra.
