"""Timing decorator."""

import logging
from collections.abc import Callable
from functools import wraps
from time import perf_counter

logger = logging.getLogger(__name__)


def timed[**P, T](fn: Callable[P, T]) -> Callable[P, T]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            logger.info("%s: %.3f ms", fn.__name__, (perf_counter() - start) * 1000)

    return wrapper
