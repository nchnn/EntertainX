"""Run blocking work (HTTP, disk) off the Qt main thread.

``run_async`` executes ``fn`` on a worker and delivers its result or error back
on the thread that called it, through a queued signal. Nothing in the UI ever
waits on the network.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from shiboken6 import isValid

POOL = QThreadPool()
POOL.setMaxThreadCount(8)

# Workers and their signal objects must outlive the call that created them,
# otherwise a collected wrapper drops the queued result.
_LIVE: set[object] = set()


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)


class _Task(QRunnable):
    def __init__(self, fn: Callable[..., Any], args: tuple, kwargs: dict) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(exc)
        else:
            self.signals.done.emit(result)


def run_async(
    fn: Callable[..., Any],
    *args: Any,
    on_done: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    owner: QObject | None = None,
    **kwargs: Any,
) -> None:
    """Call ``fn(*args, **kwargs)`` on a worker thread.

    ``on_done``/``on_error`` run on the calling (GUI) thread. If ``owner`` has
    been deleted by the time the result arrives, the callbacks are skipped so a
    closed page is never touched.
    """
    task = _Task(fn, args, kwargs)
    _LIVE.add(task)

    def alive() -> bool:
        return owner is None or isValid(owner)

    def finish() -> None:
        _LIVE.discard(task)

    def deliver_done(result: Any) -> None:
        finish()
        if on_done is not None and alive():
            on_done(result)

    def deliver_failed(error: Exception) -> None:
        finish()
        if on_error is not None and alive():
            on_error(error)

    queued = Qt.ConnectionType.QueuedConnection
    task.signals.done.connect(deliver_done, queued)
    task.signals.failed.connect(deliver_failed, queued)
    POOL.start(task)
