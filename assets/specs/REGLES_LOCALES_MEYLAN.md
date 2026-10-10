# Règles locales — Meylan, Grenoble-Alpes Métropole (carrefour Paquet Jardin)

Version 1.0 du 2026-10-10 · agent DOC-LOCALE · fichier machine : `assets/specs/regles_locales_meylan.json` (46 règles `LOC-*`, 48 sources).

Ces règles complètent `regles_conception.json` (règles nationales) et `regles_implantation.json`. Préséance : observation 2026 > règle locale sourcée > règle nationale > pratique d'une autre collectivité > a priori. Une règle locale ne déplace jamais un objet observé : elle fixe les valeurs par défaut des objets déduits, les gabarits des assets et les contrôles.

## Ce qu'il faut retenir

- **Gestionnaire unique : Grenoble-Alpes Métropole.** Les routes départementales lui ont été transférées le 1er janvier 2017. Aucune règle du Département de l'Isère ne s'applique à la RD 1090 dans le site (LOC-CTX-001).
- **Métropole apaisée (Meylan depuis 2022).** 30 km/h par défaut, 50 km/h seulement sur les axes marqués « 50 » : Verdun à 50, Vercors et Revirée à 30. Le `maxspeed=50` d'OSM est une valeur par défaut fausse. Aucun panneau de vitesse dans la commune. Une ellipse « 30 » (1,20 × 2,40 m, gabarit grenoblois) rappelle la limite au début de chaque rue à 30 ; elle confirme le gabarit mesuré sur le site, 2,45 × 1,28 m (LOC-VIT-001 à 004).
- **Charte Chronovélo, enfin sourcée** (présentation Métropole/SMMAG 2022, fiche 2 du guide). Piste bidirectionnelle de 4 m (3 m au minimum), rives jaunes, axe « • • — • » jaune et turquoise. Aux traversées piétonnes : fond turquoise sous le zébra et 3 barrettes « ralentissez ». Aux traversées de chaussée : 2 files de pavés jaunes. Séparateur d'au moins 0,30 m, chanfreiné au-delà de 7 cm. En 2026, la Chronovélo 1 passe par Verdun SO puis le Vercors ; Verdun NE n'est que « planifié » (LOC-CHR-001 à 009).
- **Arrêts de bus de la Métropole.** Quai de 18 à 21 cm (18 cm à La Revirée, desservie aussi par des cars). Revêtement contrasté, dalle de repérage, bande d'interception. Équipement d'un arrêt Chrono : abri, banc, corbeille et afficheur temps réel (LOC-TC-001 à 004).
- **Mobilier métropolitain gris RAL 7024.** Potelet acier Ø 88,9 mm de 1,20 ou 1,40 m avec bande blanche ; potelet à mémoire de forme Ø 90 mm de 0,90 m ; borne en mélèze de 150 × 150 mm et 1,30 m. Barrière à croix de Saint-André de 1,20 m. Arceaux vélos à 1 m d'entraxe et 0,50 m de la bordure. Mobilier de contention posé en dernier recours seulement (LOC-MOB-001 à 005, LOC-VEL-001).
- **Charte de l'arbre (2019).** Entraxe de 7 à 12 m selon le développement. Axe de l'arbre à 1,50 m au moins du bord d'une voie ; dégagement de 1,50 × 2,50 m. 2 m au moins d'une façade, des réseaux et d'un candélabre. Fosse de 15 m³, tuteurage tripode de 2 m. TPC planté de 2 à 6 m. En octobre 2026, les arbres de 2025 sont jeunes et tuteurés (LOC-VEG-001 à 007).
- **Meylan (PLUi, livret haies et clôtures).** Clôture de 1,80 m au plus sur rue, muret de 1 m au plus, base perméable à la faune. Haies diversifiées, jamais monospécifiques. Liste d'essences « Ville parc » et liste d'invasives interdites (LOC-CLO-001 et 002, LOC-VEG-005).
- **Aucune photo du carrefour après travaux** sur le web public : ni Ville, ni Métropole, ni presse accessible, ni Panoramax. Seul OSM apporte des faits de 2026, issus de relevés de terrain : revêtements neufs, béton le long des Saules Blancs, stabilisé sur la rive E du Vercors, afficheur au quai NO, traversées à feux sans bouton d'appel ni signal sonore.

## Règles par famille

### Contexte, gestion et état des ouvrages

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-CTX-001 | Les trois voies du site (avenue de Verdun RD 1090, avenue du Vercors, chemin de la Revirée) sont des voies métropolitaines : la Métropole exerce la compétence voirie depuis le 1er janvier 2015 et … | contraindre | haute | GAM_CHARTE_ARBRE, édito, p. imprimée 3 (PDF p. 2) |
| LOC-CTX-002 | Âge des ouvrages en octobre 2026 | générer | moyenne | MEY_MMV166, p. 7 (« Fin des travaux en décembre 2025 ») |
| LOC-CTX-003 | Bilan annoncé de la phase 2 (Vercors, Granier et carrefour Verdun/Vercors) : surfaces végétalisées de 1 700 à 2 400 m², trottoirs de 1 800 à 2 300 m², chaussée et îlots bitumés de 7 350 à 6 130 m², … | vérifier | moyenne | MEY_PRES_2025, p. 7 |

