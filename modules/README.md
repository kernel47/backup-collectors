# Modules

Ce dossier centralise les intégrations externes et les modules fonctionnels autonomes.

- `netbackup/` contient la source NetBackup et l'adaptateur vers `netbackup-py` (`nbu`).
- `backup_hub/` contient le transport vers Backup Hub.
- `referential/` contient le transport vers le référentiel.
- `logstash/` contient le transport Logstash.
- `elk/` contient le scope et les parsers ELK.
- `icinga/` contient tous les formats de sortie, codes retour et logs Icinga.

Les packages ne sont pas copiés dans ce dépôt : leurs versions sont déclarées dans
`pyproject.toml`. Une nouvelle intégration doit recevoir son propre sous-dossier ici,
afin que ses imports, sa construction et son comportement ne soient pas dispersés.
