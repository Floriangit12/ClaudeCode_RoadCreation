"""Construit l'HDA pj::bordure::1.0 (bordures en éléments préfabriqués) ; hython Houdini 22.

    hython recon/pcg/houdini/hda/pj_bordure/construire.py            # construit et enregistre pj_bordure.hdalc/
    hython recon/pcg/houdini/hda/pj_bordure/construire.py --essai [pilote|site|boite x0 y0 x1 y1]
                                                                   # réseau cuit sur la description, sans HDA

Réseau (README_HDA.md § « pj::bordure ») :
  entrée 1 (courbes d'arête avant + attributs) -> filtrer -> disposer (VEX : points durs, pas selon le rayon, coupes,
  chartières, jitter, joints) -> poser (VEX : repère, Z du nivellement, prototype) ;
  bibliothèque : dorsales_bib (VEX) -> Sweep -> abouts -> PolyBevel -> épaufrures (Copy to Points + Boolean) -> Divide
  -> Normal -> UV -> recentrer -> Pack -> Copy to Points (instances) -> Unpack (option) ;
  sur mesure : dorsales_sm (VEX, courbe régularisée à 2 mm) -> Sweep -> onglets -> abouts -> PolyBevel -> Divide
  -> Normal -> UV ; fusion -> export (attributs du contrat de branche).
Sorties : 1 = maillages (Y haut), 2 = points d'instances (pj_points/0.1 via pj::exporter_points), 3 = prototypes.
Python : seulement le nœud lire_profils (JSON des specs) ; toute la géométrie est faite par des nœuds et du VEX.
"""
import json
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
sys.path.insert(0, str(ICI))
import pj_hda_outils as O  # noqa: E402
import profils as PR  # noqa: E402

NOM = "bordure"
SPECS = O.RACINE / "assets" / "specs"
VEX = ICI / "vex"


def vex_f1(*fichiers):
    """Bibliothèques VEX de F1 (hda/pj_bordure/vex), recopiées en tête des wrangles (#include opdef: impossible)."""
    return "".join((VEX / f).read_text(encoding="utf-8") + "\n" for f in fichiers)


def corps(fichier, section=None):
    """Corps d'un wrangle : fichier .vfl entier, ou section « //@@ <nom> » d'un fichier à sections."""
    t = (VEX / fichier).read_text(encoding="utf-8")
    if section is None:
        return t
    parts = t.split("//@@ ")
    for p in parts[1:]:
        nom, _, reste = p.partition("\n")
        if nom.strip() == section:
            return reste
    raise KeyError(section)


def entetes(*f1):
    return O.vex("pj_niveau.h", "pj_repere.h") + vex_f1(*f1)


def module_python():
    """Module embarqué : profils.py + table des profils figée (TABLE_EMBARQUEE)."""
    table, src = PR.construire_table(SPECS)
    js = json.dumps({"profils": table, "source": {"dossier": "assets/specs", "sha256": src}}, sort_keys=True,
                    ensure_ascii=False, separators=(",", ":"))
    return (ICI / "profils.py").read_text(encoding="utf-8") + f"\n\nTABLE_EMBARQUEE = r'''{js}'''\n"


