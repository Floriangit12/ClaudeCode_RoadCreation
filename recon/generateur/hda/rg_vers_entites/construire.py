"""Construit l'HDA rg::vers_entites::1.0 (modèle -> ENTITÉS au contrat de pj::lire_description : bordures pour
pj::bordure et pj::caniveau ; points de végétation) ; hython Houdini 22.

    hython recon/generateur/hda/rg_vers_entites/construire.py

Réseau (recon/generateur/hda/README_RG.md § 5) :
    entrée 1 niveaux (rg::nivellement), 2 profils (rg::lire_modele, sortie 5), 3 références (rg::graphe)
      -> bordures (VEX, primitive : files de bordures -> entités de la famille bordures : intervalles (profil, vue,
         rôle courant | chartiere | bateau), niv_s / niv_z_pied / niv_z_tete, caniveau et ses intervalles, aspect)
      -> ENTITES (sortie 1)
      -> vegetation (VEX, détail : arbres des objets le long des bandes, mode points ou pas, ancrage) -> VEGETATION
Contrat pj::bordure (README_HDA § 8) : courbe d'arête avant (face vue), trottoir à gauche ; niv_s = abscisse plane de
la courbe ; niv_z_pied = pied de face du modèle unique (TQ-SOL-013 (4)). Les rampants d'abaissé deviennent des
chartières de la longueur du modèle (2,40 m à 5 % : ARR2007, RF-MA-ABA-004), en éléments de 1,00 m au plus.
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
import rg_hda_outils as R  # noqa: E402

NOM = "vers_entites"

VEX_BORDURES = r"""
// bordures (primitive, groupe bordures) : file de bordure -> entité pj (famille bordures).
// Intervalles : vue constante -> « courant » (bateau si vue <= 0,04 m : profil <profil>_bateau s'il existe) ;
// vue linéaire sur une pièce longitudinale -> « chartiere » (rampant d'abaissé) ; retour de bordure transversal :
// pied et tête suivent les surfaces basse et haute, la vue y est linéaire par tronçon de pente constante ->
// « chartiere » (raccord de vue de pj::bordure : éléments de 1,00 m au plus, vue linéaire, GA-CHR-002), « courant »
// si la vue est constante.
int pts[] = primpoints(0, @primnum);
int n = len(pts);
float S[], ZP[], ZT[], V[], SREF[];
int K[], CAN[], GRI[];
float s = 0.0;
vector q = point(0, "P", pts[0]);
foreach (int i; int pt; pts) {
    vector p = point(0, "P", pt);
    if (i > 0) s += length(set(p.x - q.x, p.z - q.z));
    push(S, s);
    float zp = point(0, "pied", pt), zt = point(0, "tete", pt), vv = point(0, "vue", pt);
    int kd = point(0, "kind", pt), cn = point(0, "can", pt), gr = point(0, "grille", pt);
    float sr = point(0, "s_ref", pt);
    push(ZP, zp); push(ZT, zt); push(V, vv); push(K, kd); push(CAN, cn); push(GRI, gr); push(SREF, sr);
    q = p;
}
string prof = s@profil;
string bateau = prof + "_bateau";
string bateaux[] = array("T2_bateau");
if (find(bateaux, bateau) < 0) bateau = prof;
dict ivs[];
int i = 0;
while (i < n - 1) {
    if (S[i + 1] - S[i] < 1e-9) { i++; continue; }          // point de raccord doublé (angle d'un retour)
    float dv = V[i + 1] - V[i];
    int trans = K[i] == 1 && K[i + 1] == 1;
    if (trans) {
        float pente = dv / max(S[i + 1] - S[i], 1e-9);
        int j = i + 1;
        while (j < n - 1 && K[j] == 1 && K[j + 1] == 1 && S[j + 1] - S[j] > 1e-9
               && abs((V[j + 1] - V[j]) / max(S[j + 1] - S[j], 1e-9) - pente) < 1e-4) j++;
        dict d; d["s0"] = S[i]; d["s1"] = S[j]; d["profil"] = prof; d["vue_m"] = V[i];
        if (abs(V[j] - V[i]) < 1e-5) d["role"] = "courant";
        else {
            d["vue_m_fin"] = V[j]; d["role"] = "chartiere";
            // retour transversal à vue variable : même pièce que la chartière pour pj::bordure (raccord de vue), mais
            // usage distinct (correction après le second contrôle : 52 retours d'avancée de S03 typés « chartiere »,
            // confondus au placement avec la chartière d'un abaissé) ; elements.json : type raccord_vue, rôle retour
            d["usage"] = "retour";
        }
        push(ivs, d);
        i = j;
    } else if (abs(dv) < 1e-5) {
        int j = i + 1;
        while (j < n - 1 && K[j] == 0 && K[j + 1] == 0 && S[j + 1] - S[j] > 1e-9 && abs(V[j + 1] - V[j]) < 1e-5
               && abs(V[j] - V[i]) < 1e-5) j++;
        dict d; d["s0"] = S[i]; d["s1"] = S[j]; d["vue_m"] = V[i];
        if (V[i] <= 0.04 + 1e-6) { d["profil"] = bateau; d["role"] = "bateau"; }
        else { d["profil"] = prof; d["role"] = "courant"; }
        push(ivs, d);
        i = j;
    } else {
        float pente = dv / max(S[i + 1] - S[i], 1e-9);
        int j = i + 1;
        while (j < n - 1 && K[j] == 0 && K[j + 1] == 0 && S[j + 1] - S[j] > 1e-9
               && abs((V[j + 1] - V[j]) / max(S[j + 1] - S[j], 1e-9) - pente) < 1e-4) j++;
        dict d; d["s0"] = S[i]; d["s1"] = S[j]; d["profil"] = prof; d["vue_m"] = V[i]; d["vue_m_fin"] = V[j];
        d["role"] = "chartiere";
        push(ivs, d);
        i = j;
    }
}
// fusion des intervalles « courant » consécutifs de même profil et de même vue
dict iv2[];
foreach (dict d; ivs) {
    if (len(iv2) > 0) {
        dict e = iv2[-1];
        string re = e["role"], rd = d["role"], pe = e["profil"], pd = d["profil"];
        float ve = e["vue_m"], vd = d["vue_m"];
        if (re == rd && re != "chartiere" && pe == pd && abs(ve - vd) < 1e-6) {
            float s1d = d["s1"];
            e["s1"] = s1d;
            iv2[-1] = e;
            continue;
        }
    }
    push(iv2, d);
}
d[]@intervalles = iv2;
f[]@niv_s = S;
f[]@niv_z_pied = ZP;
f[]@niv_z_tete = ZT;
s@famille = "bordures";
s@ligne_ref = "arete_avant";
if (s@materiau_id == "") s@materiau_id = chs("../materiau_defaut");
dict asp;
asp["epaufrures"] = chf("../epaufrures");
asp["salissure"] = chf("../salissure");
asp["mousse_joints"] = chf("../mousse_joints");
asp["herbe_joints"] = 0.0;
d@aspect = asp;
// caniveau : intervalles (abscisse de la courbe) où il est posé (deux extrémités du segment avec caniveau)
dict can;
string cprof = s@cprof;
string props = "{}";
if (cprof != "") {
    can["profil"] = cprof;
    float c0[], c1[];
    int a = -1;
    for (int m = 0; m < n - 1; m++) {
        int on = CAN[m] && CAN[m + 1];
        if (on && a < 0) a = m;
        if ((!on || m == n - 2) && a >= 0) {
            int b = on ? m + 1 : m;
            if (S[b] - S[a] > 1e-4) {
                push(c0, S[a]);
                push(c1, S[b]);
            }
            a = -1;
        }
    }
    // caniveau à grille : caniveau déclaré relevé par un ralentisseur (rg_caniveau_releve), dans l'emprise du caniveau ;
    // fil d'eau (radier) continu = pied de la file (le ralentisseur relève la chaussée, pas le fil d'eau) ;
    // décret 94-447 annexe art. 4 (source de RF-MA-RAL-001) ; moyen constructif [G], règle demandée au propriétaire
    string gv = "";
    float g0[], g1[];
    a = -1;
    for (int m = 0; m < n - 1; m++) {
        // segment non couvert par le caniveau posé (CAN aux deux bouts) dont un bout est relevé : grille (même découpe
        // que la surface de caniveau relevée de rg::sol)
        int on = (GRI[m] || GRI[m + 1]) && !(CAN[m] && CAN[m + 1]) && K[m] == 0 && K[m + 1] == 0;
        if (on && a < 0) a = m;
        if ((!on || m == n - 2) && a >= 0) {
            int b = on ? m + 1 : m;
            if (S[b] - S[a] > 1e-4) {
                gv += sprintf("%s[%.6f,%.6f]", gv == "" ? "" : ",", S[a], S[b]);
                push(g0, S[a]); push(g1, S[b]);
            }
            a = -1;
        }
    }
    // avaloirs au pied des rampes des plateaux (Certu, Coussins et plateaux, 2010, p. 46 § 2.1.3 : « avaloirs à
    // proximité d'une des rampes d'accès » ; profil en long plat : les deux rampes) ; longueur = grille d'avaloir de
    // la bibliothèque (decal_grille_avaloir, catalogue_assets_route.json : tile_m 0,65), largeur = caniveau
    string av = "";
    f[]@avaloirs_s = array();
    float la = chf("../avaloir_longueur");
    int rpts[] = expandpointgroup(1, "ralentisseurs");
    for (int i = 0; i < len(g0); i++) {
        // abscisse de la route au milieu de l'intervalle à grille
        float sm = 0.5 * (g0[i] + g1[i]), srm = 0.0;
        for (int m = 0; m < n - 1; m++)
            if (S[m] <= sm && S[m + 1] >= sm && S[m + 1] - S[m] > 1e-9) {
                srm = SREF[m] + (sm - S[m]) / (S[m + 1] - S[m]) * (SREF[m + 1] - SREF[m]); break;
            }
        int plateau = 0;
        foreach (int q; rpts) {
            string rq = point(1, "route", q), tq = point(1, "type", q);
            float sq = point(1, "s", q), lq = point(1, "longueur_m", q);
            if (rq == s@route && tq == "plateau" && abs(srm - sq) <= lq / 2.0) plateau = 1;
        }
        if (!plateau) continue;
        if (g0[i] - la >= -1e-6) {
            av += sprintf("%s[%.6f,%.6f]", av == "" ? "" : ",", g0[i] - la, g0[i]);
            append(f[]@avaloirs_s, g0[i] - la); append(f[]@avaloirs_s, g0[i]);
        }
        if (g1[i] + la <= S[-1] + 1e-6) {
            av += sprintf("%s[%.6f,%.6f]", av == "" ? "" : ",", g1[i], g1[i] + la);
            append(f[]@avaloirs_s, g1[i]); append(f[]@avaloirs_s, g1[i] + la);
        }
    }
    // file de caniveau fermée (correction après contrôle : poches de stationnement entre les avancées de S03, « avaloir
    // à prévoir en amont de chaque avancée ») : la file s'arrête contre un retour de bordure, hors bout de la voie et
    // hors caniveau à grille qui la prolonge ; sans exutoire l'eau y stagne (décret 94-447 annexe art. 4 pour les
    // ralentisseurs ; Certu 2010 p. 46 « éviter la stagnation ») : une grille d'avaloir au bout aval (abscisses
    // croissantes de la file, profil en long plat) ; moyen [G], règle demandée au propriétaire (D-CORR-9)
    if (chi("../avaloir_fin_de_file")) {
        foreach (float x; c1) {
            if (x >= S[-1] - 1e-3 || x - la < -1e-6) continue;
            int suivi = 0;
            foreach (float y; g0) if (abs(y - x) < 1e-4) suivi = 1;
            if (suivi) continue;
            av += sprintf("%s[%.6f,%.6f]", av == "" ? "" : ",", x - la, x);
            append(f[]@avaloirs_s, x - la); append(f[]@avaloirs_s, x);
        }
    }
    // l'avaloir remplace le caniveau qu'il occupe : intervalles du caniveau moins ceux des avaloirs (correction après le
    // second contrôle : avaloirs posés par-dessus les éléments de caniveau, deux pièces au même endroit dans
    // elements.json ; S03 : 26 recouvrements, S10 : 8)
    float avs[] = f[]@avaloirs_s;
    string iv = "";
    for (int q = 0; q < len(c0); q++) {
        float sa[] = array(c0[q]), sb[] = array(c1[q]);
        for (int r = 0; r + 1 < len(avs); r += 2) {
            float x0 = avs[r], x1 = avs[r + 1];
            float na[], nb[];
            for (int u = 0; u < len(sa); u++) {
                if (x1 <= sa[u] + 1e-6 || x0 >= sb[u] - 1e-6) { push(na, sa[u]); push(nb, sb[u]); continue; }
                if (x0 - sa[u] > 1e-4) { push(na, sa[u]); push(nb, x0); }
                if (sb[u] - x1 > 1e-4) { push(na, x1); push(nb, sb[u]); }
            }
            sa = na; sb = nb;
        }
        for (int u = 0; u < len(sa); u++) iv += sprintf("%s[%.6f,%.6f]", iv == "" ? "" : ",", sa[u], sb[u]);
    }
    f[]@grille_s = array();
    foreach (int i; float x; g0) { append(f[]@grille_s, x); append(f[]@grille_s, g1[i]); }
    props = sprintf("{\"caniveau_grille\":{\"intervalles\":[%s]},\"avaloirs\":{\"intervalles\":[%s],"
                    "\"materiau_id\":\"grille_avaloir\"},\"caniveau\":{\"intervalles\":[%s],\"profil\":\"%s\"}}",
                    gv, av, iv, cprof);
}
d@caniveau = can;
s@props = props;
"""

VEX_AVALOIRS = r"""
// avaloirs (détail ; entrée 0 : files de bordures avec avaloirs_s, wcp, dhcp, pied) : grille d'avaloir posée dans le
// caniveau, de la face de la bordure (fil d'eau) à l'arête côté chaussée (largeur du caniveau), au niveau du dessus du
// caniveau (plan de la face au fil d'eau, arête = fil d'eau + Δh) ; UV 0-1 sur la grille ; materiau_id grille_avaloir.
// Côté chaussée = droite de la file (trottoir à gauche) : cross(T, haut). L'avaloir remplace le caniveau qu'il occupe
// (second contrôle) : sous la grille, corps fermé de l'avaloir (parois et fond, partie = « corps ») jusqu'à 0,25 m
// sous le fil d'eau, sous l'assise du caniveau ; la grille seule (partie = « grille ») donne la position de l'élément.
addprimattrib(0, "id", "");
addprimattrib(0, "bordure", "");
addprimattrib(0, "materiau_id", "");
addprimattrib(0, "partie", "");
addprimattrib(0, "s0", 0.0);
addprimattrib(0, "s1", 0.0);
addvertexattrib(0, "uv", {0, 0, 0});
float prof = 0.25;
for (int pr = 0; pr < nprimitives(1); pr++) {
    float av[] = prim(1, "avaloirs_s", pr);
    if (len(av) < 2) continue;
    int pts[] = primpoints(1, pr);
    int n = len(pts);
    float S[];
    float s = 0.0;
    vector q = point(1, "P", pts[0]);
    foreach (int i; int pt; pts) {
        vector p = point(1, "P", pt);
        if (i > 0) s += length(set(p.x - q.x, p.z - q.z));
        push(S, s);
        q = p;
    }
    string kid = prim(1, "id", pr);
    for (int k = 0; k + 1 < len(av); k += 2) {
        int ring[], bas[];
        int ns = 4;
        for (int j = 0; j <= ns; j++) {
            float sj = av[k] + (av[k + 1] - av[k]) * j / ns;
            int m = 0;
            while (m < n - 2 && S[m + 1] < sj) m++;
            if (S[m + 1] - S[m] < 1e-9 && m < n - 2) m++;
            float u = clamp((sj - S[m]) / max(S[m + 1] - S[m], 1e-9), 0.0, 1.0);
            vector a = point(1, "P", pts[m]), b = point(1, "P", pts[m + 1]);
            vector P = lerp(a, b, u);
            vector T = normalize(set(b.x - a.x, 0, b.z - a.z));
            vector dr = normalize(cross(T, {0, 1, 0}));           // côté chaussée (droite de la file)
            float wc = lerp(float(point(1, "wcp", pts[m])), float(point(1, "wcp", pts[m + 1])), u);
            float dh = lerp(float(point(1, "dhcp", pts[m])), float(point(1, "dhcp", pts[m + 1])), u);
            float zf = P.y;                                        // fil d'eau (pied de la face)
            vector Pf = set(P.x, zf, P.z);
            vector Pa = set(P.x + wc * dr.x, zf + dh, P.z + wc * dr.z);
            push(ring, addpoint(0, Pf));
            push(ring, addpoint(0, Pa));
            push(bas, addpoint(0, Pf - set(0, prof, 0)));
            push(bas, addpoint(0, Pa - set(0, prof, 0)));
        }
        string aid = sprintf("%s/AV%02d", kid, k / 2);
        int faces[];
        for (int j = 0; j < ns; j++) {
            int f = addprim(0, "poly", ring[2 * j], ring[2 * j + 2], ring[2 * j + 3], ring[2 * j + 1]);
            setprimattrib(0, "partie", f, "grille");
            setvertexattrib(0, "uv", f, 0, set(float(j) / ns, 0, 0));
            setvertexattrib(0, "uv", f, 1, set(float(j + 1) / ns, 0, 0));
            setvertexattrib(0, "uv", f, 2, set(float(j + 1) / ns, 1, 0));
            setvertexattrib(0, "uv", f, 3, set(float(j) / ns, 1, 0));
            push(faces, f);
            // parois côté face de la bordure et côté chaussée, fond
            int g1 = addprim(0, "poly", ring[2 * j], bas[2 * j], bas[2 * j + 2], ring[2 * j + 2]);
            int g2 = addprim(0, "poly", ring[2 * j + 1], ring[2 * j + 3], bas[2 * j + 3], bas[2 * j + 1]);
            int g3 = addprim(0, "poly", bas[2 * j], bas[2 * j + 1], bas[2 * j + 3], bas[2 * j + 2]);
            int gs[] = array(g1, g2, g3);
            foreach (int g; gs) { setprimattrib(0, "partie", g, "corps"); push(faces, g); }
        }
        // parois des deux bouts (contre le caniveau coupé)
        int e0 = addprim(0, "poly", ring[0], ring[1], bas[1], bas[0]);
        int e1 = addprim(0, "poly", ring[2 * ns], bas[2 * ns], bas[2 * ns + 1], ring[2 * ns + 1]);
        int es[] = array(e0, e1);
        foreach (int g; es) { setprimattrib(0, "partie", g, "corps"); push(faces, g); }
        foreach (int f; faces) {
            setprimattrib(0, "id", f, aid);
            setprimattrib(0, "bordure", f, kid);
            setprimattrib(0, "materiau_id", f, "grille_avaloir");
            setprimattrib(0, "s0", f, av[k]);
            setprimattrib(0, "s1", f, av[k + 1]);
        }
    }
}
"""

VEX_VEGETATION = r"""
// vegetation (détail) : arbres d'alignement des bandes (objets_le_long, famille vegetation) : mode « points »
// (s_points) ou « pas » (pas_m, phase_m, intervalle) ; ancrage rive_gauche | centre | rive_droite + decalage_m
// (t positif à gauche) ; seulement dans les sections dont le profil porte l'objet. Points : P (au sol du modèle non
// évalué : y = 0), id, route, s, t, type, bande. Entrées : 0 références, 1 niveaux, 2 profils.
addpointattrib(0, "id", "");
addpointattrib(0, "route", "");
addpointattrib(0, "type", "");
addpointattrib(0, "bande", "");
addpointattrib(0, "s", 0.0);
addpointattrib(0, "t", 0.0);
// dimensions de l'arbre portées par le modèle (correction après contrôle) : essence, hauteur, houppier, fût
addpointattrib(0, "asset_id", "");
addpointattrib(0, "hauteur_m", 0.0);
addpointattrib(0, "houppier_rayon_m", 0.0);
addpointattrib(0, "fut_m", 0.0);
for (int pr = 0; pr < nprimitives(0); pr++) {
    if (!inprimgroup(0, "echantillonnees", pr)) continue;
    string rid = prim(0, "id", pr);
    float SEC0[] = prim(0, "sec_s0", pr);
    float SEC1[] = prim(0, "sec_s1", pr);
    string SP[] = prim(0, "sec_profil", pr);
    float L = prim(0, "longueur_m", pr);
    for (int k = 0; k < len(SEC0); k++) {
        int pp = rg_point_profil(2, SP[k]);
        int sp = rg_point_section(1, rid, k);
        string bjs[] = point(2, "bande_json", pp);
        string bid[] = point(2, "bande_id", pp);
        for (int b = 0; b < len(bjs); b++) {
            dict bj = json_loads(bjs[b], 0);
            if (!isvalidindex(bj, "objets_le_long")) continue;
            dict objs[] = bj["objets_le_long"];
            foreach (dict o; objs) {
                string fam = isvalidindex(o, "famille") ? string(o["famille"]) : "";
                if (fam != "vegetation") continue;
                string mode = o["mode"];
                float ss[];
                if (mode == "points") { float x[] = o["s_points"]; ss = x; }
                else if (mode == "pas") {
                    // s = début de l'intervalle (0 sans intervalle) + phase_m + k · pas_m (phase comptée depuis le
                    // début de l'intervalle, comme la phase d'une ligne : schéma modele_voie/0.1, marque_ligne)
                    float pas = o["pas_m"];
                    float ph = isvalidindex(o, "phase_m") ? float(o["phase_m"]) : 0.0;
                    float i0 = 0.0, i1 = L;
                    if (isvalidindex(o, "intervalle")) { dict iv = o["intervalle"]; i0 = iv["s0"]; i1 = iv["s1"]; }
                    for (int m = 0; m < 100000; m++) {
                        float x = i0 + ph + m * pas;
                        if (x > i1 + 1e-9 || x > L + 1e-9) break;
                        push(ss, x);
                    }
                }
                string ref = "centre";
                float dec = 0.0;
                if (isvalidindex(o, "ancrage")) { dict an = o["ancrage"]; ref = an["reference"]; if (isvalidindex(an, "decalage_m")) dec = an["decalage_m"]; }
                string oid = isvalidindex(o, "id") ? string(o["id"]) : sprintf("veg_%s", bid[b]);
                string ty = o["type"];
                string asset = isvalidindex(o, "asset_id") ? string(o["asset_id"]) : "";
                float hm = isvalidindex(o, "hauteur_m") ? float(o["hauteur_m"]) : 0.0;
                float rh = isvalidindex(o, "houppier_rayon_m") ? float(o["houppier_rayon_m"]) : 0.0;
                float fm = isvalidindex(o, "fut_m") ? float(o["fut_m"]) : 0.0;
                foreach (int m; float x; ss) {
                    if (x < SEC0[k] - 1e-9 || x > SEC1[k] + 1e-9) continue;
                    float T[] = rg_t_limites(1, sp, x);
                    float t = ref == "rive_gauche" ? T[b] + dec : (ref == "rive_droite" ? T[b + 1] + dec : 0.5 * (T[b] + T[b + 1]) + dec);
                    vector2 xy = rg_local_st(0, pr, x, t);
                    int p = addpoint(0, set(xy.x, 0, -xy.y));
                    setpointattrib(0, "id", p, sprintf("%s-%03d", oid, m));
                    setpointattrib(0, "route", p, rid);
                    setpointattrib(0, "type", p, ty);
                    setpointattrib(0, "bande", p, bid[b]);
                    setpointattrib(0, "asset_id", p, asset);
                    setpointattrib(0, "hauteur_m", p, hm);
                    setpointattrib(0, "houppier_rayon_m", p, rh);
                    setpointattrib(0, "fut_m", p, fm);
                    setpointattrib(0, "s", p, x);
                    setpointattrib(0, "t", p, t);
                    setpointgroup(0, "arbres", p, 1);
                }
            }
        }
    }
}
"""


def parametres():
    T = hou
    F = T.FloatParmTemplate
    return [
        T.StringParmTemplate("materiau_defaut", "Matériau des bordures (si le modèle n'en dit pas)", 1,
                             default_value=("beton_bordure_gris",),
                             help="materiau_id par défaut de pj::bordure (béton gris)."),
        F("epaufrures", "Aspect : épaufrures", 1, default_value=(0.1,), min=0.0, max=1.0,
          help="Choix de rendu (aucune règle) : bordure récente (< 0,2 : joints 5,5-7 mm, pj::bordure)."),
        F("salissure", "Aspect : salissure", 1, default_value=(0.2,), min=0.0, max=1.0, help="Choix de rendu."),
        F("mousse_joints", "Aspect : mousse des joints", 1, default_value=(0.05,), min=0.0, max=1.0,
          help="Choix de rendu."),
        F("avaloir_longueur", "Longueur d'une grille d'avaloir (m)", 1, default_value=(0.65,), min=0.2, max=2.0,
          help="Grille d'avaloir posée au pied de chaque rampe de plateau, dans le caniveau (Certu, Coussins et plateaux, "
               "2010, p. 46 § 2.1.3) ; 0,65 m = asset decal_grille_avaloir de assets/specs/route/catalogue_assets_route.json "
               "(tile_m). Aucune règle de regles_route_fr.json ne la cote : règle demandée au propriétaire de la base."),
        T.ToggleParmTemplate("avaloir_fin_de_file", "Avaloir au bout d'une file de caniveau fermée", default_value=True,
                             help="Grille d'avaloir au bout aval (abscisses croissantes) de toute file de caniveau qui "
                                  "s'arrête contre un retour de bordure (avancée, îlot), hors bout de la voie et hors "
                                  "caniveau à grille : sans exutoire, l'eau stagne. Moyen [G] (aucune règle de "
                                  "regles_route_fr.json ; demande D-CORR-9 de validation/regles_demandees_correction.json)."),
    ]


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    e1, e2, e3 = sub.indirectInputs()[:3]
    gb = sub.createNode("blast", "files_de_bordures")
    gb.setInput(0, e1)
    gb.parm("group").set("bordures")
    gb.parm("grouptype").set("prims")
    gb.parm("negate").set(1)
    # boucles fermées (îlot central isolé : la bordure en fait le tour) ouvertes au premier point, le dernier point
    # répétant le premier : pj::bordure ne pose que des courbes ouvertes (correction après contrôle : îlot de S_M24
    # sans bordure)
    ouv = R.wrangle(sub, "ouvrir_boucles", r"""
