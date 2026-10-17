# Format de description d'un réseau (`description_reseau/0.1`), proposé pour l'étape 3

*`recon/generateur/FORMAT_DESCRIPTION_RESEAU.md`, 17/10/2026. Proposition du lot « chaîne de construction » (étape E00
de `CHAINE_CONSTRUCTION.md`). Le résolveur `recon/generateur/reseau/resoudre_reseau.py` sera écrit au lot N1.*

Ce format décrit un morceau de Meylan : plusieurs tronçons reliés par des nœuds partagés, des carrefours, des
giratoires, des bretelles et des ouvrages. Les coordonnées sont réelles (Lambert-93) ou relatives, accrochées à OSM
quand c'est utile. Les valeurs peuvent être approchées (« environ 20 m », « à peu près au milieu »).

**Il ne crée pas un format de plus. C'est une couche au-dessus du format de l'étape 2.** Le lot « scenes » de l'étape 2
écrit en ce moment le compilateur de réseau `description/carrefours.py`, appelé par `description_vers_modele.py`. Son
format est `description_simple/0.2` : des `troncons[]` portant chacun un `id`, avec des coordonnées exactes, et des
`carrefours[]`, `giratoires[]` et `bretelles[]` (exemples dans `scenes_carrefours/J1` à `J3`). La couche réseau
ajoute ce qui manque pour décrire Meylan d'après photo :

- des **nœuds** nommés et ancrés (L93, OSM, site du dossier 13, position relative) ;
- des **valeurs approchées** avec leur plage ;
- l'**accrochage à OSM** (tracé, profil, chaînes) ;
- les **itinéraires**, les **ouvrages** et les **échangeurs** ;
- l'**état décrit**, les **sources** et les **preuves**.

Le résolveur (lot N1) transforme une description réseau en description exacte au format de l'étape 2. Le compilateur
de l'étape 2 en fait ensuite le modèle (§ 9). Les clés de l'étape 2 citées ici ont été lues dans `carrefours.py`
(`CLES_CARREFOUR`, `CLES_BRANCHE`, `CLES_GIRATOIRE`, `CLES_BRANCHE_GIR`, `CLES_BRETELLE`) le 17/10/2026. Elles sont à
recaler quand l'étape 2 sera close.

## 0. Principe

Trois règles :

1. **Ce qui est dit est repris**, avec sa plage s'il est approché et sa preuve (photo, ortho, OSM). Ce qui n'est pas
   dit vient de la règle de `assets/specs/route/regles_route_fr.json` qui le fixe, et cette règle est citée.
2. **Une valeur approchée est une contrainte, pas une invention.** « Environ 20 m » veut dire « entre 18 et 22 m ».
   Le résolveur choisit dans cette plage : d'abord une mesure, sinon une règle, sinon le centre (§ 4.3). Il garde la
   plage et la raison de son choix dans la provenance.
3. **Les nœuds sont partagés.** Deux tronçons qui se touchent citent le même nœud. Un carrefour est un objet décrit
   (type, régime, branches), jamais la fin d'un tronçon. C'est la condition de la continuité (CHAINE_CONSTRUCTION P3).

Chaque tronçon accepte toute la grammaire du tronçon simple (`description/FORMAT_DESCRIPTION.md` § 3 à § 12 bis) :
profil en travers, matériaux, marquages, évènements, végétation, objets, abords, signalisation, écarts admis. Un mot ou
une clé inconnus sont des erreurs. Une valeur non dite qu'aucune règle ne fixe arrête la compilation.

**Photos.** Seuls les identifiants Panoramax, les noms de tuiles et les constats entrent dans un fichier versionné. Les
photos et leurs tuiles natives (≤ 1092 px, `recon/pcg/vision/decoupe.py`) restent dans
`recon/out/generateur/meylan/<site>/photos_non_versionnees/`.

**Où ranger les fichiers.** On suit la convention des descriptions de sites déjà en cours d'écriture dans
`recon/generateur/meylan/<site>/` : `description.yaml`, `mesures.json`, `photos.json`. Une description réseau va dans
`recon/generateur/meylan/<reseau>/description_reseau.yaml`, à côté de ses `mesures.json` et `photos.json`.

## 1. L'exemple le plus court

« Route à 2 voies à double sens, avec un terre-plein entre les deux sens, végétalisé sur environ 20 m » :

```yaml
format: description_reseau/0.1
reseau: exemple_terre_plein_20m
contexte: {agglomeration: oui, vitesse: 50}
noeuds:
  A: {position: [0, 0]}
  B: {position: [150, 0]}
troncons:
  - id: R1
    de: A
    vers: B
    profil: "trottoir | voie ← | voie → | trottoir"
    evenements:
      - "sur environ 20 m au milieu : terre-plein planté"
```

Ce que le résolveur et le compilateur en tirent (le détail le long de la chaîne est au § 2.3 de
`CHAINE_CONSTRUCTION.md`) :

| Valeur | Plage | Retenu | Raison |
|---|---|---|---|
| longueur du terre-plein planté | [18 ; 22] m (« environ » sur une longueur : ± 10 %, § 4.2) | 20 m | aucune règle ne fixe cette longueur : centre de la plage |
| position | « au milieu » : centre à 0,5 L ± 0,1 L = [60 ; 90] m | centre à 75 m, soit [65 ; 85] m | centre ; avertissement « position approchée » |
| largeur du terre-plein | non dite | 2,00 m | RF-OSM-LAR-050 (confiance faible) |
| emprise | non dite | la plate-forme s'élargit de 2 m ; les bandes extérieures se déportent de 1 m de chaque côté | défaut du format (§ 6.3), avertissement |
| voies, trottoirs, bordures | non dites | 3,00 m ; 2,00 m ; T2 vue 0,14 ; I2 vue 0,11 autour du terre-plein | RF-OSM-LAR-010 ; DEF-004 ; DEF-005 |
| raccord des voies au nez | non dit | déport de 1 m sur L/2 = 19,5 m avant chaque nez | oblique de tête d'îlot symétrique (RF-MQ-OBL-05), plus douce que le déport de 1/15 de RF-GV-CAR-010 |
| nœuds A et B | sans carrefour décrit | `limite_carte` | bord de la description |

## 2. Clés du fichier

