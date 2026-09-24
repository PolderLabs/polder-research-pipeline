---
type: system
status: current
tags:
  - classification
  - typesafe
  - laya
---

# Classification providers

The evidence API automatically classifies registered sources, claims, entities,
and segments using the closed, versioned taxonomy in `research.config.yaml`.
The built-in `rules` provider is the default and has no network or model
dependency. Switch `classification.provider` to `jev` or `laya` to use a model.

## Jev / TypeSafe API

Jev sends the bounded input text to TypeSafe's hosted System One API. Set
`TYPESAFE_API_KEY` in the process environment. The endpoint is fixed to
`https://api.typesafe.ai/v1/systemone`; requests use `jev-latest` by default.
No key or document text is written to classification records.

## Laya, in process

Install the optional extra with `pip install 'polder-research-pipeline[laya]'`
and set `classification.provider: laya`. Inference then runs locally in the
pipeline process using Laya's Python `Router`; no Laya API server is involved.
The model checkpoint is downloaded on first use unless already cached, and
requires disk, memory, and suitable PyTorch support. For offline operation,
pre-cache the selected model and disable all other networked pipeline actions.

The current default model is Laya's multilingual router. A different local
checkpoint can be selected with `classification.laya.model`. Laya model
quality must be measured on a project-specific, human-labeled set before its
outputs are trusted for unattended routing.

## Decision and review policy

Category uses one typed `choice`; each tag is a separate `noul` decision. The
configured minimum confidence gates proposals. Each run creates an immutable
`.research/classifications/cls_*.json` record with hashes, complete answers,
probabilities, provider/model, threshold, and disposition. Input text itself is
not copied into that record. Provider failures are recorded and do not block
evidence registration. Existing user metadata is preserved; accepted results
are merged with it. Classification is organizational metadata, never evidence
of a claim and never a substitute for systematic review screening, appraisal,
extraction, or adjudication.

## Sources and inspiration

- [TypeSafe introduction](https://docs.typesafe.ai/introduction) and [API quick start](https://docs.typesafe.ai/introduction/quickstart): typed choice, score, and yes/no decisions.
- [TypeSafe confidence routing](https://docs.typesafe.ai/confidence): route uncertain results for review.
- [Laya upstream project](https://github.com/NandhaKishorM/laya): local Python Router, multilingual checkpoints, and typed decisions.
- [TypeSafe router](https://github.com/TypeSafeAI/typesafe-router): API payload patterns.
- [Laya ONNX implementation](https://github.com/receptron/laya): alternate local runtime and schema patterns.

The project uses a small provider adapter rather than adopting provider SDKs as
core dependencies. This keeps Jev and local Laya switchable without coupling
evidence schemas to either runtime.
