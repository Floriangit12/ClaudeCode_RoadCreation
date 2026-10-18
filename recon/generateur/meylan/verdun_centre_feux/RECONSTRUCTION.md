# Avenue de Verdun × chemin des Buclos (M17) — reconstruction, étape 3

*`recon/generateur/meylan/verdun_centre_feux/RECONSTRUCTION.md` — 18/10/2026, lot « carrefours ». État décrit :
**28/07/2026** (photos IGN de22683a, f252d62f, fce0902f). Aucune photo ni planche n'est versionnée.*

## 1. Résultat en bref

- **Fabriqué et rendu** (rendu seul) : `recon/out/generateur/meylan_verdun_centre_feux/rendus/dessus.png` (75,6 m de
  côté), `oblique_carrefour.png`, planche `planche_meylan_verdun_centre_feux.png`.
- **Ressemblance** : **moyenne**. Le passage à feux, son refuge bordé, la zone hachurée centrale et les deux débouchés
  en baïonnette sont à leur place ; depuis l'itération 1, les deux voies vers le nord-est (tourne-à-gauche) existent.
  Mais 4 des 6 photos retenues sont des photos à plat du 31/08/2025 dont la position GNSS est décalée : leurs planches
  sont faibles ou inexploitables. Itération 1 : 1 « bonne », 1 « moyenne », 3 « faible », 1 inexploitable ; grille
  14 conformes, 13 différents, 15 non visibles (itération 0 : 0 / 2 / 2 / 2 ; 12 / 12 / 18).
- **Écarts restants** : surtout des manques du générateur (baïonnette coupée en deux routes, pistes et herbe
  interrompues du côté continu des T, bande verte), voir `BESOINS.md`.
- **Contournement déclaré** : Triangulate 2D du cœur (besoin G2), `angle_min = 0` sur l'instance `rg::carrefours_sol`
  (enveloppe `recon/out/generateur/meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), code partagé inchangé.

## 2. Ce qui a été fait

| Étape | Commande / fichier | Résultat |
|---|---|---|
| Relecture | `DESCRIPTION.md`, `description.yaml` ; tuiles de22683a t003, t004 ; plan annoté | description cohérente ; relecture M6 déjà intégrée (Buclos nord à sens unique puis double sens) |
| Fabrication | `hython …/fabriquer_lot_a.py recon/generateur/meylan/verdun_centre_feux/description.yaml --complet` | 0 erreur, 0 non-conformité ; L3 6 coins ; L4 9 trajectoires, 9 conflits (itération 1) |
| Comparaison | `python …/comparer_lot_a.py --sortie recon/out/generateur/meylan_verdun_centre_feux/comparaison --sites-conf recon/generateur/meylan/verdun_centre_feux/comparaison_site.json meylan_verdun_centre_feux --depuis 2025-06-01` | 6 photos (28/07/2026 et 31/08/2025), quadrants +x, −x, gauche (aucune vue « droite » ne passe les filtres : 11 photos seulement retenues sur 118) |
| Grille | `comparaison/meylan_verdun_centre_feux/ecarts.json` (+ `ecarts_iter0.json`, `ecarts_iter1.json`) | voir § 4 |

## 3. Itérations

| Itération | Changement de la description | Preuve | Effet |
|---|---|---|---|
| 0 | description du lot réseau | — | fce0902f « moyenne » : une seule voie vers le nord-est, zone hachurée de 3,7 m là où la photo montre deux voies |
| 1 | entre le refuge et Buclos nord (`verdun_milieu_s`, `verdun_milieu_n`) : voie de tourne-à-gauche de 3,0 m vers le nord-est prise sur la zone hachurée (3,7 → 0,95 m) et la voie directe (3,5 → 3,25, RF-OSM-LAR-012) ; au-delà de Buclos nord (`verdun_ne`), la voie continue sur ≈ 15 m puis s'efface (`ouverture` vers le profil du nœud partagé, contrat 1 + 1 inchangé) ; `fleches: non` sur la branche courte de Buclos nord | de22683a t004 (C24 et deux voies dès le refuge), fce0902f (deux voies à ≈ 35 m), OSM 1412130603 `left\|through` | fce0902f passe à « bonne » |

Pas d'itération 2 : les écarts restants relèvent du générateur (C1, C2) ou de nœuds partagés à déplacer (C3, propriété
du lot réseau).

## 4. Ressemblance par photo (itération 1)

| Photo | Date | Vue | Pose | Ressemblance | Constat principal |
|---|---|---|---|---|---|
| f252d62f | 28/07/2026 | depuis Buclos sud vers le passage | orientation, 10,0 px | moyenne | zone hachurée et passage ressemblants ; bande verte de traversée cyclable absente ; refuge hors cadre du rendu |
| fce0902f | 28/07/2026 | vers le nord-est, au-delà du passage | orientation, 12,9 px | bonne | deux voies vers le nord-est (itération 1), zone hachurée étroite, herbe à droite |
| 150818b1 | 31/08/2025 | vers le sud-ouest | rejetée, 23,8 px | faible | position GNSS décalée, rendu sur l'herbe |
| 5a55da9f | 31/08/2025 | vers le sud-ouest | rejetée, 26,3 px | inexploitable | rendu depuis la piste ; « 50 » au sol absent |
| b6d669f3 | 31/08/2025 | Verdun sud-ouest | complète, 18,1 px | faible | voie de tourne-à-droite vers une rue latérale absente (C3) ; rendu depuis l'accotement |
| cf5da50c | 31/08/2025 | Verdun sud-ouest | rejetée, 28,4 px | faible | même constat |

Mesures de l'outil (médianes) : recouvrement à 3 px 0,05 → 0,11, écart moyen 25,1 → 20,9 px.

## 5. Écarts restants

- Baïonnette : le tronçon de 29 m entre les deux T est coupé en deux routes (le solveur ne gère qu'un carrefour par
  route, à son extrémité « fin », C1) ; décrochements des bandes extérieures à la coupure.
- Du côté continu de chaque T, la Chronovélo et la bande enherbée sont remplacées par un « trottoir de carrefour » sur
  ≈ 15 m (C2) : visibles sur les rendus de dessus et oblique, contraires aux photos.
- Bande verte de traversée cyclable du passage à feux (A2 / G4) ; fissures pontées (G8).
- Débouchés voisins non décrits (voie de tourne-à-droite au sud-ouest, allée de la Faculté au nord-est) : les nœuds
  partagés N_VERDUN_M17_SO / N_VERDUN_M17_NE et leurs contrats 1 + 1 sont au lot réseau (C3).
- Couverture photographique : aucune vue « vers la droite » retenue, quatre photos du 31/08/2025 mal positionnées.

## 6. Fichiers

- Versionnés : `description.yaml` (itération 1), `DESCRIPTION.md`, `BESOINS.md`, ce rapport.
- Non versionnés : `recon/out/generateur/meylan_verdun_centre_feux/` (modèle, L1-L4, rendus, `comparaison/`,
  `_travail/` avec la description de l'itération 0, les jugements et les journaux).
