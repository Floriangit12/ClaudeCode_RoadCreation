# Description résolue du carrefour Paquet Jardin (état octobre 2026)

Base de description 0.3 + seulement les décisions prouvées de la fusion 0.3 et de la cohérence v3, arbitrées par la revue adverse v3 (et par la revue v2 pour les décisions qu'elle a relues et qui n'ont pas changé, RES-SRC-002). Une décision jugée « faux » n'est jamais appliquée ; deux retours à la source de la cohérence v3 jugés « faux » sont corrigés par la position que la revue prouve sur photos (RES-POS-007). Commande : `python recon/pcg/decrire/resoudre.py` (`--sans-planches`, `--sans-validation`, `--forcer`). Déterministe : deux exécutions donnent des fichiers identiques à l'octet. Ni `base/`, ni le paquet, ni `enrichi/`, ni `coherence/` ne sont modifiés.

## Utiliser la description résolue

- **Houdini** : dans `pj::lire_description`, régler le paramètre **Dossier de la description (`dossier`)** sur `<dépôt>/recon/out/paquet_jardin/v2/description/resolue/base` au lieu de `.../description/base` (dans la scène maîtresse : `PJ_DESCRIPTION=<dépôt>/recon/out/paquet_jardin/v2/description/resolue/base`). Le lecteur y trouve les cinq familles, `nivellement.json` et `nivellement_grille.npz`, et lit le manifeste `resolue/description_scene_v2.json` (dossier parent). Les marquages retirés portent `fabrication.statut = non_fabrique` : ils sont exclus par défaut (paramètre « Garder les marquages non fabriqués »).
- **Objets** (non lus par `pj::lire_description`) : `resolue/objets/mobilier.geojson` et `arbres.geojson` ont le schéma du paquet (`x_local`, `y_local`, `z_local`, `instancier`, `statut_2026`…) plus une propriété `resolution`. Pour les consommer, pointer la constante `OBJETS` de `recon/pcg/ue/vegetation/arbres.py` (et `PAQUET/donnees/objets` de `recon/pcg/ue/contexte/preparer_usd.py`) vers `resolue/objets` (modification à faire par leur propriétaire). Un objet porté (`porte_par`, `instancier_fut = false`) ne doit pas recevoir de fût propre. `vegetation_ajouts.geojson` (haies, massifs) et `ponctuels_sol_ajouts.geojson` (tampons, avaloirs) sont nouveaux.
- **Validation** : `python recon/pcg/decrire/valider.py recon/out/paquet_jardin/v2/description/resolue` : 0 erreur, 88 avertissements (identiques à ceux de la base). Entités remises à l'état de base par la garde de validation : aucune.
- **Empreintes** : hash_description 1bb443ecaf000e47cdb9e375b40d9cc89cd74812b74276b3b28eaf67634ad8ee (base : 7a869e6aa1656d45280500abb158036da103e3021ed5a74de5882c8ed221c584) ; hash_marquages 0cde1fdbcf2c65e00e7e159f8273954655cf156dd60efa6a28e1ccffc24efd99.
- **Chaîne** (RES-CHN-001) : cohérence v3 et fusion 0.3 ont lu la base courante.

## Comparaison avec la résolution précédente

Référence figée : `resolue/historique/journal_resolution_r1.json` (résolution r1 : cohérence v2, revue v2). Une modification est identifiée par (famille, entité, nature, attribut).

|  | résolution r1 | cette résolution |
|---|---|---|
| modifications appliquées | 279 | 279 |
| entités ou propositions non résolues | 304 | 302 |

Modifications : 269 inchangées, 7 modifiées, 3 nouvelles, 3 retirées (retours à la base). Non résolues : 20 sorties de la liste (résolues, confirmées ou devenues sans objet), 18 entrées.

Nouvelles :

| entité | nature | après | règles | motif |
|---|---|---|---|---|
| `MF-6020` | recalage_fleche | 0.255 m | MQ-FLE-006, RES-MQ-001, RES-SRC-001, RES-SRC-002 | flèche centrée dans sa voie (voie OpenDRIVE 2/-1 ; bornes réelles mesurées par la revue : ligne GAM (orange) à 1,20 m et ML-0785 à 1,61 m de la flèche : 0,21 m  |
| `MF-8000` | retrait | fabrication non_fabrique | RES-MQ-004, RES-SRC-001 | marque générée (regle:INF-FLE-004) contredite par la géométrie 2026 : bordure 2026 K-0415 dans la boîte de la flèche (marge 0.1 m) ; revue adverse v3 n° 39 et s |
| `ML-8000` | retrait | fabrication non_fabrique | RES-MQ-004, RES-SRC-001 | marque générée (regle:MQ-DET-002) contredite par la géométrie 2026 : trait dans la boîte de la flèche levée GAM 2026 MF-5527 ; revue adverse v3 n° 34 et seconde |

Modifiées :

| entité | nature | r1 | maintenant | motif |
|---|---|---|---|---|
| `arbre_027` | non_instancie_absent_2026 | instancier False ; statut « absent 2026 (photos calées 2026-07-28, revue + seconde lecture) » | instancier False ; statut « absent 2026 (photos calées 2026-07-28, revue de présence, revue adverse v3 et seconde lecture) » | absent sur les photos 2026 calées (revue de présence Q4 de la cohérence, jugée juste par la revue v3, seconde lecture) ; à intégrer comme constat ARB  |
| `arbre_028` | non_instancie_absent_2026 | instancier False ; statut « absent 2026 (photos calées 2026-07-28, revue + seconde lecture) » | instancier False ; statut « absent 2026 (photos calées 2026-07-28, revue de présence, revue adverse v3 et seconde lecture) » | absent sur les photos 2026 calées (revue de présence Q4 de la cohérence, jugée juste par la revue v3, seconde lecture) ; à intégrer comme constat ARB  |
| `feu_NE_TPC_t2` | reorientation_tete | azimut 297.5° | azimut 296.0° | azimut de saisie 315.0° remplacé par la cible fonctionnelle (extrémité opposée du passage MP-5170) |
| `feu_NE_TPC_t3` | reorientation_tete | azimut 150.0° | azimut 151.4° | azimut de saisie 135.0° remplacé par la cible fonctionnelle (extrémité opposée du passage MP-5191) |
| `feu_REV_droite` | deplacement | (-11.865 ; 8.956), 0.16 m | (-11.842 ; 8.959), 0.17 m | triangulation multi-vues (axe triangulé (4 vues, 82.9°)) de 0.17 m, en accord avec les photos (Q1), sous le seuil de double lecture |
| `lamp_9514828517` | deplacement | (13.250 ; -140.340), 0.70 m | (13.250 ; -140.340), 0.70 m | retour à la source de la cohérence v3 jugé faux par la revue v3 : position prouvée sur les photos calées pnx:f8d91bb1, pnx:ded07efa (fusion_recensemen |
| `pan_AB4_2` | deplacement | (32.220 ; -137.570), 0.92 m | (32.253 ; -137.709), 0.78 m | décision de la cohérence v3 jugée juste par la revue v3 (position relue à 0.000 m) |

Retirées (la base est rétablie ; raison actuelle) :

| entité | nature | r1 | raison |
|---|---|---|---|
| `MF-6017` | recalage_fleche | 0.188 m | non résolu (recalage_fleche, proposition_rejetee) : recalage non appliqué : bords non représentatifs : K-0626 absent en travers de la tête |
| `MF-6018` | recalage_fleche | 0.162 m | non résolu (recalage_fleche, incertain) : recalage non appliqué : bords non représentatifs : K-0381 absent en travers de la tête ; revue « incertain » : le bord K-0381 est un court tronçon de bordure  |
| `poteau_bois_REV_ilot` | deplacement | (-8.374 ; 13.116), 0.12 m | non résolu (position, incertain) : mesure de 0.12 m (axe triangulé (5 vues, 85.7°)) devenue indice par la cohérence v3 (Q1 : desaccord avec les photos décisives de la planche) et non relue par une rev |

## Décisions prises contre la cohérence v3

La cohérence v3 a ramené deux mâts à leur source et gardé deux marques générées que la revue adverse v3 met en cause ; chaque reprise s'appuie sur la preuve photo de la revue et sur ma seconde lecture des vignettes (P16).

| entité | décision | preuve (revue v3) | seconde lecture |
|---|---|---|---|
| `MF-8000` | retrait fabrication non_fabrique | revue_adverse_coherence_v3 n° 39 : faux — la flèche glissée de −11 m tombe dans un tronçon couvert par le levé GAM 2026 (lignes de voie à 1,4 m) sans aucune flèche ; ce levé contient la répétition MF-5525 dans la voie de gauche et | seconde_lecture_resolution : la flèche décrite (magenta) est posée sur l'ancienne flèche peinte de 2022 que la bordure K-0415 de 2026 (rouge) coupe en deux ; sur la carte des classes sa queue est dans l'espace vert ; la position g |
| `ML-8000` | retrait fabrication non_fabrique | revue_adverse_coherence_v3 n° 34 : juste — flèche GAM gardée à juste titre ; la « limite » qui coupe la boîte est ML-8000, ligne générée par MQ-DET-002 (« sans ligne de délimitation ») qui traverse en biais la voie de gauche alors | seconde_lecture_resolution : ML-8000 (vert fin) part du nez d'îlot et traverse en biais la flèche GAM MF-5527 de la voie de tourne-à-gauche puis court au milieu de cette voie, à ≈ 1,6 m de ML-5228 (GAM) et ≈ 1,7 m de ML-0408 : auc |
| `feu_NE_TPC` | deplacement (11.886 ; 8.849), 0.19 m | revue_adverse_coherence_v3 n° 41 : faux — e5d79de9 (5,9 m) : poteau à u ≈ 1505, T à 1500,8, A à 1471,6 (A contredit de 2°, rA = +3,0σ ; photo exclue par Q2) ; 5c0d1d39 (7,8 m) : poteau à u ≈ 782-784, T à 776,9, A à 759,4, où Q1 a  | seconde_lecture_resolution : e5d79de9 : le repère T (vert) est sur le fût du support et les modules, A (magenta) sur la haie à gauche, ≈ 30 px du fût ; 119d9094 : T sur le module du support, A dans le feuillage à gauche du fût : l |
| `lamp_9514828517` | deplacement (13.250 ; -140.340), 0.70 m | revue_adverse_coherence_v3 n° 40 : faux — f8d91bb1 (2026, 3,8 m) : mât « 0456 » portant B6a1 et C13a sur F à ≈ 5 px, A à 171 px (10,7°) ; photo source de la mesure écartée par le filtre « pied visible » ; ded07efa (7,4 m) : mât à  | seconde_lecture_resolution : f8d91bb1 : le repère F (jaune) touche le bord gauche du mât « 0456 » portant le disque B6a1 et le panonceau C13a, le repère A (magenta) tombe sur la palissade, 180 px plus à droite, sans aucun mât ; de |
| `pan_B6a1_1` | deplacement (13.250 ; -140.340), 0.68 m | revue_adverse_coherence_v3 n° 40 : faux — f8d91bb1 (2026, 3,8 m) : mât « 0456 » portant B6a1 et C13a sur F à ≈ 5 px, A à 171 px (10,7°) ; photo source de la mesure écartée par le filtre « pied visible » ; ded07efa (7,4 m) : mât à  | seconde_lecture_resolution : f8d91bb1 : le repère F (jaune) touche le bord gauche du mât « 0456 » portant le disque B6a1 et le panonceau C13a, le repère A (magenta) tombe sur la palissade, 180 px plus à droite, sans aucun mât ; de |
| `pan_C13a_1` | deplacement (13.250 ; -140.340), 0.68 m | revue_adverse_coherence_v3 n° 40 : faux — f8d91bb1 (2026, 3,8 m) : mât « 0456 » portant B6a1 et C13a sur F à ≈ 5 px, A à 171 px (10,7°) ; photo source de la mesure écartée par le filtre « pied visible » ; ded07efa (7,4 m) : mât à  | seconde_lecture_resolution : f8d91bb1 : le repère F (jaune) touche le bord gauche du mât « 0456 » portant le disque B6a1 et le panonceau C13a, le repère A (magenta) tombe sur la palissade, 180 px plus à droite, sans aucun mât ; de |

## Règles de résolution

- **RES-SRC-001** : Priorité des preuves : double lecture d'une revue > fusion stricte (FUS-COUV-02) > décision de cohérence jugée juste par la revue adverse > règle de conception appliquée à un objet déduit > base. Une décision qu'une revue juge « faux » n'est jamais appliquée.
- **RES-SRC-002** : Lien verdict-décision : un verdict de revue ne vaut que pour la décision qu'il a relue (position relue à ≤ 0,05 m, même azimut, même existence) ; la revue v3 juge les décisions de la cohérence v3, un verdict v2 ne vaut que si la décision v3 est restée celle que la revue v2 a relue ; un verdict « incertain » ou « faux » vaut toujours pour refuser.
- **RES-CHN-001** : Chaîne : enrichi/ et coherence/ doivent avoir lu la base courante (sha256 des fichiers de base) ; sinon la résolution s'arrête (option --forcer pour un essai).
- **RES-EXI-001** : Retrait ou absence 2026 prouvés strictement par la fusion (statut a_retirer / absent_2026, observation stricte) : marquage -> fabrication non_fabrique ; objet -> instancier false. Bordure : non appliqué (références de partition), listé pour le propriétaire de bordures.py.
- **RES-EXI-002** : Garde temporelle : une absence vue seulement avant la fin des travaux (05/12/2025) ne retire ni une entité posée ou refaite en 2025, ni une entité levée GAM 2026 : conflit listé.
- **RES-EXI-003** : Absence constatée sur photos 2026 calées (revue de présence Q4 de la cohérence ou revue adverse) et jugée « juste » par la revue adverse, avec une seconde lecture concordante (P16) : instancier false ; à intégrer comme constat de revue (FUS-ARB-01) par le propriétaire de la fusion. Une non-instanciation jugée « incertain » n'est pas appliquée (entité gardée, listée avec l'hypothèse de la revue).
- **RES-EXI-006** : Souche (R7) : un objet décrit comme souche et vu présent sur les photos 2026 n'est pas retiré par l'absence de l'arbre : la souche reste instanciée telle que la base ; « arbre absent, souche présente » est journalisé.
- **RES-EXI-004** : absent_2026_a_verifier (FUS-EXI-04) et non-instanciations de la cohérence jugées incertaines : entité gardée telle que la base, listée.
- **RES-EXI-005** : Absence ou retrait portés seulement par des projections photo à plus de 15 m de la caméra (FUS-VAL-02) : un trait fin peut y être invisible ; non appliqué, listé (cas MLY-MAR-017 de la critique de couverture).
- **RES-POS-001** : Mesure de position (fusion « appliquer » ou cohérence « mesure ») appliquée si la revue adverse la juge juste (RES-SRC-002) ; non revue : seulement une triangulation de déplacement ≤ 0,30 m (sous le seuil de double lecture P16) dont chaque mesure retenue est en accord avec les photos (Q1 « accord ») et sans drapeau sur la mesure retenue (un candidat écarté devenu indice ne bloque pas).
- **RES-POS-007** : Retour à la source jugé « faux » par la revue adverse, qui prouve la position mesurée sur des photos calées valides pour l'objet (postérieures aux travaux, ou antérieures pour un objet existant inchangé) avec une seconde lecture concordante (P16) : la position prouvée est appliquée au groupe de support (σ ≥ 0,30 m, confiance moyenne) ; si elle tombe sur une surface roulable, la surface est signalée. Une mesure devenue indice (Q1) sans revue n'est jamais appliquée ni reprise.
- **RES-POS-002** : Mesure pixel_ortho d'un objet haut (mât, poteau) : appliquée seulement si elle est corroborée (revue juste, départ d'ombre, triangulation) (Q7) ; une mesure rejetée par la cohérence pour sa date n'est pas appliquée.
- **RES-POS-003** : Revue « faux » : rien n'est appliqué. Revue « incertain » : seules les composantes que la revue déclare prouvées ou plausibles (ex. azimut) sont appliquées.
- **RES-POS-004** : Déplacement par la règle sans mesure : appliqué à un objet déduit ou en projet (règles dures pour les a priori, P7) dans le budget de sa source ; pour un objet existant, seulement si une revue l'a jugé juste ; sinon listé comme violation physique non tranchée (objet ou surface à vérifier).
- **RES-POS-005** : Groupe de support (membres_groupe) : une seule décision pour le mât ; fusion de supports prouvée (P5) : un seul fût instancié, l'autre objet est porté.
- **RES-POS-006** : Statut temporel : un objet existant déplacé de plus de 1 m par une mesure postérieure aux travaux passe en « déplacé lors des travaux 2025 » (Q8).
- **RES-ORI-001** : Réorientation appliquée si la revue la juge juste ou plausible, ou si l'azimut source est absent (complétion par la règle, confiance faible).
- **RES-ORI-002** : Tête de feu : réorientation par la règle fonctionnelle (FEU-05/06/07/09) appliquée si l'azimut source est une valeur de saisie (multiple de 45°) et l'écart ≤ 60° ; sinon gardée et listée.
- **RES-ATT-001** : Attribut : mise à jour de la fusion « appliquer » (FUS-ATT-06) si la confiance de la valeur est au moins moyenne, si l'attribut existe dans la famille et si la valeur est dans son domaine (enum du schéma 0.3, table des matériaux, types d'arbres du paquet) ; un azimut qui contredit de plus de 20° l'azimut résolu ou gardé par la cohérence est un conflit ; sinon listée.
- **RES-BOR-001** : Vue ou profil de bordure contestés (FUS-BOR-03) : jamais appliqués sans relevé ; listés avec la station.
- **RES-MQ-001** : Flèche recentrée (MQ-FLE-006) : flèche non levée GAM, non retirée, voie bornée par deux limites décrites (bordure ou ligne, pas OpenDRIVE seule) présentes en travers de la queue, du milieu et de la tête de la flèche (bords représentatifs), aucune bordure ni ligne ne coupe la boîte de la flèche (marge 0,10 m), empreinte recalée entièrement roulable (surfaces v2), revue ni « faux » ni « incertain » (Q5). Une revue « juste » qui mesure elle-même le centrage entre deux limites décrites remplace l'exigence de bornes décrites (cas d'une voie bornée par OpenDRIVE seule). Un glissement en s (INF-FLE-004) n'est jamais appliqué sans revue « juste ».
- **RES-MQ-004** : Marque générée par une règle (src regle:*, aucune observation) contredite par la géométrie 2026 de rang supérieur : flèche dont la boîte est coupée par une bordure 2026 décrite, ou trait qui traverse la boîte d'une flèche levée GAM 2026 (R6, règle < plan < ortho < GAM). Non fabriquée si la revue adverse la met en cause et qu'une seconde lecture concorde ; sinon conflit listé pour le propriétaire de marquages.py.
- **RES-MQ-002** : Marque au-delà de l'arête avant d'une bordure (MQ-DET-010, TQ-MQG-014) : la partie au-delà de l'intersection vérifiée avec la bordure devient une interruption (géométrie inchangée).
- **RES-MQ-003** : Ajout de marquage : trait isolé (LineString) observé en confiance ≥ moyenne, σ ≤ 0,10 m, source représentable dans src_marquage (gam, plan2025, ortho2022), sans doublon à 0,3 m ; sinon listé.
- **RES-ADD-001** : Ajout d'objet : instancier vrai dans la fusion (FUS-ADD-03), preuve stricte probante (après travaux, ou avant travaux hors emprise, ou dans l'emprise avec appui), confiance ≥ moyenne, σ ≤ seuil de la classe, type non ambigu (« _ou_ ») ; surfaces : jamais (partition de surfaces.py).
- **RES-ADD-002** : Tampons et avaloirs : écrits dans objets/ponctuels_sol_ajouts.geojson (identifiants TAM-/AVA- et ancrage du schéma) tant que la table des matériaux du schéma 0.3 n'a pas de fonte (materiau_id obligatoire de ponctuels_sol) ; à verser dans base/ponctuels_sol.geojson quand le propriétaire du schéma l'aura ajoutée.
- **RES-NRE-002** : Présence 2026 non testée : objet instancié à moins de 25 m d'une photo 2026 calée sans preuve stricte postérieure aux travaux ni revue de présence de la cohérence (Q4) ; listé pour un test de présence sur vignette. Revue de présence « non visible » (voitures) : listé pour le terrain.
- **RES-NRE-003** : Réserve ou observation d'une revue adverse sans décision prouvée (classe de surface erronée R8, orientation ambiguë, objet « conforme » invérifiable, structure non appariée R4) : rien n'est appliqué, l'entité est listée avec l'hypothèse de la revue et la station terrain.
- **RES-NRE-001** : Non résolu : toute entité en conflit ou incertaine reste telle que la base et est listée avec la station terrain la plus proche (PROTOCOLE_TERRAIN.md) ou une station à créer.

