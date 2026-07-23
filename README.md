# Document-summarizer

A small pipeline that turns a `.txt` document into an audience-tailored summary
using the Groq API. Load a document, pick a prompt style, render it into a
Jinja2 template, send it to the model, validate the structured response, print
the result, and save the final summary as a `.json` file.

This is the first version of the pipeline:

```
Load document
      ↓
Load selected prompt template
      ↓
Render document into the template
      ↓
Call the model
      ↓
Parse and validate JSON summary
      ↓
Write validated summary to `.json`
      ↓
Print validated summary + saved path + word count
```

Only `.txt` files are supported for now — no PDFs, no Word docs.

## Summary styles

The system prompt keeps every style grounded to the source document (no
invented facts, missing info called out explicitly), and each style prompt
narrows that down for a different reader:

- **executive** — for a C-suite audience: overview, key technical/business
  points, risks or missing info. Concise, non-technical framing.
- **technical** — for engineers: overview, key technical points, risks or
  limitations. Precise, deterministic language.
- **bullets** — for a non-technical/beginner audience: 10 bullet points
  covering the same three areas, casual tone.

All three are capped at 250 words. After the model responds, `main.py` parses
the JSON, validates it against a Pydantic schema, checks that the returned
style matches the requested style, enforces the 250-word cap, and requires at
least one `key_points` item.

## JSON output format

The model is prompted to return only valid JSON, and that JSON must match the
same structure enforced by the schema:

```json
{
  "title": "string",
  "style": "bullets | executive | technical",
  "overview": "string",
  "key_points": ["string"],
  "risks_or_limitations": ["string"]
}
```

The `style` field is the summary format identifier and must exactly match the
requested style from the prompt. The combined text inside `overview`,
`key_points`, and `risks_or_limitations` must stay within the 250-word limit.

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

The current tests cover schema validation, JSON parsing failures, prompt
rendering, style enforcement, word-limit validation, and the main workflow with
mocked dependencies.

## Running it

```bash
uv run src/main.py
```

Right now the entry point is hardcoded, not wired up to CLI arguments yet:
it always summarizes `sample_documents/sample.txt` using the **bullets**
style, with `llama-3.1-8b-instant` as the model. Swap the style by editing
the `SUMMARY_STYLE` constant in `main.py`, or point `DOCUMENT_PATH` at a different
`.txt` file, until argument parsing lands.

During a run, `main.py` currently prints the rendered user prompt, the validated
JSON summary, the saved output path, and the final summary word count.

The generated summary is also written to:

```text
summary_output_json/<style>_<version>_summary.json
```

Example for the current hardcoded sample:

```text
summary_output_json/technical_v1_summary.json
```

## Project layout

- `src/main.py` — entry point; wires the pipeline together with hardcoded
  defaults for the current run.
- `src/document_loader.py` — reads and validates the source `.txt` file.
- `src/prompt_manager.py` — loads the system prompt and the chosen style
  template, renders the document into it via Jinja2.
- `src/llm_client.py` — builds the Groq client from `GROQ_API_KEY`.
- `src/summarizer.py` — sends the prompts to Groq and returns the summary.
- `src/output_parser.py` — parses the model's JSON output, validates it
  against the schema, checks style, and enforces the word cap.
- `src/schema.py` — defines the structured summary shape with Pydantic.
- `summary_output_json/` — stores generated summary `.json` files.
- `prompts/` — system prompt and the three user-prompt style templates.
- `sample_documents/sample.txt` — the sample input used by the current
  hardcoded run.

## Status

- No CLI argument handling yet (planned: pick a file or paste text directly,
  pick a style at the command line).
- `src/templates/summary_template.py` is currently unused.
- Automated tests are in `tests/test_document_summarizer.py`.
