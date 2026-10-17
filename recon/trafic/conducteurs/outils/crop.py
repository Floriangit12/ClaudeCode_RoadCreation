"""Rend une zone d'une page PDF a haute resolution (fraction de page x0,y0,x1,y1) : python -I crop.py f.pdf page dpi x0 y0 x1 y1 out.png"""
import sys, fitz
f, p, dpi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
x0, y0, x1, y1 = map(float, sys.argv[4:8])
d = fitz.open(f); pg = d[p-1]; r = pg.rect
clip = fitz.Rect(r.x0 + x0*r.width, r.y0 + y0*r.height, r.x0 + x1*r.width, r.y0 + y1*r.height)
pix = pg.get_pixmap(dpi=dpi, clip=clip); pix.save(sys.argv[8]); print(sys.argv[8], pix.width, pix.height)
