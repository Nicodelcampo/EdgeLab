"""Roles LLM del agente (F2 del plan PLAN_WORKER_SV1.md). El LLM RESPONDE, nunca orquesta.

Cada rol se invoca headless con `claude -p` (suscripción, no API key), salida validada contra un JSON Schema,
sin herramientas, sin MCP y sin configuración de usuario. Todo queda en un registro `llm_calls` (SQLite):
rol, modelo, hash de entrada y salida, tokens, costo informado y estado.

Reglas que este módulo hace cumplir, no el prompt:
- Ningún rol recibe credenciales, rutas locales ni métricas privadas: `sanitize` falla cerrado.
- Una salida que no valida se reintenta una vez; después queda `LLM_INVALID_OUTPUT` y el ciclo sigue.
- Idempotencia: la misma (rol, entrada) ya respondida no se vuelve a pagar.
- Gobernador: tope diario de llamadas por rol y bloqueo hasta el reset ante límite de la suscripción.
- Ninguna salida de un rol es evidencia: es texto estructurado que el orquestador puede usar o descartar.
"""
from __future__ import annotations
import dataclasses, hashlib, json, os, re, sqlite3, subprocess, time
from pathlib import Path

# Versiones FIJADAS (reproducibilidad: cada llamada registra el modelo exacto). Se pueden cambiar por configuración (`modelos`).
HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"
SECRET = re.compile(r"(KGAT_|gho_|ghp_|github_pat_|sk-ant-|BEGIN [A-Z ]*PRIVATE KEY|KAGGLE_KEY|password|passwd|secret)", re.I)
LOCAL_PATH = re.compile(r"(^|[\s'\"])(/(etc|home|opt|var|root|mnt)/|[A-Za-z]:[\\/])")
PRIVATE_KEYS = {"holdout", "private", "d2", "secrets", "credentials", "token"}


def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}

