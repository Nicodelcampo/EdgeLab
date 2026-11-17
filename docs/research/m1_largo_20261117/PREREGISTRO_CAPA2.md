# FundedSync en futuros, capa 2: variantes de salida, stop de catástrofe de Z y R y cartera completa (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «sí, hacé todo eso» (cartera completa, variantes de Z y R, y lo que
faltaba de FundedSync). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4. Herramienta:
`tools/m1_largo.py correr … variantes|cartera` y `analizar_capa2`. Mismos datos y lector que `PREREGISTRO.md`.

Antecedentes: `python tools/antecedentes.py "FundedSync variantes de salida stop de catástrofe cartera completa"` → tanda 2
(`fundedsyncstack_20261115/tanda2/L1_SALIDAS.json`: S y W confirmadas como mejora en S&P/Dow/Russell sobre el CFD 2012+; A20 y N no;
`L2_CATASTROFE.json`: descriptivo), RESULTADO.md de esta carpeta.

Potencia previa: m1l_T.csv (referencia de frecuencia de la familia en futuros): 16.9 ops/mes, R/op +1.864, sd 6.32, n para decidir 72, 4.3 meses → OK.
Las variantes se prueban por DÍA (≈ 1.500 días por índice en 2006–2011, ≈ 4.500 juntos): potencia de sobra para diferencias del tamaño
que la tanda 2 vio en el CFD (S +0,046, W +0,107 ATR por día).

## 1. Variantes de salida (confirmatorio en años limpios)
- **Qué se compara:** S, A20, W y N con la variante de la tanda 2 (`fundedsync_tanda2.VARIANTES`) contra su original, mismo motor, NQ,
  ES y YM.
- **Unidad:** diferencia diaria (variante − original) / ATR20 de la sesión regular.
- **Confirmatorio en 2006-01 → 2011-12, los 3 índices juntos:**
  - **CONFIRMA_MEJORA** si IC90 inferior > 0;
  - **EN_CONTRA** si IC90 superior < 0;
  - si no, NO_CONCLUYENTE.
- **Descriptivo:** 2012–2019 y 2020–2025.
- Cuatro pruebas.

## 2. Stop de catástrofe de Z y R (descriptivo, como en la tanda 2)
- **Regla:** stop de 0,5 × ATR20 de la sesión regular sobre la MAE de la operación.
- **Qué se reporta:** neto por operación y peor operación, con y sin stop, por período e índice.
- Es una aproximación: la MAE ignora el orden intrabarra.

## 3. Cartera completa del vendedor (descriptivo)
- **Motor:** `motor_cartera.simular_cartera` sobre los 15 módulos en NQ: netting, tamaño por perfil, rotación, enfriamiento por pérdida y
  cierre diario.
- **Perfiles:** el de fábrica (Lucid50K) y Lucid25K, la cuenta de Nico.
- **Noticias APAGADO:** el calendario del vendedor no está, y con el valor por defecto el motor bloquearía todas las entradas.
- **T** con las fechas de la enmienda 1.
- **Qué se reporta:** USD por año con la fricción canónica sobre el bruto (puntos × contratos × valor del punto del instrumento de ejecución; corrección de UNIDADES hecha después de una primera lectura con 20 USD/pt: el motor ejecuta en MNQ por defecto, 2 USD/pt; no cambia ninguna regla ni decisión), años positivos, máximo drawdown
  cerrado y contribución por módulo.
- No hay prueba: la cartera combina lo ya medido.

## 4. Contador y justificación
- **Contador:** 4 pruebas (las variantes en años limpios), familia `M1LARGO_EXTERNAS_20261117`.
- **Justificación económica:** salir al cierre en vez de por señal deja correr el día de tendencia (tanda 2), y un stop de catástrofe acota
  la cola de los módulos sin stop.
- **Cómo podría refutarse:** que la diferencia de la variante en años limpios sea ≤ 0 (EN_CONTRA o NO_CONCLUYENTE), o que el stop de
  catástrofe empeore el neto.
