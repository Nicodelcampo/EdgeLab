"""Guardas de la auditoría de corridas del 2026-11-16 (docs/research/auditoria_corridas_20261116/CRITERIOS_AUDITORIA.md).

Cada patrón produjo un resultado inválido real; no puede volver a aparecer en código de research ni en kernels."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PATRONES = {
    # A1: convertir fechas a segundos dividiendo el int64 por 1e9 depende de la resolución (µs en pandas reciente → fechas de 1970)
    "fecha_a_segundos_por_division": re.compile(r'astype\(\s*["\']int64["\']\s*\)\s*//\s*10\s*\*\*\s*9'),
    # A2: frontera del holdout a medianoche UTC (la sesión del 1-oct abre 2026-09-30 22:00 UTC): usar edgelab.holdout
    "holdout_medianoche_utc": re.compile(r'Timestamp\(\s*["\']2026-10-01["\']\s*,\s*tz\s*=\s*["\']UTC["\']'),
}
EXCEPCIONES = {"tests/test_auditoria_patrones.py"}


def test_sin_patrones_de_errores_conocidos():
    malos = []
    for base in ("edgelab", "tools"):
        for f in (RAIZ / base).rglob("*.py"):
            rel = str(f.relative_to(RAIZ))
            if rel in EXCEPCIONES: continue
            txt = f.read_text(encoding="utf-8", errors="ignore")
            for nom, pat in PATRONES.items():
                for m in pat.finditer(txt):
                    malos.append(f"{rel}:{txt[:m.start()].count(chr(10)) + 1} {nom}")
    assert not malos, "patrones de errores ya vistos en la auditoría 2026-11-16:\n" + "\n".join(malos)
