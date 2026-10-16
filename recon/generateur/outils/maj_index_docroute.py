# -*- coding: utf-8 -*-
"""Met à jour D:\\DocRoute\\INDEX_DOCUMENTATION.md à partir de la copie d'origine (00_Synthese/...avant_maj...).

- liens file:///c:/Users/flori/Desktop/DocRoute/... -> chemins relatifs ;
- bandeau de mise à jour + section 0 (synthèse, errata, base de règles, plan) avant la section 1 ;
- sections 8 à 14 (texte dans recon/generateur/outils/index_ajouts.md) à la fin.
Le contenu d'origine des sections 1 à 7 est conservé. Idempotent : repart toujours de la copie d'origine.
"""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
ORIGINE = Path("D:/DocRoute/00_Synthese/INDEX_DOCUMENTATION_avant_maj_20261016.md")
CIBLE = Path("D:/DocRoute/INDEX_DOCUMENTATION.md")
AJOUTS = ICI / "index_ajouts.md"

ENTETE = r"""
> **Mise à jour du 16/10/2026.** Le dossier de travail est désormais `D:\DocRoute` : les liens de cet index sont
> relatifs (ils pointaient vers l'ancienne copie `C:\Users\flori\Desktop\DocRoute`). Le contenu d'origine des
> sections 1 à 7 est conservé tel quel ; plusieurs descriptions y sont inexactes : elles sont corrigées dans
> [`00_ERRATA_DOCUMENTS_EXISTANTS.md`](00_ERRATA_DOCUMENTS_EXISTANTS.md) (renvois ci-dessous). Les sections 0 et 8 à 14
> sont nouvelles. Copie de l'index d'origine : [`00_Synthese/INDEX_DOCUMENTATION_avant_maj_20261016.md`](00_Synthese/INDEX_DOCUMENTATION_avant_maj_20261016.md).

---

## 0. Synthèse de conception, errata et base de règles (à lire d'abord)

| Fichier | Contenu |
| :--- | :--- |
| [`00_SYNTHESE_CONCEPTION_ROUTES_FR.md`](00_SYNTHESE_CONCEPTION_ROUTES_FR.md) | **Référence de conception routière française pour le générateur**, rangée par élément : profil en travers, marquages et flèches, lignes transversales et passages piétons, carrefours (îlots, zone de conflit, trajectoires), giratoires, îlots et terre-pleins (cinq genres), ponts, cycles, piétons, TC et stationnement, signalisation verticale, feux, végétation ; chaque règle avec sa source officielle (page), le document détaillé et son identifiant machine ; tableau des pratiques locales observées en Isère ; valeurs par défaut et arbitrages ; lacunes. |
| [`00_ERRATA_DOCUMENTS_EXISTANTS.md`](00_ERRATA_DOCUMENTS_EXISTANTS.md) | Erreurs relevées dans cet index, les dossiers 02 à 06 et les specs du dépôt, avec la valeur correcte et sa source (E-01 à E-129). |
| Dépôt : `D:\ClaudeCode_RoadCreation\assets\specs\route\regles_route_fr.json` (+ `README.md`) | **Base machine unique** : 857 règles fusionnées et dédoublonnées des dossiers 08 à 14 (identifiants stables `RF-*`, sources canoniques, pages contrôlées), 18 arbitrages, 34 paramètres par défaut. |
| Dépôt : `D:\ClaudeCode_RoadCreation\recon\generateur\PLAN_GENERATEUR.md` | Architecture et plan d'implémentation du générateur procédural Houdini (étapes livrables, critères, scènes de test, validation visuelle sur Panoramax, puis Meylan). |

Corrections à connaître dans les sections 1 à 7 ci-dessous (détail dans l'errata) :

- § 1, IISR 1re partie : 2,30 m est une hauteur **maximale** en agglomération éclairée ; les 0,70 m se mesurent au
  **bord** du panneau ; l'IISR1 traite les balises J1 à J16 (E-02 à E-04).
- § 1, IISR 6e partie : les hauteurs « 2,30 m / 1,10 m / potence 5,10 m » ne figurent pas dans l'IISR6 (gabarit
  ≥ 2,00 m, axe du feu supérieur < 4,20 m) ; le M12 est défini dans l'IISR 1re partie (E-05, E-06).
- § 2 : `Cerema_Giratoire_Terre_Plein_Franchissable_Interurbain.pdf` = note n° 05 limitée au giratoire à TPC
  franchissable interurbain ; `Cerema_Double_Sens_Cyclable_Guide.pdf` = guide Inddigo pour la DEAL Guyane ;
  `FUB_Cerema_Voirie_Cyclable_Cles_Reussite.pdf` = diaporama Cerema de 2021 ;
  `GrandLyon_Referentiel_Conception_Voirie_Espaces_Publics.pdf` = Guide de conception des **carrefours à feux** de la
  Métropole de Lyon (2023) ; `Paris_Referentiel_Amenagements_Cyclables_Voirie.pdf` = 1re partie seulement (E-07 à E-13).
- § 3 : `IGN_Geoplateforme_DC_BDTOPO.pdf` = « Suivi des évolutions à partir de la v3.0 », pas le descriptif de
  contenu (E-14).
- § 5 et § 6 : le JSON, l'étude et le VEX du dossier 05 et le guide du dossier 06 contiennent des valeurs fausses ou
  non sourcées (E-15, E-40 à E-108) ; « NF P98-302 » → NF EN 1340 + NF P 98-340/CN (E-16).
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    src = ORIGINE.read_text(encoding="utf-8")
    n = src.count("file:///c:/Users/flori/Desktop/DocRoute/")
    t = src.replace("file:///c:/Users/flori/Desktop/DocRoute/", "")
    i = t.index("\n---\n")
    t = t[:i] + "\n" + ENTETE + t[i:]
    t = t.rstrip("\n") + "\n" + AJOUTS.read_text(encoding="utf-8")
    CIBLE.write_text(t, encoding="utf-8")
    print(f"{n} liens convertis ; {len(src)} -> {len(t)} caractères ; liens file:/// restants : {t.count('file:///')}")


if __name__ == "__main__":
    main()
