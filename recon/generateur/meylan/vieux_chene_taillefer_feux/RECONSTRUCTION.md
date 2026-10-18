# Carrefour Vieux Chêne × Taillefer × Hélice (M07) — reconstruction, étape 3

*`recon/generateur/meylan/vieux_chene_taillefer_feux/RECONSTRUCTION.md` — 18/10/2026, lot « carrefours ». État décrit :
**28/07/2026** (campagne IGN). Aucune photo ni planche n'est versionnée.*

## 1. Résultat en bref

- **Fabriqué et rendu** (rendu seul) : `recon/out/generateur/meylan_vieux_chene_taillefer_feux/rendus/dessus.png`
  (109 m de côté), `oblique_carrefour.png`, planche `planche_meylan_vieux_chene_taillefer_feux.png` (itération 2).
- **Ressemblance** : **moyenne à bonne**. Les quatre branches, la branche est courbe et son séparateur en gravillons,
  les deux tourne-à-droite directs derrière leurs îlots, le passage ouest à ≈ 47 m et les voies de l'Hélice sont à leur
  place. Itération 2 : 2 « bonne », 5 « moyenne » sur 7 ; grille 28 conformes, 13 différents, 8 non visibles
  (itération 0 : 4 moyenne, 3 faible, 1 inexploitable ; 24 / 25 différents ou absents / 7).
- **À photos égales** (5 des 8 photos de l'itération 0 relancées sur le modèle de l'itération 2) : écart moyen médian
  après affinage 15,3 → 10,6 px, recouvrement des contours à 3 px 0,19 → 0,30.
