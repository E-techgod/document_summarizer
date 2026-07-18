# document-summarizer

A small pipeline that turns a `.txt` document into an audience-tailored summary
using the Groq API. Load a document, pick a prompt style, render it into a
Jinja2 template, send it to the model, print the result.

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
Print summary + word count
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

All three are capped at 250 words. After the model responds, `main.py` counts
words itself and prints a warning if the summary ran over.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Add your Groq key to a `.env` file in the project root:

```
GROQ_API_KEY=your-key-here
```

## Running it

```bash
uv run src/main.py
```

Right now the entry point is hardcoded, not wired up to CLI arguments yet:
it always summarizes `sample_documents/sample.txt` using the **technical**
style, with `llama-3.1-8b-instant` as the model. Swap the style by editing
the `styles[...]` index in `main.py`, or point `DOCUMENT_PATH` at a different
`.txt` file, until argument parsing lands.

## Project layout

- `src/main.py` — entry point; wires the pipeline together.
- `src/document_loader.py` — reads and validates the source `.txt` file.
- `src/prompt_manager.py` — loads the system prompt and the chosen style
  template, renders the document into it via Jinja2.
- `src/llm_client.py` — builds the Groq client from `GROQ_API_KEY`.
- `src/summarizer.py` — sends the prompts to Groq and returns the summary.
- `src/output_parser.py` — placeholder for structured (JSON) output parsing
  and schema validation; not implemented yet, and not currently called from
  the pipeline (today's output is plain text).
- `prompts/` — system prompt and the three user-prompt style templates.
- `sample_documents/sample.txt` — the sample input used by the current
  hardcoded run.

## Status

- No CLI argument handling yet (planned: pick a file or paste text directly,
  pick a style at the command line).
- `output_parser.py` is a stub — summaries aren't parsed/validated as
  structured JSON yet.
- No automated tests yet.
