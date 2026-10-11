from PIL import Image, ImageDraw, ImageFont
R = "D:/ClaudeCode_RoadCreation/"
Q = R + "recon/out/paquet_jardin/v2_avant_travaux/inventaire/qualite/"
F = ImageFont.truetype("arial.ttf", 22); Ft = ImageFont.truetype("arial.ttf", 20)
cas = [
 ("recon/pc/rendus/v2_site/p_e_ilot_gravier.png", "1. Karma p_e : trou de 0,02 m2 dans le remplissage de I-0390 (1,7 ; -13,0), plis du remplissage, eclats epars poses sur l'enrobe",
  [(765, 382, 50, "trou"), (700, 300, 160, "plis"), (420, 1060, 110, "eclats")]),
 ("recon/pc/rendus/v2_site/p_a_pieton_file_joints.png", "2. Karma p_a : ondulations de la chaussee au pied de la bordure (27,4 ; 14,6), epaufrures en trous ronds",
  [(830, 520, 90, "ondulations"), (700, 1000, 60, "trous ronds"), (640, 860, 45, "")]),
 ("recon/pc/rendus/v2_site/p_b_abaisse_traversee_bev.png", "3. Karma p_b : bout de bordure coude et ressaut (16,8 ; -0,7), eclats sur la chaussee (16,5 ; 3,2)",
  [(1335, 290, 80, "coude"), (200, 590, 90, "eclats"), (1220, 455, 50, "")]),
 ("recon/pc/rendus/v2_site/c_cam1_ensemble_sud.png", "4. Karma c_cam1 : batiments = trous dans le sol, secteur est (Saules Blancs) en aplat gris, aucun arbre ni mobilier",
  [(1330, 720, 90, "trou batiment"), (1050, 760, 140, "aplat"), (120, 560, 120, "trou batiment")]),
 ("recon/out/paquet_jardin/v2/ue_pilote/ctx_cam2_1920x1080.png", "5. UE ctx_cam2 (hors pilote = v1) : bordure en mur vertical a tete en dents de scie, marquage jaune drape sur la face",
  [(1700, 1010, 80, "jaune sur bordure"), (1250, 620, 110, "dents de scie")]),
 ("recon/out/paquet_jardin/v2/ue_pilote/ctx_cam4_1920x1080.png", "6. UE ctx_cam4 (v1) : fleche vectorisee depuis le raster, contour en escalier, fusionnee avec la ligne",
  [(1150, 800, 170, "escalier + fusion")]),
]
w = 900
ims = []
for f, titre, marques in cas:
    im = Image.open(R + f).convert("RGB"); k = w / im.width
    im = im.resize((w, int(im.height * k)), Image.LANCZOS); d = ImageDraw.Draw(im)
    for x, y, r, t in marques:
        x, y, r = x * k, y * k, r * k
        d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 40, 40), width=4)
        if t: d.text((x + r + 4, y - 12), t, fill=(255, 255, 0), font=F, stroke_width=3, stroke_fill="black")
    ims.append((im, titre))
import textwrap
H = sum(im.height + 58 for im, _ in ims) + 20
P = Image.new("RGB", (w + 20, H), (24, 24, 24)); g = ImageDraw.Draw(P); y = 10
for im, t in ims:
    g.multiline_text((10, y), textwrap.fill(t, 82), fill=(230, 230, 120), font=Ft, spacing=2); P.paste(im, (10, y + 52)); y += im.height + 58
P.save(Q + "planche_defauts_annotes.png"); print(P.size)
