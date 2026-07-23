import json
import time
from pathlib import Path
from typing import Any

from document_loader import load_and_validate_document
from evaluator import (
    EvaluationResult,
    calculate_score,
    evaluate_bullet_count,
    evaluate_clean_json,
    evaluate_forbidden_claim_detection,
    evaluate_json_validity,
    evaluate_required_fact_coverage,
    evaluate_schema_validity,
    evaluate_style_correctness,
    evaluate_word_limit,
    parse_json_response,
)
from output_parser import ParsedSummary
from prompt_manager import (
    build_prompt_contract,
    load_prompt_user_template,
    load_system_prompr,
)
from summarizer import summarize_document

FAMILIES = ("technical", "bullets", "executive")
VERSIONS = ("v1", "v2", "v3")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_evaluation_matrix(
    client: Any,
    cases: list[dict[str, Any]],
    model_name: str,
    temperature: float,
    max_words: int,
    pause_seconds: float = 2.0,
) -> list[EvaluationResult]:
    """Run every (family x case x version) combination.

    Prints one progress line per call so a long run is distinguishable from a
    hang, and pauses between calls to stay under provider rate limits.
    """
    results: list[EvaluationResult] = []
    total = len(FAMILIES) * len(cases) * len(VERSIONS)
    index = 0

    for family in FAMILIES:
        for case in cases:
            for version in VERSIONS:
                index += 1
                label = f"[{index}/{total}] {family}/{version} {case['id']}"
                print(label, end=" ", flush=True)

                result = run_single_evaluation(
                    client=client,
                    case=case,
                    family=family,
                    version=version,
                    model_name=model_name,
                    temperature=temperature,
                    max_words=max_words,
                )
                results.append(result)

                if result.error:
                    print(f"FAIL ({result.error[:70]})", flush=True)
                else:
                    print(
                        f"ok  score={calculate_score(result):.0f} "
                        f"{result.latency_seconds:.1f}s "
                        f"tok={result.input_tokens}/{result.output_tokens}",
                        flush=True,
                    )

                if index < total and pause_seconds:
                    time.sleep(pause_seconds)

    failures = sum(1 for result in results if result.error)
    print(f"\nFinished {total} evaluations - {total - failures} ok, {failures} failed.")

    return results


def aggregate_results_by_family(
    results: list[EvaluationResult],
) -> dict[str, list[dict[str, str | int | float]]]:
    comparison_tables: dict[str, list[dict[str, str | int | float]]] = {}

    for family in FAMILIES:
        family_results = [result for result in results if result.family == family]
        comparison_tables[family] = build_family_comparison_table(
            family, family_results
        )

    return comparison_tables


def build_family_comparison_table(
    family: str,
    family_results: list[EvaluationResult],
) -> list[dict[str, str | int | float]]:
    table_rows: list[dict[str, str | int | float]] = []

    for version in VERSIONS:
        version_results = [
            result for result in family_results if result.prompt_version == version
        ]
        table_rows.append(build_family_version_row(family, version, version_results))

    return table_rows


def build_family_version_row(
    family: str,
    version: str,
    version_results: list[EvaluationResult],
) -> dict[str, str | int | float]:
    cases_tested = len(version_results)
    required_facts_found = sum(
        result.required_facts_found for result in version_results
    )
    required_facts_total = sum(
        result.required_facts_total for result in version_results
    )
    bullet_count_row = (
        build_bullet_count_row(version_results) if family == "bullets" else None
    )

    row: dict[str, str | int | float] = {
        "prompt_version": version,
        "cases_tested": cases_tested,
        "valid_json_rate": ratio_to_percent(
            sum(result.valid_json for result in version_results), cases_tested
        ),
        "schema_valid_rate": ratio_to_percent(
            sum(result.valid_schema for result in version_results), cases_tested
        ),
        "word_limit_compliance": ratio_to_percent(
            sum(result.within_word_limit for result in version_results), cases_tested
        ),
        "fact_coverage": ratio_to_percent(required_facts_found, required_facts_total),
        "forbidden_claims_count": sum(
            result.forbidden_claims_found for result in version_results
        ),
        "average_score": round(
            average([calculate_score(result) for result in version_results]), 2
        ),
        "average_latency_seconds": round(
            average([result.latency_seconds for result in version_results]), 3
        ),
    }

    if bullet_count_row is not None:
        row["bullet_count_10_rate"] = bullet_count_row

    return row


