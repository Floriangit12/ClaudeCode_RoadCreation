# Prompts à donner à Claude Code sur le PC

Mode d'emploi : installe Claude Code sur le PC (application de bureau ou ligne de commande).
Ouvre-le **dans le dossier du dépôt cloné** (`claudecode_roadcreation`), puis colle les prompts
**un par un, dans l'ordre**, en attendant la fin de chacun. Chaque prompt est autonome.

Si le dépôt n'est pas encore cloné, commence par :
```
git clone https://github.com/floriangit12/claudecode_roadcreation.git
cd claudecode_roadcreation
git checkout claude/adas-simulator-meylan-i6fdvn
```

---

## Prompt 1 — Mise en place et chargement dans Houdini 22

```
Contexte : ce dépôt contient la reconstruction 3D du carrefour « Paquet Jardin » à Meylan (état octobre 2026) pour un simulateur ADAS. Le paquet est dans recon/out/paquet_jardin/package/ : scène USD paquet_jardin_2026.usda (mètres, Z vers le haut, origine Lambert-93 917279.43 / 6460289.98, altitude 216.30 m), OpenDRIVE paquet_jardin_2026.xodr, textures/, donnees/, et les guides GUIDE_PC.md et PROMPTS_PC.md. Lis d'abord GUIDE_PC.md.

Tâche :
1. Vérifie que la branche claude/adas-simulator-meylan-i6fdvn est à jour (git pull).
2. Trouve Houdini 22 sur ce PC (hython.exe, husk.exe ; ex. C:\Program Files\Side Effects Software\Houdini 22.*\bin\). Si tu ne le trouves pas, demande-moi le chemin.
3. Avec hython, ouvre la scène USD en LOPs avec le script recon/out/paquet_jardin/package/houdini/charger_paquet_jardin.py. Le script a été écrit sans Houdini sous la main : corrige-le si un nom de nœud ou de paramètre diffère en Houdini 22, et garde les corrections dans recon/package_src/houdini/. Sauve un fichier recon/pc/houdini/paquet_jardin.hip.
4. Fais un rendu Karma de contrôle (husk) depuis 4 caméras que tu ajoutes dans une couche à part recon/pc/houdini/cameras.usda, sans toucher au paquet : vue d'ensemble depuis le sud à 60 m, conducteur à 1,3 m sur Verdun SO vers le carrefour, piéton sur la nouvelle traversée SO, conducteur sur le Vercors. Images 1000x1000 en PNG dans recon/pc/rendus/v1/.
5. Regarde chaque image toi-même et vérifie : scène debout (Z-up bien interprété), matériaux présents, rien de noir, de manquant ou de flottant. Corrige si besoin (option ROTATION_SOLARIS du script, unités).
6. Commite et pousse tes changements sur la même branche (git add recon/pc recon/package_src ; message clair en français).
Réponds en français avec un court bilan et les images produites.
```

---

## Prompt 2 — Look-dev réaliste du sol et des marquages (Karma / MaterialX)

```
Contexte : scène USD recon/out/paquet_jardin/package/paquet_jardin_2026.usda, déjà chargée dans recon/pc/houdini/paquet_jardin.hip (prompt précédent). L'objectif est un sol le plus fidèle et réaliste possible, pas une précision au centimètre : chaussée, trottoirs, bordures, peinture usée, herbe.

Ingrédients déjà prêts :
- couleur réelle du site : textures/albedo_macro_8192.jpg sur la primvar UV « st » (0-1 sur l'emprise). En v1, c'est l'ortho 2022 brute ; la v2 l'ortho nettoyée.
- grain : matériaux CC0 choisis et vérifiés sur photos dans assets/manifeste_cc0.json (ex. Asphalt031 enrobé ancien, Asphalt033 enrobé neuf 2025, Concrete037 bordures, Grass004 gazon), téléchargeables avec python assets/telecharger_cc0.py, en UV « st1 » (mètres) avec la taille de tuile tile_m du manifeste.
- peinture : assets/specs/peinture.json (couleurs, réflectance, rugosité, recette d'usure 0-3/F). Les meshes /World/Marquages/* portent les primvars usure, couverture et type.
- classes de sol : un mesh par classe sous /World/Voirie et /World/Terrain (chaussee, chaussee_2025, trottoir, ilot, quai_bus, piste_cyclable, parking, espace_vert, terre_plein_vegetal...) ; faces verticales des bordures sous /World/Bordures.

Tâche :
1. Télécharge les matériaux CC0 de priorité 1 et 2 (python assets/telecharger_cc0.py, en 2K).
2. Dans Houdini 22, crée une Material Library MaterialX (mtlxstandard_surface) avec, pour chaque classe :
   couleur = macro (st) × (détail / moyenne floue du détail), pour garder la teinte réelle du site avec le grain du CC0 ;
   rugosité et normale du détail (st1) ; enrobé 2025 plus sombre et homogène ;
   peinture avec manques et salissure procéduraux selon « usure » et « couverture ».
   Mets tout cela dans une couche séparée recon/pc/houdini/lookdev.usda (overrides de matériaux), pour que les mises à jour du paquet ne l'écrasent pas.
3. Rends les 4 vues du prompt 1 avec Karma, plus 3 vues proches au ras du sol (1,3 m, focale 35 mm) sur l'enrobé, une bordure et un passage piéton, dans recon/pc/rendus/lookdev_vN/. Compare-les à de vraies photos du site : télécharge quelques photos Panoramax récentes listées dans data/sites/paquet_jardin/panoramax_pictures.geojson (champ « hd » ; 2025-05-18 et 2026-07-28 de préférence). Ajuste couleur, échelle du grain, brillance et usure jusqu'à ce que ce soit crédible ; décris ce que tu as changé à chaque itération.
4. Commite et pousse (recon/pc/, en excluant les gros téléchargements CC0 : ajoute-les à .gitignore).
Réponds en français avec le bilan et les meilleures images.
```

