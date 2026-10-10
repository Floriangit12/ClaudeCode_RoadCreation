"""Toolset MCP 'pj_tools' de l'editeur UE 5.8 (projet D:/ClaudeADAS).

Publie automatiquement par le plugin ModelContextProtocol via ToolsetRegistry.
Chaque outil renvoie une chaine JSON {"ok": bool, ...} ; en cas d'echec {"ok": false, "erreur", "trace"}.
Positions d'entree en metres du repere LOCAL de la scene (voir repere.py).
"""
import contextlib
import inspect
import io
import json
import os
import time
import traceback

import unreal
import toolset_registry

from pj_tools import repere

EXT_IMAGES = ('.png', '.jpg', '.jpeg', '.tga', '.exr', '.hdr', '.tif', '.tiff', '.bmp', '.psd')
NIVEAU_POUBELLE = '/Game/PJ/Essais/Poubelle/Niveau_SansTitre'   # niveau sans titre abandonne (ecrase)


# ---------------------------------------------------------------- utilitaires
def _ok(**kw) -> str:
    kw = {'ok': True, **kw}
    return json.dumps(kw, ensure_ascii=False, default=str)


def _err(e: BaseException) -> str:
    return json.dumps({'ok': False, 'erreur': f'{type(e).__name__}: {e}',
                       'trace': traceback.format_exc()[-4000:]}, ensure_ascii=False)


def _robuste(f):
    """Toute exception devient un texte d'erreur JSON (l'outil ne leve jamais)."""
    def g(*a, **k):
        try:
            return f(*a, **k)
        except BaseException as e:  # noqa: BLE001
            return _err(e)
    g.__name__ = f.__name__
    g.__qualname__ = f.__qualname__
    g.__doc__ = f.__doc__
    g.__annotations__ = f.__annotations__
    g.__signature__ = inspect.signature(f, eval_str=True)
    return g


def _monde():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _acteurs():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _niveaux():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def _set(obj, **props):
    """set_editor_property tolerant : renvoie la liste des proprietes refusees."""
    refus = []
    for k, v in props.items():
        try:
            obj.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001
            refus.append(f'{k}: {e}')
    return refus


def _vec_ue(x_m: float, y_m: float, z_m: float) -> unreal.Vector:
    X, Y, Z = repere.local_vers_ue(x_m, y_m, z_m)
    return unreal.Vector(X, Y, Z)


def _trouver_acteur(label: str):
    for a in _acteurs().get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def _preparer_changement_niveau(abandonner_sans_titre: bool):
    """Evite toute boite de dialogue modale avant load/new level.

    Enregistre les niveaux modifies qui ont un chemin ; un niveau sans titre modifie (/Temp/...)
    provoque une erreur, sauf si abandonner_sans_titre : il est alors enregistre dans la poubelle
    NIVEAU_POUBELLE (UPackage::SetDirtyFlag n'est pas expose a Python en 5.8 ; sans cela, le
    changement de niveau ouvrirait une boite de dialogue modale).
    """
    L = unreal.EditorLoadingAndSavingUtils
    sales = list(L.get_dirty_map_packages())
    titres = [p for p in sales if not p.get_name().startswith('/Temp/')]
    sans_titre = [p for p in sales if p.get_name().startswith('/Temp/')]
    if sans_titre and not abandonner_sans_titre:
        raise RuntimeError('niveau sans titre modifie : appeler avec discard_untitled=True '
                           'ou enregistrer le niveau (new_level) avant de changer')
    if sans_titre:
        L.save_map(_monde(), NIVEAU_POUBELLE)
    if titres:
        L.save_packages(titres, True)
    return [p.get_name() for p in titres]


def _taches_import(taches):
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(taches)
    out = []
    for t in taches:
        try:
            out.extend(str(p) for p in t.get_editor_property('imported_object_paths'))
        except Exception:  # noqa: BLE001
            pass
    return out


def _journal_fichier() -> str:
    nom = os.path.splitext(os.path.basename(unreal.Paths.get_project_file_path()))[0]
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir()), f'{nom}.log')


def _journal_position() -> int:
    unreal.SystemLibrary.execute_console_command(_monde(), 'FlushLog')
    try:
        return os.path.getsize(_journal_fichier())
    except OSError:
        return 0


