export const meta = {
  name: 'paquet-jardin-unit-analysis',
  description: 'Une zone (ortho 5 cm) ou une séquence (photos de rue) du carrefour Paquet Jardin : observation, double vérification indépendante, arbitrage',
  phases: [
    { title: 'Observe', detail: 'observation (sautée si déjà faite)' },
    { title: 'Verify', detail: 're-observation + recoupement multi-sources' },
    { title: 'Arbitrate', detail: '3e avis sur les constats contestés' },
  ],
}

const ROOT = '/home/user/ClaudeCode_RoadCreation'
const SCR = '/tmp/claude-0/-home-user-ClaudeCode-RoadCreation/86d2357b-8d3a-5e9d-b8d8-a3aa44c66205/scratchpad'
const PX = `${ROOT}/data/raw/panoramax/paquet_jardin`
const T = (n) => `${ROOT}/data/raw/pcrs5cm/tiles/paquet_jardin/pcrs5cm_${n}.jpg`
const kind = args.kind
const u = args.unit
const prevObs = args.obs || null

const NOTE_GAM = `ATTENTION (vérifié) : au cœur du carrefour, les levés topographiques GAM (gam_topo_sol_*) coïncident exactement avec le plan du projet 2025 : ils décrivent l'état APRÈS travaux, pas celui de 2022. Une différence entre levés GAM et ortho 2022 n'est donc pas une erreur du rapport. Le plan du projet géoréférencé (Lambert-93) est disponible : ${ROOT}/data/sites/paquet_jardin/plan_projet_2025/plan_L93.tif (GeoTIFF à géotransformation tournée ; tuiles 1000 px natives dans plan_projet_2025/tuiles/ avec l'affine L93 de chaque tuile dans index.json).`

const COMMON_ORTHO = `Lis d'abord la fiche de contexte ${ROOT}/analysis/paquet_jardin/CONTEXT.md (Read) : elle donne la localisation, la chronologie (ortho 5 cm = 10 mai 2022, AVANT les travaux de 2025), les conventions de coordonnées des tuiles et l'échelle d'usure 0/1/2/3/F.
Carte d'assemblage des tuiles (vue d'ensemble 350 m, grille et noms des tuiles) : ${ROOT}/analysis/paquet_jardin/carte_assemblage_pcrs.jpg .
Toutes les images sont des tuiles 1000x1000 px : ouvre-les avec l'outil Read telles quelles, sans les redimensionner. Tu peux ouvrir des tuiles voisines (même dossier, nommées par le coin bas-gauche, pas de 50 m) si un objet déborde.
Tu peux exécuter du python (numpy, PIL, shapely, pyproj, rasterio, geopandas, laspy installés) pour mesurer (ex. compter des pixels, mesurer une largeur de voie en pixels × 0.05 m, lire des vecteurs). Écris tout fichier temporaire dans ${SCR}/wf_ortho/ . Ne modifie RIEN dans le dépôt git.
Réponds en français.`

const COMMON_STREET = `Lis d'abord la fiche de contexte ${ROOT}/analysis/paquet_jardin/CONTEXT.md (Read) : localisation, chronologie (travaux C1 en 2025), échelle d'usure 0/1/2/3/F.
Les photos sont découpées en tuiles 1000x1000 px dans ${PX}/tiles/<photo>_hd/ (fichiers <photo>_hd_rRR_cCC.jpg ; index.json donne la boîte pixel de chaque tuile dans la photo d'origine). Les métadonnées de chaque photo sont dans ${PX}/<photo>_hd.json (azimuth = cap au centre horizontal de l'image, projection equirectangular = 360° ; dist_site_m, dx_e_m, dy_n_m = position relative au centre du carrefour en mètres est/nord).
Pour une photo 360° (5760x2880), le centre horizontal (x=2880) regarde l'azimut indiqué ; x=0 et x=5760 regardent vers l'arrière ; la chaussée est dans la moitié basse (rangées r01 et r02) ; le bas extrême est le toit/capot du véhicule ou le porteur. Pour une photo « flat », toute l'image regarde vers l'azimut.
Ouvre les tuiles avec l'outil Read, telles quelles (aucun redimensionnement). Choisis les tuiles utiles (chaussée, carrefour) — inutile d'ouvrir le ciel.
Carte d'assemblage aérienne (pour te repérer) : ${ROOT}/analysis/paquet_jardin/carte_assemblage_pcrs.jpg ; ortho 5 cm 2022 : ${ROOT}/data/raw/pcrs5cm/tiles/paquet_jardin/ (tuiles 50 m nommées par le coin bas-gauche L93).
Tu peux exécuter du python. Fichiers temporaires : ${SCR}/wf_street/ . Ne modifie RIEN dans le dépôt git. Réponds en français.`

