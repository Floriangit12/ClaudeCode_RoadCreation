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
| `high_res_capture(out_png, cam_x_m, cam_y_m, cam_z_m, yaw_deg, pitch_deg, fov_deg, width, height, warmup=32, ev100=-100, auto_mean_target=118, exr=True, exposition_locale=False)` | rendu ASYNCHRONE sur de vraies images moteur (Lumen et SkyLight temps reel accumulent) : `warmup` images puis l'image finale ; cible RGBA16F, source tone curve HDR : EXR lineaire + PNG sRGB trame (TPDF, sans bandes) ; exposition manuelle `ev100` (biais -EV100, comme le PostProcessVolume du niveau), -100 = auto (dichotomie, EV renvoye), -200 = PPV du niveau ; reference du projet : 14 (`eclairage.EV100`) ; post-process neutre (sans vignettage) ; `exposition_locale` : exposition locale des vignettes de planches (`eclairage.EXPOSITION_LOCALE_PLANCHES`), jamais pour les captures de reference ni les capteurs ; une capture a la fois |
| `high_res_capture_etat(out_png)` | etat de la capture (rappeler jusqu'a `fini`) : phase, images, png, exr, ev100, moyenne sRGB, duree ; `ok=false` si echec |
| `list_assets(path, recursive=True, limit=2000)` | inventaire Asset Registry |
| `charger_points(json_path, asset_path, etat_seulement=False)` | cuit un fichier `pj_points/0.1` en PCGDataAsset reecrit en place (graphe outil `/Game/PJ/PCG/Outils/PG_Cuisson_Points`, asynchrone : rappeler avec `etat_seulement=true` jusqu'a `fini`) ; orientation `q` [x,y,z,w] prioritaire, sinon `rpy_deg` ; q et rpy doivent concorder (0,05 deg) ; `cd:[...]` -> attributs Float `cd0..cdN-1` (absent = -9), a passer au Static Mesh Spawner par `PCGInstanceDataPackerByAttribute` (PerInstanceCustomData, cf. materiaux/essai_bordures_cd.py) ; `materiau` (chemin UE) -> attribut `Materiau` (surcharge par attribut du `PCGMeshSelectorByAttribute`) |
| `reload_pj_tools()` | recharge le code apres mise a jour (sous-modules compris) |

Autres toolsets publies : `EditorToolset.EditorAppToolset` (CaptureViewport, Get/SetCameraTransform,
SearchCVars, StartPIE...), `EditorToolset.LogsToolset`, `editor_toolset.toolsets.*` (Actor, Asset, Scene,
StaticMesh, Material...), `PCGToolset.PCGToolset`, `PCGToolset.PCGSpatialToolset`, `ToolsetRegistry.AgentSkillToolset`.
Piege : un parametre `str = ''` devient obligatoire dans le schema ; utiliser `str | None = None`.
CaptureViewport exige l'objet `annotations` complet (gridSpacing=0... classFilter=null).

## Pilote ZP-01 dans UE (`pilote/`, niveau `/Game/PJ/Maps/PJ_2026`)
```
python recon/pcg/ue/pilote/pilote.py tout        # editeur ouvert ; ou : niveau | imports | bordures [--bibliotheque] |
                                                 #   captures [a..f] | joints | planche | inventaire
```
Entree : `recon/out/paquet_jardin/v2/fabrique_ue_snapshot/` (instantane de `fabrique/`, ignore par git, regenerable par
`hython recon/pcg/houdini/fabriquer.py --sortie ... --sans-cameras`). Sorties : `recon/out/paquet_jardin/v2/ue_pilote/`.

| Etape | Script | Effet |
|---|---|---|
| niveau | `ue/materiaux_maison.py`, `ue/niveau_2026.py` | MI maison (mortiers, bitume, touffes, eclats, contexte) ; niveau non World Partition : soleil 128 klux hors atmosphere az. 220 / 27,6 deg, SkyAtmosphere Mie 0,12, SkyLight temps reel, brouillard, PPV EV100 14 / 5500 K neutre (`eclairage.py`), GeoReferencingSystem EPSG:2154 origine O (controle local (10, 20, 3) -> L93 - O exact), plan de contexte de 3 km a z = -1,9 m (gazon UV monde) |
| imports | `pj_tools.import_usd` x 4, `ue/retirer_imports.py`, `ue/inventaire.py`, `ue/collisions.py` | `sol.usda` (14 maillages), `decals_sol.usda` (pontages, 6 532 touffes, 39 dalles BEV), `ilots.usda` (227 eclats), `ilots_couverture.usdc` (282 057 eclats) : contexte unreal, Nanite, 0 avertissement LogStaticMesh ; les acteurs d'un import precedent sont retires d'abord (un reimport REPLACE double les entrees du tableau d'acteurs du niveau) ; collisions (`collisions.py` : collision complexe cuite sur le repli Nanite a pleine resolution, profil BlockAll ; eclats, touffes, dalles BEV, pontages, marquages et bouchons de joint exclus ; controle par rayons : sol a 0,05 mm pres, 15/15 bordures touchees, `ue_pilote/collisions_controle.json`) |
| bordures | `ue/bibliotheque_bordures.py`, `points_ue.py`, `pj_tools.charger_points`, `ue/pg_bordures.py` | 253 prototypes -> `/Game/PJ/Lib/Bordures/SM_<nom>` (Nanite, sans acteur ; import ~1,5 min, reimport force ~11 min) ; `points/bordures.json` -> `ue_pilote/points/bordures_ue.json` (assets UE, `materiau`, cd + z_pied_cm + demi_longueur_cm) -> `PDA_Bordures` -> `PG_Bordures` (Load PCG Data Asset -> Static Mesh Spawner : Mesh, Materiau, cd0..cd6) sur le volume `PJ_PCG_Bordures` (profil de collision BlockAll dans le descripteur du spawner) ; controle : instances = points, 10 instances tirees au hasard (position, rotation via M.R.M contre q, echelle, mesh, materiau, cd) |
| captures | `cameras.py`, `pj_tools.high_res_capture` | 6 poses de `recon/pc/houdini/cameras_v2_pilote.usda` (cap = atan2 de la visee -Z, site, roulis nul verifie, champ = 2 atan(ouverture / 2 focale)) -> `ue_<v>_1920x1080` (reference neutre, EV100 14) et `ue_<v>_1000` (vignettes des planches, exposition locale) (PNG + EXR) ; gros plans des joints `ue_joints_<joint>` (`cameras.pose_joint`) |
| planche | `planche.py` | `planche_karma_vs_ue.png` (Karma `recon/pc/rendus/v2_pilote` a gauche, UE a droite), `planche_joints_bordures.png` |

## Contexte du pilote dans UE (`contexte/`, `vegetation/`, niveau `/Game/PJ/Maps/PJ_2026`)
```
python recon/pcg/ue/contexte/contexte.py tout    # editeur ouvert (~15 min) ; ou : usd | materiaux | imports | arbres |
                                                 #   herbe | clotures | mobilier | feuilles | perf [vues] | captures [vues] |
                                                 #   panoramax | planches | inventaire
```
Entrees : paquet v1 (lecture seule), masque `fabrique_ue_snapshot/contexte/masque_v1_pilote.usdc`, sol v2 et points des
bordures de l'instantane, `data/context` (cadastre Etalab, arbres de la Metropole), photos Panoramax. Sorties :
`ue_pilote/usd/` (USD et Z, ignore par git), `ue_pilote/points/{arbres,tuteurs,arbres_lointains,clotures,mobilier}_ue.json`,
`ue_pilote/contexte_*.json`, captures `ctx_<vue>_{1920x1080,1000}` et `ctx_pano_*`, planches `planche_contexte_*.png`,
`planche_panoramax_<id>.png`.

| Etape | Script | Effet |
|---|---|---|
| usd | `contexte/lointain.py` (pyproj), `contexte/preparer_usd.py` + `lointain_usd.py` (hython) | `contexte_v1.usdc` : sol v1 (terrain + voirie, masque du pilote : faces retirees, raccords, Z fondu) en tuiles de 50 m, un Mesh par `materiau_id` (classe v1 affinee par le revetement de `surfaces_2026.geojson` : herbe, massif, terre, stabilise, beton, paves ; chaussee 2025 = enrobe neuf), bordures v1 (faces vues des deux cotes), marquages v1 (Z recale sur le sol fondu pres de l'emprise), batiments v1 par batiment (UV des murs en m : u le long du mur, v = hauteur ; st1 = (hauteur a l'egout, alea)) ; `lointain.usdc` : 835 batiments du cadastre hors du carre v1 (rayon 700 m, hauteurs a priori par l'aire) ; `zones_pcg.usdc` : maillages d'echantillonnage (couleur de sommet R = densite : 0 a moins de 0,15 m d'une surface dure ou d'une bordure v1 / v2, rampe jusqu'a 0,35 m) ; `z_objets.json` (sol rendu sous arbres, clotures, mobilier). Les trois couches passent `contrat/verifier_usd.py` (0 erreur) |
| materiaux | `contexte/ue/materiaux_contexte.py`, `pilote/ue/niveau_2026.py` | `M_PJ_Facade` (enduit CC0 + fenetres procedurales en HLSL : etages, cadres, appuis, embrasures, volets roulants, vitrines de rez-de-chaussee) et 6 MI ; `MI_bordure_v1` ; `MI_PJ_Contexte_Lointain` (plan de 3 km abaisse a z = -4,1 m sous la jupe du terrain v1) |
| relief | `contexte/horizon.py` (numpy), `contexte/relief_usd.py` (hython ; etape `usd`) | profil de l'horizon (site par degre d'azimut vrai) releve sur 60 photos 360 Panoramax (ligne de ciel par colonne : couleur du ciel ou plus sombre que 0,88 x le ciel au-dessus ; quantile 0,15 entre photos, median 5 deg ; planche de controle `ue_pilote/horizon/controle_profil.png`) ; `relief.usdc` : anneau de cretes de 3 a 35 km (secteur 200-352 deg depuis les photos : Vercors, Bastille, Rachais, Neron, Saint-Eynard ; 10-190 deg a priori de sommets : Chartreuse, Gresivaudan, Belledonne, Taillefer), 720 colonnes x 7 rangees, profil concave, ravines en bruit deterministe, normales lisses (`pj:cusp_deg` 180) ; sol lointain raccorde au bord du terrain v1 sur 25 m puis plan a `lointain.Z_PLAN` (-0,9 m, mediane du bord) jusqu'a 60 km ; `M_PJ_Relief` (foret d'octobre, alpages, falaises claires selon la pente ; perspective aerienne de SkyAtmosphere) |
| imports | `pj_tools.import_usd` (kinds_to_collapse 2, Nanite) | 130 SM (contexte v1) + 129 SM (lointain) + 13 SM (relief, sol lointain) + 5 zones (assets seuls), 0 avertissement LogStaticMesh ; collisions (`pilote/ue/collisions.py`) |
| arbres | `vegetation/arbres.py`, `correspondance_carla.json`, `catalogue_carla.json`, `contexte/ue/pg_points.py` | `PG_Arbres` (451 arbres + 45 tuteurs des jeunes sujets 2025) et `PG_Arbres_Lointains` (701 arbres publics, sans ombre portee) ; controle des hauteurs (96,7 % a 15 % pres) et des instances (position 0 mm, orientation 0 deg) |
| herbe | `contexte/ue/pg_herbe.py` | `PG_Herbe` : PCGMeshSampler (Poisson, densite = couleur de sommet) -> filtre -> transformation -> spawner pondere : gazon ras proche (r 19 cm) / lointain (r 30 cm), herbe haute, massifs (buissons CARLA), feuilles CARLA eparses ; ~75 000 instances, disparition a 30-50 m |
| clotures, mobilier | `contexte/clotures.py`, `contexte/mobilier.py`, `pg_points.py` | 459 panneaux SM_fence_09 le long des 51 lignes de cloture v1 ; 58 substituts CARLA (lampadaires, poteaux bois, potelets) aux positions v1. Feux, panneaux et abris : phase 5 (aucun volume provisoire v1 importe) |
| feuilles | `contexte/ue/feuilles.py` | `M_PJ_Feuilles_Decal` (DBuffer, ScatteredLeaves009) : 395 decalques au pied des feuillus, seuil de hauteur croissant du tronc vers le bord (feuilles eparses) ; arbres, buissons, clotures et mobilier ne recoivent pas les decalques |
| perf | `contexte/ue/perf.py` | PIE flottante, rendu interne 1920 x 1080 (r.ScreenPercentage), VSync coupe, 300 images apres 120 de chauffe + ProfileGPU (journal) |
| captures, panoramax, revue, planches | `contexte.py`, `contexte/panoramax.py`, `contexte/planches.py` | 6 vues pilote + 4 vues v1 (`recon/pc/houdini/cameras.usda`) ; poses Panoramax 360 du 18/05/2025 (lat/lon -> L93 par pyproj, MNT 2026 + 2,0 m, cap = azimut - 2,0086 deg, champ 90 deg) et recadrage gnomonique de la photo ; vues de revue a hauteur de pieton (`VUES_REVUE` -> `revue_<vue>`) ; `planches.py --avant DIR` : `planche_corrections_revue.png` (avant / apres) |

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

Nuages (`eclairage.NUAGES`, revue UE du 10/10) : VolumetricCloud du moteur, couche 1,5-4 km, `Cloud_GlobalCoverage` -0,15
(voiles ; 0,15 et 0,4 donnent une couche grise couvrante), vent nul (images reproductibles), pas d'ombre de nuage au sol.
Mie garde a 0,12 : rapport ombre/soleil mesure sur la chaussee de la vue a (EXR) : 0,215 a 0,12, 0,154 a 0,08, 0,123 a
0,06 (critere de t7 : [0,18 ; 0,32]) ; 0,217 apres l'ajout des nuages et du relief.
`eclairage.CVARS` : `r.EyeAdaptation.CachedLightingPreExposure` 14 (comme `DefaultEngine.ini`), applique par niveau_2026.py.
Exposition locale (`eclairage.EXPOSITION_LOCALE_PLANCHES`, contraste ombres 0,7 / hautes lumieres 0,8) pour les seules
vignettes 1000 des planches.

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
34 `MI_<materiau_id>` (+ 10 `__citysample`, 23 `__carla`, 10 peintures) sur 6 maitres `/Game/PJ/Materials/Maitres/M_PJ_{Sol,
Remplissage,Bordure,Peinture,Eclat,Touffe}`, albedo etalonne dans UE sur materiaux_sol.json, deplacement Nanite des remplissages,
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
`correctifs/carla_feuillage_automne.py` (revue UE du 10/10) : teinte d'automne par arbre (PerInstanceRandom) inseree avant
BaseColor dans `M_treeLeaves_master` (parametres `PJ_PartAutomne` 0,35, `PJ_AutomneBase` 0,25, `PJ_GainAutomne`) ; idempotent.
`correctifs/carla_arbres_nanite.py` : Nanite (preservation de l'aire) sur les 37 arbres et buissons poses (ARGS points :
arbres_ue.json, arbres_lointains_ue.json) : 63,2 i/s au pire (cam1) contre 59,3 sans, GPU 10,3-15,0 ms, ShadowDepths
toujours dominant (2,1-6,9 ms).
