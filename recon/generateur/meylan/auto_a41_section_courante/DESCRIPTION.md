# A41 à Meylan — section courante au passage supérieur des Pépinières

*Lot B du relevé de Meylan (autoroute et grands axes), 17/10/2026. Site : A41 entre la sortie n° 27 (Meylan
Mi-Plaine, à l'ouest) et la bifurcation A41 / N87 (à l'est), sur 550 m centrés sur le pont du chemin des Pépinières
(L93 ≈ 917 400 → 917 940 ; 6 459 717 → 6 459 841). État décrit : 2024-2025. Fichiers voisins : `description.yaml`
(traduction), `mesures.json` (coupes ortho, valeurs et incertitudes), `photos.json` (photos regardées, constats).*

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** (photo 84303e7a la plus récente, cohérente) ; le tronçon va de `N_A41_PEPINIERES_O` à `N_A41_N87_O`, nœuds partagés avec l'extrémité ouest et le nœud A41 / N87. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description en texte libre

> Autoroute à 2 × 2 voies en rase campagne, 110 km/h, sans éclairage. Chaque chaussée a deux voies de 3,60 m et une
> bande d'arrêt d'urgence de 3,40 m à droite, bordée d'une glissière simple. Entre les deux sens, un terre-plein
> central d'environ 7 m : un mètre d'enrobé de chaque côté (bande dérasée de gauche) derrière une ligne continue,
> puis une bande d'herbe haute d'environ 5 m, avec une seule glissière, côté sud, à un demi-mètre du bord de l'enrobé
> (deux files autour de la pile du pont). Au nord, un talus enherbé monte d'environ 3 m vers une clôture et un rideau de grands
> feuillus ; au sud, après une berme enherbée et une clôture, un champ (labouré au printemps, maïs l'été) et des
> peupliers. Une ligne à haute tension traverse. Au milieu, un pont-route étroit (le chemin des Pépinières) passe
> au-dessus presque à angle droit : tablier en béton de 8 m, une pile dans le terre-plein, culées en talus bétonnés,
> trottoirs en béton avec garde-corps à barreaux vert-jaune. Juste après le pont dans le sens vers Chambéry, un grand
> panneau bleu annonce la bifurcation « A41 Chambéry / N87 Sisteron – Saint-Martin-d'Hères, 500 m ». Les lignes
> entre voies passent de tirets longs (T1) à des tirets courts serrés (T3) environ 130 m après le pont vers l'est,
> et inversement vers l'ouest à l'approche de la sortie 27. Enrobé gris homogène, marquages nets.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 terrassements, ouvrages | terrain naturel de la plaine de l'Isère, talus montant au nord, assise des deux chaussées et du TPC ; pile dans le TPC, culées perrées, tablier du chemin des Pépinières, avant la couche de roulement |
| E10 chaussée | enrobé continu BDG 1,0 + 2 voies 3,6 + BAU 3,4 par sens, dévers en toit de 2,5 % |
| E11 terre-pleins, accotements | terre végétale et herbe haute du TPC (4,9 m), bermes enherbées de 1,5 m |
| E12 marquages | rives continues 3u du TPC (u = 7,5 cm), T4 3u des BAU, T1 2u puis T3 2u entre voies |
| E13 retenue | glissières simples aux bords des BAU, une glissière dans le TPC côté sud (deux autour de la pile) |
| E14 signalisation | D41c sur deux mâts, accotement droit, sens est |
| E16 équipements | clôtures autoroutières, ligne HT ; pas de candélabre |
| E17 abords (plus tard) | talus enherbé et arbres au nord, champ et peupliers au sud |

## 3. Profil en travers (de gauche à droite dans le sens est, vers Chambéry)

| Élément | Largeur | Provenance |
|---|---|---|
| berme, herbe haute | 1,5 m | photo a2064553 (estimée ± 0,5) |
| glissière simple | — | photos a2064553, 28b78e21 |
| BAU (sens ouest) | 3,4 m | ortho : ligne t = +10,40 ± 0,16, bord revêtu +14,0 (mesuré 3,6) |
| ligne T4 3u | — | ortho (traits de 39 m), RF-MQ-SC-06 |
| 2 voies sens ouest | 3,6 + 3,6 m | ortho : lignes +10,40 / +6,85 / +3,25 (3,55 et 3,60) |
| ligne continue 3u | — | ortho, RF-MQ-SC-06 (TPC) |
| BDG | 1,0 m | ortho 0,85 (ouest) et 1,25 (est) |
| glissière simple | à ≈ 0,5 m dans l'herbe | photo a2064553 l−51 |
| bande médiane, herbe haute | 4,9 m | ortho : saturation entre t = +2,4 et −2,4 |
| glissière simple | à ≈ 0,5 m dans l'herbe | photo 5d4f7b5b l−51 |
| BDG | 1,0 m | ortho |
| ligne continue 3u | — | ortho |
| 2 voies sens est | 3,6 + 3,6 m | ortho : lignes −3,65 / −7,20 / −10,85 (3,55 et 3,65) |
| ligne T4 3u | — | ortho |
| BAU (sens est) | 3,4 m | ortho : −10,85 → bord revêtu −14,05 (mesuré 3,2) |
| glissière simple, berme 1,5 m | — | photos 28b78e21, 716ad033 |

## 4. Éléments ponctuels

- **Passage supérieur du chemin des Pépinières** à s = 69,7 m (tablier de 65,7 à 73,7, coupe ortho s0080),
  biais 88° ; chaussée en enrobé fissuré ≈ 5,4 m, bordures hautes, trottoirs béton ≈ 1,3 m avec ligne jaune
  discontinue sur la bordure, garde-corps barreaudé ≈ 1,0 m (cadre noir, barreaux vert-jaune), glissière double
  lisse en about ; pile dans le TPC, culées perrées (photos 716ad033, 84303e7a, 28b78e21).
- **D41c** « A41 Chambéry | N87 Sisteron – St-Martin-d'H. | 500 m », sens est, accotement droit, s ≈ 100 ± 20 m.
- **Ligne HT** traversant vers s ≈ 260 (pylône treillis au sud).

## 5. Simplifications et incertitudes

- Profil symétrisé (BAU 3,4 au lieu de 3,6 / 3,2 ; BDG 1,0 au lieu de 0,85 / 1,25) ; incertitude ± 0,15 m sur une
  ligne, ± 0,3 m sur un bord revêtu.
- Hauteur, type et ancrage des glissières non mesurés (glissière simple de 0,75 m supposée) ; tirant d'air du pont
  non mesuré (≥ 4,85 m exigé).
- Position du passage T1 → T3 connue à ± 25 m ; dévers et profil en long non mesurés (plaine quasi plate).
- Le format actuel ne porte ni l'ouvrage, ni les glissières dans le TPC avec leur décalage, ni le talus, ni les
  clôtures : ils sont dans `extensions_auto` (voir `../BESOINS_FORMAT_AUTO.md`, B1 à B12).

## Reconstruction (lot SITES, étape 3, 18/10/2026)

Itération 1 : le TPC n'a **qu'une glissière**, le long de la bande dérasée du sens Chambéry (sud), et non deux (ortho, coupe s0330 ; photos c235b69b, 7f197e9e, 131258a6, a2064553, 5d4f7b5b). Deux files seulement autour de la pile du pont des Pépinières (vue du pont 716ad033), non décrites. Détail : `RECONSTRUCTION.md`.
