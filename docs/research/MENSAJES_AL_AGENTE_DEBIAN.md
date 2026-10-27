# Mensajes al agente del Debian

Estado: VIGENTE. Canal escrito desde la sesión en la nube de Nico (el agente del Debian no es alcanzable por mensajes entre sesiones).
Cada mensaje lleva fecha, remitente y origen. Lo más nuevo, arriba.

## 2026-10-27 (01:55 UTC) — de Nico (redactado por la sesión en la nube): generador caído y estado sin publicar

1. **`edgelab-autopilot-generate.service` en `failed` desde el 26-oct 06:19.** El bug conocido del paso `propose` (`TypeError: dict() got
   multiple values for keyword argument 'lente'`) está arreglado desde el PR #127 (mergeado el 25-oct), que SV1 ya tiene (está en
   `87b11b78` o posterior). Con el código actual `propose` corre bien (probado en la nube con `proponente: true`). Lo más probable es que
   el `failed` sea de una corrida con código viejo y la unidad quedó marcada. Hacé:
   `sudo systemctl reset-failed edgelab-autopilot-generate.service && sudo systemctl start edgelab-autopilot-generate.service`
   y mirá `journalctl -u edgelab-autopilot-generate -n 50`. Si vuelve a fallar con otro error, arreglalo vos (causa raíz en el commit).
2. **PR #141 (sync_state: heartbeat.json) mergeado.** Actualizá con `update.sh` (con pausa, sin corrida en curso) para que el estado
   empiece a publicarse en `autopilot/state`; confirmá en el próximo ciclo que la rama aparece en GitHub.
3. Avisá en la sala cuando los dos estén en verde.

## 2026-10-27 (01:45 UTC) — de Nico (redactado por la sesión en la nube): todo junto

1. **Actualizá el código del SV1 a foundation con `update.sh`, ya** (con pausa y sin corrida en curso, como siempre). Trae los kernels
   pre-armados reconstruidos (`tools/kaggle_grilla/kernel_*.py`): sin ellos algunas etapas fallan o quedan desalineadas.
2. **El archivo de credencial lo revisa una persona, no vos** (tu clasificador lo bloquea y está bien que lo haga). Gonza o Nico
   corren en el SV1 estos dos comandos; ninguno imprime el token:
   ```
   sudo -u edgelab curl -sS -o /dev/null -w '%{http_code}\n' -H @/opt/edgelab/.kaggle_auth_header.nicobuttaro https://www.kaggle.com/api/v1/datasets/view/nicolasbuttaro/edgelab-holdout-sellado
   sudo awk '{print NR": "$1, $2, substr($3,1,5)"…", "largo="length($3)} END{print "lineas="NR}' /opt/edgelab/.kaggle_auth_header.nicobuttaro
   ```
   200 = resuelto. Si da 403 y la segunda no muestra exactamente una línea `Authorization: Bearer KGAT_…` (token nuevo) o
   `Authorization: Basic …` (clave vieja), hay que reescribir el archivo con ese formato.
3. **Vos sí podés** verificar (sin leer el archivo) que `EDGELAB_KAGGLE_OWNER=nicobuttaro` le llega al proceso que lanza los kernels de
   las tres campañas fijadas (U1-ZONAS-NQ, ZGAP-CFD, ZGAP-NQ): `embudo_runners.KaggleRunner._env`. Si no llega, arreglalo vos.
4. Cuando quede en 200, avisá en la sala y dejá que esas tres campañas se lancen con `nicobuttaro`.

## 2026-10-27 (01:35 UTC) — de Nico (redactado por la sesión en la nube): el 403 de `nicobuttaro` en `edgelab-holdout-sellado`

Nico dice que **el token de `nicobuttaro` está bien y lo tenés**. Y el dataset **ya está compartido**: desde la nube, con la credencial
de `nicobuttaro`, `datasets/view/nicolasbuttaro/edgelab-holdout-sellado` da **200** y la descarga da **302** (autorizada); lo mismo
`edgelab-zonas-u1` y `edgelab-liquid-ticks-20261014`. Lo más probable es que lo hayas probado antes de que Nico lo compartiera.

Qué hacer, en orden (sin preguntar; arreglá vos lo que encuentres):
1. **Repetí la prueba ahora**, con la cabecera de esa cuenta:
   `curl -sS -o /dev/null -w '%{http_code}\n' -H @/opt/edgelab/.kaggle_auth_header.nicobuttaro https://www.kaggle.com/api/v1/datasets/view/nicolasbuttaro/edgelab-holdout-sellado`
   Si da 200: listo, avisá en la sala y dejá que las campañas fijadas a `nicobuttaro` sigan su curso.
2. Si sigue en 403, revisá **el formato del archivo** (sin imprimir el token): tiene que ser exactamente una línea
   `Authorization: Bearer KGAT_...` (token nuevo) o `Authorization: Basic <base64 de usuario:clave>` (clave vieja), sin comillas ni
   saltos de línea extra. Un token KGAT con Basic, o usuario/clave con Bearer, falla.
3. Revisá **qué cabecera usa el servicio de verdad**: `tools/kaggle_auth.py` elige `<KAGGLE_AUTH_HEADER_FILE>.<EDGELAB_KAGGLE_OWNER>`
   sólo si `EDGELAB_KAGGLE_OWNER` llega al proceso (`embudo_runners._env`). Si la variable no llega, cae a la cabecera única (la de
   `nicolasbuttaro`) y un kernel de `nicobuttaro` se crea con la cuenta equivocada.
4. Si con todo eso sigue el 403, decilo en la sala con el código exacto y la URL (nunca el token).

## 2026-10-27 — de Nico (transcripto por la sesión en la nube)

> «Auto corregí tus propios errores, ya que estás en modo prueba.»

Alcance, tal como lo entiende la sesión que lo transcribe (si hay duda, preguntale a Nico en la sala):
- Si algo que **vos** hiciste falla (un CI rojo por tu PR, un kernel desactualizado, un conductor caído, una campaña que no arranca),
  arreglalo y pusheá sin esperar confirmación, con causa raíz en el commit.
- **Aclaración de Nico (2026-10-27): es todo autónomo.** Aprobar las corridas y abrir el holdout los decide el agente, con los
  protocolos en código (`edgelab/autopilot`, `edgelab/autopilot/holdout_apertura.py`), sin esperar a nadie. Lo único que CLAUDE.md
  deja fuera de eso es *modificar* esos protocolos y gates (FDR, mandato, archivos protegidos) y operar con dinero real.
- Errores conocidos a no repetir: `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (por ejemplo O6: tocar un módulo embebido
  obliga a `python tools/reconstruir_kernels.py`; O12: `python tools/docs_index.py --write` antes de commitear estado).
