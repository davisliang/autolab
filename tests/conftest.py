"""Shared pytest fixtures for the autolab test suite.

The package imports cleanly without AUTOLAB_PROJECT (only the helpers that
*resolve* a project demand it), so most tests need nothing more than the
standard import. Tests that exercise filesystem-touching helpers should use
the `temp_projects_root` fixture, which redirects `autolab.paths.PROJECTS`
to a tmp dir so they cannot pollute `projects/`.
"""

from __future__ import annotations

import os

import pytest

import autolab.paths as paths


@pytest.fixture
def temp_projects_root(tmp_path, monkeypatch):
    """Redirect autolab.paths.PROJECTS at a tmp dir for the test."""
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr(paths, "PROJECTS", root)
    return root


@pytest.fixture
def fake_active_project(monkeypatch):
    """Set AUTOLAB_PROJECT so `get_project_id` resolves without raising."""
    monkeypatch.setenv("AUTOLAB_PROJECT", "test-project-20260101")
    yield "test-project-20260101"
    # monkeypatch handles cleanup of AUTOLAB_PROJECT automatically
    _ = os
