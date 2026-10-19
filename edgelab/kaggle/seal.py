"""Firewall del holdout (Contrato Kaggle v2, seccion "Firewall del holdout").

Reglas del contrato que este modulo hace ejecutables:

  * research_session_date <= 2026-06-30
  * cualquier sesion con trade date >= 2026-07-01 queda excluida de eventos,
    ventanas, targets y folds
  * el holdout debe estar FISICAMENTE ausente del dataset exploratorio
  * una sesion no puede entrar parcialmente por empezar el dia UTC anterior
  * todos los conteos de exclusion se publican en el reporte

Diseno fail-closed: `apply_seal` corta por trade date de Chicago y devuelve el
conteo de filas cortadas por fecha. Abrir el holdout exige un token explicito
(M8) y queda registrado en el reporte; no hay flag booleano silencioso.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import numpy as np

from .sessions_cme import NS_PER_SEC, trade_date_ymd

RESEARCH_MAX_YMD = 20260630
HOLDOUT_START_YMD = 20260701
HOLDOUT_END_YMD = 20261231
OPEN_HOLDOUT_TOKEN = "M8_HOLDOUT_OPENED_ONCE"

# Corte UTC ingenuo, incluido solo para MEDIR el leak que produce.
NAIVE_UTC_CUT_NS = (
    int(datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()) * NS_PER_SEC
)


class HoldoutLeak(RuntimeError):
    """Se detecto al menos una fila de holdout en un artefacto exploratorio."""


@dataclass
class SealReport:
    rows_in: int = 0
    rows_kept: int = 0
    rows_cut_holdout: int = 0
    rows_cut_after_holdout: int = 0
    first_trade_date_kept: int | None = None
    last_trade_date_kept: int | None = None
    first_trade_date_cut: int | None = None
    last_trade_date_cut: int | None = None
    cut_rows_by_trade_date: dict = field(default_factory=dict)
    kept_trade_dates_list: list = field(default_factory=list)
    # Diagnostico: filas que un corte UTC ingenuo habria conservado y que la
    # regla de sesion de Chicago corta. Es el leak literal del contrato.
    rows_leaked_by_naive_utc_cut: int = 0
    holdout_opened: bool = False
    rule: str = (
        "trade_date(Chicago, apertura 17:00 CT) <= 2026-06-30; "
        "holdout 2026-07-01..2026-12-31"
    )

    @property
    def kept_trade_dates(self) -> int:
        return len(self.kept_trade_dates_list)

    def to_dict(self, *, include_kept_list: bool = False) -> dict:
        d = asdict(self)
        d["cut_rows_by_trade_date"] = {
            str(k): int(v) for k, v in sorted(self.cut_rows_by_trade_date.items())
        }
        d["kept_trade_dates"] = self.kept_trade_dates
        if not include_kept_list:
            d.pop("kept_trade_dates_list", None)
        else:
            d["kept_trade_dates_list"] = [int(x) for x in self.kept_trade_dates_list]
        return d


def apply_seal(
    ts_utc_ns: np.ndarray,
    *,
    open_holdout_token: str | None = None,
) -> tuple[np.ndarray, SealReport]:
    """Devuelve (mascara_a_conservar, SealReport).

    Si `open_holdout_token` es exactamente OPEN_HOLDOUT_TOKEN, no se corta nada
    y el reporte queda marcado con holdout_opened=True. Cualquier otro valor no
    nulo es un error.
    """
    ts = np.asarray(ts_utc_ns, dtype=np.int64)
    rep = SealReport(rows_in=int(ts.size))
    if open_holdout_token is not None:
        if open_holdout_token != OPEN_HOLDOUT_TOKEN:
            raise ValueError(
                "token de apertura de holdout invalido; se esperaba "
                f"{OPEN_HOLDOUT_TOKEN!r}"
            )
        rep.holdout_opened = True
        rep.rows_kept = int(ts.size)
        if ts.size:
            td = trade_date_ymd(ts)
            rep.first_trade_date_kept = int(td.min())
            rep.last_trade_date_kept = int(td.max())
            rep.kept_trade_dates_list = [int(x) for x in np.unique(td)]
        return np.ones(ts.shape, dtype=bool), rep

    if ts.size == 0:
        return np.zeros(0, dtype=bool), rep

    td = trade_date_ymd(ts)
    keep = td <= RESEARCH_MAX_YMD
    cut = ~keep

    rep.rows_kept = int(keep.sum())
    in_holdout = cut & (td >= HOLDOUT_START_YMD) & (td <= HOLDOUT_END_YMD)
    rep.rows_cut_holdout = int(in_holdout.sum())
    rep.rows_cut_after_holdout = int((cut & (td > HOLDOUT_END_YMD)).sum())

    if rep.rows_kept:
        kept_td = td[keep]
        rep.first_trade_date_kept = int(kept_td.min())
        rep.last_trade_date_kept = int(kept_td.max())
        rep.kept_trade_dates_list = [int(x) for x in np.unique(kept_td)]
    if int(cut.sum()):
        cut_td = td[cut]
        rep.first_trade_date_cut = int(cut_td.min())
        rep.last_trade_date_cut = int(cut_td.max())
        vals, counts = np.unique(cut_td, return_counts=True)
        rep.cut_rows_by_trade_date = {int(v): int(c) for v, c in zip(vals, counts)}

    rep.rows_leaked_by_naive_utc_cut = int((cut & (ts < NAIVE_UTC_CUT_NS)).sum())
    return keep, rep


def assert_no_leak(ts_utc_ns: np.ndarray, *, where: str = "artefacto") -> None:
    """Levanta HoldoutLeak si queda alguna fila con trade date > 2026-06-30."""
    ts = np.asarray(ts_utc_ns, dtype=np.int64)
    if ts.size == 0:
        return
    td = trade_date_ymd(ts)
    bad = int((td > RESEARCH_MAX_YMD).sum())
    if bad:
        worst = int(td.max())
        raise HoldoutLeak(
            f"{where}: {bad} filas con trade date > {RESEARCH_MAX_YMD} "
            f"(max={worst}). El contrato invalida la version completa."
        )


def merge_reports(reports: list[SealReport]) -> SealReport:
    """Agrega reportes parciales en uno global (por batch o por archivo)."""
    out = SealReport()
    kept_dates: set[int] = set()
    firsts_k: list[int] = []
    lasts_k: list[int] = []
    firsts_c: list[int] = []
    lasts_c: list[int] = []
    for r in reports:
        out.rows_in += r.rows_in
        out.rows_kept += r.rows_kept
        out.rows_cut_holdout += r.rows_cut_holdout
        out.rows_cut_after_holdout += r.rows_cut_after_holdout
        out.rows_leaked_by_naive_utc_cut += r.rows_leaked_by_naive_utc_cut
        out.holdout_opened = out.holdout_opened or r.holdout_opened
        for k, v in r.cut_rows_by_trade_date.items():
            key = int(k)
            out.cut_rows_by_trade_date[key] = out.cut_rows_by_trade_date.get(
                key, 0
            ) + int(v)
        kept_dates.update(int(x) for x in r.kept_trade_dates_list)
        if r.first_trade_date_kept is not None:
            firsts_k.append(int(r.first_trade_date_kept))
            lasts_k.append(int(r.last_trade_date_kept))
        if r.first_trade_date_cut is not None:
            firsts_c.append(int(r.first_trade_date_cut))
            lasts_c.append(int(r.last_trade_date_cut))
    out.kept_trade_dates_list = sorted(kept_dates)
    if firsts_k:
        out.first_trade_date_kept = min(firsts_k)
        out.last_trade_date_kept = max(lasts_k)
    if firsts_c:
        out.first_trade_date_cut = min(firsts_c)
        out.last_trade_date_cut = max(lasts_c)
    return out
