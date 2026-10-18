# Lot « autoroutes » : rapport

*`recon/generateur/validation/RAPPORT_autoroutes.md` — 18/10/2026. Demande de l'utilisateur : « le PCG doit reproduire des
autoroutes, des ronds-points, plusieurs types de bordures… il doit être complet ». Ce lot couvre les autoroutes : route
seule (sol neutre plat, ciel simple et soleil), pas de décor ni de végétation. Critères chiffrés :
`validation/rapport_autoroutes.json` ; mesures détaillées : `validation/controles_autoroutes.json`.*

## 1. Ce qui est livré

| Élément | Fichier | Rôle |
|---|---|---|
| HDA `rg::autoroute::1.0` | `hda/rg_autoroute/construire.py`, `vex_autoroute.py`, `rg_autoroute.hdalc/` | dispositifs de retenue (GBA / DBA béton, glissières GS2 / GS4 / DE2), musoirs des bretelles (sol, aplat, chevrons, demi-lignes de contour), raccord vertical des bretelles |
| Pilote | `fabriquer_autoroutes.py` | chaîne L1 + L2 + L2b + `rg::autoroute`, exports `autoroute/`, rendus (2 vues ; 3 pour A3), vérification de déterminisme |
| Contrôle indépendant | `validation/controler_autoroutes.py`, `validation/faire_rapport_autoroutes.py` | mesures sur la géométrie fabriquée (sol, peinture, équipements) |
| Scènes | `scenes_autoroutes/A1…A4.yaml` | A3 et A4 : rive gauche des bretelles « continue 3u » (seule modification) |
| Sorties | `recon/out/generateur/A*/` (`l1/`, `l2/`, `l2b/`, `autoroute/`, `rendus/`) | non versionnées |

`rg::autoroute` (4 entrées, 4 sorties) :

```
entrées 1 limites (rg::profils, sortie 1)   2 sol (rg::sol, sortie 1)
        3 zones et îlots + nœuds (rg::lire_modele, sorties 3 et 2 fusionnées)   4 références (rg::graphe, sortie 1)
raccord (VEX) : dz de chaque bretelle au nœud « fourche »  ->  appliquer (VEX, points du sol de la bretelle)
musoirs (VEX) : sol du musoir et du terre-plein latéral, aplat de pointe, chevrons, demi-lignes de contour
separateurs (VEX) : contours béton balayés le long des limites « separateur » ; glissières en pièces du catalogue
sorties 1 SOL (routes raccordées + musoirs, contrat de rg::sol)   2 ÉQUIPEMENTS (maillages, materiau_id du catalogue)
        3 MARQUES (contrat de pj::marquage_solide)   4 CONTRÔLES (détail ra_m_*, ra_s_*, ra_bretelles, ra_dz)
```

Houdini n'invente rien : les contours béton (`retenue_DBA`, `retenue_GBA`, `retenue_LBA`, `retenue_MVL`) et les pièces des
glissières (`retenue_glissiere_GS2/GS4/DE2_module_L400`) sont recopiés du catalogue `catalogue_assets_route.json` dans les
paramètres de l'HDA, avec leurs sources dans l'aide (Cerema, *Dispositifs de retenue*, tableaux 15 et 16 p. 32, NF P98-426 ;
fiches Aximum GS2, GS4+, DE2 ; Setra BVL 2001 p. 30). Les positions viennent des limites « separateur » du modèle ; le
musoir, des îlots du modèle (îlot peint, terre-plein latéral) et des bords des plates-formes ; les marques, de DEF-020,
RF-MQ-HACH-01 à -03 et RF-MQ-MUS-01 (algorithme `chevrons_zone` du dossier 08).

## 2. Profils autoroutiers et sources

