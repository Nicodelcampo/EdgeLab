# Estándar transversal de régimen de contratos — v1

**Estado:** `CODE_READY_NOT_RUN`  
**Policy ID:** `previous_complete_session_volume_leader_monotonic_v1`

## Problema que resuelve

Un archivo de un vencimiento no equivale al período en que ese contrato habría
sido operable. La capa de régimen se ejecuta antes de construir barras,
indicadores, zonas, episodios u outcomes. Ningún análisis formal puede mezclar
contratos sin declarar qué contrato era líquido en cada trade date CME.

## Regla congelada

Para el trade date CME `D` se usan únicamente volúmenes de la sesión completa
anterior `D-1`:

1. agregar `sum(volume)` por raíz, contrato y trade date;
2. considerar los contratos cubiertos y de vencimiento igual o posterior al
   vigente;
3. si un contrato posterior fue líder estricto de volumen y superó al vigente,
   cambiar al inicio de `D`;
4. si hay empate, conservar el vigente;
5. una vez avanzado el vencimiento, nunca volver atrás.

Esto es un cruce de una sesión con lag causal. El volumen final de `D` nunca
elige el contrato usado dentro de `D`.

### Fundamento externo

- CME permite el roll en cualquier momento y publica una fecha consuetudinaria
  para índices; después de ella el segundo vencimiento suele ser el lead month:
  https://www.cmegroup.com/trading/equity-index/rolldates.html
- Databento define el continuous por volumen mediante el ranking de la sesión
  anterior:
  https://databento.com/microstructure/continuous-contract
- Sierra Chart recomienda volume-based rollover para ES, NQ, YM, 6E y 6B, y
  advierte que datos diarios faltantes corrompen la fecha:
  https://www.sierrachart.com/index.php?page=doc/ContinuousFuturesContractCharts.html

Dos sesiones de confirmación o una razón 1,25 se rechazaron como default porque
mantendrían actividad en un contrato que ya dejó de ser el líder. Esas reglas
pueden existir después como sensibilidad, nunca reemplazar silenciosamente v1.

## Convenciones duras

```text
session = 17:00 CT D-1 hasta 16:00 CT D
maintenance = 16:00–17:00 CT
volume = suma de cantidad negociada, no cantidad de ticks
intervalo = [roll_in_trade_date, roll_out_trade_date)
price_adjustment = NONE_ACTUAL_TRADED_PRICES
state_boundary = RESET_AT_CONTRACT_ROLL
```

No se hace back-adjustment, ratio-adjustment ni blending. Para microestructura
se conservan precios realmente negociados. Zonas y estados del contrato viejo
no sobreviven al roll. Un outcome o una operación que cruce la frontera necesita
un contrato específico de roll separado; por defecto falla.

## Integridad del input

La cobertura debe ser rectangular por contrato: entre `first_trade_date` y
`last_trade_date` tiene que existir una fila diaria, incluso volumen cero. Una
fila faltante no significa cero. Si falta o la sesión no está certificada como
completa, la sesión siguiente queda `SOURCE_INCOMPLETE` e inelegible.

El primer día no tiene señal previa y queda `NO_PRIOR_SESSION`. El último tramo
queda `right_censored` hasta observar que un vencimiento posterior toma el
liderazgo. Los bordes se declaran; no se rellenan por calendario.

## Identidad obligatoria downstream

Cada tick, barra, bloque, zona, episodio y operación debe incluir:

```text
root
contract
trade_date
regime_id
roll_manifest_sha256
```

`assert_rows_follow_regime()` rechaza:

- contrato distinto del asignado;
- fecha inelegible;
- `regime_id` faltante o incorrecto;
- manifiesto de roll distinto;
- mezcla silenciosa de contratos.

Los run manifests deben copiar `manifest_sha256` en `roll_schedule_sha256`.

## Artefacto canónico

`contract_regime_manifest_v1` contiene:

- identidad de datasets y calendario;
- metadata y cobertura por contrato;
- asignación diaria causal;
- intervalos half-open;
- señal y razón de volumen observada;
- bordes censurados y diagnósticos;
- hash canónico del manifiesto.

## Consecuencia para el NQ 06-26 actual

El trace existente de aVolClusterPOI sólo contiene `NQ_06-26`. Sirve como
estudio provisional de ese archivo, pero por sí solo no permite demostrar el
roll-in desde `NQ_03-26` ni el roll-out hacia `NQ_09-26`. Para construir el
período operable exacto hacen falta los tres contratos con cobertura solapada y
sesiones completas certificadas.

EF0 puede inspeccionar el trace actual, pero ningún análisis continuo formal ni
EF1 multicontrato debe interpretar todo el rango de `NQ_06-26` como período
operable hasta producir el manifiesto de régimen.

## Orden de ejecución obligatorio

```text
P0/P1 integridad de parquets y sesiones
→ volumen diario por cadena de contratos
→ contract_regime_manifest_v1
→ selección/etiquetado de ticks
→ barras reiniciadas en roll
→ indicadores con estado reiniciado
→ análisis target-free
→ outcomes sólo bajo autorización separada
```

**Aporte al referente:** convierte “usar el contrato con liquidez” en una regla
causal, hasheada y verificable que todos los análisis deben heredar antes de
interpretar cualquier resultado.
