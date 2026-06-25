#!/usr/bin/env python3
"""Contract tests for the global completeness sweep (ADR-0004 L3, repo-wide).

Pure stdlib (unittest):

    python -m unittest docs.viloforge.rebrand.test_completeness
    # or, from this directory:
    python test_completeness.py

Pins: a residual is a line the transform would still change; do-not-touch and the
intentional-keep set are excluded; self-exempt paths (tooling/governance/generated)
are skipped; surfaces map correctly.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import completeness as c  # noqa: E402


def _lines(text):
    return [s for _, s in c.residual_lines(text)]


class DetectsResiduals(unittest.TestCase):
    def test_brand_name_line(self):
        # The exact Tier-1 miss: the TUI brand-name default.
        self.assertEqual(_lines("name: 'Hermes Agent',"), ["name: 'Hermes Agent',"])

    def test_theme_label_shadow(self):
        # The other miss: a backend theme label that shadowed the rebranded frontend.
        self.assertTrue(_lines('{"label": "Hermes Teal"}'))

    def test_already_rebranded_is_clean(self):
        self.assertEqual(_lines("name: 'ViloForge Agent',"), [])

    def test_standalone_brand_in_prose(self):
        self.assertTrue(_lines("Welcome to Hermes!"))


class ExcludesDoNotTouchAndKeeps(unittest.TestCase):
    def test_do_not_touch_not_flagged(self):
        # The transform already skips these — so they must not be residuals.
        for s in ('model = "nousresearch/hermes-3-llama"',
                  "HERMES_HOME = os.environ['HERMES_HOME']",
                  'headers["X-Hermes-Session-Token"]',
                  "from hermes_cli.config import load_config"):
            self.assertEqual(_lines(s), [], s)

    def test_intentional_keep_fork_notice(self):
        for s in ("ViloForge Agent — a ViloForge fork of Hermes Agent.",
                  "> [Hermes Agent](https://github.com/NousResearch/hermes-agent), originally by",
                  "keep this Hermes Agent line  # completeness-gate: keep"):
            self.assertEqual(_lines(s), [], s)

    def test_package_token_not_a_display_residual(self):
        # lowercase hermes-agent is a Tier-2 package token, not a \bHermes\b display token.
        self.assertEqual(_lines("pip install hermes-agent[all]"), [])


class SelfExemptAndSurfaces(unittest.TestCase):
    def test_self_exempt_paths(self):
        for p in ("docs/viloforge/rebrand/completeness.py",
                  "docs/adr/ADR-0003-rebrand-identity-and-tiering.md",
                  "AGENTS.md", "CLAUDE.md",
                  ".understand-anything/knowledge-graph.json"):
            self.assertTrue(c._self_exempt(p), p)

    def test_product_paths_not_exempt(self):
        for p in ("ui-tui/src/theme.ts", "hermes_cli/web_server.py", "web/src/app.tsx"):
            self.assertFalse(c._self_exempt(p), p)

    def test_surface_mapping(self):
        cases = {
            "ui-tui/src/banner.ts": "TUI",
            "web/src/themes/presets.ts": "Web",
            "website/docs/intro.md": "Docs",
            "apps/desktop/src/main.ts": "Desktop",
            "hermes_cli/web_server.py": "CLI",
            "cli.py": "CLI",
            "skills/github/SKILL.md": "Skills",
            "agent/run_agent.py": "Agent core",
            "tests/test_x.py": "Tests",
            "Dockerfile": "Other",
        }
        for path, want in cases.items():
            self.assertEqual(c.surface_of(path), want, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
