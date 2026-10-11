# Vérification des règles de conception : carrefour Paquet Jardin v2

Rapport produit par `python recon/pcg/controle/verifier_regles.py` (détail complet : `rapport_regles.json`). Chaque règle « verifier » de `assets/specs/regles_conception.json`, et chaque règle « contraindre » mesurable dans les fichiers, est contrôlée sur la description v2 et sur la fabrication Houdini (`fabrique_hda`). Coordonnées : repère local (L93 − O), en mètres.

## Entrées

- Règles : `assets/specs/regles_conception.json` version 1.1, 255 règles.
- Description : `recon/out/paquet_jardin/v2/description/base`, schéma description_scene_v2/0.3, hash `222b11f588b7…`.
- Fabrication : `recon/out/paquet_jardin/v2/fabrique_hda`, description lue `recon/out/paquet_jardin/v2/description/base` (hash `222b11f588b7…`, identique de la description contrôlée).

## Synthèse

- Règles « verifier » (action principale ou secondaire) : 86 ; contrôlées 84 (98 %), dont 19 en partie ; non contrôlées 2 ; en violation 60.
- Règles « contraindre » seules : 56 ; contrôlées 43 ; non contrôlables dans les fichiers 13 (réglages de l'éditeur UE).
- Toutes règles : 128 contrôles exécutés, 0 en erreur.
- Cas en violation : 4385 (bloquant 19, majeur 2752, mineur 1541, info 73).

### Par famille

| Famille | Règles | Contrôlées | Cas testés | Violations | Règles en violation | Bloquant | Majeur | Mineur | Info |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| lignes_longitudinales | 12 | 9 | 76 | 10 | 4 | 0 | 1 | 0 | 9 |
| lignes_transversales_feux | 14 | 5 | 53 | 2 | 1 | 0 | 2 | 0 | 0 |
| passages_pietons | 11 | 7 | 118 | 18 | 5 | 0 | 4 | 14 | 0 |
| fleches_symboles | 13 | 5 | 60 | 9 | 3 | 0 | 1 | 8 | 0 |
| cycles | 21 | 7 | 56 | 10 | 4 | 0 | 0 | 10 | 0 |
| transport_commun | 14 | 4 | 16 | 7 | 3 | 0 | 0 | 7 | 0 |
| ilots_refuges | 10 | 5 | 41 | 17 | 3 | 0 | 3 | 1 | 13 |
| stationnement | 6 | 3 | 24 | 11 | 1 | 0 | 0 | 11 | 0 |
| largeurs_voies | 4 | 4 | 84 | 43 | 4 | 0 | 0 | 43 | 0 |
| chaussee_profil | 4 | 3 | 162 | 119 | 3 | 0 | 76 | 43 | 0 |
| trottoirs_accessibilite | 13 | 11 | 8364 | 275 | 7 | 0 | 199 | 76 | 0 |
| abaisses_bev | 20 | 6 | 693 | 202 | 4 | 0 | 179 | 23 | 0 |
| bordures_rayons | 7 | 3 | 546 | 384 | 3 | 0 | 380 | 4 | 0 |
| assainissement | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| vegetation_fosses | 4 | 1 | 25 | 2 | 1 | 0 | 0 | 2 | 0 |
| detection_deduction | 27 | 16 | 959 | 92 | 9 | 0 | 66 | 26 | 0 |
| fusion | 5 | 5 | 1083 | 0 | 0 | 0 | 0 | 0 | 0 |
| validation | 11 | 10 | 5293 | 2112 | 10 | 557 | 1471 | 84 | 0 |
| fabrication_marquages | 15 | 7 | 1560 | 108 | 5 | 4 | 15 | 85 | 4 |
| fabrication_sol | 12 | 8 | 3363 | 720 | 6 | 14 | 635 | 36 | 35 |
| rendu_ue | 9 | 3 | 446 | 1 | 1 | 0 | 1 | 0 | 0 |
| pcg_instances | 15 | 6 | 29934 | 243 | 2 | 0 | 54 | 189 | 0 |
| verite_terrain_adas | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Les 30 pires violations

Classement : sévérité, puis écart relatif au seuil ; au plus 3 cas par règle.

| # | Règle | Sévérité | Entité | x ; y (local) | Valeur | Seuil | Détail |
|---:|---|---|---|---|---|---|---|
| 1 | TQ-SOL-009 | bloquant | T_02_02 (S-0312c, S-0301a) | -23,8 ; -15,7 | 1,700 | 0 m² de trou ou de recouvrement | 0 trou(s), 7 recouvrement(s) ; pire : recouvrement 0.86 m² |
| 2 | TQ-SOL-009 | bloquant | T_05_04 (S-B0536) | 136,4 ; 71,1 | 1,400 | 0 m² de trou ou de recouvrement | 0 trou(s), 1 recouvrement(s) ; pire : recouvrement 1.40 m² |
| 3 | TQ-SOL-009 | bloquant | T_02_03 (S-0312a) | -10,6 ; 6,6 | 1,260 | 0 m² de trou ou de recouvrement | 0 trou(s), 5 recouvrement(s) ; pire : recouvrement 0.39 m² |
| 4 | TQ-MQG-005 | bloquant | ML-6200 | -137,6 ; -151,2 | -1,000 | dessus − sol dans [0,5 ; 6] mm | 15 sommet(s) hors sol, 0 enterré(s) ou flottant(s) (min 2.0, max 2.0 mm) |
| 5 | TQ-MQG-005 | bloquant | ML-5139 | 150,1 ; 132,2 | -1,000 | dessus − sol dans [0,5 ; 6] mm | 8 sommet(s) hors sol, 0 enterré(s) ou flottant(s) (min 2.0, max 2.0 mm) |
| 6 | VAL-SOL-009 | bloquant | noue (noue_plantee) | 42,0 ; -36,2 | 32,500 | talus ≤ 1/3 (≈ 18,4°) | partie 1b : 41 triangle(s) de noue à plus de 20° (pire 32° sur 2 cm) |
| 7 | TQ-MQG-005 | bloquant | ML-5159 | -150,1 ; -143,2 | -1,000 | dessus − sol dans [0,5 ; 6] mm | 2 sommet(s) hors sol, 0 enterré(s) ou flottant(s) (min 2.0, max 2.0 mm) |
| 8 | GA-TRO-004 | majeur | S-0213a | 79,4 ; 44,9 | 29,100 | ≤ 8 % sur 2 m (≤ 0,25 m²), ≤ 12 % sur 0… | 1426.62 m² > 8 % sur 2 m, 553.76 m² > 12 % sur 0,5 m, 1876.0 m² > 5 % ; trottoir |
| 9 | GA-TRO-004 | majeur | S-0415b | 110,2 ; 60,7 | 20,100 | ≤ 8 % sur 2 m (≤ 0,25 m²), ≤ 12 % sur 0… | 85.19 m² > 8 % sur 2 m, 49.59 m² > 12 % sur 0,5 m, 106.2 m² > 5 % ; trottoir |
| 10 | GA-TRO-004 | majeur | S-0415a | 124,1 ; -21,0 | 20,100 | ≤ 8 % sur 2 m (≤ 0,25 m²), ≤ 12 % sur 0… | 77.09 m² > 8 % sur 2 m, 29.08 m² > 12 % sur 0,5 m, 250.0 m² > 5 % ; trottoir |
| 11 | TQ-VAL-002 | majeur | ML-5253 | -13,6 ; -28,0 | 4,000 | (1)-(5) | (1) aire +108.36 % ; (3) dessus − sol varie de ±7.0 mm (p95) ; (2) bas de jupe à +1.0 mm du sol ; (5) angle min 0.4° |
| 12 | GA-CHA-004 | majeur | S-0159a | -12,5 ; -55,5 | 0,068 | avaloir à ≤ 1 m | point bas de 68 mm sur 176.20 m² sans avaloir |
| 13 | GA-RES-001 | majeur | S-0213a | 78,8 ; 44,1 | 1483,000 | aucune marche > 0,02 m dans la surface | (b) 11 marche(s) > 2 cm dans la surface (la plus longue : 1483 nœuds) |
| 14 | VAL-SOL-009 | majeur | K-0100 | 26,5 ; -39,6 | 0,244 | ±0,002 m | partie 2 : sol devant − pied = +244.2 mm (s = 0.2 m) |
| 15 | GA-CHA-004 | majeur | S-0161a | -118,8 ; -41,5 | 0,337 | avaloir à ≤ 1 m | point bas de 337 mm sur 120.64 m² sans avaloir |
| 16 | VAL-SOL-009 | majeur | S-0161a | -118,8 ; -41,5 | 0,337 | cuvette ≤ 3 mm ou ≤ 0,25 m² | partie 4 : 13 cuvette(s), pire 337 mm sur 120.64 m² |
| 17 | GA-CHA-004 | majeur | S-0161a | -127,1 ; -86,1 | 0,111 | avaloir à ≤ 1 m | point bas de 111 mm sur 93.32 m² sans avaloir |
| 18 | GA-TRO-001 | majeur | S-0203a | 16,9 ; -79,1 | 80,900 | largeur ≥ 1,40 m | 1 partie(s) plus étroite(s) que 1,40 m, la plus grande 80.9 m² |
| 19 | TQ-SOL-013 | majeur | K-0380 | -53,9 ; -38,5 | 0,150 | p95 ≤ 0,03 (alerte 0,05) ; tête = pied … | (b) pied − fil d'eau MNT p95 15.0 cm (max 18.6 cm) |
| 20 | GA-BOR-005 | majeur | K-0232 (fin) / K-0238 | -133,4 ; 62,8 | 0,000 | tête ≤ 0,02, pied ≤ 0,01 (fabriqué ≤ 0,… | en T contre le dos : écart de tête décrit 0.0 cm, de pied 63.5 cm, de dessus fabriqué 0.0 cm |
| 21 | VAL-LIG-002 | majeur | ML-5253 | -12,4 ; -26,7 | 2,000 | (a)-(e) | largeur fabriquée 166 mm pour 120 mm ; aire peinte +108.4 % de l'attendu |
| 22 | MQ-DET-010 | majeur | ML-5139 | 113,5 ; 94,5 | 1,000 | (a)-(d) | (d) 10.41 m² sur trottoir, hors |
| 23 | GA-BOR-005 | majeur | K-0217 (debut) / K-0238 | -132,3 ; 63,4 | 0,000 | tête ≤ 0,02, pied ≤ 0,01 (fabriqué ≤ 0,… | en T contre le dos : écart de tête décrit 0.0 cm, de pied 52.4 cm, de dessus fabriqué 0.0 cm |
| 24 | GA-BOR-001 | majeur | K-0666 | 74,2 ; 62,1 | 97,400 | vue ≥ 0,05 m hors abaissés | 97.4 m sur 97.4 m piéton/circulé sous 0,05 m (vue min 0.010 m) |
| 25 | GA-BOR-005 | majeur | K-0220 (debut) / K-0238 | -131,9 ; 63,5 | 0,000 | tête ≤ 0,02, pied ≤ 0,01 (fabriqué ≤ 0,… | en T contre le dos : écart de tête décrit 0.0 cm, de pied 48.8 cm, de dessus fabriqué 0.0 cm |
| 26 | GA-TRO-001 | majeur | S-0269i | 121,1 ; 109,8 | 48,780 | largeur ≥ 1,40 m | 1 partie(s) plus étroite(s) que 1,40 m, la plus grande 48.8 m² |
| 27 | VAL-FLE-001 | majeur | route 6 voies 1/2 | — | 22,540 | /Δs/ ≤ 0,5 m | dernières flèches des voies voisines décalées de 22.54 m (profil commun) |
| 28 | GA-TRO-001 | majeur | S-0431f | 111,5 ; 71,8 | 40,310 | largeur ≥ 1,40 m | 1 partie(s) plus étroite(s) que 1,40 m, la plus grande 40.3 m² |
| 29 | TQ-VAL-002 | majeur | ML-0208 | -110,6 ; 72,5 | 3,000 | (1)-(5) | (1) aire -18.81 % ; (2) bas de jupe à +1.0 mm du sol ; (5) angle min 9.1° |
| 30 | GA-BOR-001 | majeur | K-0341 | -9,3 ; 22,4 | 71,800 | vue ≥ 0,05 m hors abaissés | 71.8 m sur 74.5 m piéton/circulé sous 0,05 m (vue min 0.015 m) |

## Règles en violation

| Règle | Sévérité | Cible | Statut | Testés | Violations | Conformité | Pire cas |
|---|---|---|---|---:|---:|---:|---|
| VAL-SOL-009 | bloquant | fabrication | implemente | 1030 | 557 | 46 % | noue (noue_plantee) : partie 1b : 41 triangle(s) de noue à plus de 20° (pire 32° sur 2 cm) |
| TQ-SOL-009 | bloquant | fabrication | partiel | 36 | 14 | 61 % | T_02_02 (S-0312c, S-0301a) : 0 trou(s), 7 recouvrement(s) ; pire : recouvrement 0.86 m² |
| TQ-MQG-005 | bloquant | fabrication | implemente | 389 | 4 | 99 % | ML-6200 : 15 sommet(s) hors sol, 0 enterré(s) ou flottant(s) (min 2.0, max 2.0 mm) |
| VAL-KRB-005 | majeur | les_deux | implemente | 3147 | 965 | 69 % | K-0100 : (d) vue posée -0.244 m pour 0.000 m décrite (s = 0.2 m) |
| TQ-SOL-013 | majeur | les_deux | implemente | 1223 | 611 | 50 % | K-0380 : (b) pied − fil d'eau MNT p95 15.0 cm (max 18.6 cm) |
| TQ-VAL-002 | majeur | fabrication | partiel | 389 | 389 | 0 % | ML-5253 : (1) aire +108.36 % ; (3) dessus − sol varie de ±7.0 mm (p95) ; (2) bas de jupe à +1.0 mm … |
| GA-BOR-005 | majeur | les_deux | implemente | 449 | 326 | 27 % | K-0232 (fin) / K-0238 : en T contre le dos : écart de tête décrit 0.0 cm, de pied 63.5 cm, de dessus fabriqué 0.0… |
| GA-ABA-004 | majeur | les_deux | implemente | 618 | 179 | 71 % | K-0360/E003 : chartière posée 0.195 -> 0.001 m sur 0.954 m (chartiere_T3195_T3001_L950_desc) |
| GA-RES-001 | majeur | les_deux | implemente | 224 | 86 | 62 % | S-0213a : (b) 11 marche(s) > 2 cm dans la surface (la plus longue : 1483 nœuds) |
| GA-CHA-004 | majeur | fabrication | implemente | 76 | 76 | 0 % | S-0159a : point bas de 68 mm sur 176.20 m² sans avaloir |
| VAL-XOD-008 | majeur | les_deux | implemente | 138 | 63 | 54 % | route 6 s0 voie 2 [9-19] brok… : (a) ML-5228 : largeur 0.25 pour width 0.12, modulation continue pour broken |
| MQ-DET-010 | majeur | fabrication | implemente | 389 | 59 | 85 % | ML-5139 : (d) 10.41 m² sur trottoir, hors |
| GA-TRO-001 | majeur | description | implemente | 176 | 57 | 68 % | S-0203a : 1 partie(s) plus étroite(s) que 1,40 m, la plus grande 80.9 m² |
| GA-BOR-001 | majeur | description | implemente | 89 | 54 | 39 % | K-0666 : 97.4 m sur 97.4 m piéton/circulé sous 0,05 m (vue min 0.010 m) |
| GA-TRO-004 | majeur | fabrication | implemente | 176 | 54 | 69 % | S-0213a : 1426.62 m² > 8 % sur 2 m, 553.76 m² > 12 % sur 0,5 m, 1876.0 m² > 5 % ; trottoir |
| TQ-BOR-007 | majeur | fabrication | implemente | 504 | 54 | 89 % | K-0592 : pas de sol sous l'élément à s = 3.1 m (30 sondes) |
| TQ-SOL-001 | majeur | description | implemente | 1410 | 22 | 98 % | S-0166a : 2 arête(s) < 5 mm, 0 sommet(s) hors grille |
| VAL-LIG-002 | majeur | les_deux | implemente | 258 | 19 | 93 % | ML-5253 : largeur fabriquée 166 mm pour 120 mm ; aire peinte +108.4 % de l'attendu |
| TQ-MQG-014 | majeur | fabrication | implemente | 389 | 14 | 96 % | ML-0121 : 1.223 m² sur bordure, 0.000 m² sur caniveau |
| VAL-FLE-001 | majeur | les_deux | implemente | 36 | 10 | 72 % | route 6 voies 1/2 : dernières flèches des voies voisines décalées de 22.54 m (profil commun) |
| VAL-ZEB-003 | majeur | les_deux | implemente | 12 | 9 | 25 % | MP-5282 : intervalle d'extrémité (début) 1.15 m pour g = 0.50 m (K-0388) ; intervalle d'extrémité (… |
| VAL-COV-006 | majeur | description | implemente | 41 | 8 | 80 % | MP-0860 extrémité A (K-0380) : A-0380-1 sans BEV décrite |
| VAL-JCT-010 | majeur | les_deux | implemente | 48 | 8 | 83 % | reviree : MP-6101 B : A-0631-1 sans BEV |
| DET-KRB-015 | majeur | les_deux | implemente | 7 | 7 | 0 % | ligne 675 tronçons 47-49 -> K… : plage abaissée LiDAR de 3.0 m (vue ≤ 0,04, encadrée de 0.11 / 0.11) sans abaissé décrit s… |
| GA-ILO-001 | majeur | description | implemente | 7 | 3 | 57 % | I-0056 (sans zébra) : îlot typé refuge sans traversée, largeur minimale 0.43 m : type ou largeur à revoir |
| MQ-PP-002 | majeur | description | implemente | 22 | 3 | 86 % | MP-5170 : groupe R12 le plus proche à 9.3 m |
| GA-TRO-006 | majeur | description | implemente | 3 | 2 | 33 % | K-0238 : vue jusqu'à 0.64 m (A2), longée par une clôture sur 0 % ; côtés ['acces_riverain', 'parki… |
| MQ-LEF-004 | majeur | description | implemente | 8 | 2 | 75 % | MT-8006 : feu à 0.65 m en aval ; peinte/hypothèse à 3.65 m du passage MP-5189, angle 18.9° (feu tri… |
| TQ-SOL-014 | majeur | fabrication | partiel | 10 | 2 | 80 % | jonction 100 : pente > 4 % sur 5.5 % de l'aire (31.9 m²) |
| INF-FLE-004 | majeur | description | implemente | 11 | 1 | 91 % | MF-6015 : R1.v-2 : TD au lieu de TD_TAD (src plan2025, conflit_norme noté) |
| MQ-LIG-001 | majeur | les_deux | implemente | 25 | 1 | 96 % | ML-5193 : 22.0 m peints dans l'aire du carrefour (continue, src gam, rôle axe) |
| MQ-PP-008 | majeur | les_deux | implemente | 9 | 1 | 89 % | BEV-0352-1 / BEV-0381-5 : BEV distantes de 0.23 m |
| TQ-MQG-001 | majeur | description | implemente | 112 | 1 | 99 % | MZ-0996 : contour raster v1 ; 0 anneau(x) en escalier (src ortho2022, zone/t_stationnement) |
| TQ-MQR-005 | majeur | fabrication | implemente | 388 | 1 | 100 % | ML-5253 : épaisseur min -5.01 mm, médiane 2.00 mm, écart de drapé p95 7.00 mm |
| TQ-BOR-005 | mineur | fabrication | partiel | 7398 | 189 | 97 % | K-0368/J005 : joint 8.0 mm, pas de sol derrière |
| TQ-MQG-004 | mineur | fabrication | implemente | 388 | 85 | 78 % | ML-5253 : angle min 0.4°, p5 0.4° (8 triangles) |
| VAL-IMG-007 | mineur | description | partiel | 194 | 84 | 57 % | ML-0107 : ligne/continue (src ortho2022) : NCC -0.02 avec le contraste de l'ortho 2022 |
| GA-TRO-003 | mineur | fabrication | implemente | 47 | 43 | 8 % | S-0136r : dévers fabriqué médian -3.67 % (100 % négatif, p5 -4.5, p95 -1.8 %) ; modèle décrit 3.28 % |
| TQ-SOL-003 | mineur | fabrication | partiel | 540 | 36 | 93 % | K-0213 : 12/12 sondes où un triangle chevauche le pied (s = 0.30 m) |
| GA-CHA-003 | mineur | description | implemente | 54 | 29 | 46 % | K-0341 : pente du fil d'eau 0.01 % sur 20 m (s 30-50) |
| GA-CHA-005 | mineur | description | implemente | 36 | 24 | 33 % | route 1 s135.37 voie -1 (stoc… : largeur médiane 3.25 m (min 3.25, max 3.27), 100 % hors plage |
| GA-TRO-005 | mineur | les_deux | partiel | 20 | 20 | 0 % | S-0071c : rampe R-0299-1 : pente décrite 5.45 %, mesurée 5.8 % ; palier haut plat trouvé : 0.00 m² |
| GA-CHA-001 | mineur | fabrication | implemente | 32 | 14 | 56 % | route 6 s19.39 voie 1 : /dévers/ médian 0.52 %, 99 % des nœuds hors [1 ; 4,5] % |
| GA-OBS-003 | mineur | description | implemente | 36 | 13 | 64 % | cloture_gam_029 : cloture à 0.00 m d'une bordure de chaussée |
| GA-BEV-005 | mineur | description | implemente | 12 | 12 | 0 % | BEV-0372-1 : BEV L = 0.384 sur beton_balaye (S-0340b) L = 0.363 |
| MQ-STA-004 | mineur | description | partiel | 11 | 11 | 0 % | MS-5508 : pictogramme de 0.79 m |
| MQ-LAR-002 | mineur | description | implemente | 21 | 10 | 52 % | route 6 s19.39 voie 2 : voie de droite de 2.87 m |
| GA-ABA-008 | mineur | description | implemente | 28 | 9 | 68 % | A-0339-1 :  vue 0.010 |
| DET-REG-001 | mineur | description | implemente | 17 | 8 | 53 % | MS-0897 : recalage image de 0.42 m (plan2025) |
| MQ-PP-003 | mineur | description | implemente | 12 | 6 | 50 % | MP-0860 : bandes de 3.50 m ; abaissés voisins [('A-0380-1', 4.18), ('A-0402-1', 5.18)] |
| GA-RAY-003 | mineur | description | implemente | 9 | 5 | 44 % | route 6 s0 voie -5 : rayon min 0.5 m, hors extrémités inf m |
| MQ-LAR-003 | mineur | description | implemente | 9 | 5 | 44 % | route 3 s0 voie -5 : piste de 1.87 m (min 1.84) |
| MQ-RAL-001 | mineur | description | implemente | 11 | 5 | 55 % | MS-0890 : base 0.81, hauteur 1.89, pas au voisin 2.08 m |
| DET-LIG-011 | mineur | description | implemente | 20 | 4 | 80 % | ML-0226 : modulation mesuree (trait 1.095, vide 0.707) non ramenée à la table IISR |
| GA-CHA-006 | mineur | description | partiel | 18 | 4 | 78 % | pan_AB3a_3 : panneau AB3a sur trottoir, bord bas estimé 0.90 m |
| GA-RAY-002 | mineur | description | partiel | 8 | 4 | 50 % | S_TAG (liaison 109) : rayon min 13.2 m ; 41 point(s) de nez balayé(s) : ['K-0390', 'K-0628'] |
| MQ-PP-005 | mineur | description | implemente | 11 | 4 | 64 % | MP-5189 : bandes à 24.3° des bordures d'extrémité, obliquité 0° |
| MQ-PP-013 | mineur | description | partiel | 48 | 4 | 92 % | MP-0860 A sens +1 : masque : cloture_gam_026 |
| DET-FLE-004 | mineur | description | implemente | 8 | 3 | 62 % | MF-6014 : NCC 0.714 (sans étiquette a_verifier) |
| DET-FLE-005 | mineur | description | implemente | 18 | 3 | 83 % | MF-5527 : décalé de 0.76 m du milieu de la voie 6/2 (largeur 2.73 m, décalage normatif 0.425) |
| DET-FLE-008 | mineur | description | implemente | 14 | 3 | 79 % | MF-0774 : meilleur score 0.47 (TD_TAD), posé TD_TAD (src plan2025) |
| DET-PLN-016 | mineur | description | implemente | 3 | 3 | 0 % | ML-0407 : écart médian au levé GAM ML-5401 42.7 cm |
| GA-QBU-004 | mineur | description | implemente | 4 | 3 | 25 % | K-0406 : rayon min sur la partie QUAI_BUS (1.0-6.7 m) 1.4 m |
| GA-QBU-007 | mineur | description | partiel | 5 | 3 | 40 % | K-0377 : passage MP-5257 à 4.9 m |
| MQ-FLE-008 | mineur | description | implemente | 3 | 3 | 0 % | route 1 côté -1 : flèches ['TD', 'TD_TAD', 'TD_TAG'] sans panneau C24 décrit |
| DET-FLE-007 | mineur | description | implemente | 2 | 2 | 0 % | MF-0769 : score 0.48, 2 source(s) |
| GA-ARB-005 | mineur | description | partiel | 25 | 2 | 92 % | arbre_167 : planté 2025 (projet) : tronc à 0.90 m d'une bordure de chaussée |
| GA-BEV-006 | mineur | description | partiel | 11 | 2 | 82 % | feu_REV_droite : support R12 à 0.01 m d'une BEV |
| MQ-CYC-001 | mineur | description | implemente | 2 | 2 | 0 % | ML-5228 : continue 0.25 m, 0.0 m dans le carrefour |
| MQ-CYC-012 | mineur | description | implemente | 11 | 2 | 82 % | ML-0506 : ligne de piste 0.12 m, continue, rôle axe, blanc |
| GA-CYC-005 | mineur | description | partiel | 2 | 1 | 50 % | abri_NO_0021 : abri à 0.93 m de la chaussée, piste à 0.00 m |
| GA-ILO-006 | mineur | description | implemente | 2 | 1 | 50 % | I-0628 / MP-8201 : îlot de 0.90 m dans le sens de la traversée cyclable |
| GA-QBU-005 | mineur | description | partiel | 2 | 1 | 50 % | abri_NO_0021 : abri à 0.09 m du nez de bordure |
| TQ-SOL-010 | info | fabrication | partiel | 48 | 35 | 27 % | T_00_00 : taille 50.0 m, pivot du component [0.0, 0.0] (coin SO [-150. -150.]) |
| GA-ILO-005 | info | description | implemente | 17 | 13 | 24 % | I-0297 / K-9297a : profils ['P1'], vues [0.02] (hauteur a_priori:limite_massif_p1) |
| MQ-LIG-006 | info | description | partiel | 6 | 6 | 0 % | ML-0785 : T3 colinéaire trouvée : 0.0 m |
| TQ-MQG-008 | info | fabrication | implemente | 4 | 4 | 0 % | marquages_lignes : 327 components par entité (0 au format MQ_*) ; max 722 triangles par mesh |
| MQ-LIG-005 | info | description | partiel | 6 | 2 | 67 % | ML-5402 : continue de délimitation de 5.4 m (src gam) |
| MQ-LIG-007 | info | description | implemente | 3 | 1 | 67 % | route 1 s135.37 median 1 : bord du median longé par une continue sur 2 % de 49 m |

## Règles conformes

Sans violation (44) : DET-FLE-003, DET-FLE-006, DET-LID-013, DET-LIG-010, DET-PRE-002, DET-TRV-012, DET-ZEB-009, FUS-CON-005, FUS-SCO-002, FUS-SNP-004, FUS-SRC-001, GA-BEV-002, GA-ILO-002, GA-ILO-007, GA-OBS-001, GA-OBS-002, GA-QBU-008, GA-RES-002, GA-TRO-007, INF-FLE-006, MQ-CHR-001, MQ-CYC-013, MQ-FLE-009, MQ-LEF-003, MQ-LEF-008, MQ-LEF-010, MQ-LIG-002, MQ-LIG-008, MQ-LIG-009, MQ-PP-001, MQ-PP-014, MQ-STA-001, MQ-STA-002, MQ-TRV-005, TQ-BOR-002, TQ-MQG-006, TQ-MQG-011, TQ-MQR-001, TQ-OMB-002, TQ-PCG-001, TQ-REF-002, TQ-REF-003, TQ-SOL-008, TQ-SOL-012.

Sans objet sur le site (aucune entité concernée, 5) : FUS-ASS-003, GA-ABA-006, MQ-CYC-010, MQ-RAB-002, MQ-RAB-003.

## Règles non contrôlées

| Règle | Catégorie | Raison |
|---|---|---|
| MQ-CYC-011 | contraindre | neutralisation du stationnement avant une bande ou une piste : les places de stationnement ne sont pas décrites comme entités |
| DET-KRB-014 | verifier | affinage par la marche LiDAR point à point : les dalles LAZ classées (classe 2) ne sont pas sur le PC ; la vue décrite est comparée à la marche LiDAR agrégée par VAL-KRB-005 (b) |
| TQ-VAL-001 | verifier | test de scintillement : exige 120 images TSR capturées dans l'éditeur UE (niveau PJ_2026) |
| TQ-SOL-011 | contraindre | déplacement Nanite des matériaux d'enrobé : réglage des matériaux UE, absent des fichiers |
| TQ-MQR-002 | contraindre | WPO / PDO des matériaux maîtres : réglage des matériaux UE, absent des fichiers |
| TQ-MQR-003 | contraindre | Cast Shadow, distance fields, collisions des components de marquage : réglages de l'import UE |
| TQ-MQR-004 | contraindre | réglages Nanite (position_precision, keep_percent) : appliqués après import dans UE |
| TQ-MQR-006 | contraindre | choix décalques / géométrie : pas de décalque dans la fabrication v2 (aucune donnée à contrôler) |
| TQ-OMB-001 | contraindre | Nanite partout : réglage des StaticMesh importés dans UE |
| TQ-BOR-001 | contraindre | ISM vs HISM et data packer cd0..cd6 : graphe PCG PG_Bordures dans UE |
| TQ-BOR-004 | contraindre | ombres et cache des ISM de bordure : réglages UE |
| TQ-PCG-002 | contraindre | nœud PCG Houdini Digital Asset : réglages du graphe PCG dans UE |
| TQ-PCG-003 | contraindre | densité des instances Nanite dispersées : graphes PCG d'UE |
| TQ-PCG-005 | contraindre | retouches manuelles dans UE : aucune trace dans les fichiers |
| TQ-REF-001 | contraindre | choix d'outillage (Labs Road Generator) : décision documentaire, rien à mesurer |

Les règles « generer » et « deduire_si_absent » sans action secondaire « verifier » ne sont pas contrôlées en tant que telles : leur résultat est mesuré par les règles « verifier » associées.

## Méthode

- Les USD de `fabrique_hda` sont relus en hython (`extraire_fabrication.py`) et mis en cache numpy ; le sol fabriqué est échantillonné par requête verticale exacte sur ses triangles (grille de 0,10 m du nivellement pour les pentes, cuvettes, trous et recouvrements).
- Classes de surface : partition de la description rasterisée sur la même grille ; modèle de nivellement : `nivellement_requete.Nivellement` ; OpenDRIVE : `xodr_echantillonne` et `nivellement_xodr`.
- Unité testée, seuils et limites propres à chaque règle : champs `methode`, `limites` et `mesures` de `rapport_regles.json`.
- Déterminisme : tri fixe, arrondis fixes, aucun horodatage ; deux exécutions donnent des fichiers identiques à l'octet.

