# Estado consolidado de campañas y dependencias — 2026-08-28

> Snapshot documental. No congela specs, no autoriza outcomes y no reemplaza manifests de campaña.

## 1. Cadena de integración

```text
main (baseline antiguo)
└─ foundation/f0b-compatibility-probe (base de integración)
   ├─ work/bt2a-gate2-l2-hardening
   │  └─ PR #15 work/bt2a-gate2-p2a-freeze
   │     ├─ PR #16 results/bt2a-p2a-v1-r1
   │     ├─ PR #18 research/bt2a-p2b-economic-gc-v1
   │     └─ PR #20 research/bt2a-p2a-clock-heterogeneity-v1
   ├─ PR #17 work/indicator-coordinate-store-v1
   ├─ PR #19 research/avolcluster-compression-v1
   ├─ research/avolcluster-nq-microticks-v1 (sin PR al corte inicial)
   └─ PR #21 docs/traceability-refresh-20260828
```

La indentación expresa dependencia conceptual/base declarada, no prueba de merge ni patch-equivalence.

## 2. Pull requests abiertas

| PR | Rama | Base | Estado | Rol |
|---:|---|---|---|---|
| #8 | `fix/g2-a1-calibration-hardening` | `foundation/f0b-compatibility-probe` | draft | contrato G2 rival; decisión semántica pendiente |
| #9 | `prep/indicator-onboarding-registry` | `foundation/f0b-compatibility-probe` | draft | onboarding de indicadores |
| #11 | `research/bigtrap2-distance-matched-null` | `audit/p0-bigtrap2-drift` | draft | investigación histórica/null |
| #12 | `fix/bigtrap2-v252-tick-export` | `audit/p0-bigtrap2-drift` | draft | corrección export BT2 |
| #13 | `research/zamr1-zone-atlas` | `research/bigtrap2-local-displacement-null` | draft | atlas multirresolución |
| #14 | `work/crypto-context-foundation-20260824` | `foundation/f0b-compatibility-probe` | draft | contexto crypto aislado |
| #15 | `work/bt2a-gate2-p2a-freeze-20260826` | `work/bt2a-gate2-l2-hardening-20260826` | draft | contrato P2-A |
| #16 | `results/bt2a-p2a-v1-r1-20260827` | `foundation/f0b-compatibility-probe` | open | publicación de resultado P2-A |
| #17 | `work/indicator-coordinate-store-v1-20260827` | `foundation/f0b-compatibility-probe` | open | coordinate store target-free |
| #18 | `research/bt2a-p2b-economic-gc-v1-20260827` | `work/bt2a-gate2-p2a-freeze-20260826` | draft | protocolo económico |
| #19 | `research/avolcluster-compression-v1-20260827` | `foundation/f0b-compatibility-probe` | draft | protocolo aVol/BigTrap |
| #20 | `research/bt2a-p2a-clock-heterogeneity-v1-20260827` | `work/bt2a-gate2-p2a-freeze-20260826` | draft | diagnóstico horario post-selección |
| #21 | `docs/traceability-refresh-20260828` | `foundation/f0b-compatibility-probe` | draft | refresh documental y registro de ramas |

## 3. Ledger de afirmaciones

| Objeto | MEDIDO | NO MEDIDO / NO AUTORIZADO |
|---|---|---|
| BT2A P2-A GC | first passage pre-cost en población publicada | confirmación, P&L neto, promoción |
| BT2A clock | cuatro sesiones prematuras, cuarentenadas | familia final 234 sesiones |
| aVol NQ microticks | densidad, cobertura y ancho de zonas en 378 configuraciones | first touch, expansión, compresión, dirección, P&L |
| aVol compression protocol | spec/runner de medición en rama PR #19 | resultado de Gate 1 para NQ-120t |
| Coordinate Store | infraestructura target-free en PR #17 | edge económico |
| Trazabilidad 28-ago | ramas, PR, dependencias y firewalls inventariados | contención/patch-equivalence de ramas históricas |

## 4. Reglas de actualización

Cada cambio material debe registrar en el mismo commit:

1. rama y `head_start`/`head_end`;
2. dirty/clean y archivos modificados;
3. spec/manifiesto gobernante y hashes;
4. población, instrumento, contratos y fechas;
5. outcomes abiertos/cerrados;
6. holdout tocado/no tocado;
7. estado `MEDIDO`/`NO MEDIDO`;
8. etiqueta permitida y etiquetas prohibidas;
9. relación con PR/base/resultado padre;
10. siguiente decisión que requiere intervención humana.

## 5. Criterio de cierre de ramas

Una rama sólo puede proponerse para cierre cuando exista evidencia de:

- PR cerrada/mergeada o decisión `not_planned` explícita;
- `merge-base --is-ancestor` cuando corresponda;
- `git cherry` o diff que adjudique contenido propio;
- destino de docs, specs, resultados y artefactos externos;
- ausencia de referencias activas desde manifests y protocolos;
- aprobación explícita del referente.

Este snapshot **no autoriza ningún cierre**.

## Aporte al referente

El mapa separa base, contratos, resultados y diagnósticos; evita leer las ramas como una línea temporal única y define qué evidencia falta antes de integrar o archivar.
