# Carrefour à feux avenue de Verdun × avenue de Chamrousse × chemin de Chaumetière

*Relevé Meylan, lot A, 17/10/2026. Site M08 du dossier `D:\DocRoute\13_Observations_Panoramax_Isere` (« carrefour à feux
av. de Verdun, près du rond-point du Lycée »). Point du site : 45,213561 N, 5,777548 E ; Lambert-93 (917 989,78 ;
6 460 971,81) ; z ≈ 249,2 m (RGE ALTI). Le rond-point du Lycée (`../rp_lycee/`) est à ≈ 190 m au nord-est.*

**État décrit : 28/07/2026** (campagne IGN, photos planes 92° de 10:59), le plus récent.

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** ; Verdun sud-ouest finit sur `N_VERDUN_M08_SO` (médiane OSM, 2 m du bout d'avant) : l'axe de `axe_verdun_centre` y finit (recouvrement de 35,7 m supprimé) ; le profil de ce site est le contrat du joint. Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

## 1. Description simple

> Carrefour à feux en croix sur l'avenue de Verdun, qui a ici deux chaussées séparées par des îlots plantés. Depuis le
> nord-est arrivent 3 voies d'environ 3,6 m (tourner à gauche, tout droit, tout droit et à droite) ; une seule voie
> repart, derrière un îlot de 3 m ; côté nord-ouest, une large bande plantée d'environ 8 m puis une piste vélo. Au
> sud-ouest, 2 voies dans chaque sens séparées par la pointe d'un îlot, et la Chronovélo derrière une bande d'herbe.
> À l'ouest l'avenue de Chamrousse (une voie par sens, bande cyclable en sortie, petit îlot planté avec une balise),
> au sud le chemin de Chaumetière, une rue étroite d'environ 6 m. Passages piétons sur chaque branche, petit îlot rond
> bas au milieu des passages, butte plantée d'arbustes couvre-sol dans le grand îlot, murets et palissades avec
> affiches. Enrobé fissuré avec pontages, tirets de guidage peints dans le carrefour.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | pente douce vers le sud-ouest (z ≈ 249 m) |
| E08 bordures | îlots séparateurs de Verdun, îlot planté de Chamrousse, petit îlot rond, nez |
| E10 chaussée | Verdun à chaussées séparées, Chamrousse, Chaumetière, zone de conflit centrale |
| E11 trottoirs, pistes | bande plantée de 8 m, pistes, liaisons revêtues aux passages |
| E12 marquages | voies affectées et flèches, lignes d'effet, passages, bande cyclable de Chamrousse (les tirets observés dans le carrefour ne sont pas reproduits par défaut : ARB-08) |
| E14 signalisation et feux | feux sur les 4 entrées, R12, panneaux d'affectation, balises de nez |
| E15 éclairage | candélabres |
| E16 mobilier | murets, palissades, potelets |
| E17 végétation (plus tard) | buttes d'arbustes, grands arbres |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Verdun nord-est (30 m) | entrée 3 voies 10,98 m (3,58 / 3,68 / 3,62), îlot 3,27, sortie 4,41 ; bande plantée 8,06 ; piste 3,16 | coupe `ne_30` ; OSM left\|through\|through;right |
| Verdun sud-ouest (30 m) | entrée 2 voies 7,39, îlot 2,81, sortie 2 voies 7,1, bande 1,26, Chronovélo | coupe `so_30` ; OSM 63600574, 1412130619, 398052219 |
| Chamrousse (30 m) | îlot 3,44, entrée 4,47, sortie 3,9 + bande cyclable 1,5 | coupe `chamrousse_30` ; OSM 7838799, 1271547679 ; photo ef8cd80b |
| Chaumetière (25 m) | chaussée 6,17 m à double sens | coupe `chaumetiere_25` |
| Régime | feux, 4 nœuds OSM ; passages sur chaque branche | OSM ; photos 921c90d1, 5922e7b4 |
| Tirets dans le carrefour | prolongement des voies | photo 5922e7b4 ; dossier 13 M08 (« différent », IISR7 art. 117-1) |
| Îlots | butte plantée basse, petit îlot rond bas | photo 921c90d1 |

## 4. Ce que la description simplifie

- Deux croisements de chaussées séparées (4 nœuds de feux) sont réunis en un seul carrefour centré au milieu.
- L'allée du Château (zone 30) au sud-est et les liaisons internes (OSM primary_link) ne sont pas décrites.
- Les tirets de guidage, les buttes plantées, le petit îlot rond et les palissades n'ont pas de mot ou sont exclus
  par règle (`../BESOINS_FORMAT.md`).

## Étape 3 — reconstruction (18/10/2026)

- Itération 1 : la bande plantée entre Verdun nord-est et la piste ne fait ≈ 2 m qu'au-delà de 50 m du centre et
  s'élargit à 8 m en approchant (photos 0c2f5716, a86b55d2 ; coupe ne_30) ; les deux sens de Chamrousse s'écartent
  autour d'un îlot planté d'environ 5 m (photos 208a1f46, cb597029, 921c90d1 ; OSM 7838796 / 7838799), largeur
  constante (l'îlot réel est triangulaire, BESOINS.md L2).
- Rapport : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## Étape 3, passe v2 — centre relu (18/10/2026)

Dossier de compréhension v2 lu en tuiles natives (59 photos, 129 vues dont 52 du centre ; IGN 2015 à 2025, levé GAM en
surimpression) : `COMPREHENSION.md`. Description simple du centre, telle qu'on la dirait :

> Un carrefour très ouvert : les médianes plantées de Verdun finissent chacune par un nez revêtu qui avance jusqu'au
> cœur et porte le refuge du passage ; l'avenue de Chamrousse arrive très en biais, ses deux sens écartés autour d'une
> butte plantée ; un long passage en biais longe le bord nord-ouest de Verdun avec de petits refuges à balise J5, et
> des traversées cyclables en carrés coupent le cœur ; le chemin de Chaumetière s'évase au débouché.

| Itération | Changement | Preuve |
|---|---|---|
| v2-1 | médianes de Verdun NE et SO en béton depuis ≈ 26 m jusqu'au cœur : îlots portés par le profil, refuges des passages (la passe 1 n'avait aucun îlot dans le carrefour) ; liaison revêtue NE réduite à 3 m ; passage de Chaumetière en retrait de 0,6 m | `gam_NE`, `gam_SO`, `gam_SE` (IGN 2024 + levé GAM) ; 54c3c177 -008, 8892229b -012 (18/05/2025), 6b04ee98 (28/07/2026) |

Hors format : `BESOINS.md` (LY-1 nez d'îlot dans la zone de conflit, LY-2 long passage en biais, LY-3 traversées en
carrés et refuges à J5, LY-4 embouchure évasée ; L1-L4 de la passe 1).
