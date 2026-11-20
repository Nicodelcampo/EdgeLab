# «Atrás» de reglas congeladas de la v2 y la v4 sobre M1 real de futuros (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de lanzar. Pedido de Nico («dale»). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4 (confirmación de reglas congeladas en datos que su linaje no
usó). Herramienta: `tools/atras_m1.py`. Datos: `nicolasbuttaro/edgelab-nt8-m1-futuros` (NT8, MergeNonBackAdjusted, UTC, apertura de
vela), lector `fuentes_ticks.bloques_m1nt8` (corta en la frontera del holdout).

Antecedentes: `python tools/antecedentes.py "re-medir reglas congeladas sobre M1 de años anteriores, calibrado contra ticks"` → papel_m1_20261115
(M1 de Dukascopy contra ticks: ASIA y OTR930 calibraron, RANGO0100 y TORI no), U1_ORO_GRILLA «atrás» (XAU 2023–2025), `ATRAS_EVALUACION.md`
(las CFD no tenían ventana con potencia), F-HOLDOUT-A5-INTERCALADO.

Potencia previa: atras_m1_ops.csv (las 5 reglas, desarrollo en ticks): 32.0 ops/mes, R/op +0.372, sd 1.80, n para decidir 145, 4.5 meses → OK |
lectura de N 600 con la mitad del efecto: potencia 0.814. La ventana primaria tiene 60–90 meses por regla: se esperan ≈ 2.000 operaciones.

## 1. Reglas (congeladas, sin cambios: módulo, celda, cortes y tope de su acta o de la selección de la cosecha)
| Regla | Canasta | Instrumento | Ventana primaria | Descriptivo |
|---|---|---|---|---|
| CVGAP2-GC#11 | v4 | GC | 2018-01-02 → 2025-07-31 | 2008-01 → 2017 |
| COMEX-CIERRE-GC-R#0 | v4 | GC | 2018-01-02 → 2025-07-31 | 2008-01 → 2017 |
| IF-LUX-NQ-R2#1 | v4 | NQ | 2018-01-02 → 2022-12-30 | 2006-01 → 2017 |
| CVGAP-ES-C | v2 | ES | 2018-01-02 → 2025-07-31 | 2006-01 → 2017 |
| PREAPERTURA-NQ | v2 | NQ | 2018-01-02 → 2022-12-30 | 2006-01 → 2017 |

Fuera: las que usan velas de 50 ticks (CVGAP2-NQ#18, #3, CVGAP2-GC#5), footprint (U1-*, CONF-CVR), o señal en CFD (ORO-ALM-CFD,
IF-LUX-CFD, CVGAP-CFD-ES-C). NQ termina en 2022: el ancestro común AREAS_EXP_1_CRUZADO midió el Nasdaq (USATECH) de 2023-01 a 2025-07.

## 2. Fase 1 — calibración (2025-08-05 → 2026-09-30, sin holdout)
Cada regla sobre M1 de NT8 contra sus operaciones en ticks, R por sesión. **Calibra** si: mismo signo de la media, diferencia ≤ 1 error
estándar combinado, correlación por sesión > 0,5 en ≥ 30 sesiones comunes (`papel_m1_20261115/VALIDACION.md`). `CALIBRACION.json` se
commitea ANTES de lanzar la fase 2; la que no calibra no se mide en M1.

## 3. Fase 2 — atrás (sólo las que calibran)
Por regla: R/op, IC90 por sesiones, e-proceso (cotas [−6, 30]), R por año. Canasta: suma de R por sesión de las calibradas, bootstrap
unilateral (H0 media ≤ 0).

## 4. Decisión (cuenta a favor Y en contra; costos canónicos actuales)
- **Por regla:**
  - **A FAVOR_ATRAS** si IC90 inferior > 0 y ≥ 60 % de los años positivos;
  - **EN_CONTRA_ATRAS** si media ≤ 0 con potencia ≥ 0,8 para la mitad de su efecto de desarrollo;
  - si no, **NO_CONCLUYENTE**.
- **Canasta:**
  - **CONFIRMADA_ATRAS** si p ≤ 0,05, media > 0 y ≥ 60 % de años positivos;
  - **REFUTADA_ATRAS** si media ≤ 0;
  - si no, NO_CONCLUYENTE.
- **Consecuencias (sin tocar nada sobre la marcha):**
  - una regla EN_CONTRA_ATRAS sale de su canasta operativa en la próxima versión, con un pre-registro nuevo;
  - una canasta CONFIRMADA_ATRAS habilita proponer tamaño real mínimo (decisión de Nico) con el terminal como vigilancia.
- El tramo descriptivo (2006/2008–2017) nunca decide.

## 5. Riesgos declarados
- **Escala:** NQ subió de ≈ 7.000 a ≈ 21.000 entre 2018 y 2025, y los parámetros en puntos pesan distinto en otra época. Los que usan ATR
  o razones se escalan solos. Se reporta ops/mes por año para ver la deriva de frecuencia.
- **Costos:** fricción canónica de hoy, aplicada a todo el período.
- **M1:** la ejecución se aproxima con 4 ticks por vela en orden conservador. Eso es lo que mide la fase 1.
- **Linaje:** la mirada queda registrada como consumida (2006 → ventana primaria) para el linaje de cada regla; ninguna familia derivada
  la usa después como holdout A5.

## 6. Contador y justificación
5 pruebas por regla + 1 de canasta = **6**, familia `ATRAS_M1_V2V4_20261117` (linaje: CVGAP2_GC, COMEX_CIERRE_ORO_GC,
INTENTO_FALLIDO_LUX_NQ, CORREDOR_VOL_GAPS_ES, RANGO_PREAPERTURA_NQ). La calibración no es una prueba con desenlace nuevo (compara fuentes).

- **Justificación económica:** la de cada regla en su SPEC. Si el mecanismo es real y la deriva es lenta (paso 1/1b), tiene que verse en
  años que nadie usó para elegirlo.
- **Cómo podría refutarse:** media ≤ 0 con potencia en 2018 → 2022/2025 (EN_CONTRA_ATRAS / REFUTADA_ATRAS); o que ninguna calibre (el M1
  no sirve para estas reglas).

## Enmienda 1 (2026-11-18): relanzamiento con el motor de la grilla corregido (K40)
- **Qué pasó:** el motor de la grilla (`areas_expansion.simular_cierre_linea`) cobraba el stop en el pseudo-tick extremo de la vela M1, no
  en su nivel.
- **Evidencia:** la calibración v1 dio M1 < ticks en las 5 reglas (−0,007 a −0,162 R por sesión), dentro de 1 EE pero siempre del mismo
  lado.
- **Corrección:** con `m1_sintetico` el stop sale en su nivel, salvo un hueco en la apertura. Hay test.
- **Relanzamiento:** se relanza todo (calibración y «atrás»), con las mismas reglas, ventanas, criterios y pruebas. No se cuentan pruebas
  nuevas.
- **La v1:** queda en `descartada_v1/`.
