# GC exact4 — mínimo local para Nico / Antigravity

No hace falta rediseñar el detector ni usar créditos de Claude para programar.
La nube auditó el paquete; faltan las velas originales para generar las capas
reales. Esta entrega automatiza ese paso local.

## 1. Preparación

- Un solo escritor en `E:\EdgeLab`. Verificar rama
  `foundation/f0b-compatibility-probe`, cambios locales y HEAD.
- Traer los nuevos archivos versionados sin pisar cambios locales. Si se usa el
  ZIP de entrega, copiar `tools/gc_exact4_review.py`,
  `viewer/nt8_bridge/gc_exact4_review_guard.js` y tests a sus rutas.
  `index.html` NO se copia ni se reemplaza.
- Descomprimir el ZIP privado del censo en `E:\gc_exact4_censo`.
- El bundle original debe estar en
  `E:\EdgeLab\viewer\nt8_bridge\bundles\GC_04-26_202602_25T_HFT.json`.
  Se exige SHA-256
  `1fe735ee2ede0998c74bfb4bea38526e89bc4b98849eea0d3137d330ddf9bae3`.
  NO editar la captura ni cambiar hashes para hacer pasar el chequeo.

## 2. Un comando desde E:\EdgeLab

```powershell
.\.venv\Scripts\python.exe tools\gc_exact4_review.py `
  --census-dir E:\gc_exact4_censo `
  --chart-bundle viewer\nt8_bridge\bundles\GC_04-26_202602_25T_HFT.json `
  --viewer-dir viewer\nt8_bridge `
  --install-safe-copy `
  --report E:\gc_exact4_review_local_v1.json
```

Si el módulo productor/resolver tiene cambios, el programa se abstiene:
revisar la procedencia, no relajar. Si algún hook del visor cambió, se abstiene
ANTES de escribir capas. No borrar cambios de otro escritor. Si una capa o
reporte ya existe, tampoco sobrescribe; revisar su hash antes de decidir otra
salida/cuarentena.

El programa verifica el hash exacto del bundle, serie, ventana y geometría de
los cuatro picos; crea capas `__exact4_c1` a `c4` y una copia
`index_gc_exact4.html`. Mantiene el `index.html` original y la capa C0 intactos.
No necesita cargar millones de grupos L2: sólo el bundle de velas y el censo.

## 3. Revisar

Usar el servidor local habitual. Si no está abierto:

```powershell
.\.venv\Scripts\python.exe viewer\nt8_bridge\server.py 8088
```

Abrir, cambiando `c1` por `c2`, `c3` o `c4`:

```text
http://127.0.0.1:8088/index_gc_exact4.html?asset=GC_04-26_202602_25T_HFT&tf=tick_25&solo=det&det=exact4_c1
```

Investigación → Revisar detecciones. Se conservan los cuatro miembros, los
juicios quedan en `labels/<activo>__exact4_c1.json`…`c4`, sin mezclar C0.
Cerrar el panel o usar Flotante para que no tape el patrón; S/N/espacio permiten
revisar sin dejarlo abierto. “Sí más larga” es un juicio humano, NO permiso para
extender el evento congelado.

Avisos esperados: `RAW PENDIENTE`, `DET lógico p4`, ausencia de tablero de trades.
El punto azul es el cierre de la barra de detección, no un fill en el umbral.
La cortina va después de `det_i`; NO certifica una revisión ciega porque el
dataset/escala pueden contener futuro y febrero ya fue visto.

## 4. Devolver a nube

- `E:\gc_exact4_review_local_v1.json`.
- Los juicios exportados y, si hay discrepancias, IDs/capturas de las zonas.
- Opcional: el bundle original privado para que la nube compruebe la paridad real.
- Para certificar disponibilidad: barras reconstruidas con filas y timestamps
  de publicación observados y procedencia raw. El bundle OHLC no los sustituye.

Los archivos con eventos, velas, precios y juicios son privados: NO git add,
NO publicar. El conversor no calcula retornos/TP/SL/MAE/MFE/costos. Hace falta
manifest + OK separado de Nico antes de cualquier investigación económica.

## Aporte al referente

El trabajo local restante es ejecutar el enlace y juzgar geometría, no volver
a programar exact4. Disponibilidad raw y potencia siguen pendientes.