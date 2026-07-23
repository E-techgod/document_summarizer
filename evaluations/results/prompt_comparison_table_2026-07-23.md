# Prompt Comparison Table (2026-07-23)

This table is based on:
- `evaluations/results/comparison_tables_2026-07-23.json`
- `evaluations/results/technical_evaluation_2026-07-23.json`
- `evaluations/results/bullets_evaluation_2026-07-23.json`
- `evaluations/results/executive_evaluation_2026-07-23.json`
- prompt files in `prompts/user_prompts/`

## Tested Results

| Family | Version | Prompt structure | Result summary | Pros | Cons | Why this was the result |
| --- | --- | --- | --- | --- | --- | --- |
| `technical` | `v1` | Plain instruction prompt with explicit sections | Best tested technical result. `94/100`, valid JSON, valid schema, style correct, under word limit, `4/5` required facts. | Simple and direct. Low ambiguity. Strong alignment with the evaluator's technical schema (`overview`, `key_technical_points`, `risks_or_limitations`). Fastest tested technical run at `1.0s`. | Less guidance than newer prompts, so it missed one required fact. No explicit reasoning/extraction pass. | The structure is close to what the model needed to return and does not add extra formatting pressure. Fewer moving parts meant the model could produce parseable JSON and stay within constraints. |
| `technical` | `v2` | XML-like tagged prompt with required `<thinking>` extraction pass | Failed structurally. `30/100`, valid JSON but invalid schema, wrong style behavior, no usable fact coverage. | Better instruction quality than `v1`. Stronger grounding language. Explicit extraction pass should help factuality in principle. | `<thinking>` conflicts with `Return only valid JSON` if the model follows both literally. Output format asks for `Overview`, `Key technical points`, and a `style` field, while shared JSON instructions expect normalized keys like `title`, `version`, `key_points`. Longer and more complex. | The failure was not mainly content quality; it was format mismatch. This prompt asks for reasoning-plus-JSON, while the pipeline and evaluator reward clean family-schema JSON only. The model returned JSON, but not in the schema the technical evaluator validates. |
| `executive` | `v3` | Example-driven prompt with exact example input/output to imitate | Failed at JSON parsing. `15/100`, invalid JSON, invalid schema, zero fact coverage. | Strong audience targeting. Example gives clear tone and field naming. Good for style imitation when parsing is robust. | Most brittle format of the tested set. Example-conditioned prompts often copy surrounding prose or partial structure. Also conflicts with shared instructions that require a different schema including `title` and `version`. Slowest tested run at `3.0s`. | The parser recorded `json fail`, which suggests the model did not return a clean JSON object. The example likely improved stylistic clarity but increased the chance of extra text or mismatched keys, which the evaluator rejected immediately. |
| `bullets` | `v1` | Plain instruction prompt asking for 10 bullets | Best overall tested result. `100/100`, valid JSON, valid schema, style correct, under word limit, `5/5` facts, exact `10` bullets. | Very clear output target. Tight alignment with bullets evaluator and schema. Simpler beginner-oriented language likely reduced overproduction. Good balance between structure and freedom. | Less sophisticated than `v2`/`v3`; may be less robust on harder documents even though it worked here. | This prompt fits the evaluated bullets schema well and gives one concrete deliverable: exactly 10 bullets. That made it easy for the model to satisfy both content and structure constraints in a single pass. |

## Untested or Not Executed in Results

| Family | Version | Prompt structure | Status | Expected strengths | Expected risks |
| --- | --- | --- | --- | --- | --- |
| `executive` | `v1` | Plain instruction prompt | Not tested in results | Likely the safest executive prompt because it is simpler and closer to direct JSON generation. | Still may clash with shared JSON instructions vs executive family schema if the runtime injects normalized output instructions. |
| `executive` | `v2` | XML-like tagged prompt with `<thinking>` | Not tested in results | Better grounding and prioritization for executives. | Same structural risk as technical `v2`: hidden reasoning plus JSON-only requirement can break parseability or schema compliance. |
| `technical` | `v3` | Example-driven prompt | Not tested in results | Could improve tone and field consistency if the example exactly matches evaluator schema. | Current example output uses family-specific keys and omits normalized keys like `title` and `version`, so it may fail the shared parser path or evaluator depending on which schema is enforced. |
| `bullets` | `v2` | XML-like tagged prompt with `<thinking>` | Not tested in results | Good factual extraction in principle; clear beginner audience control. | Same dual-output problem as other `v2` prompts. `<thinking>` is risky when the system also demands JSON-only output. |
| `bullets` | `v3` | Example-driven prompt | Not tested in results | The 10-bullet example is concrete and should help count compliance. | Example imitation can cause extra prose, copied wording patterns, or schema drift. Safer than executive `v3` for content shape, but still structurally brittle. |

## Main Pattern

| Pattern | Observation |
| --- | --- |
| Simplest prompts performed best | `v1` prompts were the most reliable in the actual results because they minimized conflict between content instructions and output-format constraints. |
| Structural failures dominated | The weak scores were caused more by parsing/schema issues than by hallucinations or factual mistakes. Forbidden claims stayed at `0` in every tested case. |
| Prompt/evaluator mismatch is the biggest issue | Prompt files, shared JSON instructions, parser normalization, and family-specific evaluator schemas are not fully aligned. Some prompts ask for one schema while the shared template asks for another. |
| `<thinking>` is high risk in this pipeline | `v2` prompts introduce an extraction pass that is useful for quality, but unsafe when the system requires the final response to be only valid JSON. |
| Example prompts are stylistically strong but brittle | `v3` prompts help tone and layout imitation, but they are more likely to produce formatting drift unless the example schema exactly matches the evaluator schema. |

## Bottom Line

- Best tested prompt for reliability: `bullets v1`
- Best tested prompt for technical summaries: `technical v1`
- Weakest tested behavior: `executive v3`
- Main reason for poor results: output-format conflicts, not factual quality
