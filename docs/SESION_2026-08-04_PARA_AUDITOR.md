# Sesión 2026-08-04 — consolidado para el auditor

Todo lo hecho hoy en la máquina local, en un solo documento. Los reportes
detallados están en `docs/REPORTE_LOCAL_2026-08-04{f,g,h}.md`; acá va el
resumen y, arriba de todo, **lo que necesita una decisión que no es mía**.

Rama `fix/capture-probe-v2-contract`, commits `a390bc7` → `c4962f3`.

---

## 1. DECISIONES PENDIENTES

### D1 · `tools/tickbar_diag.py` — la firma `ATTRIBUTION_MISMATCH` es inalcanzable

El test de H2 usa `n_events` por barra como proxy de los cortes de barra
(línea 200: `cuts_ok = cuts_equal == m`), y H3 exige `cuts_ok` (líneas 212,
248). Pero `n_events` **no es el corte de barra**: es la atribución que hizo el
indicador. Con eso, `ATTRIBUTION_MISMATCH` no puede emitirse nunca cuando la
atribución está rota — el único caso en que hace falta. Rama muerta, misma
forma que el `PASS` inalcanzable del capture-auditor.

Esto no es teórico: **hoy produjo una clasificación equivocada** (ver §2). El
ledger ya trae el OHLC por barra, así que el test correcto está disponible sin
recapturar.

**No lo toqué.** Cambiar el criterio de un clasificador después de ver los
datos que clasifica es lo que el pre-registro impide. Es tuya la decisión.

### D2 · ¿Enmienda a TICKBAR-001 por el cambio de clasificación?

La clasificación pasó de H2 a H3 **después** de gastar el oráculo. La
predicción falsable del fix se escribe sobre la clasificación corregida, pero
eso implica registrar una enmienda con acceso a datos ya visto. Cómo se
formaliza es criterio tuyo.

### D3 · La tasa post-`sep_min` no discrimina entre indicadores

Medido sobre el universo completo (§3.1): las tasas crudas abarcan un factor de
83 y las post-`sep_min` colapsan a un factor de 3,2. `sep_min=120` **satura**;
no filtra señales malas. Consecuencia: **no sirve como criterio de selección de
indicador**. Si se quiere comparar productividad hay que hacerlo antes del
anti-solapamiento o con un `sep_min` que no sature. Decisión de diseño.

### D4 · Censo — revisión de cobertura y saturación antes de H1–H3

Como pediste, **no llené H1–H3**. El censo del universo completo está en §3.1
para que revises cobertura y saturación primero.

### D5 · Criterio #5 de la enmienda G2 (DSR bajo dependencia)

Sigue esperando decisión de Nico desde antes de esta sesión. Sin cambios.

### D6 · `BigTrap2.cs` appendea el EventLog *(bajo riesgo, listo para aprobar)*

`BigTrap2.cs` abre el `EventLogPath` en modo append, sin sufijo de resolución ni
rotación de índice. Hoy tres corridas cayeron en un solo archivo (647 KB →
11,6 MB), cada una desde `seq=0`, con un único `# meta` describiendo solo la
primera. Es el modo de falla del 2026-07-24.

`TickBarDiag` v1.1 ya lo resolvió y **funcionó hoy** (rotó a `__Tick10` y
`__Tick10_2` sin que se lo pidiéramos). Portar esa protección es mecánico, no
toca el kernel y no es la causa de ningún mismatch — es trazabilidad.

---

## 2. TICKBAR-001 — el oráculo se gastó, y la conclusión final NO es la del clasificador

Capturas de Nico en NT8, `BigTrap2.cs` v2.2 (`75910484b7d87510…`, instalado y
verificado por hash), **Tick Replay destildado** (confirmado), ventana
`6E 09-26` pre-holdout 2026-06-14 → 06-18.

### 2.1 PRED-003 refutada en sus dos predicciones

