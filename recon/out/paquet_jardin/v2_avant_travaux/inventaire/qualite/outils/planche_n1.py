import sys
sys.path.insert(0, "C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
from qutil import *
from PIL import Image, ImageDraw, ImageFont
OUT = R / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/qualite"
cx, cy = -1.569, -5.089
half = 40.0703519 * math.tan(math.radians(34.0))
x0, y0, x1, y1 = O[0]+cx-half, O[1]+cy-half, O[0]+cx+half, O[1]+cy+half
res = 2*half/700
orth = Image.fromarray(ortho(x0, y0, x1, y1, res))
rendu = Image.open(R / "recon/pc/rendus/v2_site/n1_centre_dessus_40m.png").convert("RGB").resize((700, 700), Image.LANCZOS)
ov = orth.copy(); d = ImageDraw.Draw(ov)
px = lambda l: [((x - x0) / res, (y1 - y) / res) for x, y in l]
for l in lignes(load(R/'data/sites/paquet_jardin/etat_2026/bordure_lin_L93.geojson')): d.line(px(l), fill=(255, 40, 40), width=2)
for l in lignes(load(R/'data/sites/paquet_jardin/etat_2026/signalisation_horizontale_lin_L93.geojson')): d.line(px(l), fill=(0, 255, 255), width=1)
# superposition rendu / ortho (fondu 50 %)
mix = Image.blend(orth, rendu, 0.5)
W = 700*2 + 30; H = 700*2 + 110
P = Image.new("RGB", (W, H), (24, 24, 24)); g = ImageDraw.Draw(P)
try:
    f = ImageFont.truetype("arial.ttf", 18); fs = ImageFont.truetype("arial.ttf", 15)
except Exception:
    f = fs = ImageFont.load_default()
g.text((10, 8), "Centre du carrefour vu de dessus, emprise identique (54 x 54 m, nord en haut, centre local (-1,57 ; -5,09))", fill="white", font=f)
cases = [(orth, "a. Ortho PCRS 5 cm du 10/05/2022 (etat AVANT travaux)"), (rendu, "b. Rendu Karma n1 de la fabrication 2026 (fabrique_hda)"),
         (ov, "c. Leve GAM (etat_2026 = gam_topo_sol) sur l'ortho 2022 : bordures rouge, marquages cyan"), (mix, "d. Fondu 50 % ortho 2022 / rendu 2026")]
for k, (im, t) in enumerate(cases):
    c, r = k % 2, k // 2
    X = 10 + c*(700+10); Y = 40 + r*(700+35)
    P.paste(im, (X, Y + 22)); g.text((X, Y), t, fill=(230, 230, 120), font=fs)
P.save(OUT / "planche_n1_rendu2026_vs_ortho2022.png")
print(P.size, res)
