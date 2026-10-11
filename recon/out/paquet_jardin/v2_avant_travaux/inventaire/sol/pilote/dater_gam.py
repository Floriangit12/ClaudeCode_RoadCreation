"""Datation tronçon par tronçon des bordures du levé GAM (SOL_BORDURE = etat_2026, identiques) et du PCRS 2019
(et, à titre indicatif, des caniveaux et limites de revêtement GAM : pour ces lignes à niveau, seule l'arête
sur les orthos est probante).

Pour chaque échantillon (pas 0,5 m) d'une ligne, preuves indépendantes de l'existence avant travaux :
  - R21 : crête de pente LiDAR 2021 (raster pente 15 cm, palette décodée) à ± 0,30 m de la ligne ;
  - H21 : marche du MNT LiDAR 2021 en JPEG décodé (profil perpendiculaire, médianes à 0,3–0,9 m de part et
    d'autre) et, hors zones modifiées en 2025, marche de la heightmap v1 (même LiDAR, 16 bits) ;
  - E22 : arête de luminance sur l'ortho PCRS 2022 5 cm à ± 0,15 m (rapport au gradient médian du profil) ;
  - E24 : même test sur la BD ORTHO 2024 (20 cm, recalée).
Classes par échantillon :
  relief_2021        (R21 ou H21 ≥ 0,05 m) et (E22 ou ortho masquée) -> bordure existante en 2021 (vue mesurable)
  relief_seul        relief 2021 sans arête sur l'ortho 2022 -> douteux (crête voisine, ancien îlot à < 0,3 m)
  arasee_visible     sans relief, arête E22         -> bordure à niveau / bateau existant en 2022
  apparue_2022_2024  ni relief ni E22, mais E24     -> posée entre 05/2022 et 08/2024 (constructions)
  absente_avant      ni relief ni E22 ni E24        -> postérieure au 09/08/2024 (travaux 2025) ou invisible
  masquee            ortho 2022 masquée (canopée, ombre) et pas de relief -> indéterminée
  terrain_remanie_2021  relief seulement dans un terrain accidenté en 2021 (chantier, talus : crête de pente sur
                     plus de 45 % d'un profil de ± 1,5 m) sans arête 2022 -> la crête ne prouve pas la bordure
Sorties : ../datation/gam_bordures_datation.geojson (L93, un trait par tronçon homogène),
          ../datation/datation_resume.json
Usage : python -I dater_gam.py
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

import commun_sol as C
from dtm_jpg import MNT2021Jpg

PAS = 0.5
SEUIL_PENTE = 0.80          # rouge de la palette
SEUIL_MARCHE = 0.05
SEUIL_ARETE = 2.5           # rapport gradient au centre / gradient médian du profil
SEUIL_ARETE_ABS = 6.0       # niveaux de luminance par 5 cm


def secteur(x, y):
    if np.hypot(x - 0.0, y + 5.0) < 40.0:
        return "coeur"
    if (y < 0.7 * x - 8.0) and (x > 26.0 + (-18.0 - y) * 0.136):
        return "est_constructions"
    return "autres"


def profils(src, P, N, offs):
    Q = P[:, None, :] + offs[None, :, None] * N[:, None, :]
    return Q


def main():
    R = C.sources_raster()
    jpg = MNT2021Jpg()
    hm = C.Heightmap()
    zm = C.ZonesModifiees()
    sorties = C.SORTIE / "datation"
    sorties.mkdir(exist_ok=True)
    jeux = [("gam", C.charger_lignes(C.SITE / "vector/gam_topo_sol_bordure_lin.geojson", wgs=True)),
            ("pcrs2019", C.charger_lignes(C.SITE / "vector/gam_limite_voirie_pcrs.geojson", wgs=True,
                                          filtre=lambda p: "Bordure" in (p.get("calque") or ""))),
            ("gam_caniveau", C.charger_lignes(C.SITE / "vector/gam_topo_sol_caniveau_lin.geojson", wgs=True)),
            ("gam_limite_revetement", C.charger_lignes(C.SITE / "vector/gam_topo_sol_limite_revetement_lin.geojson", wgs=True))]
    feats, stats = [], {}
    o_r = np.arange(-0.30, 0.3001, 0.075)
    o_h = np.r_[-np.arange(0.3, 0.91, 0.1)[::-1], np.arange(0.3, 0.91, 0.1)]
    o_e = np.arange(-0.40, 0.4001, 0.025)
    o_e24 = np.arange(-0.80, 0.8001, 0.10)
    for nom, lignes in jeux:
        cpt_m = defaultdict(lambda: Counter())
        for idx, props, P, _ in lignes:
            if len(P) < 2:
                continue
            Q, s, T = C.reechantillonner(P, PAS)
            if len(Q) == 0:
                continue
            Nn = np.c_[-T[:, 1], T[:, 0]]
            # R21
            G = Q[:, None, :] + o_r[None, :, None] * Nn[:, None, :]
            pn = C.pente_norm(R["pente2021"].echantillonner(G[..., 0] + C.O[0], G[..., 1] + C.O[1]))
            r21 = pn.max(1)
            G = Q[:, None, :] + np.arange(-1.5, 1.501, 0.15)[None, :, None] * Nn[:, None, :]
            rug = (C.pente_norm(R["pente2021"].echantillonner(G[..., 0] + C.O[0], G[..., 1] + C.O[1])) >= SEUIL_PENTE).mean(1)
            # H21 (JPEG décodé et heightmap)
            G = Q[:, None, :] + o_h[None, :, None] * Nn[:, None, :]
            zj = jpg(G[..., 0] + C.O[0], G[..., 1] + C.O[1])
            k = len(o_h) // 2
            mj = np.abs(np.median(zj[:, k:], 1) - np.median(zj[:, :k], 1))
            zh = hm(G[..., 0] + C.O[0], G[..., 1] + C.O[1])
            mh = np.abs(np.median(zh[:, k:], 1) - np.median(zh[:, :k], 1))
            cz = zm(G[..., 0], G[..., 1])
            hm_ok = (cz == 0).all(1)
            # E22
            G = Q[:, None, :] + o_e[None, :, None] * Nn[:, None, :]
            rgb = R["ortho2022"].echantillonner(G[..., 0] + C.O[0], G[..., 1] + C.O[1])
            L = C.luminance(rgb)
            Ls = (np.roll(L, 1, 1) + L + np.roll(L, -1, 1)) / 3
            g = np.abs(np.diff(Ls[:, 1:-1], axis=1)) * 2      # par 5 cm
            c = g.shape[1] // 2
            gc = g[:, c - 6:c + 6].max(1)
            gm = np.median(g, 1) + 0.5
            e22 = (gc >= SEUIL_ARETE_ABS) & (gc / gm >= SEUIL_ARETE)
            vert = (rgb[..., 1].astype(float) - (rgb[..., 0].astype(float) + rgb[..., 2]) / 2).mean(1)
            masque = (L.mean(1) < 75) | (vert > 18)
            # E24
            G = Q[:, None, :] + o_e24[None, :, None] * Nn[:, None, :]
            L24 = C.luminance(R["ortho2024"].echantillonner(G[..., 0] + C.O[0], G[..., 1] + C.O[1]))
            g24 = np.abs(np.diff(L24, axis=1))
            c24 = g24.shape[1] // 2
            e24 = (g24[:, c24 - 3:c24 + 3].max(1) >= 8) & (g24[:, c24 - 3:c24 + 3].max(1) / (np.median(g24, 1) + 0.5) >= 2.0)
            relief = (r21 >= SEUIL_PENTE) | (mj >= SEUIL_MARCHE) | (hm_ok & (mh >= SEUIL_MARCHE))
            cl = np.where(relief & (rug > 0.45) & ~e22, "terrain_remanie_2021",
                          np.where(relief & (e22 | masque), "relief_2021", np.where(relief, "relief_seul",
                          np.where(e22, "arasee_visible",
                                   np.where(masque, "masquee",
                                            np.where(e24, "apparue_2022_2024", "absente_avant"))))))
            # lissage des classes (vote sur 5 échantillons = 2,5 m)
            cl2 = cl.copy()
            for i in range(len(cl)):
                w = Counter(cl[max(0, i - 2):i + 3])
                cl2[i] = w.most_common(1)[0][0]
            sec = [secteur(*q) for q in Q]
            for c_, s_ in zip(cl2, sec):
                cpt_m[s_][c_] += PAS
            # tronçons homogènes
            debut = 0
            for i in range(1, len(cl2) + 1):
                if i == len(cl2) or cl2[i] != cl2[debut]:
                    a, b = debut, i
                    pts = Q[a:b]
                    if len(pts) == 1:
                        pts = np.r_[pts - T[a] * PAS / 2, pts + T[a] * PAS / 2]
                    feats.append({"type": "Feature", "properties": {
                        "source": nom, "indice": idx, "classe": str(cl2[a]), "secteur": sec[a],
                        "longueur_m": round(PAS * (b - a), 2),
                        "pente21_max_p50": round(float(np.median(r21[a:b])), 2),
                        "marche_jpg21_p50_m": round(float(np.median(mj[a:b])), 3),
                        "marche_hm21_p50_m": round(float(np.median(mh[a:b][hm_ok[a:b]])), 3) if hm_ok[a:b].any() else None,
                        "arete22_frac": round(float(e22[a:b].mean()), 2), "arete24_frac": round(float(e24[a:b].mean()), 2),
                        "rugosite21_p50": round(float(np.median(rug[a:b])), 2)},
                        "geometry": {"type": "LineString", "coordinates": np.round(pts + C.O, 3).tolist()}})
                    debut = i
        stats[nom] = {s_: {str(k): round(v, 1) for k, v in sorted(c_.items())} for s_, c_ in sorted(cpt_m.items())}
    gj = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
          "features": feats}
    C.ecrire_json(sorties / "gam_bordures_datation.geojson", gj)
    C.ecrire_json(sorties / "datation_resume.json", {"longueurs_m_par_source_secteur_classe": stats,
                                                     "seuils": {"pente_norm": SEUIL_PENTE, "marche_m": SEUIL_MARCHE,
                                                                "arete_rapport": SEUIL_ARETE, "arete_abs": SEUIL_ARETE_ABS},
                                                     "pas_m": PAS})
    print(stats)


if __name__ == "__main__":
    main()
