# Familia 6E-REGIMES: regímenes de liquidez en 6E (registro, 2026-09-24)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Estado:** REGISTRADA. Etapa 1 (target-free) congelada abajo **antes de medir**.
**Ledger propio:** `artifacts/hippocampus/regimes_6e_20260924.jsonl`. No hereda población, costos, resultados ni presupuesto de ninguna otra familia (BigTrap2, absorción L2, aVolClusterPOI).
**Autorización de Nico (chat, 2026-09-24):**
- (1) usar el L2 del 6E de julio a septiembre (holdout) **solo para validar el sustituto de profundidad, sin retornos**;
- (2) registrar esta familia y arrancar.

## Idea

En un mercado de **tick grande** como el 6E (spread de 1 tick el ~91 % de los trades), el precio cambia cuando se vacía la fila del mejor nivel. Cuánta liquidez hay en esa fila, y qué tan rápido se consume, define un **estado del mercado** que dura minutos u horas: un régimen. Se estudia el estado, no el trade suelto.

**Justificación económica:**
- La probabilidad y la velocidad de un cambio de precio dependen del tamaño de las filas (Cont y de Larrard 2013; Gould y Bonart 2016, desequilibrio de filas en tick grande).
- Un régimen de liquidez cambia tres cosas operables:
  - el costo y la probabilidad de llenado de una orden pasiva (pregunta M4 de la Fase 0 del 6E);
  - el tamaño razonable de stops;
  - si un movimiento tiende a seguir o a volver.
- El uso esperado es un **filtro o dimensionamiento por régimen**, no una señal de entrada aislada.

**Por qué ticks y no L2:**
- El L2 del 6E tiene 4 sesiones pre-holdout.
- Los ticks (`research-v2`) tienen ~230, del 25/07/2025 al 30/06/2026, con bid y ask en cada trade pero **sin tamaños de fila**.
- La familia usa un **sustituto de la profundidad calculable con ticks**, y el L2 se usa para **validar ese sustituto**.

## Datos

| Fuente | Rango | Uso |
|---|---|---|
| `E:\EdgeLab\data\nt8_research_v2\6E\*.parquet` (ticks con bid/ask) | 25/07/2025–30/06/2026 | Construir el sustituto y medir persistencia |
| `E:\l2_parquet\6E_09-26`, `6E_12-26`: 4 sesiones de junio | 25, 28, 29 y 30/06/2026 | Validar el sustituto; puente ticks↔L2 |
| Idem, julio–septiembre (**holdout**) | 01/07–22/09/2026 | **Solo** validar el sustituto, sin retornos (autorización 1). Cada corrida se asienta en `docs/holdout_access_log.md` vía `check_holdout(purpose="target_free_validation")` |

- **Contrato por día:** el que tiene más trades ese día (target-free).
- **Día de sesión:** la fecha de (hora de Chicago + 7 h), así la sesión CME de 17:00 a 16:00 CT cae en un solo día.
- **Reloj del L2 6E:** ART guardado como si fuera UTC. Para comparar con ticks se suma 3 h, y se verifica con la correlación cruzada de trades por minuto (tiene que dar el máximo en 0 después de corregir).

## Población: espacio enumerado antes de elegir

| Alternativa | Qué es | Etapa 1 |
|---|---|---|
| (a) Estado a reloj fijo | El sustituto en bloques de 15 min, todo el día | **ELEGIDA**: la mayor cantidad de observaciones y no requiere umbrales |
| (b) Estado a reloj de volumen | Bloques de N contratos | Enumerada, no medida |
| (c) Episodios de régimen | Tramos entre cruces de umbral | Enumerada: requiere umbrales, se congelan en la etapa 2 |
| (d) Transiciones de régimen | Eventos de cambio | Enumerada: etapa 2 |
| (e) Régimen de la sesión | Un valor por día | Enumerada: variante de baja potencia |
| (f) Condicionado por franja | Asia / Londres / Nueva York | Se reporta como desglose, no como población aparte |

