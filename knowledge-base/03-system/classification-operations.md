---
type: guide
status: current
tags:
  - classification
  - research-methods
---

# Classification operations

This guide defines how provider-generated classification metadata is evaluated,
reviewed, and operated. Classification organizes records and routes work. It is
not evidence, a truth judgment, a substitute for appraisal, or a replacement for
the independent human decisions required by a systematic evidence review.

## Operating sequence

1. Extract text from a source with a format-aware extractor. Preserve its source
   identity, extraction version, and section/page locators. Do not treat decoded
   binary bytes as document text.
2. Submit bounded, privacy-approved state with a versioned set of independent
   questions. A document-level request can ask several decisions together;
   segment-level decisions should retain links to their parent source.
3. Validate the response against the exact question and option schema. Reject
   malformed or out-of-set values. Store full distributions, resolved provider
   and model, input/taxonomy/question-set hashes, latency, and available usage.
4. Apply field-specific policy. A confident negative tag is different from an
   uncertain result. Keep uncertain answers for review rather than silently
   interpreting them as “no”.
5. Preserve model proposals as immutable provenance. Apply metadata only through
   the configured automation policy or a recorded human review decision.
6. Evaluate providers and taxonomy changes against a frozen, human-adjudicated
   set before changing unattended behavior.

## Provider roles

- **Rules** provide a deterministic baseline and can cheaply identify exact
  vocabulary matches. A keyword match is not a model-quality benchmark.
- **Laya** runs locally and is suitable for private or high-volume first-pass
  work when the selected checkpoint has been evaluated on the project corpus.
  Route multilingual text deliberately; high reported confidence does not rule
  out a wrong language or model route.
- **Jev** calls TypeSafe's hosted API. Use it only when the project's data
  handling policy permits sending the submitted text to that service. Keep
  credentials out of project YAML, redact request bodies from logs, and record
  only bounded, non-sensitive operational metadata.

Thresholds are provider-, field-, and consequence-specific. Do not compare Jev
and Laya confidence values directly. TypeSafe describes Choice/Score confidence
as a statistic derived from its probability distribution; Noul returns only the
probability of “yes”. Neither confidence nor probability proves correctness.

## Evaluation protocol

Build a versioned gold set from representative records, stratified by record
kind, research domain, language, and source format. Human labels should be made
without seeing provider outputs, with disagreement adjudicated and the label
rubric recorded. Keep training/tuning items separate from the held-out evaluation
set. Freeze the set and rubric for each reported comparison.

For every provider and field, report precision, recall, F1, confusion counts,
abstention/review rate, coverage, and confidence calibration where sample size
allows. Include per-stratum results, latency percentiles, failure/retry rates,
and Jev token usage when returned. Report the evaluated software/model,
question-set hash, taxonomy version, date, sample count, and uncertainty around
the estimates. Category accuracy should include a Wilson 95% interval; wide
intervals on small strata are evidence that the sample is too small for a
deployment conclusion. Do not use synthetic examples as evidence of real-world
quality.

## Replay and evaluation commands

`polder-research classify-existing --dry-run` lists replay candidates. Source
records are replayed from persisted metadata only; source body text is not
stored in the replay manifest. Use extracted segment records for content-level
classification. A non-dry replay writes an append-only, versioned manifest in
`.research/classification-jobs/` and returns a job ID. Resume only that frozen
target set with `polder-research classify-existing --resume <job-id>`.

Use `--provider rules|laya|jev` to create deliberate matched provider replays.
Any source-derived target marked internal, confidential, restricted, or with
personal data is blocked before Jev is called. `classification-compare` reports
agreement among matched outputs; agreement is not a quality metric.

`classification-evaluate --gold labels.jsonl --split held_out` scores only
human-authored labels. Every JSONL label requires `rubric_id`, `split`, a named
human annotator, and the exact `input_sha256`; taxonomy SHA and version are
checked when available. The report includes coverage, missing reasons,
per-record-kind metrics, category confusion counts, and direct-probability
calibration. It never treats a model prediction as a gold label.

Deploy in stages: shadow evaluation first, then human-reviewed proposals, then
limited automatic metadata application for fields that meet predeclared quality
and coverage criteria. Monitor label distributions, review corrections,
abstention, latency, and provider failures; pause automation when inputs,
taxonomy, model, or quality drift outside the evaluation envelope.

## Research-method boundary

Classification may identify candidate relevance, methods, source type, or
potential support/contradiction for a human to inspect. It must not mark sources
included/excluded, rate risk of bias, verify claims, settle conflicts, or satisfy
systematic-review completion criteria. Follow the frozen protocol and the
independent reviewer and adjudication requirements in
[[00-home/research-methods]].

## References

- [TypeSafe primitives](https://docs.typesafe.ai/primitives)
- [TypeSafe confidence](https://docs.typesafe.ai/confidence)
- [TypeSafe API, including overload retry guidance](https://docs.typesafe.ai/api)
- [Laya upstream Router and batching](https://github.com/NandhaKishorM/laya)
- [[03-system/classification-providers|Provider setup and configuration]]
