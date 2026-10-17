# Rapport du lot L0 : description simple, inférence OSM → modèle, validateur

*`recon/generateur/validation/RAPPORT_L0.md` — 17/10/2026. Données chiffrées : `rapport_L0.json`, produit par
`python recon/generateur/validation/faire_rapport_L0.py` (rejoue tout ; deux exécutions donnent le même fichier à
l'octet). Base de règles lue : `regles_route_fr/1.0` du 17/10/2026, SHA-256 `d4d63ede…`, 857 règles, non modifiée.*

**Statut : ok** — les 12 critères sont atteints.

## 1. Ce que le lot apporte

Étape 1 de la demande de l'utilisateur : décrire une route **simplement**, comme devant une photo, et obtenir un
modèle exact et conforme aux règles françaises, que le générateur Houdini fabriquera aux lots suivants.

```yaml
scene: ma_rue
contexte: {agglomeration: oui, vitesse: 30}
troncon: {de: [0, 0], vers: [120, 0]}
profil: "trottoir 2 béton balayé | bordure T2 granit | voie ← | voie → | stationnement | trottoir 2"
evenements:
  - "à 40 : passage piéton"
  - "à 95 : plateau avec passage piéton"
```

Ce qui est dit est repris (provenance `description:…`) ; tout le reste est complété par la règle qui le fixe et la
cite (voies 3,00 m RF-OSM-LAR-010, bordures 0,14 m DEF-005, axe T'1 2u RF-OSM-MRQ-010, abaissés et BEV DEF-031,
neutralisation du stationnement RF-OSM-STA-002, bandes du passage sur plateau RF-MQ-PP-04…). Une valeur qu'aucune
règle ne fixe doit être dite, sinon la compilation s'arrête ; un mot inconnu est une erreur.

Sur les 24 descriptions compilées (12 exemples + 12 scènes du catalogue voisin), les 2 019 entrées de provenance se
répartissent en 1 138 valeurs dites (56 %), 752 complétées par une règle `RF-*` / `DEF-*` / `ARB-*` (80 règles
distinctes, 1 477 citations), 79 tirées des tables du volet 12 (matériaux, catégories) et 50 calculées ; 124 contrôles
de conformité (largeurs, refuges, cheminement…) tous conformes ; 78 sections.

## 2. Critères

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L0-1 cas de test de tags | 36 | ≥ 32 | oui |
| L0-2 cas donnant le profil attendu (tags, réseaux, validateur) | 56 / 56 | 100 % | oui |
| L0-3 `highway=stop` seul → `stop_a_verifier`, ni AB4 ni ligne ni continue ; + `traffic_sign=FR:AB4` → `stop` (ARB-19) | R03, R14 : stop_a_verifier sans ligne ni AB4 ; R04 : STOP, ligne continue 0,50, continue d'approche 15 m, AB4 | conforme | oui |
| L0-4 validateur : 0 erreur sur les 2 exemples migrés du dossier 12 | 0 | 0 | oui |
| L0-5 validateur, provenance exigée (C01-C13) : 0 erreur sur les sorties | 15 réseaux de test, extrait OSM réel du site, 24 descriptions : 0 erreur | 0 | oui |
| L0-6 C11 rejette un identifiant inconnu (`RF-OSM-LAR-999`) ; refuse un ancien identifiant en donnant sa cible | rejeté ; `OSM-LAR-020 → RF-OSM-LAR-020` | rejeté | oui |
| L0-7 déterminisme (deux exécutions identiques à l'octet) | descriptions 24 / 24, réseaux 15 / 15, extrait OSM réel, migration, rapport | 100 % | oui |
| L0-8 descriptions compilant en modèle valide | 24 / 24 | 100 % | oui |
| L0-9 scènes du catalogue voisin écrites dans le format, attendus vérifiables au niveau du modèle retrouvés | 12 / 12 | 100 % | oui |
| L0-10 faits attendus sur les exemples (règles appliquées, écrits à la main) | 25 / 25 | 100 % | oui |
| L0-11 refus attendus (valeur sans règle, interdits, clés inconnues) | 11 / 11 | 100 % | oui |
| L0-12 sorties écrites dans `recon/out/generateur/<scene>/` | 24 / 24 | 100 % | oui |

## 3. Livrables

| Fichier | Rôle |
|---|---|
| `regles.py` | accès aux règles (`regle`, `defaut`, `arbitrage`, `valeur`, résolution des anciens identifiants par `index_alias`) — repris, vérifié |
| `schema/modele_voie.schema.json` | copie versionnée du schéma du dossier 12 (identique) |
| `schema/valider_modele.py` | validateur corrigé (motifs `RF-…`, `DEF-\d{3}`, `ARB-\d{2}`, `index_alias`, C12 provenance, C13 ARB-19) ; genres de provenance `description`, `osm`, `regle`, `table_volet12`, `solveur` |
| `schema/migrer_exemples.py`, `schema/exemples/` | migration des 2 exemples (97 citations ; ECL-01, ECL-04, ECL-05 sans équivalent, § 5) — reprise, relancée à l'identique |
| `commun/prov.py`, `commun/geometrie.py`, `commun/profil.py` | socle commun : provenance (une règle citée doit exister), ligne de référence (droites, arcs, clothoïdes ; point (s, t)), **construction de profil** partagée par l'inférence et la description (largeurs, niveaux, dévers, bordures, marquages, matériaux, figurines, contrôles) |
| `inference/osm_lecture.py` | lecture OSM XML / PBF / GeoJSON, Lambert-93 — reprise |
| `inference/osm_vers_modele.py` | inférence OSM → modèle : découpe aux nœuds, catégorie, vitesse, voies, bus, cyclables, stationnement, trottoirs, largeurs (dont `width` réparti et signalé hors plage), carrefours et régimes (feux, STOP / ARB-19, cédez, priorité à droite « à vérifier », giratoires), lignes d'arrêt, continue d'approche, flèches `turn:lanes`, panneaux `traffic_sign`, passages, modération, ponts ; un way sans règle applicable est écarté et signalé |
| `inference/tests/cas_tags.json`, `cas_carrefours.json`, `tester_inference.py` | 36 cas de tags, 15 réseaux, 5 tests du validateur |
| `description/FORMAT_DESCRIPTION.md` | **le format**, avec ses tables (bandes, limites, matériaux, évènements, règles qui complètent) et ses exemples |
| `description/description_vers_modele.py`, `format_profil.py`, `vocabulaire.py`, `yaml_simple.py` | compilateur, analyse du profil (forme en ligne et forme structurée), vocabulaire, lecteur YAML sans dépendance (PyYAML absent, rien installé sur C:) |
| `description/exemples/01…12` | route sans bordure en courbe, rue à trottoirs, bandes cyclables et tampon, 2 × 2 à terre-plein refuge, scène E sans carrefour (piste intermédiaire, bande plantée, arrêt de bus en avancée), rabattement, dos-d'âne / plateau / coussins, sens unique et entrées charretières, tourne-à-gauche, changement de profil, description rapide « depuis une photo », piste bidirectionnelle |
| `description/tests/tester_descriptions.py` | compilation et déterminisme des 24 descriptions, faits attendus, attendus du catalogue voisin, refus |
| `validation/faire_rapport_L0.py`, `rapport_L0.json`, `tests_*_L0.json`, ce rapport | rapport du lot |

Évènements du format : passage piéton, dos-d'âne, plateau (avec ou sans passage), coussin, rabattement N → N−1
(biseau, oblique peinte et zébra, trottoir élargi), élargissement N → N+1 (voie, tourne-à-gauche…), zone de
dépassement interdit (annonce, flèches à cheval), flèches directionnelles, inscription, arrêt de bus (quai, zigzag,
poteau, abri, C6), entrée charretière, abaissé, panneau, changement de profil (avec transition). Objets : arbres
d'alignement, figurines, avancées plantées ; abords (pelouse, prairie, champ…).

## 4. Coordination avec le lot catalogue (`scenes_simples/`)

Les 12 scènes S01-S12 se compilent **telles qu'elles sont écrites** (forme structurée `{bande: …}`, `{bordure: …}`,
`{ligne: …}`), en modèle valide, et les attendus que le modèle peut porter sont retrouvés (longueur, emprise, chaussée,
voies, flèches et leurs abscisses, figurines, inscriptions, passages, abaissés, BEV, longueurs de bordure en plan,
bordures d'avancées, oblique). Les attendus de dessin (nombre de traits, hachures, aplats) relèvent du lot L4 et sont
listés comme non vérifiables au lot L0. Les remarques de `RAPPORT_catalogue.md` § « Coordination avec le lot L0 »
sont toutes traitées :

| Remarque | Traitement |
|---|---|
| refus de `zone_depassement_interdit`, `fleches`, `inscription`, `objets`, `nombre_fleches`, séparateur haut + bordure (S05) | ajoutés ; S01, S05, S07, S12 compilent |
| flèches de S09 comptées depuis le milieu du biseau physique | comptées depuis le milieu de l'oblique de longueur L (RF-MQ-RAB-07, RF-MQ-OBL-02) : 25,5 et 51,5 m, comme attendu |
| bandes du passage sur plateau | plateau + 2 × 0,50 m (RF-MQ-PP-04) : 5,00 m pour S10 |
| biseau par défaut 37 × d (ARP, interurbain) appliqué en agglomération | hors agglomération seulement ; en agglomération, faute de règle, pris égal à l'oblique L (RF-MQ-OBL-02, confiance faible) |

Deux défauts du compilateur trouvés grâce au catalogue et corrigés : des clés inconnues (bloc `objets`, paramètres
d'évènements) étaient ignorées en silence (désormais des erreurs) ; en sens unique, la ligne de référence s'appuyait
toujours sur la bordure gauche, si bien qu'un trottoir gauche élargi repoussait la façade (le bord fixe est maintenant
celui opposé à la variation).

## 5. Règles manquantes ou à préciser dans `regles_route_fr.json` (signalées, non modifiées)

1. **Candélabres** : recul du fût derrière la bordure, pas, distance aux arbres (anciennes règles ECL-01, ECL-04,
   ECL-05 des specs du dépôt) : aucune règle équivalente (relevé de migration).
2. **Entrées charretières** : largeur non chiffrée (doit être dite) ; neutralisation du stationnement au droit
   (stationnement gênant, code de la route R417-10) absente : le compilateur ne la fait pas.
3. **Biseau physique en agglomération** (suppression ou ajout de voie) : seules les valeurs ARP (37 × d) et AU70
   (78 m) existent ; un `DEF-*` serait utile (choix actuel : L, confiance faible).
4. **Marge latérale des coussins** (≥ 0,70 m, 0,50 en zone 30, guide « Coussins et plateaux » p. 20-26, cité par
   `PROFILS_EN_TRAVERS.md` § 6) : absente de RF-GV-RAL-001 ; le contrôle s'y réfère sans règle.
5. **Largeur d'une voie centrale banalisée** (`lanes:both_ways`) : aucune règle ; ces ways sont écartés et signalés.
6. **Piste à niveau intermédiaire** : seule une plage [0,02 ; 0,04] (RF-MA-SEP-005) ; milieu retenu, confiance faible
   — un `DEF-*` à fixer. Pas de profil normalisé de bordure chanfreinée dans la base (profil « autre »).
7. **Terre-plein planté sans largeur dite** : minimum de RF-OSM-LAR-050 (2,00 m), confiance faible — un `DEF-*` à fixer.
8. **Vue des îlots / terre-pleins** : DEF-005 « îlot » 0,11 est inférieur à DEF-005 « refuge_min » 0,12
   (RF-MA-REF-003) : un terre-plein traversé par un passage doit être porté à 0,12 au moins ; le compilateur le contrôle
   (l'exemple 04 le dit) mais ne le corrige pas seul.
9. **u des routes `primary`** : la table `highway_vers_categorie` du volet 12 donne 6 cm, RF-OSM-MRQ-001 et
   `INFERENCE_OSM_VERS_PROFIL.md` § 4 ne le posent que si l'itinéraire est déclaré : l'inférence suit RF-OSM-MRQ-001.
10. **Champs absents de `modele_voie/0.1`** (pour une version 0.2) : rayon de houppier, texte et hauteur des
    inscriptions (rangés dans `x-opendrive`), rampes d'un plateau (dans la provenance) ; les valeurs dites sans champ
    sont listées dans `compilation.json` (`non_portes_par_le_schema`).

## 6. Inférence sur des données réelles

Extrait OSM du site Paquet Jardin (`data/sites/paquet_jardin/vector/osm_roads.geojson` + `osm_crossings.geojson`) :
69 routes, 21 profils, 28 carrefours (tous en priorité à droite : l'extrait ne contient aucun nœud de feux ni de STOP),
dont 10 « à vérifier » (rangs de voie différents, RF-OSM-CAR-012), 12 passages ; 0 erreur de validation, sortie
identique à l'octet sur deux exécutions ; 18 avertissements (trottoirs et pistes cartographiés à part, ancien schéma de
stationnement traduit, une largeur de 4,00 m hors plage gardée en confiance faible).

## 7. Limites et suite

- Un tronçon décrit est isolé (pas de carrefour) : c'est l'étape 1 voulue par l'utilisateur ; les carrefours viendront
  avec les lots L3 et suivants.
- Le modèle donne lignes, modulations, intervalles, interruptions, gabarits et ancrages ; le dessin des traits, des
  hachures et des symboles est fait au lot L4 par les HDA `pj::marquage_*` et `pj::symbole_iisr` v2 (gabarits du dossier
  08 : `TRIANGLE_DOS_ANE`, `RAB_D`, `ZIGZAG_BUS_10M_U5`…).
- Prochaine étape : lot L1 (`rg::lire_modele`, `rg::graphe`, `rg::profils`) sur ces modèles ; puis la boucle voulue par
  l'utilisateur — regarder une photo de Meylan (tuiles natives, photos sous `photos_non_versionnees/`), l'écrire dans ce
  format, fabriquer, comparer.

## 8. Rejouer

```
python recon/generateur/validation/faire_rapport_L0.py                      # tout, écrit rapport_L0.json
python recon/generateur/inference/tests/tester_inference.py                 # 56 cas
python recon/generateur/description/tests/tester_descriptions.py            # 24 descriptions, 25 faits, 11 refus
python recon/generateur/description/description_vers_modele.py FICHIER.yaml --verifier-determinisme
python recon/generateur/inference/osm_vers_modele.py ENTREE.osm|.pbf|.geojson… [--agglomeration oui|non|auto]
python recon/generateur/schema/valider_modele.py MODELE.json --exiger-prov
```

Rien n'a été écrit hors de `D:` (quatre petits fichiers temporaires posés par erreur dans le dossier temporaire de la
session sur `C:` ont été supprimés aussitôt) ; `D:\DocRoute` et les specs de l'autre équipe n'ont été que lus.
