# Catalogue des besoins — librairie graphique du carrefour Paquet Jardin (état oct. 2026)

Inventaire **vérifié** des types d’objets, de matériaux et de végétaux présents dans l’emprise de 300 m, à fabriquer ou à télécharger pour la librairie `assets/lib/`. Version machine : `assets/catalogue_besoins.json` (même contenu, avec chemins complets des tuiles). Règles de nommage et d’axes : `assets/CONVENTIONS.md`.

**Méthode.** Chaque type a été vu sur au moins une tuile photo 1000×1000 native (liste en fin de document) et/ou trouvé dans une source indépendante (OSM 2026, annotations Panoramax, inventaire des arbres, levé GAM, plan projet 2025). Confiance : *haute* = vu et recoupé ; *moyenne* = une source ou lecture partielle ; *faible* = déduit. Priorité : 1 indispensable (vu depuis les voies), 2 utile, 3 optionnel.

**Chemins des tuiles.** Une tuile Panoramax nommée `<photo>_rXX_cYY.jpg` se trouve dans `data/raw/panoramax/paquet_jardin/tiles/<photo>/` (chemins absolus complets dans le JSON). Les autres chemins (tuile complémentaire, plan projet) sont donnés depuis la racine du dépôt.

**Limite principale.** Aucune photo de rue n’est postérieure aux travaux C1 au cœur du carrefour (dernières vues : 2025-08-31, en travaux). Les modèles 2026 sont supposés identiques aux modèles d’avant travaux ; les plantations 2025 viennent du plan projet.


## Signalisation verticale (panneaux, feux, supports)


### Panneau

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `panneau_B21a1` | B21a1 | Contournement obligatoire par la droite (disque bleu, flèche blanche oblique vers le bas à droite) | 4 (3-5) | disque Ø ≈ 0,45 m ; bas du disque ≈ 0,5-0,8 m au-dessus de l’îlot | haute | 1 |
| `panneau_C113` | C113 | Piste ou bande cyclable conseillée et réservée aux cycles (carré bleu, vélo blanc) | 2 (1-3) | carré ≈ 0,5 m vu en biais, bas ≈ 2,0-2,3 m sur accotement enherbé | haute | 1 |
| `panneau_C114` | C114 | Fin de piste ou bande cyclable conseillée (carré bleu, vélo barré rouge) | 1 | carré ≈ 0,45-0,5 m, haut du mât ≈ 3 m | haute | 1 |
| `panneau_AB3a` | AB3a | Cédez le passage à l’intersection (triangle pointe en bas) | 4 (3-5) | triangle ≈ 0,6-0,7 m de côté, bas ≈ 1,9-2,2 m | haute | 1 |
| `panneau_AB4` | AB4 | STOP (octogone rouge) | 1 | octogone ≈ 0,6 m, bas ≈ 1,8-2,0 m (vu à ≈ 25 m) | haute (présence) / faible (implantation exacte) | 1 |
| `panneau_B1` | B1 | Sens interdit | 2 (2-3) | disque ≈ 0,6 m, bas ≈ 2,0-2,2 m | haute | 1 |
| `panneau_B2b` | B2b | Interdiction de tourner à droite à la prochaine intersection | 1 | disque ≈ 0,6 m, haut du mât ≈ 3,2 m | haute | 1 |
| `panneau_B2a` | B2a | Interdiction de tourner à gauche à la prochaine intersection | 1 | disque ≈ 0,6 m | haute | 1 |
| `panneau_B6a1` | B6a1 | Stationnement interdit | 4 (3-5) | disque ≈ 0,43 m (rapport au fût du candélabre) | haute | 1 |
| `panneau_C13a` | C13a | Impasse (rectangle bleu, T blanc à barre rouge) | 1 | ≈ 0,25 × 0,40 m sous le B6a1 du candélabre n° 0456 | haute | 2 |
| `panneau_A17` | A17 | Annonce de feux tricolores (triangle de danger, fond blanc) | 1 | triangle ≈ 0,7 m (≈ 4 fois le diamètre du fût), bas ≈ 2,3 m | haute (permanent, pas AK17) | 2 |

- **`panneau_B21a1`** — gamme : miniature (Ø 450 mm) — mesuré ≈ 0,42-0,45 m sur 119d r01_c00 ; support : mât rond acier galvanisé Ø 60 mm, court (≈ 1,0-1,3 m hors sol), scellé dans l’îlot ; 2 colliers ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : bleu (arrêté de 1967, RAL 5017 env.), flèche et liseré blancs rétroréfléchissants classe 1 ; référence : IISR art. 5 : disques miniature 450 / petite 650 / normale 850 mm ; quantité : 3 vus en 2025 (nez du TPC NE, petit îlot rond SO, îlot au droit de 734a) ; le nouveau TPC planté SO (2025) en porte probablement un ; source de fabrication : maison (SVG Wikimedia Commons, domaine public) (lot signalisation).  
  Tuiles : `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`, `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c02.jpg`, `2023-03-18_e2574612-b380-4cb2-918e-d5506aff8145_hd_r01_c01.jpg`

- **`panneau_C113`** — gamme : petite (carré 500 mm) probable ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : bleu, pictogramme blanc ; quantité : côté Revirée (angle NO) ; 9 annotations Panoramax d’un même petit groupe de panneaux ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`

- **`panneau_C114`** — gamme : petite (500 mm) ou miniature (350 mm) — rapport au triangle AB3a voisin ≈ 0,85 ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; 3 panneaux superposés (C114 / AB3a / panonceau) ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : bleu, vélo blanc, barre rouge ; quantité : débouché du chemin du Ruisseau sur la Revirée, au-dessus d’un AB3a et d’un panonceau ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-08-31_10ec04d5-3da4-4e39-aa0f-828450425ad1_hd_r01_c03.jpg`

- **`panneau_AB3a`** — gamme : petite (côté 700 mm) le plus souvent ; miniature (500 mm) possible sur le mât de la Revirée ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond blanc, bordure rouge ; référence : IISR : triangles miniature 500 / petite 700 / normale 1000 mm ; quantité : chemin du Ruisseau (avec C114) ; contre-allée NE (avec B2a) ; jonction allée de L’Horloge / traversée cyclable Vercors (2026) ; panonceau triangulaire sous un feu du Vercors (AB3a ou M12, 2025-01) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-08-31_10ec04d5-3da4-4e39-aa0f-828450425ad1_hd_r01_c03.jpg`, `2025-08-31_9ef861d4-0b2e-403d-b1ee-2d8e038c6cad_hd_r01_c03.jpg`, `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`

- **`panneau_AB4`** — gamme : petite (650 mm) probable ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : rouge, inscription STOP blanche ; quantité : sortie de l’allée de L’Horloge sur l’avenue du Vercors (≈ 130-136 m au sud) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`

- **`panneau_B1`** — gamme : petite (Ø 650 mm) ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : rouge, barre blanche ; quantité : mât de la contre-allée/accès NE (avec B2b) ; sortie du parking de L’Horloge (2026) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r01_c02.jpg`, `2025-05-18_9fc8ba46-9a08-483b-92f7-ad37798f9330_hd_r01_c03.jpg`, `2026-07-28_ffc2e8ac-50a1-422d-8a27-6514243a81e5_hd_r01_c00.jpg`

- **`panneau_B2b`** — gamme : petite (Ø 650 mm) ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond blanc, bordure et barre rouges, flèche noire ; quantité : au-dessus du B1 de l’accès NE (permanent, fond blanc) ; source de fabrication : maison (lot signalisation) ; note : Une variante TEMPORAIRE sur fond carré jaune (chantier 2025-08, fermeture du tourne-à-droite vers le P+R) est listée dans la catégorie chantier.  
  Tuiles : `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r00_c02.jpg`, `2025-05-18_9fc8ba46-9a08-483b-92f7-ad37798f9330_hd_r01_c03.jpg`

- **`panneau_B2a`** — gamme : petite (Ø 650 mm) ; support : mât rond acier galvanisé Ø 60 mm (Ø 76 mm si 3 panneaux), 2,8-3,5 m hors sol, platine ou scellement ; colliers à brides ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond blanc, bordure et barre rouges, flèche noire ; quantité : deuxième mât de l’accès NE, au-dessus d’un AB3a + panonceau ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-08-31_9ef861d4-0b2e-403d-b1ee-2d8e038c6cad_hd_r00_c03.jpg`, `2025-08-31_b536a4a0-72c8-4d78-ac7d-fe7d65b98d91_hd_r01_c02.jpg`

- **`panneau_B6a1`** — gamme : miniature (Ø 450 mm) sur candélabre ; support : colliers sur candélabre ou mât Ø 60 mm ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : bleu, bordure et barre rouges ; quantité : candélabre n° 0456 (Vercors sud) ; parking de L’Horloge (avec panonceau privé) ; portail P+R (2020) ; B6 avec panonceau vert côté est du Vercors (2025-01) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c04.jpg`, `2026-07-28_ded07efa-75ec-4289-972a-56c9e98a1309_hd_r01_c02.jpg`, `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c01.jpg`

- **`panneau_C13a`** — gamme : miniature ; support : colliers sur candélabre ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : bleu, blanc, rouge ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c04.jpg`

