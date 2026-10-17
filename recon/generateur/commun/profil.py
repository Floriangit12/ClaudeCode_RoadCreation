# -*- coding: utf-8 -*-
"""Construction d'un profil `modele_voie/0.1` complet à partir d'une liste ordonnée de bandes (lot L0).

Entrée : bandes de la gauche vers la droite (sens de la ligne de référence), chacune avec ce qui est connu (type,
sens, largeur ou None, attributs, provenance) ; limites explicites facultatives (None = à déduire). Ce module
complète tout ce qui n'est pas dit, en citant la règle de `regles_route_fr.json` qui fixe la valeur :

| Complément | Règles |
|---|---|
| largeurs par défaut | DEF-002 à DEF-004, DEF-007 à DEF-009 ; RF-OSM-LAR-010 à -050 ; RF-GV-TPC-010 ; RF-GV-PT-004, -013 |
| niveaux (vue, dévers) | DEF-005, DEF-006, DEF-032 ; RF-OSM-NIV-010, -011, -013 ; RF-OSM-LAR-033 ; RF-MA-SEP-005 |
| bordures (saut de niveau) | RF-OSM-NIV-010 (T2), DEF-005 + RF-AS-profil_I2 (terre-plein), DEF-032 (quai), RF-MA-SEP-* |
| marquages longitudinaux | RF-OSM-MRQ-010, -011, -020, -021, -022, -030, -031, -060 ; RF-MQ-LAR-A1b, -D1 ; RF-OSM-CAR-051 ; RF-OSM-CYC-002 |
| u | DEF-001 (RF-MQ-U-0x) |
| matériaux | table surface_vers_materiau du volet 12 ; RF-MA-BAN-009 ; RF-MA-PIS-009 ; RF-OSM-VEG-002 |
| figurines vélo | DEF-018 (RF-OSM-CYC-001) |

Conventions : `largeur` peut être une loi `{type: points, interpolation: lineaire, points: [[s, l], …]}` dont les s
sont des **abscisses absolues** le long de la ligne de référence de la route (convention du générateur, écrite dans
`meta.conventions` des modèles produits) ; même convention pour `interruptions`, `intervalle`, `abaisses`.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import regles  # noqa: E402
from commun import prov as P  # noqa: E402

# ---------------------------------------------------------------------------------------------------- familles
VOIES_MOTORISEES = {"voie_circulation", "voie_bus", "voie_tram", "voie_tourne_gauche", "voie_tourne_droite",
                    "voie_stockage", "voie_insertion", "voie_deceleration", "voie_centrale_banalisee",
                    "chaussee_partagee"}
TYPES_CHAUSSEE = VOIES_MOTORISEES | {"bande_cyclable", "rive_cyclable_cvcb", "stationnement", "livraison",
                                     "zone_neutralisee", "bande_derasee", "accotement_revetu",
                                     "bande_arret_urgence"}
TYPES_ACCOTEMENT = {"bande_derasee", "accotement_revetu", "bande_arret_urgence"}
TYPES_TERRAIN = {"berme", "fosse", "noue", "talus", "autre"}
TYPES_PIETONS = {"trottoir", "chemin_pieton", "quai_bus"}

ABREVIATIONS = {
    "voie_circulation": "v", "voie_bus": "bus", "voie_tram": "tram", "voie_tourne_gauche": "tag",
    "voie_tourne_droite": "tad", "voie_stockage": "sto", "voie_insertion": "ins", "voie_deceleration": "dec",
    "voie_centrale_banalisee": "vcb", "chaussee_partagee": "ch", "bande_cyclable": "bc", "piste_cyclable": "pc",
    "voie_verte": "vv", "rive_cyclable_cvcb": "rc", "stationnement": "st", "livraison": "liv", "trottoir": "tr",
    "quai_bus": "quai", "chemin_pieton": "chp", "terre_plein": "tp", "zone_neutralisee": "zn", "separateur": "sep",
    "bande_plantee": "bp", "accotement_revetu": "acc", "bande_derasee": "bdd", "bande_arret_urgence": "bau",
    "berme": "ber", "fosse": "fos", "noue": "noue", "talus": "tal", "autre": "aut",
}

LANE_TYPE = {  # MODELE_VOIE § 8 : type de bande → e_laneType OpenDRIVE
    "voie_bus": "bus", "voie_tram": "tram", "bande_cyclable": "biking", "piste_cyclable": "biking",
    "voie_verte": "biking", "rive_cyclable_cvcb": "biking", "trottoir": "sidewalk", "quai_bus": "sidewalk",
    "chemin_pieton": "walking", "stationnement": "parking", "livraison": "parking", "terre_plein": "median",
    "zone_neutralisee": "restricted", "bande_derasee": "shoulder", "accotement_revetu": "shoulder",
    "bande_arret_urgence": "shoulder", "separateur": "curb", "berme": "border", "fosse": "border",
    "noue": "border", "talus": "border", "bande_plantee": "border", "voie_insertion": "entry",
    "voie_deceleration": "exit", "voie_centrale_banalisee": "bidirectional", "autre": "none",
}
TAGS_GRAPHE = {"voie_bus": ["bus"], "bande_cyclable": ["velo"], "piste_cyclable": ["velo"], "voie_verte": ["velo", "pieton"],
               "trottoir": ["pieton"], "quai_bus": ["pieton"], "chemin_pieton": ["pieton"],
               "stationnement": ["stationnement"], "livraison": ["stationnement"]}
USAGERS = {"voie_circulation": ["vl", "pl", "velo"], "voie_bus": ["bus"], "voie_tram": ["tram"],
           "voie_tourne_gauche": ["vl", "pl", "velo"], "voie_tourne_droite": ["vl", "pl", "velo"],
           "voie_stockage": ["vl", "pl", "velo"], "chaussee_partagee": ["vl", "pl", "velo", "pieton"],
           "voie_centrale_banalisee": ["vl", "pl"], "bande_cyclable": ["velo"], "piste_cyclable": ["velo", "edpm"],
           "voie_verte": ["velo", "pieton"], "trottoir": ["pieton"], "quai_bus": ["pieton"],
           "chemin_pieton": ["pieton"], "stationnement": ["vl"], "livraison": ["vl", "pl"]}


AFFLEURANT = 0.015   # écart de niveau (m) en dessous duquel deux bandes sont de plain-pied (pas de bordure)


class ErreurProfil(ValueError):
    """Profil impossible à compléter sans inventer une valeur (aucune règle ne la fixe)."""


def nombre(v):
    """Largeur constante d'une bande (loi : première valeur)."""
    if isinstance(v, dict):
        return v["points"][0][1] if v.get("type") == "points" else v["morceaux"][0]["a"]
    return v


def largeur_max(v):
    if isinstance(v, dict) and v.get("type") == "points":
        return max(p[1] for p in v["points"])
    return nombre(v)


