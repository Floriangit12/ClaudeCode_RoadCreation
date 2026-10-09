export const meta = {
  name: 'recon-atelier',
  description: 'Atelier de reconstruction 3D du carrefour Paquet Jardin : construction, double vérification visuelle indépendante, correction',
  phases: [
    { title: 'Build', detail: 'construction de la couche + script reproductible + rendus QA' },
    { title: 'Verify', detail: 'contrôle visuel indépendant + contrôle de cohérence/simulateur' },
    { title: 'Fix', detail: 'application des corrections, nouveaux rendus QA' },
  ],
}

const ROOT = '/home/user/ClaudeCode_RoadCreation'
const SCR = '/tmp/claude-0/-home-user-ClaudeCode-RoadCreation/86d2357b-8d3a-5e9d-b8d8-a3aa44c66205/scratchpad'
const A = args
const OUTDIR = `${ROOT}/recon/out/paquet_jardin/${A.key}`
const STAGE = `${ROOT}/recon/stages/${A.key}.py`

const COMMON = `CONTEXTE — reconstruction 3D du carrefour « Paquet Jardin » à Meylan (avenue de Verdun RD1090 / chemin de la Revirée / avenue du Vercors) pour un simulateur ADAS sous Unreal Engine 5.8, préparé dans Houdini 22. Tout doit être le plus identique possible au réel : chaussée, topologie, voies, manœuvres, marquages, passages piétons, traversées cyclables, végétation. Le mobilier secondaire peut être approximatif.
LIS D'ABORD (Read) :
- ${ROOT}/recon/CONVENTIONS.md (repère, date de l'état modélisé = octobre 2026 après travaux C1 2025, classes, types de marquages, QA) ;
- ${ROOT}/analysis/paquet_jardin/CONTEXT.md (chronologie, conventions des tuiles, échelle d'usure) ;
- ${ROOT}/analysis/paquet_jardin/observations_initiales/etat_actuel.json : description détaillée de la configuration ACTUELLE par branche (voies, largeurs, flèches, lignes d'arrêt, traversées, arrêts de bus) avec un repère u/v (u le long de Verdun vers le NE, v vers le NW ; x = 917279.43 + 0.7071(u − v), y = 6460289.98 + 0.7071(u + v)) — c'est la spécification de référence (en cours de double vérification ; si tu trouves une contradiction avec les sources, signale-la) ;
- ${ROOT}/analysis/paquet_jardin/verification/lidar_historique.json : géométrie 3D vérifiée (pentes, dévers, bordures) et historique/projet vérifiés.
OUTILS : ${ROOT}/recon/common_recon.py (repère local, lecture des couches du site en L93, écriture GeoJSON L93, échantillonnage raster, rendus QA qa_tiles() en tuiles 1000x1000 à 5 cm sur l'ortho 2022). Python : numpy, scipy, shapely 2.1, pyproj, rasterio, geopandas, cv2, PIL, laspy[lazrs], trimesh, mapbox_earcut, triangle, usd-core (pxr), scenariogeneration, pymupdf.
DONNÉES DU SITE (${ROOT}/data/sites/paquet_jardin/) : vector/ (osm_*, bdtopo_*, gam_* : levés topo GAM = état APRÈS travaux au cœur, état ancien ailleurs ; PCRS vecteur 2019), ortho5cm_2022/ (tuiles 50 m, nom = coin bas-gauche), plan_projet_2025/ (plan_L93.tif à géotransformation tournée + tuiles natives), etat_2026/ (levés GAM en L93), lidar/ (tuiles 15/25 cm), marquages/ (carte de contraste 2022 et indice par marquage GAM), panoramax_pictures.geojson. Bruts : ${ROOT}/data/raw/lidar/paquet_jardin/*.tif (MNT, MNS, hauteur, intensité, pente — GeoTIFF float L93), ${ROOT}/data/raw/lidar/npl/LHD_FXX_0917_6461_PTS_LAMB93_IGN69.copc.laz (nuage classé 2021), ${ROOT}/data/raw/lidar/mnh/ (MNH 50 cm), ${ROOT}/data/raw/panoramax/paquet_jardin/ (photos HD + tuiles), ${ROOT}/data/raw/pcrs5cm/dalles/ (GeoTIFF 5 cm), ${ROOT}/data/vector_gz/ et ${ROOT}/data/context/.
IMPÉRATIF VISUEL : toutes les images à analyser sont des tuiles 1000x1000 px que tu ouvres avec l'outil Read, sans redimensionnement. Tu dois toi-même REGARDER les rendus de contrôle et les sources : c'est ton analyse visuelle qui valide.
Fichiers temporaires : ${SCR}/recon_${A.key}/ (disque limité : garde-les sous 300 Mo et supprime les gros fichiers intermédiaires à la fin). Géométrie « état actuel » déjà extraite par l'analyse : ${ROOT}/analysis/paquet_jardin/etat_actuel_agent.geojson (à vérifier, non certifiée). Annotations de panneaux Panoramax (détection automatique) : ${ROOT}/data/raw/panoramax/meylan_panoramax_raw.ndjson.gz. Réponds en français.`

