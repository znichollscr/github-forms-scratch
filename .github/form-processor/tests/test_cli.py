"""Tests for the Typer command-line interface."""

import json

from typer.testing import CliRunner

from github_form_processor.cli import app


def test_process_accepts_output_directories_as_options(tmp_path, monkeypatch):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "action": "opened",
                "issue": {
                    "number": 1,
                    "title": "[Experiment registration]: Test",
                    "labels": [{"name": "registration: experiment"}],
                    "body": "",
                },
                "repository": {"default_branch": "main"},
            }
        )
    )
    call = {}

    def fake_prepare_registration(**kwargs):
        call.update(kwargs)
        return None, [], []

    monkeypatch.setattr(
        "github_form_processor.cli.prepare_registration",
        fake_prepare_registration,
    )

    result = CliRunner().invoke(
        app,
        [
            "--event-path",
            str(event_path),
            "--experiment-output-dir",
            "custom-experiments",
            "--activity-output-dir",
            "custom-activities",
        ],
    )

    assert result.exit_code == 0
    assert call["experiment_output_dir"] == "custom-experiments"
    assert call["activity_output_dir"] == "custom-activities"
