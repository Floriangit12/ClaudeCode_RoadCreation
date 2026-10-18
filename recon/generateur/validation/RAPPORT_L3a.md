# Rapport du lot L3a : modèles de véhicules de projet et balayage (épures de giration)

*`recon/generateur/validation/RAPPORT_L3a.md` — produit par `python recon/generateur/vehicules/controler_L3a.py` (données : `rapport_L3a.json`). Python 3 + numpy (shapely non requis ; même résultat à l'octet dans hython 22). Bases lues, non modifiées : `regles_route_fr.json`, DocRoute 10 et 17.*

**Statut : ok — 3 critères du plan sur 3 atteints ; contrôles d'appui : 5 / 7** (les contrôles d'appui non atteints concernent l'autocar 15 m, § 6)

## 1. Ce que le lot apporte

```
python recon/generateur/vehicules/construire_vehicules.py  # -> vehicules/vehicules_projet.json
python recon/generateur/vehicules/controler_L3a.py        # -> validation/rapport_L3a.json, RAPPORT_L3a.md,
                                                          #    recon/out/generateur/L3a/planche_*.png
```

- `vehicules/vehicules_projet.json` : 7 véhicules de projet (VL, bus standard 12 m, variante Citaro 12 m, bus articulé 18 m, porteur 11 m, semi-remorque 16,50 m, autocar 15 m) ; chaque cote porte sa source (document, page), sa nature, sa confiance et, si elle est dérivée, son calcul ; une partie `cinematique` (unités, empattements, attelages) et une partie `giration` (braquage minimal, rayons établis, conformité à la couronne 96/53) ; des alias (VL, bus, bus_articule, PL, semi, car) ;
- `vehicules/balayage.py` : modèle bicyclette multi-unités (tractrice intégrée exactement par pas), enveloppe de caisse rendue en polygone avec trous (réunion exacte de polygones convexes par distance signée + marching squares, ± 5 mm) ;
- API pour le solveur (lots L3, L5) :

```python
from vehicules.balayage import vehicule, rayon_min, balayage, balayage_detail, faisabilite, distance_signee, axe_virage
v = vehicule("bus")                    # nom ou alias (VL, bus, bus_articule, PL, semi, car)
rayon_min(v)                             # 8,653 m : rayon minimal de l'axe suivi par le centre de l'essieu avant
poly = balayage(v, axe)                  # axe [(x, y), ...] -> Polygone(exterieur, trous)
distance_signee(poly, p)                 # < 0 dedans ; nez d'îlot au « premier contact + 0,30 m » : >= 0,30
faisabilite(v, axe)["faisable"]          # rayon local de l'axe >= rayon_min(v)
axe_virage(R, angle, approche, sortie)   # droite - arc - droite (RF-GV-TRJ-006), flèche <= 0,5 mm
```

## 2. Critères

| Critère | Valeur | Seuil | Atteint |
|---|---|---|---|
| L3a-1 100 % des dimensions sourcées (source connue, nature, calcul des cotes dérivées) ; longueur hors tout de la cinématique = cote sourcée ± 1 mm | 63 / 63 cotes sourcées (annonce 8, derive 14, donnee_administrative 1, donnee_constructeur 16, norme 24) ; écart de longueur hors tout max 0.001 mm | 100 % ; ≤ 1 mm | oui |
| L3a-2 balayage d'un virage du cercle homologué (semi-remorque de vérification N05 / 96/53) reproduit Rext 12,50 / Rint 5,30 m (CU p. 78) à ± 0,10 m — *avance de sellette dérivée de la couronne : Rint reproduit PAR CONSTRUCTION en régime établi ; la mesure valide la chaîne numérique (approche, convergence de la tractrice, enveloppe rendue)* | poses : Rext 12.500, Rint 5.300 ; polygone rendu : Rext 12.503, Rint 5.297 ; écart max 0.003 m | 12.50 / 5.30 ± 0,10 m | oui |
| L3a-3 balayage du bus standard reproduit Rint 4,80 / Rext 11,50 m (VU p. 144) à ± 0,10 m — *Rext 11,50 = donnée de calage du braquage ; Rint = contrôle indépendant des cotes (Urbanway 12, transbus)* | poses : Rext 11.500, Rint 4.867 ; polygone rendu : Rext 11.503, Rint 4.864 ; écart max 0.067 m | 11.50 / 4.80 ± 0,10 m | oui |
| L3a-A1 (appui) virage de 720° de chaque véhicule au rayon minimal : rayons mesurés (poses, polygone rendu) = régime établi analytique | 7 véhicules ; écart max 5.3 mm ; 1 composante, 1 trou chacun | ≤ 10 mm | oui |
| L3a-A2 (appui) chaque véhicule s'inscrit dans la couronne 96/53 § 1.5 (Rint ≥ 5,30 m quand Rext = 12,50 m) | 6 / 7 ; non conforme : autocar_15m (Rint 4.91 m) | 7 / 7 | non |
| L3a-A3 (appui) autobus : débord au-delà du plan tangent au flanc en entrant dans la couronne ≤ 0,60 m (96/53 § 1.5 bis ; borne haute, braquage instantané) | bus_standard_12m 0.220 m ; bus_12m_citaro 0.277 m ; bus_articule_18m 0.348 m ; autocar_15m 0.677 m | ≤ 0,60 m | non |
| L3a-A4 (appui) faisabilité (rayon local de l'axe ≥ rayon_min) : axe à 1,002 × rayon_min accepté, à 0,95 × rayon_min refusé ; braquage simulé ≤ braquage maximal + 0,1° à 1,002 × rayon_min | 7 / 7 | 7 / 7 | oui |
| L3a-A5 (appui) balayage rectiligne de 30 m du bus : aire = largeur × (30 + longueur) | 104.9975 m² pour 105.0000 m² (0.0024 %) | ≤ 0,1 % | oui |
| L3a-A6 (appui) témoins négatifs : une cote faussée fait sortir Rint de la tolérance | empattement du bus + 0,30 m -> écart -0.308 m ; largeur du bus + 0,20 m -> écart -0.132 m ; pivot - essieux de la semi + 0,30 m -> écart -0.369 m | 3 / 3 détectés | oui |
| L3a-A7 (appui) déterminisme : vehicules_projet.json reconstruit à l'octet ; polygones de deux virages identiques dans deux processus Python et dans hython 22 | JSON identique ; empreintes 08d220b6d5d1 / 08d220b6d5d1 ; hython 08d220b6d5d1 | identique | oui |

## 3. Véhicules

| Véhicule | Rayon min. de l'axe | Rext caisse (calage) | Rint calculé | Rint publié | Braquage max | Couronne 96/53 (Rint à Rext 12,50) |
|---|---|---|---|---|---|---|
| `autocar_15m` — Autocar 15 m à essieu arrière directionnel (autocar de vérification N05 ; Setra S 519 HD) | 8,949 m | 12,045 m (SETRA (cercle de braquage 24 090 mm)) | 4,119 m | — | 52,9° | 4,91 m **non conforme** |
| `bus_12m_citaro` — Autobus Mercedes-Benz Citaro 12 m (variante constructeur) | 8,571 m | 11,485 m (CITARO p. 3 (turning circle 22 970 mm)) | 4,942 m | 4,80 m | 43,5° | 6,42 m conforme |
| `bus_articule_18m` — Autobus articulé 18 m (Mercedes-Benz Citaro G, pousseur) | 9,143 m | 12,000 m (CF p. 22) | 5,300 m | 5,30 m | 40,2° | 6,05 m conforme |
| `bus_standard_12m` — Autobus urbain standard 12 m (Iveco Urbanway 12, successeur des Agora / Citelis) | 8,653 m | 11,500 m (VU p. 144) | 4,868 m | 4,80 m | 45,0° | 6,35 m conforme |
| `pl_porteur` — Camion porteur 11 m (camion de VU p. 144) | 10,516 m | 12,500 m (VU p. 144) | 6,500 m | 6,50 m | 42,3° | 6,50 m conforme |
| `semi_remorque` — Tracteur 4x2 + semi-remorque 3 essieux (ensemble de vérification N05, 16,50 m) | 10,755 m | 12,500 m (D9653 annexe I § 1.5 ; CU p. 78) | 5,300 m | 5,30 m | 20,1° | 5,30 m conforme |
| `vl` — Voiture particulière (berline de référence, VU p. 144) | 5,467 m | 6,900 m (VU p. 144) | 3,600 m | 3,60 m | 31,7° | 9,78 m conforme |

Natures des cotes : norme (guides VU, CU, CF, N05 ; directive 96/53), donnée constructeur (fiche Citaro locale ; fiche Setra lue par moteur de recherche), donnée administrative (AEE), annonce (transbus.org, annonces de véhicules d'occasion : confiance moyenne), dérivé (calcul écrit dans le JSON). Aucune cote estimée sans source.

## 4. Méthode et mesures

- **Point guide** : centre de l'essieu avant directeur ; l'axe d'un mouvement (axe de voie – arc tangent – axe de voie, RF-GV-TRJ-006) est la trajectoire de ce point. **Braquage minimal** : calé sur un rayon extérieur de caisse publié (VU p. 144, CF p. 22, couronne 96/53, cercle de braquage constructeur) ; `rayon_min` = rayon du point guide correspondant.
- **Cinématique** : l'essieu équivalent de chaque unité suit son meneur en tractrice ; sur un pas rectiligne du meneur, tan(φ'/2) = tan(φ/2)·exp(−s/L) est exacte (pas de 5 cm). Essieu équivalent : milieu du groupe de 3 essieux fixes de la semi-remorque, essieu moteur de l'autocar (essieu suiveur directionnel idéal) [G]. Faisabilité : rayon local de l'axe ≥ `rayon_min` (en transitoire le braquage ne dépasse pas celui du régime établi de la courbure maximale).
- **Enveloppe** : caisses aux positions retenues (pas 0,25 m) + enveloppes convexes de chaque tronçon de 0,25 m du contour entre deux positions (l'enveloppe convexe de la caisse entière débordait de ~0,07 m vers le centre : défaut trouvé et corrigé pendant le lot) ; réunion par fonction de distance signée (zéro exact) et marching squares au pas de 5 cm, simplification 3 mm.
- **Mesure de L3a-2 et L3a-3** : virage de 720° pris depuis une approche rectiligne ; rayons mesurés sur le second tour, sur les poses (sommets et distance minimale des caisses au centre) et sur le polygone rendu (anneau extérieur et trou).

| Véhicule | R axe | Rext / Rint établis | Rext / Rint poses | Rext / Rint polygone | Écart max |
|---|---|---|---|---|---|
| autocar_15m | 8,949 | 12,045 / 4,119 | 12,045 / 4,119 | 12,047 / 4,115 | 3,9 mm |
| bus_12m_citaro | 8,571 | 11,485 / 4,942 | 11,485 / 4,941 | 11,488 / 4,938 | 3,6 mm |
| bus_articule_18m | 9,143 | 12,000 / 5,300 | 12,000 / 5,300 | 12,003 / 5,296 | 3,7 mm |
| bus_standard_12m | 8,653 | 11,500 / 4,868 | 11,500 / 4,867 | 11,503 / 4,864 | 3,4 mm |
| pl_porteur | 10,516 | 12,500 / 6,500 | 12,500 / 6,500 | 12,503 / 6,496 | 3,7 mm |
| semi_remorque | 10,755 | 12,500 / 5,300 | 12,500 / 5,300 | 12,502 / 5,297 | 3,2 mm |
| vl | 5,467 | 6,900 / 3,600 | 6,900 / 3,600 | 6,902 / 3,595 | 5,3 mm |

## 5. Ce qui est contrôlé et ce qui est « par construction »

- **Bus standard (L3a-3) — contrôle indépendant** : cotes de l'Urbanway 12 (empattement 6,12, porte-à-faux avant 2,71, largeur 2,50 m ; transbus.org via DocRoute 17, confiance moyenne), braquage calé sur Rext = 11,50 m ; le rayon intérieur **calculé** vaut 4,867 m pour 4,80 publié (écart 0,067 m, dans ± 0,10). Sensibilité : avec les cotes du Citaro 12 m (fiche constructeur, confiance haute) on trouve 4,94 m à Rext 11,485 m (écart 0,14 m, hors tolérance) : le « bus 12 m » de VU p. 144 a un avant plus long que le Citaro.
- **Cercle homologué (L3a-2) — par construction en régime établi** : ni l'avance de sellette du tracteur ni sa cote équivalente ne figurent dans les fiches lues ; la semi-remorque de vérification (N05 : 6,08 + 13,67 m ; 96/53 : 16,50 m, pivot - arrière 12,00 m, rayon avant 2,04 m ; Schmitz S.CS : pivot - essieux 7,70 m) est complétée par l'avance de sellette (0,741 m) qui l'inscrit au plus juste dans la couronne. Le critère valide la chaîne numérique (approche rectiligne, convergence de la tractrice, enveloppe rendue), pas les cotes ; témoin : +0,30 m sur le pivot - essieux déplace Rint de −0,37 m.
- **VL, bus articulé, porteur** : la cote manquante (porte-à-faux avant du VL, articulation du Citaro G, empattement du porteur) est dérivée des deux rayons publiés (VU p. 144, CF p. 22) : leurs rayons sont reproduits par construction.

## 6. Problèmes et limites

- Autocar 15 m (Setra S 519 HD, cotes lues par moteur de recherche) : avec l'empattement avant-moteur de 7,14 m et un essieu suiveur directionnel idéal, le modèle ne s'inscrit pas dans la couronne 96/53 (Rint 4,91 m < 5,30 m à Rext 12,50 m), alors que le véhicule est homologué : porte-à-faux avant (2,89 m) à confirmer sur la fiche PDF du constructeur, ou empattement équivalent < 7,14 m (centre instantané en avant de l'essieu moteur). Le balayage de l'autocar est donc plus large que le réel côté intérieur (sécuritaire).
- Débord 96/53 § 1.5 bis > 0,60 m pour autocar_15m (0.68 m) : borne haute (braquage instantané à l'entrée du cercle) ; pour l'autocar, porte-à-faux arrière de 4,97 m derrière l'essieu moteur dans le modèle (essieu suiveur directionnel idéal) — même cause probable que la couronne (cotes Setra à confirmer).
- Cotes « annonce » (confiance moyenne) : empattement du tracteur (3,70 m), pivot - essieux et entraxe de la semi-remorque (7,70 / 1,31 m), cotes de l'Urbanway 12 ; à remplacer par des fiches constructeurs téléchargées (le téléchargement demande l'accord de l'utilisateur).
- Modèle sans glissement ni dévers ; caisses rectangulaires (rétroviseurs inclus pour le VL seulement, comme VU p. 142-144) ; le braquage instantané à l'entrée d'un arc majore le débord arrière (§ 1.5 bis).
- `rayon_min` de la semi-remorque (10,75 m) est celui de la couronne d'homologation, pas le braquage maximal du tracteur seul.

## 7. Rendus regardés

Planches ≤ 1092 px, regardées en entier après découpe par `recon/pcg/vision/decoupe.py` (1 tuile chacune) : `recon/out/generateur/L3a/planche_couronne.png` (semi-remorque et bus dans leur couronne de référence ; tirets rouges : 12,50 / 5,30 et 11,50 / 4,80 m ; axe suivi en vert) ; `planche_virages.png` (virage à gauche de 90° au rayon minimal pour six véhicules : sur-largeur intérieure, débord avant, débord arrière de l'autobus et de l'autocar).

