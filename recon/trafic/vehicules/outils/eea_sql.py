"""Interroge le point d'accès SQL Discodata de l'AEE et écrit le résultat en JSON + CSV.
usage: python -E -P eea_sql.py "REQUETE" sortie_sans_ext [nrOfHits]"""
import sys, json, csv, urllib.request, urllib.parse
q, out = sys.argv[1], sys.argv[2]
n = sys.argv[3] if len(sys.argv) > 3 else "5000"
url = "https://discodata.eea.europa.eu/sql?" + urllib.parse.urlencode({"query": q, "p": "1", "nrOfHits": n})
with urllib.request.urlopen(url, timeout=600) as r:
    d = json.load(r)
if "errors" in d:
    print(d); sys.exit(1)
res = d["results"]
json.dump({"requete": q, "url": url, "resultats": res}, open(out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if res:
    with open(out + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
print(len(res), "lignes ->", out)
for r in res[:40]: print(r)
