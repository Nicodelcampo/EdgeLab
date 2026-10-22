"""Emulación mínima de `fcntl.flock` en Windows, SÓLO para la suite (la carga `tests/conftest.py` si no existe `fcntl`).

El autopilot corre en el Debian con `fcntl` real y sus módulos protegidos (`fdr.py`) lo importan directo; en Windows esos
imports fallaban y la suite no podía probar el ciclo. Esto no es un stub nulo: bloquea de verdad con `msvcrt.locking`
sobre el primer byte del archivo, así que las pruebas de "un solo controlador" siguen probando exclusión mutua.
"""
import msvcrt
import os
import time

LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8


def flock(f, op):
    fd = f if isinstance(f, int) else f.fileno()
    pos = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        if op & LOCK_UN:
            try: msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError: pass
            return
        if op & LOCK_NB:
            try: msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as e: raise BlockingIOError(11, "Resource temporarily unavailable") from e
            return
        while True:                                   # bloqueante, como flock
            try: msvcrt.locking(fd, msvcrt.LK_NBLCK, 1); return
            except OSError: time.sleep(0.01)
    finally:
        os.lseek(fd, pos, os.SEEK_SET)
