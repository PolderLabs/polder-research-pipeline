"""Small non-blocking advisory locks for local state transitions."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import IO


class LockBusyError(RuntimeError):
    """Raised when another process currently owns a named local lock."""


def acquire_file_lock(path: Path, *, wait: bool = False) -> IO[bytes]:
    """Acquire an OS-released, non-blocking lock and return its open handle.

    The lock file is intentionally persistent: deleting a locked inode can let
    another process lock a replacement inode while the first process is still
    active. The operating system releases the advisory lock on process exit.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if not wait:
                        raise LockBusyError(f"state is already locked: {path.name}") from exc
                    time.sleep(0.05)
        else:
            import fcntl

            try:
                operation = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB
                fcntl.flock(handle.fileno(), operation)
            except BlockingIOError as exc:
                raise LockBusyError(f"state is already locked: {path.name}") from exc
        return handle
    except Exception:
        handle.close()
        raise


def release_file_lock(handle: IO[bytes]) -> None:
    """Release an advisory lock and close its descriptor."""
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


__all__ = ["LockBusyError", "acquire_file_lock", "release_file_lock"]