- **`panneau_A17`** — gamme : petite (700 mm) probable ; support : colliers sur candélabre gris-bleu Ø ≈ 0,17 m ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond blanc, bordure rouge, feux rouge/jaune/vert ; quantité : approche NE de Verdun (sens Montbonnot → Grenoble), fixé sur un candélabre à ≈ 150 m du centre (bord de l’emprise) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `data/raw/panoramax/complements/tiles/2025-08-31_f6297e9f-f229-45c1-bc88-c902fa605716_hd_x2100_y500.jpg`


### Balise

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `panneau_J5` | J5 | Balise de tête d’îlot (plaque bleue rectangulaire, flèche blanche oblique) | 2 (2-3) | plaque ≈ 0,5 m de large, bas à ≈ 0,3-0,5 m de l’îlot, légèrement inclinée sur fdc59178 | moyenne | 1 |

- **`panneau_J5`** — gamme : modèle courant (≈ 0,50 × 0,45 m observé ; dimensions IISR J5 à confirmer par le lot signalisation) ; support : mât rond acier galvanisé Ø 60 mm, court (≈ 1,0-1,3 m hors sol), scellé dans l’îlot ; 2 colliers ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond bleu, flèche blanche rétroréfléchissante ; quantité : musoir de l’îlot Revirée (2025-08) et îlot côté P+R (734a 2025-05) ; Panoramax FR:J5 ×3 ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-08-31_fdc59178-d148-43e0-a307-4742929b45a2_hd_r01_c00.jpg`, `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c00.jpg`


### Panonceau

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `panneau_M9c` | M9c (code à confirmer) | Panonceau à inscription « CÉDEZ LE PASSAGE » sous AB3a | 2 | ≈ 0,45 × 0,20 m, lettres bleu foncé/noires sur fond blanc, coins arrondis | moyenne (présence haute, code M9c probable) | 1 |
| `panneau_M12a` | M12a (probable) | Cédez-le-passage cycliste au feu rouge, tourne-à-droite (petit triangle sous la tête de feu) | 1 (0-2) | petit triangle sous la tête R11v, ≈ 0,3 m | faible | 2 |

- **`panneau_M9c`** — gamme : petite ; support : sur le mât de l’AB3a, colliers ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond blanc, texte foncé ; quantité : sous les AB3a du chemin du Ruisseau et de la contre-allée NE ; source de fabrication : maison (texte vectoriel) (lot signalisation).  
  Tuiles : `2025-08-31_10ec04d5-3da4-4e39-aa0f-828450425ad1_hd_r01_c03.jpg`, `2025-08-31_9ef861d4-0b2e-403d-b1ee-2d8e038c6cad_hd_r01_c03.jpg`

- **`panneau_M12a`** — gamme : panonceau M12 (triangle ≈ 0,25-0,30 m) ; support : colliers sur le mât de feu ; recto/verso : dos gris (aluminium/acier galvanisé brut) avec 2 colliers et rail de fixation ; marquage propriétaire possible ; couleurs : fond blanc, bordure rouge, vélo et flèche jaunes/noirs (IISR) ; quantité : OSM red_turn:right:bicycle=yes (Revirée, relevé 2022) ; panonceau triangulaire sous un feu vu en 2025-01 (AB3a ou M12) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`


### Direction

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `panneau_D21a_la_reviree_college` | D21a (famille D21) | Panneau de direction en flèche, fond blanc : « LA REVIRÉE / Collège L. Terray » (flèche à droite) | 1 | ≈ 1,1 × 0,35 m ; bas ≈ 2,2 m ; flèche vers la droite | haute | 1 |
| `panneau_D21a_commerces_reviree` | D21a (famille D21) | Panneau de direction en flèche : « Commerces de LA REVIRÉE » | 1 | ≈ 1,1 × 0,22 m sous le précédent | haute | 1 |

- **`panneau_D21a_la_reviree_college`** — gamme : composition locale (2 lignes) ; support : un seul mât rond galvanisé Ø 60-76 mm sur le refuge de la Revirée, portant les 2 panneaux D21 ; recto/verso : dos gris, rails et colliers ; couleurs : fond blanc, liseré et texte noirs (police L1/L4 de l’IISR) ; source de fabrication : maison (texte vectoriel) (lot signalisation).  
  Tuiles : `2024-05-01_1149e115-2c88-48fc-a908-bbf633abaa72_hd_r01_c02.jpg`, `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c03.jpg`, `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`

- **`panneau_D21a_commerces_reviree`** — gamme : composition locale (1 ligne) ; support : même mât que panneau_D21a_la_reviree_college ; recto/verso : dos gris ; couleurs : fond blanc, texte noir ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2024-05-01_1149e115-2c88-48fc-a908-bbf633abaa72_hd_r01_c02.jpg`, `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`


### Plaque de rue

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `plaque_rue_avenue_de_verdun` | plaque de rue | « AVENUE DE VERDUN », lettres blanches sur fond bleu, coins arrondis | 1 (1-2) | ≈ 0,55 × 0,25 m, à ≈ 2,8 m sur un mât de feux (n° 3150) | haute | 3 |

- **`plaque_rue_avenue_de_verdun`** — support : colliers sur mât de feux ; recto/verso : dos gris ; couleurs : bleu RAL 5003 env., blanc ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`


### Support

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `mat_panneau_d60` | support | Mât rond galvanisé Ø 60 mm, bouchon, 3,0 / 3,5 m (variantes de longueur par échelle Z) | 12 (10-16) | Ø 60-76 mm ; gris galvanisé clair ; scellé dans trottoir/accotement | haute | 1 |
| `mat_panneau_ilot_court` | support | Mât court Ø 60 mm (1,0-1,3 m) pour B21a1 / J5 sur îlot | 6 (5-8) | Ø 60 mm, 1,0-1,3 m hors sol | haute | 1 |
| `mat_feu_d114` | support | Mât de feux rond Ø ≈ 114 mm, 3,5 m, gris galvanisé ; variante anthracite ; fourreau jaune de pied en option | 16 (14-20) | Ø 100-114 mm ; 3,0-4,0 m ; fourreau jaune ≈ 0,4 m vers 0,5-0,9 m ; numéro d’inventaire peint (ex. 3150) | haute | 1 |
| `mat_feu_crosse_camera` | support | Mât anthracite à crosse « col de cygne » portant une caméra dôme de vidéoprotection et une tête R11v | 1 (1-2) | ≈ 5,5-6 m, crosse ≈ 0,4 m, dôme Ø ≈ 0,2 m ; tête R11v à ≈ 3 m | haute | 2 |

- **`mat_panneau_d60`** — support : — ; couleurs : acier galvanisé ; référence : hauteur sous panneau 2,30 m en agglomération sur trottoir (IISR) ; observé 1,9-2,3 m ; quantité : un par groupe de panneaux listés ci-dessus ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r01_c02.jpg`, `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`

- **`mat_panneau_ilot_court`** — couleurs : galvanisé ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`, `2025-08-31_fdc59178-d148-43e0-a307-4742929b45a2_hd_r01_c00.jpg`

- **`mat_feu_d114`** — support : — ; couleurs : galvanisé clair / gris anthracite RAL 7016 env. / jaune (fourreau) ; quantité : ≥ 14 supports sur l’ortho 2022 (coeur-40) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`, `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`, `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c02.jpg`

- **`mat_feu_crosse_camera`** — support : — ; couleurs : gris anthracite, dôme blanc/fumé ; quantité : îlot refuge SO ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`, `2023-03-18_a275b2ea-ca5a-4224-b4ad-f335ddbfe981_hd_r00_c01.jpg`


### Feu

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `feu_R11v` | R11v | Signal tricolore circulaire véhicules (3 feux, rouge en haut) | 14 (10-18) | feux Ø 200 mm (urbain) ; corps ≈ 0,30 × 0,95 m avec visières ; tête basse à ≈ 2,5-3,5 m ; montage latéral sur bras court ou en tête de mât ; plusieurs têtes par mât (dos à dos) | haute | 1 |
| `feu_R11v_repetiteur` | R11v (répétiteur) | Petit répétiteur tricolore à hauteur d’yeux, sous la tête principale | 5 (4-8) | feux Ø ≈ 100 mm, corps noir ≈ 0,15 × 0,45 m, bas à ≈ 1,8-2,2 m | haute | 1 |
| `feu_R12` | R12 | Signal piétons (bonhomme rouge / vert), 2 feux | 14 (12-16) | pictogrammes Ø 200 mm ; boîtier vertical noir ≈ 0,30 × 0,70 m à ≈ 2,3-2,8 m ; une variante en boîtier HORIZONTAL à 2 pictogrammes côte à côte observée (angle Revirée) | haute | 1 |
| `feu_R12_horizontal` | R12 (variante) | Boîtier horizontal à 2 pictogrammes piétons | 1 (1-2) | ≈ 0,55 × 0,30 m, noir, sur bras latéral à ≈ 2,5 m | moyenne | 2 |
| `feu_R13c` | R13c | Signal cycles (pictogramme vélo) — NON confirmé | 0 (0-4) | — | faible | 3 |

