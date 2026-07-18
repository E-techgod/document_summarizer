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
from document_loader import load_and_validate_document
from prompt_manager import load_prompt_template, build_user_prompt, SUMMARY_TEMPLATE

PROJECT_DIRECTORY= Path(__file__).parent.parent 
DOCS_DIRECTORY= "sample_documents"
DOCUMENT_FILE= "sample.txt" 
DOCUMENT_PATH= PROJECT_DIRECTORY / DOCS_DIRECTORY / DOCUMENT_FILE

def main():
    document_text = load_and_validate_document(DOCUMENT_PATH)

    template = load_prompt_template("executive")

    final_prompt = build_user_prompt(template, document_text)

    print(final_prompt)

if __name__ == "__main__":
    main() 