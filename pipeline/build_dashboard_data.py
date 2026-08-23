#!/usr/bin/env python3
"""
build_dashboard_data.py — Mission 26004 / Que Choisir Ensemble

Construit data_dashboard/ a partir des sorties deja auditees de FINDINGS/.
Aucune lecture des bases brutes : DVF_clean, DPE_clean et RPLS_clean ne sont
jamais ouverts. Les CSV de FINDINGS/ font foi.

Sorties : communes_acces.csv, departements_tension.csv, departements_qualite.csv,
          series_temporelles.csv, confort_ete.csv, villes.csv,
          decomposition_prix_taux.csv
"""

import json
import os
import sys
import unicodedata

import numpy as np
import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "data_dashboard")

# Les sources auditees (FINDINGS/, Base de donnees/) vivent dans le dossier de mission,
# hors du depot. Ordre de resolution : variable d'environnement, puis dossier voisin.
CANDIDATS_SOURCE = [
    os.environ.get("QCE_SOURCE_ROOT", ""),
    RACINE,
    os.path.join(os.path.dirname(RACINE), "MISSION JE"),
]


def racine_sources():
    for c in CANDIDATS_SOURCE:
        if c and os.path.isdir(os.path.join(c, "FINDINGS", "Phase2")):
            return c
    raise SystemExit(
        "Sources introuvables. Le pipeline a besoin de FINDINGS/Phase2 et de "
        "« Base de données », qui vivent dans le dossier de mission.\n"
        "Définir QCE_SOURCE_ROOT, par exemple :\n"
        '  QCE_SOURCE_ROOT="$HOME/Desktop/MISSION JE" python pipeline/build_dashboard_data.py')


SOURCES = racine_sources()
PHASE2 = os.path.join(SOURCES, "FINDINGS", "Phase2")
BASES = os.path.join(SOURCES, "Base de données")

RATIO_SOCIAL_2016 = 4.06
RATIO_SOCIAL_2025 = 7.34

DUREE_MOIS = 240
TAUX_ASSURANCE = 0.0030


def facteur_financement(taux):
    i = taux / 12
    return i / (1 - (1 + i) ** -DUREE_MOIS) + TAUX_ASSURANCE / 12


FACTEUR_2021 = facteur_financement(0.0100)
FACTEUR_2025 = facteur_financement(0.0320)


def sans_accent(nom):
    plat = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode()
    return plat.strip().lower().replace(" ", "_").replace("-", "_")


def normalise_colonnes(df):
    df.columns = [sans_accent(c) for c in df.columns]
    return df


def lire(chemin, **kw):
    return normalise_colonnes(pd.read_csv(chemin, low_memory=False, **kw))


# ---------- chargement ----------
def charger():
    src = {}
    src["effort"] = lire(os.path.join(PHASE2, "taux_effort_anil_all.csv"),
                         dtype={"INSEE_C": str, "DEP": str, "REG": str})
    src["achat"] = lire(os.path.join(PHASE2, "pouvoir_achat_immo.csv"),
                        dtype={"INSEE_C": str, "DEP": str, "REG": str})
    src["peine"] = lire(os.path.join(PHASE2, "double_peine_communes.csv"),
                        dtype={"INSEE_C": str, "DEP": str, "REG": str})
    src["qualite"] = lire(os.path.join(PHASE2, "qualite_communes.csv"),
                          dtype={"INSEE_C": str, "DEP": str, "REG": str})
    src["sne"] = lire(os.path.join(BASES, "SNE", "SNE_tension_ratio.csv"),
                      dtype={"dept_code": str})
    src["w12"] = lire(os.path.join(PHASE2, "dept_effort_weighted_t12.csv"), dtype={"DEP": str})
    src["w3p"] = lire(os.path.join(PHASE2, "dept_effort_weighted_t3p.csv"), dtype={"DEP": str})
    src["serie_nat"] = lire(os.path.join(PHASE2, "serie_surface_national.csv"))
    src["serie_villes"] = lire(os.path.join(PHASE2, "serie_surface_villes.csv"))
    src["serie_communes"] = lire(os.path.join(PHASE2, "serie_surface_communes.csv"),
                                 dtype={"INSEE_C": str, "DEP": str})
    src["villes_effort"] = lire(os.path.join(PHASE2, "grandes_villes_effort.csv"))
    src["villes_achat"] = lire(os.path.join(PHASE2, "pouvoir_achat_grandes_villes.csv"))
    src["decomp"] = lire(os.path.join(PHASE2, "serie_surface_decomposition.csv"))
    src["rp"] = normalise_colonnes(pd.read_csv(
        os.path.join(BASES, "INSEE_RP", "INSEE_logement_2022_dept.csv"),
        sep=";", dtype={"dept_code": str}))
    with open(os.path.join(PHASE2, "confort_ete_aggregats.json"), encoding="utf-8") as fh:
        src["confort"] = json.load(fh)
    return src


