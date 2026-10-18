# Vieux Chêne × Taillefer × Hélice (M07) — manques du générateur rencontrés à l'étape 3

*`recon/generateur/meylan/vieux_chene_taillefer_feux/BESOINS.md` — 18/10/2026, lot « carrefours » de l'étape 3. Le code
partagé n'a pas été modifié ; chaque besoin cite le site, l'élément, la photo ou le fichier qui le montre et la règle.
Les besoins G2 et G6 à G8 sont communs aux quatre carrefours du lot (même texte dans leurs `BESOINS.md`).*

## G1 — Bande « séparateur » d'un profil : fabrication refusée (bloquant)

- **Élément** : séparateur bordé de 0,26 m entre la sortie et les voies d'entrée du chemin du Vieux Chêne est
  (coupe `e_30` : gam 15,45 → 15,71 ; photo 3eb5557e : séparateur bordé à droite de la voie de sortie).
- **Constat** : `séparateur 0,3` (FORMAT_DESCRIPTION § 5.1, RF-OSM-LAR-033) devient une bande `separateur` de dz 0,15 m
  dont les deux limites portent `nature: separateur` (bordure séparatrice, RF-MA-SEP-001) **sans bordure** ;
  `rg::nivellement` refuse alors le dénivelé : « route R-2 section 0 : dénivelé sans bordure entre v1 et sep1 »
  (journal `recon/out/generateur/meylan_vieux_chene_taillefer_feux/_travail/fab_v1.log`). L'exemple
  `description/exemples/12_piste_bidirectionnelle_separateur.yaml` est donc compilable mais pas fabricable.
- **Contournement de la description** : `terre-plein 0,3 béton` (bordures I2 des deux côtés). Il produit un nez de
  0,15 m de rayon dont les faces arrière se recoupent (boucle de segments de 2 cm, voir G2).
- **Besoin** : poser une bordure (profil de séparateur, vue 0,15) sur les limites d'une bande `separateur`, ou la
  fabriquer comme un élément de bordure double face posé sur la limite.

## G2 — Raffinement de Triangulate 2D de `rg::carrefours_sol` qui ne se termine pas (bloquant, commun au lot)

- **Constat** : sur les quatre carrefours du lot (et sur `vieux_chene_inovallee_piste` du lot voisin), la fabrication
  monte à 14-18 Go de mémoire privée puis plante dans `GU_Delaunay` (« Fatal error: Segmentation fault »,
  `SOP_Triangulate2D_3_0`), pendant la cuisson de `sol_total`. Journaux du premier passage :
  `meylan_paquet_jardin/_travail/fab_v1.log`, `meylan_verdun_centre_feux/_travail/diag.log`,
  `meylan_verdun_lycee_feux/_travail/fab_v1.log`.
- **Diagnostic** (géométrie d'entrée enregistrée, `meylan_vieux_chene_taillefer_feux/_travail/diag_tri/tri01_entree.bgeo.sc`,
  scripts `meylan_paquet_jardin/_travail/{diag_triangulations,analyser_entree_tri,tester_tri}.py`) :
  la triangulation de `rg::sol` passe (234 518 triangles, 2,5 s) ; celle de `rg::carrefours_sol` (arête 0,5 m, angle
  minimal 25°) s'emballe. Son entrée contient 114 paires de segments de contrainte à moins de 5° dont la plupart à
  **0°** (lignes des faces de bordure posées exactement sur le contour), 8 croisements entre lignes et contour, des
  boucles d'îlot « ouvertes en un sommet » dont les deux bouts restent écartés de 0,17 à 5 mm (îlot directionnel
  ouest → Hélice, points 1375/1376 et 1550/1551), et la boucle de 2 cm du nez de l'îlot de 0,3 m (G1). Essais sur cette
  entrée : angle 25°, 20°, 15°, 10° et 5° → arrêt après 70 s ; **0° → 29 556 triangles en 0,3 s** ; sans les deux
  lignes de l'îlot directionnel, ou avec une soudure de 1 cm, le résultat dépend du reste de l'entrée (non monotone).
