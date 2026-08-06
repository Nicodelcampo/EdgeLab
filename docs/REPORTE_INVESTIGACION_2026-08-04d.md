# Reporte de investigación (4) — 2026-08-04 · censo completo y handoff local

> Autoría: sesión de investigación. Este reporte coordina el trabajo remoto con
> la máquina operativa sin atribuirse ejecuciones locales que no realizó.

## 1 · Cambio implementado

Commit previo en esta rama:

```
17ab97a41db0c5a9f888cc66f3c619062b89c625
feat(research): run full outcome-free signal-rate census
```

El piloto de 20 días de `diag/tasa_senales/post_sepmin.py` fue reemplazado por
un censo de **todas** las sesiones elegibles entregadas por
`cargar_dias_de_estudio`. El cambio:

- elimina la selección fija de 10 días centrales para dos contratos;
- deriva la raíz del repo desde el archivo en vez de hardcodear `E:/EdgeLab`;
- falla cerrado si una sesión aparece duplicada o en dos contratos;
- conserva conteos crudos y post-`sep_min` por día;
- emite `post_sepmin.run_manifest.json` con commit, SHA-256 del universo y del
  output, cobertura, contratos, indicadores, configuración y declaración
  `outcomes_accessed=false`;
- agrega regresiones del plan completo y del manifiesto.

Verificación realizada en sandbox:

```
py_compile: PASS
SIGNAL_RATE_FULL_CENSUS_HARNESS_PASS
```

No se presenta ese harness como sustituto de pytest canónico ni como ejecución
del censo sobre los parquets reales.

## 2 · Evidencia local leída y reconciliada

Se leyeron los tres reportes de Claude en `fix/capture-probe-v2-contract`:

- `REPORTE_LOCAL_2026-08-04.md`;
- `REPORTE_LOCAL_2026-08-04b.md`;
- `REPORTE_LOCAL_2026-08-04c.md`.

Estado incorporado:

1. suite canónica hasta `f4367a2` y rama correctiva: **586 passed, 0 failed,
   37 skipped**;
2. CaptureEventProbeV2 v2.1 fue corregido a CRLF, instalado y compilado en la
   ruta real de OneDrive;
3. captura P2: transporte íntegro y schema limpio (`schema_ok=true`, 0
   centinelas, 2.505 filas, exit code 0);
4. defecto confirmado: `PASS` es inalcanzable porque cualquier warning degrada
   a `TRANSPORT_PASS_WITH_SCHEMA_DEBT`, incluso un límite estructural declarado;
5. `source_time` retrocedió 29 veces (máximo 50 ms); el orden autoritativo es
   `callback_seq/capture_seq`;
6. la propuesta de mover el holdout al manifiesto fue retractada: la autoridad
   sigue siendo la puerta única;
7. se midieron dos cierres anticipados, pero el 2026-06-26 es un outlier de
   horario sin explicar; un calendario CME versionado debe partir de la fuente
   publicada y usar los ticks sólo como verificación;
8. un PASS de EXPLORE con `p_global` es G1 y no autoriza G2; `theta_trade` sigue
   siendo la primaria económica;
9. DSR bajo dependencia continúa sin resolución autoritativa.

Ninguno de estos resultados abre allowlists, selecciona H1–H3 ni modifica
veredictos históricos.

## 3 · Handoff explícito para Claude

Cuando la máquina operativa lea este reporte:

1. hacer `fetch` de `work/research-architecture-hardening` y trabajar sobre
   `17ab97a...` o un descendiente limpio;
2. ejecutar:

```bash
python -m pytest tests/research/test_signal_rate_census.py --basetemp=C:/t -q
```

3. comprobar si existe `runs/censo/manifiesto_universo.json` en la máquina;
4. si existe, ejecutar `python diag/tasa_senales/post_sepmin.py` sin abrir
   holdout ni modificar la puerta única;
5. correr `audit_post_sepmin.py` sobre el output y registrar SHA-256, sesiones,
   contratos, errores por indicador y duración;
6. si el manifiesto no existe, **no reconstruirlo ad hoc**: reportar el bloqueo
   y el productor canónico requerido;
7. no llenar H1–H3 aunque el auditor dé COMPLETE; primero reportar el censo para
   revisión de cobertura y saturación.

Además, no corregir todavía la taxonomía del auditor de captura: el hallazgo está
confirmado, pero cambiar sus estados exige una decisión semántica y actualización
de la documentación que los consume.

## 4 · Estado

El código para el censo completo está publicado. Falta la ejecución canónica y,
si el manifiesto existe, la corrida sobre datos reales. Ése es el siguiente
trabajo de la máquina operativa; la sesión de investigación queda a cargo de
revisar y registrar sus resultados.
