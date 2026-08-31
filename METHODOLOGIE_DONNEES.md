# Méthodologie des données du dashboard — Mission 26004 / Que Choisir Ensemble

Ce document décrit la construction de `data_dashboard/`, la généalogie de chacun des huit
fichiers livrés, les pièges de calcul rencontrés et les règles à respecter pour toute
reproduction ou mise à jour.

Producteur unique : `pipeline/build_dashboard_data.py`. Il **ne lit aucune base brute** —
ni `DVF_clean.csv`, ni `DPE_clean.csv`, ni `RPLS_clean.csv` — et part exclusivement des sorties
auditées du pipeline de mission, dont la reproductibilité a été établie (27 CSV et 39 figures
reproduits à l'identique — audit de reproductibilité clos le 22 août 2026, dont le rapport
complet est conservé côté TSE Junior Études).

Mis à jour le 30 août 2026.

---

## 0. La chaîne, de bout en bout

```
00_SOURCES/           bases brutes : ADEME, DVF, RPLS, SNE, ANIL, INSEE, Filosofi
      │                cf. 00_SOURCES/SOURCES.md
      ▼
01_PIPELINE/10_nettoyage/     bruts → *_clean.csv
01_PIPELINE/20_socle/         taux_effort_anil.R → socle de 34 923 communes
01_PIPELINE/30_indicateurs/   effort locatif, surface finançable, triple peine, qualité
01_PIPELINE/40_figures/       les 18 figures du rapport
      ▼
02_DONNEES_INTERMEDIAIRES/    27 CSV + 34 PNG — le témoin des 61 empreintes
      ▼
pipeline/build_dashboard_data.py    (dépôt dashboard-logement)
      ▼
data_dashboard/       8 CSV, 6,97 Mo — ce que lit l'application
```

**Deux entrées échappent à cette chaîne** et doivent être connues :

- `02_DONNEES_INTERMEDIAIRES/confort_ete_aggregats.json` — extraction API figée, non
  reconstructible depuis `00_SOURCES/` (§4) ;
- `02_DONNEES_INTERMEDIAIRES/INSEE_logement_2022_dept.csv` — reconstruit pendant l'audit, il
  était une orpheline d'entrée (§1).

> **Corrigé le 24 août 2026.** `build_dashboard_data.py` résolvait encore ses entrées sous
> `FINDINGS/Phase2/` et `Base de données/`, chemins disparus à la réorganisation ; le script
> s'arrêtait sur `Sources introuvables`. Il pointe désormais sur `02_DONNEES_INTERMEDIAIRES/`
> et `00_SOURCES/`. **Vérification faite** : après correction, les huit CSV régénérés sont
> identiques au md5 à ceux qui étaient livrés, et les 47 contrôles passent.

---

## 1. Le piège de la suroccupation départementale

**Règle : la suroccupation départementale est une somme pondérée par les résidences
principales. Ce n'est PAS la médiane des taux communaux.**

C'est le point le plus facile à rater de tout le jeu de données, et l'erreur a déjà été commise
une fois sur cette mission.

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

C'est exactement la source qu'utilise `01_PIPELINE/40_figures/v3_bloc5_qualite.py` pour les
figures n° 11 à 13 du rapport. Le dashboard et le rapport sont donc alignés par construction.

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
Script : `01_PIPELINE/10_nettoyage/build_insee_logement_dept.py`.

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

Le dashboard **et le rapport** publient désormais **4,06 (2016) → 7,34 (2025)**, soit une
progression de 81 %.

Les versions antérieures du rapport portaient 3,8 → 7,0 (+82 %), valeurs qu'aucune agrégation
des bases livrées ne reproduit — cinq périmètres testés. L'arbitrage a été rendu le 22 août
2026 : **alignement sur le code**. La correction est portée au rapport depuis le 24 août, avec
une note de méthode en page 5 qui explique l'écart avec la médiane départementale (5,17 en
2025), un ratio de ratios ne constituant pas un ratio.

**Publier deux décimales rend la progression vérifiable** : 7,34 / 4,06 = +80,8 %, soit 81 %
après arrondi. Les valeurs arrondies à une décimale ne le permettaient pas — 7,3 / 4,1 donne
+78 %, trois points d'écart avec le pourcentage publié.

---

