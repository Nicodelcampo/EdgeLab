# H-ES-CTX-3 — Pre-registro: contexto GATE (micro-régimen) sobre eventos ES

- **Estado:** `DRAFT_READY_TO_FREEZE` (no ejecutado; no se miraron outcomes de la familia)
- **Fecha de plantilla:** 2026-08-23
- **Reemplaza / complementa:** H-ES-CTX-2 (régimen = `pct_rv` terciles). CTX-3 evalúa un **contexto distinto**: labels GATE en \(t_0\).
- **Tipo de estudio:** Observacional / condicionado (OSF: observational). No es un edge; no autoriza P&L.
- **Cadena:** geometría del evento → **información de contexto** → (futuro) P&L. Este estudio solo el eslabón de contexto.

---

## 0. Criterio de elección del contexto (escrito antes de outcomes)

Un contexto GATE se acepta para el trial solo si cumple **todas**:

1. Labels producidos con schema `gate_context_schema_v1` y join **as-of** (`feature_ts ≤ t0`).
2. Pasada **target-free** (Paso 2) con:
   - `corr` régimen–`ancho_ticks` en veredicto `OK_LOW_CORR` (|Pearson| < 0,20); si `WARN` o `REJECT_LIKE_CTX2`, **no se congela** este trial.
   - Cobertura: objetivo ≥ 40 sesiones por celda de análisis (mismo piso que CTX-2).
3. `model_id` congelado y declarado (Paso 5).
4. Disponible en ≥ 99 % de eventos de la población con `as_of_ok=true`.

Si el Paso 2 falla el filtro de ancho, este pre-registro queda `SUPERSEDED` sin correr outcomes.

---

## 1. Población

| Campo | Valor |
|-------|--------|
| Instrumento | ES (CME) |
| Fuente de eventos | Export oráculo / BigTrap2Absorption / HFTZones según snapshot del lab |
| Ventana discovery | La misma pre-firewall que CTX-2 (p. ej. ES 03-26, 62 sesiones) — **sin holdout** |
| Unidad de emparejamiento | La ya definida en la familia (pares zona vs control) si aplica |
| Unidad de inferencia | **Sesión** (por clustering; Fano / DEFF del atlas) |
| Holdout | Intact (no se toca) |

Exclusiones pre-declaradas:

- `as_of_ok = false`
- eventos sin `ancho_ticks` si el filtro de Paso 2 lo requiere
- sesiones con < N_min zonas (mismo N_min que la familia base)

---

## 2. Contexto primario — GATE

**Definición**

- `regime ∈ {calmo, normal, volatil, toxico}` en \(t_0\) del evento.
- Códigos: 0/1/2/3 según `gate_context_schema_v1`.
- Tóxico = overlay VPIN del `model_id` (no 4º estado HMM entrenado como tal).

**Celdas de análisis primario (propuesta)**

| Celda | Definición | Rol |
|-------|------------|-----|
| G-operable | `regime ∈ {calmo, normal}` | Primaria (gate “se permite operar contexto”) |
| G-estres | `regime ∈ {volatil, toxico}` | Primaria contrastante |
| (opcional exploratorio) | terciles internos de `post_*` | Secundario; no entra en Holm primario |

**Baseline de comparación (incremental — Paso 4)**  
Mismo estimando condicionado solo a `pct_rv` (CTX-2). La pregunta de CTX-3 no es solo “¿hay efecto en G-operable?” sino, en Paso 4, “¿GATE aporta más allá de `pct_rv`?”.

---

## 3. Hipótesis

**H1 (primaria, no direccional en el estimando de costo/cruce o AbsMagnitude — alinear al estimando vivo de la familia):**  
El estimando primario de la familia, agregado por sesión, **difiere** entre celdas G-operable y G-estres  
(o, si la familia es de equivalencia/nulo: el patrón de equivalencia **no** es el mismo en ambas celdas).

**H0:** ninguna diferencia de celda (tras multiplicidad).

**H2 (secundaria, exploratoria):**  
Dentro de G-operable, el estimando no se degrada vs la población completa (equivalencia dentro de margen pre-fijado).

