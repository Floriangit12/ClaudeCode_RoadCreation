"""Écrit D:/DocRoute/14_Assets_Route_Statics/ASSETS_ROUTE.md (catalogue lisible) à partir des catalogues JSON.

    python recon/pcg/assets_route/ecrire_doc_assets_route.py [--sortie D:/DocRoute/14_Assets_Route_Statics/ASSETS_ROUTE.md]

Les tableaux (assets, matériaux, contrôles de masse) sont lus dans assets/specs/route/catalogue_assets_route.json et
assets/lib/route_fr/materiaux/catalogue.json ; le texte (constats, erreurs relevées, lacunes) est écrit ici.
"""
import argparse
import collections
import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
CAT = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
MATS = DEPOT / "assets" / "lib" / "route_fr" / "materiaux" / "catalogue.json"
MAN = ICI / "manifeste_materiaux_route.json"
CONTROLE = Path("D:/DocRoute/14_Assets_Route_Statics/controle/rendus_controle.json")


def src_txt(s):
    t = s.get("doc", "?")
    if s.get("page") is not None:
        t += f" p. {s['page']}"
    if s.get("article"):
        t += f", {s['article']}"
    if s.get("figure"):
        t += f" ({s['figure']})"
    return t


def dims_txt(a):
    d = a.get("dimensions") or {}
    parts = []
    for k, v in d.items():
        if isinstance(v, float):
            parts.append(f"{k.replace('_m', '')} {v:g}")
        elif isinstance(v, (int, str)):
            parts.append(f"{k} {v}")
    return ", ".join(parts)


