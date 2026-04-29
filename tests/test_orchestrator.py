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
            "review",
        ]

    def test_review_is_terminal_phase(self):
        # `review` is the new terminal phase; it gates whether the paper
        # ships or whether the orchestrator loops back to an earlier phase.
        assert orch.PHASES[-1] == "review"

    def test_retreat_phases_are_subset_of_phases(self):
        assert set(orch.RETREAT_PHASES).issubset(set(orch.PHASES))

    def test_retreat_phases_exclude_terminal_phases(self):
        # Retreat re-runs the middle of the pipeline; it must not reset the
        # terminal phases.
        assert "seed" not in orch.RETREAT_PHASES
        assert "write" not in orch.RETREAT_PHASES
        assert "final" not in orch.RETREAT_PHASES
        assert "review" not in orch.RETREAT_PHASES

    def test_valid_review_loopback_phases_are_in_phases(self):
        # Every phase a reviewer may request must actually exist as a phase.
        assert orch.VALID_REVIEW_LOOPBACK_PHASES.issubset(set(orch.PHASES))

    def test_reviewer_personas_are_distinct_and_nonempty(self):
        ids = [p["id"] for p in orch.REVIEWER_PERSONAS]
        assert len(ids) == len(set(ids)), "reviewer persona ids must be unique"
        assert {"methodologist", "domain-expert", "clarity-reviewer"}.issubset(set(ids))
        for p in orch.REVIEWER_PERSONAS:
            assert (
                isinstance(p.get("focus"), str) and len(p["focus"]) >= 40
            ), f"persona {p.get('id')} missing or has short focus"


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


class TestCommitteeReviewWiring:
    """phase_review runs after phase_final and either ships the paper or
    triggers a loopback via review_loopback_check. These tests pin the
    structural wiring without invoking claude."""

    def test_phase_review_helper_exists(self):
        assert hasattr(orch, "phase_review") and callable(orch.phase_review)

    def test_review_loopback_check_exists(self):
        assert hasattr(orch, "review_loopback_check") and callable(orch.review_loopback_check)

    def test_phase_review_invokes_committee_reviewer_skill(self):
        import inspect

        src = inspect.getsource(orch.phase_review)
        assert (
            '"committee-reviewer"' in src
        ), "phase_review must dispatch to the committee-reviewer skill"
        assert (
            "parallel_calls(" in src
        ), "phase_review must run reviewers in parallel via parallel_calls"
        assert "persona" in src, "phase_review must pass a persona to each call"

    def test_phase_review_respects_skip_env_var(self):
        import inspect

        src = inspect.getsource(orch.phase_review)
        assert "AUTOLAB_SKIP_REVIEW" in src, (
            "phase_review should honor AUTOLAB_SKIP_REVIEW for users who "
            "want to opt out of the committee step"
        )

    def test_run_phase_dispatches_review(self):
        import inspect

        src = inspect.getsource(orch.run_phase)
        assert 'phase == "review"' in src, "run_phase must dispatch the review phase"
        assert "phase_review()" in src

    def test_next_phase_to_run_consults_review_loopback(self):
        import inspect

        src = inspect.getsource(orch.next_phase_to_run)
        assert 'cur == "review"' in src, (
            "next_phase_to_run must call review_loopback_check() after the " "review phase"
        )
        assert "review_loopback_check()" in src

    def test_review_loopback_uses_retreat_machinery(self):
        import inspect

        src = inspect.getsource(orch.review_loopback_check)
        assert "_retreat(" in src, (
            "review_loopback_check must reuse _retreat() so checkpoint "
            "wiping + cycle-counter bumping is consistent with the other "
            "retreat loops"
        )
        assert "MAX_REVIEW_CYCLES" in src

    def test_max_review_cycles_constant_exists(self):
        assert isinstance(orch.MAX_REVIEW_CYCLES, int)
        assert orch.MAX_REVIEW_CYCLES >= 1


