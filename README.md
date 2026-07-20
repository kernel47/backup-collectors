# Backup Collector

Backup Collector exécute une collecte depuis un asset de sauvegarde, parse les données
selon un scope, puis les envoie vers une destination.

Le scope choisit une séquence complète. Chaque type de données est collecté, parsé et
envoyé avant de passer au suivant afin de limiter la mémoire utilisée.

Le flux est volontairement explicite :

```text
cli.py
  -> runtime.py
  -> services/referential.py pour résoudre le hostname en objet Asset
  -> collectors/<scope>/collector.py
  -> collectors/netbackup.py, datadomain.py ou tapelibrary.py
  -> modules/netbackup.py pour accéder au package externe nbu
  -> collectors/<scope>/parser.py
  -> collectors/<scope>/output.py
  -> services/output.py
  -> Backup Hub, Logstash, Referential, fichier ou stdout
```

Il n'existe ni registre dynamique, ni découverte automatique, ni classe par petit
composant. `runtime.py` contient uniquement les branchements lisibles qui sélectionnent
le scope. Chaque scope reste autonome pour ses collectes, son traitement et sa sortie.

## Structure

```text
modules/
└── netbackup.py     # wrapper du package externe netbackup-py / nbu

collectors/
├── netbackup.py             # accès technique à la source NetBackup
├── datadomain.py            # futur accès technique à Data Domain
├── tapelibrary.py           # futur accès technique à Tape Library
├── pamela/
│   ├── collector.py         # séquence policies -> clients -> jobs
│   ├── parser.py            # traitement et filtres Pamela
│   └── output.py            # destination Backup Hub
├── logstash/
│   ├── collector.py         # séquence jobs -> policies -> images
│   ├── parser.py            # format des événements Logstash
│   └── output.py            # destination Logstash
└── baseline/
    ├── collector.py         # séquence propre à chaque source
    ├── parser.py            # règles Baseline
    └── output.py            # destination Referential

services/
├── referential.py   # recherche d'un asset à partir de son hostname
├── output.py        # Backup Hub, Logstash, Referential, fichier et stdout
└── icinga.py        # messages, logs et codes retour Icinga
```

Les fichiers racine restent simples :

- `cli.py` définit les arguments, crée le contexte et lance la commande ;
- `runtime.py` résout l'asset et transmet l'exécution au collecteur du scope ;
- `models.py` contient toutes les dataclasses, y compris le contexte, les résultats et
  les réglages des destinations ;
- `exceptions.py` contient les erreurs applicatives.

## Installation

Installation classique des dépendances :

```bash
python -m pip install -r requirements.txt
```

Installation du projet avec la commande `backup-collector` et les outils de
développement :

```bash
python -m pip install -e '.[dev]'
```

Une fois le venv activé, cette installation crée directement la commande :

```bash
backup-collector --help
backup-collector collect netbackup --asset master-01 --scope pamela
```

Il n'est donc plus nécessaire d'utiliser `python cli.py`. Si la commande n'est pas
trouvée, vérifier que le bon venv est actif avec `which python` et
`which backup-collector`, puis relancer `python -m pip install -e .`.

Créer ensuite la configuration locale à partir de l'exemple :

```bash
cp .env.example .env
set -a
source .env
set +a
```

Le programme lit les variables d'environnement ; il ne charge pas automatiquement le
fichier `.env`.

La valeur de `--asset` est toujours un hostname. Avant la collecte, le runtime appelle
le référentiel externe et construit un objet `Asset` contenant :

```text
hostname
api_username, api_password, api
ssh_username, ssh_password, ssh
domain_type, domain_name, version
region, datacenter
```

Les noms `api_username` et `ssh_username` évitent toute ambiguïté entre les deux jeux
d'identifiants. Les mots de passe sont exclus de la représentation texte de l'objet
pour éviter leur apparition accidentelle dans les logs.

