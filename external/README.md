# External modules

Ce dossier centralise les adaptateurs très fins vers les packages Python externes.

- `netbackup.py` adapte `netbackup-py` au collecteur.
- Backup Collector lui transmet uniquement le hostname du master server.
- La recherche de la configuration, des identifiants et des secrets reste entièrement
  sous la responsabilité de `netbackup-py`.

Les packages ne sont pas copiés dans ce dépôt : leurs versions sont déclarées dans
`pyproject.toml`. Un nouvel outil externe doit recevoir ici un adaptateur minimal afin
que ses imports et sa construction ne soient pas dispersés dans le projet.
