# Description résolue du carrefour Paquet Jardin (état octobre 2026)

Base de description 0.3 + seulement les décisions prouvées de la fusion 0.3 et de la cohérence v2, arbitrées par les revues adverses. Commande : `python recon/pcg/decrire/resoudre.py` (`--sans-planches`, `--sans-validation`, `--forcer`). Déterministe : deux exécutions donnent des fichiers identiques à l'octet. Ni `base/`, ni le paquet, ni `enrichi/`, ni `coherence/` ne sont modifiés.

## Utiliser la description résolue

- **Houdini** : dans `pj::lire_description`, régler le paramètre **Dossier de la description (`dossier`)** sur `<dépôt>/recon/out/paquet_jardin/v2/description/resolue/base` au lieu de `.../description/base` (dans la scène maîtresse : `PJ_DESCRIPTION=<dépôt>/recon/out/paquet_jardin/v2/description/resolue/base`). Le lecteur y trouve les cinq familles, `nivellement.json` et `nivellement_grille.npz`, et lit le manifeste `resolue/description_scene_v2.json` (dossier parent). Les marquages retirés portent `fabrication.statut = non_fabrique` : ils sont exclus par défaut (paramètre « Garder les marquages non fabriqués »).
- **Objets** (non lus par `pj::lire_description`) : `resolue/objets/mobilier.geojson` et `arbres.geojson` ont le schéma du paquet (`x_local`, `y_local`, `z_local`, `instancier`, `statut_2026`…) plus une propriété `resolution`. Pour les consommer, pointer la constante `OBJETS` de `recon/pcg/ue/vegetation/arbres.py` (et `PAQUET/donnees/objets` de `recon/pcg/ue/contexte/preparer_usd.py`) vers `resolue/objets` (modification à faire par leur propriétaire). Un objet porté (`porte_par`, `instancier_fut = false`) ne doit pas recevoir de fût propre. `vegetation_ajouts.geojson` (haies, massifs) et `ponctuels_sol_ajouts.geojson` (tampons, avaloirs) sont nouveaux.
- **Validation** : `python recon/pcg/decrire/valider.py recon/out/paquet_jardin/v2/description/resolue` : 0 erreur, 88 avertissements (identiques à ceux de la base). Entités remises à l'état de base par la garde de validation : aucune.
- **Empreintes** : hash_description 1bb443ecaf000e47cdb9e375b40d9cc89cd74812b74276b3b28eaf67634ad8ee (base : 7a869e6aa1656d45280500abb158036da103e3021ed5a74de5882c8ed221c584).
- **Chaîne** (RES-CHN-001) : cohérence et fusion ont lu la base courante.

## Règles de résolution

