"""Tests for autolab.orchestrator — pure constants and helpers.

The orchestrator is largely impure (subprocess calls, file IO, claude
invocations), so these tests focus on the structural constants and the
NeurIPS section-brief helper.
"""

from __future__ import annotations

import autolab.orchestrator as orch


class TestPhaseConstants:
    def test_phases_order(self):
        # The fixed pipeline. Reordering would break checkpoints; this test
        # is a tripwire against accidental reorders.
        assert orch.PHASES == [
            "seed",
            "expand",
            "survey",
            "gap-fill",
            "screen",
            "design",
            "run",
            "critique",
            "write",
            "final",
        ]

    def test_retreat_phases_are_subset_of_phases(self):
        assert set(orch.RETREAT_PHASES).issubset(set(orch.PHASES))

    def test_retreat_phases_exclude_terminal_phases(self):
        # Retreat re-runs the middle of the pipeline; it must not reset the
        # terminal phases.
        assert "seed" not in orch.RETREAT_PHASES
        assert "write" not in orch.RETREAT_PHASES
        assert "final" not in orch.RETREAT_PHASES


class TestNeuripsSectionBrief:
    SECTIONS = [
        "outline",
        "abstract",
        "introduction",
        "related-work",
        "background",
        "data-models",
        "method",
        "experiments",
        "discussion",
        "conclusion",
        "broader-impact",
        "reproducibility",
    ]

    def test_returns_dict(self):
        d = orch._neurips_section_brief()
        assert isinstance(d, dict)

    def test_covers_every_section(self):
        d = orch._neurips_section_brief()
        assert set(d.keys()) == set(
            self.SECTIONS
        ), "section-brief keys must match the phase_write section list 1-for-1"

    def test_each_brief_is_nonempty_string(self):
        d = orch._neurips_section_brief()
        for key, body in d.items():
            assert isinstance(body, str), f"{key}: brief must be a string"
            assert len(body.strip()) >= 40, f"{key}: brief is suspiciously short"

    def test_briefs_mention_their_section(self):
        # Each brief is supposed to give NeurIPS-quality guidance specific
        # to its section. A few sanity-check keywords by section:
        d = orch._neurips_section_brief()
        assert "150–250" in d["abstract"] or "200" in d["abstract"]
        assert "falsifiable" in d["introduction"]
        assert "1-for-1" in d["experiments"] or "matching" in d["experiments"]
        assert (
            "no new claims" in d["conclusion"].lower() or "no new claim" in d["conclusion"].lower()
        )


class TestPhaseWriteSectionList:
    """phase_write iterates over a fixed section list. We don't call it
    (it would invoke claude), but we can read the source to confirm the
    sections match the brief keys."""

    def test_section_list_matches_brief(self):
        # Both surfaces are supposed to be 1-for-1; the orchestrator's
        # prompt construction asserts this implicitly. Catch drift early.
        brief_keys = set(orch._neurips_section_brief().keys())
        # The phase_write section list is private; read it via the source.
        import inspect

        src = inspect.getsource(orch.phase_write)
        for sec in brief_keys:
            assert (
                f'"{sec}"' in src
            ), f"section {sec!r} in brief but missing from phase_write section list"


class TestPhaseFinalAssemblyOrder:
    """phase_final assembles in a fixed NeurIPS order. Read the source and
    confirm the order matches what the SKILL.md and brief promise."""

    EXPECTED_HEADERS = [
        ("abstract", "## Abstract"),
        ("introduction", "## 1. Introduction"),
        ("related-work", "## 2. Related Work"),
        ("background", "## 3. Background and Preliminaries"),
        ("data-models", "## 4. Data and Models"),
        ("method", "## 5. Method"),
        ("experiments", "## 6. Experiments"),
        ("discussion", "## 7. Discussion and Limitations"),
        ("conclusion", "## 8. Conclusion"),
        ("broader-impact", "## 9. Broader Impact Statement"),
        ("reproducibility", "## 10. Reproducibility Statement"),
    ]

    def test_phase_final_source_contains_each_header(self):
        import inspect

        src = inspect.getsource(orch.phase_final)
        for sec, header in self.EXPECTED_HEADERS:
            assert (
                f'("{sec}", "{header}")' in src
            ), f"phase_final order entry missing or out of date: ({sec}, {header})"


class TestPolishPass:
    """phase_final invokes a polish pass at the end that re-reads the
    assembled paper and fills in/improves it via the paper-polisher
    skill. These tests pin the wiring without invoking claude."""

    def test_polish_helper_exists(self):
        assert hasattr(orch, "_run_polish_pass"), (
            "phase_final's polish step is missing — _run_polish_pass should "
            "exist alongside phase_final"
        )
        assert callable(orch._run_polish_pass)

    def test_phase_final_calls_polish(self):
        import inspect

        src = inspect.getsource(orch.phase_final)
        assert "_run_polish_pass(" in src, (
            "phase_final must invoke _run_polish_pass after writing the "
            "assembled paper-vFINAL.md"
        )

    def test_polish_invokes_paper_polisher_skill(self):
        import inspect

        src = inspect.getsource(orch._run_polish_pass)
        assert (
            '"paper-polisher"' in src
        ), "_run_polish_pass must call_claude with skill='paper-polisher'"
        assert '"polish"' in src, "_run_polish_pass must use phase='polish'"

    def test_polish_handles_failure_gracefully(self):
        import inspect

        src = inspect.getsource(orch._run_polish_pass)
        # Polish is best-effort: a failed claude call must not destroy the
        # pre-polish assembly. The implementation should catch SystemExit
        # (raised by call_claude on error) and restore from backup.
        assert "SystemExit" in src and "backup" in src, (
            "_run_polish_pass must catch SystemExit and restore from backup "
            "so polish failures don't lose the assembled paper"
        )

    def test_polish_respects_skip_env_var(self):
        import inspect

        src = inspect.getsource(orch._run_polish_pass)
        assert "AUTOLAB_SKIP_POLISH" in src, (
            "_run_polish_pass should honor AUTOLAB_SKIP_POLISH for users "
            "who want to opt out of the polish step"
        )


class TestPolisherSkillOnDisk:
    """Sanity-check that the paper-polisher skill file exists and looks
    well-formed. The orchestrator references it by name; a missing skill
    file would cause polish to fail at runtime."""

    def test_skill_md_exists(self):
        from autolab.paths import SKILLS

        skill = SKILLS / "paper-polisher" / "SKILL.md"
        assert skill.exists(), (
            f"missing skill file at {skill} — paper-polisher is referenced "
            "by phase_final's polish pass"
        )

    def test_skill_md_has_frontmatter(self):
        from autolab.paths import SKILLS

        text = (SKILLS / "paper-polisher" / "SKILL.md").read_text()
        assert text.startswith("---\n"), "skill file missing YAML frontmatter"
        assert "name: paper-polisher" in text, "skill name field missing/wrong"
        assert "description:" in text, "skill description field missing"
