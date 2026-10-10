"""pj_bordure_pose : pose des éléments préfabriqués le long des bordures de la description.

Règles (assets/specs/bordures_elements.json ; revue conformité r2) :
- pas : le plus long de 1,00 / 0,50 dont la flèche de corde reste ≤ 10,5 mm, le coin de joint (base x
  déviation des tangentes) ≤ 6 mm et le coin vertical (H x changement de pente) ≤ 4 mm (R ≥ 25 m pour
  1,00 et R ≥ 12,5 m pour 0,50 avec une base de 0,15) ; sinon pièce courbe sur mesure (abouts radiaux,
  arc ≤ 1 m et ≤ quart de cercle) ; hystérésis à 60 % des seuils ;
- chaque file part d'un point dur (abaissé > angle vif > changement de profil > extrémité ; jamais
  d'une coupe de zone) avec des éléments entiers et finit par un élément de coupe (≥ 0,20 m, sinon
  deux coupes égales) ; longueur = pas − joint (0,994 pour 1,00 avec joint de 6 mm) ; une file
  multiple du pas à ±1 % (tolérance NF) est posée en éléments égaux, sans coupe ;
- chartière : un élément de raccord (loft du profil courant posé à sa vue vers le profil abaissé à
  0,02 m), qui suit la face (loft le long du chemin) sur une courbe ou un coude ; bateau : éléments du
  profil de l'intervalle à sa vue ;
- Z : dessous du bloc = fil d'eau au milieu de la corde + vue − H ; tangage = pente du fil d'eau sur la
  corde ; jitter ±2 mm (dont ±1,5 mm corrélé sur 3-5 m), ±0,3° de lacet, ±1 mm latéral, ±0,15° de
  roulis ; ni jitter de hauteur ni de roulis sur bateaux et chartières ; la variation de longueur est
  portée par la largeur des joints ;
- joints : largeur tirée par joint (bordures_elements.json element.joint_mm, 3-8 mm) : 5,5-7 mm sur une
  bordure neuve, 5-8 mm (log-normale centrée sur 6,5) sur une ancienne ; entre deux éléments droits,
  joint centré à mi-base et mi-hauteur (déviation en plan, lacet de jitter et changement de pente
  compris) : w ± coin aux 4 coins, ramenés dans 3,5-9,5 mm ; coude du levé (coin > 6 mm) : l'élément
  dont la corde s'écarte le plus de la face devient une pièce sur mesure ; une pièce sur mesure prend
  la normale d'about de sa voisine droite (ou la bissectrice), d'où des abouts parallèles ; angle vif :
  onglet ; bouchon de mortier en retrait de 4 mm (joint_<profil>, sombre) ou, pour la moitié des joints
  des bordures anciennes, mortier clair à fleur (jointf_<profil>), orienté sur la normale du joint ;
- bordures anciennes : désaffleurement (hauteur ±3 mm) et lacet (±0,5°) plus marqués ;
- échelle X de chaque instance = longueur posée / longueur du prototype (coupes 0,80-1,00, éléments
  d'une file multiple du pas ±0,6 %) : chaque élément occupe exactement sa case ;
- raccords de profil (rôle chartière sans abaissé, description) : loft du profil haut vers le profil
  de l'intervalle voisin à l'extrémité basse ;
- caniveaux (description `caniveau`, CS1-CS3) : éléments alignés sur ceux de la bordure, devant la face
  vue (u de −largeur à 0), dessous = fil d'eau − h_cote_bordure.
Sortie : listes d'éléments, de joints et de caniveaux ; pj_bordure_prototypes fabrique les prototypes.
"""
import math

import numpy as np

import pj_commun as K

C = K.C
JOINT_DEFAUT = 0.006
COUPE_MIN = 0.20
LONGUEURS_BASE_COUPE = [0.194, 0.244, 0.294, 0.344, 0.394, 0.444, 0.494, 0.594, 0.694, 0.794, 0.894, 0.994]
# (coupes : prototypes à abouts sciés nets, X mis à l'échelle de 0,80 à 1,00)
PRIORITE = {"abaisse": 3, "angle": 2, "profil": 1, "extremite": 0, "coupe_zone": -1}


# --------------------------------------------------------------------------- rayon et angles
def rayons(B, pas=0.25):
    """Rayon local (m) échantillonné tous les `pas` m (médiane glissante sur 3 m)."""
    s = np.arange(0.0, B.L + 1e-9, pas)
    if len(s) < 2:
        s = np.array([0.0, B.L])
    r = C.rayon_courbure(B.P, s, h=1.0)
    r = C.mediane_glissante(np.minimum(r, 1e4), int(3.0 / pas) | 1)
    return s, r


def angles_vifs(B):
    """Abscisses des angles vifs (déviation > 30° sur 0,5 m)."""
    out = []
    for i in range(1, len(B.P) - 1):
        s = B.S[i]
        if s < 0.3 or s > B.L - 0.3:
            continue
        if any(a0 - 0.05 <= s <= a1 + 0.05 for a0, a1 in getattr(B, "arcs_fab", [])):
            continue                                   # nez arrondi : posé en pièces courbes
        a, ta = B.point(max(s - 0.25, 0))
        b, tb = B.point(min(s + 0.25, B.L))
        dev = math.degrees(math.acos(np.clip(float(ta[0] @ tb[0]), -1, 1)))
        if dev > 30:
            if not out or s - out[-1] > 0.5:
                out.append(float(s))
    return out


# --------------------------------------------------------------------------- segments
def segments(B):
    """Segments entre points durs : [(a, b, intervalle, type_a, type_b)]."""
    durs = {}

    def ajouter(s, typ):
        s = round(float(s), 4)
        if s in durs:
            if PRIORITE[typ] > PRIORITE[durs[s]]:
                durs[s] = typ
        else:
            durs[s] = typ
    cz = B.p.get("coupe_zone") or {}
    ajouter(0.0, "coupe_zone" if cz.get("debut") else "extremite")
    ajouter(B.L, "coupe_zone" if cz.get("fin") else "extremite")
    for k, i in enumerate(B.iv):
        if k == 0:
            continue
        prev = B.iv[k - 1]
        typ = "abaisse" if (i["role"] != "courant" or prev["role"] != "courant") else "profil"
        ajouter(i["s0"], typ)
    for s in angles_vifs(B):
        # un angle à moins de 0,25 m d'un autre point dur ne crée pas de file minuscule
        if all(abs(s - x) >= 0.25 for x in durs):
            ajouter(s, "angle")
    cles = sorted(durs)
    out = []
    for a, b in zip(cles[:-1], cles[1:]):
        if b - a < 1e-4:
            continue
        iv = B.intervalle(0.5 * (a + b))
        out.append((a, b, iv, durs[a], durs[b]))
    return out


