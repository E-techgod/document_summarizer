"""
Decides wich prompt to use based on user's input and fills in variables
"""
from pathlib import Path
from jinja2 import Template

PROMPTS_DIR= Path(__file__).parent.parent / "prompts"

PROMPT_FILES={
    "executive": "executive_v1.txt",
    "technical": "technical_v1.txt",
    "bullets": "bullets_v1.txt",
}

# The {{}} needs to match whe using jinja2, if using replace then use {}
SUMMARY_TEMPLATE= """
Please summarize the following document cleanly:
{{ document_text }} 
"""

def load_prompt_template(style: str) -> str:
    if style not in PROMPT_FILES:
        raise ValueError(f"Unsupported summary style: {style}")
    
    PROMPT_PATH= PROMPTS_DIR / PROMPT_FILES[style]

    return PROMPT_PATH.read_text(encoding="utf-8")

def build_user_prompt(template: str, document_text: str) -> str:
    tmpl= Template(template)
    return tmpl.render(document_text=document_text.strip())