# Rapport du lot L2b : marquages de la section courante et rendus soignés (S01-S12)

*`recon/generateur/validation/RAPPORT_L2b.md` — produit par `python recon/generateur/validation/faire_rapport_L2b.py` (données : `rapport_L2b.json`, `controles_L2b.json`, `constats_visuels_L2b.json`). Houdini 22.0.459 Indie (hython), VEX interprété, Karma XPU (husk). Base de règles lue, non modifiée : `regles_route_fr/1.0` ; dossier 08 lu, non modifié.*

**Statut : partiel — 14 critères sur 16 atteints**, 1 reporté(s) à l'étape 2 (décision de l'utilisateur : la route seule)

## 1. Ce que le lot apporte

Une description simple (« voie ← | T'1 | voie → », un passage piéton ici, un dos-d'âne là, une réduction de voies avec
ses flèches de rabattement) est compilée en modèle (L0), échantillonnée (L1), nivelée et fabriquée en sol, bordures et
caniveaux (L2), puis **peinte** :

```
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S08_rue_dos_d_ane_passage.yaml --l2b --rendus
  -> recon/out/generateur/S08/l2b/      empreintes, peinture (maillages), mesures, route_l2b.usda
  -> recon/out/generateur/S08/rendus/   dessus, oblique, conducteur, piéton, détail ; planche_S08.png ; tuiles
```

