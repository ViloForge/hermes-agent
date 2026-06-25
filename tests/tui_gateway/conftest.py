"""tui_gateway test-process teardown guard.

`tests/tui_gateway/test_protocol.py` passes (all 65 tests) but consistently times out
at the per-file 140s limit in CI — the hang is at **interpreter teardown**, not in any
test (a per-test `faulthandler_timeout` never fires; the file runs the full 140s). The
cause is `tui_gateway.server`'s module-level non-daemon threads — the `ThreadPoolExecutor`
(`_pool`, exercised by the `test_dispatch_*` long-handler tests) plus session/atexit
shutdown — which Python's interpreter-exit joins with no timeout. It reproduces only in
CI (passes locally even under full CPU saturation), and the module's own fixture
docstring already flags this shutdown path as fragile (`_enter_buffered_busy`).

Fixing the gateway's shutdown is risky without a local repro, and the tests themselves
are correct. So in `pytest_unconfigure` — after pytest has written its results and the
terminal summary, but before the hung atexit handlers run — we hard-exit the test
process with pytest's real exit status. This is scoped to tui_gateway tests, changes no
product code, and turns the opaque 140s SIGKILL into a clean, fast pass/fail.
"""

import os
import sys

import pytest

_EXIT = {"code": 0}


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
