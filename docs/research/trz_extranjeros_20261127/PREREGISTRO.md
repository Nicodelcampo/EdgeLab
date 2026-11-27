# TRZ-EXTRANJEROS: T, R y Z de la cartera NT8, sin cambios, en índices extranjeros (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — antes de correr el motor sobre ningún índice extranjero. Lo único mirado: calidad y alineación horaria de las
velas preparadas (sin retornos).

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3:** réplica fuera de mercado con la regla congelada. **Familia:** `FUNDEDSYNC_TRANSFER` (hija de `FUNDEDSYNC`).
- **Pruebas:** 4. La canasta T+R+Z es la primaria; T, R y Z por separado son secundarias.

Cambio respecto a falla previa:
- T, R y Z se midieron sólo en índices de EE. UU. (NQ, ES, YM, RTY, EMD), y el vendedor vio 2020 → 2026-08. Su Sharpe deflactado
  (0,97) es una cota optimista, porque no se conocen sus pruebas.
- Lo que nadie miró, ni el vendedor ni EdgeLab, son **mercados distintos**: DAX, FTSE, EuroStoxx 50, CAC 40, Nikkei 225 y ASX 200.
- Es la misma prueba que confirmó a Carril 2 en `confianza_sin_forward_20261127` (H1), ahora para la intradía.

