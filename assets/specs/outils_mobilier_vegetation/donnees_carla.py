"""Correspondances CARLA (contenu Unreal du dépôt CARLA de l'utilisateur) pour chaque asset de la
librairie. Seuls les noms et chemins publiés dans la documentation officielle sont donnés comme
« documentés » ; les chemins exacts des static meshes sont résolus sur le PC par
assets/carla_resoudre_chemins.py (lecture de Content/Carla/Config/*.Package.json et des dossiers
de contenu)."""

DOC = {
    "props": "https://carla.readthedocs.io/en/latest/catalogue_props/",
    "bp_library": "https://carla.readthedocs.io/en/latest/bp_library/",
    "props_json": "https://carla.readthedocs.io/en/latest/content_authoring_props/",
    "maps": "https://carla.readthedocs.io/en/latest/tuto_content_authoring_maps/",
    "tl_0915": "https://carla.readthedocs.io/en/0.9.15/tuto_M_custom_add_tl/",
    "landscape_0915": "https://carla.readthedocs.io/en/0.9.15/tuto_M_custom_weather_landscape/",
    "road_painter_0915": "https://carla.readthedocs.io/en/0.9.15/tuto_M_custom_road_painter/",
    "core_map": "https://carla.readthedocs.io/en/latest/core_map/",
}

DOSSIERS = {
    "static": {"chemin": "/Game/Carla/Static/", "contenu": "racine du contenu statique (citée par la documentation du Road Painter : « Content/Carla/Static/Decals and Content/Carla/Static ») : recherche par mots-clés pour les objets non listés (lampadaires, bornes, clôtures, coffrets)", "doc": DOC["road_painter_0915"]},
    "props": {"chemin": "/Game/Carla/Static/Static/", "contenu": "static meshes des props (ex. documenté : /Game/Carla/Static/Static/SM_Atm.SM_Atm pour le prop « ATM »)",
              "enregistrement": "Content/Carla/Config/Default.Package.json : entrée {name, path, size} ; identifiant Python static.prop.<name en minuscules>", "doc": DOC["props_json"]},
    "feux": {"chemin": "/Game/Carla/Static/TrafficLight/StreetLights_01/", "contenu": "blueprints de feux tricolores (logique CARLA : groupes, volumes de déclenchement)", "doc": DOC["maps"]},
    "panneaux": {"chemin": "/Game/Carla/Static/TrafficSign/", "contenu": "blueprints de panneaux (Stop, Yield, limitations de vitesse...)", "doc": DOC["maps"]},
    "vegetation": {"chemin": "/Game/Carla/Static/Vegetation/", "contenu": "blueprints d'arbres, buissons, arbustes", "doc": DOC["maps"]},
    "poteaux_reseau": {"chemin": "/Game/Carla/Static/Pole/PoweLine/", "contenu": "BP_SplinePoweLine (poteaux électriques + câbles le long d'une courbe) et maillages de poteaux", "doc": DOC["landscape_0915"]},
    "level_design": {"chemin": "/Game/Carla/Blueprints/LevelDesign/", "contenu": "BP_Spline (maillage déformé le long d'une courbe : bordures, haies), BP_RepSpline (éléments répétés : potelets, arceaux), BP_Wall (éléments joints : barrières, clôtures)", "doc": DOC["landscape_0915"]},
    "decals": {"chemin": "/Game/Carla/Static/Decals/", "contenu": "décals de chaussée (tampons, fissures, taches)", "doc": DOC["road_painter_0915"]},
    "materiaux": {"chemin": "/Game/Carla/Static/GenericMaterials/", "contenu": "matériaux génériques (Asphalt/Textures, RoadPainterMaterials)", "doc": DOC["road_painter_0915"]},
}

