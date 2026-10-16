# assets/specs/route : règles et catalogues de la route française pour le générateur

Ce dossier rassemble ce que le générateur procédural de routes (Houdini 22 → USD, OpenDRIVE, graphe de voies) lit pour
fabriquer une route française : les règles de conception, les faces de panneaux et les static meshes.

| Fichier | Contenu | Produit par |
|---|---|---|
| `regles_route_fr.json` | **857 règles** fusionnées et dédoublonnées (901 lues, 44 doublons fusionnés), 20 arbitrages entre volets, 34 paramètres par défaut, 100 sources ; révision du 17/10/2026 après la relecture adverse | `recon/generateur/outils/fusionner_regles.py` |
| `catalogue_assets_route.json` | 120 static meshes `route_fr` (bordures, caniveaux, supports, feux, garde-corps…) avec cotes et sources | `recon/pcg/assets_route/` (dossier 14 de DocRoute) |
| `panneaux_fr_catalogue.json` | 870 faces de panneaux tirées des 863 PDF officiels (code, gamme, dimensions, fichier PNG, usage, SHA-256) | `recon/pcg/assets_route/signalisation/convertir_panneaux.py` (dossier 09) |

Les explications humaines sont dans `D:\DocRoute\00_SYNTHESE_CONCEPTION_ROUTES_FR.md` (référence par élément) et dans
les documents des volets 08 à 14 (`renvoi` de chaque règle). Les erreurs relevées dans les documents plus anciens sont
dans `D:\DocRoute\00_ERRATA_DOCUMENTS_EXISTANTS.md`.

## 1. Régénérer et contrôler

```
python -I recon/generateur/outils/fusionner_regles.py          # écrit regles_route_fr.json
python -I recon/generateur/outils/verifier_regles_route_fr.py  # 16 634 contrôles, 0 erreur au 17/10/2026
```

Le vérificateur contrôle la structure, les références et les numéros de page ; il **ne contrôle pas les valeurs**. Les
valeurs ont été relues à part (relecture adverse du 16-17/10/2026, `D:\DocRoute\15_Relecture_Adverse`) ; les
corrections qui en découlent sont listées dans `D:\DocRoute\00_ERRATA_DOCUMENTS_EXISTANTS.md` § 10.

Toutes les décisions manuelles (identifiants, familles, sources canoniques, doublons, recoupements, arbitrages,
paramètres par défaut) sont dans `recon/generateur/outils/tables_fusion.py`. La fusion ne modifie jamais les JSON des
volets : leur SHA-256 est enregistré dans `volets` ; le vérificateur signale tout volet modifié depuis la fusion.
Les corrections de la relecture adverse ont été portées **dans les JSON des volets** par
`D:\DocRoute\16_Corrections_Relecture\outils\corriger_json_volets.py` (08 à 12 et 14 ; idempotent, à relancer après
toute régénération d'un volet par son script d'origine) et `corriger_volet13.py` (volet 13, puis `o5_livrables.py`) ;
chaque règle corrigée porte un champ `correction` (repris dans `details.correction`).

Le vérificateur contrôle : champs obligatoires, unicité des identifiants, familles et natures connues, source
principale et sources secondaires présentes dans le catalogue, page ou article pour toute règle réglementaire,
existence des `voir_aussi`, des alias, des arbitrages et des paramètres, existence du document de `renvoi`, et que
chaque page citée est dans les bornes du PDF local (74 PDF ouverts, 0 page hors bornes).

## 2. Forme d'une règle

```json
{
  "id": "RF-MQ-PP-02",
  "famille": "pietons_accessibilite",
  "sujet": "passage pour piétons : nombre de bandes",
  "condition": "fonction de la largeur roulable",
  "valeurs": {"table": [{"largeur_m": [4, 6], "bandes": [3, 5]}, "..."]},
  "unite": "m / unités",
  "tolerance": null,
  "source": {"doc": "IISR7", "page": 44, "article": "118"},
  "nature": "reglementaire",
  "confiance": "haute",
  "alias": [{"id_fusionne": "RF-MA-PP-003", "volet": "11", "id_origine": "MA-PP-003", "...": "..."}],
  "voir_aussi": ["RF-MQ-PP-05", "RF-OSM-CAR-040"],
  "arbitrages": [],
  "origine": {"volet": "08", "fichier": "08_Marquages_Geometrie_IISR7/marquages_iisr7.json", "id": "PP-02"},
  "renvoi": "08_Marquages_Geometrie_IISR7/MARQUAGES_IISR7_COMPLET.md"
}
```

