# Carrefour à feux Verdun × Chamrousse × Chaumetière (M08) — reconstruction, étape 3

*`recon/generateur/meylan/verdun_lycee_feux/RECONSTRUCTION.md` — 18/10/2026, lot « carrefours ». État décrit :
**28/07/2026** (photos IGN 921c90d1, 5922e7b4, ef8cd80b). Aucune photo ni planche n'est versionnée.*

## 1. Résultat en bref

- **Fabriqué et rendu** (rendu seul) : `recon/out/generateur/meylan_verdun_lycee_feux/rendus/dessus.png` (76,6 m de
  côté), `oblique_carrefour.png`, planche `planche_meylan_verdun_lycee_feux.png`.
- **Ressemblance** : **moyenne**. Les branches de Verdun (terre-plein engazonné, refuges revêtus au passage, voies
  affectées, bande plantée étroite loin du carrefour) ressemblent ; la grande zone de conflit aussi. Chamrousse a
  désormais son îlot planté (forme simplifiée). Manquent le petit îlot rond du cœur, les pistes qui traversent les
  angles plantés et la forme réelle (chaussées séparées qui se croisent). Itération 2 : 2 « bonne », 5 « moyenne »,
  2 « faible », 1 inexploitable sur 10 ; grille 36 conformes, 18 différents, 1 absent, 15 non visibles (itération 0 :
  2 / 3 / 4 / 1 ; 29 / 22 / 2 / 17).
- **Mesures de l'outil** : peu parlantes ici (photos 360° à vélo et au casque inclinées de 5 à 11°, la moitié des poses
  rejetées) : écart moyen médian après affinage 20,8 px (itération 0), 20,6 (itération 1), 23,2 (itération 2, autre
  tirage de photos).
