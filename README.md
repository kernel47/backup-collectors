# Backup Collector

CLI ponctuelle lancée par Tasker : collecte → vérification/parsing → envoi progressif
OpenSearch → rapport final. Aucun scheduler ni service permanent. Backup Index reste
responsable des mappings, alias, scripts et purges ; il n'est pas une dépendance Python.

## Utilisation

```bash
backup-collector collect --scope netbackup --type jobs --asset master-01
backup-collector collect --scope netbackup --type jobs --asset master-01 --hours 5
backup-collector collect --scope netbackup --type images --asset master-01 \
  --start-date 2026-10-20T00:00:00Z --end-date 2026-10-21T00:00:00Z
backup-collector collect --scope netbackup --type policies --asset master-01
backup-collector collect --scope netbackup --type slps --asset master-01
```

Paramètres de base : --scope, --type, --asset, --dry-run et --debug. Jobs, images et contenus d’images
acceptent --hours (24 heures par défaut), ou --start-date et --end-date ensemble.
Policies et SLP n'ont aucun paramètre temporel et représentent l'état actuel.
Les dossiers datadomain/tapelibrary sont réservés. Leur exécution échoue explicitement.
La séquence images-contents est branchée ; son transport attend votre méthode SSH
get_image_contents(image_id).

Pour vérifier les documents sans écriture :

```bash
backup-collector collect --scope netbackup --type jobs --asset master-01 --dry-run --debug
backup-collector collect --scope netbackup --type policies --asset master-01 --dry-run > /tmp/policies.jsonl
```

Dry-run fait une vraie collecte : il nécessite Reference et NetBackup. Il affiche un
JSON par document sur stdout, sans créer de client OpenSearch ; diagnostics et rapport
final vont sur stderr. En mode normal, stdout contient uniquement le rapport Tasker.
Aucun paramètre de fixture, input-file, output-file ou ancien alias CLI n'est accepté.

## Structure

```text
cli.py                       # arguments et sérialisation du rapport
core/
├── models.py                # Asset, CollectionContext, Settings et CollectionReport
├── collection.py            # CollectionRun : petites opérations d'exécution réutilisables
├── exceptions.py
└── runtime.py               # routage vers la collecte demandée
collectors/
├── netbackup/
│   ├── __init__.py          # expose les cinq fonctions de collecte
│   ├── client.py            # initialisation API/SSH, adaptation des dates nbu
│   ├── parser.py            # sélection explicite des attributs de chaque objet
│   ├── jobs.py
│   ├── policies.py
│   ├── images.py
│   ├── images_contents.py
│   └── slps.py
├── datadomain/              # réservé
└── tapelibrary/             # réservé
services/
├── opensearch.py            # transport Bulk, limites et reprises
├── referential.py           # client Reference existant
├── documents.py             # UUID, dates de collecte, validation et hash
└── ssh.py                   # interface en attente de votre classe SSH
```

## Une courte séquence par collecte

Les paramètres sont réunis dans CollectionContext, et les options techniques dans
Settings. Chaque fichier garde sa source et sa séquence explicite, sans recopier
la gestion des connexions, erreurs et compteurs :

```python
def collect_policies(context, settings=None):
    run = CollectionRun(context, settings)
    with run:
        run.prepare()
        run.resolve_asset()
        run.open_clients(client)
        run.open_output(configuration=True)
        for record in iter_policies(run.api_client, run.ssh_client):
            run.process(record, parser=parse_policy)
            del record
        run.completed = True
    return run.report
```

CollectionRun fournit de petites méthodes distinctes : préparation, résolution,
ouverture des clients/sortie, parsing et validation, envoi, vidange et fermeture.
process() compte un objet, appelle le parser explicitement fourni puis send().
Chaque collecte sélectionne son parser dans collectors/netbackup/parser.py.
La vérification technique du document est faite après la sélection des attributs ; les erreurs de document sont comptées sans arrêter les suivants.
Le contexte ferme les connexions et vide le dernier lot même après une erreur source.
Il ne contient ni liste de résultats ni registre dynamique.

Pour les policies, iter_policies() lit les résumés puis récupère les détails de chaque
policy : schedules, sélections et configuration. Il enrichit ensuite policy.clients
avec ssh_client.get_policy_clients(policy.name). Le parser du connector réutilise le parser public nbu sur la réponse originale
pour éviter de hasher les informations dérivées des SLP.
Modifier cette source ou appeler run.process(record, parser=...) se fait dans policies.py.

