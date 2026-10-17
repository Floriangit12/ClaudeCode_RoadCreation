# Rapport du lot L1 : lecture du modèle, graphe, profils (courbes de contrôle)

*`recon/generateur/validation/RAPPORT_L1.md` — 17/10/2026. Données chiffrées : `rapport_L1.json` et `controles_L1.json`,
produits par `python recon/generateur/validation/faire_rapport_L1.py` (rejoue tout : construction des HDA, fabrication,
robustesse, contrôles indépendants, témoins négatifs, dessins et tuiles ; aucune date ni durée écrite). Houdini 22.0.459
Indie (hython), VEX interprété (JIT coupé). Base de règles lue, non modifiée : `regles_route_fr/1.0` (SHA-256 `d4d63ede…`).*

**Statut : ok** — les 13 critères sont atteints.

## 1. Ce que le lot apporte

On écrit une route simplement (« trottoir 2 | voie ← | voie → | trottoir 2 », un rabattement ici, un plateau là), le
compilateur du lot L0 en fait un modèle `modele_voie/0.1`, et **Houdini le fabrique** maintenant en courbes de
contrôle exactes : la ligne de référence échantillonnée, chaque limite de bande (bordure, marquage, limite virtuelle)
à sa position, les rubans de chaque bande, les coupes de début et de fin, et le profil en long de la chaussée (plateaux,
dos-d'âne). C'est le squelette sur lequel le lot L2 posera les surfaces, les bordures en éléments et les caniveaux,
puis les rendus Karma.

```
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S09_reduction_2_vers_1_voie.yaml
  -> recon/out/generateur/S09/modele_voie.json        (description -> modèle, compilateur L0)
  -> recon/out/generateur/S09/l1/courbes_controle.json (rg::lire_modele -> rg::graphe -> rg::profils)
python recon/generateur/validation/dessiner_L1.py S09 --tuiles   (plan de contrôle et tuiles natives)
```

Trois HDA nouvelles, dans l'espace `rg::` (« route générée »), construites avec le même outillage que les HDA `pj::`
(dossiers `.hdalc` développés, signature de construction) : `rg::lire_modele`, `rg::graphe`, `rg::profils`
(`recon/generateur/hda/README_RG.md`). Houdini n'invente rien : chaque cote vient du modèle, la seule valeur ajoutée
par une HDA est la rampe des plateaux, absente du schéma 0.1 (paramètre dont le défaut est écrit depuis DEF-034, 7 %).

## 2. Critères

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L1-1 HDA `rg::lire_modele`, `rg::graphe`, `rg::profils` : dossiers développés, signature stable, reconstruction identique à l'octet | 3 / 3 ; signatures stables (`e842abca…`, `c0e141d0…`, `787681f8…`), dossiers identiques après deux reconstructions | 3 / 3 | oui |
| L1-2 pilote `fabriquer_generateur.py` : entrée description simple et entrée modèle | descriptions 27 / 27 (S01-S12, 12 exemples du format, 3 essais) ; modèle OSM réel 1 / 1 (69 routes) | 100 % | oui |
| L1-3 échantillonnage à flèche ≤ 0,5 mm (référence et toutes les limites décalées, mesure indépendante) | max 0,452 mm : arc 0,452, clothoïde 0,379, droite 0,016 mm (27 844 cordes de limites, 4 272 de référence) | ≤ 0,5 mm | oui |
| L1-4 écart des limites décalées à la position analytique, mesuré au milieu des cordes | droite 0,009 mm ; arc 0,452 mm ; clothoïde 0,379 mm ; sommets : max 0,016 mm | ≤ 1 mm par type | oui |
| L1-5 0 bande de largeur négative ou nulle | 0 négative ; 0 nulle hors extrémité de biseau (6 extrémités : bande qui naît ou disparaît à une jonction) | 0 | oui |
| L1-6 0 chevauchement | réunion des rubans = somme des aires à 6,1e-12 m² près (bruit numérique) ; 0 repli (1 − tκ ≤ 0) ; 0 limite inversée ; 0 ruban invalide | 0 (≤ 1e-6 m²) | oui |
| L1-7 sections contiguës de 0 à L (modèle et sorties) | 27 / 27 scènes, 83 sections | 100 % | oui |
| L1-8 transitions de profil continues aux jonctions de sections | 55 jonctions continues, écart max 0,000 mm ; 1 changement instantané déclaré (ex10, s = 140 m, bande cyclable de 1,50 m, `transition_entree : instantanee`) compté à part | ≤ 1 mm | oui |
| L1-9 transitions verticales (plateaux, dos-d'âne) | dz exporté contre analytique : 0,001 mm ; flèche du profil en long : 0,395 mm | ≤ 1 mm ; ≤ 0,5 mm | oui |
| L1-10 sommets obligatoires (raccords, sections, lois de largeur, abaissés et marquages, ralentisseurs) | 0 manquant | 0 | oui |
| L1-11 déterminisme (deux processus) | 54 fichiers (`courbes_controle.json`, `manifest_l1.json`) identiques à l'octet ; HDA reconstruites identiques | 100 % | oui |
| L1-12 S01-S12 en courbes de contrôle, regardées en tuiles natives | 12 / 12 fabriquées, 12 / 12 regardées ; 26 tuiles regardées sur 79 produites | 12 / 12 | oui |
| L1-13 témoins négatifs détectés par le contrôle indépendant | 4 / 4 (§ 4) | 100 % | oui |

Les critères L1 du plan (§ 3) sont L1-3, L1-4, L1-5, L1-6, L1-7 et L1-8 ; les autres vérifient le livrable
(HDA, pilote, déterminisme, scènes regardées) et la capacité du contrôle à trouver une erreur.

## 3. Mesures

**Méthode, indépendante du VEX.** `validation/analytique_L1.py` relit le modèle et recalcule tout en double précision
sans code commun avec les HDA : droites et arcs en forme fermée, clothoïdes par quadrature adaptative
(`scipy.integrate.quad`, table à 0,02 m interpolée en Hermite avec la tangente exacte) alors que le VEX intègre par
Gauss-Legendre composite ; positions t des limites par cumul des lois de largeur ; loi verticale des ralentisseurs.
`validation/controler_L1.py` mesure, pour chaque corde de la référence et de chaque limite : la flèche (33 points
puis raffinement), la distance du milieu de la corde à la courbe analytique (section dorée), l'écart des sommets ;
puis les largeurs, la réunion des rubans (shapely), les replis, les jonctions (coordonnées exportées), la loi
verticale et les sommets obligatoires (recalculés depuis le modèle).

| Courbe | Type | Cordes | Flèche max | Milieu de corde max | Sommets max |
|---|---|---|---|---|---|
| limites | droite | 21 842 | 0,016 mm | 0,009 mm | 0,016 mm |
| limites | arc | 4 708 | 0,452 mm | 0,452 mm | 0,015 mm |
| limites | clothoïde | 1 294 | 0,379 mm | 0,379 mm | 0,009 mm |
| référence | droite / arc / clothoïde | 3 308 / 724 / 240 | 0,010 / 0,435 / 0,350 mm | idem | ≤ 0,010 mm |

- Pas : visé à flèche × marge = 0,45 mm, avec un majorant de |P''| sur toutes les limites de l'intervalle (arc de 60 m,
  limite à 5 m : 0,446 m ; arc de 25 m de E3, limite extérieure à 13,5 m : 0,247 m) ; pas maximal 1 m en droite.
  La marge couvre le stockage des sommets en flottants 32 bits (écart des sommets ≤ 0,016 mm).
- Information : aires des rubans (quadrilatères Houdini) contre l'aire analytique ∫ [w − κ (t_g² − t_d²)/2] ds :
  écart relatif max 1,2e-4 (cordes en courbe) ; raccords des primitives du modèle : 5,8e-7 m et 3,9e-7° ;
  `longueur_m` (arrondie à 0,1 mm par le compilateur) contre somme des primitives : 4,7e-5 m.
- Scènes : 12 du catalogue (S01-S12, une seule courbe : S11), 12 exemples du format (dont ex05, scène E du plan sans
  carrefour ; ex01 et ex11 en courbe) et 3 essais du lot, écrits dans le format parce qu'aucune scène n'avait de
  clothoïde : `validation/essais_L1/E1_rue_clothoides.yaml` (clothoïdes de 30 m vers et depuis R 60),
  `E2_rue_s_rabattement_ralentisseurs.yaml` (courbe en S, clothoïde de +1/80 à −1/80, rabattement dans la courbe,
  plateau et dos-d'âne), `E3_avenue_courbe_serree.yaml` (27 m d'emprise sur un arc de 25 m).

## 4. Témoins négatifs (le contrôle doit refuser une sortie fausse)

| Témoin | Mesure | Détecté |
|---|---|---|
| `rg::graphe` réglé à une flèche de 5 mm (S11, E1 ; pas plafonné à 1 m) | flèche 2,248 mm | oui |
| un sommet d'une limite de S09 déplacé de 3 mm latéralement | sommet 3,000 mm, milieu de corde 1,496 mm | oui |
| ex10 sans `transition_entree : instantanee` | jonction non déclarée de 1,500 m | oui |
| une limite de S02 portée au-delà de sa voisine | 101 largeurs négatives, recouvrement 100 m² | oui |

## 5. Livrables

| Fichier | Rôle |
|---|---|
| `hda/README_RG.md` | conventions, entrées-sorties et attributs des HDA `rg::*`, commandes, limites |
| `hda/commun/rg_hda_outils.py`, `hda/commun/vex/rg_geometrie.h` | construction des HDA (signature, VEX 64 bits) ; bibliothèque VEX (primitives, lois, positions t, loi verticale) |
| `hda/rg_lire_modele/{construire.py, lecteur.py, rg_lire_modele.hdalc/}` | lecteur unique du modèle : 5 sorties (routes, nœuds, zones et îlots, ponctuels, profils), erreurs explicites |
| `hda/rg_graphe/{construire.py, rg_graphe.hdalc/}` | échantillonnage à flèche ≤ 0,5 mm sur toutes les limites, sommets obligatoires, branches triées aux nœuds |
| `hda/rg_profils/{construire.py, rg_profils.hdalc/}` | limites décalées par section, rubans, profils d'extrémité, profil en long ; contrôles internes |
| `fabriquer_generateur.py` | pilote hython : description `.yaml` (compilée par le Python du système) ou modèle `.json` → courbes de contrôle, manifeste, `--verifier-determinisme`, `--hip` |
| `validation/analytique_L1.py`, `controler_L1.py`, `dessiner_L1.py`, `faire_rapport_L1.py` | géométrie analytique indépendante, contrôles, plans de contrôle et tuiles, rapport |
| `validation/essais_L1/E1…E3.yaml` | descriptions d'essai (clothoïdes, courbe en S, courbe serrée) |
| `validation/rapport_L1.json`, `controles_L1.json`, `constats_visuels_L1.json`, ce rapport | rapport du lot |
| `recon/out/generateur/<scene>/l1/` (non versionné) | `courbes_controle.json`, `manifest_l1.json`, `plan_l1.png`, détails, profils en long, tuiles |

## 6. Corrections du compilateur de description (lot L0) révélées par le lot L1

Le lot L1 mesure la géométrie au demi-millimètre ; deux défauts du compilateur sont apparus et ont été corrigés dans
`description/description_vers_modele.py` (version précédente gardée dans `tmp/l1/description_vers_modele.py.avant_L1`).
`faire_rapport_L0.py` relancé ensuite : les 12 critères du lot L0 restent atteints ; seules les empreintes de 4 modèles
changent (ex01, ex10, ex11, S11).

1. **Courbures arrondies à 1e-4 m⁻¹** (arrondi général du modèle à 4 décimales) : la courbure 1/60 devenait 0,0167,
   soit un arc de 59,88 m dont la fin tombait à 6 cm du départ de la droite suivante (S11) ; même défaut sur ex01
   (R 150 → 0,0067) et ex11. La géométrie régulière est désormais écrite au µm (positions, longueurs), au 1e-9 degré
   (caps) et à 1e-12 m⁻¹ (courbures) : raccords à 5,8e-7 m.
2. **Changement de profil sans transition non déclaré** : ex10 (« à 140 m une bande cyclable apparaît : changement
   instantané ») produisait un décroché de 1,50 m de la bordure que rien ne distinguait d'une erreur. Le compilateur
   écrit maintenant `transition_entree : {type: instantanee}` (champ du schéma) sur la section qui commence au
   changement dit sans transition, ou dont la transition est impossible (bandes différentes) ; `rg::profils` et le
   contrôle comptent ces jonctions à part.

## 7. Revue visuelle

Plans de contrôle dessinés depuis les seules sorties de Houdini (`dessiner_L1.py` : rubans colorés par type de bande,
bordures en noir, marquages en blanc, limites virtuelles en tireté, référence en rouge, sommets obligatoires en bleu,
sommets d'échantillonnage en rouge dans les détails), découpés en tuiles natives par `decoupe.py image` ; 26 tuiles
regardées, consignées dans `constats_visuels_L1.json` : S01-S12 toutes conformes (rabattement de S09, avancées de S03,
plateau de S10, dos-d'âne de S08, arc de S11), essais E1-E3 conformes, ex05, ex06, ex09, ex10 conformes ; extrait OSM réel : replis aux sommets anguleux (§ 8). Deux constats
ont changé le code : le sommet du dos-d'âne tombait entre deux sommets (ajouté comme sommet obligatoire) ; l'écart de
6 cm au raccord de S11 a conduit à la correction 1 du § 6. Aucune photo de tiers n'a été utilisée.

## 8. Problèmes, règles et limites

- **Schéma 0.1 : la rampe d'un plateau n'est pas portée** (seulement longueur totale et hauteur). `rg::graphe` et
  `rg::profils` prennent DEF-034 (7 %) ; une rampe dite autrement dans la description est perdue avant Houdini (déjà
  listée par le lot L0 parmi les valeurs non portées). À ajouter au schéma 0.2.
- **Pas maximal en droite : 1 m, sans règle** (choix de fabrication, paramètre de `rg::graphe`, repris dans le manifeste).
- **Routes en polyligne (inférence OSM)** : décalage en onglet aux sommets ; sur l'extrait réel du site (69 routes),
  les décalés intérieurs se replient aux sommets anguleux du tracé OSM (5 routes, 14 cordes inversées, 1 ruban
  invalide, écart de Hausdorff jusqu'à 0,70 m dans ces replis). Hors des critères du lot (géométries régulières),
  mais à traiter avant les carrefours : régularisation du tracé (droites et arcs ajustés) ou nettoyage des boucles
  (PolyExpand2D, prévu par 12A). Les routes se recouvrent aux nœuds : solveur de carrefours au lot L3.
- **À fabriquer au lot L2** : segment de bordure transversal des changements instantanés (ex10) et retours de bordure
  des avancées (S03) ; coussins (ralentisseurs locaux, restés en ponctuels) ; niveaux, vues et dévers (nivellement).
- **Refusés explicitement** (aucune instance ne les utilise) : primitive `parampoly3`, interpolation `cubique_lisse`
  (non définie par le schéma 0.1), transitions d'entrée `lineaire`, `biseau_iisr`, `clothoide` (le compilateur écrit
  les transitions en lois de largeur).
- `longueur_m` est arrondie à 0,1 mm par le compilateur alors que la géométrie régulière est au µm : écart de 4,7e-5 m
  en bout de route, sans effet (la route finit à `longueur_m`).
- Outillage : le Python de Houdini n'a pas `jsonschema` ; le pilote compile les descriptions avec le Python du système,
  dans un environnement débarrassé des variables de Houdini (sinon le Python 3.11 charge la bibliothèque du 3.13).
  Signature de construction : un subnet créé après une autre HDA dans la même session avait ses drapeaux d'affichage
  à faux, ce qui changeait la signature d'une session à l'autre ; corrigé dans `rg_hda_outils.sous_reseau`
  (drapeaux posés, conteneur vidé). **Le même défaut existe dans `recon/pcg/houdini/hda/commun/pj_hda_outils.py`**
  (non modifié : outillage des HDA `pj::`). Le message « Unable to find dialog script » affiché à la reconstruction
  d'une HDA est sans effet.
- Écritures : tout sur D: ; les dossiers temporaires de hython sont redirigés vers `recon/generateur/tmp/hython` ;
  hython peut écrire ses préférences dans le profil de l'utilisateur (exécution autorisée). Pas de git ; DocRoute et
  les specs de l'autre équipe seulement lus.

## 9. Reproduction

```
python recon/generateur/validation/faire_rapport_L1.py               # tout le lot (~1 min 30)
hython recon/generateur/fabriquer_generateur.py DESCRIPTION.yaml|MODELE.json [--verifier-determinisme] [--hip]
python recon/generateur/validation/controler_L1.py recon/out/generateur/<scene> [--json SORTIE]
python recon/generateur/validation/dessiner_L1.py <scene> --tuiles
```
