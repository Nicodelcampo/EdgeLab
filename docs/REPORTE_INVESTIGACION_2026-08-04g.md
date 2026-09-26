# Reporte de investigación (7) — datos locales viejos y gate de integridad

## Reporte nuevo de Claude leído

`docs/REPORTE_LOCAL_2026-08-04e.md` ejecutó el handoff del censo en la máquina
operativa. Resultado material:

- tests del censo: 7 passed;
- el productor canónico `tools/censo_integridad.py` generó el manifiesto;
- los parquets locales son los viejos;
- se detectaron 76 duplicaciones de bloque, todas con desfase +3 h, en cinco
días;
- `6E 09-26` tiene 2.085.208 filas y reproduce exactamente la huella anterior;
- no se ejecutó el censo de señales ni se seleccionaron H1–H3.

La decisión de abortar fue correcta. Un censo sobre esos datos produciría tasas
plausibles pero infladas.

También se acepta la retractación: la medición del 2026-06-19 queda contaminada;
la atribución de `+2 sesiones` a dos feriados se retira. El 2026-07-03 permanece
provisionalmente en pie.

## Contención agregada

`tools/audit_censo_gate.py` convierte el resultado del censo de integridad en un
gate binario reutilizable. Falla cerrado ante:

- cualquier `error` de parquet;
- ausencia del campo de duplicaciones;
- uno o más bloques duplicados;
- payload vacío o mal formado.

Sólo `may_run_signal_census=true` y exit code 0 habilitan el siguiente paso.
Sobre el censo reportado por Claude devolvería:

```
status=BLOCKED_SOURCE_INTEGRITY
total_duplicate_blocks=76
exit_code=1
```

## Desbloqueo operativo

Hace falta una de estas dos acciones en la máquina con datos:

1. restaurar los `.Last.txt` limpios re-exportados el 27-jul, regenerar los
parquets y repetir `censo_integridad.py`; o
2. ejecutar el censo en la máquina que ya conserva esos exports limpios.

Criterio previo a toda tasa: cero duplicaciones en los cinco contratos. La
configuración faltante de front-month para 6E 09-25 se trata después de limpiar
la fuente; no se mezclan ambos problemas.

**Aporte al referente:** se transformó una decisión manual correcta en un gate
ejecutable. Ningún análisis de señales debe continuar sobre una fuente que el
censo canónico declare defectuosa.
