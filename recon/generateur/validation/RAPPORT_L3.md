# Rapport du lot L3 : solveur de carrefours plans (géométrie)

*`recon/generateur/validation/RAPPORT_L3.md` — 18/10/2026. Critères : `validation/rapport_L3.json` ; détail mesuré :
`validation/controles_L3.json` (contrôle indépendant `validation/controler_L3.py`, Python + numpy, sans Houdini).
Documentation de l'API : `hda/README_RG.md` § 9.*

Demande : « le PCG doit reproduire des autoroutes, des ronds-points, plusieurs types de bordures… et **surtout les
carrefours complexes** ». Ce lot fabrique dans Houdini l'**intérieur des carrefours plans** décrits par le lot
« scenes » (J1-J5) : jusqu'ici les branches se chevauchaient au centre. Route seule : sol neutre plat autour, ciel
simple et soleil, aucune végétation.

## 1. Ce qui a été fait

| Élément | Fichier | Rôle |
|---|---|---|
| HDA `rg::carrefours::1.0` | `hda/rg_carrefours/` (`construire.py`, `vex_solveur.py`, `lecteur_carrefours.py`, `vex/rg_carrefour.h`) | solveur (plan § 2.4, étapes 1 à 4) : branches, bords de chaussée, coins tangents, coupes des routes et des trottoirs, nez des îlots, frontière fermée |
| HDA `rg::carrefours_sol::1.0` | `hda/rg_carrefours/` (`vex_sol.py`) | étapes 5-6 et sol : sol étanche du cœur, des coins et des nez ; bordures (coins, nez, îlots du cœur) avec abaissés et BEV ; lignes CÉDEZ / STOP / effet des feux ; passages sans route |
| Pilote | `fabriquer_carrefours.py` | chaîne L1 + L2 + L2b + carrefour ; balayages des véhicules (lot L3a) ; exports `l3/` ; rendus (2 vues, 3 pour J5) |
| Contrôle, rapport | `validation/controler_L3.py`, `validation/faire_rapport_L3.py` | mesures sur la géométrie fabriquée |
| Documentation | `hda/README_RG.md` § 9 (ajout) | API pour les lots giratoires, marquages, signalisation |

Aucun fichier partagé n'est modifié (hors l'ajout du § 9 au README) : le pilote importe `fabriquer_generateur`,
`fabriquer_l2` et `fabriquer_l2b` et assemble son propre réseau ; les HDA `rg::*` et `pj::*` existantes sont utilisées
telles quelles.

**Principe.** `rg::carrefours` se place entre `rg::lire_modele` et `rg::graphe` : il raccourcit chaque branche à la fin
de sa chaussée (`s_end`) et, au-delà de l'amorce du coin (`s_cut`), lui donne un **profil réduit** (trottoir et bordure
extérieure retirés, transition instantanée hors de l'emprise commune : `rg::nivellement` ne pose aucun retour). Toute la
chaîne existante (sol, bordures, îlots des branches, passages et refuges, marquages de section) fabrique donc les
branches jusqu'à la frontière ; `rg::carrefours_sol` fabrique le reste : cœur, coins (congé tangent aux bords réels,
amorces de 3 m), trottoirs de coin, nez arrondis des îlots du profil, îlots du cœur, avec les mêmes conventions de Z
(`rg_coupe` du modèle unique aux raccords, harmonique ailleurs) et le même contrat que `rg::sol`, `rg::vers_entites` et
`rg::marquages`.

## 2. Les cinq scènes

