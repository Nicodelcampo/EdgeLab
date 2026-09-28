# Idea de Nico: indicador de impulsos espejados («zonas espejo») — contexto para una sesión local (2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** idea y especificación de diseño. **No es un resultado.** El indicador todavía no existe.

## 1. La tesis de Nico (en sus palabras, ordenadas)

> Las zonas espejo son una especie de «manipulación»: el precio explora un rango de manera **ineficiente**. Al llegar a
> cierto punto, quien empujaba el precio de manera «forzada» afloja, y **por inercia el precio hace el mismo recorrido
> a la inversa**.

Lo que se ve en el chart (capturas de MNQ en la conversación): un impulso fuerte A→B, y después una vuelta B→A con
**velocidad y forma de ondas** parecidas, que termina recorriendo el impulso completo, a veces un poco más. «Parecida»
es **velocidad y forma de las ondas** (respuesta explícita de Nico).

## 2. Traducción operativa (para discutir, no congelada)

- **Impulso:** tramo A→B de recorrido grande con eficiencia baja o media: «explora de manera ineficiente». Es la
  diferencia con TBZX, que exige eficiencia ≥ 0,6. A validar con Nico: su «ineficiente» puede ser la eficiencia del
  camino, el volumen por tick (poco volumen para mucho recorrido: empuje sin participación) o las dos cosas.
- **Agotamiento («afloja»):** un punto B donde el empuje se detiene. Candidatos: caída de la velocidad, caída del
  volumen agresivo en la dirección del impulso, primer retroceso mayor que el ruido.
- **Espejo:** la vuelta B→A con velocidad, eficiencia y ondas comparables a las del impulso invertido en el tiempo. La
  vuelta recorre primero lo último que recorrió el impulso.
- **Espejo completo:** la vuelta llega a A. Sobrepaso = cuánto pasa de A, en fracción de W.

## 3. Lo que ya se midió (no repetir, usar)

| Estudio | Qué encontró | Dónde |
|---|---|---|
| TBZX-ESPEJO (ES y NQ, 25 t) | ES: llega a A +5 pp sobre el control de igual volatilidad. NQ: contra N-REV (misma vuelta sin franja) desaparece; importa cómo empieza la vuelta | `docs/research/MANIFIESTO_TBZX_ESPEJO_20260925.md` |
| ESPEJO-SIM (MNQ 09-25, 25 t) | Con impulsos de 17 t, las vueltas parecidas completan el espejo +1,5 a +4,9 pp más que las poco parecidas (FDR de grilla). **Sin replicar.** A esa escala no paga la fricción (hace falta un exceso ≈ costo/W ≈ 14 pp) | `docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_MNQ_20260926.md`, `artifacts/research/espejo_sim/` |
| ESPEJO-MACRO (SPY 2008–2021 → ES, 5/15 min) | Corriendo al escribir esto | `docs/research/MANIFIESTO_ESPEJO_MACRO_ES_20260926.md` |

**Lección de medición:** medir la fracción recorrida con el extremo de la vela sesga el nulo (−10 a −14 pp). Lo
correcto es la posición **al cierre** de la vela en que el evento se conoce.
**Nulo exacto:** sin memoria, estando en la fracción f de la vuelta, P(llegar a A antes que a B) = f.

## 4. Código reutilizable

- `tools/tbzx_espejo.py::detect`: detector de impulsos TBZX, paridad con el visor verificada (707/707 y 11.594/11.594
  franjas en enero de ES).
- `tools/espejo_macro.py::detect_var`: la misma lógica con umbral por vela (k·ATR); probado equivalente con umbral
  constante.
- `tools/espejo_semejanza.py::eventos`: semejanza de la vuelta contra el tramo espejo (`vel`, `efi`, `forma`, `ondas`)
  y desenlace; rangos percentiles con empates al medio.
- Visor: `viewer/nt8_bridge/index.html` (diseñador `EDGELAB_TBZX_DESIGNER`), configuración de Nico en
  `docs/specs/TBZX_CONFIG_BORRADOR_20260925.json`.

## 5. Reglas del proyecto que este indicador tiene que respetar

1. **F9 (nuevos indicadores) está PAUSADA por decisión sellada de Nico** hasta correr una campaña formal sobre los 5
   indicadores existentes (`CLAUDE.md`). Este indicador es una excepción que Nico tiene que declarar por escrito.
   Registrarla en el documento de la familia antes de escribir código.
2. **Construcción target-free** (`docs/kernel_contract.md`): el indicador dibuja geometría con información pasada. No
   se ajusta mirando si después hubo espejo.
3. **Sin repintado y con censo as-of:**
   - dos estados separados: **candidato** (la vuelta empezó y se parece) y **espejo completado** (llegó a A);
   - el visor debe mostrar también los candidatos que **fracasaron**;
   - si sólo se dibujan los espejos completados, lo que se ve es sesgo de supervivencia de la regla de dibujo, no
     mercado (regla permanente de `CLAUDE.md`).
4. **Registro de familia antes de estudiar:** indicador, parámetros congelados y ledger propio. No transporta
   resultados de TBZX ni de ESPEJO-SIM.
5. **Paridad NT8 ↔ Python** si se lleva a NinjaTrader (`docs/nt8_indicator_parity_contract.md`).
6. Holdout 2026-07-01+ intocable; abr–jun 2026 reservado para confirmación.

---
**Alcance (2026-09-26, pedido de Nico):** este estudio es un **tamiz** («¿seguir con la idea del espejo?»), no un
veredicto sobre el espejo. Qué midió exactamente, qué no y la regla para cerrar la familia:
`docs/research/ESPEJO_MEDIDO_Y_NO_MEDIDO.md`. Un NO de acá invalida sólo su población, su detector (impulsos
**eficientes**, eficiencia ≥ 0,6), su semejanza y su horizonte.