## 4. Confort d'été — donnée figée, non reconstructible

`confort_ete.csv` dérive de `confort_ete_aggregats.json`, **extraction de l'API ADEME du
27 juillet 2026**. Ce fichier est en lecture seule (`chmod 444`) et sauvegardé sous
`confort_ete_aggregats.FIGE_2026-07-27.json`.

**Il ne peut pas être régénéré depuis les bases livrées** : l'export local `dpe03existant.csv`
ne contient ni `indicateur_confort_ete`, ni aucun des cinq sous-critères. Le pipeline du
dashboard n'émet **aucun appel réseau**.

Pour une mise à jour annuelle, QCE devra re-télécharger le jeu ADEME **en incluant ces six
colonnes**, puis rejouer `01_PIPELINE/00_acquisition/confort_ete_agg.py`. Les effectifs
changeront : la base ADEME est alimentée en continu.

### 4.0 Les figures du chapitre sont reproductibles — leur mise en page ne l'est pas

Les figures 14 à 18 du rapport sont bien produites par `01_PIPELINE/40_figures/confort_ete_charts.py`,
aux mêmes valeurs. Ce qui est **inséré** dans le document a subi une mise en page manuelle :
redimensionnement, le PDF n'étant pas net à la taille d'origine, et un pied de source complété
de la date d'extraction — « …(dpe03existant), extraction du 27 juillet 2026 — TSE Junior
Études » — que le script ne produit pas.

Régénérer les figures redonne donc les mêmes graphiques, **au format d'origine et sans la date
dans le pied**. Le geste de mise en page est à refaire à l'insertion. Les sept recadrages de
`03_FIGURES/recadrages_inseres_dans_le_rapport/` relèvent du même travail.

**Aucune valeur n'est concernée.**

### 4.1 Dérive mesurée de la base ADEME — et pourquoi elle ne biaise pas les résultats

Le 23 août 2026, l'API a été interrogée à nouveau, à titre de contrôle. Voici l'écart avec
l'extraction publiée du 27 juillet.

| Grandeur | 27 juillet 2026 *(publié)* | 23 août 2026 | Écart |
|---|---|---|---|
| Diagnostics au total | 15 280 141 | **15 409 991** | **+0,85 %** |
| Dont indicateur de confort d'été renseigné | 10 374 236 | **10 478 537** | +1,01 % |
| Taux de renseignement | 67,9 % | 68,0 % | +0,1 pt |
| Part en confort **bon** | 17,3 % | **17,3 %** | inchangée |
| Part en confort **moyen** | 42,8 % | **42,7 %** | −0,1 pt |
| Part en confort **insuffisant** | 40,0 % | **40,0 %** | inchangée |

**C'est le contrôle qui compte : en un mois, la base gagne 129 850 diagnostics et les parts
publiées ne bougent pas.** L'instantané figé du 27 juillet n'introduit donc aucun biais de
composition — il décrit la même population, simplement moins nombreuse.

Deux conséquences pour QCE :

1. **Les pourcentages du rapport restent valables** au-delà de leur date d'extraction. Ce sont
   les **effectifs absolus** qui vieillissent — 1 793 312 logements en bon confort, par
   exemple, sera sous-estimé dès la mise à jour suivante.
2. **Lors d'une actualisation, ne comparez jamais un effectif de 2026 à un effectif publié
   ici.** Comparez des parts, ou re-publiez les deux effectifs avec leur date d'extraction.

Le contrôle est reproductible : relancer `confort_ete_agg.py` sur un dossier de sortie vierge
donne les chiffres du jour. Le script **refuse désormais d'écraser** les sorties existantes,
précisément pour que cette vérification ne détruise pas l'instantané publié.

---

## 5. Double périmètre du DPE

Deux extractions coexistent dans le projet. Ne pas les mélanger.

| Périmètre | Date | Effectif | Usage |
|---|---|---|---|
| National (API) | 27/07/2026 | 15 280 141 | effectifs nationaux, **tout le confort d'été** |
| Communal (`DPE_clean.csv`) | 09/06/2026 | 14 108 204 | **tous les indicateurs communaux et départementaux** |

L'écart de 7,7 % entre les deux mesures a deux origines. Sept semaines de dépôts
supplémentaires expliquent 2,4 % ; le solde tient au nettoyage, les diagnostics ne pouvant
être rattachés à une commune étant écartés du calcul communal. Les deux mesures sont justes ;
elles ne sont simplement pas rapprochables entre elles.

