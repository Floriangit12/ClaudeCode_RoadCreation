"""Affinage de la pose d'une vue par alignement des arêtes du modèle sur les segments rectilignes de la photo
(chanfrein orienté tronqué), avec garde-fous, validation sur des segments non utilisés et indice de confiance.

- Segments de la photo : détecteur LSD d'OpenCV ; on garde les segments d'au moins 25 px, sous l'horizon de la
  caméra nominale, hors porteur, et pas sur un bord d'ombre portée (test de teinte de part et d'autre : le côté
  sombre d'une ombre, éclairé par le seul ciel, est plus bleu ; un marquage ou une bordure ne changent pas de
  teinte). Restent marquages, bordures, limites enrobé / herbe ; pas le feuillage, les taches d'ombre ni la texture
  de l'enrobé (essais sur S_M20 : avec des contours de Canny, l'affinage collait les arêtes du modèle sur les arbres).
  Une carte de distance par classe d'orientation (8 classes de 22,5°, tolérance ± 1 classe) : un point du modèle ne
  s'apparie qu'à un segment d'orientation voisine.
- Points du modèle : arêtes de modele.Modele.aretes() vues entre 3 et 30 m par la caméra nominale (ensemble FIXE
  pour comparer les poses) ; un point sorti de l'image ou tombé sur le porteur coûte le maximum.
- Coût : POIDS_DONNEES × moyenne de min(d, tau) / tau + 0,5·Σ (x / σ)² (a priori : position GNSS, σ = 1,5 m au plus,
  volontairement serré pour ne pas absorber les erreurs de description ; cap, tangage et roulis de la caméra, hauteur).
- Contrainte de chaussée : une caméra portée par une voiture dont la position GNSS est à moins de 3 m de la chaussée
  du modèle reste sur cette chaussée (0,8 m des rives).
- Paramètres : ds, dt (m, repère du modèle), dlacet, dtangage, droulis (°), dh (m). Garde-fous : déplacement ≤ 5 m,
  lacet ≤ 10°, tangage ≤ 4° et roulis ≤ 3° sur voiture (8° et 5° pour une caméra portée : vélo, piéton),
  hauteur ≤ 0,4 m.
- Recherche : grille grossière (lacet, tangage, décalage latéral) à tau = 40 px, puis Powell borné depuis la pose
  nominale et les 4 meilleurs nœuds, à tau = 40, 20 puis 10 px.
- Trois niveaux : redressement par les verticales de la photo 360° (vues.verticale_360, indépendant du modèle),
  orientation seule (lacet, tangage, roulis), pose complète.
- Validation : les segments de la photo sont partagés en deux moitiés (rangs pairs A, impairs B) ; on affine sur A et
  on mesure le score sur B, jamais vue : une amélioration sur B est une vraie amélioration de l'alignement, pas un
  ajustement au bruit. Un niveau n'est retenu que s'il améliore B de plus de 3 %, sans garde-fou atteint et sans
  écraser l'image du modèle (étalement vertical ≥ 50 % du nominal) ; la pose complète doit valider mieux que
  l'orientation seule de MARGE_COMPLETE (+ 0,05), que l'orientation ait franchi le seuil ou non. La solution retenue
  est affinée localement sur tous les segments et n'est gardée que si elle reste à moins de 1 m et 1,5° de la
  solution validée (sinon, la solution validée) ; sans niveau retenu, pose des métadonnées.
- Stabilité : deux départs décalés (± 1,5 m, ± 2°) doivent revenir à moins de 1 m et 1,5°.
Déterministe (aucun tirage aléatoire).
"""
import math

import cv2
import numpy as np
from scipy.optimize import minimize

import vues as V

