# IPC-NIVEL × zonas HFT (MES) — resultado (2026-09-28)

**Estado: EXPLORATORIO, DISEÑO A REVISAR (Nico, 28/09: «desconfío de la forma en que lo mediste»).** No cuenta como
muerte del cruce IPC × HFT: se rediseña revisando en el visor qué zonas HFT cuentan como «cercanas», su vida y el puntaje.

**Resultado de esta versión: 0 de 16 sobreviven (BH q = 0,10).** Pedido prioritario de Nico. Código `tools/ipc_nivel_hft.py`, commit
`063c3be7`, árbol limpio. Reusa resultados y nulos de la formación (3.381 zonas) y del regreso virgen (2.214) y agrega el
rasgo: zonas HFTZonesNQPureV4 (SCALED_FUNNEL_V1, **paridad no validada**, usadas como están) activas as-of (disponibles
y hasta 500 velas después, la extensión del visor) a ≤ 20 t del nivel; S = Σ 1/(1 + d/2); niveles baja/media/alta por terciles.

| Estudio | Lado | baja | media | alta | alta − baja |
|---|---|---|---|---|---|
| formación | techo | −0,040 (p 0,018) | −0,005 | −0,008 | +0,032 [−0,011; +0,077] |
| formación | piso | +0,010 | +0,024 | +0,027 | +0,016 [−0,034; +0,069] |
| regreso | techo | +0,024 | −0,001 | −0,001 | −0,025 [−0,072; +0,025] |
| regreso | piso | +0,042 (p 0,042) | +0,014 | +0,039 (p 0,044) | −0,003 [−0,047; +0,038] |
(exceso = barre − p0; n por celda 313–601; MDE de alta − baja ≈ 0,12)

## Lectura
- La densidad y cercanía de zonas HFT **no separa** los niveles que se barren de los que resisten, en ningún estudio ni lado.
- Los niveles IPC tienen algo menos de HFT cerca que los pivotes de control (S medio 1,68 vs 1,85): descriptivo.
- Alcance: HFT sin paridad validada en MES, regla de vida fija de 500 velas, distancia ≤ 20 t, MES 25t Lucid. Un nulo acá
  puede deberse al detector HFT o a la regla de vida (no hay terminación por mitigación en los datos del bundle).

## Con el desgaste por comercio del visor (pedido de Nico, 28/09)
Réplica del MODO 2 de `index.html`: cada tick de la zona acumula vol_vela / ticks_de_la_vela de cada vela que lo cruza
después de la vela de origen y muere al llegar al umbral; la zona vive en su parte no consumida, as-of. Commit `371f081`
(ver `git log tools/ipc_nivel_hft.py`), árbol limpio. Artefactos `artifacts/ipc_nivel_hft_vol{35,100,500}/`.

| Umbral (contratos por tick) | Sobreviven | alta − baja: formación techo / piso · regreso techo / piso |
|---|---|---|
| **100 (principal, default del visor)** | **0/16** | +0,032 / +0,044 · −0,035 / +0,009 |
| 35 (estricto) | 0/16 | +0,034 / +0,031 · −0,020 / +0,012 |
| 500 (permisivo) | 0/16 | +0,037 / +0,020 · +0,006 / +0,039 |

Mismo veredicto con las tres reglas de desgaste: la densidad/cercanía HFT no discrimina. Lo único estable es un signo
chico y no significativo: en la formación, con más HFT cerca el nivel se barre algo más (+3 a +4 pp).
