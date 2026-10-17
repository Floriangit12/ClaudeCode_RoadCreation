# Relevé de Meylan, lot B : autoroute A41, Rocade Sud N87 et grands axes

*`recon/generateur/meylan/LOT_B_AUTOROUTE_AXES.md` — 17/10/2026. Lot B du relevé de Meylan pour le générateur
procédural (PLAN_GENERATEUR.md § 6) : décrire, à partir de photos Panoramax, de l'ortho IGN et d'OSM, l'autoroute,
ses échangeurs et deux grands axes, d'abord **en texte libre** comme l'utilisateur (« route 2 voies à double sens avec
terre-plein végétalisé… »), puis **en YAML** au format de `description/FORMAT_DESCRIPTION.md`, chaque valeur avec sa
provenance. Les sites du lot A (carrefours urbains) sont les autres dossiers de `meylan/`.*

## 1. Sites

Les quatre sites de l'A41 se raccordent bout à bout (même médiane OSM), la N87 se raccorde au nœud :

```
 La Tronche ── auto_a41_extremite_ouest ── auto_a41_section_courante ── auto_noeud_a41_n87 ── auto_a41_echangeur_meylan_est ── Montbonnot
   (808 m)          s 808 = 0                    s 549,9 = 0                 s 1 217,9 = 0                    (1 298 m)
                                                                                  │
                                                                     auto_n87_rocade_sud (997 m) ── pont de l'Isère
 avenue de Verdun : axe_verdun_ouest (M14 → M13, k 30-625) … Paquet Jardin (lot A) … axe_verdun_centre (k 1 080-1 950)
```

| Site | Ce qui est décrit | Tronçons | Photos / tuiles regardées | Compilation (partie au format existant) |
|---|---|---|---|---|
| `auto_a41_section_courante` | A41 2 × 2 voies, BAU 3,4, TPC 6,9 m enherbé à 2 glissières, passage supérieur des Pépinières, D41c, T1 → T3 | 1 | 5 / 10 | ok, 0 non-conformité |
| `auto_a41_echangeur_meylan_est` | sortie 26 (voie de décélération, musoir), branche N87 → A41 parallèle, entrées / sorties de Meylan-Est, convergence 2 + 2 → 4 → 3, TPC à GBA, pont | 5 | 9 / 10 | ok |
| `auto_noeud_a41_n87` | échangeur A41 / N87 à 3 niveaux, 7 bretelles, pont de la N87, hélice de Meylan | 7 | 6 / 6 | ok (confiance faible) |
| `auto_a41_extremite_ouest` | début / fin de l'autoroute (C207, B14 110, carrefour à feux), réduction 3 → 2, TPC de 14 → 7 m, sortie et entrée 27 Mi-Plaine | 4 | 7 / 7 | ok |
| `auto_n87_rocade_sud` | voie rapide 2 × 2, GBA centrale (TPC 2 m), BAU 1,7 / 2,5, muret, aire de service | 1 | 3 / 3 | ok |
| `axe_verdun_ouest` | boulevard à chaussées séparées : 2 × 3 avec couloirs bus et TPC enherbé, puis 2 × 2 avec TPC à haie taillée ; pistes latérales, damier Chronovélo, arrêt de bus | 2 | 5 / 7 | ok |
| `axe_verdun_centre` | 2 × 1 voies à îlot central peint et refuges bordés, accotements enherbés, piste bidirectionnelle, trottoir | 2 | 5 / 5 | ok (écarts admis justifiés) |

Chaque site a `DESCRIPTION.md` (texte libre, ordre de construction, profil chiffré, simplifications),
`description.yaml` (traduction ; `extensions_auto` = ce que le format ne porte pas encore, voir
`BESOINS_FORMAT_AUTO.md`), `mesures.json` (coupes ortho, lecture, largeurs retenues, écarts aux règles, lacunes) et
`photos.json` (identifiants, auteurs, positions, tuiles regardées, constats — aucune image).

## 2. Ordre de construction commun (étapes du PCG)

Pour que l'ensemble ne soit pas fait de bouts de segments, chaque description donne l'ordre du chantier
(`extensions_auto.etapes`). Pour l'autoroute et les grands axes, le même ordre revient partout :

