# Document-summarizer

[![Tests](https://github.com/E-techgod/document_summarizer/actions/workflows/tests.yml/badge.svg)](https://github.com/E-techgod/document_summarizer/actions/workflows/tests.yml)

Current package version: `0.1.0`

A small pipeline that turns a `.txt` document into an audience-tailored summary
using the Groq API. Load a document, pick a prompt family and version, render
it into a Jinja2 template, send it to the model, validate the structured
response, and save the result as a `.json` file. The repo also includes an
evaluation harness for comparing prompt versions across test cases.

This is the current single-document pipeline in `src/main.py`:

```
Load document
      ↓
Load selected prompt template
      ↓
Build the prompt contract
      ↓
Render document + output instructions into the template
      ↓
Call the model
      ↓
Parse and normalize JSON response
      ↓
Validate against the requested family schema
      ↓
Write validated summary to `.json`
      ↓
Print rendered prompt + validated summary + saved path + word count
```

Only `.txt` files are supported for now — no PDFs, no Word docs.

## Summary styles

The system prompt keeps every style grounded to the source document, and each
prompt family narrows that down for a different reader:

- **executive** — for a C-suite audience: overview, key technical/business
  points, risks or missing info.
- **technical** — for engineers: overview, key technical points, risks or
  limitations.
- **bullets** — a bullet-list version for a non-technical or beginner reader.

There are three prompt versions for each family: `v1`, `v2`, and `v3`.
The current hardcoded run in `src/main.py` uses the **technical** family with
prompt version **v1** and a 250-word limit.

## JSON output format

The runtime path in `src/main.py` normalizes model output into this shared
shape:

```json
{
  "title": "string",
  "style": "bullets | executive | technical",
  "version": "v1 | v2 | v3",
  "overview": "string",
  "key_points": ["string"],
  "risks_or_limitations": ["string"]
}
```

`src/schema.py` still also defines narrower family-specific schemas:

- `technical` expects `overview`, `key_technical_points`,
  `risks_or_limitations`, `style`
- `bullets` expects `bullets`, `style`
- `executive` expects `overview`, `key_technical_and_business_points`,
  `risks_limitations_or_missing_information`, `style`

The parser layer currently bridges between those family-specific payloads and
the shared runtime output shape.

## Evaluation results

Latest saved evaluation artifacts for July 23, 2026:

- [Prompt comparison table](./evaluations/results/prompt_comparison_table_2026-07-23.md)
- [Cross-family comparison metrics](./evaluations/results/comparison_tables_2026-07-23.json)
- [Technical evaluation details](./evaluations/results/technical_evaluation_2026-07-23.json)
- [Bullets evaluation details](./evaluations/results/bullets_evaluation_2026-07-23.json)
- [Executive evaluation details](./evaluations/results/executive_evaluation_2026-07-23.json)

The current results show that the simplest `v1` prompts were the most reliable,
while weaker scores were mostly caused by output-format and schema mismatches
between prompt versions and the evaluator, not by forbidden claims.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Add your Groq key to a `.env` file in the project root:

```
GROQ_API_KEY=your-key-here
```

## Testing

Run the automated test suite with:

```bash
uv run pytest -q
```

The suite covers schema validation, JSON parsing failures, prompt rendering,
versioned prompt loading, normalization of alternate response shapes, and the
main workflow with mocked dependencies.

I could not re-verify the old collected-count claim on July 23, 2026 because
`pytest` is not installed in the current environment. The visible test file
contains `31` test functions.

## Running it

```bash
document-summarizer
```

`uv sync` installs the project itself (via the `document-summarizer` entry
point defined in `pyproject.toml`), so once dependencies are synced the
command above works from anywhere inside the project's virtual environment.

Note: `src/main.py` uses relative imports internally, so running it directly
as a script (`uv run src/main.py` / `python src/main.py`) no longer works —
it only resolves correctly when run as part of the installed package via the
`document-summarizer` command above.

Right now the entry point is still hardcoded, not wired up to CLI arguments
yet: it targets `sample_documents/sample.txt`, uses the **technical** family,
prompt version **v1**, `llama-3.1-8b-instant`, and `TEMPERATURE = 0.0`.
Swap the family by editing `SUMMARY_STYLE`, the prompt version by editing
`SUMMARY_VERSION`, or point `DOCUMENT_PATH` at a different `.txt` file until
argument parsing lands.

During a run, `main.py` is wired to print the rendered user prompt, then the
validated summary JSON, saved output path, and final word count after
validation.

The generated summary is also written to a version-specific folder:

```text
summary_output_json/<version>/<style>_<version>_summary.json
```

Example for the current hardcoded sample:

```text
summary_output_json/v1/technical_v1_summary.json
```

## Project layout

- `src/main.py` is the single-document entry point.
- `evaluations/run_eval.py` is the evaluation entry point.
- `src/` holds the runtime pipeline, parser, schemas, and evaluation logic.
- `prompts/` holds the system prompt and versioned family prompts under
  `v1/`, `v2/`, and `v3/`.
- `summary_output_json/` stores generated summary `.json` files grouped by
  prompt version.
- `evaluations/` holds evaluation documents, cases, and saved results.
- `sample_documents/sample.txt` is the sample input used by the current
  hardcoded run.

## Status

- No CLI argument handling yet (planned: pick a file or paste text directly,
  pick a style at the command line).
- `src/templates/summary_template.py` is currently unused.
- `src/main.py` still calls `validate_max_words(summary, MAX_WORDS)`, and
  `src/output_parser.py` handles that older call style by treating an integer
  second argument as `max_words`.
- Automated tests are in `tests/test_document_summarizer.py`.