| Scène | Contenu fabriqué | Mesures clés |
|---|---|---|
| J1 T en cédez | 2 congés R 8, coin droit (côté nord), 2 abaissés + BEV sur les congés, CÉDEZ T'2 | traversée 7,61 m ; CÉDEZ au bord de la chaussée prioritaire (0,000 m) ; passage à 2,00 m ; raccords 0,13 mm |
| J2 croix en STOP | 4 congés R 12 de chaussée revêtue (bande dérasée de la RD), bermes de coin sans bordure, 2 STOP | rayons 12,000 m ; STOP à 0,000 m ; marche de 2,0 cm au point commun RD / VC (§ 4) |
| J3 croix à feux | 4 congés R 8, 8 abaissés + BEV (passages des quatre branches dans les coins) | traversées 8,14 m ; ligne d'effet virtuelle (ARB-01) : rien de peint |
| J4 îlots | 3 congés R 8 + voie directe R 25 (bord réel suivi dans l'ouverture à 1/15), 2 nez arrondis, îlot directionnel du cœur (bordure I2, refuge abaissé, BEV), traversée de la voie directe, 3 CÉDEZ | traversées ≤ 6,76 m, refuges 2,00 et 3,29 m ; nez VL : marge 0,45 m |
| **J5 carrefour complexe** | artère 2 × 2 + TAG, TPC planté et îlots de TAG (6 nez arrondis), rue à îlots, voie directe R 30 + îlot directionnel, 10 abaissés + BEV, 8 lignes d'effet / de sas, CÉDEZ de la voie directe | traversées ≤ 8,57 m, refuges 5,00 et 2,00 m ; frontière fermée (838 m²) ; 3 vues |

Rendus (Karma XPU, 2 vues par scène, 3 pour J5 ; planches ≤ 1092 px regardées en entier, vues > 1092 px regardées en
tuiles natives) : `recon/out/generateur/J*/rendus/planche_J*.png`. Vue conducteur sur la branche à CÉDEZ / STOP (sinon la
plus large), 30 m avant la frontière, voie entrante de droite, 1,20 m ; vue de dessus centrée sur le carrefour.

## 3. Critères mesurés

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L3-1 coins tangents | rupture max 0,398° (polyligne) ; tangence de l'arc ajusté 0,000° (18 congés) | ≤ 0,5° | oui |
| L3-2 rayon = consigne | écart max 0,00 mm ; file de bordure fabriquée sur la face à 0,00 mm | ± 1 cm | oui |
| L3-3 frontière fermée et simple | 5/5 | 5/5 | oui |
| L3-4 lignes CÉDEZ / STOP à la limite de la chaussée prioritaire | écart max 0,000 m (5 lignes de branche) | 0 ± 0,05 m | oui |
| L3-5 passages à 2 m de la ligne CÉDEZ / STOP | 2,00 m (5 passages) | 2,00 ± 0,05 m | oui |
| L3-6 refuges au droit des passages | min 2,000 m (9 refuges) | ≥ 2,00 m | oui |
| L3-7 aucune ligne CÉDEZ sur une branche à feux | 0 | 0 | oui |
| L3-8 **traversée hors refuge (bloquant)** | max 8,57 m (11 passages) | ≤ 12 m | oui |
| L3-9 nez au premier contact des balayages + 0,30 m, VL | marge min −1,256 m ; 4/8 nez | ≥ 0,30 m | **non** |
| L3-9 nez au premier contact des balayages + 0,30 m, bus 12 m | marge min −5,400 m ; 0/8 nez | ≥ 0,30 m | **non** |
| L3-10 îlots directionnels hors des balayages | 0,583 m | ≥ 0,30 m | oui |
| L3-11 sol étanche : écart aux raccords | J1 0,13 ; J2 20,0 ; J3 0,13 ; J4 1,74 ; J5 0,21 mm | ≤ 1 mm | **non** (J2, J4) |
| L3-12 sol étanche : bords libres hors bord extérieur | J1 1 ; J2 5 ; J3-J5 0 | 0 | **non** (J1, J2) |
| L3-13 vue des bordures T2 du carrefour | écart max 2,0 mm | ± 5 mm | oui |
| L3-14 abaissés avec BEV | 27/27 | 27/27 | oui |
| L3-15 scènes fabriquées jusque dans le carrefour | 5/5 | 5/5 | oui |
| L3-16 planches regardées en tuiles natives | 5/5 | 5/5 | oui |
| L3-17 déterminisme (J1, J4 ; deux processus, une fois en fin de lot) | identique (60 fichiers : L1, L2, L2b, L3) | identique | oui |

Critère du plan sans objet ici : la goutte d'eau ACI interurbaine (pointe à 1,00 m, saillie 0,50 m) ; aucune scène J
n'en a (J2, seule scène hors agglomération, n'a pas d'îlot).

## 4. Problèmes restants (non atteints, honnêtement)

- **Nez des îlots et balayages (L3-9).** Le solveur calcule le retrait requis (balayages du lot L3a, VL et bus standard
  12 m, approche et sortie de 15 m dans l'axe des voies) : 5,45 à 5,70 m pour le bus sur les huit nez, 1,56 m pour le VL
  sur le TPC de J5. Il est **plafonné** pour garder les refuges : les passages de J4 et J5 sont à 2 m de la frontière et
  traversent les îlots ; reculer le nez supprimerait le refuge (essai : traversées de 27 m sans refuge sur l'artère de
  J5). Les nez restent donc à la frontière et le critère n'est pas atteint : le bus balaie les nez (voies de sortie de
  3,00 m trop étroites pour un bus qui vient de tourner), et le VL balaie le nez du TPC de J5 en suivant le TAG guidé du
  modèle (polyligne à angle vif de 45° dès la frontière). À trancher dans la description (passages plus en retrait,
  voies de sortie élargies, nez franchissables) ou par les lots scenes / L4 (tracé des TAG guidés).
- **Trajectoires du modèle trop serrées.** Les TAG de J1-J4 ont un rayon d'axe de 4,47 m (< 5,47 m pour le VL, 8,65 m
  pour le bus) : infaisables, donc exclus du calcul des nez ; signalé au lot scenes.
