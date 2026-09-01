# PENDIENTE — puntero al board canónico

> **RECONCILIADO EL 2026-09-01.** Este archivo de la rama de auditoría ya no contiene
> un board independiente. La versión anterior de esta rama (blob `f924a60d`) fue una
> reescritura condensada incorrectamente presentada como restauración del original.

## Fuente canónica

El board largo canónico está en:

- rama `research/avolcluster-nq-parity-oracle-20260901`;
- archivo `PENDIENTE.md`;
- blob git `252215c11b89252400919d16464454bcff7306bb`;
- 112.595 bytes;
- entradas P-01…P-59.

Ese blob coincide con `foundation/f0b-compatibility-probe:PENDIENTE.md`. Su revisión
anterior verificable es `e2e0cf40d4606fadb836878bbed304e4f0c40ea0` (108.777 bytes,
P-01…P-57), conservada en
`research/bt2a-nq-gate1-nrand-capacity-t2-20260830`.

**Regla:** no agregar entradas en este puntero. Toda nueva entrada se asienta sobre el
board canónico, usando el próximo número libre. Ante colisión, conserva el número la
entrada con registro verificable más temprano.

## Reconciliación de entradas posteriores

- Las «tres palancas de ejecución liviana» pasan de la numeración incorrecta P-58 a
  **P-60**.
- «ML/LightGBM como generador de hipótesis» pasa de P-59 a **P-61**.
- Las P-56…P-59 canónicas conservan sus números: fuente L2 ES en holdout; conversor
  NRD→CSV; paridad aVolClusterPOI 60t; y lotes L1/L2 de GC subidos a Notion.

Detalle y cuarentena: `docs/audits/PENDIENTE_RECONCILIACION_2026-09-01.md`.