**Un troisième effectif circule** et n'est ni l'un ni l'autre : `qualite_national.csv` publie
`n_dpe = 13 995 644`, libellé « Diagnostics rattachés à une commune ». C'est le sous-ensemble
du périmètre communal effectivement apparié à une commune du socle, après agrégation
départementale. L'écart avec 14 108 204 (−0,8 %) correspond aux diagnostics dont le code
commune ne se rattache à aucune commune retenue.

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

## 7. Généalogie des huit fichiers livrés

Pour chaque fichier : d'où il vient, ce qu'on lui fait, dans quel ordre, avec quels seuils, ce
que contient chaque colonne, et ce qu'il ne faut pas lui demander.

Convention commune à tous : **UTF-8, séparateur virgule, en-têtes en minuscules sans accent**
(fonction `sans_accent`), pas de guillemets sauf nécessité, décimales au format `%.12g`.

### 7.1 `communes_acces.csv` — 34 923 lignes × 32 colonnes, 7,08 Mo

Le fichier central : une ligne par commune du socle ANIL/Filosofi.

**Entrées** — quatre CSV de `02_DONNEES_INTERMEDIAIRES/` :
`taux_effort_anil_all.csv`, `pouvoir_achat_immo.csv`, `double_peine_communes.csv`,
`qualite_communes.csv`.

**Traitements, dans l'ordre :**

1. `taux_effort_anil_all.csv` est **scindé par segment** : `T1-T2` donne le bloc « petit
   logement », `T3+` le bloc « familial ». Les colonnes sont renommées avec le suffixe
   correspondant.
2. Jointure `outer` des deux blocs sur `insee_c`, puis `outer` avec le bloc achat, puis
   `outer` avec le bloc triple peine, enfin **`left`** avec le bloc qualité.
3. Les quatre colonnes `echec_*` sont normalisées en booléen — elles arrivent en `True`/`False`
   textuels selon la source.
4. `triple_peine_median` et `triple_peine_d1` sont calculées **uniquement là où les trois
   indicateurs existent** (`n_legs_dispo == 3`), sinon `NaN`. Voir le seuil ci-dessous.
5. `insee_c` est reformaté sur 5 caractères (`zfill`), tri final par `insee_c`.

**Taux d'appariement mesurés** — sur les 34 923 lignes :

| Bloc | Renseigné | Taux |
|---|---|---|
| Effort locatif T1-T2 (`loyer_petit`) | 34 900 | 99,9 % |
| Effort locatif T3+ (`loyer_familial`) | 34 900 | 99,9 % |
| Triple peine (`tension_2025`) | 34 900 | 99,9 % |
| Qualité DPE (`n_dpe`) | 34 794 | 99,6 % |
| Suroccupation communale | 34 908 | 100,0 % |
| **Prix immobilier (`prix_m2_tous`)** | **30 304** | **86,8 %** |
| **Surface finançable** | **28 357** | **81,2 %** |

Les deux derniers taux sont les seuls réellement bas, et pour une raison de fond : DVF ne
couvre pas les communes sans transaction sur la période, et l'Alsace-Moselle ainsi que Mayotte
sont hors périmètre DVF.

**Seuils et fiabilité :**

| Colonne | Règle | Effectif |
|---|---|---|
| `fiable_loyer_petit` | seuil de fiabilité ANIL | 33 631 (96,3 %) |
| `fiable_loyer_familial` | idem | 33 751 (96,6 %) |
| `fiable_prix` | volume de ventes suffisant dans DVF | **14 118 (40,4 %)** |
| `n_legs_dispo == 3` | les trois indicateurs disponibles | 13 690 |
| `triple_peine_median` vrai | cumul des trois échecs | **238** sur 13 690 |

> **`fiable_prix` ne vaut vrai que pour 40 % des communes.** Toute carte ou tout classement
> construit sur `prix_m2_*` ou `surface_financable` **doit filtrer sur cette colonne**, sous
> peine de publier des médianes calculées sur trois ventes. C'est la limite la plus contraignante
> du fichier.

**Dictionnaire :**