| Clé | Contenu | Format de l'étape 2 | Obligatoire |
|---|---|---|---|
| `format` | `description_reseau/0.1` | remplacé par `description_simple/0.2` à la résolution | oui |
| `reseau` | nom court ; sorties dans `recon/out/generateur/meylan/<reseau>/` | devient `scene` | oui |
| `titre`, `description` | titre et phrase libre | repris | non |
| `etat` | `{nom, date}` : état décrit (« avant_travaux », 2024-08-24) ; les photos citées doivent être valables à cette date | couche réseau (va dans `date` et `meta`) | oui dès qu'une photo est citée |
| `confiance` | `haute`, `moyenne` (défaut), `faible` : confiance des valeurs dites sans plage | repris | non |
| `repere`, `origine` | § 3.1 | `origine` reprise | non (défaut : `local`, origine O du dépôt) |
| `contexte` | contexte commun (agglomération, vitesse, catégorie, u…), comme `FORMAT_DESCRIPTION.md` § 3 ; chaque tronçon peut le surcharger | repris | oui |
| `sources` | extraits et photos utilisés (§ 8.2) | couche réseau | non |
| `noeuds` | § 5 | couche réseau (résolus en coordonnées) | oui |
| `troncons` | § 6 ; liste, chaque tronçon avec son `id` | repris, `de`/`vers` résolus en coordonnées | oui |
| `carrefours`, `giratoires`, `bretelles` | § 7.1 à § 7.3 | repris (clés de l'étape 2), `noeud` résolu en `centre` | non |
| `echangeurs`, `ouvrages`, `itineraires` | § 7.4, § 7.5, § 8.1 | couche réseau | non |
| `ecarts_admis` | comme `FORMAT_DESCRIPTION.md` § 12 bis ; aussi par tronçon | repris | non |
| `attendus` | ce qui doit apparaître (recopié dans le rapport) | repris | non |

Les clés s'écrivent avec ou sans accents ni majuscules, comme dans le format du tronçon.

## 3. Repères et ancrages

### 3.1 Coordonnées

| `repere` | Sens des coordonnées | Note |
|---|---|---|
| `local` (défaut) | mètres depuis `origine` (défaut O du dépôt : 917 279,43 ; 6 460 289,98 ; 216,30 L93) | comme le format du tronçon |
| `l93` | Lambert-93 (EPSG:2154) | converti en local une seule fois, par le résolveur |
| `relatif` | aucune coordonnée absolue : tout est placé par distances et caps depuis un nœud de départ | exemples synthétiques |

Les caps suivent la convention OpenDRIVE : 0° = est, 90° = nord, sens trigonométrique.

### 3.2 Ancrer un nœud

| Écrire | Effet | Tolérance de l'ancrage [G] |
|---|---|---|
| `position: [x, y]` ou `[x, y, z]` | position dans le repère | celle de la valeur (exacte, ou plage si `≈`) |
| `osm: node/123` | nœud OSM de l'extrait cité dans `sources.osm` | 0 (géométrie OSM) |
| `osm_pres_de: 10` (avec `position` ou `site`) | recalage sur le nœud OSM routier le plus proche à moins de 10 m | 10 m (erreur au-delà) |
| `site: M17` | position du site dans `D:\DocRoute\13_…\sites.json` | ± 15 m (les sites sont des points de requête) |
| `photo: <identifiant>` | position de la prise de vue Panoramax (sans pose recalée) | ± 5 m |
| `sur: R1` + `a: …` | point de l'axe d'un tronçon, à une abscisse (§ 4) ; il coupe le tronçon en deux tronçons qui partagent ce nœud | celle de l'abscisse |
| `depuis: A` + `distance: ≈ 80` + `cap: ≈ 45` | position relative | celles de la distance et du cap |
| `intersection: [R1, R2]` | croisement des axes de deux tronçons | 0 |

Un nœud sans ancrage est une erreur. Deux ancrages contradictoires sont aussi une erreur : écart supérieur à la
somme de leurs tolérances. Un nœud ne peut pas être ancré par `sur` sur un tronçon dont il est une extrémité.

### 3.3 Ancrer un tronçon

| Écrire | Effet |
|---|---|
| `osm: auto` (défaut si le tronçon a un `nom` et des nœuds placés sur OSM) | le résolveur prend les ways OSM de même nom qui relient les deux nœuds, dans les deux sens pour des chaussées séparées, et en écrit la liste dans `compilation_reseau.json`. Un nœud non ancré sur OSM (relatif, site) est projeté sur le way de même nom le plus proche, à moins de sa tolérance |
| `osm: [way/1, way/2]` | ways dans l'ordre, de `de` vers `vers` (un way à l'envers est retourné) ; une chaîne incomplète (trou entre deux ways) est une erreur |
| `osm: {aller: [...], retour: [...]}` | chaussées séparées d'OSM fusionnées en un seul tronçon (RF-OSM-PRF-011). Seuil : 30 m entre chaussées. Au-delà, ou si le terre-plein est large et variable, décrire deux tronçons `jumele_avec` (§ 6.1) |
| `bdtopo: [cleabs…]` | tronçons BD TOPO (contrôle de la largeur, du nombre de voies et de la position au sol ; RF-OSM-BDT-001) |
| `trace: osm` (défaut si `osm` est donné) | axe tiré d'OSM puis régularisé en droites, arcs et clothoïdes (étape E02), écrit en `trace:` exact pour l'étape 2 ; écart ≤ `tolerance_trace`, défaut 1,50 m [G] |
| `trace: droite`, `trace: {…}` | tracé explicite, même grammaire que `FORMAT_DESCRIPTION.md` § 4 |
| `trace: "courbe à gauche R ≈ 150"` | tracé qualitatif, rayon approché, raccordé aux nœuds |
| `z: mnt` (défaut), `z: [[s, z], …]`, `z: plat` | altitude : MNT ou LiDAR, mesure, ou plat (déclaré) |

Un way qui passe par un nœud de la description est coupé à ce nœud. Un nœud OSM de valence ≥ 3 traversé par un
tronçon sans nœud décrit donne un avertissement : un carrefour existe peut-être là sans être décrit.

## 4. Valeurs approchées

### 4.1 Comment les écrire

| Écrire | Plage |
|---|---|
| `20`, `20 m`, `20,0` | exacte (plage nulle), confiance de la description |
| `≈ 20`, `~20`, `environ 20`, `à peu près 20`, `vers 20` | plage par défaut de la grandeur (§ 4.2) |
| `20 ± 3` | [17 ; 23] |
| `15 à 25`, `entre 15 et 25` | [15 ; 25] |
| `au moins 20`, `≥ 20` | [20 ; borne haute de la règle de la grandeur, sinon 2 × 20] [G] |
| `au plus 20`, `≤ 20` | [borne basse de la règle, sinon 0 ; 20] |

Restent toujours exacts : le **nombre de voies**, le **sens**, la **vitesse réglementaire**, le **régime** d'un
carrefour, les **mouvements** et les **codes de panneau**. « Environ 2 voies » ou « vitesse ≈ 50 » sont refusés. Un
régime incertain s'écrit `regime: a_verifier` : rien n'est alors peint ni posé (RF-OSM-CAR-012, ARB-19).

### 4.2 Plages par défaut d'« environ X » [G]

Les incertitudes de départ sont celles du dossier 13 : photo ± 0,2 à 1 m, ortho ± 0,3 m (00_SYNTHESE § 16). Les plages
ci-dessous sont des choix du format, à réviser au lot N1 sur les premiers réseaux.

| Grandeur | Plage d'« environ X » |
|---|---|
| longueur le long d'un tronçon (≥ 10 m) | ± 10 %, au moins ± 1 m |
| abscisse d'un évènement depuis un nœud | ± 10 % de la distance, au moins ± 2 m |
| largeur de bande vue sur photo (`preuve: photo:`) | ± 0,50 m |
| largeur mesurée sur l'ortho 20 cm (`preuve: ortho…`) | ± 0,30 m |
| rayon (coin, bretelle) | ± 20 % |
| diamètre extérieur ou largeur d'anneau de giratoire | ± 10 % |
| vue de bordure | ± 0,04 m |
| cap, angle | ± 10° |
| hauteur de support ou de panneau | ± 0,20 m (ARB-04 : contrôle à ± 0,20 m pour une valeur [G] tirée de photos) |

### 4.3 Comment le résolveur choisit

Pour chaque valeur approchée, dans cet ordre :

