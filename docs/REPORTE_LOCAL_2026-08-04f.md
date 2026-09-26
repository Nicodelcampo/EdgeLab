# REPORTE LOCAL — 2026-08-04f

**Censo de tasa de señales sobre el universo completo (4 de 6 indicadores) + checkpoint**

Commits: `887c6f5` (herramienta), `bb90d70` (resultado). Base: `a390bc7`.

---

## 1. Lo que cambió respecto del censo publicado

El censo que estaba publicado (`diag/tasa_senales/post_sepmin.json`) cubre **20
sesiones en 2 contratos** (10 + 10). Esto lo digo como hecho de cobertura, no
como reproche: era el piloto disponible antes de que los datos limpios
existieran en esta máquina.

Lo que se agrega ahora (`post_sepmin_rapidos.json`) cubre **201 sesiones en 4
contratos**, sobre los parquets reexportados con `dup_bloque=0`. Diez veces la
cobertura, al precio de 4 de los 6 indicadores.

Faltan `Gaps2` y `HFTZones2`, que son los caros. Están declarados en el
manifiesto como `indicadores_parciales: true` / `faltan_indicadores`, así que el
artefacto no puede confundirse con un censo cerrado.

## 2. Resultado

Universo: 201 sesiones, 4 contratos, `sep_min=120`, `lead_days=20`,
`outcomes_accessed: false`.

| indicador | cruda/día | post/día | TOTAL post | supervivencia | días=0 |
|---|---:|---:|---:|---:|---:|
| AACloseOpenDiffs | 603,55 | 11,06 | 2224 | 1,8 % | 0 |
| BigTrap2 | 79,37 | 8,84 | 1777 | 11,1 % | 0 |
| aVolCellPOI2 | 42,34 | 6,50 | 1307 | 15,4 % | 24 |
| VolTicksPOC2 | 7,31 | 3,41 | 685 | 46,6 % | 2 |

### 2.1. El techo mecánico se confirma fuera del piloto

Las tasas **crudas** abarcan un factor de 83. Después de `sep_min=120` colapsan
a un factor de 3,2. La supervivencia cae de 46,6 % a 1,8 % en proporción
inversa casi exacta a la tasa cruda.

La lectura es la que ya habías planteado como hipótesis: `sep_min` **no está
filtrando señales malas, está saturando**. Un indicador que produce 600 eventos
por día y otro que produce 7 terminan entregando 11 y 3,4 respectivamente,
porque lo que manda es cuántas ventanas de 120 minutos entran en una sesión, no
la productividad del indicador.

Esto tiene una consecuencia de diseño que dejo planteada sin resolver: **la tasa
post-`sep_min` casi no discrimina entre indicadores**, así que no sirve como
criterio de selección. Si se quiere comparar indicadores por productividad, hay
que hacerlo antes del anti-solapamiento o con un `sep_min` que no sature.

### 2.2. El piloto de 20 sesiones generalizaba mejor de lo esperable

| indicador | cruda/d piloto → completo | post/d piloto → completo |
|---|---|---|
| AACloseOpenDiffs | 611,75 → 603,55 (−1,3 %) | 10,85 → 11,06 (**+2,0 %**) |
| BigTrap2 | 94,65 → 79,37 (−16,1 %) | 8,95 → 8,84 (**−1,2 %**) |
| aVolCellPOI2 | 50,90 → 42,34 (−16,8 %) | 7,25 → 6,50 (**−10,3 %**) |
| VolTicksPOC2 | 7,25 → 7,31 (+0,8 %) | 3,50 → 3,41 (**−2,6 %**) |

Las tasas crudas se desviaron hasta −17 %. Las post-`sep_min` se desviaron
≤ 2,6 % en tres de los cuatro. Es la misma saturación vista por otro lado: el
piloto acertó porque la magnitud que midió estaba determinada por la estructura
de la sesión, no por la muestra.

La excepción es `aVolCellPOI2` (−10,3 %), arrastrado por `6E_09-26`: 3,08/día
contra ~6,7 en los otros tres contratos. Ese contrato aporta 13 sesiones. **No
lo interpreto**: puede ser el contrato, puede ser el tramo de junio, puede ser
el tamaño de muestra. Queda registrado como anomalía abierta.

`aVolCellPOI2` es también el único con muchos días en cero: 24 de 201, y 6 de
esos 24 caen en un solo contrato de 13 sesiones.

