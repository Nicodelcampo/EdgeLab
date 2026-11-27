# Operaciones de un amigo de Nico en AL29/AL30 (Veta, plataforma Matriz): qué son y cómo se mediría (2026-11-27)

Estado: IDEA + DESCRIPTIVO — no es una prueba contada ni un resultado de estrategia. Se miraron precios diarios de AL29 y AL30 (data912)
sólo para reconstruir la operación y medir liquidez; ninguna regla con P&L. Todo lo de abajo es antecedente declarado para cualquier
pre-registro futuro sobre AL29/AL30 (familia `RATIOS_BONOS_AR`).

## 1. La operación (captura enviada por Nico; las cuatro, órdenes límite DAY, ejecutadas completas)
| Hora | Bono | Lado | VN | Precio (por 100 VN) |
|---|---|---|---|---|
| 15:58:40 | AL29 | Venta | 5.000 | 85.700 |
| 15:59:14 | AL30 | Compra | 5.000 | 82.490 |
| 16:09:14 | AL29 | Compra | 6.000 | 84.750 |
| 16:09:19 | AL30 | Venta | 6.000 | 82.490 |

- **Día:** el único compatible con las cuatro ejecuciones en los diarios de data912 es el **2026-11-26** (AL29: apertura 82.510, máximo
  85.700, mínimo 82.200; AL30 entre 80.810 y 82.730).
- **Ratio AL29/AL30:** vendió a 1,0389 y recompró a 1,0274, una caída de 1,1 % en 11 minutos.
- **Resultado:** el par cerrado (5.000 VN) deja **+47.500 $** sobre ≈ 4,3 millones de nocional (≈ 1,1 %). Queda además una diferencia
  abierta de +1.000 AL29 / −1.000 AL30.
- **Toda la ganancia vino de la pata ilíquida.** AL30 se operó a 82.490 en las dos puntas: fue cobertura, no aportó. La venta de AL29 fue
  **al máximo del día** (85.700).

## 2. Qué es
- **No es el ratio de ley de la charla** (GD/AL, mismo flujo y distinta ley). Es un **ratio de vencimiento dentro de la misma ley**:
  AL29 (duration ≈ 1,7) contra AL30 (≈ 2,1). Lucioni lo descartaba: «GD29 y AL29 olvídense», por el spread.
- Es una **rotación con bonos propios para sumar nominales**: tenía AL29, lo pasó a AL30 cuando AL29 estaba caro y volvió cuando se
  abarató. Terminó con más AL29.
- La forma más probable es **proveer liquidez en el bono ilíquido y cubrirse en el líquido**. Alguien levantó AL29 hasta 85.700, él le
  vendió con una límite; diez minutos después el precio volvió y recompró. Con comisión cero (VetaFLAT), operando con límites pasivas
  **cobra** el spread en vez de pagarlo; ésa es la economía del trade.

## 3. Datos descriptivos (data912 diario; meses DESC+REP de A5; HOLDOUT y terminal excluidos salvo el día del trade)
| Medida | AL29 | AL30 |
|---|---|---|
| Volumen diario medio, últimas 60 ruedas (VN) | 1,37 M | 164,5 M (≈ 120×) |
| Spread de la punta (foto del 2026-11-27) | 0,73 % (83.860 / 84.470) | 0,085 % |
| Rango diario medio 2026 | 1,77 % | 1,09 % |
| Rango del 2026-11-26 | 4,12 % | 2,34 % |

- **Exceso de rango de AL29 sobre AL30**, mediana desde la salida del cepo (2025-04-14): **0,65 % por día**. Es la cota de lo que se puede
  capturar en la pata ilíquida, antes de cualquier selección adversa.
- **Ratio AL29/AL30 al cierre**, desde la salida del cepo: cambio diario con desvío de 0,67 % y autocorrelación −0,16; el spread implícito
  de Roll es 0,54 %. Entre 2022 y 2023 era −0,34 y 1,2 %: el ruido se achica.
