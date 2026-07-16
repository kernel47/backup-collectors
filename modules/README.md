# Modules

Chaque intégration technique tient dans un fichier :

- `netbackup.py` collecte avec `netbackup-py` (`nbu`) ;
- `datadomain.py` réserve la future collecte Data Domain ;
- `tapelibrary.py` réserve la future collecte Tape Library ;
- `output.py` sélectionne et exécute l'envoi HTTP, fichier ou stdout ;
- `icinga.py` gère les messages, logs et codes retour Icinga.

Pour ajouter une source, créer un fichier ici puis ajouter une branche explicite dans
`runtime.py`. Pour ajouter une destination, compléter les branches de `output.py`.