# ------------------------------------------------------------------------------------------------ paramètres
def parametres(mode="bordure"):
    T = hou
    F = T.FloatParmTemplate
    I = T.IntParmTemplate
    tg = T.ToggleParmTemplate
    pose = [
        T.MenuParmTemplate("altitude", "Altitude du pied", menu_items=("profil", "volume"),
                           menu_labels=("Profil en long du nivellement (niv_z_pied, TQ-SOL-013)",
                                        "Volume de nivellement (pj_niv_z devant la face)"), default_value=0,
                           help="Pied de face = fil d'eau du modèle unique ; le dessous du bloc est à pied + vue − H."),
        F("joint_mm", "Joint par défaut (mm)", 1, default_value=(6.0,), min=3.0, max=8.0,
          help="Utilisé si la bordure n'a pas de joint_mm (bordures_elements.json element.joint_mm)."),
        tg("joints_aleatoires", "Largeur de joint variable", default_value=True,
           help="5,5-7 mm (neuve) ou log-normale 5-8 mm (ancienne), coins bornés à 3,5-9,5 mm."),
        F("fleche_max_mm", "Flèche de corde max (mm)", 1, default_value=(10.5,), min=1.0, max=20.0,
          help="Élément droit admis si sa flèche reste sous ce seuil (regle_pas_rayon)."),
        F("coin_max_mm", "Coin de joint max (mm)", 1, default_value=(6.0,), min=1.0, max=20.0,
          help="Base x déviation des tangentes : au-delà, élément plus court ou pièce courbe."),
        F("coin_v_max_mm", "Coin vertical max (mm)", 1, default_value=(4.0,), min=1.0, max=20.0,
          help="H x changement de pente du fil d'eau sur l'élément."),
        F("pas_muret", "Pas des murets (m)", 1, default_value=(4.0,), min=1.0, max=10.0,
          help="Profil MURET_TALUS : pièces coulées de cette longueur au plus."),
        F("corde_mm", "Corde des courbes (mm)", 1, default_value=(2.0,), min=0.5, max=10.0,
          help="Flèche de corde max de l'échantillonnage des pièces sur mesure (courbes régularisées)."),
    ]
    aspect = [
        tg("jitter", "Jitter de pose", default_value=True, help="Graine = hachage de l'identifiant de l'élément."),
        F("jit_hauteur_mm", "Jitter de hauteur (mm)", 1, default_value=(2.0,), min=0.0, max=10.0),
        F("jit_lacet_deg", "Jitter de lacet (°)", 1, default_value=(0.3,), min=0.0, max=3.0),
        F("jit_lateral_mm", "Jitter latéral (mm)", 1, default_value=(1.0,), min=0.0, max=10.0),
        F("jit_roulis_deg", "Jitter de roulis (°)", 1, default_value=(0.15,), min=0.0, max=3.0),
        F("chanfrein_mm", "Chanfrein d'about (mm)", 1, default_value=(3.0,), min=0.0, max=10.0,
          help="Arêtes d'about de la tête et de la face vue (PolyBevel) ; 0 : arêtes vives."),
        tg("eclats", "Épaufrures (v1-v3)", default_value=True,
           help="Variantes d'éclats d'arête (Boolean) selon l'âge (bordures_elements.json epaufrures)."),
        F("joint_retrait_mm", "Retrait du mortier sombre (mm)", 1, default_value=(4.0,), min=0.0, max=10.0),
    ]
    if mode == "caniveau":
        pose += [T.StringParmTemplate("profil_defaut", "Profil par défaut", 1, default_value=("CS2",),
                                      help="Profil quand la bordure n'a pas d'attribut caniveau (CS1, CS2, CS3)."),
                 tg("sans_attribut", "Courbes sans attribut caniveau", default_value=False,
                    help="Une courbe sans attribut caniveau (tracée dans Unreal) reçoit un caniveau sur toute sa longueur.")]
    sorties = [
        T.MenuParmTemplate("sortie", "Sortie 1", menu_items=("maillages", "instances"),
                           menu_labels=("Maillages dépaquetés (export USD)", "Instances empaquetées"),
                           default_value=0,
                           help="Les points d'instances (sortie 2) sont toujours produits (unreal_instance)."),
        T.StringParmTemplate("couche", "Couche USD", 1,
                             default_value=("PJ_Caniveaux" if mode == "caniveau" else "PJ_Bordures",)),
        T.MenuParmTemplate("format_usd", "Format du fichier USD", menu_items=("usdc", "usda"),
                           menu_labels=("Binaire (.usdc)", "Texte (.usda)"),
                           default_value=1 if mode == "caniveau" else 0,
                           help="Lu par fabriquer_hda.py (bordures du site : plus de 600 000 faces, en binaire)."),
        T.StringParmTemplate("couche_bibliotheque", "Couche USD des prototypes", 1,
                             default_value=("PJ_Lib_Caniveaux" if mode == "caniveau" else "PJ_Lib_Bordures",),
                             help="Sortie 3 -> prototypes/<branche>.usda (import UE dans /Game/PJ/Lib/Bordures)."),
        T.StringParmTemplate("pivot_prototypes", "Pivot des prototypes", 1, default_value=(
            "milieu de l'élément, face vue, dessous du bloc ; X = s (le long de la bordure), Y = u (vers l'arrière), "
            "Z = v (haut), mètres (bordures_elements.json repere.pivot_prototype)",),
            help="Recopié dans le champ pivot de points/<branche>.json (pj_points/0.1)."),
        T.StringParmTemplate("sens_cd", "Sens de cd", 1, default_value=(
            "éléments : [usure (épaufrures), salissure, mousse_joints, herbe_joints, teinte] ; joints : idem "
            "(x.mortier : sombre en retrait | clair à fleur ; s[0] = (largeur + 4 mm) / 10 mm)",),
            help="Recopié dans le champ cd de points/<branche>.json."),
        T.StringParmTemplate("dossier_specs", "Dossier des specs (vide : table figée)", 1, default_value=("",),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Directory,
                             help="assets/specs (bordures.json, bordures_elements.json) ; vide : table figée dans l'HDA."),
    ]
    S = T.StringParmTemplate
    unreal = [   # agent intégration : courbes sans attributs (spline UE, courbe Houdini Engine, PCG), README_HDA.md § 9
        S("ue_id", "Identifiant", 1, default_value=("K-UE",),
          help="id des courbes qui n'en ont pas (plusieurs courbes : <id>-<n>) ; graine du jitter."),
        S("ue_profil", "Profil courant", 1, default_value=("T2",), help="Profil NF P98-340 (bordures.json)."),
        F("ue_vue", "Vue courante (m)", 1, default_value=(0.14,), min=0.0, max=0.30),
        S("ue_materiau", "Matériau", 1, default_value=("beton_bordure_gris",), help="materiau_id (materiaux_sol.json)."),
        tg("ue_abaisse", "Abaissé de traversée", default_value=False,
           help="Partie abaissée en vue réduite (GA-ABA-001) et deux rampants (chartières, GA-ABA-004)."),
        F("ue_abaisse_debut", "Début de la partie abaissée (m)", 1, default_value=(5.0,), min=0.0, max=50.0,
          help="Abscisse le long de la courbe (depuis son premier point)."),
        F("ue_abaisse_fin", "Fin de la partie abaissée (m)", 1, default_value=(7.0,), min=0.0, max=50.0,
          help="GA-ABA-001 : au moins 1,20 m de partie abaissée."),
        S("ue_profil_abaisse", "Profil abaissé", 1, default_value=("T2_bateau",)),
        F("ue_vue_abaisse", "Vue abaissée (m)", 1, default_value=(0.02,), min=0.0, max=0.10,
          help="GA-ABA-001 : 0,02 ± 0,005 m."),
        F("ue_rampant", "Longueur des rampants (m, −1 : règle)", 1, default_value=(-1.0,), min=-1.0, max=3.0,
          help="−1 : GA-ABA-004, L = min(2,00 ; Δh / 0,05), au moins Δh / 0,08 (Δh = vue courante − vue abaissée)."),
        F("ue_decalage_pied", "Décalage du pied (m)", 1, default_value=(0.0,), min=-1.0, max=1.0,
          help="Pied de face (fil d'eau) = Z de la courbe + décalage ; niv_s / niv_z_pied sont tirés de la courbe."),
        F("ue_usure", "Usure (épaufrures, salissure)", 1, default_value=(0.1,), min=0.0, max=1.0,
          help="aspect.epaufrures et aspect.salissure ; < 0,2 : bordure neuve (joints 5,5-7 mm, jitter normal)."),
        tg("sorties_unreal", "Sorties 2 et 3 vides (Houdini Engine)", default_value=False,
           help="Houdini Engine convertit toutes les sorties : vides, seuls les maillages ou instances de la sortie 1 "
                "sont créés dans Unreal (pas de prototypes à l'origine, pas d'instances de /Game/PJ/Lib absentes)."),
    ]
    return [T.FolderParmTemplate("f_pose", "Pose", parm_templates=pose, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_aspect", "Aspect", parm_templates=aspect, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_sorties", "Sorties", parm_templates=sorties, folder_type=T.folderType.Tabs),
            T.FolderParmTemplate("f_unreal", "Courbe tracée (Unreal)", parm_templates=unreal,
                                 folder_type=T.folderType.Tabs)]