# --------------------------------------------------------------------------- remplissage d'une file
FLECHE_MAX = 0.0105        # flèche de corde admise pour un élément droit (bordures_elements.json)
COIN_MAX = 0.0060          # coin de joint admis (base x déviation des tangentes) : joint de 6 mm centré -> 3-9 mm aux 4 coins


def deviation(B, s0, s1):
    """Déviation (rad, absolue) des tangentes de la face entre s0 et s1."""
    _, ta = B.point(max(min(s0, s1), 0.0))
    _, tb = B.point(min(max(s0, s1), B.L))
    return abs(math.atan2(ta[0, 0] * tb[0, 1] - ta[0, 1] * tb[0, 0], float(ta[0] @ tb[0])))


def fleche(B, s0, s1, n=11):
    """Flèche max (m) de la polyligne par rapport à la corde [s0, s1]."""
    ss = np.linspace(max(s0, 0.0), min(s1, B.L), n)
    q, _ = B.point(ss)
    d = q[-1] - q[0]
    L = max(float(np.hypot(*d)), 1e-9)
    y = np.array([-d[1], d[0]]) / L
    return float(np.max(np.abs((q - q[0]) @ y)))


COIN_V_MAX = 0.004         # coin vertical admis : H x changement de pente entre les deux moitiés de l'élément


def pente_ok(B, a, b, H):
    """Changement de pente du fil d'eau sur [a, b] (moitié 1 / moitié 2) x H ≤ COIN_V_MAX : sur un coude
    vertical (accès riverains, points bas), éléments plus courts (pratique de pose)."""
    lo, hi = max(min(a, b), 0.0), min(max(a, b), B.L)
    m = 0.5 * (lo + hi)
    if hi - lo < 0.05:
        return True
    z0, zm, z1 = (float(B.z_fe(x)) for x in (lo, m, hi))
    return H * abs((z1 - zm) - (zm - z0)) / (0.5 * (hi - lo)) <= COIN_V_MAX


def droit_ok(B, a, b, base, k=1.0, H=0.0):
    """Élément droit admis sur [a, b] : flèche de corde ≤ 10,5 mm, coin de joint (base x déviation des
    tangentes, revue conformité r2 : joints ouverts à 21 mm d'un côté, chevauchés de 8 mm de l'autre sur
    les courbes) ≤ COIN_MAX et coin vertical ≤ COIN_V_MAX ; k < 1 : seuils réduits (hystérésis)."""
    lo, hi = max(min(a, b), 0.0), min(max(a, b), B.L)
    return fleche(B, lo, hi) <= k * FLECHE_MAX and base * deviation(B, lo, hi) <= k * COIN_MAX and \
        (H <= 0 or pente_ok(B, lo, hi, H))


def classe_pas(B, s_dep, sens, t, r_loc, droit_seul=False, prec=None, base=0.15, H=0.25):
    """Pas de l'élément qui commence à t (depuis s_dep, dans le sens `sens`) : le plus long des
    pas 1,00 / 0,50 dont la flèche de corde reste ≤ 10,5 mm et le coin de joint (base x déviation)
    ≤ 6 mm (R ≥ 25 m pour 1,00, R ≥ 12,5 m pour 0,50 avec une base de 0,15) ; sinon pièce courbe
    sur mesure (abouts radiaux, joint constant ; arc ≈ 1 m, au plus un quart de cercle si R < 1 m) ;
    `droit_seul` (bateaux) : pas 0,33 / 0,25 au lieu des pièces courbes.
    Hystérésis (prec = pas de l'élément précédent) : après un élément de 0,50, on ne repasse à 1,00
    que si ce pas et le suivant restent sous 60 % de la flèche admise (pas de 1,0 / 0,5 / 1,0
    alternés dans une courbe de R ≈ 12 m, K-0385 E008-E017)."""
    pas = (1.0, 0.5, 0.33, 0.25) if droit_seul else (1.0, 0.5)
    for p in pas:
        a, b = s_dep + sens * t, s_dep + sens * (t + p)
        if p == 1.0 and prec is not None and prec < 1.0:
            c, d = s_dep + sens * (t + p), s_dep + sens * (t + 2 * p)
            if droit_ok(B, a, b, base, 0.6, H) and droit_ok(B, c, d, base, 0.6, H):
                return p, "droit"
            continue
        if droit_ok(B, a, b, base, 1.0, H) or (droit_seul and p == pas[-1]):
            return p, "droit"
    # pièce courbe : arc d'au plus 1 m et d'au plus un quart de cercle (déviation mesurée, la médiane
    # glissante du rayon effaçait les nez serrés : K-0353/E072 couvrait 118° en une pièce)
    p = 1.0
    while p > 0.3 and (deviation(B, s_dep + sens * t, s_dep + sens * (t + p)) > 0.5 * math.pi or
                       not pente_ok(B, s_dep + sens * t, s_dep + sens * (t + p), H)):
        p *= 0.85
    return max(0.3, p), "courbe"


