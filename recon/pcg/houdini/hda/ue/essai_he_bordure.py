"""Essai Houdini Engine de pj::bordure dans l'éditeur UE 5.8 (exécuté DANS Unreal : pj_tools.run_python_file).

ARGS = {"etape": ..., ...} ; l'état persiste entre deux appels dans le module sys.modules["pj_essai_he_etat"] (la cuisson
Houdini Engine est asynchrone : elle avance aux ticks de l'éditeur, entre deux appels MCP). Étapes :

    importer     {"hda": "<.hdalc>", "dossier": "/Game/PJ/Houdini"}          import (remplace) -> HoudiniAsset
    session      {}                                                           relance la session Houdini Engine
    instancier   {"asset": "/Game/PJ/Houdini/pj_bordure", "label": ..., "points_cm": [[x, y, z], ...],
                  "parametres": {nom: valeur}}                                acteur HDA + entrée courbe Houdini (spline)
    etat         {}                                                           état de cuisson, inventaire des sorties
    parametre    {"nom": "joint_mm", "valeur": 10.0}                          Public API -> recuisson automatique
    pcg          {"asset": ..., "graphe": "/Game/PJ/Houdini/PCG_Bordure_HDA", "label": ..., "points_cm": [...],
                  "parametres": {nom: valeur}}                                graphe PCG : spline -> nœud « Houdini
                                                                              Digital Asset » (pj::bordure)
    pcg_cabler   {}                                                           câble les broches de l'HDA (après son
                                                                              instanciation), acteur spline + PCG
    pcg_etat     {}                                                           composants créés par le nœud PCG
    nettoyer     {"labels": [...]}                                            retire les acteurs d'essai

Repère : UE = (100 x, −100 y, 100 z) du repère local ; Houdini Engine convertit UE -> Houdini (X, Z, Y) / 100, soit
(x, z, −y) local : la convention des HDA pj::* (README_HDA.md § 2).
"""
import json
import sys
import types

import unreal

ETAT = sys.modules.get("pj_essai_he_etat")
if ETAT is None:
    ETAT = types.ModuleType("pj_essai_he_etat")
    ETAT.journal = []
    sys.modules["pj_essai_he_etat"] = ETAT

ARGS = globals().get("ARGS") or {}
ACTEURS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def journal(msg):
    ETAT.journal.append(msg)
    unreal.log(f"pj_essai_he: {msg}")


def acteur(label):
    for a in ACTEURS.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


# ------------------------------------------------------------------------------------------------ import
def importer(hda, dossier):
    t = unreal.AssetImportTask()
    t.filename = hda
    t.destination_path = dossier
    t.automated = True
    t.replace_existing = True
    t.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    chemins = [str(p) for p in t.get_editor_property("imported_object_paths")]
    return {"importes": chemins,
            "classes": [unreal.load_asset(p).get_class().get_name() for p in chemins if unreal.load_asset(p)]}


# ------------------------------------------------------------------------------------------------ paramètres
def regler(wr, parametres):
    """Paramètres par type (Public API) ; renvoie {nom: accepté}."""
    ok = {}
    for nom in sorted(parametres):
        v = parametres[nom]
        if isinstance(v, bool):
            ok[nom] = bool(wr.set_bool_parameter_value(nom, v))
        elif isinstance(v, int):
            ok[nom] = bool(wr.set_int_parameter_value(nom, v))
        elif isinstance(v, float):
            ok[nom] = bool(wr.set_float_parameter_value(nom, v))
        else:
            ok[nom] = bool(wr.set_string_parameter_value(nom, str(v)))
    return ok