# ---------- communes : effort locatif, surface financable, cumul des exclusions ----------
def build_communes(src):
    e = src["effort"]
    petit = e[e.segment == "T1-T2"][
        ["insee_c", "libgeo", "dep", "reg", "loyer_mensuel", "revenu_menage_proxy",
         "revenu_menage_d1", "taux_effort_median", "taux_effort_d1", "fiable"]]
    petit = petit.rename(columns={
        "loyer_mensuel": "loyer_petit", "taux_effort_median": "effort_median_petit",
        "taux_effort_d1": "effort_d1_petit", "fiable": "fiable_loyer_petit"})

    fam = e[e.segment == "T3+"][
        ["insee_c", "loyer_mensuel", "taux_effort_median", "taux_effort_d1", "fiable"]]
    fam = fam.rename(columns={
        "loyer_mensuel": "loyer_familial", "taux_effort_median": "effort_median_familial",
        "taux_effort_d1": "effort_d1_familial", "fiable": "fiable_loyer_familial"})

    a = src["achat"][["insee_c", "prix_m2_tous", "prix_m2_appart", "n_ventes_tous",
                      "surface_financable", "categorie", "fiable"]]
    a = a.rename(columns={"categorie": "categorie_surface", "fiable": "fiable_prix"})

    p = src["peine"][["insee_c", "tension_2025", "echec_loc_med", "echec_loc_d1",
                      "echec_achat", "echec_social", "n_legs_dispo"]]

    df = petit.merge(fam, on="insee_c", how="outer") \
              .merge(a, on="insee_c", how="outer") \
              .merge(p, on="insee_c", how="outer")

    for c in ("echec_loc_med", "echec_loc_d1", "echec_achat", "echec_social"):
        df[c] = df[c].map({True: True, False: False, "True": True, "False": False})

    trois = df.n_legs_dispo == 3
    df["triple_peine_median"] = np.where(
        trois, df[["echec_loc_med", "echec_achat", "echec_social"]].fillna(False).all(axis=1), np.nan)
    df["triple_peine_d1"] = np.where(
        trois & df.echec_loc_d1.notna(),
        df[["echec_loc_d1", "echec_achat", "echec_social"]].fillna(False).all(axis=1), np.nan)

    df["insee_c"] = df.insee_c.astype(str).str.zfill(5)
    df["dep"] = df.dep.astype(str)
    return df.sort_values("insee_c").reset_index(drop=True)