- **rg::marquages::1.0** (nouvelle HDA, VEX) : empreintes exactes de toutes les marques de la section courante —
  lignes à modulation IISR (RF-MQ-MOD-*), rives, continues, obliques, flèches directionnelles et de rabattement,
  triangles de dos-d'âne, passages piétons (n et e par DEF-011 / RF-MQ-PP-05), zébra (DEF-020), figurines vélo, BUS au
  sol (glyphes de 1,50 m) — gabarits et glyphes du dossier 08 au sommet près ; chaque empreinte est découpée aux lignes
  de rupture du sol (couronne, bandes, rampes, dos-d'âne) et jamais posée sur une bordure ou un caniveau ;
- **pj::marquage_solide::1.0** réutilisée deux fois (peinture des lignes 2 mm, enduit des autres marques 3 mm,
  TQ-MQG-002), drapée sur le sol fabriqué (TQ-MQG-005) ;
- **rendus soignés** (`rendu/rendu_l2b.py`) : matériaux PBR de la bibliothèque (enrobé usé, béton des bordures,
  trottoir, BEV, herbe sans répétition visible, peinture avec masques d'usure), ciel physique et nuages, soleil bas,
  arbres procéduraux, sol de décor raccordé au bord du sol fabriqué, caméras standard et planches catalogue
  (rendus refaits par la correction après contrôle : § 8).

## 2. Critères

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L2b-1 HDA rg::marquages (dossier développé, signature stable, reconstruction identique) ; pj::marquage_solide::1.0 et pj::gabarits_iisr::1.0 réutilisées telles quelles | signature 8ae8d3514225 stable, dossier identique ; gabarits dérivés du dossier 08 à jour | stable, identique | oui |
| L2b-2 fabrication des marquages de S01-S12 sans erreur | 12 / 12 | 12 / 12 | oui |
| L2b-3 lignes : tirets conformes aux modulations IISR (RF-MQ-MOD-*) ; période et trait ± 1 cm, dérive cumulée sur un tronçon ≤ 1 cm sur 100 m ; début et fin de chaque tiret ± 1 cm | 347 tirets pour 347 attendus, 0 manquant, 0 en trop ; période max 0,006 mm, trait max 0,004 mm, dérive max 0,006 mm (308 périodes) ; début/fin max 0,011 mm | 0 écart de tirets ; ≤ 10 mm | oui |
| L2b-4 largeur des lignes (largeur_u × u) ± 2 mm, centrées sur leur limite | écart de largeur max 0,006 mm ; décentrage max 0,002 mm | ≤ 2 mm | oui |
| L2b-5 flèches, triangles, figurines, lettres : sommets = gabarit du dossier 08 ± 1 mm, orientation ± 0,5°, centrage ± 2 cm | 26 / 26 posés ({'fleche': 11, 'figurine': 8, 'symbole': 6, 'inscription': 1}) ; écart au gabarit max 0,004 mm ; rotation max 0.0000° ; centrage max 0.11 cm | ≤ 1 mm ; ≤ 0,5° ; ≤ 2 cm | oui |
| L2b-6 positions et interdistances des flèches (RF-MQ-RAB-05 depuis le point de référence ; DEF-017 : 20 m) ± 0,05 m ; pointe de la dernière flèche à 1,50 m d'une ligne transversale | 4 séries, écart max 0.0018 m, 0 non conforme ; pointe à 1,50 m : sans objet (aucune ligne transversale dans les scènes de section courante, lot L3) | ≤ 0,05 m | oui |
| L2b-7 passages piétons : n = floor(W − 0,50) dans la plage IISR, e = (W − 0,5 n)/(n + 1) ± 1 cm, bandes 0,50 ± 2 mm, longueur = zone du modèle ± 1 cm (DEF-011, RF-MQ-PP-02 à -05) | 2 / 2 conformes ; e max 0,000 mm ; largeur max 0,000 mm ; longueur max 0,000 mm | 100 % ; ≤ 10 mm ; ≤ 2 mm | oui |
| L2b-8 zébra : hachures à 26,565 ± 0,1° de la rive, pas perpendiculaire 1,85 ± 0,01 m, aplats sous 0,30 m (DEF-020, RF-MQ-HACH-01, -03) | 1 zébra : 4 hachures (0 sans angle mesurable), 2 aplats ; écart d'angle max 0.0001° ; écart de pas max 0,000 mm | ≤ 0,1° ; ≤ 10 mm | oui |
| L2b-9 peinture posée sur le sol fabriqué : dessus − sol = 2 mm (lignes) ou 3 mm (autres marques) ± 0,3 mm aux sommets et aux centres des faces du dessus (TQ-MQG-002, TQ-MQG-004, TQ-MQG-005) ; 0 m² sur une bordure ou un caniveau (TQ-MQG-014) | lignes : 6872 sommets, écart max 0,000 mm, 7776 centres, écart max 0,090 mm ; autres : 11769 sommets, 0,000 mm, 17718 centres, 0,231 mm ; sans sol 0 ; sur bordure ou caniveau 0.0000 m² | ≤ 0,3 mm ; 0 m² | oui |
| L2b-10 M1 : 100 % des maillages visibles texturés (couleur diffuse lue dans une texture, coordonnées de texture présentes) | 135 / 135 maillages, 12 scènes | 100 % | oui |
| L2b-11 L1 : dynamique p99 − p1 de la luminance de chaque rendu ≥ 0,75 (exposition fixe) | 1 / 66 rendus ; min 0.503 ; sous le seuil : S01/conducteur 0.536, S01/dessus 0.530, S01/detail 0.565, S01/oblique 0.524, S01/pieton 0.532, S02/conducteur 0.657, S02/dessus 0.558, S02/detail 0.697, S02/oblique 0.525, S02/pieton 0.532, S03/cible_angle_avancee 0.729, S03/conducteur 0.676, S03/dessus 0.656, S03/detail 0.659, S03/oblique 0.527, S03/pieton 0.537, S04/conducteur 0.585, S04/dessus 0.586, S04/detail 0.688, S04/oblique 0.543, S04/pieton 0.549, S05/conducteur 0.656, S05/dessus 0.623, S05/detail 0.528, S05/oblique 0.521, S05/pieton 0.503, S06/conducteur 0.654, S06/dessus 0.682, S06/detail 0.544, S06/oblique 0.552, S06/pieton 0.535, S07/conducteur 0.654, S07/dessus 0.667, S07/detail 0.568, S07/oblique 0.527, S07/pieton 0.536, S08/cible_abaisse_bev 0.557, S08/conducteur 0.657, S08/dessus 0.598, S08/detail 0.646, S08/oblique 0.531, S08/pieton 0.532, S09/cible_coude_bordure 0.602, S09/conducteur 0.654, S09/dessus 0.690, S09/detail 0.569, S09/oblique 0.538, S09/pieton 0.543, S10/cible_caniveau_plateau 0.692, S10/conducteur 0.646, S10/dessus 0.624, S10/detail 0.650, S10/oblique 0.527, S10/pieton 0.532, S11/cible_fin_de_route 0.544, S11/conducteur 0.615, S11/dessus 0.516, S11/detail 0.552, S11/oblique 0.506, S11/pieton 0.531, S12/conducteur 0.584, S12/dessus 0.695, S12/detail 0.707, S12/oblique 0.542, S12/pieton 0.539 | ≥ 0,75 partout | non |
| L2b-12 jeu de caméras standard (dessus, oblique 3/4 ~25 m, conducteur 1,20 m, piéton 1,60 m) rendu pour chaque scène ; planche catalogue par scène et planches d'ensemble ≤ 1092 px, regardées ; tuiles natives regardées | caméras 12 / 12 ; planches 12 / 12 (≤ 1092 px), regardées 15 ; ensemble 4 fichier(s) [[1092, 972], [1092, 972], [1092, 972], [1092, 972]] ; tuiles regardées 120 / 120, 12 scènes | 12 / 12 | oui |
| L2b-13 « attendus » du catalogue vérifiés sur les sorties fabriquées (L1, L2, L2b) | 11 / 12 scènes, 98 / 99 clés ; échecs : ['S03 bordures_m : attendu 256 mesuré 252.0'] | 12 / 12 | non |
| L2b-14 déterminisme (deux processus, octet : l1/, l2/, l2b/) | S01 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S02 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S03 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S04 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S05 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S06 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S07 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S08 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S09 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S10 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S11 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés); S12 : identique (28 fichiers ; .usda : chemins relatifs des matériaux normalisés) | identique | oui |
| L2b-15 témoins négatifs détectés par le contrôle indépendant | 12 / 12 : un tiret T'1 de S02 décalé de 2 cm en long → début/fin max 20.0 mm ; un tiret T3 5u de S04 élargi de 3 mm → écart de largeur max 3.00 mm ; une flèche TD de S07 tournée de 0,6° → rotation 0.600° ; écart au gabarit 41.9 mm ; une flèche TD de S07 décalée de 3 cm en travers → centrage 3.0 cm ; une flèche RAB_D de S01 agrandie de 0,3 % → écart au gabarit 9.24 mm ; une flèche RAB_D de S01 avancée de 10 cm → écart de position max 0.102 m ; une bande du passage piéton de S08 retirée → 4 bandes pour 5 ; un tiret de S08 enfoncé de 0,5 mm → écart d'épaisseur max 0.50 mm ; une hachure du zébra de S09 tournée de 0,3° → écart d'angle max 0.300° ; un tiret T'2 de S03 retiré → traits mesurés {"T'1 2u": 16, "T'2 2u": 64} (attendus {"T'1 2u": 16, "T'2 2u": 65}) ; 1 manquant ; une lettre de BUS (S12) déplacée de 2 mm → écart au gabarit 2.00 mm ; une bande du passage de S10 poussée de 68.3 cm vers la bordure (10 cm dessus) → 0.4802 m² sur bordure ou caniveau | 100 % | oui |
| L2b-16 lisibilité de la vue de dessus (ajouté à côté de L2b-11, relecture adverse) : écarts de luminance médiane trottoir − enrobé et peinture − enrobé ≥ ceux de la référence de l'utilisateur (ref_carrefour_dessus : 0,318 et 0,406) | trottoir − enrobé : S02 0.3488, S03 0.3558, S04 0.3527, S05 0.3233, S06 0.3519, S07 0.3519, S08 0.3519, S09 0.344, S10 0.3516, S11 0.3519, S12 0.3451 (11 / 11) ; peinture − enrobé : S01 0.4516, S02 0.5065, S03 0.5104, S04 0.5219, S05 0.5261, S06 0.5144, S07 0.5298, S08 0.4477, S09 0.5222, S10 0.4398, S11 0.5222, S12 0.5261 (12 / 12) ; enrobé : S01 0.3173, S02 0.3173, S03 0.3134, S04 0.3134, S05 0.3134, S06 0.3173, S07 0.3173, S08 0.3173, S09 0.3249, S10 0.3173, S11 0.3173, S12 0.3212 | ≥ 0,318 et ≥ 0,406 sur chaque scène | oui |
| L2b-17 arbres rendus aux dimensions du modèle (relecture adverse) : cartes de feuilles 0,08-0,15 m, rien sous le fût (gabarit RF-OSM-VEG-001 : 3,80 m au-dessus de la chaussée, 2,50 m au-dessus d'un trottoir), rayon du feuillage dans [0,85 ; 1,05] × houppier, hauteur ≤ 1,02 H | aucun arbre rendu : étape 1, la route seule (décision de l'utilisateur du 17/10/2026) ; dimensions portées dans le modèle (L0-16), code de rendu gardé et désactivé | 100 % | reporté (étape 2 (végétation)) |

## 3. Mesures (contrôle indépendant)

Méthode : `controler_L2b.py` relit la peinture fabriquée (sommets du pied de la jupe, au ras de l'empreinte ; sommets et centres des faces du dessus avec leur hauteur au-dessus du sol fabriqué, rayon vertical posé dans Houdini) et la compare aux marques recalculées par `analytique_L2b.py` à partir du modèle, des règles et des gabarits du dossier 08 lus directement (aucun code commun avec le VEX). Symboles : écarts des sommets au gabarit posé (dans les deux sens), rotation par ICP, position par le centre de surface des faces du dessus (biais du chanfrein ≤ 2 mm).

| Contrôle | Résultat |
|---|---|
| Tirets | 347 fabriqués / 347 attendus ; début et fin max 0.0110 mm ; largeur max 0.0060 mm ; décentrage max 0.0020 mm |
| Modulations | 308 périodes ; écart de période max 0.0060 mm ; trait 0.0040 mm ; dérive cumulée 0.0060 mm |
| Symboles | {'fleche': 11, 'figurine': 8, 'symbole': 6, 'inscription': 1} ; écart au gabarit max 0.0040 mm ; rotation 0.0000° ; centrage 0.110 cm |
| Interdistances | 4 séries ; écart max 0.0018 m |
| Passages | 2 / 2 ; e 0.0000 mm ; bandes 0.0000 mm ; longueur 0.0000 mm |
| Zébras | 4 hachures (0 sans angle mesurable), 2 aplats ; angle 0.0001° ; pas 0.0000 mm |
| Épaisseur (dessus − sol) | lignes : 6872 sommets (0.0000 mm), 7776 centres (0.0900 mm) ; autres : 11769 sommets (0.0000 mm), 17718 centres (0.2310 mm) |
| Peinture sur bordure ou caniveau | 0.000000 m² (0 faces) |
| Attendus du catalogue | 98 / 99 clés, 11 scènes |

## 4. Témoins négatifs

- un tiret T'1 de S02 décalé de 2 cm en long → début/fin max 20.0 mm : détecté
- un tiret T3 5u de S04 élargi de 3 mm → écart de largeur max 3.00 mm : détecté
- une flèche TD de S07 tournée de 0,6° → rotation 0.600° ; écart au gabarit 41.9 mm : détecté
- une flèche TD de S07 décalée de 3 cm en travers → centrage 3.0 cm : détecté
- une flèche RAB_D de S01 agrandie de 0,3 % → écart au gabarit 9.24 mm : détecté
- une flèche RAB_D de S01 avancée de 10 cm → écart de position max 0.102 m : détecté
- une bande du passage piéton de S08 retirée → 4 bandes pour 5 : détecté
- un tiret de S08 enfoncé de 0,5 mm → écart d'épaisseur max 0.50 mm : détecté
- une hachure du zébra de S09 tournée de 0,3° → écart d'angle max 0.300° : détecté
- un tiret T'2 de S03 retiré → traits mesurés {"T'1 2u": 16, "T'2 2u": 64} (attendus {"T'1 2u": 16, "T'2 2u": 65}) ; 1 manquant : détecté
- une lettre de BUS (S12) déplacée de 2 mm → écart au gabarit 2.00 mm : détecté
- une bande du passage de S10 poussée de 68.3 cm vers la bordure (10 cm dessus) → 0.4802 m² sur bordure ou caniveau : détecté

## 5. Rendus et revue visuelle

Karma XPU, 12 scènes, caméras dessus, oblique 3/4, conducteur 1,20 m, piéton 1,60 m et une vue de détail ; soleil 42.0° (DistantLight normalisée), ciel de Preetham (turbidité 2.8) ; exposition fixe, courbe « linéaire, épaule au-dessus de 0,80, sRGB, courbe en S 0.5 ». Planches : `recon/out/generateur/<scène>/rendus/planche_<scène>.png` ; ensemble : recon/out/generateur/catalogue_rendus/catalogue_dessus_oblique_1.png, recon/out/generateur/catalogue_rendus/catalogue_dessus_oblique_2.png, recon/out/generateur/catalogue_rendus/catalogue_dessus_oblique_3.png, recon/out/generateur/catalogue_rendus/catalogue_dessus_oblique_4.png. Tuiles regardées : 120 sur 120.

| Rendu | p1 | p99 | p99 − p1 |
|---|---|---|---|
| S01/conducteur | 0.262 | 0.798 | 0.536 (< 0,75) |
| S01/dessus | 0.267 | 0.797 | 0.530 (< 0,75) |
| S01/detail | 0.233 | 0.798 | 0.565 (< 0,75) |
| S01/oblique | 0.274 | 0.798 | 0.524 (< 0,75) |
| S01/pieton | 0.268 | 0.800 | 0.532 (< 0,75) |
| S02/conducteur | 0.141 | 0.798 | 0.657 (< 0,75) |
| S02/dessus | 0.247 | 0.805 | 0.558 (< 0,75) |
| S02/detail | 0.101 | 0.798 | 0.697 (< 0,75) |
| S02/oblique | 0.290 | 0.815 | 0.525 (< 0,75) |
| S02/pieton | 0.274 | 0.806 | 0.532 (< 0,75) |
| S03/cible_angle_avancee | 0.073 | 0.801 | 0.729 (< 0,75) |
| S03/conducteur | 0.121 | 0.797 | 0.676 (< 0,75) |
| S03/dessus | 0.150 | 0.806 | 0.656 (< 0,75) |
| S03/detail | 0.139 | 0.798 | 0.659 (< 0,75) |
| S03/oblique | 0.286 | 0.813 | 0.527 (< 0,75) |
| S03/pieton | 0.269 | 0.806 | 0.537 (< 0,75) |
| S04/conducteur | 0.213 | 0.798 | 0.585 (< 0,75) |
| S04/dessus | 0.246 | 0.831 | 0.586 (< 0,75) |
| S04/detail | 0.131 | 0.819 | 0.688 (< 0,75) |
| S04/oblique | 0.289 | 0.832 | 0.543 (< 0,75) |
| S04/pieton | 0.273 | 0.822 | 0.549 (< 0,75) |
| S05/conducteur | 0.140 | 0.797 | 0.656 (< 0,75) |
| S05/dessus | 0.194 | 0.817 | 0.623 (< 0,75) |
| S05/detail | 0.273 | 0.800 | 0.528 (< 0,75) |
| S05/oblique | 0.293 | 0.814 | 0.521 (< 0,75) |
| S05/pieton | 0.305 | 0.808 | 0.503 (< 0,75) |
| S06/conducteur | 0.144 | 0.798 | 0.654 (< 0,75) |
| S06/dessus | 0.141 | 0.824 | 0.682 (< 0,75) |
| S06/detail | 0.253 | 0.798 | 0.544 (< 0,75) |
| S06/oblique | 0.268 | 0.820 | 0.552 (< 0,75) |
| S06/pieton | 0.269 | 0.805 | 0.535 (< 0,75) |
| S07/conducteur | 0.143 | 0.798 | 0.654 (< 0,75) |
| S07/dessus | 0.143 | 0.810 | 0.667 (< 0,75) |
| S07/detail | 0.229 | 0.798 | 0.568 (< 0,75) |
| S07/oblique | 0.294 | 0.821 | 0.527 (< 0,75) |
| S07/pieton | 0.269 | 0.806 | 0.536 (< 0,75) |
| S08/cible_abaisse_bev | 0.262 | 0.818 | 0.557 (< 0,75) |
| S08/cible_caniveau_dos_ane | 0.104 | 0.859 | 0.755 |
| S08/conducteur | 0.141 | 0.797 | 0.657 (< 0,75) |
| S08/dessus | 0.219 | 0.817 | 0.598 (< 0,75) |
| S08/detail | 0.151 | 0.798 | 0.646 (< 0,75) |
| S08/oblique | 0.290 | 0.821 | 0.531 (< 0,75) |
| S08/pieton | 0.273 | 0.806 | 0.532 (< 0,75) |
| S09/cible_coude_bordure | 0.241 | 0.844 | 0.602 (< 0,75) |
| S09/conducteur | 0.143 | 0.798 | 0.654 (< 0,75) |
| S09/dessus | 0.143 | 0.833 | 0.690 (< 0,75) |
| S09/detail | 0.250 | 0.819 | 0.569 (< 0,75) |
| S09/oblique | 0.294 | 0.832 | 0.538 (< 0,75) |
| S09/pieton | 0.267 | 0.810 | 0.543 (< 0,75) |
| S10/cible_caniveau_plateau | 0.108 | 0.800 | 0.692 (< 0,75) |
| S10/conducteur | 0.151 | 0.798 | 0.646 (< 0,75) |
| S10/dessus | 0.182 | 0.805 | 0.624 (< 0,75) |
| S10/detail | 0.147 | 0.797 | 0.650 (< 0,75) |
| S10/oblique | 0.289 | 0.817 | 0.527 (< 0,75) |
| S10/pieton | 0.273 | 0.806 | 0.532 (< 0,75) |
| S11/cible_fin_de_route | 0.253 | 0.797 | 0.544 (< 0,75) |
| S11/conducteur | 0.182 | 0.797 | 0.615 (< 0,75) |
| S11/dessus | 0.285 | 0.801 | 0.516 (< 0,75) |
| S11/detail | 0.245 | 0.797 | 0.552 (< 0,75) |
| S11/oblique | 0.294 | 0.800 | 0.506 (< 0,75) |
| S11/pieton | 0.270 | 0.801 | 0.531 (< 0,75) |
| S12/conducteur | 0.243 | 0.827 | 0.584 (< 0,75) |
| S12/dessus | 0.139 | 0.833 | 0.695 (< 0,75) |
| S12/detail | 0.120 | 0.828 | 0.707 (< 0,75) |
| S12/oblique | 0.294 | 0.836 | 0.542 (< 0,75) |
| S12/pieton | 0.274 | 0.813 | 0.539 (< 0,75) |

- **S01** : Route rurale 2 × 1 voie sans bordure : rives T2, axe T1 puis T3 d'annonce et continue, flèches de rabattement posées à cheval sur l'axe T3, pointe vers la voie de droite ; usure u2 visible (craquelures sur les traits). Accotements engazonnés. Défauts : Vue de dessus et vue oblique peu contrastées (dynamique 0,286 et 0,367 < 0,75) : asphalte et herbe de luminance voisine, pas d'arbre dans le cadre. Herbe : motif de répétition encore perceptible en vue de dessus.
- **S02** : Rue urbaine 2 voies entre bordures : axe T'1 propre, pas de rive (bordures), bordure éclairée côté soleil, face de bordure et caniveau dans l'ombre de l'autre côté. Défauts : Bande sombre le long de la bordure ombrée (ombre physique de la face de bordure, pas un trou). Dynamique dessus 0,691 et oblique 0,654 < 0,75.
- **S03** : Stationnement longitudinal : T'2 délimitant chaque place, avancées plantées, axe T'1 conforme au catalogue. Défauts : Les houppiers des arbres du modèle encombrent la vue oblique et cachent une partie de la chaussée en vue de dessus. Le modèle porte aussi un T'2 sur les limites bordées des avancées (14 lignes écartées par rg::marquages, à retirer dans le compilateur). Dynamique dessus 0,681 et oblique 0,637 < 0,75.
- **S04** : Bandes cyclables : ligne T3 5u (traits larges, vides 1,33 m) entre voie générale et bande, figurines vélo bien orientées (tête vers l'avant, roues vers le cycliste qui arrive), axe T'1 ; usure légère visible sur le trait le plus proche. Défauts : Aucun défaut de marquage vu. Arbres du décor à feuillage clairsemé.
- **S05** : Pistes cyclables au niveau du trottoir, séparées par une rangée de pavés ; trottoirs en dalles beiges ; figurines vélo sur les pistes ; axe T'1 sur la chaussée ; caniveau sombre côté bas. Défauts : Dynamique oblique 0,748, juste sous 0,75. Les ombres des arbres du décor tombent sur l'herbe seulement.
- **S06** : 2 × 2 voies avec terre-plein central planté : T'1 entre voies, lignes continues le long du TPC, alignement d'arbres sur le TPC, ombres portées réalistes sur la chaussée. Défauts : Feuillage d'une partie de l'alignement devant la caméra en vue oblique. Dynamique dessus 0,688 < 0,75.
- **S07** : Sens unique 2 voies : flèches directionnelles « tout droit » dans les deux voies au même s (6 flèches au total), ligne T'1 entre voies, caniveau côté droit ; la bande claire côté gauche est le dessus de la bordure (pas de rive peinte, conforme au modèle). Défauts : Dynamique dessus 0,707 et oblique 0,671 < 0,75 (ombre d'arbre seule source de contraste).
- **S08** : Dos-d'âne circulaire (4,00 × 0,10 m) : 3 triangles par voie, passage piéton en bandes de 0,50 m juste avant, bandes d'éveil de vigilance et abaissés de bordure, axe T'1 et T3 sur le ralentisseur et ses abords. Défauts : Aucun défaut de marquage vu ; toutes les vues ≥ 0,75.
- **S09** : Réduction de 2 à 1 voie : zébra de 4 hachures et 2 aplats inclinés vers la voie ouverte, ligne oblique arrêtée au bord du caniveau, flèche de rabattement à 51,5 m dans la voie qui disparaît, T'1 interrompu. Défauts : La ligne oblique s'arrête au caniveau au lieu de rejoindre la bordure (règle de raccord absente du référentiel). Toutes les vues ≥ 0,75.
- **S10** : Plateau surélevé : passage piéton sur le plateau (bandes 0,50 m, 5 m de long), bordures à vue réduite au droit du plateau ; peinture épousant le relief, rampes sans marquage (aucun dans le modèle). Défauts : Aucun défaut de marquage vu ; toutes les vues ≥ 0,75.
- **S11** : Courbe R 60 m : axe T'1 qui suit la courbe, bordures continues, caniveau côté intérieur ; la bande claire côté extérieur est le dessus de la bordure (pas de rive peinte, conforme au modèle). Défauts : La route s'arrête net en fin de scène (visible en vue oblique). Dynamique dessus 0,714 et oblique 0,671 < 0,75.
- **S12** : Voie bus : inscription « BUS » lisible dans le sens de la circulation, ligne continue 5u de séparation. Défauts : Aucun défaut de marquage vu ; toutes les vues ≥ 0,75.

## 6. Écarts au plan, interprétations et règles manquantes

- **HDA pj de marquage** : pj::marquage_solide::1.0 (extrusion, chanfrein, drapé sur le sol fabriqué, UV, normales) et
  pj::gabarits_iisr::1.0 (lecture des gabarits, avec une spécification dérivée du dossier 08) sont réutilisées telles
  quelles. pj::marquage_ligne, pj::passage_pieton et pj::symbole_iisr ne le sont pas : elles ne découpent pas les
  empreintes aux lignes de rupture du sol (une ligne de 2 mm sur une couronne à 2 × 2,5 % n'est plus qu'à 0,75 mm du
  sol en son milieu ; une bande de passage de 3 mm qui enjambe l'arête haute d'une rampe à 7 % passe 1,4 mm sous le
  sol) et pj::symbole_iisr lit marquages_geometrie.json, dont RAB_D et RAB_G sont antérieurs aux corrections du
  dossier 08 (TRIANGLE_DOS_ANE et glyphes absents). Les empreintes sont faites par rg::marquages ; aucune nouvelle
  version pj:: n'a été nécessaire. Les instances pour Unreal (points + prototypes de pj::symbole_iisr) restent au lot L4.
- **Compilateur L0 modifié** (description/description_vers_modele.py, `_decorer` ; ancienne version dans
  tmp/l2b/description_vers_modele.py.avant_L2b) : une interruption d'obstacle (passage piéton, RF-MQ-PP-03) coupe aussi
  une marque de remplacement qui la chevauche (S08 : l'axe T3 du dos-d'âne traversait le passage). faire_rapport_L0
  relancé : voir rapport_L0.json.
- **Choix sans règle, déclarés [G]** (comme au lot catalogue) : phase des tirets (chaque tronçon commence par un trait,
  trait tronqué gardé s'il fait au moins la moitié d'un trait) ; dégagement de 2u bord à bord entre deux lignes qui
  convergent, la discontinue s'arrête (S09 : l'axe T'1 s'arrête à 81,075 m) ; classe d'usure de la peinture =
  ceil(3 × usure) (légère 0,2 → u1, moyenne 0,4 → u2).
- **Écarts au plan coté du catalogue** (scenes_simples/description.py), sans effet sur les « attendus » :
  T3 dessinée par le catalogue à 13/3 m de période, RF-MQ-MOD-T3 donne 4,33 m (3,00 + 1,33 ; écart cumulé 7,7 cm sur
  100 m : règle « multiples ou sous-multiples de 13 m » à préciser) ; oblique de S09 centrée sur sa limite (modèle) et
  non tangente au nez de bordure (catalogue), sa peinture s'arrête au bord du caniveau (TQ-MQG-014 : jamais sur un
  caniveau) ; 2e flèche de rabattement de S09 au milieu de la voie qui se resserre (t = 1,25, modèle) et non dans l'axe
  de la voie en section courante (t = 1,50, catalogue) : « dans l'axe de la voie supprimée » est ambigu.
