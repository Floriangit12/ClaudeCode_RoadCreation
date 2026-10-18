# Besoins du générateur relevés sur `axe_verdun_ouest` (lot SITES, 18/10/2026)

*Écarts entre les photos et le rendu qui ne viennent pas de la description. Ces éléments sont impossibles à décrire
dans le format actuel ou mal fabriqués. Le code partagé n'a pas été modifié. Les identifiants de photos renvoient à
`recon/out/generateur/comparaison/meylan_axe_verdun_ouest/selection.json`, qui ne contient aucune image.*

| # | Élément | Photo, preuve | Règle, renvoi | Ce qui manque |
|---|---|---|---|---|
| V-O1 | **Traversée cyclable en damier jaune** sur toute la chaussée sud-ouest, à côté du passage piéton à feux, à k ≈ 406 (s ≈ 126 du tronçon 2) | a880f2d0, 61a21d0a (18/05/2025) | pratique locale Chronovélo (RF-OBS-CYC, synthèse DocRoute § 0.1) ; BESOINS_FORMAT A2, BESOINS_FORMAT_AUTO B8 | Aucun mot pour une traversée cyclable de section courante, ni pour un motif en damier. Elle reste dans `extensions_auto.traversees`. |
| V-O2 | **Passage à feux de section courante** : feux R11 et R12 et boutons d'appel, sans carrefour | OSM node/1958999093 (`crossing=traffic_signals`) ; barrières vues sur a880f2d0 | lot L6 (E14) | `passage_pieton` ne porte pas de régime « feux » hors carrefour. Le passage est fabriqué, mais sans feux ni ligne d'effet. |
| V-O3 | **Haie taillée continue** d'environ 1,2 m dans le terre-plein du tronçon 2, avec ses candélabres | 9f1498db, f86cca91, 1757d451, 97854886 | E15, E17 | Le principe « route seule » l'exclut du rendu, mais c'est l'élément qui change le plus l'aspect de l'avenue sur les photos. La haie est une limite de profil sans largeur : il faudrait une haie à hauteur et largeur, posée en E17 sans être rendue comme un arbre. |
| V-O4 | **Enrobé rapiécé et fissures pontées** | 9907ba31, f86cca91, 1757d451 | E10 (L-06 : aucune règle) | `materiaux.chaussee: enrobé rapiécé` donne un enrobé homogène au rendu. Il manque des décalques de pontages et de reprises. |
| V-O5 | **Pistes et trottoirs latéraux** à 15-20 m de l'axe, au-delà des bermes | OSM ; a880f2d0 | BESOINS_FORMAT_AUTO B4 | Ils sont hors du profil et restent dans `extensions_auto.pistes_laterales`. |

## Limites de l'outil de comparaison constatées sur ce site (outil partagé, non modifié)

- **Méta-catalogue indisponible.** Le 18/10/2026 vers 15 h, `api.panoramax.xyz` répondait 500 à toute requête. Le
  cache de recherche (`cache/recherche.json`) a été rempli par une recherche sur les instances OSM France et IGN, avec
  la même emprise et la même clé (`recon/generateur/tmp/lotB_sites/cache_recherche_instances.py`).
- **Photos d'une seule origine.** Les 6 photos viennent de 2 séquences de voiture qui roulent toutes vers le sud-ouest
  sur la chaussée nord-ouest. Il n'y a aucune vue depuis la chaussée sud-est.
- **Position GNSS hors chaussée.** Pour 61a21d0a, la position GNSS tombe sur la berme, environ 3 m hors de la
  chaussée. Le rendu est donc fait depuis la berme, ce qui rend la planche inutilisable pour les largeurs (CONTROLE.md,
  point 6).

## Complément de la comparaison v2 (18/10/2026, soir)

| # | Élément (zone) | Vue, preuve | Règle, renvoi | Ce qui manque |
|---|---|---|---|---|
| V-O6 | **Refuge à barrières** (croix de Saint-André) et **poteaux de feux** sur le refuge de la traversée de k ≈ 406 | `vue_1d9018fd_-034`, `vue_0af315d8_-085`, `planche_8c267a4e_-009` | lot L6 (E14, E16) | Mobilier du refuge non porté par le format (le refuge est un terre-plein ouvert au droit du passage). |
| V-O7 | **Traversée cyclable en damier posée en biais** sur la chaussée sud-est (longue bande jaune de x ≈ 190 au passage) | `planche_61a21d0a_-173` ; IGN 2024 `site_ign2024_t04` | V-O1 | Au-delà de V-O1 (damier) : une traversée oblique (≈ 30-40° avec l'axe) n'a pas de mot ; `passage_pieton` est perpendiculaire à l'axe. |
| V-O8 | **Rue latérale débouchant au droit de la traversée** (nord-ouest) | IGN 2024 `site_ign2024_t04`, `planche_dessus_site_ign_t06` | B4 ; FORMAT réseau § 7.1 | Un carrefour sur un axe à chaussées séparées n'est pas décrit dans ce site (il faudrait un carrefour plan avec ouverture du terre-plein) ; la rue reste hors modèle. |
| V-O9 | **Candélabres décoratifs (lanterne en filet) dans le terre-plein du tronçon 1** | `vue_225508c7_-167`, `planche_0394d4c2_-010` | V-O3, E15 | Équipements hors route seule. |
