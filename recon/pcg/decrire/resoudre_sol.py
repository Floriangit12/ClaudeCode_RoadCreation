"""Résolution des familles de sol (surfaces, îlots, bordures, ponctuels) du schéma 0.3.

- surfaces / îlots : mises à jour d'attributs prouvées (FUS-ATT-06 « appliquer ») dans le domaine du schéma
  (materiau_id de la table, classes de surface) ; la provenance est écrite dans prov (src regle:resolution.*) ;
- bordures : aucune modification géométrique ou de profil (retraits de doublons et vues contestées listés pour
  le propriétaire de bordures.py) ;
- la partition des surfaces n'est jamais modifiée (ajouts de surfaces listés).
"""
import numpy as np

from commun import MATERIAUX, anneaux, arrondi, lire_json, repere
import resoudre_regles as RR

CLASSES_SURFACE = {"chaussee", "piste_cyclable", "trottoir", "ilot", "terre_plein_vegetal", "espace_vert", "quai_bus",
                   "parking", "acces_riverain", "chantier", "autre", "emprise_bordure"}
MATERIAUX_SOL = None


def _materiaux():
    global MATERIAUX_SOL
    if MATERIAUX_SOL is None:
        MATERIAUX_SOL = set(lire_json(MATERIAUX)["materiaux"])
    return MATERIAUX_SOL


def _paires(c):
    if isinstance(c[0], (int, float)):
        return [c[:2]]
    return [q for x in c for q in _paires(x)]


def _centre(f):
    g = f["geometry"]
    if g["type"] in ("Polygon", "MultiPolygon"):
        R = repere(anneaux(g)[0][0])
        return [float(R[:, 0].mean()), float(R[:, 1].mean())]
    c = repere(np.asarray(_paires(g["coordinates"]), float)).mean(axis=0)
    return [float(c[0]), float(c[1])]


def _prov(p, cle, m, note):
    obs = m.get("obs_strictes") or m.get("obs", [])
    p.setdefault("prov", {})[cle] = {"src": "regle:resolution.RES-ATT-001",
                                     "ref": f"fusion 0.3 ({', '.join(obs)}) : {note}"[:400],
                                     "conf": m.get("conf") if m.get("conf") in ("haute", "moyenne", "faible") else "moyenne"}


def _resolution_texte(p, d):
    """Les surfaces et îlots n'admettent pas de propriété libre : la décision est résumée dans prov."""
    return d