Antecedentes:
- `confianza_sin_forward_20261127/RESULTADO.md` y `DATOS_PARA_LO_PENDIENTE.md`;
- `VEREDICTO_M1_20261117.md` (T en EE. UU. desde 2012; R AtrPhase sólo NQ);
- `cartera_nt8_20261125/` (el arnés C# con paridad ≥ 98,8 % contra NT8).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7:
- K28: simulador calibrado. Se usa el arnés de la cartera, no un motor nuevo, y además se calibra el circuito de datos (abajo);
- K32: todo por EdgeLab;
- K36: causalidad. La escala usa sólo cierres del día anterior;
- K35–K39: R por operación sobre el riesgo inicial.

Potencia previa:
- Referencia: el R por operación de T, R y Z en NQ (2019–2026) es positivo, y cada índice tiene ≈ 15 años (2010/11 → 2026-09).
- Con un recorte de 50 % por cambio de mercado (`confianza_sin_forward`), la canasta de 6 índices con ≈ 180 meses cada uno da potencia
  > 0,8 si el Sharpe transferido es ≥ 0,35.
- Se publica el error estándar de cada serie.

Diagnóstico de mecanismo: sin grilla. Las configuraciones son las de producción del arnés: `T_stop100_BE15R_calFalse`,
`R_osc30_end660_ATR50` y `Z_b15_e20_eff40_ATR50`, con los parámetros de NQ. Se publican por módulo, por índice, por época y con costos ×2.

## Datos y transformaciones (declaradas antes; ninguna mira retornos)
- **Fuente:** M1 ASCII de HistData (CFD; EST fijo = UTC−5) de GRXEUR (DAX), UKXGBP (FTSE), ETXEUR (EuroStoxx), FRXEUR (CAC), JPXJPY
  (Nikkei) y AUXAUD (ASX), 2010 → 2026-09. `data/trz_extranjeros/PROCEDENCIA.json` tiene el sha256 de cada zip. Todo corta antes de
  la apertura de la sesión CME del 2026-10-01.
- **Hora:** cada día local se desplaza para que la apertura de contado local caiga a las 09:30 de Nueva York de esa fecha:
  - DAX, EuroStoxx y CAC: 09:00 local;
  - FTSE: 08:00;
  - Nikkei: 09:00;
  - ASX: 10:00.

  El huso horario y el horario de verano se toman por día.
- **Escala:** precio × (cierre de NQ del día hábil anterior / cierre del índice del día local anterior), constante dentro del día. Así
  los parámetros en puntos (el stop de T) son proporcionales.
- **Volumen:** 1 por vela, porque HistData no trae volumen; el VWAP de R pasa a ser un promedio en el tiempo.
- **Noticias:** sin veto de noticias de EE. UU.
- **Costo:** la fricción canónica de NQ (1,5455 puntos en escala NQ) restada al P&L de cada operación; estrés ×2.

## Compuerta de calibración (antes de leer cualquier índice extranjero)
- Se pasa el **CFD del Nasdaq 100 de HistData (NSXUSD)** por el mismo circuito: hora (desplazamiento 0), escala, volumen 1 y sin noticias.
- Se compara, módulo por módulo, contra la corrida canónica de NQ en futuros del arnés (`cartera_nt8_20261125/paridad_intradia/broker_NQ`)
  en 2019-07 → 2026-09.
- Criterio: `edgelab.research.a5.calibrar_por_sesion` (mismo signo, diferencia ≤ 1 error estándar combinado y correlación > 0,5 en ≥ 30
  sesiones), por módulo.
- **Un módulo que no calibra no se lee en los índices extranjeros:** se informa como «no medible con estos datos». La canasta primaria
  se arma con los módulos que calibran.

## Hipótesis y lectura (decididas antes)
- **Medida:** suma mensual del R de cada serie (módulo × índice); canasta = promedio entre series con datos ese mes.
- **Primaria:** canasta T+R+Z (los que calibran) en los 6 índices, todos los meses disponibles.
  - CONFIRMA si la t de una cola es ≥ 1,645;
  - NO_CONCLUYENTE si la media es > 0;
  - EN_CONTRA si la media es ≤ 0.
- **Secundarias:** T, R y Z por separado (canasta de 6 índices cada uno), con BH q 0,10 sobre las 4 pruebas.
- **Descriptivos:**
  - por índice;
  - antes de 2020 contra desde 2020 (el «salto desde 2020» medido en EE. UU.);
  - costos ×2.
- **Advertencia:** son CFD, no futuros. El costo real de operar FDAX, FTSE o Nikkei en futuros se aproxima con el de NQ (K34: estimado
  y declarado).

## Justificación económica
T (ruptura del rango de apertura), R (fase de ATR al inicio del contado) y Z (día de tendencia) explotan la llegada de información y de
órdenes en la apertura de contado, un rasgo común a todos los mercados de acciones grandes. Si la ventaja es del mecanismo y no un
ajuste a NQ, debería aparecer, más chica, en otros índices con su propia apertura.

## Cómo podría refutarse
- **No se transfiere:** canasta con media ≤ 0, o positiva sólo en un índice o una época. Sería un ajuste a NQ en 2020–2026 (dentro de
  la muestra del vendedor), y bajaría la confianza en la intradía de la cartera.
- **Circuito inválido:** si la calibración falla, la prueba no se puede hacer con estos datos. Se informa así y no se cuenta como
  refutación.

## Adenda (2026-11-27, antes de leer cualquier índice extranjero): lo que cambió la compuerta de calibración
Todo lo de abajo surge de la compuerta y de verificaciones sin retornos de estrategia sobre índices extranjeros.
Archivos: `CALIBRACION.json`, `CALIBRACION_DIAGNOSTICO.json`.

1. **Hora de HistData.** La primera calibración falló en los tres módulos (T 0,03 contra 0,13 de R medio).
   - Diagnóstico con NQ futuros pasados por el mismo circuito: con volumen 1 y sin noticias calibran los tres (correlación 0,89–0,99), así
     que las transformaciones están bien.
   - La correlación minuto a minuto entre el CFD del Nasdaq de HistData y NQ futuros muestra que el sello **no es EST fijo**, como dice la
     documentación de HistData. Es hora de Nueva York con horario de verano y marca la apertura de la vela: coincide en invierno (0,97) y
     en verano sólo corrido 1 h (0,91–0,95).
   - Se corrigió la lectura (`_leer`).
2. **Calibración con la hora corregida (Nasdaq CFD contra NQ futuros, 2019-07 → 2026-09):**
   - **T calibra:** media 0,122 contra 0,133, correlación 0,75.
   - **R calibra:** 0,176 contra 0,162, correlación 0,95.
   - **Z no calibra:** 0,016 contra 0,102, con 101 de 196 sesiones en común. Por la regla de arriba, **Z no se lee**.
   - La primaria pasa a ser la canasta **T+R**. Las pruebas quedan en 3: canasta T+R, T y R.
3. **Verificación horaria por índice** (sin retornos de estrategia). Se buscó el minuto local de mayor |retorno| medio en enero y febrero
   y en julio y agosto:

   | Índice | Invierno | Verano | Lectura |
   |---|---|---|---|
   | DAX | 09:00 | 09:00 | Apertura de contado: OK |
   | FTSE | 08:00 | 08:00 | OK |
   | CAC | 09:00 | 09:00 | OK |
   | EuroStoxx | 08:00 | 08:00 | Consistente entre estaciones: es la apertura de los futuros (FESX). Se mantiene la apertura declarada de contado, 09:00, igual que DAX y CAC |
   | **Nikkei** | 07:19 | 09:00 | **No coincide entre estaciones: hora no confiable** |
   | **ASX** | 17:00 | 09:50 | **No coincide: hora no confiable** |

   **Nikkei y ASX se excluyen** antes de leerlos. El universo queda en DAX, FTSE, EuroStoxx y CAC.
