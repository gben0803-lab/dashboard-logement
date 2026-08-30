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

ONGLETS = ["Vue d'ensemble", "Parc locatif privé", "Accession à la propriété",
           "Parc social et cumul", "Qualité du parc"]

RATIO_SOCIAL_2016 = 4.06
RATIO_SOCIAL_2025 = 7.34

BORNES_EFFORT = [-np.inf, 20, 33, 50, np.inf]
CATEGORIES_EFFORT = ["Accessible", "Modéré", "Effort important", "Insoutenable"]
SEUIL_EFFORT = 33
SURFACE_FAMILIALE = 72
VILLE_ATYPIQUE = "Brest"
SEUIL_SURFACE_CUMUL = 40
SEUILS_SENSIBILITE = (35, 40, 45)
ETIQUETTES_DPE = ["A", "B", "C", "D", "E", "F", "G"]
DATE_EXTRACTION_ADEME = "27 juillet 2026"

# Libelles d'affichage des tableaux de detail. Les CSV exportes conservent les noms
# techniques : ils sont la cle entre le pipeline, le dashboard et la table QCE, et sont
# documentes dans le dictionnaire de METHODOLOGIE_DONNEES.md. Ne renommer qu'a l'affichage.
LIBELLES_COLONNES = {
    "insee_c": "Code INSEE",
    "libgeo": "Commune",
    "dep": "Dép.",
    "effort_median_familial": "Effort · ménage médian",
    "effort_d1_familial": "Effort · ménage modeste",
    "effort_median_petit": "Effort · ménage médian",
    "effort_d1_petit": "Effort · ménage modeste",
    "surface_financable": "Surface finançable",
    "tension_2025": "Demandes / attribution",
    "n_legs_dispo": "Indicateurs disponibles",
    "triple_peine_median": "Triple peine",
    "triple_peine_d1": "Triple peine · ménage modeste",
    "loyer_familial": "Loyer mensuel",
    "loyer_petit": "Loyer mensuel",
    "revenu_menage_proxy": "Revenu du ménage médian",
    "revenu_menage_d1": "Revenu du ménage modeste",
    "prix_m2_tous": "Prix au m²",
    "n_ventes_tous": "Ventes retenues",
    "categorie_surface": "Catégorie de surface",
}

MENTION_EXPORT = ("Les deux fichiers contiennent les mêmes valeurs et conservent les noms "
                  "techniques des colonnes, documentés dans METHODOLOGIE_DONNEES.md. "
                  "Le CSV est au format français — point-virgule, virgule décimale.")


def libelles(df):
    """Renomme pour l'affichage seulement. Le DataFrame exporte n'est pas touche."""
    return df.rename(columns={c: LIBELLES_COLONNES.get(c, c) for c in df.columns})


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
        st.subheader("L'écart tient au revenu, pas au territoire")
        st.caption(
            "Logement familial, parc locatif privé. Le loyer est identique pour les deux "
            "profils : seul le revenu change. La totalité de l'écart vient de là.")
        graphique_ecart_profils(com_f)

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
            "Les filtres en tête d'onglet s'appliquent à l'ensemble de la page.",
            icon="ℹ️")

    # evolution de la capacite d'achat
    st.subheader("Érosion de la capacité d'achat, 2021-2025")
    graphique_serie(ser)

    # le parc social : point de comparaison, pas le sujet
    st.subheader("Vacance des logements et tension du parc social")
    st.caption(
        "Chaque point est un département. Les pointillés marquent les médianes nationales. "
        "Les logements vacants ne se situent pas là où les ménages attendent. "
        "Le parc social est ici le point de comparaison, non l'objet du diagnostic.")
    graphique_vacance_tension(ten, qua, deps, annee)

    # tableau et export
    st.subheader("Synthèse départementale")
    tableau = synthese_departementale(ten_f, qua_f, com_f, annee, col_effort, col_triple)
    st.dataframe(tableau, width="stretch", hide_index=True, height=320)
    th.boutons_export(tableau, f"qce_vue_ensemble_{annee}", f"Vue d'ensemble {annee}")
    st.caption(MENTION_EXPORT)

    th.source(
        "Sources : ANIL carte des loyers 2025 · INSEE Filosofi et recensement 2022 · "
        "DVF 2021-2025 · SNE 2025 · DPE ADEME. "
        "Agrégats produits par <code>pipeline/build_dashboard_data.py</code> depuis les sorties "
        "auditées du rapport — 47 contrôles de conformité au vert.")


def graphique_ecart_profils(com_f):
    """Ecart d'effort locatif entre menage median et menage modeste, logement familial.

    Les quatre valeurs affichees figurent parmi les controles de conformite au rapport :
    14,8 / 20,8 pour le menage median, 29,5 / 42,7 pour le menage modeste, et 2,6 % /
    86,6 % de communes au-dela du seuil de 33 %. Rien n'est recalcule ici.
    """
    fiable = com_f[com_f.fiable_loyer_familial == True]
    med = fiable.effort_median_familial.dropna()
    d1 = fiable.effort_d1_familial.dropna()
    if med.empty or d1.empty:
        st.warning("Aucune commune fiable sur ce périmètre.")
        return

    profils = ["Ménage médian", "Ménage modeste"]
    valeurs = [med.median(), d1.median()]
    parts = [100 * (med > SEUIL_EFFORT).mean(), 100 * (d1 > SEUIL_EFFORT).mean()]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=profils, y=valeurs, marker_color=[th.BLEU, th.ROUGE], width=0.5,
        text=[th.fmt(v, "taux") for v in valeurs], textposition="outside",
        textfont=dict(color=th.BLEU_FONCE, size=15),
        hovertemplate="<b>%{x}</b><br>%{y:.1f} % du revenu<extra></extra>"))
    fig.add_hline(
        y=SEUIL_EFFORT, line=dict(color=th.GRIS, dash="dash", width=1.5),
        annotation_text=f"Seuil de soutenabilité, {SEUIL_EFFORT} %",
        annotation_position="top left",
        annotation_font=dict(size=11, color=th.GRIS))
    fig.update_layout(
        xaxis=dict(title="", type="category"),
        yaxis=dict(title="Part du revenu consacrée au loyer (%)",
                   range=[0, max(valeurs) * 1.35]))
    st.plotly_chart(
        th.mise_en_forme_graphique(
            fig, 430, "Effort locatif selon le profil de ménage, logement familial"),
        width="stretch")
    st.caption(
        f"Loyer médian identique dans les deux cas. Le ménage médian y consacre "
        f"**{th.fmt(valeurs[0], 'taux')}** de son revenu, le ménage modeste "
        f"**{th.fmt(valeurs[1], 'taux')}**. Au-delà du seuil de {SEUIL_EFFORT} % : "
        f"**{th.fmt(parts[0], 'taux')}** des communes pour le premier, "
        f"**{th.fmt(parts[1], 'taux')}** pour le second.")


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
        marker_color=[th.BLEU_FONCE if a == n.annee.min() else th.BLEU for a in n.annee],
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
    st.dataframe(libelles(apercu), width="stretch", hide_index=True, height=280)
    st.caption(f"Aperçu des 200 premières lignes sur {th.fmt(len(detail))}. "
               "L'export contient l'intégralité du périmètre filtré.")
    th.boutons_export(detail, f"qce_effort_locatif_{suffixe}", f"Effort locatif {suffixe}")
    st.caption(MENTION_EXPORT)

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