| Colonne | Type | Contenu |
|---|---|---|
| `insee_c` | texte(5) | code commune INSEE — **jamais numérique** |
| `libgeo` | texte | libellé de la commune |
| `dep`, `reg` | texte | département (2 ou 3 car.), région |
| `loyer_petit`, `loyer_familial` | € / mois | loyer d'annonce médian ANIL, par segment |
| `revenu_menage_proxy` | € / an | revenu disponible médian du ménage (ANCT/Filosofi) |
| `revenu_menage_d1` | € / an | premier décile de revenu |
| `effort_median_petit`, `effort_median_familial` | % | loyer / revenu médian |
| `effort_d1_petit`, `effort_d1_familial` | % | loyer / revenu au premier décile |
| `fiable_loyer_petit`, `fiable_loyer_familial` | booléen | fiabilité de l'estimation ANIL |
| `prix_m2_tous`, `prix_m2_appart` | € / m² | prix médian DVF, tous biens / appartements |
| `n_ventes_tous` | entier | nombre de transactions retenues |
| `surface_financable` | m² | surface achetable au taux et au prix courants |
| `categorie_surface` | texte | classe de surface finançable |
| `fiable_prix` | booléen | **à filtrer systématiquement** |
| `tension_2025` | ratio | demandes / attributions du parc social, département |
| `echec_loc_med`, `echec_loc_d1` | booléen | effort locatif au-delà du seuil |
| `echec_achat` | booléen | surface finançable insuffisante |
| `echec_social` | booléen | tension du parc social excessive |
| `n_legs_dispo` | 0-3 | nombre d'indicateurs disponibles |
| `n_dpe` | entier | diagnostics rattachés à la commune |
| `taux_passoires` | % | part de logements classés F ou G |
| `cout_median` | € / an | coût énergétique annuel médian |
| `suroccupation_commune` | % | **taux communal — non agrégeable par médiane** (§1) |
| `triple_peine_median`, `triple_peine_d1` | booléen ou vide | cumul des trois échecs |

**Limites.** Les loyers sont des **loyers d'annonce**, pas des loyers quittancés : ils
surestiment le marché réel, surtout en zone tendue. Le revenu est un proxy communal, pas le
revenu du ménage locataire. Les communes fusionnées ou déléguées portant un code hors
millésime 2025 (23 à 207 selon la source) apparaissent avec `libgeo` et `dep` vides.

### 7.2 `departements_tension.csv` — 101 lignes × 21 colonnes, 15,7 Ko

**Entrées** : `SNE_tension_ratio.csv` (00_SOURCES/SNE), `dept_effort_weighted_t12.csv`,
`dept_effort_weighted_t3p.csv`.

**Traitements :** filtrage sur `level == "Departement"` ; pivot année × département sur
`tension_ratio` (agrégation `median` — sans effet, une valeur par couple) ; jointure `outer`
avec les deux tables d'effort pondéré ; tri par `dep`.

**Dictionnaire :** `dep`, `nom`, puis `tension_2015` à `tension_2025` (ratio demandes /
attributions), puis pour chaque segment `n_communes_{petit,familial}` (communes fiables),
`effort_median_*` (médiane communale), `effort_pondere_*` (moyenne pondérée par les ménages),
`ecart_*` (pondéré − médian, en points).

**Limites.** 101 lignes : 96 départements métropolitains (Corse en `2A`/`2B`) et cinq DOM,
Mayotte comprise. C'est un département de plus que `departements_qualite.csv`, qui n'a pas de
ligne 976. La tension est **départementale** — elle est recopiée telle quelle sur chaque commune dans
`communes_acces.csv`, ce qui lisse toute hétérogénéité infra-départementale. **Le ratio national
ne s'obtient pas en prenant la médiane de cette colonne** (§2) : la bonne valeur est 7,34 pour
2025, la médiane départementale donnerait 5,17.

### 7.3 `departements_qualite.csv` — 100 lignes × 11 colonnes, 7,9 Ko

**Entrées** : `qualite_communes.csv`, `INSEE_logement_2022_dept.csv`.

**Traitements :** filtre `n_dpe` non nul, puis **seuil `n_dpe >= 20`** ; `taux_passoires`
agrégé en **moyenne pondérée par `n_dpe`** (et non en médiane — §2) ; `cout_median` en médiane
des communes retenues ; jointure `outer` avec la table INSEE départementale ; `part_cout_revenu`
calculée à part (§7.4) puis jointe en `left`.