### Vitesses et Métropole apaisée

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-VIT-001 | Meylan applique depuis 2022 la « Métropole apaisée » : en agglomération, 30 km/h est la règle et 50 km/h l'exception, réservée aux axes signalés par un marquage « 50 » | contraindre | haute | GAM_F04, p. 7, « Connaître les règles élémentaires du code de la rue » |
| LOC-VIT-002 | Signalisation des vitesses dans la Métropole apaisée | contraindre | haute | CEREMA_MA_2020, p. 11 |
| LOC-VIT-003 | Gabarit grenoblois de l'ellipse « 30 » : 1,20 m de large sur 2,40 m de long, chiffres de 1,30 m de haut, centrée dans la voie et lisible dans le sens de circulation ; dimensions homogènes dans toute … | générer | haute | CEREMA_Z30_2023, p. 18 (« Exemples de marquages adoptés par Grenoble ») |
| LOC-VIT-004 | L'ellipse « 50 » des axes maintenus à 50 km/h est plus petite que l'ellipse « 30 » (marquage expérimental de 2016, arrêté du 17/01/2016) | contraindre | haute | CEREMA_MA_2020, p. 11 |

### Identité et aménagement Chronovélo

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-CHR-001 | Section courante d'une Chronovélo : piste bidirectionnelle de 4 m conseillés (3 m au minimum entre bordures), en enrobé noir lisse | générer | haute | GAM_F02, p. 3, § II « Aménager sur un axe Chronovélo » |
| LOC-CHR-002 | Interface piétonne (passage piéton qui traverse la piste) : les rives jaunes s'interrompent ; une bande turquoise couvre la largeur de la piste sur la largeur du passage, et les bandes blanches du … | générer | haute | GAM_REX_CHRONO, p. 9, « Les interfaces piétonnes » |
| LOC-CHR-003 | Interface routière (traversée de chaussée par la Chronovélo) : la traversée est bordée de part et d'autre par une file de pavés jaunes transversaux ; le motif d'axe « • • — • » se poursuit entre les … | générer | haute | GAM_REX_CHRONO, p. 9, « Les interfaces routières » |
| LOC-CHR-004 | Profil d'une Chronovélo le long d'une chaussée : séparateur d'au moins 0,30 m entre la piste et la chaussée ; séparateur haut chanfreiné si sa hauteur dépasse 7 cm ; bordure de chaussée en vue de … | déduire si absent | moyenne | GAM_REX_CHRONO, p. 7 (coupe « Chronovélo avec séparateur haut chanfreiné si hauteur > 7 cm ») |
| LOC-CHR-005 | Sobriété du mobilier sur une Chronovélo : aucun potelet ni chicane aux entrées et sorties de piste ni sur les traversées (strict minimum de potelets, obstacles dangereux) ; carrefours avec îlots en … | contraindre | haute | GAM_REX_CHRONO, p. 7 |
| LOC-CHR-006 | Indications directionnelles peintes sur la piste : grand numéro d'axe blanc (« 1 » pour la Chronovélo 1), flèche blanche et nom de destination, dans chaque sens, avant les bifurcations | vérifier | moyenne | GAM_REX_CHRONO, p. 9, « Les indications directionnelles » |
| LOC-CHR-007 | Station Chronovélo : totem, plan, banc et pompe, avec un marquage au sol multicolore en losanges (jaune, turquoise, rouge, noir) dans une encoche de la piste | vérifier | moyenne | GAM_CHRONO_2018, p. 20-22 (« Stations Chronovélo : totem + plan + banc + pompe ») |
| LOC-CHR-008 | Domaine d'application de l'identité Chronovélo en 2026 : la Chronovélo 1 « existante » arrive de Grenoble par la piste NO de Verdun SO, traverse la branche SO et repart par la piste du Vercors … | contraindre | moyenne | GAM_CARTE_CHRONO_2026, zoom Meylan et légende |
| LOC-CHR-009 | Couleur des traversées cyclables : vert (résine) jusqu'en 2018-2021, puis jaune Chronovélo (pavés) depuis 2021-2022 sur l'itinéraire ; le plan 2025 dessine en orange (= jaune) la nouvelle traversée … | déduire si absent | moyenne | MEY_PANNEAU_CARREFOUR, plan (carrés orange) |