S = {"type": "string", "maxLength": 2000}
ROLES = {
    "lector": dict(model=HAIKU, daily_cap=200, schema=_obj({
        "familias": {"type": "array", "maxItems": 50, "items": _obj({"familia": S, "resumen": S, "sobrevivientes": {"type": "integer"}})},
        "tres_lineas": S}),
        system="Resumís resultados de corridas de investigación. Sin juicio ni recomendaciones: sólo lo que dicen los números recibidos."),
    "bibliotecario": dict(model=HAIKU, daily_cap=100, schema=_obj({
        "fichas": {"type": "array", "maxItems": 12, "items": _obj({"ref": S, "afirma": S, "a_favor_o_en_contra": {"enum": ["a_favor", "en_contra", "neutral"]}})},
        "vacios": {"type": "array", "maxItems": 10, "items": S}}),
        system="Armás fichas de literatura a partir de los pasajes recibidos. La literatura nunca es evidencia propia; citá siempre la ref."),
    "cronista": dict(model=HAIKU, daily_cap=100, schema=_obj({"resumen_sala": S, "aporte_al_referente": S}),
        system="Redactás el resumen del ciclo para la sala, en español rioplatense, con los números exactamente como vienen. No inventes cifras."),
    "proponente": dict(model=OPUS, daily_cap=6, schema=_obj({
        "familia": S, "mecanismo": S, "prediccion": S, "refutacion": S,
        "parametros_libres": {"type": "array", "maxItems": 3, "items": S}, "refs": {"type": "array", "maxItems": 10, "items": S}}),
        system="Proponés UNA familia de hipótesis falsable con a lo sumo 3 parámetros libres, usando sólo primitivas del registro recibido. Sin código. Ponderá TODO el paquete: tablero, fichas del research propio, del cerebro y de papers; citá en refs las fichas que usaste (su campo ref). Lo ya medido o retirado no se repropone; los papers no son evidencia propia."),
    "revisor": dict(model=OPUS, daily_cap=10, schema=_obj({
        "decision": {"enum": ["PROMOTE", "KILL", "DERIVE"]}, "razon": S, "regla_nueva": S}),
        system="Adjudicás una familia con métricas públicas. Sos independiente del proponente. Si vienen antecedentes (research propio y papers del proyecto, con ref), contrastá el borrador con ellos: si repite algo ya medido o muerto, o contradice un resultado propio sin explicarlo, KILL. Ante la duda, KILL o DERIVE, nunca PROMOTE."),
    # Segunda opinión SÓLO ante un PROMOTE del revisor: otro modelo, otra consigna, sin ver la razón del primero.
    "revisor2": dict(model=SONNET, daily_cap=10, schema=_obj({
        "decision": {"enum": ["PROMOTE", "KILL", "DERIVE"]}, "razon": S, "riesgo_principal": S}),
        system="Sos un segundo revisor escéptico e independiente. Recibís un pre-registro, métricas públicas y antecedentes del proyecto. Buscá activamente por qué NO debería lanzarse: repetición de algo ya medido, multiplicidad excesiva, fricción que gana, sesgo de selección, look-ahead. Sólo PROMOTE si no encontrás un motivo concreto. Ante la duda, KILL."),
    # Auditor post-corrida: compara lo corrido contra lo pre-registrado. Los chequeos mecánicos ya vienen hechos.
    "auditor": dict(model=SONNET, daily_cap=20, schema=_obj({
        "veredicto": {"enum": ["CONFORME", "DESVIO", "SOSPECHA_FUGA"]},
        "desvios": {"type": "array", "maxItems": 10, "items": S}, "razon": S}),
        system="Auditás una corrida terminada contra su pre-registro. Recibís el texto del pre-registro, la especificación lanzada, la decisión numérica y los chequeos mecánicos. Marcá DESVIO si se corrió algo distinto de lo pre-registrado (pruebas no planeadas, otra métrica, otro período, otra regla de decisión) y SOSPECHA_FUGA si algo sugiere uso de datos del holdout o de información futura. No reinterpretes los números ni opines sobre si el efecto es interesante."),
    # Abogado del diablo: sólo sobre hallazgos (hit). Propone la explicación no-edge más plausible y cómo refutarla.
    "abogado": dict(model=OPUS, daily_cap=6, schema=_obj({
        "explicacion_alternativa": S, "tipo": {"enum": ["artefacto", "look_ahead", "costos", "multiplicidad", "regimen", "datos", "otro"]},
        "prueba_refutadora": S, "gravedad": {"enum": ["baja", "media", "alta"]}}),
        system="Recibís un hallazgo exploratorio (pasó Holm) con su pre-registro y antecedentes. Formulá la explicación NO-edge más plausible (artefacto de microestructura, look-ahead, costos, multiplicidad, régimen, datos) y la prueba concreta y barata que la refutaría. No digas si es un edge."),
}


def configurar_modelos(modelos: dict | None) -> None:
    """Permite fijar otras versiones desde la configuración: {"revisor2": "claude-sonnet-5-5", ...}. Rol desconocido = error."""
    for rol, m in (modelos or {}).items():
        if rol not in ROLES: raise ValueError(f"rol desconocido en modelos: {rol}")
        ROLES[rol]["model"] = str(m)


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


def claude_cli(prompt, *, model, schema, system, timeout=600):
    """La única llamada real. argv fijo, sin shell, sin herramientas, MCP ni settings de usuario. Entorno mínimo."""
    env = {k: os.environ[k] for k in ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "APPDATA", "LOCALAPPDATA", "CLAUDE_CODE_OAUTH_TOKEN") if k in os.environ}
    argv = ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--json-schema", json.dumps(schema),
            "--system-prompt", system, "--tools", "", "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"]
    r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env, shell=False)
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
            resp = self.cli(prompt, model=spec["model"], schema=spec["schema"], system=spec["system"])
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
