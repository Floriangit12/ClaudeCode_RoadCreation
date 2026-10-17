# Chaîne de construction d'un réseau routier : de la description au réseau continu

*`recon/generateur/CHAINE_CONSTRUCTION.md`, 17/10/2026. Lot « chaîne de construction » de l'étape 3 du générateur.
Version machine : `recon/generateur/chaine_construction.json` ; les fiches du § 3 et le JSON ont la même donnée. Format
d'entrée proposé : `recon/generateur/FORMAT_DESCRIPTION_RESEAU.md`. Ce document s'appuie sur `PLAN_GENERATEUR.md`
(lots L0 à L9), `hda/README_RG.md`, `description/FORMAT_DESCRIPTION.md`, la synthèse
`D:\DocRoute\00_SYNTHESE_CONCEPTION_ROUTES_FR.md` (renvois 08 à 14), la base `assets/specs/route/regles_route_fr.json`
(857 règles, 34 paramètres DEF, 20 arbitrages ARB) et les specs du dépôt (`assets/specs/regles_conception.json` pour
les familles TQ et GA, `regles_implantation.json` pour les familles RI). Le code a été lu, pas modifié. L'étape 2 (types
de bordures, solveur de carrefours, carrefour complexe, giratoires, autoroutes) est en cours dans un autre workflow :
aucun de ses fichiers n'est touché par ce lot.*

## 0. En bref

- **Le but.** Reconstruire Meylan, carrefours, avenues et bouts d'autoroute, à partir de descriptions simples écrites
  en regardant les photos Panoramax (« route à 2 voies à double sens, terre-plein planté sur environ 20 m »). Le
  résultat doit être un réseau continu, pas une suite de segments posés côte à côte.
- **La chaîne.** Elle compte 20 étapes en quatre phases : décrire (E00) ; concevoir une épure unique pour tout le réseau
  (E01 à E06) ; construire par couches dans l'ordre d'un chantier (E07 à E17) ; livrer et contrôler (E18, E19).
  Chaque étape a son contrat de données, ses HDA, ses règles RF-, DEF- et ARB- et une porte bloquante.