# ---------------------------------------------------------------------------------------------------- contexte
def contexte(agglomeration: bool, vitesse_kmh: float, categorie: str, **k) -> dict:
    """Contexte de construction. Clés facultatives : prov_agglomeration, prov_vitesse, u, prov_u, materiaux
    {classe: (materiau_id, prov)}, marquages {axe|rives|entre_voies: dict | 'aucune'}, usure_marquages (0-1),
    prov_usure, nom (pour les messages)."""
    c = {"agglomeration": bool(agglomeration), "vitesse_kmh": vitesse_kmh, "categorie": categorie,
         "materiaux": {}, "marquages": {}, "usure_marquages": None}
    c.update(k)
    if c.get("u") is None:
        cle = "piste_cyclable" if categorie == "piste_cyclable_independante" else (
            "autoroute_chaussees_separees" if categorie in ("autoroute", "voie_express") else "autres_routes")
        c["u"] = regles.valeur("DEF-001", cle)
        c["prov_u"] = P.defaut("DEF-001", note=f"u = {c['u']} m ({cle})")
    return c


# ---------------------------------------------------------------------------------------------------- largeurs
def _chaussee_separee(bandes) -> bool:
    return any(b["type"] in ("terre_plein", "separateur") for b in bandes)


def largeur_defaut(b: dict, bandes: list, ctx: dict):
    """(largeur, prov) par défaut d'une bande, selon les règles ; ErreurProfil si aucune règle ne la fixe."""
    t, agglo = b["type"], ctx["agglomeration"]
    attrs = b.get("attributs", {})
    if t == "voie_circulation":
        meme = [x for x in bandes if x["type"] == "voie_circulation" and x["sens"] == b["sens"]]
        sens_unique = not any(x["type"] in VOIES_MOTORISEES and x["sens"] not in (b["sens"], "double")
                              for x in bandes)
        if agglo:
            if len(meme) >= 2:
                return regles.valeur("RF-OSM-LAR-012", "meme_sens_defaut"), P.defaut("RF-OSM-LAR-012")
            if sens_unique:
                return regles.valeur("RF-OSM-LAR-011", "defaut"), P.defaut("RF-OSM-LAR-011", par="DEF-003")
            return regles.valeur("RF-OSM-LAR-010", "defaut"), P.defaut("RF-OSM-LAR-010", par="DEF-002")
        cat = ctx["categorie"]
        cle = {"autoroute": "autoroute_voie", "route_nationale": "route_nationale_voie",
               "voie_express": "RD_2_chaussees_voie"}.get(cat)
        if cle is None:
            cle = "RD_2_chaussees_voie" if _chaussee_separee(bandes) else "RD_1_chaussee_voie"
        conf = None if cat in ("autoroute", "route_nationale", "route_departementale", "voie_express") else "faible"
        return regles.valeur("RF-OSM-LAR-014", cle), P.defaut("RF-OSM-LAR-014", conf=conf, note=cle)
    if t == "voie_bus":
        return regles.valeur("RF-OSM-LAR-013", "defaut"), P.defaut("RF-OSM-LAR-013")
    if t in ("voie_tourne_gauche", "voie_tourne_droite", "voie_stockage"):
        return (regles.valeur("RF-OSM-LAR-012", "preselection_defaut"),
                P.defaut("RF-OSM-LAR-012", conf=None if agglo else "faible", note="preselection_defaut"))
    if t == "chaussee_partagee":
        return regles.valeur("RF-GV-PT-004", "2_VL_faible_vitesse"), P.defaut(
            "RF-GV-PT-004", conf="faible", note="chaussée partagée : croisement de 2 VL à faible vitesse")
    if t == "bande_cyclable":
        return regles.valeur("RF-OSM-LAR-030", "defaut"), P.defaut("RF-OSM-LAR-030", par="DEF-007")
    if t == "piste_cyclable":
        if attrs.get("demi_piste"):
            v = regles.valeur("RF-OSM-LAR-031", "bidirectionnelle_defaut") / 2.0
            return v, P.defaut("RF-OSM-LAR-031", par="DEF-008", note="moitié d'une piste bidirectionnelle de 3,00 m")
        return regles.valeur("RF-OSM-LAR-031", "unidirectionnelle_defaut"), P.defaut("RF-OSM-LAR-031", par="DEF-008")
    if t == "voie_verte":
        return regles.valeur("RF-GV-PT-013", "bidirectionnel_min"), P.defaut("RF-GV-PT-013", conf="faible")
    if t == "zone_neutralisee" and b.get("sous_type") == "tampon_emportierage":
        return regles.valeur("RF-OSM-LAR-032", "defaut"), P.defaut("RF-OSM-LAR-032", par="DEF-007")
    if t == "separateur":
        return regles.valeur("RF-OSM-LAR-033", "largeur_defaut"), P.defaut("RF-OSM-LAR-033", par="DEF-008")
    if t == "stationnement":
        o = (b.get("stationnement") or {}).get("orientation", "longitudinal")
        if o == "longitudinal":
            return regles.valeur("RF-OSM-LAR-040", "largeur_defaut"), P.defaut("RF-OSM-LAR-040", par="DEF-009")
        return regles.valeur("RF-OSM-LAR-041", "profondeur_conseillee"), P.defaut("RF-OSM-LAR-041")
    if t == "livraison":
        return regles.valeur("RF-MA-STA-009", "largeur"), P.defaut("RF-MA-STA-009")
    if t == "trottoir":
        return regles.valeur("DEF-004"), P.defaut("DEF-004")
    if t == "terre_plein" and (b.get("terre_plein") or {}).get("franchissable") not in ("peint",):
        return regles.valeur("RF-OSM-LAR-050", "tpc_plante_min"), P.defaut(
            "RF-OSM-LAR-050", conf="faible", note="largeur non dite : minimum d'un terre-plein planté")
    if t == "bande_plantee":
        return regles.valeur("RF-GV-TPC-010", "fosse_ideale_cote"), P.defaut(
            "RF-GV-TPC-010", note="bande plantée = côté de la fosse idéale (3 × 3 m)")
    if t in ("bande_derasee", "accotement_revetu"):
        cat = ctx["categorie"]
        if cat == "route_nationale":
            return regles.valeur("RF-OSM-LAR-014", "route_nationale_BDD"), P.defaut("RF-OSM-LAR-014", note="route_nationale_BDD")
        n = max(sum(1 for x in bandes if x["type"] == "voie_circulation" and x["sens"] == s) for s in ("avant", "arriere"))
        cle = "RD_1_chaussee_BDD_2_voies_ou_plus" if n >= 2 else "RD_1_chaussee_BDD_0_1_voie"
        return regles.valeur("RF-OSM-LAR-014", cle), P.defaut("RF-OSM-LAR-014", conf=None if not agglo else "faible", note=cle)
    if t == "bande_arret_urgence":
        return regles.valeur("RF-OSM-LAR-014", "autoroute_BAU"), P.defaut("RF-OSM-LAR-014", note="autoroute_BAU")
    if t == "berme":
        return regles.valeur("RF-OSM-LAR-014", "route_nationale_berme"), P.defaut(
            "RF-OSM-LAR-014", conf="faible", note="berme de route nationale (1,00 m), seule berme chiffrée de la base")
    raise ErreurProfil(f"largeur de la bande « {b['type']} » non dite et aucune règle ne la fixe : à décrire")