**Cómo podría refutarse la población elegida:** si toda la variación del sustituto es el perfil horario, el "régimen" es solo el reloj y (f) reemplaza a (a). Eso lo mide V3.

## Etapa 1: target-free, congelada

**Sustituto (P1, "fila aparente"):** en cada bloque de 15 min, contratos operados ÷ max(1, cambios del precio medio). El precio medio se toma del bid/ask en cada trade, y un cambio es un trade cuyo (bid+ask) difiere del anterior. Se usa log(P1). Un bloque sin trades queda indefinido y se cuenta aparte. Se excluyen los bloques que tocan la pausa diaria (16:00–17:00 CT).

**Descriptivas (no deciden nada):** trades por minuto, desequilibrio de agresor y rango del bloque.

**Verdad L2:**
- **T1** = promedio de (tamaño del mejor bid + tamaño del mejor ask) / 2 en las fotos de 1 s del bloque.
- **T2** = lo mismo con 5 niveles.

Sesiones con defectos por `l2_phase0.defect_reasons` quedan afuera y se cuentan.

**Pruebas, con umbrales fijados ahora:**
- **V1, validez del sustituto:** Spearman por sesión entre log P1 (calculado con los trades del mismo archivo L2) y T1, sobre los bloques de 15 min.
  - **VALID** si la mediana entre sesiones es ≥ 0,5; **WEAK** entre 0,3 y 0,5; **INVALID** si es < 0,3.
  - Se publican la distribución completa, la fracción de sesiones con ρ > 0, el resultado con T2 y una versión sin perfil horario (V1b: residuos contra la mediana por hora de la propia muestra).
- **V2, puente ticks↔L2** (4 sesiones de junio): Spearman por sesión entre log P1 de `research-v2` y log P1 del archivo L2, en los mismos bloques UTC.
  - **PASS** si todas dan ≥ 0,9. Si no, los dos feeds no miden lo mismo, y eso **bloquea** usar los ticks en lugar del L2.
- **V3, persistencia** (ticks pre-holdout, ~230 sesiones): autocorrelación dentro de la sesión de log P1 **sin el perfil horario** (mediana por hora de Chicago, calculada con los mismos ticks pre-holdout), a 1, 4 y 16 bloques (15 min, 1 h, 4 h).
  - Se publica la media entre sesiones con IC bootstrap por sesión.
  - **Hay régimen más allá del reloj** si la autocorrelación a 1 h, sin perfil horario, tiene IC inferior ≥ 0,3.
  - Si el IC superior queda < 0,1, **no hay régimen**: la variación es reloj más ruido, y la familia se reduce a (f).
  - La versión con perfil horario incluido se publica al lado.
  - Sensibilidad: bloques de 5 y 60 min, publicados todos, sin elegir el mejor.

**Cómo se refuta la etapa 1:**
- V1 INVALID → los ticks no sirven para medir liquidez en 6E y la familia no puede usar la historia larga.
- V2 FAIL → hay que investigar por qué dos vías de NT8 difieren antes de seguir.
- V3 sin régimen → queda solo el perfil horario.

## Particiones para la etapa 2 (declaradas ahora, antes de mirar retornos)

Regla de `PARTICIONES_Y_POTENCIA_L2_20260924.md`: con ~230 sesiones conviene 3/4 y 1/4, y la confirmación queda con ~60 sesiones.

| Partición | Rol | Días (de sesión) |
|---|---|---|
| `P-6E-REG-EXP` | EXPLORATION | 25/07/2025–31/03/2026 |
| `P-6E-REG-CONF` | CONFIRMATION_RESERVED | 01/04/2026–30/06/2026 |
| `P-6E-REG-L2VAL` | FUTURE (sin retornos) | Las 4 sesiones L2 de junio, ids `6E-L2:<fecha>` |
| `P-6E-REG-L2HOLDOUT` | FUTURE (sin retornos, holdout) | L2 del 01/07 al 22/09, ids `6E-L2:<fecha>` |

La etapa 2 (información condicional al régimen) mira retornos: **pasa por el STOP** con manifiesto propio.
