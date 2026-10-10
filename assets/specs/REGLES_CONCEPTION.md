# Règles de conception de la voirie (v1.1, 10 octobre 2026)

Ce document résume `regles_conception.json`, la spec de règles qui contraint la fabrication de la chaussée du carrefour « Paquet Jardin » (Meylan). Le JSON est la référence ; ce fichier sert à le lire. Contrôle : `python recon/pcg/specs_outils/valider_regles.py` (il vérifie aussi que ce résumé suit le JSON).

## À quoi servent ces règles

Contraindre la description (Claude), la fabrication (Houdini 22, HDAs pj_*) et la pose (UE 5.8, PCG) de la chaussée, des marquages, des bordures et des abords par les règles de conception et de marquage officielles, et poser par la norme les éléments que la détection n'a pas trouvés. Les marquages sont fabriqués en static meshes, jamais repris d'un raster.

Chaque règle a la même forme, utilisable par un générateur et par un contrôleur :

| Champ | Contenu |
|---|---|
| `id` | identifiant stable (`MQ-FLE-003`) ; les identifiants fusionnés restent dans `alias` |
| `famille, sous_famille` | regroupement (23 familles) |
| `enonce` | la règle en français |
| `parametres` | valeurs lisibles par machine ; l'unité est le suffixe du nom de clé (`distance_m`, `pente_pct`) |
| `condition` | quand elle s'applique, en termes d'entités de la scène |
| `action` | `generer`, `contraindre`, `verifier` ou `deduire_si_absent` (plus `actions_secondaires`) |
| `source, sources_secondaires` | document, article ou page, URL ; code renvoyant à la liste des sources |
| `confiance` | haute, moyenne ou faible |
| `applicabilite` | immédiate, partielle ou données nouvelles, avec les données manquantes |
| `conflits, notes` | conflits arbitrés (`CF-xx`) et remarques |

## En chiffres

- **255 règles** dans 23 familles : 237 retenues en v1.0 sur 278 proposées par 4 recherches (43 doublons fusionnés), puis 18 ajoutées et 13 corrigées en v1.1 après une critique de complétude.
- Actions : générer 91, contraindre 69, vérifier 62, déduire si absent 33.
- Confiance : haute 105, moyenne 138, faible 12.
- Applicabilité à la v2 actuelle : immédiate 221, partielle 32, données nouvelles 2.
- 28 conflits arbitrés ; 101 sources, dont 37 PDF officiels ou publics téléchargés dans `data/raw/normes/` (non versionnés) ; liste complète en fin de document.

| Famille | Règles | Objet |
|---|---|---|
| Lignes longitudinales | 12 | Lignes axiales, de délimitation et de rive ; présignalisation et rabattement. |
| Lignes d'effet, arrêt et priorité | 14 | Lignes d'effet des feux, ligne d'arrêt virtuelle, STOP et cédez-le-passage, cohérence entre feux et marquage. |
| Passages piétons | 11 | Existence, largeur, nombre de bandes, îlots, visibilité des traversées. |
| Flèches, triangles et inscriptions | 13 | Flèches directionnelles (type, nombre, intervalle, position, exclusions), triangles des ralentisseurs, marquages de vitesse. |
| Aménagements cyclables | 21 | Bandes, pistes, sas, traversées cyclables, doubles chevrons, largeurs et rayons cyclables. |
| Transport en commun | 14 | Couloirs bus, mot BUS, zigzags, quais et abords des arrêts. |
| Îlots, hachures et refuges | 10 | Obliques d'approche, hachures et chevrons, refuges piétons, bordures d'îlots. |
| Stationnement | 6 | Neutralisation près des passages, places longitudinales, en épi, PMR, livraisons. |
| Largeurs et gabarits | 4 | Largeurs des voies générales et des couloirs bus, hauteurs libres. |
| Profil de la chaussée | 4 | Dévers, forme du profil en travers, fil d'eau, points bas. |
| Trottoirs et accessibilité | 13 | Largeur libre, dévers, pentes, paliers, ressauts, revêtements, obstacles. |
| Abaissés et BEV | 20 | Abaissés de traversée, entrées charretières, bandes d'éveil de vigilance. |
| Bordures et rayons | 7 | Vue des bordures selon le contexte, compatibilité des niveaux, rayons d'angle, giration. |
| Assainissement | 6 | Avaloirs, tampons, regards, noues. |
| Fosses d'arbres | 4 | Fosses, grilles et paillages. |
| Détection et déduction | 27 | Détection image et pose par la norme des éléments non détectés. |
| Fusion des sources | 5 | Priorité des sources, score, appariement, accrochage normatif, conflits. |
| Validation | 11 | Contrôles chiffrés de la scène décrite, fabriquée et rendue : cohérence avec le .xodr, nivellement, check-list de carrefour. |
| Fabrication des marquages (Houdini) | 15 | Marquages en static meshes : volume, triangulation, UV, regroupement, déduction par la norme. |
| Fabrication du sol (Houdini) | 12 | Triangulation contrainte, nivellement unique (chaussée, carrefour, caniveaux, bordures), normales, étanchéité et collision du sol. |
| Rendu UE 5.8 | 9 | Matériaux, Nanite, ombres et Lumen pour la voirie. |
| PCG et instances UE | 15 | Bordures en ISM, transport des points, Houdini Engine, workflows de référence. |
| Vérité terrain ADAS | 2 | Vérité terrain caméra et LiDAR. |

## Révision 1.1 : critique de complétude

Une critique a relu la base sous l'angle d'un carrefour urbain à feux à 4 branches (2 × 2 voies, couloirs et arrêts de bus, piste bidirectionnelle Chronovélo avec R13c, refuges, îlots, BEV) et vérifié 10 règles tirées au sort contre leurs sources : 7 conformes, 1 conforme avec une extrapolation, 2 aux valeurs mal attribuées. Ses propositions ont été contrôlées sur les PDF locaux (IISR 7e partie, Paris, Lyon, Nice, Cerema), sur Légifrance et sur le .xodr avant d'entrer dans la base ; les écarts relevés en contrôlant (« 50 » sans règle, R13c, barrettes, liaisons de la jonction) sont corrigés dans les règles elles-mêmes.

