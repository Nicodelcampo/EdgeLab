"""Autenticación de curl contra la API de Kaggle, para los dos formatos de credencial.

- Token nuevo (KGAT_...): sólo funciona como `Authorization: Bearer` (verificado 2026-10-16: con usuario/clave da 401).
  Se guarda en un archivo de cabecera 0600 y se pasa con `-H @archivo`, así el token no aparece en la lista de procesos.
  Desde curl 7.83 (CVE-2022-27776) esa cabecera no se reenvía a otro host al seguir redirecciones: las URL firmadas
  de descarga no la reciben.
- Clave vieja: `~/.netrc` sólo para www.kaggle.com (lo que ya hacía setup_kaggle_credentials.sh).
"""
import os
from pathlib import Path


def header_file():
    p = Path(os.environ.get("KAGGLE_AUTH_HEADER_FILE", Path.home() / ".kaggle_auth_header"))
    return p if p.is_file() else None


def curl_auth(url):
    """Argumentos extra de curl para una URL. Nada para hosts que no sean la API de Kaggle."""
    if not str(url).startswith(("https://www.kaggle.com/", "https://api.kaggle.com/")):
        return []
    h = header_file()
    return ["-H", f"@{h}"] if h else []
