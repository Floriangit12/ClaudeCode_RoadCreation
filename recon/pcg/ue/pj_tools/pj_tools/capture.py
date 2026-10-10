"""Capture d'images correcte sous Lumen (editeur UE) : SceneCapture2D rendu sur de VRAIES images successives.

Lumen (cache de surface, sondes, filtres temporels) et la SkyLight temps reel (capture etalee sur plusieurs
images) n'accumulent rien si tous les rendus ont lieu dans un seul tick du thread de jeu : la capture est donc
asynchrone. lancer() pose la camera et enregistre un rappel post-tick Slate qui fait un capture_scene() par
image du moteur (et invalide les viewports pour que le rendu principal tourne aussi), 'chauffe' images
avant l'image finale ; etat() renvoie l'avancement puis le resultat.

Textures : streaming coupe pendant la capture (toutes les mips, voir _streaming_complet), cible reutilisee.
Chaine de couleur : cible RGBA16F, source SCS_FINAL_TONE_CURVE_HDR (post-process complet, courbe de ton du
tonemapper, lineaire, gamut sRGB) ; exposition manuelle EV100 par le post-process du composant (AEM_MANUAL,
biais = -EV100, sans camera physique), comme le PostProcessVolume du niveau. Sorties :
  - EXR demi-flottant (lineaire apres courbe de ton, export_render_target) ;
  - PNG 8 bits sRGB = OETF sRGB de ces valeurs + tramage TPDF (+-1 code), donc sans bandes.
EV100 : > -99 manuel ; -100 automatique (dichotomie sur la moyenne sRGB, rendu reduit) ; -200 = aucune
surcharge (exposition des PostProcessVolumes du niveau, exactement la chaine du viewport). Reference du projet :
eclairage.EV100 (14). Post-process neutre impose dans tous les cas (eclairage.POST_PROCESS_NEUTRE : ni vignettage,
ni grain, ni aberration chromatique), pour des luminances mesurables jusqu'aux bords.
"""
from __future__ import annotations

import math
import os
import random
import struct
import time
import traceback
import zlib

import unreal

from pj_tools import eclairage
from pj_tools import repere

CAPTURE_LABEL = 'PJ_Capture'
EV_AUTO = -100.0
EV_NIVEAU = -200.0
AUTO_LARGEUR = 320
AUTO_CHAUFFE = 12          # images avant la premiere mesure de la dichotomie
AUTO_PAS = 8               # pas de dichotomie (28 EV / 2^8 = 0,11 EV)
AUTO_IMAGES_PAR_PAS = 2
DUREE_MAX_S = 900.0
CHAUFFE_MIN_S = 2.0        # duree minimale avant l'image finale (chargement des mips, streaming coupe)

_jobs = {}                 # out_png -> etat (dict) ; un seul job actif a la fois
_lut = []


# ---------------------------------------------------------------- conversions
def _lut_srgb() -> list:
    """65536 entrees : lineaire i/65535 -> code sRGB 8 bits flottant (+0,5 pour l'arrondi par troncature)."""
    if not _lut:
        for i in range(65536):
            v = i / 65535.0
            e = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1.0 / 2.4) - 0.055
            _lut.append(e * 255.0 + 0.5)
    return _lut


def _bruit_tpdf(w: int, graine: int = 2154) -> list:
    """64 lignes de bruit triangulaire (-1..1 code) de longueur 3w (tuile 64x64 repetee)."""
    a = random.Random(graine)
    tuile = [[a.random() + a.random() - 1.0 for _ in range(64 * 3)] for _ in range(64)]
    reps = (w + 63) // 64
    return [(t * reps)[:3 * w] for t in tuile]


