# FP4 v0.2 — mínimo físico según captura de Nico

# FP4 — franja amplia con cuatro pasadas y poco comercio

**Prototipo v0.2, para revisión geométrica. No indicador de entrada ni edge validado.**

## Pedido congelado

- Entrar por un borde y salir por el opuesto cuenta una pasada. Misma entrada/salida no cuenta.
- Alejamiento X desde el borde de salida: `max(2 ticks, ceil(0.25 × ancho))` antes de habilitar otra pasada.
- Sin vencimiento por sesiones, días o edad. Cambiar contrato/activo o declarar un hueco desconocido obliga a reinicio, no se considera continuidad.
- **Opción2:** al completar la cuarta pasada de la primera candidata que califica, congela una única zona y detiene TODA la búsqueda. Quinta pasada y datos posteriores no cambian el estado. Reinicio manual.
- Si completa cuatro sin calificar, se retira esa candidata; no espera la quinta para rescatarla.

## Qué identifica

Una máquina de cambios direccionales reconoce impulsos observados: confirmación por reversión de `max(3, ceil(0.25 × mínimo físico))` ticks (8 en MNQ), desplazamiento mínimo12ticks (defaults estructurales, no óptimos universales). Sobre el primer impulso confirmado crea tres franjas interiores fijas:12.5–87.5%,25–75%,37.5–62.5% de su amplitud. Usa sólo ese prefijo conocido. No modifica bordes para que futuras pasadas encajen. No garantiza encontrar todas las franjas visuales posibles.

Primero cuenta cruces; al cuarto los puntúa. Incluye volumen/prints y recorrido de visitas fallidas o microreentradas intermedias, aunque no sumen pasadas. Un salto de un exterior al otro sin ningún print observado dentro no fabrica una pasada ni volumen cero.

## Dos rarezas, no dos p-values

1. Tamaño: rango percentilar de ancho frente a impulsos anteriores del mismo instrumento, contrato y familia de recorte.
2. Poco comercio: percentiles inversos de volumen30%, prints20%, permanencia30%, recorrido lateral20%.

Los tres primeros se expresan por nivel de precio incluido (`ancho+1`) y por pasada; lateral es recorrido extra dentro / ancho /4. Permanencia es una **aproximación por intervalos entre prints, con precio izquierdo observado**; no prueba ubicación continua del precio entre eventos y puede incluir tiempo sin mercado si no se provee una máscara de reloj. No confundir cantidad de operaciones con contratos.

Referencias: últimos1000impulsos elegibles; mínimo32. Para comercio, anchos entre0.5× y2× el ancho candidato. Se congelan al crear la candidata, **antes** de incorporar su impulso a la referencia: sin auto-referencia ni datos posteriores. Falta de soporte no se puntúa como escasez.

P90 es una guía. Defaults de arranque: tamaño>=P80, poco comercio>=P50, combinado `0.55*tamaño +0.45*poco_comercio >=0.82`. Permiten que comercio excepcional compense no llegar aP90. **No han sido calibrados por frecuencia ni se afirma que sean el equilibrio óptimo.** Empates percentilares reciben0.5, no rareza máxima.

No se usan viewport, barras o temporalidad para detectar: la misma capa raw se puede dibujar sobre distintas series. Resultados estadísticamente destacables = ranks descriptivos del generador, **no significancia inferencial ni ventaja financiera**.

## Escala de la captura y mínimo físico (v0.2)

La captura de Nico sirve sólo como referencia visual de tamaño. Azul superior 30837.50; azul inferior aproximadamente 30830.00. La etiqueta blanca 30830.25 es precio actual, no el límite. Se adopta **7.5 puntos = 30 ticks de MNQ** como mínimo de banda, además de los percentiles. NQ usa el mismo mínimo en puntos porque comparte la escala de cotización; no se supone igual volumen o comportamiento.

En una banda mínima, X=ceil(30×0.25)=8 ticks=2 puntos; bandas más anchas exigen mayor alejamiento. El giro que confirma impulsos también se escala a 8 ticks. Son decisiones geométricas explícitas, no parámetros optimizados con resultados futuros.

Para otros instrumentos: `mínimo_target_ticks = max(4, ceil(30 × R_target_ticks / R_MNQ_ticks))`. R requiere una referencia histórica comparable, robusta y estrictamente anterior en ticks nativos, por ejemplo rango típico de un minuto con igual calendario/horario. La captura no permite medir R. **Los perfiles GC/ES/RTY todavía no están medidos ni congelados.** No transferir 30 ticks automáticamente ni convertir por dólares. `transferMinWidth` valida el cálculo; sin perfil explícito el núcleo se abstiene (`ABSTAIN_WIDTH_PROFILE`). Para un activo con perfil medido usar `--min-width-ticks N` o el campo nuevo del panel. La interfaz no certifica por sí sola la procedencia de ese N.

Se conservan bandas pequeñas entre las referencias históricas: eliminarlas sesgaría el percentil. Sólo se impide que se conviertan en candidatas publicables.

Smoke v0.2: los primeros 200.000 ticks reales de MNQ 09-25 no produjeron zona calificada (SEARCHING; 34 candidatas completaron cuatro, 27 rechazadas y 7 sin soporte de referencia). No es un censo diario ni evidencia de frecuencia suficiente. Los smokes MNQ/RTY v0.1 son anteriores a esta escala y no validan el mínimo nuevo. No se amplió la ventana ni se bajaron umbrales para rescatar una detección.

Instalación: usar una carpeta/copia de revisión NUEVA para v0.2 que disponga de los recursos locales vendor/bundles. Los módulos v0.1 presentes son distintos y el installer se abstendrá; no sobreescribirlos a escondidas.

## Archivos

