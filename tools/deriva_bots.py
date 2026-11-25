"""Deriva entre los bots del repo y lo instalado en NT8, MT5 y cTrader de esta PC.

Compara el texto (sin diferencias de fin de línea) de cada bot del repo con su copia instalada:
  NT8      nt8/strategies/*.cs               -> Documents/NinjaTrader 8/bin/Custom/Strategies/
  MT5      mt5/Include|Experts/EdgeLabFundedSync -> <terminal>/MQL5/Include|Experts/EdgeLabFundedSync (cada terminal)
  cTrader  ctrader/Shared + wrapper de cada bot -> cAlgo/Sources/Robots/<bot>/<bot>/

  python tools/deriva_bots.py            # informe
  python tools/deriva_bots.py --check    # sale 1 si algún archivo instalado difiere del repo

Sólo lee; para instalar está `tools/sync_ctrader_mt5_bots.py`. Lo usa `tools/puerta_despliegue.py`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sync_ctrader_mt5_bots as S  # noqa: E402  (descubre las rutas instaladas al importarse)


def _txt(p: Path) -> str:
    return S._read_text_auto_enc(p).replace("\r\n", "\n").replace("\r", "\n")


def pares() -> list[tuple[str, Path, Path]]:
    """(plataforma, archivo del repo, copia instalada) para todo lo que el sync instala."""
    out = [("NT8", f, S.NT8_USER_STRAT / f.name) for f in sorted(S.NT8_DIR.glob("*.cs"))]
    for label, mql5, _ in S.MT5_TERMINALS:
        for sub, pat in (("Include", "*.mqh"), ("Experts", "*.mq5")):
            for f in sorted((S.MT5_DIR / sub / "EdgeLabFundedSync").glob(pat)):
                out.append((f"MT5:{label}", f, mql5 / sub / "EdgeLabFundedSync" / f.name))
    for name in S.BOT_NAMES:
        inner = S.CTRADER_DIR / name / name
        dst = S.CALGO_ROBOTS / name / name
        for f in [inner / f"{name}.cs", S.CTRADER_SHARED / "EdgeLabFundedSyncCfdCore.cs", S.CTRADER_SHARED / "FundedSyncCTraderAdapter.cs"]:
            if f.exists():
                out.append(("cTrader", f, dst / f.name))
    return out


def revisar() -> list[dict]:
    res = []
    for plat, src, dst in pares():
        if not dst.exists():
            estado = "NO_INSTALADO"
        else:
            estado = "IGUAL" if _txt(src) == _txt(dst) else "DERIVA"
        res.append(dict(plataforma=plat, repo=str(src.relative_to(ROOT)).replace("\\", "/"), instalado=str(dst), estado=estado))
    return res


def deriva_de(repo_rel: str, res: list[dict] | None = None) -> list[dict]:
    """Filas de un archivo del repo (p. ej. 'nt8/strategies/EdgeLabFundedSyncPortfolio.cs')."""
    return [r for r in (res if res is not None else revisar()) if r["repo"] == repo_rel]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--todo", action="store_true")
    a = ap.parse_args(argv)
    res = revisar()
    n = {k: sum(1 for r in res if r["estado"] == k) for k in ("IGUAL", "DERIVA", "NO_INSTALADO")}
    for r in res:
        if a.todo or r["estado"] == "DERIVA":
            print(f"{r['estado']:<13} {r['plataforma']:<22} {r['repo']}  ->  {r['instalado']}")
    print(f"igual {n['IGUAL']}, deriva {n['DERIVA']}, no instalado {n['NO_INSTALADO']}")
    return 1 if a.check and n["DERIVA"] else 0


if __name__ == "__main__":
    sys.exit(main())
