def evaluate_json_validity(response_text: str) -> bool:
    try:
        json.loads(response_text)
        return True
    except json.JSONDecodeError:
        return False
    try:
        summary = SummaryOutput.model_validate_json(response_text)
        valid_schema = True
    except ValidationError:
        valid_schema = False