Exemple Python :

```python
from collectors.netbackup import collect_jobs
from core.models import CollectionContext

context = CollectionContext(type="jobs", asset="master-01", hours=5, dry_run=True)
report = collect_jobs(context)
print(report.to_dict())
```

Les cinq points d'entrée collect_jobs, collect_images, collect_policies, collect_slps,
collect_images_contents ont tous la même signature (context, settings=None). Ils
retournent CollectionReport, sans liste des documents. Le contexte valide les périodes
pour les appels Python comme pour la CLI.

## Rapport stable dans les modèles

CollectionReport est défini dans core/models.py, avec CollectionStats et StorageStats.
Il porte le contrat Tasker schema_version=1.0 : collection_id, status, asset_id,
master_server, region, technology, resource, collection, storage, duration_seconds,
errors. Les compteurs sont des attributs typés, pas des dictionnaires manipulés dans
chaque script. to_dict() est l'unique sérialisation JSON et exit_code expose 0 success,
1 failed, 2 partial. finish() calcule les statuts au même endroit pour toutes les collectes.

Les écritures confirmées proviennent des résultats Bulk. Le dry-run ajoute displayed
sans inventer des créations OpenSearch. Une collecte vide terminée normalement réussit ;
une erreur avec des documents confirmés donne partial ; sans document confirmé, failed.
Les erreurs sont limitées à vingt et les messages des exceptions externes ne sont pas
recopiés. Les secrets ne sont pas inclus dans le rapport.

Les paramètres applicatifs utilisent asset/type/hours/start_date/end_date. asset_id et
resource restent uniquement les clés des contrats externes Tasker/Reference. last_hours
est uniquement le nom requis par netbackup-py à la frontière de l'adaptateur. Les champs
métier start_time/end_time des documents OpenSearch conservent leur nom contractuel.

## Lots, mémoire et debug

Un objet est récupéré, vérifié/normalisé, puis ajouté au lot avant de demander le suivant.
Jobs et images passent par les itérateurs paginés nbu. Le rapport ne conserve que les
compteurs et quelques erreurs. Le tampon Bulk garde les corps sérialisés, pas une
seconde copie complète de tous les objets. La mémoire dépend du lot, de la page source
et de l'objet courant, pas du nombre total de résultats. Policies.list/slp.list restent
des listes internes à la bibliothèque ; les détails de policies ne sont pas cumulés.
Le transport SSH des contenus doit lui aussi exposer un itérateur de chemins.

- OPENSEARCH_BATCH_SIZE=500 : plafond général ; 1 pour envoyer chaque document.
- OPENSEARCH_CONFIGURATION_BATCH_SIZE=50 : policies/SLP, plafonné par la limite générale ;
  1 pour envoyer chaque configuration immédiatement.
- OPENSEARCH_MAX_BATCH_MB=10 : limite en octets, active pour tous les lots.

Chaque résultat Bulk est vérifié ; erreurs réseau/timeouts et 429/500/502/503/504 ont des
reprises bornées avec les mêmes UUID et backoff. Les erreurs de mapping, scripts/index
absents et conflits update restent des échecs. Une écriture non confirmée n'est jamais
comptée comme succès. Le compte worker n'a besoin d'aucun droit d'administration.

--debug trace sur stderr les étapes, la progression, les tailles de lots et les reprises,
sans afficher de credentials, d'options SSH ni de payloads bruts. Les traces HTTP des
bibliothèques ne sont pas activées.

## Installation et configuration

