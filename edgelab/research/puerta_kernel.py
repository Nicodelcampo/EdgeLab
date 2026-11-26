"""Exit-gate estatico y sintetico para kernels antes de enviarse a Kaggle.

Impide subir codigo que no compile, que toque el dataset sellado/holdout,
que filtre secretos o rutas locales, o que lea datos sin guarda de holdout.
"""
from __future__ import annotations

import ast
import importlib
import re
from typing import Any

from edgelab.autopilot.roles import SECRET

_DATA_RX = re.compile(
    r"(read_parquet|read_csv|/kaggle/input|fuentes_ticks|edgelab\.research|duckdb|polars|\bpandas\b|\bpd\.)",
    re.M,
)
_SELLADO_RX = re.compile(r"edgelab-holdout-sellado", re.I)
_HOLDOUT_GUARD_RX = re.compile(
    r"(edgelab\.holdout|holdout_guard|HOLDOUT_PRIMERA_SESION|HOLDOUT_FIRST_TRADE_DATE|edgelab_data|#\s*Kernel generado por)",
    re.M,
)
_PREREG_REF_RX = re.compile(
    r"(PREREGISTRO|campaign_id|EDGELAB_LAUNCH_MANIFEST|\bFAMILIA\b|\bMODULO\b|#\s*Kernel generado por)",
    re.M,
)
_LOCAL_ABS_RX = re.compile(r"(^|[\s'\"])(/(etc|home|var|root)/|[A-Za-z]:\\\\?Users\\\\?)", re.M)
_POST_OCT_DATE_RX = re.compile(r"(2026-(?:10|11|12)-\d{2}|2026(?:10|11|12)\d{2})")


def _contiene_llamada_allow_sellado_true(tree: ast.AST) -> bool:
    """Detecta llamadas o asignaciones reales `allow_sellado=True`, incluso dentro de `compile('...', ...)`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if (
                isinstance(node.value, ast.Constant)
                and node.value.value is True
                and any(isinstance(t, ast.Name) and t.id == "allow_sellado" for t in node.targets)
            ):
                return True
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "allow_sellado" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    return True
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "compile"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                try:
                    sub = ast.parse(node.args[0].value)
                    if _contiene_llamada_allow_sellado_true(sub):
                        return True
                except SyntaxError:
                    pass
    return False


def es_kernel_de_datos(script_text: str) -> bool:
    """True si el script carga datos de mercado o ejecuta logica cuantitativa de research."""
    return bool(_DATA_RX.search(script_text or ""))


def validar_script_kernel(script_text: str, *, require_canonical: bool = False) -> list[str]:
    """Valida sintaxis, firewall de holdout, secretos y contratos antes de push_kernel."""
    errs: list[str] = []
    txt = str(script_text or "")
    try:
        tree = ast.parse(txt)
    except SyntaxError as exc:
        return [f"error de sintaxis Python (linea {exc.lineno}): {exc.msg}"]

    if _SELLADO_RX.search(txt) or _contiene_llamada_allow_sellado_true(tree):
        errs.append("firewall HOLDOUT-A4: referencia al dataset sellado o allow_sellado=True prohibida en push_kernel")
    if SECRET.search(txt):
        errs.append("seguridad: posible credencial/secreto detectado en el script del kernel")
    if _LOCAL_ABS_RX.search(txt):
        errs.append("portabilidad/seguridad: ruta absoluta local prohibida dentro de un kernel Kaggle")

    necesita_canonico = require_canonical or es_kernel_de_datos(txt)
    if necesita_canonico:
        tiene_holdout = bool(_HOLDOUT_GUARD_RX.search(txt))
        if not tiene_holdout:
            errs.append(
                "puerta_kernel: script de datos sin guarda de holdout "
                "(importar `edgelab.holdout` / `edgelab_data` o usar kernel generado canonico)"
            )
        if not _PREREG_REF_RX.search(txt):
            errs.append(
                "puerta_kernel: falta identificador de pre-registro/campana "
                "(`PREREGISTRO`, `campaign_id`, `MODULO` o kernel canonico)"
            )
        if _POST_OCT_DATE_RX.search(txt) and not tiene_holdout:
            errs.append("puerta_kernel: fecha >= 2026-10-01 sin guarda de holdout")
    return errs


def validar_modulo_sintetico(modulo: str) -> list[str]:
    """Corre preflight estatico y sintetico del modulo usando los canales canonicos."""
    mod = importlib.import_module(modulo)
    if callable(getattr(mod, "eventos", None)):
        from edgelab.research import tablas as TB

        return TB.preflight(modulo, dias=20, kernel=False)
    if callable(getattr(mod, "disparos", None)):
        from edgelab.research import preflight as PF

        rep: dict[str, Any] = PF.verificar_experimento(modulo, dinamico_tambien=True)
        return [] if rep.get("ok") else list(rep.get("errores") or ["preflight fallo"])
    return [f"{modulo} no expone `eventos(ctx)` ni `disparos(ctx)`"]
