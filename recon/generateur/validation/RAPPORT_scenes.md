# Rapport du lot « scenes » : carrefours, giratoires, autoroutes dans la description simple

*`recon/generateur/validation/RAPPORT_scenes.md` — 17/10/2026. Détail mesuré : `validation/controles_scenes.json`
(186 attendus, 42 contrôles de cohérence) ; critères : `validation/rapport_scenes.json`.*

Demande : « le PCG doit reproduire des autoroutes, des ronds-points, plusieurs types de bordures… et surtout les
carrefours complexes ». Ce lot étend la **description simple** (YAML lisible → `modele_voie/0.1`) aux réseaux : carrefours
plans à régimes, îlots et feux, giratoires, autoroutes et bretelles ; il écrit 12 scènes de test, leurs plans cotés et
leurs attendus mesurés. Route seule : ni décor ni végétation (seul le gazon des îlots et des TPC est décrit).

## 1. Ce qui a été fait

| Élément | Fichier | Nature |
|---|---|---|
| Compilateur de réseau | `description/carrefours.py` (nouveau) | branches, frontières, lignes, passages, sas, coins, îlots (profil et directionnels), trajectoires, conflits, zone de conflit, guidage, feux et contrôleur, signaux, giratoires (anneau, îlot central, îlots ACI, raccordements, déflexion), bretelles (musoir, chevrons, J14a) |
| Plan coté SVG | `description/plan_reseau.py` (nouveau) | ensemble + zoom par carrefour, rendu PNG (PyMuPDF) pour la découpe en tuiles |
| Compilateur existant | `description/description_vers_modele.py` | ajouts : clés `carrefours`, `giratoires`, `bretelles`, `plan`, `troncons[].id` ; évènements `ouverture`, `fermeture` ; `élargissement` de type insertion / décélération ; crochet de réseau ; demi-bandes centrales (référence au milieu) |
| Format du profil | `description/format_profil.py`, `vocabulaire.py` | séparateur dimensionné (`GBA largeur 0,6`), terre-plein de plain-pied, voies d'insertion / de décélération / TAG / TAD, `franchissable pl` |
| Schéma | `schema/modele_voie.schema.json` | ajouts facultatifs : `ilot.porte_par_profil`, `branche.s_frontiere_m`, `controleur.groupes` |
| Documentation | `description/FORMAT_DESCRIPTION.md` § 15 | réseau, branches, îlots, feux, guidage, giratoires, autoroutes, contrôle |
| Scènes | `scenes_carrefours/J1-J5`, `scenes_giratoires/G1-G3`, `scenes_autoroutes/A1-A4` (+ `plans/*.svg`) | valeurs réalistes, règle citée en tête de chaque fichier, liste `attendus` |
| Contrôle | `validation/controler_scenes.py` | compile, mesure les attendus, cohérence, rétrocompatibilité, déterminisme |

Rétrocompatibilité tenue à l'octet : les 12 scènes S01-S12, les 12 exemples et les 3 scènes de Meylan donnent le même
`modele_voie.json` **et** le même `compilation.json` qu'avant le lot (empreintes prises avant toute modification) ;
le banc existant `description/tests/tester_descriptions.py` passe en entier (27 / 27 valides, 25 / 25 faits, 26 / 26
erreurs attendues).

## 2. Les 12 scènes

