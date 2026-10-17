"""Écrit recon/pcg/assets_route/ASSETS_ROUTE_ETAPE3.md (bibliothèque route_fr, étape 3) à partir des données.

    python recon/pcg/assets_route/ecrire_doc_etape3.py

Tableaux lus dans assets/specs/route/catalogue_assets_route.json (entrées « etape » = 3), recon/pcg/assets_route/
fiches_materiaux_route.json, manifeste_materiaux_etape3.json, assets/lib/route_fr/panneaux_3d/contours_faces.json et
D:/DocRoute/14_Assets_Route_Statics/controle/etape3/rendus_controle_etape3.json ; le texte (méthode, phases de chantier,
constats des planches, lacunes) est écrit ici. D:/DocRoute est en lecture seule pour ce lot : ce fichier est écrit dans le
dépôt (le dossier 14 de DocRoute n'est pas modifié, hormis les planches de contrôle de controle/etape3/).
"""
import collections
import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
CAT = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
FICHES = ICI / "fiches_materiaux_route.json"
MAN = ICI / "manifeste_materiaux_etape3.json"
CONTOURS = DEPOT / "assets" / "lib" / "route_fr" / "panneaux_3d" / "contours_faces.json"
RENDUS = Path("D:/DocRoute/14_Assets_Route_Statics/controle/etape3/rendus_controle_etape3.json")
SORTIE = ICI / "ASSETS_ROUTE_ETAPE3.md"
CONSTATS = ICI / "constats_planches_etape3.json"

FAMILLES = [("retenue", "Équipements de retenue (GBA, DBA, MVL, LBA, glissières, extrémités, atténuateurs)"),
            ("balises", "Balises J et quilles"), ("assainissement", "Assainissement (grilles, regards, bouches à clé, avaloir)"),
            ("eclairage", "Éclairage (candélabres routiers et urbains)"), ("mobilier", "Mobilier urbain"),
            ("potelets", "Potelets et bornes (gamme Grenoble-Alpes Métropole)"), ("barrieres", "Barrières"),
            ("feux", "Feux (têtes du site, compléments)"), ("supports", "Supports : mâts, colliers, potences, portique"),
            ("bordures", "Bordures (courbes, granit, rampants)"), ("caniveaux", "Caniveaux courbes"),
            ("ilots", "Îlots et giratoires préfabriqués"), ("dalles", "Dalles"), ("paves", "Pavés et galets")]


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
        elif isinstance(v, int):
            parts.append(f"{k} {v}")
        elif isinstance(v, list) and len(v) <= 3 and all(isinstance(x, (int, float)) for x in v):
            parts.append(f"{k.replace('_m', '')} " + " × ".join(f"{x:g}" for x in v))
    return ", ".join(parts)


def table(assets):
    L = ["| id | type | dimensions (m) | matériau | sources des cotes | confiance | phase | tri LOD0/1/2 |",
         "|---|---|---|---|---|---|---|---|"]
    for a in assets:
        lod = a.get("lods", {})
        tri = "/".join(str(lod.get(k, {}).get("triangles", "?")) for k in ("LOD0", "LOD1", "LOD2"))
        srcs = " ; ".join(src_txt(s) for s in (a.get("sources") or [])[:3])
        L.append(f"| `{a['id']}` | {a['type']} | {dims_txt(a)} | {a.get('materiau')} | {srcs} | {a.get('confiance')} | "
                 f"{(a.get('phase_chantier') or '')[:3]} | {tri} |")
    return "\n".join(L)


