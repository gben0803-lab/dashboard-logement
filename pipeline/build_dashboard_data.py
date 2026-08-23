#!/usr/bin/env python3
"""
build_dashboard_data.py — Mission 26004 / Que Choisir Ensemble

Construit data_dashboard/ a partir des sorties deja auditees de FINDINGS/.
Aucune lecture des bases brutes : DVF_clean, DPE_clean et RPLS_clean ne sont
jamais ouverts. Les CSV de FINDINGS/ font foi.

Sorties : communes_acces.csv, departements_tension.csv, departements_qualite.csv,
          series_temporelles.csv, confort_ete.csv
"""

import json
import os
import sys
import unicodedata

import numpy as np
import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE2 = os.path.join(RACINE, "FINDINGS", "Phase2")
BASES = os.path.join(RACINE, "Base de données")
SORTIE = os.path.join(RACINE, "data_dashboard")

RATIO_SOCIAL_2016 = 4.06
RATIO_SOCIAL_2025 = 7.34


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
def controles(com, ten, qua, ser, con, src):
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

    res = controles(com, ten, qua, ser, con, src)
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
              "confort_ete.csv": con}
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