- **RES-SRC-001** : Priorité des preuves : double lecture d'une revue > fusion stricte (FUS-COUV-02) > décision de cohérence jugée juste par la revue adverse > règle de conception appliquée à un objet déduit > base. Une décision qu'une revue juge « faux » n'est jamais appliquée.
- **RES-CHN-001** : Chaîne : enrichi/ et coherence/ doivent avoir lu la base courante (sha256 des fichiers de base) ; sinon la résolution s'arrête (option --forcer pour un essai).
- **RES-EXI-001** : Retrait ou absence 2026 prouvés strictement par la fusion (statut a_retirer / absent_2026, observation stricte) : marquage -> fabrication non_fabrique ; objet -> instancier false. Bordure : non appliqué (références de partition), listé pour le propriétaire de bordures.py.
- **RES-EXI-002** : Garde temporelle : une absence vue seulement avant la fin des travaux (05/12/2025) ne retire ni une entité posée ou refaite en 2025, ni une entité levée GAM 2026 : conflit listé.
- **RES-EXI-003** : Absence relevée par une revue adverse sur photos 2026 calées et confirmée par une seconde lecture (P16) : instancier false ; à intégrer comme constat de revue (FUS-ARB-01) par le propriétaire de la fusion.
- **RES-EXI-004** : absent_2026_a_verifier (FUS-EXI-04) et non-instanciations de la cohérence jugées incertaines : entité gardée telle que la base, listée.
- **RES-EXI-005** : Absence ou retrait portés seulement par des projections photo à plus de 15 m de la caméra (FUS-VAL-02) : un trait fin peut y être invisible ; non appliqué, listé (cas MLY-MAR-017 de la critique de couverture).
- **RES-POS-001** : Mesure de position (fusion « appliquer » ou cohérence « mesure ») appliquée si la revue adverse la juge juste ; non revue : seulement une triangulation ou une ombre corroborée de déplacement ≤ 0,30 m (sous le seuil de double lecture P16), sans drapeau.
- **RES-POS-002** : Mesure pixel_ortho d'un objet haut (mât, poteau) : appliquée seulement si elle est corroborée (revue juste, départ d'ombre, triangulation) (Q7) ; une mesure rejetée par la cohérence pour sa date n'est pas appliquée.
- **RES-POS-003** : Revue « faux » : rien n'est appliqué. Revue « incertain » : seules les composantes que la revue déclare prouvées ou plausibles (ex. azimut) sont appliquées.
- **RES-POS-004** : Déplacement par la règle sans mesure : appliqué à un objet déduit ou en projet (règles dures pour les a priori, P7) dans le budget de sa source ; pour un objet existant, seulement si une revue l'a jugé juste ; sinon listé comme violation physique non tranchée (objet ou surface à vérifier).
- **RES-POS-005** : Groupe de support (membres_groupe) : une seule décision pour le mât ; fusion de supports prouvée (P5) : un seul fût instancié, l'autre objet est porté.
- **RES-POS-006** : Statut temporel : un objet existant déplacé de plus de 1 m par une mesure postérieure aux travaux passe en « déplacé lors des travaux 2025 » (Q8).
- **RES-ORI-001** : Réorientation appliquée si la revue la juge juste ou plausible, ou si l'azimut source est absent (complétion par la règle, confiance faible).
- **RES-ORI-002** : Tête de feu : réorientation par la règle fonctionnelle (FEU-05/06/07/09) appliquée si l'azimut source est une valeur de saisie (multiple de 45°) et l'écart ≤ 60° ; sinon gardée et listée.
- **RES-ATT-001** : Attribut : mise à jour de la fusion « appliquer » (FUS-ATT-06) si la confiance de la valeur est au moins moyenne, si l'attribut existe dans la famille et si la valeur est dans son domaine (enum du schéma 0.3, table des matériaux, types d'arbres du paquet) ; un azimut qui contredit de plus de 20° l'azimut résolu ou gardé par la cohérence est un conflit ; sinon listée.
- **RES-BOR-001** : Vue ou profil de bordure contestés (FUS-BOR-03) : jamais appliqués sans relevé ; listés avec la station.
- **RES-MQ-001** : Flèche recentrée (MQ-FLE-006) : flèche non levée GAM, non retirée, voie bornée par deux limites décrites (bordure ou ligne, pas OpenDRIVE seule), aucune bordure ni ligne ne coupe la boîte de la flèche (marge 0,10 m), empreinte recalée entièrement roulable (surfaces v2), revue non « faux » (Q5).
- **RES-MQ-002** : Marque au-delà de l'arête avant d'une bordure (MQ-DET-010, TQ-MQG-014) : la partie au-delà de l'intersection vérifiée avec la bordure devient une interruption (géométrie inchangée).
- **RES-MQ-003** : Ajout de marquage : trait isolé (LineString) observé en confiance ≥ moyenne, σ ≤ 0,10 m, source représentable dans src_marquage (gam, plan2025, ortho2022), sans doublon à 0,3 m ; sinon listé.
- **RES-ADD-001** : Ajout d'objet : instancier vrai dans la fusion (FUS-ADD-03), preuve stricte probante (après travaux, ou avant travaux hors emprise, ou dans l'emprise avec appui), confiance ≥ moyenne, σ ≤ seuil de la classe, type non ambigu (« _ou_ ») ; surfaces : jamais (partition de surfaces.py).
- **RES-ADD-002** : Tampons et avaloirs : écrits dans objets/ponctuels_sol_ajouts.geojson (identifiants TAM-/AVA- et ancrage du schéma) tant que la table des matériaux du schéma 0.3 n'a pas de fonte (materiau_id obligatoire de ponctuels_sol) ; à verser dans base/ponctuels_sol.geojson quand le propriétaire du schéma l'aura ajoutée.
- **RES-NRE-002** : Présence 2026 non testée : objet instancié à moins de 25 m d'une photo 2026 calée sans preuve stricte postérieure aux travaux ; listé pour un test de présence sur vignette (Q4 de la revue adverse).
- **RES-NRE-001** : Non résolu : toute entité en conflit ou incertaine reste telle que la base et est listée avec la station terrain la plus proche (PROTOCOLE_TERRAIN.md) ou une station à créer.

## Modifications appliquées

279 modifications appliquées ; 304 entités ou propositions non résolues.

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
| marquages | flèches recentrées dans leur voie | 4 |
| marquages | marquages retirés (non fabriqués) | 23 |
| mobilier | ajouts | 31 |
| mobilier | attributs mis à jour | 11 |
| mobilier | déplacements | 32 |
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
| fleche | flèches recentrées dans leur voie | 4 |
| fleche | marquages retirés (non fabriqués) | 1 |
| haie | ajouts | 3 |
| ilot | attributs mis à jour | 1 |
| lampadaire | ajouts | 2 |
| lampadaire | attributs mis à jour | 6 |
| lampadaire | déplacements | 7 |
| ligne | ajouts | 10 |
| ligne | marques arrêtées à l'arête des bordures | 2 |
| ligne | attributs mis à jour | 8 |
| ligne | marquages retirés (non fabriqués) | 22 |
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
| poteau_reseau | déplacements | 2 |
| refuge | attributs mis à jour | 1 |
| support_feux | déplacements | 10 |
| symbole | attributs mis à jour | 4 |
| tampon | ajouts | 36 |
| transversale | marques arrêtées à l'arête des bordures | 3 |
| trottoir | attributs mis à jour | 4 |

### Déplacements et réorientations d'objets

