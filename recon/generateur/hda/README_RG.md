# recon/generateur/hda : HDA `rg::*` du générateur de routes (lots L1, L2 et L2b)

*`recon/generateur/hda/README_RG.md` — 17/10/2026. Plan : `recon/generateur/PLAN_GENERATEUR.md` § 2.3 et § 3 (L1, L2, L4 pour la section courante = L2b).
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
  commun/vex/rg_marquage.h         lot L2b : empreintes en (s, t), découpe en cellules (lignes de rupture du sol, corps de
                                   bordure et caniveaux retirés), attributs du contrat de pj::marquage_solide
  rg_marquages/construire.py, marquages.vfl, rg_marquages.hdalc/     lot L2b
  rg_marquages/gabarits_iisr7.py, gabarits_iisr7_pj.json   gabarits et glyphes du dossier 08 au format de pj::gabarits_iisr
recon/generateur/fabriquer_generateur.py    pilote hython (description .yaml ou modèle .json -> courbes de contrôle ;
                                            --l2 : sol, bordures, caniveaux ; --rendus : rendus Karma XPU)
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
  sont prêts pour les coupes.
- Routes sans géométrie régulière (polylignes OSM) : décalés en onglet ; aux sommets anguleux, les limites intérieures
  se replient (contrôle `inversions`) : régularisation du tracé à prévoir.
- Primitive `parampoly3`, interpolation `cubique_lisse` et transitions d'entrée `lineaire`, `biseau_iisr`,
  `clothoide` : refusées (aucune instance ne les utilise ; le compilateur écrit les transitions en lois de largeur).
- Rampe d'un plateau : le schéma 0.1 ne porte que la longueur totale et la hauteur ; la rampe vient de DEF-034. Une
  rampe dite autrement dans la description n'arrive pas jusqu'ici (à porter dans le schéma 0.2).
- Décroché de bordure d'un changement instantané (ex10, s = 140) : la jonction est déclarée et mesurée ; le retour de
  bordure transversal est fabriqué au lot L2 (files de `rg::nivellement`).
- Lot L2 : une nappe par route (pas de carrefour : lot L3) ; profil de bordure `autre` et piste à un niveau
  intermédiaire entre deux bordures (scène E du plan, ex05) non pris en charge (erreur explicite) ; les nappes du
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