- **`feu_R11v`** — support : mât rond Ø 100-114 mm, 3,0-4,0 m ; gris galvanisé clair ou gris anthracite (gris-bleu foncé en 2020) ; certains avec fourreau jaune de repérage en pied ; recto/verso : face noire mat avec 3 visières noires ; DOS GRIS CLAIR (corps polycarbonate) très visible sur les photos ; pas de plaque de contraste observée ; couleurs : noir (face), gris clair RAL 7035 env. (dos), lentilles rouge/jaune/vert ; référence : NF EN 12368 / arrêté du 24 nov. 1967 (R11v) ; quantité : 4 approches × 2 têtes principales (accotement + TPC/refuge) + têtes « de sortie » protégeant les traversées (≥ 2 vues de dos sur les refuges SO et NE) ; ≥ 14 supports de feux identifiés sur l’ortho 2022 (coeur-40), 14 nœuds OSM ; source de fabrication : maison (CARLA : feux US à éviter) (lot signalisation) ; note : Prévoir 3 états d’allumage (rouge/orange/vert) par matériau émissif commutable ; potence au-dessus de la chaussée NON observée.  
  Tuiles : `2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433_hd_r01_c02.jpg`, `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`

- **`feu_R11v_repetiteur`** — support : même mât ; recto/verso : corps noir ; couleurs : noir ; quantité : au moins 1 par approche (vu à l’angle Revirée et à l’approche NE) ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`

- **`feu_R12`** — support : mât de feux commun ou mât piéton Ø 90-114 mm ; recto/verso : noir / dos gris ; couleurs : noir ; pictogrammes rouge et vert ; quantité : 4 traversées à feux (Verdun SO et NE et Vercors en deux temps, Revirée) × 2 extrémités × demi-traversées ; OSM : 10 nœuds crossing=traffic_signals ; source de fabrication : maison (lot signalisation) ; note : Prévoir la variante horizontale (feu_R12_horizontal) en option ; pas de répétiteur sonore (OSM traffic_signals:sound=no).  
  Tuiles : `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`, `2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d_hd_r01_c03.jpg`, `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`

- **`feu_R12_horizontal`** — support : mât de feux ; recto/verso : noir ; couleurs : noir ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`

- **`feu_R13c`** — support : mât de feux ; recto/verso : — ; couleurs : noir ; quantité : deuxième tête masquée sur le mât ouest de la traversée Revirée en 2024 (cycle ou répétiteur) ; traversée Chronovélo à feux probable mais aucun feu vélo lisible ; état 2026 : possible ; source de fabrication : maison (lot signalisation) ; note : À fabriquer seulement en variante (même corps que feu_R11v, pictogrammes vélo). R14/R15 (bus) : non observés, ne pas fabriquer.  
  Tuiles : `2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d_hd_r01_c03.jpg`


### Équipement de feux

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `boitier_bouton_appel` | — | Boîtier noir de bouton d’appel piéton / répétiteur, sur le mât à ≈ 1,1-1,3 m | 4 (3-8) | ≈ 0,12 × 0,10 × 0,25 m, noir | moyenne | 2 |

- **`boitier_bouton_appel`** — support : collier sur mât ; recto/verso : — ; couleurs : noir ; quantité : OSM button_operated=yes sur 3 traversées ; boîtiers vus sur plusieurs mâts ; source de fabrication : maison (lot signalisation).  
  Tuiles : `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`, `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c02.jpg`


### Chantier (temporaire)

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `panneau_B2b_temporaire` | B2b | B2b sur fond carré jaune (signalisation temporaire 2025-08) | 0 | voir photos | haute (observé 2020-2025) | 3 |
| `panneau_AK5` | AK5 | AK5 Travaux (triangle fond jaune) sur chevalet | 0 | voir photos | haute (observé 2020-2025) | 3 |
| `balise_chevrons_chantier` | — | Panneau à chevrons rouges/blancs de déport sur pied | 0 | voir photos | haute (observé 2020-2025) | 3 |
| `mat_feu_provisoire` | — | Mât de feu provisoire lesté de parpaings | 0 | voir photos | haute (observé 2020-2025) | 3 |

- **`panneau_B2b_temporaire`** — quantité : aucun en 2026 ; état 2026 : absent (travaux terminés jan. 2026) — scénarios travaux uniquement ; source de fabrication : maison / CARLA (cônes, barrières : proches) (lot signalisation).  
  Tuiles : `2025-08-31_1d999186-824b-4ec7-8b52-0402511307a3_hd_r01_c00.jpg`, `2025-08-31_81882270-2b91-457a-a7c9-4f955319ea22_hd_r01_c00.jpg`

- **`panneau_AK5`** — quantité : aucun en 2026 ; état 2026 : absent (travaux terminés jan. 2026) — scénarios travaux uniquement ; source de fabrication : maison / CARLA (cônes, barrières : proches) (lot signalisation).  
  Tuiles : `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c01.jpg`

- **`balise_chevrons_chantier`** — quantité : aucun en 2026 ; état 2026 : absent (travaux terminés jan. 2026) — scénarios travaux uniquement ; source de fabrication : maison / CARLA (cônes, barrières : proches) (lot signalisation).  
  Tuiles : `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`

- **`mat_feu_provisoire`** — quantité : aucun en 2026 ; état 2026 : absent (travaux terminés jan. 2026) — scénarios travaux uniquement ; source de fabrication : maison / CARLA (cônes, barrières : proches) (lot signalisation).  
  Tuiles : `2025-08-31_1d999186-824b-4ec7-8b52-0402511307a3_hd_r01_c00.jpg`


## Transport


### Signalétique

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `totem_pr_smmag` | totem SMMAG | Totem « P+R PARKING RELAIS → / M » (réseau M, SMMAG) | 1 | ≈ 0,9 m × 0,2 m × 3,6 m ; fond noir, bandeau « P+R » bleu en tête, arc bleu/jaune/vert/violet, « M » blanc, logo SMMAG ; platine boulonnée sur dalle | haute | 2 |

- **`totem_pr_smmag`** — support : platine acier sur massif ; recto/verso : double face probable ; couleurs : noir, blanc, bleu, jaune, vert ; quantité : îlot entre piste et chaussée SO (2025) ; entrée du P+R déplacée par les travaux 2025 → position 2026 à confirmer ; source de fabrication : maison (texture depuis la photo) (lot mobilier).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c03.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`, `2024-05-01_1149e115-2c88-48fc-a908-bbf633abaa72_hd_r01_c02.jpg`


### Abri voyageurs

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `abri_bus_m_reso` | — | Abri voyageurs du réseau M : ossature métallique anthracite, parois vitrées, toit plat débordant, banc, MUPI publicitaire en bout, plan/horaires, écran d’information | 2 (2-3) | ≈ 4,0 × 1,5 × 2,5 m ; MUPI ≈ 1,2 × 1,75 m ; quai haut ≈ +0,16-0,18 m | haute (présence) / moyenne (modèle 2026 identique) | 1 |

- **`abri_bus_m_reso`** — support : platines sur quai ; couleurs : gris anthracite, verre, toit gris clair ; quantité : un abri par sens sur Verdun SO (quais déplacés et mutualisés en 2025 : abri figuré sur le plan projet aux 2 quais) ; quai Revirée (Flexo 42) sans abri ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`, `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c01.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`


### Poteau d’arrêt

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `poteau_arret_m_reso` | — | Poteau d’arrêt M réso : mât anthracite ≈ 3 m, drapeau rond « M », plaque « La Revirée », plaques de lignes (C1, …) | 3 (2-3) | drapeau Ø ≈ 0,35 m ; plaque nom ≈ 0,6 × 0,15 m ; plaques de lignes ≈ 0,5 × 0,2 m | haute | 1 |

- **`poteau_arret_m_reso`** — support : platine ; couleurs : anthracite, blanc, jaune (C1) ; quantité : 1 intégré à chaque abri + 1 poteau seul (OSM public_transport=pole, quai Revirée) ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`


## Mobilier urbain et équipements


### Équipement technique

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `armoire_commande_feux` | — | Armoire métallique grise de contrôleur de feux (souvent taguée) | 1 (1-2) | ≈ 0,8 × 0,4 × 1,4 m | haute | 2 |
| `armoire_technique` | — | Armoire technique beige (réseaux) | 2 (1-3) | ≈ 0,7 × 0,3 × 1,2 m | haute | 3 |

- **`armoire_commande_feux`** — support : socle béton ; couleurs : gris clair RAL 7035 env., tags ; source de fabrication : maison (ou CARLA « traffic light box », adéquation proche) (lot mobilier).  
  Tuiles : `2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433_hd_r01_c02.jpg`, `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`

- **`armoire_technique`** — support : socle ; couleurs : beige ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c01.jpg`


### Barrière

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `barriere_croix_saint_andre` | — | Barrière de ville à croisillons (croix de Saint-André), tube gris | 15 (10-20) | module ≈ 1,5-2,0 m × 1,0 m, tubes Ø ≈ 40-50 mm | haute | 1 |
| `barriere_levante` | — | Barrière levante de parking (fût bleu, lisse blanche) | 1 (1-2) | fût ≈ 0,3 × 0,3 × 1,0 m ; lisse ≈ 4 m à 0,9 m | haute | 3 |

