# Pre-registro — U1-CRUZADO congelada, trasladada al oro: señal en XAU (Dukascopy), operación en GC

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia: `U1_ORO`. Etapa del embudo: **EF3** (réplica de una regla congelada en un instrumento nuevo; no confirma U1 en NQ ni en oro).
Pedido de Nico (2026-10-24, con OK el 2026-10-25): aplicar en el oro de Dukascopy, que tiene potencia, lo mejor diseñado de USATECH/NQ,
con los costos de GC como se hizo con USATECH → NQ.

## 1. Regla (sin cambios salvo la escala)
- Señal U1 tal cual (`edgelab/research/u1_cruzado.py::senales`): N ≥ 3 zonas LUX-IMB OG/VI en M1 dentro de un área de alto ≤ W,
  alejamiento ≥ 8·H, regreso al 75 % (x = 0,25). Ejecuciones `E1A/T1/S3` y `E1A/T3/S3` (stop más allá del extremo), sin tope.
- **Escala (única adaptación, declarada ahora):** W = 40 pts y G = 1 pt de USATECH se multiplican por
  `r = rango M1 mediano de XAU en el trimestre anterior / rango M1 mediano de USATECH en 2025-08-05 → 2026-03-31` (el descubrimiento
  de U1). Es causal (trimestre anterior) y target-free; el primer trimestre de XAU sólo calibra. Todo lo demás es relativo
  (A/H, x) o temporal y no se toca. No se prueba otro mapeo (p. ej. por nivel de precio).
- **Operación:** 2025-08-05 → 2026-09-30, en GC con `u1_cruzado.operar` (base GC − XAU al cierre del minuto de la señal, niveles
  trasladados y redondeados al tick de GC, entrada en el primer tick de la vela siguiente, resolución con ticks de GC). Antes de
  2025-08 no hay GC: 2023-01 → 2025-08-04 se opera en el propio XAU (`operar_propio`) como **proxy declarado**.
- **Costos:** fricción canónica de GC (`edgelab.costos.friccion_rt_puntos("GC")` = 0,605 pts). En el proxy, el spot con costos de GC
  sólo es válido bajo la hipótesis explícita de ejecutar en GC (la regla del repo prohíbe transportar costos fuera de ese caso).

## 2. Pruebas y decisión (fijadas ahora)
4 pruebas: {proxy_xau, cruzado_gc} × {T1, T3}. Estadístico: media neta por operación, bootstrap de sesiones (`escalera.resumen_sesiones`,
20.000), p unilateral (H1: media > 0), MDE publicado.
- **TRANSFIERE**: en `cruzado_gc` alguna ejecución con p de Holm (sobre las 2) ≤ 0,05 y media > 0, **y** la misma ejecución con media
  > 0 en `proxy_xau`.
- **NO_TRANSFIERE**: las dos ejecuciones con media ≤ 0 en `cruzado_gc`.
- **INCONCLUSO**: el resto (incluido el caso «sólo en el proxy»).
- **Alcance de la muerte:** NO_TRANSFIERE refuta la regla en el oro con este mapeo de escala; **no** refuta U1 en NQ.
- TRANSFIERE no confirma: hace de U1-ORO un candidato para forward (desde el 2026-10-01, con ejecución en GC y filtro de noticias).

## 3. Noticias (pedido de Nico del 2026-10-25)
Las operaciones no pueden estar abiertas durante noticias USD de alto impacto. Se declara ahora: cuando `config/noticias/` y
`edgelab/noticias.py` existan, se informa la misma tabla **excluyendo** las operaciones cuyo intervalo [entrada, salida] toque una
ventana bloqueada (regla de exclusión fijada antes de mirar, no se elige según el resultado). La decisión del §2 se recalcula con el
filtro y vale la más conservadora de las dos.

## 4. Justificación económica
Si U1 capta un mecanismo de microestructura (regreso a áreas donde se concentraron huecos de cotización), debería aparecer en otro
mercado continuo de 24 h con un feed CFD equivalente. El oro es el candidato con más sesiones (2023-2026).

## 5. Cómo podría refutarse
Media ≤ 0 en GC para las dos ejecuciones; o positiva sólo en el proxy (precios del spot) y no en GC.

## 6. Multiplicidad, linaje y riesgos
- Registro global: `u1_oro/transferencia`, 4 pruebas, antes de correr. Linaje: padre `AREAS_EXP_1_CRUZADO` (bruto).
- Riesgos: el spot no es el futuro a horizonte corto (`RESULTADO_EQUIVALENCIA.md`); la cola sin tope (peor −218 pts en NQ); el
  mapeo de escala es una elección (una sola, declarada). La densidad de señales del feed de oro puede diferir de la de USATECH.

## 7. Código (sha256)
`tools/kaggle_grilla/u1_oro_main.py` `9a4977199dff688b9ca15a1d1310ecef1930f4a63148d7cf1d9ab9f906c01862` ·
`edgelab/research/u1_cruzado.py` `73c4d10723ca62b547b3f0598e72db38a4631f08ce95cdc89671fdf00d4b5bbd` ·
`edgelab/research/u1_indaga.py` `fd2fe33f38647dda050210e2cfddd8e440e49be8f6cc20f6169b94b032645b9d`.
Salida: `docs/research/u1_oro_20261025/U1_ORO.json` (+ operaciones).
