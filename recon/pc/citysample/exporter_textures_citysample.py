# -*- coding: utf-8 -*-
"""Export des textures City Sample (Epic Games) pour le look-dev optionnel du carrefour Paquet Jardin.

Script Python Unreal Engine 5.7, lancé en commandlet (sans rendu) sur le projet CitySample :

  "C:/Program Files/Epic Games/UE_5.7/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
      "C:/Users/flori/Documents/Unreal Projects/CitySample/CitySample.uproject"
      -run=pythonscript -script="<chemin de ce fichier>"
      -unattended -nop4 -nosplash -NullRHI -stdout -FullStdOutLogOutput

Lecture seule : les textures sont chargées puis exportées depuis leurs données source ; aucun
asset du projet n'est modifié ni sauvegardé.

LICENCE : le contenu City Sample / Megascans est sous EULA Unreal Engine et n'est PAS
redistribuable. La sortie va dans recon/pc/citysample/textures/brut/, ignoré par git
(recon/pc/.gitignore). Ce fichier ne contient que du code et des chemins d'assets.

Variables d'environnement (optionnelles) :
  CITYSAMPLE_MODE   = export (défaut) | inventaire | tout
  CITYSAMPLE_SORTIE = dossier de sortie (défaut : <dossier de ce script>/textures/brut)
"""
import json
import os
import sys

import unreal

# Dossiers inventoriés (mode inventaire) : surfaces Megascans, atlas, kits de voirie, environnement.
DOSSIERS_INVENTAIRE = [
    "/Game/Megascans/Surfaces",
    "/Game/Megascans/Atlases",
    "/Game/Megascans/Imperfections",
    "/Game/Road",
    "/Game/Environment",
    "/Game/Building/Texture",
    "/Game/Textures/SurfaceFeature",
]

# Instances de matériaux lues pour connaître le rangement des canaux et les tuilages.
MATERIAUX_INSPECTES = [
    "/Game/Road/Material/MI/M_Asphalt_Master_Inst",
    "/Game/Road/Material/MI/M_Asphalt_Master_Inst_Intersection",
    "/Game/Road/Material/MI/M_Asphalt_Master_Inst_Crosswalk",
    "/Game/Road/Material/MI/M_Asphalt_Master_Inst_ParkingLots",
    "/Game/Road/Material/MI/M_Sidewalk_Master_Inst",
    "/Game/Road/Material/MI/M_Sidewalk_Master_Inst_2",
    "/Game/Road/Material/MI/MI_Sidewalk",
    "/Game/Road/Material/MI/M_roadcurb_master_concrete_instance",
    "/Game/Road/Material/MI/MI_FreewayAsphalt_Road",
    "/Game/Road/Material/MI/MI_FreewayAsphalt_RoadDark",
    "/Game/Road/Kit_Small_Curb_A/Material/Instance/MI_SM_Small_Curb_A_Straight_01_Element0",
    "/Game/Megascans/Atlases/Road_Dust_2x2_M_00/Road_Dust_2x2_M_00_inst",
    "/Game/Megascans/Atlases/White_Road_Line_00/White_Road_Line_00_inst",
    "/Game/Megascans/Atlases/Road_Line_00/Road_Line_00_inst",
    "/Game/Megascans/Atlases/Asphalt_Patch_01/Asphalt_Patch_01_inst",
]

