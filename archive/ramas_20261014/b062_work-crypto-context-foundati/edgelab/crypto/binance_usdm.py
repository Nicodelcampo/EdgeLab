"""Binance USD-M trades + bookTicker -> ``TickSeries`` de BigTrap2.

El contrato temporal es estricto y no negociable::

    bookTicker.transaction_time < trade.time

Un book con el mismo timestamp que el trade es futuro/ambiguo para ese trade y no
puede clasificarlo. El adaptador no abre outcomes ni decide una unidad económica de
volumen: ``quantity_unit_base`` es obligatoria y queda declarada en el reporte.

Fuentes de schema:
- Binance Public Data: USD-M trades = id, price, qty, quoteQty, time,
  isBuyerMaker.
- Binance USD-M bookTicker: u, b, B, a, A, T, E.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from edgelab.bridge.ticks import TickSeries

_TRADES_POSITIONAL = (
    "trade_id",
    "price",
    "qty",
    "quote_qty",
    "trade_time",
    "is_buyer_maker",
)
_BOOK_POSITIONAL = (
    "update_id",
    "bid_price",
    "bid_qty",
    "ask_price",
    "ask_qty",
    "transaction_time",
    "event_time",
)


def sha256_file(path: str | Path) -> str:
    h = sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _positive_decimal(value: str | float | Decimal, name: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} no es decimal: {value!r}") from exc
    if not out.is_finite() or out <= 0:
        raise ValueError(f"{name} debe ser finito y > 0: {value!r}")
    return out


@dataclass(frozen=True)
class BinanceUsdmContract:
    """Geometría explícita del piloto; no hereda unidades de futuros CME."""

    symbol: str
    tick_size: Decimal | str | float
    quantity_unit_base: Decimal | str | float
    venue: str = "BINANCE"
    product: str = "USD-M_PERPETUAL"
    quantity_unit_status: str | None = None
    quantity_unit_source: str | None = None

    def __post_init__(self) -> None:
        # La procedencia de la unidad NO tiene default: afirmar exchangeInfo sin
        # que nadie lo haya declarado seria inventar la fuente en el manifest.
        if not self.quantity_unit_status:
            raise ValueError("quantity_unit_status es obligatorio y no tiene default")
        if not self.quantity_unit_source:
            raise ValueError("quantity_unit_source es obligatorio y no tiene default")
        symbol = str(self.symbol).strip().upper()
        if not symbol:
            raise ValueError("symbol vacío")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "tick_size", _positive_decimal(self.tick_size, "tick_size"))
        object.__setattr__(
            self,
            "quantity_unit_base",
            _positive_decimal(self.quantity_unit_base, "quantity_unit_base"),
        )

    @property
    def contract_id(self) -> str:
        return f"{self.symbol}-PERP"

    def to_dict(self) -> dict[str, str]:
        return {
            "symbol": self.symbol,
            "contract_id": self.contract_id,
            "venue": self.venue,
            "product": self.product,
            "tick_size": str(self.tick_size),
            "quantity_unit_base": str(self.quantity_unit_base),
            "quantity_unit_status": self.quantity_unit_status,
            "quantity_unit_source": self.quantity_unit_source,
        }


@dataclass(frozen=True)
class CryptoPilotReport:
    n_trades: int
    n_book_updates: int
    n_joined: int
    n_unmatched_without_prior_book: int
    join_coverage: float
    strict_prior_violations: int
    n_quote_classifiable: int
    quote_classifiable_pct: float
    maker_agreement_n: int
    maker_agreement_pct: float | None
    duplicate_trade_ids: int
    id_gap_ranges: int
    missing_trade_ids: int
    gap_sample: tuple[dict[str, int], ...]
    quantity_unit_base: str
    quantity_unit_status: str
    quantity_unit_source: str = ""
    raw_id_gap_ranges: int = 0
    raw_missing_trade_ids: int = 0
    analysis_id_gap_ranges: int = 0
    analysis_missing_trade_ids: int = 0
    id_gaps_created_by_exclusion: int = 0
    n_offtick_book_rows_excluded_bid: int = 0
    n_offtick_book_rows_excluded_ask: int = 0
    offtick_book_sample: tuple[dict[str, Any], ...] = ()
    n_trades_with_changed_bbo: int = 0
    added_book_age_ns_p50: float | None = None
    added_book_age_ns_max: int = 0
    promotion_eligible: bool = True
    n_offtick_prices_excluded: int = 0
    n_offtick_book_rows_excluded: int = 0
    offtick_price_sample: tuple[dict[str, Any], ...] = ()
    offtick_exclusion_invoked: bool = False
    status: str = "OK"
    outcomes_opened: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CryptoPilotResult:
    ticks: TickSeries
    sidecar: pd.DataFrame
    report: CryptoPilotReport
    contract: BinanceUsdmContract

    def tick_frame(self) -> pd.DataFrame:
        """Tabla portable; no se adjudica como F2 canónico de NT8."""
        n = len(self.ticks)
        return pd.DataFrame(
            {
                "ts_utc_ns": self.ticks.ts_ns,
                "price_ticks": self.ticks.price_ticks,
                "volume": self.ticks.volume,
                "bid_ticks": self.ticks.bid_ticks,
                "ask_ticks": self.ticks.ask_ticks,
                "sequence": self.ticks.sequence,
                "instrument": np.repeat(self.ticks.instrument, n),
                "contract": np.repeat(self.ticks.contract, n),
                "source": np.repeat("binance_usdm_strict_prior", n),
            }
        )


def _is_number(text: object) -> bool:
    try:
        Decimal(str(text).strip())
        return True
    except (InvalidOperation, ValueError):
        return False


def _norm_header(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _read_data_vision_csv(path: str | Path, positional: tuple[str, ...], kind: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    sample = pd.read_csv(path, compression="infer", header=None, nrows=1, dtype=str)
    if sample.shape[1] < len(positional):
        raise ValueError(f"{kind}: se esperaban >= {len(positional)} columnas; hay {sample.shape[1]}")
    has_header = not _is_number(sample.iloc[0, 0])
    if has_header:
        raw = pd.read_csv(path, compression="infer", header=0)
        raw = _rename_headered(raw, kind)
    else:
        raw = pd.read_csv(path, compression="infer", header=None)
        if raw.shape[1] != len(positional):
            raise ValueError(
                f"{kind}: archivo sin header debe tener {len(positional)} columnas; "
                f"hay {raw.shape[1]}"
            )
        raw.columns = list(positional)
    missing = set(positional) - set(raw.columns)
    if missing:
        raise ValueError(f"{kind}: faltan columnas {sorted(missing)}; presentes={list(raw.columns)}")
    return raw.loc[:, list(positional)].copy()


def _rename_headered(raw: pd.DataFrame, kind: str) -> pd.DataFrame:
    if kind == "trades":
        aliases = {
            "id": "trade_id",
            "tradeid": "trade_id",
            "price": "price",
            "qty": "qty",
            "quantity": "qty",
            "quoteqty": "quote_qty",
            "quotequantity": "quote_qty",
            "time": "trade_time",
            "tradetime": "trade_time",
            "isbuyermaker": "is_buyer_maker",
        }
        exact: dict[str, str] = {}
    else:
        aliases = {
            "updateid": "update_id",
            "bestbidprice": "bid_price",
            "bidprice": "bid_price",
            "bestbidqty": "bid_qty",
            "bidqty": "bid_qty",
            "bestaskprice": "ask_price",
            "askprice": "ask_price",
            "bestaskqty": "ask_qty",
            "askqty": "ask_qty",
            "transactiontime": "transaction_time",
            "eventtime": "event_time",
        }
        # Binance websocket/Data Vision single-letter names are case-sensitive.
        exact = {
            "u": "update_id",
            "b": "bid_price",
            "B": "bid_qty",
            "a": "ask_price",
            "A": "ask_qty",
            "T": "transaction_time",
            "E": "event_time",
        }
    rename: dict[object, str] = {}
    for col in raw.columns:
        if str(col) in exact:
            rename[col] = exact[str(col)]
        else:
            norm = _norm_header(col)
            if norm in aliases:
                rename[col] = aliases[norm]
    return raw.rename(columns=rename)


def _epoch_to_ns(values: pd.Series, name: str) -> np.ndarray:
    numeric = pd.to_numeric(values, errors="raise").to_numpy(dtype=np.int64)
    if len(numeric) == 0:
        return numeric
    magnitude = int(np.median(np.abs(numeric)))
    if magnitude >= 100_000_000_000_000_000:  # ns
        factor = 1
    elif magnitude >= 100_000_000_000_000:  # us
        factor = 1_000
    elif magnitude >= 100_000_000_000:  # ms
        factor = 1_000_000
    elif magnitude >= 100_000_000:  # s
        factor = 1_000_000_000
    else:
        raise ValueError(f"{name}: unidad epoch no reconocida (mediana={magnitude})")
    limit = np.iinfo(np.int64).max // factor
    if np.any(np.abs(numeric) > limit):
        raise OverflowError(f"{name}: timestamp desborda int64 al convertir a ns")
    return numeric * factor


def _parse_bool(values: pd.Series, name: str) -> np.ndarray:
    mapped = values.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if mapped.isna().any():
        bad = sorted(values[mapped.isna()].astype(str).unique()[:5])
        raise ValueError(f"{name}: booleanos inválidos {bad}")
    return mapped.to_numpy(dtype=bool)


def read_trades(path: str | Path) -> pd.DataFrame:
    out = _read_data_vision_csv(path, _TRADES_POSITIONAL, "trades")
    out["trade_id"] = pd.to_numeric(out["trade_id"], errors="raise").astype("int64")
    for col in ("price", "qty", "quote_qty"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype("float64")
    out["trade_time_ns"] = _epoch_to_ns(out.pop("trade_time"), "trade.time")
    out["is_buyer_maker"] = _parse_bool(out["is_buyer_maker"], "is_buyer_maker")
    if (out[["price", "qty"]] <= 0).any().any():
        raise ValueError("trades: price y qty deben ser > 0")
    return out.sort_values(["trade_time_ns", "trade_id"], kind="mergesort").reset_index(drop=True)


def read_book_ticker(path: str | Path) -> pd.DataFrame:
    out = _read_data_vision_csv(path, _BOOK_POSITIONAL, "bookTicker")
    out["update_id"] = pd.to_numeric(out["update_id"], errors="raise").astype("int64")
    for col in ("bid_price", "bid_qty", "ask_price", "ask_qty"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype("float64")
    out["transaction_time_ns"] = _epoch_to_ns(
        out.pop("transaction_time"), "bookTicker.transaction_time"
    )
    out["event_time_ns"] = _epoch_to_ns(out.pop("event_time"), "bookTicker.event_time")
    if (out[["bid_price", "ask_price"]] <= 0).any().any():
        raise ValueError("bookTicker: bid/ask deben ser > 0")
    if (out["ask_price"] < out["bid_price"]).any():
        raise ValueError("bookTicker cruzado: ask < bid")
    return out.sort_values(["transaction_time_ns", "update_id"], kind="mergesort").reset_index(drop=True)


def offtick_mask(values: np.ndarray, tick_size: Decimal) -> np.ndarray:
    """True donde el precio NO cae en la grilla de tick. No aborta: sólo marca."""
    tick = float(tick_size)
    ratio = np.asarray(values, dtype=np.float64) / tick
    return ~np.isclose(values, np.rint(ratio) * tick, rtol=0.0, atol=tick * 1e-8)


def _prices_to_ticks(values: np.ndarray, tick_size: Decimal, name: str) -> np.ndarray:
    tick = float(tick_size)
    ratio = np.asarray(values, dtype=np.float64) / tick
    nearest = np.rint(ratio)
    aligned = np.isclose(values, nearest * tick, rtol=0.0, atol=tick * 1e-8)
    if not bool(np.all(aligned)):
        i = int(np.flatnonzero(~aligned)[0])
        raise ValueError(f"{name}: precio {values[i]} no alinea con tick_size={tick_size}")
    return nearest.astype(np.int64)


def _missing_id_set(trade_ids: np.ndarray) -> set[int]:
    """IDs ausentes entre el minimo y el maximo observados. Conjunto concreto,
    para poder restar poblaciones en vez de restar cantidades de rangos."""
    ids = np.unique(np.asarray(trade_ids, dtype=np.int64))
    if len(ids) < 2:
        return set()
    return set(range(int(ids[0]), int(ids[-1]) + 1)) - set(ids.tolist())


def _id_gaps(trade_ids: np.ndarray) -> tuple[int, int, tuple[dict[str, int], ...]]:
    ids = np.sort(np.unique(np.asarray(trade_ids, dtype=np.int64)))
    if len(ids) < 2:
        return 0, 0, ()
    delta = np.diff(ids)
    positions = np.flatnonzero(delta > 1)
    rows = tuple(
        {
            "after_id": int(ids[i]),
            "before_id": int(ids[i + 1]),
            "missing": int(delta[i] - 1),
        }
        for i in positions[:20]
    )
    return int(len(positions)), int(np.sum(delta[positions] - 1)), rows


def load_binance_usdm_pair(
    trades_path: str | Path,
    book_ticker_path: str | Path,
    contract: BinanceUsdmContract,
    *,
    expected_trades_sha256: str | None = None,
    expected_book_sha256: str | None = None,
    require_full_coverage: bool = True,
    allow_offtick_prices: bool = False,
) -> CryptoPilotResult:
    """Carga y une ambos archivos con búsqueda estrictamente anterior.

    Si falta book previo para cualquier trade, el default falla cerrado. Con
    ``require_full_coverage=False`` esos trades se excluyen y quedan cuantificados.

    Precios fuera de la grilla de tick abortan por default. Con
    ``allow_offtick_prices=True`` se excluyen, se cuentan y se muestrean en el
    reporte, y la corrida queda marcada ``offtick_exclusion_invoked=True``. Ese
    modo es DIAGNOSTICO: no se promueve ni se compara contra una corrida limpia.
    """
    if expected_trades_sha256 and sha256_file(trades_path) != expected_trades_sha256.lower():
        raise ValueError("SHA-256 de trades no coincide")
    if expected_book_sha256 and sha256_file(book_ticker_path) != expected_book_sha256.lower():
        raise ValueError("SHA-256 de bookTicker no coincide")

    trades = read_trades(trades_path)
    book = read_book_ticker(book_ticker_path)
    duplicate_trade_ids = int(trades["trade_id"].duplicated().sum())
    if duplicate_trade_ids:
        raise ValueError(f"trades: {duplicate_trade_ids} trade_id duplicados")

    # Precios fuera de la grilla de tick. Se resuelve ANTES del join para que la
    # cobertura y los conteos posteriores describan la poblacion efectivamente usada.
    # Gaps sobre la poblacion RAW, ANTES de cualquier exclusion. Sin esto, una
    # exclusion se disfraza de gap del venue.
    raw_gaps, raw_missing, _ = _id_gaps(trades["trade_id"].to_numpy(dtype=np.int64))
    raw_missing_set = _missing_id_set(trades["trade_id"].to_numpy(dtype=np.int64))

    _off = offtick_mask(trades["price"].to_numpy(dtype=np.float64), contract.tick_size)
    n_offtick = int(_off.sum())
    offtick_sample: tuple[dict[str, Any], ...] = ()
    if n_offtick:
        offtick_sample = tuple(
            {"trade_id": int(r.trade_id), "price": float(r.price), "qty": float(r.qty),
             "trade_time_ns": int(r.trade_time_ns)}
            for r in trades.loc[_off].head(10).itertuples())
        if not allow_offtick_prices:
            first = offtick_sample[0]
            raise ValueError(
                f"trades: {n_offtick} precios no alinea(n) con tick_size={contract.tick_size}; "
                f"primero trade_id={first['trade_id']} price={first['price']}. "
                "Usar allow_offtick_prices=True SOLO como diagnostico declarado.")
        trades = trades.loc[~_off].reset_index(drop=True)

    # Mismo fenomeno del lado del book. Se cuenta APARTE porque la semantica es
    # distinta: quitar una fila de book cambia que book ve un trade posterior,
    # no solo la poblacion de trades.
    _offb = (offtick_mask(book["bid_price"].to_numpy(dtype=np.float64), contract.tick_size)
             | offtick_mask(book["ask_price"].to_numpy(dtype=np.float64), contract.tick_size))
    n_offtick_book = int(_offb.sum())
    n_off_bid = n_off_ask = 0; offtick_book_sample: tuple[dict[str, Any], ...] = ()
    n_changed_bbo = 0; added_age_p50 = None; added_age_max = 0
    if n_offtick_book:
        if not allow_offtick_prices:
            raise ValueError(
                f"bookTicker: {n_offtick_book} filas no alinea(n) con tick_size={contract.tick_size}. "
                "Usar allow_offtick_prices=True SOLO como diagnostico declarado.")
        _ob = offtick_mask(book["bid_price"].to_numpy(dtype=np.float64), contract.tick_size)
        _oa = offtick_mask(book["ask_price"].to_numpy(dtype=np.float64), contract.tick_size)
        n_off_bid = int(_ob.sum()); n_off_ask = int(_oa.sum())
        offtick_book_sample = tuple(
            {"update_id": int(getattr(r, "update_id", -1)),
             "bid_price": float(r.bid_price), "ask_price": float(r.ask_price),
             "transaction_time_ns": int(r.transaction_time_ns),
             "offtick_side": ("bid" if _ob[i] and not _oa[i] else
                              "ask" if _oa[i] and not _ob[i] else "both")}
            for i, r in zip(np.flatnonzero(_offb)[:10], book.loc[_offb].head(10).itertuples()))
        # BBO que habria visto cada trade SIN excluir, para medir el efecto del filtro
        _t_book_pre = book["transaction_time_ns"].to_numpy(dtype=np.int64)
        _idx_pre = np.searchsorted(_t_book_pre, trades["trade_time_ns"].to_numpy(dtype=np.int64), side="left") - 1
        _keep_pos = np.flatnonzero(~_offb)
        book = book.loc[~_offb].reset_index(drop=True)
        if len(book) == 0:
            raise ValueError("bookTicker: TODAS las filas quedaron fuera de tick; abortado")
        _remap = np.full(len(_offb), -1, dtype=np.int64); _remap[_keep_pos] = np.arange(len(_keep_pos))
        _t_book_post = book["transaction_time_ns"].to_numpy(dtype=np.int64)
        _idx_post = np.searchsorted(_t_book_post, trades["trade_time_ns"].to_numpy(dtype=np.int64), side="left") - 1
        _valid = (_idx_pre >= 0) & (_idx_post >= 0)
        _changed = _valid & (_remap[np.clip(_idx_pre, 0, len(_offb)-1)] != _idx_post)
        n_changed_bbo = int(_changed.sum())
        if n_changed_bbo:
            _extra = (_t_book_pre[np.clip(_idx_pre,0,len(_t_book_pre)-1)][_changed]
                      - _t_book_post[np.clip(_idx_post,0,len(_t_book_post)-1)][_changed])
            added_age_p50 = float(np.median(_extra)); added_age_max = int(_extra.max())
        else:
            added_age_p50 = None; added_age_max = 0

    t_trade = trades["trade_time_ns"].to_numpy(dtype=np.int64)
    t_book = book["transaction_time_ns"].to_numpy(dtype=np.int64)
    if len(t_book) == 0:
        raise ValueError("bookTicker vacío")

    # side='left' excluye explícitamente T == trade.time.
    book_index = np.searchsorted(t_book, t_trade, side="left") - 1
    joined = book_index >= 0
    n_unmatched = int((~joined).sum())
    if require_full_coverage and n_unmatched:
        raise ValueError(f"join causal incompleto: {n_unmatched}/{len(trades)} sin book previo")
    if not bool(joined.any()):
        raise ValueError("ningún trade tiene book estrictamente anterior")

    tr = trades.loc[joined].reset_index(drop=True)
    bi = book_index[joined]
    bk = book.iloc[bi].reset_index(drop=True)
    selected_book_time = bk["transaction_time_ns"].to_numpy(dtype=np.int64)
    selected_trade_time = tr["trade_time_ns"].to_numpy(dtype=np.int64)
    violations = int((selected_book_time >= selected_trade_time).sum())
    if violations:
        raise AssertionError(f"join estricto violado en {violations} filas")

    price = tr["price"].to_numpy(dtype=np.float64)
    bid = bk["bid_price"].to_numpy(dtype=np.float64)
    ask = bk["ask_price"].to_numpy(dtype=np.float64)
    quote_valid = (ask > bid) & (bid > 0)
    side_quote = np.where(quote_valid & (price >= ask), 1, np.where(quote_valid & (price <= bid), -1, 0))
    maker_side = np.where(tr["is_buyer_maker"].to_numpy(dtype=bool), -1, 1)
    classifiable = side_quote != 0
    maker_agreement_n = int((side_quote[classifiable] == maker_side[classifiable]).sum())
    n_classifiable = int(classifiable.sum())

    quantity_unit = float(contract.quantity_unit_base)
    volume_units = tr["qty"].to_numpy(dtype=np.float64) / quantity_unit
    if not np.isfinite(volume_units).all() or np.any(volume_units <= 0):
        raise ValueError("volumen normalizado inválido")

    ticks = TickSeries(
        ts_ns=selected_trade_time,
        price_ticks=_prices_to_ticks(price, contract.tick_size, "trade.price"),
        volume=volume_units,
        bid_ticks=_prices_to_ticks(bid, contract.tick_size, "book.bid"),
        ask_ticks=_prices_to_ticks(ask, contract.tick_size, "book.ask"),
        sequence=np.arange(len(tr), dtype=np.int64),
        tick_size=float(contract.tick_size),
        instrument=contract.symbol,
        contract=contract.contract_id,
        source=f"{Path(trades_path).name}+{Path(book_ticker_path).name}",
    )

    gaps, missing_ids, gap_sample = _id_gaps(tr["trade_id"].to_numpy(dtype=np.int64))
    coverage = len(tr) / len(trades) if len(trades) else 0.0
    # PRECEDENCIA DE ESTADO, de menor a mayor severidad. La exclusion off-tick
    # DOMINA sobre gaps y join parcial: una corrida con exclusiones invocadas no
    # puede emitir PILOT_ACCEPTED* bajo ninguna combinacion.
    offtick_invoked = bool((n_offtick or n_offtick_book) and allow_offtick_prices)
    status = "PILOT_ACCEPTED_TARGET_FREE_WITH_ID_GAPS" if gaps else "PILOT_ACCEPTED_TARGET_FREE"
    if n_unmatched:
        status = "PILOT_PARTIAL_JOIN"
    if offtick_invoked:
        status = "DIAGNOSTIC_OFFTICK_EXCLUSION"
    promotion_eligible = not offtick_invoked and not n_unmatched
    # Excepcion explicita, NO assert: python -O elimina los assert y el
    # invariante desapareceria justo en una corrida optimizada.
    if offtick_invoked and status.startswith("PILOT_ACCEPTED"):
        raise RuntimeError(
            "invariante violado: exclusion off-tick invocada con status "
            f"{status}; una corrida con exclusiones no puede emitir PILOT_ACCEPTED")

    report = CryptoPilotReport(
        n_trades=int(len(trades)),
        n_book_updates=int(len(book)),
        n_joined=int(len(tr)),
        n_unmatched_without_prior_book=n_unmatched,
        join_coverage=float(coverage),
        strict_prior_violations=violations,
        n_quote_classifiable=n_classifiable,
        quote_classifiable_pct=float(n_classifiable / len(tr)) if len(tr) else 0.0,
        maker_agreement_n=maker_agreement_n,
        maker_agreement_pct=(float(maker_agreement_n / n_classifiable) if n_classifiable else None),
        duplicate_trade_ids=duplicate_trade_ids,
        id_gap_ranges=gaps,
        missing_trade_ids=missing_ids,
        gap_sample=gap_sample,
        quantity_unit_base=str(contract.quantity_unit_base),
        raw_id_gap_ranges=raw_gaps,
        raw_missing_trade_ids=raw_missing,
        analysis_id_gap_ranges=gaps,
        analysis_missing_trade_ids=missing_ids,
        id_gaps_created_by_exclusion=len(_missing_id_set(tr["trade_id"].to_numpy(dtype=np.int64)) - raw_missing_set),
        n_offtick_book_rows_excluded_bid=n_off_bid,
        n_offtick_book_rows_excluded_ask=n_off_ask,
        offtick_book_sample=offtick_book_sample,
        n_trades_with_changed_bbo=n_changed_bbo,
        added_book_age_ns_p50=added_age_p50,
        added_book_age_ns_max=added_age_max,
        promotion_eligible=promotion_eligible,
        quantity_unit_source=contract.quantity_unit_source,
        n_offtick_prices_excluded=n_offtick,
        n_offtick_book_rows_excluded=n_offtick_book,
        offtick_price_sample=offtick_sample,
        offtick_exclusion_invoked=bool((n_offtick or n_offtick_book) and allow_offtick_prices),
        quantity_unit_status=contract.quantity_unit_status,
        status=status,
    )
    sidecar = pd.DataFrame(
        {
            "sequence": ticks.sequence,
            "trade_id": tr["trade_id"].to_numpy(dtype=np.int64),
            "trade_time_ns": selected_trade_time,
            "book_update_id": bk["update_id"].to_numpy(dtype=np.int64),
            "book_transaction_time_ns": selected_book_time,
            "book_age_ns": selected_trade_time - selected_book_time,
            "is_buyer_maker": tr["is_buyer_maker"].to_numpy(dtype=bool),
            "side_by_quote": side_quote.astype(np.int8),
            "side_by_maker": maker_side.astype(np.int8),
            "quote_classifiable": classifiable,
        }
    )
    return CryptoPilotResult(ticks=ticks, sidecar=sidecar, report=report, contract=contract)
