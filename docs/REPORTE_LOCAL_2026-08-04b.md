# Reporte local (2) — 2026-08-04 · calendario, frontera de estimando y estado G2

> Ejecutado en la computadora operativa. Continúa `REPORTE_LOCAL_2026-08-04.md`.
> Referente: `docs/NORTH_STAR.md`.
>
> Este documento **retracta un riesgo** que declaré en el reporte anterior,
> aporta una medición nueva sobre el calendario, y fija la frontera de estimando
> que faltaba. No aprueba nada ni toca la allowlist.

## 1 · RETRACTACIÓN — el riesgo del holdout en el censo estaba mal planteado

En `REPORTE_LOCAL_2026-08-04.md` §2.1 escribí que el corte del holdout *"tiene
que ser explícito en el manifiesto del censo, no implícito en el loader"*.

**Eso es incorrecto y mi propuesta habría sido peor que lo que ya existe.**

Lo que hay hoy:

- `edgelab/research/holdout_guard.py` — frontera efectiva `min(sello, declarada)`
  más `verificar_sello()` contra la fecha del sistema (la mitad temporal del
  ataque de INC-006).
- `edgelab/research/universo_estudio.py::cargar_dias_de_estudio` — **puerta
  única**, fail-closed: sin `incluir_holdout=True` + `purpose` explícito no entra
  ningún día sellado, y la apertura queda en `docs/holdout_access_log.md`.
- `diag/tasa_senales/medir_tasa.py` ya la usa, declarado en su propio encabezado:
  *"los días salen de `cargar_dias_de_estudio` (puerta única) … nada
  >= 2026-07-01 entra."*

La lección de **INC-002** fue exactamente que *el filtro existía pero nadie lo
llamaba*. Mover el corte al manifiesto habría creado un segundo lugar donde el
holdout se decide — que es el defecto original, no su arreglo. **El corte debe
seguir viviendo en la puerta única.**

Lo que sí queda en pie de aquel riesgo es el **margen de tamaño**: hay ~235 días
hábiles pre-frontera para llenar las 200 sesiones que declara la ESPEC. Sigue
siendo estrecho y conviene declarar por anticipado qué pasa si el universo
elegible cae por debajo de 200, para no decidirlo después de ver los datos.

**No verificable localmente:** `manifiesto_universo.json` no existe en esta
máquina (lo genera el censo y no está versionado), así que la puerta única no se
pudo ejercitar contra datos reales acá. La verificación empírica queda pendiente
del lado donde exista el manifiesto.

## 2 · MEDICIÓN NUEVA — son DOS feriados, no uno, y el número cuadra

`docs/parity_coverage/aVolCellPOI2_medicion_2026-08-01.md` atribuye el desfase
de enumeración a *"feriado del 3 de julio, warm-up"* y mide un **+2 constante**
en `session_index` (0/111 coinciden).

Medido sobre `6E 09-26` (último tick por día calendario CT):

```
viernes normales      15:59 CT   (cierre 16:00)
  2026-06-12          15:59 CT
  2026-07-10          15:59 CT
  2026-07-17          15:59 CT

CIERRE ANTICIPADO     14:59 CT   (cierre 15:00)
  2026-06-19          14:59 CT   <- Juneteenth
  2026-07-03          14:59 CT   <- 4 de julio observado
```

**Hay dos cierres anticipados en el rango, no uno.** Y el número coincide
exactamente con el desfase medido: el perfil usa `lookback_sessions=20`, que
desde la ventana de medición (2026-07-13 → 07-16) alcanza hasta mediados de
junio, abarcando **ambos** feriados. Dos feriados no modelados → **+2 sesiones**.

Controles que descartan explicaciones alternativas:

- **No falta ningún día hábil** en el rango del contrato (2026-06-08 → 07-22):
  la hipótesis "Python cuenta una sesión fantasma en un día cerrado" queda
  descartada — esos días existen en los dos lados, con datos.
- Los dos días que un filtro por volumen marca como anómalos (2026-06-08 al 19%
  y 2026-07-22 al 0,1%) son **artefactos de borde**: primer y último día del
  contrato, parciales por definición. No son feriados.
- El 2026-07-03 **no fue cierre total**: 33.405 ticks, 53% de la mediana. Fue
  cierre anticipado, que es un modo de falla distinto y más sutil.

### 2.1 Consecuencia para el arreglo

`edgelab/bridge/sessions.py` declara desde su primera línea: *"Feriados NO
modelados: declarado; si el oráculo NT8 difiere en un feriado, aparece como diff
de paridad y se documenta."* La limitación estaba declarada desde el día uno y
ahora muerde exactamente donde se predijo.

El arreglo es un **calendario CME versionado** con, como mínimo, los cierres
anticipados. Pero hay que advertir el alcance:

> `sessions.py` es un primitivo **compartido**. Cambiar la enumeración de
> sesiones altera también la calibración por sesión de HFTZones2, que hoy está
> en PASS. **Un arreglo de aVolCellPOI2 puede romper la paridad de HFTZones2.**
> No es un cambio aislado y no debe hacerse sin re-correr la paridad de todos
> los kernels que dependen de sesión.

Por eso no se implementa acá: es un cambio semántico con radio de impacto, no un
fix local. Queda medido y listo para decidir.

## 3 · Frontera de estimando: `p_global` (EXPLORE) vs `theta_trade` (G2)

Resuelve el riesgo §2.2 del reporte anterior. **Ninguno de los dos documentos
cambia**; lo que faltaba era declarar el límite entre ellos.