# ---------- departements : tension du parc social et effort pondere ----------
def build_tension(src):
    sne = src["sne"]
    dep = sne[sne.level == "Departement"].copy()
    dep["tension_ratio"] = pd.to_numeric(dep.tension_ratio, errors="coerce")
    dep["year"] = pd.to_numeric(dep.year, errors="coerce").astype("Int64")

    t = dep.pivot_table(index=["dept_code", "territory"], columns="year",
                        values="tension_ratio", aggfunc="median").reset_index()
    t.columns = ["dep", "nom"] + [f"tension_{int(c)}" for c in t.columns[2:]]

    w12 = src["w12"].rename(columns={
        "dep": "dep", "n_communes_fiable": "n_communes_petit",
        "med_unweighted": "effort_median_petit", "mean_weighted": "effort_pondere_petit",
        "gap": "ecart_petit"})
    w3p = src["w3p"].rename(columns={
        "dep": "dep", "n_communes_fiable": "n_communes_familial",
        "med_unweighted": "effort_median_familial", "mean_weighted": "effort_pondere_familial",
        "gap": "ecart_familial"})

    out = t.merge(w12, on="dep", how="outer").merge(w3p, on="dep", how="outer")
    out["dep"] = out.dep.astype(str)
    return out.sort_values("dep").reset_index(drop=True)


# ---------- departements : qualite du parc ----------
def build_qualite(src):
    q = src["qualite"]
    q = q[q.n_dpe.notna()].copy()
    fiable = q[q.n_dpe >= 20]

    agg = (fiable.assign(_num=fiable.taux_passoires / 100 * fiable.n_dpe)
                 .groupby("dep")
                 .agg(n_dpe=("n_dpe", "sum"), _num=("_num", "sum"),
                      cout_median=("cout_median", "median"),
                      n_communes=("insee_c", "count"))
                 .reset_index())
    agg["taux_passoires"] = 100 * agg._num / agg.n_dpe
    agg = agg.drop(columns="_num")

    rp = src["rp"].rename(columns={"dept_code": "dep"})[
        ["dep", "nb_rp", "taux_suroccupation", "part_hlm", "part_loc_prive", "taux_vacance"]]

    out = agg.merge(rp, on="dep", how="outer")
    out["dep"] = out.dep.astype(str)
    return out.sort_values("dep").reset_index(drop=True)


# ---------- series temporelles ----------
def build_series(src):
    nat = src["serie_nat"].rename(columns={
        "median_prix_m2_tous": "prix_m2_median",
        "median_surface_financable": "surface_financable",
        "n_communes_fiables": "n_communes"})
    nat["perimetre"] = "national"
    nat["ville"] = ""
    nat["dep"] = ""
    nat["taux_pct"] = nat.taux * 100

    v = src["serie_villes"].melt(
        id_vars=["ville", "departement"],
        value_vars=[f"surface_{a}" for a in range(2021, 2026)],
        var_name="annee", value_name="surface_financable")
    v["annee"] = v.annee.str.replace("surface_", "").astype(int)
    v = v.rename(columns={"departement": "dep"})
    v["perimetre"] = "ville"
    v["dep"] = v.dep.astype(str).str.zfill(2)

    taux = dict(zip(nat.annee, nat.taux_pct))
    v["taux_pct"] = v.annee.map(taux)

    cols = ["perimetre", "annee", "ville", "dep", "surface_financable",
            "prix_m2_median", "n_communes", "taux_pct", "indice_capacite_2021_100"]
    out = pd.concat([nat, v], ignore_index=True)
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols].sort_values(["perimetre", "annee", "ville"]).reset_index(drop=True)


# ---------- grandes villes : effort locatif et surface financable ----------
def build_villes(src):
    e = src["villes_effort"].rename(columns={
        "departement": "dep", "taux_effort_t12_median": "effort_petit",
        "taux_effort_t3p_median": "effort_familial", "taux_effort_t3p_d1": "effort_d1_familial"})
    e = e[["ville", "dep", "population", "effort_petit", "effort_familial", "effort_d1_familial"]]

    a = src["villes_achat"]
    a.columns = ["rang", "ville", "dep", "population", "prix_m2_appart",
                 "revenu_menage", "surface_financable"]
    a = a[["ville", "prix_m2_appart", "revenu_menage", "surface_financable"]]

    v = src["serie_villes"].rename(columns={"departement": "dep"})
    v = v[["ville"] + [f"surface_{an}" for an in range(2021, 2026)] + ["delta_m2", "delta_pct"]]

    out = e.merge(a, on="ville", how="left").merge(v, on="ville", how="left")
    out["dep"] = out.dep.astype(str)
    return out.sort_values("population", ascending=False).reset_index(drop=True)


