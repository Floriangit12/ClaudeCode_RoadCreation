export const meta = {
  name: 'paquet-jardin-themes-finish',
  description: 'Termine la vérification des thèmes « état actuel » et « contexte/sécurité » du carrefour Paquet Jardin (double vérification + arbitrage)',
  phases: [
    { title: 'Load', detail: 'rechargement fidèle des observations/vérifications déjà faites' },
    { title: 'Verify', detail: '2 vérificateurs indépendants (état actuel)' },
    { title: 'Arbitrate', detail: '3e avis sur les constats contestés' },
  ],
}
const ROOT = '/home/user/ClaudeCode_RoadCreation'
const SCR = '/tmp/claude-0/-home-user-ClaudeCode-RoadCreation/86d2357b-8d3a-5e9d-b8d8-a3aa44c66205/scratchpad'
const O = `${ROOT}/analysis/paquet_jardin/observations_initiales`
const V = `${ROOT}/analysis/paquet_jardin/verifications_initiales`
const COMMON = `Lis d'abord ${ROOT}/analysis/paquet_jardin/CONTEXT.md (Read) : localisation, chronologie (ortho 5 cm = mai 2022 ; travaux C1 en 2025, finis fin janv. 2026), conventions.
Carte d'assemblage : ${ROOT}/analysis/paquet_jardin/carte_assemblage_pcrs.jpg ; ortho 5 cm 2022 : ${ROOT}/data/raw/pcrs5cm/tiles/paquet_jardin/ (tuiles 50 m, nom = coin bas-gauche L93, pixel (c,r) → x = X + 0.05c, y = Y + 50 − 0.05r).
Plan du projet 2025 géoréférencé : ${ROOT}/data/sites/paquet_jardin/plan_projet_2025/plan_L93.tif (géotransformation tournée) et tuiles 1000 px natives ${ROOT}/data/sites/paquet_jardin/plan_projet_2025/tuiles/ (index.json : affine L93 de chaque tuile). Superpositions levés GAM / ortho 2022 : ${ROOT}/analysis/paquet_jardin/figures/etat_actuel_sur_ortho2022/.
Images = tuiles 1000x1000 px à ouvrir telles quelles avec Read (aucun redimensionnement). Si tu fabriques une image de contrôle, fais-la en 1000x1000 px à la résolution native (recadre, ne réduis pas).
Python disponible (numpy, PIL, shapely, pyproj, geopandas, rasterio, cv2, pymupdf). Fichiers temporaires dans ${SCR}/wf_d2/ (disque limité : moins de 200 Mo, supprime les gros fichiers à la fin). Ne modifie RIEN dans le dépôt git. Réponds en français.`
const CLAIM = { type: 'object', properties: { id: { type: 'string' }, sujet: { type: 'string' }, enonce: { type: 'string' }, preuve: { type: 'string' }, confiance: { type: 'string', enum: ['haute', 'moyenne', 'faible'] } }, required: ['id', 'sujet', 'enonce', 'preuve', 'confiance'] }
const OBS = { type: 'object', properties: { theme: { type: 'string' }, constats: { type: 'array', items: CLAIM }, synthese: { type: 'string' }, description_par_branche: { type: 'string' }, implications_simulateur: { type: 'string' }, incertitudes: { type: 'string' }, fichiers_produits: { type: 'array', items: { type: 'string' } } }, required: ['theme', 'constats', 'synthese', 'implications_simulateur'] }
const VERDICT = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, verdict: { type: 'string', enum: ['confirme', 'corrige', 'refute', 'incertain'] }, correction: { type: 'string' }, justification: { type: 'string' } }, required: ['id', 'verdict', 'justification'] } }, oublis: { type: 'array', items: { type: 'string' } }, fiabilite_globale: { type: 'string' } }, required: ['verdicts', 'oublis', 'fiabilite_globale'] }
const ARB = { type: 'object', properties: { arbitrages: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, decision: { type: 'string', enum: ['retenu', 'retenu_corrige', 'rejete', 'incertain'] }, texte_final: { type: 'string' }, justification: { type: 'string' } }, required: ['id', 'decision', 'texte_final', 'justification'] } }, oublis_valides: { type: 'array', items: { type: 'object', properties: { description: { type: 'string' }, preuve: { type: 'string' } }, required: ['description', 'preuve'] } } }, required: ['arbitrages', 'oublis_valides'] }

const load = async (path, schema, n, field, label) => {
  for (let i = 0; i < 3; i++) {
    const r = await agent(`Lis le fichier JSON ${path} (outil Read, en plusieurs morceaux si nécessaire) et renvoie EXACTEMENT son contenu via la sortie structurée : tous les ${n} éléments de « ${field} », mêmes champs, même texte mot pour mot, sans rien résumer ni modifier.`, { label: `${label}#${i + 1}`, phase: 'Load', schema, effort: 'low' })
    if (r && (r[field] || []).length === n) return r
  }
  return null
}