| | EXPLORE-001 §1.3 | Enmienda G2 §2.1 |
|---|---|---|
| estimando | `p_global = mean_d p_dia(d)` | `theta_trade = Σ pnl / Σ trades` |
| unidad | el DÍA, equal-weight | el TRADE (ratio de totales) |
| pregunta | ¿existe una regularidad direccional? | ¿hay expectativa económica neta? |
| gate | G1 / exploratorio | **G2** |

**Los dos son correctos para su propia pregunta**, y la razón es la misma que da
la literatura de *informative cluster size*: el promedio-por-cluster y el
promedio-por-participante son **estimandos distintos**, y se elige por objetivo
de inferencia. EXPLORE evita pseudo-replicación (20 zonas del mismo día comparten
régimen y no son 20 observaciones independientes); G2 persigue el dinero, que se
acumula por trade y no por día.

### 3.1 Declaración

```
Un PASS de EXPLORE-001 medido con `p_global` es evidencia de nivel G1
(regularidad direccional). NO constituye, por sí solo, evidencia G2 ni
autoriza el estado `statistically_supported`.

Para pasar a G2, el candidato debe volver a evaluarse con `theta_trade`
como primaria, bajo el contrato G2 vigente. La prohibición de §2.3 sobre
`mean_d(u_d/v_d)` y `p_favorable` aplica al gate G2 y NO invalida su uso
como primaria exploratoria en EXPLORE-001.
```

Sin esta frontera escrita, un EXPLORE positivo puede leerse como
`statistically_supported` — que es exactamente lo que §2.3 existe para impedir.
La prohibición no era un error del autor de la ESPEC ni del de la enmienda: era
una frontera implícita que nadie había puesto por escrito.

## 4 · Estado real de los criterios #5 y #6 de la enmienda §12

Verificado leyendo el código, no inferido.

### #6 — `ValidationDecision` se serializa y valida

**Estructuralmente MET.** `edgelab/research/promotion.py::_validate_g2` exige,
antes de materializar cualquier estado ≥ `statistically_supported`:

- `decision_id`, `gate == "G2"`, `passed is True`;
- `contract_sha256` **presente en `APPROVED_G2_CONTRACT_SHA256S`**;
- `evidence_digest`;
- los cinco `required_gates` exactos con sus `gate_results`.

`b574d6c` ("reconstruct canonical G2 decisions before promotion") cerró el
bypass que aceptaba la forma mínima. Los 26 tests de `test_promotion.py` pasan en
entorno canónico.

**Lo que NO está met es distinto de lo que #6 pide:** la allowlist está vacía. Eso
no es un defecto pendiente — **es el mecanismo funcionando**. La allowlist vacía
es lo que impide promover mientras nadie haya aprobado un contrato.

### #5 — DSR con tratamiento explícito de dependencia

**NO MET, y no es resoluble sin una decisión.** El umbral `>= 0.95` está
implementado. Lo que falta es el tratamiento de dependencia por sesión, y hay dos
caminos, que NO son equivalentes:

**(a) Implementar DSR bajo dependencia.** Requiere un `N_eff` defendible. Pero la
ESPEC §0.2 ya declaró que `N_ef = N/b_opt` **es una heurística comparativa, no
una cantidad de observaciones independientes**. Usarla para deflactar el Sharpe
sería precisamente el tipo de salto que el proyecto rechaza. Esto es investigación
real, no una línea de código.

**(b) Declarar DSR como no-autoritativo.** La enmienda §6 ya dice: *"Hasta
validar una implementación compatible con dependencia por sesión, DSR no puede
emitir PASS formal aunque produzca un número."* Bajo esta lectura, el tratamiento
explícito **existe y es fail-closed**: DSR se computa, se reporta, y no puede
aprobar. El costo es que §9 exige los cinco gates en PASS, así que con DSR
incapaz de PASS **ningún candidato puede pasar G2** — la enmienda quedaría
aprobada pero inerte.

**Recomendación:** (b) es honesto pero deja el pipeline bloqueado, así que hay
que elegir a conciencia entre:

1. aprobar la enmienda y aceptar que G2 queda inerte hasta resolver DSR;
2. enmendar §9 para que DSR sea un veto reportado y no un gate estructural
   obligatorio, dejando el IC primario de `theta_trade` como gate decisorio;
3. postergar la aprobación hasta tener (a).

**No elijo por Nico.** Las tres cambian qué puede promoverse y cuándo, y esa es
una decisión de autoridad, no de implementación.

## 5 · Lo que este reporte NO hace

- No agrega ningún hash a `APPROVED_G2_CONTRACT_SHA256S`. Ese acto **es** la
  aprobación y el diseño fail-closed existe para que lo ejecute un humano
  informado.
- No modifica `sessions.py` ni el calendario: es un primitivo compartido y el
  cambio puede romper la paridad de HFTZones2 (§2.1).
- No modifica ninguno de los dos estimandos: sólo declara su frontera (§3.1).
- No ejecutó el censo ni seleccionó H1–H3.
- No verificó la puerta única contra datos reales: falta `manifiesto_universo.json`
  en esta máquina (§1).

**Aporte al referente:** se retracta un riesgo mal planteado antes de que
generara trabajo inútil, se mide que el desfase de calendario son **dos**
feriados de cierre anticipado —número que coincide con el `+2` observado— y se
fija por escrito la frontera que impide que un EXPLORE positivo se lea como
evidencia económica.
