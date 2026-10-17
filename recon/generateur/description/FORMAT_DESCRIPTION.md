# Format de description simple d'une route (`description simple → modele_voie`)

*`recon/generateur/description/FORMAT_DESCRIPTION.md` — lot L0 du générateur (PLAN_GENERATEUR § 3), 17/10/2026.*

On décrit une route comme on la décrirait en regardant une photo : « route X → Y, 2 × 1 voies, bordures T2, trottoir
2 m en béton balayé, rabattement ici, dos-d'âne là avec passage piéton, enrobé usé ». Le compilateur
`description_vers_modele.py` en fait un modèle `modele_voie/0.1` valide, celui que lit le générateur Houdini.

**Principe.** Ce qui est dit est repris tel quel, avec la provenance `description:<champ>`. Ce qui n'est pas dit est
complété par la règle de `assets/specs/route/regles_route_fr.json` qui le fixe (`defaut:DEF-…`, `inference:RF-…`), et
cette règle est citée dans le modèle. Si aucune règle ne fixe une valeur non dite (largeur d'une entrée charretière,
d'un fossé, d'un abord), la compilation s'arrête et le dit : **Houdini n'invente rien**. Un mot ou une clé inconnus
sont des erreurs, jamais ignorés.

```
python recon/generateur/description/description_vers_modele.py MA_RUE.yaml [--sortie DOSSIER] [--verifier-determinisme]
python recon/generateur/description/tests/tester_descriptions.py      # tous les exemples + le catalogue voisin
```

Sorties (par défaut `recon/out/generateur/<scene>/`, non versionné) : `modele_voie.json` et `compilation.json`
(avertissements, contrôles de conformité valeur / plage / règle / statut, règles utilisées, résultat du validateur).

## 1. L'exemple le plus court

```yaml
scene: ma_rue
contexte: {agglomeration: oui, vitesse: 30}
troncon: {de: [0, 0], vers: [120, 0]}
profil: "trottoir 2 | voie ← | voie → | stationnement | trottoir 2"
evenements:
  - "à 40 : passage piéton"
```

Le compilateur en tire : voies de 3,00 m (RF-OSM-LAR-010), stationnement de 2,00 m (RF-OSM-LAR-040), bordures T2 de
0,14 m entre chaussée et trottoirs (RF-OSM-NIV-010, DEF-005), dévers 2,5 % en toit et 1,5 % sur les trottoirs
(DEF-006), axe T'1 2u (RF-OSM-MRQ-010, chaussée ≥ 5,20 m), ligne T'2 2u du stationnement (RF-OSM-MRQ-060), u = 5 cm
(DEF-001) ; pour le passage : bandes de 4,00 m (DEF-011), abaissés en vue 0,02 avec rampants de 2,40 m et BEV
(DEF-031), lignes interrompues à 0,50 m (RF-MQ-PP-03), stationnement neutralisé 5 m en amont (RF-OSM-STA-002, DEF-009).

## 2. Clés du fichier

| Clé | Contenu | Obligatoire |
|---|---|---|
| `scene` | nom court (dossier de sortie) | non (nom du fichier) |
| `description` | la phrase libre : reprise dans `meta.description` | non |
| `titre`, `nom`, `date`, `format`, `attendus` | renseignements ; `attendus` est recopié dans le rapport | non |
| `confiance` | `haute`, `moyenne` (défaut), `faible` : confiance des valeurs dites (photo : moyenne ; relevé : haute) | non |
| `origine` | `[x, y, z]` Lambert-93 de l'origine locale ; défaut O du dépôt (917279,43 ; 6460289,98 ; 216,30) | non |
| `contexte` | § 3 | oui (au moins agglomération, catégorie ou vitesse) |
| `troncon` | tracé (§ 4) ; ou `trace` / `polyligne` / `longueur` directement à la racine | oui |
| `troncons` | liste de tronçons indépendants, chacun avec ses clés `profil`, `evenements`… | non |
| `profil` | profil en travers de gauche à droite (§ 5) | oui |
| `materiaux` | matériaux par classe (§ 6) | non |
| `marquages` | `auto` (défaut) ou surcharges (§ 7) | non |
| `evenements` | ce qui arrive à une abscisse (§ 8) | non |
| `vegetation`, `objets` | arbres, figurines, avancées plantées (§ 9) | non |
| `abords` | pelouse, prairie, champ… de chaque côté (§ 9) | non |
| `signalisation` | panneaux (§ 10) | non |
| `ecarts_admis` | écarts aux règles admis pour décrire un cas réel non conforme : `{RF-…/DEF-…: "motif, preuve"}` (§ 12 bis) | non |

