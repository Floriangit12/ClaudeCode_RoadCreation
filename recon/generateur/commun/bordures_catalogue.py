# -*- coding: utf-8 -*-
"""Catalogue des bordures et caniveaux du générateur (lot « bordures », 17/10/2026).

Un seul endroit pour tout ce que le générateur sait des types de bordures NF et de leurs pièces :

  - TABLE DES PROFILS (contours u, v en mètres ; u = 0 sur la face vue, v = 0 sous le bloc) : celle de pj::bordure
    (assets/specs/bordures.json + bordures_elements.json, autre équipe, lecture seule ; inchangée pour les profils
    qu'elle contient), complétée des profils du catalogue route_fr qui lui manquaient, avec leurs cotes des règles
    RF-AS-profil_* de assets/specs/route/regles_route_fr.json (contour_uv_m) : T4, I3, I4, P4, CS4, GR_T1, GR_T2, GR_P1,
    T2_basse, T2_surbaissee, T3_basse, T3_surbaissee, P1_basse, ACCESBUS (construire_table_etendue) ;
  - VUES NOMINALES par profil (bordures.json vue_courante, bordures_elements.json profils_complementaires,
    RF-AS-profil_*.vue_nominale_m) et choix d'un profil par la vue (profil_par_vue) ;
  - PIÈCES D'ABAISSÉ (bateau) par profil courant (PIECES_ABAISSE, même base que le profil courant : la nappe du
    trottoir est coupée à l'arête arrière u = base de la file) ;
  - RÈGLES PAR DÉFAUT SELON LE CONTEXTE (CONTEXTES : trottoir, îlot, refuge, terre-plein, couronne de giratoire, îlot
    central, piste, accès charretière, quai, bordurette, accotement, autoroute) ;
  - MESHES DU CATALOGUE route_fr (assets/specs/route/catalogue_assets_route.json, 64 bordures et caniveaux) : asset
    d'un élément posé (asset_element), pour le placement dans Unreal ;
  - EXTENSION DE LA DESCRIPTION (installer_description) : mots de profil (vocabulaire), règle par défaut des sauts de
    niveau sans règle (profil « autre ») et énumérations du schéma modele_voie/0.1, ajoutées en mémoire.

Rien n'est inventé : chaque cote, vue et choix cite une règle RF-* / DEF-* / ARB-* ; les choix sans règle sont marqués
[G] (moyen du générateur) et listés dans le rapport du lot (validation/RAPPORT_bordures.md).

Utilisation hors Houdini (compilation d'une description avec les types étendus, Python du système) :
    python recon/generateur/commun/bordures_catalogue.py --compiler DESCRIPTION.yaml [--sortie DOSSIER]
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent                     # recon/generateur/commun
GEN = ICI.parent                                         # recon/generateur
DEPOT = GEN.parents[1]
SPECS = DEPOT / "assets" / "specs"
REGLES = SPECS / "route" / "regles_route_fr.json"
CATALOGUE = SPECS / "route" / "catalogue_assets_route.json"
PJ_BORDURE = DEPOT / "recon" / "pcg" / "houdini" / "hda" / "pj_bordure"

VERSION = "bordures_catalogue/1.0"

# profils ajoutés à la table de pj::bordure (cotes : RF-AS-profil_<nom>.valeurs.contour_uv_m) et leur famille
AJOUTS = {
    "T4": "bordure", "I3": "bordure", "I4": "bordure", "P4": "bordure", "GR_T1": "bordure", "GR_T2": "bordure",
    "GR_P1": "bordure", "T2_basse": "bordure", "T2_surbaissee": "bordure", "T3_basse": "bordure",
    "T3_surbaissee": "bordure", "P1_basse": "bordure", "ACCESBUS": "bordure", "CS4": "caniveau",
    # granit sans règle RF-AS-profil_* : contour et vue nominale du mesh du catalogue route_fr (bordure_<nom>_L100)
    "GR_A1": "bordure", "GR_A2": "bordure", "GR_P3": "bordure",
}
# chanfrein de l'arête arrière haute ajouté quand le contour y a un coin vif (comme profils.CHANFREIN_ARRIERE pour la
# même famille : T 5 x 5 mm, P 3 x 3 mm ; bordures_elements.json aretes) ; granit scié : arête vive
CHANFREIN_AJOUTS = {"T2_basse": 0.005, "T2_surbaissee": 0.005, "T3_basse": 0.005, "T3_surbaissee": 0.005,
                    "P1_basse": 0.003, "P4": 0.003}
# famille NF de chaque profil (RF-AS-liste_profils_nf ; bordures.json famille)
FAMILLE_NF = {
    "T1": "T", "T2": "T", "T3": "T", "T4": "T", "T2_bateau": "T", "T2_basse": "T", "T2_surbaissee": "T",
    "T3_basse": "T", "T3_surbaissee": "T", "GR_T1": "T", "GR_T2": "T", "TU": "T",
    "A1": "A", "A2": "A", "AC1": "A", "GR_A1": "A", "GR_A2": "A", "GR_P3": "P", "I1": "I", "I2": "I", "I3": "I", "I4": "I", "IL": "I",
    "P1": "P", "P2": "P", "P3": "P", "P4": "P", "P1_basse": "P", "GR_P1": "P",
    "CS1": "CS", "CS2": "CS", "CS3": "CS", "CS4": "CS", "CC1": "CC", "CC2": "CC",
    "QUAI_BUS": "quai", "ACCESBUS": "quai", "PAVES_GRANIT": "pavés", "MURET_TALUS": "muret",
}
# matériau par défaut d'un profil (bordures_elements.json materiaux ; RF-AS-regle_materiaux_elements : élément unitaire
# en matière, granit_gris_flamme pour le granit)
MATERIAU_PROFIL = {"GR_T1": "granit_bordure", "GR_T2": "granit_bordure", "GR_P1": "granit_bordure",
                   "GR_A1": "granit_bordure", "GR_A2": "granit_bordure", "GR_P3": "granit_bordure",
                   "PAVES_GRANIT": "granit_bordure"}

# pièce d'abaissé (bateau, vue 0,02 m : RF-MA-ABA-001, RF-MA-ABA-002) par profil courant, même base que le profil
# courant. Un profil absent garde son propre contour, posé abaissé (« pose abaissée », [G] : aucun élément bateau de
# ce type au catalogue) ; la partie vue est alors le haut chanfreiné ou arrondi de sa face (ressaut ≤ 2 cm à bord
# arrondi ou chanfreiné, RF-MA-ABA-002).
PIECES_ABAISSE = {
    "T2": ("T2_bateau", "bordures_elements.json abaisses.traversee (T2_bateau) ; RF-MA-ABA-001"),
    "T3": ("T3_surbaissee", "RF-AS-raccord_bateau (T3 / T3 surbaissée) ; RF-AS-profil_T3_surbaissee"),
    "T2_basse": ("T2_surbaissee", "RF-AS-raccord_bateau (T2 / T2 surbaissée, T2 / T2 basse) ; RF-AS-profil_T2_surbaissee"),
    "T3_basse": ("T3_surbaissee", "RF-AS-raccord_bateau ; RF-AS-profil_T3_surbaissee (même base 0,17)"),
    "A2": ("A2", "bordures_elements.json abaisses.entree_charretiere (« A2 si la bordure courante est A2 »)"),
}
# raccords du catalogue (rampant d'abaissé en un élément de 1,00 m : RF-AS-raccord_bateau)
RACCORDS = {("T2", "T2_bateau"): "T2_T2_surbaissee", ("T2", "T2_surbaissee"): "T2_T2_surbaissee",
            ("T2", "T2_basse"): "T2_T2_basse", ("T3", "T3_surbaissee"): "T3_T3_surbaissee"}
# pièce du catalogue équivalente à un profil sans mesh propre (même rôle, même base ± 1 mm)
EQUIVALENTS_CATALOGUE = {"T2_bateau": "T2_surbaissee"}

# règles par défaut selon le contexte (profil, vue en m, règles citées, note) ; [G] = moyen du générateur
CONTEXTES = {
    "trottoir": ("T2", 0.14, ("RF-OSM-NIV-010", "DEF-005", "ARB-18"),
                 "bordure de trottoir contre la chaussée : T2, vue 0,14 m"),
    "ilot": ("I2", 0.11, ("DEF-005", "ARB-18", "RF-AS-liste_profils_nf", "RF-AS-profil_I2"),
             "îlot directionnel bordé : I2 encastrée (« I : îlots directionnels »), vue 0,11 m"),
    "ilot_franchissable": ("I1", 0.06, ("RF-GV-CAR-016", "RF-MQ-ILOT-01", "RF-AS-profil_I1"),
                           "îlot central de route principale ou îlot franchissable : bordure basse franchissable I1, vue 0,06 m"),
    "refuge": ("T2", 0.12, ("RF-MA-REF-003", "DEF-005", "RF-MQ-ILOT-01"),
               "refuge pour piétons : bordure haute (protection des piétons), vue ≥ 0,12 m"),
    "terre_plein": ("I2", 0.11, ("DEF-005", "RF-AS-profil_I2"), "ceinture de terre-plein : I2, vue nominale 0,11 m"),
    "terre_plein_vru": ("T2", 0.14, ("RF-GV-TPC-002", "RF-OSM-NIV-010"),
                        "TPC de voie rapide urbaine de type U à bordures T2 sans marquage"),
    "couronne_giratoire": ("T2_surbaissee", 0.03, ("RF-GV-GIR-006", "ARB-18", "RF-AS-profil_T2_surbaissee"),
                           "bord de la couronne franchissable côté anneau : vue ≤ 0,03 m (A2, franchissable mais de vue "
                           "nominale 0,04-0,10, ne descend pas à 0,03) ; T2 surbaissée, élément franchissable par les "
                           "véhicules, vue nominale 0-0,04"),
    "ilot_central_giratoire": ("I1", 0.06, ("RF-GV-GIR-006", "RF-AS-profil_I1"),
                               "bord de l'îlot central infranchissable (derrière la couronne) : vue ≤ 0,06 m, I1"),
    "piste_trottoir": ("A2", 0.05, ("RF-MA-SEP-004", "RF-OBS-CYC-02", "RF-AS-profil_A2"),
                       "piste plus basse que le trottoir : bordure chanfreinée basse, ≈ 0,05 m côté trottoir"),
    "piste_chaussee": ("T2", 0.13, ("RF-OBS-CYC-02", "RF-OSM-NIV-010"),
                       "piste surélevée contre la chaussée : bordure haute, ≈ 0,13 m"),
    "piste_intermediaire": ("A2", 0.04, ("RF-MA-SEP-005", "RF-OSM-NIV-012", "RF-AS-profil_A2"),
                            "piste à niveau intermédiaire (0,02-0,04 m) contre la chaussée : bordure franchissable "
                            "A2 à la borne basse de sa vue nominale [G]"),
    "charretiere": ("T2_bateau", 0.03, ("RF-MA-TRO-015", "RF-MA-TRO-016"),
                    "entrée charretière dans une bordure T2 : pièce d'abaissé T2_bateau (A2 dans une A2 : PIECES_ABAISSE), "
                    "vue 0,03 (bordures_elements.json abaisses.entree_charretiere : 0,02-0,04, défaut 0,03) sous le "
                    "maximum de 0,05 (RF-MA-TRO-015), sans BEV (RF-MA-TRO-016)"),
    "quai_bus": ("QUAI_BUS", 0.21, ("DEF-032",), "bordure de quai bus"),
    "quai_bus_accessible": ("ACCESBUS", 0.21, ("RF-MA-BUS-010", "RF-AS-profil_ACCESBUS"),
                            "bordure de quai à profil guide-roues (accostage), vue 0,18-0,21 m"),
    "bordurette": ("P1", 0.03, ("RF-AS-liste_profils_nf", "RF-AS-profil_P1"),
                   "bordurette d'allée, de parc ou d'espace vert (« P : parcs de stationnement, allées »), vue 0-0,06 m"),
    "accotement": ("A1", 0.09, ("RF-AS-liste_profils_nf", "RF-AS-profil_A1"),
                   "accotement de route bordé : bordure franchissable A (« accotements de routes, franchissables »)"),
    "granit": ("GR_T2", 0.14, ("RF-AS-profil_GR_T2", "RF-AS-regle_materiaux_elements"),
               "bordure de trottoir en granit (profil scié GR_T2, matériau granit_gris_flamme)"),
    "autoroute": (None, None, ("RF-GV-PON-005", "RF-OSM-MRQ-022"),
                  "autoroute : pas de bordure (accotements, rive continue / T4 3u ; bordure de 5 cm seule à proscrire)"),
}


# ---------------------------------------------------------------------------------------------------- données
@lru_cache(maxsize=1)
def _regles() -> dict:
    return {r["id"]: r for r in json.loads(REGLES.read_text(encoding="utf-8"))["regles"]}


@lru_cache(maxsize=1)
def _catalogue() -> dict:
    return {a["id"]: a for a in json.loads(CATALOGUE.read_text(encoding="utf-8"))["assets"]
            if a.get("famille") in ("bordures", "caniveaux")}


def _sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def profil_rf(nom: str) -> dict | None:
    """Valeurs de la règle RF-AS-profil_<nom> (base_m, H_m, vue_nominale_m, contour_uv_m) ; à défaut (granits GR_A1,
    GR_A2, GR_P3), celles du mesh droit du catalogue route_fr (params.contour_a, dimensions, vue_nominale_m) ; ou None."""
    r = _regles().get(f"RF-AS-profil_{nom}")
    if r:
        return dict(r["valeurs"])
    a = _catalogue().get(f"bordure_{nom}_L100")
    if a:
        return {"base_m": a["dimensions"]["base_m"], "H_m": a["dimensions"]["H_m"], "vue_nominale_m": a.get("vue_nominale_m"),
                "contour_uv_m": contour_catalogue(f"bordure_{nom}_L100"),
                "source": f"catalogue_assets_route.json : bordure_{nom}_L100"}
    return None


def _nettoyer(contour, eps=1e-4):
    """Sommets consécutifs à moins de 0,1 mm fusionnés (contours relevés : faces dégénérées sinon) ; −0,0 → 0,0."""
    out = []
    for u, v in contour:
        u, v = float(u) + 0.0, float(v) + 0.0
        if out and abs(u - out[-1][0]) < eps and abs(v - out[-1][1]) < eps:
            continue
        out.append([round(u, 6), round(v, 6)])
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def construire_table_etendue(dossier_specs=SPECS):
    """Table {profil: {contour, base, H, famille, h_fil_eau?}} de pj::bordure (profils.construire_table, inchangée),
    complétée des profils AJOUTS (règles RF-AS-profil_*) ; renvoie (table, source) comme profils.construire_table."""
    sys.path.insert(0, str(PJ_BORDURE))
    import profils as PR  # noqa: E402  (recon/pcg/houdini/hda/pj_bordure/profils.py, lecture seule)
    table, src = _table_pj(PR, Path(dossier_specs))
    for nom, fam in sorted(AJOUTS.items()):
        if nom in table:
            continue
        v = profil_rf(nom)
        c = _nettoyer(v["contour_uv_m"])
        base = max(p[0] for p in c)
        H = max(p[1] for p in c)
        ent = {"base": round(base, 6), "H": round(H, 6), "famille": fam}
        if fam == "bordure":
            c = PR._chanfrein_arriere(c, base, H, CHANFREIN_AJOUTS.get(nom, 0.0))
        else:
            ent["h_fil_eau"] = round(max(p[1] for p in c if abs(p[0] - base) < 1e-9), 6)
        ent["contour"] = [[round(x, 6), round(y, 6)] for x, y in c]
        table[nom] = ent
    src = dict(src)
    src["regles_route_fr.json"] = _sha16(REGLES)
    return table, src


_TABLE_PJ = None


def _table_pj(PR, d):
    """Table d'origine de pj::bordure (fonction d'origine même si profils.construire_table a été remplacée)."""
    f = getattr(PR, "_construire_table_origine", PR.construire_table)
    return f(d)


def installer_table_etendue():
    """Remplace profils.construire_table (module de pj::bordure importé) par la table étendue, en mémoire : les HDA
    construites ensuite dans ce processus (rg::nivellement, pj::bordure 2.1, pj::caniveau 2.2) figent la table étendue."""
    sys.path.insert(0, str(PJ_BORDURE))
    import profils as PR  # noqa: E402
    if not hasattr(PR, "_construire_table_origine"):
        PR._construire_table_origine = PR.construire_table
        PR.construire_table = construire_table_etendue
    return PR


@lru_cache(maxsize=1)
def vues_nominales() -> dict:
    """{profil: (vue min, vue max)} : bordures.json vue_courante, profils complémentaires, RF-AS-profil_*."""
    out = {}
    b = json.loads((SPECS / "bordures.json").read_text(encoding="utf-8"))["profils"]
    e = json.loads((SPECS / "bordures_elements.json").read_text(encoding="utf-8")).get("profils_complementaires") or {}
    for src in (b, e):
        for k, v in src.items():
            if v.get("vue_courante"):
                out[k] = tuple(float(x) for x in v["vue_courante"])
    for k in AJOUTS:
        v = profil_rf(k)
        if k not in out and v and v.get("vue_nominale_m"):
            out[k] = tuple(float(x) for x in v["vue_nominale_m"])
    return out


def regle_vue(nom: str) -> str:
    return f"RF-AS-profil_{nom}" if f"RF-AS-profil_{nom}" in _regles() else "RF-AS-liste_profils_nf"


def profil_par_vue(vue: float, familles=("T", "A", "P")) -> tuple[str, str]:
    """Profil dont la vue nominale contient la vue (famille préférée dans l'ordre donné ; plus petite section) :
    vue < 0,03 → P1, 0,03-0,09 → A2, 0,09-0,175 → T2, 0,175-0,30 → T3 / T4 (bordures.json regles_affectation,
    RF-AS-profil_*). Renvoie (profil, règle)."""
    ordre = {"T": ("T2", "T1", "T3", "T4"), "A": ("A2", "A1"), "P": ("P1", "P3", "P2"), "I": ("I1", "I2")}
    vn = vues_nominales()
    for f in familles:
        for p in ordre.get(f, ()):
            a, b = vn.get(p, (None, None))
            if a is not None and a - 1e-9 <= vue <= b + 1e-9:
                return p, regle_vue(p)
    return ("T4" if vue > 0.2 else "T2"), "RF-OSM-NIV-010"


def piece_abaisse(profil: str) -> tuple[str, str]:
    """(profil de la pièce d'abaissé, source) ; profil courant lui-même si le catalogue n'a pas de bateau du type."""
    if profil in PIECES_ABAISSE:
        return PIECES_ABAISSE[profil]
    return profil, "[G] pose abaissée du profil courant (aucun élément bateau de ce type au catalogue route_fr)"


def table_pieces_abaisse() -> dict:
    """{profil courant: profil d'abaissé} pour rg::vers_entites (paramètre pieces_abaisse), contrôlée : même base."""
    t, _ = construire_table_etendue()
    out = {}
    for k, (p, _src) in sorted(PIECES_ABAISSE.items()):
        if k in t and p in t:
            if abs(t[k]["base"] - t[p]["base"]) > 0.002:
                raise ValueError(f"pièce d'abaissé {p} de {k} : base {t[p]['base']} ≠ {t[k]['base']}")
            out[k] = p
    return out


def bordure_par_contexte(contexte: str) -> dict:
    """Règle par défaut d'un contexte : {profil, vue_m, regles, note, materiau_id?} (None pour « autoroute »)."""
    prof, vue, regles_, note = CONTEXTES[contexte]
    d = {"contexte": contexte, "profil": prof, "vue_m": vue, "regles": list(regles_), "note": note}
    if prof in MATERIAU_PROFIL:
        d["materiau_id"] = MATERIAU_PROFIL[prof]
    return d


# ---------------------------------------------------------------------------------------------------- catalogue route_fr
def assets_du_profil(profil: str) -> dict:
    """{asset_id: asset} du catalogue route_fr pour un profil (bordures et caniveaux)."""
    return {k: a for k, a in _catalogue().items() if a.get("profil") == profil}


def contour_catalogue(asset_id: str):
    a = _catalogue()[asset_id]
    v = [float(x) for x in a["params"]["contour_a"].split()]
    return [[v[i], v[i + 1]] for i in range(0, len(v), 2)]


def _distance_contours(c1, c2, pas=0.0005):
    """Écart maximal (m) entre deux contours fermés (distance de Hausdorff des pourtours échantillonnés)."""
    def ech(c):
        pts = []
        for i in range(len(c)):
            a, b = c[i], c[(i + 1) % len(c)]
            n = max(1, int(math.dist(a, b) / pas))
            pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
        return pts

    def seg_d(p, c):
        best = 1e9
        for i in range(len(c)):
            a, b = c[i], c[(i + 1) % len(c)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            best = min(best, math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
        return best
    return max(max(seg_d(p, c2) for p in ech(c1)), max(seg_d(p, c1) for p in ech(c2)))


def ecarts_contours_catalogue(table) -> dict:
    """{profil: écart maximal (m) entre le contour posé (table) et le contour du mesh droit du catalogue}."""
    out = {}
    for prof, t in sorted(table.items()):
        cand = [k for k in (f"bordure_{prof}_L100", f"bordure_{prof}_L050") if k in _catalogue()]
        if not cand:
            continue
        out[prof] = {"asset": cand[0], "ecart_m": round(_distance_contours(t["contour"], contour_catalogue(cand[0])), 5)}
    return out


def _cote(e):
    return "gauche" if (e.get("vue_fin", 0) or 0) < (e.get("vue", 0) or 0) else "droite"


def asset_element(e: dict) -> tuple[str | None, str]:
    """Asset du catalogue route_fr d'un élément posé de elements.json (pj::bordure / pj::caniveau), avec le motif ;
    (None, motif) pour une pièce sur mesure (prototype de pj::bordure : sm_*, coupe, chartière en plusieurs pièces)."""
    cat = _catalogue()
    if e.get("kind") != "element":
        return None, "joint (mortier)"
    ty, prof = e.get("type"), e.get("profil") or ""
    L = float(e.get("longueur") or 0.0)
    if ty in ("avaloir",):
        return None, "grille d'avaloir (decal_grille_avaloir, bibliothèque de matériaux)"
    if ty == "grille":
        return None, "caniveau à grille sur mesure"
    if e.get("famille") == "caniveau":
        for suf in (("L100", 0.994), ("L050", 0.494)):
            k = f"bordure_{prof}_{suf[0]}"
            if k in cat and abs(L - suf[1]) <= 0.012:
                return k, "élément entier"
        k = f"bordure_{prof}_L100"
        return (k, "coupe d'un élément du catalogue") if k in cat else (None, f"caniveau {prof} absent du catalogue")
    if ty == "chartiere":
        bas = e.get("profil_bas") or prof
        r = RACCORDS.get((prof, bas)) or RACCORDS.get((prof, PIECES_ABAISSE.get(prof, (bas,))[0]))
        if r and abs(L - 0.994) <= 0.02 and min(e.get("vue", 1), e.get("vue_fin", 1)) <= 0.045:
            return f"bordure_raccord_{r}_{_cote(e)}", "raccord du catalogue (un élément de 1,00 m)"
        return None, (f"chartière sur mesure ({L:.2f} m, vue {e.get('vue', 0):.3f} → {e.get('vue_fin', 0):.3f}) : "
                      "rampant de plusieurs pièces taillées")
    if ty == "raccord_vue":
        return None, "retour transversal à vue variable (sur mesure)"
    if e.get("angle_debut") or e.get("angle_fin"):
        sens = e.get("angle_sens") or "sortant"
        k = f"bordure_{prof}_angle_{sens}"
        if k in cat:
            return k, f"pièce d'angle {sens} du catalogue"
        return None, f"pièce d'angle sur mesure en onglet ({prof} : pas de pièce d'angle au catalogue)"
    if ty == "courbe" or e.get("sur_mesure"):
        R = e.get("rayon_m")
        if R:
            for k, a in cat.items():
                if a.get("profil") == prof and "courbe" in k and abs(float(a["params"].get("rayon", 0)) - R) <= 0.1 * R:
                    return k, f"pièce courbe du catalogue (R {a['params']['rayon']} m)"
        return None, "pièce sur mesure (courbe ou coupe en courbe)"
    p = EQUIVALENTS_CATALOGUE.get(prof, prof)
    for suf, Ln in (("L100", 0.994), ("L050", 0.494)):
        k = f"bordure_{p}_{suf}"
        if k in cat and abs(L - Ln) <= 0.012:
            return k, "élément entier" + (f" (équivalent catalogue de {prof})" if p != prof else "")
    for suf, Ln in (("L100", 0.994), ("L050", 0.494)):
        k = f"bordure_{p}_{suf}"
        if k in cat:
            eq = f" (équivalent de {prof})" if p != prof else ""
            if L <= Ln + 0.012:
                return k, f"coupe ({L:.3f} m) d'un élément du catalogue" + eq
            n = math.ceil((L + 0.006) / (Ln + 0.006) - 1e-6)
            return k, f"{n} éléments de {Ln + 0.006:.2f} m du catalogue pour {L:.3f} m (seule longueur au catalogue)" + eq
    return None, f"profil {prof} sans mesh au catalogue route_fr (prototype pj::bordure)"


# ---------------------------------------------------------------------------------------------------- description
# mots de profil ajoutés à la description (vocabulaire.PROFILS_BORDURE ; les mots existants sont gardés tels quels)
MOTS_PROFILS = {
    "t4": "T4", "i3": "I3", "i4": "I4", "p4": "P4", "tu": "TU", "ac1": "AC1",
    "gr_t1": "GR_T1", "gr_t2": "GR_T2", "gr_p1": "GR_P1", "granit_t1": "GR_T1", "granit_t2": "GR_T2",
    "granit_p1": "GR_P1", "t2_basse": "T2_basse", "t3_basse": "T3_basse", "t2_surbaissee": "T2_surbaissee",
    "t3_surbaissee": "T3_surbaissee", "p1_basse": "P1_basse", "accesbus": "ACCESBUS", "quai_accessible": "ACCESBUS",
    "gr_a1": "GR_A1", "gr_a2": "GR_A2", "gr_p3": "GR_P3", "granit_a1": "GR_A1", "granit_a2": "GR_A2", "granit_p3": "GR_P3",
    "bordurette": "P1", "paves_granit": "PAVES_GRANIT", "quai_bus": "QUAI_BUS", "t2_bateau": "T2_bateau", "cs3": "CS3", "cs4": "CS4",
}
MOTS_CANIVEAUX = {"cs4": "CS4"}


def enumerations_schema() -> tuple[list, list]:
    """(profils de bordure, profils de caniveau) admis par le schéma étendu."""
    t, _ = construire_table_etendue()
    bord = sorted(k for k, v in t.items() if k != "MURET_TALUS") + ["autre"]
    can = sorted(k for k, v in t.items() if v["famille"] == "caniveau") + ["aucun"]
    return bord, can


def _etendre_schema(s: dict) -> dict:
    bord, can = enumerations_schema()
    b = s["$defs"]["bordure"]["properties"]
    b["profil"]["enum"] = sorted(set(b["profil"]["enum"]) | set(bord), key=lambda x: (x == "autre", x))
    c = b["caniveau"]["properties"]["profil"]
    c["enum"] = sorted(set(c["enum"]) | set(can), key=lambda x: (x == "aucun", x))
    return s


def _cle_niveau(PF, x):
    try:
        return PF.cle_niveau(x)
    except Exception:  # noqa: BLE001
        return ""


def resoudre_saut_de_niveau(bo: dict, kh: str, kb: str, P) -> tuple[dict, dict]:
    """Bordure d'un saut de niveau de profil « autre » (aucune règle de profil) : profil dont la vue nominale contient
    la vue (piste à niveau intermédiaire : A2 RF-MA-SEP-005 ; contre un niveau intermédiaire : A ou T) ; renvoie
    (bordure, provenance). Appelé par commun/profil.py (bordure_entre) depuis l'intégration de l'étape 2."""
    vue = float(bo.get("vue_m") or 0.0)
    if "intermediaire" in (kh, kb) and kb == "chaussee":
        c = bordure_par_contexte("piste_intermediaire")
        prof, regle = (c["profil"], "RF-MA-SEP-005") if vue >= 0.03 else profil_par_vue(vue, ("P", "A"))
    elif "intermediaire" in (kh, kb):
        prof, regle = profil_par_vue(vue, ("A", "T")) if vue < 0.09 else profil_par_vue(vue, ("T",))
        regle = "RF-MA-SEP-004" if prof.startswith("A") else regle
    else:
        prof, regle = profil_par_vue(vue)
    bo = dict(bo, profil=prof, regle=regle)
    pv = P.defaut(regle, conf="faible", note=f"saut de niveau {kb} → {kh} de {vue:.3f} m : {prof} (vue nominale "
                                              f"{vues_nominales().get(prof)}, lot bordures)")
    return bo, pv


def installer_description():
    """Étend en mémoire le compilateur de description (Python du système) : mots de profil, règle des sauts de niveau
    sans règle (profil « autre » → contexte ou vue nominale), énumérations du schéma. Rétrocompatible : les mots et
    les choix existants ne changent pas ; seuls les cas qui échouaient (mot inconnu, profil « autre » refusé par
    rg::nivellement) sont résolus."""
    sys.path.insert(0, str(GEN))
    sys.path.insert(0, str(GEN / "schema"))
    from description import vocabulaire as V
    from commun import profil as PF
    from commun import prov as P
    import valider_modele as VM
    for k, v in MOTS_PROFILS.items():
        V.PROFILS_BORDURE.setdefault(k, v)
    for k, v in MOTS_CANIVEAUX.items():
        V.CANIVEAUX.setdefault(k, v)
    if not hasattr(VM, "_charger_origine"):
        VM._charger_origine = VM.charger
        VM.charger = lambda p: _etendre_schema(VM._charger_origine(p))
    if not hasattr(PF, "_bordure_entre_origine"):
        PF._bordure_entre_origine = PF.bordure_entre

        def bordure_entre(a, b, dza, dzb, ctx):
            r = PF._bordure_entre_origine(a, b, dza, dzb, ctx)
            bo = r.get("bordure") or {}
            if bo.get("profil") != "autre":
                return r
            haut, bas = (a, b) if dza > dzb else (b, a)
            kh, kb = _cle_niveau(PF, haut), _cle_niveau(PF, bas)
            vue = float(bo.get("vue_m") or 0.0)
            if "intermediaire" in (kh, kb) and kb == "chaussee":
                c = bordure_par_contexte("piste_intermediaire")
                prof, regle = (c["profil"], "RF-MA-SEP-005") if vue >= 0.03 else profil_par_vue(vue, ("P", "A"))
            elif "intermediaire" in (kh, kb):
                prof, regle = profil_par_vue(vue, ("A", "T")) if vue < 0.09 else profil_par_vue(vue, ("T",))
                regle = "RF-MA-SEP-004" if prof.startswith("A") else regle
            else:
                prof, regle = profil_par_vue(vue)
            bo = dict(bo, profil=prof, regle=regle)
            r = dict(r, bordure=bo)
            r["prov"] = dict(r.get("prov") or {}, bordure=P.defaut(
                regle, conf="faible", note=f"saut de niveau {kb} → {kh} de {vue:.3f} m : {prof} (vue nominale "
                                           f"{vues_nominales().get(prof)}, lot bordures)"))
            return r
        PF.bordure_entre = bordure_entre
    return V, PF, VM


def compiler(argv=None):
    """Compile une description avec l'extension (description_vers_modele.main, sortie identique au compilateur)."""
    installer_description()
    from description import description_vers_modele as DV
    sys.argv = ["description_vers_modele.py"] + list(argv or [])
    return DV.main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--compiler":
        sys.exit(compiler(sys.argv[2:]))
    t, s = construire_table_etendue()
    print(json.dumps({"profils": sorted(t), "source": s, "pieces_abaisse": table_pieces_abaisse(),
                      "ecarts_catalogue": ecarts_contours_catalogue(t)}, ensure_ascii=False, indent=1))
