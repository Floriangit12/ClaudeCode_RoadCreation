#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Matériaux PBR CC0 de la bibliothèque « route_fr » (ambientCG, Poly Haven) : choix, manifeste, téléchargement.

    python recon/pcg/assets_route/telecharger_materiaux_route.py --manifeste      # (re)construit le manifeste (API)
    python recon/pcg/assets_route/telecharger_materiaux_route.py                  # télécharge et prépare tout
    python recon/pcg/assets_route/telecharger_materiaux_route.py --materiaux enrobe_neuf granit_gris_flamme
    python recon/pcg/assets_route/telecharger_materiaux_route.py --peinture       # peinture routière procédurale
    python recon/pcg/assets_route/telecharger_materiaux_route.py --catalogue      # catalogue.json seulement

Sorties (non versionnées, régénérables) : assets/lib/route_fr/materiaux/<nom>/{<nom>.usda, meta.json, textures/}
et assets/lib/route_fr/materiaux/catalogue.json. Cache des archives : assets/lib/route_fr/_cache_cc0/.
Versionnés : ce script et recon/pcg/assets_route/manifeste_materiaux_route.json (URL, tailles, md5, licence).

Réutilise assets/telecharger_cc0.py (traitement, correction Lab, écriture USD UsdPreviewSurface, contrôle des tailles) :
seule la liste des matériaux et la résolution changent. Résolution : 4K pour les enrobés (toutes les cartes en 4K),
2K pour le reste (toutes les cartes en 2K, mode --complet), carte de hauteur 16 bits incluse.