def run_single_evaluation(
    client: Any,
    case: dict[str, Any],
    family: str,
    version: str,
    model_name: str,
    temperature: float,
    max_words: int,
) -> EvaluationResult:
    case_id = str(case["id"])
    raw_response = ""
    latency_seconds = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None

    try:
        document_path = resolve_case_document_path(case["document_path"])
        document_text = load_and_validate_document(str(document_path))
        system_prompt = load_system_prompr()
        user_template = load_prompt_user_template(family, version)
        prompt_contract = build_prompt_contract(
            user_template=user_template,
            document_text=document_text,
            style=family,
            version=version,
            max_words=max_words,
            output_instructions=build_output_instructions_for_family(
                family, version, max_words
            ),
        )

        started_at = time.perf_counter()
        completion = summarize_document(
            client=client,
            system_prompt=system_prompt,
            user_prompt=prompt_contract.rendered_prompt,
            model_name=model_name,
            temp=temperature,
        )
        raw_response = completion.text
        input_tokens = completion.input_tokens
        output_tokens = completion.output_tokens
        latency_seconds = time.perf_counter() - started_at

        valid_json = evaluate_json_validity(raw_response)
        if not valid_json:
            return build_failed_result(
                case_id=case_id,
                family=family,
                prompt_version=version,
                raw_response=raw_response,
                latency_seconds=latency_seconds,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                max_words=max_words,
                required_facts_total=len(case.get("required_facts", [])),
                error="Response was not valid JSON.",
                expected_bullet_count=get_expected_bullet_count(case, family),
            )

        payload = parse_json_response(raw_response)
        valid_schema, summary, schema_error = evaluate_schema_validity(payload, family)
        if not valid_schema or summary is None:
            return build_failed_result(
                case_id=case_id,
                family=family,
                prompt_version=version,
                raw_response=raw_response,
                latency_seconds=latency_seconds,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                max_words=max_words,
                required_facts_total=len(case.get("required_facts", [])),
                error=schema_error or "Response failed schema validation.",
                expected_bullet_count=get_expected_bullet_count(case, family),
                valid_json=True,
            )

        return build_success_result(
            case=case,
            family=family,
            version=version,
            raw_response=raw_response,
            summary=summary,
            latency_seconds=latency_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            max_words=max_words,
        )
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        return build_failed_result(
            case_id=case_id,
            family=family,
            prompt_version=version,
            raw_response=raw_response,
            latency_seconds=latency_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            max_words=max_words,
            required_facts_total=len(case.get("required_facts", [])),
            error=str(error),
            expected_bullet_count=get_expected_bullet_count(case, family),
            valid_json=evaluate_json_validity(raw_response) if raw_response else False,
        )


def build_success_result(
    case: dict[str, Any],
    family: str,
    version: str,
    raw_response: str,
    summary: ParsedSummary,
    latency_seconds: float,
    input_tokens: int | None,
    output_tokens: int | None,
    max_words: int,
) -> EvaluationResult:
    required_facts_found, required_facts_total = evaluate_required_fact_coverage(
        summary,
        family,
        case.get("required_facts", []),
    )
    forbidden_claims_found = evaluate_forbidden_claim_detection(
        summary,
        family,
        case.get("forbidden_claims", []),
    )
    word_count, within_word_limit = evaluate_word_limit(summary, family, max_words)
    bullet_count, bullet_count_correct = evaluate_bullet_count(
        summary,
        family,
        get_expected_bullet_count(case, family),
    )

    return EvaluationResult(
        case_id=str(case["id"]),
        family=family,
        prompt_version=version,
        valid_json=True,
        valid_schema=True,
        correct_style=evaluate_style_correctness(summary, family),
        word_count=word_count,
        within_word_limit=within_word_limit,
        required_facts_found=required_facts_found,
        required_facts_total=required_facts_total,
        forbidden_claims_found=forbidden_claims_found,
        latency_seconds=latency_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        raw_response=raw_response,
        error=None,
        bullet_count=bullet_count,
        bullet_count_correct=bullet_count_correct,
        clean_json=evaluate_clean_json(raw_response),
    )


