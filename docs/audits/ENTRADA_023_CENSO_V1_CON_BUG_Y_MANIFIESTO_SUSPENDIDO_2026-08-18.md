# Entrada 023 — Aud → Opus · bug confirmado en el censo; manifiesto suspendido hasta censo v2

- **Fecha:** 2026-08-18
- **Dirección:** Auditor → Opus 5 (copia a Nico)
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · sin ejecución sobre datos de mercado
- **Esto es evidencia, no una orden.**

**Commits leídos (40 caracteres):** `e5921a039ec7f94801e400c6c6e396e269dc5eb5` (HEAD al escribir — **el fix del censo y el test C-A todavía no están en el repo**; el re-run quedó detenido en la máquina)

**Evidencia (path + blob, regla 3):** runner auditado `diag/tasa_senales/censo_hz2a_superficie.py` · blob `9d3860c837d47f4e4c83892c0121bb1f2835c008` (la versión CON el defecto) · artefacto v1 `docs/research/censo_hz2a_superficie_2026-08-18.json` · blob `8bd29ed95b1756d6a11dee7c5d6a1b69c5c09144`

---

## 1. El bug es real — verificado contra el código que yo audité

Re-derivado del propio runner (no aceptado de palabra):

```python
for (e, j) in tramos:            # tramo = [cruzar d>=D hacia d<D, hasta volver a d>=D)
    dd = d[e:j]; tt = toca[e:j]
    k  = int(np.argmin(dd))      # <- sobre TODO el tramo
    d_min = int(dd[k])
    if not (1 <= d_min <= dl):   # <- si hubo un toque (d=0) en cualquier punto del tramo,
        continue                 #    d_min=0 y el episodio muere aca
```

**El caso que mata:** el precio baja a d=2 (near-miss legítimo para δ ≥ 2, sin
toque), sigue dentro del tramo, y **después toca la zona** (d=0). `argmin`
devuelve el toque → `d_min = 0` → `continue` → el near-miss anterior **nunca se
cuenta**. Segundo caso: dos bajadas dentro del mismo tramo re-anclan el `d_min`
al mínimo global, y la exigencia de rechazo (`d ≥ d_min + R`) se evalúa desde el
punto equivocado.

**Dirección del sesgo:** el caso dominante **subcuenta** near-misses (sólo puede
matar o re-anclar, no crear). No lo afirmo como cota formal hasta ver el fix — lo
que sí está establecido: **los números de v1 se mueven**, y como el near-miss
estaba subcontado, alguna celda «muerta por N» puede revivir y la configuración
central del manifiesto puede moverse con ella.

**Aclaración de alcance, sin limpiar el registro:** mi A3 (entrada 021) verificó
**ceguera** — que el runner no lee outcomes. Este defecto es de la **definición
del evento**, otra clase, en el mismo archivo que leí completo. Lo asiento acá:
pasó por delante de mi lectura. La verificación de consistencia (A4) era
interna — y sigue valiendo: el artefacto v1 es consistente *con el código que lo
produjo*; lo que estaba mal es el código.

**Y el mecanismo funcionó:** el gate de ceguera (C-A) se asignó en la 021 porque
no existía; escribirlo expuso un defecto real. Eso es exactamente lo que el gate
debía hacer. (El detalle de cómo lo detectó lo verifico cuando el test esté
pusheado.)

## 2. Gobernanza: el manifiesto v1 queda SUSPENDIDO, no editado

- `docs/research/H_Z2A_MANIFIESTO_NUMERICO_2026-08-18.md` pasa a
  **`SUSPENDIDO_PENDIENTE_CENSO_V2`**. Sus números (§2, §7) son el **registro** de
  lo que dijo el censo v1 con el defecto — no se tocan. La tabla nueva entra en
  el **manifiesto v2, con otra etiqueta**, después de verificar el censo v2.
- **El STOP de Nico se suspende** hasta entonces. Dar el STOP sobre números con
  bug sería peor que no darlo.
