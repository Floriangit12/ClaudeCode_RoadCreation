#!/usr/bin/env python3
"""Fusion du recensement (ortho 2022, orthos 2024-2025, Panoramax 2020-2026, Mapillary, web) avec la description v2.

Entrées (lues, jamais modifiées) :
  recon/out/paquet_jardin/v2/enrichi/recensement/obs_*.json (tous, ordre alphabétique), web/obs_web.json
  recon/out/paquet_jardin/v2/description/enrichi/arbitrages_fusion.json (décisions de revue, FUS-ARB-01)
  recon/out/paquet_jardin/v2/description/base/*.geojson (v0.3, régénérée en parallèle : lue telle quelle)
  recon/out/paquet_jardin/v2/description/coherence/{corrections.geojson, propositions_ajouts.geojson,
      rapport_coherence.json, carte/bordures_site.geojson}
  recon/out/paquet_jardin/package/donnees/objets/{mobilier.geojson, arbres.geojson, instances.json}
  recon/out/paquet_jardin/package/donnees/surfaces/surfaces_2026.geojson, relief/relief_zones_2026.geojson
  data/sites/paquet_jardin/etat_2026/arbre_pct_L93.geojson (levé GAM 2026), panoramax_pictures.geojson,
  data/sites/paquet_jardin/ortho5cm_2022/*.jpg (fond de carte)

Sorties (couche séparée, fusionnée plus tard par le composeur) :
  recon/out/paquet_jardin/v2/description/enrichi/
    attributs.geojson, ajouts.geojson, corrections_position.geojson, conflits.json,
    entites_verifiees.json, observations_index.json, couverture.json, couverture_preuves.png, RESUME.md

Déterministe : aucun aléa, itérations triées, flottants arrondis. Chaque décision cite ses
observations (id) et la règle FUS-* appliquée (table REGLES ci-dessous, recopiée dans RESUME.md).

0.3 : couverture large (FUS-COUV-01) et stricte (FUS-COUV-02, seule utilisée pour décider) ; classes de date relatives
aux travaux avec appui de règle (FUS-DATE-02) et zone des travaux étendue par les photos 2026 (FUS-ZONE-01) ; validité
incertaine jamais preuve de présence (FUS-VAL-04) ; liens groupés (FUS-LIEN-09) ; contrôles automatiques des bordures
(FUS-AUTO-01/02) ; vote de la vue, du profil et des abaissés de bordure (FUS-BOR-01..03) ; arbitrages
invalider_observation et constat_revue (FUS-ARB-01).

Usage : python recon/pcg/enrichir/fusion_recensement.py [--sans-carte]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

VERSION = "fusion_recensement/0.3"
ROOT = Path(__file__).resolve().parents[3]
DESC = ROOT / "recon/out/paquet_jardin/v2/description"
BASE = DESC / "base"
COH = DESC / "coherence"
OUT = DESC / "enrichi"
RECENS = ROOT / "recon/out/paquet_jardin/v2/enrichi/recensement"
PKG = ROOT / "recon/out/paquet_jardin/package/donnees"
SITE = ROOT / "data/sites/paquet_jardin"
ARBITRAGES = OUT / "arbitrages_fusion.json"
POSES_2026 = RECENS / "pano_2026/poses/poses_2026-07-28.json"
MLY_IMAGES = ROOT / "data/raw/mapillary/paquet_jardin/images.json"

# tous les fichiers d'observations du recensement (ordre alphabétique : déterministe), puis le web
FICHIERS_OBS = sorted(RECENS.glob("obs_*.json")) + [RECENS / "web/obs_web.json"]

FIN_TRAVAUX = "2025-12-05"   # travaux du cœur 23/06-05/12/2025 (trottoirs du Vercors jusqu'au 30/01/2026)
# catégories de preuve, de la plus récente à la plus ancienne (FUS-DATE-01) ; tranche = colonne de la couverture
CATEGORIES = ["photo_2026", "photo_2025", "ortho_2025", "photo_2020_2024", "ortho_2024", "ortho_2022", "web"]
TRANCHE = {"photo_2026": "2026", "photo_2025": "2025", "ortho_2025": "2025", "photo_2020_2024": "2020_2024",
           "ortho_2024": "2020_2024", "ortho_2022": "ortho_2022", "web": "web"}
TRANCHES = ["2026", "2025", "2020_2024", "ortho_2022", "web", "non_concluant", "non_valable_2026", "aucune"]
PRESENCE = ("confirme", "attribut_corrige", "position_corrigee")
COEUR_DEMI_M = 80.0          # cœur du carrefour : carré ± 80 m autour de l'origine (panneaux C/D de la carte)
RAYON_DEDOUBLONNAGE_M = 1.5  # FUS-ADD-04
# contrat d'un contrôle automatique acceptable (FUS-AUTO-02)
AUTO_PART_MASQUEE_MAX = 0.2
CLASSES_AUTO_REQUALIFIEES = ("marquage", "bordure")   # FUS-AUTO-01 (bordures : critique de couverture, cause 4)
# validité et confiance des projections photo (FUS-VAL-02, FUS-CONF-02)
DIST_DATE_INDEPENDANT_MAX_M = 15.0
DIST_CONFIANCE_MAX_M = 20.0
# classes de date relatives aux travaux (FUS-DATE-02) et zone des travaux (FUS-ZONE-01)
EMPRISE_MARGE_M = 3.0
CLASSES_DATE = ["apres_travaux", "avant_travaux_hors_emprise", "avant_travaux_dans_emprise"]
TRANCHES_STRICTES = CLASSES_DATE + ["indice_seulement", "non_concluant", "non_valable_2026", "aucune"]
# liens groupés (FUS-LIEN-09)
GROUPE_LIENS_MIN = 3
# vote des bordures (FUS-BOR-01..03) : profils de bordures.json (regles_affectation)
CLASSES_VUE = [("P1", 0.0, 0.03), ("A2", 0.03, 0.09), ("T2", 0.09, 0.175), ("T3", 0.175, 0.30), ("MURET_TALUS", 0.30, 9.0)]
TOL_VUE_M = 0.02
FENETRE_BORDURE_M = 5.0     # étendue vue autour du point projeté (FUS-BOR-02/03)
F_LECTURE = {"haute": 1.0, "moyenne": 0.8, "faible": 0.5}
CHAMPS_PROFIL = ("hauteur_vue_estimee_m", "profil_observe", "profil_description", "observe", "observation", "note")
VERDICTS_RETRAIT = ("absent_2026", "retirer", "retirer_doublon", "non_instancier")

# --------------------------------------------------------------------------------------------
# Règles de fusion (citées dans toutes les sorties)
# --------------------------------------------------------------------------------------------
REGLES = {
    "FUS-LIEN-01": "lien_description explicite (ids séparés par « ; ») résolu dans l'index : base v0.3 > mobilier > arbres > instances > bordures_site > surfaces v1 > propositions de cohérence.",
    "FUS-LIEN-02": "marquage absent de la v0.3 mais présent dans marquages_indices_v1 : remappé par lien_v1 -> marquages_correspondance (devenir « genere » -> entité v0.3 ; « retire » -> entité retirée).",
    "FUS-LIEN-03": "surface v0.2 sans suffixe (S-0121) : polygone S-0121* qui contient le point (sinon le plus proche à ≤ 1 m).",
    "FUS-LIEN-04": "autre id introuvable : appariement spatial dans la famille de son préfixe, tolérance de la classe ; sinon conflit lien_introuvable.",
    "FUS-LIEN-05": "liens secondaires (attributs liens / confirmes / arbres_confirmes / arbres) : l'observation vaut pour chaque entité citée (attributs et existence) ; la position ne vaut que pour les liens primaires co-implantés (≤ 1,5 m, même support).",
    "FUS-LIEN-06": "observation sans lien (statut ≠ absent_de_description, précision ≤ 3 m) : entité la plus proche de la famille compatible dans la tolérance de classe.",
    "FUS-CTX-01": "observation de contexte (précision absente ou > 5 m, sous-type chantier / hors emprise / programme / état 2022 remplacé, bâtiment) sans lien : indexée, jamais fusionnée ni ajoutée.",
    "FUS-TMP-01": "objet temporaire (chantier, provisoire, temporaire, base vie, bungalow, affiche) : jamais ajouté ; s'il est lié et que l'image est postérieure à l'attestation de l'objet, existence « non_instancier » (sinon conflit validite_2026_douteuse).",
    "FUS-VAL-01": "poids de validité 2026 : vrai 1 ; incertain 0,5 (attributs et mesures seulement, FUS-VAL-04) ; faux 0 (observation historique, conservée pour la traçabilité).",
    "FUS-VAL-02": "constat indépendant de la date (sous-type faux_positif*, raison « artefact », marquage posé sur une toiture ou un massif) : poids 1 même si valide_2026 = faux, à condition que la projection photo soit vue à 15 m au plus de la caméra (attributs.image.distance_m ; sans limite sur une ortho) ; au-delà, constat ordinaire, que seul un arbitrage de revue (FUS-ARB-01) peut corroborer (critique de couverture : MLY-MAR-017, projection à 25,9 m tombée sur la haie, alors que la photo 2026 montre des places en enrobé).",
    "FUS-VAL-04": "validité 2026 « incertaine » : jamais une preuve de présence ni d'absence (existence, couverture, statut confirmé) ; seuls les attributs et les mesures de position la gardent avec le poids 0,5 (mesures toujours en revue, FUS-POS-05).",
    "FUS-CONF-02": "projection de la description sur une photo prise à plus de 20 m (attributs.image.distance_m) : confiance plafonnée à « faible » (à 20 m, 0,5° d'erreur de pose déplace le tracé de 0,17 m et l'occultation n'est plus lisible ; échecs de la critique au-delà de 20 m).",
    "FUS-DATE-02": "classes de date relatives aux travaux (23/06-05/12/2025 ; trottoirs du Vercors jusqu'au 30/01/2026) : « apres_travaux » (image du 05/12/2025 ou après) ; « avant_travaux_hors_emprise » (image antérieure, entité à plus de 3 m de la zone des travaux FUS-ZONE-01) ; « avant_travaux_dans_emprise » (image antérieure, entité dans la zone ou à 3 m au plus). Les photos de 2025-01 à 2025-08 sont antérieures ou contemporaines du chantier : aucune n'est « après travaux ». Une observation « avant_travaux_dans_emprise » ne vaut (présence, absence, attribut, position) que si une règle appuie la conservation de l'entité pendant les travaux (FUS-SRC-001 de regles_conception, admissibilité par état) : marquage « conserve » ; bordure levée GAM hors du périmètre refait (zone_travaux_2025 faux, hauteur non « modifiee_2025 », à plus de 3 m d'une extension FUS-ZONE-01) ; surface « inchange_2022 » ou « construit_2023_2024 » hors de la zone ; îlot à ceinture levée GAM ; objet ou arbre attesté après les travaux (levé GAM, OSM édité à partir du 01/12/2025, « 2026 confirmé », Panoramax 2026, arbre du levé GAM 2026 à 2 m au plus). Sans appui : présumée conservée, pas prouvée (non probante).",
    "FUS-ZONE-01": "zone des travaux 2025 : surfaces v1 « modifie_2025 », zones de relief reprises (ancienne chaussée rehaussée, traversées abaissées, trottoirs par défaut), et toute surface de la description dont une photo postérieure aux travaux (valide 2026, confiance moyenne ou haute) montre un revêtement neuf (sous-type ou matériau proposé « neuf ») : S-0268a, chaussée du Vercors, enrobé neuf sur PANO2026-034 (critique, cause 5) ; son état devient « modifie_2025 » (mise à jour etat_v1).",
    "FUS-LIEN-09": "photo liée à 3 entités ou plus qui ne sont pas sur le même support (liens primaires non co-implantés et liens secondaires) : seule une entité dont l'identifiant est cité dans la preuve (preuve.note) ou dans le texte de l'observation est prouvée ; pour les autres, le lien devient « vu, non prouvé » (incertain : ni présence, ni attribut, ni couverture) (critique : PANO2026-014 liait 10 places, ses pixels de preuve n'en citent que 3).",
    "FUS-VAL-03": "entité créée après l'image (marquage neuf_2025 ou refait, bordure ou surface modifiée 2025, objet « déduit 2026 » ou « planté 2025 », surface construite 2023-2024) : l'image antérieure ne prouve ni absence ni attribut (poids 0). Une absence ne prouve l'absence 2026 que si la première attestation de l'objet (LiDAR 2021, ortho 2022, OSM daté, inventaire 2023, plan 2025, levé GAM postérieur aux travaux ≈ 2025-12, « 2026 confirmé ») précède l'image ; sinon elle est non probante : signalée (conflit validite_2026_douteuse) sauf si l'observateur la dit attendue (« cohérent avec la description », « comme attendu », « plantations postérieures »...).",
    "FUS-LIEN-07": "observation absent_de_description portant un lien vers une entité d'une autre famille (surface, support, proposition de cohérence) : le lien est l'hôte de l'objet nouveau, l'observation devient candidat d'ajout ; ses liens secondaires sont des « liens associés » sans effet sur les attributs. Même famille (surface sur surface) : constat d'état de l'entité (notes).",
    "FUS-LIEN-08": "ids de la carte de cohérence (KS-xxxx-n) et des surfaces v1 (surf_xxxx) : remappés vers la description de base (K- de même ligne GAM, S- de même lien_v1) au plus proche de la mesure (≤ 2 m / ≤ 1 m).",
    "FUS-ATT-05": "surface de plus de 2 000 m² : une observation ponctuelle ne requalifie pas tout le polygone ; matériaux et classes proposés y deviennent des sous-zones (conflit surface_a_decouper).",
    "FUS-POS-08": "après correction, deux objets de même classe à moins de 0,75 m : conflit doublon_apres_correction (fusion à décider).",
    "FUS-CONF-01": "poids de confiance : haute 1 ; moyenne 0,6 ; faible 0,3 ; contrôle automatique (automatique, automatique_2_dates, automatique_2e_date) x0,7 ; valeur « probable » ou « ? » x0,6.",
    "FUS-POS-01": "mesures de position : triangulation σ = max(préc. ; 0,05) et rayon au sol σ = 2·max(préc. ; 0,30) (tout statut) ; pixel ortho σ = 1,25·max(préc. ; 0,10) seulement pour position_corrigee (ailleurs le pixel peut désigner une lanterne ou une couronne) ; une observation « confirme » sans mesure (projection, pixel ortho) = confirmation à la position décrite, utilisée seulement sans autre mesure (σ = 1,5·max(préc. ; 0,15) en projection) ; pour la pondération, σ divisé par √(poids confiance x validité). Mesures identiques (≤ 1 cm, même méthode) comptées une fois.",
    "FUS-POS-02": "triangulation à angle d'intersection < 15° (lu dans l'observation) : σ x2.",
    "FUS-POS-03": "moyenne pondérée 1/σ², rejet itératif de la mesure au plus fort résidu normalisé (> 3 et > tolérance de classe) -> conflit position_desaccord.",
    "FUS-POS-04": "verdict (README triangulation) : écart d à la description ≤ max(0,35 m ; 3σ), σ de mesure fusionné sans pondération de confiance -> confirmé ; sinon affinage (≤ 0,75 m) ou déplacement (> 0,75 m).",
    "FUS-POS-05": "application : « appliquer » si une mesure valide 2026 (poids 1) existe, σ ≤ 0,5 m, σ ≤ max(σ de la preuve décrite ; 0,30) et (triangulation, ou ≥ 2 sources indépendantes concordantes, ou position_corrigee affirmée par l'observateur en confiance ≥ moyenne) et qu'au moins une mesure est stricte (FUS-COUV-02) ; sinon « revue_requise ».",
    "FUS-POS-06": "objet levé GAM (σ ≤ 0,05 m) : jamais déplacé de plus de 0,5 m sans revue (« revue_requise »).",
    "FUS-POS-07": "ligne ou polygone (marquage, bordure, clôture, BEV) : vecteur du point le plus proche de la géométrie (ou du point « au lieu de (x ; y) » cité) à la mesure ; translation proposée si |v| > max(0,10 m marquage | 0,20 m autre ; 3σ).",
    "FUS-ATT-01": "attributs normalisés par table d'alias (hauteur, couronne, essence, type, crosses, lanternes, azimut de face, code, modulation, couleur, état, usure, gabarit, largeur, matériau, classe, bouton d'appel...). Le texte libre reste en notes.",
    "FUS-ATT-02": "vote pondéré (confiance x validité x contrôle x « probable ») ; catégoriel : valeur de poids maximal ; numérique : moyenne pondérée ; azimut : moyenne circulaire.",
    "FUS-ATT-03": "conflit d'attribut : catégoriel si le 2e poids ≥ 0,5 x le 1er (et ≥ 0,3) ; numérique si l'étendue dépasse max(tolérance absolue ; tolérance relative x moyenne) ; azimut si un vote s'écarte de > 30°.",
    "FUS-ATT-04": "mise à jour émise si poids gagnant ≥ 0,3 et écart à la description au-delà du seuil de l'attribut (valeur absente de la description : ajout d'attribut).",
    "FUS-EXI-01": "existence : présence (confirme, attribut_corrige, position_corrigee) contre absence (absent_sur_image) ; « absent_2026 » si poids absence ≥ 0,6 et ≥ 2 x présence ; conflit si les deux ≥ 0,3.",
    "FUS-EXI-03": "chronologie : quand présence et absence probantes s'opposent, si toutes les absences sont postérieures à toutes les présences, l'objet est absent en 2026 (retiré entre deux prises de vue, absence ≥ 0,6) ; dans le cas inverse il est présent (posé entre deux prises de vue) ; conflit d'information changement_entre_dates.",
    "FUS-EXI-02": "retrait (artefact de la description : faux positif, « à retirer », « à supprimer », doublon) si poids ≥ 0,6 ; retypage (poteau réseau au lieu de lampadaire) si vote explicite ≥ 0,6.",
    "FUS-ADD-01": "ajouts : observations absent_de_description (et candidats incertains non appariés) regroupées par lien simple, même groupe de classe, distance ≤ tolérance + min(σi + σj ; 3 m) entre ateliers différents, ≤ tolérance et même sous-type dans un même atelier.",
    "FUS-ADD-02": "ajout à moins de la moitié de la tolérance d'une entité existante de même famille : conflit ajout_proche_existant, non instancié. Exceptions : sous-zone ou reprise de surface (la surface est son hôte) ; équipement porté (boîtier, plaque, panonceau : le support voisin est son hôte).",
    "FUS-ADD-03": "ajout instancié si au moins une observation valide 2026 (vrai) en confiance ≥ moyenne, non temporaire, famille cible connue ; croisé avec les propositions de cohérence (≤ 3 m) et le levé GAM 2026 des arbres (≤ 2 m).",
    "FUS-COH-01": "contrôle croisé avec coherence/corrections.geojson : accord si la position image est à ≤ max(0,35 ; 2σ) de la position corrigée ; désaccord si elle est à cette distance de la position d'origine seulement ; partiel si elle est loin des deux ; les deux dans la tolérance : tendance_accord / tendance_desaccord si l'écart les départage d'au moins σ, sinon indifférent ; confirmations sans mesure : non concluant ; azimut : accord à ≤ 30° ; propositions d'ajout rejointes par une observation : corroborées (datées).",
    "FUS-SRC-01": "sources : « ortho2022 » (PCRS 5 cm du 10/05/2022) -> ortho_2022 ; « ortho_recente:<couche> » (IGN 20 cm du 09/08/2024 -> ortho_2024 ; Pléiades 2025 non datée, avant travaux -> ortho_2025) ; « pnx: » (Panoramax) et « mly: » (Mapillary) : photos, catégorie selon la date : photo_2026 (≥ 05/12/2025, fin des travaux), photo_2025, photo_2020_2024 ; autres : documents web.",
    "FUS-DATE-01": "priorité photo_2026 : pour l'état 2026, dès qu'une observation photo_2026 de poids > 0 porte sur l'existence, un attribut ou la position d'une entité, elle seule décide de cet aspect ; les observations plus anciennes sont gardées comme antérieures (obs_anterieures_ecartees) ; un désaccord ouvre un conflit d'information changement_2026 ou position_anterieure_divergente (objet déplacé, refait ou retiré pendant les travaux).",
    "FUS-AUTO-01": "confirmation automatique d'un marquage ou d'une bordure sur ortho (contrôles ortho_A / ortho_B 2022, orthos récentes 2024, bordures « automatique_2_dates ») sans contrat FUS-AUTO-02 : requalifiée « incertain » (ni présence, ni preuve de couverture) sauf si une observation manuelle (contrôle visuel ou photo) confirme la même entité avec un poids de présence > 0. Deux contrôles automatiques ne se corroborent pas (erreurs corrélées : voitures garées aux mêmes places, ombres de supports fixes, lignes de places détectées à tort ; bordure K-0236 confirmée sur deux dates sans arête réelle).",
    "FUS-AUTO-02": "contrat de tout contrôle automatique futur : il n'est accepté comme confirmation (poids x0,7) que s'il déclare attributs.controle_auto = {masque_vehicules_ombres: true (taches claires ou sombres de plus de 3 m² et de largeur ≥ 1,2 m, ombres portées), part_masquee ≤ 0,2 le long de l'objet, et pour un marquage reponse_ligne_fine: true (trait de 0,10 à 0,15 m répondant sur toute la longueur) ou reponse_peinture: true (flèche, symbole : part peinte ≥ 0,3) ; pour une bordure reponse_ligne_fine: true (tête de bordure claire de 0,10 à 0,20 m répondant sur toute la longueur) ou reponse_arete: true (saut de luminance de la face vue sur 80 % des profils non masqués)} ; calcul de référence : controle_auto.py ; sinon FUS-AUTO-01 (marquages, bordures) ou drapeau « automatique seul » (autres classes). Un contrôle automatique n'est jamais une preuve stricte (FUS-COUV-02).",
    "FUS-ADD-04": "dédoublonnage des ajouts : entité existante de même classe (type de marquage compatible ; pavés de traversée = passage) dans un rayon max(1,5 m ; tolérance de classe) ; si elle vient d'un levé GAM (marquage, bordure, îlot, arbre, clôture), pas d'ajout : conflit ajout_contre_leve_gam (l'objet vu est probablement l'objet levé, mal placé ou mal typé ; à trancher sur photo 2026 ou terrain). Exception : l'atelier qui signale l'objet a aussi confirmé à la main l'entité levée, sans la retyper (deux objets distingués par le même observateur).",
    "FUS-ARB-01": "arbitrages de revue (description/enrichi/arbitrages_fusion.json, clés = identifiants d'observations, jamais les ENR-* renumérotés) : ne_pas_instancier (ajout), ancrer_bord_ilot (ajout ponctuel ramené au bord de l'îlot ou de l'espace vert le plus proche, en retrait vers l'intérieur), mesure_position (coordonnées d'un document utilisées comme mesure de position, σ donné, pondérée comme FUS-POS-01), invalider_observation (lien d'une observation à une entité rendu « incertain » : erreur de projection, occultation), constat_revue (lecture d'une image par une revue, versée comme observation « REV-… » de l'agent revue, avec sa source, sa date, sa confiance et son drapeau « à vérifier »). Chaque arbitrage cite son motif et sa preuve ; un arbitrage sans effet ouvre un conflit arbitrage_inapplicable.",
    "FUS-COUV-01": "couverture large (définition 0.2, gardée pour comparaison ; aucune décision ne l'utilise) : preuve image la plus récente, valable 2026 et concluante (présence, attribut, position, ou absence probante ; observations « incertain », liens invalidés ou groupés sans preuve propre, confirmations automatiques requalifiées exclues ; confiance faible et validité incertaine admises), par tranche : 2026 > 2025 > 2020-2024 (photos, ortho IGN 2024) > ortho 2022 > web seul ; « non concluant » : vue sans conclusion ; « non valable 2026 » : vue seulement avant sa forme 2026.",
    "FUS-COUV-02": "couverture stricte (décisions) : au moins une observation image manuelle (ni contrôle automatique, ni document web), de confiance moyenne ou haute (après FUS-CONF-02), valide 2026 (vrai, ou constat indépendant de la date FUS-VAL-02), probante après FUS-VAL-03/04 et FUS-DATE-02, non invalidée (FUS-ARB-01) ni liée en groupe sans preuve propre (FUS-LIEN-09), portant sur la présence (confirme, attribut ou position corrigés) ou sur une absence probante. Classée par la meilleure classe de date (FUS-DATE-02) : après travaux > avant travaux hors emprise > avant travaux dans l'emprise avec appui de règle ; sinon « indice seulement » (vue concluante au sens large, sans preuve stricte). Le statut « confirmé », les décisions d'application (position, attribut, retrait) et la carte utilisent cette définition.",
    "FUS-STAT-01": "statut de vérification d'une entité : « confirme » (preuve stricte de présence, sans correction ni contradiction) ; « corrige » (preuve stricte de présence, attribut ou position corrigés) ; « conteste » (preuve stricte de présence, mais attribut contredit : vue de bordure FUS-BOR-03) ; « absent_2026 » ou « a_retirer » (absence ou artefact prouvés strictement) ; « absent_2026_a_verifier » (FUS-EXI-04) ; « indice_seulement » (vue sans preuve stricte) ; « non_valable_2026 » (vue seulement avant sa forme 2026 ou sans appui de règle).",
    "FUS-ATT-06": "décision d'une mise à jour d'attribut : « appliquer » si la valeur gagnante est portée par au moins une observation stricte (FUS-COUV-02) sans conflit d'attribut ; sinon « revue_requise ».",
    "FUS-EXI-04": "absence sans preuve stricte : un retrait ou une absence 2026 qu'aucune observation stricte ne porte, ou dont un constat de revue est marqué « à vérifier », ou une absence vue (poids ≥ 0,3) sans présence ni seuil de retrait, devient « absent_2026_a_verifier » : l'entité est gardée (instancier = null) et un conflit existence_douteuse_2026 est ouvert.",
    "FUS-BOR-01": "lecture des profils de bordure en texte libre (champs hauteur_vue_estimee_m, profil_observe, profil_description, observe, observation, note des observations de présence) : vue chiffrée (« vue ≈ 12–14 cm », « ≈0,13-0,15 m », « vue ≤ 5 cm ») -> intervalle [min ; max] (valeur seule « ≈ x » : x ± 0,02 m), lecture haute ; qualificatif explicite (arasée, à niveau, affleurante, sans vue, aucune bordure saillante) -> [0 ; 0,03 m], lecture moyenne ; « basse » -> [0,03 ; 0,09 m], « bordure de trottoir » -> [0,09 ; 0,175 m], lecture faible ; abaissé (abaissé, bateau, chartière) -> abaissé vrai. Profil déduit de la vue par bordures.json (regles_affectation : P1 < 0,03 ; A2 < 0,09 ; T2 < 0,175 ; T3 < 0,30 m). Une limite sans mot de bordure (pelouse, haie, enrobé, rive) ne vote pas.",
    "FUS-BOR-02": "vote par intervalle de la description : chaque lecture est rapportée à l'abscisse s de l'observation sur la bordure (≤ 3 m) ; poids = confiance x validité (FUS-DATE-02) x lecture (1 ; 0,8 ; 0,5) ; vue observée = moyenne pondérée des milieux ; profil = classe de cette vue ; abaissé : vote contre le rôle de l'intervalle (bateau, chartière). Accord : vue décrite dans l'intervalle lu ± 0,02 m ou même classe de profil -> attribut confirmé.",
    "FUS-BOR-03": "contradiction de vue : intervalle lu qui exclut la vue décrite (± 0,02 m) avec une autre classe de profil (ex. rive « arasée » contre T2 de 8 à 14 cm), poids ≥ 0,15 -> conflit bordure_vue_contradiction (à vérifier), statut « conteste », proposition « revue_requise » (jamais appliquée sans revue : vue mesurée au LiDAR 2021 ou estimée a priori, signalée) ; lectures incompatibles entre elles -> conflit bordure_vue_desaccord.",
}

CONF_W = {"haute": 1.0, "moyenne": 0.6, "faible": 0.3}
SIG_METHODE = {  # (plancher, facteur)
    "triangulation": (0.05, 1.0),
    "pixel_ortho": (0.10, 1.25),
    "rayon_sol": (0.30, 2.0),
    "projection_description": (0.15, 1.5),
}
TOL_CLASSE = {"arbre": 2.0, "candelabre": 1.5, "feu": 1.5, "panneau": 1.5, "potelet": 0.75,
              "mobilier": 1.5, "abri_bus": 2.0, "cloture": 1.0, "tampon": 0.75, "avaloir": 0.75,
              "bev": 1.5, "marquage": 0.5, "bordure": 0.5, "surface": 0.0, "ilot": 0.0,
              "autre_poteau": 1.5, "haie": 2.0, "massif": 2.0, "autre": 1.5, "batiment": 3.0}
TYPES_MOB_DIVERS = {"banc", "corbeille", "armoire", "poteau_incendie", "stationnement_velos", "abri_bus",
                    "poteau_arret", "conteneur_verre", "distributeur", "fontaine", "mobilier_publicitaire",
                    "boite_aux_lettres", "barriere_levante", "chicane", "totem_PR", "panneau_information",
                    "mat_camera"}
FAM_SPATIALE = {
    "arbre": [("arbres", None)],
    "candelabre": [("mobilier", {"lampadaire", "mat_camera", "poteau_reseau"})],
    "autre_poteau": [("mobilier", {"poteau_reseau", "lampadaire"})],
    "feu": [("mobilier", {"support_feux", "mat_camera"})],
    "panneau": [("mobilier", {"panneau", "panneau_information", "totem_PR", "poteau_arret"})],
    "potelet": [("mobilier", {"potelet", "balise_J11", "poteau_incendie"})],
    "mobilier": [("mobilier", TYPES_MOB_DIVERS)],
    "abri_bus": [("mobilier", {"abri_bus", "poteau_arret"})],
    "cloture": [("mobilier", {"cloture", "portail"})],
    "tampon": [("ponctuels_sol", None)], "avaloir": [("ponctuels_sol", None)], "bev": [("ponctuels_sol", None)],
    "marquage": [("marquages", None)],
    "bordure": [("bordures", None), ("bordures_site", None)],
    "surface": [("surfaces", None)],
    "ilot": [("ilots", None)],
}
GROUPE_AJOUT = {"tampon": "ponctuel", "avaloir": "ponctuel", "bev": "ponctuel", "arbre": "arbre",
                "haie": "vegetal", "massif": "vegetal", "marquage": "marquage", "candelabre": "mat",
                "autre_poteau": "mat", "panneau": "panneau", "feu": "feu", "potelet": "potelet",
                "mobilier": "mobilier", "abri_bus": "mobilier", "cloture": "cloture", "surface": "surface",
                "ilot": "surface", "bordure": "bordure", "autre": "autre", "batiment": "autre"}
FAMILLE_CIBLE = {"tampon": "ponctuels_sol.tampon", "avaloir": "ponctuels_sol.avaloir", "bev": "ponctuels_sol.bev",
                 "arbre": "vegetation.arbres", "haie": "vegetation.haies", "massif": "vegetation.massifs",
                 "marquage": "marquages", "candelabre": "mobilier.lampadaire", "autre_poteau": "mobilier.poteau_reseau",
                 "panneau": "signaux.panneaux", "feu": "signaux.feux", "potelet": "mobilier.potelet",
                 "mobilier": "mobilier", "abri_bus": "mobilier.abri_bus", "cloture": "mobilier.cloture",
                 "surface": "surfaces", "ilot": "ilots", "bordure": "bordures", "autre": None, "batiment": None}
CODE_AJOUT = {"ponctuel": "PON", "arbre": "ARB", "vegetal": "VEG", "marquage": "MAR", "mat": "MAT",
              "panneau": "PAN", "feu": "FEU", "potelet": "POT", "mobilier": "MOB", "cloture": "CLO",
              "surface": "SUR", "bordure": "BOR", "autre": "AUT"}
CLASSE_OBS_FUSION = {"arbre": "arbre", "marquage": "marquage", "candelabre": "candelabre_poteau",
                     "autre_poteau": "candelabre_poteau", "panneau": "panneau", "feu": "feu",
                     "potelet": "potelet_borne", "mobilier": "mobilier", "abri_bus": "mobilier",
                     "cloture": "cloture_barriere", "haie": "haie_massif", "massif": "haie_massif",
                     "tampon": "ponctuel_sol", "avaloir": "ponctuel_sol", "bev": "ponctuel_sol",
                     "surface": "surface_ilot", "ilot": "surface_ilot", "bordure": "bordure",
                     "autre": "autre", "batiment": "autre"}
ORDRE_CLASSES = ["arbre", "haie_massif", "marquage", "bordure", "surface_ilot", "ponctuel_sol",
                 "candelabre_poteau", "panneau", "feu", "potelet_borne", "cloture_barriere", "mobilier", "autre"]

RE_CTX = re.compile(r"^(hors_emprise|chantier|programme|itineraire|etat_2022_remplace|parking_pr_hors_emprise|"
                    r"identite_chronovelo|bilan_surfaces|anciens_marquages|base_vie|toiture|jeunes_plantations)")
RE_TMP = re.compile(r"chantier|provisoire|temporaire|base_vie|bungalow|affiche", re.I)
RE_TMP_RAISON = re.compile(r"temporaire|provisoire", re.I)
RE_RETRAIT = re.compile(r"retirer du marquage|entit[ée] à supprimer|à supprimer", re.I)
RE_NE_PAS_INST = re.compile(r"ne pas (l'|les )?instancier(?!\s+(de|d'|en)\b)", re.I)
RE_ABS_COHERENT = re.compile(r"cohérent avec (la description|son statut|leur date)|comme attendu|plantations? postérieures?|"
                             r"posés? après 05/2022|ne peut pas (les|le|la) confirmer", re.I)
GAM_DATE = "2025-12-01"   # levé GAM non daté, postérieur aux travaux 2025 (constats vérifiés)
SURFACE_MAX_PONCTUELLE_M2 = 2000.0
RE_ANGLE = re.compile(r"angle(?:\s+d.intersection)?\s*[≈~]?\s*(\d+(?:[.,]\d+)?)\s*°")
RE_AU_LIEU = re.compile(r"au lieu de \(\s*([-−]?\d+(?:[.,]\d+)?)\s*[;,]\s*([-−]?\d+(?:[.,]\d+)?)\s*\)")
RE_ID = re.compile(r"^(arbre_\d+|lamp_\w+|pan_\w+|M[LFPSZT]-\w+|K-\w+|KS-[\w-]+|S-\w+|I-\d+|surf_\d+|potelet_\w+|"
                   r"poteau_\w+|feu_\w+|cloture_\w+|BEV-[\d-]+|mat_\w+|abri_\w+|armoire_\w+|banc_\w+|corbeille_\w+|"
                   r"totem_\w+|balise_\w+|portail_\w+|chicane_\w+|barriere_\w+|ADD-[\w-]+)$")
COMPAS = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
GENRES = ["Acer", "Aesculus", "Alnus", "Betula", "Carpinus", "Catalpa", "Cedrus", "Celtis", "Cercis", "Fagus",
          "Fraxinus", "Ginkgo", "Gleditsia", "Koelreuteria", "Liquidambar", "Magnolia", "Malus", "Morus", "Picea",
          "Pinus", "Platanus", "Populus", "Prunus", "Pyrus", "Quercus", "Robinia", "Salix", "Sophora", "Sorbus",
          "Taxus", "Thuja", "Tilia", "Ulmus", "Zelkova", "Cupressus", "Laurus", "Photinia", "Ligustrum"]
GENRE_FR = {"cèdre": "Cedrus", "cedre": "Cedrus", "peuplier": "Populus", "platane": "Platanus", "tilleul": "Tilia",
            "érable": "Acer", "erable": "Acer", "chêne": "Quercus", "bouleau": "Betula", "savonnier": "Koelreuteria",
            "troène": "Ligustrum", "laurier": "Laurus", "pin": "Pinus", "saule": "Salix", "charme": "Carpinus"}
COULEURS = ["blanc", "jaune", "ocre", "bleu", "vert", "turquoise", "rouge", "orange"]
ETATS_MQ = ["refait_2025_identique", "neuf_2025", "conserve", "neuf_2023_2025"]
GABARITS = ["TD_TAD", "TD_TAG", "RAB_D", "RAB_G", "TAG", "TAD", "TD"]

# (attribut) -> (type, tolérance absolue, tolérance relative, seuil de mise à jour absolu, relatif)
ATTR_SPEC = {
    "hauteur_m": ("num", 1.0, 0.25, 0.5, 0.15),
    "couronne_m": ("num", 1.5, 0.30, 1.0, 0.20),
    "largeur_m": ("num", 0.03, 0.20, 0.02, 0.0),
    "porte_a_faux_m": ("num", 0.5, 0.30, 0.5, 0.0),
    "diametre_m": ("num", 0.05, 0.20, 0.03, 0.0),
    "epaisseur_m": ("num", 0.5, 0.30, 0.3, 0.0),
    "dimension_m": ("num", 0.2, 0.30, 0.1, 0.0),
    "usure": ("num", 1.0, 0.0, 1.0, 0.0),
    "azimut_deg": ("circ", 30.0, 0.0, 20.0, 0.0),
}

# --------------------------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------------------------

def charger_json(p: Path, essais: int = 3):
    """Lecture tolérante à une réécriture concurrente (la description est régénérée en parallèle)."""
    err = None
    for k in range(essais):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:  # fichier en cours d'écriture
            err = e
            time.sleep(2.0)
    raise RuntimeError(f"lecture impossible : {p} ({err})")


def sha256(p: Path) -> str | None:
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def r3(x):
    return None if x is None else round(float(x), 3)


def fnum(s: str) -> float:
    return float(s.replace(",", ".").replace("−", "-"))


def parse_num(v):
    """Nombre, ou milieu d'un intervalle « a-b » en tête de texte ; None pour « > x », « < x »."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if re.match(r"^\s*[<>≥≤]", s):
            return None
        m = re.match(r"^\s*[≈~]?\s*([-−]?\d+(?:[.,]\d+)?)(?:\s*(?:[-–]|à)\s*([-−]?\d+(?:[.,]\d+)?))?", s)
        if m:
            a = fnum(m.group(1))
            if m.group(2):
                return (a + fnum(m.group(2))) / 2.0
            return a
    return None


