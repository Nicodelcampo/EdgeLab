# Banco de eventos — muchos experimentos, poca multiplicidad

Estado: VIGENTE (2026-11-10, pedido de Nico: «que pase a ser una estructura central en EdgeLab, accesible y usable por cualquier
agente»). Va completo en el núcleo de contexto de TODOS los roles (`edgelab/autopilot/contexto.py::NUCLEO_FUENTES`).
Código: `edgelab/research/banco_eventos.py`. Uso: `python tools/banco_eventos.py`. Tests: `tests/research/test_banco_eventos.py`.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Para qué
Probar muchísimas ideas distintas sobre eventos (toques, creaciones, barridos, expansiones…) **sin diseñar cada una** y **sin gastar
multiplicidad por cada cosa mirada**. Lo que cuesta no es mirar: es elegir y confirmar en datos no mirados. El banco separa las dos
cosas de forma mecánica.

## Cómo funciona (siempre igual, para cualquier experimento)
1. **Generador → tabla.** Un kernel produce una fila por evento: `inst`, `fecha` (sesión CME, AAAAMMDD), `placebo` (0 real, 1
   control que comparte la condición), rasgos causales numéricos y desenlaces. Los generadores conocidos están en
   `banco_eventos.GENERADORES` (`python tools/banco_eventos.py generadores`). Uno nuevo se agrega ahí con su test de causalidad por
   prefijo (K7) y su control.
2. **Experimento = especificación JSON** (`python tools/banco_eventos.py plantilla`), guardada en
   `docs/research/banco_eventos/specs/`: tabla, ventana (antes del holdout), desenlace y TODAS las columnas de desenlace (para que
   ninguna entre como rasgo), dirección esperada (+1, −1 o 0), nulo, umbral económico (0,08 R), k, q, justificación económica y cómo
   podría refutarse. Nada más: no se escribe código por experimento.
3. **Partición honesta.** Semanas alternas, con desfase fijado por el hash de la familia: mitad A (explorar) y mitad B (probar). Sólo
   depende de la fecha; una semana entera cae en la misma mitad.
4. **Mitad A: exploración libre.** Cada rasgo × 3 estratos, cada par de rasgos × 9 estratos y un modelo aditivo encogido con todos
   los rasgos. Los cortes salen de A (terciles por activo; cortes fijos para rasgos discretos, K10). Nada de A es evidencia.
5. **Congelado antes de mirar B.** Las k mejores celdas (rasgos distintos, n ≥ `min_n`, más allá del umbral económico en la dirección
   declarada) y el modelo se escriben en `HIPOTESIS_CONGELADAS.json` con su sha.
6. **Mitad B: k + 1 pruebas.** Media por bootstrap de sesiones, p de una cola contra el nulo, BH q 0,10. El modelo se prueba como
   «tercil alto del puntaje − tercil bajo». El control (placebo) con la misma celda va como diagnóstico.
6b. **Hipótesis previas** (`hipotesis_previas`): las elegidas en OTROS datos (otro activo, otra familia) y declaradas antes de
   mirar esta tabla no salen de A, así que se prueban con TODA la tabla y su propio BH (registro `banco/<nombre>/previas`). Es la
   forma barata de confirmar una pista en datos independientes sin gastar la réplica.
6c. **Mecanismo, no herencia:** cada celda informa también `vs_resto` (celda − resto de la tabla, bootstrap por sesión). La prueba
   «la celda paga» (media > nulo) puede salir positiva sólo porque el evento entero paga; `vs_resto` dice si la condición agrega algo.
7. **Salida como guía.** `RESULTADO.json` + `RECOMENDACIONES.md` (`recomendador.py`: CONFIRMAR, INDAGAR, ESTRUCTURA_DE_PRECIO,
   DESCARTAR…). Lo nominado va a la **réplica congelada** de la familia (o al embudo); nada se promueve desde el banco.

## Rasgos y generadores propios (Nico 2026-11-10, acotación de F9, sin cupo)
El agente puede crear rasgos nuevos (una columna causal más en la tabla de un generador) y generadores nuevos (un detector de
eventos con su control). No puede crear indicadores de dibujo/zonas operables: eso sigue pausado (F9). Contrato:
1. **Antes de tocar retornos:** mecanismo que mide, justificación económica y cómo podría refutarse, escritos en el docstring del
   generador o del rasgo y en `GENERADORES`.
