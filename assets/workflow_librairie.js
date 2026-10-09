export const meta = {
  name: 'librairie-graphique',
  description: 'Librairie graphique du simulateur (Meylan) : inventaire des besoins sur photos, cahier des charges vérifié (panneaux/feux, matériaux CC0, mobilier, bordures, végétation, CARLA) pour fabrication sur le PC',
  phases: [
    { title: 'Inventaire', detail: 'besoins de la scène, vérifiés sur photos 1000x1000' },
    { title: 'Fabrication', detail: '3 lots de préparation en parallèle' },
    { title: 'Verify', detail: 'contrôle visuel vs photos réelles + contrôle normatif/technique' },
    { title: 'Fix', detail: 'corrections et catalogue final' },
  ],
}

const ROOT = '/home/user/ClaudeCode_RoadCreation'
const SCR = '/tmp/claude-0/-home-user-ClaudeCode-RoadCreation/86d2357b-8d3a-5e9d-b8d8-a3aa44c66205/scratchpad'
const A = args || {}

const COMMON = `CONTEXTE — simulateur ADAS de Meylan (Isère), carrefour « Paquet Jardin » d'abord (avenue de Verdun RD1090 / chemin de la Revirée / avenue du Vercors), état octobre 2026. Chaîne : couches 3D -> USD -> Houdini 22 -> Unreal Engine 5.8. L'utilisateur veut une LIBRAIRIE GRAPHIQUE (static meshes, matériaux, textures) la plus réaliste et conforme au réel français possible ; il a le dépôt CARLA sur son PC ; on peut aussi fabriquer nous-mêmes et télécharger d'autres sources libres.
LIS D'ABORD (Read) : ${ROOT}/assets/CONVENTIONS.md (arborescence, règles d'assets : mètres, Z-up, pivot au pied, face avant +Y, noms, budgets, licences, QA) et ${ROOT}/recon/CONVENTIONS.md.
DONNÉES : photos de rue Panoramax du site ${ROOT}/data/raw/panoramax/paquet_jardin/ (<id>_hd.jpg + <id>_hd.json : date, azimut, projection flat/équirectangulaire, position) et leurs TUILES 1000x1000 natives dans ${ROOT}/data/raw/panoramax/paquet_jardin/tiles/<id>_hd/<id>_hd_rXX_cYY.jpg (204 photos, 2020-2026) ; index géographique ${ROOT}/data/sites/paquet_jardin/panoramax_pictures.geojson ; annotations automatiques de panneaux Panoramax (commune) ${ROOT}/data/raw/panoramax/meylan_panoramax_raw.ndjson.gz ; OSM du site ${ROOT}/data/sites/paquet_jardin/vector/osm_*.geojson (road_signs, crossings, barriers, public_transport, street_lamps...) ; inventaire des arbres de la Métropole ${ROOT}/data/context/arbres_metropole.geojson (genre, essence, hauteur, circonférence, port) ; ortho 5 cm ${ROOT}/data/sites/paquet_jardin/ortho5cm_2022/ ; analyses ${ROOT}/analysis/paquet_jardin/observations_initiales/*.json (constats sur le mobilier, les feux, les matériaux de surface et leur usure) ; atelier objets en cours : ${ROOT}/recon/out/paquet_jardin/objets/ (si présent).
OUTILS : Python (numpy, trimesh 5, usd-core/pxr 26, PIL, cv2, scikit-image, cairosvg, shapely, pyvista ; pip install possible, ex. manifold3d pour les booléens) ; rendu 3D de contrôle : node ${ROOT}/recon/tools/render3d/render.mjs <fichier.glb> <vues.json> <dossier> (tuiles 1000x1000 ; vues.json = [{"nom","oeil":[x,y,z],"cible":[x,y,z],"fov"}] en repère Z-up ; le glb doit être en Y-up glTF standard : (x, y, z)_Zup -> (x, z, -y)). Réseau : ambientCG (https://ambientcg.com/api/v2/full_json?type=Material&q=...&include=downloadData), Poly Haven (https://api.polyhaven.com/assets?t=textures|models, /files/<id> ; fichiers sur dl.polyhaven.org), Wikimedia Commons (API avec en-tête User-Agent explicite, débit modéré : SVG officiels des panneaux français, domaine public), documentation CARLA https://carla.readthedocs.io (catalogues props/végétation) ; l'API GitHub n'est pas accessible.
IMPÉRATIF VISUEL : toute image que tu analyses est une tuile 1000x1000 px ouverte avec Read (sans redimensionnement) ; c'est TON analyse visuelle qui valide (compare chaque asset aux photos réelles du site).
DISQUE ET DÉPÔT : sources téléchargées volumineuses dans ${ROOT}/data/raw/assets_src/ (non versionné) ; dans assets/lib/ ne garder que des textures 2K max (JPEG q90 pour albédo/rugosité/AO, PNG pour normal/opacité), budget total versionné de la librairie <= 250 Mo ; temporaires dans ${SCR}/lib_<lot>/ (supprime les gros fichiers à la fin). Réponds en français.`

