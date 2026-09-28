# Manifiesto IPC-ROB: prueba de robustez del positivo de la etapa A 25t (2026-09-28)

**North Star:** `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
**Estado:** PRE-REGISTRO, escrito antes de correr. **OK de Nico: 28/09** («OK a la prueba de robustez»).
**Origen:** auditoría 046 (GPT-6 Sol) y respuesta 047 §3. **Sólo descubrimiento** (sesiones ≤ 2026-03-31); abr–sep no se toca.
**Ledger:** `artifacts/hippocampus/ipc_20260926.jsonl` (partición de exploración ya declarada).

## Pregunta
¿El positivo de la etapa A (23 celdas; reporte `ff25451223b2`) sobrevive cuando se corrigen, sobre los **mismos eventos**, las fallas que señaló la auditoría? Si desaparece, IPC 25t cae antes de hablar de P&L.

## Correcciones que se aplican (todas antes de ver resultados)
1. **Zonas as-of en los controles:** un nivel fantasma o pivote se excluye sólo por zonas **ya creadas** en el instante `q` del control (creación = pico que completa el mínimo + w), con sus picos confirmados hasta `q`.
2. **Precio medio:** la misma carrera se mide también sobre el midquote ((bid+ask)/2 del parquet canónico, por vela de 25t alineada con las velas de trades; se verifica la alineación vela a vela y se publica la fracción de cotizaciones inválidas).
3. **C-SW emparejado:** pivote de otra sesión, a la misma hora ± 1 h, mismo estado y actividad, **distancia al objetivo ± max(1 t, 10 %)**, **edad del pivote entre 0,5 y 2 veces la edad de la zona** en el evento, y **exposición**: velas restantes de la sesión ≥ 0,8 de las del evento.
4. **Volumen causal:** `vol_rel` = volumen medio por vela entre creación y evento / mediana del volumen por vela de la sesión **antes** de la creación. Terciles fijados sobre descubrimiento.
5. **Velas ambiguas** (tocan nivel y barrera a la vez): se cuentan y se publica el resultado con ambos desempates (0 y 1).
6. **Donantes:** se registra la sesión de cada control y su número de usos.

## Contrastes (por celda, sobre los mismos eventos elegibles)
| Código | Contraste |
|---|---|
| A | real (trade) − C-SZ (trade) — el original, con zonas as-of |
| B | real (trade) − C-SW actual (trade) |
| C | real (trade) − C-SW emparejado (trade) |
| **D (primario)** | **real (mid) − C-SW emparejado (mid)** |
| E | real (mid) − C-SZ (mid) |
Placebo incluido: C-SW emparejado es el «pivote solitario emparejado» de la 046. El placebo «zona sin alejamiento» **no se implementa en esta corrida** (queda anotado).

## Celdas
- Las **23** de `pasan_B` (ES estándar = D1, estricto = D2; NQ con su detector de la etapa A).
- **5 celdas D4** (comercio entre picos, validada en 68 %): las mismas combinaciones que las celdas ES estándar con volumen «todos».
- **Total: 28 pruebas primarias (contraste D).**

## Inferencia y veredicto (fijados ahora)
- Bootstrap por sesión del evento (1.000), IC 95 %; p unilateral; **BH q = 0,10 sobre las 28**. También: leave-one-month-out (mín. y máx.), MDE, cobertura del control emparejado, y resultado **con y sin la sesión 2025-12-15** (entrada 049).
- Una celda **sostiene** si el IC inferior de D > 0 y pasa BH.
- **IPC 25t es robusto** si sostienen ≥ 12 de las 23 celdas originales. Si no, **cae** con alcance: la etapa A 25t con este evento y estas definiciones. Las D4 se reportan aparte.
- **Justificación económica / cómo podría refutarse:** las del manifiesto IPC; esta prueba es exactamente su refutación más barata.

## Resultado (28/09, reporte sha `f8e68b1a404b`, árbol limpio): **NO_ROBUSTO — 0 de 23 celdas sostienen**
- ES 36.350 filas, NQ 1.822; cobertura del C-SW emparejado 79 % (ES) y 68 % (NQ); velas ambiguas 0 %.
- **Qué mató el efecto, en orden** (celda más grande, ES estándar, no virgen, k 4, último pico; etapa A original: +0,204 contra C-SZ):
  - **A** (misma comparación, pero excluyendo sólo zonas ya existentes en el momento del control): **+0,062** [+0,03, +0,09]. La corrección de la fuga en los controles (auditoría 046 §1) sola se lleva ~70 % del efecto.
  - B (C-SW actual): +0,044; C (C-SW emparejado, trade): +0,048.
  - **D (primario: midquote contra C-SW emparejado): −0,040** [−0,08, +0,00]; E (mid contra C-SZ): −0,022. Sobre el precio medio el efecto desaparece o se invierte (rebote bid/ask, `LES-R3-TRADE-PRICE-BOUNCE`).
- Patrón general: A > B ≈ C > D en casi todas las celdas; varias D significativamente negativas (ES estándar virgen k 4: −0,12; D4 no virgen k 4: −0,21).
- Única zona con signo positivo sostenido en C y D: **ES k 8, último pico** (D +0,076 [−0,01, +0,16], n 221; volumen bajo +0,149, n 57), no significativa y con n chico. Queda anotada como pista, no como resultado.
- **Veredicto con alcance:** cae IPC 25t **como fue medido en la etapa A** (evento alejamiento, carrera al último/primer pico, detectores estándar/estricto/D4, ES y NQ, descubrimiento Lucid). El positivo era mayormente **controles contaminados por zonas futuras** más **rebote de precio de trade**. No cae el abanico del diseño (`DISENO_IPC_ABANICO_DE_MECANISMOS_20260927.md`): otros eventos, objetivos sin barrera, escalas y el uso como componente siguen sin medir.
