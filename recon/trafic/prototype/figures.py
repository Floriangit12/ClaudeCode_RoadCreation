"""Figures du rapport de prototype (matplotlib, PNG 1300 × 750 px au plus : lisibles sans réduction).

Couleurs (palette de référence validée du skill dataviz, ordre fixe) : bleu = notre modèle, orange = SUMO
Krauss, vert d'eau = SUMO EIDM ; trait plein = réglage par défaut, tirets = variante (« nos lois » pour
SUMO) ; noir = valeurs cibles sourcées.
"""
from __future__ import annotations

import numpy as np

C_MOD, C_KR, C_EI, C_REF, C_GRIS = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#898781"
STYLE_SUMO = {"krauss_defaut": (C_KR, "-"), "krauss_nos_lois": (C_KR, "--"), "eidm_defaut": (C_EI, "-"), "eidm_nos_lois": (C_EI, "--"),
              "krauss_nos_lois_asl": (C_KR, ":"), "krauss_nos_lois_ds": (C_KR, "-.")}
LIB_SUMO = {"krauss_defaut": "SUMO Krauss (défaut)", "krauss_nos_lois": "SUMO Krauss (nos lois)",
            "eidm_defaut": "SUMO EIDM (défaut)", "eidm_nos_lois": "SUMO EIDM (nos lois)",
            "krauss_nos_lois_asl": "SUMO Krauss (nos lois, actionStepLength = TPR)",
            "krauss_nos_lois_ds": "SUMO Krauss (nos lois, driverstate)"}


def plt_():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 100, "font.size": 10, "axes.grid": True,
                         "grid.color": "#e1e0d9", "grid.linewidth": 0.6, "axes.edgecolor": "#c3c2b7",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 11,
                         "legend.fontsize": 8, "legend.frameon": False})
    return plt


def _sauver(fig, chemin):
    fig.tight_layout()
    fig.savefig(chemin)
    import matplotlib.pyplot as plt
    plt.close(fig)


def fig_s1(R, cibles, chemin):
    plt = plt_()
    fig, axes = plt.subplots(1, 2, figsize=(13, 7.5))
    ax = axes[0]
    rg = np.arange(1, 21)
    ax.plot(rg, R["modele"]["tiv_moyen_par_rang_s"], color=C_MOD, lw=2.2, marker="o", ms=5, label="notre modèle")
    for c, r in R["sumo"].items():
        col, ls = STYLE_SUMO[c]
        ax.plot(rg, r["tiv_moyen_par_rang_s"], color=col, ls=ls, lw=1.6, label=LIB_SUMO[c])
    s = cibles["salles_tiv"]
    ax.plot([1, 2, 3], [s["rang1"], s["rang2"], s["rang3"]], "s", color=C_REF, ms=8, label="Salles 2020 fig. 10 (drone, Stuttgart)")
    ax.plot([4, 9], [s["rang4_plus"][0]] * 2, color=C_REF, lw=1)
    ax.plot([4, 9], [s["rang4_plus"][1]] * 2, color=C_REF, lw=1)
    ax.fill_between([4, 9], s["rang4_plus"][0], s["rang4_plus"][1], color=C_REF, alpha=0.08)
    ax.axhline(2.0, color=C_REF, ls=":", lw=1.2)
    ax.text(20, 2.03, "1 800 uvpd/h = 2,0 s (Certu Feux 2010 p. 34)", ha="right", va="bottom", fontsize=8)
    ax.axvspan(4.5, 12.5, color=C_GRIS, alpha=0.07)
    ax.set_xlabel("rang dans la file")
    ax.set_ylabel("temps intervéhiculaire au passage de la ligne (s) ; rang 1 : depuis le vert")
    ax.set_title("S1 — décharge d'une file de 20 VL au vert (moyenne par rang)")
    ax.set_xticks(rg)
    ax.set_ylim(0, 4.5)
    ax.legend(loc="upper right")
    ax = axes[1]
    ax.plot(rg, R["modele"]["pic_acc_moyen_par_rang_ms2"], color=C_MOD, lw=2.2, marker="o", ms=5, label="notre modèle")
    for c, r in R["sumo"].items():
        col, ls = STYLE_SUMO[c]
        ax.plot(rg, r["pic_acc_moyen_par_rang_ms2"], color=col, ls=ls, lw=1.6, label=LIB_SUMO[c])
    p = cibles["salles_pic"]
    ax.plot([1, 2, 3], [p["rang1"], p["rang2"], p["rang3"]], "s", color=C_REF, ms=8, label="Salles 2020 fig. 8a (moyenne)")
    ax.plot([4, 9], [p["rang4_9"]] * 2, color=C_REF, lw=2)
    et = R["modele"].get("pic_acc_ecart_type_par_rang_ms2")
    if et:
        ax.plot(rg, et, color=C_MOD, lw=1.4, ls=":", marker=".", label="notre modèle : écart-type du pic par rang")
        lo, hi = p["ecart_type"]
        ax.fill_between([0.5, 20.5], lo, hi, color=C_REF, alpha=0.07, lw=0)
        ax.text(20, hi + 0.04, f"écart-type mesuré {lo:.2f}-{hi:.2f} m/s² (Salles fig. 8b)".replace(".", ","), ha="right", fontsize=8)
    ax.set_xlabel("rang dans la file")
    ax.set_ylabel("pic d'accélération : moyenne et écart-type (m/s²)")
    ax.set_title("Pic d'accélération au démarrage par rang")
    ax.set_xticks(rg)
    ax.set_ylim(0, 4.5)
    ax.legend(loc="upper right")
    _sauver(fig, chemin)