if (primintrinsic(0, "closed", @primnum)) {
    int pts[] = primpoints(0, @primnum);
    addvertex(0, @primnum, pts[0]);
    setprimintrinsic(0, "closed", @primnum, 0);
}
""", "primitive", gb)
    bor = R.wrangle(sub, "bordures", VEX_BORDURES, "primitive", ouv, entrees=(e1,))
    # contrat de pj::bordure : attributs de la description seulement (les attributs internes du nivellement, « kind »
    # entier notamment, entraient en collision avec ceux de pj::bordure : kind = element | joint)
    net = sub.createNode("attribdelete", "contrat_pj")
    net.setInput(0, bor)
    net.parm("ptdel").set("* ^P")
    net.parm("vtxdel").set("*")
    net.parm("primdel").set("* ^id ^famille ^ligne_ref ^intervalles ^niv_s ^niv_z_pied ^niv_z_tete ^aspect ^caniveau "
                            "^props ^materiau_id ^route ^grille_s ^avaloirs_s")
    net.parm("dtldel").set("*")
    grp = sub.createNode("groupdelete", "groupes")
    grp.setInput(0, net)
    grp.parm("group1").set("*")
    out = sub.createNode("null", "ENTITES")
    out.setInput(0, grp)
    R.sortie(sub, out, 0, "sortie_entites")
    out.setDisplayFlag(True)
    veg = R.wrangle(sub, "vegetation", VEX_VEGETATION, "detail", None, entrees=(e1, e2),
                    bibliotheques=("rg_geometrie.h", "rg_niveau.h"))
    veg.setInput(0, e3)
    gv = sub.createNode("blast", "arbres")
    gv.setInput(0, veg)
    gv.parm("group").set("arbres")
    gv.parm("grouptype").set("points")
    gv.parm("negate").set(1)
    gv.parm("removegrp").set(0)
    nv = sub.createNode("attribdelete", "attributs_vegetation")
    nv.setInput(0, gv)
    nv.parm("ptdel").set("* ^P ^id ^route ^type ^bande ^s ^t ^asset_id ^hauteur_m ^houppier_rayon_m ^fut_m")
    nv.parm("primdel").set("*")
    nv.parm("dtldel").set("*")
    sv = sub.createNode("null", "VEGETATION")
    sv.setInput(0, nv)
    R.sortie(sub, sv, 1, "sortie_vegetation")
    # sortie 3 : grilles d'avaloir (correction après contrôle : fil d'eau des ralentisseurs)
    av = R.wrangle(sub, "avaloirs", VEX_AVALOIRS, "detail", None, entrees=(bor,))
    va = sub.createNode("null", "AVALOIRS")
    va.setInput(0, av)
    R.sortie(sub, va, 2, "sortie_avaloirs")
    R.ranger(sub)
    aide = ("Modèle -> entités au contrat de pj::lire_description : bordures (intervalles courant, chartière, bateau ; "
            "niv_s, niv_z_pied, niv_z_tete ; caniveau et ses intervalles ; aspect) pour pj::bordure et pj::caniveau ; "
            "points des arbres d'alignement ; caniveau à grille au droit des ralentisseurs (intervalles dans props) et "
            "grilles d'avaloir au pied des rampes de plateau et au bout des files de caniveau fermées (sortie 3), qui "
            "remplacent le caniveau qu'elles occupent (intervalles du caniveau coupés) ; retours transversaux à vue "
            "variable marqués usage = retour (elements.json : raccord_vue).")
    details = ("== Entrées ==\n\n1. Niveaux (rg::nivellement), 2. Profils (rg::lire_modele, sortie 5), 3. Références "
               "(rg::graphe).\n\n== Sorties ==\n\n1. Entités bordures (polylignes au pied, côté haut à gauche).\n"
               "2. Végétation (points : id, route, type, bande, s, t).\n3. Grilles d'avaloir (quadrilatères dans le "
               "caniveau, au pied des rampes de plateau et au bout aval des files de caniveau fermées par un retour de "
               "bordure ; id, bordure, s0, s1, materiau_id grille_avaloir).\n\n"
               "Règles : TQ-SOL-013, RF-MA-ABA-004, DEF-030 ; écoulement des eaux : décret 94-447 annexe art. 4 "
               "(source de RF-MA-RAL-001), Certu Coussins et plateaux 2010 p. 46 (avaloirs) ; moyens [G] déclarés.")
    return R.creer_hda(sub, NOM, "RG Vers entités (contrat pj::*)", parametres(), dossier, entrees=(3, 3), sorties=3,
                       aide=aide, details_aide=details, icone="SOP_attribcopy",
                       etiquettes_entrees=("Niveaux", "Profils", "Références échantillonnées"),
                       etiquettes_sorties=("Entités (bordures)", "Végétation", "Grilles d'avaloir"))


if __name__ == "__main__":
    print(construire())
