# -*- coding: utf-8 -*-
"""Nivellement analytique de référence du lot L2 (contrôles indépendants de rg::nivellement et de rg::sol).

Aucun code commun avec les HDA (VEX) : ce module relit le modèle `modele_voie/0.1`, les cotes des profils de bordure
et de caniveau (assets/specs/bordures.json, autre équipe, lecture seule) et la géométrie analytique du lot L1
(`analytique_L1` : référence, lois de largeur, limites, loi verticale), puis recalcule le Z attendu en (s, t) selon
l'ordre de TQ-SOL-013 :
  (1) chaussée : groupes de bandes basses continues ancrés à Z = 0 sur la ligne de référence (t = 0), ou à leur
      limite la plus proche ; dévers de chaque bande (+ = descend vers la droite) ; + dz(s) des ralentisseurs
      (plateau, dos-d'âne, d'un trottoir à l'autre) ;
  (3) caniveau : arête côté chaussée au Z de la chaussée, fil d'eau = arête − (h côté chaussée − h côté bordure) ;
  (4) pied = fil d'eau (sinon chaussée au droit de la face), hors ralentisseur ;
  (5) tête = pied + vue (abaissés : vue réduite et rampants linéaires ; abaissé couvert par un ralentisseur : non) ;
  (6) trottoir et bandes hautes : tête − 4 mm à l'arrière de la bordure, puis dévers ; (7) bande plantée isolée entre
      deux bordures : tête − 4 cm ; bande haute sans dévers : plan entre ses appuis, sinon horizontale ;
  bordure « virtuelle » : même paire de bandes bordée dans une autre section (avancées : niveau du trottoir gardé).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import analytique_L1 as A1

DEPOT = Path(__file__).resolve().parents[3]
RETRAIT_TROTTOIR = 0.004        # TQ-SOL-013 (6)
RETRAIT_PLANTE = 0.04           # TQ-SOL-013 (7) : 3 à 5 cm
VEGETAUX = {"gazon_tondu", "gazon_sec", "herbe_haute", "terre_nue", "paillage_mineral", "brf_bois_concasse",
            "brf_bois_gris", "noue_plantee"}


def profils_bordures():
    """{profil: (base, H, Δh caniveau)} depuis assets/specs/bordures.json (+ chanfreins de bordures_elements.json
    sans effet sur base et H)."""
    b = json.loads((DEPOT / "assets/specs/bordures.json").read_text(encoding="utf-8"))["profils"]
    out = {}
    for k, v in b.items():
        c = v.get("contour")
        if not c:
            continue
        base = max(p[0] for p in c)
        H = max(p[1] for p in c)
        dh = 0.0
        if "h_cote_chaussee" in v and "h_cote_bordure" in v:
            dh = float(v["h_cote_chaussee"]) - float(v["h_cote_bordure"])
        out[k] = (float(base), float(H), dh)
    return out


class Route:
    def __init__(self, modele: dict, rid: str, rampe_pct: float = 7.0):
        self.m = modele
        self.rid = rid
        self.route = next(r for r in modele["routes"] if r["id"] == rid)
        self.origine = modele["repere"]["origine_l93"][:2]
        self.ref = A1.Reference(self.route, self.origine)
        self.L = self.ref.L
        self.prof = {p["id"]: p for p in modele["profils"]}
        self.secs = self.route["sections"]
        self.rampe = rampe_pct
        self.objets = modele.get("objets", [])
        self.pb = profils_bordures()
        self.ral = [(float(o["rattachement"]["s"]) - float(o["dimensions"]["longueur_m"]) / 2,
                     float(o["rattachement"]["s"]) + float(o["dimensions"]["longueur_m"]) / 2)
                    for o in self.objets if (o.get("rattachement") or {}).get("route") == rid
                    and o.get("type") in ("plateau", "dos_d_ane")]
        self.abords = {"gauche": (0.0, None), "droite": (0.0, None)}
        for z in modele.get("zones", []):
            at = z.get("attributs") or {}
            if z.get("type") in ("espace_vert", "friche", "champ", "massif", "parking", "foret", "haie") and at.get("cote"):
                self.abords[at["cote"]] = (float(at.get("largeur_m", 0.0)), at.get("materiau_id"))
        # bordures réelles de toutes les sections (paires de bandes)
        self.reelles = []
        for k, sc in enumerate(self.secs):
            p = self.prof[sc["profil"]]
            ids = [b["id"] for b in p["bandes"]]
            for l, lim in enumerate(p["limites"]):
                if 0 < l < len(ids) and "bordure" in lim:
                    self.reelles.append((k, ids[l - 1], ids[l], lim["bordure"]))

    # -------------------------------------------------------------------------------------------- sections
    def section(self, s: float) -> int:
        k = 0
        for i, sc in enumerate(self.secs):
            if sc["s0"] <= s + 1e-9:
                k = i
        return k

    def profil(self, k: int) -> dict:
        return self.prof[self.secs[k]["profil"]]

    @staticmethod
    def haute(b: dict) -> bool:
        n = b.get("niveau") or {}
        return n.get("reference") in ("trottoir", "propre") and float(n.get("dz_m", 0.0)) > 1e-6

    def dz(self, s: float) -> float:
        return A1.dz_chaussee(self.objets, self.rid, s, self.rampe)

    def bordure_effective(self, k: int, l: int):
        """(bordure dict, réelle 1 | virtuelle 2) de la limite l de la section k, sinon (None, 0)."""
        p = self.profil(k)
        lim = p["limites"][l]
        if "bordure" in lim:
            return lim["bordure"], 1
        if l == 0 or l == len(p["bandes"]):
            return None, 0
        g, d = p["bandes"][l - 1]["id"], p["bandes"][l]["id"]
        best = None
        for kk, gg, dd, bo in self.reelles:
            if gg != g or dd != d:
                continue
            hb = p["bandes"][l - 1] if bo["cote_haut"] == "gauche" else p["bandes"][l]
            if not self.haute(hb):
                continue
            if best is None or abs(kk - k) < best[0]:
                best = (abs(kk - k), bo)
        return (best[1], 2) if best else (None, 0)

    def vue(self, bo: dict, s: float) -> float:
        v = float(bo["vue_m"])
        for a in bo.get("abaisses", []) or []:
            s0, s1, va, r = float(a["s0"]), float(a["s1"]), float(a.get("vue_m", 0.02)), float(a.get("rampant_m", 0.0))
            if any(s1 > r0 and s0 < r1 for r0, r1 in self.ral):
                continue                                # abaissé réalisé par le ralentisseur
            if s0 <= s <= s1:
                w = va
            elif s < s0:
                w = v if s <= s0 - r else va + (v - va) * (s0 - s) / max(r, 1e-9)
            else:
                w = v if s >= s1 + r else va + (v - va) * (s - s1) / max(r, 1e-9)
            v = min(v, w)
        return v

    def caniveau_pose(self, s: float) -> bool:
        return not any(r0 < s < r1 for r0, r1 in self.ral)

    # -------------------------------------------------------------------------------------------- coupe
    def coupe(self, s: float, k: int | None = None) -> dict:
        """Coupe en travers en s (section k) : T, plans des bandes (a, g : Z = a + g·t, sans dz), classes, bordures
        (pied, tête, vue), dz."""
        if k is None:
            k = self.section(s)
        p = self.profil(k)
        B = p["bandes"]
        n = len(B)
        T = A1.t_limites(p, s)
        dz = self.dz(s)
        cls = [1 if self.haute(b) else 0 for b in B]
        dev = [(b.get("niveau") or {}).get("devers_pct") for b in B]
        a = [None] * n
        g = [None] * n
        bord = [self.bordure_effective(k, l) for l in range(n + 1)]
        # (1) groupes bas
        i = 0
        while i < n:
            if cls[i]:
                i += 1
                continue
            j = i
            while j + 1 < n and cls[j + 1] == 0 and bord[j + 1][1] != 1:
                j += 1
            if T[j + 1] <= 1e-9 and T[i] >= -1e-9:
                ba = next(c for c in range(i, j + 1) if T[c + 1] <= 1e-9 and T[c] >= -1e-9)
                ta = 0.0
            else:
                lmin = min(range(i, j + 2), key=lambda l: abs(T[l]))
                ba = lmin if lmin <= j else j
                ta = T[lmin]
            g[ba] = (dev[ba] or 0.0) / 100.0
            a[ba] = -g[ba] * ta
            for c in range(ba + 1, j + 1):
                z = a[c - 1] + g[c - 1] * T[c]
                g[c] = (dev[c] or 0.0) / 100.0
                a[c] = z - g[c] * T[c]
            for c in range(ba - 1, i - 1, -1):
                z = a[c + 1] + g[c + 1] * T[c + 1]
                g[c] = (dev[c] or 0.0) / 100.0
                a[c] = z - g[c] * T[c + 1]
            i = j + 1
        # (2) bordures : pied, tête ; appuis des bandes hautes
        bords = {}
        appuis = {c: [] for c in range(n)}
        for l in range(1, n):
            bo, nat = bord[l]
            if not bo:
                continue
            h = 1 if bo["cote_haut"] == "gauche" else -1
            hb = l - 1 if h > 0 else l
            rng = range(l, n) if h > 0 else range(l - 1, -1, -1)
            bb = next((c for c in rng if cls[c] == 0 and a[c] is not None), None)
            if bb is None or not cls[hb]:
                if nat == 1:
                    raise ValueError(f"{self.rid} s={s} : bordure {l} sans bande basse ou haute")
                continue
            base, H, dh = self.pb[bo["profil"]]
            can = (bo.get("caniveau") or {}).get("profil")
            if can and can != "aucun":
                wc, _, dhc = self.pb[can]
                pied = a[bb] + g[bb] * (T[l] - h * wc) - dhc
            else:
                wc, dhc = 0.0, 0.0
                pied = a[bb] + g[bb] * T[l]
            v = self.vue(bo, s) if nat == 1 else float(bo["vue_m"])
            bords[l] = {"pied": pied, "tete": pied + v, "vue": v, "h": h, "base": base, "H": H, "wc": wc, "dhc": dhc,
                        "nature": nat, "bande_basse": bb, "bande_haute": hb}
        # retraits (TQ-SOL-013 (6), (7))
        ret = []
        for c in range(n):
            b = B[c]
            plante = (b["type"] in ("terre_plein", "bande_plantee") and b.get("materiau_id") in VEGETAUX
                      and bord[c][1] == 1 and bord[c + 1][1] == 1)
            ret.append(RETRAIT_PLANTE if plante else RETRAIT_TROTTOIR)
        for l, d in bords.items():
            appuis[d["bande_haute"]].append((T[l] + d["h"] * d["base"], d["tete"] - ret[d["bande_haute"]]))
        # (3) bandes hautes
        for _ in range(2 * n + 2):
            change = False
            for repli in (False, True):
                for c in range(n):
                    if a[c] is not None or not cls[c]:
                        continue
                    cs = list(appuis[c])
                    if c > 0 and a[c - 1] is not None and bord[c][1] != 1 and cls[c - 1]:
                        cs.append((T[c], a[c - 1] + g[c - 1] * T[c]))
                    if c + 1 < n and a[c + 1] is not None and bord[c + 1][1] != 1 and cls[c + 1]:
                        cs.append((T[c + 1], a[c + 1] + g[c + 1] * T[c + 1]))
                    if not cs:
                        continue
                    if dev[c] is not None:
                        g[c] = dev[c] / 100.0
                        a[c] = cs[0][1] - g[c] * cs[0][0]
                    elif len(cs) >= 2:
                        (t0, z0), (t1, z1) = max(((x, y) for x in cs for y in cs), key=lambda q: abs(q[0][0] - q[1][0]))
                        g[c] = 0.0 if abs(t1 - t0) < 1e-6 else (z1 - z0) / (t1 - t0)
                        a[c] = z0 - g[c] * t0
                    elif repli:
                        g[c], a[c] = 0.0, cs[0][1]
                    else:
                        continue
                    change = True
                if change:
                    break
            if not change:
                break
        if any(x is None for x in a):
            raise ValueError(f"{self.rid} s={s} : bande sans niveau")
        return {"k": k, "T": T, "a": a, "g": g, "cls": cls, "dz": dz, "bords": bords, "bandes": B, "retraits": ret}

    def z_bande(self, c: dict, b: int, t: float) -> float:
        return c["a"][b] + c["g"][b] * t + (c["dz"] if c["cls"][b] == 0 else 0.0)

    def z_surface(self, s: float, t: float, k: int | None = None) -> float:
        """Z attendu de la surface visible (bande ou abord) en (s, t) ; hors emprise des éléments."""
        c = self.coupe(s, k)
        T = c["T"]
        n = len(T) - 1
        if t > T[0]:
            return self.z_bande(c, 0, T[0])
        if t < T[n]:
            return self.z_bande(c, n - 1, T[n])
        b = next(i for i in range(n) if T[i + 1] - 1e-9 <= t <= T[i] + 1e-9)
        return self.z_bande(c, b, t)

    def contour_t(self, s: float, k: int | None = None):
        """(t max, t min) du contour extérieur (profil et abords) en s."""
        c = self.coupe(s, k)
        return c["T"][0] + self.abords["gauche"][0], c["T"][-1] - self.abords["droite"][0]


def charger(dossier_scene: Path) -> dict:
    return json.loads((Path(dossier_scene) / "modele_voie.json").read_text(encoding="utf-8"))