def fig_s1b(R, cibles, chemin):
    plt = plt_()
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    ax = axes[0]
    x = np.linspace(0, 8, 200)
    lg = cibles["logistique"]
    ax.plot(x, 1 / (1 + np.exp(-(x - lg["t50"]) / lg["echelle"])), color=C_REF, lw=2,
            label="loi logistique du projet par les 2 points FHWA 2008 (10 % à 2,5 s, 90 % à 5,5 s ; approches > 35 mph)")
    for cle, ls, lab in (("sans_H11", "-", "notre modèle (seuil FHWA seul)"), ("avec_H11", "--", "notre modèle avec l'option H-11")):
        r = R[cle]["P_arret_par_TTL"]
        ax.plot(r["centres_s"], r["P"], color=C_MOD, ls=ls, lw=2, marker="o", ms=4, label=lab)
    ax.axvline(3.0, color=C_GRIS, ls=":", lw=1)
    ax.text(3.05, 0.02, "jaune 3 s", fontsize=8, color="#52514e")
    ax.set_xlabel("temps jusqu'à la ligne au début du jaune, TTL (s)")
    ax.set_ylabel("part des conducteurs qui s'arrêtent")
    ax.set_title("S1b — décision au jaune (arrivées libres, artère à 50 km/h)")
    ax.legend(loc="upper left")
    ax = axes[1]
    for cle, ls, lab in (("sans_H11", "-", "seuil FHWA seul"), ("avec_H11", "--", "avec H-11")):
        d = np.sort(R[cle]["_decel"])
        if d.size:
            ax.plot(d, np.arange(1, d.size + 1) / d.size, color=C_MOD, ls=ls, lw=2, label=f"notre modèle, {lab}")
    ax.axvline(3.05, color=C_REF, lw=1.5, label="3,05 m/s² (ITE, FHWA p. 5-13)")
    ax.axvline(4.5, color=C_KR, lw=1.2, label="SUMO Krauss 0,1 s : 4,5 m/s² pour 100 % (volet 03, S2)")
    ax.set_xlabel("décélération maximale des véhicules qui s'arrêtent (m/s²)")
    ax.set_ylabel("fonction de répartition")
    ax.set_title("Décélération à l'arrêt au jaune")
    ax.set_xlim(0, 8)
    ax.legend(loc="lower right")
    _sauver(fig, chemin)


