# recon/generateur/hda : HDA `rg::*` du générateur de routes (étape 1 : lots L1, L2, L2b ; étape 2 : carrefours, giratoires, autoroutes, bordures)

*`recon/generateur/hda/README_RG.md` — 17/10/2026, complété le 18/10/2026 (intégration de l'étape 2 : § 10 à 14). Plan : `recon/generateur/PLAN_GENERATEUR.md` § 2.3 et § 3 (L1, L2, L4 pour la section courante = L2b).
Conventions communes avec les HDA `pj::*` : `recon/pcg/houdini/hda/README_HDA.md` (repère, Python réservé aux
entrées-sorties, HDA développées, VEX sans `#include "opdef:"` ni `struct`, déterminisme).*

« Claude décrit, Houdini fabrique » : une description simple (`description/FORMAT_DESCRIPTION.md`) ou un modèle
`modele_voie/0.1` entre dans Houdini par `rg::lire_modele` ; `rg::graphe` échantillonne les lignes de référence ;
`rg::profils` déroule les profils en travers. **Houdini n'invente rien** : chaque cote vient d'un attribut du modèle
(avec sa provenance dans le modèle) ou d'un paramètre d'HDA dont la règle est citée (rampe des plateaux : DEF-034).

```
hda/
  README_RG.md                     ce fichier
  commun/rg_hda_outils.py          construction des HDA rg::* (signature, dossier développé, wrangles VEX 64 bits)
  commun/vex/rg_geometrie.h        primitives droite / arc / clothoïde, lois de largeur, positions t des limites,
                                   loi verticale des ralentisseurs (recopiée en tête des wrangles)
  commun/vex/rg_niveau.h           lot L2 : modèle de Z unique (TQ-SOL-013), coupe en travers rg_coupe, inversion
                                   (x, y) -> (s, t), nœuds du HeightField (nappes, prolongements)
  rg_lire_modele/construire.py, lecteur.py, rg_lire_modele.hdalc/
  rg_graphe/construire.py, rg_graphe.hdalc/
  rg_profils/construire.py, rg_profils.hdalc/
  rg_nivellement/construire.py, rg_nivellement.hdalc/        lot L2
  rg_sol/construire.py, rg_sol.hdalc/                        lot L2
  rg_vers_entites/construire.py, rg_vers_entites.hdalc/      lot L2
  pj_caniveau_v2/construire.py, pj_caniveau_2.0.hdalc/       pj::caniveau::2.0 (nouvelle version, la 1.0 reste intacte)
  pj_bordure_v2/construire.py, pj_bordure_2.0.hdalc/         pj::bordure::2.0 (nouvelle version, la 1.0 reste intacte)
  pj_caniveau_v2_1/construire.py, pj_caniveau_2.1.hdalc/     pj::caniveau::2.1 (second contrôle ; 1.0 et 2.0 intactes)
  pj_bordure_v2_1/construire.py, pj_bordure_2.1.hdalc/       pj::bordure::2.1 (lot bordures : table étendue ; § 13)
  pj_caniveau_v2_2/construire.py, pj_caniveau_2.2.hdalc/     pj::caniveau::2.2 (lot bordures : CC2, CS4, prototypes ; § 13)
  rg_carrefours/construire.py, rg_carrefours.hdalc/, rg_carrefours_sol.hdalc/   lot L3, carrefours plans (§ 9)
  rg_marquages_carrefour/construire.py, rg_marquages_carrefour.hdalc/         lot L4, marquages des carrefours (§ 10)
  rg_giratoires/construire.py, rg_giratoires.hdalc/, rg_giratoires_sol.hdalc/   lot L5, giratoires (§ 11)
  rg_autoroute/construire.py, rg_autoroute.hdalc/            lot autoroutes : retenues, bifurcations, musoirs (§ 12)
  commun/vex/rg_marquage.h         lot L2b : empreintes en (s, t), découpe en cellules (lignes de rupture du sol, corps de
                                   bordure et caniveaux retirés), attributs du contrat de pj::marquage_solide
  rg_marquages/construire.py, marquages.vfl, rg_marquages.hdalc/     lot L2b
  rg_marquages/gabarits_iisr7.py, gabarits_iisr7_pj.json   gabarits et glyphes du dossier 08 au format de pj::gabarits_iisr
recon/generateur/fabriquer_generateur.py    pilote hython (description .yaml ou modèle .json -> courbes de contrôle ;
                                            --l2 : sol, bordures, caniveaux ; --l2b : marquages et chaîne de réseau
                                            choisie d'après le modèle ; --complet : description -> rendu ; § 14)
recon/generateur/fabriquer_carrefours.py, fabriquer_marquages_carrefour.py, fabriquer_giratoires.py,
  fabriquer_autoroutes.py, fabriquer_bordures.py   pilotes des lots de l'étape 2, bibliothèques de fabriquer_generateur
commun/bordures_catalogue.py                types de bordures et caniveaux du catalogue route_fr (§ 13)
vehicules/balayage.py, vehicules_projet.json   lot L3a : véhicules de projet et épures de giration
recon/generateur/fabriquer_l2.py            lot L2 du pilote (réseau, exports, sondes de mesure, USD)
recon/generateur/fabriquer_l2b.py           lot L2b du pilote (rg::marquages -> pj::marquage_solide x 2, mesures, USD)
recon/generateur/rendu/                     rendus de contrôle (rendre_l2.py, rendu_scenes.py, decor.py) ; lot L2b :
                                            rendu_l2b.py, ciel.py, decor_l2b.py, textures.py, planches.py
recon/generateur/validation/controler_L1.py contrôles indépendants (Python, scipy, shapely)
recon/generateur/validation/dessiner_L1.py  plans de contrôle (SVG, PNG) et tuiles natives
recon/generateur/validation/analytique_L2.py, controler_L2.py, faire_rapport_L2.py   contrôle indépendant du lot L2
recon/generateur/validation/analytique_L2b.py, controler_L2b.py, faire_rapport_L2b.py contrôle indépendant du lot L2b
```

## 1. Outils et conventions

- Houdini 22.0.459 Indie, `hython`. HDA enregistrées en dossiers développés `rg_<nom>.hdalc/` (réseau non compressé),
  installables tels quels (`hou.hda.installFile`). Signature de construction (sha256 du réseau `asCode`, de
  l'interface, du module Python et de l'aide) dans la section `RgSignature` : si elle ne change pas, le dossier
  existant est gardé à l'octet. Les fichiers temporaires de construction vont dans `recon/generateur/tmp/` (D:).
- Wrangles en **VEX 64 bits** (`vex_precision = 64`) : la clothoïde est intégrée en double précision.
  Stockage Houdini : positions et attributs en flottants 32 bits (résolution ≤ 1,5e-5 m sous 256 m de l'origine,
  50 fois sous les tolérances du lot).
- Repère : local = Lambert-93 − `repere.origine_l93` du modèle ; Houdini `(x, z, −y)`, Y haut ; conversion faite une
  seule fois, dans `rg::lire_modele`. Courbes de contrôle planimétriques (Y = 0), sauf le profil en long (Y = dz).
- Conventions du modèle : `s` abscisse absolue le long de la ligne de référence ; `t` positif à gauche ; cap
  OpenDRIVE (0 = est, sens trigonométrique), courbure > 0 à gauche ; à un raccord de primitives, le point appartient à
  la primitive suivante (départ exact du modèle).
- Déterminisme : le pilote se relance avec `HOUDINI_VEX_DISABLE_JIT=1` ; aucune date ni durée dans les sorties ;
  `--verifier-determinisme` compare deux processus à l'octet.

## 2. `rg::lire_modele::1.0` (« RG Lire le modèle de voies »)

Cinq Python SOP (module `lecteur.py` embarqué, seul Python géométrique admis), une sortie chacun ; aucune opération
géométrique : les valeurs du modèle sont rangées en attributs.

| Sortie | Contenu | Attributs principaux |
|---|---|---|
| 1 Routes | polyligne `ligne_reference.geometrie` (groupe `routes`) | `id`, `categorie`, `agglomeration`, `vitesse_kmh`, `sens_unique`, `noeud_debut`, `noeud_fin`, `longueur_m`, `geometrie_reguliere` ; `geo_type[]` (0 droite, 1 arc, 2 clothoïde), `geo_s0[]`, `geo_longueur[]`, `geo_x0[]`, `geo_y0[]` (locaux), `geo_cap[]` (rad), `geo_k0[]`, `geo_k1[]` ; `sec_s0[]`, `sec_s1[]`, `sec_profil[]`, `sec_transition[]` ; `props` (JSON sans provenance) |
| 2 Nœuds | points | `id`, `type`, `carrefour`, `routes[]`, `props` |
| 3 Zones et îlots | polygones (anneau 0 extérieur, groupe `trou`) | `id`, `famille_modele`, `type`, `materiau_id`, `anneau`, `props` |
| 4 Ponctuels | objets (plateaux, dos-d'âne, coussins, arbres, abris…), signaux, marquages | `id`, `famille_modele`, `famille`, `type`, `route`, `bande`, `s`, `t`, `longueur_m`, `largeur_m`, `hauteur_m`, `rayon_m`, `regles[]`, `a_position`, `props` |
| 5 Profils | un point par profil effectif (profil d'une section en ligne : `<route>~S<k>` ; avec surcharges : `<profil>~<route>~S<k>`) | `profil`, `ref_limite`, `ref_decalage`, `n_bandes` ; bandes `bande_id[]`, `bande_type[]`, `bande_sens[]`, `bande_materiau[]`, `niv_*[]`, `bande_json[]` ; lois de largeur aplaties `larg_type[]` (0 nombre, 1 points linéaire, 2 palier, 4 poly3), `larg_s0[]`, `larg_v0[]`, `larg_n[]`, `larg_s[]`, `larg_v[]` ; limites `lim_nature[]`, `lim_bordure[]`, `lim_vue[]`, `lim_cote_haut[]`, `lim_caniveau[]`, `lim_marquages[]` (JSON), `lim_separateur[]`, `lim_json[]` ; `evts_s[]` (abaissés, intervalles et interruptions de marquage) |

Détail `rg_modele` sur chaque sortie : fichier, sha256, origine, comptes, familles non lues (carrefours, ouvrages,
contrôleurs, graphe de voies : avertissement du nœud). **Erreurs** (jamais de silence) : schéma autre que
`modele_voie/0.1`, clé racine inconnue, primitive `parampoly3`, interpolation `cubique_lisse` (non définie par le
schéma 0.1), transition d'entrée autre que `instantanee`, surcharge non reconnue, profil inconnu, nombre de limites
≠ n + 1.

## 3. `rg::graphe::1.0` (« RG Graphe »)

Entrées : 1 routes, 2 profils, 3 ponctuels, 4 nœuds. Sorties : 1 références échantillonnées, 2 nœuds.

- **Sommets obligatoires** : 0 et L, raccords des primitives, bornes des sections, points des lois de largeur, évènements
  des limites (abaissés, intervalles et interruptions de marquage ; paramètre « Sommets aux évènements »), pieds et
  hauts de rampe des plateaux, bornes et sommet des dos-d'âne.
- **Pas** entre deux sommets obligatoires : uniforme, h = min(pas_max, √(8 f / B)), f = flèche maximale × marge
  (0,5 mm × 0,9), B majorant de |P''| sur toutes les limites décalées de l'intervalle :
  B = max_limites [2 |t'| |κ| + |t| |κ'| + (1 + |t| |κ|) |κ| + |t''|], et |dz''| de la loi verticale (dos-d'âne).
  Pour un arc de rayon R et une limite à |t| : h = √(8 f R² / (R + |t|)) (0,45 m pour R = 60 m, |t| = 5 m).
- Points : `s`, `cap_rad`, `courbure`, `T`, `gauche` (normale à gauche, en onglet aux sommets d'une polyligne),
  `obligatoire`, `route` ; primitives : attributs de la route recopiés (Attribute Copy par `id`), `n_echantillons`,
  `pas_min_m`, `fleche_majorant_m`.
- Routes sans géométrie régulière (inférence OSM) : droites par sommets, abscisse ramenée à `longueur_m`, décalage en
  onglet aux sommets (les sommets anguleux replient les décalés intérieurs : à régulariser avant les carrefours).
- Nœuds : `branches[]` (routes triées par azimut, sens trigonométrique), `extremites[]`, `azimuts_deg[]`, `valence`.
- Paramètres : flèche maximale (0,0005 m), marge (0,9), pas maximal (1 m, choix de fabrication), rampe des plateaux
  (DEF-034 : 7 %), sommets aux évènements (oui).

## 4. `rg::profils::1.0` (« RG Profils »)

Entrées : 1 références échantillonnées, 2 profils, 3 ponctuels. Sorties : 1 limites, 2 bandes (rubans), 3 profils
d'extrémité, 4 profil en long.

- Pour chaque section [s0, s1] (échantillons des bornes dédoublés : chaque section a les siens) et chaque échantillon :
  limite i en P(s) + t_i(s) · gauche(s), t_r = −`reference.decalage_m`, t_i = cumul des largeurs w_b(s).
- **Transitions de profil** : élargissement et rabattement par les lois de largeur des sections (continuité contrôlée
  aux jonctions, bande par bande) ; changement instantané seulement s'il est déclaré (`transition_entree:
  instantanee`, écrit par le compilateur pour un changement de profil dit sans transition) ; plateaux et dos-d'âne par
  la loi verticale `dz_chaussee(s)` (plateau trapézoïdal : longueur totale et hauteur du modèle, rampe DEF-034 ;
  dos-d'âne : segment de cercle de corde `longueur_m` et de flèche `hauteur_m`, RF-MA-RAL-001). Les coussins
  (ralentisseurs locaux, pas une transition de profil) restent des ponctuels pour le lot L2.
- Limites (polylignes) : `route`, `section`, `profil`, `limite`, `cle` (`bande gauche|bande droite`), `nature`,
  `bordure`, `vue_m`, `vue_loi`, `cote_haut`, `caniveau`, `marquages` (JSON), `separateur`, `limite_json`,
  `est_reference`, `transition_entree` ; points `s`, `t`, `dz_chaussee`, `limite`, `section`.
- Rubans : quadrilatères (normale +Y) partageant les points des limites ; `bande`, `type`, `sous_type`, `sens`,
  `materiau_id`, `niv_reference`, `niv_dz`, `niv_devers`, `niv_forme`, `largeur_min_m`, `largeur_max_m`,
  `bande_json`.
- Profils d'extrémité : coupe de gauche à droite en s = 0 et s = L (`extremite`, `noeud`) : frontière des futurs
  carrefours (lot L3).
- Profil en long : polyligne (x, dz, −y) de la chaussée.
- Détail : `rg_largeur_min_m`, `rg_largeurs_negatives`, `rg_largeurs_nulles_hors_biseau`, `rg_extremites_de_biseau`,
  `rg_replis` (1 − t κ ≤ 0), `rg_sections_non_contigues`, `rg_jonctions_discontinues`, `rg_jonction_*` (route, s,
  écart, bande, instantanée déclarée).

## 5. Lot L2 : `rg::nivellement`, `rg::sol`, `rg::vers_entites`, `pj::caniveau::2.0`

Chaîne (`fabriquer_l2.py`) :

```
rg::graphe ──► rg::nivellement ─┬─ 1 NIVEAUX ─┬─► rg::sol ──► 1 SOL, 2 BEV, 3 ZONES
rg::lire_modele (profils,       │             └─► rg::vers_entites ─► 1 ENTITÉS ─► pj::bordure::2.0, pj::caniveau::2.0
  ponctuels, zones)             │                                  └► 2 VÉGÉTATION (arbres)
                                └─ 2 HeightField ─────────────────────► entrée 2 de pj::bordure et pj::caniveau
```

**Un seul modèle de Z** (`commun/vex/rg_niveau.h`, TQ-SOL-013), évalué en (s, t) le long de la ligne de référence :
(1) chaussée : chaque groupe de bandes basses ancré à Z = 0 en t = 0 (ou à sa limite la plus proche), dévers de
chaque bande, + dz(s) des ralentisseurs (plateau DEF-034, dos-d'âne RF-MA-RAL-001, d'un trottoir à l'autre) ;
(2) caniveau : arête côté chaussée au Z de la chaussée, fil d'eau = arête − Δh du profil (bordures.json) ; (3) pied
de face = fil d'eau (sinon chaussée au droit de la face) ; (4) tête = pied + vue (abaissés avec rampants, DEF-031,
RF-MA-ABA-004) ; (5) trottoir à tête − 4 mm derrière la bordure puis dévers (TQ-SOL-013 (6)), bande plantée isolée
entre bordures à tête − 4 cm (TQ-SOL-013 (7)) ; (6) bande haute sans dévers dit : plan entre ses deux appuis.
Bordures « virtuelles » : une limite bordée dans une autre section garde son niveau (avancées de trottoir).

### `rg::nivellement::1.0` (« RG Nivellement (modèle de Z unique) »)

Entrées : 1 références (rg::graphe), 2 profils, 3 ponctuels, 4 zones (rg::lire_modele). Sorties :

1. **NIVEAUX** : groupe `sections` (un point par section : tables `b_*` bandes, `l_*` limites — bordure réelle ou
   virtuelle, côté haut, base, H, vue, caniveau —, `a_*` abaissés, `r_*` ralentisseurs, abords ; lois de largeur
   recopiées : la géométrie se suffit à elle-même), points `ralentisseurs`, groupe `bordures` (files chaînées, côté
   haut à gauche : longitudinales et retours transversaux aux jonctions de sections ; points `s_ref`, `t_ref`,
   `pied`, `tete`, `vue`, `zbf`, `zemp`, `can`, `kind`, `k_bas`, `b_bas`).
2. **HeightField** au pas de 0,10 m rangé comme celui de `pj::lire_description` (README_HDA § 2 : `height`, `r0`,
   `z1`, `r1`, `z2`, `r2` ; détail `niv_x0`, `niv_y0`, `niv_pas`, `niv_ni`, `niv_nj`, `niv_routes`). Région =
   100 × rang de la route + nappe (nappe 0 à gauche ; frontière au milieu du corps de chaque bordure réelle, ou
   virtuelle entre bande haute et bande basse). `z1`/`z2` : prolongements des nappes voisines à moins de deux nœuds
   (en travers, puis section voisine aux jonctions). Domaine élargi d'un demi-pas ; hors domaine, r0 = −1 et Z
   prolongé (affichage). Lu par `pj_niv_z` sans modification de `pj_niveau.h`.

Paramètres : rampe des plateaux (DEF-034), pas des retours (0,25 m), pas et marge du HeightField (0,10 m ; 1 m).

### `rg::sol::1.0` (« RG Sol (nappe étanche sur le modèle unique) »)

Entrées : 1 références, 2 niveaux. Sorties : 1 SOL, 2 BEV, 3 ZONES (contrôle).

- Triangulate 2D unique par route dans le plan des paramètres (s + décalage, −t) : contour (profil + abords), lignes
  de rupture contraintes (limites sans bordure réelle, jonctions de sections, bords de rampe et de bateau,
  TQ-SOL-003), zones sous les bordures (sol bas prolongé sous la bordure jusqu'à base − 12 mm, TQ-BOR-007 ; sol caché
  sous caniveau posé ; surface de caniveau relevée par un ralentisseur). Arête cible 0,25 m, arête minimale 0,02 m,
  angle min 25° (TQ-SOL-002).
- Z de chaque sommet par le modèle unique selon la zone de son triangle ; Split Points par Z puis **murs** entre les
  copies (copies intermédiaires comprises) : une seule nappe 2-variété, bord seulement sur le contour.
- Passage exact au monde (`rg_local_st`), normales cusp 30° puis, sur les faces de bande, gradient analytique du
  modèle (TQ-SOL-008), UV en mètres ; `materiau_id`, `pj_couche`, `pj_entite`.
- BEV : dalles podotactiles à 0,50 m du nez (DEF-031), profondeur 0,5875 m (0,40 si trottoir < 1,90 m), dessus 3 mm
  au-dessus du trottoir, plots en quinconce au pas de 75 mm.
- Correction après contrôle (17/10/2026) : une file de bordure **fermée** (îlot isolé dont la bordure fait le tour,
  rues de Meylan) a ses zones comme une file ouverte refermée sur son premier point, onglet à la fermeture (avant : zones
  non faites, le sol du terre-plein traversait la bordure et dessinait des dents de scie le long des chartières) ; BEV
  avec coordonnées de texture le long de la bordure (dalles jointées), étendue limitée à la vue visible < 0,05 m.

`pj::sol` n'est pas utilisé : il triangule un relevé de site (polygones de surfaces, HeightField à 0,10 m) ; le sol
généré doit porter les lignes de rupture du modèle (TQ-SOL-003) et le Z exact de chaque sommet (TQ-SOL-004), d'où
`rg::sol`, qui sort le même contrat (maillage Y haut, `materiau_id`, `pj_couche`, `pj_entite`, N, uv).

### `rg::vers_entites::1.0` (« RG Vers entités (contrat pj::*) »)

Entrées : 1 niveaux, 2 profils, 3 références. Sorties : 1 ENTITÉS (une courbe par file de bordure, au contrat de
`pj::lire_description` : `id`, `famille`, `intervalles` — rôles courant / chartière / bateau, profil, vue —,
`niv_s`, `niv_z_pied`, `niv_z_tete`, `caniveau`, `props`, `materiau_id`, `aspect`), 2 VÉGÉTATION (arbres des
`objets_le_long` de famille vegetation : mode points ou pas, phase comptée depuis le début de l'intervalle).
Retours de bordure : pied et tête suivent les surfaces basse et haute, la vue est linéaire par tronçon ; intervalles
« chartière » (raccord de vue de pj::bordure, éléments de 1,00 m au plus) ou « courant » si la vue est constante.

**Correction après contrôle (17/10/2026)** :
- sortie 3 GRILLES D'AVALOIR (quadrilatères dans le caniveau, au pied de chaque rampe de plateau, longueur 0,65 m =
  grille `decal_grille_avaloir` du catalogue, largeur du caniveau ; Certu, Coussins et plateaux 2010, p. 46 § 2.1.3) ;
  et au bout aval (abscisses croissantes de la file, profil en long plat) de toute file de caniveau fermée par un retour
  de bordure, hors bout de la voie et hors caniveau à grille (paramètre `avaloir_fin_de_file`, actif par défaut ; poches
  de stationnement entre les avancées de S03 : 13 avaloirs ; moyen [G], demande D-CORR-9) ;
- caniveau à grille au droit des ralentisseurs : `props` porte `caniveau_grille.intervalles` (et l'attribut
  `grille_s`), là où le caniveau déclaré est relevé par un plateau ou un dos-d'âne (attribut `grille` des points de
  file de `rg::nivellement`, fonction `rg_caniveau_releve` de `rg_niveau.h`) : le fil d'eau reste continu sous la grille
  (décret 94-447, annexe art. 4 : « ne doit pas nuire à l'écoulement des eaux », source de RF-MA-RAL-001) ; le moyen
  constructif (grille dans l'emprise du caniveau) est un choix [G] : la règle est demandée au propriétaire de
  `regles_route_fr.json` (validation/regles_demandees_correction.json) ;
- boucles fermées (îlot central isolé dont la bordure fait le tour) ouvertes au premier point avant `pj::bordure`, qui
  ne pose que des courbes ouvertes (l'îlot de S_M24 n'avait aucune bordure) ;
- végétation : les points portent `asset_id`, `hauteur_m`, `houppier_rayon_m`, `fut_m` du modèle (rendu aux dimensions).

**`rg::sol` (correction après contrôle)** : surface du caniveau relevé par un ralentisseur en `grille_caniveau`
(caniveau à grille) ; BEV limitée au droit des bordures de vue visible < 0,05 m (RF-MA-BEV-002 : sur S10, la BEV
dépassait de 7 cm sur les rampants du plateau, devant 0,055 m), bornes affinées par interpolation ; coordonnées de
texture des BEV le long de la bordure (u en mètres depuis le début de la BEV, v de 0 au nez à 1 au fond : dalles
podotactiles jointées au rendu).

**Correction après le second contrôle de l'étape 1 (17/10/2026)** :
- `rg::vers_entites` : l'avaloir **remplace** le caniveau qu'il occupe (intervalles du caniveau moins ceux des avaloirs ;
  avant : deux pièces au même endroit dans elements.json, S03 26 recouvrements, S10 8) ; sortie 3 : grille au niveau du
  dessus du caniveau (plus 2 mm au-dessus) et corps fermé de l'avaloir sous la grille, jusqu'à 0,25 m sous le fil d'eau
  (attribut `partie` = `grille` | `corps` ; la position de l'élément dans elements.json est celle de la grille) : sans
  lui, la grille flottait au-dessus de l'assise du caniveau retiré ; retour transversal à vue
  variable marqué `usage = retour` dans ses intervalles (même pièce de raccord de vue que la chartière pour pj::bordure ;
  elements.json : type `raccord_vue`, rôle `retour`, au lieu de « chartiere », confondu au placement avec la chartière
  d'un abaissé) ;
- `rg::sol` : BEV posée dans sa section seulement (un profil repris dans une autre section reposait la même BEV) ;
  attribut `materiau_voisin` (revêtement de la bande où la BEV est posée) : la teinte de la BEV est choisie en contraste
  avec lui (RF-MA-OBS-003 : anthracite sur revêtement clair, gris clair sur enrobé ; bev.json : `materiau_voisin`,
  `teinte`) ;
- `rg::nivellement` : à un bout de la route, un élément répété coupé par le bout (profil de la première ou de la dernière
  section repris plus loin entre deux sections d'un autre profil : avancées de S03 en [0 ; 2,5] et [97,5 ; 100]) a son
  côté transversal construit contre le profil de la section voisine, supposé continuer au-delà du bout (S03 : 256 m de
  bordures, comme le catalogue) ;
- `pj::caniveau::2.1` (nouvelle version) : pièce de caniveau gardée dès 5 mm (au lieu de 5 cm) à une borne d'intervalle,
  sinon la coupe du caniveau à l'avaloir laissait un trou de 1 à 5 cm devant lui ; une coupe de moins de 0,20 m
  (TQ-BOR-002) est partagée avec l'élément voisin de la même file (deux pièces de même longueur, S03 : 2 × 0,52 m devant
  chaque avaloir au lieu de 0,994 + 0,047 m) ;
- `fabriquer_l2.py` (mesures) : la sonde « devant la face » d'une bordure voit les grilles d'avaloir (elles remplacent le
  caniveau) ; `validation/controler_L2.py` compte à part les sondes devant le côté transversal d'une avancée posé sur la
  coupe d'un bout de scène (face tournée hors de l'emprise, rien de modélisé devant : S03, 12 sondes) ;
- `fabriquer_l2.py` : `l2/vegetation.json` au format `rg_vegetation/0.2` (`{"etape": 2, "usage": …, "arbres": […]}`) : les
  arbres du modèle sont exportés pour l'étape 2 et ne sont pas placés à l'étape 1 ;
- compilateur (`description/description_vers_modele.py`) : abaissés et BEV sur les seules bordures de la traversée d'un
  passage (aboutissement sur la première surface piétonne, refuge, bordure franchie), bandes peintes sur les seules
  bandes traversées, passage refusé s'il aboutit dans une berme, une bande plantée ou le bord du profil
  (`traversee_passage`, `FORMAT_DESCRIPTION.md` § 8) ; dévers dit d'une bande (`dévers 0`).

### `pj::bordure::2.0` (étape 1, correction après contrôle)

Même réseau que `pj::bordure::1.0` (construit depuis `recon/pcg/houdini/hda/pj_bordure/construire.py`, importé sans
modification), correctif dans le nœud `disposer` (fonction `pj_disposer` de `pj_pose.h`) : (1) les sommets vifs de la
courbe (déviation de cap > 30° entre deux primitives : « angle vif », `assets/specs/bordures_elements.json`,
pose.points_durs) sont ajoutés aux coins voulus — les courbes de `rg::vers_entites` sont des polylignes sans
`geometrie_reguliere.coins` et n'en déclaraient aucun ; (2) un angle confondu (< 1 mm) avec un point dur de changement
d'intervalle (« abaisse », « profil ») devient un angle. Les deux éléments qui touchent l'angle sont alors posés sur
mesure et aboutés en onglet (plan bissecteur, joint de 3,5 à 9,5 mm) : c'est la pièce d'angle. Avant : aux angles des
avancées de S03 (retour en chartière → nez courant), joint de petite déviation ouvert à 90° en fente de 0,12 m sur le
nez (about droit, 26 angles, 1,58 m de « trous » dans elements.json). La 1.0 reste intacte dans le dépôt.

### `pj::caniveau::2.0` et `pj::caniveau::2.1`

Même réseau que `pj::caniveau::1.0` (construit depuis `recon/pcg/houdini/hda/pj_bordure/construire.py`), une seule
correction : la lecture des intervalles du caniveau (`props.caniveau.intervalles`) utilisait `re_findall` avec des
groupes capturants (VEX renvoie alors les groupes, pas les nombres) ; la 2.0 utilise des groupes non capturants. Les
caniveaux sont ainsi interrompus au droit des ralentisseurs et des avancées. La 1.0 reste intacte dans le dépôt.
La 2.1 (second contrôle) reprend la 2.0 et garde une pièce de caniveau dès 5 mm (au lieu de 5 cm) à la coupe d'un élément
de bordure par une borne d'intervalle : le caniveau coupé à l'avaloir n'a plus de trou devant lui ; une coupe de moins de
0,20 m (éléments rigides, TQ-BOR-002) est partagée avec l'élément voisin de la même file (joint ≤ 2 cm) : les deux pièces
prennent chacune la moitié de leur longueur totale, et le joint du caniveau quitte celui de la bordure à cet endroit
seulement. Le pilote utilise la 2.1 ; la 1.0 et la 2.0 restent intactes.

### Pilote et contrôle

```
hython recon/generateur/fabriquer_generateur.py --construire-hda --l2            # HDA L1 + L2
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S08_rue_dos_d_ane_passage.yaml --l2 [--rendus] [--verifier-determinisme]
python recon/generateur/validation/controler_L2.py [recon/out/generateur/<scene> ...] [--json SORTIE]
python recon/generateur/validation/faire_rapport_L2.py                           # rejoue tout, rapport du lot
```

Sorties : `recon/out/generateur/<scene>/l2/` (sol_*.npy, niveaux.json, heightfield.json, entites.json,
elements.json, bev.json, vegetation.json, mesures_l2.json, route_l2.usda, manifest_l2.json) et `rendus/` (PNG,
tuiles natives, scene_rendu.usda, manifest_rendus.json). Rendus : Karma XPU, soleil `DistantLight` avec
`inputs:normalize = 1`, ciel lat-long, exposition fixe ; vue de dessus quasi orthographique (caméra perspective à
2 000 m : la caméra orthographique de Karma XPU 22.0.459 ne lance aucun rayon et bloque husk).

## 6. Lot L2b : `rg::marquages::1.0` (marquages de la section courante)

**Correction après contrôle (17/10/2026)** : une zone hachurée interrompue par une autre section (îlot bordé de même
largeur, S_M24, S_M27) est découpée en suites continues (une entité par suite) ; auparavant la zone était jointe
par-dessus l'interruption et lue avec un indice de bande absent (polygone peint hors de la chaussée). Une zone pleine
dès le début du tronçon (largeur ≥ 0,30 m à s = 0) est hachurée (le test `sa > 0` la remplissait d'un aplat).

Chaîne (`fabriquer_l2b.py`, option `--l2b` du pilote) :

```
rg::graphe (1) ─┐
rg::nivellement (NIVEAUX) ─┤
rg::lire_modele (profils 5, ponctuels 4) ─┴─► rg::marquages ─┬─ 1 LIGNES  ─► pj::marquage_solide::1.0 (2 mm) ─┐
pj::gabarits_iisr::1.0 (spec = gabarits_iisr7_pj.json) ─┘          ├─ 2 MARQUES ─► pj::marquage_solide::1.0 (3 mm) ─┴► peinture
                                                                  └─ 3 TABLE (une ligne par marque)
entrées 2 et 3 de pj::marquage_solide : HeightField de rg::nivellement, sol de rg::sol (drapé sur le sol maillé)
```

**Houdini n'invente rien** : modulations RF-MQ-MOD-* (trait, intervalle, recopiés de `regles_route_fr.json` dans le
VEX à la construction), largeurs `largeur_u × u_m` du modèle, intervalles et interruptions du modèle ; passages : zone
du modèle, `n` maximal et `e = (W − 0,5 n)/(n + 1)` (DEF-011, RF-MQ-PP-05) ; flèches, triangles de dos-d'âne,
figurines, lettres : gabarits et glyphes du dossier 08 posés à l'ancrage et au cap du modèle ; zébras : DEF-020,
RF-MQ-HACH-01, -03, RF-MQ-MUS-01 ; jamais de peinture sur une bordure ni sur un caniveau (MQ-DET-010, TQ-MQG-014).
Choix sans règle, déclarés « [G] » comme au lot catalogue : phase des tirets (chaque tronçon commence par un trait ;
trait tronqué gardé s'il fait au moins la moitié d'un trait) ; dégagement de 2u bord à bord entre deux lignes qui
convergent (la discontinue s'arrête ; RF-MQ-MUS-01 par analogie).

- **Lignes** : morceaux (entrée de marquage d'une limite dans une section, moins ses interruptions) réunis en tronçons
  d'une section à l'autre par la clé de limite « bande gauche|bande droite » (S09 : l'axe T'1 garde sa phase de 0 à
  81 m) ; aucune ligne sur une limite bordée.
- **Cellules** : chaque empreinte est construite dans le plan (s, t) puis découpée aux abscisses de rupture du sol
  (sections, points des lois, ralentisseurs, abaissés) et aux limites des bandes (couronne, changements de dévers),
  corps de bordure et caniveaux posés retirés ; une ligne est faite de deux demi-empreintes de part et d'autre de sa
  limite. Drapée sommet par sommet par pj::marquage_solide, la peinture reste à son épaisseur partout (TQ-MQG-004 :
  e_top ± 0,3 mm) ; pas de 5 cm en long sur un dos-d'âne.
- **Symboles** : anneaux du gabarit posés en (x, y) (repère du gabarit : x à droite, y dans le sens de circulation ;
  cap du modèle), convertis en (s, t) (rg_st_local) pour la découpe ; lettres (anneaux à trous) posées telles quelles,
  une ligne de rupture qui les traverserait est comptée (`rg_marquages_traversant_rupture`).
- **Sorties** : polygones plans (x, 0, −y) au contrat de pj::marquage_solide (`pj_entite` = un tiret, une bande de
  passage, une pièce de zébra, un symbole ; `materiau_id` = `peinture_<couleur>_u<classe d'usure>`), table des marques
  (points `m_*`), détail de contrôle (`rg_marquages_sur_bordure`, `_hors_bande`, `_sans_gabarit`, `_degagements`).

pj::symbole_iisr::1.0, pj::marquage_ligne::1.0 et pj::passage_pieton::1.0 ne sont pas utilisées : elles ne découpent pas
les empreintes aux lignes de rupture du sol (calcul : une ligne de 2 mm de 0,10 m sur une couronne à 2 × 2,5 % n'est
plus qu'à 0,75 mm du sol en son milieu ; une bande de passage de 3 mm qui enjambe l'arête haute d'une rampe à 7 % avec
des sommets à 0,125 m de part et d'autre passe 1,4 mm sous le sol) et pj::symbole_iisr lit les gabarits de marquages_geometrie.json,
antérieurs aux corrections du dossier 08 (RAB_D, RAB_G ; TRIANGLE_DOS_ANE et glyphes absents). Aucune nouvelle version
n'est donc nécessaire pour ce lot ; les instances UE (points + prototypes) restent au lot L4.

```
hython recon/generateur/fabriquer_generateur.py --construire-hda --l2b                     # HDA L1, L2, L2b
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S08_rue_dos_d_ane_passage.yaml --l2b [--rendus] [--verifier-determinisme]
python recon/generateur/validation/controler_L2b.py [recon/out/generateur/<scene> ...] [--json SORTIE]
python recon/generateur/validation/faire_rapport_L2b.py [--sans-rendus] [--sans-fabrication]
```

Sorties : `recon/out/generateur/<scene>/l2b/` (empreintes.json, table_marques.json, peinture_*.npy, mesures_l2b.npz,
mesures_l2b.json, route_l2b.usda, manifest_l2b.json) ; rendus soignés dans `rendus/` (`rendu/rendu_l2b.py` : ciel de
Preetham, soleil `normalize = 1`, matériaux de la bibliothèque, caméras dessus, oblique, conducteur, piéton, détail de
l'élément propre à la scène et vues ciblées, planche `planche_<scene>.png`) ; planches d'ensemble (dessus + oblique)
dans `recon/out/generateur/catalogue_rendus/`.

**Étape 1 — la route seule** (décision de l'utilisateur du 17/10/2026 : « il ne doit pas générer la montagne : il doit
générer les routes, la chaussée, etc. dans un premier temps ; la végétation, c'est dans un deuxième temps ») : par
défaut, le rendu ne pose rien hors de l'emprise de la route. Les abords du modèle (« pelouse 6 ») ne sont pas rendus
(GeomSubset lié à un matériau invisible ; `l2/route_l2.usda` reste référencé tel quel) ; la route repose sur un socle
(jupe verticale sous la limite extérieure du profil et coupe nette en s = 0 et s = L, `decor_l2b.socle_jupe`) posé sur
un sol plat neutre et uni (`decor_l2b.sol_plat`, albédo 0,50) ; ciel clair sans nuage ; aucun arbre (ni du modèle ni de
décor), ni relief, ni prairie, ni prolongement. Le décor de l'étape 2 (arbres aux dimensions du modèle, prolongements,
sol de décor, relief, nuages) est gardé, désactivé : `hython fabriquer_generateur.py ... --l2b --rendus --decor-etape2`.
Second contrôle : soleil et ciel du sol neutre liés à lui seul et sans ombre portée (liens UsdLux : plus de trait
d'ombre de la route au nord du profil) ; murs du sol hors de l'emprise (entre deux abords) non rendus ; teintes calées sur
le rendu (enrobé ~32°, bordures et caniveaux gris chaud par échelle d'albédo par canal, piste recalée sur les photos
Panoramax) ; cartes d'usure lues en (s, t) de la route (primvar `st_route` écrite par le rendu) avec un décalage propre à
la scène ; BEV en contraste avec son revêtement voisin ; passages grisés × 0,93.

## 7. Commandes (lot L1)

Depuis la racine du dépôt (`hython` = `C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe`) :

```
hython recon/generateur/fabriquer_generateur.py --construire-hda                  # (re)construit les trois HDA
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S11_rue_courbe_R60.yaml [--hip]
hython recon/generateur/fabriquer_generateur.py MODELE.json                       # entrée modèle (ex. inférence OSM)
hython recon/generateur/fabriquer_generateur.py ... --verifier-determinisme       # second processus, comparaison
python recon/generateur/validation/controler_L1.py [recon/out/generateur/<scene> ...] [--json SORTIE]
python recon/generateur/validation/dessiner_L1.py [<scene> ...] [--tuiles]
python recon/generateur/validation/faire_rapport_L1.py                            # rejoue tout, rapport du lot
```

Une description `.yaml` est compilée par le Python du système (le validateur exige `jsonschema`, absent du Python de
Houdini), dans un environnement débarrassé des variables de Houdini. Sorties : `recon/out/generateur/<scene>/l1/`
(`courbes_controle.json`, `manifest_l1.json`, `plan_l1.png`, détails, profils en long, tuiles ; `generateur_l1.hiplc`
avec `--hip`, à ouvrir après installation des trois HDA, par exemple `hou.hda.installFile` sur chaque dossier
`rg_*.hdalc`).

## 8. Limites connues

- Pas de carrefour : les routes d'un réseau se chevauchent aux nœuds (solveur au lot L3) ; les profils d'extrémité
  sont prêts pour les coupes. *Levé à l'étape 2 : carrefours plans, giratoires et bifurcations (§ 9 à 14).*
- Routes sans géométrie régulière (polylignes OSM) : décalés en onglet ; aux sommets anguleux, les limites intérieures
  se replient (contrôle `inversions`) : régularisation du tracé à prévoir.
- Primitive `parampoly3`, interpolation `cubique_lisse` et transitions d'entrée `lineaire`, `biseau_iisr`,
  `clothoide` : refusées (aucune instance ne les utilise ; le compilateur écrit les transitions en lois de largeur).
- Rampe d'un plateau : le schéma 0.1 ne porte que la longueur totale et la hauteur ; la rampe vient de DEF-034. Une
  rampe dite autrement dans la description n'arrive pas jusqu'ici (à porter dans le schéma 0.2).
- Décroché de bordure d'un changement instantané (ex10, s = 140) : la jonction est déclarée et mesurée ; le retour de
  bordure transversal est fabriqué au lot L2 (files de `rg::nivellement`).
- Lot L2 : une nappe par route (pas de carrefour : lot L3) ; profil de bordure `autre` et piste à un niveau
  intermédiaire entre deux bordures (scène E du plan, ex05) non pris en charge (erreur explicite ; *depuis l'intégration
  de l'étape 2, le compilateur choisit le profil par la vue nominale, § 13*) ; les nappes du
  HeightField sont numérotées par route (une même surface peut changer de numéro à une jonction de sections où le
  nombre de marches change ; les prolongements de la section voisine couvrent les requêtes au voisinage) ; marquages
  au lot L4 ; le volume des fosses d'arbres (9-12 m³) n'est pas modélisé (invisible), la surface plantée l'est.
- Lot L2b : marquages de la section courante seulement (lignes transversales, carrefours, pointe de flèche à 1,50 m
  d'une ligne d'effet : lots L3/L4) ; pas d'instances UE des symboles (lot L4). Le côté transversal d'une avancée qui
  touche le bout de la scène est construit depuis le second contrôle (S03 : 256 m). Les angles des avancées sont des
  pièces d'angle en onglet depuis pj::bordure::2.0.
- BEV : portée par l'abaissé d'une bordure (schéma 0.1) ; un passage qui aboutit de plain-pied (trottoir au niveau de la
  chaussée) ne peut pas en recevoir : interdit RF-MA-BEV-001 signalé par le compilateur (admis pour S_M27, photos sans
  BEV) ; à porter au schéma 0.2 (BEV sur une limite sans bordure).
- Caniveau aux ralentisseurs : caniveau à grille dans l'emprise du caniveau et avaloirs au pied des rampes de plateau
  (moyens [G], règle demandée) ; files fermées par une avancée : un avaloir par file (moyen [G], règle demandée ; le
  caniveau ne contourne pas l'avancée, la description ne le dit pas) ; une bande qui naît en cours de tronçon décroche les rives (pas de biseau de
  terre-plein : les scènes de Meylan décrivent l'îlot dans une zone hachurée de même largeur).

## 9. Lot L3 : carrefours plans (`rg::carrefours`, `rg::carrefours_sol`)

*Ajout du lot L3 (18/10/2026). Plan : PLAN_GENERATEUR § 2.4 (étapes 1 à 6) et § 3 (L3). Rapport :
`validation/RAPPORT_L3.md`. HDA construites par `hda/rg_carrefours/construire.py` (bibliothèque VEX
`hda/rg_carrefours/vex/rg_carrefour.h`, code des wrangles `vex_solveur.py` et `vex_sol.py`, lecture Python
`lecteur_carrefours.py`). Pilote : `fabriquer_carrefours.py` (importe fabriquer_generateur, fabriquer_l2 et
fabriquer_l2b sans les modifier). Contrôle indépendant : `validation/controler_L3.py`.*

```
rg::lire_modele ─(1 routes, 5 profils)─► rg::carrefours ─► 1 routes coupées ─► rg::graphe ─► rg::profils
                                                        ├► 2 profils (+ réduits) ─► rg::graphe, rg::profils, rg::nivellement,
                                                        │                            rg::vers_entites, rg::marquages
                                                        └► 3 SOLVEUR ──────────────┐
rg::nivellement (NIVEAUX) + rg::graphe (références) ───────────────────────────────┴► rg::carrefours_sol
   sorties : 1 sol du carrefour, 2 BEV, 3 ENTITÉS des bordures du carrefour, 4 MARQUES, 5 CONTRÔLES
pilote : sol total = rg::sol + sol du carrefour (subnet « sol_total », sorties 1 sol, 2 BEV ; entrée 1 = rg::graphe) ;
         entités totales = rg::vers_entites + ENTITÉS (subnet « entites_total ») -> pj::bordure, pj::caniveau ;
         MARQUES + rg::marquages (sortie 2) -> pj::marquage_solide (marques, 3 mm, drapé sur le sol total)
```

### `rg::carrefours::1.0` (« RG Carrefours (solveur, coupes) »)

Entrées : 1 routes, 2 profils de `rg::lire_modele` ; paramètres `fichier` (le pilote le relie à celui de
`rg::lire_modele`) et `balayages` (JSON des enveloppes balayées du lot L3a, calculées par le pilote). Seuls les carrefours
de type `plan_*` sont traités (giratoires, mini-giratoires et bifurcations : lots giratoires et autoroutes).

1. **Branches** (VEX) : repère de la branche à la limite de la chaussée abordée (`s_front` = `s_frontiere_m` du modèle) ;
   bords de chaussée = limites extérieures de la première et de la dernière bande `niv_reference = chaussee` (voies,
   bandes cyclables, bandes dérasées, zones neutralisées ; trottoir, berme, terre-plein à l'extérieur) ; îlots de la bande
   médiane (bandes non « chaussee » entre les bords).
2. **Nez des îlots du profil** : arrondis au rayon du modèle (`ilots[].nez.rayon_m`, défaut RF-GV-ILO-015 : 0,50 m), de
   longueur égale au rayon, pointe à `s_front − retrait` ; retrait = premier contact des balayages faisables (lot L3a ;
   le pilote ajoute 15 m d'approche et de sortie dans l'axe des branches) avec la bande de l'îlot prolongée + 0,30 m,
   **plafonné** pour garder le refuge d'un passage qui traverse l'îlot (bande + rampant DEF-031) ; le retrait requis et
   le plafonnement sont rangés (`nez_retrait_requis`, `nez_limite_refuge`).
3. **Coins** (droit de A, gauche de B, branches consécutives dans l'ordre trigonométrique) : congé de rayon
   `coin_droit.rayon_m` (DEF-010 à défaut, signalé), tangent aux **bords réels** (lois de largeur suivies : ouverture
   d'îlot à 1/15 près du coin), itéré au point de tangence ; arcs au pas angulaire ≤ 0,8° (rupture ≤ 0,4° au point de
   tangence) et flèche ≤ 0,5 mm ; amorces droites de 3 m ([G]) sur les deux branches ; bords alignés (angle > 179°) :
   bordure droite d'une embouchure à l'autre.
4. **Coupes** : route raccourcie à `s_end` (fin de la chaussée de la branche) ; au-delà de `s_cut` de chaque côté, profil
   réduit `<profil>~cG` / `~cD` / `~cGD` (bandes extérieures retirées, bord de chaussée sans bordure ni marquage de rive),
   transition instantanée : `rg::nivellement` ne pose aucun retour (le trottoir retiré est hors de l'emprise commune).
5. **Frontière** fermée (groupe `frontiere`) : embouchures en `s_end` (partie 0, joints) et bords + congés (partie 1).

Sortie 3 **SOLVEUR** (API pour les lots giratoires, marquages et signalisation) :

| Élément | Géométrie | Attributs |
|---|---|---|
| groupe de points `branche` | centre du carrefour | `carrefour`, `branche`, `route`, `rang`, `azimut`, `regime`, `ligne_type`, `ligne_distance`, `s_front`, `s_end`, `s_cut_g`, `s_cut_d`, `s_tan_g`, `s_tan_d`, `t_g`, `t_d` (bords de chaussée), `t_ext_g`, `t_ext_d`, `w_g`, `w_d` (largeurs extérieures), `bordure_g/d`, `vue_g/d`, `mat_ext_g/d`, `Pf` (point de la référence en `s_front`, local), `Pe` (en `s_end`), `dir` (vers le centre), `nrm` (gauche), `coin_g`, `coin_d`, `nez_c`, `nez_retrait`, `nez_retrait_requis`, `nez_limite_refuge`, `nez_intrusion_x`, `nez_balayage` |
| polylignes `coin` | face de la bordure de coin (Houdini, Y = 0), côté haut à gauche, de B vers A | points `u` (abscisse), `partie` (0 amorce de B, 1 congé, 2 amorce de A) ; `coin`, `branche_a`, `branche_b`, `route_a`, `route_b`, `rayon`, `droit`, `rayon_defaut`, `centre_arc`, `angle_deg`, `bordure`, `vue`, `w_a`, `w_b`, `mat_ext`, `ref_ext`, `g_a`, `g_b` (dévers extérieurs), `s_cut_a`, `s_cut_b`, `bord_a`, `bord_b` (bords réels entre embouchure et tangence), `n_a`, `n_b`, `tangente_hors` |
| polylignes `nez` | face de la bordure du nez, de la limite droite à la limite gauche de l'îlot (îlot à gauche) | `branche`, `route`, `s_end`, `t_g`, `t_d`, `bande`, `bordure`, `vue`, `materiau`, `rayon` |
| polylignes `embouchure` | coupe en `s_end`, un sommet par limite du bord gauche au bord droit | points `t`, `limite` ; `branche`, `route`, `s_end` |
| polygone `frontiere` | frontière fermée | points `partie` (0 joint, 1 voie) ; `carrefour` |
| `ilot`, `passage`, `passage_libre`, `ligne`, `trajectoire`, `balayage` | lus dans le modèle et dans `balayages` | voir `lecteur_carrefours.py` |

### `rg::carrefours_sol::1.0` (« RG Carrefours (sol, bordures, marques) »)

Entrées : 1 NIVEAUX (`rg::nivellement`), 2 profils coupés, 3 SOLVEUR, 4 références (`rg::graphe`).

- **Faces de bordure** : coins, nez, îlots du cœur (`ilots[]` sans `porte_par_profil`, sens trigonométrique, densifiés
  à 0,5 m, boucle ouverte en un sommet aligné hors des passages) ; base de la table de `pj::bordure` ; **abaissés** là où
  la face coupe la bande d'un passage (axe du modèle ± longueur des bandes / 2 ; passages sans route : repère de la voie
  de coin la plus proche) : vue DEF-031 (0,02), rampants 2,40 m réduits au bout de la file (signalé sous 1,50 m).
- **Sol** : contour (embouchures, bords réels, amorces, bords extérieurs des trottoirs de coin), lignes de contrainte
  (faces, arrières des bordures = face + base − 12 mm, TQ-BOR-007), Triangulate 2D (arête 0,5 m, angle 25°) ; classes :
  `carrefour_chaussee`, `sous_bordure` (chaussée prolongée sous la bordure, pente de la voie voisine),
  `carrefour_trottoir` (tête − 4 mm + dévers depuis l'arrière, TQ-SOL-013 (5) ; abaissés : trottoir abaissé sur toute sa
  largeur, rampants latéraux), `carrefour_accotement` (sans bordure : pied + dévers), `carrefour_ilot` (nez : plan de la
  bande d'îlot de la branche ; îlots du cœur : tête − 4 mm, − 4 cm s'ils sont plantés), murs (`mur`, invisibles) aux
  marches. Z imposés du modèle unique (`rg_coupe`) aux embouchures, sur les bords réels des branches et aux coupes des
  trottoirs ; pied des coins = Z bas du modèle sur les amorces, linéaire sur le congé ; chaussée libre : interpolation
  harmonique (initialisation 1/d⁴ puis Gauss-Seidel sur-relaxé, 400 itérations, ω = 1,8). Contrat de `rg::sol`
  (z_type 10, murs 14 ; `s` = 10 000 + x, `t` = y pour les cartes d'usure du rendu).
- **BEV** derrière chaque abaissé (DEF-031 : 0,50 m du nez, 0,5875 m, 0,40 m si trottoir < 1,90 m), 3 mm au-dessus du sol.
- **ENTITÉS** : contrat de `rg::vers_entites` (identifiant `K-<coin|nez|îlot>`, intervalles courant / chartière / bateau,
  pièce d'abaissé T2 -> T2_bateau, `niv_s`, `niv_z_pied`, `niv_z_tete`, caniveau vide).
- **MARQUES** : lignes transversales du modèle (CÉDEZ T'2 0,50 ; STOP continue 0,50 ; EFFET_FEUX T'2 0,15 :
  RF-MQ-CED-01, RF-MQ-STOP-01, RF-MQ-FEU-01, RF-MQ-MOD-T'2 ; motif centré, [G]) et bandes des passages sans route
  (DEF-011) au contrat de `pj::marquage_solide`. Lignes de guidage, figurines, zones de sas et chevrons : lot L4.
- **CONTRÔLES** : faces de bordure avec `pied_z`, `ab0` / `ab1` / `abv` / `abr`, `exterieur`, `arriere`, `base`.

Exports du pilote : `<scene>/l3/carrefours.json` (branches, solveur, faces, entités, balayages résumés),
`l3/mesures_l3.json` (raccords sol du carrefour / sol des branches : écart vertical, bords libres hors bord extérieur),
`l3/manifest_l3.json` ; les sorties L1, L2, L2b et les rendus comprennent le carrefour.

```
hython recon/generateur/fabriquer_carrefours.py recon/generateur/scenes_carrefours/J5_carrefour_complexe.yaml [--rendus]
                                                [--verifier-determinisme] [--sans-balayages]
python recon/generateur/validation/controler_L3.py [recon/out/generateur/<scene> ...] [--json SORTIE]
```

Limites (lot L3) : branches tracées vers le centre (extrémité « fin ») et ligne de référence droite près du carrefour ;
pas de ralentisseur ni de caniveau dans le carrefour (un coin ne prolonge pas le caniveau d'une branche) ; chaussée du
cœur par interpolation harmonique (le profil en toit de la route prioritaire n'est pas prolongé tel quel) ; deux branches
dont les profils diffèrent au point commun de leurs embouchures (J2 : bande dérasée de la RD contre voie de la VC)
laissent une marche de 2 cm à ce point ; passages sans route : bandes rectangulaires dans le repère de la voie (non
découpées) ; un seul carrefour par route, à son extrémité « fin ».

## 10. Lot L4 : marquages des carrefours plans (`rg::marquages_carrefour::1.0`)

*Détail complet : `hda/rg_marquages_carrefour/README_L4.md` ; rapport : `validation/RAPPORT_L4.md`.* Construite par
`hda/rg_marquages_carrefour/construire.py` (VEX dans `vex_l4.py`, lecture du modèle dans `lecteur_marquages_carrefour.py`,
bibliothèques `rg_geometrie.h`, `rg_niveau.h`, `rg_marquage.h`, `rg_carrefours/vex/rg_carrefour.h` recopiées en tête des
wrangles).

```
rg::carrefours (3 SOLVEUR) ─┐
rg::nivellement (1 NIVEAUX) ┼─► rg::marquages_carrefour ─► 1 LIGNES ─► pj::marquage_solide (2 mm)
rg::graphe (1 références) ──┤                          ├► 2 MARQUES ─► + MARQUES de rg::marquages et de rg::carrefours_sol
rg::marquages (1 + 2) ──────┘                          │               ─► pj::marquage_solide (3 mm)
                                                       ├► 3 DONNÉES (trajectoires, conflits, zone de conflit, voies, guidage)
                                                       └► 4 CONTRÔLES (LIGNES d'entrée : rg_l4_retire, rg_l4_raison)
pilote : les ponctuels « fleche » ancrés à un carrefour sont retirés de l'entrée 4 de rg::marquages (l'HDA les pose)
```

- **Trajectoires voie à voie** (RF-GV-TRJ-006) : droite – arc – droite sur l'axe réel des voies, rayon ≥ rayon d'axe
  minimal du VL (5,467 m, lot L3a) ; TAD : rayon du coin + écart axe-bord ; TAG opposés non guidés : rayon commun qui
  sépare leurs axes ; TAG guidés : plus petit rayon qui garde la caisse de son côté de la ligne de guidage.
- **Ligne de guidage** T'2 0,10 (RF-MQ-GUI-01, RF-MQ-CAR-03, ARB-08) seulement là où le modèle la décrit
  (`guidage.materialise` : TAG à l'indonésienne).
- **Conflits** (divergence, convergence, croisement ; `meme_phase`) ; **zone de conflit** (cœur + approches jusqu'au bord
  amont des lignes d'arrêt, RF-MQ-CAR-02 / -04) sans ligne longitudinale (morceaux retirés ou coupés).
- **Flèches** au gabarit exact du dossier 08 (DEF-017, ARB-11, RF-MQ-DIR-*) : pointe de la dernière à 1,50 m de la
  ligne, 20 m entre pointes, sur voie formée et droite ; **figurines vélo** des sas (RF-MQ-SAS-01) ; **axe prioritaire**
  prolongé et rives interrompues au droit des affluentes (RF-MQ-CAR-01, RF-MQ-SC-11).
- Paramètres : `fichier` (relié à `rg::lire_modele`), `spec` (gabarits du lot L2b), véhicule de projet (`vl`,
  `r_min_vehicule` 5,467, `largeur_vehicule` 1,80), angle d'un tout-droit 25° [G], `fleche_arc` 0,5 mm, pas angulaire
  0,8°, largeurs des lignes, T'2 0,50 / 0,50, flèches (fraction de largeur 0,99, rectitude 0,5° [G]), pas de
  densification 0,25 / 0,10 m [G], figurine `VELO`, `usure_peinture` (lue sur les LIGNES de `rg::marquages`).
- Exports (`<scene>/l4/`) : `trajectoires.json`, `conflits.json`, `zone_conflit.json`, `guidage.json`,
  `graphe_voies.json` (`rg_graphe_voies/0.1` : voies, connecteurs, zones, passages, étiquettes ≤ 32), `marques_l4.json`,
  `lignes_retirees.json`, `mesures_l4.json`, `manifest_l4.json`. Contrôle : `validation/controler_L4.py`,
  `dessiner_L4.py`, `faire_rapport_L4.py`.

## 11. Lot L5 : giratoires (`rg::giratoires::1.0`, `rg::giratoires_sol::1.0`)

*Détail complet : `hda/rg_giratoires/README_GIRATOIRES.md` ; rapport : `validation/RAPPORT_giratoires.md`.* Le giratoire
réutilise le cœur des carrefours plans : `rg::giratoires` traduit l'anneau en coins au contrat de `rg::carrefours`, et
`rg::carrefours_sol` (§ 9, inchangée) fabrique le sol de la chaussée annulaire, des bouches et des trottoirs de coin,
les bordures des raccordements et les lignes CÉDEZ. Les îlots sont **posés** sur ce sol par `rg::giratoires_sol`.

```
rg::lire_modele ─► rg::carrefours ─(1 routes, 2 profils, 3 SOLVEUR)─► rg::giratoires ─► 1 routes coupées, sans anneaux ─► rg::graphe …
                                                                                   ├► 2 profils (+ réduits ~cG / ~cD / ~cGD)
                                                                                   ├► 3 SOLVEUR fusionné ─► rg::carrefours_sol
                                                                                   └► 4 GIRATOIRES ─┐
                                    sol sans îlots (rg::sol + rg::carrefours_sol, sortie 1) ───────┴► rg::giratoires_sol
   sorties : 1 sol des îlots, 2 BEV, 3 ENTITÉS (bordures des îlots), 4 MARQUES (contour du dôme, lignes de l'anneau), 5 CONTRÔLES
```

- `rg::giratoires` : bord intérieur de la chaussée annulaire `Rg − la` ; rayons des limites du profil d'anneau ;
  raccordements d'entrée `Re` et de sortie `Rs` (ACI tableau 1, RF-GV-GIR-003) tangents au bord réel de la branche
  (évasement compris, itéré) et au cercle `R0` ; coins (amorce 3 m [G], congé de sortie, arc de l'anneau, congé d'entrée,
  amorce) ; coupes des branches (code L3) ; routes d'anneau retirées ; SOLVEUR fusionné avec celui des carrefours plans.
  Paramètres : `fichier`, `amorce` 3 [G], `rampant_passage` 2,40 (DEF-031), `garde_passage` 0,10 [G], `fleche` 0,0005,
  `pas_angulaire_max` 0,8°.
- `rg::giratoires_sol` : couronne franchissable (bordure du profil, A2 0,03 m ; pente 5 %, RF-GV-GIR-006 ; pavés), îlot
  central (A2, gazon, tête − 4 cm, TQ-SOL-013 (7)), dôme du mini-giratoire (10 cm, relief 2 cm, RF-GV-GIR-016),
  îlots séparateurs ACI tableau 2 (I2, refuges abaissés avec BEV, DEF-031) ; contour T'2 3u du dôme (RF-MQ-GIR-02) et
  lignes de l'anneau interrompues aux bouches (RF-MQ-GIR-04).
- Exports (`<scene>/l5/`) : `giratoires.json` (anneau, branches, congés, faces des îlots, coupes radiales, entités, BEV,
  marques ; clés triées depuis l'intégration), `mesures_l5.json`, `manifest_l5.json` ; et ceux du lot L3 (`l3/`).
  Contrôle : `validation/controler_giratoires.py`, `faire_rapport_giratoires.py`.

## 12. Lot « autoroutes » : `rg::autoroute::1.0` (retenues, bifurcations, musoirs)

*Rapport : `validation/RAPPORT_autoroutes.md`.* Construite par `hda/rg_autoroute/construire.py` (VEX dans
`vex_autoroute.py`).

```
rg::profils (1 limites) ─┐
rg::sol (1 sol) ─────────┼─► rg::autoroute ─► 1 SOL (bretelles raccordées en Z + musoirs + terre-plein latéral) = sol total
zones + nœuds (lire 3+2) ┤                 ├► 2 ÉQUIPEMENTS (DBA / GBA / LBA / MVL, glissières GS2 / GS4 / DE2) ─► USD /Monde/Equipements
rg::graphe (1 réf.) ─────┘                 ├► 3 MARQUES (aplat de pointe, chevrons « 2 pour 1 », moitiés de contour) ─► pj::marquage_solide
                                           └► 4 CONTRÔLES (détail ra_* : raccord, musoirs, séparateurs)
```

- **Séparateurs** le long des limites `separateur` du modèle (`{type: GBA|DBA|LBA|MVL|glissiere, largeur_m, modele?}`) :
  contours béton et pièces des glissières recopiés de `assets/specs/route/catalogue_assets_route.json` (Cerema, Dispositifs
  de retenue, tableaux 15-16 p. 32 ; fiches GS2, GS4, DE2) ; GS2 par défaut [G] ; seuil GBA / DBA 0,55 m, encastrement
  0,05 m [G].
- **Bifurcations** (carrefours `bifurcation` du modèle) : raccord vertical de la bretelle (dz au point de jonction, profil
  en long parallèle [G]) ; sol du musoir en enrobé, terre-plein latéral en gazon de plain-pied (pas de bordure sur
  autoroute) ; aplat de pointe sous 0,30 m et chevrons pointés vers le conducteur, 2u non peints contre le contour
  (DEF-020, RF-MQ-HACH-01 à -03, RF-MQ-MUS-01) ; moitiés manquantes des lignes de contour au droit du musoir.
- u = 7,5 cm sur autoroute (RF-MQ-U-01). Exports (`<scene>/autoroute/`) : `musoirs.json`, `equipements.json`,
  `manifest_autoroute.json` ; couche USD `/Monde/Equipements` de `l2/route_l2.usda` (double face). Contrôle :
  `validation/controler_autoroutes.py`, `faire_rapport_autoroutes.py`.

## 13. Lot « bordures » : 32 types du catalogue route_fr (`pj::bordure::2.1`, `pj::caniveau::2.2`)

*Rapport : `validation/RAPPORT_bordures.md` ; données : `commun/bordures_catalogue.py`.* Depuis l'intégration, toute la
chaîne connaît les types ajoutés :

- **Table des profils étendue** (`bordures_catalogue.construire_table_etendue`) : table de `pj::bordure` (inchangée
  pour ses profils) complétée de T4, I3, I4, P4, CS4, GR_T1, GR_T2, GR_P1, GR_A1, GR_A2, GR_P3, T2_basse, T3_basse,
  T2_surbaissee, T3_surbaissee, P1_basse, ACCESBUS (cotes RF-AS-profil_* ; granits A1, A2, P3 : contour du mesh du
  catalogue). Figée dans `rg::nivellement` (`table_profils`), donc aussi dans `rg::carrefours_sol` et
  `rg::giratoires_sol`, et dans `pj::bordure::2.1` / `pj::caniveau::2.2`.
- `pj::bordure::2.1` (`hda/pj_bordure_v2_1`) : réseau de la 2.0, table étendue. `pj::caniveau::2.2`
  (`hda/pj_caniveau_v2_2`) : correctifs de la 2.1, face parasite du CC2 retirée, CS4, prototypes espacés de 2 m. Les
  versions 1.0, 2.0 et 2.1 restent intactes.
- `rg::vers_entites` : file coupée à chaque changement de type (`decouper_profils`, parts `id.1`, `id.2`…), boucles
  ouvertes en un sommet aligné ; paramètres `pieces_abaisse` (posé par `fabriquer_l2.py` : T2 → T2_bateau,
  T3 → T3_surbaissee, T2_basse → T2_surbaissee, T3_basse → T3_surbaissee, A2 → A2 ; même base contrôlée) et
  `vue_max_bateau` (0,05 : RF-MA-TRO-015).
- Description : mots de profil ajoutés au vocabulaire, énumérations du schéma étendues, saut de niveau sans règle
  (profil « autre ») résolu par la vue nominale (`bordures_catalogue.resoudre_saut_de_niveau`, appelé par
  `commun/profil.py`), entrée charretière à 0,03 m (`bordures_elements.json` abaisses.entree_charretiere, bornée par
  RF-MA-TRO-015).
- `elements.json` : `asset_id` et `asset_motif` (mesh du catalogue route_fr ou pièce sur mesure), `angle_debut`,
  `angle_fin`, `angle_sens` (sortant / rentrant), `angle_deviation_deg`, `sens`, `fleche_mm`, `proto_type`,
  `prototype_pj`. Contrôle : `validation/controler_bordures.py`.

## 14. Chaîne complète : une seule commande, description → rendu (intégration de l'étape 2)

`fabriquer_generateur.py` choisit la chaîne d'après le modèle compilé (`familles()`), puis compose les insertions des
pilotes de lots, qui sont devenus des bibliothèques (`fabriquer_carrefours.reseau(avant_l2b)`,
`fabriquer_giratoires.inserer`, `fabriquer_marquages_carrefour.inserer`, `fabriquer_autoroutes.inserer_sol` /
`inserer_marques`, et leurs exports et caméras) :

| Famille (modèle) | Détectée par | Réseau ajouté à L1 + L2 + L2b | Sorties ajoutées |
|---|---|---|---|
| aucune (rue, route) | — | chaîne de l'étape 1, inchangée | `l1/`, `l2/`, `l2b/` |
| `carrefours` | carrefour `plan_simple`, `plan_ilots`, `plan_feux` | `rg::carrefours`, `rg::carrefours_sol` (§ 9) + `rg::marquages_carrefour` (§ 10) ; balayages VL et bus 12 m (lot L3a) | `l3/`, `l4/` |
| `giratoires` | carrefour `giratoire`, `mini_giratoire` | `rg::carrefours`, `rg::carrefours_sol` + `rg::giratoires`, `rg::giratoires_sol` (§ 11) | `l3/`, `l5/` |
| `autoroute` | carrefour `bifurcation`, ou séparateur DBA / GBA / LBA / MVL / glissière | `rg::autoroute` (§ 12) après le sol | `autoroute/`, couche USD Equipements |

Les familles se composent (carrefours plans + giratoires sur le même cœur L3 ; autoroute insérée avant L2b par le
crochet de `fabriquer_carrefours.reseau`) ; une composition sans scène de contrôle dédiée est signalée à la fabrication.
Le contournement de `pj::marquage_solide` est décidé sur son entrée réelle (`fabriquer_l2b.cuire`, marques des
carrefours, giratoires et musoirs comprises) ; `rg::marquages_carrefour` y est cuite et contrôlée d'abord.

```
hython recon/generateur/fabriquer_generateur.py --l2b --construire-hda          # (re)construit toutes les HDA
hython recon/generateur/fabriquer_generateur.py SCENE.yaml [SCENE.yaml ...] --complet   # = --l2b --rendus
hython recon/generateur/fabriquer_generateur.py ... --l2b --verifier-determinisme       # second processus, comparaison
         [--vues dessus,conducteur | --vues toutes] [--decor-etape2] [--sortie DOSSIER]
python recon/generateur/validation/comparer_integration.py RÉFÉRENCE recon/out/generateur [SCENE ...] [--json F]
python recon/generateur/validation/faire_rapport_integration.py              # rapport de l'intégration
```

Rendus (route seule, sol neutre, ciel simple et soleil) : 2 vues par scène (dessus, conducteur à 1,20 m dans une voie
entrante), 3 pour les scènes phares J5, G1, A3 (+ oblique 3/4) ; planche ≤ 1092 px par scène
(`<scene>/rendus/planche_<scene>.png`) ; vue de dessus centrée sur le carrefour, le giratoire ou le musoir. Une
description peut donner sa vue de dessus (`<scene>.vues.json` : largeur, résolution, abscisse du sujet ; B01). Les
pilotes de lots restent utilisables seuls (mêmes sorties, rendus propres à chaque lot).

## 15. Correction de l'étape 2 (contrôle indépendant, 18/10/2026)

*Rapport : `validation/RAPPORT_correction_etape2.md` ; contrôles ajoutés : `validation/controler_correction_etape2.py`.*

- **Une seule source de trajectoires.** Les balayages des véhicules (lot L3a) qui placent les nez des îlots sont calculés
  sur les trajectoires FINALES de `rg::marquages_carrefour` (L4), et non plus sur les géométries du compilateur
  (`fabriquer_generateur.balayages_trajectoires_l4`, `fabriquer_carrefours.balayages_l4`). Les nez dépendent des
  balayages et la fin des branches (`s_end`) des nez : passes successives jusqu'à ce que les balayages ne changent plus
  (journal `l3/manifest_l3.json` → `balayages_passes`, contrôle `l4/manifest_l4.json` → `trajectoires_balayees_identiques`) ;
  balayages complets dans `l3/balayages.json`. Véhicules par mouvement : `trajectoires[].usagers` (clé de description
  `vehicule`) ; le bus suit les axes de voie de la trajectoire L4 avec un arc de son rayon minimal.
- **L4** : TAG guidés à `garde_guidage` (0,725 m) du bord de la peinture le long des raccords et de l'oblique
  (RF-GV-TRJ-006, VU p. 142) ; rayon des TAG non guidés tenu entre les frontières du carrefour (`s_front`, indépendant
  des nez) ; séparation des TAG opposés cherchée seulement s'ils partagent une phase.
- **rg::carrefours** : une section qui commencerait à moins de 1 mm de `s_end` est absorbée par la précédente.
- **rg::carrefours_sol** : pente du dessous de bordure des coins prise au bord de chaussée réel en `s_tan` (bords évasés) ;
  bandes des passages des branches **prolongées dans les congés de coin** : la série de bandes des groupes extrêmes (zones
  du modèle, attributs `pp_zxy`, `pp_zn`, `pp_zid` des points `passage` lus par `lecteur_carrefours.py` et
  `lecteur_giratoires.py`) continue au-delà du bord de chaussée de la section, chaque bande découpée à e de la première
  face rencontrée (congé, nez, îlot du cœur) ; entités `MQ_<marquage>_xg|xdNN`.
- **rg::marquages** : zébras et aplats interrompus à 0,50 m des passages (paramètre `pp_degagement_zebra`, RF-MQ-PP-03) ;
  zone hachurable bornée aussi par les lignes peintes au-delà des limites de sa bande (demi-bandes d'une zone centrale
  scindée) et, là où sa ligne est interrompue, par la marge de la ligne la plus proche sur la même limite.
- **rg::autoroute** : demi-lignes de contour des musoirs bornées à la moitié de l'écart entre les deux bords.
- **Pilote** : réseau reconstruit pour chaque scène (sorties indépendantes de l'ordre des scènes).
- **Compilateur** : lignes de bord d'une bande centrale qui naît de largeur nulle (ouverture) : la ligne de droite commence là
  où les deux lignes se touchent (interruption sur la limite extérieure de la demi-bande droite) ;
  refuges des terre-pleins plantés revêtus au droit des passages (opération `revetir`,
  RF-OBS-ILO-01) ; ligne arrière du sas non doublée ; rives de l'anneau en continue 3u (RF-MQ-GIR-01 / -04) ; passage
  de giratoire avec retrait dit ; îlot franchissable du mini-giratoire en retrait de 5u ; entrées de giratoire à 2 voies.
- **Scènes** : J5 refaite (voies de TAG face à face, 4 phases, passages à 5 m, coins de 6 m, bus en tout droit) ; J6
  (second carrefour complexe) et G4 (giratoire multivoie) ajoutées ; G3 (îlots 2,00 m, passages à 5 m) ; A3 (rive
  continue 3u sur les 35 m avant l'interruption de la BAU, RF-MQ-SC-13) ; J4 (bus sur l'avenue, passage nord à 6 m).
- **Limites restantes** (rapport § 6) : nez sud de J4 dans le balayage des TAG ; figurines des bandes cyclables posées
  sans les exclusions du modèle (J6) ; bandes des passages voisins d'un îlot directionnel dimensionnées sur la voie peinte
  et non jusqu'à la face de l'îlot ; deux trous de rive dans A4 ; pas de caniveau dans les coins.