| Bande | Largeur | Source |
|---|---|---|
| Voie (principale, bretelle, insertion, décélération) | 3,50 | RF-OSM-LAR-014 (autoroute_voie) ; VSA 90/110 § 5.1.2 p. 21 |
| BAU | 3,00 | RF-OSM-LAR-014 (autoroute_BAU) ; VSA 90/110 § 5.3.2 p. 23 (3,00 m si PL > 2 000 /j) |
| Berme | 1,00 | RF-OSM-LAR-014 (autoroute_berme) ; VSA 90/110 § 6.4.5 p. 48-49 |
| BDG | 1,00 | RF-GV-TPC-002 (BDG_A_normale, ICTAVRU p. 50) ; VSA 90/110 § 5.2.1 p. 22 |
| TPC A1 / A3 / A4 | 2,60 = BDG 1,00 + DBA 0,60 + BDG 1,00 | RF-GV-TPC-002, -003 (DBA, bande médiane 0,60) ; RF-OBS-TPC-01 (DBA ≈ 2,6 m observée en Isère) |
| TPC A2 | 5,00 = BDG 1,00 + gazon 3,00 + BDG 1,00, deux glissières | RF-GV-TPC-006 (engazonné si ≥ 3,00 m) ; RF-GV-TPC-008 (barrières sur TPC < 12 m) |

ICTAAL n'est pas dans les sources locales. Les bretelles suivent la VSA 90/110 (Cerema 2014). Contrôle AU-02 :
115 bandes sur 115 aux valeurs sourcées.

## 3. Marquages

- **u = 7,5 cm sur autoroute : vérifié** (RF-MQ-U-01, IISR7 art. 113-1 C p. 7). Lignes mesurées sur la peinture fabriquée :
  - délimitation T1 2u (0,15 m) ;
  - BAU T4 3u (39 / 13 m) ;
  - TPC et rive sans BAU : continue 3u ;
  - BAU des bretelles T'3 3u (20 / 6 m) ;
  - voies d'insertion et de décélération T2 5u (0,375 m). Sources : IISR7 art. 114-2 C, 114-4 B p. 15 et 117-3.
- **Rive gauche des bretelles.** Le compilateur posait la rive de route T2 3u (RF-OSM-MRQ-021). Les descriptions A3 et A4
  disent maintenant « ligne continue 3u » (IISR7 art. 114-4 B : en l'absence de BAU, la rive est continue 3u ;
  RF-MQ-SC-06 « sans_bau »).
- **Musoirs.** Contour continue 3u, puis 2u non peints (RF-MQ-MUS-01). Aplat là où la zone a moins de 0,30 m
  (RF-MQ-HACH-03). Chevrons partout ailleurs (RF-MQ-HACH-02) :
  - deux familles symétriques par rapport à la bissectrice des deux lignes de contour ;
  - inclinées « 2 pour 1 » sur elle (26,565°) ;
  - bandes de 0,50 m, pas de 1,85 m (DEF-020) ;
  - pointe vers le conducteur. Contrôlé à la fois sur la figure IISR7 p. 37 (convergence et divergence) et sur la peinture.
- **Demi-lignes de contour.** `rg::marquages` ne peint que la moitié intérieure d'une ligne posée sur la limite
  extérieure d'un profil (0,11 m au lieu de 0,225 m). Au droit du musoir, `rg::autoroute` pose la moitié côté musoir sur
  le sol du musoir.
- **Flèches « ×4/3 » : non applicables ici.** L'IISR ne prévoit aucune homothétie de la flèche de rabattement (annexe
  B.1 ; dossier 08 § 7.3). Le rapport 4/3 concerne les **flèches directionnelles** sur autoroute (nota des annexes B.2 et
  B.3, p. 62-63, RF-MQ-DIR-09) ; elles ne servent qu'avec une affectation de voies, que A1-A4 ne décrivent pas. Les
  gabarits `*_X4_3` existent dans `gabarits_iisr7_pj.json`. A1-A4 n'ont aucune flèche : le critère AU-14 est marqué non
  atteint (non démontré).

## 4. Dispositifs de retenue

- **DBA (A1, A3, A4).** « GBA largeur 0,6 » est posée en séparateur double DBA : base 0,60 m, 0,81 m de haut, profil du
  catalogue. Elle est centrée sur la limite et balayée sans joint le long des sections. Les bouts ne sont fermés qu'aux
  extrémités de la route. La base est encastrée de 5 cm dans le sol ([G]) : aucun jour sous le talon quand le sol a un
  dévers.
  - Mesure sur 38 coupes (3 scènes) : base 0,600 m, hauteur au-dessus du sol fabriqué 0,810 m.
  - Continuité de 0 à L, pas maximal de 1,00 m.
