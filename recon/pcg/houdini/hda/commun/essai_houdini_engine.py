"""Essai Houdini Engine (HAPI, session Thrift par tube nommé : la voie du plugin Unreal) du paquet d'HDA pj::*.

    hython recon/pcg/houdini/hda/commun/essai_houdini_engine.py [paquet.hdalc] [--emprise pilote]

Démarre HARS (Indie), charge le paquet unique (recon/out/paquet_jardin/v2/fabrique_hda/hda/pj_paquet_jardin.hdalc),
instancie pj::lire_description, règle l'emprise, cuit, puis lit les sorties comme le ferait Unreal : nombre de
parties, de points et de primitives par sortie, attributs id / materiau_id, volumes du HeightField. Imprime un JSON.
"""
import json
import sys
import time
from pathlib import Path

import hapi

RACINE = Path(__file__).resolve().parents[5]
PAQUET = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda/hda/pj_paquet_jardin.hdalc"


def _chaine(s, h):
    return hapi.getString(s, h, hapi.getStringBufLength(s, h)) if h else ""


def essai(paquet=PAQUET, emprise="pilote"):
    opts = hapi.ThriftServerOptions()
    opts.autoClose = True
    opts.timeoutMs = 20000.0
    tube = f"pj_hapi_{int(time.time())}"
    hapi.startThriftNamedPipeServer(opts, tube, "")
    s = hapi.createThriftNamedPipeSession(tube, hapi.SessionInfo())
    hapi.initialize(s, hapi.CookOptions(), True, -1, "", "", "", "", "")
    lib = hapi.loadAssetLibraryFromFile(s, str(paquet), True)
    n = hapi.getAvailableAssetCount(s, lib)
    noms = [_chaine(s, h) for h in hapi.getAvailableAssets(s, lib, n)]
    out = {"paquet": str(paquet), "definitions": noms}
    noeud = hapi.createNode(s, -1, "pj::lire_description::1.0", "lire", False)
    pid = hapi.getParmIdFromName(s, noeud, "emprise")
    hapi.setParmIntValue(s, noeud, "emprise", 0, {"site": 0, "pilote": 1}[emprise])
    t = time.time()
    hapi.cookNode(s, noeud, hapi.CookOptions())
    while hapi.getStatus(s, hapi.statusType.CookState) > hapi.state.Ready:
        time.sleep(0.05)
    out["cuisson_s"] = round(time.time() - t, 1)
    out["etat"] = hapi.getStatus(s, hapi.statusType.CookResult)
    sorties = []
    for g in hapi.getOutputGeoInfos(s, noeud, hapi.getOutputGeoCount(s, noeud)):
        info = {"parties": g.partCount}
        for k in range(g.partCount):
            pi = hapi.getPartInfo(s, g.nodeId, k)
            d = {"type": int(pi.type), "points": pi.pointCount, "primitives": pi.faceCount,
                 "attributs_prim": pi.attributeCounts[int(hapi.attributeOwner.Prim)]}
            if pi.faceCount and d["attributs_prim"]:
                noms_a = [_chaine(s, h) for h in hapi.getAttributeNames(s, g.nodeId, k, hapi.attributeOwner.Prim,
                                                                        d["attributs_prim"])]
                d["exemple_attributs"] = sorted(noms_a)[:12]
                for a in ("id", "materiau_id"):
                    if a in noms_a:
                        ai = hapi.getAttributeInfo(s, g.nodeId, k, a, hapi.attributeOwner.Prim)
                        vals = hapi.getAttributeStringData(s, g.nodeId, k, a, ai, 0, min(3, ai.count))
                        d[a] = [_chaine(s, h) if isinstance(h, int) else h for h in vals]
            if pi.type == hapi.partType.Volume:
                vi = hapi.getVolumeInfo(s, g.nodeId, k)
                d["volume"] = {"nom": _chaine(s, vi.nameSH), "res": [vi.xLength, vi.yLength, vi.zLength]}
            info.setdefault("detail", []).append(d)
        sorties.append(info)
    out["sorties"] = sorties
    hapi.cleanup(s)
    hapi.closeSession(s)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    emp = sys.argv[sys.argv.index("--emprise") + 1] if "--emprise" in sys.argv else "pilote"
    print(json.dumps(essai(Path(args[0]) if args else PAQUET, emp), ensure_ascii=False, indent=1)[:6000])
