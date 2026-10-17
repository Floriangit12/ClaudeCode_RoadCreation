# recon/trafic/conception — conception du modèle « conducteur + véhicule » (volet 04, v0.1)

Code de la conception. Le document est
`D:\DocRoute\17_Modele_Vehicules_Conducteurs\04_Conception\MODELE_CONDUCTEUR_VEHICULE.md` ; les paramètres retenus
sont dans `assets/specs/trafic/parametres_modele.json` (voir `assets/specs/trafic/README.md`).

| Fichier | Rôle |
|---|---|
| `verifier_coherence.py` | calculs de cohérence C1 à C6 des choix de conception, avec les lois des volets 01 et 02 : décharge d'une file au feu (IIDM, T de suivi contre 1 800 uvpd/h), équilibre IDM contre IIDM, vitesse en courbe (Bosetti contre Sétra), couplage conducteur-véhicule, adhérence, feu jaune. Écrit `04_Conception/verification/coherence.json`. |
| `construire_parametres_modele.py` | assemble `parametres_modele.json` : recopie sans ressaisie les paramètres des volets 01, 02 et 03, ajoute couches, usages, règles, hypothèses, correspondances (réseaux, modèle de route, SUMO) et cibles de validation. |
| `test_parametres_modele.py` | contrôle de forme, traçabilité vers les volets, fraîcheur et renvois ; code 1 si échec. |

```bash
cd D:/ClaudeCode_RoadCreation
python recon/trafic/conception/verifier_coherence.py           # ≈ 15 s ; --n 20000 --files 300 par défaut
python recon/trafic/conception/construire_parametres_modele.py
python recon/trafic/conception/test_parametres_modele.py
```

Dépendances : Python 3.11 ; numpy et scipy pour `verifier_coherence.py` (il importe
`recon/trafic/conducteurs/modele_conducteurs.py` et `recon/trafic/vehicules/population.py`) ; bibliothèque standard
pour les deux autres scripts. Ces scripts ne lisent que des fichiers produits par le projet : pas de fichier
téléchargé.