**Dictionnaire :** `dep`, `n_dpe` (somme), `cout_median` (€/an), `n_communes` (communes au-delà
du seuil), `taux_passoires` (%, pondéré), `nb_rp` (résidences principales), `taux_suroccupation`
(%, **valeur INSEE directe, jamais recalculée depuis les communes**), `part_hlm`,
`part_loc_prive`, `taux_vacance` (%), `part_cout_revenu` (%, médiane communale du coût rapporté
au revenu).

**Limites.** 100 lignes et non 101 : **Mayotte (976) est absente** — elle est hors périmètre du
DPE communal, alors qu'elle est bien présente dans `departements_tension.csv`. Le
seuil `n_dpe >= 20` écarte 9 229 communes des 34 923 — les plus petites, donc les plus rurales.

### 7.4 `qualite_national.csv` — 8 lignes × 4 colonnes, 0,6 Ko

Table longue `cle / libelle / valeur / format`, destinée à l'affichage des cartouches nationaux.

| Clé | Valeur | Méthode |
|---|---|---|
| `taux_passoires` | 9,779 % | **pondérée par `n_dpe`** sur les départements |
| `cout_median` | 1 769 € | médiane des communes à `n_dpe >= 20` — *exception assumée au §2* |
| `part_revenu_med` | 4,772 % | médiane de `cout_median / revenu_menage_proxy` |
| `part_revenu_q1` | 3,859 % | premier quartile |
| `part_revenu_q3` | 5,851 % | troisième quartile |
| `n_communes_part_revenu` | 25 576 | communes du calcul ci-dessus |
| `taux_suroccupation` | 9,629 % | **Σ(taux × nb_rp) / Σ nb_rp** (§1) |
| `n_dpe` | 13 995 644 | diagnostics rattachés à une commune (§5) |

Le calcul de la part du revenu joint `qualite_communes` et `pouvoir_achat_immo` en `inner`,
supprime les valeurs manquantes puis applique `n_dpe >= 20` : 25 576 communes retenues.

**Limites.** La colonne `format` (`taux` / `euro` / `entier`) pilote l'arrondi d'affichage ; les
valeurs stockées ne sont pas arrondies (§9). Ne pas comparer `n_dpe` ici aux effectifs
nationaux du confort d'été — périmètres différents (§5).

### 7.5 `series_temporelles.csv` — 200 lignes × 9 colonnes, 8,7 Ko

**Entrées** : `serie_surface_national.csv`, `serie_surface_villes.csv`.

**Traitements :** le bloc national est renommé et complété de `taux_pct = taux × 100` ; le bloc
villes est **dépivoté** (`melt`) des colonnes `surface_2021`…`surface_2025` vers un couple
`annee` / `surface_financable` ; le taux annuel national est reporté sur les villes par
correspondance d'année ; concaténation, tri par périmètre, année, ville.

**Dictionnaire :** `perimetre` (`national` ou `ville`), `annee` (2021-2025), `ville`, `dep`,
`surface_financable` (m²), `prix_m2_median` (€/m², national seulement), `n_communes`
(national seulement), `taux_pct` (taux de crédit en %), `indice_capacite_2021_100` (base 100
en 2021, national seulement).

Série nationale publiée : **119,1 → 102,0 → 85,9 → 85,5 → 89,6 m²**, soit −29,5 m² et −24,8 %
entre 2021 et 2025.

**Limites.** Le panel communal varie d'une année à l'autre (16 947 communes en 2021,
14 068 en 2025) : la série nationale n'est **pas à panel constant**. C'est précisément pourquoi
`decomposition_prix_taux.csv` existe et travaille, lui, sur un panel fixe de 12 915 communes.
Les colonnes `prix_m2_median`, `n_communes` et `indice_capacite_2021_100` sont vides sur les
lignes `ville`.

### 7.6 `villes.csv` — 42 lignes × 16 colonnes, 5,8 Ko

**Entrées** : `grandes_villes_effort.csv`, `pouvoir_achat_grandes_villes.csv`,
`serie_surface_villes.csv`.

**Traitements :** renommage des trois tables ; jointures **`left` sur le nom de ville**, à
partir de la table d'effort ; tri par population décroissante.