Les clés s'écrivent avec ou sans accents ni majuscules (`Dos d'âne:` = `dos_d_ane:`).

## 3. Contexte

| Clé | Valeurs | Si non dit |
|---|---|---|
| `agglomeration` | oui / non | déduite de la catégorie, sinon de la vitesse ≤ 50 (RF-OSM-AGG-001, confiance faible) |
| `categorie` | rue, avenue, boulevard, allée, route, route départementale, route nationale, zone de rencontre, voie verte… | rue en agglomération, route départementale hors (table du volet 12) |
| `vitesse` (ou `vitesse_kmh`) | km/h | 50 en agglomération (RF-OSM-VIT-002) ; 80 / 90 / 110 / 130 hors (RF-OSM-VIT-003) ; 20 en zone de rencontre (RF-OSM-VIT-004) |
| `u` (« 6 cm ») ou `u_m` (0,06) | 3, 5, 6 ou 7,5 cm | DEF-001 (5 cm ; 7,5 cm autoroute ; 3 cm piste) |
| `sens_unique` | oui / non | déduit des flèches des voies |
| `v15` (ou `V15_kmh`) | km/h, pour la longueur L des flèches et annonces | la vitesse, plafonnée à 100 en double sens (RF-MQ-PS-02) |
| `usure_marquages` | 0 (neuf) à 1 (effacé) | aucune |

## 4. Tronçon et tracé

Coordonnées locales en mètres depuis `origine` (ou `repere: l93` pour des coordonnées Lambert-93). Cap en degrés à la
façon OpenDRIVE : 0° = est, 90° = nord, sens trigonométrique.

```yaml
troncon: {de: [0, 0], vers: [150, 0]}                 # une droite
troncon: {longueur: 120, depart: [0, 0], cap: 90}     # une droite de 120 m vers le nord
troncon:                                              # droites, arcs et clothoïdes raccordés
  depart: [0, 0]
  cap: 0
  trace:
    - droite: 60
    - clothoide: {longueur: 20, rayon_fin: 150, sens: gauche}
    - arc: {rayon: 150, angle: 25, sens: gauche}      # ou longueur: au lieu d'angle:
    - droite: 50