def remplir(D, pas_a, joint):
    """Découpe d'une file de longueur D (depuis son point de départ) en éléments.
    pas_a(t) -> (pas, genre). Renvoie [(t0, longueur_reelle, genre, coupe)]."""
    out = []
    t = 0.0
    # file multiple du pas (±1 %, genre constant) : éléments égaux, sans coupe
    p0, g0 = pas_a(0.0, None)
    n = int(round(D / p0))
    if n >= 1 and abs(D - n * p0) <= 0.01 * n * p0 and \
            all(pas_a(k * p0, p0 if k else None) == (p0, g0) for k in range(n)):
        L = D / n
        return [(k * L, L - joint, g0, False) for k in range(n)]
    prec = None
    while D - t > 1e-6:
        reste = D - t
        p, g = pas_a(t, prec)
        prec = p
        if reste >= p + COUPE_MIN + joint:
            out.append((t, p - joint, g, False))
            t += p
        elif reste > p + 0.003:
            h = reste / 2
            out.append((t, h - joint, g, True))
            out.append((t + h, h - joint, g, True))
            t = D
        elif reste >= p - 0.01:
            out.append((t, reste - joint, g, False))
            t = D
        elif reste - joint >= COUPE_MIN or not out:
            if reste - joint >= 0.05:                 # file plus courte qu'une coupe : une seule pièce
                out.append((t, reste - joint, g, True))
            t = D
        else:
            t0, l0, g0_, _ = out.pop()
            h = (l0 + joint + reste) / 2
            out.append((t0, h - joint, g0_, True))
            out.append((t0 + h, h - joint, g0_, True))
            t = D
    return out


# --------------------------------------------------------------------------- pose
def directions(B, e):
    """Directions (plan, unitaires) des normales d'about au début et à la fin d'un élément : corde
    (élément droit, coupe, bateau, chartière) ou tangente de la face (pièce courbe)."""
    if sur_mesure(e):
        _, ta = B.point(e["s0"])
        _, tb = B.point(e["s1"])
        return ta[0], tb[0]
    a, _ = B.point(e["s0"])
    b, _ = B.point(e["s1"])
    d = (b - a)[0]
    d = d / max(float(np.hypot(*d)), 1e-12)
    return d, d


def sur_mesure(e):
    """Pièce fabriquée sur mesure le long de la face (pièce courbe, chartière qui suit la face, élément
    droit, coupe ou bateau sur un coude) : origine au milieu de la corde, abouts radiaux ou en onglet."""
    return e["type"] == "courbe" or bool(e.get("suit_face")) or bool(e.get("sur_mesure"))


def _ancien(B):
    """Bordure ancienne (aspect.epaufrures ≥ 0,2) : jitter, joints et teintes plus marqués."""
    return float((B.p.get("aspect") or {}).get("epaufrures", 0.3)) >= 0.2


