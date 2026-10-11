"""Planches de revue 2022 | 2024 | 2025 par zone de 75 m (grille 4 x 4 sur l'emprise)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa

out = PLANCHES / "revue_75m"
out.mkdir(parents=True, exist_ok=True)
noms = "ABCD"
for i, x0 in enumerate((-150, -75, 0, 75)):
    for j, y1 in enumerate((150, 75, 0, -75)):
        nom = f"{noms[i]}{j + 1}"
        if len(sys.argv) > 1 and nom not in sys.argv[1:]:
            continue
        b = boite_locale(x0, y1 - 75, x0 + 75, y1)
        pans = [Vue(k, b, 600).grille(5, 25).im for k in ("2022", "2024", "2025")]
        assembler(pans, f"zone {nom} : local x {x0:+d}..{x0 + 75:+d}, y {y1 - 75:+d}..{y1:+d} (grille 5 m) : PCRS 2022 | IGN 2024 | Pléiades 2025").save(out / f"zone_{nom}.jpg", quality=88)
        print(nom)
