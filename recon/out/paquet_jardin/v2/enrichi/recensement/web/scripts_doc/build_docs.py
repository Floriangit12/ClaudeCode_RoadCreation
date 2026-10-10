import json, os
R='D:/ClaudeCode_RoadCreation/'
reg=json.load(open(R+'assets/specs/regles_locales_meylan.json',encoding='utf-8'))
by_file={s['fichier_local']:s for s in reg['sources'] if s.get('fichier_local')}
extra={
 'data/raw/docs_web/urbanmaestro/urban-maestro_grenoble-public-space-programme_t-gabrieli.pdf':('https://urbanmaestro.org/wp-content/uploads/2020/09/urban-maestro_grenoble-public-space-programme_t-gabrieli.pdf','Urban Maestro (ONU-Habitat), « Grenoble Public Space Programme », 2020','lu, non exploité (méthode de la grille, sans cote)'),
 'data/raw/docs_web/ruedelavenir/GuideEspacePublicGrenoble.pdf':('https://www.ruedelavenir.com/wp-content/uploads/2018/10/GuideEspacePublicGrenoble.pdf',"Rue de l'Avenir, présentation du guide métropolitain et de la grille (2018)",'lu ; a fourni les liens vers les fiches'),
 'data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espace-public-Fiche-handicaps-visuels.pdf':('https://www.grenoblealpesmetropole.fr/cms_viewFile.php?idtf=2144&path=Espace-public-Fiche-handicaps-visuels.pdf','GAM, fiche accessibilité « Les handicaps visuels » (ERP)','lu en diagonale, non exploité (ERP)'),
 'data/raw/docs_web/grenoblealpesmetropole/guide_espaces_publics/Espace-public-Fiche-Acces-aux-commerces.pdf':('https://www.grenoblealpesmetropole.fr/cms_viewFile.php?idtf=1799&path=Espace-public-Fiche-Acces-aux-commerces.pdf','GAM, fiche « Accès aux commerces »','non exploité'),
 'data/raw/docs_web/data_gouv_arbres/patrimoine_arbore.csv':('https://www.data.gouv.fr/api/1/datasets/r/05566402-cd0d-4c9b-90b6-4a90e4629e03','GAM, patrimoine arboré (CSV)','doublon CSV du GeoJSON'),
 'data/raw/docs_web/data_gouv_arbres/hdr1.txt':(None,'en-têtes HTTP du téléchargement','technique'),
 'data/raw/docs_web/data_gouv_arbres/hdr2.txt':(None,'en-têtes HTTP du téléchargement','technique'),
}
docs=[]
for d,_,fs in os.walk(R+'data/raw/docs_web'):
    for f in sorted(fs):
        p=os.path.relpath(os.path.join(d,f),R).replace(os.sep,'/')
        s=by_file.get(p)
        e={'fichier_local':p,'taille_octets':os.path.getsize(R+p)}
        if s:
            e.update({'source_id':s['id'],'titre':s['titre'],'url':s['url'],'date':s['date'],'licence':s['licence'],'note':s.get('note'),'utilisee_par_n_regles':s.get('utilisee_par_n',0)})
        elif p in extra:
            u,t,n=extra[p]; e.update({'source_id':None,'titre':t,'url':u,'licence':"document public ; analyse interne, non redistribué" if u else None,'note':n,'utilisee_par_n_regles':0})
        else:
            e.update({'source_id':None,'titre':None,'url':None,'note':'non catalogué'})
        docs.append(e)
pages=[{'url':'https://www.meylan.fr/311-ligne-c1.htm','objet':'page Ligne C1+ (liens des PDF, calendrier)'},
 {'url':'https://www.meylan.fr/actualite/1129/42-travaux-c1-carrefour-verdun-vercors.htm','objet':"actualité expirée (redirige vers l'accueil) ; contenu connu par le moteur de recherche : chantier du 23/06 au 05/12/2025"},
 {'url':'https://www.meylan.fr/actualite/1108/42-travaux-c1-avenue-du-vercors.htm','objet':"actualité expirée ; Vercors en sens unique, trottoirs et végétalisation jusqu'au 30/01/2026"},
 {'url':'https://www.meylan.fr/actualite/1227/42-amelioration-ligne-c1-le-point-sur-les-chantiers-en-cours.htm','objet':'actualité expirée'},
 {'url':'https://www.grenoblealpesmetropole.fr/actualite/490/45-grenoble-gieres-meylan-vif...-les-chantiers-de-l-ete-dans-la-metropole.htm','objet':"chantiers de l'été 2025 (25/07/2025) : travaux entre Verdun et Vercors jusqu'en janvier 2026 ; aucune image du site"},
 {'url':'https://www.placegrenet.fr/2024/06/10/reamenagement-annonce-des-avenues-du-vercors-et-du-granier-a-meylan-pour-ameliorer-la-ligne-de-bus-c1/631029','objet':'article (budget 4 303 105 € TTC ; image Google Maps avant travaux, non téléchargée)'},
 {'url':'https://lacentraledesmarches.com/marches-publics/Meylan-Grenoble-Alpes-Metropole-Travaux-de-reamenagement-des-avenues-du-Vercors-et-du-Granier--Meylan/319899','objet':'avis de marché BOAMP 24-127427 (3 lots)'},
 {'url':'https://www.data.gouv.fr/datasets/patrimoine-arbore-du-territoire-metropolitain','objet':'fiche du jeu de données (ODbL, archivé 2023-09-11)'},
 {'url':'https://api.panoramax.xyz/api/search (bbox ±200 m, 2025-09-01..2026-10-10)','objet':'44 photos, toutes du 2026-07-28 à 129-212 m au sud : déjà connues ; aucune du cœur'},
 {'url':'https://overpass.kumi.systems/api/interpreter','objet':'extrait OSM (base 2026-05-31) -> preuves/osm_extrait_site_2026-05-31.json'},
 {'url':'https://web.archive.org/cdx/search/cdx (grenoblealpesmetropole.fr/cms_viewFile.php)','objet':'récupération des fiches du guide retirées du site'}]
out={'agent':'DOC-LOCALE','date':'2026-10-10','racine_telechargements':'data/raw/docs_web/ (ignoré par git ; usage interne, jamais redistribué)','n_fichiers':len(docs),
     'taille_totale_octets':sum(d['taille_octets'] for d in docs),'fichiers':docs,'pages_consultees_sans_telechargement':pages,
     'images_extraites_ou_rendues':'recon/out/paquet_jardin/v2/enrichi/recensement/web/preuves/ (rendus de pages et recadrages des PDF ci-dessus)'}
json.dump(out,open(R+'recon/out/paquet_jardin/v2/enrichi/recensement/web/documents_web.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(out['n_fichiers'], out['taille_totale_octets'], [d['fichier_local'] for d in docs if d.get('note')=='non catalogué'])
