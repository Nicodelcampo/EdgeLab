# Camino a PASS de paridad — para los 7 y para el próximo

- **Fecha:** 2026-08-19
- **Para qué:** que BigTrap2, aVolClusterPOI, Gaps2, AACloseOpenDiffs, VolTicksPOC2,
  HFTZones2 y aVolCellPOI2 (y el que venga) lleguen a un PASS **por el mismo
  camino**, no por un arreglo distinto cada vez.
- **Esto no corre kernels.** Extrae el patrón que ya cazó el canal. El que tiene
  la máquina (Opus) lo ejecuta.
- **Firewall:** no toca holdout, P&L ni F4.

## 1. Qué es PASS acá (una sola definición)

PASS = el kernel Python y el oráculo NT8 producen **las mismas zonas** (geometría,
lado, timestamps de creación) bajo el matcher del repo, **después** de descontar
warmup, y el veredicto **se deriva** del matcher, no de un string.

No es PASS:

- un `version=` que dice v2.3 (P-34);
- un `WARN` guardado como `parity_exact` (P-35, decidido: WARN no es exacto);
- “representativa” usada para promover (P-37: no entra a G2+);
- un % alto sin códigos de residual (P-43 sí localizó; eso es el modelo).

## 2. El camino, en orden. El próximo indicador recorre el mismo.

1. **Identidad por blob, no por etiqueta.** `.cs` del repo = `.cs` que produjo el
   CSV. Si el que corrió no está commiteado, cuarentena. (P-08, P-34)
2. **Oráculo con holdout físicamente afuera.** Corte por trade date CME, no por
   calendario. `holdout_included` **computado**. (P-17, P-41)
3. **Kernel Python del mismo blob.** Sin re-transcribir. Path + blob sha1.
4. **Dos corridas de warmup**, no una. Warmup=1 vs el mínimo del indicador
   (p.ej. 12). Lo que baja entre las dos es warmup; lo que queda es defecto.
   (P-42: 14 → 9 MISSING)
5. **Matcher con códigos**, no un %. `MATCHED` / `GEOMETRY_DIFF` /
   `FEATURE_DIFF` / `TIMESTAMP_DIFF` / `MISSING_*`. Cada código tiene una causa
   o queda abierto con un caso reproductor.
6. **Causa raíz antes de tocar el gate.** Prohibido ampliar tolerancia después
   de ver el número.
7. **Test que falla si la propiedad se rompe** + control negativo (un caso que
   el test *puede* atrapar). Construcción + declaración no es gate.
8. **Publicar al store solo con el veredicto derivado.** WARN ≠ exacto.

Si el paso 5 deja un residual de borde documentado (colas, madurez), eso es
**representativa** (D-6). Sirve para investigación. **No** para promover.

## 3. Estado de los 7, contra ese camino

| # | Indicador | Dónde está | Próximo paso (máquina) |
|---|---|---|---|
| 1 | BigTrap2 | Exacta medida (3.628/3.638) | Cerrar `tick:5/10` o declararlos fuera |
| 2 | aVolClusterPOI v0.5 | 72/72; D-6 exacta | No bloquea H-Z2A. Cablear al store es P-40, no paridad |
| 3 | Gaps2 | Representativa 11.435/11.442 | Residuos de borde: dejarlos nombrados, no “arreglarlos” a PASS |
| 4 | AACloseOpenDiffs | Representativa 18.004/18.020 | Igual |
| 5 | VolTicksPOC2 | Representativa + `tick:N` sin secuenciador | No promover `tick:N` (P-28 / D-3) |
| 6 | HFTZones2 | 99,89 % GC; hay PASS 4.821 | Canon formal **después** de censo v2 (P-48) |
| 7 | aVolCellPOI2 | **FAIL** 671 vs 678, 16 reales | **P-42**: umbral del perfil por bucket. Es el único PASS que falta de verdad |

“La mayoría den PASS” **ya es cierto en el sentido D-6** si se acepta
representativa para el trío. “Los 7 den PASS exacto” exige cerrar P-42 y el
canon de HFTZones2. Eso no se hace desde acá: hace falta oráculo + máquina.

## 4. Lo que sí se hace desde acá (y queda hecho)

Este archivo **es** el camino. El próximo indicador no se inventa un procedimiento:
copia la lista del §2. Si un paso se salta, no es PASS.

Cuando vuelva el artefacto del censo v2, el auditor verifica eso primero.
P-42 se retoma **después** de v2, en paralelo a HFTZones2, no antes: v2 es la
ruta crítica.

**Aporte al referente:** paridad es un medio (nivel 6). Un camino repetible evita
que el octavo indicador cueste otra semana de cazar etiquetas.
