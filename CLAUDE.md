# Consignes pour Claude (dépôt ClaudeCode_RoadCreation)

## Analyse d'images : toujours en tuiles natives avec recouvrement

Une image plus grande que l'entrée image native de Claude est réduite avant d'être vue. Sur l'ortho 5 cm, un trait de 15 cm (3 px) ou un panneau lointain disparaît alors.

- Avant d'analyser visuellement une image (ortho, photo, rendu, capture, planche), découpe-la avec `recon/pcg/vision/decoupe.py`. Il produit des tuiles de 1092 × 1092 px au plus, avec 20 % de recouvrement par défaut. Augmente le recouvrement jusqu'à la taille du plus grand objet cherché.
  - `ortho` : tuiles géoréférencées au pas natif (PCRS 2022 à 5 cm, IGN 2024 à 20 cm). Un fichier `.pgw` et `tuiles.json` donnent les coordonnées locales et L93 de chaque tuile.
  - `equirect` : photos 360° en vues perspectives sur tout l'horizon. Le champ de vision est réglé sur la résolution angulaire de la source.
  - `image` : photos planes, rendus, captures.
  - `verifier` : contrôle qu'une image entre sans réduction (grand côté ≤ 1568 px et aire ≤ 1092² px).
- Pour un objet précis, fais plutôt une découpe ciblée à sa projection (`recon/pcg/enrichir/projection.py:decoupe_perspective` ou `vue_equirect`), à la taille native.
- Planches : chaque fichier doit entrer sans réduction. Pas de planche haute à 6 panneaux. Au-delà, écris un fichier par panneau.
- Ne conclus jamais sur un détail vu dans une image réduite : redécoupe-la.

## Rappels du projet

- Les photos de tiers (Panoramax, Mapillary) et les tuiles ou planches qui en contiennent vont dans un dossier `photos_non_versionnees/` (ignoré par git). Street View est interdit. City Sample est interdit hors d'Unreal.
- Le jeton Mapillary se lit seulement dans `%USERPROFILE%\.config\meylan_adas\mapillary_token.txt`. Il ne doit jamais être affiché ni écrit.
- Ne pas modifier `assets/specs/{bordures,vegetation,mobilier,carla_correspondances}.json` : ils appartiennent à une autre équipe.
- Cible actuelle : l'état avant travaux (`recon/pcg/etat`, sorties dans `recon/out/paquet_jardin/v2_avant_travaux/`). `recon/out/paquet_jardin/v2/` est l'archive gelée de l'état 2026 (étiquette `etat_2026_gel`).