# ---------------------------------------------------------------------------------------------------- niveaux
def cle_niveau(b: dict) -> str:
    """chaussee, trottoir, intermediaire, separateur, terre_plein, quai, terrain."""
    t = b["type"]
    a = b.get("attributs", {})
    if t in TYPES_CHAUSSEE:
        st = b.get("stationnement") or {}
        if t == "stationnement" and st.get("position") in ("trottoir", "mi_trottoir"):
            return "trottoir"
        return "chaussee"
    if t == "piste_cyclable":
        return a.get("niveau", "trottoir")
    if t in ("trottoir", "chemin_pieton", "bande_plantee"):
        return a.get("niveau", "trottoir")
    if t == "quai_bus":
        return "quai"
    if t == "separateur":
        return "separateur"
    if t == "terre_plein":
        f = (b.get("terre_plein") or {}).get("franchissable", "non")
        return "chaussee" if f == "peint" else "terre_plein"
    return "terrain"


def _vue_trottoir(ctx):
    v = ctx.get("vue_trottoir")
    if v is not None:
        return v
    return regles.valeur("DEF-005", "trottoir"), P.defaut("DEF-005", note="vue de bordure de trottoir")


def niveau_dz(b: dict, ctx: dict):
    """(dz, prov) du niveau de la bande par rapport au fil d'eau de la chaussée."""
    k = cle_niveau(b)
    a = b.get("attributs", {})
    if "dz_m" in a:
        return a["dz_m"], a.get("prov_dz") or P.description("profil.niveau")
    if k == "chaussee" or k == "terrain":
        return 0.0, P.defaut("RF-OSM-NIV-010", note="bande au niveau de la chaussée (fil d'eau), dz = 0")
    if k == "trottoir":
        v = _vue_trottoir(ctx)
        return v if isinstance(v, tuple) else (v, P.description("bordure.vue"))
    if k == "intermediaire":
        lo, hi = regles.valeur("RF-MA-SEP-005", "denivellation_avec_chaussee")
        return round((lo + hi) / 2, 3), P.defaut("RF-MA-SEP-005", conf="faible",
                                                note=f"piste à niveau intermédiaire : milieu de la plage [{lo} ; {hi}]")
    if k == "separateur":
        return regles.valeur("RF-OSM-LAR-033", "hauteur_cote_chaussee"), P.defaut("RF-OSM-LAR-033", note="hauteur côté chaussée")
    if k == "terre_plein":
        f = (b.get("terre_plein") or {}).get("franchissable", "non")
        if f in ("vl_pl", "pl_seulement"):
            return 0.04, P.defaut("RF-OSM-NIV-012", conf="faible", note="bordure franchissable : borne basse de 0,04-0,10")
        return regles.valeur("DEF-005", "ilot"), P.defaut("DEF-005", note="vue de bordure d'îlot / terre-plein")
    if k == "quai":
        return regles.valeur("DEF-032", "hauteur"), P.defaut("DEF-032", note="hauteur de quai bus")
    return 0.0, P.solveur("niveau")


# ---------------------------------------------------------------------------------------------------- matériaux
def materiau_defaut(b: dict, ctx: dict):
    """(materiau_id, prov) ou (None, None)."""
    t, k = b["type"], cle_niveau(b)
    m = ctx.get("materiaux", {})
    if t in ("bande_cyclable",):
        if "chaussee" in m:
            return m["chaussee"][0], P.defaut("RF-MA-BAN-009", note="revêtement de la chaussée")
        return "enrobe_bbsg_ancien", P.defaut("RF-MA-BAN-009", note="revêtement de la chaussée (table surface_vers_materiau, surface absente)")
    if t in ("piste_cyclable",):
        if "pistes" in m:
            return m["pistes"]
        if k == "chaussee":
            return (m.get("chaussee") or ("enrobe_bbsg_ancien", None))[0], P.defaut("RF-MA-PIS-009", note="piste au niveau de la chaussée")
        return "enrobe_piste_cyclable", P.defaut("RF-MA-PIS-009", note="piste haute : enrobé distinct (table surface_vers_materiau, piste)")
    if t in TYPES_CHAUSSEE and t not in TYPES_ACCOTEMENT:
        return m.get("chaussee") or ("enrobe_bbsg_ancien", P.table("surface_vers_materiau", note="surface absente → chaussée"))
    if t in TYPES_ACCOTEMENT:
        return m.get("accotements") or m.get("chaussee") or ("enrobe_bbsg_ancien", P.table("surface_vers_materiau", note="surface absente → chaussée"))
    if t in ("trottoir", "chemin_pieton"):
        return m.get("trottoirs") or ("enrobe_trottoir", P.table("surface_vers_materiau", note="surface absente → trottoir"))
    if t == "quai_bus":
        return m.get("quais") or m.get("trottoirs") or ("enrobe_trottoir", P.table("surface_vers_materiau", note="surface absente → trottoir"))
    if t in ("bande_plantee", "berme"):
        return m.get("vegetal") or ("gazon_tondu", P.defaut("RF-OSM-VEG-002", conf="faible", note="bande plantée sans précision : gazon"))
    if t == "terre_plein":
        tp = b.get("terre_plein") or {}
        r = (tp.get("remplissage") or {}).get("materiau_id")
        if r:
            return r, b.get("prov_terre_plein") or P.defaut("RF-OSM-VEG-002")
        if tp.get("franchissable") == "peint":
            return m.get("chaussee") or ("enrobe_bbsg_ancien", P.table("surface_vers_materiau", note="TPC peint : revêtement de chaussée"))
    return None, None


# ---------------------------------------------------------------------------------------------------- marquages
def marque(modulation: str, largeur_u: float | None, ctx: dict, regle: str, couleur: str = "blanc",
           u: float | None = None, largeur_m: float | None = None) -> dict:
    m = {"modulation": modulation}
    if largeur_m is not None:
        m["largeur_m"] = largeur_m
    else:
        m["largeur_u"] = largeur_u
        m["u_m"] = u if u is not None else ctx["u"]
    m["couleur"] = couleur
    if ctx.get("usure_marquages") is not None:
        m["usure"] = ctx["usure_marquages"]
    m["regle"] = regle
    return m


def _xodr(mods: list[dict]) -> dict:
    m = mods[0]["modulation"]
    if m == "continue":
        return {"roadmark_type": "solid", "lane_change": "none"}
    if m == "double_continue":
        return {"roadmark_type": "solid solid", "lane_change": "none"}
    return {"roadmark_type": "broken", "lane_change": "both"}


def limite_marquage(mods: list[dict], prov_e: dict) -> dict:
    return {"nature": ["marquage"], "marquages": mods, "x-opendrive": _xodr(mods), "prov": {"marquages": prov_e}}


def _voies_par_sens(groupe: list[dict]) -> dict:
    n = {"avant": 0, "arriere": 0, "double": 0}
    for b in groupe:
        if b["type"] in VOIES_MOTORISEES:
            n[b["sens"]] = n.get(b["sens"], 0) + 1
    return n


def _surcharge(ctx, cle):
    """Surcharge de la description pour axe / rives / entre_voies : (dict marque, prov) | ('aucune', prov) | None."""
    return (ctx.get("marquages") or {}).get(cle)


