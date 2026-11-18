# Veredicto de todas las reglas con la evidencia del M1 real de futuros (2026-11-17)

Estado: VIGENTE (actualizado el 2026-11-18 con el «atrás» v2: motor corregido por K40; mismos veredictos, pérdidas la mitad, PREAPERTURA-NQ ≈ 0) — pedido de Nico: «emití un veredicto de todos los resultados y cómo eso afecta las decisiones futuras sobre esas reglas».
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Fuentes:
- `docs/research/atras_m1_20261117/RESULTADO.md` (el «atrás» de 5 reglas del embudo, v2 con el motor corregido; la v1 está en `descartada_v1/`);
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
4. **Hay señales estables en 20 años y en años nunca usados: SOM (también en el MidCap y el Russell) y Franklin** (bruto +0,064 R, IC90 [+0,033, +0,095], 3 índices). El módulo R de
   FundedSync la tiene en NQ.

## 2. Veredicto por regla y qué cambia

### Embudo: cartera v2 (8 reglas), v3 (+3) y v4 (10)
| Regla | Canasta | Evidencia | Veredicto | Decisión futura |
|---|---|---|---|---|
| CVGAP-ES-C | v2, v3 | atrás v2 EN_CONTRA (potencia 1,0; −0,04 R/op, IC90 cruza 0) | **REFUTADA** | sale en la próxima versión |
| CVGAP2-GC#11 | v4 | atrás v2 EN_CONTRA (0,99; −0,13 R/op); holdout −1,45 R | **REFUTADA** | sale |
| COMEX-CIERRE-GC-R#0 | v4 | atrás v2 EN_CONTRA (0,97; −0,18 R/op); holdout −0,63 R | **REFUTADA** | sale |
| PREAPERTURA-NQ | v2, v3 | atrás v2 ≈ 0 (−0,002 R/op, IC90 [−0,16, +0,17], potencia 0,57; el «IC90 entero < 0» de la v1 era K40); régimen análogo +0,35 contra −0,34 (no significativo) | **SIN VENTAJA DEMOSTRADA, con sospecha de régimen** | papel sin tamaño; la prueba de régimen se repite con datos nuevos (forward en meses análogos) |
| IF-LUX-NQ-R2#1 | v4 | atrás v2 NO_CONCLUYENTE (−0,09 R/op); régimen +0,19 contra −0,38 | **DÉBIL** | papel sin tamaño |
| ASIA-NQ-CANASTA | papel | M1 de futuros = ticks (corr 0,985, K47); bruto −0,02 a −0,11 R/op en NQ/ES/YM 2006–2011, EMD y RTY; «noche movida» era fuga (K48), la causal +0,035 R NO_CONFIRMADA (`asia_noche_20261118`) | **SIN VENTAJA HISTÓRICA** | sin tamaño; sacarla en la próxima versión |
| OTR930-NQ-CANASTA | papel | validada en M1; negativa 2012 → 2025-07, sin régimen (p 0,40–0,96; `papel_m1_20261115/LARGO_V2.md`) | **SIN RESPALDO HISTÓRICO** | papel sin tamaño; la decide el forward |
| U1-RACIMOS-GRILLA-NQ, U1-ZONAS-BT2-ES/NQ, U1-ORO-GRILLA, CONF-CVR-CFD-NQ-R, CVGAP-CFD-ES-C (v2); DRC-NQ-R, U1-ZONAS-AVCL-ES-C/NQ (v3); ORO-ALM-CFD#4/#18, CVGAP2-NQ#18/#3, CVGAP2-GC#5, U1-ZONAS-GRILLA-YM, IF-LUX-CFD-NQ (v4) | — | no medibles en M1 (footprint, ticks o señal CFD); mismo proceso de selección; holdout de la v4 −4,6 R | **SIN EVIDENCIA PROPIA, expectativa ≈ 0** | papel con e-proceso; ningún tamaño real; se confirman sólo con la partición A5 cuando haya ticks largos, o con el forward |

- **Para las canastas:**
  - la v2 pierde CVGAP-ES-C y queda sin ninguna regla con evidencia propia;
  - la v4 pierde 2 reglas y su holdout arrancó en contra;
  - ninguna habilita tamaño real.

