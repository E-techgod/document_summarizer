"""
Decides wich prompt to use based on user's input and fills in variables
"""
import sys
from pathlib import Path
from jinja2 import Template
from templates.prompt_template_files import PROMPT_TEMPLATE_FILES

PROMPTS_DIR= Path(__file__).parent.parent / "prompts"

PROMPT_SYSTEM_FILE= PROMPTS_DIR / "system_prompt" / "system.txt"

# The {{}} needs to match whe using jinja2, if using replace then use {}

def load_system_prompr() -> str:

    if not PROMPT_SYSTEM_FILE.exists():
        raise FileNotFoundError(f"Prompt system file was not found in {PROMPT_SYSTEM_FILE}")
    
    prompt = PROMPT_SYSTEM_FILE.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("System prompt cannot be empty.")
    
    return prompt

def load_prompt_user_template(style: str) -> str: # Different user's prompt versions

    if style not in PROMPT_TEMPLATE_FILES:
        raise ValueError(f"Unsupported summary style: {style}")
    
    PROMPT_PATH= PROMPTS_DIR / "user_prompts" / PROMPT_TEMPLATE_FILES[style]

    prompt= PROMPT_PATH.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("Temple prompt cannot be empty")
    
    return prompt

def build_user_prompt(user_template: str, document_text: str, style: str, max_words: int, output_instructions: str) -> str:
    template= Template(user_template) # Here goes one of the users prompts variations
    return template.render(document_text=document_text.strip(), style=style, max_words=max_words, output_instructions=output_instructions) # PROMPT + SUMMARY_TEMPLATE (RENDER of the DOC)


"""
PROMPT HERE 
...... 


RENDER PART HERE
............
DOCUMENT:
<document>
{{document_text}} 
</document>
............

"""