# ------------------------------------------------------------------------------------------------ réseau
# Agent intégration (README_HDA.md § 9) : courbes sans attributs de la description (spline UE, courbe Houdini Engine,
# spline PCG, courbe tracée à la main) -> attributs de la description depuis l'onglet « Courbe tracée (Unreal) ».
# Une courbe de la description (famille renseignée ou intervalles présents) passe inchangée : sorties du site identiques.
VEX_COMPLETER = r"""
// completer_unreal (primitive) : courbe sans « intervalles » ni « famille » -> id, materiau_id, aspect, intervalles,
// niv_s / niv_z_pied / niv_z_tete tirés de la courbe elle-même (TQ-SOL-013 : pied de face = profil en long de la courbe).
// Abaissé de traversée : partie abaissée en vue 0,02 d'au moins 1,20 m (GA-ABA-001), deux rampants (chartières) de
// longueur L = min(2,00 ; Δh / 0,05), au moins Δh / 0,08 (GA-ABA-004) ; bornes des intervalles = points durs (GA-BOR-005).
dict ivs[] = prim(0, "intervalles", @primnum);
string fam = hasprimattrib(0, "famille") ? prim(0, "famille", @primnum) : "";
if (fam != "" || len(ivs) > 0) return;
int pts[] = primpoints(0, @primnum);
float S[], Z[];
float s = 0;
vector q = point(0, "P", pts[0]);
foreach (int i; int pt; pts) {
    vector p = point(0, "P", pt);
    if (i > 0) s += length(set(p.x - q.x, p.z - q.z));      // abscisse plane (Houdini Y haut : plan XZ)
    append(S, s);
    append(Z, p.y + chf("../ue_decalage_pied"));
    q = p;
}
float L = s;
string pc = chs("../ue_profil"), pa = chs("../ue_profil_abaisse");
float vc = chf("../ue_vue"), va = chf("../ue_vue_abaisse");
string base = chs("../ue_id");
string kid = nprimitives(0) > 1 ? sprintf("%s-%02d", base, @primnum) : base;
dict out[];
dict d;
if (!chi("../ue_abaisse")) {
    d["s0"] = 0.0; d["s1"] = L; d["profil"] = pc; d["vue_m"] = vc; d["role"] = "courant";
    append(out, d);
} else {
    float a0 = clamp(min(chf("../ue_abaisse_debut"), chf("../ue_abaisse_fin")), 0.0, L);
    float a1 = clamp(max(chf("../ue_abaisse_debut"), chf("../ue_abaisse_fin")), 0.0, L);
    if (a1 - a0 < 1.2) warning("GA-ABA-001 : partie abaissée de %.2f m (< 1,20 m)", a1 - a0);
    float dh = max(vc - va, 0.0);
    float r = chf("../ue_rampant");
    if (r < 0) r = max(min(2.0, dh / 0.05), dh / 0.08);    // GA-ABA-004
    r = max(r, 1e-3);
    float c0 = max(0.0, a0 - r), c1 = min(L, a1 + r);
    string ab = kid + "-A1";
    if (c0 > 1e-3) {
        d = {}; d["s0"] = 0.0; d["s1"] = c0; d["profil"] = pc; d["vue_m"] = vc; d["role"] = "courant"; append(out, d);
    }
    if (a0 - c0 > 1e-3) {
        d = {}; d["s0"] = c0; d["s1"] = a0; d["profil"] = pc; d["vue_m"] = va + dh * (a0 - c0) / r;
        d["vue_m_fin"] = va; d["role"] = "chartiere"; d["abaisse"] = ab; append(out, d);
    }
    if (a1 - a0 > 1e-3) {
        d = {}; d["s0"] = a0; d["s1"] = a1; d["profil"] = pa; d["vue_m"] = va; d["role"] = "bateau"; d["abaisse"] = ab;
        append(out, d);
    }
    if (c1 - a1 > 1e-3) {
        d = {}; d["s0"] = a1; d["s1"] = c1; d["profil"] = pc; d["vue_m"] = va; d["vue_m_fin"] = va + dh * (c1 - a1) / r;
        d["role"] = "chartiere"; d["abaisse"] = ab; append(out, d);
    }
    if (L - c1 > 1e-3) {
        d = {}; d["s0"] = c1; d["s1"] = L; d["profil"] = pc; d["vue_m"] = vc; d["role"] = "courant"; append(out, d);
    }
}
float ZT[];
foreach (int i; float si; S) {                              // tête = pied + vue de l'intervalle (murets seulement)
    float v = vc;
    foreach (dict iv; out) {
        float s0 = iv["s0"], s1 = iv["s1"], v0 = iv["vue_m"];
        float v1 = isvalidindex(iv, "vue_m_fin") ? iv["vue_m_fin"] : v0;
        if (si >= s0 - 1e-6 && si <= s1 + 1e-6) { v = lerp(v0, v1, (si - s0) / max(s1 - s0, 1e-6)); break; }
    }
    append(ZT, Z[i] + v);
}
dict asp;
asp["epaufrures"] = chf("../ue_usure"); asp["salissure"] = chf("../ue_usure");
asp["mousse_joints"] = 0.0; asp["herbe_joints"] = 0.0;
s@id = kid;
s@materiau_id = chs("../ue_materiau");
d@aspect = asp;
d[]@intervalles = out;
f[]@niv_s = S;
f[]@niv_z_pied = Z;
f[]@niv_z_tete = ZT;
"""