# Props documentés (catalogue officiel) utiles ici : blueprint → libellé du catalogue
PROPS = {
    "static.prop.bench01": "Bench 01", "static.prop.bench02": "Bench 02", "static.prop.bench03": "Bench 03",
    "static.prop.trashcan01": "Trash can 01", "static.prop.trashcan02": "Trash can 02", "static.prop.trashcan03": "Trash can 03",
    "static.prop.trashcan04": "Trash can 04", "static.prop.trashcan05": "Trash can 05", "static.prop.bin": "Bin",
    "static.prop.busstop": "Bus stop", "static.prop.busstoplb": "Bus stop alternate", "static.prop.advertisement": "Advertisement",
    "static.prop.chainbarrier": "Chain barrier", "static.prop.chainbarrierend": "Chain barrier end",
    "static.prop.streetbarrier": "Street barrier", "static.prop.constructioncone": "Construction cone",
    "static.prop.trafficcone01": "Traffic cone 01", "static.prop.trafficcone02": "Traffic cone 02",
    "static.prop.warningconstruction": "Warning construction", "static.prop.trafficwarning": "Traffic warning",
    "static.prop.mailbox": "Mailbox", "static.prop.streetfountain": "Street fountain", "static.prop.glasscontainer": "Glass container",
    "static.prop.cypresstree": "Cypress tree", "static.prop.aporosatree": "Aporosa tree", "static.prop.streetsign": "Street sign",
}


def prop(bp, note=None):
    d = {"nom": PROPS[bp], "blueprint_id": bp, "dossier_unreal": DOSSIERS["props"]["chemin"],
         "chemin_unreal": None, "a_resoudre": f"entrée « name » = {bp.split('.')[-1]} (insensible à la casse) de Default.Package.json → champ path",
         "documente": "catalogue des props (blueprint ID)", "source_doc": DOC["props"]}
    if note:
        d["note"] = note
    return d


def dossier(cle, mots, note=None):
    d = {"nom": f"contenu du dossier {DOSSIERS[cle]['chemin']}", "blueprint_id": None, "dossier_unreal": DOSSIERS[cle]["chemin"],
         "chemin_unreal": None, "mots_cles": mots, "documente": "dossier cité par la documentation (noms des assets non publiés)",
         "source_doc": DOSSIERS[cle]["doc"]}
    if note:
        d["note"] = note
    return d