def _codes(px, w: int, h: int, tramage: bool = True):
    """Pixels LinearColor (lineaires) -> lignes d'octets RGB sRGB 8 bits, et moyenne des codes."""
    lut = _lut_srgb()
    bruit = _bruit_tpdf(w) if tramage else [[0.0] * (3 * w)] * 64
    lignes, somme = [], 0
    for y in range(h):
        flat = [v for c in px[y * w:(y + 1) * w] for v in (c.r, c.g, c.b)]
        q = [lut[0 if v <= 0.0 else (65535 if v >= 1.0 else int(v * 65535.0))] + n
             for v, n in zip(flat, bruit[y & 63])]
        b = bytes([0 if x < 0.0 else (255 if x >= 255.0 else int(x)) for x in q])
        somme += sum(b)
        lignes.append(b)
    return lignes, somme / (3.0 * w * h)


def _ecrire_png(chemin: str, w: int, h: int, lignes: list) -> int:
    def bloc(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    brut = b''.join(b'\x00' + l for l in lignes)
    data = (b'\x89PNG\r\n\x1a\n' + bloc(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + bloc(b'sRGB', b'\x00') + bloc(b'IDAT', zlib.compress(brut, 6)) + bloc(b'IEND', b''))
    tmp = chemin + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, chemin)
    return len(data)


# ---------------------------------------------------------------- scene
def _monde():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _invalider_viewports():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
    except Exception:  # noqa: BLE001
        pass


def _camera(x_m, y_m, z_m, yaw_deg, pitch_deg):
    act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    X, Y, Z = repere.local_vers_ue(x_m, y_m, z_m)
    loc = unreal.Vector(X, Y, Z)
    rot = unreal.Rotator(roll=0.0, pitch=float(pitch_deg), yaw=repere.yaw_local_vers_ue(float(yaw_deg)))
    cap = None
    for a in act.get_all_level_actors():
        if a.get_actor_label() == CAPTURE_LABEL:
            cap = a
    if cap is None or not isinstance(cap, unreal.SceneCapture2D):
        cap = act.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot)
        cap.set_actor_label(CAPTURE_LABEL)
    cap.set_actor_location_and_rotation(loc, rot, False, False)
    return cap, loc, rot


def _set(obj, **props):
    refus = []
    for k, v in props.items():
        try:
            obj.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001
            refus.append(f'{k}: {e}')
    return refus


_cibles = {}               # (monde, w, h) -> cible reutilisee (une cible par capture saturait la memoire : ~16 Mo chacune)


def _valide(obj) -> bool:
    """Objet UE encore vivant ; une cible detruite par le ramasse-miettes (niveau recharge sous le meme chemin)
    leve TypeError dans is_valid au lieu de renvoyer False."""
    try:
        return obj is not None and bool(unreal.SystemLibrary.is_valid(obj))
    except Exception:  # noqa: BLE001
        return False


def _rt(w, h):
    cle = (_monde().get_path_name(), int(w), int(h))
    rt = _cibles.get(cle)
    if not _valide(rt):
        rt = unreal.RenderingLibrary.create_render_target2d(
            _monde(), int(w), int(h), unreal.TextureRenderTargetFormat.RTF_RGBA16F,
            unreal.LinearColor(0, 0, 0, 1), False)
        _cibles[cle] = rt
    return rt


def _streaming_complet(actif: bool, precedent=None):
    """Textures a pleine resolution pendant la capture : le streaming de textures d'UE dimensionne les mips sur
    la camera du viewport de l'editeur, pas sur la SceneCapture (constat : remplissages a 64 px, image floue).
    r.TextureStreaming 0 charge toutes les mips en quelques secondes ; la valeur precedente est restauree."""
    if actif:
        precedent = unreal.SystemLibrary.get_console_variable_int_value('r.TextureStreaming')
        if precedent:
            unreal.SystemLibrary.execute_console_command(_monde(), 'r.TextureStreaming 0')
        return precedent
    if precedent:
        unreal.SystemLibrary.execute_console_command(_monde(), f'r.TextureStreaming {int(precedent)}')
    return None


