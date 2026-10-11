# recon/pcg/houdini/hda : HDA Houdini du projet Paquet Jardin (fabrication procédurale v2)

« Claude décrit, Houdini fabrique, UE 5.8 place ». La fabrication passe par des **réseaux de nœuds Houdini empaquetés
en HDA** (`pj::<nom>::1.0`). Les modules numpy `recon/pcg/houdini/pj_*.py` ne servent plus que de références de
comparaison. Python n'est permis qu'à trois endroits :

- dans le lecteur `pj::lire_description`, pour convertir le GeoJSON, le JSON et le npz en géométrie Houdini avec
  attributs ;
- dans de petits Python SOP d'entrées-sorties, par exemple la sérialisation JSON de `pj::exporter_points` ;
- dans les scripts de construction (`construire*.py`, qui appellent `hou.createNode` puis enregistrent l'HDA) et dans
  le pilote batch `recon/pcg/houdini/fabriquer_hda.py`.

Toute opération géométrique passe par des nœuds : SOP, VEX ou LOP.

```
hda/
  README_HDA.md                      ce fichier (conventions communes, contrat des HDA de branche)
  commun/
    pj_hda_outils.py                 outils des scripts de construction (créer, développer, installer, empaqueter, compter)
    vex/pj_niveau.h, vex/pj_repere.h bibliothèques VEX recopiées dans les wrangles (requête de nivellement, repères)
    construire_commun.py             construit pj::niveau_z, pj::preparer_export, pj::exporter_points
    pj_niveau_z.hdalc/  pj_preparer_export.hdalc/  pj_exporter_points.hdalc/   HDA développées (versionnées)
    verifier_paquet.py               le paquet pour Unreal est autonome (session hython neuve)
    essai_houdini_engine.py          essai HAPI (refusé par la licence Engine Indie hors plugin agréé, voir § 1)
    rendre_integration.py            contrôle visuel de toutes les couches fabriquées (Karma XPU, § 9)
  ue/                                essai Houdini Engine et PCG dans l'éditeur UE 5.8 (§ 9.4)
  pj_lire_description/
    construire.py, lecteur.py        construction du lecteur ; module Python embarqué (section PythonModule)
    pj_lire_description.hdalc/       HDA développée (versionnée)
  <branche>/                         HDA des branches (agents F) : construire.py + pj_<branche>.hdalc/
recon/pcg/houdini/paquet_jardin_pcg.hip   scène maîtresse (construite par fabriquer_hda.py --construire-hip)
recon/pcg/houdini/fabriquer_hda.py        pilote batch
recon/out/paquet_jardin/v2/fabrique_hda/  sorties (USD par branche ou tuile, points, matériaux, paquet UE, contrôles)
```

## 1. Outils Houdini 22 Indie (vérifiés le 10/10/2026, hython 22.0.459, licence Indie)

- `hou.hda.defaultFileExtension()` vaut `.hdalc` : une HDA créée en Indie s'enregistre en `.hdalc`.
- **Format développé** (`hou.hda.expandToDirectory`, `hotl -t`) : c'est un dossier `<nom>.hdalc/` qui contient
  `houdini.hdalibrary`, `Sections.list` et un sous-dossier par définition (`DialogScript`, `CreateScript`,
  `Contents`, `PythonModule`, `Help`, `PjSignature`…).
  - Ce dossier **s'installe directement** (`hou.hda.installFile(dossier)`) et c'est la forme versionnée.
  - Le réseau (`Contents`) est enregistré non compressé (`HDAOptions.setCompressContents(False)`).
  - `hou.hda.collapseFromDirectory` / `hotl -l` reconstruit le fichier compact.
- **Une HDA Indie n'est jamais identique à l'octet** d'une construction à l'autre. `Contents` porte des marques de
  licence `HouLC…` datées et des dates `stat create/modify`, et `INDEX__SECTION` porte `Modified:`.
  - `pj_hda_outils.creer_hda` calcule donc une **signature de construction** : sha256 du réseau (`asCode`), de
    l'interface, du module, de l'aide et de la version de Houdini. Elle est rangée dans la section `PjSignature`.
  - Si la signature ne change pas, le dossier existant est gardé tel quel (aucun diff parasite). Vérifié sur deux
    reconstructions successives : aucune différence.
- **Modules Python embarqués** : section `PythonModule`, lue par `node.hdaModule()`. Un Python SOP interne y accède
  par `hou.pwd().parent().hdaModule()`.
- **VEX** : deux limites de Houdini 22 pour le code d'un wrangle.
  - `#include "opdef:..."` **échoue** (« Unable to include »), alors que `hou.readFile` lit bien la section.
  - Une `struct` y est refusée (« unexpected struct ») et une fonction qui renvoie un tableau exige le mot-clé
    `function`.
  - Les bibliothèques `commun/vex/*.h` sont donc écrites sans struct et **recopiées en tête des wrangles** par
    `pj_hda_outils.vex(...)`. Chaque HDA reste autonome, sans `HOUDINI_VEX_PATH`, y compris dans Unreal.
  - Piège rencontré : `@w` est lu comme le vecteur standard de vitesse angulaire. Il faut nommer les volumes
    autrement ou typer explicitement (`f@`).
- **HeightField** : un volume 2D créé en Python n'est reconnu par les outils HeightField (Resample, Convert, affichage)
  qu'avec l'intrinsèque `volumevisualmode = "heightfield"`. Le lecteur le pose sur toutes ses couches.
- **Solaris** (paramètres réglés par le pilote) :
  - SOP Import : `copycontents = on`, `enable_savepath = 0` (sinon la couche SOP part dans `$HIP/usd/*.usd`),
    `pathattr = path`, `prefixabsolutepaths = 0`, `kindschema = nestedgroup`, `attribs = "P N uv Cd"`,
    `reversepolygons = 1` (`orientation = rightHanded`), `bindmaterials = bind`. La liaison est faite par l'attribut
    de primitive **`usdmaterialpath`**, et non par `shop_materialpath`, qui ne produit qu'un primvar.
  - Configure Primitive : `kind = assembly` sur `/World`, `setextents` sur `%type:Mesh`.
  - Configure Layer : `upaxis = z`, `metersperunit = 1`, `defaultprim = /World`, données `pj:*`.
  - USD ROP : `flattensoplayers = 1`, `savetimeinfo = 0`, `clearhoudinicustomdata = 1`.
  - Configure Layer range les clés `pj:x` dans un dictionnaire `{pj: {x}}`. Le pilote les remet à plat
    (`aplatir_donnees_calque`), comme les attend `verifier_usd` (`customLayerData['pj:cusp_deg']`).
- **Houdini Engine pour Unreal** (v4.0.2, `D:/ClaudeADAS/Plugins/HoudiniEngine`) :
  - Conversion des positions : `UE = (Hx, Hz, Hy) × 100` (`HoudiniEngineUtils.cpp`,
    `ConvertHoudiniPositionToUnrealVector`). Avec la convention du § 2, on retrouve exactement le contrat :
    `X = 100·x, Y = −100·y, Z = 100·z`.
  - Le nœud PCG « Houdini Digital Asset » lit les points `P`, `orient`, `scale` (3 flottants), `Cd`, `BoundsMin`,
    `BoundsMax`, `Seed`, `Density` et `Steepness` (`HoudiniPCGTranslator.cpp`). Les autres attributs deviennent des
    métadonnées PCG.
  - Attributs Unreal disponibles : `unreal_material`, `unreal_instance`, `unreal_output_name`, `unreal_split_attr`,
    `unreal_uproperty_*`, `unreal_bake_*`, `unreal_output_curve*`…
- **HAPI direct refusé en Indie** : `hapi.createThriftNamedPipeSession`, comme `createInProcessSession`, renvoie
  « Houdini Engine Indie license found but it can only be used with approved Houdini Engine plugins »
  (`essai_houdini_engine.py`).
  - L'essai Houdini Engine proprement dit se fait donc **dans Unreal** (plugin agréé) : fait le 11/10/2026, § 9.4.
  - Le pilote vérifie à la place que le paquet est autonome : `verifier_paquet.py` lance un hython neuf qui
    n'installe que le paquet, puis cuit lecteur, `niveau_z` et `preparer_export`. Résultat : 0 erreur, une seule
    bibliothèque chargée.
- **HDA imbriquées dans UE** : Houdini Engine ne charge que la bibliothèque de l'asset importé. Le pilote écrit donc un
  **paquet unique** `fabrique_hda/hda/pj_paquet_jardin.hdalc` qui contient toutes les définitions `pj::*`.
  - Houdini Engine instancie la **première** définition d'une bibliothèque et, dans l'éditeur, ouvre une boîte de
    choix modale quand elle en contient plusieurs (`bShowMultiAssetDialog`, vrai par défaut).
  - Le pilote écrit donc aussi une **bibliothèque à une seule définition** par HDA sans HDA `pj::` imbriquée :
    `fabrique_hda/hda/pj_<nom>.hdalc` (bordure, caniveau, sol, ilot, lire_description, niveau_z, preparer_export,
    exporter_points, gabarits_iisr, marquage_solide). Ce sont elles qu'on importe dans UE (§ 9.4). Les HDA de
    marquage à HDA imbriquée passent par le paquet.

## 2. Conventions communes (toutes les HDA `pj::*`)

### Repère et unités

| | Description (GeoJSON, JSON) | Houdini (SOP) | USD exporté (contrat `pj_usd/0.1`) | Unreal |
|---|---|---|---|---|
| Axes | L93 / NGF, puis local Z haut | **Y haut** | Z haut (`upAxis = "Z"`) | Z haut |
| Point | `(x, y, z)` local = L93 − O, z = NGF − 216,30 | **`(x, z, −y)`** | `(x, y, z)` local | `(100x, −100y, 100z)` cm |

- O = (917279,43 ; 6460289,98 ; 216,30). Les unités sont des mètres (`metersPerUnit = 1`). Dans la vue de dessus de
  Houdini, le nord est en haut.
- La conversion description → Houdini n'a lieu qu'**une fois**, dans `pj::lire_description`.
- La conversion Houdini → USD Z haut n'a lieu qu'**une fois**, dans `pj::preparer_export` : Transform SOP
  `rx = +90°`, soit `(X, Y, Z) → (X, −Z, Y)`, appliqué aussi aux normales.
- `commun/vex/pj_repere.h` fournit :
  - `pj_vers_local(P)` = `(P.x, −P.z, P.y)` et `pj_vers_houdini(p)` ;
  - `pj_quat_vers_local(orient)` : conjugaison par Rx(+90°), représentant w ≥ 0 ;
  - `pj_rpy_local(q)` : ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r) ;
  - `pj_nom_prim(id)` : `K-0005` → `K_0005`.
  - Contrôle : quatre rotations d'essai (lacet 30°, tangage 10°, roulis 5°, composée) donnent exactement
    `pj_commun.q_xyzw` (6 décimales).
