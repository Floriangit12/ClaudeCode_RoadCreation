# -*- coding: utf-8 -*-
"""Analyse d'un profil en travers écrit en une ligne, de gauche à droite (sens du tronçon) :

    "trottoir 2,0 béton balayé | bordure T2 granit | stationnement 2,0 | voie 3,2 ← | voie 3,2 → | bande cyclable 1,5 | trottoir 2"

Chaque élément séparé par « | » est une BANDE (type, largeur facultative en m, sens facultatif, attributs) ou une
LIMITE entre deux bandes (« bordure … », « ligne … », séparateur ponctuel « potelets », « caniveau CS2 »). Une limite
non écrite est déduite par les règles ; une limite écrite précise la limite déduite (profil de bordure, matériau,
vue, caniveau) ou la remplace (ligne).

Sortie : bandes (dict internes de `commun/profil.py`, encore sans sens résolu pour certaines) et limites (None ou
{"raffiner": True, …}), avec la provenance « description:profil[i] ».
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from commun import prov as P  # noqa: E402
from description import vocabulaire as V  # noqa: E402


class ErreurFormat(ValueError):
    pass


def elements(profil, chemin: str) -> list:
    """Éléments du profil : textes (« trottoir 2,0 »), ou dictionnaires de la forme structurée
    ({bande: voie, sens: avant, largeur: 3.0}, {bordure: T2, vue: 0.14}, {ligne: "T'1", largeur_u: 2})."""
    if isinstance(profil, str):
        return [e.strip() for e in profil.split("|")]
    if isinstance(profil, list):
        out = []
        for x in profil:
            if isinstance(x, dict):
                out.append(x)
            else:
                out += [e.strip() for e in str(x).split("|")]
        return out
    raise ErreurFormat(f"{chemin} : chaîne « a | b | c » ou liste attendue")


_IDS_MATERIAUX = None


def ids_materiaux() -> set:
    """materiau_id du catalogue assets/specs/materiaux_sol.json (lecture seule)."""
    global _IDS_MATERIAUX
    if _IDS_MATERIAUX is None:
        import json
        f = Path(__file__).resolve().parents[3] / "assets" / "specs" / "materiaux_sol.json"
        _IDS_MATERIAUX = set(json.loads(f.read_text(encoding="utf-8"))["materiaux"])
    return _IDS_MATERIAUX


def _texte_dict(x: dict) -> str:
    return "{" + ", ".join(f"{k}: {v}" for k, v in x.items()) + "}"


def analyser_dict(x: dict, chemin: str):
    """Élément structuré → ('bande', bande) | ('limite', limite)."""
    from description.vocabulaire import norm_cle
    d = {norm_cle(k): v for k, v in x.items()}
    if "bande" in d:
        b = analyser_bande(str(d["bande"]).replace("_", " "), chemin)
        b["_texte"] = _texte_dict(x)
        b["prov"]["*"] = P.description(chemin, note=b["_texte"])
        for k, v in d.items():
            if k == "bande" or v is None:
                continue
            if k in ("largeur", "largeur_m"):
                b["largeur"] = V.nombre(v, f"{chemin}.{k}")
                b["prov"]["largeur"] = P.description(chemin + ".largeur")
            elif k == "sens":
                s = V.SENS.get(V.norm(v))
                if s is None:
                    raise ErreurFormat(f"{chemin}.sens : avant, arriere, double, → ou ← attendu")
                b["sens"] = s
            elif k in ("materiau", "materiau_id"):
                if str(v) in ids_materiaux():
                    b["attributs"]["materiau"] = str(v)
                else:
                    cle, n = V.correspondance(V.jetons(v), 0, V.MATERIAUX)
                    if not cle:
                        raise ErreurFormat(f"{chemin}.materiau : « {v} » ni materiau_id de materiaux_sol.json ni matériau connu")
                    b["attributs"]["materiaux"] = b["attributs"].get("materiaux", []) + [cle]
            elif k in ("niveau", "orientation", "position"):
                b["attributs"][k] = V.norm(v).replace(" ", "_")
            elif k in ("bidirectionnelle", "plante", "arbres", "places_marquees", "velos_admis", "permanent"):
                b["attributs"][k] = V.booleen(v, f"{chemin}.{k}")
            elif k == "franchissable":
                b["attributs"][k] = V.norm(v) if not isinstance(v, bool) else ("vl_pl" if v else "non")
            elif k in ("vue", "dz", "dz_m"):
                b["attributs"]["dz_m"] = V.nombre(v, f"{chemin}.{k}")
                b["attributs"]["prov_dz"] = P.description(f"{chemin}.{k}")
            elif k in ("devers", "devers_pct"):
                b["attributs"]["devers_pct"] = V.nombre(v, f"{chemin}.{k}")
                b["prov"]["niveau.devers_pct"] = P.description(f"{chemin}.{k}")
            elif k == "id":
                if not str(v).replace("_", "").isalnum():
                    raise ErreurFormat(f"{chemin}.id : lettres, chiffres et « _ » seulement")
                b["id"] = str(v)
            elif k in ("nom", "note", "commentaire"):
                continue
            else:
                raise ErreurFormat(f"{chemin} : clé de bande inconnue « {k} »")
        return "bande", b
    lim = {"raffiner": True, "prov": P.description(chemin, note=_texte_dict(x))}
    if "bordure" in d:
        bo = {}
        prof = V.norm(d["bordure"])
        if prof not in ("oui", "true", "1"):
            if prof not in V.PROFILS_BORDURE:
                raise ErreurFormat(f"{chemin}.bordure : profil inconnu « {d['bordure']} »")
            bo["profil"] = V.PROFILS_BORDURE[prof]
        for k, v in d.items():
            if k == "bordure" or v is None:
                continue
            if k in ("vue", "vue_m"):
                bo["vue_m"] = V.nombre(v, f"{chemin}.{k}")
            elif k == "caniveau":
                c = V.norm(v)
                if c not in V.CANIVEAUX:
                    raise ErreurFormat(f"{chemin}.caniveau : {', '.join(V.CANIVEAUX.values())}")
                bo["caniveau"] = {"profil": V.CANIVEAUX[c]}
            elif k in ("materiau", "materiau_id"):
                if str(v) in ids_materiaux():
                    bo["materiau_id"] = str(v)
                else:
                    cle, _ = V.correspondance(V.jetons(v), 0, V.MATERIAUX_BORDURE, 2)
                    if not cle:
                        raise ErreurFormat(f"{chemin}.materiau : « {v} » inconnu")
                    bo["materiau_id"] = V.MATERIAUX_BORDURE[cle]
            elif k == "peinte":
                bo["peinte"] = V.booleen(v, f"{chemin}.peinte")
            elif k in ("note", "commentaire"):
                continue
            else:
                raise ErreurFormat(f"{chemin} : clé de bordure inconnue « {k} »")
        lim["bordure"] = bo
        return "limite", lim
    if "ligne" in d:
        txt = "ligne " + str(d["ligne"])
        if d.get("largeur_u") is not None:
            txt += f" {d['largeur_u']}u"
        elif d.get("largeur_m") is not None:
            txt += f" {d['largeur_m']} m"
        if d.get("couleur"):
            txt += f" {d['couleur']}"
        lim["marquages"] = analyser_ligne(V.jetons(txt), chemin)
        return "limite", lim
    if "separateur" in d:
        cle, _ = V.correspondance(V.jetons(d["separateur"]), 0, V.SEPARATEURS)
        if not cle:
            raise ErreurFormat(f"{chemin}.separateur : {', '.join(V.SEPARATEURS)}")
        lim["separateur"] = {"type": V.SEPARATEURS[cle]}
        if d.get("pas") is not None:
            lim["separateur"]["pas_m"] = V.nombre(d["pas"], chemin + ".pas")
        return "limite", lim
    raise ErreurFormat(f"{chemin} : élément structuré sans « bande », « bordure », « ligne » ni « separateur »")


def _est_limite(toks: list[str]) -> bool:
    if not toks:
        return False
    if toks[0] in ("bordure", "bordures", "ligne", "lignes", "caniveau") or toks[:2] in (["sans", "bordure"], ["sans", "ligne"]):
        return True
    cle, _ = V.correspondance(toks, 0, V.SEPARATEURS)
    return cle is not None and not any(V.NOMBRE.match(t) for t in toks)


def analyser_ligne(toks: list[str], chemin: str) -> dict | str:
    """« ligne T3 5u jaune » → marque (sans u_m : complété par le contexte) ; « ligne aucune » → 'aucune'."""
    i, mod, lu, lm, coul = 0, None, None, None, "blanc"
    while i < len(toks):
        t = toks[i]
        if t in ("ligne", "lignes"):
            i += 1
            continue
        cle, n = V.correspondance(toks, i, V.MODULATIONS, 2)
        if cle:
            mod = V.MODULATIONS[cle]
            i += n
            continue
        if t.endswith("u") and V.NOMBRE.match(t[:-1]):
            lu = float(t[:-1])
            i += 1
            continue
        if V.NOMBRE.match(t):
            u = toks[i + 1] if i + 1 < len(toks) else "m"
            lm = float(t) / (100.0 if u == "cm" else 1.0)
            i += 2 if u in ("cm", "m") else 1
            continue
        if t in V.COULEURS:
            coul = V.COULEURS[t]
            i += 1
            continue
        if t in V.MOTS_VIDES:
            i += 1
            continue
        raise ErreurFormat(f"{chemin} : mot inconnu « {t} » dans une ligne (modulations : T1, T'1, T2, T'2, T3, T'3, "
                           "T4, continue, double continue, aucune ; largeur en u ou en cm)")
    if mod is None:
        raise ErreurFormat(f"{chemin} : modulation de ligne manquante")
    if mod == "aucune":
        return "aucune"
    m = {"modulation": mod}
    if lm is not None:
        m["largeur_m"] = lm
    else:
        m["largeur_u"] = lu if lu is not None else 2.0
    m["couleur"] = coul
    return m


def analyser_limite(texte: str, chemin: str) -> dict:
    toks = V.jetons(texte)
    lim = {"raffiner": True, "prov": P.description(chemin, note=texte)}
    if toks[:2] in (["sans", "bordure"], ["sans", "bordures"]):
        lim["sans_bordure"] = True
        return lim
    if toks[0] in ("ligne", "lignes"):
        lim["marquages"] = analyser_ligne(toks, chemin)
        return lim
    if toks[:2] == ["sans", "ligne"]:
        lim["marquages"] = "aucune"
        return lim
    cle, n = V.correspondance(toks, 0, V.SEPARATEURS)
    if cle:
        lim["separateur"] = {"type": V.SEPARATEURS[cle]}
        reste = toks[n:]
        for j, t in enumerate(reste):
            if V.NOMBRE.match(t):
                lim["separateur"]["pas_m"] = float(t)
        return lim
    bo, i = {}, 0
    while i < len(toks):
        t = toks[i]
        if t in ("bordure", "bordures"):
            i += 1
            continue
        if t == "caniveau" and i + 1 < len(toks) and toks[i + 1] in V.CANIVEAUX:
            bo["caniveau"] = {"profil": V.CANIVEAUX[toks[i + 1]]}
            i += 2
            continue
        if t == "vue" and i + 1 < len(toks):
            u = toks[i + 2] if i + 2 < len(toks) else "m"
            bo["vue_m"] = V.nombre(toks[i + 1] + (" cm" if u == "cm" else ""), chemin)
            i += 3 if u in ("cm", "m") else 2
            continue
        if t in ("peinte", "peinte en blanc"):
            bo["peinte"] = True
            i += 1
            continue
        cle, n = V.correspondance(toks, i, V.MATERIAUX_BORDURE, 2)
        if cle:
            bo["materiau_id"] = V.MATERIAUX_BORDURE[cle]
            i += n
            continue
        if t in ("paves",) and i + 1 < len(toks) and toks[i + 1] == "granit":
            bo["profil"] = "PAVES_GRANIT"
            i += 2
            continue
        if t in V.PROFILS_BORDURE:
            bo["profil"] = V.PROFILS_BORDURE[t]
            i += 1
            continue
        if t in V.MOTS_VIDES:
            i += 1
            continue
        raise ErreurFormat(f"{chemin} : mot inconnu « {t} » dans une bordure (profils T1, T2, T3, A1, A2, I1, I2, "
                           "P1-P3, quai ; matériau béton, béton clair, granit, calcaire ; « vue 0,12 » ; "
                           "« caniveau CS2 » ; « peinte »)")
    lim["bordure"] = bo
    return lim


def analyser_bande(texte: str, chemin: str) -> dict:
    toks = V.jetons(texte)
    cle, n = V.correspondance(toks, 0, V.BANDES)
    if not cle:
        raise ErreurFormat(f"{chemin} : type de bande inconnu au début de « {texte} » (trottoir, voie, voie bus, "
                           "bande cyclable, piste cyclable, stationnement, terre-plein, bande plantée, séparateur, "
                           "tampon, zone hachurée, accotement, berme, bande dérasée, quai, voie verte…)")
    typ, sous, attrs0 = V.BANDES[cle]
    b = {"type": typ, "sous_type": sous, "sens": None, "largeur": None, "attributs": dict(attrs0), "_texte": texte,
         "prov": {"*": P.description(chemin, note=texte)}}
    i = n
    materiaux = []
    while i < len(toks):
        t = toks[i]
        if V.NOMBRE.match(t):
            if b["largeur"] is not None:
                raise ErreurFormat(f"{chemin} : deux largeurs dans « {texte} »")
            u = toks[i + 1] if i + 1 < len(toks) else "m"
            b["largeur"] = float(t) / (100.0 if u == "cm" else 1.0)
            b["prov"]["largeur"] = P.description(chemin + ".largeur")
            i += 2 if u in ("cm", "m") else 1
            continue
        if t in V.SENS:
            b["sens"] = V.SENS[t]
            i += 1
            continue
        if t == "devers" and i + 1 < len(toks) and V.NOMBRE.match(toks[i + 1]):
            # dévers dit (%, + : descend vers la droite, convention du modèle) : remplace le dévers déduit (DEF-006) ;
            # sert à raccorder une liaison revêtue à ses voisines d'une autre section (correction après second contrôle)
            b["attributs"]["devers_pct"] = float(toks[i + 1])
            b["prov"]["niveau.devers_pct"] = P.description(chemin + ".devers")
            i += 3 if i + 2 < len(toks) and toks[i + 2] == "%" else 2
            continue
        cle, n = V.correspondance(toks, i, V.ATTRIBUTS)
        cle_m, n_m = V.correspondance(toks, i, V.MATERIAUX)
        if cle_m and n_m >= n:
            materiaux.append(cle_m)
            i += n_m
            continue
        if cle:
            k, v = V.ATTRIBUTS[cle]
            b["attributs"][k] = v
            i += n
            continue
        if t in V.USURE_ENROBE:
            b["attributs"]["usure"] = t
            i += 1
            continue
        if t in V.MOTS_VIDES:
            i += 1
            continue
        raise ErreurFormat(f"{chemin} : mot inconnu « {t} » dans « {texte} »")
    b["attributs"]["materiaux"] = materiaux
    if b["largeur"] is not None and not (0 < b["largeur"] <= 30):
        raise ErreurFormat(f"{chemin} : largeur {b['largeur']} m invraisemblable")
    return b


def analyser(profil, chemin: str = "profil"):
    """(bandes, limites) ; len(limites) == len(bandes) + 1."""
    els = elements(profil, chemin)
    bandes, limites = [], [None]
    for k, e in enumerate(els):
        c = f"{chemin}[{k}]"
        if isinstance(e, dict):
            genre, x = analyser_dict(e, c)
            if genre == "bande":
                bandes.append(x)
                limites.append(None)
            elif limites[-1] is not None:
                limites[-1] = fusion_limites(limites[-1], x, c)
            else:
                limites[-1] = x
            continue
        if not e:
            raise ErreurFormat(f"{c} : élément vide (deux « | » de suite ?)")
        toks = V.jetons(e)
        if _est_limite(toks):
            lim = analyser_limite(e, c)
            if limites[-1] is not None:
                limites[-1] = fusion_limites(limites[-1], lim, c)
            else:
                limites[-1] = lim
        else:
            bandes.append(analyser_bande(e, c))
            limites.append(None)
    if not bandes:
        raise ErreurFormat(f"{chemin} : aucune bande")
    return bandes, limites


def fusion_limites(a: dict, b: dict, chemin: str) -> dict:
    """Deux éléments de limite de suite (« bordure T2 | ligne T2 3u ») : réunis."""
    out = dict(a)
    for k, v in b.items():
        if k == "prov":
            continue
        if k in out and k != "raffiner":
            raise ErreurFormat(f"{chemin} : « {k} » dit deux fois pour la même limite")
        out[k] = v
    out["prov"] = P.description(chemin, note=f"{a['prov'].get('note', '')} + {b['prov'].get('note', '')}")
    return out
