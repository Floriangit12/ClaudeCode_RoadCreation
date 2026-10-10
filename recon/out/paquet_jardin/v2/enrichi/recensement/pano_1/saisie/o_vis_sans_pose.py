import sys
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg/enrichir"); sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/pcg")
sys.path.insert(0, "D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/v2/enrichi/recensement/pano_1")
import obs_outils as T
from obs_outils import obs, preuve as pv, pos, etat
import camera
def S(i): return "pnx:" + camera.photo(i).id
L = []
L.append(obs(S("e26b9309"), "2025-01-12T12:11", "haie", "haie_taillee_piste_vercors",
              dict(description="haie persistante taillée en mur (laurier-cerise / photinia, feuillage rouge en hiver) longeant le bord OUEST de la piste Chronovélo de l'avenue du Vercors, sans recul, h ≈ 2,0-2,5 m, ép. ≈ 1,0-1,5 m",
                   coupe_type_observee="haie | piste bidirectionnelle enrobé sombre ≈ 3 m (axe : tirets turquoise + points jaunes) | bordure peinte jaune | bande enherbée ≈ 1,5-2 m avec candélabres | chaussée",
                   position="photo sans pose calée : position GNSS ±4 m"),
              (22.0, -100.0, -1.6), 5.0, "rayon_sol", None, "absent_de_description", "moyenne",
              pv("e26b9309_v0_brut.jpg", bbox=[0, 300, 500, 900]),
              valide=("incertain", "avenue du Vercors réaménagée (trottoirs, végétalisation) de mars 2025 à début 2026 : haie probablement conservée mais non vérifiée")))
L.append(obs(S("b48e2561"), "2025-01-12T12:11", "bordure", "bordure_peinte_jaune_piste",
              dict(description="bordure basse béton peinte en JAUNE côté bande enherbée le long de la piste Chronovélo (identité Chronovélo), axe de piste en tirets turquoise et points jaunes, logos vélo blancs",
                   remarque="à rapprocher des constats vercors_s-31/32 ; matériau 'peint_jaune' à prévoir dans la bibliothèque de bordures"),
              (18.0, -70.0, 0.0), 5.0, "rayon_sol", None, "attribut_corrige", "moyenne",
              pv("b48e2561_v1_brut.jpg", bbox=[180, 340, 1020, 900]),
              valide=("incertain", "identité Chronovélo stable, mais Vercors réaménagé en 2025-2026")))
L.append(obs(S("a0a70830"), "2024-05-01T17:17", "mobilier", "arceaux_velos",
              dict(description="3 arceaux vélos en U inversé (acier galvanisé) sur le trottoir près de l'arrêt de bus de Verdun SO, poteau béton de ligne aérienne à côté, places deux-roues marquées en jaune sur la chaussée",
                   position="photo sans pose calée (±4 m)"),
              (-55.0, -40.0, 0.0), 5.0, "rayon_sol", None, "incertain", "faible",
              pv("a0a70830_v0_brut.jpg", bbox=[680, 560, 1000, 780]),
              valide=(False, "branche Verdun SO réaménagée en 2025 (quai NO avancé)")))
n = T.ajouter("vis_sans_pose", *L); print("ajoutées", n)
