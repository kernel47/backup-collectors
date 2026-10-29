# Contrat des collectes NetBackup

Ce document décrit les données produites par le collecteur et les règles des scripts
du dépôt `backup-index` consulté localement. Ces scripts et les mappings doivent être
installés sur le cluster ; le collecteur ne les crée pas.

## Fonctionnement commun

- `--asset` désigne le hostname recherché via `BACKUP_REFERENCIAL_ASSET_URL`.
  Ce hostname devient `master_server` dans les documents.
- Le parser sélectionne les attributs, convertit les dates et vérifie les champs
  essentiels. Une erreur de parsing prévue rejette le document, pas toute la collecte.
  Une erreur de source API/SSH peut arrêter le parcours ; le dernier lot est alors envoyé.
- `prepare_document()` nettoie les secrets, ajoute les métadonnées et génère l'identité.
- Le `_id` est un UUID déterministe calculé avec le type de collecte, le hostname et
  les attributs d'identité indiqués ci-dessous. Même identité = même `_id`.
  Le namespace UUID est une constante : aucun appel réseau n'est nécessaire au calcul.
- Le collecteur ne vérifie pas l'existence par un GET OpenSearch. Il envoie des lots
  Bulk ; OpenSearch décide de créer, modifier ou ignorer chaque document.
- Lots : 500 documents maximum, 50 pour policies/SLP, avec une limite commune de 10 Mio
  par défaut. Les paramètres `.env` permettent de réduire ces limites, y compris à 1.
- `--dry-run` affiche les documents sans écrire dans OpenSearch. Le rapport distingue
  les documents créés, modifiés, ignorés (`noop`), invalides et les échecs de stockage.

## Jobs — `backup-jobs`

- **Source :** deux fonctions `iter_started_jobs()` et `iter_finished_jobs()`, chacune
  avec un parcours hors VMware et un parcours VMware, soit quatre parcours API. Chaque requête utilise
  un filtre simple `policyType ne 'VMWARE'` ou `policyType eq 'VMWARE'` et une seule
  plage de dates, fixée une fois pour les quatre parcours (bornes incluses).
  Chaque fonction accepte `start_date`/`end_date` ou `hours` et retourne un itérateur
  paginé complet de sa catégorie temporelle. `iter_jobs()` les combine et déduplique.
  Un job commencé avant la période et terminé dedans est donc récupéré. Un job dont
  début et fin sont tous deux dans la période est ignoré lors du parcours `endTime`,
  car déjà traité par le parcours `startTime`, sans mémoriser une liste d’identifiants.
  Un job commencé avant et toujours actif après la période n’est pas sélectionné.
  `--hours 1` sélectionne la dernière heure (24 h par défaut). `iter()` permet
  de traiter progressivement les réponses, sans accumuler toutes les pages.
- **Identité :** `job_id` + `start_time`, en plus du type de collecte et du hostname.
- **Attributs :** identifiants job/parent/backup, type, état, statut, policy, client,
  schedule, stockage, dates, durée, volume, fichiers et progression.
  `data` contient `status_description`.
- **Vérifications essentielles :** `job_id`, `state` et `start_time` présents ; dates
  avec fuseau horaire. L'identifiant numérique est normalisé et les dates sont en UTC.
- **Hash :** aucun.
- **OpenSearch :** script `backup_jobs_upsert`. Création si absent. Sinon, observation
  plus récente, identité et attributs descriptifs compatibles, transitions d'état
  autorisées. Un job `DONE` ne régresse pas ; les corrections de valeurs finales déjà
  connues sont désactivées par défaut. Une entrée incompatible est ignorée (`noop`).

## Images — `backup-images`

- **Source :** parcours API paginé sur la période, sans récupération du contenu SSH.
- **Identité :** `image_id`, en plus du type de collecte et du hostname.
  `copy_number` ne participe pas au `_id` : le contrat actuel garde un document par image.
- **Attributs :** identifiants image/backup, client, policy, types de policy/schedule,
  schedule, niveau de rétention, stockage, dates de sauvegarde/expiration, numéro de
  copie et volume. `data` est actuellement vide.
