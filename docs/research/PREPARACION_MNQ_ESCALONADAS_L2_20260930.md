# MNQ escalonadas × L2 — preparación ejecutable desde nube

**Estado: PREPARADO / NO MEDIDO EN MNQ REAL.** R02/I-3; no rescate de climas.
Pedido de Nico: hacerse cargo desde nube y reducir Claude local a una ejecución.

## Entregables

- `tools/streaming_escalonadas.py`: geometría incremental de PLANAS MNQ150t,
  precio confirmado. Sólo picos conocidos, sin geometría final de una serie futura.
- `tools/mnq_l2_prepare.py`: hashes/schema/clock, reader de L1/L2 propio,
  velas150-LAST, reconstrucción canónica, eventos a cierre y features disponibles
  al terminar el timestamp. Exporta derivados privados compactos, no retornos.
- `tools/mirror_landmark.py`: helper de landmark de segundo impulso con A/B
  ya disponibles y congelados. No encuentra A/B, no predice precio, no backtest.
- Plan target-free, borrador de manifiesto financiero y handoff de un comando.
  **No existe todavía un runner financiero aprobado ni se afirma un efecto MNQ.**

## Qué se probó realmente

**19/19 tests**: geometría contra funciones exactas del detector existente en cada
prefijo de cuatro series sintéticas de140 velas y una serie construida de10;
eventos no reescritos por futuro, gaps, escala, orden; landmarks en ambos sentidos,
B todavía desconocido, intento invalidado, A/B no reescribibles; cierre de grupo
de timestamp, barra incompleta, libro inválido/null, cantidad cero; schema sin
`price` redundante, hash alterado rechazado y solapamiento conjunto entre archivos.

Oracle cargado mediante AST de las funciones Python puras existentes, no mediante
JIT/numba ni el CLI de producción completo. Esto no certifica paridad de todas
las sesiones reales MNQ. El CLI fue actualizado por otra sesión mientras se
preparaba el código (tick desde metadata); cambio revisado y tests reejecutados:
en MNQ tick0,25 sigue siendo el contrato.

Smoke de ejecución sobre GC real disponible, sólo9.000 grupos: 1.194 LAST,
7 velas completas150t, 144 prints restantes y0 señales con esta geometría.
Conteo de JSONL verificado independientemente. **No son datos MNQ ni una medición
de frecuencia, utilidad o potencia del detector MNQ**. No se interpretó reloj
absoluto de GC ni se calcularon destinos de precio.

Evidencia agregada y hashes:
`artifacts/mnq_l2_preparation_20260930/evidence.json`.
Entorno: NumPy2.5.3, pandas3.0.6, PyArrow25.0.0; no se afirma CI/lock completo.
Code ejecutado fuera de worktree, byte-hashed; no se presenta como corrida de commit clean.

## Corrección antes de probar

El CLI original escala también `CONF_TICKS`: en MNQ150t, 2×12,42 redondea a
**25 ticks**, igual que escalón máximo; retroceso5×12,42 redondea a62.
La transcripción inicial X2 se corrigió antes de ejecutar pruebas/datos, según
código fuente. No se ajustó ningún umbral a resultados.

## Por qué hace falta sólo una acción local

Fuentes privadas Kaggle consultadas por MNQ y L2: aparecen ticks MNQ y GC L2/NQ
contextos, **no el raw L2 MNQ**. El catálogo y acta del repo sitúan sus52 sesiones
en la PC. No se inventó acceso remoto, no se sustituyó L2 por labels y no se
inició otra sesión Claude.

Ejecutar `HANDOFF_MNQ_L2_UN_COMANDO_LOCAL_20260930.md` para una sesión. El ZIP de
salida permite seguir QA/support desde nube. Después de PASS de esa muestra,
el mismo exporter recorre todas las sesiones en un solo proceso.
No se tocaron visor, raw ni climas. El nuevo loader publica recortes de overlap
y reinicia libro al cambiar archivo; no se certifica sin MNQ real que equivalga
al loader de los climas ni que la cobertura de sus features sea100 %.

## Qué queda bloqueado

Utilidad en señales, costos, P&L, MFE/MAE, potencia financiera y transferencia
fuera de muestra. Filtro de2 recoveries en10s propuesto antes de MNQ, no validado.
Primero contar soporte target-free; si escasea, STOP/inconcluso, no bajar el umbral.
Comisión y otras reglas de `BORRADOR_MNQ_ESCALONADAS_L2_20260930.md` deben
ratificarse y congelarse con Nico. Holdout forward oct+ intacto.

## Aporte al referente

El diseño y el código quedan en nube; Claude local no debe investigar ni reescribir
el pipeline. Falta trasladar una muestra propia para validar ejecución MNQ real,
no prometer resultados de un libro al que esta sesión aún no accedió.