#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Étape 3 de la bibliothèque « route_fr » : matériaux PBR CC0 manquants et fiches mesurées de TOUS les matériaux.

    python recon/pcg/assets_route/telecharger_materiaux_etape3.py --manifeste     # (re)construit le manifeste (API)
    python recon/pcg/assets_route/telecharger_materiaux_etape3.py                 # télécharge et prépare les nouveaux
    python recon/pcg/assets_route/telecharger_materiaux_etape3.py --materiaux enrobe_bbtm
    python recon/pcg/assets_route/telecharger_materiaux_etape3.py --fiches        # fiches seulement (mesures)

Ce script N'ÉCRASE AUCUN matériau existant de assets/lib/route_fr/materiaux (lus en parallèle par le générateur) :
il n'écrit que les dossiers des matériaux nouveaux listés dans CHOIX_E3, le catalogue local (écriture atomique) et
les fiches (fiche.json dans chaque dossier, recon/pcg/assets_route/fiches_materiaux_route.json versionné).

Fiche d'un matériau (mesurée sur les cartes livrées, pas recopiée) : albédo moyen linéaire et sRGB 8 bits (moyenne
de l'albédo sous-échantillonné au pas 4), L*a*b* moyen, écart-type de luminance (texture plus ou moins contrastée),
rugosité moyenne et écart-type (carte de rugosité, 0-1), métal moyen, résolution, côté physique de tuile (tile_m) et
son origine, licence, source et identifiant.

