"""Tests for run state tracking."""

import json

import pytest

from curator.state import Phase, RunStatus, load_status, write_status


class TestPhaseOrdering:
    def test_phase_ordering(self):
        assert Phase.NONE < Phase.FETCHED < Phase.VALIDATED < Phase.IMPORTED

    def test_phase_values(self):
        assert Phase.NONE.value == "none"
        assert Phase.FETCHED.value == "fetched"
        assert Phase.IMPORTED.value == "imported"


class TestLoadStatus:
    def test_returns_empty_status_when_no_file(self, tmp_path):
        status = load_status(tmp_path / "run_status.json")
        assert status.phase == Phase.NONE
        assert status.result is None

    def test_loads_existing_status(self, tmp_path):
        path = tmp_path / "run_status.json"
        path.write_text(json.dumps({
            "last_run": "2026-01-01T00:00:00Z",
            "phase": "fetched",
            "result": "success",
        }))
        status = load_status(path)
        assert status.phase == Phase.FETCHED
        assert status.result == "success"


class TestWriteStatus:
    def test_writes_status_file(self, tmp_path):
        path = tmp_path / "run_status.json"
        write_status(path, Phase.IMPORTED, result="success", summary={"created": 10})

        data = json.loads(path.read_text())
        assert data["phase"] == "imported"
        assert data["result"] == "success"
        assert data["summary"]["created"] == 10
        assert "last_run" in data

    def test_overwrites_previous_status(self, tmp_path):
        path = tmp_path / "run_status.json"
        write_status(path, Phase.FETCHED)
        write_status(path, Phase.IMPORTED, result="success")

        data = json.loads(path.read_text())
        assert data["phase"] == "imported"