# Textures exportées : (chemin de l'asset, nom du fichier de sortie sans extension).
# Les noms Megascans (…_2x2_M…) donnent la taille de tuile (2 m).
_AR = "/Game/Megascans/Surfaces/Cast_In_Situ_Concrete_Wall_vcfice0"
TEXTURES = [
    # enrobé ancien (chaussée, parking, accès riverains, piste)
    (_AR + "/Asphalt_Road_2x2_M_01/th5ldh0cw_8K_Albedo", "asphalt_road_01_albedo"),
    (_AR + "/Asphalt_Road_2x2_M_01/th5ldh0cw_8K_Normal", "asphalt_road_01_normal"),
    (_AR + "/Asphalt_Road_2x2_M_01/th5ldh0cw_8K_Roughness", "asphalt_road_01_roughness"),
    (_AR + "/Asphalt_Road_2x2_M_02/tiggcjdo_8K_Albedo", "asphalt_road_02_albedo"),
    (_AR + "/Asphalt_Road_2x2_M_02/tiggcjdo_8K_AO", "asphalt_road_02_ao"),
    (_AR + "/Asphalt_Road_2x2_M_02/tiggcjdo_8K_Normal", "asphalt_road_02_normal"),
    (_AR + "/Asphalt_Road_2x2_M_02/tiggcjdo_8K_Roughness", "asphalt_road_02_roughness"),
    (_AR + "/Asphalt_Road_2x2_M_03/th5kfebew_8K_Albedo", "asphalt_road_03_albedo"),
    (_AR + "/Asphalt_Road_2x2_M_03/th5kfebew_8K_Normal", "asphalt_road_03_normal"),
    (_AR + "/Asphalt_Road_2x2_M_03/th5kfebew_8K_Roughness", "asphalt_road_03_roughness"),
    (_AR + "/Coarse_Road_2x2_M_01/se0oeima_8K_Albedo", "coarse_road_01_albedo"),
    (_AR + "/Coarse_Road_2x2_M_01/se0oeima_8K_Normal", "coarse_road_01_normal"),
    (_AR + "/Coarse_Road_2x2_M_01/se0oeima_8K_Roughness", "coarse_road_01_roughness"),
    ("/Game/Megascans/Surfaces/Asphalt_Dried01_2x2/Asphalt_Dried01_C", "asphalt_dried01_albedo"),
    ("/Game/Megascans/Surfaces/Asphalt_Dried01_2x2/Asphalt_Dried01_N", "asphalt_dried01_normal"),
    ("/Game/Megascans/Surfaces/Asphalt_Dried01_2x2/Asphalt_Dried01_AOMRD", "asphalt_dried01_aomrd"),
    # enrobé neuf (albédo seul dans City Sample)
    ("/Game/Megascans/Surfaces/Asphalt_Fresh_2x2_M_00/sfrofg0a_8K_Albedo", "asphalt_fresh_00_albedo"),
    ("/Game/Megascans/Surfaces/Cracked_Asphalt_2x2_M_00/Cracked_Asphalt_2x2_M_tlomaeady_4K_Normal",
     "cracked_asphalt_00_normal"),
    # trottoirs, béton, bordures
    ("/Game/Megascans/Surfaces/Dirty_Sidewalk_2x2_M_00/ugxjcdpn_4K_Albedo_noEdge", "dirty_sidewalk_00_albedo_noedge"),
    ("/Game/Megascans/Surfaces/Dirty_Sidewalk_2x2_M_00/ugxjcdpn_4K_Albedo", "dirty_sidewalk_00_albedo"),
    ("/Game/Megascans/Surfaces/Dirty_Sidewalk_2x2_M_00/ugxjcdpn_4K_Normal", "dirty_sidewalk_00_normal"),
    ("/Game/Megascans/Surfaces/Dirty_Sidewalk_2x2_M_00/ugxjcdpn_4K_Roughness", "dirty_sidewalk_00_roughness"),
    ("/Game/Megascans/Surfaces/Dirty_Sidewalk_2x2_M_00/ugxjcdpn_4K_AO", "dirty_sidewalk_00_ao"),
    ("/Game/Megascans/Surfaces/Concrete_Castinsitu_uflnbcofw/uflnbcofw_8K_Albedo", "concrete_castinsitu_albedo"),
    ("/Game/Megascans/Surfaces/Concrete_Castinsitu_uflnbcofw/uflnbcofw_8K_Normal", "concrete_castinsitu_normal"),
    ("/Game/Megascans/Surfaces/Concrete_Castinsitu_uflnbcofw/uflnbcofw_8K_Roughness", "concrete_castinsitu_roughness"),
    ("/Game/Megascans/Surfaces/Rough_Concrete_Floor_2x2/Rough_Concrete_Floor_2x2_C", "rough_concrete_floor_albedo"),
    ("/Game/Megascans/Surfaces/Rough_Concrete_Floor_2x2/Rough_Concrete_Floor_2x2_N", "rough_concrete_floor_normal"),
    ("/Game/Road/Textures/Sidewalks/T_sidewalk_concreteNoLines_Color", "sidewalk_concrete_nolines_albedo"),
    ("/Game/Road/Textures/Sidewalks/T_sidewalk_concreteNoLines_Normal", "sidewalk_concrete_nolines_normal"),
    ("/Game/Road/Textures/Sidewalks/T_sidewalk_concreteNoLines_AOR", "sidewalk_concrete_nolines_aor"),
    ("/Game/Megascans/Surfaces/FRACTURES/Concrete_Rough_2x2_M_00/Concrete_Rough_2x2_M_C", "concrete_rough_2x2_albedo"),
    ("/Game/Megascans/Surfaces/FRACTURES/Concrete_Rough_2x2_M_00/Concrete_Rough_2x2_M_N", "concrete_rough_2x2_normal"),
    ("/Game/Megascans/Surfaces/FRACTURES/Concrete_Rough_2x2_M_00/Concrete_Rough_2x2_M_AOMRD", "concrete_rough_2x2_aomrd"),
    ("/Game/Building/Texture/ConcreteDirty/T_ConcreteDirty_C", "concrete_dirty_albedo"),
    ("/Game/Building/Texture/ConcreteDirty/T_ConcreteDirty_N", "concrete_dirty_normal"),
    ("/Game/Building/Texture/ConcreteDirty/T_ConcreteDirty_AORMD", "concrete_dirty_aormd"),
    # peinture routière usée, poussière, imperfections
    ("/Game/Megascans/Atlases/White_Road_Line_00/sejqvcl_4K_Albedo", "white_road_line_00_albedo"),
    ("/Game/Megascans/Atlases/White_Road_Line_00/sejqvcl_4K_Opacity", "white_road_line_00_opacity"),
    ("/Game/Megascans/Atlases/White_Road_Line_00/sejqvcl_4K_Normal", "white_road_line_00_normal"),
    ("/Game/Megascans/Atlases/Road_Dust_2x2_M_00/Road_Dust_2x2_M_sg1no3n_8K_Albedo", "road_dust_00_albedo"),
    ("/Game/Megascans/Atlases/Road_Dust_2x2_M_00/Road_Dust_2x2_M_sg1no3n_8K_Opacity", "road_dust_00_opacity"),
    ("/Game/Megascans/Atlases/Road_Dust_2x2_M_00/Road_Dust_2x2_M_sg1no3n_8K_RAODM", "road_dust_00_raodm"),
    ("/Game/Megascans/Surfaces/Grunge_00/uh4uabdc_8K_Roughness", "grunge_00_roughness"),
    ("/Game/Megascans/Imperfections/sdnqcbnc_4K_Roughness", "imperfection_sdnqcbnc_roughness"),
]


