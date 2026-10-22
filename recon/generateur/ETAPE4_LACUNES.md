# Étape 4 : inventaire des lacunes du générateur de routes françaises

*`recon/generateur/ETAPE4_LACUNES.md`, 22/10/2026. Même donnée en machine : `recon/generateur/etape4_lacunes.json` (schéma `etape4_lacunes/0.1`). Lot « inventaire des lacunes » de l'étape 4, écrit après la nouvelle orientation de l'utilisateur : imaginer des routes à partir d'images réelles de Meylan et de France. Le code a été lu, pas modifié. Les ponts / ouvrages et la signalisation verticale + feux sont implémentés en ce moment par un autre workflow : ils sont inventoriés ici, mais classés à part.*

## 0. En bref

- **153 fonctionnalités** d'un réseau routier français, de la rue de centre-ville à l'autoroute, en 18 familles. **26 sont faites, 32 partielles, 89 absentes** et 6 en cours dans le workflow parallèle.
- **Ce que le générateur sait faire est solide** : profils urbains et interurbains, 32 types de bordures, carrefours plans à régimes et feux, carrefours complexes à tourne-à-gauche guidés, giratoires, autoroutes en section courante, bretelles et musoirs. Les marquages des familles courantes sont exacts au gabarit.
- **Ce que montrent les rendus** (planches A1, A3, J5, G1, S01, S03 et nœud A41 / N87 regardées à leur taille native) : une route seule, posée à plat sur un sol uni. On n'y voit ni relief, ni talus, ni panneau, ni feu, ni candélabre, ni mobilier, ni pont. Le nœud A41 / N87, décrit avec ses ponts et ses talus, est fabriqué à plat.
- **Cinq manques structurels** pèsent sur toutes les scènes :
  - le relief (profil en long, terrain, talus) ;
  - le réseau continu (aujourd'hui un seul carrefour par route) ;
  - la signalisation de direction composée (D20 ex-D21, D42, D43, D61, EB10) ;
  - le graphe de voies hors carrefours plans et l'export OpenDRIVE ;
  - les équipements verticaux (éclairage, retenue posée par règle).
- **Beaucoup de règles sont déjà sur le disque, mais n'ont pas été versées dans la base** : ARP 2022, VSA 90/110, ICTAVRU et le guide Cerema 2022 des dispositifs de retenue (§ 4.2, pages repérées). Il manque en revanche l'ICTAAL, le guide des échangeurs de 2013, le guide de l'assainissement de 2006, le dossier pilote des tunnels et la norme de composition des panneaux directionnels (§ 4.3).
- **Beaucoup d'assets existent sans être posés** : 8 candélabres, des extrémités de glissières, 4 atténuateurs, un portique, 11 balises, du mobilier, et des gabarits de marquage (PMR, IRVE, damier TC, double chevron, MRE…). Plusieurs gains rapides en découlent (§ 7.3).
- **Nouvelle orientation.** Le générateur ne sait encore ni proposer une typologie de route française, ni tirer des variantes plausibles : chaque scène est écrite à la main. Trois leviers sont à poser avant ou à côté du TOP 20 (§ 6) : catalogue de typologies, tirage de variantes, relevé de fréquences sur photos.
- **TOP 20** (§ 7). Il exclut les éléments du workflow parallèle et la végétation. Il commence ainsi : 1. Terrain naturel et abords ; 2. Graphe de voies complet ; 3. Profil en long ; 4. Signalisation de direction composée ; 5. Réseau continu ; 6. Export OpenDRIVE 1.4 (CARLA) et 1.8.1.

## 1. Méthode

- **Lu** :
  - `PLAN_GENERATEUR.md`, `CHAINE_CONSTRUCTION.md` (§ 4 à 9), `FORMAT_DESCRIPTION.md`, `FORMAT_DESCRIPTION_RESEAU.md`
    (§ 7), `hda/README_RG.md` (§ 1 à 15) ;
  - les besoins de format des sites de Meylan (`meylan/BESOINS_FORMAT*.md`, A1 à A20 et B1 à B17) ;
  - `RESULTATS_ETAPE3_PASSE1.json`, `comparaison/CONTROLE.md` et les rapports de validation ;
  - la base `assets/specs/route/regles_route_fr.json` (857 règles, 34 DEF, 20 ARB) ;
  - le catalogue `catalogue_assets_route.json` (915 entrées : 288 meshes, 600 panneaux, 27 ensembles) et `panneaux_fr_catalogue.json` (870 faces, dont 259 exemples à recomposer) ;
  - `D:\DocRoute` : synthèse, dossiers 08, 09, 10, 13, 14 et 17.
- **Vérifié dans le code** : recherche de chaque fonctionnalité (mots du vocabulaire, gabarits, codes de signaux, familles du modèle) dans `description/`, `commun/`, `reseau/`, `hda/` et les pilotes. Les preuves citent fichier et ligne. Celles qui viennent de `CHAINE_CONSTRUCTION.md` le disent (numéros de ligne du 17/10).
- **Vérifié dans les rendus** : planches de 1092 px de large au plus, donc regardées sans réduction. Aucune photo de tiers n'a été ouverte pour ce lot. Les fréquences citées du dossier 13 sont des comptes de mentions dans `observations.json`, sur 72 sites choisis par thème : indicatif, avec un biais de sélection.
- **Pages des documents locaux** : index du fichier PDF (1 = première page), repérés par recherche de mots et relus par sondage. La page imprimée est indiquée quand elle a été vérifiée.
- **Score.** Il se calcule en trois temps :
  - fréquence par contexte, de 0 à 4 : U (urbain), P (périurbain), R (rase campagne), A (autoroutes et voies rapides) ;
  - fréquence = 1 + Σ poids × fréquence, de 1 à 5 ; les poids sont un choix [G] déclaré et modifiable : U 0,40, P 0,25, R 0,20, A 0,15 ;
  - score = impact (1 à 5) × fréquence, de 1 à 25.
  - Priorités : **P1** ≥ 15, **P2** de 10 à 15, **P3** de 6 à 10, **P4** < 6.
  - Impact : 5 = casse la scène ou fausse un comportement ADAS ; 4 = visible au premier regard ; 3 = visible pour un œil attentif ; 2 = détail ; 1 = négligeable.
- **Effort** : S ≤ 2 jours ; M de 3 à 7 jours ; L de 2 à 4 semaines ; XL plus d'un mois.
- **États** : *fait* = fabriqué et contrôlé sur au moins une scène ; *partiel* = porté par le modèle ou fabriqué en partie ; *absent* ; *en cours ailleurs* = workflow parallèle.

## 2. Ce que le générateur fabrique aujourd'hui (constat vérifié)

| Couche de la chaîne | État | Preuve |
|---|---|---|
| Description (simple, réseau, carrefours, giratoires, bretelles) | fait | FORMAT_DESCRIPTION § 1-15 ; résolveur réseau N1 (93 tests) |
| Tracé en plan (droite, arc, clothoïde) | fait | rg::graphe ; S11, E1_rue_clothoides |
| Profil en long, relief, terrain | absent | rg_niveau.h l. 5 (Z = 0) ; decor_l2b.py l. 820, 855 (socle, sol plat) |
| Profils en travers, bordures, caniveaux, trottoirs | fait | lots L1, L2, bordures (32 types) |
| Carrefours plans, giratoires, bretelles | fait (un carrefour par route) | J1-J6, G1-G4, A3-A4 ; README_RG l. 519-524 |
| Marquages | fait pour les familles courantes | L2b, L4, autoroute ; 11 gabarits jamais posés (§ 5) |
| Ouvrages d'art | absent (en cours ailleurs) | lecteur.py l. 32 : famille « ouvrages » non lue |
| Retenue | partiel : en ligne seulement | rg::autoroute (GBA, DBA, LBA, MVL, GS2, GS4, DE2) |
| Signalisation verticale et feux | placés dans le modèle, non fabriqués (en cours ailleurs) | carrefours.py l. 411-412, 1523, 1590-1627 |
| Éclairage, mobilier, assainissement posé | absent | aucune HDA ; assets au catalogue |
| Végétation, bâti | désactivé (étape ultérieure) | README_RG § 6 |
| Graphe de voies, trajectoires, conflits | carrefours plans seulement | fabriquer_marquages_carrefour.py l. 240-297 |
| OpenDRIVE, ZoneGraph | absent | PLAN_GENERATEUR L7, § 7 |

## 3. Grille complète par famille

Colonnes : état ; ce qui manque et sa preuve ; règles disponibles → à trouver ; assets disponibles → à créer ; effort ; fréquence U / P / R / A (0 à 4) ; impact ; score ; priorité. Les priorités entre parenthèses sont hors classement : en cours ailleurs, étape ultérieure ou levier de méthode. Une fonctionnalité faite n'a ni score ni priorité ici (le JSON garde son poids).

### TR — Tracé, profil en long, relief et terrassements

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| TR-01 | Tracé en plan : droites, arcs, clothoïdes | fait | rg::graphe (README_RG § 3) ; scènes S11 (R 60), ex01 (R 150), E1_rue_clothoides ; contrôle L1 (flèche ≤ 0,5 mm) | RF-GV-RAY-*, RF-GV-PT-014 → règles de tracé ARP / ICTAVRU / VSA 90-110 non versées (CHAINE L-01) | — | — | 4/4/4/4 | 4 | — | — |
| TR-02 | Profil en long : déclivités, raccordements, points hauts et bas | absent | chaussée ancrée à Z = 0 sur chaque route ; profil_long jamais lu ; pas de MNT — hda/commun/vex/rg_niveau.h l. 5 (ancrage Z = 0) ; CHAINE R-03 ; aucun mot « declivite », « altitude », « layer » dans reseau/ ni description/ — fréquence : relief partout hors plaine ; Grenoble : rampes des échangeurs, piémont de Chartreuse | RF-GV-CAR-005, RF-GV-GIR-022, RF-MA-TRO-003, RF-OSM-OUV-001 → ARP 2022 (DocRoute 10, sources) p. PDF 61-62, 78, 85-86 ; ICTAVRU p. PDF 33-34, 92 ; VSA 90/110 p. PDF 15, 18, 49-50 ; Règles de visibilité (madoc) p. PDF 13, 22, 33-42 ; en ville aucune règle (CHAINE L-02) | à créer : MNT / LiDAR HD des chantiers (CHAINE L-08) | L | 3/3/4/4 | 4 | 17,4 | P1 |
| TR-03 | Dévers en courbe, variation de dévers (gauchissement) | absent | seuls le toit 2,5 % et la pente unique existent ; aucun dévers lié à la courbure — commun/profil.py l. 675-702 (dévers dit ou déduit, sans courbure) ; aucune occurrence de RF-GV-DEV-002 dans le code | RF-GV-DEV-001, RF-GV-DEV-002, RF-GV-DEV-003 → VSA 90/110 et ICTAVRU (dévers des bretelles) à verser | — | M | 1/2/3/4 | 3 | 9,3 | P3 |
| TR-04 | Surlargeur en courbe | absent | aucune loi de largeur liée au rayon — le mot « surlargeur » du vocabulaire désigne un accotement revêtu (vocabulaire.py l. 99) | RF-GV-RAY-012 | — | S | 1/2/3/2 | 2 | 5,6 | P4 |
| TR-05 | Terrain naturel et abords (relief, raccord au terrain, sol hors emprise) | absent | rendu sur sol plat neutre et socle à coupe nette ; abords décrits (zones) mais non rendus — rendu/decor_l2b.py l. 820 (socle_jupe), l. 855 (sol_plat) ; CHAINE R-08 ; rendus regardés : A1, A3, S01, nœud A41/N87 sur fond uni — fréquence : toute scène hors centre dense ; la route « flotte » aujourd'hui | RF-OSM-BDT-* → aucune règle : MNT mesuré (provenance mesure:mnt) | décor de l'étape 2 désactivé (--decor-etape2) → HDA rg::terrain (lot N9) ; matériaux de terre, herbe sèche, rochers | L | 2/3/4/4 | 5 | 19,8 | P1 |
| TR-06 | Talus de déblai et de remblai (pente, hauteur, raccord, végétation) | partiel | la bande « talus » est une bande plate de largeur donnée ; ni pente, ni hauteur, ni crête, ni pied — commun/profil.py l. 40 (TYPES_TERRAIN) ; vocabulaire.py l. 108 ; nœud A41/N87 « talus 2 » plat | CAND-E4-001, CAND-E4-002 → ARP p. PDF 28, 39, 72, 108 ; Cerema Dispositifs de retenue (2022) p. 22-25 imprimées ; GTR (Sétra-LCPC) pour les pentes types : à obtenir | à créer : profil de talus paramétrique, matériaux (terre, enherbé, enrochement) | L | 1/2/3/4 | 4 | 12,4 | P2 |
| TR-07 | Fossés, noues et bermes en creux | partiel | bandes plates « fosse », « noue », « berme » : pas de profil en V ou trapézoïdal, pas de fil d'eau — commun/profil.py l. 40 ; vocabulaire.py l. 106-107 | GA-ASS-* (regles_conception.json du dépôt) → Sétra, Assainissement routier, guide technique 2006 (à télécharger) ; ARP p. PDF 39, 100, 108 ; Cerema Dispositifs de retenue p. PDF 10, 25-28 (fossés, cunettes) | à créer : profil de fossé paramétrique | M | 0/2/4/3 | 3 | 8,2 | P3 |
| TR-08 | Murs de soutènement, murets, enrochements | absent | un « muret » observé est écrit GBA faute de mieux (nœud A41/N87) ; profil MURET_TALUS seulement dans la table des bordures — commun/bordures_catalogue.py l. 66 ; meylan/auto_noeud_a41_n87/description.yaml l. 92 — fréquence : « mur / muret » cité sur 10 des 72 sites du dossier 13 | à trouver : GPOA p. PDF 294-296 (murs) ; guide Sétra des murs de soutènement à rechercher | à créer : murs béton, gabions, enrochements, couronnement | M | 2/2/2/2 | 3 | 9,0 | P3 |
| TR-09 | Merlons et buttes paysagères | absent | aucun objet | à trouver : ARP p. PDF 39, 109 | à créer : butte paramétrique (via rg::terrain) | S | 0/1/1/2 | 2 | 3,5 | P4 |
| TR-10 | Route de montagne : lacets, épingles, parapets, murs, pare-blocs | absent | aucune scène ; dépend du profil en long, des surlargeurs, des murs et des talus — fréquence : faible au niveau national, forte en Isère (Chartreuse, Vercors, Belledonne) | RF-GV-RAY-012, RF-SV-J4 → ARP (rayons minimaux, enchaînements) p. PDF 59-63 ; guide spécifique montagne à rechercher (Cerema) | balises J1, J4 (catalogue) → parapets maçonnés, filets pare-blocs, murs de soutènement | L | 0/1/2/0 | 4 | 6,6 | P3 |
| TR-11 | Ajustement d'un tracé régulier sur une polyligne (OSM, photo, ortho) | absent | lot N2 non fait : routes OSM en onglet, replis aux sommets — README_RG § 8 ; CHAINE R-09 ; besoin B14 (BESOINS_FORMAT_AUTO) — fréquence : surtout utile pour la reconstruction fidèle (Meylan) | RF-GV-DEV-002, RF-GV-DEV-003 | — | L | 2/2/2/2 | 2 | 6,0 | P3 |

### PR — Profils en travers : catégories de voies

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| PR-01 | Rue urbaine : trottoirs, bordures (32 types), caniveaux, stationnement longitudinal | fait | S02, S03, ex02, ex08 ; lot bordures (README_RG § 13) ; rendus S03 regardés | RF-OSM-LAR-*, DEF-004, DEF-005, RF-AS-profil_* | 104 bordures, 24 caniveaux | — | 4/3/1/0 | 5 | — | — |
| PR-02 | Stationnement en épi, en bataille, marquage des places | partiel | bande d'épi ou de bataille admise par le vocabulaire, jamais éprouvée ; marquage transversal des places non dessiné (champ marquage_places compilé seulement) — description_vers_modele.py l. 302-306 ; aucune scène en épi ; rendu S03 : seule la T'2 longitudinale | RF-MQ-STA-01, RF-MQ-STA-09, RF-OSM-LAR-041 | — | M | 3/2/0/0 | 3 | 8,1 | P3 |
| PR-03 | Bandes et pistes cyclables (uni, bi, niveau intermédiaire) | fait | S04, S05, ex12, ex05 | RF-MA-PIS-*, RF-MA-BAN-*, DEF-007, DEF-008 | — | — | 3/3/1/0 | 4 | — | — |
| PR-04 | Avenue 2 × 2 à terre-plein central (planté, hachuré, franchissable) | fait | S06, ex04, J5, J6 | RF-GV-TPC-*, DEF-020 | îlots préfabriqués (9) | — | 2/3/1/0 | 4 | — | — |
| PR-05 | Rue à sens unique, voies de même sens | fait | S07, ex08 | RF-OSM-MRQ-011 | — | — | 3/1/0/0 | 3 | — | — |
| PR-06 | Zone 30 : porte d'entrée (B30, marquage « ZONE 30 », anneau 30), plateaux, coussins | partiel | ralentisseurs faits ; entrée de zone absente (ni panneau, ni inscription, ni anneau E.1, ni effet de porte) — S08, S10, ex07, G3 (zone 30) ; aucun gabarit ZONE 30 / anneau 30 utilisé — fréquence : ville à 30 généralisée dans la Métropole de Grenoble (GAM-F16) | RF-SV-B30.ZONE30, RF-MQ-INS-TXT-04, RF-MQ-INS-TXT-06, RF-MA-ZCA-001, RF-MQ-RAL-04 → forme de l'anneau E.1 non cotée par l'IISR (dossier 08 § 14) | glyphes, ANNEAU_LIMITATION_50 (modèle de forme) → anneau 30 vectorisé | S | 2/1/0/0 | 3 | 6,1 | P3 |
| PR-07 | Zone de rencontre et aire piétonne (plain-pied, caniveau central, B52 / B54, figurines dilatées) | partiel | catégorie et vitesse 20 seulement ; aucune scène ; pas de chaussée de plain-pied à caniveau central — description_vers_modele.py l. 148, 164 ; vocabulaire.py l. 268 | RF-OSM-VIT-004, RF-MA-ZCA-001, RF-MQ-INS-TXT-06 → Cerema, fiches zones de circulation apaisée (à télécharger) | dalles, pavés, caniveaux CC → figurines B52 / B54 au sol | M | 1/0/0/0 | 3 | 4,2 | P4 |
| PR-08 | Chaussée à voie centrale banalisée (CVCB, « chaucidou ») | partiel | vocabulaire présent, aucune scène, contrôle non éprouvé — vocabulaire.py l. 64, 72-73 | RF-MA-CVCB-* | — | S | 1/2/1/0 | 2 | 4,2 | P4 |
| PR-09 | Voie verte et piste indépendante (barrières d'accès, croisements) | partiel | type et catégorie présents, aucune scène ; ni barrières d'accès ni croisement de route — vocabulaire.py l. 71, 269 | RF-MA-VV-001, RF-MA-VV-003, RF-MA-VV-004, RF-MA-VV-005 | barrières (6) → barrière de voie verte, chicane | M | 1/2/2/0 | 2 | 4,6 | P4 |
| PR-10 | Vélorue, rue partagée | absent | aucun type | RF-MA-VLR-001 | — | S | 1/0/0/0 | 2 | 2,8 | P4 |
| PR-11 | Contre-allée (desserte parallèle séparée) | absent | besoin A9 non porté — meylan/BESOINS_FORMAT.md A9 | RF-OSM-PRF-001 | — | M | 1/1/0/0 | 3 | 4,9 | P4 |
| PR-12 | Route bidirectionnelle hors agglomération (rives, BDD, accotements) | fait | S01, ex01, J2, G2 ; rendu S01 regardé (ni terrain, ni balises, ni panneaux : voir TR-05, SV-*, EQ-11) | RF-MQ-SC-01, RF-MQ-SC-10, RF-GV-PT-009, RF-GV-DEV-001 | — | — | 0/3/4/0 | 5 | — | — |
| PR-13 | Route étroite < 5,20 m (sans axe, marques MRE) | partiel | axe supprimé sous 5,20 m ; marques MRE (gabarit présent) jamais posées — gabarit MRE non utilisé (grep) | RF-MQ-SC-02, RF-MQ-MRE-01, RF-OSM-MRQ-010 | gabarit MRE (dossier 08) | S | 1/2/3/0 | 2 | 5,0 | P4 |
| PR-14 | Route à 3 voies, 2 + 1, créneaux de dépassement, ligne mixte | absent | ni profil 2 + 1 alterné, ni ligne mixte, ni affectation de la voie centrale — aucune scène ; RF-MQ-MIX-01 non utilisée | RF-MQ-SC-03, RF-MQ-MIX-01, RF-MQ-VIS-04, RF-GV-PT-014 → ARP 2022 p. PDF 19-24, 46-53 (créneaux) ; Cerema 2 × 1 voie 2021 p. PDF 4-33 ; Catalogue des types de routes p. PDF 21-36 | — | M | 0/1/2/1 | 3 | 5,4 | P4 |
| PR-15 | Zones de dépassement interdit calculées depuis la visibilité | partiel | évènement décrit à la main ; aucun calcul de visibilité (dépend du profil en long et des courbes) — FORMAT_DESCRIPTION § 8 | RF-MQ-VIS-01, RF-MQ-VIS-02, RF-MQ-VIS-03, RF-MQ-PS-04, RF-MQ-PS-05 → Règles de visibilité (madoc) p. PDF 11-42 | — | M | 0/1/3/0 | 3 | 5,6 | P4 |
| PR-16 | 2 × 2 nationale, voie express, 2 × 1 à chaussées séparées | partiel | profils d'autoroute réutilisables ; catégorie voie_express sans scène ; 2 × 1 séparée absente ; C107 / C108 absents — vocabulaire.py l. 267 ; scenes_autoroutes A1-A4 seulement | RF-MQ-SC-05, RF-MQ-U-01, RF-GV-TPC-007 → Cerema 2 × 1 voie 2021 (local) ; ICTAAL 2015 (fiche Cerema, à obtenir) | — | M | 0/2/2/3 | 3 | 7,1 | P3 |
| PR-17 | Voie rapide urbaine (rocade, VRU) | partiel | profils d'autoroute ; règles ICTAVRU non versées sauf deux — CHAINE L-01 ; site meylan auto_n87_rocade_sud | RF-GV-PT-008, RF-GV-TPC-002 → ICTAVRU 2009 (local) p. PDF 31-34, 50, 85-94 | — | M | 0/2/0/3 | 3 | 5,8 | P4 |
| PR-18 | Autoroute 2 × 2 / 2 × 3 en section courante | fait | A1, A2 ; rendus regardés (GBA, glissières) | RF-MQ-SC-06, RF-MQ-U-01, RF-GV-TPC-008 | retenue (21) | — | 0/0/0/4 | 5 | — | — |
| PR-19 | Transitions : élargissement, rabattement, biseau, ouverture, fermeture | fait | S09, ex06, ex09, ex10 ; FORMAT § 15.5 | RF-MQ-OBL-*, RF-MQ-RAB-*, RF-GV-PT-014 | — | — | 2/2/2/3 | 4 | — | — |
| PR-20 | Ralentisseurs : dos-d'âne, plateau, coussin | fait | S08, S10, ex07 | RF-MA-RAL-001, RF-MQ-RAL-01, RF-MQ-RAL-02, RF-MQ-RAL-03, DEF-034 | — | — | 2/1/0/0 | 3 | — | — |
| PR-21 | Chicanes, écluses, rétrécissements à sens alterné (B15 / C18) | absent | aucun évènement — vocabulaire.py (aucun mot) | RF-SV-B15.C18, RF-MQ-ALT-01, RF-MA-TRO-009 → Cerema PAS VII06 Chicane (local, DocRoute 10) | potelets, jardinières (à créer) → jardinières | M | 1/2/1/0 | 3 | 6,3 | P3 |
| PR-22 | Traverse d'agglomération : porte d'entrée, îlot séparateur d'entrée, transition de profil | absent | aucune scène ; EB10 / EB20 non posés | RF-SV-EB.POSITION, RF-SV-EB10.PRESCRIPTIONS, RF-SV-B14.EMPLOI → CERTU PAS VII04 Îlot séparateur d'entrée d'agglomération (local, DocRoute 10) | — | M | 0/3/2/0 | 4 | 8,6 | P3 |

### CP — Carrefours plans et giratoires

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| CP-01 | Carrefours en T et en croix : priorité à droite, cédez, STOP | fait | J1, J2 ; carrefours.py l. 455-507 | RF-MQ-CED-*, RF-MQ-STOP-*, DEF-012, DEF-013, ARB-19 | — | — | 4/4/3/0 | 5 | — | — |
| CP-02 | Carrefours à feux : phases, ligne d'effet, sas vélo, contrôleur | fait | géométrie et contrôleur faits ; les feux eux-mêmes ne sont pas fabriqués (FE-01) — J3, J5, J6 ; rendu J5 regardé (sas, ligne d'effet) | RF-FEU.*, DEF-015, DEF-016, DEF-027, DEF-028, ARB-01 | — | — | 3/2/0/0 | 5 | — | — |
| CP-03 | Îlots séparateurs, directionnels, gouttes d'eau, refuges | fait | J4, J5, G1-G4 | RF-GV-ILO-*, DEF-022, RF-GV-GIR-013 | îlots préfabriqués (9) | — | 3/3/2/0 | 4 | — | — |
| CP-04 | Carrefour complexe : TAG guidés, zone de conflit, trajectoires balayées | fait | J5, J6 ; L4 (trajectoires.json, zone_conflit.json, guidage.json) ; correction étape 2 (balayages sur trajectoires finales) | RF-GV-TRJ-006, RF-MQ-GUI-01, RF-MQ-CAR-02, RF-MQ-CAR-03, ARB-08 | — | — | 2/1/0/0 | 5 | — | — |
| CP-05 | Branches courbes ou très obliques près d'un carrefour, carrefour en Y | absent | branches rectilignes exigées au voisinage du carrefour — README_RG l. 519 ; FORMAT_DESCRIPTION § 15.7 (limites) | RF-GV-RAY-* | — | L | 3/3/2/1 | 3 | 10,5 | P2 |
| CP-06 | Carrefour sur chaussées séparées (plusieurs nœuds de feux), demi-carrefour sur 2 × 2 | absent | besoin A18 non porté ; demi-carrefour interurbain absent — meylan/BESOINS_FORMAT.md A18 | RF-GV-ILO-007, RF-GV-VS-018, RF-GV-VS-008 | — | L | 2/2/1/0 | 3 | 7,5 | P3 |
| CP-07 | Carrefour surélevé (plateau sur tout le carrefour) | absent | aucune clé — carrefours.py : aucune occurrence de « plateau » | RF-MA-RAL-001, DEF-034 → Cerema PAS V03 Carrefour plateau surélevé (local) | — | M | 1/1/0/0 | 2 | 3,3 | P4 |
| CP-08 | Ouverture de terre-plein pour tourne-à-gauche ou demi-tour | absent | aucune clé | RF-GV-TPC-014, RF-GV-VS-008 → rayon de demi-tour non chiffré (00_SYNTHESE § 18) | — | M | 2/2/1/0 | 3 | 7,5 | P3 |
| CP-09 | Traversées cyclables de carrefour (IISR : doubles chevrons, figurines ; styles locaux) | absent | besoin A2 ; gabarit DOUBLE_CHEVRON_CEREMA présent mais jamais posé — grep : DOUBLE_CHEVRON non utilisé | RF-MQ-CYC-03, RF-OBS-MAR-01, RF-MA-CAR-* | gabarits VELO, DOUBLE_CHEVRON_CEREMA | S | 2/2/0/0 | 3 | 6,9 | P3 |
| CP-10 | Giratoires urbain, périurbain, mini, multivoie | fait | B21-1, AB25, J5 dans le modèle mais non fabriqués (SV-01) — G1-G4 ; rendu G1 regardé | RF-GV-GIR-*, RF-MQ-GIR-*, DEF-024 | éléments Ariane, giratoire franchissable | — | 2/3/2/0 | 5 | — | — |
| CP-11 | Giratoire : îlot central composé, bande cyclable annulaire, bras entrée seule / sortie seule, shunt | partiel | besoins A4, A5 ; shunt de giratoire non porté — meylan/BESOINS_FORMAT.md A4, A5 | RF-GV-VS-016, RF-GV-VS-017, RF-MA-GIR-002, RF-OBS-GIR-04 | à créer : muret d'îlot, butte | M | 1/2/1/0 | 2 | 4,2 | P4 |
| CP-12 | Double giratoire, giratoire allongé, giratoire à feux, giratoire traversé par un tram | absent | aucune clé | à trouver : Cerema SdB fiche 36 Doubles giratoires urbains (local) ; Cerema Giratoires et tramways 2017 (local, non exploité) | — | L | 1/1/0/1 | 3 | 5,4 | P4 |
| CP-13 | Carrefour à 5 branches et plus, place | partiel | non éprouvé (aucune scène) | RF-SV-CARREFOUR.COMPLEXE | — | M | 1/0/0/0 | 2 | 2,8 | P4 |
| CP-14 | Caniveau, ralentisseur et nivellement dans le cœur du carrefour | partiel | pas de caniveau dans les coins ; cœur par interpolation harmonique (pas de plan coté) — README_RG l. 519-524 ; § 15 (limites restantes) | TQ-SOL-014, GA-CHA-003 | caniveaux courbes (12) | M | 3/2/0/0 | 2 | 5,4 | P4 |

### EC — Échangeurs, autoroutes et voies rapides

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| EC-01 | Bretelles d'entrée (insertion) et de sortie (déboîtement), musoirs à chevrons | fait | A3, A4 ; rendu A3 regardé | RF-MQ-INS-*, RF-MQ-DEC-*, RF-MQ-MUS-01, RF-MQ-HACH-02 → obliquité contrôlée sur VSA 90/110 p. 38 | — | — | 0/1/0/4 | 5 | — | — |
| EC-02 | Voie d'entrecroisement | absent | décrite seulement par une suite de profils — aucune clé | RF-MQ-DEC-01, RF-MQ-LAR-B1b, RF-SV-INSERTION.AB3A → VSA 90/110 p. PDF 25, 32, 39, 49-51, 62-64 ; ICTAVRU p. PDF 55, 64-66, 81-82, 95-100 ; VSA Voies auxiliaires 2020 p. PDF 11 | — | M | 0/1/0/3 | 3 | 5,1 | P4 |
| EC-03 | Bifurcation et convergence de chaussées (juxtaposition 2 + 2, affectation) | partiel | bifurcation de bretelle seulement ; convergence 2 + 2 et divergence jumelée non représentables (B2) — meylan/BESOINS_FORMAT_AUTO.md B2 ; RESULTATS_ETAPE3_PASSE1 (décalage de 4,8 m) | RF-MQ-INS-02, RF-MQ-INS-03, RF-MQ-DEC-03 → VSA 90/110 p. PDF 30-31 | — | M | 0/1/0/3 | 4 | 6,8 | P3 |
| EC-04 | Diffuseur en losange (et losange éclaté) | absent | aucun gabarit d'échangeur ; demande ouvrages, profil en long, carrefours de raccordement — FORMAT_DESCRIPTION_RESEAU § 7.4 : l'échangeur ne fait que regrouper des objets — fréquence : chaque sortie d'autoroute ou de voie rapide en a un | RF-SV-J14 → ICTAVRU p. PDF 63-65, 77-79 ; VSA 90/110 p. PDF 66 (typologie) ; guide Sétra 2013 « Les échangeurs sur routes de type autoroute » (à obtenir) | — | XL | 0/1/1/4 | 5 | 10,2 | P2 |
| EC-05 | Demi-trèfle, trèfle, trompette, giratoire dénivelé | absent | aucun gabarit | à trouver : ICTAVRU p. PDF 77-81 ; VSA 90/110 p. PDF 66-67 ; guide Sétra 2013 (à obtenir) | — | XL | 0/0/0/3 | 5 | 7,2 | P3 |
| EC-06 | Nœud autoroutier (bretelles semi-directes, ouvrages superposés) | absent | nœud A41 / N87 décrit, fabriqué à plat sans ouvrage — rendu meylan_auto_noeud_a41_n87 regardé ; description.yaml l. 122-126 (ouvrages en extensions_auto) | RF-OSM-OUV-001 → ICTAVRU p. PDF 63-100 ; guide Sétra 2013 | — | XL | 0/0/0/2 | 5 | 6,5 | P3 |
| EC-07 | Bretelles en boucle et bretelles bidirectionnelles (rayon, dévers, profil en long) | partiel | tracé arc / clothoïde possible ; ni dévers ni profil en long — A3, A4 droites ; hélice de Meylan à plat | RF-GV-DEV-002 → VSA 90/110 p. PDF 13-15, 41-44 ; ICTAVRU p. PDF 89-94 | — | M | 0/1/0/3 | 4 | 6,8 | P3 |
| EC-08 | Barrière de péage (élargissement, cabines, auvent, voies télépéage) | absent | aucun objet | RF-FEU.R23 → IISR5 p. PDF 15-17, 39, 46-52 (signalisation) ; guide de conception des gares de péage à rechercher | à créer : auvent, cabines, îlots de péage, barrières | L | 0/0/0/2 | 4 | 5,2 | P4 |
| EC-09 | Aires de repos et de service (accès, parkings PL, bâtiments) | absent | besoin B4 non porté — meylan/BESOINS_FORMAT_AUTO.md B4 | à trouver : ICTAVRU p. PDF 188 ; guide Sétra 2013 (accès aux aires annexes) ; IISR5 p. PDF 22, 33, 64 | à créer : bâtiments, abris, mobilier d'aire | L | 0/0/0/1 | 3 | 3,4 | P4 |
| EC-10 | Voie de détresse (lit d'arrêt, damier rouge et blanc) | absent | gabarit CARREAU_DETRESSE présent, jamais posé — grep : CARREAU_DETRESSE non utilisé | dossier 08 § 16 (IISR7 art. 118-10) | gabarit CARREAU_DETRESSE → lit de gravier | S | 0/0/1/1 | 2 | 2,7 | P4 |
| EC-11 | Début et fin d'autoroute, vitesses par sens (C207 / C208, B14) | absent | besoins B10, B11 — meylan/BESOINS_FORMAT_AUTO.md B10, B11 | RF-OSM-VIT-003, RF-SV-B14.EMPLOI → IISR5 (C207, C208) | faces C207, C208 | S | 0/1/0/2 | 2 | 3,1 | P4 |

### OA — Ouvrages d'art et ouvrages hydrauliques

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| OA-01 | Pont courant (PI, PS, PO) : tablier, piles, culées, corniches, garde-corps, joints | en cours ailleurs | rien n'est fabriqué à ce jour ; famille « ouvrages » non lue par Houdini — hda/rg_lire_modele/lecteur.py l. 32 (NON_LUS_L1) ; nœud A41/N87 à plat — *workflow parallèle (ponts / ouvrages)* — fréquence : pont relevé sur 8 des 72 sites du dossier 13 | RF-GV-PON-001 à -016, DEF-033, RF-OSM-OUV-001, RF-OSM-OUV-002, RF-OBS-PON-01, RF-OBS-PON-02 → GPOA (local) ; Joints de chaussée 2016 (local) | garde-corps (4) → corniches, appareils d'appui, BN1 / BN2 / BN4 | XL | 2/2/2/3 | 5 | 15,8 | (P1) |
| OA-02 | Passerelle piétons et cycles | en cours ailleurs | voir OA-01 — *workflow parallèle (à vérifier)* | RF-MA-VV-002, RF-GV-PON-006, RF-GV-PON-007 | garde_corps_pont_S8_cycles_L30 | L | 1/1/1/1 | 3 | 6,0 | (P3) |
| OA-03 | Pont sur cours d'eau (berges, perrés, piles en rivière) | absent | ni eau ni berge — *à coordonner avec le workflow ponts* — fréquence : Isère : ponts de Meylan, Grenoble | RF-GV-PON-* → GPOA (local) | à créer : berges, perrés, surface d'eau | L | 1/1/1/1 | 4 | 8,0 | P3 |
| OA-04 | Pont-rail et passage sous voie ferrée (gabarit, B12) | absent | aucune voie ferrée — *à coordonner avec le workflow ponts* | RF-GV-PON-012, RF-SV-B12.HAUTEUR | à créer : voie ferrée, ballast, caténaire | L | 1/1/1/0 | 3 | 5,6 | P4 |
| OA-05 | Viaduc (grandes portées, piles hautes) | absent | *à coordonner avec le workflow ponts* | RF-GV-PON-015 | à créer : piles hautes | L | 0/0/1/1 | 3 | 4,1 | P4 |
| OA-06 | Tunnel, tranchée couverte, trémie urbaine | absent | aucun objet ; tunnel=* lu par l'inférence seulement — RF-OSM-OUV-001 (inférence) | RF-OSM-OUV-001, RF-SV-DIM.HB_CARACTERES (tunnel) → CETU, Dossier pilote des tunnels, document Géométrie (1990) et Éclairage (à télécharger) ; ICTAVRU p. PDF 7-9, 24, 49, 54, 75, 108-160 | à créer : portail, voûte, piédroits, éclairage de tunnel, niches | L | 1/0/1/1 | 4 | 7,0 | P3 |
| OA-07 | Buses, dalots, ponceaux, têtes d'aqueduc | absent | — | à trouver : GPOA p. PDF 16, 114, 194, 254 ; Sétra Assainissement routier 2006 | à créer : têtes d'aqueduc | S | 0/1/2/1 | 2 | 3,6 | P4 |
| OA-08 | Passages à faune (supérieurs, inférieurs) | absent | — | à trouver : Cerema, guide des passages à faune (mise à jour des guides Sétra 1993 et 2005, à obtenir) ; GPOA p. PDF 123-127, 157-161 | — | L | 0/0/0/1 | 2 | 2,3 | P4 |
| OA-09 | Écrans acoustiques (section courante et sur ouvrage) | absent | — | à trouver : ICTAVRU p. PDF 107, 111-121 ; GPOA p. PDF 114-126, 152-175 | à créer : panneaux absorbants, poteaux HEA, écrans transparents | M | 1/1/0/2 | 3 | 5,8 | P4 |
| OA-10 | Joints de chaussée et dalles de transition | absent | *workflow ponts* | RF-GV-PON-011 → Joints de chaussée 2016 (local) | à créer : joint à peigne, joint à lèvres | S | 1/1/1/2 | 2 | 4,3 | P4 |

### EQ — Équipements : retenue, éclairage, clôtures, exploitation

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| EQ-01 | Séparateurs béton GBA, DBA, LBA, MVL le long d'une limite | fait | rg::autoroute (README_RG § 12) ; A1 ; rendu A1 regardé | RF-GV-TPC-002, RF-GV-TPC-003, RF-GV-TPC-008 | retenue_GBA_*, DBA_*, LBA_*, MVL_* | — | 0/1/0/3 | 4 | — | — |
| EQ-02 | Glissières GS2, GS4, DE2 le long d'une limite | partiel | posées seulement là où le profil les écrit ; pas de contournement de pile ni de double file décalée (B3) — hda/rg_autoroute/construire.py l. 44-45 ; nœud A41/N87 regardé | RF-GV-PON-009, RF-GV-PON-010 | retenue_glissiere_GS2/GS4/DE2_module_L400 | M | 0/2/3/4 | 4 | 10,8 | P2 |
| EQ-03 | Extrémités de dispositifs (abaissées, ancrées), raccords GBA-glissière, atténuateurs de choc | absent | les files commencent et finissent net — rg_autoroute : aucune extrémité ni atténuateur | à trouver : Cerema Dispositifs de retenue 2022 (local, non exploité, CHAINE L-05) | extrémités GBA/DBA/GS2/GS4 abaissées, 4 atténuateurs → terminal « queue de carpe », raccord NF 058, GR4, GRC (ASSETS_ROUTE_ETAPE3 § 10) | M | 0/2/3/4 | 3 | 8,1 | P3 |
| EQ-04 | Implantation de la retenue par règle (zone de sécurité, talus, obstacles, appuis) | absent | la retenue n'existe que si on l'écrit — CHAINE L-05 | RF-GV-TPC-008, RF-GV-PON-014, CAND-E4-001, CAND-E4-002, CAND-E4-003 → Cerema Dispositifs de retenue en section courante (2022, local) p. imprimées 19-54 ; VSA 90/110 p. 23 imprimée (zone de sécurité) | — | M | 0/2/3/4 | 4 | 10,8 | P2 |
| EQ-05 | Barrières de pont BN1, BN2, BN4 et garde-corps d'ouvrage | en cours ailleurs | voir OA-01 — *workflow ponts* | RF-GV-PON-007, RF-GV-PON-008, RF-GV-PON-009, RF-GV-PON-010, DEF-033 | garde-corps (4) → BN1, BN2, BN4 | M | 1/1/1/2 | 3 | 6,4 | (P3) |
| EQ-06 | Éclairage public (candélabres, pas, implantation en rue, giratoire, échangeur) | absent | aucune pose ; 8 candélabres au catalogue non utilisés — aucune occurrence « candelabre » / « eclairage » dans le code ; rendus sans mât — fréquence : candélabre relevé sur 11 des 72 sites (dossier 13) | RF-OBS-ECL-01, RI ECL-01 à ECL-05 (regles_implantation.json) → NF EN 13201 non lue (payante) ; ARP p. PDF 73-79 ; ICTAVRU p. PDF 23-27, 106-110 ; VSA Voies auxiliaires p. PDF 40-41 ; guide Cerema éclairage à rechercher | 8 candélabres (routiers 8-12 m, urbains 4-8 m) → luminaires photométriques, mâts à crosse double, candélabres de style | M | 4/3/1/1 | 4 | 14,8 | P2 |
| EQ-07 | Clôtures autoroutières, grillages faune, portails de service | absent | — | à trouver : ICTAVRU p. PDF 106-108 ; Cerema 2 × 1 p. PDF 7, 44 | à créer : clôture grillagée, poteaux, portails | S | 0/1/1/4 | 2 | 4,1 | P4 |
| EQ-08 | Postes d'appel d'urgence (PAU) et leur marquage | absent | — | RF-MQ-PAU-01 → Cerema Dispositifs de retenue p. PDF 21, 39, 74 ; VSA 90/110 p. PDF 61 ; IISR5 art. 78-1 p. PDF 23 | à créer : borne PAU orange, refuge | S | 0/0/0/3 | 2 | 2,9 | P4 |
| EQ-09 | Panneaux à messages variables (PMV) | absent | — | à trouver : IISR 9e partie (local) p. PDF 3-43 | à créer : PMV sur portique et sur mât | M | 0/1/0/2 | 3 | 4,7 | P4 |
| EQ-10 | Portiques, potences et hauts mâts de signalisation | absent | assets présents, aucune pose — aucune occurrence « portique » / « potence » dans le code — *à coordonner avec le workflow signalisation* — fréquence : portique ou potence relevé sur 6 des 72 sites | RF-SV-GEN.HAUTEUR.SURPLOMB, RF-SV-DIM.HB_CARACTERES → IISR5 p. PDF 44, 48, 57-60 ; GPOA (structures) | portique_signalisation_L1600, potence_signalisation_L600, potences de feux (4) → portiques à treillis de grande portée, potences doubles | M | 1/1/0/4 | 4 | 9,0 | P3 |
| EQ-11 | Balises J1, J3, J4, J5, J6, J11, J13, J14 | partiel | J3, J5, J14a placées dans le modèle, aucune fabriquée ; J1 / J4 (virages) jamais posées — carrefours.py l. 411-412, 1523 — *à coordonner avec le workflow signalisation* | RF-SV-J1, RF-SV-J3, RF-SV-J4, RF-SV-J5, RF-SV-J6, RF-SV-J11_J12, RF-SV-J13, RF-SV-J14 | 11 balises (J1, J3, J6, J11, J12, J13, J15a…) → J14a / J14b, J1 sur glissière, J7 | S | 1/3/3/3 | 3 | 9,6 | P3 |
| EQ-12 | Réseaux aériens et coffrets : poteaux EDF / télécom, armoires, caméras | absent | — | — | feu_armoire_commande → poteaux bois et béton, câbles, coffrets | M | 2/3/3/1 | 2 | 6,6 | P3 |
| EQ-13 | Bornes et repères kilométriques (PR) | absent | — | dossier 08 § 16 (IISR7 art. 118-12) | à créer : borne PR, plaquette | S | 0/1/3/4 | 2 | 4,9 | P4 |

### SV — Signalisation verticale

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| SV-01 | Signalisation de police (AB, B, C) : choix, placement, supports, ensembles | en cours ailleurs | le compilateur place AB3a, AB4, AB25, AB2, AB5, B21-1, C20a, C6, M9c… dans le modèle ; aucun panneau fabriqué ni rendu — carrefours.py l. 411-412 ; description_vers_modele.py l. 1092, 1759 ; rendus J5, G1, S01 sans panneau — *workflow parallèle (signalisation verticale + feux)* — fréquence : panneau relevé sur 19 des 72 sites | RF-SV-* (95 règles), DEF-025, DEF-026, ARB-04, ARB-20 | 600 panneaux, 39 supports, 24 ensembles montés | L | 4/4/4/3 | 5 | 24,2 | (P1) |
| SV-02 | Signalisation de danger (A) et ses distances | absent | aucune pose — *à coordonner avec le workflow signalisation* | RF-SV-A.DISTANCE, RF-SV-A13B.EMPLOI, RF-SV-A17.FEUX | 30 faces A, 2 ensembles A13 | S | 1/2/3/1 | 3 | 7,9 | P3 |
| SV-03 | Entrée et sortie d'agglomération EB10 / EB20, limitations B14 et leur répétition | absent | EB10 / EB20 sont des exemples à recomposer (nom de commune) ; B14 jamais posé automatiquement — panneaux_fr_catalogue.json (EB10, EB20 : « exemple de composition ») ; CHAINE CC-13 — *placement : workflow signalisation ; composition du texte : avec SV-05* — fréquence : B14 relevé sur 10 des 72 sites | RF-SV-EB.POSITION, RF-SV-EB10.PRESCRIPTIONS, RF-SV-B14.EMPLOI → IISR5 p. PDF 36, 78-80 | ensembles B14 30 / 50 / 70 / 90 → EB10 / EB20 composés (texte) | M | 1/3/3/2 | 4 | 12,2 | P2 |
| SV-04 | Indication (C) : C12, C13, C24 (affectation), C27, C107 / C108, C207 / C208 | partiel | C20a, C6, C24a placés dans le modèle (non fabriqués) ; C24 exigé par les flèches d'affectation — carrefours.py l. 411-412 — *workflow signalisation* | RF-SV-C12.EMPLOI, RF-SV-C24.EMPLOI, RF-SV-C27.RALENTISSEUR, RF-MQ-DIR-01 | 74 faces C, 4 ensembles C | S | 2/2/1/2 | 3 | 8,4 | P3 |
| SV-05 | Signalisation de direction : D20 (position, ex-D21), D30, D40 (D42, D43), D50, D60 (D61, D62), Da, Dc, Dp | absent | aucune pose ; faces D = exemples à recomposer (texte, cartouches, flèches) ; D21 / D20 absent du catalogue de faces — panneaux_fr_catalogue.json (259 « exemples de composition ») ; aucun code D2x dans les faces — *à coordonner avec le workflow signalisation* — fréquence : D21 relevé sur 9 des 72 sites | RF-SV-D21.POSITION, RF-SV-D.TEMPS_DE_PARCOURS, RF-SV-D.HAUTEURS, RF-SV-DIM.HB_CARACTERES, RF-SV-DIM.D_E_EB, RF-OBS-SIG-05 → IISR5 art. 79 à 84 p. PDF 42-58 ; NF P 98-532 (alphabets L1, L2, L4 et règles de composition des panneaux directionnels : norme, accès à obtenir) ; police numérisée libre à rechercher | 103 faces D (exemples), mâts directionnels Ø 89 / 114 → compositeur de panneaux (texte, cartouches E / SU / SE, flèches), polices | L | 3/3/3/4 | 4 | 16,6 | P1 |
| SV-06 | Signalisation autoroutière : présignalisation sur portique, numéros de sortie, D41 / Da | absent | besoin B9 ; ni portique ni panneau d'autoroute — meylan/BESOINS_FORMAT_AUTO.md B9 ; description nœud A41/N87 l. 130 (D41a relevé) | RF-SV-GEN.REPETITION_GAUCHE_2X2, RF-SV-DIM.CHOIX_GAMME, RF-SV-J14 → IISR5 p. PDF 44-60 ; guide Sétra 2013 (échangeurs) | portique L16, faces D41 / Da41 → panneaux autoroutiers composés (fond bleu), cartouches SE | L | 0/1/0/4 | 4 | 7,4 | P3 |
| SV-07 | Jalonnement cyclable (Dv) et piéton | absent | — | RF-SV-DV.POSITION, RF-MA-CYC-010 → IISR5 p. PDF 71-72 | faces Dv (exemples) → compositeur (SV-05) | S | 2/2/1/0 | 2 | 5,0 | P4 |
| SV-08 | Localisation et services : E (cours d'eau, lieux-dits), CE, H, SR, plaques de rue E60 | absent | — | RF-SV-E60.PLAQUE_RUE → IISR5 (local) | faces E, CE, H, SR → plaques E60 composées | S | 3/2/2/1 | 2 | 6,5 | P3 |
| SV-09 | Signalisation temporaire de chantier (K, AK, cônes, K16, alternat) | absent | besoin A8 ; l'option chantier a été retirée des descriptions (RESULTATS_ETAPE3_PASSE1) — meylan/BESOINS_FORMAT.md A8 — fréquence : marquage de chantier vu sur 5 sites (RF-OBS-MAR-03) ; cas difficile pour l'ADAS | RF-MQ-TMP-01, RF-OBS-MAR-03, RF-FEU.EXTENSION_EMPLOI → IISR 8e partie (local) p. PDF 3-46 | faces K et AK (temporaire_K : 10) → cônes, K16, K8, barrières de chantier, GBA plastique | M | 1/1/1/1 | 4 | 8,0 | P3 |
| SV-10 | Passage à niveau (G, A7 / A8, SAL, R24, barrières, rails) | absent | — | RF-MQ-PN-01, RF-FEU.R24.HAUTEUR, RF-FEU.R24.IMPLANTATION → IISR2 p. PDF 4, 10-15 ; arrêté du 18 mars 1991 (PN) à télécharger (Légifrance) | faces G (passage_niveau_G_balises_J) → barrières, SAL, rails, platelage | L | 1/1/1/0 | 3 | 5,6 | P4 |
| SV-11 | Miroirs, panneaux de rue, numéros | absent | — | RF-SV-GEN.MIROIR | à créer : miroir convexe | S | 1/1/0/0 | 1 | 1,6 | P4 |

### FE — Feux de circulation

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| FE-01 | Feux R11 + répétiteurs, R12, boutons d'appel : fabrication et pose | en cours ailleurs | placés et phasés dans le modèle (signaux, contrôleur) ; aucun feu fabriqué — carrefours.py l. 1590-1627 ; rendu J5 sans mât — *workflow parallèle (feux)* — fréquence : feux relevés sur 17 des 72 sites | RF-FEU.* (45), DEF-027, DEF-028, ARB-05, ARB-14 | 17 têtes de feux, 3 ensembles, mâts Ø 90 / 114 | M | 3/2/0/0 | 5 | 13,5 | (P2) |
| FE-02 | Potences, juxtaposition, R14 directionnels, R13 bus, R19 vélos, écran de contraste | en cours ailleurs | *workflow parallèle (feux)* | RF-FEU.R14, RF-FEU.JUXTAPOSITION, RF-FEU.OPTIQUE.CONTRASTE, RF-OBS-FEU-04 | 4 potences de feux, R13b, R13c, écran de contraste → R14, R19, pictogrammes R12 / R13c (ASSETS_ROUTE_ETAPE3 § 10) | M | 2/1/0/0 | 4 | 8,2 | (P3) |
| FE-03 | Feux d'alternat, de PN (R24), de contrôle d'accès et de péage (R23) | absent | — | RF-FEU.EXTENSION_EMPLOI, RF-FEU.R23, RF-FEU.R24.IMPLANTATION → IISR6 (local) | à créer : R23, R24 | M | 1/1/1/1 | 2 | 4,0 | P4 |
| FE-04 | États lumineux animés et synchronisés au plan de feux (Unreal) | absent | contrôleur exporté dans le modèle, rien côté UE — FORMAT § 15.3 (controleurs[]) — *à coordonner avec le workflow feux* | DEF-028, RF-GV-FEU-003 | à créer : matériaux émissifs pilotés | M | 3/2/0/0 | 4 | 10,8 | P2 |

### MQ — Marquages (IISR 7e partie)

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| MQ-01 | Lignes longitudinales (axes, rives, délimitations, T1 à T4, continues, doubles), u = 5 et 7,5 cm | fait | L2b (rg::marquages) ; S01-S12 ; A1-A4 | RF-MQ-MOD-*, RF-MQ-LAR-*, RF-MQ-SC-*, RF-MQ-U-* | — | — | 4/4/4/4 | 5 | — | — |
| MQ-02 | Lignes transversales : STOP, cédez, effet des feux | fait | ligne d'effet de passage piéton et d'alternat absentes — rg::carrefours_sol (README_RG § 9) | RF-MQ-CED-01, RF-MQ-STOP-01, RF-MQ-FEU-01, RF-MQ-PPE-01, RF-MQ-ALT-01 | — | — | 3/3/2/0 | 4 | — | — |
| MQ-03 | Flèches directionnelles et de rabattement | fait | L2b, L4 ; gabarits TD, TAG, TAD, RAB_D, RAB_G | RF-MQ-DIR-*, RF-MQ-RAB-*, DEF-017, ARB-11 | gabarits du dossier 08 | — | 3/3/2/3 | 4 | — | — |
| MQ-04 | Passages piétons, hachures, zébras, chevrons de musoir, guidage TAG | fait | L2b, L4, autoroute | RF-MQ-PP-*, RF-MQ-HACH-*, RF-MQ-MUS-01, RF-MQ-GUI-01, DEF-020 | — | — | 4/3/1/2 | 5 | — | — |
| MQ-05 | Ligne mixte et ligne d'annonce calculées | partiel | annonce posée avec la zone de dépassement interdit ; ligne mixte absente — RF-MQ-MIX-01 non utilisée | RF-MQ-MIX-01, RF-MQ-PS-04 | — | S | 0/1/3/0 | 2 | 3,7 | P4 |
| MQ-06 | Marquages cyclables : figurines encadrées début / fin, doubles chevrons, flèches ½, sas | partiel | figurines au pas et sas faits ; doubles chevrons, figurine encadrée, flèches ½ absents — J5 (sas) ; DOUBLE_CHEVRON non utilisé | RF-MQ-CYC-01, RF-MQ-CYC-03, RF-MQ-CYC-04, RF-MQ-SAS-01, RF-MQ-PRA-NAN-01 | VELO, DOUBLE_CHEVRON_CEREMA → figurine encadrée, flèche ½ cycliste | S | 3/2/0/0 | 2 | 5,4 | P4 |
| MQ-07 | Marquage du stationnement : places, PMR, IRVE, livraison (croix jaune), PAYANT, zone bleue | absent | gabarits PMR et IRVE présents, jamais posés ; aucun trait de place — grep : PMR, IRVE non utilisés ; rendu S03 | RF-MQ-STA-01 à -10 | gabarits PMR, PMR_X2, IRVE, glyphes | M | 3/2/0/0 | 3 | 8,1 | P3 |
| MQ-08 | Marques jaunes sur bordure et en rive (arrêt, stationnement gênants) | absent | — | RF-MQ-STA-04 | à créer : peinture sur face de bordure (aujourd'hui interdite par MQ-DET-010 pour le blanc) | S | 2/1/0/0 | 2 | 4,1 | P4 |
| MQ-09 | Transports collectifs : damier TC, BUS / TRAM répétés, interruption au carrefour | partiel | zigzag fait ; inscription BUS possible à la main ; damier jamais posé — description_vers_modele.py l. 1732 ; CARRE_DAMIER_TC non utilisé | RF-MQ-TC-01 à -04 | CARRE_DAMIER_TC, glyphes | S | 2/1/0/0 | 2 | 4,1 | P4 |
| MQ-10 | Inscriptions de zone : ZONE 30, anneaux 30 / 50, figurine piéton | absent | voir PR-06 | RF-MQ-INS-TXT-04, RF-MQ-INS-TXT-05, RF-MQ-INS-TXT-06 → formes E.1, E.2 non cotées (00_SYNTHESE § 18) | ANNEAU_LIMITATION_50, glyphes → anneau 30, figurine piéton | S | 2/1/0/0 | 2 | 4,1 | P4 |
| MQ-11 | Triangles cédez au sol (« dents de requin ») | absent | gabarit CEDEZ_V60 présent, jamais posé — grep : CEDEZ_V60 non utilisé | ARB-16, RF-OBS-MAR-05 | CEDEZ_V60, CEDEZ_V60P | S | 1/2/1/0 | 2 | 4,2 | P4 |
| MQ-12 | Marquage temporaire jaune (chantier) | absent | fréquence : cas d'école des essais ADAS de maintien dans la voie | RF-MQ-TMP-01, RF-OBS-MAR-03 → IISR8 p. PDF 10-12 | couleurs de peinture (jaune existe pour zigzag / livraison) | S | 1/1/1/1 | 3 | 6,0 | P3 |
| MQ-13 | Marquages autoroutiers complémentaires : surlargeur, PAU, points de repère | absent | gabarit BANDE_SURLARGEUR_1M présent, jamais posé — grep | RF-MQ-SUR-01, RF-MQ-PAU-01, RF-MQ-SC-12 | BANDE_SURLARGEUR_1M, RECTANGLE_POINT_REPERE | S | 0/0/1/3 | 2 | 3,3 | P4 |
| MQ-14 | Balisage d'obstacles, marquage de passage à niveau | absent | — | RF-MQ-OBS-01, RF-MQ-PN-01 | — | S | 1/1/1/0 | 2 | 3,7 | P4 |
| MQ-15 | Phase continue des tirets le long d'un itinéraire | absent | « chaque tronçon commence par un trait » [G] — hda/rg_marquages/marquages.vfl l. 435 ; CHAINE R-06 | RF-MQ-U-05 | — | M | 3/3/3/3 | 2 | 8,0 | P3 |
| MQ-16 | Usure fine : faïençage, effacement, marquages fantômes, reprises | partiel | usure globale par classe faite ; faïençage et fantômes absents (besoin A14) — FORMAT_DESCRIPTION § 6 ; BESOINS_FORMAT A14 | RF-OBS-REV-01 | peinture_<couleur>_u<usure> → décalques de fantômes | M | 3/3/3/2 | 3 | 11,6 | P2 |
| MQ-17 | Pratiques locales relevées : damier cyclable, Chronovélo, îlot ocre, anneau vert | absent | besoins A2, A3 ; styles admis seulement s'ils sont photographiés (§ 0.1) — BESOINS_FORMAT A2, A3 — fréquence : propre à la métropole grenobloise | RF-OBS-MAR-01, RF-OBS-MAR-02, RF-OBS-ILO-03, RF-OBS-GIR-07 | résine verte, enrobé ocre | S | 1/0/0/0 | 2 | 2,8 | P4 |

### MA — Modes actifs : piétons, cycles

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| MA-01 | Trottoirs, cheminement de 1,40 m, abaissés, BEV, refuges | fait | L2, L3 ; ex05 ; J4 | RF-MA-TRO-*, RF-MA-BEV-*, DEF-022, DEF-031 | dalles et BEV (10) | — | 4/3/1/0 | 4 | — | — |
| MA-02 | Séparateurs ponctuels de piste : potelets, balises, plots, jardinières | partiel | le séparateur bordé est fait ; les séparateurs ponctuels sont lus mais pas fabriqués — commun/profil.py l. 444-448 ; aucune HDA ne pose de potelet | RF-MA-SEP-*, RF-MA-SEP-011 | potelets (9), balise J11 → jardinières, plots | S | 2/2/0/0 | 3 | 6,9 | P3 |
| MA-03 | Réseau piéton et cyclable continu (CC-10, CC-11) | absent | contrôles de réseau non écrits — CHAINE § 4 | RF-MA-BAN-008 | — | M | 3/2/1/0 | 2 | 5,8 | P4 |
| MA-04 | Stationnement vélo (arceaux), abris vélo | absent | aucune pose | RF-MA-SVE-001 | 3 arceaux → abri vélo | S | 2/1/0/0 | 2 | 4,1 | P4 |
| MA-05 | Escaliers, rampes PMR, garde-corps urbains, passages inférieurs piétons | absent | besoin A12 — BESOINS_FORMAT A12 | RF-MA-TRO-003, DEF-033 | garde_corps_urbain_L20 → escaliers, rampes | M | 2/1/0/0 | 2 | 4,1 | P4 |
| MA-06 | Trottoir et piste traversants au débouché d'une rue | absent | aucune clé | RF-MA-CAR-010 | — | M | 1/1/0/0 | 2 | 3,3 | P4 |

### TC — Transports collectifs

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| TC-01 | Arrêt de bus : quai, zigzag, neutralisations | fait | abri, poteau et arrêt sans quai contigu absents (A11) — ex05 ; description_vers_modele.py l. 1732, 1759 | RF-MA-BUS-*, DEF-019, DEF-032, ARB-03 | abris bus (2), bordures quai → poteau d'arrêt | — | 2/2/1/0 | 3 | — | — |
| TC-02 | Couloirs bus, voies réservées | fait | S12 | RF-MQ-SC-08, RF-OSM-MRQ-031 | — | — | 2/1/0/0 | 3 | — | — |
| TC-03 | Tramway : plateforme, rails, quais, ligne aérienne, traversées, giratoire percé | absent | type voie_tram dans le modèle sans mot dans le vocabulaire ni fabrication — commun/profil.py l. 33 (voie_tram) ; vocabulaire.py (aucun mot tram) — fréquence : fort à Grenoble, nul à Meylan | RF-GV-RAY-009, RF-MQ-TC-03, RF-SV-B27A.EMPLOI, RF-FEU.R24.IMPLANTATION → Cerema Giratoires et tramways 2017 (local, non exploité) ; guide d'insertion urbaine du tramway (Certu / STRMTG) à rechercher | à créer : rails, plateforme engazonnée, poteaux LAC, quais | L | 1/0/0/0 | 4 | 5,6 | P4 |
| TC-04 | Arrêt sur accotement, en encoche, station BHNS | partiel | besoins A11, B4 — BESOINS_FORMAT A11 | RF-MA-BUS-* | — | S | 1/2/1/0 | 2 | 4,2 | P4 |

### AS — Assainissement

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| AS-01 | Caniveaux au pied des bordures (CS, CC) | fait | pas de caniveau dans les coins de carrefour — pj::caniveau 2.2 ; README_RG § 15 | TQ-BOR-007, RF-AS-profil_* | 24 caniveaux | — | 4/3/1/0 | 3 | — | — |
| AS-02 | Avaloirs, grilles, regards, tampons, bouches à clé (pose réglée) | partiel | grilles au pied des rampes et en bout de file seulement [G] ; ni pas, ni regards, ni tampons — README_RG § 8 (caniveau aux ralentisseurs) | GA-ASS-*, RF-MA-BUS-016 → Sétra Assainissement routier 2006 (à télécharger) | 5 assets d'assainissement → tampons de chaussée variés | M | 4/3/1/1 | 3 | 11,1 | P2 |
| AS-03 | Points bas, pente du fil d'eau, bassins de surface (CC-12) | absent | lot N5 — CHAINE E06 | GA-CHA-003, GA-CHA-004, TQ-SOL-014 | — | M | 3/2/1/1 | 2 | 6,1 | P3 |
| AS-04 | Fossés, cunettes, descentes d'eau sur talus, bassins de rétention | absent | voir TR-07 | GA-ASS-* → Sétra Assainissement routier 2006 ; Cerema Dispositifs de retenue p. PDF 25-28 | à créer : descentes d'eau, cunettes béton | M | 0/2/3/3 | 3 | 7,6 | P3 |
| AS-05 | Caniveau central (zone de rencontre, rue pavée) | absent | besoin A10 (variante) — BESOINS_FORMAT A10 | — | caniveaux CC | S | 1/0/0/0 | 2 | 2,8 | P4 |

### RV — Revêtements, aspect et conditions de rendu

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| RV-01 | Matériaux de chaussée et de trottoir (enrobés, béton, dalles, pavés) | fait | 34 matériaux de sol ; vocabulaire § 6 | RF-AS-regle_materiaux_elements | 48 PBR + 29 matériaux du site | — | 4/4/4/4 | 4 | — | — |
| RV-02 | Dégradations : pontages de fissures, rapiéçages, tranchées, faïençage, nids-de-poule | absent | besoin A14 ; aucune décalcomanie — BESOINS_FORMAT A14 — fréquence : observé sur les 8 sites du lot A | RF-OBS-REV-01 | enrobe_reprise_tranchee → décalques (graphe PG_Decalques) | M | 4/4/4/3 | 3 | 14,5 | P2 |
| RV-03 | Plaques de réseaux non hydrauliques (télécom, gaz, électricité), joints de dalles, reprises linéaires | absent | aucune pose (les regards d'assainissement sont en AS-02) | — | à créer : plaques télécom, gaz, chambres de tirage | S | 4/3/1/1 | 2 | 7,4 | P3 |
| RV-04 | Coutures de texture d'usure entre routes | absent | cartes d'usure lues en (s, t) de chaque route — rendu_l2b.py l. 963 ; CHAINE R-07 | — | — | M | 3/3/2/2 | 2 | 7,3 | P3 |
| RV-05 | Salissures, traces de pneus, taches, feuilles, sable en rive | absent | — | — | à créer : décalques | M | 3/3/3/2 | 2 | 7,7 | P3 |
| RV-06 | Conditions de rendu : nuit et rétroréflexion, chaussée mouillée, neige, ciel couvert | absent | ciel clair et soleil franc toujours (comparaison CONTROLE.md § Rendus) — comparaison/CONTROLE.md l. 194 | RF-SV-GEN.RETROREFLEXION, RF-MQ-RETRO-01 | à créer : matériaux rétroréfléchissants, eau, neige | L | 2/2/2/2 | 4 | 12,0 | P2 |

### MU — Mobilier urbain

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| MU-01 | Potelets, bornes, barrières de trottoir | absent | aucune pose — aucune occurrence « potelet » hors vocabulaire — fréquence : potelets relevés sur 8 des 72 sites | RF-MA-OBS-001, RF-MA-OBS-002, RI (regles_implantation.json) | potelets (9), barrières (6) | S | 3/2/0/0 | 3 | 8,1 | P3 |
| MU-02 | Bancs, corbeilles, abris, arceaux, bornes fontaines | absent | aucune pose | RF-MA-TRO-013, RF-MA-BUS-012 | 11 assets de mobilier | S | 2/1/0/0 | 2 | 4,1 | P4 |
| MU-03 | Jardinières, bacs, conteneurs, sanisettes, kiosques, totems | absent | — | — | à créer : conteneurs, jardinières | M | 2/1/0/0 | 2 | 4,1 | P4 |

### VB — Végétation et bâti (étape ultérieure)

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| VB-01 | Arbres d'alignement (essences, fosses, exclusions) | partiel | portés par le modèle et le décor de l'étape 2, désactivé à l'étape 1 — README_RG § 6 (étape 1 route seule) — *étape ultérieure (décision du 17/10/2026)* — fréquence : arbre relevé sur 13 des 72 sites | DEF-030, RF-OSM-VEG-001, RF-OBS-VEG-01, ARB-13 | 35 essences (vegetation.json, autre équipe) | M | 3/3/2/1 | 5 | 17,5 | (P1) |
| VB-02 | Îlots et terre-pleins plantés (strates, massifs, haies), visibilité 0,60 m | partiel | gazon seul ; strates non portées (A15) — BESOINS_FORMAT A15 — *étape ultérieure* | DEF-029, RF-GV-TPC-011, RF-OBS-GIR-04 | — | M | 3/3/2/1 | 4 | 14,0 | (P2) |
| VB-03 | Abords : prairie, champs, forêt, végétation de talus | partiel | zones décrites, non rendues — FORMAT_DESCRIPTION § 9 — *étape ultérieure* | — | — | M | 1/3/4/4 | 5 | 17,8 | (P1) |
| VB-04 | Bâti : façades, murs de clôture, portails, accès | absent | rg::vegetation_bati non écrite — PLAN_GENERATEUR § 2.3 (HDA 12) — *étape ultérieure* | à trouver : BD TOPO (bâti) | à créer : bâti procédural | XL | 4/3/1/0 | 5 | 17,8 | (P1) |

### CO — Comportements et exports (graphe de voies, trajectoires, conflits)

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| CO-01 | Graphe de voies des carrefours plans (voies, connecteurs, zones, ≤ 32 étiquettes) | fait | fabriquer_marquages_carrefour.py l. 240-297 ; RAPPORT_L4 L4-17 | RF-GV-TRJ-006 | — | — | 3/2/1/0 | 5 | — | — |
| CO-02 | Graphe de voies des sections courantes, giratoires, bretelles et bifurcations | absent | graphe_voies.json n'est écrit que par le lot L4 (carrefours plans) — sorties G1 (l3, l5) et A3 (autoroute) sans l4/graphe_voies.json | à trouver : 12M § 7 (DocRoute 12) | — | M | 3/4/3/4 | 4 | 17,6 | P1 |
| CO-03 | Trajectoires et conflits des giratoires et des bretelles, balayages | partiel | trajectoires de giratoire calculées par le compilateur, non balayées par la chaîne L3a / L4 ; aucune pour les bretelles — FORMAT § 15.4 ; README_RG § 14 | RF-GV-GIR-008, RF-GV-TRJ-006 | — | M | 2/3/2/3 | 4 | 13,6 | P2 |
| CO-04 | Export OpenDRIVE 1.4 (CARLA) et 1.8.1 | absent | rg::exporter_opendrive non écrite ; CARLA non installé — PLAN_GENERATEUR L7 ; CHAINE E18 — fréquence : toute scène destinée à la simulation ADAS | à trouver : ASAM OpenDRIVE 1.8.1 ; validateur autonome (esmini, libOpenDRIVE) | — | L | 4/4/4/4 | 3 | 15,0 | P1 |
| CO-05 | Import ZoneGraph dans Unreal | absent | script d'éditeur à écrire — PLAN_GENERATEUR § 7 | — | — | M | 3/3/3/3 | 3 | 12,0 | P2 |
| CO-06 | Branchement du modèle de trafic (DocRoute 17) sur le graphe pour éprouver les trajectoires | absent | prototype autonome (recon/trafic/prototype) — DocRoute 17, synthèse | — | — | M | 3/3/3/3 | 2 | 8,0 | P3 |

### RS — Continuité du réseau

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| RS-01 | Plusieurs carrefours sur une même route ; plan-masse et nivellement à l'échelle du réseau | absent | un seul carrefour par route, à son extrémité « fin » ; une nappe et un HeightField par route ; corridors de Meylan sans leurs carrefours — README_RG l. 524 ; CHAINE R-04, R-05 ; meylan/axe_verdun_centre/description.yaml l. 104 — fréquence : une rue entre deux carrefours est le cas le plus courant en ville | à trouver : CHAINE_CONSTRUCTION E05, E06 (lots N4, N5) | — | L | 4/3/2/1 | 4 | 15,6 | P1 |

### IM — Imaginer des scènes (nouvelle orientation)

| Id | Fonctionnalité | État | Ce qui manque — preuve | Règles : disponibles → à trouver | Assets : disponibles → à créer | Eff. | U/P/R/A | Imp. | Score | Prio. |
|---|---|---|---|---|---|---|---|---|---|---|
| IM-01 | Catalogue de typologies françaises (« routes types ») tiré de photos réelles | absent | les scènes de test sont des cas d'école ; aucune fiche de typologie (rue de centre ancien, faubourg, traverse de village, RD de plaine, route de montagne, 2 × 2, rocade, autoroute, échangeur, zone d'activités) — scenes_simples, scenes_carrefours, scenes_giratoires, scenes_autoroutes — fréquence : nouvelle orientation : imaginer des routes à partir d'images réelles | RF-OBS-*, DocRoute 13 → relevé de fréquences sur un échantillon national stratifié (IM-04) ; Cerema Catalogue des types de routes (local) | — | M | 4/4/4/4 | 4 | 20,0 | (P1) |
| IM-02 | Tirage de variantes plausibles et déterministes (largeurs, matériaux, usure, équipements, probabilités) | absent | chaque scène est écrite à la main ; aucune loi de tirage | ARB-16, RF-OBS-GIR-06, RF-OBS-ILO-04, DEF-024 → lois de fréquence à mesurer (IM-04) | — | M | 4/4/4/4 | 4 | 20,0 | (P1) |
| IM-03 | Description d'une scène par Claude depuis une photo (Panoramax, Mapillary) | partiel | boucle faite sur 3 rues et 15 sites de Meylan ; pas de procédure générique ni de contrôle de plausibilité — scenes_meylan M20, M24, M27 ; meylan/*/description.yaml ; comparaison/ | PLAN_GENERATEUR § 6.2 | — | M | 4/4/4/4 | 3 | 15,0 | (P1) |
| IM-04 | Relevé de fréquences d'éléments sur un échantillon national de photos | absent | dossier 13 : 72 sites choisis par thème (biais de sélection) — DocRoute 13 (observations.json) | à trouver : Panoramax (API publique) ; Mapillary (jeton local) | — | M | 4/4/4/4 | 3 | 15,0 | (P1) |
| IM-05 | Assembler un quartier ou un itinéraire imaginé (plusieurs tronçons, carrefours, giratoires) | partiel | résolveur réseau N1 et compositions faits ; limité par RS-01 — reseau/resoudre_reseau.py ; RESULTATS_ETAPE3_PASSE1 (5 compositions) | — | — | M | 4/3/2/1 | 4 | 15,6 | (P1) |

## 4. Règles : disponibles, à verser, à trouver

### 4.1 Ce que la base couvre déjà

`regles_route_fr.json` couvre bien le marquage (IISR 7 : 216 règles du volet 08), la signalisation verticale (95 règles), les feux (53), les carrefours plans (65), les giratoires (31), les modes actifs (cycles 103, piétons 58) et l'inférence OSM (80). Elle couvre mal :

- le tracé et le profil en long : 4 règles de dévers, aucune de déclivité en ville ;
- les échangeurs : seulement le marquage (RF-MQ-INS-*, RF-MQ-DEC-*) et la balise J14 ;
- la retenue le long d'une route : aucune règle d'implantation ;
- l'éclairage : une observation ;
- l'assainissement : rien dans la base ; règles GA-ASS-* dans les specs du dépôt ;
- les ouvrages autres que les ponts courants : tunnels, murs, buses, faune, écrans ;
- la composition des panneaux de direction : dimensions et temps de parcours seulement.

### 4.2 Documents déjà dans DocRoute, non versés dans la base

À verser par le propriétaire de la base (ce lot n'écrit pas dans `regles_route_fr.json`). Les PDF du Cerema interdisent la reproduction : paraphraser et citer la page.

| Document | Où | Pages | Sujets (pages) | Items |
|---|---|---|---|---|
| Cerema, ARP Aménagement des routes principales (2022) | DocRoute 10, sources | pages PDF | créneaux de dépassement 19-24, 46-53 ; clothoïdes 49, 58-60 ; rayons 59-63 ; déclivités 61-62, 78, 85-86 ; talus 28, 39, 72, 108 ; fossés 39, 100, 108 ; éclairage 73-79 ; écrans 78, 109 ; tunnels 53, 90 ; diffuseurs 122, 129 | TR-02, TR-06, TR-07, PR-14, EQ-06 |
| Cerema, VSA 90/110 (2014) | DocRoute 10, sources | pages PDF (imprimée = PDF − 2) | zone de sécurité 25 ; entrecroisement 25, 32, 39, 49-51, 62-64 ; diffuseurs 30-31, 47, 50-51, 60-66 ; typologie losange / trèfle / trompette 66-67 ; clothoïdes 13-14, 29, 41-44 ; déclivités 15, 18, 49-50 ; PAU 61 | EC-02 à EC-07, EQ-04, EQ-08 |
| Cerema, VSA Voies auxiliaires (2020) | DocRoute 10, sources | pages PDF | entrecroisement 11 ; portiques 30, 36, 52 ; éclairage 40-41 | EC-02, EQ-10, EQ-06 |
| Certu, ICTAVRU (réédition 2009) | DocRoute 10, sources | pages PDF (imprimée = PDF − 2) | échanges 63-100 (losange 77-79, trèfle 79-81, trompette 80) ; tracé 31-34, 85-94 ; tunnels 7-9, 108-160 ; écrans 107, 111-121 ; éclairage 23-27, 106-110 ; clôtures 106-108 ; aires 188 | EC-04, EC-05, EC-06, OA-06, OA-09, EQ-06, EQ-07 |
| Cerema, Dispositifs de retenue en section courante (2022) | DocRoute 10, sources | pages PDF (imprimée = PDF − 2) | refuges et déports 21 ; talus 21-25, 39-41, 48-56 ; fossés et cunettes 10, 25-28, 56 ; écrans 27, 33, 66-68 ; PAU 21, 39, 74 | EQ-02, EQ-03, EQ-04, TR-06, AS-04 |
| Sétra, Guide du projeteur ouvrages d'art, ponts courants (1999) | DocRoute 10, sources | pages PDF | portiques et cadres 16-22 ; buses et dalots 16, 114, 194, 254 ; murs de soutènement 294-296 ; écrans 114-126, 152-175 ; faune 123-127, 157-161 | OA-*, TR-08 |
| Cerema, 2 × 1 voie à chaussées séparées (2021) | DocRoute 10, sources | pages PDF | créneaux 4-33 ; rayons 12, 27-35 ; clôtures 7, 44 | PR-14, PR-16 |
| Cerema, Catalogue des types de routes ; Règles de visibilité (copies madoc) | DocRoute 10, sources | pages PDF | créneaux 21-36 ; échangeurs 51 ; péage 52 / visibilité et déclivités 11-42 | PR-14, PR-15, IM-01 |
| Certu / Cerema PAS VII04, V03, VII06 ; SdB fiche 36 ; Giratoires et tramways (2017) | DocRoute 10, sources | fichiers entiers | îlot d'entrée d'agglomération ; carrefour plateau ; chicane ; doubles giratoires ; giratoire percé par un tram (non exploités) | PR-22, CP-07, PR-21, CP-12, TC-03 |
| IISR 5e partie (VC 2025-09-04) | DocRoute 01 | pages PDF | direction art. 79 à 84 : 42-58 ; Hb 48-49 ; EB10 36, 78-80 ; portiques et potences 44, 48, 57-60 ; péage 15-17, 39, 46-52 ; aires 22, 33, 64 ; PAU art. 78-1 : 23 | SV-03, SV-05, SV-06, EQ-10, EC-08 |
| IISR 8e partie (temporaire) ; 9e partie (dynamique, PMV) ; 2e partie (PN) | DocRoute 01 | pages PDF | temporaire 3-46 ; PMV 3-43, portiques 8, 18, 24, 31-33 ; PN 4, 10-15 | SV-09, EQ-09, SV-10 |

### 4.3 Documents à obtenir

Ils sont publics, sauf les normes AFNOR. Une fois téléchargés, ils vont dans un `sources/` de DocRoute avec `SOURCES.md` ; c'est le rôle des lots voisins qui créent les volets 18 à 20.

| Document | Accès | État | Items |
|---|---|---|---|
| Sétra, Assainissement routier, guide technique (octobre 2006) | https://piles.cerema.fr/IMG/pdf/setra_guide_technique_assainissement_routier_2006_cle04a7e3.pdf | PDF public repéré | TR-07, AS-02, AS-04, OA-07 |
| CETU, Dossier pilote des tunnels, document Géométrie (1990) | https://www.cetu.developpement-durable.gouv.fr/IMG/pdf/DP_geometrie_cle797c61-2.pdf | PDF public repéré | OA-06 |
| CETU, Dossier pilote des tunnels, Éclairage | https://www.cetu.developpement-durable.gouv.fr/IMG/pdf/DP_Eclairage_cle7c81c7.pdf | PDF public repéré | OA-06, EQ-06 |
| ICTAAL (2000, version consolidée 2015) et instruction du 13/07/2015 (BO MEDDE 2015/14) | https://cerema.fr/fr/product/4569 ; https://www.bulletin-officiel.developpement-durable.gouv.fr/documents/Bulletinofficiel-0028736/met_20150014_0000_0018.pdf | fiche Cerema ; texte intégral à obtenir (CHAINE L-01 : absente de DocRoute) | PR-16, PR-18, EC-* |
| Sétra, Les échangeurs sur routes de type autoroute, complément à l'ICTAAL (2013, amendé 2015) | https://cerema.fr/en/product/4568 | fiche Cerema ; texte intégral à obtenir | EC-04 à EC-09 |
| Cerema, guide des passages à faune (mise à jour des guides Sétra 1993 et 2005) | https://doc.cerema.fr/Default/doc/SYRACUSE/595295 | notice ; titre exact et accès à confirmer | OA-08 |
| NF P 98-532 (alphabets, graphismes, compositions des panneaux directionnels) | AFNOR (norme payante) | accès à obtenir ; seule source des règles de composition | SV-05, SV-06, SV-03 |
| NF EN 13201 (éclairage public) | AFNOR (norme payante) | non lue (CHAINE L-04) | EQ-06 |
| Arrêté du 18 mars 1991 relatif aux passages à niveau | Légifrance | à télécharger | SV-10 |
| Guide des terrassements routiers (GTR, Sétra-LCPC) | à rechercher (Cerema) | pentes types de talus | TR-06 |
| Wiki OpenStreetMap, France/Autoroutes (description des sorties, échangeurs, aires) | https://wiki.openstreetmap.org/wiki/France/Autoroutes | description, pas une règle | IM-01, EC-* |

### 4.4 Règles candidates relevées pendant l'inventaire

Forme machine (`regles_candidates` du JSON). Ces règles ne sont pas versées : elles sont à relire puis à proposer au propriétaire de la base.

| Id | Sujet | Condition | Valeur | Source | Confiance |
|---|---|---|---|---|---|
| CAND-E4-001 | traitement d'un talus de remblai selon sa pente p et sa hauteur h | talus de remblai en section courante ; h = hauteur totale si la crête est dans la zone de sécurité | colonnes h < 1 / 1-2,5 / 2,5-4 / ≥ 4 m ; p ≤ 25 % : non isolé ; 25-33 % : non isolé, DR à étudier, DR conseillé, à isoler ; 33-67 % : non isolé, DR à étudier, à isoler, à isoler ; > 67 % : DR à étudier, puis à isoler (m ; %) | Cerema, Dispositifs de retenue en section courante, guide d'installation (janvier 2022), tableau 6, p. 22 imprimée (PDF 24) | moyenne (tableau lu par extraction du texte (ordre des cellules déduit) : à relire sur une tuile native de la page avant versement ; DR = dispositif de retenue) |
| CAND-E4-002 | talus qui appellent l'étude d'un dispositif de retenue | déblai de pente > 33 % (3 pour 1) ; remblai de hauteur > 2,50 m et de pente > 25 % | deblai_pente_pct_min = 33; remblai_hauteur_m_min = 2.5; remblai_pente_pct_min = 25; decision = étude au cas par cas, DR souvent nécessaire (% ; m) | Cerema, Dispositifs de retenue en section courante (janvier 2022), § 1.2.6, p. 22 imprimée (PDF 24) | haute (la réglementation ne l'impose pas ; recommandation) |
| CAND-E4-003 | largeur de la zone de sécurité d'une voie structurante d'agglomération | VSA 110 / VSA 90, à compter du bord de chaussée ; en déblai, limitée à 3,00 m de hauteur | VSA_110 = 8.5; VSA_90 = 7.0; deblai_hauteur_max = 3.0 (m) | Cerema, VSA 90/110 (2014), § 5.3.1, p. 23 imprimée (PDF 25) | haute (tout dispositif agressif y est exclu ou isolé) |
| CAND-E4-004 | pente de déport d'un dispositif de retenue (cas particuliers) | routes bidirectionnelles ou à chaussées séparées, V autorisée ≤ 110 km/h, contraintes d'emprise ou d'exploitation | eloignement_du_bord = 1/4; rapprochement_du_bord = 1/10 (rapport) | Cerema, Dispositifs de retenue en section courante (janvier 2022), § 1.2.4.2.3, p. 19 imprimée (PDF 21) | moyenne (disposition appréciée par le maître d'ouvrage ; sert au contournement d'une pile (besoin B3)) |

## 5. Assets : présents mais jamais posés, et à créer

| Famille | Présents au catalogue, jamais posés | Items |
|---|---|---|
| Éclairage | 8 candélabres (routiers 8 à 12 m, urbains 4 à 8 m) | EQ-06 |
| Retenue | extrémités abaissées GBA / DBA / GS2 / GS4, 4 atténuateurs | EQ-03 |
| Supports | portique L16, potence de signalisation L6, mâts directionnels Ø 89 / 114 | EQ-10, SV-05 |
| Balises | J1, J3, J6, J11 (3 hauteurs), J12, J13, J15a, bornes et quilles | EQ-11, MA-02 |
| Assainissement | avaloir T2, grille 750 × 300, 2 regards Ø 600, bouche à clé | AS-02 |
| Mobilier | 2 abris bus, 3 arceaux, 3 bancs, 2 corbeilles, borne fontaine | MU-02, TC-01, MA-04 |
| Potelets et barrières | 9 potelets et bornes, 6 barrières | MU-01, MA-02 |
| Panneaux et ensembles | 600 faces 3D, 24 ensembles montés (AB, B, C, J5…) | SV-* |
| Feux | 17 assets (R11, R12, R13, répétiteurs, écran, armoire), 3 ensembles, 4 potences | FE-* |
| Gabarits de marquage | PMR, IRVE, CARRE_DAMIER_TC, DOUBLE_CHEVRON_CEREMA, MRE, CEDEZ_V60, CARREAU_DETRESSE, BANDE_SURLARGEUR_1M, ANNEAU_LIMITATION_50, RECTANGLE_POINT_REPERE | MQ-* |

À créer (colonne « à créer » de la grille, 61 items) : les plus demandés sont le terrain et les talus (rg::terrain) ; le compositeur de panneaux (texte, cartouches, polices) ; les décalques de chaussée ; les tampons et plaques ; les ouvrages (workflow parallèle) ; les éléments d'autoroute (PAU, clôture, péage) ; le tramway ; les écrans acoustiques. Les lacunes de forme du catalogue actuel sont listées dans `recon/pcg/assets_route/ASSETS_ROUTE_ETAPE3.md` § 10 : J14 non fabriquée, extrémités de glissière simplifiées, BN1 / BN2 / BN4 absentes, échelle estimée des panneaux D.

## 6. Socle de la nouvelle orientation : imaginer des routes à partir d'images réelles

Ces leviers ne sont pas des éléments d'une scène. Ils ne sont donc pas classés avec eux, mais ils conditionnent la demande : faire des routes françaises plausibles sans recopier un lieu.

| Id | Levier | État | Ce qui manque | Effort | Dépend de |
|---|---|---|---|---|---|
| IM-01 | Catalogue de typologies françaises (« routes types ») tiré de photos réelles | absent | les scènes de test sont des cas d'école ; aucune fiche de typologie (rue de centre ancien, faubourg, traverse de village, RD de plaine, route de montagne, 2 × 2, rocade, autoroute, échangeur, zone d'activités) | M | — |
| IM-02 | Tirage de variantes plausibles et déterministes (largeurs, matériaux, usure, équipements, probabilités) | absent | chaque scène est écrite à la main ; aucune loi de tirage | M | IM-01 |
| IM-03 | Description d'une scène par Claude depuis une photo (Panoramax, Mapillary) | partiel | boucle faite sur 3 rues et 15 sites de Meylan ; pas de procédure générique ni de contrôle de plausibilité | M | IM-01 |
| IM-04 | Relevé de fréquences d'éléments sur un échantillon national de photos | absent | dossier 13 : 72 sites choisis par thème (biais de sélection) | M | — |
| IM-05 | Assembler un quartier ou un itinéraire imaginé (plusieurs tronçons, carrefours, giratoires) | partiel | résolveur réseau N1 et compositions faits ; limité par RS-01 | M | RS-01, IM-02 |

Proposition d'ordre :

1. **IM-04** : relever des fréquences sur un échantillon national de photos (Panoramax), stratifié par catégorie de route. Cela remplace les fréquences [G] de cette grille par des mesures.
2. **IM-01** : écrire une quinzaine de fiches de typologie, chacune avec ses éléments et leurs fréquences. Exemples : rue de centre ancien, avenue de faubourg, boulevard 2 × 2, rue de zone 30, traverse de village, RD de plaine, route de montagne, 2 × 2 nationale, rocade, autoroute, échangeur, giratoire périurbain, zone d'activités.
3. **IM-02** : écrire un tireur déterministe (graine = hash de l'identifiant, comme le reste de la chaîne) qui produit une description YAML au format existant. Il ne pose que ce que le générateur sait fabriquer ; le reste est signalé « non fabriqué ».

## 7. TOP 20 priorisé

### 7.1 Classement

Classement par score : impact sur le réalisme × fréquence. Les items proches sont regroupés quand ils se réalisent ensemble ; le score affiché est celui du meilleur item du groupe. Sont exclus : les éléments du workflow parallèle, la végétation et le bâti (étape ultérieure), et les leviers du § 6.

| Rang | Items | Fonctionnalité | Score | Effort | Dépend de | Pourquoi | Première action |
|---|---|---|---|---|---|---|---|
| 1 | TR-05 | Terrain naturel et abords : le relief autour de la route, au lieu du socle sur sol neutre | 19,8 (P1) | L | TR-02 | la route « flotte » sur un plan uni dans tous les rendus ; c'est le premier défaut vu sur toute scène hors centre dense | rg::terrain (lot N9) : MNT ou relief procédural raccordé aux limites extérieures du profil ; matériaux d'abord sans végétation |
| 2 | CO-02 | Graphe de voies complet : sections courantes, giratoires, bretelles, bifurcations | 17,6 (P1) | M | — | aujourd'hui seuls les carrefours plans ont un graphe ; un véhicule simulé ne peut ni faire le tour d'un giratoire ni prendre une bretelle | généraliser l'écriture de graphe_voies.json du lot L4 aux sorties l5 et autoroute ; contrôle « chaque voie entrante a un successeur » sur G1-G4 et A3-A4 |
| 3 | TR-02 | Profil en long : déclivités, raccordements, points hauts et bas | 17,4 (P1) | L | — | condition de presque tout le reste : ponts, échangeurs, talus, assainissement, visibilité, route de montagne | lot N2 : profil_long.py (MNT ou loi décrite), puis lecture par rg::nivellement ; règles à verser depuis ARP et ICTAVRU (§ 4.2) |
| 4 | SV-05, SV-07, SV-08 | Signalisation de direction composée : D20 (ex-D21), D40 (D42, D43), D60 (D61, D62), Dv, E, E60 *(à coordonner avec le workflow signalisation)* | 16,6 (P1) | L | SV-01 | les mâts de D21 à l'angle des carrefours et les présignalisations sont la signature visuelle d'un carrefour français ; aucune face n'est utilisable telle quelle | compositeur de panneaux (texte, cartouches, flèches, Hb selon RF-SV-DIM.HB_CARACTERES) ; obtenir l'accès à NF P 98-532 ; vérifier d'abord le périmètre du workflow signalisation |
| 5 | RS-01, MQ-15, RV-04 | Réseau continu : plusieurs carrefours par route, plan-masse et nivellement communs, phase des tirets et usure sans couture | 15,6 (P1) | L | TR-02 | une rue entre deux carrefours est le cas le plus courant en ville ; aujourd'hui un seul carrefour par route, à son extrémité « fin » | lots N4 et N5 de la chaîne (rg::plan_masse, rg::nivellement 2.0) ; scène de contrôle : une rue de 150 m entre un carrefour à feux et un giratoire |
| 6 | CO-04 | Export OpenDRIVE 1.4 (CARLA) et 1.8.1 | 15,0 (P1) | L | CO-02, TR-02 | sans lui, aucune scène imaginée ne sert à la simulation ADAS | rg::exporter_opendrive sur J1 et A1 ; validateur autonome tant que CARLA n'est pas installé |
| 7 | EQ-06 | Éclairage public : candélabres en rue, sur giratoire, en échangeur | 14,8 (P2) | M | — | élément vertical le plus répété d'une rue française (11 sites sur 72 le citent) ; 8 assets existent et ne sont jamais posés | rg::eclairage::1.0 (règles RI ECL-01 à -05, RF-OBS-ECL-01) ; pas et côté décrits, sinon [G] déclaré |
| 8 | RV-02, MQ-16 | Chaussée et peinture vieillies : pontages, rapiéçages, tranchées, faïençage, marquages fantômes | 14,5 (P2) | M | — | observé sur tous les sites du lot A ; une chaussée neuve et uniforme est le second défaut visible des rendus | décalques en points (graphe PG_Decalques) tirés par graine ; densité décrite (A14) |
| 9 | CO-03 | Trajectoires et conflits des giratoires et des bretelles, balayés comme les carrefours plans | 13,6 (P2) | M | CO-02 | priorité rappelée par l'utilisateur : des trajectoires qui passent correctement dans les zones de conflit | brancher les trajectoires du compilateur de giratoire sur la chaîne L3a / L4 (balayages VL et bus) ; ajouter les trajectoires de bretelle |
| 10 | TR-06, TR-07, AS-04 | Talus de déblai et de remblai, fossés, cunettes et descentes d'eau | 12,4 (P2) | L | TR-02, TR-05 | toute route hors agglomération ; aujourd'hui des bandes plates | profils de talus et de fossé paramétriques dans rg::terrain ; règles candidates CAND-E4-001 et -002 (§ 4.4) |
| 11 | SV-03, PR-22 | Entrées d'agglomération et traverses : EB10 / EB20, B14 et leur répétition, porte d'entrée, îlot *(placement : workflow signalisation ; composition du texte : avec SV-05)* | 12,2 (P2) | M | SV-05 | séquence vue sur toute route départementale qui entre dans un bourg | placement : workflow signalisation ; composition des noms de commune avec le compilateur de SV-05 ; gabarit d'îlot d'entrée (CERTU PAS VII04) |
| 12 | CO-05 | Import ZoneGraph dans Unreal | 12,0 (P2) | M | CO-02 | le graphe ne sert dans UE que s'il y est importé | script d'éditeur recon/pcg/ue/zonegraph_depuis_graphe.py (PLAN § 7) |
| 13 | RV-06 | Conditions de rendu : nuit et rétroréflexion, chaussée mouillée, neige, ciel couvert | 12,0 (P2) | L | — | les essais ADAS se jouent de nuit et sous la pluie ; les comparaisons Panoramax sont faussées par le ciel toujours clair | côté Unreal d'abord (matériaux rétroréfléchissants des panneaux et de la peinture) ; contrôle sur une planche de nuit |
| 14 | AS-02, AS-03, RV-03 | Avaloirs, regards, tampons et plaques en chaussée, points bas | 11,1 (P2) | M | TR-02 | chaque rue française en porte plusieurs ; 5 assets existent | pose réglée par le fil d'eau (après TR-02) ; d'ici là, pas [G] déclaré |
| 15 | EQ-04, EQ-02, EQ-03 | Retenue routière : implantation par règle, extrémités, raccords, contournement des piles | 10,8 (P2) | M | TR-06 | la retenue n'existe que si on l'écrit et ses files finissent net | exploiter le guide Cerema 2022 (local) ; règles candidates CAND-E4-001 à -004 ; poser les extrémités abaissées déjà au catalogue |
| 16 | FE-04 | Feux animés selon le plan de feux (Unreal) *(à coordonner avec le workflow feux)* | 10,8 (P2) | M | FE-01 | un carrefour à feux figé n'est pas utilisable en simulation | à faire après la fabrication des feux (workflow parallèle) : matériaux émissifs pilotés par le contrôleur du modèle |
| 17 | CP-05 | Branches courbes ou très obliques près d'un carrefour, carrefour en Y | 10,5 (P2) | L | TR-01 | les routes réelles arrivent rarement droites ; imaginer une scène plausible l'exige | coins et trajectoires sur bords courbes dans rg::carrefours (aujourd'hui droites prolongées) |
| 18 | EC-04, EC-07 | Diffuseur en losange et bretelles en courbe avec dévers et profil en long | 10,2 (P2) | XL | CP-10, OA-01, TR-02, TR-03 | chaque sortie d'autoroute ou de voie rapide ; le premier échangeur à savoir faire | après TR-02 et les ponts du workflow parallèle : gabarit losange ICTAVRU / VSA 90-110, carrefours de raccordement en giratoire (G2) |
| 19 | EQ-11 | Balises J1, J3, J4, J5, J11, J13, J14 *(à coordonner avec le workflow signalisation)* | 9,6 (P3) | S | SV-01 | fréquentes hors agglomération ; J3, J5, J14a déjà placées dans le modèle ; 11 assets existent | vérifier d'abord si le workflow signalisation les pose ; sinon pose directe (effort S) |
| 20 | TR-03, TR-04 | Dévers en courbe, gauchissement, surlargeur | 9,3 (P3) | M | TR-01, TR-02 | toute courbe hors agglomération et toute bretelle ; les règles existent déjà dans la base | loi de dévers fonction de la courbure (RF-GV-DEV-002, -003) dans commun/profil.py et rg::nivellement |

Juste après le TOP 20 viennent : TR-08 Murs de soutènement, murets, enrochements (9,0) ; EQ-10 Portiques, potences et hauts mâts de signalisation (9,0) ; SV-04 Indication (8,4) ; MU-01 Potelets, bornes, barrières de trottoir (8,1) ; PR-02 Stationnement en épi, en bataille, marquage des places (8,1) ; MQ-07 Marquage du stationnement (8,1) ; SV-09 Signalisation temporaire de chantier (8,0) ; CO-06 Branchement du modèle de trafic (8,0).

### 7.2 Ordre de réalisation conseillé (dépendances)

1. **Vague A, sans Houdini lourd, en parallèle :**
   - les leviers IM-04, IM-01 et IM-02 ;
   - le versement des règles du § 4.2 par le propriétaire de la base ;
   - le graphe de voies complet (CO-02, rang 2).
2. **Vague B, la troisième dimension :** profil en long (rang 3), puis dévers (rang 20), terrain (rang 1), talus et fossés (rang 10), et enfin assainissement réglé par le fil d'eau (rang 14).
3. **Vague C, le réseau :** réseau continu (rang 5), branches courbes (rang 17), trajectoires des giratoires et bretelles (rang 9), puis exports OpenDRIVE et ZoneGraph (rangs 6 et 12).
4. **Vague D, les équipements visibles :**
   - éclairage (rang 7) et retenue (rang 15) ;
   - avec le workflow signalisation : direction (rang 4), entrées d'agglomération (rang 11), balises (rang 19) et feux animés (rang 16).
5. **Vague E, l'aspect :** chaussée et peinture vieillies (rang 8), conditions de rendu (rang 13).
6. **Vague F, les échangeurs :** losange et bretelles (rang 18), après les ponts du workflow parallèle et le profil en long. Puis trèfle et trompette (EC-05), nœud autoroutier (EC-06), péage (EC-08).

### 7.3 Gains rapides (effort S, règles et assets déjà présents)

- **EQ-11** Balises J1, J3, J4, J5, J6, J11, J13, J14 : score 9,6, effort S ; J3, J5, J14a placées dans le modèle, aucune fabriquée ; J1 / J4 (virages) jamais posées.
- **MU-01** Potelets, bornes, barrières de trottoir : score 8,1, effort S ; aucune pose.
- **MA-02** Séparateurs ponctuels de piste : potelets, balises, plots, jardinières : score 6,9, effort S ; le séparateur bordé est fait ; les séparateurs ponctuels sont lus mais pas fabriqués.
- **MQ-11** Triangles cédez au sol (« dents de requin ») : score 4,2, effort S ; gabarit CEDEZ_V60 présent, jamais posé.
- **MQ-06** Marquages cyclables : figurines encadrées début / fin, doubles chevrons, flèches ½, sas : score 5,4, effort S ; figurines au pas et sas faits ; doubles chevrons, figurine encadrée, flèches ½ absents.
- **CP-09** Traversées cyclables de carrefour (IISR : doubles chevrons, figurines ; styles locaux) : score 6,9, effort S ; besoin A2 ; gabarit DOUBLE_CHEVRON_CEREMA présent mais jamais posé.
- **MQ-09** Transports collectifs : damier TC, BUS / TRAM répétés, interruption au carrefour : score 4,1, effort S ; zigzag fait ; inscription BUS possible à la main ; damier jamais posé.
- **MQ-10** Inscriptions de zone : ZONE 30, anneaux 30 / 50, figurine piéton : score 4,1, effort S ; voir PR-06.
- **PR-06** Zone 30 : porte d'entrée (B30, marquage « ZONE 30 », anneau 30), plateaux, coussins : score 6,1, effort S ; ralentisseurs faits ; entrée de zone absente (ni panneau, ni inscription, ni anneau E.1, ni effet de porte).
- **PR-13** Route étroite < 5,20 m (sans axe, marques MRE) : score 5,0, effort S ; axe supprimé sous 5,20 m ; marques MRE (gabarit présent) jamais posées.
- **MQ-13** Marquages autoroutiers complémentaires : surlargeur, PAU, points de repère : score 3,3, effort S ; gabarit BANDE_SURLARGEUR_1M présent, jamais posé.
- **EC-10** Voie de détresse (lit d'arrêt, damier rouge et blanc) : score 2,7, effort S ; gabarit CARREAU_DETRESSE présent, jamais posé.
- **MQ-12** Marquage temporaire jaune (chantier) : score 6,0, effort S ; —.

## 8. Hors classement : en cours ailleurs, étape ultérieure

| Id | Fonctionnalité | État | Score | Prio. | Raison |
|---|---|---|---|---|---|
| SV-01 | Signalisation de police (AB, B, C) : choix, placement, supports, ensembles | en cours ailleurs | 24,2 | P1 | en cours dans le workflow parallèle (ponts / ouvrages, signalisation verticale + feux) |
| VB-03 | Abords : prairie, champs, forêt, végétation de talus | partiel | 17,8 | P1 | étape ultérieure (végétation et bâti, décision du 17/10/2026) |
| VB-04 | Bâti : façades, murs de clôture, portails, accès | absent | 17,8 | P1 | étape ultérieure (végétation et bâti, décision du 17/10/2026) |
| VB-01 | Arbres d'alignement (essences, fosses, exclusions) | partiel | 17,5 | P1 | étape ultérieure (végétation et bâti, décision du 17/10/2026) |
| OA-01 | Pont courant (PI, PS, PO) : tablier, piles, culées, corniches, garde-corps, joints | en cours ailleurs | 15,8 | P1 | en cours dans le workflow parallèle (ponts / ouvrages, signalisation verticale + feux) |
| VB-02 | Îlots et terre-pleins plantés (strates, massifs, haies), visibilité 0,60 m | partiel | 14,0 | P2 | étape ultérieure (végétation et bâti, décision du 17/10/2026) |
| FE-01 | Feux R11 + répétiteurs, R12, boutons d'appel : fabrication et pose | en cours ailleurs | 13,5 | P2 | en cours dans le workflow parallèle (ponts / ouvrages, signalisation verticale + feux) |
| FE-02 | Potences, juxtaposition, R14 directionnels, R13 bus, R19 vélos, écran de contraste | en cours ailleurs | 8,2 | P3 | en cours dans le workflow parallèle (ponts / ouvrages, signalisation verticale + feux) |
| EQ-05 | Barrières de pont BN1, BN2, BN4 et garde-corps d'ouvrage | en cours ailleurs | 6,4 | P3 | en cours dans le workflow parallèle (ponts / ouvrages, signalisation verticale + feux) |
| OA-02 | Passerelle piétons et cycles | en cours ailleurs | 6,0 | P3 | en cours dans le workflow parallèle (ponts / ouvrages, signalisation verticale + feux) |

La signalisation de police (SV-01, score 24,2), les arbres et les abords (VB-01, VB-03), le bâti (VB-04) et les ponts (OA-01) auraient tous leur place dans les six premiers rangs. Quand le workflow parallèle aura livré, il faudra vérifier dans les rendus que les panneaux, les feux et les ponts y figurent, puis mettre à jour l'état de ces lignes. La végétation reste la plus grosse lacune visuelle après le terrain : son report a été décidé le 17/10/2026, et c'est à l'utilisateur de le lever.

## 9. Limites de cet inventaire

- **Fréquences et impacts** : ce sont des estimations [G]. Elles s'appuient, quand c'est noté, sur des comptes de mentions du dossier 13, dont l'échantillon est biaisé (sites choisis par thème). Le levier IM-04 doit les remplacer par des mesures.
- **Poids des contextes** : les poids U / P / R / A sont un choix [G]. Le JSON garde la fréquence par contexte : on peut recalculer les scores pour une campagne surtout autoroutière ou surtout urbaine.
- **Documents** : les pages des documents locaux sont des index PDF repérés par mots, relus par sondage seulement. La règle candidate CAND-E4-001 vient d'un tableau lu par extraction du texte : il faut la relire sur une tuile native avant de la verser.
- **Recherche en ligne** : elle s'est limitée à repérer les documents de règles manquants (§ 4.3). Aucun document n'a été téléchargé, et aucune description de route par des tiers n'a été recopiée.
- **Workflow parallèle** : son périmètre exact n'est pas connu de ce lot (balises J, danger A, portiques, passerelles, ponts sur rivière ?). Ces lignes portent « à coordonner ».
- **Rendus et photos** : seules les planches existantes ont été regardées ; aucun rendu n'a été relancé. Aucune photo Panoramax ou Mapillary n'a été ouverte pour ce lot.

## 10. Fichiers

- `recon/generateur/ETAPE4_LACUNES.md` : ce document.
- `recon/generateur/etape4_lacunes.json` : grille (153 items avec preuve, règles, assets, fréquences par contexte, impact, score, priorité), TOP 20, gains rapides, règles candidates, pointeurs locaux, documents à obtenir, assets dormants.
- Aucun autre fichier n'a été modifié.
