# Plan de l'étape 4 : imaginer des routes françaises plausibles

*`recon/generateur/PLAN_ETAPE4.md`, 22/10/2026. Lot « plan de l'étape 4 ». Il s'appuie sur quatre rapports :
l'inventaire des lacunes (`ETAPE4_LACUNES.md` et `etape4_lacunes.json`), les règles complémentaires
(`D:\DocRoute\18_Ouvrages_Autoroutes_VoiesRapides_Equipements`), les descriptions humaines
(`D:\DocRoute\19_Descriptions_Routes_Humaines`) et les typologies observées sur images
(`D:\DocRoute\20_Typologies_Routes_France_Images`). Ce document est un plan. Aucun code n'a été modifié. Le seul autre
fichier touché est `D:\DocRoute\INDEX_DOCUMENTATION.md`, auquel les sections 18, 19 et 20 ont été ajoutées.*

## 0. En bref

- **Nouvelle orientation.** L'utilisateur veut *imaginer* des routes françaises plausibles à partir d'images réelles
  (Meylan, l'Isère, la France), et non plus reconstruire Meylan au centimètre. Meylan reste un cas d'usage.
  L'étape 4 donne au générateur deux choses : un **mode « imagination »** (§ 3) et les **fonctionnalités qui lui
  manquent** pour fabriquer ce qu'il imagine (§ 2).
- **Mode « imagination »** (§ 3). En entrée : une phrase, ou une typologie T01 à T12, avec en option la fiche d'une photo
  de référence. En sortie : une description au format existant, que le compilateur et Houdini savent déjà fabriquer.
  Chaque valeur porte sa provenance, dans cet ordre de préférence :
  1. la phrase ou la photo ;
  2. une règle (RF, RC, RI) ;
  3. une loi observée sur photos (lot 20), bornée par les règles ;
  4. une statistique du corpus (lot 19) ;
  5. un arbitrage déclaré ;
  6. sinon, la valeur reste « à dire ».

  L'aléa est contrôlé par une graine : une même entrée donne les mêmes octets. Trente cohérences sont vérifiées, dont
  les quinze du lot 19. Dix phrases d'exemple sont données avec la scène qu'elles doivent produire (§ 3.14). Un exemple
  chiffré (typologie T07, variante 3) a été compilé à blanc, en mémoire : 0 non-conformité (§ 3.13).
- **Backlog** (§ 2) : 38 éléments, de BK-01 à BK-38. Chacun a sa fiche : règles citées, assets, HDA à créer ou à étendre,
  scène de test, critères mesurables, effort. Le classement part du score de l'inventaire (impact × fréquence). Deux
  bonus s'y ajoutent : un pour les typologies observées, un pour les fonctionnalités citées par le corpus. Les leviers
  de la nouvelle orientation et la priorité déjà exprimée par l'utilisateur (zone de conflit) passent en tête.
- **Workflow parallèle.** Les ponts et ouvrages (`rg::ouvrages`) et la signalisation verticale avec les feux (lot L6,
  `rg::signalisation`) sont déjà bien avancés : les fichiers ont été lus, sans rien y écrire. Le plan ne les refait pas.
  Il les complète et les généralise après leur livraison (§ 1.2) :
  - balises J1, J4, J6, J11, J13 ;
  - portiques et PMV ;
  - chantier ;
  - tunnels ;
  - protection des piles ;
  - profil en long et terrain sur toutes les scènes.
- **Cinq lots** (§ 4). Chacun se livre et se montre avec ses rendus et sa porte de fin mesurable :
  1. **4.1 Imaginer avec ce qu'on sait fabriquer** : mode imagination, éclairage, usure, balises, mobilier, marquages
     dormants, créneau, traverse de village, zone 30 ;
  2. **4.2 Zone de conflit et trajectoires partout** : graphe de voies, giratoires et bretelles balayés, silhouettes de
     véhicules, écarts ouverts, branches courbes, OpenDRIVE, ZoneGraph ;
  3. **4.3 Relief et abords** : profil en long, terrain, talus, dévers, murs, retenue, route de montagne,
     assainissement ;
  4. **4.4 Réseau continu et échangeurs** : plusieurs carrefours par route, losange, trèfle partiel, trompette,
     entrecroisement, péage ;
  5. **4.5 Équipements et conditions ADAS** : équipements d'autoroute, portiques et PMV, chantier, tunnel, écrans, nuit
     et pluie, aires.

  À la fin du lot 4.1, 7 typologies sur 12 sont fabricables à plat, 8 avec les ponts du workflow parallèle (§ 4.7). À la
  fin du lot 4.4, elles le sont toutes, hors végétation et bâti.
- **Zone de conflit et trajectoires** (§ 5). C'est la demande de l'utilisateur du 18/10 : un couloir central guidé et
  des trajectoires de véhicules qui passent correctement, avec des silhouettes visibles. Le principe est d'avoir une
  seule source de trajectoires pour toutes les familles : carrefour, giratoire, bretelle, entrecroisement, créneau,
  chicane, péage, diffuseur. Les véhicules de projet sont choisis selon le contexte, avec des balayages, des contrôles
  chiffrés et des planches. Toute scène imaginée doit passer ces contrôles (cohérence C-23).

## 1. Entrées et état au 22/10/2026

### 1.1 Les quatre rapports

| Rapport | Contenu utile au plan | Où |
|---|---|---|
| Inventaire des lacunes | 153 fonctionnalités en 18 familles : 26 faites, 32 partielles, 89 absentes, 6 en cours ailleurs ; score impact × fréquence ; TOP 20 ; 13 gains rapides ; 4 règles candidates (CAND-E4-001 à -004) ; assets dormants | `ETAPE4_LACUNES.md`, `etape4_lacunes.json` |
| Règles complémentaires (lot 18) | 236 règles `RC-*` sourcées (autoroutes, échangeurs, VSA, créneaux, ouvrages, appuis, tunnels, soutènements, équipements, signalisation de direction autoroutière) ; 22 PDF publics ; 5 schémas types | `D:\DocRoute\18_…\regles_complementaires.json`, synthèses, `schemas/` |
| Descriptions humaines (lot 19) | 138 fiches ; vocabulaire → paramètres (100 entrées) ; grammaire « phrase → scène » (gabarits, arbitrages ARB-I-01 à 03, cohérences C-01 à C-15) ; 62 règles `RI-*` ; fonctionnalités les plus citées | `D:\DocRoute\19_…\GRAMMAIRE_IMAGINATION.md`, `vocabulaire_parametres.json`, `regles_imagination.json` |
| Typologies observées (lot 20) | 92 sites, dont 88 dans les statistiques et 47 en Isère, sur photos Panoramax (une Mapillary) et ortho IGN 20 cm ; 12 typologies T01 à T12 ; lois de tirage (discrètes, triangulaires), présences, lois conditionnelles, 56 règles observées `OBS20-*` | `D:\DocRoute\20_…\parametres_typologies.json`, `observations.json`, `TYPOLOGIES_OBSERVEES.md` |

### 1.2 Le workflow parallèle : ce qu'il fait, ce que l'étape 4 ajoute

État lu le 22/10/2026 vers 18 h 30, dans `recon/generateur`. Rien n'y a été écrit.

| Domaine | Fait ou en cours dans le workflow parallèle | Ce que l'étape 4 ajoute | Règle de coordination |
|---|---|---|---|
| Ponts | `rg::ouvrages::1.0` (README_RG § 16), compilateur `description/ouvrages.py`, clé `ouvrages` (FORMAT_DESCRIPTION § 17) ; PS, PI, pont, viaduc ; tabliers PSIDA, PSIDP, PIPO, PICF, PRAD, VIPP, caisson ; piles, culées, corniches, appareils d'appui, joints ; garde-corps S8 et BN4 ; règles `OA-*` (`assets/specs/route/regles_ouvrages_fr.json`) ; scènes D1 à D4 ; contrôle `validation/controler_ouvrages.py` | gabarits d'imagination `pont_porte` et `pont_franchi` (BK-01) ; rétablissement du losange (BK-26) ; protection des piles par une glissière, laissée à l'étape E13 par ce lot (BK-22) ; tunnels et trémies, non traités par ce lot (BK-34) ; cours d'eau sous l'ouvrage (BK-18) | les descriptions de l'étape 4 emploient la clé `ouvrages` telle qu'elle est. Aucune modification de `rg::ouvrages` ni d'`ouvrages.py` sans leur propriétaire |
| Profil en long et terrain, autour d'un ouvrage | z_long(s) analytique de la route portée (palier, rentrant, rampe, saillant) ; terrain naturel unique (maillage de 1 m à 0,50 m près de l'ouvrage, horizon de 2 km, jupes, talus 3/2 : OA-TAL-001) | profil en long et terrain pour **toutes** les scènes (BK-17, BK-18) | réutiliser ce code au lieu d'en écrire un second : l'extraire dans `hda/commun/` avec son propriétaire. D1 à D4 doivent rester identiques à l'octet |
| Signalisation verticale | `rg::signalisation`, `plan_signalisation.py` (plan de pose hors Houdini), `faces_composees.py` : EB10, EB20, E42, D21, D42a, D42b, D43, D31, D41, C24b, panonceaux M1, M5 et M9z, police Bahnschrift [G] ; B14 (rappel, répétition à gauche), AB3a d'insertion, D31d sur potence allongée (pas de portique), D41a et D51c prévus mais hors des scènes de 800 m (non posés), D21 en T et aux sorties de giratoire (ni D61 ni D29), J3, J5, J14a, A2b, A13b, C20a, C27 ; compléments de 18 scènes (`scenes_signalisation/complements/`) ; scène E01 ; règles `L6-*` | balises J1, J4, J6, J11, J13 et délinéateurs (BK-04) ; portique, PMV et séquence complète de sortie D50, D40, D30, Da (BK-32) ; signalisation temporaire K et AK (BK-33) ; péage et aires (BK-29, BK-37) ; jalonnement Dv, plaques E60, confirmation D61 et D29 (BK-38). Le mode imagination écrit le **complément de signalisation** de chaque scène imaginée (BK-01) | les ajouts sont des extensions du plan L6, faites après sa livraison, avec lui |
| Feux | R11, R11v et R12 posés ; lentilles allumées selon la première phase du contrôleur | feux animés dans Unreal (BK-16) | idem |

Pendant la rédaction de ce plan, le lot L6 a écrit `hda/rg_signalisation/README_SIGNALISATION.md` et ses contrôles
(`validation/controler_signalisation.py`, `faire_rapport_signalisation.py`). Ses limites déclarées confirment le partage
ci-dessus :
- pas de portique ;
- D21 seulement en T et aux sorties de giratoire ;
- ni D61 ni D29 ;
- D41a et D51c hors des scènes de 800 m ;
- police Bahnschrift [G].

Son rapport final, et une section dans `hda/README_RG.md`, restent à lire avant le lot 4.1 (préalable P-1).

### 1.3 Ce que devient le TOP 20 de l'inventaire

| Rang de l'inventaire | Items | Devenir |
|---|---|---|
| 1 | TR-05 Terrain | BK-18, lot 4.3 |
| 2 | CO-02 Graphe de voies complet | BK-10, lot 4.2 |
| 3 | TR-02 Profil en long | BK-17, lot 4.3 |
| 4 | SV-05, SV-07, SV-08 Direction composée | **en grande partie pris par L6** (D21, D42, D43, D31, D41 composés). Restes : BK-32 (autoroute, portiques), BK-38 (Dv, E60) |
| 5 | RS-01, MQ-15, RV-04 Réseau continu | BK-25, lot 4.4 |
| 6 | CO-04 OpenDRIVE | BK-15, lot 4.2 |
| 7 | EQ-06 Éclairage | BK-02, lot 4.1 |
| 8 | RV-02, MQ-16 Usure | BK-03, lot 4.1 |
| 9 | CO-03 Trajectoires des giratoires et des bretelles | BK-11, lot 4.2 |
| 10 | TR-06, TR-07, AS-04 Talus et fossés | BK-19, lot 4.3 |
| 11 | SV-03, PR-22 Entrées d'agglomération | placement par L6 (EB10, EB20, B14 ; scène E01). Le reste (îlot d'entrée, chicane) : BK-08, lot 4.1 |
| 12 | CO-05 ZoneGraph | BK-16, lot 4.2 |
| 13 | RV-06 Conditions de rendu | BK-36, lot 4.5 |
| 14 | AS-02, AS-03, RV-03 Assainissement | BK-24, lot 4.3 |
| 15 | EQ-04, EQ-02, EQ-03 Retenue | BK-22, lot 4.3 |
| 16 | FE-04 Feux animés | BK-16 (L6 allume la 1re phase) |
| 17 | CP-05 Branches courbes | BK-14, lot 4.2 |
| 18 | EC-04, EC-07 Losange | BK-26, lot 4.4 |
| 19 | EQ-11 Balises | J3, J5 et J14a par L6 ; J1, J4, J6, J11, J13 : BK-04, lot 4.1 |
| 20 | TR-03, TR-04 Dévers, surlargeur | BK-20, lot 4.3 |

## 2. Backlog priorisé

### 2.1 Méthode

1. **En tête, hors score** : le levier de la nouvelle orientation (BK-01, mode imagination) et la priorité déjà
   exprimée par l'utilisateur (zone de conflit et trajectoires : BK-10 à BK-13).
2. **Score de l'étape 4** = score de l'inventaire (impact × fréquence, de 1 à 25 : `ETAPE4_LACUNES.md` § 1), auquel
   s'ajoutent deux bonus :
   - **+2 (typologie)** si l'élément est vu « presque toujours » ou « souvent » dans au moins une typologie du lot 20,
     ou s'il fait le trait qui la définit (exemple : les cabines du péage pour T03) ;
   - **+1 (corpus)** si au moins 20 fiches du lot 19 le citent (`travail/frequence_fonctionnalites.json`).
   
   Pour un groupe d'items, on retient le meilleur score du groupe, comme le fait l'inventaire.
3. **Le rang dit la valeur, le lot dit quand on peut le faire.** Un élément bien classé peut attendre une dépendance :
   le terrain, par exemple, attend le profil en long. Un élément mal classé mais peu coûteux peut entrer dans un lot
   précoce s'il complète une typologie : le créneau rend T06 fabricable.

Les poids des bonus sont un choix [G] déclaré, modifiable. Le JSON de l'inventaire garde les fréquences par contexte, ce
qui permet de recalculer.

### 2.2 Tableau

Effort, sur l'échelle de l'inventaire : **S** ≤ 2 jours ; **M** de 3 à 7 jours ; **L** de 2 à 4 semaines ; **XL** plus d'un
mois. Abréviations de la colonne « Coordination » : « L6 » = signalisation, « OA » = ouvrages (workflow parallèle).