- **L'ordre retenu.** On conçoit d'abord la chaussée : graphe, tracé, profil en long, profils en travers, carrefours.
  On construit ensuite comme sur un chantier : terrassements et ouvrages, puis bordures et caniveaux, avaloirs, enrobé,
  trottoirs, marquages (lignes, puis lignes d'arrêt, puis flèches), dispositifs de retenue, panneaux et feux,
  éclairage, mobilier urbain, et la végétation plus tard. Six changements par rapport à la proposition de départ sont
  justifiés au § 2.2.
- **La continuité est garantie par construction.** Une seule épure : graphe, plan-masse et champ de Z sont communs à
  tout le réseau. Les raccords entre routes et carrefours sont des contrats (profil d'extrémité figé). Les objets
  linéaires suivent des chaînes, pas des routes : tour d'îlot pour les bordures, itinéraire pour les marquages,
  réseau pour les piétons. Treize contrôles de continuité (CC-01 à CC-13) s'y ajoutent.
- **Le code actuel fabrique des segments isolés.** Dix ruptures précises sont relevées (§ 6). Les principales :
  nœuds `limite_carte` à chaque tronçon décrit ; carrefours non lus par Houdini ; chaussée ancrée à Z = 0 ; une
  triangulation et un HeightField par route ; files de bordure par route ; phase des tirets remise à zéro à chaque
  tronçon ; cartes d'usure en (s, t) de la route.
- **La migration** se fait en 11 lots (N1 à N11), dans de nouveaux dossiers et de nouvelles versions d'HDA. Elle ne
  casse rien : une description au format de l'étape 2 doit traverser le résolveur sans changer d'un octet, et les
  empreintes sha256 des scènes S01-S12, J1-J3 et M20/M24/M27 servent de témoin.
- **Le format réseau n'est pas un format de plus.** C'est une couche au-dessus du format de réseau que l'étape 2 écrit
  en ce moment (`description_simple/0.2` : `troncons`, `carrefours`, `giratoires`, `bretelles`). Elle ajoute les nœuds
  ancrés, les valeurs approchées, l'accrochage à OSM, les itinéraires, les ouvrages et les échangeurs.
- **Les lacunes sont nommées (§ 9).** La géométrie des échangeurs et des autoroutes manque dans la base. Les guides
  ICTAVRU et VSA 90/110 sont pourtant dans DocRoute ; les valeurs utiles ont été relues et sont citées « à verser ».
  Manquent aussi le profil en long en ville, l'assainissement, l'éclairage, la retenue, certains assets, le LiDAR
  hors Paquet Jardin et le schéma 0.2.

## 1. Pourquoi une chaîne de réseau

L'utilisateur a demandé un PCG « très complexe et très bien fait », avec beaucoup d'assets, de bibliothèques de
textures et d'étapes de conception, « pour que l'ensemble soit pas des bouts de segment sans continuité ». Il a donné
un exemple : « d'abord on fabrique le bitume puis les trottoirs puis les panneaux puis flèche etc. A toi de voir l'ordre
des étapes ».

Un projet routier réel ne commence pas par l'enrobé. Il commence par une **épure** : le tracé en plan et en long, les
profils en travers et les carrefours, le plan de masse avec ses bordures, le nivellement et l'assainissement. Le
chantier vient ensuite, couche par couche, et chaque couche s'appuie sur la même épure. Le générateur doit faire de
même. C'est ce qui manque aujourd'hui : chaque route est un petit monde (s, t) avec son sol, son Z, ses bordures et ses
tirets. Deux routes qui se touchent ne savent rien l'une de l'autre (§ 6).

Principes de la chaîne :

| Id | Principe | Règle |
|---|---|---|
| P1 | Une seule épure | Une description, un graphe, un plan-masse et un champ de Z pour tout le réseau. Chaque couche fabriquée lit l'épure et n'en garde jamais de copie locale : c'est la fin des « mondes (s, t) » séparés, un par route. |
| P2 | Concevoir avant de construire | Les étapes E01 à E06 fixent toute la géométrie : plan, altitudes, profils, carrefours, plan-masse et nivellement. Les étapes E07 à E17 posent des objets sur cette géométrie, dans l'ordre d'un chantier réel, et n'en modifient aucune cote. |
| P3 | Raccords par contrat | Une route se termine toujours sur un nœud partagé. Au droit d'un carrefour, son profil d'extrémité est figé (position t de chaque limite, niveaux) et la frontière du carrefour le reprend exactement (segment `joint`, OpenDRIVE 1.8.1 § 12.10 ; 12M § 4.1). |
| P4 | Les objets linéaires suivent des chaînes, pas des routes | Chaque objet linéaire est porté par une chaîne qui ignore les découpes en routes : les bordures font le tour de l'îlot bâti ou du terre-plein, coins compris ; les marquages suivent l'itinéraire ; les cheminements piétons et cyclables forment des réseaux ; le fil d'eau est découpé en bassins. |
| P5 | Houdini n'invente rien (inchangé) | Chaque valeur vient de la description (avec sa plage si elle est approchée), d'une mesure ou d'une règle nommée RF-*, DEF-* ou ARB-*, et porte sa provenance (`prov`). Sans aucune de ces sources, l'étape s'arrête et le dit. |
| P6 | Portes bloquantes | Une étape ne démarre que si la porte de l'étape précédente est franchie (0 échec bloquant). Chaque porte écrit son rapport JSON. Un écart admis (`ecarts_admis`, FORMAT_DESCRIPTION § 12 bis) lève un contrôle « non conforme », jamais un contrôle de continuité. |
| P7 | Déterminisme et identifiants stables | Les identifiants sont dérivés des noms de la description et la graine vaut hash(id). Deux fabrications donnent les mêmes octets (README_HDA § 9.2 ; README_RG § 1). |
| P8 | Chantiers et tuiles | Le réseau est fabriqué par chantiers : une emprise plus une bande de recouvrement, avec une origine locale par chantier. Chaque chantier est découpé en tuiles de 50 m le long de lignes de grille insérées comme contraintes (TQ-SOL-002, TQ-SOL-010). Les arêtes communes à deux tuiles, ou à deux chantiers, sont identiques à l'octet. |

## 2. L'ordre retenu

### 2.1 Vue d'ensemble

```
 A  DÉCRIRE            E00 description réseau (phrases + photos Panoramax + ortho + OSM) ──► meylan/<reseau>/description_reseau.yaml
                          │
 B  CONCEVOIR          E01 graphe ──► E02 tracé en plan + profil en long ──► E03 profils en travers ──► E04 carrefours,
    (une épure                                                                                           giratoires, échangeurs
     pour tout le                                                                                             │
     réseau)           E05 plan-masse unique : faces typées, arêtes, chaînes de bordure, chantiers et tuiles ◄─┘
                          │
                       E06 nivellement unique + hydraulique de surface : Z, aires de carrefour, points bas, fil d'eau
                          │
 C  CONSTRUIRE         E07 terrassements, plate-forme, ouvrages d'art
    (ordre du             ─► E08 bordures et caniveaux (chaînes continues) ─► E09 avaloirs, grilles, regards
     chantier)            ─► E10 chaussée (enrobé, reprises, joints, usure) ─► E11 trottoirs, pistes, terre-pleins, îlots
                          ─► E12 marquages : lignes ► approches et îlots ► transversales ► passages, sas ► flèches, symboles
                          ─► E13 dispositifs de retenue ─► E14 signalisation verticale et feux ─► E15 éclairage
                          ─► E16 mobilier urbain ─► E17 végétation (étape ultérieure)
                          │
 D  LIVRER             E18 exports : USD par tuile + points PCG (UE 5.8), OpenDRIVE 1.4 / 1.8.1, graphe de voies
                          ─► E19 contrôles globaux CC-01 à CC-13, comparaison aux photos Panoramax, revue indépendante
```

Chaque étape ne lit que des sorties d'étapes antérieures. Les étapes E01 à E06 écrivent la géométrie ; à partir d'E07,
plus aucune cote n'est modifiée (P2). Un écart vu en E19 se corrige dans la description (E00), dans une règle ou dans
une HDA, jamais par une retouche de la scène (PLAN_GENERATEUR § 5.2, point 6).

### 2.2 Ce qui change par rapport à la proposition de départ, et pourquoi

| Proposition de départ | Chaîne retenue | Raison |
|---|---|---|
| 0 à 4 (description, graphe, tracé, profils, carrefours) | E00 à E04, inchangés | Ordre d'une étude de projet : on ne dessine un carrefour qu'une fois connus les axes, les altitudes et les profils qui y arrivent. |
| — | **E05 plan-masse unique**, ajouté | C'est la pièce qui supprime les segments isolés. Toutes les limites des routes, des carrefours et des îlots deviennent un seul arrangement plan typé. Le sol, les bordures, les marquages et les objets lisent cet arrangement, et non le (s, t) de chaque route. Un projet réel produit la même pièce : le plan de masse et le plan des bordures (le PCRS en est la forme normalisée, CNIG PCRS v2.0). |
| 5 plate-forme et nivellement | **E06 nivellement et hydraulique de surface** | L'écoulement fait partie de la conception du Z, il n'est pas posé après coup. Le fil d'eau doit avoir une pente d'au moins 0,5 % ou être réglé en dents de scie (GA-CHA-003). Aucun point bas ne doit rester sans exutoire (GA-CHA-004). L'aire d'un carrefour est un plan coté sans minimum dans un passage (TQ-SOL-014). La proposition rangeait l'assainissement en 9 ; la pose des avaloirs reste en E09. |
| — | **E07 terrassements et ouvrages**, ajouté | Les bouts d'autoroute et l'échangeur de Meylan (A41, N87 Rocade Sud, bretelle « Hélice de Meylan », ponts `bridge=yes`, `layer=1` dans OSM) ne se construisent pas sans tablier, piles ni talus. Dans un vrai chantier, ces ouvrages précèdent la chaussée. Le rendu actuel pose la route sur un socle plat (R-08). |
| 6 chaussée, 7 bordures, 9 assainissement | **E08 bordures et caniveaux → E09 avaloirs et regards → E10 chaussée** | Ordre du chantier : les bordures et les caniveaux forment le coffrage de l'enrobé, et les tampons sont mis à la cote avant la couche de roulement. Il y a aussi une raison technique : le maillage de chaussée est coupé contre la face réellement posée du caniveau (TQ-BOR-007 : même Z à ± 3 mm, enrobé jamais en contrebas) et autour des grilles et tampons. Le « d'abord le bitume » de l'utilisateur reste vrai pour la conception : la chaussée est la première chose dessinée (E02 à E06). |
| 10 marquages, 11 panneaux | E12 marquages **puis** E14 panneaux | Les panneaux se placent par rapport aux marques. L'AB4 se pose au droit de la ligne STOP (RF-SV-AB4.POSITION). Le R11 se pose au droit ou à l'aval de la ligne d'effet (RF-FEU.POSITION_LIGNE_EFFET). Une flèche d'affectation exige un C24 (RF-MQ-DIR-01). Dans E12, l'ordre interne suit la même logique : lignes, approches et îlots, lignes transversales, passages et sas, puis flèches. La pointe de la dernière flèche est à 1,50 m de la ligne d'arrêt (DEF-017), qui doit donc exister avant elle. |
| 12 équipements | **E13 dispositifs de retenue** (avant les panneaux) et **E16 mobilier urbain** (après l'éclairage) | Les deux familles n'ont pas les mêmes dépendances. La retenue découle de la plate-forme et des ouvrages : terre-plein de voie rapide de moins de 12 m (RF-GV-TPC-008), appuis à isoler (RF-GV-PON-014). Elle doit précéder les panneaux, car un support ne peut pas être dans l'emprise d'une glissière et, en rase campagne, son implantation dépend de la zone de récupération (RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE). Le mobilier (potelets, arceaux, bancs) prend la place qui reste, autour des supports et des candélabres. La description du site A41 d'un lot voisin (`recon/generateur/meylan/auto_a41_section_courante/description.yaml`, `extensions_auto.etapes`) place elle aussi la retenue avant la signalisation verticale. |
| 13 à 16 | E15, E17, E18, E19, même ordre | L'éclairage avant la végétation : la distance d'un arbre à un candélabre se contrôle à la pose des arbres (RI ECL-05). La végétation reste une étape ultérieure (décision du 17/10/2026, README_RG § 6). |

L'ordre du chantier invoqué ici (terrassements, réseaux, bordures, chaussée, trottoirs, marquage, signalisation,
équipements, éclairage, plantations) est la pratique courante des travaux de voirie. Aucun volet de DocRoute ne le
fixe : c'est un choix [G], justifié chaque fois par une dépendance de données.

### 2.3 Fil rouge : l'exemple de l'utilisateur

Voici « route à 2 voies à double sens, avec un terre-plein entre les deux sens, végétalisé sur environ 20 m », décrit au
format réseau (FORMAT_DESCRIPTION_RESEAU § 10.1), à travers la chaîne :

| Étape | Ce qui se passe |
|---|---|
| E00 | « environ 20 m » devient la plage [18 ; 22] m (FORMAT_DESCRIPTION_RESEAU § 4). Aucune règle ne fixe la longueur d'un terre-plein planté : la valeur retenue est le centre, 20 m (provenance `description:approx`, choix « centre »). « Terre-plein » sans largeur dite prend 2,00 m (RF-OSM-LAR-050, confiance faible). La position, non dite, est prise « au milieu », avec un avertissement. |
| E01 | Deux nœuds partagés avec les rues voisines ; un itinéraire ; u = 5 cm (DEF-001). |
| E02 | Axe régulier calé sur OSM ou sur l'ortho ; z depuis le MNT ; palier ≤ 2 % sur 10 à 20 m avant un carrefour non prioritaire (RF-GV-CAR-005). |
| E03 | Profil « trottoir \| voie ← \| terre-plein \| voie → \| trottoir » sur [s0 ; s0 + 20], profil sans terre-plein ailleurs. Le terre-plein naît et meurt par des lois de largeur, sans saut : chaque voie se déporte de la moitié de la largeur du terre-plein, soit 1 m. |
| E04 | Si l'une des extrémités est un carrefour, le profil d'extrémité est repris tel quel par sa frontière. |
| E05 | Le terre-plein est une face `terre_plein` (genre planté) entourée d'une chaîne de bordure I2 fermée (DEF-005 : vue 0,11). |
| E06 | Tête de bordure moins 3 à 5 cm pour la terre végétale (TQ-SOL-013 (7)) ; chaussée en toit à 2,5 % de part et d'autre (DEF-006). |
| E08 | La chaîne I2 est posée en éléments de 1 m, avec des quarts de rond aux nez. |
| E10, E11 | Enrobé continu de part et d'autre ; terre végétale et gazon dans le terre-plein (`materiaux_sol.json` : gazon_tondu). |
| E12 | Axe T'1 2u hors terre-plein (RF-OSM-MRQ-010). À chaque nez : tête d'îlot symétrique, avec oblique de L/2 = 19,5 m à 50 km/h et continue d'approche de L/6 = 6,5 m portée à 3u (RF-MQ-OBL-05, RF-MQ-OBL-08). Zébra et contour 3u à 2u de la bordure (RF-MQ-MUS-01, RF-MQ-HACH-01, DEF-020). Aucune ligne le long du terre-plein bordé, la bordure délimite (RF-OSM-MRQ-020). Ces cotes viennent des règles, pas de la description. |
| E14 | Balise J5 au nez si l'îlot fait au moins 1,90 m entre rives (RF-GV-ILO-008). |
| E17 | Plus tard : végétation basse à moins de 0,60 m dans les triangles de visibilité (DEF-029). |

## 3. Fiches des étapes

Chaque fiche donne : le but ; les entrées ; les sorties avec leur contrat ; les HDA (existantes, en cours dans l'étape
2, ou à créer) ; les contraintes normatives (base fusionnée, specs du dépôt, documents DocRoute, et valeurs relues dans
les PDF de DocRoute mais pas encore versées dans la base) ; les bibliothèques ; les contrôles bloquants de la porte ; ce
qui garantit la continuité ; l'état du code. Les sorties d'un réseau vont dans `recon/out/generateur/meylan/<reseau>/`
(non versionné). Les photos et leurs tuiles vont seulement dans `recon/out/generateur/meylan/<site>/photos_non_versionnees/`.

### E00 — Description du réseau (texte libre et photos → YAML réseau)

*Phase A ; étape 0 de la proposition de départ ; lot de migration : N1.*

**But.** Écrire ce que montrent les photos Panoramax, l'ortho et OSM, sans viser le millimètre : routes, carrefours, giratoires, bretelles et ouvrages, accrochés à des ancrages (nœuds nommés, OSM, Lambert-93). Chaque valeur dite garde sa plage (« environ 20 m » devient [18 ; 22] m) et sa preuve.

**Entrées.**

- phrases de l'utilisateur ou de Claude (« route 2 × 1 voies avec terre-plein planté sur environ 20 m »)
- photos Panoramax (API STAC, CC-BY-SA ou Etalab) : identifiant, date, pose ; tuiles natives ≤ 1092 px (`recon/pcg/vision/decoupe.py equirect`) rangées dans `recon/out/generateur/meylan/<site>/photos_non_versionnees/`
- ortho IGN 20 cm (WMS Géoplateforme ; `data/raw/ortho_recentes/ign_bdortho_2024_rvb_20cm`) pour les largeurs (`decoupe.py ortho`)
- OSM : `data/vector_gz/osm/roads.geojson.gz` (5 506 ways) ; BD TOPO : `data/vector_gz/bdtopo/troncon_de_route.geojson.gz` (6 890 tronçons : nature, nombre_de_voies, largeur_de_chaussee, position_par_rapport_au_sol)
- constats du dossier 13 (`observations.json` : 72 sites, dont 34 à Meylan) et `assets/specs/regles_locales_meylan.json` (46 règles LOC-*)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/generateur/meylan/<reseau>/description_reseau.yaml` | description_reseau/0.1 (FORMAT_DESCRIPTION_RESEAU.md), versionné, sans aucune image : identifiants de photos, coordonnées et constats seulement ; à côté de `mesures.json` et `photos.json`, comme les descriptions de sites des lots voisins |
| `recon/out/generateur/meylan/<reseau>/description_resolue.yaml` | description exacte au format `description_simple/0.2` de l'étape 2 (troncons[] à id, carrefours, giratoires, bretelles), entrée du compilateur de réseau |
| `recon/out/generateur/meylan/<reseau>/compilation_reseau.json` | approximations résolues (valeur dite, plage, valeur retenue, raison : mesure, règle ou centre), ancrages résolus, avertissements, erreurs |

**HDA et outils.**

- `recon/pcg/vision/decoupe.py` (tuiles natives)
- `recon/pcg/enrichir/projection.py` (`decoupe_perspective`) et `recon/pcg/vision/decoupe.py` (`vue_equirect`) : découpes ciblées à la taille native
- `inference/osm_vers_modele.py` (brouillon du graphe et des régimes, lecture seule)
- `description/description_vers_modele.py` et `commun/profil.py` (grammaire des profils, importés sans modification)
- à créer : `recon/generateur/reseau/resoudre_reseau.py` (lot N1), qui écrit une description au format de l'étape 2 puis appelle son compilateur (FORMAT_DESCRIPTION_RESEAU § 9)

**Contraintes normatives.**

- Base fusionnée : RF-OBS-MAR-01, RF-OBS-MAR-02, RF-OBS-ILO-03, RF-OSM-CAR-011, RF-OSM-CAR-012, RF-OSM-PRF-011, RF-OBS-VEG-02, RF-OBS-MAR-03, RF-OSM-OUV-001, RF-OSM-BDT-001 ; DEF-008, DEF-020 ; ARB-19.
- DocRoute : 00_SYNTHESE § 0.1 (ordre de priorité) et § 16 (pratiques locales) ; 13 OBSERVATIONS_ISERE.md ; 12I INFERENCE_OSM_VERS_PROFIL.md.

**Contrôles bloquants (porte P00).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P00-1 | clés et mots connus | 0 inconnu (erreur, jamais ignoré) | FORMAT_DESCRIPTION § 12 |
| P00-2 | chaque route a `de` et `vers` sur des nœuds déclarés ; chaque nœud a un ancrage résoluble (L93, local, OSM ou relatif) | 100 % | — |
| P00-3 | chaque valeur approchée a une plage finie et non vide | 100 % | — |
| P00-4 | chaque pratique locale non conforme à l'IISR (ocre, vert, Chronovélo, damier) porte une preuve `photo:` ou `mesure:` | 100 % | 00_SYNTHESE § 0.1 ; RF-OBS-MAR-01 |
| P00-5 | date d'état unique ; photos citées datées, valables à cette date, hors marquage de chantier | 0 photo hors état (avertissement si la date manque) | RF-OBS-MAR-03 |
| P00-6 | aucune image ni tuile dans un fichier versionné | 0 | CLAUDE.md du dépôt |

**Ce qui garantit la continuité.**

- Les nœuds portent un nom partagé : deux routes qui se touchent citent le même nœud.
- Un carrefour est un objet décrit (type, régime, branches), jamais la fin d'un tronçon.
- Les itinéraires (nom de voie, u, priorité) sont déclarés une fois pour toute la suite de routes.

**État du code (lecture seule, 17/10/2026).**

- Existe : format d'un tronçon isolé (`description/FORMAT_DESCRIPTION.md`) et son compilateur (`description_vers_modele.py`, 2 418 lignes à la lecture).
- Existe : compilateur de réseau de l'étape 2 en cours d'écriture : `description/carrefours.py`, format `description_simple/0.2` (troncons[] à id, carrefours, giratoires, bretelles ; scènes `scenes_carrefours/J1` à `J3`).
- Existe : descriptions de sites de Meylan en cours dans les lots voisins (`recon/generateur/meylan/<site>/` : description.yaml, mesures.json, photos.json, et `extensions_auto` pour ce que le format ne dit pas encore).
- Existe : 12 exemples, catalogue S01 à S12, trois rues de Meylan décrites d'après photo (M20, M24, M27).
- Existe : inférence OSM → modèle avec nœuds partagés et carrefours topologiques.
- Manque : couche réseau (proposée : FORMAT_DESCRIPTION_RESEAU.md) : nœuds ancrés, valeurs approchées, accrochage à OSM, itinéraires, ouvrages, échangeurs.
- Manque : résolveur (lot N1).

### E01 — Graphe topologique

*Phase B ; étape 1 de la proposition de départ ; lot de migration : N1, N3.*

**But.** Construire un seul graphe pour tout le réseau. Il contient les nœuds partagés et les routes de nœud à nœud. Chaque carrefour regroupe un ou plusieurs nœuds fusionnés. Les branches sont triées par azimut. Le graphe porte aussi les sens, les régimes, les priorités, les mouvements autorisés voie à voie et les itinéraires.

**Entrées.**

- description compilée (E00)
- topologie OSM (`osm_vers_modele.construire`) quand la route est ancrée sur OSM

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/modele/modele_reseau.json` | modele_voie/0.2 (proposé) : `noeuds[]` (type RF-OSM-CAR-001), `routes[]` (noeud_debut, noeud_fin, categorie, vitesse_kmh, agglomeration, prioritaire), `carrefours[]` (type, regime, noeuds fusionnés, branches : regime, bandes_entrantes, bandes_sortantes, mouvements), `itineraires[]` (nouveau : suite ordonnée de routes, nom, u_m, prioritaire) |
| `recon/out/generateur/meylan/<reseau>/controle/p01_graphe.json` | porte P01 |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::lire_modele::1.0` | existe | `recon/generateur/hda/rg_lire_modele` | ne lit pas `carrefours` (lecteur.py l. 30-32, avertissement l. 313) : version lisant les carrefours = lot de l'étape 2, à reprendre |
| `rg::graphe::1.0` | existe | `recon/generateur/hda/rg_graphe` | branches triées par azimut, valence (construire.py l. 247-282) : utilisable tel quel |

- compilateur réseau (N1) : fusion des carrefours complexes (osm2streets CollapseShortRoads), mouvements depuis `turn:lanes`

**Contraintes normatives.**

- Base fusionnée : RF-OSM-CAR-001, RF-OSM-CAR-002, RF-OSM-CAR-010, RF-OSM-CAR-011, RF-OSM-CAR-012, RF-OSM-PRF-011, RF-OSM-VOI-001, RF-OSM-VOI-004, RF-OSM-VIT-001, RF-OSM-AGG-001, RF-GV-CAR-001, RF-GV-CAR-006, RF-GV-GIR-017, RF-SV-CARREFOUR.COMPLEXE, RF-MQ-U-05, RF-OSM-MRQ-001, RF-MQ-CED-03 ; DEF-001 ; ARB-19.
- DocRoute : 12M § 1 à § 4 ; 12I § 5 ; 10C § 1 ; 09F § 3 (couloirs).

**Contrôles bloquants (porte P01).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P01-1 | chaque extrémité de route est un nœud du graphe ; `limite_carte` seulement au bord de l'emprise déclarée | 100 % | CC-01 |
| P01-2 | tout nœud de valence ≥ 3 appartient à un carrefour ; deux nœuds reliés par une route de moins de 15 m [G] sont fusionnés ou la route est justifiée | 0 exception non justifiée | RF-OSM-CAR-001 |
| P01-3 | graphe orienté connexe (sens uniques compris) ou composante isolée déclarée | 0 cul-de-sac non déclaré | — |
| P01-4 | chaque branche entrante a ≥ 1 mouvement sortant ; chaque branche a un régime, sinon « à vérifier » (rien de peint) | 100 % | RF-OSM-CAR-012 ; ARB-19 |
| P01-5 | aucune ligne cédez ni AB4 prévue sur une branche à feux | 0 | RF-MQ-CED-03 ; RF-SV-AB4.POSITION |
| P01-6 | u constant le long d'un itinéraire | 0 changement | RF-MQ-U-05 |

**Ce qui garantit la continuité.**

- Les routes partagent leurs nœuds : il n'y a plus de `limite_carte` à l'intérieur du réseau.
- Un itinéraire est une chaîne de routes. Elle porte à travers les carrefours la ligne d'axe, sa phase, u et la priorité (RF-MQ-CAR-01).
- Les mouvements voie à voie sont les futurs liens du graphe de voies (E18).

**État du code (lecture seule, 17/10/2026).**

- Existe : inférence OSM : nœuds partagés et carrefours (osm_vers_modele.py l. 585-613 ; `carrefour_plan` l. 766 ; `carrefour_giratoire` l. 928).
- Existe : rg::graphe : branches et valence.
- Manque : description : chaque tronçon isolé reçoit deux nœuds `limite_carte` (description_vers_modele.py l. 2221-2222) ; l'étape 2 crée désormais les nœuds des carrefours décrits (`description/carrefours.py`), mais pas encore les nœuds de connexion ni les ancrages.
- Manque : itinéraires, mouvements voie à voie, fusion des carrefours complexes.
- Manque : lecture des carrefours dans Houdini (lot de l'étape 2).

### E02 — Tracé en plan et profil en long

*Phase B ; étape 2 de la proposition de départ ; lot de migration : N2.*

**But.** Donner à chaque route une ligne de référence régulière (droites, arcs, clothoïdes), raccordée en tangence à ses voisines d'itinéraire. Lui donner aussi une altitude réelle : un profil en long (pentes et raccordements) calé sur le terrain et sur les gabarits des ouvrages, et un dévers en courbe.

**Entrées.**

- graphe (E01)
- polylignes OSM ou tracé décrit
- mesures d'axe sur l'ortho
- MNT ou LiDAR HD : 4 dalles de 1 km² autour de Paquet Jardin (`data/sites/paquet_jardin/avant_travaux/lidar_hd*`) ; le reste de Meylan est à télécharger (lacune L-08)
- gabarits verticaux des ouvrages (E04, E07)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/modele/modele_reseau.json` | `routes[].ligne_reference.geometrie_reguliere` (schéma 0.1) ; `routes[].profil_long` (0.1 : points [s, z] ; 0.2 proposé : déclivités + raccordements de rayon R, source mnt \| lidar \| mesure \| ouvrage) ; `routes[].devers` (loi de s) ; z de chaque nœud |
| `recon/out/generateur/meylan/<reseau>/controle/p02_trace.json` | porte P02 (écarts au tracé OSM ou mesuré, ruptures de cap, déclivités) |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::graphe::1.0` | existe | `recon/generateur/hda/rg_graphe` | échantillonnage à flèche ≤ 0,5 mm des droites, arcs et clothoïdes |
| lecture du profil en long | à créer | — | `profil_long` existe au schéma 0.1 mais n'est lu nulle part ; le Z de la chaussée est ancré à 0 en t = 0 (rg_niveau.h l. 5) |

- ajustement des géométries régulières sur les polylignes OSM ou sur les mesures (Python hors Houdini, lot N2)
- échantillonnage du MNT le long des axes (Python, lot N2)

**Contraintes normatives.**

- Base fusionnée : RF-GV-DEV-001, RF-GV-DEV-002, RF-GV-DEV-003, RF-GV-RAY-012, RF-GV-RAY-009, RF-MA-CYC-004, RF-GV-CAR-004, RF-GV-CAR-005, RF-GV-GIR-022, RF-MA-TRO-003, RF-GV-PON-012, RF-OSM-OUV-001, RF-OSM-OUV-002, RF-GV-PT-008, RF-MQ-PS-01, RF-MQ-MIX-01.
- Specs du dépôt : TQ-SOL-004.
- DocRoute : 10PT § 3 (surlargeur) et § 5 (dévers, pentes) ; 10P § 4 (gabarits).
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : ICTAVRU (2009) p. 29-30 : rayons en plan A 80 : 240 m (dévers 5 %), non déversé 400 m ; U 60 : 120 m ; U 80 : 240 m ; clothoïde L = max(14 (δ1 − δ0) ; R/9).
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : ICTAVRU p. 31 : déclivité moyenne ≤ 6 % (U 60, U 80, A 80), ≤ 5 % (A 100), ≤ 3 % conseillé à l'approche d'un carrefour plan (type U) ; rayon rentrant minimal 800 / 1 000 / 1 500 m (U 60 / U 80 et A 80 / A 100).
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : VSA 90/110 (Cerema 2014) p. 12-14 : Rm 240 m (VSA 90) et 400 m (VSA 110) avec d = 7 % ; Rdn 370 / 650 m ; clothoïde si R < 1,5 Rdn ; alignement ≥ 75 / 92 m entre deux courbes de même sens ≤ 1 500 m ; déclivité ≤ 6 % ; saillant ≥ 2 700 / 6 000 m ; rentrant ≥ 1 300 / 1 900 m.

**Contrôles bloquants (porte P02).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P02-1 | raccords des primitives et des routes d'un même itinéraire : continuité de position et de cap | écart ≤ 1 mm ; rupture de cap ≤ 0,5° | CC-02 |
| P02-2 | écart du tracé régulier à l'ancrage (OSM ou mesure) | OSM ≤ 1,50 m [G] ; mesure ortho ≤ 0,30 m [G] | RF-OSM-BDT-001 (contrôle croisé) |
| P02-3 | z continu aux nœuds : toutes les routes d'un nœud ont le même z (centre du carrefour ou joint) | \|Δz\| ≤ 1 cm | CC-03 |
| P02-4 | déclivités et rayons dans les plages de la catégorie | 0 hors plage non admis | à verser (ICTAVRU, VSA 90/110) |
| P02-5 | deux routes qui se croisent sans nœud ont un ouvrage qui déclare l'écart de niveau | écart ≥ gabarit (4,30 m ; 4,75 m sous autoroute) + 0,10 m | RF-GV-PON-012 ; RF-OSM-OUV-001 |
| P02-6 | dévers : variation le long des clothoïdes seulement, jamais dans l'arc | 0 | RF-GV-DEV-003 |

**Ce qui garantit la continuité.**

- Les itinéraires sont continus en tangence (G1) à travers les nœuds de connexion et les carrefours.
- Toutes les routes d'un nœud partagent le même z.
- Un croisement sans nœud est forcément dénivelé, avec un ouvrage déclaré.

**État du code (lecture seule, 17/10/2026).**

- Existe : droites, arcs et clothoïdes dans la description et dans rg::graphe.
- Existe : dévers en toit ou à pente unique (DEF-006, commun/profil.py l. 632-684).
- Manque : ajustement de géométries régulières sur OSM (README_RG § 8 : décalés en onglet, replis aux sommets).
- Manque : profil en long : jamais lu ; chaussée ancrée à Z = 0 (README_RG § 5).
- Manque : dévers en courbe (RF-GV-DEV-002) et gauchissement le long des clothoïdes.
- Manque : règles de tracé des voies rapides urbaines (ICTAVRU, VSA 90/110) absentes de la base.

### E03 — Profils en travers et transitions le long des arcs

*Phase B ; étape 3 de la proposition de départ ; lot de migration : N1 (contrôle inter-routes), étape 2 (profils d'autoroute).*

**But.** Dérouler le profil de chaque route (bandes et limites), ses transitions (élargissements, rabattements, voies de tourne-à-gauche, terre-pleins qui naissent) et son profil d'extrémité. Le profil d'extrémité devient le contrat passé avec le carrefour ou avec la route suivante.

**Entrées.**

- modèle (E01, E02)
- profils décrits ou inférés

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/modele/modele_reseau.json` | `profils[]`, `routes[].sections[]` contiguës de 0 à L, lois de largeur |
| `recon/out/generateur/meylan/<reseau>/l1/courbes_controle.json` | limites (s, t, x, y), rubans, profils d'extrémité (sortie 3 de rg::profils), profil en long |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::profils::1.0` | existe | `recon/generateur/hda/rg_profils` | limites décalées, rubans, profils d'extrémité « frontière des futurs carrefours » (construire.py l. 264-269) |

- `commun/profil.py` (constructeur commun à la description et à l'inférence, 844 lignes)

**Contraintes normatives.**

- Base fusionnée : RF-OSM-PRF-001, RF-OSM-PRF-002, RF-OSM-PRF-010, RF-OSM-LAR-010, RF-OSM-LAR-014, RF-GV-PT-001, RF-GV-PT-002, RF-GV-PT-006, RF-GV-PT-008, RF-GV-PT-009, RF-GV-PT-014, RF-GV-VS-001, RF-GV-VS-005, RF-GV-VS-010, RF-MQ-OBL-02, RF-OSM-NIV-010, RF-OSM-NIV-011, RF-OSM-NIV-013, RF-MA-TRO-001, RF-MA-PIS-006, RF-MA-SEP-001, RF-GV-TPC-001, RF-GV-TPC-002, RF-GV-TPC-005, RF-GV-TPC-006 ; DEF-002, DEF-003, DEF-004, DEF-005, DEF-006, DEF-007, DEF-008, DEF-009 ; ARB-06, ARB-17, ARB-18.
- DocRoute : 10PT § 1 et § 2 ; 10T § 2 ; 11C § 3 ; 12M § 3.
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : ICTAVRU p. 91 : bretelle à 1 voie 4 m + S(R) avec BAU, 5 m + S(R) sans ; 2 voies 7 m + 2 S(R) ; S(R) = 35/R (diffuseurs), 50/R (nœuds) ; berme ≥ 1 m ; BAU 2 m si possible ; BDG 0,50 à 1 m.

**Contrôles bloquants (porte P03).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P03-1 | contrôles du lot L1 : largeurs > 0, 0 chevauchement, sections contiguës, jonctions de sections | écart ≤ 1 mm | README_RG § 4 |
| P03-2 | nœud de connexion (valence 2) : mêmes bandes et mêmes largeurs des deux côtés, ou transition déclarée | écart ≤ 1 mm | CC-04 |
| P03-3 | cheminement libre de 1,40 m sur chaque trottoir (hors bande technique) | 100 % du linéaire | RF-MA-TRO-001 |
| P03-4 | non-conformités de compilation non admises | 0 (bloque la fabrication, comme aujourd'hui) | FORMAT_DESCRIPTION § 11 |

**Ce qui garantit la continuité.**

- Le profil d'extrémité est figé : le carrefour (E04) le reprend tel quel, avec les mêmes t et les mêmes niveaux.
- Les transitions se font par lois de largeur, jamais par saut, sauf changement instantané déclaré.

**État du code (lecture seule, 17/10/2026).**

- Existe : rg::profils et commun/profil.py (lots L0 à L2b).
- Manque : contrôle de continuité d'une route à la suivante (aujourd'hui seulement d'une section à l'autre dans une route).
- Manque : profils d'autoroute et de bretelle (BAU, BDG, séparateur GBA) : lot de l'étape 2.

### E04 — Conception des carrefours, giratoires et échangeurs

*Phase B ; étape 4 de la proposition de départ ; lot de migration : étape 2 (solveur) ; N4 consomme ses sorties.*

**But.** Résoudre chaque carrefour : coins, coupes des routes, frontière fermée, îlots (gouttes d'eau, central, directionnel, refuges), giratoires (anneau, îlot central, couronne, îlots séparateurs), échangeurs (bretelles, musoirs, voies d'insertion et de décélération), trajectoires, conflits et zone de conflit. Placer aussi les lignes d'arrêt et les passages, comme données de conception (la peinture vient en E12).

**Entrées.**

- graphe, tracé, profils d'extrémité (E01 à E03)
- véhicules de projet (lot L3a de l'étape 2)
- description des carrefours (E00)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/modele/modele_reseau.json` | `carrefours[]` complets (frontiere, ilots, anneau, trajectoires, conflits, zone_conflit, passages_pieton, controleur) ; routes coupées (`trim`) et routes trop courtes absorbées ; `ilots[]` |
| `recon/out/generateur/meylan/<reseau>/controle/p04_carrefours.json` | porte P04 (rg_carrefours_controles) |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| compilateur de réseau `description/carrefours.py` | étape 2 (en cours) | `recon/generateur/description/carrefours.py` | en cours dans l'étape 2 : deux passes de compilation ; branches, frontière (limite de la chaussée abordée), coins, lignes transversales, passages, sas, flèches, îlots, trajectoires, conflits, zone de conflit, signaux, contrôleur de feux, anneau de giratoire, musoirs de bretelle ; géométrie calculée en Python (shapely) à la compilation. Cette chaîne en consomme les sorties sans les refaire |
| `rg::carrefours::1.0` | à créer | — | prévue au plan (lot L3) ; à redéfinir : la conception est faite à la compilation, Houdini fabrique (E05 et suivantes) |

- `vehicules/vehicules_projet.json`, `vehicules/balayage.py` (lot L3a, étape 2)

**Contraintes normatives.**

- Base fusionnée : RF-GV-RAY-001, RF-GV-RAY-003, RF-GV-RAY-005, RF-GV-RAY-006, RF-GV-RAY-007, RF-GV-CAR-004, RF-GV-CAR-007, RF-GV-CAR-010, RF-GV-CAR-015, RF-GV-CAR-017, RF-GV-ILO-001, RF-GV-ILO-003, RF-GV-ILO-004, RF-GV-ILO-007, RF-GV-ILO-008, RF-GV-ILO-015, RF-GV-GIR-004, RF-GV-GIR-006, RF-GV-GIR-008, RF-GV-GIR-013, RF-GV-GIR-014, RF-GV-VS-016, RF-GV-VS-017, RF-GV-VS-018, RF-GV-TPC-014, RF-GV-TRJ-001, RF-GV-TRJ-006, RF-GV-PIE-010, RF-MQ-INS-01, RF-MQ-INS-02, RF-MQ-INS-03, RF-MQ-DEC-01, RF-MQ-OBL-04, RF-SV-INSERTION.AB3A, RF-OSM-CAR-030, RF-OSM-CAR-040, RF-OSM-CAR-060 ; DEF-010, DEF-012, DEF-022, DEF-023, DEF-024 ; ARB-02, ARB-09, ARB-15.
- DocRoute : 10C § 2 à § 9 (algorithme § 9) ; 10G § 2 à § 7 ; 10T § 3 ; PLAN_GENERATEUR § 2.4 ; 12A § 4.
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : ICTAVRU p. 83-84 : bretelle = déboîtement ou insertion, décélération ou accélération, courbe, transition ; obliquité d'une entrée entre 1/20 et 1/30.
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : ICTAVRU p. 87-89 : longueur de décélération L = (Vs² − V(R)²)/3 (1,5 m/s²), d'accélération L' = (Vi² − V(R)²)/2 (1 m/s²) ; R ≥ 20 m sur une attache, ≤ 50 m sur une boucle ; V(R) = 30 km/h pour R = 22 m, 50 km/h pour R = 80 m (dévers 5 %).
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : ICTAVRU p. 90 : déclivités des bretelles de diffuseur, entrée 5 % en rampe et 8 % en pente, sortie 7 % et 6 %.
- À verser dans la base (relu le 17/10/2026 dans le PDF, pages imprimées) : VSA 90/110 p. 37-38 : obliquité de sortie 1/33 (1/20 depuis une bretelle à une voie), d'entrée 1/33 à 1/20 ; entrecroisement de 300 à 750 m entre une entrée et une sortie rapprochées ; 0,70 m au moins entre la balise de musoir et le bord de la bretelle.

**Contrôles bloquants (porte P04).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P04-1 | frontière fermée, segments dans le sens trigonométrique | 100 % | 12M § 4.1 |
| P04-2 | coins tangents et rayon = consigne | rupture ≤ 0,5° ; ± 1 cm | PLAN_GENERATEUR L3 |
| P04-3 | traversée piétonne hors refuge | ≤ 12 m (bloquant) | RF-GV-PIE-010 |
| P04-4 | refuge au droit du passage | ≥ 2,00 m (2,50 m aux feux si chaussée ≥ 12 m) | DEF-022 ; ARB-15 |
| P04-5 | giratoire : déflexion | < 100 m sur chaque couple de branches | RF-GV-GIR-008 |
| P04-6 | trajectoires : rayon d'axe ≥ véhicule de projet | 100 % | RF-GV-TRJ-006 |
| P04-7 | nombre de voies constant dans l'intersection | 100 % | RF-GV-CAR-007 |
| P04-8 | joint : la frontière reprend le profil d'extrémité de la route | t des limites ± 1 mm ; z ± 1 mm | CC-04 |

**Ce qui garantit la continuité.**

- Chaque segment `joint` de la frontière coïncide avec le profil d'extrémité de sa route (P3).
- Les coins raccordent en tangence les limites extérieures de deux branches voisines. Les bordures deviennent ainsi continues d'une rue à l'autre.
- Une bretelle est une route de catégorie `bretelle`. Ses deux bouts sont des nœuds `fourche` (musoirs de divergence et de convergence) partagés avec la chaussée principale.

**État du code (lecture seule, 17/10/2026).**

- Existe : contrat de données (schéma : carrefour, branche, frontiere_segment, trajectoire, conflit, ilot, anneau).
- Existe : compilateur de réseau de l'étape 2 en cours, scènes J1 (T en cédez), J2 (croix à STOP), J3 (croix à feux).
- Manque : fin de l'étape 2 (hors de ce lot) : giratoires et autoroutes encore vides le 17/10/2026 (`scenes_giratoires/`, `scenes_autoroutes/`).
- Manque : échangeurs : aucune règle de géométrie de bretelle dans la base (lacune L-01).

### E05 — Plan-masse unique (épure 2D du réseau) *(étape ajoutée)*

*Phase B ; étape ajoutée à la proposition de départ ; lot de migration : N4.*

**But.** Assembler toutes les limites en un seul arrangement plan du chantier, typé et sans trou : rives et bordures des routes, coins, frontières de carrefour, îlots, bretelles, abords. Chaque face reçoit un type, un matériau et une région de niveau. Chaque arête reçoit une nature (bordure, changement de revêtement, ligne de rupture, bord de plate-forme). Les arêtes de bordure s'enchaînent en chaînes continues.

**Entrées.**

- limites décalées et rubans (E03)
- coins, frontières et îlots (E04)
- abords décrits (pelouse, parking…)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/plan_masse/arrangement.json` | faces (id stable, type : chaussee \| trottoir \| piste \| terre_plein \| ilot \| quai \| abord, materiau_id, region_niveau, route ou carrefour propriétaire) ; arêtes (nature, profil de bordure, vue (loi), caniveau, abaissés) ; chaînes de bordure (id, suite d'arêtes, côté haut, fermée ou non, points durs) ; lignes de rupture (couronnes, joints de sections) |
| `recon/out/generateur/meylan/<reseau>/plan_masse/tuiles.json` | chantiers, origines locales, grille de tuiles de 50 m (lignes de grille = contraintes) |
| `recon/out/generateur/meylan/<reseau>/controle/p05_plan_masse.json` | porte P05 |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::plan_masse::1.0` | à créer | — | VEX, Intersection Analysis, Boolean, PolyExpand2D ; remplace la partition en (s, t) propre à chaque route |

- contrôle indépendant en Python (shapely), comme `validation/controler_L1.py`

**Contraintes normatives.**

- Base fusionnée : RF-GV-RAY-001, RF-MA-ABA-006, RF-AS-pas_element, RF-MA-TRO-011 ; DEF-005 ; ARB-18.
- Specs du dépôt : TQ-SOL-001, TQ-SOL-002, TQ-SOL-003, TQ-SOL-010.
- DocRoute : 03 CNIG PCRS v2.0 (classes limite de voirie, fil d'eau, bordure) ; 12A § 5 (contrat de `pj::sol`).

**Contrôles bloquants (porte P05).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P05-1 | arrangement plan valide : 0 auto-intersection, 0 trou, 0 recouvrement ; somme des aires des faces = aire de l'emprise | écart d'aire ≤ 1e-6 relatif | CC-05 ; TQ-SOL-001 |
| P05-2 | chaque face a un seul type et un seul matériau | 100 % | — |
| P05-3 | entre deux faces de niveaux différents : une bordure, ou « sans bordure » déclarée avec dz = 0 | 100 % | — |
| P05-4 | chaînes de bordure sans lacune ; un bout de chaîne seulement sur un point dur déclaré (abaissé, bateau, chartière, bord de chantier) | lacune ≤ 1 mm | CC-06 |
| P05-5 | arêtes calées sur une grille de 1 mm ; arêtes < 5 mm et contraintes quasi parallèles à < 5 mm fusionnées | 100 % | TQ-SOL-001 |

**Ce qui garantit la continuité.**

- C'est la garantie centrale : une seule vérité plane pour toutes les couches fabriquées (sol, bordures, marquages, objets).
- Les arêtes partagées sont identiques des deux côtés : même polyligne, même sens de parcours inversé.

**État du code (lecture seule, 17/10/2026).**

- Existe : partition en (s, t) d'une seule route (rg::nivellement, rg::sol) ; zones sous les bordures.
- Manque : arrangement plan à l'échelle du réseau (tout est à créer).

### E06 — Nivellement unique et hydraulique de surface

*Phase B ; étape 5 de la proposition de départ ; lot de migration : N5.*

**But.** Calculer un seul champ de Z pour tout le chantier. Sur la chaussée hors carrefour : profil en long et dévers. Dans l'aire d'un carrefour : un plan coté, interpolé entre les profils des branches. Ensuite viennent les caniveaux, les pieds et les têtes de bordure, les trottoirs, les îlots et les abords raccordés au terrain. Le même calcul vérifie que chaque point bas a un exutoire et donne les pentes du fil d'eau.

**Entrées.**

- plan-masse (E05)
- profil en long et dévers (E02)
- vues de bordure et niveaux des bandes (E03)
- MNT

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/niveau/heightfield_<tuile>.npy` | HeightField 0,10 m (height, r0, z1, r1, z2, r2), rangé comme celui de pj::lire_description (README_HDA § 2) |
| `recon/out/generateur/meylan/<reseau>/niveau/niveaux.json` | sections, files de bordure (pied, tête, vue, fil d'eau), aires de carrefour |
| `recon/out/generateur/meylan/<reseau>/niveau/hydraulique.json` | points bas et leur exutoire, pente de chaque file de fil d'eau, bassins de surface et aire collectée |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::nivellement::1.0` | existe | `recon/generateur/hda/rg_nivellement` | modèle de Z unique par route ; nappes numérotées par route (construire.py l. 777-815) |
| `rg::nivellement::2.0` | à créer | — | Z réseau : profil en long, aires de carrefour, MNT, hydraulique |

- `hda/commun/vex/rg_niveau.h` (coupe en travers, inversion (x, y) → (s, t)) : réutilisé

**Contraintes normatives.**

- Base fusionnée : RF-GV-DEV-001, RF-GV-DEV-002, RF-GV-GIR-005, RF-GV-GIR-006, RF-GV-CAR-005, RF-MA-TRO-002, RF-MA-TRO-003, RF-MA-TRO-004, RF-MA-ABA-001, RF-MA-ABA-004, RF-MA-RAL-001, RF-GV-PON-012, RF-MA-BUS-011 ; DEF-005, DEF-006, DEF-031, DEF-034.
- Specs du dépôt : TQ-SOL-013, TQ-SOL-014, TQ-SOL-004, TQ-SOL-007, GA-CHA-003, GA-CHA-004, GA-ASS-001.
- DocRoute : 10PT § 5 ; 10G § 4 ; 11P § 1 et § 3.

**Contrôles bloquants (porte P06).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P06-1 | un seul Z par (x, y, région) ; les marches existent seulement aux bordures | vue = modèle ± 5 mm | TQ-SOL-013 |
| P06-2 | continuité aux joints, aux tuiles et aux chantiers | \|Δz\| ≤ 1 mm | CC-03 ; CC-07 |
| P06-3 | cheminement : dévers ≤ 2 % ; pente < 5 % hors rampants | 100 % | RF-MA-TRO-002 ; RF-MA-TRO-003 |
| P06-4 | aucun point bas sans exutoire (avaloir à moins de 1 m) | 0 | GA-CHA-004 ; CC-12 |
| P06-5 | fil d'eau : pente ≥ 0,5 %, sinon dents de scie avec un avaloir à chaque point bas | 100 % | GA-CHA-003 |
| P06-6 | aire de carrefour : pente résultante ≥ 0,5 %, dévers local ≤ 4 %, aucun minimum dans un passage, un abaissé ou un sas | 100 % | TQ-SOL-014 |
| P06-7 | anneau de giratoire : dévers vers l'extérieur, ≤ 3 % | 100 % | RF-GV-GIR-005 |
| P06-8 | hauteur libre sous ouvrage | ≥ 4,30 m (4,75 m autoroute) + 0,10 m | RF-GV-PON-012 |

**Ce qui garantit la continuité.**

- Le Z est continu à travers les joints, les carrefours, les tuiles et les chantiers.
- Le fil d'eau est continu d'une route au coin de carrefour suivant : les caniveaux tournent avec les bordures.
- Hors des surfaces modélisées, le terrain est le MNT conditionné, raccordé aux bords de plate-forme (TQ-SOL-007).

**État du code (lecture seule, 17/10/2026).**

- Existe : modèle de Z unique sur une route (README_RG § 5), HeightField 0,10 m, abaissés, ralentisseurs, grilles au droit des plateaux.
- Manque : Z réel (profil en long, MNT) : la chaussée est à Z = 0 en t = 0.
- Manque : aires de carrefour (TQ-SOL-014), points bas, exutoires, pentes du fil d'eau.
- Manque : HeightField à l'échelle du réseau (régions numérotées 100 × rang de route + nappe).

### E07 — Terrassements, plate-forme et ouvrages d'art *(étape ajoutée)*

*Phase C ; étape ajoutée à la proposition de départ ; lot de migration : N9.*

**But.** Fabriquer ce qui porte la chaussée. D'abord la plate-forme étanche, raccordée au terrain par des talus. Puis les murs de soutènement et les ouvrages : tablier, corniches, piles, culées, joints, trémies, par exemple les trois ponts OSM de la bretelle de la Rocade Sud vers l'A41 et l'« Hélice de Meylan ». Le terrain est abaissé sous les ouvrages.

**Entrées.**

- plan-masse et Z (E05, E06)
- `ouvrages[]` du modèle (routes portées, franchit, gabarit, travées)
- MNT

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/fabrique/terrain_<tuile>.usda` | terrain et talus (materiau_id, pj_couche) |
| `recon/out/generateur/meylan/<reseau>/fabrique/ouvrages.usda` | tabliers, piles, culées, murs ; points `pj_points/0.1` des garde-corps et barrières |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::ouvrages::1.0` | à créer | — | prévue au lot L8 du plan |
| `rg::terrain::1.0` | à créer | — | raccord au MNT, talus, abaissement sous ouvrage |

**Contraintes normatives.**

- Base fusionnée : RF-GV-PON-001, RF-GV-PON-002, RF-GV-PON-003, RF-GV-PON-005, RF-GV-PON-007, RF-GV-PON-009, RF-GV-PON-010, RF-GV-PON-011, RF-GV-PON-012, RF-GV-PON-014, RF-GV-PON-015, RF-AS-garde_corps_S8, RF-AS-garde_corps_hauteur, RF-OSM-OUV-001 ; DEF-033.
- Specs du dépôt : TQ-SOL-007, TQ-SOL-009.
- DocRoute : 10P (PONTS_OUVRAGES.md) ; 14 § 6.8.

**Bibliothèques (meshes, matériaux, gabarits).**

- garde-corps (4 meshes, dont S8) et barrières (3) de `catalogue_assets_route.json`
- matériaux béton PBR `route_fr`
- manquent : glissières GS2/GS4, BN4, parapets béton, garde-corps à lisses (ASSETS_ROUTE § 9) ; GBA, DBA et corniches (non prévus au dossier 14)

**Contrôles bloquants (porte P07).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P07-1 | hauteur libre sous ouvrage | ≥ gabarit + 0,10 m | RF-GV-PON-012 |
| P07-2 | épaisseur de tablier selon le type | l/20 à l/28 (dalle PSIDA) | RF-GV-PON-015 |
| P07-3 | hauteur des garde-corps | [0,90 + 0,005 Hc ; min(1,00 + 0,005 Hc ; 1,20)] | DEF-033 |
| P07-4 | terrain sans trou ni surplomb sous l'ouvrage ; plate-forme étanche | 0 arête libre intérieure | TQ-SOL-009 |

**Ce qui garantit la continuité.**

- Le dessus du tablier est la plate-forme d'E06 : la chaussée sur l'ouvrage est la même face du plan-masse.
- Les joints de chaussée aux abouts traversent aussi le trottoir (RF-GV-PON-011).

**État du code (lecture seule, 17/10/2026).**

- Existe : contrat `ouvrage` au schéma (type, routes_portees, franchit, gabarit, tablier, appuis, joints).
- Manque : toute la fabrication ; le rendu de l'étape 1 pose la route sur un socle plat neutre (decor_l2b.py l. 820-861).

### E08 — Bordures et caniveaux en chaînes continues

*Phase C ; étape 7 de la proposition de départ ; lot de migration : N6.*

**But.** Poser les bordures et les caniveaux élément par élément le long des chaînes du plan-masse. Une chaîne fait le tour de l'îlot bâti et des terre-pleins, passe les coins en pièces courbes et inclut les abaissés, les bateaux, les chartières et les raccords de vue comme des intervalles. Comme sur un vrai chantier, bordures et caniveaux viennent avant l'enrobé : ils en sont le coffrage.

**Entrées.**

- chaînes de bordure (E05)
- pieds, têtes et fil d'eau (E06)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/fabrique/bordures/elements.json` | éléments posés (profil, longueur, transformation, rôle : courant, chartière, bateau, angle, retour) |
| `recon/out/generateur/meylan/<reseau>/points/bordures.json` | `pj_points/0.1` pour PG_Bordures (TQ-PCG-001) |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::vers_entites::1.0` | existe | `recon/generateur/hda/rg_vers_entites` | files de bordure par route, boucles ouvertes au premier point |
| `rg::vers_entites::2.0` | à créer | — | entités au contrat de pj::lire_description depuis les chaînes du plan-masse |
| `pj::bordure::2.0` | existe | `recon/generateur/hda/pj_bordure_v2` | pièces d'angle en onglet, éléments sur mesure |
| `pj::caniveau::2.1` | existe | `recon/generateur/hda/pj_caniveau_v2_1` | coupe partagée < 0,20 m |

**Contraintes normatives.**

- Base fusionnée : RF-AS-liste_profils_nf, RF-AS-profil_T2, RF-AS-profil_I2, RF-AS-profil_A2, RF-AS-profil_CS2, RF-AS-pas_element, RF-AS-raccord_bateau, RF-OSM-NIV-010, RF-OSM-NIV-012, RF-MA-ABA-001, RF-MA-ABA-006, RF-MA-TRO-015, RF-MA-TRO-016, RF-GV-GIR-006, RF-MA-REF-003, RF-GV-RAY-001 ; DEF-005, DEF-031 ; ARB-18.
- Specs du dépôt : TQ-BOR-001, TQ-BOR-002, TQ-BOR-005, TQ-BOR-007, bordures_elements.json (autre équipe, lecture seule).
- DocRoute : 14 § 6.1 et § 6.2 ; 11P § 3.

**Bibliothèques (meshes, matériaux, gabarits).**

- 64 bordures et 12 caniveaux de `catalogue_assets_route.json` (33 profils lus sur les dessins Alkern)
- matériaux `beton_bordure_gris`, `beton_bordure_clair`, `granit_bordure`, `calcaire_bordure`, `caniveau_beton` (`materiaux_sol.json`)
- manquent : pièces d'angle T3/T4, courbes A et I, quart de rond intérieur T2 coté (ASSETS_ROUTE § 9)

**Contrôles bloquants (porte P08).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P08-1 | joints entre éléments | 3,5 à 9,5 mm ; 0 fente | pj::bordure::2.0 (README_RG § 5) |
| P08-2 | coupe minimale d'un élément | ≥ 0,20 m | TQ-BOR-002 |
| P08-3 | vue posée | = modèle ± 5 mm | DEF-005 |
| P08-4 | chaîne d'îlot fermée ; coin posé en pièce courbe du rayon du coin | 100 % | CC-06 |
| P08-5 | aucun élément sur une face de chaussée | 0 | — |

**Ce qui garantit la continuité.**

- Les identifiants de chaîne sont stables. La pose part d'un point dur et les joints sont phasés le long de la chaîne, pas le long de la route.
- Le caniveau suit sa bordure à travers le coin et ne s'interrompt qu'aux grilles, aux bateaux et aux ralentisseurs.

**État du code (lecture seule, 17/10/2026).**

- Existe : pose en éléments, pièces d'angle, chartières, retours transversaux, grilles d'avaloir (lots L2, L2b, corrections).
- Manque : chaînes à l'échelle du réseau : aujourd'hui une file par route et par côté, coupée aux bouts de route.
- Manque : coins de carrefour (solveur de l'étape 2).
- Manque : types de bordures étendus (étape 2).

### E09 — Assainissement : avaloirs, grilles, regards, tampons

*Phase C ; étape 9 de la proposition de départ ; lot de migration : N6.*

**But.** Poser les ouvrages d'assainissement visibles, avant la couche de roulement comme sur un vrai chantier : un avaloir à chaque point bas d'E06 et au pas réglementaire, des grilles au pied des rampes de plateau, des regards de visite et des tampons sur l'axe de la voie lente, hors traces de roues.

**Entrées.**

- hydraulique (E06)
- chaînes de caniveau (E08)
- trajectoires (E04) pour éviter les traces de roues

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/points/assainissement.json` | `pj_points/0.1` (avaloir, grille, tampon ; classe EN 124) ; trous dans les faces de chaussée et de caniveau |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::vers_entites (sortie 3)` | existe | `recon/generateur/hda/rg_vers_entites` | grilles au pied des rampes de plateau et en bout de file fermée |
| `rg::assainissement::1.0` | à créer | — | points bas → avaloirs ; regards au pas |

**Contraintes normatives.**

- Base fusionnée : RF-MA-BUS-016, RF-MA-RAL-001.
- Specs du dépôt : GA-ASS-001, GA-ASS-002, GA-ASS-003, GA-ASS-004, GA-ASS-006, GA-CHA-004.
- DocRoute : Certu, Coussins et plateaux 2010, p. 46 (cité par README_RG § 5).

**Bibliothèques (meshes, matériaux, gabarits).**

- `decal_grille_avaloir` (décalque) ; prototypes d'avaloir de GA-ASS-002
- manquent : avaloirs et regards en volume (ASSETS_ROUTE § 9)

**Contrôles bloquants (porte P09).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P09-1 | chaque point bas a son avaloir | ≤ 1 m | GA-CHA-004 |
| P09-2 | pas des avaloirs | s = min(350 / largeur drainée ; 50 m) | GA-ASS-001 |
| P09-3 | regards de visite | pas 50 m, ≤ 75 à 80 m ; hors traces de roues et hors stationnement | GA-ASS-004 |
| P09-4 | aucun avaloir dans un passage piéton, une BEV ou un abaissé | 0 | [G] |

**Ce qui garantit la continuité.**

- L'avaloir remplace la pièce de caniveau qu'il occupe. La chaîne de caniveau reste continue (README_RG § 5).

**État du code (lecture seule, 17/10/2026).**

- Existe : grilles au pied des rampes et en bout de file (rg::vers_entites, corrections du 17/10/2026).
- Manque : points bas, pas réglementaire, regards et tampons.

### E10 — Chaussée (bitume) : revêtement, reprises, joints

*Phase C ; étape 6 de la proposition de départ ; lot de migration : N5.*

**But.** Revêtir toutes les faces de chaussée du chantier (routes, carrefours, bretelles) d'un seul maillage étanche, coupé contre les faces de caniveau et autour des tampons. Puis ajouter l'aspect : type d'enrobé par zone, reprises et rapiéçages, pontages de fissures, faïençage, usure dans les traces de roues. Les masques sont calculés en coordonnées du chantier, pas en (s, t) d'une route.

**Entrées.**

- faces `chaussee` (E05)
- Z (E06)
- éléments posés (E08, E09)
- trajectoires (E04) pour les traces de roues

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/fabrique/sol_<tuile>.usda` | maillage Y haut → USD Z haut ; materiau_id ; pj_couche ; pj_entite ; N ; uv en m continues entre tuiles ; primvars de masques (usure, reprise, graine) |
| `recon/out/generateur/meylan/<reseau>/points/decalques_chaussee.json` | décalques (pontages, rapiéçages, tampons) en `pj_points/0.1` |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::sol::1.0` | existe | `recon/generateur/hda/rg_sol` | triangulation contrainte en (s, t) d'une route |
| `rg::sol::2.0` | à créer | — | triangulation (x, y) du chantier contrainte par le plan-masse, Z par région (E06) |
| `rg::aspect_chaussee::1.0` | à créer | — | masques d'usure le long des trajectoires, zones de reprise |

- `rendu/textures_sol.py` et `rendu/textures.py` (cartes d'usure) : à reporter en coordonnées du chantier

**Contraintes normatives.**

- Base fusionnée : RF-OBS-REV-01, RF-OBS-MAR-03, RF-AS-regle_materiaux_elements.
- Specs du dépôt : TQ-SOL-002, TQ-SOL-003, TQ-SOL-008, TQ-SOL-009, TQ-SOL-010, TQ-SOL-011, TQ-SOL-012, TQ-BOR-007.
- DocRoute : 14 § 3 et § 5 (matériaux PBR) ; 13 § 2.9 (revêtements observés).

**Bibliothèques (meshes, matériaux, gabarits).**

- `materiaux_sol.json` (34 matériaux : enrobe_bbsg_ancien, enrobe_bbsg_neuf_2025, enrobe_reprise_tranchee, enrobe_clair_granulats…)
- 27 matériaux PBR CC0 `route_fr` + matériaux du site ; `materiaux_rendu_v2.json`
- `assets/lib` (2,6 Go non versionnés, régénérables)

**Contrôles bloquants (porte P10).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P10-1 | sol 2-variété, sans doublon ni auto-intersection | 0 défaut | TQ-SOL-009 ; CC-07 |
| P10-2 | arêtes communes aux tuiles identiques ; normales calculées avant découpe | 100 % | TQ-SOL-002 ; TQ-SOL-008 |
| P10-3 | caniveau / enrobé au même Z | ± 3 mm ; chaussée sous l'élément ≥ flèche + 1,5 mm | TQ-BOR-007 |
| P10-4 | masques d'aspect continus d'une route au carrefour | 0 couture visible (revue en tuiles) | CC-07 |

**Ce qui garantit la continuité.**

- Un seul maillage par chantier, découpé en tuiles le long de lignes de grille : plus de nappe par route.
- Les UV et les masques sont en coordonnées du chantier (ou de l'itinéraire pour les traces de roues) : aucun raccord de texture au changement de route.

**État du code (lecture seule, 17/10/2026).**

- Existe : rg::sol (étanche sur une route, lignes de rupture, BEV) ; rendu Karma avec cartes d'usure.
- Manque : triangulation du réseau.
- Manque : cartes d'usure lues en (s, t) de la route avec un décalage propre à la scène (rendu_l2b.py l. 963, README_RG § 6) : couture à chaque changement de route.

### E11 — Trottoirs, pistes, terre-pleins et îlots (revêtements)

*Phase C ; étape 8 de la proposition de départ ; lot de migration : N5, N6.*

**But.** Revêtir les autres faces : trottoirs (enrobé, béton balayé ou désactivé avec joints sciés, dalles), pistes et séparateurs, BEV, quais de bus, entrées charretières. Fabriquer aussi les cinq genres de terre-plein (planté, BRF, gravier, hachuré, franchissable) et les îlots.

**Entrées.**

- faces non circulées (E05)
- Z (E06)
- bordures posées (E08)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/fabrique/sol_<tuile>.usda` | faces non circulées dans le même maillage que E10 (même triangulation) |
| `recon/out/generateur/meylan/<reseau>/fabrique/ilots.usda` | remplissages (pj::ilot) |
| `recon/out/generateur/meylan/<reseau>/points/bev.json` | BEV (dalles podotactiles) |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::sol (BEV)` | existe | `recon/generateur/hda/rg_sol` | BEV à 0,50 m du nez, contraste avec le revêtement voisin |
| `rg::terre_pleins::1.0` | à créer | — | prévue au plan (genres → pj::ilot, pj::marquage_zone, semis) |
| `pj::ilot::1.0` | existe (recon/pcg) | `recon/pcg/houdini/hda/pj_ilot` | remplissages BRF, gravier, gazon |

**Contraintes normatives.**

- Base fusionnée : RF-MA-TRO-001, RF-MA-TRO-010, RF-MA-TRO-011, RF-MA-BEV-001, RF-MA-BEV-002, RF-MA-BEV-004, RF-MA-PIS-001, RF-MA-PIS-002, RF-MA-SEP-005, RF-MA-SEP-006, RF-GV-TPC-010, RF-GV-TPC-012, RF-GV-TPC-013, RF-MQ-ILOT-01, RF-MA-BUS-002, RF-MA-BUS-005, RF-GV-GIR-006, RF-OBS-ILO-04 ; DEF-004, DEF-008, DEF-031, DEF-032 ; ARB-06, ARB-17.
- DocRoute : 10T § 1 à § 6 (cinq genres) ; 11P § 1 à § 4 ; 11T § 1 ; 12M § 5.

**Bibliothèques (meshes, matériaux, gabarits).**

- dalles et BEV (5), pavés (4) de `catalogue_assets_route.json`
- `materiaux_sol.json` : beton_balaye, beton_desactive, dalles_beton, paves_granit, bev_podotactile, remplissages d'îlots (brf_bois_concasse, gravier_concasse_6_10, galets_20_40, gazon_tondu…)

**Contrôles bloquants (porte P11).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P11-1 | réseau piéton connexe (trottoirs, passages, refuges) ; cheminement de 1,40 m continu | 100 % | CC-10 ; RF-MA-TRO-001 |
| P11-2 | BEV à chaque traversée matérialisée | 100 % | RF-MA-BEV-001 |
| P11-3 | refuge : BEV selon la largeur | table BEV03 | RF-MA-BEV-004 |
| P11-4 | part de surface perméable rapportée (Métropole de Grenoble) | ≥ 10 % visé (avertissement) | RF-GV-TPC-013 |

**Ce qui garantit la continuité.**

- Les trottoirs d'une rue et ceux du coin de carrefour forment une seule face par îlot bâti, avec les mêmes joints de dalle.
- Les itinéraires cyclables restent continus à travers les traversées. Leurs interruptions sont déclarées (RF-MA-BAN-008).

**État du code (lecture seule, 17/10/2026).**

- Existe : trottoirs, pistes, bandes plantées, zones hachurées, îlot refuge bordé dans une même nappe par route ; BEV.
- Manque : rg::terre_pleins (genres).
- Manque : joints sciés des bétons.
- Manque : réseau piéton et cyclable à l'échelle du réseau.

### E12 — Marquages : longitudinaux, puis transversaux, puis flèches et symboles

*Phase C ; étape 10 de la proposition de départ ; lot de migration : N7.*

**But.** Peindre dans cet ordre. (a) Les lignes longitudinales le long des itinéraires, continues à travers les approches et absentes de la zone de conflit. (b) Les approches : annonces, continues d'approche, contours d'îlots, zébras, chevrons. (c) Les lignes transversales : STOP, cédez, effet des feux. (d) Les passages piétons et les sas. (e) Les flèches et symboles, posés après la ligne d'arrêt qu'ils visent. (f) Le guidage seulement s'il est décrit.

**Entrées.**

- sol fabriqué (E10, E11)
- itinéraires (E01)
- lignes d'arrêt, passages, sas, trajectoires (E04)
- profils (E03)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/fabrique/marquages_<tuile>.usda` | peinture drapée (+2 à 3 mm), materiau_id peinture_<couleur>_u<usure> |
| `recon/out/generateur/meylan/<reseau>/marquages/table_marques.json` | une ligne par marque (type, gabarit, ancrage, règle) |
| `recon/out/generateur/meylan/<reseau>/points/marquages_symboles.json` | instances de symboles pour PG_Symboles |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::marquages::1.0` | existe | `recon/generateur/hda/rg_marquages` | section courante d'une route (lot L2b) |
| `rg::marquages::2.0` | à créer | — | lignes par itinéraire, transversales et symboles de carrefour |
| `pj::marquage_solide::1.0` | existe (recon/pcg) | `recon/pcg/houdini/hda/pj_marquage_commun` | drapage de la peinture |

- `rg_marquages/gabarits_iisr7.py`, `gabarits_iisr7_pj.json` (gabarits et glyphes du dossier 08)

**Contraintes normatives.**

- Base fusionnée : RF-MQ-CAR-01, RF-MQ-CAR-02, RF-MQ-CAR-04, RF-GV-TRJ-002, RF-OSM-MRQ-042, RF-MQ-U-01, RF-MQ-U-05, RF-MQ-LAR-A1b, RF-MQ-LAR-B1b, RF-MQ-LAR-B2d, RF-MQ-LAR-B3, RF-MQ-SC-06, RF-MQ-SC-13, RF-MQ-PS-03, RF-MQ-PS-04, RF-MQ-PS-05, RF-MQ-OBL-01, RF-MQ-OBL-05, RF-MQ-OBL-08, RF-MQ-MUS-01, RF-MQ-HACH-01, RF-MQ-HACH-02, RF-MQ-STOP-01, RF-MQ-STOP-03, RF-MQ-CED-01, RF-MQ-CED-03, RF-MQ-FEU-01, RF-MQ-PP-01, RF-MQ-PP-03, RF-MQ-PP-05, RF-MQ-SAS-01, RF-MQ-DIR-01, RF-MQ-DIR-03, RF-MQ-DIR-06, RF-MQ-DIR-09, RF-MQ-RAB-04, RF-MQ-RAB-06, RF-MQ-INS-01, RF-MQ-DEC-02, RF-MQ-GUI-01, RF-MQ-TC-02, RF-MQ-GIR-01, RF-MQ-GIR-04 ; DEF-001, DEF-011, DEF-012, DEF-013, DEF-014, DEF-015, DEF-016, DEF-017, DEF-018, DEF-019, DEF-020, DEF-021 ; ARB-01, ARB-02, ARB-03, ARB-07, ARB-08, ARB-11, ARB-12, ARB-16.
- Specs du dépôt : TQ-MQG-004, TQ-MQG-005, TQ-MQG-014.
- DocRoute : 08 MARQUAGES_IISR7_COMPLET.md (§ 5 à § 15) ; 08 marquages_iisr7.json (42 gabarits, 72 glyphes, 15 motifs).

**Bibliothèques (meshes, matériaux, gabarits).**

- `marquages_iisr7.json` du dossier 08 : 42 gabarits, 72 glyphes
- `assets/specs/peinture.json`, `marquages_geometrie.json`

**Contrôles bloquants (porte P12).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P12-1 | modulations : période et trait ; largeurs | ± 1 cm sur 100 m ; ± 2 mm | PLAN_GENERATEUR L4 |
| P12-2 | phase continue le long de l'itinéraire : aucun trait tronqué à moins de la moitié au droit d'un joint | 0 | CC-08 |
| P12-3 | 0 ligne longitudinale dans la zone de conflit, hors guidage décrit | 0 | RF-MQ-CAR-02 ; RF-MQ-CAR-04 |
| P12-4 | flèches : pointe de la dernière à 1,50 m de la ligne d'arrêt ; interdistance 20 m | ± 2 cm ; ± 5 cm | DEF-017 |
| P12-5 | peinture au-dessus du sol fabriqué | +2 à 3 mm | TQ-MQG-005 |
| P12-6 | ligne de la route prioritaire non interrompue au droit d'une route non prioritaire | 100 % | RF-MQ-CAR-01 |

**Ce qui garantit la continuité.**

- Les lignes sont construites sur la courbe de l'itinéraire, à travers les routes et les approches. La phase est portée par l'itinéraire, pas remise à zéro à chaque tronçon.
- Les marques transversales et les symboles sont rattachés à leur branche de carrefour, donc à une ligne d'arrêt unique.

**État du code (lecture seule, 17/10/2026).**

- Existe : rg::marquages : lignes, passages, zébras, flèches, triangles, figurines de la section courante, drapés par pj::marquage_solide.
- Manque : phase par itinéraire : aujourd'hui « chaque tronçon commence par un trait » [G] (README_RG § 6).
- Manque : transversales et symboles de carrefour (lots L3 et L4).
- Manque : marquages d'autoroute (u 7,5 cm, T4, T2 5u) : étape 2.

### E13 — Dispositifs de retenue : glissières, séparateurs béton, BN4, garde-corps

*Phase C ; étape 12 (partie retenue) de la proposition de départ ; lot de migration : N8.*

**But.** Poser, avant les panneaux, les dispositifs de retenue qu'exigent la plate-forme et les ouvrages : glissières de rive et de terre-plein, séparateurs en béton (GBA, DBA), barrières BN4 et garde-corps d'ouvrage. Ils forment des files continues, avec extrémités et raccords traités. Leur emprise devient un obstacle connu pour la pose des supports de panneaux et de feux (E14) et du mobilier (E16).

**Entrées.**

- profils et terre-pleins (E03)
- plan-masse (E05)
- Z (E06)
- ouvrages, talus et appuis (E07)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/points/retenue.json` | `pj_points/0.1` : files d'éléments le long d'une chaîne du plan-masse, extrémités, raccords ; emprise de chaque file (polygone) pour E14 et E16 |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::retenue::1.0` | à créer | — | files le long des limites du plan-masse ; éléments, extrémités et raccords en instances |

**Contraintes normatives.**

- Base fusionnée : RF-GV-TPC-002, RF-GV-TPC-003, RF-GV-TPC-004, RF-GV-TPC-005, RF-GV-TPC-007, RF-GV-TPC-008, RF-GV-PON-004, RF-GV-PON-007, RF-GV-PON-008, RF-GV-PON-009, RF-GV-PON-010, RF-GV-PON-014, RF-AS-garde_corps_S8, RF-AS-garde_corps_hauteur ; DEF-033.
- DocRoute : 10T § 2 et § 5 ; 10P § 2 et § 4 ; 14 § 6.8.
- Lacune : guides `Cerema_Guide_Dispositifs_Retenue_Routiers.pdf` et `SETRA_CSEE121_Separateurs_Modulaires_2001.pdf` du dossier 10, non exploités (L-05).

**Bibliothèques (meshes, matériaux, gabarits).**

- garde-corps (4 meshes, dont S8) et barrières (3) de `catalogue_assets_route.json`
- manquent : glissières GS2/GS4, BN4, parapets béton, garde-corps à lisses (ASSETS_ROUTE § 9) ; GBA et DBA (non prévus au dossier 14)

**Contrôles bloquants (porte P13).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P13-1 | terre-plein central de voie rapide de moins de 12 m : barrière de niveau N | 100 % | RF-GV-TPC-008 |
| P13-2 | appuis d'ouvrage proches des voies isolés par un dispositif de retenue ; ≥ 2 m entre voie et appui | 100 % | RF-GV-PON-014 |
| P13-3 | garde-corps : hauteur et vides | [0,90 + 0,005 Hc ; min(1,00 + 0,005 Hc ; 1,20)] ; vides < 15 cm | DEF-033 ; RF-GV-PON-008 |
| P13-4 | files continues : aucune interruption non déclarée ; extrémités et raccords traités | 0 | P4 (chaînes) |

**Ce qui garantit la continuité.**

- Les files suivent les limites du plan-masse à travers les routes et les ouvrages : une glissière de terre-plein continue sous un passage supérieur et contourne la pile. Elles ne s'arrêtent qu'aux extrémités déclarées.

**État du code (lecture seule, 17/10/2026).**

- Existe : garde-corps et barrières en assets ; règles BN01, GC02 et GC97 versées dans la base.
- Manque : toute la pose ; assets de glissières et de séparateurs.

### E14 — Signalisation verticale et feux

*Phase C ; étape 11 de la proposition de départ ; lot de migration : N8.*

**But.** Implanter les panneaux, balises et feux. Leurs positions s'appuient sur les lignes et les surfaces déjà fabriquées : AB4 au droit de la ligne STOP, R11 au droit ou à l'aval de la ligne d'effet, C24 dès qu'il y a des flèches d'affectation, aucun support dans le cheminement de 1,40 m ni dans l'emprise d'un dispositif de retenue (E13). Il faut aussi poser les séquences d'itinéraire (AB6/AB7, B14, EB10/EB20) et, sur autoroute, les panneaux de très grande gamme répétés à gauche.

**Entrées.**

- marquages (E12)
- dispositifs de retenue (E13)
- surfaces (E10, E11)
- branches, régimes et contrôleurs (E01, E04)
- itinéraires (E01)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/points/signalisation.json` | `pj_points/0.1` : panneau (code IISR, face, gamme), support, panonceaux |
| `recon/out/generateur/meylan/<reseau>/points/feux.json` | mâts, têtes, répétiteurs, R12, boutons ; `controleurs[]` du modèle |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::signalisation::1.0` | à créer | — | prévue au plan (lot L6) ; algorithmes 09S § 13 et 09F § 13 |

**Contraintes normatives.**

- Base fusionnée : RF-SV-GEN.DISTANCE_RIVE, RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE, RF-SV-GEN.HAUTEUR.AGGLO, RF-SV-GEN.HAUTEUR.RASE_CAMPAGNE, RF-SV-GEN.EMPLACEMENT, RF-SV-GEN.ORIENTATION, RF-SV-GEN.REPETITION_GAUCHE_2X2, RF-SV-DIM.CHOIX_GAMME, RF-SV-AB3A.POSITION, RF-SV-AB4.POSITION, RF-SV-AB6.EMPLOI, RF-SV-AB25.EMPLOI, RF-SV-B14.EMPLOI, RF-SV-EB.POSITION, RF-SV-J5, RF-SV-J14, RF-MQ-DIR-01, RF-FEU.POSITION_LIGNE_EFFET, RF-FEU.R11.NOMBRE_ET_COTES, RF-FEU.R14, RF-FEU.R12.POSITION, RF-FEU.HAUTEUR.TROTTOIR, RF-FEU.JUXTAPOSITION, RF-GV-ILO-008, RF-GV-ILO-009, RF-GV-VIS-003 ; DEF-025, DEF-026, DEF-027, DEF-028 ; ARB-04, ARB-05, ARB-14, ARB-19, ARB-20.
- Specs du dépôt : RI GEN-01, RI GEN-02, RI GEN-05, RI GEN-08.
- DocRoute : 09S § 4 à § 13 ; 09F § 4 à § 13.

**Bibliothèques (meshes, matériaux, gabarits).**

- `panneaux_fr_catalogue.json` : 870 faces (licence non levée : PNG non diffusés)
- supports (15) et feux (8) de `catalogue_assets_route.json`
- manquent : mât de feux Ø 114, potence, R12m, R14 à R25, écran de contraste (ASSETS_ROUTE § 9 ; 00_SYNTHESE § 15) ; portiques de signalisation d'autoroute (non prévus au dossier 14)

**Contrôles bloquants (porte P14).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P14-1 | branches à régime : panneaux présents (AB3a + M9c, AB4, AB25, B21-1…) | 100 % | PLAN_GENERATEUR L6 |
| P14-2 | 0 AB4 sur une branche à feux ou « à vérifier » | 0 | RF-SV-AB4.POSITION ; ARB-19 |
| P14-3 | bord de panneau à la rive | ≥ 0,70 m, sauf « contrainte » signalée | RF-SV-GEN.DISTANCE_RIVE ; ARB-20 |
| P14-4 | rase campagne : aplomb hors de la zone de récupération ou support à ≥ 2 m du bord ; aucun support dans l'emprise d'un dispositif de retenue | 100 % | RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE |
| P14-5 | 0 support dans le cheminement de 1,40 m ; ≥ 2,20 m au-dessus | 0 | RF-MA-TRO-001 ; RF-MA-TRO-008 |
| P14-6 | flèches d'affectation ⇒ C24a/C24b ou Da30 | 100 % | RF-MQ-DIR-01 |
| P14-7 | feux : R11 à droite de chaque couloir, au droit ou à l'aval de la ligne d'effet ; bas ≥ 2,00 m ; axe < 4,20 m | 100 % | RF-FEU.POSITION_LIGNE_EFFET ; RF-FEU.HAUTEUR.TROTTOIR |
| P14-8 | séquences le long des itinéraires (AB6 ↔ AB7, B14 répété, EB10/EB20) | 0 incohérence | CC-13 |

**Ce qui garantit la continuité.**

- Les séquences de signalisation sont calculées par itinéraire, à l'échelle du réseau, et non par segment.
- Un même support porte les ensembles de feux et de panneaux d'un couloir (RF-FEU.JUXTAPOSITION ; RI GEN-05).

**État du code (lecture seule, 17/10/2026).**

- Existe : signaux décrits (C20a…) portés par le modèle ; régimes inférés d'OSM.
- Manque : toute l'implantation (lot L6).

### E15 — Éclairage

*Phase C ; étape 13 de la proposition de départ ; lot de migration : N8.*

**But.** Implanter les candélabres en rangées régulières, à recul constant, sur trottoir, terre-plein ou îlot, avec la crosse vers la chaussée, en évitant les supports déjà posés.

**Entrées.**

- surfaces et bordures (E08, E11)
- retenue et supports (E13, E14)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/points/eclairage.json` | `pj_points/0.1` (mât, crosse, lanterne, hauteur de feu) |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::eclairage::1.0` | à créer | — | rangées par chaîne de bordure |

**Contraintes normatives.**

- Base fusionnée : RF-OBS-ECL-01, RF-MA-TRO-001.
- Specs du dépôt : RI ECL-01, RI ECL-02, RI ECL-03, RI ECL-04, RI ECL-05, LOC-ECL (regles_locales_meylan.json).
- DocRoute : 13 § 2.9 (candélabres de 8 à 11 m observés).
- Lacune : aucune norme d'éclairage (NF EN 13201) dans DocRoute (L-04).

**Bibliothèques (meshes, matériaux, gabarits).**

- manquent : candélabres (ASSETS_ROUTE § 9)

**Contrôles bloquants (porte P15).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P15-1 | intervalle dans une rangée | 3 à 5 fois la hauteur de feu | RI ECL-04 |
| P15-2 | nu du fût à ≥ 0,50 m de la bordure, hors cheminement | 100 % | RI ECL-01 |
| P15-3 | distance aux arbres (vérifiée en E17) | ≥ 2 m (plus selon la couronne) | RI ECL-05 |

**Ce qui garantit la continuité.**

- Une rangée suit une chaîne de bordure à travers les routes, avec le même recul (RI ECL-03).

**État du code (lecture seule, 17/10/2026).**

- Existe : règles RI ECL-01 à ECL-05.
- Manque : pose et assets.

### E16 — Mobilier urbain : potelets, barrières, arceaux, abris, bancs

*Phase C ; étape 12 (partie mobilier) de la proposition de départ ; lot de migration : N8.*

**But.** Poser le mobilier dans la place qui reste : potelets et barrières de ville, arceaux vélos, abris de quai, bancs, corbeilles, bornes et armoires. Chaque objet respecte l'abaque de détection, le cheminement libre, les reculs et les supports déjà posés (E13 à E15).

**Entrées.**

- surfaces et bordures (E08, E10, E11)
- retenue, supports et candélabres (E13 à E15)
- passages, abaissés et BEV (E04, E11)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/points/mobilier.json` | `pj_points/0.1` (files de potelets ou de barrières le long d'une chaîne ; objets ponctuels) |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::mobilier::1.0` | à créer | — | files le long des chaînes de bordure ; objets ponctuels par règles RI |

**Contraintes normatives.**

- Base fusionnée : RF-MA-OBS-001, RF-MA-OBS-002, RF-MA-OBS-005, RF-MA-OBS-006, RF-MA-SEP-014, RF-MA-SVE-001, RF-MA-SVE-004, RF-MA-BUS-007, RF-MA-TRO-011, RF-SV-J11_J12, RF-SV-J13 ; DEF-032.
- Specs du dépôt : RI GEN-01, RI GEN-03, RI GEN-08, RI POT-01, RI POT-02, RI POT-04, RI BAR-01, RI MOB-01, RI MOB-04, RI RES-01, mobilier.json (autre équipe, lecture seule).
- DocRoute : 11P § 2 ; 11T § 1.

**Bibliothèques (meshes, matériaux, gabarits).**

- potelets (5) et barrières (3) de `catalogue_assets_route.json`
- `mobilier.json` : 23 modèles
- `assets/catalogue_besoins.json` : 122 noms d'assets relevés à Paquet Jardin
- manquent : arceaux, bornes, balises J11/J13 (ASSETS_ROUTE § 9)

**Contrôles bloquants (porte P16).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P16-1 | aucun objet sur une surface circulée | 0 | RI GEN-01 |
| P16-2 | recul du nu ≥ 0,30 m derrière l'arête de bordure (objet > 0,30 m) | 100 % | RI GEN-03 |
| P16-3 | abaque de détection (hauteur et largeur) ; contraste | 100 % | RF-MA-OBS-001 ; RF-MA-OBS-002 |
| P16-4 | cheminement de 1,40 m libre | 100 % | RF-MA-TRO-001 |
| P16-5 | potelets et barrières hors des rampes et des BEV des traversées | 0 | RI POT-04 |

**Ce qui garantit la continuité.**

- Les files de potelets et de barrières suivent les chaînes de bordure à travers les routes ; leur entraxe (1,20 à 1,60 m, RI POT-02) est phasé sur la chaîne.

**État du code (lecture seule, 17/10/2026).**

- Existe : assets potelets et barrières ; règles d'implantation RI du dépôt.
- Manque : toute la pose.

### E17 — Végétation (étape ultérieure)

*Phase C ; étape 14 de la proposition de départ ; lot de migration : après N8.*

**But.** Planter les arbres d'alignement, les massifs et les îlots de giratoire, et semer les zones vertes pour le PCG. Les plantations respectent les triangles de visibilité, les passages, les abaissés, le cheminement et la couronne de giratoire. Décision de l'utilisateur du 17/10/2026 : la végétation vient dans un deuxième temps.

**Entrées.**

- toutes les surfaces et tous les objets posés (E08 à E16)
- objets_le_long du modèle

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/points/vegetation.json` | `rg_vegetation/0.2` puis `pj_points/0.1` ; zones/*.json pour PG_Herbe |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `rg::vegetation_bati::1.0` | à créer | — | prévue au plan (lot L8) |
| `rg::vers_entites (sortie 2)` | existe | `recon/generateur/hda/rg_vers_entites` | arbres des objets_le_long, exportés pour l'étape 2 |

**Contraintes normatives.**

- Base fusionnée : RF-GV-TPC-010, RF-GV-TPC-011, RF-GV-VIS-001, RF-OSM-VEG-001, RF-OBS-VEG-01, RF-OBS-VEG-02, RF-GV-GIR-006, RF-OBS-GIR-04 ; DEF-029, DEF-030 ; ARB-10, ARB-13.
- Specs du dépôt : RI VEG-05, RI GEN-08, vegetation.json (autre équipe, lecture seule).
- DocRoute : 10T § 4 ; 06 (triangles de visibilité).

**Bibliothèques (meshes, matériaux, gabarits).**

- `vegetation.json` : 35 essences
- `assets/lib` (CC0)

**Contrôles bloquants (porte P17).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P17-1 | 0 arbre dans les triangles de visibilité, passages, abaissés, cheminement, pistes | 0 | DEF-029 ; DEF-030 |
| P17-2 | couronne de 2 m sans masque autour de l'îlot central | 100 % | RF-GV-GIR-006 |
| P17-3 | distance arbre ↔ candélabre | RI ECL-05 | RI ECL-05 |

**Ce qui garantit la continuité.**

- Les alignements suivent la chaîne du trottoir ou du terre-plein. Le pas (7,5 m, DEF-030) est phasé sur la chaîne et non remis à zéro à chaque route.

**État du code (lecture seule, 17/10/2026).**

- Existe : arbres des objets_le_long exportés (l2/vegetation.json, `rg_vegetation/0.2`), rendu de l'étape 2 désactivé (`--decor-etape2`).
- Manque : pose réseau, exclusions, zones PCG.

### E18 — Exports : USD et PCG d'Unreal, OpenDRIVE, graphe de voies

*Phase D ; étape 15 de la proposition de départ ; lot de migration : N10.*

**But.** Livrer le chantier. Les maillages partent en USD par tuile et par couche, les instances en `pj_points/0.1` pour les graphes PCG d'Unreal. On produit aussi l'OpenDRIVE (1.4 restreint pour CARLA, 1.8.1 complet) et le graphe de voies pour ZoneGraph et le routage piétons et vélos.

**Entrées.**

- toutes les couches (E07 à E17)
- modèle complet (E01 à E04)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/export/usd/` | une couche par famille (PJ_Sol, PJ_Bordures, PJ_Marquages, PJ_Ouvrages, PJ_Signalisation…), Z haut, materiau_id remappé en MI_<id> |
| `recon/out/generateur/meylan/<reseau>/export/points/*.json` | pj_points/0.1 → PCGDataAsset → Static Mesh Spawner (TQ-PCG-001) |
| `recon/out/generateur/meylan/<reseau>/export/opendrive/reseau_1_4.xodr, reseau_1_8_1.xodr` | PLAN_GENERATEUR L7 |
| `recon/out/generateur/meylan/<reseau>/export/graphe_voies.json` | 12M § 7 (≤ 32 tags, zones spline et polygone) |
| `recon/out/generateur/meylan/<reseau>/manifest_reseau.json` | empreintes sha256 de chaque sortie, versions des HDA, description |

**HDA et outils.**

| HDA | Statut | Où | Note |
|---|---|---|---|
| `pj::preparer_export, pj::exporter_points` | existe (recon/pcg) | `recon/pcg/houdini/hda` | contrat E1 à E9 |
| `rg::exporter_opendrive::1.0` | à créer | — | lot L7 |
| `rg::exporter_graphe::1.0` | à créer | — | lot L4 |

- `recon/pcg/ue/contrat/verifier_usd.py`
- `recon/pcg/ue/pj_tools` (charger_points)
- graphes PCG existants : PG_Bordures, PG_Symboles, PG_Arbres, PG_Massifs, PG_Herbe (ARCHITECTURE § 1.5) ; à ajouter : PG_Retenue, PG_Signalisation, PG_Eclairage, PG_Mobilier, PG_Assainissement, PG_Decalques

**Contraintes normatives.**

- Base fusionnée : RF-OSM-CAR-060, RF-OSM-CAR-061.
- Specs du dépôt : TQ-PCG-001, TQ-PCG-003, TQ-PCG-004, TQ-PCG-005, TQ-SOL-010, TQ-BOR-001.
- DocRoute : 12A § 6 et § 7 ; 12M § 7 et § 8.

**Bibliothèques (meshes, matériaux, gabarits).**

- `DT_Bibliotheque` (assets/bibliotheque.json prévu par ARCHITECTURE § 1.5)

**Contrôles bloquants (porte P18).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P18-1 | USD | 0 erreur à verifier_usd.py | 12A § 9 |
| P18-2 | OpenDRIVE 1.4 se charge dans CARLA, 1.8.1 sans erreur au validateur ; waypoints continus | saut ≤ 0,1 m | PLAN_GENERATEUR L7 ; CC-09 |
| P18-3 | graphe de voies : chaque voie entrante a ≥ 1 successeur ; ≤ 32 tags | 100 % | CC-09 |
| P18-4 | déterminisme : deux fabrications identiques à l'octet | 100 % | README_HDA § 9.2 |

**Ce qui garantit la continuité.**

- Une zone spline par section et une zone polygone par carrefour et par changement de profil (12M § 7) : les formes ZoneGraph se raccordent.

**État du code (lecture seule, 17/10/2026).**

- Existe : route_l2.usda et route_l2b.usda par scène ; contrat pj_points/0.1 ; outillage UE de recon/pcg/ue.
- Manque : OpenDRIVE, graphe de voies, export par tuile et par chantier, import UE des sorties du générateur ; CARLA non installé.

### E19 — Contrôles globaux et revue visuelle

*Phase D ; étape 16 de la proposition de départ ; lot de migration : N11.*

**But.** Rejouer les contrôles de continuité CC-01 à CC-13 sur le réseau entier. Comparer ensuite le rendu aux photos Panoramax, à pose égale et en tuiles natives, puis passer la revue indépendante.

**Entrées.**

- toutes les sorties
- photos Panoramax recalées par points d'appui (`recon/pcg/enrichir/poses.py`, `calage_sequence.py`)

**Sorties (contrat de données).**

| Fichier | Contrat |
|---|---|
| `recon/out/generateur/meylan/<reseau>/controle/rapport_reseau.json` | CC-01 à CC-13, portes P00 à P18, écarts au réel |
| `recon/out/generateur/meylan/<site>/photos_non_versionnees/planches/` | planches rendu \| photo (jamais versionnées) |
| `recon/generateur/validation/comparaison_<reseau>.json` | constats sans photo (critère, constat, tuile, règle, identifiant) |

**HDA et outils.**

- `recon/pcg/vision/decoupe.py`
- `recon/pcg/enrichir/poses.py` (acceptation si ≤ 0,5° en 360° ou ≤ 8 px à plat)
- `rendu/planches_photo.py`

**Contraintes normatives.**

- Base fusionnée : —.
- DocRoute : PLAN_GENERATEUR § 5 et § 6.3 ; recon/pcg/ARCHITECTURE.md § 1.7.

**Contrôles bloquants (porte P19).**

| Id | Contrôle | Seuil | Règle |
|---|---|---|---|
| P19-1 | contrôles de continuité CC-01 à CC-13 | 0 échec | § 4 de ce document |
| P19-2 | reprojection des arêtes sur les photos recalées | ≤ 8 px à plat | ARCHITECTURE § 1.7 |
| P19-3 | revue indépendante (rendus et photos en ordre aléatoire) | moyenne ≥ 2, aucun 0 | PLAN_GENERATEUR § 5.2 |
| P19-4 | conclusions seulement sur des tuiles natives ≤ 1092 px | 100 % | CLAUDE.md |

**Ce qui garantit la continuité.**

- Les vues de contrôle sont choisies aussi aux raccords (joints, coins, changements de tuile) et pas seulement au milieu des segments.

**État du code (lecture seule, 17/10/2026).**

- Existe : contrôles par lot (controler_L1, L2, L2b), rendus en tuiles, planches rendu | photo.
- Manque : contrôles de réseau ; vues de raccord.


## 4. Contrôles de continuité

Ces treize contrôles sont la définition opérationnelle de « pas de bouts de segments sans continuité ». Chacun est
évalué à la porte indiquée, puis rejoué sur tout le réseau en E19. Un écart admis (`ecarts_admis`) ne peut pas lever un
contrôle de continuité (P6).

| Id | Objet | Contrôle | Seuil | Porte |
|---|---|---|---|---|
| CC-01 | topologie | chaque extrémité de route est un nœud partagé ; `limite_carte` seulement au bord du chantier | 100 % | P01 |
| CC-02 | plan | itinéraires continus en position et en cap aux nœuds et aux raccords | ≤ 1 mm ; ≤ 0,5° | P02 |
| CC-03 | altimétrie | même z de chaussée de part et d'autre de chaque joint ; pente continue | \|Δz\| ≤ 1 mm | P02, P06 |
| CC-04 | profil au joint | chaque limite a le même t des deux côtés d'un joint (route ↔ carrefour, route ↔ route) | ≤ 1 mm | P03, P04 |
| CC-05 | plan-masse | 0 trou, 0 recouvrement ; somme des aires = emprise | ≤ 1e-6 relatif | P05 |
| CC-06 | bordures | chaînes sans lacune ; fin seulement sur point dur déclaré ; coins en pièces courbes | lacune ≤ 1 mm (joint posé 3,5 à 9,5 mm) | P05, P08 |
| CC-07 | sol | maillage 2-variété sur tout le chantier ; arêtes de tuiles identiques ; Z continu ; masques sans couture | 0 défaut | P06, P10 |
| CC-08 | marquage | phase continue le long de l'itinéraire ; u constant ; 0 trait tronqué < ½ trait au joint | 0 | P12 |
| CC-09 | graphe de voies | chaque voie entrante a un successeur ; voies continues | saut ≤ 0,1 m | P18 |
| CC-10 | réseau piéton | trottoirs, passages et refuges forment un graphe connexe ; cheminement de 1,40 m continu | 100 % | P11 |
| CC-11 | réseau cyclable | itinéraires cyclables continus ; interruptions déclarées (RF-MA-BAN-008) | 0 interruption non déclarée | P11, P12 |
| CC-12 | hydraulique | chaque point bas a un exutoire ; chaque bassin de surface a un avaloir | 0 point bas orphelin | P06, P09 |
| CC-13 | signalisation | séquences cohérentes le long des itinéraires (AB6 ↔ AB7, B14 répété hors agglomération, EB10 ↔ EB20) | 0 incohérence | P14 |

## 5. État du code, étape par étape

Lecture seule du 17/10/2026 (`recon/generateur`, lots L0, L1, L2 et L2b terminés). Les numéros de ligne citent les
fichiers à cette date.

| Étape | Existe | Manque | Lot |
|---|---|---|---|
| E00 Description du réseau (texte libre et photos → YAML réseau) | format d'un tronçon isolé (`description/FORMAT_DESCRIPTION.md`) et son compilateur (`description_vers_modele.py`, 2 418 lignes à la lecture)<br>compilateur de réseau de l'étape 2 en cours d'écriture : `description/carrefours.py`, format `description_simple/0.2` (troncons[] à id, carrefours, giratoires, bretelles ; scènes `scenes_carrefours/J1` à `J3`)<br>descriptions de sites de Meylan en cours dans les lots voisins (`recon/generateur/meylan/<site>/` : description.yaml, mesures.json, photos.json, et `extensions_auto` pour ce que le format ne dit pas encore)<br>12 exemples, catalogue S01 à S12, trois rues de Meylan décrites d'après photo (M20, M24, M27)<br>inférence OSM → modèle avec nœuds partagés et carrefours topologiques | couche réseau (proposée : FORMAT_DESCRIPTION_RESEAU.md) : nœuds ancrés, valeurs approchées, accrochage à OSM, itinéraires, ouvrages, échangeurs<br>résolveur (lot N1) | N1 |
| E01 Graphe topologique | inférence OSM : nœuds partagés et carrefours (osm_vers_modele.py l. 585-613 ; `carrefour_plan` l. 766 ; `carrefour_giratoire` l. 928)<br>rg::graphe : branches et valence | description : chaque tronçon isolé reçoit deux nœuds `limite_carte` (description_vers_modele.py l. 2221-2222) ; l'étape 2 crée désormais les nœuds des carrefours décrits (`description/carrefours.py`), mais pas encore les nœuds de connexion ni les ancrages<br>itinéraires, mouvements voie à voie, fusion des carrefours complexes<br>lecture des carrefours dans Houdini (lot de l'étape 2) | N1, N3 |
| E02 Tracé en plan et profil en long | droites, arcs et clothoïdes dans la description et dans rg::graphe<br>dévers en toit ou à pente unique (DEF-006, commun/profil.py l. 632-684) | ajustement de géométries régulières sur OSM (README_RG § 8 : décalés en onglet, replis aux sommets)<br>profil en long : jamais lu ; chaussée ancrée à Z = 0 (README_RG § 5)<br>dévers en courbe (RF-GV-DEV-002) et gauchissement le long des clothoïdes<br>règles de tracé des voies rapides urbaines (ICTAVRU, VSA 90/110) absentes de la base | N2 |
| E03 Profils en travers et transitions le long des arcs | rg::profils et commun/profil.py (lots L0 à L2b) | contrôle de continuité d'une route à la suivante (aujourd'hui seulement d'une section à l'autre dans une route)<br>profils d'autoroute et de bretelle (BAU, BDG, séparateur GBA) : lot de l'étape 2 | N1 (contrôle inter-routes), étape 2 (profils d'autoroute) |
| E04 Conception des carrefours, giratoires et échangeurs | contrat de données (schéma : carrefour, branche, frontiere_segment, trajectoire, conflit, ilot, anneau)<br>compilateur de réseau de l'étape 2 en cours, scènes J1 (T en cédez), J2 (croix à STOP), J3 (croix à feux) | fin de l'étape 2 (hors de ce lot) : giratoires et autoroutes encore vides le 17/10/2026 (`scenes_giratoires/`, `scenes_autoroutes/`)<br>échangeurs : aucune règle de géométrie de bretelle dans la base (lacune L-01) | étape 2 (solveur) ; N4 consomme ses sorties |
| E05 Plan-masse unique (épure 2D du réseau) | partition en (s, t) d'une seule route (rg::nivellement, rg::sol) ; zones sous les bordures | arrangement plan à l'échelle du réseau (tout est à créer) | N4 |
| E06 Nivellement unique et hydraulique de surface | modèle de Z unique sur une route (README_RG § 5), HeightField 0,10 m, abaissés, ralentisseurs, grilles au droit des plateaux | Z réel (profil en long, MNT) : la chaussée est à Z = 0 en t = 0<br>aires de carrefour (TQ-SOL-014), points bas, exutoires, pentes du fil d'eau<br>HeightField à l'échelle du réseau (régions numérotées 100 × rang de route + nappe) | N5 |
| E07 Terrassements, plate-forme et ouvrages d'art | contrat `ouvrage` au schéma (type, routes_portees, franchit, gabarit, tablier, appuis, joints) | toute la fabrication ; le rendu de l'étape 1 pose la route sur un socle plat neutre (decor_l2b.py l. 820-861) | N9 |
| E08 Bordures et caniveaux en chaînes continues | pose en éléments, pièces d'angle, chartières, retours transversaux, grilles d'avaloir (lots L2, L2b, corrections) | chaînes à l'échelle du réseau : aujourd'hui une file par route et par côté, coupée aux bouts de route<br>coins de carrefour (solveur de l'étape 2)<br>types de bordures étendus (étape 2) | N6 |
| E09 Assainissement : avaloirs, grilles, regards, tampons | grilles au pied des rampes et en bout de file (rg::vers_entites, corrections du 17/10/2026) | points bas, pas réglementaire, regards et tampons | N6 |
| E10 Chaussée (bitume) : revêtement, reprises, joints | rg::sol (étanche sur une route, lignes de rupture, BEV) ; rendu Karma avec cartes d'usure | triangulation du réseau<br>cartes d'usure lues en (s, t) de la route avec un décalage propre à la scène (rendu_l2b.py l. 963, README_RG § 6) : couture à chaque changement de route | N5 |
| E11 Trottoirs, pistes, terre-pleins et îlots (revêtements) | trottoirs, pistes, bandes plantées, zones hachurées, îlot refuge bordé dans une même nappe par route ; BEV | rg::terre_pleins (genres)<br>joints sciés des bétons<br>réseau piéton et cyclable à l'échelle du réseau | N5, N6 |
| E12 Marquages : longitudinaux, puis transversaux, puis flèches et symboles | rg::marquages : lignes, passages, zébras, flèches, triangles, figurines de la section courante, drapés par pj::marquage_solide | phase par itinéraire : aujourd'hui « chaque tronçon commence par un trait » [G] (README_RG § 6)<br>transversales et symboles de carrefour (lots L3 et L4)<br>marquages d'autoroute (u 7,5 cm, T4, T2 5u) : étape 2 | N7 |
| E13 Dispositifs de retenue : glissières, séparateurs béton, BN4, garde-corps | garde-corps et barrières en assets ; règles BN01, GC02 et GC97 versées dans la base | toute la pose ; assets de glissières et de séparateurs | N8 |
| E14 Signalisation verticale et feux | signaux décrits (C20a…) portés par le modèle ; régimes inférés d'OSM | toute l'implantation (lot L6) | N8 |
| E15 Éclairage | règles RI ECL-01 à ECL-05 | pose et assets | N8 |
| E16 Mobilier urbain : potelets, barrières, arceaux, abris, bancs | assets potelets et barrières ; règles d'implantation RI du dépôt | toute la pose | N8 |
| E17 Végétation (étape ultérieure) | arbres des objets_le_long exportés (l2/vegetation.json, `rg_vegetation/0.2`), rendu de l'étape 2 désactivé (`--decor-etape2`) | pose réseau, exclusions, zones PCG | après N8 |
| E18 Exports : USD et PCG d'Unreal, OpenDRIVE, graphe de voies | route_l2.usda et route_l2b.usda par scène ; contrat pj_points/0.1 ; outillage UE de recon/pcg/ue | OpenDRIVE, graphe de voies, export par tuile et par chantier, import UE des sorties du générateur ; CARLA non installé | N10 |
| E19 Contrôles globaux et revue visuelle | contrôles par lot (controler_L1, L2, L2b), rendus en tuiles, planches rendu \| photo | contrôles de réseau ; vues de raccord | N11 |

## 6. Ruptures de continuité actuelles

| Id | Rupture | Preuve | Étape qui la supprime | Lot |
|---|---|---|---|---|
| R-01 | Chaque tronçon décrit seul reçoit ses deux nœuds `limite_carte` : il n'y a ni nœud partagé ni carrefour. L'étape 2 corrige en ce moment le cas des carrefours décrits (`description/carrefours.py`) ; restent les nœuds de connexion, les ancrages et les itinéraires. | description/description_vers_modele.py l. 2221-2222 | E00, E01 | N1 |
| R-02 | Les carrefours du modèle ne sont pas lus par Houdini. | hda/rg_lire_modele/lecteur.py l. 30-32 (NON_LUS_L1), l. 313 | E01 | étape 2, N3 |
| R-03 | Aucune altitude de réseau : chaque route est ancrée à Z = 0 en t = 0 et `profil_long` n'est jamais lu. | hda/commun/vex/rg_niveau.h l. 5 et l. 128 ; README_RG § 5 | E02, E06 | N2, N5 |
| R-04 | Une triangulation et un HeightField par route : nappes numérotées 100 × rang de route + nappe. | README_RG § 5 ; hda/rg_nivellement/construire.py l. 777-815 ; hda/rg_sol/construire.py l. 1-9 | E05, E06, E10 | N4, N5 |
| R-05 | Bordures et caniveaux en files par route et par côté, avec retour transversal aux bouts et sans coin de carrefour. | README_RG § 5 (files, retours) et § 8 (pas de carrefour) | E05, E08 | N4, N6 |
| R-06 | La phase des tirets est remise à zéro à chaque tronçon : « chaque tronçon commence par un trait » [G]. | README_RG § 6 ; hda/rg_marquages/marquages.vfl l. 435 | E12 | N7 |
| R-07 | Les cartes d'usure sont lues en (s, t) de la route avec un décalage propre à la scène : il y a une couture de texture à chaque changement de route. | rendu/rendu_l2b.py l. 963 (`st_route`) ; README_RG § 6 | E10 | N5 |
| R-08 | Au rendu, la route repose sur un socle à coupe nette en s = 0 et s = L, sur un sol plat neutre (choix de l'étape 1). | rendu/decor_l2b.py l. 820-861 ; README_RG § 6 | E07 | N9 |
| R-09 | Routes OSM sans géométrie régulière : décalés en onglet et replis aux sommets. Les chaussées séparées et les îlots d'OSM découpent l'avenue de Verdun en dizaines de ways à sens unique entre (−305 ; −314) et (646 ; 641) en local, soit autant de micro-routes. | README_RG § 3 et § 8 ; data/vector_gz/osm/roads.geojson.gz (ways 63600584, 1275266695, 1412130583 à 1412130610…) | E01, E02 | N1, N2 |
| R-10 | Précision : Houdini stocke les positions en flottants 32 bits. Le pas de quantification vaut 0,12 mm entre 1 et 2 km de l'origine O, 0,24 mm de 2 à 4 km et 0,49 mm de 4 à 8 km. Or l'extrait BD TOPO de Meylan mesure ≈ 6,7 × 8 km et le contrôle de flèche est à 0,5 mm. | README_RG § 1 (résolution ≤ 1,5e-5 m sous 256 m) ; emprise de data/vector_gz/bdtopo/troncon_de_route.geojson.gz | toutes | N4 (origine locale par chantier, P8) |

Ces ruptures ne sont pas des erreurs de l'étape 1. Elles découlent de son périmètre : une route seule, « pas de
carrefour : les routes d'un réseau se chevauchent aux nœuds », comme le dit README_RG § 8. Elles deviennent bloquantes
dès qu'on assemble un réseau.

## 7. Plan de migration par lots

### 7.1 Lots

| Lot | Contenu | Livrables | Touche l'étape 2 | Dépend de | Critère de fin |
|---|---|---|---|---|---|
| N0 | Chaîne et format réseau (ce lot) | CHAINE_CONSTRUCTION.md<br>chaine_construction.json<br>FORMAT_DESCRIPTION_RESEAU.md | non | — | identifiants cités tous présents dans la base (vérifié) |
| N1 | Compilateur réseau et graphe (E00, E01, contrôle inter-routes de E03) | recon/generateur/reseau/resoudre_reseau.py (description réseau → description exacte de l'étape 2)<br>recon/generateur/reseau/tests/<br>schéma modele_voie/0.2 proposé (copie nouvelle, la 0.1 reste)<br>recon/generateur/meylan/<reseau>/description_reseau.yaml | non | N0, compilateur de réseau de l'étape 2 | une description au format de l'étape 2 ressort du résolveur identique à l'octet ; S01-S12, J1-J3, exemples et M20/M24/M27 : empreintes sha256 des modèles inchangées ; porte P01 sur 2 réseaux de Meylan |
| N2 | Tracé en plan et profil en long (E02) | recon/generateur/reseau/trace.py (ajustement droites, arcs, clothoïdes)<br>recon/generateur/reseau/profil_long.py (MNT, déclivités, raccordements)<br>règles ICTAVRU / VSA 90/110 proposées au propriétaire de regles_route_fr.json | non | N1 | porte P02 ; écart à l'axe ortho ≤ 0,30 m sur le corridor de l'avenue de Verdun |
| N3 | Lecture des carrefours dans Houdini (E01) | adoption de la version de rg::lire_modele produite par l'étape 2 | oui (réutilisation) | étape 2 terminée | aucun développement propre : réutiliser, ne pas refaire |
| N4 | Plan-masse (E05) et chantiers (P8) | hda/rg_plan_masse/ (rg::plan_masse::1.0)<br>validation/controler_plan_masse.py | non | N1, étape 2 (compilateur de réseau) | porte P05 sur un carrefour à feux et un giratoire de Meylan |
| N5 | Nivellement réseau et sol (E06, E10, E11) | rg::nivellement::2.0<br>rg::sol::2.0<br>rg::aspect_chaussee::1.0 | non | N2, N4 | portes P06, P10 ; CC-03, CC-07, CC-12 ; les versions 1.0 restent intactes et servent toujours S01-S12 |
| N6 | Bordures en chaînes et assainissement (E08, E09) | rg::vers_entites::2.0<br>rg::assainissement::1.0 | non | N4, N5 | portes P08, P09 ; CC-06 |
| N7 | Marquages réseau (E12) | rg::marquages::2.0 (itinéraires, transversales, symboles de carrefour) | non | N5, étape 2 (lignes d'arrêt) | porte P12 ; CC-08 |
| N8 | Retenue, signalisation, éclairage, mobilier (E13 à E16) | rg::retenue::1.0<br>rg::signalisation::1.0<br>rg::eclairage::1.0<br>rg::mobilier::1.0<br>assets manquants (glissières, mât Ø 114, potence, candélabres, arceaux) | non | N7 | portes P13 à P16 ; CC-13 |
| N9 | Terrain et ouvrages (E07) | rg::terrain::1.0<br>rg::ouvrages::1.0<br>dalles LiDAR HD du chantier | non | N2, N5 | porte P07 (échangeur A41 / N87 et Hélice de Meylan) |
| N10 | Exports et Unreal (E18) | rg::exporter_opendrive<br>rg::exporter_graphe<br>export USD par tuile<br>graphes PCG PG_Retenue, PG_Signalisation, PG_Eclairage, PG_Mobilier, PG_Assainissement, PG_Decalques | non | N5 à N9 | porte P18 |
| N11 | Premiers chantiers de Meylan (E19) | corridor de l'avenue de Verdun (≈ 920 m à vol d'oiseau, carrefours M13 et M17)<br>échangeur A41 / N87 (Rocade Sud) et Hélice de Meylan<br>comparaisons Panoramax | non | N10 | porte P19 |

Ordre conseillé : N1 et N2 peuvent démarrer tout de suite, car ce sont des scripts Python dans de nouveaux dossiers.
N4 démarre quand le solveur de l'étape 2 livre ses premières frontières. N5 et N6 suivent, puis N7, N8 et N9, et enfin
N10 et N11. Les premiers chantiers de Meylan (N11) sont choisis pour couvrir les trois cas demandés :

- **le corridor de l'avenue de Verdun**, d'Aiguinards (site M13, carrefour à feux) au chemin des Buclos (site M17 :
  passage piéton à feux avec refuge, entre deux débouchés en baïonnette en cédez-le-passage, relevé
  `meylan/verdun_centre_feux`), en passant par la suite d'îlots refuges et d'îlots peints du site M27. Il
  fait environ 920 m à vol d'oiseau, avec une avenue, des carrefours à feux, des refuges et une traversée cyclable
  verte (pratique locale photographiée, donc admise : 00_SYNTHESE § 0.1) ;
- **le bout d'autoroute** : A41 (OSM : 2 voies par sens sur l'essentiel du tronçon, 3 ou 4 au droit des insertions,
  110 km/h ; ways 4020688, 4017853, 4017854…), N87 Rocade Sud
  (2 voies, 90 km/h, terre-plein à double séparateur béton de 2,6 m ± 0,5 m, site M26), et la bretelle dite
  « Hélice de Meylan » (ways 112621089, 361790056, 361790055, 857526255, 235030396). Celle-ci débouche sur le carrefour
  à feux du chemin du Vieux Chêne (site M07) ;
- **un giratoire** de Meylan déjà observé (Rond-Point de Didcot, site M03, Ø 47 m, couronne pavée rouge et galets),
  pour l'anneau, la couronne et les îlots séparateurs.

### 7.2 Coexistence avec l'étape 2

Fichiers de l'étape 2, à ne pas modifier pendant qu'elle tourne : `recon/generateur/{hda, description, schema, rendu,
vehicules, scenes_*}` et `recon/generateur/fabriquer_*.py`.

- Aucun fichier existant de l'étape 2 n'est modifié pendant qu'elle tourne. Le travail réseau va dans de nouveaux
  dossiers et dans de nouvelles HDA ou versions (`rg::*::2.0` installées à côté de la 1.0, comme `pj::bordure::2.0` à
  côté de la 1.0). Le résolveur va dans `recon/generateur/reseau/` ; les descriptions réseau vont dans
  `recon/generateur/meylan/<reseau>/`, selon la convention des descriptions de sites des lots voisins.
- Le compilateur de réseau de l'étape 2 (`description/carrefours.py`, format `description_simple/0.2`) est réutilisé
  tel quel. Le résolveur écrit une description à son format puis l'appelle (FORMAT_DESCRIPTION_RESEAU § 9). Les clés
  qui manquent à l'étape 2 (traversée cyclable photographiée, supports de feux, divergence entre deux bretelles,
  retenue, talus) lui sont proposées au lieu d'être recodées à côté.
- Le résolveur importe le vocabulaire et la lecture des profils de la description (`description/vocabulaire.py`,
  `description/format_profil.py`) sans les modifier. Une description déjà au format de l'étape 2 le traverse sans
  changer d'un octet.
- Non-régression : empreintes sha256 des modèles compilés, avant et après chaque lot, par la même méthode que
  `tmp/scenes/empreintes.py` de l'étape 2 ; idem pour les USD de S01-S12, J1-J3 et M20/M24/M27.
- Le solveur de carrefours, les types de bordures, les giratoires, les autoroutes et les véhicules appartiennent à
  l'étape 2. La chaîne réseau consomme leurs sorties (E04) sans les réécrire.
- Les sorties du réseau vont dans `recon/out/generateur/meylan/<reseau>/`, sans collision avec
  `recon/out/generateur/<scene>/`.

## 8. Bibliothèques et PCG d'Unreal : ce que chaque couche apporte

Le PCG d'Unreal ne reçoit pas des segments mais des couches de chantier. Ce sont des maillages USD par tuile de 50 m et
des points `pj_points/0.1`, que lisent les graphes PCG (TQ-PCG-001 : points JSON, puis `pj_tools.charger_points`, puis
PCGDataAsset et Static Mesh Spawner). La richesse demandée vient du nombre de couches et de la bibliothèque derrière
chacune :

| Couche | Étape | Sortie | Graphe PCG ou import | Bibliothèque |
|---|---|---|---|---|
| Terrain, talus, ouvrages | E07 | USD | import USD | béton PBR `route_fr` |
| Bordures et caniveaux | E08 | points | PG_Bordures (MeshSelectorByAttribute) | 64 bordures et 12 caniveaux paramétriques, 33 profils Alkern ; granit, béton, calcaire |
| Joints (herbe, mousse) | E08, E10 | zones | PG_Joints | `assets/lib` (CC0) |
| Avaloirs, grilles, tampons | E09 | points | PG_Assainissement (à créer) | décalque de grille ; avaloirs et regards en volume à créer |
| Chaussée | E10 | USD (tuiles) + points de décalques | import USD (Nanite, MI_<materiau_id>) ; PG_Decalques (à créer) | 34 matériaux `materiaux_sol.json` (enrobés ancien, neuf, reprise, clair, ocre…), 27 PBR `route_fr` ; pontages, rapiéçages |
| Trottoirs, pistes, îlots | E11 | USD + zones | import USD ; PG_Ilots | dalles et BEV (5), pavés (4), remplissages d'îlots (BRF, gravier, galets, gazon) |
| Marquages : lignes | E12 | USD (peinture drapée) | import USD | `peinture_<couleur>_u<usure>` ; usure de 0 à 0,85 |
| Marquages : symboles | E12 | points | PG_Symboles | 42 gabarits et 72 glyphes du dossier 08 (flèches, figurines, triangles, PMR, lettres) |
| Dispositifs de retenue | E13 | points | PG_Retenue (à créer) | garde-corps (4), barrières (3) ; glissières, BN4, GBA, DBA à créer |
| Signalisation et feux | E14 | points | PG_Signalisation (à créer) | 870 faces de panneaux (licence non levée : PNG non diffusés), 15 supports, 8 feux ; mât Ø 114 et potence à créer |
| Éclairage | E15 | points | PG_Eclairage (à créer) | candélabres à créer (8 à 11 m observés, RF-OBS-ECL-01) |
| Mobilier urbain | E16 | points | PG_Mobilier (à créer) | potelets (5), `mobilier.json` (23 modèles), 122 noms d'assets relevés (`assets/catalogue_besoins.json`) ; arceaux, bornes à créer |
| Végétation | E17 | points + zones | PG_Arbres, PG_Massifs, PG_Herbe | 35 essences (`vegetation.json`) |

Les graphes PG_Bordures, PG_Symboles, PG_Arbres, PG_Massifs, PG_Herbe, PG_Joints et PG_Ilots sont décrits dans
`recon/pcg/ARCHITECTURE.md` § 1.5. Les six graphes « à créer » sont des propositions de ce document.

## 9. Lacunes

| Id | Sujet | État | Proposition |
|---|---|---|---|
| L-01 | géométrie des autoroutes et des échangeurs | ICTAAL absente de DocRoute. ICTAVRU (2009), VSA 90/110 (2014) et VSA Voies auxiliaires (2020) sont présents dans `10_…/sources/` mais n'ont pas été versés dans la base, sauf deux règles ICTAVRU (RF-GV-PT-008, RF-GV-TPC-002). La base ne couvre de l'autoroute que le marquage et la signalisation (RF-MQ-INS-*, RF-MQ-DEC-*, RF-MQ-SC-06, RF-MQ-SC-13, RF-SV-J14…). | Verser dans `regles_route_fr.json` les valeurs relues le 17/10/2026 et citées en E02, E03 et E04. C'est le travail du propriétaire de la base : ce lot n'y écrit pas. |
| L-02 | profil en long en ville | Aucune règle de déclivité ni de raccordement pour les rues. Seuls existent le palier avant carrefour (RF-GV-CAR-005), la pente du site d'un giratoire (RF-GV-GIR-022) et la pente du cheminement (RF-MA-TRO-003). | Sans règle, prendre le MNT tel quel (provenance `mesure:mnt`) et vérifier les pentes du cheminement et du fil d'eau. |
| L-03 | assainissement | Les règles GA-ASS-* et GA-CHA-003/004 existent dans `assets/specs/regles_conception.json` (relevé du site), pas dans la base fusionnée ; DocRoute n'a pas de volet assainissement. | Reprendre ces règles telles quelles (provenance `depot:GA-ASS-*`) ; les proposer à la fusion. |
| L-04 | éclairage | Seules existent les règles RI ECL-* du dépôt et une observation (RF-OBS-ECL-01). Aucune norme lue (NF EN 13201). | Pose par règles RI, hauteurs observées ; marquer [G]. |
| L-05 | dispositifs de retenue | Le guide Cerema des dispositifs de retenue (`Cerema_Guide_Dispositifs_Retenue_Routiers.pdf`) et le guide Setra CSEE121 (séparateurs modulaires) sont dans `10_…/sources/` sans avoir été exploités. La base ne tire de la retenue que quatre règles : RF-GV-TPC-003, RF-GV-TPC-004 et RF-GV-TPC-008 (BN01, TPC) et RF-GV-PON-010 (GC02, bord d'ouvrage). Aucune ne fixe l'implantation d'une glissière le long d'une route. | Volet à ouvrir avant le lot N8. |
| L-06 | couches de chaussée, joints de reprise, rapiéçages | Pas de règle : les seules données sont des observations (RF-OBS-REV-01). | Aspect seulement, choix [G] déclarés ; jamais de géométrie inventée. |
| L-07 | assets manquants | Mât de feux Ø 114, potence, R12m, R14 à R25, écran de contraste, glissières et BN4, candélabres, arceaux, bornes, balises J11/J13, avaloirs et regards en volume (ASSETS_ROUTE § 9 ; 00_SYNTHESE § 15). S'y ajoutent, hors du dossier 14 : GBA, DBA, corniches, portiques. | Les fabriquer avec les HDA `route::*` du dossier 14 avant les lots N8 et N9. |
| L-08 | terrain | LiDAR HD local : 4 dalles de 1 km² autour de Paquet Jardin (0916-0917 × 6460-6461). L'échangeur A41 / N87 (≈ 918,4 km ; 6459,9 km) est en dehors. | Télécharger les dalles LiDAR HD (IGN, Licence Ouverte) des chantiers, sur D:. |
| L-09 | schéma | `modele_voie/0.1` n'a ni itinéraires, ni profil en long régulier (seulement des points [s, z]), ni plage pour une valeur approchée, ni ancrage d'un nœud sur OSM autre que `osm_node`. | Proposer `modele_voie/0.2` dans une nouvelle copie de schéma (FORMAT_DESCRIPTION_RESEAU § 9) ; la 0.1 reste valide. |
| L-10 | OSM d'avant travaux | L'extrait OSM local (`data/vector_gz/osm`) est l'état actuel. L'état « avant travaux » de Paquet Jardin a ses propres extraits (`data/sites/paquet_jardin/avant_travaux/osm_*`). | La description réseau porte sa date d'état ; l'ancrage OSM cite l'extrait utilisé. |

## 10. Fichiers de ce lot et vérifications

- `recon/generateur/CHAINE_CONSTRUCTION.md` (ce document) et `recon/generateur/chaine_construction.json` (même donnée,
  schéma `chaine_construction/0.1` : principes, phases, étapes, contrôles de continuité, ruptures, lots, lacunes,
  règles de coexistence avec l'étape 2).
- `recon/generateur/FORMAT_DESCRIPTION_RESEAU.md` : format de description d'un réseau, sous forme d'une couche
  au-dessus du format de réseau de l'étape 2 (`description_simple/0.2`). Le résolveur sera écrit au lot N1.
- Vérifications faites le 17/10/2026 :
  - chaque identifiant RF-, DEF- ou ARB- cité dans les deux documents et dans le JSON existe dans
    `regles_route_fr.json` (outil `recon/generateur/outils/verifier_citations_md.py`, plus un contrôle du JSON) ;
  - chaque identifiant TQ-, GA- ou RI cité existe dans `assets/specs/regles_conception.json` ou
    `regles_implantation.json` ;
  - chaque fichier du dépôt cité comme existant existe ;
  - les valeurs « à verser » ont été relues dans les PDF de `D:\DocRoute\10_…\sources\` (ICTAVRU 2009 ; Cerema, VSA
    90/110, 2014) par extraction de la couche texte, pages imprimées.
- Aucune image n'a été regardée pour ce lot. Les identifiants de photos et les constats cités viennent du dossier 13
  (`observations.json`). Les positions et les ways cités viennent des extraits OSM et BD TOPO du dépôt.