- **Contournement déclaré** : la fabrication saturait la mémoire puis plantait (Triangulate 2D du cœur, besoin G2) ;
  rendus obtenus avec `angle_min = 0` sur l'instance `rg::carrefours_sol` (enveloppe non versionnée
  `recon/out/generateur/meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), code partagé inchangé.

## 2. Ce qui a été fait

| Étape | Commande / fichier | Résultat |
|---|---|---|
| Relecture | `DESCRIPTION.md`, `description.yaml` ; tuiles natives ad0b728e (l+0, l+0154.3), fccb6997 (l+102.9), e8178560 (t004) ; plan annoté et ortho IGN 2024 (zoom 5 m) | séparateur « séparateur 0,3 » non fabricable (G1) : réécrit en terre-plein |
| Fabrication | `hython …/fabriquer_lot_a.py recon/generateur/meylan/vieux_chene_taillefer_feux/description.yaml --complet` | itération 2 : 0 erreur, 0 non-conformité ; L3 4 coins, 3 nez ; L4 14 trajectoires, 42 conflits |
| Comparaison | `python …/comparer_lot_a.py --sortie recon/out/generateur/meylan_vieux_chene_taillefer_feux/comparaison --sites-conf recon/generateur/meylan/vieux_chene_taillefer_feux/comparaison_site.json meylan_vieux_chene_taillefer_feux --depuis 2025-06-01` (+ `--photos …` pour la relance à photos égales, dans `comparaison_photos_iter0/`) | 7 à 8 photos (28/06/2026 et 28/07/2026), 4 quadrants, positions chaussée / accotement / hors modèle |
| Grille | `comparaison/meylan_vieux_chene_taillefer_feux/ecarts.json` (+ `ecarts_iter0.json`, `ecarts_iter1.json`, `ecarts_iter2.json`) | voir § 4 |

## 3. Itérations

| Itération | Changements de la description | Preuves | Effet |
|---|---|---|---|
| 0 | `séparateur 0,3` → `terre-plein 0,3 béton` (sinon rg::nivellement refuse : « dénivelé sans bordure », G1) | — | branche est droite : efc67150, 3eb5557e « faible », 4c3c6ec3 inexploitable (photos prises dans la courbe, hors du modèle) ; passage ouest au débouché alors qu'il est à ≈ 47 m ; îlot séparateur ouest absent |
| 1 | branche est tracée en courbe sur la médiane OSM (droite de 36 m depuis le centre, arc de 24 m de rayon, droite de 10 m) ; axe ouest recalé sur la médiane OSM ; passage ouest déplacé à ≈ 47 m du centre (évènement du tronçon, liaison revêtue de la bande enherbée) ; îlot séparateur bordé d'environ 1,4 m sur les 20 derniers mètres de la branche ouest, précédé de sa zone hachurée | OSM 857526256, 190600688, 235030395, 190600691, 857526258/59 ; levé GAM (bandes et damier, bordure fermée) ; photos efc67150, 3eb5557e, 4c3c6ec3, 4289a952, e5c7653d | branche est juste (efc67150, 3eb5557e « bonne ») ; une première version (droite de 23 m) a mis une bande de gazon à travers la zone de conflit (coin calculé sur l'arc, G3) : corrigée en allongeant la droite |
| 2 | séparateur du Vieux Chêne est : 0,3 m béton → **≈ 1,2 m garni de gravillons** | photos 3eb5557e, efc67150, 12844b83, c02e39f5 (deux bordures, gravillons, feu sur le nez) | séparateur ressemblant (3eb5557e, efc67150, c02e39f5) |

## 4. Ressemblance par photo (itération 2)

| Photo | Date | Vue | Pose | Ressemblance | Constat principal |
|---|---|---|---|---|---|
| efc67150 | 28/07/2026 | sortie est, vers le nord | redressement, 9,7 px | bonne | branche courbe, voies d'entrée de l'autre côté du séparateur en gravillons |
| 251e36bc | 28/07/2026 | branche ouest vers le carrefour | complète, 14,4 px | bonne | passage ouest à la bonne distance ; damier de traversée cyclable absent (A2) |
| 12844b83 | 28/07/2026 | entrée est, vers le carrefour | orientation, 9,9 px | moyenne | caméra rendue contre l'îlot du tourne-à-droite ; nez du séparateur |
| c02e39f5 | 28/07/2026 | depuis le cœur vers l'est | métadonnées, 20,5 px | moyenne | forme de la branche est et séparateur justes, nez rendu plus près |
| c4763a2a | 28/07/2026 | cœur vers le nord-ouest | orientation, 17,1 px | moyenne | nez d'îlot, passage ; traversée verte absente |
| 45da0502 | 28/06/2026 | Taillefer | métadonnées, 19,3 px | moyenne | voies et passage ; traversée verte absente ; fourgon au premier plan |
| d7449e61 | 28/06/2026 | Hélice à ≈ 50 m | complète, 4,1 px | moyenne | voies justes ; glissières entre les chaussées et en rive non décrites (G5), bordures en trop |

Relance à photos égales (itération 0 → 2, écart moyen après affinage) : efc67150 25,6 → 10,6 px ; 3eb5557e 15,1 → 9,8 px ;
d7449e61 8,1 → 6,9 px ; a8876103 16,4 → 15,6 px ; 45da0502 20,2 → 19,3 px. Les trois autres photos de l'itération 0
(e5c7653d, 4289a952, 4c3c6ec3) n'ont plus de vue retenue par les filtres de l'outil sur le nouveau modèle.

## 5. Écarts restants

- Traversées cyclables peintes (bande verte au nord, damier à l'ouest) : pas de mot dans le format (G4 / A2).
- Hélice : glissières et rives peintes au lieu d'un terre-plein bordé à 50 m du carrefour (G5).
- Séparateur de la branche est : largeur constante ≈ 1,2 m, alors que le réel s'élargit vers le nez (feu) ; îlots des
  tourne-à-droite : gazon plat (plantations et haies hors étape).
- Enrobé très rapiécé : rendu uniforme (G8) ; candélabres décorés, D21 et panneau d'autoroute : hors « route seule ».
- Branche est : écart à la médiane OSM jusqu'à ≈ 2,8 m dans la courbe (la droite a été allongée pour le solveur, G3).

## 6. Fichiers

- Versionnés : `description.yaml` (itération 2), `DESCRIPTION.md`, `BESOINS.md`, ce rapport.
- Non versionnés : `recon/out/generateur/meylan_vieux_chene_taillefer_feux/` (modèle, L1-L4, rendus, `comparaison/`,
  `comparaison_photos_iter0/`, `_travail/` : descriptions des itérations 0 et 1, jugements, journaux, diagnostic de la
  triangulation `diag_tri/`).
