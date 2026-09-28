# IPC-NIVEL-REGRESO (MES) — resultado del descubrimiento (2026-09-28)

**Veredicto: 1 de 36 sobrevive (BH q = 0,10), en el sentido de «resiste», no de imán.** OK de Nico. Simulaciones
corridas en `a22ea90b` (árbol limpio); estadísticas recalculadas en `9d23775c` (árbol limpio) tras corregir un bootstrap
degenerado: la primera versión del reporte daba p = 0 en celdas con n = 1 y listaba 4 «sobrevivientes»; con el mínimo de
30 eventos por celda (ya usado en CONT-TPSL) sobrevive 1. La versión con el error se conserva en el scratchpad de la sesión,
no en el repo. Artefactos: `artifacts/ipc_nivel_regreso/{eventos,reporte}.json`.

MES 25t, Lucid, 171 sesiones. 2.214 regresos a niveles vírgenes, 93.642 regresos de control (pivotes sueltos).
Cortes: D (distancia máxima antes de volver) 18 / 32 t; V (volumen relativo del alejamiento) 50 / 226.

- **Sobrevive:** P2 piso, D bajo, V bajo: el nivel se barre **6,8 pp menos** que el pivote suelto en la misma celda
  (IC 90 % [−11,5; −2,9], p 0,002; n 275 / 7.215).
- Casi: P2 techo, D bajo, V bajo −7,2 pp (p 0,008; no pasa BH).
- Contra el azar (P1): ninguna. La celda lejos + mucho volumen (la del imán) queda en −0,6 / +0,5 pp y **se barre igual
  que el pivote suelto** (P2 ≈ 0).
- Celdas vacías o chicas (lejos + poco volumen; cerca + mucho volumen): sin prueba, publicadas con su n.

## Lectura
Coherente con la formación: el nivel resiste más que un extremo cualquiera cuando el precio vuelve **rápido y sin
volumen**; cuando vuelve de lejos y con volumen, la diferencia desaparece. El imán tal como se lo imaginó (lejos + volumen
→ barre más) no aparece. Aviso de Nico sobre efectos que se anulan: vigente; L2 pendiente.
Candidato a la confirmación única abr–jun: celdas D bajo / V bajo (piso y techo), sentido «resiste».
