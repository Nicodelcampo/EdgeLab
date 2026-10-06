# Decisión 2026-10-05 — se levanta ABSTAIN_LICENSE para compartir research-v2 con Gonzalo Escobar

**Decide:** Nico (dueño del proyecto), en sesión del 2026-10-05, explícitamente: "decido que se levante".

**Qué se levanta:** el bloqueo interno que impedía compartir `research-v2` (y los datasets de ticks CME/NT8 privados)
por `ABSTAIN_LICENSE`. Alcance: compartir con **gonzaloescobar** (compañero de trabajo, aprobado por Nico para todo).

**Qué NO cambia:**
- Los datasets siguen **privados**: compartir con un usuario no es publicar. Nada se hace público.
- Los otros gates de publicación de `research-v2` (capacidad: tres compuertas en rojo) siguen como estaban.
- El holdout (desde la sesión del 2026-10-01) sigue sellado para cualquier agente.

**Riesgo asumido y registrado:** el bloqueo venía de la licencia del proveedor de datos, no de una regla interna; si el
contrato no permite compartir con terceros, el riesgo legal lo asume Nico por esta decisión. Se informó antes de decidir.

**Verificación al 2026-10-05:** `mnq-parquet` no aparece en la búsqueda pública de Kaggle y su URL devuelve 404 sin
sesión (privado); `mnq-tick-data` no existe en la cuenta. La nota de "públicos temporalmente" queda resuelta.

**Ejecución (manual, la hace Nico):** Kaggle → cada dataset → Settings → Sharing → `gonzaloescobar` (lector).
Token de API que circuló por chats: revocar y regenerar (independiente de esta decisión).
