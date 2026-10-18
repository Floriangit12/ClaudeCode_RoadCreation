# Chemin du Vieux Chêne (Inovallée) — reconstruction (étape 3)

*`recon/generateur/meylan/vieux_chene_inovallee_piste/RECONSTRUCTION.md`, 18/10/2026. Lot de sites « giratoires et
rues ». Description : `description.yaml` (format réseau) ; besoins du générateur : `BESOINS.md`. Sorties non
versionnées : `recon/out/generateur/meylan_vieux_chene_inovallee_piste/`.*

## État

**Passe 2 (18/10/2026, soir)** : l'itération 2 est finale. Elle est comparée avec l'outil v2 (39 photos, 87 vues).
Détails dans la section « Passe 2 » ci-dessous et dans `COMPREHENSION.md`. L'état du premier passage suit.

**Premier passage : fabriqué, rendu et comparé (itération 1).** Date d'état : 28/07/2026 (enrobé et marquages refaits depuis
l'ortho 2024). Carrefour en T à feux : branches ouest et est en courbe (polylignes OSM lissées), desserte nord ; îlots
peints ocre au milieu des deux branches ; piste séparée au nord ; passages sur la branche ouest et la desserte.

| Fichier | Contenu |
|---|---|
| `rendus/dessus.png`, `rendus/oblique_carrefour.png`, `rendus/planche_meylan_vieux_chene_inovallee_piste.png` | rendu seul (route seule) de l'itération 1 |
| `iterations/iter0/`, `iter1/` | vues de dessus et obliques de chaque itération |
| `comparaison/meylan_vieux_chene_inovallee_piste/` | sélection, poses, rendus des vues photo, grille `ecarts.json` et `ecarts_iter{0,1}.json` ; planches dans `photos_non_versionnees/` |
| `comparaison/jugements/iter{0,1}.json` | jugements de l'agent versés dans la grille |
| `journaux/` | `fab_1.log` (plantage du premier passage), `essai_*.log` (recherche de la cause), `fab_iter0b.log`, `fab_iter1.log`, `comp_iter{0,1}.log`, copies de la description |
| `essais/` | sorties des essais de diagnostic (dossier créé par ce lot) |

## Fabrication : le plantage du premier passage

