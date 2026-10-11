// pj_repere.h : conversions de repère du projet (README_HDA.md § 2).
// Description / USD / pj_points : local Z haut (x, y, z) ; Houdini : Y haut (x, z, -y) ; C = Rx(+90°) : Houdini -> local.
#ifndef PJ_REPERE_H
#define PJ_REPERE_H

function vector pj_vers_local(vector P) { return set(P.x, -P.z, P.y); }
function vector pj_vers_houdini(vector p) { return set(p.x, p.z, -p.y); }

// Rotation Houdini (orient, [x, y, z, w]) -> rotation dans le repère local : q_l = c q c^-1, c = Rx(+90°).
// Représentant à w >= 0 (pj_commun.q_xyzw).
function vector4 pj_quat_vers_local(vector4 q)
{
    vector4 c = quaternion(radians(90.0), {1, 0, 0});
    vector4 r = qmultiply(qmultiply(c, q), qinvert(c));
    r = normalize(r);
    if (r.w < 0) r = -r;
    return r;
}

// Angles [r, p, y] (degrés) ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r) (convention de pj_tools/repere.py) d'une
// rotation locale q. Les colonnes de R sont les images des axes : R[i][j] = composante i de l'image de l'axe j.
function vector pj_rpy_local(vector4 q)
{
    vector ex = qrotate(q, {1, 0, 0});
    vector ey = qrotate(q, {0, 1, 0});
    vector ez = qrotate(q, {0, 0, 1});
    // R00 = ex.x, R10 = ex.y, R20 = ex.z, R21 = ey.z, R22 = ez.z
    float p = asin(clamp(-ex.z, -1.0, 1.0));
    float r = atan2(ey.z, ez.z);
    float y = atan2(ex.y, ex.x);
    if (abs(ex.z) > 0.999999) {          // blocage de cardan : roulis reporté sur le lacet
        r = 0;
        y = atan2(-ey.x, ey.y);
    }
    return set(degrees(r), degrees(p), degrees(y));
}

// Nom de prim USD valide ([A-Za-z0-9_], ne commence pas par un chiffre) : "K-0005" -> "K_0005".
function string pj_nom_prim(string s)
{
    string r = re_replace("[^A-Za-z0-9_]", "_", s);
    if (r == "" || re_match("^[0-9]", r)) r = "_" + r;
    return r;
}

#endif