class TestCycleStateReviewKeys:
    """read_cycle_state() must initialize review_cycle/review_history so
    review_loopback_check has something to read on the first iteration."""

    def test_defaults_include_review_keys(self, tmp_path, monkeypatch):
        # Redirect cycle_state_path to a tmp path so this test doesn't
        # need a real project on disk.
        monkeypatch.setenv("AUTOLAB_PROJECT", "test-cycle-state")
        cycle_path = tmp_path / "cycles.json"
        monkeypatch.setattr(orch, "cycle_state_path", lambda: cycle_path)

        state = orch.read_cycle_state()
        assert state["review_cycle"] == 1
        assert state["review_history"] == []


class TestCommitteeReviewerSkillOnDisk:
    """The committee-reviewer skill file must exist and declare itself
    correctly; the orchestrator references it by name."""

    def test_skill_md_exists(self):
        from autolab.paths import SKILLS

        skill = SKILLS / "committee-reviewer" / "SKILL.md"
        assert skill.exists(), (
            f"missing skill file at {skill} — committee-reviewer is " "referenced by phase_review"
        )

    def test_skill_md_has_frontmatter_and_name(self):
        from autolab.paths import SKILLS

        text = (SKILLS / "committee-reviewer" / "SKILL.md").read_text()
        assert text.startswith("---\n")
        assert "name: committee-reviewer" in text
        assert "description:" in text


class TestReviewArtifactType:
    """The append_artifact CLI must accept --type Review with the REV-
    prefix, since the committee-reviewer skill emits Review artifacts."""

    def test_review_in_type_prefix(self):
        from autolab.append_artifact import TYPE_PREFIX

        assert TYPE_PREFIX.get("Review") == "REV"


