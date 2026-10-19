# Prompt para la sesión local: indicador de impulsos espejados

Copiar desde la línea siguiente.

---

Vas a diseñar y construir un indicador que marque **impulsos espejados**: un impulso A→B seguido de una vuelta B→A
con velocidad y forma de ondas parecidas, que recorre el impulso completo.

**Antes de escribir código:**

1. Corré `.venv\Scripts\python tools\estado.py` y hacé el chequeo de raíz, HEAD, worktree y árbol limpio que pide
   `CLAUDE.md`.
2. Traé la rama `claude/focused-fermat-qjt805` (`git fetch origin claude/focused-fermat-qjt805`). Ahí está el
   contexto, todavía sin mergear. Trabajá según la regla de ramas de `CLAUDE.md`.
3. Leé, en este orden:
   - `docs/research/IDEA_INDICADOR_ESPEJO_NICO_20260926.md`: mi tesis, lo ya medido, el código reutilizable y las
     reglas que aplican;
   - `docs/research/HANDOFF_2026-09-26_HFT_REV_Y_ESPEJO.md`;
   - `docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_MNQ_20260926.md` y `docs/research/MANIFIESTO_ESPEJO_MACRO_ES_20260926.md`;
   - `docs/kernel_contract.md` y `docs/nt8_indicator_parity_contract.md`.

**Mi tesis:** el impulso es una exploración **ineficiente** y forzada del precio. Cuando quien empuja afloja, el precio,
por inercia, hace el mismo recorrido a la inversa. Quiero verlo marcado en el visor para estudiarlo.

**Lo que te pido:**

1. **Registrá la excepción a F9.** F9 (nuevos indicadores) está pausada, y la autorizo para este indicador. Dejá
   escrito el registro de la familia (indicador, subfamilias, parámetros, ledger propio) antes de codear.
2. **Proponeme una definición operativa** antes de implementar:
   - «impulso ineficiente»: eficiencia del camino, volumen por tick, o las dos;
   - «afloja»: el punto de agotamiento;
   - «espejo parecido»: velocidad, eficiencia, forma y ondas, reusando `tools/espejo_semejanza.py::eventos`.

   Con alternativas escritas y cómo podría refutarse cada una. Esperá mi OK.
3. **Implementalo en Python, target-free y causal:**
   - sin repintado, con estados separados **candidato** → **espejo completado** / **fracasado**;
   - todos quedan en el censo, también los fracasados;
   - reusá `tools/tbzx_espejo.py::detect` o `tools/espejo_macro.py::detect_var` para el impulso;
   - tests con fixtures chicos y deterministas.
4. **Llevalo al visor** (`viewer/nt8_bridge/index.html`): los tres estados con colores distintos, y el impulso y su
   espejo unidos visualmente. Tiene que funcionar en velas de 25 ticks y en velas de tiempo (5/15 min).
5. **Nada de medir P&L ni ajustar parámetros mirando si después hubo espejo.** Eso es una campaña aparte, con
   pre-registro y mi OK.
6. **Si lo llevás a NinjaTrader,** seguí el protocolo de paridad.

Commits chicos, verificados con `git show --stat`. Pusheá al terminar y, al final de cada checkpoint, escribí «Aporte
al referente».