def extremes(d, tout, n=15):
    """Limite un classement aux n premiers et n derniers, sauf demande contraire."""
    if tout or len(d) <= 2 * n:
        return d, False
    return pd.concat([d.head(n), d.tail(n)]), True


def graphique_departements(base, col_effort, profil, segment):
    if base.empty:
        st.warning("Aucune commune documentée sur ce périmètre.")
        return
    noms = dl.noms_departements()
    d = (base.groupby("dep")[col_effort].agg(["median", "count"])
             .reset_index().rename(columns={"median": "effort", "count": "n"}))
    d = d[d.n >= 3].sort_values("effort")
    d["nom"] = d.dep.map(noms).fillna(d.dep)
    total = len(d)
    tout = st.checkbox(f"Afficher les {total} départements", key="tous_dep_effort")
    d, tronque = extremes(d, tout)

    couleurs = [th.ROUGE if v > SEUIL_EFFORT else th.BLEU for v in d.effort]
    fig = go.Figure(go.Bar(
        x=d.effort, y=d.nom, orientation="h", marker_color=couleurs,
        customdata=np.stack([d.dep, d.n], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Effort %{x:.1f} %<br>"
                      "%{customdata[1]} communes<extra></extra>"))
    fig.add_vline(x=SEUIL_EFFORT, line=dict(color=th.BLEU_FONCE, dash="dash", width=1.5))
    fig.update_layout(xaxis=dict(title="Taux d'effort médian (%)"),
                      yaxis=dict(title="", tickfont=dict(size=9)))
    hauteur = max(420, 18 * len(d))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, hauteur, f"{profil} · {segment.split(' (')[0]}"),
        width="stretch")
    st.caption(
        f"Médiane des taux communaux, départements documentés sur au moins 3 communes. "
        f"La ligne marque le seuil de 33 %. "
        + (f"Affichage des 15 départements les moins contraints et des 15 plus contraints, "
           f"sur {total}." if tronque else f"{total} départements affichés."))


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


# ---------- onglet 3 : accession a la propriete ----------
def accession():
    th.bandeau(
        "Accès à la propriété",
        "À revenu constant, la capacité d'acquisition s'est contractée d'un quart en quatre ans. "
        "La perte vient du crédit, pas des prix.")

    com = dl.communes()
    ser = dl.series()
    dec = dl.decomposition()
    vil = dl.villes()

    f1, f2 = st.columns([2, 1], gap="medium")
    deps = selecteur_departements(f1, "acc")
    vue_villes = f2.radio("Vue complémentaire", ["Grandes villes", "Aucune"], key="vue_acc")

    com_f = appliquer_departements(com, deps)
    fiable = com_f[com_f.fiable_prix == True].dropna(subset=["surface_financable"])

    # indicateurs
    st.subheader("La capacité d'acquisition aujourd'hui")
    nat = ser[ser.perimetre == "national"].sort_values("annee")
    d1 = dec[dec.ordre == "prix_puis_taux"].set_index("etape")
    d2 = dec[dec.ordre == "taux_puis_prix"].set_index("etape")
    perte = nat.surface_financable.iloc[-1] - nat.surface_financable.iloc[0]

    c = st.columns(5)
    with c[0]:
        th.kpi("Surface finançable médiane", th.fmt(fiable.surface_financable.median(), "surface"),
               f"{th.fmt(len(fiable))} communes au prix fiable")
    with c[1]:
        sous = 100 * (fiable.surface_financable < SURFACE_FAMILIALE).mean() if len(fiable) else np.nan
        th.kpi(f"Sous {SURFACE_FAMILIALE} m²", th.fmt(sous, "taux"),
               "ne peut financer un logement familial", critique=True)
    with c[2]:
        th.kpi("Perte depuis 2021", th.fmt(abs(perte), "surface"),
               f"soit {th.fmt(100 * perte / nat.surface_financable.iloc[0], 'taux')} "
               "à revenu constant", critique=True)
    with c[3]:
        th.kpi("Part imputable au crédit",
               f"{th.fmt(d1.loc[3, 'part_pct'], 'taux0', unite=False)} à "
               f"{th.fmt(d2.loc[2, 'part_pct'], 'taux0')}",
               "selon l'ordre de décomposition")
    with c[4]:
        th.kpi("Taux d'emprunt 20 ans", th.fmt(nat.taux_pct.iloc[-1], "taux2"),
               f"contre {th.fmt(nat.taux_pct.iloc[0], 'taux2')} en 2021")

    # geographie
    st.subheader("Surface finançable par département")
    graphique_surface_departements(fiable)

    # serie et decomposition
    gauche, droite = st.columns(2, gap="large")
    with gauche:
        st.subheader("Évolution 2021-2025")
        graphique_serie_accession(nat)
    with droite:
        st.subheader("D'où vient la perte ?")
        graphique_decomposition(dec)

    if vue_villes == "Grandes villes":
        st.subheader("Les grandes villes")
        tableau_villes_accession(vil, deps)

    # export
    st.subheader("Détail communal")
    colonnes = ["insee_c", "libgeo", "dep", "prix_m2_tous", "n_ventes_tous",
                "revenu_menage_proxy", "surface_financable", "categorie_surface"]
    detail = fiable[colonnes].copy()
    apercu = detail.head(200).copy()
    apercu["prix_m2_tous"] = apercu.prix_m2_tous.map(lambda v: th.fmt(v, "euro"))
    apercu["revenu_menage_proxy"] = apercu.revenu_menage_proxy.map(lambda v: th.fmt(v, "euro"))
    apercu["surface_financable"] = apercu.surface_financable.map(lambda v: th.fmt(v, "surface"))
    st.dataframe(libelles(apercu), width="stretch", hide_index=True, height=280)
    st.caption(f"Aperçu des 200 premières lignes sur {th.fmt(len(detail))}. "
               "L'export contient l'intégralité du périmètre filtré.")
    th.boutons_export(detail, "qce_surface_financable", "Surface finançable")
    st.caption(MENTION_EXPORT)

    th.source(
        "Sources : DVF 2021-2025 × INSEE Filosofi × Observatoire Crédit Logement / CSA. "
        "Hypothèses : 35 % d'endettement maximal, 240 mois, assurance 0,30 % par an, "
        "apport 10 %, frais de mutation 8 %. Le revenu est figé sur un millésime unique : la "
        "série isole l'effet des prix et des taux, elle ne mesure pas une perte de niveau de vie.")


