# Avenue des 7 Laux (RD1090) — reconstruction (étape 3)

*`recon/generateur/meylan/avenue_7_laux_separateur/RECONSTRUCTION.md`, 18/10/2026. Lot de sites « giratoires et rues ».
Description : `description.yaml` (format réseau, résolue par `recon/generateur/reseau/`) ; besoins du générateur :
`BESOINS.md`. Sorties non versionnées : `recon/out/generateur/meylan_avenue_7_laux_separateur/`.*

## État

**Fabriqué, rendu et comparé (itération 2, finale).** Date d'état : 28/07/2026. Le tronçon de 73,5 m part du nœud
partagé `N_7LAUX_SO` (contrat de profil, continuité avec la branche des 7 Laux de `rp_lycee`) et va vers le nord-est.

| Fichier | Contenu |
|---|---|
| `rendus/dessus.png`, `rendus/oblique.png`, `rendus/planche_meylan_avenue_7_laux_separateur.png` | rendu seul (route seule, sans photo) de l'itération 2 |
| `iterations/iter0/`, `iterations/iter1/` | vues de dessus et obliques des itérations 0 et 1 |
| `comparaison/meylan_avenue_7_laux_separateur/` | sélection, poses, rendus des vues photo, grille `ecarts.json` (itération 2) et `ecarts_iter{0,1,2}.json` ; planches dans `photos_non_versionnees/` |
| `comparaison/jugements/iter{0,1,2}.json` | jugements de l'agent, versés dans la grille par `outils_lot_c/remplir_grille.py` |
| `journaux/` | fabrication (`fab_*.log`), comparaison (`comp_*.log`), copies de la description de chaque itération |

Commandes (enveloppes non versionnées du lot, sans modifier le code partagé : voir `../rp_lycee/BESOINS.md` G6, G7) :
`hython recon/out/generateur/meylan_rp_lycee/outils_lot_c/fabriquer_site.py description.yaml` (fabrication complète par
`fabriquer_generateur.py`, vues dessus + oblique seulement) ; `python …/outils_lot_c/comparer_site.py --sortie
recon/out/generateur/meylan_avenue_7_laux_separateur/comparaison --sites-conf comparaison_site.json
meylan_avenue_7_laux_separateur` ; les deux sous `outils_lot_c/garde_memoire.py` (plafond de mémoire).

## Itérations

| Itération | Description | Comparaison (12 photos, 4 quadrants) | Constat principal |
|---|---|---|---|
| 0 (premier passage du lot) | relevé du 17/10 + harmonisation N1 : séparateur « terre-plein 1,5 béton » sur toute la longueur, bande plantée entre piste et contre-allée refermée à 28 m | conformes 28, différents 14, absent 1 ; ressemblance bonne 2, moyenne 3, faible 2, inexploitable 5 | séparateur bas à caniveau en pavés gris (pas en béton) ; muret plein vers le rond-point ; piste et contre-allée côte à côte (ligne de gros blocs) |
| 1 (premier passage, fabriquée ; comparée à la reprise) | séparateur en pavés après 12 m ; bande plantée refermée avant le point du site | conformes 25, différents 17, absent 1 ; bonne 1, moyenne 5, faible 1, inexploitable 5 | planches vues en tuiles ; **erreur de lecture** : l'abscisse « s » affichée par les planches est le x du repère local, pas la distance le long du tronçon ; lue comme une distance, elle a fait placer 8e286398 à 17 m (prise en fait à 61 m) et 4388769c à 32 m (78 m). Les décisions de l'itération 2 en découlent en partie (voir « Écarts restants » 2 et 3). La seconde voie au-delà du point du site reste juste (tirets sur 0630f847 à 46 m et 4388769c à 78 m ; ligne de voie du levé GAM) |
| 2 (reprise) | chaussée nord-ouest à **deux voies de 2,6 m jusqu'à ≈ 50 m**, puis une voie (fermeture de 50 à 62 m) ; fermeture de la bande plantée avancée à 14 → 24 m | conformes 28, différents 16, absent 1 ; **bonne 1, moyenne 7**, faible 0, inexploitable 4 ; recouvrement 3 px médian 0,05 → 0,08, écart moyen médian 24,9 → 21,1 px (5 poses affinées sur 12) | toutes les planches vues en tuiles natives ; les deux voies sont justes à 9, 41 et 46 m |