const COMMON = kind === 'ortho' ? COMMON_ORTHO : COMMON_STREET

const CAT_O = ['marquage_longitudinal', 'marquage_transversal', 'fleche_symbole', 'passage_pieton', 'amenagement_cyclable', 'arret_bus', 'bordure_ilot_trottoir', 'revetement_texture', 'degradation', 'assainissement_reseaux', 'signalisation_verticale_feux', 'geometrie_voies', 'mobilier_vegetation', 'autre']
const CAT_S = [...CAT_O, 'travaux_provisoire']
const CLAIM = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    categorie: { type: 'string', enum: kind === 'ortho' ? CAT_O : CAT_S },
    description: { type: 'string' },
    localisation: { type: 'string' },
    preuve: { type: 'string' },
    usure: { type: 'string', enum: ['0', '1', '2', '3', 'F', 'NA'] },
    cause_usure: { type: 'string' },
    mesure: { type: 'string' },
    date_source: { type: 'string' },
    confiance: { type: 'string', enum: ['haute', 'moyenne', 'faible'] },
  },
  required: ['id', 'categorie', 'description', 'localisation', 'preuve', 'usure', 'confiance'],
}
const OBS_O = {
  type: 'object',
  properties: {
    zone: { type: 'string' }, tuiles_vues: { type: 'array', items: { type: 'string' } }, constats: { type: 'array', items: CLAIM },
    configuration_voies: { type: 'string' }, revetement_synthese: { type: 'string' }, usure_synthese: { type: 'string' },
    pourquoi_cette_conception: { type: 'string' }, points_adas: { type: 'string' }, incertitudes: { type: 'string' },
  },
  required: ['zone', 'tuiles_vues', 'constats', 'configuration_voies', 'revetement_synthese', 'usure_synthese', 'points_adas'],
}
const OBS_S = {
  type: 'object',
  properties: {
    sequence: { type: 'string' }, photos_et_tuiles_vues: { type: 'array', items: { type: 'string' } }, constats: { type: 'array', items: CLAIM },
    configuration_voies_vue_du_sol: { type: 'string' }, signalisation_verticale_et_feux: { type: 'string' }, revetement_et_usure_synthese: { type: 'string' },
    eclairage_ombres_meteo: { type: 'string' }, differences_avec_ortho_2022: { type: 'string' }, points_adas: { type: 'string' }, incertitudes: { type: 'string' },
  },
  required: ['sequence', 'photos_et_tuiles_vues', 'constats', 'configuration_voies_vue_du_sol', 'signalisation_verticale_et_feux', 'revetement_et_usure_synthese', 'differences_avec_ortho_2022', 'points_adas'],
}
const VERDICT = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, verdict: { type: 'string', enum: ['confirme', 'corrige', 'refute', 'incertain'] }, correction: { type: 'string' }, usure_verifiee: { type: 'string', enum: ['0', '1', '2', '3', 'F', 'NA'] }, justification: { type: 'string' } }, required: ['id', 'verdict', 'justification'] } },
    oublis: { type: 'array', items: { type: 'string' } },
    fiabilite_globale: { type: 'string' },
  },
  required: ['verdicts', 'oublis', 'fiabilite_globale'],
}
const ARB = {
  type: 'object',
  properties: {
    arbitrages: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, decision: { type: 'string', enum: ['retenu', 'retenu_corrige', 'rejete', 'incertain'] }, texte_final: { type: 'string' }, usure_finale: { type: 'string', enum: ['0', '1', '2', '3', 'F', 'NA'] }, justification: { type: 'string' } }, required: ['id', 'decision', 'texte_final', 'justification'] } },
    oublis_valides: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, localisation: { type: 'string' }, usure: { type: 'string' }, preuve: { type: 'string' } }, required: ['description', 'preuve'] } },
  },
  required: ['arbitrages', 'oublis_valides'],
}

