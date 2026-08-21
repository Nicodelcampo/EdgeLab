# HFT CTX Handoff Audit — 2026-08-20

> ## ⬛ RESUELTO — R1 sellado el 2026-08-21
>
> Este informe describe el estado en `59a9f28` y **se conserva sin editar** como registro
> fechado. Sus hallazgos C2, C1 y E1/E2 ya fueron atendidos:
>
> | hallazgo | resolución |
> |---|---|
> | **C2** — p Monte Carlo usa `count/B` | corregido a `(1 + count)/(B + 1)` en `6a15255`, migrado a `p_montecarlo()` con test de equivalencia en Commit A |
> | **C1** — 3 sesiones excluidas sin documentar | `excluded_items[]` **computado y serializado**: 20260216 (8), 20260317 (9), 20260319 (4) |
> | **E1/E2** — docs desactualizados | `censo_contextos_es.json` y `HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` actualizados en Commit B |
> | **D1** — N efectivo presentado como medido | marcado `INFERRED_NOT_VERIFIED`; rho nunca se estimó |
>
> **Los números de este informe son los de antes del sellado.** El valor vigente es
> **p mediana 0,1796** (no 0,1775), `run_id 0e16a11b81dcb865`, código `056618f`.
> El 0,1775 queda como `RETRACTED_INVALID_ESTIMATOR_COUNT_OVER_B`.
>
> **Siguen abiertos**: B4 (perfil del 18,3 % sin control), B5 (CI clusterizado) y C3
> (estadístico global para la memoria de nivel). Son R2 y R3, fuera del alcance de R1.

> **Auditor**: Antigravity (Claude Opus 4.6 Thinking), invocado como auditor reproducible.
> **Rama auditada**: `foundation/f0b-compatibility-probe`
> **HEAD remoto verificado**: `59a9f28efae1fdffa7d25847fedd0e9e248610ba` ✓
> **Estado local al iniciar**: rama `research/bigtrap2-local-displacement-null` @ `438ef1b`, sin archivos modificados, 3 untracked (parquet/csv de 6E).
> **H-ES-CTX-1_PREREGISTRO.md**: **no existe** ni localmente ni en el remoto. No fue descartado: nunca fue creado.
> **Holdout 2026-07-01→2026-12-31**: NO fue leído ni abierto. Confirmado por `CUTOFF_MS` en los 3 scripts.
> **Outcomes ejecutados por esta auditoría**: ninguno.

---

## 1. Tabla de afirmaciones → artefacto → veredicto

