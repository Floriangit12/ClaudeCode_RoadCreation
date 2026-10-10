"""Famille « marquages » de la description v2 (schéma description_scene_v2/0.2), site complet.

Usage :
    python recon/pcg/decrire/marquages.py [--sortie DOSSIER] [--rapport RAPPORT.json]
    (normalement appelé par composer.py, qui écrit aussi le manifeste et lance la validation)
Sorties (défaut recon/out/paquet_jardin/v2/description/base) :
    marquages.geojson                     entités paramétriques (Lambert-93), une par ligne, triées par id
    marquages_correspondance.geojson      devenir de chacun des 996 marquages v1 (géométrie nulle)

Principe : chaque marquage v1 (polygone, souvent vectorisé depuis un raster) devient une entité
paramétrique (générée), un polygone simplifié sans marche d'escalier (gardé) ou une boîte à
vectoriser ; aucune géométrie de fabrication n'est tirée d'un raster. Classes :
- ligne (ML-) : ancrage xodr {route, bords [{section_s, voie, s0, s1}], t_off_m} ou axe propre (GAM / v1),
  type continue | discontinue | segment, modulation (code IISR), trait_m, vide_m, phase_m, largeur_m,
  interruptions [[σ0, σ1]] (σ le long de l'axe), voir marquages_lignes ;
- transversale (MT-) : ligne d'effet des feux T'2 0,15, ancrée sur l'objet stopLine du .xodr ;
- passage (MP-) : zébra {axe [A, B], largeur_bande_m, intervalle_m, pas_axe_m, longueur_bande_m,
  cap_bandes_deg, nb_bandes, coupures} ; traversée cyclable {files [{axe, gabarit | tuile_m, pas_m, nb}]} ;
- fleche (MF-) : gabarit IISR, echelle, pose {point_l93, cap_deg}, ancrage {route, voie, s, t}, iou_v1 ;
- symbole (MS-) : velo (gabarit VELO), dent_requin, chevron, barre, point, a_vectoriser (PMR, 30, 50) ;
- zone (MZ-) : hachures (bande, pas, cap, contour), zigzag (base, amplitude, période), aplat,
  surface_coloree, divers, bande_isolee ;
- fantome (MG-) : empreinte effacée reconstruite par primitive (rectangle, ruban, gabarit) ou contour redressé ;
  empreintes qui se recouvrent réunies en une entité.
Compléments (revue du 10/10) :
- symboles PMR, « 30 » / « 50 » et T de stationnement construits par primitives (glyphe {nom, paramètres},
  marquages_glyphes) ; figurine VELO D1 reconstruite par primitives ;
- flèches conservées ou refaites à l'identique recalées sur l'ortho PCRS 2022 (recalage_ortho) ;
- marques neuves de 2025 en usure 0 (usure_v1 gardée) ;
- retraits justifiés (devenir « retire ») : ligne interrompue sur toute sa longueur par un passage, marque sur
  l'emprise d'un bâtiment v1 (dalle hors sol) ;
- lignes sur axe levé GAM prolongées par les lignes GAM jointives non rattachées au v1 (prolongements_gam) ; chaînes
  GAM orphelines d'au moins 10 m -> nouvelles lignes (ML-9kkk, ajout {gam, preuve}, lien_v1 vide).
Reprises (revue du 10/10, deuxième tour ; marquages_reprises, marquages_bordures) :
- flèches de 2022 hors des voies roulables du .xodr 2026 retirées (MF-0401 : flèche à trois directions sur l'ortho, voie
  en biseau, emprise réaménagée en 2025) ; flèches du parking levées à 4 m gardées (écart noté) ;
- lignes ancrées xodr : profil latéral t(s) sur le levé GAM de tous leurs MQ (t_off_profil) ; lignes GAM d'une autre marque
  exclues (gam_refs_exclues) ; tirets du plan qui se suivent sur un même bord réunis (pas de baïonnette) ; modulation IISR
  seulement si elle est celle de la table, sinon « <code>_site » mesurée ; T3 harmonisées à 0,12 ; rôle rive_piste ;
- lignes interrompues au droit des zigzags, aplats et lignes d'effet des feux ; bandes isolées découpées par les lignes
  qui les traversent ; recouvrements supprimés (symboles déplacés, passages découpés) ;
- dégagement des bordures (2u ; position levée GAM : 0,02 m) : lignes décalées ou interrompues, polygones découpés
  (decoupes), gabarits déplacés ; marques sur sol surélevé : retirées (bord lu comme une marque, marque 2022 sur le sol 2026
  de la zone pilote), gardées sur ce sol (piste, stationnement au niveau du trottoir : support_sol) ou gardées non fabriquées
  (plan 2025 sur un espace vert v1, sol en talus : fabrication.statut non_fabrique, devenir garde_non_fabrique) ;
- fantômes : rectangle orienté ou réunion de 2-3 rectangles avant le contour redressé ; ajouts GAM vus gris sur photo en
  usure 2.
Géométrie GeoJSON : axe (lignes, transversales, zébras, zigzags), gabarit posé (flèches, symboles),
polygone (zones, fantômes) — dérivée des paramètres sauf pour les contours redressés.
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
import marquages_lignes as LG  # noqa: E402
import marquages_passages as PS  # noqa: E402
import marquages_symboles as SY  # noqa: E402
import marquages_zones as ZN  # noqa: E402
import xodr_echantillonne as X  # noqa: E402
from commun import (DONNEES, PAQUET, SORTIE, VECTEURS, ZONE, arrondi, coords_geojson, ecrire_geojson,  # noqa: E402
                    geom_polygones, repere)

SCHEMA_ID = "description_scene_v2/0.2"
FICHIER = "marquages.geojson"
FICHIER_CORR = "marquages_correspondance.geojson"
REFERENCES = {
    "opendrive": (PAQUET / "paquet_jardin_2026.xodr", "réseau OpenDRIVE 1.7 (bords de voie, roadMarks, objets)"),
    "lanes_v1": (DONNEES / "opendrive/lanes_2026.geojson", "polygones de voies (validation de l'échantillonneur)"),
    "marquages_v1_tous": (DONNEES / "marquages/marquages_2026.geojson", "996 marquages v1 (famille marquages)"),
    "gam_signalisation_lin": (VECTEURS / "etat_2026/signalisation_horizontale_lin_L93.geojson", "levé GAM des marquages (axes, contours)"),
    "gam_signalisation_pct": (VECTEURS / "etat_2026/signalisation_horizontale_pct_L93.geojson", "blocs GAM (SYMBOLE_VELO, PMR, flèches)"),
    "spec_marquages": (M.SPEC, "marquages_geometrie.json : modulations, largeurs, gabarits IISR"),
    "ortho_pcrs_2022": (VECTEURS / "ortho5cm_2022/index.json", "ortho PCRS 5 cm 2022 (dalles 50 m) : phase des tirets et pose des flèches conservées"),
    "surfaces_v1_batiments": (DONNEES / "surfaces/surfaces_2026.geojson", "surfaces v1 : bâtiments (dalle hors sol) et sols surélevés "
                              "(trottoir, espace vert, îlot : dégagement des bordures, hors emprise pilote)"),
    "zone_pilote": (ZONE, "emprise pilote : sol et bordures v2 de la description (dégagement des bordures)"),
}
SCRIPTS = ["xodr_echantillonne.py", "marquages.py", "marquages_commun.py", "marquages_lignes.py",
           "marquages_passages.py", "marquages_symboles.py", "marquages_zones.py", "marquages_gam.py",
           "marquages_glyphes.py", "marquages_ortho.py", "marquages_bordures.py", "marquages_reprises.py"]


# --------------------------------------------------------------------------- conversion en GeoJSON
def _l93(P):
    return repere(np.asarray(P, float), "l93")


def _geometrie(geom):
    t, g = geom
    if t == "LineString":
        return {"type": "LineString", "coordinates": coords_geojson(_l93(g))}
    if t == "MultiLineString":
        return {"type": "MultiLineString", "coordinates": [coords_geojson(_l93(x)) for x in g]}
    if t in ("Polygon", "MultiPolygon"):
        polys = [[_l93(r) for r in poly] for poly in g]
        return geom_polygones(polys)
    raise ValueError(t)


def _propriete(k, v):
    """Points locaux -> Lambert-93 ; arrondi au mm."""
    if k == "pose":
        v = dict(v)
        o = v.pop("origine_local")
        return {"point_l93": coords_geojson(_l93(np.asarray(o)[None]))[0], **arrondi(v)}
    if k == "origine_bandes_local":
        return coords_geojson(_l93(np.asarray(v)[None]))[0]
    if k == "files":
        out = []
        for f in v:
            f = dict(f)
            f["axe_l93"] = coords_geojson(_l93(np.vstack(f.pop("axe"))))
            out.append(arrondi(f))
        return out
    return arrondi(_locaux(v))


def _locaux(v):
    """Clés « *_local » (point ou polyligne locale) -> « *_l93 », récursivement."""
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if k.endswith("_local"):
                a = np.asarray(x, float)
                out[k[:-6] + "_l93"] = coords_geojson(_l93(a[None]))[0] if a.ndim == 1 else coords_geojson(_l93(a))
            else:
                out[k] = _locaux(x)
        return out
    if isinstance(v, (list, tuple)):
        return [_locaux(x) for x in v]
    return v


def feature(e):
    props = {"id": e["id"], "famille": "marquages"}
    for k in ("classe", "type"):
        props[k] = e[k]
    for k, v in e.items():
        if k in ("id", "geom", "classe", "type"):
            continue
        if k == "origine_bandes_local":
            props["origine_bandes_l93"] = _propriete(k, v)
        else:
            props[k] = _propriete(k, v)
    return {"type": "Feature", "geometry": _geometrie(e["geom"]), "properties": props}


# --------------------------------------------------------------------------- recouvrements et doublons
def _preuve(e):
    """0 : marque levée (contour ou tiret levé GAM) ; 1 : sinon."""
    V = {m["id"]: m for m in M.v1()}
    return 0 if any("contour" in V[i]["p"]["source"] or "tiret levé" in V[i]["p"]["source"] for i in e["lien_v1"]) else 1


def _prio(e):
    a = e["ancrage"]
    rang = 0 if a["type"] == "xodr" else (1 if a.get("source") == "gam" else 2)
    return (rang, {"continue": 0, "discontinue": 1, "segment": 2}[e["type"]], -e["longueur_m"], e["id"])


def _peint(e):
    from marquages_controles import _echantillons, _pieces, _segments
    P = e["geom"][1]
    iv = _pieces(e, P)
    q, t = _echantillons(P, iv)
    A, B = _segments(P, iv)
    return P, q, t, A, B, sum(b - a for a, b in iv)


def _recouvre(ea, da, eb, db):
    """Échantillons peints de a recouverts par les parties peintes de b (quasi parallèles)."""
    from commun import distance_segments
    _, qa, ta, _, _, _ = da
    _, _, _, Ab, Bb, _ = db
    if len(qa) == 0 or len(Ab) == 0:
        return np.zeros(0, bool)
    d, j, _ = distance_segments(qa, Ab, Bb)
    seg = Bb[j] - Ab[j]
    seg /= np.maximum(np.hypot(*seg.T), 1e-12)[:, None]
    par = np.abs(np.einsum("ij,ij->i", seg, ta)) > 0.9
    return (d < (ea["largeur_m"] + eb["largeur_m"]) / 2 - 0.005) & par


def resoudre_recouvrements(lignes, devenir):
    """Lignes dont les parties peintes se recouvrent (doublons du v1, même ligne portée deux fois) :
    une ligne recouverte à 60 % ou plus est absorbée par l'autre (ses MQ y sont rattachés), sauf si
    elle seule est levée (GAM) : l'autre s'interrompt alors ; sinon la ligne de moindre priorité
    (ancrage xodr > axe GAM > axe v1 ; continue > discontinue > segment ; plus longue) reçoit une
    interruption sur le recouvrement (± 0,10 m). -> (lignes gardées, journal)."""
    from commun import projeter
    data = {e["id"]: _peint(e) for e in lignes}
    par_id = {e["id"]: e for e in lignes}
    bb = {i: (*d[0].min(axis=0) - 0.5, *d[0].max(axis=0) + 0.5) for i, d in data.items()}
    retires, journal = set(), []
    ids = sorted(par_id)
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            a, b = ids[x], ids[y]
            if a in retires or b in retires:
                continue
            A, B = bb[a], bb[b]
            if A[2] < B[0] or B[2] < A[0] or A[3] < B[1] or B[3] < A[1]:
                continue
            ea, eb = par_id[a], par_id[b]
            ra = _recouvre(ea, data[a], eb, data[b])
            rb = _recouvre(eb, data[b], ea, data[a])
            ova, ovb = ra.sum() * 0.05, rb.sum() * 0.05
            if max(ova, ovb) <= 0.20 + 1e-6:
                continue
            fa, fb = ova / max(data[a][5], 1e-6), ovb / max(data[b][5], 1e-6)
            if max(fa, fb) >= 0.6:
                if min(fa, fb) >= 0.6:
                    perd, garde = (a, b) if _prio(ea) > _prio(eb) else (b, a)
                else:
                    perd, garde = (a, b) if fa > fb else (b, a)
                if _preuve(par_id[perd]) < _preuve(par_id[garde]):
                    # la marque recouverte est levée (GAM) et l'autre non : elle prime, l'autre s'interrompt
                    perd, autre, r = garde, perd, (ra if garde == a else rb)
                else:
                    retires.add(perd)
                    lg = round(max(ova, ovb), 2)
                    pg = par_id[garde]
                    for mq in par_id[perd]["lien_v1"]:
                        devenir[mq] = ("genere", garde, f"absorbé par {garde} : recouvert sur {lg} m (même marque décrite deux fois dans le v1, ou tiret porté par la modulation)")
                    pg["lien_v1"] = sorted(set(pg["lien_v1"]) | set(par_id[perd]["lien_v1"]))
                    journal.append({"absorbe": perd, "par": garde, "recouvrement_m": lg})
                    continue
            else:
                perd, autre, r = (a, b, ra) if _prio(ea) > _prio(eb) else (b, a, rb)
            e = par_id[perd]
            q = data[perd][1][r]
            s, _, _ = projeter(e["geom"][1], q)
            s = np.sort(s)
            coupes = np.where(np.diff(s) > 0.2)[0]
            debut = np.r_[0, coupes + 1]
            fin = np.r_[coupes, len(s) - 1]
            iv = [[max(0.0, float(s[i]) - 0.10), min(e["longueur_m"], float(s[j]) + 0.10)] for i, j in zip(debut, fin)]
            e["interruptions"] = _fusion(e["interruptions"] + [[round(u, 3), round(v, 3)] for u, v in iv])
            e.setdefault("interruptions_lignes", []).append(autre)
            data[perd] = _peint(e)
            journal.append({"interrompt": perd, "par": autre, "intervalles": iv})
    return [e for e in lignes if e["id"] not in retires], journal


def _fusion(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def doublons_symboles(gardes, references, devenir):
    """Polygones gardés (divers, aplat) couverts à 50 % ou plus par une flèche ou un symbole posé :
    retirés (même marque lue deux fois, gabarit et contour d'ortho)."""
    out = []
    for e in gardes:
        if e["type"] not in ("divers", "aplat"):
            out.append(e)
            continue
        polys = e["geom"][1]
        P = np.vstack([r for poly in polys for r in poly])
        x0, y0 = P.min(axis=0) - 0.05
        nx, ny = int((P[:, 0].max() - x0) / 0.02) + 5, int((P[:, 1].max() - y0) / 0.02) + 5
        mine = M.raster_masque(polys, x0, y0, nx, ny, 0.02)
        dup = None
        o = M.rect_min(P)
        if 3.5 <= o["L"] <= 4.2 and 0.6 <= o["W"] <= 1.3:
            # tache d'ortho aux dimensions d'une flèche, à moins de 2,5 m d'une flèche posée de même axe
            for r in references:
                if r["classe"] != "fleche":
                    continue
                c = np.asarray(r["pose"]["origine_local"]) + 2.0 * np.array([math.cos(math.radians(r["pose"]["cap_deg"])), math.sin(math.radians(r["pose"]["cap_deg"]))])
                if float(np.hypot(*(c - o["c"]))) < 2.5 and min(M.ecart_cap(r["pose"]["cap_deg"], M.cap_de(o["u"])), M.ecart_cap(r["pose"]["cap_deg"], M.cap_de(-o["u"]))) < 15.0:
                    dup = r["id"]
                    break
        for r in references:
            if dup:
                break
            Q = np.vstack([rr for poly in r["geom"][1] for rr in poly])
            if Q[:, 0].max() < x0 or Q[:, 0].min() > x0 + nx * 0.02 or Q[:, 1].max() < y0 or Q[:, 1].min() > y0 + ny * 0.02:
                continue
            autre = M.raster_masque(r["geom"][1], x0, y0, nx, ny, 0.02)
            if mine.sum() and (mine & autre).sum() / mine.sum() >= 0.4:
                dup = r["id"]
                break
        if dup:
            for r in references:
                if r["id"] == dup:
                    r["lien_v1"] = sorted(set(r["lien_v1"]) | set(e["lien_v1"]))
            for mq in e["lien_v1"]:
                devenir[mq] = ("genere", dup, f"absorbé par {dup} : même marque (contour d'ortho) déjà posée en gabarit")
        else:
            out.append(e)
    return out


# --------------------------------------------------------------------------- retraits et ajouts
# preuves photographiques des lignes GAM non rattachées au v1 (ajouts)
PREUVES_AJOUTS = {185: "photo Panoramax 20d1a815 (2025-08-31, Verdun NE) : ligne de rive le long de la bordure droite",
                  186: "photo Panoramax 20d1a815 (2025-08-31, Verdun NE) : ligne de rive le long de la bordure droite"}


def _points(e, pas=0.2):
    from commun import densifier
    t, g = e["geom"]
    if t == "LineString":
        return [densifier(g, pas)[0]]
    if t == "MultiLineString":
        return [densifier(x, pas)[0] for x in g if len(x) >= 2]
    return [densifier(np.vstack([r, r[:1]]), pas)[0] for poly in g for r in poly]


def _peint_l(e):
    from marquages_controles import _pieces
    return _pieces(e, e["geom"][1])


def retirer(entites, devenir):
    """Entités sans marque à fabriquer -> devenir « retire » (justifié) : ligne interrompue sur toute sa longueur par
    un passage (arrêt à 0,50 m, art. 118), marque posée sur l'emprise d'un bâtiment v1 (dalle : sol non modélisé)."""
    from commun import DONNEES, anneaux, dans_polygones
    bat = [(f["properties"]["id"], [[repere(r) for r in poly] for poly in anneaux(f["geometry"])])
           for f in sorted(C_lire(DONNEES / "surfaces/surfaces_2026.geojson"), key=lambda f: f["properties"]["id"])
           if f["properties"].get("classe") == "batiment"]
    out, journal = [], []
    for e in entites:
        raison = None
        if e["classe"] == "ligne" and e.get("interruptions") and not _peint_l(e):
            raison = f"ligne interrompue sur toute sa longueur par le passage {', '.join(e.get('interruptions_zebras', []))} (arrêt à 0,50 m, IISR art. 118)"
        else:
            Q = np.vstack(_points(e))
            for bid, polys in bat:
                lo, hi = np.min([r.min(axis=0) for p_ in polys for r in p_], axis=0), np.max([r.max(axis=0) for p_ in polys for r in p_], axis=0)
                if Q[:, 0].max() < lo[0] or Q[:, 0].min() > hi[0] or Q[:, 1].max() < lo[1] or Q[:, 1].min() > hi[1]:
                    continue
                if dans_polygones(Q, polys).mean() >= 0.9:
                    raison = f"posée sur l'emprise du bâtiment v1 {bid} (dalle de parking) : sol absent du paquet, marque gardée non fabriquée"
                    break
        if raison and "bâtiment" in raison:
            # marque réelle (vue sur l'ortho) sur un sol que le paquet ne modélise pas : gardée, non fabriquée
            e["fabrication"] = {"statut": "non_fabrique", "raison": raison}
            for mq in e["lien_v1"]:
                devenir[mq] = ("garde_non_fabrique", e["id"], raison)
            journal.append({"entite": e["id"], "lien_v1": e["lien_v1"], "raison": raison, "devenir": "garde_non_fabrique"})
            out.append(e)
        elif raison:
            for mq in e["lien_v1"]:
                devenir[mq] = ("retire", None, raison)
            journal.append({"entite": e["id"], "lien_v1": e["lien_v1"], "raison": raison})
        else:
            out.append(e)
    return out, journal


def C_lire(chemin):
    from commun import lire_geojson
    return lire_geojson(chemin)


def _orphelines(entites, loin=True, exclure=()):
    """Axes levés (médiane des paires) des lignes GAM non rattachées au v1 ; loin=True : seulement celles à plus de
    0,5 m de toute marque v2 (ajouts) ; sinon toutes, plus les lignes courtes qui ne portent que des tirets v1
    synthétiques (prolongements)."""
    import marquages_gam as MG
    refs = {k for m in M.v1() for k in M.gam_refs(m["p"])} | set(exclure)
    if loin:
        pts = np.vstack([q for e in entites for q in _points(e)])
        orph = set(MG.orphelines(refs, pts))
    else:
        # non rattachées, ou courtes (≤ 6,5 m) et rattachées seulement à des tirets v1 synthétiques (position non observée)
        synth = collections.defaultdict(list)
        for m in M.v1():
            for k in M.gam_refs(m["p"]):
                synth[k].append(LG.synthetique(m) and m["p"]["type"] == "ligne_discontinue")
        from commun import abscisses
        orph = {k for k, P in enumerate(M.gam_lin()) if MG.ouverte(P) and len(P) >= 2 and k not in set(exclure)
                and (k not in synth or (all(synth[k]) and float(abscisses(P)[-1]) <= 6.5))}
    return {ks: (A, w) for A, w, ks in MG.axes_leves(sorted(orph)) if all(k in orph for k in ks)}


def prolonger(lignes, orph, emprises):
    """Lignes sur axe levé GAM prolongées par les lignes GAM non rattachées au v1 qui les continuent (extrémités à moins
    de 0,10 m, déviation < 30°, paires de bords réunies) : même marque levée en plusieurs polylignes (ombre,
    végétation, morceau non vectorisé) ; un tiret ou segment v1 alors recouvert est absorbé (resoudre_recouvrements)."""
    from commun import abscisses, couper_polyligne
    journal = []
    change = True
    while change:
        change = False
        for e in sorted(lignes, key=lambda e: e["id"]):
            if e["ancrage"].get("type") != "axe" or e["ancrage"].get("source") != "gam" or e["classe"] != "ligne":
                continue
            P = e["geom"][1]
            for ks in sorted(orph):
                A, w = orph[ks]
                fait = None
                for bout in ("fin", "debut"):
                    E = P[-1] if bout == "fin" else P[0]
                    tE = (P[-1] - P[-2]) if bout == "fin" else (P[0] - P[1])
                    tE = tE / max(np.hypot(*tE), 1e-12)
                    for Q in (A, A[::-1]):
                        dq = Q[1] - Q[0]
                        dq = dq / max(np.hypot(*dq), 1e-12)
                        if np.hypot(*(Q[0] - E)) < 0.10 and float(dq @ tE) > math.cos(math.radians(30.0)):
                            fait = (bout, Q)
                            break
                    if fait:
                        break
                if not fait:
                    continue
                bout, Q = fait
                ajout = float(abscisses(Q)[-1])
                P = M.dedoublonner(np.vstack([P, Q[1:]]) if bout == "fin" else np.vstack([Q[::-1][:-1], P]))
                e["geom"] = ("LineString", M.douglas_peucker(P, 0.001))
                P = e["geom"][1]
                e["longueur_m"] = round(float(abscisses(P)[-1]), 3)
                if bout == "debut" and e["type"] == "discontinue":
                    per = e["trait_m"] + e["vide_m"]
                    e["phase_m"] = round((e["phase_m"] + ajout) % per, 3)
                inter = sorted((round(z0, 3), round(z1, 3), zid) for zid, poly in emprises for z0, z1 in couper_polyligne(P, [poly]))
                e["interruptions"] = [[a, b] for a, b, _ in inter]
                if inter:
                    e["interruptions_zebras"] = sorted({z for _, _, z in inter})
                e.setdefault("prolongements_gam", []).append(list(ks))
                e["prov"]["geometrie"] = dict(e["prov"]["geometrie"], ref=e["prov"]["geometrie"]["ref"]
                                              + f" ; prolongé par la ligne GAM {','.join(map(str, ks))} ({ajout:.2f} m, levée, non rattachée au v1)")
                journal.append({"entite": e["id"], "gam": list(ks), "longueur_m": round(ajout, 3), "bout": bout})
                del orph[ks]
                change = True
                break
    return journal


def ajouts(orph, reseau, entites, emprises):
    """Chaînes de lignes GAM orphelines d'au moins 10 m (levées, sans marque v1) -> nouvelles lignes continues
    (identifiant ML-9kkk, k = plus petit indice GAM), ancrées sur le bord de voie OpenDRIVE quand il suit le levé à
    4 cm près partout, sinon sur l'axe levé (rôle lu sur le bord de voie le plus proche) ; largeur selon le rôle (rive 3u)."""
    from commun import abscisses, couper_polyligne, densifier, projeter
    restants = dict(orph)
    chaines = []
    while restants:
        ks = sorted(restants)[0]
        A, _ = restants.pop(ks)
        ch, cle = A, list(ks)
        change = True
        while change:
            change = False
            for k2 in sorted(restants):
                B, _ = restants[k2]
                for Q in (B, B[::-1]):
                    if np.hypot(*(Q[0] - ch[-1])) < 0.10:
                        ch = np.vstack([ch, Q[1:]])
                    elif np.hypot(*(Q[-1] - ch[0])) < 0.10:
                        ch = np.vstack([Q[:-1], ch])
                    else:
                        continue
                    cle += list(k2)
                    del restants[k2]
                    change = True
                    break
                if change:
                    break
        chaines.append((sorted(cle), M.dedoublonner(ch)))
    out = []
    reseau_ch = LG.chaines_reseau(reseau)
    LG.RESEAU[:] = [reseau]
    for cle, P in chaines:
        L = float(abscisses(P)[-1])
        if L < 10.0:
            continue
        u = (P[-1] - P[0]) / max(np.hypot(*(P[-1] - P[0])), 1e-9)
        anc = LG.ancrer(reseau_ch, P, u)
        eid = f"ML-9{cle[0]:03d}"
        voisin = min(entites, key=lambda e: float(np.min(np.hypot(*(np.vstack(_points(e)) - P.mean(axis=0)).T))))
        photo = any(k in PREUVES_AJOUTS for k in cle)
        e = {"id": eid, "classe": "ligne", "type": "continue", "modulation": "continue", "couleur": "blanc",
             "usure": "2" if photo else "1", "couverture": 0.62 if photo else 0.88, "etat": "conserve", "groupe": "ajout_gam",
             "branche": voisin["branche"],
             "lien_v1": [], "ajout": {"gam": cle, "preuve": "; ".join(sorted({PREUVES_AJOUTS[k] for k in cle if k in PREUVES_AJOUTS}))},
             "mesures": {}}
        src_g = {"src": "gam", "ref": f"lignes GAM {', '.join(map(str, cle))} levées, non rattachées au v1"
                 + (" ; " + e["ajout"]["preuve"] if e["ajout"]["preuve"] else ""), "conf": "moyenne" if e["ajout"]["preuve"] else "faible"}
        role = ("rive", "bord de chaussée levé (GAM)")
        axe = P
        if anc is not None:
            ch, t_off, _ = anc
            sig, _, _ = projeter(ch.xy, P)
            s0, s1 = float(ch.s_de_sig(sig.min())), float(ch.s_de_sig(sig.max()))
            Q = ch.axe(t_off, s0, s1)
            _, d, _ = projeter(Q, densifier(P, 0.10)[0])
            if float(d.max()) <= LG.TOL_LAT_GAM:
                axe = Q
                e["ancrage"] = {"type": "xodr", "route": ch.route, "bords": ch.troncons(s0, s1), "s0": round(s0, 3), "s1": round(s1, 3),
                                "t_off_m": round(t_off, 4)}
                e["prov"] = {"geometrie": dict(src_g, src="xodr", ref=f"bord {ch.cle} + t_off médian du levé ; " + src_g["ref"]),
                             "ancrage": {"src": "xodr", "ref": "paquet_jardin_2026.xodr", "conf": "haute"}}
                role = LG.role_xodr(ch, 0.5 * (s0 + s1)) or role
                e["mesures"]["lateral_gam_p95_m"] = round(float(np.percentile(d, 95)), 4)
        if "ancrage" not in e:
            if anc is not None:
                role = LG.role_xodr(ch, 0.5 * (s0 + s1)) or role
                e["mesures"]["ecart_bord_xodr_max_m"] = round(float(d.max()), 4)
            axe = LG.GL.adoucir(P)
            e["ancrage"] = {"type": "axe", "source": "gam"}
            e["prov"] = {"geometrie": src_g}
        e["geom"] = ("LineString", M.douglas_peucker(axe, 0.001))
        e["longueur_m"] = round(float(abscisses(e["geom"][1])[-1]), 3)
        inter = sorted((round(z0, 3), round(z1, 3), zid) for zid, poly in emprises for z0, z1 in couper_polyligne(e["geom"][1], [poly]))
        e["interruptions"] = [[a, b] for a, b, _ in inter]
        if inter:
            e["interruptions_zebras"] = sorted({z for _, _, z in inter})
        w, pw = LG.largeur([], "continue", e["branche"], role)
        e["largeur_m"], e["role"] = w, role[0]
        e["prov"]["largeur_m"] = pw
        e["prov"]["usure"] = ({"src": "panoramax:20d1a815/r01_c02", "ref": "photo 20d1a815 (2025-08-31) : rive grise, salie par les débris du caniveau, "
                                                          "interrompue par endroits -> usure 2, couverture 0,62", "conf": "moyenne"} if photo else
                              {"src": "a_priori:ajout_gam", "ref": "usure 1 (couverture 0,88) : ligne de 2022 encore visible en 2025", "conf": "faible"})
        out.append(e)
    return out


# --------------------------------------------------------------------------- construction
def construire():
    """-> (features marquages, features correspondance, rapport)."""
    reseau = X.lire_xodr()
    objets = X.objets(reseau)
    validation_xodr = X.valider(reseau)
    zeb, dv_z, isolees, _ = PS.zebras()
    trav, dv_t = PS.traversees_cyclables()
    emprises = PS.emprises_zebras(zeb)
    lig, dv_l, mesures = LG.lignes(reseau, emprises)
    stop = [o for o in objets if o["sous_type"] == "stopLine"]
    tra, dv_tr = LG.transversales(reseau, stop)
    fle, dv_f, table_fleches, orphelins = SY.fleches(reseau, objets)
    sym, dv_s = SY.symboles(reseau)
    hach, dv_h = ZN.hachures()
    zz, dv_zz = ZN.zigzags()
    devenir = {}
    for d in (dv_z, dv_t, dv_l, dv_tr, dv_f, dv_s, dv_h, dv_zz):
        devenir.update(d)
    V = {m["id"]: m for m in M.v1()}
    # polygones gardés (forme non normée) : bandes isolées, aplats, surfaces colorées, divers
    restes = collections.defaultdict(list)
    for m in M.v1():
        if m["id"] in devenir or m["p"]["type"] == "fantome":
            continue
        t, g = m["p"]["type"], m["p"]["groupe"]
        if t == "passage_pieton_bande":
            restes[("zone", "bande_isolee", "bande de zébra isolée (non regroupable en passage)")].append(m)
        elif t == "hachures":
            restes[("zone", "aplat", "aplat / nez d'îlot peint")].append(m)
        elif t == "surface_coloree":
            restes[("zone", "surface_coloree", "surface colorée (résine)")].append(m)
        else:
            restes[("zone", "divers", "forme non normée (symbole divers)")].append(m)
    gardes = []
    for (classe, type_, note), ms in sorted(restes.items()):
        e, d = ZN.polygones_gardes(ms, classe, type_, "MZ", note)
        gardes += e
        devenir.update(d)
    fan, dv_g = ZN.fantomes()
    devenir.update(dv_g)
    # lignes discontinues d'un seul tiret « observé » sans suite : segment continu
    for e in lig:
        if e["type"] == "discontinue" and e["mesures"].get("n_tirets_v1") == 1 and e.get("modulation_v1") not in LG.modulations():
            e["type"] = "segment"
            e["modulation"] = "continue"
            for k in ("trait_m", "vide_m", "phase_m", "modulation_source", "n_tirets"):
                e.pop(k, None)
            e["prov"].pop("modulation", None)
            e["prov"].pop("phase_m", None)
            e["note"] = "tiret v1 isolé sans modulation lisible : segment peint sur tout l'axe"
    lig, journal = resoudre_recouvrements(lig, devenir)
    gardes = doublons_symboles(gardes, fle + sym, devenir)
    entites = lig + tra + zeb + trav + fle + sym + hach + zz + gardes + fan
    entites, retraits = retirer(entites, devenir)
    # marques neuves de 2025 : film continu (photo 2026-07-28 f8d91bb1 : zébras et damiers 2025 uniformes) ; l'usure
    # 1 du v1 (hypothèse « traces de roues aux feux ») est portée par le facteur de manque des traces de roues
    neuves_u0 = []
    for e in entites:
        if e["etat"] == "neuf_2025" and str(e["usure"]) not in ("0", "F"):
            e["usure_v1"] = e["usure"]
            e["usure"], e["couverture"] = "0", 0.97
            e.setdefault("prov", {})["usure"] = {"src": "a_priori:neuf_2025_u0", "ref": "repeint fin 2025 : usure 0 sauf preuve photo "
                                                 "(photo Panoramax 2026-07-28 f8d91bb1 : marques 2025 uniformes) ; usure v1 1 "
                                                 "(traces de roues aux feux) rendue par les traces de roues de la peinture", "conf": "moyenne"}
            neuves_u0.append(e["id"])
    libres = _orphelines(entites, loin=False)
    j_prol = prolonger([e for e in entites if e["classe"] == "ligne"], libres, emprises)
    # une ligne prolongée peut recouvrir un tiret ou un segment v1 porté par la même marque levée : absorption
    lig2, journal2 = resoudre_recouvrements([e for e in entites if e["classe"] == "ligne"], devenir)
    entites = lig2 + [e for e in entites if e["classe"] != "ligne"]
    journal += journal2
    orph = _orphelines(entites, exclure=[k for j in j_prol for k in j["gam"]])
    nouvelles = ajouts(orph, reseau, entites, emprises)
    entites += nouvelles
    # reprises (revue du 10/10, deuxième tour) : flèches hors des voies 2026, recouvrements, dégagement des bordures
    import marquages_bordures as MB
    import marquages_reprises as RP
    entites, j_hors_voie = RP.fleches_hors_voie(entites, reseau, devenir)
    j_gam = RP.suivre_gam(entites, reseau)
    j_int = RP.interrompre_lignes(entites)
    entites, j_bord = MB.degager(entites, reseau, devenir)
    j_rec = RP.resoudre(entites, devenir)
    j_sol = RP.sol_non_fabricable(entites, devenir)
    j_pt = RP.fleches_levees_pleine_taille(entites)
    entites, j_vides = RP.sans_peinture(entites, devenir)
    rec_restants = RP.recouvrements(entites)
    ids = [e["id"] for e in entites]
    doublons = [i for i, n in collections.Counter(ids).items() if n > 1]
    if doublons:
        raise RuntimeError(f"identifiants en double : {doublons[:10]}")
    manquants = sorted(set(V) - set(devenir))
    if manquants:
        raise RuntimeError(f"marquages v1 sans devenir : {manquants[:20]}")
    feats = [feature(e) for e in entites]
    ids_ok = set(ids)
    corr = []
    for mq in sorted(V):
        fate, eid, note = devenir[mq]
        p = V[mq]["p"]
        if fate in ("genere", "garde_simplifie", "a_vectoriser", "garde_non_fabrique") and eid not in ids_ok:
            raise RuntimeError(f"{mq} : entité {eid} absente")
        corr.append({"type": "Feature", "geometry": None,
                     "properties": {"id": mq, "type_v1": p["type"], "groupe_v1": p["groupe"], "source_v1": p["source"],
                                    "contour_raster_v1": V[mq]["raster"], "devenir": fate, "entite": eid, "note": note}})
    rapport = _rapport(entites, devenir, V, mesures, table_fleches, orphelins, validation_xodr, isolees)
    rapport["recouvrements_lignes"] = arrondi(journal)
    rapport["retires"] = [{"mq": mq, "note": devenir[mq][2]} for mq in sorted(V) if devenir[mq][0] == "retire"]
    rapport["retraits"] = retraits
    rapport["neuves_2025_usure_0"] = neuves_u0
    rapport["prolongements_gam"] = arrondi(j_prol)
    rapport["ajouts_gam"] = [{"id": e["id"], "gam": e["ajout"]["gam"], "longueur_m": e["longueur_m"], "ancrage": e["ancrage"]["type"],
                              "largeur_m": e["largeur_m"]} for e in nouvelles]
    rapport["gam_orphelines_restantes"] = sorted(k for ks in orph for k in ks if not any(k in e["ajout"]["gam"] for e in nouvelles))
    rapport["gam_non_rattachees_restantes"] = sorted(k for ks in libres for k in ks)
    rapport["reprises"] = arrondi({"fleches_hors_voie": j_hors_voie, "profils_gam": j_gam, "sol_non_fabricable": j_sol, "fleches_pleine_taille": j_pt,
                                   "lignes_sans_peinture": j_vides, "lignes_interrompues": j_int, "recouvrements": j_rec, "bordures": j_bord,
                                   "recouvrements_restants": [list(r) for r in rec_restants]})
    rapport["non_fabriques"] = sorted([e["id"], e["fabrication"]["raison"]] for e in entites if e.get("fabrication"))
    return feats, corr, rapport


def _pct(v, q):
    return round(float(np.percentile(v, q)), 4) if len(v) else None


def _rapport(entites, devenir, V, mesures, table_fleches, orphelins, validation_xodr, isolees):
    par_classe = collections.Counter((e["classe"], e["type"]) for e in entites)
    couverture = collections.defaultdict(collections.Counter)
    for mq, (fate, _, _) in devenir.items():
        couverture[V[mq]["p"]["type"]][fate] += 1
    raster = collections.Counter(devenir[m][0] for m in V if V[m]["raster"])
    lat = {t: np.concatenate([x for _, tt, x in mesures["lateral_gam"] if tt == t]) if any(tt == t for _, tt, _ in mesures["lateral_gam"]) else np.array([])
           for t in ("xodr", "axe")}
    ph = np.concatenate([v for _, v in mesures["phase_gam"]]) if mesures["phase_gam"] else np.array([])
    ph2 = np.concatenate([v for n, v in mesures["phase_gam"] if n >= 2]) if mesures["phase_gam"] else np.array([])
    ious = np.array([r["iou"] for r in table_fleches])
    lignes = [e for e in entites if e["classe"] == "ligne"]
    disc = [e for e in lignes if e["type"] == "discontinue"]
    velo = np.array([e["iou_v1"] for e in entites if e.get("type") == "velo"])
    return arrondi({
        "schema": SCHEMA_ID,
        "comptes_par_classe": {f"{c}/{t}": n for (c, t), n in sorted(par_classe.items())},
        "n_entites": len(entites),
        "couverture_v1": {"total": len(V), "par_type": {t: dict(sorted(c.items())) for t, c in sorted(couverture.items())},
                          "par_devenir": dict(sorted(collections.Counter(f for f, _, _ in devenir.values()).items())),
                          "contours_raster_v1": {"n": sum(1 for m in V.values() if m["raster"]), "devenir": dict(sorted(raster.items()))}},
        "echantillonneur_xodr": {k: validation_xodr[k] for k in ("n_echantillons", "p50_m", "p95_m", "max_m")},
        "lignes": {
            "n": len(lignes), "ancrage": dict(sorted(collections.Counter(e["ancrage"]["type"] + ("/" + e["ancrage"].get("source", "") if e["ancrage"]["type"] == "axe" else "") for e in lignes).items())),
            "types": dict(sorted(collections.Counter(e["type"] for e in lignes).items())),
            "modulations": dict(sorted(collections.Counter(f"{e['modulation']}/{e['modulation_source']}" for e in disc).items())),
            "lateral_gam_xodr_m": {"n": len(lat["xodr"]), "p50": _pct(lat["xodr"], 50), "p95": _pct(lat["xodr"], 95), "max": _pct(lat["xodr"], 100)},
            "lateral_gam_axe_m": {"n": len(lat["axe"]), "p50": _pct(lat["axe"], 50), "p95": _pct(lat["axe"], 95), "max": _pct(lat["axe"], 100)},
            "phase_tirets_gam_m": {"n": len(ph), "p50": _pct(ph, 50), "p95": _pct(ph, 95), "max": _pct(ph, 100)},
            "phase_tirets_gam_segments_2plus_m": {"n": len(ph2), "p50": _pct(ph2, 50), "p95": _pct(ph2, 95), "max": _pct(ph2, 100)},
            "segments_discontinus": len(disc), "segments_un_tiret": sum(1 for e in disc if e["mesures"]["n_tirets_v1"] == 1),
            "tirets_combles": sum(e["mesures"].get("tirets_combles", 0) for e in disc),
            "tirets_partiels_v1": sum(e["mesures"].get("tirets_partiels_v1", 0) for e in disc),
            "interrompues_zebras": sum(1 for e in lignes if e["interruptions"]),
            "largeurs_m": dict(sorted(collections.Counter(str(e["largeur_m"]) for e in lignes).items())),
        },
        "fleches": {"n": len(table_fleches), "iou": {"min": _pct(ious, 0), "p50": _pct(ious, 50), "moyenne": round(float(ious.mean()), 3) if len(ious) else None},
                    "par_gabarit": dict(sorted(collections.Counter(r["gabarit"] for r in table_fleches).items())),
                    "accord_direction_v1": sum(1 for r in table_fleches if SY.DIR_V1.get(r["direction_v1"]) in (None, r["gabarit"])),
                    "accord_xodr": sum(1 for r in table_fleches if r["xodr"] and r["xodr"][2] in (None, r["gabarit"])),
                    "objets_xodr_sans_fleche_v1": orphelins,
                    "trois_par_voie": SY.controle_trois_par_voie([e for e in entites if e["classe"] == "fleche"]),
                    "table": table_fleches},
        "velo_iou": {"n": len(velo), "p50": _pct(velo, 50), "note": "pictogramme du site (vélo couché, roues rondes) ≠ figurine IISR D1 : IoU bas attendu"},
        "zebras": [{"id": e["id"], "nb": e["nb_bandes"], "intervalle_m": e["intervalle_m"], "longueur_bande_m": e["longueur_bande_m"],
                    "coupures": e["coupures"], "residu_max_m": e["mesures"]["residu_bandes_max_m"]} for e in entites if e.get("type") == "zebra"],
        "bandes_isolees": sorted(m["id"] for m in isolees),
    })


def ecrire(sortie, feats, corr, zone="site"):
    sortie = Path(sortie)
    ent = {"schema": SCHEMA_ID, "famille": "marquages", "zone_pilote": zone, "emprise": "site complet (marquages_2026, 996 entités v1)",
           "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98, 216.30)"}
    ecrire_geojson(sortie / FICHIER, feats, "marquages", ent)
    ent2 = dict(ent, famille="marquages_correspondance")
    ecrire_geojson(sortie / FICHIER_CORR, corr, "marquages_correspondance", ent2)
    return sortie / FICHIER, sortie / FICHIER_CORR


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sortie", default=str(SORTIE / "base"))
    ap.add_argument("--rapport", help="écrit le rapport JSON (comptes, couverture, métriques)")
    a = ap.parse_args()
    feats, corr, rap = construire()
    ecrire(a.sortie, feats, corr)
    print(json.dumps({k: v for k, v in rap.items() if k not in ("fleches", "zebras")}, ensure_ascii=False, indent=1)[:6000])
    if a.rapport:
        Path(a.rapport).write_text(json.dumps(rap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