### 2.3. Sobre `MIN_STUDENTIZED_SESSIONS=160`

Los cuatro superan el mínimo de sesiones con al menos una señal; el peor caso es
`aVolCellPOI2` con 177. Lo anoto porque es una precondición que conviene tener
verificada antes de cualquier ESPEC, no porque implique nada sobre H1–H3.

**Esto sigue siendo outcome-free. No llené H1–H3 ni voy a hacerlo antes de que
revises cobertura y saturación.**

## 3. Checkpoint (`887c6f5`)

Motivo concreto: la corrida completa cuesta ~25 h de CPU en esta máquina
(`HFTZones2` solo tardó **18.070 s = 5,0 h** sobre 60 sesiones, `Gaps2`
**8.143 s = 2,3 h**), y el resultado se escribía **una vez, al final**. Una
caída en la hora 24 costaba las 24.

Grano: **(contrato × indicador)**. Es la unidad de cómputo real — va de 3 s
(`BigTrap2`) a 5 h (`HFTZones2`). Más fino no existe sin partir el barrido de un
indicador; más grueso (por contrato) perdería hasta 8 h.

Diseño fail-closed: el checkpoint guarda un `sha256` de
`(plan, universo, commit, sep_min, lead_days)`. Si no coincide se levanta
`CheckpointMismatch` y **no se borra el archivo ajeno**. Mezclar dos
configuraciones dentro de un mismo censo es exactamente lo que el manifiesto
existe para impedir, así que no se descarta en silencio: hay que pedirlo con
`--fresh`. El archivo se declara `complete: false` y lleva `unidades_pendientes`.

También `--indicators` (subconjunto) y `--out` (no pisar el censo publicado
mientras corre uno parcial).

12 tests en `tests/research/test_census_checkpoint.py`. Suite completa de
`tests/research/`: **165 passed, 4 skipped**.

## 4. Estado de la corrida completa — y una limitación que no puedo arreglar

La corrida de los 6 indicadores sigue viva (PID 6584, arrancada 05:11 UTC,
9,15 h de CPU). Terminó el contrato 1 completo y va por el 2.

**Corre con el código anterior al checkpoint.** No se le puede retrofitear.

Evalué matarla y relanzarla con `--indicators "Gaps2,HFTZones2"` para que quede
protegida. La descarté con números: relanzar rehace el contrato 1 (7,3 h ya
pagadas) y lleva el total restante de ~15 h a ~26 h. Se queda corriendo
desprotegida, que es el mal menor. Lo dejo dicho explícitamente para que no
parezca un descuido: **si esa corrida se cae, se pierden ~24 h de CPU.**

Lo que ya está a salvo del contrato 1, del log:

```
Gaps2       cruda=440,0/día  post-sep_min=10,20/día  días_cero=0  (8143 s)
HFTZones2   cruda=521,1/día  post-sep_min=10,15/día  días_cero=0  (18070 s)
```

Ambos caen dentro de la banda 10–11 de los otros indicadores de alta tasa
cruda — o sea, la saturación aplica también a los dos que faltan. Es evidencia
parcial (un contrato), no el resultado.

## 5. Nota de método

La corrida rápida tardó **183 s** para el universo completo, contra las 5 h que
`HFTZones2` tardó en un solo contrato. Esa asimetría de 100× es la que hace que
separar rápidos de lentos valga la pena, y es la que justifica el grano del
checkpoint.

Se corrió en paralelo con la lenta vigilando RAM: la máquina tiene **8 GB, no
16** como asume el docstring de `censo_integridad.py`. La libre osciló entre
890 y 2.190 MB sin tocar piso. Vale la pena corregir ese docstring.

## 6. Abierto

- Anomalía `aVolCellPOI2` en `6E_09-26` (§2.2) — sin interpretar.
- La tasa post-`sep_min` no discrimina entre indicadores (§2.1) — decisión de
  diseño pendiente.
- Criterio #5 de la enmienda G2 (DSR bajo dependencia) — espera decisión de Nico.
- Taxonomía de veredictos del capture-auditor (`PASS` inalcanzable) — diferido
  por vos.
- Calendario de feriados CME en `sessions.py` — medido, no implementado.
- Paridad `aVolCellPOI2` — bloqueada, el oráculo no está en esta máquina.
- Docstring de `censo_integridad.py` asume 16 GB.
