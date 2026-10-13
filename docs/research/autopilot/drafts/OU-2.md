# OU-2 — Reversión de ZB a 5-15 min con precio medio bid/ask (descarta rebote bid-ask)
**Estado: BORRADOR generado por el autopilot (regla R3_ARTIFACT_CHECK). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
Si la reversión sobrevive con precio medio es de otra naturaleza; si desaparece, queda cerrado. Requiere un script que reconstruya mid desde bid_ticks/ask_ticks (no existe aún).
Evidencia propia de origen: ZB_REV_5_15. Tipo de vacío: DATA_DEFINITION.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- L_BOUNCE: La autocorrelación negativa intradía en precios de transacción es mayormente rebote bid-ask para escalas < 20 min; desaparece al muestrear a 5 min o más en FX; se ve más en futuros de tick grueso. (Goodhart (1989); Cont (2001) stylized facts; resumen en finance.martinsewell.com/stylized-facts/dependence; arXiv 2606.29591 (rebote bid-ask y reversión de horizonte corto en índices))

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"cells": [[5, 60], [5, 240], [15, 240], [60, 240]], "desde": "2025-07-01", "hasta": "2026-09-30", "inst": "ZB", "mode": "ou2", "n_planned": 4, "nperm": 5000, "seed": 20261019}
```
Pruebas planeadas: 4 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.6 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

Definiciones congeladas (script `tools/ou2_mid.py`):
- Datos: ZB, sesiones aprobadas 2025-07-01 → 2026-09-30 (líder por sesión del resolver; fecha de sesión CME del catálogo). Mismas sesiones y celdas que OU-1 Parte A para ZB (misma muestra que originó la pista: es la prueba de DEFINICIÓN del precio, no de muestra nueva).
- Por (sesión, minuto): «last» = último trade del minuto; «mid» = (bid+ask)/2 del último tick del minuto con libro válido (0 < bid ≤ ask). Los minutos sin libro válido se excluyen del análisis de «mid».
- Estadístico (idéntico a OU-1): X_t = ln P_t − SMA_N(ln P_t) dentro de sesión sobre barras de s minutos (último valor de cada barra); b = pendiente agrupada de (X_{t+1} − X_t) sobre X_t; primera barra de sesión con retorno 0. Nulo: signo aleatorio independiente por retorno de barra (5.000 sorteos, semilla 20261019); z = (b − media_nulo)/sd_nulo, bilateral.
- Pruebas (4, Holm 4) con «mid»: (barra, ventana) = (5,60), (5,240), (15,240), (60,240) minutos. «La reversión sobrevive» = z < 0 y p_Holm < 0,05 en la celda con «mid»; si «last» da reversión y «mid» no, el hallazgo de OU-1 era rebote bid-ask.
- Descriptivo (no es prueba): «last» y «mid» sobre los mismos minutos, y por mitades de sesiones (cada mitad: z de «last» y «mid» en 3 celdas); cobertura de «mid».

## Transparencia sobre lo ya mirado (antes de este pre-registro)
- OU-1 ya midió ZB con precio de transacción (último trade del minuto): b y z en las 4 celdas (z = −14,05 / −7,68 / −3,28 / +0,06; Holm 36 = 0,0072 / 0,0072 / 0,0204 / 1). Esta corrida usa la MISMA muestra de sesiones con otra definición de precio.
- El pipeline se probó solo en datos sintéticos (con y sin rebote bid-ask inyectado); no se miró ningún resultado de «mid» en ZB real.
- Esto es información sobre el mecanismo, no una estrategia: aunque «mid» sobreviva, que sea operable es otra pregunta (spread, costos).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 4 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.1818, "power": 0.6, "utility": "info=0.3", "rho_required": null, "feasibility": 1.0, "cost_factor": 2.449, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 1} → 0.0134