def parse_date(s) -> str | None:
    s = str(s or "")
    m = re.search(r"(\d{4})-(\d{2})(?:-(\d{2}))?", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3) or '15'}"
    m = re.search(r"\b(?:19|20)\d{2}\b", s)
    if m:
        return m.group(0) + "-07-01"
    return None


def texte(v) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def court(s: str, n: int = 280) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def angle_diff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def moyenne_circulaire(vals, ws):
    s = sum(w * math.sin(math.radians(v)) for v, w in zip(vals, ws))
    c = sum(w * math.cos(math.radians(v)) for v, w in zip(vals, ws))
    return (math.degrees(math.atan2(s, c)) + 360.0) % 360.0


# ---- géométrie (numpy, sans shapely) ----

def dist_polyligne(p, C):
    """Distance d'un point à une polyligne (n x 2) et point le plus proche."""
    if len(C) == 1:
        d = float(np.hypot(*(p - C[0])))
        return d, C[0].copy()
    A, B = C[:-1], C[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1)
    t = np.where(L2 > 0, ((p - A) * AB).sum(1) / np.where(L2 > 0, L2, 1.0), 0.0).clip(0.0, 1.0)
    Q = A + t[:, None] * AB
    d = np.hypot(p[0] - Q[:, 0], p[1] - Q[:, 1])
    i = int(d.argmin())
    return float(d[i]), Q[i].copy()


def segment_le_plus_proche(p, C):
    """Distance d'un point à une polyligne, point le plus proche et indice du segment."""
    A, B = C[:-1], C[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1)
    t = np.where(L2 > 0, ((p - A) * AB).sum(1) / np.where(L2 > 0, L2, 1.0), 0.0).clip(0.0, 1.0)
    Q = A + t[:, None] * AB
    d = np.hypot(p[0] - Q[:, 0], p[1] - Q[:, 1])
    i = int(d.argmin())
    return float(d[i]), Q[i].copy(), i


def dans_anneau(p, R) -> bool:
    x, y = float(p[0]), float(p[1])
    xi, yi, xj, yj = R[:-1, 0], R[:-1, 1], R[1:, 0], R[1:, 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / np.where(yj - yi == 0, 1e-300, yj - yi) + xi)
    return bool(c.sum() % 2 == 1)


def dans_anneau_multi(P, R):
    """Test point-dans-anneau vectorisé pour un nuage de points (n x 2)."""
    x, y = P[:, 0:1], P[:, 1:2]
    xi, yi, xj, yj = R[:-1, 0][None, :], R[:-1, 1][None, :], R[1:, 0][None, :], R[1:, 1][None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / np.where(yj - yi == 0, 1e-300, yj - yi) + xi)
    return c.sum(1) % 2 == 1


def dist_points_polyligne(P, C):
    """Distance de chaque point d'un nuage (n x 2) à une polyligne."""
    A, B = C[:-1], C[1:]
    AB = B - A
    L2 = (AB ** 2).sum(1)
    t = (((P[:, None, :] - A[None]) * AB[None]).sum(2) / np.where(L2 > 0, L2, 1.0)[None]).clip(0.0, 1.0)
    Q = A[None] + t[..., None] * AB[None]
    return np.hypot(P[:, None, 0] - Q[..., 0], P[:, None, 1] - Q[..., 1]).min(1)


def abscisse(p, C):
    """Distance d'un point à une polyligne et abscisse curviligne s de sa projection."""
    d, q, i = segment_le_plus_proche(p, C)
    seg = np.hypot(*np.diff(C, axis=0).T)
    return d, float(seg[:i].sum() + np.hypot(*(q - C[i])))


# ---- profils de bordure (FUS-BOR-01) ----

def profil_de_vue(v):
    for code, a, b in CLASSES_VUE:
        if a <= v < b:
            return code
    return CLASSES_VUE[-1][0]


def vue_a_abscisse(it, s):
    v0 = float(it.get("vue_m") or 0.0)
    if it.get("vue_m_fin") is None or it["s1"] <= it["s0"]:
        return v0
    t = min(1.0, max(0.0, (s - it["s0"]) / (it["s1"] - it["s0"])))
    return v0 + t * (float(it["vue_m_fin"]) - v0)


def vue_compatible(vd, iv):
    """Vue décrite compatible avec un intervalle lu (± TOL) ou de même classe de profil que son milieu (FUS-BOR-03)."""
    lo, hi = iv
    if lo - TOL_VUE_M <= vd <= hi + TOL_VUE_M:
        return True
    return profil_de_vue(vd) == profil_de_vue((lo + hi) / 2.0)


RE_VUE_CM = re.compile(r"\b(vue|hauteur|ressaut|face)\b([^;]{0,30}?)(≤|<|≈|~)?\s*(\d+(?:[.,]\d+)?)\s*"
                       r"(?:(?:[–-]|à)\s*(\d+(?:[.,]\d+)?))?\s*cm\b", re.I)
RE_VUE_M = re.compile(r"\b(vue|hauteur|face)\b([^;]{0,40}?)(≤|<|≈|~)?\s*(0[.,]\d+)\s*(?:(?:[–-]|à)\s*(0[.,]\d+))?\s*m\b", re.I)
RE_PLAGE_M = re.compile(r"^\s*(≤|<|≈|~)?\s*(\d+[.,]\d+)\s*(?:(?:[–-]|à)\s*(\d+[.,]\d+))?")
RE_ARASEE = re.compile(r"\baras[ée]e?s?\b|à niveau|affleur|sans vue|pas de vue|aucune vue|aucune bordure saillante|"
                       r"non saillante|sans ressaut|pas de ressaut", re.I)
RE_BASSE = re.compile(r"\b(?:bordure|rive)s?\b[^;,()]{0,40}?\bbasses?\b|\bprofil bas\b", re.I)
RE_TROTTOIR = re.compile(r"\bbordures? de trottoir\b", re.I)
RE_ABAISSE = re.compile(r"abaiss|\bbateaux?\b|charti[eè]res?", re.I)
RE_ABAISSE_NON = re.compile(r"\b(?:sans|pas d'|pas de|aucun)\s*(?:abaiss|bateau)", re.I)
RE_SURVEY = re.compile(r"levé|dz_|décrit|description|non vérifiable", re.I)


def _plage(op, a, b, echelle):
    a = fnum(a) * echelle
    if b is not None:
        b = fnum(b) * echelle
        return round(min(a, b), 3), round(max(a, b), 3)
    if op in ("≤", "<"):
        return 0.0, round(a, 3)
    return round(max(0.0, a - TOL_VUE_M), 3), round(a + TOL_VUE_M, 3)


def lire_profil_bordure(attrs):
    """Lectures de vue et d'abaissé dans le texte libre d'une observation de bordure (FUS-BOR-01)."""
    cands, abaisses = [], []
    for k_, champ in enumerate(CHAMPS_PROFIL):
        v = attrs.get(champ)
        if not isinstance(v, str) or not v.strip():
            continue
        s = v.strip()
        if re.search(r"non vérifiable", s, re.I):
            continue
        if champ == "hauteur_vue_estimee_m":
            m = RE_PLAGE_M.match(s)
            if m:
                lo, hi = _plage(m.group(1), m.group(2), m.group(3), 1.0)
                cands.append((0, k_, {"attribut": "vue_m", "min": lo, "max": hi, "lecture": "haute", "champ": champ,
                                      "extrait": court(s, 80)}))
                continue
        trouve = False
        for rx, ech in ((RE_VUE_CM, 0.01), (RE_VUE_M, 1.0)):
            for m in rx.finditer(s):
                if RE_SURVEY.search(m.group(0)):
                    continue
                lo, hi = _plage(m.group(3), m.group(4), m.group(5), ech)
                if hi > 0.6:      # pas une vue de bordure (largeur, distance)
                    continue
                cands.append((0, k_, {"attribut": "vue_m", "min": lo, "max": hi, "lecture": "haute", "champ": champ,
                                      "extrait": court(m.group(0), 80)}))
                trouve = True
                break
            if trouve:
                break
        if not trouve:
            m = RE_ARASEE.search(s)
            if m:
                cands.append((1, k_, {"attribut": "vue_m", "min": 0.0, "max": 0.03, "lecture": "moyenne", "champ": champ,
                                      "extrait": court(s, 110)}))
            else:
                m = RE_BASSE.search(s)
                if m:
                    cands.append((2, k_, {"attribut": "vue_m", "min": 0.03, "max": 0.09, "lecture": "faible", "champ": champ,
                                          "extrait": court(m.group(0), 80)}))
                else:
                    m = RE_TROTTOIR.search(s)
                    if m:
                        cands.append((2, k_, {"attribut": "vue_m", "min": 0.09, "max": 0.175, "lecture": "faible",
                                              "champ": champ, "extrait": court(m.group(0), 80)}))
        if RE_ABAISSE_NON.search(s):
            abaisses.append((k_, {"attribut": "abaisse", "valeur": False, "lecture": "moyenne", "champ": champ,
                                  "extrait": court(RE_ABAISSE_NON.search(s).group(0), 60)}))
        elif RE_ABAISSE.search(s) and not RE_SURVEY.search(s):
            abaisses.append((k_, {"attribut": "abaisse", "valeur": True, "lecture": "moyenne", "champ": champ,
                                  "extrait": court(RE_ABAISSE.search(s).group(0), 60)}))
    out = []
    if cands:
        out.append(sorted(cands, key=lambda c: (c[0], c[1]))[0][2])
    if abaisses:
        out.append(sorted(abaisses, key=lambda c: c[0])[0][1])
    return out


def geom_norm(g):
    """GeoJSON -> {type: point|ligne|poly, pt, lignes, polys, bbox} en L93 2D."""
    if not g:
        return None
    t = g["type"]
    lignes, polys, pts = [], [], []
    if t == "Point":
        pts = [np.array(g["coordinates"][:2], float)]
    elif t == "MultiPoint":
        pts = [np.array(c[:2], float) for c in g["coordinates"]]
    elif t == "LineString":
        lignes = [np.array([c[:2] for c in g["coordinates"]], float)]
    elif t == "MultiLineString":
        lignes = [np.array([c[:2] for c in l], float) for l in g["coordinates"]]
    elif t == "Polygon":
        polys = [[np.array([c[:2] for c in r], float) for r in g["coordinates"]]]
    elif t == "MultiPolygon":
        polys = [[np.array([c[:2] for c in r], float) for r in pg] for pg in g["coordinates"]]
    return construire_geom(pts, lignes, polys)


def construire_geom(pts, lignes, polys):
    allc = [p[None, :] for p in pts] + lignes + [r for pg in polys for r in pg]
    if not allc:
        return None
    A = np.vstack(allc)
    bbox = (float(A[:, 0].min()), float(A[:, 1].min()), float(A[:, 0].max()), float(A[:, 1].max()))
    if polys:
        typ = "poly"
    elif lignes:
        typ = "ligne"
    else:
        typ = "point" if len(pts) == 1 else "multipoint"
    G = {"type": typ, "pts": pts, "lignes": lignes, "polys": polys, "bbox": bbox}
    G["pt"] = point_representatif(G)
    return G


def point_representatif(G):
    if G["type"] == "point":
        return G["pts"][0]
    if G["type"] == "multipoint":
        return np.mean(np.array(G["pts"]), axis=0)
    if G["type"] == "ligne":
        C = max(G["lignes"], key=len)
        seg = np.hypot(*np.diff(C, axis=0).T) if len(C) > 1 else np.array([0.0])
        L = seg.sum()
        if L == 0:
            return C[0]
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        k = int(np.searchsorted(cum, L / 2.0) - 1)
        k = max(0, min(k, len(seg) - 1))
        t = (L / 2.0 - cum[k]) / seg[k] if seg[k] > 0 else 0.0
        return C[k] + t * (C[k + 1] - C[k])
    # polygone : centroïde surfacique de l'anneau extérieur du plus grand polygone
    best, ba = None, -1.0
    for pg in G["polys"]:
        R = pg[0] - pg[0][0]   # coordonnées décalées : évite l'annulation numérique en Lambert-93
        x, y = R[:, 0], R[:, 1]
        a = 0.5 * float(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
        if abs(a) > ba:
            ba, best = abs(a), (R, a, pg[0])
    R, a, R0 = best
    if abs(a) < 1e-9:
        return R0.mean(axis=0)
    x, y = R[:, 0], R[:, 1]
    cr = x[:-1] * y[1:] - x[1:] * y[:-1]
    cx = float(((x[:-1] + x[1:]) * cr).sum() / (6 * a))
    cy = float(((y[:-1] + y[1:]) * cr).sum() / (6 * a))
    return np.array([cx, cy]) + R0[0]


def dist_geom(p, G):
    """Distance d'un point à une géométrie normalisée (0 à l'intérieur d'un polygone) et point le plus proche."""
    best, q = math.inf, None
    for P in G["pts"]:
        d = float(np.hypot(*(p - P)))
        if d < best:
            best, q = d, P
    for pg in G["polys"]:
        if dans_anneau(p, pg[0]) and not any(dans_anneau(p, h) for h in pg[1:]):
            return 0.0, p.copy()
        for R in pg:
            d, qq = dist_polyligne(p, R)
            if d < best:
                best, q = d, qq
    for C in G["lignes"]:
        d, qq = dist_polyligne(p, C)
        if d < best:
            best, q = d, qq
    return best, q


def densifier(G, pas=0.5):
    """Nuage de points d'une géométrie (pour les distances entre géométries)."""
    out = list(G["pts"])
    for C in G["lignes"] + [R for pg in G["polys"] for R in pg]:
        for a, b in zip(C[:-1], C[1:]):
            n = max(1, int(math.ceil(float(np.hypot(*(b - a))) / pas)))
            for k in range(n + 1):
                out.append(a + (b - a) * (k / n))
        if len(C) == 1:
            out.append(C[0])
    return np.array(out) if out else np.zeros((0, 2))


def dist_geoms(G1, G2):
    A, B = densifier(G1), densifier(G2)
    if len(A) == 0 or len(B) == 0:
        return math.inf
    d = np.hypot(A[:, None, 0] - B[None, :, 0], A[:, None, 1] - B[None, :, 1])
    return float(d.min())


def bbox_proche(bb, p, marge):
    return bb[0] - marge <= p[0] <= bb[2] + marge and bb[1] - marge <= p[1] <= bb[3] + marge


# --------------------------------------------------------------------------------------------
# Chargement de la description et des références
# --------------------------------------------------------------------------------------------

class Index:
    def __init__(self):
        self.E: dict[str, dict] = {}
        self.par_famille: dict[str, list[str]] = defaultdict(list)
        self.indices_v1: dict[str, dict] = {}
        self.correspondance: dict[str, dict] = {}
        self.entrees: dict[str, str] = {}
        self.O = (917279.43, 6460289.98)

    def ajouter(self, eid, famille, typ, geom, props, sigma=None, preuve=None):
        if eid in self.E or geom is None:
            return
        self.E[eid] = {"id": eid, "famille": famille, "type": typ, "G": geom, "props": props,
                       "sigma": sigma, "preuve": preuve, "classe": classe_fusion_entite(famille, typ)}
        self.par_famille[famille].append(eid)


def classe_fusion_entite(fam, typ):
    typ = typ or ""
    if fam == "arbres":
        return "arbre"
    if fam in ("marquages", "retire_v03"):
        return "marquage"
    if fam in ("bordures", "bordures_site"):
        return "bordure"
    if fam in ("surfaces", "surfaces_v1", "ilots"):
        return "surface_ilot"
    if fam == "ponctuels_sol":
        return "ponctuel_sol"
    if fam == "propositions_coherence":
        return "autre"
    if fam == "instances":
        if typ.startswith("feu"):
            return "feu"
        if "arbre" in typ or typ in ("arbuste_bosquet", "souche"):
            return "arbre"
        return "mobilier"
    if typ in ("lampadaire", "mat_camera", "poteau_reseau"):
        return "candelabre_poteau"
    if typ in ("panneau", "panneau_information", "totem_PR"):
        return "panneau"
    if typ == "support_feux":
        return "feu"
    if typ in ("potelet", "balise_J11", "poteau_incendie"):
        return "potelet_borne"
    if typ in ("cloture", "portail", "barriere_levante", "chicane"):
        return "cloture_barriere"
    return "mobilier"


def date_min_entite(ent) -> str | None:
    """Date à partir de laquelle l'entité existe sous sa forme décrite (FUS-VAL-03)."""
    p = ent["props"]
    fam = ent["famille"]
    if fam in ("marquages",):
        if p.get("etat") in ("neuf_2025", "refait_2025_identique"):
            return "2025-06-23"
    if fam == "bordures" and p.get("zone_travaux_2025"):
        return "2025-06-23"
    if fam == "surfaces":
        ev = str(p.get("etat_v1") or "")
        if "modifie_2025" in ev:
            return "2025-06-23"
        if "2023_2024" in ev:
            return "2023-01-01"
    if fam in ("mobilier", "arbres"):
        st = f"{p.get('statut_2026') or ''} {p.get('etat_2026') or ''}"
        if re.search(r"déduit 2026|planté 2025", st):
            return "2025-06-23"
    return None


def atteste_2026(ent) -> bool:
    p = ent["props"]
    return ent["famille"] in ("mobilier", "arbres") and "2026 confirmé" in str(p.get("statut_2026") or "")


def leve_gam(ent) -> bool:
    """L'entité vient-elle du levé topographique GAM (postérieur aux travaux) ? (FUS-ADD-04)"""
    p = ent["props"]
    fam = ent["famille"]
    geo = str(((p.get("prov") or {}).get("geometrie") or {}).get("src") or "").lower()
    if fam == "marquages":
        return str(p.get("src") or "").lower().startswith("gam") or geo.startswith("gam")
    if fam in ("bordures", "ilots"):
        return geo.startswith("gam")
    if fam == "bordures_site":
        return True
    if fam in ("arbres", "mobilier"):
        return bool(re.match(r"\s*GAM\b", str(p.get("source") or "")))
    return False


def type_marquage_obs(sous_type: str) -> str | None:
    """Type de marquage de la description correspondant au sous-type observé (None : indéterminé, compatible)."""
    s = (sous_type or "").lower()
    for rx, t in ((r"pav[ée]s", "passage"), (r"symbole|v[ée]lo|pmr|logo|figurine|picto|chiffre|lettr|inscription", "symbole"),
                  (r"fl[èe]che", "fleche"), (r"zebra|z[ée]bra|passage|bandes_traversee|pi[ée]ton", "passage"),
                  (r"stop|c[ée]dez|effet|transversal", "transversale"),
                  (r"hachur|zone|damier|ilot_peint|zigzag", "zone"),
                  (r"ligne|tiret|place|stationnement|discontinu|continu", "ligne")):
        if re.search(rx, s):
            return t
    return None


def dates_texte(s: str) -> list[str]:
    out = [f"{m.group(1)}-{m.group(2)}-{m.group(3) or '15'}" for m in re.finditer(r"\b(20\d\d)-(\d\d)(?:-(\d\d))?", s)]
    if re.search(r"lidar", s, re.I):
        out.append("2021-06-01")
    if re.search(r"ortho ?2022|ortho_2022", s, re.I):
        out.append("2022-05-10")
    if re.search(r"ortho IGN 2024", s, re.I):
        out.append("2024-06-01")
    if re.search(r"\bGAM\b|levé GAM|Meylan_Topo", s):
        out.append(GAM_DATE)
    if re.search(r"inventaire", s, re.I):
        out.append("2023-09-11")
    if re.search(r"plan (projet )?2025|plan2025", s, re.I):
        out.append("2025-06-23")
    return out


def date_attestation_recente(ent) -> str | None:
    """Dernière date d'attestation de l'objet dans la description (appui de conservation, FUS-DATE-02)."""
    p = ent["props"]
    fam = ent["famille"]
    ds = []
    if fam in ("mobilier", "arbres", "instances"):
        s = " ".join(str(p.get(k) or "") for k in ("source", "etat_2026", "statut_2026"))
        ds = dates_texte(s)
        if re.search(r"Panoramax 2026|photo 2026", s):
            ds.append("2026-07-28")
        if "2026 confirmé" in s:
            ds.append("2026-01-01")
    return max(ds) if ds else None


def date_attestation(ent) -> str | None:
    """Première date à laquelle la description atteste l'existence de l'objet (FUS-VAL-03)."""
    p = ent["props"]
    fam = ent["famille"]
    ds = []
    if fam in ("bordures", "bordures_site"):
        src = str(((p.get("prov") or {}).get("geometrie") or {}).get("src") or p.get("source") or "gam")
        ds = [GAM_DATE] if "gam" in src.lower() else []
    elif fam == "arbres":
        ds = dates_texte(str(p.get("source") or ""))
    elif fam == "mobilier":
        ds = dates_texte(" ".join(str(p.get(k) or "") for k in ("source", "etat_2026")))
        if p.get("type") == "cloture" and "GAM" in str(p.get("etat_2026")):
            ds.append(GAM_DATE)
    elif fam == "marquages":
        prov = p.get("prov") or {}
        for k in ("existence", "pose", "geometrie"):
            s = str((prov.get(k) or {}).get("src") or "")
            if s.startswith("gam"):
                ds.append(GAM_DATE)
            elif "ortho" in s:
                ds.append("2022-05-10")
            elif "plan2025" in s:
                ds.append("2025-06-23")
    return min(ds) if ds else None


def charger_index() -> Index:
    ix = Index()
    man = charger_json(DESC / "description_scene_v2.json")
    o = man.get("site", {}).get("origine_l93_ngf")
    if o:
        ix.O = (float(o[0]), float(o[1]))
    ix.entrees["description_scene_v2.json"] = sha256(DESC / "description_scene_v2.json")
    rap = charger_json(COH / "rapport_coherence.json")
    preuves = {ob["id"]: ob.get("preuve") or {} for ob in rap.get("objets", [])}
    ix.coherence_objets = {ob["id"]: ob for ob in rap.get("objets", [])}
    ix.entrees[rel(COH / "rapport_coherence.json")] = sha256(COH / "rapport_coherence.json")

    def fc(p):
        ix.entrees[rel(p)] = sha256(p)
        return charger_json(p).get("features", [])

    for fam in ["bordures", "surfaces", "ilots", "ponctuels_sol", "marquages"]:
        for f in fc(BASE / f"{fam}.geojson"):
            pr = f["properties"]
            typ = pr.get("classe") or pr.get("type")
            sig = 0.05 if fam == "bordures" else 0.25
            if fam == "marquages":
                src = str((pr.get("prov") or {}).get("pose", {}).get("src") or pr.get("src") or "")
                sig = 0.05 if src.startswith("gam") else (0.25 if "ortho" in src else 0.5)
            ix.ajouter(pr["id"], fam, typ, geom_norm(f.get("geometry")), pr, sig, None)
    for f in fc(PKG / "objets/mobilier.geojson"):
        pr = f["properties"]
        pv = preuves.get(pr["id"], {})
        ix.ajouter(pr["id"], "mobilier", pr.get("type"), geom_norm(f.get("geometry")), pr,
                   pv.get("sigma_m", 1.0), pv.get("classe"))
    for f in fc(PKG / "objets/arbres.geojson"):
        pr = f["properties"]
        pv = preuves.get(pr["id"], {})
        ix.ajouter(pr["id"], "arbres", pr.get("type"), geom_norm(f.get("geometry")), pr,
                   pv.get("sigma_m", 1.0), pv.get("classe"))
    inst = charger_json(PKG / "objets/instances.json")
    ix.entrees[rel(PKG / "objets/instances.json")] = sha256(PKG / "objets/instances.json")
    for it in inst.get("instances", []):
        if it["id"] in ix.E:
            continue
        g = construire_geom([np.array([it["x"] + ix.O[0], it["y"] + ix.O[1]])], [], [])
        pv = preuves.get(it["id"], {})
        ix.ajouter(it["id"], "instances", it.get("prototype"), g, it, pv.get("sigma_m", 1.0), pv.get("classe"))
    for f in fc(COH / "carte/bordures_site.geojson"):
        pr = f["properties"]
        if pr.get("id"):
            ix.ajouter(pr["id"], "bordures_site", "bordure", geom_norm(f.get("geometry")), pr, 0.05, "gam")
    for f in fc(PKG / "surfaces/surfaces_2026.geojson"):
        pr = f["properties"]
        if pr.get("id"):
            ix.ajouter(pr["id"], "surfaces_v1", pr.get("classe"), geom_norm(f.get("geometry")), pr, 0.25, None)
    for f in fc(COH / "propositions_ajouts.geojson"):
        pr = f["properties"]
        ix.ajouter(pr["id"], "propositions_coherence", pr.get("type"), geom_norm(f.get("geometry")), pr, 2.0, "a_priori")
    for f in fc(BASE / "marquages_indices_v1.geojson"):
        ix.indices_v1[f["properties"]["id"]] = f["properties"]
    for f in fc(BASE / "marquages_correspondance.geojson"):
        ix.correspondance[f["properties"]["id"]] = f["properties"]
    for e in ix.E.values():
        e["date_min"] = date_min_entite(e)
        e["atteste_2026"] = atteste_2026(e)
        e["date_attest"] = date_attestation(e)
        e["date_attest_max"] = date_attestation_recente(e)
        e["leve_gam"] = leve_gam(e)
    # index de remappage (FUS-LIEN-08)
    ix.par_lien_v1 = defaultdict(list)
    for eid in ix.par_famille.get("surfaces", []):
        lv = ix.E[eid]["props"].get("lien_v1")
        if isinstance(lv, str):
            ix.par_lien_v1[lv].append(eid)
    ix.par_ligne_gam = defaultdict(list)
    for eid in ix.par_famille.get("bordures", []):
        lg = (ix.E[eid]["props"].get("source") or {}).get("ligne")
        if lg is not None:
            ix.par_ligne_gam[lg].append(eid)
    return ix


# --------------------------------------------------------------------------------------------
# Observations
# --------------------------------------------------------------------------------------------

def normaliser_obs(o, agent, ix):
    O = ix.O
    v = o.get("valide_2026")
    vv = v.get("valeur") if isinstance(v, dict) else v
    raison = (v.get("raison") if isinstance(v, dict) else "") or ""
    attrs = o.get("attributs") or {}
    atxt = json.dumps(attrs, ensure_ascii=False)
    sous = o.get("sous_type") or ""
    n = {"id": o["id"], "agent": agent, "o": o, "classe": o.get("classe") or "autre", "sous_type": sous,
         "statut": o.get("statut"), "date": parse_date(o.get("date_image")), "conf": o.get("confiance") or "moyenne",
         "attrs": attrs, "atxt": atxt, "raison": raison, "valide": vv, "drapeaux": []}
    if n["classe"] == "autre" and re.search(r"poteau", sous):
        n["classe"] = "autre_poteau"
    if n["classe"] == "surface_ilot":
        n["classe"] = "surface"
    # source et catégorie de preuve (FUS-SRC-01)
    src = str(o.get("source") or "")
    if src.startswith("ortho2022"):
        n["source"], n["type_source"] = "ortho2022", "ortho2022"
    elif src.startswith("ortho_recente:"):
        n["source"], n["type_source"] = src, "ortho_recente"
    elif src.startswith("pnx:"):
        n["source"], n["type_source"] = "pnx:" + src[4:12], "panoramax"
    elif src.startswith("mly:"):
        n["source"], n["type_source"] = "mly:" + src[4:].split("-")[0], "mapillary"
    else:
        n["source"], n["type_source"] = src, "web"
    d_ = n["date"] or ""
    if n["type_source"] == "ortho2022":
        n["categorie"] = "ortho_2022"
    elif n["type_source"] == "ortho_recente":
        n["categorie"] = "ortho_2025" if d_ >= "2025-01-01" else "ortho_2024"
    elif n["type_source"] in ("panoramax", "mapillary"):
        n["categorie"] = ("photo_2026" if d_ >= FIN_TRAVAUX else "photo_2025" if d_ >= "2025-01-01" else "photo_2020_2024")
    else:
        n["categorie"] = "web"
    n["photo"] = n["type_source"] in ("panoramax", "mapillary")
    pos = o.get("position") or {}
    im = attrs.get("image") if isinstance(attrs.get("image"), dict) else {}
    try:
        n["distance_m"] = float(im["distance_m"]) if im.get("distance_m") is not None else None
    except (TypeError, ValueError):
        n["distance_m"] = None
    # confiance plafonnée des projections lointaines (FUS-CONF-02)
    n["conf_obs"] = n["conf"]
    if n["photo"] and pos.get("methode") == "projection_description" and n["distance_m"] is not None \
            and n["distance_m"] > DIST_CONFIANCE_MAX_M and CONF_W.get(n["conf"], 0.6) > CONF_W["faible"]:
        n["conf"] = "faible"
        n["drapeaux"].append("FUS-CONF-02")
    # poids de validité (FUS-VAL-01/02)
    w_val = 1.0 if vv is True else (0.5 if vv == "incertain" else 0.0)
    candidat_di = bool(sous.startswith("faux_positif") or re.search(r"artefact|aucun marquage réel", raison)
                       or re.search(r"toiture|sur la bande plantée|tombe sur la bande plantée", atxt)
                       and n["statut"] == "absent_sur_image")
    loin = n["photo"] and n["distance_m"] is not None and n["distance_m"] > DIST_DATE_INDEPENDANT_MAX_M
    n["date_independant"] = candidat_di and not loin
    if n["date_independant"]:
        w_val = 1.0
        n["drapeaux"].append("FUS-VAL-02")
    elif candidat_di:
        n["drapeaux"].append("FUS-VAL-02:projection_au_dela_de_15m")
    n["w_val"] = w_val
    w_conf = CONF_W.get(n["conf"], 0.6)
    n["auto"] = bool(str(o.get("controle") or "").startswith("automatique") or attrs.get("verification") == "automatique")
    ca = attrs.get("controle_auto")
    try:
        part = float(ca.get("part_masquee", 1.0)) if isinstance(ca, dict) else 1.0
    except (TypeError, ValueError):
        part = 1.0
    # contrat FUS-AUTO-02 : masque véhicules / ombres et réponse de ligne fine (marquage, bordure) ou d'arête (bordure)
    if n["classe"] == "marquage":
        reponse = isinstance(ca, dict) and (ca.get("reponse_ligne_fine") is True or ca.get("reponse_peinture") is True)
    elif n["classe"] == "bordure":
        reponse = isinstance(ca, dict) and (ca.get("reponse_ligne_fine") is True or ca.get("reponse_arete") is True)
    else:
        reponse = True
    n["auto_masque"] = bool(n["auto"] and isinstance(ca, dict) and ca.get("masque_vehicules_ombres") is True
                            and part <= AUTO_PART_MASQUEE_MAX and reponse)
    if n["auto"]:
        w_conf *= 0.7
        n["drapeaux"].append("controle_automatique")
        if n["auto_masque"]:
            n["drapeaux"].append("FUS-AUTO-02:masque")
    n["w_conf"] = w_conf
    # position
    pos = o.get("position") or {}
    n["prec"] = pos.get("precision_m")
    n["methode"] = pos.get("methode")
    p = None
    if isinstance(pos.get("l93"), list) and len(pos["l93"]) >= 2:
        p = np.array(pos["l93"][:2], float)
    elif isinstance(pos.get("local"), list) and len(pos["local"]) >= 2:
        p = np.array([pos["local"][0] + O[0], pos["local"][1] + O[1]], float)
    n["p"] = p
    n["sigma"] = None
    n["sigma_brut"] = None
    if p is not None and n["prec"] is not None and n["methode"] in SIG_METHODE:
        fl, fa = SIG_METHODE[n["methode"]]
        s = max(float(n["prec"]), fl) * fa
        if n["methode"] == "triangulation":
            m = RE_ANGLE.search(atxt)
            if m and fnum(m.group(1)) < 15.0:
                s *= 2.0
                n["drapeaux"].append("FUS-POS-02")
        w = w_conf * w_val
        n["sigma"] = s / math.sqrt(w) if w > 0 else None
        n["sigma_brut"] = s
    # géométrie observée (lignes, groupes de points, emprises)
    n["G"] = geom_obs(o, p, O)
    # contexte, temporaire
    prec = n["prec"]
    n["contexte"] = bool(p is None or prec is None or float(prec) > 5.0 or RE_CTX.match(sous) or n["classe"] == "batiment")
    n["temporaire"] = bool(RE_TMP.search(sous) or RE_TMP_RAISON.search(raison)
                           or (n["classe"] == "cloture" and re.search(r"chantier", texte(attrs.get("type_observe", "")))))
    n["a_verifier"] = attrs.get("a_verifier") is True   # constat de revue « à vérifier » (FUS-ARB-01, FUS-EXI-04)
    return n


CLES_LISTES = {"liens", "confirmes", "arbres_confirmes", "arbres", "image", "autres_vues", "non_verifiables"}


def ids_cites(o) -> set:
    """Identifiants cités dans la preuve (note, ids) et dans le texte libre d'une observation (FUS-LIEN-09)."""
    textes = []
    pv = o.get("preuve") if isinstance(o.get("preuve"), dict) else {}
    for k, v in sorted(pv.items()):
        if k in ("note", "ids", "entites", "cible"):
            textes.append(texte(v))
    for k, v in sorted((o.get("attributs") or {}).items()):
        if k not in CLES_LISTES and isinstance(v, str):
            textes.append(v)
    out = set()
    for s in textes:
        for t in re.split(r"[;,\s()«»:/\[\]\"']+", s):
            t = t.rstrip(".")
            if RE_ID.match(t):
                out.add(t)
    return out


def geom_obs(o, p, O):
    pos = o.get("position") or {}
    a = o.get("attributs") or {}

    def l93(L):
        return [np.array(c[:2], float) for c in L if isinstance(c, (list, tuple)) and len(c) >= 2]

    def loc(L):
        return [np.array([c[0] + O[0], c[1] + O[1]], float) for c in L if isinstance(c, (list, tuple)) and len(c) >= 2]

    for src, conv in ((pos.get("geometrie_l93"), l93), (o.get("geometrie_l93"), l93), (a.get("geometrie_l93"), l93),
                      (a.get("geometrie_l93_approx"), l93),
                      (a.get("trace_l93"), l93), (a.get("trace_local"), loc), (a.get("extremites_local"), loc)):
        if isinstance(src, list) and len(src) >= 2:
            pts = conv(src)
            if len(pts) >= 2:
                g = construire_geom([], [np.array(pts)], [])
                g["source_geom"] = "trace"
                return g
    ax = a.get("axe")
    if isinstance(ax, str):
        cs = re.findall(r"\(\s*([-−]?\d+(?:[.,]\d+)?)\s*;\s*([-−]?\d+(?:[.,]\d+)?)\s*\)", ax)
        if len(cs) >= 2:
            g = construire_geom([], [np.array([[fnum(x) + O[0], fnum(y) + O[1]] for x, y in cs])], [])
            g["source_geom"] = "axe_texte_local"
            return g
    if isinstance(a.get("positions_l93"), list) and len(a["positions_l93"]) >= 2:
        g = construire_geom(l93(a["positions_l93"]), [], [])
        g["source_geom"] = "positions_l93"
        return g
    et = a.get("etendue_l93")
    if isinstance(et, list) and len(et) == 2:
        (x0, y0), (x1, y1) = et[0][:2], et[1][:2]
        R = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]], float)
        g = construire_geom([], [], [[R]])
        g["source_geom"] = "emprise_approx"
        return g
    if p is not None:
        g = construire_geom([p], [], [])
        g["source_geom"] = "point"
        return g
    return None


