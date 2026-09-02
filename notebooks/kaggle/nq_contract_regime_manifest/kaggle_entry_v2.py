#!/usr/bin/env python3
"""Entrypoint fino para Kaggle: fija sys.argv y ejecuta
nq_contract_regime_manifest_runner.py sin modificarlo (ese archivo es el que
se audito/testeo). Kaggle 'script' kernels no aceptan argumentos de linea de
comandos propios -- este wrapper es el unico lugar donde se fijan.

modo scan-and-build con el template de evidencia SIN aprobar (approved=False,
generado por el propio scan): produce el candidato v2 con status
ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED si falta evidencia real de
completitud, nunca certifica en falso. Aprobar evidencia es una decision
separada, posterior, de Nico -- no de esta corrida.
"""
import runpy
import sys
from pathlib import Path

EXPECTED_CODE_COMMIT = "ab89de5ff176bab5abb38cc17c5e5f6db568f763"
OUTPUT_DIR = "/kaggle/working/nq_contract_regime_manifest_v2"

sys.argv = [
    "nq_contract_regime_manifest_runner.py",
    "--mode", "scan-and-build",
    "--expected-code-commit", EXPECTED_CODE_COMMIT,
    "--output-dir", OUTPUT_DIR,
    "--evidence", f"{OUTPUT_DIR}/nq_complete_session_evidence_template_v1.json",
]

runpy.run_path(str(Path(__file__).parent / "nq_contract_regime_manifest_runner.py"),
                run_name="__main__")
