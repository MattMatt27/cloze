# Contributing to Cloze

Thanks for your interest in Cloze. We're a small team and we maintain Cloze as
research infrastructure for studying human–AI interaction. This document
explains how to report problems, ask questions, and contribute changes.

## Get in touch first

Cloze is in active development and we coordinate work closely, so **please reach
out before starting any non-trivial change** rather than opening a pull request
directly. This saves you from building something that conflicts with work in
progress or with our roadmap.

- **Found a bug?** Open a [GitHub issue](https://github.com/MattMatt27/cloze/issues)
  with steps to reproduce, what you expected, and what happened.
- **Have a question or want to use Cloze for a study?** Open a
  [Discussion](https://github.com/MattMatt27/cloze/discussions).
- **Want to propose a feature or a code change?** Open an issue describing the
  idea first. We'll discuss scope and approach before any code is
  written. Unsolicited pull requests may be closed with a request to open an
  issue first — this isn't a rejection of the idea, just how we keep the project
  coordinated.
- **Security issue?** Do **not** open a public issue. See
  [SECURITY.md](SECURITY.md).

## Development setup

See the [README](README.md) for installation. In short:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # test + lint tooling
cp .env.example .env
```

## Running checks before you submit

Please make sure these pass locally — CI runs the same checks on every pull
request:

```bash
ruff check .          # lint
ruff format --check . # formatting
pytest                # tests
```

If you add or change behaviour, add or update tests to cover it.

## Pull request expectations

Once we've agreed on an approach in an issue:

1. Branch off `main`.
2. Keep the change focused; one logical change per pull request.
3. Make sure lint, formatting, and tests pass.
4. Reference the issue you discussed in the pull request description.

## Contributor License Agreement

Before we can merge your contribution, you'll need to agree to our Contributor
License Agreement (CLA). By submitting a contribution you confirm that:

- the contribution is your own original work (or you have the right to submit
  it), and
- you grant the Cloze maintainers a perpetual, worldwide, royalty-free license
  to use, reproduce, modify, and distribute your contribution, **and to license
  it under the project's current license (AGPL-3.0) and under other license
  terms the maintainers may adopt for the project in the future.**

This lets us keep Cloze open under the AGPL while retaining the flexibility to
sustain the project (for example, through a non-profit offering hosted
deployments). We'll point you to the CLA when you open your first pull request.

## Code of conduct

Participation in this project is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md). Please read it.
