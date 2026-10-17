# -*- coding: utf-8 -*-
"""Lecteur YAML restreint et déterministe pour les descriptions simples (`description_simple/0.1`).

PyYAML n'est installé ni dans le Python du dépôt ni dans hython 22 : ce module lit le sous-ensemble de YAML 1.2
employé par les fichiers de `recon/generateur/scenes_simples/`, de façon que **PyYAML lirait la même chose** :

- mappings en bloc (`cle: valeur`, `cle:` suivi d'un bloc indenté) ;
- séquences en bloc (`- element`), y compris `- cle: valeur` (mapping dans une séquence) ;
- collections en ligne `{a: 1, b: [x, y]}` et `[1, 2]`, éventuellement sur plusieurs lignes ;
- scalaires : entiers, flottants, `true` / `false`, `null` / `~`, chaînes nues ou entre guillemets ('…' ou "…") ;
- commentaires `#` (en début de ligne, ou précédés d'un blanc).

Refusé (erreur explicite plutôt qu'une lecture différente de PyYAML) : tabulations d'indentation, ancres et alias
(`&`, `*`), balises (`!`), blocs littéraux (`|`, `>`), clés complexes (`?`), documents multiples (`---`), et les
booléens YAML 1.1 `yes / no / on / off` (PyYAML les lit comme des booléens : on exige `true` / `false`).

    from yaml_simple import charger, charger_texte
    d = charger("S02_rue_1x1_bordures_trottoirs.yaml")
"""
from __future__ import annotations

import re
from pathlib import Path

_ENTIER = re.compile(r"^[-+]?(0|[1-9][0-9]*)$")
_FLOTTANT = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")
_BOOL_11 = {"yes", "no", "on", "off", "y", "n", "Yes", "No", "On", "Off", "YES", "NO", "ON", "OFF"}


class ErreurYaml(ValueError):
    def __init__(self, msg: str, ligne: int | None = None, fichier: str | None = None):
        loc = f"{fichier or '<texte>'}:{ligne}" if ligne is not None else (fichier or "<texte>")
        super().__init__(f"{loc} : {msg}")


def _etats_guillemets(ligne: str):
    """Pour chaque caractère : (dans_simple, dans_double) AVANT ce caractère. Un guillemet n'ouvre une chaîne
    qu'en début de jeton (début de ligne ou après un blanc, « [ », « { », « , », « : ») : l'apostrophe de « T'1 »
    ou de « l'axe » ne compte pas (comme en YAML, où un scalaire nu peut contenir une apostrophe)."""
    simple = double = False
    etats = []
    i = 0
    while i < len(ligne):
        c = ligne[i]
        etats.append((simple, double))
        debut_jeton = i == 0 or ligne[i - 1] in " \t[{,:-"
        if c == "'" and not double:
            if simple:
                if i + 1 < len(ligne) and ligne[i + 1] == "'":   # '' : apostrophe échappée, la chaîne continue
                    etats.append((simple, double))
                    i += 2
                    continue
                simple = False
            elif debut_jeton:
                simple = True
        elif c == '"' and not simple:
            if double:
                if ligne[i - 1] != "\\":
                    double = False
            elif debut_jeton:
                double = True
        i += 1
    return etats


def _sans_commentaire(ligne: str) -> str:
    """Retire un commentaire `#` (début de ligne ou précédé d'un blanc), hors guillemets."""
    etats = _etats_guillemets(ligne)
    for i, c in enumerate(ligne):
        s, d = etats[i]
        if c == "#" and not s and not d and (i == 0 or ligne[i - 1] in " \t"):
            return ligne[:i].rstrip()
    return ligne.rstrip()


