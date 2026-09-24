---
type: system
status: current
tags:
  - system
  - control-panel
  - configuration
---

# Local research control panel

Install a fresh workspace with `curl -fsSL https://raw.githubusercontent.com/PolderLabs/polder-research-pipeline/main/install.sh | sh -s -- --target ./my-research`, then run `.venv/bin/polder-research serve` from that workspace. Existing checkouts can run `polder-research serve` from the repository root. The server prints its local address (default `http://127.0.0.1:8765`); `--port` selects another port. Stop it with Ctrl-C.

The dashboard reads authoritative `.research/` records and current vault configuration. Analytics include record counts, source/tag distributions, per-field classification outcomes, confidence bands, latency summaries, review decisions, and 30-day additions. These are operational signals, not accuracy estimates or claims of research completeness. Provider quality requires a held-out human-labeled evaluation using `classification-evaluate`. Health combines schema validation, workflow health, configured maintenance checks, provider readiness, and local disk information.

## Configuration

The Configuration view provides common controls and a complete validated YAML editor for `knowledge-base/research.config.yaml`. Edits use revision checks to prevent overwriting changes made by another process. Provider credentials are not allowed in YAML.

Jev uses the official TypeSafe System One API. Enter its API key in the credential field; the value is written to `.research/web-secrets.json` with owner-only file permissions and is never returned to the browser. A server environment variable named by `classification.jev.api_key_env` takes precedence over this saved value. The optional connectivity check sends a fixed, non-research test prompt.

Laya runs inside the local Python server process. Install its optional dependency using `pip install 'polder-research-pipeline[laya]'`, restart the server, choose a checkpoint and compute device, then use Download and load model. The first download requires Hugging Face network access and available disk and memory. Checkpoints are stored in the Hugging Face cache, outside the repository. Model setup can take several minutes and uses memory while loaded. Classification review saves an immutable, self-reported reviewer decision; it does not edit source metadata or authenticate the reviewer.

## Local security boundary

The web server binds to `127.0.0.1` and rejects non-loopback Host and cross-origin write requests. It has no authentication layer and is intended for a trusted local machine, not exposure through a reverse proxy or LAN. Keep the server private. API responses do not include TypeSafe key material; request logs omit query strings and bodies. `.research/web-secrets.json` is ignored by Git.

## Upstream references

- [TypeSafe API quickstart](https://docs.typesafe.ai/introduction/quickstart)
- [Laya Python SDK and model setup](https://github.com/NandhaKishorM/laya)
