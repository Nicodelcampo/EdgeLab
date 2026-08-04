# Migración — desde la máquina local (2026-08-04)

Nico recupera acceso a la máquina donde vivía la versión anterior del proyecto.
Este documento es el traspaso: **qué está en GitHub, qué NO puede estar, y qué
hay que hacer para no perder nada.**

Escrito el 2026-08-04 al cierre de la sesión. Rama de trabajo
`fix/capture-probe-v2-contract`, tip **`4a1ba55`**.

---

## 1. TODO EL CÓDIGO Y LA DOCUMENTACIÓN YA ESTÁN EN GITHUB

No queda trabajo sin pushear. Verificado rama por rama y tag por tag:

| ref | estado |
|---|---|
| `fix/capture-probe-v2-contract` | **tip `4a1ba55`** — la rama de trabajo |
| `main` | idéntica al remoto |
| `backup/foundation-f0b-local` | **pusheada hoy** (no tenía remoto) |
| `preserve/f0b-local-divergente-2026-08-04` | **creada hoy** — ver §1.1 |
| tag `baseline-pre-foundation` | ya estaba |
| tag `backup/pre-sync-2026-08-03` | **pusheado hoy** (no estaba) |

### 1.1 Una divergencia que hay que resolver a mano

`foundation/f0b-compatibility-probe` **local** y **remota** divergieron: el
remoto tiene 119 commits que el local no, y el local tenía **1** que el remoto
no (`a48efcd docs: root README for cross-machine handoff`).

Ese commit quedó preservado en `preserve/f0b-local-divergente-2026-08-04`. **No
lo mergeé** — el auditor pidió expresamente *no reconciliar el README* en su
procedimiento de sync. Queda para que Nico y el auditor decidan.

---

## 2. LO QUE **NO** VIAJA POR GIT — leer antes de borrar nada

Está en `.gitignore` a propósito. Si se apaga esta máquina sin copiar esto, se
pierde:

| ruta | tamaño | ¿se puede regenerar? |
|---|---:|---|
| `data/nt8/6E/*.parquet` | **944 MB** (5 archivos, 42–89 MB) | Sí, pero **caro**: exige purgar + redescargar tick data en NT8 y re-correr F2. Fue el trabajo de medio día. |
| `oracles/*.csv` | **55 MB** | **NO automáticamente** — son capturas de NT8. Ver §2.1. |
| `archive/` | 167 MB | backups de `.cs`, incluido `BigTrap2_v2.0_20260804.cs` |
| `runs/` | 368 KB | artefactos de corrida |

### 2.1 Los oráculos de hoy son irreemplazables sin recapturar

Estos CSV salieron de NT8 hoy y **no están en git**:

```
oracles/tickbar_frontera3_10t__Tick10.csv      33 MB  <- la captura que clasifico TICKBAR-001
oracles/tickbar_frontera2_10t__Tick10.csv             (150 barras, submuestreada)
oracles/tickbar_frontera2_10t__Tick10_2.csv           (idem, duplicada por rotacion)
oracles/BigTrap2_tick25_6E_0926_v22.csv        11.6 MB <- MEZCLADO, ver abajo
oracles/split/BigTrap2_v22_6E_0926__Tick25_run1.csv
oracles/split/BigTrap2_v22_6E_0926__Tick10_run2.csv
oracles/split/BigTrap2_v22_6E_0926__Tick10_run3.csv
```

> **`BigTrap2_tick25_6E_0926_v22.csv` contiene TRES corridas appendeadas**
> (una de 25 Tick y dos de 10 Tick), cada una arrancando en `seq=0`, con un
> único `# meta` al tope que describe solo la primera. **No usarlo como
> oráculo.** Las copias en `oracles/split/` son derivadas y **tampoco son
> oráculos** (llevan el `# meta` de la corrida 1). El defecto que lo causó está
> arreglado en `BigTrap2.cs` v2.3, así que **una recaptura ya sale limpia**.

**Recomendación**: copiar `oracles/` y `data/` a la otra máquina por disco o
Drive antes de dar de baja ésta. `archive/` es deseable pero reconstruible.

---

## 3. CLAVES Y SECRETOS

**No hay ninguna en esta máquina.** Verificado:

- **No existe `.env`** ni `.env.*` ni `secrets.*` ni `credentials.*`.
- El remoto `github` usa HTTPS con el credential manager de Windows — **la
  credencial es del sistema operativo, no del repo**. En la otra máquina hay
  que autenticarse de nuevo (`gh auth login` o el prompt de git).
- El remoto se llama **`github`**, no `origin`. Los comandos con `origin`
  fallan con *"does not appear to be a git repository"*.

No hay nada que copiar en materia de secretos. Lo único que se re-configura es
la autenticación de git.

---

