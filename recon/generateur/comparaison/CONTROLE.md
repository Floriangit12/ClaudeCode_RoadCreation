# Contrôle indépendant de l'outil de comparaison multivues

*`recon/generateur/comparaison/`. Contrôle du 18/10/2026, fait par un agent qui n'a pas écrit l'outil.*

## En bref

- L'outil tourne, il est **déterministe**, et ses **rendus sont bien cadrés**, au même champ et à la même pose que les
  vues photo. Le soleil suit la date et l'heure de chaque photo. Aucune photo n'est rangée hors de
  `photos_non_versionnees/`, et les grilles d'écarts remplies sont conservées à chaque relance.
- **Trois bogues sont corrigés**, dont deux touchent la pose :
  1. la solution finale remplaçait souvent la solution validée ;
  2. la marge de la pose complète était contournée ;
  3. le diagnostic de site était faux.
  Après correction, **17 poses sur 35 sont retenues (49 %)**, contre 19 sur 35 annoncées (54 %).
- **À l'œil, 7 de ces 17 poses seulement sont plausibles.** Les autres reposent sur une validation trop indulgente :
  - la pose complète absorbe les largeurs de la description ;
  - sur les tronçons courbes, la caméra est rendue dans la mauvaise bande ;
  - certaines vues ne montrent pas le modèle.
- La sélection couvre bien plusieurs positions le long du tronçon. En revanche, la couverture « 4 quadrants » repose
  en partie sur un classement **arbitraire des vues diagonales**. C'est un bogue que je n'ai pas corrigé, parce que sa
  correction change la sélection. Le détail est plus bas.
- Les grilles sont remplies et justes sur la description. Il y manque surtout les cas où **le rendu n'est pas pris
  du même endroit que la photo**, ce qui rend la planche inutilisable pour juger les largeurs.

## Ce qui a été fait

1. J'ai relu tout le code : `comparer_multivues`, `geo`, `api_panoramax`, `modele`, `vues`, `selection`, `pose`,
   `rendu_hython`, `planches`, `sites_meylan.json` et le README. J'ai aussi relu `decoupe.vue_equirect`, ainsi que
   `rendu/ciel.py` et `scene_rendu.usda` pour les conventions.
2. **Relance de l'outil inchangé sur S_M24** (toutes les étapes) : 272 s. `selection.json` et `poses.json` sont
   identiques, durées exceptées, à ceux du passage déclaré, et les grilles sont conservées.
3. Correction des bogues, puis **relance des trois sites** pour que les sorties correspondent au code : M24 249 s,
   M27 279 s, M20 270 s. J'ai ensuite relancé les étapes `selection,pose` sur S_M27 : les résultats sont identiques,
   donc le code corrigé reste déterministe.
4. J'ai regardé en tuiles natives :
   - les 11 planches de M24, la synthèse et le plan du site ;
   - les synthèses de M20 et de M27 ;
   - les planches de toutes les poses retenues ou modifiées par la correction ;
   - les vues natives de 1092 px quand le détail comptait.
5. Contrôles automatiques indépendants (scripts dans `recon/out/generateur/comparaison/_controle/`) :
   - **cadrage** des rendus (`verif_cadrage.py`) ;
   - **verticales** des photos contre les caméras retenues (`verif_verticales.py`) ;
   - **effet d'un classement robuste des quadrants** sur la sélection (`essai_quadrant.py`, sans écriture dans les
     sorties).

   Les JSON d'avant la relance sont sauvegardés dans `_controle/avant_relance/`.

## Vérifications passées

