# Mensaje para el dueño del Debian — 2026-10-19

Estado: BORRADOR — se envía recién cuando el PR #123 esté mergeado en foundation con CI en verde y el SHA del merge reemplace `<SHA_DEL_MERGE>`.

---

Hola. Te paso las novedades del agente de EdgeLab para el Debian y lo que necesito que evalúes de tu lado.

**Qué cambió**
- **El agente ahora consulta todo lo que sabe el proyecto, y deja registrado qué usó.** Indexa una vez por día el Brain, más de 400 papers, el research propio y los registros de pruebas. Cada propuesta guarda con qué fuentes exactas se tomó.
- **Varios modelos, cada uno con un rol, y el código sigue mandando.** Opus propone, revisa y busca explicaciones alternativas a los hallazgos. Sonnet hace una segunda revisión independiente y audita cada corrida contra su pre-registro. Haiku arma los resúmenes. Para promover hacen falta los dos revisores.
- **Canal de pedidos.** Cuando el agente necesita algo que solo una persona puede dar, lo pide por la sala. Por ejemplo: datos que faltan en Kaggle, una exportación de NT8, una credencial o una decisión. Cada pedido tiene un id. Se responde con `resuelto <id> [nota]` y se listan los abiertos con `pedidos`. Si queda más de 72 h sin respuesta, el vigilante avisa.
- **Operación:**
  - un vigilante revisa cada 30 min y avisa si algo se cae (opcional: aviso al celular con ntfy);
  - la sala ya no puede levantar una pausa puesta desde la consola;
  - la base de corridas se respalda una vez por día;
  - cada pre-registro se publica en GitHub antes de lanzar;
  - el código queda fijado a un commit revisado.

**Cambios en la instalación (solo si ya instalaste)**
1. Reinstalar desde la rama viva `foundation/f0b-compatibility-probe`, fijado al commit revisado: `sudo CODE_REF=<SHA_DEL_MERGE> bash deploy/debian/install.sh`. Si ya existe `/etc/edgelab/candidates.json`, el instalador lo migra a `/var/lib/...`.
2. La deploy key de GitHub también tiene que estar en el clon de código. Ver `deploy/debian/LEEME.md`, paso 4.
3. Activar el vigilante: `sudo systemctl enable --now edgelab-watchdog.timer`.
4. Opcional, para recibir avisos en el celular: agregar `EDGELAB_ALERT_URL=https://ntfy.sh/<tu-tópico>` en `/etc/edgelab/autopilot.env`.

**Plan de Claude y uso de créditos (para que evalúes)**
- Los modelos se usan con la suscripción, a través de `claude setup-token`. Nunca con una API key.
- **Lo más importante: la cuenta.** El agente consume del MISMO cupo que todo lo que hagas vos con esa suscripción. Si usás Claude a diario, el agente y tu uso propio compiten por el mismo cupo de Opus: en días de uso intenso tuyo, el agente se queda sin Opus (espera), y viceversa. Conviene una cuenta aparte para el agente. La decisión de plan y cuenta es tuya.
- Todo arranca apagado. Se enciende por etapas desde `/etc/edgelab/autopilot.json`:

| Etapa | Qué se enciende | Llamadas por día (estimación, no medición / techo de configuración) |
|---|---|---|
| 0–1 | ciclo numérico, sin modelos | 0 |
| 2 | auditor (Sonnet) + cronista (Haiku, solo en ciclos con novedades) | ~2–10 Sonnet y ~10–40 Haiku / techo 20 y 100 |
| 3 | + proponente (Opus) | +1–2 Opus / techo 6 |
| 4 | + promoción automática (2 revisores) + abogado | +2–8 Opus y +1–5 Sonnet / techo 16 Opus y 10 Sonnet |

- **Todas las cifras de esta sección son ESTIMACIONES mías, no mediciones.** Antes de elegir plan, mirá la primera semana el consumo real: `llm_calls.sqlite` registra cada llamada (rol, modelo, tokens) y el informe de uso lo resume por rol y por día.
- **Tokens (estimado):** cada llamada de Opus o Sonnet lleva unos 3–6 mil tokens de entrada y menos de mil de salida. Las de Haiku son chicas.
  - En la etapa 4, el uso realista es del orden de **50–150 mil tokens por día**, casi todo en Opus y Sonnet.
  - Son estimaciones mías, no mediciones. El consumo real queda registrado en `llm_calls.sqlite` y el informe de uso lo muestra por rol.
- **Mi recomendación (a confirmar con el consumo medido):**
  - Para las etapas 0 a 3 alcanza un plan Pro, siempre que no lo compartas con un uso intenso tuyo.
  - Para la etapa 4, o si la cuenta es compartida, conviene un **Max**, por el cupo de Opus.
  - Si llega al límite, el agente no se rompe: espera al reset y lo numérico sigue andando.
  - También se pueden cambiar modelos sin tocar código, con la clave `modelos` en la configuración. Por ejemplo, poner Sonnet como proponente para ahorrar cupo de Opus.
- **Kaggle:** el cómputo pesado sigue en Kaggle, con tope de 2 corridas por día (`max_per_day`) y el tope de la cuenta.

**Lo que falta y solo se hace en la máquina**
- Una prueba de punta a punta con una corrida barata.
- Tu decisión de plan o cuenta para los roles.

Cuando lo tengas, avisame el commit instalado y la salida del doctor (`tools/autopilot_doctor.py`).

Referencias: `docs/autopilot/ARQUITECTURA_MULTIAGENTE.md` · `docs/autopilot/RESOLUCION_REVISION_DEBIAN_20261019.md` · `deploy/debian/LEEME.md`
