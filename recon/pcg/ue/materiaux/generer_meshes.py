"""Maillages d'essai des matériaux (USDA conformes à CONTRAT_EXPORT.md, Python pur, déterministes).

    python recon/pcg/ue/materiaux/generer_meshes.py        -> recon/out/paquet_jardin/v2/ue_materiaux/usd/*.usda

- Plaques : dessus à z = 0, centrées sur l'origine, UV st = (x, y) en mètres depuis le coin bas-gauche ;
  pas de 5 cm pour les plaques d'essai et de remplissage (déplacement Nanite), 0,5 m pour les grandes plaques ;
  remplissage d'îlot bombé de 1,5 cm au centre (pourtour à z = 0).
- Bordure T2 (profil « pose_exemple » de assets/specs/bordures.json, vue 0,14 m : v = 0 au fil d'eau) en élément
  préfabriqué : pivot au pied de la face vue, au début de l'élément ; +X le long de l'élément, +Y vers l'arrière
  (trottoir, intérieur d'un îlot), Z haut. About « joint » : chanfrein de 3 mm (bordures_elements.json aretes) ;
  about « onglet » : coupe à 45° (angle saillant d'un îlot, face vue à l'extérieur).
  UV : u = x le long de l'élément, v = périmètre du profil (m) ; abouts : (y, z).
Normales par sommet de face (angle de rupture 30°), kinds assembly/group/component, matériau lié à
/World/Looks/<materiau_id> (UsdPreviewSurface + info:unreal:sourceAsset = /Game/PJ/Materials/MI_<id>).
"""
from __future__ import annotations

import json
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import catalogue as C  # noqa: E402

CUSP = 30.0
JOINT = 0.006
CHANFREIN = 0.003
SORTIE = f'{C.OUT}/usd'


# ------------------------------------------------------------------ géométrie
def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    n = math.sqrt(sum(x * x for x in a))
    return [x / n for x in a] if n > 0 else [0.0, 0.0, 1.0]


def normales_cusp(pts, faces, cusp=CUSP):
    nf = []
    for f in faces:
        n = [0.0, 0.0, 0.0]
        for i in range(1, len(f) - 1):
            c = _cross(_sub(pts[f[i]], pts[f[0]]), _sub(pts[f[i + 1]], pts[f[0]]))
            n = [n[k] + c[k] for k in range(3)]
        nf.append(n)
    autour = {}
    for k, f in enumerate(faces):
        for v in f:
            autour.setdefault(v, []).append(k)
    cmin = math.cos(math.radians(cusp))
    out = []
    for k, f in enumerate(faces):
        u = _norm(nf[k])
        for v in f:
            s = [0.0, 0.0, 0.0]
            for j in autour[v]:
                if sum(a * b for a, b in zip(_norm(nf[j]), u)) >= cmin:
                    s = [s[i] + nf[j][i] for i in range(3)]
            out.append(_norm(s))
    return out


def plaque(lx, ly, pas, bombement=0.0):
    """Plaque à z = 0 ; bombement (m) : dôme z = b (1 - (2x/lx)²)(1 - (2y/ly)²), nul sur le pourtour (raccord aux
    bordures), maximal au centre (remplissages d'îlots, materiaux_sol.json couche.bombement_m)."""
    nx, ny = max(1, round(lx / pas)), max(1, round(ly / pas))
    xs = [-lx / 2 + lx * i / nx for i in range(nx + 1)]
    ys = [-ly / 2 + ly * j / ny for j in range(ny + 1)]
    pts = [(x, y, bombement * (1 - (2 * x / lx) ** 2) * (1 - (2 * y / ly) ** 2)) for y in ys for x in xs]
    faces, uv = [], []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            f = [a, a + 1, a + nx + 2, a + nx + 1]
            faces.append(f)
            uv += [(pts[v][0] + lx / 2, pts[v][1] + ly / 2) for v in f]
    return pts, faces, uv


def profil_t2():
    b = json.load(open(C.SPEC_BORDURES, encoding='utf-8'))['profils']['T2']
    return [tuple(p) for p in b['pose_exemple']['contour_pose']]      # (u, v) : u = 0 face vue, v = 0 fil d'eau