def graphique_surface_departements(fiable):
    if fiable.empty:
        st.warning("Aucune commune au prix fiable sur ce périmètre.")
        return
    noms = dl.noms_departements()
    d = (fiable.groupby("dep").surface_financable.agg(["median", "count"])
               .reset_index().rename(columns={"median": "surface", "count": "n"}))
    d = d[d.n >= 3].sort_values("surface", ascending=False)
    d["nom"] = d.dep.map(noms).fillna(d.dep)
    total = len(d)
    tout = st.checkbox(f"Afficher les {total} départements", key="tous_dep_surface")
    d, tronque = extremes(d, tout)

    couleurs = [th.ROUGE if v < SURFACE_FAMILIALE else th.BLEU for v in d.surface]
    fig = go.Figure(go.Bar(
        x=d.surface, y=d.nom, orientation="h", marker_color=couleurs,
        customdata=np.stack([d.dep, d.n], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>%{x:.1f} m²<br>"
                      "%{customdata[1]} communes<extra></extra>"))
    fig.add_vline(x=SURFACE_FAMILIALE, line=dict(color=th.BLEU_FONCE, dash="dash", width=1.5))
    fig.update_layout(xaxis=dict(title="Surface finançable médiane (m²)"),
                      yaxis=dict(title="", tickfont=dict(size=9)))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, max(420, 18 * len(d)),
                                   "Surface finançable médiane par département, 2025"),
        width="stretch")
    st.caption(
        f"Médiane des surfaces communales, départements documentés sur au moins 3 communes. "
        f"La ligne marque les {SURFACE_FAMILIALE} m² du logement familial de référence. "
        + (f"Affichage des 15 départements les plus favorables et des 15 plus contraints, "
           f"sur {total}." if tronque else f"{total} départements affichés."))


def graphique_serie_accession(nat):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=nat.annee, y=nat.surface_financable, name="Surface finançable",
        marker_color=[th.BLEU_FONCE if a == nat.annee.min() else th.BLEU for a in nat.annee],
        text=[th.fmt(v, "surface") for v in nat.surface_financable],
        textposition="outside", textfont=dict(color=th.BLEU_FONCE),
        customdata=np.stack([nat.taux_pct, nat.prix_m2_median, nat.n_communes], axis=-1),
        hovertemplate="<b>%{x}</b><br>%{y:.1f} m²<br>Taux %{customdata[0]:.2f} %<br>"
                      "Prix médian %{customdata[1]:.0f} €/m²<br>"
                      "%{customdata[2]:.0f} communes fiables<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=nat.annee, y=nat.taux_pct, name="Taux d'emprunt 20 ans (%)", yaxis="y2",
        mode="lines+markers", line=dict(color=th.BLEU_FONCE, width=2.5), marker=dict(size=8),
        hovertemplate="Taux %{y:.2f} %<extra></extra>"))
    fig.update_layout(
        yaxis=dict(title="m² finançables", range=[0, nat.surface_financable.max() * 1.22]),
        yaxis2=dict(title="Taux (%)", overlaying="y", side="right", showgrid=False,
                    range=[0, nat.taux_pct.max() * 1.6]))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 380, "Surface finançable et taux d'emprunt, 2021-2025"),
        width="stretch")
    st.caption(
        "Le prix médian au m² est quasiment stable depuis 2023 "
        f"({th.fmt(nat.prix_m2_median.iloc[2], 'euro')} puis "
        f"{th.fmt(nat.prix_m2_median.iloc[-1], 'euro')}), quand le taux passe de "
        f"{th.fmt(nat.taux_pct.iloc[0], 'taux2')} à {th.fmt(nat.taux_pct.iloc[-1], 'taux2')}.")


def graphique_decomposition(dec):
    d1 = dec[dec.ordre == "prix_puis_taux"].set_index("etape")
    d2 = dec[dec.ordre == "taux_puis_prix"].set_index("etape")
    etapes = ["2021\nprix et taux 2021", "effet PRIX\nprix 2025, taux 2021",
              "effet TAUX\nprix et taux 2025"]
    vals = [d1.loc[1, "surface_m2"], d1.loc[2, "surface_m2"], d1.loc[3, "surface_m2"]]

    fig = go.Figure(go.Bar(
        x=etapes, y=vals, marker_color=[th.ECHELLE_BLEUE[2], th.BLEU, th.ROUGE],
        text=[th.fmt(v, "surface") for v in vals], textposition="outside",
        textfont=dict(color=th.BLEU_FONCE),
        hovertemplate="%{x}<br>%{y:.1f} m²<extra></extra>"))
    fig.add_annotation(x=0.5, y=(vals[0] + vals[1]) / 2 + 8, showarrow=False,
                       text=f"<b>{th.fmt(d1.loc[2, 'effet_m2'], 'surface')}</b>",
                       font=dict(color=th.BLEU, size=13))
    fig.add_annotation(x=1.5, y=(vals[1] + vals[2]) / 2 + 8, showarrow=False,
                       text=f"<b>{th.fmt(d1.loc[3, 'effet_m2'], 'surface')}</b>",
                       font=dict(color=th.ROUGE, size=13))
    fig.update_layout(yaxis=dict(title="m² finançables", range=[0, vals[0] * 1.25]),
                      xaxis=dict(title="", type="category", tickfont=dict(size=10)))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 380, "Décomposition de la perte entre prix et taux"),
        width="stretch")
    st.caption(
        f"Panel constant de {th.fmt(dec.n_communes_panel.iloc[0])} communes au prix fiable en "
        f"2021 et en 2025 — d'où une base de {th.fmt(vals[0], 'surface')}, inférieure aux "
        f"119,1 m² de la série nationale qui porte sur 16 947 communes. "
        f"Les conditions de crédit expliquent "
        f"{th.fmt(d1.loc[3, 'part_pct'], 'taux0', unite=False)} à "
        f"{th.fmt(d2.loc[2, 'part_pct'], 'taux0')} de la contraction selon l'ordre retenu.")