- **`barriere_croix_saint_andre`** — support : scellement ; couleurs : gris anthracite ; quantité : ≈ 9 éléments sur ≈ 12 m sur l’îlot séparateur du couloir bus (2022) + ≥ 6 le long du quai SO ; à reconfirmer après les travaux ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c01.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`

- **`barriere_levante`** — support : platine ; couleurs : bleu, blanc ; quantité : parking de L’Horloge ; OSM lift_gate ×2 ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2026-07-28_ffc2e8ac-50a1-422d-8a27-6514243a81e5_hd_r01_c00.jpg`


### Potelet

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `potelet_noir` | — | Potelet anti-stationnement noir/anthracite à tête blanche réfléchissante | 8 (5-12) | Ø ≈ 90-100 mm, 0,8-1,1 m | moyenne | 1 |

- **`potelet_noir`** — support : scellé ; couleurs : noir, bande blanche ; quantité : Revirée (3 aux extrémités du passage, 2 balises du fuseau), surface centrale sud, OSM bollard ×3 ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`, `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`


### Banc

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `banc_bois_metal` | — | Banc à lattes de bois, piétement métal | 2 (2-3) | ≈ 1,8 × 0,6 × 0,8 m | haute | 2 |

- **`banc_bois_metal`** — support : posé/scellé ; couleurs : bois brun, métal gris ; source de fabrication : CC0 (Poly Haven) ou maison (lot mobilier).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`, `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c01.jpg`


### Corbeille

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `corbeille_cylindrique` | — | Corbeille cylindrique à lames métalliques grises, couvercle jaune | 2 (2-3) | Ø ≈ 0,4 m, h ≈ 0,9 m | haute | 2 |

- **`corbeille_cylindrique`** — support : scellée ; couleurs : gris acier, jaune ; quantité : photo 2025-05 + plan projet (« Corbeille » aux 2 quais) ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`


### Stationnement vélo

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `arceau_velo` | — | Arceau vélo en U renversé, tube gris | 6 (5-8) | ≈ 0,8 × 0,8 m, tube Ø 50-60 mm | haute | 2 |

- **`arceau_velo`** — support : scellé ; couleurs : gris galvanisé / anthracite ; quantité : 5-6 arceaux près du quai SO (photo 2025, plan projet « Stationnement vélos ») ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`


### Réseau

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `poteau_incendie` | — | Poteau d’incendie rouge | 1 (1-2) | ≈ Ø 0,2 × 0,9 m | haute | 3 |

- **`poteau_incendie`** — support : — ; couleurs : rouge RAL 3000 ; source de fabrication : CARLA (« fire hydrant » US : à éviter) → maison (lot mobilier).  
  Tuiles : `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c01.jpg`


### Protection de plantation

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `ganivelle_bois` | — | Ganivelle en lattes de châtaignier (protection des jeunes plantations 2025) | 40 (20-80) | h ≈ 1,0-1,2 m | moyenne | 3 |

- **`ganivelle_bois`** — support : piquets bois ; couleurs : bois gris-brun ; quantité : mètres linéaires, rive est du Vercors (2026) ; état 2026 : present (temporaire) ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`


### Clôture

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `cloture_grillage_rigide` | — | Clôture en panneaux de grillage rigide (limites de propriétés) | 900 (600-950) | h ≈ 1,2-2,0 m | moyenne | 3 |

- **`cloture_grillage_rigide`** — support : poteaux ; couleurs : vert RAL 6005 ou gris ; quantité : mètres ; GAM SOL_CLOTURES ≈ 913 m dans l’emprise ; OSM fence metal ; source de fabrication : CARLA/CC0 (proche) (lot mobilier).  
  Tuiles : — (source non photographique : GAM; OSM)


### Chantier (temporaire)

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `separateur_modulaire_K16` | — | Séparateurs modulaires de voie plastique rouges/blancs lestés (K16) | 0 | voir photos | haute (observé 2020-2025) | 3 |
| `barriere_chantier_rouge_blanc` | — | Barrière de chantier métallique rouge/blanc et clôture mobile | 0 | voir photos | haute (observé 2020-2025) | 3 |

- **`separateur_modulaire_K16`** — quantité : aucun en 2026 ; état 2026 : absent (travaux terminés jan. 2026) — scénarios travaux uniquement ; source de fabrication : maison / CARLA (cônes, barrières : proches) (lot mobilier).  
  Tuiles : `2025-08-31_a83dae90-c92a-472e-8d22-2e8863c47968_hd_r01_c01.jpg`, `2025-08-31_1d999186-824b-4ec7-8b52-0402511307a3_hd_r01_c00.jpg`

- **`barriere_chantier_rouge_blanc`** — quantité : aucun en 2026 ; état 2026 : absent (travaux terminés jan. 2026) — scénarios travaux uniquement ; source de fabrication : maison / CARLA (cônes, barrières : proches) (lot mobilier).  
  Tuiles : `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`, `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c01.jpg`


## Éclairage et réseaux aériens


### Candélabre

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `candelabre_double_crosse` | — | Candélabre de l’avenue de Verdun : mât cylindro-conique ≈ 10-12 m, double crosse en T (bras opposés), 2 lanternes plates | 12 (10-14) | hauteur de feu ≈ 10-11 m (ombre 7,9 m, soleil ≈ 55-60°) ; bras ≈ 1,5-2 m ; lanterne plate ≈ 0,8 × 0,35 m ; décors de Noël fixés sur certains mâts | haute | 1 |
| `candelabre_crosse_simple` | — | Candélabre à crosse simple (bras ≈ 1,5 m), lanterne plate, ≈ 8-10 m | 4 (2-6) | ≈ 8-10 m, bras incliné ≈ 1,5 m | moyenne | 1 |
| `candelabre_mat_droit_led` | — | Mât droit ≈ 6-8 m, lanterne LED plate en tête (légèrement inclinée), plaque de numéro (ex. « 0456 ») | 20 (16-22) | fût Ø ≈ 0,15 m en pied, 6-8 m ; lanterne ≈ 0,6 × 0,3 m ; supports de B6a1/C13a sur certains | haute | 1 |
| `candelabre_mat_droit_shp` | — | Variante Revirée : mât droit ≈ 8 m, lanterne sodium haute pression (SHP) | 3 (3-4) | ≈ 8 m | faible (modèle de lanterne non vu de près) | 3 |

- **`candelabre_double_crosse`** — support : massif béton, platine ; couleurs : gris galvanisé / gris-bleu ; lanterne gris clair ; quantité : OSM lamp_mount=bent_mast ×13 le long de Verdun (réf. 2341-2358, pas ≈ 29 m), certains à crosse simple ; source de fabrication : maison (CARLA : lampadaires proches en silhouette) (lot mobilier).  
  Tuiles : `2024-05-01_1149e115-2c88-48fc-a908-bbf633abaa72_hd_r01_c02.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`, `2023-03-18_a275b2ea-ca5a-4224-b4ad-f335ddbfe981_hd_r00_c01.jpg`

- **`candelabre_crosse_simple`** — support : massif ; couleurs : gris galvanisé ; quantité : Verdun côté SE et Vercors (OSM bent_mast réf. 3153 ; 2025-06 nouveaux mâts près du P+R) ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c03.jpg`, `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c03.jpg`, `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`

- **`candelabre_mat_droit_led`** — support : massif ; couleurs : gris galvanisé clair, numéro bleu ; quantité : OSM straight_mast ×19 + 3 inconnus (Vercors, allées, P+R, cheminements, Revirée) ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`, `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c04.jpg`, `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c01.jpg`

- **`candelabre_mat_droit_shp`** — support : massif ; couleurs : gris ; quantité : OSM lamp_type=high_pressure_sodium ×3 (Revirée) ; LiDAR 7,9-8,2 m ; source de fabrication : variante de candelabre_mat_droit_led (lumière orangée 2000 K) (lot mobilier).  
  Tuiles : — (source non photographique : OSM; analyse reviree_no-28)


### Réseau aérien

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `poteau_bois_reseau` | — | Poteau bois (réseau aérien télécom/électrique), brun, ≈ 9-11 m, avec câbles | 5 (3-8) | Ø ≈ 0,2-0,25 m, 9-11 m, affiches et étiquettes | haute | 2 |
| `mat_illumination_cable` | — | Mât métallique brun avec bras porte-câbles (guirlandes et câbles aériens transversaux) | 2 (1-4) | ≈ 9-10 m, bras horizontal ≈ 4-5 m | moyenne | 3 |

- **`poteau_bois_reseau`** — support : enterré ; couleurs : bois brun-orangé ; quantité : angle Revirée, branche NE, Vercors ; câbles aériens au-dessus des voies (ombres linéaires) ; source de fabrication : maison (CARLA : poteaux électriques, adéquation proche) (lot mobilier).  
  Tuiles : `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c03.jpg`, `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`, `2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d_hd_r01_c03.jpg`

- **`mat_illumination_cable`** — support : massif ; couleurs : brun-orangé ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`, `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c01.jpg`


## Bordures, caniveaux, abaissés, BEV


