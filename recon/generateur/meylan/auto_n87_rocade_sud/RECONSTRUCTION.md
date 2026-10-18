# Reconstruction de `auto_n87_rocade_sud` (étape 3, lot SITES autoroute et axes)

*18/10/2026. N87 Rocade Sud à Meylan, 1,1 km du pont de l'Isère au nœud A41 / N87 (`N_N87_NOEUD`). Aucune image dans
ce fichier : planches sous `recon/out/generateur/comparaison/meylan_auto_n87_rocade_sud/photos_non_versionnees/`.*

## État décrit

- **Date d'état** : **13/09/2026** (itération 1) au lieu du 23/06/2024 : trois photos du 13/09/2026 (0feb1b4f,
  53f09e82, 8aa90ca1) trouvées par la comparaison montrent le même état que la série de 2024.
- **Fabrication** : `fabriquer_generateur.py … --complet` (chaîne autoroute ; 3,0 M faces de sol ; DBA et glissières
  posées par rg::autoroute). Origine déplacée par le premier passage (BESOINS G1).
- **Rendus seuls** : `recon/out/generateur/meylan_auto_n87_rocade_sud/rendus/` (`dessus.png`, `oblique_34.png`,
  `conducteur_autoroute.png`) ; itération 0 dans `rendus_it0/`.

## Itérations

| It. | Ce qui change | Pourquoi (preuve) |
|---|---|---|
| 0 | description du lot B harmonisée (N87 prolongée de 103 m jusqu'au nœud) | — |
| 1 | bord extérieur du sens sud : **glissière** jusqu'à s ≈ 650, puis **muret béton écrit `GBA`** ; date d'état 13/09/2026 | 53f09e82 (s ≈ 470) et 8aa90ca1 (s ≈ 380) montrent une glissière ; 2e993fc0 (s ≈ 777) un muret ; le mot `muret` n'était pas fabriqué (BESOINS N-1) |

## Comparaison multivues, itération 0 (6 photos, 4 quadrants, 4 séquences)

Fenêtre de comparaison de 480 m autour de l'aire de service (BESOINS C-1 : 0 photo sur la scène entière). Recouvrement
des contours à 3 px médian 0,30 → 0,61 ; écart moyen médian 10,2 → 7,2 px ; 6 poses affinées sur 6 (confiance haute 2,
moyenne 4).

| Photo | Date | Vue | Ressemblance | Constat principal |
|---|---|---|---|---|
| 0feb1b4f | 13/09/2026 | conducteur vers le nord | bonne | 2 voies, BAU, glissière, DBA : très ressemblant |
| 8dc93bc5 | 23/06/2024 | vers la DBA | moyenne | DBA à sa place mais claire et d'aspect plat au rendu (mur gris sur la photo) |
| 922f52c4 | 23/06/2024 | conducteur vers le sud | bonne | voie de l'aire de service (T2 5u) à la bonne place |
| 490b4ca9 | 23/06/2024 | vers la DBA | moyenne | même constat que 8dc93bc5 |
| 53f09e82 | 13/09/2026 | vers l'ouest | moyenne | glissière extérieure de la chaussée sud absente (muret décrit, non fabriqué) |
| 8aa90ca1 | 13/09/2026 | vers l'ouest | bonne | DBA et rive justes ; glissière extérieure absente |

## Comparaison multivues, itération 1

*(en cours ; mêmes photos, poses recalculées sur le modèle corrigé)*

## Écarts restants

- Aspect de la DBA (BESOINS N-2), voie de l'aire de service qui naît et disparaît d'un coup (N-3).
- Station-service, portiques de signalisation, PMV : hors route seule (E14, E15).
- Enrobé fissuré et ponté sur les photos, homogène au rendu.