def scalaire(txt: str, ligne: int | None = None):
    """Valeur d'un scalaire nu ou entre guillemets."""
    t = txt.strip()
    if t == "":
        return None
    if t[0] in "&*!|>?%@`":
        raise ErreurYaml(f"construction YAML non prise en charge : « {t} »", ligne)
    if t[0] == "'":
        if len(t) < 2 or t[-1] != "'":
            raise ErreurYaml(f"chaîne mal fermée : {t}", ligne)
        return t[1:-1].replace("''", "'")
    if t[0] == '"':
        if len(t) < 2 or t[-1] != '"':
            raise ErreurYaml(f"chaîne mal fermée : {t}", ligne)
        return (t[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\"))
    if t in ("null", "Null", "NULL", "~"):
        return None
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if t in _BOOL_11:
        raise ErreurYaml(f"« {t} » est un booléen en YAML 1.1 (PyYAML) : écrire true / false ou le citer", ligne)
    if _ENTIER.match(t):
        return int(t)
    if _FLOTTANT.match(t):
        return float(t)
    if ": " in t or t.endswith(":"):
        raise ErreurYaml(f"« : » inattendu dans un scalaire : « {t} »", ligne)
    return t


# ------------------------------------------------------------------------------------------- collections en ligne
class _Flux:
    def __init__(self, txt: str, ligne: int | None):
        self.t, self.i, self.ligne = txt, 0, ligne

    def blancs(self):
        while self.i < len(self.t) and self.t[self.i] in " \t\n":
            self.i += 1

    def valeur(self):
        self.blancs()
        if self.i >= len(self.t):
            raise ErreurYaml("collection en ligne incomplète", self.ligne)
        c = self.t[self.i]
        if c == "{":
            return self.mapping()
        if c == "[":
            return self.sequence()
        if c in "'\"":
            fin = self.i + 1
            while True:
                fin = self.t.find(c, fin)
                if fin < 0:
                    raise ErreurYaml("chaîne mal fermée", self.ligne)
                if c == "'" and fin + 1 < len(self.t) and self.t[fin + 1] == "'":
                    fin += 2
                    continue
                break
            brut = self.t[self.i:fin + 1]
            self.i = fin + 1
            return scalaire(brut, self.ligne)
        debut = self.i
        while self.i < len(self.t) and self.t[self.i] not in ",]}":
            if self.t[self.i] == ":" and (self.i + 1 >= len(self.t) or self.t[self.i + 1] in " ,]}"):
                break
            self.i += 1
        return scalaire(self.t[debut:self.i], self.ligne)

    def mapping(self):
        self.i += 1
        d = {}
        while True:
            self.blancs()
            if self.i < len(self.t) and self.t[self.i] == "}":
                self.i += 1
                return d
            cle = self.valeur()
            self.blancs()
            if self.i >= len(self.t) or self.t[self.i] != ":":
                raise ErreurYaml(f"« : » attendu après la clé {cle!r}", self.ligne)
            self.i += 1
            v = self.valeur()
            if cle in d:
                raise ErreurYaml(f"clé en double : {cle}", self.ligne)
            d[cle] = v
            self.blancs()
            if self.i < len(self.t) and self.t[self.i] == ",":
                self.i += 1
            elif self.i < len(self.t) and self.t[self.i] == "}":
                continue
            else:
                raise ErreurYaml("« , » ou « } » attendu", self.ligne)

    def sequence(self):
        self.i += 1
        s = []
        while True:
            self.blancs()
            if self.i < len(self.t) and self.t[self.i] == "]":
                self.i += 1
                return s
            s.append(self.valeur())
            self.blancs()
            if self.i < len(self.t) and self.t[self.i] == ",":
                self.i += 1
            elif self.i < len(self.t) and self.t[self.i] == "]":
                continue
            else:
                raise ErreurYaml("« , » ou « ] » attendu", self.ligne)


def _flux(txt: str, ligne: int | None):
    f = _Flux(txt, ligne)
    v = f.valeur()
    f.blancs()
    if f.i != len(f.t):
        raise ErreurYaml(f"texte après la collection : « {f.t[f.i:]} »", ligne)
    return v


def _equilibre(txt: str) -> int:
    """Crochets et accolades ouverts moins fermés, hors chaînes entre guillemets."""
    n = 0
    etats = _etats_guillemets(txt)
    for i, c in enumerate(txt):
        s, d = etats[i]
        if not s and not d and c in "[]{}":
            # un guillemet ouvrant sur ce caractère ne compte pas ; « [ » / « { » hors chaîne seulement
            n += (c in "[{") - (c in "]}")
    return n


def _valeur_ligne(txt: str, ligne: int):
    t = txt.strip()
    if t.startswith(("{", "[")):
        return _flux(t, ligne)
    return scalaire(t, ligne)


# ------------------------------------------------------------------------------------------------------ blocs
def _lignes(texte: str, fichier: str | None):
    """(numéro, indentation, contenu) des lignes utiles ; collections en ligne multi-lignes jointes."""
    brutes = texte.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sortie, i = [], 0
    while i < len(brutes):
        l = brutes[i]
        if "\t" in l[:len(l) - len(l.lstrip())]:
            raise ErreurYaml("tabulation dans l'indentation", i + 1, fichier)
        c = _sans_commentaire(l)
        if c.strip() in ("---", "...") and c == c.strip():
            raise ErreurYaml("documents multiples non pris en charge", i + 1, fichier)
        if c.strip() == "":
            i += 1
            continue
        num, ind = i + 1, len(c) - len(c.lstrip(" "))
        contenu = c.strip()
        while _equilibre(contenu) > 0:
            i += 1
            if i >= len(brutes):
                raise ErreurYaml("collection en ligne non fermée", num, fichier)
            contenu += " " + _sans_commentaire(brutes[i]).strip()
        sortie.append((num, ind, contenu))
        i += 1
    return sortie


def _cle_valeur(contenu: str, num: int):
    """('cle', 'reste') si la ligne est « cle: reste » (hors collection en ligne), sinon None."""
    if contenu.startswith(("{", "[", "'", '"')):
        return None
    m = re.match(r"^([^\s:#\[\]{},][^:#\[\]{},]*?)\s*:(\s+(.*))?$", contenu)
    if not m:
        return None
    return m.group(1).strip(), (m.group(3) or "").strip()


def _bloc(lignes, k: int, ind: int, fichier):
    """Lit le bloc qui commence à lignes[k] (indentation ind). Retourne (valeur, k suivant)."""
    num, i0, contenu = lignes[k]
    if contenu.startswith("- ") or contenu == "-":
        seq = []
        while k < len(lignes) and lignes[k][1] == ind and (lignes[k][2].startswith("- ") or lignes[k][2] == "-"):
            num, _, contenu = lignes[k]
            reste = contenu[1:].strip()
            if reste == "":
                if k + 1 < len(lignes) and lignes[k + 1][1] > ind:
                    v, k = _bloc(lignes, k + 1, lignes[k + 1][1], fichier)
                else:
                    v, k = None, k + 1
                seq.append(v)
                continue
            cv = _cle_valeur(reste, num)
            if cv is not None:
                # mapping dans la séquence : « - cle: valeur » puis clés alignées sur la première
                ind_m = ind + (len(contenu) - len(reste))
                faux = [(num, ind_m, reste)] + lignes[k + 1:]
                v, j = _bloc(faux, 0, ind_m, fichier)
                k = k + j
                seq.append(v)
                continue
            seq.append(_valeur_ligne(reste, num))
            k += 1
        if k < len(lignes) and lignes[k][1] > ind:
            raise ErreurYaml("indentation inattendue", lignes[k][0], fichier)
        return seq, k
    d = {}
    while k < len(lignes) and lignes[k][1] == ind:
        num, _, contenu = lignes[k]
        cv = _cle_valeur(contenu, num)
        if cv is None:
            raise ErreurYaml(f"« cle: valeur » attendu, lu « {contenu} »", num, fichier)
        cle, reste = cv
        if cle in d:
            raise ErreurYaml(f"clé en double : {cle}", num, fichier)
        cle_v = scalaire(cle, num)
        if reste == "":
            if k + 1 < len(lignes) and (lignes[k + 1][1] > ind or
                                         (lignes[k + 1][1] == ind and lignes[k + 1][2].startswith("- "))):
                v, k = _bloc(lignes, k + 1, lignes[k + 1][1], fichier)
            else:
                v, k = None, k + 1
        else:
            v, k = _valeur_ligne(reste, num), k + 1
        d[cle_v] = v
    if k < len(lignes) and lignes[k][1] > ind:
        raise ErreurYaml("indentation inattendue", lignes[k][0], fichier)
    return d, k


def charger_texte(texte: str, fichier: str | None = None):
    lignes = _lignes(texte, fichier)
    if not lignes:
        return None
    if lignes[0][1] != 0:
        raise ErreurYaml("le document doit commencer en colonne 0", lignes[0][0], fichier)
    v, k = _bloc(lignes, 0, 0, fichier)
    if k != len(lignes):
        raise ErreurYaml("contenu après la fin du document", lignes[k][0], fichier)
    return v


def charger(chemin) -> object:
    p = Path(chemin)
    return charger_texte(p.read_bytes().decode("utf-8"), str(p.name))