- **Contournement déclaré (rendus de ce lot)** : l'enveloppe `meylan_paquet_jardin/_travail/fabriquer_lot_a.py` met
  `angle_min = 0` sur l'instance `rg::carrefours_sol` dans le processus de fabrication (rien n'est enregistré dans les
  HDA) ; le raffinement en taille d'arête (0,5 m) est gardé, `rg::sol` garde 25°. Conséquence : TQ-SOL-002 (25°) n'est
  pas tenu dans le cœur des carrefours (triangles étirés), la forme du sol n'est pas changée.
- **Besoin** : nettoyer l'entrée de la triangulation du cœur (retirer les segments de ligne colinéaires au contour,
  souder les bouts des boucles d'îlot ouvertes, fermer les boucles de nez dégénérées), plafonner `maxnewpts` avec un
  message d'erreur au lieu d'un plantage, et ajouter un carrefour réel (M07) aux scènes de non-régression.

## G3 — Branche courbe : coin calculé sur la partie courbe, bande d'herbe à travers le carrefour

- **Élément** : chemin du Vieux Chêne est, courbe de ≈ 24-48 m de rayon à partir de ≈ 25 m du centre
  (OSM 857526256, 190600688 ; photos efc67150, 3eb5557e, 4c3c6ec3).
- **Constat** : avec une droite de 23 m près du carrefour puis un arc (itération 1, première fabrication), le point
  de tangence du coin du tourne-à-droite Hélice → est tombait sur l'arc ; le sol du carrefour a reçu une bande
  `carrefour_trottoir` en gazon de ≈ 3 × 43 m, de x −11 à x +32, à travers la zone de conflit (rendu
  `rendus/dessus.png` de 17:23, 1 387 faces `carrefour_trottoir / gazon_tondu`). Aucun contrôle ne l'a signalé.
- **Contournement de la description** : droite allongée à 36 m (écart à la médiane OSM porté de 0,6 à 2,8 m).
- **Besoin** : un contrôle bloquant « coin tangent hors de la partie droite de la branche » (README_RG § 9, limite
  connue : « ligne de référence droite près du carrefour »), puis la prise en charge des bords courbes dans les coins.

## G4 — Traversées cyclables peintes (vert, damier) : pas de mot dans le format (besoin A2 existant)

- Photos ad0b728e (l-102.9) et 45da0502 : bande verte de traversée cyclable doublant le passage nord ; photo 4289a952 :
  damier au passage ouest. RF-OBS-CYC-03, RF-MA-CHR-007 (pratique locale photographiée, DEF-008).

## G5 — Hélice de Meylan : glissières entre les chaussées non décrites

- Photo d7449e61 (Hélice à ≈ 50 m du centre) : chaussées séparées par une bande étroite portant une glissière
  métallique, rives peintes et glissière à l'extérieur ; la description garde un terre-plein bordé de 2 m. Une limite
  `glissière` ferait entrer la famille `autoroute` dans une scène à carrefour plan, composition « sans scène de contrôle
  dédiée » (README_RG § 14) : non essayée dans ce lot. Besoin : une scène de contrôle carrefour + retenue.

## G6 — Outil de comparaison : grille et position de prise de vue pensées pour un tronçon droit

- `ecarts.json`, rubrique `profil_modele_vise` : sur une scène de réseau, le profil « visé » est celui de la première
  route avec des largeurs fausses (trottoir 11,81 m, voies de 12,7 à 13,96 m pour la photo e5c7653d) ; `position_modele`
  donne s, t dans le repère local (x, y) et la bande la plus proche. Les rubriques ont été remplies à la main d'après
  les planches. Besoin : profil de la route et de l'abscisse réellement vues (`comparaison/modele.py`).

## G7 — Pilote : vues économes des scènes de réseau