def tableau_villes_accession(vil, deps):
    v = vil.dropna(subset=["surface_financable"]).copy()
    if deps:
        v = v[v.dep.isin(deps)]
    if v.empty:
        st.info("Aucune ville de plus de 100 000 habitants dans la sélection.")
        return
    v = v.sort_values("surface_financable")
    affichage = pd.DataFrame({
        "Ville": v.ville,
        "Dép.": v.dep,
        "Prix appartement": v.prix_m2_appart.map(lambda x: th.fmt(x, "euro")),
        "Revenu ménage": v.revenu_menage.map(lambda x: th.fmt(x, "euro")),
        "Surface finançable": v.surface_financable.map(lambda x: th.fmt(x, "surface")),
        "2021": v.surface_2021.map(lambda x: th.fmt(x, "surface")),
        "2025": v.surface_2025.map(lambda x: th.fmt(x, "surface")),
        "Recul": v.delta_m2.map(lambda x: th.fmt(x, "surface")),
    })
    st.dataframe(affichage, width="stretch", hide_index=True, height=420)

    brest = vil[vil.ville == VILLE_ATYPIQUE]
    if not brest.empty:
        b = brest.iloc[0]
        st.warning(
            f"**{VILLE_ATYPIQUE} — valeur atypique, écartée de toute communication.** "
            f"Le recul affiché, {th.fmt(abs(b.delta_m2), 'surface')}, est un **artefact de "
            f"composition** : l'appartement médian y passe de 2 pièces et 52 m² en 2021 à "
            f"3 pièces et 60 m² en 2025. Le marché observé a changé de nature, pas seulement "
            f"de prix. Ce chiffre ne mesure pas une perte de pouvoir d'achat.",
            icon="⚠️")
    st.caption(
        "Communes de plus de 100 000 habitants, classées par surface finançable croissante. "
        "Ces valeurs reposent sur le **prix de l'appartement**, non sur le prix agrégé : "
        "dans les villes denses, l'appartement est le marché.")


# ---------- onglet 4 : parc social et cumul des exclusions ----------
def parc_social():
    th.bandeau(
        "Parc social et cumul des exclusions",
        "Le parc social devrait absorber ce que le marché privé rejette. Il est lui-même saturé. "
        "Là où les trois portes se ferment ensemble, il ne reste aucune solution.")

    com = dl.communes()
    ten = dl.tension()

    f1, f2, f3 = st.columns([2, 1, 1], gap="medium")
    deps = selecteur_departements(f1, "soc")
    annee = f2.select_slider("Année de la tension", options=list(range(2015, 2026)),
                             value=2025, key="annee_soc")
    profil = f3.radio("Profil de ménage", ["Ménage médian", "Ménage modeste (1er décile)"],
                      key="profil_soc")

    modeste = profil.startswith("Ménage modeste")
    col_triple = "triple_peine_d1" if modeste else "triple_peine_median"
    col_tension = f"tension_{annee}"

    com_f = appliquer_departements(com, deps)
    ten_f = appliquer_departements(ten, deps)
    seuil_tension = ten[col_tension].median()

    trois = com_f[com_f.n_legs_dispo == 3]
    if modeste:
        trois = trois[trois.triple_peine_d1.notna()]
        th.perimetre_modeste(int(com_f[com_f.n_legs_dispo == 3].triple_peine_d1.notna().sum()))
    n_triple = int(trois[col_triple].fillna(0).sum())

    # indicateurs
    st.subheader("Le parc social ne joue plus son rôle d'amortisseur")
    c = st.columns(5)
    with c[0]:
        th.kpi("Tension médiane", th.fmt(ten_f[col_tension].median(), "ratio"),
               f"demandes par attribution · {annee}")
    with c[1]:
        th.kpi("Ratio national", th.fmt(RATIO_SOCIAL_2025, "ratio"),
               f"contre {th.fmt(RATIO_SOCIAL_2016, 'ratio')} en 2016", critique=True)
    with c[2]:
        th.kpi("Communes en triple peine", th.fmt(n_triple, "entier"),
               f"sur {th.fmt(len(trois))} à trois indicateurs", critique=True)
    with c[3]:
        part = 100 * n_triple / len(trois) if len(trois) else np.nan
        th.kpi("Part des communes", th.fmt(part, "taux"),
               "parmi celles pleinement documentées")
    with c[4]:
        g = trois.groupby("dep")[col_triple].sum()
        epargnes = g[g == 0].index
        metro = int(sum(1 for d in epargnes if not str(d).startswith("97")))
        th.kpi("Départements épargnés", th.fmt(len(epargnes), "entier"),
               f"aucune commune en triple peine · dont {th.fmt(metro)} en métropole")

    # seuils et disponibilite
    gauche, droite = st.columns(2, gap="large")
    with gauche:
        st.subheader("Les trois seuils retenus")
        st.markdown(f"""
| Voie d'accès | Indicateur | Seuil de défaillance |
|---|---|---|
| Location privée | taux d'effort, logement familial | **supérieur à {SEUIL_EFFORT} %** |
| Accession | surface finançable | **inférieure à {SEUIL_SURFACE_CUMUL} m²** |
| Parc social | demandes par attribution | **supérieure à {th.fmt(seuil_tension, 'ratio')}** |
""")
        st.caption(
            "Chaque voie est déclarée défaillante ou non, et l'on compte les défaillances. "
            "Un score pondéré supposerait d'arbitrer entre trois grandeurs hétérogènes — "
            "un taux, une surface, un ratio — et toute pondération serait attaquable. "
            f"Le seuil du parc social est la médiane nationale des ratios départementaux de "
            f"{annee}.")
    with droite:
        st.subheader("Disponibilité des indicateurs")
        graphique_disponibilite(com_f)

    # geographie
    st.subheader("Part des communes en triple peine, par département")
    graphique_triple_peine(trois, col_triple, profil)

    # evolution et sensibilite
    bas_g, bas_d = st.columns(2, gap="large")
    with bas_g:
        st.subheader("Évolution de la tension, 2015-2025")
        graphique_tension_serie(ten_f, deps)
    with bas_d:
        st.subheader("Sensibilité aux seuils")
        graphique_sensibilite(com_f, ten)

    # export
    st.subheader("Détail communal")
    colonnes = ["insee_c", "libgeo", "dep", "effort_median_familial", "effort_d1_familial",
                "surface_financable", "tension_2025", "n_legs_dispo",
                "triple_peine_median", "triple_peine_d1"]
    detail = com_f[colonnes].copy()
    apercu = detail[detail.n_legs_dispo == 3].head(200).copy()
    for c_ in ("effort_median_familial", "effort_d1_familial"):
        apercu[c_] = apercu[c_].map(lambda v: th.fmt(v, "taux"))
    apercu["surface_financable"] = apercu.surface_financable.map(lambda v: th.fmt(v, "surface"))
    apercu["tension_2025"] = apercu.tension_2025.map(lambda v: th.fmt(v, "ratio"))
    st.dataframe(libelles(apercu), width="stretch", hide_index=True, height=280)
    st.caption(f"Aperçu des communes à trois indicateurs. L'export contient les "
               f"{th.fmt(len(detail))} communes du périmètre filtré, complétude comprise.")
    th.boutons_export(detail, "qce_cumul_exclusions", "Cumul des exclusions")
    st.caption(MENTION_EXPORT)

    th.source(
        "Sources : SNE 2015-2025 (demandes actives et attributions) × ANIL × DVF × Filosofi. "
        "Le ratio national est le rapport de la somme des demandes à la somme des attributions ; "
        "il diffère de la médiane des ratios départementaux, un ratio de ratios n'étant pas un "
        "ratio.")


