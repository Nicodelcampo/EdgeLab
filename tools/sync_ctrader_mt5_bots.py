#!/usr/bin/env python3
"""Syncs, installs, and compiles the EdgeLabFundedSync NT8, cTrader (C#), and MT5 (MQL5) bot suites."""
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTRADER_DIR = ROOT / "ctrader"
CTRADER_SHARED = CTRADER_DIR / "Shared"
MT5_DIR = ROOT / "mt5"
NT8_DIR = ROOT / "nt8" / "strategies"

BOT_NAMES = [
    "EdgeLabFundedSyncPortfolio",
    "EdgeLabFundedSyncCore5AltaConv",
    "EdgeLabFundedSyncCore6",
    "EdgeLabFundedSyncSnipersRZ",
    "EdgeLabFundedSyncSingleModule",
    "EdgeLabFundedSyncESCoreUS500",
]

NT8_FILES = [
    "EdgeLabFundedSyncCore.cs",
    "EdgeLabFundedSyncPortfolio.cs",
    "EdgeLabFundedSyncCore6.cs",
    "EdgeLabFundedSyncCore5AltaConv.cs",
    "EdgeLabFundedSyncSnipersRZ.cs",
    "EdgeLabFundedSyncSingleModule.cs",
]


def _read_text_auto_enc(file_path: Path) -> str:
    raw = file_path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    if b"\x00" in raw[:64]:
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="replace")


def _read_metaeditor_log(log_path: Path) -> str:
    return _read_text_auto_enc(log_path)


def _candidate_docs_dirs() -> list[Path]:
    """Return deduplicated candidate Windows Documents folders (official Shell path + OneDrive/local fallbacks)."""
    cands: list[Path] = []
    if os.name == "nt":
        try:
            buf = ctypes.create_unicode_buffer(1024)
            # CSIDL_PERSONAL (5) = current user's My Documents (follows OneDrive / Spanish locale redirection)
            rc = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
            if rc == 0 and buf.value:
                cands.append(Path(buf.value))
        except Exception:
            pass
    home = Path.home()
    for rel in (
        Path("Documents"),
        Path("Documentos"),
        Path("OneDrive") / "Documents",
        Path("OneDrive") / "Documentos",
    ):
        cands.append(home / rel)

    dedup: list[Path] = []
    seen: set[str] = set()
    for p in cands:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    return dedup


def discover_csc_and_wpf() -> tuple[Path, Path]:
    win_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for rel in (
        Path("Microsoft.NET") / "Framework64" / "v4.0.30319" / "csc.exe",
        Path("Microsoft.NET") / "Framework" / "v4.0.30319" / "csc.exe",
    ):
        p = win_dir / rel
        if p.exists():
            return p, p.parent / "WPF"
    fallback = win_dir / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
    return fallback, fallback.parent / "WPF"


def discover_calgo_paths() -> tuple[Path, Path]:
    docs = _candidate_docs_dirs()
    robots_dir: Path | None = None
    api_dll: Path | None = None
    for d in docs:
        r = d / "cAlgo" / "Sources" / "Robots"
        if robots_dir is None and r.exists():
            robots_dir = r
        a = d / "cAlgo" / "API" / "cAlgo.API.dll"
        if api_dll is None and a.exists():
            api_dll = a
    default_doc = next((d for d in docs if d.exists()), docs[0])
    return (
        robots_dir if robots_dir is not None else default_doc / "cAlgo" / "Sources" / "Robots",
        api_dll if api_dll is not None else default_doc / "cAlgo" / "API" / "cAlgo.API.dll",
    )


