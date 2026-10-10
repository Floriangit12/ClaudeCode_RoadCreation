import sys, os, pymupdf as fitz
out=sys.argv[1]
for f in sys.argv[2:]:
    try:
        d=fitz.open(f)
    except Exception as e:
        print('ERR',f,e); continue
    name=os.path.basename(f)[:-4]
    with open(os.path.join(out,name+'.txt'),'w',encoding='utf-8') as w:
        for i,p in enumerate(d):
            w.write('\n=== PAGE %d (img %d) ===\n'%(i+1,len(p.get_images())))
            w.write(p.get_text())
    print(name, d.page_count, os.path.getsize(os.path.join(out,name+'.txt')))
