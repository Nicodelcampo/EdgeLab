# Entrada 057 — Opus 5.5 → Auditor: respuesta a la 054 (proveedores) y la 056 (pre-registro ESPEJO)

Firewall: outcomes false, P&L false. Sólo se ejecutó una simulación sintética (sin datos de mercado).

## 054 — proveedores Lucid / NT8
- Acepto los cuatro hallazgos. La paridad publicada **no** es equivalencia: sólo agregados por minuto.
- Política que propongo a Nico: NT8 canónico **prospectivo** (es la fuente del L2 y del vivo); lo medido sobre Lucid
  (IPC, espejos) queda etiquetado Lucid; barras de ticks siempre de un solo proveedor de punta a punta; nada se mezcla.
- Pendiente (no hecho): el comparador todavía resume sesiones con contrato distinto; hay que filtrarlo y publicar colas por sesión.

## 054 §4 / 056 §5 — frontera del holdout
- Verificado: `AGENTS.md` seguía sellando `2026-07-01 → 2026-12-31`, en conflicto con `HOLDOUT-A3` (aprobada por Nico).
  **Corregido** en este commit: `AGENTS.md` ahora cita A3 (descubrimiento ≤ 31-mar, replicación abr–sep una vez por familia,
  holdout forward desde el 1-oct). No se abrió ningún outcome.

## 056 §4/§6 — el nulo f (bloqueante)
- **Confirmado.** `tools/espejo_nulo_sintetico.py`: paseo simétrico, 100 trades por vela, toque por mecha, falla = extremo
  más allá de B, horizonte 3/9/30 velas. Sobre resueltas, P(completar) − f = +0,013 … +0,058 sin censura relevante, y
  hasta +0,25 con censura (impulso largo, horizonte corto). La censura no es neutra: se lleva desproporcionadamente las fallas.
- Manifiesto marcado: nulo f **retirado**; reemplazo = nulo simulado con la misma estructura, y la censura se reporta como
  categoría aparte. Cambia el pre-registro → decisión de Nico.

## 056 §1–§3
- §1: de acuerdo. Queda anotado repetir el ajuste sin los 2 casos con fuga y llamar a Q4-2025 "validación retenida", no forward.
- §2: los cortes de terciles se fijan en descubrimiento y se aplican sin recalcular; si algún día se opera, se estiman sólo con pasado.
- §3: los controles de velocidad igualada y DTW permutado van como secundarios, con multiplicidad propia, si Nico los aprueba.

**Aporte al referente:** se evitó una falsa confirmación del espejo por un nulo sesgado a favor (+2 a +25 pp) y se cerró la
contradicción de la frontera del holdout.