- **Salvedad 1, precios viejos.** Cada bono solo no muestra rebote diario (autocorrelación ≥ 0); el rebote aparece sólo en el ratio. Lo
  más probable es que el cierre de AL29 sea a menudo el de una operación vieja (comercio no sincrónico). Esa «reversión diaria» no se
  puede operar al cierre: sólo la captura quien está en el libro cuando el precio se mueve.
- **Salvedad 2, amortizaciones.** El ratio con precios salta en los pagos (9-ene, 9-jul), porque AL29 y AL30 amortizan distinto. Una regla
  sobre AL29/AL30 tiene que usar paridad o ajustar por pagos; con GD/AL del mismo flujo no pasa.

## 4. Qué se puede concluir y qué no
- **Una operación ganadora no es evidencia.** Vemos la que salió bien y que alguien eligió mostrar (supervivencia y selección). Falta la
  serie completa: cuántas límites quedaron sin ejecutar, cuántas veces el precio no volvió y cuánto perdió entonces.
- **El riesgo es de selección adversa:** cuando la límite pasiva se ejecuta en AL29, a veces es porque el precio se va (noticia, flujo
  grande) y no vuelve. Con ≈ 1,4 M VN por día, salir de una posición mala cuesta varias veces el spread.
- **La capacidad es chica.** Su tamaño (5.000–6.000 VN) ya es comparable a la punta del libro (10.000 VN en la compra). No escala a cuentas
  grandes.
- **Encaja con lo medido:** BONOS-ROTACION encontró que en swing el bruto existe pero el spread se lo come. Si se **cobra** el spread en
  vez de pagarlo, el signo de ese costo cambia. Por eso la versión intradía pasiva es la única que tiene chance, y no está medida.

## 5. Matriz y cómo se mediría
- **Matriz es el OMS de Primary (xOMS) de Veta:** `matriz.veta.xoms.com.ar`. Veta expone además la **API de Primary**
  (`api.veta.xoms.com.ar`): token con `/auth/getToken` (usuario y contraseña de API que emite el broker) y después `X-Auth-Token`. Es la
  misma API que usa `pyRofex` (entorno LIVE).
- `/rest/data/getTrades` da operaciones históricas con `dateFrom`/`dateTo` y `external=true` para otros mercados. **Sin verificar** si
  cubre BYMA (`MERV - XMEV - AL29 - 24hs`) y con qué profundidad; la documentación pública sólo muestra ROFEX.

**Tres caminos, de mejor a peor evidencia (decisión de Nico):**
1. **El historial real del amigo**, con su consentimiento: todas sus órdenes (ejecutadas y no) y sus resultados durante meses. Son
   ejecuciones reales con el spread real. Sesgo: él eligió cuándo operar.
2. **La API de Primary vía Veta** con credenciales de API de una cuenta (de Nico o del amigo): si `getTrades` cubre BYMA, da operaciones
   intradía históricas de AL29 y AL30 para medir la regla hacia atrás. Las credenciales nunca van al chat: se cargan con el formulario
   seguro del entorno.
3. **Grabar hacia adelante** puntas y volumen de data912 `/live/arg_bonds` cada minuto: gratis y sin credenciales, pero sólo la punta (no
   las operaciones) y tarda meses en juntar N.

Con datos intradía, la prueba a pre-registrar sería: límite pasiva en AL29 cuando el ratio AL29/AL30 se aleja más de k desvíos de su
media intradía (la técnica de bandas de la charla), cobertura inmediata en AL30, salida en la media o al cierre; fill sólo si el precio
**atraviesa** la límite (no si la toca); costo = derechos más medio spread de AL30; reporte de fills, de las que no se ejecutaron y de la
pérdida cuando el precio no vuelve.

Aporte al referente: identifica el único mecanismo de bonos con chance de ser neto positivo (cobrar el spread del bono ilíquido con
comisión cero, cubierto en el líquido), explica por qué la versión swing medida no lo captura y deja definidos los datos y la prueba que
lo confirmarían o refutarían.