- **J2 : marche de 2,0 cm** aux quatre coins du cœur : la bande dérasée de la RD (bord à −0,095 m) et la voie de la VC
  (bord à −0,075 m) n'ont pas le même Z à leur point commun ; le sol du carrefour ne peut raccorder les deux. Il faut un
  raccordement du profil en long de la VC (nivellement des carrefours, plan § 8), hors de ce lot. Mêmes points : 5 bords
  libres.
- **J4 : 1,74 mm** en un point du bord réel de la branche sud dans l'ouverture à 1/15 (sous 1 mm partout ailleurs) ;
  **J1 : 1 bord libre** sous la bordure droite du côté nord (zone cachée sous la bordure).
- **Bordures I2** : la sonde de fabriquer_l2 à 7 cm de la face tombe sur le chanfrein et ne lit pas la vue ; les I2 du
  carrefour (0,071-0,091 m) se lisent comme celles posées par la chaîne sur les branches (0,071-0,085 m). Les T2 sont
  dans ± 5 mm.
- **Lot L4 et amont** : les bandes de passage du modèle de J5 couvrent aussi le TPC engazonné (peintes sur le refuge par
  `rg::marquages`) ; les lignes de rive de la RD de J2 vont jusqu'à la frontière (interruption au droit de la VC à décider
  au lot marquages) ; marquages internes de J5 non faits (guidage T'2 0,10, figurines, zones de sas) ; signaux au lot L6.
- **Choix [G] déclarés** : amorce droite de 3 m des bordures de coin ; phase des tirets T'2 (motif centré) ; trottoir de
  coin à largeur interpolée le long du congé ; bandes des passages sans route rectangulaires dans le repère de la voie ;
  chaussée du cœur par interpolation harmonique (le toit de la route prioritaire n'est pas prolongé tel quel).
- **Limites** : branches tracées vers le centre, axe droit près du carrefour ; pas de caniveau ni de ralentisseur dans
  le carrefour ; giratoires, mini-giratoires et bifurcations laissés aux autres lots (ignorés par le solveur).

## 5. Corrections faites en cours de lot (constatées sur les plans de contrôle, les mesures et les rendus)

- Contour du domaine vide : un détail VEX ne relit pas les primitives qu'il crée ; tableaux à plat.
- NIVEAUX sans références échantillonnées : Z nul partout ; entrée 4 (références de `rg::graphe`) fusionnée.
- Sol sous la bordure plat au pied : marche de 3,4 mm contre la branche ; chaussée prolongée avec la pente de la voie
  (0,13 mm).
- Ouverture d'îlot à 1/15 dans le congé R 25 de J4 : bord supposé constant, bande non raccordée de 6 m ; congé tangent au
  bord réel, itéré, amorces et bords sur le bord réel.
- Pied linéaire sur les longs côtés des îlots du cœur (bordure 5 cm sous le sol) : faces densifiées à 0,5 m ; boucle
  d'îlot ouverte hors des passages (abaissé coupé en deux).
- Nez reculés de 5,6 m par le bus : refuges perdus ; retrait plafonné, retrait requis rapporté.
- Amorce oblique des balayages (premier segment des TAG guidés) : contact fictif à 3,5 m dans la branche ; approche et
  sortie dans l'axe des voies.
- Vue conducteur trop loin et sur la route prioritaire : caméra propre sur la branche à CÉDEZ / STOP.

## 6. Interface pour les autres lots

`hda/README_RG.md` § 9 : SOLVEUR (branches, coins, nez, embouchures, frontière : attributs), contrat des sorties de
`rg::carrefours_sol`, exports `l3/carrefours.json` et `l3/mesures_l3.json`, commandes.
