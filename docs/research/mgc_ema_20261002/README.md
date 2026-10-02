# MGC EMA 200/500/2000 — rerun 2026-10-02

## Estado

Corrida **discovery-only**. El holdout con `trade_date >= 20260401` permanece cerrado. Este directorio registra código, política, hashes y resultados pequeños; los Parquet/NPY/NPZ regenerables quedan fuera de Git.

## Fuente y auditoría

- Dataset privado: `nicolasbuttaro/edgelab-mgc-nt8-raw-parquet-20261002`.
- Raw: 90,076,982 filas en contratos separados. `MGC_08-25` sólo contiene 3 filas; faltan `MGC_10-25` y `MGC_10-26`; el origen declara reloj UTC y canonicalización todavía no certificados.
- La unicidad correcta es `(ts_utc_ns, sequence)`. Repeticiones de price/bid/ask/volume con secuencia distinta son eventos válidos y no se deduplican.
- Tick size: 0.1.

## Continuo causal

`databuild/build_mgc_canonical.py` aplica la política vigente de EdgeLab:

1. trade date CME en `America/Chicago`, sesión 17:00–16:00 CT;
2. contrato de D decidido sólo con volumen de la sesión completa D-1;
3. líder estricto, roll monotónico y sin vuelta atrás;
4. precios reales, sin back-adjustment;
5. reset explícito de estado en cada roll;
6. holdout cerrado por trade date.

Resultado canónico:

- 56,575,239 ticks discovery;
- SHA-256 `87aac766d630fe3e347615ddedc640c2f9ba919cae12d3337f5b8d202e3d44b3`;
- roll manifest `70a813b7b7aa7bb43b9de70f082e4981a4e8aa15e85bcaee4f415ddc040e060d`;
- 0 inversiones temporales; 0 duplicados de clave.

Régimen:

| Contrato | Inicio | Fin exclusivo | Ticks |
|---|---:|---:|---:|
| MGC_12-25 | 20251008 | 20251126 | 18,642,180 |
| MGC_02-26 | 20251126 | 20260129 | 16,490,374 |
| MGC_04-26 | 20260129 | 20260330 | 20,793,514 |
| MGC_06-26 | 20260330 | holdout | 649,171 |

## Arrays versionados

- Barras 25T: 2,262,954; sólo se descartan 1,389 ticks de colas incompletas de sesión.
- Cada `.npy` tiene dtype, shape y SHA-256 en `manifest.json` del artefacto local.
- IDs observados en esta corrida:
  - barras: `7655ce91a20b897dc45b`;
  - ticks: `b8e5942297c925d6ff9b`.
- Los builders escriben artefactos inmutables derivados del hash de fuente/política/código y un puntero `LATEST` local.

## Señal reconstruida

El snapshot del repositorio no contenía el runner MGC original ni el registro exacto de sus 126 celdas. La definición que reproduce la escala reportada (1,728 señales viejas; 1,641 con el continuo corregido) es:

- EMA 200 cruza EMA 500;
- EMA 500 debe estar del mismo lado de EMA 2000;
- warm-up de 2,000 barras por contrato;
- decisión al cierre de la barra; entrada causal posterior.

No se inventó el grid faltante. Se preregistró antes de mirar resultados un núcleo auditable de 42 celdas: dirección normal/inversa × SL {100,150,200} × TP {150,200,250,300,350,400,450}, entrada inmediata y BE apagado.

## Ejecución y resultados

Screening de barra: siguiente apertura 25T a ask/bid, stop-first ante ambigüedad, TP con trade-through de 1 tick, 0.5 tick RT de fees, una posición a la vez y flat forzado en roll.

Finalistas tick-exact con el mismo contrato causal de EdgeLab:

| SL | TP | Trades | Neto ticks | Ticks/trade | Win rate |
|---:|---:|---:|---:|---:|---:|
| 200 | 300 | 713 | 6,252.5 | 8.77 | 42.22% |
| 200 | 400 | 623 | 9,920.5 | 15.92 | 36.44% |
| 200 | 450 | 592 | 8,535.0 | 14.42 | 33.45% |

El mejor screening fue TP 400, no TP 450. Ninguna cifra abre el holdout ni constituye validación final.

## Gauntlet

Sobre el grid bar-level de 42 celdas:

- mirror signal: PASS;
- prefix causality: PASS;
- sintéticos del kernel stateful: PASS;
- replay Python independiente: PASS en 200 trades de cada uno de 3 finalistas;
- PBO/CSCV: 0.2897 (252 splits);
- DSR > 0.95: 0/42;
- BH q < 0.05: 0/42;
- TP400 bootstrap por sesión positivo: 92.895%;
- TP400 OOS cronológico 30% de discovery: +1,729.5 ticks bar-level;
- febrero 2026 negativo y MGC_06-26 levemente negativo (muestra muy corta).

Conclusión: sigue siendo candidato de investigación, **no edge validado**. Falla aún evidencia ajustada por multiplicidad (DSR/BH) y estabilidad completa por contrato/régimen. El holdout no debe abrirse.

## Rendimiento

En la máquina de 2 CPU y sin GPU usada en esta corrida:

- barras 25T por streaming/vectorización: 6.7 s;
- screening 42 celdas con Numba: 5.6 s;
- arrays tick-exact: 23.9 s;
- replay tick-exact de 3 finalistas: 1.5 s;
- gauntlet 42 celdas: 2.0 s.

El runner preliminar tardaba ~39m22s porque reconstruía/reprocesaba caminos dentro de bucles Python por celda. La nueva ruta paga I/O y features una vez y reserva el tick replay para finalistas.

## Reproducción

Desde el root, con el raw privado ya descargado en `/data/raw/mgc`:

```bash
python databuild/build_mgc_canonical.py
python tools/build_mgc_25t_arrays.py
python tools/run_mgc_ema_screen.py
python tools/build_mgc_tick_arrays.py
python tools/run_mgc_tick_exact_finalists.py
python tools/validate_mgc_ema.py
python tools/verify_mgc_stateful_kernel.py
```

## Pendientes obligatorios

1. Recuperar el registro original de 126 configuraciones (pullback/timeout/BE). No reconstruirlo post-hoc.
2. Convertir ese registro a un JSON inmutable con hash y rerun sin cambiar parámetros.
3. Implementar pullback/BE en el motor compartido, con sintéticos y doble simulador, no dentro de la estrategia.
4. Ejecutar MCPT del pipeline completo; SPA/Reality Check sobre la familia registrada.
5. Aumentar cobertura de contratos/regímenes y sólo después decidir si se abre una única vez el holdout.
