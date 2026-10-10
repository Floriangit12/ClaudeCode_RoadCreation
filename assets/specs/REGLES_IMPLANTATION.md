# Règles d'implantation et résolution des positions

Spec : `assets/specs/regles_implantation.json` (schéma `regles_implantation/0.1`, 66 règles).
Validateur et essai : `recon/pcg/specs_outils/valider_regles_implantation.py`.

## 1. Rôle

Les couches d'objets du paquet (`mobilier.geojson`, `arbres.geojson`) mêlent des positions levées au
centimètre (GAM 2026), mesurées (LiDAR 2021, ortho 5 cm 2022), lues sur photo, prises dans OSM ou
déduites. Une partie tombe au mauvais endroit : panneau sur la chaussée, potelet dans la piste,
lampadaire OSM au fil d'eau, arbre placé au sommet de sa couronne au-dessus d'une piste, azimut
arrondi à 45°. Cette spec donne au pipeline de quoi raisonner :

- **vérifier** qu'un objet est plausible là où il est (surface, recul à la bordure, hauteur, orientation,
  position par rapport à la ligne d'effet, au passage, au nez d'îlot, au quai) ;
- **replacer** un objet qui viole une règle physique ou normative, au plus près, en gardant sa position
  le long de la route, sans dépasser ce que sa preuve autorise ;
- **arbitrer** quand le replacement est impossible : est-ce l'objet qui est faux, ou la surface ?
- **contraindre** les objets déduits ou dispersés (Houdini `pj_*`, PCG UE) ;
- **déduire** les objets obligatoires absents (R12 aux deux extrémités d'une traversée à feux, bouton d'appel).

Principe directeur : la norme sert d'a priori, la preuve tranche. Un objet levé ou mesuré n'est jamais
corrigé au nom d'une norme (la réalité urbaine est souvent non conforme : supports à 0,32 m de la
bordure, AB3a partageant un candélabre). Seules les incohérences physiques (gravité `critique`)
s'imposent à tous.

## 2. Format d'une règle

| champ | contenu |
|---|---|
| `id` | `AAA-00`, unique (GEN, PMR, SIG, FEU, ECL, POT, TC, MOB, BAR, VEG, RES) |
| `famille` | clé de `vocabulaire.familles` |
| `objet_types` | types de `mobilier.geojson` (+ `arbre`, `tete_feu`, `barriere`, `massif`), ou `*` |
| `filtre` (option) | `{propriété: [valeurs]}`, `propriété_exclus`, `propriété_contient`, `type_tete`, `zone` |
| `enonce` | la règle en clair |
| `parametres` | nombres avec suffixe d'unité (`_m`, `_deg`, `_pct`, `_n`, `_ratio`, `_s`...) ; `[a, b]` = intervalle ; `table_*` = table ; `{classe: valeur}` = valeur par classe |
| `surfaces_autorisees` / `surfaces_interdites` | classes de `vocabulaire.classes_surface` (vide = pas de contrainte) |
| `relations` | `[{rel, cible, paramètres suffixés}]`, `rel` dans `vocabulaire.relations` |
| `exceptions` (option) | `[{objet_types, filtre, zones_autorisees, condition, regle}]` |
| `action` | `contraindre`, `verifier`, `deplacer_si_violation`, `deduire_si_absent` |
| `gravite` | `critique`, `majeur`, `mineur`, `info` |
| `source` | `{doc, ref, url}` ; `doc` = clé du registre `sources` (url identique au registre) |
| `sources_complementaires`, `note` (option) | appuis secondaires ; valeurs a priori signalées dans `note` |
| `confiance` | `haute` (texte officiel), `moyenne` (guide, référentiel, observation du site), `faible` (pratique) |

## 3. Vocabulaire