N_ORIENT = 8
NOMS = ("ds", "dt", "dlacet", "dtangage", "droulis", "dh")
DEPLACEMENT_MAX = 5.0
BORNES = {"ds": 5.0, "dt": 5.0, "dlacet": 10.0, "dtangage": 4.0, "droulis": 3.0, "dh": 0.4}
BORNES_PORTEE = dict(BORNES, dtangage=8.0, droulis=5.0)
SIGMA = {"ds": 4.0, "dt": 4.0, "dlacet": 5.0, "dtangage": 1.5, "droulis": 1.0, "dh": 0.2}
SIGMA_PORTEE = dict(SIGMA, dtangage=3.5, droulis=2.0)
PROF_MIN, PROF_MAX = 3.0, 30.0
# position : a priori serré et marge de validation plus forte pour la pose complète. Un déplacement de la caméra
# peut « absorber » une erreur de description (largeurs, position d'un passage) et la masquer (essai S_M24, 9badc00e :
# caméra reculée de 2,6 m sur la piste pour recaler les bandes du passage, alors que la photo est prise sur le trottoir
# près de la bordure) ; or c'est précisément ce que la comparaison doit montrer.
SIGMA_POSITION = 1.5
MARGE_COMPLETE = 0.05
SEUIL_REDRESSEMENT = 0.06    # le redressement seul (sans ajustement sur le modèle) doit valider nettement
# poids du terme de données (moyenne du chanfrein tronqué, entre 0 et 1) face à l'a priori 0,5·Σ(x/σ)² : nombre
# effectif d'observations indépendantes (une trentaine de lignes du modèle visibles, très corrélées le long d'une ligne)
POIDS_DONNEES = 30.0
LONGUEUR_MIN = 25.0          # px : segments plus courts écartés (feuillage, taches d'ombre, texture de l'enrobé)
SEUIL_OMBRE = 0.08           # écart de log(B/R) entre les deux côtés (côté sombre plus bleu) au-delà duquel c'est une ombre
ELEVATION_MAX = 3.0          # ° : segments au-dessus de l'horizon (caméra nominale) écartés (bâtiments, arbres, panneaux)


BORNES_INCONNU = dict(BORNES, dtangage=6.0, droulis=4.0)
SIGMA_INCONNU = dict(SIGMA, dtangage=2.5, droulis=1.5)
ROTATION = (2, 3, 4)                     # indices de dlacet, dtangage, droulis
ETALEMENT_MIN = 0.50                     # étalement vertical du modèle projeté / nominal (refus des écrasements)
# la solution finale (affinée sur tous les segments) doit rester à moins de ces écarts de la solution validée sur B
# (mêmes tolérances que la stabilité) ; au-delà, elle n'a pas été validée et l'on garde la solution validée
PROCHE_POSITION = 1.0                    # m
PROCHE_ANGLE = 1.5                       # ° (lacet, tangage, roulis)