def entree_courbe(wr, points_cm):
    """Entrée 1 = courbe Houdini (HoudiniPublicAPICurveInput : spline éditable dans UE), polygone par les points."""
    ci = wr.create_empty_input(unreal.HoudiniPublicAPICurveInput)
    co = unreal.HoudiniPublicAPICurveInputObject(ci)
    co.set_curve_points([unreal.Transform(location=unreal.Vector(*p)) for p in points_cm])
    co.set_curve_type(unreal.HoudiniPublicAPICurveType.POLYGON)
    co.set_closed(False)
    ci.set_input_objects([co])
    return bool(wr.set_input_at_index(0, ci))


# ------------------------------------------------------------------------------------------------ inventaire
def inventaire_composant(comp, obj=None):
    rec = {"classe": comp.get_class().get_name(), "nom": comp.get_name()}
    sm = None
    if isinstance(comp, unreal.StaticMeshComponent):
        sm = comp.get_editor_property("static_mesh")
    if sm is not None:
        rec["mesh"] = sm.get_name()
        try:
            rec["triangles"] = int(sm.get_num_triangles(0))
        except Exception:  # noqa: BLE001
            pass
        b = sm.get_bounding_box()
        rec["etendue_cm"] = [round(b.max.x - b.min.x, 2), round(b.max.y - b.min.y, 2), round(b.max.z - b.min.z, 2)]
        rec["materiaux"] = sorted({m.get_name() for m in comp.get_materials() if m})
    if isinstance(comp, unreal.InstancedStaticMeshComponent):
        n = comp.get_instance_count()
        rec["instances"] = n
        sx = []
        for i in range(n):
            tr = comp.get_instance_transform(i, False)
            sx.append(round(tr.scale3d.x, 4))
        rec["echelles_x"] = sx
    elif sm is not None:                    # instancier à une seule instance : Houdini Engine pose un StaticMeshComponent
        rec["instances"] = 1
        rec["echelles_x"] = [round(comp.get_editor_property("relative_scale3d").x, 4)]
    return rec


def inventaire(wr):
    out = []
    for i in range(wr.get_num_outputs()):
        ids = wr.get_output_identifiers_at(i)
        if isinstance(ids, tuple):
            ids = ids[-1]
        for ident in ids or []:
            obj = wr.get_output_object_at(i, ident)
            comp = wr.get_output_component_at(i, ident)
            rec = {"sortie": i, "type": str(wr.get_output_type_at(i)),
                   "objet": obj.get_path_name() if obj else None}
            if comp is not None:
                comps = comp if isinstance(comp, (list, tuple)) else [comp]
                rec["composants"] = [inventaire_composant(c, obj) for c in comps if c]
            out.append(rec)
    return out