def graphique_disponibilite(com_f):
    vc = com_f.n_legs_dispo.value_counts().reindex([3, 2, 1, 0]).fillna(0)
    libelles = ["Trois indicateurs", "Deux indicateurs", "Un seul indicateur", "Aucun indicateur"]
    couleurs = [th.BLEU, th.ECHELLE_BLEUE[3], th.ECHELLE_BLEUE[2], th.GRIS]
    total = len(com_f)
    fig = go.Figure(go.Bar(
        y=libelles, x=vc.values, orientation="h", marker_color=couleurs,
        text=[f"{th.fmt(v)}  ({th.fmt(100 * v / total, 'taux')})" for v in vc.values],
        textposition="outside", textfont=dict(color=th.BLEU_FONCE, size=11),
        hovertemplate="%{y}<br>%{x:,.0f} communes<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Communes", range=[0, vc.max() * 1.42]),
                      yaxis=dict(title="", autorange="reversed"))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 300, f"Sur {th.fmt(total)} communes documentées"),
        width="stretch")
    st.caption(
        "Le croisement n'est possible que sur les communes disposant des trois indicateurs. "
        "L'accession manque le plus souvent : elle exige au moins dix ventes dans l'année, "
        "un problème de petit échantillon plutôt que d'absence de marché.")


def graphique_triple_peine(trois, col_triple, profil):
    if trois.empty:
        st.warning("Aucune commune à trois indicateurs sur ce périmètre.")
        return
    noms = dl.noms_departements()
    g = (trois.groupby("dep")[col_triple].agg(["sum", "count"]).reset_index())
    g = g[g["count"] >= 3]
    g["part"] = 100 * g["sum"] / g["count"]
    g = g.sort_values("part", ascending=False)
    g["nom"] = g.dep.map(noms).fillna(g.dep)
    total = len(g)
    tout = st.checkbox(f"Afficher les {total} départements", key="tous_dep_peine")
    if not tout and total > 20:
        g = g.head(20)
        tronque = True
    else:
        tronque = False

    couleurs = [th.ROUGE if v > 0 else th.GRIS for v in g.part]
    fig = go.Figure(go.Bar(
        x=g.part, y=g.nom, orientation="h", marker_color=couleurs,
        customdata=np.stack([g.dep, g["sum"], g["count"]], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>%{x:.1f} %<br>"
                      "%{customdata[1]:.0f} communes sur %{customdata[2]:.0f}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Part des communes en triple peine (%)"),
                      yaxis=dict(title="", autorange="reversed", tickfont=dict(size=9)))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, max(400, 20 * len(g)),
                                   f"Cumul des trois défaillances · {profil.lower()}"),
        width="stretch")
    st.caption(
        "Départements documentés sur au moins 3 communes à trois indicateurs, classés par part "
        "décroissante. "
        + (f"Affichage des 20 premiers sur {total}." if tronque
           else f"{total} départements affichés.")
        + " Le phénomène est urbain et concentré, non diffus sur le territoire.")


def graphique_tension_serie(ten_f, deps):
    annees = list(range(2015, 2026))
    colonnes = [f"tension_{a}" for a in annees]
    med = [ten_f[c].median() for c in colonnes]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=annees, y=med, mode="lines+markers", name="Médiane départementale",
        line=dict(color=th.BLEU, width=3), marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>%{y:.2f} demandes par attribution<extra></extra>"))
    if deps:
        noms = dl.noms_departements()
        for d in deps[:5]:
            ligne = ten_f[ten_f.dep == d]
            if ligne.empty:
                continue
            fig.add_trace(go.Scatter(
                x=annees, y=[ligne[c].iloc[0] for c in colonnes], mode="lines",
                name=noms.get(d, d), line=dict(width=1.8, dash="dot"),
                hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="", dtick=1),
                      yaxis=dict(title="Demandes par attribution", rangemode="tozero"))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 360, "Tension du parc social, médiane départementale"),
        width="stretch")
    st.caption(
        f"Au niveau national, le rapport entre demandes actives et attributions passe de "
        f"{th.fmt(RATIO_SOCIAL_2016, 'ratio')} en 2016 à {th.fmt(RATIO_SOCIAL_2025, 'ratio')} "
        f"en 2025. La médiane départementale, plus basse, décrit le département type et non "
        f"le ménage type.")