Le premier passage s'était arrêté sur ce site : `rg::sol` (Triangulate 2D raffiné) consommait la mémoire sans fin
(hython à 67 Go, journal système 2004 de 15:37, puis « Segmentation fault »), en gênant les autres lots. À la reprise,
huit essais sous garde mémoire (`outils_lot_c/garde_memoire.py`, arbre de processus tué au-delà d'un plafond) ont isolé
la cause : la **zone hachurée centrale** posée sur des **polylignes à cassures non raccordées** (21,5° et 17,3°).
Passages, enrobé ocre, évènements, fermeture des îlots avant le carrefour : sans effet. Sans zone centrale : fabrication
normale. Avec les tracés lissés (cassures ≤ 9°) : fabrication normale **avec** les îlots (2,4 Go, 388 s). Besoin V1.

## Itérations

| Itération | Description | Comparaison (10 photos, 4 quadrants) | Constats |
|---|---|---|---|
| 0 (reprise) | relevé du 17/10 recalé sur OSM, branches vers le carrefour ; **îlots peints retirés** (seul moyen de fabriquer avec les polylignes du relevé) | conformes 30, différents 17, absents 7 ; ressemblance bonne 1, moyenne 6, faible 3 ; recouvrement 3 px médian 0,11 → 0,29, écart moyen 20,9 → 15,2 px (7 poses affinées) | carrefour, passages, coins, bande enherbée et piste justes ; îlot peint absent sur 6 planches (7d44455e, 7d0a7eda, fe78d282, 96e5dcb1, 71607e1f, 10834a8d) |
| 1 | tracés lissés, îlots peints « zone hachurée enrobé ocre » rétablis (2,3 m à l'ouest, 1,0 m à l'est) | **conformes 40**, différents 17, absent 1 ; **bonne 2, moyenne 5**, faible 3 ; recouvrement 0,06 → 0,16, écart 22,5 → 17,9 px (4 poses affinées) | îlot peint présent et à sa place (cbd7ccdb, 7d0a7eda, 96e5dcb1, 71607e1f, 6e324d31, 10834a8d) ; il est hachuré blanc là où la photo le montre plein et arrondi (V2) |

## Ressemblance par photo (itération 1)

| Photo | Date | Prise | Ressemblance | Ce que la planche montre |
|---|---|---|---|---|
| cbd7ccdb | 28/07/2026 | branche est vers le carrefour | **bonne** | îlot peint ocre à gauche, rive, bande enherbée à bordure arrondie, carrefour au fond |
| 7d0a7eda | 01/05/2024 | angle nord-ouest | **bonne** | passage, coin et îlot peint à la bonne place ; refuge peint rond au milieu du passage absent (V3) |
| 10834a8d | 23/11/2024 | branche ouest, courbe | moyenne | courbe et îlot central justes ; en 2024 séparateur bas bordé (avant réfection) |
| 6e324d31 | 28/07/2026 | branche ouest, courbe | moyenne | courbe et îlot central ressemblants |
| 96e5dcb1 | 23/11/2024 | branche est | moyenne | naissance de l'îlot (double ligne) comme le modèle |
| 71607e1f | 01/05/2024 | bande enherbée nord | moyenne | bande enherbée, chaussée, îlot peint |
| 609aa874 | 01/05/2024 | piste nord | moyenne | piste, bande enherbée, chaussée à îlot |
| 17826b13 | 28/07/2026 | branche ouest | faible | point de vue différent (pose corrigée vers le carrefour) |
| 7d44455e | 28/07/2026 | centre du carrefour | faible | rendu orienté vers la desserte ; l'angle nord-ouest est un îlot bordé arrondi, pas un trottoir d'angle |
| c9e3e7e6 | 23/11/2024 | branche est, loin | faible | bout du modèle : lignes blanches qui se croisent |

## Écarts restants

1. **Îlots peints** : hachures blanches sur fond ocre au lieu d'un aplat ocre à contour blanc et bout arrondi (V2) ;
   refuge peint rond au droit du passage ouest absent (V3).
2. **Marquage le long des îlots** : sur la vue de dessus de l'itération 1, une ligne blanche quitte le bord de l'îlot
   peint aux sommets des polylignes et coupe la voie (aussi visible sur c9e3e7e6, bout est) : défaut de tracé des
   délimitations sur polyligne (à confirmer par le lot Extension).
3. **Angle nord-ouest** : îlot bordé arrondi entre la branche ouest et la desserte (7d44455e) rendu en trottoir d'angle.
4. Traversée cyclable à figurines et chevrons (V4), arrêts de bus à zigzags (V5), feux : non décrits.
5. Tracés lissés à la main (contournement de V1) : écart au tracé OSM ≤ 1 m.

## Passe 2 (18/10/2026) : compréhension par fusion des images, centre et îlots

### Dossier v2

Commande : `comparer_multivues.py meylan_vieux_chene_inovallee_piste --v2 --depuis 2025-01-01`.

- **Fenêtre d'état.** Elle commence après la réfection, qui a eu lieu entre le 23/11/2024 et le 28/07/2026.
- **Photos.** 39 au total (26 Panoramax, 13 Mapillary), soit 87 vues dont 33 du centre. Aucune zone aveugle.
  - 11 photos sont dans la fenêtre, toutes du 28/07/2026.
  - 28 sont hors fenêtre (2022 et 2024). Elles ont servi à comprendre les états successifs, pas à décrire.
- **Ce que j'ai lu moi-même**, en tuiles natives (`COMPREHENSION.md` § 1) :
  - les orthos datées et le zoom GAM du centre ;
  - les vues côte à côte rendu | ortho ;
  - 6 planches du centre (24 vues) et 13 vues natives du 28/07/2026 ;
  - après fabrication : `p2_centre_est` et 4 planches photo | rendu.

### Itérations

**Itération 2a** (fabrication tuée)
- Description :
  - îlot ouest refermé juste après le passage (`fermeture` à a = 78) ;
  - îlot est ouvert de s = 60 à 75, puis refermé de 88 à 90.
- Résultat : `rg::sol` s'emballe. Le garde mémoire tue la fabrication à 10,9 Go.

**Essais d'isolement** (`essais/passe2/`, garde à 5 Go)
- Fermeture ouest : emballement (7,4 Go en 68 s).
- Profil instantané ouest : emballement lent (5,1 Go en 184 s).
- Fermeture est seule : fabrication normale.
- Ouverture est seule : normale jusqu'à l'arrêt manuel.

**Itération 2b** (fabrication tuée)
- Description : ouverture est et fermeture est, sans évènement à l'ouest.
- Résultat : emballement **jusqu'à 18,5 Go**, au-delà du plafond de 10 Go, entre deux relevés du garde (pas de 10 s ; besoin V7 bis). Le garde accepte maintenant `--pas`.

**Itération 2c** (finale)
- Description : seule la fermeture est est gardée. La zone ocre est se termine à ≈ 10 m du centre.
- Résultat :
  - 0 erreur ; fabrication en 539 s, 6,5 Go.
  - Le nez de l'îlot est est à sa place (`p2_centre_est`, planche `7d44455e_-169`).
  - Vues jugées : 4 (3 moyennes, 1 faible). Fichiers : `comparaison/jugements/passe2_iter2.json`, grille `ecarts_iterp2_2.json`.

Rendus seuls (route seule) de l'itération 2c : `rendus/dessus.png` et `oblique_carrefour.png`, copiés dans
`iterations/passe2_iter2/`.

### Ressemblance du centre : moyenne

- Ce qui est juste : les passages, l'absence de guidage, la fin de l'îlot est.
- Ce qui est faux :
  - zone ocre ouest jusqu'au centre (V7) ;
  - hachures au lieu d'aplats (V2) ;
  - refuge rond (V3) et traversée cyclable à figurines (V4) absents ;
  - angle nord-ouest rendu en trottoir.

### Écarts restants après la passe 2

1. Branche ouest : zone ocre menée au centre, ≈ 4 m de trop. Refuge peint rond absent (V7, V3).
2. Branche est : zone ocre continue au-delà de ≈ 25 m du centre, alors que le réel a deux lignes puis un axe en tirets (V7 bis, V8).
3. Îlots peints hachurés, nez en biseau (V2). Traversée cyclable à figurines et chevrons absente (V4). Arrêts de bus absents (V5).
4. Angle nord-ouest : îlot bordé enherbé rendu en trottoir d'angle.
5. Lignes blanches qui coupent la voie aux sommets des polylignes : vues sur la vue de dessus, à l'est (`p2_centre_est`).
