"""Tests for registration preparation."""

import json

from github_form_processor.cv import CvClient, CvRepositories, JsonLookup, UrlCheck
from github_form_processor.processor import prepare_registration


class FakeCvClient:
    """Fake CV client for deterministic tests."""

    def __init__(self, entries):
        self.entries = entries

    def fetch_json(self, base_url, folder, identifier):
        entry = self.entries.get((base_url, folder, identifier))
        if entry is None:
            return JsonLookup(found=False)
        return JsonLookup(found=True, data=entry)


class FakeUrlChecker:
    """Fake URL checker for deterministic tests."""

    def __init__(self, results):
        self.results = results

    def check(self, url):
        return self.results.get(url, UrlCheck(accessible=True, status=200))


def test_prepare_experiment_registration_renders_superset_json():
    issue = {
        "title": "[Experiment registration]: Test",
        "labels": [{"name": "registration: experiment"}],
        "body": _body(
            {
                "Experiment name": "My-Experiment",
                "Experiment description": "A short experiment description.",
                "Activity": "CMIP",
                "Tier": "1 - highest priority",
                "Minimum ensemble size": "2",
                "Start date": "2000-01-01",
                "End date": "2010-01-01",
                "Minimum number of years per simulation": "9.5",
                "Required model components": "AOGCM",
                "Additional allowed model components": "AER\nBGC",
                "Parent experiment": "piControl",
                "Parent activity": "CMIP",
                "Parent MIP era": "cmip7",
                "Branch information": (
                    "Branch from `piControl` at a time of your choosing"
                ),
            }
        ),
    }
    cv_client = FakeCvClient(
        {
            (
                "https://raw.githubusercontent.com/WCRP-CMIP/CMIP7-CVs/esgvoc",
                "activity",
                "cmip",
            ): {"id": "cmip"},
            (
                "https://raw.githubusercontent.com/WCRP-CMIP/WCRP-universe/esgvoc",
                "source_type",
                "aogcm",
            ): {"id": "aogcm"},
            (
                "https://raw.githubusercontent.com/WCRP-CMIP/WCRP-universe/esgvoc",
                "source_type",
                "aer",
            ): {"id": "aer"},
            (
                "https://raw.githubusercontent.com/WCRP-CMIP/WCRP-universe/esgvoc",
                "source_type",
                "bgc",
            ): {"id": "bgc"},
            (
                "https://raw.githubusercontent.com/WCRP-CMIP/WCRP-universe/esgvoc",
                "experiment",
                "picontrol",
            ): {
                "id": "picontrol",
                "activity": "cmip",
            },
        }
    )

    prepared, errors, notes = prepare_registration(
        issue=issue,
        experiment_output_dir="experiment",
        activity_output_dir="activity",
        cv_client=cv_client,
    )

    assert errors == []
    assert notes == []
    assert prepared is not None
    assert prepared.output_path == "experiment/my-experiment.json"
    payload = json.loads(prepared.content)
    assert payload == {
        "@context": "000_context.jsonld",
        "id": "my-experiment",
        "type": "experiment",
        "description": "A short experiment description.",
        "drs_name": "My-Experiment",
        "start_timestamp": "2000-01-01",
        "end_timestamp": "2010-01-01",
        "activity": "cmip",
        "additional_allowed_model_components": ["aer", "bgc"],
        "branch_information": "Branch from `piControl` at a time of your choosing",
        "min_ensemble_size": 2,
        "parent_activity": "cmip",
        "parent_experiment": "picontrol",
        "parent_mip_era": "cmip7",
        "required_model_components": ["aogcm"],
        "tier": 1,
        "min_number_yrs_per_sim": 9.5,
    }


def test_prepare_experiment_rejects_min_years_longer_than_date_span():
    issue = {
        "title": "[Experiment registration]: Test",
        "labels": [{"name": "registration: experiment"}],
        "body": _body(
            {
                "Experiment name": "My-Experiment",
                "Experiment description": "A short experiment description.",
                "Activity": "cmip",
                "Tier": "1 - highest priority",
                "Minimum ensemble size": "1",
                "Start date": "2000-01-01",
                "End date": "2001-01-01",
                "Minimum number of years per simulation": "2.0",
                "Required model components": "aogcm",
            }
        ),
    }

    prepared, errors, notes = prepare_registration(
        issue=issue,
        experiment_output_dir="experiment",
        activity_output_dir="activity",
        external_checks=False,
    )

    assert prepared is None
    assert notes == []
    assert any("minimum number of years per simulation" in error for error in errors)


