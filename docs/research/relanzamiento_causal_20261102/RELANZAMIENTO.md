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

Hasta que haya decisión, esas 4 siguen BLOQUEADAS y las otras 7 siguen el embudo.
