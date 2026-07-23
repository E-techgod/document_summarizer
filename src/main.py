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
from schema import SummaryOutput
from llm_client import create_client_groq
from summarizer import summarize_document
from document_loader import load_and_validate_document
from templates.summary_json_structure_template import JSON_OUTPUT_INSTRUCTIONS
from prompt_manager import load_system_prompr, load_prompt_user_template, build_user_prompt
from output_parser import SummaryParsingError, validate_request_style, count_summary_words, validate_max_words

PROJECT_DIRECTORY= Path(__file__).parent.parent 
DOCS_DIRECTORY= "sample_documents"
DOCUMENT_FILE= "sample.txt" 
DOCUMENT_PATH= PROJECT_DIRECTORY / DOCS_DIRECTORY / DOCUMENT_FILE
MODEL_NAME= "llama-3.1-8b-instant"
MAX_WORDS= 250
SUMMARY_STYLE="technical" # Options: "bullets", "executive", "technical"


def build_summary_output_path(style: str) -> Path:
    return PROJECT_DIRECTORY / "summary_output_json" / f"{style}_summary.json"

def write_summary_json(summary: SummaryOutput, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return output_path

def main():

    document_text = load_and_validate_document(DOCUMENT_PATH) 

    #print(f"\n========================================================= SOURCE DOCUMENT  =========================================================\n {document_text}")
    user_template = load_prompt_user_template(SUMMARY_STYLE) # User prompt (different versions) + the placeholder of the document

    # print(f"\n========================================================= RAW TEMPLATE: {SUMMARY_STYLE} =========================================================\n {user_template}")

    user_prompt = build_user_prompt(user_template, document_text, SUMMARY_STYLE, MAX_WORDS, JSON_OUTPUT_INSTRUCTIONS) # User prompt (different versions) + the document (the placeholder is now filled with the the actual doc)

    print(f"\n========================================================= RENDERED USER PROMPT =========================================================\n {user_prompt}")

    system_prompt= load_system_prompr()

    #print(f"\n========================================================= SYSTEM PROMPT =========================================================\n {system_prompt}")

    client= create_client_groq()

    raw_reponse= summarize_document(client, system_prompt, user_prompt, MODEL_NAME)

    summary= SummaryParsingError.parse_summary_response(raw_reponse)

    validate_request_style(summary, SUMMARY_STYLE)

    validate_max_words(summary, MAX_WORDS)

    output_path = write_summary_json(summary, build_summary_output_path(SUMMARY_STYLE))

    print(f"\n========================================================= VALIDATED SUMMARY: {SUMMARY_STYLE} ========================================================= \n")
    print(summary.model_dump_json(indent=2))
    print(f"\n Summary JSON saved to: {output_path}")

    print(f"\n Word count: {count_summary_words(summary)}")


if __name__ == "__main__":
    main() 
