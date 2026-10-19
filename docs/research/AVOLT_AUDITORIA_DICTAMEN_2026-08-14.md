# AVOLT — Dictamen de auditoría (2026-08-14)

**Auditor:** agente auditor (línea independiente)
**Objeto:** commit `2ef38f599cf4abb8382f83ab54ac0e1290c0cb34` (runner, tests, JSON sellado, informe), oráculo `b0c1bd142e1849d03cbb224351807e71245f8620`.
**Material verificado por el auditor:** runner completo, tests (7 funciones), informe, oráculo CSV íntegro (504 eventos), payload JSON del repo con recomputación independiente de sha256, media y HAC desde `session_means` embebido.

---

## Veredicto

**La etiqueta `ABSTAIN_P2` es CORRECTA y es lo único del paquete que se sostiene.**
`decide_labels` es fail-closed y funcionó: con `p2_pass=false` no se emite ninguna
etiqueta de efecto. Eso está bien y hay que decirlo.

Todo lo demás — los "hallazgos" sobre las 798 zonas — queda **en cuarentena**:
son la salida de un pipeline que no demostró paridad con el indicador (P2 FAIL),
construido además sobre barras con defectos estructurales (H5). **No son una
medición de aVolClusterPOI y no autorizan NINGUNA conclusión sobre el indicador,
ni a favor ni en contra.** La frase del chat ejecutor "no tiene ventaja
estadística suficiente, descartarlo nos ahorra tiempo y dinero" es inválida:
un `ABSTAIN_P2` no mide el indicador, y aun midiéndolo, con SE=0.046 el MDE es
~0.13 y el efecto esperado por la corrida v2.1 era ~0.15 — el test no tenía
potencia para distinguir. Ausencia de evidencia no es evidencia de ausencia.

---

## Hallazgos

### H1. El sello sha256 del JSON no cierra sobre su propio contenido

Recomputación independiente del auditor sobre el archivo del repo:
`sha256(json.dumps(payload_sin_campo_sha, sort_keys=True))` =
`60874030dd9d7f06869f93886eb12c81a9ff8367fbd5fb6f8b1c2cc3bb93133c` ≠ declarado
`d5c41684e16280a4a08c54f85194613363c5ba2e80e3cc98691184b8ab86fd3d`.
Además `zones.session_means` contiene **176 valores** contra `n_sessions=188`
declarado en el mismo payload; la media del array embebido es 0.07041 y el SE
recomputado 0.0420, distintos de los declarados (0.06570 / 0.0463). Como el
runner hashea el mismo objeto que escribe a disco, el archivo commiteado **no es
el payload que produjo la corrida**: fue alterado o regenerado después.
Verificación de una línea en la máquina del ejecutor:
`python3 -c "import json; p=json.load(open('diag/tasa_senales/AVOLT_formal_d5c41684e162.json')); print(len(p['zones']['session_means']))"`.
Si imprime 176: regenerar el JSON desde el runner y recommitear. Un sello que no
cierra no protege nada.

### H2. El diagnóstico del informe contradice el meta del propio oráculo

El informe atribuye el P2 FAIL a que "NT8 operaba con contrato continuo de front
month". La línea meta del oráculo declara `instrument=6E 09-26` (contrato
aislado) y los timestamps cubren exactamente la ventana del replay
(2026-04-10T06:22 → 2026-06-30T17:02). Si el meta es cierto, la comparación fue
mismo contrato y misma ventana, y `match_rate=0.0` (133 zonas oráculo vs 51
zonas Python) es **no-paridad real de kernel o de datos**, no un artefacto de
roll. Si el meta miente y era continuo, hay que re-exportar el oráculo
declarándolo. Las dos versiones no pueden convivir.

### H3. El gate P2 comparó un NT8 con lookback caliente contra un Python en frío

El oráculo arranca en `session_index=7`: NT8 tenía historia previa cargada y sus
umbrales (percentil 98 sobre lookback de 20 sesiones, `min_samples=20`) estaban
calientes desde el primer día. El replay Python instancia `SessionProfile` nuevo
al entrar a la ventana: durante las primeras ~20 sesiones sus umbrales se
construyen con historia insuficiente y **no pueden** reproducir las zonas del
oráculo. El gate así construido no mide paridad de kernel: mide diferencia de
condiciones iniciales. Fix: precalentar el perfil del replay con las sesiones
previas a la ventana, o evaluar el match solo sobre la porción post-calentamiento
del oráculo.