**Dictionnaire :** `ville`, `dep`, `population`, `effort_petit` / `effort_familial` /
`effort_d1_familial` (%), `prix_m2_appart` (€/m²), `revenu_menage` (€/an),
`surface_financable` (m², 2025), `surface_2021`…`surface_2025` (m²), `delta_m2` et `delta_pct`
(évolution 2021→2025).

**Limites.** **La jointure se fait sur le libellé, pas sur le code INSEE** — c'est la seule
jointure textuelle de tout le pipeline, et donc le seul point où une variante d'accent ou de
graphie casserait l'appariement en silence. Les libellés sont normalisés en NFC en amont ;
Saint-Étienne est le cas test des contrôles (§8). Périmètre : les 42 plus grandes villes,
communes-centres uniquement, hors intercommunalité.

### 7.7 `decomposition_prix_taux.csv` — 6 lignes × 7 colonnes, 0,5 Ko

Répond à une seule question : dans la perte de surface finançable 2021→2025, quelle part
revient au prix, quelle part au taux de crédit ?

**Entrées** : `serie_surface_decomposition.csv`, `serie_surface_communes.csv`.

**Traitements :** les trois scénarios de référence sont lus **par appariement sur la colonne
`scenario`, jamais par position** — c'est la correction du bug F-1. Le scénario croisé
« prix 2021 + taux 2025 » est recalculé sur le panel des communes disposant des deux millésimes,
via le rapport des facteurs de financement (240 mois, assurance 0,30 %, taux 1,00 % en 2021 et
3,20 % en 2025). Les effets sont exprimés dans les **deux ordres de décomposition**.

| Ordre | Étape | Scénario | Surface | Effet | Part |
|---|---|---|---|---|---|
| prix → taux | 1 | prix 2021 + taux 2021 | 114,69 m² | — | — |
| prix → taux | 2 | prix 2025 + taux 2021 | 107,78 m² | −6,91 m² | 26,5 % |
| prix → taux | 3 | prix 2025 + taux 2025 | 88,63 m² | −19,15 m² | **73,5 %** |
| taux → prix | 2 | prix 2021 + taux 2025 | 94,31 m² | −20,38 m² | **78,2 %** |
| taux → prix | 3 | prix 2025 + taux 2025 | 88,63 m² | −5,68 m² | 21,8 % |

**Limites.** C'est une décomposition **non additive** : l'ordre change les parts (73,5 % contre
78,2 % pour le taux). Les deux sont publiés pour cette raison — annoncer un seul chiffre
supposerait un ordre arbitraire. Panel constant de **12 915 communes**, plus restreint que la
série de §7.5, d'où une base 2021 de 114,7 m² au lieu de 119,1 m². **Ne pas rapprocher les deux
séries sans le dire.**

### 7.8 `confort_ete.csv` — 190 lignes × 10 colonnes, 15,7 Ko

**Entrée unique** : `confort_ete_aggregats.json`, figé au 27 juillet 2026 (§4).

**Traitements :** mise à plat du JSON en table longue. Une ligne par croisement, la colonne
`dimension` indiquant le niveau : `national`, `paradoxe_ab`, `par_etiquette`, `par_region`,
`par_departement`, `par_energie`, `par_periode`, `par_batiment`,
`paris_arrondissements`, `sous_critere`. Les codes région sont traduits en libellés par une
table interne de 18 entrées. Les sous-critères produisent deux lignes chacun, clé
`{critere}|{insuffisant,bon}`.

**Dictionnaire :** `dimension`, `cle`, `libelle`, `bon` / `moyen` / `insuffisant` (effectifs),
`renseigne` (diagnostics renseignés), `total_dpe` (diagnostics du périmètre),
`pct_insuffisant`, `pct_bon` (%).

**Limites.** Les lignes `sous_critere` n'ont **ni** `bon`, `moyen`, `insuffisant`, **ni**
`total_dpe` : leur `pct_insuffisant` est une part de « oui » sur les renseignés, pas une
répartition en trois classes. Les taux se calculent sur `renseigne` (68 % des diagnostics), pas
sur `total_dpe`. **Les effectifs vieillissent, les parts non** (§4.1).

---

## 8. Contrôles automatiques

