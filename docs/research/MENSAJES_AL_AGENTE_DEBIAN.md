# Mensajes al agente del Debian

Estado: VIGENTE. Canal escrito desde la sesión en la nube de Nico (el agente del Debian no es alcanzable por mensajes entre sesiones).
Cada mensaje lleva fecha, remitente y origen. Lo más nuevo, arriba.

## 2026-10-27 — de Nico (transcripto por la sesión en la nube)

> «Auto corregí tus propios errores, ya que estás en modo prueba.»

Alcance, tal como lo entiende la sesión que lo transcribe (si hay duda, preguntale a Nico en la sala):
- Si algo que **vos** hiciste falla (un CI rojo por tu PR, un kernel desactualizado, un conductor caído, una campaña que no arranca),
  arreglalo y pusheá sin esperar confirmación, con causa raíz en el commit.
- No cambia lo que sigue siendo sólo humano (CLAUDE.md): gates/FDR/mandato/archivos protegidos (incluido el protocolo de apertura del
  holdout) y operar con dinero real.
- Errores conocidos a no repetir: `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (por ejemplo O6: tocar un módulo embebido
  obliga a `python tools/reconstruir_kernels.py`; O12: `python tools/docs_index.py --write` antes de commitear estado).