def _dossier_sortie():
    d = os.environ.get("CITYSAMPLE_SORTIE")
    if not d:
        ici = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        d = os.path.join(ici, "textures", "brut")
    os.makedirs(d, exist_ok=True)
    return d


def _log(msg):
    unreal.log("[citysample] " + msg)
    print("[citysample] " + msg)
    sys.stdout.flush()


def inventaire(sortie):
    """Liste les Texture2D des dossiers candidats (tags du registre, sans chargement) et les
    paramètres des instances de matériaux de voirie (rangement des canaux, tuilage)."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.scan_paths_synchronous(DOSSIERS_INVENTAIRE, True)
    textures = []
    for dossier in DOSSIERS_INVENTAIRE:
        for a in reg.get_assets_by_path(dossier, recursive=True):
            classe = str(a.asset_class_path.asset_name)
            if classe not in ("Texture2D",):
                continue
            tags = {}
            for t in ("Dimensions", "Format", "CompressionSettings", "SRGB", "LODGroup", "VirtualTextureStreaming"):
                v = a.get_tag_value(t)
                if v:
                    tags[t] = str(v)
            textures.append({"asset": str(a.package_name), **tags})
    _log("%d textures inventoriées" % len(textures))
    mel = unreal.MaterialEditingLibrary
    materiaux = []
    for chemin in MATERIAUX_INSPECTES:
        mi = unreal.load_asset(chemin)
        if mi is None:
            materiaux.append({"asset": chemin, "erreur": "introuvable"})
            continue
        info = {"asset": chemin, "parent": str(mi.get_editor_property("parent").get_path_name())
                if mi.get_editor_property("parent") else None, "textures": {}, "scalaires": {}, "vecteurs": {}}
        for n in mel.get_texture_parameter_names(mi):
            t = mel.get_material_instance_texture_parameter_value(mi, n)
            info["textures"][str(n)] = t.get_path_name() if t else None
        for n in mel.get_scalar_parameter_names(mi):
            info["scalaires"][str(n)] = mel.get_material_instance_scalar_parameter_value(mi, n)
        for n in mel.get_vector_parameter_names(mi):
            c = mel.get_material_instance_vector_parameter_value(mi, n)
            info["vecteurs"][str(n)] = [round(c.r, 4), round(c.g, 4), round(c.b, 4), round(c.a, 4)]
        materiaux.append(info)
    chemin_json = os.path.join(sortie, "inventaire_citysample.json")
    with open(chemin_json, "w", encoding="utf-8") as f:
        json.dump({"textures": textures, "materiaux": materiaux}, f, ensure_ascii=False, indent=1)
    _log("inventaire écrit : " + chemin_json)


def _exporter_une(tex, fichier_base):
    """Exporte une texture depuis ses données source : PNG si possible, sinon TGA, sinon EXR."""
    for ext, exporteur in (("png", unreal.TextureExporterPNG), ("tga", unreal.TextureExporterTGA),
                           ("exr", getattr(unreal, "TextureExporterEXR", None))):
        if exporteur is None:
            continue
        fichier = fichier_base + "." + ext
        task = unreal.AssetExportTask()
        task.set_editor_property("object", tex)
        task.set_editor_property("filename", fichier)
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("exporter", exporteur())
        ok = unreal.Exporter.run_asset_export_task(task)
        if ok and os.path.isfile(fichier) and os.path.getsize(fichier) > 0:
            return fichier
    return None


def exporter(sortie):
    resultats = []
    for chemin, nom in TEXTURES:
        tex = unreal.load_asset(chemin)
        if tex is None:
            _log("ABSENT : " + chemin)
            resultats.append({"asset": chemin, "fichier": None, "erreur": "introuvable"})
            continue
        info = {"asset": chemin, "nom": nom,
                "srgb": bool(tex.get_editor_property("srgb")),
                "compression": str(tex.get_editor_property("compression_settings")),
                "flip_green": bool(tex.get_editor_property("flip_green_channel"))}
        fichier = _exporter_une(tex, os.path.join(sortie, nom))
        info["fichier"] = os.path.basename(fichier) if fichier else None
        _log(("OK     " if fichier else "ECHEC  ") + chemin + " -> " + str(info["fichier"]))
        resultats.append(info)
    with open(os.path.join(sortie, "export_citysample.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=1)
    n_ok = sum(1 for r in resultats if r.get("fichier"))
    _log("%d/%d textures exportées dans %s" % (n_ok, len(resultats), sortie))


def main():
    mode = os.environ.get("CITYSAMPLE_MODE", "export").strip().lower()
    sortie = _dossier_sortie()
    _log("mode %s, sortie %s" % (mode, sortie))
    if mode in ("inventaire", "tout"):
        inventaire(sortie)
    if mode in ("export", "tout"):
        exporter(sortie)


main()