const LOT = {
  type: 'object',
  properties: {
    assets: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          nom: { type: 'string' }, categorie: { type: 'string' }, chemin_usda: { type: 'string' },
          source: { type: 'string' }, licence: { type: 'string' }, dimensions: { type: 'string' },
          reference: { type: 'string', description: 'norme / code officiel / photo de référence' },
          triangles: { type: 'number' }, equivalent_carla: { type: 'string' }, qa: { type: 'string' },
        },
        required: ['nom', 'categorie', 'chemin_usda', 'source', 'licence', 'dimensions', 'reference', 'qa'],
      },
    },
    scripts: { type: 'array', items: { type: 'string' } },
    resume: { type: 'string' },
    qa_tuiles_examinees: { type: 'array', items: { type: 'string' } },
    manques: { type: 'string', description: 'besoins non couverts et pourquoi' },
    consignes_pc: { type: 'string', description: 'Houdini 22 / Unreal 5.8 / CARLA : comment utiliser ou améliorer' },
  },
  required: ['assets', 'scripts', 'resume', 'qa_tuiles_examinees', 'manques'],
}
const CHECK = {
  type: 'object',
  properties: {
    ecarts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' }, asset: { type: 'string' },
          gravite: { type: 'string', enum: ['bloquant', 'majeur', 'mineur'] },
          description: { type: 'string' }, preuve: { type: 'string' }, correction_proposee: { type: 'string' },
        },
        required: ['id', 'asset', 'gravite', 'description', 'preuve', 'correction_proposee'],
      },
    },
    points_valides: { type: 'string' },
    verdict_global: { type: 'string' },
  },
  required: ['ecarts', 'points_valides', 'verdict_global'],
}