# --------------------------------------------------------------------------------------------
# Résolution des liens
# --------------------------------------------------------------------------------------------

def plus_proche(ix, p, familles, tol):
    """Entité la plus proche (distance géométrique) parmi des familles/types, dans la tolérance."""
    best = None
    for fam, types in familles:
        for eid in ix.par_famille.get(fam, []):
            e = ix.E[eid]
            if types is not None and e["type"] not in types:
                continue
            if not bbox_proche(e["G"]["bbox"], p, tol + 0.01):
                continue
            d, _ = dist_geom(p, e["G"])
            if d <= tol + 1e-9 and (best is None or (d, eid) < best):
                best = (d, eid)
    return best


def resoudre_id(ix, i, n):
    """-> (entité, mode, règle) ou (None, raison, règle)."""
    if i in ix.E and i.startswith("KS-"):
        lg = ix.E[i]["props"].get("ligne")
        ref = n["p"] if n["p"] is not None else ix.E[i]["G"]["pt"]
        cands = sorted((dist_geom(ref, ix.E[k]["G"])[0], k) for k in ix.par_ligne_gam.get(lg, []))
        if cands and cands[0][0] <= 2.0:
            return cands[0][1], f"ks_vers_k:{i}", "FUS-LIEN-08"
    if i in ix.E and i.startswith("surf_"):
        ref = n["p"] if n["p"] is not None else ix.E[i]["G"]["pt"]
        cands = sorted((dist_geom(ref, ix.E[k]["G"])[0], k) for k in ix.par_lien_v1.get(i, []))
        if cands and cands[0][0] <= 1.0:
            return cands[0][1], f"surface_v1:{i}", "FUS-LIEN-08"
    if i in ix.E:
        return i, "id", "FUS-LIEN-01"
    if i in ix.indices_v1:
        liens = ix.indices_v1[i].get("lien_v1") or []
        cibles = sorted({(ix.correspondance.get(m) or {}).get("entite") for m in liens} - {None})
        if cibles and cibles[0] in ix.E:
            return cibles[0], f"remap_v1:{i}", "FUS-LIEN-02"
        rid = "RETIRE:" + i
        if rid not in ix.E:
            pr = dict(ix.indices_v1[i])
            g = None
            ix.E[rid] = {"id": rid, "famille": "retire_v03", "type": pr.get("classe"), "G": g, "props": pr,
                         "sigma": 0.3, "preuve": None, "classe": "marquage", "date_min": None, "atteste_2026": False,
                         "date_attest": None}
        return rid, f"retire_v03:{i}", "FUS-LIEN-02"
    if re.match(r"^S-\d{4}$", i) and n["p"] is not None:
        cands = []
        for eid in ix.par_famille.get("surfaces", []):
            if re.match(re.escape(i) + r"[a-z]+$", eid):
                d, _ = dist_geom(n["p"], ix.E[eid]["G"])
                cands.append((d, eid))
        cands.sort()
        if cands and cands[0][0] <= 1.0:
            return cands[0][1], f"surface_v02:{i}", "FUS-LIEN-03"
    if n["p"] is not None:
        fam = None
        if i.startswith("BEV-"):
            fam = [("ponctuels_sol", None)]
        elif i.startswith("S-"):
            fam = [("surfaces", None)]
        elif i.startswith(("ML-", "MF-", "MP-", "MS-", "MZ-", "MT-")):
            fam = [("marquages", None)]
        elif i.startswith("K-"):
            fam = [("bordures", None)]
        if fam:
            tol = max(TOL_CLASSE.get(n["classe"], 1.0), 1.5)
            b = plus_proche(ix, n["p"], fam, tol)
            if b:
                return b[1], f"spatial_prefixe:{i}", "FUS-LIEN-04"
    return None, f"introuvable:{i}", "FUS-LIEN-04"


def meme_famille(n, ent) -> bool:
    """L'entité liée est-elle de la famille de l'objet observé (sinon : hôte, FUS-LIEN-07) ?"""
    for fam, types in FAM_SPATIALE.get(n["classe"], []):
        fams = {fam, "surfaces_v1"} if fam == "surfaces" else ({fam, "bordures_site"} if fam == "bordures" else {fam})
        if ent["famille"] in fams and (types is None or ent["type"] in types):
            return True
    if n["classe"] == "arbre" and ent["famille"] == "instances" and "arbre" in str(ent["type"]):
        return True
    return False


def ids_dans(v):
    out = []
    vals = v if isinstance(v, list) else [v]
    for x in vals:
        if isinstance(x, str):
            for t in re.split(r"[;,\s]+", x):
                if RE_ID.match(t):
                    out.append(t)
    return out


# --------------------------------------------------------------------------------------------
# Attributs
# --------------------------------------------------------------------------------------------

def facteur_probable(v) -> float:
    s = texte(v)
    return 0.6 if re.search(r"probable|\?|possible", s, re.I) else 1.0


def norm_essence(v):
    s = texte(v)
    if re.search(r"non déterminable|indéterminable", s, re.I):
        return None
    m = re.search(r"\b(" + "|".join(GENRES) + r")\s+([a-z]{3,})\b", s)
    if m and m.group(2) not in ("probable", "confirme", "confirmé", "plutot", "plutôt", "ou"):
        return f"{m.group(1)} {m.group(2)}"
    m = re.search(r"\b(" + "|".join(GENRES) + r")\b", s)
    if m:
        return m.group(1)
    for fr, g in GENRE_FR.items():
        if re.search(r"\b" + fr + r"\b", s, re.I):
            return g
    return None


def norm_materiau(v, vocab):
    s = texte(v).lower()
    for k in sorted(vocab, key=len, reverse=True):
        if k in s:
            return k, True
    regles = [(r"galet|pierres roul", "galets_20_40"), (r"concass", "gravier_concasse_6_10"),
              (r"stabilis", "stabilise_beige"), (r"pav[ée]s", "paves_beton"), (r"gazon|pelouse", "gazon_tondu"),
              (r"herbe haute|friche|prairie", "herbe_haute"), (r"brf|copeaux|plaquette", "brf_bois_concasse"),
              (r"béton|beton|concrete", "beton_balaye"), (r"terre nue|terre_nue", "terre_nue")]
    for rx, k in regles:
        if re.search(rx, s):
            return k, True
    tok = re.split(r"[ (/,;]", s.strip())[0]
    return (tok or None), False


def extraire_attributs(n, ent, vocab):
    """Votes d'attributs canoniques d'une observation : [(attr, genre, valeur, facteur, clé)] (FUS-ATT-01)."""
    a = n["attrs"]
    cls = n["classe"]
    fam = ent["famille"] if ent else None
    etype = ent["type"] if ent else None
    out = []

    def add(attr, genre, val, cle, f=1.0):
        if val is None:
            return
        out.append((attr, genre, val, f, cle))

    est_panneau = cls == "panneau" or etype in ("panneau",)
    # hauteurs
    if est_panneau:
        for k in ("hauteur_centre_m", "hauteur_centre_estimee_m"):
            if k in a:
                v = a[k]
                if isinstance(v, dict):
                    code = (ent or {}).get("props", {}).get("code") if ent else None
                    v = v.get(code) if code in v else None
                add("hauteur_m", "num", parse_num(v), k, facteur_probable(a[k]))
                break
    elif cls not in ("marquage", "surface", "ilot", "bordure", "tampon", "avaloir", "bev"):
        for k in ("hauteur_mesuree_m", "hauteur_estimee_m", "hauteur_observee_m", "hauteur_visible_m"):
            if k in a:
                add("hauteur_m", "num", parse_num(a[k]), k, facteur_probable(a[k]))
                break
    for k in ("couronne_m", "couronne_estimee_m", "couronne_proposee_m"):
        if k in a and cls in ("arbre",):
            add("couronne_m", "num", parse_num(a[k]), k, facteur_probable(a[k]))
            break
    if cls == "marquage":
        for k in ("largeur_observee_m", "largeur_estimee_m"):
            if k in a:
                v = parse_num(a[k])
                if v is not None and v <= 0.6:  # largeur de trait (les emprises de zones restent en notes)
                    add("largeur_m", "num", v, k)
                break
        for k in ("modulation_proposee", "modulation"):
            if k in a:
                s = texte(a[k])
                m = re.search(r"T'?\d", s)
                val = m.group(0) if m else ("continue" if "continue" in s else None)
                add("modulation", "cat", val, k, facteur_probable(a[k]))
                break
        if "couleur" in a:
            s = texte(a["couleur"]).lower()
            m = re.search(r"\b(" + "|".join(COULEURS) + r")", s)
            add("couleur", "cat", m.group(1) if m else None, "couleur")
        if "etat_propose" in a:
            s = texte(a["etat_propose"])
            for e in ETATS_MQ:
                if e in s:
                    add("etat", "cat", e, "etat_propose", 0.6 if " ou " in s else 1.0)
                    break
        for k in ("usure_observee", "usure"):
            if k in a:
                s = texte(a[k]).strip().strip('"')
                m = re.match(r"^\s*([0-3])", s)
                val = float(m.group(1)) if m else (3.0 if "forte" in s else 2.0 if "moyenne" in s else None)
                add("usure", "num", val, k)
                break
        if "gabarit" in a:
            s = texte(a["gabarit"])
            for g in GABARITS:
                if re.search(r"\b" + g + r"\b", s):
                    add("gabarit", "cat", g, "gabarit")
                    break
    if cls in ("candelabre", "autre_poteau") or etype in ("lampadaire",):
        for k in ("nb_crosses", "nb_crosses_propose", "crosses"):
            if k in a:
                v = a[k]
                s = texte(v).lower()
                val = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else (
                    2 if re.match(r"^\s*\"?(double|2)", s) else 1 if re.match(r"^\s*\"?(simple|1)", s) else None)
                add("nb_crosses", "cat", val, k)
                break
        for k in ("nb_lanternes", "nb_lanternes_vues", "nb_luminaires"):
            if k in a and isinstance(a[k], (int, float)):
                add("nb_lanternes", "cat", int(a[k]), k)
                break
        for k in ("porte_a_faux_observe_m", "porte_a_faux_m"):
            if k in a:
                add("porte_a_faux_m", "num", parse_num(a[k]), k)
                break
        retype = " ".join(texte(a.get(k, "")) for k in ("type_propose", "type_reel")) + " " + n["sous_type"]
        if re.search(r"poteau[_ ](de )?(bois|r[ée]seau)|poteau_reseau", retype, re.I) and etype == "lampadaire":
            add("type", "cat", "poteau_reseau", "type_propose|sous_type")
    if cls in ("candelabre", "feu", "potelet", "autre_poteau", "mobilier"):
        for k in ("couleur_mat", "teinte"):
            if k in a:
                s = texte(a[k]).lower().split("(")[0].strip().strip('"')
                add("couleur_mat", "cat", s or None, k, facteur_probable(a[k]))
                break
    if cls == "potelet" and "diametre_m" in a:
        add("diametre_m", "num", parse_num(a["diametre_m"]), "diametre_m")
    if cls in ("arbre", "massif", "haie") or (fam == "arbres"):
        if cls == "arbre" or fam == "arbres":
            for k in ("essence", "essence_probable"):
                if k in a:
                    ess = norm_essence(a[k])
                    add("essence", "cat", ess, k, facteur_probable(a[k]) * (0.8 if n["type_source"] == "web" else 1.0))
                    break
        # type végétal : seulement un type explicitement observé (pas l'écho du type décrit d'un contrôle automatique)
        s = n["sous_type"].lower() + " " + texte(a.get("type_observe", "")).lower()
        tv = None
        if re.search(r"haie", s) or cls in ("haie", "massif"):
            tv = "haie"
        elif re.search(r"conif|cedr|cèdre", s):
            tv = "conifere"
        elif re.search(r"arbuste", s):
            tv = "arbuste"
        elif re.search(r"feuillu|peuplier", s):
            tv = "feuillu"
        explicite = ("type_observe" in a or n["statut"] == "attribut_corrige"
                     or (ent is not None and tv not in (None, ent["type"])))
        if tv and ent is not None and ent["famille"] == "arbres" and explicite and "controle_automatique" not in n["drapeaux"]:
            add("type", "cat", tv, "sous_type|type_observe")
    if cls == "haie":
        for k in ("essence", "essence_probable"):
            if k in a:
                add("essence", "cat", court(texte(a[k]), 80), k, 0.6)
                break
        for k in ("epaisseur_m", "epaisseur_estimee_m", "largeur_m"):
            if k in a:
                add("epaisseur_m", "num", parse_num(a[k]), k)
                break
    if est_panneau:
        if "code" in a:
            m = re.search(r"\b([A-Z]{1,2}\d{1,3}[a-z]?\d?)\b", texte(a["code"]))
            add("code", "cat", m.group(1) if m else None, "code")
        az = None
        if isinstance(a.get("face_azimut_deg"), (int, float)):
            az, cle = float(a["face_azimut_deg"]), "face_azimut_deg"
        else:
            for k in ("face", "orientation", "faces", "coherence"):
                if k in a:
                    m = re.search(r"(?:face(?:\s+au|\s+vers\s+le|\s+vers\s+la)?|vers\s+le|vers\s+la)\s+(NE|NO|SE|SO|N|S|E|O)\b",
                                  texte(a[k]))
                    if m:
                        az, cle = float(COMPAS[m.group(1)]), k
                        break
        if az is not None:
            add("azimut_deg", "circ", az, cle)
    if cls in ("surface", "ilot", "massif"):
        for k in ("materiau_propose", "materiau_observe", "remplissage_observe"):
            if k in a:
                mat, dans_vocab = norm_materiau(a[k], vocab)
                add("materiau_id", "cat", mat, k, facteur_probable(a[k]) * (1.0 if dans_vocab else 0.8))
                break
        if "classe_proposee" in a and cls == "surface":
            s = texte(a["classe_proposee"]).strip('"')
            add("classe", "cat", re.split(r"[ (]", s)[0] or None, "classe_proposee")
        # revêtement neuf vu après les travaux : surface refaite en 2025 (FUS-ZONE-01)
        if cls == "surface" and n["categorie"] == "photo_2026" and n["valide"] is True and fam == "surfaces" \
                and re.search(r"neuf", (n["sous_type"] + " " + texte(a.get("materiau_propose", ""))).lower()):
            add("etat_v1", "cat", "modifie_2025", "sous_type|materiau_propose")
    if cls in ("tampon", "avaloir") and "forme" in a:
        s = texte(a["forme"]).lower()
        fo = "rectangulaire" if "rectang" in s else ("carre" if "carr" in s else ("rond" if re.search(r"rond|disque|anneau", s) else None))
        add("forme", "cat", fo, "forme")
        m = re.search(r"≈\s*(\d+(?:[.,]\d+)?)", s)
        if m:
            add("dimension_m", "num", fnum(m.group(1)), "forme")
        if re.search(r"grille|barreaux", s):
            add("grille", "cat", True, "forme")
    if cls == "feu":
        for k in ("bouton_appel", "signal_sonore", "vibreur"):
            if k in a:
                s = texte(a[k]).lower()
                val = False if re.search(r"\bno\b|non|false|absent|aucun", s) else (True if re.search(r"yes|oui|true|présent", s) else None)
                add(k, "cat", val, k)
    if cls == "cloture":
        for k in ("hauteur_observee_m",):
            if k in a:
                add("hauteur_m", "num", parse_num(a[k]), k)
    # textes lus (non votés)
    for k in ("lecture", "texte", "texte_lu", "lames", "lame_haut", "lame_bas", "lame_1", "lame_2"):
        if k in a and isinstance(a[k], str):
            add("texte_lu", "texte", court(a[k], 160), k)
    return out


def valeur_description(ent, attr):
    if ent is None:
        return None
    p = ent["props"]
    fam = ent["famille"]
    if fam in ("mobilier", "instances"):
        m = {"hauteur_m": p.get("hauteur_m"), "nb_crosses": p.get("nb_crosses"), "porte_a_faux_m": p.get("porte_a_faux_m"),
             "azimut_deg": p.get("azimut_deg"), "code": p.get("code"), "type": p.get("type")}
        return m.get(attr)
    if fam == "arbres":
        m = {"hauteur_m": p.get("hauteur_m"), "couronne_m": p.get("diametre_couronne_m"), "essence": p.get("essence"),
             "type": p.get("type")}
        return m.get(attr)
    if fam == "marquages":
        if attr == "usure":
            u = p.get("usure")
            return float(u) if u not in (None, "") and str(u).isdigit() else None
        return {"modulation": p.get("modulation"), "couleur": p.get("couleur"), "etat": p.get("etat"),
                "gabarit": p.get("gabarit"), "largeur_m": p.get("largeur_m")}.get(attr)
    if fam == "surfaces":
        return {"materiau_id": (p.get("revetement") or {}).get("materiau_id"), "classe": p.get("classe"),
                "etat_v1": p.get("etat_v1")}.get(attr)
    if fam == "ilots":
        return {"materiau_id": (p.get("remplissage") or {}).get("materiau_id")}.get(attr)
    return None


def voter(votes, attr, genre=None):
    """votes : [(valeur, poids, obs_id)] -> dict résultat (FUS-ATT-02/03)."""
    genre = genre or ATTR_SPEC.get(attr, ("cat",))[0]
    vs = [(v, w, i) for v, w, i in votes if w > 0]
    if not vs:
        return None
    if attr == "essence":
        # un genre seul (« Cedrus ») conforte l'espèce du même genre (« Cedrus deodara ») au lieu de s'y opposer
        especes = defaultdict(float)
        for v, w, i in vs:
            if isinstance(v, str) and " " in v:
                especes[v] += w
        vs2 = []
        for v, w, i in vs:
            if isinstance(v, str) and " " not in v:
                cands = sorted(((ww, e) for e, ww in especes.items() if e.split(" ")[0] == v), key=lambda t: (-t[0], t[1]))
                if cands:
                    v = cands[0][1]
            vs2.append((v, w, i))
        vs = vs2
    W = sum(w for _, w, _ in vs)
    res = {"genre": genre, "poids": round(W, 3), "obs": sorted({i for _, _, i in vs}), "conflit": False, "detail": None}
    if genre == "num":
        vals = np.array([v for v, _, _ in vs], float)
        ws = np.array([w for _, w, _ in vs], float)
        mu = float((vals * ws).sum() / ws.sum())
        _, tabs, trel, _, _ = ATTR_SPEC.get(attr, ("num", 0.5, 0.25, 0.5, 0.15))
        etendue = float(vals.max() - vals.min())
        res["valeur"] = round(mu, 3)
        res["etendue"] = round(etendue, 3)
        if len(vs) > 1 and etendue > max(tabs, trel * abs(mu)):
            res["conflit"] = True
            res["detail"] = {str(i): r3(v) for v, _, i in sorted(vs, key=lambda t: t[2])}
    elif genre == "circ":
        vals = [v for v, _, _ in vs]
        ws = [w for _, w, _ in vs]
        mu = moyenne_circulaire(vals, ws)
        res["valeur"] = round(mu, 1)
        if any(angle_diff(v, mu) > ATTR_SPEC[attr][1] for v in vals):
            res["conflit"] = True
            res["detail"] = {str(i): v for v, _, i in sorted(vs, key=lambda t: t[2])}
    else:
        acc = defaultdict(float)
        qui = defaultdict(list)
        for v, w, i in vs:
            k = json.dumps(v, ensure_ascii=False)
            acc[k] += w
            qui[k].append(i)
        ordre = sorted(acc.items(), key=lambda t: (-t[1], t[0]))
        res["valeur"] = json.loads(ordre[0][0])
        res["poids"] = round(ordre[0][1], 3)
        res["poids_total"] = round(W, 3)
        if len(ordre) > 1:
            res["alternatives"] = {k: round(w, 3) for k, w in ordre[1:]}
            if ordre[1][1] >= 0.5 * ordre[0][1] and ordre[1][1] >= 0.3:
                res["conflit"] = True
                res["detail"] = {k: sorted(qui[k]) for k, _ in ordre}
        if genre == "texte":
            res["valeur"] = [json.loads(k) for k, _ in ordre]
            res["conflit"] = False
            res["detail"] = None
    return res


def ecart_significatif(attr, fused, desc):
    if desc is None:
        return True
    genre = ATTR_SPEC.get(attr, ("cat",))[0]
    if genre == "num":
        try:
            d = abs(float(fused) - float(desc))
        except (TypeError, ValueError):
            return True
        _, _, _, sabs, srel = ATTR_SPEC.get(attr, ("num", 0.5, 0.25, 0.5, 0.15))
        return d > max(sabs, srel * abs(float(desc))) - 1e-9
    if genre == "circ":
        try:
            return angle_diff(float(fused), float(desc)) > ATTR_SPEC[attr][3]
        except (TypeError, ValueError):
            return True
    if attr == "essence" and isinstance(desc, str) and isinstance(fused, str):
        return fused.lower() not in desc.lower()
    return str(fused) != str(desc)


# --------------------------------------------------------------------------------------------
# Fusion
# --------------------------------------------------------------------------------------------

