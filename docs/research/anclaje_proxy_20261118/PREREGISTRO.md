# Proxy de gamma desde 2006 («anclaje») y el filtro de exclusión en T + Franklin + SOM: diseño completo antes de tocar retornos (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — commiteado y contado antes de correr.
- **Pedido de Nico:** «¿por qué forward teniendo tantos datos? La idea es no necesitar forward» y «estandarizá la manera de evitar el
  error y sí, adelante con eso».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. **Familia:** `ANCLAJE_PROXY` (linaje:
  `DIA_TENDENCIA_A5`, `FUNDEDSYNC`, `FRANKLIN`, `SOM`).
- **Etapas:** fase 0 sin retornos de estrategia; fase 1 EF2 (DESC 2011+); fase 2 EF5 (2006-01 → 2011-10, una lectura).
- **Herramienta:** `tools/anclaje_proxy.py`.

Antecedentes: `docs/research/gex_tendencia_20261118/RESULTADO.md`.
- **Filtro de GEX:** con gamma alta, T, Franklin y SOM en NQ/ES/YM pierden (canasta −0,5 R/día en DESC y en REP + HOLDOUT). Confirmación
  significativa al nivel LORD, pero 53 % de años: NO_CONFIRMADA.
- **Datos limpios:** se agotaron porque GEX existe desde 2011 (K49).
- **Datos que sí hay desde 2006:** M1 de futuros, VIX/VXN/VXD (`cboe_volatility_daily.parquet`, llegó hoy al dataset M1NT8) y el
  calendario de eventos.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6.
- **K49:** cadena entera pre-registrada antes de mirar, y potencia en días con `a5.exigir_potencia` antes de la lectura.
- **K48:** todo del cierre de d−1.
- **K35:** R por regla.

Potencia previa: se calcula en la fase 1 con `a5.plan_lectura` (mitad del efecto de DESC por día, nivel LORD de la familia, días de
2006-01 → 2011-10). **Si es < 0,8, la fase 2 no se corre** y queda escrito.

## 1. Justificación económica
- **Por qué funcionaría un proxy:** la gamma de los dealers no se observa antes de 2011, pero sus huellas sí. Con gamma alta el
  mercado revierte dentro del día (variance ratio < 1, autocorrelación negativa) y la volatilidad implícita suele estar baja y
  estable.
- **Qué se prueba:** si un proxy reproduce a GEX desde 2011, sirve para probar el filtro en los años anteriores, que ningún cruce con
  la gamma tocó.

## 2. Fase 0 (sin retornos de estrategia): elegir el proxy
**Candidatos** (todos del cierre de d−1):
- `vix_ivp`: percentil del VIX contra 252 días;
- `vix_z20`: (VIX − media de 20) / desvío de 20;
- `vr20`: variance ratio intradía de NQ RTH, var(retornos de 30 min) / (30 · var(retornos de 1 min)), en las 20 sesiones previas;
- `ac20`: autocorrelación de retornos de 5 min de NQ RTH en las 20 sesiones previas.

**Elección:** el de mayor |Spearman| con `g_rank250` por día, 2011-11 → 2025-07. GEX no es un desenlace de estrategia.
- «Anclaje alto» es el lado del proxy que acompaña a la gamma alta.
- **Corte:** tercil alto del proxy en 2011-11 → 2025-07, congelado.
- **Exigencia:** |Spearman| ≥ 0,3. Si ningún candidato llega, se termina sin mirar retornos.

## 3. Fase 1 (EF2, datos ya mirados: meses DESC de 2011-11 → 2025-07)
- **Canasta:** T + Franklin + SOM (NQ/ES/YM; Franklin NQ/ES), R neto por día.
- **Medida:** anclaje alto − resto. Da el efecto y el desvío por día para el plan de potencia.
- **Plan:** `a5.plan_lectura(efecto, n = días de 2006-01 → 2011-10 con operaciones)`; `a5.exigir_potencia` decide si hay fase 2.

## 4. Fase 2 (EF5, una lectura): 2006-01-01 → 2011-10-31
- **Datos:** todos los meses; el cruce de estas reglas con la gamma o el proxy nunca se calculó en esos años. **Declaración:** el R
  agregado de esas reglas en esos años sí se miró (prueba de «años limpios» de M1 largo).
- **Estadístico:** contraste anclaje alto − resto de la canasta, bootstrap por día. H1: < 0.
- **α:** nivel LORD++ reservado (`ANCLAJE_PROXY::CONF_20261118`).
- **CONFIRMADA:** p ≤ nivel y ≥ 60 % de los años con contraste < 0.
- **REFUTADA:** contraste ≥ 0, o cota inferior unilateral al 95 % > −0,1 R/día.
- **Económico:** canasta sin anclaje alto R/día > 0.

## 5. Cómo podría refutarse
- **Ningún proxy correlaciona ≥ 0,3 con GEX:** la gamma no deja huella observable.
- **El proxy no reproduce el efecto en 2006–2011 con potencia:** el filtro de gamma es un fenómeno de 2011+ o de GEX en sí.

## 6. Contador
- **Contador:** 2 pruebas (fase 1 exploratoria y fase 2 confirmatoria).
  `tools/registro_global.py preregistrado ANCLAJE-PROXY ANCLAJE_PROXY 2 docs/research/anclaje_proxy_20261118/PREREGISTRO.md`,
  y el commit del registro.