## Modifications appliquées

279 modifications appliquées ; 302 entités ou propositions non résolues ; 8 décisions de garder la base confirmées par une revue.

| famille | nature | n |
|---|---|---|
| arbres | ajouts | 19 |
| arbres | attributs mis à jour | 20 |
| arbres | déplacements | 6 |
| arbres | objets non instanciés (absents en 2026) | 5 |
| ilots | attributs mis à jour | 1 |
| marquages | ajouts | 10 |
| marquages | marques arrêtées à l'arête des bordures | 5 |
| marquages | attributs mis à jour | 15 |
| marquages | flèches recentrées dans leur voie | 3 |
| marquages | marquages retirés (non fabriqués) | 25 |
| mobilier | ajouts | 31 |
| mobilier | attributs mis à jour | 11 |
| mobilier | déplacements | 31 |
| mobilier | réorientations | 6 |
| mobilier | réorientations de têtes de feux | 10 |
| mobilier | supports fusionnés (un seul fût) | 1 |
| ponctuels_sol | ajouts | 45 |
| surfaces | attributs mis à jour | 29 |
| vegetation | ajouts | 6 |

Par classe d'objet :

| classe | nature | n |
|---|---|---|
| R11v_rep | réorientations de têtes de feux | 2 |
| R12 | réorientations de têtes de feux | 6 |
| R13c | réorientations de têtes de feux | 2 |
| abri_bus | déplacements | 1 |
| abri_technique | ajouts | 1 |
| acces_riverain | attributs mis à jour | 1 |
| arbre | déplacements | 6 |
| arbuste | ajouts | 8 |
| arbuste | attributs mis à jour | 1 |
| avaloir | ajouts | 9 |
| banc | ajouts | 4 |
| bloc_rocheux | ajouts | 17 |
| chaussee | attributs mis à jour | 6 |
| conifere | attributs mis à jour | 3 |
| conteneur_tri | ajouts | 1 |
| emprise_bordure | attributs mis à jour | 1 |
| espace_vert | attributs mis à jour | 8 |
| feuillu | ajouts | 11 |
| feuillu | attributs mis à jour | 16 |
| feuillu | objets non instanciés (absents en 2026) | 5 |
| fleche | attributs mis à jour | 2 |
| fleche | flèches recentrées dans leur voie | 3 |
| fleche | marquages retirés (non fabriqués) | 2 |
| haie | ajouts | 3 |
| ilot | attributs mis à jour | 1 |
| lampadaire | ajouts | 2 |
| lampadaire | attributs mis à jour | 6 |
| lampadaire | déplacements | 7 |
| ligne | ajouts | 10 |
| ligne | marques arrêtées à l'arête des bordures | 2 |
| ligne | attributs mis à jour | 8 |
| ligne | marquages retirés (non fabriqués) | 23 |
| massif | ajouts | 3 |
| mat_camera | déplacements | 1 |
| mat_camera | supports fusionnés (un seul fût) | 1 |
| panneau | ajouts | 4 |
| panneau | attributs mis à jour | 5 |
| panneau | déplacements | 11 |
| panneau | réorientations | 4 |
| panneau_information | ajouts | 1 |
| parking | attributs mis à jour | 8 |
| passage | attributs mis à jour | 1 |
| portail | ajouts | 1 |
| poteau_incendie | réorientations | 2 |
| poteau_reseau | déplacements | 1 |
| refuge | attributs mis à jour | 1 |
| support_feux | déplacements | 10 |
| symbole | attributs mis à jour | 4 |
| tampon | ajouts | 36 |
| transversale | marques arrêtées à l'arête des bordures | 3 |
| trottoir | attributs mis à jour | 4 |

### Déplacements et réorientations d'objets

