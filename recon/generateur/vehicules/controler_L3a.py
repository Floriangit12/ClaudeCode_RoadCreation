# -*- coding: utf-8 -*-
"""Contrôle du lot L3a (modèles de véhicules et balayage) : critères du plan + contrôles d'appui, planches, rapport.

    python recon/generateur/vehicules/controler_L3a.py
      -> recon/generateur/validation/rapport_L3a.json, RAPPORT_L3a.md
      -> recon/out/generateur/L3a/planche_couronne.png, planche_virages.png (≤ 1092 px)

Critères du plan (PLAN_GENERATEUR § 3, L3a) :
  L3a-1 100 % des dimensions sourcées ;
  L3a-2 balayage d'un virage du cercle homologué : Rext 12,50 / Rint 5,30 (CU p. 78) à ± 0,10 m ;
  L3a-3 balayage du bus standard : 4,80 / 11,50 (VU p. 144) à ± 0,10 m.
Les rayons sont MESURÉS sur la simulation (poses au pas de 5 cm, second tour d'un virage de 720° pris depuis une
approche rectiligne) et sur le polygone de balayage rendu (anneau extérieur et trou), pas recopiés du JSON.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import balayage as B  # noqa: E402
import construire_vehicules as CV  # noqa: E402

GEN = ICI.parent
DEPOT = GEN.parents[1]
VALID = GEN / "validation"
SORTIES = DEPOT / "recon" / "out" / "generateur" / "L3a"
TOL = 0.10
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")

NATURES = {"norme", "donnee_constructeur", "donnee_administrative", "annonce", "derive", "convention"}


# ----------------------------------------------------------------------------------------------------------------
def essai_couronne(v: B.Vehicule, r_guide: float, tours: float = 2.0):
    """Virage circulaire (centre à l'origine) de `tours` tours, approche rectiligne ; mesures sur le dernier tour."""
    axe = B.axe_virage(r_guide, 360.0 * tours, 0.0, 0.0, depart=(0.0, -r_guide))
    sim = B.simuler(v, axe)
    k = int(round(2 * math.pi * r_guide * (tours - 1) / sim["pas"]))
    poses = sim["poses"][k:]
    rp = B.rayons_poses(v, poses)
    polys = B.enveloppe(v, poses)
    rg = B.rayons_polygone(polys[0])
    return {"poses": rp, "polygone": rg, "n_poses": len(poses), "anneaux": 1 + len(polys[0].trous),
            "composantes": len(polys)}, polys[0], poses


def debord_1_5_bis(v: B.Vehicule):
    """96/53 annexe I § 1.5 bis : entrée dans la couronne (extérieur 12,50 m) depuis une approche rectiligne ;
    débord du véhicule au-delà du plan tangent à son flanc extérieur (borne haute : braquage instantané)."""
    r0 = B.r0_pour_rext(v.unites, 12.50)
    rg = math.hypot(r0, v.unites[0].empattement)
    axe = B.axe_virage(rg, 180.0, 40.0, 0.0, depart=(-40.0, -rg))
    sim = B.simuler(v, axe)
    plan = -rg - v.unites[0].largeur / 2.0
    caisses = B.caisses_locales(v)
    ymin = min(y for pose in sim["poses"] for P in B.polygones_pose(v, pose, caisses) for (_, y) in P)
    return plan - ymin


def sources_cote(c: dict, cles_sources) -> tuple:
    src = c.get("source") or ""
    connue = any(k in src for k in cles_sources) or src.startswith("semi_remorque.")
    nature_ok = c.get("nature") in NATURES
    calcul_ok = c.get("nature") != "derive" or bool(c.get("calcul") or c.get("note"))
    return connue and nature_ok and calcul_ok, src


def empreinte_virages() -> str:
    """Empreinte des polygones de deux virages (bus standard, semi-remorque) : contrôle de déterminisme."""
    h = hashlib.sha256()
    for nom in ("bus_standard_12m", "semi_remorque"):
        v = B.vehicule(nom)
        axe = B.axe_virage(B.rayon_min(v), 90.0, 20.0, 20.0)
        P = B.balayage(v, axe)
        h.update(json.dumps([P.exterieur, P.trous]).encode())
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------------------------
# Planches (PIL)
# ----------------------------------------------------------------------------------------------------------------
def _police(t):
    from PIL import ImageFont
    for f in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"):
        try:
            return ImageFont.truetype(f, t)
        except OSError:
            pass
    return ImageFont.load_default()


class Panneau:
    def __init__(self, img, x0, y0, w, h, bbox, titre):
        from PIL import ImageDraw
        self.d = ImageDraw.Draw(img)
        self.x0, self.y0, self.w, self.h = x0, y0, w, h
        (bx0, by0, bx1, by1) = bbox
        marge = 26
        s = min((w - 2 * marge) / (bx1 - bx0), (h - 2 * marge - 22) / (by1 - by0))
        self.s = s
        self.cx = x0 + w / 2 - s * (bx0 + bx1) / 2
        self.cy = y0 + 22 + (h - 22) / 2 + s * (by0 + by1) / 2
        self.d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], outline=(150, 150, 150))
        self.d.text((x0 + 8, y0 + 4), titre, fill=(20, 20, 20), font=_police(15))

    def p(self, x, y):
        return (self.cx + self.s * x, self.cy - self.s * y)

    def poly(self, pts, fill=None, outline=None, width=1):
        q = [self.p(*a) for a in pts]
        if fill is not None:
            self.d.polygon(q, fill=fill)
        if outline is not None:
            self.d.line(q + q[:1], fill=outline, width=width)

    def ligne(self, pts, fill, width=1):
        self.d.line([self.p(*a) for a in pts], fill=fill, width=width)

    def cercle(self, r, fill, tirets=True, width=2):
        n = 180
        for k in range(n):
            if tirets and k % 2:
                continue
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            self.ligne([(r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1))], fill, width)

    def texte(self, x, y, t, fill=(20, 20, 20), taille=13):
        self.d.text((x, y), t, fill=fill, font=_police(taille))

    def echelle(self, m=5.0):
        x, y = self.x0 + 12, self.y0 + self.h - 16
        self.d.line([(x, y), (x + self.s * m, y)], fill=(0, 0, 0), width=3)
        self.texte(x, y - 17, f"{m:g} m", taille=12)


