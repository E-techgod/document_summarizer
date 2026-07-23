from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from evaluation_runner import load_evaluation_cases, run_evaluation_matrix
from llm_client import create_client_groq


MODEL_NAME = "llama-3.1-8b-instant"
TEMPERATURE = 0.0
MAX_WORDS = 250
CASES_PATH = PROJECT_ROOT / "evaluations" / "cases" / "evaluation_cases.json"


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

    print(f"Completed {len(results)} evaluations.")


if __name__ == "__main__":
    main()