def fig_s2(R, cibles, chemin):
    plt = plt_()
    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    ax = axes[0]
    rg = np.arange(1, 11)
    for (mode, dm), ls in ((("markkula", "6.68"), "-"), (("tpr", "6.68"), "--"), (("markkula", "4.0"), "-."), (("tpr", "4.0"), ":")):
        r = R["modele"][f"{mode}_{dm}"]["rangs"]
        ax.plot(rg, [100 * (r[k]["taux_collision_primaire_meneur_intact"] or 0) for k in rg], color=C_MOD, ls=ls, lw=2, marker="o", ms=4,
                label=f"notre modèle, {'Markkula' if mode == 'markkula' else 'TPR NCHRP + décél. équivalente'}, meneur {dm.replace('.', ',')} m/s²")
    for c, r in R["sumo_6.68"].items():
        col, ls = STYLE_SUMO[c]
        ax.plot(rg, [100 * (r["rangs"][k]["taux_collision_brut"] or 0) for k in rg], color=col, ls=ls, lw=1.5, label=f"{LIB_SUMO[c]}, 6,68 m/s²")
    ax.set_xlabel("rang derrière le meneur qui freine")
    ax.set_ylabel("collisions primaires, meneur intact (%) ; SUMO : collisions brutes")
    ax.set_title("S2 — freinage du meneur d'un peloton à 60 km/h")
    ax.set_xticks(rg)
    ax.legend(loc="upper right", fontsize=7)
    ax = axes[1]
    x = np.linspace(0.01, 4, 300)
    tp = cibles["tpr_signal"]
    from scipy import stats
    ax.plot(x, stats.norm.cdf((np.log(x) - tp["mu_log"]) / tp["sigma_log"]), color=C_REF, lw=2,
            label="TPR « signal inattendu » NCHRP 400 tab. 13 (loi du volet 02)")
    for mode, ls in (("markkula", "-"), ("tpr", "--")):
        d = np.sort(R["modele"][f"{mode}_6.68"]["_delais_rang1"])
        ax.plot(d, np.arange(1, d.size + 1) / d.size, color=C_MOD, ls=ls, lw=2,
                label=f"notre modèle, {'Markkula' if mode == 'markkula' else 'TPR'} : feux stop du rang 1 - feux stop du meneur")
    for c in ("krauss_defaut", "eidm_defaut", "eidm_nos_lois", "krauss_nos_lois_asl"):
        d = np.sort(R["_sumo_delais"].get(c, []))
        if len(d):
            col, ls = STYLE_SUMO[c]
            ax.plot(d, np.arange(1, d.size + 1) / d.size, color=col, ls=ls, lw=1.5, label=LIB_SUMO[c])
    ax.set_xlabel("délai de réponse au freinage du meneur (s)")
    ax.set_ylabel("fonction de répartition")
    ax.set_title("Délai feux stop meneur → rang 1 (seuil de détection 1,3 m/s², convention)")
    ax.set_xlim(0, 4)
    ax.legend(loc="lower right", fontsize=7)
    _sauver(fig, chemin)


def fig_s3(R, cibles, chemin):
    plt = plt_()
    from scipy import stats
    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    ax = axes[0]
    x = np.linspace(0.5, 25, 400)
    series = [("modele", C_MOD, "-", "notre modèle")] + [(c, *STYLE_SUMO[c], LIB_SUMO[c].replace("nos lois", "nos lois, impatience 0,5")) for c in R["sumo"]]
    for cle, col, ls, lab in series:
        r = R["modele"] if cle == "modele" else R["sumo"][cle]
        m = r.get("creneau_critique_mle_arretes_depuis_arret_point_conflit") or r.get("creneau_critique_mle_arretes")
        if m:
            ax.plot(x, stats.norm.cdf((np.log(x) - m["mu_log"]) / m["sigma_log"]), color=col, ls=ls, lw=2,
                    label=f"{lab} : {m['moyenne_s']:.1f} ± {m['ecart_type_s']:.1f} s (n = {m['n_conducteurs']})")
    ax.axvline(5.0, color=C_REF, lw=2, label="t_c Certu (CU 2010 p. 93) : 5 s, paramètre de méthode de capacité (norme)")
    ax.axvspan(5.0 - 0.5, 5.0 + 0.5, color=C_REF, alpha=0.06)
    ax.set_xlabel("créneau critique (s)")
    ax.set_ylabel("fonction de répartition (loi lognormale par maximum de vraisemblance)")
    ax.set_title("S3 — créneau critique, arrêtés au STOP, depuis l'arrêt, au point de conflit (Troutbeck)")
    ax.set_xlim(0, 25)
    ax.legend(loc="lower right", fontsize=7)
    ax = axes[1]
    noms = ["arrêt complet\n(v < 0,1 m/s)", "arrêt glissé\n(0,1-3 m/s)", "pas d'arrêt\n(≥ 3 m/s)"]
    cib = [cibles["stop"]["arret_complet"], cibles["stop"]["arret_glisse"], cibles["stop"]["pas_d_arret"]]
    larg = 0.16
    xs = np.arange(3)
    ax.bar(xs - 2 * larg, [100 * c for c in cib], larg, color="#c3c2b7", edgecolor=C_REF, label="Vaughan 2006 (Ontario, confiance faible)")
    for k, (cle, col, ls, lab) in enumerate(series[:3] + series[3:]):
        r = R["modele"] if cle == "modele" else R["sumo"][cle]
        al = r.get("arrivees_libres")
        if not al:
            continue
        vals = [al["part_arret_complet_v_inf_0_1"], al["part_glisse_0_1_a_3"], al["part_sans_arret_sup_3"]]
        ax.bar(xs + (k - 1) * larg, [100 * v for v in vals], larg, color=col, alpha=1.0 if ls == "-" else 0.55,
               hatch=None if ls == "-" else "//", edgecolor="white", label=f"{lab} (n = {al['n']})")
    ax.set_xticks(xs, noms)
    ax.set_ylabel("part des arrivées libres (%)")
    ax.set_title("Comportement au STOP, vitesse minimale dans les 3 derniers mètres")
    ax.legend(loc="upper right", fontsize=7)
    _sauver(fig, chemin)