| corrida | K | barras | `FOOTPRINT_MISMATCH` | resyncs | zonas |
|---|---:|---:|---:|---:|---:|
| 1 | 25 | 12.395 | **3,91 %** (predicho 0 %, corte 1 %) | 1 | 322 |
| 2 | 10 | 30.993 | **81,78 %** (P2: generalidad) | 3 | **0** |
| 3 | 10 | 30.993 | 81,78 % (idéntica a la 2) | 3 | 0 |

Determinista. Por la regla pre-registrada el fix se rechaza como está.

### 2.2 Lo que el fix sí consiguió

El defecto viejo era **asignación de volumen** (baldes de 15 a 34 eventos donde
iban 25) y era **silencioso**. Hoy los 25.832 mismatches dicen todos
`n_eventos=K, k=K`: **el conteo quedó correcto en las dos resoluciones**. Lo que
falla es la identidad OHLC, que es el verificador *nuevo* de v2.2.

Y en K=10 la política de rotura **suprimió todas las zonas** en vez de dejar
entrar 30.000 barras de footprint corrupto al store. v2.2 convirtió una
corrupción silenciosa en una detenida y puesta en cuarentena.

### 2.3 La clasificación, corregida

Captura completa (`skip_bars=0`, `max_bars=40000`, 340.936 filas, las cuatro
fronteras de sesión adentro). El clasificador devolvió `BAR_BUILDER_MISMATCH`.
**La medición directa lo contradice:**

```
OHLC de NT8 vs bars.build_tick_bars(tk, 10), índice contra índice:
IDÉNTICO en 30.994 de 30.994 barras = 100,00 %
```

Con:

| | |
|---|---|
| stream de ticks | **idéntico** — digest `9639232233418205644` en los dos lados, 309.939 eventos |
| cortes de barra | **idénticos** — OHLC 100 % |
| `n_events` por barra | difiere en **81,6 %** |

Si el stream es el mismo y los cortes son los mismos, lo único que queda es **a
qué barra se asigna cada evento**: **H3 `ATTRIBUTION_MISMATCH`**, no H2.
Refuerza: media de eventos por barra **exactamente 10,00**, drift **−2 sobre
30.994 barras**. Un constructor de barras equivocado no da media exacta.

**Hasta que se resuelva D1, el veredicto del clasificador no debe usarse:**
contradice evidencia directa que no depende de ningún proxy.

### 2.4 Consecuencias

1. **El lado Python está exacto y no se toca.** Valida `build_tick_bars` con
   reinicio por sesión y, de rebote, valida el conversor F2 por vía
   independiente: el digest de 310 k eventos coincide con NT8.
2. **El fix va en el `.cs`**, en cómo el secuenciador empareja eventos BIP1 con
   barras — no en cómo se cortan. v2.2 agrupa por **orden de llegada** en
   bloques de K y los aparea con el snapshot de la barra N; K eventos
   consecutivos no son los eventos de la barra N aunque la barra esté bien
   cortada.
3. No se diseñó ni implementó ningún fix (TICKBAR-001 §6).

---

## 3. Censo de tasa de señales

### 3.1 Universo completo, 4 de 6 indicadores *(`bb90d70`)*

201 sesiones, 4 contratos, datos limpios (`dup_bloque=0`). El censo publicado
cubría 20 sesiones en 2 contratos: esto es **10× la cobertura**.

| indicador | cruda/día | post/día | TOTAL post | supervivencia | días=0 |
|---|---:|---:|---:|---:|---:|
| AACloseOpenDiffs | 603,55 | 11,06 | 2224 | 1,8 % | 0 |
| BigTrap2 | 79,37 | 8,84 | 1777 | 11,1 % | 0 |
| aVolCellPOI2 | 42,34 | 6,50 | 1307 | 15,4 % | 24 |
| VolTicksPOC2 | 7,31 | 3,41 | 685 | 46,6 % | 2 |

