# Revisión de Claude de la apertura conjunta del HOLDOUT A5 sin CME (2026-11-27)

Estado: VIGENTE — revisión descriptiva de `RESULTADO.md` y del código (`tools/holdout_a5_nocme_20261127.py`,
`tools/canasta_amplia.py`). No abre nada ni suma pruebas. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Procedimiento: conforme
- **K27:** la cita de autorización de Nico está en `AUTORIZACION_K27` y en cada línea de apertura de `HOLDOUT_VENTANAS.jsonl` (5
  aperturas, una por familia), como en `a20_terminal.py`.
- **Orden:** el pre-registro (`f99de827`, 13:53) es anterior al resultado (`af99e58c`, 14:05).
- **TERMINAL sellado:** la serie mensual publicada termina en 2026-09.
- **Lector de Carril 2:** es el mío, verificado IDÉNTICO en DESC y REP (`verificar_motor`). El único cambio es la ruta de
  `exigir_contada`.

## 2. Lectura de los resultados
| Familia | Potencia previa (× 0,5 / 1) | HOLDOUT | Lectura de Claude |
|---|---|---|---|
| **Carril 2 sellada (16)** | 0,25 / 0,63 | SR 1,06, t 2,42, p 0,0077 | **Confirmación limpia** (detalle abajo) |
| Pozo sin CME (4 frentes, 63 meses) | 0,30 / 0,73 | SR 0,92, t 2,12, p 0,017 | Confirma por la regla de FDR del embudo (BH q 0,10 sobre las 5 familias), pero lo arrastra Carril 2 (correlación 0,55 con Macro) |
| Macro risk premia | 0,11 / 0,21 | SR 0,38, t 0,87 | NO_CONCLUYENTE; su holdout se gastó con potencia ≈ 0,15 |
| Cripto v3 | 0,18 / 0,48 | SR 0,49, t 0,60 | NO_CONCLUYENTE; retiene el 38 % del SR de desarrollo |
| Cripto OFI | 0,10 / 0,18 | SR 1,13, t 1,39 | NO_CONCLUYENTE; señal a favor, sin potencia |

**Carril 2 sellada:**
- 902 operaciones; 14 de 16 regla-instrumento con R medio positivo.
- SR en HOLDOUT (1,06) igual o mayor que en DESC (0,80) y en REP (1,07): no hay encogimiento.
- Por época: 2006–12 0,68; 2013–18 1,42; 2019–26 1,12. El temor de que decaiga después de 2018 (visto en DESC 2021–26) no se repite
  en los meses sellados.

**Multiplicidad:**
- El resultado rotula 9 cortes como CONFIRMA, pero son carteras correlacionadas que repiten a Carril 2. Las pruebas independientes
  son las 5 familias.
- Con Holm sobre esas 5 sólo confirma Carril 2 (p 0,0077 ≤ 0,01). Con BH q 0,10, la regla del embudo, confirman Carril 2 y el pozo.

**Stouffer con la REP:** no vale para cripto, porque su REP se iteró entre v1 y v3. Para cripto, lo limpio es sólo la t del HOLDOUT.

## 3. Consecuencias
- **Carril 2 es la primera canasta de EdgeLab con el HOLDOUT A5 sellado a favor.** No queda promovida a operación real:
  `puede_promover` exige R forward > 0 y el operar con dinero es decisión de Nico.
  - Siguiente evidencia: su terminal desde 2026-10-01 (sin tocar) y el forward.
  - Necesita una cuenta que permita mantener posiciones de noche (no Lucid).
- **Macro, cripto y OFI ya no tienen holdout:** sólo les queda el forward.
- **Lección para el registro de errores:** abrir familias nacidas el mismo día con potencia 0,10–0,21 gasta su única confirmación con
  muy poca probabilidad de decidir. Es lo que K27 buscaba evitar. Acá fue una decisión explícita de Nico, no un error de procedimiento.

Aporte al referente: confirma con datos sellados la canasta Carril 2, el primer resultado que pasa una confirmación limpia. Separa esa
confirmación de los cortes correlacionados y de las familias que gastaron su holdout sin potencia.