| Règle | Changement | Objet |
|---|---|---|
| MQ-PP-011 | corrigée | triangles : seul le passage surélevé (ralentisseur trapézoïdal) en est exclu, un plateau les garde |
| MQ-LEF-001 | corrigée | formule absente de l'IISR remplacée par le contenu de 117-4 C |
| MQ-LIG-007 | corrigée | l'IISR dit « peut être nécessaire » ; la ligne 3u d'un TPC physique reste prescrite |
| MQ-BUS-002 | corrigée | biseau de 3,00 m à 45° attribué à Paris (l'IISR ne le cote pas) |
| MQ-STA-005 | corrigée | dimensions des aires attribuées à Paris (l'IISR ne cote que le marquage) |
| GA-CHA-005 | corrigée | 2,70 m « acceptable » rangé en section droite ; « hors caniveau » retiré (ni Lyon ni Paris) |
| GA-QBU-003 | corrigée | tolérances 8 % / 12 % ajoutées, « ni BEV » retiré (non sourcé), références précisées |
| MQ-PP-013 | corrigée | 28 m et 45 m absents de la fiche P.4 : devenus des a priori à sourcer |
| TQ-SOL-004 | corrigée | périmètre limité à la chaussée hors jonction ; couplage des bordures renvoyé à TQ-SOL-013 |
| TQ-SOL-010 | corrigée | la déclaration UsdPhysics ne suffit pas : collision à lever après chaque import UE |
| GA-QBU-004 | corrigée | confiance ramenée à moyenne : seul « en alignement ou en avancée » est dans l'arrêté |
| MQ-LIG-003 | corrigée | variante T3 de l'axe de piste ajoutée (118-1 B), renvoi à MQ-CYC-012 |
| GA-CHA-001 | corrigée | compte des profils du .xodr corrigé (31 superelevation + 66 shape) et plage de dévers de Verdun |
| MQ-PP-014 | ajoutée | contraste tactile des traversées (arrêté 2007 modifié en 2024) |
| MQ-RAL-001 | ajoutée | triangles de dos-d'âne, coussins et plateaux (118-9) ; 14 dent_requin sans règle |
| MQ-Z30-001 | ajoutée | marquage « 30 » de rappel de zone 30 (E.1) |
| MQ-V50-001 | ajoutée | marquage « 50 » en anneau (E.3), ajout de la synthèse |
| TQ-MQG-013 | ajoutée | construction des lettres et chiffres depuis les planches D.3-D.4 (static meshes) |
| MQ-CYC-012 | ajoutée | axe et rives de la piste bidirectionnelle (118-1 B) |
| MQ-CYC-013 | ajoutée | configuration de la traversée selon l'écart piste / chaussée et les R13c (Paris, Lyon) |
| MQ-CHR-001 | ajoutée | marques jaunes Chronovélo, posées seulement sur observation |
| MQ-LEF-011 | ajoutée | hypothèse de LEF non peinte, à vérifier |
| TQ-SOL-013 | ajoutée | modèle de nivellement unique (CF-26) |
| TQ-SOL-014 | ajoutée | surface de l'aire du carrefour |
| GA-BOR-005 | ajoutée | niveaux compatibles aux fins de bordure (pointes de sol) |
| GA-ILO-007 | ajoutée | espace de 2u entre ligne d'îlot et bordure |
| TQ-BOR-007 | ajoutée | recouvrement sol / bordure / caniveau |
| TQ-MQG-014 | ajoutée | support du drapé des marques (caniveaux) |
| VAL-XOD-008 | ajoutée | cohérence avec le .xodr (roadMark, objets, signaux, Z) |
| VAL-SOL-009 | ajoutée | nivellement, drainage et interfaces (E8, E9) |
| VAL-JCT-010 | ajoutée | check-list par branche d'un carrefour à feux |

## Comment les règles se combinent avec la détection

Les valeurs posées viennent d'abord de l'observation, puis de la détection, puis de la règle. La forme d'une marque vient toujours de la norme (accrochage FUS-SNP-004) : la détection ne fournit que la pose et le type. Une règle « deduire_si_absent » ne crée un élément que s'il manque après fusion, avec src = 'regle:regles_conception.<ID>' et la confiance de la règle. Une détection fiable qui contredit une règle n'est pas écrasée : elle est étiquetée conflit_norme.

**Ordre de priorité des sources de valeurs** (le premier disponible l'emporte) :

1. valeur arbitrée par l'utilisateur (couche arbitre/, photo_utilisateur)
2. levé vectoriel GAM 2026 ou PCRS
3. détection image scorée et admissible (plan 2025 en zone refaite ou neuve, ortho 2022 en zone conservée, Panoramax datée, LiDAR en appui)
4. mesure de calibrage du site (marquages_2026, description v2)
5. valeur par défaut d'une règle de cette spec
6. a priori non sourcé (étiqueté a_priori)

**Ordre d'autorité des textes** en cas de conflit de valeurs :

1. loi et décret : Code de la route (R412-30), Code de la voirie routière (L118-5-1), décret n° 2006-1658
2. arrêtés et instructions : arrêté du 15/01/2007 modifié, IISR 3e, 6e et 7e parties
3. normes NF et EN (lues via des sources secondaires)
4. guides nationaux Cerema / Certu
5. guides de collectivités (Lyon, Paris, Nantes, Nice, Versailles Grand Parc, Montpellier)
6. pratique mesurée sur le site
7. proposition interne (convention de génération ou de contrôle)

**Score et seuils.** S = r_source × c_detection × v_temporelle ; existence fusionnée P = 1 − Π(1 − S_i). P ≥ 0,5 : posé ; 0,3 ≤ P < 0,5 : posé avec a_verifier ; P < 0,3 : rejeté, sauf si une règle deduire_si_absent l'exige.

**Ordre d'application dans le générateur :**

1. **Recalage et prétraitement** : DET-REG-001, DET-PRE-002
2. **Détection** : DET-FLE-003 à DET-FLE-008, DET-ZEB-009, DET-LIG-010, DET-LIG-011, DET-TRV-012, DET-LID-013, DET-KRB-014, DET-KRB-015, DET-PLN-016
3. **Fusion** : FUS-SRC-001, FUS-ASS-003, FUS-SCO-002, FUS-CON-005
4. **Accrochage normatif** : FUS-SNP-004, MQ-DET-003, TQ-DED-002
5. **Déduction des éléments absents, dans l'ordre des dépendances** : passages et configuration de piste (MQ-DET-004, GA-ABA-006, MQ-CYC-013) → lignes d'arrêt (MQ-LEF-001, MQ-LEF-002, MQ-LEF-005, MQ-LEF-006, MQ-DET-007, puis hypothèses MQ-LEF-011) → sas (MQ-DET-005) → flèches (INF-FLE-004, MQ-DET-001, MQ-FLE-003 à MQ-FLE-006) → lignes (MQ-LIG-003, MQ-DET-002, MQ-DET-011) → zones et ralentisseurs (MQ-DET-008, MQ-DET-009, MQ-RAL-001) → abaissés, BEV et bordures (GA-ABA-001, GA-BEV-001, GA-BEV-003, GA-CHR-001, GA-BOR-002) → profils (GA-CHA-001, GA-CHA-002)
6. **Contraintes** : règles d'action « contraindre » (exclusions, distances, largeurs)
7. **Fabrication** : nivellement unique (TQ-SOL-013, TQ-SOL-014) avant pj_bordure_pose et pj_sol ; puis familles fabrication_sol, fabrication_marquages, pcg_instances, rendu_ue
8. **Vérification** : règles d'action ou d'action secondaire « verifier », VAL-* (dont VAL-XOD-008, VAL-SOL-009, VAL-JCT-010), TQ-VAL-*

## Conflits arbitrés

| Code | Sujet | Valeurs en présence | Décision | Règles |
|---|---|---|---|---|
| CF-01 | Chartières de l'abaissé de traversée | bordures_elements : 1 chartière de 1,00 m par côté (12 % pour une T2 en vue 0,14) ; arrêté du 15/01/2007 art. 1, 1° : 5 %, 8 % sur ≤ 2 m, 12 % sur ≤ 0,50 m | 2 éléments de 1,00 m par côté (6 %), 1,50 m au minimum ; abaissés observés gardés et signalés | GA-ABA-004, GA-ABA-001 |
| CF-02 | Vue d'une entrée charretière | bordures_elements : 0,03 par défaut (0,02-0,04), pratique non sourcée ; Lyon : 5 cm au plus, vue minimale détectable | 0,045 par défaut (0,04-0,05), pour ne pas imiter un abaissé piéton sans BEV | GA-CHR-001 |
| CF-03 | Profondeur de la BEV | Cerema fiche 03 et CFPSAA : 0,5875 ; Paris : 0,605-0,61 ; bordures_elements : 0,42 par défaut ; site : 0,40-0,45 | observé d'abord ; sinon 0,5875 si le trottoir dépasse 1,90 m, 0,40 (produit 0,42) sinon ; tolérance ±0,02 | GA-BEV-003 |
| CF-04 | Mode de fusion du matériau de marquage | peinture.json : M_Marquage Masked (trous d'usure) ; recherche technique : opaque fondu vers l'enrobé | opaque ; usure par fondu vers l'enrobé avec les mêmes UV monde ; Masked seulement après mesure du coût | TQ-MQR-001 |
| CF-05 | Largeur de bande cyclable | fiche vélo 02 (2015) : 1,50 recommandée, 1,00 ponctuel ; note Cerema annexe 3 (≈ 2021) : 1,50 minimum, 2,00 recommandée | 1,50 minimum, 2,00 recommandée ; 1,00-1,20 seulement ponctuel et signalé | MQ-LAR-003 |
| CF-06 | Largeur minimale d'une voie de stockage aux feux | Paris : 2,60 m ; Lyon (présélection) : 2,50 m | 2,60 m pour le stockage aux feux ; valeurs de Lyon pour le reste | GA-CHA-005 |
| CF-07 | Modulation des lignes de délimitation en section courante | IISR : T'1 (T3 avec flèches) ; site : T3 de 0,12 sur Verdun ; recherche détection : T3 partout | modulation observée sur la même route d'abord, sinon table IISR | MQ-LIG-003 |
| CF-08 | Ligne d'effet des feux sur toute approche à feux | recherche détection : LEF inférée partout ; R412-30 et feux.json : sans LEF, l'arrêt est avant le passage piéton | LEF peinte seulement si attestée (levé, détection, plan 2025, sas) ; sinon ligne d'arrêt virtuelle non peinte ; hypothèse non peinte étiquetée a_verifier quand d'autres approches du carrefour portent une LEF (MQ-LEF-011) | MQ-LEF-001, MQ-LEF-002, MQ-LEF-011 |
| CF-09 | Distances feu / passage / LEF | recherche détection : LEF rattachée à un passage à moins de 10 m, feu 0-3 m en aval de la LEF ; Lyon : 4 m | 4 m pour les deux seuils | MQ-LEF-004, MQ-LEF-006 |
| CF-10 | Nombre de bandes d'un passage piéton | recherche détection : n = floor((W − 2·marge + vide)/(bande + vide)), marge 0,25-0,75 ; IISR + abaque Paris : W = 0,5 n + g (n + 1) | formule IISR, n = floor(W − 0,5) ; contrôle des marges d'extrémité = g ± 0,10 | MQ-PP-004, VAL-ZEB-003 |
| CF-11 | Largeur d'un passage piéton déduit | Lyon / Paris : 4,00 m ; site : 2,80-3,50 m (médiane 3,0) ; IISR : ≥ 2,50 m | 3,00 m sur le site, 4,00 m hors site, jamais sous 2,50 m | MQ-PP-003 |
| CF-12 | Longueur de présignalisation L à 50 km/h | marquages_geometrie : ligne L = 39 jugée illisible, correspondance V15/L mal alignée ; tableau IISR lu sur l'image : L = 39 m pour 40-50 km/h | L = 39 m confirmé (cellules fusionnées par paires de vitesses) | MQ-LIG-006 |
| CF-13 | Hauteur des masques dans le triangle de visibilité | recherche géométrie : 0,80 m (hypothèse) ; Cerema : aucun masque entre 0,60 et 2,30 m | 0,60-2,30 m | MQ-PP-013 |
| CF-14 | Création d'une traversée sur une branche sans détection | recherche géométrie : traversée déduite sur toute branche ; recherche marquages : rien sans preuve | création seulement sur indice (R12, abaissés en vis-à-vis, BEV, OSM) ; sinon signalement | MQ-PP-001, GA-ABA-006, MQ-DET-004 |
| CF-15 | Nombre de flèches par voie | IISR : 3, exceptionnellement 2 en ville ; recherche détection : 3 par défaut ; site : 2 | 2 sur le site, 3 ailleurs si la longueur le permet | MQ-FLE-003 |
| CF-16 | Intervalle entre flèches | Paris : ≈ 20 m ; recherche détection : 39 m (Verdun NE, 2022) ; site 2025 : 23,9 m ; Vercors : ≈ 31 m | mesure de l'approche, sinon 24 m sur le site et 20 m ailleurs ; bornes 10-39 m | MQ-FLE-005 |
| CF-17 | Position latérale d'une flèche | recherche détection : origine (pied de tige) au milieu de la voie ; CETE 2010 : boîte englobante centrée | boîte englobante centrée (décalages de MQ-FLE-006) | MQ-FLE-006, FUS-SNP-004 |
| CF-18 | Position du zigzag d'arrêt de bus | recherche détection : centré sur le poteau ; Paris : 20 m en amont, 10 m en aval | 20 m / 10 m | MQ-BUS-005, MQ-DET-009 |
| CF-19 | Marquage de repli d'une traversée cyclable | recherche détection : bandes IISR à l'homothétie 1/2 ; IISR 118-1 C (dernier alinéa) et PAMA 14 : doubles chevrons ou figurines | doubles chevrons et figurines ; les bandes 1/2 marquent un passage piéton sur piste (MQ-CYC-009) | MQ-CYC-007, MQ-CYC-009 |
| CF-20 | Largeur d'une aire de livraison | Paris : 2,00 m × 12 m (8 à 15 m) ; l'IISR ne cote pas les aires ; Lyon : 2,20-2,50 m × 12 à 15 m | 2,00 m par défaut, plage de contrôle 2,00-2,50 m | MQ-STA-005 |
| CF-21 | Dévers maximal d'un trottoir | Lyon (2010) : jusqu'à 4 % ; arrêté du 15/01/2007 : 2 % | 2 % | GA-TRO-003 |
| CF-22 | Phase des tirets d'une ligne générée | recherche marquages : ancrage sur la LEF, trait plein au contact ; recherche détection : fin aval du dernier trait sur l'ancrage | conventions équivalentes, fusionnées ; priorité phase GAM > phase_ortho > ancrage aval | MQ-DET-011 |
| CF-23 | Épaisseur des marques fabriquées | peinture.json : film de 0,4-0,6 mm, enduit 1,5-3 mm ; recherche technique : 2 mm (peinture) et 3 mm (enduit) en géométrie | 2 / 3 mm géométriques (choix de rendu documenté, cohérent avec roadMark height = 0,002 du .xodr) ; vérité terrain sur le contour | TQ-MQG-002, TQ-MQG-011 |
| CF-24 | Cotes du double chevron | marquages_geometrie.cycles : « aucune cote officielle » ; Cerema (via Nantes, Paris) : 1,35 × 0,76, trait 0,12, décalage 0,65 | ajouter un gabarit DOUBLE_CHEVRON avec ces cotes (confiance moyenne) | MQ-CYC-008 |
| CF-25 | Coupure d'un passage au droit d'un refuge | marquages_geometrie.passages_pietons.coupure_refuge : coupure sans condition ; Paris : coupure seulement si l'îlot fait ≥ 1,50 m et que la traversée se fait en deux temps | condition ajoutée (MQ-PP-006) | MQ-PP-006 |
| CF-26 | Z du pied de bordure et de la chaussée | bordures_elements.repere.z_instance : pied de bordure = fil d'eau 2021 (hors travaux) ou heightmap 2026 ; houdini/README : dessous du bloc = fil d'eau au milieu de la corde + vue − H ; TQ-SOL-004 : chaussée tirée du .xodr (écart p95 attendu 3 cm, alerte 5 cm) | un seul modèle de nivellement (TQ-SOL-013) : caniveau calé sur la chaussée fabriquée, pied de face sur le caniveau ou la chaussée ; fil d'eau mesuré et MNT seulement en contrôle (p95 ≤ 3 cm) ; niveaux incompatibles corrigés dans la description (GA-BOR-005) | TQ-SOL-013, TQ-SOL-004, GA-BOR-005 |
| CF-27 | Triangles de ralentisseur du site | IISR 118-9 B : base 0,70 m, triangles contigus ; site (GAM, plan 2025) : base 0,79-0,81 m, hauteur 1,89 m, pas 0,81-0,93 m, non contigus | géométrie observée gardée avec le drapeau ecart_IISR ; gabarit IISR pour toute déduction ; arbitrage final sur photo postérieure aux travaux | MQ-RAL-001 |
| CF-28 | Longueur des chiffres d'un marquage de vitesse en anneau | marquages_geometrie.symboles_a_vectoriser.chiffres_30_50 : ≥ 1,50 m si V ≤ 50 (118-7, inscriptions) ; IISR annexe E.3 : chiffres de 1,00 m dans une ellipse de 1,80 × 0,90 m ; site : « 50 » 1,90 × 1,00 m, « 30 » 2,45 × 1,28 m | schéma E.3 pour les marquages de vitesse en anneau ; 1,50 m minimum pour les inscriptions en lettres (BUS, ZONE 30…) ; tailles observées gardées | MQ-Z30-001, MQ-V50-001, TQ-MQG-013 |

## Ce qui s'applique tout de suite à la zone pilote ZP-01

La zone ZP-01 couvre le refuge du TPC NE, la traversée NE de Verdun, le trottoir et la piste bidirectionnelle de Verdun NE jusqu'à l'accès riverain, et les îlots du Vercors. Les règles ci-dessous tournent avec les données actuelles (les règles partielles avec leurs valeurs par défaut) : seul le code (`decrire/`, `pj_*`, graphes PCG, réglages UE) est à écrire.

| Priorité | Règles | Ce que cela corrige |
|---|---|---|
| 1 | TQ-MQG-001, TQ-MQG-002, TQ-MQG-003, TQ-MQG-004, TQ-MQG-005, TQ-MQG-007, TQ-MQG-008 | Marquages en static meshes : les marques v1 vectorisées depuis le raster (effet « pixel ») sont remplacées par des solides minces de 2 à 3 mm, triangulés proprement (plus d'aiguilles), drapés sur le sol v2 seulement. |
| 2 | TQ-MQR-001, TQ-MQR-002, TQ-MQR-003, TQ-MQR-004, TQ-MQR-006, TQ-OMB-001 | Réglages UE des marques : opaque, sans WPO, sans ombre portée ni distance field, Nanite en précision 5 avec repli exact : plus de z-fighting ni de scintillement. |
| 3 | TQ-MQG-013, MQ-RAL-001, MQ-Z30-001, MQ-V50-001 | Inscriptions et triangles en static meshes construits depuis les planches IISR (D.3-D.4, E.1, E.3) : « 30 », « 50 » et triangles de ralentisseur du site, plus aucun glyphe repris du raster. |
| 4 | FUS-SNP-004, MQ-DET-003, MQ-PP-003, MQ-PP-004, MQ-PP-006, MQ-PP-014 | Traversées NE de Verdun et du Vercors régénérées par la norme : bandes de 0,50 m, intervalle par la formule IISR, coupure conditionnelle au refuge du TPC NE, aucun contour en escalier. Contraste tactile vérifié sur chaque traversée. |
| 5 | MQ-LIG-002, MQ-LIG-003, MQ-DET-010, MQ-DET-011 | Lignes : coupure à 0,50 m des passages, rien entre ligne d'effet et passage, modulation observée, phase ancrée à l'aval. |
| 6 | GA-ABA-001, GA-ABA-002, GA-ABA-003, GA-ABA-004, GA-ABA-005, GA-BEV-001, GA-BEV-002, GA-BEV-003, GA-BEV-004, GA-ILO-001, GA-ILO-003, GA-ILO-004, GA-ILO-007 | Abaissés et BEV de la traversée NE et du refuge TPC : vue 0,02, rampants à 6 % sur deux éléments par côté (corrige bordures_elements), BEV posées selon la largeur du refuge. Bordure du refuge à 2u de sa ligne 3u, jamais dans la voie. |
| 7 | GA-CHR-001, GA-CHR-002, GA-CHR-004 | Entrée charretière surf_0265 (trottoir et piste) : vue de 0,045 m, abaissement limité, cheminement de 1,40 m conservé. |
| 8 | MQ-CYC-009, MQ-LAR-003, GA-CYC-002, GA-CYC-003, GA-ABA-010, MQ-CYC-012, MQ-CYC-013 | Piste bidirectionnelle de Verdun NE : passage piéton à l'homothétie 1/2 sur la piste, séparateurs, franchissement de bordure sans ressaut, largeurs contrôlées. Configuration de la traversée selon l'écart piste / chaussée et les R13c ; axe et rives de piste. |
| 9 | TQ-SOL-001, TQ-SOL-002, TQ-SOL-003, TQ-SOL-004, TQ-SOL-008, TQ-SOL-009, GA-CHA-001, GA-CHA-002, TQ-SOL-010 | Sol : une triangulation contrainte avec lignes de rupture, Z tiré du modèle OpenDRIVE (elevation, superelevation, shape), normales calculées avant la découpe, sol étanche. Collision cuite après chaque import UE (pilote/ue/collisions.py). |
| 10 | TQ-SOL-013, GA-BOR-005, TQ-BOR-007, TQ-MQG-014, VAL-SOL-009 | Plus de bordure flottante ni de pointe de sol : un seul nivellement (caniveau et pied de bordure calés sur la chaussée fabriquée), niveaux compatibles aux fins de bordure, sol passant sous les éléments, marques jamais posées sur une bordure ou un caniveau, contrôles E8 et E9 du contrat UE. |
| 11 | GA-TRO-001, GA-TRO-003, GA-TRO-004, GA-TRO-005, GA-RES-001, GA-RES-002 | Trottoir de Verdun NE : couloir libre de 1,40 m, dévers de 1 à 2 %, pentes, paliers et ressauts mesurés sur la géométrie fabriquée. |
| 12 | GA-ARB-003, GA-TRO-007, TQ-PCG-003 | Îlots BRF (goutte NE) et gravier (Vercors) : paillage arasé de 3 à 5 cm, aucun débordement en surface sur le cheminement. |
| 13 | TQ-BOR-001, TQ-BOR-002, TQ-BOR-003, TQ-BOR-004, TQ-BOR-005 | Bordures en ISM Nanite rigides, collision simple, joints non transparents. |
| 14 | MQ-PP-013, MQ-LEF-010, GA-CHA-006, GA-OBS-001 | Exclusions pour la végétation et le mobilier : triangles de visibilité, 30 m de visibilité des feux, hauteurs libres. |
| 15 | VAL-LIG-002, VAL-ZEB-003, VAL-KRB-005, TQ-VAL-002, MQ-DET-010, VAL-XOD-008, VAL-JCT-010 | Contrôleur : critères chiffrés pour la revue de la zone pilote. Cohérence avec le .xodr et check-list par branche. |

**Règles qui attendent des données** (elles tournent avec leurs valeurs par défaut, marquées `a_priori`, en attendant) :

| Règle | Statut | Données requises |
|---|---|---|
| MQ-LEF-011 | partielle | photo postérieure aux travaux (Panoramax ou prise de vue D3) pour confirmer chaque hypothèse |
| MQ-PP-014 | partielle | photo postérieure aux travaux pour identifier le dispositif tactile réel (bandes à relief, tapis traversant) |
| MQ-FLE-002 | partielle | plan de feux (phasage) des carrefours, non disponible ; seuls les signaux R11/R12/R13c du .xodr existent |
| GA-CYC-002 | partielle | pas des interruptions d'écoulement (photos) |
| MQ-CHR-001 | partielle | charte Chronovélo de Grenoble-Alpes Métropole (introuvable en ligne) ; photos postérieures aux travaux pour la couleur et le motif |
| MQ-CYC-007 | partielle | charte Chronovélo / guide des espaces publics de Grenoble-Alpes Métropole (introuvables) ; photos postérieures à 2025 pour la couleur et le motif des traversées refaites |
| MQ-CYC-013 | partielle | photo postérieure aux travaux pour trancher entre les cas (a) et (b) au droit des 4 R13c ; écart piste / chaussée à mesurer sur les bordures v2 |
| GA-QBU-001 | partielle | hauteur de quai propre au réseau SMMAG (inconnue) |
| MQ-BUS-003 | partielle | vectorisation des lettres BUS (marquages_geometrie.symboles_a_vectoriser) |
| MQ-STA-004 | partielle | vectorisation du pictogramme PMR |
| GA-CHA-003 | partielle | fil d'eau observé dans les zones refaites en 2025 (absent : relevé ou photos rasantes) |
| GA-TRO-006 | partielle | photos pour confirmer la présence des garde-corps |
| GA-CHR-003 | partielle | photo de l'entrée charretière (bordure élargie ou non) |
| GA-RAY-002 | partielle | gabarits des bus du réseau SMMAG / M (inconnus) |
| GA-ASS-001 | partielle | positions des avaloirs dans les zones refaites (photos, PCRS) |
| GA-ASS-004 | données nouvelles | tracé du réseau d'assainissement (plan de récolement ou PCRS des tampons) |
| GA-ASS-005 | partielle | profondeur réelle de la noue SE (MNT 2021 antérieur aux travaux) |
| GA-ARB-001 | partielle | emprise réelle des fosses des 15 arbres plantés en 2025 (photos) |
| GA-ARB-005 | partielle | essence et catégorie de développement des arbres plantés en 2025 |
| DET-FLE-006 | partielle | photos Panoramax datées pour revalider les seuils de typage |
| DET-KRB-014 | données nouvelles | LAZ LiDAR HD classés (points de classe 2) |
| DET-LID-013 | partielle | LAZ LiDAR HD classés de la dalle (non téléchargés) |
| MQ-DET-009 | partielle | photos postérieures à 09/2025 (Panoramax ou prise de vue D3) pour confirmer les zigzags |
| FUS-SRC-001 | partielle | photos Panoramax postérieures à 09/2025 ou prise de vue D3 (état après travaux) |
| TQ-VAL-001 | partielle | étalonnage des seuils sur captures UE |
| VAL-SOL-009 | partielle | positions des avaloirs dans les zones refaites (GA-ASS-001) pour les zones d'exclusion du contrôle (4) |
| TQ-MQG-009 | partielle | étalonnage sur captures UE et photos Panoramax |
| TQ-MQG-010 | partielle | photos Panoramax pour recaler les traces de roues |
| TQ-MQG-013 | partielle | vectorisation unique des planches D.3 et D.4 (PDF de l'IISR déjà dans data/raw/normes/cerema) |
| TQ-SOL-011 | partielle | vérification du bug UE-370671 en 5.8.3 |
| TQ-SOL-014 | partielle | positions des avaloirs dans l'aire du carrefour (GA-ASS-001) |
| TQ-MQR-007 | partielle | modèle de frottement Chaos du véhicule ego (à définir) |
| TQ-ADAS-001 | partielle | test du stencil Custom Depth sur un component Nanite en UE 5.8.3 |
| TQ-ADAS-002 | partielle | capteur LiDAR maison à écrire |

## Règles par famille

Colonnes : action (Act.), confiance (Conf.), applicabilité (Appl.). Le texte complet, les paramètres et les conditions sont dans le JSON.

### Lignes longitudinales (12)

Lignes axiales, de délimitation et de rive ; présignalisation et rabattement.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| MQ-LIG-001 (fusionne INF-LIG-015) | Aucune ligne longitudinale (axe, délimitation de voies, bande cyclable) n'est tracée dans l'aire d'un carrefour à feux ou à priorité à droite. | contraindre | haute | IISR7, art. 117-1 (p. 36) | immédiate |
| MQ-LIG-002 (fusionne INF-ZEB-011) | Sur une approche à feux, les lignes de délimitation de voies s'arrêtent sur la ligne d'effet des feux (LEF). | contraindre | haute | IISR7, art. 118 (p. 44) | immédiate |
| MQ-LIG-003 (fusionne INF-LIG-014) | Modulation des lignes générées depuis les bords de voie OpenDRIVE quand aucune ligne n'est levée ni détectée, en agglomération, entre voies de même sens : T3 2u si des flèches directionnelles sont posées (voies affectées ou … | générer | haute | IISR7, art. 114-3 (p. 13), 114-5 (p. 15-16), 115-3 C §5 (p. 24), 118-1 B (p. 45) | immédiate |
| MQ-LIG-004 | En amont d'un carrefour à feux, les files sont matérialisées sur environ 30 m (zone de stockage), dans le prolongement des files de l'autre côté du carrefour, lignes parallèles à la bordure. | générer | moyenne | PARIS_SH, §II.1 (p. 8) | immédiate |
| MQ-LIG-005 (fusionne INF-LIG-016, MQ-LIG-010) | Principe de valorisation : pas de ligne continue là où elle ne s'impose pas. | générer | haute | IISR7, art. 113 B §2 (p. 5), 115-3 A (p. 20-21), 115-3 C §5 (p. 24) | immédiate |
| MQ-LIG-006 | La longueur de présignalisation L dépend de V15, plafonnée en agglomération à la vitesse réglementaire : V15 de 40 à 50 km/h, L = 39 m (3 × 13) ; 60-70 : 78 m ; 80-90 : 117 m ; 100 : 156 m ; 110 : 195 m ; 120 : 234 m. | contraindre | haute | IISR7, art. 115-1 C (p. 19), tableau 115-3 A (p. 21, lu sur le rendu image de la page), tableau 115-3 B (p. 22) | immédiate |
| MQ-LIG-007 | Sur une route urbaine à 2 × 2 voies, l'IISR admet, selon les conditions de desserte, une ligne axiale continue de 3u ou 5u, ou un terre-plein peint de deux continues 3u espacées d'au moins 3u (hachures si l'espace le permet). | générer | haute | IISR7, art. 114-5 (p. 15-16) | immédiate |
| MQ-LIG-008 | Aucune ligne axiale sur une chaussée bidirectionnelle à deux voies de largeur circulable inférieure à 5,20 m. | contraindre | moyenne | PARIS_SH, §II.1 (p. 9) | immédiate |
| MQ-LIG-009 (fusionne INF-RIV-018) | En milieu urbain, la rive est matérialisée par la bordure : pas de ligne de rive le long d'une chaussée bordée, sauf si un levé ou une détection la montre. | contraindre | haute | IISR7, art. 114-5 (p. 16), 114-4 (p. 14) | immédiate |
| MQ-RAB-001 | Réduction du nombre de voies en ville (V ≤ 50 km/h) : ligne oblique de longueur L = 39 m par voie supprimée (Paris : au moins 40 m), précédée d'une continue de L/6 = 6,5 m. | générer | haute | IISR7, art. 115-3 A-B (p. 20-22), 115-4 A (p. 24) | immédiate |
| MQ-RAB-002 | Sauf exception, la voie supprimée est la plus à gauche : on rabat de la gauche vers la droite. | contraindre | haute | IISR7, art. 115-3 B §1 (p. 21) | immédiate |
| MQ-RAB-003 | Pas de flèches de rabattement sur une voie d'insertion en carrefour. | contraindre | haute | IISR7, art. 115-3 B (p. 21) | immédiate |

### Lignes d'effet, arrêt et priorité (14)

Lignes d'effet des feux, ligne d'arrêt virtuelle, STOP et cédez-le-passage, cohérence entre feux et marquage.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| MQ-LEF-001 (fusionne INF-LEF-001) | Ligne d'effet des feux : T'2 de 0,15 m, sur les seules voies commandées (MQ-LEF-003). | générer | haute | IISR7, art. 113 (p. 4), 117-4 C (p. 42) | immédiate |
| MQ-LEF-002 | Si aucune ligne d'effet n'est détectée ni décrite, la ligne d'arrêt réglementaire (vérité terrain ADAS) est juste avant le passage piéton s'il précède le feu, sinon à l'aplomb du feu. | déduire si absent | haute | CR_R412_30, présentation p. 2 (R412-30, décret n° 2019-1328) | immédiate |
| MQ-LEF-003 | La ligne d'effet ne couvre que les voies commandées par le signal. | contraindre | haute | IISR7, art. 117-4 C (p. 42) | immédiate |
| MQ-LEF-004 (fusionne INF-LEF-003, VAL-LEF-004) | Cohérence feu / ligne d'effet. | contraindre | haute | IISR6, art. 109-4 (p. 10), 110-1 §1 (p. 22) | immédiate |
| MQ-LEF-005 (fusionne INF-LEF-002) | Recul d'une ligne d'effet à générer (attestée mais non mesurée) par rapport au passage piéton aval, mesuré bord à bord, ligne parallèle au passage : 3,0 m par défaut (médiane du site). | générer | moyenne | LYON_RFX_LEF, p. 1-2 | immédiate |
| MQ-LEF-006 | Sans passage piéton, ou si le feu est à plus de 4 m du passage (cas des girations), la ligne d'effet est tracée au droit du feu. | générer | moyenne | LYON_RFX_LEF, p. 1 | immédiate |
| MQ-LEF-008 | Sur une branche à feux, on ne pose ni panneau STOP AB4 ni ligne STOP. Si un AB3a accompagne le feu, la ligne cédez-le-passage n'est pas tracée : seule la ligne d'effet des feux peut l'être. | contraindre | haute | IISR3, art. 42-9 B §2 et §4 (p. 9-10) | immédiate |
| MQ-LEF-009 | Ligne d'effet des passages piétons (T'2, 0,15 m) : facultative, entre 2 et 5 m en amont d'un passage piéton non géré par des feux ; elle ne double jamais une ligne d'effet des feux. | générer | haute | IISR7, art. 117-4 F (p. 43) | immédiate |
| MQ-LEF-010 | Les signaux doivent être visibles d'au moins 30 m pour une vitesse de référence de 50 km/h : aucun masque (végétation, mobilier, panneau) sur cette distance dans l'axe de chaque voie. | vérifier | moyenne | CEREMA_AUDIT, CF.1 (p. 13) | immédiate |
| MQ-LEF-011 | Une approche à feux n'a aucune LEF attestée alors que d'autres approches du même carrefour en portent une (pratique homogène du gestionnaire) et qu'un passage piéton précède le R11. | déduire si absent | faible | IISR7, art. 117-4 C (p. 42) | partielle |
| MQ-TRV-001 | Ligne STOP (continue de 0,50 m) : tracée chaque fois qu'un AB4 est implanté, sauf impossibilité technique, et jamais sans AB4. | générer | haute | IISR7, art. 117-4 A (p. 41) | immédiate |
| MQ-TRV-002 | Ligne cédez-le-passage (T'2 de 0,50 m) : tracée avec tout AB3a hors branche à feux. | générer | haute | IISR7, art. 117-4 B (p. 41-42) | immédiate |
| MQ-TRV-003 | Sur une route à double sens sans îlot, les lignes STOP et cédez-le-passage sont précédées, sur 10 à 20 m, d'une ligne axiale continue 2u. | déduire si absent | haute | IISR7, art. 117-4 A-B (p. 41-42) | immédiate |
| MQ-TRV-005 | Cédez-le-passage cycliste au feu (tourne-à-droite ou tout droit) : seulement le panonceau M12 sous le signal, ou un feu R19. | contraindre | haute | IISR6, art. 110 B §3 (p. 17) | immédiate |

### Passages piétons (11)

Existence, largeur, nombre de bandes, îlots, visibilité des traversées.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| MQ-PP-001 | En général, chaque branche d'un carrefour à feux a une traversée piétonne dans le prolongement des cheminements sur trottoir ; une branche sans traversée ne se justifie que pour des raisons de sécurité. | vérifier | moyenne | CEREMA_AUDIT, CF.8 (p. 15) | immédiate |
| MQ-PP-002 | Dans un carrefour à feux, une traversée matérialisée est en général équipée de signaux piétons R12, placés sur le trottoir ou le refuge de destination. | vérifier | haute | IISR6, art. 110 B §4 (p. 17), 110-2 §1-2 (p. 25) | immédiate |
| MQ-PP-003 (fusionne GA-TRV-001) | Largeur de la traversée (longueur des bandes, mesurée parallèlement à l'axe de la chaussée) : 2,50 m minimum en ville, 4,00 m en standard dans les guides (Lyon, Paris), jusqu'à 10 m pour de forts flux ou des lignes de désir. | contraindre | haute | IISR7, art. 118 (p. 44) | immédiate |
| MQ-PP-004 (fusionne INF-ZEB-010) | Bandes de 0,50 m, intervalle g constant sur une même traversée, compris entre 0,50 et 0,80 m, avec un intervalle g à chaque extrémité (bordure ou refuge) : W = 0,50 n + g (n + 1). | générer | haute | IISR7, art. 118 (p. 44) | immédiate |
| MQ-PP-005 | Le passage suit le cheminement naturel, hors courbe, au plus court. | contraindre | moyenne | LYON_RFX_PP, p. 2 | immédiate |
| MQ-PP-006 | Au droit d'un îlot, deux cas. | générer | moyenne | PARIS_SH, §II.9 (p. 16) et annexe 120b | immédiate |
| MQ-PP-008 | Les passages de deux branches contiguës ne se chevauchent pas, et leurs BEV restent écartées d'au moins 0,50 m. | vérifier | moyenne | LYON_RFX_PP, p. 2 | immédiate |
| MQ-PP-009 | Sur une branche sans feux, le passage est en retrait d'environ 2,00 m de la ligne cédez-le-passage ou de la limite de la chaussée abordée. | générer | moyenne | CEREMA_AUDIT, P.2 (p. 26) | immédiate |
| MQ-PP-011 | Passage piéton surélevé (ralentisseur trapézoïdal dont le plateau constitue le passage) : bandes de l'article 118, prolongées de 0,50 m de part et d'autre du plateau, sur les rampes ; aucun triangle (l'art. 118-9 A exclut les … | générer | haute | IISR7, art. 118 (p. 44), 118-9 A dernier alinéa et 118-9 B (p. 55) | immédiate |
| MQ-PP-013 (fusionne GA-TRV-002) | Dans le triangle de visibilité d'un carrefour ou d'une traversée, aucun masque entre 0,60 et 2,30 m de haut (stationnement, mobilier, végétation à maturité, panneaux), sauf les mâts ; le stationnement est neutralisé sur 5 m en … | contraindre | moyenne | CEREMA_AUDIT, C.3 (p. 7), P.4 (p. 27), TC.7 (p. 48) | immédiate |
| MQ-PP-014 | Chaque passage piéton porte, en plus du contraste visuel du marquage, un contraste tactile appliqué sur la chaussée ou sur le marquage, ou tout dispositif d'efficacité équivalente, qui permet de se situer sur le passage ou d'en … | vérifier | moyenne | ARR2007, art. 1, 4° (rédaction issue de l'arrêté du 8 mars 2024) : contraste tactile | partielle |

### Flèches, triangles et inscriptions (13)

Flèches directionnelles (type, nombre, intervalle, position, exclusions), triangles des ralentisseurs, marquages de vitesse.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| INF-FLE-004 (fusionne MQ-FLE-007) | Type de flèche de chaque voie entrante, déduit de l'ensemble des mouvements autorisés depuis cette voie (manœuvres 2026) : {TD} → TD, {TAG} → TAG, {TAD} → TAD, {TD, TAG} → TD_TAG, {TD, TAD} → TD_TAD. Une voie « toutes directions … | déduire si absent | haute | IISR7, art. 115-3 C, note 3 et conditions 1-2 (p. 23-24) | immédiate |
| INF-FLE-006 | Exclusions d'implantation d'une flèche : pas dans la jonction, ni sur un passage piéton ou une traversée cyclable, ni à moins de 0,50 m d'une ligne transversale, ni entre la ligne d'effet et le passage piéton. | contraindre | moyenne | LYON_RFX_LEF, p. 1 | immédiate |
| MQ-FLE-001 | Dès qu'une voie d'une approche est affectée (plus de voies en amont que de voies pour le mouvement direct), toutes les voies adjacentes du même sens reçoivent des flèches, au milieu de chaque voie et dans un même profil en … | générer | haute | IISR7, art. 115-3 C et note 3 (p. 23-24) | immédiate |
| MQ-FLE-002 | Quand un mouvement (tourne-à-gauche notamment) ou un mode est géré en phase spéciale sans îlot pour séparer son couloir, les voies portent obligatoirement des flèches directionnelles au sol. | déduire si absent | haute | IISR6, art. 110 A (p. 14), 110-1 §3 (p. 23-24) | partielle |
| MQ-FLE-003 (fusionne INF-FLE-005) | Nombre et implantation des flèches d'une voie. | générer | haute | IISR7, art. 115-3 C §2-4 (p. 24) | immédiate |
| MQ-FLE-004 | La dernière flèche se place au plus près du point d'arrêt (LEF) ou de divergence. | générer | moyenne | IISR7, art. 115-3 C §4 (p. 24) | immédiate |
| MQ-FLE-005 | L'intervalle entre flèches successives d'une même voie est constant. | générer | moyenne | IISR7, art. 115-3 C §3 (p. 24) | immédiate |
| MQ-FLE-006 | Position latérale : la flèche est centrée sur l'axe de la voie par sa boîte englobante. | générer | moyenne | CETE_SH2010, diapositive 24 « Positionnement des flèches directionnelles » | immédiate |
| MQ-FLE-008 | En cas d'affectation de voies, les flèches s'accompagnent impérativement d'un panneau C24, ou de panneaux Da30. | vérifier | haute | IISR7, art. 115-3 C (p. 23) | immédiate |
| MQ-FLE-009 | Sur une chaussée à sens unique ou en sortie de carrefour, des flèches tout droit peuvent confirmer le sens de circulation. | contraindre | moyenne | IISR7, art. 115-3 C §6 (p. 24) | immédiate |
| MQ-RAL-001 | Triangles blancs des ralentisseurs. | générer | haute | IISR7, art. 118-9 A et B (p. 55), annexe D.8 (p. 80 : triangles 0,7 × 2 m sur un ralentisseur de 4 m) | immédiate |
| MQ-V50-001 | Marquage « 50 » dans un anneau (annexe E.3) : quand la vitesse est abaissée sur l'ensemble de l'agglomération sauf certaines voies, il indique sur ces seules voies la vitesse maximale de 50 km/h, seul ou avec les panneaux. | générer | haute | IISR7, art. 118-7 (p. 53), annexe E.3 (p. 84, cotes 180 × 90 cm, chiffres 1 m × 45 cm) | immédiate |
| MQ-Z30-001 | Marquage « 30 » de rappel de zone 30 (annexe E.1 : chiffres 30 dans un anneau), posé dans l'axe de la voie, lisible dans le sens de circulation. | générer | haute | IISR7, art. 118-7 (p. 53-54), annexe E.1 « Zone 30 rappel » (p. 82) | immédiate |

### Aménagements cyclables (21)

Bandes, pistes, sas, traversées cyclables, doubles chevrons, largeurs et rayons cyclables.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-CYC-002 | Séparation piste / chaussée en agglomération : bordure de 0,15 m de haut côté chaussée, de 0,20 à 0,50 m de large (0,70 m au plus), chanfreinée côté piste. | générer | moyenne | CEREMA_ANNEXE3B, p. 9 | partielle |
| GA-CYC-003 | Séparation piste / trottoir. | générer | moyenne | CEREMA_ANNEXE3B, p. 10 | immédiate |
| GA-CYC-004 | Piste à niveau intermédiaire entre chaussée et trottoir : dénivellation de 2 à 4 cm avec la chaussée, chanfreinée à 5 pour 1 ; au moins 0,10 m sous le trottoir. | générer | moyenne | LYON_CYCL, p. 54 | immédiate |
| GA-CYC-005 | Piste longeant un arrêt de bus : elle passe derrière l'abri. | contraindre | moyenne | LYON_CYCL, p. 59-60 | immédiate |
| GA-RAY-003 | Rayon minimal d'une piste cyclable selon la vitesse de référence : 5 m en carrefour ou changement de direction (10 à 12 km/h) ; 10 m sur itinéraire secondaire en agglomération (20 km/h) ; 22 m sur itinéraire principal ou à haut … | contraindre | moyenne | CEREMA_ANNEXE3B, p. 11 « Des rayons de courbure qui optimisent les déplacements à vélo » | immédiate |
| MQ-CHR-001 | Marques jaunes de la Chronovélo (charte locale, non normative) : pavés de traversée (0,70 × 0,37 m au pas de 0,60 m), barrettes (environ 0,71 × 0,16 m, par paires au pas de 0,80 m), points d'axe (Ø 0,20 m) et ligne jaune continue … | contraindre | faible | LOC_V2DESC, groupes piste_chronovelo_barres, piste_chronovelo_axe, piste_chronovelo_bordure, traversee_cyclable_paves ; médianes recalculées le 10/10/2026 (barrettes 0,71 × 0,16 m, pas 0,78-0,82 m ; points Ø 0,20 m) | partielle |
| MQ-CYC-001 | Bande cyclable : ligne T3 5u blanche (exceptionnellement continue 3u, en cas de masque ou de virage). | contraindre | haute | IISR7, art. 114-3 (p. 13), 117-1 (p. 36) | immédiate |
| MQ-CYC-002 | Début et fin de bande : interruption sans biseau (de préférence) ou trait oblique 5u avec une coupure de 0,50 m au milieu. | générer | haute | IISR7, art. 118-1 A (p. 45) | immédiate |
| MQ-CYC-003 | Figurines vélo sur bande ou piste : en tête de l'aménagement (avec une flèche tout droit 1/2), après chaque intersection, répétées environ tous les 50 m en ville, et au droit des accès riverains ou des sorties de parking ; dans … | générer | moyenne | CERTU_VELO02, p. 2 et 4 | immédiate |
| MQ-CYC-004 | Le marquage de la bande s'interrompt sur 10 m avant un arrêt de bus, pour l'accostage au quai, et reprend quelques mètres après. | générer | moyenne | CERTU_VELO02, p. 3 | immédiate |
| MQ-CYC-005 | Sas vélo : la ligne d'effet avant est au droit ou en retrait du feu, ou c'est le passage piéton. | générer | haute | IISR7, art. 118-1 D (p. 45-46) | immédiate |
| MQ-CYC-006 | On accède au sas par une bande ou une amorce de bande : au moins 2 tirets T3 5u (environ 10 m), 1,50 m hors marquage (de 1,00 à 2,00 m), avec une figurine. | générer | haute | IISR7, art. 118-1 D (p. 46) | immédiate |
| MQ-CYC-007 (fusionne INF-CYC-012) | Traversée cyclable d'une branche de carrefour à feux : parallèle et contiguë au passage piéton, d'un seul côté (celui de la piste), sans raccourcir les bandes du passage ; largeur d'environ 2,00 m (1,50 m minimum), écart … | générer | moyenne | IISR7, art. 118-1 C (p. 45) | partielle |
| MQ-CYC-008 | Double chevron (cote Cerema reprise par Nantes et Paris ; l'IISR ne le cote pas) : 1,35 m de long, 0,76 m de large, trait de 0,12 m, second chevron décalé de 0,65 m. | générer | moyenne | NANTES_CYC, p. 6 | immédiate |
| MQ-CYC-009 | Passage piéton traversant une piste cyclable : bandes de 0,25 m (homothétie 1/2) espacées de 0,40 m (0,25 m minimum), longues d'au moins 2,50 m. | générer | moyenne | IISR7, art. 118-1 C (p. 45) | immédiate |
| MQ-CYC-010 | La figurine encadrée ne sert qu'à signaler l'entrée d'une piste ou d'une bande large sans panneau, jamais en section courante. | contraindre | moyenne | CEREMA_PAMA14, p. 9 | immédiate |
| MQ-CYC-011 | À l'approche d'un carrefour à feux, une piste peut devenir une bande jusqu'au sas (T3 3u à Paris). | contraindre | moyenne | CEREMA_AUDIT, C.4 (p. 8), AC.3 (p. 40), AC.11 (p. 43) | immédiate |
| MQ-CYC-012 | Marquage d'une piste bidirectionnelle (u = 0,03 m). | générer | haute | IISR7, art. 118-1 B (p. 45) | immédiate |
| MQ-CYC-013 | Traversée piétonne d'une branche bordée par une piste bidirectionnelle, dans un carrefour à feux. | contraindre | moyenne | PARIS_CYC2023, §III.4.1 et III.4.2 (p. 17-25) ; cas n° 1 (p. 23) et n° 2 (p. 25) | partielle |
| MQ-FLE-010 (fusionne INF-FLE-007) | Flèches pour cycles à l'homothétie 1/2 (2,00 m), posées seulement si un mouvement cyclable dirigé est établi (plan, levé). | générer | moyenne | IISR7, art. 118-1 C (p. 45) | immédiate |
| MQ-TRV-004 | Au débouché d'une piste ou d'un double-sens cyclable : cédez-le-passage cycliste (T'2 0,50 à l'homothétie 1/2 : carrés de 0,25 × 0,25 espacés de 0,25) ou STOP cycliste (continue de 0,25). | générer | moyenne | IISR7, art. 118-1 C (p. 45) | immédiate |

### Transport en commun (14)

Couloirs bus, mot BUS, zigzags, quais et abords des arrêts.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-QBU-001 | Hauteur du quai (vue de la bordure de quai) adaptée au matériel roulant : 0,21 m par défaut pour un arrêt urbain desservi seulement par des autobus, 0,18 m s'il est aussi desservi par des cars. | déduire si absent | moyenne | CEREMA_BUS2018, §3.1.2 p. 83-84 | partielle |
| GA-QBU-002 | Longueur de la partie surélevée du quai : longueur du véhicule plus au moins 1 m de chaque côté, soit 14 m pour un bus standard de 12 m et 20 m pour un articulé de 18 m, multipliée par n si n bus stationnent simultanément ; … | déduire si absent | haute | CEREMA_BUS2018, §2.1 p. 73-74 | immédiate |
| GA-QBU-003 | Raccords entre quai et trottoir : pente au plus de 5 %, tolérée à 8 % sur 2,00 m au plus et à 12 % sur 0,50 m au plus. | générer | moyenne | NICE_QUAIS, §1.2 Rappel de la réglementation, pentes (p. 3) ; §2.2.1 Longueur, raccordements (p. 5-6) ; §3.1.5 bande contrastée hors rampes (p. 13) | immédiate |
| GA-QBU-004 (fusionne MQ-BUS-006) | En milieu urbain, l'arrêt est en ligne (alignement droit) ou en avancée plutôt qu'en alvéole, sauf impossibilité technique ; de préférence après le carrefour ; jamais le long d'un trottoir en courbe. | vérifier | moyenne | ARR2007, art. 1, 12° (arrêts en alignement ou en avancée, sauf impossibilité technique) | immédiate |
| GA-QBU-005 | Dégagements sur le quai : au moins 0,90 m libre entre le nez de bordure et l'abri, 1,40 m si le passage à l'arrière n'est pas possible ; une aire de rotation de 1,50 m de diamètre ; au droit de la porte médiane (palette de 0,70 … | contraindre | haute | ARR2007, art. 1, 12° | immédiate |
| GA-QBU-006 | Bordure de quai : profil d'aide à l'accostage (type Kassel) ou bordure biaise, face lisse, contrastée avec la chaussée, posée avec précision (lacune horizontale < 5 cm). | générer | moyenne | CEREMA_BUS2018, §3.1.3 p. 85-86 et §3.2.2 p. 87 | immédiate |
| GA-QBU-007 (fusionne MQ-PP-012) | Abords d'un arrêt : stationnement interdit 5 m en amont et 5 m en aval du quai. | contraindre | moyenne | CEREMA_BUS2018, p. 64 et p. 75 | immédiate |
| GA-QBU-008 | Pas d'avaloir sous le passage des roues du bus sur l'emprise du quai et 3 m de part et d'autre (sinon : déplacer l'avaloir ou poser une bordure-avaloir). | contraindre | moyenne | NICE_QUAIS, §3.2.1-3.2.2 | immédiate |
| GA-QBU-009 | Profil du quai : éviter le cumul pente et dévers, viser un dévers de 1 % et une pente longitudinale unique d'au plus 2 % sur la zone d'attente. | générer | moyenne | CEREMA_BUS2018, §3.1.4 p. 86 | immédiate |
| MQ-BUS-001 | Couloir bus dans le sens normal : ligne T3 5u. | générer | haute | IISR7, art. 114-3 §2 (p. 13) | immédiate |
| MQ-BUS-002 | Au carrefour, le couloir bus est interrompu à l'approche : la T3 5u s'arrête avant le passage piéton et le mot BUS est posé dans le couloir, en amont du passage (schéma indicatif IISR). | générer | moyenne | IISR7, art. 118-3 B (schémas indicatifs, p. 50), 118-3 D (damier, p. 51) | immédiate |
| MQ-BUS-003 | Mot BUS : en tête du couloir et de chaque tronçon qui suit une interruption, au droit des passages piétons, et répété environ tous les 100 m ; dans l'axe du couloir, en lettres d'au moins 1,50 m de long à 50 km/h. | générer | moyenne | IISR7, art. 118-3 E (p. 51), 118-7 (p. 53) | partielle |
| MQ-BUS-004 | Couloir bus ouvert aux vélos : figurine vélo dans l'axe du couloir, juste en amont des mots BUS, tous les 100 m (couloir standard) ; en couloir élargi, figurine sur le côté droit, en alternance avec BUS tous les 50 m. | générer | moyenne | PARIS_SH, §II.2 (p. 10), annexes 101-102 | immédiate |
| MQ-BUS-005 | Zigzag d'arrêt de bus (jaune 2u, amplitude 2,50 m, période de 5 m, trait perpendiculaire de 2,50 m à chaque extrémité) : au moins 10 m, en général environ 30 m, soit environ 20 m en amont du poteau d'arrêt et 10 m en aval, … | générer | moyenne | IISR7, art. 118-3 C (p. 51) | immédiate |

### Îlots, hachures et refuges (10)

Obliques d'approche, hachures et chevrons, refuges piétons, bordures d'îlots.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-ILO-001 (fusionne MQ-LAR-005) | Un îlot ne joue le rôle de refuge piéton que s'il fait au moins 1,50 m dans le sens de la traversée (2,00 m recommandés ; Paris préconise 2,50 m ; 2,00 m minimum pour un refuge en baïonnette). | vérifier | haute | CEREMA_BEV03, p. 6 | immédiate |
| GA-ILO-002 (fusionne MQ-PP-007) | Longueur maximale d'une traversée sans refuge : 12 m en carrefour à feux, 8 m sans feux. | vérifier | moyenne | CEREMA_AUDIT, P.12-P.13 (p. 30) | immédiate |
| GA-ILO-003 | Un îlot refuge est délimité par des bordures hautes, de vue ≥ 0,12 m (T2). | générer | haute | CEREMA_BEV03, p. 6 | immédiate |
| GA-ILO-004 | Pose des deux BEV d'un refuge selon sa largeur L. De 1,50 à 1,80 m : deux BEV réduites, pas de freinage réduit à (L − 0,80) / 2. | générer | haute | CEREMA_BEV03, p. 6-8 « Implantation selon la largeur du refuge » (schémas issus de NF P98-351 révisée) | immédiate |
| GA-ILO-005 (fusionne MQ-ILO-004) | Un îlot destiné surtout à protéger les piétons a des bordures hautes (GA-ILO-003). | déduire si absent | haute | IISR7, art. 117-2 B Îlots (p. 37-38) | immédiate |
| GA-ILO-006 | Un refuge utilisé par des cyclistes traversant en deux temps fait au moins 2,00 m dans le sens de la traversée (longueur d'un vélo), et environ 2,50 m pour les vélos cargos ou avec remorque. | vérifier | faible | INTERNE, déduction : encombrement d'un vélo | immédiate |
| GA-ILO-007 | Îlot ou terre-plein bordé le long d'une voie. | contraindre | haute | IISR7, art. 117-2 A (p. 37) et B (p. 37-38) | immédiate |
| MQ-ILO-001 | Approche d'un îlot sans changement du nombre de voies : ligne oblique de déport de longueur n × L pour n files déportées, et L/2 pour des têtes d'îlot symétriques (déport d'une demi-file), soit 19,5 m à 50 km/h. | générer | haute | IISR7, art. 115-4 B (p. 25), 113-2 note (1) (p. 8) | immédiate |
| MQ-ILO-002 | Pratique parisienne quand l'oblique IISR (MQ-ILO-001) ne tient pas dans la géométrie : l'îlot est annoncé par une continue 3u d'environ 30 m, tangente aux bordures, qui écarte l'usager peu à peu. | générer | moyenne | PARIS_SH, §II.7 (p. 13) | immédiate |
| MQ-ILO-003 | Zones neutralisées autour des îlots : contour continu 3u, puis un espace non peint de 2u entre le contour et les hachures ou la bordure. | générer | haute | IISR7, art. 117-2 A-B (p. 37-38) | immédiate |

### Stationnement (6)

Neutralisation près des passages, places longitudinales, en épi, PMR, livraisons.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| MQ-STA-001 (fusionne GA-STA-001, MQ-LEF-007) | Aucune place de stationnement motorisé sur la chaussée dans les 5 m en amont d'un passage piéton, dans le sens de circulation (places pour cycles et engins de déplacement personnel admises) ; obligation pour tous travaux … | contraindre | haute | CEREMA_PAMA10, art. L118-5-1 CVR (loi LOM, art. 52), p. 1 et 4 | immédiate |
| MQ-STA-002 (fusionne GA-STA-002) | Stationnement longitudinal : emplacements délimités en T'2 2u blanc (bleu en zone bleue) ; place standard de 2,00 × 5,00 m, largeur de 1,80 m minimum marquage compris et de 2,20 m maximum ; places en talon d'au moins 4,50 m ; … | générer | moyenne | IISR7, art. 118-2 A (p. 46-47) | immédiate |
| MQ-STA-003 | Stationnement en bataille ou en épi (45° ou 60°) : ligne T'2 2u à au moins 4,50 m de la bordure (5,00 m conseillés), avec des amorces ou des limites de places. | générer | moyenne | IISR7, art. 118-2 A a (p. 46) | immédiate |
| MQ-STA-004 (fusionne GA-STA-003) | Place réservée PMR : largeur d'au moins 3,30 m (épi ou bataille), pente et dévers inférieurs à 2 %, raccordée au trottoir par un passage d'au moins 0,80 m ; au moins 2 % des places de chaque zone (arrondi au supérieur). | générer | haute | ARR2007, art. 1, 8° | partielle |
| MQ-STA-005 | Aire de livraison (IISR) : délimitation jaune 2u, en T'2 si elle est périodique ; si elle est permanente, une seconde ligne continue accolée à au moins 1u, à l'extérieur de l'emplacement ; croix diagonale jaune continue 2u ; mot … | générer | moyenne | IISR7, art. 118-2 C (p. 48-49), marquage seulement | immédiate |
| MQ-STA-006 | Arrêt ou stationnement gênant : ligne jaune 2u sur le dessus de la bordure, ou en rive à au moins 2u du trottoir ; en T'2 pour le stationnement, continue pour l'arrêt. | générer | haute | IISR7, art. 118-2 B (p. 47) | immédiate |

### Largeurs et gabarits (4)

Largeurs des voies générales et des couloirs bus, hauteurs libres.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-CHA-005 (fusionne MQ-LAR-001) | Contrôle des largeurs de files de circulation générale en agglomération, mesurées d'axe en axe des lignes (Paris). | vérifier | moyenne | LYON_DIM, p. 3-6 (sens unique, double sens, double voie, présélection) | immédiate |
| GA-CHA-006 | Hauteur libre d'au moins 3,80 m au-dessus de la chaussée et d'au moins 2,20 m au-dessus des cheminements piétons (panneaux, potences, branches, abris, enseignes). | vérifier | haute | ARR2007, art. 1, 6° c et d (2,20 m) | immédiate |
| MQ-LAR-002 | Couloir bus : largeur normale de 3,00 à 3,50 m (Paris : 3,00 m minimum hors marquage, 3,20 m souhaitable). | vérifier | haute | CERTU_VELO09, p. 3 | immédiate |
| MQ-LAR-003 (fusionne MQ-LAR-004, GA-CYC-001) | Largeurs cyclables, mesurées hors marquage et hors caniveau. | contraindre | haute | CEREMA_ANNEXE3B, p. 7 (pistes), p. 16-17 (bandes, tampon de 0,50 m) | immédiate |

### Profil de la chaussée (4)

Dévers, forme du profil en travers, fil d'eau, points bas.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-CHA-001 (fusionne TQ-SOL-005) | Dévers de la chaussée revêtue à défaut d'observation : 2,5 % vers le fil d'eau en section courante (2,0 % sur béton) ; minimum 1,5 %, maximum 4 % localement. | déduire si absent | moyenne | LYON_DIM, p. 11 « Valeurs des profils en long et en travers » | immédiate |
| GA-CHA-002 | Forme du profil en travers à défaut d'observation. | déduire si absent | faible | LYON_DIM, p. 11 pour la valeur | immédiate |
| GA-CHA-003 | Le fil d'eau a une pente longitudinale d'au moins 0,5 % (normale 1 %). | contraindre | moyenne | LYON_DIM, p. 11, chaussée / long : mini 0,5 % dans le caniveau, normal 1 % | partielle |
| GA-CHA-004 | Aucun point bas sans exutoire : tout minimum local de la surface revêtue (fil d'eau, carrefour gauchi, quai en avancée, abaissé) a un avaloir à moins de 1 m ; sinon on pose un avaloir ou on corrige les pentes. | vérifier | moyenne | VGP_ASS, §5.3 Implantation des avaloirs | immédiate |

### Trottoirs et accessibilité (13)

Largeur libre, dévers, pentes, paliers, ressauts, revêtements, obstacles.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-OBS-001 | Le mobilier est posé hors du cheminement de 1,40 m (GA-TRO-001). | contraindre | haute | ARR2007, art. 1, 6° c, d, e | immédiate |
| GA-OBS-002 | Bornes, potelets et poteaux sur cheminement : hauteur d'au moins 0,50 m et, à 0,50 m, une largeur ou un diamètre d'au moins 0,28 m (abaque : un poteau de 1,10 m peut avoir 0,06 m de diamètre, une borne de 0,60 m doit faire au … | vérifier | haute | ARR2007, art. 1, 6° b-c et annexe 3 (modifiée en 2012) | immédiate |
| GA-OBS-003 | Barrière de protection piétonne, en dernier recours seulement (limite avec la chaussée non détectable faute de 5 cm de dénivelé hors zone de rencontre, îlot séparateur traversé en deux temps, abords d'école) : posée à l'arrière … | contraindre | moyenne | LYON_RFX_BARRIERE, p. 1-2 | immédiate |
| GA-RES-001 | Tout ressaut sur un cheminement fait au plus 2 cm, à bord arrondi ou chanfreiné ; 4 cm au plus avec un chanfrein à 1 pour 3. | vérifier | haute | ARR2007, art. 1, 5° Ressauts | immédiate |
| GA-RES-002 | Les trous et fentes dans le sol des cheminements (grilles d'avaloir, grilles d'arbre, caniveaux à fente, joints ouverts) ont un diamètre ou une largeur inférieurs à 2 cm. | vérifier | haute | ARR2007, art. 1, 6° a | immédiate |
| GA-RES-003 | Tampons, grilles et cadres sont posés au niveau du sol fini, affleurants ; charnière du tampon dans le sens de la circulation, ou du côté haut sur un terrain en pente. | générer | moyenne | VGP_ASS, §4.6 Dispositifs de fermeture | immédiate |
| GA-TRO-001 (fusionne GA-ARB-004) | Le cheminement piéton a une largeur libre de tout obstacle d'au moins 1,40 m, réductible à 1,20 m seulement en l'absence de mur ou d'obstacle des deux côtés. | contraindre | haute | ARR2007, art. 1, 3° Profil en travers | immédiate |
| GA-TRO-002 | Largeur de trottoir par défaut pour un trottoir neuf sans relevé : 2,00 m. | déduire si absent | moyenne | CEREMA_BUS2018, p. 62-63 | immédiate |
| GA-TRO-003 | Le dévers du cheminement est au plus de 2 %, au moins de 1 % pour l'écoulement, et orienté vers la chaussée. | générer | haute | ARR2007, art. 1, 3° (≤ 2 %) | immédiate |
| GA-TRO-004 (fusionne TQ-SOL-006) | La pente longitudinale d'un cheminement est inférieure à 5 %. | contraindre | haute | ARR2007, art. 1, 1° Pentes | immédiate |
| GA-TRO-005 | Si la pente dépasse 4 %, un palier de repos horizontal de 1,20 × 1,40 m hors obstacle est aménagé en haut et en bas de chaque plan incliné, et tous les 10 m en cheminement continu. | générer | haute | ARR2007, art. 1, 1° et 2° Paliers de repos | immédiate |
| GA-TRO-006 | Un garde-corps permettant de prendre appui est obligatoire le long de toute rupture de niveau de plus de 0,40 m bordant un cheminement. | vérifier | haute | ARR2007, art. 1, 1° (garde-corps, rupture de niveau > 0,40 m) | partielle |
| GA-TRO-007 | Le sol des cheminements n'est ni meuble ni glissant et ne comporte pas d'obstacle à la roue : pas de gravillons, BRF, galets ni stabilisé non compacté dans la bande de cheminement. | contraindre | haute | DEC2006, art. 1 I 1° | immédiate |

### Abaissés et BEV (20)

Abaissés de traversée, entrées charretières, bandes d'éveil de vigilance.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-ABA-001 (fusionne INF-ABA-022) | Au droit de chaque traversée piétonne, marquée ou non, et des deux côtés (trottoir ou refuge bordé), un abaissé a une partie abaissée d'au moins 1,20 m de large, en vue 0,02 ± 0,005 m (ressaut ≤ 2 cm, 4 cm avec chanfrein à 1 pour … | déduire si absent | haute | ARR2007, art. 1, 4° (réécrit par l'arrêté du 8 mars 2024) et 5° | immédiate |
| GA-ABA-002 | La partie abaissée couvre toute la largeur du passage piéton marqué (longueur des bandes) et tient dans celle-ci ; le marquage n'est jamais moins large que la BEV, et la BEV ne dépasse jamais du marquage. | générer | haute | CEREMA_BEV03, p. 2 | immédiate |
| GA-ABA-003 | Configuration de l'abaissé selon la largeur du trottoir. | générer | moyenne | ARR2007, art. 1, 4° (passage horizontal ≥ 0,80 m si la largeur le permet) et 1° (pentes) | immédiate |
| GA-ABA-004 | Longueur de chaque rampant latéral (chartière plus surface du trottoir) : L ≥ Δh / 0,05 recommandé ; au minimum L ≥ Δh / 0,08 avec L ≤ 2,00 m ; jamais 12 % sur plus de 0,50 m. | contraindre | haute | ARR2007, art. 1, 1° | immédiate |
| GA-ABA-005 | La zone abaissée en vue 0,02 est horizontale en long, avec un dévers ≤ 2 % vers la chaussée. | générer | haute | ARR2007, art. 1, 1°, 2° et 3° | immédiate |
| GA-ABA-006 | Placement d'une traversée déduite (MQ-DET-004) : dans le prolongement naturel du cheminement, hors des arrondis de bordure (sur la tangente droite), au plus court, perpendiculaire à la chaussée ; deux traversées ne se chevauchent … | contraindre | moyenne | LYON_RFX_PP, p. 1-2 | immédiate |
| GA-ABA-007 | Dans un angle portant deux traversées, la bordure remonte à une vue d'au moins 0,05 m entre les deux abaissés, et la BEV y est interrompue. | générer | moyenne | CEREMA_BEV03, p. 4-5 (cas n° 1 et n° 2) | immédiate |
| GA-ABA-008 | L'abaissé et la BEV restent praticables par tous les temps et libres de flaques. | contraindre | moyenne | LYON_DIM, p. 14 (vue 0 cm : fil d'eau non garanti) | immédiate |
| GA-ABA-009 | Une traversée sur chaussée surélevée (plateau) sans dénivellation détectable reçoit quand même une BEV ; on conserve de préférence un ressaut de 2 cm en limite du trottoir, et la règle des 50 mm de vue s'applique. | générer | moyenne | CEREMA_BEV03, p. 8 | immédiate |
| GA-ABA-010 | Le franchissement d'une bordure par une piste cyclable (traversée cyclable, raccord piste / chaussée) se fait sans ressaut, raccordé à 0 avec continuité du matériau, ou par deux caniveaux CS1/CS2 accolés. | générer | moyenne | CEREMA_ANNEXE3B, p. 12 « Quelles solutions pour franchir les seuils ? » | immédiate |
| GA-BEV-001 (fusionne MQ-PP-010) | Une BEV est posée au droit de chaque traversée équipée d'abaissés (marquée ou non), de chaque traversée surélevée et des traversées de voies ferrées : face à la traversée, parallèle à la bordure, sur toute la partie de bordure de … | déduire si absent | haute | ARR2007, art. 1, 4° | immédiate |
| GA-BEV-002 | Pas de freinage : 0,50 ± 0,02 m entre le nez de la bordure (arête avant haute) et la première ligne de plots de la BEV. | vérifier | haute | CEREMA_BEV03, p. 2 | immédiate |
| GA-BEV-003 | Profondeur de la BEV (perpendiculaire à la bordure) : standard 0,5875 m en voirie ; largeur réduite 0,40 m (produits de 0,42 m) admise si le trottoir fait 1,90 m ou moins au droit de la traversée. | déduire si absent | haute | CFPSAA_BEV, §II.3 Dimensions, §III | immédiate |
| GA-BEV-004 | Sur un abaissé en arrondi, les BEV sont posées bout à bout, sans joint au sommet du côté opposé à la chaussée ; l'écart entre les plots extrêmes de deux bandes consécutives ne dépasse pas 110 mm. | générer | haute | CEREMA_BEV03, p. 3-4 | immédiate |
| GA-BEV-005 | La BEV et le mobilier sur cheminement sont contrastés visuellement avec leur support : contraste de luminance visé de 70 % à l'état neuf, contrôlé par les albédos de materiaux_sol.json : (Lmax − Lmin) / Lmax ≥ 0,70. | vérifier | haute | ARR2007, annexe 1 (contraste visuel) | immédiate |
| GA-BEV-006 | Le poteau d'un feu piéton (répétiteur sonore, bouton) se place dans le prolongement du marquage du passage, contre le bord de la BEV et non sur elle, hors du couloir de 1,40 m. | contraindre | moyenne | CEREMA_BEV03, p. 9 | immédiate |
| GA-CHR-001 | La bordure d'une entrée charretière a une vue au plus de 5 cm, qui est aussi la vue minimale détectable et évite la confusion avec un abaissé piéton. | déduire si absent | moyenne | LYON_DIM, p. 13 (vue maximale 5 cm, variante 13 cm sur 50 cm) | immédiate |
| GA-CHR-002 | Sur un trottoir d'au moins 2,50 m, l'abaissement d'une entrée charretière se limite à 1,10 m de profondeur depuis la bordure, de préférence dans la bande technique, et laisse au moins 1,40 m de cheminement plat (dévers ≤ 2 %). | générer | moyenne | LYON_RFX_CHR, p. 1, conditions d'aménagement | immédiate |
| GA-CHR-003 | Sur un trottoir étroit (moins de 2,50 m), deux options. | générer | moyenne | LYON_RFX_CHR, p. 2, options 1 et 2 | partielle |
| GA-CHR-004 | Des entrées charretières distantes de moins de 2,50 m sont couplées en un profil continu unique. | générer | moyenne | LYON_RFX_CHR, p. 2 | immédiate |

### Bordures et rayons (7)

Vue des bordures selon le contexte, compatibilité des niveaux, rayons d'angle, giration.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-BOR-001 | Hors des abaissés, toute limite entre espace piéton et espace circulé a une vue d'au moins 0,05 m, hauteur détectable à la canne. | vérifier | haute | CEREMA_BEV03, p. 2 (bordure de 50 mm détectable) | immédiate |
| GA-BOR-002 | Vue de la bordure de trottoir en limite de chaussée : minimum 0,05 m, courante 0,14 m (T2, 0,12 à 0,16), maximum 0,16 à 0,18 m (0,16 encore franchissable par un VL, 0,18 protection effective). | déduire si absent | moyenne | LYON_DIM, p. 16 « Les bordures en limite de chaussée » | immédiate |
| GA-BOR-003 | Bordure de fond de stationnement : vue courante 0,11 m (minimum 0,05, maximum 0,16). | déduire si absent | moyenne | LYON_DIM, p. 15 et p. 20 (butte-roue) | immédiate |
| GA-BOR-004 | Bande surélevée franchissable longeant la chaussée (bande cyclable surélevée, surlargeur) : chanfrein de 2 pour 1 vers la chaussée et vue au plus de 0,04 m, abaissée au droit des passages piétons. | générer | moyenne | LYON_DIM, p. 14 « Les chanfreins entre la bande et la chaussée » | immédiate |
| GA-BOR-005 | Compatibilité des niveaux aux extrémités et aux changements de bordure. | vérifier | moyenne | LOC_HOU_README, § Sol « Pente maximale » (revue UE du 10/10 : pointes de sol de 6 à 23 cm jusqu'à 89° à 24 fins de bordure, niveaux incompatibles entre bordures voisines, ex. P1 K-9297a contre le bateau K-0385) | immédiate |
| GA-RAY-001 | Rayon de la bordure d'angle en carrefour urbain sans géométrie relevée. 3 à 4 m : très serré, rues sans bus ni PL. 5 à 6 m : serré, centre dense, VL. 8 à 10 m : normal, bus ou PL occasionnels. 12 m : fluide, lignes de bus … | déduire si absent | moyenne | LYON_DIM, p. 10 « Giration des véhicules, calcul des rayons de courbure » | immédiate |
| GA-RAY-002 | Vérification de giration avec le véhicule de projet de la branche. | vérifier | moyenne | LYON_DIM, p. 10-11 « Liste des véhicules les plus contraignants » | partielle |

### Assainissement (6)

Avaloirs, tampons, regards, noues.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-ASS-001 | Des avaloirs sont posés à chaque point bas et au moins un pour 350 m² de surface de ruissellement collectée. | déduire si absent | moyenne | VGP_ASS, §5.3 Implantation des avaloirs | partielle |
| GA-ASS-002 | Prototypes d'avaloir. | générer | moyenne | VGP_ASS, §5.2 (tableau des dimensions) et §5.4 (grilles, classes, avaloir 1100/300) | immédiate |
| GA-ASS-003 | Classe de résistance EN 124 selon la zone. | générer | moyenne | EN124, groupes 1 à 4 | immédiate |
| GA-ASS-004 | Regards de visite sur collecteur : Ø 1000 mm (800 mm à défaut), idéalement tous les 50 m et au plus tous les 75 à 80 m, obligatoires à chaque changement de direction, de pente ou de section ; dans l'axe de la voie circulée ou au … | déduire si absent | moyenne | VGP_ASS, §4.2, §4.4, §4.6 | données nouvelles |
| GA-ASS-005 | Ouvrages de surface. | générer | moyenne | LYON_DIM, p. 23-25 (fossés, noues, tranchées) | partielle |
| GA-ASS-006 | Le fil d'eau est placé de préférence en limite de chaussée. | générer | moyenne | LYON_DIM, p. 20 « Fil d'eau - Positionnement » | immédiate |

### Fosses d'arbres (4)

Fosses, grilles et paillages.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| GA-ARB-001 | Fosse d'arbre (volume enterré) : 9 m³ en terre végétale, 12 m³ en terre-pierre (6 m³ en exception pour un petit développement) ; largeur minimale 1,80 m, profondeur maximale 1,50 m. | déduire si absent | moyenne | MTP_FOSSE, fiche 1.2.4 | partielle |
| GA-ARB-002 | Grille d'arbre : dimensions extérieures d'au moins 1,60 m, centrée sur le tronc, en 2 ou 4 éléments ; évidement central d'au moins Ø 0,55 m ou couronne amovible ; fentes de moins de 2 cm ; cadre périphérique scellé affleurant ; … | générer | moyenne | LYON_ARBRES, p. 9 « Les grilles et le platelage bois » | immédiate |
| GA-ARB-003 | Paillage de pied d'arbre ou d'îlot : minéral (sablé, pouzzolane, gravier) de 5 à 10 cm sur géotextile ; organique (broyat, BRF) de 8 à 15 cm. | générer | moyenne | LYON_ARBRES, p. 5-8 (mulchs minéraux et organiques) | immédiate |
| GA-ARB-005 | Distances de plantation d'un arbre déduit ou replanté : à une limite de propriété privée, tronc à au moins 2,00 m si l'arbre dépasse 2 m de haut, 0,50 m sinon (Code civil, art. 671-672) ; côté chaussée, l'entourage de l'arbre … | contraindre | moyenne | MTP_PLANTATION, p. 1 (Code civil art. 671-672 ; entourages 2 × 2 et 3 × 3 m) | partielle |

### Détection et déduction (27)

Détection image et pose par la norme des éléments non détectés.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| DET-FLE-003 | Détection des flèches rectifiée par voie sur l'ortho 2022. | vérifier | moyenne | TESTS_DETECT, tm_voies.py, tm_voies.json, planche_detections.png (test B) | immédiate |
| DET-FLE-004 | Même détecteur rectifié sur le raster du plan projet 2025 inversé, rééchantillonné à 5 cm en coordonnées de voie par l'affine de georef.json : source privilégiée pour la position et le type des flèches de 2025 (acceptation à NCC … | vérifier | haute | TESTS_DETECT, tm_plan.py, tm_plan.json (test C) | immédiate |
| DET-FLE-005 | A priori de réseau pour la détection des flèches : fenêtre latérale de ±0,5 m autour du milieu de voie (±1,5 m sur voie large), cap selon la tangente ±4°. Une détection appuyée par une autre dans la voie adjacente de la même … | contraindre | haute | IISR7, art. 115-3 C, conditions 1 à 4 (p. 23-24) | immédiate |
| DET-FLE-006 | Typage des flèches par parties, pas par argmax du gabarit entier. | vérifier | moyenne | TESTS_DETECT, tm_voies.json | partielle |
| DET-FLE-007 | Recherche libre invariante en rotation, hors réseau OpenDRIVE (parkings, intérieur de jonction) : balayage de cap au pas de 3° puis affinage à 0,5°, fenêtre d'origine de ±3 m, NCC par FFT. Acceptation seulement si NCC ≥ 0,80, ou … | vérifier | moyenne | TESTS_DETECT, tm_fleches.py, tm_resultats.json (test A) | immédiate |
| DET-FLE-008 | Glyphe hors bibliothèque : dans une boîte de 4,0 × 1,3 m centrée sur la voie, si au moins 15 % des pixels dépassent 25 DN de top-hat et que la meilleure NCC IISR reste < 0,70, ou si le test trident (DET-FLE-006) est positif, … | vérifier | moyenne | TESTS_DETECT, tridents vus sur l'ortho 2022 (Vercors et MF-0401) | immédiate |
| DET-KRB-014 | Affinage des bordures par la marche de hauteur LiDAR : tous les 0,5 m, profil perpendiculaire à la bordure v2 sur ±0,6 m, points de classe 2 (ou MNT 2021 à 10 cm), ajustement z = a + b·x + h·sigmoïde((x − x0) / 0,03). | vérifier | moyenne | LOC_RELIEF, méthode §5 (dessus − fil d'eau par tronçon de 1 m), résidu 1,76 cm | données nouvelles |
| DET-KRB-015 | Détection d'un abaissé : une plage de vue ≤ 0,04 m sur au moins 1,20 m, encadrée de vues courantes ≥ 0,10 m et de transitions de 0,5 à 1,5 m (chartières), est un abaissé candidat. | vérifier | haute | ARR2007, art. 1, 4° et 5° | immédiate |
| DET-LID-013 | L'intensité LiDAR HD 2021 n'est qu'une preuve d'appui pour les marquages, jamais suffisante seule (poids 0,4). | vérifier | moyenne | LOC_LIDAR, stats_15cm.json, vols des 12/08 et 06/09/2021 | partielle |
| DET-LIG-010 | Extraction des lignes longitudinales par détection de crête (Hessienne multi-échelle) dans un couloir de ±0,40 m autour de chaque bord de voie xodr : crêtes chaînées le long de s, décalage t(s) ajusté par spline robuste, largeur … | vérifier | moyenne | LOC_VALID_XODR, écarts bords de voie / levé : p50 0,001-0,009 m, p95 0,014-0,042 m | immédiate |
| DET-LIG-011 | Classification de la modulation : binarisation (Otsu) du profil top-hat le long de la ligne ajustée, plages trait / vide, médianes comparées à la table IISR à ±10 % près. | vérifier | haute | IISR7, art. 113-1 B (tableau p. 6) | immédiate |
| DET-PLN-016 | Lignes du plan 2025 : même extracteur de crêtes sur le plan inversé (traits noirs CAO), pour la présence, le type continu / discontinu et la position (±0,10 m). | vérifier | moyenne | LOC_PLAN2025, planche MF0772_plan.png | immédiate |
| DET-PRE-002 | Canal de vraisemblance de marquage : top-hat blanc de la luminance avec un élément structurant carré plus large que la plus large marque (1,275 m pour TD_TAD) ; les tuiles contraste_5cm existantes (2 m, seuil 25) conviennent. | vérifier | haute | LOC_CONTRASTE, élément structurant 2 m, seuil 25 | immédiate |
| DET-REG-001 | Recaler tous les rasters sur le PCRS avant toute détection. | vérifier | moyenne | LIDARHD, précision annoncée : 10 cm en Z, 50 cm en XY | immédiate |
| DET-TRV-012 | Lignes transversales : test périodique 1D (pas 1,0 m, rapport cyclique 0,5, largeur 0,15) le long des positions candidates données par MQ-LEF-005 (±2 m), sur toutes les voies commandées. | vérifier | moyenne | TESTS_DETECT, lidar_contraste.py | immédiate |
| DET-ZEB-009 | Détection des zébras par périodicité : direction des bandes par le tenseur de structure du top-hat ; profil moyenné sur 60 % de la longueur de bande, le long de la normale aux bandes ; pas = pic FFT dans [0,8 ; 1,6] m (si la … | vérifier | haute | TESTS_DETECT, zebra_fft.py (test D : MP-0085, 0326, 0333, 0570, 0574, 0580, 0586) | immédiate |
| MQ-DET-001 | Une flèche directionnelle détectée seule implique un jeu complet : dans sa voie, 2 ou 3 flèches du même type à intervalle constant (MQ-FLE-003 à MQ-FLE-005) ; dans chaque voie adjacente du même sens, des flèches dans le même … | déduire si absent | moyenne | IISR7, art. 115-3 C §1-3 (p. 24) | immédiate |
| MQ-DET-002 | Des flèches impliquent des files matérialisées : générer les lignes de délimitation T3 2u entre les voies fléchées, depuis la ligne d'effet jusqu'à au moins 30 m en amont, ou jusqu'au début de l'affectation. | déduire si absent | moyenne | PARIS_SH, §II.1 (p. 8) | immédiate |
| MQ-DET-003 | Un passage piéton détecté en partie, ou issu du raster (contour en escalier), se régénère en entier, de bordure à bordure ou jusqu'à l'îlot : bandes et intervalles recalculés par MQ-PP-004, bandes parallèles à l'axe de la … | déduire si absent | moyenne | IISR7, art. 118 (p. 44) | immédiate |
| MQ-DET-004 (fusionne INF-ZEB-008, INF-ZEB-009) | Indices d'existence d'un passage piéton non détecté, par confiance décroissante : (1) un groupe de signaux piétons R12 d'une même traversée (têtes d'un même mât fusionnées à 1 m près, au moins 2 mâts), l'axe passant par les mâts … | déduire si absent | moyenne | IISR6, art. 110-2 §1-2 (p. 25) | immédiate |
| MQ-DET-005 (fusionne INF-SAS-013) | Un sas vélo est déduit si une figurine vélo est détectée ou levée entre une ligne d'effet et le passage piéton (ou dans les 5 m en amont de la LEF), ou si une bande cyclable atteint la LEF d'une approche à feux. | déduire si absent | moyenne | IISR7, art. 118-1 D (p. 45-46) | immédiate |
| MQ-DET-006 | Bande ou piste cyclable sans signalisation détectée à son entrée : poser en tête une figurine et une flèche tout droit à l'homothétie 1/2, puis une figurine après chaque intersection. | déduire si absent | moyenne | NANTES_CYC, p. 4 | immédiate |
| MQ-DET-007 (fusionne INF-CED-021) | Un panneau AB4 détecté implique une ligne STOP (continue de 0,50 m) sur toute la largeur des voies concernées ; un AB3a détecté hors feux implique une ligne cédez T'2 de 0,50 m, avec un triangle facultatif ; variante cycliste à … | déduire si absent | haute | IISR3, art. 42-2 C et E (p. 3-4) | immédiate |
| MQ-DET-008 (fusionne INF-HAC-020) | Îlot peint (polygone sans bordure) ou zone non circulée entre bords de voie divergents ou convergents, détecté ou levé sans hachures : générer le contour continu 3u, l'espace de 2u, des hachures de 0,50 m espacées de 1,35 m à … | déduire si absent | moyenne | IISR7, art. 117-2 A et schéma C3 (p. 37-38), 115-4 B (p. 25) | immédiate |
| MQ-DET-009 (fusionne INF-BUS-019) | Arrêt de bus détecté (poteau, abri, quai, signal xodr C6 ou arrêt OSM) hors couloir bus et sans zigzag : proposer un zigzag de 30 m (20 m en amont du poteau, 10 m en aval), longueur multiple de 5 m, à confirmer sur photo, car … | déduire si absent | faible | IISR7, art. 118-3 C (p. 51) | partielle |
| MQ-DET-010 | Contrôles d'artefacts : aucune ligne de voie ni ligne axiale ne traverse un passage piéton (coupure à 0,50 m), une ligne d'effet, un sas ou l'aire de conflit ; aucune marque n'en chevauche une autre (sauf damier ou figurine … | vérifier | haute | IISR7, art. 118 (p. 44), 117-1 (p. 36), 118-2 B (p. 47) | immédiate |
| MQ-DET-011 (fusionne INF-LIG-017) | Phase des tirets d'une ligne discontinue générée sans phase observée : la modulation (T3, T'1) s'ancre à l'aval (ligne d'effet, début du tronçon continu ou interruption de 0,50 m avant un passage) et se déroule vers l'amont, avec … | générer | faible | INTERNE, convention de génération | immédiate |

### Fusion des sources (5)

Priorité des sources, score, appariement, accrochage normatif, conflits.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| FUS-ASS-003 | Appariement multi-sources par classe, avec portes de distance, puis affectation hongroise sur le coût distance / porte. | contraindre | moyenne | INTERNE, proposition | immédiate |
| FUS-CON-005 | Conflits à signaler : une détection de confiance ≥ 0,6 contredit une inférence de règle ou les manœuvres 2026. | vérifier | haute | INTERNE, proposition | immédiate |
| FUS-SCO-002 | Score d'une hypothèse : S = r_source × c_detection × v_temporelle. | contraindre | moyenne | TESTS_DETECT, tests A à E (tm_voies.json, tm_plan.json) | immédiate |
| FUS-SNP-004 (fusionne TQ-DED-001) | Accrochage normatif : un contour de marque détecté ou levé (GAM, ortho, plan, vision) n'est jamais posé tel quel ; on y ajuste le modèle paramétrique normatif le plus proche. | contraindre | haute | IISR7, art. 113-1, 113-2, 115-3 C, 118 | immédiate |
| FUS-SRC-001 | Ordre de priorité des sources par attribut (existence, géométrie, type) : levé vectoriel (GAM état 2026, PCRS) > détection image scorée (plan projet 2025 dans les zones refaites ou neuves, ortho PCRS 2022 dans les zones … | contraindre | moyenne | LOC_ARCHI, §1.3 (provenance) | partielle |

### Validation (11)

Contrôles chiffrés de la scène décrite, fabriquée et rendue : cohérence avec le .xodr, nivellement, check-list de carrefour.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| TQ-VAL-001 | Test de scintillement et de z-fighting dans UE : caméra à 1,3 m, angles rasants de 2 à 10°, distances de 5 à 150 m, 120 images TSR à pose fixe et glissante. | vérifier | faible | INTERNE, méthode de projet | partielle |
| TQ-VAL-002 | Contrôles géométriques des marques en volume, dans Houdini : écart d'aire aux paramètres ≤ 0,5 % ; boîte des gabarits ≤ 1 mm ; bas de jupe ≤ z_sol − 1,5 mm en tout sommet ; dessus − sol = e_top ± 0,3 mm ; 0 m² hors sol ; angle … | vérifier | haute | LOC_MANIFEST_MQ, aires p95 0,011 %, gabarits 0,769 mm au plus | immédiate |
| VAL-COV-006 | Complétude par approche et par traversée. | vérifier | haute | INTERNE, règles « deduire_si_absent » | immédiate |
| VAL-FLE-001 | Contrôle des flèches : écart d'origine p95 ≤ 0,10 m par rapport à la référence (levé ou plan) ; écart de cap ≤ 2° ; type conforme aux manœuvres (100 %) ; recouvrement du gabarit rendu avec le masque de détection ≥ 0,6 sur l'ortho … | vérifier | haute | LOC_ARCHI, phase 2 (critères) | immédiate |
| VAL-IMG-007 | Preuve image a posteriori : la description finale est rendue à 5 cm (marquages_apercu) et chaque élément est comparé par NCC au top-hat de l'ortho (zones conservées) ou au plan inversé (zones refaites ou neuves). | vérifier | moyenne | LOC_MQ_ORTHO, marquages_apercu.py | immédiate |
| VAL-JCT-010 | Check-list par branche et par sens d'un carrefour urbain à feux à 4 branches. | vérifier | moyenne | INTERNE, assemblage de règles sourcées (extension de VAL-COV-006) | immédiate |
| VAL-KRB-005 | Contrôle des bordures : écart planimétrique p95 ≤ 0,05 m par rapport au levé GAM ; vue à ±0,02 m de la marche LiDAR pour les tronçons « mesurée » ; abaissés à 0,02 ± 0,005 m et d'au moins 1,20 m de large. | vérifier | haute | LOC_ARCHI, phase 1 | immédiate |
| VAL-LIG-002 | Contrôle des lignes : écart latéral p95 ≤ 0,05 m ; phase des tirets p95 ≤ 0,10 m ; largeur à ±0,02 m ; modulation IISR exacte ; interruption de 0,50 ± 0,10 m aux passages ; aucune ligne longitudinale non justifiée dans la … | vérifier | haute | LOC_ARCHI, phase 2 (phase p95 < 0,10 m ; latéral p95 < 0,05 m) | immédiate |
| VAL-SOL-009 | Contrôles de nivellement, de drainage et d'interfaces sur la géométrie fabriquée. | vérifier | moyenne | LOC_CONTRAT, §5 bis, contrôles E8 et E9 (revue UE du 10/10) | partielle |
| VAL-XOD-008 | Cohérence entre le .xodr et la scène fabriquée (vérité terrain ADAS). roadMark solid, broken et solid solid : type, largeur (±0,01 m) et height (= e_top, TQ-MQG-011) égaux à ceux des lignes fabriquées ; pour les discontinues, … | vérifier | moyenne | LOC_XODR, roadMark (solid 19, broken 15, solid solid 5, curb 29), objets (crosswalk 12, trafficIsland 3), signaux 1000001 (8), 1000002 (16), 1000013 (4), C6 (3), comptés le 10/10/2026 | immédiate |
| VAL-ZEB-003 | Contrôle des passages : nombre de bandes exact par rapport au levé ou à la détection et dans la table IISR ; pas à ±0,03 m ; angle à ±3° ; longueur de bande à ±0,20 m ; axe à ≤ 0,20 m ; intervalle d'extrémité aux bordures égal à … | vérifier | haute | IISR7, art. 118 (table du nombre de bandes) | immédiate |

### Fabrication des marquages (Houdini) (15)

Marquages en static meshes : volume, triangulation, UV, regroupement, déduction par la norme.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| TQ-DED-002 | Lignes discontinues trouées par des masquages (véhicules, ombres) : reconstruire toute la séquence de tirets selon la modulation retenue et la phase ajustée par moindres carrés sur les tirets observés (p95 < 0,10 m). | déduire si absent | moyenne | LOC_ARCHI, phase 2 : phase p95 < 0,10 m | immédiate |
| TQ-MQG-001 | Dans UE, remplacer tous les marquages v1 (contexte_v1.usdc, contours vectorisés depuis un raster) par la couche v2 fabriquée par pj_marquages en static meshes. | contraindre | haute | LOC_UE_README, tableau contexte (contexte_v1 : marquages v1) | immédiate |
| TQ-MQG-002 (fusionne TQ-DED-003) | Chaque marque est un solide mince : dessus à +e_top au-dessus de la chaussée le long de la normale du sol, jupe latérale descendant à −e_ancrage sous la chaussée, pas de face inférieure. e_top selon le produit, par défaut si la … | générer | moyenne | HAUC_SROH, thermoplastique : chape 3,5 ± 1,5 mm, extrudé 3,0 ± 0,5 mm, projeté ≥ 1,5 mm | immédiate |
| TQ-MQG-003 | Chaîne de SOP Houdini pour une marque : (1) Triangulate 2D (contraintes Polygons, Refine, angle minimal 25°, arête cible 0,25-0,5 m, constructions exactes) ; (2) Z évalué sur le modèle analytique de la chaussée (ou Ray SOP sur le … | générer | moyenne | SFX_TRI2D, Refine, Minimum Angle (> 30° non garanti) | immédiate |
| TQ-MQG-004 | Ne plus confiner chaque triangle de marque dans un seul triangle du sol (méthode actuelle, source d'aiguilles). | vérifier | haute | LOC_MANIFEST_MQ, controles.triangles : p5 angle_min 4,16°, 170 triangles < 1°, 1 786 < 5° | immédiate |
| TQ-MQG-005 | Draper les marques uniquement sur le sol v2 : pj_sol couvre toute la voirie du site avant pj_marquages. | contraindre | haute | LOC_MANIFEST_MQ, controles.aires.hors_sol_m2 = 1,6115 ; 15 entités hors sol (MG-0277, ML-0229, MP-0272…) | immédiate |
| TQ-MQG-006 | Une flèche ou un symbole n'est posé comme prototype rigide (point PCG + SM de bibliothèque) que si le sol sous son emprise est plan à 1 mm près ; sinon, maillage drapé propre à l'entité. | vérifier | moyenne | SPEC_MQG, gabarits TD/TAD 4,00 m, RAB 6,00 m | immédiate |
| TQ-MQG-007 | UV et attributs des marques. st = (x, y) monde en mètres, identique au mapping de l'enrobé (l'usure laisse voir le même grain). st1 = (s le long de la marque, d distance signée au contour), en mètres, par xyzdist. | générer | haute | LOC_CONTRAT, §3 (displayColor), §4 (st en m, st1 autorisé, pas de projection de dessus sur une face verticale) | immédiate |
| TQ-MQG-008 | Regrouper les marques en components USD par (tuile de 50 m, classe sémantique, matériau peinture_<couleur>_u<usure>) : un StaticMesh par groupe, de kind component, pivot au coin SO de la tuile sur le mètre entier, nom … | contraindre | moyenne | LOC_CONTRAT, §2 (component < 500 k triangles, tuiles de 32-64 m) | immédiate |
| TQ-MQG-009 | Dentelure des bords : par défaut dans le matériau (bande d < 5 mm du contour où un bruit fond la peinture vers l'enrobé, amplitude croissante avec l'usure ; usure 0 : bords nets). | générer | faible | SPEC_PEINTURE, usure.niveaux 0 à 2 | partielle |
| TQ-MQG-010 | Usure dans les traces de roues : sur les marques transversales, les flèches et les figurines d'une voie circulée, augmenter la couleur de sommet R dans deux bandes de 0,60 m centrées à ±0,80 m de l'axe de la voie (gain de 0,15 à … | déduire si absent | faible | SPEC_PEINTURE, usure.niveaux.2 « plaques arrachées dans les traces de roues » | partielle |
| TQ-MQG-011 | L'épaisseur fabriquée e_top d'une marque longitudinale égale l'attribut height du roadMark OpenDRIVE correspondant (0,002 m), à 0,1 mm près ; sinon le .xodr est mis à jour dans la même version. | vérifier | moyenne | LOC_XODR, roadMark type=solid/broken width=0.12 height=0.002 | immédiate |
| TQ-MQG-012 | Les marques fantômes (effacées) n'ont pas de volume. | générer | moyenne | SPEC_PEINTURE, rugosite.fantome_F (rugosité de l'enrobé − 0,08) | immédiate |
| TQ-MQG-013 | Construction des inscriptions (BUS, LIVRAISON, PAYANT, chiffres…). | générer | haute | IISR7, art. 118-7 (p. 53) ; annexes D.3 (p. 70), D.4 (p. 71-72), D.5-D.6 (p. 73-76), E.1 (p. 82), E.3 (p. 84) | partielle |
| TQ-MQG-014 | Support du drapé des marques : union du sol v2 et des faces supérieures des éléments posés au niveau de la chaussée (caniveaux CS, pontages, tampons). | contraindre | moyenne | IISR7, art. 117-4 C (p. 42 : LEF sur les seules voies commandées), 118 (p. 44 : bandes), 118-2 B (p. 47 : ligne jaune sur bordure) | immédiate |

### Fabrication du sol (Houdini) (12)

Triangulation contrainte, nivellement unique (chaussée, carrefour, caniveaux, bordures), normales, étanchéité et collision du sol.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| TQ-SOL-001 | Préparer la topologie 2D avant Houdini : tout est calé sur une grille de 1 mm (surfaces, bordures, voies, emprises de marques insérées) ; les arcs partagés sont identiques, sans trou ni recouvrement ; les arêtes de moins de 5 mm … | contraindre | moyenne | SFX_TRI2D, points en double, contraintes qui se croisent | immédiate |
| TQ-SOL-002 | Une seule triangulation contrainte pour tout le site, puis découpe en tuiles le long de lignes de grille déjà insérées comme contraintes (aucune jonction en T entre tuiles). | générer | moyenne | SFX_TRI2D, Refine, Minimum Angle, Triangle Sizes, Minimum Edge Length | immédiate |
| TQ-SOL-003 | Les lignes de rupture sont des arêtes contraintes de la triangulation : couronne (changement de signe du dévers), fil d'eau, pied de face de bordure, bords de caniveau, changements de dévers entre voies, bords de rampe et de … | vérifier | moyenne | LOC_CONTRAT, §3 (angle de rupture 30°, arêtes vives cassées, dévers lissés) | immédiate |
| TQ-SOL-004 | Le Z de la chaussée hors jonction vient du modèle OpenDRIVE (elevation + superelevation + shape / lateralProfile), évalué en chaque sommet par projection (s, t) sur la ligne de référence : c'est la même surface que la vérité … | générer | moyenne | LOC_XODR, routes 1 à 6 (elevation, superelevation, shape) ; routes 101 à 114 de la jonction 100 : un seul polynôme d'élévation et un dévers constant chacune | immédiate |
| TQ-SOL-007 | Conditionnement du MNT hors surfaces modélisées (talus, espaces verts, abords) : filtre médian 3 × 3 sur le MNT de 10 cm puis lissage gaussien de σ 0,3 m, points épinglés aux sommets contraints (arrière des bordures, bords de … | générer | faible | LOC_HOU_README, Sol : raccord sur 30 × l'écart au MNT | immédiate |
| TQ-SOL-008 | Normales calculées une seule fois sur le maillage complet, avant la découpe en tuiles, pour qu'elles soient identiques des deux côtés d'une couture : par sommet de face, cusp 30° ; sur la chaussée, normale issue du gradient … | vérifier | moyenne | LOC_CONTRAT, §3 (normales faceVarying, cusp 30°) | immédiate |
| TQ-SOL-009 | Étanchéité du sol (PolyDoctor en mode Mark) : aucun point non manifold, aucun polygone en double, aucune auto-intersection, aucune aire < 1e-6 m² ; arêtes de bord seulement sur l'emprise extérieure et sur les trous voulus … | vérifier | moyenne | SFX_POLYDOCTOR, Ill-Formed, Overlapping, Self-intersecting, Non-Manifold | immédiate |
| TQ-SOL-010 | Tuiles de sol de 50 m (64 m au plus), pivot au coin SO sur le mètre entier ; Nanite et distance field activés. | contraindre | moyenne | LOC_CONTRAT, §2 et §5 bis « Collision dans UE » (bNeverNeedsCookedCollisionData ; 4,5 cm d'écart avec le repli simplifié par défaut) | immédiate |
| TQ-SOL-011 | Pas de déplacement Nanite sur l'enrobé : la macrotexture passe par les normales. | contraindre | faible | UE_ISSUE_370671, Multiply sur la broche Displacement → géométrie fantôme flottante (5.7.3) | partielle |
| TQ-SOL-012 | Ni Mesh Terrain (expérimental en UE 5.8) ni Landscape pour la chaussée et les trottoirs ADAS : on garde les tuiles StaticMesh fabriquées par Houdini, déterministes et versionnées. | contraindre | moyenne | UE58_PRESSE, système expérimental de terrain à base de maillages 3D | immédiate |
| TQ-SOL-013 | Un seul modèle de nivellement pour toute la voirie, évalué dans cet ordre : (1) chaussée hors jonction : modèle .xodr (TQ-SOL-004) ; (2) aire du carrefour : TQ-SOL-014 ; (3) caniveaux : arête côté chaussée au Z de la chaussée … | contraindre | moyenne | LOC_HOU_README, § Bordures (dessous du bloc = fil d'eau au milieu de la corde + vue − H ; caniveaux CS2 : chaussée à fil d'eau + 2,5 cm) et § Sol (côté haut : dessus − 4 mm ; Z = MNT 2026 corrigé) | immédiate |
| TQ-SOL-014 | Surface de l'aire du carrefour (jonction xodr 100). | générer | moyenne | SETRA_GTAR2006, §1.2.1 (p. 16 du PDF : éviter les pentes < 0,5 %, stagnation au changement de dévers) ; p. 25 (calage des fils d'eau des carrefours selon les dévers) ; p. 39 (plans cotés des carrefours) | partielle |

### Rendu UE 5.8 (9)

Matériaux, Nanite, ombres et Lumen pour la voirie.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| TQ-MQR-001 | Matériau des marques opaque, pas Masked : l'usure fait fondre BaseColor, Roughness et Normal vers l'enrobé, échantillonné avec les mêmes UV monde (MF_EnrobeDetail). | contraindre | moyenne | UE_NANITE, Nanite : Opaque et Masked ; Translucent → matériau par défaut | immédiate |
| TQ-MQR-002 | Aucun World Position Offset ni Pixel Depth Offset sur les matériaux de chaussée, de marquage et de bordure : les décalages se font en géométrie seulement (UE n'a pas de polygon offset réglable sur l'opaque). | contraindre | haute | UE_VSM, WPO ou PDO invalident les pages de cache à chaque image | immédiate |
| TQ-MQR-003 | Réglages de primitive et de build des marques : Cast Shadow désactivé ; Affect Distance Field Lighting désactivé ; Generate Mesh Distance Field désactivé ; Receives Decals activé ; Shadow Cache Invalidation Behavior = Static ; … | contraindre | moyenne | UE_LUMEN, distance fields et objets très minces | immédiate |
| TQ-MQR-004 | Réglages Nanite identiques pour les tuiles de sol et les marques : enabled ; position_precision fixée à 5 (pas de 2^-5 cm ≈ 0,31 mm), jamais Auto ; keep_percent_triangles = 1,0 ; fallback_percent_triangles = 1,0 et … | contraindre | moyenne | UE_NANITE_TECH, pas = 2^-PositionPrecision cm ; même précision et décalage multiple du pas → pas de fissure ; fallback pour collision complexe et réflexions HWRT | immédiate |
| TQ-MQR-005 | Bilan anti-z-fighting : e_top ≥ max(1,5 mm ; 2 × pas de quantification + écart de drapé + écart de simplification du sol). | vérifier | moyenne | REED_DEPTH, Z inversé et tampon flottant | immédiate |
| TQ-MQR-006 | Choix de technique par élément. | contraindre | haute | UE_MESHDECALS, pas d'ordre de tri, biais fixe | immédiate |
| TQ-MQR-007 | Matériau physique des marques : frottement relatif à l'enrobé ≈ PTV_marque / PTV_enrobé, selon les classes NF EN 1436 (pendule SRT sur sol mouillé : S1 45, S2 50, S3 55, S4 60, S5 65). | déduire si absent | faible | MARKON_EN1436, table 7 EN 1436 | partielle |
| TQ-OMB-001 | Tout le contenu de voirie est en Nanite, même peu dense : tuiles de sol, marques, bordures, mortiers, dalles BEV, pontages (aucun matériau Translucent sur la voirie). | contraindre | haute | UE_VSM, activer Nanite sur toute la géométrie supportée, y compris low-poly | immédiate |
| TQ-OMB-002 | Lumen et ray tracing : tuiles de sol de 64 m au plus (qualité des distance fields) ; marques hors distance fields ; en ray tracing matériel avec Hit Lighting pour les reflets, fallback exact sur sol et marques (aucun repli du sol … | vérifier | moyenne | UE_LUMEN, les petits objets sont retirés de la scène Lumen | immédiate |

### PCG et instances UE (15)

Bordures en ISM, transport des points, Houdini Engine, workflows de référence.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| TQ-BOR-001 | Bordures, caniveaux et mortiers posés en ISM (pas HISM) avec des prototypes Nanite : Static Mesh Spawner du PCG avec bAllowDescriptorChanges = vrai, MeshSelectorByAttribute sur « Mesh », PCGInstanceDataPackerByAttribute cd0..cd6 … | contraindre | haute | UE_ISM, projet tout Nanite : ISM | immédiate |
| TQ-BOR-002 | Les éléments de bordure et de caniveau sont des instances rigides, transformées par pj_bordure_pose (pas selon le rayon, coupe d'au moins 0,20 m, points durs). | contraindre | haute | UE_PCG_SPLINEMESH, un USplineMeshComponent par segment | immédiate |
| TQ-BOR-003 | Collision des bordures pour la dynamique des roues : une collision simple par prototype (1 à 3 enveloppes convexes du profil), générée par Houdini (UsdPhysics), profil BlockAll (WorldStatic). | générer | moyenne | UE_NANITE_TECH, le fallback sert à la collision complexe | immédiate |
| TQ-BOR-004 | Ombres et cache des bordures : Cast Shadow activé (faces vues de 2 à 20 cm), Shadow Cache Invalidation Behavior = Static, pas de WPO (vieillissement par PerInstanceCustomData). | contraindre | moyenne | UE_VSM, Static ; −1 sur le biais double la résolution | immédiate |
| TQ-BOR-005 | Non-transparence des joints : rayons lancés depuis des hauteurs de caméra de 1,2 à 1,6 m, à 2, 5 et 10 m, à travers chaque joint (3,5 à 9,5 mm) ; chaque rayon touche le mortier ou le sol à moins de 0,30 m derrière la face ; ciel … | vérifier | moyenne | LOC_HOU_README, le sol passe sous l'élément ; bouchon de mortier | immédiate |
| TQ-BOR-006 | Option interactive seulement : Shape Grammar du PCG pour retoucher une file de bordure dans UE (Spline To Segment puis Subdivide Segment, grammaire « CHG, E100*, COUPE, CHD », COUPE sous-module scalable de 0,5 m, Accept … | générer | moyenne | UE_SHAPEGRAMMAR, syntaxe A*, <A,B,C> | immédiate |
| TQ-BOR-007 | Interfaces sol / bordure / caniveau. | vérifier | moyenne | LOC_HOU_README, § Sol (bande occupée : face + 12 mm ; le sol passe sous l'élément) et § Bordures (flèche de corde ≤ 10,5 mm ; chaussée arrêtée au bord des caniveaux, à fil d'eau + 2,5 cm) | immédiate |
| TQ-PCG-001 | Transport canonique des instances : points JSON pj_points/0.1 → pj_tools.charger_points vers un PCGDataAsset → Load PCG Data Asset → Static Mesh Spawner (bSynchronousLoad pour des captures de contrôle déterministes). | contraindre | haute | LOC_ARCHI, §1.5 | immédiate |
| TQ-PCG-002 | Nœud PCG Houdini Digital Asset : sorties en données PCG par l'attribut unreal_pcg_params (ou Force PCG Outputs) ; un seul port de sortie filtré par Filter Data By Tag (output_0…) ; surcharges par le nom interne des paramètres ; … | contraindre | haute | SFX_PCG, overview et workflows | immédiate |
| TQ-PCG-003 | Les petites instances Nanite dispersées (éclats, feuilles, gravillons) n'ont ni distance de culling ni rayon d'écran minimal : leur densité se règle dans les données, selon la zone et la distance aux bords ; 16 millions … | contraindre | haute | UE_NANITE, filtrage par vue non supporté | immédiate |
| TQ-PCG-004 | Pratiques reprises d'Electric Dreams : MeshSelectorByAttribute avec l'attribut « Mesh » (et « Material » pour surcharger le matériau) ; objets composites (mât + têtes de feux + panneaux) en hiérarchie de points (ActorIndex, … | générer | haute | UE_ELECTRIC, MeshSelectorByAttribute, RelativeTransform | immédiate |
| TQ-PCG-005 | Les retouches manuelles sur le contenu PCG (possibles depuis UE 5.8) ne sont admises que si elles sont réexportées dans la couche arbitre/ de la description, avec la provenance photo_utilisateur ou arbitrage ; sinon la … | contraindre | moyenne | UE58_PRESSE, retouches manuelles sur du contenu procédural | immédiate |
| TQ-REF-001 | Le Labs Road Generator de SideFX ne convient pas à ce site (ni marquages, ni voies, ni bordures, ni trottoirs ; carrefours noyés dans la géométrie ; modules valables en section droite) : il ne sert que de référence d'idées. | contraindre | haute | SFX_LABS_ROAD, entrées courbes ou OSM, sorties route / lignes / nuage | immédiate |
| TQ-REF-002 | Reprendre la pratique CARLA / RoadRunner : marques en maillages séparés de la route (Merge Marking décoché), classées RoadLine selon leur dossier, usure par décalques ; aucune collision sur les décalques et les meshes posés sur … | contraindre | haute | CARLA_RR, Merge Roads / Marking / Terrain décochés ; Export to Tiles | immédiate |
| TQ-REF-003 | City Sample : Houdini exporte des nuages de points (Point Cloud Alembic), le Rule Processor les traduit en assets, Zone Graph pour les voies de trafic, HLOD par World Partition. | vérifier | moyenne | UE_CITYSAMPLE, EXPORT ALL PBC ; Rule Processor ; Zone Graph ; HLOD | immédiate |

### Vérité terrain ADAS (2)

Vérité terrain caméra et LiDAR.

| ID | Règle | Act. | Conf. | Source principale | Appl. |
|---|---|---|---|---|---|
| TQ-ADAS-001 | La vérité terrain des marquages vient de la description vectorielle (polygones exacts, classe IISR, lien au .xodr), projetée par le modèle de caméra calibré ; le rendu sémantique ne sert que de contrôle croisé (IoU ≥ 0,95 jusqu'à … | générer | moyenne | CARLA_SENSORS, 24 RoadLine ; tags par chemin de fichier | partielle |
| TQ-ADAS-002 | LiDAR : les marques, en requête seule, sont touchées par les traces Visibility. | générer | moyenne | CARLA_SENSORS, atmosphere_attenuation_rate | partielle |

## Lacunes

- Grenoble-Alpes Métropole : ni le guide des espaces publics et de la voirie, ni le règlement de voirie de 2018, ni la charte Chronovélo n'ont été trouvés en PDF public. Les pratiques locales (carrés de 0,50 m et pavés jaunes des traversées cyclables, hauteur de quai du réseau SMMAG, matériaux des bordures neuves) restent non sourcées. La fiche GRAIE n° 92 renvoie vers un portail réservé aux membres et la présentation JTR 2018 de la Métropole est inaccessible (certificat invalide).
- Normes AFNOR payantes non lues : NF P98-351 (BEV), NF P98-352 (bandes de guidage), NF P98-340/CN (bordures), NF P98-332, NF EN 124, NF EN 1436, NF EN 1824, NF EN 13201. Leurs valeurs viennent du Cerema, de la CFPSAA, de guides de villes et de fabricants.
- Guides nationaux non accessibles : Certu « Carrefours urbains » (2010), « Recommandations pour les aménagements cyclables » (2008), Cerema « Rendre sa voirie cyclable » (2021), fiche PAMA n° 6 (traversées cyclables contiguës), fiches cheminements n° 07 et 08, ARP 2022, guide VSA. Largeurs de voies, rayons d'angle et dévers de chaussée reposent sur Lyon (2010) et Paris (2015).
- Légifrance a bloqué la lecture automatique de R412-30 et de L118-5-1 : leurs textes viennent de documents du Cerema et d'une préfecture. La dernière version consolidée trouvée de l'IISR 3e partie date du 09/01/2019.
- L'IISR ne chiffre ni l'intervalle des flèches, ni la distance de la dernière flèche à la ligne d'effet, ni la distance entre ligne d'effet et passage piéton : valeurs du site et des guides de Lyon et de Paris.
- Lignes d'effet : on ignore si les 23 lignes mesurées ferment des sas (aucune figurine vérifiée entre ligne et passage) ; feux.json indique qu'il n'y a pas de LEF peinte au cœur du carrefour ; les LEF de 2022 sont invisibles sur l'ortho.
- État après travaux : aucune photo postérieure à 09/2025 (décision D3 reportée). Le plan 2025 est un projet, pas un récolement ; les règles de fusion et de détection en zone neuve reposent sur lui (tolérance de 0,30 m).
- Aucun LAZ LiDAR HD local : l'affinage des bordures par marche de hauteur (DET-KRB-014) n'a pas été testé, et l'intensité LiDAR n'est qu'une preuve d'appui (rasters JPEG 8 bits).
- Les seuils de détection (typage des flèches 0,07 / 0,15, seuils de NCC, zébras à 3 bandes) viennent de 8 cas : les règles de détection et de déduction sont à calibrer sur Panoramax avant d'être activées par défaut. Les gabarits GAM plus étroits que l'IISR (parkings) ne sont pas couverts.
- Plan de feux (phasage) indisponible : la règle des flèches obligatoires en phase spéciale (MQ-FLE-002) ne peut s'appuyer que sur les signaux du .xodr. La configuration (a) ou (b) de MQ-CYC-013 au droit des 4 R13c est à confirmer sur photo.
- Assainissement : aucune règle nationale d'espacement des avaloirs (règle locale de Versailles Grand Parc), réglage en dents de scie non sourcé, tracé du réseau inconnu.
- Épaisseurs réglementaires françaises des produits de marquage introuvables en accès libre : les 2 et 3 mm fabriqués sont un choix de rendu, cohérent avec le .xodr, à recaler sur une photo rasante.
- UE 5.8.3 à tester : stencil Custom Depth sur Nanite, règle de Position Precision « Auto », présence des décalques DBuffer dans les reflets Hit Lighting, état du bug UE-370671 ; annonces officielles 5.7 et 5.8 en erreur 403.
- Valeurs géométriques sans source : nez d'îlot (rayon, recul), distance entre arbre et réseaux ou bâti (schéma de Montpellier illisible à l'extraction), tolérance d'affleurement des tampons, largeur d'un refuge pour cyclistes (2,00 / 2,50 m déduits) ; affleurement entre enrobé et caniveau (TQ-BOR-007 : ±3 mm, choix de contrôle) ; seuil de « traversée longue » (MQ-PP-014 : 12 m, choix de contrôle).
- Cinq PDF ont été déposés dans data/raw/normes par un autre agent après la remise des recherches, sans URL d'origine : ils sont catalogués avec leur copie locale ; l'arrêté de 2012 (abaque), la fiche lyonnaise « barrières » et la fiche de Montpellier ont été lus et exploités (GA-OBS-002, GA-OBS-003, GA-ARB-005), l'IISR 1re partie non. La fiche « barrières » a ensuite été renommée en grandlyon_RFX_barriere_2019.pdf (même taille, 888 620 octets) : le catalogue pointe désormais vers ce nom (erreur du validateur corrigée en v1.1).
- Gabarits à ajouter à marquages_geometrie.json (spec non modifiée ici) : TRIANGLE_DOS_D_ANE (0,70 × 2,00), TRIANGLE_COUSSIN (0,50 × rampe ; report 1,20-1,50), TRIANGLE_PLATEAU (0,70 × rampe ; report 2,00), RAPPEL_30 (E.1), VITESSE_50 (E.3 : 1,80 × 0,90), BARRETTE_CHRONOVELO, POINT_AXE_CHRONOVELO, DOUBLE_CHEVRON ; lettres et chiffres des planches D.3-D.4 (TQ-MQG-013) ; pictogramme PMR. La description v2 porte déjà 14 dent_requin, 2 « 30 », 2 « 50 », 20 barrettes et 5 points jaunes.
- Gabarits des bus du réseau grenoblois inconnus : la vérification de giration (GA-RAY-002) utilise les bus de Lyon.
- Spécification ASAM de roadMark@height non lue (page en erreur 404) ; documentation RoadRunner derrière une connexion MathWorks. VAL-XOD-008 s'appuie sur le parseur de CARLA.
- Vérification v1.1 (critique de complétude) de 10 règles tirées au sort (random.seed(20261010) sur les 193 règles à source web) : 7 conformes (MQ-CYC-010, TQ-SOL-012, MQ-RAB-002, TQ-PCG-005, MQ-ILO-003, GA-RES-002, MQ-ILO-002), 1 conforme avec une extrapolation (GA-QBU-003), 2 aux valeurs mal attribuées (MQ-STA-005, GA-CHA-005). Erreurs trouvées hors tirage : MQ-LIG-007, MQ-PP-011, MQ-PP-013, MQ-BUS-002, MQ-LEF-001, TQ-SOL-004, TQ-SOL-010, GA-QBU-004. Toutes corrigées en v1.1, ainsi que MQ-LIG-003 et GA-CHA-001 (constats de la synthèse).
- Nivellement de l'aire du carrefour (TQ-SOL-014) : aucune source nationale accessible ne traite le nivellement d'un carrefour urbain ; le guide Certu « Carrefours urbains » (2010) n'est pas en ligne et le guide Sétra GTAR (2006) est interurbain. Méthode interne ; seuils sourcés (0,5 %, 4 %).
- Écarts entre le site et la norme, à arbitrer sur photo postérieure aux travaux : triangles de ralentisseur de 0,79-0,81 m non contigus contre 0,70 m contigus (CF-27) ; « 50 » de 1,90 × 1,00 m contre 1,80 × 0,90 m (CF-28) ; pictogramme PMR de 0,79 m contre 0,60 ou 1,20 m (118-2 C) ; carrés et pavés des traversées cyclables non normatifs.
- Contraste tactile des traversées (MQ-PP-014) : obligation certaine (arrêté de 2007 modifié en 2024), mais aucun dispositif n'est défini techniquement ; la norme du tapis traversant est en cours. Le défaut retenu (bandes à relief) est un choix de projet.
- Téléchargements v1.1 : aucun fichier ajouté à data/raw/normes. Le guide Sétra GTAR 2006 (2 732 375 octets) et la fiche CFPSAA « Traversée piétonne » (706 591 octets) ont été lus depuis le cache de l'outil web, hors dépôt (sources SETRA_GTAR2006 et CFPSAA_TRAV) ; le Sétra peut être copié dans data/raw/normes/cerema/ sur demande. Les autres PDF relus (IISR 7e partie, Paris, Lyon, Nice, Cerema) sont les copies locales.

## Sources

### PDF téléchargés (`data/raw/normes/`, ignoré par git)

| Code | Document | Date | Fichier local | Taille (octets) |
|---|---|---|---|---|
| IISR7 | [IISR 7e partie « Marques sur chaussées », version consolidée VC20250404 (Cerema / DSR-DGITM)](https://equipementsdelaroute.cerema.fr/IMG/pdf/iisr_7epartie_vc_20250404.pdf) | 2025-04-04 | `data/raw/normes/cerema/iisr_7epartie_vc_20250404.pdf` | 8 882 091 |
| IISR6 | [IISR 6e partie « Feux de circulation permanents », version consolidée VC20250904](https://equipementsdelaroute.cerema.fr/IMG/pdf/iisr_6epartie_vc_20250904.pdf) | 2025-09-04 | `data/raw/normes/cerema/iisr_6epartie_vc_20250904.pdf` | 2 000 566 |
| IISR3 | [IISR 3e partie « Intersections et régimes de priorité », version VP20190109](https://equipementsdelaroute.cerema.fr/IMG/pdf/iisr_3epartie_vc_201901_cle09e7a7.pdf) | 2019-01-09 | `data/raw/normes/cerema/iisr_3epartie_vc_201901.pdf` | 2 322 124 |
| ARR2007_JO | [Arrêté du 15 janvier 2007, version initiale (JO du 3 février 2007, texte 29), copie de la préfecture du Cantal](https://www.cantal.gouv.fr/contenu/telechargement/4955/64107/file/arrete_voirie_prescriptions_techniques_150107_cle24219f.pdf) | 2007-02-03 | `data/raw/normes/accessibilite/arrete_15janvier2007_voirie_prescriptions_cantal.pdf` | 433 984 |
| ARR2012 | [Arrêté du 18 septembre 2012 modifiant l'arrêté du 15 janvier 2007 : annexe 3 « Abaque de détection des obstacles bas » (JO du 2 octobre 2012, texte 21)](file:///D:/ClaudeCode_RoadCreation/data/raw/normes/accessibilite/abaque_obstacles_bas_2012_seine_et_marne.pdf) | 2012-09-18 | `data/raw/normes/accessibilite/abaque_obstacles_bas_2012_seine_et_marne.pdf` | 168 450 |
| IISR1 | [IISR 1re partie « Généralités », version consolidée VC20250904](file:///D:/ClaudeCode_RoadCreation/data/raw/normes/cerema/iisr_1epartie_vc_20250904.pdf) | 2025-09-04 | `data/raw/normes/cerema/iisr_1epartie_vc_20250904.pdf` | 2 651 101 |
| CR_R412_30 | [Code de la route, art. R412-30 (version issue du décret n° 2019-1328), cité par Cerema « Modifications de l'IISR et de l'arrêté accessibilité » (journée tramway STRMTG)](https://www.strmtg.developpement-durable.gouv.fr/IMG/pdf/tw_3_cerema_iisr_accessibilite.pdf) | 2025-06-12 | `data/raw/normes/cerema/strmtg_tw3_cerema_iisr_accessibilite_2025.pdf` | 792 431 |
| CEREMA_PAMA10 | [Cerema, fiche PAMA n° 10 « Neutralisation du stationnement motorisé dans les 5 m en amont du passage piéton » (art. L118-5-1 du Code de la voirie routière, loi LOM art. 52), hébergée par la préfecture de la Mayenne](https://www.mayenne.gouv.fr/contenu/telechargement/51895/378214/file/Loi%20LOM%20et%20stationnement.pdf) | 2020-01 | `data/raw/normes/deal/prefecture_mayenne_loi_LOM_stationnement.pdf` | 4 361 816 |
| CEREMA_AUDIT | [Cerema, Audit de sécurité routière : fiches techniques, milieu urbain, avant mise en service](https://demarches-securite-routes.cerema.fr/IMG/pdf/fichetechnique_pms_urbain_cle243f66.pdf) | 2012-03 | `data/raw/normes/cerema/cerema_fichetechnique_pms_urbain.pdf` | 779 835 |
| CETE_SH2010 | [CETE de Lyon (Cerema), diaporama « La signalisation horizontale » (CoTITA 15/06/2010), hébergé par le Cerema](https://www.cerema.fr/system/files/documents/2021/12/pdf_2-signalisation.pdf) | 2010-06-15 | `data/raw/normes/cerema/cerema_2021_pdf_2-signalisation.pdf` | 1 414 995 |
| CEREMA_BEV03 | [Certu/Cerema, Les cheminements des personnes aveugles et malvoyantes, fiche n° 03 « Les bandes d'éveil de vigilance : implantation sur la voirie »](https://www.manche.gouv.fr/contenu/telechargement/50735/352459/file/cheminement_bande_vigilance_implantation.pdf) | 2010-07 | `data/raw/normes/cerema/certu_cerema_fiche03_bev_implantation_2010.pdf` | 937 341 |
| CEREMA_BUS2018 | [Cerema, Points d'arrêt de bus et de car accessibles à tous : de la norme au confort (collection Références)](https://www.aude.gouv.fr/contenu/telechargement/23124/153216/file/cerema-points_arrets_bus_car_accessibles.pdf) | 2018-05 | `data/raw/normes/cerema/cerema_points_arret_bus_car_accessibles_2018.pdf` | 8 494 213 |
| CEREMA_PAMA12 | [Cerema, fiche PAMA n° 12 « La possibilité du sas cycliste sans bande d'accès »](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/12_sas_cycliste.pdf) | 2016-11 | `data/raw/normes/deal/cerema_fiche12_sas_cycliste.pdf` | 752 321 |
| CEREMA_PAMA14 | [Cerema, fiche PAMA n° 14 « Marquage des trajectoires matérialisées pour les cycles »](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/14-marqtrajeccyclistes.pdf) | 2016-05 | `data/raw/normes/deal/cerema_fiche14_marquage_trajectoires_cyclistes.pdf` | 2 287 097 |
| CEREMA_PAMA05 | [Cerema, fiche PAMA n° 05 « Extension du cédez-le-passage cycliste au feu »](https://www.aude.gouv.fr/contenu/telechargement/10271/88951/file/1770_firf01515pama05-cedezlepassfeu_cle2b8ca9.pdf) | 2015-09 | `data/raw/normes/deal/cerema_pama05_cedez_passage_cycliste_feu.pdf` | 483 890 |
| CEREMA_ANNEXE3 | [Cerema, note de recommandations techniques (annexe 3 de l'appel à projets « Fonds mobilités actives »), exemplaire « _du_cerema »](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/annexe_3_recommandations_techniques_du_cerema.pdf) | vers 2020 | `data/raw/normes/deal/cerema_recommandations_techniques_annexe3.pdf` | 3 413 362 |
| CEREMA_ANNEXE3B | [Cerema, note de recommandations techniques (annexe 3, aménagements cyclables), second exemplaire DEAL Guadeloupe](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/annexe_3_recommandations_techniques.pdf) | 2021 (estimée) | `data/raw/normes/deal/cerema_recommandations_techniques_annexe3_dealguadeloupe.pdf` | 3 432 761 |
| CERTU_VELO02 | [Cerema, fiche vélo n° 02 « Les bandes cyclables » (mise à jour)](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/bandecyclable.pdf) | 2015-02 | `data/raw/normes/deal/certu_fiche_bande_cyclable.pdf` | 2 566 279 |
| CERTU_VELO11 | [Certu, fiche vélo n° 11 « Les sas à vélos »](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/sas_velo.pdf) | 2012-08 | `data/raw/normes/deal/certu_fiche_velo11_sas_velo_2012.pdf` | 477 198 |
| CERTU_VELO09 | [Certu, fiche vélo n° 09 « Vélos et transports publics : partage de la voirie »](https://www.guadeloupe.developpement-durable.gouv.fr/IMG/pdf/velo_et_tc.pdf) | 2011-03 | `data/raw/normes/deal/certu_fiche_velo_et_tc.pdf` | 832 250 |
| SMT_BUS2009 | [SMT Artois-Gohelle, schéma directeur d'accessibilité : guide technique des arrêts de bus, hébergé par la préfecture du Gers](https://www.gers.gouv.fr/index.php/contenu/telechargement/12759/88661/file/Guide%20technique%20arr%C3%AAt%20de%20bus.pdf) | 2009-06 | `data/raw/normes/deal/ddt_gers_guide_technique_arret_bus.pdf` | 4 798 027 |
| LYON_RFX_LEF | [Métropole de Lyon, fiche réflexe « Ligne d'effet des feux et sas vélo » (MAJ juin 2017)](https://labdesespacespublics.grandlyon.com/app/uploads/2024/07/2019-04-RFX-ligne-deffet-des-feux-sas-velo-MAJjuin2017.pdf) | 2017-06 | `data/raw/normes/metropoles/grandlyon_RFX_ligne_effet_feux_sas_velo_2019.pdf` | 843 240 |
| LYON_RFX_PP | [Métropole de Lyon, fiche réflexe « Les passages piétons en carrefour »](https://labdesespacespublics.grandlyon.com/app/uploads/2024/07/2019-04-RFX-Passage-pietons-carrefour-MAJjuin2017.pdf) | 2019-04 | `data/raw/normes/metropoles/grandlyon_RFX_passage_pietons_carrefour_2019.pdf` | 957 374 |
| LYON_RFX_CHR | [Métropole de Lyon, fiche réflexe « Les entrées charretières »](https://labdesespacespublics.grandlyon.com/app/uploads/2024/07/2019-04-RFX-entree-charretiere-MAJjuin2017.pdf) | 2017-06 | `data/raw/normes/metropoles/grandlyon_RFX_entree_charretiere_2017.pdf` | 851 475 |
| LYON_DIM | [Métropole de Lyon, Référentiel de conception et de gestion des espaces publics : Cohérence des dimensions](https://www.grandlyon.com/fileadmin/user_upload/media/pdf/voirie/referentiel-espaces-publics/20091201_gl_referentiel_espaces_publics_dimensions_coherence_dimensions.pdf) | 2010 | `data/raw/normes/metropoles/grandlyon_referentiel_coherence_dimensions_2010.pdf` | 2 449 687 |
| LYON_ARBRES | [Métropole de Lyon, Référentiel : Matériaux, les pieds d'arbres](https://www.grandlyon.com/fileadmin/user_upload/media/pdf/voirie/referentiel-espaces-publics/20091201_gl_referentiel_espaces_publics_materiaux_piedsdarbres.pdf) | 2010 | `data/raw/normes/metropoles/grandlyon_referentiel_pieds_arbres_2010.pdf` | 2 149 246 |
| LYON_EP | [Métropole de Lyon, Référentiel : Ouvrages enterrés de gestion des eaux pluviales](https://www.grandlyon.com/fileadmin/user_upload/media/pdf/voirie/referentiel-espaces-publics/20091201_gl_referentiel_espaces_publics_ouvrages_enterres_gestion_eaux_pluviales.pdf) | 2010 | `data/raw/normes/metropoles/grandlyon_referentiel_ouvrages_enterres_eaux_pluviales_2010.pdf` | 1 764 514 |
| LYON_CYCL | [Métropole de Lyon, Guide pour la conception des aménagements cyclables](https://www.grandlyon.com/fileadmin/user_upload/media/pdf/voirie/20190621_guide-amenagement-cyclable.pdf) | 2019-06 | `data/raw/normes/metropoles/grandlyon_guide_amenagements_cyclables_2019.pdf` | 3 478 832 |
| LYON_ACC | [Métropole de Lyon, Recueil sur l'accessibilité des aménagements](https://labdesespacespublics.grandlyon.com/app/uploads/2024/07/Recueil-sur-laccessibilite-des-amenagements-2021.pdf) | 2021 | `data/raw/normes/metropoles/grandlyon_recueil_accessibilite_amenagements_2021.pdf` | 3 254 535 |
| LYON_RFX_BARRIERE | [Métropole de Lyon, fiche réflexe « Les barrières » (mise à jour avril 2019)](file:///D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/grandlyon_RFX_barriere_2019.pdf) | 2019-04 | `data/raw/normes/metropoles/grandlyon_RFX_barriere_2019.pdf` | 888 620 |
| MTP_PLANTATION | [Ville de Montpellier, fiche plantation conception n° 1 « Distances de plantation des arbres sur l'espace public selon l'espace aérien disponible » (cite le Code civil, art. 671-672)](file:///D:/ClaudeCode_RoadCreation/data/raw/normes/metropoles/montpellier_distances_plantation_espace_aerien_2024.pdf) | 2024 | `data/raw/normes/metropoles/montpellier_distances_plantation_espace_aerien_2024.pdf` | 18 779 987 |
| NANTES_CYC | [Nantes Métropole, « Signalisation horizontale : marques sur chaussée pour les cycles » (validé le 04/12/2019, modifié le 11/10/2022)](https://metropole.nantes.fr/files/pdf/espace-public/Marques_sur_chauss%C3%A9e_cycles.pdf) | 2022-10-11 | `data/raw/normes/metropoles/nantes_metropole_marques_sur_chaussee_cycles.pdf` | 864 245 |
| NICE_QUAIS | [Métropole Nice Côte d'Azur, Charte d'aménagement des quais bus accessibles aux PMR (Ad'AP)](https://www.nicecotedazur.org/wp-content/uploads/2020/12/SDAAd_AP_Charte_amenagement_quais_bus.pdf) | 2016 | `data/raw/normes/metropoles/nicecotedazur_charte_quais_bus_pmr_2016.pdf` | 1 315 701 |
| PARIS_SH | [Ville de Paris, « Guide de la signalisation horizontale à Paris » (version du 11/03/2015)](https://cdn.paris.fr/paris/2019/07/24/c63bc81ff4044e9dd71a888afbb05306.pdf) | 2015-03-11 | `data/raw/normes/metropoles/paris_guide_signalisation_horizontale.pdf` | 7 985 805 |
| PARIS_CYC2023 | [Ville de Paris, « Guide des aménagements cyclables, 3e partie : carrefours »](https://cdn.paris.fr/paris/2024/09/30/guide-amenagements-cyclables-partie-3-carrefours-juin-2023-light-Xlfv.pdf) | 2023-06 | `data/raw/normes/metropoles/paris_guide_amenagements_cyclables_p3_carrefours_2023.pdf` | 3 675 876 |
| VGP_ASS | [Versailles Grand Parc, Prescriptions techniques assainissement (version 2021.05)](https://www.versaillesgrandparc.fr/fileadmin/user_upload/au_quotidien/le_cycle_de_l_eau/Assainissement_et_vous/Prescriptions_techniques_assainissement_VGP_06-2022.pdf) | 2021-05 | `data/raw/normes/metropoles/versaillesgrandparc_prescriptions_assainissement_2021.pdf` | 5 237 533 |
| MTP_FOSSE | [Ville de Montpellier, fiche 1.2.4 « Fosse de plantation individuelle »](https://www.montpellier.fr/sites/default/files/2024-12/Fosse-de-plantation-individuelle.pdf) | 2020-12 | `data/raw/normes/metropoles/montpellier_fiche_fosse_plantation_individuelle_2020.pdf` | 742 923 |

Total : 107 521 725 octets.

Cinq fichiers ont été déposés le 10/10/2026 entre 12:42 et 12:45 par un autre agent, après la remise des quatre recherches : `arrete_15janvier2007_voirie_prescriptions_cantal.pdf`, `abaque_obstacles_bas_2012_seine_et_marne.pdf`, `iisr_1epartie_vc_20250904.pdf`, `grandlyon_RFX_barriere_2019.pdf`, `montpellier_distances_plantation_espace_aerien_2024.pdf`. La copie de l'arrêté de 2007 est identique (MD5) au PDF lu à l'URL de la préfecture du Cantal, mis en cache par l'outil web (`C:/Users/flori/.claude/projects/D--/193706ca-c280-454e-8894-a24c258637c3/tool-results/webfetch-1791626769079-j5lggy.pdf`). Pour les quatre autres, l'URL d'origine n'a pas été transmise : le lien pointe vers la copie locale. La fiche lyonnaise « barrières » a été renommée après coup (`_2017` devenu `_2019`) ; le catalogue suit le nouveau nom depuis la v1.1. L'IISR 1re partie est cataloguée mais n'a pas été exploitée.

Lus en ligne sans copie dans le dépôt (copie de travail dans le cache de l'outil web, voir le tableau suivant) : SETRA_GTAR2006, CFPSAA_TRAV.

### Autres sources (pages web, données et documents du projet)

| Code | Document | Type | Date | Lien |
|---|---|---|---|---|
| ARR2007 | Arrêté du 15 janvier 2007 (accessibilité de la voirie et des espaces publics), version consolidée Légifrance (modifié en 2012 et le 8 mars 2024) | reglementaire | 2007-01-15 (consolidé au 2024-03-24) | https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000646680 |
| ARR2024 | Arrêté du 8 mars 2024 modifiant l'arrêté du 15 janvier 2007 (art. 1, 4°, traversées pour piétons) | reglementaire | 2024-03-08 | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049314393 |
| DEC2006 | Décret n° 2006-1658 du 21 décembre 2006 (prescriptions techniques pour l'accessibilité de la voirie), reproduction du JO | reglementaire | 2006-12-21 | https://www.marche-public.fr/Marches-publics/Textes/Decrets/Decret_no_2006-1658-EQUR0600944D.htm |
| BDT_L118 | Banque des Territoires, « Passages piétons : les maires peuvent aménager une zone tampon » (art. L118-5-1 CVR, source secondaire) | presse_institutionnelle | 2019-12-24 | https://www.banquedesterritoires.fr/passages-pietons-les-maires-peuvent-amenager-une-zone-tampon-pour-plus-de-securite |
| CFPSAA_BEV | CFPSAA, fiche « Bande d'éveil de vigilance (BEV) », synthèse de NF P98-351 (lue, non copiée : hébergeur associatif) | associatif | 2021-06 | https://aveuglesdefrance.org/app/uploads/2022/03/Fiche-sur-les-bande-deveil-de-vigilance-PDF-Accessible.pdf |
| EN124 | NF EN 124-1/-3:2015, dispositifs de couronnement et de fermeture (groupes A15 à D400), notice iteh et fiches fabricants | norme | 2015 | https://iteh.es/catalog/standards/cen/c71fd97c-e384-475c-b9b6-d4de3b3b820f/en-124-3-2015 |
| PAM_PAMREX | Saint-Gobain PAM, fiche PAMREX 600 D400 cadre rond (cotes reprises d'un résumé de recherche) | fabricant | 2025 | https://www.pamline.com/fr-fr/media/123686/download |
| HAUC_SROH | HAUC (UK), SROH Ancillary activities : traffic signs and road markings (épaisseurs thermoplastiques) | norme_etrangere | 2023 | https://app.hauc-uk.org.uk/sroh-ancillary-activities-traffic-signs-road-markings-general |
| AXIMUM_G17 | Aximum, fiche Thermolit G17 (enduit à chaud extrudé) | fabricant | s.d. | https://aximum.com/sites/default/files/pdf-documentation/enduit-chaud-extrude-thermolit-g17.pdf |
| MARKON_EN1436 | Markon, road marking datasheet (classes SRT de NF EN 1436:2018) | fabricant | s.d. | https://www.leiths-group.co.uk/files/docs/Markon-Datasheets/Road-Marking-Data-Sheet-Markon.pdf |
| TRB_CROSS | TRB, Justification for cross slope design criteria | recherche | s.d. | https://trid.trb.org/View/39441 |
| REED_DEPTH | N. Reed, « Depth Precision Visualized » | technique | 2015 | https://www.reedbeta.com/blog/depth-precision-visualized/ |
| LIDARHD | data.gouv.fr, Semis de points LiDAR HD classé Isère 2021-2022 (CRAIG / IGN) | donnees_ouvertes | 2021-2022 | https://www.data.gouv.fr/datasets/semis-de-points-lidar-hd-classe-isere-2021-2022/informations |
| SKYSCAPES | Azimi et al., SkyScapes : Fine-Grained Semantic Understanding of Aerial Scenes (ICCV 2019) | recherche | 2019 | https://openaccess.thecvf.com/content_ICCV_2019/html/Azimi_SkyScapes__Fine-Grained_Semantic_Understanding_of_Aerial_Scenes_ICCV_2019_paper.html |
| SOILAN2017 | Soilán et al., Segmentation and classification of road markings using MLS data, ISPRS J. 123:94-103 | recherche | 2017 | https://hdl.handle.net/11093/1336 |
| UE_NANITE | Epic, Nanite Virtualized Geometry (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine |
| UE_NANITE_TECH | Epic, Nanite Technical Details (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-technical-details |
| UE_API_NANITE | Epic, Python API unreal.MeshNaniteSettings (5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MeshNaniteSettings |
| UE_VSM | Epic, Virtual Shadow Maps (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine |
| UE_LUMEN | Epic, Lumen Technical Details (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-technical-details-in-unreal-engine |
| UE_DECALS | Epic, Decal Materials (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/decal-materials-in-unreal-engine |
| UE_MESHDECALS | Epic, Using Mesh Decals (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/using-mesh-decals-in-unreal-engine |
| UE_ISM | Epic, Instanced Static Mesh Component (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/unreal-engine/instanced-static-mesh-component-in-unreal-engine |
| UE_PCG_SPAWNER | Epic, API UPCGStaticMeshSpawnerSettings | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/PCG/UPCGStaticMeshSpawnerSettings |
| UE_PCG_SPLINEMESH | Epic, Python API PCGSpawnSplineMeshSettings | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PCGSpawnSplineMeshSettings |
| UE_SHAPEGRAMMAR | Epic, Using Shape Grammar with PCG (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/using-shape-grammar-with-pcg-in-unreal-engine |
| UE_ELECTRIC | Epic, Procedural Content Generation in Electric Dreams (UE 5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-in-electric-dreams |
| UE_USDIMPORT | Epic, Python API UsdStageImportOptions (5.8) | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/UsdStageImportOptions |
| UE_CITYSAMPLE | Epic, City Sample Quick Start for generating a city and freeway using Houdini | technique | consulté 2026-10-10 | https://dev.epicgames.com/documentation/en-us/unreal-engine/city-sample-quick-start-for-generating-a-city-and-freeway-using-houdini |
| UE_ISSUE_370671 | Unreal Engine issue UE-370671 (déplacement Nanite et Multiply, 5.7.3) | technique | consulté 2026-10-10 | https://issues.unrealengine.com/issue/UE-370671 |
| UE_FORUM_STENCIL | Forum UE, « 5.1 Nanite not able to write to stencil buffers » | technique | consulté 2026-10-10 | https://forums.unrealengine.com/t/5-1-nanite-not-able-to-write-to-stencil-buffers/746933 |
| UE58_PRESSE | gamefromscratch, « Unreal Engine 5.8 Released » (annonce officielle en erreur 403) | presse | consulté 2026-10-10 | https://gamefromscratch.com/unreal-engine-5-8-released/ |
| SFX_PCG | SideFX Houdini 22, Unreal PCG overview et PCG workflows | technique | consulté 2026-10-10 | https://www.sidefx.com/docs/houdini/unreal/pcg/overview.html |
| SFX_TRI2D | SideFX Houdini 22, Triangulate 2D SOP | technique | consulté 2026-10-10 | https://www.sidefx.com/docs/houdini/nodes/sop/triangulate2d.html |
| SFX_POLYEXPAND2D | SideFX Houdini 22, PolyExpand 2D SOP | technique | consulté 2026-10-10 | https://www.sidefx.com/docs/houdini/nodes/sop/polyexpand2d.html |
| SFX_POLYEXTRUDE | SideFX Houdini 22, PolyExtrude / PolyBevel / Ray SOP | technique | consulté 2026-10-10 | https://www.sidefx.com/docs/houdini/nodes/sop/polyextrude.html |
| SFX_POLYDOCTOR | SideFX Houdini 22, PolyDoctor SOP | technique | consulté 2026-10-10 | https://www.sidefx.com/docs/houdini/nodes/sop/polydoctor.html |
| SFX_LABS_ROAD | SideFX Labs Road Generator | technique | consulté 2026-10-10 | https://www.sidefx.com/docs/houdini/nodes/sop/labs--road_generator.html |
| CARLA_SENSORS | CARLA, Sensors reference (segmentation sémantique, LiDAR) | technique | consulté 2026-10-10 | https://carla.readthedocs.io/en/latest/ref_sensors/ |
| CARLA_RR | CARLA, How to make a new map with RoadRunner (0.9.6) ; Road Painter | technique | consulté 2026-10-10 | https://carla.readthedocs.io/en/0.9.6/how_to_make_a_new_map/ |
| CARLA_LANEPARSER | CARLA, LaneParser.cpp (lecture de roadMark@height) | technique | consulté 2026-10-10 | https://carla.org/Doxygen/html/d0/d2e/LaneParser_8cpp_source.html |
| SPEC_MQG | assets/specs/marquages_geometrie.json (IISR 7e partie : u, modulations, 13 gabarits) | spec_projet | 2026-10-10 | assets/specs/marquages_geometrie.json |
| SPEC_BORD_EL | assets/specs/bordures_elements.json (abaissés, BEV, éléments) | spec_projet | 2026-10-10 | assets/specs/bordures_elements.json |
| SPEC_PEINTURE | assets/specs/peinture.json (couleurs, usure, rugosité, épaisseurs) | spec_projet | 2026-10-09 | assets/specs/peinture.json |
| LOC_ARCHI | recon/pcg/ARCHITECTURE.md (pipeline v2) | doc_projet | 2026-10-10 | recon/pcg/ARCHITECTURE.md |
| LOC_CONTRAT | recon/pcg/ue/CONTRAT_EXPORT.md (contrat USD Houdini vers UE) | doc_projet | 2026-10-10 | recon/pcg/ue/CONTRAT_EXPORT.md |
| LOC_UE_README | recon/pcg/ue/README.md (couches importées dans UE) | doc_projet | 2026-10-10 | recon/pcg/ue/README.md |
| LOC_HOU_README | recon/pcg/houdini/README.md (règles de fabrication) | doc_projet | 2026-10-10 | recon/pcg/houdini/README.md |
| LOC_XODR | paquet_jardin_2026.xodr (OpenDRIVE 1.7 : elevation, superelevation, shape, roadMark) | donnees_site | 2026-10 | recon/out/paquet_jardin/package/paquet_jardin_2026.xodr |
| LOC_MANOEUVRES | donnees/opendrive/manoeuvres_2026.json (manœuvres autorisées par voie) | donnees_site | 2026-10 | recon/out/paquet_jardin/package/donnees/opendrive/manoeuvres_2026.json |
| LOC_VALID_XODR | donnees/opendrive/validation_2026.json (écarts .xodr / levé) | donnees_site | 2026-10 | recon/out/paquet_jardin/package/donnees/opendrive/validation_2026.json |
| LOC_MARQ2026 | marquages_2026.geojson (996 entités) et distances mesurées (calibrage du site) | donnees_site | 2026-10-10 | recon/out/paquet_jardin/package/donnees/marquages/marquages_2026.geojson |
| LOC_RELIEF | donnees/relief/README_relief.md (méthode de mesure des vues de bordure) | donnees_site | 2026-10 | recon/out/paquet_jardin/package/donnees/relief/README_relief.md |
| LOC_V2DESC | Description v2 (description_scene_v2.json et couches base/*.geojson) | donnees_site | 2026-10-10 | recon/out/paquet_jardin/v2/description/description_scene_v2.json |
| LOC_MANIFEST_MQ | v2/fabrique/marquages_manifest.json (contrôles de pj_marquages v0.1) | donnees_site | 2026-10-10 | recon/out/paquet_jardin/v2/fabrique/marquages_manifest.json |
| LOC_ORTHO | Ortho PCRS 5 cm, Grenoble-Alpes Métropole (CRAIG), 49 dalles JPEG + .jgw, prise de vue du 10/05/2022 | donnees_site | 2022-05-10 | data/sites/paquet_jardin/ortho5cm_2022 |
| LOC_PLAN2025 | Plan projet 2025, raster calé par affine (261 points, RMSE 0,030 m) | donnees_site | 2025 | data/sites/paquet_jardin/plan_projet_2025/georef.json |
| LOC_LIDAR | Rasters LiDAR HD 2021 (MNT, hauteur sol, intensité, pente ; 15 et 25 cm) | donnees_site | 2021-08/09 | data/sites/paquet_jardin/lidar |
| LOC_CONTRASTE | data/sites/paquet_jardin/marquages/contraste_par_tuile.json (top-hat 2 m, seuil 25) | donnees_site | 2026-10 | data/sites/paquet_jardin/marquages/contraste_par_tuile.json |
| LOC_MQ_ORTHO | recon/pcg/decrire/marquages_ortho.py (phase_ortho) et marquages_apercu.py | code_projet | 2026-10-10 | recon/pcg/decrire/marquages_ortho.py |
| TESTS_DETECT | Tests de faisabilité de la détection (tm_fleches.py, tm_voies.py, tm_plan.py, zebra_fft.py, lidar_contraste.py et résultats JSON) | essai_projet | 2026-10-10 | C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/detect |
| INTERNE | Proposition de la synthèse « règles de conception » (convention de génération ou de contrôle, non normative) | interne | 2026-10-10 | interne:regles_conception |
| SETRA_GTAR2006 | Sétra, Guide technique « Assainissement routier » (GTAR, octobre 2006), hébergé par le Cerema (lu, non copié dans le dépôt) | guide_national | 2006-10 | https://piles.cerema.fr/IMG/pdf/setra_guide_technique_assainissement_routier_2006_cle04a7e3.pdf |
| CFPSAA_TRAV | CFPSAA, fiche « Traversée piétonne » (création janvier 2019, mise à jour juin 2021) (lue, non copiée : hébergeur associatif) | associatif | 2021-06 | https://aveuglesdefrance.org/app/uploads/2022/03/Fiche-Traversee-pietonne-PDF-Accessible.pdf |

## Fusions d'identifiants

Les identifiants proposés par les recherches et absorbés par une autre règle :

| Ancien | Retenu |
|---|---|
| GA-ARB-004 | GA-TRO-001 |
| GA-CYC-001 | MQ-LAR-003 |
| GA-STA-001 | MQ-STA-001 |
| GA-STA-002 | MQ-STA-002 |
| GA-STA-003 | MQ-STA-004 |
| GA-TRV-001 | MQ-PP-003 |
| GA-TRV-002 | MQ-PP-013 |
| INF-ABA-022 | GA-ABA-001 |
| INF-BUS-019 | MQ-DET-009 |
| INF-CED-021 | MQ-DET-007 |
| INF-CYC-012 | MQ-CYC-007 |
| INF-FLE-005 | MQ-FLE-003 |
| INF-FLE-007 | MQ-FLE-010 |
| INF-HAC-020 | MQ-DET-008 |
| INF-LEF-001 | MQ-LEF-001 |
| INF-LEF-002 | MQ-LEF-005 |
| INF-LEF-003 | MQ-LEF-004 |
| INF-LIG-014 | MQ-LIG-003 |
| INF-LIG-015 | MQ-LIG-001 |
| INF-LIG-016 | MQ-LIG-005 |
| INF-LIG-017 | MQ-DET-011 |
| INF-RIV-018 | MQ-LIG-009 |
| INF-SAS-013 | MQ-DET-005 |
| INF-ZEB-008 | MQ-DET-004 |
| INF-ZEB-009 | MQ-DET-004 |
| INF-ZEB-010 | MQ-PP-004 |
| INF-ZEB-011 | MQ-LIG-002 |
| MQ-BUS-006 | GA-QBU-004 |
| MQ-FLE-007 | INF-FLE-004 |
| MQ-ILO-004 | GA-ILO-005 |
| MQ-LAR-001 | GA-CHA-005 |
| MQ-LAR-004 | MQ-LAR-003 |
| MQ-LAR-005 | GA-ILO-001 |
| MQ-LEF-007 | MQ-STA-001 |
| MQ-LIG-010 | MQ-LIG-005 |
| MQ-PP-007 | GA-ILO-002 |
| MQ-PP-010 | GA-BEV-001 |
| MQ-PP-012 | GA-QBU-007 |
| TQ-DED-001 | FUS-SNP-004 |
| TQ-DED-003 | TQ-MQG-002 |
| TQ-SOL-005 | GA-CHA-001 |
| TQ-SOL-006 | GA-TRO-004 |
| VAL-LEF-004 | MQ-LEF-004 |

## Historique

- **v1.0** (2026-10-10) : synthèse de 4 recherches (278 règles proposées, 237 retenues, 43 doublons fusionnés).
- **v1.1** (2026-10-10) : critique de complétude (carrefour urbain à feux à 4 branches) : règles ajoutées et corrigées, 3 conflits (CF-26 à CF-28), 2 sources, chemin de la fiche lyonnaise « barrières » réparé. Ajouts : MQ-PP-014, MQ-RAL-001, MQ-Z30-001, MQ-V50-001, TQ-MQG-013, MQ-CYC-012, MQ-CYC-013, MQ-CHR-001, MQ-LEF-011, TQ-SOL-013, TQ-SOL-014, GA-BOR-005, GA-ILO-007, TQ-BOR-007, TQ-MQG-014, VAL-XOD-008, VAL-SOL-009, VAL-JCT-010. Corrections : MQ-PP-011, MQ-LEF-001, MQ-LIG-007, MQ-BUS-002, MQ-STA-005, GA-CHA-005, GA-QBU-003, MQ-PP-013, TQ-SOL-004, TQ-SOL-010, GA-QBU-004, MQ-LIG-003, GA-CHA-001.
