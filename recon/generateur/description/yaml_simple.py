# -*- coding: utf-8 -*-
"""Lecteur YAML minimal, sans dépendance : le compilateur tourne aussi sous le Python de Houdini, sans PyYAML. PyYAML
6.0.3 est installé pour le Python du système (site-packages de l'utilisateur) : tests/tester_descriptions.py s'en sert
comme contrôle croisé (test Y1). Sur les 30 descriptions du dépôt, les deux lecteurs ne diffèrent que sur deux points,
ramenés au même texte par le compilateur : le saut de ligne final des blocs « | » et « > » (yaml_simple ne le garde
pas) et les dates nues AAAA-MM-JJ (chaîne pour yaml_simple, datetime.date pour PyYAML ; meta.date = str()).

Sous-ensemble lu, suffisant pour le format de description (FORMAT_DESCRIPTION.md) :
- commentaires `# …` (en début de ligne ou après une espace, hors guillemets) ;
- dictionnaires en blocs (`clé: valeur`, indentation par espaces, jamais de tabulation) ;
- listes en blocs (`- élément`, `- clé: valeur` qui ouvre un dictionnaire) ;
- listes et dictionnaires en ligne : `[a, b, [1, 2]]`, `{a: 1, b: x}` (la virgule y sépare les éléments :
  écrire les décimales avec un point dans ces formes, `[2.5, 3]`) ;
- scalaires : chaînes nues ou entre guillemets ('…' ou "…"), nombres (point décimal), `true` / `false`,
  `null` / `~` ; une chaîne nue comme `3,20` reste une chaîne (le compilateur lit la virgule décimale) ;
- blocs de texte `|` (lignes conservées) et `>` (lignes jointes).
Toute construction hors de ce sous-ensemble (ancres, balises, clés complexes) lève ErreurYaml avec le numéro de
ligne. Les clés sont gardées telles quelles ; le compilateur les normalise (accents, espaces).
"""
from __future__ import annotations

import re


class ErreurYaml(ValueError):
    pass


NOMBRE = re.compile(r"^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$")


def scalaire(txt: str):
    s = txt.strip()
    if s == "" or s in ("~", "null", "Null", "NULL"):
        return None
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        corps = s[1:-1]
        if s[0] == "'":
            return corps.replace("''", "'")
        return corps.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if NOMBRE.match(s):
        return int(s) if re.match(r"^[-+]?\d+$", s) else float(s)
    return s


def _sans_commentaire(ligne: str) -> str:
    q = None
    for i, c in enumerate(ligne):
        if q:
            if c == q:
                q = None
        elif c in "'\"" and (i == 0 or ligne[i - 1] in " :[{,-"):
            q = c
        elif c == "#" and (i == 0 or ligne[i - 1] in " \t"):
            return ligne[:i].rstrip()
    return ligne.rstrip()


def _cle_valeur(txt: str):
    """Découpe « clé: valeur » (le « : » suivi d'une espace ou en fin) hors guillemets et crochets ; None sinon."""
    q, prof = None, 0
    for i, c in enumerate(txt):
        if q:
            if c == q:
                q = None
            continue
        if c in "'\"" and (i == 0 or txt[i - 1] in " :[{,"):
            q = c
        elif c in "[{":
            prof += 1
        elif c in "]}":
            prof -= 1
        elif c == ":" and prof == 0 and (i + 1 == len(txt) or txt[i + 1] == " "):
            cle = txt[:i].strip()
            if cle.startswith(("'", '"')):
                cle = scalaire(cle)
            return cle, txt[i + 1:].strip()
    return None


def _en_ligne(txt: str, num: int):
    """Liste ou dictionnaire en ligne (récursif)."""
    pos = [0]

    def blanc():
        while pos[0] < len(txt) and txt[pos[0]] == " ":
            pos[0] += 1

    def valeur():
        blanc()
        if pos[0] >= len(txt):
            raise ErreurYaml(f"ligne {num} : forme en ligne incomplète")
        c = txt[pos[0]]
        if c == "[":
            pos[0] += 1
            out = []
            blanc()
            if txt[pos[0]] == "]":
                pos[0] += 1
                return out
            while True:
                out.append(valeur())
                blanc()
                c = txt[pos[0]] if pos[0] < len(txt) else ""
                pos[0] += 1
                if c == "]":
                    return out
                if c != ",":
                    raise ErreurYaml(f"ligne {num} : « , » ou « ] » attendu dans {txt!r}")
        if c == "{":
            pos[0] += 1
            out = {}
            blanc()
            if txt[pos[0]] == "}":
                pos[0] += 1
                return out
            while True:
                blanc()
                deb = pos[0]
                q = None
                while pos[0] < len(txt):
                    ch = txt[pos[0]]
                    if q:
                        if ch == q:
                            q = None
                    elif ch in "'\"" and pos[0] == deb:
                        q = ch
                    elif ch == ":":
                        break
                    pos[0] += 1
                cle = scalaire(txt[deb:pos[0]])
                pos[0] += 1
                out[str(cle)] = valeur()
                blanc()
                c = txt[pos[0]] if pos[0] < len(txt) else ""
                pos[0] += 1
                if c == "}":
                    return out
                if c != ",":
                    raise ErreurYaml(f"ligne {num} : « , » ou « }} » attendu dans {txt!r}")
        # scalaire jusqu'à , ] } (un guillemet n'ouvre une chaîne qu'en tête du scalaire)
        deb, q, prof = pos[0], None, 0
        while pos[0] < len(txt):
            ch = txt[pos[0]]
            if q:
                if ch == q:
                    q = None
            elif ch in "'\"" and pos[0] == deb:
                q = ch
            elif ch in ",]}" and prof == 0:
                break
            pos[0] += 1
        return scalaire(txt[deb:pos[0]])

    v = valeur()
    blanc()
    if pos[0] != len(txt):
        raise ErreurYaml(f"ligne {num} : texte en trop après la forme en ligne : {txt[pos[0]:]!r}")
    return v


