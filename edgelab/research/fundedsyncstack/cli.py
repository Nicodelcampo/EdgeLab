"""CLI para ejecutar los 15 sub-modulos y el motor de cartera de FUNDEDSYNCSTACK sobre datos M1.

Ejemplos de uso:
  python -m python.cli --csv "C:\\StrategyQuantX145\\user\\mcp-work\\edgelab_m1\\NQ_M1_dukas-M1-.csv" --desde 2026-01-01 --hasta 2026-09-30 --modulo TODOS
  python -m python.cli --csv "C:\\StrategyQuantX145\\user\\mcp-work\\edgelab_m1\\NQ_M1_dukas-M1-.csv" --desde 2026-01-01 --hasta 2026-09-30 --modulo V --v-atr-days 60
"""
from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path
import sys
from typing import Any, Dict

from . import CONFIG_CLASSES, MODULOS, correr_modulo, correr_todos, load_m1_data, build_multi_series   # en el repo: siempre como paquete
from .paridad_vendedor import PERFILES_DISPONIBLES, obtener_config_modulo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ejecuta cualquiera de las 15 sub-estrategias o la cartera completa de FUNDEDSYNCSTACK."
    )
    ap.add_argument("--csv", required=True, help="Ruta al archivo CSV o Parquet M1 (pre-holdout < 2026-10-01)")
    ap.add_argument("--desde", default="2026-01-01", help="Fecha inicial UTC (YYYY-MM-DD)")
    ap.add_argument("--hasta", default="2026-10-01", help="Fecha final exclusiva UTC (YYYY-MM-DD, <= 2026-10-01)")
    ap.add_argument("--tz", default="UTC", help="Zona horaria del CSV de entrada (default: UTC)")
    ap.add_argument(
        "--modulo",
        default="TODOS",
        help="Tag del modulo (A1,A20,F,S,P,C,V,O,W,N,T,R,Z,E,Q) o TODOS",
    )
    ap.add_argument(
        "--v-atr-days",
        type=int,
        default=None,
        help="Override opcional para V_DailyAtrLength en VaultBreak (default IL: 252)",
    )
    ap.add_argument(
        "--perfil",
        choices=PERFILES_DISPONIBLES,
        default="il_fabrica",
        help="Perfil de configuracion: il_fabrica (1:1 DLL) o vendedor_calibrado (validado OOS)",
    )
    ap.add_argument("--out-csv", default=None, help="Ruta opcional para exportar la lista de trades en CSV")
    args = ap.parse_args(argv)

    df_m1 = load_m1_data(args.csv, start=args.desde, end=args.hasta, tz_input=args.tz, allow_sellado=False)
    ms = build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)
    print(f"[INFO] Series construidas: bip1={len(ms.bip1.close):,} barras M1 ({args.desde} -> {args.hasta})")

    mod = args.modulo.strip().upper()
    if mod == "TODOS":
        mod_cfgs: Dict[str, Any] = {}
        if args.v_atr_days is not None:
            mod_cfgs["V"] = dataclasses.replace(obtener_config_modulo("V", perfil=args.perfil), daily_atr_length=args.v_atr_days)
        res = correr_todos(ms, perfil=args.perfil, incluir_cartera=True, module_configs=mod_cfgs)
        print("\n=== RESUMEN POR MODULO (STANDALONE) ===")
        print(res["resumen_df"].to_string(index=False))
        if res["cartera"] is not None:
            comp = res["cartera"]["comparison"]
            print("\n=== CARTERA CONSOLIDADA (VIRTUAL LEDGER VS BROKER NETTING) ===")
            for k, v in comp.items():
                print(f"  {k}: {v}")
        if args.out_csv:
            res["trades_df"].to_csv(args.out_csv, index=False)
            print(f"[OK] Trades exportados a {args.out_csv}")
    else:
        kwargs = {}
        if mod == "V" and args.v_atr_days is not None:
            kwargs["daily_atr_length"] = args.v_atr_days
        df_t = correr_modulo(mod, ms, perfil=args.perfil, **kwargs)
        print(f"\n=== MODULO {mod}: {len(df_t)} TRADES ===")
        if len(df_t) > 0:
            print(
                f"Net PnL USD: {df_t['pnl_usd'].sum():,.2f} | WinRate: {(df_t['pnl_usd'] > 0).mean()*100:.1f}%"
            )
            print(df_t.head(10).to_string(index=False))
        if args.out_csv:
            df_t.to_csv(args.out_csv, index=False)
            print(f"[OK] Trades exportados a {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