def main():
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    A = [a for a in cat["assets"] if a.get("etape") == 3]
    A1 = [a for a in cat["assets"] if a.get("etape") != 3]
    fiches = json.loads(FICHES.read_text(encoding="utf-8"))["materiaux"]
    man = {m["nom"]: m for m in json.loads(MAN.read_text(encoding="utf-8"))["materiaux"]}
    cont = json.loads(CONTOURS.read_text(encoding="utf-8"))
    rendus = json.loads(RENDUS.read_text(encoding="utf-8")) if RENDUS.exists() else {}
    constats = json.loads(CONSTATS.read_text(encoding="utf-8")) if CONSTATS.exists() else {}
    fam = collections.Counter(a["famille"] for a in A)
    meshes = [a for a in A if a["famille"] not in ("panneaux", "panneaux_montes", "feux_montes")]
    pans = [a for a in A if a["famille"] == "panneaux"]
    ens = [a for a in A if a["famille"] in ("panneaux_montes", "feux_montes")]
    conf = collections.Counter(a["confiance"] for a in meshes)
    confp = collections.Counter(a["confiance"] for a in pans)
    nouv = [f for f in fiches if f.get("etape3")]
    o = []
    w = o.append
    w("# Bibliothèque d'assets de la route française (`route_fr`) — étape 3 : élargissement\n")
    w(f"*Généré le {cat['etape3']['date']} par `recon/pcg/assets_route/ecrire_doc_etape3.py` à partir du catalogue versionné "
      "`assets/specs/route/catalogue_assets_route.json` (entrées `\"etape\": 3`). Complète `D:\\DocRoute\\14_Assets_Route_Statics\\"
      "ASSETS_ROUTE.md` (étape 1, 120 meshes, non modifié). Toute cote renvoie à un document et une page ; « estimation » signale "
      "une valeur sans source.*\n")
    # ------------------------------------------------------------------ 1
    w("## 1. Résumé\n")
    w(f"- **{len(meshes)} nouveaux static meshes** fabriqués dans Houdini 22 (hython ; HDA `route::assemblage` et `route::panneau` "
      "créées pour cette étape, HDA `route::extrusion_profil`, `revolution`, `poteau`, `dalle`, `ossature` de l'étape 1), en USD "
      "(Z haut, m, variantes LOD0/1/2, UV en mètres `st`/`st1`, sous-ensembles par matériau) et FBX (un fichier par LOD) : "
      + ", ".join(f"{k} {v}" for k, v in collections.Counter(a["famille"] for a in meshes).most_common()) + ".")
    w(f"  Confiance des cotes : haute {conf.get('haute', 0)}, moyenne {conf.get('moyenne', 0)}, estimation {conf.get('estimation', 0)}.")
    w(f"- **{len(pans)} panneaux montés sur plaques** (un USD par signal, jeu de variantes `gamme`, faces officielles des PNG du "
      f"dossier 09 en texture à UV 0-1, revers, bord tombé, rails de fixation) ; {sum(len(a['dimensions']['gammes_m']) for a in pans)} "
      f"variantes de gamme fabriquées (une plaque à la taille de chaque gamme IISR) ; échelle : haute {confp.get('haute', 0)}, moyenne {confp.get('moyenne', 0)}, estimation "
      f"{confp.get('estimation', 0)} (panneaux à dimensions variables D, E, H, SR).")
    w(f"- **{len(ens)} ensembles** (compositions USD par références) : support + colliers + panneau(x) aux hauteurs de l'IISR, mâts + "
      "têtes de feux aux hauteurs relevées à Meylan.")
    w(f"- **{len(nouv)} matériaux PBR CC0 nouveaux** (enrobés 4K : BBTM, ESU, pelade, granulats clairs, rouge, ocre ; bétons désactivés, "
      "galets scellés, résine gravillonnée, gravillons, pavés, dalles, BRF, terres, bois, RAL 7024) et **fiche mesurée** (albédo moyen, "
      f"rugosité, licence) pour les {len(fiches)} matériaux de `route_fr` et du site : `recon/pcg/assets_route/fiches_materiaux_route.json`.")
    w(f"- **{len(rendus)} planches de rendu Karma XPU** (≤ 1092 px, regardées à la taille native) dans "
      "`D:\\DocRoute\\14_Assets_Route_Statics\\controle\\etape3\\` ; constats et corrections au § 9.")
    w(f"- Catalogue : {len(A1)} entrées existantes **conservées à l'identique**, {len(A)} ajoutées (écriture atomique) ; clés "
      "nouvelles `etape3`, sources et matériaux ajoutés sans retrait.\n")
    # ------------------------------------------------------------------ 2
    w("## 2. Construire comme un chantier : phases et continuité\n")
    w("Chaque asset porte `phase_chantier` (ordre de pose) et `pose` (pas de répétition, raccords, accroches, hauteurs). Le PCG "
      "fabrique la scène phase par phase, chaque phase s'appuyant sur la géométrie de la précédente (niveau fini, arêtes de bordure, "
      "axes des voies) — c'est ce qui évite les « bouts de segments » :\n")
    w("| phase | contenu | assets (familles) | ce que la phase fournit à la suivante |")
    w("|---|---|---|---|")
    suite = {"P01_reseaux": "positions des regards et chambres (sous chaussée et trottoir)",
             "P02_bordures": "arêtes vues des bordures (fil d'eau, nez) : limites des surfaces, abaissés, nez d'îlots",
             "P03_chaussee": "niveau fini de la chaussée (couche de roulement) et son matériau",
             "P04_trottoirs": "niveau fini des trottoirs, îlots, terre-pleins",
             "P05_affleurants": "tampons, grilles, bouches à clé mis au niveau fini (dessus à Z = 0 de l'asset)",
             "P06_retenue": "files continues : modules au pas, extrémités, atténuateurs aux musoirs",
             "P07_eclairage": "candélabres au pas dans la bande technique",
             "P08_signalisation": "supports, panneaux et balises (hauteurs, dégagements IISR)",
             "P09_feux": "mâts, têtes, répétiteurs, boîtiers (hauteurs [G] du dossier 09)",
             "P10_marquage": "marquage (dossier 08), plots J15a, balises J11/J12 le long des lignes",
             "P11_mobilier": "potelets, barrières, arceaux, bancs, corbeilles, abris hors cheminement de 1,40 m"}
    par_phase = collections.defaultdict(collections.Counter)
    for a in A:
        par_phase[a.get("phase_chantier")][a["famille"]] += 1
    for pid, role in cat["etape3"]["phases_chantier"] and [(p["id"], p["role"]) for p in cat["etape3"]["phases_chantier"]]:
        fams = ", ".join(f"{k} {v}" for k, v in par_phase.get(pid, {}).items()) or (
            "matériaux de chaussée (§ 7)" if pid == "P03_chaussee" else "— (les corps de regards sont portés par les affleurants P05)")
        w(f"| {pid} | {role} | {fams} | {suite.get(pid, '')} |")
    w("")
    w("Règles de continuité des éléments linéaires (champ `pose`) :\n")
    w("- **Modules au pas** : bordures et caniveaux 1,00 m (0,994 + joint 6 mm), courbes de 1 m mesurés sur la face (R 1,2 / 3 / 6 m), "
      "GBA/DBA/MVL/LBA en modules de 1 et 4 m sans joint (ouvrage coulé en place), glissières en modules de 4 m (lisse de 4,315 m, "
      "recouvrement 0,315 m modélisé par une éclisse en bout de module) ; le PCG pose les modules bout à bout le long de la courbe "
      "(pivot au milieu du module, face côté circulation vers −Y).")
    w("- **Débuts et fins de file** : `retenue_GBA/DBA_extremite_abaissee_L0165` (fin de file) et `_L2000` (origine), "
      "`retenue_glissiere_GS2/GS4_extremite_abaissee_L1200` (lisse abaissée et enterrée), atténuateurs `retenue_attenuateur_*` au nez "
      "des musoirs (Cerema, guide d'installation, § 4.1, p. 49-51).")
    w("- **Raccords de bordure** : rampants T2 → T2 basse / surbaissée (étape 1), T3 → T3 basse et T2 basse → T2 surbaissée (étape 3), "
      "pièces d'angle et courbes ; avaloir T2 à la place d'un élément de 1 m.")
    w("- **Accroches** : panneaux (rails à `pose.rails_z_m`, face à Y = rayon du poteau + 0,06 m) ; colliers `collier_panneau_D*` à la "
      "hauteur des rails ; têtes de feux sur mâts (azimut, hauteur du bas) ; potences et portique (console à 5,00 / 5,50 m).\n")
    w("### 2.1 Du vocabulaire des descriptions simples aux assets\n")
    w("Proposition au générateur (clé `etape3.correspondances_description` du catalogue) : les mots des descriptions simples "
      "(`recon/generateur/description/FORMAT_DESCRIPTION.md` § 5-10) et l'asset ou le matériau choisi par défaut (premier de la "
      "liste), les autres étant des variantes. Exemple : « route 2 × 2 voies avec terre-plein central végétalisé de 20 m » → "
      "bordures `bordure_I2_L100` et courbes I2 autour du terre-plein (P02), enrobé `enrobe_bbsg_use` (P03), terre `terre_vegetale` "
      "et plantations (P04 + végétation), candélabres `candelabre_routier_H100_double_crosse` dans le terre-plein (P07), balise J5 "
      "et `ensemble_B21_1_ilot` aux nez (P08).\n")
    w("| catégorie | mot | assets / matériaux |")
    w("|---|---|---|")
    for catg, d in cat["etape3"].get("correspondances_description", {}).items():
        for mot, ids in d.items():
            w(f"| {catg} | {mot} | " + ", ".join(f"`{i}`" for i in ids) + " |")
    w("")
    # ------------------------------------------------------------------ 3
    w("## 3. Où sont les fichiers\n")
    w("| Quoi | Chemin | Versionné |")
    w("|---|---|---|")
    for q, c, v in (
            ("Table des cotes, sources, phases, descriptions de pièces", "recon/pcg/assets_route/specs_assets_etape3.py", "oui"),
            ("HDA `route::assemblage`, `route::panneau` (format développé)", "recon/pcg/assets_route/hda/route_assemblage.hdalc, route_panneau.hdalc + construire_hda_etape3.py", "oui"),
            ("Fabrication (assets, panneaux, ensembles, catalogue)", "recon/pcg/assets_route/fabriquer_assets_etape3.py", "oui"),
            ("Contours des plaques relevés sur les faces", "recon/pcg/assets_route/signalisation/contours_faces_panneaux.py → assets/lib/route_fr/panneaux_3d/contours_faces.json", "script oui"),
            ("Matériaux CC0 et fiches", "recon/pcg/assets_route/telecharger_materiaux_etape3.py, manifeste_materiaux_etape3.json, fiches_materiaux_route.json", "oui"),
            ("Rendus de contrôle", "recon/pcg/assets_route/rendre_controle_etape3.py → D:/DocRoute/14_Assets_Route_Statics/controle/etape3/", "script oui"),
            ("Scène maîtresse Houdini (une instance d'HDA par asset)", "recon/pcg/assets_route/assets_route_etape3.hiplc", "oui"),
            ("Static meshes USD + FBX", "assets/lib/route_fr/meshes/<famille>/<id>/", "non"),
            ("Panneaux (USD par signal + FBX gamme normale)", "assets/lib/route_fr/panneaux_3d/<famille_signal>/panneau_<code>/", "non"),
            ("Ensembles (compositions USD)", "assets/lib/route_fr/meshes/ensembles/<id>/", "non"),
            ("Sources téléchargées (fiches fabricants)", "assets/lib/route_fr/_sources_etape3/ (retenue, mobilier)", "non"),
            ("Catalogue versionné", "assets/specs/route/catalogue_assets_route.json (entrées `etape: 3`, clé `etape3`)", "oui")):
        w(f"| {q} | `{c}` | {v} |")
    w("\nRégénérer : `python -P recon/pcg/assets_route/signalisation/contours_faces_panneaux.py` puis "
      "`hython recon/pcg/assets_route/fabriquer_assets_etape3.py` puis `hython recon/pcg/assets_route/rendre_controle_etape3.py` ; "
      "matériaux : `python recon/pcg/assets_route/telecharger_materiaux_etape3.py`. `fabriquer_assets_route.py` (étape 1) a été "
      "corrigé pour **conserver** les entrées de l'étape 3 et écrire le catalogue de façon atomique.\n")
    # ------------------------------------------------------------------ 4
    w("## 4. Conventions et HDA nouvelles\n")
    for k, v in cat["etape3"]["conventions"].items():
        w(f"- **{k}** : {v}")
    w("- **`route::assemblage`** : un texte décrit des pièces cotées, une par ligne : `B` boîte (centre, tailles, rotation Z), `T` tube "
      "à rayon variable le long d'une polyligne (transport parallèle, onglets), `Q` profil (u, v) balayé le long d'une polyligne, `E` "
      "ellipsoïde, `F` face rectangulaire et `G` disque à UV 0-1 (décalques : tampons, grilles, vasques). Le wrangle VEX fabrique des "
      "pièces fermées orientées vers l'extérieur (normale contrôlée par la méthode de Newell), UV en mètres ; Fuse, Divide (polygones "
      "convexes, pour un import sûr dans Unreal), puis la chaîne commune de l'étape 1 (normales à angle de coupure, LOD PolyReduce).")
    w("- **`route::panneau`** : plaque(s) convexe(s) relevée(s) sur l'emprise opaque de la face officielle ; face avant à UV rapportées "
      "à l'image entière (une seule texture pour toutes les plaques d'un dessin : panneau + panonceau), bord tombé de 25 mm, rebord "
      "arrière de 12 mm, tôle de 2 mm, revers creux, 1 ou 2 rails de fixation (2 si la plaque dépasse 0,45 m). Vue de face, la "
      "gauche de l'image est en +X (corrigé après la 1re planche, § 9).\n")
    # ------------------------------------------------------------------ 5
    w("## 5. Static meshes de l'étape 3\n")
    for f_, titre in FAMILLES:
        lot = [a for a in meshes if a["famille"] == f_]
        if not lot:
            continue
        w(f"### 5.{FAMILLES.index((f_, titre)) + 1} {titre} ({len(lot)})\n")
        w(table(lot))
        w("")
    w("Lecture des profils et pièces nouvelles (cotes en mm) :\n")
    w("| asset | lecture du document | source |")
    w("|---|---|---|")
    vus = set()
    for a in meshes:
        if a.get("note") and a["famille"] in ("retenue",) and a["type"] not in vus:
            vus.add(a["type"])
            w(f"| `{a['id']}` | {a['note']} | {src_txt(a['sources'][0])} |")
    w("")
    # ------------------------------------------------------------------ panneaux
    w("## 6. Panneaux sur plaques (signalisation verticale)\n")
    S = cont["signaux"]
    w(f"Méthode (`contours_faces_panneaux.py`) : pour chacun des {len(S)} signaux « plaques » des 870 faces (les symboles, idéogrammes, "
      "feux, balises cylindriques et panneaux temporaires K hors triangles AK sont exclus), le masque d'opacité est découpé en "
      "composantes connexes (plaques), les supports dessinés sont écartés, les plaques jointives à un poteau dessiné sont séparées "
      "par une ouverture morphologique horizontale ; l'enveloppe convexe de chaque plaque est simplifiée à 0,8 px. "
      f"{len(cont.get('refus', []))} exemples de composition à plaques jointives (illustrations) ne sont pas fabriqués.\n")
    w("Échelle (m par pixel) à la gamme normale :\n")
    regles = collections.Counter(s["regle_echelle"].split(" ;")[0].split(" :")[0] for s in S)
    w("| règle | nombre de signaux |")
    w("|---|---|")
    for k, v in regles.most_common():
        w(f"| {k} | {v} |")
    w("\nContrôle : l'échelle des dessins du Cerema (cadre du PDF × 4,99) redonne la gamme normale à ± 0,1 % pour les disques "
      "(850), l'octogone AB4 (800), les carrés (700) et les triangles (925 mm de largeur pour 1000 de côté à angles arrondis). Écarts "
      "> 3 % (confiance ramenée à « moyenne ») :\n")
    ec = [(s["id"], s["ecart_echelle_dessin_pct"], s["regle_echelle"]) for s in S if abs(s["ecart_echelle_dessin_pct"]) > 3 and s["confiance"] != "estimation"]
    for i, e, r in ec:
        w(f"- `{i}` : {e:+.1f} % — {r}")
    w("")
    fs = collections.Counter(a["famille_signal"] for a in pans)
    w("| famille de signaux | panneaux | gammes fabriquées | exemple (taille normale, m) |")
    w("|---|---|---|---|")
    for k, v in sorted(fs.items()):
        ex = next(a for a in pans if a["famille_signal"] == k)
        gn = ex["dimensions"]["gammes_m"].get("normale", {})
        w(f"| {k} | {v} | {', '.join(ex['dimensions']['gammes_m'])} | `{ex['id']}` {gn.get('largeur')} × {gn.get('hauteur')} |")
    w("\nGammes (IISR 1 art. 5-3, p. 10) : triangle 500 / 700 / 1000 / 1250 / 1500 ; disque 450 / 650 / 850 / 1050 / 1250 ; octogone "
      "400 / 600 / 800 / 1000 / 1200 ; carré 350 / 500 / 700 / 900 / 1050 (exceptionnelle et supérieure non fabriquées, réservées "
      "aux C et CE de présignalisation). Les plaques des panneaux à dimensions variables (D, E/EB, H, SR) sont à l'échelle "
      "« hauteur minimale de 250 mm » : à redimensionner selon le texte réel (le PNG garde les proportions du dessin).\n")
    w("### 6.1 Ensembles\n")
    w("| id | composants | bas (m) | haut (m) | sources |")
    w("|---|---|---|---|---|")
    for a in ens:
        comp = " + ".join(c["id"] + (f" ({c['gamme']})" if c.get("gamme") else "") for c in a["composants"])
        d = a.get("dimensions", {})
        w(f"| `{a['id']}` | {comp} | {d.get('bas_m', '')} | {d.get('haut_m', '')} | {' ; '.join(src_txt(s) for s in a['sources'][:2])} |"
          + (f" ⚠ {a['alerte']}" if a.get("alerte") else ""))
    w("")
    # ------------------------------------------------------------------ matériaux
    w("## 7. Matériaux PBR CC0 nouveaux (fiches mesurées)\n")
    w("Licence de toutes les sources : CC0 1.0 (ambientCG https://docs.ambientcg.com/license/ ; Poly Haven https://polyhaven.com/license). "
      "Choix : vignettes des sources puis recadrages NATIFS 340 × 340 px des albédos 1K des candidats retenus (planches de travail "
      "hors dépôt). Albédo et rugosité mesurés sur les cartes livrées (pas 4).\n")
    w("| nom | source | rés. | tuile (m) | albédo moyen linéaire (sRGB 8 bits) | rugosité moy. ± σ | usage | choix |")
    w("|---|---|---|---|---|---|---|---|")
    for f in nouv:
        m = man.get(f["nom"], {})
        rg = f.get("rugosite") or {}
        al = f.get("albedo_moyen_lineaire") or []
        w(f"| `{f['nom']}` | {f['source']} {f['source_id']} | {f['resolution']} | {f['tile_m']} ({(f.get('tile_m_source') or '')[:40]}) | "
          f"{', '.join(f'{x:.3f}' for x in al)} ({', '.join(str(x) for x in f.get('albedo_moyen_srgb8') or [])}) | "
          f"{rg.get('moyenne')} ± {rg.get('ecart_type')} | {m.get('libelle', '')} | {m.get('choix', '')} |")
    w("\nFiches des autres matériaux (`route_fr` étape 1 et site, non modifiés) :\n")
    w("| nom | bibliothèque | albédo moyen linéaire | rugosité moyenne | tuile (m) |")
    w("|---|---|---|---|---|")
    for f in fiches:
        if f.get("etape3"):
            continue
        rg = f.get("rugosite") or {}
        al = f.get("albedo_moyen_lineaire") or []
        w(f"| `{f['nom']}` | {f['bibliotheque']} | {', '.join(f'{x:.3f}' for x in al)} | {rg.get('moyenne')} | {f.get('tile_m')} |")
    w("")
    # ------------------------------------------------------------------ sources
    w("## 8. Sources de l'étape 3\n")
    import specs_assets_etape3 as SE  # noqa: E402
    w("| clé | document | fichier ou URL | statut |")
    w("|---|---|---|---|")
    for k, v in SE.SOURCES_E3.items():
        w(f"| `{k}` | {v.get('doc')} | {v.get('fichier') or v.get('url') or ''} | {v.get('statut', '')} |")
    w("\nSources de l'étape 1 réutilisées : IISR 1re partie (art. 5-3, 6, 8, 9, 9-1, 9-2, 10), IISR 6e partie, Alkern 2026 (p. 11, "
      "15, 21, 49-53), Angers CPU, Noblema, arrêté du 15/01/2007, `assets/specs/feux.json` (relevés de Meylan).\n")
    w("Pages web consultées le 17/10/2026 (cotes relevées, rien de copié) : fiches Aximum GS2, GS4+, DE2+R4, Tau Tube P50/80 et "
      "plaquette atténuateurs (aximum.com, PDF dans `_sources_etape3/retenue`) ; Ville d'Angers, CPU : banc-banquette-lames-de-bois, "
      "corbeille-proprete-beton, corbeille-proprete-vigipirate, abribus, abri-tramway, arceaux-velos (fiche-arceau.pdf), "
      "borne-fontaine, lanternes ; Hellopro : mâts Odyssée Lumière 3-6 m et 9,3-12,8 m ; résultats de recherche pamline.com "
      "(PAMREX 600, grille ECML30ZF, bouche à clé TOTALE) ; API ambientCG et Poly Haven (textures CC0).\n")
    # ------------------------------------------------------------------ contrôles
    w("## 9. Contrôles\n")
    w("### 9.1 Planches de rendu (Karma XPU, exposition fixe, ≤ 1092 px, regardées à la taille native)\n")
    w("| planche | assets | fichier | constat |")
    w("|---|---|---|---|")
    for k, v in rendus.items():
        w(f"| {k} | {len(v['assets'])} | `controle/etape3/{v['png']}` | {constats.get(k, '')} |")
    w("")
    w("### 9.2 Contrôles automatiques\n")
    neg = [a["id"] for a in meshes if (a.get("volume_m3") or 0) <= 0]
    w(f"- Volume des maillages (faces orientées vers l'extérieur) : {len(meshes) - len(neg)} / {len(meshes)} positifs ; "
      + (f"négatifs ou nuls : {', '.join(neg)} (pièces à faces ouvertes F/G : décalques, vasques, ce qui fausse le volume signé)." if neg else "aucun négatif."))
    al = [a for a in A if a.get("alerte")]
    w(f"- Alertes de fabrication : {len(al)}" + (" — " + " ; ".join(f"`{a['id']}` : {a['alerte']}" for a in al) if al else "."))
    w(f"- Panneaux : {len(pans)} USD, {sum(len(a['dimensions']['gammes_m']) for a in pans)} variantes de gamme, "
      f"{sum(1 for a in pans if 'fbx_normale' in a['fichiers'])} FBX (gamme normale).")
    w("")
    w("### 9.3 Constats et corrections\n")
    for c in constats.get("_corrections", []):
        w(f"- {c}")
    w("")
    # ------------------------------------------------------------------ lacunes
    w("## 10. Lacunes\n")
    for l in constats.get("_lacunes", []):
        w(f"- {l}")
    w("")
    w("## 11. Licences\n")
    w("- Meshes : création maison (HDA `route::*`), cotes tirées de documents publics cités ; aucune géométrie copiée d'un fabricant, "
      "aucune donnée City Sample ni CARLA.")
    w("- Matériaux : CC0 1.0 (ambientCG, Poly Haven) ; matériaux simples : maison.")
    w("- Faces des panneaux : signaux officiels du Cerema (PDF détourés, Licence Ouverte 2.0 présumée, réserve non levée : voir "
      "`panneaux_fr_catalogue.json` meta.licence_source) ; PNG et USD de panneaux non versionnés.")
    w("- Fiches fabricants (Aximum, Saint-Gobain PAM, Odyssée Lumière, Alkern) et documents des collectivités (Angers, Grenoble-Alpes "
      "Métropole) : consultés et cités (cotes, pages), non redistribués (`assets/lib/route_fr/_sources_etape3/`, non versionné).")
    SORTIE.write_text("\n".join(o) + "\n", encoding="utf-8")
    print("écrit", SORTIE, len(o), "lignes")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ICI))
    main()
