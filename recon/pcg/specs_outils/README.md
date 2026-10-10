# Outils de génération des specs V2

Ces scripts ont produit les specs normatives de la V2 dans `assets/specs/` (voir `assets/specs/README_specs_v2.md`).
Ce sont des générateurs ponctuels. On ne les relance que pour modifier une spec ; la référence reste le JSON produit.

| Script | Produit | Entrées |
|---|---|---|
| `gen_marquages.py SORTIE VELO` | `assets/specs/marquages_geometrie.json` | cotes IISR 7e partie VC20250404 (annexes B1/B2/B3, D1), `velo_vecteur.json` |
| `vectoriser_velo.py IMAGE [SORTIE] [TOL]` | `velo_vecteur.json` (figurine vélo vectorisée, Douglas-Peucker 4 mm) | image native de l'annexe D1 de l'IISR |
| `mesure_rab.py IMAGE` | mesure de la tête de la flèche de rabattement (sans cote horizontale dans l'IISR) | image native de l'annexe B1 |
| `controler_marquages.py SPEC` | `controle_marquages.txt` (polygones simples, sens, cotes) | `marquages_geometrie.json` |
| `planche_marquages.py SPEC PNG` | `planche_gabarits_marquages.png` | `marquages_geometrie.json` |
| `gen_bordures_elements.py SORTIE` | `assets/specs/bordures_elements.json` (+ `profils_bordures_v2.png`) | `assets/specs/bordures.json`, catalogues Celtys et Sepa |
| `gen_materiaux_sol.py SORTIE` | `assets/specs/materiaux_sol.json` | `assets/manifeste_cc0.json`, textures de `assets/lib/materiaux/` |
| `ajouter_manifeste.py` | 4 entrées CC0 ajoutées à `assets/manifeste_cc0.json` (BRF WoodChips003/001, gravier 6/10, calcaire) | API ambientCG / Poly Haven (métadonnées) |

Le dernier contrôle des gabarits (`controle_marquages.txt`) ne relève aucune erreur : 13 gabarits sur 13 sont simples,
orientés dans le sens trigonométrique et conformes aux cotes.