def marquage_entre(a: dict, b: dict, groupe: list[dict], ctx: dict):
    """Limite déduite entre deux bandes de niveau chaussée a | b (a à gauche). Retourne (limite, avertissements)."""
    ta, tb, agglo = a["type"], b["type"], ctx["agglomeration"]
    av = []
    mot_a, mot_b = ta in VOIES_MOTORISEES, tb in VOIES_MOTORISEES

    def virtuelle(note, regle="RF-OSM-PRF-001"):
        return {"nature": ["virtuelle"], "prov": {"*": P.inference(regle, note=note)}}

    # séparation des sens
    if mot_a and mot_b and {a["sens"], b["sens"]} == {"arriere", "avant"}:
        s = _surcharge(ctx, "axe")
        if s is not None:
            if s[0] == "aucune":
                return virtuelle("axe : aucune ligne (description)"), av
            return limite_marquage([dict(s[0], **({"usure": ctx["usure_marquages"]} if ctx.get("usure_marquages") is not None else {}))], s[1]), av
        n = _voies_par_sens(groupe)
        if n["avant"] >= 2 and n["arriere"] >= 2:
            return limite_marquage([marque("continue", 5, ctx, "RF-MQ-LAR-A1b")], P.inference("RF-MQ-LAR-A1b", note="axe d'une chaussée à 4 voies")), av
        larg = sum(nombre(x["largeur"]) for x in groupe if x["type"] in VOIES_MOTORISEES)
        seuil = regles.valeur("RF-OSM-MRQ-010", "largeur_circulable_min_pour_axe")
        if larg < seuil - 1e-9:
            av.append(f"axe non marqué : largeur circulable {larg:.2f} m < {seuil} m (RF-OSM-MRQ-010)")
            return virtuelle(f"largeur circulable {larg:.2f} < {seuil} : pas d'axe", "RF-OSM-MRQ-010"), av
        mod = "T'1" if agglo else "T1"
        return limite_marquage([marque(mod, 2, ctx, "RF-OSM-MRQ-010")],
                               P.inference("RF-OSM-MRQ-010", note=f"axe {mod} 2u ({'agglomération' if agglo else 'rase campagne'})")), av
    # voies de même sens
    if mot_a and mot_b:
        if "voie_bus" in (ta, tb):
            bus, autre = (a, b) if ta == "voie_bus" else (b, a)
            if bus["sens"] != autre["sens"] or (bus.get("attributs") or {}).get("permanent"):
                return limite_marquage([marque("continue", 5, ctx, "RF-OSM-MRQ-031")], P.inference("RF-OSM-MRQ-031", note="couloir bus permanent ou à contresens")), av
            return limite_marquage([marque("T3", 5, ctx, "RF-OSM-MRQ-031")], P.inference("RF-OSM-MRQ-031")), av
        s = _surcharge(ctx, "entre_voies")
        if s is not None:
            if s[0] == "aucune":
                return virtuelle("entre voies : aucune ligne (description)"), av
            return limite_marquage([dict(s[0])], s[1]), av
        if {ta, tb} & {"voie_tourne_gauche", "voie_tourne_droite", "voie_stockage"}:
            return limite_marquage([marque("T3", 2, ctx, "RF-OSM-MRQ-011")],
                                   P.inference("RF-OSM-MRQ-011", note="voie affectée (flèches) : T3 2u")), av
        mod = "T'1" if agglo else "T1"
        return limite_marquage([marque(mod, 2, ctx, "RF-OSM-MRQ-011")], P.inference("RF-OSM-MRQ-011", note=f"voies de même sens {mod} 2u")), av
    # cyclable
    if (mot_a and tb == "bande_cyclable") or (mot_b and ta == "bande_cyclable"):
        s = _surcharge(ctx, "cyclable")
        if s is not None and s[0] != "aucune":
            return limite_marquage([dict(s[0])], s[1]), av
        return limite_marquage([marque("T3", 5, ctx, "RF-OSM-MRQ-030")], P.inference("RF-OSM-MRQ-030")), av
    # stationnement
    if "stationnement" in (ta, tb):
        autre = b if ta == "stationnement" else a
        if autre["type"] == "zone_neutralisee" and autre.get("sous_type") != "tampon_emportierage":
            return virtuelle("stationnement contre une zone neutralisée"), av
        if autre["type"] == "stationnement":
            return virtuelle("deux files de stationnement"), av
        if autre["type"] == "bande_cyclable":
            av.append("bande cyclable contre le stationnement sans tampon de 0,50 m (RF-MA-BAN-004, RF-OSM-LAR-032)")
        return limite_marquage([marque("T'2", 2, ctx, "RF-OSM-MRQ-060")], P.inference("RF-OSM-MRQ-060")), av
    if "livraison" in (ta, tb):
        return limite_marquage([marque("T'2", 2, ctx, "RF-OSM-MRQ-060", couleur="jaune")], P.inference("RF-OSM-MRQ-060", note="aire de livraison : jaune")), av
    # tampon (zone neutralisée contre l'ouverture des portières)
    if "zone_neutralisee" in (ta, tb):
        z, autre = (a, b) if ta == "zone_neutralisee" else (b, a)
        if z.get("sous_type") == "neutralisation_stationnement":
            return virtuelle("stationnement neutralisé : la ligne de stationnement s'interrompt", "RF-OSM-STA-002"), av
        if z.get("sous_type") == "tampon_emportierage":
            return virtuelle("tampon : délimité par la ligne de la bande cyclable et celle du stationnement", "RF-OSM-LAR-032"), av
        if autre["type"] in VOIES_MOTORISEES or autre["type"] == "bande_cyclable":
            return limite_marquage([marque("continue", 3, ctx, "RF-OSM-CAR-051")], P.inference("RF-OSM-CAR-051", note="contour de zone neutralisée continue 3u")), av
        return virtuelle("zone neutralisée"), av
    # terre-plein peint
    if "terre_plein" in (ta, tb):
        return limite_marquage([marque("continue", 3, ctx, "RF-MQ-LAR-D1")], P.inference("RF-MQ-LAR-D1", note="délimitation de terre-plein central peint")), av
    # rives sur accotement revêtu
    if ta in TYPES_ACCOTEMENT or tb in TYPES_ACCOTEMENT:
        return limite_rive(ctx, "bande_arret_urgence" in (ta, tb)), av
    if mot_a and tb == "rive_cyclable_cvcb" or mot_b and ta == "rive_cyclable_cvcb":
        return limite_marquage([marque("T3", 5, ctx, "RF-OSM-MRQ-030")], P.inference("RF-OSM-MRQ-030", note="rive cyclable (CVCB)")), av
    if ta not in TYPES_CHAUSSEE or tb not in TYPES_CHAUSSEE:
        return {"nature": ["changement_revetement"],
                "prov": {"*": P.inference("RF-OSM-MRQ-020", note=f"{ta} | {tb} de plain-pied : pas de ligne")}}, av
    return virtuelle(f"{ta} | {tb}"), av


