# Rues réelles de Meylan décrites d'après photo (boucle photo → description → fabrication)

*`recon/generateur/scenes_meylan/` — correction après contrôle de l'étape 1, 17/10/2026.*

La boucle voulue par l'utilisateur : **regarder une photo de Meylan, écrire une description simple, laisser le
générateur la fabriquer**. Chaque fichier décrit une section droite de rue, sans carrefour, au format
`description/FORMAT_DESCRIPTION.md`, en regardant les tuiles natives (1092 px) des photos Panoramax du dossier 13
(`D:\DocRoute\13_Observations_Panoramax_Isere\photos_tiers_locales\photos_non_versionnees\<site>\`, jamais versionnées
ni diffusées). Le commentaire d'en-tête dit ce qui est vu sur quelle tuile, et ce qui est simplifié.

| Fichier | Rue | Photos (date) | Ce qui est décrit |
|---|---|---|---|
| `M24_avenue_du_granier.yaml` | avenue du Granier (Inovallée) | 9badc00e, f877235a (12/01/2025, hiver) | 2 × 1 voies, zone hachurée devenant îlot refuge bordé bas au passage piéton, trottoirs béton balayé, piste bidirectionnelle au niveau du trottoir, bande enherbée plantée ; écarts admis : refuge 1,80 m, bordure 0,10 m |
| `M27_avenue_de_verdun.yaml` | avenue de Verdun (centre) | 176f9ab0, 7ab5b751 (18/05/2025) | 2 × 1 voies, îlot peint hachuré et refuge bordé de 10 m au passage, accotements enherbés coupés au droit du passage par des liaisons revêtues au niveau de la chaussée (bandes du passage prolongées dessus, comme sur les photos), chemin au-delà de la piste, piste en enrobé, grands arbres, flèche « tout droit » ; écarts admis : bordure du refuge 0,11 m, débouchés de plain-pied sans BEV (RF-MA-BEV-001, photos sans BEV) |
| `M20_avenue_de_chamechaude.yaml` | avenue de Chamechaude | 30b80a7b (28/07/2026, été) | rue 1 + 1 de 6 m sans axe entre bordures basses, accotements enherbés, chemin piéton, bouleaux et chênes (essences de `assets/specs/vegetation.json`), passage piéton avec C20a relié de chaque côté par une traversée revêtue (chemin vers l'immeuble à gauche, liaison jusqu'au chemin piéton à droite), abaissés et BEV contre la chaussée |

```
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_meylan/M24_avenue_du_granier.yaml --l2b --rendus
python recon/generateur/rendu/planches_photo.py S_M24        # planches rendu | photo (photos_non_versionnees/planches)
```

Les vues `photo_<id>` du rendu (rendu/rendu_l2b.py, `VUES_PHOTO`) ont le champ (68,25°) et le tangage (− 12°) de la
vue « vise » de la photo ; la position de la caméra est estimée sur la photo (rue simplifiée : ce sont des cas
semblables, pas des vues recalées).

Correction après le second contrôle de l'étape 1 : un passage doit aboutir de chaque côté sur une surface piétonne par
des bandes revêtues (le compilateur refuse sinon) ; M20 et M27 décrivent désormais la traversée revêtue des accotements
au droit du passage (évènements `profil`), regardée sur les zooms natifs des photos (M27 : liaisons revêtues visibles).
