"""
Decides wich prompt to use based on user's input and fills in variables
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from jinja2 import Template
from templates.prompt_template_files import PROMPT_TEMPLATE_FILES

PROMPTS_DIR= Path(__file__).parent.parent / "prompts"

PROMPT_SYSTEM_FILE= PROMPTS_DIR / "system_prompt" / "system.txt"


@dataclass(frozen=True)
class PromptContract:
    style: str
    version: str
    expects_extraction_block: bool
    example_output_keys: tuple[str, ...]
    rendered_prompt: str

# The {{}} needs to match whe using jinja2, if using replace then use {}

def load_system_prompr() -> str:

    if not PROMPT_SYSTEM_FILE.exists():
        raise FileNotFoundError(f"Prompt system file was not found in {PROMPT_SYSTEM_FILE}")
    
    prompt = PROMPT_SYSTEM_FILE.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("System prompt cannot be empty.")
    
    return prompt

def load_prompt_user_template(style: str, version: str) -> str: # Different user's prompt versions

    if style not in PROMPT_TEMPLATE_FILES:
        raise ValueError(f"Unsupported summary style: {style}")

    style_templates = PROMPT_TEMPLATE_FILES[style]

    if version not in style_templates:
        raise ValueError(f"Unsupported prompt version '{version}' for style '{style}'")

    PROMPT_PATH= PROMPTS_DIR / "user_prompts" / version / style_templates[version]

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt template file was not found in {PROMPT_PATH}")

    prompt= PROMPT_PATH.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("Temple prompt cannot be empty")
    
    return prompt

def render_output_instructions(output_instructions: str, style: str, version: str, max_words: int) -> str:
    template = Template(output_instructions)
    return template.render(style=style, version=version, max_words=max_words).strip()


def _extract_json_object_block(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return None


def build_prompt_contract(
    user_template: str,
    document_text: str,
    style: str,
    version: str,
    max_words: int,
    output_instructions: str,
) -> PromptContract:
    rendered_prompt = build_user_prompt(
        user_template=user_template,
        document_text=document_text,
        style=style,
        version=version,
        max_words=max_words,
        output_instructions=output_instructions,
    )
    example_block = _extract_json_object_block(user_template)
    example_output_keys: tuple[str, ...] = ()

    if example_block:
        import json

        try:
            parsed_example = json.loads(example_block)
        except json.JSONDecodeError:
            parsed_example = None

        if isinstance(parsed_example, dict):
            example_output_keys = tuple(parsed_example.keys())

    return PromptContract(
        style=style,
        version=version,
        expects_extraction_block="<thinking>" in user_template.lower(),
        example_output_keys=example_output_keys,
        rendered_prompt=rendered_prompt,
    )

def build_user_prompt(
    user_template: str,
    document_text: str,
    style: str,
    version: str,
    max_words: int,
    output_instructions: str,
) -> str:
    template= Template(user_template) # Here goes one of the users prompts variations
    rendered_output_instructions = render_output_instructions(output_instructions, style, version, max_words)
    return template.render(
        document_text=document_text.strip(),
        style=style,
        version=version,
        max_words=max_words,
        output_instructions=rendered_output_instructions,
    )
    # PROMPT + SUMMARY_TEMPLATE (RENDER of the DOC)
    
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