def blast(sub, nom, src, groupe, garder=True):
    b = sub.createNode("blast", nom)
    b.setInput(0, src)
    b.parm("group").set(groupe)
    b.parm("negate").set(1 if garder else 0)
    return b


ATTR_DORSALE = ("asset name proto_type variante proto_L decalage piece chanfrein materiau_id repere_x id bordure "
                "t_debut t_fin n_debut n_fin n_rangs graine usure salissure")
ATTR_SECTION = "n_pts H base h_fil_eau i_top k_back famille profil"


def balayer(sub, nom, dorsales, sections):
    """Sweep : dorsales (attribut de point variant = numéro de section) x sections (contours u, v). Les attributs
    propres à chaque flux sont retirés de l'autre (sinon le Sweep écrase ceux de la dorsale par ceux de la section)."""
    suf = nom.split("_")[-1]
    ds = sub.createNode("attribdelete", f"attributs_dorsales_{suf}")
    ds.setInput(0, dorsales)
    ds.parm("ptdel").set("u_cs v_cs chaine rang p_cs perim")
    ds.parm("primdel").set(ATTR_SECTION.replace(" profil", "") if suf == "bib" else ATTR_SECTION)
    se = sub.createNode("attribdelete", f"attributs_sections_{suf}")
    se.setInput(0, sections)
    se.parm("ptdel").set("variant s_dorsale courbure")
    se.parm("primdel").set(ATTR_DORSALE + " profil")
    s = sub.createNode("sweep::2.0", nom)
    s.setInput(0, ds)
    s.setInput(1, se)
    for p, v in (("surfaceshape", 0), ("surfacetype", 5), ("copyorder", 4), ("crosssectionattrib", "variant"),
                 ("endcaptype", 1), ("addendcapsgroup", 1), ("endcapsgroup", "endcaps"), ("upvectortype", 2),
                 ("addptrow", 1), ("ptrowattrib", "ptrow"), ("closeifnocurveinput", 0)):
        s.parm(p).set(v)
    return O.wrangle(sub, f"attributs_abouts_{suf}", corps("post.vfl", "attributs_abouts"), "primitive", s)


