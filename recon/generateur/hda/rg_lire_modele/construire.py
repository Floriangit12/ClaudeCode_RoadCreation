"""Construit l'HDA rg::lire_modele::1.0 (lecteur du modèle modele_voie/0.1) ; hython Houdini 22.

    hython recon/generateur/hda/rg_lire_modele/construire.py

Réseau (recon/generateur/hda/README_RG.md § 2) : cinq Python SOP (module lecteur.py embarqué), un par sortie :
    lire_routes -> ROUTES        polylignes de référence (geometrie du modèle) + géométrie régulière, sections
    lire_noeuds -> NOEUDS        points
    lire_zones -> ZONES          polygones (zones, îlots)
    lire_ponctuels -> PONCTUELS  objets (plateaux, dos-d'âne, coussins, arbres…), signaux, marquages
    lire_profils -> PROFILS      un point par profil effectif (bandes, lois de largeur aplaties, limites)
"""
import sys
from pathlib import Path

import hou

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "commun"))
import rg_hda_outils as R  # noqa: E402

NOM = "lire_modele"
SORTIES = (("routes", "lire_routes", "ROUTES", "Routes (lignes de référence)"),
           ("noeuds", "lire_noeuds", "NOEUDS", "Nœuds"),
           ("zones", "lire_zones", "ZONES", "Zones et îlots"),
           ("ponctuels", "lire_ponctuels", "PONCTUELS", "Ponctuels (objets, signaux, marquages)"),
           ("profils", "lire_profils", "PROFILS", "Profils"))


def parametres():
    T = hou
    f = T.StringParmTemplate("fichier", "Modèle (modele_voie.json)", 1, default_value=("",),
                             string_type=T.stringParmType.FileReference, file_type=T.fileType.Any,
                             help="Fichier modele_voie/0.1 : sortie de description_vers_modele.py (description simple) "
                                  "ou de osm_vers_modele.py (inférence OSM). Coordonnées Lambert-93, converties une "
                                  "seule fois : local = L93 − repere.origine_l93, puis Houdini (x, z, −y).")
    return [f]


def construire(dossier=ICI):
    sub = R.sous_reseau("rg_" + NOM)
    sub.setParmTemplateGroup(hou.ParmTemplateGroup(parametres()))
    module = (ICI / "lecteur.py").read_text(encoding="utf-8")
    nuls = []
    for k, (cle, fonction, nul, _) in enumerate(SORTIES):
        py = sub.createNode("python", fonction)
        py.parm("python").set(f"# Lecteur du modèle (module lecteur.py embarqué dans l'HDA) : sortie {k + 1}, {cle}\n"
                              f"hou.pwd().parent().hdaModule().{fonction}(hou.pwd())\n")
        n = sub.createNode("null", nul)
        n.setInput(0, py)
        R.sortie(sub, n, k, f"sortie_{cle}")
        nuls.append(n)
    for n in nuls:
        n.setDisplayFlag(False)
    nuls[0].setDisplayFlag(True)
    R.ranger(sub)
    aide = ("Lecteur unique du générateur : modèle modele_voie/0.1 (JSON, Lambert-93) converti en géométrie Houdini "
            "(Y haut, (x, z, −y) locaux) avec attributs ; aucune opération géométrique (échantillonnage et profils : "
            "rg::graphe, rg::profils).")
    details = ("== Sorties ==\n\n"
               "1. Routes : polyligne ligne_reference.geometrie ; primitives id, categorie, agglomeration, vitesse_kmh, "
               "sens_unique, noeud_debut, noeud_fin, longueur_m ; géométrie régulière geo_type (0 droite, 1 arc, "
               "2 clothoïde), geo_s0, geo_longueur, geo_x0, geo_y0 (locaux), geo_cap (rad), geo_k0, geo_k1 ; sections "
               "sec_s0, sec_s1, sec_profil, sec_transition ; props (JSON).\n"
               "2. Nœuds : points id, type, carrefour, routes.\n"
               "3. Zones et îlots : polygones id, famille_modele, type, materiau_id, anneau (groupe trou).\n"
               "4. Ponctuels : objets, signaux, marquages (id, famille_modele, type, route, bande, s, t, longueur_m, "
               "largeur_m, hauteur_m, regles, a_position, props).\n"
               "5. Profils : un point par profil effectif (profil, ref_limite, ref_decalage, bandes et lois de "
               "largeur aplaties larg_type / larg_s0 / larg_v0 / larg_n / larg_s / larg_v, niveaux, limites lim_*, "
               "evts_s).\n\nDétail rg_modele sur chaque sortie : fichier, sha256, origine, comptes, familles non lues.\n"
               "Erreurs (jamais de silence) : primitive parampoly3, interpolation cubique_lisse, transition d'entrée "
               "autre qu'instantanée, surcharge non reconnue, profil inconnu.\n\n"
               "Conventions : recon/generateur/hda/README_RG.md.")
    return R.creer_hda(sub, NOM, "RG Lire le modèle de voies", parametres(), dossier, entrees=(0, 0),
                       sorties=len(SORTIES), aide=aide, details_aide=details, module_python=module, icone="SOP_file",
                       etiquettes_sorties=tuple(s[3] for s in SORTIES))


if __name__ == "__main__":
    print(construire())