- **Contournement déclaré** : Triangulate 2D du cœur (besoin G2) : `angle_min = 0` sur l'instance
  `rg::carrefours_sol` (enveloppe `recon/out/generateur/meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), code
  partagé inchangé.

## 2. Ce qui a été fait

| Étape | Commande / fichier | Résultat |
|---|---|---|
| Relecture | `DESCRIPTION.md`, `description.yaml` ; tuiles 921c90d1 t004, 5922e7b4 t004 ; plan annoté ; OSM du site | relecture M4 (îlots tronqués) confirmée |
| Fabrication | `hython …/fabriquer_lot_a.py recon/generateur/meylan/verdun_lycee_feux/description.yaml --complet` | itération 2 : 0 erreur, 0 non-conformité ; L3 4 coins, 3 nez ; L4 11 trajectoires, 29 conflits |
| Comparaison | `python …/comparer_lot_a.py --sortie recon/out/generateur/meylan_verdun_lycee_feux/comparaison --sites-conf recon/generateur/meylan/verdun_lycee_feux/comparaison_site.json meylan_verdun_lycee_feux --depuis 2024-05-01` | 10 photos (01/05/2024 à 31/08/2025), 4 quadrants, positions chaussée / piste / trottoir / accotement / hors modèle |
| Grille | `comparaison/meylan_verdun_lycee_feux/ecarts.json` (+ `ecarts_iter0.json` à `ecarts_iter2.json`) | voir § 4 |

**Pourquoi `--depuis 2024-05-01`.** Avec `--depuis 2025-06-01`, la sélection ne gardait que 6 photos à plat du
31/08/2025 d'un seul quadrant : les 68 photos IGN du 28/07/2026 (dont les trois du relevé) sont écartées par le seuil
d'emprise du modèle dans la vue (1,4 à 2,8 % contre 3,5 %, `selection.py`, diagnostic
`_travail/debug_selection.py`) ; le seuil n'a pas été baissé. La voirie n'a pas changé entre 2024 et 2026 (mêmes
bordures, îlots et marquages sur les photos de 2024, 2025 et 2026) ; la date d'état reste le 28/07/2026.

## 3. Itérations

| Itération | Changements de la description | Preuves | Effet |
|---|---|---|---|
| 0 | description du lot réseau | — | bande plantée de 8 m jusqu'au bout de Verdun nord-est (0c2f5716, a86b55d2 « faible ») ; sens de Chamrousse accolés, sans îlot (208a1f46, cb597029) |
| 1 | Verdun nord-est : bande plantée de 2 m au-delà de 50 m du centre, qui s'élargit à 8 m sur 15 m (`ouverture`) ; Chamrousse : îlot planté d'environ 5 m entre les sens (zone hachurée d'approche de 8 m puis terre-plein en gazon traversé par le passage) ; liaisons revêtues des passages avancées | photos 0c2f5716, a86b55d2, 208a1f46, cb597029, 921c90d1 ; OSM 7838796 / 7838799 ; coupe ne_30 | a86b55d2 et cb597029 passent de « faible » à « moyenne » |
| 2 | liaison revêtue de Verdun nord-est raccourcie (48,5 au lieu de 47,5) pour que l'angle nord-ouest ne soit pas rendu en trottoir | rendu de dessus de l'itération 1 | **sans effet visible** : le coin prend le revêtement de la bande extérieure à la frontière (limite du solveur, § 5) |

## 4. Ressemblance par photo (itération 2)

| Photo | Date | Vue | Pose | Ressemblance | Constat principal |
|---|---|---|---|---|---|
| ce9382f5 | 18/05/2025 | passage sud-ouest, vers la droite | redressement, 8,9 px | bonne | refuge revêtu traversé par le passage, comme la photo (barrières rouges : mobilier) |
| 4075f6e0 | 01/05/2024 | Verdun sud-ouest depuis la piste | complète, 12,7 px | bonne | bande enherbée étroite, terre-plein engazonné, refuge au loin |
| 674d46c6 | 01/05/2024 | Chamrousse au passage | complète, 12,9 px | moyenne | îlot de Chamrousse présent ; sur la photo le passage le longe au lieu de le traverser |
| cb597029 | 09/05/2024 | sortie vers Chamrousse | rejetée, 23,7 px | moyenne | îlot présent ; sortie courbe à potelets et flèche absentes |
| a86b55d2 | 18/05/2025 | Verdun nord-est à ≈ 55 m | rejetée, 26,7 px | moyenne | bande plantée étroite (itération 1) |
| 551efb9c | 31/08/2025 | approche nord-est | rejetée, 18,6 px | moyenne | petit îlot rond du cœur absent (L1) ; tirets de guidage non décrits (L4) |
| 8892229b | 18/05/2025 | Verdun nord-est depuis le passage | métadonnées, 22,7 px | moyenne | voies, passage, terre-plein (planté d'arbustes sur la photo) |
| 052a814a | 18/05/2025 | Verdun nord-est à ≈ 60 m | rejetée, 25,1 px | faible | profil plausible, rendu pris depuis la piste |
| 90781bde | 09/05/2024 | piste dans l'angle nord-est | rejetée, 30 px | faible | piste courbe à travers l'angle planté, absente (L3) |
| 9aa4825c | 01/05/2024 | piste dans l'angle nord-ouest | rejetée (inclinée de 10,6°) | inexploitable | — |

## 5. Écarts restants

- Petit îlot rond (≈ 2 m) au milieu de la zone de conflit : pas de mot pour un îlot libre (L1).
- Forme réelle : deux routes à chaussées séparées qui se croisent (quatre nœuds de feux) ; îlot triangulaire de
  Chamrousse rendu en bande de largeur constante (L2).
- Pistes cyclables qui traversent les angles plantés (Chronovélo) : absentes (L3) ; angle nord-ouest rendu en trottoir
  revêtu (le coin prend le revêtement de la liaison du passage) au lieu de la butte plantée.
- Tirets de guidage dans le carrefour (pratique locale non conforme, L4), potelets et barrières (mobilier), buttes
  plantées (végétation hors étape), fissures pontées (G8).

## 6. Fichiers

- Versionnés : `description.yaml` (itération 2), `DESCRIPTION.md`, `BESOINS.md`, ce rapport.
- Non versionnés : `recon/out/generateur/meylan_verdun_lycee_feux/` (modèle, L1-L4, rendus, `comparaison/`,
  `_travail/` : descriptions des itérations 0 et 1, jugements, journaux, diagnostic de sélection).
