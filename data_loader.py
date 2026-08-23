"""
data_loader.py — Mission 26004 / Que Choisir Ensemble
Chargement des agregats de data_dashboard/. Chemins relatifs uniquement,
codes geographiques lus en texte.

Le cache est indexe sur une empreinte du fichier (taille et date de
modification) : sans elle, @st.cache_data conserve indefiniment la version
lue au premier demarrage, puisque la cle de cache ne depend que du code de la
fonction. Un fichier regenere ne serait jamais relu tant que le processus vit.
"""

import os

import pandas as pd
import streamlit as st

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_dashboard")

TYPES_GEO = {"insee_c": str, "dep": str, "reg": str, "cle": str}

FICHIERS = {
    "communes": "communes_acces.csv",
    "tension": "departements_tension.csv",
    "qualite": "departements_qualite.csv",
    "series": "series_temporelles.csv",
    "confort": "confort_ete.csv",
    "villes": "villes.csv",
    "decomposition": "decomposition_prix_taux.csv",
    "qualite_national": "qualite_national.csv",
}


# ---------- empreinte du fichier, pour invalider le cache a bon escient ----------
def _empreinte(nom):
    chemin = os.path.join(DOSSIER, nom)
    if not os.path.exists(chemin):
        st.error(f"Fichier absent : data_dashboard/{nom}. "
                 "Lancer `python pipeline/build_dashboard_data.py` avant de démarrer.")
        st.stop()
    infos = os.stat(chemin)
    return f"{infos.st_size}-{infos.st_mtime_ns}"


@st.cache_data(show_spinner=False)
def _charger(nom, empreinte):
    chemin = os.path.join(DOSSIER, nom)
    entetes = pd.read_csv(chemin, nrows=0).columns
    types = {c: t for c, t in TYPES_GEO.items() if c in entetes}
    return pd.read_csv(chemin, dtype=types, low_memory=False)


def _table(cle):
    nom = FICHIERS[cle]
    return _charger(nom, _empreinte(nom))


# ---------- acces aux tables ----------
def communes():
    return _table("communes")


def tension():
    return _table("tension")


def qualite():
    return _table("qualite")


def series():
    return _table("series")


def confort():
    return _table("confort")


def villes():
    return _table("villes")


def decomposition():
    return _table("decomposition")


def qualite_national():
    d = _table("qualite_national")
    return {str(c): float(v) for c, v in zip(d["cle"], d["valeur"])}


def noms_departements():
    t = tension()[["dep", "nom"]].dropna()
    return dict(zip(t.dep, t.nom))
