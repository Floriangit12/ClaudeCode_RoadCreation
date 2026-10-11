"""Présence 2026 (correctif Q4 de la revue adverse v2) : vignettes de présence, test automatique et entrée de
revue OBLIGATOIRE pour tout objet à moins de 25 m d'une photo calée postérieure aux travaux.

- vignettes : planches/presence/<id>.jpg (une vignette par photo : boîte projetée de l'objet, pied et sommet,
  emprise) et planches/presence/00_index_<n>.jpg (mosaïques de relecture) ; photos de tiers, locales (.jpg
  ignorés par git) ;
- test automatique (coherence_photos.test_presence) : structure verticale dans la boîte (mât) ; végétation
  (indice ExG) ou tronc (arbre) ;
- entrée de revue : revue_coherence.json « presence_2026 » {id: {valeur : present | absent | non_visible,
  photos, note}}, saisie par Claude sur les vignettes ; une entrée manquante est signalée
  (`presence_2026_non_revue`) ; « absent » -> non_instancie_absent_2026, constat renvoyé à la fusion.
Sortie : coherence/presence_2026.json.
"""
import math

from coherence_carte import COHERENCE
from commun import RACINE, arrondi, ecrire_json

DOSSIER = COHERENCE / "planches" / "presence"
SORTIE = COHERENCE / "presence_2026.json"


def _mosaique(images, titre, chemin, n_col=3):
    from PIL import Image, ImageDraw
    from coherence_preuves import POLICE
    if not images:
        return
    w, h = images[0].size
    n_lig = int(math.ceil(len(images) / n_col))
    out = Image.new("RGB", (w * min(n_col, len(images)), 18 + h * n_lig), (25, 25, 25))
    dr = ImageDraw.Draw(out)
    dr.text((4, 2), titre[:200], fill=(255, 255, 255), font=POLICE)
    for k, im in enumerate(images):
        out.paste(im, ((k % n_col) * w, 18 + (k // n_col) * h))
    out.save(chemin, quality=88)


def finaliser(objets, presence, revues, exist, faire=True):
    """Écrit les vignettes, rattache les entrées de revue, renvoie {id: dict(...)} (sans les images)."""
    from PIL import ImageDraw
    from coherence_preuves import POLICE_P
    par = {o["id"]: o for o in objets}
    if faire:
        DOSSIER.mkdir(parents=True, exist_ok=True)
        for f in sorted(DOSSIER.glob("*.jpg")):
            f.unlink()
    out = {}
    index = []
    for oid in sorted(presence):
        p = presence[oid]
        o = par[oid]
        rv = revues.get(oid)
        vigs = []
        for l in p["photos"]:
            im = l.pop("_vignette", None)
            if im is not None:
                dr = ImageDraw.Draw(im)
                txt = f"auto {l.get('auto')}" + (f" veg {l.get('vegetation')}" if l.get("vegetation") is not None else "") \
                      + (" tronc" if l.get("tronc") else "") + (f" axe r={l.get('residu')}" if l.get("structure") else "") \
                      + ("" if l.get("pose_validee_q2") else " pose non validée Q2") + (" bâti" if l.get("occulte_batiment") else "")
                dr.rectangle([0, 14, im.size[0], 27], fill=(0, 0, 0))
                dr.text((2, 14), txt[:60], fill=(255, 230, 120), font=POLICE_P)
                vigs.append(im)
        chemin = DOSSIER / f"{oid}.jpg"
        if faire and vigs:
            _mosaique(vigs, f"{oid} ({o['type']}) : présence 2026 - auto {p['auto']} - revue "
                            f"{(rv or {}).get('valeur', 'MANQUANTE')}", chemin, n_col=3)
            index.extend(vigs[:3])
        e = exist.get(oid) or {}
        out[oid] = dict(type=o["type"], couche=o["couche"], statut_2026=o.get("statut_source", o["statut"]),
                        position=p["position"], auto=p["auto"],
                        photos=[{k: v for k, v in l.items() if not k.startswith("_")} for l in p["photos"]],
                        vignette=None if not vigs else chemin.relative_to(RACINE).as_posix(),
                        revue=rv, revue_manquante=rv is None, existence_fusion=e.get("existence"),
                        decision=("absent" if (rv or {}).get("valeur") == "absent" else
                                  "present" if (rv or {}).get("valeur") == "present" else
                                  "non_visible" if (rv or {}).get("valeur") == "non_visible" else "a_revoir"))
    if faire and index:
        for k in range(0, len(index), 24):
            _mosaique(index[k:k + 24], f"présence 2026 : vignettes {k + 1} à {min(k + 24, len(index))} sur {len(index)}",
                      DOSSIER / f"00_index_{k // 24 + 1}.jpg", n_col=6)
    ecrire_json(SORTIE, arrondi(dict(
        schema="pj_coherence_presence/0.1",
        regle="Q4 : tout objet à moins de 25 m d'une photo calée postérieure aux travaux (2026-07-28) reçoit une vignette, "
              "un test automatique (structure verticale, végétation) et une entrée de revue obligatoire",
        comptes=dict(objets=len(out), revues=sum(1 for v in out.values() if not v["revue_manquante"]),
                     absents=sorted(k for k, v in out.items() if v["decision"] == "absent"),
                     revues_manquantes=sorted(k for k, v in out.items() if v["revue_manquante"]),
                     auto=dict(sorted(__import__("collections").Counter(v["auto"] for v in out.values()).items()))),
        objets=out), 3))
    return out