def finir(sub, suffixe, src, onglets=False):
    """Finition commune : (onglets) -> abouts (groupe) -> chanfreins -> Divide -> Normal -> UV."""
    n = src
    if onglets:
        n = O.wrangle(sub, "onglets", corps("post.vfl", "onglets"), "point", n)
    gc = sub.createNode("groupcreate", f"groupe_about_{suffixe}")      # groupe d'arêtes vide (entrée vide : PolyBevel
    gc.setInput(0, n)                                                  # reste valide)
    for p, v in (("groupname", "about"), ("grouptype", 2), ("groupbase", 0)):
        gc.parm(p).set(v)
    n = O.wrangle(sub, f"abouts_{suffixe}", corps("post.vfl", "abouts"), "primitive", gc)
    b = sub.createNode("polybevel::3.0", f"chanfreins_{suffixe}")
    b.setInput(0, n)
    for p, v in (("group", "about"), ("grouptype", 2), ("filletshape", 3), ("divisions", 1)):
        b.parm(p).set(v)
    b.parm("offset").setExpression('ch("../chanfrein_mm") / 1000')
    sw = sub.createNode("switch", f"si_chanfrein_{suffixe}")
    sw.setInput(0, n)
    sw.setInput(1, b)
    sw.parm("input").setExpression('ch("../chanfrein_mm") > 0')
    return sw


def finir2(sub, suffixe, src):
    orph = O.wrangle(sub, f"attributs_orphelins_{suffixe}", corps("post.vfl", "attributs_orphelins"), "primitive", src)
    d = sub.createNode("divide", f"trianguler_{suffixe}")
    d.setInput(0, orph)
    d.parm("convex").set(1)
    d.parm("numsides").set(4)
    g = sub.createNode("groupdelete", f"nettoyer_groupes_{suffixe}")
    g.setInput(0, d)
    g.parm("group1").set("about endcaps dorsale")
    nm = sub.createNode("normal", f"normales_{suffixe}")
    nm.setInput(0, g)
    nm.parm("type").set(1)                    # par sommet de face
    nm.parm("cuspangle").set(30.0)            # E2 : angle de rupture 30°
    uv = O.wrangle(sub, f"uv_{suffixe}", corps("post.vfl", "uv"), "sommet", nm)
    return uv


