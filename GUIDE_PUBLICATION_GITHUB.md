# Publier et maintenir le tableau de bord — guide pas à pas

**Pour qui.** Une personne de Que Choisir Ensemble qui ne programme pas. Aucune ligne de
commande n'est nécessaire : tout se fait dans un navigateur.

**Ce que vous obtiendrez.** Une adresse web publique, du type
`https://votre-nom-dapp.streamlit.app`, qui affiche le tableau de bord et que vous pourrez
mettre à jour vous-même.

**Combien de temps.** Comptez 30 minutes la première fois. Les mises à jour suivantes prennent
2 minutes.

**Ce que ça coûte.** Rien. Les deux services utilisés — GitHub et Streamlit Community Cloud —
ont une offre gratuite qui suffit largement à cet usage.

---

## Ce que vous avez sous la main

Le dossier **`code/dashboard/`** de la livraison. Il contient exactement ceci :

```
app.py                      l'application elle-meme
theme.py                    couleurs et mise en forme QCE
data_loader.py              chargement des donnees
requirements.txt            liste des composants a installer
runtime.txt                 version de Python a utiliser
.streamlit/config.toml      reglages d'affichage
data_dashboard/             8 fichiers CSV — les donnees
images/                     3 cartes du rapport, affichees dans l'onglet Qualite
pipeline/                   le script qui regenere les donnees
```

**Poids total : environ 12 Mo.** C'est petit. Aucun fichier n'approche les limites décrites
au § 7.

> **Le point de vocabulaire qui débloque tout le reste.** GitHub est un **classeur en ligne**
> où vivent les fichiers. Streamlit est le **service qui les fait tourner** et produit la page
> web. Streamlit ne stocke rien : il va chercher les fichiers sur GitHub à chaque démarrage.
> C'est pourquoi il faut faire les deux, et dans cet ordre.

---

## 1. Créer un compte GitHub

1. Aller sur **https://github.com/signup**.
2. Saisir une adresse électronique. **Utilisez une adresse de l'association, pas une adresse
   personnelle** — voir l'encadré ci-dessous.
3. Choisir un mot de passe et un nom d'utilisateur. Le nom d'utilisateur apparaîtra dans
   l'adresse du dépôt ; quelque chose comme `que-choisir-ensemble` convient.
4. Valider le code reçu par courriel.
5. À la question sur l'offre, choisir **Free**.

> **Qui doit détenir ce compte.** Le tableau de bord tourne aujourd'hui sur un compte
> personnel du prestataire. Le but de ce guide est précisément que ce ne soit plus le cas.
> Créez le compte au nom de l'association, avec une adresse électronique à laquelle **plusieurs
> personnes ont accès** (une boîte partagée, ou une redirection). Un compte rattaché à une
> personne qui part est un compte perdu.

---

## 2. Créer le dépôt

Un « dépôt » (*repository*) est un dossier hébergé sur GitHub.

1. Une fois connecté, cliquer sur le **+** en haut à droite, puis **New repository**.
2. **Repository name** : `dashboard-logement` (ou un autre nom, sans espace ni accent).
3. **Description** : facultative. Par exemple *Tableau de bord — accès au logement en France*.
4. **Choisir `Public`.** Voir l'encadré ci-dessous.
5. **Ne cocher aucune** des cases « Add a README file », « Add .gitignore », « Choose a
   license ». Elles créeraient des fichiers qui compliqueraient l'étape suivante.
6. Cliquer sur **Create repository**.

> **Pourquoi public, et non privé.** L'offre gratuite de Streamlit Community Cloud est prévue
> pour des dépôts publics. Publier depuis un dépôt privé demande d'accorder à Streamlit des
> autorisations supplémentaires sur votre compte GitHub, et le nombre d'applications privées
> est limité — c'est le motif de refus le plus fréquent au moment de déployer. Comme le tableau
> de bord est destiné à être diffusé et que **les données publiées sont déjà des données
> publiques**, le dépôt public est le choix simple et sans friction. Ne déposez simplement
> jamais dans ce dépôt un fichier que vous ne publieriez pas sur le site de l'association.

