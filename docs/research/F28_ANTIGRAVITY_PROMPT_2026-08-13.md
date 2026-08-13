# Prompt para Google Antigravity — F2.8

Copiá todo el bloque. No improvises fuera de él.

---

Sos el implementador local de EdgeLab. No sos un auditor informal y no estás autorizando Z2.

Trabajá **sólo** en:

```text
research/bigtrap2-local-displacement-null
```

HEAD esperado al empezar: incluye `49d0e36` o posterior en esa rama. Si el árbol está sucio, parar.

## Qué ya está hecho. No lo reescribas

- Spec: `specs/bigtrap2_f28_distance_coverage_v0.json`
- Protocolo: `docs/research/BIGTRAP2_F28_DISTANCE_COVERAGE_PROTOCOL_2026-08-13.md`
- Labels: `edgelab/research/f28/residual_atlas.py`
- Interrupción: `edgelab/research/f28/interruption.py`
- Controles: `edgelab/research/f28/controls.py`
- Tests: `tests/research/test_f28_residual_atlas.py`
- F2.7 formal: `diag/tasa_senales/F2.7_formal_93c2e3f3ac44.json`
- F2.7 runner: `diag/tasa_senales/F2.7_nulo_reflexion_local.py`

F2.7 ya adjudicó:

```text
Δ = +0.04815265363200558
IC95 = [0.0306759691, 0.0656293381]
201 sesiones / 15947 zonas
8280 real primero / 7661 espejo primero
d p50 = 2; frac_le_2 = 0.6267; frac_le_5 = 0.9108
overlap espejo-otra-zona = 15890  (NO es ocupación de rango)
```

Eso es un hecho geométrico. F2.8 localiza el mecanismo y mapea residuales. No es un tribunal para matar BigTrap2.

## Datos canónicos. No uses los Parquet de Z1

La formal F2.7 usó estos hashes, no los exports extendidos de ZAMR-1:

```text
6E_12-25_ticks.parquet  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26_ticks.parquet  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26_ticks.parquet  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26_ticks.parquet  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

Si el hash no coincide, **ABSTAIN_PROVENANCE**. No sustituyas por `fd2e358…` ni `654e006…`.

Rutas esperadas: `data/nt8/6E/<archivo>` vía el `data_root()` de F2.7.

## Tarea

Implementá de forma **aditiva** `diag/tasa_senales/F2.8_atlas_residuales.py`.

Reusá, no copies divergente:

- `construir_reflejo`
- `first_passage_race`
- `zone_lifecycle`
- `agregar_por_sesion`
- `hac_bartlett_ic`
- `dias_research` / carga canónica / firewall de F2.7

No toques `bigtrap2.py`, F1.1, holdout, tick:25, P&L, retornos, dirección, Z2 ni Kaggle.

### Orden de corrida

1. Reproducir totales F2.7 (201, 15947, Δ global compatible).
2. Familia A: curva de `Δ(d)` con cortes `d<=2`, `3<=d<=5`, `d>=6`, más `d>3` y `d>5`.
3. Familia C: ocupación activa precio × tiempo. Unión de zonas **vivas** sobre `[low,high]` de cada barra. 200 colocaciones aleatorias/sesión, semilla `20260813`.
4. Familia B: controles de barra creadora.
   - geometría emparejada en barra sin BigTrap2;
   - placebo en la misma barra si existe ubicación disjunta.
   - contrastar `Δ_BT2 − Δ_control` por sesión.
   - si `match_rate < 0.40` en un corte: abstener ese contraste.
5. Familia E: tras primer contacto, 5 barras: `through` / `bounce` / `stay`. Sin P&L.
6. Familia D: etiquetar residuales con `decide_labels`.
7. Escribir artefacto `diag/tasa_senales/F2.8_formal_<sha12>.json` y un markdown de reporte.

### Gates

- 201 sesiones
- cobertura ≥ 0.95
- resolución global ≥ 0.30
- empates técnicos ≤ 0.01
- estrato: ≥30 sesiones y ≥200 pares resueltos, si no `CONTINUE_AMBIGUOUS` para ese corte
- árbol limpio, HEAD estable, `outcomes_accessed=false`

### Etiquetas. Pueden convivir

```text
OPEN_FAR_ZONE_FAMILY
OPEN_BAR_CLASSIFIER
OPEN_HOLE_FAMILY
OPEN_FADE_MIRROR
OPEN_INTERRUPTION_FAMILY
OPEN_DENSITY_FEATURES
CLOSE_ZONE_ATTRACTION
CONTINUE_AMBIGUOUS
```

Cualquier `OPEN_*` produce **una** spec de seguimiento, no un atlas de 17 frames. No autorices Z2.

## Tests que tenés que agregar y pasar

Además de los existentes:

- interrupción: through vs bounce vs stay en paths sintéticos;
- control: intervalo al mismo `d` y ancho, disjunto del ancla;
- ocupación: merge de intervalos y zona aislada;
- labels: los casos ya cubiertos no deben romperse;
- reproducción de los totales F2.7 o fail-closed.

Correr:

```text
./.venv/Scripts/python.exe -m pytest tests/research/test_f28_residual_atlas.py tests/research/test_f28_interruption.py -q
./.venv/Scripts/python.exe diag/tasa_senales/F2.8_atlas_residuales.py --formal
```

Si el venv está en otra ruta gobernada, usala. Si no hay venv, no ejecutes.

## Qué devolver

1. Commits en la misma rama, árbol limpio.
2. Totales F2.7 reproducidos sí/no.
3. Tabla `Δ(d)` con n, sesiones, resolución, IC.
4. Ocupación p50/p90 y isolated_rate.
5. Match rate de controles y contraste.
6. through/bounce/stay vs controles.
7. Lista de labels.
8. Qué familia única abrirías después, si hay `OPEN_*`.
9. Confirmación explícita: no holdout, no P&L, no Z2.

## Prohibido

Inventar cortes primarios después de ver números. Relajar hashes. Subir ticks. Tocar el kernel. Interpretar rentabilidad. Abrir PIT/Kaplan–Meier en esta corrida.
