#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Téléchargement reproductible des matériaux CC0 de la librairie (ambientCG, Poly Haven).

À lancer sur le PC (Python 3.9+, numpy, Pillow ; pxr/usd-core facultatif pour valider l'USD) :

    python assets/telecharger_cc0.py --liste
    python assets/telecharger_cc0.py                          # tous les matériaux, 2K, dans assets/lib/materiaux/
    python assets/telecharger_cc0.py --materiaux enrobe_bbsg_ancien gazon_tondu --resolution 1K
    python assets/telecharger_cc0.py --resolution 4K          # 4K hors dépôt : data/raw/assets_src/materiaux_4k/
    python assets/telecharger_cc0.py --verifier               # vérifie les URL du manifeste sans rien écrire
    python assets/telecharger_cc0.py --peinture               # masques d'usure + matériaux de peinture (specs/peinture.json)
    python assets/telecharger_cc0.py --seuils masque.png      # seuils d'usure pour un masque fait dans Houdini

Pour chaque matériau du manifeste (assets/manifeste_cc0.json) :
  1. télécharge la résolution choisie dans le cache (data/raw/assets_src/cc0/, non versionné) ;
  2. vérifie : taille annoncée, md5 (Poly Haven), intégrité du zip (ambientCG), dimensions des images ;
  3. applique la correction de teinte en CIE Lab (gain/décalage) à l'albédo, et le réglage de rugosité ;
  4. écrit assets/lib/materiaux/<nom>/textures/*.jpg|png, <nom>.usda (UsdPreviewSurface, Z-up, mètres,
     textures en chemins relatifs) et meta.json (source, licence, tile_m, correction, empreintes sha256).

Textures écrites : albédo, rugosité, AO en JPEG q90 ; normale (OpenGL, +Y) et opacité en PNG ;
hauteur en PNG 16 bits (option --hauteur). Par défaut (mode « dépôt ») l'albédo est à la résolution
demandée et les autres cartes à 1K au plus, pour tenir le budget de la librairie ; --complet garde
toutes les cartes à la résolution demandée.

Licence des sources : CC0 1.0 (aucune attribution requise ; auteurs indiqués dans meta.json par courtoisie).
"""
import argparse
import datetime
import fnmatch
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

import numpy as np
from PIL import Image

VERSION = "1.0 (2026-10-09)"
ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(ICI)
UA = {"User-Agent": "MeylanADAS-librairie/1.0 (telecharger_cc0.py)"}
RES_PX = {"1K": 1024, "2K": 2048, "4K": 4096}
Image.MAX_IMAGE_PIXELS = None


# --------------------------------------------------------------------------------------------
# couleur : sRGB <-> CIE Lab (D65), numpy pur
# --------------------------------------------------------------------------------------------
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_MI = np.linalg.inv(_M)
_W = np.array([0.95047, 1.0, 1.08883])


def srgb_vers_lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_vers_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _f(t):
    d = 6 / 29
    return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)


def _fi(t):
    d = 6 / 29
    return np.where(t > d, t ** 3, 3 * d * d * (t - 4 / 29))


def rgb_vers_lab(rgb01):
    xyz = srgb_vers_lin(rgb01) @ _M.T / _W
    f = _f(xyz)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_vers_rgb(lab):
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    xyz = np.stack([_fi(fx), _fi(fy), _fi(fz)], -1) * _W
    return lin_vers_srgb(xyz @ _MI.T)


def lab_moyen(rgb01, pas=4):
    return rgb_vers_lab(rgb01[::pas, ::pas].reshape(-1, 3)).mean(0)


def corriger_lab(rgb01, c, bloc=512):
    """L' = gL·L + oL ; a' = gab·a + oa ; b' = gab·b + ob (par blocs pour limiter la mémoire)."""
    out = np.empty_like(rgb01)
    for y in range(0, rgb01.shape[0], bloc):
        lab = rgb_vers_lab(rgb01[y:y + bloc])
        lab[..., 0] = np.clip(c["gain_L"] * lab[..., 0] + c["decalage_L"], 0, 100)
        lab[..., 1] = c["gain_ab"] * lab[..., 1] + c["decalage_a"]
        lab[..., 2] = c["gain_ab"] * lab[..., 2] + c["decalage_b"]
        out[y:y + bloc] = np.clip(lab_vers_rgb(lab), 0, 1)
    return out


# --------------------------------------------------------------------------------------------
# outils
# --------------------------------------------------------------------------------------------
def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def md5(chemin):
    h = hashlib.md5()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def telecharger(url, dest, taille=None, md5_attendu=None, essais=4):
    """Télécharge url -> dest (via .part), avec reprise simple, contrôle de taille et de md5."""
    if os.path.exists(dest):
        ok = (taille is None or os.path.getsize(dest) == taille) and (md5_attendu is None or md5(dest) == md5_attendu)
        if ok:
            return dest
        os.remove(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for k in range(essais):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r, open(dest + ".part", "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            if taille is not None and os.path.getsize(dest + ".part") != taille:
                raise IOError(f"taille {os.path.getsize(dest + '.part')} ≠ {taille} annoncée")
            if md5_attendu is not None and md5(dest + ".part") != md5_attendu:
                raise IOError("md5 différent de celui de l'API")
            os.replace(dest + ".part", dest)
            return dest
        except (urllib.error.URLError, IOError, TimeoutError) as e:
            log(f"  essai {k + 1}/{essais} échoué : {e}")
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"échec du téléchargement : {url}")


def verifier_url(url, taille=None):
    """Requête HEAD (ou GET des premiers octets) : renvoie (ok, message)."""
    for methode in ("HEAD", "GET"):
        try:
            h = dict(UA)
            if methode == "GET":
                h["Range"] = "bytes=0-1023"
            req = urllib.request.Request(url, headers=h, method=methode)
            with urllib.request.urlopen(req, timeout=60) as r:
                code = r.status
                lg = r.headers.get("Content-Length")
                cr = r.headers.get("Content-Range")
                tot = int(cr.split("/")[-1]) if cr and "/" in cr and cr.split("/")[-1].isdigit() else (int(lg) if lg and methode == "HEAD" else None)
                if taille is not None and tot is not None and tot != taille:
                    return False, f"HTTP {code}, taille {tot} ≠ {taille}"
                return True, f"HTTP {code}" + (f", {tot} o" if tot else "")
        except urllib.error.HTTPError as e:
            if methode == "GET":
                return False, f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            if methode == "GET":
                return False, str(e)
    return False, "?"


def lire_image(src):
    im = Image.open(src)
    im.load()
    return im


def redim(im, n, normale=False):
    if im.size[0] == n:
        return im
    if normale:
        a = np.asarray(im.convert("RGB"), np.float32) / 255.0 * 2 - 1
        b = np.asarray(Image.fromarray(((a + 1) / 2 * 255).astype(np.uint8)).resize((n, n), Image.LANCZOS), np.float32) / 255.0 * 2 - 1
        b /= np.maximum(np.linalg.norm(b, axis=-1, keepdims=True), 1e-6)
        return Image.fromarray(np.clip((b + 1) / 2 * 255 + 0.5, 0, 255).astype(np.uint8))
    return im.resize((n, n), Image.LANCZOS)


def gris(im):
    """Carte scalaire : canal unique (L ; la plupart des cartes CC0 sont déjà en niveaux de gris)."""
    if im.mode in ("I;16", "I;16B", "I", "F"):
        a = np.asarray(im, np.float64)
        return Image.fromarray(np.clip(a / (65535.0 if a.max() > 255 else 255.0) * 255 + 0.5, 0, 255).astype(np.uint8))
    return im.convert("L")


# --------------------------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------------------------
ROLES = ("albedo", "normale", "rugosite", "ao", "hauteur", "opacite", "metal")


def obtenir_cartes(m, res, cache, hauteur):
    """Renvoie {role: chemin local} dans le cache, après vérification."""
    tel = m["telechargements"].get(res)
    if tel is None:
        raise RuntimeError(f"{m['nom']} : résolution {res} absente du manifeste")
    dossier = os.path.join(cache, m["source"].replace(" ", "_").lower(), m["id"], res)
    os.makedirs(dossier, exist_ok=True)
    cartes = {}
    if tel["format"] == "zip":
        zp = telecharger(tel["url"], os.path.join(dossier, tel["fichier"]), tel.get("taille_o"))
        with zipfile.ZipFile(zp) as z:
            mauvais = z.testzip()
            if mauvais:
                raise RuntimeError(f"zip corrompu ({mauvais}) : {zp}")
            noms = z.namelist()
            for role, motif in m["cartes_zip"].items():
                if role == "hauteur" and not hauteur:
                    continue
                cand = [n for n in noms if fnmatch.fnmatch(os.path.basename(n), motif)]
                if role == "normale" and not cand:      # anciens paquets : *_Normal.jpg (= OpenGL)
                    cand = [n for n in noms if fnmatch.fnmatch(os.path.basename(n), "*_Normal.jpg")]
                if not cand:
                    continue
                dst = os.path.join(dossier, os.path.basename(cand[0]))
                if not os.path.exists(dst):
                    with z.open(cand[0]) as f, open(dst, "wb") as g:
                        g.write(f.read())
                cartes[role] = dst
    else:
        for role, f in tel["fichiers"].items():
            if role == "hauteur" and not hauteur:
                continue
            dst = os.path.join(dossier, os.path.basename(f["url"]))
            cartes[role] = telecharger(f["url"], dst, f.get("taille_o"), f.get("md5"))
    if "albedo" not in cartes:
        raise RuntimeError(f"{m['nom']} : pas de carte d'albédo dans la source")
    return cartes


# --------------------------------------------------------------------------------------------
# USD (texte, sans dépendance ; validé par pxr si disponible)
# --------------------------------------------------------------------------------------------
def ecrire_usda(chemin, nom, tex, tile_m, primvar, meta_court, decalque):
    s = 1.0 / float(tile_m) if primvar == "st1" else 1.0
    racine = f"/{nom}"
    L = ["#usda 1.0", "(",
         f'    defaultPrim = "{nom}"', "    metersPerUnit = 1", '    upAxis = "Z"',
         '    doc = "Matériau CC0 de la librairie Paquet Jardin (assets/telecharger_cc0.py). UsdPreviewSurface ; UV en mètres (st1) mis à l\'échelle par tile_m."',
         ")", "",
         f'def Material "{nom}" (', '    kind = "component"', "    customData = {"]
    for k, v in meta_court.items():
        if isinstance(v, (int, float)):
            L.append(f"        double {k} = {v}")
        else:
            L.append(f'        string {k} = "{v}"')
    L += ["    }", ")", "{",
          f"    token outputs:surface.connect = <{racine}/Surface.outputs:surface>", "",
          '    def Shader "Surface"', "    {", '        uniform token info:id = "UsdPreviewSurface"',
          "        int inputs:useSpecularWorkflow = 0"]
    L.append(f"        color3f inputs:diffuseColor.connect = <{racine}/Albedo.outputs:rgb>")
    if "rugosite" in tex:
        L.append(f"        float inputs:roughness.connect = <{racine}/Rugosite.outputs:r>")
    else:
        L.append("        float inputs:roughness = 0.9")
    if "metal" in tex:
        L.append(f"        float inputs:metallic.connect = <{racine}/Metal.outputs:r>")
    else:
        L.append("        float inputs:metallic = 0")
    if "normale" in tex:
        L.append(f"        normal3f inputs:normal.connect = <{racine}/Normale.outputs:rgb>")
    if "ao" in tex:
        L.append(f"        float inputs:occlusion.connect = <{racine}/AO.outputs:r>")
    if "opacite" in tex:
        L.append(f"        float inputs:opacity.connect = <{racine}/Opacite.outputs:r>")
        L.append("        float inputs:opacityThreshold = 0.5")
    L += ["        token outputs:surface", "    }", "",
          '    def Shader "LecteurUV"', "    {", '        uniform token info:id = "UsdPrimvarReader_float2"',
          f'        string inputs:varname = "{primvar}"', "        float2 outputs:result", "    }", "",
          '    def Shader "EchelleUV"', "    {", '        uniform token info:id = "UsdTransform2d"',
          f"        float2 inputs:in.connect = <{racine}/LecteurUV.outputs:result>",
          f"        float2 inputs:scale = ({s:.6f}, {s:.6f})", "        float2 outputs:result", "    }"]

    def tx(nom_shader, fichier, espace, sortie, extra=()):
        b = ["", f'    def Shader "{nom_shader}"', "    {", '        uniform token info:id = "UsdUVTexture"',
             f"        asset inputs:file = @./textures/{fichier}@",
             f'        token inputs:sourceColorSpace = "{espace}"',
             f'        token inputs:wrapS = "{"clamp" if decalque else "repeat"}"',
             f'        token inputs:wrapT = "{"clamp" if decalque else "repeat"}"',
             f"        float2 inputs:st.connect = <{racine}/EchelleUV.outputs:result>"]
        b += [f"        {e}" for e in extra]
        b += [f"        {sortie}", "    }"]
        return b

    L += tx("Albedo", tex["albedo"], "sRGB", "float3 outputs:rgb")
    if "rugosite" in tex:
        L += tx("Rugosite", tex["rugosite"], "raw", "float outputs:r")
    if "metal" in tex:
        L += tx("Metal", tex["metal"], "raw", "float outputs:r")
    if "normale" in tex:
        L += tx("Normale", tex["normale"], "raw", "float3 outputs:rgb",
                ("float4 inputs:scale = (2, 2, 2, 1)", "float4 inputs:bias = (-1, -1, -1, 0)"))
    if "ao" in tex:
        L += tx("AO", tex["ao"], "raw", "float outputs:r")
    if "opacite" in tex:
        L += tx("Opacite", tex["opacite"], "raw", "float outputs:r")
    L += ["}", ""]
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def valider_usd(chemin):
    try:
        from pxr import Usd, UsdShade
    except Exception:  # noqa: BLE001
        return "pxr absent : validation USD sautée"
    st = Usd.Stage.Open(chemin)
    p = st.GetDefaultPrim()
    mat = UsdShade.Material(p)
    surf = mat.ComputeSurfaceSource()[0]
    if not surf or surf.GetIdAttr().Get() != "UsdPreviewSurface":
        raise RuntimeError(f"{chemin} : sortie surface invalide")
    base = os.path.dirname(chemin)
    for prim in st.Traverse():
        if prim.GetTypeName() == "Shader":
            a = prim.GetAttribute("inputs:file")
            if a and a.Get() is not None:
                f = os.path.join(base, a.Get().path)
                if not os.path.exists(f):
                    raise RuntimeError(f"texture manquante : {f}")
    return "USD valide (pxr)"


# --------------------------------------------------------------------------------------------
# traitement d'un matériau
# --------------------------------------------------------------------------------------------
def traiter(m, args, sortie):
    nom = m["nom"]
    res = args.resolution
    n_alb = RES_PX[res]
    n_autres = n_alb if (args.complet or res == "1K") else min(n_alb, 1024)
    if res == "4K":
        n_autres = n_alb
    dossier = os.path.join(sortie, nom)
    if os.path.exists(os.path.join(dossier, "meta.json")) and not args.forcer:
        mt = json.load(open(os.path.join(dossier, "meta.json"), encoding="utf-8"))
        if mt.get("resolution") == res and mt.get("version_manifeste") == args.version_manifeste:
            log(f"{nom} : déjà présent ({res}) — --forcer pour refaire")
            return mt
    log(f"{nom} : {m['source']} {m['id']} ({res})")
    cartes = obtenir_cartes(m, res, args.cache, args.hauteur)
    os.makedirs(os.path.join(dossier, "textures"), exist_ok=True)
    tex, fichiers = {}, []

    # albédo + correction Lab
    alb = lire_image(cartes["albedo"]).convert("RGB")
    if alb.size[0] != alb.size[1] or alb.size[0] < n_alb // 2:
        log(f"  attention : albédo {alb.size} pour {res}")
    alb = redim(alb, n_alb)
    a01 = np.asarray(alb, np.float64) / 255.0
    lab_avant = lab_moyen(a01)
    corr = m.get("correction_teinte")
    corr_app = None
    if corr and args.correction != "aucune":
        c = dict(corr)
        if args.correction == "cible":
            cib = corr["lab_cible"]
            c["decalage_L"] = cib[0] - c["gain_L"] * lab_avant[0]
            c["decalage_a"] = cib[1] - c["gain_ab"] * lab_avant[1]
            c["decalage_b"] = cib[2] - c["gain_ab"] * lab_avant[2]
        a01 = corriger_lab(a01, c)
        corr_app = {k: round(float(c[k]), 3) for k in ("gain_L", "decalage_L", "gain_ab", "decalage_a", "decalage_b")}
    lab_apres = lab_moyen(a01)
    f = f"{nom}_albedo.jpg"
    Image.fromarray((a01 * 255 + 0.5).astype(np.uint8)).save(os.path.join(dossier, "textures", f), quality=90, subsampling=0)
    tex["albedo"] = f

    # rugosité (+ réglage du manifeste)
    if "rugosite" in cartes:
        r = redim(gris(lire_image(cartes["rugosite"])), n_autres)
        rg = m.get("rugosite") or {}
        g, o = float(rg.get("gain", 1.0)), float(rg.get("decalage", 0.0))
        if g != 1.0 or o != 0.0:
            r = Image.fromarray(np.clip((np.asarray(r, np.float64) / 255.0 * g + o) * 255 + 0.5, 0, 255).astype(np.uint8))
        f = f"{nom}_rugosite.jpg"
        r.save(os.path.join(dossier, "textures", f), quality=90)
        tex["rugosite"] = f
    if "ao" in cartes:
        f = f"{nom}_ao.jpg"
        redim(gris(lire_image(cartes["ao"])), n_autres).save(os.path.join(dossier, "textures", f), quality=90)
        tex["ao"] = f
    if "normale" in cartes:
        f = f"{nom}_normale.png"
        redim(lire_image(cartes["normale"]).convert("RGB"), n_autres, normale=True).save(os.path.join(dossier, "textures", f), optimize=True)
        tex["normale"] = f
    if "opacite" in cartes:
        f = f"{nom}_opacite.png"
        redim(gris(lire_image(cartes["opacite"])), n_autres).save(os.path.join(dossier, "textures", f), optimize=True)
        tex["opacite"] = f
    if "metal" in cartes:
        f = f"{nom}_metal.jpg"
        redim(gris(lire_image(cartes["metal"])), n_autres).save(os.path.join(dossier, "textures", f), quality=90)
        tex["metal"] = f
    if "hauteur" in cartes and args.hauteur:
        h = lire_image(cartes["hauteur"])
        a = np.asarray(h, np.float64)
        if a.ndim == 3:
            a = a[..., 0]
        a = a / (65535.0 if a.max() > 255 else 255.0)
        h16 = Image.fromarray((np.clip(a, 0, 1) * 65535 + 0.5).astype(np.uint16))
        h16 = h16.resize((n_autres, n_autres), Image.LANCZOS) if h16.size[0] != n_autres else h16
        f = f"{nom}_hauteur.png"
        h16.save(os.path.join(dossier, "textures", f))
        tex["hauteur"] = f

    # contrôle des dimensions
    for role, fn in tex.items():
        w, hh = Image.open(os.path.join(dossier, "textures", fn)).size
        attendu = n_alb if role == "albedo" else n_autres
        if (w, hh) != (attendu, attendu):
            raise RuntimeError(f"{fn} : {w}x{hh} au lieu de {attendu}x{attendu}")
        fichiers.append(dict(role=role, fichier=f"textures/{fn}", px=w, octets=os.path.getsize(os.path.join(dossier, "textures", fn)),
                             sha256=sha256(os.path.join(dossier, "textures", fn))))

    decalque = m.get("type") == "decalque"
    primvar = m.get("uv", {}).get("primvar", "st" if decalque else "st1")
    usda = os.path.join(dossier, f"{nom}.usda")
    ecrire_usda(usda, nom, {k: v for k, v in tex.items() if k != "hauteur"}, m["tile_m"], primvar,
                dict(source=m["source"], source_id=m["id"], licence="CC0-1.0", tile_m=float(m["tile_m"]), resolution=res), decalque)
    valid = valider_usd(usda)

    meta = dict(
        nom=nom, categorie="materiaux", type=m.get("type"), libelle=m.get("libelle"),
        source=m["source"], source_id=m["id"], page=m.get("page"), auteur=m.get("auteur"),
        licence=m["licence"], resolution=res, resolution_px=dict(albedo=n_alb, autres=n_autres),
        tile_m=m["tile_m"], tile_m_source=m.get("tile_m_source"), uv=dict(primvar=primvar, echelle=1.0 / m["tile_m"] if primvar == "st1" else 1.0),
        dimensions=dict(tile_m=m["tile_m"]), reference_normative=("NF P98-351 (dalles podotactiles 40 x 40)" if nom == "bev_podotactile" else None),
        normales="OpenGL (+Y vert) ; Unreal : cocher Flip Green Channel",
        correction_teinte=dict(mode=args.correction, appliquee=corr_app, lab_moyen_avant=[round(float(v), 2) for v in lab_avant],
                               lab_moyen_apres=[round(float(v), 2) for v in lab_apres], lab_cible=(corr or {}).get("lab_cible")),
        albedo_moyen_lineaire=[round(float(v), 4) for v in srgb_vers_lin(a01[::4, ::4].reshape(-1, 3)).mean(0)],
        rugosite=m.get("rugosite"), cible=m.get("cible"), usage_scene=m.get("usage_scene"),
        photos_reference=m.get("photos_reference"), qa=m.get("qa"), equivalents_carla=None, lod=None, triangles=0,
        textures=fichiers, usd=os.path.basename(usda), validation_usd=valid,
        version_manifeste=args.version_manifeste, script=f"assets/telecharger_cc0.py {VERSION}",
        date=datetime.datetime.now().isoformat(timespec="seconds"))
    json.dump(meta, open(os.path.join(dossier, "meta.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    tot = sum(x["octets"] for x in fichiers)
    log(f"  ok : {len(fichiers)} textures, {tot / 1e6:.1f} Mo ; Lab {np.round(lab_avant, 1).tolist()} -> {np.round(lab_apres, 1).tolist()} ; {valid}")
    return meta


# --------------------------------------------------------------------------------------------
# peinture : masques d'usure (spécification assets/specs/peinture.json)
# --------------------------------------------------------------------------------------------
def bruit_periodique(n, taille_px, octaves, rng, persistance=0.5):
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    acc = np.zeros((n, n))
    amp = 1.0
    for o in range(octaves):
        f0 = (2 ** o) / taille_px
        filt = np.exp(-0.5 * ((f - f0) / (0.45 * f0)) ** 2)
        w = np.fft.rfft2(rng.standard_normal((n, n)))
        b = np.fft.irfft2(w * filt, s=(n, n))
        acc += amp * b / (b.std() + 1e-12)
        amp *= persistance
    r = acc.ravel().argsort().argsort().astype(np.float64) / (n * n - 1)
    return r.reshape(n, n)


def faiencage(n, cellule_px, largeur_px, rng):
    m = max(2, int(round(n / cellule_px)))
    c = n / m
    I, J = np.meshgrid(np.arange(m), np.arange(m), indexing="ij")
    r = rng.random((m, m, 2))
    gy = (I + r[..., 0]) * c
    gx = (J + r[..., 1]) * c
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ci = (yy // c).astype(int)
    cj = (xx // c).astype(int)
    d1 = np.full((n, n), 1e9, np.float32)
    d2 = np.full((n, n), 1e9, np.float32)
    alea = rng.random((m, m)).astype(np.float32)
    cel = np.zeros((n, n), np.float32)
    for di in (-2, -1, 0, 1, 2):
        for dj in (-2, -1, 0, 1, 2):
            ti = ci + di
            tj = cj + dj
            ii = ti % m
            jj = tj % m
            py = gy[ii, jj] + (ti - ii) / m * n
            px = gx[ii, jj] + (tj - jj) / m * n
            d = np.hypot(yy - py, xx - px)
            d2 = np.where(d < d1, d1, np.minimum(d2, d))
            cel = np.where(d < d1, alea[ii, jj], cel)
            d1 = np.minimum(d1, d)
    return np.clip(1.0 - (d2 - d1) / largeur_px, 0, 1), cel


def generer_masque(spec):
    mq = spec["usure"]["masque"]
    n, tile, graine = int(mq["taille_px"]), float(mq["tile_m"]), int(mq["graine"])
    ca = mq["canaux"]
    rng = np.random.default_rng(graine)
    pxm = n / tile
    R = bruit_periodique(n, ca["R"]["taille_element_m"] * pxm, ca["R"]["octaves"], rng, ca["R"]["persistance"])
    B, G = faiencage(n, ca["B"]["taille_cellule_m"] * pxm, ca["B"]["largeur_fissure_m"] * pxm, rng)
    A = bruit_periodique(n, ca["A"]["taille_element_m"] * pxm, ca["A"]["octaves"], rng, ca["A"]["persistance"])
    return np.stack([R, G, B, A], -1)


def _score(M, nv):
    w = nv["poids_RGA"]
    return M[..., 0] * w[0] + M[..., 1] * w[1] + M[..., 3] * w[2]


def _hors_fissure(M, nv):
    if nv.get("fissure_B") is None:
        return np.ones(M.shape[:2], bool)
    return ~((M[..., 2] > nv["fissure_B"]) & (M[..., 3] > nv["fissure_A"]))


def calculer_seuils(M, spec):
    out = {}
    for u, nv in spec["usure"]["niveaux"].items():
        s = _score(M, nv)
        ok = _hors_fissure(M, nv)
        q = min(1.0, max(0.0, 1 - (1 - nv["trous"]) / ok.mean()))
        out[u] = round(float(np.quantile(s[ok], q)), 5)
    return out


def masque_niveau(M, nv, seuil):
    return (_score(M, nv) > seuil) & _hors_fissure(M, nv)


def faire_peinture(args, sortie):
    spec_p = os.path.join(ICI, "specs", "peinture.json")
    spec = json.load(open(spec_p, encoding="utf-8"))
    nom = "peinture_routiere"
    d = os.path.join(sortie, nom)
    os.makedirs(os.path.join(d, "textures"), exist_ok=True)
    log("peinture : génération du masque d'usure (≈ 30 s en 2048 px)")
    M = np.round(generer_masque(spec) * 255) / 255.0       # quantifié comme le PNG 8 bits lu par Unreal/Houdini
    S = calculer_seuils(M, spec)
    tile = spec["usure"]["masque"]["tile_m"]
    Image.fromarray(np.round(M * 255).astype(np.uint8), "RGBA").save(os.path.join(d, "textures", "masque_usure_peinture.png"), optimize=True)
    stats = {}
    for u, nv in spec["usure"]["niveaux"].items():
        p = masque_niveau(M, nv, S[u])
        sal = np.clip(nv["salete"] * (0.6 + 0.8 * M[..., 3]), 0, 1)
        stats[u] = dict(seuil=S[u], peinture=round(float(p.mean()), 3), couverture_effective=round(float((p * (1 - sal)).mean()), 3),
                        couverture_visee=nv["couverture_effective"])
        Image.fromarray((p * 255).astype(np.uint8), "L").save(os.path.join(d, "textures", f"masque_peinture_u{u}.png"), optimize=True)
    # matériaux UsdPreviewSurface approchés (couleur effective constante + opacité découpée par le masque)
    sol = np.array(spec["etalonnage"]["enrobe_ancien_reference"]["albedo_lineaire"])
    L = ["#usda 1.0", "(", f'    defaultPrim = "{nom}"', "    metersPerUnit = 1", '    upAxis = "Z"',
         '    doc = "Peinture routière : matériaux approchés UsdPreviewSurface (la recette complète est la Material Function Unreal décrite dans assets/specs/peinture.json)."',
         ")", "", f'def Scope "{nom}"', "{"]
    for coul, cdef in spec["couleurs"].items():
        neuf = np.array(cdef["neuf"]["albedo_lineaire"])
        for u, nv in spec["usure"]["niveaux"].items():
            mn = f"peinture_{coul}_u{u}"
            sal = nv["salete"]
            chroma = float((cdef.get("chroma_par_usure") or {}).get(u, 1.0))
            gris = float(neuf @ np.array([0.2126, 0.7152, 0.0722]))
            coul_u = gris + (neuf - gris) * chroma                     # décoloration UV des produits colorés
            eff = coul_u * (1 - sal) + sol * sal
            if u == "F":
                eff = 0.5 * eff + 0.5 * sol * nv["fond_gain"]
            rug = spec["rugosite"]["peinture_par_usure"].get(u) or 0.8
            r = f"/{nom}/{mn}"
            L += [f'    def Material "{mn}"', "    {", f"        token outputs:surface.connect = <{r}/Surface.outputs:surface>",
                  '        def Shader "Surface"', "        {", '            uniform token info:id = "UsdPreviewSurface"',
                  f"            color3f inputs:diffuseColor = ({eff[0]:.4f}, {eff[1]:.4f}, {eff[2]:.4f})",
                  f"            float inputs:roughness = {rug}", "            float inputs:metallic = 0",
                  f"            float inputs:opacity.connect = <{r}/Masque.outputs:r>", "            float inputs:opacityThreshold = 0.5",
                  "            token outputs:surface", "        }",
                  '        def Shader "LecteurUV"', "        {", '            uniform token info:id = "UsdPrimvarReader_float2"',
                  '            string inputs:varname = "st1"', "            float2 outputs:result", "        }",
                  '        def Shader "EchelleUV"', "        {", '            uniform token info:id = "UsdTransform2d"',
                  f"            float2 inputs:in.connect = <{r}/LecteurUV.outputs:result>",
                  f"            float2 inputs:scale = ({1 / tile:.6f}, {1 / tile:.6f})", "            float2 outputs:result", "        }",
                  '        def Shader "Masque"', "        {", '            uniform token info:id = "UsdUVTexture"',
                  f"            asset inputs:file = @./textures/masque_peinture_u{u}.png@", '            token inputs:sourceColorSpace = "raw"',
                  '            token inputs:wrapS = "repeat"', '            token inputs:wrapT = "repeat"',
                  f"            float2 inputs:st.connect = <{r}/EchelleUV.outputs:result>", "            float outputs:r", "        }",
                  "    }"]
    L += ["}", ""]
    usda = os.path.join(d, f"{nom}.usda")
    open(usda, "w", encoding="utf-8").write("\n".join(L))
    try:
        from pxr import Usd
        st = Usd.Stage.Open(usda)
        nmat = sum(1 for p in st.Traverse() if p.GetTypeName() == "Material")
        valid = f"USD valide (pxr), {nmat} matériaux"
    except ImportError:
        valid = "pxr absent : validation USD sautée"
    fichiers = []
    for fn in sorted(os.listdir(os.path.join(d, "textures"))):
        p = os.path.join(d, "textures", fn)
        fichiers.append(dict(fichier=f"textures/{fn}", octets=os.path.getsize(p), sha256=sha256(p)))
    meta = dict(nom=nom, categorie="materiaux", type="peinture", source="maison (procédural, specs/peinture.json)",
                licence="maison (même licence que le dépôt)", tile_m=tile, uv=dict(primvar="st1", echelle=1 / tile),
                seuils_score=S, niveaux=stats, graine=spec["usure"]["masque"]["graine"], textures=fichiers, usd=os.path.basename(usda),
                validation_usd=valid, script=f"assets/telecharger_cc0.py {VERSION}", date=datetime.datetime.now().isoformat(timespec="seconds"))
    json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for u, s in stats.items():
        log(f"  usure {u} : seuil {s['seuil']:.4f}, peinture {s['peinture']:.2f}, couverture effective {s['couverture_effective']:.2f} (visée {s['couverture_visee']})")
    log(f"  {valid} ; {sum(x['octets'] for x in fichiers) / 1e6:.1f} Mo")
    return meta


def seuils_pour(png):
    spec = json.load(open(os.path.join(ICI, "specs", "peinture.json"), encoding="utf-8"))
    M = np.asarray(Image.open(png).convert("RGBA"), np.float64) / 255.0
    S = calculer_seuils(M, spec)
    print(json.dumps(S, indent=1))
    return S


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifeste", default=os.path.join(ICI, "manifeste_cc0.json"))
    ap.add_argument("--resolution", choices=list(RES_PX), default="2K")
    ap.add_argument("--materiaux", nargs="*", help="noms d'assets (défaut : tous)")
    ap.add_argument("--priorite-max", type=int, default=3, help="ne traiter que les priorités <= N")
    ap.add_argument("--sortie", help="défaut : assets/lib/materiaux (1K/2K), data/raw/assets_src/materiaux_4k (4K)")
    ap.add_argument("--cache", default=os.path.join(DEPOT, "data", "raw", "assets_src", "cc0"))
    ap.add_argument("--correction", choices=["cible", "manifeste", "aucune"], default="cible")
    ap.add_argument("--complet", action="store_true", help="toutes les cartes à la résolution demandée (sinon cartes secondaires <= 1K)")
    ap.add_argument("--hauteur", action="store_true", help="ajoute la carte de hauteur (PNG 16 bits)")
    ap.add_argument("--forcer", action="store_true")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--verifier", action="store_true", help="vérifie les URL (HEAD) sans rien télécharger")
    ap.add_argument("--peinture", action="store_true", help="génère le masque d'usure et les matériaux de peinture")
    ap.add_argument("--seuils", metavar="PNG", help="calcule les seuils d'usure pour un masque RGBA donné")
    ap.add_argument("--budget-mo", type=float, default=150.0, help="alerte si la sortie dépasse ce volume")
    args = ap.parse_args()

    if args.seuils:
        seuils_pour(args.seuils)
        return
    man = json.load(open(args.manifeste, encoding="utf-8"))
    args.version_manifeste = man.get("version")
    mats = [m for m in man["materiaux"] if (not args.materiaux or m["nom"] in args.materiaux) and int(m.get("priorite") or 3) <= args.priorite_max]
    if args.materiaux:
        inconnus = set(args.materiaux) - {m["nom"] for m in man["materiaux"]}
        if inconnus:
            sys.exit(f"matériaux inconnus : {sorted(inconnus)}")
    sortie = args.sortie or (os.path.join(DEPOT, "data", "raw", "assets_src", "materiaux_4k") if args.resolution == "4K"
                             else os.path.join(ICI, "lib", "materiaux"))
    if args.resolution == "4K" and os.path.abspath(sortie).startswith(os.path.join(ICI, "lib")):
        log("attention : 4K dans assets/lib dépasse la règle « 2K maximum dans le dépôt »")

    if args.liste:
        for m in mats:
            t = m["telechargements"].get(args.resolution, {})
            print(f"{m['nom']:26s} p{m.get('priorite')}  {m['source']:10s} {m['id']:24s} tile {m['tile_m']:5.2f} m  {t.get('taille_o', 0) / 1e6:6.1f} Mo ({args.resolution})")
        print(f"total téléchargement {args.resolution} : {sum(m['telechargements'].get(args.resolution, {}).get('taille_o', 0) for m in mats) / 1e6:.0f} Mo")
        return
    if args.verifier:
        bad = 0
        for m in mats:
            for r, t in m["telechargements"].items():
                urls = [(t["url"], t.get("taille_o"))] if t["format"] == "zip" else [(f["url"], f.get("taille_o")) for f in t["fichiers"].values()]
                for u, sz in urls:
                    ok, msg = verifier_url(u, sz)
                    bad += not ok
                    print(f"{'OK ' if ok else 'ERR'} {m['nom']:26s} {r} {msg:28s} {u}")
                    time.sleep(0.2)
        print(f"{bad} erreur(s)")
        sys.exit(1 if bad else 0)
    if args.peinture:
        faire_peinture(args, sortie)
        return

    bilan, erreurs = [], []
    for m in mats:
        try:
            bilan.append(traiter(m, args, sortie))
        except Exception as e:  # noqa: BLE001
            erreurs.append((m["nom"], str(e)))
            log(f"ERREUR {m['nom']} : {e}")
    tot = sum(sum(x["octets"] for x in b["textures"]) for b in bilan if b)
    log(f"{len(bilan)} matériau(x) dans {sortie} ; textures {tot / 1e6:.1f} Mo")
    if tot / 1e6 > args.budget_mo:
        log(f"attention : {tot / 1e6:.0f} Mo > budget {args.budget_mo:.0f} Mo (mode --complet ? résolution ?)")
    if erreurs:
        for n, e in erreurs:
            log(f"  échec {n} : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