## 4. ENTORNO — hay una diferencia declarada que importa

`tests/foundation/test_environment_contract.py` **falla en esta máquina**:

```
pyarrow 22.0.0 < 25          (el contrato declara piso 25)
ModuleNotFoundError: No module named 'duckdb'
```

Intérprete: **Python 3.12.10**, pandas 3.0.3, numpy 2.4.6.

Eso arrastra **27 fallos + 13 errores** en la suite completa
(`test_audit_p3`, `test_store_v2`, `test_coverage_propagation`,
`test_build_viewer`, `test_vectorbt_demo`, `test_features`, `test_campaign`):
todos dependen de `duckdb` o del store, que acá no existen.

**Son ambientales, no regresiones.** Lo verifiqué corriendo la suite ANTES de
tocar nada, sobre el commit del auditor.

> **No actualicé pyarrow a propósito.** PRED-004 dice *"Python congelado"* y
> subir de 22 a 25 toca la lectura de los parquets F2 — podría mover mediciones
> ya publicadas. Si la otra máquina ya tiene pyarrow ≥ 25 y duckdb, **la suite
> debería dar verde ahí**, y eso hay que verificarlo antes de sacar
> conclusiones de cualquier número.

El store de campaña (`runs/nt8_bridge/campaign_store`) **no existe acá**, por
eso no se pudo reproducir CAMP-001 desde el store. **Debería existir en la otra
máquina.**

---

## 5. ESTADO DE TICKBAR-001 / PRED-004 — lo que falta es exactamente lo que la otra máquina puede hacer

### Hecho y pusheado

- **Clasificación**: `ATTRIBUTION_MISMATCH` (H3). H1 descartada (stream
  idéntico: digest `9639232233418205644`, 309.939 eventos). H2 descartada por
  medición directa: **OHLC idéntico en 30.994/30.994 barras**.
- **PRED-003 refutada**: 3,91 % en K=25, 81,78 % en K=10.
- **`BigTrap2.cs` v2.3** (`4a1ba55`): atribución por OHLCV único con ancla
  acotada y verificada, abstención fail-closed, rotación de EventLog.
  - sha256 **`e5dd810a56e4883596d6a01cfffebdf9eda28bccb36cf69941589c7ba684e977`**
  - `check_nt8_cs` OK · 1109 líneas CRLF · 9/9 expresiones triajeadas
  - `csc.exe /t:library`: 146 errores, **todos CS0246/CS0234** (tipos de
    NinjaTrader ausentes acá) · **cero CS1xxx: el archivo parsea**
  - El **camino de tiempo quedó intacto** para garantizar P5 (`time:1`
    bit-idéntico)

### PENDIENTE — requiere NT8, en este orden (PRED-004 §orden_de_ejecucion)

1. **Compilar en NT8** (F5)
2. **`time:1` bit-idéntico** al oráculo previo — P5
3. **Oráculo K=25** — P1, refuta si mismatch > 1 %
4. **Oráculo K=10** — P2, mismo código sin reajustar nada
5. Publicar hashes, tasas de mismatch, **abstenciones** (`ANCLAJE_AMBIGUO`) y
   archivos generados

**Sin esos pasos PRED-004 no está ni confirmada ni refutada.**

### Dos tests en rojo, a propósito

| test | por qué |
|---|---|
| `test_el_cs_canonico_es_el_declarado` | el sha256 del `.cs` cambió (`75910484b7d87510` → `e5dd810a56e48835`). **El pin se mueve cuando el `.cs` esté validado en NT8**, no antes. |
| `test_la_version_del_kernel_coincide_con_la_del_cs` | `.cs` 2.3 vs kernel Python 2.2. Asimetría **real y buscada**: el kernel Python nunca tuvo el defecto (asigna por `tick_bar_idx`, el mismo slice del OHLC) y PRED-004 lo congela. Cómo se expresa esa asimetría lo decide el auditor. |

---

## 6. TRABAJO EN CURSO QUE SE VA A PERDER AL APAGAR

**Censo de tasa de señales, 6 indicadores** — PID 6584, **13,7 h de CPU**,
contrato 2 de 4, ~13 h restantes. Arrancó con el código **previo** al checkpoint
y no se le puede retrofitear: **si se apaga la máquina, se pierde entero.**

Lo que ya está salvado y pusheado:

- **Censo del universo completo para los 4 indicadores rápidos**
  (`post_sepmin_rapidos.json`, commit `bb90d70`): 201 sesiones, 4 contratos.
- Del contrato 1, los dos lentos quedaron en el log (no en JSON):
  `Gaps2` cruda=440,0/día post=10,20/día · `HFTZones2` cruda=521,1/día post=10,15/día

En la otra máquina **conviene relanzarlo con el checkpoint ya implementado**
(`887c6f5`), que guarda a nivel (contrato × indicador):

