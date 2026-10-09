# Reconstruction 3D — conventions communes (carrefour Paquet Jardin, puis Meylan)

Cible : simulateur ADAS sous **Unreal Engine 5.8**, préparation et raffinement procédural sous
**Houdini 21**. Chaîne retenue :

```
données ouvertes (GeoJSON, rasters, LiDAR)                       [cloud, ce dépôt]
   └─► couches « état 2026 » normalisées (recon/out/<site>/*.geojson, *.tif)
         ├─► OpenDRIVE (.xodr)  : topologie, voies, manœuvres, signaux  → logique ADAS / trafic
         ├─► USD (.usda/.usdc)  : maillages chaussée, trottoirs, îlots, bordures, marquages
         │                        (décalques avec usure), arbres/mobilier (instances), bâtiments
         └─► textures/masques   : macro-albédo enrobé (ortho 5 cm nettoyée), masques d'usure,
                                  rapiéçages, fissures (GeoTIFF/PNG 16 bits, 5 cm)
                                                                  [PC de l'utilisateur]
   Houdini 21 (Solaris/SOP) : import USD + scripts → raffinement (biseaux, décals, scatter)
   Unreal 5.8               : import USD (ou Houdini Engine) + matériaux + OpenDRIVE
```

## Repère
- Référence géographique : **Lambert-93 (EPSG:2154)**, altitudes **NGF-IGN69**.
- **Repère local du site** (toutes les sorties 3D) : origine `O = (917279.43, 6460289.98, 216.30)`
  - `X = Est − 917279.43` (m), `Y = Nord − 6460289.98` (m), `Z = altitude − 216.30` (m)
  - USD : `upAxis = "Z"`, `metersPerUnit = 1.0`. Unreal convertit à l'import (cm, Y inversé).
  - Houdini est en Y-up : les scripts fournis appliquent la rotation (X, Z, −Y) ou laissent la
    scène en Z-up selon l'option choisie (voir `recon/houdini/README.md`).
- Repère d'axe de Verdun utilisé dans l'analyse : `u` le long de Verdun vers le NE, `v` vers le NW :
  `x = 917279.43 + 0.7071 (u − v)`, `y = 6460289.98 + 0.7071 (u + v)`.

## Emprise
Site `paquet_jardin` : carré de 300 m centré sur O (x 917129.43 → 917429.43, y 6460139.98 → 6460439.98).

## Date de l'état modélisé
**Octobre 2026 (après les travaux C1 de 2025)** pour la géométrie, la topologie et les marquages :
- cœur du carrefour : levés topographiques GAM (= projet 2025, vérifié), complétés par le plan
  projet géoréférencé (terre-plein planté, flèches, lignes d'arrêt, queue d'îlot Vercors) ;
- topologie (sens, nb de voies, arrêts) : OSM 2026 ;
- hors cœur : levés GAM / PCRS vecteur, ortho 5 cm 2022 (inchangé) ;
- relief : LiDAR HD 2021 (inchangé hors îlots refaits) ;
- texture et usure : ortho 5 cm 2022 + photos 2023-2025 ; marquages refaits en 2025 → usure 0-1.
Le mobilier secondaire (poubelles, potelets) peut être d'une autre date : sans impact ADAS.

## Classes de surface (attribut `classe`)
`chaussee`, `piste_cyclable`, `trottoir`, `ilot` (îlot/refuge minéral), `terre_plein_vegetal`,
`espace_vert`, `quai_bus`, `parking`, `acces_riverain`, `chantier`, `batiment`, `autre`.

## Marquages (attribut `type`)
`ligne_continue`, `ligne_discontinue` (préciser `modulation` T1/T2/T3 et `largeur_m`), `ligne_stop`,
`ligne_effet_feux`, `passage_pieton_bande`, `traversee_cyclable`, `fleche` (+ `direction`),
`symbole_velo`, `symbole_bus`, `zigzag_arret_bus`, `hachures`, `chevrons`, `damier`, `texte`,
`fantome` (ancien marquage effacé). Couleur : `blanc`, `jaune`, `ocre`, `vert`.
Usure : `usure` ∈ {0,1,2,3,F} (cf. analysis/paquet_jardin/CONTEXT.md) + `couverture` (0-1).

## Contrôle qualité (obligatoire)
Chaque couche est rendue en **tuiles 1000×1000 px à 5 cm** sur l'ortho 2022, le plan projet
et/ou les levés GAM (`recon/qa_render.py`) et examinée visuellement ; écarts listés et corrigés.
