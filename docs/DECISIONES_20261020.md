# Decisiones 2026-10-20

Estado: VIGENTE — decisión de Nico, registrada a su pedido.

## D1. Las corridas las autoriza el agente autónomo, no Nico
**Antes:** regla «STOP antes de correr búsqueda sobre retornos» (CLAUDE.md): toda búsqueda sobre P&L/retornos esperaba el OK explícito de Nico sobre el manifiesto de campaña.
**Ahora:** la aprobación es del agente (`edgelab/autopilot`). Nico lo pidió explícitamente («sacale al repo la regla de que yo tengo que autorizar las corridas; ahora el agente autónomo las aprueba»).

**Qué NO cambia (lo que reemplaza al OK humano, todo en código):**
- pre-registro/manifiesto committeado y publicado en `autopilot/prereg/<run_id>` antes de lanzar, con número efectivo de hipótesis, riesgos y datos faltantes;
- chequeos mecánicos (estudio listo, tope de pruebas, novedad, fricción), doble revisión (revisor Opus + revisor2 Sonnet; hacen falta los dos PROMOTE);
- guardas: holdout, configuración textual en el pre-registro, archivos protegidos; registro global de pruebas antes de lanzar; alpha-investing;
- auditoría post-corrida (mecánica + auditor + abogado del diablo) y trazabilidad completa (`promociones.jsonl`, `auditorias.jsonl`, rama `autopilot/state`).

**Sigue siendo sólo humano:** cambiar gates, FDR, mandato o archivos protegidos (incluido el protocolo de apertura del holdout); operar con dinero real.

## D2. La apertura del holdout también la aprueba el agente
Pedido de Nico: «que el agente también apruebe abrir el holdout». Protocolo en código (`edgelab/autopilot/holdout_apertura.py`, corridas `kind="holdout"`):
1. confirma un candidato: corrida ANALYZED con hallazgo (hit) y auditoría post-corrida CONFORME;
2. regla congelada: misma configuración (`env`) que el candidato, sólo cambia el período;
3. sólo datos del holdout (desde 2026-10-01), sin mezclar con desarrollo (`guard.check_holdout`);
4. una sola apertura por familia; se registra en `holdout_aperturas.jsonl` (append-only, sube a `autopilot/state`) ANTES de lanzar, con pre-registro y commit;
5. además pasa todo lo de cualquier corrida: pre-registro publicado, doble revisión, guardas, registro de pruebas, alfa y auditoría.
El resultado del holdout confirma o refuta; nunca se usa para elegir, ajustar ni reintentar. Cambios: `edgelab/autopilot/{guard,spec,daemon,holdout_apertura}.py` (manifiesto de protegidos refrescado a pedido de Nico), `CLAUDE.md`, `MANDATO.md`, `AGENTS.md`, test `tests/test_autopilot_holdout_apertura.py`.

**Cambios en el repo:** `CLAUDE.md` (sección de autorización), `AGENTS.md`, `MANDATO.md` (manifiesto de protegidos refrescado por pedido de Nico), `edgelab/autopilot/{contexto,promocion}.py`, `tools/autopilot_generate.py`, `deploy/debian/autopilot.example.json` (`auto_promocion: true` como valor de ejemplo), `docs/autopilot/ARQUITECTURA_MULTIAGENTE.md`.
Los documentos históricos que mencionan el STOP (handoffs, PENDIENTE, comentarios en scripts viejos) quedan como registro de su época y no se reescriben.