**Surfaces et zones.** Classes de `surfaces_2026` / surfaces v2 (`chaussee`, `trottoir`, `ilot`,
`piste_cyclable`, `quai_bus`, `espace_vert`, `terre_plein_vegetal`, `parking`, `acces_riverain`,
`batiment`, `autre`) et zones dérivées calculées à la volée : `passage_pietons`, `traversee_cyclable`
(marquages v2), `ilot_peint` (hachures, fuseaux), `voie_bus`, `bande_cyclable` (lanes_2026),
`abaisse_traversee`, `palier_abaisse` (abaissés v2), `bev` (ponctuels_sol v2), `cheminement_pmr`,
`bande_fonctionnelle`, `triangle_visibilite`, `stationnement_chaussee`. Chaque zone dérivée déclare
dans quelles classes elle se pose (`dans`) ; la zone retenue en un point suit `precedence_zones`
(la plus spécifique d'abord : un J11 dans un fuseau peint est en `ilot_peint`, pas en `chaussee`).

**Repère d'une bordure.** `s` = abscisse sur l'arête avant, `t` = décalage signé (t > 0 côté haut,
t < 0 côté chaussée ; les bordures v2 sont orientées côté haut à gauche). `t_bord` = t du nu du support,
`d_rive` = distance de l'aplomb de l'extrémité côté chaussée (bord du panneau) à la rive,
`ds` = distance signée le long du couloir (> 0 à l'aval) à la ligne d'effet, au passage ou à la ligne
de cédez-le-passage.

**Azimuts.** Direction vers laquelle regarde la face, nord L93 = 0, sens horaire ; azimut Panoramax
vrai − 2,0086°. Asset face +Y : lacet local = −azimut, `yaw_UE` = −lacet local.

## 4. Index des règles

| id | famille | objets | énoncé (début) | action | gravité | source | conf. |
|---|---|---|---|---|---|---|---|
| GEN-01 | general | panneau, panneau_information, totem_P... | Aucun support vertical ni tronc sur une surface circulée | deplacer_si_violation | critique | IISR1 art. 8, 1er alinéa | haute |
| GEN-02 | general | panneau, panneau_information, totem_P... | Hors des abaissés de traversée (rampe), du palier de 0,80 m derrièr... | deplacer_si_violation | critique | ARR2007 art. 1er, 4° | haute |
| GEN-03 | general | panneau, panneau_information, totem_P... | Recul minimal anti-choc | deplacer_si_violation | majeur | GL_RFX_BARRIERE_2019 page 2 | moyenne |
| GEN-04 | general | * | Objet posé | contraindre | critique | SITE_DONNEES README v2 | haute |
| GEN-05 | general | panneau, support_feux, tete_feu, lamp... | Groupe rigide | contraindre | critique | IISR1 art. 9-1 A | haute |
| GEN-06 | general | * | Doublons | verifier | majeur | PRATIQUE cohérence des couches | moyenne |
| GEN-07 | general | * | Réancrage après travaux | deplacer_si_violation | majeur | SITE_SPECS mobilier.json | moyenne |
| GEN-08 | general | abri_bus, mobilier_publicitaire, pann... | Masques de visibilité | verifier | majeur | CEREMA_PMS_2012 fiches C.3, TC.7, P.4 | moyenne |
| GEN-09 | general | * | Pas d'objet dans l'emprise d'un bâtiment, sauf sur une dalle access... | deplacer_si_violation | critique | SITE_DONNEES mobilier.geojson | haute |
| PMR-01 | cheminement_pmr | * (zone: trottoir, quai_bus, ilot, acces_riverain) | Cheminement piéton continu d'au moins 1,40 m libre de mobilier ou d... | deplacer_si_violation | majeur | ARR2007 art. 1er, 3° | haute |
| PMR-02 | cheminement_pmr | panneau, panneau_information, boite_a... | Au-dessus d'un cheminement | contraindre | majeur | ARR2007 art. 1er, 6° c) et d) | haute |
| PMR-03 | cheminement_pmr | potelet, poteau_incendie, fontaine, c... | Bornes et poteaux détectables à la canne | contraindre | majeur | ARR2012 annexe 3 « Détection d'obstacles » | haute |
| PMR-04 | cheminement_pmr | tete_feu, boite_aux_lettres, distribu... | Commandes manuelles (bouton d'appel piéton, distributeur, borne d'i... | contraindre | majeur | ARR2007 art. 1er, 8° | haute |
| PMR-05 | cheminement_pmr | chicane, potelet, barriere | Un passage sélectif (chicane, potelets serrés) sans alternative lai... | verifier | majeur | ARR2007 art. 1er, 6° e) | haute |
| SIG-01 | signalisation_verticale | panneau | Panneau sur accotement ou trottoir, terre-plein central, îlot bordé... | deplacer_si_violation | critique | IISR1 art. 8, 1er alinéa | haute |
| SIG-02 | signalisation_verticale | panneau | Distance latérale | deplacer_si_violation | majeur | IISR1 art. 8 i) | haute |
| SIG-03 | signalisation_verticale | panneau | Hauteur du bord inférieur du panneau le plus bas | contraindre | majeur | IISR1 art. 9 a), b) | haute |
| SIG-04 | signalisation_verticale | panneau, balise_J11 | Orientation | deplacer_si_violation | majeur | IISR1 art. 8 a) | haute |
| SIG-05 | signalisation_verticale | panneau (code_exclus: D21, D21a, B21a1, J5, B6a1, plaque de rue) | Côté | verifier | majeur | IISR1 art. 8 b) et e) | haute |
| SIG-06 | signalisation_verticale | panneau (code: AB3a, AB4) | Panneau de position | verifier | majeur | IISR3 art. 42-2 C | moyenne |
| SIG-07 | signalisation_verticale | panneau (code: AB2, AB3a, AB6, AB1, AB4) | Carrefour à feux | verifier | majeur | IISR3 art. 42-9 B 2° | haute |
| SIG-08 | signalisation_verticale | panneau | Groupement | verifier | mineur | IISR1 art. 4 B et C | haute |
| SIG-09 | signalisation_verticale | balise_J11 | Balises J11 | deplacer_si_violation | critique | IISR1 art. 9-2 I | haute |
| SIG-10 | signalisation_verticale | panneau (code: J5) | Balise J5 | deplacer_si_violation | majeur | IISR1 art. 9-2 E | haute |
| SIG-11 | signalisation_verticale | panneau (code: B21a1, B21a2, B21b) | Contournement d'îlot (B21a1 « par la droite ») | deplacer_si_violation | majeur | IISR1 art. 8 b) | moyenne |
| SIG-12 | signalisation_verticale | panneau (code: D21, D21a) | Panneaux de direction (D21) | verifier | mineur | IISR1 art. 8 b) | moyenne |
| SIG-13 | signalisation_verticale | panneau | Signalisation pour cyclistes | verifier | mineur | IISR1 art. 8 h) | haute |
| FEU-01 | feux | support_feux | Signal tricolore principal R11 | deplacer_si_violation | critique | IISR6 art. 109-4 | haute |
| FEU-02 | feux | support_feux | Rappel d'un R11 | verifier | majeur | IISR6 art. 110-1 1) | haute |
| FEU-03 | feux | tete_feu, support_feux | Gabarit | contraindre | majeur | IISR6 art. 109-4, fig. 16 | haute |
| FEU-04 | feux | support_feux | Recul du mât de feux | deplacer_si_violation | majeur | SITE_SPECS feux.json / mobilier.geojson | moyenne |
| FEU-05 | feux | tete_feu (type_tete: R11v, R13c) | Orientation des têtes principales | contraindre | majeur | IISR6 art. 109-4 | haute |
| FEU-06 | feux | tete_feu (type_tete: R11v_rep) | Répétiteur | contraindre | majeur | IISR6 art. 109-4, fig. 13-15 | moyenne |
| FEU-07 | feux | tete_feu, support_feux (type_tete: R12, R12m) | Signaux piétons R12 | deduire_si_absent | majeur | IISR6 art. 110-2 1) à 3) | haute |
| FEU-08 | feux | tete_feu (type_tete: boitier_bouton_appel) | Dispositif d'appel / sonore ou tactile | deduire_si_absent | majeur | IISR6 art. 110-2 5) | moyenne |
| FEU-09 | feux | tete_feu (type_tete: R13c, R13b) | Signal modal R13 | verifier | mineur | IISR6 art. 110-3 2) et 6) | haute |
| FEU-10 | feux | support_feux | Un support de feux ne porte pas d'équipement qui nuirait à la perce... | verifier | mineur | IISR6 art. 109-4 | haute |
| ECL-01 | eclairage | lampadaire, mat_camera | Candélabre et mât | deplacer_si_violation | majeur | PRATIQUE recul usuel des candélabres urbains | moyenne |
| ECL-02 | eclairage | lampadaire | Orientation | deplacer_si_violation | mineur | SITE_SPECS mobilier.json pivot_orientation des cand | moyenne |
| ECL-03 | eclairage | lampadaire | Alignement | deplacer_si_violation | mineur | PRATIQUE implantation en file régulière des résea | moyenne |
| ECL-04 | eclairage | lampadaire | Pas régulier | deduire_si_absent | mineur | PRATIQUE conception NF EN 13201 | faible |
| ECL-05 | eclairage | lampadaire | Distance aux arbres | verifier | mineur | MTP_ARBRES_2024 page 2 | moyenne |
| POT-01 | potelets_bornes | potelet | Potelet anti-stationnement | deplacer_si_violation | majeur | PRATIQUE protection des trottoirs contre le stati | moyenne |
| POT-02 | potelets_bornes | potelet | Interdistance d'une file | contraindre | mineur | GL_DIMENSIONS_2010 interdistance hors tout des mobiliers | moyenne |
| POT-03 | potelets_bornes | potelet | Potelet sur une piste cyclable | deplacer_si_violation | majeur | GL_CYCLABLE_2019 p. 124 « Potelets » | moyenne |
| POT-04 | potelets_bornes | potelet, barriere | Aux traversées | verifier | mineur | GL_ACCESS_2021 barrière plutôt que potelets dans l'arro | faible |
| TC-01 | transport_collectif | abri_bus | Abri voyageurs sur le quai | deplacer_si_violation | majeur | ARR2007 art. 1er, 12° | haute |
| TC-02 | transport_collectif | poteau_arret | Poteau d'arrêt | deplacer_si_violation | majeur | CEREMA_ARRETS_BUS_2018 § 4.1.1 poteau d'arrêt | haute |
| TC-03 | transport_collectif | banc, corbeille, distributeur, poteau... | Aire de rotation d'un fauteuil de 1,50 m de diamètre libre devant l... | deplacer_si_violation | majeur | ARR2007 art. 1er, 12° | haute |
| MOB-01 | mobilier_urbain | banc, corbeille, distributeur, mobili... | Mobilier de confort | deplacer_si_violation | majeur | ARR2007 art. 1er, 3° et 6° | moyenne |
| MOB-02 | mobilier_urbain | banc | Banc | contraindre | mineur | PRATIQUE usage des bancs en bord de voie | faible |
| MOB-03 | mobilier_urbain | corbeille | Corbeille | verifier | mineur | GL_ACCESS_2021 éviter les poubelles sur potelets au niv | moyenne |
| MOB-04 | mobilier_urbain | stationnement_velos | Arceaux vélos | contraindre | mineur | GL_CYCLABLE_2019 p. 108-110 | moyenne |
| MOB-05 | mobilier_urbain | mobilier_publicitaire, panneau_inform... | Affichage, conteneurs, distributeurs | verifier | mineur | CEREMA_PMS_2012 fiche 15 TP | moyenne |
| BAR-01 | barrieres_acces | barriere | Barrière de ville | deplacer_si_violation | majeur | GL_RFX_BARRIERE_2019 pages 1-2 | moyenne |
| BAR-02 | barrieres_acces | cloture | Clôtures levées (GAM) | verifier | info | SITE_DONNEES mobilier.geojson | haute |
| BAR-03 | barrieres_acces | portail, barriere_levante, chicane | Portails, barrières levantes, chicanes | verifier | info | ARR2007 art. 1er, 6° e) | moyenne |
| VEG-01 | vegetation | arbre | Tronc jamais sur chaussée, voie bus, piste ou bande cyclable, passa... | deplacer_si_violation | critique | CEREMA_PMS_2012 fiche V.4 | haute |
| VEG-02 | vegetation | arbre | Recul du tronc à l'arête avant de la bordure, au moins la demi-larg... | deplacer_si_violation | majeur | MTP_ARBRES_2024 page 1 | moyenne |
| VEG-03 | vegetation | arbre | Pour les arbres déduits ou issus du plan 2025 | verifier | mineur | MTP_ARBRES_2024 page 1 | moyenne |
| VEG-04 | vegetation | arbre | Gabarit sous houppier | contraindre | majeur | GL_DIMENSIONS_2010 gabarits | moyenne |
| VEG-05 | vegetation | massif, arbre | Triangles de visibilité et nez d'îlots | contraindre | majeur | CEREMA_PMS_2012 fiches C.3, TC.7 | moyenne |
| VEG-06 | vegetation | arbre (source_contient: sommet du MNH) | Arbre positionné au sommet de couronne LiDAR | deplacer_si_violation | majeur | SITE_DONNEES arbres.geojson | moyenne |
| RES-01 | reseaux_techniques | armoire | Armoire technique ou de commande des feux | deplacer_si_violation | majeur | PRATIQUE implantation usuelle des coffrets | faible |
| RES-02 | reseaux_techniques | poteau_reseau | Poteau de réseau (bois, béton) | deplacer_si_violation | majeur | PRATIQUE implantation usuelle des supports de rés | faible |
| RES-03 | reseaux_techniques | poteau_incendie | Poteau d'incendie | verifier | mineur | PRATIQUE règlements départementaux de défense ext | faible |

