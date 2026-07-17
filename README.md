# Backup Collector

Backup Collector exécute une collecte depuis un asset de sauvegarde, parse les données
selon un scope, puis les envoie vers une destination.

Le flux est volontairement explicite :

```text
cli.py
  -> runtime.py
  -> services/referential.py pour résoudre le hostname en objet Asset
  -> collectors/netbackup.py ou collectors/datadomain.py
  -> modules/netbackup.py pour accéder au package externe nbu
  -> parsers/service.py
  -> parsers/pamela.py, parsers/logstash.py ou parsers/baseline.py
  -> services/output.py
  -> Backup Hub, Logstash, Referential, fichier ou stdout
```

Il n'existe ni registre dynamique, ni découverte automatique, ni classe par petit
composant. `runtime.py` contient les branchements lisibles qui sélectionnent la source,
le parser et l'output.

## Structure

```text
modules/
└── netbackup.py     # wrapper du package externe netbackup-py / nbu

collectors/
├── netbackup.py     # collectes policies, jobs, images et shares
├── datadomain.py    # futur collecteur Data Domain
└── tapelibrary.py   # futur collecteur Tape Library

parsers/
├── pamela.py        # parsing Pamela
├── logstash.py      # parsing des événements envoyés à Logstash
├── baseline.py      # règles et format Baseline
└── service.py       # sélection explicite du parser selon le scope

services/
├── referential.py   # recherche d'un asset à partir de son hostname
├── output.py        # Backup Hub, Logstash, Referential, fichier et stdout
└── icinga.py        # messages, logs et codes retour Icinga
```

Les fichiers racine restent simples :

- `cli.py` définit les arguments, crée le contexte et lance la commande ;
- `runtime.py` exécute le flux complet ;
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
backup-collector collect netbackup policies --asset master-01 --scope pamela
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
backup-collector collect netbackup policies \
  --asset master-emea-01 \
  --scope pamela

backup-collector collect netbackup jobs \
  --asset master-emea-01 \
  --scope pamela \
  --hours 24

backup-collector collect netbackup images \
  --asset master-emea-01 \
  --scope logstash

backup-collector collect netbackup shares \
  --asset master-emea-01 \
  --scope logstash \
  --output file

backup-collector collect netbackup baseline \
  --asset master-emea-01 \
  --scope baseline \
  --output referential
```

La route Data Domain existe déjà, mais son collecteur sera défini ultérieurement :

```bash
backup-collector collect datadomain future --asset dd-01 --scope pamela
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