| # | Afirmación | Artefacto | Veredicto |
|---|-----------|-----------|-----------|
| A1 | H-ES-CTX-1_PREREGISTRO.md no está en GitHub | `git ls-tree -r 59a9f28` | ✅ **CONFIRMADO** — no existe en el tree. Solo existe `edgelab/research/preregistro.py` (infraestructura genérica). |
| B1 | Población total: 9.486 zonas, 62 sesiones | `censo_contextos_es.json` → `universo.n_zonas=9486, n_sesiones=62` vs `h_es_cruce_1.json` → `universo.n_zonas=9234` | ⚠️ **PARCIAL** — El censo cuenta 9.486 zonas brutas. El cruce excluye 251 de altura 0 → 9.234 en `filas`. Los 7.542 pares = 9.234 − 1.692 sin control. Aritmética consistente, pero los dos JSON usan `n_zonas` para cosas distintas. |
| B2 | 7.542 pares emparejados por ancho exacto + ≤30 min | `h_es_cruce_1.json` → `tasas.zona.denominador=7542` | ✅ **CONFIRMADO** — 9.234 − 1.692 = 7.542. |
| B3 | Delta pareada ≈ 0 en 5 métricas, zona gana < 50% | `h_es_cruce_1.json` → `metricas.*` | ✅ **CONFIRMADO** — ticks +1.5, ms 0.0, vol 0.0, ticks/ancho +0.75, vol/ancho 0.0. `frac_zonas_mas_caras` entre 0.4855 y 0.4940. |
| B4 | El 18,3% sin control está analizado por covariables | scripts y JSON | ❌ **FALTA** — No hay análisis del 18,3% por fase, ancho, dirección, absorb/sweep, volatilidad ni solapamiento. Ver §B abajo. |
| B5 | Intervalo de confianza con sesión como cluster | scripts y JSON | ❌ **FALTA** — No hay CI publicado. Solo medianas y percentiles de la distribución de pares. Ver §B abajo. |
| C1 | 62 sesiones → n_sesiones=59 en memoria | `memoria_nivel_nulo_correcto.json` | ⚠️ **DISCREPANCIA** — 3 sesiones excluidas por `len(anchos) < 10` tras quitar altura 0: 20260216 (8→<10), 20260317 (9→<10), 20260319 (4→<10). Motivo válido pero no documentado en el JSON. |
| C2 | p Monte Carlo usa fórmula `(1+count)/(B+1)` | `memoria_nivel_nulo_correcto.py` L136-139 | ❌ **INCORRECTO** — Usa `np.mean(nulo >= obs)` = `count / B`. Produce p=0.0 para 5 sesiones. Con la fórmula correcta `(1+count)/(B+1)`, el mínimo posible con B=400 es 1/401 ≈ 0,00249. |
| C3 | Resultado "31% de sesiones p<0,05" no se interpreta como muerto ni como hallazgo | commit `59a9f28` | ⚠️ **PARCIAL** — El commit dice "pendiente, no efecto". Correcto. Pero falta un estadístico global (Fisher, Stouffer, etc.) y la distribución nula conjunta. Ver §C. |
| C4 | El nulo condiciona adecuadamente | `memoria_nivel_nulo_correcto.py` L124-128 | ⚠️ **INCOMPLETO** — Condiciona por número de zonas y ancho. NO condiciona por fase de sesión, posición temporal/local dentro de la sesión, ancho estratificado por fase, ni estado previo de volatilidad. Ver §C. |
| D1 | N_efectivo ≈ 1.078 es "medido" | `memoria_nivel_nulo_correcto.json` → `efecto_de_diseno` | ❌ **INCORRECTO** — El JSON dice claramente que rho=0,05 es hipotético (`"rho hay que estimarlo por metrica"`), pero el commit dice "N_efectivo = N/8,8" como si fuera un resultado. No se estimó ICC. |
| E1 | `censo_contextos_es.json` contiene el 71,19% retractado | `censo_contextos_es.json` → `memoria_de_nivel` | ❌ **DESACTUALIZADO** — `frac_sesiones_p_max_menor_005=0.7119`, `p_max_mediana=0.005`, `medicion_comprometida=true`. Valores retractados en `59a9f28`, pero el JSON del censo NO fue actualizado. |
| E2 | `HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` actualizado con `59a9f28` | doc en el tree | ❌ **DESACTUALIZADO** — Introducido en `be21d35`, no modificado en `59a9f28`. No refleja la retractación de la memoria de nivel del 71% → 31%, ni los hallazgos del nulo corregido. Viola su propia regla: "se actualiza en el mismo commit que cualquier medición nueva". |
| F1 | Pre-registro local existe | búsqueda recursiva local | ✅ **NO EXISTE** — No hay draft local. No se descartó nada. |

---

## 2. Contradicciones exactas

### Contradicción 1: `censo_contextos_es.json` → 71% retractado pero vigente

```
censo_contextos_es.json (commit be21d35, no modificado en 59a9f28):
  "frac_sesiones_p_max_menor_005": 0.7119
  "p_max_mediana": 0.005
  "medicion_comprometida": true

memoria_nivel_nulo_correcto.json (commit 59a9f28):
  "frac_sesiones_p_menor_005": 0.3051  (i.e., 18/59)
  "p_mediana": 0.1775
```

