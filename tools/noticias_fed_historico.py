"""Transcribe las fechas FOMC 2008-2022 de las páginas oficiales de la Fed a `config/noticias/crudo/fed_2008_2022.txt`.

Fuentes (federalreserve.gov responde a curl, a diferencia de bls.gov):
  https://www.federalreserve.gov/monetarypolicy/fomchistorical<año>.htm   (2008-2020)
  https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm        (2021-2022)
De cada reunión: comunicado (`monetaryYYYYMMDDa`), conferencia de prensa (`fomcpresconfYYYYMMDD`) y minutas
(«Released <Mes> DD, YYYY»). La página no trae la hora: se aplica la convención de la Fed y se anota cuál
(`tools/noticias_calendario.py` la convierte a UTC):
  comunicado  14:15 ET hasta 2012 (12:30 ET en reuniones con conferencia abr-2011 → dic-2012); 14:00 ET desde 2013
  conferencia 14:15 ET en 2011-2012; 14:30 ET desde 2013
  minutas     14:00 ET
Las reuniones no programadas se listan con `NO_PROGRAMADA` para verificar su hora aparte (no siguen la convención).

  python tools/noticias_fed_historico.py --bajar <carpeta>   # baja las páginas (no se versionan)
  python tools/noticias_fed_historico.py --carpeta <carpeta> # escribe la transcripción
"""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SALIDA = ROOT / "config" / "noticias" / "crudo" / "fed_2008_2022.txt"
URL_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{}.htm"
URL_CAL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