def reseau(sub, mode="bordure"):
    """Crée le réseau de pj::bordure (mode « bordure ») ou de pj::caniveau (mode « caniveau ») dans le subnet `sub` ;
    renvoie les nœuds de sortie (maillages, points, prototypes)."""
    ent = sub.createNode("null", "ENTREE_BORDURES")
    ent.setInput(0, sub.indirectInputs()[0])
    niv = sub.createNode("null", "ENTREE_NIVEAU")
    niv.setInput(0, sub.indirectInputs()[1])
    filtrer = O.wrangle(sub, "filtrer", r"""
// filtrer : courbes ouvertes de la famille bordures (ou sans famille : courbes tracées dans UE), au moins 2 points.
string fam = hasprimattrib(0, "famille") ? s@famille : "";
if ((fam != "" && fam != "bordures") || primintrinsic(0, "closed", @primnum) || @numvtx < 2) removeprim(0, @primnum, 1);
""", "primitive", ent)
    filtrer = O.wrangle(sub, "completer_unreal", VEX_COMPLETER, "primitive", filtrer)
    lp = sub.createNode("python", "lire_profils")
    lp.parm("python").set("# Table des profils (bordures.json, bordures_elements.json) -> contours (module profils.py)\n"
                          "hou.pwd().parent().hdaModule().lire_profils(hou.pwd())\n")
    disp = O.wrangle(sub, "disposer", entetes("pj_courbe.h", "pj_pose.h") +
                     corps("disposer_caniveau.vfl" if mode == "caniveau" else "disposer.vfl"), "primitive",
                     filtrer, entrees=(lp,))
    poser = O.wrangle(sub, "poser", entetes("pj_courbe.h", "pj_pose.h") + corps("poser.vfl"), "point", disp,
                      entrees=(filtrer, niv, lp))
    sm = blast(sub, "sur_mesure", poser, '@sur_mesure=1')
    sm.parm("grouptype").set(3)               # points
    bib = blast(sub, "instances_bib", poser, '@sur_mesure=0')
    bib.parm("grouptype").set(3)
    # ---- bibliothèque de prototypes
    db = O.wrangle(sub, "dorsales_bib", entetes("pj_sections.h") + corps("dorsales_bib.vfl"), "detail", lp,
                   entrees=(bib,))
    sec_b = blast(sub, "sections_bib", db, "dorsale", garder=False)
    dor_b = blast(sub, "dorsales_bib_seules", db, "dorsale")
    sw_b = balayer(sub, "balayer_bib", dor_b, sec_b)
    fin_b = finir(sub, "bib", sw_b)
    ec = O.wrangle(sub, "eclats_centres", entetes("pj_sections.h") + corps("post.vfl", "eclats"), "detail", db,
                   entrees=(lp,))
    ecp = blast(sub, "eclats_points", ec, "eclat")
    ecp.parm("grouptype").set(3)
    sph = sub.createNode("sphere", "eclat_forme")
    sph.parm("type").set(1)                   # polygones
    sph.parm("freq").set(3)
    bos = sub.createNode("attribnoise::2.0", "eclat_bosses")
    bos.setInput(0, sph)
    for p, v in (("attribs", "P"), ("displace", 1), ("amplitude", 0.25), ("elementsize", 0.9)):
        bos.parm(p).set(v)
    cpe = sub.createNode("copytopoints::2.0", "copier_eclats")
    cpe.setInput(0, bos)
    cpe.setInput(1, ecp)
    boo = sub.createNode("boolean::2.0", "retirer_eclats")
    boo.setInput(0, fin_b)
    boo.setInput(1, cpe)
    boo.parm("booleanop").set(2)              # soustraction A − B
    sw_e = sub.createNode("switch", "si_eclats")
    sw_e.setInput(0, fin_b)
    sw_e.setInput(1, boo)
    sw_e.parm("input").setExpression('ch("../eclats") && npoints("../eclats_points") > 0')
    ap = O.wrangle(sub, "attributs_pieces", corps("post.vfl", "attributs_pieces"), "primitive", sw_e,
                   entrees=(dor_b,))
    uv_b = finir2(sub, "bib", ap)
    rec = O.wrangle(sub, "recentrer", corps("post.vfl", "recentrer"), "point", uv_b)
    apr = O.wrangle(sub, "attributs_prototypes", r"""
// attributs_prototypes (primitive) : un component USD par prototype (pj_entite = asset -> SM_<asset> dans UE),
// couche de bibliothèque, un Mesh par matériau (README_HDA.md § 4, sortie 3).
s@pj_couche = chs("../couche_bibliotheque");
s@pj_entite = s@asset;
s@pj_maillage = s@materiau_id;
""", "primitive", rec)
    protos = sub.createNode("null", "PROTOTYPES")
    protos.setInput(0, apr)
    pk = sub.createNode("pack", "empaqueter")
    pk.setInput(0, protos)
    pk.parm("packbyname").set(1)
    pk.parm("nameattribute").set("asset")
    pk.parm("transfer_attributes").set("asset")
    cp = sub.createNode("copytopoints::2.0", "copier_instances")
    cp.setInput(0, pk)
    cp.setInput(1, bib)
    cp.parm("useidattrib").set(1)
    cp.parm("idattrib").set("asset")
    cp.parm("pack").set(1)
    cp.parm("targetattribs").set(1)
    cp.parm("applyto1").set(2)                # primitives (une par instance)
    cp.parm("applyattribs1").set("id bordure materiau_id graine kind type profil")
    up = sub.createNode("unpack", "depaqueter")
    up.setInput(0, cp)
    up.parm("transfer_attributes").set("id bordure materiau_id graine kind type profil")
    up.parm("limit_iterations").set(0)        # instances de fragments empaquetés : dépaquetage complet
    # ---- pièces sur mesure (dans le repère du site)
    ds = O.wrangle(sub, "dorsales_sm", entetes("pj_courbe.h", "pj_pose.h", "pj_sections.h") + corps("dorsales_sm.vfl"),
                   "detail", lp, entrees=(sm, filtrer, niv))
    sec_s = blast(sub, "sections_sm", ds, "dorsale", garder=False)
    dor_s = blast(sub, "dorsales_sm_seules", ds, "dorsale")
    sw_s = balayer(sub, "balayer_sm", dor_s, sec_s)
    fin_s = finir(sub, "sm", sw_s, onglets=True)
    uv_s = finir2(sub, "sm", fin_s)
    pieces = sub.createNode("null", "PIECES_SUR_MESURE")
    pieces.setInput(0, uv_s)
    # ---- sortie
    choix = sub.createNode("switch", "choix_sortie")
    choix.setInput(0, up)
    choix.setInput(1, cp)
    choix.parm("input").setExpression('ch("../sortie")')
    fus = sub.createNode("merge", "fusion")
    fus.setInput(0, choix)
    fus.setInput(1, pieces)
    exp = O.wrangle(sub, "export", corps("post.vfl", "export"), "primitive", fus)
    nett = sub.createNode("attribdelete", "attributs_internes")
    nett.setInput(0, exp)
    nett.parm("ptdel").set("u_cs v_cs chaine rang ptrow variant p_cs perim s_dorsale courbure")
    nett.parm("primdel").set("decalage piece n_rangs t_debut t_fin n_debut n_fin chanfrein repere_x proto_L "
                             "proto_type name cap")
    ue = O.wrangle(sub, "attributs_unreal", r"""
// attributs_unreal (primitive) : matériau Unreal de chaque face ou instance empaquetée (Houdini Engine), même chemin
// que pj::preparer_export (MI_<materiau_id> de /Game/PJ/Materials).
string mid = s@materiau_id;
if (mid != "") s@unreal_material = "/Game/PJ/Materials/MI_" + mid + ".MI_" + mid;
""", "primitive", nett)
    out_m = sub.createNode("null", "SORTIE_MAILLAGES")
    out_m.setInput(0, ue)
    out_p = sub.createNode("null", "POINTS_INSTANCES")
    out_p.setInput(0, bib)
    # Houdini Engine convertit toutes les sorties : « sorties_unreal » les vide (2 : instances de /Game/PJ/Lib,
    # 3 : prototypes à l'origine), seule la sortie 1 est créée dans Unreal.
    vides = []
    for nom, src in (("points", out_p), ("prototypes", protos)):
        v = sub.createNode("blast", f"vider_{nom}")
        v.setInput(0, src)
        v.parm("group").set("*")
        v.parm("grouptype").set(3)            # points (et leurs primitives)
        sw = sub.createNode("switch", f"sortie_unreal_{nom}")
        sw.setInput(0, src)
        sw.setInput(1, v)
        sw.parm("input").setExpression('ch("../sorties_unreal")')
        vides.append(sw)
    O.sortie(sub, out_m, 0, "sortie_maillages")
    O.sortie(sub, vides[0], 1, "sortie_points")
    O.sortie(sub, vides[1], 2, "sortie_prototypes")
    out_m.setDisplayFlag(True)
    O.ranger(sub)
    return out_m, out_p, protos


