# Carril 2 (estrategias que cruzan sesiones): diseño de la medición sobre el motor de barras ya calibrado (2026-11-19)

Estado: PROPUESTA — diseño previo a los pre-registros por estrategia; no mide nada.
- **Origen:** catálogo de Antigravity `../flujos_macro_20261119/CATALOGO_14_ESTRATEGIAS_POST_FRICCION.md` (11 de las 14 finalistas son
  multi-sesión). Pedido de Nico: «realizá todos … riguroso en los controles … sin falsos positivos».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Motor: no se construye uno nuevo
- `edgelab/research/sqx_catalogo.py::simular` ya mide posiciones de varios días sobre barras D1/H4 armadas desde el M1 (`barras_desde_m1`,
  día de trading desde las 18:00 NY), con hueco de apertura contra stop/objetivo, stop antes que objetivo dentro de la barra y camino M1
  opcional (`indices_m1`) para resolver el orden intrabarra. Tiene calibración registrada (`config/simuladores_baseline.json` →
  `test_calibracion_motor_barras`, K28: rupturas al azar sobre caminata sin deriva → R ≈ 0 con el M1). Lo usaron Turtles en oro y Connors D1.
- Regla de EdgeLab: ningún simulador nuevo sin calibración. Si una estrategia necesita algo que este motor no hace (p. ej. entrar al cierre
  RTH de las 15:55 en lugar de a la apertura de la barra siguiente), se agrega al motor con su test de calibración, no en un runner aparte.

## 2. Decisiones a fijar en cada pre-registro (antes de mirar)
- **Barra:** D1 de sesión CME (cierra 17:00 NY) o D1 RTH (cierra 16:00). Las reglas de cierre (IBS, Double Seven, cambio de mes) están
  definidas sobre el cierre RTH: se usa D1 RTH y la entrada es «al cierre» sólo si el motor la soporta calibrada; si no, apertura siguiente,
  declarada como desvío de la regla publicada.
- **Riesgo (R):** stop de la regla si lo tiene; si no, stop de catástrofe k × ATR20 previo fijado de antemano (como R/Z en NETO-PISTAS).
- **Costos:** canónicos (`edgelab/costos.py`), una fricción por operación (las de varios días pagan una sola vez: fricción en R muy baja).
- **Partición A5 con posiciones largas:** una operación se asigna al bloque de su entrada y **se descarta entera si su salida cae en un mes
  HOLDOUT o EMBARGO** (el embargo de 1 día hábil de A5 no alcanza para tenencias de hasta 20 días; sin esta regla una operación DESC leería
  precios sellados). Se verifica con un test: ninguna operación evaluada tiene salida en HOLDOUT/EMBARGO.
- **Potencia (K49) y frecuencia (F-FRECUENCIA-MINIMA):** varias son de baja frecuencia (Turnaround Tuesday, pre-FOMC, picos de VIX); su
  potencia en días se calcula antes de abrir REP; las que operan < 4 veces por mes se miden agrupadas en canasta o no se abren.
- **Familias y linaje:** CONNORS_D1 (si existe en `LINAJES.jsonl`, si no se crea con padres SQX_CATALOGO), TURTLES_ORO (Dynamic Breakout II en
  GC), y familias nuevas por mecanismo (calendario, régimen de volatilidad) declaradas con sus padres antes de correr.

## 3. Orden propuesto
1. Las de mayor frecuencia y mecanismo más documentado: IBS diario (+VIX > SMA100), Double Seven, cambio de mes (T−5 → T+3), overnight largo.
2. Régimen de volatilidad: eVRP + VIX9D/VIX, VIX alto (P80–P90), picos de VIX: una familia, con su potencia en días.
3. Oro: Dynamic Breakout II contra el canal fijo 55/20 de Turtles (control natural), rotación ES/GC mensual (baja frecuencia: canasta).
4. Pre-FOMC con filtro de VIX: ≈ 8 eventos por año → sólo como parte de una canasta de calendario; sola no tiene potencia.

## 4. Ejecutabilidad en la cuenta objetivo (agregado 2026-11-19, después de los lotes 1 y 2)
- **LucidFlex (y LucidPro/LucidDirect) no permite posiciones de un día al otro ni de fin de semana:** todo se cierra a las 16:45 ET de lunes a
  viernes (Lucid lo cierra solo) y se reabre a las 18:00 ET (soporte de Lucid «Allowed Trading Times», support.lucidtrading.com/en/articles/
  11404729; FAQ general lucidtrading.com/general-faq). Las reglas de este carril **no son operables en la cuenta objetivo**: sólo en una cuenta
  propia de broker (otro capital, otro margen) o en LucidLive.
- Consecuencia: no se invierte más en Carril 2 para Lucid (overnight largo y pre-FOMC que cruzan el cierre quedan fuera). Lo medido (lote 1 y 2)
  queda como evidencia para una eventual cuenta de broker. Lección general: verificar la ejecutabilidad en la cuenta objetivo (horario, tenencia,
  noticias, instrumentos) **antes** de abrir una familia (North Star, objetivo 4).
- Noticias: en LucidFlex/Pro/Direct se puede entrar y salir alrededor de noticias programadas («Other Trading Activities», support.lucidtrading.com/
  en/articles/11404728): T, R, SOM y Franklin (09:30–10:00, días de datos macro) no tienen restricción. Ojo: Lucid escribe «4:45 PM EST» todo el
  año; con horario de verano conviene tomarlo como 16:45 de Nueva York (lo más temprano). Las intradía cierran antes de las 16:00.
