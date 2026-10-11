# recon/pcg/controle : vérification automatique des règles de conception

Ce dossier contrôle la description v2 et la fabrication Houdini (`fabrique_hda`) contre la base de règles
`assets/specs/regles_conception.json`. Il ne modifie aucune autre donnée : il écrit seulement dans
`recon/out/paquet_jardin/v2/controle/` et dans `recon/pc/rendus/v2_site/`.

```
python recon/pcg/controle/verifier_regles.py                      # toutes les règles (≈ 1 min 30) -> rapport
python recon/pcg/controle/verifier_regles.py --regles GA-TRO-004,VAL-SOL-009 --chrono   # quelques règles, résumé console
python recon/pcg/controle/verifier_regles.py --description recon/out/paquet_jardin/v2/description/resolue/base
hython recon/pcg/controle/extraire_fabrication.py [--forcer]      # cache numpy des USD (lancé seul si une source change)
hython recon/pcg/controle/rendre_controle.py [--vues a,b] [--res 1400] [--spp 64]       # rendus Karma XPU
```

## Modules

| Module | Rôle |
|---|---|
| `verifier_regles.py` | Pilote : charge les règles, lance un contrôle par règle « verifier » (principale ou secondaire) et par règle « contraindre » mesurable, écrit `rapport_regles.json` et `RAPPORT_REGLES.md` |
| `ctl_commun.py` | Contexte (description, nivellement, OpenDRIVE, levés GAM, mobilier, fabrication), géométrie numpy, requêtes verticales exactes sur les triangles fabriqués, rasters de la grille de 0,10 m, objet `Resultat` |
| `ctl_sol.py` | Sol, bordures, abaissés, BEV, cheminements : TQ-SOL-*, VAL-SOL-009, VAL-KRB-005, GA-TRO-*, GA-RES-*, GA-BOR-*, GA-ABA-*, GA-BEV-*, TQ-BOR-*, TQ-PCG-001 |
| `ctl_marquages.py` | Marquages : MQ-*, INF-FLE-*, VAL-LIG-002, VAL-ZEB-003, VAL-FLE-001, MQ-DET-010, TQ-MQG-*, TQ-VAL-002, TQ-MQR-005 |
| `ctl_reseau.py` | Réseau et carrefour : VAL-XOD-008, VAL-JCT-010, VAL-COV-006, largeurs, rayons, visibilité, quais, îlots |
| `ctl_detection.py` | Détection, fusion, preuve image : DET-*, FUS-*, VAL-IMG-007 (top-hat de l'ortho 2022) |
| `ctl_tq.py` | Chaîne d'export mesurable dans les fichiers : TQ-REF-003, TQ-OMB-002, TQ-MQR-001 |
| `rapport.py` | Raisons des règles non contrôlées, mise en forme Markdown |
| `extraire_fabrication.py` | hython : USD -> `controle/cache/<couche>.npz` (triangles, entités, matériaux, normales du sol) |
| `rendre_controle.py` | hython : scène de contrôle (v2 seule, ciel, soleil), caméras, rendus husk et développement PNG |

## Conventions

- Une règle = un contrôle décoré `@regle(id, cible, sévérité, méthode, statut, limites)`. Chaque cas testé est
  conforme ou non ; un cas non conforme porte l'entité, les coordonnées locales et Lambert-93, la valeur, le
  seuil, le détail et l'écart relatif au seuil (classement des pires cas).
- Sévérités : `bloquant` (défaut visible ou géométrie cassée), `majeur` (écart à une règle réglementaire ou de
  sécurité), `mineur` (écart de pratique ou de précision), `info` (écart admis ou choix d'organisation).
- Statut : `implemente`, `partiel` (une partie de la règle est mesurable ; voir `limites`), `non_implemente`
  (raison dans `rapport.NON_IMPLEMENTEES`).
- Grille de contrôle : celle du nivellement (0,10 m, local [-150, 150]²) ; le sol fabriqué y est échantillonné par
  requête verticale exacte (cache `sol_grille.npz`, clé = sha256 de `sol.usdc`).
- Déterminisme : tri fixe, arrondis fixes, aucun horodatage ; deux exécutions donnent des rapports identiques à
  l'octet.