---

## Prompt 3 — Import dans Unreal Engine 5.8

```
Contexte : paquet USD recon/out/paquet_jardin/package/ (lis GUIDE_PC.md, section 3) et look-dev Houdini dans recon/pc/houdini/lookdev.usda.

Tâche :
1. Trouve Unreal Engine 5.8 (UnrealEditor.exe, UnrealEditor-Cmd.exe). Si aucun projet n'existe, demande-moi de créer un projet vide « MeylanADAS » depuis le launcher, puis continue.
2. Active les plugins USD Importer et Python Editor Script Plugin (et Georeferencing) dans le .uproject.
3. Importe la scène avec recon/out/paquet_jardin/package/unreal/importer_paquet_jardin.py, d'abord en MODE="stage" pour vérifier, puis en MODE="import" dans /Game/Meylan/PaquetJardin. Le script a été écrit sans Unreal sous la main : corrige-le si l'API Python de la 5.8 diffère, et garde les corrections dans recon/package_src/unreal/.
4. Recrée dans Unreal l'équivalent du look-dev Houdini : un matériau maître sol (macro UV0 × détail CC0 UV1 tuilé, rugosité, normale) et un matériau peinture avec usure, avec des instances par classe affectées aux meshes importés. Fais-le par script Python Unreal (MaterialEditingLibrary), dans recon/pc/unreal/.
5. Ajoute soleil, ciel, atmosphère et brouillard. Prends des captures (HighResShot ou rendu de vue) des 4 vues de contrôle dans recon/pc/rendus/unreal/ et vérifie-les toi-même : échelle 1 m = 100 uu, orientation, matériaux, rien de manquant.
6. Commite et pousse le projet sans les dossiers volumineux (Intermediate, Saved, DerivedDataCache dans .gitignore), plus recon/pc/unreal/ et les captures.
Réponds en français avec le bilan.
```

---

## Prompt 4 — Librairie d'assets (CARLA, CC0, fabrication maison)

```
Contexte : chaque objet de la scène (feux, panneaux, candélabres, abris, arbres...) est un prototype USD nommé comme l'asset final, avec un volume provisoire. Les besoins vérifiés sur photos sont dans assets/catalogue_besoins.md et .json (et assets/CAHIER_DES_CHARGES.md s'il existe). Les spécifications sont dans assets/specs/ : panneaux.json avec faces officielles PNG, feux.json, mobilier.json, bordures.json avec profils pour Sweep, vegetation.json. Les équivalents CARLA sont dans assets/carla_correspondances.json (outil assets/carla_resoudre_chemins.py). Conventions : assets/CONVENTIONS.md (mètres, Z vers le haut, pivot au pied, face avant vers +Y).

Tâche :
1. Trouve le dépôt et le contenu CARLA sur ce PC (demande-moi le chemin si besoin). Vérifie quelle version d'Unreal il utilise : les assets d'une version plus ancienne doivent être ouverts et migrés depuis l'éditeur CARLA. Résous les chemins réels avec assets/carla_resoudre_chemins.py.
2. Pour chaque asset de priorité 1 (feux R11v/R12, panneaux, candélabres, abri bus, poteau d'arrêt, bordures), choisis la meilleure source : fabrication maison dans Houdini d'après assets/specs (aux cotes réglementaires, faces officielles des panneaux), CARLA si l'objet est identique, ou Fab/Megascans. Pour les arbres : SpeedTree, Fab ou le générateur d'arbres de SideFX Labs, selon assets/specs/vegetation.json.
3. Exporte chaque asset en USD dans assets/lib/<categorie>/<nom>/<nom>.usda (nom exact du prototype, pivot au pied, face +Y, Z-up, mètres), avec meta.json (source, licence, dimensions).
4. Lance hython recon/out/paquet_jardin/package/substituer_assets.py --librairie assets/lib et vérifie par des rendus Karma 1000x1000 que chaque objet est bien orienté, à la bonne taille et à la bonne place, en comparant aux photos Panoramax.
5. Commite et pousse assets/lib (sans les assets CARLA ou Fab, qui ne sont pas redistribuables : chemins seulement dans meta.json) et les rendus de contrôle.
Réponds en français avec la liste des assets faits, ceux restant provisoires, et les images.
```

---

## Prompt 5 — Mettre à jour quand une nouvelle version du paquet arrive (v2...)

```
Une nouvelle version du paquet Paquet Jardin a été poussée sur la branche claude/adas-simulator-meylan-i6fdvn. Fais git pull, lis la section « Version du paquet » de recon/out/paquet_jardin/package/GUIDE_PC.md pour voir ce qui a changé, puis recharge la scène :
- dans Houdini : recharge le Sublayer LOP de paquet_jardin.hip ; le look-dev recon/pc/houdini/lookdev.usda doit continuer à s'appliquer (les noms de prims ne changent pas) ; adapte-le pour exploiter les nouvelles cartes (masques d'usure, fissures, rapiéçages s'ils existent dans textures/) ;
- dans Unreal : réimporte (ou recharge le UsdStageActor) et réaffecte les matériaux ;
- relance substituer_assets.py si la librairie existe.
Refais les rendus de contrôle et compare-les à la version précédente et aux photos réelles. Commite et pousse. Réponds en français avec le bilan.
```
