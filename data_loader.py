"""
data_loader.py — Mission 26004 / Que Choisir Ensemble
Chargement des agregats de data_dashboard/. Chemins relatifs uniquement,
codes geographiques lus en texte, cache Streamlit sur chaque lecture.
"""

import os

import pandas as pd
import streamlit as st

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_dashboard")

TYPES_GEO = {"insee_c": str, "dep": str, "reg": str, "cle": str}


def _lire(nom):
    chemin = os.path.join(DOSSIER, nom)
    if not os.path.exists(chemin):
        st.error(f"Fichier absent : data_dashboard/{nom}. "
                 "Lancer `python pipeline/build_dashboard_data.py` avant de démarrer.")
        st.stop()
    return pd.read_csv(chemin, dtype=TYPES_GEO, low_memory=False)


@st.cache_data(show_spinner=False)
def communes():
    return _lire("communes_acces.csv")


@st.cache_data(show_spinner=False)
def tension():
    return _lire("departements_tension.csv")


@st.cache_data(show_spinner=False)
def qualite():
    return _lire("departements_qualite.csv")


@st.cache_data(show_spinner=False)
def series():
    return _lire("series_temporelles.csv")


@st.cache_data(show_spinner=False)
def confort():
    return _lire("confort_ete.csv")


@st.cache_data(show_spinner=False)
def villes():
    return _lire("villes.csv")


@st.cache_data(show_spinner=False)
def decomposition():
    return _lire("decomposition_prix_taux.csv")


@st.cache_data(show_spinner=False)
def qualite_national():
    d = _lire("qualite_national.csv").set_index("cle")
    return d


@st.cache_data(show_spinner=False)
def noms_departements():
    t = tension()[["dep", "nom"]].dropna()
    return dict(zip(t.dep, t.nom))