1. **Mesure dans la plage.** Une mesure disponible et comprise dans la plage est retenue : largeur OSM `width:lanes`,
   largeur BD TOPO, cote PCRS ou GAM, mesure sur l'ortho (`mesures.json` du site). Provenance `mesure:<source>`.
2. **Règle dans la plage.** Une règle RF ou DEF dont la valeur tombe dans la plage est retenue, avec la provenance
   « règle dans la plage dite ». Par exemple, « trottoir ≈ 2 » retient 2,00 m (DEF-004).
3. **Centre de la plage.** Sinon le centre, avec la provenance `description:approx`.
4. **Contraintes entre valeurs.** Plusieurs valeurs peuvent être liées : somme des largeurs égale à une largeur de
   chaussée mesurée, évènements sans chevauchement, ordre des abscisses, évènement contenu dans son tronçon, giratoire
   dont l'anneau vaut au moins 1,2 fois l'entrée la plus large (RF-GV-GIR-004). Le résolveur les ajuste alors à
   l'intérieur de leurs plages, en déplaçant d'abord les valeurs les moins sûres : centre, puis règle, puis mesure ;
   une valeur exacte ne bouge jamais. Si c'est impossible, il s'arrête en citant les valeurs en conflit.
5. **Conformité.** Si toute la plage est hors d'une plage réglementaire, la valeur est « non conforme ». La
   fabrication est alors bloquée sauf écart admis (`FORMAT_DESCRIPTION.md` § 12 bis). Une plage qui chevauche la plage
   réglementaire est ramenée dans l'intersection, avec un avertissement.

Le choix est déterministe : même fichier, même choix. Chaque valeur porte
`prov = {src, regle, conf, plage: [min, max], choix: mesure | regle | centre | contrainte}` : c'est l'extension
`plage` et `choix` proposée au schéma 0.2 (§ 9). Confiance : `faible` pour une plage tirée d'une photo, `moyenne` pour
une plage mesurée sur l'ortho.

### 4.4 Positions dites en mots

| Écrire (dans un évènement ou `a:`) | Abscisse s sur le tronçon, de `de` (s = 0) à `vers` (s = L) |
|---|---|
| `au début`, `au départ` | [0 ; 0,15 L] |
| `au milieu`, `à peu près au milieu` | 0,5 L ± 0,1 L |
| `à la fin`, `au bout` | [0,85 L ; L] |
| `à 30 de N1`, `à ≈ 30 après N1` | 30 m depuis N1 (exact, ou plage par défaut) |
| `à 30 avant N2` | L − 30 |
| `juste avant N2`, `juste avant le carrefour` | 5 à 20 m [G] avant la **frontière** du carrefour (résolu après E04, § 6.4) |
| `juste après N1` | 5 à 20 m [G] après la frontière |
| `au droit de N3`, `en face de <objet>` | projection orthogonale sur l'axe |
| `sur toute la longueur` | [0 ; L] |
| `sur environ 20 m au milieu` | longueur [18 ; 22], centrée sur 0,5 L ± 0,1 L |
| `de 40 à 60`, `de ≈ 40 à ≈ 60` | intervalle, chaque borne avec sa plage |

## 5. Nœuds

```yaml
noeuds:
  N_SOURCES: {position: [917483.4, 6460499.0], repere: l93, osm_pres_de: 10}
  N_BUCLOS:  {site: M17, osm_pres_de: 15}
  N_ALLEE:   {sur: R_VERDUN_2, a: ≈ 120}      # point de l'axe (débouché d'une allée) : coupe R_VERDUN_2 en deux tronçons
  N_X:       {depuis: N_BUCLOS, distance: ≈ 80, cap: ≈ 45}
```

| Clé | Contenu |
|---|---|
| ancrage | une des formes du § 3.2 (obligatoire) |
| `repere` | surcharge le repère global pour ce nœud |
| `type` | déduit de la valence (RF-OSM-CAR-001) ; à dire seulement pour `limite_carte` (bord de la description), `impasse` ou `fourche` (musoir) |
| `z` | altitude dite ; sinon le MNT, et le z est commun à tous les tronçons du nœud (CHAINE P02-3) |
| `preuves` | `[photo:<id>, ortho:<millésime>, osm:<id>]` |

Un nœud de valence ≥ 3 sans carrefour décrit reçoit un carrefour de régime `a_verifier` (rien de peint, RF-OSM-CAR-012),
sauf si l'ancrage OSM porte un régime lisible (`traffic_signals`, `give_way`, `stop` + `traffic_sign=FR:AB4`). Un
`highway=stop` seul donne « stop à vérifier » (ARB-19).

## 6. Tronçons

### 6.1 Clés propres au réseau

```yaml
troncons:
  - id: R_VERDUN_2
    de: N_SOURCES                  # nom de nœud (couche réseau) ou [x, y] (étape 2)
    vers: N_BUCLOS
    itineraire: I_VERDUN
    osm: auto                      # ways « Avenue de Verdun » des deux chaussées entre les deux nœuds
    profil: "trottoir ≈ 2 | bande plantée ≈ 4 | voie ≈ 3,25 ← | zone hachurée ≈ 2,8 | voie ≈ 3,25 → | bande plantée ≈ 4 | trottoir ≈ 2"
    evenements:
      - "à ≈ 20 de N_SOURCES : passage piéton"
```