### Traversées piétonnes du projet C1

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-TRV-001 | Traversée piétonne « sécurisée » au sens du projet C1 de Meylan : îlot central avec signalisation adaptée ; voie rétrécie pour inciter au ralentissement ; zébra d'au moins 2,50 m de large, … | vérifier | haute | MEY_PANNEAU_VERCORS, encadré « C'est quoi une sécurisation de traversée piétonne ? » |
| LOC-TRV-002 | Traversée type du Vercors (exemple de la piscine des Buclos, hors site) : passage de 3 m, îlot central planté à nez arrondi, refuge minéral avec deux BEV, et bandes de résine colorée (orange) le … | vérifier | moyenne | MEY_PANNEAU_VERCORS, « Exemple de la future traversée piscine des Buclos » (photomontage et plan) |
| LOC-TRV-003 | Le passage piéton marqué (bandes blanches) s'impose dans les carrefours à feux, sur les axes à 50 km/h et dans les secteurs sensibles (écoles) ; ailleurs en zone 30, il n'est pas systématique | vérifier | haute | GAM_F16, p. 5, § c) et « Je prends en compte l'accessibilité » |
| LOC-TRV-004 | Tête d'îlot séparateur à Meylan : panneau d'obligation de contourner (flèche blanche oblique sur fond bleu, B21-1) et deux balises cylindriques grises réfléchissantes (J11) sur le nez de l'îlot, … | vérifier | moyenne | MEY_PRES_2024, diapositive 32, PDF p. 30 (photo « Exemple d'aménagement sécurisé ») |

