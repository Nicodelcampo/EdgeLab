"""Roles LLM del agente (F2 del plan PLAN_WORKER_SV1.md). El LLM RESPONDE, nunca orquesta.

Cada rol se invoca headless con `claude -p` (suscripción, no API key), salida validada contra un JSON Schema,
sin herramientas, sin MCP y sin configuración de usuario. Todo queda en un registro `llm_calls` (SQLite):
rol, modelo, hash de entrada y salida, tokens, costo informado y estado.

Reglas que este módulo hace cumplir, no el prompt:
- Ningún rol recibe credenciales, rutas locales ni métricas privadas: `sanitize` falla cerrado.
- Una salida que no valida se reintenta una vez; después queda `LLM_INVALID_OUTPUT` y el ciclo sigue.
- Idempotencia: la misma (rol, entrada) ya respondida no se vuelve a pagar.
- Gobernador (topes subidos el 2026-11-08 por decisión de Nico: plan Max y más corridas por día): tope diario de llamadas por rol y bloqueo hasta el reset ante límite de la suscripción.
- Ninguna salida de un rol es evidencia: es texto estructurado que el orquestador puede usar o descartar.
"""
from __future__ import annotations
import dataclasses, hashlib, json, os, re, sqlite3, subprocess, time
from pathlib import Path

# Modelos y topes: FUENTE ÚNICA `config/autopilot/AGENTES.json` (edgelab/autopilot/agentes.py). Acá sólo viven el esquema de salida
# y la consigna de cada rol; cada llamada registra el modelo exacto. La configuración (`modelos`) queda para excepciones.
from edgelab.autopilot import agentes as _AG
HAIKU, SONNET, OPUS, FABLE = (_AG.tabla()["modelos"][k]["id"] for k in ("haiku", "sonnet", "opus", "fable"))
SECRET = re.compile(r"(KGAT_|gho_|ghp_|github_pat_|sk-ant-|BEGIN [A-Z ]*PRIVATE KEY|KAGGLE_KEY|password|passwd|secret)", re.I)
LOCAL_PATH = re.compile(r"(^|[\s'\"])(/(etc|home|opt|var|root|mnt)/|[A-Za-z]:[\\/])")
PRIVATE_KEYS = {"holdout", "private", "d2", "secrets", "credentials", "token"}


def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}

