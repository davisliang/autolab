"""Tests for autolab.paths — pure helpers and project-id construction."""

from __future__ import annotations

import re

import pytest

import autolab.paths as paths
from autolab.paths import (
    drafts_dir,
    experiments_dir,
    get_project_id,
    list_projects,
    make_project_id,
    parking_lot,
    project_dir,
    slugify,
    thoughts_dir,
)


class TestSlugify:
    def test_basic_phrase(self):
        assert slugify("Hello World") == "hello-world"

    def test_strips_punctuation(self):
        # Default max_words=6, so the trailing "it" is dropped.
        assert slugify("It's a test, isn't it?") == "it-s-a-test-isn-t"

    def test_strips_punctuation_with_room(self):
        assert slugify("It's a test, isn't it?", max_words=10) == "it-s-a-test-isn-t-it"

    def test_truncates_to_max_words(self):
        assert slugify("one two three four five six seven", max_words=3) == "one-two-three"

    def test_empty_input_returns_fallback(self):
        assert slugify("") == "idea"
        assert slugify("   ") == "idea"
        assert slugify("!!!") == "idea"

    def test_unicode_is_dropped(self):
        # The slug regex is [a-z0-9]+; non-ASCII letters drop out.
        assert slugify("café résumé") == "caf-r-sum"

    def test_collapses_whitespace_and_repeated_punct(self):
        assert slugify("foo___bar  --  baz") == "foo-bar-baz"


class TestMakeProjectId:
    def test_format_is_slug_dash_yyyymmdd(self, temp_projects_root):
        pid = make_project_id("Layer-wise LRs help small MLPs")
        assert re.match(r"^layer-wise-lrs-help-small-mlps-\d{8}$", pid), pid

    def test_collision_appends_numeric_suffix(self, temp_projects_root):
        first = make_project_id("same idea")
        # Materialize the first one so the second collides.
        (temp_projects_root / first).mkdir()
        second = make_project_id("same idea")
        assert second.endswith("-2"), second
        assert second != first

    def test_repeated_collisions_increment_suffix(self, temp_projects_root):
        first = make_project_id("repeat")
        (temp_projects_root / first).mkdir()
        second = make_project_id("repeat")
        (temp_projects_root / second).mkdir()
        third = make_project_id("repeat")
        assert third.endswith("-3"), third


class TestProjectScopedHelpers:
    def test_helpers_resolve_under_project_dir(self, fake_active_project):
        pid = fake_active_project
        assert project_dir(pid).name == pid
        assert thoughts_dir(pid) == project_dir(pid) / "thoughts"
        assert drafts_dir(pid) == project_dir(pid) / "drafts"
        assert experiments_dir(pid) == project_dir(pid) / "experiments"
        assert parking_lot(pid) == project_dir(pid) / "ideas" / "parking_lot.md"

    def test_get_project_id_reads_env(self, fake_active_project):
        assert get_project_id() == fake_active_project

    def test_get_project_id_raises_without_env(self, monkeypatch):
        monkeypatch.delenv("AUTOLAB_PROJECT", raising=False)
        with pytest.raises(SystemExit, match="AUTOLAB_PROJECT"):
            get_project_id()

    def test_program_md_is_under_prompts(self):
        # PROGRAM moved from program.md → prompts/program.md during the
        # repo reorganization; this guards against regressing it back.
        assert paths.PROGRAM.parent.name == "prompts"
        assert paths.PROGRAM.name == "program.md"

    def test_repo_constant_points_at_repo_root(self):
        # REPO must contain the autolab package and the prompts directory.
        assert (paths.REPO / "autolab").is_dir()
        assert (paths.REPO / "prompts").is_dir()


class TestListProjects:
    def test_empty_dir(self, temp_projects_root):
        assert list_projects() == []

    def test_returns_sorted_dir_names_only(self, temp_projects_root):
        (temp_projects_root / "b-project").mkdir()
        (temp_projects_root / "a-project").mkdir()
        (temp_projects_root / "INDEX.md").write_text("not a project")
        assert list_projects() == ["a-project", "b-project"]