const observePrompt = kind === 'ortho' ? `${COMMON}

TA MISSION : analyse très détaillée de la CHAUSSÉE de la zone « ${u.label} » sur l'ortho PCRS 5 cm (2022).
Tuiles à analyser (ouvre-les TOUTES) :
${(u.tiles || []).map(t => '- ' + T(t)).join('\n')}

Inventorie, avec position et preuve :
1. Marquages longitudinaux (lignes continues/discontinues, type T1/T2/T3 si identifiable, largeur, rive, axe), transversaux (lignes d'effet des feux, cédez-le-passage, stop), flèches de présélection, symboles (vélo, bus, « 30 », losanges...), zébras/hachures, marquage jaune (arrêt bus en zigzag, provisoire de chantier).
2. Passages piétons (nombre de bandes, largeur, état), traversées cyclables (couleur, damiers/blocs), refuges, abaissés de trottoir, bandes podotactiles.
3. Aménagements cyclables (piste, bande, sas vélo), arrêts de bus (quais, marquage).
4. Bordures, îlots (forme, matériau), terre-pleins, trottoirs, séparateurs.
5. Revêtement : type (enrobé BBSG, béton bitumineux, pavés...), teinte, texture, granulométrie apparente, ressuage, réparations/patchs, tranchées refermées, fissures (longitudinales, transversales, faïençage), orniérage, nids-de-poule, joints, tampons/regards/avaloirs/grilles.
6. Feux, poteaux, mâts, câbles aériens et leurs ombres, arbres et ombres.
Pour CHAQUE marquage, donne l'usure (0/1/2/3/F) et la cause probable (ex. usure dans les traces de roues, girations des poids lourds, freinage avant la ligne de feux).
Mesure en pixels (×0.05 m) les largeurs de voies et de marquages quand c'est utile.
Explique pourquoi la géométrie est conçue ainsi et ce qui pose problème pour un ADAS (caméra/LiDAR).
Donne des identifiants de constats « ${u.key}-01 », « ${u.key}-02 »...` : `${COMMON}

TA MISSION : analyser depuis le sol la chaussée du carrefour Paquet Jardin avec la séquence Panoramax « ${u.label} ».
Photos (commence par la plus proche du centre) :
${(u.photos || []).map(p => `- ${PX}/${p}_hd.json  → tuiles ${PX}/tiles/${p}_hd/`).join('\n')}

Inventorie avec preuve (photo + tuile) : marquages (type, couleur, usure 0/1/2/3/F et cause), passages piétons et traversées cyclables, flèches et symboles, bordures/îlots/refuges, revêtement (texture, teinte, réparations, fissures, nids-de-poule, ressuage, tranchées), tampons et avaloirs, feux et panneaux, éléments de chantier ou provisoires, végétation et ombres. Décris la configuration des voies telle qu'un conducteur la voit (nombre de voies, flèches, positionnement des lignes de feux).
Compare explicitement avec l'ortho 5 cm de mai 2022 (ouvre les tuiles 5 cm correspondantes) : qu'est-ce qui a changé ? Les marquages ont-ils été refaits ou se sont-ils dégradés ?
Liste les pièges pour un ADAS (marquages effacés, lignes fantômes, marquage jaune provisoire superposé au blanc, contre-jour, ombres de câbles...).
Identifiants de constats : « ${u.key}-01 », « ${u.key}-02 »...`

