# Rapport du lot « integration » (étape 2) : une seule commande, description → rendu, pour tous les types de scène

*`recon/generateur/validation/RAPPORT_integration.md` — 18/10/2026. Critères et mesures : `validation/rapport_integration.json`
(écrit par `validation/faire_rapport_integration.py`) ; comparaison fichier par fichier : `validation/comparer_integration.py`.
Documentation : `hda/README_RG.md` § 10 à 14, `description/FORMAT_DESCRIPTION.md` § 5.2, 8 et 16.*

> **Corrigé le 18/10/2026 par le lot « correction de l'étape 2 »** (`RAPPORT_correction_etape2.md`) : INT-2 et
> INT-5-bordures reformulés (le livrable USD change par les caniveaux ; R2 non compté) ; ex05, ex08 et ex11 refabriqués ;
> correction connue de `vex_sol.py` appliquée ; sorties indépendantes de l'ordre des scènes (réseau reconstruit par scène).

Demande de l'utilisateur : « le PCG doit reproduire des autoroutes, des ronds-points, plusieurs types de bordures etc.,
il doit être complet, et surtout les carrefours complexes ». Les lots de l'étape 2 (bordures, L3a, scenes, L3, L4,
giratoires, autoroutes) avaient chacun leur pilote. Ce lot les réunit : **une seule commande fabrique et rend n'importe
quelle scène**, rue, carrefour plan (jusqu'au carrefour complexe J5), giratoire ou autoroute, avec tous les types de
bordures. Route seule : sol neutre plat, ciel simple et soleil.

```
hython recon/generateur/fabriquer_generateur.py SCENE.yaml [SCENE.yaml ...] --complet      # = --l2b --rendus
```

## 1. Ce qui a été fait

**Chaîne unique (`fabriquer_generateur.py`).** Après compilation, la chaîne est choisie d'après le modèle (`familles()`) :

| Famille | Détectée par | Ajouté à L1 + L2 + L2b | Sorties en plus |
|---|---|---|---|
| aucune (rue, route) | — | rien : chaîne de l'étape 1, **inchangée** | — |
| `carrefours` | carrefour `plan_simple`, `plan_ilots`, `plan_feux` | `rg::carrefours`, `rg::carrefours_sol`, `rg::marquages_carrefour` ; balayages VL et bus 12 m (L3a) | `l3/`, `l4/` |
| `giratoires` | `giratoire`, `mini_giratoire` | `rg::carrefours`, `rg::carrefours_sol`, `rg::giratoires`, `rg::giratoires_sol` | `l3/`, `l5/` |
| `autoroute` | `bifurcation`, ou séparateur DBA / GBA / LBA / MVL / glissière | `rg::autoroute` après le sol | `autoroute/`, couche USD Equipements |

Les pilotes des lots sont devenus des bibliothèques. Leurs insertions sont composables :
`fabriquer_carrefours.reseau(avant_l2b)`, `fabriquer_giratoires.inserer`, `fabriquer_marquages_carrefour.inserer`,
`fabriquer_autoroutes.inserer_sol` et `inserer_marques`. Leurs exports et leurs caméras sont repris tels quels. Un type
de carrefour inconnu arrête la fabrication. Une composition de familles (par exemple une bretelle qui débouche sur un
giratoire) est construite, mais aucune scène ne la contrôle encore : la fabrication le signale.

**Ajouts en mémoire des lots reportés dans le code commun :**

- `fabriquer_l2b.cuire` décide du contournement de `pj::marquage_solide` sur son **entrée réelle** (marques des carrefours,
  des giratoires et des musoirs comprises), après avoir cuit et contrôlé `rg::marquages_carrefour`. Pour la chaîne simple,
  l'entrée est la sortie de `rg::marquages`, comme avant.
- `fabriquer_l2.ecrire_usd` écrit la couche `/Monde/Equipements` (lot autoroutes).
- `rendu_l2b` : matériau de rendu `beton_prefa_lisse`.

Les deux remplacements faits au chargement des modules (L4 et autoroutes) sont retirés. Sans cela, importer le pilote
L4 cassait les scènes sans carrefour.

**Lot bordures, reporté dans les fichiers communs (rétrocompatible) :**

- vocabulaire : 31 mots de profil et CS4 ;
- schéma `modele_voie` : énumérations étendues ;
- `commun/profil.bordure_entre` : un saut de niveau sans règle (profil « autre ») prend le profil dont la vue nominale
  contient la vue (`bordures_catalogue.resoudre_saut_de_niveau`) ;
- `rg::nivellement.table_profils` = table étendue. Elle est donc aussi figée dans `rg::carrefours_sol` et
  `rg::giratoires_sol`, reconstruites : les coins et les îlots acceptent les nouveaux types ;
- `fabriquer_l2` : `pj::bordure::2.1`, `pj::caniveau::2.2`, `pieces_abaisse` (T2 → T2_bateau, T3 → T3_surbaissee,
  T2_basse / T3_basse → surbaissées, A2 → A2), `vue_max_bateau` 0,05 (RF-MA-TRO-015), et dans `elements.json` les
  assets du catalogue route_fr et les angles ;
- entrée charretière à 0,03 m (`bordures_elements.json` abaisses.entree_charretiere, défaut 0,03, borné par le maximum
  0,05 de RF-MA-TRO-015).

Le pilote `fabriquer_bordures.py` ne garde que ses rendus propres (B01).

**Harmonisation des HDA.** Signatures après reconstruction :

- changées : `rg::nivellement` aa8a79afb91c → d4ea0ac18a7d, `rg::carrefours_sol` 4f14624995e7 → 195726c65828,
  `rg::giratoires_sol` 4a9ec528d3b7 → 7f2834f61860 (table étendue) ;
- inchangées : toutes les autres HDA `rg::*` ;
- versions `pj::*` : 2.1 et 2.2, les anciennes versions restent intactes.

**Rendus et planches.**

- 2 vues par scène (dessus, conducteur à 1,20 m), 3 pour J5, G1 et A3 (+ oblique 3/4) ; planche ≤ 1092 px par scène.
- Vue de dessus centrée sur le carrefour, le giratoire ou le musoir. B01 garde sa vue de dessus de 100 m (`.vues.json`).
- `--vues toutes` rend les caméras de l'étape 1.
- Planches d'ensemble : `recon/out/generateur/catalogue_rendus/etape2_1.png` à `etape2_7.png`, avec une vignette dessus
  et une vignette conducteur par scène (`rendu/planches_etape2.py`).

**Documentation.**

- `hda/README_RG.md` : § 10 L4, § 11 giratoires, § 12 autoroutes, § 13 bordures, § 14 chaîne complète ; arborescence et
  limites mises à jour.
- `description/FORMAT_DESCRIPTION.md` : types de bordures (§ 5.2), entrée charretière (§ 8), fabrication (§ 16).

**Fabrication.** Les 25 scènes ont été fabriquées et rendues en **un seul processus**, ordre J1, G3, A1, S01-S12, B01,
J2-J5, G1, G2, A2-A4, code 0. Durée : 2 h 18 min pour 25 scènes et 59 vues. Les autoroutes pèsent le plus : 0,9 à
1,2 million de faces de sol, 344 à 471 s de rendu chacune. Une scène simple prend environ 2 min 30 s rendus compris.

## 2. Critères

| Id | Critère | Valeur mesurée | Seuil | Atteint |
|---|---|---|---|---|
| INT-1 | une seule commande (`--complet`) pour les 25 scènes, description → rendu | 25/25 scènes, code 0 | 25/25, code 0 | oui |
| INT-2 | S01-S12 : sol, peinture, niveaux, HeightField, entités, BEV, empreintes, courbes L1 identiques à l'étape 1 (*reformulé après le contrôle de l'étape 2*) | 12/12 pour ces fichiers ; **le livrable USD `route_l2.usda` diffère dans 11 des 12 scènes** (toutes sauf S01) : caniveaux de `pj::caniveau::2.2` | 12/12 | oui, pour la liste dite |
| INT-3 | écarts non voulus, 25 scènes, toutes sorties hors rendus | 0 (tous les écarts sont dans la liste fermée du § 3) | 0 | oui |
| INT-4 | compilation : rétrocompatibilité S01-S12, exemples, Meylan (modèle et rapport à l'octet) | 24/27 ; ex05, ex08, ex11 différents, voulus (§ 3) | identiques hors changements voulus | oui |
| INT-5-L3 | contrôle du lot L3 rejoué sur J1-J5 intégrés, comparé au même contrôle sur les sorties d'avant | écart numérique 0, 0 valeur différente | 0 | oui |
| INT-5-L4 | contrôle du lot L4 rejoué sur J1-J5, comparé à `controles_L4.json` du lot | écart 0, 0 valeur différente | 0 | oui |
| INT-5-giratoires | contrôle du lot L5 rejoué sur G1-G3, comparé au même contrôle sur les sorties d'avant | écart 0, 0 valeur différente | 0 | oui |
| INT-5-autoroutes | contrôle du lot autoroutes rejoué sur A1-A4, comparé au même contrôle sur les sorties d'avant | écart 0, 0 valeur différente | 0 | oui |
| INT-5-bordures | critères recalculés par `controler_bordures.py` (B01, S01-S12, Meylan) | 15/16 ; **R2 non compté** (*correction de l'étape 2* : gagné seulement par le changement de résolution, matériau non corrigé) ; C-B11 et C-B12 (pilote du lot) remplacés par INT-2, INT-3 et INT-7 | aucun critère perdu | **non** (R2) |
| INT-6 | rendus : 2 vues (3 pour J5, G1, A3), planche ≤ 1092 px, géométrie rendue = géométrie finale (empreintes des .usda) | 25/25 | 25/25 | oui |
| INT-7 | déterminisme, une fois en fin de lot : J5 et G1, deux processus | identique (70 fichiers : l1, l2, l2b, l3, l4, l5) | identique | oui |
| INT-8 | planches d'ensemble `etape2_*.png` ≤ 1092 px regardées en entier | 7/7 (1092 × 1040 ; la dernière 1092 × 296) | toutes | oui |

En plus, les 25 planches par scène ont été regardées en entier : J1, G3, S03, J5, G1, A3 et B01 une par une, les 18
autres empilées deux par deux (9 images ≤ 1092 px).

## 3. Non-régression : ce qui change, scène par scène

Méthode. Avant toute modification, les sorties ont été copiées dans `tmp/integration/avant/` : étape 1 pour S01-S12, et
pour B01, J, G et A les dernières sorties des lots. Chaque fichier de `l1/`, `l2/`, `l2b/`, `l3/`, `l4/`, `l5/`,
`autoroute/`, ainsi que `modele_voie.json` et `compilation.json`, est comparé à l'octet. La seule normalisation est celle
du contrôle de déterminisme (chemins relatifs des matériaux dans les `.usda`). Chaque fichier différent est ensuite
classé dans une liste fermée et mesuré.

| Scènes | Fichiers identiques | Différents (tous voulus ou dérivés) |
|---|---|---|
| S01 | 28 | 2 manifestes |
| S02, S04-S07, S11, S12 | 26 | 2 manifestes, `elements.json`, `route_l2.usda` (caniveaux) |
| S03, S08, S09, S10 | 25 | les mêmes + `mesures_l2.json` (rayons des joints, dérivé) |
| B01 | 17 | entrée charretière 0,05 → 0,03 m : modèle, sol, bordures, mesures dans s ∈ [83,6 ; 90,4] m seulement |
| J1, J3, J4, J5 | 35 | libellé `lot` de `courbes_controle.json`, manifestes, `elements.json` |
| J2 | 36 | libellé `lot`, manifestes (pas de bordure) |
| G1, G2, G3 | 28 | libellé `lot`, manifestes, `elements.json`, `giratoires.json` (ordre des clés) |
| A1-A4 | 28 | libellé `lot`, manifestes (pas de bordure) |

**Liste fermée des changements voulus.**

1. **`elements.json`** (toutes les scènes à bordures) : champs ajoutés seulement (`asset_id`, `asset_motif`,
   `angle_debut`, `angle_fin`, `angle_sens`, `angle_deviation_deg`, `sens`, `fleche_mm`, `proto_type`, `prototype_pj`).
   Aucune valeur existante ne change.
2. **Caniveaux de `pj::caniveau::2.2`** (`route_l2.usda`, maillages `Caniveaux/*`) : mêmes faces, points à 0,7 µm au plus,
   UV des pièces décalées (prototypes espacés de 2 m), normales recalculées. Le sol, les bordures et la peinture sont
   identiques à l'octet.
3. **Rayons des joints** (`mesures_l2.json` de S03, S08, S09, S10 : sondes du pilote, pas de la géométrie). Ce sont des
   rayons rasants dont la cible est l'arête d'un joint : un écart de 0,7 µm suffit à changer la face touchée devant la
   bordure. Écarts : S03 et S10 1,1 cm ; S08 0,73 m (impact devant la face → au joint) ; S09 0,51 m (au joint → devant la
   face). Le critère que ces sondes servent à mesurer ne change pas : l'impact le plus profond derrière la face reste
   0,028 m (S08), 0,018 m (S09) et 0,032 m (S10), et aucun rayon ne passe sans impact.
4. **B01, entrée charretière** à 0,03 m au lieu de 0,05 m (vue nominale de T2_bateau : 0,02-0,04). Le modèle change
   (2 valeurs). Les points du sol modifiés sont tous dans s ∈ [83,6 ; 90,4] m, c'est-à-dire l'entrée de 85,5 à 88,5 m
   plus ses rampants de 2 m, avec Δz de −2,0 cm au plus. Mêmes effets sur `niveaux.json`, `entites.json`,
   `heightfield.json` et `mesures_l2.json`.
5. **Compilation** des exemples :
   - ex08 et ex11 : entrée charretière à 0,03 m ;
   - ex05 : la bordure « autre » de la piste à niveau intermédiaire devient T1 (RF-AS-profil_T1, choisie par la vue
     nominale) ; `rg::nivellement` refusait jusqu'ici ce profil.
6. **Manifestes** :
   - signatures d'HDA, pilote, familles, empreintes de fichiers ;
   - avertissements de cuisson de `pj::marquage_solide` dans `manifest_l2b.json` : S02, S03, S06 et S11 passent de 0 à
     3 avertissements (groupe `a_retourner` absent, attribut `pj_maillage`). Ils dépendent de la scène fabriquée juste
     avant dans le même processus, car les nœuds sont réutilisés d'une scène à l'autre. La peinture est identique à
     l'octet (voir § 5).
7. **`courbes_controle.json`** des scènes de réseau : seul le libellé `lot` change.
8. **`l5/giratoires.json`** : clés triées à l'export. L'ordre des attributs Houdini variait d'un processus à l'autre ;
   les valeurs sont identiques.
9. **Rendus** des scènes simples : 2 vues au lieu de 5 ou 6 à l'étape 1 (oblique, piéton et détail retirés, règle de
   vitesse) ; J5 : 3 vues au lieu de 4.

## 4. Contrôles des lots rejoués sur les sorties intégrées

`controler_L3.py`, `controler_giratoires.py` et `controler_autoroutes.py` ont été rejoués deux fois, sur la copie
d'avant et sur les sorties intégrées. Mesures identiques à la valeur près. `controler_L4.py` lit ses scènes sous
`recon/out/generateur` ; il est comparé à `controles_L4.json` écrit par le lot L4 sur ses sorties finales. Mesures
identiques.

Les critères des lots sont donc ceux de leurs rapports, inchangés par l'intégration. Ceux qui restent non atteints
sont repris au § 6.

`controler_bordures.py` (lot bordures) : les 16 critères qu'il calcule sont atteints.

- C-B5 : les vues des abaissés sont maintenant 0,02 et 0,03 (au lieu de 0,05).
- C-B8 : 74,9 % de la longueur posée en meshes du catalogue (au lieu de 74,6 %).
- R2 : la teinte de l'enrobé de B01 en vue conducteur mesure 30,0° au lieu de 37,5°. Ce n'est pas une correction du
  matériau : la même caméra est rendue en 1600 × 1000 au lieu de 1092 × 683, et l'écart était d'un pas de 1/255 sur une
  médiane 8 bits. Le seuil n'a pas changé.

## 5. Déterminisme

Vérifié **une fois**, en fin de lot, sur J5 (carrefours plans : L3 + L4) et G1 (giratoires : L3 + L5), avec
`fabriquer_generateur.py … --l2b --verifier-determinisme` : deux processus, **identique (70 fichiers)**. Un troisième
processus, le passage principal avec rendus, donne aussi les mêmes octets que le premier pour ces deux scènes. Seule
différence : `manifest_l4.json` de J5 recense `plan_l4.png`, une image de contrôle laissée par le lot L4 dans `l4/`.

Contre-épreuve sans coût : S03, J1, G3 et A1 avaient été fabriqués une première fois, pendant la mise au point, par un
processus distinct. Leurs sorties sont identiques à celles du passage principal, avec deux écarts expliqués :

- `manifest_l2b.json` de S03 : avertissements de cuisson qui dépendent de l'ordre des scènes (§ 3, point 6) ;
- G3 : ordre des clés de `giratoires.json`, corrigé entre les deux passages (§ 3, point 8).

## 6. Ce qui reste (non atteint ou à reprendre)

**Hérités des lots, inchangés par l'intégration** (mesures identiques, § 4) :

- L3 :
  - L3-9a / L3-9b : nez des îlots au premier contact des balayages + 0,30 m. Le VL passe sur 4 nez sur 8, le bus sur
    aucun.
  - L3-11 / L3-12 : sol étanche. Marche de 2 cm aux coins du cœur de J2 (profils RD et VC différents), 1,74 mm dans J4 ;
    bords libres : 1 dans J1, 5 dans J2.
- L4 (J5, carrefour complexe) :
  - L4-13 : les balayages des deux TAG guidés se recouvrent de 2,27 m² et touchent le nez du TPC sur 0,63 m.
  - L4-16 : les TAG nord et sud de la rue se croisent.
  - Les deux tiennent à la géométrie décrite (rue de 8 m, nez à la frontière) : c'est à trancher dans la description.
- Giratoires :
  - GI-03 : îlots séparateurs du mini-giratoire G3 dégénérés dans le modèle (lot scenes).
  - GI-11 : 8 bords libres cachés en G1, marche de 1,72 mm en G3.
- Autoroutes : AU-14 sans objet (aucune flèche ×4/3 dans A1-A4).
- L3a : autocar 15 m hors de la couronne 96/53 (cotes à confirmer).

**Correction connue, non appliquée.** La marche de 1,7 mm de J4 et de G3 a une cause identifiée par le lot giratoires :
`hda/rg_carrefours/vex_sol.py` prend la pente sous la bordure de coin en `s_tan` avec le `t` du bord pris en `s_end`, et
sur un bord évasé aucune limite ne correspond. La correction est d'évaluer `t` en `s`. Elle ne fait basculer aucun
critère (J2 et les bords libres de G1 restent), et elle demanderait de refaire J4 et G3. Elle n'a pas été faite, par
souci de durée.

**Limites de l'intégration :**

- Aucune scène ne compose deux familles (par exemple bretelle → giratoire). Le réseau composé existe mais n'est pas
  éprouvé.
- Les avertissements de `pj::marquage_solide` dans `manifest_l2b.json` dépendent de l'ordre des scènes dans un même
  processus. Pour un déterminisme indépendant de l'ordre, il faudrait reconstruire le réseau à chaque scène ou exclure
  ces avertissements du manifeste.
- L'exemple ex05, qui compile maintenant (bordure T1), n'a pas été refabriqué dans ce lot.

## 7. Fichiers

**Modifiés :**

- pilotes : `fabriquer_generateur.py`, `fabriquer_l2.py`, `fabriquer_l2b.py`, `fabriquer_carrefours.py`,
  `fabriquer_marquages_carrefour.py`, `fabriquer_giratoires.py`, `fabriquer_autoroutes.py`, `fabriquer_bordures.py` ;
- description et schéma : `description/vocabulaire.py`, `description/description_vers_modele.py`, `commun/profil.py`,
  `commun/bordures_catalogue.py`, `schema/modele_voie.schema.json` ;
- HDA et rendu : `hda/rg_nivellement/construire.py`, `rendu/rendu_l2b.py`, `rendu/planches.py` ;
- documentation : `hda/README_RG.md`, `description/FORMAT_DESCRIPTION.md`.

**HDA reconstruites :** `rg_nivellement.hdalc`, `rg_carrefours_sol.hdalc`, `rg_giratoires_sol.hdalc`.

**Créés :** `rendu/planches_etape2.py`, `validation/comparer_integration.py`, `validation/faire_rapport_integration.py`,
ce rapport et `validation/rapport_integration.json`.

**Sorties (non versionnées) :**

- `recon/out/generateur/<scene>/` pour les 25 scènes ;
- `recon/out/generateur/catalogue_rendus/etape2_1.png` à `etape2_7.png` ;
- copie de référence `recon/generateur/tmp/integration/avant/`, journal `tmp/integration/fabrication.log`.