| objet | classe | décision | d (m) / azimut | conf. | règles | revue | vs r1 |
|---|---|---|---|---|---|---|---|
| `arbre_013` | feuillu | non_instancie_absent_2026 |  | moyenne | FUS-COUV-02, FUS-DATE-01, FUS-EXI-01, FUS-STAT-01, RES-EXI-001 | revue_adverse_coherence_v3 n° 15 : juste | inchangee |
| `arbre_015` | feuillu | non_instancie_absent_2026 |  | moyenne | FUS-COUV-02, FUS-DATE-01, FUS-EXI-01, FUS-STAT-01, RES-EXI-001 | revue_adverse_coherence_v3 n° 16 : juste | inchangee |
| `arbre_027` | feuillu | non_instancie_absent_2026 |  | moyenne | RES-EXI-003, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 17 : juste | modifiee |
| `arbre_028` | feuillu | non_instancie_absent_2026 |  | moyenne | RES-EXI-003, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 18 : juste | modifiee |
| `arbre_167` | arbre | deplacement | 0.05 | faible | RES-POS-004 |  | inchangee |
| `arbre_175` | feuillu | non_instancie_absent_2026 |  | moyenne | FUS-COUV-02, FUS-EXI-01, FUS-EXI-03, FUS-STAT-01, RES-EXI-001 | revue_adverse_coherence_v3 n° 20 : juste | inchangee |
| `arbre_180` | arbre | deplacement | 0.05 | faible | RES-POS-004 |  | inchangee |
| `arbre_181` | arbre | deplacement | 0.30 | faible | RES-POS-004 |  | inchangee |
| `arbre_195` | arbre | deplacement | 0.20 | faible | RES-POS-004 |  | inchangee |
| `arbre_196` | arbre | deplacement | 0.40 | faible | RES-POS-004 |  | inchangee |
| `arbre_396` | arbre | deplacement | 1.60 | faible | RES-POS-004, RES-SRC-001 | revue_adverse_coherence_v1 : juste | inchangee |
| `abri_NO_0021` | abri_bus | deplacement | 0.85 | faible | RES-POS-004 |  | inchangee |
| `feu_NE_TPC` | support_feux | deplacement | 0.19 | moyenne | RES-POS-007, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 41 : faux | inchangee |
| `feu_NE_droite` | support_feux | deplacement | 0.36 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 13 : juste | inchangee |
| `feu_REV_E_pietons` | support_feux | deplacement | 0.07 | moyenne | RES-POS-001 |  | inchangee |
| `feu_REV_droite` | support_feux | deplacement | 0.17 | moyenne | RES-POS-001 |  | modifiee |
| `feu_SW_NO_pietons` | support_feux | deplacement | 0.35 | faible | RES-POS-004 |  | inchangee |
| `feu_SW_TPC` | support_feux | deplacement | 0.05 | faible | RES-POS-004 |  | inchangee |
| `feu_SW_cycles_NO` | support_feux | deplacement | 0.05 | faible | RES-POS-004 |  | inchangee |
| `feu_SW_cycles_SE` | support_feux | deplacement | 0.10 | faible | RES-POS-004 |  | inchangee |
| `feu_VERC_O_pietons` | support_feux | deplacement | 0.11 | faible | RES-POS-004 |  | inchangee |
| `feu_VERC_droite` | support_feux | deplacement | 0.26 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v2 n° 16 : juste | inchangee |
| `lamp_12668578865` | lampadaire | deplacement | 1.63 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 5 : juste | inchangee |
| `lamp_12668620636` | lampadaire | deplacement | 1.83 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 4 : juste | inchangee |
| `lamp_12894130974` | lampadaire | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v2 n° 17 : juste | inchangee |
| `lamp_9514795519` | lampadaire | deplacement | 1.20 | faible | RES-POS-004 |  | inchangee |
| `lamp_9514825221` | lampadaire | deplacement | 1.17 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 8 : juste | inchangee |
| `lamp_9514828517` | lampadaire | deplacement | 0.70 | moyenne | RES-POS-007, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 40 : faux | modifiee |
| `lamp_9665416817` | lampadaire | deplacement | 0.58 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 14 : juste | inchangee |
| `mat_camera_9831317323` | mat_camera | deplacement | 1.12 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 12 : juste | inchangee |
| `mat_camera_9831317323` | mat_camera | support_commun |  | moyenne | RES-POS-005 | revue_adverse_coherence_v3 n° 12 : juste | inchangee |
| `pan_AB3a_1` | panneau | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v2 n° 17 : juste | inchangee |
| `pan_AB3a_2` | panneau | reorientation | 342.0 -> 15.5 | faible | RES-ORI-001, RES-POS-003 | revue_adverse_coherence_v3 n° 3 : incertain | inchangee |
| `pan_AB3a_3` | panneau | deplacement | 4.15 | moyenne | RES-POS-001, RES-POS-006, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 2 : juste | inchangee |
| `pan_AB4_2` | panneau | deplacement | 0.78 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 7 : juste | modifiee |
| `pan_B21a1_2` | panneau | deplacement | 0.05 | faible | RES-POS-004 |  | inchangee |
| `pan_B21a1_3` | panneau | deplacement | 0.15 | faible | RES-POS-004 |  | inchangee |
| `pan_B2a_1` | panneau | reorientation | 342.0 -> 15.5 | faible | RES-ORI-001, RES-POS-003 | revue_adverse_coherence_v3 n° 3 : incertain | inchangee |
| `pan_B6a1_1` | panneau | deplacement | 0.68 | moyenne | RES-POS-007, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 40 : faux | inchangee |
| `pan_C113_1` | panneau | deplacement | 0.09 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 1 : juste | inchangee |
| `pan_C113_1` | panneau | reorientation | 225.0 -> 65.0 | moyenne | RES-ORI-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 1 : juste | inchangee |
| `pan_C114_1` | panneau | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v2 n° 17 : juste | inchangee |
| `pan_C13a_1` | panneau | deplacement | 0.68 | moyenne | RES-POS-007, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 40 : faux | inchangee |
| `pan_J5_1` | panneau | deplacement | 0.93 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v3 n° 6 : juste | inchangee |
| `pan_M9_1` | panneau | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001, RES-SRC-002 | revue_adverse_coherence_v2 n° 17 : juste | inchangee |
| `pan_M9_2` | panneau | reorientation | 342.0 -> 15.5 | faible | RES-ORI-001, RES-POS-003 | revue_adverse_coherence_v3 n° 3 : incertain | inchangee |
| `poteau_bois_NE` | poteau_reseau | deplacement | 0.18 | moyenne | RES-POS-001 |  | inchangee |
| `poteau_incendie_4587565593` | poteau_incendie | reorientation | None -> 54.0 | faible | RES-ORI-001 |  | inchangee |
| `poteau_incendie_5948977094` | poteau_incendie | reorientation | None -> 268.7 | faible | RES-ORI-001 |  | inchangee |

### Marquages

