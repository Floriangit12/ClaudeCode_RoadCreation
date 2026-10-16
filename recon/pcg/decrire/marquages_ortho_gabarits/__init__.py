"""Marquages sur ortho, ajustés aux gabarits, indépendants d'OpenDRIVE (lot 1j du plan avant travaux).

Promu du pilote v2_avant_travaux/inventaire/marquages/pilote/{detection, zebras, fleches, lignes, damiers}.py.
Lit l'ortho PCRS 5 cm 2022 (référence), la BD ORTHO IGN 2024 (secteur reconstruit, précision dégradée) et les
gabarits IISR (assets/specs/marquages_geometrie.json, lecture seule). Aucun réseau OpenDRIVE, aucun levé GAM en
entrée ; la v1 n'est pas lue par ce paquet.

Modules :
  raster       mosaïques, filtres, étiquetage, rastérisation, géométrie (numpy + Pillow)
  detection    probabilité de peinture (fond au 30e percentile, ombres séparées), composantes
  cretes       détecteur de crêtes fines (Hessien multi-échelle), chaînage en polylignes
  lignes       mesure sous-pixel des lignes, files, modulation IISR, phase, segments peints / masqués
  occultation  houppiers, véhicules, ombres denses (sortie « masquee »)
  zebras, fleches, damiers   passages, flèches (gabarits IISR), pavés et carrés (repris du pilote)
  coins        coins nets de marques (GCP candidats)
  extraction   chaîne complète par blocs sur une emprise
  reference    tuiles réservées, planches d'annotation, mesure contre l'annotation
  planches     superpositions de contrôle (ortho seulement)
"""
VERSION = "1.0"
