# Besoins du générateur relevés sur `auto_a41_echangeur_meylan_est` (lot SITES, comparaison v2, 18/10/2026)

*Ce que le PCG ne sait pas faire, ou fait mal, pour les « centres » de l'échangeur 26. Le code partagé n'a pas été
modifié. Clés de vues : `recon/out/generateur/meylan_auto_a41_echangeur_meylan_est/comparaison/<fenêtre>/selection.json`
(aucune image ici) ; compréhension : `COMPREHENSION.md`.*

| # | Élément (zone) | Vue, preuve | Règle, renvoi | Ce qui manque |
|---|---|---|---|---|
| A41E-1 | **Musoir de la sortie 26** (côté ← de l'A41 : chevrons x ≈ 27-88, nez à x ≈ 27) | `site_ign2024_t04`, `contours_site_ign_t06` ; `vue_6714e161_-022` | RF-MQ-MUS-01, RF-MQ-DEC-01 ; FORMAT § 15.6 ; B2 | Même limite que A41O-2 : `bretelles` ne fabrique un musoir que du côté → d'une chaussée principale. Contournement : divergence et voie de décélération à la bonne abscisse, **zone hachurée à la place de la BAU** de s = 240,8 à 305,9, bretelle qui part de la voie de décélération. Pas de chevrons « 2 pour 1 », pas de J14a, pas de terre-plein latéral en saillie. |
| A41E-2 | **Entrée de Meylan-Est sur la branche N87** : arrivée en boucle serrée | `contours_site_ign_t06` | VSA 90/110 p. 38 (obliquité 1/33-1/20) | Décrite en `bretelles` (type entrée) ; la fin de la bretelle a dû être retracée tangente (obliquité 0,046) pour passer le contrôle ; la courbe réelle arrive un peu plus franchement (≈ 0,07 sur les 20 derniers mètres). Le musoir est donc plus long au modèle que sur l'ortho (à juger sur le rendu de l'itération 1). |
| A41E-3 | **Sortie de la branche vers Meylan-Est** : voie de droite de la branche qui court en parallèle depuis le nœud puis s'en sépare vers x ≈ −30 | `site_ign2024_t03`, `contours_site_ign_t09` | B2 | Le départ est au nœud partagé N_A41_BRANCHE_N87 (fin du site voisin) : une voie de décélération ne peut pas commencer dans le site voisin ; la bretelle reste un tronçon parallèle (deux glissières et deux bermes superposées sur ≈ 90 m). |
| A41E-4 | **Pont de l'échangeur** (tablier sur piles, à x ≈ −115) | `site_ign2024_t03` | B5 ; RF-GV-PON-* | Ouvrage non fabriqué (déjà ND-2 sur le nœud). |
| A41E-5 | **Double glissière** entre l'A41 et la branche (deux files séparées par une bande d'herbe) | `vue_6ae77446_-030` | B3 | Une file par limite de profil ; la seconde file appartient au tronçon voisin (bermes superposées). |
