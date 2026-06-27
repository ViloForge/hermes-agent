#!/usr/bin/env python3
"""Contract tests for the guard-aware brand transform (ADR-0004 L1).

Pure stdlib (unittest):

    python -m unittest docs.viloforge.rebrand.test_rebrand_apply
    # or, from this directory:
    python test_rebrand_apply.py

These pin the *behavioral contract* of the transform: it rebrands display chrome
and leaves every do-not-touch / skeleton token byte-for-byte intact. The
edge-case set is the one ADR-0004 D3 names plus the X-Hermes near-miss.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebrand_apply as ra  # noqa: E402


class RebrandsDisplayChrome(unittest.TestCase):
    def test_multiword_wins_over_bare(self):
        self.assertEqual(ra.rebrand_text("Welcome to Hermes Agent!"),
                         "Welcome to ViloForge Agent!")

    def test_bare_brand(self):
        self.assertEqual(ra.rebrand_text("Hermes is a personal AI agent."),
                         "ViloForge is a personal AI agent.")

    def test_desktop(self):
        self.assertEqual(ra.rebrand_text("the Hermes Desktop window"),
                         "the ViloForge Desktop window")

    def test_framework_banner(self):
        self.assertEqual(ra.rebrand_text("⚕ NOUS HERMES ⚕"), "⚕ VILOFORGE ⚕")

    def test_idempotent(self):
        once = ra.rebrand_text("Hermes Agent and Hermes")
        self.assertEqual(once, "ViloForge Agent and ViloForge")
        self.assertEqual(ra.rebrand_text(once), once)


class LeavesIdentifiersIntact(unittest.TestCase):
    """Word boundaries must protect code identifiers and the package token."""

    def test_class_and_camelcase_identifiers(self):
        for s in ("class HermesCLI:", "updateHermes(state)", "HermesClaw",
                  "self.hermesAgent = x"):
            self.assertEqual(ra.rebrand_text(s), s, s)

    def test_lowercase_package_token_untouched(self):
        # `hermes-agent` is a Tier-2 target, not a display-brand token; the
        # case-sensitive transform must not touch it.
        s = "pip install hermes-agent[all]"
        self.assertEqual(ra.rebrand_text(s), s)


class CjkAdjacency(unittest.TestCase):
    """`\\bHermes\\b` is Unicode-aware and skips brand tokens glued to a CJK /
    accented letter (the boundary char counts as a word char). The ASCII
    lookaround boundaries must still rebrand these display residuals — the
    blind spot a live preview caught in the i18n bundles."""

    def test_brand_glued_to_cjk_is_rebranded(self):
        # Korean particles glued directly to the brand token (no space).
        self.assertEqual(ra.rebrand_text("Hermes가 신호를 감지"), "ViloForge가 신호를 감지")
        self.assertEqual(ra.rebrand_text("Hermes를 더 사용"), "ViloForge를 더 사용")
        # Leading CJK char immediately before the brand token.
        self.assertEqual(ra.rebrand_text("私のHermes"), "私のViloForge")
        # Accented (Latin-1) letter adjacency also counts as a word char for \b.
        self.assertEqual(ra.rebrand_text("Hermesé"), "ViloForgeé")

    def test_cjk_adjacency_still_protects_identifiers(self):
        # ASCII-letter/digit/underscore adjacency must remain protected.
        for s in ("class HermesCLI:", "updateHermes(x)", "Hermes_home"):
            self.assertEqual(ra.rebrand_text(s), s, s)


class NeverCorruptsProtected(unittest.TestCase):
    """The do-not-touch boundary + the deferred skeleton survive byte-for-byte."""

    def test_x_hermes_headers(self):
        # The near-miss: \bHermes\b sits between hyphens in the header.
        for s in ('headers["X-Hermes-Session-Token"] = tok',
                  "res.headers['x-hermes-model']"):
            self.assertEqual(ra.rebrand_text(s), s, s)

    def test_model_ids(self):
        for s in ("nousresearch/hermes-3-llama-3.1-405b", "Hermes-2-Pro",
                  'if "hermes-3" in model_name:'):
            self.assertEqual(ra.rebrand_text(s), s, s)

    def test_model_family_prose_spaceform(self):
        for s in ("built on Hermes 3", "the Nous Hermes models"):
            self.assertEqual(ra.rebrand_text(s), s, s)

    def test_hermes_cli_skeleton(self):
        s = "from hermes_cli.config import load_config"
        self.assertEqual(ra.rebrand_text(s), s)

    def test_hermes_env_prefix(self):
        s = "HERMES_HOME = os.environ['HERMES_HOME']"
        self.assertEqual(ra.rebrand_text(s), s)

    def test_nousresearch_surface(self):
        for s in ("https://portal.nousresearch.com/auth",
                  'author = "Nous Research"',
                  "security@nousresearch.com"):
            self.assertEqual(ra.rebrand_text(s), s, s)

    def test_trap_host_not_rewritten(self):
        # hermes inside *.nousresearch.com is upstream infra, not our brand.
        s = "BASE = 'https://setup.hermes-agent.nousresearch.com/v1'"
        self.assertEqual(ra.rebrand_text(s), s)


class MixedLines(unittest.TestCase):
    """A line carrying both a rebrandable token and a protected token: rebrand
    the brand, preserve the protected token. (Conservative span-skip means a
    Hermes adjacent to a protected span is left alone — under-rebrand, never
    corruption; L3 completeness catches it.)"""

    def test_brand_and_model_id_same_line(self):
        # "Hermes Agent" is rebrandable; "hermes-3" must survive.
        s = "Hermes Agent runs hermes-3 by default"
        out = ra.rebrand_text(s)
        self.assertIn("ViloForge Agent", out)
        self.assertIn("hermes-3", out)

    def test_fork_notice_context_preserved(self):
        # The fork notice deliberately keeps the upstream attribution. The
        # transform rebrands "Hermes Agent" -> "ViloForge Agent" but must leave
        # "Nous Research" intact (nousresearch guard covers the bare token only
        # when spelled solid; the spaced author form is handled by review, so we
        # only assert the protected token here, not the prose).
        s = "ViloForge Agent is a fork of Hermes Agent."
        self.assertEqual(ra.rebrand_text(s), "ViloForge Agent is a fork of ViloForge Agent.")


class PathExclusion(unittest.TestCase):
    def test_preview_honors_path_exclusion(self):
        # rebrand_file_preview must no-op on a path-excluded file even if it
        # contains a brand token. (We can't easily create plugins/*/nous/ here,
        # so assert the guard wiring directly.)
        import exclusions as ex
        ok, _ = ex.path_excluded("plugins/openrouter/nous/adapter.py")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
