# HANDOFF — familia AVZP2 (aVolZonePOI2) y racimos — 2026-10-08

Escrito para que **cualquier agente continúe sin acceso a la conversación** que lo produjo. Rama:
`foundation/f0b-compatibility-probe` (worktree de trabajo `E:\EdgeLab-gex`). Hash NORTH_STAR vigente:
`ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.

## 0. Resumen en 6 líneas
1. **aVolZonePOI2** es la versión mejorada de `aVolZonePOI`: zonas de volumen anómalo, orderblocks (rojo) y racimos
   (violeta). **Paridad NT8↔Python exacta** en 200t (defaults) y en 25t (configuración de Nico).
2. Las zonas sueltas **no rebotan más que el azar** (AVZP2-REBOTE). Las rojas parecían rebotar, pero era el
   "alejamiento limpio" (nulo apareado OB).
3. Los **racimos comprimen**: después de salir de la franja, el precio se mueve 4–10 % menos que en una consolidación
   de la misma ocupación. **Robusto en 23/23 definiciones; 21 confirman.**
4. En **racimos largos y anchos** (ventana 1.000 velas, altura 30–45 ticks), **la salida va a favor de la tendencia
   previa** +5 a +8 pp sobre el azar apareado (controlando magnitud de tendencia y momentum). **Confirmado.** Con la
   config de Nico (6/500/30) ese efecto es 0.
5. Sin seguimiento de ruptura ni rebote en las líneas, en ninguna definición.
6. **Nada de esto tiene P&L medido.** El siguiente paso natural es un manifiesto de P&L (requiere STOP y OK de Nico).

## 1. El indicador
| artefacto | ruta |
|---|---|
| NT8 (fuente que usa Nico) | `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\aVolZonePOI2.cs`; copia versionada en `nt8/aVolZonePOI2.cs` |
| aVolZonePOI original (con logger agregado, sin grupos naranja) | `nt8/aVolZonePOI.cs`; original sin tocar en `nt8/aVolZonePOI.cs.orig_20261007` |
| réplica Python | `edgelab/bridge/indicators/avolzonepoi2.py` (`run(bars, footprints_csr, session_id, params)`) |
| réplica Python del original (v1) | `edgelab/bridge/indicators/avolzonepoi.py` |

### Reglas de aVolZonePOI2 (resumen; el detalle está en el docstring de la réplica)
- **Detección:** bloques de N velas que se reinician con la sesión. Niveles hot = volumen ≥ mediana × M. Clusters
  de niveles hot con hueco ≤ gap. Score = suma (o densidad). Umbral = percentil de las **últimas 20 sesiones
  completas** en franjas de 15 min, hora de Chicago, con un mínimo de 20 muestras.
- **Orderblock (rojo):** desde la creación, en la primera vela en que el precio queda a max(k × altura, 8 ticks), es OB
  si el volumen operado dentro hasta ese momento es ≤ X %. Si no se aleja en 100 velas, es normal.
- **Racimo (violeta):** al nacer una zona, si ella y al menos (mín − 1) zonas de las últimas W velas entran
  **completas en una franja de A ticks**, todas se marcan. El racimo se amplía sólo si sigue entrando en A. Líneas en
  techo y piso del racimo, de L velas.
  - **Ojo, repinta:** en el chart la zona aparece violeta desde su inicio, pero en tiempo real se vuelve violeta
    recién al formarse el racimo. Toda medición usa la **vela de formación** (`racimo_bar` / `t0`).
- **Logger** (`LogPath`), líneas:
  - `B`: bloque;
  - `Z`: zona;
  - `O`: decisión de OB;
  - `R`: entrada de una zona a un racimo;
  - `C`: racimo creado o ampliado. Esta línea se agregó después: el log de 25t no la tiene.
- **Config de Nico (25t):** detección por defecto; OB 100 velas / **6 alturas** / 8 ticks / **4 %**; racimo
  **6 zonas / 500 velas / 30 ticks / líneas 5.000**.

### Paridad
| | archivo | resultado |
|---|---|---|
| 200t, defaults | `docs/parity/PARIDAD_AVOLZONEPOI2_MNQ1226_200T_20261007.md` | bloques 45.916, zonas 2.723 y OB 641: **100 %** |
| 25t, config de Nico | `docs/parity/PARIDAD_AVOLZONEPOI2_MNQ1226_25T_20261008.md` | bloques 367.455, zonas 21.701, OB 4.118 y racimo 1.190: **100 %** |

- Script: `tools/paridad_avolzonepoi2.py <log.csv>`, con env `ZP_SPEC` y `ZP_PARAMS` (JSON).
- Oráculos: `E:\EdgeLab\data\nt8_oracles\avolzonepoi_MNQ1226_200t_20260715_20260930.csv` y
  `avolzonepoi2_MNQ1226_25t_20260715_20260930.csv` (datos locales, no están en git).
- **El chart de Nico está en "Merge back adjusted":** hasta el roll (sesión del 14-09) las velas son del 09-26, con un
  offset de +299,75 puntos. El script de paridad reconstruye esa serie. **Las mediciones de research usan cada
  contrato con sus propios ticks**, sin merge.
- **Memoria:** la PC tiene 16 GB. Cargar dos contratos completos a la vez coincidió con un cuelgue. El script
  concatena sólo hora, precio y volumen.

## 2. Estudios realizados (todos en `docs/research/`)
| estudio | manifiesto | resultado | estado |
|---|---|---|---|
| AVZP2-REBOTE (primer regreso a zonas 200t) | `AVZP2_REBOTE_MANIFIESTO_20261007.md` | `AVZP2_REBOTE_RESULTADOS_20261007.md` | todas ≈ azar; AVZP2 = AVCL; rojas provisional |
| ↳ enmienda 1: nulo apareado OB | (en el mismo manifiesto) | (en el mismo acta) | rojas +2,5 pp, p 0,068: **sin efecto propio** |
| AVZP2-RACIMO (config de Nico, 25t) | `AVZP2_RACIMO_MANIFIESTO_20261008.md` | `AVZP2_RACIMO_RESULTADOS_20261008.md` | **compresión −7 % confirmada**; sin dirección |
| AVZP2-RACIMO-GRILLA (36 definiciones) | `AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md` | `AVZP2_RACIMO_GRILLA_RESULTADOS_20261008.md` | compresión 23/23; **O1 en ventanas largas, confirmado tras auditoría** |

Registro vivo: `HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md`, secciones AVZP2. Ledgers de multiplicidad (jsonl encadenado por
hash): `avzp2_rebote_20261007/trial_registry.jsonl` y `avzp2_racimo_20261008/trial_registry.jsonl`. JSON de cada
resultado en la carpeta del mismo nombre.

### Datos usados
- MNQ en 6 contratos. **Descubrimiento:** 09-25, 12-25, 03-26 y 06-26. **Confirmación:** 09-26 y 12-26.
- **Los contratos de confirmación ya se usaron** para:
  - el rebote de las rojas;
  - O5 en la celda base;
  - las celdas que pasaron en la grilla (O5, O1 y O2).

  **Ya no son vírgenes para la familia AVZP2.** Una confirmación nueva necesita otro instrumento (NQ, ES), años
  anteriores de MNQ o el holdout (≥ 2026-10-01, **que no se abre** sin protocolo).
- Holdout no leído.

## 3. Cómo se corre (pipeline)
1. **Etapa 1, en Kaggle**, porque son ticks completos. Los scripts son:
   - `tools/avzp2_rebote_stage1.py`;
   - `tools/avzp2_ob_stage1.py`;
   - `tools/avzp2_racimo_stage1.py`;
   - `tools/avzp2_racimo_grid_stage1.py`.

   Cada uno arma barras con `edgelab.bridge.bars`, footprint CSR NT8, corre `avolzonepoi2.run` y guarda un parquet
   por contrato con los eventos reales y pseudo.
2. **Construir y subir los kernels:**
   `python tools/build_avzp2_kernels.py <stage1.py> <prefijo> --out E:\kaggle_kernels --push`.
   - **El dataset de código de Kaggle no tiene `avolzonepoi2.py`;** el constructor lo incrusta en el script.
   - Kaggle falla a veces al arrancar (log vacío o `[]`): hay que relanzar sin cambios.
   - Hay un máximo de 5 sesiones de CPU simultáneas.
3. **Etapa 2, local** (liviana):
   - `python tools/avzp2_rebote_stage2.py <dir>` (con `AVZP2_PAT="*_avzp2ob.parquet"` para el nulo OB);
   - `python tools/avzp2_racimo_stage2.py <dir>`;
   - `python tools/avzp2_racimo_grid_stage2.py <dir>`.
4. **Estimador común:**
   - β real − pseudo en un modelo lineal de probabilidad / MCO;
   - FE absorbidos por proyecciones alternadas (`absorb`);
   - SE clusterizado por sesión;
   - MDE = 2,8 × SE;
   - Holm sobre las pruebas pre-registradas.

## 4. Lecciones de esta línea (no repetir)
- **El nulo tiene que aparear la característica obvia del evento.** Ejemplos:
  - el "alejamiento limpio" para las rojas;
  - la **ocupación previa** para los racimos;
  - la **magnitud de la tendencia y el momentum** para la dirección de salida.

  Sin eso, los efectos son de momentum o de consolidación, no del indicador.
- **Grupos y ventanas, sólo con el pasado** (memorias `grupo-comparacion-sin-lookahead` y
  `metrica-relativa-ventana-fuera-del-evento`).
- **El violeta del chart repinta.** Medir desde la vela de formación.
- **Semillas:** `hash()` de Python cambia por proceso.
  - La grilla ya usa `zlib.crc32`.
  - REBOTE, OB, RACIMO base y HFTV4 todavía usan `hash()`: sus números exactos no se reproducen, aunque las
    conclusiones no cambian.
  - Tarea abierta: "Fix non-deterministic hash() seeds".

## 5. NO MEDIDO (consolidado; lo detallado está en cada acta)
- **P&L de cualquier lógica.** Requiere STOP, manifiesto y OK de Nico. Los candidatos son:
  - **(a)** la salida de un racimo largo (≥ 1.000 velas, 30–45 ticks) a favor de la tendencia de 500 velas, con
    objetivos cortos, porque la compresión limita el recorrido: la excursión mediana después de salir es de ≈ 0,25
    alturas;
  - **(b)** una lógica de rango o reversión alrededor de cualquier racimo.
- O1 y la compresión en **otros instrumentos** (NQ, ES, MGC) y otras escalas: es la confirmación limpia pendiente.
- Ventanas > 1.000 velas y alturas > 45 ticks (el patrón de O1 es monótono creciente).
- Persistencia más allá de 200 velas, y las líneas del racimo en sesiones posteriores.
- La interacción O1 × compresión, y si el lado de la salida modera el seguimiento.
- Toques n-ésimos de zonas; otras configuraciones de detección (percentil, bloque, franja); composición del racimo.
- Reversión dentro de la franja (de borde a borde).

## 6. Siguiente paso recomendado
1. **Replicar O1 + compresión en NQ (o ES) 25t**, con las celdas 4–6 / 1.000 / 30–45 **congeladas**, una sola prueba
   por celda y Holm. Es información, no P&L, así que no requiere STOP. Sí requiere ticks del instrumento y el
   RESOLVER.
2. Si replica: **manifiesto de P&L** de la regla (a), con costos propios del instrumento, simulación tick a tick y
   STOP con OK de Nico antes de correr.
XEOF
cd /e/EdgeLab-gex; /e/EdgeLab/.venv/Scripts/python - <<'XEOF'
p="CLAUDE.md"; s=open(p,encoding="utf-8").read()
a="- `docs/research/HANDOFF_2026-08-21_ESTADO_COMPLETO.md` — **punto de entrada operativo vigente**.\n"
assert s.count(a)==1
s=s.replace(a,a+"- `docs/research/HANDOFF_AVZP2_RACIMOS_20261008.md` — familia aVolZonePOI2 (zonas, OB, racimos): indicador, paridad, estudios, pipeline Kaggle, NO MEDIDO y siguiente paso.\n")
open(p,"w",encoding="utf-8").write(s)
XEOF
git add docs/research/HANDOFF_AVZP2_RACIMOS_20261008.md tools/build_avzp2_kernels.py CLAUDE.md; git commit -qm "docs(avzp2): handoff completo de la familia aVolZonePOI2/racimos + constructor de kernels versionado; puntero en CLAUDE.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; git show --stat HEAD|tail -4; git push -q origin HEAD:foundation/f0b-compatibility-probe && echo pushed