| marquage | classe | décision | preuve | vs r1 |
|---|---|---|---|---|
| `MF-0286` | fleche | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO-B-102 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `MF-0769` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (bordure K-0402 / ligne ML-0799) : écart -0.188 m corrigé ; aucune limite dans la boîte, empreinte 100 % roulable ; bords  | inchangee |
| `MF-6013` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (bordure K-0627 / ligne ML-5297) : écart -0.325 m corrigé ; aucune limite dans la boîte, empreinte 100 % roulable ; bords  | inchangee |
| `MF-6020` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (voie OpenDRIVE 2/-1 ; bornes réelles mesurées par la revue : ligne GAM (orange) à 1,20 m et ML-0785 à 1,61 m de la flèche | nouvelle |
| `MF-8000` | fleche | marquages retirés (non fabriqués) | marque générée (regle:INF-FLE-004) contredite par la géométrie 2026 : bordure 2026 K-0415 dans la boîte de la flèche (marge 0.1 m) ; revue adverse v3  | nouvelle |
| `ML-0102` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0008 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0106` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0009 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0107` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO-B-211 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0112` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0068 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0113` | ligne | marques arrêtées à l'arête des bordures | 1.24 m de marque au-delà de l'arête avant de K-0233 rendus non peints (géométrie inchangée) | inchangee |
| `ML-0121` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0084 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0131` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0051 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0132` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0052 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0133` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0053 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0135` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0054 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0148` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0092 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0150` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0093 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0151` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0094 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0161` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0106 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0162` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0107 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0163` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0108 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0168` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0109 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0201` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0010 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0202` | ligne | marquages retirés (non fabriqués) | absent en 2026 : preuve stricte ORTHO-B-208 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0208` | ligne | marques arrêtées à l'arête des bordures | 0.47 m de marque au-delà de l'arête avant de K-0230 rendus non peints (géométrie inchangée) | inchangee |
| `ML-0225` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0095 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0226` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0096 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0432` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte PANO2026-004 (photo_2026, apres_travaux) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-0930` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO-B-206 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 | inchangee |
| `ML-7000` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7001` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7002` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7003` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7004` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7005` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7006` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7007` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7008` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-7009` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m | inchangee |
| `ML-8000` | ligne | marquages retirés (non fabriqués) | marque générée (regle:MQ-DET-002) contredite par la géométrie 2026 : trait dans la boîte de la flèche levée GAM 2026 MF-5527 ; revue adverse v3 n° 34  | nouvelle |
| `MT-0563` | transversale | marques arrêtées à l'arête des bordures | 0.10 m de marque au-delà de l'arête avant de K-0386z rendus non peints (géométrie inchangée) | inchangee |
| `MT-8000` | transversale | marques arrêtées à l'arête des bordures | 0.19 m de marque au-delà de l'arête avant de K-0388, K-0627 rendus non peints (géométrie inchangée) | inchangee |
| `MT-8001` | transversale | marques arrêtées à l'arête des bordures | 0.19 m de marque au-delà de l'arête avant de K-0388, K-0627 rendus non peints (géométrie inchangée) | inchangee |

### Base gardée et confirmée par une revue

| entité | nature | motif | revue |
|---|---|---|---|
| `arbre_029` | souche_presente | arbre absent, souche présente : l'objet décrit est la souche (type souche, levé GAM, 0,4 m), vue sur ded07efa et f8d91bb1 ; non-instanciation de la cohérence non appliqué | revue_adverse_coherence_v3 n° 19 : juste |
| `arbre_052` | conforme_confirme | PCRS 2022 (sans feuilles) : centre de couronne et branches rayonnant depuis le point (< 0,3 m) | revue_adverse_coherence_v3 n° 30 : juste |
| `arbre_325` | conforme_confirme | dans la rangée de houppiers le long du bâtiment en 2022 et 2024 (GAM σ 0,05 m) | revue_adverse_coherence_v3 n° 28 : juste |
| `arbre_411` | conforme_confirme | houppier présent en 2022, 2024 et sur Pléiades 2025 | revue_adverse_coherence_v3 n° 29 : juste |
| `MF-5527` | fleche_voie_coupee_levee | flèche gam gardée ; la limite qui coupait sa boîte (ligne ML-8000 (x -0.30)) est une marque générée retirée (RES-MQ-004) | revue_adverse_coherence_v3 n° 34 : juste |
| `MF-6000` | fleche_garde_par_ortho | flèche gardée à sa position décrite (garde_par_ortho), confirmée par la revue v3 | revue_adverse_coherence_v3 n° 33 : juste |
| `abri_SE_0396` | conforme_confirme | centroïde du polygone OSM way/185326914 remis à jour après les travaux ; concorde avec le quai bus du plan 2025 et GTFS 2026 (arrêt 0396) | revue_adverse_coherence_v3 n° 24 : juste |
| `lamp_9665416717` | position_source_confirmee | la cohérence v3 garde la position de la base, confirmée sur photos par la revue v3 | revue_adverse_coherence_v3 n° 36 : juste |

## Planches avant / après (10 changements)

À gauche, ortho PCRS 5 cm du 2022-05-10 (antérieure aux travaux) ; jaune : arêtes avant des bordures 2026 ; rouge : avant ; cyan : après (échelle 1 m pour les déplacements de moins de 0,5 m). À droite, pour un objet, jusqu'à deux vues perspectives des photos Panoramax calées : axe du mât à la position avant (rouge, A) et après (cyan, C). Sélection : décisions contre la cohérence, puis nouvelles ou modifiées depuis r1, puis portée. Mosaïque : `planches/av_ap_00_index.jpg`. Les planches contiennent une imagerie tierce : elles restent locales (ignorées par git).

| # | entité | décision | vs r1 | photos | planche |
|---|---|---|---|---|---|
| 1 | `ML-8000` | retrait | nouvelle | - | `planches/av_ap_01_ML-8000_retrait.jpg` |
| 2 | `MF-8000` | retrait | nouvelle | - | `planches/av_ap_02_MF-8000_retrait.jpg` |
| 3 | `lamp_9514828517` | deplacement | modifiee | pnx:f8d91bb1, pnx:ded07efa | `planches/av_ap_03_lamp_9514828517_deplacement.jpg` |
| 4 | `feu_NE_TPC` | deplacement | inchangee | pnx:e5d79de9, pnx:5c0d1d39 | `planches/av_ap_04_feu_NE_TPC_deplacement.jpg` |
| 5 | `arbre_027` | non_instancie_absent_2026 | modifiee | pnx:ded07efa, pnx:f8d91bb1 | `planches/av_ap_05_arbre_027_non_instancie_absent_2026.jpg` |
| 6 | `MF-6020` | recalage_fleche | nouvelle | - | `planches/av_ap_06_MF-6020_recalage_fleche.jpg` |
| 7 | `pan_AB4_2` | deplacement | modifiee | pnx:ded07efa, pnx:f8d91bb1 | `planches/av_ap_07_pan_AB4_2_deplacement.jpg` |
| 8 | `feu_REV_droite` | deplacement | modifiee | pnx:5c0d1d39, pnx:e5d79de9 | `planches/av_ap_08_feu_REV_droite_deplacement.jpg` |
| 9 | `pan_AB3a_3` | deplacement | inchangee | pnx:ded07efa, pnx:f8d91bb1 | `planches/av_ap_09_pan_AB3a_3_deplacement.jpg` |
| 10 | `pan_C113_1` | reorientation | inchangee | pnx:e5d79de9, pnx:9834f494 | `planches/av_ap_10_pan_C113_1_reorientation.jpg` |

Lecture des planches (agent RÉSOLUTION, après les avoir regardées) :

- #01 `ML-8000` : le trait retiré (rouge) part du nez de l'îlot, traverse la flèche de tourne-à-gauche peinte en 2022 puis court au milieu de la voie, entre ML-5402 / ML-0408 (vert, côté îlot) et ML-5228 (vert, tirets visibles en 2022) ; aucune peinture sur son tracé : il couperait une voie de 3,3 m en deux : retrait justifié.
- #02 `MF-8000` : le contour rouge est posé sur l'ancienne flèche TD_TAD peinte en 2022 ; la bordure 2026 K-0415 (jaune) la coupe dans sa longueur, sa moitié droite est hors de la chaussée 2026 : la flèche ne peut pas exister telle que décrite ; le levé GAM 2026 n'en montre aucune : retrait justifié.
- #03 `lamp_9514828517` : ortho 2022 : l'ombre fine du mât (vers le NNO) part de C (cyan), pas de A (rouge, 0,7 m à l'ouest) ; f8d91bb1 (4,5 m) et ded07efa (7,8 m), 2026 : l'axe C suit le mât jusqu'à la lanterne, l'axe A tombe sur la palissade et le ciel : position F reprise à juste titre (groupe B6a1 / C13a).
- #04 `feu_NE_TPC` : e5d79de9 (5,9 m) et 5c0d1d39 (7,9 m) : l'axe C (cyan) est sur le fût du support, l'axe A (rouge) à côté, à gauche, sans fût ; sur l'ortho l'ombre du support part de C : déplacement de 0,19 m cohérent.
- #05 `arbre_027` : 2022 : pelouse au point levé ; ded07efa (11,2 m) et f8d91bb1 (12,4 m), 2026 : l'axe projeté tombe sur une voiture garée puis sur la façade, sans tronc ni houppier ; la traînée grise verticale voisine est une salissure de l'objectif (même colonne de l'image, côté gauche, sur les 3 photos, vérifié sur les images brutes) : absence confirmée.
- #06 `MF-6020` : la flèche recentrée (cyan) est à mi-distance de ML-0785 (au NO) et de la ligne au SE (≈ 1,45 m et 1,54 m mesurés sur la planche agrandie), l'ancienne (rouge) était plus près de la ligne SE ; flèche neuve 2025 : le fond 2022 montre l'ancien marquage.
- #07 `pan_AB4_2` : ded07efa (18,8 m) et f8d91bb1 (19,9 m), 2026 : le poteau du STOP est sur C, A tombe dans le vide à sa droite ; l'écart de 0,12 m signalé par la revue (poussée par la règle, R8) n'est pas lisible à cette échelle (listé).
- #08 `feu_REV_droite` : 0,17 m : sur 5c0d1d39 (15,9 m) et e5d79de9 (20,1 m) les deux axes touchent le fût, C au centre, A sur son bord gauche : écart sous ce que ces vues séparent ; appliqué comme triangulation en accord Q1, sans plus.
- #09 `pan_AB3a_3` : ded07efa (14,3 m) et f8d91bb1 (15,2 m), 2026 : le triangle AB3a et son poteau sont sur C, dans le refuge 2026 (contour jaune) ; A tombe sur le poteau du STOP voisin (pan_AB4_2), sans triangle : déplacement de 4,15 m confirmé.
- #10 `pan_C113_1` : 9834f494 (caméra au 64°) voit la face bleue de face : la face est vers le NE, 225° est faux ; mais e5d79de9 (caméra au 167°) voit aussi la face, de biais : à 65° elle y serait de dos ; azimut fin probablement ≈ 95° (77-109°), listé à mesurer sur place.

## Ce qui reste non résolu

| famille | origine | n |
|---|---|---|
| ajouts | proposition_rejetee | 7 |
| ajouts | schema | 5 |
| arbres | incertain | 13 |
| arbres | proposition_rejetee | 5 |
| arbres | schema | 1 |
| bordures | conflit | 25 |
| bordures | incertain | 1 |
| bordures | schema | 2 |
| ilots | incertain | 1 |
| marquages | conflit | 31 |
| marquages | incertain | 24 |
| marquages | proposition_rejetee | 6 |
| marquages | schema | 20 |
| mobilier | conflit | 4 |
| mobilier | incertain | 39 |
| mobilier | proposition_rejetee | 10 |
| objets | conflit | 40 |
| objets | incertain | 13 |
| surfaces | conflit | 28 |
| surfaces | incertain | 25 |
| surfaces | schema | 2 |

Origines : `conflit` (sources contradictoires), `incertain` (preuve insuffisante ou revue « incertain »), `proposition_rejetee` (proposition de la fusion ou de la cohérence refusée par une règle RES), `schema` (non représentable dans le schéma 0.3), `validation` (retirée par la garde de validation).

### Par station terrain

| station | lieu | n | natures principales |
|---|---|---|---|
| S9 | parcours rive SE de Verdun NE | 28 | conflit 7, marque_hors_chaussee 5, attribut 4, position 3 |
| S13 | débouché des Mitaillères | 24 | conflit 8, ajout 5, anomalie_surface 4, absence_a_verifier 3 |
| N1 | station à créer en (-96 ; -114) : hors de portée de S1-S15 | 20 | conflit 7, attribut 5, ajout 3, vue_intervalle_0 2 |
| N2 | station à créer en (+71 ; -91) : hors de portée de S1-S15 | 17 | attribut 8, ajout 3, conflit 2, retrait 2 |
| N3 | station à créer en (-121 ; +122) : hors de portée de S1-S15 | 15 | violation_physique 3, conflit 3, ajout 2, anomalie_surface 2 |
| S7 | îlot du Vercors | 15 | orientation_tete 5, attribut 4, raccourcissement 2, marque_hors_chaussee 1 |
| S4 | angle O, Verdun SO × Revirée | 14 | absence_projection_lointaine 2, conflit 2, anomalie_surface 2, conflit_surface_marquage 1 |
| S14 | parcours Verdun SO | 13 | anomalie_surface 4, violation_physique 2, recalage_fleche 2, conforme_non_verifiable 2 |
| S12 | parcours de la Revirée | 12 | hypothese_spec 4, existence 3, attribut 1, orientation_tete 1 |
| N4 | station à créer en (-18 ; -128) : hors de portée de S1-S15 | 11 | presence_2026_non_visible 4, ajout 2, existence 1, violation_physique 1 |
| N5 | station à créer en (+92 ; +57) : hors de portée de S1-S15 | 10 | attribut 3, fleche_voie_non_bornee 2, surface_a_corriger 2, anomalie_surface 2 |
| N6 | station à créer en (+133 ; +98) : hors de portée de S1-S15 | 9 | anomalie_surface 3, conflit 2, attribut 1, marque_hors_chaussee 1 |
| S11 | arc de bordures (50-67 ; 98-105) | 9 | conflit 7, attribut 2 |
| S10b | sortie de la voie privée des Saules Blancs | 8 | attribut 3, violation_physique 2, conflit 1, position 1 |
| S15 | parcours rive est du Vercors | 8 | fleche_leve_ecart_garde 2, conflit 2, ajout 1, violation_physique 1 |
| S3 | angle S, Vercors × Verdun SO | 7 | attribut 3, conflit 2, marque_hors_chaussee 1, violation_physique 1 |
| S8 | quais La Revirée, Verdun SO | 7 | conflit 2, ajout 1, violation_physique 1, position_douteuse 1 |
| N7 | station à créer en (+90 ; -38) : hors de portée de S1-S15 | 6 | conflit 2, anomalie_surface 2, vue_intervalle_3 1, vue_intervalle_0 1 |
| S1 | angle N, Revirée × Verdun NE | 6 | conflit 3, ajout 1, orientation_a_preciser 1, position_fusion 1 |
| S5 | refuge (TPC) de Verdun SO | 6 | marque_hors_chaussee 2, conflit 2, position_fusion 1, hypothese_spec 1 |
| N8 | station à créer en (-71 ; +96) : hors de portée de S1-S15 | 5 | ajout 3, position_fusion 1, conflit 1 |
| N10 | station à créer en (+125 ; -97) : hors de portée de S1-S15 | 4 | attribut 2, conflit 1, anomalie_surface 1 |
| N11 | station à créer en (-94 ; -32) : hors de portée de S1-S15 | 4 | ajout 2, conflit 2 |
| N9 | station à créer en (+62 ; +22) : hors de portée de S1-S15 | 4 | fleche_voie_non_bornee 2, attribut 1, conflit 1 |
| N12 | station à créer en (-16 ; +138) : hors de portée de S1-S15 | 3 | marque_hors_chaussee 3 |
| N13 | station à créer en (+28 ; +92) : hors de portée de S1-S15 | 3 | marque_hors_chaussee 2, conflit 1 |
| N14 | station à créer en (-139 ; +51) : hors de portée de S1-S15 | 3 | ajout 1, conflit 1, position_fusion 1 |
| N15 | station à créer en (-109 ; +24) : hors de portée de S1-S15 | 3 | conflit 3 |
| S2 | angle E, Verdun NE × Vercors | 3 | position_fusion 1, tete_feu 1, conflit 1 |
| S6 | refuge (TPC) de Verdun NE | 3 | attribut 1, raccourcissement 1, tete_feu 1 |
| sans position | position inconnue | 3 | attribut 2, conflit 1 |
| N16 | station à créer en (-48 ; +71) : hors de portée de S1-S15 | 2 | violation_physique 1, position_fusion 1 |
| N17 | station à créer en (+138 ; +22) : hors de portée de S1-S15 | 2 | conforme_non_verifiable 1, conflit 1 |
| N18 | station à créer en (-146 ; -53) : hors de portée de S1-S15 | 2 | ajout 2 |
| N19 | station à créer en (-57 ; -114) : hors de portée de S1-S15 | 2 | ajout 1, conflit 1 |
| N20 | station à créer en (+82 ; -129) : hors de portée de S1-S15 | 2 | conflit 1, attribut 1 |
| N21 | station à créer en (+131 ; -136) : hors de portée de S1-S15 | 1 | anomalie_surface 1 |
| N22 | station à créer en (-50 ; +148) : hors de portée de S1-S15 | 1 | existence 1 |
| N23 | station à créer en (-99 ; +88) : hors de portée de S1-S15 | 1 | conforme_non_verifiable 1 |
| N24 | station à créer en (-131 ; -115) : hors de portée de S1-S15 | 1 | absence_projection_lointaine 1 |
| N25 | station à créer en (-149 ; -146) : hors de portée de S1-S15 | 1 | ajout 1 |
| N26 | station à créer en (-44 ; +30) : hors de portée de S1-S15 | 1 | ajout 1 |
| N27 | station à créer en (+52 ; +133) : hors de portée de S1-S15 | 1 | conflit 1 |
| N28 | station à créer en (-67 ; -1) : hors de portée de S1-S15 | 1 | conflit 1 |
| N29 | station à créer en (-95 ; +142) : hors de portée de S1-S15 | 1 | ajout 1 |

Les stations S1 à S15 sont celles de `recon/pcg/enrichir/PROTOCOLE_TERRAIN.md` (portée 30 m pour une station, 15 m pour un parcours) ; N1, N2… sont des stations à créer (couverture gloutonne de 30 m des entités hors de portée ; leur numérotation dépend de l'ensemble des entités et change d'une résolution à l'autre).

### Liste complète par station

Pour chaque station : entité (nature, origine) — ce qu'il faut regarder sur place. Le détail (motif complet, proposition, observations, revue) est dans `journal_resolution.json` (`non_resolues`) et `non_resolus.geojson`.

**S9** — parcours rive SE de Verdun NE (28)

- `K-0185` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-010 : intervalle 0 (s 0.0-4.6 m, T2, vue 0.125 m mesurée au LiDAR 2021) contre MLY-BOR-012 à s 2.279 m « rive de chaussée arasée contre l'accotement enherbé (ligne de rive e
- `K-0185` (vue_intervalle_0, conflit) : vue observée contredisant le profil de l'intervalle 0 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `MF-5042` (fleche_leve_ecart_garde, incertain) : flèche gardée (leve_ecart_garde, écart -0.366 m ; bordure K-0386 | ligne ML-5136) : bords de voie à vérifier
- `MF-5043` (fleche_leve_ecart_garde, incertain) : flèche gardée (leve_ecart_garde, écart 0.336 m ; ligne ML-5136 | ligne ML-5185) : bords de voie à vérifier
- `MF-6003` (fleche_garde_par_ortho, incertain) : flèche gardée (garde_par_ortho, écart 0.302 m ; ligne ML-5136 | ligne ML-5185) : bords de voie à vérifier
- `ML-5140` (marque_hors_chaussee, conflit) : 27% hors chaussée (débord 0.68 m), source gam : bordure, limite de chaussée ou marque à revoir
- `ML-5141` (absence_anterieure_contre_2026, conflit) : retrait vu(e) avant la fin des travaux (avant_travaux_hors_emprise) contre un marquage levé GAM 2026
- `ML-5142` (marque_hors_chaussee, conflit) : 27% hors chaussée (débord 0.531 m), source gam : bordure, limite de chaussée ou marque à revoir
- `ML-5145` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source gam : bordure, limite de chaussée ou marque à revoir
- `ML-5146` (marque_hors_chaussee, conflit) : 27% hors chaussée (débord 0.686 m), source gam : bordure, limite de chaussée ou marque à revoir
- `MS-5000` (conflit:ajout_contre_leve_gam, conflit) : CF-ENR-005 : objet observé absent de la description (symbole_velo) à 0.66 m de MS-5000 (marquages symbole, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) — trancher 
- `MZ-5002` (absence_anterieure_contre_2026, conflit) : retrait vu(e) avant la fin des travaux (avant_travaux_hors_emprise) contre un marquage levé GAM 2026
- `MZ-5002` (conflit:validite_2026_douteuse, conflit) : CF-ENR-101 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-091, FUS-VAL-03). rien de peint au po
- `MZ-5211` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 0.986 m), source gam : bordure, limite de chaussée ou marque à revoir
- `lamp_9665416717` (position_fusion, conflit) : correction fusion appliquer de 0.876 m (pixel_ortho) non appliquée : Q1 : desaccord avec les photos décisives de la planche ; revue_adverse_coherence_v3 n° 36 : juste; 
- `lamp_9665416817` (attribut:couleur_mat, incertain) : mise à jour couleur_mat en revue (FUS-ATT-06)
- `pan_AB3a_2` (position, incertain) : déplacement de 0.70 m non appliqué : revue « incertain »
- `pan_B1_1` (attribut:azimut_deg, conflit) : azimut fusion 45.0° contre azimut 125.0° de la cohérence v3 (revue de cohérence : azimut origine)
- `pan_B1_1` (orientation_ambigue, incertain) : « conforme » non vérifiable (revue v3 n° 21) : position plausible (vu devant le mât 2 depuis le NE sur bb9c05ff) ; azimut 125° tiré d'une seule vue oblique à plat (w/h 0,44), ambig
- `pan_B2a_1` (attribut:azimut_deg, conflit) : azimut fusion 45.0° contre azimut 15.5° de la cohérence v3
- `pan_B2a_1` (position, incertain) : déplacement de 0.70 m non appliqué : revue « incertain »
- `pan_M9_2` (position, incertain) : déplacement de 0.70 m non appliqué : revue « incertain »
- `ADD-SPEC-M9c_acces_NE` (hypothese_spec, incertain) : panneaux.json décrit M9c_acces_NE (M9c), absent de mobilier.geojson
- `lamp_9665416717` (conflit:coherence_desaccord, conflit) : CF-ENR-025 : cohérence : deplacement de 0.1 m ; image à 0.84 m de la position corrigée et 0.88 m de l'origine (partiel) — position image prioritaire si la décision de fusion est « 
- `lamp_9665416817` (conflit:attribut_desaccord, conflit) : CF-ENR-006 : couleur_mat : {"\"brun-rouille\"": ["MLY-CON-001", "VISION-PANORAMAX-1-17"], "\"gris anthracite patiné\"": ["VISION-PANORAMAX-1-43"]} — valeur retenue brun-rouille (po
- `lamp_9665416817` (conflit:coherence_desaccord, conflit) : CF-ENR-026 : cohérence : deplacement de 0.65 m ; image à 0.44 m de la position corrigée et 0.58 m de l'origine (partiel) — position image prioritaire si la décision de fusion est «
- `pan_J5_1` (conflit:validite_2026_douteuse, conflit) : CF-ENR-123 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-003, FUS-VAL-04). aucune balise ni ombre au point décrit (extrémité NE de l'îlo
- `S-0120a` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)

