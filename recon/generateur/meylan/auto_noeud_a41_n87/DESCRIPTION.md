# Nœud A41 / N87 — échangeur de Meylan et hélice de Meylan

*Lot B du relevé de Meylan, 17/10/2026. Site : l'A41 de x ≈ 917 940 à 919 113 (L93) et les 7 bretelles qui la
relient à la Rocade Sud N87 et à Meylan-Centre. Raccords : `auto_a41_section_courante` à l'ouest,
`auto_a41_echangeur_meylan_est` à l'est, `auto_n87_rocade_sud` au sud. État 2023-2025. Description de confiance
faible : la géométrie des bretelles est celle des axes OSM ; les largeurs sont mesurées sur l'ortho là où c'est
lisible.*

## 1. Description en texte libre

> Grand échangeur sur trois niveaux au milieu des champs. L'A41 (2 × 2 voies, terre-plein enherbé à deux glissières,
> BAU de 3,4 m, 110 km/h) passe sous un long pont à poutres en béton posé sur plusieurs files de piles — la poutre de
> rive est couverte de graffitis — qui porte la Rocade Sud. Celle-ci arrive du sud en remblai et se divise devant un
> musoir à chevrons : deux voies continuent vers Chambéry en longeant l'A41 au sud derrière une double glissière (elles
> la rejoindront 2 km plus loin), et une bretelle d'une voie fait une boucle serrée à 50 km/h pour rejoindre l'A41 vers
> Grenoble par une voie d'insertion juste avant le pont. Dans l'autre sens, l'A41 vers Grenoble se dédouble 200 m avant
> le pont de desserte : deux voies vers Grenoble-Centre, deux voies qui montent sur le pont vers Gières et le Domaine
> universitaire ; vers Chambéry, la sortie « Sisteron » quitte l'A41 par une longue courbe balisée (balises bleues et
> blanches) et redescend vers la Rocade Sud. Au nord, l'hélice de Meylan : une bretelle à 30 km/h qui tourne sur
> elle-même entre un muret en béton et un talus, passe sous son propre pont, puis s'élargit à deux voies avec flèches
> au sol jusqu'à un carrefour à feux de Meylan-Centre ; de ce carrefour repartent une bretelle vers l'A41 (La Tronche)
> et une vers la Rocade Sud. Bretelles de 4 m, rive gauche continue, rive droite en tirets longs, glissières des deux
> côtés ; borne orange d'appel d'urgence, panneau de sortie « n° 27 à 1 500 m » vers Grenoble ; pas d'éclairage.

## 2. Ordre de construction

1. Terrassements : remblais de la N87 et des bretelles hautes, talus de l'hélice.
2. Ouvrages, avant les chaussées qu'ils enjambent : pont de la N87 sur l'A41 (s ≈ 525), ponts des bretelles,
   passage de l'hélice sous elle-même (23 m), passage supérieur de desserte (s ≈ 1 007).
3. Chaussées : A41 2 + 2, branches à 2 voies, bretelles d'une voie, voies d'insertion.
4. TPC : herbe à deux glissières jusqu'à s ≈ 1 000, puis revêtu avec GBA (raccord à l'échangeur 26).
5. Retenue : glissières, doubles glissières entre chaussées parallèles, murets de l'hélice.
6. Marquages : lignes de l'A41 (u = 7,5 cm), T2 5u des insertions, T'3 3u des bretelles, chevrons des musoirs,
   flèches de l'hélice.
7. Signalisation : B14 70 et J14a à la divergence de la N87, J4 sur la courbe de la sortie Sisteron, D41a / D41c,
   CE2a, panneau du concessionnaire. 8. Abords : bois, champs, talus.

## 3. Tronçons décrits (`description.yaml`)

| Tronçon | Longueur | Profil | Provenance des largeurs |
|---|---|---|---|
| A41 deux sens (nœud) | 1 218 m | section courante, insertion 3,5 m (s 420-559, sens ←), TPC à GBA après s = 1 000 | coupes a41_noeud |
| N87 vers A41 Chambéry | 1 023 m | 2 voies 3,6 + BAU 2,5, 70 km/h | coupes b_n87_vers_chambery |
| N87 vers A41 Grenoble (boucle) | 808 m | 1 voie 4,0 [G], 50 km/h | analogie (ouvrages superposés illisibles) |
| A41 vers N87 sud | 1 054 m | 2 voies 3,6 + BAU 2,0, 70 km/h | coupe b_a41_vers_n87_sud s0158 |
| sortie Sisteron | 555 m | 1 voie 4,2, 70 km/h | coupes b_sisteron |
| hélice de Meylan | 337 m | 1 voie 4,6 puis 2 voies 3,7 / 3,5, murets, 30 km/h | coupes b_helice, photo 74dd6869 |
| Meylan vers A41 La Tronche | 527 m | 1 voie 3,8 | coupe b_meylan_vers_a41 |

## 4. Simplifications et incertitudes

- Les raccords (divergences, convergences, musoirs, superpositions d'ouvrages) ne sont pas encore exprimables dans le
  format : `extensions_auto.raccordements` et `ouvrages` (BESOINS B2, B5, B15). Le profil en long (trois niveaux)
  n'est pas décrit : aucun MNT n'a été utilisé.
- Polylignes OSM avec cassures de 7 à 30° dans les boucles (ajustement en arcs à faire, BESOINS B14).
- Le carrefour à feux en haut de l'hélice et la bretelle Meylan → Rocade Sud (134 m) ne sont pas décrits en détail.
- La photo de l'hélice date de mars 2023 (seule couverture) ; aucune photo du pont de desserte.
