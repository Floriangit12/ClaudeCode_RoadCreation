# Besoins de format relevés par le lot B (autoroute A41, N87, grands axes de Meylan)

*`recon/generateur/meylan/BESOINS_FORMAT_AUTO.md` — 17/10/2026. Ce que les descriptions des sites `auto_*` et
`axe_*` doivent dire et que le format de `description/FORMAT_DESCRIPTION.md` (compilateur de l'étape 1, en cours
d'extension par le lot « étape 2 ») ne sait pas encore porter. Chaque `description.yaml` du lot B garde la partie au
format existant (elle compile : `auto_outils/tester_descriptions_lotB.py`) et range le reste sous la clé racine
**`extensions_auto`**, avec la syntaxe proposée ci-dessous. Ce fichier ne modifie rien du compilateur : c'est une
liste de besoins chiffrés, chacun avec les sites qui en ont besoin et les règles concernées
(`assets/specs/route/regles_route_fr.json`).*

État des 7 descriptions au 17/10/2026 (partie au format existant, compilateur du dépôt importé sans modification) :
7 / 7 compilent, 0 non-conformité bloquante, avertissements expliqués dans chaque `mesures.json`.

| # | Besoin | Syntaxe proposée (`extensions_auto`) | Sites | Règles |
|---|---|---|---|---|
| B1 | **Chaussées séparées** : dire qu'un profil porte deux sens séparés (entraxe, nature de la séparation) ; distinguer une chaussée unique à îlot peint que OSM trace en deux ways (piège RF-OSM-PRF-011) | `chaussees_separees: {entraxe_m, separation, tronçons}` | tous | RF-OSM-PRF-011, RF-MQ-SC-05/-06 |
| B2 | **Raccordements entre tronçons** : divergence (sortie, bifurcation), convergence (entrée, juxtaposition 2 + 2), continuité d'un site à l'autre ; voie quittante (décélération) ou entrante (insertion) ; **musoir** : zone de chevrons (longueur), nez (abscisse), balise J14a | `raccordements: [{type: divergence/convergence/continuite, de, a, vers, a_vers, sens, voie_quittante, voie_entrante, musoir: {chevrons, longueur_zone_m, nez_a, balise}, mode}]` | auto_a41_echangeur_meylan_est, auto_noeud_a41_n87, auto_a41_extremite_ouest | RF-MQ-INS-01 à -03, RF-MQ-DEC-01/-02, RF-MQ-MUS-01, RF-MQ-HACH-02, RF-SV-J5 |
| B3 | **Dispositifs de retenue avec emprise et position** : GBA comme bande (base 0,6, hauteur 0,8 ; aujourd'hui écrite « demi-bande béton | GBA | demi-bande ») ; glissière simple ou double décalée dans une bande (à 0,5 m dans l'herbe du TPC), contournant une pile ; muret ; haie taillée comme bande de largeur donnée | `dispositifs_retenue: [{limite, type: GBA_double_face/glissiere_simple/glissiere_double/muret, hauteur_m, largeur_base_m, decalage_m, de, a, contournement_pile}]` | tous les `auto_*`, axe_verdun_ouest (haie) | RF-GV-TPC-002/-003/-008, RF-GV-PON-009/-010, RF-OBS-TPC-01 |
| B4 | **Éléments parallèles hors du profil courant** : piste et trottoir à 15-20 m de l'axe au-delà d'accotements ; arrêt de bus sur accotement (le format exige un trottoir contigu) ; aire de service ; route de liaison à double sens portée par un pont | `pistes_laterales`, `arrets_bus`, `aire_de_service`, `route_de_liaison` | axe_verdun_ouest, axe_verdun_centre, auto_n87_rocade_sud, auto_a41_echangeur_meylan_est | RF-MA-BUS-*, RF-MA-PIS-001/-002 |
| B5 | **Ouvrages** : passage supérieur (abscisse, biais, largeur et profil du tablier, appuis : pile dans le TPC, culées perrées, tirant d'air, garde-corps), pont portant une bretelle, tunnel court | `ouvrages: [{type: passage_superieur/pont/tunnel_court, a, biais_deg, largeur_tablier_m, profil_tablier, appuis, tirant_air_m, garde_corps}]` | auto_a41_section_courante, auto_a41_echangeur_meylan_est, auto_noeud_a41_n87 | RF-GV-PON-001 à -015, DEF-033 (lot L8) |
| B6 | **Équipements** : éclairage (implantation, hauteur, crosse, pas), clôture autoroutière, ligne HT, borne d'appel d'urgence | `equipements: [{type, cote, hauteur_m, pas_m, a}]` | tous | RF-OBS-ECL-01, RF-MQ-PAU-01 |
| B7 | **Terrain et végétation hors profil** : talus montant / descendant (hauteur, pente, végétation), haie taillée, alignement de grands arbres derrière une glissière | `talus`, `vegetation` | auto_a41_section_courante, axe_verdun_* | RF-OSM-VEG-001, RF-OBS-VEG-01 |
| B8 | **Marquages détaillés** : changer la modulation d'une seule ligne sur un intervalle (T1 → T3 de dissuasion) sans redéclarer tout le profil ; flèche de rabattement isolée observée (le format impose 2 ou 3) ; traversée cyclable en damier (pratique locale relevée) ; poche de tourne-à-gauche ouverte dans un îlot peint | `marquages_detail`, `traversees`, `ouvertures_tag` | auto_a41_section_courante, auto_a41_extremite_ouest, axe_verdun_* | RF-MQ-DEC-02, RF-MQ-RAB-03, RF-OBS-CYC-*, RF-MQ-DIR-01 |
| B9 | **Signalisation autoroutière** : D41a / D41c, portique (éventuellement porté par un ouvrage), PMV, J14a, J4, AB3a + panonceau sur une voie qui disparaît ; position « au-dessus » | `signalisation: [{code, texte, troncon, a, cote: droite/gauche/au-dessus/nez, porte_par}]` | tous les `auto_*` | RF-SV-DIM.CHOIX_GAMME, RF-SV-GEN.REPETITION_GAUCHE_2X2, RF-SV-J5 |
| B10 | **Vitesse par sens** (110 vers l'est, 90 puis 70 vers l'ouest sur le même tronçon) | `vitesses: [{sens, de, a, kmh}]` | auto_a41_extremite_ouest | RF-OSM-VIT-003 |
| B11 | **Début / fin d'autoroute** (C207 / C208 des deux côtés, B14, raccord à un carrefour à feux) | `extremite: {a, sens_est, sens_ouest, carrefour}` | auto_a41_extremite_ouest | IISR5 (C207, C208) |
| B12 | **Étapes de construction** : ordre du chantier que le PCG suit (plate-forme → ouvrages → chaussées → TPC → retenue → marquages → signalisation → équipements → abords) | `etapes: ["1 …", "2 …"]` | tous | — |
| B13 | **Transition relative au profil précédent** : aujourd'hui une transition n'est linéaire que si les bandes sont celles du profil de départ du tronçon ; sinon changement instantané (d'où la coupe en deux tronçons de auto_a41_extremite_ouest) | `profil: {a, transition, par_rapport_a: precedent}` | auto_a41_extremite_ouest | — |
| B14 | **Tracé depuis une polyligne OSM** : ajustement automatique en droites / arcs / clothoïdes (cassures de 2 à 30° dans les bretelles) | `polyligne: …` + `ajuster: arcs` | auto_noeud_a41_n87, auto_a41_echangeur_meylan_est, auto_n87_rocade_sud | RF-GV-DEV-002/-003 |
| B15 | **Niveaux et superpositions** : profil en long, ouvrages superposés (trois niveaux au nœud A41 / N87), passage d'une bretelle sous elle-même | `niveaux: [{troncon, de, a, z_m ou layer}]` | auto_noeud_a41_n87 | RF-OSM-OUV-001 (layer n'est pas une altitude) |
| B16 | **Provenance par valeur dans le fichier** (aujourd'hui en commentaires) : la reporter dans `prov.src` du modèle (`mesure:ortho_ign_2024`, `photo:<id>`, `osm:<way>`) au lieu de `description:<champ>` | `provenance: {"<chemin YAML>": "O …" / "P …" / "OSM …"}` | tous | PLAN_GENERATEUR § 6.2 |
| B17 | **Bretelle comme catégorie** : sur une bretelle, la rive droite est T'3 3u (RF-MQ-SC-06, RF-MQ-LAR-B2d) ; le compilateur avertit qu'il aurait posé T4 3u (RF-OSM-MRQ-022) | `contexte: {categorie: bretelle}` | auto_a41_echangeur_meylan_est, auto_noeud_a41_n87, auto_a41_extremite_ouest | RF-MQ-SC-06, RF-OSM-MRQ-022 |

## Conventions communes des descriptions du lot B

- Repère : `origine` = point L93 de la médiane OSM au début du site ; coordonnées locales en mètres ; tronçon orienté
  dans le sens de l'abscisse croissante ; profil de gauche à droite dans ce sens (la chaussée « ← » est à gauche).
- Provenance : `[O]` ortho IGN BD ORTHO 2024 (09/08/2024, 20 cm, coupes redressées `auto_outils/coupe_ortho.py`),
  `[P]` photo Panoramax (identifiant 8 caractères, `photos.json`), `[OSM]` tag OpenStreetMap (extrait du 17/10/2026),
  `[R]` règle citée, `[G]` choix faute de mesure, `[M27]` description de l'étape 1.
- Lignes mesurées d'axe de ligne à axe de ligne, ± 0,15 m ; bords revêtus ± 0,3 m ; positions le long de l'axe
  ± 10-50 m selon la source (indiqué à chaque valeur).
- Les pratiques locales non conformes (damier jaune Chronovélo) ne sont écrites que là où une photo les montre, avec
  la provenance de la photo (synthèse DocRoute § 0.1).