Las hipótesis se fijan al **estimando ya usado** en H-ES-CTX-2 / acta AbsMagnitude vigente — no se inventa métrica nueva en este documento.

---

## 4. Estimando primario

- **Métrica:** la misma primaria de la familia activa (p. ej. delta pareada de `ticks_por_ancho` **o** AbsMagnitude — **una sola**; rellenar al congelar con el acta viva).
- **Agregación:** mediana (o la misma que CTX-2) **dentro de sesión**; sesión = unidad.
- **Inferencia:** bootstrap de sesiones (B = 10_000, seed declarado), IC 95 %; p bilateral.
- **Multiplicidad primaria:** Holm sobre las pruebas primarias de celda (típicamente 2: G-operable y G-estres, o el contraste G-operable − G-estres como una sola prueba — **elegir una estructura al congelar y no cambiar**).

Secundarias: etiquetadas exploratorias; no alimentan el cierre formal.

---

## 5. Potencia / MDE (publicar antes de correr)

Antes de mirar el estimando:

1. Usar la dispersión **entre sesiones** observada en corridas previas target-free o en CTX-2.
2. Reportar MDE (80 %, α=0,05, bilateral) por celda con el mismo bootstrap de sesiones.
3. Si una celda tiene MDE >> margen de equivalencia de la familia, declarar **sin potencia** (como CTX-2 en terciles extremos).

Fórmula operativa (alineada al lab):  
`MDE ≈ (z_{0.975} + z_{0.80}) * SE_boot_sesiones`.

---

## 6. Multiplicidad

| Familia | Pruebas | Corrección |
|---------|---------|------------|
| Primaria | Contrastes de celda GATE pre-declarados | **Holm** |
| Secundaria / exploratoria | posteriors, sub-terciles, etc. | Sin claim confirmatorio |

No se añaden celdas post-hoc sin nuevo pre-registro.

---

## 7. Criterios de cierre / lectura

| Resultado | Lectura |
|-----------|---------|
| Holm no rechaza H0 en primarias y celdas con potencia tienen equivalencia dentro de margen | Contexto GATE **no separa** el estimando; no rescata la familia |
| Rechazo Holm en dirección pre-registrada (si se fija direccional al congelar) | Contexto **informa**; **aún no es edge** — falta eslabón P&L y gauntlet |
| Celdas sin potencia | Estado: sin efecto detectado + potencia insuficiente (no cerrar a la fuerza) |
| Paso 2 corr(ancho) alta | Trial **no se ejecuta** |

**Este estudio NO decide edge.** No hay reglas de entrada/salida, sizing ni fricción neta.

---

## 8. Firewall y proveniencia

- Holdout del lab: **intacto**.
- Cada corrida de labels: `run_id`, `seed`, `model_id`, `commit`, `schema_version`.
- Artefactos: JSON de labels (schema v1) + JSON de resultado condicionado (espejo de `h_es_ctx2_condicionado.json`).
- Código detector: solo offline; **no** se modifica el `.cs` del indicador.

---

## 9. Desviaciones permitidas (log)

Cualquier cambio post-freeze se registra como desviación con fecha y motivo. Cambios al estimando primario o a las celdas primarias → nuevo pre-registro (CTX-3b).

---

## 10. Checklist de congelado (antes de outcomes)

- [ ] Paso 1: labels reales con `as_of_ok` y proveniencia
- [ ] Paso 2: target-free con veredicto `OK_LOW_CORR` y cobertura reportada
- [ ] `model_id` fijado (Paso 5)
- [ ] Estimando primario copiado del acta viva (una frase, sin ambigüedad)
- [ ] Estructura Holm fijada (1 contraste vs 2 pruebas de celda)
- [ ] MDE por celda publicado
- [ ] Seed y B publicados
- [ ] Firma / OK de Nico para pasar a `PREREGISTERED_READY_TO_RUN`

---

## Referencias de método (plantilla)

- Estilo H-ES-CTX-2 del repo EdgeLab (celdas, Holm, MDE, sesión como unidad, no-edge).
- OSF observational preregistration: hipótesis, diseño, outcomes primarios/secundarios, datos existentes.
- Holm sequential Bonferroni para familia primaria.
- Bootstrap / SE a nivel sesión (cluster).
