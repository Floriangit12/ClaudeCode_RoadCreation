# Description simple d'un tronçon : format proposé (`description_simple/0.1`) et catalogue S01-S12

*`recon/generateur/scenes_simples/FORMAT_PROPOSE.md` — lot « catalogue », 17/10/2026. Proposé au lot L0 tant que
`recon/generateur/description/FORMAT_DESCRIPTION.md` n'existe pas ; aligné sur le vocabulaire que le compilateur L0
(`description/description_vers_modele.py`) accepte déjà (§ 8).*

## 1. Principe

Une description simple est ce que l'on écrit en regardant une photo ou un plan : « rue 1 + 1 à 50, trottoirs de 2 m,
bordures T2, passage piéton à 48 m, dos-d'âne juste après ». Elle dit **quoi** et **où** ; les cotes de détail
(nombre de bandes d'un passage, position des flèches, modulation et phase des tirets, rampants, BEV, hachures…)
sont **déduites des règles** de `assets/specs/route/regles_route_fr.json`. Une valeur écrite dans la description est
reprise telle quelle (provenance `description:<champ>`) ; une valeur non écrite vient de la règle qui la fixe
(`defaut:DEF-…`, `inference:RF-…`) ; s'il n'y a ni l'une ni l'autre, on s'arrête (Houdini n'invente rien).

Dans le catalogue, chaque valeur écrite cite en commentaire la règle qui la justifie (`# DEF-004, RF-OSM-LAR-020`) ;
`catalogue.py` vérifie que tous les identifiants cités existent dans la base.

Fichier YAML (sous-ensemble lu par `yaml_simple.py`, identique à ce que lirait PyYAML ; booléens `true`/`false` ou
`oui`/`non`, jamais `yes`/`no`).

## 2. Clés de premier niveau

| Clé | Obligatoire | Contenu |
|---|---|---|
| `format` | oui | `description_simple/0.1` |
| `scene`, `nom`, `titre` | oui | identifiant court (`S08`), nom de fichier, titre lisible |
| `description` | non | une phrase, telle qu'on la dirait |
| `contexte` | oui | `agglomeration` (oui/non), `vitesse_kmh`, `V15_kmh` (défaut : la vitesse, plafonnée par RF-MQ-PS-02), `categorie` (rue, avenue, departementale…), `u_m` (défaut DEF-001) |
| `marquages` | non | `{usure: légère | moyenne | forte}` (aspect, sans effet géométrique) |
| `trace` | oui | ligne de référence de s = 0 à la fin : `- droite: 100`, `- arc: {rayon: 60, angle: 60, sens: gauche}` |
| `profil` | oui | bandes et limites de gauche à droite (§ 3) |
| `evenements` | non | points singuliers le long de s (§ 4) |
| `objets` | non | objets répétés le long d'une bande (§ 5) |
| `abords` | non | `{gauche: pelouse 6, droite: prairie 6}` : type et largeur (m) au-delà du profil |
| `attendus` | oui (catalogue) | une ligne `{clé: valeur, …}` de ce qui doit apparaître, comparée au calcul (§ 6) |