def limite_rive(ctx: dict, bau: bool = False) -> dict:
    s = _surcharge(ctx, "rives")
    if s is not None:
        if s[0] == "aucune":
            return {"nature": ["virtuelle"], "prov": {"*": s[1]}}
        return limite_marquage([dict(s[0])], s[1])
    if bau:
        return limite_marquage([marque("T4", 3, ctx, "RF-OSM-MRQ-022")], P.inference("RF-OSM-MRQ-022", note="rive de BAU T4 3u"))
    if ctx["categorie"] in ("autoroute", "voie_express"):
        return limite_marquage([marque("continue", 3, ctx, "RF-OSM-MRQ-022")],
                               P.inference("RF-OSM-MRQ-022", note="rive sans BAU ou côté TPC : continue 3u"))
    return limite_marquage([marque("T2", 3, ctx, "RF-OSM-MRQ-021")], P.inference("RF-OSM-MRQ-021", note="rive sans bordure T2 3u"))


# ---------------------------------------------------------------------------------------------------- bordures
def bordure_entre(a: dict, b: dict, dza: float, dzb: float, ctx: dict) -> dict:
    """Limite « bordure » entre deux bandes de niveaux différents (a à gauche)."""
    haut, bas = (a, b) if dza > dzb else (b, a)
    kh, kb = cle_niveau(haut), cle_niveau(bas)
    vue = round(abs(dza - dzb), 4)
    cote = "gauche" if dza > dzb else "droite"
    if kb == "chaussee" and kh in ("trottoir",) and haut["type"] != "piste_cyclable":
        bo = {"profil": "T2", "vue_m": vue, "cote_haut": cote, "regle": "RF-OSM-NIV-010"}
        pv = P.defaut("RF-OSM-NIV-010", note="trottoir contre chaussée : bordure T2")
    elif kb == "chaussee" and kh == "trottoir":   # piste au niveau du trottoir contre la chaussée
        bo = {"profil": "T2", "vue_m": vue, "cote_haut": cote, "regle": "RF-OSM-NIV-010"}
        pv = P.defaut("RF-OSM-NIV-010", conf="faible", note="piste au niveau du trottoir contre la chaussée (RF-MA-PIS-006 : séparateur attendu)")
    elif kh == "terre_plein":
        bo = {"profil": "I2", "vue_m": vue, "cote_haut": cote, "regle": "DEF-005"}
        pv = P.defaut("DEF-005", note="ceinture de terre-plein : I2 (vue nominale 0,11, RF-AS-profil_I2)")
    elif kh == "quai" and kb == "chaussee":
        bo = {"profil": "QUAI_BUS", "vue_m": vue, "cote_haut": cote, "regle": "DEF-032"}
        pv = P.defaut("DEF-032", note="bordure de quai bus")
    elif "intermediaire" in (kh, kb):
        bo = {"profil": "autre", "vue_m": vue, "cote_haut": cote, "regle": "RF-MA-SEP-005"}
        pv = P.defaut("RF-MA-SEP-005", conf="faible", note="piste à niveau intermédiaire : bordure chanfreinée (5 pour 1)")
    elif kh == "separateur":
        sep = haut
        return {"nature": ["separateur"], "separateur": {
            "type": (sep.get("attributs") or {}).get("separateur", "bordure_separatrice"),
            "largeur_m": nombre(sep["largeur"]), "hauteur_m": vue, "regle": "RF-MA-SEP-001"},
            "prov": {"*": P.defaut("RF-MA-SEP-001", note="séparateur piste / chaussée")}}
    else:
        bo = {"profil": "autre", "vue_m": vue, "cote_haut": cote}
        pv = P.solveur("bordure", note=f"saut de niveau {kb} → {kh}", conf="faible")
    return {"nature": ["bordure"], "bordure": bo, "prov": {"bordure": pv}}


# ---------------------------------------------------------------------------------------------------- construction
def ids_bandes(bandes: list[dict]) -> None:
    """Identifiants stables : abréviation du type + rang de gauche à droite parmi les bandes de même abréviation."""
    rangs: dict[str, int] = {}
    for b in bandes:
        if b.get("id"):
            continue
        ab = ABREVIATIONS.get(b["type"], "b")
        rangs[ab] = rangs.get(ab, 0) + 1
        b["id"] = f"{ab}{rangs[ab]}"


def groupes_chaussee(bandes: list[dict]) -> list[list[int]]:
    """Suites contiguës d'indices de bandes au niveau chaussée."""
    out, cur = [], []
    for i, b in enumerate(bandes):
        if cle_niveau(b) == "chaussee":
            cur.append(i)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def reference(bandes: list[dict], decalage_sens_unique: float | None = None, bord: str = "gauche"):
    """(limite, decalage_m, prov) de la ligne de référence (RF-OSM-PRF-010) : séparation des sens (milieu du
    terre-plein éventuel) pour une route à double sens ; sinon bord gauche de la chaussée décalé de la demi-largeur
    (axe de la chaussée)."""
    arr = [i for i, b in enumerate(bandes) if b["type"] in VOIES_MOTORISEES and b["sens"] == "arriere"]
    ava = [i for i, b in enumerate(bandes) if b["type"] in VOIES_MOTORISEES and b["sens"] == "avant"]
    if arr and ava:
        ia, iv = max(arr), min(ava)
        if ia > iv:
            raise ErreurProfil("voie « ← » à droite d'une voie « → » : la circulation se fait à droite en France "
                               "(RF-OSM-PRF-002) ; vérifier l'ordre des bandes (de gauche à droite)")
        if iv == ia + 1:
            return iv, 0.0, P.inference("RF-OSM-PRF-010", note="séparation des sens")
        mil = sum(nombre(bandes[j]["largeur"]) for j in range(ia + 1, iv))
        return ia + 1, -mil / 2.0, P.inference("RF-OSM-PRF-010", note="milieu du terre-plein entre les deux sens")
    mot = [i for i, b in enumerate(bandes) if b["type"] in VOIES_MOTORISEES or b["type"] in ("piste_cyclable", "voie_verte")]
    if not mot:
        raise ErreurProfil("profil sans voie de circulation : ligne de référence indéterminée")
    groupes = groupes_chaussee(bandes) or [[i] for i in mot]
    g = next((g for g in groupes if mot[0] in g), [mot[0]])
    W = sum(nombre(bandes[j]["largeur"]) for j in g)
    if bord == "droite":     # bord droit fixe (la largeur varie à gauche : voie supprimée ou ajoutée, trottoir élargi)
        dec = W / 2.0 if decalage_sens_unique is None else decalage_sens_unique
        return g[-1] + 1, dec, P.inference("RF-OSM-PRF-010", note="sens unique : bord droit de la chaussée décalé de la "
                                                                 "demi-largeur initiale (bord fixe opposé à la variation)")
    dec = -W / 2.0 if decalage_sens_unique is None else decalage_sens_unique
    return g[0], dec, P.inference("RF-OSM-PRF-010", note="sens unique : bord gauche de la chaussée décalé de la demi-largeur")


