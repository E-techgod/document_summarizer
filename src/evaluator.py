from pydantic import BaseModel


class EvaluationResult(BaseModel):
    case_id: str
    family: str
    prompt_version: str
    valid_json: bool
    valid_schema: bool
    correct_style: bool
    word_count: int
    within_word_limit: bool
    required_facts_found: int
    required_facts_total: int
    forbidden_claims_found: int
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_response: str
    error: str | None = None
    bullet_count: int | None = None
    bullet_count_correct: bool | None = None