- **Modèle** : sur les avancées de S03, la limite bordée porte encore la ligne T'2 du stationnement ; rg::marquages ne
  peint jamais une limite bordée (MQ-DET-010) — 14 lignes écartées, à retirer à la source dans le compilateur.
- **Contrôle renforcé par les témoins** : à leur premier passage, trois témoins n'étaient pas détectés. Deux montraient
  une faiblesse du contrôle, corrigée : la position d'une flèche venait d'un seul Kabsch sur les plus proches sommets
  (un recul de 10 cm le long du fût n'en donnait que 1,5 cm ; position désormais par le centre de surface des faces du
  dessus, rotation par ICP) ; une hachure découpée par le maillage en segments de moins de 0,30 m n'avait aucun côté
  mesurable et échappait au contrôle d'angle (enveloppe débarrassée des sommets alignés, hachure sans angle signalée).
  Le troisième était mal construit (bande de S10 déplacée de 40 cm alors que e = 58 cm : elle n'atteignait pas la
  bordure ; elle est désormais poussée de e + 10 cm).
- **« Attendus » du catalogue** : la largeur de chaussée est mesurée sur la largeur courante (celle qui couvre la plus
  grande longueur ; S03 : 8,00 sur les places, 6,00 sur les avancées) et un abaissé est un tronçon de bordure de vue
  ≤ 3 cm (DEF-031 : 2 cm ; le sommet du dos-d'âne de S08, 10 cm sous une bordure de 14 cm, laisse 4 cm et n'est pas un
  abaissé). Reste un écart sur S03 : le catalogue compte 256 m de bordures, la géométrie L2 en a 252 m. Les deux
  avancées d'extrémité (0-2,50 m et 97,50-100 m) touchent les bouts de la scène ; le catalogue compte leur côté
  transversal extérieur (2 × 2,00 m), rg::vers_entites ne le construit pas (aucune section voisine au-delà du bout).
  Convention à trancher (catalogue ou lot L2), hors du périmètre de ce lot : le critère est laissé non atteint.