## Ressemblance par photo (itération 2)

Abscisse `s` = distance le long du tronçon depuis le nœud `N_7LAUX_SO` (les planches affichent `s` = x du repère
local, ce qui n'est pas la même chose).

| Photo | Date | Prise (s, côté) | Vue | Ressemblance | Ce que la planche montre |
|---|---|---|---|---|---|
| 42320873 | 09/05/2024 | 55 m, bande béton | en travers | **bonne** | bande béton à barrière, chaussée à deux voies, séparateur bas, chaussée sud-est, talus |
| 7f4bd2a6 | 18/05/2025 | 9 m, chaussée nord-ouest | vers le nord-est | moyenne | deux voies justes ; séparateur réel = muret béton plein |
| 7b560dfa | 18/05/2025 | 33 m, chaussée | vers le sud-ouest | moyenne | about incliné du muret vers 25 m, puis caniveau en pavés bas |
| 36bf8ffd | 01/05/2024 | 41 m, bande béton | vers le sud | moyenne | deux voies, about du muret ; barrière bordeaux absente |
| 0630f847 | 28/07/2026 | 46 m, chaussée nord-ouest | vers le rond-point | moyenne | deux voies (tirets) comme le modèle ; rendu pris sur l'autre chaussée (GNSS) |
| 4388769c | 28/07/2026 | 78 m (au-delà du bout) | vers le rond-point | moyenne | deux voies encore à 75 m ; ligne de gros blocs le long de la contre-allée |
| 8e286398 | 01/05/2024 | 61 m, piste | vers le rond-point | moyenne | barrière, piste à figurine, contre-allée accolée (ligne de blocs) |
| 58cc1950 | 28/07/2026 | 27 m | vers le nord-ouest | moyenne | bande béton à la bonne place ; barrière bordeaux absente |
| 18d61cc3 | 01/05/2024 | 15 m, derrière les arbres | — | inexploitable | montre seulement le muret |
| 73088e91, e6742a81, 6f988e15 | — | haie, feuillage, hors du modèle | — | inexploitable | — |

## Écarts restants

1. **Muret séparateur plein** (≈ 0,8-1 m, about incliné) du nœud jusqu'à **≈ 25 m** (photos 7b560dfa, 36bf8ffd,
   7f4bd2a6, 0630f847) : non fabriqué, pas de mot hors autoroute (BESOINS S1). La description le fait finir à 12 m
   (« terre-plein 1,5 béton » puis « pavés ») : d'après les photos de l'itération 2, le changement devrait être à ≈ 25 m
   (prochaine correction, non refabriquée : itérations épuisées).
2. **Seconde voie vers le rond-point** : elle continue au-delà de 62 m (tiret à ≈ 75 m sur 4388769c) ; le modèle la
   referme de 50 à 62 m.
3. **Fermeture de la bande plantée** avancée à 14 → 24 m à l'itération 2 sur une lecture fausse de l'abscisse de la
   photo 8e286398 (prise en fait à 61 m) : ni infirmée ni confirmée par les photos (aucune ne voit 15-25 m de ce côté).
4. **Ligne de gros blocs** entre piste et contre-allée, **barrière bordeaux**, **enrobé fissuré à pontages** : absents
   (BESOINS S2, S3, S4).
5. Vues de contrôle : la vue de dessus du pilote ne couvre que 39 m sur les 73 m du tronçon (choix de la scène simple).