**S13** — débouché des Mitaillères (24)

- `ENR-PON-066` (ajout:tampon, proposition_rejetee) : σ 1.033 m > 0.5 m (classe ponctuel)
- `arbre_016` (attribut:hauteur_m, incertain) : valeur 3.0 de confiance faible (< moyenne)
- `K-0511` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-016 : intervalle 0 (s 0.0-2.4 m, P1, vue 0.015 m mesurée au LiDAR 2021) contre MLY-BOR-056 à s 1.197 m « vue ≈ 10 cm » -> [0.08, 0.12] m (haute) -> vue lue 0.100 m (T2) — re
- `K-0511` (vue_intervalle_0, conflit) : vue observée contredisant le profil de l'intervalle 0 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `ENR-MAR-035` (ajout, schema) : ajout instanciable par la fusion non intégré : type paves_jaunes_traversee_cyclable, traversee_cyclable_jaune : paramètres de modulation ou d'aplat non observés
- `ENR-MAR-036` (ajout, schema) : ajout instanciable par la fusion non intégré : type paves_jaunes_traversee_cyclable : paramètres de modulation ou d'aplat non observés
- `ENR-MAR-037` (ajout, schema) : ajout instanciable par la fusion non intégré : type ligne_continue_axiale : paramètres de modulation ou d'aplat non observés
- `ENR-MAR-038` (ajout, schema) : ajout instanciable par la fusion non intégré : type ligne_effet_stop : paramètres de modulation ou d'aplat non observés
- `ML-5341` (absence_a_verifier, incertain) : absence 2026 sans preuve stricte (FUS-EXI-04) : marquage gardé
- `ML-5341` (conflit:existence_douteuse_2026, conflit) : CF-ENR-041 : absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.30, retrait 0.00, présence 0.00). au bord droit du cadre, au-delà de ML-5342 :
- `ML-5342` (absence_a_verifier, incertain) : absence 2026 sans preuve stricte (FUS-EXI-04) : marquage gardé
- `ML-5342` (conflit:existence_douteuse_2026, conflit) : CF-ENR-042 : absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.60, retrait 0.00, présence 0.00). place à l'est de la Dacia vue en entier, de 
- `ML-5343` (absence_a_verifier, incertain) : absence 2026 sans preuve stricte (FUS-EXI-04) : marquage gardé
- `ML-5343` (conflit:existence_douteuse_2026, conflit) : CF-ENR-043 : absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.30, retrait 0.00, présence 0.00). tracé en grande partie sous la Dacia et son 
- `lamp_9514828431` (position_fusion, incertain) : correction fusion revue_requise de 1.883 m (triangulation) ; cohérence v3 : hypothèse confirmée par Q1 (pnx:ded07efa), non relue par une revue adverse (> 0,30 m); σ fusion 0.60 m >
- `lamp_9514828431` (conflit:coherence_desaccord, conflit) : CF-ENR-024 : cohérence : deplacement de 0.1 m ; image à 1.98 m de la position corrigée et 1.88 m de l'origine (partiel) — position image prioritaire si la décision de fusion est « 
- `lamp_9514828431` (conflit:deplacement_non_etaye, conflit) : CF-ENR-034 : deplacement de 1.88 m proposé ; σ fusion 0.60 m > 0,5 m — revue visuelle des planches avant application
- `pan_B6a1_1` (conflit:coherence_desaccord, conflit) : CF-ENR-028 : cohérence : deplacement de 0.016 m ; image à 0.70 m de la position corrigée et 0.68 m de l'origine (partiel) — position image prioritaire si la décision de fusion est 
- `pan_C13a_1` (conflit:coherence_desaccord, conflit) : CF-ENR-029 : cohérence : deplacement de 0.016 m ; image à 0.70 m de la position corrigée et 0.68 m de l'origine (partiel) — position image prioritaire si la décision de fusion est 
- `S-0457a` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `lamp_9514828517` (anomalie_surface, conflit) : position prouvée sur photos (RES-POS-007) sur la classe chaussee (S-0268b) : îlot, trottoir ou espace vert manquant dans la partition ; surface à corriger par le propriétaire de su
- `pan_AB4_2` (anomalie_surface, conflit) : réserve de la revue v3 n° 7 (R8) : sur ab42_pnx_ded07efa.jpg le poteau est sur M (u ≈ 4325, M 4325,1) et C à 5,6 px (≈ 0,12 m) : la poussée de −0,25 m par la règle (M en classe « c
- `pan_B6a1_1` (anomalie_surface, conflit) : position prouvée sur photos (RES-POS-007) sur la classe chaussee (S-0268b) : îlot, trottoir ou espace vert manquant dans la partition ; surface à corriger par le propriétaire de su
- `pan_C13a_1` (anomalie_surface, conflit) : position prouvée sur photos (RES-POS-007) sur la classe chaussee (S-0268b) : îlot, trottoir ou espace vert manquant dans la partition ; surface à corriger par le propriétaire de su

**N1** — station à créer en (-96 ; -114) : hors de portée de S1-S15 (20)

- `K-0118` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-007 : intervalle 0 (s 0.0-1.2 m, T3, vue 0.190 m mesurée au LiDAR 2021) contre MLY-BOR-002 à s 0.598 m « vue ≤ 5 cm » -> [0.0, 0.05] m (haute) -> vue lue 0.025 m (P1) — rele
- `K-0118` (vue_intervalle_0, conflit) : vue observée contredisant le profil de l'intervalle 0 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `K-0298` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-011 : intervalle 0 (s 0.0-12.6 m, T3, vue 0.210 m mesurée au LiDAR 2021) contre MLY-BOR-020 à s 7.336 m « vue ≈ 5–10 cm » -> [0.05, 0.1] m (haute) -> vue lue 0.075 m (A2) — 
- `K-0298` (vue_intervalle_0, conflit) : vue observée contredisant le profil de l'intervalle 0 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `K-0675` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-022 : intervalle 7 (s 35.5-45.5 m, T2, vue 0.100 m mesurée au LiDAR 2021) contre MLY-BOR-078 à s 50.049 m « rive arasée de la contre-allée de stationnement (limite gravillon
- `K-0675` (vue_intervalle_10, conflit) : vue observée contredisant le profil de l'intervalle 10 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `K-0675` (vue_intervalle_7, conflit) : vue observée contredisant le profil de l'intervalle 7 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `ENR-MAR-006` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Point : forme du marquage inconnue (polygone ou trait à relever)
- `ENR-MAR-007` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Point : forme du marquage inconnue (polygone ou trait à relever)
- `ENR-MAR-011` (ajout, schema) : ajout instanciable par la fusion non intégré : type ligne_discontinue_stationnement : paramètres de modulation ou d'aplat non observés
- `ML-0212` (attribut:modulation, schema) : modulation continue -> T'1 demande trait, vide et phase (absents de l'observation)
- `ML-0222` (absence_a_verifier, incertain) : absence 2026 sans preuve stricte (FUS-EXI-04) : marquage gardé
- `ML-0222` (conflit:existence_douteuse_2026, conflit) : CF-ENR-040 : absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » (absence 0.30, retrait 0.00, présence 0.00). le tracé tombe sur la bande plantée (haie ta
- `ML-5159` (conflit:ajout_contre_leve_gam, conflit) : CF-ENR-001 : objet observé absent de la description (t_stationnement) à 1.42 m de ML-5159 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) — trancher
- `arbre_022` (conflit:validite_2026_douteuse, conflit) : CF-ENR-102 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0046, FUS-VAL-04). pelouse sans couronne à la position en 05/2022 — garder l'ob
- `stationnement_velos_12673486211` (conflit:validite_2026_douteuse, conflit) : CF-ENR-124 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-03-17) (MLY-MOB-035, FUS-VAL-03). banc-muret béton, r
- `S-0136h` (attribut:classe, incertain) : mise à jour classe en revue (FUS-ATT-06)
- `S-0136h` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0136m` (attribut:materiau_id, incertain) : valeur 'massif' de confiance faible (< moyenne)
- `S-0343a` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)

**N2** — station à créer en (+71 ; -91) : hors de portée de S1-S15 (17)

- `ENR-SUR-005` (ajout:surface, schema) : surface observée : la partition des surfaces appartient à surfaces.py (hôte S-0352a)
- `ENR-SUR-006` (ajout:surface, schema) : surface observée : la partition des surfaces appartient à surfaces.py (hôte S-0352a)
- `ENR-SUR-007` (ajout:surface, schema) : surface observée : la partition des surfaces appartient à surfaces.py (hôte S-0465b)
- `arbre_101` (attribut:essence, incertain) : valeur 'Platanus' de confiance faible (< moyenne)
- `arbre_134` (attribut:essence, incertain) : valeur 'Platanus' de confiance faible (< moyenne)
- `arbre_135` (attribut:couronne_m, incertain) : mise à jour couronne_m en revue (FUS-ATT-06)
- `arbre_135` (attribut:hauteur_m, incertain) : mise à jour hauteur_m en revue (FUS-ATT-06)
- `K-0465` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-014 : intervalle 1 (s 2.0-49.8 m, T2, vue 0.140 m « estimee » (a priori)) contre MLY-BOR-043 à s 39.708 m « rive arasée entre la voie en enrobé et les places en stabilisé / 
- `K-0465` (vue_intervalle_1, conflit) : vue observée contredisant le profil de l'intervalle 1 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `K-0470` (retrait, schema) : retrait prouvé (retirer) mais référencé par S-0374a, S-0374l, S-B0470 : à faire par le propriétaire de bordures.py / surfaces.py (partition)
- `K-0472` (retrait, schema) : retrait prouvé (retirer) mais référencé par S-0374a, S-B0471, S-B0471-2, S-B0472 : à faire par le propriétaire de bordures.py / surfaces.py (partition)
- `portail_13827066656` (conforme_non_verifiable, incertain) : « conforme » non vérifiable (revue v3 n° 26) : BD ORTHO 2024 : entrée d'allée au pied d'un nouveau bâtiment ; portillon illisible à 20 cm
- `S-0351` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0374a` (conflit:surface_a_decouper, conflit) : CF-ENR-060 : surface de 2072 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : herbe_haute (MLY-SUR-087) — découper le polygone dans la description du sol (sous-zo
- `S-0374d` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0374e` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0459b` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)

**N3** — station à créer en (-121 ; +122) : hors de portée de S1-S15 (15)