### Arrêts et gabarits des bus

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-TC-001 | Règles d'or d'un arrêt de bus accessible du réseau grenoblois : hauteur de quai de 18 à 21 cm selon le matériel (bus ou car), pour sortir la palette sans agenouillement ; revêtement de couleur … | générer | haute | GAM_F03, p. 3, « Je prends en compte l'accessibilité » |
| LOC-TC-002 | Implantation d'un arrêt : passage piéton en amont de l'arrêt (au moins 4 m), à l'arrière du bus, pour la covisibilité ; arrêts sur chaussée (en ligne), en vis-à-vis avec îlot central ou décalés avec … | vérifier | moyenne | GAM_F03, p. 3, « Arrêts » |
| LOC-TC-003 | Gabarits pour les bus : voie bus d'au moins 3,05 m ; chaussée bidirectionnelle d'au moins 6,40 m pour le croisement de deux bus sur un axe à 50 km/h (6,20 à 6,40 m hors caniveau sur un axe à 30, y … | vérifier | haute | GAM_F03, p. 4, « Concilier les enjeux TC et la vie locale » |
| LOC-TC-004 | Équipement d'un arrêt de ligne Chrono (C1) après travaux : abri, banc, corbeille, poteau d'arrêt, afficheur d'attente en temps réel, éclairage, bandes podotactiles ; à proximité : distributeur de … | déduire si absent | moyenne | OSM_2026, way/185326915 (2026-04-01), way/185326913 (2025-09-21), way/1445374292 (2026-04-13) |

### Vélos hors Chronovélo

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-VEL-001 | Arceaux vélos de la Métropole : modèle tube acier gris RAL 7024 ; au moins 4 arceaux par emplacement (3 si peu fréquenté ou contraint) ; 1 m entre arceaux ; 0,50 m de dégagement à la bordure ; de … | générer | haute | GAM_F02, p. 6-7, § IV « Proposer des solutions de stationnement » |
| LOC-VEL-002 | Aménagements cyclables hors Chronovélo : à 30 km/h, mixité sur chaussée ; à 50 km/h, séparation (bande d'au moins 1,50 m, 2 m recommandés, ou piste) ; aux carrefours à feux, sas vélos et … | vérifier | haute | GAM_F02, p. 4-6 |

### Feux

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-FEU-001 | Pratique métropolitaine : intégrer des sas vélos et supprimer les répétiteurs bas des feux tricolores | déduire si absent | faible | GAM_F02, p. 6, § 2 « La gestion des carrefours » |
| LOC-FEU-002 | Les traversées à feux du carrefour n'ont ni bouton d'appel ni répéteur sonore ou vibrant (OSM : button_operated=no, traffic_signals:sound=no, vérifiés en 2023 puis en février-mars 2026 sur le Vercors) | contraindre | moyenne | OSM_2026, node/1959022964 (2026-02-27), node/1959022961 (2026-03-07), nodes 1959022973/76 (2023-08-26), 6569623985/86 (2023-10-22) |

### Mobilier métropolitain

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-MOB-001 | Gamme métropolitaine de mobilier de contention, posée en dernier recours et jamais à titre préventif : potelet acier monobloc Ø 88,9 mm, RAL 7024, hauteur 1,20 m ou 1,40 m, avec bande de peinture … | générer | haute | GAM_F16, p. 4, « Harmoniser : tendre vers une gamme métropolitaine » |
| LOC-MOB-002 | Barrière métropolitaine : croix de Saint-André, RAL 7024, hauteur 1,20 m, longueurs de 0,80, 1,20 ou 1,50 m ; à n'employer qu'en dernier recours. | générer | haute | GAM_F16, p. 4, « Les barrières métropolitaines » |
| LOC-MOB-003 | Couleur par défaut du mobilier métallique métropolitain non relevé (potelets, arceaux, barrières) : gris graphite RAL 7024, finition mate | déduire si absent | moyenne | GAM_F16, p. 4 |
| LOC-MOB-004 | Rangement du mobilier : une bande « fonctionnelle » le long de la chaussée regroupe mobilier, signalisation, stationnements vélos et arbres ; le cheminement piéton reste libre, continu et … | contraindre | haute | GAM_F08, p. 1, 6 et 7, « Organiser : zone fonctionnelle » |
| LOC-MOB-005 | Sobriété de l'aménagement métropolitain : limiter le nombre de matériaux, de couleurs et de styles de mobilier ; supprimer le marquage non obligatoire en zone 30 (ligne axiale, passages hors … | contraindre | haute | GAM_F16, p. 4-5 |

### Éclairage

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-ECL-001 | Teinte des lanternes pour le rendu de nuit : lanternes au sodium haute pression (OSM lamp_type=high_pressure_sodium : Revirée, Verdun NE) en lumière orangée (environ 2 000 K) ; lanternes LED … | générer | faible | OSM_2026, nodes 12894130974, 12894141026, 9530354220, 9530354517 (SHP) ; 9514828418, 9514828517, 9514828717, 12887274329 (LED) |

### Matériaux et couleurs de sol

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-MAT-001 | Revêtements des espaces publics métropolitains : chaussée et piste en enrobé ; trottoirs en enrobé (observé sur Verdun SO après travaux) ou en béton clair ; cheminements le long des espaces plantés … | déduire si absent | moyenne | GAM_F19, p. 3, 4 et 7 |
| LOC-MAT-002 | Palette des couleurs de sol à usage codifié dans le site : jaune Chronovélo (rives, pavés, barrettes, points) ; turquoise (tirets d'axe Chronovélo, fond des interfaces piétonnes sur piste) ; blanc … | contraindre | moyenne | GAM_REX_CHRONO, p. 9 |

### Arbres, plantations et eau

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-VEG-001 | Entraxe des arbres d'alignement de la Métropole selon le développement : grand (plus de 25 m) 10 à 12 m ; moyen (15 à 25 m) 7 à 8 m ; petit (moins de 15 m) 7 m ; en zone de stationnement 7 m au … | contraindre | haute | GAM_CHARTE_ARBRE, p. imprimées 38-43, PDF p. 20-22 (schéma de synthèse ; « Distances en alignement ») |
| LOC-VEG-002 | Distances de plantation de la Métropole : axe de l'arbre à 1,50 m au moins du bord d'une chaussée, d'une piste cyclable ou d'un cheminement, avec un dégagement de 1,50 m de large sur 2,50 m de haut … | contraindre | haute | GAM_CHARTE_ARBRE, p. imprimées 38-39 et 46-47, PDF p. 20 et 24 (« Distances aux voies de circulation », « Distances aux réseaux aériens ») |
| LOC-VEG-003 | Plantation type d'un arbre métropolitain : fosse de 15 m³ (12 à 18 m³) en mélange terre-pierre et terre végétale ; arbre d'environ 3 m à la plantation ; tuteurage tripode ou quadripode d'environ 2 m … | générer | haute | GAM_CHARTE_ARBRE, p. imprimées 38-39, PDF p. 20 (schéma « Le bon arbre au bon endroit ») |
| LOC-VEG-004 | Un terre-plein central planté d'arbres mesure 2 à 6 m de large | contraindre | haute | GAM_CHARTE_ARBRE, p. imprimées 42-43, PDF p. 22 (« Pour un terre-plein central : prévoir 2 à 6 m de large ») |
| LOC-VEG-005 | Palette végétale de Meylan (OAP Paysage et biodiversité, ambiance « Ville parc » de la plaine) : essences locales et diversifiées, résistantes à la chaleur, caduques en majorité | contraindre | moyenne | MEY_LIVRET_HAIES, p. 8-14 (règles du PLUi, tableaux d'essences) |
| LOC-VEG-006 | Gestion de l'eau et pleine terre : chaque projet métropolitain réserve au moins 10 % de surfaces perméables en pleine terre (cap de 25 % à l'horizon 2030) ; les noues sont dimensionnées pour … | contraindre | haute | GAM_F11, p. 1 et 4 |
| LOC-VEG-007 | Les grands arbres d'alignement de Verdun NE (rive SE, environ 36 à 156 m du centre) sont des peupliers noirs (Populus nigra, port fastigié probable, 20 à 29 m d'après le LiDAR 2021) selon … | déduire si absent | moyenne | DATAGOUV_ARBRES, ids MEY00085 à MEY00100 |

### Clôtures et soutènements riverains

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-CLO-001 | Clôtures riveraines à Meylan (PLUi) : en limite du domaine public, hauteur totale de 1,80 m au plus ; muret de 1,00 m au plus, surmonté d'un dispositif à claire-voie ; portails et portillons de 1,80 … | contraindre | haute | MEY_LIVRET_HAIES, p. 9-10 (« Règles générales », « Concernant la clôture ») |
| LOC-CLO-002 | Murs de soutènement riverains : maçonnerie enduite, petit appareil de pierres sèches ou béton structuré à motifs ; enrochements interdits ; gabions seulement en soutènement et remplis de pierres … | contraindre | haute | MEY_LIVRET_HAIES, p. 10 |

### Accessibilité

| id | règle (résumé) | action | confiance | source |
|---|---|---|---|---|
| LOC-ACC-001 | Repères pour les déficients visuels : un espace partagé piétons/vélos est contrasté et séparé par un ressaut ou une bordure de 0,5 à 2 cm ; la bande de guidage podotactile n'est pas préconisée … | contraindre | haute | GAM_F02, p. 3, « Je prends en compte l'accessibilité » |

## Conflits avec les specs nationales

| id | sujet | décision |
|---|---|---|
| CF-LOC-01 | Ellipses « 30 » sur chaussée refaite | repose à l'identique seulement d'une ellipse relevée en 2022 sur une chaussée refaite en 2025 ; aucune création ailleurs |
| CF-LOC-02 | Barrettes Chronovélo | l'observé prime ; 3 barrettes seulement pour une interface Chronovélo déduite sans relevé |
| CF-LOC-03 | Hauteur des barrières | 1,20 m pour une barrière métropolitaine sans relevé ; hauteur relevée sinon |
| CF-LOC-04 | Largeur du cheminement piéton | 1,40 m reste le seuil de violation ; 2 m est la cible pour placer un objet déduit ; 1,50 m pour les objets autorisés (terrasses, mobilier commercial) |
| CF-LOC-05 | Distances des arbres | pour un arbre déduit ou issu du plan 2025 (projet métropolitain), appliquer la charte (plus contraignante) ; un arbre observé n'est jamais déplacé pour ces seules règles |

Les conflits CF-LOC-03 et CF-LOC-05 visent `regles_implantation.json`, qui n'a pas été modifié.

## Observations web (`recon/out/paquet_jardin/v2/enrichi/recensement/web/obs_web.json`)

34 observations au format OBS (identifiants `DOC-LOCALE-001` à `DOC-LOCALE-034`) : 13 confirme, 10 attribut_corrige, 6 incertain, 5 absent_de_description. Le script `construire_obs_web.py` les reconstruit et les preuves sont dans `preuves/`.

- **DOC-LOCALE-001** (web:meylan_panneau_carrefour_verdun_vercors_2025, 2025-04-03) : programme travaux carrefour. Statut confirme, lien —, confiance haute.
- **DOC-LOCALE-002** (web:meylan_ma_ville_165_p12+166_p7, 2025-10) : jeunes plantations 2025. Statut confirme, lien —, confiance moyenne.
- **DOC-LOCALE-003** (web:meylan_presentation_reunion_2025-04-03_p7, 2025-04-03) : bilan surfaces phase2. Statut incertain, lien —, confiance moyenne.
- **DOC-LOCALE-004** (web:meylan_panneau_avenue_vercors_2025, 2025-04-03) : cheminement pieton neuf rive E Vercors. Statut absent_de_description, lien —, confiance moyenne.
- **DOC-LOCALE-005** (web:gam_carte_chronovelo_2026-01, 2026-01) : itineraire chronovelo. Statut confirme, lien —, confiance moyenne.
- **DOC-LOCALE-006** (web:gam_chronovelo_reunion_publique_2018-12-04_p26, 2018) : identite chronovelo 2018. Statut incertain, lien —, confiance faible.
- **DOC-LOCALE-007** (web:osm:way/185326915@2026-04-01, 2026-04-01) : quai bus equipement. Statut attribut_corrige, lien abri_NO_0021, confiance moyenne.
- **DOC-LOCALE-008** (web:osm:way/185326913@2025-09-21, 2025-09-21) : quai bus equipement. Statut confirme, lien abri_SE_0396, confiance moyenne.
- **DOC-LOCALE-009** (web:osm:way/1445374292@2026-04-13, 2026-04-13) : arret bus sans abri. Statut confirme, lien poteau_REV_ligne42, confiance moyenne.
- **DOC-LOCALE-010** (web:osm:node/1959022964@2026-02-27, 2026-02-27) : traversee pietonne a feux. Statut confirme, lien MP-5282, confiance moyenne.
- **DOC-LOCALE-011** (web:osm:node/1959022961@2026-03-07, 2026-03-07) : traversee pietonne a feux. Statut incertain, lien MP-5189, confiance faible.
- **DOC-LOCALE-012** (web:osm:node/9592546348@2026-03-16, 2026-03-16) : passage pieton. Statut incertain, lien —, confiance faible.
- **DOC-LOCALE-013** (web:osm:way/1412130596@2026-05-14, 2026-05-14) : cheminement beton Saules Blancs. Statut attribut_corrige, lien S-0318, confiance moyenne.
- **DOC-LOCALE-014** (web:osm:way/185327130,way/699599900,way/759539695,way/1445374294,way/1445374295,way/1488785306@2026-04-13, 2026-04-13) : trottoirs enrobe neuf Verdun SO. Statut confirme, lien S-0313, confiance moyenne.
- **DOC-LOCALE-015** (web:osm:way/698843233,way/398052317@2026-04-13, 2026-04-13) : piste chronovelo 4m. Statut confirme, lien S-0321, confiance moyenne.
- **DOC-LOCALE-016** (web:osm:way/185326635@2026-04-13, 2026-04-13) : lignes de voie vercors. Statut incertain, lien —, confiance faible.
- **DOC-LOCALE-017** (web:osm:way/169866973@2026-04-13, 2026-04-13) : lignes de voie vercors. Statut incertain, lien —, confiance faible.
- **DOC-LOCALE-018 à DOC-LOCALE-034** : 17 arbres de l'inventaire métropolitain de 2023 à moins de 160 m du centre, dont 15 peupliers noirs sur Verdun NE. Statuts : 8 attribut_corrige, 5 confirme, 4 absent_de_description.

Points à reporter dans la description :

- La surface `S-0318` est décrite en enrobé. Le cheminement neuf le long des Saules Blancs est en béton clair d'après OSM (2026-05-14) : DOC-LOCALE-013.
- Le trottoir de la rive E du Vercors est absent de la description. OSM le donne en stabilisé compacté et éclairé : DOC-LOCALE-004.
- Le quai NO a un afficheur temps réel : DOC-LOCALE-007.
- Les traversées à feux n'ont ni bouton d'appel ni signal sonore : DOC-LOCALE-010 et 011, LOC-FEU-002. OSM note aussi l'absence de BEV sur la partie E du Vercors, ce qui contredit le projet et reste à vérifier.
- L'essence Populus nigra manque pour 8 arbres de Verdun NE : DOC-LOCALE-018 à 033.
- OSM porte `lane_markings=no` sur l'entrée du Vercors, ce qui contredit le plan et le levé GAM. Statut incertain : DOC-LOCALE-016 et 017.

## Documents trouvés

Téléchargements dans `data/raw/docs_web/` (ignoré par git, usage interne, jamais redistribué) : 52 fichiers, 204 Mo. La liste complète (URL, taille, licence, usage) est dans `recon/out/paquet_jardin/v2/enrichi/recensement/web/documents_web.json`.

| source | document | fichier local | octets | droits |
|---|---|---|---|---|
| GAM_GUIDE | Guide métropolitain des espaces publics et de la voirie — « Cinq principes globaux pour des aménagements locaux » (livret, 28 p.) | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Guide-metropolitain-des-espaces-public-et-de-la-voirie.pdf` | 6131979 | public, usage interne |
| GAM_F01 | Guide métropolitain des espaces publics et de la voirie, fiche n°1 « Donner envie de marcher » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-1.pdf` | 4103325 | public, usage interne |
| GAM_F02 | Guide métropolitain des espaces publics et de la voirie, fiche n°2 « Pourquoi pas à vélo ? » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-2.pdf` | 6057082 | public, usage interne |
| GAM_F03 | Guide métropolitain des espaces publics et de la voirie, fiche n°3 « Des transports en commun intégrés dans leur environnement » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-3.pdf` | 4019328 | public, usage interne |
| GAM_F04 | Guide métropolitain des espaces publics et de la voirie, fiche n°4 « Vivre et se déplacer serein dans la ville à 30 » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-4.pdf` | 4955125 | public, usage interne |
| GAM_F05 | Guide métropolitain des espaces publics et de la voirie, fiche n°5 « La voiture bien utilisée » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-5.pdf` | 5021312 | public, usage interne |
| GAM_F06 | Guide métropolitain des espaces publics et de la voirie, fiche n°6 « Je prends en compte l'accessibilité » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-6.pdf` | 2073345 | public, usage interne |
| GAM_F07 | Guide métropolitain des espaces publics et de la voirie, fiche n°7 « Usages d'aujourd'hui et de demain » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-7.pdf` | 3021024 | public, usage interne |
| GAM_F08 | Guide métropolitain des espaces publics et de la voirie, fiche n°8 « Un espace fonctionnel agréable à vivre au quotidien » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-8.pdf` | 5590619 | public, usage interne |
| GAM_F09 | Guide métropolitain des espaces publics et de la voirie, fiche n°9 « Pendant le chantier, la vie continue » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-9.pdf` | 1832063 | public, usage interne |
| GAM_F10 | Guide métropolitain des espaces publics et de la voirie, fiche n°10 « Nature : une valeur ajoutée au projet » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-10.pdf` | 9066071 | public, usage interne |
| GAM_F11 | Guide métropolitain des espaces publics et de la voirie, fiche n°11 « L'eau de pluie, une richesse locale » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-11.pdf` | 6020475 | public, usage interne |
| GAM_F12 | Guide métropolitain des espaces publics et de la voirie, fiche n°12 « Paysage : différents plans à préserver » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-12.pdf` | 4940115 | public, usage interne |
| GAM_F13 | Guide métropolitain des espaces publics et de la voirie, fiche n°13 « Je participe à la protection de la santé » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-13.pdf` | 687140 | public, usage interne |
| GAM_F14 | Guide métropolitain des espaces publics et de la voirie, fiche n°14 « Concerter » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-14.pdf` | 3188019 | public, usage interne |
| GAM_F15 | Guide métropolitain des espaces publics et de la voirie, fiche n°15 « Un patrimoine vivant » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-15.pdf` | 4958196 | public, usage interne |
| GAM_F16 | Guide métropolitain des espaces publics et de la voirie, fiche n°16 « Pour un meilleur partage de l'espace public : les nouveaux réflexes » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-16.pdf` | 2014829 | public, usage interne |
| GAM_F17 | Guide métropolitain des espaces publics et de la voirie, fiche n°17 « Grille d'analyse et d'évaluation » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-17.pdf` | 12977480 | public, usage interne |
| GAM_F18 | Guide métropolitain des espaces publics et de la voirie, fiche n°18 « De la demande à la réponse : co-construction Métropole/commune » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-18.pdf` | 4584637 | public, usage interne |
| GAM_F19 | Guide métropolitain des espaces publics et de la voirie, fiche n°19 « Faire mieux avec moins » | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espaces-publics-Fiche-19.pdf` | 1113687 | public, usage interne |
| GAM_RGV | Règlement général de voirie métropolitaine — dispositions administratives (Grenoble-Alpes Métropole, 06/07/2018) | `data/raw/docs_web/grenoblealpesmetropole/Reglement-general-de-voirie-metropolitaine.pdf` | 1410052 | public, usage interne |
| GAM_CHARTE_ARBRE | Charte de l'arbre — guide technique en faveur de la protection et du développement du patrimoine arboré (Grenoble-Alpes Métropole, 2019) | `data/raw/docs_web/biodiversite_aura/Charte-de-l-Arbre-Grenoble-Alpes-Metropole.pdf` | 5534522 | public, usage interne |
| GAM_REX_CHRONO | « Chronovélo et tramway à Grenoble : quelles solutions retenues » — Grenoble-Alpes Métropole et SMMAG, webinaire Cerema « Tramway et aménagements cyclables » du 29/11/2022 | `data/raw/docs_web/cerema/5_rdvmob_velos_tramway_rex_grenoblealpesmetropole.pdf` | 5694261 | public, usage interne |
| GAM_CHRONO_2018 | Projet Chronovélo, réunion publique du 4 décembre 2018 (Grenoble-Alpes Métropole) | `data/raw/docs_web/cluq/Projet-Chronovelo-GAM-reunion-publique-04122018-V2.pdf` | 10136386 | public, usage interne |
| GAM_CARTE_CHRONO_2026 | Carte « Axes Chronovélo » (janvier 2026), Grenoble-Alpes Métropole | `data/raw/docs_web/grenoblealpesmetropole/Carte-Chronovelo-janvier-2026.pdf` | 2900517 | public, usage interne |
| GAM_JTR_2018 | L. Faure (Grenoble-Alpes Métropole), « Métropole apaisée et aménagements modes actifs », Journées techniques de la route 2018 | `data/raw/docs_web/univ_eiffel_jtr/3_Faure_Grenoble_JTR2018.pdf` | 5040460 | public, usage interne |
| GAM_ABECEDAIRE | Abécédaire de la Métropole apaisée (Grenoble-Alpes Métropole) | `data/raw/docs_web/saint_egreve/Abecedaire-Metropole-apaisee.pdf` | 6054463 | public, usage interne |
| GRENOBLE_DP_MA | Dossier de presse « Métropole apaisée » (Ville de Grenoble) | `data/raw/docs_web/grenoble_fr/dossier-de-presse-metropole-apaisee.pdf` | 751964 | public, usage interne |
| CEREMA_MA_2020 | Cerema Centre-Est, « Grenoble Métropole apaisée — évaluation du dispositif villes et villages à 30 km/h » (juillet 2020) | `data/raw/docs_web/cerema/cerema_ce_grenoble_rapport_ma_3a_vfinale.pdf` | 6144099 | public, usage interne |
| CEREMA_Z30_2023 | Cerema, « Principes d'aménagement des zones 30 », Club sécurité routière du 27/06/2023 (diffusé par la préfecture de l'Aude) | `data/raw/docs_web/aude_gouv/Cerema_principes_amenagements_zone_30_23-06-27.pdf` | 2930610 | public, usage interne |
| MEY_PANNEAU_CARREFOUR | Panneau « Aménagement carrefour Verdun/Vercors » (Ville de Meylan, Métropole, SMMAG) | `data/raw/docs_web/meylan_fr/Panneau-Amenagement-carrefour-Verdun-Vercors.pdf` | 852064 | public, usage interne |
| MEY_PANNEAU_VERCORS | Panneau « Aménagement avenue du Vercors » (définition d'une traversée sécurisée ; exemple de la traversée piscine des Buclos) | `data/raw/docs_web/meylan_fr/panneau-amenagement-avenue-du-vercors.pdf` | 847085 | public, usage interne |
| MEY_PANNEAU_GRANIER | Panneau « Aménagement avenue du Granier » | `data/raw/docs_web/meylan_fr/panneau-amenagement-avenue-du-granier.pdf` | 1014367 | public, usage interne |
| MEY_PANNEAU_C1 | Panneau générique « Travaux d'amélioration de la ligne C1 » | `data/raw/docs_web/meylan_fr/Panneau-generique-travaux-d-amelioration-ligne-C1.pdf` | 854403 | public, usage interne |
| MEY_PRES_2024 | Réunion publique du 14/05/2024, 1re phase du réaménagement Vercors-Granier (Métropole, Meylan, SMMAG) | `data/raw/docs_web/meylan_fr/Presentation-reunion-publique-14-05-24.pdf` | 3053426 | public, usage interne |
| MEY_PRES_2025 | Réunion publique du 03/04/2025, seconde phase du réaménagement des avenues Vercors et Granier | `data/raw/docs_web/meylan_fr/presentation-reunion-C1-03-04-25.pdf` | 1291352 | public, usage interne |
| MEY_MMV164 | Meylan ma ville n°164 (journal municipal) | `data/raw/docs_web/meylan_fr/MMV-164-etet-2025.pdf` | 1308109 | public, usage interne |
| MEY_MMV165 | Meylan ma ville n°165 (journal municipal) | `data/raw/docs_web/meylan_fr/MMV-165.pdf` | 1329526 | public, usage interne |
| MEY_MMV166 | Meylan ma ville n°166 (journal municipal) | `data/raw/docs_web/meylan_fr/MMV-166-decembre25-janvier26.pdf` | 2039889 | public, usage interne |
| MEY_MMV167 | Meylan ma ville n°167 (journal municipal) | `data/raw/docs_web/meylan_fr/MMV-167-fevrier-mars-2026.pdf` | 1766007 | public, usage interne |
| MEY_MMV168 | Meylan ma ville n°168 (journal municipal) | `data/raw/docs_web/meylan_fr/MMV-168-juin-ete-26.pdf` | 13413187 | public, usage interne |
| MEY_PAGE_C1 | Page « Ligne C1+ » (meylan.fr/311-ligne-c1.htm) et pages travaux (actualités 1108, 1129, 1227 expirées) | (page web) |  | public, usage interne |
| MEY_CHARTE_URBA | Charte communale d'urbanisme de Meylan (septembre 2026) | `data/raw/docs_web/meylan_fr/Charte-urba-2026.pdf` | 13678757 | public, usage interne |
| MEY_LIVRET_HAIES | « Quelle haie, quelle clôture pour mon jardin ? » — cahier pédagogique (Ville de Meylan, CEM ; extraits du PLUi métropolitain et de l'OAP Paysage et biodiversité) | `data/raw/docs_web/meylan_fr/Livret-haies-et-clotures.pdf` | 2252589 | public, usage interne |
| DATAGOUV_ARBRES | Patrimoine arboré du territoire métropolitain (Grenoble-Alpes Métropole), jeu archivé | `data/raw/docs_web/data_gouv_arbres/patrimoine_arbore.geojson` | 12884869 | ODbL |
| OSM_2026 | OpenStreetMap, extrait Overpass (base du 2026-05-31) autour du carrefour | `recon/out/paquet_jardin/v2/enrichi/recensement/web/preuves/osm_extrait_site_2026-05-31.json` | 163012 | ODbL |
| BOAMP_C1 | Avis BOAMP 24-127427 « Travaux de réaménagement des avenues du Vercors et du Granier – Meylan » (marché 2024-TX-ACP-0331, 3 lots) | (page web) |  | public, usage interne |
| GAM_PANNEAUX_VELO | Affiche « À vélo : les panneaux de signalisation à connaître » (Grenoble-Alpes Métropole) | `data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Panneaux-de-signalisation-velo.pdf` | 139764 | public, usage interne |

## Lacunes

- Charte graphique Chronovélo officielle (cotes des pavés, barrettes, points, teintes RAL) : non publiée ; reconstituée depuis GAM_REX_CHRONO p. 9 et GAM_F02 p. 3, cotes du site (MQ-CHR-001).
- Guide de conception cyclable et catalogue des aménagements cyclables de la Métropole (cités dans la bibliographie de la fiche 2) : introuvables en ligne.
- Volume « dispositions techniques » du règlement de voirie métropolitain et cahier des prescriptions générales assainissement : non trouvés.
- Référentiel des espaces publics de la Ville de Grenoble (2014), cité par la charte de l'arbre : non trouvé.
- SMMAG : aucun schéma directeur d'accessibilité (SDA-Ad'AP) ni guide des quais publié ; règles de quai tirées de la fiche 3 du guide métropolitain.
- DCE du marché 2024-TX-ACP-0331 (CCTP : matériaux, bordures, mobilier « spécifique », essences) : consultation close, accès par formulaire sur marches-publics.info ; non consulté.
- Département de l'Isère : sans objet (routes départementales transférées à la Métropole le 1er janvier 2017).
- Photos du carrefour après travaux (sept. 2025 - oct. 2026) : aucune trouvée (meylan.fr, grenoblealpesmetropole.fr, Place Gre'net, Le Dauphiné Libéré non accessible, Panoramax : seules les photos IGN du 2026-07-28 à 129-212 m au sud) ; OSM cite une photo Mapillary 4411579125519625 du quai NO (API à jeton, non consultée).
- OAP Paysage et biodiversité (carnet « Vallée de l'Isère amont ») et règlement écrit du PLUi : non téléchargés (extraits repris par le livret de Meylan).