troncon: {polyligne: [[0, 0], [50, 0], [100, 20]]}    # droites par sommets (cassures signalées si > 1°)
```

La ligne du tronçon est **l'axe de la chaussée** : la séparation des sens d'une route à double sens (le milieu du
terre-plein s'il y en a un) ou le milieu de la chaussée d'une route à sens unique (RF-OSM-PRF-010).

## 5. Profil en travers

De **gauche à droite en regardant dans le sens du tronçon** (de `de` vers `vers`). Une ligne, éléments séparés par
`|` (la ligne peut être coupée avec `>-`, ou écrite en liste, un élément par ligne) :

```yaml
profil: "trottoir 2,0 béton balayé | bordure T2 granit | stationnement 2,0 | voie 3,2 ← | voie 3,2 → | bande cyclable 1,5 | trottoir 2"
```

Chaque élément est **une bande** (type, largeur en m facultative, sens, attributs) ou **une limite** entre deux
bandes (bordure, ligne, séparateur ponctuel). Une limite non écrite est déduite des niveaux et des types (§ 5.3).

### 5.1 Bandes

| Écrire | Type du modèle | Largeur si non dite |
|---|---|---|
| `trottoir` | trottoir | 2,00 (DEF-004) |
| `voie`, `voie de circulation` | voie_circulation | 3,00 double sens (RF-OSM-LAR-010) ; 3,25 sens unique à 1 voie (RF-OSM-LAR-011) ; 3,00 voies de même sens (RF-OSM-LAR-012) ; hors agglomération 3,00 / 3,50 selon la catégorie (RF-OSM-LAR-014) |
| `voie bus`, `couloir bus` | voie_bus | 3,20 (RF-OSM-LAR-013) |
| `tourne-à-gauche`, `tourne-à-droite`, `voie de stockage` | voie_tourne_gauche… | 2,75 (RF-OSM-LAR-012, présélection) |
| `chaussée partagée` | chaussee_partagee (sens double) | 4,00 (RF-GV-PT-004, confiance faible) |
| `bande cyclable`, `bande vélo` | bande_cyclable | 1,50 (RF-OSM-LAR-030, DEF-007) |
| `piste cyclable`, `piste` | piste_cyclable ; `bidirectionnelle` → deux demi-pistes de sens opposés | 2,00 uni, 3,00 bi (RF-OSM-LAR-031, DEF-008) |
| `voie verte` | voie_verte | 3,00 (RF-GV-PT-013, faible) |
| `stationnement`, `parking` (`longitudinal`, `épi`, `bataille`, `mi-trottoir`, `sur trottoir`, `encoche`, `places marquées`) | stationnement | 2,00 longitudinal (RF-OSM-LAR-040) ; 5,00 épi / bataille (RF-OSM-LAR-041) |
| `livraison` | livraison | 2,00 (RF-MA-STA-009) |
| `tampon` | zone neutralisée contre l'ouverture des portières | 0,50 (RF-OSM-LAR-032) |
| `zone hachurée`, `zone neutralisée` | zone_neutralisee (hachures) | — à dire |
| `terre-plein`, `TPC` (`planté`, `arbres`, `gazon`, `BRF`, `gravier`, `hachuré` / `peint`, `franchissable`) | terre_plein (+ objet terre_plein) | 2,00 planté (RF-OSM-LAR-050, faible) ; peint : à dire |
| `bande plantée`, `bande enherbée` (`arbres`) | bande_plantee | 3,00 (RF-GV-TPC-010, fosse 3 × 3 m) |
| `séparateur` | separateur (0,15 m de haut, RF-OSM-LAR-033) | 0,30 (RF-OSM-LAR-033) |
| `accotement`, `bande dérasée`, `BDD`, `BDG`, `surlargeur` | accotement_revetu, bande_derasee | 0,50 / 1,00 (RD), 2,50 (RN) (RF-OSM-LAR-014) |
| `accotement herbe`, `accotement enherbé`, `berme` | berme | 1,00 (RF-OSM-LAR-014, faible) |
| `BAU` | bande_arret_urgence | 3,00 (RF-OSM-LAR-014) |
| `quai`, `quai bus` | quai_bus | — à dire |
| `chemin`, `fossé`, `noue`, `talus` | chemin_pieton, fosse, noue, talus | — à dire |

**Sens** : `→` (ou `->`, `avant`) dans le sens du tronçon, `←` (`<-`, `arrière`) à contresens, `↔` (`<->`). Si aucune voie
n'a de flèche, une moitié gauche ← et une moitié droite → (circulation à droite, RF-OSM-PRF-002) ; les bandes
cyclables, le stationnement et les couloirs bus prennent le sens de la voie la plus proche. Une voie ← à droite d'une
voie → est refusée.

**Dévers** (non dits, aucune clé) : chaussée 2,5 % en toit, crête sur la séparation des sens (DEF-006) — une bande de
séparation au niveau de la chaussée (zone hachurée) est à plat (crête, RF-OSM-NIV-011) ; trottoir 1,5 % vers la chaussée
(DEF-006) ; **hors agglomération**, bande dérasée 4 % et berme 8 % vers l'extérieur (RF-GV-DEV-001, ARP p. 46), la
surlargeur revêtue restant au dévers de la chaussée. Chaque dévers porte sa provenance (`prov["niveau.devers_pct"]`).

**Dévers dit** : `dévers 2,5` (ou `devers: 2.5` en forme structurée), en %, + : descend vers la droite (convention
du modèle) ; remplace le dévers déduit (par exemple une liaison revêtue à plat qui coupe un accotement au droit d'un
passage, raccordée sans marche aux sections voisines).

**Niveaux** : `niveau trottoir`, `niveau intermédiaire` (pistes, 2-4 cm, RF-MA-SEP-005), `niveau chaussée`,
`de plain-pied` / `sans bordure`. Par défaut : chaussée à 0 ; trottoir, bande plantée et piste au niveau du trottoir
(vue DEF-005, piste : RF-OSM-NIV-013) ; terre-plein bordé à 0,11 (DEF-005 îlot) ; quai à 0,21 (DEF-032).

**Forme structurée** (celle du catalogue `scenes_simples/`) : une liste de dictionnaires, équivalente à la ligne :

```yaml
profil:
  - {bande: trottoir, id: tr1, largeur: 2.00, materiau: enrobe_trottoir}
  - {bordure: T2, vue: 0.14, caniveau: CS2}
  - {bande: voie, id: v1, sens: arriere, largeur: 3.00}
  - {ligne: "T'1", largeur_u: 2}
  - {bande: voie, id: v2, sens: avant, largeur: 3.00}
  - {bordure: T2, vue: 0.14, caniveau: CS2}
  - {bande: trottoir, id: tr2, largeur: 2.00}
