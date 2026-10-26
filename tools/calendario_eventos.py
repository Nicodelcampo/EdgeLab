"""Calendario as-of de eventos macro de EE. UU. (2026-10-26): baja las fechas oficiales y regenera
`edgelab/research/eventos_datos.py` (datos embebibles en los kernels de Kaggle, sin archivos aparte).

Fuentes primarias: ALFRED (Fed de St. Louis) para las fechas de publicación de CPI (rid 10) y Employment Situation/NFP (rid 50),
08:30 ET; la página de calendarios del FOMC de la Reserva Federal (día de la decisión = último día de la reunión, 14:00 ET; se
omiten los votos por notación). Son fechas PROGRAMADAS (no dato de mercado): incluir las futuras no toca el holdout.
  python tools/calendario_eventos.py            # muestra lo que bajaría
  python tools/calendario_eventos.py --write    # regenera el módulo (commitearlo junto con el cambio)
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "edgelab" / "research" / "eventos_datos.py"
ALFRED = "https://alfred.stlouisfed.org/release/downloaddates?rid={rid}&ff=txt"
FOMC = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
MESES = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September",
                                     "October", "November", "December"), 1)}
NY = ZoneInfo("America/New_York")


def _get(url: str) -> str:
    """curl (respeta el proxy del entorno y sigue redirecciones); urllib como respaldo si no hay curl."""
    import shutil, subprocess
    if shutil.which("curl"):
        return subprocess.run(["curl", "-sfL", "--max-time", "60", url], capture_output=True, text=True, check=True).stdout
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def _utc(d: dt.date, hh: int, mm: int) -> int:
    return int(dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=NY).timestamp())


def alfred(rid: int, desde: int) -> list[dt.date]:
    return [dt.date.fromisoformat(x) for x in re.findall(r"^(\d{4}-\d{2}-\d{2})\s*$", _get(ALFRED.format(rid=rid)), re.M) if int(x[:4]) >= desde]


def fomc(desde: int) -> list[dt.date]:
    s = _get(FOMC); partes = re.split(r"(\d{4}) FOMC Meetings", s); out = []
    for i in range(1, len(partes), 2):
        y = int(partes[i])
        if y < desde: continue
        for mes, dia in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', partes[i + 1], re.S):
            if "notation" in dia.lower(): continue
            m = next(v for k, v in MESES.items() if k.startswith(mes.split("/")[-1].strip()[:3])); d = int(re.findall(r"\d+", dia)[-1])
            out.append(dt.date(y, m, d))
    return sorted(set(out))


def generar(desde: int = 2022) -> str:
    filas = [(_utc(d, 8, 30), "CPI", d.isoformat()) for d in alfred(10, desde)]
    filas += [(_utc(d, 8, 30), "NFP", d.isoformat()) for d in alfred(50, desde)]
    filas += [(_utc(d, 14, 0), "FOMC", d.isoformat()) for d in fomc(desde)]
    filas.sort()
    cuerpo = "\n".join(f"    ({t}, {k!r}, {f!r})," for t, k, f in filas)
    return ('"""GENERADO por tools/calendario_eventos.py (no editar a mano). Eventos macro de EE. UU.: (t_utc_s, tipo, fecha ET).\n'
            f'Fuentes: ALFRED rid 10 (CPI) y 50 (NFP), 08:30 ET; calendario FOMC de la Fed, 14:00 ET. Generado {dt.date.today()}."""\n'
            f"EVENTOS = (\n{cuerpo}\n)\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); ap.add_argument("--desde", type=int, default=2022)
    a = ap.parse_args(); txt = generar(a.desde)
    if a.write: DESTINO.write_text(txt, encoding="utf-8"); print(f"escrito {DESTINO} ({txt.count(chr(10)) - 4} eventos)")
    else: sys.stdout.write(txt)


if __name__ == "__main__":
    main()
