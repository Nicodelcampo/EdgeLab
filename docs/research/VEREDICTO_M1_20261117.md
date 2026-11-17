# Veredicto de todas las reglas con la evidencia del M1 real de futuros (2026-11-17)

Estado: VIGENTE — pedido de Nico: «emití un veredicto de todos los resultados y cómo eso afecta las decisiones futuras sobre esas reglas».
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Fuentes:
- `docs/research/atras_m1_20261117/RESULTADO.md` (el «atrás» de 5 reglas del embudo);
- `docs/research/m1_largo_20261117/RESULTADO.md` y `RESULTADO_CAPA2.md` (FundedSync, SOM, régimen, variantes, cartera);
- `docs/research/cosecha_pozo_20261117/RESULTADO_HOLDOUT.md`;
- `urgencia_vs_evidencia_20261117` (pasos 1, 1b y 2).

Nada de esto cambia por sí solo una canasta en papel: cada cambio operativo va con su pre-registro (versión nueva). Operar con dinero real
sigue siendo decisión de Nico.

## 1. Lo que aprendimos (vale para todas las decisiones)
1. **Elegir entre miles de variantes con 14 meses de datos produce ganadoras de ruido.** Las 5 reglas del embudo medibles en M1 no tenían
   señal ni bruta en 2006–2025. Paso 2: lo elegido por el embudo no conserva nada en la réplica.
2. **El «antes no, ahora sí» es fricción relativa, no régimen de mercado.** La fricción es fija en puntos y el rango diario creció:
   fricción/ATR en NQ bajó de ≈ 0,045 (2006–2011) a 0,006 (2020–2025). Una señal bruta chica y estable sólo es rentable hoy.
3. **El régimen de mercado (volatilidad y tendencia) no explica nada de forma significativa** (9 pruebas NO_CONCLUYENTE). Sólo dejó una
   sospecha en PREAPERTURA-NQ e IF-LUX-NQ.
4. **Hay una señal estable en 20 años y en años nunca usados: SOM** (bruto +0,064 R, IC90 [+0,033, +0,095], 3 índices). El módulo R de
   FundedSync la tiene en NQ.

## 2. Veredicto por regla y qué cambia

### Embudo: cartera v2 (8 reglas), v3 (+3) y v4 (10)
| Regla | Canasta | Evidencia | Veredicto | Decisión futura |
|---|---|---|---|---|
| CVGAP-ES-C | v2, v3 | atrás EN_CONTRA (potencia 1,0), bruto ≈ 0 | **REFUTADA** | sale en la próxima versión |
| CVGAP2-GC#11 | v4 | atrás EN_CONTRA (0,99); holdout −1,45 R | **REFUTADA** | sale |
| COMEX-CIERRE-GC-R#0 | v4 | atrás EN_CONTRA (0,97); holdout −0,63 R | **REFUTADA** | sale |
| PREAPERTURA-NQ | v2, v3 | atrás IC90 entero < 0 sin potencia; régimen análogo +0,35 contra −0,34 (no significativo) | **EN CONTRA, con sospecha de régimen** | papel sin tamaño; la prueba de régimen se repite con datos nuevos (forward en meses análogos) |
| IF-LUX-NQ-R2#1 | v4 | atrás NO_CONCLUYENTE; régimen +0,19 contra −0,38 | **DÉBIL** | papel sin tamaño |
| U1-RACIMOS-GRILLA-NQ, U1-ZONAS-BT2-ES/NQ, U1-ORO-GRILLA, CONF-CVR-CFD-NQ-R, CVGAP-CFD-ES-C (v2); DRC-NQ-R, U1-ZONAS-AVCL-ES-C/NQ (v3); ORO-ALM-CFD#4/#18, CVGAP2-NQ#18/#3, CVGAP2-GC#5, U1-ZONAS-GRILLA-YM, IF-LUX-CFD-NQ (v4) | — | no medibles en M1 (footprint, ticks o señal CFD); mismo proceso de selección; holdout de la v4 −4,6 R | **SIN EVIDENCIA PROPIA, expectativa ≈ 0** | papel con e-proceso; ningún tamaño real; se confirman sólo con la partición A5 cuando haya ticks largos, o con el forward |

