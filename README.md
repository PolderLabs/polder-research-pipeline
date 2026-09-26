<p align="center">
  <img src="docs/assets/polder-banner.svg" alt="Illustrated waterways and fields" width="100%">
</p>

<p align="center">
  <a href="https://github.com/PolderLabs/polder-research-pipeline/actions/workflows/ci.yml"><img src="https://github.com/PolderLabs/polder-research-pipeline/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status"></a>
  <a href="https://github.com/PolderLabs/polder-research-pipeline/releases/latest"><img src="https://img.shields.io/github/v/release/PolderLabs/polder-research-pipeline?label=latest%20release" alt="Latest release"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.14%2B-377e68.svg" alt="Python 3.14 or newer"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-377e68.svg" alt="MIT License"></a>
</p>

<h1 align="center">Polder Research Pipeline</h1>

Polder gives your research a place to live. Keep sources, notes, evidence, and review decisions together in a workspace you can inspect, edit, and carry forward.

It is built for people doing ongoing research as well as teams who need a documented, protocol-led evidence review. The project is in alpha, so take a look around and check important findings against their sources.

## Get started

You’ll need Python 3.14 or newer, Git, and `curl`. This installs the latest published release into a new directory, sets up a local environment, and starts a fresh research workspace:

```sh
curl -fsSL https://raw.githubusercontent.com/PolderLabs/polder-research-pipeline/main/install.sh \
  | sh -s -- --target ./my-research

cd ./my-research
.venv/bin/polder-research serve
```

Open the local address printed in your terminal. The dashboard listens on `127.0.0.1` and helps you configure your workspace, manage the Laya model, and review research activity.

Want the newest changes from `main` instead of a published release? Add `--unstable`:

```sh
curl -fsSL https://raw.githubusercontent.com/PolderLabs/polder-research-pipeline/main/install.sh \
  | sh -s -- --unstable --target ./my-research
```

The installer keeps the new workspace independent: it creates a local Git repository without a remote, and starts you with a blank project brief. See [`install.sh`](install.sh) for options such as `--without-laya`, `--with-dev`, and installing from a fork.

## Pick a research workflow

| If you’re… | Start here |
|---|---|
| Keeping up with a topic over time | Use the continuous research and knowledge-maintenance workflow. It supports bounded discovery and source processing; it does not claim exhaustive coverage. |
| Planning a systematic evidence review | Read [Research methods](knowledge-base/00-home/research-methods.md) first. Freeze your protocol before searching, then record searches, screening, extraction, and appraisal as you go. |
| Filing one paper, report, or other source | Follow the [research intake guide](knowledge-base/00-home/research-intake-guide.md) to register the original and connect your notes to it. |

Polder keeps source records and evidence in structured, validated files, with Markdown notes alongside them. The [evidence model](knowledge-base/00-home/evidence-model.md) explains how those pieces connect.

## Your workspace and your data

Polder runs on your machine. Research records, search exports, generated state, and local credentials live in the ignored `.research/` directory. The dashboard is for local use and has no login, so keep it on your own machine rather than exposing it to a network.

Laya is the default classifier and runs locally after its model is downloaded. You can skip its large machine-learning dependencies during installation with `--without-laya`. A remote TypeSafe/Jev provider is available when you choose and configure it; classification data sent to that provider leaves your machine. Read the [provider guide](knowledge-base/03-system/classification-providers.md) and [security policy](SECURITY.md) before working with sensitive material.

## A few useful places to look

- [Knowledge base dashboard](knowledge-base/index.md) for the vault’s home page and navigation.
- [Control panel guide](knowledge-base/03-system/control-panel.md) for dashboard setup and settings.
- [Provenance model](knowledge-base/00-home/provenance-model.md) for how Polder records where information came from.
- [Agent roles](agents/) for the documented research responsibilities and capabilities.
- [Audit and roadmap](knowledge-base/AUDIT.md) for current limitations and planned work.
- [Contributing](CONTRIBUTING.md) if you’d like to improve the project.

## What Polder can and can’t claim

Polder helps you keep a review trail, but it does not certify research quality or PRISMA compliance. Reviewers enter their own IDs; the software does not verify identities or independence. A generated review report indexes records and hashes, rather than packaging all the underlying evidence. See [Research methods](knowledge-base/00-home/research-methods.md) for the full process and its limits.

The project is in alpha and has not had an independent security audit. Validate findings against the original sources, especially before using them for consequential decisions.

## Working on the project

To set up a development environment, install the package and its development tools, then run the checks:

```sh
python -m pip install -r requirements-ci.txt
python -m pip install -e .
ruff check .
ruff format --check .
PYTHONPATH=src pytest -q
```

Polder is available under the [MIT License](LICENSE).
