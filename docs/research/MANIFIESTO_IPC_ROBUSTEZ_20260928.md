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
