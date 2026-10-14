"""Construcción reproducible de la release líquida (un Parquet de ticks por activo) desde los exports NT8.

Plan y criterios: docs/infra/LOCAL_AGENT_LIQUID_DATA_REPAIR_HANDOFF_20261014.md. Este paquete NO certifica datos:
produce evidencia (escaneos, censos, selección causal) y un producto CANDIDATE hasta que Nico lo revise.
"""
