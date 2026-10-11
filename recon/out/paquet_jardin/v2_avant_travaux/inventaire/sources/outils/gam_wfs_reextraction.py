"""Comparaison du WFS geoflux re-interrogé le 2026-10-11 (data/sites/paquet_jardin/avant_travaux/gam_geoflux_2026-10-11)
avec data/sites/paquet_jardin/etat_2026 (extraction du 2026-10-06). Tolérance 5 cm (90e centile des écarts).
Usage : python -I gam_wfs_reextraction.py <dossier_wfs_2026-10-11> <dossier_etat_2026> <sortie.json>"""
import json,sys,collections
import numpy as np
B=(917129.43,6460139.98,917429.43,6460439.98)
O=(917279.43,6460289.98)
def pts(g):
    def fl(c):
        if isinstance(c[0],(int,float)): return [c]
        o=[]
        for x in c: o+=fl(x)
        return o
    return np.array([q[:2] for q in fl(g['coordinates'])],float)
def dens(P,step=0.1):
    out=[P[0]]
    for a,b in zip(P[:-1],P[1:]):
        L=np.hypot(*(b-a)); n=max(1,int(L/step))
        for k in range(1,n+1): out.append(a+(b-a)*k/n)
    return np.array(out)
res={}
for lay,old in [("topo_sol_bordure_lin","bordure_lin_L93"),("topo_sol_signalisation_horizontale_lin","signalisation_horizontale_lin_L93"),("topo_sol_limite_revetement_lin","limite_revetement_lin_L93"),("topo_sol_signalisation_horizontale_pct","signalisation_horizontale_pct_L93")]:
    new=json.load(open(f"{sys.argv[1]}/donnees_referentielles_topo_{lay}.geojson",encoding='utf-8'))['features']
    oldf=json.load(open(f"{sys.argv[2]}/{old}.geojson",encoding='utf-8'))['features']
    pct=lay.endswith('_pct')
    new=[f for f in new if f.get('geometry') and ((f['properties'].get('type_geom') in ('fme_point','fme_text'))==pct)]
    # dedupe new by rounded geometry+calque
    seen={}
    for f in new:
        P=pts(f['geometry'])
        if not any(B[0]<=q[0]<=B[2] and B[1]<=q[1]<=B[3] for q in P): continue
        k=(f['properties'].get('calque'),tuple(np.round(P,3).ravel()))
        seen.setdefault(k,f)
    newu=list(seen.values())
    ids=collections.Counter(f['id'] for f in new)
    # build point cloud of densified new
    NP=np.vstack([dens(pts(f['geometry'])) for f in newu]); OP=np.vstack([dens(pts(f['geometry'])) for f in oldf])
    from collections import defaultdict
    def grid(P,c=0.5):
        g=defaultdict(list)
        for i,(x,y) in enumerate(P): g[(int(x//c),int(y//c))].append(i)
        return g
    gN=grid(NP); gO=grid(OP)
    def nn(P,Q,gQ,c=0.5):
        d=np.full(len(P),9.9)
        for i,(x,y) in enumerate(P):
            ix,iy=int(x//c),int(y//c); best=9.9
            for a in (-1,0,1):
                for b in (-1,0,1):
                    for j in gQ.get((ix+a,iy+b),()):
                        dd=np.hypot(*(Q[j]-P[i]))
                        if dd<best: best=dd
            d[i]=best
        return d
    def feat_match(F,Q,gQ):
        ok=0; ko=[]
        for f in F:
            P=dens(pts(f['geometry']))
            d=nn(P,Q,gQ)
            if np.percentile(d,90)<0.05: ok+=1
            else: ko.append(f)
        return ok,ko
    ok_o,ko_o=feat_match(oldf,NP,gN)
    ok_n,ko_n=feat_match(newu,OP,gO)
    def loc(F):
        c=[pts(f['geometry']).mean(0)-O for f in F]
        return [ [round(float(x),1),round(float(y),1)] for x,y in c]
    print(lay,"| WFS bruts",len(new),"ids uniques",len(ids),"géométries uniques dans emprise",len(newu),"| etat_2026",len(oldf))
    print("   etat_2026 retrouvés dans WFS du jour (<5 cm)",ok_o,"/",len(oldf),"; WFS du jour retrouvés dans etat_2026",ok_n,"/",len(newu))
    print("   ex. absents du jour (local):",loc(ko_o)[:8])
    print("   ex. nouveaux du jour (local):",loc(ko_n)[:8])
    res[lay]=dict(wfs_bruts=len(new),geom_uniques=len(newu),etat_2026=len(oldf),etat_retrouves=ok_o,jour_retrouves=ok_n,absents_local=loc(ko_o),nouveaux_local=loc(ko_n))
json.dump(res,open(sys.argv[3],'w',encoding='utf-8'),indent=1)