Vous arrivez sur une page qui affiche des instructions en ligne de commande. **Ignorez-les.**
Cherchez la ligne « uploading an existing file » et cliquez sur ce lien — ou allez directement
à l'étape 3.

---

## 3. Déposer les fichiers, sans ligne de commande

Sur la page de votre dépôt vide, cliquer sur **uploading an existing file**. Si le dépôt n'est
plus vide, le chemin est : onglet **Add file** → **Upload files**.

Vous voyez une zone « Drag files here to add them to your repository ».

### 3.1 D'abord les fichiers isolés

Ouvrir le dossier `code/dashboard/` sur votre ordinateur. **Sélectionner les cinq fichiers qui ne sont
pas dans un sous-dossier** — `app.py`, `theme.py`, `data_loader.py`, `requirements.txt`,
`runtime.txt` — et les faire glisser dans la zone.

Les noms apparaissent en liste. En bas de page, dans **Commit changes**, écrire un court
message : `Depot initial de l'application`. Cliquer sur **Commit changes**.

### 3.2 Puis les dossiers, un par un

Retourner sur **Add file** → **Upload files**.

Faire glisser le **dossier entier** `data_dashboard` — pas son contenu, le dossier lui-même.
GitHub conserve l'arborescence et affichera `data_dashboard/communes_acces.csv`, etc.

Valider avec **Commit changes**.

Recommencer pour les dossiers `images` puis `pipeline`.

### 3.3 Le dossier `.streamlit`, qui demande une manipulation

`.streamlit` commence par un point : **votre système d'exploitation le cache par défaut**, et
vous ne pourrez pas le faire glisser si vous ne le voyez pas.

- **macOS** : dans le Finder, appuyer sur **⌘ + Maj + .** (commande, majuscule, point) pour
  afficher les fichiers cachés. Le dossier apparaît en grisé. Refaire ⌘ + Maj + . ensuite pour
  les recacher.
- **Windows** : dans l'Explorateur, onglet **Affichage** → cocher **Éléments masqués**.

Faire glisser le dossier `.streamlit` comme les précédents, puis **Commit changes**.

> **Si le dossier refuse obstinément de se déposer**, il existe un contournement sans fichier
> caché : sur GitHub, **Add file** → **Create new file**, taper dans le champ du nom
> `.streamlit/config.toml` — la barre oblique crée automatiquement le dossier — puis coller le
> contenu du fichier `config.toml` que vous avez sur votre ordinateur (ouvrez-le avec le
> Bloc-notes ou TextEdit). Valider avec **Commit new file**.

### 3.4 Vérifier

Sur la page d'accueil du dépôt, vous devez voir **neuf entrées** : les dossiers `.streamlit`,
`data_dashboard`, `images`, `pipeline`, et les fichiers `app.py`, `data_loader.py`,
`requirements.txt`, `runtime.txt`, `theme.py`.

Cliquer sur `data_dashboard` : les **8 fichiers CSV** doivent y être. S'il en manque un, refaire
un dépôt pour celui-là — redéposer un fichier existant ne casse rien, il est simplement
remplacé.

---

## 4. Publier avec Streamlit

1. Aller sur **https://share.streamlit.io**.
2. Cliquer sur **Continue with GitHub**, puis **Authorize streamlit**. C'est ce qui permet à
   Streamlit de lire votre dépôt.
3. Cliquer sur **Create app**, puis choisir l'option indiquant que l'application existe déjà
   sur GitHub (*Deploy a public app from GitHub*).
4. Remplir le formulaire :

   | Champ | Valeur |
   |---|---|
   | **Repository** | `votre-nom-utilisateur/dashboard-logement` |
   | **Branch** | `main` |
   | **Main file path** | `app.py` |
   | **App URL** | l'adresse publique — modifiable, par exemple `acces-logement-france` |