```

`id` donne un nom à la bande (sinon `tr1`, `v1`, `v2`…), utilisable dans les évènements et objets. Les matériaux
s'y écrivent en `materiau_id` du catalogue `assets/specs/materiaux_sol.json` ou en mots (§ 6).

### 5.2 Limites écrites

| Écrire | Effet |
|---|---|
| `bordure T2` (`T1`, `T3`, `A1`, `A2`, `I1`, `I2`, `P1`-`P3`, `CS1`… `quai`, `bateau`, `basse` = A2, `haute` = T2) | profil de bordure ; la vue est le saut de niveau des deux bandes |
| `bordure … granit` / `béton` / `béton clair` / `calcaire` | matériau de la bordure |
| `bordure … vue 0,12` (ou `vue 12 cm`) | vue dite : la bande haute voisine prend ce niveau |
| `bordure … caniveau CS2` | caniveau au pied de la bordure |
| `ligne T3 5u`, `ligne continue 3u`, `ligne T'1`, `ligne aucune`, `ligne T'2 2u jaune`, `ligne continue 10 cm` | remplace la ligne déduite (si c'est la même que la règle, la règle reste citée ; sinon l'écart est signalé) |
| `potelets`, `balises`, `plots`, `jardinières`, `glissière`, `GBA`, `muret`, `haie`, `bordure séparatrice` (+ pas) | séparateur ponctuel ou continu sur la limite |
| `sans bordure` | plain-pied (refusé si les niveaux diffèrent) |

### 5.3 Limites déduites (rien d'écrit)

| Entre | Limite | Règle |
|---|---|---|
| chaussée et trottoir, bande plantée, piste au niveau du trottoir | bordure T2, vue = saut de niveau | RF-OSM-NIV-010, DEF-005 |
| chaussée et terre-plein | bordure I2 (vue nominale 0,11) | DEF-005, RF-AS-profil_I2 |
| chaussée et quai | bordure QUAI_BUS | DEF-032 |
| piste à niveau intermédiaire et voisins | bordure chanfreinée (« autre ») | RF-MA-SEP-005 |
| chaussée et séparateur | séparateur (bordure séparatrice 0,15 m) | RF-MA-SEP-001 |
| voie ← et voie → | axe T'1 2u en agglomération, T1 2u hors ; aucune ligne sous 5,20 m de largeur circulable ; continue 5u sur une chaussée à 4 voies | RF-OSM-MRQ-010, RF-MQ-LAR-A1b |
| voies de même sens | T'1 2u (T1 hors agglomération) ; T3 2u à côté d'une voie affectée | RF-OSM-MRQ-011 |
| voie et bande cyclable | T3 5u | RF-OSM-MRQ-030 |
| voie et voie bus | T3 5u ; continue 5u si permanent ou contresens | RF-OSM-MRQ-031 |
| voie (ou bande cyclable, tampon) et stationnement | T'2 2u (jaune pour une livraison) | RF-OSM-MRQ-060 |
| voie et zone hachurée ou terre-plein peint | continue 3u | RF-OSM-CAR-051, RF-MQ-LAR-D1 |
| voie et accotement, bande dérasée, herbe (pas de bordure) | rive T2 3u (continue 3u ou T4 3u sur autoroute) | RF-OSM-MRQ-021, RF-OSM-MRQ-022 |
| deux demi-pistes | axe T'1 2u en u = 3 cm | RF-OSM-CYC-002 |
| autres bandes au même niveau | changement de revêtement | — |

## 6. Matériaux et usure

Sur une bande (`trottoir 2 béton balayé`) ou pour une classe :

```yaml
materiaux: {chaussee: enrobé usé, trottoirs: dalles, pistes: enrobé, bordures: granit, terre_plein: gazon}
```

| Mots | materiau_id (`materiaux_sol.json`) |
|---|---|
| `enrobé` | enrobe_bbsg_ancien (chaussée), enrobe_trottoir (trottoir), enrobe_piste_cyclable (piste) |
| `enrobé usé` / `ancien`, `enrobé neuf` / `récent`, `enrobé rapiécé`, `enrobé clair`, `enrobé ocre` | enrobe_bbsg_ancien, enrobe_bbsg_neuf_2025, enrobe_reprise_tranchee, enrobe_clair_granulats, enrobe_colore_ocre |
| `béton` / `béton balayé`, `béton désactivé`, `dalles`, `pavés`, `pavés granit`, `stabilisé` | beton_balaye, beton_desactive, dalles_beton, paves_beton, paves_granit, stabilise_beige |
| `gazon` / `pelouse` / `herbe`, `herbe haute`, `gravier`, `gravillons`, `galets`, `BRF`, `terre`, `résine verte` | gazon_tondu, herbe_haute, gravier_concasse_6_10, gravillons_ilot, galets_20_40, brf_bois_concasse, terre_nue, resine_verte |
| bordures : `béton`, `béton clair`, `granit`, `calcaire` | beton_bordure_gris, beton_bordure_clair, granit_bordure, calcaire_bordure |

Un matériau dit pour une bande vaut pour les bandes suivantes du même type (« trottoir 2 dalles | … | trottoir 2 » :
deux trottoirs en dalles). Non dit : table `surface_vers_materiau` du volet 12 ; bande cyclable = revêtement de la
chaussée (RF-MA-BAN-009) ; piste haute = enrobé de piste (RF-MA-PIS-009). Les pratiques locales non conformes à
l'IISR (ocre, vert, Chronovélo) ne s'appliquent que si on les écrit (DEF-008, DEF-020).

**Usure des marquages** (`marquages: {usure: légère}`, échelle du format, 0 = neuf, 1 = effacé) : neuf 0 ; légère
0,2 ; moyenne 0,4 ; usée 0,5 ; forte / très usée 0,7 ; effacée 0,85.

## 7. Marquages

`marquages: auto` (défaut) : tout vient des règles (§ 5.3). Surcharges globales :

```yaml
marquages: {axe: "T1", rives: "T2 3u", entre_voies: "T3", cyclable: "continue 5u", usure: usée}
marquages: {axe: aucune}
```

## 8. Évènements le long du tronçon

Deux écritures équivalentes : un dictionnaire, ou une phrase « à S : … ».

```yaml
evenements:
  - passage_pieton: {a: 40}
  - "à 95 : plateau avec passage piéton"
  - "à 150 : arrêt de bus droite"
  - rabattement: {a: 200, sens: →, voie: gauche, biseau: 60}