def _journal_depuis(pos: int, categories, max_lignes: int = 200) -> dict:
    """Lignes Warning/Error des categories donnees ecrites dans le journal de l'editeur depuis 'pos'."""
    unreal.SystemLibrary.execute_console_command(_monde(), 'FlushLog')
    time.sleep(0.2)
    try:
        with open(_journal_fichier(), 'rb') as f:
            f.seek(pos)
            txt = f.read().decode('utf-8', 'replace')
    except OSError as e:
        return {'erreur': str(e)}
    out = {}
    for ligne in txt.splitlines():
        for cat in categories:
            if f'{cat}: Warning' in ligne or f'{cat}: Error' in ligne:
                out.setdefault(cat, []).append(ligne.split(']', 2)[-1].strip()[:400])
    return {k: v[:max_lignes] for k, v in out.items()}


class _Tee(io.TextIOBase):
    def __init__(self, *flux):
        self.flux = flux

    def write(self, s):
        for f in self.flux:
            try:
                f.write(s)
            except Exception:  # noqa: BLE001
                pass
        return len(s)

    def flush(self):
        for f in self.flux:
            try:
                f.flush()
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------- toolset
@unreal.uclass()
class pj_tools(unreal.ToolsetDefinition):  # noqa: N801 (nom public du toolset)
    """Outils du projet Paquet Jardin : execution Python, imports USD/textures, pose d'assets
    en coordonnees locales de la scene, niveaux, sauvegarde, capture d'images et inventaire."""

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def run_python_file(path: str, args_json: str | None = None) -> str:
        """Execute un fichier .py dans le Python de l'editeur (porte de sortie generale).

        Args:
            path: chemin absolu du fichier .py.
            args_json: chaine JSON optionnelle (dict), exposee au script dans la variable globale ARGS.

        Returns:
            JSON {ok, stdout, resultat} ; 'resultat' = variable globale RESULT du script si definie.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        src = open(path, encoding='utf-8-sig').read()
        g = {'__name__': '__main__', '__file__': path, 'unreal': unreal,
             'ARGS': json.loads(args_json) if args_json else {}}
        buf = io.StringIO()
        t0 = time.time()
        import sys
        tee_out, tee_err = _Tee(buf, sys.stdout), _Tee(buf, sys.stderr)
        try:
            with contextlib.redirect_stdout(tee_out), contextlib.redirect_stderr(tee_err):
                exec(compile(src, path, 'exec'), g)
        except BaseException as e:  # noqa: BLE001
            return json.dumps({'ok': False, 'erreur': f'{type(e).__name__}: {e}',
                               'stdout': buf.getvalue()[-20000:],
                               'trace': traceback.format_exc()[-4000:]}, ensure_ascii=False)
        return _ok(stdout=buf.getvalue()[-20000:], resultat=g.get('RESULT'),
                   duree_s=round(time.time() - t0, 2))

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def import_usd(usd_path: str, dest_path: str, render_context: str | None = None,
                   collapse: bool = False, kinds_to_collapse: int | None = None,
                   use_prim_kinds_for_collapsing: bool | None = None, uv_pleine_precision: bool = True,
                   nanite: bool = False) -> str:
        """Importe un fichier USD (.usd/.usda/.usdc) : assets dans dest_path, acteurs dans le niveau courant.

        Le repere USD (metres, Z haut, direct) est converti par l'importeur UE (cm, Y inverse),
        ce qui correspond exactement a la convention du projet. Toutes les options utiles sont fixees
        explicitement (les options d'import USD d'UE sont memorisees d'une session a l'autre).
        Contrat Houdini -> UE et critere d'acceptation : recon/pcg/ue/CONTRAT_EXPORT.md (0 avertissement
        LogStaticMesh pendant l'import, renvoye dans 'acceptation').

        Args:
            usd_path: chemin disque du fichier USD.
            dest_path: dossier de contenu cible, ex. /Game/PJ/Import/Sol.
            render_context: contexte de rendu des materiaux ('unreal' par defaut : un materiau USD dote de
                outputs:unreal:surface -> info:unreal:sourceAsset est remplace par ce materiau UE ; sinon
                repli sur UsdPreviewSurface ; 'universal' pour ignorer le remappage).
            collapse: raccourci : fusionner les prims de kind component et subcomponent (kinds_to_collapse=18) ;
                faux par defaut (kinds_to_collapse=0 : un StaticMesh par Mesh USD).
            kinds_to_collapse: masque EUsdDefaultKind (model 1, component 2, group 4, assembly 8,
                subcomponent 16) des prims dont le sous-arbre devient UN asset ; prioritaire sur collapse.
            use_prim_kinds_for_collapsing: utiliser kinds_to_collapse (vrai par defaut) ; faux = aucune fusion.
            uv_pleine_precision: UV en flottants 32 bits (vrai par defaut) : indispensable avec des UV en
                metres (en demi-flottant, pas de 0,125 m au-dela de 128 m).
            nanite: activer Nanite sur les StaticMesh importes (faux par defaut) ; requis pour le deplacement
                (tessellation Nanite) des materiaux de remplissage M_PJ_Remplissage (ilots BRF, gravier).

        Returns:
            JSON {ok, nb, objets, meshes [reglages de build, nb UV, sommets, materiaux], options effectives,
            journal (LogStaticMesh / LogUsd : avertissements et erreurs), acceptation, duree_s}.
        """
        if not os.path.isfile(usd_path):
            raise FileNotFoundError(usd_path)
        kinds = int(kinds_to_collapse) if kinds_to_collapse is not None else (18 if collapse else 0)
        upk = True if use_prim_kinds_for_collapsing is None else bool(use_prim_kinds_for_collapsing)
        opts = unreal.UsdStageImportOptions()
        refus = _set(opts, import_actors=True, import_geometry=True, import_materials=True,
                     import_skeletal_animations=False, import_level_sequences=False,
                     import_groom_assets=False, import_sounds=False, import_sparse_volume_textures=False,
                     prims_to_import=['/'], purposes_to_import=7, material_purpose='preview',
                     render_context_to_import=render_context or 'unreal',
                     use_prim_kinds_for_collapsing=upk, kinds_to_collapse=kinds,
                     merge_identical_material_slots=True, share_assets_for_identical_prims=True,
                     override_stage_options=False, prim_path_folder_structure=False,
                     existing_actor_policy=unreal.ReplaceActorPolicy.REPLACE,
                     existing_asset_policy=unreal.ReplaceAssetPolicy.REPLACE)
        t = unreal.AssetImportTask()
        _set(t, filename=usd_path, destination_path=dest_path, automated=True,
             replace_existing=True, save=True, options=opts)
        t0 = time.time()
        pos = _journal_position()
        objs = _taches_import([t])
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        meshes = []
        for p in objs:
            sm = unreal.load_asset(p)
            if not isinstance(sm, unreal.StaticMesh):
                continue
            bs = sub.get_lod_build_settings(sm, 0)
            if uv_pleine_precision and not bs.get_editor_property('use_full_precision_u_vs'):
                bs.set_editor_property('use_full_precision_u_vs', True)
                sub.set_lod_build_settings(sm, 0, bs)               # reconstruit le mesh
                unreal.EditorAssetLibrary.save_loaded_asset(sm, False)
            if nanite:
                ns = sm.get_editor_property('nanite_settings')
                if not ns.get_editor_property('enabled'):
                    ns.set_editor_property('enabled', True)
                    sm.set_editor_property('nanite_settings', ns)
                    unreal.EditorAssetLibrary.save_loaded_asset(sm, False)
            meshes.append({'mesh': p, 'sommets': sub.get_number_verts(sm, 0), 'uv': sub.get_num_uv_channels(sm, 0),
                           'nanite': bool(sm.get_editor_property('nanite_settings').get_editor_property('enabled')),
                           **{k: bool(bs.get_editor_property(k)) for k in (
                               'recompute_normals', 'recompute_tangents', 'use_full_precision_u_vs', 'use_mikk_t_space')},
                           'materiaux': [m.material_interface.get_path_name() if m.material_interface else None
                                         for m in sm.get_editor_property('static_materials')]})
        try:
            unreal.AutomationLibrary.finish_loading_before_screenshot()   # fin des constructions asynchrones
        except Exception as e:  # noqa: BLE001
            refus.append(f'finish_loading_before_screenshot: {e}')
        journal = _journal_depuis(pos, ('LogStaticMesh', 'LogUsd', 'LogUsdStage', 'LogMeshDescription'))
        eff = {}
        for n in dir(opts):                                 # options effectives (tracabilite)
            if n.startswith('_'):
                continue
            try:
                eff[n] = str(opts.get_editor_property(n))[:300]
            except Exception:  # noqa: BLE001
                pass
        n_sm = len(journal.get('LogStaticMesh', []))
        return _ok(nb=len(objs), objets=objs[:500], meshes=meshes[:500], options_refusees=refus, options=eff,
                   journal=journal, acceptation={'avertissements_logstaticmesh': n_sm, 'ok': n_sm == 0},
                   duree_s=round(time.time() - t0, 2))

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def import_textures(dir: str, dest_path: str) -> str:  # noqa: A002 (nom impose)
        """Importe toutes les images d'un dossier (non recursif) comme Texture2D.

        Heuristique par suffixe : normales (_n, _nrm, _normal, _normalgl : vert inverse si GL)
        en TC_NORMALMAP ; masques (_orm, _arm, _rough*, _ao, _metal*, _mask, _h, _height, _disp*)
        en lineaire (sRGB off).

        Args:
            dir: dossier disque contenant les images.
            dest_path: dossier de contenu cible, ex. /Game/PJ/Textures/Asphalte.

        Returns:
            JSON {ok, nb, textures}.
        """
        if not os.path.isdir(dir):
            raise NotADirectoryError(dir)
        fichiers = sorted(f for f in os.listdir(dir) if f.lower().endswith(EXT_IMAGES))
        taches = []
        for f in fichiers:
            t = unreal.AssetImportTask()
            _set(t, filename=os.path.join(dir, f), destination_path=dest_path, automated=True,
                 replace_existing=True, save=False)
            taches.append(t)
        objs = _taches_import(taches)
        regl = []
        for p in objs:
            tex = unreal.load_asset(p)
            if not isinstance(tex, unreal.Texture2D):
                continue
            n = tex.get_name().lower()
            fin = n.rsplit('_', 1)[-1] if '_' in n else ''
            if fin in ('n', 'nrm', 'normal', 'normalgl', 'nor', 'norgl', 'normaldx', 'nordx') or 'normal' in fin:
                _set(tex, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP, srgb=False,
                     flip_green_channel=('gl' in fin))
                regl.append((p, 'normale'))
            elif fin in ('orm', 'arm', 'rough', 'roughness', 'ao', 'ambientocclusion', 'metal', 'metallic',
                         'metalness', 'mask', 'h', 'height', 'disp', 'displacement', 'r', 'm'):
                _set(tex, compression_settings=(unreal.TextureCompressionSettings.TC_MASKS if fin in ('orm', 'arm', 'mask')
                                                else unreal.TextureCompressionSettings.TC_GRAYSCALE), srgb=False)
                regl.append((p, 'lineaire'))
            unreal.EditorAssetLibrary.save_loaded_asset(tex, only_if_is_dirty=False)
        return _ok(nb=len(objs), textures=objs, reglages=regl)

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def spawn_static_mesh(asset_path: str, x_m: float, y_m: float, z_m: float, yaw_deg: float,
                          label: str, scale: float = 1.0) -> str:
        """Pose un StaticMesh dans le niveau courant, en coordonnees LOCALES de la scene.

        Convention appliquee : X_ue = 100x, Y_ue = -100y, Z_ue = 100z (cm), yaw_ue = -yaw.
        Si un acteur porte deja ce label, il est deplace au lieu d'etre recree.

        Args:
            asset_path: chemin de l'asset, ex. /Game/Carla/Static/Vegetation/Trees/SM_Oak_M_v1.
            x_m: x local (m, vers l'est).
            y_m: y local (m, vers le nord).
            z_m: z local (m, altitude NGF - 216.30).
            yaw_deg: cap local en degres (sens trigo depuis +x).
            label: nom de l'acteur dans l'outliner.
            scale: echelle uniforme (1 par defaut).

        Returns:
            JSON {ok, acteur, ue_cm, yaw_ue}.
        """
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is None:
            raise ValueError(f'asset introuvable : {asset_path}')
        loc = _vec_ue(x_m, y_m, z_m)
        rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=repere.yaw_local_vers_ue(yaw_deg))
        a = _trouver_acteur(label) if label else None
        if a is None:
            a = _acteurs().spawn_actor_from_object(asset, loc, rot)
            if a is None:
                raise RuntimeError('spawn_actor_from_object a echoue')
            if label:
                a.set_actor_label(label)
        else:
            a.set_actor_location_and_rotation(loc, rot, False, False)
            if isinstance(a, unreal.StaticMeshActor) and isinstance(asset, unreal.StaticMesh):
                a.static_mesh_component.set_static_mesh(asset)
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        return _ok(acteur=a.get_path_name(), label=a.get_actor_label(),
                   ue_cm=[loc.x, loc.y, loc.z], yaw_ue=rot.yaw)

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def load_level(path: str, discard_untitled: bool = False) -> str:
        """Charge un niveau existant dans l'editeur (le niveau courant modifie est enregistre).

        Args:
            path: chemin du niveau, ex. /Game/PJ/Maps/PJ_2026.
            discard_untitled: abandonner les modifications d'un niveau sans titre au lieu d'echouer.

        Returns:
            JSON {ok, niveau, enregistres}.
        """
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            raise FileNotFoundError(f'niveau absent : {path}')
        sauves = _preparer_changement_niveau(discard_untitled)
        ok = _niveaux().load_level(path)
        return json.dumps({'ok': bool(ok), 'niveau': path, 'enregistres': sauves})

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def new_level(path: str, template: str | None = None, discard_untitled: bool = False) -> str:
        """Cree un niveau (enregistre a 'path') et l'ouvre.

        Args:
            path: chemin du nouveau niveau, ex. /Game/PJ/Maps/PJ_Test.
            template: niveau modele optionnel, ex. /Engine/Maps/Templates/Template_Default
                (ciel, soleil, brouillard) ; absent = niveau vierge.
            discard_untitled: abandonner les modifications d'un niveau sans titre au lieu d'echouer.

        Returns:
            JSON {ok, niveau}.
        """
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise FileExistsError(f'niveau deja present : {path} (utiliser load_level)')
        _preparer_changement_niveau(discard_untitled)
        if template:
            ok = _niveaux().new_level_from_template(path, template)
        else:
            ok = _niveaux().new_level(path)
        return json.dumps({'ok': bool(ok), 'niveau': path, 'template': template})

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def save_all() -> str:
        """Enregistre tous les paquets modifies (niveaux et contenu), sans boite de dialogue.

        Returns:
            JSON {ok, niveaux, contenus} (paquets qui etaient modifies).
        """
        L = unreal.EditorLoadingAndSavingUtils
        cartes = [p for p in L.get_dirty_map_packages() if not p.get_name().startswith('/Temp/')]
        sans_titre = [p.get_name() for p in L.get_dirty_map_packages() if p.get_name().startswith('/Temp/')]
        contenus = list(L.get_dirty_content_packages())
        res_c = L.save_packages(cartes, True) if cartes else True
        res_p = L.save_packages(contenus, True) if contenus else True
        return _ok(niveaux=[p.get_name() for p in cartes], niveaux_sans_titre_ignores=sans_titre,
                   contenus=[p.get_name() for p in contenus][:500], nb_contenus=len(contenus),
                   resultat=bool(res_c) and bool(res_p))

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def high_res_capture(out_png: str, cam_x_m: float, cam_y_m: float, cam_z_m: float,
                         yaw_deg: float, pitch_deg: float, fov_deg: float, width: int, height: int,
                         warmup: int = 32, ev100: float = -100.0, auto_mean_target: float = 118.0,
                         exr: bool = True) -> str:
        """Lance un rendu du niveau courant (SceneCapture2D, Lumen) vers un PNG 8 bits trame et un EXR.

        ASYNCHRONE : le rendu se fait sur de vraies images successives du moteur (Lumen et la SkyLight
        temps reel accumulent d'une image a l'autre) : 'warmup' images de chauffe puis l'image finale.
        Rappeler high_res_capture_etat(out_png) jusqu'a fini=true (une seule capture a la fois).
        Streaming de textures coupe pendant la capture (toutes les mips ; valeur restauree ensuite).
        Cible RGBA16F, source 'tone curve HDR' (post-process complet, lineaire) : EXR demi-flottant lineaire
        et PNG sRGB avec tramage triangulaire (pas de bandes). Exposition comme le viewport : manuelle
        EV100 (post-process AEM_MANUAL, biais -EV100, sans camera physique).

        Args:
            out_png: fichier PNG de sortie (chemin absolu) ; l'EXR a le meme nom en .exr.
            cam_x_m: x local de la camera (m).
            cam_y_m: y local de la camera (m).
            cam_z_m: z local de la camera (m).
            yaw_deg: cap local (deg, trigo depuis +x).
            pitch_deg: site (deg, positif vers le haut).
            fov_deg: champ horizontal (deg).
            width: largeur en pixels.
            height: hauteur en pixels.
            warmup: images moteur de chauffe avant l'image finale (32 par defaut).
            ev100: exposition manuelle EV100 ; -100 = automatique (dichotomie sur la moyenne sRGB, rendu
                reduit, EV renvoye) ; -200 = exposition des PostProcessVolumes du niveau (aucune surcharge).
            auto_mean_target: moyenne sRGB visee en mode auto (0-255, 118 = gris moyen).
            exr: ecrire aussi l'EXR (vrai par defaut).

        Returns:
            JSON {ok, en_cours, fini, png, exr, phase, images, ev100, ...} (etat initial).
        """
        from pj_tools import capture
        return _ok(**capture.lancer(out_png, cam_x_m, cam_y_m, cam_z_m, yaw_deg, pitch_deg, fov_deg,
                                    width, height, warmup, ev100, auto_mean_target, exr))

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def high_res_capture_etat(out_png: str) -> str:
        """Etat d'une capture lancee par high_res_capture (a rappeler jusqu'a fini=true).

        Args:
            out_png: le PNG passe a high_res_capture.

        Returns:
            JSON {ok, fini, en_cours, phase (auto|chauffe|export|fini|erreur), images, png, octets, exr,
            exr_octets, ev100, moyenne (sRGB 0-255), duree_s, erreur} ; ok=false si la capture a echoue.
        """
        from pj_tools import capture
        e = capture.etat(out_png)
        if e['phase'] == 'erreur':
            return json.dumps({'ok': False, **e}, ensure_ascii=False, default=str)
        return _ok(**e)

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def charger_points(json_path: str, asset_path: str, etat_seulement: bool = False) -> str:
        """Cuit un fichier de points pj_points/0.1 en PCGDataAsset (voie b du transport des points).

        Le graphe outil /Game/PJ/PCG/Outils/PG_Cuisson_Points (Python Data Processor -> Save PCG Data
        Asset) est execute par un volume PCG temporaire du niveau courant : la generation est asynchrone
        (quelques ticks) ; rappeler avec etat_seulement=True jusqu'a fini=true. L'asset produit porte
        un PCGPointData (transform UE, graine) avec les attributs Mesh (SoftObjectPath), Id, Graine (et cd0..cdN-1
        si les points portent des donnees d'instance cd) ;
        il se relit par le noeud natif 'Load PCG Data Asset'.

        Args:
            json_path: fichier pj_points/0.1 (chemin disque).
            asset_path: PCGDataAsset cible, ex. /Game/PJ/PCG/Donnees/PDA_Arbres.
            etat_seulement: ne rien lancer, renvoyer l'etat de la derniere cuisson de cet asset.

        Returns:
            JSON {ok, fini, asset_existe, nb_points, script}.
        """
        from pj_tools import charger_points as cp
        if etat_seulement:
            e = cp._cuissons.get(asset_path, (None, None, {}))[2]
            return _ok(**e, asset_existe=unreal.EditorAssetLibrary.does_asset_exist(asset_path))
        e = cp.lancer_cuisson(json_path, asset_path)
        return _ok(**e, asset_existe=unreal.EditorAssetLibrary.does_asset_exist(asset_path))

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def list_assets(path: str, recursive: bool = True, limit: int = 2000) -> str:
        """Liste les assets d'un dossier de contenu (Asset Registry).

        Args:
            path: dossier de contenu, ex. /Game/Carla/Static/Vegetation/Trees.
            recursive: inclure les sous-dossiers (vrai par defaut).
            limit: nombre maximal d'entrees renvoyees (2000 par defaut).

        Returns:
            JSON {ok, nb, assets: [[chemin, classe], ...], tronque}.
        """
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        donnees = reg.get_assets_by_path(path.rstrip('/'), recursive=recursive)
        out = []
        for a in donnees:
            try:
                cls = str(a.asset_class_path.asset_name)
            except Exception:  # noqa: BLE001
                cls = '?'
            out.append([f'{a.package_name}.{a.asset_name}', cls])
        out.sort()
        return _ok(nb=len(out), assets=out[:max(0, int(limit))], tronque=len(out) > int(limit))

    @toolset_registry.tool_call
    @staticmethod
    @_robuste
    def reload_pj_tools() -> str:
        """Recharge le code Python de pj_tools au tick suivant (apres mise a jour des sources).

        Returns:
            JSON {ok, message}.
        """
        def _recharger(_dt):
            unreal.unregister_slate_post_tick_callback(_h[0])
            try:
                import importlib
                import sys
                import pj_tools as _m
                for nom in sorted(sys.modules):     # sous-modules (repere, charger_points...) d'abord
                    if nom.startswith('pj_tools.') and nom != 'pj_tools.toolset':
                        importlib.reload(sys.modules[nom])
                toolset_registry.reload_module(_m)
                unreal.log('pj_tools: recharge')
            except Exception as e:  # noqa: BLE001
                unreal.log_error(f'pj_tools: echec du rechargement : {e}')
        _h = [None]
        _h[0] = unreal.register_slate_post_tick_callback(_recharger)
        return _ok(message='rechargement programme au prochain tick')
