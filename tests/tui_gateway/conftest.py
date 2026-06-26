"""tui_gateway shared test fixtures + test-process teardown guard.

The protocol tests for `tui_gateway.server` originally lived in one 1500-line
`test_protocol.py` (65 tests). That single file ran ~45s in isolation but, under
CI's parallel per-file load, the run itself overran the per-file 140s timeout and
the file was SIGKILL'd *before* pytest could write its summary (the CI log reported
it as "no tests ran / timeout before collection"). It was split into
`test_protocol_core.py`, `test_protocol_session.py`, and `test_protocol_dispatch.py`
so each file's runtime stays comfortably under the timeout even under contention.
The shared `server` / `capture` / `_restore_stdout` fixtures moved here so all three
files reuse them.

Sibling tui_gateway test files (`test_undo_command.py`, `test_goal_command.py`, …)
that define their own `server` fixture shadow the one below; none use `capture`; and
the autouse `_restore_stdout` is a harmless no-op when a test never touches stdout.

Teardown guard: `tui_gateway.server` starts module-level non-daemon threads (the
`ThreadPoolExecutor` `_pool` exercised by the `test_dispatch_*` long-handler tests,
plus session/atexit shutdown) that Python's interpreter-exit joins with no timeout,
which can itself hang the file process to the 140s SIGKILL. So in
`pytest_unconfigure` — after pytest has written its results and the terminal summary,
but before the hung atexit handlers run — we hard-exit the test process with pytest's
real exit status. Scoped to tui_gateway tests, changes no product code.
"""

import io
import os
import sys
from unittest.mock import MagicMock

import pytest

_EXIT = {"code": 0}

# ── Shared fixtures (used by the split test_protocol_*.py files) ──────────────

_original_stdout = sys.stdout


@pytest.fixture(autouse=True)
def _restore_stdout():
    yield
    sys.stdout = _original_stdout


@pytest.fixture(scope="module")
def _server_module():
    """Import ``tui_gateway.server`` once per file, with its heavy/unwanted deps
    mocked — WITHOUT a per-test ``patch.dict(sys.modules)``.

    ``patch.dict("sys.modules", …)`` snapshots the whole module table on enter
    and *restores it verbatim* on exit, which evicts every module the
    ``command.dispatch`` / ``slash.exec`` handlers lazily import (the entire
    ``hermes_cli`` command registry). With the old per-test fixture that meant a
    full ~9 000-module re-import on every test (~2 s each) — the runtime blow-up
    that pushed the old single ``test_protocol.py`` past the 140 s CI per-file
    timeout. Mocking the four deps once per module and importing ``server`` once
    leaves the lazily-imported tree cached across tests, so each dispatch test
    drops from ~2 s to ~0.1 s.

    The four mocks are left in ``sys.modules`` for the file's lifetime: they are
    test doubles only ``tui_gateway.server`` consults, every test in these files
    wants them mocked, and per-file process isolation stops them leaking to
    other files. ``server`` is imported (not reloaded) exactly once, so the
    module's atexit hooks register only once — avoiding the ``_enter_buffered_busy``
    double-shutdown race the original fixture guarded against.
    """
    import importlib

    mock_keys = {
        "hermes_constants": MagicMock(get_hermes_home=MagicMock(return_value="/tmp/hermes_test")),
        "hermes_cli.env_loader": MagicMock(),
        "hermes_cli.banner": MagicMock(),
        "hermes_state": MagicMock(),
    }
    saved = {k: sys.modules.get(k) for k in mock_keys}
    sys.modules.update(mock_keys)
    try:
        yield importlib.import_module("tui_gateway.server")
    finally:
        for k, original in saved.items():
            if original is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = original


@pytest.fixture()
def server(_server_module):
    mod = _server_module
    yield mod
    # Per-test state reset (the module is shared across the file). Close any real
    # ``_SlashWorker`` subprocess a test spawned before dropping the session
    # refs — a bare ``_sessions.clear()`` orphans the HermesCLI subprocess at
    # ``session["slash_worker"]`` (its close path, ``_finalize_session``, is
    # bypassed by clear()), leaking workers across tests. ``_SlashWorker.close()``
    # is poll()-guarded and idempotent. ``_methods`` is NOT cleared — it is
    # populated once at import time and never re-registered here.
    for _sess in list(mod._sessions.values()):
        _worker = _sess.get("slash_worker") if isinstance(_sess, dict) else None
        if _worker is not None:
            try:
                _worker.close()
            except Exception:
                pass
    mod._sessions.clear()
    mod._pending.clear()
    mod._answers.clear()


@pytest.fixture()
def capture(server):
    """Redirect server's real stdout to a StringIO and return (server, buf)."""
    buf = io.StringIO()
    server._real_stdout = buf
    return server, buf


def pytest_sessionfinish(exitstatus):
    # Record only — exiting here would pre-empt the terminal summary line that the
    # per-file runner parses. The actual hard-exit happens in pytest_unconfigure.
    _EXIT["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if os.environ.get("HERMES_NO_TEARDOWN_HARDEXIT"):
        return
    # Results + summary are written by now. Bypass tui_gateway.server's
    # non-daemon-thread teardown that would otherwise hang to the 140s file-timeout.
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        os._exit(_EXIT["code"])