class Poseur:
    def __init__(self, desc, specs):
        self.desc, self.specs = desc, specs
        self.elements, self.joints = [], []
        self.caniveaux, self.joints_caniveaux = [], []

    def dims(self, profil):
        return self.specs.dims(profil)

    def poser(self):
        for B in self.desc.bordures:
            self._bordure(B)
        return self.elements, self.joints

    def _bordure(self, B):
        joint = float(B.p.get("joint_mm") or 6) / 1000.0
        sr, rr = rayons(B)
        r_min = lambda s0, s1: float(np.min(rr[(sr >= s0 - 0.13) & (sr <= s1 + 0.13)], initial=1e4))
        elems = []
        h = joint / 2          # chaque élément est centré dans sa case : demi-joint de part et d'autre
        for (a, b, iv, ta, tb) in segments(B):
            D = b - a
            if iv["role"] == "chartiere":
                e = self._element(B, iv, a + h, b - h, "chartiere", False, joint)
                # chartière sur une courbe ou un coude : loft le long de la face (abouts radiaux)
                e["suit_face"] = not droit_ok(B, a + h, b - h, self.dims(iv["profil"])[0])
                elems.append(e)
                continue
            depart_fin = PRIORITE[tb] > PRIORITE[ta]
            sens = -1.0 if depart_fin else 1.0
            s_dep = b if depart_fin else a

            bateau = iv["role"] == "bateau"

            base_p, H_p = self.dims(iv["profil"])

            def pas_a(t, prec, s_dep=s_dep, sens=sens, bateau=bateau, base_p=base_p, H_p=H_p):
                return classe_pas(B, s_dep, sens, t, r_min, droit_seul=bateau, prec=prec, base=base_p, H=H_p)
            seg = []
            for (t0, L, genre, coupe) in remplir(D, pas_a, joint):
                if depart_fin:
                    s1 = b - t0 - h
                    s0 = s1 - L
                else:
                    s0 = a + t0 + h
                    s1 = s0 + L
                typ = "bateau" if iv["role"] == "bateau" else genre
                if typ == "droit" and not droit_ok(B, s0, s1, base_p, 1.0, H_p):
                    typ = "courbe"            # coupe tombée dans une courbe serrée : sur mesure
                e = self._element(B, iv, s0, s1, typ, coupe, joint)
                e["depart"] = "fin" if depart_fin else "debut"
                seg.append(e)
            if seg and ta == "angle":         # angle vif : about en onglet (bissectrice), _largeurs_joints
                min(seg, key=lambda e: e["s0"])["angle_debut"] = True
            if seg and tb == "angle":
                max(seg, key=lambda e: e["s1"])["angle_fin"] = True
            elems += seg
        elems.sort(key=lambda e: e["s0"])
        for k, e in enumerate(elems):
            e["id"] = f"{B.id}/E{k:03d}"
            e["index"] = k
        self._jitter(B, elems)                # avant les joints : le lacet de jitter entre dans le coin de joint
        self._largeurs_joints(B, elems)
        self.elements += elems
        for e0, e1 in zip(elems[:-1], elems[1:]):
            ecart = e1["s0"] - e0["s1"]
            if ecart < 0.02:
                self.joints.append(self._joint(B, e0, e1, ecart))
        self._caniveaux(B, elems)

    def _largeurs_joints(self, B, elems):
        """Largeur de chaque joint (graine = hash(bordure, joint)) : 5,5-7 mm (neuve), log-normale
        centrée sur 6,5 mm bornée à 5-8 mm (ancienne) ; les deux éléments voisins sont raccourcis ou
        allongés autour du milieu du joint (la case de 1,00 m ne bouge pas).
        Abouts (revue conformité r2 : joints ouverts à 21 mm d'un côté, chevauchés de 8 mm de l'autre) :
        - deux éléments droits : abouts perpendiculaires à leurs cordes, non parallèles (déviation φ,
          + = à gauche, vers l'arrière) ; l'écart vaut w − u·φ à la profondeur u, le joint est centré à
          mi-base (écart sur la face w + base·φ/2) : w ± base·φ/2 aux quatre coins ;
        - si base·|φ| > COIN_MAX (coude du levé) : l'élément dont la corde s'écarte le plus de la face
          devient une pièce sur mesure qui suit la face ; angle vif : les deux (onglet) ;
        - une pièce sur mesure prend la normale d'about de sa voisine droite, ou la bissectrice des deux
          tangentes si les deux sont sur mesure : abouts parallèles, joint constant (biais calculés par
          poses())."""
        ancien = _ancien(B)
        paires = [(k, e0, e1) for k, (e0, e1) in enumerate(zip(elems[:-1], elems[1:])) if e1["s0"] - e0["s1"] < 0.02]

        def phi_de(e0, e1):
            """Déviation des normales d'about (rad, + = à gauche), lacet de jitter compris."""
            _, d0 = directions(B, e0)
            d1, _ = directions(B, e1)
            jl = math.radians(e1["jitter"]["lacet"] - e0["jitter"]["lacet"])
            return math.atan2(d0[0] * d1[1] - d0[1] * d1[0], float(d0 @ d1)) + jl, d0, d1

        def base_de(e0, e1):
            return min(self.dims(e0.get("profil_bas", e0["profil"]))[0], self.dims(e0["profil"])[0],
                       self.dims(e1.get("profil_bas", e1["profil"]))[0], self.dims(e1["profil"])[0])

        def convertir(e):
            e["suit_face" if e["type"] == "chartiere" else "sur_mesure"] = True

        def ecart_corde(e, s):
            """Écart angulaire entre la corde (ou la tangente) de l'élément et la face au joint s."""
            d0, d1 = directions(B, e)
            d = d1 if abs(s - e["s1"]) < abs(s - e["s0"]) else d0
            _, t = B.point(s)
            return abs(math.atan2(d[0] * t[0, 1] - d[1] * t[0, 0], float(d @ t[0])))
        for k, e0, e1 in paires:
            if e0.get("angle_fin") and e1.get("angle_debut"):
                for e in (e0, e1):
                    if not sur_mesure(e):
                        convertir(e)
                continue
            if sur_mesure(e0) or sur_mesure(e1):
                continue
            phi, _, _ = phi_de(e0, e1)
            if base_de(e0, e1) * abs(phi) > COIN_MAX:
                m = 0.5 * (e0["s1"] + e1["s0"])
                convertir(e0 if ecart_corde(e0, m) >= ecart_corde(e1, m) else e1)
        for k, e0, e1 in paires:
            r = K.rng(B.id, "largeur_joint", k)
            w = float(np.clip(r.lognormal(math.log(0.0065), 0.16), 0.005, 0.008)) if ancien \
                else float(r.uniform(0.0055, 0.007))
            phi, d0, d1 = phi_de(e0, e1)
            c0, c1 = sur_mesure(e0), sur_mesure(e1)
            # coin vertical : changement de pente Δp entre les deux éléments (+ = point bas) ; l'écart vaut
            # g_pied − v·Δp à la hauteur v : centré à mi-hauteur
            pente = lambda e: float(B.z_fe(e["s1"]) - B.z_fe(e["s0"])) / max(e["s1"] - e["s0"], 1e-3)
            H = min(self.dims(e0["profil"])[1], self.dims(e1["profil"])[1])
            dv = 0.5 * H * (pente(e1) - pente(e0))
            if c0 or c1:
                dj = d0 + d1 if (c0 and c1) else (d1 if c0 else d0)
                dj = dj / max(float(np.hypot(*dj)), 1e-12)
                e0["n_fin"], e1["n_debut"] = dj, dj
                _, t = B.point(0.5 * (e0["s1"] + e1["s0"]))
                w = float(np.clip(w, 0.0035 + abs(dv), 0.0095 - abs(dv))) if abs(dv) < 0.003 else 0.0065
                g = w / max(abs(float(dj @ t[0])), 0.5) + dv
            else:
                dj = d0 + d1
                dj = dj / max(float(np.hypot(*dj)), 1e-12)
                dw = 0.5 * base_de(e0, e1) * abs(phi) + abs(dv)
                w = float(np.clip(w, 0.0035 + dw, 0.0095 - dw)) if dw < 0.003 else 0.0065   # coins dans 3,5-9,5 mm
                g = max(0.0035, w + 0.5 * base_de(e0, e1) * phi + dv)
            m = 0.5 * (e0["s1"] + e1["s0"])
            e0["s1"], e1["s0"] = m - g / 2, m + g / 2
            e0["joint_w"], e0["joint_dir"] = w, dj
            e0["mortier_fin"] = e1["mortier_debut"] = "clair" if ancien and r.uniform() < 0.5 else "sombre"
        for e in elems:
            e["longueur"] = e["s1"] - e["s0"]

    def _caniveaux(self, B, elems):
        """Éléments de caniveau devant les éléments de bordure (joints alignés, description `caniveau`)."""
        if not (B.p.get("caniveau") or {}).get("intervalles"):
            return
        prec = None
        for e in elems:
            sm = 0.5 * (e["s0"] + e["s1"])
            prof = B.caniveau_a(sm)
            if prof is None:
                prec = None
                continue
            c = {"bordure": B.id, "s0": e["s0"], "s1": e["s1"], "longueur": e["longueur"], "profil": prof,
                 # sur une courbe, élément droit = joints en coin ouverts côté chaussée (u = −0,25) : pièce
                 # sur mesure dès 2 mm de flèche
                 "type": "caniveau", "genre": "courbe" if sur_mesure(e) or fleche(B, e["s0"], e["s1"]) > 0.002 else "droit",
                 "coupe": bool(e["coupe"] or abs(e["longueur"] - 0.994) > 0.012), "materiau": "caniveau_beton",
                 "id": e["id"].replace("/E", "/C"), "index": e["index"], "graine": K.graine(B.id, "caniveau", e["index"]),
                 "vue": 0.0, "role": "caniveau"}
            self.caniveaux.append(c)
            if prec is not None and c["s0"] - prec["s1"] < 0.02:
                self.joints_caniveaux.append({"bordure": B.id, "id": f"{B.id}/JC{prec['index']:03d}",
                                              "s": float(0.5 * (prec["s1"] + c["s0"])), "profil": prof,
                                              "ecart": float(c["s0"] - prec["s1"]), "caniveau": True,
                                              "mortier": "sombre",
                                              "graine": K.graine(B.id, "joint_caniveau", prec["index"])})
            prec = c

    def _element(self, B, iv, s0, s1, typ, coupe, joint):
        s0, s1 = max(s0, 0.0), min(s1, B.L)
        e = {"bordure": B.id, "s0": float(s0), "s1": float(s1), "longueur": float(s1 - s0),
             "type": typ, "coupe": bool(coupe), "profil": iv["profil"], "role": iv["role"],
             "vue": float(iv["vue_m"]), "joint": joint, "materiau": B.p.get("materiau", "beton_gris")}
        if typ == "chartiere":
            e["vue_fin"] = float(iv["vue_m_fin"])
            # profil de l'extrémité basse : intervalle voisin (bateau, ou profil courant plus bas)
            e["profil_bas"] = B.profil_bas(iv)
            e["sens"] = "desc" if iv["vue_m"] > iv["vue_m_fin"] else "asc"
        return e

    def _jitter(self, B, elems):
        """Jitter déterministe (graine = hash(bordure, élément)) ; hauteur corrélée le long de s."""
        J = dict(self.specs.elements["jitter"])
        if _ancien(B):                 # désaffleurements et lacets d'une bordure ancienne (photo 1)
            J["hauteur_mm"], J["lacet_deg"] = 1.5 * J["hauteur_mm"], max(J["lacet_deg"], 0.5)
        g = K.rng(B.id, "tassement")
        ph = g.uniform(0, 2 * math.pi, 3)
        lam = g.uniform(3.0, 5.0, 3)
        for e in elems:
            r = K.rng(B.id, e["index"])
            sm = 0.5 * (e["s0"] + e["s1"])
            k_h = J["hauteur_mm"] / 2.0
            lent = sum(math.sin(2 * math.pi * sm / l + p) for l, p in zip(lam, ph)) / 3.0 * 1.5e-3 * 1.6 * k_h
            fixe = e["type"] in ("bateau", "chartiere")
            dz = 0.0 if fixe else float(np.clip(lent + r.uniform(-1e-3, 1e-3) * k_h, -J["hauteur_mm"] / 1000, J["hauteur_mm"] / 1000))
            e["jitter"] = {
                "dz": dz,
                "lacet": float(r.uniform(-J["lacet_deg"], J["lacet_deg"])),
                "lateral": float(r.uniform(-J["lateral_mm"], J["lateral_mm"]) / 1000),
                "longueur": float(r.uniform(-J["longueur_mm"], J["longueur_mm"]) / 1000),
                "roulis": 0.0 if fixe else float(r.uniform(-J["roulis_deg"], J["roulis_deg"])),
            }
            e["graine"] = K.graine(B.id, e["index"])

    def _joint(self, B, e0, e1, ecart):
        """Bouchon de mortier : profil de l'extrémité la plus basse des deux éléments."""
        def bout(e, cote):
            if e["type"] == "chartiere":
                haut = (e["sens"] == "desc") == (cote == "debut")
                return (e["profil"], e["vue"] if haut else e["vue_fin"]) if haut else (e["profil_bas"], min(e["vue"], e["vue_fin"]))
            return e["profil"], e["vue"]
        p0, v0 = bout(e0, "fin")
        p1, v1 = bout(e1, "debut")
        z0 = float(B.z_fe(e0["s1"])) + v0
        z1 = float(B.z_fe(e1["s0"])) + v1
        prof, vue = (p0, v0) if z0 <= z1 else (p1, v1)
        s = 0.5 * (e0["s1"] + e1["s0"])
        # bouchon : orienté sur la normale du joint (abouts parallèles) ou la bissectrice, largeur à mi-base
        dm = e0.get("joint_dir")
        if dm is None:
            _, d0 = directions(B, e0)
            d1, _ = directions(B, e1)
            dm = (d0 + d1) / max(float(np.hypot(*(d0 + d1))), 1e-12)
        return {"bordure": B.id, "id": f"{B.id}/J{e0['index']:03d}", "s": float(s), "profil": prof,
                "vue": float(vue), "ecart": float(e0.get("joint_w", ecart)), "ecart_face": float(ecart),
                "dir": dm, "graine": K.graine(B.id, "joint", e0["index"]), "mortier": e0.get("mortier_fin", "sombre")}