# ---------------------------------------------------------------- job
def lancer(out_png: str, cam_x_m: float, cam_y_m: float, cam_z_m: float, yaw_deg: float, pitch_deg: float,
           fov_deg: float, width: int, height: int, warmup: int = 32, ev100: float = EV_AUTO,
           auto_mean_target: float = 118.0, exr: bool = True) -> dict:
    """Prepare la capture et l'enregistre sur le tick ; renvoie l'etat initial (asynchrone, voir etat())."""
    actifs = [k for k, e in _jobs.items() if e['phase'] not in ('fini', 'erreur')
              and time.time() - e['t0'] < DUREE_MAX_S]
    if actifs:
        raise RuntimeError(f'capture deja en cours : {actifs[0]} (attendre high_res_capture_etat)')
    out_png = os.path.abspath(out_png).replace('\\', '/')
    if not out_png.lower().endswith('.png'):
        raise ValueError('out_png doit finir par .png')
    t0 = time.time()
    cap, loc, rot = _camera(cam_x_m, cam_y_m, cam_z_m, yaw_deg, pitch_deg)
    comp = cap.get_editor_property('capture_component2d')
    refus = _set(comp, fov_angle=float(fov_deg),
                 capture_source=unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR,
                 capture_every_frame=False, capture_on_movement=False,
                 always_persist_rendering_state=True, use_ray_tracing_if_enabled=True,
                 exclude_from_scene_texture_extents=True)
    pp = comp.get_editor_property('post_process_settings')
    refus += _set(pp, override_dynamic_global_illumination_method=True,
                  dynamic_global_illumination_method=unreal.DynamicGlobalIlluminationMethod.LUMEN,
                  override_reflection_method=True, reflection_method=unreal.ReflectionMethod.LUMEN)
    refus += _set(pp, **eclairage.POST_PROCESS_NEUTRE)
    manuel = ev100 > EV_NIVEAU + 1.0
    refus += _set(pp, override_auto_exposure_method=manuel,
                  auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
                  override_auto_exposure_apply_physical_camera_exposure=manuel,
                  auto_exposure_apply_physical_camera_exposure=False,
                  override_auto_exposure_bias=manuel)
    streaming_precedent = _streaming_complet(True)
    try:
        unreal.AutomationLibrary.finish_loading_before_screenshot()   # shaders, champs de distance, streaming
    except Exception as e:  # noqa: BLE001
        refus.append(f'finish_loading_before_screenshot: {e}')
    etat = {'png': out_png, 'exr': (os.path.splitext(out_png)[0] + '.exr') if exr else None,
            'phase': 'auto' if abs(ev100 - EV_AUTO) < 1.0 else 'chauffe', 'images': 0, 'chauffe': max(1, int(warmup)),
            'ev100': None if not manuel else (12.0 if abs(ev100 - EV_AUTO) < 1.0 else float(ev100)),
            'exposition': 'auto' if abs(ev100 - EV_AUTO) < 1.0 else ('manuelle' if manuel else 'niveau'),
            'auto_cible': float(auto_mean_target), 'fov_deg': float(fov_deg), 'largeur': int(width),
            'hauteur': int(height), 'ue_cm': [loc.x, loc.y, loc.z], 'rot_ue': [rot.roll, rot.pitch, rot.yaw],
            't0': t0, 'reglages_refuses': refus, 'monde': _monde().get_path_name()}
    j = {'comp': comp, 'pp': pp, 'rt': None, 'lo': -8.0, 'hi': 20.0, 'pas': 0, 'n_phase': 0}

    def exposer(ev):
        if ev is not None:
            pp.set_editor_property('auto_exposure_bias', float(-ev))   # manuel sans camera physique : -EV100
        comp.set_editor_property('post_process_settings', pp)
        comp.set_editor_property('post_process_blend_weight', 1.0)

    def cible(w, h):
        j['rt'] = _rt(w, h)
        comp.set_editor_property('texture_target', j['rt'])
        j['n_phase'] = 0

    if etat['phase'] == 'auto':
        exposer(0.5 * (j['lo'] + j['hi']))
        cible(AUTO_LARGEUR, max(1, round(AUTO_LARGEUR * height / width)))
    else:
        exposer(etat['ev100'])
        cible(width, height)

    def finir(_erreur=None):
        try:
            unreal.unregister_slate_post_tick_callback(j['h'])
        except Exception:  # noqa: BLE001
            pass
        try:
            comp.set_editor_property('texture_target', None)
        except Exception:  # noqa: BLE001
            pass
        try:
            _streaming_complet(False, streaming_precedent)
        except Exception:  # noqa: BLE001
            pass
        etat['duree_s'] = round(time.time() - t0, 2)
        if _erreur:
            etat['phase'] = 'erreur'
            etat['erreur'] = _erreur

    def tick(_dt):
        try:
            if _monde().get_path_name() != etat['monde']:
                raise RuntimeError('le niveau a change pendant la capture')
            if time.time() - t0 > DUREE_MAX_S:
                raise TimeoutError(f'capture > {DUREE_MAX_S} s')
            _invalider_viewports()
            comp.capture_scene()                      # une image par tick moteur
            etat['images'] += 1
            j['n_phase'] += 1
            if etat['phase'] == 'auto':
                besoin = (AUTO_CHAUFFE if j['pas'] == 0 else 0) + AUTO_IMAGES_PAR_PAS
                if j['n_phase'] < besoin:
                    return
                px = unreal.RenderingLibrary.read_render_target_raw(_monde(), j['rt'])
                w = AUTO_LARGEUR
                _, moy = _codes(list(px), w, len(px) // w, tramage=False)
                mi = 0.5 * (j['lo'] + j['hi'])
                if moy > etat['auto_cible']:
                    j['lo'] = mi
                else:
                    j['hi'] = mi
                j['pas'] += 1
                j['n_phase'] = 0
                if j['pas'] >= AUTO_PAS:
                    etat['ev100'] = round(0.5 * (j['lo'] + j['hi']), 2)
                    etat['phase'] = 'chauffe'
                    exposer(etat['ev100'])
                    cible(etat['largeur'], etat['hauteur'])
                else:
                    exposer(0.5 * (j['lo'] + j['hi']))
                return
            if etat['phase'] == 'chauffe':
                if j['n_phase'] >= etat['chauffe'] and time.time() - t0 >= CHAUFFE_MIN_S:
                    etat['phase'] = 'export'          # l'image du prochain tick est l'image finale
                return
            # ---- image finale (rendue ci-dessus) : lecture, EXR, PNG
            monde = _monde()
            dossier, nom = os.path.split(etat['png'])
            os.makedirs(dossier, exist_ok=True)
            if etat['exr']:
                if os.path.exists(etat['exr']):
                    os.remove(etat['exr'])
                unreal.RenderingLibrary.export_render_target(monde, j['rt'], dossier, os.path.basename(etat['exr']))
                etat['exr_octets'] = os.path.getsize(etat['exr']) if os.path.exists(etat['exr']) else 0
            px = list(unreal.RenderingLibrary.read_render_target_raw(monde, j['rt']))
            w, h = etat['largeur'], etat['hauteur']
            if len(px) != w * h:
                raise RuntimeError(f'{len(px)} pixels lus pour {w}x{h}')
            t1 = time.time()
            lignes, moy = _codes(px, w, h)
            etat['octets'] = _ecrire_png(etat['png'], w, h, lignes)
            etat['conversion_s'] = round(time.time() - t1, 2)
            etat['moyenne'] = round(moy, 1)
            etat['phase'] = 'fini'
            finir()
        except BaseException as e:  # noqa: BLE001
            finir(f'{type(e).__name__}: {e} | {traceback.format_exc()[-1500:]}')

    _jobs[out_png] = etat
    j['h'] = unreal.register_slate_post_tick_callback(tick)
    etat['_job'] = j                                   # garde les references vivantes
    return publique(etat)


def publique(etat: dict) -> dict:
    e = {k: v for k, v in etat.items() if not k.startswith('_')}
    e['fini'] = etat['phase'] == 'fini'
    e['en_cours'] = etat['phase'] not in ('fini', 'erreur')
    if e['en_cours']:
        e['ecoule_s'] = round(time.time() - etat['t0'], 1)
    return e


def etat(out_png: str) -> dict:
    cle = os.path.abspath(out_png).replace('\\', '/')
    if cle not in _jobs:
        raise KeyError(f'aucune capture lancee pour {cle}')
    return publique(_jobs[cle])