### Externas
| Regla | Evidencia | Veredicto | Decisión futura |
|---|---|---|---|
| **SOM** (sin_finde) | señal bruta estable 2006–2025 en NQ, ES y YM; años limpios +0,064 R bruto; **transfiere al MidCap y al Russell (bruto +0,030 R, IC90 +0,006/+0,055, A_FAVOR, 2026-11-18)**; neto hoy en NQ ≈ +0,04 R; holdout +0,16 R | **LA MEJOR PISTA DEL PROYECTO** (bruto confirmado; neto chico y dependiente de la fricción) | confirmar en un índice no mirado (RTY/MidCap de NT8) en neto con la fricción actual, y forward; operarla sólo cuando la fricción en R de la operación sea baja (filtro declarado antes) |
| **R** AtrPhase (FundedSync) | bruto positivo en NQ en los 3 períodos; años limpios +0,097 ATR bruto (3 índices); en ES y YM decae después de 2011; **no transfiere con fuerza a EMD + RTY (+0,011 ATR, NO_CONCLUYENTE con potencia 0,93)**; sin stop | **PISTA SÓLO NQ** | sólo NQ y con el stop de catástrofe (0,5 × ATR20): baja la peor operación de −415 a −169 pts y casi no cambia el neto |
| **Z** ZetaTrend (FundedSync) | bruto positivo en NQ y ES, más débil en YM; años limpios +0,028 (IC cruza 0) | **PISTA DÉBIL** | con stop de catástrofe; como complemento, no como pilar |
| **T** FtmEngine (FundedSync) | **revisado 2026-11-18** (`m1_largo_20261117/RESULTADO_T_2020.md`): en R (su unidad) tiene bruto positivo en NQ en 13 de 14 años desde 2012 y crece desde 2020 en NQ, ES y YM; el tope de 100 pts no lo explica; en MidCap + Russell 2020–2025 NO_CONCLUYENTE (+0,033 R); neto NQ 2020–2025 ≈ +0,15 R; holdout +14 pts | **PISTA FUERTE EN NQ** (la versión anterior, «frágil», salió de medir en ATR) | vuelve a ser pilar de la B; B' sólo como comparación; se suma a la canasta de señales estables |
| A20, E, F, V, C (FundedSync) | **revisado 2026-11-18 en R** (`AUDITORIA_Y_VIEJAS.md`): señal en NQ 2020–2025 (A20 +0,083 R neto, E +0,045, F +0,050, V +0,021); ≈ 0 antes de 2020 y en ES/YM (salvo E, débil): compatible con ajuste del vendedor a NQ reciente | **PISTAS NQ, por debajo de T** | forward, no tamaño |
| O (FundedSync) | bruto chico; positivo sólo con la fricción reciente | sin ventaja demostrada | no se opera |
| W, N (FundedSync) | la variante de salida mejora (confirmado en años limpios) pero sigue ≈ 0 o negativa | **SIN VENTAJA** | no se operan |
| A1, P, Q, E, F, S (FundedSync) | negativos o ≈ 0 | **SIN VENTAJA** | no se operan |
| **Cartera completa de FundedSync** (motor del vendedor) | pierde todos los años 2006–2018, gana desde 2019–2020; drawdown −128 k USD con el perfil 25K | **NO OPERABLE tal cual** | no se usa el motor de cartera del vendedor ni sus perfiles de tamaño |
| **Franklin** | años limpios 2006–2011 en futuros: bruto +0,195 R (IC90 +0,095/+0,296, 83 % de años), A_FAVOR; neto 2020–2025 +0,082 R (fricción 0,04 R); holdout +0,27 R | **SEÑAL BRUTA ESTABLE (confirmada 2026-11-18)** | junto a SOM, la candidata con mejor base; operar sólo con fricción en R baja; forward |
| QLB (EA de oro) | gatillos compilados, sin fuente | **NO MEDIBLE** | se descarta como candidata |
| EdgeReplica (60 reglas NQ) | NQ 2006–2022 ≈ 0 (potencia 1,0); señal sólo 2024–2026, donde se eligió | **DESCARTADA: ajuste, no patrón** | no se opera |
| Oro, corto 04:15 CT | GC 2008–2022: sesgo bruto +1,62 ticks confirmado; neto −4,4 (costo ≈ 6 ticks) | **SESGO REAL, NO OPERABLE SOLO** | como información de horario para otras operaciones de oro |
| MGC EMA 200/500/2000 | barras de 25 operaciones: no medible con M1 | sin cambios («no se valida») | haría falta ticks viejos |
| LuxImb impulsos con zonas en el 25 % | **medida 2026-11-18 (A5, `luximb_a5_20261118/RESULTADO.md`)**: reversión bruta real en 17 años (REP confirma), zonas suman en DESC; neto refutado por fricción | **PISTA BRUTA, NO OPERABLE** | holdout A5 sin abrir; sólo un hijo con stop amplio o como filtro de contexto |
| TURTLES-ORO | 0,4 operaciones por mes (K27) | fuera | — |

## 3. Cómo cambian las decisiones de aquí en adelante
1. **Dinero real:** ninguna regla del embudo, y ninguna canasta, habilita tamaño real hoy. La única candidata con base para proponerlo es SOM,
   y Franklin: el bruto ya se confirmó en datos no usados; falta el forward con el filtro de fricción.
2. **Versiones nuevas en papel** (cada una con su pre-registro):
   - v2.1 sin CVGAP-ES-C;
   - v4.1 sin CVGAP2-GC#11 ni COMEX;
   - B' = R + Z con stop de catástrofe, sin T, sólo como comparación (corrección del 2026-11-18: T es pista fuerte en NQ, B con T es la principal);
   - una canasta «señal estable» con SOM + R (NQ) que se siga en forward; a sumar Franklin con su propio pre-registro.
3. **Filtro de fricción en R antes de entrar:** pasa a ser parte de toda regla operable (paso 3 de urgencia/evidencia), con umbral
   declarado.
4. **Búsqueda nueva:**
   - sólo con la partición A5 sobre M1 largo y mecanismos medibles en barras;
   - se exige señal BRUTA estable en todos los períodos antes de mirar el neto;
   - no se vuelve a elegir sobre 14 meses.
5. **Datos que faltan:** RTY y MidCap de NT8 (confirmar SOM y R), y ticks más largos para medir las reglas de footprint.
