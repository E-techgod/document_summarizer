"""Responsible for validating structured responses"""
import json
from typing import TypeAlias

from pydantic import ValidationError

from schema import BulletsSummary, ExecutiveSummary, SummaryOutput, TechnicalSummary

ParsedSummary: TypeAlias = SummaryOutput | TechnicalSummary | BulletsSummary | ExecutiveSummary

class SummaryParsingError(ValueError):
    """Raised when LLM summary cannot be parsed or validated"""

    def parse_summary_response(
        response: str,
        requested_style: str | None = None,
        requested_version: str | None = None,
        example_output_keys: tuple[str, ...] = (),
    ) -> ParsedSummary:
        cleaned_response= response.strip()

        if not cleaned_response:
            raise SummaryParsingError("The LLM return an empty response")

        raw_data = _parse_response_payload(cleaned_response)
        normalized_data = normalize_summary_payload(
            raw_data,
            requested_style=requested_style,
            requested_version=requested_version,
            example_output_keys=example_output_keys,
        )

        try:
            return SummaryOutput.model_validate(normalized_data)
        except ValidationError as error:
            raise SummaryParsingError(f"The response failed schema validation:\n{error}") from error


def _parse_response_payload(response: str) -> dict:
    try:
        raw_data = json.loads(response)
    except json.JSONDecodeError:
        raw_data = None

    if isinstance(raw_data, dict):
        return raw_data

    candidates = _extract_json_candidates(response)
    for candidate in reversed(candidates):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    raise SummaryParsingError("The model returned invalid json Unable to locate a valid JSON object in the response")


def _extract_json_candidates(text: str) -> list[str]:
    candidates: list[str] = []

    for start_index, char in enumerate(text):
        if char != "{":
            continue

        depth = 0
        in_string = False
        escaped = False

        for end_index in range(start_index, len(text)):
            current = text[end_index]

            if escaped:
                escaped = False
                continue

            if current == "\\":
                escaped = True
                continue

            if current == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start_index:end_index + 1])
                    break

    return candidates


def normalize_summary_payload(
    raw_data: dict,
    requested_style: str | None = None,
    requested_version: str | None = None,
    example_output_keys: tuple[str, ...] = (),
) -> dict:
    payload = dict(raw_data)

    if {"title", "overview", "key_points", "risks_or_limitations"}.issubset(payload):
        if requested_style and "style" not in payload:
            payload["style"] = requested_style
        if requested_version and "version" not in payload:
            payload["version"] = requested_version
        return payload

    bullets = _coerce_string_list(payload.get("bullets"))
    overview = _coerce_string(payload.get("overview"))
    key_points = _first_non_empty_list(
        _coerce_string_list(payload.get("key_points")),
        _coerce_string_list(payload.get("key_technical_points")),
        _coerce_string_list(payload.get("key_technical_and_business_points")),
    )
    risks = _first_non_empty_list(
        _coerce_string_list(payload.get("risks_or_limitations")),
        _coerce_string_list(payload.get("risks_limitations_or_missing_information")),
    )

    if bullets:
        classified = _classify_bullets(bullets)
        if not overview:
            overview = classified["overview"]
        if not key_points:
            key_points = classified["key_points"]
        if not risks:
            risks = classified["risks_or_limitations"]

    normalized = {
        "title": _coerce_string(payload.get("title")) or _derive_title(overview, requested_style),
        "style": _coerce_string(payload.get("style")) or requested_style,
        "version": _coerce_string(payload.get("version")) or requested_version,
        "overview": overview,
        "key_points": key_points,
        "risks_or_limitations": risks,
    }

    if not normalized["overview"] and key_points:
        normalized["overview"] = key_points[0]
        normalized["key_points"] = key_points[1:] or key_points

    if not normalized["key_points"] and example_output_keys == ("bullets", "style") and bullets:
        classified = _classify_bullets(bullets)
        normalized["overview"] = normalized["overview"] or classified["overview"]
        normalized["key_points"] = classified["key_points"]
        normalized["risks_or_limitations"] = classified["risks_or_limitations"]

    return normalized


def _classify_bullets(bullets: list[str]) -> dict[str, str | list[str]]:
    risk_keywords = (
        "risk",
        "limitation",
        "missing",
        "unclear",
        "unknown",
        "does not",
        "not ",
        "offline",
        "outage",
        "error",
        "gap",
    )
    risks = [bullet for bullet in bullets if any(keyword in bullet.lower() for keyword in risk_keywords)]
    key_points = [bullet for bullet in bullets if bullet not in risks]

    if len(key_points) > 1:
        overview = key_points[-1]
        key_points = key_points[:-1]
    elif key_points:
        overview = key_points[0]
    else:
        overview = bullets[0]

    return {
        "overview": overview,
        "key_points": key_points or [overview],
        "risks_or_limitations": risks,
    }


def _coerce_string(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _coerce_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _first_non_empty_list(*lists: list[str]) -> list[str]:
    for values in lists:
        if values:
            return values
    return []


def _derive_title(overview: str | None, requested_style: str | None) -> str:
    if overview:
        words = overview.split()
        return " ".join(words[:6]).rstrip(".,:;") or "Summary"
    if requested_style:
        return f"{requested_style.title()} Summary"
    return "Summary"

def validate_request_style(summary: ParsedSummary, requested_style: str) -> None:
    if summary.style != requested_style:
        raise ValueError(f"The model return the wrong summary style.\n Expected '{requested_style}' but recieved {summary.style}")

def validate_version_style(summary: ParsedSummary, requested_version: str) -> None:
    if summary.version != requested_version:
        raise ValueError(f"The model return the wrong summary version.\n Expected '{requested_version}' but recieved {summary.version}")


def _infer_summary_family(summary: ParsedSummary) -> str:
    if isinstance(summary, SummaryOutput):
        return summary.style
    if isinstance(summary, TechnicalSummary):
        return "technical"
    if isinstance(summary, BulletsSummary):
        return "bullets"
    if isinstance(summary, ExecutiveSummary):
        return "executive"
    raise ValueError("Unable to infer summary family")


def summary_to_text(summary: ParsedSummary, family: str | None = None) -> str:
    family = family or _infer_summary_family(summary)

    if isinstance(summary, SummaryOutput):
        sections = [
            summary.overview,
            *summary.key_points,
            *summary.risks_or_limitations,
        ]
        return " ".join(sections)

    if family == "technical":
        sections = [
            summary.overview,
            *summary.key_technical_points,
            *summary.risks_or_limitations,
        ]
        return " ".join(sections)

    if family == "bullets":
        return " ".join(summary.bullets)

    if family == "executive":
        sections = [
            summary.overview,
            *summary.key_technical_and_business_points,
            *summary.risks_limitations_or_missing_information,
        ]
        return " ".join(sections)

    raise ValueError(f"Unsupported summary family: {family}")


def count_summary_words(summary: ParsedSummary, family: str | None = None) -> int:
    return len(summary_to_text(summary, family).split())


def validate_max_words(summary: ParsedSummary, family: str | int, max_words: int | None = None) -> None:
    if isinstance(family, int):
        max_words = family
        family = None

    if max_words is None:
        raise ValueError("max_words is required")

    word_count = count_summary_words(summary, family)

    if word_count > max_words:
        raise ValueError(f"The summary contains '{word_count}' words.\n The maximum allowed were '{max_words}'")

        
