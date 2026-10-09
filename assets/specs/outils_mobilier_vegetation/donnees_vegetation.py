"""Végétation de l'emprise (300 m) : essences de l'inventaire de la Métropole présentes en 2026,
jeunes sujets plantés en 2025 (plan projet), arbres privés vus sur les photos, génériques, haies
et massifs. Feuillage décrit pour l'état modélisé (mi-octobre 2026, Grenoble, ≈ 215 m) et par
saison. Couleurs sRGB indicatives (feuillage au soleil, à recaler sur les photos dans Unreal).

Sources des positions et hauteurs : recon/out/paquet_jardin/objets/arbres.geojson (atelier objets :
inventaire Métropole, levé GAM, LiDAR HD 2021, plan projet 2025). Le script de substitution met
chaque arbre à l'échelle de sa hauteur mesurée : la hauteur de l'asset compte surtout pour les
proportions (fût / houppier).
"""
from commun import tuile
from donnees_mobilier import T_E540, T_9FC8, T_5C0D, T_D888, T_2AB4, T_BC579, T_2374, T_DED0, T_FFC2, T_E5D7, T_119D, T_F8D9, T_31D1, T_B401, T_0508, T_7A18

T_9834 = "2025-05-18_9834f494-dbcb-4c89-b8f7-0c3a8cb42433"
T_5C0D_C4 = "2024-08-24_5c0d1d39-bfe4-4e40-a6ad-4722501df97a"

SOURCES_PROD = {
    "speedtree": "SpeedTree (Modeler 10 / bibliothèque du compte de l'utilisateur) : modèles par essence, saisons (été/automne/hiver) et LOD ; export FBX ou USD → Houdini (mise en Z-up, pivot au pied) → assets/lib/vegetation/<nom>/<nom>.usda",
    "fab": "Fab / Quixel Megascans (compte de l'utilisateur) : arbres et arbustes photogrammétriques (feuillage Nanite UE 5.x) — peu d'essences urbaines européennes : privilégier pour haies, arbustes, souches, herbes",
    "labs": "SideFX Labs (Houdini 22) : Labs Tree Trunk Generator + Tree Branch Generator + Tree Leaf Generator (+ Tree Simple Leaf) paramétrés avec le gabarit ci-dessous ; atlas de feuilles CC0 (photos de feuilles détourées)",
    "carla": "contenu CARLA /Game/Carla/Static/Vegetation (arbres, buissons) : silhouettes génériques non européennes → doublure uniquement (voir carla_correspondances.json)",
}


def feuillage(persistance, ete, automne, etat_oct, hiver, chute=None, debourrement=None):
    d = {"persistance": persistance, "ete_srgb": ete, "automne_srgb": automne, "etat_mi_octobre_2026": etat_oct, "hiver": hiver}
    if chute:
        d["chute"] = chute
    if debourrement:
        d["debourrement"] = debourrement
    return d


# correspondance essence (atelier objets) → asset ; 'classe' = classe de hauteur de l'inventaire
def asset_pour(ess, classe, statut, code):
    e = (ess or "").lower()
    if "planté 2025" in (statut or ""):
        c = (code or "").strip()
        return {"Alc": "arbre_alnus_cordata_jeune", "As": "arbre_alnus_spaethii_jeune", "Ce": "arbre_cercis_siliquastrum_jeune",
                "Cs": "arbre_cercis_siliquastrum_jeune", "Ul": "arbre_ulmus_hybride_jeune", "Oc": "arbre_quercus_cerris_jeune",
                "Qc": "arbre_quercus_cerris_jeune", "Gt": "arbre_gleditsia_triacanthos_jeune", "Ca": "arbre_celtis_australis_jeune",
                "Ac": "arbre_acer_campestre_jeune", "Aca": "arbre_acer_campestre_jeune"}.get(c, "arbre_jeune_tuteure_generique")
    if "absent" in (statut or "") or e == "souche":
        return None
    if e.startswith("populus alba"):                       # V2 : fiche « Abattu » mais houppier présent 2021-2025
        return "arbre_populus_alba_grand"
    if e.startswith("feuillage pourpre"):                  # V2 : arbre pourpre de l'angle Revirée (photos 2024-08, 2025-05)
        return "arbre_prunus_cerasifera_pissardii_moyen"
    cl = {"[0;5m[": "jeune", "[5;10m[": "petit", "[10;20m[": "moyen", "[20;30m[": "grand"}.get(classe or "")
    if e.startswith("populus nigra italica"):
        return "arbre_populus_nigra_italica_grand"
    if e.startswith("populus nigra"):
        return "arbre_populus_nigra_grand" if cl == "grand" else "arbre_populus_nigra_moyen"
    if e.startswith("populus sp"):
        return "arbre_populus_sp_tetard_moyen"
    if e.startswith("cedrus"):
        return "arbre_cedrus_atlantica_grand"
    if e.startswith("tilia"):
        return "arbre_tilia_cordata_moyen"
    if e.startswith("quercus robur"):
        return {"petit": "arbre_quercus_robur_petit", "grand": "arbre_quercus_robur_grand"}.get(cl, "arbre_quercus_robur_moyen")
    if e.startswith("acer campestre"):
        return "arbre_acer_campestre_jeune"
    if e.startswith("fraxinus"):
        return "arbre_fraxinus_excelsior_moyen"
    if e.startswith("carpinus"):
        return "arbre_carpinus_betulus_moyen"
    if e.startswith("betula"):
        return "arbre_betula_pendula_moyen"
    if e.startswith("corylus"):
        return "arbre_corylus_colurna_petit"
    if e.startswith("magnolia"):
        return "arbre_magnolia_grandiflora_jeune"
    if e.startswith("crataegus"):
        return "arbre_crataegus_laevigata_jeune"
    if e.startswith("sorbus"):
        return "arbre_sorbus_sp_jeune"
    if e.startswith("salix babylonica"):
        return "arbre_salix_babylonica_tetard_petit"
    if e == "conifere":
        return "arbre_conifere_generique_moyen"
    if e == "feuillu":
        return "arbre_feuillu_generique_moyen"
    return None


