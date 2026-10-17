# Besoins de format relevés par le lot A (carrefours et rues de Meylan)

*`recon/generateur/meylan/BESOINS_FORMAT.md` — 17/10/2026. Ce que les huit descriptions du lot A (`INDEX_SITES.md`)
doivent dire et que le format de `description/FORMAT_DESCRIPTION.md`, complété par l'extension réseau du lot voisin
« étape 2 » (`description/carrefours.py`, version `carrefours/1.0` : clés racine `troncons`, `carrefours`,
`giratoires`, `bretelles`), ne sait pas encore porter. Rien n'est modifié dans `description/` (lot voisin) : c'est une
liste de besoins chiffrés, avec les sites et les règles concernés. Les besoins communs avec le lot B renvoient à
`BESOINS_FORMAT_AUTO.md` (B1 à B17).*

## 0. Ce qui marche déjà

Les 8 descriptions **compilent** avec le compilateur du dépôt importé sans modification (17/10/2026, 23 h) :
0 erreur de validation, 0 non-conformité non admise ; les écarts aux règles des cas réels sont dits dans
`ecarts_admis` avec leur preuve (coupe, photo). Ce qui manque est **décrit en commentaire** dans le YAML et dans
`DESCRIPTION.md` (§ 4 « Ce que la description simplifie »), jamais inventé.

Constats sur le compilateur pendant le relevé (pour le lot « étape 2 », sans action de ma part) :

| Constat | Site | État |
|---|---|---|
| `ilots[*]` : propriété `porte_par_profil` refusée par le schéma (3 erreurs de validation) | paquet_jardin | corrigé par le lot voisin pendant le relevé (0 erreur à 23 h) |
| déflexion des giratoires rendue à 10 000 m (non conforme) | rp_lycee, rp_didcot | corrigé pendant le relevé (21 à 37 m, conformes) ; l'écart admis provisoire a été retiré |
| un « tout droit » n'existe qu'entre branches à moins de 45° de l'alignement : un plan de feux qui cite `chamrousse TD` est refusé | verdun_lycee_feux | normal ; à documenter dans FORMAT_DESCRIPTION.md |

## 1. Besoins

