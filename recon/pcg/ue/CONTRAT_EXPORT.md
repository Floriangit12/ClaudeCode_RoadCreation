# Contrat d'export Houdini → Unreal (`pj_usd/0.1`, `pj_points/0.1`)

Ce contrat fixe ce que les HDAs `pj_*` (hython, Houdini 22) écrivent pour Unreal 5.8.3 (`D:/ClaudeADAS`).
Il se vérifie par programme :

- `contrat/verifier_usd.py` contrôle un USD (pxr seul : hython, Python de l'éditeur UE).
- `contrat/echantillon_contrat.usda` est l'échantillon de référence ; `echantillon_contrat.py` le régénère.
- `contrat/test_contrat.py` (éditeur ouvert) vérifie l'échantillon, l'importe et applique le critère d'acceptation, avec deux contrôles négatifs sur la couche v1. Le rapport est écrit dans `recon/out/paquet_jardin/v2/ue_phase0/contrat_export.json`.

**Critère d'acceptation d'un USD** :

1. `verifier_usd.py` ne renvoie aucune erreur.
2. `pj_tools.import_usd` renvoie `acceptation.ok = true`, c'est-à-dire aucune ligne `LogStaticMesh: Warning|Error` pendant l'import et la construction des meshes.
3. Chaque mesh importé a `recompute_normals = false` (normales du fichier), au moins un canal UV et `use_full_precision_u_vs = true`.

## 1. Repère et unités

- Repère **local** de la scène : local = Lambert-93 − O (917279,43 ; 6460289,98), z = NGF − 216,30. Les distances sont en mètres et Z est vers le haut. Ne jamais écrire du L93 brut : le vérificateur refuse toute coordonnée au-delà de 5 km (E1).
- Métadonnées de scène : `metersPerUnit = 1`, `upAxis = "Z"`, `defaultPrim = "World"`. Points en `point3f[]` : le float32 garde une précision de 0,03 mm à 300 m.
- `orientation = "rightHanded"` est conseillée. `leftHanded` est accepté, mais les normales doivent alors rester cohérentes avec l'enroulement des faces.
- L'importeur UE convertit seul : X = 100·x, Y = −100·y, Z = 100·z (cm, Y inversé). Le contrôle de la phase 0 donne un écart de 0,0005 cm. Il ne faut rien compenser côté Houdini.

## 2. Hiérarchie, kinds et fusion à l'import

```
/World                        Xform, kind = assembly
/World/Looks                  Scope : un Material par materiau_id utilisé
/World/<Couche>               Xform, kind = group        (Sol, Bordures, Marquages, Ilots…)
/World/<Couche>/<Entite>      Xform, kind = component    (une entité ou une tuile de sol)
    <Entite>/<nom>            Mesh(es) : un par matériau, ou un seul Mesh avec des GeomSubsets
```

- **Noms de prims** : uniquement `[A-Za-z0-9_]`, uniques dans la couche, et identifiant stable de l'entité (`K-0005` devient `K_0005`). Ce nom devient celui de l'asset UE (`SM_<Entite>`).
- **Import** : `pj_tools.import_usd(usd, dest, kinds_to_collapse=2)`. La valeur 2 (`component`) produit **un StaticMesh par component**, qui fusionne ses Mesh enfants et garde un slot de matériau par matériau.
  - `kinds_to_collapse` est un masque `EUsdDefaultKind` : model 1, component 2, group 4, assembly 8, subcomponent 16. Le défaut de l'outil, 0, donne un StaticMesh par Mesh USD ; les noms de Mesh doivent alors être uniques.
  - `use_prim_kinds_for_collapsing=false` désactive toute fusion. Les options effectives sont renvoyées dans `options`.
- **Taille d'un component** : moins de 500 000 triangles environ. Découper le sol en tuiles de 32 à 64 m, ou par entité, pour le culling et le streaming.
- **Points d'instances** : pas de `PointInstancer` dans une couche destinée à UE (E7), car UE recrée alors les meshes au lieu de référencer les assets de la bibliothèque. Une couche Karma qui en contient (par exemple `bordures.usda`) reste hors de l'import UE ; UE reçoit ces instances par `pj_points/0.1` (§ 7).

## 3. Géométrie et normales

- `Mesh` polygonal avec `subdivisionScheme = "none"`, obligatoire : sinon USD ignore les normales (E6). Faces planes (triangles ou quads), sans face d'aire nulle. `doubleSided = false`. `extent` renseigné.
- **Normales par sommet de face** : attribut `normals` (ou `primvars:normals`), interpolation `faceVarying` (ou `vertex` si aucune arête vive), vecteurs unitaires orientés vers l'extérieur.
- **Angle de rupture** (cusp) : 30° par défaut (SOP Normal : type *Vertex*, `cuspangle = 30`).
  - Une autre valeur se déclare dans `customLayerData["pj:cusp_deg"]`.
  - Le vérificateur (E2) exige que les arêtes de dièdre supérieur à cusp + 5° soient cassées : arêtes de bordure, chanfreins, joints sciés, nez d'îlot, bords de rampe.
  - Les arêtes de dièdre inférieur à cusp − 5° doivent être lissées : arrondis, dévers, terrain. Une arête lissée à tort ne donne qu'un avertissement.
  - Sans normales, UE lisse tout le mesh : boîte arrondie, dégradé courbe (constat de la phase 0).
- **Couleur de sommet** (facultative) : `primvars:displayColor` (color3f) avec R = usure, G = salissure, B = graine. UE l'importe en Vertex Color. Les autres primvars ne servent pas à UE ; `primvars:materiau_id` (constant) reste permis pour la traçabilité.

## 4. Coordonnées de texture

- **`primvars:st`** : `texCoord2f[]`, interpolation `faceVarying` (ou `vertex`), **en mètres réels** (1 unité UV = 1 m). Il devient l'UV0 d'UE. Le vérificateur (E3) exige une médiane de √(aire UV / aire 3D) comprise entre 0,9 et 1,1, et aucune face d'aire non nulle dégénérée en UV.
  - Sol, trottoirs, îlots : `st = (x, y)` local, ancré au monde, continu d'une tuile à l'autre. Les dalles et pavés sont alignés sur leur module (repère de l'appareillage).
  - Bordures, caniveaux : UV dépliés, avec u = abscisse le long de l'élément et v = périmètre du profil. Sinon, une projection boîte par face, comme dans `pj_bordure_prototypes`. **Jamais** de projection de dessus sur une face verticale : elle dégénère, donne des tangentes nulles et l'avertissement `LogStaticMesh` « degenerate tangent bases ».
- Le tuilage `tile_m` de `materiaux_sol.json` se règle **dans le matériau** (paramètre du `MI_<id>` côté UE, `UsdTransform2d` de facteur 1/tile_m côté Karma), jamais dans les UV.
- **`primvars:st1`** : second jeu facultatif, UV1 d'UE (par exemple un masque 0-1 par élément pour l'usure). Aucun autre `texCoord2f` n'est permis (E4), car UE numérote les canaux UV dans l'ordre lexicographique des noms. Vérifié : `st` seul donne UV0 ; `st` + `st1` donne UV0 et UV1 ; `st1` seul donne UV0.
- À l'import, UE écrit v' = 1 − v (convention de texture). L'aspect est identique ; ne rien compenser.
- `import_usd` règle `use_full_precision_u_vs` (vrai par défaut). En demi-flottant, des UV en mètres ont un pas de 0,125 m au-delà de 128 m.
- **Transition** :
  - Les sorties `pj_*` du 10/10 portent les UV métriques en `st1` seul. UE les place bien en UV0, et le vérificateur les tolère avec un avertissement. La cible reste `st`.
  - La bibliothèque CC0 Karma (`assets/lib/materiaux/*.usda`, `varname = "st1"`) doit passer à `st`. D'ici là, on peut écrire `st` et `st1` identiques.

## 5. Matériaux

- Un `Material` par matériau, nommé **exactement** d'après un `materiau_id` de `assets/specs/materiaux_sol.json` et placé à `/World/Looks/<materiau_id>` (E5).
  - Il doit être **présent dans la scène composée**, dans le même fichier ou par une sous-couche (`subLayers`).
  - Une liaison vers une couche non composée (par exemple `/World/Looks_v2/...` défini seulement dans `materiaux_v2.usda`) donne, dans UE, des faces sans matériau.
- Contenu du Material :
  - `outputs:surface` : un `UsdPreviewSurface` de repli (albédo cible, rugosité de la spec) ;
  - `outputs:unreal:surface` : un Shader avec `info:implementationSource = "sourceAsset"` et `info:unreal:sourceAsset = @/Game/PJ/Materials/MI_<materiau_id>.MI_<materiau_id>@`.
- **Liaison** : `MaterialBindingAPI` directe sur le Mesh, ou par `GeomSubset` (famille `materialBind`, type `partition`). UE crée un slot par sous-ensemble.
- **Comportement vérifié dans UE** :
  - Avec `render_context='unreal'` (le défaut) et un `MI_<id>` absent : le slot reste vide (matériau par défaut en damier) et un avertissement `LogUsd` apparaît. Il ne compte pas dans l'acceptation.
  - Avec `render_context='universal'` : des instances `MI_<materiau_id>` de prévisualisation sont créées dans le dossier d'import, puis remappées par leur nom.
  - Règle : importer en `unreal` une fois les `/Game/PJ/Materials/MI_<id>` créés ; avant cela, importer en `universal`.
    Les 34 `MI_<id>` existent (`materiaux/`, 10/10/2026) : importer en `unreal`. Les remplissages d'îlots
    (`MI_brf_*`, `MI_gravier_*`, `MI_gravillons_ilot`, `MI_galets_20_40`, `MI_paillage_mineral`) se déplacent par
    tessellation Nanite : importer leurs couches avec `nanite=True`.

## 6. Fichiers et déterminisme

- Format `.usda` (texte, comparable) ou `.usdc`, sans horodatage, ordre des prims fixé par le code, `customLayerData` avec `pj:contrat = "pj_usd/0.1"` et le hash de la description.
- Une couche par famille (`sol`, `marquages`, `ilots`…), plus `materiaux` en sous-couche commune. `manifest_fabrication.json` indique la cible de chaque couche (`ue`, `karma` ou les deux).

## 7. Points `pj_points/0.1`

```
{schema: "pj_points/0.1", famille, source_hash, repere, convention_rpy, pivot, bibliotheque,
 points: [{id, asset, p: [x, y, z], q: [x, y, z, w], rpy_deg: [r, p, y], s: [sx, sy, sz], graine, cd: [...], x: {...}}]}
```

- `p` : m locaux, Z haut ; c'est le pivot du prototype (base centrée, +X vers l'avant, sauf convention déclarée dans `pivot`).
- **`q` (à privilégier)** : quaternion unitaire **`[x, y, z, w]`** de la rotation dans le repère local. C'est l'ordre de l'attribut `orient` de Houdini. Attention : `Gf.Quat*` et `pj_commun.quat_de_matrice` sont dans l'ordre (w, x, y, z).
- `rpy_deg` (lisible, facultatif si `q` est présent) : angles ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r), rotations directes autour des axes locaux.
  - Quand `q` et `rpy_deg` sont tous deux présents, ils doivent concorder à 0,05° près, sinon `charger_points` refuse le fichier.
  - Si `q` est présent, `charger_points` l'utilise.
- **Conversion vers UE** : une seule implémentation, dans `pj_tools/pj_tools/repere.py`.
  - `quat_local_vers_ue` : Quat(−x, y, −z, w).
  - `rpy_local_vers_ue` : Rotator(roll = r, pitch = −p, yaw = −y).
  - Les deux sont la conjugaison par le miroir M = diag(1, −1, 1). La preuve par comparaison des axes est dans `tests/test_rotations.py` (Python pur et éditeur).
- `s` : échelle par axe du prototype. `graine` : entier sur 31 bits. `cd` : données d'instance. `x` : informations libres, non lues par UE.
- **Chargement** :
  1. `pj_tools.charger_points(json, /Game/PJ/PCG/Donnees/PDA_<famille>)` cuit le fichier en PCGDataAsset ; le PDA est réécrit en place.
  2. Le nœud natif `Load PCG Data Asset` le relit, puis `Static Mesh Spawner` (`MeshSelectorByAttribute` sur `Mesh`) pose les instances.
