# Campañas de grilla (datos, no código)

Un JSON por campaña. `edgelab/autopilot/generate.py::campanas_grilla` lo convierte en candidata con RunSpec (kernel genérico,
decisión `escalera_v1`) y borrador de pre-registro. Campos obligatorios: `cid`, `titulo`, `experimento`, `kernel`, `fuente`,
`modo` (E0/DESC/REP), `desde`, `hasta`, `needs`, `n_trials`, `family`, `spec`, `justificacion_economica`, `como_podria_refutarse`.
Opcionales: `cortes`, `celdas` (REP: congelados), `extra_datasets`, `est_seconds`, `potencia`, `activa` (false = no compite).
Plantilla de los campos: `config/autopilot/grillas/PLANTILLA_GENERICA.json`. Test: `tests/test_autopilot_campanas_grilla.py`.