El censo reporta un resultado que su propio autor retractó un commit después. Cualquiera que lea el censo sin leer la corrección cree que hay señal fuerte.

### Contradicción 2: 62 sesiones → 59 sin documentar

```
censo_contextos_es.json:     n_sesiones = 62
h_es_cruce_1.json:           n_sesiones = 62 (universo), 60 (métricas, por MIN_ZONAS=8)
memoria_nivel_nulo_correcto: n_sesiones = 59 (por len(anchos) < 10)
```

Tres umbrales distintos de exclusión en tres scripts, ninguno documenta cuáles sesiones excluye ni por qué el umbral difiere.

### Contradicción 3: p=0.0 publicado con B=400

5 sesiones reportan `p_max=0.0` en `memoria_nivel_nulo_correcto.json`. Con B=400 remuestreos y la fórmula correcta `(1 + count(nulo >= obs)) / (B + 1)`, el p mínimo posible es 1/401 = 0,00249. Un p=0.0 es un artefacto de `np.mean(>= obs)` cuando ninguna iteración alcanza el observado.

### Contradicción 4: HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md desactualizado

El documento dice literalmente:

> Este archivo se actualiza **en el mismo commit** que cualquier medición nueva sobre esta familia.

Pero `59a9f28` añade `memoria_nivel_nulo_correcto.py/.json` (una medición nueva) sin tocar este archivo. El doc sigue listando "memoria de nivel" solo en "cosas que el censo descriptivo SÍ está midiendo ahora", sin reflejar que el resultado censal fue retractado.

### Contradicción 5: N_efectivo presentado como resultado

Commit `59a9f28` dice: "N_efectivo = N/8,8". El JSON dice: "rho hay que estimarlo por métrica; acá se publica m para que cualquier intervalo futuro lo aplique". Lo primero suena a medición, lo segundo a cálculo ilustrativo con rho hipotético. No se estimó ICC en ningún script.

---

## 3. Archivos que necesitan corrección