const verifyPrompt = (obs, lens) => {
  if (kind === 'ortho') {
    return `${COMMON}

TU ES VÉRIFICATEUR (${lens === 'reobs' ? 'RE-OBSERVATION INDÉPENDANTE' : 'RECOUPEMENT MULTI-SOURCES'}). Un premier analyste a produit le rapport ci-dessous pour la zone « ${u.label} ». Ton rôle est de le contrôler de façon critique, constat par constat (verdict confirme / corrige / refute / incertain), puis de lister les oublis importants. Sois exigeant : en cas de doute, ne confirme pas.
${NOTE_GAM}

${lens === 'reobs'
      ? `MÉTHODE : ré-ouvre toi-même chacune des tuiles 5 cm de la zone et vérifie chaque constat (existence, type, position, mesure, usure). Ne te fie pas au rapport : regarde.
Tuiles : ${(u.tiles || []).map(t => T(t)).join(' , ')}`
      : `MÉTHODE : confronte chaque constat à des sources DIFFÉRENTES de l'ortho 5 cm de 2022 :
- carte objective de contraste des marquages (ortho 2022, top-hat, vert = contrasté/neuf, rouge = faible/usé ; tuiles nommées contraste_<X>_<Y>.jpg comme les tuiles 5 cm) : ${ROOT}/data/sites/paquet_jardin/marquages/contraste_5cm/ et statistiques ${ROOT}/data/sites/paquet_jardin/marquages/contraste_par_tuile.json — attention : les bandes ocre ont naturellement un contraste de luminance plus faible, et les bordures/quais béton peuvent apparaître à tort ;
- levés topographiques et PCRS vecteur de la Métropole : ${ROOT}/data/sites/paquet_jardin/vector/gam_*.geojson (WGS84 ; convertis en L93 avec pyproj) — hors cœur du carrefour ils décrivent l'état ancien, au cœur l'état 2025 ;
- LiDAR HD 2021 : intensité rehaussée (marquages) ${ROOT}/data/sites/paquet_jardin/lidar/intensity_enhanced_15cm/ et hauteurs ${ROOT}/data/sites/paquet_jardin/lidar/height_above_ground_15cm/ (tuiles 1000 px à 0.15 m/px ; index.json donne l'emprise L93 de chaque tuile) ;
- ortho IGN 20 cm 2021 et 2024 : ${ROOT}/data/raw/ortho/paquet_jardin/ORTHOIMAGERY_ORTHOPHOTOS2021_20cm/ et ..._2024_20cm/ ;
- photos de rue Panoramax : liste ${ROOT}/data/sites/paquet_jardin/panoramax_pictures.geojson (dx_e_m/dy_n_m = position relative au centre L93 917279.43, 6460289.98 ; azimuth = direction de vue) et tuiles ${ROOT}/data/raw/panoramax/paquet_jardin/tiles/ — choisis 2 à 4 photos pertinentes ;
- OSM 2026 : ${ROOT}/data/sites/paquet_jardin/vector/osm_*.geojson.
Tu peux aussi rouvrir une tuile 5 cm si nécessaire : ${(u.tiles || []).map(t => T(t)).join(' , ')}
Pour l'usure, indique si les autres sources (2021 LiDAR, 2024, photos 2023-2025, carte de contraste) confirment, et note toute évolution temporelle.`}

RAPPORT À VÉRIFIER :
${JSON.stringify(obs, null, 1)}`
  }
  return `${COMMON}

TU ES VÉRIFICATEUR (${lens === 'reobs' ? 'RE-OBSERVATION INDÉPENDANTE' : 'RECOUPEMENT MULTI-SOURCES'}) du rapport ci-dessous sur la séquence « ${u.label} ». Contrôle chaque constat (confirme / corrige / refute / incertain) et liste les oublis importants. Sois exigeant : en cas de doute, ne confirme pas.
${NOTE_GAM}
${lens === 'reobs'
    ? `MÉTHODE : rouvre toi-même les tuiles des photos de la séquence (${(u.photos || []).map(p => `${PX}/tiles/${p}_hd/`).join(' , ')}) et vérifie chaque constat en regardant, sans te fier au rapport. Vérifie notamment que l'orientation (azimut) et donc la branche du carrefour attribuée à chaque objet sont correctes.`
    : `MÉTHODE : confronte chaque constat à d'AUTRES sources : autres séquences Panoramax d'autres dates (liste ${ROOT}/data/sites/paquet_jardin/panoramax_pictures.geojson, tuiles ${PX}/tiles/), ortho 5 cm 2022 (${ROOT}/data/raw/pcrs5cm/tiles/paquet_jardin/), carte de contraste des marquages 2022 (${ROOT}/data/sites/paquet_jardin/marquages/contraste_5cm/), ortho IGN 2024 20 cm (${ROOT}/data/raw/ortho/paquet_jardin/ORTHOIMAGERY_ORTHOPHOTOS2024_20cm/), plan du projet 2025 (${ROOT}/data/raw/docs/tiles/panneau_150dpi/ et plan géoréférencé ci-dessus), levés GAM (${ROOT}/data/sites/paquet_jardin/vector/gam_*.geojson), OSM 2026 (${ROOT}/data/sites/paquet_jardin/vector/osm_*.geojson). Vérifie la cohérence des dates et de l'usure dans le temps (un marquage ne peut pas être « neuf » en 2023 puis « neuf » en 2025 sans réfection, etc.).`}

RAPPORT À VÉRIFIER :
${JSON.stringify(obs, null, 1)}`
}

const srcList = kind === 'ortho'
  ? `tuiles 5 cm : ${(u.tiles || []).map(t => T(t)).join(' , ')} ; et si utile carte de contraste ${ROOT}/data/sites/paquet_jardin/marquages/contraste_5cm/, LiDAR ${ROOT}/data/sites/paquet_jardin/lidar/, ortho 2024 ${ROOT}/data/raw/ortho/paquet_jardin/ORTHOIMAGERY_ORTHOPHOTOS2024_20cm/, Panoramax ${PX}/tiles/, vecteurs ${ROOT}/data/sites/paquet_jardin/vector/`
  : `photos : ${(u.photos || []).map(p => `${PX}/tiles/${p}_hd/`).join(' , ')} ; et si utile ortho 5 cm ${ROOT}/data/raw/pcrs5cm/tiles/paquet_jardin/, autres photos ${PX}/tiles/, plan projet ${ROOT}/data/sites/paquet_jardin/plan_projet_2025/`

phase('Observe')
let obs = prevObs
if (!obs && args.obsPath) {
  // rechargement fidèle d'une observation déjà faite ; contrôle du nombre de constats
  for (let i = 0; i < 3 && !obs; i++) {
    const r = await agent(`Lis le fichier JSON ${args.obsPath} (outil Read, en plusieurs morceaux si nécessaire) et renvoie EXACTEMENT son contenu via la sortie structurée : mêmes champs, TOUS les ${args.nConstats || ''} constats, même texte mot pour mot, sans rien résumer, corriger ni ajouter.`, { label: `load-obs:${u.key}#${i + 1}`, phase: 'Observe', schema: kind === 'ortho' ? OBS_O : OBS_S, effort: 'low' })
    if (r && (r.constats || []).length && (!args.nConstats || r.constats.length === args.nConstats)) obs = r
    else log(`rechargement ${u.key} incomplet (${(r?.constats || []).length} constats), nouvel essai`)
  }
}
if (!obs) obs = await agent(observePrompt, { label: `observe:${u.key}`, phase: 'Observe', schema: kind === 'ortho' ? OBS_O : OBS_S })
if (!obs) return null

phase('Verify')
// réutilise une vérification déjà faite (fichier) si fournie, sinon la lance
const loadV = async (path, n, lab) => {
  for (let i = 0; i < 3; i++) {
    const r = await agent(`Lis le fichier JSON ${path} (outil Read, en plusieurs morceaux si nécessaire) et renvoie EXACTEMENT son contenu via la sortie structurée : TOUS les ${n || ''} verdicts, mêmes champs, même texte mot pour mot, sans rien résumer ni modifier.`, { label: `load-${lab}:${u.key}#${i + 1}`, phase: 'Verify', schema: VERDICT, effort: 'low' })
    if (r && (r.verdicts || []).length && (!n || r.verdicts.length === n)) return r
  }
  return null
}
const [v1, v2] = await parallel([
  async () => (args.v1Path && await loadV(args.v1Path, args.nV1, 'v1')) || agent(verifyPrompt(obs, 'reobs'), { label: `verify-reobs:${u.key}`, phase: 'Verify', schema: VERDICT }),
  async () => (args.v2Path && await loadV(args.v2Path, args.nV2, 'v2')) || agent(verifyPrompt(obs, 'cross'), { label: `verify-cross:${u.key}`, phase: 'Verify', schema: VERDICT }),
])

phase('Arbitrate')
const disputed = (obs.constats || []).filter(c => {
  const a = (v1?.verdicts || []).find(v => v.id === c.id)
  const b = (v2?.verdicts || []).find(v => v.id === c.id)
  return !(a?.verdict === 'confirme' && b?.verdict === 'confirme')
})
const oublis = [...(v1?.oublis || []), ...(v2?.oublis || [])]
let arb = { arbitrages: [], oublis_valides: [] }
if (disputed.length || oublis.length) {
  arb = await agent(`${COMMON}

TU ES ARBITRE (3e vérification) pour « ${u.label} ». Deux vérificateurs indépendants n'ont pas tous deux confirmé les constats ci-dessous et ont signalé des oublis. Regarde toi-même les sources (${srcList}) et tranche chaque cas (retenu / retenu_corrige / rejete / incertain, avec le texte final) ; valide ou rejette chaque oubli.
${NOTE_GAM}

CONSTATS CONTESTÉS (avec les deux avis) :
${JSON.stringify(disputed.map(c => ({ constat: c, avis_reobservation: (v1?.verdicts || []).find(v => v.id === c.id) || null, avis_recoupement: (v2?.verdicts || []).find(v => v.id === c.id) || null })), null, 1)}

OUBLIS SIGNALÉS :
${JSON.stringify(oublis, null, 1)}`, { label: `arbitrate:${u.key}`, phase: 'Arbitrate', schema: ARB }) || arb
}
const out = { label: u.label, observation: obs, verification_reobservation: v1, verification_recoupement: v2, arbitrage: arb }
if (kind === 'ortho') { out.zone = u.key; out.tiles = u.tiles } else { out.sequence = u.key; out.photos = u.photos }
return [out]
