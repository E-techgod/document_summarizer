"""Responsible for validating structured responses"""
import json
from schema import SummaryOutput
from pydantic import ValidationError

class SummaryParsingError(ValueError):
    """Raised when LLM summary cannot be parsed or validated"""

    def parse_summary_response(response: str) -> SummaryOutput:
        cleaned_response= response.strip()

        if not cleaned_response:
            raise SummaryParsingError("The LLM return an empty response")
        
        try:
            raw_data= json.loads(cleaned_response)
        except json.JSONDecodeError as error:
            raise SummaryParsingError(f"The model returned invalid json {error.msg}") from error 
        
        try:
            return SummaryOutput.model_validate(raw_data)
        except ValidationError as error:
            raise SummaryParsingError(f"The response failed schema validation:\n{error}") from error
        

def validate_request_style(summary: SummaryOutput, requested_style: str) -> None:
    if summary.style != requested_style:
        raise ValueError(f"The model return the wrong summary style.\n Expected '{requested_style}' but recieved {summary.style}")
    
def count_summary_words(summary: SummaryOutput) -> int:
    """ Counts only the meaningful sections"""
    sections=[
        summary.overview,
        *summary.key_points,
        *summary.risks_or_limitations,
    ]

    combined_sections= " ".join(sections)
    return len(combined_sections.split())

def validate_max_words(summary: SummaryOutput, max_words: int) -> None:
    word_count= count_summary_words(summary)

    if word_count > max_words:
        raise ValueError(f"The summary contains '{word_count}' words.\n The maximum allowed were '{max_words}'")

        