- **Pointe de la dernière flèche à 1,50 m d'une ligne transversale** (DEF-017) : sans objet dans les scènes de section
  courante (aucune ligne transversale) ; contrôlé au lot L3/L4 avec les carrefours.
- **Règles manquantes ou à préciser** (à porter dans regles_route_fr.json par son propriétaire) : phase des tirets et
  traitement d'un trait tronqué ; espace minimal entre deux marques distinctes (lignes qui convergent, flèche et
  oblique) ; raccord de l'oblique d'une réduction de voies à la bordure (nez, caniveau) ; position latérale d'une flèche
  de rabattement dans une voie qui se resserre ; période de T3 (1,33 ou 13/3) ; correspondance entre l'usure dite
  (légère, moyenne) et les classes IISR.
- **Rendus** : le ciel est un modèle analytique (Preetham) avec des nuages fractals et un voile d'horizon, et non une
  HDRI CC0 (aucune sur le disque ; un téléchargement demandait l'accord de l'utilisateur) ; le ciel vu en image est
  rendu 2,2 fois plus lumineux que le ciel qui éclaire (dôme de fond sans contribution, choix de rendu déclaré) ; les
  arbres sont procéduraux (3 prototypes par gabarit, PointInstancer), décor hors de l'emprise du modèle sauf les arbres
  du modèle ; l'enrobé ancien est rendu avec l'enrobé usé de route_fr (albédo 0,17 ; celui du site, étalonné sur
  l'ortho, vaut 0,28) ; les BEV de rg::sol n'ont pas de coordonnées de texture (projection de dessus ajoutée dans la
  scène de rendu seulement, à corriger à la source dans rg::sol) ; carte de rugosité du gazon inversée au rendu
  (rapport L2). *Après la correction (§ 8) : enrobé ancien recoloré à 0,11 ; BEV avec coordonnées de texture dans
  rg::sol ; sols en MaterialX.*

## 8. Corrections après contrôle (relecture adverse de l'étape 1, 17/10/2026)

Détail et mesures avant / après : `RAPPORT_correction.md`. Pour ce lot :

- **Zébras** (rg::marquages) : une zone hachurée interrompue par une autre section (îlot bordé de même largeur, rues de
  Meylan) était jointe par-dessus l'interruption avec un indice de bande absent (polygone peint hors de la chaussée) ;
  elle est découpée en suites continues. Une zone pleine dès s = 0 était remplie d'un aplat (test `sa > 0`) : hachurée.
  S01-S12 inchangés (aucun zébra de ce genre).
- **Rendus** (rendu/rendu_l2b.py, textures_sol.py, decor_l2b.py) : soleil à 42° (faces des bordures prises pour des
  rives à 25°) ; exposition au gain 1 et courbe en S 0,50 ; sols en MaterialX (détail de la bibliothèque recoloré ×
  carte macro × bruit fractal en coordonnées du monde, aucune répétition, aucune couture entre abord et décor) :
  enrobé ancien d'albédo 0,11 gris chaud, béton balayé 0,35 à joints, enrobé de trottoir clair 0,35 (à 0,24, l'écart
  trottoir − enrobé ne valait que 0,21 contre 0,318 dans la référence), dalles 0,32 grises (et non sable), herbe à
  teinte 75-80° de saturation modérée, cartes macro (4-20 m) et méso (touffes 7-30 cm, plaques 0,2-1,2 m, bruit
  spectral isotrope, deux périodes incommensurables : aucune répétition) ; bordures au 0,80 de leur albédo ; BEV en dalles
  podotactiles jointées (UV le long de la bordure, rg::sol) ; peinture salie (blanc 0,66 / 0,58 / 0,52 selon la classe)
  et masques d'usure à granulats affleurants (plus de cellules polygonales) ; caniveau à grille au droit des
  ralentisseurs, grilles d'avaloir au pied des rampes de plateau et au bout des files de caniveau fermées par une
  avancée (S03) ; arbres aux dimensions du modèle ; prolongement de la route sur 400 m hors de
  l'emprise ; sol de décor sans triangles géants (Karma XPU ne rendait pas les triangles de plusieurs kilomètres :
  stries) ; fond de relief voilé de bleu-gris (perspective aérienne) ; saison lue dans `date` du modèle ; empreintes
  sha256 de route_l2.usda et route_l2b.usda dans manifest_rendus.json.
