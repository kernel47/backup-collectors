# Backup Collector

Backup Collector exécute une collecte depuis un asset de sauvegarde, parse les données
selon un scope, puis les envoie vers une destination.

Le flux est volontairement explicite :

```text
cli.py
  -> runtime.py
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

```bash
python -m pip install -e '.[dev]'
```

Le module `netbackup-py` reçoit uniquement le hostname du master server. Il reste
responsable de chercher sa configuration et ses secrets dans le référentiel.

Variables disponibles pour les destinations :

```text
BACKUP_HUB_URL, BACKUP_HUB_TOKEN
LOGSTASH_URL, LOGSTASH_TOKEN
REFERENTIAL_URL, REFERENTIAL_TOKEN
BACKUP_COLLECTOR_OUTPUT_DIR, BACKUP_COLLECTOR_LOG_LEVEL
```

## Commandes

L'aide intégrée rappelle les paramètres disponibles et contient des exemples :

```bash
backup-collector --help
backup-collector collect --help
```

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

## Tests

```bash
python -m pytest
ruff check .
```

Les tests n'effectuent aucun appel réel vers NetBackup ou une destination HTTP.