Conventions : s croissant le long du tracé ; t positif à gauche ; ligne de référence = séparation des sens (milieu du
terre-plein s'il y en a un ; sens unique : limite du milieu des voies), comme RF-OSM-PRF-010 et le lot L0.

## 3. Profil en travers

Liste ordonnée de gauche à droite (en regardant vers s croissant), alternant **bandes** et **limites** :

```yaml
profil:
  - {bande: trottoir, largeur: 2.00, materiau: enrobe_trottoir}
  - {bordure: T2, vue: 0.14, caniveau: CS2}
  - {bande: voie, sens: arriere, largeur: 3.00, materiau: enrobe_bbsg_ancien}
  - {ligne: T'1, largeur_u: 2}
  - {bande: voie, sens: avant, largeur: 3.00}
  - {bordure: T2, vue: 0.14, caniveau: CS2}
  - {bande: trottoir, largeur: 2.00}
```

- **Bande** : `bande` (voie, voie_bus, bande_cyclable, piste_cyclable, stationnement, trottoir, terre_plein, bdg,
  bdd, surlargeur, separateur, bande_plantee, berme), `id` (facultatif ; sinon abréviation + rang : `v1`, `tr2`),
  `sens` (avant | arriere ; obligatoire pour une voie), `largeur` (m, **entre les axes des deux limites**, comme
  OpenDRIVE et `modele_voie` ; loi `[[s, l], …]` possible), `materiau` (id de `assets/specs/materiaux_sol.json` ;
  omis = celui de la bande précédente de même type), `niveau` (trottoir | chaussee) ou `dz` (m) si la bande n'est
  pas au niveau que la bordure voisine donne.
- **Limite** : `{bordure: T2, vue: 0.14, caniveau: CS2}` (profil NF du catalogue `RF-AS-profil_*`, caniveau côté
  bas) ; `{ligne: T'1, largeur_u: 2}` (continue, T1, T'1, T2, T'2, T3, T'3, T4 ; couleur blanc par défaut) ;
  `{ligne: aucune}` (ni bordure ni marquage, changement de revêtement seulement). Deux bandes écrites de suite sans
  limite : limite à déduire par les règles (lot L0).
- **Niveau** : bande de chaussée à 0 ; une bande haute prend la vue de la bordure qui la sépare de la chaussée
  (RF-OSM-NIV-010, DEF-005).

## 4. Évènements (le long de s)

Chaque évènement est `- type: {a: S, …}` ; **`a` est l'abscisse du milieu** de l'objet, sauf mention.

| Type | Paramètres (défauts par règle) | Ce que le calcul en déduit |
|---|---|---|
| `passage_pieton` | `a` milieu ; `largeur` = longueur des bandes (DEF-011 : 4,00) ; `abaisses: oui` ; `pente_rampants_pct` (5, DEF-031) ; `bev: oui` | n = ⌊W − 0,5⌋ bandes de 0,50, e = (W − 0,5 n)/(n + 1) (DEF-011, RF-MQ-PP-02, -05) ; lignes coupées à 0,50 m (RF-MQ-PP-03) ; abaissés vue 0,02 de la largeur du marquage, rampants latéraux Δh / pente ; BEV 0,5875 à 0,50 du nez (DEF-031) |
| `dos_d_ane` | `a` milieu ; `longueur` 4,00, `hauteur` 0,10 (RF-MA-RAL-001) | 3 triangles 0,70 × 2,00 par voie sur la moitié montante (RF-MQ-RAL-01) ; axe T3 2u sur le ralentisseur ± 10 m si chaussée bidirectionnelle ≥ 5 m ; refus d'un passage dessus |
| `plateau` | `a` milieu ; `longueur` du dessus (2,50-4,00), `hauteur` 0,10, `rampe_pct` 7 (RF-MA-RAL-001, DEF-034) ; `passage_pieton: oui` ; `bev` | ralentisseur trapézoïdal : rampants h / pente ; bandes = dessus + 2 × 0,50 et pas de triangles (RF-MQ-PP-04) ; abaissé = vue − h au droit du dessus |
| `rabattement` | `a` = **point de fin du rétrécissement physique (PCF)** ; `biseau` = longueur Lp de ce rétrécissement ; `voie: gauche | droite | id` ; `sens` ; `fleches: oui` + `nombre_fleches` ; `zebra: oui` ; `elargit` (bande qui récupère la largeur ; défaut : celle au-delà de la bordure) | oblique continue 3u de longueur max(Lp, L), finissant au PCF (RF-MQ-OBL-02, RF-MQ-LAR-A1c), raccordée au nez de bordure à ses deux bouts ; L = f(V15) (RF-MQ-PS-03) ; flèches RAB_D dans l'axe de la voie supprimée à L, L − i1, L − i1 − i2 **du milieu de l'oblique** (RF-MQ-RAB-04, -05, -07) ; zébra (DEF-020) ; ligne de voie arrêtée à 2u de l'oblique [G] |
| `zone_depassement_interdit` | `a` = début de la continue axiale ; `sens` | annonce T3 2u de longueur L avant `a`, continue 2u après, 3 flèches RAB_D à cheval sur l'annonce (RF-MQ-PS-04, RF-MQ-RAB-02, -03, -05) |
| `fleches` | `type` (TD, TAD, TAG, TD_TAD, TD_TAG) ; `voies: toutes | [ids]` ; `a` = pied de la 1re flèche ; `nombre` (3) et `interdistance` (20) de DEF-017 | gabarits exacts du dossier 08 au milieu de chaque voie, même profil en travers (RF-MQ-DIR-03, -04, -09) |
| `inscription` | `a` = ligne de base ; `texte` ; `voie` ; `hauteur` (1,50 si V ≤ 50) | glyphes de l'annexe D (série V ≤ 70), espacement 0,15, centrés dans la voie, pied côté conducteur |

## 5. Objets le long d'une bande

| Type | Paramètres | Déduit |
|---|---|---|
| `avancees_plantees` | `bande` (stationnement) ; `de`, `a`, `pas` (centres) ; `longueur` ; `bordure` ; `sol` ; `arbre: {t_depuis_voie, houppier_rayon}` | avancées de trottoir entre les places, bordure sur 3 côtés, arbre à `t_depuis_voie` du bord de la voie (DEF-030) ; places = intervalles ; bordure principale, caniveau et ligne T'2 interrompus au droit des avancées |
| `arbres` | `bande` ; `de`, `a`, `pas` ; `houppier_rayon` | arbres dans l'axe de la bande (DEF-030) |
| `figurines` | `gabarit` (VELO) ; `bandes` ; `a: [s…]` | figurine dans l'axe de la bande, tournée dans le sens de circulation (DEF-018, RF-MA-CYC-012) |

## 6. Ligne « attendus »

Une ligne YAML `attendus: {…}` écrite à la main (calcul dans les commentaires) ; `catalogue.py` recalcule chaque
clé et le contrôle `attendus` exige l'égalité (± 0,001). Clés disponibles :

| Clé | Définition |
|---|---|
| `longueur`, `largeur_emprise`, `largeur_chaussee` | m ; emprise et chaussée (bord à bord des bordures ou des surlargeurs) à s = 0 |
| `voies` | nombre de voies par sens à s = 0 |
| `traits` | `{"T'1 2u": 16, …}` : nombre de tirets peints par modulation et largeur (phase : chaque segment commence par un trait ; un trait tronqué en fin de segment n'est peint que s'il fait au moins la moitié d'un trait [G]) |
| `continues_m` | longueur peinte des continues par largeur |
| `bordures_m`, `bordures_avancees_m` | longueur de bordure par profil (le long du nez), hors interruptions ; bordures des avancées |
| `fleches`, `fleches_s` | nombre par gabarit ; abscisses des pieds (par voie puis s) |
| `passages` | `[{s, W, bandes, e, longueur_bandes}]` |
| `triangles`, `abaisses`, `bev`, `arbres`, `avancees`, `places`, `figurines`, `inscriptions`, `hachures`, `aplats` | décomptes |
| `oblique` (`L`, `s0`, `s1`, `PCI`, `Lp`), `annonce` (`L`, `s0`, `s1`), `rayons` | géométrie des points singuliers |

## 7. Choix du générateur (non fixés par les textes, marqués [G])

- Phase des tirets : chaque segment de ligne commence par un trait (l'IISR ne fixe pas la phase) ; trait final gardé
  s'il fait au moins la moitié d'un trait.
- Coupures de lignes : la partie en aval d'une coupure (passage, avancée) recommence par un trait.
- Espace minimal entre deux marques distinctes (flèche / oblique, ligne de voie / oblique) : 2u, par analogie avec
  l'espace non peint de RF-MQ-MUS-01 (aucune règle n'en fixe).
- Oblique de réduction raccordée au nez de bordure à ses deux bouts (passe sur le caniveau CS, affleurant).
- Hachures : la première bande part du point où la zone atteint 0,30 m (phase non fixée, DEF-020).

## 8. Correspondance avec le compilateur du lot L0 (état du 17/10/2026, 01 h 50)

Le compilateur L0 lit déjà : le profil structuré (`{bande: …}`, `{bordure: …}`, `{ligne: …}`, `{ligne: aucune}`),
`trace` au premier niveau, `titre`, `attendus` (gardés dans le rapport), `evenements` avec `a`, `passage_pieton`,
`dos_d_ane`, `plateau`, `rabattement` (`biseau`), `abords` « pelouse 6 », `marquages.usure`, `categorie`
departementale. Essai sur les 12 descriptions (`--sortie recon/generateur/tmp/catalogue/l0/…`) : **8 compilent
sans erreur de validation** (S02, S03, S04, S06, S08, S09, S10, S11). Ajouts demandés au lot L0 :

1. évènements `zone_depassement_interdit` (S01), `fleches` (S07), `inscription` (S12) ;
2. `nombre_fleches` (entier) pour `rabattement` ;
3. bande `separateur` avec `dz` ou `niveau: trottoir` suivie d'une `bordure` (S05 : bande pavée au niveau du
   trottoir, contre la bordure T2) — aujourd'hui refusé (« deux bandes au même niveau ») ;
4. `objets` (avancees_plantees, arbres, figurines) en plus de `vegetation` ;
5. **écart de règle sur `rabattement`** : pour S09 (Lp = 19,5 < L = 39), L0 place 3 flèches à 35,25 / 61,25 /
   74,25 m, comptées depuis le milieu du biseau **physique** ; l'IISR (115-4 A, schémas p. 22, 34) et RF-MQ-OBL-02,
   RF-MQ-RAB-04, -07 font partir les distances du milieu de l'**oblique marquée**, de longueur L et finissant au PCF
   (ici 45 → 84, milieu 64,5) : flèches à 25,5 et 51,5 m ; la 3e (d = 0, case vide du tableau p. 22) tomberait dans
   le zébra (marge −0,74 m) → 2 flèches (exception d'agglomération, RF-MQ-RAB-03) ;
6. `plateau` + passage : bandes = dessus + 2 × 0,50 (RF-MQ-PP-04), pas seulement la longueur du plateau ;
7. le biseau par défaut 37 × d (RF-GV-PT-014, ARP, interurbain) n'est pas une règle d'agglomération.

## 9. Outils et sorties

```
python -B recon/generateur/scenes_simples/catalogue.py [--sans-png] [--verifier-determinisme]
```

- `description.py` : lecture, normalisation, géométrie de contrôle, mesures, contrôles (règles citées existantes,
  matériaux, largeurs, vues, passages, abaissés, ralentisseurs, flèches, arbres, attendus) ;
- `plan_svg.py` : plan coté SVG (bandes, bordures, caniveaux, abaissés, BEV, marquages aux gabarits exacts, arbres,
  chaînes de cotes transversales et longitudinale, chaînage, cartouche) → `plans/S??_*.svg` ;
- PNG (PyMuPDF) et vues de détail ×3 → `recon/out/generateur/catalogue/{plans_png,details}/`, tuiles natives
  (`recon/pcg/vision/decoupe.py`) → `recon/out/generateur/catalogue/tuiles/` ;
- rapport : `recon/generateur/validation/rapport_catalogue.json` et `RAPPORT_catalogue.md`.

## 10. Catalogue

| Scène | Fichier | Ce qu'elle éprouve |
|---|---|---|
| S01 | `S01_route_1x1_hors_agglomeration.yaml` | route 70 km/h sans bordures, accotements enherbés, rives T2 3u, axe T1 → annonce T3 + 3 RAB_D → continue |
| S02 | `S02_rue_1x1_bordures_trottoirs.yaml` | rue 1 + 1, T2 + CS2, trottoirs 2 m, axe T'1 |
| S03 | `S03_rue_stationnement_arbres.yaml` | S02 + stationnement longitudinal à droite (T'2), avancées plantées et arbres tous les 7,50 m |
| S04 | `S04_rue_bandes_cyclables.yaml` | bandes cyclables T3 5u des deux côtés, figurines |
| S05 | `S05_rue_pistes_sur_trottoir.yaml` | pistes unidirectionnelles au niveau du trottoir, séparées par revêtements contrastés |
| S06 | `S06_avenue_2x2_terre_plein_plante.yaml` | 2 × 2 voies, BDG, continues 3u, TPC planté de 4 m bordé de T2, arbres |
| S07 | `S07_rue_sens_unique_2_voies.yaml` | sens unique 2 voies, 3 flèches TD par voie |
| S08 | `S08_rue_dos_d_ane_passage.yaml` | 30 km/h, passage avec abaissés et BEV, dos-d'âne et triangles, axe T3 ± 10 m |
| S09 | `S09_reduction_2_vers_1_voie.yaml` | réduction 2 → 1 : oblique L, zébra, rétrécissement physique, 2 flèches RAB_D |
| S10 | `S10_rue_plateau_passage.yaml` | plateau trapézoïdal portant un passage, vue 0,12 → abaissé 0,02, BEV |
| S11 | `S11_rue_courbe_R60.yaml` | seule courbe : droite + arc R 60 m sur 60° + droite |
| S12 | `S12_couloir_bus.yaml` | voie générale + couloir bus (continue 5u), BUS au sol |