| objet | classe | décision | d (m) / azimut | conf. | règles | revue |
|---|---|---|---|---|---|---|
| `arbre_013` | feuillu | non_instancie_absent_2026 |  | moyenne | FUS-COUV-02, FUS-DATE-01, FUS-EXI-01, FUS-STAT-01, RES-EXI-001 |  |
| `arbre_015` | feuillu | non_instancie_absent_2026 |  | moyenne | FUS-COUV-02, FUS-DATE-01, FUS-EXI-01, FUS-STAT-01, RES-EXI-001 |  |
| `arbre_027` | feuillu | non_instancie_absent_2026 |  | moyenne | RES-EXI-003, RES-SRC-001 | revue_adverse_coherence_v2 n° 30 : faux |
| `arbre_028` | feuillu | non_instancie_absent_2026 |  | moyenne | RES-EXI-003, RES-SRC-001 | revue_adverse_coherence_v2 n° 27 : faux |
| `arbre_167` | arbre | deplacement | 0.05 | faible | RES-POS-004 |  |
| `arbre_175` | feuillu | non_instancie_absent_2026 |  | moyenne | FUS-COUV-02, FUS-EXI-01, FUS-EXI-03, FUS-STAT-01, RES-EXI-001 |  |
| `arbre_180` | arbre | deplacement | 0.05 | faible | RES-POS-004 |  |
| `arbre_181` | arbre | deplacement | 0.30 | faible | RES-POS-004 |  |
| `arbre_195` | arbre | deplacement | 0.20 | faible | RES-POS-004 |  |
| `arbre_196` | arbre | deplacement | 0.40 | faible | RES-POS-004 |  |
| `arbre_396` | arbre | deplacement | 1.60 | faible | RES-POS-004, RES-SRC-001 | revue_adverse_coherence_v1 : juste |
| `abri_NO_0021` | abri_bus | deplacement | 0.85 | faible | RES-POS-004 |  |
| `feu_NE_TPC` | support_feux | deplacement | 0.19 | moyenne | RES-POS-001 |  |
| `feu_NE_droite` | support_feux | deplacement | 0.36 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 14 : juste |
| `feu_REV_E_pietons` | support_feux | deplacement | 0.07 | moyenne | RES-POS-001 |  |
| `feu_REV_droite` | support_feux | deplacement | 0.16 | moyenne | RES-POS-001 |  |
| `feu_SW_NO_pietons` | support_feux | deplacement | 0.35 | faible | RES-POS-004 |  |
| `feu_SW_TPC` | support_feux | deplacement | 0.05 | faible | RES-POS-004 |  |
| `feu_SW_cycles_NO` | support_feux | deplacement | 0.05 | faible | RES-POS-004 |  |
| `feu_SW_cycles_SE` | support_feux | deplacement | 0.10 | faible | RES-POS-004 |  |
| `feu_VERC_O_pietons` | support_feux | deplacement | 0.11 | faible | RES-POS-004 |  |
| `feu_VERC_droite` | support_feux | deplacement | 0.26 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 16 : juste |
| `lamp_12668578865` | lampadaire | deplacement | 1.63 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 5 : juste |
| `lamp_12668620636` | lampadaire | deplacement | 1.83 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 4 : juste |
| `lamp_12894130974` | lampadaire | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 17 : juste |
| `lamp_9514795519` | lampadaire | deplacement | 1.20 | faible | RES-POS-004 |  |
| `lamp_9514825221` | lampadaire | deplacement | 1.17 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 8 : juste |
| `lamp_9514828517` | lampadaire | deplacement | 0.70 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 9 : juste |
| `lamp_9665416817` | lampadaire | deplacement | 0.58 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 15 : juste |
| `mat_camera_9831317323` | mat_camera | deplacement | 1.12 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 12 : juste |
| `mat_camera_9831317323` | mat_camera | support_commun |  | moyenne | RES-POS-005 | revue_adverse_coherence_v2 n° 12 : juste |
| `pan_AB3a_1` | panneau | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 17 : juste |
| `pan_AB3a_2` | panneau | reorientation | 342.0 -> 15.5 | faible | RES-ORI-001, RES-POS-003 | revue_adverse_coherence_v2 n° 3 : incertain |
| `pan_AB3a_3` | panneau | deplacement | 4.15 | moyenne | RES-POS-001, RES-POS-006, RES-SRC-001 | revue_adverse_coherence_v2 n° 2 : juste |
| `pan_AB4_2` | panneau | deplacement | 0.92 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 7 : juste |
| `pan_B21a1_2` | panneau | deplacement | 0.05 | faible | RES-POS-004 |  |
| `pan_B21a1_3` | panneau | deplacement | 0.15 | faible | RES-POS-004 |  |
| `pan_B2a_1` | panneau | reorientation | 342.0 -> 15.5 | faible | RES-ORI-001, RES-POS-003 | revue_adverse_coherence_v2 n° 3 : incertain |
| `pan_B6a1_1` | panneau | deplacement | 0.68 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 9 : juste |
| `pan_C113_1` | panneau | deplacement | 0.09 | moyenne | RES-POS-001 |  |
| `pan_C113_1` | panneau | reorientation | 225.0 -> 65.0 | moyenne | RES-ORI-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 1 : juste |
| `pan_C114_1` | panneau | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 17 : juste |
| `pan_C13a_1` | panneau | deplacement | 0.68 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 9 : juste |
| `pan_J5_1` | panneau | deplacement | 0.93 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 6 : juste |
| `pan_M9_1` | panneau | deplacement | 0.30 | moyenne | RES-POS-001, RES-SRC-001 | revue_adverse_coherence_v2 n° 17 : juste |
| `pan_M9_2` | panneau | reorientation | 342.0 -> 15.5 | faible | RES-ORI-001, RES-POS-003 | revue_adverse_coherence_v2 n° 3 : incertain |
| `poteau_bois_NE` | poteau_reseau | deplacement | 0.18 | moyenne | RES-POS-001 |  |
| `poteau_bois_REV_ilot` | poteau_reseau | deplacement | 0.12 | moyenne | RES-POS-001 |  |
| `poteau_incendie_4587565593` | poteau_incendie | reorientation | None -> 54.0 | faible | RES-ORI-001 |  |
| `poteau_incendie_5948977094` | poteau_incendie | reorientation | None -> 268.7 | faible | RES-ORI-001 |  |

