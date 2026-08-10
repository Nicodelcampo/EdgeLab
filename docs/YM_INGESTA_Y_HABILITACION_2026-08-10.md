# YM — ingesta de ticks y habilitación en el bridge

**Fecha** 2026-08-10 · **NORTH_STAR** sha256 `21bb3b01a33e2b37…`
**Origen** Nico descargó 5 archivos `.Last.txt` de YM (Mini Dow, CBOT/CME) a
`data/nt8/YM/` y pidió procesarlos.

---

## 1. Qué se hizo

### 1.1 Ingesta — herramienta existente, sin modificar

`tools/build_nt8_ticks.py`, la misma que produjo todos los parquets canónicos
existentes (6E, ES, NQ, GC, MES, MGC, MNQ), corrida sobre los 5 contratos:

```
tick_size = 1.0   (punto de índice, spec estándar CME del Mini Dow)
out       = data/nt8/YM_parquet/
```

| contrato | ticks | no parseadas | desorden | unclassified |
|---|---|---|---|---|
| YM 09-25 | 1.551.901 | 0 | 0 | 14 |
| YM 09-26 | 3.220.596 | 0 | 0 | 2 |
| YM 12-25 | 5.798.136 | 0 | 0 | 80 |
| YM 03-26 | 6.460.091 | 0 | 0 | 97 |
| YM 06-26 | 6.213.697 | 0 | 0 | 77 |
| **TOTAL** | **23.244.421** | **0** | **0** | 270 (0,001 %) |

Los propios controles del constructor (grid de precio, libro cruzado) pasaron
sin excepción — `FAIL-LOUD` no se disparó en ningún archivo.

### 1.2 Verificación empírica del huso horario — no heredada, chequeada

El código declara offset 0 (`ts_utc_ns = ts_local_ns`) y advierte explícitamente
que esa asunción **"NO se re-verifica acá"** por instrumento
(`build_nt8_ticks.py`, contrato §2). Antes de confiar en ella para YM se buscó
el gap de fin de semana en los datos crudos:

```
cierre   2025-08-15 20:59:59  ->  reapertura 2025-08-17 22:00:00
cierre   2025-08-29 20:59:59  ->  reapertura 2025-08-31 22:00:00
```

En horario de verano (CDT, UTC−5), eso es **16:00 CT viernes / 17:00 CT
domingo** — los horarios reales de cierre y reapertura de CME. La asunción
queda verificada para YM, no transplantada de 6E sin control.

*Límite declarado*: el chequeo se hizo sobre semanas de agosto-septiembre 2025,
todas en CDT. No se verificó ningún cruce de frontera de DST — si hiciera falta
usar datos de invierno, ese cruce debería revisarse aparte.

### 1.3 Habilitación en el bridge — cambio de código, con tu OK explícito

El parquet se generaba bien pero `load_canonical_parquet` fallaba: el catálogo
de instrumentos del bridge sólo tenía `6E`. Es código F1/F2
(`edgelab/data/nt8_contract.py`, `edgelab/bridge/ticks.py`), protegido por
`CLAUDE.md`, así que se preguntó antes de tocarlo. Con el OK, cambio **aditivo**
(no se tocó la entrada de `6E`):

```python
# edgelab/data/nt8_contract.py
YM = InstrumentSpec(symbol="YM", tick_size=1.0, tick_value=5.00, multiplier=5.0)
# tick_value = tick_size * multiplier (1.0 * 5.0 = 5.00) -- misma formula que 6E

# edgelab/bridge/ticks.py
INSTRUMENT_CATALOG = {"6E": SIX_E, "YM": YM}
```

Verificado: `load_canonical_parquet` carga YM correctamente (secuencia
monótona, rango de precio 44.642–46.379 puntos, rango de fechas
2025-08-14→2026-06-30 a través de los 5 contratos). Suite completa:
**799 passed**, mismas 2 fallas preexistentes y no relacionadas (ver §3).

### 1.4 Registro de procedencia

`tools/manifiesto_datos.py --emitir` — fusiona, no reemplaza (la guardia de
angostamiento arreglada el 2026-08-09 sigue vigente y se re-verificó con su
propia suite: `tests/test_manifiestos_no_se_angostan.py`, 10/10). Los 5
archivos YM quedan declarados en `docs/datos_manifiesto.json`; los 6 archivos
`6E_dirty_*` que esta máquina no tiene se conservaron, no se borraron.

---

## 2. Qué NO se hizo — deliberadamente, y por qué

**No se corrió BigTrap2 (ni ningún indicador) sobre YM.** Habilitar la carga
de ticks es un prerequisito, no un análisis. Ninguno de los hallazgos de hoy
(F0.2, F1.1, F1.2, F1.3, F2, F0.3) se repitió sobre este instrumento.

**No se agregó YM al calendario de research (`dias_research()`).** Mismo
bloqueo que ya se había identificado hoy para ES/NQ (`REGISTRO_NO_MEDIDO_
2026-08-10.md` §2.5): el universo de sesiones de estudio está definido en un
archivo que enumera contratos por nombre, y extenderlo es una decisión de
población que la regla nueva de `CLAUDE.md` exige justificar por escrito antes
de tomar — no se resuelve de paso. **YM se suma a ES/NQ en la misma cola.**

**No se validó paridad NT8↔Python para YM.** Los oráculos de paridad son pares
(indicador, ventana, parámetros) contra un `.cs` específico — no existen
oráculos para YM todavía. Eso requeriría exports nuevos desde NT8, y es un
trabajo aparte.

**No se tocó nada del holdout.** Las fechas de los 5 contratos van desde
2025-08-14 hasta dentro del rango research (el archivo 06-26 llega hasta
2026-06-30, verificado abajo) — pero como YM no está en `dias_research()`,
ningún análisis puede leerlo todavía sin pasar por el firewall que todos los
módulos de hoy ya traen (`assert peor <= MAX_FECHA`).

```python
# verificado: rango real de fechas del contrato mas nuevo
>>> tk.ts_ns.max() -> 2026-06-30 (dentro de research, no toca el sello)
```

---

## 3. Hallazgo colateral, marcado aparte y no mezclado con esto

Al correr la suite completa aparecieron 2 fallas **preexistentes, confirmadas
no relacionadas** con este trabajo (se revirtió el cambio de catálogo con
`git stash` y las mismas 2 fallas persistieron idénticas): el kernel Python de
BigTrap2 declara `version=2.2` y `nt8/BigTrap2.cs` está en `version=2.5.1`.

Es potencialmente serio — si 2.5.1 cambió semántica real del indicador, la
paridad NT8↔Python vigente (y por lo tanto H1 y toda la tanda de hoy) estaría
validada contra una versión vieja del kernel. **No se investigó ni se tocó**:
se marcó como tarea aparte (`task_cd68069a`) para no mezclar un hallazgo de
esa magnitud con una tarea de ingesta de datos.

---

## Aporte al referente

YM queda con datos ingeridos, verificados y cargables — la primera extensión
real del bridge más allá de 6E desde que existe el catálogo de instrumentos.
No amplía todavía el edge (no se corrió ningún análisis), pero reduce el costo
de la próxima decisión de potencia: sumar instrumentos deja de requerir escribir
un parser nuevo, y el bloqueo que queda (calendario de research) es el mismo,
ya identificado, que ES y NQ. Y de paso destapó una posible brecha de paridad
de versión que, si se confirma real, sería más importante que cualquier
resultado de esta sesión — motivo suficiente para haberla separado en vez de
resolverla de pasada.