| Scène | Contenu | Mesures clés (modèle) |
|---|---|---|
| J1 T en cédez | rue 2 × 1 prioritaire, secondaire en cédez, passage, continue d'approche 15 m | frontières 3,00 m ; cédez à 3,00 m ; passage à 5,50 m ; 9 conflits (3 / 3 / 3) ; zone 36 m² |
| J2 croix en STOP | RD 80 km/h, voie communale en STOP ; AB4, AB5 et AB2 à 150 m, J3 × 4, coins 12 m | 16 croisements / 32 conflits (référence CU), 18 géométriques (2 TAG opposés) |
| J3 croix à feux | 2 phases (25 s / 20 s), R11 + répétiteur × 4, R12 × 8, ligne d'effet non peinte (ARB-01) | cycle 55 s (jaune 3 s, dégagement 2 s) ; 16 / 32 conflits de référence |
| J4 îlots | îlots séparateurs urbains de 2,00 m (ouverture 1/15 + nez hachuré), shunt de TAD R 25 m / 4 m en cédez | refuges 2,00 / 2,00 / 3,29 m ; AB3a × 3 ; îlot directionnel hors des voies (0 m²) |
| **J5 carrefour complexe** | artère 2 × 2 + voies de TAG séparées des directs par des îlots portant les R11 ; 3 phases (directs + TAD / **TAG en phase spéciale** / rue) ; TAG à l'indonésienne **guidés T'2 0,10** ; sas vélos 4 m ; îlots séparateurs de la rue ; shunt R 30 m en cédez ; passages à refuges | 14 trajectoires ; croisements par phase P1 0 / P2 0 / P3 3 ; TAG guidés sans croisement ; voies directes alignées (écart 0) ; refuges ≥ 2,00 m ; traversée max 7,50 m ; zone 200 m², trajectoire max 25 m ; cycle 78 s ; 17 signaux, 7 îlots |
| G1 giratoire urbain Ø 40 | anneau 7, couronne pavée 1,50, îlot central engazonné, gouttes d'eau ACI (H 20, B 5), passages à 5 m | déflexion 25,39 m ; refuges 2,12 m ; raccords Re 15 / Rs 20 ; AB25 × 4, B21-1 × 4 |
| G2 giratoire périurbain Ø 50 | hors agglomération, anneau 8, ACI tableaux 1 et 2 (H 25, B 6,25), AB3a + M9c, AB25 à 150 m | déflexion 31,45 m ; entrée 4,00 / sortie 5,00 ; îlots dans l'enveloppe (0 m² hors) |
| G3 mini-giratoire Ø 20 | îlot central franchissable en dôme 10 cm, anneau 8, îlots franchissables 1,50 m, zone 30 | Rext 10, Ri 2 ; entrée 3,00, sortie 3,25 ; angles 90° ; pas de B21-1 |
| A1 autoroute 2 × 2 | voies 3,50, BAU 3,00, BDG 1,00, TPC 2,60 à GBA (0,60) | plate-forme 24,60 m ; T1 2u, BAU T4 3u, TPC continue 3u ; u = 7,5 cm ; 0 bordure |
| A2 autoroute 2 × 3 | TPC 5,00 engazonné entre deux glissières | plate-forme 34,00 m ; 2 glissières |
| A3 bretelle d'entrée | obliquité 1/25, musoir (chevrons de E.5,00 à E.1,00), voie d'insertion 200 m depuis E.1,00 + biseau 75 m, T2 5u, BAU interrompue | point à 1 m : 25,0 m ; à 5 m : 125,25 m ; voie d'insertion s 300 → 550 |
| A4 bretelle de sortie | biseau de déboîtement 150 m, T2 5u, obliquité 1/33, musoir à chevrons, J14a, BAU reprise au nez | point à 1 m : 33,0 m ; à 5 m : 165,25 m |

## 3. Critères mesurés

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| SC-01 scènes compilées en modèle valide (validateur, provenance exigée) | 12 / 12 | 12 / 12 | oui |
| SC-02 non-conformités bloquantes | 0 | 0 | oui |
| SC-03 attendus mesurables retrouvés | 186 / 186 | 100 % | oui |
| SC-04 rétrocompatibilité (S01-S12, exemples, Meylan : modèle et rapport) | 27 / 27 à l'octet | 27 / 27 | oui |
| SC-05 îlots en saillie hors des voies motorisées | 0,000 m² (16 îlots) | ≤ 0,05 m² | oui |
| SC-06 îlots de giratoire dans l'enveloppe peinte | 0,000 m² (12 îlots) | ≤ 0,05 m² | oui |
| SC-07 branches qui se rejoignent | extrémités à ≤ 0,05 m (imposé), excentration 0 | ≤ 0,05 / ≤ 0,5 m | oui |
| SC-08 continuité de la voie des bretelles à la jonction | 0,000 / 0,006 m | ≤ 1,75 m | oui |
| SC-09 déterminisme J5 et G1 | 2 / 2 identiques | 2 / 2 | oui |
| SC-10 J5 : TAG guidés sans croisement | 0 | 0 | oui |
| SC-11 J5 : TAG guidé jamais avec le direct opposé | 0 | 0 | oui |
| SC-12 traversées hors refuge (bloquant) | max 7,50 m | ≤ 12 m | oui |
| SC-13 refuges au droit des passages | min 2,00 m | ≥ 2,00 m | oui |
| SC-14 déflexion des giratoires | 25,39 / 31,45 m | ≤ 100 m | oui |
| SC-15 croix complète, décompte de référence | 16 / 32 | 16 / 32 | oui |
| SC-16 plans cotés regardés en tuiles natives | 12 / 12 scènes | 12 / 12 | oui |

Deux attendus écrits à la main étaient faux et ont été corrigés après mesure, sans toucher à aucun seuil : le cycle de
J3 (63 s annoncé par une erreur d'addition ; la règle donne 25 + 3 + 2 + 20 + 3 + 2 = 55 s, dégagement
ceil(13 m / 10 m/s) = 2 s) et le nombre d'îlots séparateurs de J5 (4 annoncés ; les nez des deux TPC sont aussi des îlots
de carrefour : 6).

## 4. Corrections faites en cours de lot (constatées sur les plans en tuiles)

