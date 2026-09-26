"""Reglas de una cuenta de prop firm (evaluación + cuenta fondeada), como datos.

Todas las cantidades monetarias en USD. Un catálogo vive en `config/propfirms/*.json`; cada entrada declara de dónde
salió (`source_url`, `fetched_at`, `sha256` del HTML) y si una persona la verificó (`verified`). Una regla no
verificada se puede simular, pero el reporte lo marca: el scraper extrae candidatos, no verdades.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DRAWDOWN_KINDS = ("static", "eod_trailing", "intraday_trailing")


@dataclass
class Rules:
    firm: str
    plan: str
    account_size: float
    # evaluación
    eval_fee: float                      # precio por intento (mensual o único)
    profit_target: float
    max_loss: float                      # distancia al piso de pérdida
    drawdown_kind: str = "eod_trailing"
    lock_at_profit: float | None = None  # el piso deja de subir al llegar a este beneficio (None = nunca)
    daily_loss_limit: float | None = None
    consistency_cap: float | None = None  # fracción máxima del beneficio total en un día (0.5 = 50 %)
    min_trading_days: int = 1
    max_contracts: int | None = None
    # cuenta fondeada
    activation_fee: float = 0.0
    funded_max_loss: float | None = None  # si None, igual a max_loss
    funded_drawdown_kind: str | None = None
    funded_lock_at_profit: float | None = None
    funded_daily_loss_limit: float | None = None
    funded_consistency_cap: float | None = None
    payout_min_days: int = 5              # días de trading entre retiros
    payout_min_profit: float = 0.0        # beneficio mínimo del ciclo para poder retirar
    payout_split: float = 0.9
    payout_cap: float | None = None       # tope por retiro
    payout_max_count: int = 5
    # procedencia
    source_url: str = ""
    fetched_at: str = ""
    sha256: str = ""
    verified: bool = False
    notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.drawdown_kind not in DRAWDOWN_KINDS:
            raise ValueError(f"drawdown_kind debe ser uno de {DRAWDOWN_KINDS}")
        if self.funded_drawdown_kind and self.funded_drawdown_kind not in DRAWDOWN_KINDS:
            raise ValueError(f"funded_drawdown_kind debe ser uno de {DRAWDOWN_KINDS}")
        if self.profit_target <= 0 or self.max_loss <= 0:
            raise ValueError("profit_target y max_loss deben ser positivos")
        if self.consistency_cap is not None and not 0 < self.consistency_cap <= 1:
            raise ValueError("consistency_cap en (0, 1]")

    @property
    def key(self) -> str:
        return f"{self.firm}|{self.plan}"

    def geometric_ceiling(self) -> float:
        """Techo de pase para un participante sin ventaja, piso fijo y trayectoria continua: L / (T + L)
        (Villahermosa 2026, Prop. 1). El piso móvil, los saltos y el horizonte finito sólo lo bajan."""
        return self.max_loss / (self.profit_target + self.max_loss)

    def funded(self) -> "Rules":
        """Las reglas de la etapa fondeada, con los defaults heredados de la evaluación."""
        d = asdict(self)
        d.update(max_loss=self.funded_max_loss or self.max_loss,
                 drawdown_kind=self.funded_drawdown_kind or self.drawdown_kind,
                 lock_at_profit=self.funded_lock_at_profit if self.funded_lock_at_profit is not None else self.lock_at_profit,
                 daily_loss_limit=self.funded_daily_loss_limit if self.funded_daily_loss_limit is not None else self.daily_loss_limit,
                 consistency_cap=self.funded_consistency_cap)
        return Rules(**d)


def load_catalog(path: str | Path) -> list[Rules]:
    """Carga todos los `*.json` de un directorio (cada archivo: una regla o una lista)."""
    p = Path(path)
    files = sorted(p.glob("*.json")) if p.is_dir() else [p]
    out: list[Rules] = []
    for f in files:
        raw = json.loads(f.read_text(encoding="utf-8"))
        for r in raw if isinstance(raw, list) else [raw]:
            out.append(Rules(**r))
    return out


def save_rules(rules: list[Rules], path: str | Path) -> None:
    Path(path).write_text(json.dumps([asdict(r) for r in rules], indent=1, ensure_ascii=False), encoding="utf-8")
