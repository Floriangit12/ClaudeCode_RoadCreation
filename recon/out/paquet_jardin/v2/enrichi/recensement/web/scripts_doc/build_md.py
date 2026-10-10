# -*- coding: utf-8 -*-
import json, collections
R = 'D:/ClaudeCode_RoadCreation/'
reg = json.load(open(R + 'assets/specs/regles_locales_meylan.json', encoding='utf-8'))
obs = json.load(open(R + 'recon/out/paquet_jardin/v2/enrichi/recensement/web/obs_web.json', encoding='utf-8'))
docs = json.load(open(R + 'recon/out/paquet_jardin/v2/enrichi/recensement/web/documents_web.json', encoding='utf-8'))
ACT = {'generer': 'générer', 'contraindre': 'contraindre', 'verifier': 'vérifier', 'deduire_si_absent': 'déduire si absent'}


def court(t, n=200):
    t = t.split('. ')[0]
    return t if len(t) <= n else t[:n - 1].rsplit(' ', 1)[0] + ' …'


L = []
A = L.append
A('# Règles locales — Meylan, Grenoble-Alpes Métropole (carrefour Paquet Jardin)')
A('')
A("Version %s du %s · agent DOC-LOCALE · fichier machine : `assets/specs/regles_locales_meylan.json` (%d règles `LOC-*`, %d sources)."
  % (reg['version'], reg['date'], len(reg['regles']), len(reg['sources'])))
A('')
A("Ces règles complètent `regles_conception.json` (règles nationales) et `regles_implantation.json`. Préséance : observation 2026 > règle locale sourcée > règle nationale > pratique d'une autre collectivité > a priori. Une règle locale ne déplace jamais un objet observé : elle fixe les valeurs par défaut des objets déduits, les gabarits des assets et les contrôles.")
A('')
A("## Ce qu'il faut retenir")
A('')
for b in [
    "**Gestionnaire unique : Grenoble-Alpes Métropole.** Les routes départementales lui ont été transférées le 1er janvier 2017. Aucune règle du Département de l'Isère ne s'applique à la RD 1090 dans le site (LOC-CTX-001).",
    "**Métropole apaisée (Meylan depuis 2022).** 30 km/h par défaut, 50 km/h seulement sur les axes marqués « 50 » : Verdun à 50, Vercors et Revirée à 30. Le `maxspeed=50` d'OSM est une valeur par défaut fausse. Aucun panneau de vitesse dans la commune. Une ellipse « 30 » (1,20 × 2,40 m, gabarit grenoblois) rappelle la limite au début de chaque rue à 30 ; elle confirme le gabarit mesuré sur le site, 2,45 × 1,28 m (LOC-VIT-001 à 004).",
    "**Charte Chronovélo, enfin sourcée** (présentation Métropole/SMMAG 2022, fiche 2 du guide). Piste bidirectionnelle de 4 m (3 m au minimum), rives jaunes, axe « • • — • » jaune et turquoise. Aux traversées piétonnes : fond turquoise sous le zébra et 3 barrettes « ralentissez ». Aux traversées de chaussée : 2 files de pavés jaunes. Séparateur d'au moins 0,30 m, chanfreiné au-delà de 7 cm. En 2026, la Chronovélo 1 passe par Verdun SO puis le Vercors ; Verdun NE n'est que « planifié » (LOC-CHR-001 à 009).",
    "**Arrêts de bus de la Métropole.** Quai de 18 à 21 cm (18 cm à La Revirée, desservie aussi par des cars). Revêtement contrasté, dalle de repérage, bande d'interception. Équipement d'un arrêt Chrono : abri, banc, corbeille et afficheur temps réel (LOC-TC-001 à 004).",
    "**Mobilier métropolitain gris RAL 7024.** Potelet acier Ø 88,9 mm de 1,20 ou 1,40 m avec bande blanche ; potelet à mémoire de forme Ø 90 mm de 0,90 m ; borne en mélèze de 150 × 150 mm et 1,30 m. Barrière à croix de Saint-André de 1,20 m. Arceaux vélos à 1 m d'entraxe et 0,50 m de la bordure. Mobilier de contention posé en dernier recours seulement (LOC-MOB-001 à 005, LOC-VEL-001).",
    "**Charte de l'arbre (2019).** Entraxe de 7 à 12 m selon le développement. Axe de l'arbre à 1,50 m au moins du bord d'une voie ; dégagement de 1,50 × 2,50 m. 2 m au moins d'une façade, des réseaux et d'un candélabre. Fosse de 15 m³, tuteurage tripode de 2 m. TPC planté de 2 à 6 m. En octobre 2026, les arbres de 2025 sont jeunes et tuteurés (LOC-VEG-001 à 007).",
    "**Meylan (PLUi, livret haies et clôtures).** Clôture de 1,80 m au plus sur rue, muret de 1 m au plus, base perméable à la faune. Haies diversifiées, jamais monospécifiques. Liste d'essences « Ville parc » et liste d'invasives interdites (LOC-CLO-001 et 002, LOC-VEG-005).",
    "**Aucune photo du carrefour après travaux** sur le web public : ni Ville, ni Métropole, ni presse accessible, ni Panoramax. Seul OSM apporte des faits de 2026, issus de relevés de terrain : revêtements neufs, béton le long des Saules Blancs, stabilisé sur la rive E du Vercors, afficheur au quai NO, traversées à feux sans bouton d'appel ni signal sonore.",
]:
    A('- ' + b)
