# Avenue de Verdun × chemin des Buclos (M17) — manques du générateur rencontrés à l'étape 3

*`recon/generateur/meylan/verdun_centre_feux/BESOINS.md` — 18/10/2026, lot « carrefours » de l'étape 3. Le code
partagé n'a pas été modifié. Les besoins G2, G6, G7 et G8 sont communs aux quatre carrefours du lot ; leur diagnostic
complet est dans `../vieux_chene_taillefer_feux/BESOINS.md`.*

## G2 — Triangulate 2D de `rg::carrefours_sol` qui ne se termine pas (bloquant)

Premier passage : plantage `GU_Delaunay` pendant la cuisson de `sol_total`
(`recon/out/generateur/meylan_verdun_centre_feux/_travail/diag.log`). Rendus obtenus avec le contournement déclaré
`angle_min = 0` sur `rg::carrefours_sol` (enveloppe `meylan_paquet_jardin/_travail/fabriquer_lot_a.py`).

## C1 — Une route ne peut porter un carrefour qu'à son extrémité « fin » (baïonnette)

- **Élément** : tronçon de Verdun de ≈ 29 m entre Buclos sud et Buclos nord, qui porte le passage à feux et son refuge.
- **Constat** : `rg::carrefours` ne prend en charge que l'extrémité « fin » d'une route (README_RG § 9 : « un seul
  carrefour par route, à son extrémité fin » ; refus « extrémité début non prise en charge »). Le tronçon est donc
  coupé en deux (`verdun_milieu_s`, `verdun_milieu_n`) qui partent d'un point sans nom ; le résolveur ne les fusionne
  pas (nœud de valence 2 non nommé). Sur le rendu (`rendus/oblique_carrefour.png`, 18/10/2026), les bandes extérieures
  (trottoir, piste, herbe) présentent des décrochements à la coupure et autour du passage.
- **Besoin** : une route avec un carrefour à chaque bout (coupe « début » dans le solveur).

## C2 — Côté continu d'un carrefour en T : bandes extérieures remplacées par un « trottoir de carrefour »

- **Constat** : du côté sans branche (nord-ouest à Buclos sud, sud-est à Buclos nord), le solveur coupe les bandes
  extérieures des deux branches alignées (piste, bande enherbée) et pose un sol `carrefour_trottoir` : la Chronovélo et
  la bande enherbée sont interrompues sur ≈ 15 m (rendus de dessus et oblique). Sur les photos (de22683a t003, f252d62f),
  la piste et l'herbe continuent.
- **Besoin** : prolonger les bandes extérieures du côté continu d'un T (coin « aligné » qui garde le profil).

## C3 — Débouchés voisins non décrits

- Photo fca91c2c (31/08/2025) : voie de tourne-à-droite fléchée vers une rue latérale à ≈ 50 m au sud-ouest ; photo
  63066c96 : îlot planté et passage de l'allée de la Faculté à ≈ 45 m au nord-est (hors emprise, lot B). Les deux
  bouts sont des nœuds partagés à contrat 1 + 1 (`../reseau_meylan.yaml`) : décrire ces débouchés demande de déplacer
  les nœuds (propriété du lot réseau).

## G4 — Bande verte de traversée cyclable du passage à feux (besoin A2)

- Photos de22683a (t003) et f252d62f : bande verte au passage à feux, absente du format.

## G6, G7, G8 — communs au lot (outil de comparaison, vues économes, fissures pontées) : voir `../vieux_chene_taillefer_feux/BESOINS.md`

- G6 ici : 4 des 6 photos retenues (31/08/2025, « Binnette », photos à plat) ont une position GNSS décalée vers le
  nord-ouest ; trois poses sont rejetées et deux planches sont inexploitables (5a55da9f, 63066c96 hors emprise).

## Passe v2 (18/10/2026) : ce que le centre réel montre et que le PCG ne sait pas faire

Lecture du dossier de compréhension v2 (50 photos, 77 vues, orthos IGN 2015-2025) : `COMPREHENSION.md`. Repère du site
(x vers l'est, y vers le nord, origine au passage à feux) ; lectures à grille dans
`recon/out/generateur/meylan_verdun_centre_feux/_travail/v2/lecture/`.

### VC-1 — Îlots refuges en D de part et d'autre d'un passage dans une zone hachurée

- **Élément** : deux îlots bordés en D (gravillons, B21 de contournement) dans la zone hachurée de 3,7 m, de part et
  d'autre du passage à feux, vers (−5 à −2 ; −6 à −2) et (0 à 3 ; 1 à 5). Images : `modele_gam_S` (bordures GAM
  fermées sur l'IGN 2024) ; vues 2b9bed48_-011 (18/05/2025), de22683a (28/07/2026).
- **Constat** : décrits en un seul terre-plein revêtu rectangulaire de ≈ 8 m que le passage coupe (refuge revêtu) ;
  la forme en D (nez arrondi côté passage, coupe droite côté hachures) et le remplissage en gravillons de part et
  d'autre du passage ne sont pas dits. **Besoin** : refuge de passage en deux demi-îlots de forme dite (nez arrondi,
  remplissage), RF-GV-ILO-008, RF-OBS-ILO-01.

### VC-2 — Traversée de la Chronovélo de Buclos nord (G4 précisé)

- **Élément** : zébra + bande verte de la Chronovélo et du trottoir, quelques mètres après la ligne de cédez de
  Buclos nord. Image : 2b9bed48_+155 (18/05/2025). Le passage de branche (retrait 4 m) rend le zébra ; la bande verte
  manque (besoin de l'objet « traversée cyclable » de branche, `../paquet_jardin/BESOINS.md` PJ-1).

### G2 étendu — triangulations de `rg::sol`

- Fabrication v2-1 avec `--angle-sol 0` en plus de `--angle-carrefour 0` (enveloppe
  `meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), après le plantage de `rg::sol` observé sur Paquet Jardin
  (`../paquet_jardin/BESOINS.md` PJ-8).
