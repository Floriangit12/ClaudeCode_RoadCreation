# Relecture adverse de la préparation : chaîne de construction, relevés de Meylan (lots A et B), assets de l'étape 3

*`recon/generateur/meylan/RELECTURE_PREPARATION.md`, 18/10/2026. Relecture indépendante des quatre livrables qui
préparent la reconstruction de Meylan par le PCG : `recon/generateur/CHAINE_CONSTRUCTION.md`, `chaine_construction.json`
et `FORMAT_DESCRIPTION_RESEAU.md` (lot « chaîne ») ; les 8 sites du lot A et les 7 sites du lot B sous
`recon/generateur/meylan/` ; la bibliothèque `route_fr` de l'étape 3 (`assets/specs/route/catalogue_assets_route.json`,
`recon/pcg/assets_route/ASSETS_ROUTE_ETAPE3.md`). Rien n'a été écrit dans les fichiers de l'étape 2, dans `D:\DocRoute`,
ni sur C: (deux scripts de travail posés d'abord dans le scratchpad de C: ont été déplacés sur D: puis effacés). Pas de
git. Une seule correction de nommage a été faite (§ 9). Les outils de cette relecture et leurs sorties sont dans
`recon/out/generateur/meylan/relecture_preparation/` (non versionné).*

## 0. Verdict en bref

| Livrable | Verdict | Problèmes bloquants avant les lots N1 et N4 |
|---|---|---|
| Chaîne de construction | L'ordre est solide et chaque contrainte citée existe. Les citations ont été recomptées indépendamment : 0 introuvable, hors familles écrites avec « * ». Sur 45 règles relues en contenu, 5 sont imprécises. | 2 dépendances à rebours dans la chaîne (E02 lit E04 et E07 ; E07 modifie le terrain après E06). Les listes « manquent » sont périmées : les assets de l'étape 3 les comblent en partie. |
| Ordre du chantier entre les lots | **Non cohérent.** La préparation contient quatre ordres différents : la chaîne (E07 à E17), le lot A, le lot B et les phases P01 à P11 des assets. Le marquage est en E12 dans la chaîne, mais en P10 dans les assets, après les panneaux et l'éclairage. | Oui (§ 3) |
| Format réseau | Bonne architecture : une couche au-dessus du format de l'étape 2. | La règle de choix de la § 4.3 jette en silence une mesure hors de la plage dite. L'exemple du § 10.2 décrit M17 comme un carrefour à feux, ce qu'il n'est pas. L'exemple du § 10.3 serait refusé par son propre § 11. Trois clés utilisées ne sont pas déclarées. |
| Relevés de Meylan | Fidèles aux photos : 35 tuiles et 15 orthos ou coupes revues, aucun constat photo contredit. | Cinq paires de sites se recouvrent sur 30 à 53 m, avec des profils contradictoires, et un vide de 103 m sépare la N87 du nœud A41/N87. Les dates d'état vont de 2023 à 2026 (M01 mêle trois états). Quatre écarts admis ne reposent sur aucune mesure. Les YAML du lot B sont refusés tels quels (`extensions_auto`). « GBA » y désigne un séparateur double face, c'est-à-dire un DBA. |
| Photos | Aucune image dans les fichiers versionnés des quatre lots. | **Hors des quatre lots :** 23 vues Panoramax sont dans `recon/generateur/tmp/**/rendus/`, un chemin qui n'est ni `photos_non_versionnees` ni ignoré par git (§ 6). |
| Assets | Cotes sourcées : 0 entrée sans source sur 795, et 202 marquées « estimation ». Matériaux sous CC0 (76 fiches sur 77, plus 1 « maison »). Planches toutes à la taille native. | La licence des faces des 600 panneaux est « présumée, réserve non levée ». Les 120 assets de l'étape 1 n'ont pas de phase. Le mot « GBA » mène au modèle simple face. Plusieurs objets vus à Meylan n'ont pas d'asset. |

## 1. Méthode

- **Citations.** `outils/verif_ids.py` extrait tous les identifiants des trois fichiers de la chaîne et de tous les
  `DESCRIPTION.md`, `description.yaml`, `mesures.json` et `*.md` de `meylan/` : 925 mentions RF-, 158 DEF-, 73 ARB-,
  137 TQ-/GA-, 68 RI et 2 LOC-. Il vérifie que chacune existe dans `regles_route_fr.json` (857 règles, 34 DEF, 20 ARB)
  ou dans `regles_conception.json`, `regles_implantation.json` et `regles_locales_meylan.json`. `outils/voir.py` a
  servi à relire le contenu de 45 règles, comparé à ce que la chaîne leur fait dire.
- **Sources PDF.** Deux valeurs « à verser » ont été relues dans `D:\DocRoute\10_…\sources\` par la couche texte :
  ICTAVRU 2009, p. 29-30 imprimées, et VSA 90/110 (2014), Rm et Rdn.
- **Compilation.** `outils/compiler_tous.py` recompile les 15 `description.yaml` avec le compilateur du dépôt,
  importé sans modification et sans écrire de bytecode, deux fois : tels quels, puis sans `extensions_auto`. Résultat :
  `relecture_preparation/compilation_relecture.json`.
- **Raccords.** `outils/recouvrements.py` ramène chaque tronçon en Lambert-93 (origine du site plus coordonnées
  locales, axes non tournés). Il mesure ensuite, pour chaque paire de sites, la longueur d'axe à moins de 6 m
  (recouvrement) et la distance entre extrémités (raccord).
- **Images.** Toutes ont été regardées à la taille native, en tuiles de 1 092 px au plus produites par `decoupe.py`,
  déjà présentes et contrôlées à 1 092 × 1 092. Les orthos IGN font 800 × 800 à 0,20 m et les coupes 450 × 600 au plus.
  Les agrandissements ×3 ou ×4 sont au plus proche voisin, à partir de recadrages natifs.
  - 35 tuiles de photos, au moins 2 photos par site ;
  - 1 ortho ou coupe d'ortho par site ;
  - 4 planches d'assets sur 49.

  La liste est au § 5.1. Les photos et leur agrandissement restent dans `recon/out/generateur/meylan/<site>/photos_non_versionnees/`.

## 2. Chaîne de construction (CHAINE_CONSTRUCTION.md, chaine_construction.json)

### 2.1 Cohérence de l'ordre

L'ordre retenu tient : on conçoit d'abord (E01 à E06), puis on construit (E07 à E17). Les bordures et les avaloirs
viennent avant l'enrobé, les marquages avant les panneaux. Les six écarts du § 2.2 sont justifiés par des dépendances
de données. Le JSON et le Markdown portent les mêmes identifiants, étape par étape, pour les 20 étapes ; la seule
différence est E19, où le Markdown écrit l'intervalle « CC-01 à CC-13 ». Les problèmes :

| # | Problème | Preuve | Correctif |
|---|---|---|---|
| C1 | E02 lit des sorties postérieures : ses entrées comptent « gabarits verticaux des ouvrages (E04, E07) ». Cela contredit le § 2.1 (« chaque étape ne lit que des sorties d'étapes antérieures ») et crée une boucle E02 → E07 → E02. | MD l. 276 ; JSON `etapes[2].entrees` (détecté par script : seule étape fautive) | Le gabarit est une donnée de description (`ouvrages[].gabarit`, E00) ou une règle (RF-GV-PON-012), lue par E01 et E02. E07 ne fait que fabriquer. |
| C2 | P2 dit qu'« à partir d'E07, plus aucune cote n'est modifiée ». Or E07 abaisse le terrain sous les ouvrages et crée les talus. E06 annonce pourtant déjà « le MNT conditionné, raccordé aux bords de plate-forme ». | § 1 P2 ; fiche E07 (But) ; fiche E06 (continuité) | Calculer le terrain, les talus et l'abaissement sous les ouvrages en E06 (sortie `niveau/terrain`). E07 en fait les maillages. |
| C3 | Le contrôle P06-4 (« avaloir à moins de 1 m ») ne peut pas se faire à la porte P06 : les avaloirs ne sont posés qu'en E09. | fiches E06 et E09 | À P06, contrôler « chaque point bas a un exutoire prévu (position d'avaloir) ». La pose reste contrôlée par P09-1. |
| C4 | E10 et E11 écrivent le même fichier `fabrique/sol_<tuile>.usda` (« même triangulation ») : deux étapes possèdent une même sortie. | contrats E10 et E11 | E10 triangule toutes les faces du plan-masse. E11 n'ajoute que les matériaux, les joints, les BEV et les remplissages, dans un fichier ou une couche à part. |
| C5 | Les listes « manquent » des bibliothèques et la lacune L-07 sont périmées. Elles ont été écrites avant la livraison des assets de l'étape 3, le même jour. | Le catalogue compte aujourd'hui : bordures 104 (la chaîne dit 64), caniveaux 24 (12), supports 39 (15), feux 17 (8), PBR 48 (27) ; retenue 21 (GS2, GS4, DE2, GBA, DBA, MVL, LBA, atténuateurs) ; éclairage 8 ; assainissement 5 ; balises J11 et J13 ; mât D114 ; potences ; portique ; écran de contraste | Mettre à jour E07, E08, E09, E10, E13 à E16, § 8 et L-07 dans le JSON (source machine), puis régénérer le Markdown. Restent vraiment manquants : BN1, BN2, BN4, GR4, corniches, J14a et J14b, panneaux à texte variable D21 et D41, CE2a, clôture autoroutière. |
| C6 | Fiche E04 : « giratoires et autoroutes encore vides ». Ce n'est plus vrai : `scenes_giratoires/` contient G1 à G3, `scenes_autoroutes/` A1 à A4 et `scenes_carrefours/` J4 et J5. | `ls recon/generateur/scenes_*` | Écrire « à la date de lecture » ou retirer la phrase. |
| C7 | Les numéros de ligne cités dans des fichiers de l'étape 2 ont déjà bougé. `limite_carte` est à la l. 2431 de `description_vers_modele.py` (citée l. 2221-2222 ; le fichier fait 2 636 lignes, contre 2 418 à la lecture). `st_route` est à la l. 973 de `rendu_l2b.py` (citée l. 963). | grep du 17/10 | Citer des noms de fonction (`st_route`, `socle_jupe`, `carrefour_plan`) plutôt que des lignes. |
| C8 | Le JSON est déclaré « source machine », mais le script qui l'a produit avec le Markdown (`gen_chaine.py`) est resté dans le scratchpad de C:, hors du dépôt, ce qui est contraire à la règle « rien sur C: », que le lot signale lui-même. Rien dans le dépôt ne régénère le Markdown depuis le JSON : chaque correction devra être faite deux fois à la main, au risque d'un écart. | `grep chaine_construction` dans `recon/` : aucun script ; scratchpad : `gen_chaine.py`, `chaine_modele.md` | Verser un générateur dans `recon/generateur/outils/` (JSON → Markdown) et le faire tourner après chaque correction ; ajouter un contrôle d'égalité entre les deux fichiers. |

### 2.2 Les contraintes citées existent-elles ?

**Existence.** 0 identifiant introuvable dans la base ou dans les specs du dépôt. Les seuls « inconnus » sont des
familles écrites avec « * » : RF-MQ-INS-*, RF-MQ-DEC-*, RF-GV-PON-*, RF-MA-BUS-*, RF-OBS-CYC-*, RF-OSM-LAR-*. Les chiffres
de la base sont exacts (857 règles, 34 DEF, 20 ARB). Les 31 chemins de fichiers cités comme existants ont été testés et
existent tous. Tous les ways OSM cités sont dans `data/vector_gz/osm/roads.geojson.gz`, y compris 28712715, 41914735 et
165939596, qui complètent la chaîne de la bretelle.

**Contenu (45 règles relues).** 40 sont citées à bon escient. Exemples : L/2 = 19,5 m et L/6 = 6,5 m à 50 km/h ; DEF-005
« îlot 0,11 » ; DEF-017 « pointe à 1,50 m, interdistance 20 m » ; RF-GV-PON-012 « 4,30 / 4,75 + 0,10 » ; TQ-BOR-007 ; GA-CHA-003
et GA-CHA-004 ; RF-GV-GIR-005 et RF-GV-GIR-008 ; RI ECL-01, ECL-04, ECL-05 ; RI POT-02 ; DEF-033. Les cinq à reprendre :

| # | Citation | Ce que dit la base | Correctif |
|---|---|---|---|
| R1 | P12-5 « peinture +2 à 3 mm : TQ-MQG-005 » | TQ-MQG-005 dit : draper seulement sur le sol v2. L'épaisseur (2 mm pour la peinture, 3 mm pour l'enduit) est dans **TQ-MQG-002**. | Citer TQ-MQG-002. |
| R2 | P13-1 et § 2.2 : « terre-plein de **voie rapide** de moins de 12 m → barrière N (RF-GV-TPC-008) » | Condition de la règle : « Autoroutes, ICTAAL » (BN01 p. 56). La N87 est une VRU (ICTAVRU). | Restreindre aux autoroutes, ou citer ICTAVRU et marquer l'extension [G]. |
| R3 | P04-3 « traversée hors refuge ≤ 12 m, bloquant » ; FORMAT § 7.1 « refuge imposé si traversée > 12 m » | RF-GV-PIE-010 ne vaut que pour un carrefour à feux. | Ajouter la condition « à feux ». |
| R4 | § 2.3 et FORMAT § 1 : RF-OSM-LAR-050 « confiance faible » | `confiance: moyenne` | Corriger. Citer aussi RF-MQ-PS-03 (V15 → L = 39 m), d'où vient L/2 = 19,5 m. |
| R5 | E15 « LOC-ECL » ; VSA 90/110 « p. 12-14 (pages imprimées) » | L'identifiant exact est LOC-ECL-001. Rm et Rdn (240 et 400 m ; 370 et 650 m) sont en p. 11 imprimée (p. 13 du PDF) : valeurs vérifiées. Les valeurs ICTAVRU des p. 29-30 sont vérifiées et exactes. | Corriger l'identifiant et la plage de pages. |

## 3. Il faut un seul ordre de construction

La préparation donne quatre ordres de chantier. Le PCG ne peut en suivre qu'un.

| Ouvrage | Chaîne (référence) | Lot A (`DESCRIPTION.md` § 2) | Lot B (`extensions_auto.etapes`) | Assets (`phase_chantier`) |
|---|---|---|---|---|
| Terrassements, ouvrages | E07 | 1 plate-forme (sans ouvrages) | 1 plate-forme, 2 ouvrages | P01 réseaux |
| Bordures, caniveaux | E08, **avant** l'enrobé | 3, **après** les chaussées | 4 (TPC) ; dans `axe_verdun_centre`, refuges avant enrobé | P02 |
| Avaloirs, tampons | E09, avant l'enrobé | — | — | avaloir en P02 ; tampons et grilles en P05, **après** les trottoirs |
| Chaussée | E10 | 2 | 3 | P03 |
| Trottoirs, terre-pleins | E11 | 4 | 4 | P04 |
| Marquages | **E12**, avant la retenue et les panneaux | 5 | 6, **après** la retenue | **P10**, après les panneaux, les feux et l'éclairage |
| Retenue | E13 | — | 5 | P06 |
| Panneaux et feux | E14 | 6 | 7 | P08 et P09 |
| Éclairage | E15, après les panneaux | 7 (avec mobilier et végétation) | 8 | **P07, avant les panneaux** |
| Mobilier | E16 | 7 | 8 | P11 |
| Végétation | E17 | 7 | 9 | — |

**Correctif proposé.** La chaîne est la référence : chacun de ses écarts est justifié par une dépendance de données
(AB4 au droit de la ligne STOP, R11 au droit de la ligne d'effet, C24 dès qu'il y a des flèches, coffrage des
bordures).

- Assets : ajouter `etape_chaine` (E08 à E16) à chaque entrée. Correspondance : P02 → E08 ; avaloir P02 et P05 → E09 ;
  P03 → E10 ; P04 → E11 ; P10 → E12 ; P06 → E13 ; P08 et P09 → E14 ; P07 → E15 ; P11 → E16.
- Ce champ manque aussi aux 120 assets de l'étape 1 (`phase_chantier` = null, § 7).
- Les ordres propres aux sites (lot A § 2, lot B `etapes`) deviennent des notes : le FORMAT § 7.5 le prévoit déjà
  (« l'ordre est celui de la chaîne »).

## 4. Format réseau (FORMAT_DESCRIPTION_RESEAU.md)

| # | Problème | Preuve | Correctif |
|---|---|---|---|
| F1 | **Une mesure hors de la plage « ≈ » est jetée sans rien dire** (§ 4.3, point 1 : « une mesure comprise dans la plage est retenue »). Exemple tiré du § 10.2 : « zone hachurée ≈ 2,8 » donne [2,3 ; 3,3]. La mesure de l'ortho (3,4 m, lot B) et celle du levé GAM (3,66 m, lot A) sont hors de cette plage. Le résolveur garderait donc 2,8, le centre de la plage, alors que la valeur venait d'une estimation photo de l'étape 1 que la mesure corrige. | FORMAT § 4.2, § 4.3, § 10.2 ; `axe_verdun_centre/description.yaml` ; `verdun_centre_feux/mesures.json` | Une mesure hors de la plage est une erreur (« description contredite par la mesure ») ou est retenue avec un avertissement. Jamais de retour au centre. |
| F2 | **Exemple § 10.2 : M17 n'est pas un carrefour à feux.** Le relevé du lot A montre un passage piéton à feux avec refuge entre deux débouchés en baïonnette, en cédez-le-passage. Preuves : OSM `traffic_signals` seulement au passage (nœuds 1333024067 et 1333024069, et 7472840576 et 8355380884, un par sens) ; AB3a et B1 sur le chemin des Buclos (photos de22683a t003, f252d62f t004, regardées). L'exemple met `regime: feux`, trois branches avec passage et un « îlot central ovale ». | `verdun_centre_feux/DESCRIPTION.md` ; `sites.json` du dossier 13, qui nomme M17 « Carrefour à feux » | Réécrire C_BUCLOS : carrefours BS (sortie seule) et BN (cédez), passage à feux sur le tronçon intermédiaire d'environ 29 m. Reprendre les largeurs mesurées (3,6 / 3,4 / 3,6 du lot B), pas celles de M27 (3,25 / 2,8). Signaler au propriétaire de DocRoute l'intitulé de M17 dans le dossier 13. Fait dans la chaîne (§ 9). |
| F3 | **Exemple § 10.3 refusé pour une autre raison que la ligne volontairement fausse.** Le way 361790056 (B_HELICE) passe sous l'ouvrage O_3 (way 165939595), vers (918 525 ; 6 460 094). O_3 n'a pas de `franchit: [B_HELICE]`, et le § 11 refuse « deux tronçons qui se croisent sans nœud ni ouvrage » (P02-5). Par ailleurs, M_CONV_A41 est posé sur le nœud OSM, à 7 m de l'axe du pont O_2 (918 473 ; 6 459 983), alors que le lot B mesure l'insertion de s 420 à s 559 : le musoir est à environ 35 m à l'est du pont. La boucle est à 50 km/h, 1 voie de 4,0 m (lot B) ; l'exemple dit 90. | calcul sur l'extrait OSM ; `auto_noeud_a41_n87/DESCRIPTION.md` § 1 et § 3 | Ajouter `franchit: [B_HELICE]` à O_3. Reprendre les cotes et la vitesse du lot B (`mesures.json` prime, comme le dit le § 10). |
| F4 | **Clés utilisées mais non déclarées.** La table du § 7.5 transpose `extensions_auto` vers `retenue:`, `equipements:` et `talus:`. Ces clés manquent au § 2 et au § 6.1 ; or le § 0 dit qu'« une clé inconnue est une erreur ». Le § 7.5 dit aussi que `BESOINS_FORMAT_AUTO.md` n'est « pas encore écrit, B1 à B12 » : il existe et va jusqu'à B17. `BESOINS_FORMAT.md` (A1 à A20) n'est pas cité. | FORMAT § 0, § 2, § 6.1, § 7.5 | Déclarer les trois clés, ou les retirer. Mettre la table à jour avec B1 à B17 et A1 à A20 (couverture au tableau F7). |
| F5 | **La phrase de l'utilisateur est lue de deux façons.** Chaîne et format : 2 × 1 voies, terre-plein de 20 m de **long** et 2 m de large, posé « au milieu » (mot que l'utilisateur n'a pas dit). Assets (`etape3.correspondances_description`, ASSETS § 2.1) : « 2 × 2 voies avec terre-plein central végétalisé de 20 m » et candélabres routiers de 10 m dans le terre-plein. Une troisième lecture est possible : un terre-plein continu, végétalisé sur 20 m. | CHAINE § 2.3 ; FORMAT § 1 ; ASSETS_ROUTE_ETAPE3 § 2.1 | E00 consigne l'interprétation choisie et l'autre lecture (« question ouverte » dans `compilation_reseau.json`). Une seule lecture dans tous les lots. |
| F6 | `ouvrages.type` n'a pas `passage_inferieur`, que le lot A demande (A12, rp_lycee, OSM `layer=-1` × 4). | § 7.5 | Ajouter la valeur. |

**F7. Les besoins des lots A et B sont-ils couverts par la couche réseau ?**

| Couvert par la couche réseau | Couvert en partie | Non couvert (à proposer à l'étape 2 ou à la couche réseau) |
|---|---|---|
| B1 (`osm: {aller, retour}`, `jumele_avec`) ; B5 (`ouvrages`) ; B12 et A19 (ordre de la chaîne) ; B14 (`trace: osm`) ; B17 (`categorie: bretelle`) | B2 (bretelles et nœuds `fourche` ; divergence d'une bretelle en deux bretelles : « à proposer ») ; B15 (`z: mnt`, gabarit ; pas de niveaux dits) ; B16 et A7 (`preuves`, `prov.plage/choix`, mais par tronçon, pas par valeur) ; A2 (traversée cyclable : refusée tant que l'étape 2 ne la porte pas) ; A6 (`choix` de provenance, sans clé « hypothèse ») ; A18 (fusion des nœuds, P01-2) ; B8 (évènements `profil`) | A1, A3, A4, A5 (clés `entree` et `sortie` de l'étape 2 à documenter), A8 (option datée « chantier » : `etat` n'admet qu'une date), A9, A10, A11 et B4 (arrêts de bus, pistes latérales, aire de service, route de liaison), A12 (voir F6), A13 et B6, A14, A15 et B7, A16, A17, A20 et B13, B3 (voir F4), B9 (signalisation autoroutière), B10 (vitesse par sens), B11 (début et fin d'autoroute) |

## 5. Relevés de Meylan

### 5.1 Fidélité aux photos (tuiles natives regardées par cette relecture)

| Site | Photos et tuiles | Ortho ou coupe | Constat de la relecture |
|---|---|---|---|
| verdun_centre_feux (M17) | de22683a t003, t004 ; f252d62f t004 | ortho 800 px et deux zooms ×3 | Conforme : refuge et balise de nez, feu sur mât avec caméra, bande verte, B1, AB3a, C24, piste derrière l'herbe au sud-est. Voir M6. |
| paquet_jardin (M01) | 22c050a5 t006 ; 119d9094 l+102.9 ; 20d1a815 t006 | ortho et zoom ×3 de Verdun nord-est | Conforme : pavés jaunes de la Chronovélo, K16, îlot de la Revirée avec ses D21, deux voies vers le sud-ouest avec flèches. État mélangé, voir M2. |
| rp_lycee (M02) | 3d7dd376 l-51.4 ; 770c2fc8 l+102.9 | ortho : Ø ≈ 67 m, anneau et couronne ≈ 9 m | Conforme : muret et massif surélevé, joints de bordure blancs, B1 et AB3a de dos. Un feu sur poteau à l'entrée de Verdun ouest n'est pas expliqué. `ilot_central: herbe haute` faute de mot (A4). |
| rp_didcot (M03) | 25cbe3d8 l-102.9 ; 0f41f230 l+102.9 | ortho : Ø ≈ 46 m, anneau ≈ 9 m | Conforme : couronne en pavés rouges avec deux rangs de galets, B21-1 et panonceau, mâts rouges, barrière et B1 de la bretelle. |
| verdun_lycee_feux (M08) | 921c90d1 t004 ; ef8cd80b t004 | ortho | Conforme : petit îlot rond, butte basse, palissade, tirets de guidage. Voir M4 (îlots tronqués). |
| vieux_chene_taillefer_feux (M07) | fccb6997 l+102.9 ; ad0b728e l-102.9 | ortho | Conforme : îlot directionnel bordé, voie directe de tourne-à-droite, D21, B1, passage faïencé et bande verte. |
| vieux_chene_inovallee_piste (M16) | 7d44455e l-154.3, l+51.4 ; 17826b13 l+0 | ortho 2024, antérieure à la réfection, ce que le relevé explique | Conforme : îlot ocre sans hachures, figurines et doubles chevrons, feu cycliste, borne incendie, abri « M ». |
| avenue_7_laux_separateur | c531e1b2 l+0, l+102.9 ; ce125bd7 l+154.3 | ortho | Conforme dans l'ensemble : caniveau central en pavés, muret plus loin, barrière **bordeaux**, pontages. Voir M7. |
| axe_verdun_centre | 9985e2e3 l+0 ; 1977f0a0 l+0 | coupe verdun_c s0340 et ortho de M17 | 1977f0a0 conforme. 9985e2e3 contredit la description (M5). |
| axe_verdun_ouest | a880f2d0 l+0 ; 9f1498db l+0 | coupe verdun_o s0440 | Conforme : damier jaune, haie taillée d'environ 1,2 m dans le TPC, 2 voies. |
| auto_a41_section_courante | 716ad033 l+102.9 t-35, et zoom ×4 du D41c ; a2064553 l-51.4 | coupe a41_sc s0230 | Conforme : D41c « 500 m » lu sur le zoom ; TPC de 6,8 m entre lignes intérieures (6,9 annoncé) ; T3 au-delà du pont. |
| auto_a41_echangeur_meylan_est | 4d06322c l+0 ; c0a557b7 l+0 | coupe a41_est s0650 | Conforme : chevrons, J14a, 4 voies dont la décélération, séparateur béton. Le rôle de 4d06322c dit « sur la bretelle », mais la prise de vue est sur la voie de droite de l'A41. |
| auto_a41_extremite_ouest | 07416282 l+0 ; 80d3d532 l+0 | coupe a41_ouest s0260 | Conforme : C207 et B14 « 110 » des deux côtés, ligne d'effet, C28, flèche de rabattement. |
| auto_noeud_a41_n87 | 3f34cf0a l+0 ; 74dd6869 t007 | coupe b_helice s0169 | Conforme : musoir à chevrons et J14a, B14 « 70 », muret et talus de l'hélice. |
| auto_n87_rocade_sud | 8357ddf1 l+0 ; 2e993fc0 l+0 (rangées dans le dossier de `auto_noeud_a41_n87`) | coupe n87 s0530 | Conforme : un seul séparateur béton double face, d'environ 0,8 m, TPC d'environ 2 m. Voir M8 sur le mot « GBA ». |

### 5.2 Problèmes

| # | Problème | Preuve | Correctif | Propriétaire |
|---|---|---|---|---|
| M1 | **Les descriptions se recouvrent, avec des profils contradictoires.** 5 paires de tronçons de sites différents ont des axes à moins de 1 m sur 30 à 53 m (détail sous ce tableau). Deux exemples. (1) Au sud-ouest de M17 : le lot A donne une voie de 4,1, une zone hachurée de 3,7, de l'herbe au nord-ouest sur 2,8 et une piste de 3,0 ; le lot B donne une voie de 3,6, une zone hachurée de 3,4, un accotement de 5,6 et une piste de 4,0. Au sud-est, le lot A a une piste mixte de 3,0, le lot B un trottoir de 2,0 ; la photo de22683a t004 montre bien un cheminement derrière l'herbe. (2) Au nord-est de M01 : le lot A a 4 voies (11,6 m) à 80 m ; le lot B commence à k 1 080 (76 m) en 1 + 1 avec une zone hachurée de 3,4. Or la photo 20d1a815 t006 et l'ortho 2024 montrent deux voies vers le sud-ouest à environ 70 m. | `relecture_preparation/outils/recouvrements.py` ; photos citées | Une règle « un tronçon, un propriétaire ». Couper les axes du lot B à la frontière des carrefours du lot A, avec des nœuds partagés (format réseau, porte P03-2 et CC-04). En attendant, dire dans INDEX_SITES § 6 quel lot fait foi sur chaque recouvrement. | lots A et B |
| M2 | **Dates d'état mélangées.** Lot A : 28/07/2026 pour 7 sites, 31/08/2025 (chantier) pour M01. Lot B : de 2023-03 (hélice) à 2026-07 ; `axe_verdun_*` au 18/05/2025 ; échangeur de Meylan-Est entre 2024-06 et 2026-02. Exemple du format : printemps 2025. La porte P00-5 de la chaîne exige une date unique par réseau. **M01 réunit trois états** : Revirée et Vercors au 18/05/2025 (avant travaux) ; Verdun au 31/08/2025 (chantier, en option) ; côté nord-ouest de Verdun sud-ouest pris dans le levé GAM, qui est l'« état projet », donc après travaux, ce que dit `DESCRIPTION.md` § 4. La cible du dépôt est l'état avant travaux (CLAUDE.md). | `date:` des YAML ; `paquet_jardin/description.yaml` (Verdun SO, coupe `verdun_so_40`) | Décision de l'utilisateur : quel état de référence pour Meylan ? Pour M01 : reprendre l'inventaire avant travaux (`recon/out/paquet_jardin/v2_avant_travaux/inventaire/`) et garder le 31/08/2025 en option datée (A8). | utilisateur, puis lot A |
| M3 | M17 est mal qualifié dans le dossier 13 (« carrefour à feux »). Le lot A a raison ; la chaîne et l'exemple du format avaient repris l'erreur. | F2 | Chaîne corrigée (§ 9) ; exemple du format, voir F2 ; ERRATA du dossier 13. | format ; DocRoute |
| M4 | **Écarts admis sans mesure, ou créés par la simplification**, alors qu'INDEX_SITES § 3 dit qu'ils ont tous une coupe ou une photo. Quatre cas. (1) `verdun_centre_feux` RF-GV-RAY-006 : rayon de 2,7 m « calculé sur la géométrie simplifiée ; mouvement ni observé ni exclu ». (2) `verdun_lycee_feux` RF-GV-CAR-008 : îlots « réduits par le solveur à leur nez », alors que les vrais îlots dépassent 20 m. (3) RF-MA-REF-003 à 0,11 m « non mesurable » (`paquet_jardin`, `verdun_lycee_feux`). (4) RF-MA-REF-003 dans `verdun_centre_feux`, prouvé par le dossier 13 et non par une mesure du site. | `ecarts_admis` des YAML | Un artefact n'est pas un écart admis. Mouvement : l'interdire (`mouvements`) ou corriger la géométrie. Îlots longs : nouveau besoin A21. Valeur non mesurée : prendre la valeur conforme ou une valeur [G] de confiance faible, sans « admettre » de non-conformité. | lot A |
| M5 | `axe_verdun_centre` : (a) « pas de bordure le long des voies » est contredit à k ≈ 1 500-1 525 : 9985e2e3 montre une bordure et une voie de tourne-à-droite avec flèche ; (b) le carrefour latéral de k ≈ 1 420-1 460 n'est pas décrit. La coupe s0340 montre un débouché au nord-ouest, un passage et une traversée verte (OSM way/759539693, rue résidentielle à 4,2 m) ; plus largement, les rues latérales (tous les 60 à 100 m) ne sont décrites ni par un nœud ni par un évènement. (c) Le rôle de 9985e2e3 dit « approche du carrefour M17 » : la prise de vue est 46 m au sud-ouest de M17 et s'en éloigne. (d) Le tronçon 1 commence en 1 + 1 à k 1 080, voir M1. | photos et coupe citées ; positions L93 de `photos.json` | Arrêter le tronçon 1 avant k ≈ 1 460, ou y décrire le débouché, la voie de tourne-à-droite et la bordure. Reprendre le début du tronçon 1. Corriger le rôle dans `constats_photos.json` du lot B, puis régénérer `photos.json`. | lot B |
| M6 | `verdun_centre_feux` : le tronçon `buclos_n` est à double sens sur 40 m. OSM : 581180883 (2 voies, environ 20 m), puis 27286062 à sens unique vers l'avenue. Le B1 de cette partie à sens unique est visible sur de22683a t003. La provenance « give_way osm:8355380882 » est fausse : ce nœud est à 7,5 m au nord-ouest de l'axe, près du passage, à environ 20 m du débouché de Buclos nord. L'AB3a de f252d62f suffit comme preuve. | `vecteurs/osm.json` du site | Limiter le double sens à 20 m, ajouter le B1 et corriger la provenance. | lot A |
| M7 | `avenue_7_laux_separateur` : la chaussée nord-ouest est coupée par des tirets vers le rond-point (c531e1b2 l+0, deux voies d'entrée, cohérent avec rp_lycee « entrée 2 voies 8,1 m »). Le YAML garde une seule « voie 6,0 » à l'extrémité sud-ouest. Avec la branche `sept_laux` de rp_lycee : décalage latéral de 11,6 m et vide de 17 m. | photo ; `recouvrements.py` | Décrire le passage à deux voies et raccorder par un nœud partagé avec rp_lycee. | lot A |
| M8 | **GBA ou DBA.** Le lot B (4 YAML), le format de l'étape 2 (vocabulaire : `gba` seulement ; scène A1 « TPC 2,60 à GBA ») et la table mots → assets confondent les deux. Un séparateur central double face est un **DBA** (Cerema ; catalogue `retenue_DBA_*`, base 0,60). `extensions_auto` donne d'ailleurs `largeur_base_m: 0.6`. Le mot « GBA » mène à `retenue_GBA_*`, simple face (base 0,48, dos à 6°) : le PCG poserait un mur à dos plat au milieu du TPC. | photos 8357ddf1, 2e993fc0, c0a557b7 ; planche `e3_retenue_beton` (regardée) ; `vocabulaire.py` l. 208 | Ajouter `DBA` au vocabulaire (étape 2). Renommer dans le lot B. Dans la table des assets, règle « séparateur entre deux sens » → DBA. | étape 2, lot B, assets |
| M9 | **Les YAML du lot B sont refusés tels quels** par le compilateur (« clé(s) inconnue(s) extensions_auto ») : 7 sur 7. Ils compilent seulement une fois cette clé retirée, ce que fait l'outil de test du lot. | `compilation_relecture.json` | Ranger les extensions dans un fichier voisin (`description_extensions.yaml`), ou faire accepter une clé réservée (`extensions`) par le compilateur. | lot B ou étape 2 |
| M10 | **L'échangeur ne peut pas être reconstruit en 3D avec ces descriptions** : aucun MNT, aucun profil en long, ouvrages et tirants d'air sans cote, trois niveaux au nœud A41/N87 (B15). Le LiDAR HD local ne couvre pas l'échangeur (L-08). | LOT_B § 4 ; CHAINE L-08 | Télécharger les dalles LiDAR HD de l'échangeur (IGN, Licence Ouverte, sur D:) avant les lots N2 et N9. | lot N2 et N9 |

Recouvrements mesurés : longueur d'axe à moins de 6 m, distance minimale entre axes.

| Tronçon 1 | Tronçon 2 | Longueur commune | Écart d'axe |
|---|---|---|---|
| axe_verdun_centre, tronçon 1 | verdun_centre_feux `verdun_so` | 52,9 m | 0,3 m |
| axe_verdun_centre, tronçon 2 | verdun_centre_feux `verdun_ne` | 48,1 m | 0,7 m |
| auto_noeud_a41_n87 « Meylan vers A41 La Tronche » | vieux_chene_taillefer_feux `helice_s` | 44,5 m | 0,0 m |
| axe_verdun_centre, tronçon 2 | verdun_lycee_feux `verdun_so` | 35,7 m | 1,1 m |
| axe_verdun_centre, tronçon 1 | paquet_jardin `verdun_ne` | 29,6 m | 2,1 m |

Les quatre sites de l'A41 se raccordent bien bout à bout : les extrémités coïncident (0,0 m) sur cinq raccords, dont
la branche N87 → A41 vers Chambéry entre le nœud et l'échangeur de Meylan-Est.

**La N87 n'atteint pas le nœud.** `auto_n87_rocade_sud` s'arrête en (918 327 ; 6 459 581), à s = 997. Les bretelles
de `auto_noeud_a41_n87` commencent à 103 m de là (918 366 ; 6 459 677, début du way 84073), et à 116 m pour « A41 vers
N87 sud ». Personne ne décrit ces 103 à 116 m, alors que `LOT_B_AUTOROUTE_AXES.md` § 1 et
`extensions_auto.limites_du_site` disent que la N87 « se raccorde au nœud ». Correctif (lot B) : prolonger la N87
jusqu'aux musoirs, ou commencer les bretelles à s = 997, avec un nœud partagé.

### 5.3 Compatibilité des YAML avec le format (recompilation du 17-18/10/2026)

| Sites | Tels quels | Sans `extensions_auto` | Erreurs de validation | Non-conformités non admises | Avertissements |
|---|---|---|---|---|---|
| 8 sites du lot A | 8 / 8 compilent | — | 0 | 0 | paquet_jardin 5 (dont un refuge de 1,00 m < 2,0, DEF-022), verdun_lycee_feux 2, verdun_centre_feux 1, autres 0 |
| 7 sites du lot B | **0 / 7** (clé inconnue) | 7 / 7 | 0 | 0 | 1 à 13 par site : cassures de polylignes OSM jusqu'à 30° ; « T'3 3u posé, la règle donne T4 3u » ; biseaux de 60 à 80 m < L = 156 à 195 m (RF-MQ-RET-01) |

Les besoins non portés sont listés (A1 à A20, B1 à B17). Les annonces des deux lots sont donc exactes, à M9 près.

### 5.4 Les descriptions suffisent-elles pour refaire la scène ?

**Oui pour les carrefours urbains et les sections courantes**, en plan : profils chiffrés et sourcés, régimes, équipements
et matériaux observés.

**Non, pas encore, pour :**

- les raccords entre sites (M1) ;
- les rues latérales de l'avenue de Verdun (M5) ;
- le relief et les ouvrages de l'échangeur (M10) ;
- les plans de feux, qui ne sont que des hypothèses (A6) ;
- les hauteurs, estimées à ± 0,2 à 0,4 m.

## 6. Photos et versionnement

- **Lots A et B.** `recon/generateur/meylan/` contenait 78 fichiers texte et aucune image avant ce rapport. `carte_sites.svg` ne contient
  aucune image, ni intégrée ni liée. Aucun `base64` dans les JSON. Photos, tuiles, orthos et coupes sont sous
  `recon/out/generateur/meylan/` (ignoré : `recon/out/*`). Les photos et tuiles de tiers sont toutes sous
  `<site>/photos_non_versionnees/`, sauf les 3 photos de la N87, rangées dans le dossier de `auto_noeud_a41_n87` :
  c'est acceptable, et `photos.json` le dit. Les `photos.json` donnent auteur, licence et lien, sans image.
- **Chaîne et assets.** Aucune photo n'a été regardée ni stockée pour la chaîne. Les planches d'assets ne montrent que
  des rendus (`D:\DocRoute\14_…\controle\etape3\`, 49 planches de 1 092 × 774 à 854 px, qui entrent toutes sans
  réduction).
- **Hors des quatre lots, mais contraire à la règle.** 23 fichiers sont des vues Panoramax des sites M20, M24 et M27 :
  `photo_176f9ab0`, `photo_9badc00e`, `photo_f877235a`, `photo_30b80a7b` et leurs tuiles. `rendu/planches_photo.py`
  les copie dans `recon/generateur/tmp/**/rendus/`, chemin qui n'est **ni** un `photos_non_versionnees/` **ni**
  ignoré : le `.gitignore` racine n'a pas de règle pour `recon/generateur/tmp/`, et `recon/generateur/.gitignore` ne
  contient que `__pycache__/`. `recon/generateur/tmp/l3a/sources/` contient aussi des images de fabricants.
  **Correctif :**
  - ajouter `recon/generateur/tmp/` au `.gitignore`, ou écrire ces planches dans un `photos_non_versionnees/` ;
  - vérifier par `git status` qu'aucune n'a été suivie (non fait : pas de git dans cette relecture).
- **Cette relecture.** Les agrandissements d'ortho (Etalab) sont dans `relecture_preparation/zooms/`. L'agrandissement
  tiré d'une photo (D41c) est dans `auto_a41_section_courante/photos_non_versionnees/relecture_preparation/`.

## 7. Assets de l'étape 3

**Ce qui est vérifié :**

- 795 entrées de l'étape 3 : 0 sans source ; confiance haute 246, moyenne 347, estimation 202 ;
- 21 matériaux nouveaux sous CC0 1.0 (12 Poly Haven, 9 ambientCG) ;
- 77 fiches mesurées : 76 sous CC0, 1 « maison » ;
- 400 USD de panneaux lus : 400 références de texture, 0 manquante ;
- 49 planches au format natif.

Les quatre planches regardées (`retenue_zoom_GS2_GBA`, `retenue_beton`, `panneaux_montes_1`, `eclairage_routier`)
sont conformes à leurs constats : lisse à deux ondes à 0,70 m, supports au pas de 2 m, GBA simple face, DBA
symétrique, faces des panneaux à l'endroit, hauteurs agglomération et campagne différenciées.

| # | Problème | Preuve | Correctif |
|---|---|---|---|
| X1 | Les phases P01 à P11 contredisent l'ordre de la chaîne (§ 3). Les **120 assets de l'étape 1** (bordures, caniveaux, garde-corps, feux, supports…) n'ont pas de `phase_chantier` (null). « Chaque asset porte une phase » ne vaut que pour 795 entrées sur 915. | catalogue | Ajouter `etape_chaine` à toutes les entrées. Les 120 entrées de l'étape 1 restent inchangées, sauf ce champ. |
| X2 | **La licence des faces de panneaux n'est pas levée** : « Licence Ouverte 2.0 présumée, réserve non levée ». Cela concerne 600 panneaux, 1 644 variantes et les 27 ensembles qui les utilisent, ainsi que les planches `e3_panneaux_*`. Les PNG et USD sont dans `assets/lib`, non versionné : c'est correct, mais il n'y a pas encore de « licence propre ». | `licence` des entrées `panneau_*` | Lever la réserve avant toute diffusion (paquet UE, captures, dépôt public). C'est à l'utilisateur ou au lot panneaux. |
| X3 | Confiance incohérente : `abri_bus_L340` et `dalle_reperage_porte_bus_600x600` n'ont que la source « estimation », mais sont notés « moyenne ». | catalogue | Les passer en « estimation ». |
| X4 | Des mots et objets vus à Meylan n'ont pas d'asset ou en ont un faux. Barrière **bordeaux** (photos c531e1b2, ce125bd7) : l'asset est en RAL 7024 graphite. D21 et D41 (texte variable : 0 asset, alors qu'ils sont partout en M01, M02, M07 et sur l'A41). J14a et J14b (musoirs de l'A41 et de la N87 ; lacune reconnue par le lot). CE2a (borne d'appel d'urgence). Clôture autoroutière. Caméra sur mât de feux. BN1, BN2, BN4. GR4. « GBA » → simple face, voir M8. | `correspondances_description` ; `_lacunes` des constats | Variante de teinte bordeaux. Familles D21 et D41 paramétriques (texte, nombre de lignes). J14a et CE2a. Règle DBA. |
| X5 | La phrase de l'utilisateur est lue « 2 × 2 voies + TPC de 20 m » (F5). | ASSETS § 2.1 | S'aligner sur la lecture de E00. |
| X6 | La planche `eclairage_routier` est prise dans l'axe : 02 (double crosse) et 03 (simple crosse) se superposent, et la double crosse n'est pas vérifiable. Le constat ne la mentionne pas. | planche regardée | Refaire la vue en 3/4. |
| X7 | À vérifier : l'USD de `retenue_GBA_L100` (étape 3) porte `route:script = fabriquer_assets_route.py` (script de l'étape 1). | en-tête USD | Écrire le script de l'étape 3 dans les métadonnées, si c'est lui qui fabrique. |

## 8. Correctifs, par priorité

| Priorité | Correctif | Propriétaire |
|---|---|---|
| Bloquant | Un seul ordre de construction : `etape_chaine` dans le catalogue, phases réordonnées, ordres de site en notes (§ 3, X1). | assets, lots A et B |
| Bloquant | Un propriétaire par tronçon, et des nœuds partagés entre les sites qui se recouvrent (M1, M7) ; combler le vide de 103 m entre la N87 et le nœud (§ 5.2). | lots A et B, puis lot N1 |
| Bloquant | État de référence unique pour Meylan, et M01 remis à l'état avant travaux (M2). | utilisateur, puis lot A |
| Bloquant | FORMAT § 4.3 : une mesure hors de la plage n'est jamais jetée (F1). | format réseau |
| Bloquant | `extensions_auto` accepté ou déplacé (M9) ; DBA dans le vocabulaire et dans la table des assets (M8). | étape 2, lot B, assets |
| Bloquant | Photos tierces de `recon/generateur/tmp/` à protéger (§ 6). | étape 2 et utilisateur |
| Important | C1 à C4 (dépendances, P06-4, sortie partagée) dans le JSON, puis le Markdown ; C8 (générateur versionné). | chaîne |
| Important | F2, F3, F4 et F6 (exemples et clés du format). | format réseau |
| Important | M4 (écarts admis), M5 (axe de Verdun centre), M6 (Buclos nord), M10 (LiDAR de l'échangeur). | lots A et B, N2 |
| Important | X2 (licence des panneaux), X4 (assets manquants). | utilisateur, assets |
| Mineur | C5 à C7, R1 à R5 (listes périmées, lignes, citations), F5, X3, X5 à X7, rôles des photos (M5c, 4d06322c). | chaîne, format, assets, lot B |

## 9. Correction faite par cette relecture

Une seule correction de nommage. Dans `CHAINE_CONSTRUCTION.md` § 7.1, paragraphe du corridor de l'avenue de Verdun,
qui n'est pas dupliqué dans le JSON :

- avant : « site M17, carrefour à feux à îlot central refuge » ;
- après : « site M17 : passage piéton à feux avec refuge, entre deux débouchés en baïonnette en
  cédez-le-passage, relevé `meylan/verdun_centre_feux` ».

Le reste n'a pas été modifié. Quatre corrections touchent des passages présents aussi dans `chaine_construction.json`,
la source machine : identifiant LOC-ECL-001, listes de la § 3, entrées d'E02, P12-5. Les faire dans le seul Markdown
créerait un écart entre les deux fichiers. Elles sont donc laissées au lot « chaîne ».

## 10. Limites de cette relecture

- 45 règles relues sur les 350 identifiants distincts cités par la chaîne et le format : les autres n'ont été contrôlées qu'en existence.
- 35 tuiles regardées sur les 93 citées par les lots, et 4 planches d'assets sur 49.
- Les largeurs n'ont pas été remesurées sur l'ortho, sauf le contrôle visuel des diamètres de giratoires et du TPC de
  l'A41.
- Pas de `git status` (consigne) : on ne sait pas si les fichiers de `recon/generateur/tmp/` sont déjà suivis.
- Les 795 USD n'ont pas été rouverts avec pxr : le module n'est pas disponible hors de hython.