def corr(asset):
    """Renvoie (candidats, adequation, justification, recommandation) pour un nom d'asset."""
    a = asset
    # ---------------------------------------------------------------- signalisation
    if a.startswith("panneau_"):
        code = a.split("_", 1)[1]
        if code == "AB4":
            return ([dossier("panneaux", ["Stop"])], "proche",
                    "octogone rouge « STOP » de même forme, mais typographie, proportions et rétroréflexion non conformes à l'IISR / arrêté de 1967",
                    "maison (face officielle specs/panneaux/faces/AB4.png) ; le blueprint Stop CARLA peut servir de doublure logique")
        if code == "AB3a":
            return ([dossier("panneaux", ["Yield"])], "proche",
                    "triangle « cédez le passage » de même forme, liseré et proportions non IISR",
                    "maison (face officielle)")
        if code in ("B2b_temporaire", "AK5"):
            c = [prop("static.prop.warningconstruction", "losange orange américain")] if code == "AK5" else []
            return (c, "à éviter", "signalisation temporaire américaine (losange orange) sans équivalent français K/AK", "maison")
        return ([dossier("panneaux", [code])], "à éviter" if code[0] in "ABCJM" else "aucun équivalent",
                "pas d'équivalent français dans le contenu CARLA (panneaux américains / génériques)", "maison (faces officielles Wikimedia, specs/panneaux.json)")
    if a.startswith("plaque_rue") or a.startswith("totem_"):
        return ([], "aucun équivalent", "signalétique locale (texte, charte SMMAG)", "maison")
    if a.startswith("mat_panneau"):
        return ([dossier("panneaux", ["Pole", "Post"])], "proche", "simple tube : géométrie triviale, mais diamètre / bouchon à contrôler", "maison (tube Ø 60 mm)")
    if a.startswith("feu_") or a == "boitier_bouton_appel" or a.startswith("mat_feu"):
        if a == "mat_feu_provisoire":
            return ([], "aucun équivalent", "mât de chantier lesté (scénario travaux)", "maison")
        return ([dossier("feux", ["TrafficLight", "Light"], "blueprints américains (têtes à 3 feux avec plaque, potences) : utiles pour la LOGIQUE CARLA, pas pour l'aspect")],
                "à éviter", "feux américains (têtes, plaques de contraste, potences) très différents des R11v/R12 français à modules séparés et visières",
                "maison (specs/feux.json) ; si simulation CARLA : remplacer le mesh des blueprints StreetLights_01 par l'asset français en gardant la logique")
    if a == "armoire_commande_feux":
        return ([dossier("static", ["ElectricBox", "Electric_Box", "Cabinet", "TrafficBox"])], "aucun équivalent", "pas d'armoire de contrôleur documentée", "maison")
    # ---------------------------------------------------------------- éclairage / réseaux
    if a.startswith("candelabre_"):
        return ([dossier("static", ["StreetLight", "Streetlight", "Street_Light", "Lamp", "LightPole"], "les lampadaires des villes CARLA (couche « StreetLights ») ne sont pas listés dans la documentation : résolution par mots-clés sur le PC")],
                "proche", "silhouette de candélabre routier possible, mais lanternes et crosses différentes (Verdun : double crosse en T de 2,4 m, lanternes plates)",
                "maison (mobilier.json)")
    if a == "poteau_bois_reseau":
        return ([dossier("poteaux_reseau", ["Pole", "PowerLine", "PoweLine", "Wood"])], "proche",
                "poteaux bois américains à traverses ; le BP_SplinePoweLine est utile pour poser les câbles", "maison (ou CARLA en supprimant les traverses)")
    if a == "mat_illumination_cable":
        return ([dossier("poteaux_reseau", ["Pole", "PowerLine"])], "à éviter", "poteaux électriques américains ; le mât acier brun à bras porte-câbles n'existe pas", "maison")
    # ---------------------------------------------------------------- transport
    if a == "abri_bus_m_reso":
        return ([prop("static.prop.busstop", "ossature verte, banc rouge"), prop("static.prop.busstoplb")], "proche",
                "même typologie (abri vitré + panneau publicitaire), couleurs, toit et proportions différents de l'abri M réso",
                "maison ; doublure CARLA possible (retexturer anthracite, banc bois)")
    if a == "poteau_arret_m_reso":
        return ([prop("static.prop.streetsign", "panneau sur pied américain")], "à éviter", "aucun poteau d'arrêt à disque « M »", "maison")
    # ---------------------------------------------------------------- mobilier
    if a == "potelet_noir":
        return ([prop("static.prop.chainbarrierend", "potelet noir isolé (extrémité de chaîne)"), prop("static.prop.chainbarrier")], "proche",
                "potelet cylindrique sombre ; il manque la tête blanche contrastée", "maison (ou CARLA + bande blanche)")
    if a == "banc_bois_metal":
        return ([prop("static.prop.bench01", "lattes bois + dossier"), prop("static.prop.bench02", "sans dossier")], "proche",
                "banc à lattes de bois et dossier : forme proche, bois trop clair", "CARLA bench01 retexturé (bois brun, piétement sombre) ou maison")
    if a == "corbeille_cylindrique":
        return ([prop("static.prop.trashcan03", "cylindre"), prop("static.prop.trashcan02", "corbeille ouverte sur pied")], "proche",
                "silhouette cylindrique ; ni lames ajourées ni couvercle jaune", "maison")
    if a == "barriere_croix_saint_andre":
        return ([dossier("level_design", ["BP_Wall"], "pour poser les modules le long d'une courbe")], "aucun équivalent", "pas de barrière de ville française", "maison")
    if a == "arceau_velo":
        return ([dossier("level_design", ["BP_RepSpline"], "pour aligner les arceaux")], "aucun équivalent", "pas d'arceau vélo documenté", "maison")
    if a in ("barriere_levante", "armoire_technique", "ganivelle_bois"):
        return ([], "aucun équivalent", "non présent dans le catalogue des props", "maison")
    if a == "poteau_incendie":
        return ([dossier("static", ["Hydrant"], "si une borne d'incendie américaine existe dans les villes CARLA : à éviter")], "à éviter",
                "les bornes d'incendie américaines (bouches latérales, couleur, gabarit) ne correspondent pas au poteau rouge NF EN 14384", "maison")
    if a == "cloture_grillage_rigide":
        return ([dossier("level_design", ["BP_Wall"]), dossier("static", ["Fence"])], "proche",
                "clôtures des villes CARLA (étiquette sémantique Fence) : grillages américains, à vérifier", "CC0 / Fab (panneaux rigides) posés avec BP_Wall")
    if a in ("separateur_modulaire_K16", "balise_chevrons_chantier"):
        return ([], "aucun équivalent", "signalisation temporaire française (K16, K8/J4 temporaire)", "maison")
    if a == "barriere_chantier_rouge_blanc":
        return ([prop("static.prop.streetbarrier", "chevalet américain jaune et blanc")], "à éviter", "barrière américaine (couleurs et forme) ; K2 français rouge/blanc", "maison")
    # ---------------------------------------------------------------- bordures
    if a.startswith("bordure_") or a in ("caniveau_cs", "abaisse_chartiere"):
        return ([dossier("level_design", ["BP_Spline"], "outil de pose : déformer le maillage de profil (bordures.json) le long des lignes de bordures")],
                "aucun équivalent", "les bordures CARLA sont générées avec les routes (profils américains) ; pas de profil T2/A2/P1/quai",
                "maison (profils bordures.json, Sweep Houdini)")
    if a == "bev_podotactile":
        return ([], "aucun équivalent", "pas de dalle podotactile NF P98-351", "maison (géométrie) + CC0 (béton)")
    # ---------------------------------------------------------------- matériaux
    if a.startswith("enrobe_"):
        return ([dossier("materiaux", ["Asphalt"])], "proche", "enrobés génériques CARLA (texture américaine, sans fissures pontées ni teinte de l'ortho)",
                "CC0 (manifeste_cc0.json + telecharger_cc0.py, recolorés sur l'ortho)")
    if a.startswith("peinture_"):
        if a in ("peinture_blanche",):
            return ([dossier("materiaux", ["RoadPainter", "LaneMarking"])], "proche", "marquage blanc générique du Road Painter CARLA ; usure et rétroréflexion à reprendre",
                    "maison (specs/peinture.json : MF_PeintureRoutiere)")
        return ([], "aucun équivalent", "teintes françaises (jaune Chronovélo, jaune zigzag, vert) absentes", "maison (specs/peinture.json)")
    if a.startswith("decal_") or a == "pontage_fissures":
        return ([dossier("decals", ["Manhole", "Crack", "Decal"])], "proche", "décals génériques de tampons et de fissures", "maison / CC0 (tampons fonte français)")
    if a in ("resine_verte", "resine_cyan", "enrobe_colore_ocre"):
        return ([], "aucun équivalent", "revêtements colorés locaux", "CC0 recoloré")
    if a in ("beton_bordure", "paves_granit", "beton_galets", "gravillons_ilot", "stabilise_beige", "gazon_tondu", "herbe_haute", "gazon_sec",
             "noue_plantee", "paillage_mineral", "terre_nue"):
        return ([dossier("materiaux", ["Concrete", "Grass", "Gravel", "Dirt", "Cobble"])], "proche", "matériaux génériques des villes CARLA (non documentés individuellement)",
                "CC0 (manifeste_cc0.json) ; Megascans (Fab) pour herbes 3D")
    # ---------------------------------------------------------------- végétation
    if a == "arbre_cupressus_sempervirens_grand":
        return ([prop("static.prop.cypresstree", "cyprès colonnaire (à mettre à l'échelle 15-18 m)"), dossier("vegetation", ["Cypress"])], "proche",
                "silhouette colonnaire proche du cyprès d'Italie ; densité et teinte à vérifier", "SpeedTree (ou CARLA cypresstree en doublure)")
    if a.startswith("arbre_") or a in ("haie_taillee_persistante", "massif_arbustif"):
        mots = {
            "populus": ["Poplar", "Populus"], "cedrus": ["Cedar", "Cedrus"], "tilia": ["Linden", "Lime", "Tilia"], "quercus": ["Oak", "Quercus"],
            "acer": ["Maple", "Acer"], "fraxinus": ["Ash", "Fraxinus"], "carpinus": ["Hornbeam", "Carpinus"], "betula": ["Birch", "Betula"],
            "corylus": ["Hazel", "Corylus"], "magnolia": ["Magnolia"], "crataegus": ["Hawthorn", "Crataegus"], "sorbus": ["Rowan", "Sorbus"],
            "salix": ["Willow", "Salix"], "pinus": ["Pine", "Pinus"], "alnus": ["Alder", "Alnus"], "cercis": ["Judas", "Cercis", "Redbud"],
            "ulmus": ["Elm", "Ulmus"], "gleditsia": ["Locust", "Gleditsia"], "celtis": ["Hackberry", "Celtis"], "feuillu": ["Tree", "Broadleaf"],
            "conifere": ["Pine", "Spruce", "Fir", "Conifer"], "jeune": ["Sapling", "Young"], "haie": ["Hedge", "Bush"], "massif": ["Bush", "Shrub"],
        }
        g = a.split("_")[1] if a.startswith("arbre_") else a.split("_")[0]
        if a.startswith("arbre_jeune"):
            g = "jeune"
        m = mots.get(g, ["Tree"])
        adequ = "proche" if g in ("feuillu", "conifere", "massif", "haie") else "à vérifier"
        just = ("végétation générique CARLA : silhouette acceptable pour un générique" if adequ == "proche"
                else "essence européenne précise rarement présente dans CARLA : vérifier les candidats listés par le script de résolution")
        reco = {"haie": "maison (coque extrudée + cartes) ou Fab", "massif": "Fab (Megascans) ou SpeedTree"}.get(g, "SpeedTree (ou SideFX Labs Tree / Fab)")
        return ([dossier("vegetation", m)], adequ, just, reco)
    return ([], "aucun équivalent", "non traité", "maison")


