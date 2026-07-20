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
  -> services/netbackup.py, datadomain.py ou tapelibrary.py
  -> collectors/<scope>/parser.py
  -> services/output.py route vers file_output, http_output ou logstash_output
  -> services/icinga.py pour la progression, les logs et le rapport
  -> Backup Hub, Logstash, Referential, fichier ou stdout
```

Il n'existe ni registre dynamique, ni découverte automatique, ni classe par petit
composant. `runtime.py` contient uniquement les branchements lisibles qui sélectionnent
le scope. Chaque scope reste autonome pour ses collectes, son traitement et sa sortie.

## Structure

```text
collectors/
├── pamela/
│   ├── collector.py         # séquence policies -> clients -> jobs
│   └── parser.py            # traitement et filtres Pamela
├── logstash/
│   ├── collector.py         # séquence jobs -> policies -> images
│   └── parser.py            # format des événements Logstash
└── baseline/
    ├── collector.py         # séquence propre à chaque source
    └── parser.py            # règles Baseline

services/
├── netbackup.py        # clients API nbu et SSH NetBackup
├── ssh.py              # client SSH générique et exécution de commande
├── datadomain.py       # futur accès Data Domain
├── tapelibrary.py      # futur accès Tape Library
├── referential.py      # recherche d'un asset à partir de son hostname
├── record_filters.py   # filtres génériques par nom, type et date
├── output.py           # routeur léger des destinations
├── file_output.py      # écriture JSON atomique
├── http_output.py      # POST JSON générique
├── logstash_output.py  # envoi vers l'input HTTP Logstash
└── icinga.py           # progression, logs, rapport et codes retour Icinga
```

Il n'existe plus de dossiers racine `parsers/` ou `modules/`. Un parser appartient à
son scope, et une intégration externe appartient aux services.

Les fichiers racine restent simples :

- `cli.py` définit les arguments, crée le contexte et lance la commande ;
- `runtime.py` résout l'asset et appelle explicitement le collecteur du scope ;
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

`services/netbackup.py` expose deux clients à partir du même objet :

```python
from services.netbackup import create_api_client, create_ssh_client
from services.ssh import run

api_client = create_api_client(asset)
ssh_client = create_ssh_client(asset)
exit_code, stdout, stderr = run(ssh_client, "hostname")
ssh_client.close()
```

Le client API utilise `api_username` et `api_password`. Le client SSH utilise
`ssh_username` et `ssh_password`. Par sécurité, le serveur SSH doit déjà être présent
dans les clés hôtes connues de la machine qui exécute la collecte.

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
  --hours 24 \
  --policy-type Standard \
  --policy-name 'PROD-*'

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

`--policy-type` et `--policy-name` sont répétables. Les noms acceptent les patterns
`*`, `?` et `[]`. Un nom exact est également envoyé à l'API NetBackup pour limiter le
volume récupéré. Les jobs sont filtrés pendant le fetch puis à nouveau dans le parser
avec `--start-time`, `--end-time`, `--hours` ou `--days`.

Pour ajouter ou modifier un besoin futur propre à Pamela, Baseline ou Logstash, les
changements restent dans le dossier du scope concerné. Les services ne changent que si
l'accès à une source ou à une destination évolue.

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

Les sorties sont indépendantes et réutilisables :

- `file_output.py` écrit un document JSON atomiquement ;
- `http_output.py` envoie un payload JSON vers une API HTTP ;
- `logstash_output.py` envoie une collection vers l'input HTTP Logstash.

`--output file` écrit sous :

```text
$BACKUP_COLLECTOR_OUTPUT_DIR/<scope>/<source>/<data_type>/
```

## Icinga

Chaque scope utilise `services/icinga.py` pour afficher sa progression et écrire un log
après chaque type de données. Ce service reste le seul fichier à modifier pour changer
les messages, le rapport ou les codes retour : `0 OK`, `1 WARNING`, `2 CRITICAL`,
`3 UNKNOWN`.

Chaque type collecté et chaque scope terminé écrivent un log `INFO` avec le statut et
les totaux collectés, parsés et envoyés. Le rapport final contient également la durée.
Pour afficher les logs :

```bash
export BACKUP_COLLECTOR_LOG_LEVEL=INFO
```

## Test smoke

```bash
python -m pytest
ruff check .
```

Les tests n'effectuent aucun appel réel vers NetBackup ou une destination HTTP.
Il reste volontairement un seul test CLI pour valider le chargement général du module,
les paramètres principaux et le rapport final.