S = {"type": "string", "maxLength": 2000}
ROLES = {
    "lector": dict(schema=_obj({
        "familias": {"type": "array", "maxItems": 50, "items": _obj({"familia": S, "resumen": S, "sobrevivientes": {"type": "integer"}})},
        "tres_lineas": S}),
        system="Resumís resultados de corridas de investigación. Sin juicio ni recomendaciones: sólo lo que dicen los números recibidos."),
    "bibliotecario": dict(schema=_obj({
        "fichas": {"type": "array", "maxItems": 12, "items": _obj({"ref": S, "afirma": S, "a_favor_o_en_contra": {"enum": ["a_favor", "en_contra", "neutral"]}})},
        "vacios": {"type": "array", "maxItems": 10, "items": S}}),
        system="Armás fichas de literatura a partir de los pasajes recibidos. La literatura nunca es evidencia propia; citá siempre la ref."),
    "cronista": dict(schema=_obj({"resumen_sala": S, "aporte_al_referente": S}),
        system="Redactás el resumen del ciclo para la sala, en español rioplatense, con los números exactamente como vienen. No inventes cifras."),
    "proponente": dict(schema=_obj({
        "familia": S, "mecanismo": S, "prediccion": S, "refutacion": S,
        "parametros_libres": {"type": "array", "maxItems": 3, "items": S}, "refs": {"type": "array", "maxItems": 10, "items": S},
        "pedido_codigo": S}, required=["familia", "mecanismo", "prediccion", "refutacion", "parametros_libres", "refs"]),
        system="Proponés UNA familia de hipótesis falsable: o una hipótesis puntual con a lo sumo 3 parámetros libres, o un BARRIDO MASIVO (millones de variantes) que declara todas sus perillas y cuenta todas sus celdas, sobre el conductor genérico (edgelab/research/grilla_generica.py) y con indicadores PASS de config/autopilot/indicadores.json o propios causales. Si la familia necesita una primitiva, un detector o un experimento que todavía no existe, describilo en pedido_codigo (qué hace, con qué datos, qué controles) y lo escribe el programador; si no hace falta, dejalo vacío. Para miles de variantes de una misma idea preferí la grilla masiva (docs/research/GUIA_GRILLA_MASIVA.md). Ponderá TODO el paquete: tablero, fichas del research propio, del cerebro y de papers; citá en refs las fichas que usaste (su campo ref). Lo ya medido o retirado no se repropone; los papers no son evidencia propia. ORDEN DE PRIORIDAD (criterio del dueño: centrar el esfuerzo en lo más valioso ya descubierto): primero indagar una PISTA_VIVA de nucleo_proyecto.factores_con_ventaja; después aplicar una PALANCA_DE_DISENO a una idea con motivo económico; recién después una familia nueva. Nada de lo que figura en NO_REPETIR se propone igual. Seguí nucleo_proyecto.metodo_de_investigacion: decí en qué paso estás (E0 sin retornos, hipótesis con control que comparta la condición, contexto, réplica) y qué produce; sin E0 previo no propongas nada con retornos; incluí las SUGERENCIAS de próximo análisis por ítem para el recomendador. Declará siempre la fricción en R esperada (fricción del instrumento / stop mediano): si supera ~0,08 R por operación, rediseñá antes de proponer. Si la idea es sobre eventos que ya tienen generador (nucleo_proyecto.banco_de_eventos), proponela como especificación del banco de eventos, juntando en una sola todas las ideas sobre la misma tabla."),
    "revisor": dict(schema=_obj({
        "decision": {"enum": ["PROMOTE", "KILL", "DERIVE"]}, "razon": S, "regla_nueva": S}),
        system="Adjudicás una familia con métricas públicas. Sos independiente del proponente. Si vienen antecedentes (research propio y papers del proyecto, con ref), contrastá el borrador con ellos: si repite algo ya medido o muerto, o contradice un resultado propio sin explicarlo, KILL. Criterios del dueño: macro antes que micro (la fricción mata lo chico); un edge condicionado a régimen vale si el régimen se detecta en tiempo real y está pre-registrado; queremos edges ACTUALES: que una idea haya fallado en datos viejos no es motivo de KILL si la propuesta mide lo reciente con ventana declarada antes y confirma hacia adelante; preferí lo que diversifica una cartera de varias estrategias. KILL también (errores K4–K9 del núcleo): grilla con retornos de más de 500 celdas sin un E0 sin retornos previo que la reduzca por regla mecánica; pre-registro que no declara la fricción en R esperada o que supera 0,08 R por operación sin rediseñar el stop; vigencias en barras en vez de segundos; detector nuevo sin test de causalidad por prefijo; P&L propuesto sin un paso previo de información contra placebo. También KILL si falta el control que comparte la condición del evento o la regla mecánica de elección escrita antes (metodo_de_investigacion). KILL a una especificación del banco de eventos sin preflight en verde o que reuse la mitad B de una familia y ventana. Ante la duda, KILL o DERIVE, nunca PROMOTE."),
    # Segunda opinión SÓLO ante un PROMOTE del revisor: otro modelo, otra consigna, sin ver la razón del primero.
    "revisor2": dict(schema=_obj({
        "decision": {"enum": ["PROMOTE", "KILL", "DERIVE"]}, "razon": S, "riesgo_principal": S}),
        system="Sos un segundo revisor escéptico e independiente. Recibís un pre-registro, métricas públicas y antecedentes del proyecto. Buscá activamente por qué NO debería lanzarse: repetición de algo ya medido, multiplicidad NO contada o no filtrada (un barrido masivo con todas sus celdas registradas, tamiz, Romano-Wolf y réplica no es multiplicidad excesiva), fricción que gana, sesgo de selección, look-ahead. Sólo PROMOTE si no encontrás un motivo concreto. Ante la duda, KILL."),
    # Auditor post-corrida: compara lo corrido contra lo pre-registrado. Los chequeos mecánicos ya vienen hechos.
    "auditor": dict(schema=_obj({
        "veredicto": {"enum": ["CONFORME", "DESVIO", "SOSPECHA_FUGA"]},
        "desvios": {"type": "array", "maxItems": 10, "items": S}, "razon": S}),
        system="Auditás una corrida terminada contra su pre-registro. Recibís el texto del pre-registro, la especificación lanzada, la decisión numérica y los chequeos mecánicos. Marcá DESVIO si se corrió algo distinto de lo pre-registrado (pruebas no planeadas, otra métrica, otro período, otra regla de decisión) y SOSPECHA_FUGA si algo sugiere uso de datos del holdout o de información futura. No reinterpretes los números ni opines sobre si el efecto es interesante."),
    # Abogado del diablo: sólo sobre hallazgos (hit). Propone la explicación no-edge más plausible y cómo refutarla.
    "abogado": dict(schema=_obj({
        "explicacion_alternativa": S, "tipo": {"enum": ["artefacto", "look_ahead", "costos", "multiplicidad", "regimen", "datos", "otro"]},
        "prueba_refutadora": S, "gravedad": {"enum": ["baja", "media", "alta"]}}),
        system="Recibís un hallazgo exploratorio (pasó Holm) con su pre-registro y antecedentes. Formulá la explicación NO-edge más plausible (artefacto de microestructura, look-ahead, costos, multiplicidad, régimen, datos) y la prueba concreta y barata que la refutaría. No digas si es un edge."),
}


