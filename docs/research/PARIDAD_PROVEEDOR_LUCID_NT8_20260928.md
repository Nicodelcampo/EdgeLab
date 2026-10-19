# Paridad de proveedor Lucid (research-v2) ↔ NinjaTrader, jul-2025 → jun-2026 — resultado target-free (2026-09-28)

**Herramienta:** `tools/paridad_proveedor_lucid_nt8.py`. **Datos:** research-v2 (Lucid) contra el solape NT8 canonizado (`tools/build_es_ext_2026q3.py ES|NQ --solape`, catálogos `docs/research/contract_regimes/{ES,NQ}_nt8_overlap_sessions_catalog.json`). Artefactos: `artifacts/paridad_proveedor/`. No mira retornos.

| | ES | NQ |
|---|---|---|
| Sesiones comunes | 232 | 184 |
| Mismo contrato elegido | 100 % | 98,4 % |
| Razón ticks / volumen (mediana) | 1,000 / 1,000 | 1,000 / 1,000 |
| Minutos con máximo idéntico (mediana; mínimo) | 100 %; 99,8 % | 100 %; — |
| Correlación de volumen por minuto (mediana) | 1,000 | 1,000 |
| Sesiones con cantidad de ticks distinta | 67 de 232 | 111 de 184 |
| Cierres de velas de 25t idénticos (mediana) | 100 % | **53 %** |

**Lectura:**
- **Es el mismo feed.** Precio y volumen por minuto coinciden prácticamente siempre.
- Las diferencias son **pocos ticks sueltos** por sesión (1–20, repartidos) y, a veces, **huecos de un proveedor** (p. ej. ES 23-dic-2025: Lucid sin ticks entre 04:33 y ~04:40 UTC que NT8 sí tiene).
- **Consecuencia para velas de ticks:** un solo tick de diferencia corre todas las fronteras de 25t siguientes, así que las velas de 25t dejan de ser idénticas aunque el mercado sea el mismo (NQ: mediana 53 %). Para velas de tiempo y por minuto, los proveedores son intercambiables.
- **Regla propuesta (a confirmar con el auditor, entradas 053/054):** una familia que usa velas de ticks corre **de punta a punta con un solo proveedor**; los resultados deberían ser estadísticamente equivalentes entre proveedores, pero no vela a vela. Como NT8 cubre jul-2025 → sep-2026 y coincide con el L2, es el candidato natural a proveedor único.