### Marquages

| marquage | classe | décision | preuve |
|---|---|---|---|
| `MF-0286` | fleche | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO-B-102 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `MF-0769` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (bordure K-0402 | ligne ML-0799) : écart -0.188 m corrigé ; aucune limite dans la boîte, empreinte 100 % roulable |
| `MF-6013` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (bordure K-0627 | ligne ML-5297) : écart -0.325 m corrigé ; aucune limite dans la boîte, empreinte 100 % roulable |
| `MF-6017` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (bordure K-0626 | ligne ML-5298) : écart -0.188 m corrigé ; aucune limite dans la boîte, empreinte 100 % roulable |
| `MF-6018` | fleche | flèches recentrées dans leur voie | flèche centrée dans sa voie (ligne ML-5298 | bordure K-0381) : écart -0.162 m corrigé ; aucune limite dans la boîte, empreinte 100 % roulable |
| `ML-0102` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0008 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0106` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0009 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0107` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO-B-211 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0112` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0068 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0113` | ligne | marques arrêtées à l'arête des bordures | 1.24 m de marque au-delà de l'arête avant de K-0233 rendus non peints (géométrie inchangée) |
| `ML-0121` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0084 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0131` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0051 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0132` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0052 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0133` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0053 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0135` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0054 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0148` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0092 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0150` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0093 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0151` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0094 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0161` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0106 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0162` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0107 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0163` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0108 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0168` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0109 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0201` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0010 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0202` | ligne | marquages retirés (non fabriqués) | absent en 2026 : preuve stricte ORTHO-B-208 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0208` | ligne | marques arrêtées à l'arête des bordures | 0.47 m de marque au-delà de l'arête avant de K-0230 rendus non peints (géométrie inchangée) |
| `ML-0225` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0095 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0226` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO_A-0096 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0432` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte PANO2026-004 (photo_2026, apres_travaux) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-0930` | ligne | marquages retirés (non fabriqués) | retiré : preuve stricte ORTHO-B-206 (ortho_2022, avant_travaux_hors_emprise) ; fusion_recensement/0.3, RES-EXI-001 |
| `ML-7000` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7001` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7002` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7003` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7004` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7005` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7006` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7007` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7008` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `ML-7009` | ligne | ajouts | trait de place (ligne_place_stationnement) observé sur l'ortho 2022 hors emprise des travaux, σ 0.1 m |
| `MT-0563` | transversale | marques arrêtées à l'arête des bordures | 0.10 m de marque au-delà de l'arête avant de K-0386z rendus non peints (géométrie inchangée) |
| `MT-8000` | transversale | marques arrêtées à l'arête des bordures | 0.19 m de marque au-delà de l'arête avant de K-0388, K-0627 rendus non peints (géométrie inchangée) |
| `MT-8001` | transversale | marques arrêtées à l'arête des bordures | 0.19 m de marque au-delà de l'arête avant de K-0388, K-0627 rendus non peints (géométrie inchangée) |

## Planches avant / après (15 changements les plus significatifs)

Fond : ortho PCRS 5 cm du 2022-05-10 ; jaune : arêtes avant des bordures 2026 ; rouge : avant ; cyan : après. Mosaïque : `planches/00_index.jpg`. Les planches contiennent une imagerie tierce : elles restent locales.

| # | entité | décision | planche |
|---|---|---|---|
| 1 | `pan_AB3a_3` | deplacement | `planches/01_pan_AB3a_3_deplacement.jpg` |
| 2 | `pan_C113_1` | reorientation | `planches/02_pan_C113_1_reorientation.jpg` |
| 3 | `arbre_013` | non_instancie_absent_2026 | `planches/03_arbre_013_non_instancie_absent_2026.jpg` |
| 4 | `arbre_015` | non_instancie_absent_2026 | `planches/04_arbre_015_non_instancie_absent_2026.jpg` |
| 5 | `arbre_027` | non_instancie_absent_2026 | `planches/05_arbre_027_non_instancie_absent_2026.jpg` |
| 6 | `MF-6013` | recalage_fleche | `planches/06_MF-6013_recalage_fleche.jpg` |
| 7 | `ML-0121` | retrait | `planches/07_ML-0121_retrait.jpg` |
| 8 | `lamp_12668620636` | deplacement | `planches/08_lamp_12668620636_deplacement.jpg` |
| 9 | `ML-0113` | arret_a_l_arete | `planches/09_ML-0113_arret_a_l_arete.jpg` |
| 10 | `lamp_12668578865` | deplacement | `planches/10_lamp_12668578865_deplacement.jpg` |
| 11 | `arbre_396` | deplacement | `planches/11_arbre_396_deplacement.jpg` |
| 12 | `MF-0769` | recalage_fleche | `planches/12_MF-0769_recalage_fleche.jpg` |
| 13 | `lamp_9514795519` | deplacement | `planches/13_lamp_9514795519_deplacement.jpg` |
| 14 | `lamp_9514825221` | deplacement | `planches/14_lamp_9514825221_deplacement.jpg` |
| 15 | `pan_J5_1` | deplacement | `planches/15_pan_J5_1_deplacement.jpg` |

Lecture des planches (agent RÉSOLUTION) :

- #01 `pan_AB3a_3` : 2022 : un poteau et son ombre au point avant (A) ; le point après (C) tombe dans le contour 2026 du refuge I-0658 (jaune), comme sur les photos 2026 : déplacement cohérent avec les travaux.
- #02 `pan_C113_1` : poteau inchangé (0,09 m) ; la face passe de 225° (vers le SO) à 65° (vers le NE), sens confirmé par la revue.
- #03 `arbre_013` : fond 2022 antérieur : seule la photo 2026 (PANO2026-026) prouve l'absence ; la croix tombe sur la pelouse au bord d'une ombre d'arbre voisin.
- #04 `arbre_015` : fond 2022 antérieur : l'absence vient de PANO2026-027 ; le point est sur la bande enherbée.
- #05 `arbre_027` : un petit arbre est visible en 2022 au point levé ; absent sur les trois photos 2026 calées (revue et relecture) : abattu après 2022.
- #06 `MF-6013` : la flèche glisse de 0,33 m vers sa droite et reste entre K-0627 et ML-5297 ; le marquage visible en 2022 est l'ancien (non probant pour une flèche neuve 2025).
- #07 `ML-0121` : le « trait » suit exactement l'arête du toit du bâtiment : artefact de détection, retrait justifié.
- #08 `lamp_12668620636` : le point après est au centre de la jardinière ronde où part l'ombre du mât ; le point avant (OSM) est dans les places de stationnement.
- #09 `ML-0113` : la marque est arrêtée à l'arête de K-0233 (1,24 m non peints, en rouge) ; elle court dans l'ombre portée du bâtiment : son existence n'est pas jugée ici.
- #10 `lamp_12668578865` : le point après est sur le disque clair de la lanterne d'où part l'ombre fine vers le NNO ; le point avant tombe sur une voiture garée.
- #11 `arbre_396` : déplacement de 1,6 m sous la couronne : la position du tronc n'est pas lisible sur l'ortho ; sens jugé juste par la revue v1 (ampleur minimale).
- #12 `MF-0769` : recentrage de 0,19 m dans la voie bornée par K-0402 et ML-0799, empreinte entièrement sur la chaussée.
- #13 `lamp_9514795519` : objet déduit 2026 : le fond 2022 (avant travaux) ne le montre pas ; sortie de 1,2 m de la bande cyclable décrite, confiance faible, à vérifier sur place.
- #14 `lamp_9514825221` : le point après est au pied SSE de l'unique ombre de mât, contre les images claires de la lanterne et du boîtier caméra ; le point avant est 1,2 m plus au NNO sur l'ombre.
- #15 `pan_J5_1` : le point après est sur le nez du TPC (contour jaune), 0,93 m plus loin que le point avant.

## Ce qui reste non résolu

| famille | origine | n |
|---|---|---|
| ajouts | proposition_rejetee | 7 |
| ajouts | schema | 5 |
| arbres | incertain | 19 |
| arbres | proposition_rejetee | 5 |
| arbres | schema | 1 |
| bordures | conflit | 25 |
| bordures | incertain | 1 |
| bordures | schema | 2 |
| ilots | incertain | 1 |
| marquages | conflit | 31 |
| marquages | incertain | 25 |
| marquages | proposition_rejetee | 8 |
| marquages | schema | 20 |
| mobilier | conflit | 4 |
| mobilier | incertain | 31 |
| mobilier | proposition_rejetee | 11 |
| objets | conflit | 40 |
| objets | incertain | 14 |
| surfaces | conflit | 27 |
| surfaces | incertain | 25 |
| surfaces | schema | 2 |

Origines : `conflit` (sources contradictoires), `incertain` (preuve insuffisante ou revue « incertain »), `proposition_rejetee` (proposition de la fusion ou de la cohérence refusée par une règle RES), `schema` (non représentable dans le schéma 0.3), `validation` (retirée par la garde de validation).

### Par station terrain

| station | lieu | n | natures principales | exemples |
|---|---|---|---|---|
| S9 | parcours rive SE de Verdun NE | 29 | conflit 7, marque_hors_chaussee 5, position 4, attribut 4 | `K-0185`, `MF-5042`, `MF-5043`, `MF-6000`, `MF-6003`, `ML-5140` … |
| S13 | débouché des Mitaillères | 28 | conflit 8, ajout 5, anomalie_surface 4, presence_2026_non_testee 3 | `ENR-PON-066`, `arbre_006`, `arbre_016`, `arbre_017`, `arbre_049`, `K-0511` … |
| N1 | station à créer en (-96 ; -114) : hors de portée de S1-S15 | 20 | conflit 7, attribut 5, ajout 3, vue_intervalle_0 2 | `K-0118`, `K-0298`, `K-0675`, `ENR-MAR-006`, `ENR-MAR-007`, `ENR-MAR-011` … |
| N2 | station à créer en (+72 ; -92) : hors de portée de S1-S15 | 16 | attribut 8, ajout 3, conflit 2, retrait 2 | `ENR-SUR-005`, `ENR-SUR-006`, `ENR-SUR-007`, `arbre_101`, `arbre_134`, `arbre_135` … |
| S7 | îlot du Vercors | 15 | orientation_tete 5, attribut 4, raccourcissement 2, marque_hors_chaussee 1 | `I-0390`, `MP-5189`, `MT-8005`, `MT-8006`, `MZ-5189`, `feu_VERC_droite_t1` … |
| N3 | station à créer en (-122 ; +122) : hors de portée de S1-S15 | 14 | violation_physique 3, conflit 3, ajout 2, anomalie_surface 2 | `ENR-MOB-002`, `arbre_413`, `ENR-MAR-004`, `ML-0115`, `armoire_1313238971`, `barriere_levante_12462947804` … |
| N4 | station à créer en (-16 ; -132) : hors de portée de S1-S15 | 13 | presence_2026_non_testee 8, ajout 2, violation_physique 1, attribut 1 | `ENR-MOB-013`, `arbre_004`, `arbre_005`, `arbre_025`, `ENR-MAR-030`, `boite_aux_lettres_12887274328` … |
| S4 | angle O, Verdun SO × Revirée | 13 | absence_projection_lointaine 2, conflit 2, anomalie_surface 2, marque_hors_chaussee 1 | `MF-0774`, `ML-0238`, `ML-0240`, `lamp_lidar_SW_NO`, `poteau_reseau_12888056356`, `ADD-SPEC-plaque_mat_3150` … |
| S14 | parcours Verdun SO | 12 | anomalie_surface 4, violation_physique 2, recalage_fleche 2, existence 1 | `arbre_109`, `arbre_110`, `MF-6020`, `MF-6021`, `ML-5302`, `lamp_9514795817` … |
| S15 | parcours rive est du Vercors | 12 | fleche_leve_ecart_garde 3, conflit 2, ajout 1, presence_2026_non_testee 1 | `ENR-PAN-012`, `arbre_050`, `arbre_173`, `MF-5524`, `MF-5525`, `MF-5527` … |
| S12 | parcours de la Revirée | 11 | hypothese_spec 4, existence 3, attribut 1, orientation_tete 1 | `arbre_260`, `feu_REV_droite_t4`, `pan_D21_1`, `pan_D21_2`, `pan_J5_2`, `ADD-ILOT-poteau_bois_REV_ilot` … |
| N5 | station à créer en (+92 ; +57) : hors de portée de S1-S15 | 10 | attribut 3, fleche_voie_non_bornee 2, surface_a_corriger 2, anomalie_surface 2 | `arbre_296`, `arbre_334`, `MF-5096`, `MF-5097`, `ML-5136`, `cloture_gam_047` … |
| S11 | arc de bordures (50-67 ; 98-105) | 9 | conflit 7, attribut 2 | `K-0078`, `K-0081`, `K-0082`, `K-0083`, `K-0084`, `K-0085` … |
| N6 | station à créer en (+134 ; +97) : hors de portée de S1-S15 | 8 | conflit 2, anomalie_surface 2, attribut 1, marque_hors_chaussee 1 | `arbre_412`, `ML-5139`, `ADD-ILOT-arbre_397`, `arbre_362`, `arbre_383`, `ADD-SURF-arbre_398` … |
| S10b | sortie de la voie privée des Saules Blancs | 8 | attribut 3, violation_physique 2, conflit 1, position 1 | `MS-5129`, `portail_13827066643`, `potelet_13827066657`, `potelet_13827066658`, `S-0415j`, `S-0415n` … |
| S3 | angle S, Vercors × Verdun SO | 7 | attribut 3, conflit 2, marque_hors_chaussee 1, violation_physique 1 | `MP-5282`, `MZ-5282`, `poteau_reseau_13624544994`, `arbre_184`, `cloture_gam_001` |
| N7 | station à créer en (+90 ; -38) : hors de portée de S1-S15 | 6 | conflit 2, anomalie_surface 2, vue_intervalle_3 1, vue_intervalle_0 1 | `K-0435`, `K-0439`, `arbre_188`, `arbre_189` |
| S5 | refuge (TPC) de Verdun SO | 6 | marque_hors_chaussee 2, conflit 2, position_fusion 1, hypothese_spec 1 | `ML-5252`, `ML-5253`, `mat_camera_SW_TPC`, `ADD-SPEC-J5_SO` |
| S8 | quais La Revirée, Verdun SO | 6 | conflit 2, ajout 1, violation_physique 1, position_fusion 1 | `ENR-SUR-002`, `arbre_093`, `banc_8360664518`, `cloture_gam_002`, `arbre_194` |
| N8 | station à créer en (-71 ; +96) : hors de portée de S1-S15 | 5 | ajout 3, position_fusion 1, conflit 1 | `ENR-ARB-005`, `ENR-MAR-015`, `ENR-MAR-020`, `potelet_12462947806` |
| S1 | angle N, Revirée × Verdun NE | 5 | conflit 3, ajout 1, position_fusion 1 | `ENR-VEG-002`, `poteau_reseau_12888048898`, `arbre_229`, `arbre_230` |
| N10 | station à créer en (+125 ; -97) : hors de portée de S1-S15 | 4 | attribut 2, conflit 1, anomalie_surface 1 | `arbre_071`, `S-0374b`, `S-0374c`, `arbre_034` |
| N11 | station à créer en (-94 ; -32) : hors de portée de S1-S15 | 4 | ajout 2, conflit 2 | `ENR-MAR-008`, `ENR-MAR-009`, `lamp_12758859672`, `lamp_12887274334` |
| N9 | station à créer en (+62 ; +22) : hors de portée de S1-S15 | 4 | fleche_voie_non_bornee 2, attribut 1, conflit 1 | `arbre_247`, `MF-5092`, `MF-5109`, `cloture_gam_049` |
| N12 | station à créer en (-16 ; +138) : hors de portée de S1-S15 | 3 | marque_hors_chaussee 3 | `ML-0187`, `ML-0189`, `ML-0190` |
| N13 | station à créer en (+28 ; +92) : hors de portée de S1-S15 | 3 | marque_hors_chaussee 2, conflit 1 | `ML-0197`, `ML-0198`, `S-0094a` |
| N14 | station à créer en (-139 ; +51) : hors de portée de S1-S15 | 3 | ajout 1, conflit 1, position_fusion 1 | `ENR-CLO-001`, `K-0227` |
| N15 | station à créer en (-109 ; +24) : hors de portée de S1-S15 | 3 | conflit 3 | `arbre_257`, `arbre_258`, `S-0161a` |
| S2 | angle E, Verdun NE × Vercors | 3 | position_fusion 1, tete_feu 1, conflit 1 | `arbre_224`, `ADD-BTN-MP-5191-a` |
| S6 | refuge (TPC) de Verdun NE | 3 | attribut 1, raccourcissement 1, tete_feu 1 | `MT-0563`, `MT-8002`, `ADD-BTN-MP-5191-b` |
| sans position | position inconnue | 3 | attribut 2, conflit 1 | `BEV-0348-2`, `surf_0246` |
| N16 | station à créer en (-48 ; +71) : hors de portée de S1-S15 | 2 | violation_physique 1, position_fusion 1 | `arbre_308`, `lamp_9530354517` |
| N17 | station à créer en (+138 ; +22) : hors de portée de S1-S15 | 2 | conforme_non_verifiable 1, conflit 1 | `arbre_236`, `arbre_269` |
| N18 | station à créer en (-146 ; -53) : hors de portée de S1-S15 | 2 | ajout 2 | `ENR-MAR-002`, `ENR-MAR-003` |
| N19 | station à créer en (-57 ; -114) : hors de portée de S1-S15 | 2 | ajout 1, conflit 1 | `ENR-MAR-021`, `lamp_13539965051` |
| N20 | station à créer en (+82 ; -129) : hors de portée de S1-S15 | 2 | conflit 1, attribut 1 | `MP-0370`, `S-0461d` |
| N21 | station à créer en (+131 ; -136) : hors de portée de S1-S15 | 1 | anomalie_surface 1 | `arbre_019` |
| N22 | station à créer en (-99 ; +88) : hors de portée de S1-S15 | 1 | conforme_non_verifiable 1 | `portail_12462947807` |
| N23 | station à créer en (-131 ; -115) : hors de portée de S1-S15 | 1 | absence_projection_lointaine 1 | `ML-0935` |
| N24 | station à créer en (-149 ; -146) : hors de portée de S1-S15 | 1 | ajout 1 | `ENR-MAR-001` |
| N25 | station à créer en (-44 ; +30) : hors de portée de S1-S15 | 1 | ajout 1 | `ENR-MAR-027` |
| N26 | station à créer en (+52 ; +133) : hors de portée de S1-S15 | 1 | conflit 1 | `arbre_435` |
| N27 | station à créer en (-67 ; -1) : hors de portée de S1-S15 | 1 | conflit 1 | `lamp_12758894668` |
| N28 | station à créer en (-95 ; +142) : hors de portée de S1-S15 | 1 | ajout 1 | `ENR-SUR-001` |

Les stations S1 à S15 sont celles de `recon/pcg/enrichir/PROTOCOLE_TERRAIN.md` (portée 30 m pour une station, 15 m pour un parcours) ; N1, N2… sont des stations à créer (couverture gloutonne de 30 m des entités hors de portée).

### Propositions rejetées (extrait)

| entité | nature | origine | motif | station |
|---|---|---|---|---|
| `arbre_093` | violation_physique | proposition_rejetee | déplacement par la règle de 1.25 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (bande_cyclable, classe faible) à vérifier | S8 |
| `arbre_110` | violation_physique | proposition_rejetee | déplacement par la règle de 1.35 m (GEN-01, VEG-01) sans mesure ni revue : objet ou surface (piste_cyclable, classe sûre) à vérifier | S14 |
| `arbre_173` | violation_physique | proposition_rejetee | déplacement par la règle de 0.70 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (piste_cyclable, classe faible) à vérifier | S15 |
| `arbre_308` | violation_physique | proposition_rejetee | déplacement par la règle de 1.80 m (GEN-01, VEG-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N16 |
| `arbre_413` | violation_physique | proposition_rejetee | déplacement par la règle de 0.50 m (GEN-01, VEG-01, VEG-06) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N3 |
| `MF-0774` | recalage_fleche | proposition_rejetee | recalage non appliqué : empreinte recalée roulable à 0% seulement ; revue « faux » : flèche et recalage à 100 % sur la classe trottoir : conflit surface / marquage, pas u | S4 |
| `MF-6020` | recalage_fleche | proposition_rejetee | recalage non appliqué : voie bornée seulement par OpenDRIVE (voie OpenDRIVE 2/-1) | S14 |
| `MF-6021` | recalage_fleche | proposition_rejetee | recalage non appliqué : voie bornée seulement par OpenDRIVE (voie OpenDRIVE 2/-2) | S14 |
| `MF-8000` | recalage_fleche | proposition_rejetee | recalage non appliqué : voie coupée : bordure K-0415 dans la boîte de la flèche (marge 0.1 m) ; empreinte recalée roulable à 36% seulement ; revue « faux » : la bordure K | S15 |
| `ML-5141` | absence_anterieure_contre_2026 | conflit | retrait vu(e) avant la fin des travaux (avant_travaux_hors_emprise) contre un marquage levé GAM 2026 | S9 |
| `MT-8002` | raccourcissement | proposition_rejetee | raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité | S6 |
| `MT-8005` | raccourcissement | proposition_rejetee | raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité | S7 |
| `MT-8006` | raccourcissement | proposition_rejetee | raccourcissement non vérifié : debut : aucune bordure croisée dans les 0.80 m d'extrémité | S7 |
| `MZ-5002` | absence_anterieure_contre_2026 | conflit | retrait vu(e) avant la fin des travaux (avant_travaux_hors_emprise) contre un marquage levé GAM 2026 | S9 |
| `corbeille_12328578845` | violation_physique | proposition_rejetee | déplacement par la règle de 0.25 m (GEN-01, MOB-01) sans mesure ni revue : objet ou surface (parking, classe faible) à vérifier | N3 |
| `feu_VERC_ilot` | violation_physique | proposition_rejetee | déplacement par la règle de 0.40 m (FEU-02, FEU-07, GEN-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | S7 |
| `lamp_9514828418` | violation_physique | proposition_rejetee | déplacement par la règle de 0.15 m (ECL-01, GEN-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N4 |
| `lamp_9530354517` | position_fusion | conflit | correction fusion appliquer de 1.2 m (pixel_ortho) non appliquée : mesure du 2022-05-10 non valable pour l'état 2026 de l'objet (2026 confirmé);  | N16 |
| `lamp_9665416717` | position | proposition_rejetee | déplacement de 0.88 m non appliqué : revue « faux » | S9 |
| `lamp_9665416717` | position_fusion | conflit | correction fusion appliquer de 0.876 m (pixel_ortho) non appliquée : revue « faux »;  | S9 |
| `pan_B1_1` | attribut:azimut_deg | conflit | azimut fusion 45.0° contre azimut 125.0° de la cohérence v2 (revue de cohérence : azimut origine) | S9 |
| `pan_B2a_1` | attribut:azimut_deg | conflit | azimut fusion 45.0° contre azimut 15.5° de la cohérence v2 | S9 |
| `portail_13827066643` | violation_physique | proposition_rejetee | déplacement par la règle de 0.30 m (BAR-03, GEN-09) sans mesure ni revue : objet ou surface (batiment, classe sûre) à vérifier | S10b |
| `poteau_incendie_9577881491` | violation_physique | proposition_rejetee | déplacement par la règle de 0.70 m (GEN-01, RES-03) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | N3 |
| `poteau_reseau_13624544994` | violation_physique | proposition_rejetee | déplacement par la règle de 0.45 m (GEN-01, RES-02) sans mesure ni revue : objet ou surface (parking, classe faible) à vérifier | S3 |
| `potelet_13827066657` | violation_physique | proposition_rejetee | déplacement par la règle de 0.45 m (GEN-01, POT-01) sans mesure ni revue : objet ou surface (chaussee, classe faible) à vérifier | S10b |
| `stationnement_velos_10265340447` | violation_physique | proposition_rejetee | déplacement par la règle de 0.40 m (GEN-01) sans mesure ni revue : objet ou surface (bande_cyclable, classe faible) à vérifier | S14 |

## Fichiers

- `description_scene_v2.json` : manifeste 0.3 (couches et sha256, `statistiques.resolution`, références des entrées).
- `base/` : familles du schéma 0.3 (copies identiques à l'octet quand aucune décision ne les touche).
- `objets/` : objets résolus et ajouts.
- `journal_resolution.json` : décisions appliquées (avant / après, observations, règles, revue, confiance) et entités non résolues (motif, origine, station).
- `modifications.geojson`, `non_resolus.geojson` : couches de contrôle (L93).
- `planches/` : planches avant / après (locales).
