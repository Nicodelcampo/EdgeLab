#!/usr/bin/env bash
# Instala la credencial de Kaggle para el usuario `edgelab` SOLO para www.kaggle.com (curl --netrc), sin tocar otros hosts (las URL firmadas de GCS no la reciben).
# Uso (como root):  KAGGLE_USERNAME=... KAGGLE_KEY=... ./setup_kaggle_credentials.sh      (la clave se obtiene en kaggle.com → Settings → API → Create New Token)
set -euo pipefail
: "${KAGGLE_USERNAME:?}" "${KAGGLE_KEY:?}"
H=/opt/edgelab
printf 'machine www.kaggle.com login %s password %s\n' "$KAGGLE_USERNAME" "$KAGGLE_KEY" > $H/.netrc
printf 'netrc\n' > $H/.curlrc
chown edgelab:edgelab $H/.netrc $H/.curlrc; chmod 600 $H/.netrc $H/.curlrc
echo "Credencial instalada para el usuario edgelab (solo www.kaggle.com)."
