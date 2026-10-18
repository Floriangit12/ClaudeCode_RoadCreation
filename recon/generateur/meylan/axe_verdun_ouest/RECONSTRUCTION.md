# Reconstruction de `axe_verdun_ouest` (étape 3, lot SITES autoroute et axes)

*18/10/2026. Avenue de Verdun côté La Tronche : tronçon 1 (k 30-225, 2 × 3 voies avec couloirs bus, TPC enherbé étroit)
et tronçon 2 (k 280-625, 2 × 2 voies, TPC bordé planté d'une haie). Aucune image dans ce fichier : planches sous
`recon/out/generateur/comparaison/meylan_axe_verdun_ouest/photos_non_versionnees/`.*

## État décrit

- **Date d'état** : 18/05/2025 (inchangée ; photos de la comparaison du 24/08/2024 et du 18/05/2025).
- **Fabrication** : `fabriquer_generateur.py meylan/axe_verdun_ouest/description.yaml --complet` (la glissière du
  tronçon 1 fait passer la scène par la chaîne autoroute ; 14 min).
- **Rendus seuls** : `recon/out/generateur/meylan_axe_verdun_ouest/rendus/` : `dessus.png` (84 m, tronçon 1),
  `conducteur_autoroute.png`, `oblique_34.png` (vue 3/4 sur la traversée de k ≈ 406).

## Itérations

| It. | Ce qui change | Pourquoi (preuve) |
|---|---|---|
| 0 | description du lot B harmonisée | — |
| 1 | **passage piéton** (à feux dans la réalité ; feux non portés hors carrefour, V-O2) à s ≈ 128 du tronçon 2 (k ≈ 406), **ouverture du terre-plein en refuge** de 2,6 m bordé (haie interrompue) et débouchés sur trottoir bordé, sur 6 m | it0 : a880f2d0 et 61a21d0a montraient la traversée (passage, refuge, barrières) absente du modèle ; OSM node/1958999093 (`crossing=traffic_signals`) et 1958999095, 1958999142 ; position ± 5 m |

## Ressemblance par photo (6 photos, 4 quadrants, 2 séquences de voiture vers le sud-ouest)

| Photo | Date | Vue | It. 0 | It. 1 | Constat |
|---|---|---|---|---|---|
| 9907ba31 | 18/05/2025 | tronçon 1, vers le TPC | bonne | bonne | 3 + 3 voies et TPC étroit bordé justes ; herbe sèche (photo) / verte (rendu) |
| a880f2d0 | 18/05/2025 | traversée de k ≈ 406 | faible | **moyenne** | passage et refuge présents depuis l'it. 1, ≈ 4 m trop près de la caméra ; damier jaune Chronovélo absent |
| f86cca91 | 18/05/2025 | tronçon 2, dans l'axe | moyenne | moyenne | profil juste ; haie taillée du TPC absente par principe (route seule) ; enrobé rapiécé |
| 1757d451 | 24/08/2024 | vers le TPC | moyenne | moyenne | bordure du TPC à sa place ; la haie masque tout sur la photo |
| 97854886 | 24/08/2024 | vers l'est | moyenne | moyenne | idem, candélabres dans la haie |
| 61a21d0a | 18/05/2025 | traversée, depuis la voie | non jugeable | non jugeable | rendu depuis la berme (GNSS ≈ 3 m hors chaussée) ; le passage du modèle tombe à la même distance que sur la photo |

Mesures de l'outil (médianes initiale → retenue) : recouvrement des contours à 3 px 0,10 → 0,21 (it. 0) puis
0,09 → 0,28 (it. 1) ; écart moyen 22,6 → 16,5 px puis 22,5 → 14,0 px ; poses affinées 5 puis 6 sur 6.

## Écarts restants (BESOINS.md)

- Traversée cyclable en **damier jaune** (V-O1), feux et barrières du passage (V-O2), **haie taillée** du TPC et
  candélabres (V-O3), enrobé rapiécé et pontages (V-O4), pistes et trottoirs latéraux à 15-20 m (V-O5).
- Photos d'une seule origine (deux séquences vers le sud-ouest) : la chaussée sud-est n'est jugée que de loin.

## Comparaison v2 (18/10/2026, soir) : dossier de compréhension, 13 photos / 50 vues

Remarque de l'utilisateur appliquée : plus de vues, et c'est le modèle qui comprend la scène en regardant lui-même les
images (orthos de plusieurs dates + photos sous toutes les directions) : `COMPREHENSION.md`.

```
python recon/generateur/comparaison/comparer_multivues.py meylan_axe_verdun_ouest --v2 --sites-conf recon/generateur/meylan/axe_verdun_ouest/comparaison_site.json --sortie recon/out/generateur/meylan_axe_verdun_ouest/comparaison --depuis 2024-05-01 --jusqu-au 2025-06-22
```

| | v1 (itération 1 du lot B) | v2 |
|---|---|---|
| Photos / vues | 6 / 6 (2 séquences, une seule origine) | 13 / 50 (4 séquences : voiture 24/08/2024 et 18/05/2025, vélo 01/05/2024) |
| Directions d'observation | 4 quadrants, chaussée sud-est vue de loin | les deux chaussées, les deux sens ; traversée de k ≈ 406 vue sous 4 directions (dont depuis le trottoir) |
| Zones aveugles | — | aucune (cases de 20 m + 2 passages) |
| Orthos | IGN 2024 | IGN 2024, 2021, 2018, 2015, IRC 2024, Pléiades 2025, Plan IGN |
| Recouvrement 3 px (médiane, initial → retenu) | 0,09 → 0,28 | 0,14 → 0,30 |

Grille d'écarts : `recon/out/generateur/meylan_axe_verdun_ouest/comparaison/meylan_axe_verdun_ouest/ecarts.json`
(6 vues commentées, les autres vues des mêmes photos confirment).

**Ressemblance (v2) : moyenne à bonne.** Profils des deux tronçons justes (nombre de voies, couloirs bus, terre-pleins
bordés, rives) ; passage et refuge de la traversée de k ≈ 406 à ≈ 4 m de leur place. Écarts restants, tous hors de ce
que la description peut dire : damier Chronovélo **en biais** (V-O1, V-O7), feux et barrières du refuge (V-O2, V-O6),
rue latérale au droit de la traversée (V-O8), haie taillée et candélabres (V-O3, V-O9), enrobé rapiécé (V-O4), flèches
directionnelles du tronçon 1 (vues sur une seule photo, non ajoutées).

**Itération** : aucune nouvelle itération de description (rien de faux dans ce qui est descriptible) ; les rendus seuls de
l'itération 1 (`recon/out/generateur/meylan_axe_verdun_ouest/rendus/dessus.png`, `oblique_34.png`) restent valables.