A('')
A('## Règles par famille')
A('')
for fam in reg['familles']:
    A('### %s' % fam['titre'])
    A('')
    A('| id | règle (résumé) | action | confiance | source |')
    A('|---|---|---|---|---|')
    for rid in fam['regles']:
        x = next(r for r in reg['regles'] if r['id'] == rid)
        A('| %s | %s | %s | %s | %s, %s |' % (rid, court(x['enonce']).replace('|', '/'), ACT[x['action']], x['confiance'],
                                             x['source']['id'], x['source']['ref'].replace('|', '/')))
    A('')
A('## Conflits avec les specs nationales')
A('')
A('| id | sujet | décision |')
A('|---|---|---|')
for c in reg['conflits']:
    A('| %s | %s | %s |' % (c['id'], c['sujet'], c['decision']))
A('')
A("Les conflits CF-LOC-03 et CF-LOC-05 visent `regles_implantation.json`, qui n'a pas été modifié.")
A('')
A('## Observations web (`recon/out/paquet_jardin/v2/enrichi/recensement/web/obs_web.json`)')
A('')
c = collections.Counter(o['statut'] for o in obs)
A("%d observations au format OBS (identifiants `DOC-LOCALE-001` à `DOC-LOCALE-%03d`) : %s. Le script `construire_obs_web.py` les reconstruit et les preuves sont dans `preuves/`."
  % (len(obs), len(obs), ', '.join('%d %s' % (v, k) for k, v in c.most_common())))
A('')
for o in obs:
    if o['sous_type'] == 'arbre_inventaire_metropole':
        continue
    A('- **%s** (%s, %s) : %s. Statut %s, lien %s, confiance %s.' % (
        o['id'], o['source'].split(' ;')[0], o['date_image'].split(' (')[0], o['sous_type'].replace('_', ' '),
        o['statut'], o['lien_description'] or '—', o['confiance']))
arb = [o for o in obs if o['sous_type'] == 'arbre_inventaire_metropole']
A("- **%s à %s** : %d arbres de l'inventaire métropolitain de 2023 à moins de 160 m du centre, dont 15 peupliers noirs sur Verdun NE. Statuts : %s." % (
    arb[0]['id'], arb[-1]['id'], len(arb), ', '.join('%d %s' % (v, k) for k, v in collections.Counter(o['statut'] for o in arb).most_common())))
A('')
A('Points à reporter dans la description :')
A('')
A("- La surface `S-0318` est décrite en enrobé. Le cheminement neuf le long des Saules Blancs est en béton clair d'après OSM (2026-05-14) : DOC-LOCALE-013.")
A("- Le trottoir de la rive E du Vercors est absent de la description. OSM le donne en stabilisé compacté et éclairé : DOC-LOCALE-004.")
A("- Le quai NO a un afficheur temps réel : DOC-LOCALE-007.")
A("- Les traversées à feux n'ont ni bouton d'appel ni signal sonore : DOC-LOCALE-010 et 011, LOC-FEU-002. OSM note aussi l'absence de BEV sur la partie E du Vercors, ce qui contredit le projet et reste à vérifier.")
A("- L'essence Populus nigra manque pour 8 arbres de Verdun NE : DOC-LOCALE-018 à 033.")
A("- OSM porte `lane_markings=no` sur l'entrée du Vercors, ce qui contredit le plan et le levé GAM. Statut incertain : DOC-LOCALE-016 et 017.")
A('')
A('## Documents trouvés')
A('')
A("Téléchargements dans `data/raw/docs_web/` (ignoré par git, usage interne, jamais redistribué) : %d fichiers, %.0f Mo. La liste complète (URL, taille, licence, usage) est dans `recon/out/paquet_jardin/v2/enrichi/recensement/web/documents_web.json`."
  % (docs['n_fichiers'], docs['taille_totale_octets'] / 1e6))
A('')
A('| source | document | fichier local | octets | droits |')
A('|---|---|---|---|---|')
for s in reg['sources']:
    A('| %s | %s | %s | %s | %s |' % (s['id'], s['titre'].replace('|', '/'),
                                    ('`%s`' % s['fichier_local']) if s['fichier_local'] else '(page web)',
                                    s['taille_octets'] or '', 'ODbL' if 'ODbL' in s['licence'] else 'public, usage interne'))
A('')
A('## Lacunes')
A('')
for l in reg['documents_non_trouves']:
    A('- ' + l)
A('')
open(R + 'assets/specs/REGLES_LOCALES_MEYLAN.md', 'w', encoding='utf-8').write('\n'.join(L))
print(len(L), 'lignes')