- `fabriquer_generateur.py` rend « dessus + conducteur » pour une scène à carrefour et l'oblique 3/4 seulement pour les
  scènes phares (J5, G1, A3) ; l'étape 3 demande dessus + oblique. Contournement : enveloppe
  `fabriquer_lot_a.py` (remplace `rendre_reseau` dans le processus). Besoin : option `--vues dessus,oblique` pour les
  scènes de réseau (même besoin noté par le lot « giratoires et rues »).

## G8 — Revêtement : fissures pontées et reprises

- Photos e8178560 (t004), ad0b728e, 3eb5557e : enrobé très rapiécé, pontages noirs ; le matériau `enrobe_reprise_tranchee`
  (« enrobé rapiécé ») est uniforme. Besoin : carte de fissures pontées / reprises pour `enrobé usé` et `enrobé rapiécé`
  (RF-OBS-REV-01).

## Passe v2 (18/10/2026) : ce que le centre réel montre et que le PCG ne sait pas faire

Lecture du dossier de compréhension v2 (60 photos, 169 vues dont 65 du centre, orthos IGN 2015-2025) :
`COMPREHENSION.md`. Repère du site (x vers l'est, y vers le nord, origine au point M07) ; lectures à grille dans
`recon/out/generateur/meylan_vieux_chene_taillefer_feux/_travail/v2/lecture/`.

### VT-1 — Îlot refuge court suivi d'un séparateur étroit (Taillefer)

- **Élément** : au débouché du Taillefer, îlot refuge bordé ≈ 1,5 × 4 m vers (−2,6 ; 8 à 11,5), B21 et contour peint,
  mât de feu ; le passage et la traversée verte le coupent ; au-delà, séparateur étroit bordé (≈ 0,5 m) sur ≈ 8-10 m.
  Images : `ign24_coeur` (IGN 2024) ; vues c02e39f5_-131 et -174, 3c82fa3f_+013, 23ecaea9_+003, 2a5175d2_+009 (2026).
- **Constat** : décrit par une ouverture (terre-plein 1,5 m) : le modèle fait un îlot de 1,5 m de largeur constante du
  passage jusqu'à la frontière, sans le rétrécissement en séparateur étroit (une bande « séparateur » n'est pas
  fabricable : G1). **Besoin** : G1 (bordure de séparateur), puis îlot de branche à largeur variable (refuge élargi au
  droit du passage).

### VT-2 — Traversées cyclables : bande verte au nord, damier à l'ouest (G4 précisé)

- **Élément** : bande verte d'≈ 1,5 m accolée au passage du Taillefer côté cœur, de (−8 ; 10) à (2 ; 13) environ ;
  damier vert et blanc au passage ouest (≈ 47 m du centre). Images : c02e39f5_-131, 3c82fa3f_+013, ad0b728e_+091
  (2026) ; 4289a952 (passe 1). **Besoin** : objet « traversée cyclable » de branche (voir `../paquet_jardin/BESOINS.md`
  PJ-1), marquages `bande verte` et `damier vert`.

### VT-3 — Zébra du levé GAM différent de l'état photographié

- **Constat** : le levé GAM place le zébra du Taillefer vers (−11 ; 3) → (1 ; 11), ≈ 4 m au sud de celui de l'ortho
  2024 et des photos de 2026 (au nord de l'îlot refuge). Le levé est d'un autre état (projet ou antérieur) : il ne sert
  qu'aux bordures (concordantes à ≈ 0,5 m). À signaler à la reprise du levé (pas un manque du générateur).

### G2 étendu — triangulations de `rg::sol`

- Fabrications de la passe v2 avec `--angle-sol 0` en plus de `--angle-carrefour 0` (enveloppe
  `meylan_paquet_jardin/_travail/fabriquer_lot_a.py`), après le plantage de `rg::sol` observé sur Paquet Jardin
  (`../paquet_jardin/BESOINS.md` PJ-8) : TQ-SOL-002 n'est pas tenu sur les routes ; la forme du sol est inchangée.