- `source.doc` est une clé du catalogue `sources` (titre, fichier local ou URL, décalage de pages s'il y en a).
  Les pages sont celles du **fichier PDF** sauf mention contraire dans `sources[...].decalage_pages`.
- `nature` : `reglementaire` (IISR, arrêtés, codes), `recommandation` (Cerema, Certu, Setra), `pratique_locale`
  (Grenoble-Alpes Métropole, Lyon, Paris, Nantes, Isère), `observation` (Panoramax, ortho, relevé), `inference`
  (lecture des tags OSM), `donnee_fabricant`, `calcul`, `choix_generateur`.
- `confiance` : `haute`, `moyenne`, `faible` (les échelles des volets sont ramenées à celle-ci ; l'originale est
  gardée dans `confiance_origine`).
- `details` garde les champs propres à un volet : `sortie` (chemin dans `modele_voie`) pour l'inférence OSM,
  `n_exemples`, `statistiques_mesures`, `usage_generateur` pour les observations, `type` pour la signalisation…

## 3. Identifiants stables

L'identifiant est l'identifiant d'origine précédé d'un préfixe par volet. Il ne change que si le volet change le sien.

| Volet (D:\DocRoute) | Préfixe | Exemple |
|---|---|---|
| 08 Marquages (IISR 7e partie) et pratiques locales | `RF-MQ-` | `RF-MQ-PP-02`, `RF-MQ-PRA-PAR-03` |
| 09 Signalisation verticale | `RF-SV-` | `RF-SV-AB4.POSITION` |
| 09 Feux | `RF-` | `RF-FEU.HAUTEUR.TROTTOIR` |
| 10 Carrefours, îlots, giratoires, terre-pleins, ponts | `RF-GV-` | `RF-GV-GIR-003` |
| 11 Cycles, piétons, accessibilité, TC | `RF-` | `RF-MA-PIS-002` |
| 12 Inférence OSM | `RF-` | `RF-OSM-CAR-020` |
| 13 Observations Panoramax en Isère | `RF-` | `RF-OBS-GIR-01` |
| 14 Assets | `RF-AS-` | `RF-AS-profil_T2` |

Une règle fusionnée dans une autre (doublon) disparaît de la liste mais reste trouvable : `index_alias` associe
`"11:MA-CAR-001"` et `"RF-MA-CAR-001"` à la règle canonique `RF-MQ-SAS-01`. Toute citation d'un ancien identifiant
se résout donc par `index_alias[...]`.

## 4. Familles (par élément du générateur)

| Famille | Règles | Famille | Règles |
|---|---|---|---|
| generalites | 62 | cycles | 103 |
| profil | 31 | pietons_accessibilite | 58 |
| marquage_longitudinal | 29 | transports_collectifs | 21 |
| points_singuliers | 21 | stationnement | 19 |
| fleches | 16 | moderation | 11 |
| lignes_transversales | 13 | signalisation_verticale | 95 |
| inscriptions_symboles | 6 | feux | 53 |
| carrefour_plan | 65 | vegetation_visibilite | 10 |
| giratoire | 31 | inference_osm | 80 |
| ilots_terre_pleins | 19 | assets | 40 |
| pont | 16 | pratiques_locales | 58 |

## 5. Ordre d'application (champ `priorite_d_application`)

1. mesure ou relevé du site (PCRS, levé GAM, LiDAR, ortho 5 cm, photo recalée) ;
2. règle `reglementaire` : le générateur ne l'enfreint jamais. En conséquence, une pratique locale non conforme à
   l'IISR (damier ou carrés des traversées cyclables, jaune et cyan Chronovélo, îlots peints ocre, anneau cyclable
   vert) n'est jamais un style par défaut : elle ne s'applique qu'à un élément relevé ou photographié (priorité 1) ;
