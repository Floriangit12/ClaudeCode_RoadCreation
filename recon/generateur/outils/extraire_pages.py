# -*- coding: utf-8 -*-
"""Extrait le texte de pages précises d'un PDF (contrôle ponctuel des valeurs citées par les volets).

Usage : python -I extraire_pages.py FICHIER.pdf 44 [45 ...] [--motif TEXTE]
Les pages sont celles du fichier PDF (1 = première page). Lecture seule.
"""
import sys

import pymupdf


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    motif = None
    if "--motif" in args:
        i = args.index("--motif")
        motif = args[i + 1].lower()
        args = args[:i] + args[i + 2:]
    chemin, pages = args[0], [int(a) for a in args[1:]]
    doc = pymupdf.open(chemin)
    for p in pages:
        texte = doc[p - 1].get_text()
        print(f"===== {chemin.split('/')[-1]} p. {p} / {doc.page_count}")
        if motif:
            lignes = texte.splitlines()
            for k, l in enumerate(lignes):
                if motif in l.lower():
                    print("\n".join(lignes[max(0, k - 4):k + 6]))
                    print("-----")
        else:
            print(texte)


if __name__ == "__main__":
    main()