class TestRunHistory:
    """Cross-loop narrative file at <project>/thread/history.md.

    Every loopback (experiment retreat, idea retreat, review loopback)
    appends one Markdown section. Every phase that may run as part of a
    loopback injects the file content via `history_block()`. This is the
    single source of truth for cross-loop context — replaces the earlier
    per-loop helpers (cycle_context_block / idea_cycle_context_block /
    review_cycle_context_block).
    """

    # ---- helpers exist and have the right shape ----

    def test_history_block_exists(self):
        assert callable(orch.history_block)

    def test_append_history_entry_exists(self):
        assert callable(orch.append_history_entry)

    def test_three_entry_builders_exist(self):
        assert callable(orch._history_entry_experiment_retreat)
        assert callable(orch._history_entry_idea_retreat)
        assert callable(orch._history_entry_review_loopback)

    def test_legacy_per_loop_helpers_are_gone(self):
        # Belt-and-suspenders: confirm the old per-loop helpers are removed
        # so nothing accidentally falls back to them.
        for name in (
            "cycle_context_block",
            "idea_cycle_context_block",
            "review_cycle_context_block",
        ):
            assert not hasattr(orch, name), (
                f"legacy helper {name!r} should have been deleted; the "
                f"unified history mechanism replaces it"
            )

    # ---- history_block file I/O ----

    def test_history_block_returns_empty_for_virgin_project(
        self, tmp_path, monkeypatch, fake_active_project
    ):
        # Point history_log at a tmp file that doesn't exist.
        log_path = tmp_path / "history.md"
        monkeypatch.setattr(orch, "history_log", lambda: log_path)
        assert orch.history_block() == ""

    def test_history_block_returns_empty_for_whitespace_only_file(
        self, tmp_path, monkeypatch, fake_active_project
    ):
        log_path = tmp_path / "history.md"
        log_path.write_text("\n   \n")
        monkeypatch.setattr(orch, "history_log", lambda: log_path)
        assert orch.history_block() == ""

    def test_history_block_renders_when_file_has_content(
        self, tmp_path, monkeypatch, fake_active_project
    ):
        log_path = tmp_path / "history.md"
        log_path.write_text("### Cycle 1 ended — experiment retreat → survey\n\nbody\n")
        monkeypatch.setattr(orch, "history_log", lambda: log_path)
        block = orch.history_block()
        assert "RUN HISTORY" in block
        assert "Cycle 1 ended" in block

    def test_history_block_truncates_when_oversize(
        self, tmp_path, monkeypatch, fake_active_project
    ):
        # Synthesize a long history file and confirm the elision marker
        # appears and the block respects the budget.
        log_path = tmp_path / "history.md"
        log_path.write_text("X" * 20000)
        monkeypatch.setattr(orch, "history_log", lambda: log_path)
        block = orch.history_block(max_chars=2000)
        assert "elided" in block.lower(), "oversize history must mention elision"
        # The cap is inclusive of the framing prefix; verify it's bounded.
        assert len(block) < 4000

    def test_append_history_entry_writes_section_separated(
        self, tmp_path, monkeypatch, fake_active_project
    ):
        log_path = tmp_path / "history.md"
        monkeypatch.setattr(orch, "history_log", lambda: log_path)
        orch.append_history_entry("### A\n\nfirst")
        orch.append_history_entry("### B\n\nsecond")
        text = log_path.read_text()
        assert "### A" in text and "### B" in text
        # Each entry must terminate with a blank line so the next append
        # doesn't visually run together.
        assert text.count("\n\n") >= 2

    def test_append_history_entry_ignores_empty_input(
        self, tmp_path, monkeypatch, fake_active_project
    ):
        log_path = tmp_path / "history.md"
        monkeypatch.setattr(orch, "history_log", lambda: log_path)
        orch.append_history_entry("")
        orch.append_history_entry("   \n  \n")
        assert not log_path.exists() or log_path.read_text() == ""

    # ---- entry builders ----

    def _fake_thread(self):
        return [
            {"type": "Hypothesis", "id": "HYP-001", "claim": "Layer-wise LRs help small MLPs"},
            {"type": "Hypothesis", "id": "HYP-002", "claim": "Mixup helps small RL"},
            {
                "type": "Critique",
                "id": "CRIT-007",
                "target_id": "HYP-001",
                "mode": "validity",
                "severity": "high",
                "concerns": ["single-seed", "baseline used different optimizer"],
            },
            {
                "type": "Critique",
                "id": "CRIT-005",
                "target_id": "HYP-001",
                "mode": "boredom",
                "severity": "high",
                "concerns": ["variant of standard practice; not novel"],
            },
            {
                "type": "Review",
                "id": "REV-001",
                "persona": "methodologist",
                "recommendation": "major_revision",
                "target_phase": "design",
                "summary": "baseline used different seeds; ablation absent",
                "created_at": "2026-04-29T05:01:00+00:00",
            },
            {
                "type": "Review",
                "id": "REV-002",
                "persona": "domain-expert",
                "recommendation": "minor_revision",
                "summary": "missing comparison",
                "created_at": "2026-04-29T05:01:05+00:00",
            },
        ]

    def test_experiment_retreat_entry_inlines_hyps_and_critiques(self):
        thread = self._fake_thread()
        md = orch._history_entry_experiment_retreat(
            {"current": 1},
            {
                "failed_hyp_ids": ["HYP-001", "HYP-002"],
                "failed_plan_ids": ["EXP-003"],
                "summary": "2 primary experiments, 0 pass",
            },
            thread,
        )
        assert "experiment retreat → survey" in md
        assert "HYP-001" in md and "HYP-002" in md
        assert "Layer-wise LRs help small MLPs" in md, "must inline the HYP claim"
        assert "CRIT-007" in md, "must inline the validity Critique id"
        assert "single-seed" in md, "must inline the Critique concerns"
        assert "**Next:**" in md, "must end with a directive for the re-run skill"

    def test_idea_retreat_entry_inlines_parked_and_boredom_critiques(self):
        thread = self._fake_thread()
        md = orch._history_entry_idea_retreat(
            {"idea_cycle": 1},
            {"parked_hyp_ids": ["HYP-001"], "n_survivors": 0},
            thread,
        )
        assert "idea retreat → expand" in md
        assert "HYP-001" in md
        assert "CRIT-005" in md, "must inline the boredom Critique id"
        assert "variant of standard practice" in md
        assert "Wildness Tickets" in md
        assert "**Next:**" in md

    def test_review_loopback_entry_lists_per_persona_verdicts(self):
        thread = self._fake_thread()
        md = orch._history_entry_review_loopback(
            {"review_cycle": 1, "review_history": []},
            {
                "target_phase": "design",
                "recommendations": ["major_revision", "minor_revision"],
                "summary": "1 major rev, 1 minor; target=design",
            },
            thread,
        )
        assert "review loopback → design" in md
        assert "REV-001" in md and "REV-002" in md
        assert "methodologist" in md and "domain-expert" in md
        assert "major_revision" in md
        assert "**Next:**" in md

    # ---- integration: every loopback-eligible phase injects history_block ----

    def test_history_block_injected_into_every_loopback_eligible_phase(self):
        """Every phase that may run as part of any loopback must inject
        `history_block()` so the re-run skill sees the cross-loop narrative."""
        import inspect

        # Phases that are downstream of any retreat/loopback target. This
        # is a superset of VALID_REVIEW_LOOPBACK_PHASES because experiment
        # and idea retreats also re-enter expand/screen/gap-fill.
        eligible = {
            "expand": orch.phase_expand,
            "survey": orch.phase_survey,
            "gap-fill": orch.phase_gap_fill,
            "screen": orch.phase_screen,
            "design": orch.phase_design,
            "run": orch.phase_run,
            "critique": orch.phase_critique,
            "write": orch.phase_write,
            "final": orch._run_polish_pass,  # the claude call inside phase_final
            "review": orch.phase_review,
        }
        for phase_name, fn in eligible.items():
            src = inspect.getsource(fn)
            assert "history_block(" in src, (
                f"phase {phase_name!r} must call history_block() so the "
                f"re-run narrative reaches the skill prompt"
            )

    # ---- integration: each retreat hook passes its narrative_builder ----

    def test_retreat_hooks_pass_narrative_builder(self):
        import inspect

        for fn, builder_name in (
            (orch.cycle_retreat_check, "_history_entry_experiment_retreat"),
            (orch.idea_retreat_check, "_history_entry_idea_retreat"),
            (orch.review_loopback_check, "_history_entry_review_loopback"),
        ):
            src = inspect.getsource(fn)
            assert (
                f"narrative_builder={builder_name}" in src
            ), f"{fn.__name__} must pass narrative_builder={builder_name} to _retreat()"

    def test_retreat_helper_accepts_narrative_builder_kw(self):
        import inspect

        sig = inspect.signature(orch._retreat)
        assert "narrative_builder" in sig.parameters, (
            "_retreat must accept a narrative_builder kwarg so each loop "
            "can append its templated history.md entry"
        )


