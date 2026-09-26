# Iteración 1 — GPT — preprocesamiento independiente de las tareas para Claude

**Fecha:** 2026-08-05  
**Rama auditada:** `fix/capture-probe-v2-contract`  
**Tip de entrada:** `a0087b9429eb2ec741a5d4a1c3d4ba6d3b783a58`  
**Naturaleza:** análisis estático y diseño de pruebas; no implementación  
**Outcomes consultados:** no  
**Holdout abierto:** no  
**NT8 ejecutado:** no

> Esta es la primera de tres iteraciones de modelos distintos. Su función no es
> ordenar a Claude que aplique parches ciegamente, sino reducir la ambigüedad:
> separar hechos, inferencias, reproducciones mínimas, criterios de aceptación y
> dependencias. Claude debe volver a verificar todo contra el tip que reciba.

## 1. Veredicto ejecutivo

El commit `a0087b9` corrige dos defectos reales e importantes:

1. elimina el identificador `ok` no declarado de `BigTrap2.cs`;
2. agrega `BARRA_PROCESADA` al camino de tick para que P1/P2 dispongan de un
   denominador por barra.

Pero el paquete todavía **no está listo para revisión ciega ni captura**. El
estado defendible es:

```text
reparación plausible en fuente
!= compilación demostrada
!= analizador totalmente alcanzado
!= instrumento validado con emisor real
!= medición válida de PRED-004
```

Antes de abrir NT8 hay que completar una microauditoría del analizador, construir
un gate real de compilación y actualizar el preflight obsoleto. En paralelo
pueden avanzar procedencia P5, firewall por capacidad, linaje 256→193 e
inferencia/multiplicidad.

## 2. Evidencia inspeccionada

Archivos leídos en el tip de entrada:

- `nt8/BigTrap2.cs`
- `tools/pred004_analyze.py`
- `tests/bridge/test_pred004_analyze.py`
- `docs/CONTRATO_ANALIZADOR_PRED-004.md`
- `docs/PREFLIGHT_PRED-004_NT8_2026-08-04.md`
- `CLAUDE.md`
- `CONTRATO_LLM.md`
- `ENVIRONMENT.md`

Restricciones heredadas que siguen vigentes:

- no abrir outcomes para diseñar el instrumento;
- no abrir holdout para esta reparación;
- no mover el pin ni capturar antes de compilación y revisión;
- no tocar los dos tests rojos declarados hasta validar en NT8;
- F9 continúa pausada;
- cambios de semántica del contrato requieren consulta a Nico;
- cada checkpoint de Claude debe terminar con `Aporte al referente: ...`.

## 3. Hallazgos que Claude debe reproducir antes de corregir

### H-GPT-1 — Rama `denom == 0` con nombre inexistente

En `tools/pred004_analyze.py`, dentro de `modo_p1p2`, la rama:

```python
if denom == 0:
```

construye `barras_ambiguas_interior` usando `verif`, pero `verif` no está
definida en la versión actual del módulo.

La prueba existente llamada
`test_p1p2_denominador_cero_es_ABSTAIN_no_PASS` no alcanza necesariamente esa
rama. Fabrica un log sin `BARRA_PROCESADA`, por lo que la función puede abstener
antes, en `primera_ok is None`.

#### Reproducción mínima exigida

Crear un log sintético que:

1. tenga `# meta`;
2. tenga por lo menos un `BARRA_PROCESADA`, para superar la abstención temprana;
3. haga que toda barra procesada del interior también figure en `amb`, de modo
   que `proc` quede vacío;
4. llegue efectivamente a `denom == 0`;
5. demuestre el fallo actual antes del parche.

#### Criterio de aceptación

- devuelve `estado=ABSTAIN`;
- exit code 2 por CLI;
- no lanza excepción;
- publica contadores consistentes;
- el test demuestra, por instrumentación o monkeypatch/coverage acotada, que la
  rama `denom == 0` fue alcanzada.

No alcanza con conservar el nombre del test anterior.

