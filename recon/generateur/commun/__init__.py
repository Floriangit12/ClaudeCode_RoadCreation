# -*- coding: utf-8 -*-
"""Socle commun du générateur (lot L0) : provenance, géométrie de la ligne de référence, construction des profils.

Utilisé par `inference/osm_vers_modele.py` (tags OSM → modèle) et `description/description_vers_modele.py`
(description simple → modèle) : les deux passent par la même construction de profil (`commun/profil.py`), si bien
qu'une même bande décrite ou inférée reçoit les mêmes largeurs, niveaux, limites et marquages par défaut, avec les
mêmes règles citées.
"""