Choix des textures (17/10/2026) : vignettes 512 px des sources (sphères de rendu, 115 candidats) puis recadrages
NATIFS 340 × 340 px des albédos 1K des 22 candidats retenus (planches de travail hors dépôt, non réduites) ; les
raisons sont dans le champ « choix ». Licence de toutes les sources : CC0 1.0.
"""
import argparse
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(ICI))
import telecharger_materiaux_route as B  # noqa: E402  (entree_ambientcg, entree_polyhaven, lab_de_srgb8, LICENCE, T)

T = B.T
LIB = DEPOT / "assets" / "lib" / "route_fr"
SORTIE = LIB / "materiaux"
CACHE = LIB / "_cache_cc0"
MANIFESTE = ICI / "manifeste_materiaux_etape3.json"
FICHES = ICI / "fiches_materiaux_route.json"
MAT_SITE = DEPOT / "assets" / "lib" / "materiaux"

# Lab des cibles mesurées sur le site (assets/manifeste_cc0.json, champ « cible » : ortho 2022 ou photos Panoramax)
CIBLE_OCRE_SITE = [61.1, 3.34, 10.14]      # îlots ocre de la Revirée (ortho 2022, R − B ≈ +29) : enrobe_colore_ocre du site

CHOIX_E3 = [
    # --- enrobés (4K)
    dict(nom="enrobe_bbtm", source="ambientCG", id="Asphalt027A", res="4K", famille="enrobe", tile_m=2.0,
         tile_m_source="estimé : granulats de 3 à 6 px sur l'albédo 1K pour un BBTM 0/6-0/10, soit ≈ 2 mm/px",
         libelle="Béton bitumineux très mince (BBTM 0/6-0/10) : enrobé sombre à macrotexture ouverte, granulats serrés",
         choix="recadrage natif : grain grossier régulier, sombre et ouvert, sans fissure ni marquage ; Asphalt010 (bleuté, "
               "fin) et ph asphalt_01 (brun) rejetés"),
    dict(nom="enrobe_esu_gravillonne", source="Poly Haven", id="tarred_gravel", res="4K", famille="enrobe",
         libelle="Enduit superficiel d'usure (ESU, gravillonnage) : liant noir et gravillons clairs épars (routes "
                 "secondaires, accotements revêtus)",
         choix="seul candidat montrant des gravillons clairs isolés sur liant noir (aspect d'un enduit bicouche usé)"),
    dict(nom="enrobe_pelade_rapiece", source="ambientCG", id="Asphalt019", res="4K", famille="enrobe",
         libelle="Enrobé ancien sombre avec plage de pelade (arrachement de la couche de roulement, granulats clairs à nu) : "
                 "chaussée rapiécée ou dégradée",
         choix="recadrage natif : enrobé noir lisse et une plage arrachée claire à bord franc ; les « Road0xx » rapiécés "
               "portent des marquages américains"),
    dict(nom="enrobe_granulats_clairs", source="ambientCG", id="Asphalt023S", res="4K", famille="enrobe",
         libelle="BBSG à granulats clairs (gris moyen, gravillons blancs épars) : enrobé récent à granulats calcaires",
         choix="recadrage natif : gris neutre, gravillons clairs nets de 2-8 mm ; complète enrobe_clair_granulats (site, 2K, "
               "source pebble_cemented_floor recolorée)"),
    dict(nom="enrobe_colore_rouge", source="ambientCG", id="Asphalt029B", res="4K", famille="enrobe",
         libelle="Enrobé coloré rouge (liant pigmenté oxyde de fer) : couloirs bus, pistes cyclables, plateaux",
         choix="seul enrobé rouge homogène de la source (Asphalt029A sert déjà à resine_rouge) ; rouge vif de la source "
               "ramené vers un rouge brique",
         correction_cible_lab=[44.0, 28.0, 20.0],
         note_cible="estimation (aucune mesure sur site) : rouge brique d'un enrobé coloré vieilli, sRGB ≈ (150, 84, 70)"),
    dict(nom="enrobe_colore_ocre", source="ambientCG", id="Asphalt020S", res="4K", famille="enrobe",
         libelle="Enrobé ou résine ocre (îlots, trottoirs, plateaux) à grain fin",
         choix="enrobé gris fin à gravillons épars ramené sur la teinte ocre MESURÉE au site (îlots de la Revirée) ; "
               "version 4K du matériau du site (2K)",
         correction_cible_lab=CIBLE_OCRE_SITE,
         note_cible="assets/manifeste_cc0.json, enrobe_colore_ocre.cible : ortho 2022, îlots ocre de la Revirée"),
    # --- bétons, galets, résine (2K)
    dict(nom="beton_desactive_gros", source="Poly Haven", id="gravel_concrete_02", res="2K", famille="beton",
         libelle="Béton désactivé à gros granulats roulés (6/14) affleurants, teinte brun-gris",
         choix="recadrage natif : granulats roulés de 5-15 mm serrés (béton désactivé grossier) ; distinct de "
               "beton_desactive (granulats fins) et de beton_bordure"),
    dict(nom="beton_desactive_moyen", source="Poly Haven", id="gravel_embedded_concrete", res="2K", famille="beton",
         libelle="Béton désactivé gris à granulats moyens (4/10), trottoirs et parvis",
         choix="recadrage natif : granulats gris serrés, matrice grise ; intermédiaire entre beton_desactive et "
               "beton_desactive_gros"),
    dict(nom="galets_scelles", source="Poly Haven", id="rock_embedded_concrete", res="2K", famille="mineral",
         libelle="Galets roulés 5-8 cm scellés au mortier (pavage en galets, couronnes et nez d'îlots, caniveaux pavés)",
         choix="recadrage natif : galets ovales jointifs dans un mortier gris (« calade ») ; seul candidat à galets scellés"),
    dict(nom="resine_gravillonnee_beige", source="Poly Haven", id="pebble_cemented_floor", res="2K", famille="resine",
         libelle="Gravillons liés à la résine (sol drainant beige), trottoirs, pieds d'arbres, îlots",
         choix="petits gravillons jointifs liés (aspect d'un sol en gravillons-résine) ; même source que "
               "enrobe_clair_granulats du site mais recolorée en beige",
         correction_cible_lab=[66.0, 3.0, 14.0],
         note_cible="estimation : beige clair d'un gravillon-résine (sRGB ≈ 175, 160, 140)"),
    dict(nom="gravillons_stabilises", source="Poly Haven", id="floor_pebbles_01", res="2K", famille="mineral",
         libelle="Gravillons roulés sur sable stabilisé (allées, accotements, pieds d'arbres)",
         choix="recadrage natif : gravillons roulés épars sur matrice sableuse"),
    dict(nom="gravillons_roules_gris", source="ambientCG", id="Gravel041", res="2K", famille="mineral", tile_m=0.6,
         tile_m_source="estimé : gravillons 8/16 (≈ 12 mm) de 15 à 30 px sur l'albédo 1K, soit ≈ 0,6 mm/px",
         libelle="Gravillons roulés gris-vert 8/16 en couche (îlots minéraux, noues)",
         choix="recadrage natif : gravillons roulés jointifs gris-vert (alluvions alpines) ; complète gravillons_ilot du site"),
    # --- pavés, dalles (2K)
    dict(nom="paves_granit_carres", source="Poly Haven", id="cobblestone_square", res="2K", famille="paves",
         libelle="Pavés de granit gris carrés (≈ 9 cm : 90 px sur l'albédo 1K d'une tuile de 1,0 m) clivés, joints sablés et moussus",
         choix="recadrage natif : pavés gris clivés à arêtes émoussées, joints larges (anneaux et couronnes de giratoire)"),
    dict(nom="paves_beton_chevrons", source="Poly Haven", id="herringbone_pavement_03", res="2K", famille="paves",
         libelle="Pavés béton gris foncé 20 × 10 en chevrons (voies piétonnes, plateaux)",
         choix="recadrage natif : pavés rectangulaires gris anthracite à joints fins, appareillage en chevrons"),
    dict(nom="dalles_beton_gazon", source="Poly Haven", id="grass_concrete_pavement", res="2K", famille="dalles",
         libelle="Dalles béton-gazon (alvéoles engazonnées) : stationnements, accotements stabilisés",
         choix="recadrage natif : plots béton carrés réguliers et herbe sèche dans les alvéoles"),
    dict(nom="dalles_beton_ocre", source="Poly Haven", id="concrete_pavers_02", res="2K", famille="dalles",
         libelle="Dalles béton rectangulaires ocre-brun à joints larges",
         choix="recadrage natif : dalles rectangulaires teintées, joints marqués"),
    # --- sols organiques, bois (2K)
    dict(nom="brf_copeaux_frais", source="ambientCG", id="WoodChips003", res="2K", famille="sol",
         libelle="Bois raméal fragmenté frais / copeaux clairs (paillage de massifs et de pieds d'arbres)",
         choix="vignettes : copeaux clairs fins ; WoodChips002 (vu en recadrage natif, plus grossier) écarté car son albédo n'est "
               "pas carré (2048 × 1024) ; complète brf_bois_concasse et brf_bois_gris du site (vieillis)"),
    dict(nom="terre_vegetale", source="ambientCG", id="Ground048", res="2K", famille="sol",
         libelle="Terre végétale sombre humifère (massifs, fosses d'arbres, chantier)",
         choix="recadrage natif : terre brun foncé à débris organiques"),
    dict(nom="terre_battue", source="Poly Haven", id="dirt_floor", res="2K", famille="sol",
         libelle="Terre battue compactée brun clair (chemins, accotements non revêtus)",
         choix="recadrage natif : terre sèche compactée, débris fins"),
    dict(nom="bois_brut_grise", source="Poly Haven", id="rough_wood", res="2K", famille="bois",
         libelle="Bois brut grisé (mélèze, chêne vieilli) : bornes bois, lames de bancs, rondins",
         choix="vignettes : seul bois d'extérieur grisé sans joints de lames (convient aux éléments unitaires)"),
    # --- métal (GAM : RAL 7024)
    dict(nom="acier_thermolaque_7024", source="ambientCG", id="Metal027", res="2K", famille="metal", tile_m=1.0,
         tile_m_source="estimé (grain de poudre fin)",
         libelle="Acier thermolaqué gris graphite RAL 7024 (gamme de Grenoble-Alpes Métropole : potelets, barrières, arceaux)",
         choix="même source que acier_thermolaque_7016, moyenne ramenée sur RAL 7024 (GAM fiche n° 16 p. 4 : potelets, "
               "barrières, arceaux en RAL 7024)",
         correction_cible_srgb=[0x47, 0x4A, 0x51],
         note_cible="RAL 7024 gris graphite ≈ sRGB #474A51 (valeur RAL usuelle, approximation écran)"),
]


def construire_manifeste():
    sortie = []
    for c in CHOIX_E3:
        print("API", c["source"], c["id"], flush=True)
        e = B.entree_ambientcg(c) if c["source"] == "ambientCG" else B.entree_polyhaven(c)
        tile = c.get("tile_m") or e.pop("tile_m_api", None)
        e.pop("tile_m_api", None)
        src_tile = c.get("tile_m_source") or ("API Poly Haven « dimensions » (mm)" if c["source"] == "Poly Haven"
                                              else "API ambientCG dimensionX (cm)")
        if not tile:
            tile, src_tile = 2.0, "estimé (aucune dimension publiée par la source) : 2,0 m"
        m = dict(nom=c["nom"], categorie="materiaux", type="sol_tuilable" if c["famille"] not in ("metal", "bois") else "surface_tuilable",
                 famille=c["famille"], libelle=c["libelle"], choix=c["choix"], priorite=1, source=c["source"], id=c["id"],
                 resolution_cible=c["res"], licence=B.LICENCE, tile_m=round(float(tile), 4), tile_m_source=src_tile,
                 uv={"primvar": "st1", "repere": "UV en mètres (st1) ; UsdTransform2d scale = 1/tile_m"}, etape="route_fr étape 3", **e)
        lab = None
        if c.get("correction_cible_srgb"):
            lab = B.lab_de_srgb8(c["correction_cible_srgb"])
        if c.get("correction_cible_lab"):
            lab = list(c["correction_cible_lab"])
        if lab:
            m["correction_teinte"] = dict(espace="CIE L*a*b* (D65)", gain_L=1.0, decalage_L=0.0, gain_ab=1.0, decalage_a=0.0,
                                          decalage_b=0.0, lab_cible=lab, note=c.get("note_cible", ""))
            m["cible"] = dict(lab=lab, note=c.get("note_cible", ""))
        if c["famille"] == "metal":
            m["metal_force"] = None
        sortie.append(m)
    man = dict(version=1, date=datetime.date.today().isoformat(),
               description="Matériaux PBR CC0 de l'étape 3 de la bibliothèque route_fr. Script : "
                           "recon/pcg/assets_route/telecharger_materiaux_etape3.py ; traitement commun : assets/telecharger_cc0.py.",
               licence_sources="CC0 1.0 (ambientCG https://docs.ambientcg.com/license/ ; Poly Haven https://polyhaven.com/license)",
               materiaux=sortie)
    ecrire_json_atomique(MANIFESTE, man)
    print("manifeste :", MANIFESTE, len(sortie), "matériaux")
    return man


def ecrire_json_atomique(chemin, donnees):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=chemin.name + ".", suffix=".tmp", dir=str(chemin.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=1, ensure_ascii=False)
    os.replace(tmp, chemin)


def preparer(man, noms=None, forcer=False):
    existants_avant = {d.name for d in SORTIE.iterdir() if d.is_dir()} if SORTIE.exists() else set()
    nouveaux = {c["nom"] for c in CHOIX_E3}
    conflit = (existants_avant & nouveaux) - {c["nom"] for c in CHOIX_E3 if (SORTIE / c["nom"] / "meta.json").exists()
                                                and json.loads((SORTIE / c["nom"] / "meta.json").read_text(encoding="utf-8"))
                                                .get("version_manifeste", "").startswith("route_fr_e3")}
    if conflit:
        raise RuntimeError(f"noms déjà pris par des matériaux existants (on n'écrase rien) : {sorted(conflit)}")
    bilan, erreurs = [], []
    for m in man["materiaux"]:
        if noms and m["nom"] not in noms:
            continue
        a = argparse.Namespace(resolution=m["resolution_cible"], complet=True, cache=str(CACHE), hauteur=True,
                               forcer=forcer, correction="cible", version_manifeste=f"route_fr_e3-{man['version']}")
        try:
            meta = T.traiter(m, a, str(SORTIE))
            bilan.append(meta)
        except Exception as e:  # noqa: BLE001
            erreurs.append((m["nom"], repr(e)))
            print("ERREUR", m["nom"], e, flush=True)
    return bilan, erreurs


# ---------------------------------------------------------------------------------------------- fiches
def _moy_carte(p, pas=4):
    im = Image.open(p)
    a = np.asarray(im, np.float64)
    if a.ndim == 3:
        a = a[..., 0]
    a = a / (65535.0 if a.max() > 255 else 255.0)
    a = a[::pas, ::pas]
    return float(a.mean()), float(a.std())


def fiche(dossier):
    mf = dossier / "meta.json"
    if not mf.exists():
        return None
    m = json.loads(mf.read_text(encoding="utf-8"))
    tex = {t["role"]: dossier / t["fichier"] for t in m.get("textures", []) if isinstance(t, dict) and "role" in t}
    f = dict(nom=m.get("nom", dossier.name), libelle=m.get("libelle"), bibliotheque=("route_fr" if dossier.parent == SORTIE else "site"),
             source=m.get("source"), source_id=m.get("source_id"), page=m.get("page"),
             licence=(m.get("licence") or {}).get("nom") if isinstance(m.get("licence"), dict) else m.get("licence"),
             resolution=m.get("resolution"), tile_m=m.get("tile_m"), tile_m_source=m.get("tile_m_source"),
             correction_teinte=(m.get("correction_teinte") or {}).get("appliquee"),
             usd=f"{dossier.name}/{m.get('usd', dossier.name + '.usda')}")
    if "albedo" in tex and tex["albedo"].exists():
        a = np.asarray(Image.open(tex["albedo"]).convert("RGB"), np.float64)[::4, ::4] / 255.0
        lin = T.srgb_vers_lin(a.reshape(-1, 3))
        moy_lin = lin.mean(0)
        lum = lin @ np.array([0.2126, 0.7152, 0.0722])
        lab = T.rgb_vers_lab(a.reshape(-1, 3)).mean(0)
        f["albedo_moyen_lineaire"] = [round(float(v), 4) for v in moy_lin]
        f["albedo_moyen_srgb8"] = [int(round(float(T.lin_vers_srgb(v)) * 255)) for v in moy_lin]
        f["luminance_albedo"] = dict(moyenne=round(float(lum.mean()), 4), ecart_type=round(float(lum.std()), 4),
                                     p05=round(float(np.percentile(lum, 5)), 4), p95=round(float(np.percentile(lum, 95)), 4))
        f["lab_moyen"] = [round(float(v), 2) for v in lab]
    else:
        f["albedo_moyen_lineaire"] = None
    for role, cle in (("rugosite", "rugosite"), ("metal", "metal"), ("ao", "occlusion")):
        if role in tex and tex[role].exists():
            mo, et = _moy_carte(tex[role])
            f[cle] = dict(moyenne=round(mo, 3), ecart_type=round(et, 3), source="carte " + tex[role].name)
        else:
            f[cle] = None
    if f.get("rugosite") is None:
        f["rugosite"] = dict(moyenne=None, note="pas de carte : valeur constante de l'USD")
    f["mesure"] = ("moyennes sur l'albédo et les cartes livrées, sous-échantillonnées au pas 4 ; albédo linéaire = sRGB "
                   "décodé (IEC 61966-2-1) ; luminance Rec. 709")
    return f


def ecrire_fiches():
    toutes = []
    for base in (SORTIE, MAT_SITE):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            fi = fiche(d)
            if fi is None:
                continue
            if base == SORTIE:
                ecrire_json_atomique(d / "fiche.json", fi)
            toutes.append(fi)
    nouveaux = {c["nom"] for c in CHOIX_E3}
    for fi in toutes:
        fi["etape3"] = fi["nom"] in nouveaux and fi["bibliotheque"] == "route_fr"
    ecrire_json_atomique(FICHES, dict(schema="route_fr/fiches_materiaux/1.0", date=datetime.date.today().isoformat(),
                                      script="recon/pcg/assets_route/telecharger_materiaux_etape3.py --fiches",
                                      note="mesures sur les textures livrées (assets/lib/route_fr/materiaux et "
                                           "assets/lib/materiaux) ; les matériaux du site ne sont pas modifiés",
                                      materiaux=toutes))
    print("fiches :", FICHES, len(toutes), "matériaux")
    return toutes


def catalogue_local():
    """assets/lib/route_fr/materiaux/catalogue.json : même format que telecharger_materiaux_route.catalogue(), écriture atomique."""
    ent = []
    for d in sorted(SORTIE.iterdir()):
        mf = d / "meta.json"
        if not d.is_dir() or not mf.exists():
            continue
        m = json.loads(mf.read_text(encoding="utf-8"))
        ent.append(dict(nom=m["nom"], libelle=m.get("libelle"), source=m.get("source"), source_id=m.get("source_id"),
                        page=m.get("page"), licence=(m.get("licence") or {}).get("nom") if isinstance(m.get("licence"), dict) else m.get("licence"),
                        resolution=m.get("resolution"), tile_m=m.get("tile_m"), usd=f"{d.name}/{m.get('usd')}",
                        textures=[t["fichier"] for t in m.get("textures", [])],
                        octets=sum(t.get("octets", 0) for t in m.get("textures", []))))
    cat = dict(version=1, date=datetime.datetime.now().isoformat(timespec="seconds"), racine="assets/lib/route_fr/materiaux",
               materiaux=ent, total_octets=sum(e["octets"] for e in ent))
    ecrire_json_atomique(SORTIE / "catalogue.json", cat)
    print("catalogue local :", len(ent), "matériaux,", round(cat["total_octets"] / 1e6), "Mo")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifeste", action="store_true")
    ap.add_argument("--materiaux", nargs="*")
    ap.add_argument("--forcer", action="store_true")
    ap.add_argument("--fiches", action="store_true")
    a = ap.parse_args()
    if a.fiches:
        ecrire_fiches()
        return
    man = construire_manifeste() if (a.manifeste or not MANIFESTE.exists()) else json.loads(MANIFESTE.read_text(encoding="utf-8"))
    if a.manifeste:
        return
    bilan, err = preparer(man, a.materiaux, a.forcer)
    catalogue_local()
    ecrire_fiches()
    print(len(bilan), "matériaux prêts ;", len(err), "erreur(s)")
    for n, e in err:
        print("  échec", n, e)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