const THEMES = [
  {
    key: 'etat_actuel', label: 'Géométrie ACTUELLE du carrefour (après travaux 2025)', obsPath: `${O}/etat_actuel.json`, n: 16,
    verifyHints: `RE-OBSERVATION : refais toi-même la superposition levés GAM / ortho 2022 / plan projet géoréférencé et vérifie chaque constat (y compris les mesures u/v, largeurs, positions des traversées, flèches, lignes d'arrêt). Repère : x = 917279,43 + 0,7071(u − v), y = 6460289,98 + 0,7071(u + v). RECOUPEMENT : confronte chaque constat à OSM 2026 (géométrie + tags lanes/turn:lanes/crossing ; historique d'édition dans ${ROOT}/data/raw/osm/map_*.osm et via l'API https://api.openstreetmap.org/api/0.6/way/<id>/history.json), BD TOPO, photos 2025-08-31 (travaux) et 2026-07-28 (${ROOT}/data/raw/panoramax/paquet_jardin/tiles/), ortho IGN 2024 ; signale toute contradiction.`,
  },
  {
    key: 'contexte_securite', label: 'Fonction du carrefour, trafic, transports, accidentologie et justification de la conception', obsPath: `${O}/contexte_securite.json`, n: 32,
    v1Path: `${V}/contexte_securite__verify-reobs.json`, v2Path: `${V}/contexte_securite__verify-cross.json`,
    verifyHints: `Vérifie toi-même les affirmations factuelles : accidents BAAC (fichier recalculé indépendamment ${ROOT}/data/context/baac_meylan_2015_2024.csv), GTFS ${ROOT}/data/context/gtfs_SEM.zip, comptages ${ROOT}/data/context/, documents ${ROOT}/data/raw/docs/, recherche web autorisée (WebSearch/WebFetch via ToolSearch) ; rejette toute affirmation non sourcée.`,
  },
]

const results = await pipeline(
  THEMES,
  async (t) => {
    const obs = await load(t.obsPath, OBS, t.n, 'constats', `load-obs:${t.key}`)
    if (!obs) throw new Error('chargement impossible ' + t.key)
    return obs
  },
  async (obs, t) => {
    const mk = (lens) => `${COMMON}

TU ES VÉRIFICATEUR (${lens === 'reobs' ? 'RE-OBSERVATION / RECALCUL INDÉPENDANT' : 'RECOUPEMENT MULTI-SOURCES'}) du rapport « ${t.label} » ci-dessous. Contrôle chaque constat (confirme / corrige / refute / incertain, avec la valeur corrigée) et liste les oublis importants. Sois exigeant : en cas de doute, ne confirme pas.
${t.verifyHints}

RAPPORT À VÉRIFIER :
${JSON.stringify(obs, null, 1)}`
    const [v1, v2] = await parallel([
      async () => (t.v1Path && await load(t.v1Path, VERDICT, t.n, 'verdicts', `load-v1:${t.key}`)) || agent(mk('reobs'), { label: `verify-reobs:${t.key}`, phase: 'Verify', schema: VERDICT }),
      async () => (t.v2Path && await load(t.v2Path, VERDICT, t.n, 'verdicts', `load-v2:${t.key}`)) || agent(mk('cross'), { label: `verify-cross:${t.key}`, phase: 'Verify', schema: VERDICT }),
    ])
    return { obs, v1, v2 }
  },
  async (r, t) => {
    const disputed = r.obs.constats.filter(c => {
      const a = (r.v1?.verdicts || []).find(v => v.id === c.id)
      const b = (r.v2?.verdicts || []).find(v => v.id === c.id)
      return !(a?.verdict === 'confirme' && b?.verdict === 'confirme')
    })
    const oublis = [...(r.v1?.oublis || []), ...(r.v2?.oublis || [])]
    let arb = { arbitrages: [], oublis_valides: [] }
    if (disputed.length || oublis.length) {
      arb = await agent(`${COMMON}

TU ES ARBITRE (3e vérification) du thème « ${t.label} ». Deux vérificateurs n'ont pas tous deux confirmé les constats ci-dessous et ont signalé des oublis. Vérifie toi-même et tranche ; valide ou rejette chaque oubli.
${t.verifyHints}

CONSTATS CONTESTÉS :
${JSON.stringify(disputed.map(c => ({ constat: c, avis_1: (r.v1?.verdicts || []).find(v => v.id === c.id) || null, avis_2: (r.v2?.verdicts || []).find(v => v.id === c.id) || null })), null, 1)}

OUBLIS SIGNALÉS :
${JSON.stringify(oublis, null, 1)}`, { label: `arbitrate:${t.key}`, phase: 'Arbitrate', schema: ARB }) || arb
    }
    return { theme: t.key, label: t.label, observation: r.obs, verification_1: r.v1, verification_2: r.v2, arbitrage: arb }
  },
)
return results.filter(Boolean)