### Bordure de trottoir

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bordure_T2` | T2 | Bordure de trottoir béton T2 (profil à chanfrein), gris clair | 4500 (3500-5500) | vue 14-17 cm (îlots +0,17-0,21 m, quai +0,16 m au LiDAR) ; tête ≈ 15 cm | haute | 1 |

- **`bordure_T2`** — support : — ; couleurs : béton gris clair, épaufrures, mousses ; référence : NF EN 1340 + NF P98-340/CN (T2 : 15 × 25 cm, à confirmer par le lot) ; quantité : m ; GAM SOL_BORDURE 6,85 km de traits dans l’emprise (deux arêtes par bordure souvent) ; libellé « T2 » dans le levé GAM ; source de fabrication : maison (profil extrudé) (lot mobilier).  
  Tuiles : `2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433_hd_r01_c02.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`


### Bordure de refuge

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bordure_T2_peinte_blanc` | T2 peinte | Bordure T2 de refuge en D peinte en blanc (refuges SO) | 30 (20-50) | refuges ≈ 2,7 × 2,5 m, vue ≈ 15 cm | haute | 1 |

- **`bordure_T2_peinte_blanc`** — couleurs : blanc sur béton (peinture usée) ; quantité : m ; source de fabrication : variante matériau (lot mobilier).  
  Tuiles : `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c01.jpg`


### Bordure de quai

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bordure_quai_bus` | bordure de quai haute | Bordure de quai bus accessible (face inclinée), bande claire en tête | 60 (40-80) | vue ≈ 16-18 cm (2021) ; quais 2025 probablement 18-21 cm | moyenne | 1 |

- **`bordure_quai_bus`** — couleurs : béton clair ; quantité : m (2 quais) ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`


### Bordure franchissable

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bordure_A2` | A2 | Bordure arrondie franchissable (piste cyclable / accotements / nez d’îlots) | 800 (400-1200) | vue ≈ 5-10 cm, profil arrondi | moyenne (type exact) | 1 |

- **`bordure_A2`** — couleurs : béton gris ; quantité : m ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`, `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c00.jpg`


### Bordure de jardin

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bordure_P1` | P1 | Bordure de jardin béton (espaces verts, faible vue) | 600 (300-900) | vue 0-5 cm, largeur ≈ 5-8 cm | moyenne | 1 |

- **`bordure_P1`** — couleurs : béton gris ; quantité : m ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`, `2026-07-28_ded07efa-75ec-4289-972a-56c9e98a1309_hd_r01_c02.jpg`


### Caniveau

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `caniveau_cs` | CS1/CS2 | Caniveau béton à joints transversaux (fil d’eau) ; variante caniveau à fente le long du quai SE | 140 (100-300) | largeur 25-50 cm | moyenne | 1 |

- **`caniveau_cs`** — couleurs : béton gris ; quantité : m ; GAM SOL_CANIVEAU 139 m ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c03.jpg`


### Bordure d’îlot

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bordure_paves_granit` | — | Anneau de pavés de granit clairs sertis autour des petits îlots ronds (porte-B21a1) | 2 (1-3) | pavés ≈ 0,10-0,15 m, îlot Ø ≈ 2 m | moyenne | 2 |

- **`bordure_paves_granit`** — couleurs : granit gris clair ; quantité : îlots ; source de fabrication : maison + CC0 (lot mobilier).  
  Tuiles : `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`, `2023-03-18_e2574612-b380-4cb2-918e-d5506aff8145_hd_r01_c01.jpg`


### Abaissé

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `abaisse_chartiere` | bateau / chartières | Abaissé de trottoir aux traversées (bordure abaissée vue 0-2 cm + chartières droite/gauche) | 21 (16-30) | vue 0-2 cm, rampants ≈ 1 m | haute | 1 |

- **`abaisse_chartiere`** — couleurs : béton ; quantité : GAM blocs CHARTIERE_GAUCHE ×11 / DROITE ×10 ; source de fabrication : maison (lot mobilier).  
  Tuiles : `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`, `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`


### Bande d’éveil de vigilance

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `bev_podotactile` | BEV (NF P98-351) | Dalles podotactiles à plots (40 × 40 cm), gris clair ou blanches, en tête des traversées | 18 (12-24) | bandes ≈ 0,4-0,45 × 1,5-2,3 m | haute | 1 |

- **`bev_podotactile`** — couleurs : gris clair / blanc ; référence : NF P98-351 : profondeur 0,40-0,42 m, plots tronconiques en quinconce ; quantité : extrémités de traversées ; OSM tactile_paving=yes ×7 nœuds ; refuges ; source de fabrication : maison (géométrie) + matériau (lot mobilier).  
  Tuiles : `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`, `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`


## Matériaux : revêtements, peintures, décalques


### Revêtement

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `enrobe_bbsg_ancien` | — | Enrobé BBSG ancien gris clair oxydé, texture fermée, fissures pontées au bitume (réseau dense) | surface | luminance 150-165/255 sur l’ortho ; RVB ≈ 155-160 neutre ; bandes de gomme sombres dans les traces ; pontages = décalque séparé | haute | 1 |
| `enrobe_bbsg_neuf` | — | Enrobé neuf 2025 (réfection travaux C1 : centre du carrefour, avenue du Vercors probable), sombre et homogène | surface | nettement plus sombre que l’allée voisine, granulats fins | moyenne | 1 |
| `enrobe_reprise_tranchee` | — | Reprise d’enrobé (tranchées, rapiéçages) plus sombre et plus lisse, joints nets | surface | bandes 1-3 m et plaques ≈ 170 m² (arrêt SO) | haute | 2 |
| `enrobe_piste_cyclable` | — | Enrobé de la piste bidirectionnelle (Chronovélo), plus récent et plus sombre, plumage par endroits | surface | RVB ≈ 131/138/134 ; largeur 3,0-3,4 m | haute | 1 |
| `enrobe_trottoir` | — | Enrobé de trottoir, plus sombre et rugueux | surface | trottoirs et cheminements 1,8-3 m | haute | 2 |
| `enrobe_clair_granulats` | — | Surface centrale / refuges : enrobé clair grenaillé ou béton désactivé à granulats apparents | surface | gris très clair, gravillons visibles (2020) | moyenne | 2 |
| `enrobe_colore_ocre` | — | Enrobé ou résine coloré ocre-orangé délavé (îlots à niveau de la Revirée) | surface | R−B ≈ +27 à +36 | moyenne (ortho seule) | 2 |
| `resine_verte` | — | Résine verte délavée des traversées cyclables de la Revirée | surface | RVB ≈ 150/162/151 (presque gris) | haute | 2 |
| `resine_cyan` | — | Résine/peinture cyan pâle (rectangles de la traversée de piste NO, tirets turquoise d’axe) | surface | RVB ≈ 164/181/180 | moyenne | 3 |
| `beton_bordure` | — | Béton gris clair des bordures, caniveaux et dalles (vieilli, épaufrures, mousses) | surface | — | haute | 1 |
| `paves_granit` | — | Pavés de granit gris clair (anneaux d’îlots, rangée de pavés affleurants de l’allée sud) | surface | pavés 10-15 cm | haute | 2 |
| `beton_galets` | — | Galets sertis dans le béton (îlots du raccordement SE de Verdun) | surface | ≈ 2 m de large | moyenne (ortho) | 3 |
| `gravillons_ilot` | — | Gravillons clairs des îlots du Vercors | surface | — | haute | 2 |
| `stabilise_beige` | — | Sable stabilisé / grave fine beige (cheminements, abords est) | surface | RVB ≈ 153/148/135 | moyenne | 3 |
| `gazon_tondu` | — | Gazon tondu (îlots engazonnés, accotements) | surface | — | haute | 1 |
| `herbe_haute` | — | Herbe haute non tondue (accotements NE, bande piste/chaussée) | surface | 0,3-0,6 m | haute | 1 |
| `gazon_sec` | — | Gazon grillé d’été (juillet 2026) avec feuilles mortes | surface | — | haute | 2 |
| `noue_plantee` | — | Noue / bande plantée de gestion des eaux pluviales (terre, prairie, jeunes arbres) | surface | bande ≈ 4,6 m (v −10,8 à −15,4) côté SE | moyenne (plan projet, non vue en photo) | 2 |
| `paillage_mineral` | — | Paillage minéral (galets/gravier) au pied des jeunes arbres | surface | — | moyenne | 3 |
| `terre_nue` | — | Terre nue remaniée (bandes en attente de plantation) | surface | — | moyenne | 3 |

- **`enrobe_bbsg_ancien`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c01.jpg`, `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`, `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c02.jpg`

- **`enrobe_bbsg_neuf`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux) ; note : Le centre du carrefour est déjà en enrobé neuf sombre sur l’ortho IGN 2024.  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`

- **`enrobe_reprise_tranchee`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c02.jpg`

- **`enrobe_piste_cyclable`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c00.jpg`, `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`

- **`enrobe_trottoir`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`

- **`enrobe_clair_granulats`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux) ; note : Probablement refait en 2025 au centre (à confirmer).  
  Tuiles : `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c01.jpg`, `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c02.jpg`

- **`enrobe_colore_ocre`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : — (source non photographique : analyses reviree_no-09/17 (ortho 5 cm))

- **`resine_verte`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`, `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`

- **`resine_cyan`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`

- **`beton_bordure`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433_hd_r01_c02.jpg`, `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`

- **`paves_granit`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`

- **`beton_galets`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : — (source non photographique : analyse verdun_so-09)

- **`gravillons_ilot`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`

- **`stabilise_beige`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : — (source non photographique : analyse abords_est-22)