def graphique_sensibilite(com_f, ten):
    seuil = ten.tension_2025.median()
    base = com_f[(com_f.n_legs_dispo == 3) & com_f.effort_d1_familial.notna()]
    valeurs = []
    for s in SEUILS_SENSIBILITE:
        n = int(((base.effort_d1_familial > SEUIL_EFFORT)
                 & (base.surface_financable < s)
                 & (base.tension_2025 > seuil)).sum())
        valeurs.append(n)
    couleurs = [th.ECHELLE_BLEUE[2], th.BLEU, th.ECHELLE_BLEUE[2]]
    fig = go.Figure(go.Bar(
        x=[f"< {s} m²" for s in SEUILS_SENSIBILITE], y=valeurs, marker_color=couleurs,
        text=[th.fmt(v) for v in valeurs], textposition="outside",
        textfont=dict(color=th.BLEU_FONCE),
        hovertemplate="Seuil %{x}<br>%{y} communes<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Seuil de surface finançable", type="category"),
                      yaxis=dict(title="Communes en triple peine",
                                 range=[0, max(valeurs) * 1.25]))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 360, "Effet du seuil de surface, ménage modeste"),
        width="stretch")
    st.caption(
        f"La surface est le seuil le plus sensible : de {th.fmt(valeurs[0])} à "
        f"{th.fmt(valeurs[-1])} communes selon qu'on retient 35 ou 45 m². C'est pourquoi le "
        f"rapport publie une fourchette de 160 à 430, jamais un chiffre unique. "
        f"Le seuil retenu est {SEUIL_SURFACE_CUMUL} m².")


# ---------- onglet 5 : qualite du parc ----------
def qualite_parc():
    th.bandeau(
        "Qualité du parc de logements",
        "Trois dimensions du mal-logement aux géographies distinctes — les deux dimensions "
        "énergétiques vont de pair, la suroccupation les contredit — et une quatrième, absente "
        "du diagnostic remis au consommateur : le confort d'été.")

    qua = dl.qualite()
    qnat = dl.qualite_national()
    con = dl.confort()
    com = dl.communes()

    f1, f2 = st.columns([2, 1], gap="medium")
    deps = selecteur_departements(f1, "qua")
    dimension = f2.radio(
        "Dimension cartographiée",
        ["Passoires énergétiques", "Coût de l'énergie", "Suroccupation"], key="dim_qua")

    qua_f = appliquer_departements(qua, deps)
    com_f = appliquer_departements(com, deps)
    dpe_f = com_f[com_f.n_dpe >= 20]

    # indicateurs
    st.subheader("Trois dimensions, trois géographies")
    q = qua_f.dropna(subset=["taux_passoires", "n_dpe"])
    c = st.columns(5)
    with c[0]:
        v = 100 * (q.taux_passoires / 100 * q.n_dpe).sum() / q.n_dpe.sum() if len(q) else np.nan
        th.kpi("Passoires énergétiques", th.fmt(v, "taux"), "logements classés F ou G",
               critique=True)
    with c[1]:
        th.kpi("Coût énergétique médian", th.fmt(dpe_f.cout_median.median(), "euro"),
               f"par logement et par an · {th.fmt(len(dpe_f))} communes")
    with c[2]:
        part = qua_f.part_cout_revenu.median()
        th.kpi("Part du revenu", th.fmt(part, "taux"),
               f"médiane · Q1 {th.fmt(qnat['part_revenu_q1'], 'taux')} · "
               f"Q3 {th.fmt(qnat['part_revenu_q3'], 'taux')}")
    with c[3]:
        s = qua_f.dropna(subset=["taux_suroccupation", "nb_rp"])
        v = (s.taux_suroccupation * s.nb_rp).sum() / s.nb_rp.sum() if len(s) else np.nan
        th.kpi("Suroccupation", th.fmt(v, "taux"), "des résidences principales")
    with c[4]:
        cn = con[con.dimension == "national"].iloc[0]
        th.kpi("Confort d'été insuffisant", th.fmt(cn.pct_insuffisant, "taux"),
               f"{th.fmt(cn.insuffisant)} logements diagnostiqués", critique=True)

    st.caption(
        "La dégradation énergétique est rurale et liée au bâti ancien ; la suroccupation est "
        "métropolitaine et ultramarine.")

    # les trois geographies, cote a cote
    st.subheader("Trois cartes, à lire ensemble")
    cartes_qualite()

    # exploration interactive, sensible au filtre departemental
    st.subheader(f"Explorer une dimension : {dimension.lower()}")
    st.caption(
        "Contrairement aux trois cartes ci-dessus, qui sont nationales et figées sur les "
        "figures du rapport, ce classement suit le filtre départemental en tête d'onglet.")
    graphique_qualite_departements(qua_f, dimension)

    # confort d'ete
    st.subheader("Le confort d'été, angle mort du diagnostic")
    st.caption(
        f"Extraction ADEME du {DATE_EXTRACTION_ADEME}. Ce chapitre repose sur une donnée figée : "
        "les colonnes de confort d'été ne figurent pas dans l'export local du répertoire DPE et "
        "ne peuvent pas être recalculées depuis les bases livrées.")
    g, d = st.columns(2, gap="large")
    with g:
        graphique_confort_repartition(con)
    with d:
        graphique_confort_etiquette(con)

    g2, d2 = st.columns(2, gap="large")
    with g2:
        graphique_confort_facteurs(con)
    with d2:
        graphique_confort_region(con)

    # export
    st.subheader("Détail départemental")
    tableau = tableau_qualite(qua_f, con)
    st.dataframe(tableau, width="stretch", hide_index=True, height=320)
    th.boutons_export(qua_f, "qce_qualite_parc", "Qualité du parc")
    st.caption(MENTION_EXPORT)

    st.info(
        "Deux éléments du rapport ne figurent pas ici, faute de source reproductible depuis les "
        "agrégats livrés : la ventilation des passoires par période de construction, qui exige "
        "une relecture du répertoire DPE complet, et le tableau des passoires par statut "
        "d'occupation, qui reprend des estimations du SDES — le diagnostic ne portant pas le "
        "statut d'occupation du logement.", icon="ℹ️")

    th.source(
        f"Sources : DPE ADEME (indicateurs communaux, export du 9 juin 2026 ; confort d'été, "
        f"extraction API du {DATE_EXTRACTION_ADEME}) · INSEE recensement 2022 pour la "
        "suroccupation, calculée comme une somme pondérée par les résidences principales et non "
        "comme une médiane communale.")