**El piloto de 20 sesiones generalizó mejor de lo esperable**: las tasas crudas
se desviaron hasta −17 % pero las post-`sep_min` ≤ 2,6 % en tres de cuatro. Es
la misma saturación vista por otro lado — midió estructura de sesión, no
muestra. Excepción: `aVolCellPOI2` (−10,3 %), arrastrado por `6E_09-26`
(3,08/día contra ~6,7 en los otros tres). **Anomalía abierta, sin interpretar.**

Los cuatro superan `MIN_STUDENTIZED_SESSIONS=160` (peor caso 177).

> **Aviso sobre a qué configuración corresponden estos números.** Se midieron en
> `time:1`. Por el propio marco de TICKBAR-001 —*«`time:1` fue el laboratorio
> donde se verificó la fidelidad del traductor, no el hábitat de la
> hipótesis»*— la tasa de BigTrap2 es la del laboratorio. No es la tasa de la
> hipótesis que se quiere testear. Mi reporte inicial no hizo esa distinción.

### 3.2 Checkpoint *(`887c6f5`)*

Grano **(contrato × indicador)** — la unidad de cómputo real, de 3 s (BigTrap2)
a 5 h (HFTZones2). Fail-closed por `sha256` de
`(plan, universo, commit, sep_min, lead_days)`: si no coincide levanta
`CheckpointMismatch` y **no borra el archivo ajeno**; para descartarlo hay que
pedir `--fresh`. Se declara `complete: false` con `unidades_pendientes`.
Además `--indicators` y `--out`. 12 tests; `tests/research/`: **165 passed, 4
skipped**.

### 3.3 Corrida completa — en curso y desprotegida

Los 6 indicadores siguen corriendo (PID 6584, **11,0 h de CPU**), contrato 2 de
4. **Arrancó con el código previo al checkpoint y no se le puede retrofitear.**
Evalué matarla y relanzarla protegida: rehacer el contrato 1 llevaría el
restante de ~15 h a ~26 h. Queda corriendo. **Si se cae, se pierden ~24 h.**

---

## 4. Resolución de ejecución *(`4e6b19d`, autorizado por Nico)*

Preocupación de origen: backtestear sobre m1 en vez del movimiento real puede
**esconder** un edge, porque cuando target y stop caen en la misma barra la
spec §6.3 resuelve «gana el adverso».

Patrón de oro: con steps de tick `low=high=last`, así que `hit_t and hit_s`
exigiría `tgt <= stp` — imposible. **Ambigüedad exactamente cero.**

Señales construidas UNA vez sobre m1 y simuladas sobre seis streams (solo varía
la resolución de ejecución). Gaps2 con params de CAMP-001, ventana pre-holdout,
835 trades:

| res | trades | ambiguos | % | neto (ticks) |
|---|---:|---:|---:|---:|
| tick | 835 | 0 | 0,00 | −622,0 |
| 1s | 835 | 0 | 0,00 | −619,0 |
| 5s | 836 | 0 | 0,00 | −615,0 |
| 10s | 835 | 0 | 0,00 | −620,0 |
| 30s | 835 | 0 | 0,00 | −621,0 |
| **60s (m1)** | 836 | **1** | **0,12** | −630,0 |

Distribución de salidas idéntica (525 stop, 285 target). El neto difiere **8
ticks sobre 835 trades**.

**El mecanismo importa más que el número.** La ambigüedad exige que el rango de
la barra contenga los dos niveles:

- rango de barra m1 en 6E: mediana **2** ticks, p90 4, p99 11, máx 98
- span `stop+target` de Gaps2: mediana **18** ticks, p10 10, p05 8

Con el span 9× el rango mediano hace falta que una barra p99 se cruce con una
señal p05. **El resultado NO se generaliza**: con span ~4 ticks se estaría en el
p90 del rango y la exposición sería de otro orden — que es justo el caso de
BigTrap2, indicador de microestructura con stops cortos. El criterio operativo
es comparar el span previsto contra la distribución de rango de la resolución
candidata, no heredar este número.

**No reproduce CAMP-001**: usa sus params pero el `kernel_id` cambió desde el
sellado, así que el `config_id` es otro y esto no restablece ni revisa su
veredicto.

