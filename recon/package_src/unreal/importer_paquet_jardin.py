"""Unreal Engine 5.8 — importe la scène « Paquet Jardin, octobre 2026 » (USD).

Prérequis (une fois) : Edit > Plugins, activer « USD Importer » et « Python Editor Script Plugin »
(et, si besoin, « Georeferencing »), puis redémarrer l'éditeur.

Lancement : Tools > Execute Python Script... (choisir ce fichier), ou dans l'Output Log (Python) :
    py "C:/.../package/unreal/importer_paquet_jardin.py"

Deux modes :
  MODE = "stage"  : ajoute un UsdStageActor qui lit directement le .usda (scène « vivante » :
                    rechargement instantané quand le paquet est régénéré ; idéal pour vérifier).
  MODE = "import" : convertit en assets Unreal (Static Meshes, matériaux, textures) dans DEST
                    et place les acteurs dans le niveau (pour Nanite, éclairage, packaging, CARLA).

Repère : USD en mètres Z-up ; Unreal convertit à l'import (1 m = 100 uu, axe Y inversé).
Origine du niveau = point O (Lambert-93 917279.43 / 6460289.98, altitude NGF 216.30 m).
"""
import os

import unreal

MODE = "stage"                              # "stage" ou "import"
DEST = "/Game/Meylan/PaquetJardin"
AJOUTER_LUMIERES = True                     # soleil + ciel + atmosphère si le niveau n'en a pas
PKG = None                                  # dossier « package » ; détecté automatiquement si None


def paquet():
    if PKG:
        return PKG
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        raise SystemExit("Renseigne PKG (chemin du dossier package) en tête du script.")


def regler(obj, valeurs):
    for k, v in valeurs.items():
        try:
            obj.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001 — les noms de propriétés varient selon les versions
            unreal.log_warning(f"[paquet_jardin] propriété ignorée {k} : {e}")


def acteurs():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def mode_stage(usda):
    a = acteurs().spawn_actor_from_class(unreal.UsdStageActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    a.set_actor_label("PaquetJardin_2026_USD")
    try:
        a.set_root_layer(usda)
    except Exception:  # noqa: BLE001
        a.set_editor_property("root_layer", unreal.FilePath(usda))
    unreal.log(f"[paquet_jardin] UsdStageActor créé sur {usda}")
    return a


def mode_import(usda):
    opts = unreal.UsdStageImportOptions()
    regler(opts, {
        "import_actors": True, "import_geometry": True, "import_materials": True,
        "import_skeletal_animations": False, "import_level_sequences": False,
        "reuse_identical_assets": True, "merge_identical_material_slots": True,
        "existing_actor_policy": unreal.ReplaceActorPolicy.REPLACE,
        "existing_asset_policy": unreal.ReplaceAssetPolicy.REPLACE,
    })
    t = unreal.AssetImportTask()
    regler(t, {"filename": usda, "destination_path": DEST, "automated": True, "save": True,
               "replace_existing": True, "options": opts})
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    unreal.log(f"[paquet_jardin] import terminé dans {DEST} : {list(t.get_editor_property('imported_object_paths'))[:5]}...")


def lumieres():
    presentes = {type(a).__name__ for a in acteurs().get_all_level_actors()}
    sub = acteurs()
    if "DirectionalLight" not in presentes:
        sun = sub.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 5000), unreal.Rotator(-45, 0, 135))
        try:
            sun.light_component.set_editor_property("atmosphere_sun_light", True)
        except Exception:  # noqa: BLE001
            pass
    if "SkyAtmosphere" not in presentes:
        sub.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    if "SkyLight" not in presentes:
        sky = sub.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
        try:
            sky.light_component.set_editor_property("real_time_capture", True)
        except Exception:  # noqa: BLE001
            pass
    if "ExponentialHeightFog" not in presentes:
        sub.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))


def main():
    pkg = paquet().replace("\\", "/")
    usda = f"{pkg}/paquet_jardin_2026.usda"
    if not os.path.exists(usda):
        raise SystemExit(f"introuvable : {usda}")
    if MODE == "import":
        mode_import(usda)
    else:
        mode_stage(usda)
    if AJOUTER_LUMIERES:
        lumieres()
    unreal.log("[paquet_jardin] terminé — voir GUIDE_PC.md pour les matériaux Unreal, l'OpenDRIVE et CARLA.")


main()
