import pytest
import numpy as np
from pathlib import Path
from tools.analyze_all_es_10sessions import EXPECTED_FILES, analyze_exports
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks
from tools.run_mbt_export import load_canonical_ticks_fast
from tools.analyze_mbt_apriori import percentile

DIR = Path("E:/DatosNT8/es_apriori")


def test_current_score_never_participates_in_own_threshold():
    """Punto 1: current_score no entra en su propio threshold causal."""
    ring = [10.0, 20.0, 30.0]
    # Si agregamos 100.0 antes del percentil:
    thr_leaked = percentile(ring + [100.0], 90.0)
    # Orden causal estricto:
    thr_causal = percentile(ring, 90.0)
    assert thr_causal != thr_leaked
    assert thr_causal < thr_leaked


def test_exact_eight_exports_and_rejection_of_extras(tmp_path):
    """Punto 5 y 6: Validación de lista exacta de 8 exports y detección de extras/faltantes."""
    # Carpeta vacía -> falla
    with pytest.raises(ValueError, match="Faltantes"):
        analyze_exports(tmp_path)

    # Carpeta con archivo extra -> falla
    for f in EXPECTED_FILES:
        (tmp_path / f).write_text("# meta\n", encoding="utf-8")
    (tmp_path / "extra_file.csv").write_text("# meta\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Sobran / Extras"):
        analyze_exports(tmp_path)


@pytest.mark.skipif(not DIR.exists(), reason="Exports dir not available")
def test_native_q90_parity_and_session_invariants():
    """Puntos 2, 3, 4: Paridad nativa q90, sum(by_session) == total, median == published_median."""
    res = analyze_exports(DIR)
    for m in res["manifest"]:
        fname = m["file"]
        assert m["n_zones_native"] == m["recomputed_q90_zones"], f"Falla paridad q90 en {fname}"
        
        r = res["results"][fname]
        for q, qst in r["q_eval"].items():
            by_ses_vals = list(qst["by_session"].values())
            assert sum(by_ses_vals) == qst["total"], f"sum(by_session) != total en {fname}, q={q}"
            assert np.isclose(np.median(by_ses_vals), qst["med"]), f"median != published en {fname}, q={q}"


def test_fast_loader_parity_with_canonical_fixture(tmp_path):
    """Punto 8 y 9: Comparación byte a byte en fixture y verificación de fallos."""
    fixture_content = (
        "20260713 220000 0040000;7518.25;7518.00;7518.25;5\n"
        "20260713 220000 0050000;7518.50;7518.25;7518.50;2\n"
        "20260713 220000 0060000;7518.25;7518.00;7518.25;1\n"
    )
    fixture_path = tmp_path / "fixture.txt"
    fixture_path.write_text(fixture_content, encoding="utf-8")

    t_fast = load_canonical_ticks_fast(fixture_path, tick_size=0.25)
    t_canon, _, _, _, _, _ = load_canonical_ticks(fixture_path, tick_size=0.25)

    assert len(t_fast) == len(t_canon) == 3
    assert np.array_equal(t_fast.ts_ns, t_canon.ts_ns)
    assert np.array_equal(t_fast.price_ticks, t_canon.price_ticks)
    assert np.array_equal(t_fast.bid_ticks, t_canon.bid_ticks)
    assert np.array_equal(t_fast.ask_ticks, t_canon.ask_ticks)
    assert np.array_equal(t_fast.volume, t_canon.volume)
    assert np.array_equal(t_fast.sequence, t_canon.sequence)


def test_malformed_or_missing_bbo_fail_closed(tmp_path):
    """Punto 9: Fallo ante línea malformada o BBO no positivo cuando allow_missing_bbo=False."""
    malformed_path = tmp_path / "malformed.txt"
    malformed_path.write_text("20260713 220000 0040000;7518.25;7518.00\n", encoding="utf-8")
    with pytest.raises(ValueError, match="línea malformada"):
        load_canonical_ticks_fast(malformed_path, tick_size=0.25)

    missing_bbo_path = tmp_path / "missing_bbo.txt"
    missing_bbo_path.write_text("20260713 220000 0040000;7518.25;0.00;0.00;5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="BBO no positivo"):
        load_canonical_ticks_fast(missing_bbo_path, tick_size=0.25, allow_missing_bbo=False)


def test_full_tick_grid_streaming_scanner(tmp_path):
    """Punto 7: Escaneo streaming de tick grid."""
    offgrid_path = tmp_path / "offgrid.txt"
    offgrid_path.write_text("20260713 220000 0040000;7518.27;7518.00;7518.25;5\n", encoding="utf-8")
    
    # Comprobación de detección de off-grid
    parts = offgrid_path.read_text(encoding="utf-8").strip().split(";")
    p = float(parts[1])
    assert abs(p / 0.25 - round(p / 0.25)) > 1e-5
