"""Décor de rendu (hython) : arbres procéduraux simples posés aux points d'arbres du modèle (rg::vers_entites, sortie
2), sur le sol fabriqué. Construction par nœuds SOP (script de construction) ; aucune donnée de la route n'est créée
ici : les positions viennent du modèle (objets_le_long des bandes), la forme est un aperçu (lot L8 : végétation).

Arbre : tronc conique (Tube), houppier de sphères bruitées (Sphere + Attribute Noise) dans un ellipsoïde ; variations
déterministes par arbre (graine = hachage de l'id : échelle 0,85-1,15, lacet).
"""
import hou

VEX_POSER = r"""
// poser (point) : Z du sol fabriqué sous l'arbre (rayon vertical, entrée 1), échelle et lacet déterministes.
vector hit, uvw;
int pr = intersect(1, set(@P.x, 100.0, @P.z), {0, -200, 0}, hit, uvw);
if (pr >= 0) @P.y = hit.y;
int g = random_shash(s@id);
f@pscale = fit01(rand(g % 100003), 0.85, 1.15) * chf("echelle");
float lac = 2 * PI * rand((g + 7) % 100003);
p@orient = quaternion(lac, {0, 1, 0});
"""

VEX_HOUPPIER = r"""
// houppier (détail) : centres des touffes dans un ellipsoïde (rayon R, centre à H) : une masse centrale et 34
// touffes de 0,30 R à 0,45 R réparties en surface (silhouette de houppier d'alignement, sans trou).
float R = chf("../rayon"), H = chf("../hauteur_houppier");
int p0 = addpoint(0, set(0, H, 0));
setpointattrib(0, "pscale", p0, 0.78 * R);
for (int i = 0; i < 34; i++) {
    vector u = set(rand(i * 3 + 1), rand(i * 3 + 2), rand(i * 3 + 3));
    float a = 2 * PI * u.x, cz = 1.6 * u.y - 0.7;
    vector d = set(sqrt(max(0.0, 1 - cz * cz)) * cos(a), cz * 0.85, sqrt(max(0.0, 1 - cz * cz)) * sin(a));
    int p = addpoint(0, set(0, H, 0) + d * fit01(u.z, 0.55, 0.8) * R);
    setpointattrib(0, "pscale", p, R * fit01(rand(i * 5 + 11), 0.30, 0.45));
}
"""


def construire_arbres(parent, points, sol, rayon=2.5, hauteur_tronc=2.6):
    """Réseau d'arbres dans `parent` (géométrie SOP) : renvoie le nœud de sortie (maillages, materiau_id) ; réutilisé
    s'il existe déjà (une scène après l'autre dans la même session)."""
    if parent.node("arbres") is not None:
        return parent.node("arbres")
    tronc = parent.createNode("tube", "tronc")
    for p, v in (("type", 1), ("cap", 1), ("rad1", 0.16), ("rad2", 0.09), ("height", hauteur_tronc + 1.2),
                 ("ty", (hauteur_tronc + 1.2) / 2), ("cols", 12), ("rows", 4)):
        tronc.parm(p).set(v)
    mt = parent.createNode("attribwrangle", "tronc_materiau")
    mt.parm("class").set(1)
    mt.parm("snippet").set('s@materiau_id = "ecorce";')
    mt.setInput(0, tronc)
    centres = parent.createNode("attribwrangle", "houppier_centres")
    centres.parm("class").set(0)
    tg = centres.parmTemplateGroup()
    tg.append(hou.FloatParmTemplate("rayon", "rayon", 1, default_value=(rayon,)))
    tg.append(hou.FloatParmTemplate("hauteur_houppier", "hauteur", 1, default_value=(hauteur_tronc + rayon * 0.85,)))
    centres.setParmTemplateGroup(tg)
    centres.parm("snippet").set(VEX_HOUPPIER.replace("../", ""))
    sph = parent.createNode("sphere", "boule")
    sph.parm("type").set(2)               # polygones (polymesh)
    sph.parm("freq").set(4)
    cp = parent.createNode("copytopoints::2.0", "houppier")
    cp.setInput(0, sph)
    cp.setInput(1, centres)
    noise = parent.createNode("attribnoise::2.0", "feuillage_bosses")
    noise.setInput(0, cp)
    for p, v in (("attribs", "P"), ("displace", 1), ("amplitude", 0.22), ("elementsize", 0.45)):
        noise.parm(p).set(v)
    mf = parent.createNode("attribwrangle", "feuillage_materiau")
    mf.parm("class").set(1)
    mf.parm("snippet").set('s@materiau_id = "feuillage";')
    mf.setInput(0, noise)
    proto = parent.createNode("merge", "arbre")
    proto.setInput(0, mt)
    proto.setInput(1, mf)
    nrm = parent.createNode("normal", "arbre_normales")
    nrm.setInput(0, proto)
    nrm.parm("type").set(1)
    nrm.parm("cuspangle").set(60.0)
    pos = parent.createNode("attribwrangle", "poser")
    pos.parm("class").set(2)
    tg = pos.parmTemplateGroup()
    tg.append(hou.FloatParmTemplate("echelle", "échelle", 1, default_value=(1.0,)))
    pos.setParmTemplateGroup(tg)
    pos.parm("snippet").set(VEX_POSER)
    pos.setInput(0, points)
    pos.setInput(1, sol)
    cop = parent.createNode("copytopoints::2.0", "arbres")
    cop.setInput(0, nrm)
    cop.setInput(1, pos)
    return cop