- `ENR-MOB-002` (ajout:mobilier, proposition_rejetee) : type ambigu (abri_ou_range_velos)
- `arbre_413` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.50 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier
- `ENR-MAR-004` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Polygon : forme du marquage inconnue (polygone ou trait à relever)
- `ML-0115` (translation, proposition_rejetee) : translation de 0.077 m sous la résolution des sources : sans effet
- `armoire_1313238971` (position_douteuse, incertain) : « conforme » non vérifiable (revue v3 n° 22) : PCRS 2022 : A tombe sur la bande claire de la bordure, sans coffret ; rangée de boîtes claires (ombre au NNO) 1,3 à 2,5 m plus à l'ou
- `armoire_1313238971` (position_fusion, incertain) : correction fusion revue_requise de 1.044 m (pixel_ortho); une seule source non triangulée et pas de correction affirmée; aucune mesure stricte (FUS-COUV-02)
- `barriere_levante_12462947804` (conforme_non_verifiable, incertain) : « conforme » non vérifiable sur image
- `corbeille_12328578845` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.25 m (GEN-01, MOB-01) sans mesure ni revue : objet ou surface (parking, classe faible) à vérifier
- `poteau_incendie_9577881491` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.70 m (GEN-01, RES-03) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier
- `ADD-ILOT-lamp_12668578865` (ilot_manquant, incertain) : objets prouvés (lamp_12668578865) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `armoire_1313238971` (conflit:deplacement_non_etaye, conflit) : CF-ENR-032 : deplacement de 1.04 m proposé ; une seule source non triangulée et pas de correction affirmée ; aucune mesure stricte (FUS-COUV-02) — revue visuelle des planches avant
- `barriere_levante_12462947804` (conflit:validite_2026_douteuse, conflit) : CF-ENR-113 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-189, FUS-VAL-04). aucune lisse ni potence visible au point (voie du parking) en
- `chicane_12462947805` (conflit:validite_2026_douteuse, conflit) : CF-ENR-114 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-177, FUS-VAL-04). aucune barrière / chicane visible au point (place de parking 
- `lamp_12668578865` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; mesure retenue comme nouvel a priori (P3) : revue_coherence, σ 0.3 m, 1.63
- `lamp_12668620636` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; mesure retenue comme nouvel a priori (P3) : fusion_recensement_0.3, σ 0.18

**S7** — îlot du Vercors (15)

- `I-0390` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `MP-5189` (attribut:bouton_appel, incertain) : mise à jour bouton_appel en revue (FUS-ATT-06)
- `MP-5189` (attribut:signal_sonore, incertain) : mise à jour signal_sonore en revue (FUS-ATT-06)
- `MP-5189` (attribut:vibreur, incertain) : mise à jour vibreur en revue (FUS-ATT-06)
- `MT-8005` (raccourcissement, proposition_rejetee) : raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité
- `MT-8006` (raccourcissement, proposition_rejetee) : raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité
- `MZ-5189` (marque_hors_chaussee, conflit) : 30% hors chaussée (débord 0.338 m), source gam : bordure, limite de chaussée ou marque à revoir
- `feu_VERC_droite_t1` (orientation_tete, incertain) : tête à 10.5° de la cible (voie gérée à 40 m en amont de la ligne MT-8006) : gardée par la cohérence
- `feu_VERC_droite_t3` (orientation_tete, proposition_rejetee) : azimut source 172.0° non saisi au pas de 45° ou écart 10.8° > 60°
- `feu_VERC_droite_t4` (orientation_tete, incertain) : tête à 10.5° de la cible (voie gérée à 40 m en amont de la ligne MT-8006) : gardée par la cohérence
- `feu_VERC_ilot` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.40 m (FEU-02, FEU-07, GEN-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier
- `feu_VERC_ilot_t1` (orientation_tete, incertain) : tête à 17.3° de la cible (voie gérée à 40 m en amont de la ligne MT-8006) : gardée par la cohérence
- `feu_VERC_ilot_t2` (orientation_tete, incertain) : tête à 23.9° de la cible (extrémité opposée du passage MP-5189) : gardée par la cohérence
- `pan_B21a1_4` (orientation, incertain) : réorientation 10.0° -> 341.1° sans revue juste
- `ADD-SPEC-M12a_ou_AB3a_feu_VERC_droite` (hypothese_spec, incertain) : panneaux.json place M12a_ou_AB3a_feu_VERC_droite (M12a (probable)) à 0.255 m de feu_VERC_droite (même support ?)

**S4** — angle O, Verdun SO × Revirée (14)

- `MF-0774` (conflit_surface_marquage, conflit) : flèche plan2025 entièrement hors des surfaces roulables (avant 0.0, recalée 0.0) : conflit surface / marquage, aucun recalage ; surface ou flèche à vérifier
- `MF-0774` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source plan2025 : bordure, limite de chaussée ou marque à revoir
- `MF-6018` (recalage_fleche, incertain) : recalage non appliqué : bords non représentatifs : K-0381 absent en travers de la tête ; revue « incertain » : le bord K-0381 est un court tronçon de bordure (nez d'îlot), pas un b
- `ML-0238` (absence_projection_lointaine, incertain) : absence vue seulement en projection à 18.5 m de la caméra : trait fin possiblement invisible
- `ML-0240` (absence_projection_lointaine, incertain) : absence vue seulement en projection à 17.4 m de la caméra : trait fin possiblement invisible
- `lamp_lidar_SW_NO` (type, incertain) : type à vérifier : poteau_reseau probable
- `poteau_reseau_12888056356` (position_fusion, incertain) : correction fusion revue_requise de 3.29 m (triangulation); aucune mesure stricte (FUS-COUV-02); mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-
- `ADD-SPEC-plaque_mat_3150` (hypothese_spec, incertain) : panneaux.json décrit plaque_mat_3150 (plaque de rue), absent de mobilier.geojson
- `poteau_reseau_12888056356` (conflit:deplacement_non_etaye, conflit) : CF-ENR-037 : deplacement de 3.29 m proposé ; aucune mesure stricte (FUS-COUV-02) ; mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02) — re
- `poteau_reseau_12888056356` (conflit:doublon_apres_correction, conflit) : CF-ENR-039 : position corrigée à 0.66 m de lamp_lidar_SW_NO (lampadaire) : même objet probable — fusionner poteau_reseau_12888056356 et lamp_lidar_SW_NO (garder un seul objet au po
- `ADD-SURF-S-0282a` (surface_a_corriger, incertain) : 3 objets de 1 source(s) (arbres/plan2025) sur la surface S-0282a classée chaussee (a_priori:vote_indices_classe ; v1 surf_0282 espace_vert) : bande plantée, îlot ou trottoir probab
- `S-0081a` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `arbre_206` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher
- `arbre_207` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher

**S14** — parcours Verdun SO (13)

- `arbre_109` (existence, incertain) : non-instanciation proposée par la cohérence (a_arbitrer_photo, a_verifier_terrain2026, surface_modifiee_2025) : entité gardée telle que la base
- `arbre_110` (violation_physique, proposition_rejetee) : déplacement par la règle de 1.35 m (GEN-01, VEG-01) sans mesure ni revue : objet ou surface (piste_cyclable, classe sûre) à vérifier
- `MF-6017` (recalage_fleche, proposition_rejetee) : recalage non appliqué : bords non représentatifs : K-0626 absent en travers de la tête
- `MF-6021` (recalage_fleche, proposition_rejetee) : recalage non appliqué : voie bornée seulement par OpenDRIVE (voie OpenDRIVE 2/-2)
- `ML-5302` (marque_hors_chaussee, conflit) : 4% hors chaussée (débord 0.42 m), source gam : bordure, limite de chaussée ou marque à revoir
- `banc_12321340512` (conforme_non_verifiable, incertain) : « conforme » non vérifiable (revue v3 n° 25) : sur le nouveau quai, à 5,2 m du centre de l'abri ; une seule source, aucune image postérieure aux travaux
- `lamp_9514795817` (conforme_non_verifiable, incertain) : « conforme » non vérifiable sur image
- `stationnement_velos_10265340447` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.40 m (GEN-01) sans mesure ni revue : objet ou surface (bande_cyclable, classe faible) à vérifier
- `ADD-SURF-S-0280a` (surface_a_corriger, incertain) : 4 objets de 2 source(s) (arbres/plan2025, mobilier/osm) sur la surface S-0280a classée chaussee (a_priori:vote_indices_classe ; v1 surf_0280 espace_vert) : bande plantée, îlot ou t
- `arbre_166` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher
- `arbre_179` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher
- `poteau_reseau_9742811518` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher
- `stationnement_velos_8360665117` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher

**S12** — parcours de la Revirée (12)

- `arbre_260` (attribut:type, schema) : type 'haie' hors des types d'arbres du paquet (objet à requalifier : haie ou massif)
- `feu_REV_droite_t4` (orientation_tete, proposition_rejetee) : azimut source 330.0° non saisi au pas de 45° ou écart 22.3° > 60°
- `pan_D21_1` (existence, incertain) : non-instanciation proposée par la cohérence (non_resolu, a_verifier_terrain2026, obsolete_probable) : entité gardée telle que la base
- `pan_D21_2` (existence, incertain) : non-instanciation proposée par la cohérence (non_resolu, a_verifier_terrain2026, obsolete_probable) : entité gardée telle que la base
- `pan_J5_2` (existence, incertain) : non-instanciation proposée par la cohérence (non_resolu, a_verifier_terrain2026, obsolete_probable, surface_modifiee_2025) : entité gardée telle que la base
- `poteau_bois_REV_ilot` (position, incertain) : mesure de 0.12 m (axe triangulé (5 vues, 85.7°)) devenue indice par la cohérence v3 (Q1 : desaccord avec les photos décisives de la planche) et non relue par une revue adverse : po
- `ADD-ILOT-poteau_bois_REV_ilot` (ilot_manquant, incertain) : objets prouvés (poteau_bois_REV_ilot) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; emprise a priori (MNT 2026 : -0.01 m)
- `ADD-SPEC-M12a_feu_REV_droite` (hypothese_spec, incertain) : panneaux.json place M12a_feu_REV_droite (M12a (probable)) à 0.169 m de feu_REV_droite (même support ?)
- `ADD-SPEC-M9c_ruisseau` (hypothese_spec, incertain) : panneaux.json place M9c_ruisseau (M9c) à 0.238 m de lamp_12894130974 (même support ?)
- `ADD-SPEC-feu_REV_ilot_E` (hypothese_spec, incertain) : feux.json place feu_REV_ilot_E (support_feux) à 0.583 m de pan_D21_1 (même support ?)
- `ADD-SPEC-feu_REV_ilot_axial` (hypothese_spec, incertain) : feux.json place feu_REV_ilot_axial (support_feux) à 0.054 m de poteau_bois_REV_ilot (même support ?)
- `poteau_bois_REV_ilot` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; preuve forte (photo_pnp, σ 0.1 m) sur chaussee de classe peu sûre (d bordu

**N4** — station à créer en (-18 ; -128) : hors de portée de S1-S15 (11)

- `ENR-MOB-013` (ajout:mobilier, proposition_rejetee) : σ 0.807 m > 0.5 m (classe point)
- `ENR-MAR-030` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Point : forme du marquage inconnue (polygone ou trait à relever)
- `barriere_levante_3375058657` (presence_2026_non_visible, incertain) : revue de présence Q4 : masquée par une voiture garée ; seule vue à 22,7 m
- `boite_aux_lettres_12887274328` (presence_2026_non_visible, incertain) : revue de présence Q4 : masquée par les voitures garées sur les 3 vues
- `lamp_12887274329` (existence, incertain) : non-instanciation de la cohérence (revue de présence : aucun mât dans la boîte ni à ±2 m sur les 3 vues (façade et ciel visibles derrière, jusqu'à 7 m de haut) ; un luminaire mural
- `lamp_9514828418` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.15 m (ECL-01, GEN-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier
- `pan_B6a1_2` (position_douteuse, incertain) : R4 : disque B6a1 non apparié (revue de présence) triangulé sur 3 photos en (−3,28 ; −129,29), résidus < 0,09 m, ≈ 13 m de la position à 2 rayons ; identité et pose non relues
- `pan_B6a1_2` (presence_2026_non_visible, incertain) : revue de présence Q4 : position masquée par les voitures garées ; un disque B6a1 est visible ≈ 17° plus à droite devant la façade, non apparié (position de la triangulation à 2 ray
- `stationnement_velos_13542473491` (presence_2026_non_visible, incertain) : revue de présence Q4 : masqué par les voitures garées (21,4 m)
- `S-0071b` (attribut:materiau_id, incertain) : valeur 'massif' de confiance faible (< moyenne)
- `S-0159a` (conflit:surface_a_decouper, conflit) : CF-ENR-058 : surface de 4036 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées :  — découper le polygone dans la description du sol (sous-zones à leurs positions)

**N5** — station à créer en (+92 ; +57) : hors de portée de S1-S15 (10)

- `arbre_296` (attribut:essence, incertain) : mise à jour essence en revue (FUS-ATT-06)
- `arbre_334` (attribut:essence, incertain) : mise à jour essence en revue (FUS-ATT-06)
- `MF-5096` (fleche_voie_non_bornee, incertain) : flèche gardée (voie_non_bornee, écart None m ; None) : bords de voie à vérifier
- `MF-5097` (fleche_voie_non_bornee, incertain) : flèche gardée (voie_non_bornee, écart None m ; None) : bords de voie à vérifier
- `ML-5136` (attribut:modulation, schema) : modulation continue -> T3 demande trait, vide et phase (absents de l'observation)
- `cloture_gam_047` (conflit:validite_2026_douteuse, conflit) : CF-ENR-117 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (MLY-MOB-023, FUS-VAL-03).  — garder l'objet ;
- `ADD-SURF-arbre_297` (surface_a_corriger, incertain) : arbre levé (arbre_297) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.85 m)) : fosse, bande plantée ou limite de surface à co
- `ADD-SURF-arbre_298` (surface_a_corriger, incertain) : arbre levé (arbre_298) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : +0.03 m)) : fosse, bande plantée ou limite de surface à co
- `arbre_297` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 4.
- `arbre_298` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 3.

**N6** — station à créer en (+133 ; +98) : hors de portée de S1-S15 (9)

- `arbre_412` (attribut:essence, incertain) : mise à jour essence en revue (FUS-ATT-06)
- `ML-5139` (marque_hors_chaussee, conflit) : 99% hors chaussée (débord 1.0 m), source gam : bordure, limite de chaussée ou marque à revoir
- `ADD-ILOT-arbre_397` (ilot_manquant, incertain) : objets prouvés (arbre_397) sur la chaussée à plus de 2 m de toute bordure : îlot bordé absent des surfaces ; MNT 2026 surélevé de 0.07 m
- `arbre_362` (conflit:validite_2026_douteuse, conflit) : CF-ENR-110 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-193, FUS-VAL-03). au point de arbre_3
- `arbre_383` (conflit:validite_2026_douteuse, conflit) : CF-ENR-111 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-194, FUS-VAL-03). même cas que arbre_
- `ADD-SURF-arbre_398` (surface_a_corriger, incertain) : arbre levé (arbre_398) sur une chaussée v1 d'origine raster, à plus de 2 m de toute bordure (emprise a priori (MNT 2026 : -0.23 m)) : fosse, bande plantée ou limite de surface à co
- `arbre_397` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 2.
- `arbre_398` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 2.
- `arbre_411` (anomalie_surface, conflit) : réserve de la revue v3 n° 29 (R8) : point = sommet de couronne LiDAR (σ 1 m), classe « trottoir » à 7 m de K-0666 au milieu d'un boisement : erreur de surface (R8) ; signalement de

**S11** — arc de bordures (50-67 ; 98-105) (9)

- `K-0078` (conflit:validite_2026_douteuse, conflit) : CF-ENR-092 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `K-0081` (conflit:validite_2026_douteuse, conflit) : CF-ENR-093 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `K-0082` (conflit:validite_2026_douteuse, conflit) : CF-ENR-094 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `K-0083` (conflit:validite_2026_douteuse, conflit) : CF-ENR-095 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `K-0084` (conflit:validite_2026_douteuse, conflit) : CF-ENR-096 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `K-0085` (conflit:validite_2026_douteuse, conflit) : CF-ENR-097 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `K-0086` (conflit:validite_2026_douteuse, conflit) : CF-ENR-098 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-094, FUS-VAL-03). l'arc de cercle de 
- `S-0129a` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0129g` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)

**S10b** — sortie de la voie privée des Saules Blancs (8)

- `MS-5129` (conflit:validite_2026_douteuse, conflit) : CF-ENR-100 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la fin des travaux, dans leur emprise, sans appui de conservation (VISION-PANORAMAX-2-49, FUS-
- `portail_13827066643` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.30 m (BAR-03, GEN-09) sans mesure ni revue : objet ou surface (batiment, classe sûre) à vérifier
- `potelet_13827066657` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.45 m (GEN-01, POT-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier
- `potelet_13827066658` (position, incertain) : déplacement de 1.90 m non appliqué : revue « incertain »
- `S-0415j` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0415n` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0430a` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `arbre_226` (anomalie_surface, conflit) : objet prouvé sur une surface de classe chaussee : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur chaussee de classe peu sûre (d bordure 1.

**S15** — parcours rive est du Vercors (8)

- `ENR-PAN-012` (ajout:panneau, proposition_rejetee) : σ 2.582 m > 0.5 m (classe point)
- `arbre_173` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.70 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (piste_cyclable, classe faible) à vérifier
- `MF-5524` (fleche_leve_ecart_garde, incertain) : flèche gardée (leve_ecart_garde, écart 0.225 m ; ligne ML-5228 | bordure K-0415) : bords de voie à vérifier
- `MF-5525` (fleche_leve_ecart_garde, incertain) : flèche gardée (leve_ecart_garde, écart -0.378 m ; ligne ML-5401 | ligne ML-5228) : bords de voie à vérifier
- `ML-5228` (conflit:ajout_contre_leve_gam, conflit) : CF-ENR-003 : objet observé absent de la description (lignes_de_voie_vercors) à 1.31 m de ML-5228 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) — t
- `ML-5401` (conflit:ajout_contre_leve_gam, conflit) : CF-ENR-004 : objet observé absent de la description (lignes_de_voie_vercors) à 0.92 m de ML-5401 (marquages ligne, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04) — t
- `lamp_lidar_VERC_E` (position, incertain) : déplacement de 0.45 m non appliqué : revue « incertain »
- `portail_12976463291` (conforme_non_verifiable, incertain) : « conforme » non vérifiable sur image

**S3** — angle S, Vercors × Verdun SO (7)

- `MP-5282` (attribut:bouton_appel, incertain) : mise à jour bouton_appel en revue (FUS-ATT-06)
- `MP-5282` (attribut:signal_sonore, incertain) : mise à jour signal_sonore en revue (FUS-ATT-06)
- `MP-5282` (attribut:vibreur, incertain) : mise à jour vibreur en revue (FUS-ATT-06)
- `MZ-5282` (marque_hors_chaussee, conflit) : 6% hors chaussée (débord 0.055 m), source gam : bordure, limite de chaussée ou marque à revoir
- `poteau_reseau_13624544994` (violation_physique, proposition_rejetee) : déplacement par la règle de 0.45 m (GEN-01, RES-02) sans mesure ni revue : objet ou surface (parking, classe faible) à vérifier
- `arbre_184` (conflit:validite_2026_douteuse, conflit) : CF-ENR-104 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (MLY-CON-019, pano_0-16, FUS-VAL-04). à la position d'arbre_184 : abri voyageurs vitré, 
- `cloture_gam_001` (conflit:validite_2026_douteuse, conflit) : CF-ENR-115 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-083, FUS-VAL-03). le tracé GAM de clo

**S8** — quais La Revirée, Verdun SO (7)

- `ENR-SUR-002` (ajout:surface, schema) : surface observée : la partition des surfaces appartient à surfaces.py (hôte S-0161a)
- `arbre_093` (violation_physique, proposition_rejetee) : déplacement par la règle de 1.25 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (bande_cyclable, classe faible) à vérifier
- `banc_8360664518` (position_douteuse, incertain) : « conforme » non vérifiable (revue v3 n° 23) : banc rouge visible en 2022 et 2024 en (−73,0 ; −49,0), à 4,0 m du nœud OSM 2026 (bord d'allée dans l'emprise des travaux) ; classe « 
- `banc_8360664518` (position_fusion, incertain) : correction fusion revue_requise de 4.474 m (pixel_ortho); aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines); aucune mesure stricte (FUS-COUV-02)
- `banc_8360664518` (conflit:deplacement_non_etaye, conflit) : CF-ENR-033 : deplacement de 4.47 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) ; aucune mesure stricte (FUS-COUV-02) — revue visuelle
- `cloture_gam_002` (conflit:validite_2026_douteuse, conflit) : CF-ENR-116 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (ORTHO-B-083, FUS-VAL-03). le tracé GAM de clo
- `arbre_194` (anomalie_surface, conflit) : objet prouvé sur une surface de classe bande_cyclable : surface à corriger par le propriétaire de surfaces.py ; aucune position admissible et aucune preuve pour trancher

**N7** — station à créer en (+90 ; -38) : hors de portée de S1-S15 (6)

- `K-0435` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-012 : intervalle 3 (s 17.5-31.0 m, P1, vue 0.020 m « estimee » (a priori)) contre MLY-BOR-031 à s 15.503 m « vue ≈ 10–15 cm » -> [0.1, 0.15] m (haute, intervalle voisin) -> 
- `K-0435` (vue_intervalle_3, conflit) : vue observée contredisant le profil de l'intervalle 3 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `K-0439` (conflit:bordure_vue_contradiction, conflit) : CF-ENR-013 : intervalle 0 (s 0.0-86.5 m, T2, vue 0.140 m « estimee » (a priori)) contre MLY-BOR-034 à s 43.968 m « bordure arasée entre la voie en enrobé et l'aire de stationnement
- `K-0439` (vue_intervalle_0, conflit) : vue observée contredisant le profil de l'intervalle 0 : relevé terrain (photo rasante, mètre pliant) avant tout changement
- `arbre_188` (anomalie_surface, conflit) : objet prouvé sur une surface de classe batiment : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 4.
- `arbre_189` (anomalie_surface, conflit) : objet prouvé sur une surface de classe batiment : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 6.

**S1** — angle N, Revirée × Verdun NE (6)

- `ENR-VEG-002` (ajout:haie, proposition_rejetee) : σ 2.066 m > 1.0 m (classe lineaire)
- `pan_C113_1` (orientation_a_preciser, incertain) : azimut 65.0° appliqué (revue juste) mais la seconde lecture lit la face entre 77° et 109° : azimut fin à mesurer sur place
- `poteau_reseau_12888048898` (position_fusion, incertain) : correction fusion revue_requise de 1.814 m (triangulation) ; cohérence v3 : hypothèse confirmée par Q1 (pnx:119d9094), non relue par une revue adverse (> 0,30 m); aucune mesure str
- `arbre_229` (conflit:validite_2026_douteuse, conflit) : CF-ENR-105 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (MLY-CON-020, FUS-VAL-03) ; validité 2026 ince
- `arbre_230` (conflit:validite_2026_douteuse, conflit) : CF-ENR-106 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (MLY-CON-021, MLY-CON-022, FUS-VAL-03) ; valid
- `poteau_reseau_12888048898` (conflit:deplacement_non_etaye, conflit) : CF-ENR-036 : deplacement de 1.81 m proposé ; aucune mesure stricte (FUS-COUV-02) ; mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02) — re

**S5** — refuge (TPC) de Verdun SO (6)

- `ML-5252` (marque_hors_chaussee, conflit) : 13% hors chaussée (débord 0.034 m), source gam : bordure, limite de chaussée ou marque à revoir
- `ML-5253` (marque_hors_chaussee, conflit) : 4% hors chaussée (débord 0.019 m), source gam : bordure, limite de chaussée ou marque à revoir
- `mat_camera_SW_TPC` (position_fusion, incertain) : correction fusion revue_requise de 1.59 m (triangulation); aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines); aucune mesure stricte (FUS-COUV-02)
- `ADD-SPEC-J5_SO` (hypothese_spec, incertain) : panneaux.json décrit J5_SO (J5), absent de mobilier.geojson
- `mat_camera_SW_TPC` (conflit:coherence_desaccord, conflit) : CF-ENR-027 : cohérence : deplacement de 0.05 m ; image à 1.58 m de la position corrigée et 1.59 m de l'origine (partiel) — position image prioritaire si la décision de fusion est «
- `mat_camera_SW_TPC` (conflit:deplacement_non_etaye, conflit) : CF-ENR-035 : deplacement de 1.59 m proposé ; aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines) ; aucune mesure stricte (FUS-COUV-02) — revue visuelle

**N8** — station à créer en (-71 ; +96) : hors de portée de S1-S15 (5)

- `ENR-ARB-005` (ajout:arbre, proposition_rejetee) : type ambigu (souche_ou_massif)
- `ENR-MAR-015` (ajout, schema) : ajout instanciable par la fusion non intégré : type ilot_peint_ocre : paramètres de modulation ou d'aplat non observés
- `ENR-MAR-020` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Point : forme du marquage inconnue (polygone ou trait à relever)
- `potelet_12462947806` (position_fusion, incertain) : correction fusion revue_requise de 1.969 m (pixel_ortho); une seule source non triangulée et pas de correction affirmée; aucune mesure stricte (FUS-COUV-02)
- `potelet_12462947806` (conflit:deplacement_non_etaye, conflit) : CF-ENR-038 : deplacement de 1.97 m proposé ; une seule source non triangulée et pas de correction affirmée ; aucune mesure stricte (FUS-COUV-02) — revue visuelle des planches avant

**N10** — station à créer en (+125 ; -97) : hors de portée de S1-S15 (4)

- `arbre_071` (conflit:validite_2026_douteuse, conflit) : CF-ENR-103 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-197, FUS-VAL-04). aucun arbre au point de arbre_071 (« h 5 m ») sur le parvis e
- `S-0374b` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `S-0374c` (attribut:materiau_id, incertain) : mise à jour materiau_id en revue (FUS-ATT-06)
- `arbre_034` (anomalie_surface, conflit) : objet prouvé sur une surface de classe batiment : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 7.

**N11** — station à créer en (-94 ; -32) : hors de portée de S1-S15 (4)

- `ENR-MAR-008` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie MultiPoint : forme du marquage inconnue (polygone ou trait à relever)
- `ENR-MAR-009` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Polygon : forme du marquage inconnue (polygone ou trait à relever)
- `lamp_12758859672` (conflit:validite_2026_douteuse, conflit) : CF-ENR-119 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-06-07) (MLY-CON-026, ORTHO-B-061, FUS-VAL-03). aucun 
- `lamp_12887274334` (conflit:validite_2026_douteuse, conflit) : CF-ENR-121 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-10-25) (MLY-CON-027, ORTHO-B-151, FUS-VAL-03). massif

**N9** — station à créer en (+62 ; +22) : hors de portée de S1-S15 (4)

- `arbre_247` (attribut:essence, incertain) : mise à jour essence en revue (FUS-ATT-06)
- `MF-5092` (fleche_voie_non_bornee, incertain) : flèche gardée (voie_non_bornee, écart None m ; None) : bords de voie à vérifier
- `MF-5109` (fleche_voie_non_bornee, incertain) : flèche gardée (voie_non_bornee, écart None m ; None) : bords de voie à vérifier
- `cloture_gam_049` (conflit:validite_2026_douteuse, conflit) : CF-ENR-118 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2025-12-01) (VISION-PANORAMAX-1-64, VISION-PANORAMAX-1-65,

**N12** — station à créer en (-16 ; +138) : hors de portée de S1-S15 (3)

- `ML-0187` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source ortho2022 : bordure, limite de chaussée ou marque à revoir
- `ML-0189` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source ortho2022 : bordure, limite de chaussée ou marque à revoir
- `ML-0190` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source ortho2022 : bordure, limite de chaussée ou marque à revoir

**N13** — station à créer en (+28 ; +92) : hors de portée de S1-S15 (3)

- `ML-0197` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source ortho2022 : bordure, limite de chaussée ou marque à revoir
- `ML-0198` (marque_hors_chaussee, conflit) : 100% hors chaussée (débord 1.0 m), source ortho2022 : bordure, limite de chaussée ou marque à revoir
- `S-0094a` (conflit:surface_a_decouper, conflit) : CF-ENR-057 : surface de 11598 m² (espace_vert, gazon_tondu) contenant des sous-zones observées : gazon_tondu (ORTHO-B-039); enrobe_bbsg_ancien (ORTHO-B-099) — découper le polygone 

**N14** — station à créer en (-139 ; +51) : hors de portée de S1-S15 (3)

- `ENR-CLO-001` (ajout:cloture, proposition_rejetee) : σ 1.614 m > 0.5 m (classe point)
- `K-0227` (conflit:deplacement_non_etaye, conflit) : CF-ENR-030 : translation de 0.87 m proposée ; géométrie levée GAM : translation > 0,5 m (FUS-POS-06) — revue visuelle avant application
- `K-0227` (position_fusion, incertain) : translation 0.868 m (revue_requise) : géométrie levée GAM : translation > 0,5 m (FUS-POS-06)

**N15** — station à créer en (-109 ; +24) : hors de portée de S1-S15 (3)

- `arbre_257` (conflit:validite_2026_douteuse, conflit) : CF-ENR-107 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-161, FUS-VAL-04). aucun arbre en 2022 aux points de arbre_257 et arbre_258 (« h
- `arbre_258` (conflit:validite_2026_douteuse, conflit) : CF-ENR-108 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-161, FUS-VAL-04). aucun arbre en 2022 aux points de arbre_257 et arbre_258 (« h
- `S-0161a` (conflit:surface_a_decouper, conflit) : CF-ENR-059 : surface de 10647 m² (parking, enrobe_bbsg_ancien) contenant des sous-zones observées : gravier (ORTHO-B-077); eau_bassin (ORTHO-B-149) — découper le polygone dans la d

**S2** — angle E, Verdun NE × Vercors (3)

- `arbre_224` (position_fusion, incertain) : correction fusion revue_requise de 7.823 m (coordonnees_inventaire, triangulation); σ fusion 1.87 m > 0,5 m; σ fusion 1.87 m > preuve de la description (0.05 m); objet levé GAM : d
- `ADD-BTN-MP-5191-a` (tete_feu, incertain) : OSM node/1959022976 button_operated=yes sur le passage MP-5191 : boîtier à 1,0 m sur feu_NE_SE_pietons, face vers le passage
- `arbre_224` (conflit:deplacement_non_etaye, conflit) : CF-ENR-031 : deplacement de 7.82 m proposé ; σ fusion 1.87 m > 0,5 m ; σ fusion 1.87 m > preuve de la description (0.05 m) ; objet levé GAM : déplacement > 0,5 m (FUS-POS-06) — rev

**S6** — refuge (TPC) de Verdun NE (3)

- `MT-0563` (attribut:etat, incertain) : mise à jour etat en revue (FUS-ATT-06)
- `MT-8002` (raccourcissement, proposition_rejetee) : raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité
- `ADD-BTN-MP-5191-b` (tete_feu, incertain) : OSM node/1959022976 button_operated=yes sur le passage MP-5191 : boîtier à 1,0 m sur feu_NE_TPC, face vers le passage

**sans position** — position inconnue (3)

- `BEV-0348-2` (conflit:lien_introuvable, conflit) : CF-ENR-044 : id BEV-0348-2 absent de la description courante et sans équivalent spatial — relancer l'atelier après régénération de la description ou relier à la main
- `surf_0246` (attribut:classe, schema) : entité v1 surf_0246 absente de la description 0.3 (valeur 'terrain_de_sport')
- `surf_0246` (attribut:materiau_id, schema) : entité v1 surf_0246 absente de la description 0.3 (valeur 'resine_sport_verte')

**N16** — station à créer en (-48 ; +71) : hors de portée de S1-S15 (2)

- `arbre_308` (violation_physique, proposition_rejetee) : déplacement par la règle de 1.80 m (GEN-01, VEG-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier
- `lamp_9530354517` (position_fusion, conflit) : correction fusion appliquer de 1.2 m (pixel_ortho) non appliquée : mesure du 2022-05-10 non valable pour l'état 2026 de l'objet (2026 confirmé); 

**N17** — station à créer en (+138 ; +22) : hors de portée de S1-S15 (2)

- `arbre_236` (conforme_non_verifiable, incertain) : « conforme » non vérifiable sur image
- `arbre_269` (conflit:validite_2026_douteuse, conflit) : CF-ENR-109 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0196, FUS-VAL-04). terre nue de chantier à la position en 05/2022 (hors de la c

**N18** — station à créer en (-146 ; -53) : hors de portée de S1-S15 (2)

- `ENR-MAR-002` (ajout, schema) : ajout instanciable par la fusion non intégré : type bande_centrale_hachuree : paramètres de modulation ou d'aplat non observés
- `ENR-MAR-003` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Polygon : forme du marquage inconnue (polygone ou trait à relever)

**N19** — station à créer en (-57 ; -114) : hors de portée de S1-S15 (2)

- `ENR-MAR-021` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Point : forme du marquage inconnue (polygone ou trait à relever)
- `lamp_13539965051` (conflit:validite_2026_douteuse, conflit) : CF-ENR-122 : absence (ou retrait proposé) non probante pour 2026 : image antérieure à la première attestation de l'objet (2026-02-10) (MLY-CON-028, ORTHO-B-141, FUS-VAL-03). grand 

**N20** — station à créer en (+82 ; -129) : hors de portée de S1-S15 (2)

- `MP-0370` (conflit:validite_2026_douteuse, conflit) : CF-ENR-099 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0181, FUS-VAL-04). en 05/2022 l'emplacement est un terrain de chantier (terre, 
- `S-0461d` (attribut:classe, incertain) : mise à jour classe en revue (FUS-ATT-06)

**N21** — station à créer en (+131 ; -136) : hors de portée de S1-S15 (1)

- `arbre_019` (anomalie_surface, conflit) : objet prouvé sur une surface de classe batiment : surface à corriger par le propriétaire de surfaces.py ; preuve forte (gam, σ 0.05 m) sur batiment de classe peu sûre (d bordure 8.

**N22** — station à créer en (-50 ; +148) : hors de portée de S1-S15 (1)

- `arbre_462` (existence, incertain) : « conforme » non vérifiable (revue v3 n° 27) : mai 2022 : pelouse visible au point, branches claires couchées autour de (−49,5 ; 150,5) : indice d'abattage après le LiDAR 2021 ; or

**N23** — station à créer en (-99 ; +88) : hors de portée de S1-S15 (1)

- `portail_12462947807` (conforme_non_verifiable, incertain) : « conforme » non vérifiable sur image

**N24** — station à créer en (-131 ; -115) : hors de portée de S1-S15 (1)

- `ML-0935` (absence_projection_lointaine, incertain) : absence vue seulement en projection à 18.8 m de la caméra : trait fin possiblement invisible

**N25** — station à créer en (-149 ; -146) : hors de portée de S1-S15 (1)

- `ENR-MAR-001` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Point : forme du marquage inconnue (polygone ou trait à relever)

**N26** — station à créer en (-44 ; +30) : hors de portée de S1-S15 (1)

- `ENR-MAR-027` (ajout, schema) : ajout instanciable par la fusion non intégré : géométrie Polygon : forme du marquage inconnue (polygone ou trait à relever)

**N27** — station à créer en (+52 ; +133) : hors de portée de S1-S15 (1)

- `arbre_435` (conflit:validite_2026_douteuse, conflit) : CF-ENR-112 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO_A-0178, FUS-VAL-04). pelouse ouverte (en partie à l'ombre des arbres voisins au N

**N28** — station à créer en (-67 ; -1) : hors de portée de S1-S15 (1)

- `lamp_12758894668` (conflit:validite_2026_douteuse, conflit) : CF-ENR-120 : absence (ou retrait proposé) non probante pour 2026 : validité 2026 incertaine (ORTHO-B-062, FUS-VAL-04). rien au point décrit (bord de la serre) en 2022 ; nœud OSM 20

**N29** — station à créer en (-95 ; +142) : hors de portée de S1-S15 (1)

- `ENR-SUR-001` (ajout:surface, schema) : surface observée : la partition des surfaces appartient à surfaces.py (hôte S-0269b)

### Propositions rejetées (extrait)

| entité | nature | origine | motif | station |
|---|---|---|---|---|
| `arbre_093` | violation_physique | proposition_rejetee | déplacement par la règle de 1.25 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (bande_cyclable, classe faible) à vérifier | S8 |
| `arbre_110` | violation_physique | proposition_rejetee | déplacement par la règle de 1.35 m (GEN-01, VEG-01) sans mesure ni revue : objet ou surface (piste_cyclable, classe sûre) à vérifier | S14 |
| `arbre_173` | violation_physique | proposition_rejetee | déplacement par la règle de 0.70 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (piste_cyclable, classe faible) à vérifier | S15 |
| `arbre_308` | violation_physique | proposition_rejetee | déplacement par la règle de 1.80 m (GEN-01, VEG-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N16 |
| `arbre_413` | violation_physique | proposition_rejetee | déplacement par la règle de 0.50 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N3 |
| `MF-0774` | conflit_surface_marquage | conflit | flèche plan2025 entièrement hors des surfaces roulables (avant 0.0, recalée 0.0) : conflit surface / marquage, aucun recalage ; surface ou flèche à vérifier | S4 |
| `MF-6017` | recalage_fleche | proposition_rejetee | recalage non appliqué : bords non représentatifs : K-0626 absent en travers de la tête | S14 |
| `MF-6021` | recalage_fleche | proposition_rejetee | recalage non appliqué : voie bornée seulement par OpenDRIVE (voie OpenDRIVE 2/-2) | S14 |
| `ML-5141` | absence_anterieure_contre_2026 | conflit | retrait vu(e) avant la fin des travaux (avant_travaux_hors_emprise) contre un marquage levé GAM 2026 | S9 |
| `MT-8002` | raccourcissement | proposition_rejetee | raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité | S6 |
| `MT-8005` | raccourcissement | proposition_rejetee | raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité | S7 |
| `MT-8006` | raccourcissement | proposition_rejetee | raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité | S7 |
| `MZ-5002` | absence_anterieure_contre_2026 | conflit | retrait vu(e) avant la fin des travaux (avant_travaux_hors_emprise) contre un marquage levé GAM 2026 | S9 |
| `corbeille_12328578845` | violation_physique | proposition_rejetee | déplacement par la règle de 0.25 m (GEN-01, MOB-01) sans mesure ni revue : objet ou surface (parking, classe faible) à vérifier | N3 |
| `feu_VERC_ilot` | violation_physique | proposition_rejetee | déplacement par la règle de 0.40 m (FEU-02, FEU-07, GEN-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | S7 |
| `lamp_9514828418` | violation_physique | proposition_rejetee | déplacement par la règle de 0.15 m (ECL-01, GEN-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N4 |
| `lamp_9530354517` | position_fusion | conflit | correction fusion appliquer de 1.2 m (pixel_ortho) non appliquée : mesure du 2022-05-10 non valable pour l'état 2026 de l'objet (2026 confirmé);  | N16 |
| `lamp_9665416717` | position_fusion | conflit | correction fusion appliquer de 0.876 m (pixel_ortho) non appliquée : Q1 : desaccord avec les photos décisives de la planche ; revue_adverse_coherence_v3 n° 36 : juste;  | S9 |
| `pan_B1_1` | attribut:azimut_deg | conflit | azimut fusion 45.0° contre azimut 125.0° de la cohérence v3 (revue de cohérence : azimut origine) | S9 |
| `pan_B2a_1` | attribut:azimut_deg | conflit | azimut fusion 45.0° contre azimut 15.5° de la cohérence v3 | S9 |
| `portail_13827066643` | violation_physique | proposition_rejetee | déplacement par la règle de 0.30 m (BAR-03, GEN-09) sans mesure ni revue : objet ou surface (batiment, classe sûre) à vérifier | S10b |
| `poteau_incendie_9577881491` | violation_physique | proposition_rejetee | déplacement par la règle de 0.70 m (GEN-01, RES-03) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N3 |
| `poteau_reseau_13624544994` | violation_physique | proposition_rejetee | déplacement par la règle de 0.45 m (GEN-01, RES-02) sans mesure ni revue : objet ou surface (parking, classe faible) à vérifier | S3 |
| `potelet_13827066657` | violation_physique | proposition_rejetee | déplacement par la règle de 0.45 m (GEN-01, POT-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | S10b |
| `stationnement_velos_10265340447` | violation_physique | proposition_rejetee | déplacement par la règle de 0.40 m (GEN-01) sans mesure ni revue : objet ou surface (bande_cyclable, classe faible) à vérifier | S14 |

## Fichiers

- `description_scene_v2.json` : manifeste 0.3 (couches et sha256, `statistiques.resolution`, références des entrées).
- `base/` : familles du schéma 0.3 (copies identiques à l'octet quand aucune décision ne les touche).
- `objets/` : objets résolus et ajouts.
- `journal_resolution.json` : décisions appliquées (avant / après, observations, règles, revue, seconde lecture, confiance, comparaison avec r1), entités non résolues (motif, origine, station), décisions confirmées, comparaison avec la résolution r1 (`comparaison_r1`), verdicts des revues v3, v2, v1 et secondes lectures.
- `modifications.geojson`, `non_resolus.geojson` : couches de contrôle (L93).
- `historique/journal_resolution_r1.json` : journal figé de la résolution précédente (référence de comparaison).
- `planches/` : planches avant / après (locales, ignorées par git).