# ---------- decomposition de la perte entre prix et taux ----------
def build_decomposition(src):
    d = src["decomp"]
    a_ref = float(d.loc[d.scenario == "prix 2021 + taux 2021", "surface_m2"].iloc[0])
    b_prix = float(d.loc[d.scenario == "prix 2025 + taux 2021", "surface_m2"].iloc[0])
    c_full = float(d.loc[d.scenario == "prix 2025 + taux 2025", "surface_m2"].iloc[0])

    sc = src["serie_communes"].dropna(subset=["surface_financable_2021", "surface_financable_2025"])
    b_taux = float((sc.surface_financable_2021 * (FACTEUR_2021 / FACTEUR_2025)).median())
    total = c_full - a_ref

    lignes = [
        dict(ordre="prix_puis_taux", etape=1, scenario="prix 2021 + taux 2021",
             surface_m2=a_ref, effet_m2=np.nan, part_pct=np.nan),
        dict(ordre="prix_puis_taux", etape=2, scenario="prix 2025 + taux 2021",
             surface_m2=b_prix, effet_m2=b_prix - a_ref, part_pct=100 * (b_prix - a_ref) / total),
        dict(ordre="prix_puis_taux", etape=3, scenario="prix 2025 + taux 2025",
             surface_m2=c_full, effet_m2=c_full - b_prix, part_pct=100 * (c_full - b_prix) / total),
        dict(ordre="taux_puis_prix", etape=1, scenario="prix 2021 + taux 2021",
             surface_m2=a_ref, effet_m2=np.nan, part_pct=np.nan),
        dict(ordre="taux_puis_prix", etape=2, scenario="prix 2021 + taux 2025",
             surface_m2=b_taux, effet_m2=b_taux - a_ref, part_pct=100 * (b_taux - a_ref) / total),
        dict(ordre="taux_puis_prix", etape=3, scenario="prix 2025 + taux 2025",
             surface_m2=c_full, effet_m2=c_full - b_taux, part_pct=100 * (c_full - b_taux) / total),
    ]
    out = pd.DataFrame(lignes)
    out["n_communes_panel"] = len(sc)
    return out


# ---------- confort d'ete : lecture seule du JSON fige ----------
def build_confort(src):
    j = src["confort"]
    lignes = []

    def ajoute(dim, cle, libelle, d):
        lignes.append(dict(
            dimension=dim, cle=str(cle), libelle=libelle,
            bon=d.get("bon"), moyen=d.get("moyen"), insuffisant=d.get("insuffisant"),
            renseigne=d.get("renseigne"), total_dpe=d.get("total_dpe"),
            pct_insuffisant=d.get("pct_insuffisant"), pct_bon=d.get("pct_bon")))

    n = j["national"]
    c = n["counts"]
    lignes.append(dict(
        dimension="national", cle="france", libelle="France",
        bon=c["bon"], moyen=c["moyen"], insuffisant=c["insuffisant"],
        renseigne=n["renseigne"], total_dpe=n["total_dataset"],
        pct_insuffisant=100 * c["insuffisant"] / n["renseigne"],
        pct_bon=100 * c["bon"] / n["renseigne"]))

    ab = j["paradoxe_AB"]
    cab = ab["counts"]
    lignes.append(dict(
        dimension="paradoxe_ab", cle="AB", libelle="Etiquettes A ou B",
        bon=cab["bon"], moyen=cab["moyen"], insuffisant=cab["insuffisant"],
        renseigne=ab["renseigne"], total_dpe=ab["total"],
        pct_insuffisant=100 * cab["insuffisant"] / ab["renseigne"],
        pct_bon=100 * cab["bon"] / ab["renseigne"]))

    for dim in ("par_etiquette", "par_region", "par_departement", "par_energie",
                "par_periode", "par_batiment", "paris_arrondissements"):
        for cle, d in j[dim].items():
            ajoute(dim, cle, d.get("label", str(cle)), d)

    for cle, d in j["sous_criteres"].items():
        for etat in ("insuffisant", "bon"):
            bloc = d[etat]
            lignes.append(dict(
                dimension="sous_critere", cle=f"{cle}|{etat}", libelle=d["label"],
                bon=None, moyen=None, insuffisant=None,
                renseigne=bloc["renseigne"], total_dpe=None,
                pct_insuffisant=100 * bloc["oui"] / bloc["renseigne"], pct_bon=None))

    out = pd.DataFrame(lignes)
    out["cle"] = out.cle.astype(str)
    return out


