# -*- coding: utf-8 -*-
"""Valeurs approchées de la couche réseau (FORMAT_DESCRIPTION_RESEAU.md § 4) : lecture, plage, choix.

Écritures reconnues (le reste du texte est gardé tel quel) :
    20, 20 m, 20,0                      exacte (plage nulle)
    ≈ 20, ~20, environ 20, à peu près 20, vers 20
                                        plage par défaut de la grandeur (§ 4.2)
    20 ± 3, 20 +/- 3                    [17 ; 23]
    15 à 25, entre 15 et 25             [15 ; 25]
    au moins 20, ≥ 20                   [20 ; borne haute de la règle, sinon 2 × 20]
    au plus 20, ≤ 20                    [borne basse de la règle, sinon 0 ; 20]
    … (mesure 3,62 ortho)               mesure attachée à la valeur (source libre après le nombre)

Choix (§ 4.3, corrigé après la relecture F1) : 1. la mesure attachée, toujours retenue ; si elle tombe hors de la
plage dite, elle prime quand même et un avertissement le dit (jamais de retour au centre) ; 2. la valeur de la règle
qui fixe la grandeur, si elle tombe dans la plage ; 3. le centre de la plage (avertissement « valeur prise au
centre »). Déterministe : même texte, même choix.
"""
from __future__ import annotations

import re

NUM = r"\d+(?:[.,]\d+)?"

# demi-plages par défaut d'« environ X » (FORMAT § 4.2) : (absolu, relatif, minimum absolu)
PLAGES = {
    "largeur_photo": (0.50, 0.0, 0.0),      # largeur de bande vue sur photo
    "largeur_ortho": (0.30, 0.0, 0.0),      # largeur mesurée sur l'ortho 20 cm
    "vue": (0.04, 0.0, 0.0),                # vue de bordure
    "longueur": (0.0, 0.10, 1.0),           # longueur le long d'un tronçon
    "abscisse": (0.0, 0.10, 2.0),           # abscisse d'un évènement depuis un nœud
    "rayon": (0.0, 0.20, 0.0),
    "diametre": (0.0, 0.10, 0.0),           # diamètre extérieur ou largeur d'anneau de giratoire
    "angle": (10.0, 0.0, 0.0),
    "hauteur": (0.20, 0.0, 0.0),
    "distance": (0.0, 0.10, 1.0),           # distance d'un nœud relatif
}

_ENV = r"(?:≈|~|environ|à peu près|a peu pres|à peu pres|vers)"
MOTIFS = [
    ("pm", re.compile(rf"(?P<n>{NUM})\s*(?:m\s*)?(?:±|\+/-|\+-)\s*(?P<d>{NUM})", re.I)),
    ("entre", re.compile(rf"entre\s+(?P<a>{NUM})\s*(?:m\s+)?et\s+(?P<b>{NUM})", re.I)),
    ("a", re.compile(rf"(?<![\w.,])(?P<a>{NUM})\s*(?:m\s+)?(?:à|a)\s+(?P<b>{NUM})(?![\w.,])", re.I)),
    ("env", re.compile(rf"{_ENV}\s*(?P<n>{NUM})", re.I)),
    ("min", re.compile(rf"(?:au moins|≥|>=)\s*(?P<n>{NUM})", re.I)),
    ("max", re.compile(rf"(?:au plus|≤|<=)\s*(?P<n>{NUM})", re.I)),
]
MESURE = re.compile(rf"\(\s*(?:mesure|mesuré|mesurée|mesuree|mesure:)\s*:?\s*(?P<v>{NUM})\s*(?:m\b)?\s*(?P<src>[^)]*)\)",
                    re.I)
INDICE_APPROX = re.compile(rf"≈|~|±|\+/-|environ|peu pr|\bentre\b|au moins|au plus|≥|≤|>=|<=|\(\s*mesur", re.I)


class ErreurApprox(ValueError):
    pass


def f(x: str) -> float:
    return float(str(x).replace(",", "."))


def demi_plage(kind: str, x: float) -> float:
    a, r, m = PLAGES[kind]
    return max(a, r * abs(x), m)


