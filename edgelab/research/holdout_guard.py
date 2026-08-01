"""Firewall del holdout — guard único y centralizado (FASE 3b).

Referente: `docs/NORTH_STAR.md` + `docs/edge_validation_contract.md` §G4.
Toda función de carga de datos para research económico de estrategias (P&L,
retornos, selección de candidatos) debe llamar a `check_holdout(...)` ANTES de
tocar cualquier rango de fechas.

Única fuente de verdad de la fecha de corte: `HOLDOUT_START_ISO` abajo,
citada textualmente de `docs/NORTH_STAR.md` ("Holdout sellado: 2026-07-01 →
2026-12-31") y `docs/edge_validation_contract.md` §G4.

AVISO (2026-08-01): existe una SEGUNDA definición de la fecha en código,
`tools/censo_es_nq.py:91` (`HOLDOUT_DESDE = "2026-07-01"`, hardcodeada). Hoy
coincide con el sello, así que no hay conflicto activo, pero la afirmación
anterior de este docstring ("ningún otro archivo define esta fecha") era
falsa. Unificarla es trabajo pendiente y se decide con Nico; mientras tanto
queda declarada acá para que nadie la vuelva a dar por inexistente.

## LA FRONTERA ES UN SELLO, NO UN CURSOR (regla 95)

INC-006: el 2026-08-01 03:16 un commit etiquetado `chore` movió la frontera de
2026-07-01 a 2026-08-01. Eso no "reparticiona" nada: **des-sella** el mes de
julio, que estaba protegido. Y el daño no fue inmediato — la frontera quedó
apuntando al futuro y **venció sola** cuando el reloj cruzó el 2026-08-01.

Un sello sólo puede moverse en la dirección que protege MÁS. Por eso la
frontera efectiva ya no es un literal editable sino `min(sello, declarada)`:
adelantarla (sellar más data) es posible; atrasarla (des-sellar) es
aritméticamente imposible, no "está prohibido por una convención".

La segunda mitad del ataque es temporal y la cubre `verificar_sello()`: una
frontera situada en el FUTURO deja cero material sellado — el holdout existe
en el papel y está vacío en los hechos. Eso es exactamente lo que pasó el
2026-07-31, y por eso el test lo evalúa contra la fecha del sistema.

Nota de alcance: el contrato declara un rango cerrado (2026-07-01→2026-12-31),
pero esta implementación (siguiendo la instrucción literal de la fase 3b)
solo hace cumplir el LÍMITE INFERIOR (`>= HOLDOUT_START`); no acota por el
límite superior. Con los datos actuales (hasta 2026-07-21) esto no tiene
efecto práctico distinto; si algún día se ingiere data posterior a
2026-12-31 para desarrollo, haría falta revisar si el guard debe acotar
también por arriba (decisión de diseño, no tomada acá).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

# EL SELLO. Este literal es HISTORIA, no configuración: es la fecha en que el
# holdout se cerró. No se edita nunca, ni para "reparticionar", ni para
# "absorber" meses a la muestra de desarrollo, ni por conveniencia de un
# estudio. Si alguna vez hubiera que abrir holdout, se hace por el protocolo
# de apertura (una por candidato, registrada en el log), no moviendo esto.
_SELLO_ORIGINAL_ISO = "2026-07-01T00:00:00"

# Frontera declarada por el contrato vigente. Un editor futuro puede tocar
# ESTA línea; no puede con eso des-sellar nada, porque abajo se toma el
# mínimo contra el sello.
_FRONTERA_DECLARADA_ISO = "2026-07-01T00:00:00"

HOLDOUT_END_ISO = "2026-12-31T23:59:59.999999"   # declarado, no forzado (ver nota arriba)

_VALID_PURPOSES = ("development", "target_free_validation")


class SelloInvalido(RuntimeError):
    """El sello del holdout está en un estado que no protege nada."""


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LOG_PATH = os.path.join(_REPO_ROOT, "docs", "holdout_access_log.md")

_LOG_HEADER = (
    "# Log de acceso al holdout (append-only)\n\n"
    "> Generado y mantenido por `edgelab/research/holdout_guard.py`. "
    "**Append-only**: nunca se edita ni se borra una fila existente; una "
    "corrección se registra como una fila NUEVA con una nota, no reescribiendo "
    "la vieja. Ver `docs/edge_validation_contract.md` §G4 (firewall del holdout) "
    "y `docs/NORTH_STAR.md`.\n\n"
    "| timestamp_utc | purpose | outcome | window_start_utc | window_end_utc | caller |\n"
    "|---|---|---|---|---|---|\n"
)


class HoldoutViolation(RuntimeError):
    """purpose='development' con un rango que toca el holdout sellado."""


def _iso_to_dt(s):
    if s is None:
        return None
    return datetime.fromisoformat(s.replace("Z", "")).replace(tzinfo=timezone.utc)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolver_frontera(declarada_iso=None, sello_iso=None):
    """Frontera efectiva = la MÁS TEMPRANA entre el sello y la declarada.

    `min()` no es una preferencia de estilo: es la mitad estructural de la
    regla 95. Adelantar la frontera sella MÁS material (seguro y permitido);
    atrasarla des-sella material ya protegido (INC-006). Tomando el mínimo,
    editar `_FRONTERA_DECLARADA_ISO` hacia adelante no tiene ningún efecto —
    no hay que confiar en que nadie lo haga.
    """
    declarada_iso = declarada_iso or _FRONTERA_DECLARADA_ISO
    sello_iso = sello_iso or _SELLO_ORIGINAL_ISO
    return sello_iso if _iso_to_dt(declarada_iso) > _iso_to_dt(sello_iso) else declarada_iso


HOLDOUT_START_ISO = _resolver_frontera()


def verificar_sello(ahora=None, *, frontera_iso=None):
    """Levanta `SelloInvalido` si el sello no protege nada. Corre contra reloj.

    La otra mitad de la regla 95, y la que hubiera atajado INC-006 el día que
    se escribió: una frontera situada en el FUTURO respecto de ahora deja el
    holdout **vacío** — todo lo realizado queda del lado de desarrollo. En el
    papel el holdout sigue existiendo; en los hechos no hay ni un día adentro.

    Por eso el chequeo es temporal y no puede ser un literal en un test: el
    commit de INC-006 era inofensivo el 2026-07-31 y se volvió dañino solo,
    sin que nadie tocara una línea, cuando el reloj cruzó la frontera.
    """
    ahora = ahora or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    frontera = _iso_to_dt(frontera_iso or HOLDOUT_START_ISO)
    if frontera > ahora:
        raise SelloInvalido(
            "la frontera del holdout (%s) está en el FUTURO respecto de %s: "
            "no hay un solo día sellado y todo el material realizado quedó "
            "del lado de desarrollo. Es el modo de falla de INC-006. La "
            "frontera es un sello, no un cursor (regla 95)."
            % (frontera.isoformat(), ahora.isoformat()))


def _ensure_log(log_path):
    if not os.path.exists(log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write(_LOG_HEADER)


def _log_append(log_path, *, purpose, outcome, start_utc, end_utc, caller):
    _ensure_log(log_path)
    row = "| %s | %s | %s | %s | %s | %s |\n" % (
        _now_iso(), purpose, outcome, start_utc, end_utc, caller)
    with open(log_path, "a", encoding="utf-8") as fh:   # "a" = append-only, nunca "w"
        fh.write(row)


def touches_holdout(start_utc, end_utc):
    """True si [start_utc, end_utc) puede incluir datos >= HOLDOUT_START.
    end_utc=None se trata como "sin cota superior" -> toca el holdout (fail-safe:
    ante la duda, se asume que SÍ toca, nunca se asume inocencia)."""
    hs = _iso_to_dt(HOLDOUT_START_ISO)
    e_dt = _iso_to_dt(end_utc)
    if e_dt is None:
        return True
    return e_dt >= hs


def check_holdout(start_utc, end_utc, *, purpose, caller="?", log_path=None):
    """Guard único y centralizado (edge_validation_contract.md §G4).

    start_utc / end_utc: strings ISO-8601 (mismo formato que
    `tools/run_nt8_bridge.py::iso_to_ns`). `end_utc=None` se trata fail-safe
    como "toca el holdout" (ver `touches_holdout`).
    purpose: OBLIGATORIO, sin default — "development" | "target_free_validation".
    caller: identificador libre de quién pide el acceso (para el log).
    log_path: override para tests; por defecto `docs/holdout_access_log.md`.

    - purpose="development" Y el rango toca el holdout -> `HoldoutViolation`
      (dura) + fila DENIED en el log (el intento queda trazado igual que si
      hubiera sido permitido).
    - purpose="development" Y el rango NO toca el holdout -> permitido, SIN
      escribir en el log (no es un acceso al holdout, nada que auditar).
    - purpose="target_free_validation" -> SIEMPRE permitido (paridad,
      determinismo, geometría, integridad, visor — los únicos usos legítimos
      declarados en el firewall), y SIEMPRE se registra (fila ALLOWED).
    """
    if purpose not in _VALID_PURPOSES:
        raise ValueError(
            "purpose debe ser 'development' o 'target_free_validation', no %r" % (purpose,))
    lp = log_path or DEFAULT_LOG_PATH

    if purpose == "target_free_validation":
        _log_append(lp, purpose=purpose, outcome="ALLOWED",
                   start_utc=start_utc, end_utc=end_utc, caller=caller)
        return

    # purpose == "development"
    if touches_holdout(start_utc, end_utc):
        _log_append(lp, purpose=purpose, outcome="DENIED_holdout_breach",
                   start_utc=start_utc, end_utc=end_utc, caller=caller)
        raise HoldoutViolation(
            "purpose='development' pero el rango [%s, %s) toca el holdout sellado "
            "(HOLDOUT_START=%s). Prohibido por edge_validation_contract.md §G4. "
            "Si esto es una validación target-free (paridad/determinismo/"
            "geometría/integridad/visor), pasá purpose='target_free_validation' "
            "explícitamente." % (start_utc, end_utc, HOLDOUT_START_ISO))
    # development seguro (enteramente antes del holdout): sin log.
