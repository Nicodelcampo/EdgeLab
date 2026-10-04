# edgelab.discovery

Protocolo reproducible para buscar reglas intradía sin perder rigor estadístico. No contiene reglas de ninguna estrategia concreta.

## Flujo
1. **Rejilla pre-registrada** (`config/discovery/spec_*.json`): franjas de 15 min × holdings × condiciones (+ pares). `spec_hash` la identifica; el barrido real (`tools/discovery_scan.py`) se niega a correr si el hash no aparece en un pre-registro.
2. **Datos → tensores** (`data.py`, `pipeline.py`): serie continua por volumen de la sesión anterior, elegibilidad por volumen, ejecución de libro, **guarda de retraso** (se descarta toda oportunidad cuyo tick de entrada o de salida se aleje más de 120 s de la hora prevista), retorno de tramo menos la media de la sesión (quita tendencia).
3. **Características causales** (`features.py`): momentum, rango, desviación del VWAP, desequilibrio por agresor, absorción, esfuerzo/resultado y spread; z-score con las sesiones PREVIAS de cada franja.
4. **Nulo de máximo** (`scan.py`): signo de cada sesión sorteado ±1; estadístico = máximo |z| de toda la rejilla. Misma API en CPU (NumPy) y GPU (CuPy, `backend.py`).
5. **Réplica cronológica**: top-K del primer tramo, evaluadas con signo fijo en el último, corrección de Holm. BH sobre p normales para exploración a lo ancho.
6. **Calibración con señal plantada** (`calibrate.py`): falsos positivos del propio protocolo y curva de potencia por tamaño de efecto.
7. **Contador de pruebas**: cada barrido suma su número de celdas a `TrialRegistry`.

## Límites declarados
- Un barrido produce candidatos, no edges. La decisión final exige datos que no se usaron para elegir.
- Con ~225 sesiones por activo solo se detectan efectos grandes: ver la curva de potencia de la calibración.
- GPU: `tools/kaggle_discovery_gpu.py` corre en un kernel privado con paridad CPU/GPU previa; requiere credencial para `api.kaggle.com`.