5. **Ne pas cliquer sur Deploy tout de suite.** Ouvrir d'abord **Advanced settings**.

### 4.1 Advanced settings — l'étape qu'il ne faut pas sauter

Dans **Advanced settings**, un menu **Python version** propose plusieurs versions.

**Choisir 3.13.**

C'est le réglage qui fait échouer le plus de premiers déploiements, et son message d'erreur ne
dit jamais « mauvaise version de Python » : l'installation s'interrompt sur `pyarrow` ou
`numpy`, avec plusieurs dizaines de lignes de compilation illisibles.

Le fichier `runtime.txt` du dépôt déclare bien `python-3.13`, mais **le réglage de cet écran
l'emporte** en cas de divergence. Réglez les deux sur la même valeur, et le problème disparaît.

> L'application a été développée et vérifiée sur **Python 3.13.0**. Elle ne s'installe pas sur
> Python 3.14.

6. Cliquer sur **Deploy**.

L'écran affiche le journal d'installation pendant deux à cinq minutes. Puis le tableau de bord
apparaît. **Notez l'adresse et diffusez-la.**

---

## 5. Mettre à jour plus tard

C'est la partie rassurante : **il n'y a rien à redéployer**. Streamlit surveille le dépôt et
redémarre l'application tout seul, en une minute environ, dès qu'un fichier change.

### Remplacer un fichier de données

1. Sur GitHub, ouvrir le dossier `data_dashboard`.
2. **Add file** → **Upload files**.
3. Faire glisser le nouveau CSV. **Il doit porter exactement le même nom** que celui qu'il
   remplace — sinon il s'ajoute au lieu de le remplacer, et l'application continue de lire
   l'ancien.
4. Écrire un message de validation utile : `Mise a jour des donnees DVF millesime 2026`, plutôt
   que `maj`. Dans six mois, ce message sera la seule trace de ce que vous avez fait.
5. **Commit changes**.

### Corriger un texte de l'application

1. Ouvrir `app.py` sur GitHub, cliquer sur l'icône **crayon** (Edit this file).
2. Modifier le texte entre guillemets, sans toucher au reste.
3. **Commit changes** en bas.

### Suivre le redémarrage

Sur `share.streamlit.io`, l'application apparaît en *Running*. Le menu **⋮** donne accès à
**Reboot app** si elle reste bloquée, et à **Settings** pour retrouver le réglage de version de
Python.

### Revenir en arrière

Tout est conservé. Onglet **Commits** du dépôt : chaque validation est datée, avec son message
et le détail de ce qui a changé. On peut y consulter n'importe quelle version antérieure d'un
fichier et la restaurer.

---

## 6. Régénérer les données depuis les bases sources

Cette section-ci **demande de savoir exécuter un script**, contrairement à tout le reste du
guide. Elle n'est utile que lorsqu'un nouveau millésime de données paraît (DVF, DPE, RPLS).

Le dépôt ne contient **pas** les bases sources : elles pèsent 15 Go et vivent dans le dossier de
mission. La marche à suivre complète est dans `METHODOLOGIE_DONNEES.md` § 10.

Résumé :

1. rejouer le pipeline de mission — `01_PIPELINE/run_all.sh` ;
2. régénérer les agrégats — `python pipeline/build_dashboard_data.py`, qui exécute
   **47 contrôles de conformité au rapport et n'écrit rien si l'un échoue** ;
3. déposer les CSV mis à jour sur GitHub, comme au § 5.

Deux points à connaître avant de s'y lancer :

- **Le confort d'été ne se régénère pas** depuis les bases livrées. Il provient d'une
  extraction figée au 27 juillet 2026. Voir `METHODOLOGIE_DONNEES.md` § 4.
- **Un nouveau millésime est le moment où les erreurs silencieuses apparaissent.** Faites
  vérifier le résultat par quelqu'un qui sait lire les contrôles — c'est l'objet du
  § 10 de la méthodologie.