# --------------------------------------------------------------------------- géométrie de pose
def repere_element(B, s0, s1):
    """Corde de l'élément : milieu (corrigé de la demi-flèche), direction, flèche max (m)."""
    a, _ = B.point(s0)
    b, _ = B.point(s1)
    a, b = a[0], b[0]
    d = b - a
    L = float(np.hypot(*d))
    x = d / max(L, 1e-9)
    ss = np.linspace(s0, s1, 9)
    q, _ = B.point(ss)
    y = np.array([-x[1], x[0]])
    dev = (q - a) @ y                          # écart polyligne - corde (+ = à gauche)
    milieu = 0.5 * (a + b) + y * 0.5 * float(dev[4])
    return milieu, x, y, L, float(np.max(np.abs(dev - 0.5 * dev[4])))


def nom_prototype(e, specs):
    """Nom du prototype d'un élément (prototypes partagés, sauf pièces courbes) ; pose aussi
    e["echelle_x"] = longueur posée / longueur du prototype (coupes, files multiples du pas)."""
    p = e["profil"]
    if e["type"] == "caniveau":
        if e["genre"] == "courbe":
            return "caniveau_courbe_" + e["id"].replace("/", "_").replace("-", "")
        if e["coupe"]:
            base = min([b for b in LONGUEURS_BASE_COUPE if b >= e["longueur"] - 1e-6] or [LONGUEURS_BASE_COUPE[-1]])
            e["echelle_x"] = e["longueur"] / base
            return f"caniveau_{p}_coupe_L{int(round(base * 1000))}"
        e["echelle_x"] = e["longueur"] / 0.994
        return f"caniveau_{p}_L994"
    if e["type"] == "chartiere":
        L = int(round(e["longueur"] * 1000))
        haut, bas = max(e["vue"], e["vue_fin"]), min(e["vue"], e["vue_fin"])
        if e.get("suit_face"):
            return "chartiere_courbe_" + e["id"].replace("/", "_").replace("-", "")
        return f"chartiere_{p}{int(round(haut * 1000)):03d}_{e['profil_bas']}" \
               f"{int(round(bas * 1000)):03d}_L{L}_{e['sens']}"
    if e["type"] == "courbe" or e.get("sur_mesure"):
        return "courbe_" + e["id"].replace("/", "_").replace("-", "")
    if e["coupe"] or abs(e["longueur"] - 0.994) > 0.012 and abs(e["longueur"] - 0.494) > 0.006:
        base = min([b for b in LONGUEURS_BASE_COUPE if b >= e["longueur"] - 1e-6] or [LONGUEURS_BASE_COUPE[-1]])
        e["echelle_x"] = e["longueur"] / base
        return f"coupe_{p}_L{int(round(base * 1000))}"
    base = 0.994 if e["longueur"] > 0.75 else 0.494
    e["echelle_x"] = e["longueur"] / base
    return f"element_{p}_L{int(round(base * 1000))}_v{e.get('variante', 0)}"


