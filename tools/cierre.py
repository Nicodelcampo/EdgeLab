#!/usr/bin/env python3
"""Cierre de un turno de trabajo en UN comando (AUTOMATIZACION_PROCESOS_20261111 C3): regenera todos los archivos generados y
corre los tests que los vigilan, para que ningún commit deje el CI rojo por un índice viejo (pasó dos veces el 2026-11-11).
  python tools/cierre.py            # regenera y prueba; sale 1 si algo falla
  python tools/cierre.py --rapido   # sólo regenera
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGENERAR = [["tools/reconstruir_kernels.py"], ["tools/contexto_vivo.py", "--write"], ["tools/docs_index.py", "--write"], ["tools/existente.py", "catalogo", "--write"], ["tools/familias.py", "--write"],
             ["tools/factores.py", "--write"], ["tools/remediciones.py", "--write"], ["tools/agentes.py", "--write"],
             ["tools/check_modules.py", "--write"]]
TESTS = ["tests/test_existente.py", "tests/test_persistencia_contexto.py", "tests/test_holdout_a5.py", "tests/research/test_m1nt8.py", "tests/research/test_u1_zonas_grilla_sellado.py", "tests/test_verify_indices.py", "tests/research/test_factores.py", "tests/test_holdout_unico.py",
         "tests/test_dependencias_lock.py", "tests/test_parametros_por_defecto.py", "tests/test_cadena_accesible.py",
         "tests/test_auditoria_patrones.py",                       # auditoría de corridas 2026-11-16
         "tests/test_guardas_principiante_20261117.py",            # K27–K33: potencia, simuladores, pre-registros, contador, costos
         # K34 (2026-11-17): lo que se rompió sin que el cierre lo viera (kernels embebidos, costos, embudo, promoción, índice de docs)
         "tests/research/test_kernel_areas_al_dia.py", "tests/research/test_luximb_grilla.py::test_kernel_e0_al_dia", "tests/test_costos_canonicos.py",
         "tests/research/test_embudo_runners.py", "tests/test_autopilot_promocion.py", "tests/research/test_holdout_ventanas.py",
         "tests/foundation/test_product_registry.py", "tests/research/test_canastas_vigentes.py",
         "tests/research/test_lucid_canastas.py", "tests/research/test_vida_ventaja.py"]


def main() -> int:
    mal = 0
    for c in REGENERAR:
        r = subprocess.run([sys.executable, *c], cwd=ROOT, capture_output=True, text=True)
        print(("ok   " if not r.returncode else "FALLA"), " ".join(c)); mal += bool(r.returncode)
        if r.returncode: print((r.stdout + r.stderr)[-600:])
    if "--rapido" not in sys.argv:
        r = subprocess.run([sys.executable, "-m", "pytest", *[t for t in TESTS if (ROOT / t.split("::")[0]).exists()], "-q", "-p", "no:cacheprovider"],
                           cwd=ROOT, capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-600:]); mal += bool(r.returncode)
        if r.returncode: print(r.stdout[-2500:])
    st = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout
    print("archivos cambiados:\n" + (st or "  (ninguno)"))
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
