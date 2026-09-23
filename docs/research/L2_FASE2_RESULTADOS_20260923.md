# L2 Fase 2: resultados (información condicional del libro tras la latencia, GC 08-26)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

**Pre-registro:** `PREREG_L2_FASE2_INFO_CONDICIONAL_GC_20260923.md` (congelado en `aa080a1`). Se corrió según ese texto.

**Procedencia:**
- Código: `tools/l2_phase2_info.py` (commit `3ea939f`, árbol con archivos sin trackear, `tree_dirty=true`).
- Artefacto: `artifacts/l2_phase2/results.json`.
- Datos: `E:\DatosNT8\gc_aug26_canonical_parquets`. Hay 30 sesiones usables y todas se usaron.
  - Desarrollo: del 27/05 al 18/06.
  - Test: del 19/06 al 30/06, abierto una sola vez.
- El holdout no se tocó.

## Resultado primario (ΔIC = IC(M1) − IC(M0), media por sesión de test, IC 99,17 % con Bonferroni sobre 6 pruebas)

| Prueba | IC M0 | IC M1 | ΔIC | IC | MDE (pre-reg.) | ¿Rechaza H0? |
|---|---:|---:|---:|---|---:|---|
| 30 s, direccional | 0,011 | −0,013 | **−0,024** | [−0,038; −0,010] | 0,023 | No. El L2 **empeora** la predicción. |
| 60 s, direccional | 0,015 | 0,012 | −0,003 | [−0,014; 0,011] | 0,011 | No |
| 300 s, direccional | 0,024 | 0,024 | −0,001 | [−0,027; 0,032] | 0,040 | No |
| 30 s, no direccional | 0,442 | 0,442 | −0,000 | [−0,001; 0,000] | 0,274\* | No |
| 60 s, no direccional | 0,431 | 0,431 | −0,001 | [−0,001; −0,000] | 0,391\* | No |
| 300 s, no direccional | 0,434 | 0,433 | −0,001 | [−0,003; 0,001] | 0,508\* | No |

\* El MDE pre-registrado del canal no direccional está inflado por **una** sesión de desarrollo: 20260607, apertura de domingo, con spread medio de 114 ticks y microprice desplazado ~19 ticks. Ahí M1 invierte el IC (ΔIC −0,86 a −1,60). Como diagnóstico, sin esa sesión el MDE sería 0,002–0,006. La sesión no es defectuosa según las reglas de QA fijadas, así que el número oficial no se toca.

**Ablaciones (diagnósticas), ΔIC medio:**
- **Latencia 0 ms ≈ latencia 250 ms ≈ latencia 500 ms** en las seis pruebas (por ejemplo, 30 s direccional: −0,022 / −0,024 / −0,023). **El problema no es la latencia:** el libro no agrega información ni siquiera sin retraso.
- **Placebo** (el libro de otra sesión): ≈ 0 (−0,006 a +0,002), como se esperaba.
- **Sin bloques horarios:** no cambia la conclusión.

## Lectura

1. **Canal direccional.** El libro (OFI, desequilibrio de cola, microprice, spread, profundidad) **no agrega información** sobre el cambio del mid a 30, 60 ni 300 s por encima del flujo de trades. A 60 s el nulo es **informativo**: el intervalo va de −0,014 a 0,011 con MDE 0,011, así que un aporte del orden de 0,01 de IC queda descartado. A 300 s el test tiene **poca potencia**: no descarta aportes de hasta ~0,03. A 30 s el libro empeora fuera de muestra: los features L2 son inestables entre sesiones.
2. **El modelo base ya sabe poco:** el IC de M0 direccional es 0,01–0,024. El canal no direccional es otra cosa: la volatilidad se agrupa (IC ~0,43 solo con trades) y el libro no le suma nada.
3. **No es un problema de latencia.** Es lo que más cambia la lectura de los informes: ni con L = 0 hay información incremental a estos horizontes. La información del libro que la literatura documenta vive en ~2 cambios de mid (0,14–0,8 s en GC, Fase 0), muy por debajo de 30 s.

## Veredicto (con alcance preciso)

**Muere:** "el L2 (estos 9 features, ridge, estado continuo por segundo) agrega información sobre el cambio del mid a 30–300 s por encima del flujo de trades", para **GC 08-26, del 27/05 al 30/06/2026, feed NT8, L ∈ {0, 250, 500} ms**.

**No muere** (fuera del alcance de esta prueba, cada punto requiere pre-registro propio):
- El L2 como **filtro** de señales de otras familias (M3).
- El L2 para **ejecución**, pasiva o agresiva (M4).
- Los detectores (iceberg, absorción, liquidez fugaz) con **umbral causal**: se excluyeron de esta prueba por fuga.
- Otros instrumentos o períodos.
- Horizontes menores a 30 s: son inalcanzables por latencia, aunque tuvieran información.

**Consecuencia para el plan:** se cierra la vía "predicción direccional con el libro". El valor del L2 para EdgeLab queda en **costos, ejecución y contexto de otras señales**, que era lo que anticipaban los dos deep research.

## Cómo podría refutarse este veredicto

Con otro período o instrumento (más historia, por ejemplo 2027 o datos comprados), el mismo pre-registro sin cambios daría ΔIC > 0 con el límite inferior del IC por encima de 0 a 60–300 s.
