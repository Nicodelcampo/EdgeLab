#!/usr/bin/env python3
"""Syncs, installs, and compiles the EdgeLabFundedSync cTrader (C#) and MetaTrader 5 (MQL5) bot suites."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTRADER_DIR = ROOT / "ctrader"
CTRADER_SHARED = CTRADER_DIR / "Shared"
CALGO_ROBOTS = Path(r"C:\Users\nicoc\OneDrive\Documentos\cAlgo\Sources\Robots")
CALGO_API_DLL = Path(r"C:\Users\nicoc\OneDrive\Documentos\cAlgo\API\cAlgo.API.dll")
CSC_EXE = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")

MT5_DIR = ROOT / "mt5"
MT5_TERMINALS = [
    (
        "MT5_Generic",
        Path(r"C:\Users\nicoc\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5"),
        Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"),
    ),
    (
        "MT5_The5ers",
        Path(r"C:\Users\nicoc\AppData\Roaming\MetaQuotes\Terminal\10CE948A1DFC9A8C27E56E827008EBD4\MQL5"),
        Path(r"C:\Program Files\Five Percent Online MetaTrader 5\MetaEditor64.exe"),
    ),
]

BOT_NAMES = [
    "EdgeLabFundedSyncPortfolio",
    "EdgeLabFundedSyncCore5AltaConv",
    "EdgeLabFundedSyncCore6",
    "EdgeLabFundedSyncSnipersRZ",
    "EdgeLabFundedSyncSingleModule",
]


def to_crlf_ascii(text: str) -> bytes:
    norm = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    return norm.encode("ascii")


def write_crlf_ascii(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(to_crlf_ascii(text))


def build_csproj() -> str:
    return (
        "<Project Sdk=\"Microsoft.NET.Sdk\">\n"
        "  <PropertyGroup>\n"
        "    <TargetFramework>net6.0</TargetFramework>\n"
        "  </PropertyGroup>\n"
        "  <ItemGroup>\n"
        "    <PackageReference Include=\"cTrader.Automate\" Version=\"1.*-*\" />\n"
        "  </ItemGroup>\n"
        "</Project>\n"
    )


def build_sln(bot_name: str) -> str:
    proj_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"edgelab.ctrader.{bot_name}")).upper()
    sol_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"edgelab.ctrader.sln.{bot_name}")).upper()
    return (
        "\nMicrosoft Visual Studio Solution File, Format Version 12.00\n"
        "# Visual Studio Version 16\n"
        "VisualStudioVersion = 16.0.31729.503\n"
        "MinimumVisualStudioVersion = 10.0.40219.1\n"
        f"Project(\"{{9A19103F-16F7-4668-BE54-9A1E7A4F7556}}\") = \"{bot_name}\", \"{bot_name}\\{bot_name}.csproj\", \"{{{proj_guid}}}\"\n"
        "EndProject\n"
        "Global\n"
        "\tGlobalSection(SolutionConfigurationPlatforms) = preSolution\n"
        "\t\tDebug|Any CPU = Debug|Any CPU\n"
        "\t\tRelease|Any CPU = Release|Any CPU\n"
        "\tEndGlobalSection\n"
        "\tGlobalSection(ProjectConfigurationPlatforms) = postSolution\n"
        f"\t\t{{{proj_guid}}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU\n"
        f"\t\t{{{proj_guid}}}.Debug|Any CPU.Build.0 = Debug|Any CPU\n"
        f"\t\t{{{proj_guid}}}.Release|Any CPU.ActiveCfg = Release|Any CPU\n"
        f"\t\t{{{proj_guid}}}.Release|Any CPU.Build.0 = Release|Any CPU\n"
        "\tEndGlobalSection\n"
        "\tGlobalSection(SolutionProperties) = preSolution\n"
        "\t\tHideSolutionNode = FALSE\n"
        "\tEndGlobalSection\n"
        "\tGlobalSection(ExtensibilityGlobals) = postSolution\n"
        f"\t\tSolutionGuid = {{{sol_guid}}}\n"
        "\tEndGlobalSection\n"
        "EndGlobal\n"
    )


def sync_and_compile_ctrader(install: bool = True, compile_check: bool = True) -> None:
    core_txt = (CTRADER_SHARED / "EdgeLabFundedSyncCfdCore.cs").read_text(encoding="utf-8")
    adap_txt = (CTRADER_SHARED / "FundedSyncCTraderAdapter.cs").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name in BOT_NAMES:
            proj_root = CTRADER_DIR / name
            inner = proj_root / name
            wrapper_path = inner / f"{name}.cs"
            if not wrapper_path.exists():
                raise FileNotFoundError(f"Missing cTrader wrapper: {wrapper_path}")

            # Normalize wrapper to CRLF ASCII as well
            write_crlf_ascii(wrapper_path, wrapper_path.read_text(encoding="utf-8"))
            write_crlf_ascii(inner / "EdgeLabFundedSyncCfdCore.cs", core_txt)
            write_crlf_ascii(inner / "FundedSyncCTraderAdapter.cs", adap_txt)
            write_crlf_ascii(inner / f"{name}.csproj", build_csproj())
            write_crlf_ascii(proj_root / f"{name}.sln", build_sln(name))

            if install and CALGO_ROBOTS.exists():
                dst = CALGO_ROBOTS / name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(proj_root, dst)
                print(f"[cTrader] Installed -> {dst}")

            if compile_check and CSC_EXE.exists() and CALGO_API_DLL.exists():
                out_dll = tmp_dir / f"{name}.dll"
                cmd = [
                    str(CSC_EXE),
                    "/nologo",
                    "/target:library",
                    "/warnaserror",
                    "/nowarn:1685",
                    f"/out:{out_dll}",
                    "/r:System.dll",
                    "/r:System.Core.dll",
                    f"/r:{CALGO_API_DLL}",
                    str(inner / "EdgeLabFundedSyncCfdCore.cs"),
                    str(inner / "FundedSyncCTraderAdapter.cs"),
                    str(wrapper_path),
                ]
                res = subprocess.run(cmd, capture_output=True, check=False)
                if res.returncode != 0:
                    out_s = res.stdout.decode("cp850", errors="replace") if res.stdout else ""
                    err_s = res.stderr.decode("cp850", errors="replace") if res.stderr else ""
                    raise RuntimeError(f"cTrader compile failed for {name}:\n{out_s}\n{err_s}")
                print(f"[cTrader] Compiled clean (0 errors, 0 warnings) -> {name}")


def _read_metaeditor_log(log_path: Path) -> str:
    raw = log_path.read_bytes()
    for enc in ("utf-16", "utf-16-le", "utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="replace")


def sync_and_compile_mt5(install: bool = True, compile_check: bool = True) -> None:
    inc_src = MT5_DIR / "Include" / "EdgeLabFundedSync"
    exp_src = MT5_DIR / "Experts" / "EdgeLabFundedSync"
    if not inc_src.exists() or not exp_src.exists():
        raise FileNotFoundError("Missing mt5/Include or mt5/Experts directory")

    # Normalize CRLF UTF-8 without BOM (safe for pure ASCII MQL5)
    for src_dir in (inc_src, exp_src):
        for f in src_dir.glob("*"):
            if f.is_file() and f.suffix.lower() in (".mqh", ".mq5"):
                write_crlf_ascii(f, f.read_text(encoding="utf-8"))

    for label, mql5_root, me_exe in MT5_TERMINALS:
        if not mql5_root.exists():
            print(f"[MT5] Skipping missing terminal root: {mql5_root}")
            continue
        dst_inc = mql5_root / "Include" / "EdgeLabFundedSync"
        dst_exp = mql5_root / "Experts" / "EdgeLabFundedSync"
        if install:
            dst_inc.mkdir(parents=True, exist_ok=True)
            dst_exp.mkdir(parents=True, exist_ok=True)
            for f in inc_src.glob("*.mqh"):
                shutil.copy2(f, dst_inc / f.name)
            for f in exp_src.glob("*.mq5"):
                shutil.copy2(f, dst_exp / f.name)
            print(f"[MT5:{label}] Installed includes -> {dst_inc} and experts -> {dst_exp}")

        if compile_check and me_exe.exists():
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                for name in BOT_NAMES:
                    mq5_path = dst_exp / f"{name}.mq5"
                    ex5_path = dst_exp / f"{name}.ex5"
                    if ex5_path.exists():
                        ex5_path.unlink()
                    log_path = tmp_dir / f"{label}_{name}.log"
                    cmd = [str(me_exe), f"/compile:{mq5_path}", f"/log:{log_path}"]
                    subprocess.run(cmd, check=False)
                    if not log_path.exists():
                        raise RuntimeError(f"MetaEditor produced no log for {mq5_path}")
                    log_txt = _read_metaeditor_log(log_path)
                    if "0 errors, 0 warnings" not in log_txt:
                        raise RuntimeError(f"MT5 compile failed on {label}/{name}:\n{log_txt}")
                    if not ex5_path.exists():
                        raise RuntimeError(f"Missing compiled binary: {ex5_path}")
                    print(f"[MT5:{label}] Compiled clean (0 errors, 0 warnings) -> {ex5_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("ctrader", "mt5", "all"), default="all")
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()

    if args.target in ("ctrader", "all"):
        sync_and_compile_ctrader(install=not args.no_install, compile_check=not args.no_compile)
    if args.target in ("mt5", "all"):
        sync_and_compile_mt5(install=not args.no_install, compile_check=not args.no_compile)


if __name__ == "__main__":
    main()