- Faces de sol : **normale +Y**, soit un enroulement horaire vu de dessus (convention Houdini). Le lecteur retourne
  les anneaux GeoJSON au besoin (aire signée VEX, puis Reverse SOP sur le groupe `a_inverser`).
- Les rotations d'instances restent en Houdini Y haut (`orient`) jusqu'à l'export. `pj::exporter_points` écrit `q`
  (`[x, y, z, w]`) et `rpy_deg` en repère local Z haut.

### Attributs (noms fixes)

Primitives. Une entité de la description donne une ou plusieurs primitives, qui portent le même `id` :

| Attribut | Type | Sens |
|---|---|---|
| `id` | chaîne | identifiant stable de l'entité (`K-0005`, `S-0213a`, `ML-0069`…) |
| `famille` | chaîne | `bordures`, `surfaces`, `ilots`, `ponctuels_sol`, `marquages` |
| `classe` | chaîne | classe de la description (surfaces, marquages) ; `bordure` ; type d'îlot ; type de ponctuel |
| `materiau_id` | chaîne | identifiant de `assets/specs/materiaux_sol.json`, ou matériau maison (`PJ_Peinture_<couleur>_u<usure>` pour les marquages, `mortier_joint`…). C'est aussi le nom du Material USD `/World/Looks/<materiau_id>` et du `MI_<materiau_id>` dans UE. Bordures : `beton_gris` → `beton_bordure_gris`, `beton_clair` → `beton_bordure_clair` |
| `src`, `conf` | chaîne | provenance de la géométrie (`gam`, `ortho2022`…) et confiance (`haute`, `moyenne`, `faible`) |
| `usure` | flottant 0-1 | marquages : classe IISR 0, 1, 2, 3, F → 0, ⅓, ⅔, 1, 1 (la classe reste dans `usure_desc`) ; bordures : `aspect.epaufrures` ; sinon 0 |
| `salissure` | flottant 0-1 | `aspect.salissure` (bordures), `revetement.salissure` (surfaces) ; sinon 0 |
| `couverture` | flottant 0-1 | couverture de peinture (marquages) ; sinon 1 |
| `graine` | entier 31 bits | `sha256(id + "|pj_fabrique/0.1")`, 4 premiers octets en petit-boutiste, `& 0x7FFFFFFF` (même graine que `pj_commun.graine(id)`). Toute variation aléatoire part de `graine`, plus un sel constant par usage. Entités supplémentaires sans graine : `random_shash(id)` |
| `region_niveau`, `region_haute` | entier | région du modèle de nivellement (TQ-SOL-013). Surfaces : `region_niveau` ; îlots : région de leur surface ; bordures : `region_basse` / `region_haute` de nivellement.json ; −1 : à déduire du nœud propriétaire |
| `niv_s`, `niv_z_pied`, `niv_z_tete`, `niv_z_arriere` | flottant[] | bordures : profil en long du modèle unique (nivellement.json `bordures[]`, Z local) |
| `anneau`, `partie` | entier | anneau d'un polygone GeoJSON (0 = extérieur, ≥ 1 = trou, groupe `trou`) ; partie d'une géométrie Multi* |
| `props` | chaîne | propriétés complètes de l'entité en JSON (clés triées) |
| autres | selon le type | chaque propriété de la description devient un attribut du même nom : scalaire (int, flottant, chaîne), `dict`, `dict[]` (liste de dictionnaires, ex. `intervalles`, `abaisses`), tableau de chaînes ou de flottants. Un type mêlé devient `<nom>_json` (texte) |

Coordonnées L93 contenues dans les propriétés :
- chaque clé `*_l93` reçoit une sœur `*_local` ;
- `geometrie_reguliere.primitives[].x0 / y0` sont réécrits en **local** (`x0_l93` / `y0_l93` gardés) ;
- `nez.position` reçoit `position_local`.

Points :

| Attribut | Sens |
|---|---|
| `z_decrit`, `a_z` | Z local de la description (bordures : pied de face ; ponctuels) et drapeau de présence |
| `s` | abscisse curviligne plane (m) des courbes ouvertes (VEX). C'est le `s` des intervalles, des abaissés et de `geometrie_reguliere` |
| `profil`, `vue_m`, `role` | bordures : profil NF, vue (m) et rôle de l'intervalle qui contient `s`. Sur une chartière, la vue varie linéairement de `vue_m` à `vue_m_fin` (VEX) |
| `z_pied`, `z_tete`, `z_arriere` | bordures : niveaux du modèle unique interpolés en `s` (VEX `pj_interp`) |

- Groupes de primitives : `f_<famille>`, `b_<branche>` (branches de fabrication, § 4), `avec_caniveau`, `trou`,
  `non_fabrique` (marquages `fabrication.statut = non_fabrique`, chargés seulement sur demande), `a_verifier`,
  `supplementaires`.
- Détail : `pj_hash_description` (manifeste de la description), `pj_hash_fichiers` (sha256 de chaque fichier lu),
  `pj_schemas`, `pj_comptes`, `pj_emprise` (xmin, ymin, xmax, ymax locaux), `pj_dossier`, `pj_altitude`.

### Nivellement (TQ-SOL-013, CF-26 : un seul modèle de Z)

La sortie 2 de `pj::lire_description` est un **HeightField** Houdini : volumes 2D au pas de 0,10 m, rangés comme le
SOP HeightField (axe 0 → Z monde, axe 1 → X monde, plat en Y), avec `volumevisualmode = heightfield`.

| Volume | Contenu |
|---|---|
| `height` | z0 (Z local du nœud, région propriétaire). Trous (bâtiments, r0 = −1) comblés pour l'affichage par un flou normalisé (Volume Blur + Volume Wrangle) |
| `r0` | région propriétaire (−1 = aucune) |
| `z1`, `r1`, `z2`, `r2` | prolongements (2 nœuds) des régions voisines (NaN → 0, r = −1) |

- Attributs de détail : `niv_x0`, `niv_y0` (coordonnées locales du nœud (0, 0) du recadrage), `niv_pas`, `niv_ni`,
  `niv_nj`, `niv_i0`, `niv_j0`, `niv_sous_ech`, `niv_hash`.
- Le Z de tout sommet de sol se lit **uniquement** par `pj_niv_z(g, x, y, region)` (`commun/vex/pj_niveau.h`), ou par
  l'HDA `pj::niveau_z` qui l'emballe. C'est le portage exact de `decrire/nivellement_requete.py: Nivellement.z` :
  interpolation bilinéaire restreinte à la région de la surface, si bien que les marches de bordure ne sont jamais
  lissées.
- Contrôle sur les 140 720 sommets des surfaces du site : écart VEX − Python max 0,33 mm, p99 0,007 mm (float32).
  Profils des bordures (`z_pied`, `z_tete`) : écart max 0,0004 mm.

### Graines et déterminisme

- Aucune graine globale, aucune horloge. L'ordre des primitives suit celui des fichiers (triés par `id`).
- Deux passes de fabrication donnent les mêmes fichiers à l'octet, ainsi que la même empreinte sha256 du lecteur
  (positions, id, matériaux, groupes, voxels). C'est vérifié par `fabriquer_hda.py --verifier-determinisme` et par deux
  `--essai-export` successifs (USD identiques).

### Attributs pour Unreal (Houdini Engine)

| Attribut | Classe | Usage |
|---|---|---|
| `unreal_material` | primitive | `/Game/PJ/Materials/MI_<materiau_id>.MI_<materiau_id>` (posé par `pj::preparer_export`) |
| `unreal_output_name` | primitive | `SM_<entité>` (posé par `pj::preparer_export`) |
| `unreal_instance` | point | chemin d'un StaticMesh de la bibliothèque (`/Game/PJ/Lib/...`) pour les instances. Pas de PointInstancer USD (E7) |
| `unreal_uproperty_<Propriete>` | détail / primitive | propriétés de composant (ex. `unreal_uproperty_CastShadow`) |
| `unreal_split_attr` | détail | `pj_entite` : un StaticMesh par entité |
| `seed`, `density` | point | lus par le nœud PCG « Houdini Digital Asset » (= `graine`, 1) |

## 3. HDA communes

Le nombre de nœuds est mesuré par `pj_hda_outils.compter_noeuds` et repris dans `manifest_fabrication_hda.json` ;
les wrangles contiennent chacun un VOP compilé, compté dans le total récursif.

| HDA | Entrées | Sorties | Nœuds (récursif) | Rôle |
|---|---|---|---|---|
| `pj::lire_description::1.0` | 1 facultative : entités supplémentaires | 1 : entités ; 2 : HeightField | 18 (28) | lecteur unique de la description |
| `pj::niveau_z::1.0` | 1 : géométrie ; 2 : HeightField | géométrie avec Z ou attribut | 2 (2) | requête du nivellement (VEX) |
| `pj::preparer_export::1.0` | 1 : maillages Y haut d'une branche | maillages Z haut prêts pour SOP Import | 13 (13) | normales, UV, chemins, matériau, Y → Z |
| `pj::exporter_points::1.0` | 1 : points d'instances | (passe) + détail `pj_points_json` | 3 (3) | sérialisation `pj_points/0.1`, bouton « Écrire » |

### `pj::lire_description::1.0` (« PJ Lire la description »)

Réseau, entrée facultative comprise :