| Archivo | Acción requerida |
|---------|-----------------|
| [censo_contextos_es.json](file:///d:/EdgeLab/docs/research/censo_contextos_es.json) | Actualizar `memoria_de_nivel` para reflejar la retractación. Cambiar `frac_sesiones_p_max_menor_005` a null o al valor corregido con nota. |
| [HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md](file:///d:/EdgeLab/docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md) | Añadir sección sobre memoria de nivel corregida (31% ≠ 71%, pendiente), mover a "MEDIDO — inconcluso". |
| [memoria_nivel_nulo_correcto.py](file:///d:/EdgeLab/diag/tasa_senales/memoria_nivel_nulo_correcto.py) | Corregir fórmula de p Monte Carlo: `(1 + count) / (B + 1)` en lugar de `count / B`. |
| [memoria_nivel_nulo_correcto.json](file:///d:/EdgeLab/docs/research/memoria_nivel_nulo_correcto.json) | Regenerar con p corregidos (no habrá más p=0.0; el 31% puede variar ligeramente). Documentar las 3 sesiones excluidas. |
| [velocidad_cruce_es.py](file:///d:/EdgeLab/diag/tasa_senales/velocidad_cruce_es.py) | Añadir CI bootstrap con sesión como cluster. Añadir análisis de las 1.692 zonas sin control. |
| [h_es_cruce_1.json](file:///d:/EdgeLab/docs/research/h_es_cruce_1.json) | Añadir CI y análisis del 18,3% cuando el script se actualice. |

---

## 4. Diffs propuestos

### 4.1. Corregir fórmula p Monte Carlo

```diff
--- a/diag/tasa_senales/memoria_nivel_nulo_correcto.py
+++ b/diag/tasa_senales/memoria_nivel_nulo_correcto.py
@@ -133,9 +133,9 @@
         ses.append(dict(
             trade_date=td, n_zonas=int(len(anchos)),
             max_en_un_nivel=int(obs[0]), niveles=int(obs[1]),
             niveles_3_o_mas=int(obs[2]),
-            nulo_viejo=dict(max=round(float(np.median(viejo[:, 0])), 2),
-                            p_max=round(float(np.mean(viejo[:, 0] >= obs[0])), 4)),
-            nulo_corregido=dict(max=round(float(np.median(nuevo[:, 0])), 2),
-                                p_max=round(float(np.mean(nuevo[:, 0] >= obs[0])), 4),
-                                p_3omas=round(float(np.mean(nuevo[:, 2] >= obs[2])), 4))))
+            nulo_viejo=dict(max=round(float(np.median(viejo[:, 0])), 2),
+                            p_max=round(float((1 + np.sum(viejo[:, 0] >= obs[0])) / (N_NULO + 1)), 4)),
+            nulo_corregido=dict(max=round(float(np.median(nuevo[:, 0])), 2),
+                                p_max=round(float((1 + np.sum(nuevo[:, 0] >= obs[0])) / (N_NULO + 1)), 4),
+                                p_3omas=round(float((1 + np.sum(nuevo[:, 2] >= obs[2])) / (N_NULO + 1)), 4))))
```

### 4.2. Documentar sesiones excluidas en memoria

```diff
--- a/diag/tasa_senales/memoria_nivel_nulo_correcto.py
+++ b/diag/tasa_senales/memoria_nivel_nulo_correcto.py
@@ -114,6 +114,10 @@
         anchos, lows = anchos[ok], lows[ok]
         if len(anchos) < 10:
+            # Sesiones excluidas por tener < 10 zonas con ancho > 0:
+            # 20260216 (8 brutas -> <10 tras h0), 20260317 (9 -> <10),
+            # 20260319 (4 -> <10). Total: 62 -> 59.
             continue
```

### 4.3. Añadir CI clustered y análisis del 18,3% al script de cruce

```diff
--- a/diag/tasa_senales/velocidad_cruce_es.py
+++ b/diag/tasa_senales/velocidad_cruce_es.py
@@ (after contraste function)
+    def ci_cluster_bootstrap(campo, B_boot=2000, alpha=0.05):
+        """CI bootstrap con sesion como cluster.
+
+        Remuestrea SESIONES enteras (no pares), calcula la mediana de la
+        delta pareada en cada remuestreo, y reporta el percentil alpha/2
+        y 1-alpha/2 sobre los B_boot valores.
+        """
+        rng = np.random.default_rng(20260820)
+        ses_keys = [k for k in por_ses if len(
+            [(f["zona"], f["control"]) for f in por_ses[k]
+             if f["zona"] and f["control"]
+             and f["zona"].get("cruza") and f["control"].get("cruza")]
+        ) >= MIN_ZONAS_POR_SESION]
+        boots = []
+        for _ in range(B_boot):
+            idx = rng.choice(ses_keys, len(ses_keys), replace=True)
+            diffs = []
+            for s in idx:
+                par = [(f["zona"][campo], f["control"][campo])
+                       for f in por_ses[s]
+                       if f["zona"] and f["control"]
+                       and f["zona"].get("cruza") and f["control"].get("cruza")]
+                d = [z - e for z, e in par]
+                diffs.append(float(np.median(d)))
+            boots.append(float(np.median(diffs)))
+        boots = np.array(boots)
+        lo = float(np.percentile(boots, 100 * alpha / 2))
+        hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
+        return dict(ci_lower=round(lo, 2), ci_upper=round(hi, 2),
+                    alpha=alpha, B=B_boot, method="cluster_bootstrap_sesiones")
```

```diff
+    def perfil_sin_control():
+        """Describir el 18,3% de zonas que no consiguen control emparejado."""
+        sin = [f for f in filas if f.get("control") is None]
+        con = [f for f in filas if f.get("control") is not None]
+        # Desagregar por fase, ancho, direccion, absorb/sweep, solapamiento
+        # para verificar que no son un subgrupo con efecto distinto.
+        return dict(n_sin=len(sin), n_con=len(con),
+                    ancho_med_sin=float(np.median([f["ancho_ticks"] for f in sin])),
+                    ancho_med_con=float(np.median([f["ancho_ticks"] for f in con])))
```

### 4.4. Actualizar HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md

```diff
--- a/docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md
+++ b/docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md
@@ (despues de la tabla "MEDIDO - y muerto")
+
+## MEDIDO — e inconcluso
+
+| que | resultado | alcance exacto |
+|---|---|---|
+| **Memoria de nivel** | p mediana 0,1775 (nulo corregido), p<0,05 en 31% de sesiones
+  (no 71% del censo con bug de redondeo). Enriquecimiento 6x sobre el 5% esperado,
+  pero sin estadistico global ni test de equivalencia. Pendiente. | ES Flat,
+  59 sesiones, nulo con mismo constructor de mid |

@@ (en "Retractacion vigente")
+### Retractacion adicional (commit 59a9f28)
+El "p<0,05 en el 71% de las sesiones" del censo de contextos (be21d35) fue
+causado por un bug de redondeo asimetrico: np.round(mid) colapsaba medios ticks
+sobre enteros en el observado pero no en el nulo. Con el nulo corregido, la
+fraccion baja a 31%. El 71% se retracta.

@@ (en "NO MEDIDO", seccion 1)
-1. **Retorno y costo de cruce CONDICIONADOS a contexto.**
+1. **Retorno y costo de cruce CONDICIONADOS a contexto.** El costo de cruce
+   agregado es nulo sobre 7.542 pares, pero sin CI ni test de equivalencia.
+   Pendiente: CI cluster-bootstrap y margen de equivalencia declarado.
```

### 4.5. Actualizar censo_contextos_es.json (campo memoria_de_nivel)

```diff
--- a/docs/research/censo_contextos_es.json (extracto campo memoria_de_nivel)
+++ b/docs/research/censo_contextos_es.json
-        "p_max_mediana": 0.005,
-        "frac_sesiones_p_max_menor_005": 0.7119
+        "p_max_mediana_RETRACTADO": 0.005,
+        "frac_sesiones_p_max_menor_005_RETRACTADO": 0.7119,
+        "retractacion": "commit 59a9f28: nulo del censo usaba np.round(mid) que
+           colapsaba medios ticks. Con nulo corregido: p mediana 0,1775, p<0,05
+           en 31%. Ver memoria_nivel_nulo_correcto.json.",
+        "ver": "docs/research/memoria_nivel_nulo_correcto.json"
```

---

## 5. Contenido del pre-registro local

**No existe.** Ni `H-ES-CTX-1_PREREGISTRO.md` ni ningún archivo con nombre similar fue encontrado localmente ni en el tree remoto de `59a9f28`. No se descartó ningún draft: nunca fue creado.

---

## 6. Detalle de auditoría por sección

### A. Estado remoto ✅

- `H-ES-CTX-1_PREREGISTRO.md` **no existe** en `git ls-tree -r 59a9f28`.
- La rama local es `research/bigtrap2-local-displacement-null`, totalmente separada.
- No hay archivos locales no commiteados que pertenezcan a esta rama.
- Separación local/remoto: limpia.

### B. Cruce ⚠️

**Población**: 9.486 brutas → 9.234 tras excluir 251 de altura 0 → 7.542 con control emparejado (81,7%). Aritmética verificada.

**18,3% sin control (1.692 zonas)**:
- ❌ No se analiza si difieren por fase, ancho, dirección, absorb/sweep, volatilidad previa ni solapamiento.
- ❌ El commit dice "la zona gana MENOS del 50% en las cinco métricas" pero esto aplica solo a los 7.542 pares, no a la población completa.
- **Requerido**: perfil de las 1.692 zonas sin control vs las 7.542 con control, desagregado por las covariables del censo.

**CI y test formal**:
- ❌ No hay intervalo de confianza publicado.
- ❌ No hay test de equivalencia (TOST) con margen predeclarado.
- El resultado es "mediana de la delta por sesión = 0" con dispersión enorme (p25 −704 / p75 +881 ticks). Sin CI, no se puede distinguir entre nulo real y potencia insuficiente.
- **Requerido**: CI cluster-bootstrap con sesión como unidad de remuestreo.

**"Mecanismo muerto"**:
- El commit dice "mata un tercer mecanismo candidato" y "cierra el tercer mecanismo".
- ⚠️ Con dispersión p05 −17.315 / p95 +21.189 ticks, la mediana cero puede esconder dos efectos opuestos (P-55). No se puede llamar "muerto" sin un margen de equivalencia predeclarado cuyo CI completo quede dentro.
- **Recomendación**: el resultado es "nulo agregado sobre 7.542 pares, pendiente equivalencia/CI". No "muerto".

### C. Memoria de nivel ⚠️

**Discrepancia 62 → 59 sesiones**:
- Sesiones excluidas: 20260216 (8 zonas brutas → <10 tras h0), 20260317 (9 → <10), 20260319 (4 → <10).
- Motivo: `len(anchos) < 10` en `memoria_nivel_nulo_correcto.py` L116.
- ⚠️ No documentado en el JSON. Las 3 sesiones tampoco tienen `memoria_nivel` en el censo original (el censo usa el mismo corte implícitamente). Consistente pero opaco.

**Fórmula p Monte Carlo**:
- Script usa: `np.mean(nulo[:, 0] >= obs[0])` → p = count(nulo ≥ obs) / B
- Correcto: `(1 + count(nulo >= obs)) / (B + 1)` (North et al. 2002, Davison & Hinkley 1997)
- Impacto: 5 sesiones con p=0.0 → pasarían a p ≈ 0,0025. La fracción p<0,05 podría cambiar marginalmente.
- **El p=0.0 no debe interpretarse como certeza**; es un artefacto de la fórmula.

**Resultado global**:
- p mediana 0,1775 con 31% de sesiones p<0,05 (18/59) vs 5% esperado bajo nulo global.
- ⚠️ El 31% es un enriquecimiento 6.1× sobre el 5% esperado. Pero no hay:
  - Test global (Fisher, Stouffer, Bonferroni conjunto) sobre las 59 sesiones
  - Distribución nula conjunta de "fracción de sesiones p<0,05" bajo nulo verdadero
  - Distinción entre **concentración geométrica** (las zonas se apilan en ciertos niveles) y **memoria económica** (esos niveles importan para el outcome)
- **Requerido**: un estadístico global y su distribución nula permutacional.

**Especificación del nulo**:
- El nulo corregido condiciona por: número de zonas en la sesión, ancho de cada zona, precios operados reales (no uniformes).
- ⚠️ NO condiciona por: fase de sesión (Asia ≠ RTH), posición temporal/local dentro de la sesión, ancho estratificado por fase, ni estado previo de volatilidad.
- Si las zonas de RTH-pm (3 ticks, Absorb) tienen diferente distribución de niveles que las de Asia (6 ticks, Sweep), el nulo debería condicionar por fase.

### D. N efectivo ⚠️

- El script **no estima ICC/rho**. No hay cálculo de varianza entre-sesiones vs dentro-sesiones.
- El commit presenta "N_efectivo = N/8,8" como resultado. El JSON aclara que es ilustrativo con rho=0,05.
- Fano 7,78 y 81% de solapamiento demuestran **dependencia probable**, pero no calculan el DEFF del outcome (costo de cruce, retorno, etc.).
- **Requerido**: no publicar 1.078 como N_efectivo medido. Usar inferencia clustered por sesión (que no necesita estimar rho explícitamente). Explicar que Fano y solapamiento son evidencia de dependencia, no medidas del DEFF.

### E. Reconciliación documental ❌

**Estado correcto de cada frente al cierre de `59a9f28`:**

| Frente | Estado correcto |
|--------|----------------|
| Costo de cruce ES Flat | Nulo agregado sobre 7.542 pares. Pendiente: CI cluster, test de equivalencia, perfil del 18,3% sin control. |
| Retorno a zona ES Flat | **RETRACTADO**. Control espejo degenerado. Sin re-medición válida con control casi-zona. |
| Volumen (tasa) ES V2 | Nulo sobre población V2 sesgada. rho≈0 se sostiene sin espejo. No transportar a Flat. |
| Soporte/resistencia | Alcance 6E, no ES Flat. |
| Memoria de nivel | 71% **RETRACTADO**. Resultado corregido: 31% sesiones p<0,05, p mediana 0,1775. **Inconcluso**, no efecto ni nulo. |

**Lo que los documentos dicen vs lo que deberían decir:**

| Documento | Dice | Debería decir |
|-----------|------|---------------|
| `censo_contextos_es.json` | `frac_sesiones_p_max_menor_005: 0.7119` | Valor retractado, con referencia a `memoria_nivel_nulo_correcto.json` |
| `HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` | "memoria de nivel" en "cosas que el censo SÍ está midiendo" | Sección propia: "MEDIDO — inconcluso", con resultado corregido |
| `h_es_cruce_1.json` | Sin CI | Necesita CI y perfil del grupo excluido |

### F. Pre-registro y MDE

- **No existe** pre-registro local ni remoto. No hay draft que tratar como DRAFT.
- No hay MDE declarado (+6,7 ticks ni ningún otro valor).
- No hay outcome, estimador, alpha, potencia, multiplicidad, varianza entre sesiones, población emparejable ni margen de equivalencia documentados.
- **Requerido antes de pre-registrar**: script que calcule MDE a partir de la varianza observada de la delta pareada, con la potencia y alpha deseados, clustered por sesión. El MDE debe ser reproducible (script + JSON).

---

## 7. Recomendación GO / NO-GO para congelar pre-registro

> [!CAUTION]
> ### 🔴 NO-GO

**No se puede congelar un pre-registro que no existe.** Pero más importante: la base sobre la cual se construiría tiene defectos que hay que corregir primero:

1. **Fórmula de p incorrecta** en `memoria_nivel_nulo_correcto.py` → produce p=0.0 imposibles.
2. **Documentación desincronizada** → `censo_contextos_es.json` y `HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` publican un resultado retractado.
3. **Sin CI** en el cruce → no se puede declarar "nulo" sin saber el ancho del intervalo.
4. **18,3% sin control no analizado** → posible sesgo de selección en el emparejamiento.
5. **No hay estadístico global** para la memoria de nivel → el 31% vs 5% es sugestivo pero no formalizado.
6. **N_efectivo no estimado** → cualquier cálculo de MDE que use N=9.234 o N=7.542 como si fueran independientes estará inflado.

### Secuencia propuesta antes del pre-registro

1. Corregir fórmula p MC → regenerar JSON → verificar impacto en fracción p<0,05.
2. Documentar sesiones excluidas en los 3 scripts.
3. Actualizar `censo_contextos_es.json` y `HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md`.
4. Añadir CI cluster-bootstrap al cruce y publicar en el JSON.
5. Perfilar el 18,3% sin control.
6. Producir estadístico global para memoria de nivel con distribución nula permutacional.
7. **Recién entonces** redactar el pre-registro con MDE derivado de varianza observada, clustered.

---

> **Este informe NO fue commiteado.** Esperando aprobación explícita antes de cualquier corrección o medición.