| Rang | Id | Fonctionnalité | Items de l'inventaire | Score inv. | Bonus | Score E4 | Effort | Lot | Dépend de | Coordination |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BK-01 | Mode imagination v1 | IM-01, IM-02, IM-03, IM-05 | (20,0) | — | levier | L | 4.1 | P-1, P-2 | écrit les compléments L6 |
| 2 | BK-10 | Graphe de voies complet | CO-02 | 17,6 | — | priorité utilisateur | M | 4.2 | — | OA (couches superposées) |
| 3 | BK-11 | Trajectoires, balayages, conflits des giratoires et des bretelles | CO-03 | 13,6 | — | priorité utilisateur | M | 4.2 | BK-10 | — |
| 4 | BK-12 | Visualisation : silhouettes de véhicules, planches de balayage | (demande du 18/10) | — | — | priorité utilisateur | S-M | 4.2 | BK-11 | — |
| 5 | BK-13 | Écarts ouverts de la zone de conflit (CE-L3-9, CE-L4-16, CE-3, CE-1, CE-4) | CP-04 (suite) | — | — | priorité utilisateur | M | 4.2 | — | — |
| 6 | BK-18 | Terrain naturel et abords, cours d'eau | TR-05, OA-03, TR-09 | 19,8 | 0 | 19,8 | L | 4.3 | BK-17 | OA (terrain local) |
| 7 | BK-17 | Profil en long général | TR-02 | 17,4 | +1 | 18,4 | L | 4.3 | P-1 | OA (z_long) |
| 8 | BK-02 | Éclairage public | EQ-06 | 14,8 | +2 | 16,8 | M | 4.1 | — | — |
| 9 | BK-25 | Réseau continu (plusieurs carrefours par route) | RS-01, MQ-15, RV-04 | 15,6 | +1 | 16,6 | L | 4.4 | BK-17 | — |
| 10 | BK-03 | Chaussée et peinture vieillies | RV-02, MQ-16, RV-05 | 14,5 | +2 | 16,5 | M | 4.1 | — | — |
| 11 | BK-15 | Export OpenDRIVE 1.4 / 1.8.1 | CO-04 | 15,0 | 0 | 15,0 | L | 4.2 | BK-10 | — |
| 12 | BK-19 | Talus, fossés, cunettes, descentes d'eau | TR-06, TR-07, AS-04, OA-07 | 12,4 | +2 | 14,4 | L | 4.3 | BK-17, BK-18 | — |
| 13 | BK-26 | Diffuseur en losange | EC-04, EC-07 | 10,2 | +2 +1 | 13,2 | XL | 4.4 | BK-17, BK-20, P-1 | OA (PS) ; L6 (sortie) |
| 14 | BK-22 | Retenue posée par règle | EQ-02, EQ-03, EQ-04 | 10,8 | +2 | 12,8 | M | 4.3 | BK-19 | OA (piles) |
| 15 | BK-16 | ZoneGraph dans Unreal et feux animés | CO-05, FE-04 | 12,0 | 0 | 12,0 | M | 4.2 | BK-10 | L6 (contrôleur) |
| 16 | BK-36 | Nuit, pluie, rétroréflexion | RV-06 | 12,0 | 0 | 12,0 | L | 4.5 | BK-02 | L6 (faces) |
| 17 | BK-24 | Assainissement réglé par le fil d'eau | AS-02, AS-03, RV-03 | 11,1 | 0 | 11,1 | M | 4.3 | BK-17 | — |
| 18 | BK-21 | Murs de soutènement, parapets, parois rocheuses | TR-08 | 9,0 | +2 | 11,0 | M | 4.3 | BK-18 | — |
| 19 | BK-32 | Portiques, potences, PMV, séquence complète de sortie | EQ-09, EQ-10, SV-06 | 9,0 | +2 | 11,0 | M-L | 4.5 | P-1 | **L6** |
| 20 | BK-08 | Traverse d'agglomération : îlot d'entrée, chicane, écluse | PR-22, PR-21 | 8,6 | +2 | 10,6 | M | 4.1 | — | L6 (EB10, B15/C18) |
| 21 | BK-14 | Branches courbes ou obliques, carrefour en Y | CP-05 | 10,5 | 0 | 10,5 | L | 4.2 | — | — |
| 22 | BK-27 | Trèfle partiel, demi-trèfle, trompette | EC-05 | 7,2 | +2 +1 | 10,2 | XL | 4.4 | BK-26 | OA |
| 23 | BK-05 | Mobilier urbain et séparateurs ponctuels | MU-01, MU-02, MA-02, MA-04 | 8,1 | +2 | 10,1 | S-M | 4.1 | — | — |
| 24 | BK-06 | Marquages dormants (gabarits présents, jamais posés) | MQ-07, PR-02, MQ-09 à -13, MQ-06, CP-09, EC-10, PR-13 | 8,1 | +2 | 10,1 | M | 4.1 | — | — |
| 25 | BK-23 | Route de montagne : lacets, profil asymétrique | TR-10 | 6,6 | +2 +1 | 9,6 | L | 4.3 | BK-17 à BK-22 | — |
| 26 | BK-04 | Balises J1, J4, J6, J11, J13, délinéateurs | EQ-11 | 9,6 | 0 | 9,6 | S | 4.1 | P-1 | **L6** |
| 27 | BK-20 | Dévers, gauchissement, surlargeur | TR-03, TR-04 | 9,3 | 0 | 9,3 | M | 4.3 | BK-17 | — |
| 28 | BK-34 | Tunnel, tranchée couverte, trémie | OA-06 | 7,0 | +1 | 8,0 | L | 4.5 | BK-17, BK-18 | **OA** |
| 29 | BK-33 | Signalisation temporaire de chantier | SV-09, MQ-12 | 8,0 | 0 | 8,0 | M | 4.5 | P-1 | L6 |
| 30 | BK-28 | Bifurcation 2 + 2, entrecroisement, collectrice | EC-02, EC-03 | 6,8 | +1 | 7,8 | M-L | 4.4 | BK-11 | — |
| 31 | BK-30 | Voie express à carrefours plans : ouverture de TPC, demi-carrefour | CP-06, CP-08 | 7,5 | 0 | 7,5 | L | 4.4 | BK-14 | — |
| 32 | BK-07 | Créneau de dépassement, route à 3 voies affectées | PR-14, MQ-05 | 5,4 | +2 | 7,4 | M | 4.1 | — | — |
| 33 | BK-29 | Barrière de péage et portique à flux libre | EC-08 | 5,2 | +2 | 7,2 | L | 4.4 | BK-11 | L6 (D47, C64) |
| 34 | BK-38 | Jalonnement cyclable Dv, plaques de rue E60, localisation, confirmation D61 | SV-07, SV-08 | 6,5 | 0 | 6,5 | S | 4.5 | P-1 | **L6** |
| 35 | BK-09 | Zone 30 et zone de rencontre | PR-06, PR-07, MQ-10, AS-05 | 6,1 | 0 | 6,1 | S-M | 4.1 | — | L6 (B30, B52) |
| 36 | BK-35 | Écrans acoustiques | OA-09 | 5,8 | 0 | 5,8 | M | 4.5 | BK-22 | — |
| 37 | BK-31 | Équipements d'autoroute : clôture, PR, refuges et PAU, ITPC | EQ-07, EQ-08, EQ-13 | 4,9 | 0 | 4,9 | M | 4.5 | — | — |
| 38 | BK-37 | Aires de repos et de service | EC-09 | 3,4 | +1 | 4,4 | L | 4.5 | BK-26 | L6 (D46) |

Ce que le backlog ne prend pas :
- **la végétation et le bâti** (VB-01 à VB-04), reportés par décision du 17/10 (§ 6, décision 1) ;
- **les éléments que le workflow parallèle fabrique déjà** : pont courant, passerelle, BN4, signalisation de police, feux ;
- **les items de score inférieur à 4** de l'inventaire (PR-10, CP-07, CP-13, SV-11, etc.) : ils restent dans
  `etape4_lacunes.json`.

### 2.3 Fiches

Conventions communes aux fiches :
- **Géométrie dans les HDA.** Toute géométrie sort de réseaux SOP empaquetés en HDA (`.hdalc`). Python ne sert qu'à lire la
  description, à écrire les plans de pose et aux entrées-sorties, comme `plan_signalisation.py`.
- **Rétrocompatibilité.** Une HDA modifiée l'est par une nouvelle version installée à côté (`::2.0`). Une description sans
  la nouvelle clé compile et se fabrique **à l'octet** comme avant ; le contrôle se fait par les empreintes sha256 des
  modèles et des USD (CHAINE § 7.2).
- **Critères.** Ils sont vérifiés par un contrôle indépendant (`validation/controler_<lot>.py`), puis par le regard sur
  les rendus en tuiles natives : planches de 1 092 px au plus, découpées par `recon/pcg/vision/decoupe.py`.

#### Lot 4.1 — Imaginer avec ce qu'on sait fabriquer

**BK-01 — Mode imagination v1** (rang 1 · effort L)
- *Couvre* : IM-01, IM-02, IM-03 et IM-05. IM-04, le relevé de fréquences, a été fait par le lot 20 sur 12 typologies.
- *Données* (en lecture seule) :
  - lot 19 : `GRAMMAIRE_IMAGINATION.md` § 2 à 6, `vocabulaire_parametres.json`, `regles_imagination.json` (RI-*) ;
  - lot 20 : `parametres_typologies.json` (lois, présences, lois conditionnelles, OBS20-*), `observations.json`
    (sites-modèles) ;
  - lot 18 : `regles_complementaires.json` (RC-*) ;
  - base : `regles_route_fr.json` (RF-*, DEF-*, ARB-*) ;
  - arbitrages ARB-I-01 à 03 (lot 19), et ARB-I-04 à 07 proposés au § 3.9.
- *Code* : un nouveau dossier `recon/generateur/imagination/` en Python, hors Houdini, comme l'inférence OSM. Il contient :
  - `imaginer.py` (ligne de commande) ;
  - `lire_phrase.py`, `typer.py`, `lois.py`, `tirages.py`, `gabarits.py`, `controles.py` ;
  - `ecrire_description.py` et `ecrire_complement_l6.py`.
  
  Le compilateur ne change pas : la grammaire écrit une description, elle ne fabrique rien (lot 19 § 10).
- *Scènes* :
  - `recon/generateur/scenes_imagination/I00` à `I10` : entrées du § 3.14, au format `imagination/0.1` ;
  - sorties dans `recon/out/generateur/imagination/<id>_v<variante>/`.
- *Critères* : ceux du § 3.15 (compilation, déterminisme, fidélité des fréquences, provenances, refus motivés).
- *Dépend de* : P-1 (ouvrages et L6 livrés, pour les gabarits de pont et les compléments de signalisation), P-2
  (versement des règles ; sinon lecture directe des fichiers de DocRoute, avec la provenance `docroute18:`, `docroute19:`
  ou `docroute20:`).

**BK-02 — Éclairage public** (rang 8 · effort M)
- *Couvre* : EQ-06 (14,8).
- *Typologies* :
  - T04 : mâts 0,86 ;
  - T03 : 0,62 ;
  - T02 : 0,43 (échangeurs urbains) ;
  - T09 : 0,25 ;
  - T10 et T12 : rarement.
- *Règles* :
  - ECL-01 à ECL-05 (`assets/specs/regles_implantation.json`) : recul de 0,50 à 1,00 m derrière l'arête, orientation à
    ± 10°, alignement à 0,30 m près, pas de 3 à 5 fois la hauteur de feu, distance aux arbres ;
  - RF-OBS-ECL-01 : 8 à 11 m observés ;
  - RC-AUT-034 : pas d'éclairage en section courante d'autoroute ; oui aux péages et en tunnel ;
  - RC-EQ-025 (aires) et RC-EQ-026 (classes) ;
  - RC-EQ-027 [G] : hauteur de feu de 10 à 12 m, interdistance d'environ 3,5 fois la hauteur ;
  - RC-APP-016 : sur ouvrage, ancrage dans la longrine, jamais dans la corniche.
- *Assets* :
  - existants : 8 candélabres, `candelabre_routier_H080/H100/H120` (simple ou double crosse) et
    `candelabre_urbain_H040 à H080` ;
  - à créer : un mât haut d'échangeur, différé au lot 4.4.
- *HDA* : `rg::eclairage::1.0` (étape E15), qui produit des points `pj_points/0.1` et des instances USD. Rangées le long
  des bords, du TPC (double crosse) et des îlots. Giratoire : sur l'îlot central ou en périphérie [G].
- *Scènes* :
  - S06 : TPC planté, double crosse ;
  - G1 : giratoire ;
  - A1 : contrôle négatif, aucun mât ;
  - E01 : traverse ;
  - I01, I07.
- *Critères* :
  - 0 mât sur la chaussée, une piste ou le cheminement ;
  - recul dans [0,50 ; 1,00] m pour 100 % des mâts ;
  - pas / hauteur dans [3 ; 5] ;
  - azimut à ± 10° ;
  - A1 : 0 mât ;
  - cheminement libre ≥ 1,40 m conservé (RF-MA-TRO-*).

**BK-03 — Chaussée et peinture vieillies** (rang 10 · effort M)
- *Couvre* : RV-02, MQ-16 et RV-05 (14,5).
- *Observé* (lot 20) :
  - pontages de fissures : T04, T05, T09 ;
  - rapiéçages carrés : T07, T08 ;
  - faïençage : T08 ;
  - rives effritées et gravillons : T07 ;
  - BAU plus claire que les voies : T01.
- *Règles* :
  - RF-OBS-REV-01 ;
  - pas de règle de géométrie : aspect seulement, choix [G] déclarés (CHAINE L-06).
- *Assets* :
  - existant : `enrobe_reprise_tranchee` ;
  - décalques à créer : pontage au bitume, rapiéçage, faïençage, gravillons de rive, marquage fantôme ; tags sur
    GBA plus tard.
- *HDA* : `rg::aspect_chaussee::1.0` (CHAINE E10). Points de décalques tirés par la graine de la scène, avec une densité
  par classe d'état (`etat_chaussee` du lot 20). Usure renforcée le long des traces de roues, tirées des axes de voie et
  des trajectoires du lot L4. Export vers le graphe PCG `PG_Decalques`.
- *Scènes* : S01, J3, I03, I07.
- *Critères* :
  - 0 décalque hors chaussée ;
  - densité, en décalques pour 100 m de voie, dans la plage déclarée de sa classe ;
  - marquages fantômes décalés de 0,5 à 3,5 m de la ligne actuelle [G] ;
  - mêmes octets à deux exécutions.

**BK-04 — Balises et délinéateurs** (rang 26 · effort S · **extension du plan L6**)
- *Couvre* : EQ-11 (9,6). J3, J5 et J14a sont déjà posées par L6.
- *Règles* :
  - RF-SV-J1 : extérieur de virage, intervalle ≥ 8 m, 2 ou 3 balises sur les alignements ;
  - RF-SV-J4 : hauteur selon la route, bord inférieur à 1,00 m ;
  - RF-SV-J6 : 1,00 m, des deux côtés, remplace J1 sur l'itinéraire ;
  - RC-EQ-011 et RC-EQ-012 : espacement e = d/5, 50 m si la visibilité est ≥ 250 m ;
  - RF-SV-J11_J12 et RC-EQ-013 : J11 à 0,50 m d'une ligne continue ;
  - RF-SV-J13 ;
  - RC-ECH-028 : 0,70 m de dégagement à J14a ;
  - RC-EQ-016 : perches à neige côté vide, tous les 20 à 40 m.
- *Assets* :
  - existants : `balise_J1`, `balise_J6`, `balise_J11_H050/H070/H085`, `balise_J12_H085`, `balise_J13`,
    `panneau_J4_t_d/g` ;
  - à créer : J1 sur glissière, perche à neige.
- *HDA* : ajout d'une rubrique « balises » à `plan_signalisation.py` et pose par `rg::signalisation`. À faire avec le
  propriétaire du lot L6, après sa livraison. À défaut, une `rg::balisage::1.0` séparée.
- *Scènes* : S01, S11 (variante hors agglomération), I03, I04, I05.
- *Critères* :
  - J6 des deux côtés au pas de RC-EQ-011, à ± 1 m ;
  - J4 à la hauteur de sa catégorie dans 100 % des cas ;
  - dégagement de J14a ≥ 0,70 m ;
  - 0 balise sur la chaussée.

**BK-05 — Mobilier urbain et séparateurs ponctuels** (rang 23 · effort S-M)
- *Couvre* : MU-01, MU-02, MA-02, MA-04 et l'abri de TC-01 (8,1).
- *Typologies* :
  - T10 : potelets 0,71, arceaux 0,43, barrières 0,43 ;
  - T11 : potelets 0,50.
- *Règles* :
  - RF-MA-OBS-001 : abaque de détection ;
  - RF-MA-SEP-011 ;
  - règles RI de `regles_implantation.json` ;
  - RF-MA-TRO-013, RF-MA-BUS-012 ;
  - RF-MA-SVE-001 : arceaux ;
  - RF-MA-TRO-* : cheminement de 1,40 m.
- *Assets* : 8 potelets, 6 barrières, 3 arceaux, 3 bancs, 2 corbeilles, une borne fontaine, 2 abris de bus ; jardinières à
  créer (elles servent aussi à BK-08).
- *HDA* : `rg::mobilier::1.0` (étape E16).
- *Scènes* : S03, ex05 (arrêt de bus), I01, I10.
- *Critères* :
  - cheminement libre ≥ 1,40 m partout (0 violation) ;
  - 0 objet sur un abaissé, une BEV ou un passage ;
  - abri sur le quai ;
  - potelets au pas déclaré, à ± 0,05 m.