- **Critère ajouté** L2b-16 (lisibilité mesurée sur la vue de dessus, contrôle indépendant controler_correction.py) et
  L2b-17 (arbres) ; le seuil de L2b-11 (dynamique ≥ 0,75) est gardé tel quel (il ne mesure pas la lisibilité : la
  référence de l'utilisateur n'atteint que 0,47).
- **Revue visuelle** : toutes les tuiles natives des rendus refaits (constats_visuels_L2b.json), vues ciblées aux points
  singuliers (coude de bordure, caniveau au dos-d'âne et au plateau, fin de route, angle d'avancée).

## 7. Fichiers

- HDA : `recon/generateur/hda/rg_marquages/` (construire.py, marquages.vfl, rg_marquages.hdalc, gabarits_iisr7.py,
  gabarits_iisr7_pj.json), `recon/generateur/hda/commun/vex/rg_marquage.h`, `README_RG.md` § 6.
- Pilote : `recon/generateur/fabriquer_generateur.py` (`--l2b`), `recon/generateur/fabriquer_l2b.py`,
  `recon/generateur/rendu/{rendu_l2b,ciel,decor_l2b,textures,planches}.py`, `recon/generateur/commun/determinisme.py`.
- Contrôle : `recon/generateur/validation/{analytique_L2b,controler_L2b,faire_rapport_L2b}.py`, `rapport_L2b.json`,
  `controles_L2b.json`, `constats_visuels_L2b.json`.
- Sorties (non versionnées) : `recon/out/generateur/S01…S12/l2b/` et `rendus/`, `recon/out/generateur/catalogue_rendus/`.