def choisir_variantes(desc, elements, specs):
    """Variante d'épaufrures v0-v3 selon l'âge (neuf 2025 / ancien) et la graine de l'élément."""
    rep = specs.elements["epaufrures"]["repartition"]
    for e in elements:
        B = desc.par_id[e["bordure"]]
        asp = B.p.get("aspect") or {}
        table = rep["ancien"] if float(asp.get("epaufrures", 0.3)) >= 0.2 else rep["neuf_2025"]
        if e["type"] in ("chartiere", "courbe") or e["coupe"] or sur_mesure(e):
            e["variante"] = 0
            continue
        u = (e["graine"] % 10007) / 10007.0
        acc = 0.0
        e["variante"] = 3
        for k, v in enumerate(["v0", "v1", "v2", "v3"]):
            acc += table[v]
            if u < acc:
                e["variante"] = k
                break


def poses(desc, specs, elements, joints, caniveaux=(), joints_caniveaux=()):
    """Transformations finales (pivot, rpy, échelle) des éléments, des joints et des caniveaux. Le
    prototype (et son échelle X) est choisi AVANT la pose : chaque élément occupe exactement sa case
    (une coupe de 0,595 m posée sur un prototype de 0,694 m est à l'échelle 0,858)."""
    for e in list(elements) + list(caniveaux):
        e["asset"] = nom_prototype(e, specs)
    for e in elements:
        B = desc.par_id[e["bordure"]]
        milieu, x, y, L, fl = repere_element(B, e["s0"], e["s1"])
        if sur_mesure(e):                           # pièce sur mesure : origine au milieu de la corde
            a, _ = B.point(e["s0"])
            b, _ = B.point(e["s1"])
            milieu = 0.5 * (a[0] + b[0])
        e["fleche_mm"] = round(fl * 1000, 2)
        prof = e["profil"]
        base, H = specs.dims(prof)
        # fil d'eau au milieu de la CORDE (et non de la courbe) : les abouts tombent sur le fil d'eau
        zfe = 0.5 * float(B.z_fe(e["s0"]) + B.z_fe(e["s1"]))
        j = e["jitter"]
        vue = max(e["vue"], e["vue_fin"]) if e["type"] == "chartiere" else e["vue"]
        z = zfe + vue - H + j["dz"]
        lat = j["lateral"]
        lacet = math.degrees(math.atan2(x[1], x[0])) + j["lacet"]
        tangage = math.degrees(math.atan2(float(B.z_fe(e["s1"]) - B.z_fe(e["s0"])), L))
        p = np.r_[milieu + y * lat, z]
        e["p"] = p
        e["rpy"] = [j["roulis"], -tangage, lacet]          # p > 0 abaisse l'avant (convention UE pj_tools)
        e["z_pied"] = H - vue                       # fil d'eau dans le repère de l'élément
        # variation de longueur portée par la largeur des joints (jitter de longueur non appliqué)
        sx = e.get("echelle_x", 1.0) if not (e["type"] == "chartiere" or sur_mesure(e)) else 1.0
        # la pose se fait en abscisse horizontale : sur une pente, l'élément est allongé de 1/cos(pente)
        # pour couvrir sa case (K-0177 à 10 % : joints de 11-12 mm sinon)
        e["s"] = [sx / math.cos(math.radians(tangage)), 1.0, 1.0]
        e["corde"] = (milieu, x, y, L)
        # demi-longueur du prototype en repère objet (mousse aux abouts, pj_materiaux)
        e["demi_longueur"] = 0.5 * L if sur_mesure(e) else 0.5 * e["longueur"] / e.get("echelle_x", 1.0)
        if sur_mesure(e):
            # abouts de la pièce sur mesure : normales imposées par _largeurs_joints (voisine droite ou
            # bissectrice), en biais par rapport aux tangentes du chemin (repère de l'élément)
            ch = chemin_courbe(B, e)
            for cle, k, sg in (("debut", 0, -1.0), ("fin", -1, 1.0)):
                n = e.get("n_" + cle)
                e["biais_" + cle] = 0.0
                if n is None:
                    continue
                t = ch[1] - ch[0] if k == 0 else ch[-1] - ch[-2]
                t = t / max(float(np.hypot(*t)), 1e-12)
                nl = np.array([float(n @ x), float(n @ y)])
                # le lacet de jitter tourne toute la pièce : retranché pour garder la normale imposée
                e["biais_" + cle] = sg * (math.atan2(t[0] * nl[1] - t[1] * nl[0], float(t @ nl)) - math.radians(j["lacet"]))
    for c in caniveaux:
        B = desc.par_id[c["bordure"]]
        milieu, x, y, L, fl = repere_element(B, c["s0"], c["s1"])
        if c["genre"] == "courbe":
            a, _ = B.point(c["s0"])
            b, _ = B.point(c["s1"])
            milieu = 0.5 * (a[0] + b[0])
        _, h_bord, _ = specs.caniveau(c["profil"])
        sm = 0.5 * (c["s0"] + c["s1"])
        r = K.rng(c["id"], "jitter")
        z = float(B.z_fe(sm)) - h_bord + float(r.uniform(-1e-3, 1e-3))
        tangage = math.degrees(math.atan2(float(B.z_fe(c["s1"]) - B.z_fe(c["s0"])), L))
        c["p"] = np.r_[milieu, z]
        c["rpy"] = [0.0, -tangage, math.degrees(math.atan2(x[1], x[0])) + float(r.uniform(-0.15, 0.15))]
        c["z_pied"] = h_bord
        c["s"] = [(c.get("echelle_x", 1.0) if c["genre"] != "courbe" else 1.0) / math.cos(math.radians(tangage)), 1.0, 1.0]
        c["corde"] = (milieu, x, y, L)
        c["demi_longueur"] = 0.5 * L if c["genre"] == "courbe" else 0.5 * c["longueur"] / c.get("echelle_x", 1.0)
        c["fleche_mm"] = round(fl * 1000, 2)
    for jt in list(joints) + list(joints_caniveaux):
        B = desc.par_id[jt["bordure"]]
        a, t = B.point(jt["s"])
        x = jt.get("dir", t[0])
        if jt.get("caniveau"):
            _, h_bord, _ = specs.caniveau(jt["profil"])
            z = float(B.z_fe(jt["s"])) - h_bord
            jt["asset"] = f"joint_{jt['profil']}"
        else:
            base, H = specs.dims(jt["profil"])
            z = float(B.z_fe(jt["s"])) + jt["vue"] - H
            jt["asset"] = ("jointf_" if jt.get("mortier") == "clair" else "joint_") + jt["profil"]
        jt["p"] = np.r_[a[0], z]
        jt["rpy"] = [0.0, 0.0, math.degrees(math.atan2(x[1], x[0]))]
        # bouchon de 10 mm (joint de 6 + 2 x 2 mm sous les abouts) mis à la largeur réelle du joint
        jt["s_ech"] = [float((jt["ecart"] + 0.004) / (JOINT_DEFAUT + 0.004)), 1.0, 1.0]


