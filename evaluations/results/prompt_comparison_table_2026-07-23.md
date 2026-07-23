# Prompt Comparison — Real Evaluation Run (2026-07-23)

Full matrix: **3 families × 5 documents × 3 prompt versions = 45 evaluations.**
Model `llama-3.1-8b-instant` (Groq), `temperature=0.0`, `max_words=250`.
Result: **45 completed, 0 failed.**

Source data:
- `evaluations/results/comparison_tables_2026-07-23.json`
- `evaluations/results/technical_evaluation_2026-07-23.json`
- `evaluations/results/bullets_evaluation_2026-07-23.json`
- `evaluations/results/executive_evaluation_2026-07-23.json`
- Cases: `evaluations/cases/evaluation_cases.json`
- Prompts: `prompts/user_prompts/`

---

## Results

### Technical

| Version | Cases | Valid JSON | Schema valid | Word limit | Fact coverage | Forbidden claims | Avg score | Avg latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1` | 5 | 100% | 100% | 100% | 72.0% | 1 | 88.6 | 2.79s |
| `v2` | 5 | 100% | 100% | 100% | 84.0% | 0 | 95.2 | 5.88s |
| `v3` | 5 | 100% | 100% | 100% | 80.0% | 0 | 94.0 | 5.99s |

### Bullets

| Version | Cases | Valid JSON | Schema valid | Word limit | Fact coverage | Forbidden claims | Avg score | Avg latency | 10-bullet rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1` | 5 | 100% | 100% | 100% | 88.0% | 1 | 93.4 | 5.18s | 100% |
| `v2` | 5 | 100% | 100% | 100% | 84.0% | 0 | 95.2 | 7.80s | 100% |
| `v3` | 5 | 100% | 100% | 100% | 92.0% | 1 | 94.6 | 9.40s | 100% |

### Executive

| Version | Cases | Valid JSON | Schema valid | Word limit | Fact coverage | Forbidden claims | Avg score | Avg latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `v1` | 5 | 100% | 100% | 100% | 92.0% | 1 | 94.6 | 3.65s |
| `v2` | 5 | 100% | 100% | 100% | 80.0% | 1 | 91.0 | 7.95s |
| `v3` | 5 | 100% | 100% | 100% | 80.0% | 0 | 94.0 | 7.63s |

---

## Finding 1 — Every structural metric is saturated

`valid_json`, `schema_valid`, and `word_limit_compliance` are **100% in all nine cells**. Across 45 runs there was not a single parse failure, schema violation, or word-limit breach.

This includes the `v2` prompts, which mandate a `<thinking>` reasoning block, and the `v3` prompts, which supply a few-shot example. Neither caused the format instability that was expected — the model reliably produced schema-conformant JSON under all three prompt designs.

**Consequence:** three of the six rubric components no longer discriminate between prompts. They now function as pass/fail gates that everything passes.

## Finding 2 — Fact coverage is the only quality axis carrying signal

Fact coverage spans **72%–92%**, the only metric with meaningful variance. Averaged across families:

| Version | Mean fact coverage |
| --- | --- |
| `v1` | 84.0% |
| `v2` | 82.7% |
| `v3` | 84.0% |

**No version wins.** `v1` and `v3` tie; `v2` is marginally lower. Per-family winners are inconsistent — `v2` leads technical, `v3` leads bullets, `v1` leads executive. A prompt design that were genuinely superior would be expected to lead in all three.

## Finding 3 — Prompt complexity roughly doubles latency for no accuracy gain

This is the largest and most consistent effect in the dataset. It holds in every family without exception.

| Version | Mean latency | vs `v1` | Mean score |
| --- | --- | --- | --- |
| `v1` | 3.87s | — | 92.2 |
| `v2` | 7.21s | 1.86× | 93.8 |
| `v3` | 7.67s | 1.98× | 94.2 |

`v3` buys **2.0 score points for 2× the latency**, and that 2.0 sits well inside the noise band described below. The `<thinking>` block and the few-shot example both inflate output tokens without measurably improving factual accuracy.

## Finding 4 — Score differences are within noise

Total spread across all nine cells is **88.6 to 95.2** — 6.6 points.

With `n=5` cases and 25 fact checks per cell, technical `v1` (72%) versus `v2` (84%) is 18/25 versus 21/25 correct: **a three-fact difference**. That is not a basis for preferring one prompt over another. No statistical significance is claimed anywhere in this report.

## Finding 5 — Five forbidden claims appeared across 45 runs

Forbidden claims are assertions the source documents do not support and the prompts explicitly prohibit. Five were detected:

| Family | Version | Count |
| --- | --- | --- |
| technical | `v1` | 1 |
| bullets | `v1` | 1 |
| bullets | `v3` | 1 |
| executive | `v1` | 1 |
| executive | `v2` | 1 |

`v1` accounts for three of the five, `v2` and `v3` for one each. Directionally this suggests the more elaborate prompts suppress unsupported claims slightly better, but at these counts the difference is not distinguishable from chance.

This is the highest-value signal in the run: it is the only metric measuring genuine hallucination rather than format compliance. The specific failing responses are worth manual review.

---

## Methodology note: the rubric is compressing results

The 100-point rubric allocates:

| Component | Points | Varies? |
| --- | --- | --- |
| JSON validity | 15 | No — 100% everywhere |
| Schema validity | 15 | No — 100% everywhere |
| Correct style | 10 | No — 100% everywhere |
| Word-limit compliance | 15 | No — 100% everywhere |
| Required-fact coverage | 30 | **Yes** |
| No forbidden claims | 15 | **Yes** |

**55 of 100 points are earned automatically by every run.** Only 45 points vary, which is why all nine cells land in the high 80s / low 90s regardless of prompt quality.

Verification — technical `v1`: `55 + (30 × 0.72) + 12 = 88.6`. Matches the reported score exactly.

The rubric was designed under the assumption that structural failures would be common. They are not. Rebalancing toward fact coverage and forbidden claims — or collapsing the four saturated components into a single small "parsed successfully" gate — would let real differences surface.

## Methodology note: JSON extraction

`evaluator.parse_json_response` originally used bare `json.loads`, which scored any reply wrapped in code fences or preceded by a `<thinking>` block as invalid JSON. Because the `v2` prompts *require* a thinking block, every `v2` run would have failed on parsing rather than on summary quality — an artifact of the measurement instrument, not a property of the prompt.

The evaluator now uses the same `_parse_response_payload` extractor as the runtime pipeline, so the evaluation measures what production would actually accept. Bare-JSON output is tracked separately as `clean_json` so format tidiness cannot mask summary quality.

---

## Conclusions

1. **Ship `v1`.** Across 45 evaluations the three prompt versions are indistinguishable on quality while `v1` runs roughly twice as fast. The added complexity of `v2` and `v3` bought no measurable accuracy.
2. **The harness needs harder cases.** Four of six rubric components are pinned at 100%. The current five documents do not stress the pipeline enough to differentiate prompt designs.
3. **Hallucination is the remaining real problem.** Five forbidden claims in 45 runs is the only genuine quality failure observed, and it is where further prompt work should be aimed.

## Next steps

- Add adversarial cases: contradictory sources, very long documents, documents with deliberate factual gaps.
- Rebalance the rubric so saturated components contribute a smaller fixed share.
- Add `clean_json` as a column to the comparison tables.
- Manually review the five responses containing forbidden claims.
- Increase `n` per cell before drawing any conclusion about version differences.

---

*Changelog: a previous version of this file reported illustrative figures produced from placeholder fixtures rather than a live model run. All numbers above come from the 45-evaluation run recorded in the linked result files.*