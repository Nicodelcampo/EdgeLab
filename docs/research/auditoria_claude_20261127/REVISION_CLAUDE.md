# Revisión de Claude del trabajo de Antigravity del 2026-11-27 (auditoría del PR, CRIPTO-PIT v2/v3, frentes ortogonales, supercartera v2)

Estado: VIGENTE — revisión verificada contra el código, las series publicadas y los datos locales. Descriptiva: no suma pruebas ni mira
el holdout. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Documentos revisados:
- `HANDOFF_ANTIGRAVITY_2026-11-27.md`;
- esta carpeta;
- `cripto_pit_v3_20261127/`, `frentes_ortogonales_20261127/` y `supercartera_v2_20261127/`.

## 1. Verificado y aceptado
| Afirmación | Verificación | Lectura |
|---|---|---|
| Custodia: nada de HOLDOUT A5 ni desde 2026-10-01 | Las 4 series publicadas sólo tienen valores en DESC y REP; la última fecha es 2026-08-30 | Correcta |
| El XSMOM de cripto repartía peso residual en monedas planas | `w.sub(w.where(E1).mean(axis=1))` resta la media, con ceros incluidos, a todas las elegibles | Correcta. El defecto viene de la regla original de la auditoría del 26-nov (`cartera_cripto_binance.py`, `w_xs.sub(w_xs.mean(axis=1))`); `cripto_pit.py` la congeló tal cual, como declaraba su pre-registro. Se corrige hacia adelante |
| Los futuros continuos `=F` de Yahoo no sirven (empalmes sin ajuste) | Es la corrida propia de Antigravity (`futuros_no_equity_v2.py`, 22 `=F`) | Correcta. No afecta a `F-TENDENCIA-NO-EQUITY-MENSUAL`, que usó 14 ETF con `adjclose` (sin empalmes) |
| Carril 2 decae después de 2018 | Coincide con `canasta_amplia_20261127/RESULTADO.md` §3 (DESC desde 2019, SR 0,19–0,40) | Correcta |
| K27 por familia sola no llega a potencia 0,8 con 18–22 meses | Aritmética correcta | Por eso la hipótesis pasó a nivel canasta. Cambiar K27 sigue siendo decisión de Nico |
| FundedSync O con 1 MNQ empeora las carteras | 36 operaciones, −3.041 USD | Correcta, y se informó |
| CSCV: promediar le gana a elegir la mejor regla | Carril 2: mejor regla 0,32 fuera de muestra contra 1/N 0,85 | Correcta; es la misma lectura que `F-N-DILUYE-SOLO-CON-MECANISMOS-DISTINTOS` |

## 2. Objeciones

1. **Global_VolComp no es ortogonal a Carril 2: es la misma señal.**
   - C2_VZ y C2_EVRP disparan con el VIX de EE. UU.; acá se aplican a DAX, EuroStoxx, FTSE, Nikkei y oro.
   - Correlación mensual con C2_VZ + C2_EVRP de ES/NQ: **0,48** en 2014–2026 y 0,37 en 2021–2026.
   - El 0,13 informado se mide contra `Carril2_Sell16`, que excluye a VZ y EVRP a propósito.
   - Sirve como evidencia de que el mecanismo se transfiere a otros índices. No es un frente independiente, y el «pozo sin CME» no
     puede tratarlo como tal al calcular potencia.
2. **La evidencia propia de Global_VolComp es débil.**
   - En los 109 meses completos de DESC + REP: SR 0,45, **t 1,37**. El t 2,39 citado es la subventana 2021–2026, elegida después de
     mirar.
   - El costo de 8 pb no sale de `edgelab/costos.py`. NKD y GC tienen componente canónico; DAX, EuroStoxx y FTSE no.
   - A 16 pb, EuroStoxx y FTSE dan negativo.
   - Potencia de su propio HOLDOUT A5: 0,11–0,20.
3. **La REP de cripto ya no está limpia.** «Limpio» en estos documentos quiere decir «sin el sesgo del vendedor CME». No quiere decir
   sin iteración: v1 (pre-registrada), v2 (registro posterior) y v3 se diseñaron sobre los mismos 51 meses con la REP a la vista.
   - Entre v1 y v2 cambiaron la ventana (14 → 21 días), las patas (2 → 4), el rebalanceo escalonado y el filtro de universo.
   - La REP 1,72 de la canasta v3 es exploratoria; la prueba limpia de cripto son sus 18 meses de HOLDOUT A5.
   - `Cripto_v3_XSMOM_BAB` (SR 1,47) saca una pata después de ver el resultado. Antigravity lo marca para pre-registrar; hasta
     entonces no es evidencia.
4. **`HRP_Weekly` es la misma cartera que EQ.** Da pesos 0,25 exactos y cifras idénticas, así que de las 4 pruebas contadas de
   SUPERCARTERA-V2 dos son duplicados. Contar de más es conservador; lo que no vale es leerla como una ponderación distinta.
5. **La REP 3,38 de `Super_v2_NoCME` no agrega evidencia.** Viene de la REP de Carril 2 en 2021–2026 (3,07), que es la misma REP ya
   informada en `canasta_amplia`, más la REP iterada de cripto.
6. **Procedimiento.**
   - Las corridas v3, frentes y supercartera llaman a `exigir_contada`, así que se contaron antes de correr; el commit del registro
     llegó junto con los resultados.
   - El CI quedaba en rojo por tres razones:
     - dos funciones copiadas: `stats_monthly_10vol` y el guardado de gráficos;
     - 8 herramientas fuera del catálogo;
     - RESULTADO sin «Diagnóstico de grilla:» ni «Episodios:».
   - Faltaba `Estado:` en dos documentos, y había enlaces `file:///C:/…` locales.
   - Lo arreglé en este commit: importé las funciones originales, regeneré el catálogo y agregué las líneas, el `Estado:` y los
     enlaces relativos.

## 3. Qué queda en pie, neto

| Frente | Evidencia | Prueba limpia pendiente |
|---|---|---|
| Carril 2 sellada (16) | REP t 2,01 (sellada) / 3,11 (completa); débil desde 2019 | HOLDOUT A5, 63 meses (potencia 0,25 / 0,39 / 0,63) |
| Cripto XSMOM L/S + BAB (beta ≈ 0) | DESC + REP t 2,2–2,7, iterado sobre la misma muestra | HOLDOUT A5, 18 meses (potencia 0,19 / 0,29 / 0,47) |
| Global_VolComp (transferencia de VZ/EVRP) | t 1,37 en la muestra completa, correlación 0,48 con su versión de EE. UU. | HOLDOUT A5, 38 meses (potencia 0,11–0,20) |

- El pozo conjunto con 63 meses dinámicos da potencia 0,54 con el efecto × 0,7 (`supercartera_v2` §3). Supone a Global_VolComp como
  independiente; con su correlación real queda por debajo.
- Ninguna combinación llega a 0,8. **K27 sigue bloqueando cualquier apertura**, y levantarlo es decisión de Nico.
- Si Nico lo levanta, la candidata más defendible sigue siendo una sola apertura con miembros congelados antes:
  - Carril 2 sellada;
  - cripto v3 según la regla del pre-registro (no XSMOM_BAB);
  - Global_VolComp como miembro con su peso, sin contarlo como un frente aparte.

Aporte al referente: separa lo que suma información nueva (cripto beta-neutral, con prueba limpia de 18 meses pendiente) de lo que es la
misma señal medida en otros activos (Global_VolComp con correlación 0,48). Deja el CI de la rama en condiciones y explicita que la
potencia del pozo está sobreestimada.