phase('Inventaire')
const inv = await agent(`${COMMON}

TÂCHE : INVENTAIRE DES BESOINS de la librairie pour le carrefour Paquet Jardin (emprise 300 m) — écris ${ROOT}/assets/catalogue_besoins.json et ${ROOT}/assets/catalogue_besoins.md.
Pour chaque catégorie, liste les TYPES distincts réellement présents (état 2026 quand c'est connu, sinon le plus récent observé), avec quantité estimée, dimensions observées, et 1 à 3 tuiles photo de référence (chemins exacts) que tu as REGARDÉES :
- panneaux : codes français exacts (B14 + valeur, AB3a, AB4, C12, C20a, B21-1/B21a1, J5 balise, M9/M12 panonceaux, D21, CE...), gamme de taille (miniature/petite/normale/grande), support (mât rond Ø, hauteur, fixation), recto/verso ; recoupe OSM road_signs + annotations Panoramax + photos ;
- feux : types R11v (3 feux), R12 (piétons), R13c/R14/R15 (vélos, bus), répétiteurs, présence de boîtiers de comptage/boutons d'appel, potence ou mât, couleur des supports (gris RAL, vert...) ;
- éclairage (modèles de candélabres : hauteur, crosse, lanterne), transport (abri bus modèle, poteau d'arrêt TAG/M réso), mobilier (potelets, barrières, bancs, corbeilles, bornes), bordures (types T1/T2/T3, A2, CS1/CS2/P1, bordures franchissables, abaissés, bandes podotactiles BEV), revêtements (enrobé BBSG ancien/neuf, enrobé coloré piste, béton désactivé, pavés, résine, stabilisé, gazon, noue), peinture (blanc rétroréfléchissant, jaune/ocre des traversées cyclables, vert), arbres (essences de l'inventaire Métropole dans l'emprise : genre/essence, nombre, classes de hauteur et port ; jeunes sujets 2025) ;
- noms d'assets à fabriquer en suivant les règles de nommage de assets/CONVENTIONS.md.
Sois exhaustif mais vérifié (ne liste pas un panneau que tu n'as pas vu ou trouvé dans au moins une source ; indique la confiance).`, { label: 'inventaire', phase: 'Inventaire', schema: {
  type: 'object',
  properties: {
    fichiers: { type: 'array', items: { type: 'string' } },
    resume: { type: 'string' },
    noms_assets: { type: 'array', items: { type: 'string' } },
    tuiles_examinees: { type: 'array', items: { type: 'string' } },
  },
  required: ['fichiers', 'resume', 'noms_assets', 'tuiles_examinees'],
} })
if (!inv) return null

// Décision (utilisateur) : la FABRICATION des meshes et matériaux se fait sur le PC (CARLA, Fab,
// SpeedTree, Houdini 22, Unreal 5.8). Ici : cahier des charges vérifié + entrées prêtes à l'emploi.
const PREP = {
  type: 'object',
  properties: {
    livrables: {
      type: 'array',
      items: {
        type: 'object',
        properties: { fichier: { type: 'string' }, contenu: { type: 'string' }, nb_elements: { type: 'number' } },
        required: ['fichier', 'contenu'],
      },
    },
    scripts: { type: 'array', items: { type: 'string' } },
    resume: { type: 'string' },
    qa_tuiles_examinees: { type: 'array', items: { type: 'string' } },
    manques: { type: 'string', description: 'besoins non couverts et pourquoi' },
    consignes_pc: { type: 'string', description: 'comment fabriquer / obtenir ces assets sur le PC (Houdini 22, Unreal 5.8, CARLA, Fab)' },
  },
  required: ['livrables', 'scripts', 'resume', 'qa_tuiles_examinees', 'manques', 'consignes_pc'],
}
const PC = `DÉCISION DE L'UTILISATEUR : la fabrication finale des static meshes et matériaux se fera sur SON PC (dépôt et contenu CARLA, Fab/Megascans, SpeedTree, Houdini 22, Unreal 5.8). Ton rôle ici : préparer un CAHIER DES CHARGES VÉRIFIÉ et des ENTRÉES PRÊTES À L'EMPLOI (spécifications, cotes, textures de faces, profils, manifestes, scripts à lancer sur le PC). NE FABRIQUE PAS de maillages 3D détaillés. Les noms d'assets suivent assets/CONVENTIONS.md : ce sont les noms des prototypes de la scène USD, que l'utilisateur remplacera par ses assets du même nom.`