LABS = "labs"
SPT = "speedtree"

ESSENCES = [
    {"asset": "arbre_populus_nigra_moyen", "nom_latin": "Populus nigra", "nom_francais": "peuplier noir", "nom_anglais": "black poplar",
     "source": "inventaire Métropole (alignement « Avenue de Verdun/Schneider », branche NE côté SE)", "priorite": 1, "confiance": "haute",
     "port": "semi-libre : grand fût droit, houppier ovoïde irrégulier, charpentières ascendantes, gourmands sur le tronc",
     "tronc": "écorce gris sombre profondément crevassée, broussins ; Ø 0,46-0,62 m (circonférence 145-195 cm)",
     "feuillage": feuillage("caduc", "#4E7A2C", "#D8B23C", "vert-jaune, 30-50 % jauni, chute commencée (feuilles au sol)", "silhouette nue, fines branches dressées",
                            chute="mi-octobre à mi-novembre", debourrement="début avril"),
     "gabarit": {"hauteur": 23.5, "fut_nu": 6.0, "couronne_diametre": 10.8, "forme_couronne": "ovoïde haute irrégulière", "angle_charpentieres_deg": 35,
                 "feuille_cm": "6-9 (deltoïde)", "densite": "moyenne (ciel visible)"},
     "note_hauteur": "inventaire [10;20 m[ mais LiDAR 2021 22,9-27,4 m (médiane 23,4) : construire l'asset à ≈ 23 m",
     "production": {"principale": SPT, "alternatives": [LABS, "fab"]},
     "photos_reference": [tuile(T_E540, "r01_c01"), tuile(T_119D, "r01_c00")]},
    {"asset": "arbre_populus_nigra_grand", "nom_latin": "Populus nigra", "nom_francais": "peuplier noir", "nom_anglais": "black poplar",
     "source": "inventaire Métropole (même alignement)", "priorite": 1, "confiance": "haute",
     "port": "libre : très grand houppier étalé", "tronc": "Ø ≈ 0,46 m (145 cm)",
     "feuillage": feuillage("caduc", "#4E7A2C", "#D8B23C", "comme arbre_populus_nigra_moyen", "nu"),
     "gabarit": {"hauteur": 26.0, "fut_nu": 7.0, "couronne_diametre": 13.0, "forme_couronne": "ovoïde large", "angle_charpentieres_deg": 40},
     "production": {"principale": SPT, "alternatives": [LABS]},
     "photos_reference": [tuile(T_E540, "r01_c01")]},
    {"asset": "arbre_populus_sp_tetard_moyen", "nom_latin": "Populus sp. (têtard)", "nom_francais": "peuplier conduit en têtard", "nom_anglais": "pollarded poplar",
     "source": "inventaire Métropole (alignement NE côté NO, port « Têtard »)", "priorite": 1, "confiance": "haute (port) / moyenne (essence)",
     "port": "têtard : tronc court et épais, têtes renflées (« têtes de chat ») portant des rejets droits de 1-3 ans ; LiDAR 5,9-25,9 m (grands sujets non recépés)",
     "tronc": "Ø 0,38-0,89 m (118-280 cm), écorce crevassée, têtes noueuses",
     "feuillage": feuillage("caduc", "#557F33", "#D2B046", "rejets feuillus vert-jaune", "têtes nues hérissées de rejets (silhouette caractéristique)"),
     "gabarit": {"hauteur": 18.0, "hauteur_tetes": "3-8 m (selon recépage)", "couronne_diametre": 9.6, "forme_couronne": "têtes + gerbes de rejets verticaux"},
     "note_hauteur": "deux silhouettes à prévoir : têtard récemment recépé (6-8 m) et têtard non recépé (≈ 23 m)",
     "production": {"principale": LABS, "alternatives": [SPT], "note": "le têtard n'existe pas en bibliothèque : tronc + têtes modélisés, rejets générés (Labs Branch Generator)"},
     "photos_reference": [tuile(T_9FC8, "r01_c03")]},
    {"asset": "arbre_populus_nigra_italica_grand", "nom_latin": "Populus nigra 'Italica'", "nom_francais": "peuplier d'Italie", "nom_anglais": "Lombardy poplar",
     "source": "inventaire Métropole (parc NO, port architecturé, planté en 1960)", "priorite": 3, "confiance": "faible (état 2026 : probablement recépé ou abattu)",
     "port": "fastigié (colonne étroite), branches dressées dès la base", "tronc": "Ø ≈ 0,67 m (210 cm)",
     "feuillage": feuillage("caduc", "#4F7B2F", "#E0BE45", "vert-jaune", "colonne nue de rameaux dressés"),
     "gabarit": {"hauteur": 24.0, "fut_nu": 1.5, "couronne_diametre": 4.5, "forme_couronne": "colonne fusiforme"},
     "note_hauteur": ("V2 : LiDAR HD 2021 3,0 m ET MNH IGN 4,1 m concordants (couronne 4,8 m) : le sujet de 1960 a très probablement été recépé "
                      "ou abattu (cépée de rejets) — la classe [20;30 m[ de l'inventaire est périmée. Construire l'asset à 24 m (utile ailleurs à Meylan), "
                      "mais à l'emplacement arbre_363 poser une cépée de 3-4 m (massif_arbustif) ou souche_arbre ; aucune photo à moins de 90 m pour trancher"),
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_cedrus_atlantica_grand", "nom_latin": "Cedrus atlantica (dont 'Glauca')", "nom_francais": "cèdre de l'Atlas", "nom_anglais": "Atlas cedar",
     "source": "inventaire Métropole (2 : grand cèdre de l'angle Revirée, « Cedrus » 10-20 m mais LiDAR 25,7 m ; cèdre glauque NE 20,9 m)", "priorite": 1, "confiance": "haute",
     "port": "libre : tronc puissant, étages de branches horizontales en plateaux, flèche inclinée ; repère visuel majeur, ombre portée sur la Revirée",
     "tronc": "Ø 0,38-0,53 m (120-165 cm), écorce gris foncé écailleuse",
     "feuillage": feuillage("persistant", "#5A7E78", "#5A7E78", "inchangé (aiguilles bleu-vert glauque), cônes dressés", "inchangé"),
     "gabarit": {"hauteur": 24.0, "fut_nu": 3.0, "couronne_diametre": 12.0, "forme_couronne": "conique large à plateaux étagés", "angle_charpentieres_deg": 80},
     "note_hauteur": "LiDAR 20,9 et 25,7 m ; couronne LiDAR 6,4-8,8 (sous-estimée : la photo montre ≈ 12-15 m d'envergure)",
     "production": {"principale": SPT, "alternatives": [LABS, "fab"]},
     "photos_reference": [tuile(T_5C0D, "r01_c03"), tuile("2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d", "r01_c03")]},
    {"asset": "arbre_tilia_cordata_moyen", "nom_latin": "Tilia cordata", "nom_francais": "tilleul à petites feuilles", "nom_anglais": "small-leaved lime / linden",
     "source": "inventaire Métropole (groupement de 6, parc NO de la Revirée)", "priorite": 1, "confiance": "moyenne",
     "port": "libre : houppier ovoïde dense, branches basses arquées",
     "tronc": "Ø 0,30-0,59 m (95-184 cm), écorce gris lisse puis finement fissurée",
     "feuillage": feuillage("caduc", "#3F6B2B", "#C9A43B", "jaunissement 30-60 %, chute partielle (souvent précoce après un été sec)", "ramure dense, rameaux rougeâtres", chute="octobre"),
     "gabarit": {"hauteur": 14.0, "fut_nu": 2.5, "couronne_diametre": 8.0, "forme_couronne": "ovoïde dense", "feuille_cm": "4-7 (cordée)"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": [tuile(T_5C0D, "r01_c04")]},
    {"asset": "arbre_quercus_robur_moyen", "nom_latin": "Quercus robur", "nom_francais": "chêne pédonculé", "nom_anglais": "English oak",
     "source": "inventaire Métropole (groupements NO et sud)", "priorite": 1, "confiance": "moyenne",
     "port": "libre / semi-libre : charpentières tortueuses, houppier large irrégulier",
     "tronc": "Ø 0,35-0,53 m (110-165 cm), écorce gris-brun crevassée",
     "feuillage": feuillage("caduc (marcescent jeune)", "#3E6A2A", "#9A6B2E", "encore vert à 80 %, brunissement tardif (fin octobre-novembre)", "branches tortueuses, feuilles sèches persistantes sur les jeunes"),
     "gabarit": {"hauteur": 14.0, "fut_nu": 3.0, "couronne_diametre": 10.0, "forme_couronne": "étalée irrégulière", "feuille_cm": "7-12 (lobée)"},
     "production": {"principale": SPT, "alternatives": [LABS, "fab"]}, "photos_reference": []},
    {"asset": "arbre_quercus_robur_petit", "nom_latin": "Quercus robur", "nom_francais": "chêne pédonculé", "nom_anglais": "English oak",
     "source": "inventaire Métropole (classe 5-10 m ; dont 1 fiche d'état inconnu, doublon probable)", "priorite": 2, "confiance": "moyenne",
     "port": "semi-libre", "tronc": "Ø 0,21-0,35 m",
     "feuillage": feuillage("caduc (marcescent)", "#3E6A2A", "#9A6B2E", "vert", "feuilles sèches persistantes"),
     "gabarit": {"hauteur": 8.0, "fut_nu": 2.0, "couronne_diametre": 5.0, "forme_couronne": "ovoïde irrégulière"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_quercus_robur_grand", "nom_latin": "Quercus robur", "nom_francais": "chêne pédonculé", "nom_anglais": "English oak",
     "source": "inventaire Métropole (1, parc NO)", "priorite": 2, "confiance": "moyenne", "port": "libre", "tronc": "Ø ≈ 0,41 m (129 cm)",
     "feuillage": feuillage("caduc", "#3E6A2A", "#9A6B2E", "vert", "nu"),
     "gabarit": {"hauteur": 20.0, "fut_nu": 4.0, "couronne_diametre": 13.0, "forme_couronne": "large"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_acer_campestre_jeune", "nom_latin": "Acer campestre", "nom_francais": "érable champêtre", "nom_anglais": "field maple",
     "source": "inventaire Métropole (alignement « Avenue de Verdun nord », 7 dont 1 têtard, plantés en 1975 sous la haie séparative) + plan projet 2025 (« Ac » ×2, « Aca » conservé)", "priorite": 1, "confiance": "haute",
     "port": "semi-libre : petit arbre à cime arrondie, souvent pris dans la haie",
     "tronc": "Ø 0,11-0,19 m (35-60 cm), écorce liégeuse brun clair",
     "feuillage": feuillage("caduc", "#4A7A30", "#D8B23A", "vert-jaune (jaune d'or fin octobre)", "rameaux liégeux"),
     "gabarit": {"hauteur": 5.5, "fut_nu": 1.5, "couronne_diametre": 5.0, "forme_couronne": "arrondie", "feuille_cm": "5-8 (3-5 lobes)"},
     "note_hauteur": "inventaire [0;5 m[, LiDAR 4,1-7,5 m (médiane 5,2)",
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_fraxinus_excelsior_moyen", "nom_latin": "Fraxinus excelsior", "nom_francais": "frêne commun", "nom_anglais": "European ash",
     "source": "inventaire Métropole (angle NE éloigné)", "priorite": 2, "confiance": "moyenne",
     "port": "libre : houppier ample et léger, feuilles composées", "tronc": "Ø ≈ 0,27 m (83-85 cm), écorce gris clair",
     "feuillage": feuillage("caduc", "#4C7A33", "#B8B04A", "chute des folioles encore vertes ou jaune pâle, houppier clairsemé (chalarose possible)", "bourgeons noirs, ramure claire"),
     "gabarit": {"hauteur": 16.5, "fut_nu": 4.0, "couronne_diametre": 8.0, "forme_couronne": "ovoïde lâche", "feuille_cm": "20-30 (composée, 9-13 folioles)"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_carpinus_betulus_moyen", "nom_latin": "Carpinus betulus (+ 1 'Pyramidalis')", "nom_francais": "charme commun", "nom_anglais": "European hornbeam",
     "source": "inventaire Métropole (4 libres NE + 1 fastigié 'Pyramidalis' au NO, classé 0-5 m mais LiDAR 13,4 m)", "priorite": 2, "confiance": "moyenne",
     "port": "libre : houppier ovoïde dense ; variante 'Pyramidalis' en ogive (à traiter en variante de cet asset)", "tronc": "Ø 0,20-0,39 m, écorce grise lisse cannelée",
     "feuillage": feuillage("caduc (marcescent en haie)", "#4C7A30", "#D3B04A", "vert-jaune", "ramure fine, feuilles sèches persistantes sur les sujets taillés"),
     "gabarit": {"hauteur": 15.5, "fut_nu": 2.5, "couronne_diametre": 7.0, "forme_couronne": "ovoïde (variante ogivale)"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_betula_pendula_moyen", "nom_latin": "Betula pendula", "nom_francais": "bouleau verruqueux", "nom_anglais": "silver birch",
     "source": "inventaire Métropole (parc NO, 2 présents, 2 abattus)", "priorite": 2, "confiance": "moyenne",
     "port": "semi-libre : houppier léger, rameaux pleureurs", "tronc": "Ø 0,21-0,25 m, écorce blanche à losanges noirs",
     "feuillage": feuillage("caduc", "#6A8E3A", "#E1C04A", "jaune 50 %, chute en cours", "écorce blanche très visible, rameaux retombants"),
     "gabarit": {"hauteur": 13.3, "fut_nu": 2.5, "couronne_diametre": 6.5, "forme_couronne": "ovoïde légère, pleureuse"},
     "production": {"principale": SPT, "alternatives": [LABS, "fab"]}, "photos_reference": []},
    {"asset": "arbre_corylus_colurna_petit", "nom_latin": "Corylus colurna", "nom_francais": "noisetier de Byzance", "nom_anglais": "Turkish hazel",
     "source": "inventaire Métropole (alignement ouest)", "priorite": 3, "confiance": "moyenne",
     "port": "libre : pyramidal régulier, axe droit", "tronc": "Ø 0,14-0,27 m, écorce liégeuse claire",
     "feuillage": feuillage("caduc", "#3F6A2C", "#CDAF45", "vert-jaune", "conique régulier"),
     "gabarit": {"hauteur": 10.0, "fut_nu": 1.8, "couronne_diametre": 6.0, "forme_couronne": "conique"},
     "note_hauteur": "inventaire [5;10 m[, LiDAR 9,2-15,7",
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_magnolia_grandiflora_jeune", "nom_latin": "Magnolia grandiflora", "nom_francais": "magnolia à grandes fleurs", "nom_anglais": "southern magnolia",
     "source": "inventaire Métropole (2, allée de L'Horloge)", "priorite": 3, "confiance": "moyenne",
     "port": "libre : cime ovoïde dense", "tronc": "Ø ≈ 0,11 m (35 cm)",
     "feuillage": feuillage("persistant", "#2F5525", "#2F5525", "inchangé (grandes feuilles vernissées, revers roux)", "inchangé"),
     "gabarit": {"hauteur": 5.0, "fut_nu": 1.0, "couronne_diametre": 3.5, "forme_couronne": "ovoïde dense", "feuille_cm": "15-20"},
     "note_hauteur": ("inventaire [0;5 m[ ; LiDAR 7,9-9,0 et MNH IGN 7,7-8,1 → V2 : la photo 2026-07-28 05089869 r01_c04 (à 7,5 m) montre à cet endroit "
                      "un grand feuillu caduc à gros tronc dont le houppier couvre l'allée : la hauteur mesurée est la sienne → garder 5 m pour les magnolias "
                      "(petits sujets de 35 cm de circonférence, non distingués sur la photo)"),
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": [tuile(T_0508, "r01_c04")]},
    {"asset": "arbre_crataegus_laevigata_jeune", "nom_latin": "Crataegus laevigata", "nom_francais": "aubépine épineuse", "nom_anglais": "Midland hawthorn",
     "source": "inventaire Métropole (1)", "priorite": 3, "confiance": "moyenne",
     "port": "libre : petit arbre à cime arrondie, rameaux épineux", "tronc": "Ø ≈ 0,16 m",
     "feuillage": feuillage("caduc", "#4C7A30", "#C27A33", "jaune-orangé, fruits rouges (cenelles)", "rameaux épineux denses"),
     "gabarit": {"hauteur": 5.0, "fut_nu": 1.2, "couronne_diametre": 4.0, "forme_couronne": "arrondie"},
     "note_hauteur": "V2 : inventaire [0;5 m[ (planté 1990, circonférence 50 cm) ; LiDAR 11,9 / MNH IGN 10,9 m invraisemblables pour une aubépine (≤ 8-10 m) → couronne voisine ; hauteur retenue 6 m",
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_sorbus_sp_jeune", "nom_latin": "Sorbus sp.", "nom_francais": "sorbier", "nom_anglais": "rowan / whitebeam",
     "source": "inventaire Métropole (1)", "priorite": 3, "confiance": "moyenne",
     "port": "libre : petite cime ovoïde", "tronc": "Ø ≈ 0,08 m",
     "feuillage": feuillage("caduc", "#4E7C34", "#C8562E", "rouge-orangé, fruits orange", "nu"),
     "gabarit": {"hauteur": 4.9, "fut_nu": 1.5, "couronne_diametre": 3.0, "forme_couronne": "ovoïde"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": []},
    {"asset": "arbre_salix_babylonica_tetard_petit", "nom_latin": "Salix babylonica (têtard)", "nom_francais": "saule pleureur conduit en têtard", "nom_anglais": "pollarded weeping willow",
     "source": "inventaire Métropole (1, NE éloigné)", "priorite": 3, "confiance": "moyenne",
     "port": "têtard : tronc court massif (Ø ≈ 0,70 m, 220 cm), rejets souples retombants", "tronc": "écorce crevassée",
     "feuillage": feuillage("caduc tardif", "#7FA046", "#D5C460", "vert clair", "rejets jaunâtres retombants"),
     "gabarit": {"hauteur": 8.0, "hauteur_tetes": 2.5, "couronne_diametre": 6.0, "forme_couronne": "boule de rejets retombants"},
     "note_hauteur": "inventaire [5;10 m[ ; LiDAR 25,5 m (arbre voisin) → garder 8 m",
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": []},
    # ---------------------------------------------------------------- privés (photos + GAM)
    {"asset": "arbre_cupressus_sempervirens_grand", "nom_latin": "Cupressus sempervirens", "nom_francais": "cyprès d'Italie", "nom_anglais": "Italian cypress",
     "source": "photos (jardinerie Paquet Jardin, privé) + levé GAM", "priorite": 1, "confiance": "haute (essence) / faible (positions)",
     "port": "fastigié : colonne très étroite et dense, pointe effilée", "tronc": "non visible",
     "feuillage": feuillage("persistant", "#2E4A28", "#2E4A28", "inchangé (vert très sombre)", "inchangé"),
     "gabarit": {"hauteur": 16.0, "fut_nu": 0.5, "couronne_diametre": 2.5, "forme_couronne": "colonne fusiforme (rapport h/l ≈ 6-8)"},
     "positions_note": ("V2 : HORS EMPRISE. Relèvements de la colonne sombre sur 3 photos (2025-05-18 bc579b89 r01_c03 x≈910 → az 289° depuis (−54, −55) ; "
                        "2025-05-18 2374105b r01_c03 x≈655 → az 273° depuis (−40, −40) ; 2024-08-24 2ab4efbc r01_c03 x≈585 → az 272° depuis (−11, −6)) "
                        "quasi parallèles : sujets à ≥ 120-150 m vers l'ouest, au-delà de la limite x = −150 m. Les candidats V1 (arbre_108, 139, 140, 143, 164 ; "
                        "x −104…−115) sont à 20-25° de ces directions : ce sont des conifères génériques (groupe de cimes coniques privé). "
                        "Asset utile comme décor lointain / extension de l'emprise"),
     "production": {"principale": SPT, "alternatives": ["fab", "carla static.prop.cypresstree (silhouette proche, à mettre à l'échelle)"]},
     "photos_reference": [tuile(T_2AB4, "r01_c03"), tuile(T_BC579, "r01_c03"), tuile(T_2374, "r01_c03")]},
    {"asset": "arbre_pinus_sylvestris_moyen", "nom_latin": "Pinus sylvestris (probable)", "nom_francais": "pin sylvestre", "nom_anglais": "Scots pine",
     "source": "photos 2026-07 (abords sud, privé)", "priorite": 2, "confiance": "faible (espèce) — écorce orangée en tête observée",
     "port": "fût élancé dénudé, houppier clair et irrégulier en tête", "tronc": "écorce brun-gris en pied, orange saumon en partie haute",
     "feuillage": feuillage("persistant", "#3F5F3A", "#3F5F3A", "inchangé (aiguilles vert-bleu)", "inchangé"),
     "gabarit": {"hauteur": 15.0, "fut_nu": 8.0, "couronne_diametre": 6.0, "forme_couronne": "parasol irrégulier"},
     "production": {"principale": SPT, "alternatives": ["fab", LABS]}, "photos_reference": [tuile(T_DED0, "r01_c02"), tuile(T_F8D9, "r01_c02")]},
    {"asset": "arbre_cedrus_deodara_grand", "nom_latin": "Cedrus deodara (ou atlantica)", "nom_francais": "cèdre de l'Himalaya", "nom_anglais": "deodar cedar",
     "source": "photo 2025-01-12 (rive est du Vercors, devant le local technique, privé)", "priorite": 2, "confiance": "moyenne",
     "port": "grand conifère multi-troncs à branches retombantes, flèche penchée", "tronc": "2-3 troncs",
     "feuillage": feuillage("persistant", "#4C6A4A", "#4C6A4A", "inchangé", "inchangé"),
     "gabarit": {"hauteur": 17.0, "fut_nu": 2.0, "couronne_diametre": 10.0, "forme_couronne": "conique lâche, branches pendantes"},
     "production": {"principale": SPT, "alternatives": [LABS]}, "photos_reference": [tuile(T_D888, "r01_c01")]},
    # ---------------------------------------------------------------- compléments V2 (présents dans la scène, absents du catalogue des besoins)
    {"asset": "arbre_prunus_cerasifera_pissardii_moyen", "hors_catalogue_v1": True,
     "nom_latin": "Prunus cerasifera 'Pissardii' (probable ; Fagus sylvatica 'Purpurea' possible)", "nom_francais": "prunier myrobolan pourpre (ou hêtre pourpre)",
     "nom_anglais": "purple-leaf plum (or copper beech)",
     "source": "atelier objets arbre_273 (orthos 2022 et 2024 : couronne pourpre ≈ 8 m ; MNH 2021 : 10-11,5 m) ; vérifié V2 sur 2 photos", "priorite": 2,
     "confiance": "haute (présence, couleur) / faible (essence)",
     "port": "libre : houppier arrondi ajouré, ramure fine visible, derrière la haie de laurier-cerise de l'angle Revirée (repère coloré fort depuis le carrefour)",
     "tronc": "non visible (masqué par la haie)",
     "feuillage": feuillage("caduc", "#6B2E3A", "#8A3A2E", "pourpre-brun virant au rouge-bronze, chute commencée", "nu (rameaux fins sombres)",
                            chute="mi-octobre à début novembre", debourrement="mars-avril (floraison blanc rosé avant les feuilles si Prunus)"),
     "gabarit": {"hauteur": 11.0, "fut_nu": 2.0, "couronne_diametre": 8.0, "forme_couronne": "arrondie, ajourée", "feuille_cm": "4-6 (Prunus) / 6-10 (Fagus)"},
     "note_hauteur": "MNH IGN 10,0 m, LiDAR 2021 11,5 m ; sur la photo 2024-08-24 le sommet est au niveau du 3e-4e étage de l'immeuble voisin (≈ 10-11 m)",
     "production": {"principale": SPT, "alternatives": [LABS, "fab"], "note": "si Prunus : 1 tronc court, charpentières obliques ; texture de feuilles pourpres sombres (albédo ≈ #5A2630 à l'ombre)"},
     "photos_reference": [tuile(T_9834, "r01_c04"), tuile(T_5C0D_C4, "r01_c04")]},
    {"asset": "arbre_populus_alba_grand", "hors_catalogue_v1": True,
     "nom_latin": "Populus alba (d'après l'inventaire ; essence non confirmée sur photo)", "nom_francais": "peuplier blanc", "nom_anglais": "white poplar",
     "source": "inventaire Métropole (fiche « Abattu », non datée) ; atelier objets arbre_424 « à vérifier » : couronne LiDAR 2021 30,7 m, MNH IGN 28,8 m, ortho 2024 végétation 0,82",
     "priorite": 2, "confiance": "moyenne (présence d'un grand houppier à cet emplacement en 2025) / faible (essence)",
     "port": "libre : très grand fût, houppier large et irrégulier (17 m), charpentières épaisses",
     "tronc": "écorce blanc-gris lisse à lenticelles en losanges, crevassée noire en pied (Ø ≈ 0,46 m d'après 144 cm)",
     "feuillage": feuillage("caduc", "#5E8240", "#D8C060", "vert sombre dessus / revers blanc feutré (scintillement au vent), jaunissement tardif", "silhouette nue, rameaux blanchâtres"),
     "gabarit": {"hauteur": 29.0, "fut_nu": 6.0, "couronne_diametre": 17.0, "forme_couronne": "large, irrégulière"},
     "note_hauteur": "V2 : la photo 2025-05-18 7a182db7 (r00_c05 / r01_c05, à 28 m) montre à cet emplacement une masse arborée haute et dense le long de Verdun NE → arbre présent en 2025 ; garder 29 m (LiDAR/MNH concordants)",
     "production": {"principale": SPT, "alternatives": [LABS]},
     "photos_reference": [tuile(T_7A18, "r00_c05"), tuile(T_7A18, "r01_c05")]},
    # ---------------------------------------------------------------- génériques
    {"asset": "arbre_feuillu_generique_moyen", "nom_latin": "feuillus divers (essence non renseignée)", "nom_francais": "feuillu générique", "nom_anglais": "generic deciduous tree",
     "source": "levé GAM (ARBRE_FEUILLU) et LiDAR HD 2021 hors inventaire public", "priorite": 1, "confiance": "moyenne",
     "port": "3 variantes de silhouette recommandées (ovoïde dense type érable plane, étalée type robinier/frêne, colonne type charme fastigié)",
     "tronc": "Ø 0,2-0,5 m",
     "feuillage": feuillage("caduc", "#4C7A30", "#C9A845", "mélange vert / vert-jaune", "nu"),
     "gabarit": {"hauteur": 10.0, "fut_nu": 2.5, "couronne_diametre": 6.0, "forme_couronne": "variantes"},
     "note_hauteur": "atelier : 372 feuillus existants hors essences, hauteur LiDAR 2,5-29,5 m (médiane 10,1), couronne 1-17,5 m (médiane 4,3) → mise à l'échelle par instance",
     "production": {"principale": SPT, "alternatives": [LABS, "fab", "carla"]}, "photos_reference": [tuile(T_E540, "r01_c03")]},
    {"asset": "arbre_conifere_generique_moyen", "nom_latin": "conifères divers", "nom_francais": "conifère générique", "nom_anglais": "generic conifer",
     "source": "levé GAM (ARBRE_CONIFERE) + LiDAR", "priorite": 2, "confiance": "moyenne",
     "port": "conique (épicéa / pin noir / thuya)", "tronc": "Ø 0,2-0,4 m",
     "feuillage": feuillage("persistant", "#2F4F30", "#2F4F30", "inchangé", "inchangé"),
     "gabarit": {"hauteur": 12.0, "fut_nu": 1.5, "couronne_diametre": 5.0, "forme_couronne": "conique"},
     "note_hauteur": "atelier : 12 conifères, 5,0-27,0 m (médiane 12,4)",
     "production": {"principale": SPT, "alternatives": ["fab", "carla"]}, "photos_reference": []},
    # ---------------------------------------------------------------- jeunes sujets 2025
    {"asset": "arbre_alnus_cordata_jeune", "nom_latin": "Alnus cordata (code « Alc »)", "nom_francais": "aulne de Corse", "nom_anglais": "Italian alder",
     "source": "plan projet 2025 (TPC planté de Verdun SO, 2 sujets)", "priorite": 1, "confiance": "moyenne (code lisible à 150 dpi)", "jeune_sujet": True,
     "port": "jeune tige conique, axe droit", "tronc": "tige 16/18 (Ø ≈ 0,055 m à 1 m)",
     "feuillage": feuillage("caduc tardif", "#2F5E2A", "#5C7A2E", "encore vert foncé brillant (chute en novembre-décembre)", "chatons et petits cônes noirs"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 1.8, "forme_couronne": "conique étroite"},
     "production": {"principale": LABS, "alternatives": [SPT], "note": "générateur « jeune sujet » commun (voir arbre_jeune_tuteure_generique) paramétré par essence"},
     "photos_reference": ["data/sites/paquet_jardin/plan_projet_2025/tuiles/plan_projet_r01_c01.jpg", "assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_alnus_spaethii_jeune", "nom_latin": "Alnus × spaethii (code « As », lecture probable ; l'atelier lit « Acer sp. »)", "nom_francais": "aulne de Spaeth", "nom_anglais": "Spaeth's alder",
     "source": "plan projet 2025 (TPC planté SO, 2 sujets « As »)", "priorite": 2, "confiance": "faible (interprétation du code)", "jeune_sujet": True,
     "port": "jeune tige ovoïde", "tronc": "tige 16/18",
     "feuillage": feuillage("caduc tardif", "#355E2C", "#6B7A30", "vert foncé (jeunes pousses pourpres au printemps)", "nu"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 1.8, "forme_couronne": "ovoïde"},
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": ["assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_cercis_siliquastrum_jeune", "nom_latin": "Cercis siliquastrum (code « Cs »/« Ce », lecture probable)", "nom_francais": "arbre de Judée", "nom_anglais": "Judas tree",
     "source": "plan projet 2025 (TPC planté SO, 1 sujet)", "priorite": 2, "confiance": "faible", "jeune_sujet": True,
     "port": "jeune cépée ou tige, cime étalée", "tronc": "tige 14/16",
     "feuillage": feuillage("caduc", "#4F7B33", "#D6B648", "jaune pâle, gousses brun-violet", "gousses pendantes"),
     "gabarit": {"hauteur": 3.5, "fut_nu": 1.5, "couronne_diametre": 2.0, "forme_couronne": "étalée"},
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": ["assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_ulmus_hybride_jeune", "nom_latin": "Ulmus (hybride résistant à la graphiose, code « Ul »)", "nom_francais": "orme résistant", "nom_anglais": "disease-resistant elm",
     "source": "plan projet 2025 (noue plantée SE, 2 sujets)", "priorite": 1, "confiance": "moyenne", "jeune_sujet": True,
     "port": "jeune tige ovoïde à colonnaire selon cultivar", "tronc": "tige 16/18",
     "feuillage": feuillage("caduc", "#3F6B2D", "#D2B347", "vert", "nu"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 1.6, "forme_couronne": "ovoïde étroite"},
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": ["assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_quercus_cerris_jeune", "nom_latin": "Quercus cerris (code « Qc » ; l'atelier lit « Oc » = Ostrya carpinifolia)", "nom_francais": "chêne chevelu (ou charme-houblon)", "nom_anglais": "Turkey oak (or hop hornbeam)",
     "source": "plan projet 2025 (noue plantée SE, 2 sujets)", "priorite": 2, "confiance": "faible (code ambigu Qc/Oc à 150 dpi)", "jeune_sujet": True,
     "port": "jeune tige ovoïde", "tronc": "tige 16/18",
     "feuillage": feuillage("caduc", "#3E6A2C", "#A47A35", "vert (brunit fin octobre-novembre)", "nu"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 1.8, "forme_couronne": "ovoïde"},
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": ["assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_gleditsia_triacanthos_jeune", "nom_latin": "Gleditsia triacanthos (code « Gt », probablement 'Inermis' sans épines)", "nom_francais": "févier d'Amérique", "nom_anglais": "honey locust",
     "source": "plan projet 2025 (bande plantée NO le long de la piste, 2 sujets)", "priorite": 2, "confiance": "moyenne", "jeune_sujet": True,
     "port": "jeune tige à cime légère, feuillage très fin", "tronc": "tige 16/18",
     "feuillage": feuillage("caduc", "#6E9440", "#E2C54A", "jaune vif, chute rapide (souvent déjà clairsemé mi-octobre)", "gousses torsadées brunes"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 2.0, "forme_couronne": "étalée légère", "feuille_cm": "15-20 (bipennée, folioles 2 cm)"},
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": ["assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_celtis_australis_jeune", "nom_latin": "Celtis australis (code « Ca »)", "nom_francais": "micocoulier de Provence", "nom_anglais": "European nettle tree",
     "source": "plan projet 2025 (angle NO / Revirée, 1 sujet)", "priorite": 2, "confiance": "moyenne", "jeune_sujet": True,
     "port": "jeune tige à cime arrondie", "tronc": "tige 16/18, écorce grise lisse",
     "feuillage": feuillage("caduc tardif", "#4A7630", "#C8BE5A", "vert (jaune pâle en novembre)", "nu"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 2.0, "forme_couronne": "arrondie"},
     "production": {"principale": LABS, "alternatives": [SPT]}, "photos_reference": ["assets/qa/mobilier_vegetation_carla/qa_07_plan_jeunes_sujets.jpg"]},
    {"asset": "arbre_jeune_tuteure_generique", "nom_latin": "jeune sujet tuteuré (essence non confirmée)", "nom_francais": "jeune arbre tuteuré", "nom_anglais": "staked young tree",
     "source": "plan projet 2025 (15 fosses d'arbres) ; photos 2026-07 (jeunes plantations au sud et à l'est)", "priorite": 1, "confiance": "haute (besoin)", "jeune_sujet": True,
     "port": "tige de pépinière (force 16/18 à 20/25), cime formée de 5-8 charpentières",
     "tronc": "Ø 0,05-0,08 m à 1 m",
     "tuteurage": {"type": "tripode", "piquets": "3 piquets bois ronds Ø 0,08 m, h 2,2 m hors sol, à 0,5 m du tronc", "liaisons": "3 demi-rondins en tête + colliers caoutchouc",
                   "fosse": "cuvette Ø 1,5-2,0 m, paillage (minéral gris ou copeaux brun)", "protection": "option : ganivelle (voir mobilier.json) ou corset de protection en pied"},
     "feuillage": feuillage("caduc", "#4C7A30", "#C9A845", "feuillé, début de coloration ; 2e automne après plantation (feuillage clairsemé)", "tige nue + tuteurs (silhouette fine)"),
     "gabarit": {"hauteur": 4.5, "fut_nu": 1.8, "couronne_diametre": 1.8, "forme_couronne": "ovoïde lâche"},
     "production": {"principale": LABS, "alternatives": [SPT], "note": "un HDA Houdini « jeune_sujet » (tronc + 5-8 branches + feuilles + tripode) paramétré par essence couvre les 8 essences 2025"},
     "photos_reference": [tuile(T_FFC2, "r01_c00"), tuile(T_F8D9, "r01_c03")]},
    # ---------------------------------------------------------------- haies, massifs
    {"asset": "haie_taillee_persistante", "nom_latin": "Prunus laurocerasus / Photinia / Ligustrum (probables)", "nom_francais": "haie taillée persistante", "nom_anglais": "trimmed evergreen hedge",
     "source": "BD TOPO (haie 646 m) + GAM SOL_VEGETATION + photos (haies séparatives de Verdun SO, angle Revirée)", "priorite": 1,
     "confiance": "haute (présence) / moyenne (essence : laurier-cerise confirmé de près à l'angle Revirée — 2024-05-01 b4013696 r01_c04 : grandes feuilles vernissées elliptiques, 10-15 cm)",
     "port": "volume taillé à faces planes et dessus plat ou arrondi, base parfois dégarnie",
     "tronc": "—",
     "feuillage": feuillage("persistant", "#3D6A2A", "#3D6A2A", "inchangé (quelques pousses claires si taille tardive)", "inchangé"),
     "gabarit": {"hauteur": "1,2-2,5 (Verdun SO ≈ 2,0 ; angle Revirée ≈ 1,2-1,8)", "epaisseur": "1,0-2,5", "module": "segment extrudable de 2 m (coque + cartes de feuillage), extrémités arrondies"},
     "production": {"principale": "maison Houdini (coque extrudée le long des lignes BD TOPO/GAM + scatter de cartes de feuilles)", "alternatives": ["fab (haies Megascans)", "carla BP_Spline / BP_Wall avec un maillage de haie"]},
     "photos_reference": [tuile(T_B401, "r01_c04"), tuile(T_E5D7, "r01_c04"), tuile("2024-05-01_3fc0ff2e-69fd-4697-95ca-337b368e178d", "r01_c03"), tuile(T_E540, "r01_c03")]},
    {"asset": "massif_arbustif", "nom_latin": "mélange d'arbustes (charmille libre, laurier, cornouiller, buis, graminées)", "nom_francais": "massif arbustif", "nom_anglais": "shrub bed",
     "source": "BD TOPO zone de végétation ≈ 9 900 m² + photos", "priorite": 2, "confiance": "haute (présence)",
     "port": "touffes 0,5-3 m, masses libres", "tronc": "—",
     "feuillage": feuillage("mixte", "#4A7630", "#B98D3E", "mélange vert / jaune / roux", "masses brunes, persistants verts"),
     "gabarit": {"hauteur": "0,5-3,0", "elements": "4-6 arbustes types à disperser (scatter) selon la densité de l'ortho"},
     "production": {"principale": "fab", "alternatives": [SPT, "carla /Game/Carla/Static/Vegetation (buissons)"]},
     "photos_reference": [tuile("2025-05-18_734a0da6-aa95-4a49-ab8d-975a95986a2a", "r01_c03"), tuile(T_2374, "r01_c03"), tuile(T_F8D9, "r01_c02")]},
]

NON_RETENUS = [
    {"type": "Populus alba, Populus nigra (1), Salix alba (3), Robinia pseudoacacia, Betula pendula (2), Fraxinus excelsior (1), Acer campestre (1), Crataegus laevigata (1), Populus sp. (5)",
     "raison": ("16 fiches « Abattu » de l'inventaire dans l'emprise : absents en 2026 — sauf V2 : le Populus alba arbre_424 (houppier LiDAR 2021 de 30,7 m, "
                "ortho 2024 et photo 2025-05-18 7a182db7) est retenu comme présent probable (arbre_populus_alba_grand)")},
    {"type": "Platanus × acerifolia", "raison": "pas de platane d'alignement dans l'emprise (le têtard du NE est un peuplier d'après l'inventaire)"},
]


# V2 : hauteurs à utiliser à la place de la hauteur mesurée de l'atelier quand celle-ci est manifestement celle d'un voisin
# (la substitution met chaque arbre à l'échelle de sa hauteur : une valeur aberrante donne un saule de 26 m ou un peuplier de 3 m).
HAUTEURS_RETENUES = {
    "arbre_363": (3.5, "peuplier d'Italie probablement recépé/abattu : LiDAR 2021 3,0 m et MNH IGN 4,1 m concordants → cépée de 3-4 m (ou souche)", "LiDAR + MNH"),
    "arbre_458": (8.0, "saule têtard (classe [5;10 m[) : LiDAR 26,4 / MNH 26,0 m = peupliers voisins", "inventaire"),
    "arbre_339": (6.0, "aubépine (classe [0;5 m[, plantée 1990) : LiDAR 11,9 / MNH 10,9 m = couronne voisine", "inventaire + âge"),
    "arbre_004": (5.0, "magnolia (classe [0;5 m[) : 9,0 m mesurés = grand feuillu voisin (photo 2026-07-28 05089869 r01_c04)", "photo"),
    "arbre_005": (5.0, "magnolia (classe [0;5 m[) : 7,9 m mesurés = grand feuillu voisin (photo 2026-07-28 05089869 r01_c04)", "photo"),
}

# V2 : instances de la scène à poser avec un autre asset que celui de leur essence (preuve à l'appui)
REAFFECTATIONS = {
    "arbre_363": ("massif_arbustif", "peuplier d'Italie de 1960 très probablement recépé : LiDAR 2021 3,0 m et MNH IGN 4,1 m, couronne 4,8 m → cépée de rejets ; "
                                     "garder arbre_populus_nigra_italica_grand pour d'autres sites"),
}
