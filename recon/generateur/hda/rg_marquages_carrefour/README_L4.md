# `rg::marquages_carrefour::1.0` — lot L4 (marquages, trajectoires, conflits, zone de conflit des carrefours plans)

*`recon/generateur/hda/rg_marquages_carrefour/README_L4.md` — 18/10/2026. Plan : `PLAN_GENERATEUR.md` § 2.4 (étapes 7
à 10) et § 3 (L4). Rapport : `validation/RAPPORT_L4.md`. À reporter dans `hda/README_RG.md` (§ 10) par l'agent
d'intégration : ce fichier n'a pas été modifié par le lot.*

Construite par `construire.py` (code VEX dans `vex_l4.py`, lecture du modèle dans `lecteur_marquages_carrefour.py`,
bibliothèques `rg_geometrie.h`, `rg_niveau.h`, `rg_marquage.h` et `hda/rg_carrefours/vex/rg_carrefour.h` recopiées en
tête des wrangles). Pilote : `fabriquer_marquages_carrefour.py` (importe `fabriquer_carrefours.py` sans le modifier).
Contrôle indépendant : `validation/controler_L4.py` ; plan de contrôle : `validation/dessiner_L4.py`.

```
rg::carrefours (3 SOLVEUR) ─┐
rg::nivellement (1 NIVEAUX) ┼─► rg::marquages_carrefour ─► 1 LIGNES ─► pj::marquage_solide (2 mm)
rg::graphe (1 références) ──┤                          ├► 2 MARQUES ─► + MARQUES de rg::marquages et de rg::carrefours_sol
rg::marquages (1 LIGNES) ───┘                          │               ─► pj::marquage_solide (3 mm)
                                                       ├► 3 DONNÉES (trajectoires, conflits, zone, voies, guidage, table)
                                                       └► 4 CONTRÔLES (LIGNES d'entrée marquées)
pilote : les ponctuels « fleche » ancrés à un carrefour sont retirés de l'entrée de rg::marquages (l'HDA les pose)
```

## Entrées, paramètres

1. SOLVEUR de `rg::carrefours` (sortie 3) ; 2. NIVEAUX de `rg::nivellement` (sortie 1) ; 3. références échantillonnées de
`rg::graphe` (sortie 1) ; 4. LIGNES de `rg::marquages` (sortie 1). Paramètre `fichier` (relié à celui de
`rg::lire_modele`) : consignes de flèches (`branches[].fleches`), sas (`sas_velo`), lignes d'arrêt, mouvements
autorisés (`trajectoires[]` : de / vers, mouvement, `guidage.materialise`), phases vertes (feux R11 du contrôleur).
Paramètres : véhicule de projet `vl` (rayon d'axe minimal 5,467 m, caisse 1,80 m : lot L3a), angle d'un tout-droit 25°
[G], flèche 0,5 mm et pas angulaire 1° des arcs, largeurs des lignes (RF-MQ-GUI-01, RF-MQ-FEU-01, RF-MQ-CED-01,
RF-MQ-STOP-01), T'2 0,50 / 0,50 (RF-MQ-MOD-T'2), flèches : fraction de largeur 0,99 et rectitude 0,5° [G], pas de
densification 0,25 m [G], figurine des sas `VELO`, usure (lue par le pilote sur les LIGNES de `rg::marquages`).

## Ce que l'HDA fabrique