3. `pratique_locale` du territoire de la scène (Grenoble-Alpes Métropole, observations de l'Isère) ;
4. `recommandation` nationale ;
5. `parametres_par_defaut` (valeurs retenues quand les textes laissent une plage ou ne chiffrent pas).

## 6. Arbitrages et paramètres par défaut

Les volets ont parfois retenu des valeurs différentes pour la même chose. `arbitrages` liste chaque cas, les valeurs
en présence, la décision et sa justification ; les règles concernées portent l'identifiant de l'arbitrage. Les
principaux :

| Arbitrage | Décision |
|---|---|
| ARB-01 ligne d'effet des feux | non peinte par défaut (le passage piéton tient lieu de ligne d'arrêt) ; si peinte : 3,0 m en amont du passage (1,50-5,00) |
| ARB-02 ligne cédez / STOP et passage | ligne à la limite de la chaussée prioritaire ; passage 2 m en amont (2-5 m en giratoire, 4 m en interurbain) |
| ARB-03 zigzag de bus | 30 m (20 m en amont du poteau, 10 m en aval), jamais moins de 10 m |
| ARB-04 panneaux au nez d'îlot | J5 : bas 1,00 m adaptable, sommet ≤ 1,00 m en tête d'îlot de route principale (ACI p. 69) ; prescription : 1,00 m hors agglomération, 0,60 m [G] en agglomération (confiance faible ; corrigé le 17/10/2026, l'ancienne valeur de 0,50 m reposait sur une clause de rase campagne) |
| ARB-05 mât de feux | Ø 114 mm, 3,4 m (relevé de Meylan) |
| ARB-06 piste bidirectionnelle | Chronovélo 4,00 m, autres 3,00 m (3,50 m souhaitable) ; 2,50 m seulement si le trafic cycliste est très faible, notamment en interurbain, avec un accotement circulable (RVC p. 19) |
| ARB-14 feux | bas du boîtier 2,30 m, répétiteur centré à 1,40 m, potence à 5,0 m |
| ARB-19 STOP issu d'OSM | `highway=stop` seul → régime `stop_a_verifier` (confiance faible), ni AB4 ni ligne ; AB4 si `traffic_sign=FR:AB4` ou confirmation |
| ARB-20 supports sur trottoir étroit | règle de placement : axe à 0,70 + l/2 si 1,40 m restent libres ; sinon support côté façade (axe ≥ 1,40 + r, surplomb ≥ 2,20 m) ; sinon axe réduit signalé « IISR1 8 i, contrainte » |

`parametres_par_defaut` (DEF-001 à DEF-034) donne une valeur par paramètre (u, largeurs, vues de bordure, dévers,
passages, lignes, flèches, sas, zigzag, hachures, refuges, îlots, giratoires, panneaux, feux, durées, visibilité,
arbres, abaissés, quais, ponts, plateaux) avec les règles qui la fondent.

## 7. Relations avec les autres specs du dépôt

`regles_route_fr.json` **ne remplace pas** les specs existantes ; il les cite comme sources (`DEPOT_RC` =
`regles_conception.json`, `DEPOT_RI` = `regles_implantation.json`, `DEPOT_RL` = `regles_locales_meylan.json`,
`DEPOT_MQG` = `marquages_geometrie.json`, `DEPOT_MAT` = `materiaux_sol.json`). Corrections à reporter dans ces specs
(non faites ici, voir l'errata) :

- `marquages_geometrie.json` : correspondance V15 → L lisible (40-50 → 39 m … 120 → 234 m, IISR7 p. 21) ; triangle
  cédez à 5-25 m de la ligne (p. 42) ; colonne `u3_piste_m` à réserver aux lignes tracées sur une piste ; gabarits
  PMR, IRVE et glyphes disponibles dans `D:\DocRoute\08_Marquages_Geometrie_IISR7\marquages_iisr7.json` ;
- `feux.json` : citer l'IISR 6e partie (PDF local) au lieu d'un résumé ; diamètre des répétiteurs non fixé par l'IISR ;
- `bordures_elements.json` (autre équipe) : chartières de 1,00 m à 12 % non conformes à l'arrêté du 15/01/2007.

## 8. Limites

- Les règles du volet 12 (`inference_osm`) et du volet 13 (`observation`) ne sont jamais fusionnées avec les règles
  de conception : elles sont liées par `voir_aussi`.
- Les pages des sources composées du volet 12 (« RC GA-CHA-005 ; IISR7 ») ne sont pas contrôlées automatiquement.
- Sept sources sont seulement en ligne (Légifrance, questions parlementaires, ASAM) : pas de fichier local.
- Les valeurs `choix_generateur` et les arbitrages sont des choix ; une mesure du site les remplace toujours.