| Point | Résultat |
|---|---|
| Déterminisme | Identique sur S_M24 avant correction et sur S_M27 après correction (`selection.json`, `poses.json`, durées exceptées). |
| Cadrage des rendus | Les matrices USD des caméras redonnent exactement les projections Python (écart < 0,1 px sur des points témoins). Sur S_M27, les arêtes projetées tombent à 0 ou 1 px des contours du rendu (médiane), contre 2 à 5 px si l'on décale le lacet de 2°. |
| Taille des rendus | 35 rendus sur 35 ont exactement la taille de leur vue : 1092 × 1092 px, ou 1092 × 491 px pour la photo à plat 89fde77c. |
| Soleil | Convention d'azimut identique à `ciel.py` et à la DistantLight de `rendu_l2b`. Hauteur et azimut sont calculés depuis la date UTC. Sur b27ea343 (M27), l'ombre portée du lampadaire va bien dans le sens du soleil calculé (OSO, 33°). |
| Redressement des photos 360° (casque, M24) | Les verticales mesurées indépendamment confirment la correction. Résidu médian (métadonnées → pose retenue) : 6db5081f − 8,1° → + 0,2° ; ebf03c20 − 8,0° → − 0,7° ; f877235a + 5,1° → + 1,1° ; 9badc00e − 4,3° → − 1,7°. |
| Photos de tiers | Aucune image hors de `photos_non_versionnees/` (recherche récursive). `rendus/`, `plan_site.png`, `cache/` et `_controle/cadrage/` ne contiennent aucune photo. Le dossier versionné ne contient que du code, du JSON et du Markdown, avec seulement des identifiants, dates, positions et caps. `recon/out/*` est ignoré par git. |
| Scène de rendu | Les empreintes sha256 de `scene_rendu.usda` sont égales à celles de `rapport.json`. Ses sous-couches `l2/route_l2.usda` et `l2b/route_l2b.usda` sont égales à celles du manifeste de rendu, sur les trois sites. |
| Grilles | 35 grilles sur 35 sont remplies (rubriques et synthèse) et conservées à l'identique par les relances. |
| Écritures sur C: | Pendant les relances, aucun fichier Houdini ou Karma n'a été écrit dans `Documents\houdini22.0`, `AppData` ou `%TEMP%`. |

## Bogues corrigés

### 1. La solution finale n'était pas la solution validée (`pose.py`, `Alignement.affiner`)

**Bogue.** Après la validation sur la moitié B des segments, la solution était « affinée sur tous les segments »
par `_optimiser("tout")`. Cette fonction relance la **recherche globale** : grille de départs et quatre meilleurs
nœuds. Elle retenait donc souvent un **autre minimum**, jamais validé. La boucle de stabilité pouvait, elle aussi,
remplacer la solution par un minimum lointain.

**Ampleur.** Sur 18 poses affinées, 12 étaient hors du bassin de la solution validée (plus de 1 m ou plus de 1,5°).
Exemples :

| Photo | Lacet validé | Lacet final retenu |
|---|---|---|
| S_M20 053922ee | − 2,4° | + 4,4° |
| S_M20 b098d25a | + 5,4° | − 2,8° |

Autres cas, avec l'écart de la solution finale à la solution validée :

| Site | Photo | Écart |
|---|---|---|
| S_M20 | ef372e02 | 5,3° |
| S_M20 | b52c062b | 5,5° |
| S_M20 | 8482f1bc | 4,0° |
| S_M24 | f9242c7f | 2,7° |
| S_M24 | ebf03c20 | 3,0° |
| S_M24 | 9badc00e | 1,8° |
| S_M24 | 93ccf5e5 | 1,1 m et 3,3° |
| S_M24 | 06f383bd | 4,4° |
| S_M27 | 1977f0a0 | 4,5° |
| S_M27 | b27ea343 | 4,3° |

**Correction.** L'affinage est désormais **local** : Powell depuis la solution validée, à 20 puis 10 px. La solution
finale n'est gardée que si elle reste à moins de 1 m et 1,5° de la solution validée (`proche`, mêmes tolérances
que la stabilité). Sinon, c'est la solution validée qui est retenue. La boucle de stabilité ne remplace plus la
solution que dans ce même bassin. L'écart final est écrit dans
`validation.ecart_solution_finale_a_la_validee`.

### 2. La marge de la pose complète était contournée (`pose.py`, choix du niveau)

**Bogue.** Le README annonce que la pose complète doit valider mieux que l'orientation seule de 0,05. Or le code
ne comparait la pose complète qu'au niveau déjà retenu. Quand l'orientation seule n'avait pas franchi le seuil de
0,03, la pose complète passait avec n'importe quel gain au-dessus de 0,03, ce qui revenait à déplacer la caméra
pour un gain de validation d'environ 0,01 :

| Site | Photo | Orientation | Complète |
|---|---|---|---|
| S_M24 | 93ccf5e5 | + 0,024 | + 0,037 |
| S_M27 | 47898337 | + 0,025 | + 0,064 |

**Correction.** La pose complète est maintenant comparée à l'orientation seule dans tous les cas. Les deux poses
reviennent aux métadonnées. Le docstring est corrigé : il annonçait encore + 0,02.

