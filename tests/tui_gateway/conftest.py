"""tui_gateway test diagnostics.

`tests/tui_gateway/test_protocol.py` passes locally (~6s) but consistently hits the
per-file 140s timeout in CI (`run_tests_parallel.py` then SIGKILLs it). The tests
themselves pass — the hang is at/near interpreter shutdown, in `tui_gateway.server`'s
fragile atexit path (the module registers `_pool.shutdown` + `_shutdown_sessions`
atexit hooks; the `server` fixture's docstring already notes a `_enter_buffered_busy`
shutdown race). A SIGKILL leaves no traceback, and it does not reproduce locally even
under CPU saturation, so we cannot see *where* it hangs.

This watchdog dumps every thread's stack to fd-level stderr a few seconds before the
140s SIGKILL, *and exits the process* (`exit=True`). The exit is the load-bearing part:
`run_tests_parallel.py` DISCARDS a file's output on the 140s timeout path, so a dump
that merely prints (exit=False) is thrown away with the SIGKILL. Exiting at 130s makes
it a normal (non-timeout) process exit whose stderr the runner keeps — so the dump
actually reaches the CI log. faulthandler writes from a watchdog thread at the C level,
so it fires even while the main thread is blocked in an atexit hook. It only triggers
on a genuine multi-minute hang — a normal run finishes long before and never sees it.
Opt out with `HERMES_NO_FAULT_WATCHDOG=1`.
"""

import faulthandler
import os
import sys

# A bit under run_tests_parallel.py's _DEFAULT_FILE_TIMEOUT_SECONDS (140s) so the
# process exits (dumping its stacks) before the runner's timeout-kill path discards
# the output.
_WATCHDOG_SECONDS = 130.0

if not os.environ.get("HERMES_NO_FAULT_WATCHDOG"):
    faulthandler.dump_traceback_later(_WATCHDOG_SECONDS, repeat=False, exit=True, file=sys.stderr)
