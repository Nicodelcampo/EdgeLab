"""Identidades canónicas + validación de parámetros (F6.1).

Sin identidades inmutables y deterministas no se sostiene el store. Estos tests
fijan: determinismo, equivalencia canónica (defaults materializados), que
cualquier cambio semántico de código cambia el kernel_id, y que la validación
rechaza los 5 tipos de parámetro inválido.
"""
import numpy as np
import pytest

from edgelab.bridge import identity as idy
from edgelab.bridge.ticks import make_synthetic


# --------------------------- dataset_id ------------------------------------ #
def test_dataset_id_deterministic_and_content_addressed():
    tk = make_synthetic(n_sessions=1, ticks_per_session=2000)
    d1 = idy.dataset_id(tk, tz_interpretation="synthetic")
    d2 = idy.dataset_id(tk, tz_interpretation="synthetic")
    assert d1 == d2                                   # mismo contenido -> mismo id
    assert len(d1) == idy.ID_LEN
    # cambiar el contenido cambia el id (la ruta NO es identidad)
    tk2 = make_synthetic(n_sessions=1, ticks_per_session=2001)
    assert idy.dataset_id(tk2, tz_interpretation="synthetic") != d1
    # cambiar la interpretación de tz cambia el id
    assert idy.dataset_id(tk, tz_interpretation="canonical_utc_verified") != d1


def test_dataset_id_sensitive_to_prices():
    tk = make_synthetic(n_sessions=1, ticks_per_session=2000, seed=1)
    tk_mut = make_synthetic(n_sessions=1, ticks_per_session=2000, seed=1)
    tk_mut.price_ticks = tk_mut.price_ticks.copy()
    tk_mut.price_ticks[100] += 1                      # un solo tick distinto
    assert idy.dataset_id(tk, tz_interpretation="x") != \
        idy.dataset_id(tk_mut, tz_interpretation="x")


# --------------------------- kernel_id ------------------------------------- #
def test_kernel_id_deterministic():
    assert idy.kernel_id("Gaps2") == idy.kernel_id("Gaps2")
    assert idy.kernel_id("Gaps2") != idy.kernel_id("BigTrap2")


def test_kernel_id_changes_when_kernel_file_mutates():
    src = idy.kernel_sources("Gaps2")
    base = idy.kernel_id("Gaps2", src)
    mut = dict(src)
    kf = "gaps2.py"
    mut[kf] = mut[kf] + b"\n# cambio semantico\n"
    assert idy.kernel_id("Gaps2", mut) != base


def test_kernel_id_changes_when_shared_dep_mutates():
    # Cambiar el bar builder (bars.py) o los helpers (common.py) cambia el
    # kernel_id de TODOS los que dependen de ellos.
    for dep in ("common.py", "bars.py"):
        src = idy.kernel_sources("VolTicksPOC2")
        base = idy.kernel_id("VolTicksPOC2", src)
        mut = dict(src)
        mut[dep] = mut[dep] + b"\n# x\n"
        assert idy.kernel_id("VolTicksPOC2", mut) != base, f"dep {dep} no afecta"


def test_session_dep_only_in_session_kernels():
    # sessions.py es dependencia de HFTZones2/aVolCellPOI2, no de Gaps2.
    assert "sessions.py" in idy.kernel_sources("HFTZones2")
    assert "sessions.py" in idy.kernel_sources("aVolCellPOI2")
    assert "sessions.py" not in idy.kernel_sources("Gaps2")
    assert "sessions.py" not in idy.kernel_sources("VolTicksPOC2")


# --------------------------- config_id ------------------------------------- #
def test_config_id_canonical_equivalence():
    kid = idy.kernel_id("Gaps2")
    # {min_gap_ticks:5} (== default) y el dict con TODOS los defaults explícitos
    # deben dar el MISMO config_id.
    from edgelab.bridge.indicators import gaps2
    partial = idy.config_id("Gaps2", {"min_gap_ticks": 5}, "time_1", "UTC", kid)
    full = idy.config_id("Gaps2", dict(gaps2.DEFAULTS), "time_1", "UTC", kid)
    empty = idy.config_id("Gaps2", {}, "time_1", "UTC", kid)
    assert partial == full == empty


