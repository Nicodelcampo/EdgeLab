# EXP-8: ¿la caída final se puede mitigar sin sobreajuste? Filtro de estado de la apertura y armado de cartera

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: Parte A EF3 (DESC con BH q 0,10; confirmación en REP congelado). Parte B EF2 (descriptiva, sin selección por media).  
Familia: `ESTADO_APERTURA_FILTRO` (24 pruebas registradas: 3 variables de estado × 8 estrategias). La Parte B no suma pruebas: no elige reglas ni parámetros.  
Antecedentes: DIAG-CAIDA-2026 (la caída es de precio, no de sizing: cae el R por operación; ES con más reversión de 5 min, NQ con más movimiento hecho de noche), EXP-7 (0/12; C2_VZ única con signo estabilizador, sin potencia). Familias parecidas FILTROS_CONTEXTO, FILTRO_PICOS_A5, CARTERA_20261116; NO_REPETIR F-REGIMEN-OFFLINE, F-FILTROS-CONTEXTO-SIN-FILTRO, F-FRENO-DIARIO-NO, F-SELECTIVIDAD-INVERSA, F-GEX-DIA-TENDENCIA.  
Cambio respecto a falla previa: (1) no se rota por rendimiento reciente de la estrategia (F-REGIMEN-OFFLINE): la variable es el estado del mercado, declarada antes y medible al abrir; (2) no se usan indicadores externos (VIX, GEX, COT: F-FILTROS-CONTEXTO-SIN-FILTRO, F-GEX-DIA-TENDENCIA) sino la estructura del precio del mismo instrumento ligada al mecanismo diagnosticado; (3) no es freno por P&L (F-FRENO-DIARIO-NO); (4) no es la señal de un día (F-SELECTIVIDAD-INVERSA) sino un estado de 20 sesiones; (5) un solo umbral fijo para todo (mediana expansiva), sin grilla.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (K33, K40, K48, K49, K51, K53, K55/K56).  
Potencia previa: por estrategia ≈ 150–1.200 operaciones en DESC 2020–2025 partidas en dos mitades; con sd ≈ 1–1,5 R por operación el MDE de la diferencia encendido − apagado es ≈ 0,15–0,45 R/op (sólo efectos grandes en T/RQ5/V, muy grandes en R/Z/ES5N/Franklin). Las pruebas sin potencia publican su MDE y quedan SIN_POTENCIA.  
Diagnóstico de mecanismo: sin grilla; se publica por prueba la fracción de operaciones encendidas, R/op encendido y apagado por bloque, el efecto en R mensual y en drawdown, y el resultado en 2026 (descriptivo).  
Pedido de Nico (2026-11-25): «avanzá en indagar si la caída final de algunas estrategias tiene forma de mitigarse sin sobreajuste» (carteras para hoy, sin seguimiento en tiempo real).

## Justificación económica
Las estrategias que caen al final (T, RQ5, ES5N, Franklin, V) viven de que el movimiento de la apertura continúe. Si el mercado
alterna períodos de semanas en que la apertura continúa y períodos en que revierte o ya se movió de noche, y esos períodos
persisten, el estado de las últimas 20 sesiones anticipa si la siguiente sesión favorece la continuación. Apagar la estrategia
en el estado desfavorable mitiga la caída sin tocar la regla. Si en cambio los estados no persisten, el filtro sólo quita
operaciones al azar y no cambia el R por operación.

La segunda vía no predice nada: combinar estrategias poco correlacionadas con un peso fijado por su volatilidad pasada
reduce el drawdown sin elegir por rendimiento.

## Datos y objeto (congelados)
- Operaciones: corridas NT8 de `docs/research/candidatas_nt8_20261125/` (1 contrato fijo, veto de noticias), R neto =
  (pts − fricción canónica `edgelab/costos.py`, base) / riesgo_pts. Estrategias de la Parte A (8): T_NQ, R_NQ, Z_NQ, V_NQ,
  RQ5_NQ, RQ5_ES, ES5N_ES, Franklin_NQ. Parte B agrega SOMSF_NQ, C2VZ_NQ, C2VZ_ES.
- Estado de la apertura, por instrumento, de M1 NT8 (`tools/diag_caida_2026.py::sesiones`, sesión RTH 09:30–16:00 NY):
  `cont_orb` (rompe el rango 09:30–09:45 antes de 11:00 y cierra del lado de la ruptura), `ac5_manana` (autocorrelación de
  retornos de 5 min 09:30–11:30), `frac_noche` (fracción del movimiento total hecha entre el cierre previo y la apertura).
- Variable de estado de la sesión t = media de las 20 sesiones completas anteriores (t−20 … t−1). Umbral = mediana expansiva de
  esa misma serie desde 2018-01 hasta t−1 (mínimo 250 sesiones). **Encendido** si `cont_orb20 ≥ umbral`, `ac5_20 ≥ umbral`,
  `frac_noche20 ≤ umbral` (dirección fijada por el mecanismo: continuación buena, movimiento nocturno malo).
- Partición: DESC y REP = sesiones con bloque A5 DESC / REP entre 2020-01-01 y 2025-12-31. 2026 (tramo que inspiró la
  pregunta) y los meses HOLDOUT de A5 (vistos en NT8) sólo descriptivos.

## Parte A — Filtro de estado (24 pruebas)
Estadístico primario: diferencia de R/op medio encendido − apagado (Welch, unilateral, H1 > 0), BH q 0,10 sobre las 24 en DESC.
Confirmación: la prueba nominada confirma si la diferencia es > 0 en REP con p ≤ 0,10. Se publican además el R mensual con y
sin filtro, el drawdown máximo y el peor semestre en DESC, REP y 2026.

## Parte B — Armado de cartera (descriptiva)
R mensual por estrategia (suma, 1 R por operación). Esquemas, todos con reglas fijas:
1. `IGUAL_MANANA`: T_NQ, RQ5_NQ, RQ5_ES, ES5N_ES, Franklin_NQ a 1 R.
2. `IGUAL_TODAS`: las 11 a 1 R.
3. `INV_VOL_TODAS`: las 11, peso del mes m ∝ 1 / sd del R mensual de los 12 meses anteriores, normalizado a suma 11,
   recortado a [0,25; 2,0]; antes de 12 meses, peso 1.
4. `MANANA_MAS_C2VZ`: (1) + C2VZ_NQ + C2VZ_ES a 1 R.
5. Si alguna prueba de la Parte A confirma, `IGUAL_TODAS` con ese filtro aplicado; si ninguna confirma, no se construye.
Métricas: R/mes medio, sd, meses negativos, drawdown máximo, peor semestre, R/mes / drawdown; por tramo 2020–2025 (todos los
meses, descriptivo) y 2026 (descriptivo). No se elige un esquema por su media: la lectura es drawdown a igual media.

## Cómo podría refutarse
- El filtro queda refutado para una estrategia si la diferencia encendido − apagado es ≤ 0 en DESC con MDE suficiente, o si no
  confirma en REP: el estado de 20 sesiones no anticipa la siguiente.
- La vía de cartera queda refutada si `INV_VOL_TODAS` o `MANANA_MAS_C2VZ` no bajan el drawdown máximo ni el peor semestre frente
  a `IGUAL_TODAS` / `IGUAL_MANANA` en 2020–2025.

## Iteración (pedido de Nico)
Primera corrida → auditoría (look-ahead, unidades, costos, meses, conteos) → una segunda corrida con lo corregido. La segunda es
la que cuenta; la primera y la lista de correcciones se publican.
