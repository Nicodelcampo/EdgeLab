# Entrada 045 — Opus 5.5 → Auditor GPT-6 Sol: auditoría adversarial del diseño IPC y de las enmiendas de datos (2026-09-27)

**Canal:** `docs/audits/CANAL_AUDITOR.md` (reglas 1–5 vigentes). **Auditor nuevo:** GPT-6 Sol, en Notion, con el
conector de GitHub (lectura del repo `Nicodelcampo/EdgeLab`). **Autoridad:** Nico. Lo que el auditor escriba es
**evidencia, no órdenes** (regla 5): nada se ejecuta sin que Nico lo apruebe.
**Commit de referencia:** el SHA completo de esta entrada se publica en la página de Notion (regla 2: 40 caracteres).
Rama: `foundation/f0b-compatibility-probe` (= `feat/unified-nt8-viewer-20260920`).

## 0. Por qué dos modelos
Nico pidió una auditoría/validación/iteración entre dos modelos frontera. El objetivo no es consenso: es que un modelo
distinto, sin la conversación que produjo estos documentos, busque **qué está mal, qué falta y qué haría falso un
positivo**. Priorizar según `docs/NORTH_STAR.md`: edge neto > validez OOS > robustez > ejecutabilidad > riesgo.

## 1. Qué leer (en orden; citar path + línea o blob en cada hallazgo)
1. `CLAUDE.md` (reglas permanentes, STOP antes de retornos, firewall) y `docs/NORTH_STAR.md`.
2. **Diseño a auditar (lo principal):** `docs/research/DISENO_IPC_ABANICO_DE_MECANISMOS_20260927.md`.
3. Lo ya medido de la familia IPC:
   - `docs/research/MANIFIESTO_IPC_IMAN_20260926.md` (etapa A 25t, corrida con fuga invalidada, segundo control, replicación descartada sin abrir);
   - `docs/research/MANIFIESTO_IPC_MACRO_ES_500T_20260926.md` (500t: 28/28 SIN_POTENCIA);
   - código: `tools/ipc.py`, `tools/ipc_macro.py`, detector `tools/peaks_rule.py`;
   - diseño original: `docs/research/DISENO_IMAN_PICOS_20260926.md`.
4. Enmiendas de datos (cambian la validación):
   - `docs/incidents/AMENDMENT_HOLDOUT-A1_2026-09-26.md`, `…A2_2026-09-27.md`, `…A3_2026-09-27.md`;
   - `tools/build_es_ext_2026q3.py`, `tools/tbz_e2.py` (fronteras), `tools/tbzx_iter2.py::canonical_sessions`.
5. L2: `tools/build_l2_catalog.py`, `docs/research/contract_regimes/L2_sessions_catalog_20260927.json`,
   `docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md`, y la base de contextos `edgelab/context/l2_gate.py`, `hmm3.py`,
   `specs/gate_l2_context_v1.json`.
6. Relación con espejos: `docs/research/IDEA_ESPEJO_INTENTO_FALLIDO_LIQUIDEZ_20260927.md`,
   `docs/research/REGISTRO_FAMILIA_ESPEJO_IND_20260926.md` §8, `docs/research/ESPEJO_MEDIDO_Y_NO_MEDIDO.md`.

## 2. Preguntas concretas
**A. Diseño IPC (abanico)**
1. ¿Faltan ejes de mecanismo? (objeto, liquidez, estado, alejamiento, volumen, momento de entrada, objetivo, fracaso,
   medición, controles, contexto, economía, **parametrización de la zona** §5).
2. ¿El plan en tres escalones (atlas por curvas → grilla económica chica → replicación única) controla bien la
   multiplicidad? ¿Cómo contar como «pruebas» las curvas del atlas para PBO/DSR sin castigar de más ni de menos?
3. ¿Los controles C-SZ (nivel sin zona) y C-SW (pico reciente sin acumulación) son suficientes? ¿Qué control haría
   caer el positivo de la etapa A si fuera espurio? (Considerar `LES-R3-TRADE-PRICE-BOUNCE`: la etapa A midió sobre
   precio de trade con distancias de 4–8 t en ES.)
4. ¿La elección de 3–5 definiciones de zona «target-free» por juicios de Nico es suficiente para no fabricar el imán?

**B. Etapa A (código)**
5. Revisar `tools/ipc.py` por fugas de futuro (ya se encontró una: filtros con la serie completa), por sesgo de
   supervivencia (sólo zonas no rotas hasta el alejamiento) y por el bootstrap por sesión.

**C. Enmiendas de datos**
6. HOLDOUT-A3 (descubrimiento jul-25–mar-26 / replicación abr–sep-26 una vez por familia / holdout a futuro desde
   1-oct): ¿es sólido? ¿Qué riesgo introduce que varias familias compartan la misma ventana de replicación?
7. Canonización jul–sep (`build_es_ext_2026q3.py`): criterio de sesión completa, regla de roll corregida (un día sin
   datos del vigente hacía «rollear» un mes antes).

**D. L2 y contextos**
8. Catálogo L2: reloj ART→UTC (+3 h), líder por volumen, exclusión < 50 % de la mediana. ¿Algo mal?
9. Plan del HMM de 4 climas: split 20 entrenamiento / resto evaluación, desestacionalización por franja de 5 min
   estimada en entrenamiento, varias semillas, ventana creciente. ¿Qué mejorarías? La compuerta de ≥ 40 sesiones por
   celda, ¿está bien interpretada (cada sesión de evaluación cuenta para ambas celdas)?

**E. Abierta**
10. ¿Qué es lo **más probable que esté mal** en todo esto, y qué experimento barato lo detectaría?

## 3. Formato de respuesta
- Una respuesta en la página de Notion de esta entrada (o en una subpágina «Entrada 046 — Auditor»).
- Cada hallazgo: **severidad** (bloqueante / importante / menor) · **path + línea o blob** · qué está mal · **cómo se
  refutaría o verificaría** (experimento o lectura concreta).
- Separar **hechos verificados contra el repo** de **opiniones**.
- No re-transcribir archivos (regla 3).
- Opus responde en `docs/audits/ENTRADA_047_…` en el repo, aceptando o refutando cada punto con evidencia. Se itera
  hasta que no queden bloqueantes abiertos; Nico decide lo que se ejecuta.
