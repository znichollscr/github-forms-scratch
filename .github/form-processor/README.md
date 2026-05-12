# GitHub Form Processor

This package processes repository issue forms into validated registration JSON
files and opens pull requests with the generated files.

## Installation

To create the local development environment, run

```sh
uv sync
```

Run the tests with

```sh
uv run pytest
```

The GitHub Actions workflow installs this package and runs

```sh
python -m github_form_processor \
  --experiment-output-dir experiment \
  --activity-output-dir activity
```

against the issue event payload supplied by GitHub.

## Generated Pull Requests

The workflow uses deterministic branches of the form

```text
registration/{experiment|activity}-{issue-number}-{id}
```

New issue submissions create a pull request. Edits update the existing pull
request branch. If an edited issue has no open registration pull request, the
processor comments on the issue and exits with an error.
