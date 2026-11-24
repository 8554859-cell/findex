"""Timing decorator."""
from functools import wraps
from time import perf_counter


def timed(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            print(f"{fn.__name__}: {(perf_counter()-start)*1000:.3f} ms")
    return wrapper
