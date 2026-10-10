# recon/pcg/ue : pont Claude -> Unreal 5.8 (projet D:/ClaudeADAS)

## Connexion MCP
- L'editeur (plugin `ModelContextProtocol`, demarrage auto) sert `http://127.0.0.1:8000/mcp`
  (Streamable HTTP JSON-RPC, protocole 2025-06-18, en-tete `Mcp-Session-Id`).
- `.mcp.json` a la racine du depot declare le serveur `unreal-mcp` pour Claude Code.
- `bEnableToolSearch=True` : 3 meta-outils seulement, `list_toolsets`, `describe_toolset`,
  `call_tool{toolset_name, tool_name, arguments}`.
- Client Python reutilisable : `mcp_client.py` (requests).

```
python mcp_client.py wait 600                     # attend l'editeur
python mcp_client.py toolsets
python mcp_client.py pj list_assets '{"path":"/Game/Carla/Static/Vegetation/Trees"}'
```
```python
from mcp_client import McpClient
with McpClient() as c:
    c.pj('spawn_static_mesh', {'asset_path': '/Game/Carla/Static/Vegetation/Trees/SM_Oak_M_v1',
         'x_m': 0, 'y_m': 0, 'z_m': 0, 'yaw_deg': 0, 'label': 'Chene_essai'})
```

## Toolset `pj_tools` (nom MCP : `pj_tools.toolset.pj_tools`)
Source de verite : `pj_tools/` (paquet `pj_tools/pj_tools/` + `init_unreal.py`).
Installation : `python pj_tools/installer.py` (copie dans `D:/ClaudeADAS/Content/Python/`), puis
outil `reload_pj_tools` (editeur ouvert) ou redemarrage. Chaque outil renvoie du JSON `{"ok": ...}`.