Choix des textures : comparaison visuelle de recadrages natifs 512 px (pas de réduction) des albédos 1K candidats
(62 candidats, planches de travail hors dépôt) ; les raisons sont dans le champ « choix » de chaque entrée.
Licence de toutes les sources : CC0 1.0 (ambientCG : https://docs.ambientcg.com/license/ ;
Poly Haven : https://polyhaven.com/license).
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
sys.path.insert(0, str(DEPOT / "assets"))
import telecharger_cc0 as T  # noqa: E402

LIB = DEPOT / "assets" / "lib" / "route_fr"
SORTIE = LIB / "materiaux"
CACHE = LIB / "_cache_cc0"
MANIFESTE = ICI / "manifeste_materiaux_route.json"
UA = {"User-Agent": "MeylanADAS-librairie/1.0 (route_fr)"}
LICENCE = {"nom": "CC0 1.0 Universal (transfert dans le domaine public)",
           "url": "https://creativecommons.org/publicdomain/zero/1.0/", "attribution_requise": False}

# ------------------------------------------------------------------------------------------------ choix
# tile_m : côté physique de la texture (m). Poly Haven : champ « dimensions » de l'API (mm) ; ambientCG : dimensionX
# (cm) quand il est renseigné, sinon estimation d'après la taille des éléments (indiquée dans tile_m_source).
CHOIX = [
    # --- enrobés (4K)
    dict(nom="enrobe_neuf", source="Poly Haven", id="clean_asphalt", res="4K", famille="enrobe",
         libelle="Enrobé neuf gris foncé à grain fin (BBSG 0/10 de quelques mois), teinte homogène",
         choix="gris neutre, grain fin, sans marquage ni réparation ; préféré à Asphalt033 (brunâtre) et Asphalt020L (trop clair)"),
    dict(nom="enrobe_neuf_frais", source="Poly Haven", id="asphalt_track", res="4K", famille="enrobe",
         libelle="Enrobé tout juste mis en œuvre (< 1 mois) : liant noir, granulats peu visibles",
         choix="seul candidat réellement noir (bitume frais), granularité fine régulière"),
    dict(nom="enrobe_bbsg_use", source="ambientCG", id="Asphalt015", res="4K", famille="enrobe", tile_m=1.6,
         tile_m_source="estimé : gros granulats de 8-12 px sur l'albédo 1K, soit ≈ 1,6 mm/px pour un BBSG 0/10 (D ≈ 10-14 mm)",
         libelle="BBSG usé gris moyen, liant érodé, granulats 0/10 apparents (5 à 10 ans de trafic)",
         choix="gris neutre, granulats apparents nets : aspect le plus courant des chaussées urbaines françaises vieillies"),
    dict(nom="enrobe_bbsg_ancien", source="ambientCG", id="Asphalt031", res="4K", famille="enrobe", tile_m=2.0,
         tile_m_source="manifeste assets/manifeste_cc0.json (estimé d'après la taille des granulats)",
         libelle="BBSG ancien gris clair oxydé, texture fermée (réseau de fissures pontées dans la version d'origine)",
         choix="même source et même étalonnage que assets/lib/materiaux/enrobe_bbsg_ancien (ortho 2022 du site), ici en 4K",
         correction_depuis_manifeste="enrobe_bbsg_ancien"),
    dict(nom="enrobe_fissure", source="Poly Haven", id="asphalt_02", res="4K", famille="enrobe",
         libelle="Enrobé gris usé avec fissure longitudinale ouverte et granulats apparents",
         choix="fissure franche unique et granulats nets ; candidat road_damaged rejeté (brun, sale)"),
    dict(nom="enrobe_faience", source="ambientCG", id="Asphalt021", res="4K", famille="enrobe",
         libelle="Enrobé faïencé (fissuration en mailles, « peau de crocodile ») à joints de bitume sombres",
         choix="faïençage net à mailles de 5-15 cm, gris neutre"),
    dict(nom="enrobe_reprise", source="Poly Haven", id="asphalt_pit_lane", res="4K", famille="enrobe",
         libelle="Enrobé de reprise (rapiéçage, tranchée) plus sombre et plus lisse que l'enrobé voisin",
         choix="même source que assets/lib/materiaux/enrobe_reprise_tranchee (2K) ; ici en 4K. Les textures « Road001-006 » "
               "(rapiéçages) sont rejetées : marquages américains incrustés (lignes jaunes et blanches)"),
    dict(nom="enrobe_grenaille", source="ambientCG", id="Asphalt030", res="4K", famille="enrobe",
         libelle="Enrobé grenaillé clair : liant décapé, granulats clairs apparents (traitement de surface)",
         choix="granulats clairs serrés sur fond gris-beige ; Asphalt027C (trop sombre) et gravel_embedded_concrete_02 "
               "(béton) rejetés"),
    # --- bétons, pierres, pavés, dalles (2K)
    dict(nom="beton_balaye", source="Poly Haven", id="brushed_concrete_04", res="2K", famille="beton",
         libelle="Béton balayé (stries transversales de balai) avec joints de retrait sciés",
         choix="seul candidat à stries parallèles de balai ; brushed_concrete (lissé à la truelle) rejeté"),
    dict(nom="beton_desactive", source="Poly Haven", id="granular_concrete", res="2K", famille="beton",
         libelle="Béton désactivé fin (granulats 4/10 affleurants), trottoirs et îlots",
         choix="granulats fins dispersés sur matrice grise"),
    dict(nom="beton_prefa_lisse", source="ambientCG", id="Concrete006", res="2K", famille="beton", tile_m=1.0,
         tile_m_source="estimé : bullage de 1 à 4 mm (2 à 8 px sur l'albédo 2K)",
         libelle="Béton préfabriqué vibré gris, peau de ciment lisse à bullage fin (bordures et caniveaux neufs ou récents)",
         choix="comparaison de recadrages natifs 512 px (16/10/2026) de Concrete003/006/014/016/025/027-030/034/037/044A : "
               "Concrete006 = seule peau lisse grise à petites bulles ; beton_bordure (Concrete037, assets/lib/materiaux) "
               "montre des granulats roulés de 1-3 cm (béton vieilli ou désactivé), trop grossier pour une bordure récente"),
    dict(nom="granit_gris_flamme", source="ambientCG", id="Granite002A", res="2K", famille="pierre", tile_m=1.0,
         tile_m_source="estimé : cristaux de 4-12 mm (granit gris à grain moyen)",
         libelle="Granit gris clair à grain moyen pour bordures et dalles flammées ou bouchardées",
         choix="granit gris à feldspath blanc et biotite noire (type granit gris bleu des bordures, cf. Angers CPU) ; "
               "la source est un plan de travail poli : rugosité relevée (flammé ≈ 0,6-0,9)",
         rugosite=dict(gain=0.3, decalage=0.6, motif="flammé/bouchardé : la rugosité polie de la source est remontée")),
    dict(nom="paves_beton_rect", source="ambientCG", id="PavingStones081", res="2K", famille="paves", tile_m=0.82,
         tile_m_source="estimé : pavé de 20 × 10 cm ≈ 250 px sur l'albédo 1K",
         libelle="Pavés béton rectangulaires gris 20 × 10 cm chanfreinés, pose en panneresse croisée",
         choix="pavés rectangulaires gris à chanfrein net"),
    dict(nom="paves_beton_autobloquant", source="ambientCG", id="PavingStones099", res="2K", famille="paves",
         libelle="Pavés béton autobloquants gris (double T), joints sablés",
         choix="forme autobloquante courante (parkings, trottoirs), gris neutre"),
    dict(nom="paves_pierre_scies", source="Poly Haven", id="cobblestone_pavement", res="2K", famille="paves",
         libelle="Pavés de pierre sciés rectangulaires (teintes variées), joints mortier",
         choix="pavés sciés à faces planes (accessibles PMR, cf. Angers CPU « pavés doivent être sciés »)"),
    dict(nom="paves_mosaique", source="Poly Haven", id="cobblestone_04", res="2K", famille="paves",
         libelle="Pavés mosaïque ≈ 10 × 10 cm sombres (granit ou basalte) en grille, joints terreux",
         choix="petits pavés carrés en grille régulière"),
    dict(nom="paves_granit_anciens", source="ambientCG", id="PavingStones070", res="2K", famille="paves",
         libelle="Pavés de granit anciens éclatés (≈ 14 × 14 cm), joints enherbés",
         choix="pavés éclatés à arêtes émoussées, herbe dans les joints (vieux centres, anneaux d'îlots)"),
    dict(nom="dalles_beton_grises", source="Poly Haven", id="concrete_tiles_02", res="2K", famille="dalles",
         libelle="Dalles béton grises rectangulaires jointives (trottoir), joints fins",
         choix="dalles grises lisses à joints fins"),
    dict(nom="dalles_beton_joint_gravier", source="Poly Haven", id="large_square_pattern_01", res="2K", famille="dalles",
         libelle="Grandes dalles béton grises à joints ouverts garnis de gravillons et mousse",
         choix="dalles carrées à joints larges (abords, parvis)"),
    dict(nom="dalles_beton_40", source="ambientCG", id="PavingStones136", res="2K", famille="dalles", tile_m=1.6,
         tile_m_source="estimé : dalle de 40 × 40 cm ≈ 256 px sur l'albédo 1K",
         libelle="Dalles béton carrées 40 × 40 cm beige-gris, joints moussus",
         choix="dalles carrées à joints fins colonisés"),
    # --- revêtements colorés, minéraux
    dict(nom="resine_rouge", source="ambientCG", id="Asphalt029A", res="2K", famille="resine", tile_m=2.0,
         tile_m_source="estimé (texture homogène sans élément d'échelle)",
         libelle="Revêtement coloré rouge (résine gravillonnée ou enrobé coloré) des pistes et bandes cyclables",
         choix="seul rouge homogène ; à désaturer dans le moteur pour un rouge-brique usé"),
    dict(nom="galets_roules", source="Poly Haven", id="dry_river_pebbles", res="2K", famille="mineral",
         libelle="Galets roulés 3-12 cm (beige et noirs) en paillage décoratif d'îlot",
         choix="galets de rivière secs, mélange clair/sombre"),
    # --- métaux (supports, potelets, feux, garde-corps)
    dict(nom="acier_galvanise", source="ambientCG", id="Metal014", res="2K", famille="metal", tile_m=1.0,
         tile_m_source="estimé (plages de zinc de 5-30 cm)",
         libelle="Acier galvanisé à chaud vieilli (poteaux, platines, garde-corps de pont)",
         choix="plages claires/sombres de galvanisation vieillie"),
    dict(nom="acier_thermolaque_7016", source="ambientCG", id="Metal027", res="2K", famille="metal", tile_m=1.0,
         tile_m_source="estimé (grain de poudre fin)",
         libelle="Acier thermolaqué gris anthracite (≈ RAL 7016) finition sablé-givré : potelets, barrières, mâts",
         choix="poudre noire fine recolorée en RAL 7016 (Angers CPU : potelets, barrières RAL 7016 sablé-givré)",
         correction_cible_srgb=[0x38, 0x3E, 0x42]),
    dict(nom="plastique_noir_feux", source="ambientCG", id="Metal027", res="2K", famille="metal", tile_m=1.0,
         tile_m_source="estimé (grain fin)",
         libelle="Polycarbonate / poudre noir mat des boîtiers, visières et pattes de feux",
         choix="même source que acier_thermolaque_7016, gardée noire (fiches Trafic : boîtier, visières en polycarbonate noir)",
         metal_force=0.0),
    dict(nom="inox_brosse", source="ambientCG", id="Metal009", res="2K", famille="metal", tile_m=0.5,
         tile_m_source="estimé (stries de brossage)",
         libelle="Inox brossé (têtes de potelets, mains courantes inox)", choix="stries de brossage régulières"),
]


# ------------------------------------------------------------------------------------------------ API
def lire_json(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("  nouvel essai", url, e)
            time.sleep(3 * (k + 1))
    raise RuntimeError(url)


def entree_ambientcg(c):
    d = lire_json(f"https://ambientcg.com/api/v2/full_json?id={c['id']}&include=downloadData,tagData")
    a = d["foundAssets"][0]
    tels = {}
    for cat in a["downloadFolders"]["default"]["downloadFiletypeCategories"].values():
        for t in cat["downloads"]:
            if t["attribute"] in ("1K-JPG", "2K-JPG", "4K-JPG"):
                tels[t["attribute"][:2]] = dict(format="zip", url=t["fullDownloadPath"], taille_o=t["size"],
                                                fichier=t["fileName"])
    dim = a.get("dimensionX") or 0
    return dict(page=f"https://ambientcg.com/a/{c['id']}", auteur="Lennart Demes (ambientCG)", type_source=a.get("dataType"),
                methode=a.get("creationMethodName"), telechargements=tels,
                cartes_zip={"albedo": "*_Color.jpg", "normale": "*_NormalGL.jpg", "rugosite": "*_Roughness.jpg",
                            "ao": "*_AmbientOcclusion.jpg", "hauteur": "*_Displacement.jpg", "opacite": "*_Opacity.jpg",
                            "metal": "*_Metalness.jpg"},
                tile_m_api=(dim / 100.0 if dim else None))


def entree_polyhaven(c):
    info = lire_json(f"https://api.polyhaven.com/info/{c['id']}")
    fil = lire_json(f"https://api.polyhaven.com/files/{c['id']}")
    roles = {"albedo": ("Diffuse", ("jpg", "png")), "normale": ("nor_gl", ("jpg", "png")), "rugosite": ("Rough", ("jpg", "png")),
             "ao": ("AO", ("jpg", "png")), "hauteur": ("Displacement", ("png", "jpg"))}
    tels = {}
    for res in ("1K", "2K", "4K"):
        fichiers = {}
        for role, (cle, fmts) in roles.items():
            r = (fil.get(cle) or {}).get(res.lower()) or {}
            for f in fmts:
                if f in r:
                    fichiers[role] = dict(url=r[f]["url"], taille_o=r[f]["size"], md5=r[f]["md5"])
                    break
        if "albedo" in fichiers:
            tels[res] = dict(format="fichiers", fichiers=fichiers, taille_o=sum(v["taille_o"] for v in fichiers.values()))
    dims = info.get("dimensions") or [0, 0]
    return dict(page=f"https://polyhaven.com/a/{c['id']}", auteur=", ".join(info.get("authors", {}).keys()) + " (Poly Haven)",
                type_source="texture", categorie_source=info.get("category"), telechargements=tels,
                tile_m_api=(round(dims[0] / 1000.0, 3) if dims[0] else None))


def lab_de_srgb8(rgb):
    import numpy as np
    a = np.array(rgb, float).reshape(1, 3) / 255.0
    return [round(float(v), 2) for v in T.rgb_vers_lab(a)[0]]


def construire_manifeste():
    man0 = json.loads((DEPOT / "assets" / "manifeste_cc0.json").read_text(encoding="utf-8"))
    par_nom = {m["nom"]: m for m in man0["materiaux"]}
    sortie = []
    for c in CHOIX:
        print("API", c["source"], c["id"])
        e = entree_ambientcg(c) if c["source"] == "ambientCG" else entree_polyhaven(c)
        tile = c.get("tile_m") or e.pop("tile_m_api")
        e.pop("tile_m_api", None)
        if not tile:
            raise RuntimeError(f"{c['nom']} : tile_m inconnu")
        m = dict(nom=c["nom"], categorie="materiaux", type="sol_tuilable" if c["famille"] != "metal" else "surface_tuilable",
                 famille=c["famille"], libelle=c["libelle"], choix=c["choix"], priorite=1, source=c["source"], id=c["id"],
                 resolution_cible=c["res"], licence=LICENCE, tile_m=tile,
                 tile_m_source=c.get("tile_m_source") or ("API Poly Haven « dimensions » (mm)" if c["source"] == "Poly Haven"
                                                          else "API ambientCG dimensionX (cm)"),
                 uv={"primvar": "st1", "repere": "UV en mètres (st1) ; UsdTransform2d scale = 1/tile_m"}, **e)
        if c.get("rugosite"):
            m["rugosite"] = c["rugosite"]
        if c.get("correction_depuis_manifeste"):
            src = par_nom[c["correction_depuis_manifeste"]]
            m["correction_teinte"] = src["correction_teinte"]
            m["cible"] = src.get("cible")
        if c.get("correction_cible_srgb"):
            lab = lab_de_srgb8(c["correction_cible_srgb"])
            m["correction_teinte"] = dict(espace="CIE L*a*b* (D65)", gain_L=1.0, decalage_L=0.0, gain_ab=1.0, decalage_a=0.0,
                                          decalage_b=0.0, lab_cible=lab,
                                          note=f"moyenne ramenée sur sRGB {c['correction_cible_srgb']} (≈ RAL 7016 anthracite, "
                                               "valeur sRGB de assets/specs/feux.json couleurs.mat_anthracite)")
        if c.get("metal_force") is not None:
            m["metal_force"] = c["metal_force"]
        sortie.append(m)
    man = dict(version=1, date=datetime.date.today().isoformat(),
               description="Matériaux PBR CC0 de la bibliothèque route_fr (générateur procédural de routes françaises). "
                           "Script : recon/pcg/assets_route/telecharger_materiaux_route.py ; traitement commun : "
                           "assets/telecharger_cc0.py.",
               licence_sources="CC0 1.0 (ambientCG https://docs.ambientcg.com/license/ ; Poly Haven https://polyhaven.com/license)",
               complements_existants="assets/lib/materiaux/ (29 matériaux 2K du site : BRF, gravier, gazon, terre, BEV, "
                                     "décalques, etc.) : référencés par le catalogue route_fr, pas dupliqués",
               materiaux=sortie)
    MANIFESTE.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print("manifeste :", MANIFESTE, len(sortie), "matériaux")
    return man


# ------------------------------------------------------------------------------------------------ préparation
def preparer(man, noms=None, forcer=False):
    bilan, erreurs = [], []
    for m in man["materiaux"]:
        if noms and m["nom"] not in noms:
            continue
        a = argparse.Namespace(resolution=m["resolution_cible"], complet=True, cache=str(CACHE), hauteur=True,
                               forcer=forcer, correction="cible", version_manifeste=f"route_fr-{man['version']}")
        try:
            meta = T.traiter(m, a, str(SORTIE))
            if m.get("metal_force") is not None:
                forcer_metal(m["nom"], m["metal_force"])
            bilan.append(meta)
        except Exception as e:  # noqa: BLE001
            erreurs.append((m["nom"], repr(e)))
            print("ERREUR", m["nom"], e)
    return bilan, erreurs


def forcer_metal(nom, valeur):
    """Matériau non métallique tiré d'une source métal : métal constant (UsdPreviewSurface) au lieu de la carte."""
    p = SORTIE / nom / f"{nom}.usda"
    t = p.read_text(encoding="utf-8")
    t = t.replace(f"float inputs:metallic.connect = </{nom}/Metal.outputs:r>", f"float inputs:metallic = {valeur}")
    p.write_text(t, encoding="utf-8")


def catalogue():
    ent = []
    for d in sorted(SORTIE.iterdir()):
        mf = d / "meta.json"
        if not mf.exists():
            continue
        m = json.loads(mf.read_text(encoding="utf-8"))
        ent.append(dict(nom=m["nom"], libelle=m.get("libelle"), source=m.get("source"), source_id=m.get("source_id"),
                        page=m.get("page"), licence=(m.get("licence") or {}).get("nom") if isinstance(m.get("licence"), dict) else m.get("licence"),
                        resolution=m.get("resolution"), tile_m=m.get("tile_m"), usd=f"{d.name}/{m.get('usd')}",
                        textures=[t["fichier"] for t in m.get("textures", [])],
                        octets=sum(t.get("octets", 0) for t in m.get("textures", []))))
    cat = dict(version=1, date=datetime.datetime.now().isoformat(timespec="seconds"), racine="assets/lib/route_fr/materiaux",
               materiaux=ent, total_octets=sum(e["octets"] for e in ent))
    (SORTIE / "catalogue.json").write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    print("catalogue :", len(ent), "matériaux,", round(cat["total_octets"] / 1e6), "Mo")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifeste", action="store_true", help="reconstruit le manifeste depuis les API")
    ap.add_argument("--materiaux", nargs="*")
    ap.add_argument("--forcer", action="store_true")
    ap.add_argument("--peinture", action="store_true")
    ap.add_argument("--catalogue", action="store_true")
    a = ap.parse_args()
    SORTIE.mkdir(parents=True, exist_ok=True)
    if a.catalogue:
        catalogue()
        return
    if a.peinture:
        T.faire_peinture(argparse.Namespace(), str(SORTIE))
        catalogue()
        return
    man = construire_manifeste() if (a.manifeste or not MANIFESTE.exists()) else json.loads(MANIFESTE.read_text(encoding="utf-8"))
    if a.manifeste:
        return
    bilan, err = preparer(man, a.materiaux, a.forcer)
    catalogue()
    print(len(bilan), "matériaux prêts ;", len(err), "erreur(s)")
    for n, e in err:
        print("  échec", n, e)
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
