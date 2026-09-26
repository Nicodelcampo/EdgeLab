# INC-003: Ruptura Externa de Entorno y Vencimiento del Baseline (2026-07-16)

Este incidente documenta la pérdida de paridad entre el estado del repositorio y el entorno de ejecución, descubierta el 2026-07-31 durante la auditoría de paridad del logger NT8.

## Cronología del Evento (Deducida)

- **2026-07-16 21:12 a 21:16:** Un usuario ejecutó un `pip install` (presuntamente de `streamlit==1.36.0` u otro de los 56 paquetes instalados en esa franja) sobre el intérprete de sistema `C:\Users\Usuario\AppData\Local\Programs\Python\Python312\python.exe`.
- **El Conflicto:** `streamlit 1.36.0` impuso un techo duro `pandas < 3`. Esto arrastró a `pandas 2.2.2`, que a su vez obligó a bajar a `numpy 1.26.4`. Todo esto en abierta violación del contrato de versiones (pandas >= 3.0.3, numpy >= 2.4.6).
- **2026-07-21 18:20:** Se introdujo `test_environment_contract.py` (commit `49289a1`). Dado que `pyarrow 20.0.0` estaba instalado desde febrero, este test *nunca* pudo haber pasado en este intérprete global.
- **Conclusión sobre el Baseline:** Las salidas de `510 passed` que el proyecto usó como baseline en la última quincena **no pudieron producirse en ningún intérprete presente en la máquina**. El contrato exige `pyarrow >= 25`; el inventario completo (§98) muestra que el máximo disponible antes de hoy era `pyarrow 24.0.0` (TradingPlayground). `test_environment_contract.py` existía desde el 21 de julio (commit `49289a1`) y se recolectaba en toda corrida. La procedencia de esas líneas de suite se investiga en INC-004.
- **Consecuencia de Datos:** Los parquets de data y runs fueron generados por `pandas 3.0.3` (visible en metadata interna dictionary-encoded de `parquet-cpp-arrow`). Al leerlos con `pandas 2.2.2`, `pyarrow` lanza `ArrowTypeError`.

## Mediciones de Pytest (Intérprete Roto - 2026-07-31)

Salidas finales de pytest verbatim. El baseline esperado era `510 passed, 3 deselected`.

**Árbol de producción (`E:\EdgeLab`):**
```text
= 24 failed, 472 passed, 1 skipped, 3 deselected, 13 errors in 270.16s (0:04:30) =
```

**Worktree aislado (`E:\EdgeLab_worktrees\nt8-logger-paridad`):**
```text
= 20 failed, 451 passed, 26 skipped, 3 deselected, 13 errors in 228.47s (0:03:48) =
```

## Consecuencias Estructurales Detectadas

1. **Riesgo de Intérprete Global:** EdgeLab carecía de `.venv` versionado local; operaba en el intérprete global (compartido con utilitarios como opencv, pyannote, streamlit). Toda certificación desde el 16 de julio (ej. §88–§94) es precaria, operada sobre un entorno clandestinamente degradado.
2. **Defecto de Testeo en Worktrees:** Un worktree recién creado reporta **25 skipped extras** sin fallar, por falta de runs u oráculos no versionados. Ningún turno futuro en worktree reproducirá el número "passed" puro. Debe declararse el delta de `skipped` esperado.

---

## §98 — Cierre del Incidente (2026-07-31)

### Restauración del Entorno

- Se creó `E:\EdgeLab\.venv` instalando exclusivamente desde `requirements\core-bridge-dev.lock`.
- El intérprete global (`C:\Users\Usuario\AppData\Local\Programs\Python\Python312\python.exe`) **no fue tocado**: es la única evidencia física del incidente.

### Inventario de Intérpretes de la Máquina

| Intérprete | pandas | pyarrow |
|---|---|---|
| `C:\Freqtrade\...\venv` | 2.3.3 | 22.0.0 |
| `C:\NicoEdgeFinder\...\venv` | 2.2.3 | 18.1.0 |
| `C:\TradingPlayground\.venv` | 3.0.3 | 24.0.0 |
| `E:\EdgeLab\.venv` (canónico) | **3.0.3** | **25.0.0** ✅ |
| `E:\EdgeLab\sidecar\kronos_env` | n/a | no instalado |

### Resultados de Verificación en `.venv`

**Suite completa** (`pytest -m "not vectorbt"`):
```text
510 passed, 3 deselected in 673.95s (0:11:13)
```

**Unidades de paridad** (`test_oracle_parity` + `test_nt8_tick_contract`):
```text
15 passed in 9.65s
```

### Veredicto

- Baseline **510 passed, 3 deselected** reproducido en entorno limpio por primera vez con intérprete verificado. ✅
- La rama de entorno de INC-003 queda **cerrada**: el .venv canónico existe y la suite pasa.
- La procedencia de las líneas de suite anteriores (490 de §88, 510 de ee257bc) se transfiere a **INC-004**.
- §94 permanece **provisional** hasta que se reemitan los cinco valores de paridad desde el .venv.