**BK-06 — Marquages dormants** (rang 24 · effort M · gains rapides de l'inventaire § 7.3)
- *Couvre* : MQ-07 et PR-02 (places, PMR, IRVE, livraison), MQ-09 (damier TC), MQ-10 (ZONE 30), MQ-11 (triangles cédez),
  MQ-06 et CP-09 (doubles chevrons, figurine encadrée), MQ-12 (jaune temporaire), MQ-13 (surlargeur, PAU, points de
  repère), EC-10 (damier de détresse), PR-13 (marques MRE).
- *Règles* :
  - RF-MQ-STA-01 à -10 ;
  - RF-MQ-TC-01 à -04 ;
  - RF-MQ-INS-TXT-04 à -06 ;
  - ARB-16 : triangle cédez au sol avec une probabilité de 0,2 ; base à 5 m (V ≤ 60) ou 10 m ;
  - RF-MQ-CYC-01, -03, -04 ;
  - RF-MQ-TMP-01 ;
  - RF-MQ-SUR-01, RF-MQ-PAU-01 ;
  - RF-MQ-MRE-01, RF-MQ-SC-02.
- *Typologies* : stationnement marqué (T10 0,43 ; T11 0,50), logo vélo (T10 0,43 ; T11 0,50), livraison jaune (T10 0,29).
- *Assets* :
  - gabarits existants : PMR, PMR_X2, IRVE, CARRE_DAMIER_TC, DOUBLE_CHEVRON_CEREMA, MRE, CEDEZ_V60, CARREAU_DETRESSE,
    BANDE_SURLARGEUR_1M, ANNEAU_LIMITATION_50, RECTANGLE_POINT_REPERE ;
  - à créer : anneau 30, figurine encadrée.
- *HDA* : `rg::marquages::1.1`, installée à côté de la 1.0, pour les évènements « places », « inscription de zone »,
  « damier ». La correction CE-1 (exclusions des figurines au droit des passages) se fait dans cette version.
- *Scènes* : S03 (places), S12 (damier), S08 (ZONE 30), J1 (cédez au sol), S01 étroite (MRE), A1 (surlargeur, PAU).
- *Critères* :
  - sommets des symboles = gabarit à ± 1 mm (méthode L4) ;
  - distances de pose de chaque règle tenues dans 100 % des cas ;
  - 0 recouvrement marquage / passage ;
  - scènes sans clé identiques à l'octet.

**BK-07 — Créneau de dépassement et route à 3 voies affectées** (rang 32 · effort M)
- *Couvre* : PR-14, MQ-05 et une partie de PR-15 ; typologie T06 ; 8 fiches du corpus.
- *Règles* :
  - RC-ARP-001 : 600 m en rampe, de 1 000 à 1 250 m en plaine ;
  - RC-ARP-002 : ≥ 4 à 5 km entre créneaux ;
  - RC-ARP-003 : voies affectées ; 3 voies banalisées proscrites ;
  - RC-ARP-004 : jamais en amont d'un point dur ;
  - RC-ARP-005 : décrochement de 130 m ;
  - RC-ARP-006 : Li de 234 m à 90 km/h, plus une zone tampon ≥ 88 m ;
  - RC-ARP-009 : 90 / 80 km/h ;
  - RC-ARP-011 [G] ;
  - RI-TYP-008 ;
  - RF-MQ-SC-03, RF-MQ-MIX-01, RF-MQ-RAB-* ;
  - OBS20-T06-LARGEUR_CHAUSSEE (10,4 à 10,8 m), OBS20-T06-LARGEUR_VOIE.
- *Code* :
  - gabarit d'imagination `creneau`, qui écrit `ouverture`, `fermeture` et les profils (S09, A3) ;
  - ligne mixte dans le compilateur, si elle manque encore (RF-MQ-MIX-01 n'est pas utilisée aujourd'hui).
- *Scènes* : `scenes_imagination/I05` et un créneau à plat de 1 600 m.
- *Critères* :
  - longueur dans la plage de RC-ARP-001 ;
  - décrochement de 130 ± 1 m ;
  - rabattement de 234 m, puis tampon ≥ 88 m ;
  - axe continu côté sens à une voie, T1 entre les voies de même sens ;
  - 0 accès ni carrefour dans le créneau ni à moins de 300 m ;
  - trajectoire de rabattement balayée (§ 5).

**BK-08 — Traverse d'agglomération : îlot d'entrée, chicane, écluse** (rang 20 · effort M)
- *Couvre* : PR-22 et PR-21. L6 place déjà les EB10, EB20 et B14 (scène E01).
- *Règles* :
  - RF-SV-EB.POSITION, RF-SV-EB10.PRESCRIPTIONS ;
  - RF-SV-B15.C18, RF-MQ-ALT-01 ;
  - RF-MA-TRO-009 ;
  - RF-SV-J4 : monochevron en agglomération ;
  - RF-GV-RAL-002 : plateau ;
  - OBS20-T09-LARGEUR_CHAUSSEE (4 à 7,5 m), OBS20-T09-LARGEUR_TROTTOIR (1,5 à 2 m) ;
  - à verser depuis DocRoute 10 : CERTU PAS VII04 (îlot d'entrée) et Cerema PAS VII06 (chicane), présents mais non
    exploités (inventaire § 4.2).
- *Assets* : jardinières (BK-05) ; bordures existantes.
- *Code* :
  - évènements `chicane`, `ecluse` et `ilot_entree` dans le compilateur (nouvelles clés, rétrocompatibles) ;
  - les avancées sont des bandes du profil (trottoir, bande plantée) ;
  - jardinières posées par `rg::mobilier`.
- *Scènes* : E01 avec une chicane ajoutée ; I02.
- *Critères* :
  - passage libre de la chicane ≥ la largeur de la règle versée ;
  - balayages du bus, de l'autocar et du porteur dans la voie libre, sans toucher les avancées (§ 5, alternat) ;
  - couple B15 / C18 présent (L6) ;
  - transition de profil à l'EB10, à ± 20 m [G].

**BK-09 — Zone 30 et zone de rencontre** (rang 35 · effort S-M)
- *Couvre* : PR-06, PR-07, MQ-10 et AS-05 (caniveau central).
- *Règles* :
  - RF-SV-B30.ZONE30 ;
  - RF-MA-ZCA-001 : double sens cyclable par défaut ;
  - RF-MQ-INS-TXT-04, RF-MQ-INS-TXT-06 ;
  - RF-MQ-RAL-04 ;
  - RF-GV-RAL-001 : coussin de 1,75 à 1,90 × 3 à 4 m ;
  - RF-OSM-VIT-004 ;
  - OBS20-T11-LARGEUR_CHAUSSEE (4,5 à 6,5 m, sans axe).
- *Code* : évènement `entree_zone` : B30 ou B52 par L6, inscription ZONE 30, effet de porte (plateau ou rétrécissement). Zone
  de rencontre : chaussée de plain-pied avec caniveau central.
- *Scènes* : S08 (variante) ; I10.
- *Critères* :
  - B30 à chaque entrée ;
  - inscription au gabarit à ± 1 mm ;
  - double sens cyclable présent par défaut (RF-MA-ZCA-001) ;
  - 0 ligne d'axe.

#### Lot 4.2 — Zone de conflit, trajectoires et graphe partout

**BK-10 — Graphe de voies complet** (rang 2 · effort M)
- *Couvre* : CO-02 (17,6).
- *Règles et contrat* :
  - RF-GV-TRJ-006 ;
  - modèle de voie et graphe (DocRoute 12, `MODELE_VOIE_ROUTE_CARREFOUR.md`) ;
  - correspondances OpenDRIVE (lanes, links, junctions).
- *Code* : généraliser l'écriture de `graphe_voies.json` du lot L4. Elle est aujourd'hui limitée aux carrefours plans ;
  elle doit couvrir :
  - les sections (`l1/`) ;
  - les giratoires (`l5/`) ;
  - les bretelles et bifurcations (`autoroute/`) ;
  - les routes superposées des ouvrages (couches, `layer`).
  
  Exporteur `rg::exporter_graphe` : c'est de l'entrée-sortie, donc du Python.
- *Scènes* : toutes les scènes de référence (S01 à S12, J1 à J6, G1 à G4, A1 à A4, D1 à D4) et I01 à I10.
- *Critères* :
  - chaque voie entrante a au moins un successeur, chaque voie sortante au moins un prédécesseur, hors limites de carte ;
  - continuité des axes aux connecteurs ≤ 1 cm et ≤ 1° ;
  - au plus 32 étiquettes (L4-17) ;
  - mêmes octets à deux exécutions.

**BK-11 — Trajectoires, balayages et conflits des giratoires et des bretelles** (rang 3 · effort M)
- *Couvre* : CO-03 (13,6). Aujourd'hui, les trajectoires de giratoire sont calculées par le compilateur, mais ne sont pas
  balayées ; les bretelles n'en ont aucune.
- *Règles* :
  - RF-GV-GIR-008 : déflexion ≤ 100 m ;
  - DEF-024 ;
  - RF-GV-TRJ-001 : 4 points de conflit VL / VL et 8 VL / piétons au giratoire ;
  - RF-GV-TRJ-006 ;
  - RC-ECH-014 et RC-ECH-015 : Ld et La ;
  - RC-ECH-025 et RC-ECH-026 : obliquités ;
  - RC-ECH-029 : déboîtement de 150 m ;
  - RC-ECH-032 : insertion de 200 m plus 75 m ;
  - RI-ECH-011 : points caractéristiques S.1,00, S.1,50, S.5,00 et E.1,00.
- *Code* :
  - trajectoires entrée, anneau, sortie, et cas du mini-giratoire : le bus et le porteur franchissent l'îlot, pas le VL ;
  - insertion : de la voie d'insertion à la voie de droite, avec convergence entre E.1,00 et la fin du biseau ;
  - déboîtement : de S.1,50 à S.5,00 ;
  - balayages par `vehicules/balayage.py` (lot L3a), sur les trajectoires finales (« une seule source », § 5.2).
- *Véhicules* : `vl`, `bus_standard_12m`, `semi_remorque`, `autocar_15m` (`vehicules/vehicules_projet.json`).
- *Scènes* : G1 à G4, A3, A4, I10.
- *Critères* :
  - déflexion ≤ 100 m sur chaque entrée ;
  - 0 nez d'îlot séparateur touché, avec 0,30 m de marge ;
  - couronne franchissable empruntée seulement par le bus et le semi-remorque ;
  - 4 convergences VL / VL comptées par giratoire à 4 branches ;
  - courbure des trajectoires de bretelle ≤ 1 / rayon minimal du véhicule ;
  - convergence dans la zone d'insertion à 100 %.

**BK-12 — Visualisation : silhouettes de véhicules et planches de balayage** (rang 4 · effort S-M)
- *Couvre* : la demande du 18/10, « visualisation avec silhouettes de véhicules ».
- *Données* :
  - trajectoires du lot L4 et `l3/balayages.json` ;
  - gabarits des 7 véhicules de projet (`vehicules_projet.json`).
- *HDA* : `rg::silhouettes::1.0`. Volumes simples tirés des gabarits (caisse, porte-à-faux, roues), posés à l'entrée, au
  milieu, à la sortie et au point de plus grand déport de chaque trajectoire. Orientation par l'essieu arrière suiveur.
- *Rendus* :
  - planche de dessus de 1 092 px : voies, connecteurs, balayages colorés par véhicule, zone de conflit hachurée, points
    de conflit numérotés, guidage, légende ;
  - vue conducteur à 1,20 m ;
  - oblique 3/4 avec silhouettes.
- *Scènes* : J5, J6, G2, A3, I09, I10.
- *Critères* :
  - silhouette contenue dans son balayage dans 100 % des poses ;
  - roues arrière posées à moins de 2 cm de la courbe calculée par le balayage ;
  - planches qui passent `decoupe.py verifier`.

**BK-13 — Écarts ouverts de la zone de conflit** (rang 5 · effort M)
- *Couvre* : `validation/RAPPORT_correction_etape2.md` § 6, mesurés et non atteints. Aucun seuil ne sera baissé.
- *Écarts à corriger* :
  - **CE-L3-9, J4 sud** : le TAG de l'avenue balaie le nez de l'îlot de la rue sud (VL à −2,43 m ; bus à 0,25 m pour
    0,30 m demandés). Correction : redessiner l'angle sud-est, en reculant ensemble l'îlot directionnel et le passage.
  - **CE-L4-16, J5** : le modèle topologique des conflits doit tenir compte des phases.
  - **CE-3a et CE-3b** : largeur du passage de la voie directe, à prendre de la face de bordure à la face de l'îlot.
  - **CE-1, J6** : figurines sur un passage (fait dans BK-06).
  - **CE-4, A4** : deux trous de rive.
  - **GI-11, G1** : bords libres.
  - Recherche du rayon des TAG guidés par dichotomie : une passe de J6 dure environ 10 min aujourd'hui.
- *Critères* : tous les contrôles CE de J1 à J6, G1 à G4, A3 et A4 à « oui » ; temps d'une passe de J6 divisé par 3 ou plus.

**BK-14 — Branches courbes ou obliques, carrefour en Y** (rang 21 · effort L)
- *Couvre* : CP-05 (10,5). Aujourd'hui, les branches doivent être droites au voisinage du carrefour (README_RG l. 519).
- *Règles* :
  - RF-GV-CAR-004 : incidence > 20° → redressement de la branche ;
  - RF-GV-CAR-005 : palier ;
  - RF-GV-RAY-* ;
  - RF-GV-TRJ-006.
- *HDA* : `rg::carrefours::2.0` : coins sur des bords courbes, trajectoires le long d'axes de voie courbes, frontière
  calculée sur des arcs.
- *Scènes* : J7 en Y, J8 avec une branche en courbe de rayon 80 m, I02 (variante).
- *Critères* :
  - flèche des bords ≤ 0,5 mm (méthode L1) ;
  - coins tangents (G1) ;
  - balayages VL et bus sans contact ;
  - zone de conflit et conflits calculés comme sur J1 à J6.

**BK-15 — Export OpenDRIVE 1.4 (CARLA) et 1.8.1** (rang 11 · effort L)
- *Couvre* : CO-04 (15,0).
- *Contrat* : correspondances OpenDRIVE du modèle (DocRoute 12, champ `x-opendrive` déjà présent dans les bandes du
  modèle).
- *Code* : `rg::exporter_opendrive`, en Python d'entrée-sortie, à partir du modèle et du graphe. L'élévation est nulle
  jusqu'au lot 4.3 ; ensuite `elevationProfile` et `superelevation`.
- *Validation* : schéma XSD, plus un validateur autonome (esmini ou libOpenDRIVE), à installer sur décision de
  l'utilisateur (§ 6). Relecture du fichier et tracé de contrôle en tuiles.
- *Scènes* : J1, J3, G1, A3, I05, puis I06.
- *Critères* :
  - 0 erreur de schéma ;
  - axes relus à moins de 2 cm de ceux du modèle ;
  - jonctions = zones de conflit du graphe, à 100 % ;
  - liens de voies = connecteurs, à 100 %.

**BK-16 — ZoneGraph dans Unreal et feux animés** (rang 15 · effort M)
- *Couvre* : CO-05 (12,0) et FE-04 (10,8).
- *Code* :
  - `recon/pcg/ue/zonegraph_depuis_graphe.py` (PLAN_GENERATEUR § 7) ;
  - pilotage des lentilles R11 et R12 posées par L6, par le contrôleur du modèle (matériaux émissifs).
- *Scènes* : J3 et J5, dans le projet UE 5.8 (`D:\ClaudeADAS`).
- *Critères* :
  - nombre de voies et de liens du ZoneGraph = graphe (100 %) ;
  - durées de phase = contrôleur à ± 0,1 s ;
  - aucun vert simultané sur deux mouvements en conflit.

#### Lot 4.3 — Relief et abords

**BK-17 — Profil en long général** (rang 7 · effort L)
- *Couvre* : TR-02 (17,4). Supprime la rupture R-03 : aujourd'hui, Z = 0 sur toutes les routes, sauf la route portée par
  un ouvrage.
- *Règles* :
  - RC-AUT-004 à -006 (déclivités, rayons saillant et rentrant) et RC-AUT-009 (coordination plan / profil) ;
  - RC-ECH-007 (bretelles) ;
  - RI-TRA-001 à -003 ;
  - RF-GV-CAR-005 (palier avant carrefour) ;
  - RF-GV-GIR-022 (pentes du site d'un giratoire) ;
  - RF-MA-TRO-003 (cheminement) ;
  - OA-PEL-001 et OA-PEL-002 (lot ouvrages) ;
  - RF-OSM-OUV-001 (couches).
  
  En ville, aucune règle de déclivité (CHAINE L-02) : profil dit, sinon MNT, sinon plat déclaré.
- *Code* :
  - `reseau/profil_long.py` (lot N2), qui reprend le z_long(s) du lot ouvrages (palier, rampe, raccordements) ;
  - nouvelle clé de description `profil_long:` par tronçon (points, pentes, rayons ; lois du lot 19 pour l'imagination) ;
  - `rg::nivellement::2.0` lit `routes[].profil_long`.
- *Scènes* : S01 en rampe de 6 %, J2 sur une pente avec palier, G2 sur un site en pente, D1 (non-régression).
- *Critères* :
  - écart à la loi z(s) ≤ 5 mm (comme pour le lot ouvrages) ;
  - pentes et rayons dans les bornes de la catégorie ;
  - palier tenu avant chaque carrefour ;
  - scènes sans `profil_long` identiques à l'octet.

**BK-18 — Terrain naturel et abords, cours d'eau** (rang 6 · effort L)
- *Couvre* : TR-05 (19,8), OA-03 (8,0) et TR-09. Supprime R-08 : la route ne pose plus sur un socle au-dessus d'un sol
  plat.
- *Règles* :
  - OA-TAL-001 (talus 3/2) ;
  - aucune règle de relief : relief **dit**, **mesuré** (MNT ou LiDAR HD, pour la reconstruction) ou **procédural [G]**
    déclaré. Dans ce dernier cas, la classe est tirée du lot 20 (`relief` : plaine, coteau, versant, vallée, tranchée).
- *HDA* : `rg::terrain::1.0` (lot N9). Il généralise le terrain du lot ouvrages : maillage croissant jusqu'à l'horizon de
  2 km et jupes. Pour les cours d'eau : lit, berges, perrés, surface d'eau. Matériaux : terre, herbe sèche, rocher,
  gravier. Pas de végétation (§ 6).
- *Scènes* : S01 sur un relief vallonné, A1 en remblai, D3 (non-régression), I03, I04.
- *Critères* :
  - couture terrain / route ≤ 1 cm, 0 trou ni recouvrement ;
  - 0 socle visible ;
  - horizon de 2 km ;
  - mêmes octets ;
  - rendu oblique regardé en tuiles : la route ne « flotte » plus.

**BK-19 — Talus, fossés, cunettes, descentes d'eau** (rang 12 · effort L)
- *Couvre* : TR-06 (12,4), TR-07, AS-04 et OA-07 (têtes d'aqueduc).
- *Règles* :
  - CAND-E4-001 et CAND-E4-002 (talus et retenue) ;
  - RC-AUT-014 (berme ≥ 1,00 m, pente ≤ 25 %) et RC-AUT-023 (berme à 8 %) ;
  - RC-AUT-015 (zone de sécurité) ;
  - OA-TAL-001 ;
  - GA-ASS-* (dépôt) ;
  - le guide Sétra *Assainissement routier* (2006) reste à obtenir (inventaire § 4.3).
- *HDA* : dans `rg::terrain`. Les bandes `talus`, `fossé` et `noue` du profil deviennent une vraie géométrie : pente,
  crête, pied, fossé en V ou trapézoïdal, cunette béton (T08), descentes d'eau.
- *Scènes* : A1 en remblai de 4 m, T05 en déblai, I03 (fossé), I04 (cunette amont).
- *Critères* :
  - pentes de talus = valeur dite à ± 0,5 % ;
  - fil d'eau continu, sans contre-pente ;
  - les talus qui relèvent de CAND-E4-002 sont signalés à BK-22 dans 100 % des cas.

**BK-20 — Dévers, gauchissement, surlargeur** (rang 27 · effort M)
- *Couvre* : TR-03 et TR-04 (9,3).
- *Règles* :
  - RF-GV-DEV-001 à -003 ;
  - RC-AUT-024 et RC-AUT-025 ;
  - RC-ECH-013, RC-ECH-018 et RC-ECH-019 (verglas : dévers ≤ 5 %) ;
  - RI-TRA-007 et RI-TRA-008 ;
  - RF-GV-RAY-012.
  
  **Conflit à arbitrer** (P-3) : surlargeur de 50/R (RF-GV-RAY-012, ARP p. 43) contre 25/R et 30/R (RI-TRA-007, ARP 2022
  p. 93). Il faut relire les deux pages sur tuiles pour savoir s'il s'agit de deux cas différents.
- *Code* :
  - dévers en fonction de la courbure dans `commun/profil.py`, par une nouvelle fonction ; l'ancienne reste pour les
    scènes existantes ;
  - `rg::nivellement::2.0`.
- *Scènes* : S11 hors agglomération (R 200), boucle de bretelle (R 50), I04.
- *Critères* :
  - dévers = loi(R) à ± 0,1 % ;
  - longueur de gauchissement = RC-ECH-013 ;
  - point de rotation conforme à RC-AUT-025 ;
  - surlargeur = règle arbitrée, à ± 1 cm.

**BK-21 — Murs de soutènement, parapets, murets, parois rocheuses** (rang 18 · effort M)
- *Couvre* : TR-08 (9,0).
- *Règles* :
  - RC-SOU-001 à -004 ;
  - RC-EQ-005 et RC-SOU-003 (un mur est traité comme un ouvrage pour la retenue) ;
  - RF-GV-PON-010 ;
  - OBS20-T08-LARGEUR_CHAUSSEE ; loi conditionnelle amont / aval de T08. Les hauteurs de mur (2,8 m) et de parapet
    (0,8 m) n'ont été mesurées qu'une fois : ce sont des valeurs de mise en scène, pas des lois (§ 3.5).
- *Assets à créer* : mur en moellons à barbacanes, pierre appareillée, mur en béton armé, gabions, parapet maçonné,
  couronnement, glissière mixte bois-métal (T08 : 0,67 côté aval).
- *HDA* : `rg::murs::1.0`, qui balaie une coupe le long d'une limite et lit le terrain.
- *Scènes* : I04, VRU en tranchée (T04 : « tranchée, déblai soutenu »), I07.
- *Critères* :
  - proportions de RC-SOU-001 et -002 ;
  - hauteur du parapet dite, ou de mise en scène déclarée ;
  - retenue côté vide (C-13) ;
  - 0 intersection entre un mur et la chaussée.

**BK-22 — Retenue posée par règle** (rang 14 · effort M)
- *Couvre* :
  - EQ-02, EQ-03 et EQ-04 (10,8) ;
  - la protection des piles, laissée à l'étape E13 par le lot ouvrages.
- *Règles* :
  - RC-EQ-003 à -010 (niveaux minimaux, obstacles à 4, 7 ou 8,5 m, longueurs avant et après, GBA et DBA) ;
  - RC-AUT-035 ;
  - CAND-E4-001 à -004 ;
  - RF-GV-PON-014 ;
  - RC-APP-018 (indice de danger) ;
  - RC-VSA-005 et RC-AUT-015 (zone de sécurité).
- *Assets* :
  - existants : glissières GS2, GS4 et DE2 ; 6 extrémités abaissées ; 4 atténuateurs ; GBA, DBA ;
  - à créer : raccord GBA-glissière, glissière mixte bois-métal (partagée avec BK-21).
- *HDA* : `rg::retenue::1.0` (étape E13). Elle décide où poser la retenue : zone de sécurité, talus, obstacles, piles,
  murs, côté vide. La retenue écrite en ligne par `rg::autoroute` reste valable.
- *Scènes* : A1 en remblai de 4 m, D1 (piles), I04, I06.
- *Critères* :
  - tout obstacle de la zone de sécurité isolé ou hors zone (100 %) ;
  - longueurs de RC-EQ-009 ;
  - 0 file qui finit net : extrémité ou atténuateur partout ;
  - déport entre 1/4 et 1/10 (CAND-E4-004).

**BK-23 — Route de montagne : lacets, profil asymétrique** (rang 25 · effort L)
- *Couvre* : TR-10 et la typologie T08. 33 fiches citent une route de col, 15 des lacets ; la fréquence est forte en
  Isère.
- *Règles* :
  - RI-TRA-003 à -009 ;
  - RF-GV-RAY-012 ;
  - RC-AUT-002 (relief difficile) ;
  - RC-EQ-016 ;
  - RF-SV-J1, RF-SV-J4 ;
  - lois de T08 ;
  - cohérences C-09, C-10, C-13 et C-26.
- *Code* : gabarits d'imagination `montee_lacets` et `corniche` (lot 19 § 3.4). Ils écrivent le tracé en épingles, le
  profil en long, les murs, la retenue et les balises.
- *Scènes* : I04 complète ; une route de gorges en option.
- *Critères* :
  - C-10 tenue partout (rayon interne ≥ minimum du véhicule de projet, surlargeur, pente au bord interne ≤ 5 %) ;
  - balayage de l'autocar de 15 m dans chaque épingle ;
  - amont et aval cohérents (C-26).

**BK-24 — Assainissement réglé par le fil d'eau** (rang 17 · effort M)
- *Couvre* : AS-02, AS-03 et RV-03 (11,1).
- *Règles* : GA-ASS-*, GA-CHA-003, GA-CHA-004, TQ-SOL-014, RF-MA-BUS-016.
- *Assets* :
  - existants : avaloir T2, grille 750 × 300, 2 regards Ø 600, bouche à clé ;
  - à créer : plaques télécom et gaz, tampons variés.
- *HDA* : `rg::assainissement::1.0` (lot N6).
- *Scènes* : S02, S03, J3, I01.
- *Critères* :
  - un avaloir à chaque point bas (100 %) ;
  - pas maximal déclaré ;
  - 0 ouvrage sur un passage ou une BEV.

#### Lot 4.4 — Réseau continu et échangeurs

**BK-25 — Réseau continu** (rang 9 · effort L)
- *Couvre* : RS-01, MQ-15 et RV-04 (15,6) ; IM-05 (assembler un quartier imaginé).
- *Règles* : étapes E05, E06 et E12 de la chaîne (lots N4, N5, N7) ; RF-MQ-U-05.
- *HDA* : `rg::plan_masse::1.0`, `rg::nivellement::2.0`, `rg::sol::2.0`, `rg::marquages::2.0` (phase par itinéraire).
- *Scènes* : « une avenue de 150 m entre un carrefour à feux et un giratoire » (rang 5 de l'inventaire) ; quartier imaginé
  composé à partir de J3, G1 et S03.
- *Critères* :
  - contrôles CC-03, CC-07, CC-08 et CC-12 (CHAINE § 4) ;
  - 0 couture de sol ni d'usure ;
  - phase des tirets continue à ± 1 cm ;
  - au moins deux carrefours sur une même route.

**BK-26 — Diffuseur en losange** (rang 13 · effort XL)
- *Couvre* : EC-04 et EC-07 (10,2). 49 fiches parlent d'échangeurs ; le lot 20 en a vu 2 sur 7 en losange, en rase
  campagne.
- *Règles* :
  - RC-ECH-001 à -048, notamment :
    - 020 (profil de bretelle) ;
    - 025 et 026 (obliquités) ;
    - 029 (sortie Sd1 de 150 m) ;
    - 032 (entrée Ei1 de 200 m plus 75 m) ;
    - 039 (musoir) ;
    - 044 (raccordement à la voirie ordinaire) ;
    - 046 (typologie) ;
  - RI-ECH-001 à -015 ;
  - RC-AUT-018 et RI-OUV-001 (hauteur libre) ;
  - RI-OUV-003 ;
  - RC-SD-001 à -005 (L6) ;
  - ARB-I-01 à 03 ;
  - schéma `D:\DocRoute\18_…\schemas\echangeur_losange.svg`.
- *Code* : gabarit `diffuseur_losange` dans un nouveau `description/echangeurs.py`, avec la clé `echangeurs`
  (FORMAT_DESCRIPTION_RESEAU § 7.4). Il écrit les tronçons, les bretelles (courbes, avec dévers et profil en long), les
  deux carrefours de raccordement (G2, J1 ou J3) et le PS (`ouvrages`, lot parallèle).
- *Scènes* : I06 ; X1 (losange à giratoires) ; X2 (losange à carrefours plans).
- *Critères* :
  - cohérences C-03, C-06, C-07 et C-12 ;
  - obliquités de 1/33 à 1/20 ;
  - Ld et La selon RC-ECH-014 et RC-ECH-015 ;
  - hauteur libre ≥ 4,75 + 0,10 m sous une autoroute (RC-AUT-018), 4,30 m ailleurs (RI-OUV-001) ;
  - premier rayon de sortie conforme à RC-ECH-011 ;
  - balayages du semi-remorque sur les bretelles et aux carrefours (§ 5).

**BK-27 — Trèfle partiel, demi-trèfle, trompette** (rang 22 · effort XL)
- *Couvre* : EC-05. Selon le lot 20, le **trèfle partiel à une boucle** est le diffuseur urbain le plus vu (3 sur 7), avec
  des boucles de 25 à 55 m de rayon.
- *Règles* :
  - RC-ECH-003 : une branche à deux voies n'est jamais en boucle ;
  - RC-ECH-009 : boucle de 60 m au plus, conseillé ;
  - RC-ECH-038, RC-ECH-047 ;
  - RC-ECH-004 : giratoire dénivelé déconseillé ;
  - RC-ECH-049 [G] : trompette si péage ;
  - OBS20-T02-RAYON_BOUCLE ;
  - schéma `echangeur_trompette.svg`.
- *Scènes* : X3 (trèfle partiel urbain, sur T04) ; X4 (trompette et péage, avec BK-29).
- *Critères* :
  - rayon de boucle dans la loi de T02 et ≤ 60 m ;
  - collectrice ≥ 60 m après tpl (RC-ECH-038) ;
  - balayages (§ 5).

**BK-28 — Bifurcation 2 + 2, convergence, entrecroisement, collectrice** (rang 30 · effort M-L)
- *Couvre* : EC-02 et EC-03. 23 fiches parlent de tronc commun, 11 de bifurcation, 8 d'entrecroisement. C'est aussi le
  besoin B2 du nœud A41 / N87.
- *Règles* :
  - RC-ECH-041 et RC-ECH-042 (entrecroisement de 500 à 750 m) ;
  - RC-VSA-011 (300 à 750 m) ;
  - RC-ECH-043 (np) ;
  - RI-ECH-005 à -008 ;
  - RF-MQ-DEC-01 ;
  - RF-SV-INSERTION.AB3A.
- *Scènes* : X5 (entrecroisement de VRU, T04) ; variante du nœud de Meylan pour la reconstruction.
- *Critères* :
  - Z dans la plage ;
  - marquage T3 ou T2 conforme ;
  - trajectoires de changement de voie balayées dans Z.

**BK-29 — Barrière de péage et portique à flux libre** (rang 33 · effort L)
- *Couvre* : EC-08 et la typologie T03 ; 17 fiches.
- *Règles* :
  - RC-AUT-033 (îlots de 30 à 45 m) ;
  - RC-AUT-034 (éclairage) ;
  - RC-AUT-016 (ITPC) ;
  - RC-SD-019 à -022 (signalisation, L6) ;
  - RF-FEU.R23 ;
  - OBS20-T03-LARGEUR_PLAZA (50 à 170 m) et OBS20-T03-NB_VOIES_PEAGE.
  
  [G] déclarés : largeur des couloirs, auvent, évasement (lot 18, lacune 5).
- *Assets à créer* : auvents (4 styles vus), îlots-cabines, cabines, barrières levantes, feux d'affectation, bâtiment
  d'exploitation simple, portique de flux libre.
- *HDA* : `rg::peage::1.0`.
- *Scènes* : I08 ; X4.
- *Critères* :
  - longueur des îlots dans RC-AUT-033 ;
  - éventail et rabattement balayés (§ 5) ;
  - éclairage présent (C-20).

**BK-30 — Voie express à carrefours plans : ouverture de TPC, demi-carrefour** (rang 31 · effort L)
- *Couvre* : CP-06 et CP-08. C'est le type 3.1 du catalogue Cerema (RI-TYP-006 : carrefours plans sans traversée du TPC).
- *Règles* : RF-GV-TPC-014, RF-GV-VS-008, RF-GV-ILO-007, RF-GV-VS-018.
- *Scènes* : X6 (2 × 2 à demi-carrefours).
- *Critères* :
  - aucun mouvement ne traverse le TPC hors ouverture dite ;
  - rayon de demi-tour balayé (§ 5).

#### Lot 4.5 — Équipements, ouvrages complémentaires et conditions ADAS

**BK-31 — Équipements d'autoroute : clôture, PR, refuges et PAU, ITPC** (rang 37 · effort M)
- *Règles* :
  - RC-EQ-021 à -024 (clôture) ;
  - RC-EQ-014 (PR tous les 1 000 m) ;
  - RC-AUT-027 à -029 (refuges tous les 2 km : 12 m + 40 m + 32 m ; PAU) ;
  - RC-AUT-016 (ITPC tous les 3 à 5 km) ;
  - RF-MQ-PAU-01 ;
  - RI-PRO-005.
- *Assets à créer* : clôture grillagée, portail, borne PAU orange, plaquette PR sur GBA.
- *Scènes* : A1 longue (3 km), I08.
- *Critères* :
  - pas des PR et des refuges conforme à ± 1 % ;
  - clôture continue, avec retours aux ouvrages (RC-EQ-024).

**BK-32 — Portiques, potences, PMV et séquence complète de sortie** (rang 19 · effort M-L · **avec L6**)
- *Règles* :
  - RC-SD-001 à -014 (séquence D50, D40, D30 ; distances d2 et d3 ; couleurs ; mentions) ;
  - RC-SD-024 (4,75 + 0,10 m) ;
  - RC-SD-027 ;
  - RF-SV-GEN.HAUTEUR.SURPLOMB ;
  - RF-SV-DIM.HB_CARACTERES ;
  - IISR 9e partie (PMV, p. PDF 3 à 43) ;
  - schéma `implantation_signalisation_direction_echangeur.svg`.
- *Assets* :
  - existants : `portique_signalisation_L1600`, `potence_signalisation_L600` ;
  - à créer : portique à treillis de grande portée, PMV.
- *Scènes* : A4 longue (2 km : D51c et D41a enfin dans la scène, ce que les scènes de 800 m du lot L6 ne permettent
  pas), I06, I07.
- *Critères* :
  - distances de RC-SD-004 et RC-SD-005 à ± 5 m ;
  - hauteur libre sous portique ≥ 4,85 m ;
  - mentions et couleurs conformes à RC-SD-010 à -013.

**BK-33 — Signalisation temporaire de chantier** (rang 29 · effort M)
- *Couvre* : SV-09 et MQ-12 ; cas d'école des essais ADAS de maintien dans la voie.
- *Règles* : RF-MQ-TMP-01, RF-OBS-MAR-03, RF-FEU.EXTENSION_EMPLOI, IISR 8e partie (p. PDF 3 à 46).
- *Assets* :
  - existants : faces K et AK (dont `panneau_AK5`) ;
  - à créer : cônes, K5c, K8, K16, GBA plastique.
- *Scènes* : « 2 × 2 avec basculement de chantier » ; S01 en alternat.
- *Critères* :
  - le jaune temporaire neutralise le blanc concerné ;
  - balisage au pas déclaré ;
  - trajectoires de basculement balayées (§ 5).

**BK-34 — Tunnel, tranchée couverte, trémie** (rang 28 · effort L · **avec le lot ouvrages**)
- *Couvre* : OA-06. 45 fiches citent un tunnel, 13 une tranchée couverte.
- *Règles* :
  - RC-TUN-001 à -022 (profils types, hauteur libre, trottoirs, niches tous les 200 m, issues, éclairage, signalisation
    d'arrêt) ;
  - RI-OUV-008 et RI-OUV-010 ;
  - RI-PRO-005 ;
  - C-14.
- *HDA* : extension de `rg::ouvrages` (types `tunnel`, `tranchee_couverte`), avec son propriétaire. À défaut,
  `rg::tunnel::1.0`.
- *Assets à créer* : têtes, voûte, piédroits, niches, luminaires de tunnel.
- *Scènes* : I04 avec deux tunnels courts (lot 19 § 8.2) ; trémie urbaine sous un giratoire.
- *Critères* :
  - profil type et hauteur libre de RC-TUN-017 à -020 ;
  - niches au pas de RC-TUN-009 ;
  - profil de la section courante conservé (C-14).

**BK-35 — Écrans acoustiques** (rang 36 · effort M)
- *Règles* : RC-EQ-017 à -020 (dont [G] entraxe et hauteur), RI-OUV-007, RC-APP-016.
- *Assets à créer* : panneaux absorbants, poteaux HEA, écrans transparents, gabions.
- *Scènes* : I07.
- *Critères* :
  - écran derrière la retenue (RC-EQ-018) ;
  - hauteur dans la plage ;
  - 0 écran dans la zone de sécurité sans retenue.

**BK-36 — Conditions de rendu : nuit, pluie, rétroréflexion** (rang 16 · effort L)
- *Règles* : RF-SV-GEN.RETROREFLEXION, RF-MQ-RETRO-01.
- *Code* : rendus Karma de nuit (candélabres de BK-02, phares) et sous la pluie (chaussée mouillée) ; matériaux UE
  correspondants.
- *Scènes* : I07 de nuit, J3 sous la pluie.
- *Critères* :
  - panneaux et marquages plus lumineux que l'enrobé, de nuit en vue conducteur, avec un ordre conforme aux classes de
    rétroréflexion ;
  - planches regardées en tuiles.

**BK-37 — Aires de repos et de service** (rang 38 · effort L)
- *Couvre* : EC-09 ; 26 fiches.
- *Règles* : RC-AUT-030 (au plus 30 et 60 km), RC-ECH-050, RC-SD-015 à -018, RC-EQ-025.
- *Scènes* : « autoroute avec une aire de repos ».
- *Critères* :
  - bretelles d'aire conformes à RC-ECH-050 ;
  - séquence D46 posée (L6) ;
  - parkings marqués (BK-06).

**BK-38 — Jalonnement cyclable Dv, plaques de rue E60, localisation, confirmation** (rang 34 · effort S · **avec L6**)
- *Règles* : RF-SV-DV.POSITION, RF-SV-E60.PLAQUE_RUE, RF-SV-D21.POSITION ; IISR 5e partie pour les D61 (confirmation)
  et les D29, absents du lot L6.
- *Code* : compositions ajoutées à `faces_composees.py` (L6).
- *Scènes* : I01, I10.

## 3. Le mode « imagination »

### 3.1 Ce qu'il fait, ce qu'il ne fait pas

- **Il fait.** Il transforme une phrase, ou une typologie, en une **description simple** au format existant
  (`description_simple/0.1` et `0.2`, avec les clés `ouvrages` et `echangeurs` quand elles sont prises en charge). Cette
  description est plausible pour une route française :
  - elle reprend les valeurs des règles et les fréquences observées en France ;
  - elle reste reproductible ;
  - elle est contrôlée.
  
  Il écrit aussi le complément de signalisation lu par L6, et un rapport des choix.
- **Il ne fait pas.** Il ne fabrique rien : la chaîne existante (`fabriquer_generateur.py --complet`, puis les ouvrages et
  L6) reste l'unique porte vers Houdini. Il ne recopie aucun lieu : une phrase qui nomme un lieu réel (« la rocade sud de
  Grenoble ») fournit des **indices de typologie** (T04, RI-URB-001), jamais une géométrie OSM. La reconstruction fidèle
  est un autre mode (Meylan).
- **Il n'écrit que ce que le générateur sait fabriquer.** Tout élément tiré mais non fabricable est rangé dans
  `imagination.json`, rubrique `non_fabrique`, avec le BK qui le fabriquera (cohérence C-16). Le compilateur refuse les
  clés inconnues : les clés « + » du lot 19 (`relief`, `equipements`, `exploitation`) restent dans le rapport jusqu'à ce
  que le lot qui les porte les ajoute au format.

### 3.2 Entrées

```
python recon/generateur/imagination/imaginer.py "une petite route de campagne bordée de haies"
       [--typologie T07] [--fiche-photo FICHE.json] [--variante 3] [--conformite existante|neuve]
       [--style-local grenoble] [--sortie DOSSIER] [--fabriquer]
python recon/generateur/imagination/imaginer.py --typologie T07 --variante 3
python recon/generateur/imagination/imaginer.py scenes_imagination/I03.yaml
```

- **Phrase** : lue avec `vocabulaire_parametres.json` (motifs, paramètres, règles) et la grammaire du lot 19 : itinéraires,
  évènements, qualificatifs, connecteurs.
- **Typologie** : T01 à T12 (lot 20). Elle est donnée, ou déduite de la phrase (§ 3.8), ou déduite de la fiche photo.
- **Fiche photo** (facultative). Claude la rédige après avoir lu la photo en **tuiles natives** (`decoupe.py` ;
  `equirect` pour une 360°). Elle suit le schéma d'une entrée de `observations.json` du lot 20 : attributs avec valeur,
  unité, incertitude et méthode ; panneaux ; marquages ; équipements. Le script ne lit **jamais** la photo elle-même. La
  photo reste dans `photos_tiers_locales/` ou `photos_non_versionnees/` ; la fiche n'en garde que l'identifiant, le lien
  et la licence.
- **Variante** : un entier. La variante 0 est la scène **typique** : mode des lois triangulaires, valeur la plus probable
  des lois discrètes, site-modèle le plus central. Elle sert aux démonstrations.
- **Conformité** : `existante` (défaut proposé, § 3.7) ou `neuve`.
- **Style local** : `grenoble` autorise les pratiques locales photographiées de DocRoute 13 (RF-OBS-*, inventaire MQ-17).
  Sans cette option, l'IISR seule.

### 3.3 La chaîne

```
phrase ──┐                                     règles RF / RC / RI (bornes)        lois du lot 20 (+ sites-modèles)
typologie ┼─► LIRE ─► TYPER ─► PLAN DE SCÈNE ─► TIRER (graine) ─► GABARITS ─► CONTRÔLER C-01…C-30 ─► ÉCRIRE
fiche photo┘   (lot 19 § 2)   (itinéraires,     (§ 3.4 à 3.6)    (lot 19 § 3.4,   (bloquant → refus    description.yaml
                              évènements,                         § 3.14 ici)      motivé)              complément L6
                              ordre)                                                                    imagination.json
   ─► fabriquer_generateur.py --complet (+ ouvrages + L6) ─► rendus (dessus, oblique 3/4, conducteur, planche ≤ 1 092 px)
   ─► confrontation à la typologie : planche rendu | photos de référence (locale, jamais diffusée) ; fréquences (§ 3.12)
```

### 3.4 D'où vient chaque valeur (ordre de priorité)

| Rang | Source | Provenance écrite | Exemple |
|---|---|---|---|
| 1 | La phrase (mot, nombre, quantificateur flou) | `phrase:<fragment>` | « 2×3 », « petite » → chaussée étroite (lot 19, VOCABULAIRE § 4) |
| 2 | La fiche photo | `photo:<id>` | largeur de BAU lue sur la photo T04_01 |
| 3 | Une règle qui fixe la valeur dans ce contexte | `regle:RC-ECH-029` | biseau de sortie de 150 m |
| 4 | Une loi conditionnelle observée | `loi_cond:T01.separateur_central_selon_largeur_tpc` | GBA si le TPC fait de 3,5 à 6 m |
| 5 | Le site-modèle (attributs catégoriels conjoints) | `site_modele:T07_02_trieves` | revêtement, marquage d'axe, équipements du même site |
| 6 | Une loi marginale observée (n ≥ 3) | `loi:T07.largeur_chaussee` | triangulaire de 2,8 / 4,15 / 5,6 m |
| 7 | Une statistique du corpus | `corpus:RI-ECH-012` | interdistance des échangeurs |
| 8 | Un arbitrage déclaré | `arbitrage:ARB-I-01` | giratoires aux extrémités d'un losange hors agglomération |
| 9 | Une valeur de mise en scène ou « à dire » | `mise_en_scene` / `a_dire` | 300 m de marge avant le premier évènement |

Une valeur des rangs 4 à 8 est ensuite **bornée par les règles**. Le mode `neuve` la ramène dans les bornes. Le mode
`existante` accepte la valeur observée et déclare l'écart (§ 3.7).

### 3.5 Lire correctement les lois du lot 20

Il y a trois pièges, vus en lisant `parametres_typologies.json` :

1. **`valeurs` est normalisé sur les sites où l'attribut est renseigné.** Exemples :
   - T05 `marquage_voies` vaut `{temporaire_jaune: 1.0}`, alors que `part_des_sites` vaut 0,12 : un seul site sur huit ;
   - même cas pour T07 `bordure` (0,12), T09 `eclairage` (0,25), T10 `plain_pied` (0,14).

   **Règle de tirage** : tirer dans `part_des_sites`. Le reste de la masse (1 − Σ) va à la valeur **par défaut de la
   règle**, par exemple le marquage blanc de RF-MQ-SC-*. Sinon, une voie express sur deux serait tirée en marquage jaune
   de chantier.
2. **Petits effectifs.** Une loi numérique observée sur moins de 3 sites n'est pas tirée telle quelle. On prend la
   règle, sinon « à dire ». Exemples : T07 `vitesse_affichee` (1 site, 50 km/h) ; T03 `longueur_biseau` (1 site). Les
   bornes des lois triangulaires sont déjà élargies de l'incertitude de mesure (convention du lot 20) : il ne faut pas
   les élargir une seconde fois.
3. **Attributs corrélés.** Des lois marginales tirées séparément produisent des contradictions. La variante 3 de T07
   donne par exemple « enrobé très usé, rapiécé » pour `etat_chaussee` et « enrobé gris foncé régulier » pour
   `revetement_chaussee` (§ 3.13). Le tirage se fait donc en deux temps :
   - **site-modèle** (défaut) : un site de la typologie est tiré au hasard ; ses attributs catégoriels sont repris
     **ensemble**, ce qui garde les corrélations ;
   - **valeurs numériques** : tirées dans une triangulaire centrée sur la valeur du site, à plus ou moins son
     incertitude, puis bornée par la loi de la typologie ;
   - **attributs non renseignés sur ce site** : tirés dans les lois marginales.
   
   On ne reprend que des attributs, jamais la géométrie ni le nom du site. Le mode `--lois-marginales` reste disponible
   pour les tests.

Point de données à reprendre par le lot 20 : `nb_voies_peage` (T03) est une loi discrète sur cinq valeurs. Une loi
triangulaire de 7, 14 et 26 voies conviendrait mieux.

### 3.6 Aléa contrôlé

- **Graine** de la scène : les 16 premiers caractères hexadécimaux de
  `sha256("imagination/0.1|typologie=<T>|phrase=<phrase normalisée>|variante=<n>")`, une partie vide restant vide
  (exemple du § 3.13 : `typologie=T07|phrase=|variante=3`). La phrase est normalisée en minuscules, sans accents, avec
  les espaces réduits, comme dans `vocabulaire.py`.
- **Sous-graine** par paramètre : `sha256(graine + "|" + chemin du paramètre)`, d'où un tirage uniforme u dans [0 ; 1[.
  Ajouter un paramètre à la grammaire ne change donc pas les tirages des autres. Les variantes restent stables d'une
  version à l'autre.
- **Lois** :
  - discrète : cumul des probabilités dans l'ordre du fichier ;
  - triangulaire : fonction de répartition inverse ;
  - présence : u < p.
  
  Les résultats sont arrondis au pas du format : 0,05 m pour les largeurs, 1 m pour les abscisses.
- **Déterminisme** : mêmes entrées, mêmes octets pour `description.yaml`, `imagination.json` et le complément L6 (aucune
  date). Comme le reste de la chaîne.

### 3.7 Conformité : route neuve ou route existante

Les règles de conception valent pour les routes **neuves**. Les routes **observées** s'en écartent souvent : chaussée
de 3,4 m sans marquage (T07), BAU de 1 m (T05), pentes de 12 % (RI-TRA-009). Le but est d'imaginer des routes
françaises telles qu'on les voit. D'où deux modes :

- `existante` (défaut proposé, décision 4 du § 6) : une valeur observée hors des bornes d'une règle est gardée.
  - Si le compilateur **contrôle** cette règle, la description reçoit un écart admis (`ecarts_admis`) dont le motif cite
    l'observation : identifiant OBS20 et site-modèle.
  - S'il ne la contrôle pas, l'écart est noté dans `imagination.json` (`ecarts_non_controles`). Écrire un écart admis
    sans contrôle correspondant provoque un avertissement du compilateur (« à retirer ») : constaté sur l'exemple du
    § 3.13.
- `neuve` : toute valeur est ramenée dans les bornes de la règle, et aucun écart admis n'est écrit.

### 3.8 Typologies, fiches-types et familles du générateur

| Typologie (lot 20) | Fiche-type (lot 19) et type Cerema | Indices dans une phrase | Familles du générateur | État aujourd'hui |
|---|---|---|---|---|
| T01 Autoroute, section courante | 2.1, type 1 | « autoroute », « A41 », « à péage » | A1, A2 | ◐ section faite ; talus, retenue de rive, clôture, PR absents |
| T02 Échangeur, diffuseur | § 3 | « échangeur », « sortie », « demi-échangeur », « losange », « trèfle » | A3, A4 + G2, J3 | ✗ assemblage absent (BK-26, BK-27) |
| T03 Péage | 2.1 | « péage », « barrière de péage », « flux libre » | — | ✗ (BK-29) |
| T04 Voie rapide urbaine | 2.2, type 5 | « rocade », « périphérique », « voie rapide urbaine », nom d'agglomération | A1 adapté | ◐ éclairage, portiques, murs absents |
| T05 Voie express 2 × 2 | 2.3, type 1 express | « voie express », « 2x2 » sans indice urbain | A1, A2 | ◐ profil fait ; usure absente |
| T06 Créneau, route 2 + 1 | 2.5, type 4.2 | « trois voies », « créneau », « dépassement » | S09 (rabattement) | ✗ alternance absente (BK-07) |
| T07 Campagne étroite | 2.5, type 4.1 étroit | « petite route », « chemin », « campagne », « étroite » | S01 | ◐ presque faisable ; haies (végétation), usure |
| T08 Montagne | 2.6, 2.7 | « col », « lacets », « montagne », « gorges », « corniche » | — | ✗ (BK-17 à BK-23) |
| T09 Traverse d'agglomération | 2.5 → 2.8 | « traverse », « entrée de village », « bourg », « chicane » | E01 (L6) | ◐ chicane, îlot d'entrée absents |
| T10 Rue de centre-ville | 2.8, type 8 | « centre-ville », « rue commerçante », « piétonne » | S02, S03, S07 | ◐ mobilier, places, usure absents |
| T11 Zone 30 / rencontre | 2.8 | « zone 30 », « zone de rencontre », « résidentielle » | S08, S10, G3 | ◐ entrée de zone absente |
| T12 Ponts, viaducs, PI | § 4 | « pont », « viaduc », « passe sous », « enjambe » | D1 à D4 (parallèle) | en cours ailleurs |

Les carrefours plans (J1 à J6) et les giratoires (G1 à G4) n'ont pas de typologie dans le lot 20 : la grammaire les
appelle par leurs gabarits (lot 19 § 3.4), avec les règles et les observations du dossier 13.

### 3.9 Cohérences obligatoires

On reprend telles quelles les cohérences **C-01 à C-15** du lot 19 (`GRAMMAIRE_IMAGINATION.md` § 5) : pas de carrefour
plan sur une voie de type Cerema 1 ou 5 (notés T1 et T5 dans le lot 19, à ne pas confondre avec les typologies T01 à T12
du lot 20), TPC et BDG d'une 2 × 2, diffuseur avec rétablissement, symétrie des échangeurs
partiels, gabarit sous ouvrage, zones de divergence et de convergence libres, enchaînements, vitesse et géométrie,
pentes, lacets, voie centrale banalisée proscrite, topologie des bretelles, côté vide, tunnel. Elles s'étendent ainsi :

| Id | Cohérence | Nature | Règles |
|---|---|---|---|
| C-16 | Rien de non fabricable dans `description.yaml` ; chaque élément non fabriqué est listé avec son BK | bloquant | (format) |
| C-17 | Attributs catégoriels tirés ensemble (site-modèle) ; aucune paire contradictoire (état / revêtement, éclairage / environnement) | bloquant | § 3.5 |
| C-18 | Séparateur central selon la largeur du TPC : loi conditionnelle de T01 ; barrière si TPC < 12 m ; VRU : GBA double face sans TPC admise | bloquant | RF-GV-TPC-008, RF-GV-TPC-002, RF-GV-TPC-003 |
| C-19 | Pas de ligne d'axe sous 5,20 m circulables | bloquant | RF-OSM-MRQ-010 |
| C-20 | Éclairage : jamais en section courante d'autoroute de liaison ; toujours aux péages ; VRU éclairée selon la loi de T04 | bloquant | RC-AUT-034 |
| C-21 | Créneau : jamais en amont d'un point dur ; alterné ; longueur et fin réglementaires | bloquant | RC-ARP-001, RC-ARP-004, RC-ARP-006 |
| C-22 | Entrée d'agglomération : transition de profil à l'EB10 (± 20 m [G]) ; vitesse ≤ 50 après ; prescriptions groupées | bloquant | RF-SV-EB.POSITION, RF-SV-EB10.PRESCRIPTIONS |
| C-23 | **Zone de conflit et trajectoires** : contrôles du § 5.8 tenus pour tous les mouvements et tous les véhicules de projet du contexte | bloquant | § 5 |
| C-24 | Élément « presque toujours » de la typologie non tiré, alors que la phrase ne l'exclut pas | avertissement | lot 20 |
| C-25 | Largeur de voie cohérente avec la vitesse (loi conditionnelle de T04 ; 3,00 à 3,50 m à 70 km/h) | bloquant | RF-GV-PT-006, RF-GV-PT-008 |
| C-26 | Montagne : mur ou paroi côté amont, parapet, muret ou glissière côté aval ; jamais l'inverse | bloquant | loi conditionnelle de T08 ; C-13 |
| C-27 | Somme des bandes = largeur de façade à façade (T10, T11) à ± 0,10 m, quand cette largeur est dite ou tirée | bloquant | lot 20 |
| C-28 | Vitesse cohérente avec la typologie et le contexte : zone 30 ≤ 30 ; zone de rencontre 20 ; VRU 70 ou 90 | bloquant | RF-MA-ZCA-001, RI-URB-001 |
| C-29 | Un nom de lieu réel ne déclenche jamais la lecture d'OSM ni la copie d'une géométrie | bloquant | § 3.1 |
| C-30 | Toute valeur porte une provenance du § 3.4 ; « à dire » et « mise en scène » sont listés dans le rapport | bloquant | — |

Arbitrages proposés en plus de ARB-I-01 à 03. Ce sont des choix [G], à confirmer :

- **ARB-I-04**, forme d'un diffuseur non nommé. Amende ARB-I-02 d'après le lot 20 (T02) : **losange** en rase campagne,
  **trèfle partiel à une boucle** en milieu urbain.
- **ARB-I-05**, tracé non dit d'une route rurale. **Droit** par défaut, plus une mise en scène déclarée. Des courbes
  seulement si la phrase les dit (« sinueuse ») ou si la typologie a une loi de courbure (T08, `variation_cap_80m`). Le
  lot 20 n'a pas mesuré la courbure des autres typologies.
- **ARB-I-06**, noms de lieux sur les panneaux d'une scène imaginée. Noms **fictifs** de forme française (Saint-…,
  …-sur-…) [G], tant que l'utilisateur n'a pas choisi des communes réelles (§ 6, décision 3).
- **ARB-I-07**, véhicules de projet par contexte : voir le § 5.4.

Le lot 20 conforte les arbitrages ARB-I-01 et ARB-I-03 du lot 19 sur un petit échantillon. Pour T02, il trouve un
passage supérieur dans 4 diffuseurs sur 7, et des extrémités de bretelle en giratoire dans 2 cas sur les 3 renseignés.

### 3.10 Sorties

```
recon/out/generateur/imagination/<id>_v<variante>/
  description.yaml        format existant ; compilable ; clés connues seulement
  complement_l6.yaml      complément de signalisation (nom fictif de commune, destinations, limites, numéro de sortie)
  imagination.json        schéma imagination/0.1 :
                            entree {phrase, typologie, fiche_photo, variante, conformite, style_local}, graine
                            lecture  [fragments → entrées du vocabulaire]
                            choix    {chemin: {valeur, prov, regle_bornes, loi, u}}
                            site_modele {id, attributs repris}         (jamais de géométrie)
                            controles [C-xx : ok | avertissement | refus + message]
                            ecarts_admis_ecrits, ecarts_non_controles
                            non_fabrique [{element, tire_par, bk: "BK-xx"}]
                            cles_proposees {relief, equipements, exploitation…}   (lot 19 § 6)
  <chaîne existante>      modele_voie.json, l1/ … l6/, ouvrages/, rendus/
```

### 3.11 Avec une photo de référence

1. **Choisir la photo.** Elle vient du lot 20 (sites T01 à T12, liens dans `observations.json`) ou d'une nouvelle
   recherche Panoramax. Pour Mapillary, le jeton se lit seulement dans
   `%USERPROFILE%\.config\meylan_adas\mapillary_token.txt`.
2. **Découper.** Tuiles natives de 1 092 px au plus (`decoupe.py equirect` ou `image`), dans `photos_non_versionnees/`.
3. **Lire et remplir la fiche.** Claude lit les tuiles et remplit la fiche au schéma du lot 20 : attributs avec
   incertitude ; ce qui n'est pas lisible reste vide.
4. **Imaginer.** `imaginer.py --fiche-photo` fixe les attributs de la fiche (`photo:<id>`) et tire le reste. Avec
   `--varier-photo`, les valeurs de la fiche sont tirées dans plus ou moins leur incertitude.
5. **Confronter.** Planche rendu conducteur | photo, regardée en tuiles et gardée locale, jamais diffusée. Elle est
   remplie comme la grille `ecarts.json` de l'outil de comparaison v2, mais sans pose : la scène est imaginée, pas
   recalée.

### 3.12 Plausibilité et calibration

- **Fidélité des fréquences.** Pour chaque typologie, on tire 50 variantes. Pour tout élément de présence p ≥ 0,4, la
  fréquence tirée doit rester dans p ± 0,15. Avec n = 50, l'écart-type à p = 0,5 vaut environ 0,07. Les valeurs
  numériques doivent tomber à 100 % dans [min ; max] de la loi.
- **Conformité.** En mode `neuve`, 0 valeur hors des bornes d'une règle. En mode `existante`, chaque écart est déclaré.
- **Regard.** Pour chaque typologie, une planche 2 × 2 de 4 variantes (1 092 px) et une planche rendu | photo de
  référence. Le relevé suit les rubriques « presque toujours / souvent / rarement » du lot 20.
- **Calibrer les arbitrages.** Méthode du lot 19 § 9 : 20 diffuseurs de l'Isère, relevés de la même façon que le lot 20.
  Les comptes vont dans les règles observées, et ARB-I-01 à 04 sont révisés.

### 3.13 Exemple chiffré : typologie T07, variante 3

Calcul fait le 22/10/2026 avec les fonctions du § 3.6, sur `parametres_typologies.json` : graine `cdccef1a42c8aa6a`.

**Tirage par lois marginales seules** (mode de test). Il donne :
- chaussée de 3,83 m, une voie, accotement en herbe, aucun axe ;
- `etat_chaussee` « enrobé très usé, rapiécé, gravillons », mais `revetement_chaussee` « enrobé gris foncé régulier » :
  c'est la **contradiction** qui justifie la règle C-17 ;
- présences : glissière (u = 0,174 < 0,25) et arbres d'alignement (u = 0,031 < 0,12), ces derniers non fabriqués
  (végétation, étape ultérieure).

**Tirage par site-modèle** (défaut). Il tire `T07_02_trieves` (u = 0,174), un chemin rural non revêtu de 3,5 m
(± 0,7 m) avec J6 et glissière simple. Les attributs catégoriels sont repris ensemble : gravier ou terre, aucun axe,
milieu rural. La chaussée est tirée dans la triangulaire 2,8 / 3,5 / 4,2 m (u = 0,282) : **3,35 m**. On obtient :

```yaml
format: description_simple/0.1
scene: I03_T07_v3
titre: "Imaginée : petite route de campagne (T07, variante 3)"
description: "Typologie T07, variante 3 ; site-modèle T07_02_trieves (attributs seulement, aucune géométrie recopiée)."
contexte:
  agglomeration: non
  categorie: route départementale        # vitesse non dite : 80 km/h par règle (loi T07 sur 1 site, non tirée)
troncon: {de: [0, 0], vers: [300, 0]}      # tracé droit : ARB-I-05 ; 300 m : mise en scène
profil: "accotement herbe 1,0 | chaussée partagée 3,35 gravier | accotement herbe 1,0"
marquages: {usure: forte}
abords: {gauche: pelouse 6, droite: pelouse 6}
attendus: {longueur: 300}
```

- **Compilation à blanc**, en mémoire, sans écrire de fichier, avec `description_vers_modele.compiler` : 0
  non-conformité, 0 avertissement. La validation du schéma n'a pas été jouée : le module `jsonschema` est absent en mode
  isolé. La vitesse de 80 km/h vient de la règle. La chaussée partagée de 3,35 m en gravier est bien portée.
- **Écart de largeur.** La largeur est inférieure aux 4,00 m de RF-GV-PT-004 (deux VL à faible vitesse), mais le
  compilateur ne contrôle pas cette règle. Un `ecarts_admis` produit l'avertissement « admis sans aucun contrôle non
  conforme correspondant ». L'écart va donc dans `imagination.json`, rubrique `ecarts_non_controles`, avec
  OBS20-T07-LARGEUR_CHAUSSEE.
- **Non fabriqué** : J6 (BK-04), glissière de rive posée par règle (BK-22), état de surface (BK-03). Une haie aurait été
  rangée en végétation, étape ultérieure ; elle n'a pas été tirée ici.

### 3.14 Dix phrases et les scènes qu'elles doivent donner

Chaque entrée est un fichier `scenes_imagination/Ixx.yaml` (`format: imagination/0.1`, phrase ou typologie, variante,
attendus). Pour chacune, le plan donne :
- la lecture ;
- ce que la scène doit contenir (valeurs, lois, règles) ;
- ce qui est interdit ;
- ce qu'on peut fabriquer aujourd'hui, et après quel BK ;
- les contrôles d'acceptation.

**I01 — « une rue commerçante de centre-ville à sens unique, avec du stationnement d'un côté et des potelets »**
- *Lecture* :
  - T10 : indices « centre-ville », « commerçante » ;
  - agglomération ; catégorie rue ;
  - vitesse tirée dans {20 : 0,2 ; 30 : 0,8} (n = 5).
- *Scène attendue* : 120 m droits (mise en scène). Profil, de gauche à droite :
  - trottoir : loi de 0,7 à 4,5 m, mode 2,25 ;
  - bordure granit (part 0,57, sinon béton) ;
  - stationnement longitudinal de 1,7 à 2,3 m ;
  - une voie à sens unique de 2,5 à 4,0 m (RF-GV-PT-001). La phrase fixe le sens unique ; parmi les 5 rues à sens
    unique du lot 20, 2 ont un double sens cyclable, d'où une probabilité conditionnelle de 0,4 ;
  - bordure, trottoir.
  
  La somme des bandes est égale à la largeur de façade à façade tirée (6 à 27,5 m ; C-27). Un passage piéton (0,57). Les
  potelets sont **dits** : présents le long des deux bordures.
- *Interdits* : ligne d'axe sur la voie unique ; potelet sur un abaissé ou une BEV ; cheminement libre < 1,40 m.
- *Fabricable* :
  - aujourd'hui : profil, bordures, stationnement, passage, sens unique (S02, S03, S07) ;
  - après BK-05 : potelets, arceaux ;
  - après BK-06 : places marquées (0,43), livraison jaune (0,29), logo vélo ;
  - après BK-03 : enrobé rapiécé ;
  - après BK-02 : candélabres ;
  - non fabriqués : vitrines et arbres (végétation et bâti).
- *Contrôles* : C-16, C-17, C-27, C-28 ; cheminement ≥ 1,40 m.

**I02 — « une départementale qui traverse un village : panneau d'entrée, une chicane puis un plateau devant l'école »**
- *Lecture* : itinéraire T09 avec trois évènements ordonnés : entrée, chicane, plateau. « École » ajoute un passage sur
  le plateau et la signalisation A13b, posée par L6 comme dans E01.
- *Scène attendue* : 400 m.
  - De 0 à 150 m, rase campagne : 2 × 3,00 m, BDD de 0,50 m, accotements en herbe.
  - À 150 m, EB10 / EB20 (L6) et transition vers une rue :
    - chaussée tirée dans la loi de T09 (observée de 4,0 à 7,5 m) ;
    - trottoirs de 1,5 à 2,0 m ;
    - bordures béton (4 sites sur 8 ; granit 1 ; sinon valeur par défaut) ;
    - axe seulement si la chaussée fait 5,20 m ou plus (C-19).
  - Vers 220 m, chicane :
    - avancées alternées avec jardinières (0,5) ;
    - B15 et C18 (L6) ;
    - monochevrons J4.
  - Vers 300 m, plateau avec passage :
    - hauteur ≤ 0,15 m, rampants de 5 à 10 % (RF-GV-RAL-002, DEF-034) ;
    - A13b et C20a (L6).
- *Interdits* : chicane à moins de 50 m de l'EB10 [G] ; passage de chicane plus étroit que la règle versée (P-3).
- *Fabricable* : aujourd'hui, la scène E01 sans la chicane ; après BK-08, la scène complète.
- *Contrôles* : C-19, C-22 ; alternat de la chicane (§ 5.3) avec bus et porteur.

**I03 — typologie seule : `--typologie T07 --variante 3`** (« petite route de campagne »)
- *Scène attendue* : celle du § 3.13. Les autres variantes doivent couvrir :
  - une chaussée de 2,8 à 5,6 m ;
  - pas d'axe dans 88 % des variantes environ ;
  - accotements en herbe ou en gravier ;
  - des haies, rangées en non fabriqué : végétation.
- *Contrôles* : C-17, C-19, C-30 ; fidélité des fréquences sur 50 variantes (§ 3.12).

**I04 — « une petite départementale qui monte en lacets vers un col, avec un muret côté vide »**
- *Lecture* : T08 en relief difficile.
  - « Petite » → chaussée de 5,00 m sans axe (RF-OSM-MRQ-010).
  - « Monte » → pente de 6 à 8 % (RI-TRA-003).
- *Scène attendue* :
  - **Lacets** : leur nombre est à dire. Par défaut, 4 sur 1,2 km (mise en scène déclarée).
  - **Épingles** :
    - rayon interne ≥ 21 m pour l'autocar sur une chaussée de 5 m (RI-TRA-006) ;
    - surlargeur selon la règle arbitrée (P-3) ;
    - dévers de 7 % (RI-TRA-008) ;
    - pente au bord interne ≤ 5 % (RI-TRA-004).
  - **Côté amont** : mur de soutènement (2 sites sur 7), paroi rocheuse (2), sinon talus de déblai. La hauteur du mur
    n'a été mesurée qu'une fois (2,8 m) : elle n'est pas tirée (§ 3.5) et devient une valeur de mise en scène déclarée.
  - **Côté aval** : le muret dit. Sa hauteur est à dire ; à défaut, 0,8 m de mise en scène (une seule mesure observée).
  - **Équipements** :
    - J1 ou J4 dans les épingles ;
    - cunette amont ;
    - glissière mixte bois-métal là où il n'y a pas de muret (2 sites sur 7).
- *Interdits* : pente > 8 % sans « ancienne » ni « raide » (C-09) ; aval sans retenue (C-13) ; amont et aval inversés
  (C-26).
- *Fabricable* : rien de juste aujourd'hui. Le module écrit seulement le plan coté à plat et un refus partiel motivé
  (« profil en long non fabriqué »). La scène complète vient après BK-17 à BK-23, plus BK-04.
- *Contrôles* : C-09, C-10, C-13, C-26 ; autocar balayé dans chaque épingle (§ 5).

**I05 — « une nationale avec un créneau de dépassement dans une longue montée »**
- *Lecture* : T06 ; « longue montée » → créneau de 600 m en rampe (RC-ARP-001) et rampe de 4 à 6 % [G, à verser].
- *Scène attendue* : 2 000 m.
  - 2 × 3,50 m, puis ouverture du créneau sur le sens montant : décrochement de 130 m (RC-ARP-005).
  - 3 voies de 3,45 à 3,6 m, chaussée de 10,4 à 10,8 m.
  - Axe continu côté sens à une voie (5 sites sur 7 ; mixte 1), T1 entre les voies de même sens, rives discontinues.
  - Fin du créneau : rabattement de 234 m, puis tampon de 88 m (RC-ARP-006) et flèches de rabattement.
  - Vitesses : 90 km/h sur le sens du créneau, 80 sur l'autre (RC-ARP-009).
  - Accotements en herbe ; J6 dans 29 % des variantes.
- *Interdits* : accès ou carrefour dans le créneau ou à moins de 300 m (C-21) ; trois voies banalisées (C-11).
- *Fabricable* : à plat après BK-07 ; avec la rampe après BK-17 ; J6 après BK-04.
- *Contrôles* : C-11, C-21 ; convergence du rabattement balayée (§ 5).

**I06 — « une voie express 2×2 qui passe sur un pont puis un échangeur en losange vers une départementale »**
- *Lecture* : l'exemple complet du lot 19 (GRAMMAIRE § 7) : T05 + T12 + T02. Les lois du lot 20 y remplacent les
  valeurs fixes.
- *Scène attendue* :
  - **Section courante** : voies de 3,40 à 3,65 m ; TPC de 1,9 à 4,8 m ; séparateur GBA double face ou glissière double
    (C-18). BAU de 2,50 m en mode `neuve` (RI-PRO-007). En mode `existante`, BAU tirée de 1 à 3 m, ou BDD de 1 à 1,5 m
    si elle est étroite.
  - **Vitesse** : 110 km/h, ou 90 km/h si la phrase dit « en Isère » (lot 20).
  - **Pont** : PI sur ruisseau (talweg, lot ouvrages), tiré en {route, ruisseau, rivière}.
  - **Losange** :
    - PS de la RD (hauteur libre de 4,30 m au moins, plus 0,10 m) ;
    - deux giratoires hors agglomération (ARB-I-01) ;
    - sorties de 150 m et entrées de 200 m plus 75 m ;
    - J14a (L6) et séquence de sortie (L6, BK-32).
  - **Distance du pont au biseau de sortie** : au moins lc (C-06).
- *Fabricable* :
  - aujourd'hui, en morceaux : A1, A3, A4, G2, D1, D2 ;
  - assemblage après BK-26 ;
  - rampes de la RD et dévers des bretelles après BK-17 et BK-20.
- *Contrôles* : C-01 à C-08, C-12, C-18 ; trajectoires de bretelle et de giratoire (§ 5).

**I07 — « la rocade sud de Grenoble à 70, avec un GBA au centre, éclairée, avec une sortie »**, avec la fiche photo de
`T04_01_rocade_sud_echirolles`
- *Lecture* : T04, d'après les indices « rocade » et le nom d'agglomération. La fiche photo fixe ce qu'elle a lu.
  Imaginer, pas reconstruire : aucune géométrie OSM (C-29).
- *Scène attendue* :
  - **Profil** :
    - voies de 3,15 à 3,50 m (loi conditionnelle à 70 km/h, médiane 3,35 ; C-25) ;
    - GBA double face sans TPC (1,9 à 2,0 m observés entre lignes de rive) ;
    - BAU de 0,8 à 3,3 m (mode 2,3).
  - **Équipements** :
    - candélabres au TPC ou en rive (dits) ;
    - portique dans 43 % des variantes ;
    - zébras de musoir ;
    - écrans dans les variantes « urbain dense » (rocade, lot 19).
  - **Sortie** : déboîtement réduit de 110 m, admis en VSA (RC-VSA-009).
  - **Relief** : tranchée en déblai soutenu, murs (lot 20 : relief de T04).
  - **Usure** : pontages de fissures.
- *Fabricable* :
  - aujourd'hui : profil et sortie (A1, A4) ;
  - après BK-02 : éclairage ;
  - après BK-03 : usure ;
  - après BK-32 : portiques ;
  - après BK-18 et BK-21 : tranchée ;
  - après BK-35 : écrans ;
  - après BK-36 : vue de nuit.
- *Contrôles* : C-20, C-25, C-29 ; planche rendu | photo (§ 3.11).

**I08 — « une autoroute 2×3 qui arrive sur une barrière de péage »**
- *Lecture* : T01 (2 × 3, comme A2) + T03.
- *Scène attendue* :
  - **Plaza** : largeur de 41 à 179 m (mode 108,5 m), environ 14 voies de péage pour une 2 × 3 (loi à reprendre,
    § 3.5).
  - **Îlots-cabines** de 30 à 45 m (RC-AUT-033), sous un auvent.
  - **Dalle béton** au droit des cabines.
  - **Évasement** d'environ 150 m : un seul site (n = 1), donc mise en scène déclarée.
  - **Éclairage** (C-20).
  - **Signalisation** : D47 à 2 000 et 800 m, C64 sur l'auvent (RC-SD-019 à -021, L6, BK-32).
  - **ITPC** de part et d'autre (RC-AUT-016).
- *Fabricable* : aujourd'hui la section 2 × 3 ; la plaza après BK-29.
- *Contrôles* : C-20 ; trajectoires d'éventail et de rabattement (§ 5).

**I09 — « un carrefour à feux en ville entre une avenue 2×2 et une rue, avec des tourne-à-gauche protégés et des passages
piétons »**
- *Lecture* : gabarit du carrefour complexe (J5) : « protégés » veut dire phase spéciale des TAG. Le guidage T'2 0,10
  est donc **dit** par la scène, dans le cas que l'IISR prévoit (ARB-08, portée de l'art. 117-1).
- *Scène attendue* :
  - **Géométrie** : TPC et îlots de TAG de 3,50 m de part et d'autre, voies de TAG face à face (correction de l'étape 2).
  - **Feux** : 4 phases, dont la phase spéciale ; R11 sur les îlots (L6).
  - **Piétons et cycles** : refuges ≥ 2,00 m (DEF-022), traversées ≤ 12 m hors refuge, sas vélo si des bandes
    cyclables sont tirées.
  - **Balayages** : VL sur tous les mouvements, bus sur les mouvements de l'artère.
- *Fabricable* : **aujourd'hui** (famille J5). C'est la scène de démonstration du § 5.
- *Contrôles* : C-23 complet (§ 5.8).

**I10 — « une zone 30 résidentielle avec un mini-giratoire et des coussins berlinois »**
- *Lecture* : T11 + G3.
- *Scène attendue* :
  - **Chaussée** de 3,9 à 7,1 m (mode 5,25), sans axe, avec double sens cyclable (fixé par la règle RF-MA-ZCA-001, qui
    passe avant la loi observée).
  - **Stationnement** marqué dans 50 % des variantes.
  - **Mini-giratoire** de 20 m de diamètre, îlot franchissable (G3, RF-GV-GIR-016).
  - **Coussins** de 1,75 à 1,90 × 3 à 4 m (RF-GV-RAL-001).
  - **Entrée de zone** : B30 (L6) et inscription ZONE 30 (BK-06, BK-09).
- *Fabricable* : aujourd'hui, la chaussée, le mini-giratoire et les coussins ; l'entrée de zone après BK-09.
- *Contrôles* :
  - C-19, C-28 ;
  - mini-giratoire : le VL contourne l'îlot, le bus et le porteur le franchissent (§ 5.3) ;
  - les roues du bus enjambent le coussin : voie du bus > largeur du coussin + 2 × 0,10 m [G].

**I00 — test de refus : « une autoroute avec un passage piéton et des places de stationnement »**
- *Attendu* : refus motivé par C-01. Le rapport propose une correction : passerelle (OA-02) ou aire de repos (BK-37).
  Aucune description n'est écrite.

### 3.15 Critères de réception du mode (porte de BK-01)

| Critère | Seuil |
|---|---|
| I01 à I10 : description écrite et compilée sans erreur, sur la part fabricable | 100 % |
| I00 : refus motivé, citant C-01 | oui |
| Déterminisme : deux exécutions donnent les mêmes octets (description, rapport, complément L6) | 100 % |
| 12 typologies × 50 variantes : compilation sans erreur | 100 % |
| Fidélité des fréquences (présences p ≥ 0,4) | \|f − p\| ≤ 0,15 |
| Valeurs numériques dans [min ; max] de leur loi | 100 % |
| Provenance de chaque valeur (§ 3.4) | 100 % ; 0 valeur muette |
| Mode `neuve` : valeurs hors bornes de règle | 0 |
| Mode `existante` : écarts déclarés (admis ou non contrôlés) | 100 % |
| `non_fabrique` : chaque élément renvoie à un BK | 100 % |
| C-17 : paires contradictoires | 0 |

## 4. Lots

### 4.0 Préalables

- **P-1. Livraison et fusion du workflow parallèle.** Les lots ouvrages et L6 sont branchés dans
  `fabriquer_generateur.py --complet` par l'agent d'intégration. Leurs rapports sont lus, leurs rendus regardés.
- **P-2. Versement des règles.** RC-* (lot 18), RI-* (lot 19), OBS20-* (lot 20) et CAND-E4-* (inventaire) vont dans
  `regles_route_fr.json`, versés par son propriétaire (`fusionner_regles.py`). On garde les natures : règle,
  observation, choix [G]. En attendant, le mode imagination lit les fichiers de DocRoute en lecture seule, avec la
  provenance du dossier.
- **P-3. Arbitrages de règles à trancher** (relecture sur tuiles natives) :
  - surlargeur en courbe : 50/R (RF-GV-RAY-012) contre 25/R et 30/R (RI-TRA-007) ;
  - BAU : 3,00 m (RF-OSM-LAR-014), contre 2,50 m, ou 3,00 m si plus de 2 000 PL par jour (RC-AUT-013), contre 2,5 à 3,0 m
    observés (OBS20-T01-LARGEUR_BAU) ;
  - pages de la VSA 90/110 : page PDF = page imprimée + 2. Les scènes A3 et A4 citent les pages imprimées, le lot 19 les
    pages PDF ;
  - largeur de passage d'une chicane : CERTU PAS VII06, à verser ;
  - rampes des routes ordinaires (I05) : ARP, à verser.
- **P-4. Décisions de l'utilisateur** (§ 6).

### 4.1 Lot 4.1 — Imaginer avec ce qu'on sait fabriquer

- **Objectif** : dès ce lot, « imaginer » des routes françaises plausibles à partir de phrases et de typologies, pour
  tout ce que la chaîne fabrique déjà. On y ajoute les équipements les plus visibles, qui ne demandent pas de relief.
- **Contenu** : BK-01, BK-02, BK-03, BK-04 (avec L6), BK-05, BK-06, BK-07, BK-08, BK-09.
- **Jalons montrables** :
  1. **Imagination sur l'existant** : I01, I03, I09 et I10, plus 4 variantes de T07 et de T10.
  2. **Équipements** : éclairage, mobilier, marquages dormants, balises, sur S03, S06, G1, I01 et I10.
  3. **Usure et séquences** : usure ; traverse avec chicane (I02) ; créneau à plat (I05).
- **Rendus** :
  - pour chaque scène : dessus, oblique 3/4, conducteur, planche de 1 092 px au plus, tuiles natives ;
  - un **nuancier d'imagination** : planches 2 × 2 de 4 variantes d'une même phrase ;
  - planches rendu | photo de référence (locales).
- **Porte de fin** :
  - critères du § 3.15 ;
  - critères de BK-02 à BK-09 ;
  - 7 typologies fabricables à plat, hors végétation et bâti : T05, T06, T07, T09, T10, T11, et T04 en section courante ;
  - non-régression à l'octet de S01 à S12, J1 à J6, G1 à G4, A1 à A4, D1 à D4 et E01.
- **Effort cumulé** : environ L + 5 M + 3 S, en deux fils parallèles (Python d'imagination ; HDA d'équipements).
- **Risque principal** : P-1 non livré. Parade : BK-01 peut commencer sur S, J, G et A seulement.

### 4.2 Lot 4.2 — Zone de conflit, trajectoires et graphe partout (ADAS)

- **Objectif** : clore la demande de l'utilisateur du 18/10 (§ 5) et donner à toute scène, réelle ou imaginée, un graphe
  de voies exploitable par la simulation.
- **Contenu** : BK-10, BK-11, BK-12, BK-13, BK-14, BK-15, BK-16.
- **Jalons montrables** :
  1. **Silhouettes et écarts ouverts** : silhouettes sur J5 et J6 ; écarts CE fermés.
  2. **Giratoires et bretelles balayés** : G1 à G4, A3, A4, I10.
  3. **Graphe et exports** : graphe sur toutes les scènes ; OpenDRIVE relu ; ZoneGraph et feux animés dans UE.
  4. **Branches courbes** : J7 en Y, J8.
- **Rendus** :
  - planches « trajectoires » de dessus (§ 5.6) ;
  - vues conducteur avec silhouettes ;
  - tracé de l'OpenDRIVE relu ;
  - capture UE si le projet est disponible.
- **Porte de fin** : critères du § 5.8 et de BK-10 à BK-16.
- **Effort cumulé** : environ 2 L + 4 M + S.

### 4.3 Lot 4.3 — Relief et abords

- **Objectif** : la troisième dimension. La route ne flotte plus : profil en long, terrain, talus, murs, retenue posée
  par règle, et première route de montagne.
- **Contenu** : BK-17, BK-18, BK-19, BK-20, BK-21, BK-22, BK-23, BK-24.
- **Jalons montrables** :
  1. **Profil en long et terrain** : S01 en rampe, A1 en remblai, J2 avec palier.
  2. **Talus, fossés, retenue** : A1 en remblai de 4 m avec glissière, D1 avec piles protégées.
  3. **Murs et dévers** : VRU en tranchée, I07.
  4. **Montagne** : I04 complète.
- **Rendus** : obliques et vues conducteur ; vue latérale en coupe pour le profil en long.
- **Porte de fin** :
  - critères de BK-17 à BK-24 ;
  - T08 fabricable ;
  - T01, T04 et T05 complètes, hors équipements du lot 4.5 ;
  - D1 à D4 identiques à l'octet.
- **Effort cumulé** : environ 4 L + 4 M. C'est le plus gros lot. Il se scinde naturellement en 4.3a (BK-17 à BK-20) et
  4.3b (BK-21 à BK-24).

### 4.4 Lot 4.4 — Réseau continu et échangeurs

- **Objectif** : enchaîner plusieurs carrefours sur une même route et fabriquer les échangeurs.
- **Contenu** : BK-25, BK-26, BK-27, BK-28, BK-29, BK-30.
- **Jalons montrables** :
  1. **Réseau continu** : avenue entre un carrefour à feux et un giratoire ; quartier imaginé.
  2. **Losange** : I06 complète.
  3. **Trèfle partiel et entrecroisement** : sur T04.
  4. **Trompette et péage** : I08.
- **Rendus** :
  - losange de dessus et en oblique ;
  - conducteur sur la bretelle ;
  - planche des trajectoires du losange ;
  - plaza de péage.
- **Porte de fin** : critères de BK-25 à BK-30 ; T02 et T03 fabricables ; les 12 typologies fabricables hors végétation et
  bâti.
- **Effort cumulé** : environ 2 XL + 3 L + M.

### 4.5 Lot 4.5 — Équipements, ouvrages complémentaires et conditions ADAS

- **Contenu** : BK-31 à BK-38.
- **Jalons montrables** :
  1. **Rocade complète de nuit** : I07 avec écrans, portiques et éclairage.
  2. **Chantier** : basculement sur une 2 × 2.
  3. **Tunnels** : I04 avec deux tunnels.
  4. **Aire de repos**.
- **Porte de fin** : critères de BK-31 à BK-38.
- **Effort cumulé** : environ 3 L + 4 M + S.

### 4.6 Synthèse

| Lot | Contenu | Démonstration phare | Effort (échelle de l'inventaire) | Typologies fabricables à la fin |
|---|---|---|---|---|
| 4.1 | imagination, éclairage, usure, balises, mobilier, marquages, créneau, traverse, zone 30 | 10 phrases → 10 scènes ; nuancier de variantes | L + 5 M + 3 S | T04 (section), T05, T06, T07, T09, T10, T11 (à plat) |
| 4.2 | graphe, trajectoires, silhouettes, écarts, branches courbes, OpenDRIVE, ZoneGraph | J5 / G2 / A3 avec silhouettes ; OpenDRIVE relu | 2 L + 4 M + S | idem, avec graphe et trajectoires |
| 4.3 | profil en long, terrain, talus, dévers, murs, retenue, montagne, assainissement | col en lacets ; autoroute en remblai | 4 L + 4 M | + T08 ; T01, T04, T05 avec relief |
| 4.4 | réseau continu, losange, trèfle partiel, trompette, entrecroisement, péage, demi-carrefour | voie express + pont + losange ; péage | 2 XL + 3 L + M | + T02, T03 : les 12 |
| 4.5 | équipements d'autoroute, portiques et PMV, chantier, tunnel, écrans, nuit et pluie, aires, Dv et E60 | rocade de nuit ; chantier ; tunnels | 3 L + 4 M + S | les 12, équipées |

Les efforts suivent l'échelle de l'inventaire (S ≤ 2 j, M de 3 à 7 j, L de 2 à 4 semaines, XL plus d'un mois). Ce sont
des ordres de grandeur pour un seul fil de travail. Les étapes 1 à 3 ont avancé plus vite avec des workflows parallèles,
mais chaque workflow consomme beaucoup de jetons (§ 6, décision 6).

### 4.7 Progression des typologies

Légende : ✗ = non fabricable ; ◐ = en partie ; ● = fabricable, hors végétation et bâti ; « ● + » = enrichie par le lot.

| Typologie | Aujourd'hui | Après 4.1 | Après 4.2 | Après 4.3 | Après 4.4 | Après 4.5 |
|---|---|---|---|---|---|---|
| T01 Autoroute | ◐ | ◐ | ◐ (graphe) | ● (talus, retenue) | ● | ● + (clôture, PR, PAU) |
| T02 Échangeur | ✗ | ✗ | ✗ | ✗ | ● | ● + (portiques) |
| T03 Péage | ✗ | ✗ | ✗ | ✗ | ● | ● |
| T04 VRU | ◐ | ● section à plat | ● | ● + (tranchée, murs) | ● + (entrecroisement, trèfle) | ● + (écrans, nuit) |
| T05 Voie express | ◐ | ● à plat | ● | ● + (relief) | ● + (losange) | ● |
| T06 Créneau | ✗ | ● à plat | ● | ● + (rampe) | ● | ● |
| T07 Campagne étroite | ◐ | ● (sans haies) | ● | ● + (fossés, relief) | ● | ● |
| T08 Montagne | ✗ | ✗ | ✗ | ● | ● | ● + (tunnels) |
| T09 Traverse | ◐ | ● | ● | ● | ● | ● |
| T10 Centre-ville | ◐ | ● (sans façades) | ● | ● + (avaloirs) | ● | ● |
| T11 Zone 30 / rencontre | ◐ | ● | ● | ● | ● | ● |
| T12 Ponts | en cours ailleurs | ● (après P-1) | ● | ● + (cours d'eau) | ● | ● + (tunnels) |

## 5. Zone de conflit et trajectoires : intégration au chapitre demandé par l'utilisateur

### 5.1 La demande et l'état

Le 18/10, l'utilisateur a fixé sa priorité : le centre des carrefours, c'est-à-dire la zone de conflit avec un couloir
central guidé en tirets, et des trajectoires de véhicules qui passent correctement dessus, avec balayages et
silhouettes.

**Ce qui est fait.** Le lot L4 et la correction de l'étape 2 couvrent les **carrefours plans** :
- trajectoires droite – arc – droite sur les axes de voie (RF-GV-TRJ-006) ;
- conflits de croisement, de convergence et de divergence, avec la phase ;
- zone de conflit délimitée par la frontière et les approches (RF-GV-TRJ-001, RF-MQ-CAR-04) ;
- guidage T'2 0,10 m seulement dans le cas de l'art. 117-1 (ARB-08), avec une garde caisse / peinture de 0,725 m ;
- TAG face à face dans J5 et J6, 4 phases ;
- balayages du VL et du bus calculés sur les trajectoires **finales**, jusqu'au point fixe (« une seule source ») ;
- 0 ligne longitudinale dans la zone hors guidage ;
- traversées ≤ 12 m hors refuge.

**Ce qui manque** :
- les écarts mesurés et non atteints (BK-13) ;
- les giratoires et les bretelles, non balayés (BK-11) ;
- le graphe hors carrefours plans (BK-10) ;
- les branches courbes (BK-14) ;
- la **visualisation par silhouettes** (BK-12) ;
- l'export vers la simulation (BK-15, BK-16).

### 5.2 Principe : une seule source de trajectoires, pour toutes les familles

Toute connexion de voies est une `trajectoire` au contrat du schéma (de / vers, mouvement, rayon, usagers, phases).
C'est le cas dans un carrefour plan, un giratoire, une divergence ou une convergence d'échangeur, un rabattement, un
alternat, un péage ou l'accès à une aire. La règle de la correction de l'étape 2 s'étend à toutes les familles, et le
même objet sert à quatre usages :
- les **balayages** (lot L3a, au point fixe) ;
- les **conflits**, typés croisement, convergence, divergence ou **face-à-face** pour l'alternat ;
- la **zone de conflit** ;
- le **graphe**, puis OpenDRIVE et ZoneGraph.

Il n'y a jamais deux constructions concurrentes : le défaut corrigé à l'étape 2 sur J1 à J6, où les lots L3 et L4
n'utilisaient pas les mêmes trajectoires, ne doit pas réapparaître.

### 5.3 Par famille

Abréviation du tableau : semi = semi-remorque.

| Famille | Trajectoires | Zone de conflit | Véhicules (§ 5.4) | Contrôles | Règles | État → BK |
|---|---|---|---|---|---|---|
| Carrefour plan (J1 à J6, I09) | droite – arc – droite ; TAD concentrique au coin ; TAG le plus grand, ou guidé | frontières + approches | VL ; bus sur les mouvements dits ; semi hors agglomération | nez + 0,30 m ; îlots du cœur ; TAG guidés disjoints, garde 0,725 m ; 0 ligne hors guidage ; traversée ≤ 12 m ; zone ≤ 40 m (avertissement) | RF-GV-TRJ-006, RF-GV-TRJ-001, RF-MQ-CAR-02, RF-MQ-CAR-04, RF-GV-PIE-010, ARB-08 | fait ; écarts : BK-13 ; branches courbes : BK-14 |
| Giratoire (G1, G2, G4) | entrée – anneau – sortie, raccords Re et Rs | anneau découpé par branche ; convergences aux entrées | VL, bus, semi | déflexion ≤ 100 m ; 4 convergences VL / VL ; couronne franchissable réservée au bus et au semi | RF-GV-GIR-008, DEF-024, RF-GV-TRJ-001 | calculées, non balayées : BK-11 |
| Mini-giratoire (G3, I10) | le VL contourne l'îlot ; le bus et le porteur le franchissent | idem | VL, bus, porteur | le VL ne monte pas sur l'îlot | RF-GV-GIR-016 | BK-11 |
| Entrée d'autoroute (A3) | voie d'insertion → voie de droite ; convergence entre E.1,00 et la fin du biseau | bande d'insertion (200 m + 75 m) | VL, semi | La ; obliquité ; ni ouvrage ni rabattement dans la zone (C-06) | RC-ECH-015, RC-ECH-026, RC-ECH-032, RI-ECH-011 | BK-11 |
| Sortie d'autoroute (A4) | voie de droite → voie de décélération ; divergence de S.1,50 à S.5,00 | zone de divergence | VL, semi | Ld ; obliquité ; J14a ≥ 0,70 m | RC-ECH-014, RC-ECH-025, RC-ECH-028, RC-ECH-029 | BK-11 |
| Entrecroisement, collectrice | changements de voie répartis dans Z | bande Z | VL, semi | Z dans la plage | RC-ECH-042, RC-VSA-011 | BK-28 |
| Créneau, rabattement (I05) | voie supprimée → voie maintenue, sur Li | Li + tampon de 88 m | VL, semi | aucun accès dans la zone | RC-ARP-004, RC-ARP-006 | BK-07 |
| Chicane, écluse (I02) | **alternat** : les deux sens partagent la voie libre | zone d'alternat (face-à-face) | VL, bus, porteur, autocar | balayages dans la voie libre ; priorité B15 / C18 ; visibilité de part et d'autre | RF-SV-B15.C18, RF-MQ-ALT-01 | BK-08 |
| Diffuseur (I06) | bretelles + carrefours de raccordement | union des zones ci-dessus | VL, semi | lignes précédentes ; C-03, C-07 | RC-ECH-*, RI-ECH-* | BK-26, BK-27 |
| Péage (I08) | éventail : divergence vers N couloirs, puis convergence | évasement et rabattement | VL, semi | largeur de couloir [G] ; longueurs | RC-AUT-033 | BK-29 |
| Chantier | basculement : déport de voie, parfois sur la BAU | zone de basculement | VL, semi | balayage dans le gabarit balisé | RF-MQ-TMP-01 | BK-33 |
| Piétons et cycles | traversées, figurines, doubles chevrons | conflits véhicule / piéton et véhicule / vélo | piéton, vélo | 8 conflits VL / piétons au giratoire ; continuité des traversées | RF-GV-TRJ-001, RF-MQ-CYC-03 | graphe piéton : BK-10 ; marquages : BK-06 |

### 5.4 Véhicules de projet par contexte (ARB-I-07, proposé)

| Contexte | Véhicules balayés | Source |
|---|---|---|
| Agglomération, sans ligne de TC | `vl`, `pl_porteur` (livraison, collecte) | `vehicules_projet.json` (rôles : VU p. 144) |
| Agglomération, ligne de TC dite ou tirée | + `bus_standard_12m` sur les mouvements de la ligne ; `bus_articule_18m` si la ligne est « forte » | clé `vehicule` existante (FORMAT § 15.3) |
| Périurbain et rase campagne | `vl`, `semi_remorque` | véhicule de vérification interurbain (ACI, N05) |
| Montagne, route touristique | + `autocar_15m`, sauf « interdite aux cars » | RI-TRA-006 |
| Autoroute, bretelles, péage | `vl`, `semi_remorque` | — |

Dans le mode imagination, le contexte tiré écrit la clé `vehicule` de la description. Les balayages n'en dépendent pas
autrement : on garde « une seule source ».

### 5.5 Dans le mode imagination

- **C-23 est bloquante.** Une scène imaginée dont un balayage touche un nez ou un îlot n'est pas livrée. Le module essaie
  d'abord, dans cet ordre :
  1. un autre tirage de la géométrie libre : rayon de coin, recul du nez dans sa plage ;
  2. un passage plus en retrait ;
  3. sinon, un refus motivé.
  
  Il ne baisse jamais un seuil.
- **Guidage.** Il est écrit seulement dans les cas de l'art. 117-1 (ARB-08) :
  - quand la phrase demande des TAG protégés, ou une phase spéciale ;
  - ou, avec l'option `--style-local grenoble`, selon la pratique observée sur les axes de Meylan (RF-OBS-FEU-02 ; tirets
    courts, réservés à ce style).
  
  Il n'est jamais tiré au hasard ailleurs.
- **Zones de conflit compactes** (RF-GV-TRJ-001). Parmi les variantes admissibles, le module garde celles dont la plus
  longue trajectoire dans la zone fait 40 m ou moins. Au-delà, la variante reste admise avec un avertissement
  (RF-GV-PIE-010).

### 5.6 Visualisation (BK-12)

- **Planche de dessus** de 1 092 px, par carrefour, giratoire ou zone d'échangeur :
  - voies et connecteurs (graphe) ;
  - balayages, un aplat semi-transparent par véhicule ;
  - silhouettes à l'entrée, au milieu, au plus grand déport et à la sortie ;
  - zone de conflit hachurée ;
  - points de conflit numérotés, avec leur type ;
  - guidage en tirets ;
  - légende des véhicules et des phases.
  
  Une planche par phase pour les carrefours à feux.
- **Vue conducteur**, à 1,20 m sur chaque approche, avec les silhouettes des mouvements de la même phase.
- **Oblique 3/4** avec silhouettes, pour montrer les nez dégagés.
- **Tableau** joint à chaque planche : mouvement, véhicule, rayon, marge minimale aux nez, conflits.
- Chaque planche passe `decoupe.py verifier` et est regardée en tuiles natives avant toute conclusion (consigne du dépôt).

### 5.7 Graphe, OpenDRIVE, ZoneGraph

| Objet du modèle | OpenDRIVE | ZoneGraph (UE) |
|---|---|---|
| voie de section (bande `driving`, `x-opendrive.lane_type`) | `lane` d'une `road` | lane |
| trajectoire (connecteur) | `connection` + connecting road d'une `junction` | lane link |
| zone de conflit | `junction` | — (zones d'intersection) |
| contrôleur, phases | `controller`, `signal` | état des feux (BK-16) |
| profil en long, dévers (lot 4.3) | `elevationProfile`, `lateralProfile/superelevation` | Z des lanes |
| ouvrage (couches) | routes superposées sans `junction` | lanes superposées |

### 5.8 Critères mesurables du chapitre (porte du lot 4.2, puis de toute scène imaginée)

| N° | Critère | Seuil | Scènes |
|---|---|---|---|
| 1 | Toute voie entrante a au moins une trajectoire ; toute trajectoire a au moins un véhicule de projet | 100 % | toutes |
| 2 | Balayages : marge aux nez et aux îlots pour les véhicules qui desservent le mouvement | ≥ 0,30 m (0 contact) | J*, G*, A3, A4, I02, I04, I06, I09, I10 |
| 3 | Bordure franchie seulement aux abaissés, à la couronne franchissable (bus, semi) ou à l'îlot de mini-giratoire (bus, porteur) | 0 exception | idem |
| 4 | TAG guidés d'une même phase : recouvrement des balayages ; garde caisse / peinture | 0 m² ; ≥ 0,725 m | J5, J6, I09 |
| 5 | Lignes longitudinales dans la zone de conflit hors guidage | 0 | carrefours plans |
| 6 | Traversée hors refuge ; plus longue trajectoire dans la zone | ≤ 12 m (bloquant) ; ≤ 40 m (avertissement) | carrefours à feux |
| 7 | Conflits : décompte géométrique = décompte topologique, avec les phases (corrige CE-L4-16) | 0 écart | J1 à J6 |
| 8 | Giratoire : déflexion sur chaque entrée ; convergences VL / VL d'un giratoire à 4 branches | ≤ 100 m ; 4 | G1 à G4 |
| 9 | Bretelles : Ld et La ≥ formules ; obliquités dans la plage ; convergence et divergence dans leur zone | 100 % | A3, A4, I06 |
| 10 | Graphe : successeurs et prédécesseurs ; continuité des axes ; étiquettes | 100 % ; ≤ 1 cm et ≤ 1° ; ≤ 32 | toutes |
| 11 | Silhouettes contenues dans leur balayage | 100 % | planches |
| 12 | OpenDRIVE relu : axes ; jonctions = zones ; liens = connecteurs | ≤ 2 cm ; 100 % | J1, J3, G1, A3, I05 |

### 5.9 Où cela tombe dans les lots

| Lot | Apport au chapitre |
|---|---|
| 4.1 | C-23 dans le mode imagination ; I09 et I10 contrôlés ; alternat de chicane (I02) ; rabattement du créneau (I05) |
| 4.2 | le cœur du chapitre : BK-10 à BK-16 |
| 4.3 | trajectoires en 3D sur profil en long et dévers ; autocar dans les épingles (I04) |
| 4.4 | losange, trèfle partiel, entrecroisement, péage : zones et balayages ; plusieurs carrefours par route |
| 4.5 | basculement de chantier ; feux et silhouettes de nuit (BK-36) |

## 6. Décisions à prendre par l'utilisateur

1. **Végétation et bâti.** Ils sont reportés depuis le 17/10. Or 5 typologies sur 12 ont un élément végétal ou bâti
   parmi leurs traits observés : haies (T07, 0,50), vitrines et arbres (T10), plantations (T11), bâti de bourg (T09),
   abords boisés (T08). Sans eux, les scènes imaginées restent incomplètes. Proposition : un lot 4.6 « végétation et
   abords » après le lot 4.3, sur le terrain.
2. **Simulation.** Installer un validateur OpenDRIVE (esmini ou libOpenDRIVE) et, plus tard, CARLA, qui n'est pas
   installé (CHAINE E18) ? Ce sont des téléchargements de logiciels, à autoriser.
3. **Noms de lieux des scènes imaginées** : fictifs (défaut, ARB-I-06) ou communes réelles (COG de l'INSEE, Licence
   Ouverte) ?
4. **Mode de conformité par défaut** : `existante` (routes telles qu'observées, écarts déclarés) ou `neuve` ?
5. **Police des panneaux** : la norme NF P 98-532 (alphabets L1 et L4) est payante. À défaut, on garde la police
   Bahnschrift [G] du lot L6.
6. **Budget.** Les cinq lots représentent environ cinq workflows lourds en jetons, et la limite de dépense a déjà été
   atteinte une fois. Faut-il les lancer un par un, avec une démonstration à chaque jalon ?
7. **Style local.** Les pratiques de la métropole grenobloise (damier cyclable, Chronovélo, îlots ocre) doivent-elles
   être tirées par défaut dans les scènes « en Isère », ou seulement avec `--style-local` ?

## 7. Risques et parades

| Risque | Parade |
|---|---|
| Retard ou changement de périmètre du workflow parallèle | P-1 explicite ; BK-01 peut démarrer sur les scènes S, J, G et A ; coordination par extension, jamais par réécriture |
| Lois du lot 20 tirées de petits échantillons (6 à 8 sites) | n ≥ 3 ; tirage dans `part_des_sites` ; sites-modèles ; bornes des règles ; calibration (§ 3.12) |
| Imaginer finit par recopier un site réel | site-modèle réduit à des attributs, sans géométrie ni nom ; C-29 ; nombres perturbés dans leur incertitude |
| Explosion du nombre de contrôles et du temps de calcul (une passe de J6 dure 10 min) | dichotomie (BK-13) ; contrôles par famille ; cache des balayages par empreinte |
| Régression des scènes existantes | nouvelles versions d'HDA à côté des anciennes ; empreintes sha256 à chaque lot |
| Règles contradictoires entre volets | P-3 ; arbitrages déclarés au même format que les ARB-* de la base |
| Droits | photos de tiers jamais diffusées ; faces de panneaux sous licence non levée, PNG non diffusés ; textes de DocRoute paraphrasés |
| Unreal indisponible pour BK-16 | ZoneGraph contrôlé hors UE (graphe relu) ; capture dès que le projet `D:\ClaudeADAS` est ouvert |

## 8. Limites de ce plan

- Les efforts et les poids des bonus sont des estimations [G]. Les scores viennent de l'inventaire, lui-même fondé
  sur des fréquences estimées, en partie remplacées par celles du lot 20.
- L'état du workflow parallèle est celui lu le 22/10/2026 vers 18 h 30. Son périmètre final peut différer : à relire
  avant le lot 4.1 (P-1).
- Seul l'exemple I03 a été compilé, à blanc et en mémoire. Les autres phrases décrivent ce que les scènes **doivent**
  contenir ; elles n'ont pas été produites, puisque le module n'existe pas encore.
- Les règles des lots 18 à 20 ne sont pas encore versées dans la base (P-2). Leurs identifiants ont été vérifiés dans
  leurs fichiers d'origine.
- Aucune photo n'a été ouverte pour ce plan. Les valeurs observées viennent des fichiers du lot 20.

## 9. Fichiers

- `recon/generateur/PLAN_ETAPE4.md` : ce document.
- `D:\DocRoute\INDEX_DOCUMENTATION.md` : sections 18, 19 et 20 ajoutées à la fin, sans modifier le reste.
- Aucun autre fichier n'a été écrit. Aucun fichier du workflow parallèle n'a été touché : `rg::ouvrages`,
  `rg::signalisation`, `description/`, `scenes_ouvrages/` et `scenes_signalisation/` ont seulement été lus.