1. **Plate-forme** : terrassements, remblais et talus, emprise de toutes les chaussées d'un site (et des bretelles).
2. **Ouvrages** : piles, culées, tabliers, passages sous une bretelle — avant les chaussées qu'ils enjambent.
3. **Chaussées** : enrobé continu de toutes les voies, BAU, BDG, voies d'insertion et de décélération, bretelles.
4. **Terre-plein central et accotements** : herbe, GBA coulée, haie, refuges bordés (grands axes : bordures d'abord).
5. **Dispositifs de retenue** : glissières (simples, doubles, contournant les piles), murets, garde-corps.
6. **Marquages** : lignes longitudinales (u = 7,5 cm sur autoroute et chaussées séparées), puis zones (chevrons des
   musoirs, hachures), puis flèches ; pratiques locales (damier jaune) seulement là où une photo les montre.
7. **Signalisation verticale** : police (B14, C207, C28, AB3a), direction (D41a / D41c, portiques), balises (J14a,
   J4), postes d'appel d'urgence.
8. **Équipements** : éclairage, clôtures, lignes HT, aires de service, abris de bus.
9. **Abords** : végétation (haies, alignements, bois, champs), bâti.

## 3. Méthode et sources

- **Ortho** : IGN BD ORTHO 2024 RVB 20 cm (WMS Géoplateforme `HR.ORTHOIMAGERY.ORTHOPHOTOS`, identique à la couche
  2024 ; prise de vue du 09/08/2024), Etalab 2.0. Mesure par coupes redressées (`auto_outils/coupe_ortho.py` : bande
  le long de l'axe ré-échantillonnée à 0,10 m/px, pics de luminance des lignes, indice de végétation), images
  regardées en tuiles natives (`recon/pcg/vision/decoupe.py image`), statistiques (`analyse_coupes.py`).
- **Photos** : catalogue Panoramax de 26 214 photos sur la zone (`catalogue_panoramax.py`), rattachées aux routes OSM
  (`photos_par_axe.py` : 1 586 photos sur l'A41 dans Meylan, 2017-2026, dont des 360° de 2024-2025 dans les deux
  sens et depuis le pont des Pépinières) ; 40 photos téléchargées et découpées (`photos_site.py`, vues de 1 092 px,
  champ 68,25°), 48 tuiles regardées. Photos et tuiles : `recon/out/generateur/meylan/<site>/photos_non_versionnees/`
  (ignoré par git). `photos.json` est écrit par `ecrire_photos_json.py`.
- **OSM** : extraits Overpass du 17/10/2026 (routes avec nœuds, limite communale), non versionnés dans
  `recon/out/generateur/meylan/auto_travail_lotB/osm/` ; ODbL.
- **Règles** : `assets/specs/route/regles_route_fr.json` (RF-MQ-SC-06, RF-MQ-U-01, RF-MQ-DEC-02, RF-MQ-INS-01,
  RF-OSM-LAR-*, RF-GV-TPC-*, RF-GV-PON-*…), synthèse `D:\DocRoute\00_SYNTHESE_CONCEPTION_ROUTES_FR.md` (§ 2.3
  autoroute, § 7 terre-pleins, § 8 ponts), observations du dossier 13 (M26, M27, M14, M15, M13, M17, M08).
- **Contrôle** : `auto_outils/tester_descriptions_lotB.py` lit chaque `description.yaml` avec le lecteur YAML du
  dépôt, retire `extensions_auto` et compile le reste avec `description_vers_modele.compiler` sans rien écrire dans
  le dépôt (résumé dans `recon/out/generateur/meylan/auto_travail_lotB/tests_descriptions_lotB.json`).

```
python recon/generateur/meylan/auto_outils/catalogue_panoramax.py --bbox 5.750 45.195 5.822 45.222 --nom lotB
python recon/generateur/meylan/auto_outils/photos_par_axe.py
python recon/generateur/meylan/auto_outils/ortho_ign.py --ways <ids OSM> --tampon 70
python recon/generateur/meylan/auto_outils/coupe_ortho.py --site <site> --polyligne x,y … --stations … --nom <nom>
python recon/generateur/meylan/auto_outils/photos_site.py --site <site> --ids <id8> … --tangages=-10
python recon/generateur/meylan/auto_outils/tester_descriptions_lotB.py
```

## 4. Lacunes

- Aucun MNT utilisé : profils en long, dévers mesurés, hauteurs d'ouvrages et tirants d'air manquent (B15).
- Bretelles décrites par les axes OSM (cassures jusqu'à 30°) ; rayons non ajustés (B14).
- Pont de la Rocade Sud sur l'Isère, pont de desserte de l'A41 (s ≈ 1 007 au nœud), carrefour en haut de l'hélice :
  non photographiés ou hors lot.
- Avenue de Verdun entre M13 et Paquet Jardin (k 650-950) non décrite ; troisième grand axe non retenu : les candidats
  examinés n'ont pas convenu : avenue du Granier (coupes ortho : chaussée unique et carrefours, déjà décrite à l'étape 1,
  M24), D1090 à l'est du rond-point du Lycée (OSM : chaussée unique à 2 voies sur l'essentiel, non vérifié sur l'ortho).
- Hauteurs et types de glissières, candélabres, essences d'arbres : estimés sur photo, à confirmer.
