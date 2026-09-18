# ECI EVM Golden Dataset v1

## Purpose

This package provides a 120-question golden set for benchmarking an adaptive retrieval engine over five unique Election Commission of India EVM/VVPAT documents.

## Distribution

| Query class | Count | Evaluation intent |
|---|---:|---|
| `single_hop_factual` | 30 | Direct facts expected from one evidence unit |
| `multi_hop_relational` | 30 | Questions requiring two or more evidence units and synthesis |
| `corpus_summary` | 30 | Broad process or theme summaries supported by multiple sources/sections |
| `unanswerable` | 30 | Plausible ECI questions not supported by this corpus; expected action is abstention |

## Important design choices

- No expected retrieval strategy is stored. The cheapest sufficient strategy must be derived empirically from A1-A5 outcomes, not manually labelled in the gold set.
- Each class contains 10 `development` and 20 `test` items. Tune router thresholds only on development items; report final results on the held-out 80-item test split.
- `EVM BROCHURE FOR.pdf` was excluded because it is an exact duplicate of the candidate/political-party brochure.
- Every answerable item contains a reference answer, atomic reference claims, required entities, and verified source evidence.
- Every unanswerable item has `reference_answer: null`, no evidence, `expected_behavior: abstain`, and an abstention reason.
- `relevant_chunk_ids` is intentionally empty until the ingestion pipeline assigns immutable production chunk IDs.

## Evidence matching

Use `relevant_evidence_ids` as the stable source-level gold key:

- FAQ evidence: `DOC_EVM_FAQ_2026#ECI-EVM-CNN-QNN`
- Other PDF evidence: `DOCUMENT_ID#pNNN`

During ingestion, copy the matching locator into every derived chunk's metadata. After chunking is frozen, resolve each gold evidence locator to one or more chunk IDs and populate `relevant_chunk_ids`. This makes Recall@K, MRR and nDCG reproducible even if the Elasticsearch internal `_id` changes.

## Recommended benchmark protocol

1. Freeze corpus files, chunking, embedding model and prompts.
2. Map source locators to immutable chunk IDs.
3. Run A1-A6 on the same 120 questions.
4. Evaluate retrieval overall and per query class.
5. Evaluate answers for correctness, faithfulness, citation support and abstention.
6. Derive the cheapest sufficient oracle strategy from A1-A5 results; compare A6 using quality regret, cost regret and retry success.

## Leakage control

Do not tune router thresholds on all 120 items. Use a development subset for threshold selection and preserve a held-out test subset. If examples are generated or expanded later, keep document hashes and dataset versions fixed in the benchmark report.