### H4. Candidato estructural de kernel: bloques disjuntos vs ventana deslizante

El replay agrega footprints en bloques **disjuntos** de 10 barras
(`for blk in range(len(b_indices)//10)`, descartando el resto de cada sesión).
Si `aVolClusterPOI.cs` v0.5 usa ventana **deslizante** de 10 barras
(`window_bars=10` en el meta), las poblaciones de zonas difieren por
construcción. Es el candidato #1 para explicar 51 vs 133 junto con H3.
Verificar contra el `.cs` antes de cualquier reintento de P2.

### H5. Barras contaminadas por concatenación de contratos

El runner concatena los 4 parquets canónicos y ordena por timestamp. En los
solapes (típicamente mayo–junio, con 06-26 y 09-26 activos a la vez) las barras
M1 mezclan ticks de **dos instrumentos con niveles de precio distintos**:
high/low artificiales, footprints sumados cross-contrato. Además las carreras de
primer pasaje (horizonte 2000 barras) cruzan las fronteras de contrato sin
censura, resolviendo contra precios del contrato siguiente con el salto de roll.
Las 798 zonas y sus carreras están construidas sobre esa serie mixta. Fix:
correr por contrato y cortar/censurar en la frontera.

### H6. `gates.match_rate` está hardcodeado en `True`

En el payload, `gates = {..., "match_rate": True}` literal, mientras
`p2_gate.match_rate = 0.0`. El gate reportado no refleja nada. Cosmetic pero
sintomático: nadie leyó el payload contra el código.

### H7. `by_side` invierte la semántica

`direction > 0` (LONG = zona **debajo** del precio) se reporta como `above`.
El split above/below del informe está al revés.

### H8. El informe declara un HEAD inexistente

`Git HEAD: 413d703b…` en el informe ≠ HEAD real del trabajo (`2ef38f5`).
Otra señal de edición posterior a la corrida (ver H1).

---

## Qué sí queda en pie

- Los 4 hashes de parquets se verifican en el runner **antes** de correr (bien).
- `decide_labels` fail-closed: con P2 FAIL no se emite etiqueta de efecto (bien).
- `tick_first_touch` resolvió el 100% de los empates intrabarra (sobre las barras
  que hubo — ver H5).
- `outcomes_accessed=false`, `pnl_accessed=false`, `holdout_included=false`.
- Los tests 7/7 son reales pero cubren plomería (HAC, etiquetas, tick touch).
  No testean paridad de bloques, cold start, ni concatenación.

## Lo que NO queda autorizado

- "aVol no tiene ventaja / descartarlo": inválido desde un ABSTAIN (ver arriba).
- "PreRange 72% es oro puro / ventaja estructural masiva": ya dictaminado
  `NO_ADJUDICABLE` (tautología geométrica, p=0.103). La línea L3 tiene protocolo
  formal propio (`specs/prerange_sweep_v0.json`, commit `f9dda802`).
- "Automatizar sobre el ranking del barrido Kaggle": prohibido por el cerco P&L;
  921.600 combinaciones ordenadas por profit_factor son un catálogo de máximos
  accidentales, no terreno probado.

## Camino correcto para "mejorar y luego medir"

0. **Cerrar P2 honestamente** (prerrequisito de todo lo demás): mismo contrato
   declarado en el meta, lookback caliente o evaluación post-calentamiento, y
   decidir bloques vs deslizante contra el `.cs` (H2, H3, H4).
1. Solo con `P2 PASS` los números de v0.5 significan algo; hasta entonces no hay
   baseline que mejorar.
2. Los filtros propuestos para v1.0 entran **uno por línea, con spec
   preregistrado y predicción falsable cada uno**. El filtro de rechazo (mecha)
   y el de absorción (delta bid/ask) ya tienen maquinaria auditada en BigTrap2
   (F2.9, cerrada). La confluencia con extremos de rango depende de L3 PreRange,
   que está preregistrada y **bloqueada** hasta recibir: fuente de la ventana,
   CSV de fechas macro 08:30 y zona horaria de los archivos.
