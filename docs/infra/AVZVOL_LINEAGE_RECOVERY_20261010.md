# AVZVOL — recuperación de candidatos de procedencia

**Resultado: artefactos candidatos recuperados; consumo histórico y calidad NO certificados.**
Base de esta revisión: `92e8d12ab514a2385c12f4aea281de5aeb64f1cf`.
[Registro legible por agentes](../../config/research/avzvol_lineage_candidates_20261010.json).
Complementa la [auditoría original](AVZVOL_AUDIT_20261010.md) y la
[siguiente etapa](../research/AVZVOL_SIGUIENTE_ETAPA_20261010.md); no reemplaza resultados.

## Qué se recuperó

Se consultaron por MCP los notebooks **v1** `edgelab-avzvol-k1/k2/k3`, su código,
metadata y evidencia de output existente (run IDs `356884473`, `356884479`,
`356884484`). Los logs nombran una fuente por contrato, no su versión ni el hash
físico del archivo. La metadata enumera attachments sin versiones. Su
`last_run_time` no se utilizó para atribuir inputs: no coincide con el inicio
registrado en procedencia. El commit de `EDGELAB_CODE_COMMIT` es una declaración,
no una medición de los módulos importados.

Se descargaron explícitamente las siguientes versiones **candidatas**:

| Contratos nombrados por los logs | Dataset candidato | Versión recuperada |
|---|---|---|
| MNQ 09-25, 12-25, 03-26 | `nicolasbuttaro/edgelab-ticks-nt8-canonical` | 1 |
| MNQ 06-26, 09-26, 12-26 | `nicolasbuttaro/edgelab-ticks-nt8-reexport-20261005` | 2 |
| Selección de sesiones/fuentes | `nicolasbuttaro/edgelab-data-catalog` | 15 |
| Paquete Python candidato | `nicolasbuttaro/edgelab-code-avcl-fast` | 2 |

La versión 1 del re-export se describe como una carga incompleta (sólo README);
no se sustituyó por ella la versión 2. Existencia y fecha de publicación anteriores
al run no prueban qué se montó. No se hizo una selección mirando outcomes.

Los hashes del registro distinguen:

1. **Medidos:** bytes descargados de resolver, loader, metadatos, source del notebook
   y ZIP de código. El hash de transporte del ZIP no es el hash de un paquete montado.
2. **Declarados por el productor:** SHA de los seis parquets. Para canonical
   concuerdan `files.sha256` y `AUDIT_MANIFEST.json`; para re-export, README y
   manifiesto por contrato. Se verificó esa concordancia, **no se descargaron ni
   rehashearon los parquets**. Dos declaraciones coincidentes no son dos mediciones
   independientes ni certifican saneamiento.
3. **Ausentes:** versiones/hashes físicos por input y rutas/hashes de módulos en
   el run histórico. No se completaron esos campos por inferencia.

## Código candidato: se despejó una contradicción aparente

La descripción del bundle menciona `9926785a`; las notas de v2 mencionan
`ecc530a4`; el notebook declara `4e1e2693`. Esos textos no bastan para declarar
una regresión. Se comparó el bundle v2 recuperado con el árbol Git completo
`4e1e26930f9778f974a4dd4946977ac48b1725d8`.

La exploración AST de imports locales literales, incluyendo inicializadores de
paquete e imports dentro de funciones, encontró **22 módulos**: 8 idénticos byte
por byte; los restantes 14 idénticos tras reemplazar **sólo CRLF por LF**. El
registro conserva ambos SHA y ambos resultados, sin llamar «mismo hash» a la
igualdad normalizada. No se ejecutó ni importó código del ZIP.

Es una comprobación estática acotada: no acredita imports dinámicos, dependencias
externas, versiones realmente cargadas, orden/resolución de `sys.path` ni paridad
científica. La función de zonas de AVZVOL está además inlined en el source del
notebook; importar `run_full_fast` no prueba que se haya usado como detector.

## Resolver candidato y ruta legacy

Se recuperaron `RESOLVER.json` y `edgelab_data.py` de catalog v15 por versión
explícita; coinciden byte por byte con la copia candidata conservada localmente.
La elección original `groupby(dataset, file).size().idxmax()` se reconstruyó por
contador ordenado y, de forma independiente, por pandas sobre **metadatos**, sin
importar el loader. Los seis pares fuente/archivo elegidos concuerdan con los
slugs por contrato impresos en los logs. En este resolver candidato no hay
sesiones aprobadas de otro source para esos contratos: no se encontró evidencia
ahí de mezcla por el posterior uso de todas las fechas del contrato.

Esto no demuestra que v15 estuviera montado, que `_path` resolviera ese archivo
físico ni que las sesiones sean completas/líquidas. La búsqueda legacy permite
fallback por basename y los logs no guardan la ruta resuelta.

El runner abre una ventana con **45 días de warmup** anteriores a la primera
sesión seleccionada. La revisión futura debe cubrir todo el intervalo leído,
no sólo las fechas de eventos. La resta histórica de `Timedelta(days=45)` sobre
un timestamp ya localizado debe conservarse en la reconstrucción; no sustituirla
por una resta de fechas locales si atraviesa DST.

Los manifiestos del re-export declaran fechas locales NT8 `NO_DATA` y conservación
de filas viejas. Esas fechas no son directamente trade dates CME; contar `NO_DATA`
no mide cuántas sesiones analíticas quedaron truncadas. No se las eliminó, rellenó
ni tradujo como un gap de mercado demostrado. Exigen revisión explícita de
cobertura, calendario y procedencia, incluidos warmup y continuidad intrasesión.

## Criterio de cierre y próxima acción

R7/K8 siguen **abiertos**. Esta recuperación reduce incertidumbre documental,
no valida retroactivamente O5 controlado ni cuantifica sesgo.

Para cerrar custodia histórica hace falta evidencia existente del montaje/lectura
por run (si se puede recuperar): dataset/version, archivo físico, SHA de bytes,
resolver/loader y rutas+SHA importados. Si no existe, marcar el consumo histórico
**no verificable**; una nueva corrida con buenos manifests no puede certificar
qué consumió la antigua. No relanzar sólo para maquillar esa ausencia.

Antes de un contraste nuevo:

1. Aprobar una identidad nueva de revisión de desarrollo y su exposición; congelar
   inputs y ventanas, incluyendo warmup, con autoridad de campaña y holdout original.
2. Exigir selección física inequívoca; STOP ante basename ambiguo, versión sin pin
   o hash distinto. Capturar resolver/loader, módulos importados y dependencias reales
   en el runner nuevo antes del cálculo. **Este lote documenta el requisito; no lo
   conecta a lectores legacy ni crea una attestation histórica.**
3. Completar evaluación independiente MNQ de calendario, reloj, quotes, continuidad
   y selección por liquidez. Manifiestos autoemitidos y `approved` del resolver no
   son autorización científica. ES/NQ no certifican MNQ por analogía.
4. Congelar censo/soporte/calipers/escalas/censura/potencia/familia y presupuesto
   sin usar outcomes para elegirlos. Los campos pendientes de la spec siguen `null`.

**Sin nuevos ticks/precios, kernels, contrastes, P&L, holdout ni promoción.** Se
preservaron originales y planificación autónoma local. No se publican URLs firmadas,
credenciales, rutas privadas de PC ni contenido raw de calendario/precios.
