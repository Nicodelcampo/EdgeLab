# Auditoría K48: variables de contexto contra la hora de entrada (punto 3, 2026-11-18)

Estado: RESULTADO — **las pistas vivas no tienen fuga. La fuga estaba en un atlas descriptivo y ya está bloqueada.**
- **Pedido de Nico:** punto 3 de «vamos a hacer los 4, uno por vez».
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Auditoría sin desenlaces nuevos (no cuenta
  pruebas).

## Método
- **Cada uso de `noche`, `gap`, `orb15`, `vol20` y `tend60`** en `tools/` y `edgelab/research/` se comparó con la hora REAL de entrada
  de cada regla o módulo que lo usó (`papel_regimen.horas_de_sesion`).
- **Horas de conocimiento** (desde las 18:00 NY de la sesión):
  - vol20, tend60 y noche anterior: 0 h;
  - noche hasta las 09:00: 15 h; noche hasta las 09:30 y gap: 15,5 h;
  - orb15: 15,75 h.

## Resultado
| Uso | Reglas | Entrada | Veredicto |
|---|---|---|---|
| `papel_regimen` (noche hasta 09:00) | ASIA-NQ | 18:00–09:00 | **FUGA** (cerrada hoy, K48: `asia_noche_20261118`) |
| `papel_regimen` | OTR930-NQ | ≥ 09:30 | causal |
| `fundedsync_mecanismos.contexto` (noche/gap 09:30, orb15 09:45) | T, R, Z, PREAPERTURA-NQ/ES, SOM, F, P, Q, V, C | ≥ 09:31 (orb15 ≥ 09:45 se enmascara por operación) | causal |
| ídem | A1, A20, E, S, O (de noche); orb15 en N, W, Z, R | antes de las 09:30 / 09:45 | **FUGA en el atlas de mecanismos** |
| veto de noche en `franklin_seguimiento` | PREAPERTURA-ES | 09:31 | causal |
| `mejora_som` / `mejora_t` | SOM (09:35) / T (≥ 10:00) | — | causal |
| predictores del día de tendencia (`fundedsync_tanda2`) | E0 a las 10:30 y 12:00 | — | causal |

## Consecuencias
- **Atlas de FundedSync:** vuelto a correr con la guarda `CONOCIDA_EJE`. Las elegidas en A bajan de 19 a 12 (las 7 que salen eran la
  fuga) y siguen siendo 0 las que pasan en B. Se retira la propuesta «A20/A1 con gap alto».
- **Pistas vivas afectadas:** ninguna. F-NOCHE-MOVIDA-Z-Y-PREAPERTURA-ES es causal: Z entra a las 09:32 y PREAPERTURA a las 09:31.
- **Guardas:** `papel_regimen.CONOCIDA_H` (mapa y encendido) y `fundedsync_mecanismos.CONOCIDA_EJE` (atlas). La regla general quedó
  en ERRORES §E6: la hora de conocimiento se compara con la de cada módulo.
- **Datos:** el M1 del CFD que usa el atlas se obtiene ahora con `tools/datos.py traer M1DK <archivo>` (copia parcial verificada).