AIDE = ("Bordures en éléments préfabriqués posés le long des courbes régularisées de la description : pas selon le "
        "rayon, coupes en fin de file, chartières de raccord, pièces courbes sur mesure, joints de mortier, jitter "
        "déterministe, Z du modèle de nivellement unique (TQ-SOL-013).")
DETAILS = """== Entrées ==

1. Bordures : courbes de l'arête avant (sens : trottoir à gauche, face vue à droite) avec id, intervalles (dict[] :
   s0, s1, profil, vue_m, vue_m_fin, role), geometrie_reguliere (dict : primitives droite/arc), niv_s, niv_z_pied,
   materiau_id, aspect, joint_mm, coupe_zone. Seuls id et intervalles sont indispensables (repli : polyligne, Z du
   volume).
2. Nivellement (HeightField de pj::lire_description) : mode « volume » de l'altitude du pied.
3. Contexte (facultatif, inutilisé).

== Sorties ==

1. Maillages Y haut (materiau_id, pj_couche, pj_entite = bordure, N, uv en mètres).
2. Points d'instances de la bibliothèque : asset, unreal_instance (/Game/PJ/Lib/Bordures/SM_<asset>), orient, scale,
   graine, cd = [usure, salissure, mousse, herbe, teinte], x (traçabilité).
3. Prototypes (pivot : milieu de l'élément, face vue, dessous du bloc ; X = s, Y = v, Z = −u).

Règles : TQ-BOR-002, bordures_elements.json (regle_pas_rayon, pose, jitter, epaufrures, aretes), GA-CHR-002,
GA-ABA-004, GA-BOR-005, TQ-SOL-013. Conventions : recon/pcg/houdini/hda/README_HDA.md."""


