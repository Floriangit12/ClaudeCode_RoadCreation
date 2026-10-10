# Mesure de la tete de la fleche de rabattement (IISR annexe B1) sur l'image native
import sys, math
import numpy as np
from PIL import Image
im = np.asarray(Image.open(sys.argv[1]).convert('L')).astype(int)
dark = im < 110
H, W = im.shape
# axe vertical (tirets) : colonne la plus sombre sur toute la hauteur dans 330..370
colsum = dark[:, 330:370].sum(0); AX = 330 + int(np.argmax(colsum))
print('axe px', AX, 'somme', colsum.max())
# base : ligne horizontale du pied de tige (x 280..324)
base = [y for y in range(1200, H) if dark[y, 282:322].sum() > 30]
tip = [y for y in range(60, 300) if dark[y, 420:470].any()]
print('lignes base', base[:5], base[-3:], 'pointe', tip[:3])
def runs(row, xmin=200, xmax=520, excl=(AX-2, AX+2)):
    xs = [x for x in range(xmin, xmax) if dark[row, x] and not (excl[0] <= x <= excl[1])]
    out = []
    for x in xs:
        if out and x == out[-1][1] + 1: out[-1][1] = x
        else: out.append([x, x])
    return [(a + b) / 2 for a, b in out]
yb = np.mean(base[:3]) if base else None
# bord du trait : centre du trait de contour du pied
yb = float(min(base) + (max(base[:4]) - min(base)) / 2) if base else None
yt = float(tip[0] + 1.0)
s = (yb - yt) / 6.0
print('yb %.1f yt %.1f echelle %.2f px/m ; controle largeur pied' % (yb, yt, s))
r = int(round(yb - 0.3 * s)); rr = runs(r); print('  pied y=0.3 :', [(round((x - AX) / s, 3)) for x in rr])
def row(ym): return int(round(yb - ym * s))
def fit(ys_m, pick):
    P = []
    for ym in ys_m:
        rr = runs(row(ym))
        if not rr: continue
        x = pick(rr)
        if x is None: continue
        P.append(((x - AX) / s, ym))
    P = np.array(P)
    A = np.c_[P[:, 1], np.ones(len(P))]
    (a, b), res, *_ = np.linalg.lstsq(A, P[:, 0], rcond=None)
    rms = np.sqrt(np.mean((A @ [a, b] - P[:, 0]) ** 2))
    return a, b, rms, len(P)
def inter(l1, l2):  # x = a y + b
    a1, b1 = l1[:2]; a2, b2 = l2[:2]
    y = (b2 - b1) / (a1 - a2); return a1 * y + b1, y
E1 = fit(np.linspace(4.7, 5.8, 23), lambda rr: rr[0])
E4 = fit(np.linspace(3.65, 5.8, 40), lambda rr: rr[-1])
E2 = fit(np.linspace(4.18, 4.44, 8), lambda rr: rr[0])
E3 = fit(np.linspace(3.58, 3.86, 8), lambda rr: rr[-2] if len(rr) >= 2 else None)
for n, e in [('E1 pointe-barbe G', E1), ('E4 pointe-barbe D', E4), ('E2 barbe G-cassure', E2), ('E3 barbe D-encoche', E3)]:
    print('%-20s x = %.4f y + %.4f  rms %.4f m  n=%d' % (n, *e))
print('pointe      ', np.round(inter(E1, E4), 3))
print('barbe gauche', np.round(inter(E1, E2), 3))
print('barbe droite', np.round(inter(E3, E4), 3))
# bords de tige
L = []; R = []
for ym in np.arange(0.05, 3.9, 0.05):
    rr = runs(row(ym), 230, 400)
    if len(rr) >= 2:
        L.append((ym, (rr[0] - AX) / s)); R.append((ym, (rr[1] - AX) / s))
L = np.array(L); R = np.array(R)
def arcA(y, x0, Rr, yt):   # tangente verticale en yt, x(0)=x0
    xm = x0 - (Rr - math.sqrt(Rr * Rr - yt * yt)); return xm + Rr - np.sqrt(Rr * Rr - (y - yt) ** 2)
def arcB(y, x0, Rr, yt):   # verticale jusqu'a yt puis arc
    return np.where(y <= yt, x0, x0 + Rr - np.sqrt(Rr * Rr - (np.maximum(y, yt) - yt) ** 2))
for nm, E, x0, Rr, ytg in [('gauche', L, -0.36, 18.38, 0.72), ('droit', R, -0.11, 21.0, 1.155)]:
    for lab, f in [('A tangente', arcA), ('B vertical+arc', arcB)]:
        e = E[:, 1] - f(E[:, 0], x0, Rr, ytg)
        print('bord %s %s : rms %.4f max %.4f' % (nm, lab, np.sqrt(np.mean(e ** 2)), np.abs(e).max()))
for ym in [0.2, 1.0, 2.0, 3.0, 3.5, 3.8]:
    i = np.argmin(abs(L[:, 0] - ym)); print('  y=%.2f mesure G %.3f D %.3f' % (ym, L[i, 1], R[i, 1]))
# encoche et cassure : intersection avec les arcs (B gauche, A droite)
def solve(line, f, lo, hi):
    a, b = line[:2]
    for _ in range(60):
        m = (lo + hi) / 2
        g = lambda y: (a * y + b) - f(np.array(y))
        if np.sign(g(lo)) == np.sign(g(m)): lo = m
        else: hi = m
    return float(a * m + b), m
print('cassure (E2 x bord G arc B)', np.round(solve(E2, lambda y: arcB(y, -0.36, 18.38, 0.72), 3.9, 4.5), 3))
print('encoche (E3 x bord D arc A)', np.round(solve(E3, lambda y: arcA(y, -0.11, 21.0, 1.155), 3.5, 4.1), 3))