- **Glissières (A2).** Le modèle dit « glissière » sans modèle de glissière : GS2 par défaut ([G], paramètre de l'HDA).
  - La lisse (profil A) est balayée en continu, face sur la limite du modèle, côté du trafic. Le côté est lu sur la classe
    du sol fabriqué de part et d'autre de la limite.
  - Supports C100, écarteurs et boulons sont posés par module de 4 m (2 supports par module).
  - Mesures : 2 glissières, 500 supports, haut de lisse à 0,700 m au-dessus du sol, pas des supports de 2,000 m, face à
    moins de 1,3 mm de la limite.
- **Rendu.** Couche `/Monde/Equipements` de `l2/route_l2.usda`, double face. Matériaux de la bibliothèque :
  `beton_prefa_lisse` (recalé au rendu comme le béton gris des bordures) et `acier_galvanise`.

## 5. Bretelles et musoirs (A3 entrée, A4 sortie)

| Mesure (géométrie fabriquée) | A3 (entrée, 1/25) | A4 (sortie, 1/33) | Source |
|---|---|---|---|
| Voie auxiliaire : écart à la loi de largeur du modèle | 0,000 m | 0,000 m | modèle |
| Biseau | 75,0 m (3,50 → 0) | 150,0 m (0 → 3,50) | VSA 90/110 p. 34, schéma 26 ; p. 31, schéma 14 |
| Zone de manœuvre depuis E.1,00 | 199,93 m | — | VSA 90/110 p. 34 (200 m) |
| Point à 1,00 m / à 5,00 m depuis la jonction | 24,99 / 125,07 m | 32,99 / 165,05 m | VSA 90/110 p. 38 |
| Obliquité mesurée | 0,03997 | 0,03029 | 1/25 ; 1/33 |
| BAU interrompue au droit du musoir | [175 ; 300], 0 sommet de BAU | [500 ; 665], 0 | IISR7 schéma « suppression de la BAU » ; VSA p. 38 |
| Raccord vertical : dz appliqué / écart de Z à la jonction | −0,281 m / 1,5 mm | −0,281 m / 2,0 mm | solveur (voir § 7, point 3) |
| Sol du musoir : aire peinte + terre-plein latéral | 312,3 + 84,0 m² | 412,4 + 63,4 m² | îlots du modèle |
| Marche de Z aux bords du sol du musoir | 0,5 mm | 1,6 mm | — |
| Chevrons mesurés (bandes entières) : nombre, angle, largeur, pas, pointe | 42 ; 26,564-26,565° ; 0,498 m ; 1,850 m ; 42/42 vers l'amont | 56 ; idem ; 56/56 | RF-MQ-HACH-02, DEF-020 |

- **Sol du musoir.** Il occupe l'espace entre le bord de la plate-forme de la principale et celui de la bretelle, de la
  jonction au bout du terre-plein latéral du modèle. Revêtement :
  - entre la jonction et le point à 5,00 m : celui de la chaussée voisine (enrobé) ;
  - au-delà, terre-plein latéral **de plain-pied, en gazon**, celui de la berme voisine.
  Sur autoroute il n'y a pas de bordure (`bordure_par_contexte("autoroute")`, RF-GV-PON-005). Les Z sont raccordés aux
  deux sols fabriqués.
- **Point à 5,00 m.** L'îlot peint du compilateur est échantillonné au pas de 0,25 m. Son bout est ramené sur la borne
  de section de la principale où la BAU reprend (174,78 → 175,00 en A3).

## 6. Critères

| Id | Critère | Valeur | Seuil | Atteint |
|---|---|---|---|---|
| AU-01 | largeurs des bandes, sol fabriqué / modèle | 0,0000 m (56 bandes, 1 416 coupes) | ≤ 0,01 m | oui |
| AU-02 | largeurs du modèle = sources | 115/115 | 100 % | oui |
| AU-03 | modulations (trait, intervalle), peinture fabriquée | écart max 0,0058 m (694 tirets ; T1, T2, T'3, T4) | ≤ 0,01 m | oui |
| AU-04 | largeur des lignes = largeur_u × u | écart max 0,0030 m (34 lignes) | ≤ 0,01 m | oui |
| AU-05 | modulations conformes IISR7 autoroutes | 38/38 lignes | 100 % | oui |
| AU-06 | DBA : base 0,60, hauteur 0,81, continue | 0,0000 m (38 coupes), continue 3/3 | ≤ 0,01 m | oui |
| AU-07 | glissières GS2 : haut de lisse, pas, face | 0,0013 m (2 glissières, 500 supports) | ≤ 0,01 m | oui |
| AU-08 | voie d'insertion (A3) | 0,000 m ; biseau 75,0 m ; zone de 199,93 m | ≤ 0,01 m ; 200 ± 0,1 m | oui |
| AU-09 | voie de décélération (A4) | 0,000 m ; biseau 150,0 m | ≤ 0,01 m | oui |
| AU-10 | points à 1 m et 5 m, obliquité | ± 0,07 m ; ± 0,0003 | ± 0,10 m ; ± 0,0005 | oui |
| AU-11 | chevrons (angle, largeur, pas, pointe) | ± 0,001° ; ± 0,002 m ; ± 0,0001 m ; 98/98 | ± 0,1° ; ± 0,01 m ; 100 % | oui |
| AU-12 | raccord vertical, sol du musoir | 2,0 mm ; 1,6 mm | ≤ 0,01 m | oui |
| AU-13 | BAU interrompue au droit du musoir | 0 sommet | 0 | oui |
| AU-14 | gabarits des flèches ± 1 mm | sans objet (aucune flèche dans A1-A4) | ± 1 mm | **non** |
| AU-15 | déterminisme (vérifié une fois en fin de lot, A2 et A3) | identique (60 fichiers : l1, l2, l2b, autoroute) | identique | oui |
| AU-16 | rendus regardés en tuiles natives | 9/9 vues | 9/9 | oui |

La peinture mesure 2 mm de moins que l'empreinte : 0,223 m pour 0,225 m, 0,498 m pour 0,50 m. C'est le chanfrein de
`pj::marquage_solide`, déjà constaté au lot L2b, et c'est dans la tolérance. Les tirets rognés par le dégagement de 2u,
là où deux lignes convergent au bout d'un biseau (choix [G] du lot L2b), sont comptés à part
(`tirets_rognes_convergence`) et ne sont pas mesurés en largeur.

Bilan : 15 critères atteints sur 16 ; AU-14 (flèches) n'est pas démontré, faute de flèche prescrite dans A1-A4.

## 7. Problèmes et limites (à reporter par l'agent d'intégration)

1. **Îlot « musoir » du compilateur.** Il porte une bordure I2 de 0,11 m et recouvre la BAU de la principale sur environ
   2,3 m (A3 : îlot à 0,70 m des bords des **voies**). Or la VSA 90/110 p. 38 (schéma 40) compose le tpl de la BAU de la
   chaussée, puis du dispositif ou de la balise, puis de la BDG de la bretelle. Et sur autoroute il n'y a pas de bordure.
   `rg::autoroute` ne le fabrique donc pas tel quel : il pose un terre-plein latéral de plain-pied entre les plates-formes,
   sur la même étendue. À corriger dans `description/carrefours.py` (`Bretelle.construire`) : décaler le tpl de la BAU,
   pas de bordure.
2. **BDG des bretelles (VSA 90/110 § 6.4.5.2 p. 49 : 0,50 m) non décrite.** Le compilateur ancre une route à sens unique
   sur son bord gauche (`profil.reference`). Une BDG interrompue avant la jonction, sans quoi elle déborderait sur la voie
   de la principale, déplacerait la voie de 0,50 m. Il faudrait ancrer sur la voie (bord de référence au choix).
3. **Pas de profil en long par route dans le modèle de Z.** `rg_niveau.h` ancre chaque route à Z = 0 sur sa référence.
   Sans correction, la bretelle était 0,28 m au-dessus de la principale à la jonction. `rg::autoroute` décale le sol de la
   bretelle de dz, mesuré à 0,50 m de part et d'autre de la jonction : profil en long parallèle, [G]. Le HeightField de
   `rg::nivellement` n'est pas décalé, mais le drapé de la peinture le tolère (portée de 0,40 m de
   `pj::marquage_solide`). Il faudrait porter `profil_long` ou un décalage par route dans `rg::nivellement`.
4. **`rg::marquages` ne peint que la moitié intérieure** d'une ligne posée sur la limite extérieure d'un profil.
   Exemples : la rive gauche des bretelles hors musoir (0,111 m) et la rive de la principale au droit du musoir, complétée
   ici. Correction à faire dans `rg::marquages` : moitié extérieure peinte, ou bande d'accotement exigée.
5. **Compilateur.**
   - Les voies d'autoroute ont `usagers: ["vl", "pl", "velo"]`, alors que les cycles sont interdits sur autoroute (à
     retirer pour `categorie: autoroute`).
   - `ev_rabattement` applique la table des routes (RF-MQ-RAB-05) et la rive T'3. Le cas autoroute n'est pas traité :
     biseau 2L (RF-MQ-OBL-04) et interdistances RF-MQ-RAB-06.
   - La ligne T3 2u de dissuasion avant une sortie (RF-MQ-DEC-02) dépend de la position du D30 (lot L6).
