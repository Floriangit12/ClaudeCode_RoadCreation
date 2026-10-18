# Avenue des 7 Laux — besoins du générateur relevés à la reconstruction (étape 3)

*`recon/generateur/meylan/avenue_7_laux_separateur/BESOINS.md`, 18/10/2026. Manques du générateur (code partagé non
modifié par le lot de sites) rencontrés en reconstruisant le site ; chacun avec l'élément, la photo et la règle. Voir
aussi `RECONSTRUCTION.md`.*

| N° | Élément | Constat (photo, preuve) | Effet aujourd'hui | Besoin |
|---|---|---|---|---|
| S1 | Muret séparateur plein entre deux chaussées | Du rond-point du Lycée jusqu'à ≈ 25 m au-delà du nœud N_7LAUX_SO (itération 2 : about incliné vu sur 7b560dfa, 36bf8ffd ; muret sur 7f4bd2a6 à 9 m et 18d61cc3 à 15 m), le séparateur est un muret béton plein d'environ 0,8 à 1 m, à about incliné (photos 7f4bd2a6, 18d61cc3, 63237408, 0630f847 au loin ; rp_lycee db830c57, 7486b798) | Décrit en « terre-plein 1,5 béton » : bande bordée de 0,11 m ; le muret n'apparaît sur aucun rendu | Mot « muret » de séparateur continu avec hauteur, fabriqué hors autoroute : le vocabulaire a « muret » sur une limite (`vocabulaire.SEPARATEURS`), mais seuls GBA, DBA, LBA, MVL et glissière ont une géométrie, et seulement par `rg::autoroute` (le pilote bascule alors toute la scène dans la famille autoroute). Une DBA écrite entre deux demi-terre-pleins changerait aussi le profil du contrat du nœud N_7LAUX_SO (`../reseau_meylan.yaml`) : non tenté. |
| S2 | Barrière bordeaux à croisillons sur la bande béton | Photos c531e1b2 l+0102.9, 0630f847, 83beab55, 42320873, 2430c43c | Absente (mobilier, étape E16) ; l'asset du catalogue est en RAL 7024 graphite (relecture X4) | Variante de teinte bordeaux de la barrière ; mot de mobilier sur une bande (`objets: barrieres: {bande, pas, teinte}`). |
| S3 | Ligne de gros blocs entre la piste et la contre-allée | Photos c531e1b2 l+0102.9 (28/07/2026), 2430c43c (01/05/2024) | Entre la piste (au niveau du trottoir par défaut) et la contre-allée, le compilateur pose une bordure ; la ligne de blocs n'a pas de modulation dans le vocabulaire | Piste « au niveau de la chaussée » accolée à une voie avec une ligne de blocs (modulation large type T'3 en blocs) ; RF-MA-PIS-006 admis en écart. |
| S4 | Enrobé très fissuré à pontages noirs | Toutes les photos de chaussée (c531e1b2, 0630f847, 83beab55, 7f4bd2a6, 4388769c) | `enrobé usé` donne un enrobé gris uniforme | Matériau « enrobé fissuré ponté » (RF-OBS-REV-01) avec réseau de pontages procédural. |
| S5 | Rendus et comparaison | (commun au lot) | Voir `../rp_lycee/BESOINS.md` G6 et G7 | — |

## Passe 2 (18/10/2026)

| N° | Élément | Constat (vue, preuve) | Effet aujourd'hui | Besoin, règle |
|---|---|---|---|---|
| S1 bis | Muret séparateur plein jusqu'à ≈ 25 m (et non 12 m) | `0630f847_+006`, `e17dc3d0_-003` du 28/07/2026 : about incliné vu de face au bout de la chaussée ; ombre sur les orthos de 2018 à 2025 | Bande « béton » bordée de 0,11 m jusqu'à 25 m, sans muret | S1 inchangé (mot « muret » hors autoroute, hauteur, about incliné) |
| S6 | **Rétrécissement continu** d'une bande extérieure (bande plantée de 4,2 m au nœud à 0 m en pointe à s ≈ 47 m, bordures GAM) qui **chevauche** un changement de profil (séparateur béton → pavés à 25 m) | Zoom `nord_ouest_gam` ; coupe t0 (1,6 m à s ≈ 29) | Un évènement ne peut pas en chevaucher un autre : décrit en largeur constante jusqu'à 25 m, puis fermeture de 25 à 47 m | Loi de largeur d'une bande (points `s → largeur`) indépendante des changements de profil des autres bandes (« lois » du schéma, au format de description) |