def limite_deduite(i: int, bandes: list[dict], ctx: dict):
    """Limite i (entre bandes[i-1] et bandes[i]) déduite des niveaux et des types. (limite, avertissements)."""
    n = len(bandes)
    a = bandes[i - 1] if i > 0 else None
    b = bandes[i] if i < n else None
    if a is None or b is None:
        seule = a or b
        if cle_niveau(seule) == "chaussee" and seule["type"] in VOIES_MOTORISEES | {"bande_cyclable"} and not ctx["agglomeration"]:
            return limite_rive(ctx), []
        return {"nature": ["virtuelle"], "prov": {"*": P.inference("RF-OSM-PRF-001", note="rive extérieure du profil")}}, []
    da, db = a["_dz"], b["_dz"]
    ka, kb = cle_niveau(a), cle_niveau(b)
    if abs(da - db) > AFFLEURANT:
        return bordure_entre(a, b, da, db, ctx), []
    if a["type"] == "piste_cyclable" and b["type"] == "piste_cyclable" and a["sens"] != b["sens"]:
        return limite_marquage([marque("T'1", 2, ctx, "RF-OSM-CYC-002", u=regles.valeur("DEF-001", "piste_cyclable"))],
                               P.inference("RF-OSM-CYC-002", note="axe de piste bidirectionnelle T'1 2u, u = 0,03")), []
    if ka == "chaussee" and kb == "chaussee":
        groupe = next(g for g in groupes_chaussee(bandes) if i - 1 in g)
        return marquage_entre(a, b, [bandes[j] for j in groupe], ctx)
    if {ka, kb} & {"chaussee"} and ({ka, kb} & {"terrain"}):
        ch = a if ka == "chaussee" else b
        if ch["type"] in VOIES_MOTORISEES or ch["type"] == "bande_cyclable":
            return limite_rive(ctx), []
        return {"nature": ["changement_revetement"],
                "prov": {"*": P.inference("RF-OSM-MRQ-021", note="bord du revêtement (la rive est au bord de la voie)")}}, []
    if a["type"] == "piste_cyclable" and b["type"] == "piste_cyclable" and a["sens"] != b["sens"]:
        return limite_marquage([marque("T'1", 2, ctx, "RF-OSM-CYC-002", u=regles.valeur("DEF-001", "piste_cyclable"))],
                               P.inference("RF-OSM-CYC-002", note="axe de piste bidirectionnelle T'1 2u, u = 0,03")), []
    return {"nature": ["changement_revetement"],
            "prov": {"*": P.inference("RF-OSM-PRF-001", note=f"{a['type']} | {b['type']} au même niveau")}}, []


def raffiner_limite(lim: dict, exp: dict, bandes: list[dict], i: int, ctx: dict) -> dict:
    """Applique à la limite déduite ce que la description en dit (bordure, ligne, séparateur)."""
    lim = copy.deepcopy(lim)
    pv = exp["prov"]
    a = bandes[i - 1] if i > 0 else None
    b = bandes[i] if i < len(bandes) else None
    if exp.get("sans_bordure"):
        if "bordure" in lim["nature"]:
            raise ErreurProfil(f"« sans bordure » entre {a and a['id']} et {b and b['id']} alors que leurs niveaux "
                               "diffèrent : écrire « niveau chaussée » sur la bande haute")
        lim.setdefault("prov", {})["*"] = pv
    if "bordure" in exp and "bordure" not in lim["nature"] and a is not None and b is not None \
            and abs(a["_dz"] - b["_dz"]) > AFFLEURANT:
        # saut de niveau déduit comme séparateur (bande haute) : la description dit une bordure, on la pose
        lim = {"nature": ["bordure"], "bordure": {"profil": "autre", "vue_m": round(abs(a["_dz"] - b["_dz"]), 4),
                                                  "cote_haut": "gauche" if a["_dz"] > b["_dz"] else "droite"}, "prov": {}}
    if "bordure" in exp and exp.get("tolerante") and "bordure" not in lim["nature"]:
        exp = {k: v for k, v in exp.items() if k != "bordure"}      # la bande voisine a changé de niveau sur cette section
    if "bordure" in exp:
        if "bordure" not in lim["nature"]:
            raise ErreurProfil(f"bordure décrite entre {a and a['id']} et {b and b['id']}, deux bandes au même niveau : "
                               "préciser le niveau (« niveau trottoir ») ou retirer la bordure")
        bo = lim["bordure"]
        if "profil" in exp["bordure"] and exp["bordure"]["profil"] != bo.get("profil"):
            bo.pop("regle", None)
        bo.update(exp["bordure"])
        if bo.get("caniveau") and "cote" not in bo["caniveau"]:
            bo["caniveau"]["cote"] = "droite" if bo.get("cote_haut") == "gauche" else "gauche"
        lim["prov"] = {"bordure": pv}
    if "marquages" in exp:
        if exp["marquages"] == "aucune":
            nat = [x for x in lim["nature"] if x != "marquage"] or ["virtuelle"]
            lim = {k: v for k, v in lim.items() if k not in ("marquages", "x-opendrive")}
            lim["nature"] = nat
            lim["prov"] = dict(lim.get("prov") or {}, **{"*": pv})
        else:
            m = dict(exp["marquages"])
            if "largeur_u" in m:
                m.setdefault("u_m", ctx["u"])
            if ctx.get("usure_marquages") is not None:
                m["usure"] = ctx["usure_marquages"]
            ded = (lim.get("marquages") or [{}])[0]
            if ded.get("modulation") == m["modulation"] and ded.get("largeur_u") == m.get("largeur_u") and ded.get("regle"):
                m["regle"] = ded["regle"]          # ligne décrite = ligne que la règle pose : la règle reste citée
            elif ded.get("regle"):
                ctx.setdefault("_ecarts", []).append(
                    f"ligne décrite {m['modulation']} {m.get('largeur_u', m.get('largeur_m'))} entre {a and a['id']} et "
                    f"{b and b['id']} ; la règle {ded['regle']} poserait {ded['modulation']} {ded.get('largeur_u')}u")
            nat = [x for x in lim["nature"] if x not in ("virtuelle", "changement_revetement")]
            if "marquage" not in nat:
                nat.append("marquage")
            lim["nature"] = nat
            lim["marquages"] = [m]
            lim["x-opendrive"] = _xodr([m])
            lim["prov"] = dict(lim.get("prov") or {}, marquages=pv)
            lim["prov"].pop("*", None)
    if "separateur" in exp:
        nat = [x for x in lim["nature"] if x not in ("virtuelle",)]
        if "separateur" not in nat:
            nat.append("separateur")
        lim["nature"] = nat
        lim["separateur"] = exp["separateur"]
        lim["prov"] = dict(lim.get("prov") or {}, separateur=pv)
        lim["prov"].pop("*", None)
    return lim


