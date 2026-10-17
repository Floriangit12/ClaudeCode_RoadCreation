"""Convertit les 4 fichiers SDES (parc au 1er janvier 2026) en JSON : feuille -> liste de lignes
{chemin: [libellés hiérarchiques], annees: {annee: valeur}}. usage: python -E -P sdes_vers_json.py dossier sortie.json"""
import sys, json, openpyxl, os
out = {"source": "SDES, RSVERO, données sur le parc automobile français au 1er janvier 2026 (publié le 10/07/2026), données provisoires", "fichiers": {}}
for f in ["vp_national.xlsx", "vul_national.xlsx", "pl_national.xlsx", "tcp_national.xlsx"]:
    wb = openpyxl.load_workbook(os.path.join(sys.argv[1], f), read_only=True, data_only=True)
    fo = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        annees, lignes, titre = None, [], None
        for r in rows:
            vals = [v for v in r if v is not None]
            if not vals: continue
            if titre is None and isinstance(vals[0], str): titre = vals[0]
            num = [v for v in r if isinstance(v, (int, float))]
            strs = [str(v) for v in r if isinstance(v, str)]
            if annees is None and sum(1 for v in vals if str(v).strip().isdigit() and len(str(v).strip()) == 4) >= 3:
                annees = [str(v).strip() for v in vals if str(v).strip().isdigit() and len(str(v).strip()) == 4]
                continue
            if annees and num and strs:
                lignes.append({"libelle": " / ".join(s.strip() for s in strs), "annees": dict(zip(annees[-len(num):], num))})
        fo[ws.title] = {"titre": titre, "lignes": lignes}
    out["fichiers"][f] = fo
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("ok")