def bilan_joints(recs):
    """Composants instanciés : joints = prototypes de moins de 3 cm le long de X (prototype de joint de 10 mm, échelle
    X = (largeur + 4 mm) / 10 mm, poser.vfl) ; éléments = le reste."""
    j, e, larg = 0, 0, []
    for r in recs:
        for c in r.get("composants", []):
            if "instances" not in c:
                continue
            ex = (c.get("etendue_cm") or [100])[0]
            if ex < 3.0:
                j += c["instances"]
                larg += [round(s * ex / 100.0 - 0.004, 4) for s in c["echelles_x"]]
            else:
                e += c["instances"]
    larg.sort()
    return {"elements": e, "joints": j, "largeur_joints_m": {"min": larg[0], "max": larg[-1],
                                                              "p50": larg[len(larg) // 2]} if larg else None}


# ------------------------------------------------------------------------------------------------ étapes
def instancier(asset_path, label, points_cm, parametres):
    api = unreal.HoudiniPublicAPIBlueprintLib.get_api()
    ancien = acteur(label)
    if ancien is not None:
        ACTEURS.destroy_actor(ancien)
    asset = unreal.load_asset(asset_path)
    ETAT.cuissons = []
    ETAT.traitements = 0
    ETAT.parametres = parametres
    ETAT.points_cm = points_cm

    def apres_instanciation(wr):
        wr.on_post_instantiation_delegate.remove_callable(apres_instanciation)
        wr.set_proxy_mesh_enabled(False)                 # vrais StaticMesh (pas de maillages proxy)
        ETAT.regles = regler(wr, ETAT.parametres)
        ETAT.entree = entree_courbe(wr, ETAT.points_cm)
        journal(f"instancié, paramètres {ETAT.regles}, entrée courbe {ETAT.entree}")

    def apres_cuisson(wr, ok):
        ETAT.cuissons.append(bool(ok))
        journal(f"cuisson {len(ETAT.cuissons)} : {ok}")

    def apres_traitement(wr):
        ETAT.traitements += 1
        ETAT.sorties = inventaire(wr)
        journal(f"sorties traitées ({ETAT.traitements}) : {len(ETAT.sorties)} objets")

    ETAT.rappels = (apres_instanciation, apres_cuisson, apres_traitement)
    wr = api.instantiate_asset(asset, unreal.Transform(), None, None, True)
    wr.on_post_instantiation_delegate.add_callable(apres_instanciation)
    wr.on_post_cook_delegate.add_callable(apres_cuisson)
    wr.on_post_processing_delegate.add_callable(apres_traitement)
    ETAT.wrapper = wr
    a = wr.get_houdini_asset_actor()
    if a is not None:
        a.set_actor_label(label)
    return {"acteur": a.get_name() if a else None, "asset": asset.get_path_name()}


def etat():
    wr = getattr(ETAT, "wrapper", None)
    if wr is None:
        return {"wrapper": None}
    out = {"cuissons": list(ETAT.cuissons), "traitements": ETAT.traitements, "journal": ETAT.journal[-12:],
           "regles": getattr(ETAT, "regles", None), "entree": getattr(ETAT, "entree", None)}
    if ETAT.traitements:
        recs = inventaire(wr)
        out["sorties"] = [{k: (v if k != "composants" else [{kk: vv for kk, vv in c.items() if kk != "echelles_x"}
                                                             for c in v]) for k, v in r.items()} for r in recs]
        out["bilan"] = bilan_joints(recs)
        try:
            out["joint_mm"] = wr.get_float_parameter_value("joint_mm")
        except Exception:  # noqa: BLE001
            pass
    return out


def parametre(nom, valeur):
    wr = ETAT.wrapper
    ETAT.traitements_avant = ETAT.traitements
    ok = regler(wr, {nom: valeur})
    journal(f"paramètre {nom} = {valeur} : {ok}")
    return {"accepte": ok, "traitements_avant": ETAT.traitements}


# ------------------------------------------------------------------------------------------------ PCG
def _ajouter_composant(act, classe, nom):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    racines = sds.k2_gather_subobject_data_for_instance(act)
    p = unreal.AddNewSubobjectParams(parent_handle=racines[0], new_class=classe, blueprint_context=None)
    h, raison = sds.add_new_subobject(p)
    if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(h):
        raise RuntimeError(f"composant {nom} : {raison}")
    sds.rename_subobject(h, unreal.Text(nom))
    d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)


def pcg(asset_path, graphe_path, label, points_cm, parametres):
    """Graphe PCG : Get Spline Data (acteur porteur : soi) -> « Houdini Digital Asset » (pj::bordure, sortie « Cook ») ;
    paramètres de l'HDA par des jeux d'attributs (un « Create Attribute Set » par paramètre, nom = paramètre de l'HDA)
    sur la broche Parameters. Acteur d'essai : spline UE (points linéaires) + composant PCG. Le câblage des broches de
    l'HDA attend son instanciation (étape pcg_cabler)."""
    ancien = acteur(label)
    if ancien is not None:
        ACTEURS.destroy_actor(ancien)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    dossier, nom = graphe_path.rsplit("/", 1)
    if unreal.EditorAssetLibrary.does_asset_exist(graphe_path):
        # graphe existant (peut-être référencé) : jamais de suppression ni d'écrasement (boîte modale), on le vide
        g = unreal.load_asset(graphe_path)
        for n in list(g.get_editor_property("nodes")):
            g.remove_node(n)
    else:
        g = at.create_asset(nom, dossier, unreal.PCGGraph, unreal.PCGGraphFactory())
    n_spl, s_spl = g.add_node_of_type(unreal.PCGGetSplineSettings)
    sel = s_spl.get_editor_property("actor_selector")
    sel.set_editor_property("actor_filter", unreal.PCGActorFilter.SELF)
    s_spl.set_editor_property("actor_selector", sel)
    n_hda, s_hda = g.add_node_of_type(unreal.HoudiniPCGSettings)
    s_hda.set_editor_property("output_type", unreal.HoudiniPCGOutputType.COOK)
    s_hda.set_editor_property("use_pcg_cache", False)
    s_hda.set_editor_property("houdini_asset", unreal.load_asset(asset_path))
    H = unreal.PCGAttributePropertySelectorBlueprintHelpers
    noeuds_par = []
    for k in sorted(parametres):
        v = parametres[k]
        n_a, s_a = g.add_node_of_type(unreal.PCGCreateAttributeSetSettings)
        ov = s_a.get_editor_property("attribute_types")
        if isinstance(v, (bool, int)):
            ov.set_editor_property("type", unreal.PCGMetadataTypes.INTEGER32)
            ov.set_editor_property("int32_value", int(v))
        elif isinstance(v, float):
            ov.set_editor_property("type", unreal.PCGMetadataTypes.DOUBLE)
            ov.set_editor_property("double_value", float(v))
        else:
            ov.set_editor_property("type", unreal.PCGMetadataTypes.STRING)
            ov.set_editor_property("string_value", str(v))
        s_a.set_editor_property("attribute_types", ov)
        cible = s_a.get_editor_property("output_target")
        r = H.set_attribute_name(cible, k)
        s_a.set_editor_property("output_target", r if isinstance(r, type(cible)) else cible)
        noeuds_par.append(n_a)
    ETAT.pcg_graphe, ETAT.pcg_noeuds = g, (n_spl, n_hda, noeuds_par)
    ETAT.pcg_acteur_args = (label, points_cm)
    ETAT.pcg_comp = None
    return {"graphe": g.get_path_name(), "noeuds_parametres": len(noeuds_par), "broches_hda": broches(n_hda)}


def broches(n):
    return [str(p.get_editor_property("properties").get_editor_property("label")) for p in n.get_editor_property("input_pins")]


def pcg_cabler():
    """Câble les broches de l'HDA (connues après l'instanciation du cookable de paramètres), enregistre le graphe, puis
    crée l'acteur d'essai (spline UE linéaire + composant PCG) et lance la génération."""
    g = ETAT.pcg_graphe
    n_spl, n_hda, noeuds_par = ETAT.pcg_noeuds
    b = broches(n_hda)
    entrees = [x for x in b if x not in ("Parameters", "Execution Dependency")]
    if not entrees:
        return {"pret": False, "broches_hda": b}
    g.add_edge(n_spl, "Out", n_hda, entrees[0])
    for n_a in noeuds_par:
        g.add_edge(n_a, "Out", n_hda, "Parameters")
    unreal.EditorAssetLibrary.save_loaded_asset(g)
    label, points_cm = ETAT.pcg_acteur_args
    ETAT.acteurs_avant = {a.get_path_name() for a in ACTEURS.get_all_level_actors()}
    act = ACTEURS.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
    act.set_actor_label(label)
    spl = _ajouter_composant(act, unreal.SplineComponent, "Spline")
    spl.set_spline_points([unreal.Vector(*p) for p in points_cm], unreal.SplineCoordinateSpace.WORLD, True)
    for i in range(len(points_cm)):
        spl.set_spline_point_type(i, unreal.SplinePointType.LINEAR, True)
    comp = _ajouter_composant(act, unreal.PCGComponent, "PCG")
    comp.set_graph(g)
    ETAT.pcg_comp, ETAT.pcg_acteur = comp, act
    comp.generate(True)
    return {"pret": True, "broches_hda": b, "entree_courbe": entrees[0], "acteur": act.get_name()}


def pcg_etat():
    comp = getattr(ETAT, "pcg_comp", None)
    if comp is None:
        return {"pcg": None}
    recs, acteurs = [], []
    for a in ACTEURS.get_all_level_actors():
        if a.get_path_name() in ETAT.acteurs_avant and a != ETAT.pcg_acteur:
            continue
        acteurs.append(a.get_actor_label())
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if c.get_editor_property("static_mesh") is not None:
                recs.append(inventaire_composant(c))
    return {"generation": bool(comp.get_editor_property("generated")), "acteurs": acteurs,
            "composants": [{k: v for k, v in r.items() if k != "echelles_x"} for r in recs],
            "bilan": bilan_joints([{"composants": recs}])}


def nettoyer(labels):
    """Retire les acteurs d'essai (labels) et les acteurs HoudiniPCGActor* laissés par un essai PCG (niveau d'essai)."""
    faits = []
    for a in ACTEURS.get_all_level_actors():
        lb = a.get_actor_label()
        if lb in labels or lb.startswith("HoudiniPCGActor"):
            ACTEURS.destroy_actor(a)
            faits.append(lb)
    return {"retires": sorted(faits)}


def parametres_lus():
    """Valeurs des paramètres lues dans l'instance (contrôle : réglages appliqués, défauts de l'HDA)."""
    wr = ETAT.wrapper
    out = {}
    for n in ("ue_abaisse", "sorties_unreal", "joints_aleatoires", "jitter"):
        out[n] = wr.get_bool_parameter_value(n)
    for n in ("joint_mm", "ue_vue", "ue_vue_abaisse", "ue_abaisse_debut", "ue_abaisse_fin", "ue_rampant", "coin_max_mm",
              "fleche_max_mm", "corde_mm", "jit_hauteur_mm"):
        out[n] = round(wr.get_float_parameter_value(n), 4)
    for n in ("sortie", "altitude"):
        out[n] = wr.get_int_parameter_value(n)
    for n in ("ue_id", "ue_profil", "ue_profil_abaisse"):
        out[n] = wr.get_string_parameter_value(n)
    return out


def session():
    """Relance la session Houdini Engine : après un réimport de l'HDA, une instance neuve a pu lire des valeurs de
    paramètres flottants incohérentes (0, inf) dans l'ancienne session (constaté le 11/10/2026)."""
    api = unreal.HoudiniPublicAPIBlueprintLib.get_api()
    api.restart_session()
    return {"session": bool(api.is_session_valid())}


E = ARGS.get("etape")
if E == "session":
    RESULT = session()
elif E == "parametres_lus":
    RESULT = parametres_lus()
elif E == "importer":
    RESULT = importer(ARGS["hda"], ARGS.get("dossier", "/Game/PJ/Houdini"))
elif E == "instancier":
    RESULT = instancier(ARGS["asset"], ARGS["label"], ARGS["points_cm"], ARGS.get("parametres", {}))
elif E == "etat":
    RESULT = etat()
elif E == "parametre":
    RESULT = parametre(ARGS["nom"], ARGS["valeur"])
elif E == "pcg":
    RESULT = pcg(ARGS["asset"], ARGS["graphe"], ARGS["label"], ARGS["points_cm"], ARGS.get("parametres", {}))
elif E == "pcg_cabler":
    RESULT = pcg_cabler()
elif E == "pcg_etat":
    RESULT = pcg_etat()
elif E == "nettoyer":
    RESULT = nettoyer(ARGS.get("labels", []))
else:
    RESULT = {"erreur": f"étape inconnue {E!r}"}
RESULT = json.loads(json.dumps(RESULT, default=str))