def configurar_modelos(modelos: dict | None, excepciones: dict | None = None) -> None:
    """La fuente de modelos es `config/autopilot/AGENTES.json`: se actualiza sola con el código. El bloque `modelos` que quedó en la
    configuración de los servidores (copiado de una plantilla vieja) se IGNORA con un aviso, para que cambiar un modelo no exija
    tocar el servidor. Una excepción deliberada va en `modelos_excepcion`: {"revisor2": "<id>"}. Rol desconocido = error."""
    if modelos: print("aviso: el bloque `modelos` de la configuración se ignora (fuente: config/autopilot/AGENTES.json); usar `modelos_excepcion` si es deliberado")
    for rol, m in (excepciones or {}).items():
        if rol not in ROLES: raise ValueError(f"rol desconocido en modelos_excepcion: {rol}")
        ROLES[rol]["model"] = str(m)

ROLES["meta_analista"] = dict(schema=_obj({
    "factores": {"type": "array", "maxItems": 12, "items": _obj({
        "factor": S, "evidencia": S, "efecto_r": S, "donde": S, "confianza": {"enum": ["baja", "media", "alta"]},
        "siguiente_indagacion": S})},
    "que_no_repetir": {"type": "array", "maxItems": 8, "items": S},
    "prioridad_siguiente": S}),
    system="Sos el meta-analista de EdgeLab. Recibís el resultado de una campaña cerrada (celdas, canales, costos, R) y el registro vigente de factores con ventaja. Extraé QUÉ factor aportó la ventaja o la pérdida (horario, activo, stop, filtro, régimen, dirección), con el número en R y la referencia al archivo; distinguí efecto de selección y de fricción. Para cada factor decí la indagación siguiente más barata que lo confirmaría o lo mataría en datos no usados. Un resultado nulo con potencia también es un factor: decí qué no repetir. Si la campaña dejó RECOMENDACIONES_*.md (edgelab/research/recomendador.py), partí de ellas: las INDAGAR y CONFIRMAR son tus factores candidatos, con su próximo análisis. Esperá efectos chicos: tu trabajo es la pregunta siguiente que acerque al mecanismo (dónde se concentra, qué lo explica, qué lo anula). Si la campaña cambió la forma de medir respecto de corridas anteriores, decilo y nombrá qué familias habría que re-medir (docs/research/CAMBIOS_DE_MEDICION.jsonl). No inventes cifras ni promuevas nada: esto ordena la investigación, no es evidencia.")
for _r in ROLES:                                                    # modelo, tope y timeout: de AGENTES.json
    _d = _AG.rol(_r); ROLES[_r].update(model=_d["modelo"], daily_cap=_d["tope_diario"], timeout=_d["timeout_s"])


class UnsafeInput(ValueError):
    pass


