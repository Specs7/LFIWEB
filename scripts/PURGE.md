# Purge content helper

Le script `purge_content.py` dans ce dossier permet de sauvegarder puis purger
les contenus suivants de l'application :

- tables SQLite : `articles`, `photos`, `videos`
- fichiers d'uploads : `backend/static/uploads/photos/*` et `backend/static/uploads/videos/*`

Usage recommandé :

1. Depuis la racine du projet, exécutez le script en mode backup + confirmation interactive :

```bash
python3 scripts/purge_content.py --backup
```

2. Pour lancer sans prompt (danger : destructif) :

```bash
python3 scripts/purge_content.py --backup --yes
```

Options :

- `--db PATH` : spécifier la base SQLite si elle n'est pas à `./data.db`. Par exemple sur PythonAnywhere :
  `--db /home/USERNAME/LFIWEB/data.db`
- `--dry-run` : afficher ce que ferait le script sans modifier quoi que ce soit.
- `--backup` : créer une copie de la base et une archive des uploads avant purge.
- `--yes` : ne pas demander de confirmation interactive.

Sécurité : le script est destructif. Conservez les sauvegardes créées (`data.db.bak.*` et `uploads-backup-*.tgz`) avant de les supprimer définitivement.

Restauration rapide :

- pour restaurer la DB : `cp data.db.bak.YYYYMMDD_HHMMSS data.db`
- pour restaurer les uploads : décompressez l'archive `tar xzf uploads-backup-YYYYMMDD_HHMMSS.tgz` et replacez les dossiers `photos`/`videos` dans `backend/static/uploads/`.

Si vous préférez, vous pouvez aussi lancer le script sur le serveur de production (PythonAnywhere) en adaptant le chemin de la DB et en prenant des précautions horaires.

---
Fichier généré automatiquement par l'assistant pour faciliter les opérations de purge.
