import sys, json, math
sys.path.insert(0, "C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q")
from qutil import *
from PIL import Image, ImageDraw, ImageFont, ImageFilter
S = "C:/Users/flori/AppData/Local/Temp/claude/D--/193706ca-c280-454e-8894-a24c258637c3/scratchpad/q/"
Q = R / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/qualite"
PNV = Q / "photos_non_versionnees"
CAMS = json.load(open(PNV / "cameras_vignettes.json"))
bord = []
for f in load(R / "recon/out/paquet_jardin/v2/description/base/bordures.geojson"):
    a = np.array(f["geometry"]["coordinates"], float); a[:, :2] -= O; a[:, 2] -= 216.30; bord.append(a)
gam22 = []  # aucune : la description 2022 n'existe pas encore
def projeter(c, P):
    Rm = np.array(c["R"]); C = np.array(c["C"]); q = (P - C) @ Rm.T
    ok = (q[:, 1] > 0.8) & (np.linalg.norm(q, axis=1) < 70)
    u = c["W"] / 2 + c["f_px"] * q[:, 0] / np.where(ok, q[:, 1], 1)
    v = c["H"] / 2 - c["f_px"] * q[:, 2] / np.where(ok, q[:, 1], 1)
    return np.c_[u, v], ok
def dessiner(im, c, col):
    d = ImageDraw.Draw(im)
    for a in bord:
        uv, ok = projeter(c, a)
        for i in range(len(a) - 1):
            if ok[i] and ok[i + 1]:
                d.line([tuple(uv[i]), tuple(uv[i + 1])], fill=col, width=2)
    return im
def detail(im, box):
    a = np.asarray(im.convert("L").crop(box), np.float32)
    lap = np.abs(4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:])
    return float(lap.mean()), float(a.std())
try: F = ImageFont.truetype("arial.ttf", 17); Fs = ImageFont.truetype("arial.ttf", 14)
except Exception: F = Fs = ImageFont.load_default()
w, h = 640, 427
rows = list(CAMS.items())
P = Image.new("RGB", (2 * w + 30, 70 + len(rows) * (h + 30)), (24, 24, 24)); g = ImageDraw.Draw(P)
g.text((10, 8), "Photo Panoramax AVANT travaux (gauche) | rendu Karma de la fabrication 2026 (droite), meme pose calee, champ 90 deg", fill="white", font=F)
g.text((10, 32), "Trait rouge : bordures de la description v2 (leve GAM post-travaux) projetees. Photos Eric S / Panoramax (osm-fr), CC-BY-SA-4.0", fill=(200, 200, 200), font=Fs)
mesures = {}
for k, (nom, c) in enumerate(rows):
    ph = Image.open(PNV / f"{nom}.jpg").convert("RGB")
    rd = Image.open(S + f"rendu_{nom}.png").convert("RGB")
    box = (160, 400, 800, 470)   # bande de chaussee devant le capot (hors capot)
    mesures[nom] = {"photo_detail_lap": detail(ph, box)[0], "photo_ecart_type": detail(ph, box)[1],
                    "rendu_detail_lap": detail(rd, box)[0], "rendu_ecart_type": detail(rd, box)[1],
                    "date_photo": c.get("photo"), "C": c["C"], "lacet": c["lacet_grille"]}
    a = dessiner(ph.copy(), c, (255, 30, 30)).resize((w, h), Image.LANCZOS)
    b = dessiner(rd.copy(), c, (255, 30, 30)).resize((w, h), Image.LANCZOS)
    Y = 60 + k * (h + 30)
    lab = f"{nom} : camera ({c['C'][0]:.1f} ; {c['C'][1]:.1f} ; {c['C'][2]:.2f}) m, cap grille {c['lacet_grille']:.0f} deg"
    g.text((10, Y), lab, fill=(230, 230, 120), font=Fs)
    P.paste(a, (10, Y + 20)); P.paste(b, (20 + w, Y + 20))
P.save(PNV / "planche_photo_vs_karma_2026.png")
json.dump(mesures, open(Q / "mesures_detail_photo_rendu.json", "w"), indent=1)
for k, v in mesures.items(): print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items() if a != "C"})