# --------------------------------------------------------------------------- demandes et sorties
def chemin_courbe(B, e, pas=0.02):
    """Face vue de la pièce courbe dans son repère (origine au milieu de la corde, X = corde)."""
    s = np.linspace(e["s0"], e["s1"], max(3, int(math.ceil(e["longueur"] / pas)) + 1))
    q, _ = B.point(s)                       # face déjà lisse (Catmull-Rom, nez arrondis) : pas de lissage
    o, x, y, L = e["corde"]
    d = q - o
    return np.c_[d @ x, d @ y]


def demandes(desc, specs, elements, joints, caniveaux=(), joints_caniveaux=()):
    """Prototypes nécessaires : jeu complet par profil utilisé (0,994 / 0,494 x v0-v3), coupes,
    chartières, pièces courbes, joints (sombres en retrait, clairs à fleur), quarts de rond de
    catalogue, caniveaux."""
    dem = {}
    profils = sorted(set(e["profil"] for e in elements) | set(e.get("profil_bas", e["profil"]) for e in elements))
    for p in profils:
        for L in (0.994, 0.494):
            for v in range(4):
                dem[f"element_{p}_L{int(round(L * 1000))}_v{v}"] = {"type": "element", "profil": p, "longueur": L, "variante": v}
        dem[f"joint_{p}"] = {"type": "joint", "profil": p, "joint": JOINT_DEFAUT}
        dem[f"jointf_{p}"] = {"type": "joint", "profil": p, "joint": JOINT_DEFAUT, "affleurant": 1}
    for c in caniveaux:
        nom = c["asset"]
        if nom in dem:
            continue
        if c["genre"] == "courbe":
            dem[nom] = {"type": "caniveau_courbe", "profil": c["profil"], "longueur": round(c["longueur"], 3),
                        "chemin": chemin_courbe(desc.par_id[c["bordure"]], c)}
        else:
            dem[nom] = {"type": "caniveau", "profil": c["profil"], "longueur": float(nom.rsplit("_L", 1)[1]) / 1000,
                        "coupe": int(bool(c["coupe"]))}
    for jc in joints_caniveaux:
        dem.setdefault(jc["asset"], {"type": "joint_caniveau", "profil": jc["profil"], "joint": JOINT_DEFAUT})
    for p, R in (("T2", 0.5), ("T3", 0.5), ("TU", 0.25), ("I1", 0.25), ("I2", 0.25)):
        dem[f"quart_{p}_R{int(round(R * 100)):03d}"] = {"type": "quart_de_rond", "profil": p, "rayon": R}
    for e in elements:
        nom = e["asset"]
        if nom in dem:
            continue
        if e["type"] == "chartiere":
            dem[nom] = {"type": "chartiere", "profil": e["profil"], "vue_haut": max(e["vue"], e["vue_fin"]),
                        "profil_bas": e["profil_bas"], "vue_bas": min(e["vue"], e["vue_fin"]),
                        "longueur": round(e["longueur"], 3), "sens": e["sens"]}
            if e.get("suit_face"):
                dem[nom]["chemin"] = chemin_courbe(desc.par_id[e["bordure"]], e)
                for k in ("biais_debut", "biais_fin"):
                    if abs(e.get(k, 0.0)) > 1e-6:
                        dem[nom][k] = round(float(e[k]), 5)
        elif e["type"] == "courbe" or e.get("sur_mesure"):
            B = desc.par_id[e["bordure"]]
            dem[nom] = {"type": "courbe", "profil": e["profil"], "longueur": round(e["longueur"], 3),
                        "chemin": chemin_courbe(B, e)}
            for k in ("biais_debut", "biais_fin"):
                if abs(e.get(k, 0.0)) > 1e-6:
                    dem[nom][k] = round(float(e[k]), 5)
        elif nom.startswith("coupe_"):
            dem[nom] = {"type": "coupe", "profil": e["profil"], "longueur": float(nom.rsplit("_L", 1)[1]) / 1000}
    return dem