const RESULT = {
  type: 'object',
  properties: {
    fichiers_produits: { type: 'array', items: { type: 'string' } },
    script: { type: 'string' },
    resume: { type: 'string' },
    comptes: { type: 'string', description: 'nombre d objets par type/classe' },
    sources_utilisees: { type: 'string' },
    qa_tuiles_examinees: { type: 'array', items: { type: 'string' } },
    ecarts_connus: { type: 'string' },
    consignes_houdini_unreal: { type: 'string', description: 'comment utiliser ces sorties dans Houdini 22 / UE 5.8' },
  },
  required: ['fichiers_produits', 'script', 'resume', 'comptes', 'qa_tuiles_examinees', 'ecarts_connus'],
}
const CHECK = {
  type: 'object',
  properties: {
    ecarts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          gravite: { type: 'string', enum: ['bloquant', 'majeur', 'mineur'] },
          description: { type: 'string' },
          localisation: { type: 'string' },
          preuve: { type: 'string', description: 'tuile/rendu/source qui le montre' },
          correction_proposee: { type: 'string' },
        },
        required: ['id', 'gravite', 'description', 'localisation', 'preuve', 'correction_proposee'],
      },
    },
    points_valides: { type: 'string' },
    verdict_global: { type: 'string' },
  },
  required: ['ecarts', 'points_valides', 'verdict_global'],
}

phase('Build')
const built = await agent(`${COMMON}

ATELIER « ${A.label} ».
MISSION :
${A.mission}

LIVRABLES OBLIGATOIRES :
- un script Python reproductible ${STAGE} (exécutable depuis la racine du dépôt : python3 recon/stages/${A.key}.py) qui produit toutes les sorties dans ${OUTDIR}/ ;
- les sorties dans ${OUTDIR}/ ;
- des rendus de contrôle (QA) en tuiles 1000x1000 à 5 cm dans ${OUTDIR}/qa/ couvrant au minimum le cœur (tuiles 917200..917300 x 6460200..6460300) et chaque branche, que tu examines toi-même (Read) en les comparant à l'ortho, au plan projet (au cœur) et si utile aux photos Panoramax ; corrige jusqu'à ce que ce soit juste.
Tu peux modifier uniquement recon/stages/${A.key}.py et ${OUTDIR}/ (ne touche à rien d'autre dans le dépôt).`, { label: `build:${A.key}`, phase: 'Build', schema: RESULT })
if (!built) return null

phase('Verify')
const verify = (lens) => agent(`${COMMON}

TU ES VÉRIFICATEUR (${lens === 'visuel' ? 'CONTRÔLE VISUEL INDÉPENDANT' : 'CONTRÔLE DE COHÉRENCE ET D\'APTITUDE SIMULATEUR'}) de l'atelier « ${A.label} ». Ne modifie aucun fichier du dépôt (tu peux écrire dans ${SCR}/recon_${A.key}_verif_${lens}/).
Mission de l'atelier : ${A.mission}
Compte rendu du constructeur :
${JSON.stringify(built, null, 1)}

${lens === 'visuel'
    ? `MÉTHODE : produis TES PROPRES rendus de contrôle (tuiles 1000x1000 à 5 cm) des sorties sur l'ortho 2022, sur le plan projet géoréférencé (au cœur) et sur les levés GAM, et regarde-les toutes une par une (Read), branche par branche, en comparant aux sources ; ouvre aussi 2 à 4 photos Panoramax pertinentes (tuiles 1000 px). Liste chaque écart (élément manquant, en trop, mal placé > 0,3 m, mauvaise classe/type/couleur, mauvaise usure, état 2022 au lieu de 2026...).`
    : `MÉTHODE : ${A.verifyHints || ''} Vérifie la validité technique (géométries valides, fermées, sans trous/chevauchements non voulus, unités, repère, attributs complets, cohérence avec les autres couches si elles existent dans ${ROOT}/recon/out/paquet_jardin/), la conformité aux normes françaises quand c'est pertinent (IISR 7e partie pour les marquages ; dimensions usuelles), et l'aptitude à l'usage dans Houdini 22 / Unreal 5.8 / un simulateur ADAS. Fais tourner le script ${STAGE} pour vérifier qu'il est reproductible (dans une copie temporaire si besoin). Regarde au moins 6 rendus QA.`}
Sois exigeant et précis (positions L93 ou u/v, preuves).`, { label: `verify-${lens}:${A.key}`, phase: 'Verify', schema: CHECK })

const [c1, c2] = await parallel([() => verify('visuel'), () => verify('coherence')])

phase('Fix')
const ecarts = [...(c1?.ecarts || []), ...(c2?.ecarts || [])]
let fixed = built
if (ecarts.length) {
  fixed = await agent(`${COMMON}

TU ES LE CORRECTEUR de l'atelier « ${A.label} ». Deux vérificateurs indépendants ont relevé les écarts ci-dessous. Pour chacun : vérifie-le toi-même sur les sources (tuiles 1000x1000), corrige le script ${STAGE} et régénère les sorties de ${OUTDIR}/ s'il est fondé, sinon explique pourquoi tu le rejettes. Régénère les rendus QA et regarde-les. Tu peux modifier uniquement recon/stages/${A.key}.py et ${OUTDIR}/.
Mission : ${A.mission}
Compte rendu initial : ${JSON.stringify(built, null, 1)}
ÉCARTS (vérificateur visuel) : ${JSON.stringify(c1?.ecarts || [], null, 1)}
ÉCARTS (vérificateur cohérence) : ${JSON.stringify(c2?.ecarts || [], null, 1)}
Dans « ecarts_connus », liste ce qui reste non corrigé et pourquoi.`, { label: `fix:${A.key}`, phase: 'Fix', schema: RESULT }) || built
}
return { atelier: A.key, label: A.label, construction: built, verification_visuelle: c1, verification_coherence: c2, resultat_final: fixed }