### H-GPT-2 — `--resolucion` existe, pero P5 todavía permite omitirla

El subparser `p5-time` declara:

```python
a.add_argument("--resolucion", default=None)
```

`modo_p5()` sólo verifica nombres cuando `resolucion_esperada` es truthy. Por
lo tanto, agregar la opción no hizo obligatoria la precondición: un llamador
puede omitirla y comparar archivos sin acreditar `Minute1`.

El test existente sólo prueba que una incompatibilidad es rechazada cuando el
argumento se pasa voluntariamente.

#### Decisión a elevar si hay duda semántica

Hay dos implementaciones defendibles:

- hacer `--resolucion` obligatoria en la CLI y exigir `Minute1` para P5; o
- aceptar la llamada pero devolver `ABSTAIN` si falta.

Lo que no es defendible es continuar silenciosamente.

#### Criterio de aceptación

Agregar pruebas separadas para:

1. CLI sin `--resolucion`;
2. histórico `Minute1` vs nuevo `Tick25`;
3. ambos `Minute1`;
4. API interna llamada con `None`, si la API interna sigue siendo pública.

La salida sin resolución nunca puede ser `PASS`.

### H-GPT-3 — El test H1 no es un gate de compilación

`test_H1_el_cs_no_tiene_identificadores_sin_declarar` busca específicamente el
token `ok`. Eso detecta el defecto conocido; no demuestra que el `.cs` compile
ni detectaría otro `CS0103`, incompatibilidad de API, referencia faltante o
error sintáctico.

#### Criterio de aceptación de T6

Debe existir un paso ejecutable que:

1. use el compilador/assemblies que realmente gobiernan NinjaScript, o una vía
   equivalente cuya equivalencia quede demostrada;
2. falle con exit code no cero ante cualquier error;
3. registre versión del compilador, inputs, hash del `.cs`, stdout/stderr y
   resultado content-addressed;
4. se ejecute antes de instalar/capturar;
5. tenga un control negativo con una copia mutada deliberadamente no compilable;
6. no modifique el `.cs` canónico durante el control negativo.

Un regex, un hash o una inspección estática pueden ser prechecks, pero no el
veredicto `COMPILA`.

### H-GPT-4 — El preflight operativo está obsoleto

`docs/PREFLIGHT_PRED-004_NT8_2026-08-04.md` todavía describe v2.3 y su hash,
propone comandos con `run_nt8_bridge.py` y conserva nombres esperados previos.
El contrato v3 posterior explica que esos comandos no miden PRED-004 como fue
escrita.

#### Criterio de aceptación

Actualizar o reemplazar el preflight para que cite:

- commit y hash exactos del paquete congelado final;
- `BigTrap2.cs` v2.4;
- `contrato_sha` vigente;
- compilación como gate previo a instalación/captura;
- `pred004_analyze.py` para P5, P1/P2 y P6;
- `--tz-chart` y resolución obligatorias;
- orden `Minute1 → Tick25 → Tick10`;
- exit codes 0/1/2;
- tratamiento explícito de P5 si T3 no prueba identidad/procedencia;
- inventario previo y posterior de archivos para P6;
- prohibición de mover el pin antes de la adjudicación.

El preflight no debe afirmar que un paso fue ejecutado si sólo fue documentado.

### H-GPT-5 — N1 sigue abierto

P5 compara `seq` absoluto aunque `eventSeq++` es compartido con diagnósticos que
P5 excluye. Un diagnóstico agregado en v2.4 puede correr el `seq` de eventos
económicos sin alterar su contenido económico.

Claude no debe elegir una solución por conveniencia. Primero debe inventariar,
por cada versión y camino, qué tipos incrementan `eventSeq` y en qué orden.
Después debe presentar las alternativas:

1. conservar `seq` absoluto y justificar por qué es comparable;
2. comparar ordinal económico además de reportar el corrimiento absoluto;
3. degradar P5 a `ABSTAIN` cuando el inventario no permita equivalencia;
4. reformular P5, lo cual sería cambio semántico y requiere aprobación de Nico.