def _valeur_simple(txt: str, num: int):
    if txt.startswith(("[", "{")):
        return _en_ligne(txt, num)
    if txt.startswith(("&", "*", "!")):
        raise ErreurYaml(f"ligne {num} : ancres, alias et balises YAML non pris en charge")
    return scalaire(txt)


def charger(texte: str):
    """Texte YAML (sous-ensemble) → objets Python."""
    lignes = []
    brutes = texte.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(brutes):
        l = brutes[i]
        if "\t" in l[:len(l) - len(l.lstrip())]:
            raise ErreurYaml(f"ligne {i + 1} : tabulation dans l'indentation")
        c = _sans_commentaire(l)
        if c.strip() and c.strip() not in ("---", "..."):
            lignes.append((len(c) - len(c.lstrip(" ")), c.strip(), i + 1, l))
        i += 1
    # blocs de texte | et > : on relit les lignes brutes
    pos = [0]

    def bloc_texte(ind_parent: int, style: str, num: int):
        # lignes suivantes plus indentées que le parent (brutes, commentaires compris)
        out, ind = [], None
        j = num  # index 0-based de la ligne suivante dans brutes
        while j < len(brutes):
            l = brutes[j]
            if l.strip() == "":
                out.append("")
                j += 1
                continue
            r = len(l) - len(l.lstrip(" "))
            if r <= ind_parent:
                break
            ind = r if ind is None else min(ind, r)
            out.append(l)
            j += 1
        while out and out[-1] == "":
            out.pop()
        txt = [l[ind:] if l else "" for l in out]
        # avancer pos au-delà des lignes consommées
        while pos[0] < len(lignes) and lignes[pos[0]][2] <= j:
            pos[0] += 1
        return "\n".join(txt) if style == "|" else " ".join(t for t in txt if t)

    def noeud(ind: int):
        if pos[0] >= len(lignes):
            return None
        r, txt, num, _ = lignes[pos[0]]
        if r < ind:
            return None
        if txt.startswith("- ") or txt == "-":
            return liste(r)
        return dico(r)

    def liste(ind: int):
        out = []
        while pos[0] < len(lignes):
            r, txt, num, _ = lignes[pos[0]]
            if r != ind or not (txt.startswith("- ") or txt == "-"):
                if r > ind:
                    raise ErreurYaml(f"ligne {num} : indentation inattendue")
                break
            reste = txt[1:].strip()
            pos[0] += 1
            if not reste:
                out.append(noeud(ind + 1))
                continue
            kv = _cle_valeur(reste) if not reste.startswith(("[", "{", "'", '"')) else None
            if kv is None:
                out.append(_valeur_simple(reste, num))
                continue
            # « - clé: valeur » : dictionnaire dont les clés suivantes sont alignées sur « clé »
            ind_d = ind + (len(txt) - len(reste))
            d = {}
            _ajouter(d, kv, ind_d, num)
            while pos[0] < len(lignes):
                r2, t2, n2, _ = lignes[pos[0]]
                if r2 != ind_d or t2.startswith("- "):
                    if r2 > ind_d:
                        raise ErreurYaml(f"ligne {n2} : indentation inattendue")
                    break
                kv2 = _cle_valeur(t2)
                if kv2 is None:
                    raise ErreurYaml(f"ligne {n2} : « clé: valeur » attendu")
                pos[0] += 1
                _ajouter(d, kv2, ind_d, n2)
            out.append(d)
        return out

    def _ajouter(d: dict, kv, ind: int, num: int):
        cle, val = kv
        if cle in d:
            raise ErreurYaml(f"ligne {num} : clé en double « {cle} »")
        if val == "":
            d[cle] = noeud(ind + 1) if pos[0] < len(lignes) and lignes[pos[0]][0] > ind else (
                liste(ind) if pos[0] < len(lignes) and lignes[pos[0]][0] == ind and lignes[pos[0]][1].startswith("- ") else None)
        elif val in ("|", ">", "|-", ">-", "|+", ">+"):
            d[cle] = bloc_texte(ind, val[0], num)
        else:
            d[cle] = _valeur_simple(val, num)

    def dico(ind: int):
        d = {}
        while pos[0] < len(lignes):
            r, txt, num, _ = lignes[pos[0]]
            if r != ind:
                if r > ind:
                    raise ErreurYaml(f"ligne {num} : indentation inattendue")
                break
            if txt.startswith("- "):
                break
            kv = _cle_valeur(txt)
            if kv is None:
                raise ErreurYaml(f"ligne {num} : « clé: valeur » attendu, lu {txt!r}")
            pos[0] += 1
            _ajouter(d, kv, ind, num)
        return d

    if not lignes:
        return None
    r0, t0, n0, _ = lignes[0]
    if not (t0.startswith("- ") or _cle_valeur(t0)):
        if len(lignes) == 1:
            return _valeur_simple(t0, n0)
    v = noeud(r0)
    if pos[0] < len(lignes):
        raise ErreurYaml(f"ligne {lignes[pos[0]][2]} : indentation incohérente")
    return v


def lire(chemin) -> object:
    from pathlib import Path
    return charger(Path(chemin).read_text(encoding="utf-8"))