CARTES_QUALITE = [
    ("images/carte_passoires.png", "Passoires énergétiques",
     "Part de logements classés F ou G. Moyenne pondérée par le nombre de diagnostics."),
    ("images/carte_cout.png", "Coût de l'énergie",
     "Coût énergétique annuel médian par logement."),
    ("images/carte_suroccupation.png", "Suroccupation",
     "Part des résidences principales suroccupées, source INSEE."),
]


def cartes_qualite():
    """Les figures 11, 12 et 13 du rapport, cote a cote.

    Ce sont les PNG produits par 01_PIPELINE/40_figures/v3_bloc5_qualite.py, repris tels
    quels : passoires ponderees par n_dpe, suroccupation issue de la valeur departementale
    INSEE. Aucune valeur n'est recalculee ici. Elles sont nationales et ne suivent pas le
    filtre departemental — c'est voulu, la demonstration porte sur la France entiere.
    """
    colonnes = st.columns(3, gap="medium")
    for colonne, (chemin, titre, note) in zip(colonnes, CARTES_QUALITE):
        with colonne:
            st.markdown(f"**{titre}**")
            st.image(chemin, width="stretch")
            st.caption(note)

    st.markdown("")
    st.info(
        "**Ces trois géographies ne se recouvrent pas de la même façon.** Les deux dimensions "
        "énergétiques vont ensemble — la corrélation de rang entre part de passoires et coût "
        "de l'énergie atteint **+0,69**. La suroccupation, elle, les contredit : **−0,49** "
        "avec les passoires, **−0,59** avec le coût. Un département cher à chauffer et mal "
        "classé est donc, en règle générale, un département **peu** suroccupé.\n\n"
        "La Creuse en est l'illustration : **31,4 %** de passoires, le taux le plus élevé de "
        "France, pour **2,6 %** de suroccupation seulement. À l'inverse, Paris affiche "
        "**31,4 %** de suroccupation — deuxième rang derrière la Guyane, à 35,8 % — et l'un "
        "des coûts énergétiques les plus faibles de métropole, **1 021 €**, cinquième plus bas "
        "sur 96, quand le Cantal atteint **2 487 €**. Le parc parisien n'est pas pour autant "
        "performant : avec **17,9 %** de passoires, il se classe au 10ᵉ rang national, près du "
        "double de la moyenne française.\n\n"
        "C'est cette structure — deux dimensions solidaires, une troisième à rebours — qui a "
        "conduit à **écarter tout indice composite** : additionner ces trois grandeurs "
        "reviendrait à faire s'annuler des situations de mal-logement bien réelles.",
        icon="🗺️")
    st.caption(
        "Figures 11, 12 et 13 du rapport · corrélations de Spearman calculées sur les "
        "100 départements documentés. Minima nationaux : Martinique, 786 € et 2,0 % de "
        "passoires.")


def graphique_qualite_departements(qua_f, dimension):
    colonnes = {"Passoires énergétiques": ("taux_passoires", "taux", "Part F ou G (%)", True),
                "Coût de l'énergie": ("cout_median", "euro", "Coût annuel médian (€)", True),
                "Suroccupation": ("taux_suroccupation", "taux", "Taux de suroccupation (%)", True)}
    col, genre, axe, fort_est_mauvais = colonnes[dimension]
    d = qua_f.dropna(subset=[col]).copy()
    if d.empty:
        st.warning("Aucun département documenté sur cette dimension.")
        return
    noms = dl.noms_departements()
    d["nom"] = d.dep.map(noms).fillna(d.dep)
    d = d.sort_values(col, ascending=False)
    total = len(d)
    tout = st.checkbox(f"Afficher les {total} départements", key=f"tous_qua_{col}")
    d, tronque = extremes(d, tout)

    seuil = d[col].quantile(0.8)
    couleurs = [th.ROUGE if v >= seuil else th.BLEU for v in d[col]]
    fig = go.Figure(go.Bar(
        x=d[col], y=d.nom, orientation="h", marker_color=couleurs,
        customdata=np.stack([d.dep], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>%{x:.1f}<extra></extra>"))
    fig.update_layout(xaxis=dict(title=axe),
                      yaxis=dict(title="", autorange="reversed", tickfont=dict(size=9)))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, max(400, 18 * len(d)), f"{dimension}, par département"),
        width="stretch")
    st.caption(
        ("Affichage des 15 départements les plus touchés et des 15 les moins touchés, "
         f"sur {total}." if tronque else f"{total} départements affichés.")
        + " Le cinquième supérieur est signalé en rouge.")


def graphique_confort_repartition(con):
    cn = con[con.dimension == "national"].iloc[0]
    valeurs = [cn.bon, cn.moyen, cn.insuffisant]
    libelles = ["Bon", "Moyen", "Insuffisant"]
    couleurs = [th.ECHELLE_BLEUE[2], th.BLEU, th.ROUGE]
    fig = go.Figure(go.Bar(
        x=libelles, y=valeurs, marker_color=couleurs,
        text=[f"{th.fmt(100 * v / cn.renseigne, 'taux')}<br>{th.fmt(v)}" for v in valeurs],
        textposition="outside", textfont=dict(color=th.BLEU_FONCE, size=11),
        hovertemplate="%{x}<br>%{y:,.0f} logements<extra></extra>"))
    fig.update_layout(xaxis=dict(title="", type="category"),
                      yaxis=dict(title="Logements diagnostiqués",
                                 range=[0, max(valeurs) * 1.28]))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 340, "Répartition selon le confort d'été"),
        width="stretch")
    st.caption(
        f"Sur {th.fmt(cn.renseigne)} diagnostics renseignés, soit "
        f"{th.fmt(100 * cn.renseigne / cn.total_dpe, 'taux')} du répertoire.")


