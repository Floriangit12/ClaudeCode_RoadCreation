# Reconstruction de `auto_noeud_a41_n87` (étape 3, lot SITES autoroute et axes)

*18/10/2026. Nœud A41 / N87 : l'A41 sur 1 218 m (`N_A41_N87_O` → `N_A41_MEYLAN_EST_O`) et 6 bretelles (boucle, branche
vers Chambéry, « A41 vers N87 sud », sortie Sisteron, hélice de Meylan, « Meylan vers A41 La Tronche »). Aucune image
dans ce fichier : planches sous `recon/out/generateur/comparaison/meylan_auto_noeud_a41_n87/photos_non_versionnees/`.*

## État décrit

- **Date d'état** : 14/06/2025 (inchangée ; photos de la comparaison du 23/06/2024 au 28/02/2026, cohérentes).
- **Fabrication** : `fabriquer_generateur.py … --complet` (chaîne autoroute ; 3,0 M faces de sol, 0,40 M faces de
  peinture, 25 séparateurs, **0 musoir**).
- **Rendus seuls** : `recon/out/generateur/meylan_auto_noeud_a41_n87/rendus/` : `dessus.png` (84 m),
  `dessus_ensemble.png` (vue zénithale de ≈ 750 m), `oblique_34.png` ; itération 0 dans `rendus_it0/`. L'oblique montre
  l'échangeur **à plat** : les bretelles et leurs glissières croisent l'A41 à niveau (BESOINS ND-1).

## Itérations

| It. | Ce qui change | Pourquoi (preuve) |
|---|---|---|
| 0 | description du lot B harmonisée par le lot N1 | — |
| 1 | une seule glissière dans le TPC, le long de la BDG sud (comme la section courante) ; murets de l'hélice écrits `GBA` | 949a4e59 (s ≈ 450, vers le nord : rail proche puis herbe), 91d270d4 (s ≈ 563, vers le sud : herbe puis rail contre la chaussée sud), 7b271e3a ; `muret` non fabriqué (BESOINS ND-5) |

## Comparaison multivues, itération 0 (8 photos, 4 quadrants, 5 séquences)

Fenêtre de 220 × 200 m autour du pont de la N87 sur l'A41 (BESOINS C-1). Recouvrement à 3 px médian 0,22 → 0,36 ;
écart moyen médian 15,2 → 14,3 px ; 4 poses affinées sur 8 (moyenne 3, faible 5).

| Photo | Date | Vue | Ressemblance | Constat principal |
|---|---|---|---|---|
| 56bd3642 | 28/02/2026 | vers l'ouest | faible | A41 juste, mais chaussées et glissières des bretelles la traversent à niveau |
| 7b271e3a | 28/02/2026 | vers l'est | moyenne | profil juste, pont de la N87 absent, TPC à une seule glissière |
| 41d24a2b | 23/06/2024 | sur la bretelle haute | non jugeable | photo prise au niveau haut |
| 949a4e59 | 14/06/2025 | vers le TPC | moyenne | une seule glissière (côté sud) |
| dd50b13a | 01/06/2025 | divergence | faible | musoir à chevrons et voie quittante absents (bretelle parallèle bordée de glissières) |
| f7663ef0 | 23/06/2024 | sur la bretelle haute | non jugeable | idem 41d24a2b |
| 91d270d4 | 01/06/2025 | vers le TPC | moyenne | confirme la glissière unique côté sud |
| fbaa7334 | 14/06/2025 | sous le pont | faible | piles et tablier absents ; photo surexposée |

## Comparaison multivues, itération 1

*(en file d'attente : mêmes photos, poses recalculées)*

## Écarts restants (manques du générateur, BESOINS.md)

Niveaux et ouvrages (ND-1, ND-2), divergences et musoirs (ND-3), glissières autour des piles (ND-4). Ce site reste
une ressemblance « en plan » : les tracés et profils des chaussées sont justes, l'échangeur en élévation ne l'est pas.