class Fusion:
    def __init__(self, ix, obs, vocab):
        self.ix = ix
        self.obs = obs
        self.vocab = vocab
        self.membres = defaultdict(list)       # entité -> [(n, rôle, statut_effectif, mode, règle)]
        self.non_lies = []                      # observations non appariées (candidats d'ajout)
        self.index_obs = {}                     # obs -> trace
        self.conflits = []
        self.res_entites = {}
        self.ajouts = []
        self.corrections = []
        self.controle_coh = []
        corr = charger_json(COH / "corrections.geojson").get("features", [])
        self.corr_coh = defaultdict(list)
        for f in corr:
            self.corr_coh[f["properties"]["id"]].append(f["properties"])
        self.props_coh = [f for f in charger_json(COH / "propositions_ajouts.geojson").get("features", [])]
        gam = charger_json(SITE / "etat_2026/arbre_pct_L93.geojson").get("features", [])
        pts = []
        for f in gam:
            g = f.get("geometry") or {}
            cs = g.get("coordinates") or []
            if g.get("type") == "Point":
                cs = [cs]
            for c in cs:
                pts.append(c[:2])
        self.gam_arbres = np.array(pts, float) if pts else np.zeros((0, 2))
        ix.entrees[rel(SITE / "etat_2026/arbre_pct_L93.geojson")] = sha256(SITE / "etat_2026/arbre_pct_L93.geojson")
        ix.entrees[rel(COH / "corrections.geojson")] = sha256(COH / "corrections.geojson")
        ix.entrees[rel(COH / "propositions_ajouts.geojson")] = sha256(COH / "propositions_ajouts.geojson")
        self.requalifiees = {}                  # obs automatique -> verdict FUS-AUTO-01 (incertain | corroboree)
        self._ev = {}                           # (entité, obs, rôle) -> poids (FUS-VAL-03/04, FUS-DATE-02)
        self._dz = {}
        self.zone_extension = {}
        self.zone_anneaux = []
        self.ajouts_refuses = []                # groupes d'ajout remplacés par un conflit (FUS-ADD-04)
        # arbitrages de revue (FUS-ARB-01)
        self.arbitrages = []
        if ARBITRAGES.exists():
            self.arbitrages = sorted(charger_json(ARBITRAGES).get("arbitrages", []), key=lambda a: a["id"])
            ix.entrees[rel(ARBITRAGES)] = sha256(ARBITRAGES)
        self.arb_par_obs = defaultdict(list)
        for a in self.arbitrages:
            a["_applique"] = []
            for oid in a.get("obs", []):
                self.arb_par_obs[oid].append(a)
        # constats de revue versés comme observations (FUS-ARB-01, action constat_revue)
        synth = []
        for a in self.arbitrages:
            if a.get("action") != "constat_revue":
                continue
            for k, c in enumerate(a.get("constats", []), 1):
                ent = ix.E.get(c.get("entite"))
                if ent is None or ent.get("G") is None:
                    self.conflit("arbitrage_inapplicable", "a_verifier", a["id"], [],
                                 f"arbitrage {a['id']} (constat_revue) : entité {c.get('entite')} absente de la description",
                                 "mettre à jour arbitrages_fusion.json")
                    continue
                pt = ent["G"]["pt"]
                o = {"id": f"REV-{a['id']}-{k:02d}", "source": a["source_image"], "date_image": a["date_image"],
                     "classe": c.get("classe") or a.get("classe"), "sous_type": c.get("sous_type") or "",
                     "attributs": {"note": c.get("note") or "", "a_verifier": bool(a.get("a_verifier", False)),
                                   "arbitrage": a["id"]},
                     "position": {"l93": [r3(pt[0]), r3(pt[1])], "precision_m": 0.2, "methode": "projection_description"},
                     "lien_description": c["entite"], "statut": c["statut"],
                     "valide_2026": {"valeur": a.get("valide_2026", True), "raison": a.get("validite") or ""},
                     "confiance": c["confiance"],
                     "preuve": {"fichier": (a.get("preuves") or [None])[0], "note": c["entite"]}}
                if c.get("distance_m") is not None:
                    o["attributs"]["image"] = {"distance_m": c["distance_m"]}
                synth.append(normaliser_obs(o, "revue", ix))
                a["_applique"].append(c["entite"])
        self.obs_revue = synth
        self.obs = sorted(list(obs) + synth, key=lambda n: n["id"])
        par_id = {n["id"]: n for n in self.obs}
        for a in self.arbitrages:
            if a.get("action") != "mesure_position":
                continue
            for oid in a.get("obs", []):
                n = par_id.get(oid)
                if n is None or n["p"] is None:
                    continue
                pa = a.get("parametres") or {}
                s = float(pa.get("sigma_m") or max(float(n["prec"] or 1.0), 1.0))
                w = n["w_conf"] * n["w_val"]
                n["methode"] = pa.get("methode") or "mesure_arbitree"
                n["mesure_arbitree"] = a["id"]
                n["sigma_brut"] = s
                n["sigma"] = s / math.sqrt(w) if w > 0 else None
                n["drapeaux"].append(f"FUS-ARB-01:{a['id']}")

    def arbitrage(self, n, action):
        return next((a for a in self.arb_par_obs.get(n["id"], []) if a.get("action") == action), None)

    # -------- conflits --------
    def conflit(self, typ, gravite, cible, obs, detail, reco, **extra):
        self.conflits.append({"type": typ, "gravite": gravite, "cible": cible, "obs": sorted(set(obs)),
                              "detail": detail, "recommandation": reco, **extra})

    # -------- 1. liens --------
    def lier(self):
        ix = self.ix
        for n in self.obs:
            tr = {"id": n["id"], "agent": n["agent"], "source": n["source"], "date": n["date"], "categorie": n["categorie"],
                  "classe": n["o"].get("classe"),
                  "statut": n["statut"], "valide_2026": n["valide"], "confiance": n["conf"], "confiance_observee": n["conf_obs"],
                  "distance_camera_m": n["distance_m"], "controle_automatique": n["auto"],
                  "poids_validite": n["w_val"], "poids_confiance": round(n["w_conf"], 3), "liens": [], "role": None,
                  "drapeaux": list(n["drapeaux"])}
            self.index_obs[n["id"]] = tr
            prim = ids_dans(n["o"].get("lien_description")) if n["o"].get("lien_description") else []
            resolus = []
            cite_de = {}
            for i in prim:
                e, mode, regle = resoudre_id(ix, i, n)
                tr["liens"].append({"id_cite": i, "entite": e, "mode": mode, "regle": regle, "role": "primaire"})
                if e:
                    resolus.append((e, mode, regle))
                    cite_de.setdefault(e, i)
                else:
                    self.conflit("lien_introuvable", "a_verifier", i, [n["id"]],
                                 f"id {i} absent de la description courante et sans équivalent spatial",
                                 "relancer l'atelier après régénération de la description ou relier à la main")
            # liens secondaires (FUS-LIEN-05)
            sec = []
            for k, st in (("liens", None), ("confirmes", "confirme"), ("arbres_confirmes", "confirme"), ("arbres", None)):
                if k in n["attrs"]:
                    for i in ids_dans(n["attrs"][k]):
                        if i in prim:
                            continue
                        e, mode, regle = resoudre_id(ix, i, n)
                        tr["liens"].append({"id_cite": i, "entite": e, "mode": mode, "regle": "FUS-LIEN-05", "role": "secondaire"})
                        if e and all(e != r[0] for r in resolus) and all(e != s[0] for s in sec):
                            sec.append((e, mode, st))
                            cite_de.setdefault(e, i)
            # anciens ids si aucun lien
            if not resolus and not prim:
                for k in ("lien_v02", "id_v0_2"):
                    for i in ids_dans(n["attrs"].get(k)):
                        e, mode, regle = resoudre_id(ix, i, n)
                        if e and not e.startswith("RETIRE:"):
                            resolus.append((e, "ancien_id:" + i, "FUS-LIEN-04"))
                            tr["liens"].append({"id_cite": i, "entite": e, "mode": "ancien_id", "regle": "FUS-LIEN-04", "role": "primaire"})
                            break
                    if resolus:
                        break
            # appariement spatial (FUS-LIEN-06)
            if not resolus and n["statut"] != "absent_de_description" and not n["contexte"] \
                    and n["p"] is not None and float(n["prec"] or 99) <= 3.0 and n["classe"] in FAM_SPATIALE:
                tol = TOL_CLASSE.get(n["classe"], 1.0)
                b = plus_proche(ix, n["p"], FAM_SPATIALE[n["classe"]], tol)
                if b:
                    resolus.append((b[1], f"spatial:{b[0]:.2f}m", "FUS-LIEN-06"))
                    tr["liens"].append({"id_cite": None, "entite": b[1], "mode": f"spatial:{b[0]:.2f}m", "regle": "FUS-LIEN-06", "role": "primaire"})
            # objet nouveau rattaché à un hôte (FUS-LIEN-07)
            if n["statut"] == "absent_de_description" and (resolus or sec):
                meme = [e for e, _, _ in resolus if meme_famille(n, ix.E[e])]
                if not meme:
                    n["hotes"] = sorted({e for e, _, _ in resolus})
                    n["liens_associes"] = sorted({e for e, _, _ in sec})
                    for l in tr["liens"]:
                        l["role"] = "hote" if l["role"] == "primaire" else "associe"
                        l["regle"] = "FUS-LIEN-07"
                    resolus, sec = [], []
                elif n["classe"] == "surface":
                    n["statut_effectif"] = "attribut_corrige"   # constat d'état de la surface hôte
                    sec = []
            # co-implantation des liens primaires multiples
            coloc = True
            if len(resolus) > 1:
                P = [ix.E[e]["G"]["pt"] for e, _, _ in resolus if ix.E[e].get("G")]
                coloc = len(P) == len(resolus) and max(float(np.hypot(*(a - b))) for a in P for b in P) <= 1.5
            # constat d'état d'une surface sans lien (fissures...) : rattaché à la surface qui le contient
            if not resolus and not sec and n["statut"] == "absent_de_description" and n["classe"] == "surface" \
                    and re.search(r"fissur|etat", n["sous_type"]) and n["p"] is not None and not n["contexte"]:
                b = plus_proche(ix, n["p"], [("surfaces", None)], 0.0)
                if b:
                    resolus.append((b[1], "surface_hote", "FUS-LIEN-07"))
                    n["statut_effectif"] = "attribut_corrige"
                    tr["liens"].append({"id_cite": None, "entite": b[1], "mode": "surface_hote", "regle": "FUS-LIEN-07", "role": "primaire"})
            st_eff = n.get("statut_effectif", n["statut"])
            # liens groupés sur une photo sans preuve propre (FUS-LIEN-09)
            non_prouves = set()
            groupe = ([] if coloc else [e for e, _, _ in resolus]) + [e for e, _, _ in sec]
            if n["photo"] and len(set(groupe)) >= GROUPE_LIENS_MIN:
                cites = ids_cites(n["o"])
                non_prouves = {e for e in groupe if e not in cites and cite_de.get(e) not in cites}
                if non_prouves:
                    tr["drapeaux"].append("FUS-LIEN-09")
                    tr["liens_groupes_non_prouves"] = sorted(non_prouves)
                    tr["liens_groupes_prouves"] = sorted(set(groupe) - non_prouves)
            for e, mode, regle in resolus:
                self.membres[e].append({"n": n, "role": "primaire", "statut": "incertain" if e in non_prouves else st_eff,
                                        "mode": mode, "regle": regle, "position_ok": coloc and e not in non_prouves,
                                        "lien_groupe_non_prouve": e in non_prouves})
            for e, mode, st in sec:
                self.membres[e].append({"n": n, "role": "secondaire",
                                        "statut": "incertain" if e in non_prouves else (st or n["statut"]), "mode": mode,
                                        "regle": "FUS-LIEN-05", "position_ok": False,
                                        "lien_groupe_non_prouve": e in non_prouves})
            if resolus or sec:
                tr["role"] = "entite"
                continue
            if n["contexte"]:
                tr["role"] = "contexte"
                tr["regle"] = "FUS-CTX-01"
            elif n["temporaire"]:
                tr["role"] = "temporaire"
                tr["regle"] = "FUS-TMP-01"
            elif n["statut"] in ("absent_de_description", "incertain") and n["G"] is not None:
                tr["role"] = "candidat_ajout"
                self.non_lies.append(n)
            else:
                tr["role"] = "non_apparie"
                tr["regle"] = "FUS-LIEN-06"

    # -------- 1b. contrôles automatiques des marquages (FUS-AUTO-01/02) --------
    def requalifier_automatiques(self):
        for eid in sorted(self.membres):
            M = self.membres[eid]
            ent = self.ix.E[eid]
            autos = [m for m in M if m["statut"] == "confirme" and m["n"]["auto"] and not m["n"]["auto_masque"]
                     and m["n"]["classe"] in CLASSES_AUTO_REQUALIFIEES and m["n"]["type_source"] in ("ortho2022", "ortho_recente")]
            if not autos:
                continue
            corrob = sorted({m["n"]["id"] for m in M if not m["n"]["auto"] and m["statut"] in PRESENCE
                             and self.evaluer(ent, m)["w_presence"] > 0})
            for m in autos:
                oid = m["n"]["id"]
                tr = self.index_obs[oid]
                if corrob:
                    m["corroboree_par"] = corrob
                    if self.requalifiees.get(oid) != "incertain":
                        self.requalifiees[oid] = "corroboree"
                    tr.setdefault("corroboree_par", {})[eid] = corrob
                else:
                    m["statut"] = "incertain"
                    m["requalifiee"] = "FUS-AUTO-01"
                    self.requalifiees[oid] = "incertain"
                    tr["statut_effectif"] = "incertain"
                    tr["requalification"] = "FUS-AUTO-01 : confirmation automatique sans masque véhicules / ombres ni corroboration manuelle"
        for oid, v in self.requalifiees.items():
            fl = "FUS-AUTO-01:" + ("requalifiee_incertain" if v == "incertain" else "corroboree")
            if fl not in self.index_obs[oid]["drapeaux"]:
                self.index_obs[oid]["drapeaux"].append(fl)
        # arbitrages de mesure : l'observation doit être liée à l'entité visée (FUS-ARB-01)
        for a in self.arbitrages:
            if a.get("action") != "mesure_position":
                continue
            cible = a.get("entite")
            ok = [oid for oid in a.get("obs", []) if any(m["n"]["id"] == oid and m["role"] == "primaire"
                                                         for m in self.membres.get(cible, []))]
            if ok:
                a["_applique"].append(cible)
            else:
                self.conflit("arbitrage_inapplicable", "a_verifier", cible or a["id"], a.get("obs", []),
                             f"arbitrage {a['id']} (mesure_position) : observation non liée à {cible}",
                             "mettre à jour arbitrages_fusion.json")

    # -------- 1c. arbitrages d'observations (FUS-ARB-01 : invalider_observation) --------
    def appliquer_invalidations(self):
        for a in self.arbitrages:
            if a.get("action") != "invalider_observation":
                continue
            cibles = set(a.get("entites") or [])
            for oid in a.get("obs", []):
                for eid in sorted(self.membres):
                    if cibles and eid not in cibles:
                        continue
                    for m in self.membres[eid]:
                        if m["n"]["id"] != oid:
                            continue
                        m["statut"] = "incertain"
                        m["invalidee"] = a["id"]
                        m["position_ok"] = False
                        tr = self.index_obs[oid]
                        tr.setdefault("invalidations", {})[eid] = a["id"]
                        fl = f"FUS-ARB-01:{a['id']}"
                        if fl not in tr["drapeaux"]:
                            tr["drapeaux"].append(fl)
                        a["_applique"].append(f"{oid} -> {eid}")
            if not a["_applique"]:
                self.conflit("arbitrage_inapplicable", "a_verifier", a["id"], a.get("obs", []),
                             f"arbitrage {a['id']} (invalider_observation) : observation non liée aux entités visées",
                             "mettre à jour arbitrages_fusion.json")

    # -------- 1d. zone des travaux, appui de conservation (FUS-ZONE-01, FUS-DATE-02) --------
    def preparer_zone(self):
        """Anneaux de la zone des travaux 2025 et extension par photo 2026 (FUS-ZONE-01)."""
        ix = self.ix
        extension = {}
        for eid in sorted(self.membres):
            ent = ix.E[eid]
            if ent["famille"] != "surfaces" or ent.get("G") is None:
                continue
            for m in self.membres[eid]:
                n = m["n"]
                if m["role"] != "primaire" or m["statut"] not in PRESENCE or n["categorie"] != "photo_2026" \
                        or n["valide"] is not True or CONF_W.get(n["conf"], 0) < 0.6:
                    continue
                s = (n["sous_type"] + " " + texte(n["attrs"].get("materiau_propose", ""))
                     + " " + texte(n["attrs"].get("materiau_observe", ""))).lower()
                if re.search(r"neuf", s):
                    extension.setdefault(eid, []).append(n["id"])
        self.zone_extension = {k: sorted(v) for k, v in sorted(extension.items())}
        anneaux = [("v1", R) for R in zones_travaux_2025()]
        anneaux += [(eid, pg[0]) for eid in self.zone_extension for pg in ix.E[eid]["G"]["polys"]]
        self.zone_anneaux = [(src, R, (float(R[:, 0].min()), float(R[:, 1].min()), float(R[:, 0].max()), float(R[:, 1].max())))
                             for src, R in anneaux]
        self._dz = {}

    def distance_zone(self, ent, seulement_extension=False):
        """Distance de la géométrie d'une entité à la zone des travaux (0 si elle y entre)."""
        return self.distance_zone_geom(ent.get("G"), (ent["id"], seulement_extension), seulement_extension)

    def distance_zone_geom(self, G, cle, seulement_extension=False):
        if cle in self._dz:
            return self._dz[cle]
        best = math.inf
        if G is not None:
            bb = G["bbox"]
            P = None
            mg = EMPRISE_MARGE_M
            for src, R, rb in self.zone_anneaux:
                if seulement_extension and src == "v1":
                    continue
                if rb[0] - mg > bb[2] or bb[0] - mg > rb[2] or rb[1] - mg > bb[3] or bb[1] - mg > rb[3]:
                    continue
                if P is None:
                    P = densifier(G, 1.0)
                    if len(P) == 0:
                        P = np.array([G["pt"]])
                if dans_anneau_multi(P, R).any():
                    best = 0.0
                    break
                if G["polys"] and any(dans_anneau(R[0], pg[0]) for pg in G["polys"]):
                    best = 0.0   # zone contenue dans le polygone de l'entité
                    break
                best = min(best, float(dist_points_polyligne(P, R).min()))
        self._dz[cle] = best
        return best

    def dans_emprise(self, ent) -> bool:
        if "dans_emprise" not in ent:
            ent["d_zone_m"] = r3(self.distance_zone(ent)) if math.isfinite(self.distance_zone(ent)) else None
            ent["dans_emprise"] = self.distance_zone(ent) <= EMPRISE_MARGE_M
        return ent["dans_emprise"]

    def dans_emprise_obs(self, ent, n) -> bool:
        """Emprise à l'endroit observé : pour une ligne ou un polygone, au point de l'observation s'il est sur l'entité
        (≤ 5 m) ; sinon pour toute l'entité (FUS-DATE-02)."""
        G = ent["G"]
        if G["type"] != "point" and n["p"] is not None and dist_geom(n["p"], G)[0] <= 5.0:
            cle = ("pt", round(float(n["p"][0]), 3), round(float(n["p"][1]), 3))
            return self.distance_zone_geom(construire_geom([n["p"]], [], []), cle) <= EMPRISE_MARGE_M
        return self.dans_emprise(ent)

    def appui_conservation(self, ent):
        """Règle qui appuie la conservation de l'entité pendant les travaux (FUS-DATE-02) : (règle, motif) ou None."""
        if "appui" in ent:
            return ent["appui"]
        p = ent["props"]
        fam = ent["famille"]
        res = None
        if fam in ("marquages", "retire_v03"):
            if p.get("etat") == "conserve":
                res = ("FUS-SRC-001", "marquage « conserve » (admissibilité ortho 2022 / photos)")
        elif fam == "bordures":
            src = str(((p.get("prov") or {}).get("geometrie") or {}).get("src") or "")
            sh = (p.get("source") or {}).get("statut_hauteur")
            if p.get("zone_travaux_2025") is False and sh != "modifiee_2025" and src.startswith("gam") \
                    and self.distance_zone(ent, seulement_extension=True) > EMPRISE_MARGE_M:
                res = ("FUS-SRC-001", "bordure levée GAM après travaux, hors périmètre refait")
        elif fam == "bordures_site":
            if p.get("zone_travaux_2025") is False and self.distance_zone(ent, seulement_extension=True) > EMPRISE_MARGE_M:
                res = ("FUS-SRC-001", "bordure levée GAM après travaux, hors périmètre refait")
        elif fam in ("surfaces", "surfaces_v1"):
            ev = str(p.get("etat_v1") or p.get("etat") or "")
            if ev in ("inchange_2022", "construit_2023_2024") and ent["id"] not in self.zone_extension \
                    and not any(dans_anneau(ent["G"]["pt"], R) for _, R, _ in self.zone_anneaux):
                res = ("FUS-SRC-001", f"surface « {ev} » hors de la zone des travaux")
        elif fam == "ilots":
            if ent.get("leve_gam"):
                res = ("FUS-SRC-001", "îlot à ceinture levée GAM après travaux")
        elif fam in ("mobilier", "arbres", "instances"):
            dmax = ent.get("date_attest_max")
            if ent.get("atteste_2026") or (dmax and dmax >= GAM_DATE):
                res = ("FUS-SRC-001", f"objet attesté après les travaux ({dmax or '2026 confirmé'})")
            elif ent["classe"] == "arbre" and len(self.gam_arbres) and ent.get("G") is not None:
                pt = ent["G"]["pt"]
                d = float(np.hypot(self.gam_arbres[:, 0] - pt[0], self.gam_arbres[:, 1] - pt[1]).min())
                if d <= 2.0:
                    res = ("FUS-SRC-001", f"arbre du levé GAM 2026 à {d:.2f} m")
        ent["appui"] = res
        return res

    def evaluer(self, ent, m):
        """Poids d'une observation pour une entité selon la date, l'emprise et la validité (FUS-VAL-03/04, FUS-DATE-02)."""
        cle = (ent["id"], m["n"]["id"], m["role"])
        if cle in self._ev:
            return self._ev[cle]
        n = m["n"]
        w = n["w_conf"] * n["w_val"]
        t = n["date"] or ""
        di = n["date_independant"]
        if t and t >= FIN_TRAVAUX:
            cd = "apres_travaux"
        elif ent.get("G") is not None and self.dans_emprise_obs(ent, n):
            cd = "avant_travaux_dans_emprise"
        else:
            cd = "avant_travaux_hors_emprise"
        appui = self.appui_conservation(ent) if cd == "avant_travaux_dans_emprise" else None
        motifs = []
        bloque_creation = bool(ent.get("date_min") and t < ent["date_min"] and not di)
        if bloque_creation:
            motifs.append("FUS-VAL-03")
        bloque_emprise = cd == "avant_travaux_dans_emprise" and appui is None and not di
        if bloque_emprise:
            motifs.append("FUS-DATE-02")
        incertain = n["valide"] == "incertain" and not di
        if incertain:
            motifs.append("FUS-VAL-04")
        ev = {"w": w, "classe_date": cd, "appui": appui[0] + " : " + appui[1] if appui else None,
              "w_attribut": 0.0 if (bloque_creation or bloque_emprise) else w,
              "w_presence": 0.0 if (bloque_creation or bloque_emprise or incertain) else w,
              "w_position": 0.0 if bloque_creation else w,
              "probant_absence": not (bloque_emprise or incertain), "motifs": motifs}
        self._ev[cle] = ev
        return ev

    def est_stricte(self, ent, m) -> bool:
        """Preuve stricte (FUS-COUV-02) : image manuelle, confiance ≥ moyenne, valide 2026, probante, non invalidée."""
        n = m["n"]
        if n["auto"] or n["type_source"] == "web" or CONF_W.get(n["conf"], 0) < 0.6 or n["w_val"] < 1.0:
            return False
        if m.get("invalidee") or m.get("lien_groupe_non_prouve") or m.get("requalifiee"):
            return False
        ev = self.evaluer(ent, m)
        if m["statut"] in PRESENCE:
            return ev["w_presence"] > 0
        if m["statut"] == "absent_sur_image":
            v = self.evaluer_absence(ent, n, ev)[0]
            return v in ("absence", "retrait") or (v == "attendue" and self.probant(ent, n) and ev["probant_absence"])
        return False

    # -------- 2. entités --------
    def poids_existence(self, ent, m):
        """Poids de présence au sens 0.2 (FUS-VAL-03 seul) : couverture large FUS-COUV-01."""
        n = m["n"]
        w = n["w_conf"] * n["w_val"]
        dm = ent.get("date_min")
        if dm and n["date"] and n["date"] < dm and not n["date_independant"]:
            return 0.0, "FUS-VAL-03"
        return w, None

    def probant(self, ent, n) -> bool:
        """L'image est-elle postérieure à la création et à la première attestation de l'objet ?"""
        t = n["date"] or ""
        if ent.get("date_min") and t < ent["date_min"]:
            return False
        if ent.get("date_attest") and t < ent["date_attest"]:
            return False
        if ent.get("atteste_2026") and t < "2025-12-01":
            return False
        return True

    def evaluer_absence(self, ent, n, ev=None):
        """Absence sur image -> retrait | absence | attendue | non_probant (FUS-VAL-02/03/04, FUS-DATE-02, FUS-EXI-01/02).
        Sans `ev` : règles 0.2 (couverture large FUS-COUV-01)."""
        if n["date_independant"]:
            return "retrait", "FUS-VAL-02"
        if ev is not None and not ev["probant_absence"]:
            return "non_probant", ("FUS-VAL-04" if "FUS-VAL-04" in ev["motifs"] else "FUS-DATE-02")
        t = n["date"] or ""
        if ent.get("date_min") and t < ent["date_min"]:
            return "attendue", "FUS-VAL-03"
        if RE_ABS_COHERENT.search(n["raison"] + " " + n["atxt"]):
            return "attendue", "FUS-VAL-03"
        if not self.probant(ent, n):
            return "non_probant", "FUS-VAL-03"
        if RE_RETRAIT.search(n["atxt"]):
            return "retrait", "FUS-EXI-02"
        return "absence", "FUS-EXI-01"

    def existence(self, ent, M, regles):
        """Poids de présence / absence / retrait... d'un ensemble d'observations (FUS-EXI-01/02, FUS-VAL-03/04, FUS-DATE-02)."""
        W = Counter()
        qui = defaultdict(list)
        dates = defaultdict(list)
        non_probants, attendues, doublon_de = [], [], None
        stricts, a_verifier = set(), set()
        for m in M:
            n = m["n"]
            st = m["statut"]
            ev = self.evaluer(ent, m)
            w_brut = n["w_conf"] * n["w_val"]
            if self.est_stricte(ent, m):
                stricts.add(n["id"])
            if n.get("a_verifier"):
                a_verifier.add(n["id"])
            if st == "absent_sur_image":
                verdict, regle = self.evaluer_absence(ent, n, ev)
                regles.add(regle)
                if verdict == "non_probant":
                    if w_brut > 0:
                        non_probants.append(n["id"])
                    continue
                if verdict == "attendue":
                    attendues.append(n["id"])
                    continue
                k = "retrait" if verdict == "retrait" else "absence"
                W[k] += w_brut
                qui[k].append(n["id"])
                if w_brut > 0:
                    dates[k].append(n["date"] or "")
                md = re.search(r"doublon (?:géométrique )?de ([A-Za-z]{1,6}[-_][\w-]+)", n["atxt"])
                if k == "retrait" and md and RE_ID.match(md.group(1)):
                    doublon_de = md.group(1)
                continue
            for mo in ev["motifs"]:
                regles.add(mo)
            w = ev["w_attribut"]
            if w <= 0:
                continue
            if st in PRESENCE and ev["w_presence"] > 0:
                W["presence"] += ev["w_presence"]
                qui["presence"].append(n["id"])
                dates["presence"].append(n["date"] or "")
            temp_explicite = n["temporaire"] and re.search(r"chantier|provisoire|temporaire", n["sous_type"] + " " +
                                                            texte(n["attrs"].get("type_observe", ""))) \
                and not re.search(r"definitiv|définitiv", n["sous_type"] + n["atxt"])
            if m["role"] == "primaire" and (temp_explicite or RE_NE_PAS_INST.search(n["atxt"])):
                if self.probant(ent, n):
                    W["non_instancier"] += w
                    qui["non_instancier"].append(n["id"])
                else:
                    non_probants.append(n["id"])
            if m["role"] == "primaire" and isinstance(n["attrs"].get("doublon"), str) and RE_ID.match(n["attrs"]["doublon"]):
                W["doublon"] += w
                qui["doublon"].append(n["id"])
                doublon_de = n["attrs"]["doublon"]
        W["_dates"] = dates
        W["_stricts"] = stricts
        W["_a_verifier"] = a_verifier
        return W, qui, non_probants, attendues, doublon_de

    @staticmethod
    def chronologie(W):
        """FUS-EXI-03 : absences toutes postérieures aux présences (objet retiré) ou l'inverse (objet posé)."""
        d = W.get("_dates") or {}
        da, dp = [x for x in d.get("absence", []) if x], [x for x in d.get("presence", []) if x]
        if W["absence"] >= 0.6 and W["presence"] >= 0.3 and da and dp and min(da) > max(dp):
            return "retire_entre_dates"
        if W["presence"] >= 0.3 and W["absence"] >= 0.3 and da and dp and min(dp) > max(da):
            return "pose_entre_dates"
        return None

    @classmethod
    def verdict_existence(cls, W, regles, qui=None):
        """Verdict d'existence ; avec `qui`, un retrait ou une absence sans observation stricte devient
        « absent_2026_a_verifier » (FUS-EXI-04)."""
        chrono = cls.chronologie(W)
        stricts = W.get("_stricts") or set()
        a_verif = W.get("_a_verifier") or set()

        def decide(v, cle):
            if qui is None:
                return v
            porteurs = set(qui.get(cle, []))
            if not (porteurs & stricts) or (porteurs & a_verif):
                regles.add("FUS-EXI-04")
                return "absent_2026_a_verifier"
            return v

        if W["retrait"] >= 0.6:
            regles.add("FUS-EXI-02")
            return decide("retirer", "retrait")
        if W["doublon"] >= 0.6:
            regles.add("FUS-EXI-02")
            return decide("retirer_doublon", "doublon")
        if W["non_instancier"] >= 0.3:
            regles.add("FUS-TMP-01")
            return "non_instancier"
        if chrono == "retire_entre_dates":
            regles.add("FUS-EXI-03")
            return decide("absent_2026", "absence")
        if chrono == "pose_entre_dates":
            regles.add("FUS-EXI-03")
            return "present"
        if W["absence"] >= 0.6 and W["absence"] >= 2 * W["presence"]:
            regles.add("FUS-EXI-01")
            return decide("absent_2026", "absence")
        if W["presence"] >= 0.3:
            return "present"
        if qui is not None and W["absence"] >= 0.3:
            regles.add("FUS-EXI-04")
            return "absent_2026_a_verifier"
        return "non_verifie"

    def preuve_concluante(self, ent, m) -> bool:
        """Observation valable 2026 et concluante (FUS-COUV-01)."""
        n = m["n"]
        if n["w_conf"] * n["w_val"] <= 0:
            return False
        if m["statut"] in PRESENCE:
            return self.poids_existence(ent, m)[0] > 0
        if m["statut"] == "absent_sur_image":
            v = self.evaluer_absence(ent, n)[0]
            # absence attendue (l'observateur confirme le statut décrit) sur une image probante : concluante
            return v in ("absence", "retrait") or (v == "attendue" and self.probant(ent, n))
        return False

    def fusion_entite(self, eid, M):
        ix = self.ix
        ent = ix.E[eid]
        r = {"id": eid, "famille": ent["famille"], "type": ent["type"], "classe": ent["classe"],
             "obs": sorted({m["n"]["id"] for m in M}), "sources": sorted({m["n"]["source"] for m in M}),
             "conflits": [], "regles": set()}
        evs = {id(m): self.evaluer(ent, m) for m in M}
        valides = [m for m in M if m["n"]["w_val"] > 0 and evs[id(m)]["w_attribut"] > 0]
        r["date_max_valide"] = max((m["n"]["date"] for m in valides if m["n"]["date"]), default=None)
        r["date_max"] = max((m["n"]["date"] for m in M if m["n"]["date"]), default=None)
        r["dans_emprise_travaux"] = bool(ent.get("dans_emprise")) if ent.get("G") is not None else None
        r["d_zone_travaux_m"] = ent.get("d_zone_m")
        r["appui_conservation"] = (" : ".join(ent["appui"]) if ent.get("appui") else None) if r["dans_emprise_travaux"] else None
        # ---- couverture large : preuve la plus récente, valable 2026 et concluante (FUS-COUV-01, définition 0.2) ----
        concl = [m for m in M if self.preuve_concluante(ent, m)]
        cats = {m["n"]["categorie"] for m in concl}
        cat = next((c for c in CATEGORIES if c in cats), None)
        if cat is None:
            cat = "non_concluant" if valides else ("non_valable_2026" if M else None)
        r["categorie_preuve"] = cat
        r["tranche_preuve"] = TRANCHE.get(cat, cat)
        r["obs_preuve"] = sorted({m["n"]["id"] for m in concl if m["n"]["categorie"] == cat})
        r["preuve_automatique_seule"] = bool(concl) and all(m["n"]["auto"] for m in concl)
        r["requalifiees"] = sorted({m["n"]["id"] for m in M if m.get("requalifiee")})
        if r["requalifiees"]:
            r["regles"].add("FUS-AUTO-01")
        # ---- couverture stricte (FUS-COUV-02) par classe de date relative aux travaux (FUS-DATE-02) ----
        stricts = [m for m in M if self.est_stricte(ent, m)]
        cls_s = {evs[id(m)]["classe_date"] for m in stricts}
        cd = next((c for c in CLASSES_DATE if c in cls_s), None)
        if cd is None:
            if concl:
                cd = "indice_seulement"
            elif any(evs[id(m)]["w_attribut"] > 0 and m["n"]["w_val"] > 0 for m in M):
                cd = "non_concluant"
            else:
                cd = "non_valable_2026"
        r["tranche_stricte"] = cd
        r["preuve_stricte"] = {
            "obs": sorted({m["n"]["id"] for m in stricts}),
            "obs_meilleure_classe": sorted({m["n"]["id"] for m in stricts if evs[id(m)]["classe_date"] == cd}),
            "presence": sorted({m["n"]["id"] for m in stricts if m["statut"] in PRESENCE}),
            "categorie": next((c for c in CATEGORIES if c in {m["n"]["categorie"] for m in stricts}), None)}
        r["regles"].add("FUS-COUV-02")
        if any(evs[id(m)]["classe_date"] == "avant_travaux_dans_emprise" for m in M):
            r["regles"].add("FUS-DATE-02")
        r["obs_non_probantes"] = {m["n"]["id"]: evs[id(m)]["motifs"] for m in sorted(M, key=lambda m: m["n"]["id"])
                                  if evs[id(m)]["motifs"] and m["statut"] in PRESENCE + ("absent_sur_image",)} or None
        for m in M:
            ev = evs[id(m)]
            for l in self.index_obs[m["n"]["id"]]["liens"]:
                if l.get("entite") == eid:
                    l.update({"classe_date": ev["classe_date"], "appui_conservation": ev["appui"],
                              "non_probant": ev["motifs"] or None, "stricte": self.est_stricte(ent, m),
                              "statut_lien": m["statut"]})
        # ---- existence (FUS-EXI-01/02/04, FUS-VAL-03/04, FUS-DATE-02), priorité photo 2026 (FUS-DATE-01) ----
        M26 = [m for m in M if m["n"]["categorie"] == "photo_2026" and evs[id(m)]["w_attribut"] > 0
               and m["statut"] in PRESENCE + ("absent_sur_image",)]
        W, qui, non_probants, attendues, doublon_de = self.existence(ent, M26 or M, r["regles"])
        ex = self.verdict_existence(W, r["regles"], qui)
        if ex == "absent_2026_a_verifier":
            porteurs = sorted(set(qui.get("absence", [])) | set(qui.get("retrait", [])) | set(qui.get("doublon", [])))
            notes_ = "; ".join(court(texte(m["n"]["attrs"].get("note") or m["n"]["attrs"].get("observation") or ""), 160)
                               for m in M if m["n"]["id"] in porteurs)
            self.conflit("existence_douteuse_2026", "a_verifier", eid, porteurs,
                         f"absence ou retrait vu sans preuve stricte, ou constat de revue « à vérifier » "
                         f"(absence {W['absence']:.2f}, retrait {W['retrait']:.2f}, présence {W['presence']:.2f}). {notes_}",
                         "garder l'objet décrit ; trancher sur le terrain (prise de vue rasante) avant de le retirer")
            r["conflits"].append("existence_douteuse_2026")
        if doublon_de and ex in ("retirer", "retirer_doublon"):
            r["doublon_de"] = doublon_de
        r["existence"] = {"verdict": ex, "poids": {k: round(v, 3) for k, v in sorted(W.items()) if not k.startswith("_")},
                          "obs": {k: sorted(v) for k, v in sorted(qui.items())}}
        chrono = self.chronologie(W)
        if chrono:
            r["existence"]["chronologie"] = chrono
            dd = W["_dates"]
            self.conflit("changement_entre_dates", "info", eid, qui["absence"] + qui["presence"],
                         f"{'absent' if chrono == 'retire_entre_dates' else 'présent'} après "
                         f"{max(x for x in (dd['presence'] if chrono == 'retire_entre_dates' else dd['absence']) if x)} : "
                         f"objet {'retiré' if chrono == 'retire_entre_dates' else 'posé'} entre deux prises de vue (FUS-EXI-03)",
                         "état le plus récent retenu")
            r["conflits"].append("changement_entre_dates")
        if M26:
            r["regles"].add("FUS-DATE-01")
            anter = [m for m in M if m not in M26 and m["statut"] in PRESENCE + ("absent_sur_image",)]
            Wa, quia, _, _, _ = self.existence(ent, anter, set())
            ex_a = self.verdict_existence(Wa, set())
            ecartees = sorted({o for v in quia.values() for o in v})
            if ecartees:
                r["existence"]["priorite_2026"] = True
                r["existence"]["obs_anterieures_ecartees"] = ecartees
                r["existence"]["verdict_anterieur"] = ex_a
            pres = {"present"}
            abse = {"absent_2026", "retirer", "retirer_doublon", "non_instancier", "absent_2026_a_verifier"}
            if (ex_a in pres and ex in abse) or (ex_a in abse and ex in pres):
                # un retrait « artefact » (constat indépendant de la date) contredit par 2026 reste à vérifier
                grav = "a_verifier" if ex_a in ("retirer", "retirer_doublon") else "info"
                self.conflit("changement_2026", grav, eid, sorted({o for v in qui.values() for o in v}) + ecartees,
                             f"photo 2026 : {ex} ; images antérieures : {ex_a}"
                             + (" (constat d'artefact indépendant de la date contredit par la photo 2026)" if grav == "a_verifier"
                                else " (objet posé, refait ou retiré pendant les travaux 2025 ?)"),
                             "état 2026 retenu (FUS-DATE-01)" + (" ; relire les deux vues" if grav == "a_verifier" else ""))
                r["conflits"].append("changement_2026")
        if W["absence"] >= 0.3 and W["presence"] >= 0.3 and not chrono:
            self.conflit("existence_desaccord", "a_verifier", eid, qui["absence"] + qui["presence"],
                         f"présence {W['presence']:.2f} contre absence {W['absence']:.2f}",
                         "trancher sur une image postérieure aux travaux ou sur le terrain")
            r["conflits"].append("existence_desaccord")
        if attendues:
            r["existence"]["absences_attendues"] = sorted(attendues)
        if non_probants:
            r["existence"]["absences_non_probantes"] = sorted(non_probants)
            notes_abs = "; ".join(court(texte(m["n"]["attrs"].get("note") or m["n"]["attrs"].get("observe")
                                             or m["n"]["attrs"].get("observation") or m["n"]["attrs"].get("proposition") or ""), 140)
                                  for m in M if m["n"]["id"] in non_probants)
            motifs_np = {}
            for m in M:
                if m["n"]["id"] in non_probants:
                    mo = self.evaluer_absence(ent, m["n"], evs[id(m)])[1] if m["statut"] == "absent_sur_image" else "FUS-VAL-03"
                    motifs_np.setdefault(mo, set()).add(m["n"]["id"])
            lib = {"FUS-VAL-03": f"image antérieure à la première attestation de l'objet "
                                 f"({ent.get('date_attest') or ent['props'].get('statut_2026') or '?'})",
                   "FUS-DATE-02": "image antérieure à la fin des travaux, dans leur emprise, sans appui de conservation",
                   "FUS-VAL-04": "validité 2026 incertaine"}
            r["existence"]["motifs_non_probants"] = {k: sorted(v) for k, v in sorted(motifs_np.items())}
            self.conflit("validite_2026_douteuse", "a_verifier", eid, non_probants,
                         "absence (ou retrait proposé) non probante pour 2026 : "
                         + " ; ".join(f"{lib.get(k, k)} ({', '.join(sorted(v))}, {k})" for k, v in sorted(motifs_np.items()))
                         + f". {notes_abs}",
                         "garder l'objet ; vérifier sur image 2026 ou sur le terrain")
            r["conflits"].append("validite_2026_douteuse")
        # ---- attributs ----
        votes = defaultdict(list)
        genres = {}
        sous_zones = []
        cat_obs = {m["n"]["id"]: m["n"]["categorie"] for m in M}
        grande_surface = ent["famille"] == "surfaces" and float(ent["props"].get("aire_m2") or 0) > SURFACE_MAX_PONCTUELLE_M2
        ids_stricts = set(r["preuve_stricte"]["obs"])
        valeurs_obs = defaultdict(dict)
        for m in M:
            n = m["n"]
            w = evs[id(m)]["w_attribut"]
            if w <= 0 or m["statut"] == "absent_sur_image":
                continue
            if m.get("invalidee") or m.get("lien_groupe_non_prouve") or m.get("requalifiee"):
                continue   # lien invalidé, groupé sans preuve propre ou automatique requalifié : aucun attribut
            for attr, genre, val, f, cle in extraire_attributs(n, ent, self.vocab):
                valeurs_obs[attr][n["id"]] = val
                if grande_surface and attr in ("materiau_id", "classe"):
                    sous_zones.append({"obs": n["id"], "attribut": attr, "valeur": val,
                                       "l93": [r3(n["p"][0]), r3(n["p"][1])] if n["p"] is not None else None,
                                       "sous_type": n["sous_type"], "categorie": n["categorie"]})
                    continue
                votes[attr].append((val, w * f, n["id"]))
                genres[attr] = genre
        # priorité photo 2026 par attribut (FUS-DATE-01)
        anterieurs = {}
        for attr in sorted(votes):
            v26 = [v for v in votes[attr] if cat_obs.get(v[2]) == "photo_2026" and v[1] > 0]
            if v26 and len(v26) < len(votes[attr]):
                anterieurs[attr] = sorted({v[2] for v in votes[attr] if cat_obs.get(v[2]) != "photo_2026"})
                votes[attr] = v26
                r["regles"].add("FUS-DATE-01")
        if grande_surface:
            fourre_tout = [m["n"]["id"] for m in M if re.search(r"fourre_tout", m["n"]["sous_type"])]
            if sous_zones or fourre_tout:
                r["sous_zones"] = sorted(sous_zones, key=lambda s: s["obs"])
                r["regles"].add("FUS-ATT-05")
                self.conflit("surface_a_decouper", "a_verifier", eid, [s["obs"] for s in sous_zones] + fourre_tout,
                             f"surface de {float(ent['props'].get('aire_m2') or 0):.0f} m² ({ent['type']}, "
                             f"{(ent['props'].get('revetement') or {}).get('materiau_id')}) contenant des sous-zones observées : "
                             + "; ".join(f"{s['valeur']} ({s['obs']})" for s in sorted(sous_zones, key=lambda s: s["obs"])),
                             "découper le polygone dans la description du sol (sous-zones à leurs positions)")
                r["conflits"].append("surface_a_decouper")
        maj, confirmes = {}, {}
        for attr in sorted(votes):
            res = voter(votes[attr], attr, genres.get(attr))
            if res is None:
                continue
            if res["genre"] == "texte":
                r.setdefault("textes_lus", {})[attr] = {"valeurs": res["valeur"], "obs": res["obs"]}
                continue
            desc = valeur_description(ent, attr)
            if res["conflit"]:
                self.conflit("attribut_desaccord", "a_verifier", eid, res["obs"],
                             f"{attr} : {json.dumps(res['detail'], ensure_ascii=False)}",
                             f"valeur retenue {res['valeur']} (poids {res['poids']}) ; à confirmer")
                r["conflits"].append(f"attribut_desaccord:{attr}")
            if res["poids"] >= 0.3 and ecart_significatif(attr, res["valeur"], desc):
                conf = "haute" if res["poids"] >= 1.5 and len({self.src_of(i) for i in res["obs"]}) >= 2 else (
                    "moyenne" if res["poids"] >= 0.6 else "faible")
                gagnants = set(res["obs"]) if res["genre"] in ("num", "circ") else {
                    i for i in res["obs"] if json.dumps(valeurs_obs[attr].get(i), ensure_ascii=False)
                    == json.dumps(res["valeur"], ensure_ascii=False)}
                strict_ = sorted(gagnants & ids_stricts)
                maj[attr] = {"avant": desc, "apres": res["valeur"], "conf": conf, "poids": res["poids"],
                             "obs": res["obs"], "regle": "FUS-ATT-04 ; FUS-ATT-06", "conflit": res["conflit"],
                             "obs_strictes": strict_,
                             "decision": "appliquer" if strict_ and not res["conflit"] else "revue_requise"}
                if "alternatives" in res:
                    maj[attr]["alternatives"] = res["alternatives"]
                if attr in anterieurs:
                    maj[attr]["obs_anterieures_ecartees"] = anterieurs[attr]
                    maj[attr]["regle"] = "FUS-ATT-04 ; FUS-ATT-06 ; FUS-DATE-01"
            elif desc is not None and not ecart_significatif(attr, res["valeur"], desc):
                confirmes[attr] = {"valeur": desc, "obs": res["obs"]}
                if attr in anterieurs:
                    confirmes[attr]["obs_anterieures_ecartees"] = anterieurs[attr]
        r["maj"] = maj
        r["attributs_confirmes"] = confirmes
        if "type" in maj and maj["type"]["apres"] == "poteau_reseau":
            r["regles"].add("FUS-EXI-02")
        # notes textuelles des constats correctifs
        notes = []
        for m in M:
            n = m["n"]
            if m["statut"] in ("attribut_corrige", "position_corrigee", "incertain", "absent_sur_image") or m["role"] == "secondaire":
                for k in ("observe", "note", "observation", "constat", "remarque", "description", "correction",
                          "interpretation", "ecart", "action_proposee", "proposition"):
                    if k in n["attrs"] and isinstance(n["attrs"][k], str):
                        notes.append({"obs": n["id"], "date": n["date"], "texte": court(n["attrs"][k])})
                        break
        if notes:
            r["notes"] = sorted(notes, key=lambda x: x["obs"])
        # ---- bordures : vote de la vue, du profil et des abaissés (FUS-BOR-01..03) ----
        if ent["famille"] in ("bordures", "bordures_site"):
            self.voter_bordure(ent, M, evs, r)
        # ---- position ----
        self.fusion_position(ent, M, r)
        # ---- cohérence ----
        self.controle_coherence(ent, r)
        # ---- statut de vérification (FUS-STAT-01) ----
        ex = r["existence"]["verdict"]
        pos = r.get("position") or {}
        if ex == "absent_2026":
            sv = "absent_2026"
        elif ex in ("retirer", "retirer_doublon", "non_instancier"):
            sv = "a_retirer"
        elif ex == "absent_2026_a_verifier":
            sv = "absent_2026_a_verifier"
        elif r["preuve_stricte"]["presence"]:
            if (r.get("bordure") or {}).get("contradictions_a_verifier"):
                sv = "conteste"
            elif r["maj"] or pos.get("verdict") in ("affinage", "deplacement", "translation"):
                sv = "corrige"
            else:
                sv = "confirme"
        elif r["tranche_stricte"] == "non_valable_2026":
            sv = "non_valable_2026"
        else:
            sv = "indice_seulement"
        r["statut_verification"] = sv
        r["regles"].add("FUS-STAT-01")
        r["regles"] = sorted(r["regles"])
        return r

    # -------- bordures (FUS-BOR-01..03) --------
    def voter_bordure(self, ent, M, evs, r):
        """Vote de la vue, du profil et des abaissés d'une bordure (FUS-BOR-01..03)."""
        p = ent["props"]
        ivs = p.get("intervalles") or []
        C = max(ent["G"]["lignes"], key=len) if ent["G"]["lignes"] else None
        lectures, votes, candidats = [], defaultdict(list), defaultdict(list)
        for m in sorted(M, key=lambda m: m["n"]["id"]):
            n = m["n"]
            lec = lire_profil_bordure(n["attrs"])
            if not lec:
                continue
            ev = evs[id(m)]
            lien_ok = (m["statut"] in PRESENCE and not m.get("invalidee") and not m.get("lien_groupe_non_prouve")
                       and not m.get("requalifiee"))
            vote_ok = lien_ok and ev["w_attribut"] > 0
            s, d = None, None
            if C is not None and n["p"] is not None and len(C) > 1:
                d, s = abscisse(n["p"], C)
            idx = None
            if s is not None and d <= 3.0 and ivs:
                idx = next((k for k, it in enumerate(ivs) if it["s0"] - 1e-6 <= s <= it["s1"] + 1e-6), len(ivs) - 1)
            for lu in lec:
                w_brut = n["w_conf"] * n["w_val"] * F_LECTURE[lu["lecture"]]
                rec = {"obs": n["id"], "champ": lu["champ"], "extrait": lu["extrait"], "lecture": lu["lecture"],
                       "attribut": lu["attribut"], "s_m": r3(s), "d_m": r3(d), "intervalle": idx,
                       "statut_obs": m["statut"], "stricte": self.est_stricte(ent, m),
                       "non_probant": ev["motifs"] or None, "poids_brut": round(w_brut, 3)}
                if lu["attribut"] == "vue_m":
                    rec["intervalle_lu_m"] = [lu["min"], lu["max"]]
                else:
                    rec["valeur"] = lu["valeur"]
                rec["poids"] = round(ev["w_attribut"] * F_LECTURE[lu["lecture"]], 3) if vote_ok and idx is not None else 0.0
                if rec["poids"] > 0:
                    votes[idx].append(rec)
                elif idx is None:
                    rec["sans_vote"] = "hors bordure ou sans abscisse"
                elif not lien_ok:
                    rec["sans_vote"] = "lien invalidé, groupé, automatique ou sans présence"
                else:
                    rec["sans_vote"] = "observation non probante pour 2026 (" + ", ".join(ev["motifs"]) + ")"
                lectures.append(rec)
                # contradictions : intervalle de l'observation et intervalles courants vus autour (± 5 m)
                if lu["attribut"] != "vue_m" or idx is None or not lien_ok or "FUS-VAL-03" in ev["motifs"] \
                        or w_brut < 0.15:
                    continue
                for k, it in enumerate(ivs):
                    if k != idx and not (it.get("role") == "courant" and it["s1"] - it["s0"] >= 2.0
                                         and it["s0"] < s + FENETRE_BORDURE_M and it["s1"] > s - FENETRE_BORDURE_M):
                        continue
                    vd = vue_a_abscisse(it, min(max(s, it["s0"]), it["s1"]))
                    if not vue_compatible(vd, rec["intervalle_lu_m"]):
                        candidats[k].append((rec, vd, k == idx))
        if not lectures:
            return
        out = {"lectures": lectures, "intervalles": [], "contradictions": [], "desaccords": []}
        r["regles"].update({"FUS-BOR-01", "FUS-BOR-02"})
        sh = (p.get("source") or {}).get("statut_hauteur")
        src_iv = (((p.get("prov") or {}).get("intervalles") or {}).get("src"))
        if sh in ("mesuree", "sans_ressaut_mesuree", "abaissee_mesuree"):
            origine = "mesurée au LiDAR 2021"
        else:
            origine = f"« {sh} » (a priori)"
        contra_txt = []
        for idx in sorted(set(votes) | set(candidats)):
            it = ivs[idx]
            V = votes.get(idx, [])
            vues = [v for v in V if v["attribut"] == "vue_m"]
            res = {"intervalle": idx, "s0": it["s0"], "s1": it["s1"], "role": it.get("role"), "profil_decrit": it.get("profil"),
                   "statut_hauteur": sh, "source_vue": src_iv, "obs": sorted({v["obs"] for v in V})}
            if vues:
                s_obs = [v["s_m"] for v in vues]
                vd = vue_a_abscisse(it, sum(s_obs) / len(s_obs))
                W_ = sum(v["poids"] for v in vues)
                vo = sum(v["poids"] * (v["intervalle_lu_m"][0] + v["intervalle_lu_m"][1]) / 2.0 for v in vues) / W_
                accord = all(vue_compatible(vd, v["intervalle_lu_m"]) for v in vues)
                res.update({"vue_decrite_m": r3(vd), "vue_observee_m": r3(vo), "profil_observe": profil_de_vue(vo),
                            "profil_decrit_classe": profil_de_vue(vd), "poids": round(W_, 3),
                            "verdict": "accord" if accord else "contradiction"})
                lo = max(v["intervalle_lu_m"][0] for v in vues)
                hi = min(v["intervalle_lu_m"][1] for v in vues)
                if lo > hi + 2 * TOL_VUE_M:
                    res["desaccord_lectures"] = True
                    out["desaccords"].append(idx)
                    self.conflit("bordure_vue_desaccord", "a_verifier", ent["id"], sorted({v["obs"] for v in vues}),
                                 f"intervalle {idx} (s {it['s0']:.1f}-{it['s1']:.1f} m) : lectures de vue incompatibles "
                                 + "; ".join(f"{v['obs']} {v['intervalle_lu_m']} « {v['extrait']} »" for v in vues),
                                 "photo rasante à moins de 5 m, mètre pliant contre la face")
                    r["conflits"].append("bordure_vue_desaccord")
            cands = candidats.get(idx, [])
            if cands:
                fortes = [c for c, _, _ in cands
                          if c["lecture"] in ("haute", "moyenne") and "FUS-DATE-02" not in (c["non_probant"] or [])]
                grav = "a_verifier" if fortes else "info"
                vd_ = cands[0][1]
                vo_ = sum((c["intervalle_lu_m"][0] + c["intervalle_lu_m"][1]) / 2.0 for c, _, _ in cands) / len(cands)
                r["regles"].add("FUS-BOR-03")
                res["verdict"] = "contradiction"
                res["decision"] = "revue_requise"
                lect = []
                txt = []
                for c, _, loc in cands:
                    lect.append({"obs": c["obs"], "s_m": c["s_m"], "intervalle_lu_m": c["intervalle_lu_m"],
                                 "extrait": c["extrait"], "lecture": c["lecture"], "poids_brut": c["poids_brut"],
                                 "stricte": c["stricte"], "non_probant": c["non_probant"],
                                 "position": "intervalle de l'observation" if loc else "intervalle voisin (± 5 m)"})
                    np_ = (", non probante " + "/".join(c["non_probant"])) if c["non_probant"] else ""
                    vs_ = "" if loc else ", intervalle voisin"
                    txt.append(f"{c['obs']} à s {c['s_m']} m « {c['extrait']} » -> {c['intervalle_lu_m']} m "
                               f"({c['lecture']}{np_}{vs_})")
                cv = {"intervalle": idx, "gravite": grav, "s0": it["s0"], "s1": it["s1"], "vue_decrite_m": r3(vd_),
                      "profil_decrit": it.get("profil"), "statut_hauteur": sh, "source_vue": src_iv, "lectures": lect,
                      "proposition": {"vue_m": r3(vo_), "profil": profil_de_vue(vo_), "decision": "revue_requise"}}
                out["contradictions"].append(cv)
                contra_txt.append((grav, sorted({c["obs"] for c, _, _ in cands}),
                                   f"intervalle {idx} (s {it['s0']:.1f}-{it['s1']:.1f} m, {it.get('profil')}, vue {vd_:.3f} m "
                                   f"{origine}) contre " + "; ".join(txt) + f" -> vue lue {vo_:.3f} m ({profil_de_vue(vo_)})"))
            abv = [v for v in V if v["attribut"] == "abaisse"]
            if abv:
                decrit = it.get("role") in ("bateau", "chartiere") or str(it.get("profil", "")).endswith("bateau")
                wt = sum(v["poids"] for v in abv if v["valeur"] is True)
                wf = sum(v["poids"] for v in abv if v["valeur"] is False)
                obs_ab = wt >= wf
                res["abaisse"] = {"decrit": decrit, "observe": obs_ab, "poids": round(max(wt, wf), 3),
                                  "verdict": "accord" if obs_ab == decrit else "contradiction"}
                if obs_ab != decrit:
                    self.conflit("bordure_abaisse_contradiction", "a_verifier", ent["id"], sorted({v["obs"] for v in abv}),
                                 f"intervalle {idx} : abaissé {'observé' if obs_ab else 'non observé'}, "
                                 f"{'décrit' if decrit else 'non décrit'} ({it.get('role')})", "vérifier sur le terrain")
                    r["conflits"].append("bordure_abaisse_contradiction")
            out["intervalles"].append(res)
            if res.get("verdict") == "accord":
                r["attributs_confirmes"].setdefault("vue_m", {"intervalles": [], "obs": []})
                r["attributs_confirmes"]["vue_m"]["intervalles"].append(idx)
                r["attributs_confirmes"]["vue_m"]["obs"] = sorted(set(r["attributs_confirmes"]["vue_m"]["obs"]) | set(res["obs"]))
        out["contradictions_a_verifier"] = [c["intervalle"] for c in out["contradictions"] if c["gravite"] == "a_verifier"]
        if contra_txt:
            grav = "a_verifier" if any(g == "a_verifier" for g, _, _ in contra_txt) else "info"
            reco = ("relever la vue sur le terrain (photo rasante à moins de 5 m, mètre pliant contre la face) avant de changer "
                    "le profil ; ne pas appliquer sans revue")
            if grav != "a_verifier":
                reco += " (lecture déduite, ou antérieure aux travaux dans leur emprise : information)"
            self.conflit("bordure_vue_contradiction", grav, ent["id"], sorted({o for _, os_, _ in contra_txt for o in os_}),
                         " | ".join(t for _, _, t in contra_txt), reco)
            r["conflits"].append("bordure_vue_contradiction" if grav == "a_verifier" else "bordure_vue_contradiction_info")
        r["bordure"] = out

    def src_of(self, oid):
        return self.index_obs[oid]["source"]

    def fusion_position(self, ent, M, r):
        if ent.get("G") is None:
            r["position"] = {"verdict": "sans_geometrie"}
            return
        if ent["G"]["type"] == "point":
            self.position_point(ent, M, r)
        else:
            self.position_geometrie(ent, M, r)

    def mesures(self, ent, M, inclure_projection=True):
        pd = ent["G"]["pt"]
        ms = []
        for m in M:
            n = m["n"]
            if m["role"] != "primaire" or not m["position_ok"] or n["p"] is None or n["sigma"] is None:
                continue
            if m["statut"] not in ("confirme", "attribut_corrige", "position_corrigee"):
                continue
            ev = self.evaluer(ent, m)
            if ev["w_position"] <= 0 or m.get("invalidee") or m.get("lien_groupe_non_prouve"):
                continue
            stricte = self.est_stricte(ent, m)
            date02 = "FUS-DATE-02" in ev["motifs"]
            mesure = (n["methode"] in ("triangulation", "rayon_sol") or bool(n.get("mesure_arbitree"))
                      or (n["methode"] == "pixel_ortho" and m["statut"] == "position_corrigee"))
            if not mesure:
                # « confirme » sans mesure du pied (projection de la description, pixel ortho d'une lanterne ou
                # d'une couronne...) : confirmation à la position décrite, jamais une mesure (FUS-POS-01)
                if not inclure_projection or m["statut"] != "confirme":
                    continue
                ms.append({"obs": n["id"], "p": pd.copy(), "sigma": n["sigma"], "sigma_brut": n["sigma_brut"], "methode": "confirmation",
                           "methode_obs": n["methode"], "source": n["source"], "w_val": n["w_val"], "statut": m["statut"], "n": n,
                           "stricte": stricte, "date02": date02})
            else:
                ms.append({"obs": n["id"], "p": n["p"], "sigma": n["sigma"], "sigma_brut": n["sigma_brut"], "methode": n["methode"],
                           "source": n["source"], "w_val": n["w_val"], "statut": m["statut"], "n": n, "stricte": stricte,
                           "date02": date02})
        # doublons de mesure (FUS-POS-01)
        ms.sort(key=lambda x: (x["sigma"], x["obs"]))
        uniq = []
        for x in ms:
            dup = next((u for u in uniq if u["methode"] == x["methode"] and float(np.hypot(*(u["p"] - x["p"]))) <= 0.01), None)
            if dup:
                dup.setdefault("doublons", []).append(x["obs"])
            else:
                uniq.append(x)
        return uniq

    def moyenne_robuste(self, ms, tol):
        actifs = list(ms)
        rejets = []
        while True:
            w = np.array([1.0 / x["sigma"] ** 2 for x in actifs])
            P = np.array([x["p"] for x in actifs])
            po = (P * w[:, None]).sum(0) / w.sum()
            so = 1.0 / math.sqrt(w.sum())
            if len(actifs) < 3 and not (len(actifs) == 2):
                return po, so, actifs, rejets
            res = []
            for x in actifs:
                d = float(np.hypot(*(x["p"] - po)))
                res.append((d / math.sqrt(x["sigma"] ** 2 + so ** 2), d, x))
            res.sort(key=lambda t: (-t[0], t[2]["obs"]))
            z, d, x = res[0]
            if z > 3.0 and d > tol and len(actifs) > 1:
                if len(actifs) == 2:
                    # deux mesures incompatibles : on garde la plus précise, l'autre est rejetée
                    x = max(actifs, key=lambda t: (t["sigma"], t["obs"]))
                actifs.remove(x)
                rejets.append(x)
                continue
            return po, so, actifs, rejets

    def position_point(self, ent, M, r):
        pd = ent["G"]["pt"]
        ms = self.mesures(ent, M)
        reelles = [x for x in ms if x["methode"] != "confirmation"]
        projections = sorted(x["obs"] for x in ms if x["methode"] == "confirmation")
        cls_tol = {"arbre": 2.0, "candelabre_poteau": 0.75, "panneau": 0.75, "feu": 0.75, "potelet_borne": 0.5}.get(ent["classe"], 1.0)
        if not ms:
            r["position"] = {"verdict": "non_mesure"}
            return
        # priorité photo 2026 (FUS-DATE-01) : mesures (ou confirmations) 2026 seules, les autres restent antérieures
        ms26 = [x for x in ms if x["n"]["categorie"] == "photo_2026"]
        anterieures = []
        if ms26 and len(ms26) < len(ms):
            anterieures = [x for x in ms if x["n"]["categorie"] != "photo_2026" and x["methode"] != "confirmation"]
            ms = ms26
            reelles = [x for x in ms if x["methode"] != "confirmation"]
            projections = sorted(x["obs"] for x in ms if x["methode"] == "confirmation")
            r["regles"].add("FUS-DATE-01")
        if reelles:   # une projection de la description ne mesure rien : elle ne sert qu'en l'absence de mesure (FUS-POS-01)
            ms = reelles
        po, so, actifs, rejets = self.moyenne_robuste(ms, cls_tol)
        if anterieures:
            ant = []
            for x in sorted(anterieures, key=lambda t: t["obs"]):
                dx = float(np.hypot(*(x["p"] - po)))
                ant.append({"obs": x["obs"], "methode": x["methode"], "categorie": x["n"]["categorie"],
                            "l93": [r3(x["p"][0]), r3(x["p"][1])], "d_position_2026_m": r3(dx)})
            r["mesures_anterieures"] = ant
            loin = [a for a, x in zip(ant, sorted(anterieures, key=lambda t: t["obs"]))
                    if a["d_position_2026_m"] > max(cls_tol, 3 * x["sigma_brut"])]
            if loin:
                self.conflit("position_anterieure_divergente", "info", ent["id"], [a["obs"] for a in loin] + sorted(x["obs"] for x in ms),
                             "mesures antérieures aux travaux à " + ", ".join(f"{a['obs']} {a['d_position_2026_m']} m" for a in loin)
                             + " de la position 2026 retenue (objet déplacé pendant les travaux ou mesure ancienne fausse)",
                             "position 2026 retenue (FUS-DATE-01)")
                r["conflits"].append("position_anterieure_divergente")
        for x in rejets:
            self.index_obs[x["obs"]]["mesure_rejetee"] = True
        if rejets:
            self.conflit("position_desaccord", "a_verifier", ent["id"], [x["obs"] for x in ms],
                         "mesures incompatibles : " + "; ".join(
                             f"{x['obs']} ({x['methode']}, σ {x['sigma']:.2f}) en {x['p'][0]:.2f}/{x['p'][1]:.2f}" for x in rejets)
                         + f" ; retenu {po[0]:.2f}/{po[1]:.2f}", "relire les planches ; ajouter une visée indépendante")
            r["conflits"].append("position_desaccord")
            r["regles"].add("FUS-POS-03")
        reelles_act = [x for x in actifs if x["methode"] != "confirmation"]
        d = float(np.hypot(*(po - pd)))
        sm = 1.0 / math.sqrt(sum(1.0 / x["sigma_brut"] ** 2 for x in actifs))   # σ de mesure (FUS-POS-04)
        pos = {"description_l93": [r3(pd[0]), r3(pd[1])], "fusion_l93": [r3(po[0]), r3(po[1])], "d_m": r3(d),
               "sigma_m": r3(sm), "sigma_pondere_m": r3(so), "n_mesures": len(actifs), "n_mesures_reelles": len(reelles_act),
               "methodes": sorted({x["methode"] for x in actifs}), "obs": sorted(x["obs"] for x in actifs),
               "rejets": sorted(x["obs"] for x in rejets), "sigma_description_m": r3(ent.get("sigma")),
               "preuve_description": ent.get("preuve"), "confirmations_sans_mesure": projections}
        r["regles"].add("FUS-POS-04")
        if not reelles_act:
            pos["verdict"] = "confirme_sans_mesure"
            r["position"] = pos
            return
        if d <= max(0.35, 3 * sm):
            pos["verdict"] = "confirme"
            r["position"] = pos
            return
        pos["verdict"] = "affinage" if d <= 0.75 else "deplacement"
        # application (FUS-POS-05/06)
        raisons = []
        valide_plein = any(x["w_val"] >= 1.0 for x in reelles_act)
        n_tri = sum(1 for x in reelles_act if x["methode"] == "triangulation")
        n_src = len({x["source"] for x in reelles_act})
        affirme = any(x["statut"] == "position_corrigee" and CONF_W.get(x["n"]["conf"], 0) >= 0.6 for x in reelles_act)
        sd = ent.get("sigma") or 1.0
        if not valide_plein:
            raisons.append("aucune mesure valide 2026 pleine (images antérieures aux travaux ou incertaines)")
        if sm > 0.5:
            raisons.append(f"σ fusion {sm:.2f} m > 0,5 m")
        if sm > max(sd, 0.30):
            raisons.append(f"σ fusion {sm:.2f} m > preuve de la description ({sd:.2f} m)")
        if not (n_tri >= 1 or n_src >= 2 or affirme):
            raisons.append("une seule source non triangulée et pas de correction affirmée")
        if not any(x["stricte"] for x in reelles_act):
            raisons.append("aucune mesure stricte (FUS-COUV-02)")
        if all(x["date02"] for x in reelles_act):
            raisons.append("mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02)")
            r["regles"].add("FUS-DATE-02")
        if sd <= 0.05 and d > 0.5:
            raisons.append("objet levé GAM : déplacement > 0,5 m (FUS-POS-06)")
            r["regles"].add("FUS-POS-06")
        pos["decision"] = "appliquer" if not raisons else "revue_requise"
        pos["raisons"] = raisons
        r["regles"].add("FUS-POS-05")
        r["position"] = pos
        if raisons:
            self.conflit("deplacement_non_etaye", "a_verifier", ent["id"], pos["obs"],
                         f"{pos['verdict']} de {d:.2f} m proposé ; " + " ; ".join(raisons),
                         "revue visuelle des planches avant application")
            r["conflits"].append("deplacement_non_etaye")

    def position_geometrie(self, ent, M, r):
        G = ent["G"]
        ms = []
        for m in M:
            n = m["n"]
            if m["role"] != "primaire" or n["p"] is None or n["sigma"] is None:
                continue
            if m["statut"] not in ("position_corrigee", "confirme", "attribut_corrige"):
                continue
            if n["methode"] == "projection_description":
                continue
            ev = self.evaluer(ent, m)
            if ev["w_position"] <= 0 or m.get("invalidee") or m.get("lien_groupe_non_prouve"):
                continue
            d, q = dist_geom(n["p"], G)
            ref = q
            mref = "point_le_plus_proche"
            mm = RE_AU_LIEU.search(n["atxt"])
            if mm:
                ref = np.array([fnum(mm.group(1)) + self.ix.O[0], fnum(mm.group(2)) + self.ix.O[1]])
                mref = "au_lieu_de"
            v = n["p"] - ref
            ms.append({"obs": n["id"], "v": v, "d": float(np.hypot(*v)), "sigma": n["sigma_brut"], "statut": m["statut"],
                       "methode": n["methode"], "source": n["source"], "ref": mref, "w_val": n["w_val"], "q": ref,
                       "p": n["p"], "conf": n["conf"], "categorie": n["categorie"], "stricte": self.est_stricte(ent, m),
                       "date02": "FUS-DATE-02" in ev["motifs"]})
        if not ms:
            r["position"] = {"verdict": "non_mesure"}
            return
        ms26 = [x for x in ms if x["categorie"] == "photo_2026"]
        if ms26 and len(ms26) < len(ms):   # priorité photo 2026 (FUS-DATE-01)
            r["mesures_anterieures"] = [{"obs": x["obs"], "methode": x["methode"], "categorie": x["categorie"],
                                         "ecart_m": r3(x["d"])} for x in sorted(ms, key=lambda t: t["obs"]) if x not in ms26]
            ms = ms26
            r["regles"].add("FUS-DATE-01")
        seuil_min = 0.10 if ent["famille"] in ("marquages", "retire_v03") else 0.20
        corr = [x for x in ms if x["statut"] == "position_corrigee"]
        conf_ = [x for x in ms if x["statut"] != "position_corrigee"]
        out = {"type_geometrie": G["type"], "mesures": []}
        for x in sorted(ms, key=lambda t: t["obs"]):
            out["mesures"].append({"obs": x["obs"], "statut": x["statut"], "methode": x["methode"],
                                   "ecart_m": r3(x["d"]), "vecteur_m": [r3(x["v"][0]), r3(x["v"][1])],
                                   "sigma_m": r3(x["sigma"]), "reference": x["ref"]})
        r["regles"].add("FUS-POS-07")
        sig = [x for x in corr if x["d"] > max(seuil_min, 3 * x["sigma"])]
        if sig:
            w = np.array([1 / x["sigma"] ** 2 for x in sig])
            V = np.array([x["v"] for x in sig])
            v = (V * w[:, None]).sum(0) / w.sum()
            so = 1 / math.sqrt(w.sum())
            dd = float(np.hypot(*v))
            ref = min(sig, key=lambda t: (t["sigma"], t["obs"]))
            out.update({"verdict": "translation", "vecteur_m": [r3(v[0]), r3(v[1])], "d_m": r3(dd), "sigma_m": r3(so),
                        "point_reference_l93": [r3(ref["q"][0]), r3(ref["q"][1])],
                        "point_mesure_l93": [r3(ref["q"][0] + v[0]), r3(ref["q"][1] + v[1])],
                        "obs": sorted(x["obs"] for x in sig)})
            raisons = []
            if not any(x["w_val"] >= 1.0 for x in sig):
                raisons.append("aucune mesure valide 2026 pleine")
            if so > 0.5:
                raisons.append(f"σ {so:.2f} m > 0,5 m")
            if not any(CONF_W.get(x["conf"], 0) >= 0.6 for x in sig):
                raisons.append("confiance faible")
            if not any(x["stricte"] for x in sig):
                raisons.append("aucune mesure stricte (FUS-COUV-02)")
            if all(x["date02"] for x in sig):
                raisons.append("mesures antérieures aux travaux, dans leur emprise, sans appui de conservation (FUS-DATE-02)")
            if (ent.get("sigma") or 1) <= 0.05 and dd > 0.5:
                raisons.append("géométrie levée GAM : translation > 0,5 m (FUS-POS-06)")
            out["decision"] = "appliquer" if not raisons else "revue_requise"
            out["raisons"] = raisons
            if raisons:
                self.conflit("deplacement_non_etaye", "a_verifier", ent["id"], out["obs"],
                             f"translation de {dd:.2f} m proposée ; " + " ; ".join(raisons),
                             "revue visuelle avant application")
                r["conflits"].append("deplacement_non_etaye")
        else:
            tol = {"marquages": 0.5, "bordures": 0.5, "bordures_site": 0.5}.get(ent["famille"], 1.0)
            loin = [x for x in conf_ if x["d"] > max(tol, 3 * x["sigma"])]
            out["verdict"] = "confirme" if conf_ and not loin else ("non_mesure" if not conf_ else "confirmation_eloignee")
            if loin:
                self.conflit("position_desaccord", "info", ent["id"], [x["obs"] for x in loin],
                             "observation « confirme » à " + ", ".join(f"{x['d']:.2f} m" for x in loin) + " de la géométrie",
                             "vérifier l'appariement (autre entité voisine ?)")
                r["conflits"].append("confirmation_eloignee")
        r["position"] = out

    def controle_coherence(self, ent, r):
        cs = self.corr_coh.get(ent["id"])
        if not cs:
            return
        O = self.ix.O
        for c in cs:
            rec = {"entite": ent["id"], "nature": c["nature"], "statut_resolution": c["statut_resolution"],
                   "d_coherence_m": c.get("d_m"), "revue_coherence": c.get("revue") if isinstance(c.get("revue"), str) else None}
            pos = r.get("position") or {}
            ps = np.array(c["p_source_local"], float) + np.array(O)
            pr_ = np.array(c["p_resolu_local"], float) + np.array(O)
            if "deplacement" in c["nature"] and pos.get("n_mesures_reelles"):
                po = np.array(pos["fusion_l93"], float)
                so = pos["sigma_m"]
                tol = max(0.35, 2 * so)
                dres = float(np.hypot(*(po - pr_)))
                dsrc = float(np.hypot(*(po - ps)))
                if dres <= tol and dsrc <= tol:
                    # les deux positions sont dans la tolérance : tendance si l'écart les départage d'au moins σ
                    v = "indifferent" if abs(dres - dsrc) < so else ("tendance_accord" if dres < dsrc else "tendance_desaccord")
                elif dres <= tol:
                    v = "accord"
                elif dsrc <= tol:
                    v = "desaccord"
                else:
                    v = "partiel"
                rec.update({"verdict": v, "d_image_corrige_m": r3(dres), "d_image_origine_m": r3(dsrc),
                            "sigma_image_m": so, "fusion_l93": pos["fusion_l93"],
                            "coherence_resolu_l93": [r3(pr_[0]), r3(pr_[1])], "obs": pos["obs"]})
                if v in ("desaccord", "partiel"):
                    self.conflit("coherence_desaccord", "a_verifier", ent["id"], pos["obs"],
                                 f"cohérence : {c['nature']} de {c.get('d_m')} m ; image à {dres:.2f} m de la position corrigée "
                                 f"et {dsrc:.2f} m de l'origine ({v})",
                                 "position image prioritaire si la décision de fusion est « appliquer » ; sinon revue")
                    r["conflits"].append("coherence_desaccord")
            elif "deplacement" in c["nature"] and (pos.get("verdict") == "confirme_sans_mesure"):
                rec.update({"verdict": "non_conclu_sans_mesure", "obs": pos.get("obs"),
                            "note": "seules des confirmations sans mesure du pied (projection, couronne ou lanterne sur l'ortho) : non concluant"})
            if "reorientation" in c["nature"] or c["nature"] == "deplacement+reorientation":
                az = (r.get("maj") or {}).get("azimut_deg") or {}
                azv = az.get("apres")
                if azv is None and "azimut_deg" in (r.get("attributs_confirmes") or {}):
                    azv = r["attributs_confirmes"]["azimut_deg"]["valeur"]
                if azv is not None and c.get("azimut_resolu_deg") is not None:
                    da = angle_diff(float(azv), float(c["azimut_resolu_deg"]))
                    vaz = "accord" if da <= 30 else ("desaccord" if c.get("azimut_source_deg") is not None and
                                                      angle_diff(float(azv), float(c["azimut_source_deg"])) <= 30 else "partiel")
                    rec.update({"verdict_azimut": vaz, "azimut_image_deg": azv, "azimut_coherence_deg": c["azimut_resolu_deg"]})
                    if vaz != "accord":
                        self.conflit("coherence_desaccord", "a_verifier", ent["id"], az.get("obs") or [],
                                     f"azimut image {azv}° contre cohérence {c['azimut_resolu_deg']}°", "relire les faces sur photo")
                        r["conflits"].append("coherence_desaccord_azimut")
            if c["nature"] == "non_instanciation":
                ex = r["existence"]
                pres_valide = [o for o in ex["obs"].get("presence", []) if self.index_obs[o]["poids_validite"] >= 1.0]
                rec.update({"verdict": "desaccord" if pres_valide else "non_contredit", "obs": sorted(ex["obs"].get("presence", []))})
                if pres_valide:
                    self.conflit("coherence_desaccord", "a_verifier", ent["id"], pres_valide,
                                 "cohérence : non instancié ; présence observée sur une image jugée valide 2026",
                                 "vérifier sur image postérieure aux travaux")
                    r["conflits"].append("coherence_desaccord")
            if "verdict" in rec or "verdict_azimut" in rec:
                rec["regle"] = "FUS-COH-01"
                self.controle_coh.append(rec)
                r.setdefault("coherence", []).append(rec)
                r["regles"].add("FUS-COH-01")

    # -------- 3. ajouts --------
    def existant_leve_gam(self, cls, g, G, pt, rayon):
        """Entité levée GAM de même classe (type de marquage compatible) à moins de `rayon` (FUS-ADD-04)."""
        ix = self.ix
        types_obs = {type_marquage_obs(n["sous_type"]) for n in g} if cls == "marquage" else set()
        agents = {n["agent"] for n in g}
        best = None
        for fam, types in FAM_SPATIALE.get(cls, []):
            for eid in ix.par_famille.get(fam, []):
                e = ix.E[eid]
                if not e.get("leve_gam") or e.get("G") is None:
                    continue
                if types is not None and e["type"] not in types:
                    continue
                if cls == "marquage" and None not in types_obs and e["type"] not in types_obs:
                    continue
                if not (e["G"]["bbox"][0] - rayon <= G["bbox"][2] and G["bbox"][0] - rayon <= e["G"]["bbox"][2]
                        and e["G"]["bbox"][1] - rayon <= G["bbox"][3] and G["bbox"][1] - rayon <= e["G"]["bbox"][3]):
                    continue
                d = dist_geom(pt, e["G"])[0] if G["type"] == "point" else dist_geoms(G, e["G"])
                if d > rayon + 1e-9:
                    continue
                # le même atelier a confirmé à la main l'entité levée : il distingue les deux objets
                if any(m["n"]["agent"] in agents and not m["n"]["auto"] and m["role"] == "primaire"
                       and (m["statut"] == "confirme" or (m["statut"] == "attribut_corrige" and not any(
                           k in m["n"]["attrs"] for k in ("classe_proposee", "type_propose", "type_reel"))))
                       for m in self.membres.get(eid, [])):
                    continue
                if best is None or (d, eid) < best:
                    best = (d, eid)
        return best

    def ancrer_bord(self, pt, arb):
        """Point ramené au bord de l'îlot / espace vert le plus proche, en retrait vers l'intérieur (FUS-ARB-01)."""
        pa = arb.get("parametres") or {}
        rayon = float(pa.get("rayon_m", 3.0))
        retrait = float(pa.get("retrait_m", 0.3))
        classes = set(pa.get("classes_hote") or ["espace_vert"])
        best = None
        for fam in ("ilots", "surfaces", "surfaces_v1"):
            for eid in self.ix.par_famille.get(fam, []):
                e = self.ix.E[eid]
                if fam != "ilots" and e["type"] not in classes:
                    continue
                if not bbox_proche(e["G"]["bbox"], pt, rayon):
                    continue
                for pg in e["G"]["polys"]:
                    d, q, k = segment_le_plus_proche(pt, pg[0])
                    if d <= rayon and (best is None or (d, eid) < (best[0], best[1])):
                        best = (d, eid, q, pg[0], k)
        if best is None:
            return None
        d, eid, q, R, k = best
        t = R[k + 1] - R[k]
        nt = float(np.hypot(*t))
        c = q
        if nt > 0:
            nrm = np.array([-t[1], t[0]]) / nt
            for s in (1.0, -1.0):
                if dans_anneau(q + s * retrait * nrm, R):
                    c = q + s * retrait * nrm
                    break
        return c, {"hote": eid, "famille_hote": self.ix.E[eid]["famille"], "type_hote": self.ix.E[eid]["type"],
                   "d_bord_m": r3(d), "deplacement_m": r3(float(np.hypot(*(c - pt)))), "retrait_m": retrait,
                   "point_initial_l93": [r3(pt[0]), r3(pt[1])], "arbitrage": arb["id"], "regle": "FUS-ARB-01"}

    def regrouper_ajouts(self):
        L = sorted(self.non_lies, key=lambda n: n["id"])
        parent = list(range(len(L)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                a, b = L[i], L[j]
                ga, gb = GROUPE_AJOUT.get(a["classe"], "autre"), GROUPE_AJOUT.get(b["classe"], "autre")
                if ga != gb:
                    continue
                tol = max(TOL_CLASSE.get(a["classe"], 1.0), TOL_CLASSE.get(b["classe"], 1.0))
                if a["agent"] == b["agent"]:
                    # un atelier ortho (une seule image) liste des objets distincts ; un atelier photo peut revoir
                    # le même objet sur deux photos : même sous-type, objets ponctuels, à la tolérance de classe
                    if not a["photo"] or a["sous_type"] != b["sous_type"] \
                            or a["G"]["type"] != "point" or b["G"]["type"] != "point":
                        continue
                    seuil = tol
                else:
                    sa = a["sigma_brut"] if a.get("sigma_brut") else float(a["prec"] or 1.0)
                    sb = b["sigma_brut"] if b.get("sigma_brut") else float(b["prec"] or 1.0)
                    ta = set(re.split(r"[_\W\d]+", a["sous_type"].lower())) - {"", "de", "du", "la", "le", "et", "ou"}
                    tb = set(re.split(r"[_\W\d]+", b["sous_type"].lower())) - {"", "de", "du", "la", "le", "et", "ou"}
                    compatibles = bool(ta & tb) or ga in ("ponctuel", "arbre", "vegetal")
                    seuil = tol + min(sa + sb, 3.0) if compatibles else tol
                ba, bb = a["G"]["bbox"], b["G"]["bbox"]
                if ba[0] - seuil > bb[2] or bb[0] - seuil > ba[2] or ba[1] - seuil > bb[3] or bb[1] - seuil > ba[3]:
                    continue
                if dist_geoms(a["G"], b["G"]) <= seuil:
                    parent[find(j)] = find(i)
        groupes = defaultdict(list)
        for i in range(len(L)):
            groupes[find(i)].append(L[i])
        return [sorted(g, key=lambda n: n["id"]) for g in groupes.values()]

    def construire_ajouts(self):
        ix = self.ix
        bruts = []
        for g in self.regrouper_ajouts():
            classes = Counter(n["classe"] for n in g)
            cls = sorted(classes.items(), key=lambda t: (-t[1], t[0]))[0][0]
            groupe = GROUPE_AJOUT.get(cls, "autre")
            pts = [n for n in g if n["G"]["type"] == "point" and n["sigma"] is not None]
            geoms = [n for n in g if n["G"]["type"] != "point"]
            conflits = []
            if geoms:
                best = min(geoms, key=lambda n: (float(n["prec"] or 9), n["id"]))
                G = best["G"]
                pt = G["pt"]
                so = float(best["prec"] or 1.0)
                geo_src = f"{best['id']}:{G.get('source_geom')}"
            elif pts:
                ms = [{"obs": n["id"], "p": n["p"], "sigma": n["sigma"], "methode": n["methode"]} for n in pts]
                pt, so, actifs, rejets = self.moyenne_robuste(ms, TOL_CLASSE.get(cls, 1.0))
                G = construire_geom([pt], [], [])
                geo_src = "moyenne_ponderee:" + ",".join(sorted(x["obs"] for x in actifs))
                if rejets:
                    conflits.append(("position_desaccord", [x["obs"] for x in ms]))
            else:
                n0 = g[0]
                G = n0["G"]
                pt = G["pt"]
                so = float(n0["prec"] or 1.0)
                geo_src = f"{n0['id']}:{G.get('source_geom')}"
            # arbitrages de revue (FUS-ARB-01)
            arb_non = next((a for n in g for a in [self.arbitrage(n, "ne_pas_instancier")] if a), None)
            arb_anc = next((a for n in g for a in [self.arbitrage(n, "ancrer_bord_ilot")] if a), None)
            ancrage = None
            if arb_anc is not None:
                res_anc = self.ancrer_bord(pt, arb_anc) if G["type"] == "point" else None
                if res_anc:
                    pt, ancrage = res_anc
                    G = construire_geom([pt], [], [])
                    geo_src += f" ; ancré au bord de {ancrage['hote']} ({arb_anc['id']})"
                    arb_anc["_applique"].append(ancrage["hote"])
                else:
                    self.conflit("arbitrage_inapplicable", "a_verifier", arb_anc["id"], [n["id"] for n in g],
                                 f"arbitrage {arb_anc['id']} (ancrer_bord_ilot) : aucun îlot ni espace vert à moins de "
                                 f"{(arb_anc.get('parametres') or {}).get('rayon_m', 3.0)} m", "mettre à jour arbitrages_fusion.json")
            if arb_non is not None:
                arb_non["_applique"].append(",".join(n["id"] for n in g))
            valeurs = [n["valide"] for n in g]
            vmax = True if True in valeurs else ("incertain" if "incertain" in valeurs else False)
            conf_max = max((n["conf"] for n in g), key=lambda c: CONF_W.get(c, 0))
            # attributs
            votes = defaultdict(list)
            genres = {}
            for n in g:
                w = n["w_conf"] * n["w_val"]
                for attr, genre, val, f, cle in extraire_attributs(n, None, self.vocab):
                    votes[attr].append((val, w * f if w > 0 else 0.05 * f, n["id"]))
                    genres[attr] = genre
            attrs = {}
            for attr in sorted(votes):
                res = voter(votes[attr], attr, genres.get(attr))
                if res is None:
                    continue
                attrs[attr] = {"valeur": res["valeur"], "poids": res["poids"], "obs": res["obs"]}
                if res["conflit"]:
                    conflits.append((f"attribut_desaccord:{attr}", res["obs"]))
            # nombre d'objets cités
            for n in g:
                if isinstance(n["attrs"].get("nombre"), (int, float)):
                    attrs.setdefault("nombre", {"valeur": int(n["attrs"]["nombre"]), "obs": [n["id"]]})
            desc = []
            for n in g:
                for k in ("observe", "objet", "description", "note", "observation", "constat", "forme", "type", "interpretation"):
                    if k in n["attrs"] and isinstance(n["attrs"][k], str):
                        desc.append({"obs": n["id"], "texte": court(n["attrs"][k], 220)})
                        break
            # proximité d'entités existantes (FUS-ADD-02)
            proche = None
            hotes = sorted({h for n in g for h in n.get("hotes", [])})
            associes = sorted({h for n in g for h in n.get("liens_associes", [])})
            if cls in ("surface", "ilot"):
                # une sous-zone ou une reprise est toujours dans une surface : c'est son hôte, pas un doublon
                b = plus_proche(ix, pt, [("surfaces", None)], 0.0)
                if b and b[1] not in hotes:
                    hotes.append(b[1])
            elif cls in FAM_SPATIALE:
                tol = TOL_CLASSE.get(cls, 1.0)
                rayon = max(RAYON_DEDOUBLONNAGE_M, tol)
                b = plus_proche(ix, pt, FAM_SPATIALE[cls], rayon)
                equipement = all(re.search(r"bo[iî]tier|tete|panonceau|plaque|camera", n["sous_type"]) for n in g)
                if b:
                    proche = {"entite": b[1], "d_m": r3(b[0]), "leve_gam": bool(ix.E[b[1]].get("leve_gam"))}
                    if equipement:
                        # équipement porté (boîtier, plaque, panonceau) : le support voisin est son hôte, pas un doublon
                        if b[1] not in hotes:
                            hotes.append(b[1])
                    elif b[0] <= max(tol / 2.0, 0.25) and G["type"] == "point":
                        conflits.append(("ajout_proche_existant", [n["id"] for n in g]))
                # dédoublonnage contre le levé GAM (FUS-ADD-04) : conflit au lieu d'un ajout
                gam = None if equipement else self.existant_leve_gam(cls, g, G, pt, rayon)
                if gam is not None:
                    d_g, eid_g = gam
                    e_g = ix.E[eid_g]
                    sts = sorted({n["sous_type"] for n in g})
                    prop = {"classe": cls, "sous_types": sts, "l93": [r3(pt[0]), r3(pt[1])],
                            "local": [r3(pt[0] - ix.O[0]), r3(pt[1] - ix.O[1])], "geometrie": geojson_geom(G),
                            "obs": [n["id"] for n in g], "d_m": r3(d_g), "valide_2026": [n["valide"] for n in g],
                            "categories": sorted({n["categorie"] for n in g})}
                    self.ajouts_refuses.append({"entite_gam": eid_g, **prop})
                    self.conflit("ajout_contre_leve_gam", "a_verifier", eid_g, [n["id"] for n in g],
                                 f"objet observé absent de la description ({', '.join(sts)}) à {d_g:.2f} m de {eid_g} "
                                 f"({e_g['famille']} {e_g['type']}, levé GAM) : même objet probable ; ajout non créé (FUS-ADD-04)",
                                 "trancher sur photo 2026 ou terrain : déplacer / retyper l'objet levé, ou créer l'ajout s'il est distinct",
                                 proposition=prop)
                    for n in g:
                        tr = self.index_obs[n["id"]]
                        tr["role"] = "conflit_ajout"
                        tr["regle"] = "FUS-ADD-04"
                        tr["entite_gam_proche"] = eid_g
                    continue
            # références croisées (FUS-ADD-03)
            xref = {}
            for f in self.props_coh:
                gg = geom_norm(f.get("geometry"))
                if gg is None:
                    continue
                d, _ = dist_geom(pt, gg)
                if d <= 3.0:
                    xref.setdefault("propositions_coherence", []).append({"id": f["properties"]["id"],
                                                                         "type": f["properties"].get("type"), "d_m": r3(d)})
            if cls == "arbre" and len(self.gam_arbres):
                dd = np.hypot(self.gam_arbres[:, 0] - pt[0], self.gam_arbres[:, 1] - pt[1])
                k = int(dd.argmin())
                xref["gam_2026_arbre_le_plus_proche_m"] = r3(dd[k])
                xref["gam_2026_corrobore"] = bool(dd[k] <= 2.0)
            temporaire = any(n["temporaire"] for n in g)
            fam_cible = FAMILLE_CIBLE.get(cls)
            raisons = []
            if not any(n["valide"] is True and CONF_W.get(n["conf"], 0) >= 0.6 for n in g):
                raisons.append("aucune observation valide 2026 en confiance ≥ moyenne")
            if temporaire:
                raisons.append("objet temporaire (FUS-TMP-01)")
            if fam_cible is None:
                raisons.append("famille cible inexistante dans la description")
            if any(c[0] == "ajout_proche_existant" for c in conflits):
                raisons.append("entité existante très proche (FUS-ADD-02)")
            d_zone = self.distance_zone_geom(G, ("ajout", round(float(pt[0]), 3), round(float(pt[1]), 3)))
            if d_zone <= EMPRISE_MARGE_M and not any((n["date"] or "") >= FIN_TRAVAUX and n["valide"] is True
                                                     and CONF_W.get(n["conf"], 0) >= 0.6 for n in g):
                raisons.append("vu seulement avant la fin des travaux, dans leur emprise (FUS-DATE-02)")
            st_ = [n for n in g if not n["auto"] and n["type_source"] != "web" and n["valide"] is True
                   and CONF_W.get(n["conf"], 0) >= 0.6 and n["statut"] != "incertain"]
            if any((n["date"] or "") >= FIN_TRAVAUX for n in st_):
                tranche_s = "apres_travaux"
            elif st_ and d_zone > EMPRISE_MARGE_M:
                tranche_s = "avant_travaux_hors_emprise"
            else:
                tranche_s = "indice_seulement"
            if all(n["statut"] == "incertain" for n in g):
                raisons.append("observations « incertain » seulement")
            if arb_non is not None:
                raisons.append(f"arbitrage {arb_non['id']} (FUS-ARB-01) : {arb_non.get('motif', '')}")
            if ancrage and ancrage["hote"] not in hotes:
                hotes.append(ancrage["hote"])
            cats_g = {n["categorie"] for n in g if n["w_val"] > 0}
            bruts.append({"groupe": groupe, "classe": cls, "G": G, "pt": pt, "sigma": so, "geo_src": geo_src,
                          "hotes": sorted(hotes), "liens_associes": associes,
                          "membres": g, "valide": vmax, "conf": conf_max, "attrs": attrs, "desc": desc, "proche": proche,
                          "xref": xref, "fam_cible": fam_cible, "instancier": not raisons, "raisons": raisons,
                          "conflits": conflits, "ancrage": ancrage,
                          "categorie_preuve": next((c for c in CATEGORIES if c in cats_g), None),
                          "tranche_stricte": tranche_s, "d_zone_travaux_m": r3(d_zone) if math.isfinite(d_zone) else None,
                          "arbitrages": sorted({a["id"] for a in (arb_non, arb_anc) if a is not None})})
        # identifiants déterministes
        compteur = Counter()
        for a in sorted(bruts, key=lambda a: (CODE_AJOUT.get(a["groupe"], "AUT"), round(float(a["pt"][0]), 2), round(float(a["pt"][1]), 2), a["membres"][0]["id"])):
            code = CODE_AJOUT.get(a["groupe"], "AUT")
            compteur[code] += 1
            a["id"] = f"ENR-{code}-{compteur[code]:03d}"
            for typ, obs in a["conflits"]:
                self.conflit(typ.split(":")[0], "a_verifier", a["id"], obs,
                             {"position_desaccord": "positions incompatibles entre observations du même objet",
                              "ajout_proche_existant": f"entité existante {a['proche']['entite'] if a['proche'] else '?'} à {a['proche']['d_m'] if a['proche'] else '?'} m",
                              }.get(typ.split(":")[0], typ),
                             "vérifier qu'il ne s'agit pas d'un doublon" if typ.startswith("ajout") else "relire les observations")
            for n in a["membres"]:
                self.index_obs[n["id"]]["ajout"] = a["id"]
                self.index_obs[n["id"]]["role"] = "ajout"
            if a["valide"] == "incertain" and a["instancier"] is False and any(n["statut"] == "absent_de_description" for n in a["membres"]):
                pass
            self.ajouts.append(a)
        self.ajouts.sort(key=lambda a: a["id"])
        # propositions de cohérence rejointes par une observation (hôte ADD-*) : corroboration datée (FUS-COH-01)
        for a in self.ajouts:
            for h in a["hotes"]:
                if h.startswith("ADD-"):
                    self.controle_coh.append({
                        "entite": h, "nature": "proposition_ajout", "statut_resolution": "proposition",
                        "d_coherence_m": None, "ajout": a["id"], "obs": sorted(n["id"] for n in a["membres"]),
                        "verdict": "corrobore" if a["valide"] is True else "corrobore_avant_travaux",
                        "note": "objet de la proposition vu sur image ; date : "
                                + ", ".join(sorted({n["date"] or "?" for n in a["membres"]})),
                        "regle": "FUS-COH-01"})
        for a in self.ajouts:
            if a["valide"] != True and any(n["statut"] == "absent_de_description" for n in a["membres"]):
                self.conflit("validite_2026_douteuse", "info", a["id"], [n["id"] for n in a["membres"]],
                             f"ajout vu seulement sur images non valables ou incertaines pour 2026 (valide {a['valide']})",
                             "non instancié ; à vérifier sur image 2026")
        # arbitrages d'ajout sans effet (FUS-ARB-01)
        for arb in self.arbitrages:
            if arb.get("action") in ("ne_pas_instancier", "ancrer_bord_ilot") and not arb["_applique"] \
                    and not any(c["type"] == "arbitrage_inapplicable" and c["cible"] == arb["id"] for c in self.conflits):
                self.conflit("arbitrage_inapplicable", "a_verifier", arb["id"], arb.get("obs", []),
                             f"arbitrage {arb['id']} ({arb.get('action')}) : observations hors des ajouts de cette exécution",
                             "mettre à jour arbitrages_fusion.json")

    # -------- contrôles transverses --------
    def doublons_apres_correction(self):
        """FUS-POS-08 : un objet déplacé ne doit pas tomber sur un autre objet de même classe."""
        ix = self.ix
        classes = {"candelabre_poteau", "feu", "potelet_borne", "mobilier", "arbre"}
        finale = {}
        for eid, e in ix.E.items():
            if e["famille"] in ("mobilier", "arbres") and e.get("G") and e["G"]["type"] == "point" and e["classe"] in classes:
                p = e["G"]["pt"]
                pos = (self.res_entites.get(eid) or {}).get("position") or {}
                if pos.get("verdict") in ("affinage", "deplacement"):
                    p = np.array(pos["fusion_l93"], float)
                finale[eid] = p
        for eid in sorted(self.res_entites):
            pos = self.res_entites[eid].get("position") or {}
            if pos.get("verdict") not in ("affinage", "deplacement") or eid not in finale:
                continue
            c1 = ix.E[eid]["classe"]
            for oid in sorted(finale):
                if oid == eid or ix.E[oid]["classe"] != c1:
                    continue
                d = float(np.hypot(*(finale[eid] - finale[oid])))
                if d <= 0.75:
                    self.conflit("doublon_apres_correction", "a_verifier", eid, pos["obs"],
                                 f"position corrigée à {d:.2f} m de {oid} ({ix.E[oid]['type']}) : même objet probable",
                                 f"fusionner {eid} et {oid} (garder un seul objet au point mesuré)")
                    self.res_entites[eid]["conflits"].append("doublon_apres_correction")
                    self.res_entites[eid]["regles"].append("FUS-POS-08")

    def controle_boutons(self):
        """Bouton d'appel : contrôle des propositions de cohérence (FEU-08) contre les observations (FUS-COH-01)."""
        props = [f for f in self.props_coh if (f["properties"].get("type_tete") or "") == "boitier_bouton_appel"]
        for eid in sorted(self.res_entites):
            r = self.res_entites[eid]
            b = (r.get("maj") or {}).get("bouton_appel")
            ent = self.ix.E[eid]
            if not b or b["apres"] is not False or ent.get("G") is None:
                continue
            for f in props:
                g = geom_norm(f.get("geometry"))
                d, _ = dist_geom(g["pt"], ent["G"])
                if d <= 8.0:
                    pid = f["properties"]["id"]
                    rec = {"entite": eid, "nature": "proposition_ajout", "statut_resolution": f["properties"].get("statut"),
                           "d_coherence_m": None, "proposition": pid, "verdict": "desaccord", "obs": b["obs"],
                           "note": f"observations : pas de bouton d'appel ; cohérence : {f['properties'].get('justification')}",
                           "regle": "FUS-COH-01"}
                    self.controle_coh.append(rec)
                    r.setdefault("coherence", []).append(rec)
                    self.conflit("coherence_desaccord", "a_verifier", eid, b["obs"],
                                 f"proposition {pid} (boîtier d'appel, FEU-08) contredite par {', '.join(b['obs'])} "
                                 f"(pas de bouton d'appel sur la traversée {eid})",
                                 "ne pas instancier la proposition sans photo 2026")
                    r["conflits"].append("coherence_desaccord")

    # -------- exécution --------
    def executer(self):
        self.lier()
        self.appliquer_invalidations()
        self.preparer_zone()
        self.requalifier_automatiques()
        for eid in sorted(self.membres):
            self.res_entites[eid] = self.fusion_entite(eid, self.membres[eid])
        self.doublons_apres_correction()
        self.controle_boutons()
        self.construire_ajouts()
        # numérotation des conflits
        self.conflits.sort(key=lambda c: (c["type"], str(c["cible"]), c["obs"]))
        for k, c in enumerate(self.conflits, 1):
            c["id"] = f"CF-ENR-{k:03d}"
        par_cible = defaultdict(list)
        for c in self.conflits:
            par_cible[c["cible"]].append(c["id"])
        for eid, r in self.res_entites.items():
            r["conflits_ids"] = par_cible.get(eid, [])
        for a in self.ajouts:
            a["conflits_ids"] = par_cible.get(a["id"], [])
        for oid, tr in self.index_obs.items():
            tr["conflits"] = sorted({c["id"] for c in self.conflits if oid in c["obs"]})


# --------------------------------------------------------------------------------------------
# Écriture
# --------------------------------------------------------------------------------------------

def fc_entete(nom, role, ix):
    return {"type": "FeatureCollection", "name": nom,
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
            "description_v2": {"schema": "description_scene_v2/enrichi/0.1", "generateur": VERSION, "couche": nom,
                               "repere": f"EPSG:2154 ; local = L93 - ({ix.O[0]}, {ix.O[1]})", "role": role,
                               "regles": "voir RESUME.md (FUS-*)"},
            "features": []}


def geojson_geom(G):
    if G["type"] == "point":
        p = G["pts"][0]
        return {"type": "Point", "coordinates": [r3(p[0]), r3(p[1])]}
    if G["type"] == "multipoint":
        return {"type": "MultiPoint", "coordinates": [[r3(p[0]), r3(p[1])] for p in G["pts"]]}
    if G["type"] == "ligne":
        if len(G["lignes"]) == 1:
            return {"type": "LineString", "coordinates": [[r3(x), r3(y)] for x, y in G["lignes"][0]]}
        return {"type": "MultiLineString", "coordinates": [[[r3(x), r3(y)] for x, y in C] for C in G["lignes"]]}
    return {"type": "Polygon", "coordinates": [[[r3(x), r3(y)] for x, y in R] for R in G["polys"][0]]}


def provenance(F, oids):
    out = []
    for o in sorted(set(oids)):
        t = F.index_obs[o]
        out.append({"obs": o, "source": t["source"], "date": t["date"], "statut": t["statut"],
                    "confiance": t["confiance"], "valide_2026": t["valide_2026"]})
    return out


def ecrire_json(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")


def ecrire_sorties(F: Fusion, ix: Index):
    OUT.mkdir(parents=True, exist_ok=True)
    O = ix.O
    # ---- attributs.geojson ----
    att = fc_entete("attributs", "mises à jour d'attributs, d'existence et de type des entités existantes, avec provenance", ix)
    for eid in sorted(F.res_entites):
        r = F.res_entites[eid]
        ex = r["existence"]["verdict"]
        bord = r.get("bordure") or {}
        if not r["maj"] and ex not in VERDICTS_RETRAIT + ("absent_2026_a_verifier",) and not bord.get("intervalles") and not (
                r.get("notes") and any(F.index_obs[n["obs"]]["statut"] in ("attribut_corrige",) for n in r["notes"])):
            continue
        ent = ix.E[eid]
        pt = ent["G"]["pt"] if ent.get("G") else None
        props = {"id": eid, "famille": r["famille"], "type": r["type"], "classe_fusion": r["classe"],
                 "statut_verification": r["statut_verification"],
                 "maj": r["maj"], "existence": r["existence"],
                 "instancier": False if ex in VERDICTS_RETRAIT else None,
                 "a_verifier_terrain": ex == "absent_2026_a_verifier" or bool(bord.get("contradictions_a_verifier"))
                 or any(m.get("decision") == "revue_requise" for m in r["maj"].values()),
                 "doublon_de": r.get("doublon_de"), "textes_lus": r.get("textes_lus"),
                 "bordure": ({"intervalles": bord.get("intervalles"), "contradictions": bord.get("contradictions"),
                              "contradictions_a_verifier": bord.get("contradictions_a_verifier"),
                              "desaccords": bord.get("desaccords"), "lectures": bord.get("lectures")} if bord else None),
                 "notes": r.get("notes"), "revue_texte": bool(r.get("notes")) and not r["maj"],
                 "conflits": r["conflits_ids"], "regles": r["regles"], "categorie_preuve": r["categorie_preuve"],
                 "tranche_preuve": r["tranche_preuve"], "tranche_stricte": r["tranche_stricte"],
                 "preuve_stricte": r["preuve_stricte"], "date_max_valide": r["date_max_valide"],
                 "provenance": provenance(F, r["obs"])}
        att["features"].append({"type": "Feature", "properties": props,
                                "geometry": None if pt is None else {"type": "Point", "coordinates": [r3(pt[0]), r3(pt[1])]}})
    ecrire_json(OUT / "attributs.geojson", att)
    # ---- ajouts.geojson ----
    adj = fc_entete("ajouts", "objets absents de la description, observés sur image ou document, avec provenance", ix)
    for a in F.ajouts:
        g = a["membres"]
        props = {"id": a["id"], "classe": a["classe"], "groupe": a["groupe"], "famille_cible": a["fam_cible"],
                 "sous_types": sorted({n["sous_type"] for n in g}), "attributs": a["attrs"],
                 "descriptions": a["desc"], "geometrie_source": a["geo_src"], "sigma_m": r3(a["sigma"]),
                 "local": [r3(a["pt"][0] - O[0]), r3(a["pt"][1] - O[1])],
                 "valide_2026": a["valide"], "confiance": a["conf"], "instancier": a["instancier"],
                 "raisons_non_instanciation": a["raisons"], "hotes": a["hotes"], "liens_associes": a["liens_associes"],
                 "entite_existante_proche": a["proche"], "ancrage": a["ancrage"], "arbitrages": a["arbitrages"],
                 "categorie_preuve": a["categorie_preuve"], "tranche_preuve": TRANCHE.get(a["categorie_preuve"]),
                 "tranche_stricte": a["tranche_stricte"], "d_zone_travaux_m": a["d_zone_travaux_m"],
                 "references_croisees": a["xref"], "conflits": a["conflits_ids"],
                 "regles": ["FUS-ADD-01", "FUS-ADD-02", "FUS-ADD-03", "FUS-ADD-04", "FUS-DATE-02"] + (["FUS-ARB-01"] if a["arbitrages"] else []),
                 "provenance": provenance(F, [n["id"] for n in g])}
        adj["features"].append({"type": "Feature", "properties": props, "geometry": geojson_geom(a["G"])})
    ecrire_json(OUT / "ajouts.geojson", adj)
    # ---- corrections_position.geojson ----
    cp = fc_entete("corrections_position", "déplacements prouvés par image (et maintiens contre la cohérence), avec preuves", ix)
    for eid in sorted(F.res_entites):
        r = F.res_entites[eid]
        pos = r.get("position") or {}
        coh = [c for c in (r.get("coherence") or []) if "verdict" in c]
        ent = ix.E[eid]
        if pos.get("verdict") in ("affinage", "deplacement"):
            a, b = pos["description_l93"], pos["fusion_l93"]
            props = {"id": eid, "famille": r["famille"], "type": r["type"], "nature": pos["verdict"],
                     "d_m": pos["d_m"], "sigma_m": pos["sigma_m"], "decision": pos["decision"], "raisons": pos["raisons"],
                     "methodes": pos["methodes"], "n_mesures": pos["n_mesures"], "obs": pos["obs"], "rejets": pos["rejets"],
                     "preuve_description": pos["preuve_description"], "sigma_description_m": pos["sigma_description_m"],
                     "p_description_local": [r3(a[0] - O[0]), r3(a[1] - O[1])], "p_fusion_local": [r3(b[0] - O[0]), r3(b[1] - O[1])],
                     "coherence": coh[0] if coh else {"verdict": "sans_correction_coherence"},
                     "mesures_anterieures": r.get("mesures_anterieures"),
                     "conflits": r["conflits_ids"], "regles": ["FUS-POS-01", "FUS-POS-03", "FUS-POS-04", "FUS-POS-05"]
                     + (["FUS-DATE-01"] if r.get("mesures_anterieures") else []),
                     "provenance": provenance(F, pos["obs"])}
            cp["features"].append({"type": "Feature", "properties": props,
                                   "geometry": {"type": "LineString", "coordinates": [a, b]}})
        elif pos.get("verdict") == "translation":
            a, b = pos["point_reference_l93"], pos["point_mesure_l93"]
            props = {"id": eid, "famille": r["famille"], "type": r["type"], "nature": "translation_geometrie",
                     "d_m": pos["d_m"], "vecteur_m": pos["vecteur_m"], "sigma_m": pos["sigma_m"], "decision": pos["decision"],
                     "raisons": pos["raisons"], "obs": pos["obs"], "mesures": pos["mesures"],
                     "coherence": coh[0] if coh else {"verdict": "sans_correction_coherence"},
                     "conflits": r["conflits_ids"], "regles": ["FUS-POS-07"], "provenance": provenance(F, pos["obs"])}
            cp["features"].append({"type": "Feature", "properties": props,
                                   "geometry": {"type": "LineString", "coordinates": [a, b]}})
        elif coh and any(c.get("verdict") == "desaccord" and "fusion_l93" in c for c in coh):
            c = next(c for c in coh if c.get("verdict") == "desaccord" and "fusion_l93" in c)
            props = {"id": eid, "famille": r["famille"], "type": r["type"], "nature": "maintien_contre_coherence",
                     "d_m": c["d_image_corrige_m"], "decision": "garder_origine" if pos.get("verdict") == "confirme" else "revue_requise",
                     "obs": c["obs"], "coherence": c, "conflits": r["conflits_ids"], "regles": ["FUS-COH-01"],
                     "provenance": provenance(F, c["obs"])}
            cp["features"].append({"type": "Feature", "properties": props,
                                   "geometry": {"type": "LineString", "coordinates": [c["coherence_resolu_l93"], c["fusion_l93"]]}})
    ecrire_json(OUT / "corrections_position.geojson", cp)
    # ---- conflits.json ----
    ecrire_json(OUT / "conflits.json", {
        "schema": "pj_enrichi_conflits/0.1", "generateur": VERSION,
        "comptes": dict(sorted(Counter(c["type"] for c in F.conflits).items())),
        "comptes_gravite": dict(sorted(Counter(c["gravite"] for c in F.conflits).items())),
        "conflits": F.conflits,
        "controle_coherence": sorted(F.controle_coh, key=lambda c: c["entite"]),
    })
    # ---- entites_verifiees.json ----
    ev = {}
    for eid in sorted(F.res_entites):
        r = F.res_entites[eid]
        pos = r.get("position") or {}
        bord = r.get("bordure") or {}
        ev[eid] = {"famille": r["famille"], "type": r["type"], "classe_fusion": r["classe"], "obs": r["obs"],
                   "sources": r["sources"], "statut_verification": r["statut_verification"],
                   "tranche_stricte": r["tranche_stricte"], "preuve_stricte": r["preuve_stricte"],
                   "dans_emprise_travaux": r["dans_emprise_travaux"], "d_zone_travaux_m": r["d_zone_travaux_m"],
                   "appui_conservation": r["appui_conservation"], "obs_non_probantes": r["obs_non_probantes"],
                   "categorie_preuve": r["categorie_preuve"], "tranche_preuve": r["tranche_preuve"],
                   "obs_preuve": r["obs_preuve"], "preuve_automatique_seule": r["preuve_automatique_seule"],
                   "obs_requalifiees": r["requalifiees"], "date_max": r["date_max"],
                   "date_max_valide": r["date_max_valide"], "existence": r["existence"]["verdict"],
                   "existence_obs_anterieures_ecartees": r["existence"].get("obs_anterieures_ecartees"),
                   "position": {k: pos.get(k) for k in ("verdict", "d_m", "sigma_m", "decision", "n_mesures_reelles") if k in pos},
                   "mesures_anterieures": r.get("mesures_anterieures"),
                   "attributs_confirmes": r["attributs_confirmes"],
                   "attributs_maj": sorted(r["maj"]),
                   "attributs_maj_decisions": {k: v.get("decision") for k, v in sorted(r["maj"].items())},
                   "bordure_contradictions": {c["intervalle"]: c["gravite"] for c in bord.get("contradictions", [])} or None,
                   "conflits": r["conflits_ids"], "regles": r["regles"]}
    ecrire_json(OUT / "entites_verifiees.json", {"schema": "pj_enrichi_entites/0.2", "generateur": VERSION,
                                                  "n": len(ev), "comptes_statut": dict(sorted(Counter(
                                                      v["statut_verification"] for v in ev.values()).items())),
                                                  "entites": ev})
    # ---- observations_index.json ----
    ecrire_json(OUT / "observations_index.json", {"schema": "pj_enrichi_index_obs/0.1", "generateur": VERSION,
                                                   "n": len(F.index_obs),
                                                   "observations": [F.index_obs[k] for k in sorted(F.index_obs)]})


# --------------------------------------------------------------------------------------------
# Carte de couverture (Pillow)
# --------------------------------------------------------------------------------------------

PAL = {"fond": (252, 252, 251), "encre": (11, 11, 11), "encre2": (82, 81, 78), "muet": (150, 149, 144),
       "seq_2022": (0x9d, 0xc3, 0xf0), "seq_2024": (0x4f, 0x8f, 0xdc), "seq_2025": (0x1f, 0x5c, 0xb0), "seq_2026": (0x0a, 0x24, 0x52),
       "orange": (0xeb, 0x68, 0x34), "aqua": (0x1b, 0xaf, 0x7a), "critique": (0xd0, 0x3b, 0x3b), "blanc": (255, 255, 255)}
# rampe ordinale par tranche de date de la preuve (FUS-COUV-01) : clair = ancien, foncé = récent
TRANCHE_COUL = {"ortho_2022": PAL["seq_2022"], "2020_2024": PAL["seq_2024"], "2025": PAL["seq_2025"], "2026": PAL["seq_2026"]}
# rampe ordinale de la preuve stricte (FUS-COUV-02) par classe de date relative aux travaux (FUS-DATE-02)
STRICTE_COUL = {"apres_travaux": PAL["seq_2026"], "avant_travaux_hors_emprise": PAL["seq_2024"],
                "avant_travaux_dans_emprise": PAL["seq_2022"]}


def positions_photos(F: Fusion):
    """Positions L93 des photos citées : Panoramax (pose calée 2026 si acceptée, sinon GNSS) et Mapillary (SfM)."""
    out = {"pnx": {}, "mly": {}, "p2026": {}}
    try:
        from pyproj import Transformer
    except ImportError:  # pyproj absent : pas de positions de photos
        return out
    tr = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    cites = {t["source"][4:] for t in F.index_obs.values() if t["source"].startswith("pnx:")}
    cales = {}
    if POSES_2026.exists():
        for ph in charger_json(POSES_2026).get("photos", []):
            if ph.get("accepte") and ph.get("pose"):
                cales[ph["id8"]] = (ph["pose"]["x"] + F.ix.O[0], ph["pose"]["y"] + F.ix.O[1])
    for f in charger_json(SITE / "panoramax_pictures.geojson").get("features", []):
        pid = f["properties"]["id"][:8]
        if pid not in cites:
            continue
        dt = (f["properties"].get("datetime") or "")[:10]
        x, y = cales.get(pid) or tr.transform(*f["geometry"]["coordinates"][:2])
        out["p2026" if dt >= FIN_TRAVAUX else "pnx"][pid] = (x, y)
    cites_m = {t["source"][4:] for t in F.index_obs.values() if t["source"].startswith("mly:")}
    if cites_m and MLY_IMAGES.exists():
        for im in charger_json(MLY_IMAGES).get("images", []):
            if str(im.get("id")) in cites_m:
                g = im.get("computed_geometry") or im.get("geometry")
                if g:
                    out["mly"][str(im["id"])] = tr.transform(*g["coordinates"][:2])
    return out


def carte(F: Fusion, ix: Index, chemin: Path):
    from PIL import Image, ImageDraw, ImageFont

    def police(t, gras=False):
        for nom in (("arialbd.ttf" if gras else "arial.ttf"), "DejaVuSans.ttf"):
            for d in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
                if (d / nom).exists():
                    return ImageFont.truetype(str(d / nom), t)
        return ImageFont.load_default()

    f_titre, f_txt, f_pt = police(26, True), police(17), police(14)
    O = ix.O

    def fond_ortho(x0, y0, x1, y1, ppm):
        W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
        im = Image.new("RGB", (W, H), PAL["fond"])
        d = SITE / "ortho5cm_2022"
        for tx in range(int(x0 // 50 * 50), int(x1) + 1, 50):
            for ty in range(int(y0 // 50 * 50), int(y1) + 1, 50):
                fp = d / f"pcrs5cm_{tx}_{ty}.jpg"
                if not fp.exists():
                    continue
                t = Image.open(fp).convert("RGB")
                s = max(1, int(round(50 * ppm)))
                t = t.resize((s, s), Image.BILINEAR)
                im.paste(t, (int(round((tx - x0) * ppm)), int(round((y1 - (ty + 50)) * ppm))))
        g = im.convert("L").convert("RGB")
        return Image.blend(g, Image.new("RGB", (W, H), PAL["fond"]), 0.62)

    zones = [f for f in charger_json(PKG / "relief/relief_zones_2026.geojson").get("features", [])
             if (f["properties"].get("zone") or "") not in ("chaussee_2026",)]
    bords = [(e, ix.E[e]["G"]) for e in sorted(ix.par_famille.get("bordures", []))]
    photos = positions_photos(F)

    def etoile(d, X, Y, r, fill):
        pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((X + rr * math.cos(a), Y - rr * math.sin(a)))
        d.polygon(pts, fill=fill, outline=PAL["blanc"])

    def panneau(x0, y0, x1, y1, ppm, mode):
        im = fond_ortho(x0, y0, x1, y1, ppm)
        W, H = im.size

        def px(p):
            return ((p[0] - x0) * ppm, (y1 - p[1]) * ppm)

        # zones modifiées 2025 : hachures
        mask = Image.new("L", (W, H), 0)
        dm = ImageDraw.Draw(mask)
        for g in [geom_norm(f["geometry"]) for f in zones] + [ix.E[e]["G"] for e in sorted(F.zone_extension)]:
            if g is None:
                continue
            for pg in g["polys"]:
                dm.polygon([px(p) for p in pg[0]], fill=255)
                for h in pg[1:]:
                    dm.polygon([px(p) for p in h], fill=0)
        hach = Image.new("RGB", (W, H), PAL["fond"])
        dh = ImageDraw.Draw(hach)
        for k in range(-H, W, 9):
            dh.line([(k, H), (k + H, 0)], fill=(205, 170, 130), width=2)
        im.paste(hach, (0, 0), mask.point(lambda v: 110 if v else 0))
        d = ImageDraw.Draw(im)
        centre, demi = ((x0 + x1) / 2, (y0 + y1) / 2), max(x1 - x0, y1 - y0)
        # bordures : grises sans preuve ; en mode preuves, colorées par la classe de leur preuve stricte
        larg = 2 if ppm < 3 else 3
        for eid, g in bords:
            if not bbox_proche(g["bbox"], centre, demi):
                continue
            t = (F.res_entites.get(eid) or {}).get("tranche_stricte") if mode == "preuves" else None
            for C in g["lignes"]:
                if t in STRICTE_COUL:
                    d.line([px(p) for p in C], fill=STRICTE_COUL[t], width=larg)
                else:
                    d.line([px(p) for p in C], fill=(120, 119, 115), width=1)
        r0 = 2 if ppm < 3 else 3

        def rond(p, r, fill=None, out=None, w=1):
            x, y = px(p)
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=out, width=w)

        # entités décrites
        dessinables = [e for e in ix.E.values() if e.get("G") is not None and e["famille"] in
                       ("mobilier", "arbres", "ponctuels_sol", "marquages") and e["G"]["type"] in ("point", "poly", "ligne")
                       and not (e["famille"] == "mobilier" and e["type"] == "cloture")]
        if mode == "preuves":
            for x, y in sorted(photos["mly"].values()):
                if x0 <= x <= x1 and y0 <= y <= y1:
                    X, Y = px((x, y))
                    d.ellipse([X - 1.5, Y - 1.5, X + 1.5, Y + 1.5], fill=PAL["encre"])
            for x, y in sorted(photos["pnx"].values()):
                if x0 <= x <= x1 and y0 <= y <= y1:
                    X, Y = px((x, y))
                    d.line([(X - 4, Y), (X + 4, Y)], fill=PAL["encre"], width=1)
                    d.line([(X, Y - 4), (X, Y + 4)], fill=PAL["encre"], width=1)
            for e in sorted(dessinables, key=lambda e: e["id"]):
                p = e["G"]["pt"]
                if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                    continue
                r = F.res_entites.get(e["id"])
                if r is None:
                    rond(p, 1.5, fill=(175, 174, 170))
                    continue
                t = r["tranche_stricte"]
                if t in STRICTE_COUL:
                    rond(p, r0 + 2, fill=STRICTE_COUL[t], out=PAL["blanc"], w=1)
                elif t == "indice_seulement":
                    rond(p, r0 + 2, out=PAL["encre2"], w=2)
                else:
                    rond(p, r0 + 2, out=PAL["muet"], w=1)
            for a in F.ajouts:
                p = a["pt"]
                if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                    continue
                t = a.get("tranche_stricte")
                if t in STRICTE_COUL:
                    rond(p, r0 + 2, fill=STRICTE_COUL[t], out=PAL["blanc"], w=1)
                else:
                    rond(p, r0 + 2, out=PAL["encre2"], w=2)
            for x, y in sorted(photos["p2026"].values()):
                if x0 <= x <= x1 and y0 <= y <= y1:
                    X, Y = px((x, y))
                    etoile(d, X, Y, 9 if ppm >= 3 else 7, PAL["critique"])
        else:
            for e in sorted(dessinables, key=lambda e: e["id"]):
                p = e["G"]["pt"]
                if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                    continue
                r = F.res_entites.get(e["id"])
                if r is None:
                    continue
                pos = r.get("position") or {}
                ex = r["existence"]["verdict"]
                X, Y = px(p)
                sv = r["statut_verification"]
                if ex in VERDICTS_RETRAIT:
                    s = r0 + 3
                    d.line([(X - s, Y - s), (X + s, Y + s)], fill=PAL["encre"], width=3)
                    d.line([(X - s, Y + s), (X + s, Y - s)], fill=PAL["encre"], width=3)
                elif ex == "absent_2026_a_verifier":
                    s = r0 + 3
                    d.line([(X - s, Y - s), (X + s, Y + s)], fill=PAL["encre2"], width=1)
                    d.line([(X - s, Y + s), (X + s, Y - s)], fill=PAL["encre2"], width=1)
                elif pos.get("verdict") in ("affinage", "deplacement", "translation"):
                    pass
                elif r["maj"]:
                    s = r0 + 2
                    plein = any(m.get("decision") == "appliquer" for m in r["maj"].values())
                    d.rectangle([X - s, Y - s, X + s, Y + s], fill=PAL["orange"] if plein else None,
                                outline=PAL["blanc"] if plein else PAL["orange"], width=1 if plein else 2)
                elif sv == "confirme":
                    rond(p, r0, fill=(130, 129, 125))
            # flèches de déplacement (exagérées x5)
            for eid, r in sorted(F.res_entites.items()):
                pos = r.get("position") or {}
                if pos.get("verdict") in ("affinage", "deplacement"):
                    a, b = np.array(pos["description_l93"]), np.array(pos["fusion_l93"])
                elif pos.get("verdict") == "translation":
                    a, b = np.array(pos["point_reference_l93"]), np.array(pos["point_mesure_l93"])
                else:
                    continue
                if not (x0 <= a[0] <= x1 and y0 <= a[1] <= y1):
                    continue
                k_ = 5.0 if float(np.hypot(*(b - a))) < 1.0 else 1.0   # x5 seulement sous 1 m
                b5 = a + k_ * (b - a)
                A, B = px(a), px(b5)
                col = PAL["encre"] if pos.get("decision") == "appliquer" else PAL["encre2"]
                d.line([A, B], fill=PAL["blanc"], width=5)
                d.line([A, B], fill=col, width=3 if pos.get("decision") == "appliquer" else 2)
                ang = math.atan2(B[1] - A[1], B[0] - A[0])
                for s_ in (2.6, -2.6):
                    d.line([B, (B[0] - 9 * math.cos(ang + s_ / 6), B[1] - 9 * math.sin(ang + s_ / 6))], fill=col, width=3)
                d.ellipse([A[0] - 3, A[1] - 3, A[0] + 3, A[1] + 3], outline=col, width=2)
            for a in F.ajouts:
                p = a["pt"]
                if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                    continue
                X, Y = px(p)
                s = r0 + 3
                if a["instancier"]:
                    d.polygon([(X, Y - s), (X + s, Y), (X, Y + s), (X - s, Y)], fill=PAL["aqua"], outline=PAL["blanc"])
                else:
                    d.polygon([(X, Y - s), (X + s, Y), (X, Y + s), (X - s, Y)], outline=PAL["aqua"], width=2)
            # conflits
            cibles = defaultdict(int)
            for c in F.conflits:
                if c["gravite"] != "info":
                    cibles[c["cible"]] += 1
            for cib in sorted(cibles):
                if cib in ix.E and ix.E[cib].get("G") is not None:
                    p = ix.E[cib]["G"]["pt"]
                else:
                    a = next((a for a in F.ajouts if a["id"] == cib), None)
                    if a is None:
                        continue
                    p = a["pt"]
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                    rond(p, r0 + 7, out=PAL["critique"], w=2)
        # échelle
        L = 20 if (x1 - x0) < 250 else 50
        d.rectangle([12, H - 34, 12 + L * ppm, H - 28], fill=PAL["encre"])
        d.text((12, H - 26), f"{L} m", fill=PAL["encre"], font=f_pt)
        d.rectangle([0, 0, W - 1, H - 1], outline=(200, 199, 195))
        return im

    # emprises : site (dalles ortho) et cœur (± 80 m)
    site = (917100.0, 6460100.0, 917450.0, 6460450.0, 2.4)
    coeur = (O[0] - 80, O[1] - 80, O[0] + 80, O[1] + 80, 5.25)
    pA = panneau(*site, "preuves")
    pB = panneau(*site, "decisions")
    pC = panneau(*coeur, "preuves")
    pD = panneau(*coeur, "decisions")
    marge, ent_h, leg_h = 24, 70, 190
    W = marge * 3 + pA.size[0] + pB.size[0]
    H = ent_h + 40 + pA.size[1] + 40 + pC.size[1] + leg_h + marge
    im = Image.new("RGB", (W, H), PAL["fond"])
    d = ImageDraw.Draw(im)
    d.text((marge, 18), "Paquet Jardin : preuves strictes par entité et décisions de la fusion du recensement (0.3)", fill=PAL["encre"], font=f_titre)
    y = ent_h
    d.text((marge, y), "A. Site : preuve stricte, classe de date relative aux travaux (entités, bordures)", fill=PAL["encre"], font=f_txt)
    d.text((marge * 2 + pA.size[0], y), "B. Site : décisions de la fusion", fill=PAL["encre"], font=f_txt)
    y += 28
    im.paste(pA, (marge, y))
    im.paste(pB, (marge * 2 + pA.size[0], y))
    y += pA.size[1] + 12
    d.text((marge, y), "C. Cœur du carrefour (± 80 m) : preuves strictes", fill=PAL["encre"], font=f_txt)
    d.text((marge * 2 + pA.size[0], y), "D. Cœur du carrefour : décisions (flèches < 1 m x5)", fill=PAL["encre"], font=f_txt)
    y += 28
    im.paste(pC, (marge, y))
    im.paste(pD, (marge * 2 + pA.size[0], y))
    y += pC.size[1] + 16

    # légende (texte en encre, marques colorées à côté)
    def item(x, yy, dessin, lib):
        dessin(x + 9, yy + 10)
        d.text((x + 26, yy + 1), lib, fill=PAL["encre"], font=f_pt)

    def r_(c, out=None, w=1, r=6):
        return lambda X, Y: d.ellipse([X - r, Y - r, X + r, Y + r], fill=c, outline=out, width=w)

    col1 = [(r_(PAL["seq_2026"], PAL["blanc"]), "preuve stricte après travaux (photo du 28/07/2026)"),
            (r_(PAL["seq_2024"], PAL["blanc"]), "preuve stricte avant travaux, hors emprise"),
            (r_(PAL["seq_2022"], PAL["blanc"]), "avant travaux, dans l'emprise, conservation appuyée"),
            (lambda X, Y: d.line([(X - 9, Y), (X + 9, Y)], fill=PAL["seq_2024"], width=3), "bordure : couleur de sa preuve stricte (gris : aucune)"),
            (r_(None, PAL["encre2"], 2), "indice seulement (faible, incertain, automatique, groupé)"),
            (r_(None, PAL["muet"], 1), "vue non concluante ou non valable 2026")]
    col2 = [
            (r_((175, 174, 170), None, 1, 2), "entité décrite sans observation"),
            (lambda X, Y: (d.line([(X - 5, Y), (X + 5, Y)], fill=PAL["encre"]), d.line([(X, Y - 5), (X, Y + 5)], fill=PAL["encre"])),
             "photo Panoramax citée (2020-2025)"),
            (lambda X, Y: d.ellipse([X - 2, Y - 2, X + 2, Y + 2], fill=PAL["encre"]), "photo Mapillary citée"),
            (lambda X, Y: etoile(d, X, Y, 8, PAL["critique"]), "photo du 28/07/2026"),
            (lambda X, Y: d.rectangle([X - 8, Y - 6, X + 8, Y + 6], fill=(230, 205, 180)), "zone refaite 2025 (hachures)")]
    col3 = [(lambda X, Y: d.rectangle([X - 5, Y - 5, X + 5, Y + 5], fill=PAL["orange"]), "attribut corrigé (creux : en revue)"),
            (lambda X, Y: d.line([(X - 8, Y), (X + 8, Y)], fill=PAL["encre"], width=3), "déplacement (< 1 m : x5) : appliquer (épais) / revue (fin)"),
            (lambda X, Y: d.polygon([(X, Y - 7), (X + 7, Y), (X, Y + 7), (X - 7, Y)], fill=PAL["aqua"]), "ajout instancié (creux : candidat)"),
            (lambda X, Y: (d.line([(X - 6, Y - 6), (X + 6, Y + 6)], fill=PAL["encre"], width=3),
                           d.line([(X - 6, Y + 6), (X + 6, Y - 6)], fill=PAL["encre"], width=3)), "absent 2026 / à retirer (fin : à vérifier)")]
    col4 = [(r_((130, 129, 125), None, 1, 3), "entité confirmée (preuve stricte)"),
            (r_(None, PAL["critique"], 2, 8), "conflit à vérifier (voir conflits.json)")]
    xs = [marge, marge + 420, marge * 2 + pA.size[0], marge * 2 + pA.size[0] + 420]
    d.text((xs[0], y), "Preuves (A, C)", fill=PAL["encre2"], font=f_txt)
    d.text((xs[2], y), "Décisions (B, D)", fill=PAL["encre2"], font=f_txt)
    for colonne, x in zip((col1, col2, col3, col4), xs):
        yy = y + 26
        for dessin, lib in colonne:
            item(x, yy, dessin, lib)
            yy += 24
    chemin.parent.mkdir(parents=True, exist_ok=True)
    im.save(chemin, optimize=True)


# --------------------------------------------------------------------------------------------
# Résumé
# --------------------------------------------------------------------------------------------

def zones_travaux_2025():
    """Anneaux L93 des zones refaites en 2025 (surfaces « modifie_2025 » et zones de relief reprises), comme gcp.py."""
    anneaux = []
    for f in charger_json(PKG / "surfaces/surfaces_2026.geojson").get("features", []):
        if f["properties"].get("etat") == "modifie_2025":
            g = geom_norm(f.get("geometry"))
            anneaux += [pg[0] for pg in (g or {}).get("polys", [])]
    for f in charger_json(PKG / "relief/relief_zones_2026.geojson").get("features", []):
        if f["properties"].get("zone") in ("ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee",
                                           "ancienne_chaussee_trottoir_par_defaut"):
            g = geom_norm(f.get("geometry"))
            anneaux += [pg[0] for pg in (g or {}).get("polys", [])]
    return anneaux


FAM_COUVERTURE = ("mobilier", "arbres", "marquages", "bordures", "surfaces", "ilots", "ponctuels_sol")
TRANCHES_IMAGE = ("2026", "2025", "2020_2024", "ortho_2022")


# couverture publiée par la fusion 0.2 et recomptée en strict par la critique de couverture (10/10/2026), pour comparaison
REFERENCE_0_2 = {"site": {"large_pct": 23.1, "stricte_critique_pct": 13.2},
                 "coeur": {"large_pct": 19.8, "stricte_critique_pct": 11.5},
                 "zone_travaux_2025": {"large_pct": 7.6, "stricte_critique_pct": 3.3}}


def couverture(F: Fusion, ix: Index):
    """Couverture des entités décrites : large (FUS-COUV-01, définition 0.2) et stricte (FUS-COUV-02, décisions) ;
    site, cœur, zone des travaux 2025 (FUS-ZONE-01, extension comprise)."""
    O = np.array(ix.O)
    tab = {z: defaultdict(Counter) for z in ("site", "coeur", "zone_travaux_2025")}
    for e in sorted(ix.E.values(), key=lambda e: e["id"]):
        if e["famille"] not in FAM_COUVERTURE or e.get("G") is None:
            continue
        r = F.res_entites.get(e["id"])
        t = (r or {}).get("tranche_preuve") or "aucune"
        ts = (r or {}).get("tranche_stricte") or "aucune"
        p = e["G"]["pt"]
        zones = ["site"]
        if float(np.max(np.abs(p - O))) <= COEUR_DEMI_M:
            zones.append("coeur")
        if any(bbox_proche(rb, p, 0.0) and dans_anneau(p, R) for _, R, rb in F.zone_anneaux):
            zones.append("zone_travaux_2025")
        for z in zones:
            c = tab[z][e["classe"]]
            c["n"] += 1
            c["L:" + t] += 1
            c["S:" + ts] += 1
            if r and r.get("preuve_automatique_seule"):
                c["automatique_seule"] += 1
            if r and r.get("statut_verification") == "confirme":
                c["confirmees"] += 1
    out = {}
    for z, T in tab.items():
        out[z] = {}
        tot = Counter()
        for cls in ORDRE_CLASSES + sorted(set(T) - set(ORDRE_CLASSES)):
            if cls not in T:
                continue
            c = T[cls]
            tot.update(c)
            out[z][cls] = couv_ligne(c)
        out[z]["total"] = couv_ligne(tot)
    return out


def couv_ligne(c):
    n = c["n"]

    def pct(k):
        return round(100.0 * k / n, 1) if n else 0.0

    img = sum(c["L:" + t] for t in TRANCHES_IMAGE)
    stricte = sum(c["S:" + t] for t in CLASSES_DATE)
    return {"n": n,
            "large": {"n": img, "pct": pct(img), **{t: c["L:" + t] for t in TRANCHES_IMAGE}, "web_seul": c["L:web"],
                      "non_concluant": c["L:non_concluant"], "non_valable_2026": c["L:non_valable_2026"],
                      "aucune": c["L:aucune"], "pct_2024_et_plus": pct(c["L:2026"] + c["L:2025"] + c["L:2020_2024"])},
            "stricte": {"n": stricte, "pct": pct(stricte), **{t: c["S:" + t] for t in CLASSES_DATE},
                        "pct_apres_travaux": pct(c["S:apres_travaux"]),
                        **{t: c["S:" + t] for t in TRANCHES_STRICTES if t not in CLASSES_DATE}},
            "automatique_seule": c["automatique_seule"], "confirmees": c["confirmees"]}


def stats_bordures(F: Fusion):
    """Lecture des profils de bordure (FUS-BOR-01) : textes lus, lectures, votes, accords, contradictions."""
    textes, lectures = 0, Counter()
    for n in F.obs:
        if n["classe"] != "bordure":
            continue
        for champ in CHAMPS_PROFIL:
            v = n["attrs"].get(champ)
            if isinstance(v, str) and v.strip():
                textes += 1
        lec = lire_profil_bordure(n["attrs"])
        for lu in lec:
            lectures[(lu["attribut"], lu["lecture"])] += 1
        if not lec:
            lectures[("sans_lecture", "-")] += 1
    iv = Counter()
    contra = []
    for eid in sorted(F.res_entites):
        b = F.res_entites[eid].get("bordure")
        if not b:
            continue
        for it in b["intervalles"]:
            iv[it.get("verdict") or "abaisse_seul"] += 1
        for c in b["contradictions"]:
            contra.append((eid, c))
    return textes, lectures, iv, contra


def resume(F: Fusion, ix: Index, obs_par_fichier, avec_carte, couv):
    L = []
    w = L.append
    res = list(F.res_entites.values())
    tot = {z: couv[z]["total"] for z in ("site", "coeur", "zone_travaux_2025")}
    noms = {"site": "Site entier", "coeur": "Cœur du carrefour (± 80 m)", "zone_travaux_2025": "Zone des travaux 2025"}
    sv = Counter(r["statut_verification"] for r in res)
    liens = [l for t in F.index_obs.values() for l in t["liens"] if "classe_date" in l]
    w("# Fusion du recensement : couche `description/enrichi/`")
    w("")
    w(f"Générateur : `python recon/pcg/enrichir/fusion_recensement.py` ({VERSION}), déterministe : deux exécutions "
      "successives donnent des sorties identiques octet pour octet. Couche séparée : ni la description de base, ni la "
      "cohérence, ni les observations ne sont modifiées. Le composeur la fusionnera (priorité arbitré > enrichi vérifié > base).")
    w("")
    # ---- ce qui change en 0.3 ----
    w("## Ce qui change en 0.3 (critique de couverture du 10/10/2026)")
    w("")
    w("La couverture publiée en 0.2 était surestimée. La fusion garde désormais deux mesures : la couverture **large** "
      "(FUS-COUV-01, définition 0.2, pour comparaison) et la couverture **stricte** (FUS-COUV-02). Toutes les décisions "
      "utilisent la stricte : statut « confirmé », application d'un déplacement, d'un attribut ou d'un retrait, carte.")
    w("")
    w("| zone | entités | large 0.2 (publiée) | stricte 0.2 (recomptée par la critique) | large 0.3 | **stricte 0.3** | "
      "dont après travaux |")
    w("|---|---|---|---|---|---|---|")
    for z in ("site", "coeur", "zone_travaux_2025"):
        t = tot[z]
        ref = REFERENCE_0_2[z]
        w(f"| {noms[z]} | {t['n']} | {ref['large_pct']} % | {ref['stricte_critique_pct']} % | {t['large']['pct']} % | "
          f"**{t['stricte']['pct']} %** ({t['stricte']['n']}) | {t['stricte']['apres_travaux']} |")
    w("")
    w("La large 0.3 applique la définition 0.2 aux liens corrigés (contrôles automatiques des bordures requalifiés, liens "
      "groupés sans preuve propre, liens invalidés par une revue). La stricte 0.3 est plus basse que le recomptage de la "
      "critique parce qu'elle applique aussi les classes de date relatives aux travaux (cause 3), le plafond de confiance des "
      "projections lointaines (FUS-CONF-02) et les liens groupés (FUS-LIEN-09) ; la zone des travaux compte aussi plus "
      "d'entités (cause 5).")
    w("")
    # cause 1
    n_faible = sum(1 for r in res if r["tranche_preuve"] in TRANCHES_IMAGE and r["tranche_stricte"] == "indice_seulement")
    w(f"1. **Preuve stricte (FUS-COUV-02).** Une entité n'est couverte, et « confirmée », que si au moins une observation "
      f"image manuelle, de confiance moyenne ou haute, valide 2026 et probante la porte. {n_faible} entités qui avaient une "
      f"preuve au sens large n'ont qu'un indice (confiance faible, validité incertaine, contrôle automatique, lien groupé "
      f"ou image antérieure aux travaux dans leur emprise). Statuts : "
      + ", ".join(f"{k} {v}" for k, v in sorted(sv.items())) + " (FUS-STAT-01).")
    # cause 2
    n_inc = sum(1 for l in liens if "FUS-VAL-04" in (l.get("non_probant") or []))
    n_inc_seul = 0
    for r in res:
        if r["tranche_stricte"] != "indice_seulement":
            continue
        ob = [F.index_obs[o] for o in r["obs_preuve"]]
        if ob and all(o["valide_2026"] == "incertain" for o in ob):
            n_inc_seul += 1
    w(f"2. **Validité « incertaine » (FUS-VAL-04).** Elle ne prouve plus ni la présence ni l'absence : {n_inc} liens "
      f"observation-entité concernés ; {n_inc_seul} entités ne reposaient que sur ce type d'observation et passent en "
      "« indice seulement ». Les attributs et les mesures la gardent avec le poids 0,5 (toujours en revue).")
    # cause 3
    cl = Counter(l["classe_date"] for l in liens)
    ap = Counter(bool(l.get("appui_conservation")) for l in liens if l["classe_date"] == "avant_travaux_dans_emprise")
    n_2025 = sum(1 for n in F.obs if n["categorie"] == "photo_2025")
    n_0831 = sum(1 for n in F.obs if (n["date"] or "").startswith("2025-08-31"))
    w(f"3. **Dates relatives aux travaux (FUS-DATE-02).** Les {n_2025} observations sur photos de 2025 (12/01 au 31/08/2025, "
      f"dont {n_0831} du 31/08/2025, en plein chantier) sont toutes antérieures à la fin des travaux. Liens observation-entité : "
      f"après travaux {cl['apres_travaux']}, avant travaux hors emprise {cl['avant_travaux_hors_emprise']}, avant travaux "
      f"dans l'emprise (± {EMPRISE_MARGE_M:.0f} m) {cl['avant_travaux_dans_emprise']}, dont {ap[True]} avec un appui de règle "
      f"(FUS-SRC-001 : marquage conservé, bordure levée GAM hors périmètre refait, surface inchangée, objet attesté après "
      f"les travaux) et {ap[False]} sans appui, devenus non probants.")
    # cause 4
    autos_b = Counter(F.requalifiees.get(n["id"], "non_liee") for n in F.obs
                      if n["auto"] and n["classe"] == "bordure" and n["statut"] == "confirme")
    w(f"4. **Contrôles automatiques des bordures (FUS-AUTO-01/02 étendues).** {sum(autos_b.values())} confirmations "
      f"automatiques de bordures (orthos 2022 et 2024, sans masque véhicules / ombres ni réponse d'arête) : "
      f"{autos_b['incertain']} requalifiées « incertain », {autos_b['corroboree']} corroborées par une observation manuelle. "
      "La bordure K-0236 citée par la critique (fausse confirmation sur deux dates) n'a plus d'observation : l'atelier des "
      "orthos récentes l'a déjà rejetée à l'échantillonnage.")
    # cause 5
    ext = F.zone_extension
    O = np.array(ix.O)
    n_ext = 0
    anneaux_v1 = [(R, rb) for src, R, rb in F.zone_anneaux if src == "v1"]
    anneaux_ext = [(R, rb) for src, R, rb in F.zone_anneaux if src != "v1"]
    for e in ix.E.values():
        if e["famille"] not in FAM_COUVERTURE or e.get("G") is None:
            continue
        p = e["G"]["pt"]
        if any(bbox_proche(rb, p, 0.0) and dans_anneau(p, R) for R, rb in anneaux_ext) \
                and not any(bbox_proche(rb, p, 0.0) and dans_anneau(p, R) for R, rb in anneaux_v1):
            n_ext += 1
    w("5. **Zone des travaux (FUS-ZONE-01).** Elle comprend maintenant les surfaces dont une photo du 28/07/2026 montre un "
      "revêtement neuf : " + ", ".join(
          f"`{k}` ({ix.E[k]['type']}, {float(ix.E[k]['props'].get('aire_m2') or 0):.0f} m², {', '.join(v)})"
          for k, v in ext.items())
      + f". {n_ext} entités décrites y entrent en plus ; l'état de ces surfaces passe à « modifie_2025 » (mise à jour etat_v1).")
    # 3 cas
    E = F.res_entites

    def st(eid):
        r = E.get(eid)
        return f"`{eid}` {r['statut_verification']}" if r else f"`{eid}` sans observation"
    w("6. **Trois cas faux corrigés.** Places ML-5341, ML-5342 et ML-5343 : le lien groupé de PANO2026-014 ne les prouve "
      "plus (FUS-LIEN-09 : seules ML-5339, ML-5340 et ML-5344 sont citées dans sa preuve) et le constat de revue ARB-005 "
      "(photo f8d91bb1 du 28/07/2026 : enrobé et butées, aucune ligne) les met en « absent_2026_a_verifier » : "
      + ", ".join(st(e) for e in ("ML-5341", "ML-5342", "ML-5343"))
      + ". MLY-MAR-017 (« tracé sur la bande plantée », projection à 25,9 m) n'est plus un constat indépendant de la date "
      "(FUS-VAL-02 limité à 15 m) et son lien est invalidé (ARB-004) ; MLY-MAR-016 et MLY-MAR-018, même image à 23,6 et "
      "28,1 m, perdent aussi ce statut. K-0358, masquée par la haie, n'est plus confirmée (ARB-006, et confiance faible) : "
      + st("K-0358") + ".")
    textes, lec, ivs, contra = stats_bordures(F)
    nums = sum(v for (a, l_), v in lec.items() if a == "vue_m" and l_ == "haute")
    expl = sum(v for (a, l_), v in lec.items() if a == "vue_m" and l_ == "moyenne")
    ded = sum(v for (a, l_), v in lec.items() if a == "vue_m" and l_ == "faible")
    abv = sum(v for (a, l_), v in lec.items() if a == "abaisse")
    sans = lec[("sans_lecture", "-")]
    c_av = sorted({eid for eid, c in contra if c["gravite"] == "a_verifier"})
    c_in = sorted({eid for eid, c in contra if c["gravite"] == "info"} - set(c_av))
    w(f"7. **Vote des attributs de bordure (FUS-BOR-01..03).** {textes} textes libres de profil lus sur les observations de "
      f"bordures : vue chiffrée {nums}, qualificatif explicite {expl}, vue déduite {ded}, abaissé {abv} ; "
      f"{sans} observations sans lecture de profil. Intervalles votés : "
      + ", ".join(f"{k} {v}" for k, v in sorted(ivs.items()))
      + f". Contradictions de vue à vérifier : {len(c_av)} bordures ({', '.join(c_av)}) ; pour information : {len(c_in)} "
      f"({', '.join(c_in)}). Détail dans la section Bordures.")
    w("")
    # ---- dates des images ----
    w("## Dates des images et classes relatives aux travaux")
    w("")
    par_cat = defaultdict(list)
    for n in F.obs:
        if n["type_source"] != "web" and n["date"]:
            par_cat[n["categorie"]].append(n["date"])
    w("| catégorie (FUS-SRC-01) | source | dates des observations | observations | classe relative aux travaux |")
    w("|---|---|---|---|---|")
    lib = {"photo_2026": "Panoramax, 7 photos (3 calées) et constats de revue", "photo_2025": "Panoramax et Mapillary",
           "ortho_2025": "Pléiades 2025, 50 cm (non datée)", "photo_2020_2024": "Panoramax et Mapillary",
           "ortho_2024": "IGN BD ORTHO, 20 cm", "ortho_2022": "PCRS 5 cm"}
    for c in CATEGORIES:
        if c in par_cat:
            ds = sorted(par_cat[c])
            per = "2025 (sans date publiée)" if c == "ortho_2025" else (ds[0] if ds[0] == ds[-1] else f"{ds[0]} à {ds[-1]}")
            classe = "après travaux" if c == "photo_2026" else "avant travaux (hors ou dans l'emprise selon l'entité)"
            w(f"| {c} | {lib.get(c, c)} | {per} | {len(ds)} | {classe} |")
    w("")
    w("Travaux du cœur : 23/06 au 05/12/2025 ; trottoirs du Vercors achevés le 30/01/2026. Les seules images de l'état 2026 "
      "sont les photos Panoramax du 28/07/2026, prises sur la place, environ 135 m au sud du cœur : aucune ne voit le cœur. "
      "Toutes les autres sont antérieures à la fin des travaux, y compris la série à plat du 31/08/2025 (en plein chantier). "
      "Une observation antérieure ne vaut pour une entité dans l'emprise des travaux (à 3 m au plus, au point observé pour "
      "une ligne ou une surface) que si une règle appuie sa conservation (FUS-DATE-02).")
    w("")
    w("| classe de date (FUS-DATE-02) | liens observation-entité | avec appui de règle | non probants (motifs) |")
    w("|---|---|---|---|")
    for c in CLASSES_DATE:
        ls_ = [l for l in liens if l["classe_date"] == c]
        mot = Counter(m for l in ls_ for m in (l.get("non_probant") or []))
        w(f"| {c} | {len(ls_)} | {sum(1 for l in ls_ if l.get('appui_conservation'))} | "
          + (", ".join(f"{k} {v}" for k, v in sorted(mot.items())) or "-") + " |")
    w("")
    app = Counter(re.sub(r"\s*\([^()]*\)$", "", (l.get("appui_conservation") or "").split(" : ")[-1]) for l in liens
                  if l["classe_date"] == "avant_travaux_dans_emprise" and l.get("appui_conservation"))
    if app:
        w("Appuis de conservation utilisés : " + ", ".join(f"{k} ({v})" for k, v in sorted(app.items(), key=lambda t: (-t[1], t[0])))
          + ".")
        w("")
    # ---- entrées ----
    w("## Entrées")
    w("")
    w("| fichier | observations |")
    w("|---|---|")
    for f, k in obs_par_fichier:
        w(f"| `{rel(f)}` | {k} |")
    w(f"| `{rel(ARBITRAGES)}` (constats de revue, FUS-ARB-01) | {len(F.obs_revue)} |")
    w("")
    w(f"Total : {len(F.obs)} observations. Description lue : base v0.3 (`{BASE.name}/`), objets du paquet, instances, "
      "bordures du site (carte de cohérence), surfaces v1, corrections et propositions de cohérence, levé GAM 2026 des arbres, "
      f"arbitrages de revue (`{ARBITRAGES.name}`). Les empreintes SHA-256 de toutes les entrées sont dans "
      "`observations_index.json` (`meta.entrees`).")
    w("")
    # ---- synthèse ----
    n_mv = [r for r in res if (r.get("position") or {}).get("verdict") in ("affinage", "deplacement", "translation")]
    n_app = sum(1 for r in n_mv if r["position"].get("decision") == "appliquer")
    n_ret = sum(1 for r in res if r["existence"]["verdict"] in VERDICTS_RETRAIT)
    n_av = sum(1 for r in res if r["existence"]["verdict"] == "absent_2026_a_verifier")
    maj_app = sum(1 for r in res for m in r["maj"].values() if m.get("decision") == "appliquer")
    maj_tot = sum(len(r["maj"]) for r in res)
    vc_ = Counter(c.get("verdict") for c in F.controle_coh if c.get("verdict"))
    w("## Synthèse")
    w("")
    w(f"- {len(res)} entités de la description reçoivent au moins une observation ; {sv['confirme']} sont **confirmées** "
      f"(preuve stricte, sans correction) ; {sv['corrige']} corrigées ; {sv['conteste']} contestées (vue de bordure) ; "
      f"{sv['indice_seulement']} n'ont qu'un indice ; {sv['non_valable_2026']} ne sont vues qu'avant leur forme 2026 ou "
      "sans appui de conservation.")
    w(f"- Attributs : {sum(1 for r in res if r['maj'])} entités ont au moins une mise à jour ({maj_tot} mises à jour, dont "
      f"{maj_app} à appliquer et {maj_tot - maj_app} en revue, FUS-ATT-06).")
    w(f"- Position : {len(n_mv)} corrections mesurées, dont {n_app} à appliquer et {len(n_mv) - n_app} en revue (FUS-POS-05/06).")
    w(f"- Existence : {n_ret} entités à retirer ou absentes en 2026 ; {n_av} absences à vérifier (FUS-EXI-04).")
    w(f"- Ajouts : {len(F.ajouts)} objets nouveaux, dont {sum(1 for a in F.ajouts if a['instancier'])} "
      f"instanciables ; {len(F.ajouts_refuses)} ajouts remplacés par un conflit avec le levé GAM (FUS-ADD-04).")
    w(f"- Conflits : {len(F.conflits)} ({sum(1 for c in F.conflits if c['gravite'] == 'a_verifier')} à vérifier, "
      f"{sum(1 for c in F.conflits if c['gravite'] == 'info')} pour information).")
    w(f"- Cohérence : {len(F.controle_coh)} corrections du solveur ont une preuve image ; "
      + ", ".join(f"{k} {v}" for k, v in sorted(vc_.items())) + ".")
    w("")
    # ---- couverture ----
    w("## Couverture")
    w("")
    w("Entités de la description (base v0.3 + objets du paquet). **Stricte** (FUS-COUV-02, décisions) : classe de date de la "
      "meilleure preuve stricte (après travaux > avant travaux hors emprise > avant travaux dans l'emprise avec appui de "
      "règle). « indice » : vue concluante au sens large sans preuve stricte. **Large** (FUS-COUV-01, définition 0.2, "
      "comparaison seulement) : preuve image concluante quelle que soit sa confiance. « auto seul » : preuve large venant "
      "uniquement de contrôles automatiques. Cœur : carré ± 80 m autour de l'origine ; zone 2025 : FUS-ZONE-01.")
    w("")
    for z in ("site", "coeur", "zone_travaux_2025"):
        T = couv[z]
        w(f"### {noms[z]}")
        w("")
        w("| classe | entités | **stricte %** | après travaux | avant, hors emprise | avant, dans l'emprise (appui) | indice | "
          "non concluant | non valable 2026 | sans observation | large % | auto seul | confirmées |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for cls, d in T.items():
            nom = "**total**" if cls == "total" else cls
            s_, l_ = d["stricte"], d["large"]
            w(f"| {nom} | {d['n']} | **{s_['pct']}** | {s_['apres_travaux']} | {s_['avant_travaux_hors_emprise']} | "
              f"{s_['avant_travaux_dans_emprise']} | {s_['indice_seulement']} | {s_['non_concluant']} | {s_['non_valable_2026']} | "
              f"{s_['aucune']} | {l_['pct']} | {d['automatique_seule']} | {d['confirmees']} |")
        w("")
    roles = Counter(t["role"] for t in F.index_obs.values())
    w(f"Rôle des observations : {', '.join(f'{k} {v}' for k, v in sorted(roles.items()))}. "
      "« contexte » et « temporaire » ne sont jamais fusionnés (FUS-CTX-01, FUS-TMP-01) ; « conflit_ajout » : ajout remplacé "
      "par un conflit avec le levé GAM (FUS-ADD-04) ; « non_apparie » : observations sans lien ni candidat (voir l'index).")
    w("")
    # ---- liens groupés ----
    w("## Liens groupés (FUS-LIEN-09)")
    w("")
    grp = [t for t in F.index_obs.values() if "FUS-LIEN-09" in t["drapeaux"]]
    for t in sorted(grp, key=lambda t: t["id"]):
        w(f"- `{t['id']}` : prouvées {', '.join(t.get('liens_groupes_prouves') or []) or 'aucune'} ; vues sans preuve propre "
          f"{', '.join(t.get('liens_groupes_non_prouves') or [])}.")
    w("")
    # ---- contrôles automatiques ----
    w("## Contrôles automatiques (FUS-AUTO-01/02)")
    w("")
    auto = Counter()
    for n in F.obs:
        if n["auto"] and n["classe"] in CLASSES_AUTO_REQUALIFIEES and n["statut"] == "confirme" \
                and n["type_source"] in ("ortho2022", "ortho_recente"):
            v = F.requalifiees.get(n["id"], "non_liee")
            auto[(n["agent"], n["classe"], v)] += 1
    w("| atelier | classe | confirmations automatiques | requalifiées « incertain » | corroborées par une observation manuelle |")
    w("|---|---|---|---|---|")
    for ag, cls in sorted({(a, c) for a, c, _ in auto}):
        tot_ = sum(v for (a, c, _), v in auto.items() if a == ag and c == cls)
        w(f"| {ag} | {cls} | {tot_} | {auto[(ag, cls, 'incertain')]} | {auto[(ag, cls, 'corroboree')]} |")
    w("")
    w("Aucune n'a le contrat FUS-AUTO-02 (masque véhicules / ombres, part masquée ≤ 0,2, réponse de ligne fine ou de "
      "peinture pour un marquage, de ligne fine ou d'arête pour une bordure) : une confirmation automatique ne compte que si "
      "une observation manuelle confirme la même entité, et n'est jamais une preuve stricte. Calcul de référence : "
      "`recon/pcg/enrichir/controle_auto.py` (marquages ; essai sur le PCRS 2022 : `controle_auto_essai.jpg`). Le PCRS 5 cm "
      "est requis pour la réponse de ligne fine : à 20 cm (IGN 2024), un trait de 0,10-0,15 m n'est pas résolu.")
    w("")
    # ---- bordures ----
    w("## Bordures : vue, profil et abaissés (FUS-BOR-01..03)")
    w("")
    w(f"{textes} textes libres lus (champs {', '.join(CHAMPS_PROFIL)}) sur les observations de bordures. Lectures : vue chiffrée "
      f"{nums} (lecture haute), qualificatif explicite {expl} (moyenne : arasée, sans vue, aucune bordure saillante…), vue "
      f"déduite {ded} (faible : « basse », « bordure de trottoir »), abaissé {abv}. Chaque lecture est rapportée à l'abscisse "
      "de l'observation sur la bordure ; le vote se fait par intervalle de la description. Une contradiction est cherchée dans "
      f"l'intervalle observé et dans les intervalles courants vus à ± {FENETRE_BORDURE_M:.0f} m.")
    w("")
    w("| bordure | intervalle | décrit (vue, origine) | lecture | obs | gravité |")
    w("|---|---|---|---|---|---|")
    for eid, c in contra:
        for l_ in c["lectures"]:
            np_ = f", non probante {'/'.join(l_['non_probant'])}" if l_.get("non_probant") else ""
            w(f"| `{eid}` | {c['intervalle']} (s {c['s0']:.1f}-{c['s1']:.1f} m{', voisin' if l_['position'] != 'intervalle de l' + chr(39) + 'observation' else ''}) | "
              f"{c['profil_decrit']} {c['vue_decrite_m']} m ({c['statut_hauteur']}) | « {l_['extrait']} » -> "
              f"{l_['intervalle_lu_m'][0]}-{l_['intervalle_lu_m'][1]} m ({l_['lecture']}{np_}) | {l_['obs']} | {c['gravite']} |")
    w("")
    cinq = ["K-0185", "K-0439", "K-0465", "K-0668", "K-0675"]
    lignes = []
    for k in cinq:
        r = E.get(k) or {}
        b = r.get("bordure") or {}
        if b.get("contradictions_a_verifier"):
            lignes.append(f"`{k}` contradiction signalée (intervalles {', '.join(str(i) for i in b['contradictions_a_verifier'])})")
        else:
            acc = [it for it in b.get("intervalles", []) if it.get("verdict") == "accord"]
            if acc:
                it = acc[0]
                lignes.append(f"`{k}` pas de contradiction au point observé : intervalle {it['intervalle']} "
                              f"(s {it['s0']:.1f}-{it['s1']:.1f} m) décrit {it['profil_decrit']} {it['vue_decrite_m']} m, "
                              f"compatible avec la lecture « arasée »")
            else:
                lignes.append(f"`{k}` sans lecture votée")
    w("Les cinq cas de la critique (« arasée » contre 8 à 14 cm) : " + " ; ".join(lignes) + ". Aucune contradiction n'est "
      "appliquée : la proposition reste « revue_requise » (relevé terrain : photo rasante à moins de 5 m, mètre pliant).")
    w("")
    # ---- priorité 2026 ----
    def ecartees(r):
        return sorted(set((r["existence"].get("obs_anterieures_ecartees") or [])
                          + [x["obs"] for x in (r.get("mesures_anterieures") or [])]
                          + [o for m in r["maj"].values() for o in (m.get("obs_anterieures_ecartees") or [])]
                          + [o for m in r["attributs_confirmes"].values() for o in (m.get("obs_anterieures_ecartees") or [])]))
    v26 = [r for r in res if any(m["n"]["categorie"] == "photo_2026" for m in F.membres[r["id"]])]
    w("## Priorité des photos 2026 (FUS-DATE-01)")
    w("")
    w(f"{len(v26)} entités sont vues sur les photos du 28/07/2026 ({sum(1 for r in v26 if r['tranche_stricte'] == 'apres_travaux')} "
      f"avec une preuve stricte après travaux) ; pour {sum(1 for r in v26 if ecartees(r))} d'entre elles, la photo 2026 a "
      "écarté des observations plus anciennes (existence, attribut ou position).")
    w("")
    w("| entité | statut | existence | position | attributs | observations antérieures écartées |")
    w("|---|---|---|---|---|---|")
    for r in sorted(v26, key=lambda r: r["id"]):
        pos = r.get("position") or {}
        ant = ecartees(r)
        pv = pos.get("verdict", "")
        if pv in ("affinage", "deplacement"):
            pv += f" {pos.get('d_m')} m ({pos.get('decision')})"
        w(f"| `{r['id']}` | {r['statut_verification']} | {r['existence']['verdict']} | {pv} | "
          f"{', '.join(sorted(r['maj'])) or '-'} | {', '.join(ant) or '-'} |")
    w("")
    # ---- arbitrages ----
    w("## Arbitrages de revue (FUS-ARB-01)")
    w("")
    if F.arbitrages:
        w("| id | action | observations | effet | motif |")
        w("|---|---|---|---|---|")
        for a in F.arbitrages:
            eff = "; ".join(a["_applique"]) or "sans effet (conflit arbitrage_inapplicable)"
            if a.get("action") == "ancrer_bord_ilot":
                aj = next((x for x in F.ajouts if x.get("ancrage") and x["ancrage"]["arbitrage"] == a["id"]), None)
                if aj:
                    eff = (f"{aj['id']} ancré au bord de {aj['ancrage']['hote']} ({aj['ancrage']['type_hote']}), "
                           f"déplacé de {aj['ancrage']['deplacement_m']} m")
            elif a.get("action") == "ne_pas_instancier":
                aj = next((x for x in F.ajouts if a["id"] in x.get("arbitrages", [])), None)
                if aj:
                    eff = f"{aj['id']} non instancié"
            elif a.get("action") == "mesure_position" and a["_applique"]:
                pos = (F.res_entites.get(a.get("entite")) or {}).get("position") or {}
                eff = (f"{a.get('entite')} : {pos.get('verdict')} {pos.get('d_m')} m, σ {pos.get('sigma_m')} m, "
                       f"{pos.get('n_mesures_reelles')} mesures, décision {pos.get('decision')}")
            elif a.get("action") == "constat_revue":
                eff = "; ".join(f"{o['id']} -> {o['o']['lien_description']} ({o['statut']}, {o['conf']}) : "
                                f"{(F.res_entites.get(o['o']['lien_description']) or {}).get('statut_verification')}"
                                for o in F.obs_revue if o["attrs"].get("arbitrage") == a["id"])
            elif a.get("action") == "invalider_observation":
                eff = "lien invalidé : " + "; ".join(a["_applique"])
            w(f"| {a['id']} | {a.get('action')} | {', '.join(a.get('obs', []))} | {eff} | {court(a.get('motif', ''), 160)} |")
    else:
        w("Aucun arbitrage.")
    w("")
    # ---- comptes par classe ----
    w("## Comptes par classe (statut de vérification, FUS-STAT-01)")
    w("")
    tab = defaultdict(Counter)
    for r in res:
        c = r["classe"]
        tab[c]["entites"] += 1
        tab[c][r["statut_verification"]] += 1
        pos = r.get("position") or {}
        if pos.get("verdict") in ("affinage", "deplacement", "translation"):
            tab[c]["position"] += 1
            if pos.get("decision") == "appliquer":
                tab[c]["position_appliquer"] += 1
        if r["conflits_ids"]:
            tab[c]["conflit"] += 1
    for a in F.ajouts:
        c = CLASSE_OBS_FUSION.get(a["classe"], "autre")
        tab[c]["ajout"] += 1
        if a["instancier"]:
            tab[c]["ajout_inst"] += 1
        if a["conflits_ids"]:
            tab[c]["conflit"] += 1
    for a in F.ajouts_refuses:
        tab[CLASSE_OBS_FUSION.get(a["classe"], "autre")]["refus"] += 1
    w("| classe | entités vues | confirmées | corrigées | contestées | indice seulement | non valables 2026 | "
      "absentes / à retirer | absence à vérifier | position corrigée (appliquer) | ajouts (instanciés) | ajouts -> conflit GAM | "
      "avec conflit |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    tt = Counter()
    for c in ORDRE_CLASSES:
        t = tab.get(c)
        if not t:
            continue
        tt.update(t)
        w(f"| {c} | {t['entites']} | {t['confirme']} | {t['corrige']} | {t['conteste']} | {t['indice_seulement']} | "
          f"{t['non_valable_2026']} | {t['absent_2026'] + t['a_retirer']} | {t['absent_2026_a_verifier']} | "
          f"{t['position']} ({t['position_appliquer']}) | {t['ajout']} ({t['ajout_inst']}) | {t['refus']} | {t['conflit']} |")
    w(f"| **total** | {tt['entites']} | {tt['confirme']} | {tt['corrige']} | {tt['conteste']} | {tt['indice_seulement']} | "
      f"{tt['non_valable_2026']} | {tt['absent_2026'] + tt['a_retirer']} | {tt['absent_2026_a_verifier']} | "
      f"{tt['position']} ({tt['position_appliquer']}) | {tt['ajout']} ({tt['ajout_inst']}) | {tt['refus']} | {tt['conflit']} |")
    w("")
    cnt_attr = Counter(a for r in res for a in r["maj"] if a != "texte_lu")
    w("Attributs mis à jour : " + ", ".join(f"{k} {v}" for k, v in sorted(cnt_attr.items(), key=lambda t: (-t[1], t[0]))) + ".")
    w("")
    # ---- cohérence ----
    w("## Contrôle croisé avec la cohérence (`coherence/corrections.geojson`)")
    w("")
    vc = Counter(c.get("verdict") for c in F.controle_coh if c.get("verdict"))
    va = Counter(c.get("verdict_azimut") for c in F.controle_coh if c.get("verdict_azimut"))
    w(f"{len(F.controle_coh)} corrections de cohérence ont une preuve image. Positions : "
      + (", ".join(f"{k} {v}" for k, v in sorted(vc.items())) or "aucune") + ". Azimuts : "
      + (", ".join(f"{k} {v}" for k, v in sorted(va.items())) or "aucun") + " (FUS-COH-01).")
    w("")
    w("| entité | cohérence | verdict image | écart image / corrigé | écart image / origine | obs |")
    w("|---|---|---|---|---|---|")
    for c in sorted(F.controle_coh, key=lambda c: c["entite"]):
        v = c.get("verdict") or ""
        if c.get("verdict_azimut"):
            v += f" ; azimut {c['verdict_azimut']} ({c.get('azimut_image_deg')}° / {c.get('azimut_coherence_deg')}°)"
        w(f"| `{c['entite']}` | {c['nature']} {c.get('d_coherence_m') or ''} m | {v} | {c.get('d_image_corrige_m', '')} | "
          f"{c.get('d_image_origine_m', '')} | {', '.join(c.get('obs') or [])} |")
    w("")
    # ---- corrections de position ----
    w("## Corrections de position")
    w("")
    cps = [(eid, r["position"]) for eid, r in sorted(F.res_entites.items())
           if (r.get("position") or {}).get("verdict") in ("affinage", "deplacement", "translation")]
    w("| entité | nature | d (m) | σ (m) | décision | méthodes | obs | raisons |")
    w("|---|---|---|---|---|---|---|---|")
    for eid, p in sorted(cps, key=lambda t: (t[1].get("decision") != "appliquer", -(t[1].get("d_m") or 0), t[0])):
        meth = ", ".join(p.get("methodes") or sorted({m["methode"] for m in p.get("mesures", [])}))
        w(f"| `{eid}` | {p['verdict']} | {p.get('d_m')} | {p.get('sigma_m')} | {p.get('decision')} | {meth} | "
          f"{', '.join(p.get('obs') or [])} | {'; '.join(p.get('raisons') or [])} |")
    w("")
    # ---- existence ----
    exs = [(eid, r) for eid, r in sorted(F.res_entites.items())
           if r["existence"]["verdict"] in VERDICTS_RETRAIT + ("absent_2026_a_verifier",)]
    w("## Existence : entités absentes en 2026, à retirer ou à vérifier")
    w("")
    for eid, r in exs:
        e = r["existence"]
        oids = sorted({o for v in e["obs"].values() for o in v})
        w(f"- `{eid}` ({r['type']}) : **{e['verdict']}**{(' (doublon de `' + r['doublon_de'] + '`)') if r.get('doublon_de') else ''}"
          f"{' [' + e['chronologie'] + ']' if e.get('chronologie') else ''} ; obs {', '.join(oids)}")
    w("")
    # ---- ajouts ----
    w("## Ajouts")
    w("")
    ca = Counter((a["classe"], a["instancier"]) for a in F.ajouts)
    w(f"{len(F.ajouts)} objets nouveaux (groupes d'observations), dont {sum(1 for a in F.ajouts if a['instancier'])} instanciables. "
      "Par classe (instanciés / candidats) : " + ", ".join(
          f"{c} {ca[(c, True)]}/{ca[(c, False)]}" for c in sorted({a['classe'] for a in F.ajouts})) + ". "
      "Un ajout vu seulement avant la fin des travaux, dans leur emprise, n'est pas instancié (FUS-DATE-02).")
    w("")
    if F.ajouts_refuses:
        w(f"{len(F.ajouts_refuses)} ajouts proposés sont remplacés par un conflit `ajout_contre_leve_gam` (FUS-ADD-04, rayon "
          f"{RAYON_DEDOUBLONNAGE_M} m) : " + "; ".join(
              f"{', '.join(a['obs'])} ({', '.join(a['sous_types'])}) à {a['d_m']} m de `{a['entite_gam']}`"
              for a in sorted(F.ajouts_refuses, key=lambda a: a["obs"])) + ".")
        w("")
    w("| id | classe | sous-types | famille cible | preuve stricte | valide 2026 | instancier | obs |")
    w("|---|---|---|---|---|---|---|---|")
    for a in F.ajouts:
        st_ = ", ".join(sorted({n["sous_type"] for n in a["membres"]}))
        w(f"| `{a['id']}` | {a['classe']} | {court(st_, 60)} | {a['fam_cible'] or '-'} | {a['tranche_stricte']} | {a['valide']} | "
          f"{'oui' if a['instancier'] else 'non : ' + '; '.join(a['raisons'])} | {', '.join(n['id'] for n in a['membres'])} |")
    w("")
    # ---- conflits ----
    w("## Conflits")
    w("")
    cc = Counter(c["type"] for c in F.conflits)
    w(f"{len(F.conflits)} conflits : " + ", ".join(f"{k} {v}" for k, v in sorted(cc.items())) + ". Détail dans `conflits.json` "
      "(les conflits d'information ne sont pas listés ici).")
    w("")
    w("| id | type | cible | obs | détail |")
    w("|---|---|---|---|---|")
    for c in F.conflits:
        if c["gravite"] == "info":
            continue
        w(f"| {c['id']} | {c['type']} | `{c['cible']}` | {', '.join(c['obs'])} | {court(texte(c['detail']), 220)} |")
    w("")
    # ---- carte ----
    w("## Carte de couverture")
    w("")
    if avec_carte:
        w("`couverture_preuves.png` : A/C preuve stricte par entité et par bordure, colorée par classe de date relative aux "
          "travaux (rampe bleue ordinale : avant travaux dans l'emprise avec appui clair, avant travaux hors emprise moyen, "
          "après travaux foncé ; anneau gris foncé : indice seulement ; anneau gris clair : non concluant ou non valable 2026 ; "
          "petit point gris : aucune observation), zone des travaux hachurée (extension FUS-ZONE-01 comprise), positions des "
          "photos citées (croix : Panoramax, point : Mapillary, étoile : photo 2026) ; B/D décisions (carré orange plein : "
          "attribut à appliquer, creux : en revue ; flèche : déplacement, à l'échelle au-delà de 1 m et x5 en dessous ; "
          "losange aqua : ajout ; croix épaisse : absent / retirer, fine : absence à vérifier ; point gris : confirmée ; anneau "
          "rouge : conflit à vérifier). Fond : ortho 2022 éclaircie. `couverture.json` : tableaux complets (large et stricte).")
    else:
        w("Carte non produite (`--sans-carte`) ; `couverture.json` : tableaux de couverture.")
    w("")
    w("## Règles de fusion")
    w("")
    for k, v in REGLES.items():
        w(f"- **{k}** : {v}")
    w("")
    w("## Limites")
    w("")
    w("- Aucune image publique ne montre le cœur après les travaux : les 7 photos du 28/07/2026 sont sur la place, environ "
      "135 m au sud, et seules 3 sont calées ; aucune entité du cœur n'a de preuve stricte après travaux. Seule une campagne "
      "terrain (stations du protocole, à compléter de S13, S14 et S15 proposées par la critique) peut couvrir le cœur et la "
      "zone des travaux.")
    w("- L'emprise des travaux est celle des surfaces et zones de relief 2025 connues, plus les surfaces vues refaites en 2026 "
      "(FUS-ZONE-01) ; une reprise non vue (trottoirs du Vercors au-delà de la photo) reste hors emprise.")
    w("- Les appuis de conservation (FUS-DATE-02) reposent sur les états de la description (marquage « conserve », bordure "
      "hors périmètre refait…) : une erreur de ces états se propage.")
    w("- Les lectures de profil de bordure viennent de textes libres : la vue chiffrée est une estimation visuelle, pas une "
      "mesure ; une contradiction n'est jamais appliquée sans relevé.")
    w("- Les confirmations automatiques requalifiées ne sont pas des absences : ces objets restent décrits, sans preuve.")
    w("- `recon/pcg/enrichir/PROTOCOLE_TERRAIN.md` n'est pas modifié par la fusion : son propriétaire doit y reporter les "
      "stations S13, S14 et S15 de la critique, l'ordre de passage et les nouveaux taux sans preuve stricte (tableaux "
      "ci-dessus), et demander une photo rasante, mètre pliant en place, sur chaque bordure contestée.")
    w("- La description de base est régénérée en parallèle : relancer ce script après chaque régénération "
      "(les liens disparus deviennent des conflits `lien_introuvable`).")
    w("- Les poids et seuils (REGLES) sont des choix documentés, pas des mesures ; les sorties restent des propositions "
      "pour le composeur et l'arbitrage.")
    w("")
    (OUT / "RESUME.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sans-carte", action="store_true")
    args = ap.parse_args()
    ix = charger_index()
    vocab = set(charger_json(ROOT / "recon/pcg/schema/materiaux_description.json").get("materiaux", {}).keys())
    obs, par_fichier = [], []
    for f in FICHIERS_OBS:
        if not f.exists():
            par_fichier.append((f, 0))
            continue
        d = charger_json(f)
        agent = f.stem.replace("obs_", "")
        ix.entrees[rel(f)] = sha256(f)
        par_fichier.append((f, len(d)))
        for o in d:
            obs.append(normaliser_obs(o, agent, ix))
    obs.sort(key=lambda n: n["id"])
    F = Fusion(ix, obs, vocab)
    F.executer()
    ecrire_sorties(F, ix)
    couv = couverture(F, ix)
    ix.entrees[rel(PKG / "relief/relief_zones_2026.geojson")] = sha256(PKG / "relief/relief_zones_2026.geojson")
    ecrire_json(OUT / "couverture.json", {
        "schema": "pj_enrichi_couverture/0.2", "generateur": VERSION,
        "regles": {"large": "FUS-COUV-01 (définition 0.2, comparaison seulement)",
                   "stricte": "FUS-COUV-02 (décisions : statut confirmé, application, carte)",
                   "classes_date": "FUS-DATE-02", "zone_travaux": "FUS-ZONE-01"},
        "tranches_large": TRANCHES, "tranches_strictes": TRANCHES_STRICTES,
        "zones": {"site": "toutes les entités décrites",
                  "coeur": f"carré ± {COEUR_DEMI_M:.0f} m autour de l'origine",
                  "zone_travaux_2025": "surfaces modifie_2025, zones de chaussée reprises en 2025 et extension FUS-ZONE-01 ("
                                       + ", ".join(f"{k} : {', '.join(v)}" for k, v in F.zone_extension.items()) + ")"},
        "reference_0_2": REFERENCE_0_2,
        "couverture": couv})
    if not args.sans_carte:
        carte(F, ix, OUT / "couverture_preuves.png")
    # méta dans l'index (entrées et hash)
    idx = charger_json(OUT / "observations_index.json")
    idx["meta"] = {"generateur": VERSION, "commande": "python recon/pcg/enrichir/fusion_recensement.py",
                   "entrees": dict(sorted(ix.entrees.items())), "regles": REGLES}
    ecrire_json(OUT / "observations_index.json", idx)
    resume(F, ix, par_fichier, not args.sans_carte, couv)
    print(f"observations {len(F.obs)} (dont {len(F.obs_revue)} constats de revue) ; entités {len(F.res_entites)} ; ajouts {len(F.ajouts)} "
          f"({sum(1 for a in F.ajouts if a['instancier'])} instanciés) ; conflits {len(F.conflits)} ; "
          f"corrections {sum(1 for r in F.res_entites.values() if (r.get('position') or {}).get('verdict') in ('affinage', 'deplacement', 'translation'))}")
    print(f"sorties : {rel(OUT)}")


if __name__ == "__main__":
    main()
