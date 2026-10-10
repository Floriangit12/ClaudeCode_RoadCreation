"""Reference d'eclairage et d'exposition du projet (source unique, Python pur : editeur et client).

Utilisee par tests_phase0/ue/t1_niveau.py (niveaux PJ_Phase0, PJ_Materiaux, puis PJ_2026), tests_phase0/commun.py
(EV100 des captures) et materiaux/materiaux.py ; les capteurs ADAS prendront EV100 d'ici (exposition fixe).

Exposition : EV100 = 14. Sol a ~50 klux (soleil a 27,6 deg + ciel clair) : luminance d'un gris 18 %
L = 0,18 x 50 000 / pi ~ 2 900 cd/m2 ; loi d'UE (manuel, sans camera physique) pixel = L / (1,2 x 2^EV100)
-> EV100 ~ 13,7-14. A EV 12, le gris 18 % au soleil sortait a 0,52-0,55 (1,5 a 2 diaphragmes de surexposition) ;
a EV 14 il sort a 0,14 (t7, apres courbe de ton).

Soleil : avec atmosphere_sun_light, UE applique la transmittance de SkyAtmosphere a l'eclairement de la lumiere,
qui est donc celui HORS atmosphere : constante d'eclairement solaire 128 klux (1361 W/m2 x ~94 lm/W). Les
100 klux de la phase 0 (ordre de grandeur au sol) y etaient pris hors atmosphere : sol trop sombre d'un tiers des
que les aerosols sont realistes.

Ciel : SkyAtmosphere d'UE par defaut = air tres pur (Mie 0,003996 /km sur 1,2 km : epaisseur optique des aerosols
0,005) -> ciel bleu sature, ombres bleu marine (t7 a EV 14 : ombre/soleil 0,069, canal R 0,021). Vallee du
Gresivaudan : epaisseur optique ~0,1-0,2 a 550 nm ; Mie 0,12 /km (0,14) regle sur t7 (balayage 0,004-0,2 :
ombre/soleil 0,069 / 0,099 (0,03) / 0,183 (0,1) / 0,251 (0,15) / 0,316 (0,2) a 100 klux ; 0,216 et canal R 0,16 a
0,12 et 128 klux ; critere [0,18 ; 0,32], R >= 0,10). Absorption gardee a 11 % de la diffusion (albedo de diffusion
simple ~0,9, rapport d'origine). Balance des blancs 5500 K : gris 18 % au soleil B/G 1,06 (6000 K : 0,93), et
l'enrobe (cible B/G 0,92) ressort a ~0,97 comme sur les photos 1 et 2.
Lumiere du ciel : SkyLight temps reel, intensite 1 ; lower_hemisphere_color n'agit que si lower_hemisphere_is_black
est vrai : on le laisse faux (hemisphere inferieur = sol planetaire de SkyAtmosphere, albedo 0,4 : rebond du sol).
Post-process neutre (capteurs, mesures) : ni vignettage, ni grain, ni aberration chromatique.
"""

EV100 = 14.0
BALANCE_BLANCS_K = 5500.0          # preset "soleil" d'un appareil

SOLEIL = dict(soleil_az_geo=220.0, soleil_elev=27.6, convergence=2.0086, soleil_lux=128000.0)   # hors atmosphere

MIE_ECHELLE = 0.12                 # /km (UE : 0,003996)
CIEL = dict(mie_scattering_scale=MIE_ECHELLE, mie_absorption_scale=round(MIE_ECHELLE * 0.111, 6))
LUMIERE_CIEL = dict(intensity=1.0, lower_hemisphere_is_black=False)

POST_PROCESS_NEUTRE = dict(override_vignette_intensity=True, vignette_intensity=0.0,
                           override_film_grain_intensity=True, film_grain_intensity=0.0,
                           override_scene_fringe_intensity=True, scene_fringe_intensity=0.0)

# critere de t7 (ombre portee d'une boite haute sur le sol neutre, rapport de luminance ombre/soleil apres courbe de ton)
OMBRE_SOLEIL_MIN, OMBRE_SOLEIL_MAX, OMBRE_SOLEIL_R_MIN = 0.18, 0.32, 0.10