2. **Construcción sin retornos:** parámetros fijados por una regla mecánica sobre frecuencia, estabilidad y escala (E0); nunca
   ajustados mirando desenlaces.
3. **Causal por contrato:** test de causalidad por prefijo (cambiar lo posterior al evento no cambia el rasgo) y casos de borde (primer
   y último tick). `GENERADORES[<nombre>]["test_causalidad"]` apunta al test; `tests/research/test_banco_eventos.py` verifica que
   exista.
4. **Versión congelada:** un rasgo o un parámetro nuevo es una versión nueva del generador, y su tabla es una tabla nueva.
5. **Prueba sólo en datos no mirados:** lo que inspiró el rasgo nunca sirve para evaluarlo (otra ventana, otro activo o el
   forward). El banco lo hace cumplir con `tabla_no_mirada` y el libro de usos.
6. **Retiro:** un rasgo que el banco no nomina con potencia queda NO_REPETIR en `FACTORES.jsonl` con su MDE.

## Cuánto cuesta
- Registro global: `banco/<nombre>/A` (celdas exploradas, nota «no confirmatoria») y `banco/<nombre>/B` (k + 1 pruebas, las únicas
  que gastan α).
- **La mitad B se usa UNA vez por familia y ventana** (`docs/research/banco_eventos/USOS.jsonl`; el código se niega a repetir). Una
  idea nueva sobre la misma familia y ventana no va al banco: va a la réplica o espera datos nuevos.

## Guardas automáticas (`python tools/banco_eventos.py preflight <spec>`)
- Contrato: campos obligatorios, `tabla_no_mirada: true` declarado (K19), ventana y tabla antes del holdout (`edgelab/holdout.py`), sin sesiones excluidas, rasgos numéricos,
  ningún rasgo que sea desenlace, desenlace finito, a lo sumo `max_rasgos` rasgos (la biblioteca se declara, no se vuelca).
- Muestra: ≥ 20 sesiones en cada mitad; aviso si un estrato tiene < 10 % de A.
- **Calibración:** el mismo proceso con el desenlace permutado dentro de (activo, mes) y centrado en el nulo. Mide la tasa de error
  de familia del método sobre ESA tabla (medida en sintéticos: 8–13 % con q 0,10). Bloquea si hay evidencia binomial de que supera 2q.
- `correr` exige preflight en verde.

## Qué hace cada agente
- **Proponente:** una idea sobre eventos que ya tienen generador = una especificación JSON, no un módulo. Varias ideas sobre la misma
  tabla van en UNA especificación (todas se exploran en A); elegir entre ellas es trabajo del banco, no del proponente.
- **Programador:** un generador nuevo (detector causal → tabla con contrato → control → test de prefijo) se registra en
  `GENERADORES`; nunca reescribe estratos, bootstrap o BH (están en el banco).
- **Revisor:** KILL a una especificación sin preflight en verde, que reuse la mitad B de una familia y ventana, o que confunda
  exploración (A) con evidencia.
- **Meta-analista:** parte de `RECOMENDACIONES.md` del banco; `mejores_a` del resultado son pistas para la próxima tabla, nunca
  evidencia.

## Límites (no desaparecen)
- Partir en dos reduce la potencia de cada mitad: sirve para familias con muchos eventos (cientos por mitad); para eventos raros,
  una hipótesis pre-registrada contra placebo (método §4).
- La biblioteca de rasgos se congela por versión del generador. Agregar rasgos después de ver B y volver a correr es reusar B: el
  libro de usos lo impide.
- Réplica y holdout siguen siendo únicos: el banco multiplica lo que se explora, no las confirmaciones.
- Un rasgo calculado con información posterior al evento invalida todo: la causalidad es responsabilidad del generador (test de
  prefijo obligatorio).

## Primer uso declarado
`docs/research/banco_eventos/specs/HFT_RUPTURA_banco.json` queda como plantilla: **no se corre sobre `HFTC_ruptura.csv`** porque la
indagación pre-registrada de HFT-RUPTURA miró todo DESC (las dos mitades) el 2026-11-10. **Regla: el banco sólo corre sobre una
tabla cuyos desenlaces nadie miró** (otro activo, otra ventana no usada o un generador nuevo). Una tabla ya analizada no tiene
mitad B honesta.