# Doublures CARLA vues sur les vignettes officielles du catalogue (planche qa_08_carla_vs_reel.jpg)
CONSTATS_VIGNETTES = {
    "static.prop.bench01": "banc à lattes claires + dossier, piétement métal : forme proche du banc des quais",
    "static.prop.bench02": "même banc sans dossier",
    "static.prop.trashcan03": "corbeille cylindrique pleine, gris clair : silhouette seulement",
    "static.prop.trashcan02": "corbeille ouverte sur pied (type Paris) : à éviter",
    "static.prop.busstop": "abri à ossature verte, banc rouge, panneau publicitaire : typologie proche, aspect différent",
    "static.prop.chainbarrier": "potelets noirs reliés par une chaîne : potelet proche",
    "static.prop.streetbarrier": "chevalet américain jaune/blanc : à éviter",
    "static.prop.constructioncone": "cône orange à bande blanche : proche d'un K5a (le K5a français est rouge et blanc)",
    "static.prop.trafficcone01": "fût orange/blanc américain : à éviter",
    "static.prop.warningconstruction": "panneau losange orange américain : à éviter",
    "static.prop.mailbox": "boîte aux lettres USPS : à éviter",
    "static.prop.cypresstree": "cyprès colonnaire : proche du cyprès d'Italie",
    "static.prop.aporosatree": "arbre tropical : à éviter",
}