def construire_profil(pid: str, bandes_in: list[dict], limites_in: list | None, ctx: dict, nom: str | None = None,
                      decalage_sens_unique: float | None = None, bord_reference: str = "gauche"):
    """Profil complet. Retourne (profil, avertissements, controles)."""
    bandes = copy.deepcopy(bandes_in)
    n = len(bandes)
    limites_in = list(limites_in) if limites_in else [None] * (n + 1)
    if len(limites_in) != n + 1:
        raise ErreurProfil(f"{len(limites_in)} limites pour {n} bandes")
    av, ctrl = [], []
    ids_bandes(bandes)
    # largeurs
    for b in bandes:
        b.setdefault("prov", {})
        if b.get("largeur") is None:
            b["largeur"], b["prov"]["largeur"] = largeur_defaut(b, bandes, ctx)
    # niveaux
    dzs = []
    for b in bandes:
        dz, pdz = niveau_dz(b, ctx)
        dzs.append(dz)
        b["_dz"], b["_pdz"] = dz, pdz
    # dévers : par groupe de chaussée (toit à la séparation des sens, sinon pente unique vers l'extérieur du sens)
    devers = {}
    pc = regles.valeur("DEF-006", "chaussee_pct")
    for g in groupes_chaussee(bandes):
        sens = {bandes[i]["sens"] for i in g if bandes[i]["type"] in VOIES_MOTORISEES}
        if {"avant", "arriere"} <= sens:
            ia = max(i for i in g if bandes[i]["type"] in VOIES_MOTORISEES and bandes[i]["sens"] == "arriere")
            iv = min(i for i in g if bandes[i]["type"] in VOIES_MOTORISEES and bandes[i]["sens"] == "avant")
            for i in g:
                if ia < i < iv:
                    # bande de séparation des sens au niveau de la chaussée (zone hachurée…) : crête du toit à plat
                    # (RF-OSM-NIV-011 : crête sur la séparation des sens) ; les voies partent de ses rives au même
                    # niveau qu'au droit d'un îlot bordé de même largeur (correction après contrôle : marche de 2 cm à
                    # travers la chaussée aux bouts de l'îlot de S_M24)
                    devers[i] = (0.0, "toit", P.defaut("DEF-006", note="séparation des sens : crête du toit à plat",
                                                       par="RF-OSM-NIV-011"))
                else:
                    devers[i] = (-pc if i <= ia else pc, "toit", P.defaut("DEF-006", note="dévers de chaussée en toit"))
        else:
            sgn = -1.0 if sens == {"arriere"} else 1.0
            for i in g:
                devers[i] = (sgn * pc, "plan", P.defaut("DEF-006", note="dévers de chaussée à pente unique"))
    # accotements hors agglomération (RF-GV-DEV-001, ARP p. 46 : chaussée interurbaine, alignement ou courbe non
    # déversée) : bande dérasée stabilisée 4 %, berme 8 %, vers l'extérieur de la chaussée ; la surlargeur revêtue
    # (accotement_revetu) reste au dévers de la chaussée (partie revêtue, porte la rive : RF-OSM-LAR-014) ; en
    # agglomération, la règle ne s'applique pas (pas d'autre règle : dévers de la chaussée ou plan, comme avant)
    voies_idx = [j for j in range(n) if bandes[j]["type"] in VOIES_MOTORISEES]
    if voies_idx and not ctx.get("agglomeration", True):
        for i, b in enumerate(bandes):
            cle = {"bande_derasee": "BDD_stabilisee_pct", "berme": "berme_pct"}.get(b["type"])
            if cle is None or min(voies_idx) < i < max(voies_idx):
                continue
            v = regles.valeur("RF-GV-DEV-001", cle)
            vers_droite = i > max(voies_idx)
            devers[i] = (v if vers_droite else -v, "plan",
                         P.defaut("RF-GV-DEV-001", note=f"{b['type']} : {v} % vers l'extérieur de la chaussée"))
    # dévers dit par la description (« dévers 0 », structuré « devers: 0 ») : remplace le dévers déduit (liaison revêtue
    # raccordée au niveau de ses voisines d'une autre section : traversée d'un accotement au droit d'un passage)
    for i, b in enumerate(bandes):
        dv = (b.get("attributs") or {}).get("devers_pct")
        if dv is not None:
            devers[i] = (float(dv), "plan", b["prov"].get("niveau.devers_pct") or P.description("profil", note="dévers dit"))
    chaussee_idx = [j for j in range(n) if cle_niveau(bandes[j]) == "chaussee"]
    for i, b in enumerate(bandes):
        k = cle_niveau(b)
        niv = {"reference": "chaussee" if k == "chaussee" else ("trottoir" if k in ("trottoir", "quai", "intermediaire") else "propre"),
               "dz_m": b["_dz"]}
        pn = b["_pdz"]
        pdev = None
        if i in devers:
            niv["devers_pct"] = devers[i][0]
            if devers[i][1] == "toit":
                niv["forme"] = "toit"
            pdev = devers[i][2]
        elif k in ("trottoir", "quai") and b["type"] in ("trottoir", "quai_bus") and chaussee_idx:
            # pente vers la chaussée la plus proche (+ = descend vers la droite)
            dg = min((i - j for j in chaussee_idx if j < i), default=None)
            dd = min((j - i for j in chaussee_idx if j > i), default=None)
            vers_droite = dg is None or (dd is not None and dd <= dg)
            v = regles.valeur("RF-MA-BUS-011", "devers_vise_pct") if k == "quai" else regles.valeur("DEF-006", "trottoir_pct")
            niv["devers_pct"] = v if vers_droite else -v
            pdev = (P.defaut("RF-MA-BUS-011", note="dévers visé du quai") if k == "quai"
                    else P.defaut("DEF-006", note="dévers de trottoir vers la chaussée"))
        b["niveau"] = niv
        b["prov"]["niveau"] = pn
        if pdev is not None and "niveau.devers_pct" not in b["prov"]:
            b["prov"]["niveau.devers_pct"] = pdev
    # identifiants de la ligne de référence
    lim_ref, dec_ref, prov_ref = reference(bandes, decalage_sens_unique, bord_reference)
    # matériaux
    for b in bandes:
        if b.get("materiau_id") is None:
            mid, pm = materiau_defaut(b, ctx)
            if mid:
                b["materiau_id"] = mid
                b["prov"]["materiau_id"] = pm or P.table("surface_vers_materiau")
    # limites
    limites = []
    for i in range(n + 1):
        exp = limites_in[i]
        if exp is not None and not exp.get("raffiner"):
            limites.append(copy.deepcopy(exp))          # limite complète donnée (inférence OSM)
            continue
        lim, w = limite_deduite(i, bandes, ctx)
        av += w
        if exp is not None:
            lim = raffiner_limite(lim, exp, bandes, i, ctx)
        limites.append(lim)
    av += ctx.pop("_ecarts", [])
    # contrôles de structure
    for i in range(n - 1):
        a, b = bandes[i], bandes[i + 1]
        if {a["type"], b["type"]} & {"piste_cyclable"} and ({a["type"], b["type"]} & VOIES_MOTORISEES):
            av.append(f"piste cyclable {a['id'] if a['type'] == 'piste_cyclable' else b['id']} accolée à une voie "
                      "de circulation sans séparateur (RF-MA-PIS-006)")
            ctrl.append({"controle": "piste_non_contigue", "bandes": [a["id"], b["id"]], "regle": "RF-MA-PIS-006", "statut": "non_conforme"})
    ctrl += controles_largeurs(bandes, ctx)
    # objets le long : figurines vélo des bandes cyclables (DEF-018)
    for b in bandes:
        if b["type"] == "bande_cyclable" and not any(o.get("type") == "figurine_velo" for o in b.get("objets_le_long", [])):
            b.setdefault("objets_le_long", []).append({
                "id": f"fig_{b['id']}", "famille": "symbole_sol", "type": "figurine_velo", "gabarit": "VELO",
                "mode": "pas", "pas_m": regles.valeur("DEF-018"), "ancrage": {"reference": "centre", "decalage_m": 0.0},
                "orientation": {"mode": "tangent"},
                "exclusions": [{"type": "passage_pieton"}, {"type": "carrefour"}, {"type": "arret_bus"}],
                "regles": ["DEF-018", "RF-OSM-CYC-001", "RF-MA-CYC-012"]})
            b["prov"]["objets_le_long"] = P.defaut("DEF-018", note="figurines vélo au pas de 50 m")
    # vitesse sur les voies
    for b in bandes:
        if b["type"] in VOIES_MOTORISEES and ctx.get("vitesse_kmh") is not None:
            b["vitesse_kmh"] = ctx["vitesse_kmh"]
            b["prov"]["vitesse_kmh"] = ctx.get("prov_vitesse") or P.solveur("vitesse")
    profil = {"id": pid}
    if nom:
        profil["nom"] = nom
    profil["bandes"] = [bande_schema(b) for b in bandes]
    profil["limites"] = limites
    profil["reference"] = {"limite": lim_ref}
    if abs(dec_ref) > 1e-12:
        profil["reference"]["decalage_m"] = round(dec_ref, 4)
    profil["u_m"] = ctx["u"]
    profil["agglomeration"] = ctx["agglomeration"]
    regles_profil = ["RF-OSM-PRF-001", "RF-OSM-PRF-002", "RF-OSM-PRF-010"]
    profil["regles"] = regles_profil
    profil["prov"] = {"u_m": ctx.get("prov_u") or P.defaut("DEF-001"), "reference": prov_ref,
                      "agglomeration": ctx.get("prov_agglomeration") or P.solveur("agglomeration")}
    return profil, av, ctrl


