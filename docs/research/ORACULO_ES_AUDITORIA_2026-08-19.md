# Auditoría del log SQLite antes de llamarlo oráculo — ES

- **2026-08-19** · artefacto: `docs/research/oraculo_es_auditoria.json`
- Snapshot congelado: `runs/hft_logger_snapshot.sqlite` · **566,3 MB** ·
  `sha256 0d03b30e543b9a06…`
- **Estado: `NO_ES_ORACULO_TODAVIA`**

---

## 1. El bloqueante: la atribución no es verificable desde los datos

Leyendo los `.cs`, **tres indicadores escriben la misma base**:

```
HFTZonesESPureV2   ->  C:\LoggerHFT\data\hft_logger.sqlite
HFTZonesNQPureV2   ->  el mismo archivo
HFTZonesNQPureV3   ->  el mismo archivo
```

Los tres hacen `CREATE TABLE IF NOT EXISTS hft_zones` con **el mismo esquema**, y la
tabla **no tiene ninguna columna que identifique al escritor**.

Que las 2.742 filas de `ES 06-26` vengan de `HFTZonesESPureV2` es una inferencia sobre
qué gráfico estaba abierto — **no un hecho del artefacto**.

**Qué haría falta:** corrida controlada con **sólo** ese indicador sobre ES, `DbPath` a
un archivo **nuevo y vacío**, los 29 parámetros efectivos registrados, versión de NT8,
plantilla de sesión, huso y modo de cálculo, y hash del `.cs` y del archivo **antes** de
extraer.

## 2. Lo que sí quedó verificado

| chequeo | resultado |
|---|---|
| snapshot consistente (API `backup`, no `cp` sobre WAL) | ✓ hasheado |
| firmas duplicadas `(start_ts, upper, lower, dir)` | **0** |
| zonas **vivas al cruzar el firewall** | **0** |
| zonas post-firewall en `ES 06-26` | **0** |
| **retrocesos de `start_ts`** | **3** ⚠ |
| huecos de `id` | 22 (esperable: la tabla es compartida) |

Los **3 retrocesos** indican reinicio del indicador o recarga histórica sobre la misma
base. No invalidan las filas, pero confirman que la base **acumula corridas**.

Sobre el firewall: `start_ts < cutoff` **no alcanza** en general —una zona puede empezar
antes y terminar después—, pero en `ES 06-26` el chequeo da **0 vivas al corte**, así
que acá no aplica. En `ES 09-26` sí habría que censurarlas.

## 3. El número que decide la prioridad: **13 sesiones**

| contrato | zonas | pre-firewall | **sesiones** | z/sesión | MDE |
|---|---|---|---|---|---|
| **ES 06-26** | 2.742 | 2.742 | **13** | 211 | **55,7 pp** |
| ES 09-26 | 12.999 | 12.939 | **8** | 1.617 | 71,0 pp |
| ES SEP26 | 6.110 | 5.673 | **2** | 2.836 | 142,0 pp |
| MES 06-26 | 2.237 | 2.237 | 12 | 186 | 58,0 pp |
| **unión ES** | | | **23** | | **41,9 pp** |

Rango: **2026-05-25 → 2026-06-30**.

**2.742 zonas no son 2.742 observaciones.** Con `Δ ≈ 0,10·√(403/n)` sobre sesiones, la
unión de todos los contratos de ES da **23 sesiones → MDE 41,9 pp**. Para comparar: el
censo de H-Z2A sobre 6E corrió con **228 sesiones → 13,3 pp**.

**Un efecto económico realista vive en 2–5 pp.** Con 23 sesiones no se detecta nada, ni
siquiera un efecto enorme.

## 4. Consecuencia para el orden de trabajo

El censo descriptivo (paso 2 del auditor) **sí corre**: contar zonas por sesión, altura,
duración, dirección, solape y concentración no necesita potencia estadística, y es lo
que dice si el objeto tiene estructura.

Lo que **no** corre con este material es el paso 4 —reacción al primer toque,
probabilidad de rechazo, comparación con controles—. No por el STOP, sino **por N**.

**Lo que desbloquea el análisis no es portar 829 líneas: es más historia.** El logger
tiene 13 sesiones porque se corrió unos días. Dejarlo corriendo, o recargar histórico
sobre un `DbPath` limpio, multiplica el N sin escribir una línea de Python.

**Aporte al referente:** evita gastar el port completo y una campaña sobre una población
de 23 sesiones, donde ningún resultado —positivo o negativo— sería concluyente.
