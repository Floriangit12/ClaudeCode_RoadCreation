# N87 Rocade Sud à Meylan — du pont de l'Isère au nœud A41

*Lot B du relevé de Meylan, 17/10/2026. Site : N87 (voie rapide, `highway=trunk`) sur 997 m, du nord du pont de la
Rocade Sud (limite communale, L93 ≈ 918 427 ; 6 458 608) jusqu'à l'entrée du nœud A41 / N87 (≈ 918 327 ; 6 459 581).
Site M26 du dossier 13 (« TPC Rocade Sud »). État 2024. Voir `description.yaml`, `mesures.json`, `photos.json`.*

**Réseau (lot N1, 18/10/2026).** date d'état **23/06/2024** ; la N87 est **prolongée de 103,4 m** le long de la médiane OSM jusqu'à `N_N87_NOEUD`, au droit de la divergence de la chaussée nord (le trou de 103 m entre la N87 et le nœud A41 / N87 est comblé) ; 3 voies au nord sur les ≈ 65 derniers mètres (OSM 344514534) ; séparateur central en **DBA**. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description en texte libre

> Voie rapide à 2 × 2 voies, 90 km/h, sans éclairage, qui sort du pont sur l'Isère et monte en remblai vers
> l'échangeur de l'A41 par une grande courbe à gauche puis à droite. Les deux chaussées sont serrées contre une GBA en
> béton : le terre-plein ne fait que 2 m entre les lignes continues, tout en enrobé. Chaque sens a deux voies de 3,5 à
> 3,8 m. Vers le nord, à droite, une BAU de 2,5 m et une glissière, puis un talus enherbé et une clôture ; vers le
> sud, la BAU est étroite (1,7 m) et bordée par un muret en béton derrière lequel le talus est boisé. À mi-parcours,
> côté sud-ouest, une station-service avec sa voie de sortie et d'entrée (3 voies sur 200 m) et un portique. Enrobé
> ancien avec fissures longitudinales, marquages un peu usés, ligne à haute tension, falaise du Saint-Eynard au fond.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 terrassements | remblai depuis la culée nord du pont de l'Isère ; talus enherbés et boisés |
| E10 chaussée | 2 + 2 voies en enrobé, BAU 1,7 (sud) et 2,5 (nord), voie supplémentaire de l'aire de service, 3e voie au nord sur les ≈ 65 derniers mètres (prolongement jusqu'au nœud) |
| E12 marquages | rives continues 3u (u = 7,5 cm), T4 3u des BAU, T1 2u entre voies, T2 5u de la voie de l'aire |
| E13 retenue | DBA au TPC ; à droite du sens sud, glissière puis muret béton (s > 650) ; glissière à droite du sens nord |
| E14 signalisation | portique de l'aire, portique de présignalisation du nœud A41, PMV |
| E17 abords (plus tard) | station-service et abords boisés |

## 3. Profil (du côté ouest au côté est, sens du tronçon vers le nord)

| Élément | Largeur | Provenance |
|---|---|---|
| muret béton, BAU (sens sud) | 1,7 m | coupes s0130-s0230 : ligne +7,45, bord +9,2 ; photo 2e993fc0 |
| 2 voies sens sud | 3,8 + 3,5 m | lignes +7,45 / +3,65 / +0,15 |
| BDG, GBA, BDG | 0,5 + 0,8 + 0,6 m | GBA claire vers t = −0,8 ; photos 8357ddf1, 589161f4 |
| 2 voies sens nord | 3,5 + 3,6 m | lignes −1,8 / −5,3 / −8,9 |
| BAU (sens nord), glissière | 2,5 m | bord revêtu −11,3 ; photo 8357ddf1 |

## 4. Simplifications et incertitudes

- Le pont sur l'Isère (au sud) n'est pas décrit : pas de photo dans le catalogue, et il est en grande partie hors de
  Meylan. L'aire de service est réduite à sa voie supplémentaire (plan non relevé).
- Axe : médiane OSM rééchantillonnée et lissée (cassures ≤ 3,7°, avertissement du compilateur) ; le format ne fait
  pas encore l'ajustement en arcs et clothoïdes (BESOINS B14).
- GBA écrite comme une limite entre deux demi-bandes béton de 0,4 m (BESOINS B3).

## Reconstruction (lot SITES, étape 3, 18/10/2026)

Itération 1 : au bord extérieur du sens sud, une **glissière** jusqu'à s ≈ 650 (photos 53f09e82, 8aa90ca1 du 13/09/2026), puis le **muret béton**, écrit `GBA` (le mot `muret` n'est pas fabriqué) ; date d'état portée au 13/09/2026 (mêmes aménagements qu'en 2024). Détail : `RECONSTRUCTION.md`, `BESOINS.md`.
