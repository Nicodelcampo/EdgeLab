# Pre-registro: CVGAP-2 (04/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr; **no lanzado**: Nico pidió una iteración de revisión antes de la corrida). Referente
`docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2 exploratorio** (grilla masiva, `GUIA_GRILLA_MASIVA.md`). Código
`edgelab/research/cvgap2.py`; tests `tests/research/test_cvgap2.py`; certificado de causalidad en `config/causalidad_certificados.json`.

## La idea (Nico, 04/11)

Familia hija de CORREDOR-VOL-GAPS (`corredor_vol_gaps_20261028/SPEC_CORREDOR_VOL_GAPS.md`). El evento es el mismo, sin cambios:
1. Un impulso del corredor EMA 20/60.
2. La caja amarilla de volumen alto en su extremo.
3. La ruptura de la caja **sólo en la dirección del impulso**, con una excursión A.
4. El regreso a 3 puntos estructurales, con entrada en contra de la ruptura, hacia el 50 %, el 75 % o el origen del impulso.

## Qué cambia respecto del padre (lo aprendido del 02 al 04/11)

| Cambio | Por qué |
|---|---|
| Entrada **CONF**: una vela más que cierre a favor; además, a mercado (MERC) | Fue lo mejor de INTENTO-FALLIDO-HACIA |
| Stop **S_E1**: un tick más allá del extremo de la excursión; además, el colchón del padre (S_EXT) | Riesgo atado a la geometría de la trampa, medido en R |
| TP **2R**, además de MID50 / MID25 / ORIG100 (sin los rellenos mínimos artificiales del padre: si el nivel no queda delante, no se opera) | Atlas en R del 02/11 |
| Variables **dur_ida** y **dur_reg** (velas M1, terciles causales) | Pregunta de Nico: ¿la duración de las piernas cambia el resultado? |
| Salida forzada por noticias tier1 y sin entradas a ±5 min de un dato (`intento_fallido.lineas_salida`, sólo de tiempo) | Regla del 25/10, que el padre no tenía |
| Ejes de gaps fijos en «cualquiera» | Nunca separaron en DESC; más potencia por celda |
| Más activos: NQ, CFD-NQ, ES, CFD-ES, YM, GC, USA30, XAU | Diversificar con la misma lógica |

El tope de 240 velas (4 h) y el cierre a fin de sesión ya los aplicaba el simulador al padre: no cambian.

**Definición de las duraciones (sólo velas ≤ decisión):**
- `dur_reg` cuenta las velas desde la última que tocó el extremo hasta la decisión.
- `dur_ida` cuenta las velas desde la última vela anterior al extremo que estuvo del lado de la caja respecto del ancla (POC o borde
  del área de valor) hasta el extremo. Si ninguna vela de la sesión cumple eso, se cuenta desde el inicio de la sesión.

## Grilla

- Ejes:
  - escala 2 (50T, M1);
  - W 2;
  - pct_vol 2 (`ge`);
  - exc_amarilla 3 (`ge`, 1/2/4);
  - punto_regreso 3;
  - tamano_impulso 3;
  - dur_ida 3;
  - dur_reg 3;
  - vwap 3;
  - hora 5.
- Ejecuciones: 2 × 2 × 4 = 16.
- Total: **466.560 celdas por canal**, un 50 % del padre.

## Campañas, linaje y multiplicidad

| Campaña | Sensor → ejecución | Familia (padre) | DESC | Réplica |
|---|---|---|---|---|
| CVGAP2-NQ | NQ → NQ | CVGAP2_NQ (CORREDOR_VOL_GAPS_NQ) | 2025-08-05 → 2026-03-31 | abr–sep 2026 |
| CVGAP2-CFD-NQ | USATECH → NQ | CVGAP2_CFD_NQ (CORREDOR_VOL_GAPS_CFD_NQ) | idem | idem |
| CVGAP2-ES | ES → ES | CVGAP2_ES (CORREDOR_VOL_GAPS_ES) | idem | idem |
| CVGAP2-CFD-ES | USA500 → ES | CVGAP2_CFD_ES (CORREDOR_VOL_GAPS_CFD_ES) | idem | idem |
| CVGAP2-YM | YM → YM | CVGAP2_YM (CORREDOR_VOL_GAPS_ES) | idem | idem |
| CVGAP2-GC | GC → GC | CVGAP2_GC (CORREDOR_VOL_GAPS_NQ) | idem | idem |
| CVGAP2-USA30 | USA30 → USA30 | CVGAP2_USA30 (CORREDOR_VOL_GAPS_ES) | 2024-01-02 → 2026-03-31 | idem |
| CVGAP2-XAU | XAU → XAU | CVGAP2_XAU (CORREDOR_VOL_GAPS_NQ) | idem | idem |

Cada familia hereda la multiplicidad **bruta** del padre (`LINAJES.jsonl`). Las pruebas se cuentan en el contador global al lanzar
(`TrialRegistry.ensure` del embudo). Embudo en R con cola t, holdout sellado desde 2026-10-01 con N fijo 150.

Para los spot y CFD se usa la fricción del futuro como proxy declarado.

## Cómo podría refutarse

La familia se refuta en cualquiera de estos casos:
- ninguna celda nominada por FDR q 0,10 y ninguna pista que replique;
- dur_ida y dur_reg no separan;
- CONF no mejora a MERC;
- la media neta en el holdout es ≤ 0.

Un nulo sin potencia no cierra la familia.

## Justificación económica

La ruptura tardía de una caja con absorción alta, en la dirección de un impulso ya maduro, barre los stops de los que entran tarde.
Si el precio vuelve a la caja y lo confirma, los que rompieron quedan atrapados y el impulso se rellena. El stop detrás del extremo de
la excursión invalida exactamente esa lectura.

## Iteración de revisión antes de lanzar (04/11, pedido de Nico)

Correcciones hechas antes de la primera corrida. Nada se midió sobre retornos.

1. **Stop con CONF:** la vela de confirmación puede marcar un extremo nuevo. Ahora el stop estructural va detrás del extremo vigente al
   decidir (incluye la vela k+1). Antes podía quedar dentro del rango ya recorrido.
2. **Duraciones que cruzan la sesión:** el padre no reinicia la caja amarilla al cambiar de sesión. Con la búsqueda limitada a la
   sesión se perdía ~7 % de los disparos (33 de 453 en sintético), con el extremo en la sesión anterior. La búsqueda ahora cruza la
   sesión, acotada a 2.880 velas M1 hacia atrás, y la población queda idéntica a la del padre (453 de 453).
3. **Riesgo:** en sintético ninguna operación tiene un R menor de 4 ticks (mediana de unos 185 ticks), así que no hace falta un piso.
   La fricción no domina el R.

**Verificación:** tests en verde, certificado de causalidad sin errores y ninguna de las 16 ejecuciones equivale a otra.