| Clé | Contenu |
|---|---|
| `id` | identifiant (obligatoire, comme à l'étape 2) |
| `de`, `vers` | nœuds de la couche réseau, ou coordonnées comme à l'étape 2 ; le tronçon est orienté de `de` vers `vers` (sens de s, gauche et droite du profil). L'étape 2 accepte qu'un tronçon commence ou finisse au centre d'un carrefour (`carrefours.py`, tolérance 0,05 m) |
| `nom`, `ref` | nom de voie, numéro (A41, N87, RD1090) ; le nom est hérité de l'itinéraire s'il n'est pas dit |
| `itineraire` | identifiant d'itinéraire (§ 8.1) |
| `categorie`, `vitesse`, `agglomeration`… | surcharges du contexte (`FORMAT_DESCRIPTION.md` § 3) ; `categorie: autoroute \| bretelle \| anneau_giratoire…` (énumération du schéma) |
| `osm`, `bdtopo`, `trace`, `tolerance_trace`, `z` | § 3.3 |
| `longueur` | contrôle seulement (« ≈ 280 ») : la longueur vient du tracé |
| `jumele_avec` | tronçon de l'autre chaussée d'une route à chaussées séparées décrite en deux tronçons (RF-OSM-PRF-011) |
| `profil`, `materiaux`, `marquages`, `evenements`, `objets`, `vegetation`, `abords`, `signalisation`, `ecarts_admis` | grammaire du tronçon (`FORMAT_DESCRIPTION.md` § 5 à § 12 bis). Les largeurs peuvent être approchées (`voie ≈ 3,25`, `accotement herbe 3 à 5`) |
| `profil: osm` | profil inféré des tags des ways (`inference/osm_vers_modele.py`, règles RF-OSM-*) puis écrit en profil exact ; provenance `inference:` ; une section par way si les tags changent. C'est le défaut d'un tronçon ancré sur OSM dont le profil n'est pas dit, avec l'avertissement « profil non relevé » |
| `preuves` | preuves du tronçon entier |

### 6.2 Profil et sens

Le profil se lit de gauche à droite **dans le sens du tronçon** (de `de` vers `vers`). La ligne de référence est la
séparation des sens d'une route à double sens, ou le milieu de la chaussée d'une route à sens unique (RF-OSM-PRF-010),
comme dans le format du tronçon. Un tronçon d'autoroute ou de bretelle à sens unique a toutes ses voies `→`.

### 6.3 Ce qui naît en cours de tronçon

Une bande qui apparaît sur une partie du tronçon s'écrit en évènement, sans réécrire tout le profil : terre-plein,
îlot refuge, voie de tourne-à-gauche, bande cyclable, stationnement. Exemple : `"de ≈ 40 à ≈ 60 : terre-plein planté"`.
Le résolveur la traduit en évènements `profil` exacts de `FORMAT_DESCRIPTION.md` § 8.

- `largeur` : dite, sinon la règle de la bande.
- `pris_sur` : où la bande prend sa place.
  - `plate_forme` (défaut) : la plate-forme s'élargit et les bandes extérieures se déportent. Avertissement « emprise
    non dite ».
  - `trottoirs` : les trottoirs perdent la largeur, sous le contrôle du cheminement de 1,40 m (RF-MA-TRO-001).
  - `voies` : les voies se resserrent, sous le contrôle des largeurs minimales (RF-GV-PT-001).
- Les transitions suivent les règles de la bande (tête d'îlot, déport, biseau ; `FORMAT_DESCRIPTION.md` § 8).
  Elles sont ajoutées hors de l'intervalle dit, avec un avertissement si elles débordent du tronçon.
- `îlot refuge` (terre-plein bordé qui sert de refuge) et `terre-plein` **remplacent** sur l'intervalle une bande de
  séparation déjà présente au même endroit (zone hachurée, terre-plein d'un autre genre), à la même largeur si aucune
  largeur n'est dite. S'il n'y a rien à remplacer, la bande est insérée sur la ligne de référence et `pris_sur`
  s'applique. Exemple : `"de ≈ 15 à ≈ 25 : îlot refuge bordure basse vue ≈ 0,11 enrobé"`, dans une zone hachurée.

### 6.4 Positions relatives aux carrefours

« Juste avant le carrefour », « à la ligne d'arrêt » ou « 3 m avant le passage » dépendent de la frontière et des lignes
d'arrêt calculées à la compilation du réseau (étape 2, E04). Le résolveur les écrit en ancrage symbolique
`{carrefour, branche, depuis: frontiere | ligne_arret | passage, distance}`, résolu après la première passe du
compilateur de réseau. C'est l'extension `ancrage` proposée au schéma 0.2 (§ 9). Tant qu'elle n'existe pas, ces
positions sont refusées avec un message qui demande une abscisse depuis un nœud.

## 7. Carrefours, giratoires, bretelles, échangeurs, ouvrages

### 7.1 Carrefour plan ou à feux (clés de l'étape 2)

```yaml
carrefours:
  - id: C_X                         # carrefour d'illustration (exemple réel : § 10.2)
    noeud: N_X                      # couche réseau ; résolu en « centre: [x, y] » (clé de l'étape 2)
    regime: feux                    # sinon par branche
    branches:
      - {troncon: R_A, passage: oui, ligne_effet: oui, fleches: oui}   # flèches : voies affectées du profil d'approche
      - {troncon: R_B, passage: oui, coin: ≈ 8}
      - {troncon: R_C, passage: oui}
      - {troncon: R_D, regime: cedez}       # une branche peut avoir son propre régime
    feux:
      phases:
        - {nom: P1, mouvements: [R_A TD, R_A TAG, R_B TD], pietons: [R_C], vert: 25}
        - {nom: P2, mouvements: [R_C TD, R_D TD], pietons: [R_A, R_B], vert: 20}
    preuves: [photo:<identifiant>]
```

Clés de l'étape 2, à reprendre telles quelles :

- carrefour : `id`, `nom`, `centre`, `type`, `regime`, `branches`, `ilots`, `feux`, `guidage`, `vehicule`, `note`,
  `commentaire` ;
- branche : `troncon`, `regime`, `passage`, `sas`, `ligne_effet`, `coin`, `fleches`, `mouvements`, `ilot`, `triangle`,
  `note`, `commentaire` ;
- phase de feux : `nom`, `mouvements`, `vert`, `pietons`.

L'affectation des voies se dit dans le profil d'approche du tronçon (bandes `tourne-à-gauche`, évènement
`elargissement`), comme au format du tronçon ; `fleches` et `mouvements` la complètent.

La couche réseau ajoute :

- `noeud` à la place de `centre` ;
- des valeurs approchées pour les grandeurs (`coin: ≈ 8`) ;
- `preuves`.

Ce que l'étape 2 ne porte pas encore est **à lui proposer**. D'ici là, le résolveur le refuse, avec la liste des clés
non portées :

- style de traversée cyclable photographié (`traversee_cyclable: {style: resine_verte, preuves}`) ;
- supports de feux observés (`feux.supports`) ;
- balises et panneaux d'un carrefour avec hauteur observée (`signalisation`).

| Grandeur | Si non dite |
|---|---|
| régime d'une branche | celui du carrefour ; sinon `a_verifier` (rien de peint, RF-OSM-CAR-012) |
| passage, refuge | non ; refuge imposé si traversée > 12 m (RF-GV-PIE-010) |
| ligne d'effet, sas | ligne d'effet non peinte (DEF-015, ARB-01) ; sas non |
| coin | DEF-010 (ARB-09) |
| phases de feux | DEF-028 (2 phases, cycle 50 à 70 s) |
| guidage | jamais (ARB-08 : seulement décrit ou observé) |

### 7.2 Giratoire (clés de l'étape 2)

```yaml
giratoires:
  - id: G_DIDCOT                    # Rond-Point de Didcot, site M03 du dossier 13
    noeud: N_DIDCOT                 # résolu en « centre »
    diametre: 47 ± 2                # diamètre extérieur (Ø), pas le rayon Rg ; mesuré sur l'ortho (constat M03)
    anneau: 8,5 ± 1,2               # ortho (constat M03)
    couronne: {materiau: pavés rouges et galets}     # largeur non relevée : règle ou observation (RF-OBS-GIR-03)
    ilot_central: butte plantée (couvre-sol, arbustes, arbres)
    branches:
      - {troncon: R_NORD, passage: oui, ilot: peint}
      - {troncon: R_SUD, passage: oui, ilot: goutte d'eau}
    preuves: [photo:0f41f230-3eb8-455c-8c92-d1f80ed19046, ortho:ign2024]
```

Clés de l'étape 2 :

- giratoire : `id`, `nom`, `centre`, `diametre`, `rayon`, `anneau`, `couronne`, `ilot_central`, `branches`, `type`,
  `trottoir`, `passages`, `bordure_exterieure` ;
- branche : `troncon`, `ilot`, `passage`, `entree`, `sortie`.

Les règles contrôlent et complètent : anneau uniforme ≥ 1,2 fois l'entrée la plus large, de 6 à 9 m (RF-GV-GIR-004) ;
îlot central et couronne de 1,50 à 2 m, couronne de 2 m sans masque (RF-GV-GIR-006) ; déflexion < 100 m
(RF-GV-GIR-008) ; îlots séparateurs du tableau 2 de l'ACI (RF-GV-GIR-013) ; passages à 2 à 5 m de la ligne cédez
(RF-GV-GIR-015) ; AB25, ligne cédez sur chaque entrée, B21-1 face aux entrées (RF-GV-GIR-024). Les valeurs observées
en Isère (RF-OBS-GIR-01 à -04) ne servent que si rien n'est dit.

### 7.3 Bretelle (clés de l'étape 2)

Une bretelle relie un tronçon `bretelle` à un tronçon de chaussée principale par un musoir (convergence ou
divergence). Clés de l'étape 2 : `id`, `nom`, `type`, `principale`, `bretelle`, `voie`, `point`, `biseau`, `longueur`,
`musoir`, `obliquite`. La couche réseau permet d'écrire `point` comme un nœud `type: fourche`, et de donner `biseau`,
`longueur` et `obliquite` en valeurs approchées. Sinon, ces grandeurs viennent des règles de voie rapide citées en E04
de `CHAINE_CONSTRUCTION.md` : ICTAVRU et VSA 90/110, à verser dans la base (lacune L-01). Le marquage vient de
RF-MQ-INS-01 à -03, RF-MQ-DEC-01 à -03 et RF-MQ-LAR-B2d.

### 7.4 Échangeur (couche réseau)

Un échangeur **regroupe** des objets décrits ailleurs (chaussées, bretelles, musoirs). Il ne porte que ce qui vaut pour
l'ensemble :

```yaml
echangeurs:
  E_ROCADE_SUD:                     # exemple complet au § 10.3
    type: noeud                     # noeud (entre voies rapides) | diffuseur (voie rapide ↔ voirie locale), nomenclature ICTAVRU p. 89
    chaussees: [R_A41_O1, R_A41_O2]
    bretelles: [BR_A41]
    u: 7,5 cm                       # RF-MQ-U-01 (autoroutes et chaussées séparées)
```

### 7.5 Ouvrages et équipements de la plate-forme (couche réseau)

```yaml
ouvrages:
  O_2:
    type: pont                      # pont | passage_superieur | passerelle | tremie | mur | buse
    porte: [B_N87_DIV]
    franchit: [R_A41_O2]            # axes OSM croisés vers (918 473 ; 6 459 983) : à confirmer sur l'ortho
    osm: [way/28341977]             # bridge=yes, layer=1 ; layer n'est pas une altitude (RF-OSM-OUV-001)
                                    # gabarit non dit : 4,75 m sous une autoroute (RF-GV-PON-012)
```

Sous l'ouvrage, la hauteur libre est contrôlée : gabarit plus 0,10 m (RF-GV-PON-012). Le profil en long du tronçon
porté en découle (étape E02).

Les descriptions de sites d'autoroute en cours d'écriture portent dans `extensions_auto` ce que le format ne sait pas
encore dire. Exemple : `recon/generateur/meylan/auto_a41_section_courante/description.yaml`, avec ses besoins B1 à
B12 listés dans `BESOINS_FORMAT_AUTO.md` (fichier annoncé, pas encore écrit le 17/10/2026). La couche réseau les
reprend ainsi :

| Besoin du site (`extensions_auto`) | Clé de la couche réseau | Étape de la chaîne |
|---|---|---|
| `chaussees_separees` | `osm: {aller, retour}` ou `jumele_avec` (§ 3.3, § 6.1) | E01, E03 |
| `dispositifs_retenue` (limite, type, hauteur, décalage, de, a, contournement de pile) | `retenue:` sur le tronçon, liste de mêmes champs | E13 |
| `ouvrages` (passage supérieur, biais, tablier, appuis, garde-corps) | `ouvrages` (§ 7.5), mêmes champs | E07 |
| `equipements` (clôtures, lignes aériennes, éclairage) | `equipements:` sur le tronçon | E15, E16 |
| `talus` (côté, sens, hauteur, pente, végétation) | `abords` du tronçon, complété de `talus: {hauteur, pente}` | E07 |
| `marquages_detail` (ligne, modulation, de, a, motif) | évènements `profil` ou surcharge de ligne (`FORMAT_DESCRIPTION.md` § 5.2) | E12 |
| `etapes` (ordre de construction du site) | aucune : l'ordre est celui de la chaîne ; une différence locale se signale en `note` | — |

## 8. Itinéraires, sources, preuves

### 8.1 Itinéraires

```yaml
itineraires:
  I_VERDUN: {nom: avenue de Verdun, troncons: [R_VERDUN_1, R_VERDUN_2, R_VERDUN_3], prioritaire: oui}
```

Un itinéraire porte d'un tronçon à l'autre :

- la phase des marquages, qui n'est pas remise à zéro à chaque tronçon (CHAINE_CONSTRUCTION CC-08) ;
- l'unité u, constante sur l'itinéraire (RF-MQ-U-05) ;
- la priorité : la ligne de la route prioritaire n'est pas interrompue au droit d'une route secondaire (RF-MQ-CAR-01) ;
- les séquences de signalisation (AB6 / AB7, B14).

Sans `itineraires`, le résolveur regroupe les tronçons de même `nom` qui se suivent à travers un nœud, avec un
avertissement.

### 8.2 Sources et preuves

```yaml
etat: {nom: printemps_2025, date: 2025-05-18}
sources:
  osm: {extrait: data/vector_gz/osm/roads.geojson.gz, note: état 2026, à recouper avec l'état décrit}
  bdtopo: {extrait: data/vector_gz/bdtopo/troncon_de_route.geojson.gz}
  ortho: {couche: ORTHOIMAGERY.ORTHOPHOTOS, millesime: 2024, pas: 0.20}
  photos: photos.json               # fichier du site (identifiants, dates, tuiles regardées, constats)
  mesures: mesures.json             # cotes mesurées sur l'ortho (coupes), lues à l'étape 1 du choix (§ 4.3)
```

Une preuve s'écrit `photo:<identifiant>`, `tuile:<nom de tuile>`, `ortho:<millésime>`, `osm:<way|node>/<id>`,
`bdtopo:<cleabs>`, `mesure:<source>` ou `site:<id du dossier 13>`. Une pratique locale non conforme à l'IISR (ocre,
vert, Chronovélo, damier) **doit** avoir une preuve `photo:` ou `mesure:`, sinon elle est refusée (00_SYNTHESE § 0.1 ;
RF-OBS-MAR-01, RF-OBS-MAR-02, RF-OBS-ILO-03). Une photo de chantier (marquage jaune) ne prouve pas l'état permanent
(RF-OBS-MAR-03).

## 9. De la description au modèle

Trois passes, dans `recon/out/generateur/meylan/<reseau>/` :

1. **Résolution** (lot N1, `recon/generateur/reseau/resoudre_reseau.py`, Python hors Houdini). Elle résout les nœuds,
   les ancrages, OSM, les tracés et les profils `osm`, les positions en mots et les valeurs approchées. Elle écrit :
   - `description_resolue.yaml` : une description **exacte** au format `description_simple/0.2` de l'étape 2 ;
   - `compilation_reseau.json` : approximations (chemin, texte dit, plage, valeur retenue, choix, règle, confiance),
     ancrages résolus et écarts entre ancrages, ways retenus, clés de la couche réseau non portées par l'étape 2,
     avertissements, erreurs, et porte P00 (et P01 pour le graphe) au sens de `CHAINE_CONSTRUCTION.md`.
2. **Compilation du réseau** par l'étape 2 : `description/description_vers_modele.py`, qui appelle
   `description/carrefours.py`. Elle produit `modele/modele_voie.json` et le rapport de réseau de l'étape 2.
3. **Report de la couche réseau** dans le modèle. Les provenances `description:` posées par l'étape 2 sur des valeurs
   approchées sont remplacées par celles de la résolution (`plage`, `choix`). Les itinéraires, ouvrages, échangeurs,
   ancrages et l'état sont ajoutés. Le résultat est `modele/modele_reseau.json`, au schéma **`modele_voie/0.2`**
   proposé : une nouvelle copie du schéma ; la 0.1 reste valide et sert toujours les scènes S01-S12. Le schéma 0.2
   ajoute à la 0.1 :
   - `itineraires[]` : `{id, nom, routes, u_m, prioritaire, prov}` ;
   - `noeuds[].ancrage` : `{osm_node | site | photo | relatif, tolerance_m}` et `noeuds[].z` ;
   - `routes[].profil_long` régulier : `{source, declivites: [{s0, s1, pente}], raccordements: [{s, rayon, sens:
     saillant | rentrant}]}`, en plus des points `[s, z]` de la 0.1 ;
   - `routes[].jumelee_avec` ;
   - dans `prov`, les champs `plage: [min, max]` et `choix` (§ 4.3) ;
   - `ancrage` symbolique des évènements relatifs à un carrefour (§ 6.4) ;
   - `echangeurs[]` (regroupement) ;
   - `meta.etat` (nom, date).

Test de non-régression du lot N1 : une description au format de l'étape 2 passée par le résolveur ressort identique à
l'octet (`description_resolue.yaml` = entrée), et donne donc le même modèle.

## 10. Exemples

Les deux exemples réels ci-dessous montrent la syntaxe sur Meylan. Leurs valeurs viennent de deux sources : les
constats du dossier 13 (`D:\DocRoute\13_Observations_Panoramax_Isere\observations.json`, identifiants de photos
seulement) et les tags des extraits OSM et BD TOPO du dépôt. **Aucune photo n'a été regardée pour écrire ce
format.** Les valeurs « ≈ » sont à reprendre sur les tuiles natives des photos et sur l'ortho au lot N11, avant toute
fabrication. Des sites voisins sont décrits en ce moment par d'autres lots dans `recon/generateur/meylan/` :
`verdun_centre_feux`, `axe_verdun_centre`, `auto_noeud_a41_n87`, `rp_didcot`. Leurs `mesures.json` priment sur les
valeurs « ≈ » ci-dessous (choix « mesure », § 4.3).

### 10.1 La phrase de l'utilisateur

C'est l'exemple du § 1.

### 10.2 Avenue de Verdun, du chemin des Sources au chemin des Buclos (sites M27 et M17)

Le site M27 (îlots refuges et îlots peints) est à environ 20 m du débouché du chemin des Sources. Le site M17 est le
carrefour à feux du chemin des Buclos. Dans OSM (état 2026), l'avenue est découpée de part et d'autre des îlots en
ways à sens unique (`oneway=yes`, 50 km/h), dont plusieurs portent des voies de tourne-à-gauche (`turn:lanes`). Entre
les deux sites, on compte une vingtaine de ways. Ici, l'avenue est décrite comme **un** tronçon à double sens entre
deux nœuds (`osm: auto`) : c'est la fusion de RF-OSM-PRF-011, qui supprime les micro-routes (rupture R-09 de la chaîne).

```yaml
format: description_reseau/0.1
reseau: verdun_sources_buclos
titre: Avenue de Verdun (Meylan), du chemin des Sources au chemin des Buclos
etat: {nom: printemps_2025, date: 2025-05-18}     # photos M27 du 18/05/2025 ; date des photos M17 à relire
repere: l93
contexte: {agglomeration: oui, vitesse: 50, categorie: avenue}
sources:
  osm: {extrait: data/vector_gz/osm/roads.geojson.gz, note: état 2026, à recouper avec l'état décrit}
  photos: [176f9ab0-70a1-419e-9444-969bb89df5ac, 7ab5b751-02a9-459f-af08-8e8f0cb380b3,
           2b9bed48-67ea-4ebb-9c40-8356cec831b8, 10ab11e4-d6b3-43f2-b9f2-830a7adc3073]
noeuds:
  N_V0:      {position: [917391.4, 6460394.0], osm_pres_de: 10, type: limite_carte}  # côté Paquet Jardin (hors description)
  N_SOURCES: {position: [917483.4, 6460499.0], osm_pres_de: 10}                     # débouché du chemin des Sources
  N_BUCLOS:  {site: M17, osm_pres_de: 15}                                            # carrefour à feux
  N_V3:      {position: [917751.4, 6460763.0], osm_pres_de: 10, type: limite_carte}
  N_SRC_FIN: {depuis: N_SOURCES, distance: ≈ 60, cap: ≈ 290, type: limite_carte}
  N_BUC_N:   {depuis: N_BUCLOS, distance: ≈ 60, cap: ≈ 95, type: limite_carte}
itineraires:
  I_VERDUN: {nom: avenue de Verdun, troncons: [R_VERDUN_1, R_VERDUN_2, R_VERDUN_3], prioritaire: oui}
troncons:
  - id: R_VERDUN_1                                 # ≈ 140 m
    de: N_V0
    vers: N_SOURCES
    osm: auto
    # profil du tronçon M27 (scenes_meylan/M27_avenue_de_verdun.yaml), écrit d'après les tuiles des photos 176f9ab0 et 7ab5b751
    profil: "bande plantée ≈ 4 | trottoir ≈ 2 enrobé niveau chaussée | accotement herbe ≈ 2 | voie ≈ 3,25 ← | zone hachurée ≈ 2,8 | voie ≈ 3,25 → | accotement herbe ≈ 2 | piste cyclable ≈ 2,5 niveau chaussée | bande plantée ≈ 4"
    materiaux: {chaussee: enrobé usé, pistes: enrobé}
    marquages: {usure: usée}
    preuves: [photo:176f9ab0-70a1-419e-9444-969bb89df5ac, photo:7ab5b751-02a9-459f-af08-8e8f0cb380b3]
  - id: R_VERDUN_2                                 # ≈ 280 m
    de: N_SOURCES
    vers: N_BUCLOS
    osm: auto
    # même profil que R_VERDUN_1, prolongé : la suite îlot peint → continue axiale → îlot peint n'est pas relevée sur
    # toute la longueur (constats M27 et M17) ; à reprendre sur les photos avant fabrication
    profil: "bande plantée ≈ 4 | trottoir ≈ 2 enrobé niveau chaussée | accotement herbe ≈ 2 | voie ≈ 3,25 ← | zone hachurée ≈ 2,8 | voie ≈ 3,25 → | accotement herbe ≈ 2 | piste cyclable ≈ 2,5 niveau chaussée | bande plantée ≈ 4"
    evenements:
      # site M27 : îlot refuge bordé court (≈ 8 à 10 m) au passage, dans la zone hachurée ; J5 aux nez par la règle
      # (RF-GV-ILO-008 : îlot ≥ 1,90 m entre rives pour une J5 de 500)
      - "de ≈ 15 à ≈ 25 de N_SOURCES : îlot refuge bordure basse vue ≈ 0,11 enrobé"
      - "à ≈ 20 de N_SOURCES : passage piéton"
    preuves: [photo:176f9ab0-70a1-419e-9444-969bb89df5ac]
    ecarts_admis:
      RF-MA-REF-003: "bordures du refuge vues à 0,11 m ± 0,04 sur la photo M27 (176f9ab0), < 0,12 m"
  - id: R_VERDUN_3                                 # ≈ 95 m
    de: N_BUCLOS
    vers: N_V3
    osm: auto
    # constat M17 (photo 2b9bed48) : chaussée à 2 voies, bandes enherbées de 3 à 5 m entre chaussée et trottoirs
    profil: "trottoir ≈ 2 | accotement herbe 3 à 5 | voie ≈ 3,25 ← | voie ≈ 3,25 → | accotement herbe 3 à 5 | trottoir ≈ 2"
    preuves: [photo:2b9bed48-67ea-4ebb-9c40-8356cec831b8]
  - id: R_SOURCES
    nom: chemin des Sources
    de: N_SOURCES
    vers: N_SRC_FIN
    osm: [way/28420096]
    profil: osm                    # rien de relevé : profil inféré des tags OSM (avertissement « profil non relevé »)
  - id: R_BUCLOS
    nom: chemin des Buclos
    de: N_BUCLOS
    vers: N_BUC_N
    osm: auto                      # OSM : 2 voies près de l'avenue, puis sens unique (way/27286062, oneway=yes)
    profil: osm
carrefours:
  - id: C_SOURCES
    noeud: N_SOURCES
    regime: a_verifier             # régime non relevé : rien de peint ni posé (RF-OSM-CAR-012)
    branches: [{troncon: R_VERDUN_1}, {troncon: R_VERDUN_2}, {troncon: R_SOURCES}]
  - id: C_BUCLOS
    noeud: N_BUCLOS
    regime: feux
    branches:
      # constat M17 (photo 10ab11e4) : en amont, l'îlot bordé est prolongé par un îlot peint à contour continu et
      # chevrons, puis par une continue axiale ; les chevrons et la continue viennent des règles (RF-MQ-HACH-02, E12)
      - {troncon: R_VERDUN_2, passage: oui, ilot: central ovale}
      - {troncon: R_VERDUN_3, passage: oui}
      - {troncon: R_BUCLOS, passage: oui}
    preuves: [photo:2b9bed48-67ea-4ebb-9c40-8356cec831b8, photo:10ab11e4-d6b3-43f2-b9f2-830a7adc3073]
    # constats non portés par l'étape 2 (à lui proposer, § 7.1) : traversée cyclable en résine verte des deux côtés de
    # l'îlot (photo 2b9bed48) ; mâts bas R11 + R12 et répétiteur (photo 10ab11e4) ; J5 au nez, bas ≈ 0,6 m (photo 2b9bed48)
```

Ce que l'exemple éprouve :

- **Fusion des chaussées séparées d'OSM** en un tronçon à double sens (`osm: auto`). La ligne de référence passe au
  milieu de la zone hachurée.
- **Positions relatives** (« à ≈ 20 de N_SOURCES », « de ≈ 15 à ≈ 25 ») et **nœuds ancrés de quatre façons** : L93
  recalé sur OSM, site du dossier 13, relatif, limite de carte.
- **Largeur en plage** (`accotement herbe 3 à 5`), reprise d'un constat photo.
- **Régime incertain** (`a_verifier`) : rien n'est peint au débouché du chemin des Sources.
- **Écart admis** repris du tronçon M27 (`scenes_meylan/M27_avenue_de_verdun.yaml`).
- **Constats que l'étape 2 ne porte pas encore**, laissés en commentaire. La traversée cyclable verte en est un : c'est
  une pratique locale photographiée, donc admissible avec sa preuve. La hauteur de J5 (≈ 0,6 m) en est un autre :
  elle ne serait contrôlée qu'à ± 0,20 m (ARB-04).
- **Avertissements attendus** :
  - profils de R_SOURCES et R_BUCLOS non relevés (`profil: osm`) ;
  - l'allée de la Faculté débouche à environ 35 m du nœud N_BUCLOS (OSM way/1088412105) : c'est un carrefour OSM
    traversé par R_VERDUN_3 sans nœud décrit. Il faudra la décrire comme second nœud du carrefour (fusion de la porte
    P01-2) après lecture des photos.

### 10.3 Bout d'autoroute : sortie de la Rocade Sud (N87) vers l'A41 et vers le chemin du Vieux Chêne par l'« Hélice de Meylan »

Topologie lue dans l'extrait OSM (état 2026), dans le sens de circulation des ways :

- la bretelle de la Rocade Sud (`trunk_link`, `ref=N 87`) quitte la N87 vers le nord (≈ 918 366 ; 6 459 677) ;
- elle passe sur trois ouvrages (`bridge=yes`, `layer=1` : ways 28712714, 28341977, 165939595) jusqu'à une
  divergence (≈ 918 625 ; 6 460 037) ;
- une branche rejoint l'A41 vers l'ouest (way 235030397, 90 km/h, convergence vers ≈ 918 480 ; 6 459 983) ;
- l'autre est l'« Hélice de Meylan » (ways 112621089, 361790056, 361790055, 857526255, 235030396 : 30 km/h au début,
  1 voie puis 2 et 3 voies). Elle aboutit au carrefour à feux du chemin du Vieux Chêne (site M07, ≈ 918 478 ;
  6 460 318).

Les profils d'autoroute ne sont pas relevés ici. Le seul constat du dossier 13 est celui de la Rocade Sud près du site
M26 : terre-plein à double séparateur béton (DBA) de 2,6 ± 0,5 m et chaussée de 11,3 ± 0,6 m, mesurés sur l'ortho. Le
site voisin `recon/generateur/meylan/auto_noeud_a41_n87/` doit fournir les cotes.

```yaml
format: description_reseau/0.1
reseau: echangeur_rocade_sud_helice
titre: Échangeur N87 / A41 et Hélice de Meylan (une direction)
etat: {nom: actuel, date: 2026-10-09}            # date des fichiers de l'extrait OSM du dépôt ; à confirmer sur photos et ortho
repere: l93
contexte: {agglomeration: non, categorie: voie_express}
noeuds:
  N_N87_S:       {position: [918366, 6459677], osm_pres_de: 10, type: limite_carte}
  M_DIV_HELICE:  {position: [918625, 6460037], osm_pres_de: 5, type: fourche}    # musoir de divergence
  M_CONV_A41:    {position: [918480, 6459983], osm_pres_de: 5, type: fourche}    # musoir de convergence sur l'A41
  N_A41_E:       {position: [919109, 6460171], osm_pres_de: 10, type: limite_carte}
  N_A41_O:       {position: [918221, 6459917], osm_pres_de: 10, type: limite_carte}
  N_VIEUX_CHENE: {site: M07, osm_pres_de: 15}                                   # carrefour à feux
itineraires:
  I_A41: {nom: A41 sens ouest, troncons: [R_A41_O1, R_A41_O2], prioritaire: oui}   # marquage continu à travers le musoir
troncons:
  - id: B_N87_DIV
    ref: N87
    categorie: bretelle
    de: N_N87_S
    vers: M_DIV_HELICE
    osm: [way/84073, way/28712714, way/28712715, way/28341977, way/41914735, way/165939595, way/165939596]
    vitesse: 90                     # maxspeed OSM : 90 puis 70 puis 50 le long de la bretelle (évènements à écrire)
    profil: "BDG ≈ 0,75 | voie 4 → | BAU ≈ 2"            # 1 voie (OSM lanes=1) ; largeurs à mesurer
  - id: B_VERS_A41
    categorie: bretelle
    de: M_DIV_HELICE
    vers: M_CONV_A41
    osm: [way/235030397]
    vitesse: 90
    profil: "BDG ≈ 0,75 | voie 4 → | BAU ≈ 2"
  - id: R_A41_O1                    # A41 sens ouest, en amont du musoir de convergence
    ref: A41
    categorie: autoroute
    de: N_A41_E
    vers: M_CONV_A41
    osm: [way/4017853]
    vitesse: 110
    profil: "BDG ≈ 1 | voie → | voie → | BAU | berme"     # 2 voies (OSM) ; largeurs : règles (voie 3,50, BAU 3,00, berme 1,00 : RF-OSM-LAR-014)
  - id: R_A41_O2                    # en aval du musoir
    ref: A41
    categorie: autoroute
    de: M_CONV_A41
    vers: N_A41_O
    osm: [way/4017854]
    vitesse: 110
    profil: "BDG ≈ 1 | voie → | voie → | BAU | berme"
  - id: B_HELICE
    nom: Hélice de Meylan
    categorie: bretelle
    de: M_DIV_HELICE
    vers: N_VIEUX_CHENE
    osm: [way/112621089, way/361790056, way/361790055, way/857526255, way/235030396]
    # forme (boucle, diagonale, anse) à relever sur l'ortho
    vitesse: 30                     # maxspeed OSM du premier way
    profil: osm                     # OSM lanes 1, 1, 2, 3, 2 selon les ways : une section par way ; à vérifier sur les
                                    # photos du site M07 (arrivée sur feux en 2 ou 3 voies : ICTAVRU p. 91)
bretelles:
  - id: BR_A41                      # insertion de B_VERS_A41 sur l'A41 (clés de l'étape 2)
    type: entree
    principale: R_A41_O2
    bretelle: B_VERS_A41
    point: M_CONV_A41               # couche réseau : nœud fourche, résolu en position
    # biseau, longueur, obliquité non dits : règles de voie rapide (« à verser », E04)
echangeurs:
  E_ROCADE_SUD:
    type: noeud
    chaussees: [R_A41_O1, R_A41_O2]
    bretelles: [BR_A41]
    u: 7,5 cm
ouvrages:
  O_1: {type: pont, porte: [B_N87_DIV], osm: [way/28712714]}
  O_2: {type: pont, porte: [B_N87_DIV], franchit: [R_A41_O2], osm: [way/28341977]}   # croise aussi la chaussée est (non décrite) ; à confirmer sur l'ortho
  O_3: {type: pont, porte: [B_N87_DIV], osm: [way/165939595]}
carrefours:
  - id: C_VIEUX_CHENE
    noeud: N_VIEUX_CHENE
    regime: feux
    branches:
      - {troncon: B_HELICE, fleches: oui}
      - {troncon: B_HELICE, mouvements: ≈ 2}      # ERREUR VOLONTAIRE : les mouvements ne s'approchent pas, et la branche est en double
```

Ce que l'exemple éprouve, et ce qu'il refuse :

- **Bretelles et musoirs.** Les bretelles sont des tronçons et les musoirs des nœuds `fourche` partagés : la continuité
  entre la chaussée principale et la bretelle est donc topologique. L'A41 est coupée au musoir de convergence en deux
  tronçons ; l'itinéraire I_A41 garde la phase et l'unité u des marquages à travers ce nœud. L'insertion est l'objet
  `bretelles` de l'étape 2.
- **La divergence M_DIV_HELICE** (une bretelle qui se sépare en deux bretelles) n'est pas un objet `bretelles` de
  l'étape 2, qui relie une bretelle à une chaussée principale. Elle reste un nœud `fourche` de la couche réseau, à
  proposer à l'étape 2.
- **Ouvrages ancrés sur OSM.** Leur altitude vient du gabarit et du MNT, jamais de `layer` (RF-OSM-OUV-001). La porte
  P02 vérifie la hauteur libre (RF-GV-PON-012). C'est la lacune L-08 : le LiDAR HD local ne couvre pas l'échangeur.
- **Règles absentes de la base** pour la géométrie des bretelles (lacune L-01). Le résolveur le signale et applique
  les valeurs relues dans ICTAVRU et VSA 90/110, une fois versées.
- **Ligne volontairement fausse.** La seconde branche de C_VIEUX_CHENE est refusée deux fois : `mouvements` ne
  s'approche pas (§ 4.1), et la branche B_HELICE y figure en double. Il faut décrire les autres branches du carrefour
  d'après les photos (site M07 : photos c02e39f5…, 0190214f…).

## 11. Erreurs et avertissements

Le résolveur **refuse** (erreur) :

- les cas d'erreur du format du tronçon (`FORMAT_DESCRIPTION.md` § 12) et du compilateur de réseau de l'étape 2
  (par exemple une branche qui ne rejoint pas le centre à 0,05 m près) ;
- un nœud sans ancrage, ou deux ancrages contradictoires ;
- un tronçon dont `de` ou `vers` n'est ni un nœud déclaré ni une coordonnée ;
- une plage vide ou inversée ;
- une valeur approchée là où elle est interdite : nombre de voies, sens, vitesse, régime, mouvements, code de panneau ;
- un évènement hors de son tronçon ;
- des contraintes entre plages impossibles à satisfaire ;
- une pratique locale non conforme sans preuve `photo:` ou `mesure:` ;
- deux tronçons qui se croisent sans nœud ni ouvrage ;
- une bretelle dont un bout n'est ni un musoir ni un carrefour ;
- une clé de la couche réseau que l'étape 2 ne porte pas encore, si elle change la géométrie.

Il **avertit** dans les cas suivants :

- position ou emprise non dite (choix par défaut) ;
- valeur prise au centre de sa plage ;
- branche de carrefour sans régime (`a_verifier`) ;
- profil d'un tronçon non relevé (`profil: osm`) ;
- photo sans date ou d'un autre état que celui décrit ;
- itinéraire déduit des noms ;
- tracé OSM à plus de 1,50 m [G] du tracé régulier ;
- way OSM partagé avec un tronçon non décrit, ou carrefour OSM traversé sans nœud décrit.

## 12. Compatibilité

- **Format de l'étape 2.** Une description `description_simple/0.2` (tronçon seul, ou réseau à `troncons`,
  `carrefours`, `giratoires`, `bretelles`) est déjà une description réseau valide. Le résolveur la laisse inchangée,
  à l'octet.
- **Format du tronçon de l'étape 1.** `scenes_simples/S*.yaml`, `scenes_meylan/M*.yaml` et
  `description/exemples/*.yaml` restent valides tels quels et passent directement au compilateur.
- **Descriptions de sites** (`recon/generateur/meylan/<site>/description.yaml`). Ce qu'elles mettent dans
  `extensions_auto` se transpose avec la table du § 7.5.
- **Relevé de Paquet Jardin.** La description réseau ne le remplace pas (`recon/pcg`, état avant travaux). Elle sert à
  décrire le reste de Meylan ; ce relevé reste la référence de comparaison (PLAN_GENERATEUR § 6).