### 3. Le diagnostic du site était biaisé (`comparer_multivues.py`, `correction_mediane_du_site`)

**Bogue.** La médiane de ds et dt mélangeait les poses « orientation seule », pour lesquelles ds = dt = 0 par
construction. Elle était donc tirée vers 0 : M24 affichait ds = dt = 0.

**Correction.** ds et dt sont calculés sur les seules poses complètes, et l'effectif est donné
(`n_poses_completes`). Résultat : M24 dt = − 2,0 m (une pose) ; M27 dt = − 2,2 m (deux poses). Ce chiffre
**montre** le biais décrit au point 2 de la liste « Problèmes non corrigés ».

### Effet sur les résultats

| Site | Poses retenues : avant → après | Recouvrement 3 px médian : avant → après | Écart moyen médian : avant → après |
|---|---|---|---|
| S_M20 | 5/12 → 5/12 (orientations différentes) | 0,05 → 0,09 / 0,05 → 0,09 | 25,3 → 21,5 / 25,3 → 22,3 px |
| S_M24 | 7/11 → 6/11 | 0,14 → 0,31 / 0,14 → 0,25 | 20,5 → 12,6 / 20,5 → 14,1 px |
| S_M27 | 7/12 → 6/12 | 0,14 → 0,24 / 0,14 → 0,19 | 17,8 → 13,7 / 17,8 → 14,5 px |

Le recouvrement « après » baisse. C'est attendu : on garde la solution validée, au lieu de la meilleure solution
ajustée sur tous les segments, validation comprise. Les rendus, planches, `rapport.json` et `bilan.json` des trois
sites correspondent maintenant au code corrigé. Le README est mis à jour.

Dans `ecarts.json`, seul le suffixe `[pose : …]` ajouté aux synthèses par le script de remplissage a été remis au
statut actuel, pour 93ccf5e5 (M24) et 47898337 (M27). Le texte de l'agent n'est pas touché par ailleurs (script
`_controle/maj_suffixe_pose.py`).

## Plausibilité des 17 poses retenues, à l'œil sur les planches

| Site | Photo | Niveau | Verdict |
|---|---|---|---|
| M24 | f877235a | orientation (sur redressement 19,6°) | **Plausible** : bandes du passage alignées, inclinaison de la caméra au casque reproduite. |
| M24 | 6db5081f | redressement seul | **Plausible** : verticales confirmées. |
| M24 | ebf03c20 | orientation (sur redressement) | **Plausible** pour l'orientation. Le profil réel diffère à s ≈ 15 m, ce que la grille note. |
| M24 | f9242c7f | orientation (photo à plat) | **Plausible au centre.** Les bords sont faux : distorsion de l'objectif grand-angle, et caméra sur le toit du véhicule (≈ 2 m) et non derrière le pare-brise (1,35 m supposé). |
| M24 | 9badc00e | complète | **Fausse en position.** Orientation bonne, mais la caméra est déplacée de 2 m vers l'extérieur (t ≈ − 9,4 m, sur la piste). La photo est prise sur le trottoir, contre les dalles podotactiles (t ≈ − 5 m). Le rendu montre le passage loin derrière un large trottoir. |
| M24 | 06f383bd | orientation | **Hors sujet.** La photo est prise sur la piste. La position GNSS projetée sur l'axe droit du modèle tombe sur la chaussée (t = − 1,3 m), à cause de l'avenue courbe, et le rendu est fait depuis le milieu de la route. |
| M27 | 7ab5b751 | orientation | **Plausible** : très ressemblant. |
| M27 | 1977f0a0 | orientation | **Plausible.** |
| M27 | 18e1dc39 | orientation | **Faible portée** : vue depuis une rue transversale, hors du modèle, qui n'apparaît que comme une bande au loin. |
| M27 | b27ea343 | orientation | **Douteuse.** Voiture à t = 7,3 m, à 3,2 m de la chaussée du modèle : elle est sans doute dans le débouché de la rue transversale, non décrite, et le rendu la place sur le trottoir gauche du modèle. |
| M27 | 938c8e8c | complète | **Fausse** : caméra éloignée de 2,7 m de la chaussée, déjà signalé. |
| M27 | c9458d1d | complète | **Douteuse** : caméra éloignée de 1,7 m. Le rendu est fait depuis la bande plantée, alors que la photo est prise sur la piste. |
| M20 | 053922ee | orientation | **Hors sujet** : la vue montre l'anneau du giratoire, hors du modèle. Les arêtes droites du modèle sont recalées sur la rive courbe du giratoire. |
| M20 | b098d25a | orientation | **Hors sujet** : même cas que 06f383bd. La photo est prise sur la piste, le rendu depuis la chaussée, car la rue est courbe au-delà de 50 m. |
| M20 | ef372e02 | orientation | **Peu probante.** Le modèle a un chemin clair de 1,8 m là où le réel a une piste de 3 m. Le roulis de la caméra (≈ 9°) n'est pas corrigé, voir le point 5 plus bas. |
| M20 | 8482f1bc | orientation | **Plausible**, petite correction. Roulis non corrigé. |
| M20 | b52c062b | orientation | **Faible portée** : vue depuis une piste latérale hors du modèle. Le bord du socle du modèle apparaît comme un mur blanc au premier plan. |