- **`gazon_tondu`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2024-05-01_26ea5f01-166c-4871-8dba-660e5dd56686_hd_r01_c01.jpg`, `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c00.jpg`

- **`herbe_haute`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 + cartes d’herbe (instances) (lot materiaux).  
  Tuiles : `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`, `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r01_c02.jpg`

- **`gazon_sec`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`, `2026-07-28_ded07efa-75ec-4289-972a-56c9e98a1309_hd_r01_c02.jpg`

- **`noue_plantee`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`

- **`paillage_mineral`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : `2026-07-28_ffc2e8ac-50a1-422d-8a27-6514243a81e5_hd_r01_c00.jpg`

- **`terre_nue`** — quantité : voir couches voirie (recon) ; source de fabrication : CC0 (ambientCG / Poly Haven) recoloré sur l’ortho 5 cm (lot materiaux).  
  Tuiles : — (source non photographique : analyse p2025_01_vercors-20)


### Peinture / décalque

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `peinture_blanche` | — | Peinture blanche rétroréfléchissante (lignes, zébras, flèches, symboles vélo/PMR, « 30 », « 50 ») | surface | usure 0 (marquages 2025) à 3 et fantômes F ; billes de verre ; couverture 0,7-0,95 sur les zébras anciens | haute | 1 |
| `peinture_jaune_chronovelo` | — | Jaune Chronovélo (lignes de rive de piste, blocs des traversées cyclables, points d’axe) : jaune vif neuf / ocre-kaki délavé | surface | blocs ≈ 0,45 × 0,6 m, joints 0,10 m | haute | 1 |
| `peinture_jaune_zigzag` | — | Jaune des zigzags d’arrêt de bus (trait 0,10-0,12 m, pâle) | surface | RVB ≈ 171/172/156 | haute | 1 |
| `peinture_verte` | — | Vert des surfaces cyclables (voir resine_verte) | surface | délavé | haute | 2 |
| `pontage_fissures` | — | Pontage de fissures au bitume (traits sombres sinueux, brillants à contre-jour) | surface | largeur 3-6 cm | haute | 1 |
| `decal_tampon_fonte` | — | Tampons de regards en fonte (ronds Ø 0,6-0,8 m, carrés) et grilles d’avaloirs | surface | dizaines dans l’emprise | haute | 2 |
| `decal_boucle_detection` | — | Saignées de boucles de détection (traits noirs rectangulaires) | surface | 3 postes au moins (Verdun SO) | moyenne | 3 |

- **`peinture_blanche`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c02.jpg`, `2023-03-18_e2574612-b380-4cb2-918e-d5506aff8145_hd_r01_c01.jpg`

- **`peinture_jaune_chronovelo`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c01.jpg`, `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c02.jpg`, `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`

- **`peinture_jaune_zigzag`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c02.jpg`, `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`

- **`peinture_verte`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`

- **`pontage_fissures`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c01.jpg`, `2025-08-31_a83dae90-c92a-472e-8d22-2e8863c47968_hd_r01_c01.jpg`

- **`decal_tampon_fonte`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c01.jpg`, `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`

- **`decal_boucle_detection`** — quantité : marquages de recon/out/paquet_jardin/marquages ; source de fabrication : maison (masques d’usure procéduraux 0-3 + F) (lot materiaux).  
  Tuiles : — (source non photographique : analyses verdun_so, coeur)


## Végétation


### Arbre (inventaire Métropole)

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `arbre_populus_nigra_moyen` | Populus nigra | Populus nigra — classe moyen, port semi-libre | 4 | hauteur 10-20 m ; circonférence 145-195 cm | haute | 1 |
| `arbre_populus_nigra_grand` | Populus nigra | Populus nigra — classe grand, port libre | 1 | hauteur 20-30 m ; circonférence 145 cm | haute | 1 |
| `arbre_populus_sp_tetard_moyen` | Populus sp. | Populus sp. — classe moyen, port têtard | 4 | hauteur 10-20 m ; circonférence 118-280 cm | haute | 1 |
| `arbre_populus_nigra_italica_grand` | Populus nigra « Italica » | Populus nigra « Italica » — classe grand, port architecturé (fastigié) | 1 | hauteur 20-30 m ; circonférence 210 cm | moyenne | 2 |
| `arbre_cedrus_atlantica_grand` | Cedrus atlantica | Cedrus atlantica — classe grand, port libre | 2 | hauteur 20-30 m (inventaire 10-20 m pour l’angle Revirée, visiblement > 15 m) ; circonférence 120-165 cm | haute | 1 |
| `arbre_tilia_cordata_moyen` | Tilia cordata | Tilia cordata — classe moyen, port libre | 6 | hauteur 10-20 m ; circonférence 95-184 cm | moyenne | 1 |
| `arbre_quercus_robur_moyen` | Quercus robur | Quercus robur — classe moyen, port libre / semi-libre | 5 | hauteur 10-20 m ; circonférence 110-165 cm | moyenne | 1 |
| `arbre_quercus_robur_petit` | Quercus robur | Quercus robur — classe petit, port libre / semi-libre | 3 | hauteur 5-10 m ; circonférence 65-110 cm | moyenne | 2 |
| `arbre_quercus_robur_grand` | Quercus robur | Quercus robur — classe grand, port libre | 1 | hauteur 20-30 m ; circonférence 129 cm | moyenne | 2 |
| `arbre_acer_campestre_jeune` | Acer campestre | Acer campestre — classe jeune, port semi-libre (1 têtard) | 7 | hauteur 0-5 m ; circonférence 35-60 cm | haute (inventaire) | 1 |
| `arbre_fraxinus_excelsior_moyen` | Fraxinus excelsior | Fraxinus excelsior — classe moyen, port libre | 4 | hauteur 5-20 m ; circonférence 83-85 cm | moyenne | 2 |
| `arbre_carpinus_betulus_moyen` | Carpinus betulus | Carpinus betulus — classe moyen, port libre | 4 | hauteur 5-20 m ; circonférence 64-123 cm | moyenne | 2 |
| `arbre_betula_pendula_moyen` | Betula pendula | Betula pendula — classe moyen, port semi-libre | 2 | hauteur 10-30 m ; circonférence 65-80 cm | moyenne | 2 |
| `arbre_corylus_colurna_petit` | Corylus colurna | Corylus colurna — classe petit, port libre | 2 | hauteur 5-10 m ; circonférence 45-85 cm | moyenne | 3 |
| `arbre_magnolia_grandiflora_jeune` | Magnolia grandiflora | Magnolia grandiflora — classe jeune, port libre | 2 | hauteur 0-5 m ; circonférence 35 cm | moyenne | 3 |
| `arbre_crataegus_laevigata_jeune` | Crataegus laevigata | Crataegus laevigata — classe jeune, port libre | 1 | hauteur 0-5 m ; circonférence 50 cm | moyenne | 3 |
| `arbre_sorbus_sp_jeune` | Sorbus sp. | Sorbus sp. — classe jeune, port libre | 1 | hauteur 0-5 m ; circonférence 25 cm | moyenne | 3 |
| `arbre_salix_babylonica_tetard_petit` | Salix babylonica | Salix babylonica — classe petit, port têtard | 1 | hauteur 5-10 m ; circonférence 220 cm | moyenne | 3 |

- **`arbre_populus_nigra_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : alignement « Avenue de Verdun/Schneider » côté SE de la branche NE.  
  Tuiles : `2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3_hd_r01_c01.jpg`, `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r00_c02.jpg`

- **`arbre_populus_nigra_grand`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : même alignement.  
  Tuiles : `2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3_hd_r01_c01.jpg`

- **`arbre_populus_sp_tetard_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : alignement NE côté NO ; têtes de saule/peuplier taillées.  
  Tuiles : `2025-05-18_9fc8ba46-9a08-483b-92f7-ad37798f9330_hd_r01_c03.jpg`

- **`arbre_populus_nigra_italica_grand`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : parc NO.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_cedrus_atlantica_grand`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : grand cèdre de l’angle Revirée (repère visuel majeur, ombre sur la chaussée) + 1 au NE.  
  Tuiles : `2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d_hd_r01_c03.jpg`, `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c03.jpg`

- **`arbre_tilia_cordata_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : groupement NO (parc de la Revirée).  
  Tuiles : `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`

- **`arbre_quercus_robur_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : groupements NO et sud.  
  Tuiles : `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`