---

## 7. Si un fichier dépasse 25 Mo

Le plafond de l'interface web est de **25 Mo par fichier**. Cette section explique quoi faire
le jour où un fichier le dépasse — ce qui n'arrivera pas tout de suite, mais qui arrivera si
vous ajoutez des millésimes pendant plusieurs années.

### Où vous en êtes aujourd'hui

| Fichier | Poids | Marge avant 25 Mo |
|---|---|---|
| `data_dashboard/communes_acces.csv` | **6,9 Mo** | 18,1 Mo |
| tous les autres réunis | 0,07 Mo | — |

**Le nombre de communes ne bouge pas** : il est fixé à 34 923 par le socle ANIL. Un nouveau
millésime n'ajoute donc pas de lignes, il ajoute des **colonnes** — une par indicateur et par
année. Chaque colonne pèse environ **0,42 Mo**.

**Vous pouvez ajouter une quarantaine de colonnes avant d'atteindre le plafond**, soit
plusieurs années de mises à jour. Ce n'est pas un problème imminent ; c'est un problème à
reconnaître le jour où il se présente.

### Comment savoir avant de déposer

Avant tout dépôt, regardez le poids du fichier dans votre explorateur de fichiers
(clic droit → **Propriétés** sous Windows, **Lire les informations** sous macOS).

- **En dessous de 25 Mo** : déposez normalement.
- **Entre 25 et 100 Mo** : l'interface web refuse. Voir ci-dessous.
- **Au-dessus de 100 Mo** : GitHub refuse par toutes les voies. Il faut alléger le fichier,
  il n'y a pas de contournement.

Le refus est explicite : *« yourfile.csv is 32 MB; we recommend files be under 25 MB »*, et le
bouton de validation reste inactif.

### Les trois solutions, de la meilleure à la moins bonne

**1. Vérifier d'abord que le fichier devrait vraiment être si gros.** C'est le réflexe utile,
et souvent la vraie réponse. Un fichier qui triple d'un coup signale en général une erreur de
régénération — des lignes dupliquées, ou un identifiant de commune passé en nombre qui a fait
échouer une jointure et multiplié les lignes. **Ouvrez le fichier et comptez les lignes : il
doit y en avoir 34 923, plus l'en-tête.** Si le compte n'y est pas, le problème n'est pas la
taille, c'est le contenu — ne le déposez pas.

**2. Ne garder que les colonnes utiles.** Le dashboard n'affiche pas toutes les colonnes
disponibles. Si l'on a accumulé dix millésimes de taux d'effort alors que l'application n'en
montre que les cinq derniers, les cinq plus anciens peuvent quitter le fichier publié — ils
restent dans le dossier de mission. C'est une modification d'une ligne dans
`pipeline/build_dashboard_data.py`, à faire faire par quelqu'un qui code.

**3. Compresser le fichier.** Un CSV se compresse d'environ 80 % : les 6,9 Mo actuels
tomberaient sous 1,5 Mo. Le fichier devient `communes_acces.csv.gz`, et l'application le lit
**sans aucune modification du code** — `pandas` reconnaît l'extension tout seul. Il faut
seulement changer le nom du fichier appelé dans `data_loader.py`. Là encore : une ligne, mais
par quelqu'un qui code.

> **Ce qu'il ne faut pas faire : découper le fichier en morceaux** (un par région, par
> exemple). C'est la solution qui vient spontanément à l'esprit et c'est la plus coûteuse :
> elle oblige à modifier le chargement, multiplie les fichiers à tenir à jour, et introduit
> exactement le risque qu'on cherche à éviter — un morceau mis à jour et pas les autres, sans
> que rien ne le signale.

### La voie de secours, si quelqu'un peut vous aider