def table_assets(assets, fam):
    L = ["| id | type | dimensions (m) | matériau | sources des cotes | confiance | tri LOD0/1/2 |", "|---|---|---|---|---|---|---|"]
    for a in assets:
        if a["famille"] != fam:
            continue
        lod = a.get("lods", {})
        tri = "/".join(str(lod.get(k, {}).get("triangles", "?")) for k in ("LOD0", "LOD1", "LOD2"))
        srcs = " ; ".join(src_txt(s) for s in (a.get("sources") or [])[:3])
        L.append(f"| `{a['id']}` | {a['type']} | {dims_txt(a)} | {a.get('materiau')} | {srcs} | {a.get('confiance')} | {tri} |")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="D:/DocRoute/14_Assets_Route_Statics/ASSETS_ROUTE.md")
    a = ap.parse_args()
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    mats = json.loads(MATS.read_text(encoding="utf-8"))
    man = {m["nom"]: m for m in json.loads(MAN.read_text(encoding="utf-8"))["materiaux"]}
    rendus = json.loads(CONTROLE.read_text(encoding="utf-8")) if CONTROLE.exists() else {}
    A = cat["assets"]
    fam = collections.Counter(x["famille"] for x in A)
    conf = collections.Counter(x["confiance"] for x in A)
    o = []
    w = o.append
    w("# Bibliothèque d'assets de la route française (`route_fr`) — static meshes et matériaux PBR\n")
    w(f"*Dossier 14 de DocRoute — généré le {cat['date']} par `recon/pcg/assets_route/ecrire_doc_assets_route.py` à partir du "
      "catalogue versionné `assets/specs/route/catalogue_assets_route.json`. Toute cote citée renvoie à un document et une page ; "
      "« estimation » signale une valeur sans source.*\n")
    w("## 1. Résumé\n")
    w(f"- **{len(A)} static meshes paramétriques** fabriqués dans Houdini 22 (hython, 6 HDA `route::*`), chacun en USD (Z haut, "
      f"mètres, variantes LOD0/LOD1/LOD2, UV en mètres `st`/`st1`, sous-ensembles par matériau) et en FBX (un fichier par LOD) : "
      + ", ".join(f"{k} {v}" for k, v in fam.most_common()) + ".")
    w(f"- Confiance des cotes : haute {conf.get('haute', 0)}, moyenne {conf.get('moyenne', 0)}, estimation {conf.get('estimation', 0)}.")
    w(f"- **{len(mats['materiaux'])} matériaux PBR `route_fr`** (CC0 ambientCG / Poly Haven, 4K pour les enrobés, 2K sinon, + peinture "
      f"routière procédurale maison), {round(mats['total_octets'] / 1e6)} Mo, et **{len(cat.get('materiaux_site', []))} matériaux du site** "
      "déjà présents dans `assets/lib/materiaux` (BRF, gravier, gravillons, gazon, terre, galets, BEV, résines…) référencés sans duplication.")
    droits = [x for x in A if x["id"].endswith("_L100") and (x.get("controle_masse") or {}).get("ecart_pct") is not None]
    ok = [x for x in droits if abs(x["controle_masse"]["ecart_pct"]) <= 8.0]
    w("- Profils de bordures et caniveaux **relus sur les dessins cotés** (catalogue Alkern 2026, pages rendues et découpées en tuiles "
      f"natives) et **contrôlés par la masse** : {len(ok)} éléments droits de 1 m sur {len(droits)} à moins de 8 % de la masse catalogue "
      "(béton 2350 kg/m³) ; les écarts restants sont expliqués (§ 7).")
    w(f"- **{len(rendus)} planches de rendu Karma XPU** de contrôle + 4 planches de profils 2D, toutes regardées en tuiles natives "
      "(`controle/`). Les rendus ont fait corriger 5 défauts d'assets et le script de rendu lui-même (§ 7.2).")
    w("- Règles « machine » (55) : `regles_assets_route.json` (forme {id, sujet, condition, valeurs, unité, tolérance, source, confiance}).\n")

    w("## 2. Où sont les fichiers\n")
    w("| Quoi | Chemin | Versionné |\n|---|---|---|")
    w("| Table des cotes et des sources (seule source de vérité) | `D:\\ClaudeCode_RoadCreation\\recon\\pcg\\assets_route\\specs_assets_route.py` | oui |")
    w("| HDA `route::extrusion_profil`, `revolution`, `poteau`, `dalle`, `feu`, `ossature` (format développé) | `...\\recon\\pcg\\assets_route\\hda\\route_*.hdalc\\` + `construire_hda_route.py` | oui |")
    w("| Fabrication (HDA → USD/FBX → catalogues) | `...\\recon\\pcg\\assets_route\\fabriquer_assets_route.py` (≈ 35 s pour 120 assets) | oui |")
    w("| Rendus de contrôle Karma | `...\\recon\\pcg\\assets_route\\rendre_controle_route.py` ; planches 2D : `planche_profils.py` | oui |")
    w("| Matériaux CC0 (choix, manifeste, téléchargement) | `...\\recon\\pcg\\assets_route\\telecharger_materiaux_route.py`, `manifeste_materiaux_route.json` | oui |")
    w("| Règles machine | `exporter_regles_assets.py` → `D:\\DocRoute\\14_Assets_Route_Statics\\regles_assets_route.json` | script oui |")
    w("| **Catalogue versionné** | `D:\\ClaudeCode_RoadCreation\\assets\\specs\\route\\catalogue_assets_route.json` | oui |")
    w("| Static meshes USD + FBX | `D:\\ClaudeCode_RoadCreation\\assets\\lib\\route_fr\\meshes\\<famille>\\<id>\\` (36 Mo) | non (régénérable) |")
    w("| Matériaux PBR | `D:\\ClaudeCode_RoadCreation\\assets\\lib\\route_fr\\materiaux\\<nom>\\` + `catalogue.json` (≈ 790 Mo) | non |")
    w("| Scène maîtresse Houdini | `...\\recon\\pcg\\assets_route\\assets_route.hiplc` (une instance d'HDA par asset) | oui |")
    w("| Sources téléchargées | `D:\\DocRoute\\14_Assets_Route_Statics\\sources\\` + `SOURCES.md` | — |")
    w("| Contrôles visuels | `D:\\DocRoute\\14_Assets_Route_Statics\\controle\\` (PNG, `tuiles\\`, `rendus_controle.json`) | — |\n")
    w("Régénérer tout : `hython recon/pcg/assets_route/fabriquer_assets_route.py` puis `hython recon/pcg/assets_route/rendre_controle_route.py` "
      "(hython : `C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe`). Matériaux : "
      "`python recon/pcg/assets_route/telecharger_materiaux_route.py` (+ `--peinture`).\n")

    w("## 3. Conventions (à respecter par le générateur)\n")
    for k, v in cat["conventions"].items():
        w(f"- **{k}** : {v}")
    w("- **Profils** : (u, v) en m, u = 0 sur la face vue (côté chaussée), u > 0 vers l'arrière (trottoir) ; v = 0 au dessous du bloc "
      "(même repère que `assets/specs/bordures_elements.json`). Caniveaux : u = 0 côté chaussée (chanfrein 15 × 15), u = largeur contre "
      "la face de la bordure.")
    w("- **Pose** d'une bordure à la vue `vue` : décaler l'asset de `vue − H` en Z sous le niveau de chaussée. Raccords (rampants) : "
      "dessous commun au plus profond des deux profils (hauteur totale 0,27 m pour T2 → T2 surbaissée), vue 14 → 2 cm sur 1 m.")
    w("- **Feux** : optiques vers +Y, couleurs listées du haut vers le bas, ou **de gauche à droite vu de face** en disposition horizontale.")
    w("- **Règle matériaux** : " + cat.get("regle_materiaux", "") + ".")
    w("- **Lentilles** : matériaux simples éteints ; l'émission « allumée » (linéaire) est dans `customData route:emission_allumee_lineaire` "
      "du matériau USD (le générateur l'active par phase de feu).")
    w("- **Karma / USD 26** : une `DistantLight` sans `inputs:normalize = 1` éclaire 15 000 fois trop peu (son intensité est une "
      "luminance : éclairement = intensité × angle solide du disque solaire, ≈ 7 × 10⁻⁵ sr à 0,53°). Constat mesuré le 16/10/2026 "
      "(sol à 2 × 10⁻⁵ au lieu de 0,29) ; à reporter dans toute scène Karma du projet.\n")

    w("## 4. Inventaire de l'existant (avant ce dossier)\n")
    w("| Existant | Contenu | Usage dans `route_fr` |\n|---|---|---|")
    w(f"| `assets/lib/materiaux` (29 matériaux CC0 2K, équipe site) | " + ", ".join(m["nom"] for m in cat.get("materiaux_site", [])) +
      " | référencés (catalogue `materiaux_site`), non dupliqués ; `beton_bordure` (Concrete037) reste le béton par défaut des bordures (albédo étalonné sur le site) |")
    w("| `assets/specs/bordures_elements.json` | pas 1,00 m, longueur 0,994 m, joint 6 mm, pas selon le rayon, épaufrures, jitter, abaissés, BEV, caniveaux en éléments, matériaux | conventions de repère et de joint reprises ; règle « pas selon le rayon » utilisée pour les courbes 1,2 / 3 / 6 m |")
    w("| `assets/specs/materiaux_sol.json` (34 materiau_id) | albédos cibles mesurés, rugosités, chemins UE, candidats CARLA/City Sample | lu, non modifié |")
    w("| `assets/specs/peinture.json` | couleurs (blanc neuf 0,78 / en service 0,60), rugosité par usure, masque d'usure | matériau `peinture_routiere` (5 usures × 4 couleurs) généré à partir de ce fichier |")
    w("| `assets/specs/materiaux_rendu_v2.json` | surcharges Karma (familles, albédos) | non modifié ; à appliquer aussi aux matériaux `route_fr` si le rendu v2 les utilise |")
    w("| HDA `recon/pcg/houdini/hda/pj_bordure` + `assets/specs/bordures.json` (autre équipe) | profils T1, T2, T3, T2_bateau 15 × 16, A1, A2, P1-P3, CS1, CS2, CC1, CC2, I1, I2, IL, QUAI_BUS 35 × 29,5, PAVES_GRANIT | non modifiés ; écarts listés § 8.2 |")
    w("| CARLA `D:\\ClaudeADAS\\Content\\Carla\\Static` (UE 4.26/5, licence CC-BY, **utilisable seulement dans Unreal, rien copié**) | `Pole/` : SM_TrafficLight01-02, SM_Traffic_Light_Base, SM_TrafficPole_1/2, SM_Pole_Cylinder_TrafficSignalP, SM_PoleCylinder, SM_RoadSigns01-02, SM_Signs_Atlas_pole, SM_Lights/SM_Bollard01, StreetLights/Group1-3 ; `Pole/GuardRail/Town12` ; `Static/` : SM_ParkingBarrier, Chainbarrier (SM_RopePost), BikeParking ; `GenericMaterials/Gutters_Curbs` (MI_dirtyCurb), `LargeMap_materials/largeM_curb`, `LaneMarking`, `Asphalt`, `Sidewalk` ; `Decals/Road` (fissures, regards) | candidats de remplacement dans UE seulement (formes américaines : feux à 3 optiques sur crosse, pas de profils NF) ; aucun ne correspond aux profils français |")
    w("")

    w("## 5. Matériaux PBR `route_fr` (assets/lib/route_fr/materiaux)\n")
    w("Licence : CC0 1.0 (ambientCG https://docs.ambientcg.com/license/ ; Poly Haven https://polyhaven.com/license) ; `peinture_routiere` "
      "et matériaux simples : création maison. UV : primvar `st1` en mètres, `UsdTransform2d` d'échelle 1/tile_m. Normales OpenGL "
      "(Unreal : cocher *Flip Green Channel*).\n")
    w("| nom | source | rés. | tuile (m) | origine de la taille de tuile | usage |\n|---|---|---|---|---|---|")
    for m in mats["materiaux"]:
        mm = man.get(m["nom"], {})
        w(f"| `{m['nom']}` | {m.get('source')} {m.get('source_id') or ''} | {m.get('resolution') or '—'} | {m.get('tile_m')} | "
          f"{(mm.get('tile_m_source') or '—')} | {m.get('libelle') or ''} |")
    w("\nCouverture de la demande : enrobés neuf / frais / usé / ancien / rapiécé (`enrobe_reprise`) / fissuré / faïencé / grenaillé (4K) ; "
      "béton balayé, désactivé, préfabriqué lisse ; bordures béton (`beton_bordure` site, `beton_prefa_lisse`) et granit "
      "(`granit_gris_flamme`) ; pavés béton (rectangulaires, autobloquants) et pierre (granit anciens, sciés, mosaïque) ; dalles (3) ; "
      "galets ; résine colorée rouge (+ `resine_verte`, `resine_cyan` du site) ; métaux (galvanisé, thermolaqué RAL 7016, inox, "
      "plastique noir) ; peinture routière ; **gravier/gravillons, BRF/copeaux, terre, gazon** : déjà présents dans `assets/lib/materiaux` "
      "(`gravier_concasse_6_10`, `gravillons_ilot`, `brf_bois_concasse`, `brf_bois_gris`, `terre_nue`, `gazon_tondu`, `gazon_sec`, "
      "`herbe_haute`, `paillage_mineral`, `stabilise_beige`).\n")

    w("## 6. Static meshes\n")
    titres = {"bordures": "6.1 Bordures (éléments droits, pièces d'angle, courbes, quarts de rond, raccords de bateau)",
              "caniveaux": "6.2 Caniveaux", "dalles": "6.3 Dalles et bandes d'éveil de vigilance (BEV)", "paves": "6.4 Pavés",
              "potelets": "6.5 Potelets", "supports": "6.6 Supports de signalisation et de feux (poteaux, mâts, platines, potence)",
              "feux": "6.7 Signaux lumineux (R11v, R12, R13, répétiteurs)", "garde_corps": "6.8 Garde-corps de pont et urbains",
              "barrieres": "6.9 Barrières de trottoir"}
    for f, t in titres.items():
        w(f"### {t}\n")
        w(table_assets(A, f))
        w("")
    w("Profils de bordures et de caniveaux (lecture des dessins cotés, en mm) :\n")
    w("| profil | lecture du dessin | sources |\n|---|---|---|")
    vus = set()
    for x in A:
        p = x.get("profil")
        if p and "->" not in p and p not in vus and x.get("lecture_profil"):
            vus.add(p)
            w(f"| {p} | {x['lecture_profil']} | {src_txt(x['sources'][0])} |")
    w("")

    w("## 7. Contrôles\n")
    w("### 7.1 Masse des éléments (volume du maillage × 2350 kg/m³, comparé à la masse catalogue)\n")
    w("| asset | masse catalogue (kg) | masse du modèle (kg) | écart | explication |\n|---|---|---|---|---|")
    for x in A:
        cm = x.get("controle_masse") or {}
        if cm.get("masse_modele_kg") is not None:
            w(f"| `{x['id']}` | {cm['masse_catalogue_kg']} ({cm['source']}) | {cm['masse_modele_kg']} | {cm['ecart_pct']:+.1f} % | "
              f"{cm.get('explication', '')} |")
    w("\nLecture : la densité 2350 kg/m³ est une estimation (béton vibré) ; un écart de −3 % est attendu (congés et chanfreins des "
      "dessins). Les profils T1 (−0,4 %), T2 (−2,8 %), T4 (+0,1 %), T2 basse (−0,6 %), ACCESBUS (+1,2 %) valident la méthode de "
      "lecture. Les écarts > 8 % ont été relus sur les tuiles des pages concernées : dans chaque cas la géométrie suit les cotes "
      "dessinées et c'est la masse imprimée qui est incohérente.\n")
    w("### 7.2 Rendus Karma XPU (soleil 38°, ciel, exposition fixe, numéros projetés, tuiles natives regardées)\n")
    w("| planche | assets | fichier |\n|---|---|---|")
    for k, v in rendus.items():
        w(f"| {k} | {len(v.get('assets', []))} | `controle/{Path(v['png']).name}` (+ `{v.get('tuiles', '')}`) |")
    w("| profils 2D | 33 profils | `controle/profils_bordures_1-3.png`, `profils_caniveaux.png` (≤ 1020 × 1060 px, sans découpe) |")
    w("\nDéfauts trouvés sur les rendus et **corrigés** le 16/10/2026 :")
    w("1. **R12 inversé** : en disposition horizontale le rouge était à droite du piéton ; l'IISR 6e partie p. 5 (art. 109-3 A, fig. 2) "
      "impose « vert et rouge, dans cet ordre de droite à gauche ». Corrigé dans l'HDA `route::feu` (couleurs listées de gauche à droite vu de face).")
    w("2. **R12 à optiques rondes** : la fig. 2 montre des optiques carrées à figurines ; option `optique_carree` (lentille et caisson-visière carrés) ajoutée et activée pour les deux R12.")
    w("3. **Ensemble mixte R300** identique au D200 : paramètre `diametre_haut` ajouté (module rouge Ø 300 au-dessus de jaune et vert Ø 200, IISR 6 p. 10 art. 109-4).")
    w("4. **Étirement des UV** sur les raccords (rampants) et les courbes : coordonnée de périmètre recalculée pour chaque section et abscisse réelle de chaque point (arc × rayon propre).")
    w("5. **Pavés et dalles unitaires** texturés avec une texture de pavage (faux joints visibles sur un seul pavé) : matériau de matière `beton_prefa_lisse` / `granit_gris_flamme`.")
    w("6. Script de rendu de la 1re passe : soleil inopérant (cf. § 3 *Karma / USD 26*), caméra derrière les feux, exposition automatique "
      "délavée → réécrit (cadrage calculé, exposition fixe, lentilles allumées).\n")
    w("Constats non corrigés (voir lacunes) : texture `beton_bordure` (granulats roulés de 1-3 cm) très « béton désactivé » pour des "
      "bordures récentes → variante `beton_prefa_lisse` fournie (`materiaux_alternatifs`) ; `beton_prefa_lisse` (Concrete006) "
      "montre de fines stries verticales de coffrage, visibles sur les petits éléments.\n")

    w("## 8. Erreurs relevées dans les documents existants\n")
    w("### 8.1 DocRoute (fichiers non modifiés)\n")
    w("| Document | Affirmation | Ce que disent les sources | Source |\n|---|---|---|---|")
    E = [
        ("06_…/GUIDE_VEGETATION_BORDURES_ACCESSIBILITE_FR.md (titre) et 05_…/regles_conduite_et_implantation_fr.json (`profils_bordures_nf_p98_302`)",
         "bordures « NF P98-302 »", "les profils certifiés relèvent de NF EN 1340 + NF P 98-340/CN (complément national) ; « NF P 98-302 » n'apparaît dans aucune source consultée",
         "Alkern 2026 p. 56 ; fiche Fabemi I2 p. 1"),
        ("GUIDE_VEGETATION… l. 15", "T1 : « chanfrein supérieur 1 × 1 cm »", "arête avant arrondie R 20 mm, face verticale 100 mm puis inclinée (fruit 20 mm)", "Alkern 2026 p. 9"),
        ("GUIDE_VEGETATION… l. 16", "T2 : « face avant inclinée 2 cm sur 14 cm »", "face verticale 100 mm puis inclinée de 30 mm (150 − 118 − 2) sur ≈ 145 mm ; tête 118 mm",
         "Alkern 2026 p. 10"),
        ("GUIDE_VEGETATION… l. 18 et regles_conduite….json (`I2`)", "I1/I2 : base 20 cm, hauteur 18-22 cm, vue 5-7 cm, « biseauté à 30° » ; I2 0,20 × 0,22, vue 0,07",
         "I1 250 × 130 (vue 6 cm) ; I2 250 × 180 (vue 11 cm) ; dessus incliné d'environ 20° (70 mm sur ≈ 200 mm)", "Alkern 2026 p. 27-28 ; Celtys p. 3 ; Fabemi I2 p. 1"),
        ("GUIDE_VEGETATION… l. 19", "A1/A2 : hauteur 20 cm, « face inclinée à 45° »", "A1 200 × 250, A2 150 × 200 ; chanfrein 80 × 60 mm, soit ≈ 37° sur l'horizontale",
         "Alkern 2026 p. 15"),
        ("GUIDE_VEGETATION… l. 36", "abaissé : « largeur min 2,50 m »", "partie abaissée ≥ 1,20 m ; 2,50 m est la distance minimale entre deux ressauts successifs",
         "arrêté du 15/01/2007, art. 1er 4° et 5° (copie Cantal p. 2)"),
        ("GUIDE_VEGETATION… l. 39 et regles_conduite….json (`profondeur_standard_m` 0,4)", "BEV : profondeur 40 cm",
         "largeur standard 587,5 mm depuis la révision de NF P 98-351 (largeur réduite admise seulement dans des cas particuliers, ex. îlots-refuges étroits, p. 7) ; posée à 0,50 m du nez de bordure",
         "fiche Certu/Cerema n° 03 (2010) p. 3, 6 et 7"),
        ("regles_conduite….json (`support_feux`) et INDEX_DOCUMENTATION.md § 1", "feux : hauteurs 2,30 m / 1,10 m / potence 5,10 m attribuées à l'IISR 6e partie",
         "aucune de ces valeurs n'apparaît dans l'IISR 6e partie (VC 04/09/2025) ; elle fixe un gabarit de 2,00 m sous les feux sur trottoir et l'axe du feu supérieur à moins de 4,20 m",
         "IISR 6 p. 11 (fig. 16)"),
        ("GUIDE_VEGETATION… l. 20", "CS1/CS2 : pente transversale 1,5 à 2 cm", "CS1 120 → 100 (2 cm) ; CS2 135 → 110 (2,5 cm, chanfrein compris)", "Alkern 2026 p. 17"),
    ]
    for d, aff, vrai, s in E:
        w(f"| {d} | {aff} | {vrai} | {s} |")
    w("\n### 8.2 Écarts avec `assets/specs/bordures.json` (autre équipe, non modifié)\n")
    w("| Profil | bordures.json | route_fr (source) |\n|---|---|---|")
    w("| T2_bateau / T2 surbaissée | 15 × 16 | 151 × 150, face verticale 20 mm (Alkern p. 11, réf. 520034) |")
    w("| P2 | 6 × 28 (Celtys) | 60 × 250 à tête ronde R30 (Alkern p. 21) ; les deux existent selon le fabricant |")
    w("| P3 | 8 × 20 (Celtys) | dessin Alkern 60 × 200 mais masse 36 kg ≈ 80 × 200 : P3 est hors liste NF (p. 56) |")
    w("| QUAI_BUS | 35 × 29,5 | ACCESBUS 200 × 295 (Alkern p. 33) : autre produit |")
    w("| I1 / I2 | base 0,25, vue 6 / 11 | identique (Alkern p. 27-28) |")
    w("\n### 8.3 Erreurs de la 1re passe de ce dossier (corrigées)\n")
    w("- Chemins vers l'ancienne copie `C:\\Users\\flori\\Desktop\\DocRoute` remplacés par `D:\\DocRoute` (specs, rendus).")
    w("- Le fichier `sources/catalogues_bordures/sepa_hellopro_6057591.pdf` est une fiche **Fabemi** (I2 0,5 m), pas Sepa.")
    w("- R12 inversé, mixte R300, UV des rampants, matériaux des pavés : § 7.2.\n")

    w("## 9. Lacunes\n")
    L = [
        "**P4** : aucune fiche NF trouvée ; modèle 50 × 200 × 500 estimé d'après une fiche de vente au détail (confiance « estimation »). "
        "**I5, I6** : n'existent pas dans la liste NF P 98-340/CN reproduite par Alkern p. 56 (types I = I1 à I4) : non fabriqués.",
        "**Quart de rond intérieur T2 R20** (Alkern p. 10 « D × H 20 × 250 », 15 kg) : forme non cotée, modèle concentrique (36 kg) à remplacer ; "
        "**nez d'îlot I1 R25** approché (profil I1 tourné).",
        "**Granit** : seules GR_T2 (Angers) est cotée ; GR_T1, GR_P1 supposées rectangulaires (Noblema, confiance moyenne). Pas de profil "
        "NF granit (NF EN 1343) téléchargé.",
        "**Feux** : boîtiers d'après des fiches de feux de chantier (Trafic) ; pas de fiche de feu urbain à LED (boîtier, écran de contraste, "
        "visières réelles) ; **pictogrammes** des R12 (figurines), R13c (cycle), R13b (BUS) non modélisés (matériaux nommés par pictogramme, "
        "textures à produire à partir de `assets/lib/route_fr/panneaux/Feux_R/*.png` de l'équipe signalisation) ; pas d'écran de contraste "
        "(obligatoire hors agglomération, IISR 6 p. 11) ; pas de R12m, R14-R19, R22-R25.",
        "**Potence de feux** : géométrie de principe (mât Ø 168, crosse Ø 114, portée 4,5 m, hauteur 6,0 m) sans source ; pas de crosse "
        "de mât de feu ni de console de répétiteur.",
        "**Platines** : 300 × 300 × 20 (mâts directionnels) et 300 × 300 × 15 (mât de feux) estimées ; seule la platine 200 × 200 × 3 du "
        "fourreau Virages et la platine de serrage Ø 155 × 2,7 (Angers) sont sourcées.",
        "**Garde-corps** : S8 (Setra 1997) seulement ; lisse basse à 0,10 m estimée ; pas de garde-corps à lisses, de garde-corps "
        "béton/parapet, ni de dispositif de retenue (glissière GS2/GS4, BN4) — à ajouter pour les ponts routiers.",
        "**Mobilier absent** : bornes (arrêt-minute Angers téléchargée mais non modélisée), arceaux vélos (fiche téléchargée, non modélisée), "
        "balises J11/J13, plots, délinéateurs J6, candélabres, regards et avaloirs en volume (décalques seulement), entourages d'arbres.",
        "**Matériaux** : pas d'enrobé « BBSG neuf à granulats clairs » distinct ; résine colorée uniquement rouge (vert et cyan du site) ; "
        "pas de béton désactivé à gros granulats distinct de `beton_bordure` ; textures de feux (lentilles) en couleur unie.",
        "**Épaufrures, salissures, jitter de pose** : décrits dans `bordures_elements.json` mais non appliqués aux meshes (à faire par variantes "
        "ou dans le matériau UE).",
        "**Import Unreal** non testé dans ce dossier (USD : variantes LOD = convention de l'importeur UE ; FBX : un fichier par LOD).",
        "**Pièces d'angle T3/T4 et courbes T1/T3/A/I** : seules les pièces T1, T2, T3 cataloguées par Alkern sont fabriquées ; les rayons "
        "1,2 / 3 / 6 m ne sont faits qu'en T2.",
    ]
    for x in L:
        w(f"- {x}")
    w("\n## 10. Licences\n")
    w("- Meshes `route_fr` : création maison (HDA `route::*`, dépôt ClaudeCode_RoadCreation), cotes tirées de documents publics cités ; "
      "aucune géométrie copiée d'un fabricant (profils redessinés à partir des cotes), **aucune donnée City Sample ni CARLA**.")
    w("- Matériaux : CC0 1.0 (ambientCG, Poly Haven) — attribution non requise ; `peinture_routiere` et matériaux simples : maison.")
    w("- Catalogues fabricants : consultés et cités (cotes, pages), non redistribués (dossier `sources/` local).")
    w("- CARLA (CC-BY) : listé seulement ; utilisation éventuelle dans Unreal uniquement, avec attribution.")
    Path(a.sortie).write_text("\n".join(o) + "\n", encoding="utf-8")
    print(a.sortie, sum(len(x) for x in o), "caractères")


if __name__ == "__main__":
    main()
