#!/usr/bin/env bash
set -euo pipefail

# Déploiement rapide sur PythonAnywhere pour USERNAME=DrancyInsoumis
# Usage: exécuter dans une Bash console sur PythonAnywhere

USERNAME=DrancyInsoumis
# Sur votre instance PythonAnywhere le repo est directement dans /home/DrancyInsoumis
# Determine project dir: prefer /home/USERNAME/LFIWEB if it exists, otherwise use home
if [ -d "/home/${USERNAME}/LFIWEB" ]; then
  PROJECT_DIR="/home/${USERNAME}/LFIWEB"
else
  PROJECT_DIR="/home/${USERNAME}"
fi
# Detect virtualenv: prefer ~/.venv, fallback to backend/.venv
if [ -d "/home/${USERNAME}/.venv" ]; then
  VENV_PATH="/home/${USERNAME}/.venv"
elif [ -d "${PROJECT_DIR}/backend/.venv" ]; then
  VENV_PATH="${PROJECT_DIR}/backend/.venv"
else
  VENV_PATH=""
fi
WSGI_PATH="/var/www/${USERNAME}_pythonanywhere_com_wsgi.py"

echo "Début du déploiement — projet: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

echo "Récupération du code depuis origin/main"
git fetch --all
git reset --hard origin/main

if [ -d "${VENV_PATH}" ]; then
  if [ -n "${VENV_PATH}" ] && [ -f "${VENV_PATH}/bin/activate" ]; then
    echo "Activation du virtualenv ${VENV_PATH}"
    # shellcheck disable=SC1090
    source "${VENV_PATH}/bin/activate"
  else
    echo "Aucun virtualenv trouvé automatiquement. Créez-en un dans ~/.venv ou backend/.venv, ou modifiez VENV_PATH dans ce script." >&2
  fi
else
  echo "Virtualenv ${VENV_PATH} introuvable — créez-le ou modifiez le script." >&2
fi

echo "Installation des dépendances"
pip install -r backend/requirements.txt || true
pip install requests || true

echo "Exécution des migrations locales (si présentes)"
if [ -f "${PROJECT_DIR}/scripts/migrate_add_video_column.py" ]; then
  python "${PROJECT_DIR}/scripts/migrate_add_video_column.py" --db "${PROJECT_DIR}/data.db" || true
fi

echo "Réglage des permissions sur backend/static"
chmod -R u+rX,go+rX "${PROJECT_DIR}/backend/static" || true

echo "Forcer le reload WSGI (${WSGI_PATH})"
if [ -f "${WSGI_PATH}" ]; then
  touch "${WSGI_PATH}"
  echo "WSGI touch effectué." 
else
  echo "Attention: ${WSGI_PATH} introuvable. Vérifiez le chemin WSGI dans la page Web de PythonAnywhere." >&2
fi

echo "Déploiement terminé. Vérifiez les logs dans l'onglet Web de PythonAnywhere." 
