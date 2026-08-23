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

ONGLETS = ["Vue d'ensemble", "Parc locatif privé"]

RATIO_SOCIAL_2016 = 4.06
RATIO_SOCIAL_2025 = 7.34

BORNES_EFFORT = [-np.inf, 20, 33, 50, np.inf]
CATEGORIES_EFFORT = ["Accessible", "Modéré", "Effort important", "Insoutenable"]
SEUIL_EFFORT = 33


# ---------- filtres communs, rendus dans le corps de l'onglet ----------
def selecteur_departements(conteneur, cle):
    noms = dl.noms_departements()
    codes = sorted(noms, key=lambda c: (len(c), c))
    libelles = {c: f"{c} — {noms.get(c, '')}".strip(" —") for c in codes}
    return conteneur.multiselect(
        "Départements", options=codes, default=[],
        format_func=lambda c: libelles[c], key=f"dep_{cle}",
        placeholder="France entière")


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

    f1, f2, f3 = st.columns([2, 1, 1], gap="medium")
    deps = selecteur_departements(f1, "vue")
    annee = f2.select_slider("Année de la tension du parc social",
                             options=list(range(2015, 2026)), value=2025, key="annee_vue")
    profil = f3.radio("Profil de ménage",
                      ["Ménage médian", "Ménage modeste (1er décile)"], key="profil_vue")

    com_f = appliquer_departements(com, deps)
    ten_f = appliquer_departements(ten, deps)
    qua_f = appliquer_departements(qua, deps)

    modeste = profil.startswith("Ménage modeste")
    col_effort = "effort_d1_familial" if modeste else "effort_median_familial"
    col_triple = "triple_peine_d1" if modeste else "triple_peine_median"

    perimetre = "France entière" if not deps else f"{len(deps)} département(s)"
    if modeste:
        th.perimetre_modeste(int(com_f[com_f.fiable_loyer_familial == True]
                                 .effort_d1_familial.notna().sum()))

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
    st.plotly_chart(
        th.mise_en_forme_graphique(
            fig, 430, f"Vacance des logements et tension du parc social, {annee}"),
        width="stretch")
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
    st.plotly_chart(
        th.mise_en_forme_graphique(
            fig, 360, "Surface finançable médiane et taux d'emprunt sur 20 ans"),
        width="stretch")
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