def lire(texte: str, kind: str):
    """Première valeur approchée du texte : dict {forme, dit, lo, hi, debut, fin, mesure, source_mesure} ; None si le
    texte n'en contient pas. Les positions (debut, fin) couvrent l'expression à remplacer, mesure comprise."""
    s = str(texte)
    best = None
    for forme, rx in MOTIFS:
        m = rx.search(s)
        if m and (best is None or m.start() < best[1].start()):
            best = (forme, m)
    mes = MESURE.search(s)
    if best is None and mes is None:
        return None
    out = {"texte": s}
    if best is not None:
        forme, m = best
        out.update(forme=forme, debut=m.start(), fin=m.end())
        if forme == "pm":
            c, d = f(m["n"]), f(m["d"])
            out.update(dit=c, lo=c - d, hi=c + d)
        elif forme in ("entre", "a"):
            a, b = f(m["a"]), f(m["b"])
            if b < a:
                raise ErreurApprox(f"plage inversée « {m.group(0)} »")
            out.update(dit=(a + b) / 2.0, lo=a, hi=b)
        elif forme == "env":
            c = f(m["n"])
            h = demi_plage(kind, c)
            out.update(dit=c, lo=c - h, hi=c + h)
        elif forme == "min":
            c = f(m["n"])
            out.update(dit=c, lo=c, hi=None)
        elif forme == "max":
            c = f(m["n"])
            out.update(dit=c, lo=None, hi=c)
    if mes is not None:
        out["mesure"] = f(mes["v"])
        out["source_mesure"] = mes["src"].strip() or "mesure"
        if best is None:                      # « 3,6 (mesure 3,62 ortho) » : valeur exacte dite + mesure
            m0 = re.search(rf"(?P<n>{NUM})\s*(?:m\b)?\s*$", s[:mes.start()])
            if m0 is None:
                raise ErreurApprox(f"mesure sans valeur dite dans « {s} »")
            c = f(m0["n"])
            h = demi_plage(kind, c)       # valeur dite sans « ≈ » mais mesurée : sa plage est celle de la grandeur
            out.update(forme="mesuree", dit=c, lo=c - h, hi=c + h, debut=m0.start(), fin=m0.end())
        out["debut_mesure"], out["fin_mesure"] = mes.start(), mes.end()
    return out


def contient_approx(texte) -> bool:
    return isinstance(texte, str) and bool(INDICE_APPROX.search(texte))


def choisir(ap: dict, regle: tuple | None, chemin: str, avert: list):
    """(valeur, entrée de rapport). regle = (valeur, identifiant, note) ou None."""
    lo, hi = ap["lo"], ap["hi"]
    rv = regle[0] if regle else None
    if lo is None:
        lo = 0.0
    if hi is None:
        hi = max(ap["dit"] * 2.0, rv if rv is not None and rv >= ap["dit"] else 0.0)
    if lo > hi + 1e-12:
        raise ErreurApprox(f"{chemin} : plage vide ou inversée [{lo} ; {hi}]")
    ent = {"chemin": chemin, "texte": ap["texte"].strip(), "forme": ap["forme"], "plage": [round(lo, 4), round(hi, 4)]}
    if "mesure" in ap:
        v = ap["mesure"]
        ent.update(valeur=v, choix="mesure", source=ap["source_mesure"])
        if not (lo - 1e-9 <= v <= hi + 1e-9):
            ent["hors_plage"] = True
            avert.append(f"{chemin} : mesure {v} ({ap['source_mesure']}) hors de la plage dite [{lo:g} ; {hi:g}] : "
                         "la mesure prime, la description est à revoir (FORMAT_DESCRIPTION_RESEAU § 4.3)")
        return v, ent
    if ap["forme"] == "exacte":
        ent.update(valeur=ap["dit"], choix="dit")
        return ap["dit"], ent
    if rv is not None and lo - 1e-9 <= rv <= hi + 1e-9:
        ent.update(valeur=rv, choix="regle", regle=regle[1])
        if regle[2]:
            ent["note"] = regle[2]
        return rv, ent
    c = (lo + hi) / 2.0 if ap["forme"] not in ("min", "max") else ap["dit"]
    ent.update(valeur=round(c, 4), choix="centre")
    if rv is not None:
        ent["regle_hors_plage"] = {"regle": regle[1], "valeur": rv}
    avert.append(f"{chemin} : « {ap['texte'].strip()} » : aucune mesure ni règle dans [{lo:g} ; {hi:g}], "
                 f"valeur prise au centre {c:g}")
    return round(c, 4), ent


def fmt(x: float) -> str:
    """Nombre écrit à la française pour un texte de profil (« 3,25 »)."""
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def sans_valeur(ap: dict) -> str:
    """Texte sans l'expression approchée ni la mesure attachée (pour lire la règle de la grandeur non dite)."""
    s = ap["texte"]
    morceaux = [(ap["debut"], ap["fin"])]
    if "debut_mesure" in ap:
        morceaux.append((ap["debut_mesure"], ap["fin_mesure"]))
    for a, b in sorted(morceaux, reverse=True):
        s = s[:a] + " " + s[b:]
    return re.sub(r"\s{2,}", " ", s).strip()


def remplacer(texte: str, ap: dict, valeur: float) -> str:
    """Texte où l'expression approchée (et la mesure attachée) est remplacée par la valeur exacte."""
    s = ap["texte"]
    morceaux = [(ap["debut"], ap["fin"], fmt(valeur))]
    if "debut_mesure" in ap:
        morceaux.append((ap["debut_mesure"], ap["fin_mesure"], ""))
    for a, b, r in sorted(morceaux, reverse=True):
        s = s[:a] + r + s[b:]
    return re.sub(r"\s{2,}", " ", s).strip()
