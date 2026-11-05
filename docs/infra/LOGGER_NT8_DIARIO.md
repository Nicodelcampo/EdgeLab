# Logger diario de NT8 → dataset sellado de Kaggle

Estado: VIGENTE. Fecha: 2026-11-01. Pedido de Nico: «para los ticks tengo NT8» y «el SV1 tiene que usar Kaggle».
Es la pieza que faltaba para que la cartera viva mida en papel con datos nuevos (`docs/CARTERA_VIVA.md` §8.1). También es la ruta
sellada que pide la canasta de 7 (`docs/research/canasta_7_20261030/DECISION_CONTEO_20261101.md`).

## Cómo fluye
1. **NT8, en tu PC, todo el día.** El indicador `EdgeLabLiveTickLogger` graba cada trade en vivo con el bid/ask vigente en
   `C:\EdgeLab\tick_live\<CONTRATO>\<yyyymmdd>.Last.utc.txt`, con el mismo formato que EdgeLabTickHistory.
2. **Programador de tareas de Windows, una vez por día a las 17:15 ET.** `tools/nt8_sellado_diario.py diario`:
   - arma cada sesión CME cerrada en `C:\EdgeLab\sellado\<INST>_<yyyymmdd>_ticks.parquet`;
   - publica una versión nueva de `nicolasbuttaro/edgelab-holdout-sellado`.
3. **SV1, a las 17:12 ET.** La cartera corre en Kaggle (`config/cartera/cartera.json`, `"motor": "kaggle"`) y lee ese dataset. Si
   la versión del día todavía no se procesó, la sesión entra al día siguiente: las fichas suman todas las sesiones pendientes, no se
   pierde ninguna. El plan de ese día usa los datos hasta la sesión anterior.

## Instalación (una vez)
1. **Indicador.**
   - Copiá `nt8_tools/EdgeLabLiveTickLogger.cs` a `Documentos\NinjaTrader 8\bin\Custom\Indicators\`.
   - Compilá: NinjaScript Editor → F5.
2. **Un gráfico por instrumento**, con el contrato del frente: NQ 12-26, ES 12-26, YM 12-26 y GC 12-26.
   - Cualquier período sirve; un gráfico de 1 minuto alcanza.
   - Agregá el indicador "EdgeLab Live Tick Logger" con `Root = C:\EdgeLab\tick_live`.
   - Guardá el workspace, para que se reabra solo.
   - NT8 tiene que quedar abierto y conectado al feed durante la sesión. Lo que se graba es lo que llega en vivo.
3. **Python en la PC**, desde el clon del repo: `pip install pandas pyarrow kaggle`. La credencial de Kaggle de `nicolasbuttaro` va
   en `%USERPROFILE%\.kaggle\kaggle.json`.
4. **Espejo del dataset sellado:**
   `python tools\nt8_sellado_diario.py iniciar --espejo C:\EdgeLab\sellado`
   Baja la versión actual del dataset (ES y NQ hasta el 26 de octubre, más los spots de Dukascopy). Las versiones nuevas se publican
   desde ese espejo, así que nunca se pierde lo que ya estaba.
5. **Tarea diaria** (Programador de tareas → Crear tarea → todos los días a las 16:15 hora de Chicago, o sea 17:15 ET / 19:15 AR):
   `python C:\...\EdgeLab\tools\nt8_sellado_diario.py diario --espejo C:\EdgeLab\sellado --fuente C:\EdgeLab\tick_live --fuente C:\EdgeLab\tick_history`

## Rellenar el hueco del 27 al 31 de octubre (una vez)
El dataset tiene sesiones hasta el 26 de octubre y el logger graba desde que lo prendés. Para lo que quedó en el medio:
1. Exportá NQ, ES, YM y GC del 2026-10-27 en adelante a `C:\EdgeLab\tick_history\<CONTRATO>\` en formato `.Last.utc.txt`. Hay
   dos caminos:
   - el mismo método con el que armaste `ES_12-26` y `NQ_12-26` de octubre;
   - `EdgeLabTickHistory` o `EdgeLabTickLogger`. **Ojo:** los dos cortan en la frontera del holdout a propósito (fail-closed). Para
     esta exportación hay que sacar ese corte, porque estos datos van sólo al dataset SELLADO.
   Para YM y GC hacen falta también las sesiones desde el 1 de octubre, que el dataset todavía no tiene.
2. `convertir` las toma con la segunda `--fuente`. Las sesiones que ya están en el espejo no se tocan.

## Reglas
- **No se mira nada.** Este circuito mueve ticks y no calcula ningún resultado. El dataset sellado lo leen sólo kernels con acta: el
  pre-registro de cada ficha de la cartera, o el protocolo de apertura.
- **Sesión incompleta = no se sube.** Si NT8 se cayó a media sesión, el conversor la marca `INCOMPLETA_NO_SUBIDA` en
  `SELLADO_DIARIO.jsonl`. Se rellena con EdgeLabTickHistory, o se acepta con `--forzar <yyyymmdd>` en un feriado con cierre temprano.
- **El roll se resuelve solo.** Con dos contratos el mismo día, entra el de más volumen. El día del roll hay que agregar el contrato
  nuevo en NT8 (por ejemplo NQ 03-27 a mediados de diciembre).
- **Tamaño.** Kaggle sube la carpeta completa en cada versión, unos 20 a 30 MB por día con 4 instrumentos. Si con los meses la subida
  se hace lenta, se parte por trimestre: dataset nuevo y una línea en la config. Eso no cambia ninguna regla.

## Archivos
- `nt8_tools/EdgeLabLiveTickLogger.cs`: el indicador, en CRLF (`tools/check_nt8_cs.py`).
- `tools/nt8_sellado_diario.py`: el conversor y el subidor. Reutiliza `build_nt8_ticks.parsear_lote` y `fuentes_ticks._td`.
- `tests/research/test_nt8_sellado_diario.py`: sesión desde dos días UTC, sesión incompleta, roll, inmutabilidad y lectura por el
  lector sellado.
- Lado Kaggle:
  - `tools/kaggle_grilla/embudo_main.py` lee todos los archivos `<INST>_*ticks.parquet` del dataset;
  - `fuentes_ticks._leer_sellado_futuro` prioriza el diario cuando un día está en dos archivos.
