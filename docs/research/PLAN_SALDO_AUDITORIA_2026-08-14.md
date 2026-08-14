# Plan de saldo de las debilidades de la auditoría externa — 2026-08-14

**Estado:** EN EJECUCIÓN desde 2026-08-14 (instrucción de Nico: saldar las debilidades una por una).
**Punto de entrada para continuidad:** `docs/research/HANDOFF_AUDITORIA_2026-08-14.md`.
**Objeto:** convertir D1–D9 de `docs/research/AUDITORIA_EXTERNA_2026-08-14.md` §6 en una cola ordenada por dependencia, con dueño, insumos y criterio de cierre por ítem. Cada saldo cierra con commit que actualiza su estado; un FAIL se registra, nunca se re-corre con gates relajados.

**Regla de alcance del sandbox:** lo que corre en el sandbox de Notion es diagnóstico target-free, no adjudicador (precedente: ensayo estructural F2.7 del 2026-08-12). Los PASS formales salen de la máquina local gobernada. Nada en este plan abre outcomes, P&L ni holdout.

---

## Cola ordenada por dependencia

### W1 — Identidad del kernel NT8 y paridad 6E (cierra D3, P-08, P-09) — CERRADA (diagnóstico, 2026-08-14)

1. Identidad del `.cs`: **P-08 RESUELTA** (blob `ee984f6e` → luego `62b0c951` con el fix de frontera).
2. P-09 (JSON AVOLT): sigue ABIERTA (regenerar desde el runner).
3. Réplicas sandbox con identidad sellada: aVol 6E junio **72/72 exactas**; BT2 junio (post-fix) **3.628/3.638 EXACT (99,73 %)**; BT2 abril+mayo (P-12) **171/171 EXACT (100 %)**. P-13 RESUELTA (raíz + fix verificado + paridad medida); P-14 ABIERTA con causa raíz identificada (defecto del build junio-only, no de la fuente).

### W3 — ES: replay aVol ES 09-26 — CERRADA (diagnóstico, 2026-08-14)

Paquete mensual verificado (3 parquets + oráculo genuino). Replay con kernel byte-exacto: **100 % exacta antes del defecto de datos del 11-jun (119/119, todos los campos), 98,7 % después (307/311)**; global 442/467 con Δtiempo/Δbucket/Δdistance = 0 en todas las emparejadas. Warmup replicado sin ajuste (session_index 22 / samples 25 del oráculo reproducidos). **P-15 ABIERTA**: defecto del 11-jun en el parquet ES de junio (fase de bloques corrida ~2 barras; regenerar + chequeo de minutos faltantes, misma batería que P-14). Cosméticos registrados: `direction=NEUTRAL` en AT_PRICE; conteo de sesiones en la frontera dominical. Evidencia: `docs/research/W3_PARIDAD_SANDBOX_2026-08-14.md`.

Queda de la pata ES: la ruta del dictamen AVOLT (H2/H3/H4) y la verificación estructural de "mayo = ES_06-26 como historia, no concatenar", cuando haya ventana.

### W2 — Curva de especificación descriptiva (cierra D4)

Corre en local (o réplica diagnóstica en sandbox si llegan los parquets). ~500 celdas, ~2 h en 4 cores, `outcomes_accessed=false`. Insumo para decidir A/B/C/D del soporte común con números.

### W4 — Visibilidad y CI (cierra D9, P-05)

- W0 de Workers: decisión humana.
- P-05: los pushes del día ya dispararon el workflow; falta confirmar en Actions que instaló el lock exacto y terminó verde, y registrar el enlace.

### W5 — Merges (cierra D6, P-10)

Tres decisiones de Nico (`fix/g2-a1-*`, `research/ym-prerange-session-window`, `docs/lux-imb-source-correction`).

### W6 — Licencia de datos (cierra P-07/M0)

Decisión humana: `DATA_LICENSE_DECISION.md`. Insumo: docs de política CME/Kaggle commiteados en `bda944a`.

### W7 — Capa de costos + reglas prop (cierra D7)

- (sandbox) Estructura del manifiesto de costos por instrumento + wrapper de reglas prop sobre `execution_simulator_spec.md`.
- (Nico) Los costos reales por instrumento. Sin transportar los de 6E.

### W8 — F4 constitucional (cierra D1) ← último a propósito

Manifiesto de campaña + número efectivo de hipótesis + riesgos + datos faltantes → OK explícito de Nico (regla STOP) → primera medición de información condicional. Depende de W1/W3 (ya cerradas a nivel diagnóstico) y de que exista un objeto con sello.

*Nota:* D8 (potencia) no es tarea: es convención de diseño, ya adoptada en L3.

---

## Paquete de validación de paridad (qué subir y con qué identidad)

Para cada contrato × bar_spec:

1. **El `.cs` exacto que generó el oráculo, commiteado y pusheado** (la verificación es contra el blob del repo).
2. **El CSV del oráculo tal cual lo escribe el indicador**: meta intacta; un archivo por resolución por corrida; nunca append ni merge. Ojo: el formato difiere por indicador (BT2 = pipe; aVol = CSV coma con header — documentado en W3 §5).
3. **El parquet del contrato, con sha256 declarado y manifiesto regenerado desde el archivo final.** Mismatch → cuarentena. Nuevo gate adoptado (tras P-14/P-15): **0 minutos faltantes en horario activo contra la serie nativa**.
4. **Ventana declarada + timezone + arranque exacto de la instancia NT8** (W1/W3 midieron que el warmup es de primer orden).

---

## Criterios de cierre

Cada W cierra con: etiqueta (`PASS` / `FAIL` / `BLOCKED`), evidencia referenciada, y actualización de este archivo + `PENDIENTE.md` si aplica. Ninguna etiqueta de efecto se emite desde el sandbox: acá se valida identidad, estructura y paridad (P1A/P2), nunca outcomes.

---

Aporte al referente: la lista de debilidades quedó convertida en una cola ordenada por dependencia; W1 y W3 cerraron con cuatro mediciones de paridad al nivel más fino que el proyecto tuvo — dos instrumentos, dos indicadores, cuatro ventanas — y cada divergencia quedó clasificada entre defecto de datos a regenerar y artefacto cosmético a unificar.
