# Relanzamiento causal de 11 campañas cerradas (2026-11-02)

Estado: VIGENTE. Pedido de Nico: «dale, lanzá las 11». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF2 → embudo completo.

## Por qué
Las 11 terminaron en FIN con código que después se corrigió:
- la familia U1 usaba `areas_expansion.disparos` con mirada al futuro;
- CVGAP tenía dos problemas de borde.

Ver `HALLAZGO_LOOKAHEAD_DISPAROS_U1_20261102.md`. Según `GUIA_GRILLA_MASIVA.md`, una corrida lanzada con código que después se
corrigió no se mira: se documenta como descartada y se relanza.

## Qué se relanza
| Original (FIN, descartada) | Nueva campaña |
|---|---|
| U1-6B-FUT-GRILLA, U1-6B-GRILLA, U1-6E-CONFIRMA-GBP, U1-6E-FUT-GRILLA, U1-6E-GRILLA | mismo cid + `-C` |
| U1-RACIMOS-GRILLA-YM, U1-ZONAS-AVCL-ES, U1-ZONAS-BT2-YM, U1-ZONAS-GRILLA-YM | mismo cid + `-C` |
| CVGAP-ES, CVGAP-CFD-ES | mismo cid + `-C` |

- **Igual que la original:** módulo, grilla, períodos, justificación económica, condición de refutación y familia.
- **Distinto:** el código, ahora causal y certificado; el conductor, ahora `local` (esta sesión), con estado en `embudo/` de esta carpeta.
- **Multiplicidad.** Cada DESC vuelve a registrar sus celdas en el contador global: las pruebas descartadas siguen contadas. Los pasos
  de LORD++ salen del libro de cada familia. Es lo conservador.
- **Lo que no cambia.** Las réplicas que estas familias ya miraron siguen consumidas. Si una pista llega a OOS en una ventana ya mirada,
  el embudo lo trata según su regla de réplica.

## Preflight: 4 bloqueadas por el control de ruido (2026-11-02), causa raíz
U1-6B-FUT-GRILLA-C, U1-6B-GRILLA-C, U1-6E-FUT-GRILLA-C y U1-6E-GRILLA-C (módulo `u1_cfd`) quedaron BLOQUEADAS: «ruido puro con 1 celda
rechazada por Romano-Wolf».

**Diagnóstico.**
- **Sobre 6 semillas de ruido** (preflight con `B_RW = 40`):
  - 2 rechazan una celda (semillas 11 y 13) y 4 no;
  - el FDR q 0,10 no nomina ninguna celda en ninguna semilla;
  - las dos celdas rechazadas usan la ejecución 40 (`HACEV15/T3/S3`) en escala 2.
- **Las celdas:** 30 y 40 operaciones, con objetivo de ≈ 10 puntos y stop de ≈ 45. Bajo camino aleatorio ganan ≈ 82 % de las veces;
  en la semilla 11 salieron 28 de 30 ganadoras, algo con probabilidad ≈ 2 %. Con 890 mil celdas evaluables, alguna lo va a mostrar.
- **No es sesgo del simulador ni de las variables:**
  - auditoría vela a vela de esas 77 operaciones: 0 fallas;
  - la ejecución 40 completa sobre ruido da −10,3 por operación (26.947 operaciones, 60 % de acierto);
  - todas las ejecuciones son negativas sobre ruido.
- **Es la calibración del chequeo.** Romano-Wolf con 40 remuestreos tiene p mínimo de 1/41. Con pagos muy asimétricos y n chico, el
  bootstrap de la misma muestra subestima la cola de pérdidas grandes y rechaza de más: 2 de 6 contra un 5–10 % nominal.

**Qué se hizo.** Nada en el gate. Cambiarlo es cambiar la semántica de validación, y eso lo decide Nico.

**Opciones.**
1. Que el preflight exija 0 nominadas por el FDR, coherente con la decisión del 2026-10-24: Romano-Wolf es diagnóstico.
2. Subir `B_RW` del chequeo de ruido (por ejemplo a 400) y volver a medir su tasa de falsos rechazos.

