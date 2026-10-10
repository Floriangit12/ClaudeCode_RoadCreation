from PIL import Image, ImageDraw, ImageFont
import glob, os, sys
f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for i in sys.argv[1:]:
    ps=sorted(glob.glob(f'crops/{i}_v*_brut.jpg'))[:4]
    sheet=Image.new('RGB',(1600,1200),(0,0,0))
    for j,p in enumerate(ps):
        im=Image.open(p).resize((800,600)); x,y=(j%2)*800,(j//2)*600
        sheet.paste(im,(x,y)); d=ImageDraw.Draw(sheet); d.rectangle([x,y,x+300,y+22],fill=(0,0,0)); d.text((x+4,y+2),os.path.basename(p),fill=(255,255,0),font=f)
    sheet.save(f'crops/planche_360_{i}.jpg',quality=85)
print('ok')
