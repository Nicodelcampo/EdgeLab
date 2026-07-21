from numba import njit

@njit
def f():
    time_1h_us = 3600 * 1000000
    return time_1h_us

print(f())
