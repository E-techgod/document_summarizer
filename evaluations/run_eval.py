import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from evaluation_runner import (
    FAMILIES,
    aggregate_results_by_family,
    load_evaluation_cases,
    run_evaluation_matrix,
)
from llm_client import create_client_groq

MODEL_NAME = "llama-3.1-8b-instant"
TEMPERATURE = 0.0
MAX_WORDS = 250
RUN_DATE = "2026-07-23"
CASES_PATH = PROJECT_ROOT / "evaluations" / "cases" / "evaluation_cases.json"
RESULTS_DIR = PROJECT_ROOT / "evaluations" / "results"


def main() -> None:
    cases = load_evaluation_cases(CASES_PATH)
    client = create_client_groq()
    results = run_evaluation_matrix(
        client=client,
        cases=cases,
        model_name=MODEL_NAME,
        temperature=TEMPERATURE,
        max_words=MAX_WORDS,
    )
    comparison_tables = aggregate_results_by_family(results)

    save_family_results(results, RUN_DATE)
    save_aggregation_tables(comparison_tables, RUN_DATE)
    print_aggregation_tables(comparison_tables)

    print(f"Completed {len(results)} evaluations.")


def save_family_results(results, run_date: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for family in FAMILIES:
        family_results = [
            result.model_dump() for result in results if result.family == family
        ]
        output_path = RESULTS_DIR / f"{family}_evaluation_{run_date}.json"
        output_path.write_text(json.dumps(family_results, indent=2), encoding="utf-8")


def save_aggregation_tables(comparison_tables, run_date: str) -> None:
    output_path = RESULTS_DIR / f"comparison_tables_{run_date}.json"
    output_path.write_text(json.dumps(comparison_tables, indent=2), encoding="utf-8")


def print_aggregation_tables(comparison_tables) -> None:
    for family in FAMILIES:
        print()
        print(f"{family.upper()} COMPARISON")
        print(format_markdown_table(comparison_tables[family]))


def format_markdown_table(rows) -> str:
    if not rows:
        return "(no results)"

    headers = list(rows[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_lines = []

    for row in rows:
        data_lines.append(
            "| " + " | ".join(str(row.get(header, "")) for header in headers) + " |"
        )

    return "\n".join([header_line, separator_line, *data_lines])


if __name__ == "__main__":
    main()