class TestStopConditionsTracksTerminalPhase:
    """Regression: when `review` was added as the new terminal phase, the
    stop-condition check still returned True for `final.json`, causing the
    orchestrator to exit before the committee ever ran. The check must
    track PHASES[-1], not a hard-coded phase name."""

    def test_stop_conditions_source_uses_terminal_phase_dynamically(self):
        import inspect

        src = inspect.getsource(orch.stop_conditions_met)
        # Must derive the terminal phase from PHASES, not hard-code it.
        assert "PHASES[-1]" in src, (
            "stop_conditions_met must derive the terminal phase from "
            "PHASES[-1] so adding a new terminal phase doesn't silently "
            "skip it"
        )
        # The active code path must use the dynamic f"{terminal}.json"
        # form, not the literal "final.json" pattern that was the bug.
        # (Comments may still mention "final.json" for context.)
        assert 'f"{terminal}.json"' in src, (
            "stop_conditions_met must build the checkpoint filename "
            "from the resolved terminal phase variable"
        )
        assert '/ "final.json"' not in src, (
            "stop_conditions_met must not hard-code the path "
            '(checkpoints_dir() / "final.json") — that was the bug'
        )

    def test_stop_condition_message_names_terminal_phase(self, tmp_path, monkeypatch):
        # With the terminal checkpoint absent, no stop reason fires.
        ckdir = tmp_path / "checkpoints"
        ckdir.mkdir()
        monkeypatch.setattr(orch, "checkpoints_dir", lambda: ckdir)
        monkeypatch.setattr(orch, "STOP_FILE", tmp_path / "STOP-not-here")
        assert orch.stop_conditions_met() is None

        # With the terminal checkpoint present, stop fires and the message
        # names the actual terminal phase (review), not a stale "final".
        terminal = orch.PHASES[-1]
        (ckdir / f"{terminal}.json").write_text("{}")
        msg = orch.stop_conditions_met()
        assert msg is not None
        assert terminal in msg, f"stop message should mention the terminal phase; got: {msg!r}"