- `four_pass_sparse.js`: única implementación del detector, Node/browser.
- `four_pass_sparse_cli.cjs`: ticks JSONL → capa JSON.
- `prepare_four_pass_sparse.py`: canonical parquet → ticks acotados → mismo núcleo JS. Requiere `pyarrow` y `node`.
- `four_pass_sparse_worker.js`: lectura streaming JSONL en navegador sin bloquear el panel.
- `four_pass_sparse_viewer.js`: panel y overlay separado, sin inferir comercio de OHLC.
- `install_four_pass_sparse.py`: crea una copia de revisión, jamás sobreescribe index.html ni otro escritor.

## Entrada JSONL

```json
{"ts_ns":"1754000000000000001","sequence":1,"price_tick":100,"volume":3,"instrument":"MNQ","contract":"MNQ 09-25"}
```

Timestamp exacto en STRING; ticks y secuencia enteros; timestamps no decrecientes, secuencia estrictamente creciente; volumen real positivo de LAST/operación. `gap:true` se abstiene. Las velas OHLC, volumen por barra y trades L2 agregados no reconstruyen este orden.

```powershell
node four_pass_sparse_cli.cjs --input ticks.jsonl --out capa.json --tick-size 0.25 --asset ID_EXACTO_DEL_VISOR
```

Parquet canónico (ventana explícita y fuente cuyo hash ya verificó la custodia):

```powershell
python prepare_four_pass_sparse.py --source "E:/ticks/MNQ.parquet" --expected-sha256 SHA_VERIFICADO --out "E:/fp4/capa.json" --asset ID_EXACTO_DEL_VISOR --tick-size 0.25 --max-rows 200000 --before-ns 1782864000000000000
```

EOF/límite sin zona significa sólo que no se encontró una en ese prefijo, no ausencia de zonas. El adaptador puede serializar/decodificar el prefijo completo antes de que el núcleo se detenga; no afirmar que el parquet dejó de leerse justo en la señal. No se calculan desenlaces.

## Instalación LOCAL segura para Codex / Antigravity

Base auditada: `391314907dec889599493c4a38282171d94a2f25`.

1. Un worktree/escritor separado. No mezclar con cambios locales del visor ni hacer merge automático.
2. El ZIP contiene `source/index_reference.html`, una copia limpia del visor público auditado. Copiarla como `index_fp4_base_3913149.html` dentro del directorio LOCAL que ya contiene `vendor/` y `bundles/`, sin tocar el index.html activo.
3. Desde `delivery/`:

```powershell
python install_four_pass_sparse.py --viewer "E:/EdgeLab/viewer/nt8_bridge/index_fp4_base_3913149.html" --out "E:/EdgeLab/viewer/nt8_bridge/index_four_pass_review.html"
```

4. Servir esa copia con el servidor HTTP habitual del visor, no un archivo abierto sin servidor. Abrir `index_four_pass_review.html?asset=ID&tf=tick_25`.
5. Botón **4pasadas**: cargar ticks JSONL y Buscar/reiniciar, o importar una capa ya producida con el `asset` exacto del visor. `Inicio UTC` permite un punto manual; comienza con referencia fría y aprende dentro del prefijo seleccionado. No backfill de zonas completadas antes del soporte mínimo.
6. Deben coincidir activo, instrumento, contrato y tick. **El dibujo queda bloqueado hasta confirmar alineación raw↔bundle.** Offset sólo cambia dibujo, no detección ni timestamp original. No certifica el reloj financiero.
7. El rectángulo comienza en la disponibilidad de la cuarta salida, no aparece antes. Las cuatro visitas quedan en el JSON para revisión. El contador no depende de zoom/TF.

Si el visor de entrada difiere del hash auditado, installer falla cerrado; no forzarlo sobre tu copia dirty. Un archivo de módulo de otro escritor o una copia destino existente tampoco se sobrescribe.

## Tests

```powershell
node test_four_pass_sparse.cjs
node test_four_pass_integration.cjs
python test_four_pass_install.py
```

46 tests dirigidos (31 núcleo,9 puente/worker,6 instalación); no suite completa ni QA visual de navegador real. Tests regeneran fixtures `synthetic_*`: **SYNTHETIC_QA, no datos de mercado**.

## Evidencia y pendientes

Evidencia histórica v0.1, no aplicable al mínimo nuevo: dos smokes target-free: primeros200.000ticks serializados de MNQ09-25 y RTY12-25; el detector encontró una zona y se detuvo en22.148 y40.631ticks consumidos respectivamente. Auditoría independiente reconstruyó sus4pasadas desde raw. No son sesiones completas, trades, frecuencia diaria ni utilidad predictiva.

Pendiente LOCAL: inspeccionar el overlay realmente renderizado y confirmar geometría contra la captura; reloj del bundle; continuidad/fuentes raw; tiempo activo de negociación; censo de tiempo hasta primera zona con inicios explícitos, varias sesiones/activos. No ajustar contra retornos; conservar cambios de parámetros como versiones explícitas.

Sin outcomes, modelos, P&L, raw público o modificación de IPC/L2. Límite4096candidatas y2millones de prints por impulso: abstención explícita, nunca expiración silenciosa. Es instrument-neutral en coordenadas de ticks; **no está calibrado para todos los instrumentos**.

## Procedencia de esta revisión

Anterior v0.1: 41f221cd79bef33b7419d3304b17ac2ab7a2a76d. Evidencia v0.2 separada en evidence_v02.json. La capa real sin zona permanece privada; se publican sólo los conteos y hashes. El intento del auditor geométrico antiguo asumía una zona y falló sobre null; se registró como NO APLICABLE y se verificaron de forma independiente conteo, orden, dominio y reconciliación del prefijo. No se cambió el detector para corregir ese fallo del auditor.