def bajar(carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for y in range(2007, 2021):
        subprocess.run(["curl", "-s", "-m", "30", "-A", "Mozilla/5.0", "-o", str(carpeta / f"fomc{y}.htm"), URL_HIST.format(y)], check=True)
    subprocess.run(["curl", "-s", "-m", "30", "-A", "Mozilla/5.0", "-o", str(carpeta / "fomccal.htm"), URL_CAL], check=True)
    for n, u in (("testimony.json", "https://www.federalreserve.gov/json/ne-testimony.json"), ("speeches.json", "https://www.federalreserve.gov/json/ne-speeches.json")):
        subprocess.run(["curl", "-s", "-m", "30", "-A", "Mozilla/5.0", "-o", str(carpeta / n), u], check=True)


def _bloques(html: str) -> list[str]:
    """Un bloque de HTML por reunión."""
    partes = re.split(r'<h5(?: class="panel-heading[^"]*")?>|<div class="(?:fomc-meeting--shaded )?row fomc-meeting"', html)
    return partes[1:]


def _hora_comunicado(fecha: str, con_conferencia: bool) -> str:
    if fecha >= "20130101":
        return "14:00"
    if con_conferencia and fecha >= "20110401":
        return "12:30"
    return "14:15"


def transcribir(carpeta: Path) -> list[str]:
    out, vistos = [], set()
    paginas = [(y, (carpeta / f"fomc{y}.htm").read_text(encoding="utf-8", errors="replace")) for y in range(2007, 2021)]   # 2007: minutas publicadas en ene-2008
    cal = (carpeta / "fomccal.htm").read_text(encoding="utf-8", errors="replace")
    for y in (2021, 2022):
        a = cal.index(f"{y} FOMC Meetings"); b = cal.find("FOMC Meetings", a + 20)
        paginas.append((y, cal[a:b if b > 0 else None]))
    for y, html in paginas:
        for bl in _bloques(html):
            titulo = re.sub(r"<[^>]+>", " ", bl[:200])
            no_prog = bool(re.search(r"unscheduled|conference call|\(notation vote\)", titulo, re.I))
            com = sorted(set(re.findall(r"(?:pressreleases/monetary|press/monetary/)(\d{8})[a-z]\.htm", bl)))
            conf = sorted(set(re.findall(r"fomcpresconf(\d{8})\.htm", bl)))
            mins = re.findall(r"Released\s+([A-Z][a-z]+\.? \d{1,2}, \d{4})", bl)
            for f in com:
                if not f.startswith(str(y)):
                    continue
                etiqueta = "NO_PROGRAMADA" if no_prog else _hora_comunicado(f, bool(conf))
                lin = f"FOMC_DECISION {f} {etiqueta}"
                if lin not in vistos:
                    vistos.add(lin); out.append(lin)
            for f in conf:
                if f.startswith(str(y)):
                    lin = f"FOMC_PRESS_CONFERENCE {f} {'14:15' if f < '20130101' else '14:30'}"
                    if lin not in vistos:
                        vistos.add(lin); out.append(lin)
            for m in mins:
                m = m.replace(".", "").replace("Sept ", "Sep ")
                f = None
                for fmt in ("%B %d, %Y", "%b %d, %Y"):
                    try:
                        f = datetime.strptime(m, fmt).strftime("%Y%m%d"); break
                    except ValueError:
                        pass
                if f is None:
                    raise ValueError(f"fecha de minutas no reconocida: {m}")
                if "2008" <= f[:4] <= "2022":
                    lin = f"FOMC_MINUTES {f} 14:00"
                    if lin not in vistos:
                        vistos.add(lin); out.append(lin)
    return sorted(out, key=lambda l: (l.split()[1], l.split()[0]))


SALIDA_TJ = ROOT / "config" / "noticias" / "crudo" / "fed_testimonio_jh_2008_2022.txt"
URL_TEST_JSON = "https://www.federalreserve.gov/json/ne-testimony.json"
URL_SPEECH_JSON = "https://www.federalreserve.gov/json/ne-speeches.json"


def testimonio_y_jackson_hole(carpeta: Path) -> list[str]:
    """Testimonio semestral del presidente (Monetary Policy Report) y discurso en Jackson Hole, 2008-2022.

    Hora: la del JSON de la Fed si la trae; si no, 10:00 ET (audiencias). Del testimonio se veta además el día hábil
    siguiente a las 10:00 (la otra cámara suele ser al día siguiente; el JSON trae una sola entrada): conservador."""
    import json
    out = []
    t = json.loads((carpeta / "testimony.json").read_text(encoding="utf-8-sig"))
    s = json.loads((carpeta / "speeches.json").read_text(encoding="utf-8-sig"))

    def fecha_hora(d):
        p = d.split()
        f = datetime.strptime(p[0], "%m/%d/%Y")
        h = datetime.strptime(" ".join(p[1:]), "%I:%M:%S %p").strftime("%H:%M") if len(p) > 1 else "10:00"
        return f, h
    for x in t:
        if x.get("d") and re.search(r"Semiannual Monetary Policy Report", x.get("t", ""), re.I) \
                and re.match(r"Chair", x.get("s", "")):
            f, h = fecha_hora(x["d"])
            if 2008 <= f.year <= 2022:
                out.append(f"TESTIMONY {f:%Y-%m-%d} {h}")
                sig = f
                while True:
                    from datetime import timedelta
                    sig = sig + timedelta(days=1)
                    if sig.weekday() < 5:
                        break
                out.append(f"TESTIMONY_DIA2 {sig:%Y-%m-%d} 10:00")
    for x in s:
        if x.get("d") and re.match(r"Chair", x.get("s", "")) and "Kansas City" in x.get("lo", "") + x.get("t", "") \
                or (x.get("d") and re.match(r"Chair", x.get("s", "")) and "Jackson Hole" in x.get("lo", "")):
            f, h = fecha_hora(x["d"])
            if 2008 <= f.year <= 2022 and f.month == 8:
                out.append(f"JACKSON_HOLE {f:%Y-%m-%d} {h}")
    return sorted(set(out), key=lambda l: l.split()[1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--bajar", type=Path); ap.add_argument("--carpeta", type=Path)
    a = ap.parse_args(argv)
    if a.bajar:
        bajar(a.bajar)
    if a.carpeta or a.bajar:
        filas = transcribir(a.carpeta or a.bajar)
        cab = ["# Fed, páginas oficiales FOMC (fomchistorical<año>.htm 2008-2020, fomccalendars.htm 2021-2022).",
               "# formato: EVENTO yyyymmdd HH:MM (hora ET por convención, ver tools/noticias_fed_historico.py) | NO_PROGRAMADA"]
        SALIDA.write_text("\n".join(cab + filas) + "\n", encoding="utf-8", newline="\n")
        print(f"{SALIDA.relative_to(ROOT)}: {len(filas)} filas")
        tj = testimonio_y_jackson_hole(a.carpeta or a.bajar)
        cab = [f"# Fed, {URL_TEST_JSON} y {URL_SPEECH_JSON} (presidente; testimonio semestral y Jackson Hole 2008-2022).",
               "# formato: EVENTO yyyy-mm-dd HH:MM (ET; 10:00 si el JSON no trae hora). TESTIMONY_DIA2 = día hábil siguiente (conservador)."]
        SALIDA_TJ.write_text("\n".join(cab + tj) + "\n", encoding="utf-8", newline="\n")
        print(f"{SALIDA_TJ.relative_to(ROOT)}: {len(tj)} filas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