`REFERENTIAL_ASSET_URL` configure la recherche. L'URL peut contenir le placeholder
`{hostname}` ; sinon le hostname est ajouté à la fin du chemin :

```text
REFERENTIAL_ASSET_URL=https://referential.example.test/api/assets/{hostname}
```

`modules/netbackup.py` utilise ensuite les paramètres API de cet objet pour créer le
client `netbackup-py`. Le support SSH pourra utiliser les paramètres SSH du même objet.

Variables disponibles pour les destinations :

```text
BACKUP_HUB_URL, BACKUP_HUB_TOKEN
LOGSTASH_URL, LOGSTASH_TOKEN
REFERENTIAL_ASSET_URL, REFERENTIAL_URL, REFERENTIAL_TOKEN
BACKUP_COLLECTOR_OUTPUT_DIR, BACKUP_COLLECTOR_LOG_LEVEL
```

`REFERENTIAL_ASSET_URL` sert à lire la configuration de l'asset.
`REFERENTIAL_URL` reste la destination d'écriture du scope `baseline`.

## Commandes

L'aide intégrée rappelle les paramètres disponibles et contient des exemples :

```bash
backup-collector --help
backup-collector collect --help
```

Dans un terminal interactif, la commande affiche la progression de la résolution de
l'asset, de la collecte, du parsing et de l'envoi. Utiliser `--no-progress` pour la
masquer ou `--progress` pour la forcer dans un terminal non interactif. Le format
Icinga reste automatiquement sur une seule ligne hors terminal.

```bash
backup-collector collect netbackup \
  --asset master-emea-01 \
  --scope pamela

backup-collector collect netbackup \
  --asset master-emea-01 \
  --scope pamela \
  --hours 24

backup-collector collect netbackup \
  --asset master-emea-01 \
  --scope logstash

backup-collector collect netbackup \
  --asset master-emea-01 \
  --scope baseline \
  --output referential
```

Les workflows sont explicites :

```text
pamela + netbackup   : policies -> clients -> jobs       -> Backup Hub
logstash + netbackup : jobs -> policies -> images        -> Logstash
baseline + netbackup : policies                          -> Referential
```

Par exemple, Pamela envoie les policies avant de commencer les clients, puis envoie
les clients avant de collecter les jobs. Les listes des étapes précédentes ne sont donc
pas conservées pendant la collecte suivante. Les totaux sont cumulés pour le résumé
final.

Pour ajouter ou modifier un besoin futur propre à Pamela, Baseline ou Logstash, les
changements restent dans le dossier du scope concerné. Les collecteurs techniques de
source et les services génériques ne changent que si leur protocole évolue.

Les routes Baseline Data Domain et Tape Library existent déjà, mais leurs collecteurs
seront définis ultérieurement :

```bash
backup-collector collect datadomain --asset dd-01 --scope baseline
backup-collector collect tapelibrary --asset tl-01 --scope baseline
```

## Outputs

Sans `--output`, la destination dépend du scope :

```text
pamela    -> backup_hub
logstash  -> logstash
baseline  -> referential
```

Une commande peut surcharger cette destination avec :

```text
--output backup_hub
--output logstash
--output referential
--output file
--output stdout
```

`--output file` écrit atomiquement sous :

```text
$BACKUP_COLLECTOR_OUTPUT_DIR/<scope>/<source>/<data_type>/
```

## Icinga

`services/icinga.py` est le seul fichier à modifier pour changer les messages, les logs
ou les codes retour : `0 OK`, `1 WARNING`, `2 CRITICAL`, `3 UNKNOWN`.

Chaque collecte terminée écrit aussi un log `INFO` avec le statut, le total collecté,
le total parsé, le total envoyé et la durée. Pour l'afficher :

```bash
export BACKUP_COLLECTOR_LOG_LEVEL=INFO
```

## Tests

```bash
python -m pytest
ruff check .
```

Les tests n'effectuent aucun appel réel vers NetBackup ou une destination HTTP.
