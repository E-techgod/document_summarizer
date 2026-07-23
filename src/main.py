"""
Controls de application flow:
1. Read the arguments
    1.1 If the user wants the app to summarize a direct text from the terminal
    1.2 If he wants to summarize a document
2. Load de documents
3. Select prompt
4. Request the summary
5. Return summary

This first version only allows .txt files, not pds, docs

The first version of the pipeline:
Load document
      ↓
Load selected prompt template
      ↓
Render document into the Jinja template
"""

from pathlib import Path

from .document_loader import load_and_validate_document
from .llm_client import create_client_groq
from .output_parser import (
    SummaryParsingError,
    count_summary_words,
    validate_max_words,
    validate_request_style,
)
from .prompt_manager import (
    build_prompt_contract,
    load_prompt_user_template,
    load_system_prompr,
)
from .schema import SummaryOutput
from .summarizer import summarize_document
from .templates.prompt_template_files import PROMPT_TEMPLATE_FILES
from .templates.summary_json_structure_template import JSON_OUTPUT_INSTRUCTIONS

PROJECT_DIRECTORY = Path(__file__).parent.parent
DOCS_DIRECTORY = "sample_documents"
DOCUMENT_FILE = "sample.txt"
DOCUMENT_PATH = PROJECT_DIRECTORY / DOCS_DIRECTORY / DOCUMENT_FILE
MODEL_NAME = "llama-3.1-8b-instant"
MAX_WORDS = 250
SUMMARY_STYLE = "technical"  # Options: "bullets", "executive", "technical"
SUMMARY_VERSION = "v1"  # Options: "v1", "v2", "v3"
TEMPERATURE = 0.0  # Keep it 0.0 for a summary (deterministic/focused)


def get_prompt_version(style: str, version: str) -> str:
    template_filename = PROMPT_TEMPLATE_FILES[style][version]
    template_stem = Path(template_filename).stem
    expected_suffix = f"_{version}"

    if not template_stem.endswith(expected_suffix):
        raise ValueError(
            f"Prompt template filename must end with a version suffix: {template_filename}"
        )

    return version


def build_summary_output_path(style: str, version: str) -> Path:
    version = get_prompt_version(style, version)
    return (
        PROJECT_DIRECTORY
        / "summary_output_json"
        / version
        / f"{style}_{version}_summary.json"
    )


def write_summary_json(summary: SummaryOutput, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def main():

    document_text = load_and_validate_document(DOCUMENT_PATH)

    # print(f"\n========================================================= SOURCE DOCUMENT  =========================================================\n {document_text}")
    user_template = load_prompt_user_template(
        SUMMARY_STYLE, SUMMARY_VERSION
    )  # User prompt (different versions) + the placeholder of the document

    # print(f"\n========================================================= RAW TEMPLATE: {SUMMARY_STYLE} =========================================================\n {user_template}")

    prompt_contract = build_prompt_contract(
        user_template=user_template,
        document_text=document_text,
        style=SUMMARY_STYLE,
        version=SUMMARY_VERSION,
        max_words=MAX_WORDS,
        output_instructions=JSON_OUTPUT_INSTRUCTIONS,
    )
    user_prompt = prompt_contract.rendered_prompt

    print(
        f"\n========================================================= RENDERED USER PROMPT =========================================================\n {user_prompt}"
    )

    system_prompt = load_system_prompr()

    # print(f"\n========================================================= SYSTEM PROMPT =========================================================\n {system_prompt}")

    client = create_client_groq()

    raw_reponse = summarize_document(
        client, system_prompt, user_prompt, MODEL_NAME, TEMPERATURE
    ).text

    summary = SummaryParsingError.parse_summary_response(
        raw_reponse,
        requested_style=SUMMARY_STYLE,
        requested_version=SUMMARY_VERSION,
        example_output_keys=prompt_contract.example_output_keys,
    )

    validate_request_style(summary, SUMMARY_STYLE)

    validate_max_words(summary, MAX_WORDS)

    output_path = write_summary_json(
        summary, build_summary_output_path(SUMMARY_STYLE, SUMMARY_VERSION)
    )

    print(
        f"\n========================================================= VALIDATED SUMMARY: {SUMMARY_STYLE} ========================================================= \n"
    )
    print(summary.model_dump_json(indent=2))
    print(f"\n Summary JSON saved to: {output_path}")

    print(f"\n Word count: {count_summary_words(summary)}")


if __name__ == "__main__":
    main()