```

| Évènement | Paramètres (défaut et règle si non dit) | Ce que le modèle reçoit |
|---|---|---|
| `passage_pieton` | `largeur` (longueur des bandes, 4,00 DEF-011) ; `abaisses` (oui) ; `bev` (oui) ; `pente_rampants_pct` 5 ou 8 (DEF-031) ; `panneau` (C20a, non) | marquage passage_pieton (polygone par groupe de bandes traversées : chaussée, zone neutralisée, accotement revêtu, piste ; jamais sur un trottoir ni un chemin ; règles RF-MQ-PP-01/02/05) ; abaissés sur les seules bordures de la traversée (aboutissement sur la première surface piétonne de chaque côté : trottoir, chemin, quai, voie verte ; refuge ; bordure franchie entre deux bandes traversées) et BEV côté piéton aux aboutissements et sur le refuge ; **refus** si un côté aboutit sur une berme, une bande plantée, un terre-plein extérieur ou le bord du profil avant toute surface piétonne (décrire la traversée revêtue par un évènement `profil` au droit du passage) ; aboutissement de plain-pied (sans bordure) : BEV impossible au schéma 0.1, interdit RF-MA-BEV-001 admissible ; lignes interrompues à 0,50 m (RF-MQ-PP-03) ; stationnement neutralisé 5 m en amont et au droit (RF-OSM-STA-002) ; contrôle du refuge si un terre-plein est traversé (DEF-022, RF-MA-REF-003) |
| `dos_d_ane` | `longueur` 4,00, `hauteur` 0,10 (RF-MA-RAL-001) ; `triangles` (oui) | objet dos_d_ane ; 3 triangles D.8 par voie (RF-MQ-RAL-01) ; axe T3 2u prolongé de 10 m si chaussée ≥ 5 m ; **refusé** hors agglomération ou à plus de 30 km/h (décret 94-447, RF-MA-RAL-001), sauf écart admis (§ 12 bis) ; **passage piéton dessus refusé** (RF-MA-RAL-001) |
| `plateau` (`passage_pieton: oui`) | `longueur` du plateau (4,00, borne haute de RF-MA-RAL-001, faible) ; `hauteur` 0,10, `rampe_pct` 7 (DEF-034) | objet plateau (longueur rampes comprises) ; triangles TRIANGLE_PLATEAU en rampe claire (RF-MQ-RAL-03) ; avec passage : bandes = plateau + 2 × 0,50 m, pas de triangles (RF-MQ-PP-04) |
| `coussin` | `largeur` 1,75, `longueur` 3,00, `hauteur` 0,06 (RF-GV-RAL-001, bornes basses, faible) | un coussin par voie ; 3 triangles TRIANGLE_COUSSIN (RF-MQ-RAL-02) |
| `rabattement` (N → N−1) | `a` = fin du biseau ; `sens` (→ / ←) ; `voie` gauche (défaut) / droite pour les usagers ; `biseau` (hors agglomération 37 × d, RF-GV-PT-014 ; en agglomération aucune règle ne le chiffre : pris égal à l'oblique L, RF-MQ-OBL-02, confiance faible) ; `zebra` (oblique peinte de longueur max(biseau, L) et zone hachurée, RF-MQ-OBL-02) ; `elargit: <bande>` (le trottoir absorbe la largeur) ; `fleches` (oui), `nombre_fleches` (3, 2 en agglomération si la place manque) | sections : la voie passe de sa largeur à 0, puis disparaît ; flèches RAB_D / RAB_G à L, L − i1, L − i1 − i2 du milieu de l'oblique (RF-MQ-PS-03, RF-MQ-RAB-02 à -07) ; rive T'3 3u si la rive est peinte (RF-MQ-SC-11) |
| `elargissement` (N → N+1) | `a` = fin du biseau ; `sens` ; `voie` gauche / droite ; `type_voie` voie, tourne-à-gauche, tourne-à-droite, bus ; `largeur` ; `biseau` (comme le rabattement, RF-MQ-RET-01) | la nouvelle voie passe de 0 à sa largeur, puis reste |
| `zone_depassement_interdit` | `a` = début de la continue ; `sens` ; `fin` ; `annonce` (oui) ; `fleches` (oui hors agglomération) | axe continue 2u, annonce T3 2u de longueur L, 3 flèches RAB_D à cheval sur l'annonce (RF-MQ-PS-04/05, RF-MQ-RAB-02, -05, -07) |
| `fleches` | `type` TD, TAD, TAG, TD_TAD, TD_TAG (RF-MQ-DIR-02, tout autre refusé) ; `voies` (toutes ou liste) ; `nombre` 3 et `interdistance` 20 (DEF-017) | flèches au milieu des voies (RF-MQ-DIR-03) ; C24 signalé pour une affectation (RF-MQ-DIR-01) |
| `inscription` | `texte` (BUS…) ; `voie` ; `hauteur` (1,50 si V ≤ 50, RF-MA-CTC-002) | marquage inscription |
| `arret_bus` | `cote` (droite) ; `quai` (14 m, 20 si `articule`, DEF-032) ; `abri` (non) ; `zigzag` (oui) ; `panneau` (C6, non) | quai à 0,21 m sur les bandes contiguës à la chaussée (stationnement, bande plantée, trottoir ; une piste passe derrière) ; neutralisation 5 m avant et après (RF-MA-BUS-015) ; zigzag jaune 20 m avant / 10 m après le poteau (DEF-019, ARB-03) ; poteau, abri avec passage de 1,40 m devant (RF-MA-BUS-012, DEF-032) ; bande cyclable interrompue (RF-MA-BAN-007) |
| `entree_charretiere` | `cote` ; `largeur` (**à dire**) | abaissé « charretière » en vue 0,05 (RF-MA-TRO-015) ; rampants de 2 m si trottoir < 2,50 (RF-MA-TRO-016) ; pas de BEV |
| `abaisse` | `cote` (droite, gauche ou deux) ; `largeur` 1,20 (DEF-031) ; `bev` (oui) | abaissé de traversée |
| `panneau` | `code` (C20a, AB4, B14…) ; `cote` ; `valeur` | signal ; hauteur 2,30 en agglomération / 1,00 hors (DEF-025) ; décalage latéral au lot L6 (ARB-20) |
| `profil` | `nouveau` (une ligne de profil) ; `transition` (m) | nouveau profil à partir de `a` ; lois de largeur linéaires sur la transition si les bandes sont les mêmes, sinon changement instantané signalé |

Dans la phrase « à S : … », on peut écrire `gauche` / `droite`, `→` / `←`, `largeur 3`, `biseau 40`, `quai 20`,
`avec passage piéton`, `abri`, `articulé`, un code de panneau.

## 9. Végétation, objets, abords

```yaml
vegetation:
  - arbres: {bande: trottoir droite, pas: 8, essence: tilleul}   # ou « - arbres: bande plantée »
