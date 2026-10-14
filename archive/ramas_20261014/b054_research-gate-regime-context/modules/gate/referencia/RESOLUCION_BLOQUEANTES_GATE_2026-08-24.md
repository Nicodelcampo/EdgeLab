# Resolución adversarial de bloqueantes GATE — 2026-08-24

## Veredicto

**No se promueve GATE a módulo operacional todavía.** Sí se reemplazó la implementación que
fallaba por una ruta formal ejecutable. Estado exacto:

```text
FOUNDATION_EXECUTABLE
CHECKPOINT_PENDING_REAL_DATA
OUTCOMES_NOT_OPENED
```

## Decisiones irreversibles de v0

- Se retira `gate_tf_causal_bal_v2_feat10_sticky90_vpin055`.
- No se intenta «arreglar» silenciosamente el Transformer demo.
- El primer modelo formal es un HMM3 diagonal, determinista y forward-only.
- Los estados son `calm/normal/volatile`; no existe `toxic` en v0.
- `tape_imbalance` es el único nombre permitido para el signed tape disponible.
- OFI requiere eventos y tamaños de libro; VPIN requiere buckets de volumen. Ninguno se infiere
  de una media móvil temporal.
- La barra de minuto se hace disponible al cierre.
- El join requiere instrumento, contrato y sesión CME, con tolerancia de un minuto.
- No existe default de model ID: un checkpoint válido produce su propio ID.

## Evidencia ejecutable

La suite nueva convierte las conclusiones de la auditoría en invariantes:

1. agregar futuro a una secuencia no cambia posteriores ya emitidos;
2. una feature posterior a `t0` no puede etiquetar el evento;
3. otra identidad de contrato no puede cruzarse;
4. contexto de más de un minuto falla cerrado;
5. un nombre de familia sin hash es rechazado;
6. alterar configuración o pesos invalida el checkpoint;
7. la agregación no vuelve a crear columnas `ofi`/`vpin`;
8. las features sólo se publican después de terminada su ventana.

## Bloqueante que no puede resolverse desde el repo remoto

No hay en esta rama un artefacto con las 152/151 sesiones GC target-free. Por eso no se sube un
checkpoint de fixture ni se lo presenta como modelo. El CLI deja preparado el único paso válido:
entrenar donde estén los datos, con cutoff, commit limpio y hashes verificables.

## Criterio de promoción

GATE sólo cambia a `OPERATIONAL_TARGET_FREE` si se versionan o adjuntan de forma auditable:

- checkpoint real validable;
- manifiesto de features y hash del archivo;
- cutoff y universo congelados;
- labels forward-only;
- reporte del join point-in-time;
- tests/CI verdes;
- confirmación de que no se abrió outcomes.

`OPERATIONAL_TARGET_FREE` tampoco autoriza CTX-3. Esa decisión requiere el pre-registro y la
ortogonalidad exigida por la familia BigTrap2Absorption.

## Aporte al referente

La mejora principal no es un modelo más complejo, sino que ahora es imposible confundir una
familia de modelo con un modelo entrenado: identidad, pesos, normalizador, datos y commit forman
un solo artefacto verificable, y la ausencia de cualquiera de ellos impide emitir una etiqueta
formal.