Bilan : environ 7 poses plausibles, 3 douteuses ou de faible portée, et 7 fausses ou hors sujet. L'indice de
confiance ne les distingue pas : 9badc00e et 938c8e8c sont classées « haute », 06f383bd et b098d25a « moyenne ».

## Sélection : angles et positions

- **Positions le long du tronçon : bien couvertes.**
  - M20 : de 0 à 101 m ;
  - M27 : de 6 à 100 m ;
  - M24 : de − 4 à 78 m, mais avec un trou de 53 à 78 m. 4 photos sur 11 viennent de la même séquence voiture
    (95751767), au carrefour de départ (s entre − 4 et 6 m). Elles montrent surtout ce carrefour. La pénalité de
    proximité (6 et 12 m) ne les a pas séparées.
- **Positions en travers.** Chaussée, trottoir, piste et accotement sont représentés.
  - « Hors modèle » rapporte une prime de diversité. Or une photo prise hors du modèle le voit mal : 7057c99c,
    b52c062b, 18e1dc39 ou 242ef8d4, une vue en sous-bois inexploitable.
  - Sur les tronçons courbes, la classe de position est fausse loin de l'ancrage : 06f383bd et b098d25a sont
    classées « chaussée » alors qu'elles sont prises sur la piste.
- **Directions de visée : bogue non corrigé.**
  - **15 vues sur 35 sont des diagonales exactes** (± 45°, ± 135°). Les 8 directions candidates sont à k × 45° de
    l'axe, et `quadrant()` les classe selon le signe de l'arrondi.
  - Preuve : une même valeur de lacet, 45,0°, est classée « +x » pour f877235a, ebf03c20 et 93ccf5e5, mais
    « gauche » pour 053922ee, 2682d709 et c9458d1d. De même, 135,0° donne « gauche » (6db5081f, 9badc00e) ou « −x »
    (8482f1bc, 938c8e8c, 47898337).
  - Les quadrants « gauche » et « droite » de M20 et M24 ne sont couverts que par des diagonales. Le seul vrai
    lateral des trois sites (18e1dc39, − 90°) est pris hors du modèle.
  - Un classement robuste à l'arrondi change la sélection de M20 (b52c062b est remplacée par 806766d4) et les vues
    de M24 (`_controle/essai_quadrant.py`). Une correction ferait donc perdre des grilles remplies. Elle demande
    aussi un choix de conception : directions candidates décalées de 22,5°, ou une diagonale qui compte pour ses deux
    quadrants. C'est pourquoi je ne l'ai pas faite.

## Rendus

- Le cadrage et le soleil sont justes (voir « Vérifications passées »).
- Le ciel est toujours clair, avec un soleil franc. Les photos du 01/05/2024 (barnes38) sont prises par temps
  couvert, ce qui fausse la comparaison des contrastes et des ombres.
- Pour ces séquences, `datetimetz` vaut « +00:00 », alors qu'il vaut « +01:00 » ou « +02:00 » pour les autres
  contributeurs. Si l'heure était en fait l'heure locale, le soleil réel serait à 46° et non à 26°. C'est
  invérifiable ici : il n'y a pas d'ombre sur ces photos.
- Photos à plat de la séquence edcc523a (M24) :
  - elles sont prises par une caméra grand-angle à forte distorsion, que le modèle sténopé ignore ;
  - la caméra est fixée sur le toit, alors que la table des porteurs suppose un « téléphone derrière le pare-brise »
    à 1,35 m.