def graphique_confort_etiquette(con):
    d = con[con.dimension == "par_etiquette"].copy()
    d = d[d.cle.isin(ETIQUETTES_DPE)].set_index("cle").reindex(ETIQUETTES_DPE).reset_index()
    ab = con[con.dimension == "paradoxe_ab"].iloc[0]
    couleurs = [th.ROUGE if c in ("A", "B", "C") else th.BLEU for c in d.cle]
    fig = go.Figure(go.Bar(
        x=d.cle, y=d.pct_insuffisant, marker_color=couleurs,
        text=[th.fmt(v, "taux") for v in d.pct_insuffisant], textposition="outside",
        textfont=dict(color=th.BLEU_FONCE, size=11),
        hovertemplate="Étiquette %{x}<br>%{y:.1f} %% en confort insuffisant<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Étiquette énergétique", type="category"),
                      yaxis=dict(title="Confort d'été insuffisant (%)",
                                 range=[0, d.pct_insuffisant.max() * 1.25]))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 340, "Confort d'été selon l'étiquette énergétique"),
        width="stretch")
    st.caption(
        f"Le lien existe de A à G, mais il est **plat sur toute la moitié haute** : A, B et C "
        f"sont indiscernables, et le minimum se situe en **C**, non en A. Parmi les "
        f"{th.fmt(ab.renseigne)} logements étiquetés A ou B, "
        f"{th.fmt(100 * ab.insuffisant / ab.renseigne, 'taux')} surchauffent en été. "
        "L'étiquette est un indicateur d'hiver.")


def graphique_confort_facteurs(con):
    d = con[con.dimension == "sous_critere"].copy()
    d["critere"] = d.cle.str.split("|").str[0]
    d["etat"] = d.cle.str.split("|").str[1]
    piv = d.pivot(index="libelle", columns="etat", values="pct_insuffisant").reset_index()
    piv = piv.sort_values("bon", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=piv.libelle, x=piv["bon"], name="Logements au bon confort",
                         orientation="h", marker_color=th.BLEU,
                         hovertemplate="%{y}<br>présent chez %{x:.1f} %<extra></extra>"))
    fig.add_trace(go.Bar(y=piv.libelle, x=piv["insuffisant"], name="Logements inconfortables",
                         orientation="h", marker_color=th.ROUGE,
                         hovertemplate="%{y}<br>présent chez %{x:.1f} %<extra></extra>"))
    fig.update_layout(barmode="group", xaxis=dict(title="Présence du critère (%)"),
                      yaxis=dict(title="", tickfont=dict(size=10)))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 360, "Ce qui distingue un logement confortable"),
        width="stretch")
    ps = piv[piv.libelle.str.contains("Protection")].iloc[0]
    st.caption(
        f"La protection solaire extérieure est le facteur le plus discriminant : présente chez "
        f"{th.fmt(ps['bon'], 'taux')} des logements confortables, absente chez "
        f"{th.fmt(100 - ps['insuffisant'], 'taux')} des inconfortables. "
        "L'isolation de toiture va en sens inverse — c'est une mesure d'hiver.")


def graphique_confort_region(con):
    d = con[con.dimension == "par_region"].copy()
    d = d[d.renseigne >= 20000].sort_values("pct_insuffisant", ascending=False)
    couleurs = [th.ROUGE if v >= 45 else th.BLEU for v in d.pct_insuffisant]
    fig = go.Figure(go.Bar(
        x=d.pct_insuffisant, y=d.libelle, orientation="h", marker_color=couleurs,
        text=[th.fmt(v, "taux") for v in d.pct_insuffisant], textposition="outside",
        textfont=dict(color=th.BLEU_FONCE, size=10),
        hovertemplate="<b>%{y}</b><br>%{x:.1f} %<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Confort d'été insuffisant (%)",
                                 range=[0, d.pct_insuffisant.max() * 1.2]),
                      yaxis=dict(title="", autorange="reversed", tickfont=dict(size=10)))
    st.plotly_chart(
        th.mise_en_forme_graphique(fig, 360, "Confort d'été insuffisant, par région"),
        width="stretch")
    st.caption(
        "Contre-intuitif : le haut du classement est septentrional, le bas méditerranéen. "
        "L'indicateur mesure le bâti, pas le climat — le Sud a une architecture historiquement "
        "adaptée, le Nord a construit sans se protéger du soleil.")


def tableau_qualite(qua_f, con):
    noms = dl.noms_departements()
    conf = con[con.dimension == "par_departement"][["cle", "pct_insuffisant"]]
    conf = conf.rename(columns={"cle": "dep"})
    d = qua_f.merge(conf, on="dep", how="left")
    return pd.DataFrame({
        "Dép.": d.dep,
        "Département": d.dep.map(noms).fillna(""),
        "Passoires": d.taux_passoires.map(lambda v: th.fmt(v, "taux")),
        "Coût énergie": d.cout_median.map(lambda v: th.fmt(v, "euro")),
        "Part du revenu": d.part_cout_revenu.map(lambda v: th.fmt(v, "taux")),
        "Suroccupation": d.taux_suroccupation.map(lambda v: th.fmt(v, "taux")),
        "Confort d'été insuffisant": d.pct_insuffisant.map(lambda v: th.fmt(v, "taux")),
        "Diagnostics": d.n_dpe.map(lambda v: th.fmt(v, "entier")),
    }).sort_values("Dép.").reset_index(drop=True)


# ---------- navigation ----------
def main():
    st.sidebar.markdown("### Que Choisir Ensemble")
    st.sidebar.caption("Mission 26004 · diagnostic territorial de l'accès au logement")
    st.sidebar.markdown("---")

    if len(ONGLETS) == 1:
        vue_ensemble()
    else:
        for onglet, contenu in zip(st.tabs(ONGLETS),
                                   [vue_ensemble, parc_locatif, accession, parc_social,
                                    qualite_parc]):
            with onglet:
                contenu()

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Données au 22 août 2026. Confort d'été : extraction ADEME du 27 juillet 2026, figée. "
        "Voir METHODOLOGIE_DONNEES.md.")


if __name__ == "__main__":
    main()
