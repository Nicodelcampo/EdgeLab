# PRERANGE-HFT: barrido del rango 08:12-09:12 NY con confluencia de zonas HFT

Estado: PRE-REGISTRO (2026-10-30). Sin corridas. Módulo: `edgelab/research/prerange_hft.py`.

## Hipótesis
El rango pre-market concentra stops en sus extremos. Si el barrido ocurre donde ya hubo rachas agresivas (zonas HFT cerca del borde), la
liquidez absorbida ahí debería hacer más probable el retorno que el mismo barrido sin zonas. Se prueba también la continuación.

## Definiciones (sólo pasado de la vela k)
- **Rango:** velas M1 con apertura en `[08:12,09:12)` NY (`sessions.YM_PRERANGE_*`, DST exacto), ≥ 50 de 60 velas, alto ≥ 4 ticks.
- **Barrido:** en `[09:12,16:00)` el máximo o mínimo excede el borde en ≥ 1 tick. Incluye 09:12-09:29, que OTR-930 excluye.
- **Gatillos:** `REINGRESO_CIERRE`, `EXCURSION_U1_25` (idénticos a OTR-930) y `CIERRE_FUERA` (sólo continuación). Uno por lado y gatillo en la
  sesión. Sin fade en el extremo: `RETORNO` no existe sobre `CIERRE_FUERA`.
- **S:** port de `tools/ipc_nivel_hft.py`. Σ 1/(1+d/2), d = distancia al borde barrido en ticks × `10 / ATR14_ticks(k)`, 0 dentro, sólo d ≤ 20.
  Zona activa si estuvo disponible en una vela cerrada ≤ k, hace ≤ 500 velas M1, y tiene ticks vivos (desgaste 35/100/500 acumulando
  `max(1, v/(H-L+1))` por tick cruzado, por vela posterior a la zona). `ATR_REF = 10` ticks sólo fija la unidad; los cortes salen de E0.
- **`dist_barrido`:** distancia escalada del extremo barrido a la zona viva más cercana; sin zonas, 1e6 (sólo entra en el nivel «todo»).

## Grilla: 7.776 celdas por canal
fuente_zonas 2 (HFT2, HFTNQ) × desgaste 3 × gatillo 3 × hay_zona 3 (no/sí/cualquiera) × S 3 (tercil bajo/alto/cualquiera) × dist_barrido 3 ×
ejecución 16 (dirección 2, entrada 2, objetivo 2, stop 2). **Control sin S:** hay_zona, S y dist_barrido en «cualquiera». Se repite en las
6 combinaciones de fuente × desgaste (son copias; se cuentan igual, lo conservador). Cortes de S y dist: cuantiles E0 por activo.

## E0 antes de DESC
`tools/kaggle_grilla/prerange_hft_e0_main.py` publica por activo, fuente y desgaste la fracción S>0, cuantiles y `con_30_disparos`.
Si la fracción es ≥ 95 % o ≤ 5 %, o los terciles colapsan porque más de 1/3 de los disparos tiene S=0, no se lanza DESC: se recalibra y se
registra de nuevo. Los cortes se calculan juntando las dos fuentes; una fuente mucho más densa desplaza los cortes de la otra (se lee en E0).

## Dependencias sin resolver
- Dataset `nicolasbuttaro/edgelab-zonas-hft` (almacén con `INDICADOR=HFT2` y `HFTNQ`, `INSTS=ES,NQ,YM`). No existe todavía; por eso las
  campañas quedan `activa: false`.
- `hftzones_nq` certificó paridad sobre ES con umbrales absolutos; en NQ y YM su densidad no está medida. `hftzones_universal` no se usa.
- En holdout HFT2 corre sólo sobre ticks sellados; su primera sesión no tiene calibración y no crea zonas.

## Refutación
Sin celdas nominadas FDR q ≤ 0,10 ni canasta con soporte; o el control sin S iguala a las celdas con S (la confluencia no agrega nada); o
falla integridad, OOS u holdout con potencia.
