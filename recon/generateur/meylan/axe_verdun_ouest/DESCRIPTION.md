# Avenue de Verdun (D1090), côté La Tronche — boulevard à chaussées séparées

*Lot B du relevé de Meylan, 17/10/2026. Site : avenue de Verdun entre le bout de l'A41 (carrefour M14,
L93 ≈ 916 598 ; 6 459 553) et le carrefour des Aiguinards (M13, k ≈ 649), en deux tronçons de section courante
séparés par le carrefour de la Plaine Fleurie (M15, k ≈ 250). Les carrefours relèvent du lot A. État 2024-2025.*

**Réseau (lot N1, 18/10/2026).** date d'état **18/05/2025** ; pas de nœud partagé (le site est à 380 m de Paquet Jardin). Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description en texte libre

> Grande avenue d'entrée de ville à chaussées séparées, 50 km/h, éclairée. En sortant de l'autoroute, trois voies de
> chaque côté, dont la voie de droite réservée aux bus (tirets larges) ; entre les deux sens, un terre-plein étroit
> (≈ 3 m) d'herbe sèche entre deux bordures basses. Côté sud-est, derrière une glissière, un alignement de très grands
> arbres ; côté nord-ouest, une bande de terre, des candélabres hauts à double crosse, puis une voie parallèle et du
> stationnement. Après le premier carrefour à feux, deux voies par sens, plus étroites (2,6 à 3,2 m), de part et
> d'autre d'un terre-plein bordé de 3 m planté d'une haie taillée continue d'environ 1,20 m, avec les candélabres au
> milieu de la haie. Rives peintes en continu, puis de larges accotements d'herbe haute avec arbustes et grands arbres ;
> à 15-20 m de l'axe, de chaque côté, une piste cyclable de 3 m et un trottoir en enrobé. Une traversée cyclable est
> peinte en damier jaune (itinéraire Chronovélo). Avant le carrefour des Aiguinards, un arrêt de bus avec quai béton,
> abri et zigzag jaune. Enrobé ancien, fissuré et rapiécé.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | deux chaussées et le terre-plein central, larges accotements |
| E08 bordures | bordures basses du TPC (tronçon 1), bordures T2 autour de la haie (tronçon 2), bordure droite (1) |
| E10 chaussée | chaussées en enrobé, couloirs bus |
| E11 trottoirs, pistes, terre-pleins | TPC en herbe (1), terre et paillage (2), accotements enherbés, pistes et trottoirs latéraux |
| E12 marquages | T3 5u des couloirs bus, lignes entre voies, rives continues, damier jaune Chronovélo (relevé sur photo, jamais par défaut), zigzag de l'arrêt de bus |
| E13 retenue | glissière côté sud-est (1) |
| E14 signalisation | signalisation des carrefours (lot A) ; panneaux de direction près de l'A41 |
| E15 éclairage | candélabres du TPC (2) |
| E17 végétation (plus tard) | haie taillée du TPC, arbres, arbustes |

## 3. Profils (`description.yaml`, `mesures.json`)

| Tronçon | Profil (nord-ouest → sud-est) | Provenance |
|---|---|---|
| 1, k 30-225 | bande enherbée · bordure · bus 3,5 · T3 5u · 2 voies 3,25 (← La Tronche) · bordure basse · herbe 2,8 · bordure basse · 2 voies 3,0 · T3 5u · bus 3,2 (→ Meylan) · glissière · berme 5 | coupe s0140 (3 voies sur 10,5 / 9,2 m) ; OSM bus:lanes ; photo bb66244a |
| 2, k 280-625 | herbe haute 8 · accotement 0,5 · rive · 2 voies 3,0 / 2,6 · bordure · TPC 1,3 + haie + 1,3 · bordure · 2 voies 3,1 / 3,2 · rive · accotement 0,5 · herbe haute 6 | coupe s0490 ; photos 9f1498db, f86cca91, e68edc7f |

## 4. Simplifications et incertitudes

- Dans le tronçon 1, 10,5 m mesurés pour trois voies ont été ramenés à 10,0 (règles RF-OSM-LAR-012/-013) : les fils
  d'eau ne se distinguent pas à 20 cm/px.
- Pistes, trottoirs, arrêt de bus, traversée en damier, haie et candélabres sont dans `extensions_auto` (BESOINS B4,
  B6-B8) : les pistes sont à 15-20 m de l'axe, au-delà d'accotements que le profil porte en bermes.
- Le tronçon k 650-950 (vers Paquet Jardin) n'est pas décrit : chaussées rapprochées, lignes masquées par les arbres.

## Reconstruction (lot SITES, étape 3, 18/10/2026)

Itération 1 : **passage piéton** (à feux) de k ≈ 406 avec **ouverture du terre-plein en refuge** et débouchés sur trottoir (photos a880f2d0, 61a21d0a ; OSM). La traversée cyclable en damier jaune n'a pas de mot dans le format (`BESOINS.md` V-O1). Détail : `RECONSTRUCTION.md`.
