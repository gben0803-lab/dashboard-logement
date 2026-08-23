# Déploiement du dashboard — Mission 26004 / Que Choisir Ensemble

Cible : **Streamlit Community Cloud**. Usage interne QCE.

---

## 1. Fichiers à pousser sur le dépôt

Le dossier de mission pèse ~13 Go ; **ne pas le pousser tel quel**. Créer un dépôt ne
contenant que ces éléments :

```
app.py                        application, onglets
theme.py                      charte QCE et formatage — seul module qui definit des couleurs
data_loader.py                chargement cache des agregats
requirements.txt              versions epinglees
runtime.txt                   version de Python
.streamlit/config.toml        bloc [theme]
data_dashboard/               5 CSV, 4,58 Mo au total
pipeline/build_dashboard_data.py   producteur des agregats (pour la mise a jour)
METHODOLOGIE_DONNEES.md       lineage et pieges de calcul
```

Total ≈ 4,7 Mo — très en dessous des limites GitHub.

**Ne pas pousser** `.claude/launch.json` : il contient un chemin absolu vers un
environnement virtuel local, utile seulement en développement.

## 2. Réglages Streamlit Cloud

| Champ | Valeur |
|---|---|
| Main file path | `app.py` |
| Branch | `main` |
| **Python version** | **3.13** |

## 3. Le piège de la version de Python — à connaître avant lundi

**Streamlit ne s'installe pas sur Python 3.14**, qui est la version par défaut de la machine
de développement. Toute la chaîne a été validée sur **Python 3.13.0**.

`runtime.txt` déclare `python-3.13`. Streamlit Cloud lit ce fichier, mais **la version se
choisit aussi dans l'écran de déploiement** (Advanced settings). Si les deux divergent,
c'est l'écran qui l'emporte. Vérifier les deux.

Symptôme si la version est trop récente : l'installation échoue sur les roues binaires de
`pyarrow` ou de `numpy`, avec un message de compilation qui ne mentionne pas Python.

## 4. Versions épinglées

```
streamlit==1.62.0
pandas==3.0.5
numpy==2.5.2
plotly==6.9.0
pyarrow==25.0.1
```

`pyarrow` est une dépendance de `streamlit`, épinglée explicitement : c'est elle qui casse en
premier sur une version de Python non supportée.

## 5. Vérification en environnement propre — déjà effectuée

```
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Contrôles passés :

| Contrôle | Résultat |
|---|---|
| Installation depuis `requirements.txt` seul | 5 paquets, aucun conflit |
| Démarrage de l'application | aucune exception |
| Rendu des 5 sections | titres et composants présents |
| Graphiques Plotly | 2 tracés, 0 texte invalide dans le DOM |
| Formatage des valeurs | 17 cas conformes au rapport |
| Filtres (département, année, profil) | testés, cohérents |
| Chemins absolus dans le code déployé | **aucun** |
| Couleurs hors `theme.py` | **aucune** |

## 6. Deux corrections rencontrées au premier démarrage

Consignées ici : ce sont exactement les défauts triviaux qu'un premier déploiement révèle.

**`use_container_width` est déprécié depuis le 31 décembre 2025.** Streamlit 1.62 l'accepte
encore mais journalise un avertissement à chaque appel. Remplacé par `width="stretch"` dans
`app.py` et `theme.py`. À surveiller lors d'une montée de version : le paramètre finira par
être retiré.

**`title_font` sans `title` fait afficher « undefined ».** Plotly crée alors un élément de
titre au texte non défini, rendu littéralement dans le graphique. Corrigé dans
`theme.mise_en_forme_graphique()`, qui prend désormais un paramètre `titre` explicite et
définit toujours `title=dict(text=titre)`.

## 7. Mise à jour des données

```
python pipeline/build_dashboard_data.py
```

Le script relit les sorties de `FINDINGS/`, **exécute 23 contrôles de conformité au rapport**
et **n'écrit rien si l'un d'eux échoue**. Il ne lit aucune base brute et n'émet aucun appel
réseau. Committer ensuite `data_dashboard/`.

Le confort d'été fait exception : il dérive d'une extraction API figée au 27 juillet 2026,
non reconstructible depuis les bases livrées. Voir `METHODOLOGIE_DONNEES.md` §4.

## 8. Démarrage local

```
streamlit run app.py
```

Le port par défaut est 8501. En développement, `.claude/launch.json` lance l'application sur
le port 8511 avec l'environnement virtuel de test.