- **Vérifications essentielles :** `image_id` non vide ; dates présentes converties en UTC.
- **Hash :** aucun.
- **OpenSearch :** script `backup_images_upsert`. Création si absente. Sinon, identité
  identique et observation plus récente ; les valeurs manquantes peuvent être complétées.
  Une modification d'une valeur déjà connue est refusée par défaut pour tout l'envoi
  (`noop`), y compris un changement d'expiration ou de copie.

## Policies — `backup-policies`

- **Source :** liste API → exclusions par type/fragment de nom → détail API → clients SSH.
  Les exclusions se configurent dans `collectors/netbackup/policies.py`.
- **Identité :** `name`, en plus du type de collecte et du hostname.
- **Attributs :** nom, type, activation, SLP, stockage, indicateur SLP et clients.
  `data` reprend ces attributs avec schedules, sélections et rétention ;
  `data.configuration` conserve la réponse brute lorsqu'elle est disponible, nettoyée
  des secrets avant stockage.
- **Vérifications essentielles :** nom non vide, clients sous forme de liste de noms
  non vides ; une liste vide est valide.
- **Configuration :** le parser relit actuellement `raw` avec le parser du module pour
  conserver les valeurs déclarées, puis garde les clients SSH. Il ne conserve donc pas
  les remplacements stockage/rétention effectués par l'enrichissement SLP du module.
- **Hash :** SHA-256 du contenu de `data` nettoyé, hors métadonnées techniques même
  imbriquées. Les clés JSON sont triées ; l'ordre des listes reste significatif.
  Le contenu de `configuration` participe au hash.
- **OpenSearch :** script `backup_configuration_upsert`, décrit ci-dessous.

## SLP — `backup-slps`

- **Source :** liste API puis détail par nom, sans filtre temporel.
- **Identité :** `name`, en plus du type de collecte et du hostname.
- **Attributs :** nom, statut, activation et stockage cible. `data` conserve aussi les
  opérations et la rétention, ainsi que `configuration` si la réponse brute est disponible.
- **Vérification essentielle :** nom non vide.
- **Hash :** même calcul sur `data` que pour les policies.
- **OpenSearch :** script `backup_configuration_upsert` : création si absent ; sinon,
  identité identique et observation plus récente obligatoires. Même hash : seules les
  dates de dernière observation avancent, sans nouvelle version de configuration.
  Hash différent : remplacement de la configuration courante et archivage de la
  précédente dans `history`, limité à `HISTORY_MAX_VERSIONS` (10 par défaut).
  Ce comportement s'applique aussi aux policies.

## Contenus d'images — `backup-images-contents`

- **Éligibilité :** uniquement si `asset.is_naas=true`. Sinon, après résolution de
  l'asset, retour `skipped` avec `reason=asset_not_naas`, sans ouverture des clients
  NetBackup/SSH/OpenSearch. Collection et stockage sont aussi `skipped`, sans erreur,
  avec un code retour 0. L'orchestrateur doit accepter ce statut.
- **Source :** images API sur la période → `get_image_contents(image_id)` en SSH →
  chemins traités progressivement et envoyés par lots, sans attendre toutes les images.
- **Identité :** `image_id` + `path`, en plus du type de collecte et du hostname.
- **Attributs :** `image_id`, `path`, `backup_time`, `master_server`, `region`, `created_at`.
- **Vérifications essentielles :** identifiant et chemin non vides, date de sauvegarde valide.
- **Hash :** aucun.
- **OpenSearch :** opération `create`, sans script. Création si absent ; conflit 409
  compté comme `noop` si déjà présent. Aucun remplacement ni suppression des anciens chemins.

## Recherche et rapports

Les mappings actuels de `backup-index` conservent `data` et `history` sans les indexer
(`enabled: false`) : on peut les récupérer et les afficher via `_source`, mais pas
faire des recherches ou agrégations indexées sur leurs attributs. Les champs explicites
du mapping servent à la recherche ; tout nouvel attribut recherchable doit être prévu
dans le mapping et produit par le collecteur.

Les alias sont obligatoires (`require_alias=true`). Les erreurs de mapping ou de script
comptent comme échecs de stockage. Les erreurs temporaires admissibles sont réessayées
dans une limite configurée. Le rapport final donne `success`, `partial` ou `failed` ;
`--debug` ajoute les détails d'erreur et les mesures temps/CPU/mémoire.
Le statut `skipped` signale une collecte non applicable, sans échec.