def test_config_id_float_int_equivalence():
    kid = idy.kernel_id("VolTicksPOC2")
    # 99.5 y "99.5" y 99.5 deben canonicalizar igual; export_floor 95 vs 95.0.
    a = idy.config_id("VolTicksPOC2", {"detection_percentile": 99.5, "export_floor_percentile": 95}, "time_1", "UTC", kid)
    b = idy.config_id("VolTicksPOC2", {"detection_percentile": "99.5", "export_floor_percentile": 95.0}, "time_1", "UTC", kid)
    assert a == b


def test_config_id_changes_on_real_param_change():
    kid = idy.kernel_id("Gaps2")
    base = idy.config_id("Gaps2", {}, "time_1", "UTC", kid)
    assert idy.config_id("Gaps2", {"min_gap_ticks": 8}, "time_1", "UTC", kid) != base
    assert idy.config_id("Gaps2", {}, "tick_25", "UTC", kid) != base      # bar_key
    assert idy.config_id("Gaps2", {}, "time_1", "America/Argentina/Buenos_Aires", kid) != base
    # distinto kernel_id -> distinto config_id
    assert idy.config_id("Gaps2", {}, "time_1", "UTC", "otro_kid") != base


# --------------------------- run_id / zone_key ----------------------------- #
def test_run_id_and_zone_key_deterministic_and_unique():
    r1 = idy.run_id("ds1", "cfgA", "2025-08-01", "2025-08-02")
    assert r1 == idy.run_id("ds1", "cfgA", "2025-08-01", "2025-08-02")
    assert r1 != idy.run_id("ds1", "cfgB", "2025-08-01", "2025-08-02")
    # zone_key global: dos runs jamás colisionan aunque compartan geometría
    z_a = idy.zone_key(r1, 1, 10, 1000, 200, 205, "bull")
    z_b = idy.zone_key("otro_run", 1, 10, 1000, 200, 205, "bull")
    assert z_a != z_b
    assert z_a == idy.zone_key(r1, 1, 10, 1000, 200, 205, "bull")


# --------------------------- validate_params ------------------------------- #
def test_validate_rejects_unknown():
    errs = idy.validate_params("Gaps2", {"foo": 1})
    assert any("inexistente" in e for e in errs)


def test_validate_rejects_wrong_type():
    errs = idy.validate_params("Gaps2", {"min_gap_ticks": "alto"})
    assert any("tipo inválido" in e for e in errs)
    # 3.5 no es un int válido
    assert idy.validate_params("Gaps2", {"min_gap_ticks": 3.5})


def test_validate_rejects_out_of_range_and_choice():
    assert any("max" in e for e in idy.validate_params("Gaps2", {"partial_fill_pct": 150}))
    assert any("min" in e for e in idy.validate_params("Gaps2", {"min_gap_ticks": 0}))
    assert any("choices" in e for e in
               idy.validate_params("VolTicksPOC2", {"invalidation_mode": "Nope"}))


def test_validate_rejects_forbidden_and_visual():
    errs = idy.validate_params("BigTrap2", {"TopPercentFilter": 10})
    assert any("forbidden" in e for e in errs)


def test_validate_rejects_uncovered_offline_filter():
    # detection_percentile 90 con export_floor 95 -> no re-filtrable desde OBS
    errs = idy.validate_params("VolTicksPOC2",
                               {"detection_percentile": 90, "export_floor_percentile": 95})
    assert any("no cubierto" in e for e in errs)
    # cubierto (>=) -> válido
    assert not idy.validate_params("VolTicksPOC2",
                                   {"detection_percentile": 99.0, "export_floor_percentile": 95})


def test_validate_accepts_valid():
    assert idy.validate_params("Gaps2", {"min_gap_ticks": 8, "export_floor_ticks": 2}) == []


def test_canonicalize_rejects_nonanalytic():
    with pytest.raises(ValueError):
        idy.canonicalize_params("BigTrap2", {"TopPercentFilter": 10})
    with pytest.raises(KeyError):
        idy.canonicalize_params("Gaps2", {"foo": 1})