def _aire(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def retrait(poly, d):
    """Contour convexe décalé de d vers l'intérieur (intersection des côtés décalés)."""
    s = 1.0 if _aire(poly) > 0 else -1.0             # trigo : intérieur à gauche
    n = len(poly)
    lignes = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty)
        nx, ny = -ty / L * s, tx / L * s                # normale intérieure
        lignes.append(((a[0] + nx * d, a[1] + ny * d), (tx, ty)))
    out = []
    for i in range(n):
        (p1, d1), (p2, d2) = lignes[i - 1], lignes[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-12:
            out.append(p2)
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + d1[0] * t, p1[1] + d1[1] * t))
    return out


def bordure(longueur, debut='joint', fin='joint'):
    """Élément de bordure T2 extrudé le long de +X (u -> +Y, v -> +Z)."""
    prof = profil_t2()
    if _aire(prof) > 0:                                  # anneau horaire vu de +X : quads (x croissant) sortants
        prof = prof[::-1]
    n = len(prof)
    inset = retrait(prof, CHANFREIN)
    perim = [0.0]
    for k in range(n):
        a, b = prof[k], prof[(k + 1) % n]
        perim.append(perim[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    # sections : (anneau (u, v), x(u))
    # sections : (anneau, x(u), décalage UV) ; la bande de chanfrein (largeur c·√2) garde des UV en mètres
    c2 = CHANFREIN * (math.sqrt(2.0) - 1.0)
    secs = []
    if debut == 'joint':
        secs += [(inset, lambda u: 0.0, -c2), (prof, lambda u: CHANFREIN, 0.0)]
    else:                                                # onglet : x = u (face vue la plus longue)
        secs += [(prof, lambda u: u, 0.0)]
    if fin == 'joint':
        secs += [(prof, lambda u: longueur - CHANFREIN, 0.0), (inset, lambda u: longueur, c2)]
    else:
        secs += [(prof, lambda u, L=longueur: L - u, 0.0)]
    pts, du = [], []
    for anneau, fx, d in secs:
        pts += [(fx(u), u, v) for u, v in anneau]
        du += [d] * len(anneau)
    faces, uv = [], []
    for s in range(len(secs) - 1):
        a0, a1 = s * n, (s + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            f = [a0 + k, a1 + k, a1 + k2, a0 + k2]
            faces.append(f)
            uv += [(pts[a0 + k][0] + du[a0 + k], perim[k]), (pts[a1 + k][0] + du[a1 + k], perim[k]),
                   (pts[a1 + k2][0] + du[a1 + k2], perim[k + 1]), (pts[a0 + k2][0] + du[a0 + k2], perim[k + 1])]
    f0 = [k for k in range(n)]                            # about de début (normale -X)
    f1 = [(len(secs) - 1) * n + k for k in reversed(range(n))]   # about de fin (+X)
    for f in (f0, f1):
        faces.append(f)
        uv += [(pts[v][1], pts[v][2]) for v in f]
    return pts, faces, uv


def verifier_orientation(pts, faces):
    """Somme des volumes signés > 0 (normales sortantes)."""
    vol = 0.0
    for f in faces:
        for i in range(1, len(f) - 1):
            a, b, c = pts[f[0]], pts[f[i]], pts[f[i + 1]]
            vol += sum(a[k] * _cross(b, c)[k] for k in range(3)) / 6.0
    return vol


# ------------------------------------------------------------------ écriture USDA
def _f(x):
    return f'{x:.6f}'.rstrip('0').rstrip('.') if abs(x) > 1e-12 else '0'


def ecrire(chemin, nom, pts, faces, uv, materiau_id, doc):
    nrm = normales_cusp(pts, faces)
    xs, ys, zs = zip(*pts)
    L = ['#usda 1.0', '(', '    defaultPrim = "World"', '    metersPerUnit = 1', '    upAxis = "Z"',
         '    customLayerData = {', '        string "pj:contrat" = "pj_usd/0.1"', f'        double "pj:cusp_deg" = {CUSP:g}', '    }',
         f'    doc = "{doc}"', ')', '', 'def Xform "World" (', '    kind = "assembly"', ')', '{',
         '    def Scope "Looks"', '    {', f'        def Material "{materiau_id}"', '        {',
         f'            token outputs:surface.connect = </World/Looks/{materiau_id}/Apercu.outputs:surface>',
         f'            token outputs:unreal:surface.connect = </World/Looks/{materiau_id}/Unreal.outputs:out>',
         '            def Shader "Apercu"', '            {', '                uniform token info:id = "UsdPreviewSurface"',
         '                color3f inputs:diffuseColor = (0.3, 0.3, 0.3)', '                float inputs:roughness = 0.85',
         '                token outputs:surface', '            }',
         '            def Shader "Unreal"', '            {', '                uniform token info:implementationSource = "sourceAsset"',
         f'                uniform asset info:unreal:sourceAsset = @{C.UE_MAT}/MI_{materiau_id}.MI_{materiau_id}@',
         '                token outputs:out', '            }', '        }', '    }',
         '    def Xform "Essai" (', '        kind = "group"', '    )', '    {',
         f'        def Xform "{nom}" (', '            kind = "component"', '        )', '        {',
         '            def Mesh "geo" (', '                prepend apiSchemas = ["MaterialBindingAPI"]', '            )', '            {',
         '                uniform token subdivisionScheme = "none"', '                uniform bool doubleSided = 0',
         '                uniform token orientation = "rightHanded"',
         f'                float3[] extent = [({_f(min(xs))}, {_f(min(ys))}, {_f(min(zs))}), ({_f(max(xs))}, {_f(max(ys))}, {_f(max(zs))})]',
         '                int[] faceVertexCounts = [' + ', '.join(str(len(f)) for f in faces) + ']',
         '                int[] faceVertexIndices = [' + ', '.join(str(v) for f in faces for v in f) + ']',
         '                point3f[] points = [' + ', '.join(f'({_f(p[0])}, {_f(p[1])}, {_f(p[2])})' for p in pts) + ']',
         '                normal3f[] normals = [' + ', '.join(f'({_f(n[0])}, {_f(n[1])}, {_f(n[2])})' for n in nrm) + '] (',
         '                    interpolation = "faceVarying"', '                )',
         '                texCoord2f[] primvars:st = [' + ', '.join(f'({_f(a)}, {_f(b)})' for a, b in uv) + '] (',
         '                    interpolation = "faceVarying"', '                )',
         f'                rel material:binding = </World/Looks/{materiau_id}>', '            }', '        }', '    }', '}', '']
    with open(chemin, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L))
    return {'fichier': chemin, 'composant': nom, 'faces': len(faces), 'points': len(pts),
            'boite': [[min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]]}


PLAQUES = {   # nom -> (lx, ly, pas, materiau_id de liaison, bombement m)
    'PJ_Plaque_2x2': (2.0, 2.0, 0.05, 'enrobe_bbsg_ancien', 0.0),
    'PJ_Plaque_Chaussee_7x3': (7.0, 3.0, 0.25, 'enrobe_bbsg_ancien', 0.0),
    'PJ_Plaque_Trottoir_6x2': (6.0, 2.0, 0.25, 'enrobe_trottoir', 0.0),
    'PJ_Plaque_Ilot_2p72x1p72': (2.72, 1.72, 0.05, 'brf_bois_concasse', 0.015),     # bombée de 1,5 cm
    'PJ_Plaque_Sol_16x12': (16.0, 12.0, 1.0, 'enrobe_bbsg_ancien', 0.0),
}
BORDURES_PROTO = {   # nom -> (longueur, debut, fin)
    'PJ_Bordure_T2_L994_Droit': (0.994, 'joint', 'joint'),
    'PJ_Bordure_T2_L993_OngletDebut': (0.993, 'onglet', 'joint'),
    'PJ_Bordure_T2_L993_OngletFin': (0.993, 'joint', 'onglet'),
}


def main():
    os.makedirs(SORTIE, exist_ok=True)
    rap = {}
    for nom, (lx, ly, pas, mid, b) in PLAQUES.items():
        pts, faces, uv = plaque(lx, ly, pas, b)
        rap[nom] = ecrire(f'{SORTIE}/{nom}.usda', nom, pts, faces, uv, mid,
                          f'Plaque d essai {lx} x {ly} m, pas {pas} m, bombement {b} m, UV st en metres (generer_meshes.py)')
    for nom, (L, d, f) in BORDURES_PROTO.items():
        pts, faces, uv = bordure(L, d, f)
        vol = verifier_orientation(pts, faces)
        assert vol > 0, f'{nom} : volume signe {vol} (normales rentrantes)'
        rap[nom] = ecrire(f'{SORTIE}/{nom}.usda', nom, pts, faces, uv, 'beton_bordure_gris',
                          f'Element de bordure T2 {L} m, abouts {d}/{f}, vue 0,14 m (generer_meshes.py)')
        rap[nom]['volume_m3'] = round(vol, 6)
    json.dump(rap, open(f'{SORTIE}/meshes.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    for k, v in rap.items():
        print(k, v['faces'], v['points'], v.get('volume_m3', ''))


if __name__ == '__main__':
    main()
