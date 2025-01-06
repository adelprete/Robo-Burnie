from __future__ import annotations

from typing import Generator

__all__ = ("file_lock",)

import fcntl
from contextlib import contextmanager


@contextmanager
def file_lock(script: str) -> Generator[None, None, None]:
    file_path = f"/tmp/{script}.lock"
    with open(file_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
        fcntl.flock(f, fcntl.LOCK_UN)
