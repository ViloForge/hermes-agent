#!/usr/bin/env python3
"""Contract tests for the diff-scoped do-not-touch gate (ADR-0004 L2).

Pure stdlib (unittest):

    python -m unittest docs.viloforge.rebrand.test_diff_gate
    # or, from this directory:
    python test_diff_gate.py

Pins: corruption is caught; correctly-rebranded lines (which still carry the
preserved protected token) are NOT false-failed; excluded files + the suppression
marker are honored; and every brand-bearing guard pattern has a signature (so the
gate cannot silently fall behind the guard).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diff_gate as dg  # noqa: E402
import exclusions as ex  # noqa: E402


def _diff(path, *added_lines):
    body = "".join(f"+{ln}\n" for ln in added_lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n+++ b/{path}\n"
        f"@@ -1,0 +1,{len(added_lines)} @@\n"
        f"{body}"
    )


class CatchesCorruption(unittest.TestCase):
    def test_x_hermes_corruption(self):
        v = dg.scan_diff(_diff("web/src/lib/api.ts", 'headers["X-ViloForge-Session-Token"] = t'))
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].signature, "x-viloforge-header")

    def test_model_id_corruption(self):
        v = dg.scan_diff(_diff("agent/x.py", '"viloforge-3-llama-3.1-405b"'))
        self.assertTrue(any(x.signature == "viloforge-model-id" for x in v))

    def test_skeleton_corruption(self):
        for line, sig in (("from viloforge_cli.config import x", "viloforge_cli"),
                          ("VILOFORGE_HOME = env['VILOFORGE_HOME']", "viloforge-env-prefix")):
            v = dg.scan_diff(_diff("z.py", line))
            self.assertTrue(any(x.signature == sig for x in v), (line, v))

    def test_model_family_prose_corruption(self):
        v = dg.scan_diff(_diff("README.md", "Built on Nous ViloForge models"))
        self.assertTrue(any(x.signature == "nous-viloforge-spaced" for x in v))

    def test_trap_host_corruption(self):
        v = dg.scan_diff(_diff("agent/auth.py", "https://viloforge-agent.nousresearch.com/v1"))
        self.assertTrue(any(x.signature == "trap-host-viloforge" for x in v))


class NoFalsePositives(unittest.TestCase):
    def test_correctly_rebranded_line_with_preserved_skeleton(self):
        # The crux: a correct rebrand keeps hermes_cli/HERMES_ intact on the line.
        for line in ("ViloForge Agent uses hermes_cli for config",
                     "HERMES_HOME drives the ViloForge Agent profile",
                     'res.headers["X-Hermes-Session-Token"]  # ViloForge dashboard'):
            self.assertEqual(dg.scan_diff(_diff("x.py", line)), [], line)

    def test_plain_brand_text_is_clean(self):
        for line in ("Welcome to ViloForge Agent!", "the ViloForge Desktop app", "⚕ VILOFORGE ⚕"):
            self.assertEqual(dg.scan_diff(_diff("README.md", line)), [], line)

    def test_preserved_model_ids_clean(self):
        for line in ("nousresearch/hermes-3-llama", "if 'hermes-4' in model:", "Built on Hermes 3"):
            self.assertEqual(dg.scan_diff(_diff("x.py", line)), [], line)

    def test_removed_lines_ignored(self):
        # A '-' line carrying a corruption-looking token is a deletion, not an add.
        diff = ("--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n"
                "-X-ViloForge-Session\n+X-Hermes-Session\n")
        self.assertEqual(dg.scan_diff(diff), [])


class HonorsGuardBoundaries(unittest.TestCase):
    def test_excluded_file_skipped(self):
        # A do-not-touch path (plugins/*/nous/**) is the guard's domain; the gate
        # does not second-guess edits there.
        v = dg.scan_diff(_diff("plugins/openrouter/nous/adapter.py", "x-viloforge-credits: 1"))
        self.assertEqual(v, [])

    def test_suppression_marker(self):
        v = dg.scan_diff(_diff("x.py", "viloforge_cli_shim = True  # rebrand-gate: ok"))
        self.assertEqual(v, [])

    def test_self_exemption(self):
        # The gate's own machinery + governance docs carry signature strings as
        # fixtures/examples; they must not flag themselves.
        for path in ("docs/viloforge/rebrand/test_diff_gate.py",
                     "docs/viloforge/rebrand/README.md",
                     "docs/viloforge/plans/2026-06-24-001-rebrand-tiered-plan.md",
                     "docs/adr/ADR-0004-machine-enforce-do-not-touch-and-rebrand-test-strategy.md",
                     ".github/workflows/rebrand-guard.yml"):
            self.assertEqual(dg.scan_diff(_diff(path, "example: X-ViloForge-Model + viloforge_cli")), [], path)

    def test_real_code_still_scanned(self):
        # Exemption must not over-broaden: ordinary source is still gated.
        v = dg.scan_diff(_diff("agent/run_agent.py", 'h["X-ViloForge-Session"] = t'))
        self.assertTrue(v)

    def test_line_numbers_reported(self):
        diff = ("--- a/x.py\n+++ b/x.py\n@@ -10,0 +10,2 @@\n"
                "+clean line\n+X-ViloForge-Model: x\n")
        v = dg.scan_diff(diff)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].line_no, 11)


class SignatureCompleteness(unittest.TestCase):
    """Every guard pattern whose protected token CONTAINS a rebrandable brand
    token must have a corruption signature — else a codemod could corrupt it
    undetected. nous-only tokens are unreachable by a Hermes→ViloForge map."""

    # guard patterns that cannot be corrupted by the brand mapping (pure-nous)
    _UNREACHABLE = {"nousresearch", "nous-env-prefix", "x-nous-header",
                    "psyche", "atropos", "trap-host-docs-hermes-agent"}

    def test_every_brand_bearing_pattern_has_a_signature(self):
        guarded = {s.guards for s in dg.CORRUPTION_SIGNATURES}
        for pat in ex.all_patterns(include_tier3=True):
            if pat.name in self._UNREACHABLE:
                continue
            self.assertIn(pat.name, guarded,
                          f"guard pattern '{pat.name}' has no diff-gate corruption signature")

    def test_signatures_fire_on_transform_of_a_protected_token(self):
        # End-to-end sanity: if the transform were (wrongly) run over a bare
        # protected token, the produced string trips the gate. We simulate the
        # corruption by mapping the brand token inside a representative string.
        corrupt = "X-Hermes-Session".replace("Hermes", "ViloForge")
        self.assertTrue(dg.scan_diff(_diff("x.py", corrupt)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
