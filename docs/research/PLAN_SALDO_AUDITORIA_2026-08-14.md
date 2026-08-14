# Plan de saldo de las debilidades de la auditoría externa — 2026-08-14

**Estado:** EN EJECUCIÓN desde 2026-08-14 (instrucción de Nico: saldar las debilidades una por una).
**Objeto:** convertir D1–D9 de `docs/research/AUDITORIA_EXTERNA_2026-08-14.md` §6 en una cola ordenada por dependencia, con dueño, insumos y criterio de cierre por ítem. Este archivo es el instrumento de seguimiento: cada saldo cierra con commit que actualiza su estado, y un FAIL se registra, nunca se re-corre con gates relajados.

**Regla de alcance del sandbox:** lo que corre en el sandbox de Notion es diagnóstico target-free, no adjudicador (precedente: ensayo estructural F2.7 del 2026-08-12). Los PASS formales salen de la máquina local gobernada. Nada en este plan abre outcomes, P&L ni holdout.

---

## Cola ordenada por dependencia

### W1 — Identidad del kernel NT8 y paridad (cierra D3, P-08, P-09)

**Estado W1 (2026-08-14, primera vuelta): EN CURSO — réplica sandbox ejecutada.**
Evidencia: `docs/research/W1_PARIDAD_SANDBOX_2026-08-14.md`.

1. ~~(local) identidad del `.cs`~~ → **P-08 RESUELTA** (commit `2ad04ec`: blob `ee984f6e` byte-idéntico al archivo que corre en NT8).
2. (local) Regenerar `diag/tasa_senales/AVOLT_formal_d5c41684e162.json` → **P-09 sigue ABIERTA** (no estaba en los commits del 14-08).
3. (local) Oráculos exportados: BT2 time:1 90d ✓, aVol 6E ✓, aVol ES 06-26 ✓, **aVol ES 09-26 ✗ (duplicado del 06-26 → P-11)**. Faltan los bar_specs tick:5/10 del plan vigente.
4. (sandbox) Réplica ejecutada sobre el paquete W1: **aVol 72/72 creaciones exactas (Δscore = 0) con 4 extras marginales (WARN diagnóstico)**; **BT2 BLOCKED: el oráculo no emite TRAPs después del 16-abr (→ P-13)**; el parquet llegó solo con junio y manifiesto desactualizado (→ P-12). Próxima iteración cuando lleguen los paquetes corregidos.

### W2 — Curva de especificación descriptiva (cierra D4)

Corre en local (o réplica diagnóstica en sandbox si llegan los parquets). ~500 celdas, ~2 h en 4 cores, `outcomes_accessed=false`. Es el insumo para decidir A/B/C/D del soporte común con números en vez de opinión.

### W3 — ES: P2 honesto y baseline con identidad (cierra D2)

Ruta del dictamen AVOLT: H2 (mismo contrato declarado en el meta), H3 (lookback caliente o evaluación post-calentamiento), H4 (bloques disjuntos de 10 — respondida a nivel `.cs`; queda verificar la implementación del replay). La decisión "mayo = `ES_06-26` como historia, no concatenar" se verifica estructuralmente (monotonía, solapes, duplicados en la frontera).
**Bloqueo nuevo**: P-11 (el oráculo de ES 09-26 no existe).

### W4 — Visibilidad y CI (cierra D9, P-05)

- W0 de Workers (plan + habilitación + deploy): decisión humana.
- P-05: los pushes `03d1104`, `84dcfcd` y `2ad04ec` ya dispararon el workflow; falta confirmar en la pestaña Actions que instaló el lock exacto y terminó verde, y registrar el enlace.

### W5 — Merges (cierra D6, P-10)

Tres decisiones de Nico (`fix/g2-a1-*`, `research/ym-prerange-session-window`, `docs/lux-imb-source-correction`). El auditor externo ya leyó las ramas; diffs disponibles a pedido.

### W6 — Licencia de datos (cierra P-07/M0)

Decisión humana: `DATA_LICENSE_DECISION.md` con proveedor, alcance, restricciones y fecha. Insumo nuevo: los docs de política CME/Kaggle commiteados en `bda944a`.

### W7 — Capa de costos + reglas prop (cierra D7)

- (sandbox) Estructura del manifiesto de costos por instrumento + wrapper de reglas prop (trailing DD en tiempo real vs EOD, consistencia, límite diario) sobre `execution_simulator_spec.md`.
- (Nico) Los costos reales por instrumento (broker/exchange/NFA/spread/slippage observado). Sin transportar los de 6E.

### W8 — F4 constitucional (cierra D1) ← último a propósito

Manifiesto de campaña + número efectivo de hipótesis + riesgos + datos faltantes → OK explícito de Nico (regla STOP) → primera medición de información condicional. Depende de W1 (instrumentos confiables) y de que exista un objeto con sello.

*Nota:* D8 (potencia) no es tarea: es convención de diseño, ya adoptada en L3 (MDE publicado, `UNDERPOWERED` declarable por construcción).

---

## Paquete de validación de paridad (qué subir y con qué identidad)

Para cada contrato × bar_spec:

1. **El `.cs` exacto que generó el oráculo, commiteado y pusheado.** La verificación es contra el blob del repo; los adjuntos sirven solo de referencia (ya pasó: el `aVolClusterPOI.cs` adjunto resultó byte-idéntico al blob `d512d91a` tras normalizar EOL; el `BigTrap2.cs` adjunto no coincide con ningún blob → P-08, cerrada el 14-08).
2. **El CSV del oráculo tal cual lo escribe el indicador**: meta line intacta en la primera línea; un archivo por resolución por corrida (el `.cs` ya lo hace con el sufijo `__<bar_spec>`); nunca append ni merge de corridas. **Para BT2: el log de eventos COMPLETO, todos los tipos** (P-13: sin `SESION_RESINCRONIZADA`/`ANCLAJE_*` no se puede adjudicar el silencio de TRAPs).
3. **El parquet del contrato, con su sha256 declarado por el ejecutor y el manifiesto de build regenerado desde el archivo final** (P-12: el primer paquete llegó con el manifiesto de otro build). Se recomputa acá; mismatch → cuarentena (misma regla que el preflight del 14-08: hash inválido → ABSTAIN_INPUT antes de leer nada).
4. **Ventana declarada del oráculo** (inicio/fin), timezone del archivo, **y arranque exacto de la instancia NT8** (W1 midió que el warmup es de primer orden: arrancar el perfil una semana antes multiplica las emisiones espurias ×18 — 4 → 71).

**Orden sugerido de entrega:** primero `6E_09-26` (hash canónico `6ffcdf04…`) + time:1 (el camino con O1 PASS histórico), después tick:5/10, después `ES_09-26` (+ `ES_06-26` si se evalúa la historia de mayo).

---

## Criterios de cierre

Cada W cierra con: etiqueta (`PASS` / `FAIL` / `BLOCKED`), evidencia referenciada, y actualización de este archivo + `PENDIENTE.md` si aplica. Ninguna etiqueta de efecto se emite desde el sandbox: acá se valida identidad, estructura y paridad (P1A/P2), nunca outcomes.

---

Aporte al referente: convierte la lista de debilidades en una cola ordenada por dependencia, con dueños y criterios de cierre; el primer eslabón (identidad del kernel → paridad) es el que destraba al resto. W1 ya produjo su primera medición: paridad de aVol al nivel más fino registrado (72/72, Δscore = 0) y la divergencia de BT2 localizada con prueba decisiva identificada.