#### Criterio de aceptación

- inventario verificable contra el emisor real;
- test con diagnóstico insertado antes de un evento económico;
- no esconder una diferencia mediante una lista ignorable agregada post hoc;
- cualquier cambio del estimando se identifica como cambio de contrato.

### H-GPT-6 — P3 debería exigir completitud del esquema OHLCV

La lógica actual considera que P3 dispone de campos si encuentra `open_blk` y
`open_bar`. Luego compara únicamente pares presentes. En el camino tick actual,
`ReportarMismatch` parece emitir los cinco pares, pero el analizador no hace de
esa completitud una precondición explícita.

Esto no se declara como defecto confirmado del emisor, sino como hueco de
contrato del consumidor.

#### Prueba adversarial propuesta

Fabricar un `FOOTPRINT_MISMATCH` de una barra procesada con OHLC coincidente y
sin `vol_blk`/`vol_bar`. P3 no debería certificar igualdad **OHLCV**. Las salidas
defendibles son `NO_APLICA`, `ABSTAIN` o `FAIL` según la semántica que Nico
apruebe; `PASS` silencioso no lo es.

## 4. Paquetes de trabajo preparados para Claude

### C0 — Revalidar el baseline

Antes de editar:

1. verificar rama, tip y working tree;
2. leer `CLAUDE.md`, `docs/NORTH_STAR.md`, contrato v3 y este expediente;
3. confirmar que no hay outcomes/holdout abiertos;
4. correr sólo la batería target-free pertinente;
5. reproducir H-GPT-1 y H-GPT-2 en tests nuevos que inicialmente fallen.

**Salida:** reporte breve de reproducción. No corregir un hallazgo que no pudo
reproducirse; explicar por qué.

### C1 — Microparche del analizador

Alcance cerrado:

- corregir H-GPT-1;
- cerrar la ausencia de resolución de H-GPT-2;
- decidir y cubrir completitud P3;
- cerrar o adjudicar N1;
- reconciliar docstring, contrato, CLI y tests.

No refactorizar módulos ajenos ni abrir outcomes.

**Gate:** controles negativos + suite pertinente + suite completa permitida.

### C2 — Gate real de compilación

Construir T6 como una pieza separada. Si la compilación sólo puede demostrarse
dentro de NT8, preparar el mecanismo y detenerse antes de ejecutarlo si hace
falta intervención/autorización de Nico. No sustituirlo por una afirmación de
que el fuente “parece compilar”.

**Gate:** control negativo no compilable y artefacto de compilación trazable.

### C3 — Preflight final

Actualizar el procedimiento únicamente después de que C1 y C2 estén definidos.
El documento final debe ser ejecutable paso a paso y no contener comandos
retirados.

### C4 — Revisión independiente

El implementador no adjudica C1/C2. Congelar:

- commit;
- hashes;
- contrato;
- analizador;
- tests;
- `.cs`;
- preflight.

Recién entonces entregar a revisor ciego. No mostrarle los hallazgos históricos
como lista de respuestas esperadas; sí darle el contrato y el paquete.

### C5 — Captura

Fuera de alcance hasta superar C0–C4, T3 y el veto. El orden permanece:

```text
compilar → instalar → Minute1 → Tick25 → Tick10 → P6 → adjudicar → decidir pin
```

No detenerse después de K25 aunque refute: K10 está preregistrado.

## 5. Tareas paralelas que no deben bloquear la microcorrección

Estas tareas pueden ejecutarse por otros modelos/agentes, con commits separados:

- **T0':** medición alternativa de PRED-004, tratada como impugnación y no como
  permiso para borrar la predicción registrada;
- **T3:** hashes y procedencia del input de P5;
- **T4:** linaje reproducible `256 días aptos → N=193`;
- **T5:** firewall por capacidad, no por string `purpose`;
- **T11:** dependencia, multiplicidad y criterio de muerte antes de outcomes.