- Vue depuis l'extérieur du modèle, la jupe du socle apparaît comme un mur blanc au premier plan (b52c062b).
- Dans le panneau de superposition, la texture du gazon rendu produit beaucoup de faux contours magenta : c'est du
  bruit à ne pas lire.

## Grilles d'écarts : ce qui manque

Les écarts de description relevés sont justes et recoupent les planches. Il manque surtout des réserves sur la
**validité de la planche** elle-même :

| Site | Photo | Ce qui manque |
|---|---|---|
| M24 | 9badc00e | Tout est noté « conforme », mais le rendu est fait 4 m plus loin de la bordure que la photo (piste contre trottoir, au droit des dalles podotactiles). Les largeurs et la position du passage ne peuvent pas être jugées sur cette planche. |
| M24 | 93ccf5e5 | La grille dit « depuis la piste ». La photo est en fait prise depuis une voiture sur la chaussée du carrefour, et le rendu depuis la piste. Le constat « accotement enherbé entre bordure et piste » n'est pas lisible sur cette vue. |
| M24 | 06f383bd ; M20 b098d25a | Rendus faits depuis la chaussée pour des photos prises sur la piste. La cause est la courbure de la voie, avec le tronçon modélisé droit. Le constat de profil reste juste, mais la planche ne permet pas de le lire. |
| M24 | 6c65b991 | À s ≈ 25 m, la photo regarde le long de la route, mais son cap fait environ 26° avec l'axe du modèle. À s ≈ 53 m, sur f9242c7f (même véhicule), cet écart n'est que de 3°. Cela vient de la courbure de l'avenue, ce qui n'est pas noté. |
| M27 | 938c8e8c, c9458d1d, f0c59ee0, 47898337 | Ces photos sont prises sur la piste, mais rendues depuis la bande plantée : t = − 10,2 m d'après le GNSS, et jusqu'à − 12,9 m après la pose complète. C'est cohérent avec l'accotement réel d'environ 3 à 4 m (2 m décrits), que la grille note bien. Mais la grille ne dit pas que le point de vue diffère. |
| M20 | 053922ee | Affinage « validé » sur une vue du giratoire, où le modèle n'est pas visible. La pose ne vaut rien ; ce n'est pas noté. |
| M20 | ef372e02 et la séquence 4ef310d0 | Caméra portée inclinée d'environ 9°, non redressée. Le rendu est de niveau, la photo penchée. Ce n'est pas noté. |
| M27 | 89fde77c | Voiture placée sur la berme (t = − 5,6 m). La photo ne montre pas le passage que le rendu met juste devant : la position GNSS est aussi fausse le long de la voie. C'est en partie noté. |

## Problèmes non corrigés, par priorité

1. **La validation n'est pas indépendante.** Les deux moitiés A et B sont les rangs pairs et impairs de la liste des
   segments LSD. Une même bordure ou rive, découpée en plusieurs segments, se retrouve dans les deux moitiés. Une
   pose fausse qui aligne les longues lignes lointaines « valide » donc aussi : 938c8e8c gagne + 0,22, 9badc00e
   + 0,13. Il faudrait partager les segments par zone d'image (gauche et droite, ou près et loin) ou par ligne
   physique.
2. **La pose complète absorbe les écarts de la description.** Les trois poses complètes restantes éloignent toutes
   la caméra de la chaussée, de 1,7 à 2,7 m. Le dt médian du site vaut − 2,0 m sur M24 et − 2,2 m sur M27.
   - Sur M27, cela compense l'accotement réel, plus large que décrit (≈ 3 à 4 m pour 2 m).
   - Sur M24 9badc00e, la cause n'est pas établie : position du passage, hauteur ou tangage de la caméra au casque.
     La caméra s'éloigne pourtant de sa vraie place, contre la bordure.

   C'est exactement ce que l'outil veut éviter. Je suggère de supprimer ce niveau pour la comparaison, ou de ne
   l'accepter que si la position retenue reste dans la même bande du profil que la position GNSS.
