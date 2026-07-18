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
from llm_client import create_client_groq
from document_loader import load_and_validate_document
from prompt_manager import load_system_prompr, load_prompt_user_template, build_user_prompt
from summarizer import summarize_document

PROJECT_DIRECTORY= Path(__file__).parent.parent 
DOCS_DIRECTORY= "sample_documents"
DOCUMENT_FILE= "sample.txt" 
DOCUMENT_PATH= PROJECT_DIRECTORY / DOCS_DIRECTORY / DOCUMENT_FILE
MODEL_NAME= "llama-3.1-8b-instant"

def count_words(text: str) -> int:
    return len(text.split())

def main():

    document_text = load_and_validate_document(DOCUMENT_PATH) 

    print(f"\n========================================================= SOURCE DOCUMENT  =========================================================\n {document_text}")

    user_template = load_prompt_user_template("bullets") # User prompt (different versions) + the placeholder of the document

    print(f"\n========================================================= RAW TEMPLATE: executive_v1 =========================================================\n {template}")

    user_prompt = build_user_prompt(user_template, document_text) # User prompt (different versions) + the document (the placeholder is now filled with the the actual doc)

    print(f"\n========================================================= RENDERED USER PROMPT =========================================================\n {user_prompt}")

    system_prompt= load_system_prompr()

    print(f"\n========================================================= SYSTEM PROMPT =========================================================\n {system_prompt}")

    client= create_client_groq()

    summary= summarize_document(client, system_prompt, user_prompt, MODEL_NAME)

    print("\n========================================================= GENERATED SUMMARY ========================================================= \n")
    print(summary)

    word_count= count_words(summary)
    print(f"\nSummary word count: {word_count} ")

    if word_count > 250:
        print("Warning: summary exceeded the requested 250-word limit.")

if __name__ == "__main__":
    main() 