| Outil | Role |
|---|---|
| `run_python_file(path, args_json=None)` | execute un .py dans l'editeur (stdout capture, `ARGS`, `RESULT`) |
| `import_usd(usd_path, dest_path, render_context=None, collapse=False, kinds_to_collapse=None, use_prim_kinds_for_collapsing=None, uv_pleine_precision=True, nanite=False)` | import USD (assets + acteurs), options toutes explicites et renvoyees ; contexte `unreal` par defaut (materiau USD -> materiau UE via `info:unreal:sourceAsset` ; MI absent = slot vide), `universal` = UsdPreviewSurface ; fusion par kind (`kinds_to_collapse` : masque model 1, component 2, group 4, assembly 8, subcomponent 16 ; defaut 0 = un StaticMesh par Mesh ; 2 = un par component, cf. CONTRAT_EXPORT.md) ; UV 32 bits ; `nanite` active Nanite (requis pour le deplacement des remplissages) ; renvoie `meshes` (reglages de build, nb UV, nanite), `journal` (LogStaticMesh/LogUsd) et `acceptation` (0 avertissement LogStaticMesh) |
| `import_textures(dir, dest_path)` | import d'un dossier d'images (normales / masques lineaires par suffixe) |
| `spawn_static_mesh(asset_path, x_m, y_m, z_m, yaw_deg, label, scale=1)` | pose en coordonnees LOCALES |
| `load_level(path)` / `new_level(path, template=None)` | niveaux (sans boite de dialogue ; modele conseille `/Engine/Maps/Templates/Template_Default`) ; avec `discard_untitled`, un niveau sans titre modifie est enregistre dans `/Game/PJ/Essais/Poubelle/Niveau_SansTitre` (SetDirtyFlag absent de Python en 5.8) |
| `save_all()` | enregistre niveaux et contenus modifies |
| `high_res_capture(out_png, cam_x_m, cam_y_m, cam_z_m, yaw_deg, pitch_deg, fov_deg, width, height, warmup=32, ev100=-100, auto_mean_target=118, exr=True)` | rendu ASYNCHRONE sur de vraies images moteur (Lumen et SkyLight temps reel accumulent) : `warmup` images puis l'image finale ; cible RGBA16F, source tone curve HDR : EXR lineaire + PNG sRGB trame (TPDF, sans bandes) ; exposition manuelle `ev100` (biais -EV100, comme le PostProcessVolume du niveau), -100 = auto (dichotomie, EV renvoye), -200 = PPV du niveau ; reference du projet : 14 (`eclairage.EV100`) ; post-process neutre (sans vignettage) ; une capture a la fois |
| `high_res_capture_etat(out_png)` | etat de la capture (rappeler jusqu'a `fini`) : phase, images, png, exr, ev100, moyenne sRGB, duree ; `ok=false` si echec |
| `list_assets(path, recursive=True, limit=2000)` | inventaire Asset Registry |
| `charger_points(json_path, asset_path, etat_seulement=False)` | cuit un fichier `pj_points/0.1` en PCGDataAsset reecrit en place (graphe outil `/Game/PJ/PCG/Outils/PG_Cuisson_Points`, asynchrone : rappeler avec `etat_seulement=true` jusqu'a `fini`) ; orientation `q` [x,y,z,w] prioritaire, sinon `rpy_deg` ; q et rpy doivent concorder (0,05 deg) ; `cd:[...]` -> attributs Float `cd0..cdN-1` (absent = -9), a passer au Static Mesh Spawner par `PCGInstanceDataPackerByAttribute` (PerInstanceCustomData, cf. materiaux/essai_bordures_cd.py) |
| `reload_pj_tools()` | recharge le code apres mise a jour (sous-modules compris) |

Autres toolsets publies : `EditorToolset.EditorAppToolset` (CaptureViewport, Get/SetCameraTransform,
SearchCVars, StartPIE...), `EditorToolset.LogsToolset`, `editor_toolset.toolsets.*` (Actor, Asset, Scene,
StaticMesh, Material...), `PCGToolset.PCGToolset`, `PCGToolset.PCGSpatialToolset`, `ToolsetRegistry.AgentSkillToolset`.
Piege : un parametre `str = ''` devient obligatoire dans le schema ; utiliser `str | None = None`.
CaptureViewport exige l'objet `annotations` complet (gridSpacing=0... classFilter=null).

## Repere
`pj_tools/pj_tools/repere.py` (seule implementation) : local = L93 - (917279.43, 6460289.98),
z = NGF - 216.30, m, Z haut. UE : X = 100x, Y = -100y, Z = 100z (cm), yaw_UE = -yaw.
Orientations (conjugaison par le miroir M = diag(1,-1,1)) : `rpy_local_vers_ue` -> Rotator(roll=+r, pitch=-p,
yaw=-y) ; `quat_local_vers_ue` -> Quat(-x, y, -z, w). Test : `python tests/test_rotations.py` (maths) et
`pj_tools.run_python_file(tests/test_rotations.py)` (axes des Rotator/Quat d'UE, charger_points, PCGPointData).

## Contrat Houdini -> UE
`CONTRAT_EXPORT.md` : repere, kinds et fusion, normales (cusp 30 deg), UV `st` en metres, materiaux nommes
par `materiau_id`, points `pj_points/0.1` (q xyzw). Outils : `contrat/verifier_usd.py` (pxr : hython ou editeur),
`contrat/echantillon_contrat.{py,usda}` (reference), `python contrat/test_contrat.py` (acceptation dans UE :
0 avertissement LogStaticMesh, normales et UV conservees, controles negatifs sur la couche v1).

## Eclairage et exposition (pj_tools/pj_tools/eclairage.py, reference unique)
EV100 = 14 partout (PJ_Phase0, PJ_Materiaux, futur PJ_2026, captures, capteurs) ; soleil 128 klux hors atmosphere
(UE applique la transmittance de SkyAtmosphere a une lumiere atmosphere_sun_light), az. 220 deg, elev. 27,6 deg ;
SkyAtmosphere a aerosols de vallee (Mie 0,12 /km, epaisseur optique ~0,14 ; 0,004 d'origine = ombres bleu marine) ;
SkyLight temps reel, intensite 1 ; balance 5500 K ; post-process neutre (ni vignettage, ni grain, ni aberration).
Gris 18 % au soleil : 0,14 (lineaire apres courbe de ton) ; EV auto de la vue de controle t1 : 13,8.
Applique par `tests_phase0/ue/t1_niveau.py` (defauts tires du module) ; controle par t7.

## Capture (pj_tools/pj_tools/capture.py)
SceneCapture2D rendu un `capture_scene()` par tick moteur (rappel post-tick Slate, viewports invalides) ; les
48 rendus dans un seul tick de l'ancienne version privaient Lumen et la SkyLight de leur historique (ombres et
feuillage a l'ombre noirs, rapport ombre/soleil 0,016). Non-regression : `python tests_phase0/phase0.py t7`
(boite haute sur le sol neutre : rapport ombre/soleil dans [0,18 ; 0,32], canal R >= 0,10, et a moins de 20 % de
`EditorAppToolset.CaptureViewport` a la meme pose ; mesure au 10/10 : 0,216, R 0,16, ecart 0,3 %).
Post-process neutre impose a la SceneCapture (eclairage.POST_PROCESS_NEUTRE). Une cible detruite (niveau recharge
sous le meme chemin) est recreee (`_valide` : is_valid leve TypeError sur un objet ramasse).

Textures a pleine resolution pendant une capture : le streaming de textures dimensionne les mips sur la camera du
viewport de l'editeur, pas sur la SceneCapture (constat : remplissages lus a 64 px, images floues) ; la capture
coupe `r.TextureStreaming` puis restaure la valeur, avec 2 s de chauffe au minimum. Une cible de rendu par taille
est reutilisee (une par capture saturait la memoire).

## Materiaux du sol (`materiaux/`)
34 `MI_<materiau_id>` (+ 10 `__citysample`, 23 `__carla`, 10 peintures) sur 4 maitres `/Game/PJ/Materials/Maitres/M_PJ_{Sol,
Remplissage,Bordure,Peinture}`, albedo etalonne dans UE sur materiaux_sol.json, deplacement Nanite des remplissages,
niveau d'essai `/Game/PJ/Maps/PJ_Materiaux`. Commandes et choix : `materiaux/README.md`.

## Contenu CARLA
Sous-ensemble copie dans `D:/ClaudeADAS/Content/Carla/` (chemins `/Game/Carla/...` conserves,
CC-BY 4.0, CARLA Team / CVC) puis re-sauve en 5.8 (`ResavePackages`) : Static/{Vegetation, GenericMaterials,
Decals/Road, Decals/Pavement, Static, Fence, Pole}, les 2 MPC (CarlaParameters, WeatherMaterialParameters) et
135 dependances moteur seules hors de ces dossiers (fermeture calculee sur carla_scan.json). Exclus : les 10 BP
dependant de /Script/Carla (Static/Static/BP_BillBoard1-3, BP_BusStop, BP_CarlaCola, BP_Fountain, BP_TrashCan02,
DroppingAsset, Static/Pole/BP_AddPole, BP_AddPole1). 3156 fichiers, 7,19 Go copies, 6,23 Go apres resave.

## Contenu d'essai cree
`/Game/PJ/Maps/PJ_Essai_Setup` (modele Template_Default, SM_Oak_M_v1 a x=8 m, SM_Bush_M_v1, dalle USD d'essai,
acteur `PJ_Capture`), `/Game/PJ/Essais/{USD,Textures}`.

## Transport des points -> PCG (phase 0, voie retenue : b)
`pj_points/0.1` (JSON, m locaux) -> `pj_tools.charger_points` -> PCGDataAsset (attributs `Mesh` SoftObjectPath,
`Id`, `Graine` ; transform UE deja convertie) -> graphe natif `Load PCG Data Asset` -> `Static Mesh Spawner`
(`PCGMeshSelectorByAttribute`, attribut `Mesh`). Description et commandes MCP : `graphes/PG_Points_Test.json`.
Code : `pj_tools/pj_tools/charger_points.py` (lecture, conversion, script du noeud Python Data Processor, cuisson).
Pieges : le noeud Python Data Processor n'est pas propose par `PCGToolset.AddNode` (ajout en Python,
`graph.add_node_of_type`) et ne s'execute que si sa broche `Input` est alimentee ; la broche de sortie du
`Load PCG Data Asset` porte le libelle stocke dans l'asset (`In`) ; `UpdateNode` ne sait pas regler
`meshSelectorParameters` (repli Python). Voie (c) Data Table : aucune structure de ligne utilisable
(il faudrait une UserDefinedStruct faite a la main ou en C++), non retenue.

## Essais de phase 0 (`tests_phase0/`)
`python tests_phase0/phase0.py tout` (editeur ouvert) : niveau `/Game/PJ/Maps/PJ_Phase0`, vegetation CARLA,
mires, import USD, points -> PCG, Houdini Engine, non-regression de la capture (t7).
Sorties : `recon/out/paquet_jardin/v2/ue_phase0/`. t5 ne supprime aucun asset : volumes PCG nettoyes puis
detruits, graphes `PG_Points_Test*` vides et reutilises, PCGDataAsset reecrit en place (un ForceDelete d'asset
encore reference laisse un paquet corrompu en memoire).
Reference d'eclairage : `pj_tools/eclairage.py` (az. geographique 220 deg = 218 deg quadrillage L93, elevation
27,6 deg : 15/10/2026 15h43 CEST ; soleil 128 klux hors atmosphere, Mie 0,12, EV100 = 14, balance 5500 K).

## Correctifs CARLA (copie projet, jamais `D:/CARLA_Assets`)
`correctifs/carla_imposteurs.py` : les LOD imposteurs des vegetaux CARLA s'affichent en blocs arrondis dans
UE 5.8 ; leur taille d'ecran est mise a 0 (77 meshes de `/Game/Carla/Static/Vegetation`).