objets:
  - figurines: {gabarit: VELO, bandes: [pc1, pc2], a: [25, 75]}
  - arbres: {bande: tp1, de: 5, a: 95, pas: 7.5}
  - avancees_plantees: {bande: st1, de: 1.25, a: 98.75, pas: 7.5, longueur: 2.5, bordure: T2, sol: paillage_mineral, arbre: {t_depuis_voie: 1.5}}
abords:
  gauche: pelouse 8            # pelouse, gazon, herbe haute, prairie, friche, champ, forêt, bois, massif, parking, haie
  droite: {type: champ, largeur: 20, arbres: épars}
```

- **Dimensions des arbres** (correction après contrôle, portées dans le modèle : `asset_id`, `hauteur_m`,
  `houppier_rayon_m`, `fut_m` de l'objet le long) : `essence` (nom d'asset, nom français ou latin de
  `assets/specs/vegetation.json`, classe de taille facultative : « chêne grand », « tilleul ») ; `hauteur`,
  `houppier_rayon`, `fut` (hauteur des premières branches) dits, sinon ceux de la fiche de l'essence (sans essence :
  feuillu générique de la fiche, provenance `catalogue:`, confiance faible). Le fût est relevé au gabarit de
  RF-OSM-VEG-001 : 3,80 m si le houppier surplombe la chaussée, 2,50 m (cible) au-dessus d'un trottoir ; un fût dit
  plus bas est signalé non conforme. Le rendu dessine chaque arbre à ces dimensions (houppier, fût, cartes de feuilles
  de 0,08 à 0,15 m) ; la saison du rendu vient de `date` (hiver : arbres nus).
- **Arbres d'alignement** : pas 7,50 m (DEF-030) ; dans un trottoir, axe à 1,50 m du bord de chaussée (DEF-030) et
  contrôle des 1,40 m de cheminement qui restent derrière (RF-MA-TRO-001) ; dans une bande plantée ou un
  terre-plein, au milieu ; exclusions : passages, abaissés, entrées, arrêts, triangles de visibilité, cheminement.
- **Figurines vélo** : automatiques au pas de 50 m sur les bandes cyclables (DEF-018) ; ailleurs, à dire.
- **Avancées plantées** : sur chaque avancée, la file de stationnement devient une avancée au niveau du trottoir
  (bordure T2 qui en fait le tour, ligne T'2 interrompue) avec son arbre (DEF-030 « entre places »).
- **Abords** : zones `zones[]` le long des bords extérieurs, largeur **à dire** (aucune règle).

## 10. Signalisation

```yaml
signalisation:
  - {code: C20a, a: 38, cote: droite}