def proche(x, y):
    """Vrai si deux corrections (6 paramètres) sont dans le même bassin (PROCHE_POSITION, PROCHE_ANGLE)."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    return (math.hypot(x[0] - y[0], x[1] - y[1]) <= PROCHE_POSITION
            and float(np.max(np.abs(x[list(ROTATION)] - y[list(ROTATION)]))) <= PROCHE_ANGLE)


def bornes_porteur(porteur, sigma_xy):
    p = str(porteur)
    if p.startswith(("velo", "pieton")):
        b, s = BORNES_PORTEE, SIGMA_PORTEE
    elif p.startswith("inconnu"):
        b, s = BORNES_INCONNU, SIGMA_INCONNU
    else:
        b, s = BORNES, SIGMA
    sxy = min(sigma_xy, SIGMA_POSITION)
    return dict(b), dict(s, ds=sxy, dt=sxy)


# ------------------------------------------------------------------------------------------------ segments
def segments_photo(img, masque, cam0):
    """Segments rectilignes utiles à l'alignement : tableau (N, 5) x0, y0, x1, y1, longueur, et le compte des
    segments écartés par motif."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    g = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    seg = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(g)[0]
    ecart = {"courts": 0, "au_dessus_horizon": 0, "porteur": 0, "ombres": 0}
    if seg is None:
        return np.zeros((0, 5)), ecart
    seg = seg.reshape(-1, 4)
    L = np.hypot(seg[:, 2] - seg[:, 0], seg[:, 3] - seg[:, 1])
    ecart["courts"] = int((L < LONGUEUR_MIN).sum())
    seg, L = seg[L >= LONGUEUR_MIN], L[L >= LONGUEUR_MIN]
    if not len(seg):
        return np.zeros((0, 5)), ecart
    mil = (seg[:, :2] + seg[:, 2:]) / 2.0
    el = np.degrees(np.arcsin(np.clip(cam0.rayons(mil)[:, 2], -1, 1)))
    haut = el > ELEVATION_MAX
    ecart["au_dessus_horizon"] = int(haut.sum())
    iu = np.clip(mil[:, 0].astype(int), 0, cam0.W - 1)
    iv = np.clip(mil[:, 1].astype(int), 0, cam0.H - 1)
    port = ~masque[iv, iu] & ~haut
    ecart["porteur"] = int(port.sum())
    keep = ~haut & ~port
    seg, L = seg[keep], L[keep]
    b = cv2.GaussianBlur(a, (0, 0), 1.0) + 2.0
    d = (seg[:, 2:] - seg[:, :2]) / L[:, None]
    n = np.c_[-d[:, 1], d[:, 0]]
    ombre = np.zeros(len(seg), bool)
    for i, ((x0, y0, x1, y1), nn, ln) in enumerate(zip(seg, n, L)):
        f = np.linspace(0.15, 0.85, max(3, int(ln // 4)))
        Pm = np.c_[x0 + (x1 - x0) * f, y0 + (y1 - y0) * f]
        cotes = []
        for sg in (-1.0, 1.0):
            Q = np.round(Pm + sg * 4.0 * nn).astype(int)
            Q[:, 0] = np.clip(Q[:, 0], 0, a.shape[1] - 1)
            Q[:, 1] = np.clip(Q[:, 1], 0, a.shape[0] - 1)
            cotes.append(b[Q[:, 1], Q[:, 0]].mean(axis=0))
        c1, c2 = cotes
        bleu = math.log(c1[2] / c1[0]) - math.log(c2[2] / c2[0])
        ombre[i] = (bleu if c1.mean() < c2.mean() else -bleu) > SEUIL_OMBRE
    ecart["ombres"] = int(ombre.sum())
    return np.c_[seg[~ombre], L[~ombre]], ecart


def cartes_distance(segs, forme):
    """Carte des segments (H, W bool) et cartes de distance par classe d'orientation (tolérance ± 1 classe)."""
    H, W = forme
    cartes = np.zeros((N_ORIENT, H, W), np.uint8)
    bords = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1, _ in segs:
        th = math.atan2(y1 - y0, x1 - x0) % math.pi
        c = int(th / (math.pi / N_ORIENT)) % N_ORIENT
        p0, p1 = (int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1)))
        cv2.line(bords, p0, p1, 1, 1)
        for b in (c - 1, c, c + 1):
            cv2.line(cartes[b % N_ORIENT], p0, p1, 1, 1)
    dts = np.empty((N_ORIENT, H, W), np.float32)
    for b in range(N_ORIENT):
        dts[b] = cv2.distanceTransform((1 - cartes[b]), cv2.DIST_L2, 5) if cartes[b].any() else 1e4
    return bords > 0, dts


def contours_photo(img, masque, cam0):
    segs, ecart = segments_photo(img, masque, cam0)
    bords, dts = cartes_distance(segs, masque.shape)
    return bords, segs, ecart, dts


# ------------------------------------------------------------------------------------------------ alignement
class Alignement:
    """cam0 : caméra de départ (métadonnées, éventuellement redressée par les verticales) ; cam_meta : caméra des
    seules métadonnées (référence des mesures « avant » et de la validation)."""

    def __init__(self, cam0, P, T, typ, img, masque, porteur="inconnu_360", sigma_xy=4.0, modele=None, cam_meta=None):
        self.cam0 = cam0
        self.cam_meta = cam_meta or cam0
        # une caméra portée par une voiture reste sur la chaussée du modèle (contrainte souple, 0,8 m des rives) :
        # sans elle, quand la chaussée réelle est plus large que celle du modèle, l'affinage posait la voiture sur
        # l'accotement (essai S_M20, 22451897)
        # (seulement si la position GNSS est à moins de 3 m de cette chaussée : sinon la voiture roule sur une autre
        # voie, giratoire ou rue voisine, hors du modèle)
        self.modele = modele if (str(porteur).startswith("voiture") and modele is not None
                                 and modele.distance_chaussee(cam0.C[0], cam0.C[1]) <= 3.0) else None
        self.masque = masque
        self.bords, self.segments, self.ecart_segments, dts = contours_photo(img, masque, cam0)
        self.dts = {"tout": dts}
        for nom, sel in (("A", slice(0, None, 2)), ("B", slice(1, None, 2))):
            self.dts[nom] = cartes_distance(self.segments[sel], masque.shape)[1]
        uv, prof, devant = cam0.projeter(P)
        ok = devant & (prof >= PROF_MIN) & (prof <= PROF_MAX)
        ok &= (uv[:, 0] >= 0) & (uv[:, 0] < cam0.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam0.H)
        iu = np.clip(uv[:, 0].astype(int), 0, cam0.W - 1)
        iv = np.clip(uv[:, 1].astype(int), 0, cam0.H - 1)
        ok &= masque[iv, iu]
        self.P, self.T, self.typ = P[ok], T[ok], typ[ok]
        self.n = int(ok.sum())
        self.bornes, self.sigma = bornes_porteur(porteur, sigma_xy)

    def camera(self, x):
        return self.cam0.avec(*x)

    def distances(self, cam, jeu="tout"):
        """Distance (px) de chaque point au segment d'orientation voisine ; inf si hors image ou sur le porteur."""
        dts = self.dts[jeu]
        uv, _, devant = cam.projeter(self.P)
        uv2, _, dv2 = cam.projeter(self.P + 0.25 * self.T)
        d = uv2 - uv
        ang = np.arctan2(d[:, 1], d[:, 0]) % math.pi
        b = np.floor(ang / (math.pi / N_ORIENT)).astype(int) % N_ORIENT
        ok = devant & dv2 & (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)
        iu = np.clip(uv[:, 0].astype(int), 0, cam.W - 1)
        iv = np.clip(uv[:, 1].astype(int), 0, cam.H - 1)
        ok &= self.masque[iv, iu]
        out = np.full(len(self.P), np.inf)
        out[ok] = dts[b[ok], iv[ok], iu[ok]]
        return out

    def a_priori(self, x):
        return 0.5 * sum((x[i] / self.sigma[k]) ** 2 for i, k in enumerate(NOMS))

    def cout(self, x, tau, jeu="tout"):
        d = self.distances(self.camera(x), jeu)
        c = float(np.mean(np.minimum(d, tau) / tau)) if len(d) else 1.0
        garde = 100.0 * max(0.0, math.hypot(x[0], x[1]) - DEPLACEMENT_MAX) ** 2
        if self.modele is not None:
            dch = self.modele.distance_chaussee(self.cam0.C[0] + x[0], self.cam0.C[1] + x[1])
            garde += 0.5 * (dch / 0.3) ** 2
        return POIDS_DONNEES * c + self.a_priori(x) + garde

    def mesures(self, x, jeu="tout", cam=None):
        d = self.distances(cam if cam is not None else self.camera(x), jeu)
        if not len(d):
            return {"points": 0, "score_tau10": 1.0}
        fin = np.isfinite(d)
        return {"points": int(len(d)), "dans_image": round(float(fin.mean()), 4),
                "ecart_moyen_px": round(float(np.mean(np.minimum(d, 30.0))), 3),
                "ecart_median_px": round(float(np.median(np.minimum(d, 30.0))), 3),
                "recouvrement_3px": round(float(np.mean(d <= 3.0)), 4),
                "recouvrement_5px": round(float(np.mean(d <= 5.0)), 4),
                "score_tau10": round(float(np.mean(np.minimum(d, 10.0) / 10.0)), 4)}

    def _bornes(self):
        return [(-self.bornes[k], self.bornes[k]) for k in NOMS]

    def etalement(self, x):
        """Étalement vertical (écart interquartile des lignes d'image) des points du modèle projetés, rapporté à
        celui de la pose nominale : < ETALEMENT_MIN = solution dégénérée (le modèle écrasé dans une bande près de
        l'horizon, riche en segments horizontaux ; essai S_M27, 18e1dc39)."""
        def iqr(cam):
            uv, _, dv = cam.projeter(self.P)
            v = uv[dv, 1]
            return float(np.subtract(*np.percentile(v, [75, 25]))) if len(v) > 10 else 0.0
        e0 = iqr(self.cam0)
        return iqr(self.camera(x)) / e0 if e0 > 0 else 1.0

    def au_garde_fou(self, x):
        out = [k for i, k in enumerate(NOMS) if abs(x[i]) >= self.bornes[k] * 0.98]
        if math.hypot(x[0], x[1]) >= DEPLACEMENT_MAX * 0.98:
            out.append("deplacement")
        return out

    def _powell(self, x0, jeu, libres, taus=(40.0, 20.0, 10.0)):
        bornes = self._bornes()
        lo, hi = np.array([b[0] for b in bornes]), np.array([b[1] for b in bornes])
        x = np.clip(np.array(x0, dtype=np.float64), lo, hi)
        idx = list(libres)

        def plein(v):
            y = x.copy()
            y[idx] = v
            return y
        for tau in taus:
            r = minimize(lambda v: self.cout(plein(v), tau, jeu), x[idx], method="Powell",
                         bounds=[bornes[i] for i in idx], options={"xtol": 1e-3, "ftol": 1e-7, "maxfev": 1500})
            x = np.clip(plein(r.x), lo, hi)
        return x, self.cout(x, taus[-1], jeu)

    def _departs(self, jeu, libres):
        grille = []
        bt = self.bornes["dtangage"]
        lat = (-2.5, 0.0, 2.5) if 1 in libres else (0.0,)
        for dl in np.arange(-10.0, 10.01, 2.0):
            for dtg in np.arange(-bt, bt + 0.01, bt / 2.0):
                for dtt in lat:
                    x = np.array([0.0, dtt, dl, dtg, 0.0, 0.0])
                    grille.append((self.cout(x, 40.0, jeu), tuple(x)))
        grille.sort()
        return [np.zeros(6)] + [np.array(g[1]) for g in grille[:4]]

    def _optimiser(self, jeu, libres, departs_sup=()):
        res = []
        for x0 in list(departs_sup) + self._departs(jeu, libres):
            x, c = self._powell(x0, jeu, libres)
            res.append((c, tuple(np.round(x, 6))))
        res.sort()
        return np.array(res[0][1]), res[0][0]

    def emprise_verticale(self, x=None):
        """Écart interquartile des lignes d'image des points du modèle projetés, rapporté à la hauteur de l'image : une
        vue où le modèle n'occupe qu'une bande mince (vu en rasant, au loin) ne permet pas de juger l'alignement."""
        cam = self.cam0 if x is None else self.camera(x)
        uv, _, dv = cam.projeter(self.P)
        v = uv[dv, 1]
        return float(np.subtract(*np.percentile(v, [75, 25]))) / cam.H if len(v) > 10 else 0.0

    def _valider(self, x):
        b0, b1 = self.mesures(None, "B", cam=self.cam_meta), self.mesures(x, "B")
        return {"B_initial": b0, "B_apres_affinage_sur_A": b1,
                "amelioration_relative": round((b0["score_tau10"] - b1["score_tau10"]) / max(b0["score_tau10"], 1e-6), 4),
                "correction_sur_A": {k: round(float(v), 3) for k, v in zip(NOMS, x)},
                "etalement": round(self.etalement(x), 3), "au_garde_fou": self.au_garde_fou(x)}

    def affiner(self, seuil=0.03):
        """Trois niveaux, chacun validé sur la moitié B des segments (après affinage sur la moitié A pour les deux
        derniers), contre la pose des seules métadonnées :
        0. redressement (si la caméra de départ a été redressée par les verticales de la photo) : aucun paramètre
           ajusté sur le modèle ;
        1. orientation seule (lacet, tangage, roulis) ;
        2. pose complète (+ position, hauteur).
        Un niveau est retenu s'il améliore B de plus de `seuil`, sans garde-fou atteint ni écrasement du modèle ; on
        prend le niveau le plus simple sauf si un niveau plus riche valide mieux de 0,02 au moins (0,05 pour la pose
        complète, comparée à l'orientation seule même si celle-ci n'est pas retenue). La solution retenue est ensuite
        affinée localement sur tous les segments (mêmes paramètres libres) et n'est gardée que si elle reste proche
        de la solution validée (`proche`)."""
        if self.n < 30 or len(self.segments) < 4:
            return None
        tous = tuple(range(6))
        xa_rot, _ = self._optimiser("A", ROTATION)
        xa_tout, _ = self._optimiser("A", tous, departs_sup=(xa_rot,))
        redresse = self.cam0 is not self.cam_meta
        val = {"orientation": self._valider(xa_rot), "complete": self._valider(xa_tout)}
        if redresse:
            val["redressement"] = self._valider(np.zeros(6))
        cands = []
        for niv, x in (("redressement", np.zeros(6)), ("orientation", xa_rot), ("complete", xa_tout)):
            if niv not in val:
                continue
            v = val[niv]
            s_niv = max(seuil, SEUIL_REDRESSEMENT) if niv == "redressement" else seuil
            if v["amelioration_relative"] > s_niv and v["etalement"] >= ETALEMENT_MIN and not v["au_garde_fou"]:
                cands.append((niv, x, v["amelioration_relative"]))
        niveau, xa = None, None
        for niv, x, a_ in cands:                         # du plus simple au plus riche
            marge = MARGE_COMPLETE if niv == "complete" else 0.02
            ref = val[niveau]["amelioration_relative"] if niveau is not None else None
            if niv == "complete":
                # contrôle du 18/10/2026 : la pose complète doit valider nettement mieux que l'orientation seule
                # MÊME quand celle-ci n'a pas franchi le seuil (sinon + 0,037 contre + 0,024 passait : S_M24 93ccf5e5,
                # S_M27 47898337 — caméra déplacée pour un gain de validation de 0,01)
                o = val["orientation"]["amelioration_relative"]
                ref = o if ref is None else max(ref, o)
            if ref is None or a_ >= ref + marge:
                niveau, xa = niv, x
        val["niveau_retenu"] = niveau
        if niveau is None:
            return {"x": np.zeros(6), "niveau": None, "validation": val, "stabilite": []}
        if niveau == "redressement":
            return {"x": np.zeros(6), "cout": self.cout(np.zeros(6), 10.0), "niveau": niveau, "stabilite": [],
                    "validation": val}
        libres = tous if niveau == "complete" else ROTATION
        # affinage LOCAL de la solution validée sur tous les segments (contrôle du 18/10/2026 : l'ancienne recherche
        # globale « _optimiser('tout') » repartait de la grille et retenait souvent un autre minimum, jamais validé,
        # jusqu'à 8° de lacet de la solution validée : S_M20 053922ee, b098d25a) ; la solution affinée n'est gardée
        # que si elle reste dans le bassin de la solution validée
        xbest, cbest = self._powell(xa, "tout", libres, taus=(20.0, 10.0))
        if (self.etalement(xbest) < ETALEMENT_MIN or self.au_garde_fou(xbest)
                or not proche(xbest, xa)):
            xbest, cbest = xa, self.cout(xa, 10.0, "tout")       # sur tous les segments, la solution dérive : on garde A
        # stabilité : départs décalés (mesure ; une solution de coût moindre n'est prise que dans le même bassin)
        ecarts = []
        lo, hi = [b[0] for b in self._bornes()], [b[1] for b in self._bornes()]
        for pert in (np.array([1.5, -1.5, 2.0, 1.0, 0.0, 0.0]), np.array([-1.5, 1.5, -2.0, -1.0, 0.0, 0.0])):
            p = pert.copy()
            if niveau == "orientation":
                p[[0, 1, 5]] = 0.0
            x, c = self._powell(np.clip(xbest + p, lo, hi), "tout", libres, taus=(20.0, 10.0))
            ecarts.append((float(np.hypot(*(x[:2] - xbest[:2]))), float(abs(x[2] - xbest[2])), c))
            if (c < cbest - 1e-6 and self.etalement(x) >= ETALEMENT_MIN and not self.au_garde_fou(x)
                    and proche(x, xa)):
                cbest, xbest = c, x
        ecart_valide = {"position_m": round(float(np.hypot(*(xbest[:2] - xa[:2]))), 3),
                        "angle_deg": round(float(np.max(np.abs(xbest[list(ROTATION)] - xa[list(ROTATION)]))), 3)}
        val["ecart_solution_finale_a_la_validee"] = ecart_valide
        return {"x": xbest, "cout": cbest, "niveau": niveau, "stabilite": ecarts, "validation": val}


def confiance(m0, m1, x, n, stab, val, bornes, emprise=1.0):
    """Indice de confiance (0-1) et libellé : amélioration sur la moitié de segments non utilisée (validation) au niveau
    retenu, recouvrement final, nombre de points, stabilité, emprise verticale du modèle dans l'image (une bande mince
    ne prouve rien) ; « faible » si l'affinage est rejeté."""
    r1 = m1.get("recouvrement_3px", 0.0)
    gain = (m0["score_tau10"] - m1["score_tau10"]) / max(m0["score_tau10"], 1e-6)
    niveau = (val or {}).get("niveau_retenu")
    stable = (all(e[0] <= 1.0 and e[1] <= 1.5 for e in stab) if stab else niveau == "redressement")
    v = val[niveau]["amelioration_relative"] if niveau else 0.0
    f_val = float(np.clip(v / 0.15, 0.0, 1.0))
    f_emp = float(np.clip(emprise / 0.08, 0.0, 1.0))
    indice = (f_val * min(1.0, r1 / 0.35) * min(1.0, n / 400.0) * (1.0 if stable else 0.6) * f_emp
              * (1.0 if niveau == "complete" else 0.85))
    lib = "haute" if indice >= 0.5 else "moyenne" if indice >= 0.2 else "faible"
    return {"indice": round(float(indice), 3), "niveau": lib if niveau else "faible", "niveau_affinage": niveau,
            "gain_score_relatif": round(float(gain), 4), "validation_amelioration_relative": round(float(v), 4),
            "emprise_verticale_modele": round(float(emprise), 3), "stable": stable,
            "stabilite": [{"ecart_position_m": round(e[0], 2), "ecart_lacet_deg": round(e[1], 2)} for e in stab]}


def dessiner_points(img, cam, P, couleur, rayon=1):
    """Projette des points (N, 3) sur une copie de l'image (arêtes du modèle)."""
    a = np.asarray(img).copy()
    uv, prof, devant = cam.projeter(P)
    ok = devant & (prof >= 2.0) & (prof <= 60.0) & (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)
    for u, v in uv[ok].astype(int):
        cv2.circle(a, (int(u), int(v)), rayon, couleur, -1, lineType=cv2.LINE_AA)
    return a


def masque_vue(cam, porteur):
    return V.masque_porteur(cam, porteur)
