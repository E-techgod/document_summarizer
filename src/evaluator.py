import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from output_parser import (
    ParsedSummary,
    SummaryParsingError,
    _parse_response_payload,
    count_summary_words,
    summary_to_text,
)
from schema import SCHEMA_BY_FAMILY


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
    clean_json: bool = False


def calculate_score(result: EvaluationResult) -> float:
    score = 0.0

    if result.valid_json:
        score += 15

    if result.valid_schema:
        score += 15

    if result.correct_style:
        score += 10

    if result.within_word_limit:
        score += 15

    if result.required_facts_total > 0:
        coverage_ratio = result.required_facts_found / result.required_facts_total
        score += 30 * coverage_ratio

    if result.forbidden_claims_found == 0:
        score += 15

    return round(score, 2)


def parse_json_response(response_text: str) -> dict[str, Any]:
    """Extract the JSON object from a model reply, tolerating fences and
    surrounding prose. Uses the same extractor as the runtime pipeline so the
    evaluation measures what production would actually accept."""
    return _parse_response_payload(response_text)


def evaluate_json_validity(response_text: str) -> bool:
    """True if a JSON object can be recovered from the reply at all."""
    try:
        parse_json_response(response_text)
        return True
    except (SummaryParsingError, json.JSONDecodeError, ValueError, TypeError):
        return False


def evaluate_clean_json(response_text: str) -> bool:
    """True only if the reply was bare JSON, with no fences or extra prose.
    Tracked separately so format tidiness never masks summary quality."""
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return False
    return isinstance(parsed, dict)


def validate_summary_schema(payload: dict[str, Any], family: str) -> ParsedSummary:
    schema_cls = SCHEMA_BY_FAMILY[family]
    return schema_cls.model_validate(payload)


def evaluate_schema_validity(payload: dict[str, Any], family: str) -> tuple[bool, ParsedSummary | None, str | None]:
    try:
        summary = validate_summary_schema(payload, family)
        return True, summary, None
    except ValidationError as error:
        return False, None, str(error)


def evaluate_style_correctness(summary: ParsedSummary | None, family: str) -> bool:
    return summary is not None and summary.style == family


def evaluate_word_limit(summary: ParsedSummary | None, family: str, max_words: int) -> tuple[int, bool]:
    if summary is None:
        return 0, False

    word_count = count_summary_words(summary, family)
    return word_count, word_count <= max_words


def evaluate_required_fact_coverage(summary: ParsedSummary | None, family: str, required_facts: list[str]) -> tuple[int, int]:
    if summary is None:
        return 0, len(required_facts)

    searchable_text = _normalize_text(summary_to_text(summary, family))
    matches = sum(1 for fact in required_facts if _required_fact_matches(searchable_text, fact))
    return matches, len(required_facts)


def evaluate_forbidden_claim_detection(summary: ParsedSummary | None, family: str, forbidden_claims: list[str]) -> int:
    if summary is None:
        return 0

    searchable_text = _normalize_text(summary_to_text(summary, family))
    return sum(1 for claim in forbidden_claims if _forbidden_claim_matches(searchable_text, claim))


def evaluate_bullet_count(
    summary: ParsedSummary | None,
    family: str,
    expected_bullet_count: int | None,
) -> tuple[int | None, bool | None]:
    if family != "bullets":
        return None, None

    if summary is None:
        return None, False if expected_bullet_count is not None else None

    bullet_count = len(summary.bullets)
    if expected_bullet_count is None:
        return bullet_count, None

    return bullet_count, bullet_count == expected_bullet_count


def _required_fact_matches(normalized_summary_text: str, reference_text: str) -> bool:
    normalized_reference = _normalize_text(reference_text)
    if not normalized_reference:
        return False

    if normalized_reference in normalized_summary_text:
        return True

    tokens = _significant_tokens(normalized_reference)
    if not tokens:
        return False

    matched_tokens = sum(1 for token in tokens if token in normalized_summary_text)
    threshold = max(1, int(len(tokens) * 0.6))
    return matched_tokens >= threshold


def _forbidden_claim_matches(normalized_summary_text: str, reference_text: str) -> bool:
    normalized_reference = _normalize_text(reference_text)
    if not normalized_reference:
        return False

    if normalized_reference in normalized_summary_text:
        return True

    tokens = _significant_tokens(normalized_reference)
    if not tokens:
        return False

    matched_tokens = sum(1 for token in tokens if token in normalized_summary_text)
    return matched_tokens == len(tokens)


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    collapsed = re.sub(r"[^a-z0-9%$]+", " ", lowered)
    return re.sub(r"\s+", " ", collapsed).strip()


def _significant_tokens(text: str) -> list[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "were",
        "with",
    }
    return [token for token in text.split() if token not in stop_words]
