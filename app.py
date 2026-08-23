"""
app.py — Dashboard Mission 26004 / Que Choisir Ensemble
Diagnostic territorial de l'acces au logement. Usage interne QCE.
Les donnees proviennent de data_dashboard/, produit par pipeline/build_dashboard_data.py
depuis les sorties auditees de FINDINGS/. Aucun calcul n'est refait ici.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
import theme as th

th.configurer_page("Accès au logement")

ONGLETS = ["Vue d'ensemble"]

RATIO_SOCIAL_2016 = 4.06
RATIO_SOCIAL_2025 = 7.34


# ---------- filtres communs ----------
def filtres_departements(cle):
    noms = dl.noms_departements()
    codes = sorted(noms, key=lambda c: (len(c), c))
    libelles = {c: f"{c} — {noms.get(c, '')}".strip(" —") for c in codes}
    choix = st.sidebar.multiselect(
        "Départements", options=codes, default=[],
        format_func=lambda c: libelles[c], key=f"dep_{cle}",
        help="Aucune sélection = France entière")
    return choix


def appliquer_departements(df, choix, colonne="dep"):
    if not choix:
        return df
    return df[df[colonne].isin(choix)]


# ---------- onglet 1 : vue d'ensemble ----------
def vue_ensemble():
    th.bandeau(
        "Accès au logement — diagnostic territorial",
        "Trois voies d'accès au logement — location privée, accession, parc social — "
        "mesurées commune par commune, et la qualité du parc qui en résulte.")

    com = dl.communes()
    ten = dl.tension()
    qua = dl.qualite()
    ser = dl.series()

    deps = filtres_departements("vue")
    annee = st.sidebar.select_slider(
        "Année de la tension du parc social", options=list(range(2015, 2026)),
        value=2025, key="annee_vue")
    profil = st.sidebar.radio(
        "Profil de ménage", ["Ménage médian", "Ménage modeste (1er décile)"],
        key="profil_vue")

    com_f = appliquer_departements(com, deps)
    ten_f = appliquer_departements(ten, deps)
    qua_f = appliquer_departements(qua, deps)

    modeste = profil.startswith("Ménage modeste")
    col_effort = "effort_d1_familial" if modeste else "effort_median_familial"
    col_triple = "triple_peine_d1" if modeste else "triple_peine_median"

    perimetre = "France entière" if not deps else f"{len(deps)} département(s)"

    # indicateurs cles
    st.subheader("Les chiffres clés")
    c = st.columns(5)
    fiable_loyer = com_f[com_f.fiable_loyer_familial == True]
    effort = fiable_loyer[col_effort].dropna()
    with c[0]:
        th.kpi("Taux d'effort locatif",
               th.fmt(effort.median(), "taux"),
               f"logement familial · {len(effort):,} communes".replace(",", " "),
               critique=bool(len(effort) and effort.median() > 33))

    fiable_prix = com_f[com_f.fiable_prix == True]
    surface = fiable_prix.surface_financable.dropna()
    with c[1]:
        th.kpi("Surface finançable",
               th.fmt(surface.median(), "surface"),
               f"médiane · {len(surface):,} communes".replace(",", " "))

    col_tension = f"tension_{annee}"
    tens = ten_f[col_tension].dropna() if col_tension in ten_f.columns else pd.Series(dtype=float)
    with c[2]:
        th.kpi("Tension du parc social",
               th.fmt(tens.median(), "ratio"),
               f"demandes par attribution · {annee}")

    passoires = qua_f.dropna(subset=["taux_passoires", "n_dpe"])
    taux_pass = (100 * (passoires.taux_passoires / 100 * passoires.n_dpe).sum()
                 / passoires.n_dpe.sum()) if len(passoires) else np.nan
    with c[3]:
        th.kpi("Passoires énergétiques", th.fmt(taux_pass, "taux"),
               "logements classés F ou G")

    trois = com_f[com_f.n_legs_dispo == 3]
    n_triple = int(trois[col_triple].fillna(0).sum())
    part_triple = 100 * n_triple / len(trois) if len(trois) else np.nan
    with c[4]:
        th.kpi("Cumul des exclusions", th.fmt(n_triple, "entier"),
               f"communes sur {th.fmt(len(trois), 'entier')} · {th.fmt(part_triple, 'taux')}",
               critique=True)

    st.markdown("")

    # message principal
    gauche, droite = st.columns([3, 2], gap="large")

    with gauche:
        st.subheader("Vacance des logements et tension du parc social")
        st.caption(
            "Chaque point est un département. Les pointillés marquent les médianes nationales. "
            "Les logements vacants ne se situent pas là où les ménages attendent.")
        graphique_vacance_tension(ten, qua, deps, annee)

    with droite:
        st.subheader("Le message principal")
        st.markdown(f"""
