# Edge Brain: auditoría del patch del agente Notion y dirección hacia el agente autónomo (2026-09-23)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## 1. Auditoría (hecha y registrada)

- **Objeto:** `edge_brain_hardening.patch` sobre el HEAD real del PR #56 (`551f3ee`).
- **Método:** workflow de revisión con 4 lentes completadas (atomicidad, compatibilidad, amenazas, tests) y 20 veredictos de escépticos independientes, todos sobre la lente de amenazas. La lente de rendimiento, el diagnóstico del CI y el análisis del Brain completo quedaron cortados por el límite de la cuenta. No se relanzaron, por pedido de Nico.
- **Veredicto:** el patch **suma**. Valida sobre una copia antes de escribir, arregla la deriva del hash del ledger de research y pone el techo PROPOSED/LOW también en el replay. **Pero no alcanzaba para un escritor autónomo.**
- **Arreglos aplicados** en la rama `fix/edge-brain-store-hardening-20260923` (`28e4f9d` = el patch sin cambios; `7cd3a98` = arreglos), con 78 tests pasando:

| Hallazgo (reproducido) | Arreglo |
|---|---|
| Un segundo escritor bifurca la cadena en silencio y el ledger queda ilegible | Lock exclusivo de SO por ledger, más chequeo del tamaño en disco antes de cada escritura (`changed on disk` → envenena) |
| Ctrl-C o una línea sin `\n` → la siguiente escritura corrompe el ledger | Escritura binaria con fsync. Ante cualquier `BaseException` se trunca al último byte verificado y se envenena. Una cola cortada se rechaza al abrir |
| Invalidaciones fallan abiertas (texto libre; `ELIGIBLE` rehabilita) | Estados cerrados, también exigidos en el replay. `reuse_artifact` exige que la vista esté al día |
| La memoria guarda los objetos del llamador por referencia (una lección podía quedar promovida en memoria) | La memoria se publica desde el payload decodificado de la línea escrita: memoria == replay |
| El retrieval BM25 indexaba el JSONL sin verificar | `LedgerIndex.from_ledger` hace el replay verificado primero |

- **Pendiente de política, no de código:**
  - El append-only **entre commits**: los builders borran y regeneran los ledgers, y el tip anclado se edita en el mismo commit. Hace falta un test "el ledger nuevo tiene al viejo como prefijo" y un tip anclado fuera del ledger.
  - Los 3 tests de `bibliographic_cortex` fallan en Windows por una conexión SQLite abierta. Ya fallaban antes. Hay una rama `fix/brain-close-sqlite-connections-20260921` que apunta a eso.
- **CI del PR #56:** **no** falla por el Brain. Falla `tests/bridge/test_ulp_sweep.py`: 57 comparaciones de precio en `nt8/*.cs` sin clasificar. El dueño es la cadena de los indicadores NT8, no el Brain.
- **Un solo escritor por rama:** hoy escribieron en #56 dos agentes distintos. Estos arreglos van en una rama aparte a propósito. La integración la decide Nico.

## 2. Hacia dónde tiene que ir (objetivo de Nico, no se implementa hoy)

> Un Claude Code corriendo sin parar en el Debian, con API empresarial: hace análisis, usa los indicadores disponibles, crea indicadores nuevos (hay una base de indicadores por subir) y **ata cabos entre los resultados de muchos análisis**.

Lo que el Brain necesita para eso, ordenado por el North Star:

1. **Contabilidad de multiplicidad por familia (robustez).** Cada hipótesis, variante, horizonte y umbral probado es una fila. El N efectivo para DSR/PBO sale del Brain, no de la memoria del agente. Un agente autónomo que prueba mucho sin esto fabrica edges falsos a escala: es el riesgo número uno de la autonomía.
2. **La regla STOP como política ejecutable (validez OOS).** El agente no puede aprobarse a sí mismo (NO_SELF_APPROVAL). Hace falta un registro de campañas **pre-aprobadas por Nico**, con presupuesto de pruebas, horizonte, datos y costo. Dentro de ese presupuesto el agente corre solo; fuera, se detiene y pide. El holdout se accede solo a través de `holdout_guard` y cada acceso queda como fila del ledger.
3. **Invalidación en cascada conectada a los datos reales (integridad).** El caso canónico es el de hoy: el bug ×10 de la fracción de segundo invalidó una semana de parquets L2 **y** una causa raíz publicada (`EXPECTED_BOOTSTRAP_OVERLAP`). Con parquets, manifests, resultados y conclusiones registrados como artefactos con dependencias, una sola `INVALIDATED_BY_MEASUREMENT_ERROR` habría marcado todo lo derivado como `STALE_BY_DEPENDENCY` automáticamente.
4. **Episodios automáticos desde las herramientas (trazabilidad).** Cada `tools/*.py` de medición escribe su episodio (entradas con hash, commit, árbol limpio o sucio, pre-registro, salidas) sin intervención. Hoy solo se escribe a mano.
5. **"Atar cabos" con evidencia, no con narrativa.** El retrieval une resultados por población, instrumento, período, estimand y costo. Una conexión entre dos análisis es una **hipótesis nueva** (propuesta, PROPOSED/LOW) que entra al presupuesto del punto 1, nunca una conclusión.
6. **Registro de indicadores:** definición, parámetros, paridad NT8↔Python, población enumerada y estado (vivo, refutado, cerrado con alcance). Esto responde a "crea indicadores" sin repetir el sesgo de diseño del 2026-08-10 (el toque como única entrada).
7. **Un solo escritor por ledger y una cola de trabajos** en el Debian. El lock ya está; falta la cola. El Celeron alcanza para orquestar y para cálculo liviano, y el razonamiento corre en la API.

**Cómo podría refutarse esta dirección:** si un agente autónomo con estas barreras produce, en un trimestre, menos candidatos que sobreviven al holdout que el trabajo manual con el mismo presupuesto de pruebas, la autonomía no reduce la distancia al edge y hay que repensarla.
