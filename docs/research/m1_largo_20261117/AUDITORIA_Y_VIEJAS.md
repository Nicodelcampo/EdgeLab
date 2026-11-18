# Auditoría de errores de unidad y escala, y estrategias viejas con M1 largo (resultado, 2026-11-18)

Estado: RESULTADO — pre-registro `PREREGISTRO_VIEJAS.md` (EdgeReplica y oro 04:15; la auditoría es descriptiva). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RESULTADO_VIEJAS.json`, `EDGEREPLICA_NQ.csv.gz`,
`ORO415_GC.csv.gz`. Pedido de Nico: «revisá otros errores de ese estilo» y las estrategias viejas.

## 1. Errores del mismo estilo que el de T (encontrados y corregidos)
| # | Error | Dónde | Efecto | Corrección |
|---|---|---|---|---|
| E1 | Medir en ATR módulos que arriesgan mucho menos que un ATR | FundedSync: T, A20, E, F, V, C | diluye la señal ≈ 3–10 veces; los llamé «sin ventaja» o «frágil» | se miden en R (su stop inicial). Se verificó en el código que `riesgo` es el stop INICIAL en todos salvo T (activo al salir; ya corregido con el rango de apertura) |
| E2 | Comparar épocas con parámetros en puntos fijos | T (tope de stop de 100 pts), E (stop 30 / objetivo 45 pts), F (tope de riesgo 125 pts); filtros de N, W y C | antes y después de ~2018 son reglas distintas | se comparan dentro de la época en la que el parámetro es razonable (2020+); T se verificó aparte (el tope no explica su ventaja) |
| E3 | Medir en puntos por operación a través de años con precios muy distintos | informe viejo de EdgeReplica («crece 2023 → 2026») | parte del «crecimiento» era escala | se mide en ATR (§2) |
| E4 | Unidad de la cartera del vendedor (20 USD/pt en vez de MNQ a 2) | capa 2 | magnitudes ×10 | corregido antes del informe |
| E5 | Régimen análogo de T en ATR | m1_largo §4 | — | rehecho en R: análogos 2008–2019 +0,023 R contra +0,008 en el resto, NO_CONCLUYENTE. La conclusión no cambia: el estado de volatilidad y tendencia no explica el salto de 2020 |

**FundedSync en R (bruto con IC90 > 0 marcado con *; neto en NQ 2020–2025):**

| Módulo | NQ 2020–2025: bruto / neto (R) | ES / YM 2020–2025 (bruto) | Antes de 2020 |
|---|---|---|---|
| A20 | +0,124* / +0,083 | +0,029 / +0,020 | ≈ 0 |
| E | +0,097* / +0,045 | +0,025* / +0,048 | ≈ 0 |
| F | +0,071* / +0,050 | +0,030 / +0,013 | ≈ 0 |
| V | +0,037* / +0,021 | +0,008 / +0,017 | ≈ 0 |
| T | +0,176* / +0,156 | +0,084* / +0,109* | NQ +0,036 |

**Lectura:** varios módulos que declaré «sin ventaja» tienen señal en NQ desde 2020. El vendedor diseñó la estrategia para NQ, probablemente con
esos años, así que NQ 2020+ puede ser ajuste suyo. ES y YM 2020+ son fuera de muestra para ese ajuste:
- **T** lo pasa (significativo en los dos);
- **E**, débil;
- **A20, F y V** no (≈ 0).

Quedan como pistas NQ por confirmar en forward, por debajo de T.

## 2. EdgeReplica en NQ 2006–2022 (antes de su selección): sin señal → selección
- **Resultado:** bruto +0,0002 ATR por operación, IC90 [−0,0011, +0,0016], potencia 1,0 para la mitad del efecto 2023–2025 (+0,015 ATR).
- **Veredicto pre-registrado:** NO_CONCLUYENTE, porque la media es apenas > 0. En la práctica es cero: el efecto antes de 2023 es menos de
  1/50 del reciente.
- **Por año:** ≈ 0 de 2006 a 2023; +0,018 a +0,023 sólo en 2024–2026, el período de donde salieron las reglas.
- **Conclusión:** «decayó» no es la palabra. Nunca existió fuera del tramo donde se eligió: es ajuste, no un patrón horario. **Se descarta.**

## 3. Oro: corto a las 04:15 CT, en GC 2008–2022 (antes de la muestra spot)
- **H2, corto sin condición: SESGO_CONFIRMADO.** Bruto +1,62 ticks (IC90 [+1,25, +1,99]), 3.625 operaciones, 67 % de años positivos,
  potencia 0,99. H1 (tras subida) parecido: +1,99 ticks.
- **No es operable solo:** neto −4,4 ticks, porque la fricción de GC son ≈ 6 ticks y el sesgo es ≈ 1/4 del costo. Sólo en 2026 fue
  grande (+19 ticks), y en ticks eso está inflado por el precio del oro.
- **Uso posible:** como información de horario para otras operaciones de oro (no comprar justo antes de las 04:15 CT, o vender ahí si ya se
  iba a vender). No como estrategia propia.

## 4. Lo que no se pudo medir con M1
- **MGC EMA 200/500/2000 (el oro de las EMAs):** sus barras son de 25 operaciones y no se reconstruyen desde M1. Medirla con barras de
  tiempo sería otra regla.
  - Su veredicto viejo («no se valida», p = 0,10 contra el mejor de 21 celdas) queda como está.
  - Para revisitarla haría falta MGC/GC en ticks de años anteriores.
- **LuxImb, impulsos con zonas en el 25 % inicial (`luximb_grilla`):** corre en M1, así que SÍ se puede lanzar sobre NQ 2006–2025. Nunca
  se corrió (quedó como PROPUESTA el 24-oct). Es la candidata natural a primera campaña con la partición A5. Requiere:
  1. integrar la partición A5 en el embudo;
  2. una versión chica centrada en la hipótesis (impulso amplio con ≥ 3 zonas atravesadas en el 25 % inicial, pocas ejecuciones), o un
     E0 que reduzca las 907.200 celdas por canal (K4);
  3. pre-registro con potencia.