Paramètres clés :

- **Signalisation** (IISR 1re partie) : uniquement sur accotement, trottoir, terre-plein, îlot bordé
  (jamais d'îlot peint) ; bord du panneau à 0,70 m de la rive, moins en agglomération (plancher retenu :
  pas de débord au-dessus d'une voie, support à 0,30 m) ; bas du panneau jusqu'à 2,30 m en agglomération
  éclairée, 2,20 m au moins au-dessus d'un cheminement, 1,00 m sinon, moins sur îlot directionnel ;
  face perpendiculaire aux usagers visés, tournée de 3 à 5° vers l'extérieur, jamais à 88-92° du
  faisceau ; à droite ; AB3a/AB4 au plus près de la chaussée abordée, dans le plan des feux en carrefour
  à feux ; J11 à 0,50 m au-delà de la ligne continue, jamais sur la partie circulée ; J5 sur le nez
  d'îlot, bas à 1,00 m.
- **Feux** (IISR 6e partie) : R11 à droite du couloir, au droit ou juste à l'aval de la ligne d'effet
  (sans ligne : avant le passage, R412-30), jamais à l'aval des conflits ; 2,00 m dégagés sous les têtes
  sur surface piétonne, axe du feu haut < 4,20 m ; répétiteur bas (1,4 m sur le site) visant le premier
  véhicule arrêté ; R12 sur le trottoir de destination, à chaque extrémité, support dans le
  prolongement du passage à la limite de la BEV (Cerema) ; bouton à 0,90-1,30 m.
- **Accessibilité** (arrêté du 15 janvier 2007, annexe 3 de 2012) : cheminement de 1,40 m (1,20 m sans
  obstacle latéral) ; 2,20 m sous porte-à-faux ; abaissé ≥ 1,20 m et palier de 0,80 m libres ; bornes
  h ≥ 0,50 m, largeur 0,28 m à 0,50 m de haut, 0,06 m à 1,10 m ; abri : 0,90 m (1,40 m) entre nez de
  quai et abri, aire de 1,50 m devant la porte avant.
- **Éclairage, potelets, mobilier, réseaux** (pratique, référentiels lyonnais, observations du site) :
  candélabre à 0,50-1,00 m de l'arête avant, crosse vers la chaussée, rangées alignées et régulières ;
  potelets à 0,30-0,50 m, entraxe 1,20-1,60 m ; mobilier en bande fonctionnelle (0,50 m) ou adossé ;
  arceaux : interdistances par angle (90° : 0,90 / 1,00 m) ; barrières à 0,30 m mini de la chaussée.
- **Végétation** (fiche Montpellier 2024, Grand Lyon) : tronc à 0,75 / 1,00 / 1,50 m de la bordure
  (petit, moyen, grand développement), houppier à 3,80 m au-dessus de la chaussée, 2,20 m au-dessus du
  trottoir ; massifs ≤ 0,60 m dans les triangles de visibilité.

## 5. Résolution

**Politique.** `critique` : contrainte dure pour tous. `majeur` : dure si σ ≥ 0,5 m (OSM, constat, plan,
a priori, déduit), seulement signalée sinon. `mineur` : coût. Une règle `verifier` devient une
contrainte pour un objet a priori. Ordre : sécurité de circulation > accessibilité > réglementation >
pratique > alignements.

**Qualité de la preuve** (classe choisie par motifs regex sur le champ `source` ; la meilleure gagne) :

| classe | σ (m) | déplacement max sans photo (m) |
|---|---|---|
| gam (levé 2026) | 0,05 | 0,5 |
| lidar2021 (pied, tête, amas) | 0,15 | 0,75 |
| ortho2022 (pied, ombre) | 0,25 | 1,0 |
| terrain2026 / photo utilisateur | 0,3 | 1,0 |
| photo_pnp (≥ 2 rayons, pose ≤ 0,5°) | 0,3 (calculé) | 1,5 |
| plan2025 | 0,5 | 1,5 |
| constat, osm, inventaire, lidar2021_couronne | 1,0 | 2,0 |
| panoramax_brut (pose GNSS, caps faux de 0,5 à 9,4°) | 1,5 | 3,0 |
| a_priori | 2,0 | 5,0 |

Pour une classe non mesurée, σ = max(σ classe, σ confiance de l'objet : 0 / 0,5 / 1,5) et
d_max = max(d_max classe, 2σ), plafonné à 5 m. Les objets d'un même support (champ `poteau`, support
citant un autre objet) partagent la meilleure preuve du groupe.

**Algorithme** (déterministe) : normaliser → grouper et dédoublonner → contexte (bordure de référence,
(s, t), zone selon la précédence, voie visée) → réancrer si la preuve précède les travaux et que la
bordure a bougé → évaluer → chercher sur la normale à la bordure en s₀ (pas 0,05 m, côté haut d'abord),
puis en grille (Δs 0,10 m) si besoin, ou d'abord en s pour une violation longitudinale (passage,
abaissé, porte avant) → choisir le candidat de coût J = (Δt/σ)² + 4(Δs/σ)² + termes mineurs →
orienter (azimut recalculé s'il est grossier ou non mesuré) → poser (z du sol, hauteurs) → tracer
(`prov.position = regle:implantation.<ID>`).

**Arbitrage** quand aucun candidat n'existe dans d_max :
- *anomalie de surface* : objet bien prouvé (σ ≤ 0,25 m) sur une surface interdite de classe faible
  ou loin de toute bordure → on garde l'objet et on signale l'îlot, le refuge ou la bordure manquants ;
- *photo* : objet faiblement prouvé → photo Panoramax valide (date postérieure à la dernière
  modification de la zone, pose PnP ≤ 0,5° en 360° ou ≤ 8 px à plat, ≤ 25 m, 2 rayons à ≥ 15°, ou
  1 rayon coupé avec la bande de recul admissible) ; la position photo l'emporte même au-delà de d_max ;
- sinon : candidat a priori avec `conf faible` et drapeau `a_verifier_terrain2026`, ou objet non
  instancié s'il reste sur une voie circulée. Jamais de déplacement au-delà de d_max sans photo,
  jamais plus de 0,5 m pour un objet GAM, jamais de clôture déplacée.

**Sortie** : `implantation_resolue.json` par couche (position source et résolue, Δs, Δt, azimuts, z,
classe de preuve, σ, d_max, règles violées et appliquées, statut parmi `conforme`, `corrige`,
`reoriente`, `reancre`, `conforme_signale`, `anomalie_surface`, `a_arbitrer_photo`, `non_resolu`,
`deduit`, `fusionne`, drapeau `instancier`, provenance).

## 6. Essai sur `mobilier.geojson`

`python recon/pcg/specs_outils/valider_regles_implantation.py --essai` applique les règles de surface
(gravité critique ou majeure) aux 153 objets ponctuels, avec la classe de surface v1 et la distance non
signée à la bordure GAM (indicatif : ni zones dérivées ni bordures orientées). Résultat (10/10/2026) :

```
Essai sur recon\out\paquet_jardin\package\donnees\objets\mobilier.geojson : 153 objets ponctuels
classes de preuve (après groupes de support) : a_priori 4, constat 13, lidar2021 8, ortho2022 7, osm 97, panoramax_brut 12, plan2025 12
balise_J11_REV_1               balise_J11      chaussee        d_bord= 4.00 preuve=constat        sigma=1.00 d_max=2.00 besoin>= 4.30 a_verifier_zone_derivee [GEN-01, SIG-09]
balise_J11_REV_2               balise_J11      chaussee        d_bord= 3.90 preuve=constat        sigma=1.00 d_max=2.00 besoin>= 4.20 a_verifier_zone_derivee [GEN-01, SIG-09]
lamp_12758894668               lampadaire      batiment        d_bord=31.72 preuve=osm            sigma=1.00 d_max=2.00 besoin>=32.02 a_arbitrer_photo [GEN-09]
pan_D21_1                      panneau         chaussee        d_bord= 5.71 preuve=lidar2021      sigma=0.15 d_max=0.75 besoin>= 6.01 anomalie_surface [GEN-01, SIG-01] groupe=poteau:D21_REV
pan_D21_2                      panneau         chaussee        d_bord= 5.71 preuve=lidar2021      sigma=0.15 d_max=0.75 besoin>= 6.01 anomalie_surface [GEN-01, SIG-01] groupe=poteau:D21_REV
pan_J5_2                       panneau         chaussee        d_bord= 5.83 preuve=constat        sigma=1.50 d_max=3.00 besoin>= 6.13 a_arbitrer_photo (non instancié d'ici là) [GEN-01, SIG-01, SIG-10]
portail_13827066643            portail         batiment        d_bord= 1.43 preuve=osm            sigma=1.00 d_max=2.00 besoin>= 1.73 deplacable [GEN-09]
poteau_bois_REV_ilot           poteau_reseau   chaussee        d_bord= 4.11 preuve=ortho2022      sigma=0.25 d_max=1.00 besoin>= 4.41 anomalie_surface [GEN-01, RES-02]
potelet_13827066657            potelet         chaussee        d_bord= 0.30 preuve=osm            sigma=1.00 d_max=2.00 besoin>= 0.60 deplacable [GEN-01, POT-01]
potelet_13827066658            potelet         chaussee        d_bord= 2.87 preuve=osm            sigma=1.00 d_max=2.00 besoin>= 3.17 a_arbitrer_photo (non instancié d'ici là) [GEN-01, POT-01]
potelet_REV_3                  potelet         chaussee        d_bord= 0.59 preuve=constat        sigma=1.00 d_max=2.00 besoin>= 0.89 deplacable [GEN-01, POT-01]
potelet_REV_NE_2               potelet         piste_cyclable  d_bord= 0.88 preuve=ortho2022      sigma=0.25 d_max=1.00 besoin>= 1.18 conforme_signale [POT-03]
statuts : a_arbitrer_photo 3, a_verifier_zone_derivee 2, anomalie_surface 3, conforme_signale 1, deplacable 3
azimuts multiples de 45° (grossiers si non mesurés sur photo : à recalculer par SIG-04, FEU-05, ECL-02, TC-01) : 32 sur 106 (abri_bus 2, lampadaire 2, panneau 16, poteau_arret 2, stationnement_velos 1, support_feux 8, totem_PR 1)
(besoin = distance non signée à la bordure GAM + 0,30 m : borne basse du déplacement pour quitter la surface interdite ; classe de surface v1 surfaces_2026, sans zones dérivées)
```

Lecture :
- les panneaux D21 de la Revirée (`D21_REV`, amas LiDAR 2021 de 1,2 m) et le poteau bois de l'îlot
  axial (ombre ortho 2022, photos 2024 et 2025) sont bien prouvés et à 4 à 6 m de toute bordure GAM :
  ce ne sont pas eux qui sont faux, c'est `surfaces_2026` qui n'a pas l'îlot axial de la Revirée ;
- les deux J11 sont à confirmer dans le fuseau peint (`ilot_peint`), où ils sont conformes ;
- `potelet_13827066657` et `potelet_REV_3` (0,3 et 0,6 m sur la chaussée, OSM ou constat) sont
  replacés derrière la bordure ; `pan_J5_2`, `potelet_13827066658` et `lamp_12758894668` demandent
  une photo (la J5 indique de plus un nez d'îlot absent des surfaces) ;
- `potelet_REV_NE_2` dans la piste est gardé et signalé (preuve ortho, règle majeure POT-03) ;
- 32 azimuts sur 106 sont des multiples de 45° (16 panneaux, 8 supports de feux) : à recalculer par
  SIG-04, FEU-05, ECL-02, TC-01 s'ils ne sont pas mesurés sur photo.

## 7. Sources

Officielles : IISR 1re partie VC_20250904 (art. 4, 6-9, 9-1, 9-2), 3e partie (art. 42-2, 42-9),
6e partie VC20250904 (art. 109-4, 110-1 à 110-3), 7e partie (117-4) ; arrêté du 15 janvier 2007 (art. 1er)
et arrêté du 18 septembre 2012 (annexe 3) ; code de la route R412-30 ; code de la voirie routière
L118-5-1. Guides : Cerema points d'arrêt accessibles (2018), Certu/Cerema fiche BEV 03 (2010), fiches
d'audit de sécurité urbain (2012). Référentiels locaux : Métropole de Lyon (fiches réflexes ligne
d'effet, passages, barrières ; dimensions 2010 ; guide cyclable 2019 ; recueil accessibilité 2021),
Montpellier (distances de plantation 2024). Site : `assets/specs/{feux,panneaux,mobilier}.json`,
couches objets du paquet. URL et chemins locaux dans le registre `sources` du JSON.

Téléchargés pour cette spec (`data/raw/normes/`, hors git) :
`cerema/iisr_1epartie_vc_20250904.pdf`,
`accessibilite/arrete_15janvier2007_voirie_prescriptions_cantal.pdf`,
`accessibilite/abaque_obstacles_bas_2012_seine_et_marne.pdf`,
`metropoles/grandlyon_RFX_barriere_2019.pdf`,
`metropoles/montpellier_distances_plantation_espace_aerien_2024.pdf`.

## 8. Limites

- Valeurs a priori (confiance faible, signalées en `note`) : recul des candélabres et armoires,
  intervalle AB3a-ligne, distance au nez d'îlot des J5/B21, point de visée des répétiteurs, poteaux
  d'incendie (RDDECI de l'Isère non consulté), pas des candélabres.
- Le calcul des zones dérivées (triangles de visibilité, cheminement, bande fonctionnelle) et
  l'algorithme de résolution complet restent à coder dans `recon/pcg/decrire` ; l'essai n'utilise que
  la classe v1 et une distance non signée.
- Aucune photo après les travaux : en zone de travaux 2025, l'arbitrage photo est impossible, les
  objets restent a priori jusqu'à la prise de vue `terrain2026`.