`T10` puede prepararse, pero el censo pesado no corre durante capturas NT8.

## 6. Grafo de dependencias actualizado

```text
C0 reproducción
 ├─→ C1 analizador + N1 + contrato
 └─→ C2 compilación real

T3 procedencia P5 ───────────────┐
C1 + C2 ─→ C3 preflight ─→ freeze ├─→ T7 revisión ciega → T8 veto → T9 captura
T5 firewall por capacidad ───────┘

T4 y T11 deben cerrar antes de abrir EXPLORE/outcomes.
T0' corre en paralelo y sólo reemplaza algo si demuestra equivalencia del estimando.
```

## 7. Plan de commits recomendado

Mantener commits pequeños y adjudicables:

1. `test(pred-004): reproduce ramas no alcanzadas del analizador`
2. `fix(pred-004): fail-closed en denominador y resolución`
3. `test(pred-004): cubre seq y completitud OHLCV`
4. `build(nt8): agrega gate reproducible de compilación`
5. `docs(pred-004): actualiza contrato y preflight congelado`

No mezclar T3/T4/T5/T11 en esos commits.

## 8. Qué no debe hacer Claude

- no abrir NT8 ni capturar antes de los gates;
- no mover el pin;
- no leer el oráculo P5 ni el holdout para calibrar tests;
- no relajar el umbral de 1 %;
- no agregar excepciones después de ver resultados;
- no declarar T6 cerrada por regex/hash;
- no confiar en el nombre de un test como prueba de alcanzabilidad;
- no integrar Nautilus/Freqtrade/Hummingbot ahora;
- no iniciar F9;
- no combinar reparación y autoauditoría final.

## 9. Protocolo para las iteraciones 2 y 3

Para conservar señal independiente, el siguiente modelo debería:

1. auditar el mismo tip o registrar el nuevo tip exacto;
2. distinguir `hallazgo independiente`, `confirmación`, `refutación` y
   `extensión`;
3. no asumir que esta iteración es correcta;
4. proponer reproducciones mínimas, no sólo comentarios;
5. registrar desacuerdos sin resolverlos por mayoría;
6. escribir otro archivo `ITERATION_2_<MODELO>_2026-08-05.md` y luego
   `ITERATION_3_<MODELO>_2026-08-05.md`;
7. no modificar código productivo: las tres iteraciones preparan el trabajo;
   Claude implementa después del expediente consolidado.

## 10. Prompt de arranque sugerido para Claude después de las tres iteraciones

```text
Trabajá sobre la rama y tip que Nico indique. Leé CLAUDE.md, NORTH_STAR.md,
CONTRATO_LLM.md, el contrato vigente de PRED-004 y las tres iteraciones en
docs/research/ITERATION_{1,2,3}_*. No tomes ninguna como autoridad: construí una
matriz de hallazgos (confirmado/refutado/pendiente), reproducí primero cada
bloqueante contra el código actual y presentá el plan delta antes de editar.

Prioridad: fail-closed y alcanzabilidad real. No abras outcomes, holdout ni NT8;
no muevas el pin. Separá tests de reproducción, parche, gate de compilación y
preflight en commits adjudicables. El que implementa no aprueba su propia
reparación. Si una propuesta cambia la semántica congelada, frená y consultá a
Nico.
```

## 11. Resultado de esta iteración

Esta iteración no concede ni refuta PRED-004. Convierte una lista amplia de
pendientes en cinco reproducciones concretas, criterios de aceptación y un
grafo de dependencias. El principal riesgo encontrado es repetir el mismo modo
de falla con otra apariencia: un test cuyo nombre promete alcanzar una rama,
pero cuyo fixture abstiene antes de llegar a ella.

**Aporte al referente:** reduce el riesgo de capturar y adjudicar con un
instrumento que puede fallar fuera de las ramas ejercitadas, acercando PRED-004
a una medición falsable y no a un PASS nominal.