class ResolveurSol:
    def __init__(self, S, J, bloques=frozenset()):
        self.S, self.J = S, J
        self.surf = S.index_base("surfaces")
        self.ilots = S.index_base("ilots")
        self.bord = S.index_base("bordures")
        self.bloques = bloques

    def attributs(self):
        mats = _materiaux()
        for ft in sorted(self.S.attributs, key=lambda f: f["properties"]["id"]):
            q = ft["properties"]
            ident, fam = q["id"], q["famille"]
            if fam == "surfaces_v1":
                for a in sorted(q["maj"]):
                    self.J.non_resolu(ident, "surfaces", f"attribut:{a}", origine="schema", xy=None,
                                      regles=["RES-ATT-001"], observations=q["maj"][a].get("obs", []),
                                      motif=f"entité v1 {ident} absente de la description 0.3 (valeur {q['maj'][a]['apres']!r})")
                continue
            if fam not in ("surfaces", "ilots"):
                continue
            idx = self.surf if fam == "surfaces" else self.ilots
            f = idx.get(ident)
            if f is None:
                continue
            p = f["properties"]
            xy = _centre(f)
            maj = q["maj"]
            for a in sorted(maj):
                m = maj[a]
                regles = ["RES-ATT-001"] + [r.strip() for r in m.get("regle", "").split(";") if r.strip()]
                obs = m.get("obs_strictes") or m.get("obs", [])
                if m.get("decision") != "appliquer":
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="incertain", xy=xy, regles=regles,
                                      observations=m.get("obs", []), classe=p.get("classe") or p.get("type"),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=f"mise à jour {a} en revue (FUS-ATT-06)")
                    continue
                if ident in self.bloques:
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="validation", xy=xy, regles=regles,
                                      observations=obs, classe=p.get("classe") or p.get("type"),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif="mise à jour retirée : la description résolue ne passait plus valider.py")
                    continue
                if m.get("conf") not in RR.CONFIANCES_PROBANTES:
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="incertain", xy=xy, regles=regles,
                                      observations=m.get("obs", []), classe=p.get("classe") or p.get("type"),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=f"valeur {m.get('apres')!r} de confiance {m.get('conf')} (< moyenne)")
                    continue
                v = m["apres"]
                ok = (a == "materiau_id" and v in mats) or (a == "classe" and v in CLASSES_SURFACE and fam == "surfaces") or \
                     (a == "etat_v1" and isinstance(v, str) and fam == "surfaces")
                if not ok:
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="schema", xy=xy, regles=regles, observations=obs,
                                      classe=p.get("classe") or p.get("type"),
                                      proposition={"avant": m.get("avant"), "apres": v},
                                      motif=f"valeur {v!r} hors du domaine de {a} (table des matériaux / enum du schéma 0.3)")
                    continue
                if fam == "surfaces" and a == "materiau_id":
                    avant = p["revetement"]["materiau_id"]
                    p["revetement"]["materiau_id"] = v
                    note = f"materiau_id {avant} -> {v}"
                    if v == "enrobe_bbsg_neuf_2025" and p["revetement"].get("age") != "neuf_2025":
                        note += f" ; age {p['revetement'].get('age')} -> neuf_2025"
                        p["revetement"]["age"] = "neuf_2025"
                    _prov(p, "revetement", m, note)
                elif fam == "ilots" and a == "materiau_id":
                    avant = p["remplissage"]["materiau_id"]
                    p["remplissage"]["materiau_id"] = v
                    note = f"remplissage {avant} -> {v}"
                    _prov(p, "remplissage", m, note)
                elif a == "classe":
                    avant = p["classe"]
                    p["classe"] = v
                    note = f"classe {avant} -> {v}"
                    _prov(p, "classe", m, note)
                else:
                    avant = p.get("etat_v1")
                    p["etat_v1"] = v
                    note = f"etat_v1 {avant} -> {v}"
                    _prov(p, "etat_v1", m, note)
                self.J.appliquer(ident, fam, "attribut", avant={a: avant}, apres={a: v}, regles=regles, observations=obs,
                                 conf=m.get("conf") or "moyenne", xy_avant=xy, xy_apres=xy,
                                 portee=0.1 + min(float(p.get("aire_m2") or 0.0), 1500.0) / 1500.0,
                                 classe=p.get("classe") or p.get("type"), motif=note)

    def bordures(self):
        """Décisions de la fusion sur les bordures : jamais appliquées (géométrie et profils), listées."""
        for ident in sorted(self.S.entites):
            e = self.S.entites[ident]
            if e["famille"] != "bordures" or ident not in self.bord:
                continue
            f = self.bord[ident]
            xy = _centre(f)
            if e["existence"] in ("retirer", "absent_2026") and e["statut_verification"] in ("a_retirer", "absent_2026"):
                refs = sorted({s for s, g in self.surf.items() if any(b["bordure"] == ident for b in g["properties"]["bords"])}
                              | {i for i, g in self.ilots.items() if ident in g["properties"]["ceinture"]})
                self.J.non_resolu(ident, "bordures", "retrait", origine="schema", xy=xy,
                                  regles=["RES-EXI-001"] + e["regles"], observations=e["preuve_stricte"]["obs"],
                                  motif=f"retrait prouvé ({e['existence']}) mais référencé par {', '.join(refs) or 'aucune entité'} : "
                                        f"à faire par le propriétaire de bordures.py / surfaces.py (partition)")
            if e.get("bordure_contradictions"):
                for it, v in sorted(e["bordure_contradictions"].items()):
                    if v == "a_verifier":
                        self.J.non_resolu(ident, "bordures", f"vue_intervalle_{it}", origine="conflit", xy=xy,
                                          regles=["RES-BOR-001", "FUS-BOR-03"], observations=e["obs"],
                                          motif=f"vue observée contredisant le profil de l'intervalle {it} : relevé terrain "
                                                f"(photo rasante, mètre pliant) avant tout changement")
        for ft in sorted(self.S.corr_pos, key=lambda f: f["properties"]["id"]):
            q = ft["properties"]
            if q["famille"] == "bordures" and q["id"] in self.bord:
                self.J.non_resolu(q["id"], "bordures", "position_fusion", origine="incertain", xy=_centre(self.bord[q["id"]]),
                                  regles=["RES-POS-002"] + q.get("regles", []), observations=q.get("obs", []),
                                  proposition={"d_m": q["d_m"], "vecteur_m": q.get("vecteur_m")},
                                  motif=f"translation {q['d_m']} m ({q['decision']}) : " + "; ".join(q.get("raisons", [])))

    def conflits(self, xy_objets=None):
        """Conflits « à vérifier » de la fusion non couverts par une autre entrée du journal."""
        idx = {}
        for fam in ("bordures", "surfaces", "ilots", "ponctuels_sol", "marquages"):
            for i, f in self.S.index_base(fam).items():
                idx[i] = (fam, f)
        for c in sorted(self.S.conflits, key=lambda c: c["id"]):
            if c.get("gravite") != "a_verifier":
                continue
            cible = c.get("cible")
            fam, f = idx.get(cible, ("objets", None))
            xy = _centre(f) if f is not None else (xy_objets or {}).get(cible)
            self.J.non_resolu(cible or c["id"], fam, f"conflit:{c['type']}", origine="conflit", xy=xy,
                              regles=["RES-NRE-001"], observations=c.get("obs", []),
                              motif=f"{c['id']} : {c.get('detail', '')[:260]} — {c.get('recommandation', '')[:160]}")

    def executer(self, xy_objets=None):
        self.attributs()
        self.bordures()
        self.conflits(xy_objets)