def points_json(desc, elements, joints, caniveaux=(), joints_caniveaux=()):
    """Points pj_points/0.1 : éléments, bouchons de joint, caniveaux. Teinte par élément 0,88-1,12
    (ancienne) ou 0,94-1,06 (neuve) et dérive chaude / froide (lot de fabrication par bordure ±1,5 %,
    élément ±1 %) portée par `couleur` (gain RVB)."""
    pts = []
    for e in list(elements) + list(caniveaux):
        B = desc.par_id[e["bordure"]]
        asp = B.p.get("aspect") or {}
        r = K.rng(e["id"], "aspect")
        a, b = (0.88, 1.12) if _ancien(B) else (0.94, 1.06)
        teinte = float(r.uniform(a, b))
        lot = float(K.rng(B.id, "lot_teinte").uniform(-0.015, 0.015))
        d = lot + float(r.uniform(-0.01, 0.01))
        e["teinte"] = teinte
        e["couleur"] = [1.0 + d, 1.0, 1.0 - d]
        sal = asp.get("salissure", 0.3) * (1.4 if e["type"] == "caniveau" else 1.0)
        e["salissure"] = float(np.clip(sal * r.uniform(0.8, 1.2), 0, 1))
        e["mousse_joints"] = float(asp.get("mousse_joints", 0.0))
        cd = [float(asp.get("epaufrures", 0.0)), e["salissure"], float(asp.get("mousse_joints", 0.0)),
              float(asp.get("herbe_joints", 0.0)), teinte]
        pts.append({"id": e["id"], "asset": e["asset"], "p": K.r3(e["p"], 4), "q": K.q_xyzw(e["rpy"]),
                    "rpy_deg": K.r3(e["rpy"], 3), "s": K.r3(e["s"], 4), "graine": e["graine"], "cd": K.r3(cd, 3),
                    "x": {"bordure": e["bordure"], "type": e["type"], "profil": e["profil"], "vue_m": round(e["vue"], 3),
                          "s0": round(e["s0"], 3), "s1": round(e["s1"], 3), "longueur_m": round(e["longueur"], 4),
                          "coupe": e["coupe"], "variante": e.get("variante", 0), "materiau": e["materiau"],
                          "z_pied": round(e["z_pied"], 4), "couleur": K.r3(e["couleur"], 3)}})
    for j in list(joints) + list(joints_caniveaux):
        pts.append({"id": j["id"], "asset": j["asset"], "p": K.r3(j["p"], 4), "q": K.q_xyzw(j["rpy"]),
                    "rpy_deg": K.r3(j["rpy"], 3), "s": K.r3(j["s_ech"], 4), "graine": j["graine"], "cd": [],
                    "x": {"bordure": j["bordure"], "type": "joint", "profil": j["profil"], "s": round(j["s"], 3),
                          "ecart_m": round(j["ecart"], 4), "mortier": j.get("mortier", "sombre")}})
    return pts


def ecrire_usd(elements, joints, protos, chemin, ref, caniveaux=(), joints_caniveaux=()):
    """bordures.usda : PointInstancers (béton gris, béton clair, caniveaux, joints sombres et clairs)
    sur les prototypes."""
    import pj_usd as U
    from pxr import Sdf
    T = Sdf.ValueTypeNames
    st = U.scene("Bordures de la zone pilote en éléments préfabriqués (pj_bordure_pose.py) : PointInstancers "
                 "sur prototypes/*.usda ; données d'instance teinte, uv_decalage, salissure, z_pied. "
                 "Points de référence : points/bordures.json (pj_points/0.1).", data={"version": K.VERSION})
    U.xform(st, "/World/PJ_Bordures")
    groupes = [("beton_bordure_gris", [e for e in elements if e["materiau"] != "beton_clair"]),
               ("beton_bordure_clair", [e for e in elements if e["materiau"] == "beton_clair"]),
               ("caniveau_beton", list(caniveaux))]
    for mat, els in groupes:
        if not els:
            continue
        noms = sorted(set(e["asset"] for e in els))
        ix = {n: i for i, n in enumerate(noms)}
        pl = [(n, U.chemin_relatif(protos[n], ref), None) for n in noms]
        q = np.array([K.quat_de_matrice(K.rotation_rpy(e["rpy"])) for e in els])
        pi = U.instancer(st, f"/World/PJ_Bordures/{mat}", pl, [ix[e["asset"]] for e in els], [e["p"] for e in els], q,
                         echelles=[e["s"] for e in els],
                         primvars={"teinte": (U.vt([e["teinte"] for e in els], T.FloatArray), T.FloatArray),
                                   "salissure": (U.vt([e["salissure"] for e in els], T.FloatArray), T.FloatArray),
                                   "z_pied": (U.vt([e["z_pied"] for e in els], T.FloatArray), T.FloatArray),
                                   "mousse_joints": (U.vt([e["mousse_joints"] for e in els], T.FloatArray), T.FloatArray),
                                   "demi_longueur": (U.vt([e["demi_longueur"] for e in els], T.FloatArray), T.FloatArray),
                                   "couleur": (U.vt([e["couleur"] for e in els], T.Color3fArray), T.Color3fArray),
                                   "uv_decalage": (U.vt([[(e["graine"] % 1009) / 101.0, (e["graine"] // 1009 % 1013) / 101.0]
                                                         for e in els], T.Float2Array), T.Float2Array)})
        U.lier_chemin(pi.GetPrim(), f"/World/Looks_v2/{mat}")
    tous = list(joints) + list(joints_caniveaux)
    for nom_pi, mat, js in (("joints", "mortier_joint", [j for j in tous if j.get("mortier") != "clair"]),
                            ("joints_clairs", "mortier_clair", [j for j in tous if j.get("mortier") == "clair"])):
        noms = sorted(set(j["asset"] for j in js))
        if not noms:
            continue
        ix = {n: i for i, n in enumerate(noms)}
        pl = [(n, U.chemin_relatif(protos[n], ref), None) for n in noms]
        q = np.array([K.quat_de_matrice(K.rotation_rpy(j["rpy"])) for j in js])
        pi = U.instancer(st, f"/World/PJ_Bordures/{nom_pi}", pl, [ix[j["asset"]] for j in js], [j["p"] for j in js], q,
                         echelles=[j["s_ech"] for j in js])
        U.lier_chemin(pi.GetPrim(), f"/World/Looks_v2/{mat}")
    U.enregistrer(st, chemin)