---

## 5. Comparación de indicadores HFT *(consulta de Nico)*

`HFTZones2.cs` línea 2: *«Consolida: HFTZonesESPureV2 (motor + FIX#1-3) +
HFTZonesNQPureV3 (retro relativo)»*. **No son alternativas: HFTZones2 es el
descendiente de ESPureV2.**

| | ESPureV2 | HFTZones2 v2.3 |
|---|---|---|
| umbrales | fijos, calibrados a **ES** (`MinVolumeRate=500`) | adaptativos por instrumento, congelados al inicio de sesión |
| guarda de resolución | **ninguna** | `frac_zero_ms`, `resolution_limited` |
| sesgo `isDown`-first | **presente** (línea 317) | corregido y declarado |
| export / paridad | **no tiene** | `EventLogPath`, `# meta` |

Recomendación: **HFTZones2 v2.3**. Sin export no hay oráculo y sin oráculo no
hay ledger. `AdaptiveMode=false` permite el A/B con los umbrales de ESPureV2,
con export en los dos lados, que es la vía limpia si Nico prefiere ese
comportamiento.

**Hallazgo colateral que sí importa:** en 6E la **mediana del intervalo entre
ticks es 0 ms durante toda la sesión** ⇒ `Q(0.50)=0` ⇒ `resolution_limited=1`
por el gate P0 del propio indicador. **Los buckets PREDATOR/ULTRA/FAST no son
confiables en 6E**, no solo al cierre. ESPureV2 no tiene forma de detectarlo.

Versiones instaladas en el NT8 de Nico estaban atrasadas: `BigTrap2` v2.0
(repo: v2.2) y `HFTZones2` v2.0 (repo: v2.3). BigTrap2 se actualizó hoy con
backup previo; HFTZones2 **sigue en v2.0** en su NT8.

---

## 6. Correcciones y retractaciones de la sesión

Registradas porque el método las produjo, no a pesar de él.

1. **`config_id` de CAMP-001 no es reproducible** con el kernel de hoy
   (`kernel_id` cambió). No es defecto: es el sistema de identidad funcionando.
   Dejé de perseguirlo y declaré la diferencia en vez de forzar el hash.
2. **Tres hipótesis propias caídas por medición**, todas antes de tocar código:
   - empates de timestamp en la frontera → 67 % en K=25 **y** en K=10; no
     discrimina.
   - corrimiento constante de eventos → predice 23 % para K=25 y K=10;
     observado 3,91 % y 81,78 %.
   - «NT8 cuenta timestamps únicos» → 3,33 únicos por barra, 0,4 % en 10.
3. **La clasificación del clasificador** (§2.3), contradicha por OHLC.
4. En el reporte del censo **omití** que los números son de `time:1`, o sea del
   laboratorio y no del hábitat. Corregido en §3.1.

---

## 7. Fuera de alcance / pospuesto

- **HP-001** — burst de zonas HFT al cierre en **ES**. Registrado en
  `docs/HIPOTESIS_PENDIENTES.md` con su forma medible y su precondición
  (verificar `resolution_limited` en ES primero). Pospuesto por foco en 6E.
  En 6E se midió y da lo contrario: 1.775 zonas concentradas en horas de máxima
  liquidez, 2,5 % en la hora previa al cierre.
- **Filtro de mecha de BigTrap2** — lo que Nico prefiere de BigTrap v1 son dos
  perillas de v2 (`use_wick_filter=false`, `max_age_bars=0`), no la versión
  vieja. `use_wick_filter=false` **ya es PASS 393/393** (oráculo O3) y es
  corrible en `time:1` sin depender de TICKBAR-001.
- Sin cambios: taxonomía del capture-auditor, feriados CME en `sessions.py`,
  paridad `aVolCellPOI2` (oráculo ausente en esta máquina), `LongPathsEnabled`.
- `runs/` y `oracles/*.csv` están gitignored: los CSV de oráculo **no** viajan
  al repo. Quedaron locales.