Después se bloquearon también U1-ZONAS-AVCL-ES-C y U1-ZONAS-BT2-YM-C (familia `u1_zonas`), con el mismo mensaje. Total: **6 BLOQUEADAS**
hasta que haya decisión; el diagnóstico de arriba se hizo sobre `u1_cfd`.

**5 en descubrimiento (DESC lanzado):** U1-6E-CONFIRMA-GBP-C, U1-RACIMOS-GRILLA-YM-C, U1-ZONAS-GRILLA-YM-C, CVGAP-ES-C y CVGAP-CFD-ES-C. Las
conduce `tools/embudo_correr.py` desde esta sesión, con estado en `embudo/`.

## Resultados (2026-11-02 18:10 UTC)
| Campaña | DESC causal | Pistas a réplica (abr–sep 2026) | Estado |
|---|---|---|---|
| CVGAP-ES-C | 165.540 evaluables, FDR 0 | 0 de 20 confirmadas (Simes 0,37) | PISTAS_VIVAS |
| CVGAP-CFD-ES-C | 29.752 evaluables, FDR 0 | 0 de 20 (Simes 0,95) | PISTAS_VIVAS |
| U1-ZONAS-GRILLA-YM-C | 1.009 evaluables, FDR 0 | 0 de 3 (Simes 0,15) | PISTAS_VIVAS |
| U1-6E-CONFIRMA-GBP-C | 535.450 evaluables, FDR 2 (no cumplen la selección) | 0 de 20 (Simes 1,0; canasta −5,2) | SIN_CANDIDATAS |
| U1-RACIMOS-GRILLA-YM-C | 0 evaluables (ninguna celda llega a 30 operaciones) | — | SIN_CANDIDATAS (sin dato) |

**Lectura.**
- Con el código causal, ninguna de las 5 da candidatas, igual que con el código viejo: la corrección no cambió el veredicto de estas
  familias.
- PISTAS_VIVAS significa sin potencia para decidir: siguen vivas, pero no son candidatas al holdout.
- **En curso (DESC lanzado 18:10):** U1-6B-FUT-GRILLA-C, U1-6B-GRILLA-C, U1-6E-FUT-GRILLA-C, U1-6E-GRILLA-C, U1-ZONAS-AVCL-ES-C y
  U1-ZONAS-BT2-YM-C.

## Cierre del relanzamiento (2026-11-02 19:00 UTC): 11 de 11 en FIN, sin candidatas del embudo
| Campaña | Estado | Lectura |
|---|---|---|
| U1-6B-GRILLA-C | SIN_CANDIDATAS | canasta de pistas **en contra con potencia** en la réplica |
| U1-6E-GRILLA-C | SIN_CANDIDATAS | canasta de pistas **en contra con potencia** |
| U1-6E-FUT-GRILLA-C | SIN_CANDIDATAS | canasta de pistas **en contra con potencia** |
| U1-6E-CONFIRMA-GBP-C | SIN_CANDIDATAS | canasta en contra |
| U1-RACIMOS-GRILLA-YM-C | SIN_CANDIDATAS | sin dato (0 celdas evaluables) |
| U1-6B-FUT-GRILLA-C | PISTAS_VIVAS | 1 pista, no confirma |
| U1-ZONAS-AVCL-ES-C | PISTAS_VIVAS | canasta −0,49, IC90 [−1,17; +0,12] |
| U1-ZONAS-BT2-YM-C | PISTAS_VIVAS | 1 pista, no confirma |
| U1-ZONAS-GRILLA-YM-C | PISTAS_VIVAS | 3 pistas, no confirman |
| CVGAP-ES-C | PISTAS_VIVAS | canasta +1,3, no confirma |
| CVGAP-CFD-ES-C | PISTAS_VIVAS | no confirma |

**Lectura.**
- **U1 sobre FX (6B y 6E, spot y futuro), con código causal: en contra con potencia en la réplica.** Esa línea queda cerrada para estas
  celdas.
- **Nominación forzada** (`NOMINACION_FORZADA.json`): CVGAP-ES-C, CVGAP-CFD-ES-C y **U1-ZONAS-AVCL-ES-C** (réplica +2,0 en 33 operaciones,
  IC90 [−1,9; +5,7]; DESC +4,1).