const LOTS = [
  { key: 'panneaux_feux', label: 'Panneaux et feux : spécifications et faces officielles',
    mission: `(a) Faces de panneaux : pour chaque code de l'inventaire, télécharge le SVG officiel (Wikimedia Commons, catégorie des panneaux de signalisation routière en France ; en-tête User-Agent explicite, débit modéré) dans ${ROOT}/data/raw/assets_src/svg/, rasterise en PNG RGBA 1024 px (2048 pour les grands formats) dans ${ROOT}/assets/specs/panneaux/faces/<code>.png ; note URL, auteur et licence. (b) ${ROOT}/assets/specs/panneaux.json : par code : désignation, forme, gamme et dimensions (mm, IISR 4e partie), couleurs (arrêté de 1967 / nuancier), rétroréflexion (classe), support (mât Ø, hauteur du bas du panneau), recto/verso, quantité et positions sur le site (L93 si connues), photos de référence. (c) ${ROOT}/assets/specs/feux.json : types (R11v, R12, R13c/R14/R15 si présents, répétiteurs), dimensions (optiques Ø 200/300 mm, caissons, visières, plaques de contraste), supports (mât/potence, hauteurs, couleur RAL), boîtiers et boutons d'appel, quantité par approche, photos de référence. Contrôle : planches 1000x1000 associant chaque face rasterisée à un extrait de photo réelle du même panneau ; regarde-les.` },
  { key: 'materiaux_cc0', label: 'Matériaux de sol et peinture : choix CC0 et script de téléchargement',
    mission: `Pour chaque revêtement de l'inventaire (enrobé ancien patiné de Verdun, enrobé neuf 2025, enrobé coloré/ocre, béton/béton désactivé, pavés, bordures béton/granit, stabilisé, gazon, terre de noue...), choisis sur ambientCG et Poly Haven le jeu PBR CC0 le plus proche VISUELLEMENT des photos du site (télécharge uniquement des aperçus 1K dans ${ROOT}/data/raw/assets_src/apercus/ et compare en planches 1000x1000 : extrait de photo / aperçu). Écris ${ROOT}/assets/manifeste_cc0.json (nom d'asset, source, id, URLs 2K et 4K, licence, tile_m, correction de teinte proposée gain/décalage en Lab pour coller à l'ortho 5 cm et aux photos) et ${ROOT}/assets/telecharger_cc0.py (à lancer sur le PC : télécharge la résolution choisie dans assets/lib/materiaux/<nom>/, vérifie, applique la correction de teinte, écrit <nom>.usda en UsdPreviewSurface et meta.json) ; teste-le ici sur UN matériau en 1K puis supprime la sortie. Peinture routière : ${ROOT}/assets/specs/peinture.json (couleurs blanc/jaune/ocre/vert en sRGB et réflectance, rugosité, recette d'usure 0-3 avec masques procéduraux) et la manière de la réaliser en Material Function Unreal et en COPs Houdini.` },
  { key: 'mobilier_vegetation_carla', label: 'Mobilier, bordures, végétation et correspondances CARLA : spécifications',
    mission: `(1) ${ROOT}/assets/specs/mobilier.json : une fiche par modèle réellement présent (candélabres, abri bus, poteau d'arrêt réseau M, potelets, barrières, bornes, bancs/corbeilles, bandes d'éveil de vigilance) avec cotes estimées sur les photos (échelle par objets connus : bordure, panneau normalisé, personne), couleurs RAL probables, matériaux, quantité, positions si connues, photos de référence. (2) ${ROOT}/assets/specs/bordures.json : profils exacts des bordures françaises (NF EN 1340 / types T1, T2, T3, A2, CS1, CS2, P1, bordures franchissables) en polylignes 2D en mètres prêtes pour un Sweep Houdini, et quel profil où sur le site (d'après photos et hauteurs mesurées : trottoirs 0,10-0,13 m, Vercors 0,16-0,21 m, quai bus 0,20 m, terre-plein 0,15-0,17 m). (3) ${ROOT}/assets/specs/vegetation.json : essences de l'emprise (inventaire Métropole + jeunes sujets 2025) avec nombre, classes de hauteur, port, feuillage saisonnier, et source recommandée (SpeedTree, Fab/Megascans, contenu CARLA, générateur d'arbres SideFX Labs). (4) ${ROOT}/assets/carla_correspondances.json : pour chaque nom d'asset, l'équivalent du contenu CARLA (nom et chemin Unreal /Game/Carla/Static/... d'après la documentation officielle des catalogues CARLA), adéquation (identique / proche / à éviter : feux et panneaux non français) et recommandation (maison / CC0 / CARLA / Fab).` },
]