# ---------- controles de conformite au rapport ----------
def controles(com, ten, qua, ser, con, vil, dec, src):
    res = []

    def test(nom, obtenu, attendu, tol=0.05):
        ok = obtenu is not None and abs(obtenu - attendu) <= tol
        res.append((nom, attendu, obtenu, ok))

    e = src["effort"]
    for seg, lab in (("T1-T2", "petit"), ("T3+", "familial")):
        f = e[(e.segment == seg) & (e.fiable == True)]
        test(f"effort median, menage median, {lab}", f.taux_effort_median.median(),
             {"petit": 14.8, "familial": 20.8}[lab])
        test(f"effort median, menage D1, {lab}", f.taux_effort_d1.median(),
             {"petit": 29.5, "familial": 42.7}[lab])
    f3 = e[(e.segment == "T3+") & (e.fiable == True)]
    med = f3[f3.taux_effort_median.notna()]
    d1 = f3[f3.taux_effort_d1.notna()]
    test("communes > 33 %, menage median, familial", 100 * (med.taux_effort_median > 33).mean(), 2.6)
    test("communes > 33 %, menage D1, familial", 100 * (d1.taux_effort_d1 > 33).mean(), 86.6)
    test("communes disposant du D1", float(len(d1)), 5163.0, 0)

    a = src["achat"]
    test("surface financable mediane nationale",
         a.loc[a.fiable == True, "surface_financable"].median(), 88.8)

    n = ser[ser.perimetre == "national"].set_index("annee")
    for annee, attendu in ((2021, 119.1), (2022, 102.0), (2023, 85.9), (2024, 85.5), (2025, 89.6)):
        test(f"serie surface financable {annee}", n.loc[annee, "surface_financable"], attendu)

    trois = com[com.n_legs_dispo == 3]
    test("communes a trois indicateurs", float(len(trois)), 13690.0, 0)
    test("communes en triple peine, menage median",
         float(trois.triple_peine_median.sum()), 238.0, 0)

    q = qua[qua.n_dpe.notna()]
    test("part de passoires nationale", 100 * (q.taux_passoires / 100 * q.n_dpe).sum() / q.n_dpe.sum(), 9.8)
    test("cout energetique median", src["qualite"].loc[src["qualite"].n_dpe >= 20, "cout_median"].median(), 1769.0, 0.5)

    rp = src["rp"]
    test("taux de suroccupation national",
         (rp.taux_suroccupation * rp.nb_rp).sum() / rp.nb_rp.sum(), 9.6)

    p = vil[vil.ville == "Paris"].iloc[0]
    test("Paris, effort petit logement", p.effort_petit, 35.4)
    test("Paris, effort menage median, familial", p.effort_familial, 63.3)
    test("Paris, effort menage D1, familial", p.effort_d1_familial, 159.4)
    test("Paris, surface financable", p.surface_financable, 21.5)
    test("Saint-Etienne, surface financable",
         float(vil.loc[vil.ville == "Saint-Étienne", "surface_financable"].iloc[0]), 70.4)

    d1 = dec[dec.ordre == "prix_puis_taux"].set_index("etape")
    d2 = dec[dec.ordre == "taux_puis_prix"].set_index("etape")
    test("decomposition, base 2021", d1.loc[1, "surface_m2"], 114.7, 0.05)
    test("decomposition, prix seuls", d1.loc[2, "surface_m2"], 107.8, 0.05)
    test("decomposition, total 2025", d1.loc[3, "surface_m2"], 88.6, 0.05)
    test("decomposition, taux seuls (ordre inverse)", d2.loc[2, "surface_m2"], 94.3, 0.05)
    test("part des taux, ordre prix->taux", d1.loc[3, "part_pct"], 73.0, 0.5)
    test("part des taux, ordre taux->prix", d2.loc[2, "part_pct"], 78.0, 0.5)
    test("panel constant", float(dec.n_communes_panel.iloc[0]), 12915.0, 0)
    test("perte totale en m2", d1.loc[2, "effet_m2"] + d1.loc[3, "effet_m2"], -26.1, 0.05)

    n2 = ser[ser.perimetre == "national"].set_index("annee")
    perte = n2.loc[2025, "surface_financable"] - n2.loc[2021, "surface_financable"]
    test("perte nationale en m2", perte, -29.5, 0.05)
    test("perte nationale en %", 100 * perte / n2.loc[2021, "surface_financable"], -24.8, 0.05)

    sne = src["sne"]
    dep = sne[sne.level == "Departement"].copy()
    dep["tension_ratio"] = pd.to_numeric(dep.tension_ratio, errors="coerce")
    dep["year"] = pd.to_numeric(dep.year, errors="coerce")
    test("tension mediane departementale 2025", dep[dep.year == 2025].tension_ratio.median(), 5.17, 0.01)

    cn = con[con.dimension == "national"].iloc[0]
    test("confort d'ete insuffisant", cn.pct_insuffisant, 40.0)
    test("confort d'ete bon", cn.pct_bon, 17.3)

    test("ratio parc social 2016 (aligne audit)", RATIO_SOCIAL_2016, 4.06, 0)
    test("ratio parc social 2025 (aligne audit)", RATIO_SOCIAL_2025, 7.34, 0)
    return res