AIDE_CANIVEAU = ("Caniveaux préfabriqués (CS1-CS3) devant la face vue des bordures : joints alignés sur ceux de la "
                 "bordure (même disposition que pj::bordure), coupes, pièces courbes sur mesure, fil d'eau du modèle de "
                 "nivellement (TQ-SOL-013 (3)).")


def construire(dossier=ICI, mode="bordure"):
    nom = "caniveau" if mode == "caniveau" else NOM
    sub = O.sous_reseau("pj_" + nom)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres(mode)))
    reseau(sub, mode)
    if mode == "caniveau":
        return O.creer_hda(sub, nom, "PJ Caniveaux (éléments préfabriqués)", parametres(mode), dossier,
                           entrees=(1, 3), sorties=3, aide=AIDE_CANIVEAU, details_aide=DETAILS,
                           module_python=module_python(), icone="SOP_sweep",
                           etiquettes_entrees=("Bordures à caniveau (courbes)", "Nivellement (HeightField)",
                                               "Contexte (facultatif)"),
                           etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"))
    return O.creer_hda(sub, NOM, "PJ Bordures (éléments préfabriqués)", parametres(), dossier, entrees=(1, 3), sorties=3,
                       aide=AIDE, details_aide=DETAILS, module_python=module_python(), icone="SOP_sweep",
                       etiquettes_entrees=("Bordures (courbes)", "Nivellement (HeightField)", "Contexte (facultatif)"),
                       etiquettes_sorties=("Maillages", "Points d'instances", "Prototypes"))


# ------------------------------------------------------------------------------------------------ essai
def essai(emprise="pilote", boite=None, mode="bordure"):
    """Réseau cuit sur la description, sans HDA : le subnet reçoit les sorties du lecteur."""
    import time
    O.installer_tout()
    obj = hou.node("/obj/_construction") or hou.node("/obj").createNode("geo", "_construction")
    lire = obj.createNode("pj::lire_description::1.0", "lire")
    lire.parm("emprise").set(emprise if boite is None else "boite")
    if boite is not None:
        lire.parmTuple("boite_min").set(boite[:2])
        lire.parmTuple("boite_max").set(boite[2:])
    bl = obj.createNode("blast", "b_bordures")
    bl.setInput(0, lire)
    bl.parm("group").set("b_caniveaux" if mode == "caniveau" else "b_bordures")
    bl.parm("negate").set(1)
    sub = O.sous_reseau("essai_" + mode)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres(mode)))
    sub.setInput(0, bl)
    sub.setInput(1, lire, 1)
    # le Python SOP lit la table depuis le module : hors HDA, on l'importe directement
    sub.node  # noqa
    out_m, out_p, protos = reseau(sub, mode)
    sub.node("lire_profils").parm("python").set(
        f"import sys\nsys.path.insert(0, r'{ICI}')\nimport profils\nprofils.lire_profils(hou.pwd())\n")
    t = time.time()
    for n in (out_p, protos, out_m):
        try:
            n.cook(force=True)
        except hou.OperationFailed as e:
            print("ECHEC", n.path(), str(e)[:2000])
            for c in sub.children():
                if c.errors():
                    print("  ", c.name(), c.errors()[:2])
            raise
    print(f"cuisson {time.time() - t:.1f} s")
    return sub


if __name__ == "__main__":
    if "--essai" in sys.argv:
        a = sys.argv[sys.argv.index("--essai") + 1:]
        if a and a[0] == "boite":
            essai(boite=[float(x) for x in a[1:5]])
        else:
            essai(a[0] if a else "pilote")
    else:
        print(construire())
