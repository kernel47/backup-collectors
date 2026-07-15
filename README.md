# Backup Collector

Backup Collector est un noyau Python 3.12 destiné à être exécuté par Icinga sur une
machine Sys Activity. Il collecte des données d'assets de sauvegarde, les transforme
pour un besoin métier, puis les envoie à une destination technique.

Une collecte est définie par trois valeurs :

- la **source** récupère les données de l'asset (`netbackup`) ;
- le **data type** indique les données (`policies`, `jobs`, `images`, `shares`) ;
- le **scope** choisit le format et la destination (`pamela`, `elk`, `baseline`).

La séparation reste volontairement directe :

```text
CLI -> Source -> CollectionResult -> Scope/Parser -> Output -> ExecutionResult
```

NetBackup passe exclusivement par le package Python `nbu`, isolé derrière l'adaptateur
`external/netbackup.py`. Backup Collector lui transmet uniquement le hostname du master
server ; `netbackup-py` reste responsable de retrouver sa configuration et ses secrets.
Pamela envoie par défaut vers Backup Hub, ELK vers Logstash et Baseline vers le
référentiel. Les destinations JSON et stdout permettent de tester sans appel HTTP.

## Installation et configuration

```bash
python -m pip install -e '.[dev]'
```

Variables principales :

```text
BACKUP_HUB_URL, BACKUP_HUB_TOKEN
LOGSTASH_URL, LOGSTASH_TOKEN
REFERENCE_URL, REFERENCE_TOKEN
BACKUP_COLLECTOR_OUTPUT_DIR, BACKUP_COLLECTOR_LOG_LEVEL
```

Backup Collector ne lit aucune variable de connexion NetBackup et ne stocke aucun mot
de passe NetBackup. Le hostname du master server est fourni avec
`--asset MASTER_SERVER`. Une sortie JSON n'exige aucune URL HTTP.

## Exemples

```bash
backup-collector collect netbackup policies \
  --scope pamela \
  --asset master-emea-01

backup-collector collect netbackup jobs \
  --scope pamela \
  --asset master-emea-01 \
  --hours 24

backup-collector collect netbackup shares \
  --scope elk \
  --asset master-emea-01

backup-collector collect netbackup images \
  --scope elk \
  --asset master-emea-01 \
  --output json

backup-collector collect netbackup baseline \
  --scope baseline \
  --asset master-emea-01 \
  --output json
```

Pour une vérification sans écriture ni envoi, ajouter `--dry-run`. Pour afficher les
événements sur stdout, utiliser `--output stdout`. Les fichiers JSON sont écrits de
façon atomique sous :

```text
$BACKUP_COLLECTOR_OUTPUT_DIR/<scope>/<source>/<data_type>/
```

## Extensions

- **Nouvelle source** : créer une classe avec `collect(data_type, context)`, puis
  l'ajouter à `runtime/registry.py`.
- **Nouveau type de données** : ajouter un petit collecteur au dossier de la source,
  son parser dans le scope et déclarer la combinaison supportée.
- **Nouveau scope** : créer sa classe `execute`, ses fonctions de parsing et son fin
  adaptateur d'output, puis l'inscrire dans `SCOPES`.
- **Nouvel output** : implémenter `send(records, context, metadata)`, puis l'ajouter au
  dictionnaire de `outputs/__init__.py`.
- **Nouveau module externe** : déclarer sa dépendance dans `pyproject.toml`, puis créer
  un adaptateur minimal dans `external/`. Les secrets restent gérés par le module
  externe ou le référentiel, jamais par Backup Collector.

Le connecteur `shares` est une adaptation temporaire documentée : le module `nbu`
actuel ne possède pas encore de service shares, donc il expose pour l'instant les
clients protégés retournés par `client.policies.clients()`.

Baseline contient deux règles d'exemple (`EXAMPLE_*`) afin d'illustrer le workflow ;
elles ne constituent pas encore un référentiel métier de production.

## Icinga

Icinga peut appeler directement la commande installée. Elle produit une seule ligne :

```text
OK - scope=pamela source=netbackup data=policies collected=3200 parsed=3200 sent=3200 duration=42.3s
```

Codes de retour : `0 OK`, `1 WARNING`, `2 CRITICAL`, `3 UNKNOWN`.

## Tests

```bash
python -m pytest
ruff check .
```

Les tests utilisent des doubles du package `nbu` et ne contactent aucun service réel.
