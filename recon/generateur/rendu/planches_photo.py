"""Planches rendu | photo (correction après contrôle, PLAN_GENERATEUR § 5.2) : un fichier par paire et par moitié,
panneaux recadrés à la résolution native (aucune réduction), sous recon/out/generateur/<scène>/photos_non_versionnees/
planches/ (CLAUDE.md : photos de tiers jamais versionnées ni diffusées).

    python recon/generateur/rendu/planches_photo.py [SCENE ...]

Paires : vues calées sur les tuiles des photos (scènes de Meylan : même champ et même tangage que la vue « vise » de la
photo, position estimée) et cas semblables du catalogue (mêmes recadrages que la relecture adverse, tmp/verif/v09).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEPOT = Path(__file__).resolve().parents[3]
OUT = DEPOT / "recon" / "out" / "generateur"
PH = Path(r"D:\DocRoute\13_Observations_Panoramax_Isere\photos_tiers_locales\photos_non_versionnees")
HT = 32

# (scène, rendu (nom), photo, légende) : vues calées (moitiés gauche et droite, 546 × 1060 chacune)
CALEES = [
    ("S_M24", "photo_f877235a", PH / "M24_ilot_granier/vise_f877235a_centre_t-12.png",
     "M24 av. du Granier, Meylan (Panoramax f877235a, 12/01/2025, CC-BY-SA icluf)"),
    ("S_M24", "photo_9badc00e", PH / "M24_ilot_granier/vise_9badc00e_centre_t-12.png",
     "M24 av. du Granier, Meylan (Panoramax 9badc00e, 12/01/2025, CC-BY-SA icluf)"),
    ("S_M27", "photo_176f9ab0", PH / "M27_tpc_verdun/vise_176f9ab0_centre_t-12.png",
     "M27 av. de Verdun, Meylan (Panoramax 176f9ab0, 18/05/2025, CC-BY-SA Eric S)"),
    ("S_M20", "photo_30b80a7b", PH / "M20_stop_chamechaude/vise_30b80a7b_centre_t-12.png",
     "M20 av. de Chamechaude, Meylan (Panoramax 30b80a7b, 28/07/2026, etalab-2.0)"),
]
# cas semblables du catalogue (recadrages natifs 546 × 728 de la relecture adverse)
SEMBLABLES = [
    ("S08", "detail", (1000, 270), PH / "M24_ilot_granier/vise_9badc00e_centre_t-12.png", (273, 300),
     "passage piéton + abaissé + BEV ; M24 av. du Granier (Panoramax 9badc00e, CC-BY-SA icluf)"),
    ("S10", "cible_caniveau_plateau", (420, 26), PH / "I10_ilot_crolles/vise_0b351460_centre_t-12.png", (450, 250),
     "passage sur plateau ; I10 RD10 Crolles (Panoramax 0b351460)"),
    ("S06", "conducteur", (527, 136), PH / "I11_tpc_crolles/vise_25997f74_centre_t-12.png", (300, 300),
     "terre-plein central engazonné planté ; I11 Crolles (Panoramax 25997f74)"),
    ("S03", "detail", (450, 100), PH / "M34_alignement_granier/vise_51a741c3_centre_t-05.png", (420, 300),
     "alignement d'arbres et bordures ; M34 av. du Granier (Panoramax 51a741c3, CC-BY-SA icluf)"),
    ("S02", "conducteur", (527, 136), PH / "M20_stop_chamechaude/vise_30b80a7b_centre_t-12.png", (273, 250),
     "rue 1+1 ; M20 av. de Chamechaude (Panoramax 30b80a7b, etalab-2.0)"),
    ("S05", "pieton", (527, 136), PH / "M30_chronovelo_verdun_ouest/vise_9e61f41f_centre_t-12.png", (273, 300),
     "piste et trottoir ; M30 av. de Verdun ouest (Panoramax 9e61f41f)"),
    ("S01", "conducteur", (527, 136), PH / "M27_tpc_verdun/vise_176f9ab0_centre_t-12.png", (273, 200),
     "enrobé, marquage, abords ; M27 av. de Verdun (Panoramax 176f9ab0, CC-BY-SA Eric S)"),
]


def _police(t=15):
    for f in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, t)
    return ImageFont.load_default()


def _recadrer(src, x, y, w, h):
    im = Image.open(src).convert("RGB")
    x = max(0, min(x, im.width - w))
    y = max(0, min(y, im.height - h))
    return im.crop((x, y, x + w, y + h)), (x, y)


def planche(a, b, titre, dst):
    W = a.width + b.width
    pl = Image.new("RGB", (W, max(a.height, b.height) + HT), (24, 24, 28))
    pl.paste(a, (0, HT))
    pl.paste(b, (a.width, HT))
    ImageDraw.Draw(pl).text((8, 8), titre[:170], fill=(230, 230, 230), font=_police())
    dst.parent.mkdir(parents=True, exist_ok=True)
    pl.save(dst)
    return dst


def main(scenes=None):
    out = []
    for sc, vue, photo, leg in CALEES:
        if scenes and sc not in scenes:
            continue
        rendu = OUT / sc / "rendus" / f"{vue}.png"
        if not rendu.exists() or not photo.exists():
            continue
        dos = OUT / sc / "photos_non_versionnees" / "planches"
        for moitie, x in (("gauche", 0), ("droite", 546)):
            a, _ = _recadrer(rendu, x, 16, 546, 1060)
            b, _ = _recadrer(photo, x, 16, 546, 1060)
            out.append(planche(a, b, f"{sc} rendu {vue} (natif, x {x}-{x + 546}) | photo : {leg}",
                               dos / f"planche_{sc}_{vue}_{moitie}.png"))
    for sc, vue, xr, photo, xp, leg in SEMBLABLES:
        if scenes and sc not in scenes:
            continue
        rendu = OUT / sc / "rendus" / f"{vue}.png"
        if not rendu.exists() or not photo.exists():
            continue
        a, ba = _recadrer(rendu, xr[0], xr[1], 546, 728)
        b, bb = _recadrer(photo, xp[0], xp[1], 546, 728)
        dos = OUT / sc / "photos_non_versionnees" / "planches"
        out.append(planche(a, b, f"{sc} rendu {vue} (recadrage natif {ba}) | photo : {leg}",
                           dos / f"planche_{sc}_{photo.parent.name.split('_')[0]}.png"))
    for f in out:
        print(f, Image.open(f).size)
    return out


if __name__ == "__main__":
    main(sys.argv[1:] or None)
