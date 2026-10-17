"""Extrait les valeurs clés des textes de tests ADAC (lignes 'clé' suivies de la valeur). usage: python -I adac_extraire.py dossier_txt"""
import sys, os, re, json
CLES = ["Leistung", "Maximales Drehmoment", "Kraftübertragung", "Getriebe", "Höchstgeschwindigkeit",
        "Beschleunigung 0-100 km/h", "Stirnfläche/cW-Wert", "Reifengröße (Serie vo./hi.)", "Länge/Breite/Höhe",
        "Leergewicht/Zuladung", "Überholvorgang 60-100 km/h", "Elastizität", "Bremsweg aus 100 km/h",
        "Reifengröße Testwagen", "Reifenmarke Testwagen", "Wendekreis links/rechts", "Fahrzeugbreite (inkl. Außenspiegel)",
        "Batteriekapazität", "Systemleistung", "Leistung E-Motor", "Zul. Gesamtgewicht", "Antrieb"]
out = {}
for fn in sorted(os.listdir(sys.argv[1])):
    lines = [l.strip() for l in open(os.path.join(sys.argv[1], fn), encoding="utf-8")]
    d = {}
    for i, l in enumerate(lines):
        for k in CLES:
            if l.startswith(k) and k not in d:
                v = l[len(k):].strip() or (lines[i+1] if i+1 < len(lines) else "")
                if l.startswith("Leergewicht/Zuladung") and "Leergewicht/Zuladung" in d:
                    continue
                d.setdefault(k, []).append(v) if False else None
                d[k] = v
    # deuxième occurrence (mesure ADAC) du poids à vide
    occ = [lines[i+1] for i, l in enumerate(lines) if l.startswith("Leergewicht/Zuladung")]
    d["Leergewicht/Zuladung (toutes occurrences)"] = occ
    txt = " ".join(lines)
    m = re.findall(r"(\d+)\s*auf\s*(\d+)\s*km/h\s*in\s*([\d,]+)\s*s", txt)
    d["textes_x_auf_y"] = m
    m2 = re.findall(r"Vollbremsung aus 100 km/h[^.]{0,80}?([\d,]+)\s*m", txt)
    d["texte_bremsweg"] = m2
    out[fn] = d
print(json.dumps(out, ensure_ascii=False, indent=1))
