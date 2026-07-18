"""
Decides wich prompt to use based on user's input and fills in variables
"""
from pathlib import Path
from jinja2 import Template

PROMPTS_DIR= Path(__file__).parent.parent / "prompts"

PROMPT_TEMPLATE_FILES={
    "executive": "executive_v1.txt",
    "technical": "technical_v1.txt",
    "bullets": "bullets_v1.txt",
}

PROMPT_SYSTEM_PATH= PROMPTS_DIR / "system.txt"

# The {{}} needs to match whe using jinja2, if using replace then use {}
SUMMARY_TEMPLATE= """
Please summarize the following document cleanly:
{{ document_text }} 
"""

def load_system_prompr() -> str:

    if not PROMPT_SYSTEM_PATH.exists():
        raise FileNotFoundError(f"Prompt system file was not found in {PROMPT_SYSTEM_PATH}")
    
    prompt = PROMPT_SYSTEM_PATH.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("System prompt cannot be empty.")
    
    return prompt

def load_prompt_template(style: str) -> str:

    if style not in PROMPT_TEMPLATE_FILES:
        raise ValueError(f"Unsupported summary style: {style}")
    
    PROMPT_PATH= PROMPTS_DIR / PROMPT_TEMPLATE_FILES[style]

    prompt= PROMPT_PATH.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("Temple prompt cannot be empty")
    
    return prompt

def build_user_prompt(template: str, document_text: str) -> str:
    tmpl= Template(template)
    return tmpl.render(document_text=document_text.strip())