3. **Tronçons courbes et ancrage.** La position GNSS est projetée sur l'axe droit du modèle : au-delà de 30 à 40 m
   de l'ancrage, elle tombe dans une autre bande (M24 06f383bd, M20 b098d25a), et le cap s'écarte de 20 à 26°
   (M24 6c65b991). Il vaudrait mieux passer en abscisse curviligne : projeter la photo sur la polyligne OSM de la
   voie pour obtenir (s, t), et prendre le cap relatif à la tangente locale. On peut aussi limiter la sélection à la
   partie du tronçon proche de l'ancrage.
4. **Quadrants des vues diagonales** : voir la partie Sélection.
5. **Le redressement est bloqué pour les caméras portées.** La règle de cohérence de séquence (vote à 4°) et le
   minimum de 30 segments l'empêchent sur les séquences au sac à dos (4ef310d0, 69791f81). Pourtant, l'inclinaison y
   est réelle : environ 9° sur ef372e02 et environ 6° sur c9458d1d, d'après les verticales. Sur un vélo ou un piéton,
   la caméra bouge entre deux photos, et « même support, même verticale » n'y vaut pas. À l'inverse, la séquence
   voiture 95751767 est redressée de 3 à 7° sur quatre photos (M20 5ca8e01d ; M24 7057c99c, 5cb86ef9, 93ccf5e5), sans
   gain à la validation. La déclaration du workflow, qui limite le redressement à M24 au casque, est donc inexacte.
6. **Une voiture peut être rendue hors de la chaussée.** La contrainte « une voiture reste sur la chaussée »
   n'agit que dans le coût de l'affinage. Quand l'affinage est rejeté, c'est-à-dire le plus souvent, la voiture est
   rendue depuis sa position GNSS, même à moins de 3 m de la chaussée : 89fde77c sur la berme (1,5 m), 51a35517 sur
   le trottoir (1,6 m). Au-delà de 3 m, elle peut se trouver légitimement dans un carrefour non modélisé (93ccf5e5 à
   4,9 m, b27ea343 à 3,2 m). Pour une voiture à moins de 3 m, ramener la pose de départ sur la voie la plus proche
   serait physiquement justifié.
7. **Photos à plat** : distorsion non modélisée, et porteur ou hauteur non distingués (toit ou pare-brise).
8. **Fichiers périmés non nettoyés.** Planches, tuiles, vues et rendus des photos qui ne sont plus sélectionnées
   restent dans les dossiers : 12 identifiants sur M20, 3 sur M24 et 6 sur M27. Ils peuvent tromper un lecteur.
   Je ne les ai pas supprimés.
9. **Empreintes de la scène.** `rapport.json` n'enregistre que l'empreinte de `scene_rendu.usda`. Les sous-couches
   `l2/route_l2.usda` et `l2b/route_l2b.usda`, que d'autres workflows régénèrent, ne sont ni enregistrées ni
   comparées au manifeste de rendu. Elles étaient identiques ce jour.
10. **Panneau « arêtes » des planches.** Les segments cyan y sont filtrés à l'horizon avec la caméra des
    métadonnées, et non avec la caméra redressée qu'utilise l'affinage. L'affichage diffère donc légèrement des
    segments réellement utilisés sur les photos redressées.
11. **Détails.**
    - Les couches `rendus/vue_<id8>.usda` renvoient à des ciels EXR supprimés après le rendu : on ne peut pas les
      rejouer seules.
    - Le commentaire de `gabarit_ecarts` parle du rayon du pixel (W/2 ; 0,7 H), alors que le code prend 15 m
      devant.
    - `Modele.profil` ignore le 4e et le 5e sommet des faces de plus de trois sommets.
    - Les ciels ne sont pas nettoyés si hython échoue.

## Fichiers

- Code modifié :
  - `recon/generateur/comparaison/pose.py` : affinage local, `proche`, marge de la pose complète, docstrings ;
  - `recon/generateur/comparaison/comparer_multivues.py` : diagnostic de site ;
  - `recon/generateur/comparaison/README.md` : résultats et limites.
- Contrôle (non versionné) : `recon/out/generateur/comparaison/_controle/`
  - journaux : `relance_S_M24.log`, `relance_corrigee.log`, `determinisme_M27.log` ;
  - sauvegarde `avant_relance/` ;
  - scripts : `verif_verticales.py`, `verif_cadrage.py` (+ `cadrage/`, des rendus seuls), `essai_quadrant.py`,
    `maj_suffixe_pose.py` ;
  - grilles en texte lisible : `ecarts_*_lisible.txt`, état d'avant la relance.