`build_dashboard_data.py` exécute **47 contrôles** avant tout export et **n'écrit rien** si l'un
d'eux échoue (`exit 1`). Ils vérifient que les agrégats restituent les valeurs publiées.

| Famille | Contrôles | Valeurs de référence |
|---|---|---|
| Effort locatif | 4 | 14,8 / 20,8 / 29,5 / 42,7 % |
| Distribution de l'effort | 3 | 2,6 % et 86,6 % au-delà de 33 % ; 5 163 communes au D1 |
| Surface finançable | 6 | médiane 88,8 m² ; série 119,1 → 89,6 |
| Triple peine | 2 | 13 690 communes à trois indicateurs, **238** en triple peine |
| Qualité du parc | 3 | passoires 9,8 % ; coût 1 769 € ; suroccupation 9,6 % |
| Grandes villes | 5 | Paris 35,4 / 63,3 / 159,4 % et 21,5 m² ; Saint-Étienne 70,4 m² |
| Décomposition prix / taux | 8 | 114,7 / 107,8 / 88,6 / 94,3 m² ; 73 % et 78 % ; panel 12 915 |
| Perte nationale | 2 | −29,5 m², −24,8 % |
| Tension du parc social | 3 | médiane départementale 5,17 ; ratios 4,06 et 7,34 |
| Part du revenu | 4 | 4,8 / 3,9 / 5,9 % ; 25 576 communes |
| Confort d'été | 6 | 40,0 et 17,3 % ; effectifs 1 793 312 / 4 436 103 / 4 144 821 ; Hauts-de-France 51,2 % |
| Volume | 1 | plafond de 20 Mo sur l'ensemble des sorties |

**Toute modification du pipeline doit laisser ces contrôles au vert.** C'est le garde-fou
qui garantit que le dashboard ne diverge pas du rapport.

Deux contrôles méritent d'être lus pour ce qu'ils sont : « région Hauts-de-France nommée et
retrouvée » vérifie que la **table de traduction des codes région** fonctionne, et
« Saint-Étienne, surface finançable » vérifie que la **jointure textuelle accentuée** de §7.6
tient. Ce ne sont pas des tests de valeur, ce sont des tests de jointure.

---

## 9. Écarts d'arrondi entre calcul et affichage

Les valeurs calculées portent plus de décimales que les valeurs publiées : 14,79 contre 14,8 ;
9,779 contre 9,8 ; 9,629 contre 9,6. **Le dashboard applique les arrondis d'affichage du
rapport** — une décimale sur les taux, zéro sur les effectifs et les euros — via une fonction de
formatage unique, `theme.fmt()`. Aucun arrondi n'est appliqué aux données stockées.

---

## 10. Mettre à jour le jeu de données

Dans l'ordre, et sans sauter le dernier point.

1. **Nouveau millésime DVF, DPE ou RPLS** — déposer les bruts dans `00_SOURCES/`, puis
   `01_PIPELINE/run_all_from_raw.sh` (2 h 30 à 4 h, 6 Go libres exigés).
2. **Modification du code seul** — `01_PIPELINE/run_all.sh` (environ 2 minutes), puis
   comparer les 61 empreintes au témoin de reproductibilité, et les 10 cartes interactives à leur
   empreinte de contenu. *(Ce témoin vit dans le dossier
   de mission, pas dans cette livraison.)*
3. **Confort d'été** — voir §4 : re-télécharger en incluant les six colonnes, et documenter la
   nouvelle date d'extraction.
4. **Régénérer le dashboard** — `python pipeline/build_dashboard_data.py`, qui refuse d'écrire
   si un contrôle échoue.

> **Le piège qui attend QCE.** Sur toute donnée indexée par une année, retrouver la valeur
> **par son année**, jamais par sa position, et dériver les libellés des données. Un millésime
> supplémentaire ne fait pas planter un script qui indexe par position : il lui fait comparer
> les mauvaises années sous un libellé inchangé. Un faux chiffre, sans message d'erreur. Ce cas
> a été trouvé et corrigé dans `rapport_bloc45_charts.py` pendant l'audit de robustesse.

En cas de doute sur une valeur publiée, le référentiel qui fait foi — y compris pour les
valeurs arbitrées et les données figées — est conservé côté TSE Junior Études. Demandez-le
plutôt que de recalculer.