- **Para las canastas:**
  - la v2 pierde CVGAP-ES-C y queda sin ninguna regla con evidencia propia;
  - la v4 pierde 2 reglas y su holdout arrancó en contra;
  - ninguna habilita tamaño real.

### Externas
| Regla | Evidencia | Veredicto | Decisión futura |
|---|---|---|---|
| **SOM** (sin_finde) | señal bruta estable 2006–2025 en NQ, ES y YM; años limpios +0,064 R bruto; neto hoy en NQ ≈ +0,04 R; holdout +0,16 R | **LA MEJOR PISTA DEL PROYECTO** (bruto confirmado; neto chico y dependiente de la fricción) | confirmar en un índice no mirado (RTY/MidCap de NT8) en neto con la fricción actual, y forward; operarla sólo cuando la fricción en R de la operación sea baja (filtro declarado antes) |
| **R** AtrPhase (FundedSync) | bruto positivo en NQ en los 3 períodos; años limpios +0,097 ATR bruto (3 índices); en ES y YM decae después de 2011; sin stop | **PISTA en NQ** | sólo NQ y con el stop de catástrofe (0,5 × ATR20): baja la peor operación de −415 a −169 pts y casi no cambia el neto |
| **Z** ZetaTrend (FundedSync) | bruto positivo en NQ y ES, más débil en YM; años limpios +0,028 (IC cruza 0) | **PISTA DÉBIL** | con stop de catástrofe; como complemento, no como pilar |
| **T** FtmEngine (FundedSync) | sin señal bruta antes de 2020 (+0,007 ATR en 2008–2011); régimen análogo no la apoya; la cartera de fábrica del vendedor ni la incluye | **FRÁGIL** | deja de ser el pilar de la cartera B: pre-registrar una B' sin T (R + Z con stop) y comparar en forward; T queda en papel |
| O, V, A20, C (FundedSync) | bruto ≈ 0 o chico; netos positivos sólo con la fricción reciente | sin ventaja demostrada | no se operan |
| W, N (FundedSync) | la variante de salida mejora (confirmado en años limpios) pero sigue ≈ 0 o negativa | **SIN VENTAJA** | no se operan |
| A1, P, Q, E, F, S (FundedSync) | negativos o ≈ 0 | **SIN VENTAJA** | no se operan |
| **Cartera completa de FundedSync** (motor del vendedor) | pierde todos los años 2006–2018, gana desde 2019–2020; drawdown −128 k USD con el perfil 25K | **NO OPERABLE tal cual** | no se usa el motor de cartera del vendedor ni sus perfiles de tamaño |
| Franklin | holdout +0,27 R (no concluyente); desarrollo 2020+ | **sin medir en M1** | siguiente: la misma medición de 20 años, bruto y neto |
| QLB (EA de oro) | gatillos compilados, sin fuente | **NO MEDIBLE** | se descarta como candidata |
| TURTLES-ORO | 0,4 operaciones por mes (K27) | fuera | — |

## 3. Cómo cambian las decisiones de aquí en adelante
1. **Dinero real:** ninguna regla del embudo, y ninguna canasta, habilita tamaño real hoy. La única candidata con base para proponerlo es SOM,
   después de confirmarse en un índice no mirado y en forward.
2. **Versiones nuevas en papel** (cada una con su pre-registro):
   - v2.1 sin CVGAP-ES-C;
   - v4.1 sin CVGAP2-GC#11 ni COMEX;
   - B' = R + Z con stop de catástrofe, sin T;
   - una canasta «señal estable» con SOM + R (NQ) que se siga en forward.
3. **Filtro de fricción en R antes de entrar:** pasa a ser parte de toda regla operable (paso 3 de urgencia/evidencia), con umbral
   declarado.
4. **Búsqueda nueva:**
   - sólo con la partición A5 sobre M1 largo y mecanismos medibles en barras;
   - se exige señal BRUTA estable en todos los períodos antes de mirar el neto;
   - no se vuelve a elegir sobre 14 meses.
5. **Datos que faltan:** RTY y MidCap de NT8 (confirmar SOM y R), y ticks más largos para medir las reglas de footprint.