- **`arbre_quercus_robur_petit`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla).  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_quercus_robur_grand`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla).  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_acer_campestre_jeune`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : alignement « Avenue de Verdun nord » (haie séparative NO, branche SO) ; + « Ac » du plan projet 2025.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_fraxinus_excelsior_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : angle NE éloigné.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_carpinus_betulus_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : + 1 Carpinus betulus « Pyramidalis » jeune.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_betula_pendula_moyen`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : parc NO.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_corylus_colurna_petit`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : alignement ouest.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_magnolia_grandiflora_jeune`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : sud (allée de L’Horloge).  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_crataegus_laevigata_jeune`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla).  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_sorbus_sp_jeune`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla).  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)

- **`arbre_salix_babylonica_tetard_petit`** — quantité : inventaire arbres Métropole (état « Présent ») dans le carré de 300 m ; source de fabrication : procédural maison (< 30 000 tri) ; haut de gamme : SpeedTree / Megascans / SideFX Labs Tree (lot vegetation_carla) ; note : NE éloigné.  
  Tuiles : — (source non photographique : data/context/arbres_metropole.geojson)


### Arbre (hors inventaire / privé)

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `arbre_cupressus_sempervirens_grand` | Cupressus sempervirens (cyprès d’Italie) | Cupressus sempervirens (cyprès d’Italie) | 2 | fastigié, 15-20 m | haute | 1 |
| `arbre_pinus_sylvestris_moyen` | Pinus sp. (pin sylvestre probable) | Pinus sp. (pin sylvestre probable) | 2 | 12-18 m, houppier clair en tête | faible (espèce) | 2 |
| `arbre_cedrus_deodara_grand` | Cedrus (deodara ou atlantica) — grand conifère à branches retombantes | Cedrus (deodara ou atlantica) — grand conifère à branches retombantes | 1 | 15-20 m | moyenne | 2 |
| `arbre_feuillu_generique_moyen` | Feuillu générique (essence non renseignée) | Feuillu générique (essence non renseignée) | 200 | 5-20 m (échelle GAM) | moyenne | 1 |
| `arbre_conifere_generique_moyen` | Conifère générique | Conifère générique | 10 | 10-20 m | moyenne | 2 |

- **`arbre_cupressus_sempervirens_grand`** — quantité : photos + levé GAM etat_2026/arbre_pct (284 symboles dans l’emprise) ; source de fabrication : procédural maison / Megascans (lot vegetation_carla) ; note : jardinerie Paquet Jardin (privé, repère visuel fort).  
  Tuiles : `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`, `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c03.jpg`, `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`

- **`arbre_pinus_sylvestris_moyen`** — quantité : photos + levé GAM etat_2026/arbre_pct (284 symboles dans l’emprise) ; source de fabrication : procédural maison / Megascans (lot vegetation_carla) ; note : abords sud (privé).  
  Tuiles : `2026-07-28_ded07efa-75ec-4289-972a-56c9e98a1309_hd_r01_c02.jpg`

- **`arbre_cedrus_deodara_grand`** — quantité : photos + levé GAM etat_2026/arbre_pct (284 symboles dans l’emprise) ; source de fabrication : procédural maison / Megascans (lot vegetation_carla) ; note : rive est du Vercors, devant le local technique (privé).  
  Tuiles : `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c01.jpg`

- **`arbre_feuillu_generique_moyen`** — quantité : photos + levé GAM etat_2026/arbre_pct (284 symboles dans l’emprise) ; source de fabrication : procédural maison / Megascans (lot vegetation_carla) ; note : levé GAM : 270 symboles ARBRE_FEUILLU dans l’emprise dont ≈ 50 de l’inventaire public ; variantes petit/moyen/grand par échelle.  
  Tuiles : `2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3_hd_r01_c03.jpg`

- **`arbre_conifere_generique_moyen`** — quantité : photos + levé GAM etat_2026/arbre_pct (284 symboles dans l’emprise) ; source de fabrication : procédural maison / Megascans (lot vegetation_carla) ; note : levé GAM : 13 ARBRE_CONIFERE.  
  Tuiles : — (source non photographique : GAM; photos)


### Jeune sujet (plantations 2025)

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `arbre_alnus_cordata_jeune` | Alnus cordata (code « Alc ») | Alnus cordata (code « Alc ») — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 2 | TPC planté SO ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 1 |
| `arbre_alnus_spaethii_jeune` | Alnus × spaethii (code « As », lecture probable) | Alnus × spaethii (code « As », lecture probable) — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 1 | TPC planté SO ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 2 |
| `arbre_cercis_siliquastrum_jeune` | Cercis siliquastrum (code « Cs », lecture probable) | Cercis siliquastrum (code « Cs », lecture probable) — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 1 | TPC planté SO ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 2 |
| `arbre_ulmus_hybride_jeune` | Ulmus (orme hybride résistant, code « Ul ») | Ulmus (orme hybride résistant, code « Ul ») — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 2 | noue plantée SE ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 1 |
| `arbre_quercus_cerris_jeune` | Quercus cerris (code « Qc », lecture probable) | Quercus cerris (code « Qc », lecture probable) — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 2 | noue plantée SE ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 2 |
| `arbre_gleditsia_triacanthos_jeune` | Gleditsia triacanthos (code « Gt ») | Gleditsia triacanthos (code « Gt ») — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 1 | bande plantée NO le long de la piste ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 2 |
| `arbre_celtis_australis_jeune` | Celtis australis (code « Ca », lecture probable) | Celtis australis (code « Ca », lecture probable) — jeune sujet tuteuré (tige 16/18 à 20/25, ≈ 3-5 m) | 1 | bande plantée NO, angle Revirée ; hauteur 3-5 m, houppier Ø 1,5-2,5 m ; tuteur tripode bois + collier ; paillage | faible à moyenne (projet, essences déduites des abréviations ; aucune photo postérieure aux plantations au cœur) | 2 |
| `arbre_jeune_tuteure_generique` | — | Jeune arbre générique tuteuré (tripode bois, ganivelle optionnelle) — repli si l’essence n’est pas confirmée | 15 (13-20) | 3-5 m | haute (besoin) | 1 |

- **`arbre_alnus_cordata_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_alnus_spaethii_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_cercis_siliquastrum_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_ulmus_hybride_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_quercus_cerris_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_gleditsia_triacanthos_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_celtis_australis_jeune`** — quantité : symboles d’arbres plantés (carré rouge barré) et codes d’essence lus sur le plan projet 2025 géoréférencé ; 14-15 jeunes arbres au total (dont 2-3 « Ac ») ; état 2026 : probable ; source de fabrication : procédural maison (un même générateur « jeune sujet » paramétré par essence) (lot vegetation_carla).  
  Tuiles : `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`, `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`

- **`arbre_jeune_tuteure_generique`** — état 2026 : probable ; source de fabrication : procédural maison (lot vegetation_carla).  
  Tuiles : `2026-07-28_ffc2e8ac-50a1-422d-8a27-6514243a81e5_hd_r01_c00.jpg`


### Haie

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `haie_taillee_persistante` | — | Haie taillée persistante (laurier-cerise / photinia probables), 1,2-2,5 m | 650 (500-900) | h 1,2-2,5 m, épaisseur 1,0-2,5 m | haute (présence) / faible (essence) | 1 |

- **`haie_taillee_persistante`** — quantité : m ; BD TOPO haie 646 m + zones « Haie » ; haies séparatives de Verdun SO (2 lignes) ; source de fabrication : module extrudable maison (boîte + cartes de feuillage) (lot vegetation_carla).  
  Tuiles : `2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d_hd_r01_c03.jpg`, `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`, `2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3_hd_r01_c03.jpg`


### Massif

| Asset | Code / essence | Description | Qté 2026 (min-max) | Dimensions observées | Conf. | Prio. |
|---|---|---|---|---|---|---|
| `massif_arbustif` | — | Massif arbustif libre / buissons (îlots, bandes plantées, sous-bois) | surface | 0,5-3 m | haute | 2 |

- **`massif_arbustif`** — quantité : BD TOPO zone de végétation 9 900 m² ; source de fabrication : CC0 / Megascans (lot vegetation_carla).  
  Tuiles : `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c03.jpg`, `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`


## Types non retenus (non vus ou hors emprise)

- **B14 (limitation de vitesse)** : aucun panneau vu dans l’emprise ; seule une annotation FR:B14[30] à ≈ 265 m au NE (hors emprise) ; « 50 » et « 30 » peints au sol
- **B30 / B51 (zone 30)** : non observé ; l’analyse contexte_securite le recommande pour l’ISA mais aucune photo ne le montre — à vérifier sur le terrain
- **C12, C20a, CE** : non observés (traversées à feux, pas de C20a vu) — ne pas fabriquer pour ce site
- **R13c / R14 / R15 / feux bus** : aucun feu vélo ou bus lisible ; R13c laissé en variante facultative
- **B21-1, B22a** : non observés (C113 utilisé pour la piste)
- **Potence de feux au-dessus de la chaussée** : non observée
- **Bornes (borne fontaine, borne de recharge)** : non observées
- **Signalisation privée (L’Horloge : « Réservé », « Parking privé », « Cabinet kinésithérapie », « → ACCÈS »)** : présente à ≈ 130-145 m au sud ; texte propre au site : un panneau texte générique suffit (priorité 3)
- **AK3, A17 et B2a/AB4 hors emprise** : annotations Panoramax à > 150 m (NE et SO) ; seul l’A17 de l’approche NE est retenu (bord d’emprise)

## Incertitudes

- Aucune photo de rue n’est postérieure aux travaux C1 au cœur du carrefour (dernières : 2025-08-31 en travaux ; 2026-07-28 seulement à ≈ 130 m au sud) : les modèles de mobilier 2026 (abris, feux, panneaux) sont supposés identiques aux modèles d’avant travaux.
- Essences des plantations 2025 lues sur les abréviations du plan projet (Alc, As, Cs, Ul, Qc, Ac, Gt, Ca) : interprétation probable, à confirmer sur place.
- Codes de panonceaux : M9c (« CÉDEZ LE PASSAGE ») et M12a probables ; gamme exacte des C113/C114/J5 à confirmer.
- Feux : nombre exact de têtes et de répétiteurs non dénombrable sur les photos (beaucoup de têtes vues de dos) — fourchettes données.
- Lanternes SHP de la Revirée et type exact des bordures franchissables (A2) non vus de près.

## Récapitulatif des noms d’assets à fabriquer

- **lot signalisation** (31) : `panneau_B21a1`, `panneau_J5`, `panneau_C113`, `panneau_C114`, `panneau_AB3a`, `panneau_M9c`, `panneau_AB4`, `panneau_B1`, `panneau_B2b`, `panneau_B2a`, `panneau_B6a1`, `panneau_C13a` (p2), `panneau_A17` (p2), `panneau_M12a` (p2), `panneau_D21a_la_reviree_college`, `panneau_D21a_commerces_reviree`, `plaque_rue_avenue_de_verdun` (p3), `mat_panneau_d60`, `mat_panneau_ilot_court`, `feu_R11v`, `feu_R11v_repetiteur`, `feu_R12`, `feu_R12_horizontal` (p2), `feu_R13c` (p3), `boitier_bouton_appel` (p2), `mat_feu_d114`, `mat_feu_crosse_camera` (p2), `panneau_B2b_temporaire` (p3), `panneau_AK5` (p3), `balise_chevrons_chantier` (p3), `mat_feu_provisoire` (p3)
- **lot mobilier** (31) : `totem_pr_smmag` (p2), `armoire_commande_feux` (p2), `candelabre_double_crosse`, `candelabre_crosse_simple`, `candelabre_mat_droit_led`, `candelabre_mat_droit_shp` (p3), `poteau_bois_reseau` (p2), `mat_illumination_cable` (p3), `abri_bus_m_reso`, `poteau_arret_m_reso`, `barriere_croix_saint_andre`, `potelet_noir`, `banc_bois_metal` (p2), `corbeille_cylindrique` (p2), `arceau_velo` (p2), `barriere_levante` (p3), `poteau_incendie` (p3), `armoire_technique` (p3), `ganivelle_bois` (p3), `cloture_grillage_rigide` (p3), `bordure_T2`, `bordure_T2_peinte_blanc`, `bordure_quai_bus`, `bordure_A2`, `bordure_P1`, `caniveau_cs`, `bordure_paves_granit` (p2), `abaisse_chartiere`, `bev_podotactile`, `separateur_modulaire_K16` (p3), `barriere_chantier_rouge_blanc` (p3)
- **lot materiaux** (27) : `enrobe_bbsg_ancien`, `enrobe_bbsg_neuf`, `enrobe_reprise_tranchee` (p2), `enrobe_piste_cyclable`, `enrobe_trottoir` (p2), `enrobe_clair_granulats` (p2), `enrobe_colore_ocre` (p2), `resine_verte` (p2), `resine_cyan` (p3), `beton_bordure`, `paves_granit` (p2), `beton_galets` (p3), `gravillons_ilot` (p2), `stabilise_beige` (p3), `gazon_tondu`, `herbe_haute`, `gazon_sec` (p2), `noue_plantee` (p2), `paillage_mineral` (p3), `terre_nue` (p3), `peinture_blanche`, `peinture_jaune_chronovelo`, `peinture_jaune_zigzag`, `peinture_verte` (p2), `pontage_fissures`, `decal_tampon_fonte` (p2), `decal_boucle_detection` (p3)
- **lot vegetation_carla** (33) : `arbre_populus_nigra_moyen`, `arbre_populus_nigra_grand`, `arbre_populus_sp_tetard_moyen`, `arbre_populus_nigra_italica_grand` (p2), `arbre_cedrus_atlantica_grand`, `arbre_tilia_cordata_moyen`, `arbre_quercus_robur_moyen`, `arbre_quercus_robur_petit` (p2), `arbre_quercus_robur_grand` (p2), `arbre_acer_campestre_jeune`, `arbre_fraxinus_excelsior_moyen` (p2), `arbre_carpinus_betulus_moyen` (p2), `arbre_betula_pendula_moyen` (p2), `arbre_corylus_colurna_petit` (p3), `arbre_magnolia_grandiflora_jeune` (p3), `arbre_crataegus_laevigata_jeune` (p3), `arbre_sorbus_sp_jeune` (p3), `arbre_salix_babylonica_tetard_petit` (p3), `arbre_cupressus_sempervirens_grand`, `arbre_pinus_sylvestris_moyen` (p2), `arbre_cedrus_deodara_grand` (p2), `arbre_feuillu_generique_moyen`, `arbre_conifere_generique_moyen` (p2), `arbre_alnus_cordata_jeune`, `arbre_alnus_spaethii_jeune` (p2), `arbre_cercis_siliquastrum_jeune` (p2), `arbre_ulmus_hybride_jeune`, `arbre_quercus_cerris_jeune` (p2), `arbre_gleditsia_triacanthos_jeune` (p2), `arbre_celtis_australis_jeune` (p2), `arbre_jeune_tuteure_generique`, `haie_taillee_persistante`, `massif_arbustif` (p2)

## Tuiles examinées (1000×1000 natives, ouvertes une à une)

- `2024-05-01_1149e115-2c88-48fc-a908-bbf633abaa72_hd_r01_c02.jpg`
- `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c03.jpg`
- `2026-07-28_ffc2e8ac-50a1-422d-8a27-6514243a81e5_hd_r01_c00.jpg`
- `2026-07-28_f8d91bb1-694d-47fd-b2a4-3f16b57378bb_hd_r01_c04.jpg`
- `2026-07-28_ded07efa-75ec-4289-972a-56c9e98a1309_hd_r01_c02.jpg`
- `2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3_hd_r01_c01.jpg`
- `2025-05-18_e540bf1d-c8ab-4f0a-ae4e-19d7ea07ddc3_hd_r01_c03.jpg`
- `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c01.jpg`
- `2025-01-12_d88855f2-6272-43f9-bb83-562d6d894cfe_hd_r01_c00.jpg`
- `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c03.jpg`
- `2025-05-18_2374105b-0338-40b7-ba54-0672c4a92cd8_hd_r01_c03.jpg`
- `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c03.jpg`
- `2025-05-18_bc579b89-508c-49fc-a23d-246d95dc2460_hd_r01_c02.jpg`
- `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c01.jpg`
- `2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a_hd_r01_c00.jpg`
- `2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d_hd_r01_c03.jpg`
- `2024-05-01_26ea5f01-166c-4871-8dba-660e5dd56686_hd_r01_c01.jpg`
- `2025-08-31_10ec04d5-3da4-4e39-aa0f-828450425ad1_hd_r01_c03.jpg`
- `2025-08-31_fdc59178-d148-43e0-a307-4742929b45a2_hd_r01_c00.jpg`
- `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r00_c02.jpg`
- `2025-08-31_bb9c05ff-2fa0-4e65-9e7b-cd7c2ec4eb9e_hd_r01_c02.jpg`
- `2025-08-31_9ef861d4-0b2e-403d-b1ee-2d8e038c6cad_hd_r00_c03.jpg`
- `2025-08-31_9ef861d4-0b2e-403d-b1ee-2d8e038c6cad_hd_r01_c03.jpg`
- `2025-05-18_9fc8ba46-9a08-483b-92f7-ad37798f9330_hd_r01_c03.jpg`
- `2025-08-31_b536a4a0-72c8-4d78-ac7d-fe7d65b98d91_hd_r01_c02.jpg`
- `2025-08-31_81882270-2b91-457a-a7c9-4f955319ea22_hd_r01_c00.jpg`
- `2025-08-31_a83dae90-c92a-472e-8d22-2e8863c47968_hd_r01_c01.jpg`
- `2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433_hd_r01_c02.jpg`
- `2025-05-18_e5d79de9-9462-4b4d-bc3b-192ebd6ac6f5_hd_r01_c04.jpg`
- `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c01.jpg`
- `2020-05-21_0fe67f82-0d4b-4323-8c47-02545c92dc1a_hd_r01_c02.jpg`
- `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c02.jpg`
- `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c04.jpg`
- `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c02.jpg`
- `2025-05-18_119d9094-3d9e-4598-b908-d0571afd136c_hd_r01_c00.jpg`
- `2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0_hd_r01_c00.jpg`
- `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c03.jpg`
- `2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a_hd_r01_c03.jpg`
- `2024-08-24_2ab4efbc-7a8b-4efb-ab98-f9f09c47aa8c_hd_r01_c01.jpg`
- `2025-08-31_1d999186-824b-4ec7-8b52-0402511307a3_hd_r01_c00.jpg`
- `2025-08-31_ab4cfacd-9fd7-4436-a12d-e410b590026c_hd_r01_c02.jpg`
- `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r01_c02.jpg`
- `2025-05-18_31d16b8e-d371-4281-8fe7-b62c62ea0cc3_hd_r00_c02.jpg`
- `2023-03-18_e2574612-b380-4cb2-918e-d5506aff8145_hd_r01_c01.jpg`
- `2023-03-18_a275b2ea-ca5a-4224-b4ad-f335ddbfe981_hd_r00_c01.jpg`
- `data/raw/panoramax/complements/tiles/2025-08-31_f6297e9f-f229-45c1-bc88-c902fa605716_hd_x2100_y500.jpg`
- `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c01.jpg`
- `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r00_c02.jpg`
- `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c00.jpg`
- `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg`
- `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c02.jpg`
- `data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r02_c02.jpg`
