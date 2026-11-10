#!/usr/bin/env python3
"""Tabla de agentes del Debian (config/autopilot/AGENTES.json): imprime o regenera docs/autopilot/AGENTES.md.
  python tools/agentes.py            # imprime la tabla
  python tools/agentes.py --write    # regenera docs/autopilot/AGENTES.md y config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json
  python tools/agentes.py --probar DIR_ESTADO   # (servidor) una llamada mínima por modelo; escribe DIR_ESTADO/agentes_prueba.json.
                                                # Sólo vuelve a probar si cambió AGENTES.json. No corta el ciclo si falla.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import agentes as A  # noqa: E402


def probar(dir_estado: Path) -> dict:
    """Autoprueba tras una actualización de código: ¿el `claude` de este servidor acepta cada modelo y el prompt por stdin?"""
    import hashlib, time
    from edgelab.autopilot.roles import claude_cli
    huella = hashlib.sha256(A.RUTA.read_bytes()).hexdigest(); f = dir_estado / "agentes_prueba.json"
    if f.exists() and json.loads(f.read_text(encoding="utf-8")).get("huella") == huella: return json.loads(f.read_text(encoding="utf-8"))
    res = dict(huella=huella, ts=time.time(), modelos={})
    for alias, m in A.tabla()["modelos"].items():
        try:
            r = claude_cli("Respondé con ok=true.", model=m["id"], schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
                           system="Prueba de conectividad.", timeout=180)
            res["modelos"][alias] = dict(id=m["id"], ok=bool(not r.get("is_error") and r.get("structured_output") is not None), detalle=str(r.get("result", ""))[:200] if r.get("is_error") else "")
        except Exception as e: res["modelos"][alias] = dict(id=m["id"], ok=False, detalle=repr(e)[:200])
    dir_estado.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def main():
    if "--probar" in sys.argv:
        r = probar(Path(sys.argv[sys.argv.index("--probar") + 1]))
        malos = [k for k, v in r["modelos"].items() if not v["ok"]]
        print("agentes: modelos OK" if not malos else f"agentes: AVISO, modelos que este servidor no acepta (se usa el respaldo si lo hay): {malos}"); return
    md = A.markdown()
    if "--write" in sys.argv:
        (ROOT / "docs/autopilot/AGENTES.md").write_text(md, encoding="utf-8")
        from edgelab.autopilot.orquestador_multiagente import TOPOLOGIA_DEBIAN_V2
        (ROOT / "config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json").write_text(json.dumps(TOPOLOGIA_DEBIAN_V2, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("escrito docs/autopilot/AGENTES.md y config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json")
    else: print(md)


if __name__ == "__main__":
    main()
