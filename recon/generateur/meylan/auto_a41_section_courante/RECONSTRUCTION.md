# Reconstruction de `auto_a41_section_courante` (étape 3, lot SITES autoroute et axes)

*18/10/2026. A41 à Meylan, section courante de 550 m entre `N_A41_PEPINIERES_O` et `N_A41_N87_O`. Description
grossière d'après les photos Panoramax, l'ortho IGN 2024 et OSM ; le détail vient des règles. Aucune image dans ce
fichier : les planches photo | rendu sont sous `recon/out/generateur/comparaison/meylan_auto_a41_section_courante/photos_non_versionnees/`.*

## État décrit

- **Date d'état** : 28/07/2026 (84303e7a, inchangée). Photos de la comparaison : 01/05/2024 à 28/07/2026, cohérentes.
- **Fabrication** : `hython recon/generateur/fabriquer_generateur.py meylan/auto_a41_section_courante/description.yaml
  --complet` (chaîne autoroute : rg::autoroute, 8 séparateurs, 0 musoir ; 2,5 M faces de sol).
- **Rendus seuls (sans photo)** : `recon/out/generateur/meylan_auto_a41_section_courante/rendus/` — `dessus.png`
  (84 m), `oblique_34.png` ; ceux de l'itération 0 sont gardés dans `rendus_it0/`.

## Itérations

| It. | Ce qui change dans la description | Pourquoi (preuve) |
|---|---|---|
| 0 | description du lot B, harmonisée par le lot N1 | — |
| 1 | **une seule glissière dans le TPC**, le long de la BDG du sens Chambéry (sud), au lieu de deux glissières le long des deux BDG | ortho, coupe s0330 : un seul rail sombre vers t ≈ −2 ; photos de la comparaison c235b69b, 7f197e9e, 131258a6 (un rail proche depuis la chaussée sud), a2064553 (rail du côté opposé depuis la chaussée nord), vue du pont 716ad033 (deux files seulement près de la pile du pont des Pépinières, non décrites) |

## Comparaison multivues, itération 0 (6 photos, 4 quadrants, 5 séquences)

`comparer_multivues.py` (sélection et poses faites au premier passage, rendus et planches refaits ici). Recouvrement
des contours à 3 px médian 0,19 → 0,36 ; écart moyen médian 16,8 → 10,2 px ; 4 poses affinées sur 6.

| Photo | Date | Vue | Ressemblance | Constat principal |
|---|---|---|---|---|
| c235b69b | 14/06/2025 | conducteur, vers l'est | bonne | profil juste ; pont des Pépinières absent ; TPC à une seule glissière (deux au modèle) |
| 7f197e9e | 14/06/2025 | vers le TPC | moyenne | largeur du TPC juste ; une glissière rouillée (deux au modèle) |
| 131258a6 | 28/02/2026 | avant-gauche | moyenne | même constat ; tirets longs (T3) justes |
| 716ad033 | 01/05/2024 | depuis le pont (vélo) | non jugeable par l'outil | l'outil rend au niveau du sol du modèle : la pose complète a placé la caméra dans le TPC. Comparaison refaite depuis le pont (ci-dessous) |
| 0c6a4b95 | 28/07/2026 | sur le tablier du pont | non jugeable | l'A41 est hors champ, sous le pont non fabriqué |
| fd0a3744 | 01/06/2025 | arrière | non jugeable | position GNSS sur l'autre chaussée (≈ 15 m d'erreur en travers) |

**Vue depuis le pont** (`recon/generateur/tmp/lotB_sites/outils/vue_pont.py`, œil à 8,2 m au-dessus du sol du modèle,
caméra GNSS + cap non affinée ; `comparaison/meylan_auto_a41_section_courante/ponts.json`) : vers l'est, les deux
chaussées, la BAU, la glissière extérieure et le TPC enherbé se superposent à la photo (lignes communes le long des
bords) ; la caméra est décalée de quelques mètres vers le nord (GNSS) ; le TPC du modèle a deux glissières, la photo une
seule hors des abords de la pile.

## Comparaison multivues, itération 1

*(en cours : fabrication et comparaison relancées après la correction du TPC ; voir la fin de ce fichier)*

## Écarts restants

- **Pont des Pépinières** (passage supérieur, pile dans le TPC, garde-corps) : non fabriqué, manque du générateur
  (BESOINS_FORMAT_AUTO B5 ; `extensions_auto.ouvrages`).
- Glissières neuves et brillantes au rendu, rouillées sur les photos ; herbe du TPC verte au rendu, sèche et haute sur
  les photos (matériaux, étape E10-E11).
- Panneau D41c, clôtures, ligne HT : hors de la route seule (E14-E16).
- Les photos de l'A41 sont rares et presque toutes prises depuis la chaussée sud ou depuis le pont : la chaussée nord est
  surtout jugée de loin.
