#!/usr/bin/env python3
"""Contract tests for the Tier-4 do-not-touch allowlist (ADR-0003 D4).

Pure stdlib (unittest) so it runs anywhere without the pytest tree or CI:

    python -m unittest docs.viloforge.rebrand.test_exclusions
    # or, from this directory:
    python test_exclusions.py

These pin the *behavioral contract* (does the guard protect/skip the right
tokens), not a snapshot of repo counts — that lives in scan.py as a report.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exclusions as ex  # noqa: E402


def _names(text, **kw):
    return {n for _, _, n in ex.protected_spans(text, **kw)}


class DoNotTouchProtected(unittest.TestCase):
    """Every D4 category must protect its representative tokens."""

    def test_model_ids(self):
        for s in ("nousresearch/hermes-3-llama-3.1-405b", "hermes-4-70b",
                  "deephermes-3", "Hermes-2-Pro", "hermes-4.3-36b"):
            self.assertTrue(ex.line_protected(s), s)
            self.assertIn("hermes-model-id", _names(s))

    def test_model_switch_guard_literal(self):
        # The non-agentic guard name + its model-id checks must be untouchable.
        self.assertIn("nous-hermes", _names("def is_nous_hermes_non_agentic(model_name):"))
        self.assertTrue(ex.line_protected('if "hermes-3" in model_name or "hermes-4" in model_name:'))

    def test_nousresearch_surface(self):
        for s in ("https://portal.nousresearch.com/auth", "security@nousresearch.com",
                  "github.com/NousResearch/hermes-agent", 'author = "Nous Research"  # nousresearch'):
            self.assertIn("nousresearch", _names(s), s)

    def test_nous_env_prefix_case_sensitive(self):
        self.assertIn("nous-env-prefix", _names("NOUS_API_KEY"))
        self.assertIn("nous-env-prefix", _names("os.getenv('NOUS_CLIENT_ID')"))
        # lowercase nous_api is NOT the env prefix (and must not be caught by it)
        self.assertNotIn("nous-env-prefix", _names("nous_api_key = 1"))

    def test_x_nous_headers(self):
        self.assertIn("x-nous-header", _names('headers["x-nous-credits-remaining"]'))

    def test_model_family_spaced_prose(self):
        # The model family is also written with a space in prose; a \bHermes\b
        # codemod must not rewrite these upstream model references.
        self.assertIn("nous-hermes-spaced", _names("the Nous Hermes models"))
        self.assertTrue(ex.line_protected("Nous Hermes is the model family."))
        for s in ("built on Hermes 3", "Hermes 4 is non-agentic"):
            self.assertIn("hermes-model-spaced", _names(s), s)
            self.assertTrue(ex.line_protected(s), s)

    def test_allcaps_banner_is_rebrandable_not_protected(self):
        # The cli.py framework banner "⚕ NOUS HERMES ⚕" is a Tier-1 rebrand
        # target (→ VILOFORGE), distinguished from the prose model family by its
        # all-caps form. It must NOT be protected.
        self.assertNotIn("nous-hermes-spaced", _names("⚕ NOUS HERMES ⚕"))
        self.assertFalse(ex.line_protected("⚕ NOUS HERMES ⚕", include_tier3=True))

    def test_sibling_projects(self):
        self.assertIn("psyche", _names("import psyche.core"))
        self.assertIn("atropos", _names("from atropos import rollouts"))

    def test_trap_host_protects_full_host(self):
        # The trap: hermes inside *.nousresearch.com is upstream infra. The
        # protected span must COVER the leading `hermes` so a span-aware codemod
        # cannot rewrite the host into viloforge-agent.nousresearch.com.
        line = "BASE = 'https://setup.hermes-agent.nousresearch.com/v1'"
        spans = ex.protected_spans(line)
        self.assertTrue(spans)
        h = line.lower().index("hermes-agent")
        covered = any(s <= h < e for s, e, _ in spans)
        self.assertTrue(covered, "the hermes token in the host must sit inside a protected span")

    def test_docs_host_variant(self):
        self.assertTrue(ex.line_protected("docs-hermes--agent.nousresearch.com"))


class RebrandableNotProtected(unittest.TestCase):
    """The guard must NOT protect ordinary rebrandable brand tokens."""

    def test_brand_prose(self):
        for s in ("Hermes is a personal AI agent.", "Welcome to Hermes!",
                  "# Hermes Agent", "the Hermes desktop app"):
            self.assertFalse(ex.line_protected(s), s)

    def test_package_token_is_rebrandable(self):
        # `hermes-agent` (the PyPI/product token) is a Tier-2 target, NOT D4:
        # the char after `hermes-` is a letter, not [0-9], so no model-id match.
        s = "pip install hermes-agent[all]"
        self.assertFalse(ex.line_protected(s), s)

    def test_hermes_cli_only_protected_under_tier3(self):
        s = "from hermes_cli.config import load_config"
        # D4 alone does not protect the skeleton...
        self.assertFalse(ex.line_protected(s), s)
        # ...but a Tier-1/2 codemod running during the leash opts in to skip it.
        self.assertTrue(ex.line_protected(s, include_tier3=True), s)

    def test_hermes_env_only_protected_under_tier3(self):
        s = "HERMES_HOME = os.environ['HERMES_HOME']"
        self.assertFalse(ex.line_protected(s), s)
        self.assertTrue(ex.line_protected(s, include_tier3=True), s)

    def test_x_hermes_header_only_protected_under_tier3(self):
        # Our wire-contract headers are Tier-3 skeleton (kept aligned during the
        # leash), so they protect only when a codemod opts into tier3 — like the
        # rest of the skeleton. Mixed-case, so HERMES_[A-Z] does not cover them.
        for s in ('headers["X-Hermes-Session-Token"] = tok',
                  "res.headers['x-hermes-model']"):
            self.assertFalse(ex.line_protected(s), s)
            self.assertTrue(ex.line_protected(s, include_tier3=True), s)
            self.assertIn("x-hermes-header", _names(s, include_tier3=True), s)


class PathExclusions(unittest.TestCase):
    def test_nous_plugin_paths_excluded(self):
        for p in ("plugins/openrouter/nous/adapter.py", "plugins/foo/nous/deep/x.py",
                  "hermes_cli/nous_auth.py", "proxy/adapters/nous_portal.py",
                  "agent/portal_tags.py", "agent/nous_rate_guard.py"):
            ok, reason = ex.path_excluded(p)
            self.assertTrue(ok, f"{p} should be path-excluded")
            self.assertTrue(reason)

    def test_ordinary_paths_not_excluded(self):
        for p in ("plugins/openrouter/adapter.py", "hermes_cli/config.py",
                  "README.md", "agent/memory_manager.py"):
            ok, _ = ex.path_excluded(p)
            self.assertFalse(ok, f"{p} should NOT be path-excluded")


class SpanShape(unittest.TestCase):
    def test_spans_are_sorted_and_bounded(self):
        line = "NOUS_API_KEY and hermes-3 and nousresearch.com"
        spans = ex.protected_spans(line)
        self.assertTrue(spans)
        self.assertEqual(spans, sorted(spans))
        for s, e, _ in spans:
            self.assertTrue(0 <= s < e <= len(line))


if __name__ == "__main__":
    unittest.main(verbosity=2)
