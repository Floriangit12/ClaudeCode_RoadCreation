"""Politique de dureté des règles d'implantation (solveur de cohérence v2, correctifs P7 et P8 de la revue v1).

Les règles d'assets/specs/regles_implantation.json ne sont pas modifiées : cette politique les interprète.

P7 — la dureté dépend de la NATURE de la règle (source) et du STATUT de l'objet :
- nature de la règle, d'après `source.doc` : « norme » (IISR, arrêtés, code), « guide » (Cerema, Certu,
  guides de métropoles : règles de conception), « pratique » (PRATIQUE, SITE_SPECS), « donnees »
  (SITE_DONNEES : cohérence des couches) ;
- statut de l'objet : « existant » (levé, LiDAR, inventaire, OSM, ortho, photo, constat d'un objet en
  place), « projet » (plan 2025 seul), « deduit » (déduit 2026, a priori) ;
- violation PHYSIQUE (toujours dure, quel que soit l'objet) : emprise sur une surface circulée (chaussée,
  voie bus, bande ou piste cyclable, passage piéton, traversée cyclable, îlot peint), dans un bâtiment
  (GEN-09) ; un objet flottant (GEN-04) se corrige en z ; les chevauchements (GEN-06) sont exclus par la
  recherche ;
- objet existant : seules les violations physiques sont dures ; reculs, abaissés, BEV, cheminement,
  nez d'îlot, ligne d'effet et orientation deviennent des coûts mous ou des signalements (la réalité peut
  être non conforme ; un arbre de 1970 n'est pas soumis à une fiche de plantation neuve) ;
- objet projet ou déduit : politique v1 (critique dure ; majeur dure si σ ≥ 0,5 m ; « vérifier » contraint).

P8 — GEN-02 (abaissés, palier, BEV) :
- exception CEREMA (fiche BEV n° 03) : un support de feux piétons (tête R12 / R12m) ou de bouton d'appel
  peut être implanté à la limite arrière de la BEV, dans le prolongement du passage : son centre est
  testé seul (l'emprise peut toucher la BEV sans la couvrir) et le palier ne lui est pas opposé dans la
  bande du passage prolongé ;
- le palier de 0,80 m (ARR2007 art. 1er 4° : « si la largeur du trottoir le permet ») passe de critique
  à majeur ; il n'est dessiné que si la largeur du trottoir ≥ profondeur de rampe + 0,80 m + diamètre du
  mât (coherence_carte).
"""
import re

NATURE_PAR_DOC = [
    (r"^(IISR\d|ARR20\d\d|CR_|LOM_)", "norme"),
    (r"^(CEREMA|CERTU|GL_|MTP_|CETE|NANTES|PARIS|LYON|MONTP)", "guide"),
    (r"^(PRATIQUE|SITE_SPECS)$", "pratique"),
    (r"^SITE_DONNEES$", "donnees"),
]
SURFACES_PHYSIQUES = {"chaussee", "voie_bus", "bande_cyclable", "piste_cyclable", "passage_pietons",
                      "traversee_cyclable", "ilot_peint", "batiment"}
REGLES_PHYSIQUES = {"GEN-01", "GEN-09", "SIG-09", "VEG-01"}      # surfaces circulées ou bâti
TETES_PIETONNES = {"R12", "R12m", "boitier_bouton_appel"}
EXCEPTION_GEN02 = dict(
    regle="GEN-02", zones_centre_seul=("bev",), zone_palier="palier_abaisse",
    source="CEREMA_BEV_2010 fiche 03 : « poteau support […] dans la zone en prolongement du marquage piéton "
           "et à la limite de la BEV » ; ARR2007 art. 1er 4° : passage de 0,80 m « si la largeur du trottoir le permet »")
SOURCES_P7 = ("revue adverse v1 (P7) ; regles_implantation.resolution.politique « majeur … la réalité peut être "
              "non conforme » ; VEG-02 (MTP_ARBRES_2024, plantations neuves) et ECL-01 (PRATIQUE) non opposables "
              "à un objet existant")


def nature_regle(g):
    doc = str((g.get("source") or {}).get("doc") or "")
    for motif, nat in NATURE_PAR_DOC:
        if re.search(motif, doc):
            return nat
    return "pratique"


def statut_objet(o):
    """existant | projet | deduit."""
    st = str(o.get("statut") or "")
    if st.startswith("déduit"):
        return "deduit"
    if o.get("preuve_propre") == "a_priori" and not st.startswith(("existant", "2026 confirmé", "à vérifier")):
        return "deduit"
    if o.get("preuve_propre") == "plan2025" and o.get("preuve") in ("plan2025", "a_priori"):
        return "projet"
    return "existant"


def violation_physique(v):
    """Une violation est physique si elle place l'emprise sur une surface circulée ou dans le bâti."""
    if v.get("nature") != "surface":
        return False
    zones = set(v.get("valeur") or [])
    return bool(zones & SURFACES_PHYSIQUES)


def porte_tete_pietonne(o, tetes_de):
    if o.get("type") not in ("support_feux",):
        return False
    return any(t["type_tete"] in TETES_PIETONNES for t in tetes_de.get(o["id"], []))


def durete(o, g, v, seuil_sigma, statut=None):
    """(dure, motif) d'une violation v de la règle g pour l'objet o (P7)."""
    statut = statut or statut_objet(o)
    if violation_physique(v):
        return True, "physique"
    if v.get("nature") in ("orientation", "z", "info"):
        return False, "non positionnelle"
    if statut == "existant":
        return False, f"objet existant : règle {nature_regle(g)} en coût mou (P7)"
    a_priori = statut == "deduit"
    if g["action"] == "verifier" and not a_priori:
        return False, "règle « vérifier »"
    grav = v.get("gravite_effective") or g["gravite"]
    if grav == "critique":
        return True, "critique"
    if grav == "majeur":
        return (o["sigma"] >= seuil_sigma), "majeur, σ ≥ seuil" if o["sigma"] >= seuil_sigma else "majeur, σ < seuil"
    return False, "mineur"


def poids_mou(g, v):
    """Poids du coût mou d'une violation non dure (P7) : norme > guide > pratique."""
    return {"norme": 1.0, "guide": 0.5, "pratique": 0.35, "donnees": 0.5}.get(nature_regle(g), 0.35)