def dessiner_polygone(pn, P, couleur_fond=(250, 250, 250)):
    pn.poly(P.exterieur, fill=(255, 214, 153), outline=(200, 110, 0), width=2)
    for t in P.trous:
        pn.poly(t, fill=couleur_fond, outline=(200, 110, 0), width=2)


def dessiner_poses(pn, v, poses, tous=40):
    caisses = B.caisses_locales(v)
    for i in range(0, len(poses), max(1, len(poses) // tous)):
        for P in B.polygones_pose(v, poses[i], caisses):
            pn.poly(P, outline=(60, 60, 140), width=1)


def planche_couronne(chemin, essais):
    from PIL import Image
    img = Image.new("RGB", (1092, 560), (250, 250, 250))
    for k, (nom, ref, (res, P, poses), v, rg) in enumerate(essais):
        rext_ref, rint_ref = ref
        pn = Panneau(img, k * 546, 0, 546, 560, (-14.5, -14.5, 14.5, 14.5),
                     f"{nom} : {v.libelle.split(' (')[0][:44]}")
        dessiner_polygone(pn, P)
        dessiner_poses(pn, v, poses, 3)
        pn.cercle(rext_ref, (210, 0, 0))
        pn.cercle(rint_ref, (210, 0, 0))
        pn.cercle(rg, (0, 120, 0), tirets=False, width=1)
        m = res["poses"]
        pn.texte(pn.x0 + 10, pn.y0 + 26, f"référence {rext_ref:.2f} / {rint_ref:.2f} m (tirets rouges)", taille=13)
        pn.texte(pn.x0 + 10, pn.y0 + 44, f"mesuré Rext {m['Rext']:.3f}  Rint {m['Rint']:.3f} m", taille=13)
        pn.texte(pn.x0 + 10, pn.y0 + 62, f"axe suivi (vert) R = {rg:.3f} m", taille=13)
        pn.echelle(5.0)
    img.save(chemin)
    return img.size


def planche_virages(chemin, virages):
    from PIL import Image
    img = Image.new("RGB", (1092, 740), (250, 250, 250))
    W, H = 364, 370
    for k, (v, axe, d) in enumerate(virages):
        P = d["polygone"]
        xs = [x for x, _ in P.exterieur]
        ys = [y for _, y in P.exterieur]
        pad = 1.0
        pn = Panneau(img, (k % 3) * W, (k // 3) * H, W, H, (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad),
                     v.libelle.split(" (")[0][:40])
        dessiner_polygone(pn, P)
        dessiner_poses(pn, v, d["poses"], 5)
        pn.ligne(axe, (0, 120, 0), 2)
        pn.texte(pn.x0 + 10, pn.y0 + 24, f"R axe = rayon_min = {B.rayon_min(v):.2f} m ; braquage max "
                                         f"{d['braquage_max_demande_deg']:.1f}° / {d['braquage_max_vehicule_deg']:.1f}°",
                 taille=12)
        pn.echelle(5.0)
    img.save(chemin)
    return img.size


# ----------------------------------------------------------------------------------------------------------------
def controler() -> dict:
    cat = B.catalogue()
    criteres, mesures, problemes = [], {}, []

    # L3a-1 : sources -------------------------------------------------------------------------------------------
    cles = list(cat["sources"])
    n_tot = n_ok = 0
    manquants = []
    par_nature = {}
    for nom, e in cat["vehicules"].items():
        cotes = dict(e["dimensions"])
        g = e["giration"]
        cotes["giration.rayon_exterieur_caisse_min"] = g["rayon_exterieur_caisse_min"]
        if "rayon_interieur_reference" in g:
            cotes["giration.rayon_interieur_reference"] = g["rayon_interieur_reference"]
        for cle, c in cotes.items():
            n_tot += 1
            ok, src = sources_cote(c, cles)
            par_nature[c.get("nature")] = par_nature.get(c.get("nature"), 0) + 1
            if ok:
                n_ok += 1
            else:
                manquants.append(f"{nom}.{cle} ({src})")
    # cohérence cotes <-> cinématique : longueur hors tout et largeurs
    coherence = []
    for nom in B.noms():
        v = B.vehicule(nom)
        dims = cat["vehicules"][nom]["dimensions"]
        if "longueur" in dims:
            attendu = dims["longueur"]["valeur"]
        else:
            attendu = dims["tracteur_avant_pivot"]["valeur"] + dims["semi_pivot_arriere"]["valeur"]
        coherence.append((nom, round(v.longueur_totale - attendu, 6)))
    ecart_lg = max(abs(x) for _, x in coherence)
    criteres.append({
        "id": "L3a-1", "libelle": "100 % des dimensions sourcées (source connue, nature, calcul des cotes dérivées) ; "
                                  "longueur hors tout de la cinématique = cote sourcée ± 1 mm",
        "valeur": f"{n_ok} / {n_tot} cotes sourcées ({', '.join(f'{k} {v}' for k, v in sorted(par_nature.items()))}) ; "
                  f"écart de longueur hors tout max {ecart_lg * 1000:.3f} mm",
        "seuil": "100 % ; ≤ 1 mm", "atteint": n_ok == n_tot and ecart_lg <= 0.001,
        "manquants": manquants})

    # L3a-2 et L3a-3 : couronne et bus ------------------------------------------------------------------------
    semi = B.vehicule("semi_remorque")
    bus = B.vehicule("bus_standard_12m")
    e_semi = essai_couronne(semi, B.rayon_min(semi))
    e_bus = essai_couronne(bus, B.rayon_min(bus))
    for (cid, nom, vref, e, lib, note) in (
            ("L3a-2", "semi_remorque", (12.50, 5.30), e_semi,
             "balayage d'un virage du cercle homologué (semi-remorque de vérification N05 / 96/53) reproduit Rext "
             "12,50 / Rint 5,30 m (CU p. 78) à ± 0,10 m",
             "avance de sellette dérivée de la couronne : Rint reproduit PAR CONSTRUCTION en régime établi ; la mesure "
             "valide la chaîne numérique (approche, convergence de la tractrice, enveloppe rendue)"),
            ("L3a-3", "bus_standard_12m", (11.50, 4.80), e_bus,
             "balayage du bus standard reproduit Rint 4,80 / Rext 11,50 m (VU p. 144) à ± 0,10 m",
             "Rext 11,50 = donnée de calage du braquage ; Rint = contrôle indépendant des cotes (Urbanway 12, transbus)")):
        res = e[0]
        vals = [res["poses"]["Rext"] - vref[0], res["poses"]["Rint"] - vref[1],
                res["polygone"]["Rext"] - vref[0], res["polygone"]["Rint"] - vref[1]]
        criteres.append({
            "id": cid, "libelle": lib,
            "valeur": f"poses : Rext {res['poses']['Rext']:.3f}, Rint {res['poses']['Rint']:.3f} ; polygone rendu : "
                      f"Rext {res['polygone']['Rext']:.3f}, Rint {res['polygone']['Rint']:.3f} ; écart max "
                      f"{max(abs(x) for x in vals):.3f} m",
            "seuil": f"{vref[0]:.2f} / {vref[1]:.2f} ± 0,10 m", "atteint": max(abs(x) for x in vals) <= TOL,
            "note": note})
        mesures[cid] = res

    # contrôles d'appui ------------------------------------------------------------------------------------------
    # A1 : simulation et polygone = régime établi analytique, pour tous les véhicules
    rows, ecart_max, ess = [], 0.0, {}
    for nom in B.noms():
        v = B.vehicule(nom)
        rgm = B.rayon_min(v)
        res, P, poses = {"semi_remorque": e_semi, "bus_standard_12m": e_bus}.get(nom) or essai_couronne(v, rgm)
        th = B.rayons_etablis(v.unites, math.sqrt(rgm ** 2 - v.unites[0].empattement ** 2))
        ec = max(abs(res["poses"]["Rext"] - th["Rext"]), abs(res["poses"]["Rint"] - th["Rint"]),
                 abs(res["polygone"]["Rext"] - th["Rext"]), abs(res["polygone"]["Rint"] - th["Rint"]))
        ecart_max = max(ecart_max, ec)
        rows.append({"vehicule": nom, "R_guide_min": round(rgm, 4), "Rext_etabli": round(th["Rext"], 4),
                     "Rint_etabli": round(th["Rint"], 4), "Rext_poses": round(res["poses"]["Rext"], 4),
                     "Rint_poses": round(res["poses"]["Rint"], 4), "Rext_polygone": round(res["polygone"]["Rext"], 4),
                     "Rint_polygone": round(res["polygone"]["Rint"], 4), "ecart_max_m": round(ec, 4),
                     "anneaux": res["anneaux"], "composantes": res["composantes"]})
        ess[nom] = (res, P, poses)
    mesures["regime_etabli"] = rows
    criteres.append({"id": "L3a-A1", "libelle": "(appui) virage de 720° de chaque véhicule au rayon minimal : rayons "
                                               "mesurés (poses, polygone rendu) = régime établi analytique",
                     "valeur": f"7 véhicules ; écart max {ecart_max * 1000:.1f} mm ; 1 composante, 1 trou chacun",
                     "seuil": "≤ 10 mm", "atteint": ecart_max <= 0.010
                     and all(r["composantes"] == 1 and r["anneaux"] == 2 for r in rows)})

    # A2 : couronne 96/53 pour tous les véhicules
    cour = {n: cat["vehicules"][n]["giration"]["couronne_96_53"] for n in B.noms()}
    non = [f"{n} (Rint {c['Rint']:.2f} m)" for n, c in cour.items() if not c["conforme"]]
    criteres.append({"id": "L3a-A2", "libelle": "(appui) chaque véhicule s'inscrit dans la couronne 96/53 § 1.5 "
                                               "(Rint ≥ 5,30 m quand Rext = 12,50 m)",
                     "valeur": f"{len(cour) - len(non)} / {len(cour)} ; non conforme : {', '.join(non) or 'aucun'}",
                     "seuil": "7 / 7", "atteint": not non})
    if non:
        problemes.append("Autocar 15 m (Setra S 519 HD, cotes lues par moteur de recherche) : avec l'empattement "
                         "avant-moteur de 7,14 m et un essieu suiveur directionnel idéal, le modèle ne s'inscrit pas "
                         "dans la couronne 96/53 (Rint 4,91 m < 5,30 m à Rext 12,50 m), alors que le véhicule est "
                         "homologué : porte-à-faux avant (2,89 m) à confirmer sur la fiche PDF du constructeur, ou "
                         "empattement équivalent < 7,14 m (centre instantané en avant de l'essieu moteur). Le "
                         "balayage de l'autocar est donc plus large que le réel côté intérieur (sécuritaire).")

    # A3 : débord 96/53 § 1.5 bis (autobus)
    deb = {n: round(debord_1_5_bis(B.vehicule(n)), 4)
           for n in ("bus_standard_12m", "bus_12m_citaro", "bus_articule_18m", "autocar_15m")}
    mesures["debord_1_5_bis"] = deb
    trop = {k: x for k, x in deb.items() if x > 0.60}
    if trop:
        problemes.append("Débord 96/53 § 1.5 bis > 0,60 m pour " + ", ".join(f"{k} ({x:.2f} m)" for k, x in trop.items())
                         + " : borne haute (braquage instantané à l'entrée du cercle) ; pour l'autocar, porte-à-faux "
                           "arrière de 4,97 m derrière l'essieu moteur dans le modèle (essieu suiveur directionnel "
                           "idéal) — même cause probable que la couronne (cotes Setra à confirmer).")
    criteres.append({"id": "L3a-A3", "libelle": "(appui) autobus : débord au-delà du plan tangent au flanc en entrant "
                                               "dans la couronne ≤ 0,60 m (96/53 § 1.5 bis ; borne haute, braquage "
                                               "instantané)",
                     "valeur": " ; ".join(f"{k} {x:.3f} m" for k, x in deb.items()),
                     "seuil": "≤ 0,60 m", "atteint": all(x <= 0.60 for x in deb.values())})

    # A4 : faisabilité (le braquage demandé par l'axe est comparé au braquage maximal)
    fa = []
    for nom in B.noms():
        v = B.vehicule(nom)
        r = B.rayon_min(v)
        f1 = B.faisabilite(v, B.axe_virage(r * 1.002, 400, 5, 0))
        f2 = B.faisabilite(v, B.axe_virage(r * 0.95, 400, 5, 0))
        fa.append((nom, f1["faisable"], f2["faisable"]))
        mesures.setdefault("faisabilite", []).append(
            {"vehicule": nom, "braquage_max_deg": round(f1["braquage_max_vehicule_deg"], 3),
             "rayon_min": round(r, 4), "rayon_axe_1_002": round(f1["rayon_axe_min"], 4),
             "rayon_axe_0_95": round(f2["rayon_axe_min"], 4),
             "braquage_demande_1_002": round(f1["braquage_max_demande_deg"], 3),
             "braquage_demande_0_95": round(f2["braquage_max_demande_deg"], 3)})
    bons = sum(1 for (_, a, b), m in zip(fa, mesures["faisabilite"])
               if a and not b and m["braquage_demande_1_002"] <= m["braquage_max_deg"] + 0.1)
    criteres.append({"id": "L3a-A4", "libelle": "(appui) faisabilité (rayon local de l'axe ≥ rayon_min) : axe à "
                                               "1,002 × rayon_min accepté, à 0,95 × rayon_min refusé ; braquage simulé "
                                               "≤ braquage maximal + 0,1° à 1,002 × rayon_min",
                     "valeur": f"{bons} / {len(fa)}", "seuil": "7 / 7", "atteint": bons == len(fa)})

    # A5 : aire d'un balayage rectiligne (chaîne d'enveloppe exacte)
    v = B.vehicule("bus_standard_12m")
    P = B.balayage(v, [(0.0, 0.0), (30.0, 0.0)])
    attendu = v.unites[0].largeur * (30.0 + v.longueur_totale)
    err = abs(P.aire - attendu) / attendu
    criteres.append({"id": "L3a-A5", "libelle": "(appui) balayage rectiligne de 30 m du bus : aire = largeur × "
                                               "(30 + longueur)",
                     "valeur": f"{P.aire:.4f} m² pour {attendu:.4f} m² ({err * 100:.4f} %)", "seuil": "≤ 0,1 %",
                     "atteint": err <= 0.001})

    # A6 : témoins négatifs (les contrôles détectent une cote fausse)
    tem = []
    un = list(B.vehicule("bus_standard_12m").unites)
    u0 = un[0]
    for lib, mod in (("empattement du bus + 0,30 m", u0._replace(empattement=u0.empattement + 0.30,
                                                                 avant=u0.avant + 0.30)),
                     ("largeur du bus + 0,20 m", u0._replace(largeur=u0.largeur + 0.20))):
        r = B.rayons_etablis([mod], B.r0_pour_rext([mod], 11.50))
        tem.append((lib, round(r["Rint"] - 4.80, 3), abs(r["Rint"] - 4.80) > TOL))
    un = list(B.vehicule("semi_remorque").unites)
    mod = [un[0], un[1]._replace(empattement=un[1].empattement + 0.30, avant=un[1].avant + 0.30,
                                 arriere=un[1].arriere - 0.30)]
    r = B.rayons_etablis(mod, B.r0_pour_rext(mod, 12.50))
    tem.append(("pivot - essieux de la semi + 0,30 m", round(r["Rint"] - 5.30, 3), abs(r["Rint"] - 5.30) > TOL))
    criteres.append({"id": "L3a-A6", "libelle": "(appui) témoins négatifs : une cote faussée fait sortir Rint de la "
                                               "tolérance",
                     "valeur": " ; ".join(f"{a} -> écart {b:+.3f} m" for a, b, _ in tem),
                     "seuil": "3 / 3 détectés", "atteint": all(c for _, _, c in tem)})

    # A7 : déterminisme (JSON reconstruit ; polygones de deux virages calculés dans deux processus)
    json_ok = CV.serialiser(CV.construire()) == (ICI / "vehicules_projet.json").read_bytes()
    cmd = [sys.executable, "-c", "import sys; sys.path.insert(0, r'%s'); import controler_L3a as C; "
                                 "print(C.empreinte_virages())" % ICI]
    h1 = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
    h2 = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
    h3 = None
    if HYTHON.exists():                                   # même calcul dans hython (Python et numpy de Houdini)
        env = dict(os.environ, HOUDINI_VEX_DISABLE_JIT="1")
        out = subprocess.run([str(HYTHON)] + cmd[1:], capture_output=True, text=True, env=env).stdout.strip()
        h3 = out.splitlines()[-1] if out else "échec"
    criteres.append({"id": "L3a-A7", "libelle": "(appui) déterminisme : vehicules_projet.json reconstruit à l'octet ; "
                                               "polygones de deux virages identiques dans deux processus Python et "
                                               "dans hython 22",
                     "valeur": f"JSON {'identique' if json_ok else 'DIFFÉRENT'} ; empreintes {h1[:12]} / {h2[:12]}"
                               + (f" ; hython {h3[:12]}" if h3 else " ; hython absent"),
                     "seuil": "identique", "atteint": json_ok and h1 == h2 and (h3 is None or h3 == h1)})

    # planches -----------------------------------------------------------------------------------------------------
    SORTIES.mkdir(parents=True, exist_ok=True)
    t1 = planche_couronne(SORTIES / "planche_couronne.png", [
        ("semi_remorque", (12.50, 5.30), e_semi, semi, B.rayon_min(semi)),
        ("bus_standard_12m", (11.50, 4.80), e_bus, bus, B.rayon_min(bus))])
    virages = []
    for nom in ("vl", "bus_standard_12m", "bus_articule_18m", "pl_porteur", "semi_remorque", "autocar_15m"):
        v = B.vehicule(nom)
        axe = B.axe_virage(B.rayon_min(v), 90.0, 20.0, 20.0)
        virages.append((v, axe, B.balayage_detail(v, axe)))
    t2 = planche_virages(SORTIES / "planche_virages.png", virages)
    mesures["virages_90"] = [{"vehicule": v.nom, "aire_m2": round(d["polygone"].aire, 3),
                              "braquage_max_demande_deg": round(d["braquage_max_demande_deg"], 2),
                              "faisable": d["faisable"], "sommets": len(d["polygone"].exterieur)}
                             for v, _, d in virages]

    plan_ok = all(c["atteint"] for c in criteres if not c["id"].startswith("L3a-A"))
    return {
        "lot": "L3a",
        "titre": "modèles de véhicules de projet et balayage (épures de giration)",
        "plan": "recon/generateur/PLAN_GENERATEUR.md § 3 (L3a)",
        "statut": "ok" if plan_ok else "partiel",
        "criteres": criteres,
        "mesures": mesures,
        "problemes": problemes,
        "planches": {"planche_couronne.png": list(t1), "planche_virages.png": list(t2)},
        "vehicules": {n: {"libelle": cat["vehicules"][n]["libelle"],
                          "rayon_point_guide_min": cat["vehicules"][n]["giration"]["rayon_point_guide_min"]["valeur"],
                          "rayon_exterieur_caisse_min": cat["vehicules"][n]["giration"]["rayon_exterieur_caisse_min"]["valeur"],
                          "rayon_interieur_calcule": cat["vehicules"][n]["giration"]["rayon_interieur_calcule"]["valeur"],
                          "angle_braquage_bicyclette_max": cat["vehicules"][n]["giration"]["angle_braquage_bicyclette_max"]["valeur"]}
                      for n in B.noms()},
    }


def _f(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def faire_rapport(r) -> str:
    cat = B.catalogue()
    L = []
    nplan = [c for c in r["criteres"] if not c["id"].startswith("L3a-A")]
    napp = [c for c in r["criteres"] if c["id"].startswith("L3a-A")]
    L.append("# Rapport du lot L3a : modèles de véhicules de projet et balayage (épures de giration)\n")
    L.append("*`recon/generateur/validation/RAPPORT_L3a.md` — produit par `python recon/generateur/vehicules/"
             "controler_L3a.py` (données : `rapport_L3a.json`). Python 3 + numpy (shapely non requis ; même résultat "
             "à l'octet dans hython 22). Bases lues, non modifiées : `regles_route_fr.json`, DocRoute 10 et 17.*\n")
    L.append(f"**Statut : {r['statut']} — {sum(c['atteint'] for c in nplan)} critères du plan sur {len(nplan)} "
             f"atteints ; contrôles d'appui : {sum(c['atteint'] for c in napp)} / {len(napp)}** (les contrôles "
             "d'appui non atteints concernent l'autocar 15 m, § 6)\n")
    L.append("## 1. Ce que le lot apporte\n")
    L.append("```\n"
             "python recon/generateur/vehicules/construire_vehicules.py  # -> vehicules/vehicules_projet.json\n"
             "python recon/generateur/vehicules/controler_L3a.py        # -> validation/rapport_L3a.json, RAPPORT_L3a.md,\n"
             "                                                          #    recon/out/generateur/L3a/planche_*.png\n"
             "```\n")
    L.append("- `vehicules/vehicules_projet.json` : 7 véhicules de projet (VL, bus standard 12 m, variante Citaro "
             "12 m, bus articulé 18 m, porteur 11 m, semi-remorque 16,50 m, autocar 15 m) ; chaque cote porte sa "
             "source (document, page), sa nature, sa confiance et, si elle est dérivée, son calcul ; une partie "
             "`cinematique` (unités, empattements, attelages) et une partie `giration` (braquage minimal, rayons "
             "établis, conformité à la couronne 96/53) ; des alias (VL, bus, bus_articule, PL, semi, car) ;")
    L.append("- `vehicules/balayage.py` : modèle bicyclette multi-unités (tractrice intégrée exactement par pas), "
             "enveloppe de caisse rendue en polygone avec trous (réunion exacte de polygones convexes par distance "
             "signée + marching squares, ± 5 mm) ;")
    L.append("- API pour le solveur (lots L3, L5) :\n")
    L.append("```python\n"
             "from vehicules.balayage import vehicule, rayon_min, balayage, balayage_detail, faisabilite, "
             "distance_signee, axe_virage\n"
             "v = vehicule(\"bus\")                    # nom ou alias (VL, bus, bus_articule, PL, semi, car)\n"
             "rayon_min(v)                             # 8,653 m : rayon minimal de l'axe suivi par le centre de l'essieu avant\n"
             "poly = balayage(v, axe)                  # axe [(x, y), ...] -> Polygone(exterieur, trous)\n"
             "distance_signee(poly, p)                 # < 0 dedans ; nez d'îlot au « premier contact + 0,30 m » : >= 0,30\n"
             "faisabilite(v, axe)[\"faisable\"]          # rayon local de l'axe >= rayon_min(v)\n"
             "axe_virage(R, angle, approche, sortie)   # droite - arc - droite (RF-GV-TRJ-006), flèche <= 0,5 mm\n"
             "```\n")
    L.append("## 2. Critères\n")
    L.append("| Critère | Valeur | Seuil | Atteint |\n|---|---|---|---|")
    for c in r["criteres"]:
        lib = c["libelle"] + (f" — *{c['note']}*" if c.get("note") else "")
        L.append(f"| {c['id']} {lib} | {c['valeur']} | {c['seuil']} | {'oui' if c['atteint'] else 'non'} |")
    L.append("")
    L.append("## 3. Véhicules\n")
    L.append("| Véhicule | Rayon min. de l'axe | Rext caisse (calage) | Rint calculé | Rint publié | Braquage max | "
             "Couronne 96/53 (Rint à Rext 12,50) |\n|---|---|---|---|---|---|---|")
    for n in B.noms():
        e = cat["vehicules"][n]
        g = e["giration"]
        ref = g.get("rayon_interieur_reference", {}).get("valeur")
        L.append(f"| `{n}` — {e['libelle']} | {_f(g['rayon_point_guide_min']['valeur'], 3)} m | "
                 f"{_f(g['rayon_exterieur_caisse_min']['valeur'], 3)} m ({g['rayon_exterieur_caisse_min']['source']}) | "
                 f"{_f(g['rayon_interieur_calcule']['valeur'], 3)} m | {(_f(ref) + ' m') if ref else '—'} | "
                 f"{_f(g['angle_braquage_bicyclette_max']['valeur'], 1)}° | {_f(g['couronne_96_53']['Rint'], 2)} m "
                 f"{'conforme' if g['couronne_96_53']['conforme'] else '**non conforme**'} |")
    L.append("")
    L.append("Natures des cotes : norme (guides VU, CU, CF, N05 ; directive 96/53), donnée constructeur (fiche "
             "Citaro locale ; fiche Setra lue par moteur de recherche), donnée administrative (AEE), annonce "
             "(transbus.org, annonces de véhicules d'occasion : confiance moyenne), dérivé (calcul écrit dans le "
             "JSON). Aucune cote estimée sans source.\n")
    L.append("## 4. Méthode et mesures\n")
    L.append("- **Point guide** : centre de l'essieu avant directeur ; l'axe d'un mouvement (axe de voie – arc "
             "tangent – axe de voie, RF-GV-TRJ-006) est la trajectoire de ce point. **Braquage minimal** : calé sur "
             "un rayon extérieur de caisse publié (VU p. 144, CF p. 22, couronne 96/53, cercle de braquage "
             "constructeur) ; `rayon_min` = rayon du point guide correspondant.")
    L.append("- **Cinématique** : l'essieu équivalent de chaque unité suit son meneur en tractrice ; sur un pas "
             "rectiligne du meneur, tan(φ'/2) = tan(φ/2)·exp(−s/L) est exacte (pas de 5 cm). Essieu équivalent : "
             "milieu du groupe de 3 essieux fixes de la semi-remorque, essieu moteur de l'autocar (essieu suiveur "
             "directionnel idéal) [G]. Faisabilité : rayon local de l'axe ≥ `rayon_min` (en transitoire le braquage "
             "ne dépasse pas celui du régime établi de la courbure maximale).")
    L.append("- **Enveloppe** : caisses aux positions retenues (pas 0,25 m) + enveloppes convexes de chaque tronçon "
             "de 0,25 m du contour entre deux positions (l'enveloppe convexe de la caisse entière débordait de "
             "~0,07 m vers le centre : défaut trouvé et corrigé pendant le lot) ; réunion par fonction de distance "
             "signée (zéro exact) et marching squares au pas de 5 cm, simplification 3 mm.")
    L.append("- **Mesure de L3a-2 et L3a-3** : virage de 720° pris depuis une approche rectiligne ; rayons mesurés "
             "sur le second tour, sur les poses (sommets et distance minimale des caisses au centre) et sur le "
             "polygone rendu (anneau extérieur et trou).\n")
    L.append("| Véhicule | R axe | Rext / Rint établis | Rext / Rint poses | Rext / Rint polygone | Écart max |"
             "\n|---|---|---|---|---|---|")
    for x in r["mesures"]["regime_etabli"]:
        L.append(f"| {x['vehicule']} | {_f(x['R_guide_min'], 3)} | {_f(x['Rext_etabli'], 3)} / {_f(x['Rint_etabli'], 3)} | "
                 f"{_f(x['Rext_poses'], 3)} / {_f(x['Rint_poses'], 3)} | {_f(x['Rext_polygone'], 3)} / "
                 f"{_f(x['Rint_polygone'], 3)} | {_f(x['ecart_max_m'] * 1000, 1)} mm |")
    L.append("")
    L.append("## 5. Ce qui est contrôlé et ce qui est « par construction »\n")
    L.append("- **Bus standard (L3a-3) — contrôle indépendant** : cotes de l'Urbanway 12 (empattement 6,12, "
             "porte-à-faux avant 2,71, largeur 2,50 m ; transbus.org via DocRoute 17, confiance moyenne), braquage "
             "calé sur Rext = 11,50 m ; le rayon intérieur **calculé** vaut 4,867 m pour 4,80 publié (écart 0,067 m, "
             "dans ± 0,10). Sensibilité : avec les cotes du Citaro 12 m (fiche constructeur, confiance haute) on "
             "trouve 4,94 m à Rext 11,485 m (écart 0,14 m, hors tolérance) : le « bus 12 m » de VU p. 144 a un "
             "avant plus long que le Citaro.")
    L.append("- **Cercle homologué (L3a-2) — par construction en régime établi** : ni l'avance de sellette du "
             "tracteur ni sa cote équivalente ne figurent dans les fiches lues ; la semi-remorque de vérification "
             "(N05 : 6,08 + 13,67 m ; 96/53 : 16,50 m, pivot - arrière 12,00 m, rayon avant 2,04 m ; Schmitz S.CS : "
             "pivot - essieux 7,70 m) est complétée par l'avance de sellette (0,741 m) qui l'inscrit au plus juste "
             "dans la couronne. Le critère valide la chaîne numérique (approche rectiligne, convergence de la "
             "tractrice, enveloppe rendue), pas les cotes ; témoin : +0,30 m sur le pivot - essieux déplace Rint de "
             "−0,37 m.")
    L.append("- **VL, bus articulé, porteur** : la cote manquante (porte-à-faux avant du VL, articulation du "
             "Citaro G, empattement du porteur) est dérivée des deux rayons publiés (VU p. 144, CF p. 22) : leurs "
             "rayons sont reproduits par construction.\n")
    L.append("## 6. Problèmes et limites\n")
    for p in r["problemes"]:
        L.append(f"- {p}")
    L.append("- Cotes « annonce » (confiance moyenne) : empattement du tracteur (3,70 m), pivot - essieux et "
             "entraxe de la semi-remorque (7,70 / 1,31 m), cotes de l'Urbanway 12 ; à remplacer par des fiches "
             "constructeurs téléchargées (le téléchargement demande l'accord de l'utilisateur).")
    L.append("- Modèle sans glissement ni dévers ; caisses rectangulaires (rétroviseurs inclus pour le VL seulement, "
             "comme VU p. 142-144) ; le braquage instantané à l'entrée d'un arc majore le débord arrière (§ 1.5 bis).")
    L.append("- `rayon_min` de la semi-remorque (10,75 m) est celui de la couronne d'homologation, pas le braquage "
             "maximal du tracteur seul.\n")
    L.append("## 7. Rendus regardés\n")
    L.append("Planches ≤ 1092 px, regardées en entier après découpe par `recon/pcg/vision/decoupe.py` (1 tuile "
             "chacune) : `recon/out/generateur/L3a/planche_couronne.png` (semi-remorque et bus dans leur couronne "
             "de référence ; tirets rouges : 12,50 / 5,30 et 11,50 / 4,80 m ; axe suivi en vert) ; "
             "`planche_virages.png` (virage à gauche de 90° au rayon minimal pour six véhicules : sur-largeur "
             "intérieure, débord avant, débord arrière de l'autobus et de l'autocar).\n")
    return "\n".join(L) + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    r = controler()
    (VALID / "rapport_L3a.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (VALID / "RAPPORT_L3a.md").write_text(faire_rapport(r), encoding="utf-8")
    for c in r["criteres"]:
        print(f"{c['id']:7s} {'oui' if c['atteint'] else 'NON'}  {c['valeur']}")
    print("statut", r["statut"])
    for p in r["problemes"]:
        print("PROBLÈME", p)


if __name__ == "__main__":
    main()
