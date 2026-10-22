import pytest
import json, os, subprocess, time
from pathlib import Path
from edgelab.autopilot import conocimiento as K
from edgelab.autopilot.daemon import Autopilot
from edgelab.autopilot.sala import aplicar_comandos
from edgelab.autopilot.promocion import escribir_atomico
import importlib.util, sys

ROOT = Path(__file__).resolve().parents[1]


def _repo(tmp):
    r = tmp / "repo"; (r / "docs/research/x").mkdir(parents=True); (r / "corpus/ssrn/Normalizado/documentos").mkdir(parents=True)
    (r / "MANDATO.md").write_text("edges netos para challenges\n", encoding="utf-8")
    (r / "docs/research/x/RESULTADO.md").write_text("reversión horaria en NQ: MEDIDO negativo\nNO MEDIDO: costos reales\n", encoding="utf-8")
    (r / "corpus/ssrn/Normalizado/documentos/0001_intraday.txt").write_text("intraday seasonality of returns in index futures\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=r); subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "."], cwd=r)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], cwd=r)
    return r


def test_indice_trazable_y_busqueda(tmp_path):
    r = _repo(tmp_path); st = tmp_path / "st"; st.mkdir(); (st / "trial_registry.jsonl").write_text('{"family":"NQ reversión horaria"}\n', encoding="utf-8")
    idx = K.indexar(r, st)
    docs = {d["id"]: d for d in idx["docs"]}
    assert docs["docs/research/x/RESULTADO.md"]["tipo"] == "research" and docs["docs/research/x/RESULTADO.md"]["commit"]
    assert docs["corpus/ssrn/Normalizado/documentos/0001_intraday.txt"]["tipo"] == "papers"
    assert docs["estado:trial_registry.jsonl"]["tipo"] == "registro" and docs["estado:trial_registry.jsonl"]["commit"] is None
    assert all(len(d["sha256"]) == 64 for d in idx["docs"])
    hit = K.buscar(idx, "reversión horaria NQ", 2)[0]
    assert hit["doc"] in ("docs/research/x/RESULTADO.md", "estado:trial_registry.jsonl") and hit["sha256"]
    ctx = K.contexto_para(idx, "intraday seasonality reversión NQ")
    assert any(f["tipo"] == "papers" for f in ctx["fichas"]) and any(f["tipo"] == "research" for f in ctx["fichas"])
    assert any("RESULTADO.md" in v for v in ctx["vacios"])
    K.guardar(idx, st / "b.json"); assert "_inv" not in K.cargar(st / "b.json") and K.manifiesto(idx)["huella"] == idx["huella"]


def test_dos_interruptores(tmp_path):
    ap = Autopilot(tmp_path / "root", executor=None, cfg={"kill_switch": str(tmp_path / "PAUSE")})
    consola, sala = ap.pause_files()
    assert sala.name == "PAUSE_SALA" and not ap._paused()
    consola.touch(); (tmp_path / "root").mkdir(exist_ok=True)
    (tmp_path / "root/sala_inbox.jsonl").write_text(json.dumps({"autor": "nico", "texto": "reanudar"}) + "\n"); os.chmod(tmp_path / "root/sala_inbox.jsonl", 0o644)
    aplicar_comandos(tmp_path / "root", sala, ["nico"], lambda: {})
    assert consola.exists() and ap._paused()                       # la sala no levanta la pausa de consola


@pytest.mark.skipif(os.name != "posix", reason="permisos POSIX: en Windows st_mode no refleja las ACL (corre en el CI de Ubuntu)")
def test_inbox_escribible_por_otros_se_ignora(tmp_path):
    ks = tmp_path / "PAUSE_SALA"; ib = tmp_path / "sala_inbox.jsonl"
    ib.write_text(json.dumps({"autor": "nico", "texto": "pausa"}) + "\n"); os.chmod(ib, 0o666)
    out = aplicar_comandos(tmp_path, ks, ["nico"], lambda: {})
    assert out[0][0] == "inbox_inseguro" and not ks.exists()


def test_escritura_atomica(tmp_path):
    p = tmp_path / "c.json"; escribir_atomico(p, [{"a": 1}]); assert json.loads(p.read_text(encoding="utf-8")) == [{"a": 1}] and not (tmp_path / "c.json.tmp").exists()


def test_watchdog(tmp_path):
    spec = importlib.util.spec_from_file_location("wd", ROOT / "tools/autopilot_watchdog.py"); wd = importlib.util.module_from_spec(spec); spec.loader.exec_module(wd)
    st = tmp_path / "var/state/runs"; st.mkdir(parents=True); now = time.time()
    (st / "heartbeat.json").write_text(json.dumps({"ts": now - 7200, "send_uncertain": ["r1"]}))
    al = wd.revisar(st, 3600, now, systemctl=False); claves = {a[0] for a in al}
    assert {"latido_viejo", "envio_incierto"} <= claves
    assert len(wd.emitir(st, al, now)) == len(al) and wd.emitir(st, al, now + 60) == []     # no repite
    assert (st / "alertas.jsonl").exists() and "ALERTA" in (st / "sala_outbox.jsonl").read_text(encoding="utf-8")
