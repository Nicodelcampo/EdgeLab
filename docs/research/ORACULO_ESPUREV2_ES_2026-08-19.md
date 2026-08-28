# Oráculo controlado de HFTZonesESPureV2 sobre ES

- **2026-08-19** · estado **`ORACULO_CONTROLADO`**
- Snapshot: `runs/oraculo_espurev2_ES_snapshot.sqlite` · 25,4 MB · `sha256 bece887455c0347b3dd352edf487c49faf1e5dfbac796989f418c49ca4944d64`
- Manifiesto: `docs/research/oraculo_espurev2_es_auditoria.json`

## Cómo se generó

Corrida controlada en NT8: **`DbPath` nuevo y vacío**, **un solo indicador escribiendo**.
Eso resuelve el bloqueante del log compartido `hft_logger.sqlite`, donde tres
indicadores (`HFTZonesESPureV2`, `HFTZonesNQPureV2`, `HFTZonesNQPureV3`) escriben la
**misma tabla con el mismo esquema y sin columna de escritor**.

`EnableFlowLog` apagado · `Tick Replay` off · `Calculate: On bar close` ·
`Trading hours: <Use instrument settings>` · `Break at EOD` on ·
`Max bars look back: 256` · **parámetros = defaults del `.cs`, sin modificar**.

Todas las cargas con `End date` dentro de la vida de cada contrato y **anterior al
holdout**.

## Contenido

| contrato | zonas | sesiones | rango |
|---|---|---|---|
| ES 03-26 | 10378 | 54 | 20251222 → 20260309 |
| ES 06-26 | 11653 | 53 | 20260305 → 20260617 |
| ES 09-26 | 1832 | 23 | 20260506 → 20260630 |
| **unión** | **23863** | **120** | |

## Verificaciones

| chequeo | vieja (compartida) | **nueva (controlada)** |
|---|---|---|
| atribución del escritor | no verificable | **un solo indicador** |
| retrocesos de `start_ts` | 3 | **0** |
| huecos de `id` | 22 (mayor 33.405) | **6 (mayor 2)** |
| firmas duplicadas | 0 | **0** |
| zonas post-firewall | 0 | **0** |
| zonas vivas al corte | 0 | **0** |
| `end_ts` NULL | 0 | **0** |

Los **0 retrocesos** y los huecos de a lo sumo 2 confirman una escritura secuencial
única: no hay recargas ni corridas mezcladas.

## Potencia

**120 sesiones** contra las 23 del log viejo. Con la heurística de P-47
(`Δ ≈ 0,10·√(403/n)`), el MDE pasa de **41,9 pp a 18,3 pp**.

Sigue sin alcanzar para un efecto de 2–5 pp, pero **habilita el censo descriptivo y el
piloto** — que es lo que el orden del auditor pone antes de cualquier medición
económica.

## Lo que este oráculo NO tiene

`hft_zones` guarda **el barrido**, con duraciones de 0–500 ms. **No hay toques ni
invalidación**: el ciclo de vida de la zona no está en esta tabla. El análisis de
«primer regreso a la zona» hay que construirlo cruzando esta geometría con los ticks
del parquet.

**Aporte al referente:** por primera vez hay una población de zonas de este indicador
con procedencia verificable y sin contaminación de otros escritores. Sin eso, cualquier
medición posterior habría sido sobre un objeto de autoría desconocida.
