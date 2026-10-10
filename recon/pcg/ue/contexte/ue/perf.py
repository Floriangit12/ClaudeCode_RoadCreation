"""[editeur] Mesure de performance de PJ_2026 en 1920 x 1080 (session PIE en fenetre flottante, pilotee par contexte.py).

Etapes (ARGS etape) :
- 'preparer'  : PIE en fenetre 1920 x 1080, VSync coupe, t.MaxFPS 0, editeur non bride en arriere-plan ;
- 'poser'     : (PIE lancee) camera CameraActor « PJ_Perf_Camera » du monde PIE a la pose (m locaux, cap, site, champ)
                et vue du joueur sur elle ;
- 'mesurer'   : enregistre un rappel post-tick qui ignore `chauffe` images puis cumule `n` intervalles d'image, et lance
                ProfileGPU apres la chauffe (arbre des temps GPU dans le journal) ; non bloquant ;
- 'etat'      : resultats du rappel (images, ms moyen, p50, p95, i/s) ;
- 'restaurer' : reglages d'origine.
L'etat est garde dans unreal.PJ_PERF (objet module) entre les appels run_python_file.
"""
import statistics
import time

import unreal
from pj_tools import repere

A = dict(etape='etat', pose=None, chauffe=90, n=240, marque='')
A.update(globals().get('ARGS') or {})
S = getattr(unreal, 'PJ_PERF', None)
if S is None:
    S = {}
    unreal.PJ_PERF = S
SL = unreal.SystemLibrary


def cvar(nom, val):
    SL.execute_console_command(None, f'{nom} {val}')


def monde_pie():
    try:
        return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    except Exception:  # noqa: BLE001
        return None


if A['etape'] == 'preparer':
    # proprietes non exposees a Python : commande « set » sur les objets par defaut (CDO)
    for cmd in ('set EditorPerformanceSettings bThrottleCPUWhenNotForeground 0',
                'set LevelEditorPlaySettings NewWindowWidth 1920', 'set LevelEditorPlaySettings NewWindowHeight 1080',
                'set LevelEditorPlaySettings CenterNewWindow 1'):
        SL.execute_console_command(None, cmd)
    cvar('r.VSync', 0)
    cvar('t.MaxFPS', 0)
    cvar('r.ScreenPercentage', 100)
    cvar('r.ProfileGPU.ShowUI', 0)                   # pas de fenetre GPU Visualizer a chaque ProfileGPU
    RESULT = {'ok': True}

elif A['etape'] == 'poser':
    w = monde_pie()
    if w is None:
        raise RuntimeError('pas de monde PIE')
    p = A['pose']
    X, Y, Z = repere.local_vers_ue(p['cam_x_m'], p['cam_y_m'], p['cam_z_m'])
    rot = unreal.Rotator(roll=0.0, pitch=p['pitch_deg'], yaw=repere.yaw_local_vers_ue(p['yaw_deg']))
    # pion du joueur (DefaultPawn, sans gravite) : oeil = position + BaseEyeHeight ; rotation de controle ; champ
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    pion = pc.get_controlled_pawn() if hasattr(pc, 'get_controlled_pawn') else pc.get_editor_property('pawn')
    oeil = pion.get_editor_property('base_eye_height') if pion else 0.0
    pion.set_actor_location(unreal.Vector(X, Y, Z - oeil), False, True)
    pc.set_control_rotation(rot)
    pc.player_camera_manager.set_editor_property('default_fov', float(p['fov_deg']))
    SL.execute_console_command(w, f"fov {float(p['fov_deg'])}")
    taille = unreal.WidgetLayoutLibrary.get_viewport_size(w)
    # rendu interne 1920 x 1080 : pourcentage d'ecran sur la fenetre PIE (sa taille n'est pas reglable par Python)
    sp = 100.0 * 1920.0 / max(taille.x, 1.0)
    SL.execute_console_command(w, f'r.ScreenPercentage {sp:.3f}')
    RESULT = {'ok': True, 'pion': pion.get_name(), 'oeil_cm': oeil, 'viewport': [taille.x, taille.y],
              'pourcentage_ecran': round(sp, 3), 'rendu_interne': [round(taille.x * sp / 100), round(taille.y * sp / 100)],
              'monde': w.get_name()}

elif A['etape'] == 'mesurer':
    S['marque'] = A.get('marque', '')
    S['mesure'] = {'dt': [], 'vus': 0, 'chauffe': int(A['chauffe']), 'n': int(A['n']), 'fini': False, 'gpu_lance': False,
                   't0': time.time()}

    def _tick(dt):
        m = S['mesure']
        m['vus'] += 1
        if m['vus'] == m['chauffe'] and not m['gpu_lance']:
            m['gpu_lance'] = True
            w = monde_pie()
            unreal.log(f"PJ_PERF_MARQUE {S.get('marque', '')}")
            SL.execute_console_command(w, 'ProfileGPU')
        if m['vus'] > m['chauffe'] + 2:
            m['dt'].append(dt)
        if len(m['dt']) >= m['n']:
            m['fini'] = True
            unreal.unregister_slate_post_tick_callback(S['h'])

    S['h'] = unreal.register_slate_post_tick_callback(_tick)
    RESULT = {'ok': True}

elif A['etape'] == 'etat':
    m = S.get('mesure') or {}
    dt = sorted(m.get('dt', []))
    r = {'fini': m.get('fini', False), 'images': len(dt), 'duree_s': round(time.time() - m.get('t0', time.time()), 1)}
    if dt:
        ms = [1000.0 * x for x in dt]
        r.update({'ms_moyen': round(statistics.mean(ms), 2), 'ms_p50': round(ms[len(ms) // 2], 2),
                  'ms_p95': round(ms[int(0.95 * (len(ms) - 1))], 2), 'ips_moyen': round(1000.0 / statistics.mean(ms), 1)})
    RESULT = r

elif A['etape'] == 'restaurer':
    SL.execute_console_command(None, 'set EditorPerformanceSettings bThrottleCPUWhenNotForeground 1')
    cvar('r.ScreenPercentage', 100)
    RESULT = {'ok': True}
