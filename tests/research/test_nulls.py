from __future__ import annotations

import pytest

from edgelab.research.nulls import (
    CellKey,
    NullGenerator,
    NullGeneratorError,
    NullManifest,
    PlaceboResampleWithinSession,
)


def manifest(**updates):
    data = dict(
        null_id="explore-placebo-v1",
        generator_version="1.0.0",
        null_hypothesis="las anclas reales no superan placebos elegibles",
        exchangeability_assumption="intercambiabilidad dentro de sesion y estrato",
        seed=20260803,
        n_replicates=20,
    )
    data.update(updates)
    return NullManifest(**data)


def generator(**updates):
    data = dict(
        manifest=manifest(),
        session_ids=["d1", "d2", "d3"],
        real_counts={("d1", "a"): 2, ("d1", "b"): 1, ("d2", "a"): 1},
        candidate_pools={
            ("d1", "a"): [1.0],
            ("d1", "b"): [10.0],
            ("d2", "a"): [-1.0],
        },
    )
    data.update(updates)
    return PlaceboResampleWithinSession(**data)


def test_interfaz_abstracta_no_se_instancia():
    with pytest.raises(TypeError):
        NullGenerator()


def test_preserva_conteos_por_sesion_y_estrato():
    draw = generator().generate(0)
    got = {(c.key.session_id, c.key.stratum_id): len(c.values) for c in draw.cells}
    assert got == {("d1", "a"): 2, ("d1", "b"): 1, ("d2", "a"): 1}
    assert draw.clusters[0].n_trades == 3
    assert draw.clusters[1].n_trades == 1
    assert draw.clusters[2].n_trades == 0
    assert draw.theta_trade == pytest.approx(11 / 4)


def test_sesiones_sin_senales_se_conservan():
    draw = generator().generate(0)
    zero = next(c for c in draw.clusters if c.session_id == "d3")
    assert zero.n_trades == 0 and zero.pnl_net == 0


def test_misma_config_seed_y_replica_es_byte_determinista():
    a = generator(); b = generator()
    assert a.generator_digest == b.generator_digest
    assert a.generate(7) == b.generate(7)
    assert a.run() == b.run()


def test_digest_cambia_si_cambia_el_pool():
    a = generator()
    b = generator(candidate_pools={
        ("d1", "a"): [1.0, 2.0],
        ("d1", "b"): [10.0],
        ("d2", "a"): [-1.0],
    })
    assert a.generator_digest != b.generator_digest


def test_celdas_de_counts_y_pools_deben_coincidir_exactamente():
    with pytest.raises(NullGeneratorError, match="no coinciden"):
        generator(candidate_pools={("d1", "a"): [1.0]})


def test_pool_vacio_con_conteo_positivo_falla():
    with pytest.raises(NullGeneratorError, match="pool vacio"):
        generator(candidate_pools={
            ("d1", "a"): [], ("d1", "b"): [1.0], ("d2", "a"): [1.0]})


def test_celdas_fuera_del_calendario_fallan():
    with pytest.raises(NullGeneratorError, match="fuera del calendario"):
        PlaceboResampleWithinSession(
            manifest(), session_ids=["d1"],
            real_counts={("d2", "a"): 1},
            candidate_pools={("d2", "a"): [1.0]})


def test_booleanos_y_no_finitos_no_son_outcomes():
    with pytest.raises(NullGeneratorError):
        generator(candidate_pools={
            ("d1", "a"): [True], ("d1", "b"): [1.0], ("d2", "a"): [1.0]})
    with pytest.raises(NullGeneratorError):
        generator(candidate_pools={
            ("d1", "a"): [float("nan")], ("d1", "b"): [1.0],
            ("d2", "a"): [1.0]})


def test_manifest_rechaza_estadistico_o_cluster_distinto():
    with pytest.raises(NullGeneratorError, match="test_statistic"):
        manifest(test_statistic="sum_pnl")
    with pytest.raises(NullGeneratorError, match="cluster_unit"):
        manifest(cluster_unit="trade")


def test_indice_de_replica_fuera_de_rango_falla():
    g = generator()
    with pytest.raises(NullGeneratorError, match="fuera de rango"):
        g.generate(-1)
    with pytest.raises(NullGeneratorError, match="fuera de rango"):
        g.generate(g.manifest.n_replicates)


def test_clave_de_celda_es_explicita():
    assert CellKey("d1", "vol-high") < CellKey("d2", "vol-low")
    with pytest.raises(NullGeneratorError):
        CellKey("", "a")


def test_representaciones_equivalentes_no_se_pisan_en_silencio():
    key = CellKey("d1", "a")
    with pytest.raises(NullGeneratorError, match="duplicada"):
        PlaceboResampleWithinSession(
            manifest(), session_ids=["d1"],
            real_counts={key: 1, ("d1", "a"): 1},
            candidate_pools={key: [1.0]})
