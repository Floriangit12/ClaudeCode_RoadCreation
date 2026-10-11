"""Vue d'ensemble du site aux trois dates (PCRS 2022 | IGN 2024 | Pléiades 2025) + SPOT annuels."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_chg import *  # noqa

b = OR.BBOX
pans = [Vue(k, b, 700).grille(10, 50).im for k in ("2022", "2024", "2025")]
assembler(pans, "Site Paquet Jardin (local -150..+150 m) : 2022 | 2024 | 2025 (recalés sur le PCRS)").save(PLANCHES / "_ensemble_2022_2024_2025.png")
bb = boite_locale(-200, -200, 200, 200)
pans = [Vue(k, bb, 400).grille(50, 100).im for k in ("spot2022", "spot2023", "spot2024", "spot2025")]
assembler(pans, "SPOT 1,5 m annuels (local -200..+200 m) : 2022 | 2023 | 2024 | 2025 (non recalés)").save(PLANCHES / "_ensemble_spot_2022_2025.png")
print("ok")
