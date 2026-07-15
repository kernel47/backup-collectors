# Modules

Ce dossier centralise les services techniques partagés par les scopes.

- `netbackup/` contient la source NetBackup et l'adaptateur vers `netbackup-py` (`nbu`).
- `datadomain/` et `tapelibrary/` réservent la place des prochaines intégrations.
- `icinga/` contient tous les formats de sortie, codes retour et logs Icinga.
- `output/` contient le service de livraison unique. Il sélectionne Backup Hub,
  Logstash, Referential, un fichier JSON ou stdout selon les paramètres d'exécution.

Les parsers métier ne sont pas placés ici : ils restent dans `scopes/`. Le scope
`logstash` prépare les événements, puis Logstash est responsable de les envoyer vers
ELK.

Les packages ne sont pas copiés dans ce dépôt : leurs versions sont déclarées dans
`pyproject.toml`. Une nouvelle intégration doit recevoir son propre sous-dossier ici,
afin que ses imports, sa construction et son comportement ne soient pas dispersés.