```

## 11. Ce que contient le modèle produit

- `meta.conventions` : toutes les abscisses (lois de largeur, intervalles, interruptions, abaissés, ancrages) sont
  **absolues** le long de la ligne de référence ; `t` positif à gauche ; cap OpenDRIVE.
- `routes[].ligne_reference` : `geometrie_reguliere` exacte (droites, arcs, clothoïdes) et une polyligne
  d'échantillonnage (flèche ≤ 5 mm) ; `sections[]` contiguës de 0 à L ; un profil par variante (passage, quai,
  biseau…), dédupliqué.
- `prov` sur chaque valeur : `description:<champ>` (dit), `defaut:` / `inference:` + règle (complété),
  `regle:inference_osm_profil.json#tables.…` (table du volet 12), `solveur:` (calculé). Le décompte par genre est dans
  `compilation.json` (`validation.prov_genres`).
- `compilation.json` : `controles` (largeurs comparées aux plages des règles, refuges, cheminement, piste contiguë…,
  avec valeur, plage, règle, statut), `avertissements` (écarts aux règles : une description dit ce qui existe, les
  écarts aux règles de conception sont signalés), `non_conformites` (contrôles « non_conforme » ou « hors_plage » non
  admis : ils **bloquent la fabrication**, `fabriquer_generateur.preparer_entree`), `ecarts_admis`,
  `regles_utilisees`, `non_portes_par_le_schema` (valeurs dites sans champ dans
  `modele_voie/0.1`, à reprendre aux lots suivants), résultat du validateur (provenance exigée).

## 12. Ce qui est refusé

Mot ou clé inconnus ; valeur non dite qu'aucune règle ne fixe ; voie ← à droite d'une voie → ; bordure entre deux
bandes au même niveau ; passage piéton sur un dos-d'âne ; flèche d'un schéma non autorisé ; rabattement dans un sens
à une seule voie ; quai sans trottoir ni stationnement ; biseau, annonce ou quai qui sortent du tronçon.
Depuis la correction après contrôle (17/10/2026) : deux évènements de même nature dont les emprises se chevauchent
(deux passages, deux quais…) ou deux ralentisseurs qui se chevauchent (plateau et dos-d'âne) ; un interdit
réglementaire sans écart admis : dos-d'âne ou plateau trapézoïdal (2,50 à 4,00 m) hors agglomération ou à plus de
30 km/h (décret 94-447, RF-MA-RAL-001), plateau hors agglomération (RF-GV-RAL-002) ; une essence d'arbre absente du
catalogue de végétation ; un écart admis sans motif ou citant une règle inconnue.

## 12 bis. Écarts admis : décrire un cas réel non conforme

Une rue réelle peut s'écarter des règles (refuge de 1,80 m, bordure de refuge à 0,10 m, dos-d'âne existant à 50 km/h).
Le compilateur ne l'interdit pas, mais il faut le dire, avec la preuve :

