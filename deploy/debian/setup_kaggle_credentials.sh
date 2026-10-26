#!/usr/bin/env bash
# Instala la credencial de Kaggle para el usuario `edgelab`. Nunca la envía a otro host que www.kaggle.com.
# Uso (como root), según el formato del token de kaggle.com → Settings → API:
#   token nuevo (KGAT_...):  KAGGLE_API_TOKEN=... ./setup_kaggle_credentials.sh
#       -> cabecera Bearer en /opt/edgelab/.kaggle_auth_header (0600), que lee tools/kaggle_auth.py.
#          Con el token nuevo el usuario/clave por .netrc da 401 (verificado 2026-10-16).
#   clave vieja:             KAGGLE_USERNAME=... KAGGLE_KEY=... ./setup_kaggle_credentials.sh
#       -> ~/.netrc sólo para www.kaggle.com.
# Para no dejar el token en el historial:  read -rs KAGGLE_API_TOKEN && export KAGGLE_API_TOKEN && ./setup_kaggle_credentials.sh
set -euo pipefail
H=/opt/edgelab
umask 077
# Segunda cuenta (2026-10-26, reparto entre cuentas): KAGGLE_CUENTA=nicobuttaro KAGGLE_API_TOKEN=... ./setup_kaggle_credentials.sh
#   -> /opt/edgelab/.kaggle_auth_header.nicobuttaro, que tools/kaggle_auth.py usa cuando el kernel es de esa cuenta.
if [ -n "${KAGGLE_API_TOKEN:-}" ]; then
  F="$H/.kaggle_auth_header${KAGGLE_CUENTA:+.$KAGGLE_CUENTA}"
  printf 'Authorization: Bearer %s\n' "$KAGGLE_API_TOKEN" > "$F"
  chown edgelab:edgelab "$F"; chmod 600 "$F"
  rm -f "$H/.curlrc"
  echo "Token Bearer instalado para el usuario edgelab (sólo se envía a www.kaggle.com)."
else
  : "${KAGGLE_USERNAME:?falta KAGGLE_API_TOKEN o KAGGLE_USERNAME/KAGGLE_KEY}" "${KAGGLE_KEY:?}"
  printf 'machine www.kaggle.com login %s password %s\n' "$KAGGLE_USERNAME" "$KAGGLE_KEY" > "$H/.netrc"
  printf 'netrc\n' > "$H/.curlrc"
  chown edgelab:edgelab "$H/.netrc" "$H/.curlrc"; chmod 600 "$H/.netrc" "$H/.curlrc"
  echo "Credencial instalada para el usuario edgelab (solo www.kaggle.com)."
fi
