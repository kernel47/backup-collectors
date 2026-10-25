# Compatibilité et état du test serveur

Le code est préparé pour un premier test sur un serveur réel avec --dry-run.
Les validations réalisées ici utilisent des clients simulés ; elles ne confirment
ni les accès au master, ni les droits ou scripts du cluster OpenSearch distant.

## Code utilisateur à intégrer

Remplacer la classe d'interface dans services/ssh.py par votre implémentation :

- Constructeur SSHClient(host, username, password, port=22, options={}).
- get_policy_clients(policy_name) → list[str] de noms ; [] est une réponse valide.
- get_image_contents(image_id) → itérateur de chemins de répertoires (str).
- close() libère la connexion ; execute(command) peut servir à vos méthodes internes.

Activer ssh dans l'asset Reference et fournir ses informations de connexion. La
connexion est réutilisée pour toutes les policies/images d'une collecte. Une erreur
SSH ne doit jamais être remplacée silencieusement par une liste vide. Les contenus
doivent être produits progressivement, sans précharger une sortie SSH massive.

## Comportement courant des ressources

- Jobs : un seul appel de service paginé, fenêtre fixée au départ ; 24 h par défaut.
  Le scénario à deux appels standard/VMware n'est pas activé, faute de paramètre
  confirmé dans la révision installée. Le dernier échange a conservé l'appel unique.
- Images : API paginée sur la période, 24 h par défaut ; aucune récupération de
  contenu SSH dans cette collecte.
- Policies : résumés API → exclusions dans le code → détail API → clients SSH →
  parser → lots. Liste de clients SSH obligatoire pour les policies retenues.
- SLP : liste puis détail par nom. Un appel unique pourra être retenu après
  confirmation que la liste du master réel contient toutes les opérations requises.
- Images contents : API images de la période → SSH par image → chemins un à un →
  parser → lots create. Aucun document absent d'un parcours n'est supprimé.

Lots : 500 documents / 10 Mio en général, 50 configurations policies/SLP. Les deux
limites sont actives. La taille 1 permet l'envoi immédiat. Le dernier lot est vidé
après une erreur de source ; le rapport reste failed/partial selon les confirmations.

## Contrats externes

Backup Index local a été consulté en lecture seule au commit
769ea41015d031cf16af27d5a13914dd77fe5c0b : mappings, scripts et stratégie d'identité.
Aucun import Python de ce dépôt, aucune modification de ses fichiers.

- Les alias et scripts doivent déjà être installés par Backup Index ; le collecteur
  impose require_alias=true et n'administre pas le cluster.
- Les scripts interdisent created_at/history en entrée pour les quatre ressources
  scriptées ; ces champs ne sont donc pas envoyés. Les contenus suivent leur mapping
  de six champs et initialisent created_at à l'observation.
- Namespace UUID : uuid5(NAMESPACE_URL, "urn:backup-index:documents:v1"). Composants
  sérialisés en tableau JSON UTF-8 compact. Dates de jobs en UTC millisecondes.
  Des anciens documents avec d'autres IDs demandent une migration administrative.
- Une image représente une identité image_id, sans copy_number. Les scripts peuvent
  refuser par noop un changement incompatible de métadonnées de copie.
- Les observations sont datées du présent, même pour une fenêtre historique.
- Paramètres applicatifs : asset, type, hours, start_date, end_date. asset_id et
  resource sont les clés du JSON Tasker existant ; last_hours est exclusivement
  l'argument externe requis par netbackup-py.

Le client Reference existant est conservé. L'URL et les enveloppes acceptées doivent
être confirmées sur le serveur réel. master_server, region, technology et hostname
sont requis ; master_server n'est jamais remplacé par hostname.

## Bibliothèque NetBackup et points à observer

netbackup-py est figé au commit 7296f36862ad25ea2977fff7717b7d95d92757bd.
Jobs/images utilisent iter ; policies.list et slp.list matérialisent leurs listes
internes. Les configurations détaillées de policies ne sont jamais cumulées.

policies.get enrichit storage/retention à partir des SLP. Notre parser réutilise
parse_policy_detail sur raw pour retenir la configuration propre, avec les clients
SSH enrichis. Vérifier les attributs sur une policy réelle avant écriture : le parser
nbu de cette révision gère les schémas imbriqués, mais certaines variantes plates
avec policyAttributes peuvent perdre leurs champs normalisés. Une correction peut
être nécessaire dans netbackup-py pour ces variantes ; le collecteur ne modifie pas
cette bibliothèque. Le payload de configuration reste conservé dans data.

Le hash exclut les métadonnées, même imbriquées. Le normaliseur rejette les identités
absentes et les types incompatibles attendus. Les secrets sont retirés des documents.
Le debug mesure temps/CPU, allocations Python et pic RSS du processus ; le traçage
Python ajoute du coût. Aucun diagnostic HTTP sensible n'est activé.

NetBackupConfig n'accepte qu'un booléen verify_ssl. NETBACKUP_CA_CERT est transmis à
httpx via SSL_CERT_FILE pendant la construction, puis l'environnement est restauré.
Cette adaptation vise une CLI mono-processus, sans création concurrente de clients.

## Vérifications locales

Contrôles via scripts temporaires et affichage, sans réintroduire de suite de tests
permanente : cinq parcours, rapports, dates et exclusions, clients SSH simulés,
lots/unitaires, erreurs source/stockage, reprises et codes retour. Les contrôles
streaming vérifient que le premier lot part avant la fin de la source et que la
progression reste bornée par le lot. Ruff et construction du package complètent ces
contrôles. Les accès serveur et l'exécution réelle des scripts restent à vérifier
au déploiement.