Python 3.12+ dans un venv, sur macOS ou RHEL, sans modifier le Python système :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
# Compléter .env avec les valeurs réelles, puis exporter :
set -a
source .env
set +a
backup-collector collect --help
ruff check --no-cache .
```

En production, installer avec pip install . depuis une révision validée et faire lancer
par Tasker l'exécutable absolu du venv. Pour mettre à jour, préparer un nouveau venv,
contrôler par dry-run puis basculer le chemin worker en conservant le précédent.
.env n'est pas chargé automatiquement et n'est pas versionné. Les dépendances sont
centralisées dans pyproject.toml ; netbackup-py est figé au commit
7296f36862ad25ea2977fff7717b7d95d92757bd. L'installation nécessite l'accès SSH GitHub ou
un packaging interne fournissant cette révision et adaptant sa référence VCS. Un miroir
Bitbucket du seul collecteur ne suffit pas pour cette dépendance.

Le client Reference existant est conservé. BACKUP_REFERENCE_URL contient l'URL réelle
avec {asset_id} ou {hostname}, sinon la clé est ajoutée au chemin comme auparavant.
REFERENTIAL_ASSET_URL et REFERENTIAL_TOKEN restent des alias d'environnement compatibles.
La réponse doit fournir hostname, master_server, region et technology=netbackup ;
master_server n'est jamais déduit du hostname. Voir .env.example et docs/compatibility.md.

TLS est vérifié par défaut. OPENSEARCH_CA_CERT fournit un bundle PEM OpenSearch.
NETBACKUP_CA_CERT passe par SSL_CERT_FILE pendant la construction du client puis restaure
l'environnement. SSL_CERT_FILE peut aussi configurer Reference. Aucune erreur TLS ne
désactive automatiquement les vérifications.

Le client SSH est construit via services.ssh.SSHClient(host, username, password, port,
options), depuis les informations Reference. La classe actuelle expose execute(command), get_policy_clients(policy_name)
et close(), sans transport actif. Elle attend votre implémentation ; Paramiko n'est pas
une dépendance provisoire.

## Contrat des documents

Alias : backup-jobs, backup-images, backup-policies, backup-slps, backup-images-contents.
Bulk impose require_alias=true ; aucun index, alias, mapping ou script n'est administré.
Les scripts configurables backup_jobs_upsert, backup_images_upsert et
backup_configuration_upsert reçoivent document, et pour les configurations kind et
max_history_versions. Ils gèrent created_at, history, les mises à jour et la non-régression.
Le collecteur ne lit pas les documents existants. Les contenus utilisent create pour
préserver les chemins déjà enregistrés.

Les UUID v5 utilisent le namespace uuid5(NAMESPACE_URL, "urn:backup-index:documents:v1")
et un tableau JSON compact de chaînes : kind/master_server puis name (policy/SLP),
job_id/start_time (job), image_id (image), image_id/path (contenu). Les dates sont UTC à
la milliseconde ; casse et caractères sont préservés ; copy_number n'identifie pas une
image. Le SHA-256 de configuration utilise un JSON canonique avec ordre des listes
conservé. Les observations sont datées du présent, indépendamment de la fenêtre métier.
Les limites restantes du normaliseur et des variantes NetBackup sont documentées dans
docs/compatibility.md.


## Mesures de performance en debug

--debug ajoute un bilan sur stderr et un objet performance au rapport final :

- duration_seconds : durée réelle de la collecte, résolution, écritures/reprises et
  fermeture des connexions comprises.
- cpu_user_seconds / cpu_system_seconds / cpu_total_seconds : temps CPU consommé par
  le processus pendant cette exécution, en secondes.
- cpu_average_percent : CPU total divisé par la durée réelle, avec 100 % correspondant
  à un cœur pleinement occupé ; plusieurs threads peuvent dépasser 100 %.
- python_peak_bytes : pic d'allocations Python suivies pendant la collecte via
  tracemalloc. Les allocations antérieures et certaines mémoires natives sont exclues.
- process_peak_rss_bytes : pic de mémoire résidente totale du processus depuis son
  démarrage, mesuré par getrusage. Ce n'est ni la mémoire supplémentaire de la collecte,
  ni la somme des pics de ses différentes étapes.

Toutes les mémoires du JSON sont en octets ; le log les affiche en MiB. Les mesures
CPU concernent le processus, sans ses sous-processus. Le profilage est activé uniquement
en debug et ajoute un surcoût, notamment tracemalloc. Si un appelant Python a déjà
activé tracemalloc, son traçage est préservé et python_peak_bytes vaut null pour ne pas
attribuer un pic extérieur à la collecte. Les mesures sont également produites après
un échec de collecte. En mode normal, le champ performance est absent.


## Parsers propres à NetBackup

Chaque fonction prend un seul objet NetBackup et retourne un dictionnaire d'attributs :
parse_policy(policy), parse_job(job), parse_image(image), parse_slp(slp),
parse_image_content(content). Les attributs sont écrits explicitement dans chaque
fonction, sans fonction générique de sélection de champs ni registre de schémas.

```python
attributes = parse_job(job)
# {"job_id": ..., "state": ..., "client": ..., "start_time": ..., ...}
```

Les parsers n'ont besoin ni de l'asset ni de l'heure de collecte. La préparation
technique du document (UUID, métadonnées, validation des types/dates, hash) reste
séparée dans services/documents.py. Elle produit le ParsedDocument utilisé par la
sortie. Les clients enrichis des policies et les configurations propres sont conservés.


## Mesures en debug

--debug ajoute performance au rapport : temps CPU utilisateur/système/total,
pourcentage CPU moyen (100 % = un cœur), pic d'allocations Python pendant la collecte
et pic RSS du processus depuis son démarrage. Les mémoires JSON sont en octets,
les logs en MiB ; duration_seconds reste la durée réelle. Ces mesures concernent le
processus, sans sous-processus, et le traçage Python a un surcoût. Un tracemalloc déjà
actif chez l'appelant est préservé et le pic Python de la collecte vaut alors null.
Hors debug, performance est absent. Le bilan est disponible aussi après un échec.


## Séquence des policies et clients SSH

1. policies.list(include_details=False) récupère les résumés.
2. policies.get(name) récupère le détail d'une policy.
3. ssh_client.get_policy_clients(name) récupère ses clients et remplit policy.clients.
4. parse_policy(policy) sélectionne les attributs ; le document rejoint le lot Bulk.

Cette séquence est exécutée policy par policy, avec la même connexion SSH. Le contrat
local get_policy_clients est une liste de noms de clients (list[str]) ; une liste vide
est valide, mais None, un échec ou une sortie non parsée ne remplace pas les clients
par une liste vide. SSH doit être activé dans l'asset Reference. Votre classe doit
remplacer l'emplacement get_policy_clients dans services/ssh.py ; aucune commande ou
syntaxe de sortie n'est inventée ici. Un échec arrête la source et le dernier lot de
policies déjà complètes est envoyé ; le rapport est partial s'il y a des écritures
confirmées. La policy dont les clients n'ont pas été récupérés n'est pas envoyée.


## Exclusions de policies dans le code

Modifier directement les deux listes en tête de collectors/netbackup/policies.py :

```python
EXCLUDE_TYPES = ["VMware", "Standard"]
EXCLUDE_NAMES = ["test", "ancienne"]
```

Les listes sont vides par défaut. Le type est comparé exactement, sans distinction
de casse. Chaque nom exclu est un fragment recherché dans le nom complet de la policy,
également sans distinction de casse. Une correspondance de type OU de nom suffit.
Les fragments vides sont ignorés. Aucune option CLI n'est ajoutée.

L'exclusion utilise les résumés de la liste API et intervient avant policies.get et
get_policy_clients : aucun appel de détail ni SSH pour les policies ignorées. Le
rapport collection.excluded les compte séparément ; collected représente les policies
complètes effectivement traitées. Exclure toutes les policies reste une collecte
vide réussie, si les étapes requises sont disponibles.


## Collecte des contenus d'images

```bash
backup-collector collect --scope netbackup --type images-contents --asset master-01 \
  --hours 24 --dry-run --debug
```

Cette collecte est indépendante de images, qui conserve son fonctionnement de collecte
des métadonnées. images-contents suit l'itérateur API des images de la période, puis
appelle ssh_client.get_image_contents(image.image_id) pour chaque image. Le contrat
local proposé pour cette méthode est un itérateur de chemins de répertoires (str),
sans préchargement de tous les chemins. La classe SSH doit implémenter cette méthode ;
aucune commande ni format brut SSH n'est présumé.

Pour chaque chemin, le collecteur associe image_id et backup_time de l'image API,
appelle parse_image_content, puis ajoute le document au Bulk borné. Il n'attend pas la
fin de toutes les images pour envoyer les premiers lots ; un lot peut contenir des
chemins de plusieurs images. La limite générale de 500 documents / 10 Mio s'applique,
ou un envoi unitaire si OPENSEARCH_BATCH_SIZE=1. Le dernier lot est envoyé même après
une erreur source. Les chemins déjà écrits ne sont jamais supprimés si un parcours
est incomplet. Le compteur collected désigne ici le nombre de chemins traités.
