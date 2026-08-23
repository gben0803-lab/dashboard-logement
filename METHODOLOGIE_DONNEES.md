# Méthodologie des données du dashboard — Mission 26004 / Que Choisir Ensemble

Ce document décrit la construction de `data_dashboard/`, les pièges de calcul rencontrés et
les règles à respecter pour toute reproduction ou mise à jour.

Producteur unique : `pipeline/build_dashboard_data.py`. Il **ne lit aucune base brute** —
ni `DVF_clean.csv`, ni `DPE_clean.csv`, ni `RPLS_clean.csv` — et part exclusivement des sorties
auditées de `FINDINGS/`, dont la reproductibilité a été établie (27 CSV et 39 figures reproduits
à l'identique, cf. `AUDIT_REPRODUCTIBILITE.md`).

---

## 1. Le piège de la suroccupation départementale

**Règle : la suroccupation départementale est une somme pondérée par les résidences
principales. Ce n'est PAS la médiane des taux communaux.**

C'est le point le plus facile à rater de tout le jeu de données, et l'erreur a déjà été commise
une fois sur cette mission (consignée au HANDOVER §8 n° 6).

### Ce que donne chaque méthode

| Département | Médiane des communes | **Somme pondérée par les RP** | Publié au rapport |
|---|---|---|---|
| Guyane (973) | 39,2 % | **35,8 %** | 35,8 % |
| Paris (75) | 32,2 % | **31,4 %** | 31,4 % |
| National | 1,7 % | **9,6 %** | 9,6 % |

L'écart national est d'un facteur **5,6**. La médiane communale décrit la commune type ; le taux
officiel décrit le ménage type. Les deux répondent à des questions différentes, et c'est le
second que publient l'INSEE et le rapport.

### Conséquence pratique

`qualite_communes.csv` porte bien une colonne `taux_suroccupation`, mais **elle est communale**
et le fichier **ne contient pas le nombre de résidences principales** : la pondération correcte
y est donc impossible.

`departements_qualite.csv` prend en conséquence :

| Colonne | Source | Méthode |
|---|---|---|
| `taux_passoires` | `qualite_communes.csv` | moyenne pondérée par `n_dpe`, communes à `n_dpe >= 20` |
| `cout_median` | `qualite_communes.csv` | médiane des communes à `n_dpe >= 20` |
| **`taux_suroccupation`** | **`INSEE_logement_2022_dept.csv`** | **valeur départementale directe (somme pondérée par les RP)** |
| `part_hlm`, `part_loc_prive`, `taux_vacance`, `nb_rp` | `INSEE_logement_2022_dept.csv` | idem |

C'est exactement la source qu'utilise `scripts/v3_bloc5_qualite.py` pour les figures n° 11 à 13
du rapport. Le dashboard et le rapport sont donc alignés par construction.

### Formule de référence, si le fichier doit être régénéré

Depuis `base-ic-logement-2022.CSV` (recensement 2022, niveau IRIS, `latin-1`, séparateur `;`),
agrégé par département — deux premiers caractères de `COM`, **trois** pour les codes `97` :

```
taux_suroccupation = (Σ C22_RP_SUROCC_MOD + Σ C22_RP_SUROCC_ACC) / Σ P22_RP × 100
```

Deux points tranchés sur données lors de l'audit :
- le dénominateur est **`P22_RP`**, pas `C22_RP_NORME` — ce dernier donnerait 40,9 % au national ;
- le taux agrège **la suroccupation modérée et la suroccupation accentuée**.

Reconstruction vérifiée sur les 100 départements et 13 colonnes dérivées : **écart nul**.
Script : `FINDINGS/REPLICATION/scripts/build_insee_logement_dept.py`.

> `INSEE_logement_2022_dept.csv` était une **orpheline d'entrée** : aucun script du dossier ne la
> produisait, alors que trois scripts la lisaient. Elle a été reconstruite pendant l'audit.

---

## 2. La même règle ailleurs : ratio de ratios

Le piège de la suroccupation est un cas particulier d'une règle générale — **la moyenne ou la
médiane d'un ratio n'est pas le ratio des totaux**. Elle se retrouve à trois autres endroits.

| Indicateur | Méthode correcte | Ce qu'il ne faut pas faire |
|---|---|---|
| **Part de passoires départementale** | moyenne pondérée par `n_dpe` | médiane des taux communaux |
| **Tension du parc social, niveau national** | Σ demandes / Σ attributions = **4,06** (2016) → **7,34** (2025) | médiane départementale (2,80 → 5,17) |
| **Taux d'effort départemental** | les deux sont publiés — `effort_median_*` (médiane communale) **et** `effort_pondere_*` (pondéré par les ménages) | confondre les deux |

Sur le taux d'effort, l'écart entre les deux conventions atteint **+16,8 points** dans les
Alpes-Maritimes (31,4 % en médiane communale contre 48,3 % en pondéré). C'est l'objet du
tableau n° 9 du rapport. `departements_tension.csv` porte les deux colonnes, délibérément.

**Le coût énergétique fait exception** : il est publié comme **médiane des communes**
(1 769 €), pas comme moyenne pondérée. C'est la convention du rapport, conservée telle quelle.

---

## 3. Ratio du parc social — valeurs alignées après audit

Le dashboard utilise **4,06 (2016) → 7,34 (2025)**, soit une progression de 81 %.

Le rapport publie encore 3,8 → 7,0 (+82 %), valeurs qu'aucune agrégation des bases livrées ne
reproduit — cinq périmètres testés. L'arbitrage a été rendu le 22 août 2026 : **alignement sur
le code**. La correction du rapport est en cours (`CORRECTIONS_RAPPORT.md`, entrée A3).

---

## 4. Confort d'été — donnée figée, non reconstructible

`confort_ete.csv` dérive de `confort_ete_aggregats.json`, **extraction de l'API ADEME du
27 juillet 2026**. Ce fichier est en lecture seule (`chmod 444`) et sauvegardé sous
`confort_ete_aggregats.FIGE_2026-07-27.json`.

**Il ne peut pas être régénéré depuis les bases livrées** : l'export local `dpe03existant.csv`
ne contient ni `indicateur_confort_ete`, ni aucun des cinq sous-critères. Le pipeline du
dashboard n'émet **aucun appel réseau**.

Pour une mise à jour annuelle, QCE devra re-télécharger le jeu ADEME **en incluant ces six
colonnes**, puis rejouer `scripts/confort_ete_agg.py`. Les effectifs changeront : la base ADEME
est alimentée en continu.

---

## 5. Double périmètre du DPE

Deux extractions coexistent dans le projet. Ne pas les mélanger.

| Périmètre | Date | Effectif | Usage |
|---|---|---|---|
| National (API) | 27/07/2026 | 15 280 141 | effectifs nationaux, **tout le confort d'été** |
| Communal (`DPE_clean.csv`) | 09/06/2026 | 14 108 204 | **tous les indicateurs communaux et départementaux** |

Écart de 2,4 %, imputable à l'alimentation continue de la base. Les deux sont justes ; ils ne
sont simplement pas rapprochables entre eux.

---

## 6. Codes géographiques

**Règle absolue : les codes INSEE sont du texte, jamais des nombres.**

- 5 caractères, **zéros initiaux conservés** — 3 135 codes commencent par `0` ;
- Corse en **`2A` / `2B`**, jamais `20` — 360 communes ;
- DOM sur **3 caractères** au niveau département (`971` à `976`) — 113 communes.

En Python : `dtype={"insee_c": str, "dep": str}` à chaque lecture, sans exception. En PHP et en
tableur, forcer le type texte à l'import. Un code passé en entier perd son zéro initial et
casse silencieusement la jointure.

---

## 7. Fichiers produits

| Fichier | Lignes × col. | Sources |
|---|---|---|
| `communes_acces.csv` | 34 923 × 28 | `taux_effort_anil_all.csv`, `pouvoir_achat_immo.csv`, `double_peine_communes.csv` |
| `departements_tension.csv` | 101 × 21 | `SNE_tension_ratio.csv`, `dept_effort_weighted_t12/t3p.csv` |
| `departements_qualite.csv` | 100 × 10 | `qualite_communes.csv`, `INSEE_logement_2022_dept.csv` |
| `series_temporelles.csv` | 200 × 9 | `serie_surface_national.csv`, `serie_surface_villes.csv` |
| `confort_ete.csv` | 190 × 10 | `confort_ete_aggregats.json` *(figé)* |

Total **4,58 Mo**. UTF-8, séparateur virgule, en-têtes en minuscules sans accent.

---

## 8. Contrôles automatiques

`build_dashboard_data.py` exécute **23 contrôles** avant tout export et **n'écrit rien** si l'un
d'eux échoue (`exit 1`). Ils vérifient que les agrégats restituent les valeurs publiées : taux
d'effort 14,8 / 20,8 / 29,5 / 42,7 %, communes au-delà de 33 % (2,6 % et 86,6 %), surface
finançable 88,8 m², série 2021-2025, triple peine 238 sur 13 690, passoires 9,8 %, suroccupation
9,6 %, coût 1 769 €, tension 5,17.

**Toute modification du pipeline doit laisser ces 23 contrôles au vert.** C'est le garde-fou
qui garantit que le dashboard ne diverge pas du rapport.

---

## 9. Écarts d'arrondi entre calcul et affichage

Les valeurs calculées portent plus de décimales que les valeurs publiées : 14,79 contre 14,8 ;
9,779 contre 9,8 ; 9,629 contre 9,6. **Le dashboard applique les arrondis d'affichage du
rapport** — une décimale sur les taux, zéro sur les effectifs et les euros — via une fonction de
formatage unique, `theme.fmt()`. Aucun arrondi n'est appliqué aux données stockées.
