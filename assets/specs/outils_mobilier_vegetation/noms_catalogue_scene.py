"""Renomme, par une couche USD réversible, les prototypes de la scène avec les NOMS D'ASSETS DU CATALOGUE
(à lancer sur le PC AVANT package/substituer_assets.py ; Python avec pxr : hython de Houdini 22 ou usd-core).

Pourquoi : la scène v1 (paquet_jardin_2026.usda) nomme ses prototypes d'après l'atelier objets
(lampadaire_crosse_double, banc, corbeille, feu_tete_R11v, arbre_populus_nigra_petit...). Les assets que tu
fabriques portent les noms du catalogue (candelabre_double_crosse, banc_bois_metal, corbeille_cylindrique,
feu_R11v, arbre_populus_nigra_italica_grand...) et substituer_assets.py ne cherche que le nom exact du
prototype : sans cette couche, presque rien ne serait substitué.

Ce que fait la couche layers/noms_catalogue.usda (insérée en tête des sous-couches de la scène racine) :
  1. pour chaque PointInstancer, ajoute des prototypes nommés comme les assets du catalogue (chacun référence
     le prototype d'origine : le volume provisoire reste visible tant que l'asset n'est pas livré) ;
  2. réaffecte CHAQUE instance à l'asset de SON identifiant (tables « par_instance » de assets/specs/mobilier.json
     et vegetation.json › correspondance_scene_v1) : un même prototype de scène peut ainsi devenir plusieurs
     assets (lampadaire_mat_droit → candelabre_mat_droit_led ×23 + candelabre_mat_droit_shp ×4) ;
  3. ajoute aux arbres le primvar « hauteur_m » que lit substituer_assets.py pour mettre chaque arbre à
     l'échelle de sa hauteur (la scène v1 ne porte que « hauteur_cible_m ») ; les hauteurs aberrantes
     relevées en V2 (arbre voisin capté par le LiDAR) sont remplacées par la hauteur retenue.
Rien d'autre n'est modifié ; --retirer enlève la couche. Ensuite : substituer_assets.py --librairie <lib>.

Usage :
    hython noms_catalogue_scene.py --scene D:/Meylan/package/paquet_jardin_2026.usda
    python noms_catalogue_scene.py --scene <...>.usda --dry-run     (rapport seulement)
    python noms_catalogue_scene.py --scene <...>.usda --retirer
Options : --specs <dossier assets/specs> (défaut : celui de ce script).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, Vt

ICI = Path(__file__).resolve().parent
COUCHE = "layers/noms_catalogue.usda"


def tables(specs: Path):
    par_instance = {}
    for nom in ("mobilier.json", "vegetation.json"):
        d = json.loads((specs / nom).read_text(encoding="utf-8"))
        cs = d.get("correspondance_scene_v1") or {}
        par_instance.update(cs.get("par_instance") or {})
    return par_instance


def nom_valide(s: str) -> str:
    return s if Sdf.Path.IsValidIdentifier(s) else "n_" + "".join(c if c.isalnum() else "_" for c in s)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scene", required=True, help="paquet_jardin_2026.usda (scène racine)")
    ap.add_argument("--specs", default=str(ICI.parent), help="dossier assets/specs (mobilier.json, vegetation.json)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retirer", action="store_true", help="enlève la couche de renommage")
    a = ap.parse_args()

    scene = Path(a.scene).resolve()
    couche = scene.parent / COUCHE
    rel = os.path.relpath(couche, scene.parent).replace("\\", "/")
    root = Sdf.Layer.FindOrOpen(str(scene))
    if rel in root.subLayerPaths and not a.dry_run:
        root.subLayerPaths.remove(rel)
        root.Save()
    if a.retirer:
        if couche.exists():
            couche.unlink()
        print("couche retirée :", rel)
        return

    table = tables(Path(a.specs))
    stage = Usd.Stage.Open(str(scene))
    edit = None
    if not a.dry_run:                                   # écriture directe en Sdf : les références internes ne se résolvent
        if couche.exists():                             # que dans la pile de couches de la scène racine
            couche.unlink()
        edit = Sdf.Layer.CreateNew(str(couche))
        edit.pseudoRoot.SetInfo("upAxis", "Z")
        edit.pseudoRoot.SetInfo("metersPerUnit", 1.0)

    bilan = collections.Counter()
    noms_finaux = collections.Counter()
    hors_table = collections.Counter()
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.PointInstancer):
            continue
        pi = UsdGeom.PointInstancer(prim)
        cibles = list(pi.GetPrototypesRel().GetTargets())
        noms = [c.name for c in cibles]
        idx = list(pi.GetProtoIndicesAttr().Get() or [])
        pv = UsdGeom.PrimvarsAPI(prim)
        ids = list(pv.GetPrimvar("id").Get()) if pv.HasPrimvar("id") else [None] * len(idx)
        hc = list(pv.GetPrimvar("hauteur_cible_m").Get()) if pv.HasPrimvar("hauteur_cible_m") else None

        nouvelles = list(cibles)
        position = {c.name: k for k, c in enumerate(cibles)}
        source_de = {}                                  # nom catalogue -> prototype de scène d'origine (premier rencontré)
        nouv_idx = []
        hauteurs = []
        for i, k in enumerate(idx):
            proto = noms[k]
            e = table.get(ids[i]) if ids[i] is not None else None
            asset = e["asset"] if e and not str(e.get("asset", "")).startswith("(") else proto
            if not e:
                hors_table[proto] += 1
            asset = nom_valide(asset)
            if asset not in position:
                parent = cibles[k].GetParentPath()
                position[asset] = len(nouvelles)
                nouvelles.append(parent.AppendChild(asset))
                source_de[asset] = cibles[k]
            nouv_idx.append(position[asset])
            noms_finaux[asset] += 1
            bilan["renommees" if asset != proto else "inchangees"] += 1
            if hc is not None:
                h = e.get("hauteur_retenue_m") if e else None
                hauteurs.append(float(h if h is not None else hc[i]))
                if h is not None:
                    bilan["hauteurs_corrigees"] += 1
        if edit is None:
            continue
        for asset, src in source_de.items():           # nouveaux prototypes : référence interne au prototype d'origine
            ps = Sdf.CreatePrimInLayer(edit, src.GetParentPath().AppendChild(asset))
            ps.specifier = Sdf.SpecifierDef
            ps.typeName = "Xform"
            ps.referenceList.Prepend(Sdf.Reference(primPath=src))
            ps.customData = {"nom_catalogue": asset, "prototype_scene_origine": src.name}
        ip = Sdf.CreatePrimInLayer(edit, prim.GetPath())        # over sur l'instanceur
        rs = Sdf.RelationshipSpec(ip, "prototypes", custom=False)
        rs.targetPathList.explicitItems = nouvelles
        att = Sdf.AttributeSpec(ip, "protoIndices", Sdf.ValueTypeNames.IntArray)
        att.default = Vt.IntArray(nouv_idx)
        if hc is not None and str(prim.GetPath()).startswith("/World/Vegetation"):
            pv_ = Sdf.AttributeSpec(ip, "primvars:hauteur_m", Sdf.ValueTypeNames.FloatArray)
            pv_.default = Vt.FloatArray(hauteurs)
            pv_.SetInfo("interpolation", UsdGeom.Tokens.vertex)

    if edit is not None:
        edit.customLayerData = {"role": "renommage des prototypes de la scène v1 vers les noms du catalogue (assets/specs)",
                                "source": "assets/specs/outils_mobilier_vegetation/noms_catalogue_scene.py",
                                "note": "les prototypes d'origine restent dans la liste (inutilisés) : substituer_assets.py les liste comme « encore provisoires »"}
        edit.Save()
        root.subLayerPaths.insert(0, rel)
        root.Save()
        print("couche écrite :", couche)
    print(f"instances renommées : {bilan['renommees']}, inchangées : {bilan['inchangees']}, hauteurs d'arbres corrigées : {bilan['hauteurs_corrigees']}")
    if hors_table:
        print("instances absentes des tables (nom de scène conservé) :", dict(hors_table))
    print(f"{len(noms_finaux)} noms de prototypes après renommage :")
    for n, c in sorted(noms_finaux.items()):
        print(f"   {n} ×{c}")


if __name__ == "__main__":
    main()