CHAMPS_BANDE = ("id", "type", "sous_type", "sens", "usagers", "largeur", "largeur_min_m", "materiau_id", "niveau",
                "vitesse_kmh", "stationnement", "cyclable", "terre_plein", "objets_le_long", "tags_graphe",
                "x-opendrive", "prov")


def bande_schema(b: dict) -> dict:
    """Bande interne → bande du schéma (champs connus seulement, dans l'ordre du schéma)."""
    d = dict(b)
    d.setdefault("usagers", USAGERS.get(b["type"], []))
    if not d["usagers"]:
        d.pop("usagers")
    if b["type"] in TAGS_GRAPHE:
        d.setdefault("tags_graphe", TAGS_GRAPHE[b["type"]])
    elif b["type"] in VOIES_MOTORISEES:
        d.setdefault("tags_graphe", ["vehicule"])
    d.setdefault("x-opendrive", {"lane_type": LANE_TYPE.get(b["type"], "driving")})
    pv = dict(d.get("prov") or {})
    pv.setdefault("*", pv.get("largeur"))
    d["prov"] = {k: pv[k] for k in sorted(pv, key=lambda k: (k != "*", k))}
    return {k: d[k] for k in CHAMPS_BANDE if k in d and d[k] is not None}


# ---------------------------------------------------------------------------------------------------- contrôles
PLAGES = {  # type → (règle, chemin min, chemin max, condition)
    "bande_cyclable": [("RF-OSM-LAR-030", "min", "max")],
    "voie_bus": [("RF-OSM-LAR-013", "min", "max")],
    "zone_neutralisee:tampon_emportierage": [("RF-OSM-LAR-032", "min", "max")],
    "separateur": [("RF-OSM-LAR-033", "largeur_min", "largeur_max")],
}


def controles_largeurs(bandes: list[dict], ctx: dict) -> list[dict]:
    """Largeurs comparées aux plages des règles (valeur / plage / statut). Les écarts ne bloquent pas : une
    description dit ce qui existe ; ils sont rapportés."""
    out = []

    def ajoute(b, regle, lo, hi):
        w = nombre(b["largeur"])
        ok = (lo is None or w >= lo - 1e-9) and (hi is None or w <= hi + 1e-9)
        out.append({"controle": "largeur", "bande": b["id"], "type": b["type"], "valeur": round(w, 3),
                    "plage": [lo, hi], "regle": regle, "statut": "conforme" if ok else "hors_plage"})

    sens_unique = not ({"avant", "arriere"} <= {b["sens"] for b in bandes if b["type"] in VOIES_MOTORISEES})
    for b in bandes:
        t = b["type"]
        if isinstance(b["largeur"], dict):
            continue      # bande en transition (biseau) : pas de contrôle de largeur courante
        if t == "voie_circulation" and ctx["agglomeration"]:
            meme = sum(1 for x in bandes if x["type"] == t and x["sens"] == b["sens"])
            if meme >= 2:
                ajoute(b, "RF-OSM-LAR-012", regles.valeur("RF-OSM-LAR-012", "meme_sens_min"), regles.valeur("RF-OSM-LAR-012", "meme_sens_max"))
            elif sens_unique:
                ajoute(b, "RF-OSM-LAR-011", regles.valeur("RF-OSM-LAR-011", "min"), regles.valeur("RF-OSM-LAR-011", "max"))
            else:
                ajoute(b, "RF-OSM-LAR-010", regles.valeur("RF-OSM-LAR-010", "min"), regles.valeur("RF-OSM-LAR-010", "max"))
        elif t == "trottoir":
            ajoute(b, "RF-MA-TRO-001", regles.valeur("RF-MA-TRO-001", "min"), None)
        elif t == "piste_cyclable" and not (b.get("attributs") or {}).get("demi_piste"):
            ajoute(b, "RF-MA-PIS-001", regles.valeur("RF-MA-PIS-001", "minimum_absolu_Paris_Lyon"), None)
        elif t == "stationnement" and (b.get("stationnement") or {}).get("orientation", "longitudinal") == "longitudinal":
            ajoute(b, "RF-OSM-LAR-040", regles.valeur("RF-OSM-LAR-040", "largeur_min"), regles.valeur("RF-OSM-LAR-040", "largeur_max"))
        elif t == "terre_plein" and (b.get("terre_plein") or {}).get("plantation"):
            ajoute(b, "RF-OSM-LAR-050", regles.valeur("RF-OSM-LAR-050", "tpc_plante_min"), regles.valeur("RF-OSM-LAR-050", "tpc_plante_max"))
        else:
            cle = f"{t}:{b.get('sous_type')}" if f"{t}:{b.get('sous_type')}" in PLAGES else t
            for regle, mn, mx in PLAGES.get(cle, []):
                ajoute(b, regle, regles.valeur(regle, mn), regles.valeur(regle, mx))
    return out


def resume(profil: dict) -> dict:
    """Résumé comparable d'un profil (tests) : bandes (type, sens, largeur) et limites (nature, marque / bordure)."""
    bd = [[b["type"], b["sens"], round(nombre(b["largeur"]), 3)] for b in profil["bandes"]]
    li = []
    for l in profil["limites"]:
        if "marquage" in l["nature"]:
            m = l["marquages"][0]
            li.append(f"{m['modulation']} {m.get('largeur_u', m.get('largeur_m'))}{'u' if 'largeur_u' in m else 'm'}")
        elif "bordure" in l["nature"]:
            li.append(f"bordure {l['bordure']['profil']} {l['bordure'].get('vue_m')}")
        elif "separateur" in l["nature"]:
            li.append(f"separateur {l['separateur']['type']}")
        else:
            li.append(l["nature"][0])
    return {"bandes": bd, "limites": li, "reference": profil["reference"]}
