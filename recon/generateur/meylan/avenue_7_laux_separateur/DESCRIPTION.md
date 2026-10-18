# Avenue des 7 Laux (RD1090) — avenue à chaussées séparées, piste cyclable et contre-allée

*Relevé Meylan, lot A, 17/10/2026. Point du site : 45,21515 N, 5,78110 E ; Lambert-93 (918 262,22 ; 6 461 157,98) ;
z ≈ 258,1 m (RGE ALTI), à ≈ 150 m au nord-est du rond-point du Lycée (`../rp_lycee/`, branche « 7 Laux »). Le site n'est
pas dans le dossier 13 : il a été choisi pour représenter les **avenues à chaussées séparées** de Meylan (BD TOPO :
« route à 2 chaussées », tronçon de 214 m).*

**État décrit : 28/07/2026** (campagne IGN, photos 360° de 08:23), le plus récent.

**Réseau (lot N1, 18/10/2026).** date d'état **28/07/2026** ; l'axe suit le milieu du séparateur relevé aux coupes t_sw et t0 (cap 51,65°) et part du nœud partagé `N_7LAUX_SO` (coupe t_sw), dont le profil (deux voies vers le rond-point, photo c531e1b2) est le contrat du joint ; la seconde voie disparaît avant le point du site (coupe t0). Description au format réseau, résolue par `recon/generateur/reseau/resoudre_reseau.py` ; nœuds partagés et contrats de profil dans `../reseau_meylan.yaml`.

**Reconstruction (étape 3, 18/10/2026).** Séparateur en pavés après le muret (muret non fabriqué, BESOINS S1) ; bande plantée entre piste et contre-allée refermée avant le point du site ; chaussée nord-ouest à deux voies jusqu'à ≈ 50 m. Détail : `RECONSTRUCTION.md` ; manques du générateur : `BESOINS.md`.

## 1. Description simple

> Avenue à la sortie de Meylan vers Montbonnot, en deux chaussées à sens unique séparées au milieu par une bande
> d'environ 1,5 m bordée, avec un caniveau en pavés, qui devient un muret béton plein d'environ 80 cm en approchant du
> rond-point du Lycée. Une voie par sens, large : environ 5 à 6 m vers le rond-point, 4 à 6,5 m dans l'autre sens. Côté
> nord-ouest, en partant de la chaussée : une bande béton d'environ 1,5 à 2 m avec une barrière bordeaux à croisillons,
> une piste cyclable à double sens d'environ 3 m avec des figurines vélo, une bande plantée (2 à 4 m), puis une
> contre-allée d'environ 3,5 à 4 m qui dessert les maisons (murs blancs, haies taillées). Côté sud-est, une grande
> pelouse en talus, puis des parkings. Enrobé très fissuré avec un réseau de pontages noirs, grands conifères et
> feuillus, candélabres simples ; la falaise du Saint-Eynard domine.

## 2. Ordre de construction (celui de la chaîne)

L'ordre qui fait foi est celui de la chaîne de construction (`../../CHAINE_CONSTRUCTION.md` § 2 et `chaine_construction.json`) : bordures et caniveaux avant l'enrobé, marquages avant la retenue et les panneaux, éclairage après les panneaux. L'ordre que proposait ce relevé est rangé ci-dessous dans ces étapes (relecture de la préparation, § 3).

| Étape de la chaîne | Ce que le site y construit |
|---|---|
| E07 plate-forme | pente douce vers le sud-ouest (z ≈ 258 m), talus enherbé au sud-est |
| E08 bordures | bordures et caniveau pavé du séparateur (muret béton à l'approche du rond-point), bordures de la piste et de la contre-allée |
| E10 chaussée | deux chaussées à sens unique (deux voies vers le rond-point), contre-allée |
| E11 trottoirs, pistes | bande béton, piste cyclable bidirectionnelle, bande plantée, pelouse |
| E12 marquages | rives, ligne entre les deux voies vers le rond-point, figurines vélo de la piste (au pas de 50 m, DEF-018), lignes de la contre-allée |
| E14 signalisation | panneaux de direction vers le rond-point, panneaux de piste |
| E15 éclairage | candélabres |
| E16 mobilier | barrières bordeaux à croisillons |
| E17 végétation (plus tard) | haies, conifères |

## 3. Constats et provenance

| Élément | Valeur | Provenance |
|---|---|---|
| Chaussée nord-ouest (sens sud-ouest) | 5,2 m au point du site, 6,05 m à 28 m au sud-ouest | coupes `t0`, `t_sw` (GAM) ; OSM 7838790 ; photo c531e1b2 (l+0000.0) |
| Séparateur | 1,53-1,54 m, bordures + caniveau pavé ; muret béton vers le rond-point | coupes `t0`, `t_sw` ; photo c531e1b2 (l+0000.0) |
| Chaussée sud-est (sens nord-est) | 4,0 m puis 6,46 m | coupes ; OSM 7838791, 1377219194 |
| Piste cyclable | 3,0 m, figurines, entre bande béton (barrière bordeaux) et bande plantée | coupes ; OSM 1305799234 ; photo c531e1b2 (l+0102.9) |
| Contre-allée | 3,5-4,1 m, sens unique vers le sud-ouest | coupes ; OSM 184096832 |
| Revêtement | enrobé très fissuré, réseau de pontages | photos c531e1b2, ce125bd7 ; RF-OBS-REV-01 |
| Mobilier | barrières bordeaux à croisillons | photos ; dossier 13 (mobilier bordeaux I06, G16) |

## 4. Ce que la description simplifie

- Tronçon droit de 64 m ; la naissance d'une deuxième voie d'entrée vers le rond-point (tiret vu sur c531e1b2) n'est
  pas décrite.
- La contre-allée est une voie du profil (pas de mot « contre-allée ») ; le muret béton du séparateur, les barrières
  bordeaux et le talus du sud-est n'ont pas de mot (`../BESOINS_FORMAT.md`).