| # | Besoin | Syntaxe proposée | Sites | Règles, sources |
|---|---|---|---|---|
| A1 | **Traversée revêtue automatique au droit d'un passage** : chaque passage qui aboutit sur une bande enherbée ou plantée exige aujourd'hui deux évènements `profil` (avant et après) qui recopient tout le profil pour remplacer la bande par un trottoir ; c'est arrivé sur 7 sites sur 8 | `passage: {largeur: 4, liaisons: revêtues}` (ou évènement `passage_pieton: {liaisons: revêtues}`) : la bande traversée devient `chemin` revêtu sur la largeur du passage + 2 × 0,50 m, au niveau de la bande voisine | paquet_jardin, rp_didcot, verdun_centre_feux, vieux_chene_taillefer_feux, vieux_chene_inovallee_piste, verdun_lycee_feux | RF-MA-TRO-001, RF-MQ-PP-04 ; règle « aboutissement sur une surface piétonne » du compilateur |
| A2 | **Traversée cyclable d'une branche** (à côté du passage piéton) avec son style : IISR (doubles chevrons, figurines, flèches ½), bande verte, damier, pavés Chronovélo ; style non IISR seulement s'il est photographié | `branches[*].traversee_cyclable: {largeur, style: iisr\|vert\|damier\|chronovelo, cote: amont\|aval, preuve: "photo:<id>"}` → schéma `carrefours[*].traversees_cyclables` (existe) | paquet_jardin (vert, 119d9094 ; pavés jaunes Chronovélo, 22c050a5), verdun_centre_feux (vert, de22683a), vieux_chene_taillefer_feux (vert, ad0b728e), vieux_chene_inovallee_piste (figurines + chevrons, 7d44455e) | RF-MQ-CYC-03, RF-MA-CAR-006, RF-OBS-MAR-01, RF-OBS-CYC-03 ; synthèse § 0.1 ; = B8 du lot B (damier) |
| A3 | **Îlot peint rempli de couleur sans hachures** (résine ocre, pratique de Meylan) | `zone peinte 2,3 ocre` dans le profil, ou `zone hachurée 2,3 remplissage ocre` ; matériau `resine_ocre` (le vocabulaire a déjà `enrobé ocre`) | vieux_chene_inovallee_piste (7d44455e, 17826b13) | RF-OBS-ILO-03 (« différent » de l'IISR7 p. 6) ; DEF-020 |
| A4 | **Îlot central de giratoire composé** : couronne en matériau composite (pavés rouges + rangs de galets ; béton + rang de pavés), muret de soutènement (hauteur), butte ou massif boisé surélevé, sentier intérieur, œuvre d'art (mâts), B21-1 avec panonceau nominatif ; ligne continue de bord d'îlot oui / non | `ilot_central: {remplissage: butte plantée, muret: 0.6, sentier: {rayon: 15.3}, oeuvre: mâts}`, `couronne: {largeur: 2, materiau: pavés rouges, galets: 2 rangs}`, `ligne_ilot: oui`, `b21_1: {panonceau: "ROND POINT DE DIDCOT"}` | rp_lycee (3d7dd376, a23479c9), rp_didcot (25cbe3d8) | RF-GV-GIR-006, RF-OBS-GIR-03, -04, -05, -06 ; DEF-024 |
| A5 | **Bras de giratoire en entrée seule et sortie seule** séparés par un grand îlot (deux bras distincts pour une même route) : le compilateur contrôle chaque bras comme une branche complète (« entrée à 1 voie », « sortie à 1 voie ») et il faut des écarts admis | `branches: [{troncon: vc_est_entree, entree_seule: oui, paire: vc_est_sortie, ilot: {remplissage: gazon}}]` (CLES_BRANCHE_GIR a déjà `entree` / `sortie` : à documenter) | rp_didcot (7 bras), rp_lycee (accès est) | RF-GV-GIR-010, -012, -013 |
| A6 | **Plan de feux supposé** : un plan non observé est aujourd'hui tracé `description:` (comme une valeur dite) ; il devrait porter `choix:` et une confiance faible | `feux: {source: hypothese, ...}` → `prov.src = "choix:hypothese"`, `conf: faible` | paquet_jardin, vieux_chene_taillefer_feux, vieux_chene_inovallee_piste, verdun_lycee_feux | DEF-028 ; PLAN_GENERATEUR § 2.1 (« Houdini n'invente rien ») |
| A7 | **Provenance par valeur** (aujourd'hui en commentaire `# coupe:… photo:… osm:…`) | = B16 du lot B : `provenance: {"<chemin YAML>": "mesure:coupe:verdun_ne_40" \| "photo:20d1a815" \| "osm:way/…"}` | les 8 sites | PLAN_GENERATEUR § 6.2 |
| A8 | **État de chantier** (option datée) : séparateurs K16, clôtures, cônes, panneau « ROUTE BARRÉE », panneau à chevrons, ligne jaune provisoire, emprise fermée en grave | `chantier: {date: 2025-08-31, emprises: [{troncon, de, a, cote}], marquage_provisoire: [...], equipements: [K16, cone, cloture, K8]}` (jamais appris comme état permanent) | paquet_jardin (31/08/2025 : 10ec04d5, e96ea4be, 22c050a5, 4c652c50) | RF-OBS-MAR-03 ; IISR 8e partie (non traitée, synthèse § 18) |
| A9 | **Contre-allée** : voie de desserte parallèle, à sens unique, séparée de la chaussée principale par une bande plantée et une piste | bande `contre-allée 3,5 ←` (type `voie_desserte`, hors trafic de transit, sans axe) | avenue_7_laux_separateur (coupe t0 / t_sw), rp_lycee (mairie_42) | RF-OSM-PRF-001 ; = B4 du lot B (éléments parallèles) |
| A10 | **Séparateur central construit** : muret béton plein (≈ 0,8 m), caniveau central en pavés entre deux bordures, séparateur bordé de 0,26 à 1,55 m qui n'est pas une « bordure séparatrice » de piste | `séparateur 1,5 muret 0,8` / `séparateur 1,5 caniveau pavé` (limite) | avenue_7_laux_separateur (c531e1b2), rp_lycee (sept_laux_45, f4a9aa12), vieux_chene_taillefer_feux (e_30) | RF-OSM-LAR-033 (pris pour la bordure séparatrice de piste : écart admis à chaque fois) ; = B3 du lot B |
| A11 | **Arrêt de bus en alignement sur trottoir large ou derrière une bande** (abri, poteau, zigzags jaunes), aux carrefours | évènement `arret_bus` admis sans quai contigu à la chaussée : `{cote, abri: oui, zigzag: oui, quai: non}` | paquet_jardin (7dcdf1d1), rp_lycee (770c2fc8), vieux_chene_inovallee_piste (17826b13) | RF-MA-BUS-*, DEF-019, DEF-032 ; = B4 du lot B |
| A12 | **Passages inférieurs piétons / cycles** sous l'anneau ou la chaussée (trémie, murets, garde-corps sur muret) | `ouvrages: [{type: passage_inferieur, sous: anneau, largeur, garde_corps}]` | rp_lycee (OSM path layer=-1 ×4 ; 3d7dd376, ea409889) | RF-GV-PON-*, DEF-033 ; = B5 du lot B |
| A13 | **Mobilier et équipements de couleur locale** : barrières bordeaux à croisillons, potelets, candélabres doubles à décor lumineux, mâts de D21 groupés, panneau d'autoroute bleu, borne incendie, caméra sur mât de feux | `equipements: [{type: barriere_croisillons, couleur: bordeaux, limite, de, a}, {type: d21_groupes, branche, textes: [...]}]` | avenue_7_laux_separateur, vieux_chene_taillefer_feux, rp_didcot, verdun_centre_feux | RF-OBS-SIG-05, RF-OBS-ECL-01 ; dossier 13 § 2.9 ; = B6 du lot B |
| A14 | **Revêtement fissuré avec réseau de pontages** (décalques), enrobé rapiécé localisé, faïençage des bandes de passage | `materiaux: {chaussee: {base: enrobé usé, pontages: dense, rapiecage: [zones]}}`, `marquages: {faiencage: oui}` | les 8 sites (le plus fort : avenue_7_laux_separateur, verdun_centre_feux, vieux_chene_taillefer_feux) | RF-OBS-REV-01 |
| A15 | **Plantations d'îlots et de bandes** : butte basse d'arbustes couvre-sol, haie libre, massif boisé ; le profil ne connaît que `gazon` / `planté` / `arbres` | `terre-plein 3,3 butte arbustes 0,6` → schéma `terre_plein.plantation.strates` (existe), plafond 0,60 m dans les triangles de visibilité | verdun_lycee_feux (921c90d1), rp_lycee, rp_didcot, vieux_chene_taillefer_feux (fccb6997) | DEF-029, RF-GV-TPC-011, RF-OBS-ILO-04 |
| A16 | **Bordures à joints peints en blanc** (pratique locale) | `bordure T2 joints peints` (attribut de matériau) | rp_lycee (770c2fc8, a23479c9) | — (observation) |
| A17 | **Tirets de guidage observés hors des cas de l'art. 117-1** (prolongement des voies dans un carrefour à feux) : les décrire comme un écart observé, sans qu'ils deviennent une règle | `guidage: {observe: oui, mouvements: [...], conforme: non, preuve: "photo:5922e7b4"}` | verdun_lycee_feux (dossier 13 M08 : « différent ») | IISR7 art. 117-1 p. 36, RF-OBS-FEU-02, ARB-08 |
| A18 | **Carrefour de chaussées séparées** (plusieurs nœuds de feux, liaisons internes `primary_link`) décrit comme un seul carrefour | `carrefours[*].noeuds_osm: [...]` et branches à entrée / sortie sur deux chaussées distinctes | verdun_lycee_feux (4 nœuds de feux), vieux_chene_taillefer_feux | = B1 du lot B (chaussées séparées) |
| A19 | **Étapes de construction** (ordre du chantier procédural) | = B12 du lot B : `etapes: ["1 plate-forme", "2 chaussées", …]` ; l'ordre est écrit dans chaque `DESCRIPTION.md` § 2 | les 8 sites | — |
| A20 | **Branche à double profil** (chaussée qui s'élargit vers le carrefour, voie qui naît) avec transition relative au profil précédent | = B13 du lot B (`par_rapport_a: precedent`) | paquet_jardin (Verdun NE : zone hachurée à 40 m, pas à 80 m), avenue_7_laux_separateur | RF-GV-VS-010, RF-MQ-OBL-02 |

## 2. Ordre de construction suivi par les descriptions du lot A

Chaque `DESCRIPTION.md` donne, § 2, l'ordre du chantier procédural ; il est le même pour les carrefours urbains :

1. plate-forme et nivellement (z RGE ALTI au centre, pentes) ;
2. chaussées (bitume) des branches et zone de conflit ;
3. bordures, îlots et séparateurs (nez, abaissés, BEV) ;
4. trottoirs, pistes, bandes enherbées ou plantées, liaisons revêtues aux passages ;
5. marquages (lignes, flèches d'affectation, lignes d'effet, passages, traversées cyclables) ;
6. signalisation verticale et feux ;
7. végétation, mobilier, éclairage ;
8. options datées (chantier).