```
lire_entites (Python SOP, lecteur.py) ┐
supplementaires (VEX : groupes, graine) ┴ fusion -> orienter (VEX, aire signée) -> inverser (Reverse) -> nettoyer_groupes
  -> abscisses (VEX, s) -> profils (VEX, intervalles) -> niveaux_bordures (VEX, pj_interp) -> altitude (VEX, pj_niv_z) -> ENTITES
lire_nivellement (Python SOP, npz) -> flou_comblement (Volume Blur) -> combler (Volume Wrangle) -> retirer_poids (Blast) -> NIVEAU
```

Paramètres :

| Onglet | Paramètre (interne) | Sens |
|---|---|---|
| Description | Dossier de la description (`dossier`) | dossier `base/` ; dans la scène maîtresse, `$PJ_DESCRIPTION` |
| Description | Bordures, Surfaces, Îlots, Ponctuels de sol, Marquages (`fam_<famille>`) | familles à charger |
| Description | Garder les marquages non fabriqués (`marquages_non_fabriques`) | lignes virtuelles et hypothèses non peintes (MQ-LEF-002/011) |
| Description | Garder les propriétés JSON (`garder_props`) | attribut `props` |
| Description | Filtre d'identifiants (`filtre_ids`) | motifs fnmatch séparés par des espaces (`K-03* S-0213a`) |
| Emprise | Emprise (`emprise`) | site (carré de 300 m), pilote ZP-01, boîte, tuile. Une entité est gardée entière si sa boîte touche l'emprise |
| Emprise | Boîte min / max (`boite_min`, `boite_max`) | repère local |
| Emprise | Tuile : taille, indices (`tuile_taille`, `tuile_index`) | tuiles depuis (−150, −150) |
| Emprise | Marge (`marge`) | élargissement de l'emprise |
| Altitude et nivellement | Altitude des sommets (`altitude`) | décrite (Z de la description, sinon modèle), nivellement (bordures au `z_pied`, autres `pj_niv_z` dans leur région), à plat |
| Altitude et nivellement | Charger le nivellement (`charger_nivellement`) | sortie 2 |
| Altitude et nivellement | Marge du recadrage (`niv_marge`) | m autour de l'emprise |
| Altitude et nivellement | Sous-échantillonnage (`niv_pas`) | 1 = 0,10 m. Au-delà, aperçu seulement : la requête n'est plus exacte |
| Altitude et nivellement | Rayon de comblement (`comblement_rayon`) | 30 m par défaut, affichage seulement |

Mesures sur le site complet : 2 563 primitives et 165 269 points.
- Bordures : 512 entités.
- Surfaces : 1 420 entités, 1 492 anneaux.
- Îlots : 14.
- Ponctuels : 12.
- Marquages : 394 entités, 533 parties (8 non fabriqués exclus).
- HeightField : 3 001 × 3 001 × 6 couches.

Cuisson : 3,6 s pour le site, 0,4 s pour la zone pilote. Les fichiers sont mis en cache (chemin, date, taille), si bien
que changer l'emprise ne relit rien.

### `pj::niveau_z::1.0` (« PJ Niveau Z (nivellement) »)

| Paramètre | Sens |
|---|---|
| Région de nivellement (`mode_region`) | attribut (point ou primitive), ou nœud propriétaire le plus proche |
| Attribut de région (`attribut_region`) | `region_niveau` par défaut (ou `region_haute`) |
| Écrire dans (`sortie`), Nom de l'attribut (`nom_attribut`) | `P.y`, ou un attribut flottant (`z_niv`) |
| Décalage (`decalage`) | ex. +0,003 m pour une peinture posée |
| Hors modèle (`si_absent`) | garder le Z d'entrée, ou z = 0 ; attribut `niv_absent` = 1 |

### `pj::preparer_export::1.0` (« PJ Préparer l'export USD »)

Réseau :

```
verifier (VEX : attributs requis, type normal de N) -> nettoyer (Clean : faces dégénérées, points orphelins)
  -> choix_normales (Switch : Normal SOP par sommet, angle de rupture) -> choix_uv (Switch : UV de secours VEX)
  -> chemins (VEX) -> choix_couleurs (Switch : Cd = usure, salissure, graine)
  -> vers_zup (Transform rx = +90°) -> garder_attributs (Attribute Delete) -> retirer_groupes
```

- `path` = `/World/<pj_couche>/<pj_entite>/<pj_maillage | materiau_id>` (E6).
- `usdmaterialpath` = `/World/Looks/<materiau_id>` (E5).
- Plus `unreal_material` et `unreal_output_name`.

| Paramètre | Sens |
|---|---|
| Couche par défaut (`couche_defaut`) | `/World/<couche>` quand `pj_couche` manque (le pilote met la couche de la branche) |
| Matériau par défaut (`materiau_defaut`) | `PJ_Neutre` |
| Normales (`calculer_normales`) | calculer si absentes, toujours recalculer, ou garder celles d'entrée |
| Angle de rupture (`cusp`) | 30° (E2, `pj:cusp_deg`) |
| UV de secours en mètres (`uv_secours`) | projection sur le plan dominant de chaque face (E3) ; jamais une projection de dessus sur une face verticale |
| Couleur de sommet (`couleurs`) | R usure, G salissure, B graine |
| Passer en Z haut (`vers_zup`) | rx = +90° |

### `pj::exporter_points::1.0` (« PJ Exporter les points (pj_points/0.1) »)

`vers_local` (VEX : `pj_p`, `pj_q`, `pj_rpy`, `pj_s`) → `serialiser` (Python SOP : détail `pj_points_json`, une
ligne par point, tri par id) → bouton « Écrire le fichier » (`hdaModule().ecrire(node)`, également appelé par le
pilote).

- Entrée : `P`, `orient`, `scale` et/ou `pscale`, `id`, `asset` (sinon `unreal_instance`), `graine`, `cd` (tableau),
  `x` (dict).
- Paramètres : famille, fichier, hash de la description (vide : détail `pj_hash_description`), pivot, bibliothèque,
  sens de `cd`.

## 4. Scène maîtresse et contrat d'une HDA de branche (agents F)

`recon/pcg/houdini/paquet_jardin_pcg.hip` est construite par `fabriquer_hda.py --construire-hip` (Indie : contenu
`.hiplc`).

- **`/obj/paquet_jardin`** (64 nœuds au 11/10/2026) :
  `lire_description` → `ENTITES`, `NIVEAU`. Pour chaque branche `sol`, `bordures`, `caniveaux`, `ilots`,
  `marquages_lignes`, `passages`, `symboles`, `zones` :
  - `entrees_<b>` : Blast du groupe `b_<b>` ;
  - `fab_<b>` : l'HDA de la branche. Les huit sont installées ; le **Null d'emplacement** (données utilisateur
    `pj_emplacement = 1`, commentaire affiché) ne sert plus que si une HDA manque ;
  - `SORTIE_<b>` → `export_<b>` (`pj::preparer_export`, couche `PJ_Sol`, `PJ_Bordures`, `PJ_Caniveaux`, `PJ_Ilots`,
    ou `PJ_Marquages` pour les quatre branches de marquage) → `USD_<b>` ;
  - `points_<b>` : `pj::exporter_points`, sur la sortie 2 de `fab_<b>` ou sur `VIDE`.
- **`/stage`** (62 nœuds) : `materiaux` (Sublayer `$PJ_SORTIE/materiaux_ue.usda`), puis par branche `import_<b>`
  (SOP Import) → `kind_<b>` → `etendues_<b>` → `couche_<b>` (Configure Layer) → `rop_<b>` (USD ROP
  `$PJ_SORTIE/<b>.usda`) ; même chaîne `*_proto_<b>` pour les sorties 3 (prototypes).
- **Contrôle** : `/obj/apercu_lecteur` (tubes PolyWire par famille, HeightField rééchantillonné à 0,5 m et converti) et
  `/stage/apercu` (caméras orthographiques site, centre et pilote, plus une caméra oblique ; matériau MaterialX qui
  lit `displayColor` ; soleil, ciel, Karma XPU).

Contrat d'une HDA de branche, pour remplacer un emplacement :

- **Entrée 1** : entités de la branche (courbes ou polygones avec les attributs du § 2). Dans UE, ce sont des courbes
  ou des polygones tracés avec les mêmes attributs ; l'HDA doit fonctionner avec les seuls attributs qu'elle documente.
- **Entrée 2** : HeightField de nivellement (sortie 2 du lecteur). Le Z se lit par `pj_niv_z` (copier
  `pj_hda_outils.vex("pj_niveau.h")` en tête du wrangle) ou par `pj::niveau_z`.
