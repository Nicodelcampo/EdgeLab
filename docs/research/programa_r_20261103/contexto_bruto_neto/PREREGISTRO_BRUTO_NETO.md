# Pre-registro: atlas de contexto en bruto y en neto (04/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF3 diagnóstico**.
Motivo: `REVISION_ATLAS_CONTEXTO_FRICCION_20261104.md` (la fricción en R explica parte de los efectos del atlas).

## Qué se corre

- **Corridas:** las mismas etapas MARGINALES del atlas de Gemini (`tools/atlas_contexto_r.py lanzar`, 106 campañas en R × DESC y
  réplica). Calentamiento de 40 días y código de `grilla_generica.correr` con la integración del 04/11. Cada corrida guarda, en la misma
  pasada, `marginales_globales` (neto) y `marginales_globales_bruto` (`pnl / riesgo`, sin fricción).
- **Salida:** `docs/research/programa_r_20261103/contexto_bruto_neto/` (`ATLAS_SALIDA`). Análisis con
  `ATLAS_CLAVE=marginales_globales` y con `ATLAS_CLAVE=marginales_globales_bruto`: el mismo meta-análisis de DerSimonian-Laird por
  estrato.

## Qué se decide (no se elige nada nuevo)

Para cada efecto que el atlas confirmó, se clasifica según el bruto en las dos ventanas (DESC y réplica). Los efectos son S3, T3/T1,
`ctx_atr_rel` bajo/alto, `ctx_vol_rel` bajo/alto, `ctx_hora_ny=ny_manana_0930_12`, `veto_muro` y `veto_huida` (continuación).

| Clase | Criterio en bruto |
|---|---|
| **CONTEXTO** | mismo signo y efecto ≥ 50 % del neto en las dos ventanas |
| **FRICCIÓN** | efecto < 25 % del neto o cambio de signo en alguna ventana |
| **MIXTO** | el resto |

Un efecto FRICCIÓN se reemplaza por la discusión de costo (piso de riesgo, `RESULTADO_PISO_RIESGO_20261104.md`) y no se usa como
filtro de contexto. El imán sigue congelado para validar desde noviembre de 2026, cualquiera sea su clase.

**Cómo podría refutarse la revisión:** todos los efectos dan CONTEXTO, es decir que la fricción no explica nada.

Contador global: `programa_r/contexto_bruto_neto/20261104`. Son 11 efectos re-clasificados, no pruebas nuevas de selección; se
registran igual.