def test_prepare_experiment_uses_configured_remote_cv_repositories():
    issue = {
        "title": "[Experiment registration]: Test",
        "labels": [{"name": "registration: experiment"}],
        "body": _body(
            {
                "Experiment name": "My-Experiment",
                "Experiment description": "A short experiment description.",
                "Activity": "cmip",
                "Tier": "1 - highest priority",
                "Minimum ensemble size": "1",
                "Minimum number of years per simulation": "1.0",
                "Required model components": "aogcm",
            }
        ),
    }
    cv_client = FakeCvClient(
        {
            ("https://example.test/cmip7-cvs/custom", "activity", "cmip"): {
                "id": "cmip"
            },
            ("https://example.test/universe/custom", "source_type", "aogcm"): {
                "id": "aogcm"
            },
        }
    )

    prepared, errors, notes = prepare_registration(
        issue=issue,
        experiment_output_dir="experiment",
        activity_output_dir="activity",
        cv_client=cv_client,
        cv_repositories=CvRepositories(
            wcrp_universe_url="https://example.test/universe/custom",
            cmip7_cvs_url="https://example.test/cmip7-cvs/custom",
        ),
    )

    assert prepared is not None
    assert errors == []
    assert notes == []


def test_prepare_activity_blocks_inaccessible_reference_url():
    issue = {
        "title": "[Activity registration]: Test",
        "labels": [{"name": "registration: activity"}],
        "body": _body(
            {
                "Activity name": "NewActivity",
                "Activity description": "A short activity description.",
                "Experiments": "known-exp\nmissing-exp",
                "Reference URLs": "https://example.invalid/dead",
            }
        ),
    }
    cv_client = FakeCvClient(
        {
            (
                "https://raw.githubusercontent.com/WCRP-CMIP/CMIP7-CVs/esgvoc",
                "experiment",
                "known-exp",
            ): {"id": "known-exp"},
        }
    )
    url_checker = FakeUrlChecker(
        {
            "https://example.invalid/dead": UrlCheck(accessible=False, status=404),
        }
    )

    prepared, errors, notes = prepare_registration(
        issue=issue,
        experiment_output_dir="experiment",
        activity_output_dir="activity",
        cv_client=cv_client,
        url_checker=url_checker,
    )

    assert prepared is None
    assert errors == [
        "Reference URL `https://example.invalid/dead` returned HTTP status 404."
    ]
    assert notes == ["Experiment `missing-exp` is not already part of the CMIP7 CVs."]


def test_prepare_activity_renders_json():
    issue = {
        "title": "[Activity registration]: Test",
        "labels": [{"name": "registration: activity"}],
        "body": _body(
            {
                "Activity name": "MyActivity",
                "Activity description": "A short activity description.",
                "Experiments": "- exp-one\n- exp-two",
                "Reference URLs": "https://example.com/reference",
            }
        ),
    }

    prepared, errors, notes = prepare_registration(
        issue=issue,
        experiment_output_dir="experiment",
        activity_output_dir="activity",
        external_checks=False,
    )

    assert errors == []
    assert notes == []
    assert prepared is not None
    assert prepared.output_path == "activity/myactivity.json"
    assert json.loads(prepared.content) == {
        "@context": "000_context.jsonld",
        "id": "myactivity",
        "type": "activity",
        "description": "A short activity description.",
        "drs_name": "MyActivity",
        "experiments": ["exp-one", "exp-two"],
        "urls": ["https://example.com/reference"],
    }


def test_prepare_activity_can_check_cmip7_cvs_from_local_path(tmp_path):
    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir()
    (experiment_dir / "known-exp.json").write_text('{"id": "known-exp"}')
    issue = {
        "title": "[Activity registration]: Test",
        "labels": [{"name": "registration: activity"}],
        "body": _body(
            {
                "Activity name": "MyActivity",
                "Activity description": "A short activity description.",
                "Experiments": "known-exp\nmissing-exp",
            }
        ),
    }

    prepared, errors, notes = prepare_registration(
        issue=issue,
        experiment_output_dir="experiment",
        activity_output_dir="activity",
        cv_client=CvClient(),
        cv_repositories=CvRepositories(
            cmip7_cvs_path=tmp_path,
        ),
    )

    assert prepared is not None
    assert errors == []
    assert notes == ["Experiment `missing-exp` is not already part of the CMIP7 CVs."]


def _body(fields):
    return "\n\n".join(f"### {label}\n\n{value}" for label, value in fields.items())