def fig_profils(R, cibles, chemin, titre, xlab, zone, ylim, cible_texte):
    """Profils de vitesse médians (et P15-P85 du modèle) le long de s, pour S4 et S5."""
    plt = plt_()
    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    ax = axes[0]
    s, med, p15, p85 = R["profil_modele"]
    ax.fill_between(s, p15, p85, color=C_MOD, alpha=0.15, lw=0, label="notre modèle, P15-P85")
    ax.plot(s, med, color=C_MOD, lw=2.2, label="notre modèle, médiane")
    variantes = []
    for c in list(R["profils_sumo"]) + list(R["v_mesure_sumo"]):
        if "|" in c and c.split("|")[1] not in variantes:
            variantes.append(c.split("|")[1])

    def style(c):
        col, ls = STYLE_SUMO[c.split("|")[0]]
        if "|" in c and variantes.index(c.split("|")[1]) == 1:      # seconde variante de réseau : pointillés
            ls = "-." if ls == "-" else ":"
        return col, ls
    for c, (s2, m2) in R["profils_sumo"].items():
        col, ls = style(c)
        ax.plot(s2, m2, color=col, ls=ls, lw=1.5, label=LIB_SUMO[c.split("|")[0]] + (" — " + c.split("|")[1] if "|" in c else ""))
    ax.axvspan(zone[0], zone[1], color=C_GRIS, alpha=0.12)
    for y, lab in cibles.get("lignes", []):
        ax.axhline(y, color=C_REF, ls=":", lw=1.2)
        ax.text(s[0] + 5, y + 0.6, lab, fontsize=8)
    ax.set_xlabel(xlab)
    ax.set_ylabel("vitesse (km/h)")
    ax.set_ylim(*ylim)
    ax.set_title(titre)
    ax.legend(loc="lower left", fontsize=7)
    ax = axes[1]
    v = np.sort(R["v_mesure_modele"])
    ax.plot(v, np.arange(1, v.size + 1) / v.size, color=C_MOD, lw=2.2, label="notre modèle")
    if "mesure_variante" in cibles:
        vb, lab = cibles["mesure_variante"]
        vb = np.sort(vb[np.isfinite(vb)])
        ax.plot(vb, np.arange(1, vb.size + 1) / vb.size, color=C_MOD, lw=1.6, ls="--", label=lab)
    for c, vv in R["v_mesure_sumo"].items():
        vv = np.sort(vv)
        col, ls = style(c)
        ax.plot(vv, np.arange(1, vv.size + 1) / vv.size, color=col, ls=ls, lw=1.5,
                label=LIB_SUMO[c.split("|")[0]] + (" — " + c.split("|")[1] if "|" in c else ""))
    if "loi_cible" in cibles:
        m, sd, lab = cibles["loi_cible"]
        x = np.linspace(ylim[0], ylim[1], 300)
        from scipy import stats
        ax.plot(x, stats.norm.cdf(x, m, sd), color=C_REF, lw=2, label=lab)
    if "loi_cible_2" in cibles:
        m, sd, lab = cibles["loi_cible_2"]
        x = np.linspace(ylim[0], ylim[1], 300)
        from scipy import stats
        ax.plot(x, stats.norm.cdf(x, m, sd), color=C_REF, lw=1.4, ls="--", label=lab)
    for xv, lab in cibles.get("verticales", []):
        ax.axvline(xv, color=C_REF, ls="--", lw=1.2)
        ax.text(xv + 0.4, 0.04, lab, fontsize=8, rotation=90, va="bottom")
    ax.axhline(0.85, color=C_GRIS, lw=0.8)
    ax.set_xlabel(cible_texte)
    ax.set_ylabel("fonction de répartition")
    ax.set_xlim(*ylim)
    ax.legend(loc="lower right", fontsize=7)
    _sauver(fig, chemin)