def build_failed_result(
    case_id: str,
    family: str,
    prompt_version: str,
    raw_response: str,
    latency_seconds: float,
    input_tokens: int | None,
    output_tokens: int | None,
    max_words: int,
    required_facts_total: int,
    error: str,
    expected_bullet_count: int | None,
    valid_json: bool = False,
) -> EvaluationResult:
    bullet_count = None
    bullet_count_correct = None

    if family == "bullets":
        bullet_count, bullet_count_correct = derive_bullet_metrics_from_raw_response(
            raw_response,
            expected_bullet_count,
        )

    return EvaluationResult(
        case_id=case_id,
        family=family,
        prompt_version=prompt_version,
        valid_json=valid_json,
        valid_schema=False,
        correct_style=False,
        word_count=0,
        within_word_limit=False,
        required_facts_found=0,
        required_facts_total=required_facts_total,
        forbidden_claims_found=0,
        latency_seconds=latency_seconds,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        raw_response=raw_response,
        error=error,
        bullet_count=bullet_count,
        bullet_count_correct=bullet_count_correct,
        clean_json=evaluate_clean_json(raw_response) if raw_response else False,
    )


def derive_bullet_metrics_from_raw_response(
    raw_response: str,
    expected_bullet_count: int | None,
) -> tuple[int | None, bool | None]:
    if not raw_response:
        return None, False if expected_bullet_count is not None else None

    try:
        payload = parse_json_response(raw_response)
    except json.JSONDecodeError, ValueError:
        return None, False if expected_bullet_count is not None else None

    bullets = payload.get("bullets")
    if not isinstance(bullets, list):
        return None, False if expected_bullet_count is not None else None

    bullet_count = len([item for item in bullets if isinstance(item, str)])
    if expected_bullet_count is None:
        return bullet_count, None

    return bullet_count, bullet_count == expected_bullet_count


def get_expected_bullet_count(case: dict[str, Any], family: str) -> int | None:
    if family != "bullets":
        return None

    style_overrides = case.get("style_overrides", {})
    bullets_overrides = style_overrides.get("bullets", {})
    expected_bullet_count = bullets_overrides.get("expected_bullet_count")
    return expected_bullet_count if isinstance(expected_bullet_count, int) else None


def load_evaluation_cases(cases_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("Evaluation cases file must contain a JSON list.")
    return payload


def resolve_case_document_path(document_path: str) -> Path:
    path = Path(document_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def build_output_instructions_for_family(
    family: str, version: str, max_words: int
) -> str:
    if family == "technical":
        return f"""
Return only valid JSON.
Do not use Markdown code fences.
Do not add text before or after the JSON.
Set "style" exactly to "technical".
Use exactly this structure:
{{
  "overview": "string",
  "key_technical_points": ["string"],
  "risks_or_limitations": ["string"],
  "style": "technical"
}}
Keep the combined text within {max_words} words.
""".strip()

    if family == "bullets":
        return f"""
Return only valid JSON.
Do not use Markdown code fences.
Do not add text before or after the JSON.
Set "style" exactly to "bullets".
Use exactly this structure:
{{
  "bullets": ["string"],
  "style": "bullets"
}}
Keep the combined text within {max_words} words.
""".strip()

    if family == "executive":
        return f"""
Return only valid JSON.
Do not use Markdown code fences.
Do not add text before or after the JSON.
Set "style" exactly to "executive".
Use exactly this structure:
{{
  "overview": "string",
  "key_technical_and_business_points": ["string"],
  "risks_limitations_or_missing_information": ["string"],
  "style": "executive"
}}
Keep the combined text within {max_words} words.
""".strip()

    raise ValueError(f"Unsupported family: {family}")


def build_bullet_count_row(version_results: list[EvaluationResult]) -> float:
    eligible_results = [
        result for result in version_results if result.bullet_count_correct is not None
    ]
    if not eligible_results:
        return 0.0

    return ratio_to_percent(
        sum(bool(result.bullet_count_correct) for result in eligible_results),
        len(eligible_results),
    )


def ratio_to_percent(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