Un fichier entre 25 et 100 Mo passe **par la ligne de commande**, qui a un plafond de 100 Mo au
lieu de 25. Cela demande dix minutes à une personne qui sait faire, une seule fois. Ce n'est pas
une bonne solution durable — le fichier restera lourd et chaque mise à jour redemandera la même
aide — mais cela débloque une échéance.

**Git LFS, en revanche, est à éviter** : c'est le dispositif que GitHub propose pour les gros
fichiers, et il est mal pris en charge par l'hébergement gratuit de Streamlit. L'application
risque de démarrer en lisant un fichier de remplacement de quelques centaines d'octets au lieu
de vos données, **sans message d'erreur** — elle affichera simplement un tableau vide.

---

## 8. Ce qui peut coincer

Par ordre de fréquence réelle.

### « Error installing requirements » au déploiement

**Cause** : mauvaise version de Python, neuf fois sur dix. Le journal montre des lignes de
compilation sur `pyarrow` ou `numpy`.
**Correction** : sur `share.streamlit.io`, menu **⋮** de l'application → **Settings** →
**Python version** → **3.13** → **Save**. L'application se réinstalle.

### Un fichier refuse de se déposer sur GitHub

Deux plafonds différents, et c'est celui du milieu qui surprend :

| Voie | Limite par fichier |
|---|---|
| **Interface web** (ce guide) | **25 Mo** |
| Ligne de commande | 100 Mo — avertissement dès 50 Mo |

Aucun fichier de cette livraison n'approche ces seuils : le plus lourd,
`data_dashboard/communes_acces.csv`, pèse **6,9 Mo**. Mais si vous ajoutez un jour un export
plus gros, c'est **25 Mo** qui compte, pas 100.

L'interface web accepte par ailleurs **100 fichiers au maximum par dépôt**. Déposez les dossiers
un par un, comme au § 3.

### « This app has gone to sleep »

Normal, et sans gravité. Les applications gratuites se mettent en veille après quelques jours
sans visite. **Le bouton présent sur la page la réveille en une minute**, et n'importe quel
visiteur peut le faire. Aucune donnée n'est perdue.

Si le tableau de bord doit rester immédiatement disponible — le jour d'une conférence de
presse, par exemple — ouvrez-le une fois le matin.

### L'application affiche d'anciens chiffres après une mise à jour

Vérifiez d'abord que le fichier déposé porte **exactement** le même nom que l'ancien (§ 5).
Si c'est le cas, forcez un redémarrage : menu **⋮** → **Reboot app**.

### Le dépôt a été créé en privé

Sur GitHub : **Settings** du dépôt → tout en bas, section **Danger Zone** → **Change repository
visibility** → **Make public**. Puis redéployer.

---

## 9. À faire une fois que tout fonctionne

Trois précautions qui coûtent dix minutes et évitent de tout reperdre.

1. **Ajouter une deuxième personne au dépôt.** GitHub : **Settings** → **Collaborators** →
   **Add people**. Un seul détenteur, c'est un point de défaillance unique.
2. **Noter l'adresse de l'application et les identifiants** dans le classeur partagé de
   l'association — pas dans une boîte de courriel personnelle.
3. **Faire la manipulation une fois, à blanc, avec quelqu'un d'autre.** Modifier un titre dans
   `app.py`, vérifier que la page change, remettre le titre d'origine. C'est le seul moyen de
   savoir que le guide fonctionne pour une autre personne que celle qui l'a lu la première fois.

---

## En cas de blocage

Le journal de déploiement affiché par Streamlit — **Manage app** en bas à droite de
l'application — contient toujours la cause réelle, à la fin du texte. Les dix dernières lignes
suffisent en général à identifier le problème, et sont ce qu'il faut transmettre pour obtenir
de l'aide.

Documents liés :

| Document | Contenu |
|---|---|
| `METHODOLOGIE_DONNEES.md` | d'où vient chaque chiffre, et les pièges de calcul |
| `DEPLOIEMENT.md` | la même publication, vue côté technique |
| `README.md` | ce que contient la livraison |