- **Entrée 3** (facultative) : toutes les entités (contexte : bordures pour couper le sol, surfaces sous les marquages).
- **Sortie 1** : maillages en **Y haut**.
  - En primitive : `materiau_id`, `pj_couche`, `pj_entite` (id d'entité ou nom de tuile, qui devient le prim
    component) et `pj_maillage` (facultatif, `materiau_id` par défaut).
  - En sommet : `N` (angle de rupture 30°, sinon `pj::preparer_export` le calcule) et `uv` **en mètres** (`st` dans
    l'USD).
  - `Cd` est facultatif.
- **Sortie 2** (facultative) : points d'instances avec `id`, `asset`, `unreal_instance`, `orient`, `scale`, `graine`,
  `cd` (tableau de flottants) et `x` (dict de traçabilité).
- **Sortie 3** (facultative) : prototypes de bibliothèque (maillages à l'origine, `pj_entite` = nom d'asset, `pj_couche`
  `PJ_Lib_*`). Le pilote crée alors `SORTIE_PROTO_<b>` → `export_proto_<b>` → `USD_PROTO_<b>` et `/stage/*_proto_<b>`
  → `$PJ_SORTIE/prototypes/<b>.usda` (import UE dans le dossier de `unreal_instance`). Les paramètres d'HDA
  `pivot_prototypes` et `sens_cd`, s'ils existent, sont recopiés dans les champs `pivot` et `cd` de `points_<b>`.
- Nom de type : `pj::<branche>::1.0`, ou un autre déclaré dans `hda/commun/branches.json`
  (`{"branches": {"<branche>": "pj::<nom>::1.0"}}`).
- Rangement : `hda/<branche>/construire.py` (qui utilise `commun/pj_hda_outils.py` : `sous_reseau`, `wrangle`,
  `vex`, `creer_hda`) et le dossier développé `pj_<branche>.hdalc/`. `fabriquer_hda.py --construire-hda --toutes`
  lance tous les `hda/*/construire*.py`, puis `--construire-hip` remplace les emplacements.
- Chaque USD de branche écrit par le pilote est contrôlé par `recon/pcg/ue/contrat/verifier_usd.py` ; le résultat est
  repris dans le manifeste.

## 5. Commandes

Depuis la racine du dépôt, avec `PYTHONDONTWRITEBYTECODE=1` et `hython` de Houdini 22.0.459 :

```
hython recon/pcg/houdini/fabriquer_hda.py --construire-hda [--toutes]   # HDA communes et lecteur (+ branches)
hython recon/pcg/houdini/fabriquer_hda.py --construire-hip              # scène maîtresse
hython recon/pcg/houdini/fabriquer_hda.py [--emprise site|pilote] [--tuiles 64] [--sortie DIR] [--apercu] [--verifier-determinisme]
                                          [--branches marquages_lignes,passages,symboles,zones]   # sous-ensemble de branches
hython recon/pcg/houdini/hda/pj_marquage_commun/rendre_marquages.py      # vues de contrôle des marquages (§ 7)
hython recon/pcg/houdini/hda/pj_marquage_commun/verifier_marquages.py    # contrôles des marquages (§ 7)
hython recon/pcg/houdini/fabriquer_hda.py --essai-export DIR            # chaîne preparer_export -> Solaris -> USD -> verifier_usd
hython recon/pcg/houdini/hda/commun/verifier_paquet.py PAQUET.hdalc DESCRIPTION_BASE
hython recon/pcg/houdini/fabriquer_hda.py --sortie AUTRE                # passe d'un autre processus...
hython recon/pcg/houdini/fabriquer_hda.py --comparer AUTRE/manifest_fabrication_hda.json   # ...sorties identiques ?
hython recon/pcg/houdini/fabriquer_hda.py --vex-jit                     # JIT natif de VEX gardé (non déterministe, § 9.2)
hython recon/pcg/houdini/hda/commun/rendre_integration.py [--vues site,centre,oblique_centre,oblique_pilote,rue]
python recon/pcg/houdini/hda/ue/piloter_essai_he.py [--sans-pcg] [--garder-niveau]   # essai Houdini Engine dans UE (§ 9.4)
```

Le pilote se relance lui-même avec `HOUDINI_VEX_DISABLE_JIT=1` (§ 9.2) ; le manifeste porte `vex_jit`, les durées
(`durees_s`, seule partie non déterministe), la liste des fichiers écrits (`produits`) et, par branche, l'empreinte de la
géométrie cuite avant export (`empreinte_sop`).

Sorties dans `recon/out/paquet_jardin/v2/fabrique_hda/` :

```
materiaux_ue.usda                       /World/Looks/<materiau_id> : UsdPreviewSurface + outputs:unreal:surface -> MI_<id>
                                        (34 de materiaux_sol.json, 7 maison, 10 peintures PJ_Peinture_<c>_u<u>)
<branche>[_t<i>_<j>].usda               une couche par branche fabriquée (et par tuile), sous-couche materiaux_ue.usda
points/<branche>.json                   pj_points/0.1
hda/pj_paquet_jardin.hdalc              paquet unique de toutes les définitions pj::* (HDA imbriquées)
hda/pj_<nom>.hdalc                      une définition par fichier (import dans Unreal, § 9.4)
controle/apercu_lecteur_{site,centre,pilote,oblique_pilote}.png, apercu_lecteur.usdc
controle/integration.usda, integration_<vue>.png   toutes les couches + symboles instanciés (rendre_integration.py)
controle/essai_houdini_engine_ue.json, he_*.png     essai Houdini Engine dans UE (§ 9.4)
manifest_fabrication_hda.json           HDA (nœuds, bibliothèques), lecteur (comptes, empreintes), branches, paquet,
                                        vérification du paquet, hash des sorties, déterminisme
```

- Utilisation interactive dans Houdini : § 9.3. Dans Unreal (Houdini Engine, PCG) : § 9.4.

## 6. Limites connues (mises à jour le 11/10/2026)

- Les huit branches sont des HDA ; le site complet cuit de bout en bout (§ 9.1).
- Déterminisme garanti par le pilote (JIT VEX coupé, `.usdc` canonique, § 9.2). Une cuisson interactive (Houdini,
  Houdini Engine dans UE) garde le JIT : résultats identiques au dernier bit près seulement.
- Nœud PCG « Houdini Digital Asset » : le type d'entrée « PCG Input » ne se règle que dans le panneau de détails
  (§ 9.4) ; sans lui, la spline PCG n'arrive pas à l'HDA.
- `niv_pas > 1` (sous-échantillonnage) n'est qu'un aperçu ; le comblement de `height` sous les bâtiments n'est qu'un
  affichage (r0 = −1, jamais lu par `pj_niv_z`).
- Le chemin du dossier de description du lecteur est absolu par défaut (`$PJ_DESCRIPTION` dans la scène maîtresse) ;
  dans UE, le régler sur le disque de la machine.

## 7. HDA de marquage (agent F2 : `hda/pj_marquage_*`)

La peinture est fabriquée en **maillages statiques** : empreinte vectorielle exacte, triangulée, extrudée (dessus à
+3 mm du sol, flancs enfouis à −5 mm), chanfreinée (1 mm), drapée sur le modèle de nivellement, UV en mètres, normales
à 30°. Aucun raster, aucun décalque, aucune géométrie v1. Branches (`hda/commun/branches.json`) :

| Branche | HDA | Dossier | Entrées | Sorties | Nœuds |
|---|---|---|---|---|---|
| (commun) | `pj::marquage_solide::1.0` | `pj_marquage_commun/` | 1 empreintes, 2 nivellement | maillages | 36 |
| (commun) | `pj::gabarits_iisr::1.0` | `pj_marquage_commun/` | — | gabarits (polygones) | 4 (5) |
| `marquages_lignes` | `pj::marquage_ligne::1.0` | `pj_marquage_ligne/` | 1 courbes, 2 nivellement | maillages | 19 |
| `passages` | `pj::passage_pieton::1.0` | `pj_marquage_passage/` | 1 axes, 2 nivellement | maillages | 16 |
| `symboles` | `pj::symbole_iisr::1.0` | `pj_marquage_symbole/` | 1 polygones ou points, 2 nivellement | 1 drapés, 2 instances, 3 prototypes, 4 aperçu | 25 |
| `zones` | `pj::marquage_zone::1.0` | `pj_marquage_zone/` | 1 polygones ou axes, 2 nivellement | maillages | 26 |

Nœuds : enfants directs (égal au récursif ; une HDA imbriquée, `pj::marquage_solide` ou `pj::gabarits_iisr`, compte
pour un). Bibliothèque VEX : `pj_marquage_commun/vex/pj_marquage.h` (pose des gabarits, primitives régularisées,
polygones), recopiée avec `pj_niveau.h` et `pj_repere.h` en tête des wrangles (`pj_marquage_outils.vex_m`). Python :
seulement le lecteur de gabarits (`pj::gabarits_iisr`, lecture JSON) et les scripts de construction, de rendu et de
contrôle.

### `pj::marquage_solide` (empreintes → peinture)

```
garder_attributs -> defauts (VEX) -> aplatir (VEX, y = -enfouissement)
  faces déjà maillées (pj_surface = 1, rubans) -> Divide (triangles)
  empreintes -> orienter_anneaux (VEX : extérieurs trigonométriques, trous horaires) -> Reverse
     -> For-Each par pj_entite { Triangulate 2D (contraintes, raffinement « pas du maillage de drapé ») -> retirer_trous
        (VEX : réunion des parties, trous de chaque partie) -> attributs_entite (VEX) }
  -> orienter (+Y) -> pieces (Connectivity) -> region_sommets / region_pieces (VEX : région majoritaire de chaque pièce,
     TQ-SOL-013) -> PolyExtrude (groupes dessus / flancs) -> aretes_dessus (VEX) -> PolyBevel (chanfrein)
  -> draper (VEX pj_niv_z dans la région de la pièce : aucune marche de bordure dans une pièce) -> Divide (faces planes)
  -> uv_metres (VEX : dessus en (x, y) locaux, flancs dans le plan de la face) -> Normal (30°) -> attributs_sortie
     (pj_couche, unreal_material, unreal_output_name, unreal_uproperty_CastShadow, unreal_split_attr) -> controles
```

Entrée : polygones plans avec `pj_entite`, `id`, `materiau_id`, `partie`, `anneau` (≥ 1 = trou de la partie),
`pj_surface`, `pj_region` facultatif. Paramètres : épaisseur (0,003), enfouissement (0,005), chanfrein (0,001), pas du
maillage de drapé (0,25), draper, région de drapé (pièce / attribut / sommet), seuil de franchissement (0,02), couche,
angle de rupture (30°), ombre portée (non). Détail `pj_marquage_controles` : pièces, aire du dessus, sommets hors
région, entités qui franchissent une marche.

### `pj::marquage_ligne` (ML-*, MT-*)

normaliser (largeur, modulation IISR art. 113-1 B recopiée de `marquages_geometrie.json`, phase, interruptions)
→ courbes régularisées : échantillonnage VEX des primitives droite / arc / clothoïde (corde ≤ 2 mm, pas ≤ 0,5 m,
sommets aux jonctions) ; courbes brutes (tracées à la main) : Resample + abscisses
→ coupures_marches (VEX, MQ-DET-010 : la ligne s'interrompt avec 2u de dégagement là où l'axe franchit une marche de
plus de 3 cm sur plus de 0,2 m ; plus court : signalé `pj_marches_ambigues`)
→ tirets (VEX : [phase + k (trait + vide), + trait] ∩ [0, L] moins les interruptions ; phase absente ancrée à l'aval,
MQ-DET-011 ; tronçons ≤ 20 m nommés `id_cNN`) → Attribute Copy → Sweep (ruban de largeur exacte, haut +Y, bouts
perpendiculaires) → `pj::marquage_solide`.

### `pj::passage_pieton` (MP-*)

normaliser (MQ-PP-003/004/005 : bande 0,50, longueur décrite sinon 3,00, pas décrit sinon calculé, bandes parallèles à
l'axe de la chaussée) → bandes (VEX : rectangles aux centres A + k·pas, hors coupures ; files cyclables : gabarit
`PAVE_CHRONOVELO` / `CARRE_TRAVERSEE_CYCLABLE` lu par `pj::gabarits_iisr`, ou `tuile_m`, MQ-CHR-001) → decoupes (VEX
64 bits : `decoupes[].polygone_l93` lus dans `props`) → PolyExtrude (prismes) → For-Each par passage
{ Boolean surface − prismes } → `pj::marquage_solide`.

### `pj::symbole_iisr` (MF-*, MS-*)

poses (VEX, une passe par entité) : genre `gabarit` (polygone exact de `marquages_geometrie.json` si l'écart au contour
décrit est ≤ 3 cm, FUS-SNP-004), `parametrique` (barre, point, dent de requin, chevron) ou `glyphe` (forme décrite : PMR,
chiffres, figurines hors tolérance) ; cap = `pose.cap_deg` ; origine = centroïde décrit − centroïde du gabarit tourné ;
plan du sol par moindres carrés dans la région majoritaire ; résidu > 3 mm → maillage drapé. Puis :
- sortie 3 : prototypes (un par forme et peinture, `asset` = `<forme>__<couleur>_u<usure>`), repère +X = sens de
  circulation, +Y à gauche, origine du gabarit, z = 0 au sol → `prototypes/symboles.usda`, couche `PJ_Lib_Marquages` ;
- sortie 2 : un point par symbole (`orient` = inclinaison du plan × lacet du cap, `unreal_instance` =
  `/Game/PJ/Lib/Marquages/SM_<asset>.SM_<asset>`, `cd` = [couverture, usure], `x`) → `points/symboles.json` ;
- sortie 1 : symboles drapés (sol non plan sous le symbole, ou mode « drapé ») → `symboles.usda` ;
- sortie 4 : instances empaquetées (Copy to Points), pour l'aperçu dans Houdini.

Dans UE : importer `prototypes/symboles.usda` dans `/Game/PJ/Lib/Marquages`, puis poser `points/symboles.json` (PCG).
`symboles.usda` ne contient que les symboles drapés : aucun doublon.

### `pj::marquage_zone` (MZ-*)

normaliser (VEX 64 bits : genre, `origine_bandes_l93` lu dans `props`, valeurs de `marquages_geometrie.json`) → motifs
(VEX : hachures 0,50 au pas perpendiculaire 1,85 ; chevrons ; damier ; zigzag MQ-BUS-005 en segments et joints
biseautés) → For-Each par zone { PolyExpand2D (retrait 3u + 2u, bord du contour 3u) → prismes → Boolean (motifs ∩ zone,
contour peint MQ-ILO-003) → fragments < 0,02 m² retirés } → `pj::marquage_solide`. Les contours décrits (divers, bande
isolée, T de stationnement) passent tels quels.

### Contrôles (10/10/2026, description 0.3, hash 7a869e6a…)

- `verifier_usd` : 0 erreur sur `marquages_lignes`, `passages`, `symboles`, `zones` et `prototypes/symboles`. Deux
  passes donnent des sorties identiques à l'octet (`--verifier-determinisme`, 7 fichiers). Le paquet unique cuit les
  quatre HDA seul (hython neuf).
- `verifier_marquages.py` → `controle/marquages_controles.json` (mesures numpy indépendantes du VEX) :
  - VAL-LIG-002 : aire mesurée contre longueur peinte attendue, p95 0,01 % ; un écart > 2 % (ML-5253, bout de 0,19 m
    autour d'un coin) ; dépassement latéral à l'axe p95 0,3 mm ;
  - VAL-ZEB-003 : 13 zébras conformes ; les 2 autres portent des découpes décrites ;
  - VAL-FLE-001 : cap ≤ 0,04° ; écart contour décrit − gabarit posé ≤ 2,8 cm (figurines vélo) ;
  - TQ-SOL-013 : dessus − modèle − 3 mm ≤ 1 mm au p95 ;
  - comparaison à l'ancienne fabrication numpy : 216 entités communes, écart de centroïde p50 2,7 cm.
- `rendre_marquages.py` → `controle/marquages_{fleche_td_tad_1m30, detail_fleche_0m25, zebra_verdun_so_1m60,
  traversee_cyclable, centre_dessus}.png` et `marquages_planche_centre.png` (ortho + levé GAM | ortho + marquages
  fabriqués | rendu).

### Limites

- ML-0798 et ML-0799 (rives jaunes du plan 2025) sont posées sur la limite d'une bordure. Elles sont coupées aux
  franchissements nets et signalées ailleurs (`pj_marches_ambigues`). C'est à reprendre dans la description (MQ-LIG-009).
- Les polygones (zébras, zones, symboles drapés) ne sont pas coupés automatiquement aux marches : la description porte
  les dégagements (`decoupes`). Les franchissements restants sont signalés ; il n'y en a aucun sur le site.
- Figurines vélo : gabarit IISR (`VELO`) quand le contour décrit (figurine reconstruite) s'en écarte de moins de 3 cm,
  sinon forme décrite (5 prototypes « glyphe »).
- Le chemin de `marquages_geometrie.json` est absolu par défaut (paramètre « Spécification des marquages »).

## 8. HDA du sol, des bordures, des caniveaux et des îlots (agent F1 : `hda/pj_sol`, `pj_bordure`, `pj_caniveau`, `pj_ilot`)

Branches `sol`, `bordures`, `caniveaux`, `ilots` de la scène maîtresse (déclarées dans `commun/branches.json` ;
ce ne sont plus des emplacements Null, cf. § 6) :

| Branche | HDA | Dossier | Entrées | Sorties | Nœuds |
|---|---|---|---|---|---|
| `sol` | `pj::sol::1.0` | `pj_sol/` | 1 surfaces et ponctuels BEV, 2 nivellement, 3 contexte | maillages | 71 |
| `bordures` | `pj::bordure::1.0` | `pj_bordure/` | 1 courbes, 2 nivellement, 3 contexte | 1 maillages, 2 instances, 3 prototypes | 71 |
| `caniveaux` | `pj::caniveau::1.0` | `pj_caniveau/` | idem | idem | 71 |
| `ilots` | `pj::ilot::1.0` | `pj_ilot/` | 1 îlots, 2 nivellement, 3 contexte | 1 remplissages, 2 éclats, 3 prototypes | 61 |

Python n'y sert qu'à lire la table des profils (Python SOP `lire_profils` de pj::bordure / pj::caniveau, module
`pj_bordure/profils.py` avec la table figée) ; toute la géométrie est faite par des nœuds et du VEX. Les bibliothèques
VEX sont recopiées en tête des wrangles par les scripts de construction :

| Fichier | Contenu |
|---|---|
| `pj_bordure/vex/pj_courbe.h` | courbes régularisées (`geometrie_reguliere.primitives` droites / arcs, D3) : point, cap et courbure en s, échantillonnage à flèche de corde ≤ 2 mm, flèche, déviation, projection ; repli sur la polyligne (courbes tracées dans UE) |
| `pj_bordure/vex/pj_pose.h` | disposition des éléments (portage de `pj_bordure_pose.py`) : points durs, pas selon le rayon, file finie par une coupe, chartières, profil bas, repère de pose |
| `pj_bordure/vex/pj_sections.h` | contours des profils, topologie commune pour les lofts de chartière, contour réduit des joints, arête avant haute (épaufrures) |
| `pj_bordure/vex/*.vfl` | corps des wrangles : `disposer`, `disposer_caniveau`, `poser`, `dorsales_bib`, `dorsales_sm`, `post` (sections `//@@ <nœud>`) |
| `pj_sol/vex/pj_sol.h` | Z de sol sur le modèle unique **sans lissage des marches** : nœuds de grille valides seulement (même surface, ou surface continue : ni emprise de bordure, ni l'autre côté d'une même bordure) |
| `pj_sol/vex/sol.vfl`, `bev.vfl`, `pj_ilot/vex/ilot.vfl` | corps des wrangles du sol, des BEV et des îlots |

### `pj::bordure::1.0` (« PJ Bordures (éléments préfabriqués) »)

Entrées : 1 courbes d'arête avant (trottoir à gauche) avec `id`, `intervalles` (dict[] : s0, s1, profil, vue_m,
vue_m_fin, role), `geometrie_reguliere`, `niv_s`, `niv_z_pied`, `materiau_id`, `aspect`, `joint_mm` ; 2 nivellement ;
3 contexte (facultatif). Sorties : 1 maillages Y haut ; 2 points d'instances ; 3 prototypes (`PJ_Lib_Bordures`).

```
filtrer -> disposer (VEX : points durs, pas 1,00 / 0,50 selon flèche <= 10,5 mm, coin de joint <= 6 mm, coin vertical
  <= 4 mm ; sinon pièce courbe sur mesure ; bateaux 1,00 / 0,50 / 0,33 / 0,25 ; coupe finale >= 0,20 m ; chartières ;
  jitter déterministe ; largeurs de joints 3,5-9,5 mm aux coins ; onglets des angles vifs)
-> poser (VEX : corde décalée de la demi-flèche, dessous du bloc = pied + vue − H, tangage du fil d'eau, orient,
  échelle X, prototype element_/coupe_/chartiere_<...>, unreal_instance, cd, x)
bibliothèque : dorsales_bib (VEX) -> Sweep (sections par point : lofts de chartière) -> attributs_abouts -> abouts
  -> PolyBevel (3 mm) -> épaufrures v1-v3 (Sphere + Attribute Noise + Copy to Points + Boolean) -> attributs_pieces
  -> Divide -> Normal (30°) -> UV (m) -> recentrer -> PROTOTYPES -> Pack -> Copy to Points (instances) -> Unpack
sur mesure : dorsales_sm (VEX, courbe régularisée à 2 mm) -> Sweep -> onglets -> abouts -> PolyBevel -> Divide
  -> Normal -> UV ; fusion -> export (pj_entite = bordure, PJ_Bordures)
```

| Onglet | Paramètres |
|---|---|
| Pose | altitude du pied (`profil` : niv_z_pied du modèle unique, ou `volume` : pj_niv_z devant la face), joint par défaut, largeur de joint variable, flèche max, coin de joint max, coin vertical max, pas des murets, corde des courbes |
| Aspect | jitter (hauteur, lacet, latéral, roulis), chanfrein d'about, épaufrures, retrait du mortier sombre |
| Sorties | sortie 1 (maillages dépaquetés pour l'USD, ou instances empaquetées), couche, couche des prototypes, `pivot_prototypes`, `sens_cd`, `format_usd` (usdc), dossier des specs (vide : table figée) |

### `pj::caniveau::1.0`

Même réseau, nœud `disposer_caniveau` : disposition des éléments de la bordure (joints alignés, bordures_elements
caniveaux) coupée aux intervalles du caniveau ; section CS posée devant la face (u de −largeur à 0), dessous = fil
d'eau − h côté bordure (CS2 : 0,11 m). Paramètres en plus : profil par défaut, courbes sans attribut caniveau.

### `pj::sol::1.0` (« PJ Sol (surfaces sur le nivellement) »)

Entrées : 1 surfaces (anneau 0 + trous, même id) et ponctuels BEV ; 2 nivellement ; 3 contexte (bordures).
Sortie : maillages Y haut, `pj_entite` = tuile `T_<i>_<j>` de 50 m (TQ-SOL-010) ou id de BEV, `pj_maillage` =
`materiau_id`.

```
selectionner -> aplatir -> densifier (Resample par arête : même découpe des deux côtés d'une limite partagée)
-> indexer (surf_index, arête cible par classe) -> echelle
-> boucle compilée For-Each id : Triangulate 2D (contraintes = anneaux, Refine 25°, arête cible 1, bords non découpés)
   -> trous -> attributs
-> echelle_inverse -> altitude (VEX pj_sol_z) -> altitude_emprise (sol sous bordure au pied)
-> profils_raccord (sur les bordures) -> raccords_bordures (VEX) -> rogner (hors grille) -> limites_partagees (VEX)
-> Fuse -> 4 passes marches (VEX) / Group Expand (2, 4, 6, 8 anneaux) / Attribute Blur de Z -> Normal (30°)
-> UV (x, y en m) -> export ; BEV : bev_dalles (VEX) -> bev_altitude (rayon sur le sol final) -> bev_hors_pietons
-> plots (Tube + Copy to Points)
```

- Z : modèle unique (TQ-SOL-013, CF-26) lu par `pj_sol_z` ; la requête brute relevait la chaussée de quelques cm sur
  les 10 cm devant la face (nœuds d'emprise et de trottoir de la même région 0) : d'où les biseaux.
- Raccords aux bordures (onglet « Raccords aux bordures ») : correction additive Δ(s)·w(d) qui donne exactement le
  pied de face devant la bordure (TQ-SOL-013 (4), VAL-SOL-009 (2)) et tête − 4 mm derrière l'arête arrière
  (TQ-SOL-013 (6)), Δ(s) = écart bordure / sol mesuré tous les 0,25 m (`profils_raccord`) et lissé sur ± 0,5 m ; bande
  de 0,3 m devant, 1 m derrière, allongée (≤ 3 m) pour que la pente du raccord reste ≤ 10 % devant et ≤ 8 % derrière
  (GA-TRO-004). Les bordures sont retenues par position (échantillons à moins de 3 m) et la règle ne dépend pas de la
  classe : deux surfaces voisines reçoivent la même correction ; plusieurs bordures : partition de l'unité en
  1 / distance² (exacte sur chaque ligne). Un sommet d'une surface non emprise situé sous l'empreinte (limite
  d'emprise D2 à quelques mm de la ligne régularisée D3) est rattaché au côté le plus proche. Devant une bordure à
  caniveau, la chaussée passe 1 cm sous l'élément CS (TQ-BOR-007).
- Limites partagées : chaque surface est triangulée seule ; entre deux surfaces continues (ni emprise, ni de part et
  d'autre d'une même bordure), les sommets de même XY sont ramenés au même Z puis soudés (Fuse 0,1 mm).
- Marches résiduelles du modèle (VAL-SOL-009 (1), E8) : triangles de plus de 40° et 2 cm adoucis (Attribute Blur de Z
  sur leurs sommets et 2, 4, 6 puis 8 anneaux voisins) ; talus de noue et BEV laissés en place.
- Arêtes cibles : chaussée 0,5 m, trottoirs 0,35 m, rampes et talus 0,25 m (TQ-SOL-002), parkings 0,75 m, espaces verts
  1,2 m, sous bordure 1 m ; angle minimal 25°. Le sol sous les bordures (emprises) est au pied (`sous_bordure_pied`).
- BEV : dalles le long de la bordure (modules, GA-BEV-004) maillées à 0,10 m pour suivre le sol final, première rangée
  de plots à 0,50 m du nez (GA-BEV-002), plots Ø 25 mm h 5 mm en quinconce de 75 mm, dessus 3 mm au-dessus du sol (E9 :
  < 5 mm) ; chants enterrés en option (`bev_chants`, désactivée : sur une rampe E8 les compte comme sol raide).
  Cellules de dalle et plots qui tombent sur la chaussée, un parking ou l'empreinte d'une autre bordure retirés
  (`bev_hors_pietons` : BEV-0388-1 chevauche K-0397, BEV-0385-2, -0381-1, -0389-1 débordent ; 44 cellules sur 1 124).

### `pj::ilot::1.0` (« PJ Îlots (remplissages et éclats) »)

Entrées : 1 îlots (remplissage, ceinture, surface) ; 2 nivellement ; 3 contexte (surfaces, bordures). Sorties :
1 remplissages (et couverture dense en option) ; 2 éclats épars (`eclat_brf_vNN`, `eclat_gravier_vNN`,
`/Game/PJ/Lib/Ilots/SM_<asset>`) ; 3 prototypes d'éclats (`PJ_Lib_Ilots`).

```
surfaces_ilots (VEX) [+ îlots sans surface : PolyExpand2D] -> aplatir -> Resample -> boucle Triangulate 2D
-> altitude_ilot (VEX : tête de ceinture − retrait + bombement, TQ-SOL-013 (7), GA-ARB-003) -> Fuse -> Normal -> UV
-> export ; couverture : densites -> Scatter -> couverture (VEX) -> Copy to Points ; eclats_debordement (VEX)
prototypes : Box / Sphere -> Copy to Points par variante -> prototypes_eclats (VEX) -> Normal -> UV
```

### Commandes et sorties (F1)

```
hython recon/pcg/houdini/hda/pj_sol/construire.py [--essai pilote|site|boite X0 Y0 X1 Y1]   # idem pj_bordure/, pj_ilot/
hython recon/pcg/houdini/hda/pj_caniveau/construire.py [--essai site]
hython recon/pcg/houdini/fabriquer_hda.py --construire-hip
hython recon/pcg/houdini/fabriquer_hda.py --branches sol,bordures,caniveaux,ilots --verifier-determinisme
hython recon/pcg/houdini/hda/pj_bordure/controles_f1.py [--emprise site|pilote] [--json SORTIE]   # contrôles chiffrés
hython recon/pcg/houdini/hda/pj_bordure/controle_f1.py [--vues f1_file_joints,...] [--planche]    # rendus Karma
```

`fabrique_hda/` : `sol.usdc` (1,22 M triangles, 212 maillages tuile × matériau et BEV), `bordures.usdc`
(578 k faces), `caniveaux.usda`, `ilots.usda`, `prototypes/{bordures,caniveaux,ilots}.usda` (`/World/PJ_Lib_*`),
`points/{bordures,caniveaux,ilots}.json` (14 424, 141, 397 instances), `controle/controles_f1[_pilote].json`,
`controle/f1_*.png`.

### Contrôles (site, 11/10/2026)

- `verifier_usd` : 0 erreur sur les quatre couches et les trois couches de prototypes (seuls avertissements, A :
  arêtes douces cassées aux coutures) ; deux passes identiques à l'octet (`--verifier-determinisme`).
- Bordures : 7 004 éléments de bibliothèque (598 prototypes), 928 pièces sur mesure (597 courbes, 35 murets),
  7 420 joints de 5 à 8 mm (p50 6,5 mm) ; flèche des éléments droits p95 1,8 mm, max 10,1 mm (≤ 10,5 mm).
- VAL-SOL-009 (2) : sol fabriqué à 3 cm devant la face − pied posé : p50 0,1 mm, p95 1,2 cm, 92 % à moins de 1 cm
  (pilote : 93 %) ; à 3 cm derrière l'arête arrière − dessus posé : trottoir p50 −4,8 mm, p5 −2,7 cm (TQ-SOL-013 (6)).
- Sol : E8 = 0 ; pentes p50 / p95 : chaussée 2,4 / 12 %, trottoir 4,2 / 16 %, rampes 5,5 / 15 % (GA-TRO-004 : les
  p95 portent les arêtes de grille de 0,10 m du modèle D1). Fissures (même XY, ΔZ > 2 cm) : ≈ 320 sommets, dont ≈ 220
  sous l'empreinte d'une bordure (cachés) et ≈ 100 en sol ouvert près des bouts de bordure (p50 4 cm).
- Îlots : remplissage − modèle p50 1,3 cm, p95 11,5 cm (bombement voulu, GA-ARB-003) ; 397 éclats épars.
- Comparaison avec la pose numpy (`v2/fabrique/points/bordures.json`, 64 bordures communes du pilote) : 1 419
  éléments contre 916 (pas de 0,50 m et pièces courbes au lieu d'éléments de 1 m forcés, chartières coupées à 1 m),
  pivots appariés par abscisse : écart plan p50 2,8 cm, écart Z p50 1,4 cm.

### Limites

- Essai Houdini Engine de `pj::bordure` dans Unreal : fait (§ 9.4 ; onglet « Courbe tracée (Unreal) » ajouté par
  l'intégration, 71 nœuds au lieu de 65).
- Le Z vient du modèle D1 (grille de 0,10 m sans lissage des marches) : les raccords et l'adoucissement des marches le
  modifient localement (attribut `z_modele` sur les sommets corrigés). Les ≈ 100 fissures de sol ouvert sont des
  surfaces de part et d'autre d'une même bordure qui se touchent au-delà de son empreinte (limites D2).
- Le lecteur ne transmet pas les listes de listes (`caniveau.intervalles`) : pj::caniveau les relit dans `props`.
- La couverture dense de BRF / gravier (Scatter + Copy to Points, désactivée) n'est qu'un aperçu ; l'USD porte les
  remplissages texturés et les éclats épars.
- La comparaison des pivots avec la pose numpy apparie par abscisse : les bordures dont l'origine diffère donnent les
  grands écarts (p95).

## 9. Intégration : site complet, déterminisme, Houdini interactif, Unreal (agent intégration, 11/10/2026)

### 9.1 Fabrication du site complet

`hython recon/pcg/houdini/fabriquer_hda.py --verifier-determinisme` cuit la scène maîtresse de bout en bout : lecteur,
huit HDA de branche, préparation de l'export, Solaris, USD ROP, points, matériaux, paquets pour Unreal.

| Branche | HDA (nœuds) | Sortie USD | Primitives | Instances | `verifier_usd` |
|---|---|---|---|---|---|
| `sol` | `pj::sol` (71) | `sol.usdc` | 1 220 758 | — | 0 erreur, 82 avert. |
| `bordures` | `pj::bordure` (71) | `bordures.usdc` + `prototypes/bordures.usda` | 578 194 | 14 424 | 0 erreur, 285 avert. |
| `caniveaux` | `pj::caniveau` (71) | `caniveaux.usda` + prototypes | 1 931 | 141 | 0 erreur |
| `ilots` | `pj::ilot` (61) | `ilots.usda` + prototypes | 19 711 | 397 | 0 erreur, 8 avert. |
| `marquages_lignes` | `pj::marquage_ligne` (19) | `marquages_lignes.usda` | 41 217 | — | 0 erreur, 3 avert. |
| `passages` | `pj::passage_pieton` (16) | `passages.usda` | 15 968 | — | 0 erreur, 1 avert. |
| `symboles` | `pj::symbole_iisr` (25) | `symboles.usda` + prototypes | 6 830 | 85 | 0 erreur, 1 avert. |
| `zones` | `pj::marquage_zone` (26) | `zones.usda` | 6 943 | — | 0 erreur, 3 avert. |

- Les avertissements portent tous sur des arêtes douces cassées aux coutures.
- Lecteur : 2 563 primitives et 165 269 points.
- Durées d'une passe (Ryzen 9 7900X), cuisson / total avec écriture USD, canonisation et `verifier_usd` :
  - lecteur : 2,1 s ;
  - sol : 10 s / 139 s ;
  - bordures : 18 s / 96 s ;
  - les six autres branches : moins de 6 s chacune ;
  - passe complète : 252 s seule, 280 s quand deux passes tournent en parallèle ; paquets pour UE : 4 à 5 s ;
  - total avec la deuxième passe de vérification : 525 à 559 s.
- Le temps va surtout à l'écriture et au contrôle des gros USD, pas à la cuisson.

### 9.2 Déterminisme

Une passe est identique à l'octet à une autre passe, dans le même processus (`--verifier-determinisme`) comme dans un
autre processus (`--sortie AUTRE` puis comparaison des empreintes `sorties`) : 17 fichiers sur 17, plus l'empreinte du
lecteur. Trois processus indépendants (dernière passe, passe parallèle, passe précédente) donnent les mêmes 17
fichiers : `fabrique_hda/controle/determinisme_processus.json`. Deux causes de différences entre processus ont été
trouvées et corrigées :

1. **JIT natif de VEX** (`HOUDINI_VEX_JIT_OPTIMIZE` « native=on », réglage par défaut).
   - Sur six processus, la sortie du nœud `poser` de `pj::bordure` (pilote) prend deux valeurs différentes. Les écarts
     sont au dernier bit, puis atteignent 0,8 mm et une face de plus ou de moins après les Boolean et PolyBevel. Le
     sol, les îlots et les lignes ont le même défaut.
   - Avec `HOUDINI_VEX_DISABLE_JIT=1`, six processus sur six sont identiques. Le pilote se relance avec cette variable,
     sauf option `--vex-jit`. Coût mesuré : aucun (passe de 252 s contre 258 s avec le JIT).
2. **Writer `.usdc` (crate)**.
   - Le même contenu donne des octets différents d'un processus à l'autre : textes USD exportés identiques,
     binaires différents (ordre de tables hachées sur adresses).
   - `canoniser_usdc` relit chaque `.usdc` en texte canonique et le réécrit depuis ce texte : deux processus donnent
     alors les mêmes octets. Coût : environ 9 s pour `sol.usdc` et 5 s pour `bordures.usdc`.

En interactif (Houdini, Houdini Engine dans UE), le JIT reste actif : la géométrie peut différer au dernier bit de la
fabrication batch. Pour reproduire exactement, ajouter `HOUDINI_VEX_DISABLE_JIT = 1` dans `houdini.env`.

### 9.3 Dans Houdini (interactif)

1. Ouvrir `recon/pcg/houdini/paquet_jardin_pcg.hip` dans Houdini 22.0.459.
   - La scène recharge d'elle-même les HDA depuis `recon/pcg/houdini/hda/**` (chemins enregistrés, vérifié dans un
     hython neuf).
   - Sur une autre machine : *Assets > Install Asset Library*, puis `fabrique_hda/hda/pj_paquet_jardin.hdalc`.
2. Variables (*Edit > Aliases and Variables*) :
   - `$PJ_DESCRIPTION` : dossier `description/base` ;
   - `$PJ_SORTIE` : dossier des USD.
3. Pour une cuisson rapide, régler `/obj/paquet_jardin/lire_description`, onglet *Emprise*, sur `pilote` (0,4 s) ou
   `boîte`.
   - *Filtre d'identifiants* (`K-03* S-0213a`) isole quelques entités.
   - Les familles et le mode d'altitude sont dans l'onglet *Description*.
4. Sélectionner un `fab_<branche>` et mettre le drapeau d'affichage sur `SORTIE_<branche>`. Paramètres utiles :
   - `fab_bordures` / `fab_caniveaux` :
     - *Pose* : joint par défaut, joints variables, flèche max, coins ;
     - *Aspect* : jitter, chanfrein, épaufrures ;
     - *Sorties* : maillages ou instances empaquetées ;
     - *Courbe tracée (Unreal)* : courbes sans attributs.
   - `fab_sol` : onglet *Raccords aux bordures*, arêtes cibles par classe, BEV.
   - `fab_marquages_lignes`, `fab_passages`, `fab_symboles`, `fab_zones` : épaisseur, enfouissement, chanfrein, pas
     du drapé, tolérances (§ 7).
   - `fab_ilots` : bombement, couverture dense (aperçu).
5. Écrire une couche : `/stage/rop_<branche>` puis *Save to Disk*, ou lancer le pilote (§ 5), qui applique aussi la
   remise à plat des données de calque et la canonisation.
6. Contrôles visuels :
   - `/obj/apercu_lecteur` et `/stage/apercu` : courbes du lecteur sur le relief ;
   - `hda/commun/rendre_integration.py` : toutes les couches, plus les symboles instanciés.
7. Tracer une courbe soi-même :
   - un Curve SOP branché sur l'entrée 1 de `pj::bordure` ; l'onglet *Courbe tracée (Unreal)* sert aussi dans
     Houdini ;
   - ou l'entrée facultative de `pj::lire_description` (entités supplémentaires, avec attribut `famille`).

### 9.4 Dans Unreal 5.8.3 (Houdini Engine v4.0.2)

**Préparer `pj::bordure` pour une courbe d'Unreal** (`hda/pj_bordure/construire.py`, nœuds `completer_unreal`,
`attributs_unreal`, `vider_*`, `sortie_unreal_*`). Le même réseau sert `pj::caniveau`.

- Une courbe **sans** `intervalles` ni `famille` (spline Houdini Engine, spline UE en entrée World, spline PCG,
  courbe tracée à la main) reçoit les attributs de la description depuis l'onglet *Courbe tracée (Unreal)* :
  - identifiant (`ue_id`) ;
  - profil et vue courants ;
  - matériau et usure ;
  - abaissé de traversée : début et fin de la partie abaissée, profil `T2_bateau`, vue 0,02 (GA-ABA-001) ;
  - rampants (chartières) de longueur L = min(2,00 ; Δh/0,05), au moins Δh/0,08 (GA-ABA-004) ;
  - points durs aux changements de profil (GA-BOR-005) ;
  - pied de face = Z de la courbe + décalage (`niv_s` / `niv_z_pied` tirés de la courbe, TQ-SOL-013).
- Une courbe de la description passe inchangée. Vérifié : sortie du pilote identique avant et après l'ajout
  (empreinte `084272117489`).
- `unreal_material` = `/Game/PJ/Materials/MI_<materiau_id>` sur chaque face ou instance empaquetée.
- *Sorties 2 et 3 vides (Houdini Engine)* (`sorties_unreal`) : Houdini Engine convertit toutes les sorties. Sans
  cette option, il crée les prototypes à l'origine et des instances de `/Game/PJ/Lib/Bordures/SM_*` absentes.
- Les entrées des HDA portent maintenant leurs libellés : « Bordures (courbes) », etc. Avant, le libellé par défaut
  du subnet (« Sub-Network Input #1 ») les remplaçait (`pj_hda_outils.creer_hda`, `VERSION_OUTILS = 2`).

**Utilisation dans l'éditeur.**

1. Importer `fabrique_hda/hda/pj_bordure.hdalc` (une seule définition) dans `/Game/PJ/Houdini` : glisser-déposer ou
   `AssetImportTask`.
2. Poser l'asset dans un niveau.
3. Entrée 1 : type *Curve* pour dessiner une spline Houdini, ou type *World* avec un acteur qui porte une spline UE.
4. Onglet *Courbe tracée (Unreal)* : profil, vue, abaissé.
5. Cocher *Sorties 2 et 3 vides* et choisir *Sortie 1 = Instances empaquetées* : un ISM par prototype, ou un
   StaticMeshComponent pour un prototype à une seule instance.
6. Cuire puis faire un *Bake*. Avant le bake, Houdini Engine range ses maillages temporaires dans
   `/Game/HoudiniEngine/Temp/`, qui sont enregistrés avec le niveau.

**Essai mesuré** (`hda/ue/piloter_essai_he.py`, script UE `hda/ue/essai_he_bordure.py`, rapport
`fabrique_hda/controle/essai_houdini_engine_ue.json`, niveau d'essai `/Game/PJ/Maps/PJ_Test_HDA`, jamais `PJ_2026`).

- Courbe Houdini de 12 m (5 points, pente 1 %), posée par la Public API (`HoudiniPublicAPICurveInput`). Abaissé de
  5 à 7 m, rampants de 2 m (règle), joints de 6 mm non aléatoires.
- Cuisson en 3,3 s :
  - 12 éléments : 6 droits T2 de 0,994 m, 4 chartières de raccord, 2 bateaux `T2_bateau` ;
  - 11 joints de mortier, tous à 6,0 mm, avec les matériaux `MI_beton_bordure_gris` et `MI_mortier_joint`.
  - C'est le même compte que dans Houdini, sur la même courbe.
- `joint_mm` passé de 6 à 10 par `set_float_parameter_value`, recuisson automatique en 3,1 s :
  - 12 éléments, 11 joints de 9,0 à 9,5 mm (p50 9,1 mm) ;
  - la largeur est bornée à 3,5-9,5 mm moins le terme de coin (bordures_elements.json, TQ-BOR-005 : joints de 3,5
    à 9,5 mm).
- Captures `controle/he_bordure_joint{6,10}_{ensemble,joints,macro_joint}.png` : la vue macro montre le joint
  élargi.
- Piège constaté : après un réimport de l'HDA dans une session déjà ouverte, une instance neuve a lu des flottants
  incohérents (vue 0, coin max infini). Le pilote relance donc la session Houdini Engine (`restart_session`) avant
  d'instancier, et relit les paramètres (`parametres_lus`).

**PCG** (nœud « Houdini Digital Asset »).

Ce qui marche par Python :

- le graphe `/Game/PJ/Houdini/PCG_Bordure_HDA` : Get Spline Data (acteur porteur) → Houdini Digital Asset
  (`houdini_asset` = pj_bordure, sortie *Cook*, cache PCG coupé) ;
- un *Create Attribute Set* par paramètre de l'HDA sur la broche *Parameters* (nom de l'attribut = nom du paramètre) ;
- les broches de l'HDA, qui apparaissent après l'instanciation du cookable de paramètres ;
- l'acteur d'essai (spline UE linéaire de 12 m + composant PCG) ;
- la génération : Houdini Engine instancie et cuit l'HDA (`HoudiniPCGActor`).

Ce qui ne marche pas encore :

- L'entrée de l'HDA est de type *Geometry* (type déduit du libellé). Il faut le type *PCG Input* pour que la spline
  PCG soit envoyée.
- Ce réglage vit dans le `ParameterCookable` du nœud, protégé et illisible depuis Python (« is protected and cannot
  be read »). La cuisson se fait donc sans courbe : « FinishedCooking with errors », seul le logo Houdini apparaît.
- Réglage manuel (non vérifié) : ouvrir le graphe, sélectionner le nœud, mettre l'entrée « Bordures (courbes) » en
  *PCG Input*, puis régénérer `PJ_Essai_Bordure_PCG`.
- Ne jamais supprimer ni recréer par script un graphe PCG en service. La suppression échoue (« package potentially
  corrupt »), puis `create_asset` ouvre une boîte modale « Overwrite Existing Object » qui bloque l'éditeur. Le
  script vide et reconstruit le graphe existant à la place.

### 9.5 Fichiers de l'intégration

| Fichier | Rôle |
|---|---|
| `recon/pcg/houdini/fabriquer_hda.py` | pilote : relance sans JIT, durées, empreintes SOP, `produits`, `--comparer`, canonisation `.usdc`, bibliothèques unitaires |
| `recon/pcg/houdini/paquet_jardin_pcg.hip` | scène maîtresse, huit HDA branchées (`--construire-hip`) |
| `hda/commun/pj_hda_outils.py` | libellés d'entrées des HDA (`VERSION_OUTILS`) |
| `hda/pj_bordure/construire.py` | onglet *Courbe tracée (Unreal)*, `unreal_material`, sorties 2 et 3 vides pour Houdini Engine |
| `hda/commun/rendre_integration.py` | contrôle visuel de toutes les couches (Karma XPU) |
| `hda/ue/piloter_essai_he.py`, `essai_he_bordure.py`, `niveau_courant.py`, `vider_journal.py` | essai Houdini Engine et PCG dans UE |

## 10. Corrections après les revues conformité et réalisme (agent corrections, 11/10/2026)

Chaque correction cite sa règle ; les HDA sont reconstruites par `fabriquer_hda.py --construire-hda --toutes`, la scène
par `--construire-hip`.

| HDA / fichier | Correction | Règles |
|---|---|---|
| `pj_sol/reseau_sol.py` (boucle de triangulation, partagée avec `pj::ilot`) | nœud **Reverse `retourner_trous`** (groupe `@anneau>0`) avant Triangulate 2D : le lecteur oriente tous les anneaux en +Y, Triangulate 2D ne retirait donc pas les trous (S-0094a maillée sur 14 722 m² au lieu de 11 598 m², sol en double couche, taches et refuges en éclats) | TQ-SOL-009, TQ-SOL-001 |
| `pj_sol/vex/sol.vfl` `//@@ trous` | test **pair-impair** explicite (boîte puis nombre de croisements) au lieu de `xyzdist` (peu fiable sur un polygone concave) | TQ-SOL-009 |
| `pj_sol` `petits_trous` (+ paramètre *Trous comblés sous (m²)*, 2 m²) | trou d'anneau sans surface décrite dedans (mât, armoire « bâtiment » v1) comblé par la surface : plus de vide noir | TQ-SOL-009 |
| `pj_sol` passes `marches_*` | la noue n'est plus exclue de l'adoucissement : triangles de noue de plus de 25° adoucis (talus voulu à 1/3 = 18,4° sous le seuil ; 329 triangles à plus de 20°, jusqu'à 71°, avant) | GA-ASS-005, VAL-SOL-009 (1b) |
| `pj_sol` `falaises` | triangle encore > 45° et > 0,25 m après les passes d'adoucissement (goulet entre deux plateaux du modèle) retiré et compté (`pj_sol_falaises`, avertissement) | E8, VAL-SOL-009 (1) |
| `pj_sol` `tuiles_x_*`, `tuiles_y_*` | deux boucles **For-Each par nombre** de **Clip SOP** (deux côtés gardés, points de coupe partagés) : sol coupé exactement aux lignes de tuile de `tuile_m` (débord 0,83 m avant) | TQ-SOL-003, TQ-SOL-010 |
| `pj_sol` `controle_aires` | aire maillée de chaque surface comparée à `aire_m2` (0,5 % et 0,05 m²) : détail `pj_sol_controles`, avertissement du nœud | TQ-SOL-001, TQ-SOL-009 |
| `pj_marquage_solide` (entrée 3 *Sol fabriqué*, onglet Drapé : *Draper sur le sol fabriqué*, *Portée*) | drapé sur le **sol réellement maillé** (`pj_m_z_sol` : `intersect_all` vertical autour du modèle, région de la pièce d'abord, BEV exclues) et non plus sur le seul modèle (pj::sol le modifie : raccords, marches ; peinture enterrée jusqu'à −66 mm avant) | TQ-MQG-005, TQ-SOL-013, CF-26 |
| `pj_marquage_ligne`, `pj_passage_pieton`, `pj_symbole_iisr`, `pj_marquage_zone` | 3ᵉ entrée *Sol fabriqué (facultatif)* relayée au solide ; `fabriquer_hda.construire_hip` y branche `SORTIE_sol` (entrée repérée par son libellé) | TQ-MQG-005 |
| `pj_symbole_iisr` `poses` | plan de pose ajusté sur le sol fabriqué, grille de 0,25 m sous l'emprise + 0,25 m, tolérance de planéité **1 mm** (3 mm avant) : au-delà, symbole drapé | TQ-MQG-006 |
| `pj_marquage_ligne` | épaisseur des lignes **2 mm** (enduits et autres marques : 3 mm), pas max le long de l'axe 0,25 m (drapé entre sommets) | TQ-MQG-002, TQ-MQG-011 |
| `pj_marquage_zone` (zigzag) | un seul polygone à onglets limités (3 h) au lieu de rectangles et biseaux réunis (éclat en pointe au sommet) | MQ-BUS-005 |
| `pj_ilot` `petits_trous` (+ *Trous comblés sous (m²)*) | même comblement des petits trous dans les remplissages (emprises de mâts portés) | TQ-SOL-009 |
| `pj_ilot/vex/ilot.vfl` `altitude_ilot` | tête de ceinture interpolée en 1/d⁴ sur les **stations** de la ceinture et non au point projeté : sur un anneau (K-0390) le projeté sautait d'un bord à l'autre sur l'axe médian, d'où le pli et le « trou carré noir » de I-0390 (5 triangles verticaux, 0 après) | TQ-SOL-013 (7), GA-ARB-003 |
| `pj_ilot/vex/ilot.vfl` | éclats : `scale` = taille seul (le `pscale` en plus donnait taille², éclats invisibles) | TQ-PCG-001 |
| `pj_ilot/construire.py` (`copeau`) | Box SOP en `polymesh` : faces fermées (le type `poly` à divisions donnait des polygones ouverts, exportés en BasisCurves) | contrat E6 |
| `recon/pcg/ue/contrat/verifier_usd.py` | erreur E6 pour tout gprim non Mesh (BasisCurves, Points) en finalité default/render | contrat E6 |

Contrôle local (pilote et site, description du 11/10/2026) : dessus de peinture − sol fabriqué = 2,0 mm (lignes) et
3,0 mm (autres) à tous les sommets ; double couche stricte (nœud contenu dans deux triangles de sol hors BEV) de
2 700 m² à environ 6 m² (éclats d'emprise de bordure de 1 cm, cachés par les éléments) ; débord de tuile 0.