| Étape | Règle | Détail |
|---|---|---|
| voies | — | une voie par bande de circulation ou cyclable à l'embouchure (`s_end`) : axe, bords, sens (entrante = vers le centre) |
| guidage | RF-MQ-GUI-01, RF-MQ-CAR-03, DEF-021, ARB-08 | seulement pour les TAG dont le modèle dit `guidage.materialise` ; deux TAG opposés : prolongements des bords droits des voies de TAG + oblique à 45° par le milieu, raccords tangents de rayon maximal tenant entre l'embouchure et l'oblique (plafonné au rayon du VL) [G] |
| trajectoires | RF-GV-TRJ-006 | droite – arc – droite sur l'axe réel des voies (itéré si l'arc commence en amont de l'embouchure) ; TAD : rayon du coin + écart axe-bord ; TAG : plus grand rayon tenant dans les embouchures ; TAG guidé : plus petit rayon gardant la caisse de son côté de la ligne, sans toucher la peinture ; TAG opposés non guidés : plus petit rayon commun qui sépare leurs axes (convention du CU), si chaque véhicule reste dans sa voie au droit des embouchures ; tout rayon ≥ rayon du VL arrondi au cm ; vélos : tout droit d'une bande cyclable à la bande alignée [G] |
| limite de jonction | — | `d_j` par branche = plus grande sortie d'un arc hors de l'embouchure ; toutes les trajectoires d'une branche commencent (finissent) en `s_j = s_end − d_j` sur l'axe de leur voie |
| conflits | plan § 2.4 étape 8 | paires : divergence (même voie d'entrée), convergence (même voie de sortie), croisement (intersection des axes) ; `meme_phase` |
| zone de conflit | RF-GV-TRJ-001, RF-MQ-CAR-02, RF-MQ-CAR-04 | polygone `frontiere` du SOLVEUR + bandes d'approche (chaussée) de la ligne d'arrêt / d'effet (bord amont ; passage piéton si ligne virtuelle, ARB-01) à l'embouchure |
| flèches | DEF-017, ARB-11, RF-MQ-DIR-02/-03/-04/-06/-09 | gabarit exact du dossier 08 (pied de tige à l'origine), tige sur l'axe de la voie, le long de la voie ; pointe de la dernière à 1,50 m du bord amont de la ligne qui couvre la voie (sinon du passage, sinon de l'embouchure) ; 20 m de pointe à pointe ; série arrêtée là où la voie n'est pas formée (≥ 99 % de sa largeur) ou pas droite (≤ 0,5°) |
| sas | RF-MQ-SAS-01, DEF-016 | figurine VELO dans l'axe de chaque voie de circulation couverte par la ligne avant, centrée entre les deux lignes |
| axe prioritaire | RF-MQ-CAR-01, RF-GV-TRJ-002 | discontinue axiale de deux branches « prioritaire » opposées prolongée dans le carrefour : n tirets de la même modulation répartis entre les derniers tirets des deux branches [G] |
| filtre | RF-MQ-CAR-02/-04, RF-MQ-SC-11 | morceaux de LIGNES retirés dans le cœur, retirés ou coupés (bord amont de la ligne d'arrêt) sur les approches ; rives d'une branche prioritaire retirées du point de tangence du coin à l'embouchure, côté affluente |

## Sorties

1. **LIGNES** et 2. **MARQUES** : polygones à plat (x, 0, −y) au contrat de `pj::marquage_solide` (`pj_entite`
`ML_L4_*` / `MQ_L4_*`, `materiau_id`, `classe`, `type`, `gabarit`, `cle` = `guidage` ou `axe_prioritaire:<clé>`,
`modulation`, `largeur_m`, `s0`, `s1`, `rang`, `rg_l4` = 1) ; les lignes de section gardées passent telles quelles (coupées
au besoin).
3. **DONNÉES** : points `br4` (branche : repère du SOLVEUR, `s_j`, `d_j`, rayons des coins), `fl`, `mv` (modèle), `voie`
(position à `s_j`, `h`, `t_axe`, `largeur`, `entrante`), `conflit` (`type`, `a`, `b`, `famille`, `meme_phase`), `table_l4`
(flèches et figurines : `m_s0` pied, `m_s1` pointe, `m_t`, `m_cap_deg`, `m_s_ligne`) ; polylignes `trajectoire_l4`
(`id`, `mouvement`, `de_*`, `vers_*`, `rayon`, `regle_rayon`, `ext_entree`, `ext_sortie`, `dev_entree`, `dev_sortie`,
`guide`, `guidage`, `garde_guidage`, `phases[]`, `tags`), `voie_axe` (axe de chaque voie de `s_j` à l'extrémité libre),
`guidage` (axe de la ligne) ; polygones `zone_conflit` (`partie` coeur / approche, `aire_m2`) ; détail
`rg_l4_conflits`, `rg_l4_zone_m2`, `rg_l4_axe`, `rg_l4_avertissements`.
4. **CONTRÔLES** : LIGNES d'entrée avec `rg_l4_retire` (1 dans la zone, 2 rive, 3 coupé) et `rg_l4_raison`.

Exports du pilote (`<scene>/l4/`) : `trajectoires.json`, `conflits.json`, `zone_conflit.json`, `guidage.json`,
`graphe_voies.json` (`rg_graphe_voies/0.1` : voies, connecteurs, zones, passages, étiquettes ≤ 32), `marques_l4.json`
(lignes finales, marques et table), `lignes_retirees.json`, `mesures_l4.json` (peinture − sol), `manifest_l4.json`.

```
hython recon/generateur/fabriquer_marquages_carrefour.py recon/generateur/scenes_carrefours/J5_carrefour_complexe.yaml [--rendus]
                                                       [--construire-hda] [--verifier-determinisme] [--sans-balayages]
python recon/generateur/validation/controler_L4.py [<scene> ...] [--json SORTIE]
python recon/generateur/validation/dessiner_L4.py [<scene> ...] [--demi 30]
python recon/generateur/validation/faire_rapport_L4.py [--determinisme "identique (N fichiers)"]
```

## Limites

Branches tracées vers le centre (extrémité « fin », comme le lot L3) ; guidage pris en charge pour les TAG à
l'indonésienne seulement (baïonnette et carrefour complexe à TC : non) ; damier TC non fait (aucune ligne TC décrite) ;
flèches cyclables (× 1/2) et × 4/3 non utilisées (carrefours plans en agglomération) ; `pj::symbole_iisr::2.0` non faite
(les symboles sont peints par empreintes exactes ; instances UE à faire) ; balayages du lot L3a non recalculés dans
l'HDA (le contrôle les calcule) ; trajectoires vélo seulement en tout droit.