L'accès au logement ne se referme pas partout de la même façon, et **le revenu pèse
davantage que le territoire**.

Pour un logement familial, le ménage médian consacre **{th.fmt(20.83, 'taux')}** de son
revenu au loyer ; le ménage du premier décile, **{th.fmt(42.69, 'taux')}** — le loyer étant
identique. La totalité de l'écart tient au seul niveau de revenu.

Côté accession, la capacité d'achat s'est contractée de **{th.fmt(-24.8, 'taux')}** entre
2021 et 2025 à revenu constant, dont **73 % à 78 %** imputables aux seules conditions de
crédit.

Le parc social, censé absorber ces exclusions, est lui-même saturé : le rapport national
entre demandes et attributions est passé de **{th.fmt(RATIO_SOCIAL_2016, 'ratio')}** en 2016
à **{th.fmt(RATIO_SOCIAL_2025, 'ratio')}** en 2025.
        """)
        st.info(
            f"Périmètre affiché : **{perimetre}** · profil **{profil.lower()}**. "
            "Les filtres de la barre latérale s'appliquent à l'ensemble de la page.",
            icon="ℹ️")

    # evolution de la capacite d'achat
    st.subheader("Érosion de la capacité d'achat, 2021-2025")
    graphique_serie(ser)

    # tableau et export
    st.subheader("Synthèse départementale")
    tableau = synthese_departementale(ten_f, qua_f, com_f, annee, col_effort, col_triple)
    st.dataframe(tableau, width="stretch", hide_index=True, height=320)
    th.bouton_csv(tableau, f"qce_vue_ensemble_{annee}.csv")

    th.source(
        "Sources : ANIL carte des loyers 2025 · INSEE Filosofi et recensement 2022 · "
        "DVF 2021-2025 · SNE 2025 · DPE ADEME. "
        "Agrégats produits par <code>pipeline/build_dashboard_data.py</code> depuis les sorties "
        "auditées du rapport — 23 contrôles de conformité au vert.")


def graphique_vacance_tension(ten, qua, deps, annee):
    col = f"tension_{annee}"
    if col not in ten.columns:
        st.warning(f"Pas de donnée de tension pour {annee}.")
        return
    d = ten[["dep", "nom", col]].merge(qua[["dep", "taux_vacance"]], on="dep", how="inner")
    d = d.dropna(subset=[col, "taux_vacance"])
    if d.empty:
        st.warning("Aucun département documenté sur ces deux dimensions.")
        return

    med_vac = d.taux_vacance.median()
    med_ten = d[col].median()
    cumul = (d.taux_vacance > med_vac) & (d[col] > med_ten)
    selection = d.dep.isin(deps) if deps else pd.Series(False, index=d.index)

    fig = go.Figure()
    for masque, nom, couleur, taille in (
        (~cumul, "Configuration contrastée", th.ECHELLE_BLEUE[3], 9),
        (cumul, "Vacance ET tension élevées", th.ROUGE, 11),
    ):
        s = d[masque]
        fig.add_trace(go.Scatter(
            x=s.taux_vacance, y=s[col], mode="markers", name=nom,
            marker=dict(size=taille, color=couleur, line=dict(width=1, color=th.BLANC)),
            customdata=np.stack([s.dep, s.nom.fillna("")], axis=-1),
            hovertemplate="<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                          "Vacance %{x:.1f} %<br>Tension %{y:.2f}<extra></extra>"))
    if selection.any():
        s = d[selection]
        fig.add_trace(go.Scatter(
            x=s.taux_vacance, y=s[col], mode="markers", name="Sélection",
            marker=dict(size=15, color=th.TRANSPARENT,
                        line=dict(width=2.5, color=th.BLEU_FONCE)),
            hoverinfo="skip"))

    fig.add_vline(x=med_vac, line=dict(color=th.GRIS, dash="dash", width=1.5))
    fig.add_hline(y=med_ten, line=dict(color=th.GRIS, dash="dash", width=1.5))
    fig.update_xaxes(title="Logements vacants (%)")
    fig.update_yaxes(title=f"Demandes par attribution ({annee})")
    st.plotly_chart(th.mise_en_forme_graphique(fig, 430), width="stretch")
    st.caption(
        f"Médianes nationales : {th.fmt(med_vac, 'taux')} de logements vacants et "
        f"{th.fmt(med_ten, 'ratio1')} demandes par attribution. "
        f"{int(cumul.sum())} départements cumulent les deux.")


def graphique_serie(ser):
    n = ser[ser.perimetre == "national"].sort_values("annee")
    if n.empty:
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=n.annee, y=n.surface_financable, name="Surface finançable",
        marker_color=[th.ROUGE if a == n.annee.max() else th.BLEU for a in n.annee],
        text=[th.fmt(v, "surface") for v in n.surface_financable],
        textposition="outside", textfont=dict(color=th.BLEU_FONCE),
        hovertemplate="<b>%{x}</b><br>%{y:.1f} m²<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=n.annee, y=n.taux_pct, name="Taux d'emprunt 20 ans (%)", yaxis="y2",
        mode="lines+markers", line=dict(color=th.BLEU_FONCE, width=2.5),
        marker=dict(size=8), hovertemplate="Taux %{y:.2f} %<extra></extra>"))
    fig.update_layout(
        yaxis=dict(title="m² finançables (médiane nationale)",
                   range=[0, n.surface_financable.max() * 1.2]),
        yaxis2=dict(title="Taux d'emprunt (%)", overlaying="y", side="right",
                    showgrid=False, range=[0, n.taux_pct.max() * 1.6]))
    st.plotly_chart(th.mise_en_forme_graphique(fig, 360), width="stretch")
    perte = n.surface_financable.iloc[-1] - n.surface_financable.iloc[0]
    st.caption(
        f"À revenu constant, la surface finançable médiane recule de "
        f"{th.fmt(abs(perte), 'surface')} entre 2021 et 2025, soit "
        f"{th.fmt(100 * perte / n.surface_financable.iloc[0], 'taux')}. "
        "Seuls les prix et les taux varient.")


def synthese_departementale(ten, qua, com, annee, col_effort, col_triple):
    col_tension = f"tension_{annee}"
    base = ten[["dep", "nom"]].copy()
    if col_tension in ten.columns:
        base["tension"] = ten[col_tension]

    fiable_loyer = com[com.fiable_loyer_familial == True]
    eff = fiable_loyer.groupby("dep")[col_effort].median().rename("effort")
    fiable_prix = com[com.fiable_prix == True]
    surf = fiable_prix.groupby("dep").surface_financable.median().rename("surface")

    trois = com[com.n_legs_dispo == 3]
    tp = trois.groupby("dep")[col_triple].agg(["sum", "count"])
    tp["part_triple"] = 100 * tp["sum"] / tp["count"]

    out = (base.merge(eff, on="dep", how="left")
               .merge(surf, on="dep", how="left")
               .merge(tp[["sum", "count", "part_triple"]], on="dep", how="left")
               .merge(qua[["dep", "taux_passoires", "cout_median", "taux_suroccupation"]],
                      on="dep", how="left"))

    out = out.rename(columns={"sum": "n_triple", "count": "n_communes_3ind"})
    affichage = pd.DataFrame({
        "Dép.": out.dep,
        "Département": out.nom,
        "Taux d'effort": out.effort.map(lambda v: th.fmt(v, "taux")),
        "Surface finançable": out.surface.map(lambda v: th.fmt(v, "surface")),
        "Tension": out.get("tension", pd.Series(np.nan, index=out.index)).map(
            lambda v: th.fmt(v, "ratio")),
        "Passoires": out.taux_passoires.map(lambda v: th.fmt(v, "taux")),
        "Coût énergie": out.cout_median.map(lambda v: th.fmt(v, "euro")),
        "Suroccupation": out.taux_suroccupation.map(lambda v: th.fmt(v, "taux")),
        "Cumul des exclusions": out.apply(
            lambda r: "n.d." if pd.isna(r.n_triple)
            else f"{int(r.n_triple)} / {int(r.n_communes_3ind)}", axis=1),
    })
    return affichage.sort_values("Dép.").reset_index(drop=True)


# ---------- navigation ----------
def main():
    st.sidebar.markdown("### Que Choisir Ensemble")
    st.sidebar.caption("Mission 26004 · diagnostic territorial de l'accès au logement")
    st.sidebar.markdown("---")

    if len(ONGLETS) == 1:
        vue_ensemble()
    else:
        for onglet, contenu in zip(st.tabs(ONGLETS), [vue_ensemble]):
            with onglet:
                contenu()

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Données au 22 août 2026. Confort d'été : extraction ADEME du 27 juillet 2026, figée. "
        "Voir METHODOLOGIE_DONNEES.md.")


if __name__ == "__main__":
    main()