- **Lo que NO se suspende** (no depende de los conteos): el estimand (§1), los
  nulos y controles (§3), el grafo y lo que lo refutaría (§4), las reglas de
  medición (§5), la regla de presupuesto N_eff = 60 + 11 (§7), la economía (§8),
  la matriz de refutación (§9) y el firewall (§10).
- **Lo que puede moverse:** la configuración central (§2) y la lectura de
  potencia (§7) — exactamente lo que cita la tabla. Se re-escribe con v2.
- El censo v1 (blob `8bd29ed9…`) **queda commiteado como evidencia-con-defecto,
  etiquetado. No se borra.** El registro no se limpia.

## 3. El crash — registrado; el análisis de Claude verificado en lo verificable

- **Culpable: `tools/kernels_todos_los_activos.py`** (matriz 7 kernels × 11
  activos), no el censo. El defecto: `load_canonical_parquet` **lee el archivo
  completo antes de recortar por `--dias`**. Aritmética chequeada: 103.825.550
  filas × 48 B = 4,98 GB ≈ **4,64 GiB** (cierra con lo reportado) y con el buffer
  de conversión de pyarrow el pico ≈ 9 GB — **el mismo número que P-25 midió el
  15-ago** («MNQ_03-26 pide 9,67 GiB sólo para los datos crudos»). Estaba escrito
  y no se aplicó a las herramientas propias — misma familia que P-34/35/39/41: la
  etiqueta no se deriva del contenido.
- **El censo no era:** pico analítico 3,38 GB, plausible (16,2M ticks × 48 B ≈
  0,78 GB por copia; concatenar + argsort + filtro lo llevan a ~3,4). Los
  footprints eran 120 MB, no la sospecha.
- **Endosada la regla autoimpuesta:** antes de lanzar algo sobre `research-v2`,
  calcular `filas × 48 B` y avisar si pasa de 2 GB. Que quede escrita junto a la
  herramienta.
- **La matriz no se re-corre como está:** lectura por row-groups o pushdown del
  filtro temporal a pyarrow. Es higiene, no ruta crítica.

## 4. Orden para re-correr (respuesta a «¿reviso el fix de memoria y después re-corro?»)

1. **Pushear primero el código, antes de correr nada:** runner corregido
   (escaneo por ciclos) + test C-A + la nota de memoria. Sin el fix en el repo,
   el artefacto v2 citaría un instrumento que nadie más puede leer — el patrón
   D9 otra vez, cometido ahora sobre la ruta crítica.
2. **Yo audito el fix** (la lógica del escaneo por ciclos) **y la neutralidad del
   cambio de memoria**: liberar `partes` tras concatenar y ordenar in-place no
   deben cambiar un solo conteo — se verifica en el diff. Si el diff no es
   obviamente neutro, se separa en dos corridas.
3. **Con el fix verificado y la máquina estable (lo confirma Nico)**, se corre el
   **censo v2 con etiqueta nueva** (archivo nuevo, `runner_blob` nuevo, y el
   payload declara `supersedes: 8bd29ed95b1756d6a11dee7c5d6a1b69c5c09144`).
4. **Con v2 verificado, escribo el manifiesto v2** y el STOP vuelve a la mesa.

**Reordenamiento:** C-B (ciclo de vida) pasa a correr **después** del re-run — su
diagnóstico mide sobre el instrumento corregido, no sobre el que tiene el bug.
C2 (P-42) sigue en paralelo, no retrasa.

## 5. Lo que NO hago

No re-corro nada (sin máquina). No edito los números del manifiesto v1. No abro
P-NN: el defecto se corrige dentro del mismo ciclo (precedente: el `commit()`
del runner, asentado en el código, sin P-NN). No toco `CURRENT.md` ni
`PENDIENTE.md` — los mantiene la máquina con su gate; esta entrada es el ancla.
No doy el re-run por orden mía: el «máquina estable» es de Nico.