# ---------- onglet 2 : parc locatif prive ----------
def parc_locatif():
    th.bandeau(
        "Accès au parc locatif privé",
        "Le même logement, au même loyer, se révèle accessible à une partie de la population "
        "et hors de portée pour une autre. La difficulté n'est pas territoriale, elle est "
        "distributive.")

    com = dl.communes()
    vil = dl.villes()

    f1, f2, f3 = st.columns([2, 1, 1], gap="medium")
    deps = selecteur_departements(f1, "loc")
    profil = f2.radio("Profil de ménage",
                      ["Ménage médian", "Ménage modeste (1er décile)"], key="profil_loc")
    segment = f3.radio("Segment de logement",
                       ["Logement familial (3 pièces et +)", "Petit logement (1-2 pièces)"],
                       key="segment_loc")

    modeste = profil.startswith("Ménage modeste")
    familial = segment.startswith("Logement familial")
    suffixe = "familial" if familial else "petit"
    col_effort = f"effort_{'d1' if modeste else 'median'}_{suffixe}"
    col_fiable = f"fiable_loyer_{suffixe}"

    com_f = appliquer_departements(com, deps)
    base = com_f[com_f[col_fiable] == True].dropna(subset=[col_effort])
    n_modeste = int(com_f[com_f[col_fiable] == True][f"effort_d1_{suffixe}"].notna().sum())
    th.perimetre_modeste(n_modeste)

    # indicateurs des deux profils, cote a cote
    st.subheader("Le même loyer, deux capacités contributives")
    fiable = com_f[com_f[col_fiable] == True]
    med = fiable.dropna(subset=[f"effort_median_{suffixe}"])
    d1 = fiable.dropna(subset=[f"effort_d1_{suffixe}"])
    loyer = fiable[f"loyer_{suffixe}"].median()

    c = st.columns(4)
    with c[0]:
        th.kpi("Loyer mensuel médian", th.fmt(loyer, "euro"),
               f"{segment.split(' (')[0].lower()}")
    with c[1]:
        v = med[f"effort_median_{suffixe}"].median()
        th.kpi("Effort · ménage médian", th.fmt(v, "taux"),
               f"{th.fmt(len(med))} communes", critique=bool(v and v > SEUIL_EFFORT))
    with c[2]:
        v = d1[f"effort_d1_{suffixe}"].median()
        th.kpi("Effort · ménage modeste", th.fmt(v, "taux"),
               f"{th.fmt(len(d1))} communes", critique=bool(v and v > SEUIL_EFFORT))
    with c[3]:
        part = 100 * (d1[f"effort_d1_{suffixe}"] > SEUIL_EFFORT).mean() if len(d1) else np.nan
        n_sup = int((d1[f"effort_d1_{suffixe}"] > SEUIL_EFFORT).sum()) if len(d1) else 0
        th.kpi("Communes au-delà de 33 %", th.fmt(part, "taux"),
               f"{th.fmt(n_sup)} sur {th.fmt(len(d1))} · ménage modeste", critique=True)

    st.caption(
        f"Le loyer médian est identique pour les deux profils : "
        f"{th.fmt(loyer, 'euro')} par mois. Seule la capacité contributive change. "
        "La totalité de l'écart d'effort tient au seul niveau de revenu.")

    # repartition par categorie d'effort
    st.subheader("Répartition des communes par catégorie d'effort")
    graphique_categories(fiable, suffixe)

    # classement departemental
    gauche, droite = st.columns([3, 2], gap="large")
    with gauche:
        st.subheader("Taux d'effort par département")
        graphique_departements(base, col_effort, profil, segment)
    with droite:
        st.subheader("Les grandes villes")
        tableau_villes(vil, deps, modeste)

    # export
    st.subheader("Détail communal")
    colonnes = ["insee_c", "libgeo", "dep", f"loyer_{suffixe}",
                "revenu_menage_proxy", "revenu_menage_d1",
                f"effort_median_{suffixe}", f"effort_d1_{suffixe}"]
    detail = base[colonnes].copy()
    apercu = detail.head(200).copy()
    for c_ in (f"effort_median_{suffixe}", f"effort_d1_{suffixe}"):
        apercu[c_] = apercu[c_].map(lambda v: th.fmt(v, "taux"))
    for c_ in (f"loyer_{suffixe}", "revenu_menage_proxy", "revenu_menage_d1"):
        apercu[c_] = apercu[c_].map(lambda v: th.fmt(v, "euro"))
    st.dataframe(apercu, width="stretch", hide_index=True, height=280)
    st.caption(f"Aperçu des 200 premières lignes sur {th.fmt(len(detail))}. "
               "L'export contient l'intégralité du périmètre filtré.")
    th.bouton_csv(detail, f"qce_effort_locatif_{suffixe}.csv")

    th.source(
        "Sources : ANIL carte des loyers 2025 × INSEE Filosofi. Le revenu est un revenu de "
        "ménage reconstitué (niveau de vie × unités de consommation par ménage). "
        "Surfaces de référence : 37 m² pour le petit logement, 72 m² pour le logement familial.")


def graphique_categories(fiable, suffixe):
    lignes = []
    for cle, libelle, colonne in (
        ("median", "Ménage médian", f"effort_median_{suffixe}"),
        ("d1", "Ménage modeste (1er décile)", f"effort_d1_{suffixe}"),
    ):
        s = fiable.dropna(subset=[colonne])
        if s.empty:
            continue
        cat = pd.cut(s[colonne], bins=BORNES_EFFORT, labels=CATEGORIES_EFFORT, right=False)
        vc = cat.value_counts().reindex(CATEGORIES_EFFORT)
        for nom in CATEGORIES_EFFORT:
            lignes.append(dict(profil=libelle, categorie=nom, n=int(vc[nom]),
                               part=100 * vc[nom] / len(s), total=len(s)))
    if not lignes:
        st.warning("Aucune commune documentée sur ce périmètre.")
        return
    d = pd.DataFrame(lignes)

    fig = go.Figure()
    for nom in CATEGORIES_EFFORT:
        s = d[d.categorie == nom]
        fig.add_trace(go.Bar(
            y=s.profil, x=s.part, name=nom, orientation="h",
            marker_color=th.CATEGORIES_EFFORT[nom],
            text=[th.fmt(v, "taux") if v >= 4 else "" for v in s.part],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color=th.BLANC, size=12),
            customdata=np.stack([s.n, s.total], axis=-1),
            hovertemplate="<b>%{y}</b><br>" + nom +
                          " : %{x:.1f} %<br>%{customdata[0]} communes sur %{customdata[1]}"
                          "<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis=dict(title="Part des communes (%)", range=[0, 100]),
                      yaxis=dict(title=""))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 260, "Catégories d'effort locatif, par profil de ménage"),
        width="stretch")
    st.caption(
        "Seuils : accessible en dessous de 20 %, modéré de 20 à 33 %, effort important de 33 à "
        "50 %, insoutenable au-delà de 50 %. "
        + th.perimetre_modeste(inline=True).replace("<b>", "").replace("</b>", ""))