phase('Fabrication')
const built = await parallel(LOTS.map((L) => () => agent(`${COMMON}

${PC}
LOT « ${L.label} ». Inventaire des besoins (déjà fait) : ${ROOT}/assets/catalogue_besoins.json (lis-le ; résumé : ${inv.resume}).
MISSION : ${L.mission}
Écris uniquement les fichiers de ton lot (et ${ROOT}/assets/qa/${L.key}/ pour tes planches de contrôle, à garder légères : JPEG 1000x1000). Contrôle visuel obligatoire de tes planches.`, { label: `lot:${L.key}`, phase: 'Fabrication', schema: PREP })))

phase('Verify')
const report = JSON.stringify(LOTS.map((L, i) => ({ lot: L.key, resultat: built[i] })), null, 1)
const verify = (lens) => agent(`${COMMON}

${PC}
TU ES VÉRIFICATEUR (${lens === 'visuel' ? 'CONFORMITÉ AU RÉEL SUR PHOTOS' : 'CONFORMITÉ NORMATIVE ET TECHNIQUE'}) du cahier des charges de la librairie graphique. Ne modifie aucun fichier du dépôt (travaille dans ${SCR}/lib_verif_${lens}/).
Inventaire : ${ROOT}/assets/catalogue_besoins.json. Comptes rendus des lots :
${report}
${lens === 'visuel'
    ? `MÉTHODE : re-vérifie sur les tuiles photo 1000x1000 (que tu ouvres toi-même) l'existence et le type de chaque élément de l'inventaire et des spécifications (codes de panneaux, types de feux, modèles de mobilier, essences, revêtements), les faces de panneaux (bonne image pour le bon code), les cotes estimées (ordre de grandeur), le choix des matériaux CC0 (planches). Signale les éléments manquants, en trop ou mal identifiés.`
    : `MÉTHODE : vérifie les dimensions et couleurs par rapport aux normes françaises (IISR, arrêté de 1967, NF EN 1340, NF P98-351), la cohérence des noms avec assets/CONVENTIONS.md, les licences (Wikimedia, CC0), le script telecharger_cc0.py (lis-le, exécute-le en mode test 1K dans ${SCR}/lib_verif_${lens}/ en redirigeant la sortie), la validité JSON, la pertinence des correspondances CARLA (noms réels de la documentation).`}
Sois exigeant et précis (élément, preuve).`, { label: `verify-${lens}`, phase: 'Verify', schema: CHECK })
const [c1, c2] = await parallel([() => verify('visuel'), () => verify('technique')])

phase('Fix')
const fixed = await agent(`${COMMON}

${PC}
TU ES LE CORRECTEUR FINAL du cahier des charges de la librairie graphique. Deux vérificateurs indépendants ont relevé les écarts ci-dessous. Pour chacun : vérifie-le toi-même (tuiles 1000x1000), corrige s'il est fondé (sinon explique). Puis écris ${ROOT}/assets/CAHIER_DES_CHARGES.md : liste complète des assets à obtenir/fabriquer sur le PC (nom exact = nom du prototype dans la scène, catégorie, quantité, cotes, référence normative, photo de référence, source recommandée : maison Houdini / CC0 / CARLA / Fab / SpeedTree, priorité pour l'ADAS : 1 = critique pour la perception (feux, panneaux, marquages, bordures), 2 = important (mobilier proche de la chaussée, arbres d'alignement), 3 = décor), et la procédure pour les livrer (export USD dans assets/lib/<categorie>/<nom>/<nom>.usda, pivot au pied, Z-up, face +Y) ; ainsi que ${ROOT}/assets/README.md (contenu, scripts, licences).
Comptes rendus des lots : ${report}
ÉCARTS (visuel) : ${JSON.stringify(c1?.ecarts || [], null, 1)}
ÉCARTS (technique) : ${JSON.stringify(c2?.ecarts || [], null, 1)}`, { label: 'fix', phase: 'Fix', schema: PREP })

return { inventaire: inv, lots: LOTS.map((L, i) => ({ lot: L.key, resultat: built[i] })), verification_visuelle: c1, verification_technique: c2, final: fixed }
