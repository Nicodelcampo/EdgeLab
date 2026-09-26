"""Data Contract de ticks NT8 .Last.txt (gate P0). Fixtures 100% sintéticos
(NO se leen los 348 MB reales; eso es F2). Formato confirmado:
`yyyyMMdd HHmmss fffffff ; last ; bid ; ask ; volume` (fracción 100 ns)."""
import pytest
from pydantic import ValidationError


def _contract(tz="America/Argentina/Buenos_Aires"):
    from edgelab.data.nt8_contract import Nt8TickContract, SIX_E
    return Nt8TickContract(declared_tz=tz, instrument=SIX_E)


VALID = [
    "20250725 200000 0280000;1.1783;1.1783;1.17835;1",     # last==bid -> sell
    "20250725 200001 0960000;1.17835;1.1783;1.17835;5",    # last==ask -> buy
    "20250725 200001 0960000;1.17835;1.1783;1.17835;1",    # ts duplicado (legítimo)
]


def test_valid_stream_parses_and_reports():
    from edgelab.data.nt8_reader import audit
    recs, rep = audit(VALID, _contract())
    assert rep.n == 3
    assert rep.n_duplicate_ts == 1
    assert rep.aggressor["sell"] == 1 and rep.aggressor["buy"] == 2
    assert recs[0].last_ticks == 23566          # 1.1783 / 0.00005
    assert recs[1].ask_ticks == 23567           # 1.17835 / 0.00005
    assert rep.last_outside_spread == 0


def test_declared_tz_required():
    from edgelab.data.nt8_contract import Nt8TickContract, SIX_E
    with pytest.raises(ValidationError):
        Nt8TickContract(instrument=SIX_E)       # falta declared_tz -> FAIL


def test_crossed_quote_fails():
    from edgelab.data.nt8_reader import audit, Nt8ContractError
    bad = ["20250725 200000 0280000;1.1783;1.17840;1.17835;1"]   # ask<bid
    with pytest.raises(Nt8ContractError):
        audit(bad, _contract())


def test_volume_nonpositive_fails():
    from edgelab.data.nt8_reader import audit, Nt8ContractError
    with pytest.raises(Nt8ContractError):
        audit(["20250725 200000 0280000;1.1783;1.1783;1.17835;0"], _contract())


def test_non_monotonic_fails():
    from edgelab.data.nt8_reader import audit, Nt8ContractError
    bad = ["20250725 200002 0000000;1.1783;1.1783;1.17835;1",
           "20250725 200001 0000000;1.1783;1.1783;1.17835;1"]
    with pytest.raises(Nt8ContractError):
        audit(bad, _contract())


def test_misaligned_price_fails():
    from edgelab.data.nt8_reader import audit, Nt8ContractError
    bad = ["20250725 200000 0280000;1.17831;1.1783;1.17835;1"]   # 23566.2 no entero
    with pytest.raises(Nt8ContractError):
        audit(bad, _contract())


def test_bad_fraction_fails():
    from edgelab.data.nt8_reader import audit, Nt8ContractError
    bad = ["20250725 200000 028000;1.1783;1.1783;1.17835;1"]     # 6 dígitos
    with pytest.raises(Nt8ContractError):
        audit(bad, _contract())


def test_last_outside_spread_counted_not_failed():
    from edgelab.data.nt8_reader import audit
    recs, rep = audit(["20250725 200000 0280000;1.17850;1.1783;1.17835;1"], _contract())
    assert rep.n == 1 and rep.last_outside_spread == 1
    assert rep.aggressor["unclassified"] == 1


def test_resolution_limited_and_inconsistent_warn():
    from edgelab.data.nt8_reader import audit
    lines = [
        "20250725 200000 0040000;1.1783;1.1783;1.17835;1",
        "20250725 200000 0040000;1.1783;1.1783;1.17835;1",
        "20250725 200000 0080000;1.1783;1.1783;1.17835;1",
        "20250725 200000 0080000;1.1783;1.1783;1.17835;1",
        "20250725 200000 0170000;1.1783;1.1783;1.17835;1",   # 17ms: rompe la grilla 4ms
    ]
    recs, rep = audit(lines, _contract())
    assert rep.resolution_limited is True
    assert rep.inconsistent_resolution is True
    assert any("quantum" in w.lower() or "resol" in w.lower() for w in rep.warnings)