def graphique_departements(base, col_effort, profil, segment):
    if base.empty:
        st.warning("Aucune commune documentée sur ce périmètre.")
        return
    noms = dl.noms_departements()
    d = (base.groupby("dep")[col_effort].agg(["median", "count"])
             .reset_index().rename(columns={"median": "effort", "count": "n"}))
    d = d[d.n >= 3].sort_values("effort")
    d["nom"] = d.dep.map(noms).fillna(d.dep)

    couleurs = [th.ROUGE if v > SEUIL_EFFORT else th.BLEU for v in d.effort]
    fig = go.Figure(go.Bar(
        x=d.effort, y=d.nom, orientation="h", marker_color=couleurs,
        customdata=np.stack([d.dep, d.n], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Effort %{x:.1f} %<br>"
                      "%{customdata[1]} communes<extra></extra>"))
    fig.add_vline(x=SEUIL_EFFORT, line=dict(color=th.BLEU_FONCE, dash="dash", width=1.5))
    fig.update_layout(xaxis=dict(title="Taux d'effort médian (%)"),
                      yaxis=dict(title="", tickfont=dict(size=9)))
    hauteur = max(420, 16 * len(d))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, hauteur, f"{profil} · {segment.split(' (')[0]}"),
        width="stretch")
    st.caption(
        f"Médiane des taux communaux, départements documentés sur au moins 3 communes. "
        f"La ligne marque le seuil de 33 %. "
        f"{int((d.effort > SEUIL_EFFORT).sum())} département(s) au-delà.")


def tableau_villes(vil, deps, modeste):
    v = vil.copy()
    if deps:
        v = v[v.dep.isin(deps)]
    if v.empty:
        st.info("Aucune ville de plus de 100 000 habitants dans la sélection.")
        return
    colonne = "effort_d1_familial" if modeste else "effort_familial"
    v = v.sort_values(colonne, ascending=False)
    affichage = pd.DataFrame({
        "Ville": v.ville,
        "Dép.": v.dep,
        "Petit logement": v.effort_petit.map(lambda x: th.fmt(x, "taux")),
        "Familial · médian": v.effort_familial.map(lambda x: th.fmt(x, "taux")),
        "Familial · modeste": v.effort_d1_familial.map(lambda x: th.fmt(x, "taux")),
    })
    st.dataframe(affichage, width="stretch", hide_index=True, height=460)
    st.caption(
        "Communes de plus de 100 000 habitants, classées par effort décroissant du profil "
        "affiché. Paris culmine à "
        f"{th.fmt(float(vil.loc[vil.ville == 'Paris', 'effort_familial'].iloc[0]), 'taux')} "
        "pour un ménage médian et "
        f"{th.fmt(float(vil.loc[vil.ville == 'Paris', 'effort_d1_familial'].iloc[0]), 'taux')} "
        "pour un ménage modeste — niveau qui rend l'accès arithmétiquement impossible.")


# ---------- navigation ----------
def main():
    st.sidebar.markdown("### Que Choisir Ensemble")
    st.sidebar.caption("Mission 26004 · diagnostic territorial de l'accès au logement")
    st.sidebar.markdown("---")

    if len(ONGLETS) == 1:
        vue_ensemble()
    else:
        for onglet, contenu in zip(st.tabs(ONGLETS), [vue_ensemble, parc_locatif]):
            with onglet:
                contenu()

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Données au 22 août 2026. Confort d'été : extraction ADEME du 27 juillet 2026, figée. "
        "Voir METHODOLOGIE_DONNEES.md.")


if __name__ == "__main__":
    main()