6. **Lot L6.** Balise J14a au nez des musoirs, panneaux D / Da, atténuateurs de choc (catalogue `retenue_attenuateur_*`)
   et extrémités abaissées des DBA et des glissières : rien de cela n'est posé. Les bouts des scènes sont des coupes, pas
   des fins de file.
7. **Ajouts en mémoire dans `fabriquer_autoroutes.py`** (à fusionner) :
   - `F2B.cuire` décide du contournement de `pj::marquage_solide` d'après son entrée réelle : les marques du musoir
     existent sans flèche ni symbole ;
   - `F2.ecrire_usd` ajoute la couche Equipements ;
   - le rendu ajoute `ECHELLE_ALBEDO["beton_prefa_lisse"]` (béton gris des bordures) et `ATTENUER_NORMALE` ;
   - la vue de dessus est rectangulaire (1092 × 546 px) et centrée sur le sujet.
8. **ICTAAL absent des sources locales.** Les longueurs des bretelles sont celles de la VSA 110 ; principale déclarée à
   110 km/h en A3 et A4.

## 8. Rendus regardés

Tous les rendus ont été regardés en tuiles natives ≤ 1092 px (`rendus/tuiles/`).

| Scène | Vues | Constats |
|---|---|---|
| A1 | dessus (84 m), conducteur | DBA visible au centre ; T1 et T4 lisibles, avec leurs modulations |
| A2 | dessus, conducteur | TPC engazonné entre deux glissières GS2, supports tous les 2 m, lisse à 0,70 m ; 2 × 3 voies |
| A3 | dessus (195 m), oblique 3/4, conducteur sur la bretelle | voir ci-dessous |
| A4 | dessus (200 m), conducteur 70 m avant la divergence | biseau de décélération et ligne T2 5u ; musoir de divergence, chevrons pointés vers l'amont |

Constats sur A3 :
- chevrons pointés vers l'amont, aplat de pointe, BAU interrompue au droit du musoir ;
- terre-plein latéral en gazon ;
- voie d'insertion avec T2 5u.

## 9. Commandes

```
hython recon/generateur/fabriquer_autoroutes.py recon/generateur/scenes_autoroutes/A3_bretelle_entree.yaml --rendus
hython recon/generateur/fabriquer_autoroutes.py A2.yaml A3.yaml --rendus --verifier-determinisme
python recon/generateur/validation/controler_autoroutes.py [recon/out/generateur/<scene> ...] [--json SORTIE]
python recon/generateur/validation/faire_rapport_autoroutes.py --determinisme "<texte>" --rendus-regardes 9
```
