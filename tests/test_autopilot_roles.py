"""Roles LLM con CLI falso: sin red, sin tokens."""
import pytest
from edgelab.autopilot.roles import RoleRunner, sanitize, UnsafeInput, ROLES


class FakeCLI:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
    def __call__(self, prompt, *, model, schema, system):
        self.calls.append((model, prompt))
        return self.replies.pop(0)

OK_CRON = {"is_error": False, "structured_output": {"resumen_sala": "ciclo sin lanzamientos", "aporte_al_referente": "ninguno"},
           "usage": {"input_tokens": 10, "cache_creation_input_tokens": 100, "output_tokens": 20}, "total_cost_usd": 0.01}


def runner(tmp_path, replies, t=[1_000_000.0]):
    cli = FakeCLI(replies)
    return RoleRunner(tmp_path / "llm.sqlite", cli=cli, clock=lambda: t[0]), cli, t


def test_ok_is_logged_and_cached(tmp_path):
    r, cli, _ = runner(tmp_path, [OK_CRON])
    assert r.call("cronista", {"ciclo": 1})["status"] == "OK"
    assert r.call("cronista", {"ciclo": 1})["status"] == "CACHED"          # misma entrada: no se paga dos veces
    assert len(cli.calls) == 1 and cli.calls[0][0] == "haiku"
    u = r.usage()
    assert any(x["status"] == "OK" and x["ti"] == 110 for x in u)

def test_invalid_output_retries_once_then_gives_up(tmp_path):
    bad = {"is_error": False, "structured_output": {"resumen_sala": "x"}}
    r, cli, _ = runner(tmp_path, [bad, bad])
    assert r.call("cronista", {"ciclo": 2})["status"] == "LLM_INVALID_OUTPUT"
    assert len(cli.calls) == 2

def test_rate_limit_blocks_role_until_reset(tmp_path):
    rl = {"is_error": True, "api_error_status": 429, "result": "rate limit"}
    r, cli, t = runner(tmp_path, [rl, OK_CRON])
    assert r.call("cronista", {"ciclo": 3})["status"] == "RATE_LIMITED"
    assert r.call("cronista", {"ciclo": 4})["status"] == "RATE_LIMITED"    # bloqueado: no llama
    assert len(cli.calls) == 1
    t[0] += 3601
    assert r.call("cronista", {"ciclo": 4})["status"] == "OK"

def test_daily_cap(tmp_path, monkeypatch):
    monkeypatch.setitem(ROLES["proponente"], "daily_cap", 1)
    good = {"is_error": False, "structured_output": {"familia": "f", "mecanismo": "m", "prediccion": "p", "refutacion": "r", "parametros_libres": [], "refs": []}}
    r, cli, _ = runner(tmp_path, [good])
    assert r.call("proponente", {"brain": "a"})["status"] == "OK"
    assert r.call("proponente", {"brain": "b"})["status"] == "SKIPPED_CAP"
    assert len(cli.calls) == 1 and cli.calls[0][0] == "opus"

@pytest.mark.parametrize("payload", [
    {"holdout": {"sharpe": 2}}, {"private_metrics": 1}, {"nota": "token KGAT_abc123"}, {"x": ["ghp_xxxxxxxx"]},
    {"ruta": "/etc/edgelab/autopilot.env"}, {"ruta": "C:/Users/yo/kaggle.json"}, {"ruta": "D:" + chr(92) + "datos"}, {"a": {"credentials": "x"}},
])
def test_unsafe_inputs_never_reach_the_model(tmp_path, payload):
    r, cli, _ = runner(tmp_path, [OK_CRON])
    with pytest.raises(UnsafeInput):
        r.call("cronista", payload)
    assert cli.calls == []

def test_sanitize_accepts_plain_research_text():
    assert sanitize({"familia": "racimos", "metricas": {"beta": -0.07, "n": 900}, "refs": ["Muravyev & Picard"]})
