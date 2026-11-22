"""Run short blocking work off the GUI thread.

Password hashing is deliberately slow (PBKDF2, 600,000 rounds). Doing it on the
GUI thread would freeze every animation for a few hundred milliseconds, so the
auth screens hand it to the global thread pool and get the result back through
a queued signal.

Only pass work that does not touch the SQLite connection: ``sqlite3``
connections belong to the thread that created them.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, work: Callable[[], object]) -> None:
        super().__init__()
        self.setAutoDelete(False)  # kept alive by ``_live`` until it reports back
        self._work = work
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self._work()
        except Exception as exc:  # noqa: BLE001 - reported to the GUI thread
            self.signals.failed.emit(str(exc) or exc.__class__.__name__)
            return
        self.signals.done.emit(result)


_live: set[_Task] = set()


def run_in_background(
    work: Callable[[], object],
    on_done: Callable[[object], None],
    on_error: Callable[[str], None] | None = None,
) -> None:
    """Run ``work`` on a pool thread; call ``on_done(result)`` on the GUI thread.

    Pass bound methods of a ``QObject`` as callbacks: Qt then drops the
    connection automatically if that object is destroyed before the work ends.
    """
    task = _Task(work)
    _live.add(task)

    task.signals.done.connect(on_done)
    if on_error is not None:
        task.signals.failed.connect(on_error)
    # Release the task once it has reported either way.
    task.signals.done.connect(lambda _result, t=task: _live.discard(t))
    task.signals.failed.connect(lambda _message, t=task: _live.discard(t))

    QThreadPool.globalInstance().start(task)
