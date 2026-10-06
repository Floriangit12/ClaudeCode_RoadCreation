"""Découpe n'importe quelle image (photo Panoramax, mosaïque, raster LiDAR
rendu...) en tuiles carrées de 1000x1000 px, sans redimensionnement.

Usage : python3 pipeline/tile_images.py IMG [IMG...] --out DOSSIER
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import TILE_PX, cut_tiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tile", type=int, default=TILE_PX)
    ap.add_argument("--quality", type=int, default=92)
    a = ap.parse_args()
    for p in a.images:
        idx = cut_tiles(Path(p), Path(a.out) / Path(p).stem, tile=a.tile, quality=a.quality)
        print(p, "->", len(idx), "tuiles")


if __name__ == "__main__":
    main()
