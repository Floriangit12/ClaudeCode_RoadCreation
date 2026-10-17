"""Description 1D des itinéraires du prototype (sous-ensemble du modèle de route, conception § 10).

Un itinéraire (Route) porte une abscisse curviligne s (m) de l'avant du véhicule, une voie (pour la
recherche du meneur), le réseau ONISR de la vitesse désirée (CR-xx), et des points singuliers :
courbes (rayon), ralentisseurs, feux, STOP, détecteurs, jonction vers une autre voie (insertion).
Plusieurs « couloirs » indépendants partagent la même géométrie : ce sont les réplications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class Courbe:
    s0: float
    s1: float
    R: float
    agglo: Optional[bool] = None      # None : celle de la route ; True pour une trajectoire de carrefour


@dataclass
class Ralentisseur:
    s: float
    longueur: float


@dataclass
class Feu:
    """Feu sur la ligne s. Horaires par couloir (tableaux) ou communs (scalaires) :
    rouge jusqu'à t_vert, vert jusqu'à t_jaune, jaune pendant duree_jaune, puis rouge."""
    s: float
    t_vert: object = -np.inf
    t_jaune: object = np.inf
    duree_jaune: float = 3.0

    @staticmethod
    def _par_couloir(x, couloirs):
        return np.asarray(x, float)[couloirs] if np.ndim(x) else np.full(np.shape(couloirs), float(x))

    def etats(self, t: float, couloirs: np.ndarray) -> np.ndarray:
        """0 = vert, 1 = jaune, 2 = rouge, pour chaque couloir donné."""
        tv = self._par_couloir(self.t_vert, couloirs)
        tj = self._par_couloir(self.t_jaune, couloirs)
        e = np.full(np.shape(couloirs), 2, dtype=np.int8)
        e[(t >= tv) & (t < tj)] = 0
        e[(t >= tj) & (t < tj + self.duree_jaune)] = 1
        return e

    def t_jaune_couloir(self, couloirs: np.ndarray) -> np.ndarray:
        return self._par_couloir(self.t_jaune, couloirs)


@dataclass
class Stop:
    """Ligne STOP en s ; la voie prioritaire et l'abscisse du point de conflit (sur la voie prioritaire)."""
    s: float
    voie_prioritaire: int
    s_conflit: float
    creneau_ref_s: float = 5.0          # t_c du Certu pour la manœuvre (insertion TAD à 50 km/h)


@dataclass
class Jonction:
    """Au-delà de s (sur cet itinéraire), le véhicule est projeté sur la voie cible :
    s_cible = s - self.s + self.s_cible."""
    s: float
    voie: int
    s_cible: float


@dataclass
class Route:
    nom: str
    voie: int
    longueur: float
    reseau: str                          # clé de conducteurs.RESEAUX
    vlim_setra_kmh: float = 102.0        # Vlim de la relation Sétra (2 voies de 6-7 m)
    pente: float = 0.0
    courbes: list = field(default_factory=list)
    ralentisseurs: list = field(default_factory=list)
    feux: list = field(default_factory=list)
    stops: list = field(default_factory=list)
    jonction: Optional[Jonction] = None
    detecteurs: list = field(default_factory=list)   # abscisses

    def courbure(self, s) -> np.ndarray:
        s = np.asarray(s, float)
        k = np.zeros_like(s)
        for c in self.courbes:
            k = np.where((s >= c.s0) & (s <= c.s1), 1.0 / c.R, k)
        return k
