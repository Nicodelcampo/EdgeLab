# Filtro de horario CME sobre las cintas — 53 ticks fuera del marco semanal

- **Fecha:** 2026-08-24 · **Rama:** `foundation/f0b-compatibility-probe` · **Base:** `f8a1848`
- **Decisión de Nico:** *«filtralos»* (2026-08-24)
- **Firewall:** outcomes `false` · sin cambios a `.cs`, harness ni spec

---

## 1. Qué se filtra

Sólo el **marco semanal**: domingo 17:00 CT → viernes 16:00 CT. Nada más.

La base de ticks de NT8 exporta `.Last.txt` sin aplicar plantilla de sesión, así que trae
prints aislados con el exchange cerrado. El chart de NT8 **sí** los excluye — mostraba
`0` en esas fechas. Por eso filtrarlos **acerca** la cinta al oráculo, no la aleja: mejora
paridad y validez del censo a la vez.

## 2. Censo completo — 53 ticks en 5 contratos

| contrato | ticks fuera | fechas afectadas |
|---|---:|---|
| GC 12-25 | 30 | 12 |
| GC 02-26 | 20 | 10 |
| GC 04-26 | 2 | 2 |
| GC 06-26 | **0** | — |
| GC 08-26 | **0** | — |
| **total** | **53** | |

Todos en domingo antes de las 17:00 CT o en sábado. El más tardío, un sábado 21:54 CT.

**Impacto en el universo de 152 sesiones: ~11 ticks en 5 sesiones.** El resto cae en
`GC 12-25`, que queda fuera de la cadena rule-based.

## 3. Qué NO se filtra, a propósito

**Los cierres anticipados de feriado se conservan.** En Thanksgiving 2025 la cinta llega
hasta las 13:29:56 CT —el cierre oficial de metales— y el chart de NT8 corta a las 12:00
CT por un defecto de su plantilla. Esos **408 ticks son operativa real**: 218 prints, 239
contratos, precio moviéndose y spread ensanchándose de 2 a 5 ticks.

Filtrarlos sería replicar un error de 90 minutos de la plataforma dentro del research.
Detalle en `NT8_PLANTILLA_SESION_CIERRE_FERIADO_2026-08-23.md`.

```
sabado / domingo pre-apertura  ->  DESCARTA   (53 ticks, artefactos)
cierre anticipado de feriado   ->  CONSERVA   (408 ticks, operativa real)
```

## 4. Implementación

`edgelab/bridge/cme_hours.py` — `in_cme_week()` y `filter_cme_week()`.

- **Vectorizado**, sin conversión de huso tick por tick.
- **Falla cerrado** fuera del rango donde las transiciones de horario de verano están
  declaradas, en vez de adivinar el offset.
- `filter_cme_week(..., report=True)` devuelve el conteo y las fechas descartadas, para
  poder declarar en el acta qué se tiró.

### Verificación de bordes — 7/7

| caso | esperado | obtenido |
|---|:-:|:-:|
| domingo 16:59 CT (antes de apertura) | descarta | ✅ |
| domingo 17:00 CT (apertura) | conserva | ✅ |
| lunes 09:00 CT | conserva | ✅ |
| **jueves 13:29 CT (Thanksgiving)** | **conserva** | ✅ |
| viernes 15:59 CT | conserva | ✅ |
| viernes 16:00 CT (cierre) | descarta | ✅ |
| sábado 16:34 CT | descarta | ✅ |

## 5. Estado

El módulo está escrito y verificado, **todavía no cableado** al cargador de cintas. Se
cablea después de que terminen las paridades de GC 04-26 y GC 06-26, que están corriendo
con el cargador sin filtro — que es el caso conservador: si pasan sin filtrar, pasan
filtrando.

---

## Aporte al referente

El criterio queda separado en dos y por escrito: lo que el exchange no operó se descarta,
lo que operó se conserva aunque la plataforma no lo muestre. Sin esa distinción, "filtrar
para que coincida con NT8" habría borrado 408 ticks de operativa real de feriado junto con
53 artefactos de fin de semana.
