"""Construye `config/noticias/calendario_usd_tier1.csv` desde las transcripciones de `config/noticias/crudo/`.

Cada fila sale de una fuente citada (BLS, BEA, Census, Fed, ISM; ForexFactory sólo donde la fuente oficial no da
el dato histórico: ISM 2023-2025, solicitudes de subsidio por desempleo, hora de audiencia del testimonio). Las horas
ET se pasan a UTC con `zoneinfo("America/New_York")`, así que el cambio de horario (EST/EDT) lo resuelve la zona,
no una tabla propia. Qué faltó y por qué: `config/noticias/FUENTES.md`.

Uso: `python tools/noticias_calendario.py [--check]` (con --check compara contra el CSV committeado y sale 1 si difiere).
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CRUDO = ROOT / "config" / "noticias" / "crudo"
SALIDA = ROOT / "config" / "noticias" / "calendario_usd_tier1.csv"
ET = ZoneInfo("America/New_York")

URL_BLS = "https://www.bls.gov/schedule/{y}/home.htm"
URL_FOMC = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
URL_BEA_PDF = {2023: "https://www.bea.gov/sites/default/files/2022-10/2023-News-Release-Schedule.pdf",
               2024: "https://www.bea.gov/sites/default/files/2024-06/2024-News-Release-Schedule.pdf"}
URL_BEA_JSON = "https://apps.bea.gov/API/signup/release_dates.json"
URL_CENSUS = "https://www.census.gov/economic-indicators/calendar-listview-{y}.html"
URL_ISM = "https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/"
URL_FF_ISM_MFG = "https://www.forexfactory.com/calendar/252-us-ism-manufacturing-pmi"
URL_FF_ISM_SVC = "https://www.forexfactory.com/calendar/253-us-ism-services-pmi"
URL_FF_CLAIMS = "https://www.forexfactory.com/calendar/11-us-unemployment-claims"

BLS_EVENTO = {"CPI": "CPI", "EMPSIT": "NFP_EMPLOYMENT_SITUATION", "PPI": "PPI", "JOLTS": "JOLTS"}
DESDE, HASTA = "2023-01-01", "2026-12-31"


def _utc(fecha: str, hhmm: str) -> str:
    """'2024-03-12', '08:30' (ET) -> '2024-03-12T12:30Z'."""
    d = datetime.strptime(f"{fecha} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _hhmm(ampm: str) -> str:
    """'8:30AM' / '10:00:00 AM' -> '08:30' / '10:00'."""
    s = ampm.replace(" ", "").upper()
    m = re.fullmatch(r"(\d{1,2}):(\d\d)(?::\d\d)?(AM|PM)", s)
    if not m:
        raise ValueError(f"hora no reconocida: {ampm!r}")
    h, mi, p = int(m.group(1)), m.group(2), m.group(3)
    h = h % 12 + (12 if p == "PM" else 0)
    return f"{h:02d}:{mi}"


def _lineas(nombre: str):
    for linea in (CRUDO / nombre).read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            yield linea


def filas() -> list[dict]:
    out: list[dict] = []

    def add(ts, evento, url, impacto="tier1"):
        out.append({"ts_utc": ts, "evento": evento, "fuente_url": url, "impacto": impacto})

    # BLS: CPI, Employment Situation, PPI, JOLTS
    for y in (2023, 2024, 2025, 2026):
        for linea in _lineas(f"bls_{y}.txt"):
            clave, hora, *fechas = linea.split()
            for f in fechas:
                add(_utc(f, hora), BLS_EVENTO[clave], URL_BLS.format(y=y))

    oficiales = list(_lineas("oficiales_extraidos.txt"))
    for linea in oficiales:
        partes = linea.split()
        clave = partes[0]
        if clave == "FOMC_DECISION":
            f = partes[1]
            add(_utc(f, "14:00"), "FOMC_DECISION", URL_FOMC)
            add(_utc(f, "14:30"), "FOMC_PRESS_CONFERENCE", URL_FOMC)
        elif clave == "FOMC_MINUTES":
            add(_utc(partes[1], "14:00"), "FOMC_MINUTES", URL_FOMC)
        elif clave == "BEA":
            f, hora = partes[1], _hhmm(partes[2])
            titulo = linea.split("|", 1)[1].strip()
            y = int(f[:4])
            if titulo.startswith("Personal Income"):
                add(_utc(f, hora), "PCE_PERSONAL_INCOME_OUTLAYS", URL_BEA_PDF[y])
            else:
                if "(Advance" in titulo:
                    kind = "ADVANCE"
                elif "(Second" in titulo:
                    kind = "SECOND"
                elif "(Third" in titulo:
                    kind = "THIRD"
                else:  # 4.º trimestre: el PDF no trae paréntesis; ene=avance, feb=segunda, mar=tercera
                    kind = {1: "ADVANCE", 2: "SECOND", 3: "THIRD"}[int(f[5:7])]
                add(_utc(f, hora), f"GDP_{kind}", URL_BEA_PDF[y])
        elif clave in ("BEA_JSON_GDP", "BEA_JSON_PIO"):
            ts = datetime.fromisoformat(partes[1]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
            if clave == "BEA_JSON_PIO":
                add(ts, "PCE_PERSONAL_INCOME_OUTLAYS", URL_BEA_JSON)
            else:
                add(ts, "GDP_" + _GDP_KIND[ts[:10]], URL_BEA_JSON)
        elif clave == "RETAIL":
            f, hora = partes[1], _hhmm(partes[2])
            add(_utc(f, hora), "RETAIL_SALES", URL_CENSUS.format(y=f[:4]))
        elif clave in ("FED_TESTIMONY", "FED_JH"):
            cab, _quien, url = [p.strip() for p in linea.split("|")]
            _, fecha_us, h, ampm = cab.split()
            mm, dd, yy = fecha_us.split("/")
            f = f"{yy}-{int(mm):02d}-{int(dd):02d}"
            ev = "FED_CHAIR_TESTIMONY" if clave == "FED_TESTIMONY" else "FED_CHAIR_JACKSON_HOLE"
            add(_utc(f, _hhmm(h + ampm)), ev, url)

    # manual: ISM 2026 (oficial), audiencias (FF)
    for linea in _lineas("manual.txt"):
        partes = linea.split()
        if partes[0] in ("ISM_MFG_2026", "ISM_SVC_2026"):
            ev = "ISM_MANUFACTURING_PMI" if partes[0] == "ISM_MFG_2026" else "ISM_SERVICES_PMI"
            for f in partes[1:]:
                add(_utc(f, "10:00"), ev, URL_ISM)
        elif partes[0] == "FF_HEARING":
            ts = partes[1].replace("Z", "")
            ts = datetime.fromisoformat(ts).strftime("%Y-%m-%dT%H:%MZ")
            add(ts, "FED_CHAIR_TESTIMONY", partes[2])

    # ForexFactory: ISM 2023-2025 (fecha; hora 10:00 ET del ISM) y solicitudes semanales (08:30 ET, tier2)
    for linea in _lineas("ff.txt"):
        partes = linea.split()
        if partes[0] == "ISM_MFG_DATES":
            for f in partes[1:]:
                add(_utc(f, "10:00"), "ISM_MANUFACTURING_PMI", URL_FF_ISM_MFG)
        elif partes[0] == "ISM_SVC_DATES":
            for f in partes[1:]:
                add(_utc(f, "10:00"), "ISM_SERVICES_PMI", URL_FF_ISM_SVC)
        elif partes[0].startswith("CLAIMS_DATES"):
            for f in partes[1:]:
                add(_utc(f, "08:30"), "INITIAL_JOBLESS_CLAIMS", URL_FF_CLAIMS, impacto="tier2")

    # dedup exacto (ts, evento): las audiencias de FF coinciden con la hora oficial de la Fed cuando ésta es 10:00
    vistos, unicas = set(), []
    for r in sorted(out, key=lambda r: (r["ts_utc"], r["evento"], r["fuente_url"])):
        k = (r["ts_utc"], r["evento"])
        if k in vistos:
            continue
        vistos.add(k)
        if DESDE <= r["ts_utc"][:10] <= HASTA:
            unicas.append(r)
    return unicas


_GDP_KIND = {p[1]: p[2] for p in (l.split() for l in _lineas("manual.txt")) if p[0] == "GDP_KIND"}


def render(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["ts_utc", "evento", "fuente_url", "impacto"], lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="no escribe; sale 1 si el CSV committeado difiere")
    a = ap.parse_args(argv)
    txt = render(filas())
    if a.check:
        actual = SALIDA.read_text(encoding="utf-8") if SALIDA.exists() else ""
        if actual != txt:
            print("calendario desactualizado: correr python tools/noticias_calendario.py")
            return 1
        print("calendario OK")
        return 0
    SALIDA.write_text(txt, encoding="utf-8")
    print(f"{SALIDA.relative_to(ROOT)}: {txt.count(chr(10)) - 1} filas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
