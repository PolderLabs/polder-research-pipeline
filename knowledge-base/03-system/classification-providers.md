---
type: system
status: current
tags:
  - classification
  - typesafe
  - laya
---

# Classification providers

The evidence API classifies sources, segments, claims, and entities against the
versioned taxonomy in `knowledge-base/research.config.yaml`. The tracked default
uses local Laya with automatic language routing. Deterministic `rules` remains
available as an explicit local provider; Jev can be selected only with project
and target approval for remote processing. No provider silently falls back to
another.

## Jev / TypeSafe API

Jev sends bounded classification input to `POST
https://api.typesafe.ai/v1/systemone` using a bearer key. Configure the key with
`TYPESAFE_API_KEY` or save it in the local dashboard. The endpoint is fixed;
request bodies and keys are excluded from logs and classification records.
Provider responses are schema-checked. HTTP 429 and 529 receive bounded
exponential backoff; other errors are recorded without response bodies.

Treat Jev as a cloud provider. Before selecting it, check source rights and
project data-handling requirements. `internal`, `confidential`, `restricted`,
or `personal_data: true` source records are routed locally by
`classification.routing.sensitive_provider` (the included config selects Laya).
Sensitive records fail closed if configured to Jev. Laya or rules can be chosen
for those records; no remote fallback occurs when the local provider fails.

## Laya, fully local inference

For an NVIDIA GPU, create a project environment and install the matching PyTorch
wheel before installing Polder with Laya. The local RTX 3060 setup uses CUDA
13.0:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cu130
.venv/bin/python -m pip install -e '.[laya]'
.venv/bin/python -c 'import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'
.venv/bin/laya --predict --device cuda --preset router --json 'A research paper about streaming inference'
```

The repository's Laya device setting is `auto`, so CUDA is used when the active
PyTorch build supports it; one checkpoint is kept loaded to fit the RTX 3060's
6 GB memory. For CPU-only use, install from
`https://download.pytorch.org/whl/cpu` instead. Inference uses Laya's Python
`Router` inside the pipeline process. Model weights are downloaded separately
on first inference and cached outside the repository. Inference remains local;
checkpoint download requires Hugging Face network access. For offline
operation, pre-download the model and disable other networked pipeline actions.

Laya's checkpoints support English, multilingual, and typed decisions. Choose a
checkpoint for the observed language mix and workload. Use the Router rather
than assuming all text is English; evaluate language routing on the project's
own records. A high confidence score is not proof that a language route or
classification is correct. Laya quality must be compared against human labels
before unattended use.

`minimum_confidence` is a disposition threshold, not a safety gate. Treat a
confidence score as one input to a disposition, never as evidence that a
classification is correct, and prefer `review_required` for records whose
language or script the routing step could not establish confidently.

Two independent findings support that, and they are separate claims:

1. **Calibration degrades on out-of-distribution languages, and the model
   stays confident while it does.** Laya's own published benchmark reports
   that its English checkpoint's "mean confidence never drops below 0.885 at
   any accuracy level", so no threshold can filter its failure mode — which is
   why it routes before the forward pass rather than after. Independently,
   Tuli et al. (SemEval-2026 Task 13) report that expected calibration error
   roughly doubles when a fine-tuned code transformer moves from seen to
   unseen languages, and that it is wrong on a non-trivial fraction of its
   highest-confidence predictions.
   Sources: <https://github.com/NandhaKishorM/laya/blob/main/BENCHMARKS.md>
   and <https://aclanthology.org/2026.semeval-1.294/>.

2. **A single aggregate calibration figure is not sufficient evidence.** ECE
   and Brier score can *understate* miscalibration in high-effectiveness
   regimes, where correct-prediction dominance masks errors on the minority
   class; a balanced variant of Brier score that weights correct and incorrect
   predictions within each confidence bin reveals substantially poorer
   calibration than the standard scores suggest.
   Source: Prenassi et al. (ACL 2026), "When High Accuracy Hides Poor
   Calibration" — <https://aclanthology.org/2026.acl-long.2128/>.

Consequence for evaluation: report accuracy and confidence separately across
the routing decision, prefer a metric that does not have the limitation in (2),
and compare against human labels. Neither claim is a substitute for a
held-out evaluation on this project's own records.

The RTX 3060 smoke run on 2026-09-25 loaded the English checkpoint and Laya
reported an invalid checkpoint temperature, treating that signal as
uncalibrated. Polder keeps every non-rules taxonomy field in
`review_required`; it does not auto-apply Laya proposals.

## Routing and taxonomy

`classification.provider` sets the normal provider. Optional
`classification.routing.by_target_kind` overrides the provider for `source`,
`segment`, `claim`, `entity`, or `note`. `sensitive_provider` is restricted to
local-safe providers by runtime policy. Sensitive records cannot be forced to
Jev with a per-kind override.

The taxonomy includes one category choice, independent topical tags, and
controlled dimensions such as domain, method, and evidence role. `other` values
allow records outside the current vocabulary. Increment
`taxonomy.version` when editing questions, categories, tags, or dimensions;
historical classification records retain their full taxonomy snapshot and
question-set hash.

## Decision records and controls

Each `.research/classifications/cls_*.json` record stores the text/taxonomy/
question-set hashes, provider and resolved model, answer distributions, field
decisions, timing, and available usage counts. It does not store submitted text
or provider response bodies. Field states are `accepted`, `rejected`,
`review_required`, or `abstained`. Only accepted values are automatically
applied; uncertain values are not silently attached to the evidence record.

Use `polder-research classify-existing --dry-run` to inspect replay scope and
`polder-research classify-existing` to create/reuse immutable results under the
active provider and taxonomy. `classification-compare` reports matched-provider
agreement, which is not accuracy. `classification-evaluate --gold labels.jsonl`
uses separate human labels and held-out matching inputs to report performance.
Label files must include a rubric ID, split, annotator, and exact input hash;
see [[03-system/classification-operations]].

The local dashboard provides per-field analytics and a review inbox. Review
actions are append-only records in `.research/classification_reviews/`; they
do not alter model output or existing evidence metadata. Dashboard reviewer
names are self-reported, not authenticated. The web service binds to loopback;
do not expose it to an untrusted network.

Classification metadata never establishes a claim, decides systematic-review
screening inclusion, rates risk of bias, replaces appraisal, or completes
adjudication. See [[00-home/research-methods]] and
[[03-system/classification-operations]] for those controls.

## Official and upstream references

- [TypeSafe introduction and atomic questions](https://docs.typesafe.ai/introduction)
- [TypeSafe primitives](https://docs.typesafe.ai/primitives)
- [TypeSafe confidence and risk-specific thresholds](https://docs.typesafe.ai/confidence)
- [TypeSafe API and retry guidance](https://docs.typesafe.ai/api)
- [Laya Router and batch API](https://github.com/NandhaKishorM/laya)
- [[03-system/classification-operations|Classification evaluation and operating standard]]
