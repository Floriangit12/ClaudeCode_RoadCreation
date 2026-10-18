# Compréhension de la scène — `axe_verdun_centre` (avenue de Verdun entre Paquet Jardin, M17 et le lycée)

*18/10/2026, lot SITES, comparaison v2. Compréhension faite par le modèle en regardant lui-même, en tuiles natives
(≤ 1 092 px) et en zooms au plus proche voisin, les orthos de plusieurs dates, les vues tirées des photos Panoramax 360°
et les rendus du modèle ; aucune fusion algorithmique. Chemins relatifs à
`recon/out/generateur/meylan_axe_verdun_centre/comparaison/<scène>/` ; zooms d'ortho sous
`recon/generateur/tmp/lotB_sites/zooms/` (IGN, licence ouverte) ; photos et planches sous `photos_non_versionnees/`
(jamais versionnées ; aucune image ici).*

## 1. Images regardées

| Scène | Emprise (repère du site) | Photos / vues | Dates | Zone de conflit |
|---|---|---|---|---|
| `meylan_axe_verdun_centre` (T1, Paquet Jardin → M17) | x −247 → 42, y −244 → 46 | 13 / 50 (Panoramax, voiture) | 24/08/2024, 18/05/2025 (fenêtre d'état 24/08/2024 → 22/06/2025, avant le chantier de Paquet Jardin) | passage à refuge de M27, débouchés des rues latérales, poches de tourne-à-gauche |
| `meylan_axe_verdun_centre_t2` (T2, M17 → lycée) | x 116 → 362, y 130 → 354 | 13 / 52 (dont 2 Mapillary) | 18/05/2025 | passage à refuge de k ≈ 1 661, arrêt de bus, poche de TAG |

Lus : `orthos/tuiles_natives/site_ign2024_t01` (T1), zooms `avc_t1_m27`, `avc_m27_passage`, `avc_t2_debut` ;
vue de dessus `dessus/planche_dessus_site_ign_t07`, contours `dessus/contours_site_ign_t04`, `t05` ; vues et planches
citées ci-dessous.

## 2. La scène en une phrase

Avenue à une voie par sens séparées par une bande centrale hachurée entre deux lignes continues, sans bordure le long
des voies (rive peinte, puis accotement d'herbe fleurie), piste bidirectionnelle et trottoir au nord-ouest derrière
l'accotement ; aux passages piétons la bande hachurée devient un refuge bordé portant une balise B21, précédé des
hachures ; aux rues latérales elle s'ouvre en poche de tourne-à-gauche.

## 3. Ce qu'il y a où

- **Profil courant** : voie ≈ 3,6 m par sens, bande centrale hachurée ≈ 3,4 m entre deux continues, accotements
  d'herbe (fleurs jaunes au printemps), bordure basse au bord de l'accotement côté trottoir : `planche_1977f0a0_+010`
  (18/05/2025, sens sud-ouest ; le rendu reproduit la bande hachurée, les voies et l'accotement), `vue_35e216bb_-168`
  (enrobé très fissuré ; piste bidirectionnelle sombre à tirets à droite en roulant vers le sud-ouest, donc au nord-ouest ;
  la visée annoncée de cette vue, vers le nord-est, est inversée : le capot est devant).
- **Passage à refuge de M27 (zone de conflit de T1)** : bandes sur les deux voies, refuge bordé au milieu avec **B21**,
  hachures de part et d'autre, traversée prolongée en zébra sur la piste : `planche_176f9ab0_-008` (18/05/2025),
  `vue_176f9ab0_-068` ; ortho `zooms/avc_m27_passage` : bandes et refuge à (−85 ; −81), soit **9 m au sud-ouest** du
  passage du modèle (`contours_site_ign_t04` : refuge du modèle à (−78 ; −74)).
- **Rues latérales** : débouché avec bordure courbe et zone hachurée centrale qui s'ouvre (`planche_34aca5c3_-076`,
  24/08/2024) ; poche de tourne-à-gauche et îlot au droit de M17 (`vue_35e216bb_-168`).
- **T2** : passage à refuge vers x ≈ 140-150 (bandes et refuge, `zooms/avc_t2_debut`), hachures centrales, rue latérale
  au sud-est avec passage (x ≈ 180) ; *(vues photo de T2 : comparaison en file à la rédaction, voir RECONSTRUCTION.md)*.

## 4. Contradictions entre dates, résolues

- 24/08/2024 et 18/05/2025 : mêmes marquages et mêmes refuges ; l'ortho du 09/08/2024 est cohérente. Les photos
  postérieures au 23/06/2025 (chantier de Paquet Jardin) sont écartées par la fenêtre d'état.

## 5. Ce qui reste incertain

- Position du passage de T2 (± 5 m) ; largeur exacte du refuge (≈ 2 m vue sur photo).
- Hauteur des bordures du refuge (0,11 m relevée par le lot B, sous la règle de 0,12 m : écart admis).

## 6. Écarts au modèle et suite donnée

| Élément | Modèle (itération 0) | Réalité | Suite |
|---|---|---|---|
| Passage à refuge de M27 | s = 221 | s ≈ 212 (9 m plus au sud-ouest) | refuge, ouverture de l'îlot et passage reculés de 9 m (itération 1, T1 refabriqué) |
| B21 sur le refuge, zébra sur la piste | absents | présents | B21 : signalisation hors format (lot L6) ; zébra sur piste : BESOINS V-C5 |
| Poches de tourne-à-gauche | absentes | présentes | BESOINS V-C3 (déjà relevé) |