```bash
python diag/tasa_senales/post_sepmin.py --indicators "Gaps2,HFTZones2"
```

---

## 7. TRAMPAS QUE NOS COSTARON TIEMPO HOY — no repetirlas

1. **Las versiones instaladas en NT8 estaban atrasadas.** `BigTrap2` estaba en
   **v2.0** cuando el repo tenía v2.2, y `HFTZones2` sigue en **v2.0** en el
   NT8 de esta máquina contra **v2.3** del repo. Capturar con la versión vieja
   produce un FAIL sin información. **Verificar por `sha256` contra `nt8/*.cs`
   antes de cualquier captura.**
2. **Rutas.** Los docs citan `E:\EdgeLab\...` y `C:\Users\Usuario\...` — son de
   **la otra máquina**. Acá el repo es `C:\ProyectosQuant\EdgeLab` (worktree
   `EdgeLab-sync`) y **no existe unidad `E:`**. En esta máquina NT8 vive en
   `C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\bin\Custom\Indicators`
   (OneDrive, en español), **no** en `%USERPROFILE%\Documents`.
3. **Tick Replay va DESTILDADO.** Lo declara `BigTrap2.cs`: *"Requiere tick data
   histórico descargado (no Tick Replay)"*. La subserie de 1 tick no lo
   necesita.
4. **`TickBarDiag` va con `SkipBars=0` y `MaxBars=40000`.** Con los defaults
   (20/150) la captura cubre 150 barras y ninguna frontera de sesión.
5. **El ledger de `TickBarDiag` viene en hora del chart, no UTC.** El
   clasificador necesita `--tz-shift-hours 3` con chart en ART. Sin eso da
   *"selección vacía"*.
6. **`MinExportVolume=1`** es el piso analítico; `MinTrapVolume=30` es solo el
   corte on-chart. Confundirlos cambia qué eventos salen al CSV.
7. **`.cs` en CRLF.** Con LF, NT8 agrega una región generada duplicada.
8. Los shells: la consola de Nico es **PowerShell 5.1**, que **no acepta `&&`**.

---

## 8. CHECKLIST DE MIGRACIÓN

**Antes de apagar esta máquina**

- [ ] Copiar `data/nt8/6E/*.parquet` (944 MB) — caro de regenerar
- [ ] Copiar `oracles/` (55 MB) — irreemplazable sin recapturar
- [ ] Copiar `archive/` (167 MB) — deseable
- [ ] Confirmar que no hay ramas ni tags sin pushear *(hecho hoy; re-verificar
      si se trabaja más)*

**En la máquina de destino**

- [ ] `git fetch github` y traer `fix/capture-probe-v2-contract` (tip `4a1ba55`)
- [ ] Autenticar git de nuevo (la credencial no viaja)
- [ ] Verificar entorno: `pytest tests/foundation/test_environment_contract.py`
      — si pyarrow ≥ 25 y duckdb están, la suite completa debería dar verde
- [ ] Correr la suite completa y **comparar contra los 27+13 de acá** para
      separar lo ambiental de lo real
- [ ] Verificar que `runs/nt8_bridge/campaign_store` exista (acá no está)
- [ ] Instalar `nt8/BigTrap2.cs` v2.3 en NT8 **verificando sha256**
      `e5dd810a56e4883596d6a01cfffebdf9eda28bccb36cf69941589c7ba684e977`
- [ ] Ejecutar PRED-004 en su orden: compilar → `time:1` → K=25 → K=10
- [ ] Relanzar el censo con `--indicators "Gaps2,HFTZones2"` (con checkpoint)

---

## 9. DÓNDE ESTÁ CADA COSA

| tema | documento |
|---|---|
| Consolidado de la sesión y las 6 decisiones | `docs/SESION_2026-08-04_PARA_AUDITOR.md` |
| Censo del universo completo | `docs/REPORTE_LOCAL_2026-08-04f.md` |
| Oráculo gastado, PRED-003 refutada | `docs/REPORTE_LOCAL_2026-08-04g.md` |
| Clasificación corregida H2→H3 | `docs/REPORTE_LOCAL_2026-08-04h.md` |
| Handoff del auditor | `docs/REPORTE_INVESTIGACION_2026-08-04l.md` |
| Enmienda formal | `docs/amendments/TICKBAR-001-2026-08-04_attribution_reclassification.md` |
| Predicción pre-registrada | `docs/predictions/PRED-004_tickbar_attribution_v23.json` |
| Hipótesis pospuesta (HFT al cierre en ES) | `docs/HIPOTESIS_PENDIENTES.md` |
| Ambigüedad de stop por resolución | `diag/ejecucion/ambiguedad_stop.py` + `.json` |