def sanitize(payload, _path="$"):
    """Falla cerrado si la entrada de un rol trae secretos, rutas locales o claves privadas."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            if str(k).lower() in PRIVATE_KEYS or str(k).lower().startswith("private"):
                raise UnsafeInput(f"clave privada en la entrada: {_path}.{k}")
            sanitize(v, f"{_path}.{k}")
    elif isinstance(payload, list):
        for i, v in enumerate(payload):
            sanitize(v, f"{_path}[{i}]")
    elif isinstance(payload, str):
        if SECRET.search(payload):
            raise UnsafeInput(f"posible secreto en {_path}")
        if LOCAL_PATH.search(payload):
            raise UnsafeInput(f"ruta local en {_path}")
    return payload


def _digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def claude_cli(prompt, *, model, schema, system, timeout=600, **_):
    """La única llamada real. argv fijo, sin shell, sin herramientas, MCP ni settings de usuario. Entorno mínimo."""
    env = {k: os.environ[k] for k in ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "APPDATA", "LOCALAPPDATA", "CLAUDE_CODE_OAUTH_TOKEN") if k in os.environ}
    # El prompt va por la ENTRADA ESTÁNDAR: con el núcleo de contexto pesa ~100 KB y un argumento de más de 128 KB no arranca (E2BIG).
    argv = ["claude", "-p", "--model", model, "--output-format", "json", "--json-schema", json.dumps(schema),
            "--system-prompt", system, "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"]
    r = subprocess.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env, shell=False)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"is_error": True, "subtype": "cli_error", "result": (r.stdout + r.stderr)[-500:]}


class RoleRunner:
    def __init__(self, ledger_path, cli=claude_cli, clock=time.time):
        self.path, self.cli, self.clock = Path(ledger_path), cli, clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS llm_calls (id INTEGER PRIMARY KEY, ts REAL, day TEXT, role TEXT, model TEXT, "
                       "in_sha TEXT, out_sha TEXT, status TEXT, tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, output TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS governor (role TEXT PRIMARY KEY, blocked_until REAL)")

    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _day(self):
        return time.strftime("%Y-%m-%d", time.gmtime(self.clock()))

    def _log(self, db, role, model, in_sha, status, out=None, resp=None):
        u = (resp or {}).get("usage") or {}
        db.execute("INSERT INTO llm_calls (ts,day,role,model,in_sha,out_sha,status,tokens_in,tokens_out,cost_usd,output) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (self.clock(), self._day(), role, model, in_sha, _digest(out) if out is not None else None, status,
                    int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0)),
                    int(u.get("output_tokens", 0)), float((resp or {}).get("total_cost_usd") or 0), json.dumps(out) if out is not None else None))

    def call(self, role, payload, *, rate_limit_sleep=3600):
        spec = ROLES[role]
        sanitize(payload)
        in_sha = _digest([role, payload])
        with self._db() as db:
            hit = db.execute("SELECT output FROM llm_calls WHERE role=? AND in_sha=? AND status='OK' ORDER BY id DESC LIMIT 1", (role, in_sha)).fetchone()
            if hit:
                return dict(status="CACHED", output=json.loads(hit["output"]))
            row = db.execute("SELECT blocked_until FROM governor WHERE role=?", (role,)).fetchone()
            if row and row["blocked_until"] > self.clock():
                return dict(status="RATE_LIMITED", until=row["blocked_until"])
            n = db.execute("SELECT COUNT(*) FROM llm_calls WHERE role=? AND day=? AND status NOT IN ('CACHED','SKIPPED_CAP')", (role, self._day())).fetchone()[0]
            if n >= spec["daily_cap"]:
                self._log(db, role, spec["model"], in_sha, "SKIPPED_CAP")
                return dict(status="SKIPPED_CAP")
        prompt = "Entrada (JSON):\n" + json.dumps(payload, ensure_ascii=False)
        for attempt in (1, 2):
            try: resp = self.cli(prompt, model=spec["model"], schema=spec["schema"], system=spec["system"], timeout=spec.get("timeout", 600))
            except TypeError: resp = self.cli(prompt, model=spec["model"], schema=spec["schema"], system=spec["system"])   # cli de test sin timeout
            out = resp.get("structured_output")
            with self._db() as db:
                if resp.get("is_error") and (str(resp.get("api_error_status")) == "429" or "rate limit" in str(resp.get("result", "")).lower()):
                    until = self.clock() + rate_limit_sleep
                    db.execute("INSERT OR REPLACE INTO governor VALUES (?,?)", (role, until))
                    self._log(db, role, spec["model"], in_sha, "RATE_LIMITED", resp=resp)
                    return dict(status="RATE_LIMITED", until=until)
                if not resp.get("is_error") and out is not None and _valid(out, spec["schema"]):
                    self._log(db, role, spec["model"], in_sha, "OK", out, resp)
                    return dict(status="OK", output=out)
                self._log(db, role, spec["model"], in_sha, "INVALID_ATTEMPT_%d" % attempt, resp=resp)
                # El CLI del servidor puede no conocer todavía un modelo nuevo: se baja al respaldo de AGENTES.json y el ciclo sigue.
                txt = str(resp.get("result", "")).lower()
                if resp.get("is_error") and "model" in txt and any(k in txt for k in ("not found", "invalid", "not exist", "unknown", "access", "not available")):
                    resp_m = _AG.respaldo(role)
                    if resp_m and resp_m != spec["model"]:
                        self._log(db, role, spec["model"], in_sha, "MODELO_NO_DISPONIBLE", resp=resp); spec = dict(spec, model=resp_m)
        return dict(status="LLM_INVALID_OUTPUT")

    def usage(self, day=None):
        with self._db() as db:
            rows = db.execute("SELECT role, model, status, COUNT(*) n, SUM(tokens_in) ti, SUM(tokens_out) tout, SUM(cost_usd) c "
                              "FROM llm_calls WHERE day=? GROUP BY role, model, status", (day or self._day(),)).fetchall()
        return [dict(r) for r in rows]


def _valid(out, schema):
    try:
        import jsonschema
        jsonschema.validate(out, schema)
        return True
    except ImportError:
        return isinstance(out, dict) and set(schema.get("required", [])) <= set(out)
    except Exception:
        return False