def discover_nt8_paths() -> tuple[Path, Path, Path, Path]:
    docs = _candidate_docs_dirs()
    strat_dir: Path | None = None
    custom_dll: Path | None = None
    for d in docs:
        s = d / "NinjaTrader 8" / "bin" / "Custom" / "Strategies"
        if strat_dir is None and s.exists():
            strat_dir = s
        c = d / "NinjaTrader 8" / "bin" / "Custom" / "NinjaTrader.Custom.dll"
        if custom_dll is None and c.exists():
            custom_dll = c

    core_dll: Path | None = None
    gui_dll: Path | None = None
    for env_var, default_pf in (("ProgramFiles", r"C:\Program Files"), ("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        pf = os.environ.get(env_var, default_pf)
        nt_bin = Path(pf) / "NinjaTrader 8" / "bin"
        if core_dll is None and (nt_bin / "NinjaTrader.Core.dll").exists():
            core_dll = nt_bin / "NinjaTrader.Core.dll"
        if gui_dll is None and (nt_bin / "NinjaTrader.Gui.dll").exists():
            gui_dll = nt_bin / "NinjaTrader.Gui.dll"

    default_doc = next((d for d in docs if d.exists()), docs[0])
    default_pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NinjaTrader 8" / "bin"
    return (
        strat_dir if strat_dir is not None else default_doc / "NinjaTrader 8" / "bin" / "Custom" / "Strategies",
        core_dll if core_dll is not None else default_pf / "NinjaTrader.Core.dll",
        gui_dll if gui_dll is not None else default_pf / "NinjaTrader.Gui.dll",
        custom_dll if custom_dll is not None else default_doc / "NinjaTrader 8" / "bin" / "Custom" / "NinjaTrader.Custom.dll",
    )


def discover_mt5_terminals() -> list[tuple[str, Path, Path]]:
    app_data = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    term_base = app_data / "MetaQuotes" / "Terminal"
    found: list[tuple[str, Path, Path]] = []
    if not term_base.exists():
        return found

    for term_dir in sorted(term_base.iterdir(), key=lambda p: p.name):
        if not term_dir.is_dir():
            continue
        mql5_dir = term_dir / "MQL5"
        orig_file = term_dir / "origin.txt"
        if not mql5_dir.exists() or not orig_file.exists():
            continue
        orig_txt = _read_text_auto_enc(orig_file).replace("\x00", "").strip()
        if not orig_txt:
            continue
        orig_path = Path(orig_txt)
        me_exe = orig_path / "MetaEditor64.exe"
        if not me_exe.exists():
            alt = orig_path / "metaeditor.exe"
            if alt.exists():
                me_exe = alt
        if not orig_path.exists() and not me_exe.exists():
            continue
        clean_name = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in orig_path.name).strip("_")
        label = f"{clean_name}_{term_dir.name[:6]}"
        found.append((label, mql5_dir, me_exe))
    return found


CSC_EXE, WPF_DIR = discover_csc_and_wpf()
CALGO_ROBOTS, CALGO_API_DLL = discover_calgo_paths()
NT8_USER_STRAT, NT8_CORE_DLL, NT8_GUI_DLL, NT8_CUSTOM_DLL = discover_nt8_paths()
MT5_TERMINALS = discover_mt5_terminals()


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

    if install and not CALGO_ROBOTS.exists():
        print(f"[cTrader] Skipping install: cAlgo Robots dir not found at {CALGO_ROBOTS} (use --calgo-dir to override)")
    if compile_check and (not CSC_EXE.exists() or not CALGO_API_DLL.exists()):
        print(f"[cTrader] Skipping csc compile check (CSC={CSC_EXE.exists()}, cAlgo.API.dll={CALGO_API_DLL.exists()}); click Build inside cTrader Automate.")

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

    if not MT5_TERMINALS:
        print("[MT5] No MetaQuotes terminal directories detected under APPDATA (use --mt5-mql5-dir / --metaeditor to override)")
        return

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

        if compile_check:
            if not me_exe.exists():
                print(f"[MT5:{label}] Skipping MetaEditor compile: not found at {me_exe}")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                for name in BOT_NAMES:
                    mq5_path = dst_exp / f"{name}.mq5"
                    ex5_path = dst_exp / f"{name}.ex5"
                    if ex5_path.exists():
                        ex5_path.unlink()
                    log_path = tmp_dir / f"{label}_{name}.log"
                    if os.name == "nt":
                        cmd: str | list[str] = f'"{me_exe}" /compile:"{mq5_path}" /log:"{log_path}"'
                    else:
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


def sync_and_compile_nt8(install: bool = True, compile_check: bool = True) -> None:
    cs_paths = []
    if install and not NT8_USER_STRAT.exists():
        print(f"[NT8] Skipping install: NT8 Strategies dir not found at {NT8_USER_STRAT} (use --nt8-dir to override)")

    for fname in NT8_FILES:
        src = NT8_DIR / fname
        if not src.exists():
            raise FileNotFoundError(f"Missing NT8 strategy file: {src}")
        txt = src.read_text(encoding="utf-8")
        write_crlf_ascii(src, txt)
        cs_paths.append(str(src))
        if install and NT8_USER_STRAT.exists():
            write_crlf_ascii(NT8_USER_STRAT / fname, txt)
            print(f"[NT8] Installed -> {NT8_USER_STRAT / fname}")

    if compile_check:
        if not (CSC_EXE.exists() and NT8_CORE_DLL.exists() and NT8_GUI_DLL.exists() and NT8_CUSTOM_DLL.exists()):
            print(
                f"[NT8] Skipping csc compile check (Core={NT8_CORE_DLL.exists()}, Gui={NT8_GUI_DLL.exists()}, Custom={NT8_CUSTOM_DLL.exists()}); press F5 inside NinjaScript Editor."
            )
            return
        with tempfile.TemporaryDirectory() as tmp:
            out_dll = Path(tmp) / "EdgeLabFundedSyncNt8.dll"
            cmd = [
                str(CSC_EXE),
                "/nologo",
                "/target:library",
                "/warnaserror",
                f"/out:{out_dll}",
                "/r:System.dll",
                "/r:System.Core.dll",
                "/r:System.ComponentModel.DataAnnotations.dll",
                "/r:System.Xml.dll",
                f"/r:{WPF_DIR / 'PresentationCore.dll'}",
                f"/r:{WPF_DIR / 'PresentationFramework.dll'}",
                f"/r:{WPF_DIR / 'WindowsBase.dll'}",
                f"/r:{NT8_CORE_DLL}",
                f"/r:{NT8_GUI_DLL}",
                f"/r:{NT8_CUSTOM_DLL}",
                *cs_paths,
            ]
            res = subprocess.run(cmd, capture_output=True, check=False)
            if res.returncode != 0:
                out_s = res.stdout.decode("cp850", errors="replace") if res.stdout else ""
                err_s = res.stderr.decode("cp850", errors="replace") if res.stderr else ""
                raise RuntimeError(f"NT8 compile failed:\n{out_s}\n{err_s}")
            print(f"[NT8] Compiled clean (0 errors, 0 warnings) -> {len(NT8_FILES)} files")


def main() -> None:
    global CALGO_ROBOTS, CALGO_API_DLL, MT5_TERMINALS, NT8_USER_STRAT, NT8_CUSTOM_DLL

    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("ctrader", "mt5", "nt8", "all"), default="all")
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--nt8-dir", help="Custom NinjaTrader 8 bin/Custom/Strategies path")
    parser.add_argument("--calgo-dir", help="Custom cAlgo/Sources/Robots path")
    parser.add_argument("--mt5-mql5-dir", help="Custom MT5 MQL5 folder path")
    parser.add_argument("--metaeditor", help="Custom MetaEditor64.exe path (used with --mt5-mql5-dir)")
    args = parser.parse_args()

    if args.nt8_dir:
        NT8_USER_STRAT = Path(args.nt8_dir)
        NT8_USER_STRAT.mkdir(parents=True, exist_ok=True)
        cand_custom = NT8_USER_STRAT.parent / "NinjaTrader.Custom.dll"
        if cand_custom.exists():
            NT8_CUSTOM_DLL = cand_custom

    if args.calgo_dir:
        CALGO_ROBOTS = Path(args.calgo_dir)
        CALGO_ROBOTS.mkdir(parents=True, exist_ok=True)
        cand_api = CALGO_ROBOTS.parent.parent / "API" / "cAlgo.API.dll"
        if cand_api.exists():
            CALGO_API_DLL = cand_api

    if args.mt5_mql5_dir:
        mql5_p = Path(args.mt5_mql5_dir)
        me_p = Path(args.metaeditor) if args.metaeditor else (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "MetaTrader 5" / "MetaEditor64.exe")
        MT5_TERMINALS = [("MT5_Custom", mql5_p, me_p)]

    if args.target in ("nt8", "all"):
        sync_and_compile_nt8(install=not args.no_install, compile_check=not args.no_compile)
    if args.target in ("ctrader", "all"):
        sync_and_compile_ctrader(install=not args.no_install, compile_check=not args.no_compile)
    if args.target in ("mt5", "all"):
        sync_and_compile_mt5(install=not args.no_install, compile_check=not args.no_compile)


if __name__ == "__main__":
    main()