- J5 : les voies directes de l'artère n'étaient pas alignées de part et d'autre (déport d'un seul côté) ; refait en
  déport symétrique avec une ligne de référence décalée de 2,50 m par deux arcs de 276,25 m (la séparation des sens suit
  le centre du TPC) : écart latéral mesuré 0.
- Ouverture d'un îlot entre les sens : la référence (constante par profil) restait au bord de la bande qui s'ouvre, d'où
  un ressaut de 1 m au nez de l'îlot ; corrigé par deux demi-bandes centrales (`*_axe_g`, `*_axe_d`) avec la référence
  entre elles.
- TAG à l'indonésienne : les arcs « au plus grand rayon » se coupaient ; tracé refait selon RF-MQ-CAR-03 (prolongement +
  oblique à 45°) : 0 croisement, chaque courant garde la ligne de guidage à sa droite.
- Déflexion : le cercle de construction était cherché du mauvais côté (10 000 m) ; corrigé (tangence intérieure à
  l'îlot + 1,50 m) : 25,39 m pour G1, valeur recalculée à la main.
- Bretelles : la référence d'une bretelle à sens unique est au milieu de « voie + BAU », pas sur l'axe de voie ; tracés
  recalés de 1,50 m (continuité 0,006 m à la jonction).

## 5. Problèmes restants et limites

- **ICTAAL absente des sources locales** : les bretelles A3 / A4 sont cotées selon la VSA 90/110 (Cerema 2014 p. 31-38,
  schémas 14 et 26 lus en tuiles) ; la principale est déclarée à 110 km/h en conséquence.
- **Anneau des giratoires** : la bordure et le trottoir extérieurs de la route d'anneau sont continus dans le modèle ; leur
  interruption aux débouchés (raccords Re / Rs fournis dans `anneau.construction.raccordements`) est au solveur
  `rg::carrefours` ; de même, les trottoirs des branches vont jusqu'à l'extrémité et doivent être coupés aux points de
  tangence des coins (le plan les coupe pour le contrôle).
- **Enveloppe des îlots de giratoire** : décrite par une zone hachurée dans le profil ; l'îlot en saillie est une entité
  posée dessus. Les hachures doivent être peintes seulement hors de l'îlot (sinon visibles dans la saillie de 0,50 m).
- **Positions des signaux** (AB3a, AB4, R11, R12, B21-1, J3, J14a) : premier placement réglé (DEF-025, DEF-027, 0,70 m de
  la rive) ; le placement fin (ARB-20, cheminement de 1,40 m) reste au lot L6.
- **Trajectoires** : droite – arc – droite le long des axes, branches rectilignes au voisinage du carrefour ; pas encore
  d'épure de balayage (lot L3a) : nez d'îlots à la frontière, pas « au premier contact des balayages + 0,30 m ».
- **Îlots de la rue (J4, J5)** : nez à la limite de la chaussée abordée (aucun retrait chiffré par une règle urbaine).
- **Rendus Houdini** : non faits dans ce lot (pas de HDA de carrefour à ce jour) ; le contrôle visuel porte sur les plans
  cotés SVG rendus en PNG et regardés en tuiles ≤ 1092 px.
- Plans : les tirets T1 / T4 de grande longueur ne ressortent pas toujours au rendu PyMuPDF (la modulation est dans le
  modèle, vérifiée par le contrôleur).

## 6. Interface pour les autres lots

- Entrée : `python recon/generateur/description/description_vers_modele.py <scène>.yaml` → `recon/out/generateur/<scène>/`
  (`modele_voie.json`, `compilation.json` avec `reseau.objets`, `reseau.controles`, `reseau.avertissements`).
- Modèle : `carrefours[]` (types plan_simple / plan_ilots / plan_feux / giratoire / mini_giratoire / bifurcation ;
  branches avec `s_frontiere_m`, `ligne_arret`, `ligne_axiale_approche`, `passage_pieton`, `sas_velo`, `coin_droit`,
  `fleches`, `ilot_separateur`, `signaux` ; `frontiere` joints ; `zone_conflit` ; `trajectoires` avec géométrie,
  `rayon_min_m`, `guidage` ; `conflits` ; `passages_pieton` ; `anneau` ; `controleur`), `ilots[]` (polygones ; `porte_par_profil`
  pour ceux que fabrique une bande), `signaux[]` (position xyz + route/s/t), `controleurs[]` (phases, états, `groupes`),
  `marquages[]` (ligne_transversale, ligne_guidage, sas_velo, figurine_velo, fleche, passage_pieton, chevrons),
  routes `anneau_giratoire` (fermées) et `bretelle`, nœuds `carrefour` / `fourche`.
- Plans : `python recon/generateur/description/plan_reseau.py <sortie> --plans <dossier> --nom <id>`.
- Contrôle : `python recon/generateur/validation/controler_scenes.py --determinisme --json validation/controles_scenes.json`.