```yaml
ecarts_admis:
  DEF-022: "refuge de 1,80 m ± 0,40 relevé sur les photos M24 (9badc00e, f877235a)"
  RF-MA-REF-003: "bordures du refuge vues à 0,10 m ± 0,04 sur les photos M24"
```

Le contrôle correspondant passe alors à `non_conforme_admis` (ou `hors_plage_admis`) avec le motif, et la fabrication
n'est plus bloquée. Un écart admis qui ne sert à rien est signalé (à retirer). Sans écart admis, un contrôle non
conforme ou hors plage **bloque la fabrication** (`fabriquer_generateur.py` lit `compilation.json`) ; un interdit
réglementaire arrête déjà la compilation.

## 13. Exemples

| Fichier | Ce qu'il montre |
|---|---|
| `exemples/01_route_2x1_sans_bordure.yaml` | route départementale sans bordure, rives T2, BDD, accotements en herbe, virage R 150 |
| `exemples/02_rue_1x1_trottoirs.yaml` | rue 1 + 1, trottoirs, stationnement, passage piéton (exemple § 7.1 du volet 12) |
| `exemples/03_avenue_bandes_cyclables_stationnement.yaml` | bandes cyclables, tampon, stationnement, arbres dans le trottoir (§ 7.2) |
| `exemples/04_boulevard_2x2_terre_plein_plante.yaml` | 2 × 2 voies, terre-plein planté servant de refuge, bordures granit |
| `exemples/05_rue_piste_bande_plantee_arret_bus.yaml` | « scène E » sans carrefour : bande plantée, piste à niveau intermédiaire, passage, C20a, arrêt de bus en avancée |
| `exemples/06_rabattement_2_vers_1.yaml` | rabattement 2 → 1 avec biseau dit et 3 flèches |
| `exemples/07_zone30_ralentisseurs_passage.yaml` | dos-d'âne, plateau avec passage, coussins |
| `exemples/08_sens_unique_stationnement_charretieres.yaml` | sens unique, entrées charretières, abaissé, passage |
| `exemples/09_elargissement_tourne_a_gauche.yaml` | ouverture d'une voie de tourne-à-gauche |
| `exemples/10_changement_de_profil.yaml` | changement de profil avec transition, puis apparition d'une bande cyclable |
| `exemples/11_description_rapide_depuis_photo.yaml` | la forme la plus courte : phrases, mots courants, courbe |
| `exemples/12_piste_bidirectionnelle_separateur.yaml` | piste bidirectionnelle au niveau de la chaussée et séparateur |
| `../scenes_simples/S01` à `S12` (lot voisin, forme structurée) | compilées telles quelles : 12 / 12 en modèle valide, attendus vérifiables au niveau du modèle tous retrouvés (`validation/tests_description_L0.json`) |
| `../scenes_meylan/M24_avenue_du_granier.yaml`, `M27_avenue_de_verdun.yaml`, `M20_avenue_de_chamechaude.yaml` | **la boucle photo → description → fabrication** sur trois rues réelles de Meylan (correction après contrôle) : chaque description est écrite en regardant les tuiles des photos Panoramax du dossier 13 (commentaires : ce qui est vu, ce qui est simplifié) ; îlot refuge bordé dans une zone hachurée (changement de profil à largeur égale), écarts admis pour les cotes réelles non conformes, arbres d'essence connue |

## 14. Limites connues (étape 1)

- Pas de carrefour : un tronçon est isolé, ses extrémités sont des « limites de carte » (lots L3 et suivants).
- Le dessin des marques (traits, phase, hachures, aplats) est fait par les HDA `pj::marquage_*` au lot L4 : le modèle
  donne lignes, modulations, intervalles et interruptions, pas les traits.
- Le rayon de houppier, la hauteur et le fût des arbres sont portés depuis la correction après contrôle (champs
  `houppier_rayon_m` et `fut_m` ajoutés à la copie du schéma, `recon/generateur/schema/`). Quelques autres valeurs
  dites n'ont toujours pas de champ dans `modele_voie/0.1` (cotes des arbres d'une
  avancée) : elles sont listées dans `compilation.json` (`non_portes_par_le_schema`) au lieu d'être perdues en silence.
