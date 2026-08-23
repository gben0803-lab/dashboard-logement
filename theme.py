"""
theme.py — Mission 26004 / Que Choisir Ensemble
Charte graphique, formatage des valeurs et composants d'affichage du dashboard.
Seul module autorise a definir des couleurs : aucun hexadecimal ailleurs.
"""

import streamlit as st

# ---------- charte QCE ----------
BLEU = "#004F9F"
BLEU_FONCE = "#00274F"
BLEU_INTER = "#003A77"
ROUGE = "#E30613"
JAUNE = "#FFF03C"
VERT = "#3FA535"
GRIS = "#E8E8E8"
BLANC = "#FFFFFF"
GRIS_TEXTE = "#5A6672"
JAUNE_FOND = "#FFFBE0"
TRANSPARENT = "rgba(0,0,0,0)"

ECHELLE_BLEUE = ["#E8EFF7", "#C2D6EB", "#8FB4DA", "#5A8FC7", "#2E6EB0", "#004F9F", "#00274F"]
ECHELLE_BLEUE_INV = list(reversed(ECHELLE_BLEUE))
SEQUENCE_CATEGORIES = [BLEU, BLEU_INTER, BLEU_FONCE, VERT, JAUNE, ROUGE]

CATEGORIES_EFFORT = {
    "Accessible": ECHELLE_BLEUE[1],
    "Modéré": ECHELLE_BLEUE[3],
    "Effort important": BLEU,
    "Insoutenable": ROUGE,
}

POLICE = "Source Sans Pro, Segoe UI, Helvetica, Arial, sans-serif"


# ---------- formatage : point d'entree unique ----------
def fmt(valeur, genre="entier", unite=True):
    """Applique les arrondis d'affichage du rapport. genre : taux, euro, entier,
    surface, ratio, ratio1, decimal2."""
    if valeur is None:
        return "n.d."
    try:
        x = float(valeur)
    except (TypeError, ValueError):
        return "n.d."
    if x != x:
        return "n.d."

    if genre == "taux":
        s = f"{x:.1f}".replace(".", ",")
        return f"{s} %" if unite else s
    if genre == "surface":
        s = f"{x:.1f}".replace(".", ",")
        return f"{s} m²" if unite else s
    if genre == "ratio":
        s = f"{x:.2f}".replace(".", ",")
        return s
    if genre == "ratio1":
        s = f"{x:.1f}".replace(".", ",")
        return s
    if genre == "decimal2":
        return f"{x:,.2f}".replace(",", " ").replace(".", ",")
    if genre == "euro":
        s = f"{x:,.0f}".replace(",", " ")
        return f"{s} €" if unite else s
    s = f"{x:,.0f}".replace(",", " ")
    return s


def fmt_delta(valeur, genre="taux"):
    if valeur is None or valeur != valeur:
        return None
    signe = "+" if valeur > 0 else ""
    return f"{signe}{fmt(valeur, genre)}"


# ---------- mise en page ----------
def configurer_page(titre):
    st.set_page_config(page_title=f"{titre} — QCE", page_icon="🏠",
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown(f"""
        <style>
        .stApp {{ background: {BLANC}; }}
        h1, h2, h3 {{ color: {BLEU_FONCE}; font-family: {POLICE}; }}
        [data-testid="stSidebar"] {{ background: {GRIS}; }}
        [data-testid="stSidebar"] * {{ color: {BLEU_FONCE}; }}
        .bandeau {{ background: {BLEU}; color: {BLANC}; padding: 1.1rem 1.4rem;
                    border-radius: 6px; margin-bottom: 1.1rem; }}
        .bandeau h1 {{ color: {BLANC}; margin: 0; font-size: 1.55rem; }}
        .bandeau p {{ color: {BLANC}; margin: .35rem 0 0; opacity: .92; font-size: .95rem; }}
        .kpi {{ background: {BLANC}; border: 1px solid {GRIS}; border-left: 5px solid {BLEU};
                border-radius: 5px; padding: .85rem 1rem; height: 100%; }}
        .kpi.critique {{ border-left-color: {ROUGE}; }}
        .kpi .libelle {{ color: {GRIS_TEXTE}; font-size: .78rem; text-transform: uppercase;
                         letter-spacing: .04em; }}
        .kpi .valeur {{ color: {BLEU_FONCE}; font-size: 1.85rem; font-weight: 700;
                        line-height: 1.15; margin: .18rem 0; }}
        .kpi.critique .valeur {{ color: {ROUGE}; }}
        .kpi .note {{ color: {GRIS_TEXTE}; font-size: .78rem; }}
        .perimetre {{ background: {JAUNE_FOND}; border-left: 4px solid {JAUNE};
                      padding: .6rem .9rem; border-radius: 4px; font-size: .87rem;
                      color: {BLEU_FONCE}; margin: .5rem 0 .9rem; }}
        .source {{ color: {GRIS_TEXTE}; font-size: .78rem; border-top: 1px solid {GRIS};
                   padding-top: .5rem; margin-top: .8rem; }}
        </style>
    """, unsafe_allow_html=True)


def bandeau(titre, sous_titre):
    st.markdown(f'<div class="bandeau"><h1>{titre}</h1><p>{sous_titre}</p></div>',
                unsafe_allow_html=True)


def kpi(libelle, valeur, note="", critique=False):
    classe = "kpi critique" if critique else "kpi"
    st.markdown(
        f'<div class="{classe}"><div class="libelle">{libelle}</div>'
        f'<div class="valeur">{valeur}</div><div class="note">{note}</div></div>',
        unsafe_allow_html=True)


def perimetre_modeste(n_communes=5163, inline=False):
    """Rappel obligatoire : le menage modeste ne porte pas sur le territoire entier."""
    texte = (f"Le ménage modeste (1<sup>er</sup> décile) porte sur "
             f"<b>{fmt(n_communes)} communes</b> — celles pour lesquelles l'INSEE publie le "
             f"premier décile de revenu — et non sur l'ensemble du territoire.")
    if inline:
        return texte
    st.markdown(
        f'<div class="perimetre">⚠️ {texte}</div>', unsafe_allow_html=True)


def source(texte):
    st.markdown(f'<div class="source">{texte}</div>', unsafe_allow_html=True)


def mise_en_forme_graphique(fig, hauteur=420, titre=""):
    fig.update_layout(
        height=hauteur,
        font=dict(family=POLICE, color=BLEU_FONCE, size=13),
        paper_bgcolor=BLANC, plot_bgcolor=BLANC,
        margin=dict(l=10, r=10, t=40 if titre else 20, b=10),
        title=dict(text=titre, font=dict(color=BLEU_FONCE, size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=BLANC, bordercolor=BLEU, font_color=BLEU_FONCE),
    )
    fig.update_xaxes(gridcolor=GRIS, zerolinecolor=GRIS, linecolor=GRIS)
    fig.update_yaxes(gridcolor=GRIS, zerolinecolor=GRIS, linecolor=GRIS)
    return fig


def bouton_csv(df, nom_fichier, libelle="Télécharger le tableau filtré (CSV)"):
    st.download_button(
        label=libelle,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=nom_fichier,
        mime="text/csv",
        width="stretch",
    )
