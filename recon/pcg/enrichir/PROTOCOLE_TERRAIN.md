# Campagne photo terrain — carrefour Paquet Jardin (état après travaux)

**Pourquoi.** Aucune image publique ne montre le cœur du carrefour depuis les travaux (23/06 au 05/12/2025, trottoirs du
Vercors jusqu'au 30/01/2026). Vérifié le 10/10/2026 :
- Panoramax : les photos postérieures aux travaux sont toutes du 28/07/2026, la plus proche à 129 m du centre ;
- Mapillary : aucune image après le 19/05/2025 ;
- orthos ouvertes : la plus récente date du 09/08/2024 (IGN) ; le PCRS 2025 est sur abonnement.

Avec un critère strict (une observation manuelle, de confiance suffisante, valable en 2026), 86,8 % des entités
n'ont aucune preuve image, dont 84 % des bordures. **Dans la zone des travaux 2025, aucune bordure (0 sur 96) et
aucun marquage (0 sur 132) n'est observé** : flèches, lignes d'effet, abaissés, BEV et remplissages d'îlots y viennent
du levé GAM, du plan 2025 ou des règles, et 56 conflits restent à vérifier. Une demi-heure de prises de vue suffit à les trancher. Les photos alimentent directement la
chaîne existante : calage des poses (`recon/pcg/enrichir/poses.py`), projection de la description, triangulation, fusion.

## Matériel et conditions
- De préférence une caméra 360° (GoPro Max sur perche à 2 m, modèle déjà géré par `poses.py`), sinon un téléphone tenu
  à l'horizontale, zoom 1x, GPS activé.
- Un dimanche matin, ciel couvert, peu de voitures garées.
- Uniquement depuis les trottoirs et les refuges, en traversant au vert piéton.
- Une photo tous les 2 à 3 m. **À chaque abaissé et à chaque refuge, une photo rasante à moins de 5 m, avec un mètre
  pliant vertical contre la face de la bordure** (mesure de la vue).

## Ordre de passage (par gain d'information, calculé sur les entités sans preuve et les conflits)
S3, S5, S7, S4, S1, S6, S2, puis S8, S14, S15, S13, puis S9, S11, S10b, S12. Si le temps manque, les 7 premières
stations couvrent l'essentiel du cœur refait en 2025.

## Stations
Coordonnées locales (x, y) en mètres depuis l'origine du paquet, puis Lambert-93. Azimuts en degrés depuis le nord.

| Station | Où | L93 | Prises |
|---|---|---|---|
| S1 | angle N, Revirée × Verdun NE, près des potelets (-2 ; 19) | 917277,4 / 6460309,0 | vers 150° (traversée NE, TPC, feu du TPC), 225° (traversée Revirée et traversée cyclable), 330° (quai de la ligne 42), 70° (candélabre : couleur du mât) |
| S2 | angle E, Verdun NE × Vercors (17 ; -2) | 917296,4 / 6460288,0 | vers 315° (traversée NE et refuge), 200° (traversée Vercors, îlot, feu de l'îlot), 180° (candélabre E du Vercors) ; pied du peuplier arbre_224 : vers 80° depuis S2 et vers 180° depuis (37 ; 25) — un ou deux arbres ? |
| S3 | angle S, Vercors × Verdun SO (-2 ; -27) | 917277,4 / 6460263,0 | vers 80° (traversée Vercors et îlot), 250-270° (traversée SO, pavés jaunes Chronovélo, feu cycliste), 0-20° (flèches et lignes d'effet des voies d'entrée du Vercors), 180° (armoire de feux, arbre_184, clôture) |
| S4 | angle O, Verdun SO × Revirée (-24 ; -15) | 917255,4 / 6460275,0 | vers 120-140° (traversée O, refuge planté, mât caméra), 0° (arbres 229/230), 220° (poteau réseau et candélabre : un seul poteau ou deux ?) |
| S5 | refuge (TPC) de Verdun SO (-18 ; -20) | 917261,4 / 6460270,0 | 360°, pendant le vert piéton |
| S6 | refuge (TPC) de Verdun NE (10 ; 8) | 917289,4 / 6460298,0 | 360°, pendant le vert piéton |
| S7 | îlot du Vercors (8,5 ; -15) | 917287,9 / 6460275,0 | 360°, pendant le vert piéton |
| S8 | quais La Revirée, Verdun SO (-45 ; -48) | 917234,4 / 6460242,0 | abris NO et SE, afficheur, hauteur de quai au mètre (18 cm attendus), banc, poteaux d'arrêt, candélabre |
| S13 | débouché des Mitaillères (25 ; -135), depuis l'îlot nord et le trottoir est | 917304,4 / 6460155,0 | 3 ou 4 prises : lignes de places, candélabre, panneaux B6a1, C13a, AB3a et STOP (7 conflits) |

Aux refuges (S5 à S7), couvrir : la ceinture de bordures et leur vue, les BEV, les têtes de feux (nombre, R12/R13c,
boutons d'appel), et **chaque flèche au sol vue depuis la ligne d'effet vers l'amont** (type, voie occupée, centrage).

## Parcours linéaires (une photo tous les 10 m, dans les deux sens)
- S14 : Verdun SO, de (-45 ; -48) à (-95 ; -92) : chaussée reprise en 2025, 19 marquages, 8 bordures, 3 panneaux, banc.
- S15 : rive est du Vercors, de (22 ; -10) à (30 ; -125) : trottoirs et chaussée refaits, 23 bordures, 28 arbres d'alignement.
- S9 : rive SE de Verdun NE, de (20 ; 10) à (60 ; 70).
- S11 : arc de bordures en (50-67 ; 98-105).
- S10b : sortie de la voie privée des Saules Blancs en (58 ; -30).
- S12 : la Revirée de (-3 ; 17) à (-20 ; 40).
- Vues obliques des surfaces en (11 ; 106), (-20 ; -95) et (-99 ; -15).

## Ensuite
Déposer les photos (avec leurs métadonnées EXIF/GPS) dans `data/raw/terrain_2026/<date>/` : elles restent hors git.
La chaîne les cale (points d'appui : coins de zébras et bordures du levé GAM 2026), puis les intègre à la fusion avec
la source `terrain2026`, prioritaire sur toutes les autres pour l'état actuel.