# ---------- export ----------
def main():
    os.makedirs(SORTIE, exist_ok=True)
    src = charger()

    com = build_communes(src)
    ten = build_tension(src)
    qua = build_qualite(src)
    ser = build_series(src)
    con = build_confort(src)
    vil = build_villes(src)
    dec = build_decomposition(src)

    res = controles(com, ten, qua, ser, con, vil, dec, src)
    largeur = max(len(n) for n, *_ in res)
    print("CONTROLES DE CONFORMITE AU RAPPORT")
    print("-" * (largeur + 34))
    for nom, attendu, obtenu, ok in res:
        got = "n.d." if obtenu is None else f"{obtenu:.4g}"
        print(f"  {nom:<{largeur}}  attendu {attendu:>8}   obtenu {got:>9}   {'OK' if ok else '*** ECHEC ***'}")
    echecs = [n for n, _, _, ok in res if not ok]
    if echecs:
        print(f"\n{len(echecs)} controle(s) en echec — aucun fichier ecrit.")
        return 1

    tables = {"communes_acces.csv": com, "departements_tension.csv": ten,
              "departements_qualite.csv": qua, "series_temporelles.csv": ser,
              "confort_ete.csv": con, "villes.csv": vil,
              "decomposition_prix_taux.csv": dec}
    print("\nFICHIERS PRODUITS")
    total = 0
    for nom, df in tables.items():
        chemin = os.path.join(SORTIE, nom)
        df.to_csv(chemin, index=False, encoding="utf-8", float_format="%.6g")
        taille = os.path.getsize(chemin)
        total += taille
        print(f"  {nom:<28} {len(df):>7} lignes x {df.shape[1]:>2} col   {taille/1024:>8.1f} Ko")
    print(f"  {'TOTAL':<28} {'':>7}          {'':>2}      {total/1048576:>8.2f} Mo")
    if total > 20 * 1048576:
        print("\nDepassement du plafond de 20 Mo.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
