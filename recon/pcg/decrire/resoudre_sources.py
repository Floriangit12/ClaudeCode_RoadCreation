"""Lecture des entrées de la résolution (lecture seule) et contrôle de la chaîne (RES-CHN-001).

Entrées :
- description de base : description/base/*.geojson, nivellement.*, description_scene_v2.json (schéma 0.3) ;
- objets du paquet v1 : package/donnees/objets/{mobilier,arbres}.geojson ;
- fusion 0.3 : description/enrichi/{entites_verifiees.json, attributs.geojson, corrections_position.geojson,
  ajouts.geojson, conflits.json} ;
- cohérence v2 : description/coherence/{rapport_coherence.json, corrections_marquages.geojson, marquages_controle.json,
  revue_coherence.json} ;
- protocole terrain : recon/pcg/enrichir/PROTOCOLE_TERRAIN.md (stations).
"""
import copy
from pathlib import Path

from commun import DONNEES, RACINE, SORTIE, lire_json, rel, sha256

BASE = SORTIE / "base"
ENRICHI = SORTIE / "enrichi"
COHERENCE = SORTIE / "coherence"
OBJETS = DONNEES / "objets"
PROTOCOLE = RACINE / "recon/pcg/enrichir/PROTOCOLE_TERRAIN.md"

FAMILLES_BASE = ("bordures", "surfaces", "ilots", "ponctuels_sol", "marquages", "marquages_correspondance")
FICHIERS_COPIES = ("nivellement.json", "nivellement_grille.npz", "regularisation_sources.geojson",
                   "marquages_hypotheses.geojson", "marquages_indices_v1.geojson")
ENTREES = {
    "manifeste_base": SORTIE / "description_scene_v2.json",
    "mobilier_v1": OBJETS / "mobilier.geojson",
    "arbres_v1": OBJETS / "arbres.geojson",
    "fusion_entites": ENRICHI / "entites_verifiees.json",
    "fusion_attributs": ENRICHI / "attributs.geojson",
    "fusion_corrections_position": ENRICHI / "corrections_position.geojson",
    "fusion_ajouts": ENRICHI / "ajouts.geojson",
    "fusion_conflits": ENRICHI / "conflits.json",
    "fusion_arbitrages": ENRICHI / "arbitrages_fusion.json",
    "fusion_observations": ENRICHI / "observations_index.json",
    "coherence_rapport": COHERENCE / "rapport_coherence.json",
    "coherence_corrections_marquages": COHERENCE / "corrections_marquages.geojson",
    "coherence_marquages_controle": COHERENCE / "marquages_controle.json",
    "coherence_revue": COHERENCE / "revue_coherence.json",
    "protocole_terrain": PROTOCOLE,
    "poses_2026": SORTIE.parent / "enrichi/recensement/pano_2026/poses/poses_2026-07-28.json",
}


class Sources:
    def __init__(self):
        self.base = {}          # famille -> FeatureCollection (copie profonde, modifiable)
        self.base_brut = {}     # famille -> FeatureCollection d'origine (lecture seule)
        for fam in FAMILLES_BASE:
            d = lire_json(BASE / f"{fam}.geojson")
            self.base_brut[fam] = d
            self.base[fam] = copy.deepcopy(d)
        self.manifeste = lire_json(ENTREES["manifeste_base"])
        self.mobilier = lire_json(ENTREES["mobilier_v1"])
        self.arbres = lire_json(ENTREES["arbres_v1"])
        self.entites = lire_json(ENTREES["fusion_entites"])["entites"]
        self.attributs = lire_json(ENTREES["fusion_attributs"])["features"]
        self.corr_pos = lire_json(ENTREES["fusion_corrections_position"])["features"]
        self.ajouts = lire_json(ENTREES["fusion_ajouts"])["features"]
        self.conflits = lire_json(ENTREES["fusion_conflits"])["conflits"]
        obs = lire_json(ENTREES["fusion_observations"])
        self.obs_meta = obs.get("meta", {})
        self.observations = {o["id"]: o for o in obs["observations"]}
        self.rapport = lire_json(ENTREES["coherence_rapport"])
        self.corr_mq = lire_json(ENTREES["coherence_corrections_marquages"])["features"]
        self.mq_controle = lire_json(ENTREES["coherence_marquages_controle"])
        self.revue_coh = lire_json(ENTREES["coherence_revue"])["revues"]
        self.poses_2026 = [(f"pnx:{q['id8']}", (float(q["pose"]["x"]), float(q["pose"]["y"])))
                           for q in lire_json(ENTREES["poses_2026"])["photos"] if q.get("accepte") is True and q.get("pose")]
        self.empreintes = {k: {"fichier": rel(p), "sha256": sha256(p)} for k, p in sorted(ENTREES.items())}
        for fam in FAMILLES_BASE:
            p = BASE / f"{fam}.geojson"
            self.empreintes[f"base_{fam}"] = {"fichier": rel(p), "sha256": sha256(p)}

    # ------------------------------------------------------------------ index
    def index_base(self, fam):
        return {f["properties"]["id"]: f for f in self.base[fam]["features"]}

    def objets_coherence(self):
        return {o["id"]: o for o in self.rapport["objets"]}

    def chaine(self):
        """Écarts entre la base courante et la base lue par la cohérence et par la fusion (RES-CHN-001)."""
        ecarts = []
        src = self.rapport.get("sources", {})
        for cle, fam in (("bordures_v2", "bordures"), ("surfaces_v2", "surfaces"), ("marquages_v2", "marquages")):
            lu = (src.get(cle) or {}).get("sha256")
            cour = self.empreintes[f"base_{fam}"]["sha256"]
            if lu and lu != cour:
                ecarts.append(f"cohérence : base/{fam}.geojson lue {lu[:12]}, courante {cour[:12]}")
        ent = self.obs_meta.get("entrees", {})
        for fam in ("bordures", "surfaces", "ilots", "ponctuels_sol", "marquages", "marquages_correspondance"):
            cle = f"recon/out/paquet_jardin/v2/description/base/{fam}.geojson"
            lu = ent.get(cle)
            cour = self.empreintes[f"base_{fam}"]["sha256"]
            if lu and lu != cour:
                ecarts.append(f"fusion : base/{fam}.geojson lue {lu[:12]}, courante {cour[:12]}")
        for cle, nom in (("mobilier", "mobilier_v1"), ("arbres", "arbres_v1")):
            lu = (src.get(cle) or {}).get("sha256")
            if lu and lu != self.empreintes[nom]["sha256"]:
                ecarts.append(f"cohérence : objets {cle} lus {lu[:12]}, courants {self.empreintes[nom]['sha256'][:12]}")
        return ecarts


def chemin_base(nom):
    return BASE / nom


def racine():
    return Path(RACINE)
