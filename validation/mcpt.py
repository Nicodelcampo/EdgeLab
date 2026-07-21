"""MCPT — Monte Carlo Permutation Test (Timothy Masters) para estrategias
intradia sobre matrices RTH dia × minuto.

Permutacion POR SESION que preserva la apertura del dia, la distribucion de
los retornos intrabar y el vinculo (H,L,C,V) de cada barra, pero destruye el
orden temporal intradia:
  - por dia, se toman los componentes log de cada barra: g_m = log(O_m/C_{m-1}),
    h_m = log(H_m/O_m), l_m = log(L_m/O_m), c_m = log(C_m/O_m)
  - se permutan los indices de barra (un solo shuffle por dia, los 4 componentes
    y el volumen viajan juntos -> se preserva la coherencia intrabar)
  - se reconstruye el camino desde el open real del dia.

El p-value se computa re-corriendo el PIPELINE COMPLETO (incluida la
estimacion de features historicas) sobre cada permutacion:
  p = (1 + #{perm: stat_perm >= stat_real}) / (1 + n_perm)
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _permute_day(O_row, H_row, L_row, C_row, V_row, perm, o0):
    n = len(O_row)
    Op = np.full(n, np.nan); Hp = np.full(n, np.nan)
    Lp = np.full(n, np.nan); Cp = np.full(n, np.nan)
    Vp = np.full(n, np.nan)
    prev_c = o0
    for m in range(n):
        j = perm[m]
        if np.isnan(O_row[j]) or O_row[j] <= 0:
            continue
        g = np.log(O_row[j] / C_row[j - 1]) if (j > 0 and not np.isnan(C_row[j - 1]) and C_row[j - 1] > 0) else 0.0
        h = np.log(H_row[j] / O_row[j])
        l = np.log(L_row[j] / O_row[j])
        c = np.log(C_row[j] / O_row[j])
        o = prev_c * np.exp(g)
        Op[m] = o; Hp[m] = o * np.exp(h); Lp[m] = o * np.exp(l); Cp[m] = o * np.exp(c)
        Vp[m] = V_row[j]
        prev_c = Cp[m]
    return Op, Hp, Lp, Cp, Vp


def permute_rth(O, H, L, C, V, rng):
    """Permuta cada dia de las matrices (n_dias, n_min). Devuelve copias."""
    nd, nm = O.shape
    Op = np.empty_like(O); Hp = np.empty_like(H)
    Lp = np.empty_like(L); Cp = np.empty_like(C); Vp = np.empty_like(V)
    for i in range(nd):
        if np.isnan(O[i, 0]):
            Op[i] = O[i]; Hp[i] = H[i]; Lp[i] = L[i]; Cp[i] = C[i]; Vp[i] = V[i]
            continue
        perm = rng.permutation(nm)
        Op[i], Hp[i], Lp[i], Cp[i], Vp[i] = _permute_day(O[i], H[i], L[i], C[i], V[i], perm, O[i, 0])
    return Op, Hp, Lp, Cp, Vp


def mcpt(stat_fn, O, H, L, C, V, n_perm=500, seed=7, verbose=True):
    """stat_fn(O,H,L,C,V) -> escalar (ej. PnL neto total en ticks del pipeline
    completo). Devuelve (stat_real, p_value, stats_perm)."""
    rng = np.random.RandomState(seed)
    real = stat_fn(O, H, L, C, V)
    stats = np.empty(n_perm)
    ge = 0
    for k in range(n_perm):
        Op, Hp, Lp, Cp, Vp = permute_rth(O, H, L, C, V, rng)
        stats[k] = stat_fn(Op, Hp, Lp, Cp, Vp)
        if stats[k] >= real:
            ge += 1
        if verbose and (k + 1) % 100 == 0:
            p_run = (1 + ge) / (1 + k + 1)
            print(f"   MCPT {k+1}/{n_perm}  p_parcial={p_run:.3f}", flush=True)
    p = (1 + ge) / (1 + n_perm)
    return real, p, stats
