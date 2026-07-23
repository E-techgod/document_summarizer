import importlib
import json
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

if "groq" not in sys.modules:
    groq_stub = types.ModuleType("groq")
    groq_stub.Groq = type("Groq", (), {})
    sys.modules["groq"] = groq_stub


@pytest.fixture
def schema_module():
    return importlib.import_module("schema")


@pytest.fixture
def output_parser_module():
    return importlib.import_module("output_parser")


@pytest.fixture
def prompt_manager_module():
    return importlib.import_module("prompt_manager")


@pytest.fixture
def main_module():
    return importlib.import_module("main")


@pytest.fixture
def valid_summary_payload():
    return {
        "title": "API Integration Summary",
        "style": "bullets",
        "version": "v2",
        "overview": "This document explains how the integration works.",
        "key_points": [
            "Requests are authenticated with an API key.",
            "Responses are returned as structured JSON.",
        ],
        "risks_or_limitations": [
            "Rate limiting may affect throughput.",
        ],
    }


@pytest.fixture
def valid_summary_json(valid_summary_payload):
    return json.dumps(valid_summary_payload)


@pytest.fixture
def invalid_json_response():
    return '{"title": "Broken", "style": "bullets"'


@pytest.fixture
def empty_response():
    return "   "


@pytest.fixture
def wrong_style_payload(valid_summary_payload):
    payload = dict(valid_summary_payload)
    payload["style"] = "technical"
    return payload


@pytest.fixture
def oversized_summary_payload(valid_summary_payload):
    payload = dict(valid_summary_payload)
    payload["overview"] = " ".join(["word"] * 251)
    payload["key_points"] = ["A required key point."]
    payload["risks_or_limitations"] = []
    return payload


def test_summary_output_accepts_valid_payload(schema_module, valid_summary_payload):
    summary = schema_module.SummaryOutput.model_validate(valid_summary_payload)

    assert summary.title == valid_summary_payload["title"]
    assert summary.style == "bullets"
    assert summary.key_points == valid_summary_payload["key_points"]


def test_summary_output_rejects_extra_fields(schema_module, valid_summary_payload):
    invalid_payload = dict(valid_summary_payload)
    invalid_payload["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        schema_module.SummaryOutput.model_validate(invalid_payload)


def test_summary_output_rejects_missing_required_fields(
    schema_module, valid_summary_payload
):
    invalid_payload = dict(valid_summary_payload)
    invalid_payload.pop("overview")

    with pytest.raises(ValidationError):
        schema_module.SummaryOutput.model_validate(invalid_payload)


def test_parse_summary_response_returns_summary_model(
    output_parser_module, valid_summary_json
):
    summary = output_parser_module.SummaryParsingError.parse_summary_response(
        valid_summary_json
    )

    assert summary.title == "API Integration Summary"
    assert summary.style == "bullets"


def test_parse_summary_response_raises_for_empty_llm_response(
    output_parser_module, empty_response
):
    with pytest.raises(
        output_parser_module.SummaryParsingError, match="empty response"
    ):
        output_parser_module.SummaryParsingError.parse_summary_response(empty_response)


def test_parse_summary_response_raises_for_malformed_json(
    output_parser_module, invalid_json_response
):
    with pytest.raises(output_parser_module.SummaryParsingError, match="invalid json"):
        output_parser_module.SummaryParsingError.parse_summary_response(
            invalid_json_response
        )


def test_parse_summary_response_raises_for_schema_validation_failures(
    output_parser_module, valid_summary_payload
):
    invalid_payload = dict(valid_summary_payload)
    invalid_payload["key_points"] = ""

    with pytest.raises(
        output_parser_module.SummaryParsingError, match="schema validation"
    ):
        output_parser_module.SummaryParsingError.parse_summary_response(
            json.dumps(invalid_payload)
        )


def test_validate_request_style_passes_for_matching_style(
    output_parser_module, schema_module, valid_summary_payload
):
    summary = schema_module.SummaryOutput.model_validate(valid_summary_payload)

    output_parser_module.validate_request_style(summary, "bullets")


def test_validate_request_style_raises_for_wrong_style(
    output_parser_module, schema_module, wrong_style_payload
):
    summary = schema_module.SummaryOutput.model_validate(wrong_style_payload)

    with pytest.raises(ValueError, match="wrong summary style"):
        output_parser_module.validate_request_style(summary, "bullets")


def test_validate_max_words_passes_when_within_limit(
    output_parser_module, schema_module, valid_summary_payload
):
    summary = schema_module.SummaryOutput.model_validate(valid_summary_payload)

    output_parser_module.validate_max_words(summary, 100)


def test_validate_max_words_raises_when_summary_exceeds_limit(
    output_parser_module, schema_module, oversized_summary_payload
):
    summary = schema_module.SummaryOutput.model_validate(oversized_summary_payload)

    with pytest.raises(ValueError, match="maximum allowed"):
        output_parser_module.validate_max_words(summary, 250)


def test_count_summary_words_counts_only_meaningful_sections(
    output_parser_module, schema_module, valid_summary_payload
):
    summary = schema_module.SummaryOutput.model_validate(valid_summary_payload)

    word_count = output_parser_module.count_summary_words(summary)

    expected = len(
        (
            valid_summary_payload["overview"]
            + " "
            + " ".join(valid_summary_payload["key_points"])
            + " "
            + " ".join(valid_summary_payload["risks_or_limitations"])
        ).split()
    )
    assert word_count == expected


def test_build_summary_output_path_groups_files_by_version(main_module):
    output_path = main_module.build_summary_output_path("bullets", "v2")

    assert output_path == (
        PROJECT_ROOT / "summary_output_json" / "v2" / "bullets_v2_summary.json"
    )


def test_build_user_prompt_renders_all_required_inputs(prompt_manager_module):
    template = (
        "STYLE={{ style }}\n"
        "MAX={{ max_words }}\n"
        "{{ output_instructions }}\n"
        "DOC={{ document_text }}"
    )

    prompt = prompt_manager_module.build_user_prompt(
        user_template=template,
        document_text="Important source text.",
        style="bullets",
        version="v2",
        max_words=250,
        output_instructions='{"style": "{{ style }}", "version": "{{ version }}", "limit": {{ max_words }}}',
    )

    assert "STYLE=bullets" in prompt
    assert "MAX=250" in prompt
    assert "DOC=Important source text." in prompt
    assert '"style": "bullets"' in prompt
    assert '"version": "v2"' in prompt
    assert '"limit": 250' in prompt
    assert "{{" not in prompt
    assert "}}" not in prompt


def test_build_user_prompt_strips_document_edges(prompt_manager_module):
    prompt = prompt_manager_module.build_user_prompt(
        user_template="DOC={{ document_text }}",
        document_text="  text with padding  ",
        style="bullets",
        version="v2",
        max_words=250,
        output_instructions="ignored",
    )

    assert prompt == "DOC=text with padding"


@pytest.mark.parametrize("style", ["bullets", "executive", "technical"])
def test_real_prompt_templates_include_rendered_json_output_instructions(
    prompt_manager_module, style
):
    user_template = prompt_manager_module.load_prompt_user_template(style, "v1")

    prompt = prompt_manager_module.build_user_prompt(
        user_template=user_template,
        document_text="Source material.",
        style=style,
        version="v1",
        max_words=250,
        output_instructions='{"style": "{{ style }}", "version": "{{ version }}", "limit": {{ max_words }}}',
    )

    assert '"style": "' + style + '"' in prompt
    assert '"version": "v1"' in prompt
    assert '"limit": 250' in prompt
    assert "{{ output_instructions }}" not in prompt
    assert "{{ style }}" not in prompt


def test_build_user_prompt_propagates_render_failures(
    prompt_manager_module, monkeypatch
):
    def broken_renderer(*_args, **_kwargs):
        raise ValueError("output instructions failed")

    monkeypatch.setattr(
        prompt_manager_module, "render_output_instructions", broken_renderer
    )

    with pytest.raises(ValueError, match="output instructions failed"):
        prompt_manager_module.build_user_prompt(
            user_template="DOC={{ document_text }}",
            document_text="payload",
            style="bullets",
            version="v2",
            max_words=250,
            output_instructions="unused",
        )


def test_parse_summary_response_extracts_json_after_thinking_block(
    output_parser_module,
):
    response = """
<thinking>
- Fact 1
- Fact 2
</thinking>
{
  "title": "Parsed Summary",
  "style": "bullets",
  "version": "v2",
  "overview": "Overview text.",
  "key_points": ["Point A", "Point B"],
  "risks_or_limitations": ["Risk A"]
}
"""

    summary = output_parser_module.SummaryParsingError.parse_summary_response(
        response,
        requested_style="bullets",
        requested_version="v2",
    )

    assert summary.title == "Parsed Summary"
    assert summary.version == "v2"


def test_parse_summary_response_normalizes_prompt_specific_shape(output_parser_module):
    response = json.dumps(
        {
            "overview": "PaymentsAPI v2.3 adds mandatory idempotency keys.",
            "key_technical_points": [
                "Idempotency key required on POST /charges as of v2.3",
                "Missing key returns HTTP 400",
            ],
            "risks_or_limitations": [
                "Migration guide not yet published",
            ],
            "style": "technical",
        }
    )

    summary = output_parser_module.SummaryParsingError.parse_summary_response(
        response,
        requested_style="technical",
        requested_version="v3",
        example_output_keys=(
            "overview",
            "key_technical_points",
            "risks_or_limitations",
            "style",
        ),
    )

    assert summary.style == "technical"
    assert summary.version == "v3"
    assert summary.key_points == [
        "Idempotency key required on POST /charges as of v2.3",
        "Missing key returns HTTP 400",
    ]
    assert summary.risks_or_limitations == ["Migration guide not yet published"]


def test_write_summary_json_persists_validated_payload(
    main_module, valid_summary_payload, tmp_path
):
    summary = importlib.import_module("schema").SummaryOutput.model_validate(
        valid_summary_payload
    )
    output_path = tmp_path / "summaries" / "sample_summary.json"

    written_path = main_module.write_summary_json(summary, output_path)

    assert written_path == output_path
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == valid_summary_payload


def test_build_summary_output_path_uses_style_name(main_module):
    output_path = main_module.build_summary_output_path("executive", "v2")

    assert output_path == (
        main_module.PROJECT_DIRECTORY
        / "summary_output_json"
        / "v2"
        / "executive_v2_summary.json"
    )


def test_get_prompt_version_reads_version_from_template_filename(main_module):
    assert main_module.get_prompt_version("technical", "v3") == "v3"


def test_load_prompt_user_template_uses_requested_version(prompt_manager_module):
    prompt = prompt_manager_module.load_prompt_user_template("technical", "v2")

    assert 'The requested summary format identifier is "{{ style }}".' in prompt
    assert (
        "USE THIS WHEN: Your audience is a technical engineer who need the technical version"
        in prompt
    )


def test_load_prompt_user_template_rejects_unsupported_version(prompt_manager_module):
    with pytest.raises(ValueError, match="Unsupported prompt version"):
        prompt_manager_module.load_prompt_user_template("technical", "v9")


def test_main_runs_complete_workflow_with_mocked_dependencies(
    main_module, monkeypatch, valid_summary_payload, capsys
):
    summary = importlib.import_module("schema").SummaryOutput.model_validate(
        valid_summary_payload
    )
    calls = []

    monkeypatch.setattr(
        main_module,
        "load_and_validate_document",
        lambda path: calls.append(("document", path)) or "Loaded document",
    )
    monkeypatch.setattr(
        main_module,
        "load_prompt_user_template",
        lambda style, version: calls.append(("template", style, version))
        or "Prompt {{ document_text }}",
    )
    monkeypatch.setattr(
        main_module,
        "build_prompt_contract",
        lambda user_template, document_text, style, version, max_words, output_instructions: calls.append(
            (
                "prompt",
                user_template,
                document_text,
                style,
                version,
                max_words,
                output_instructions,
            )
        )
        or types.SimpleNamespace(
            rendered_prompt="Rendered prompt", example_output_keys=("title", "style")
        ),
    )
    monkeypatch.setattr(
        main_module,
        "load_system_prompr",
        lambda: calls.append(("system",)) or "System prompt",
    )
    monkeypatch.setattr(
        main_module, "create_client_groq", lambda: calls.append(("client",)) or object()
    )
    monkeypatch.setattr(
        main_module,
        "summarize_document",
        lambda client, system_prompt, user_prompt, model_name, temp=0.0: calls.append(
            ("summarize", system_prompt, user_prompt, model_name)
        )
        or types.SimpleNamespace(
            text='{"title":"unused"}', input_tokens=None, output_tokens=None
        ),
    )
    monkeypatch.setattr(
        main_module.SummaryParsingError,
        "parse_summary_response",
        staticmethod(
            lambda response, requested_style=None, requested_version=None, example_output_keys=(): calls.append(
                (
                    "parse",
                    response,
                    requested_style,
                    requested_version,
                    example_output_keys,
                )
            )
            or summary
        ),
    )
    monkeypatch.setattr(
        main_module,
        "validate_request_style",
        lambda parsed_summary, requested_style: calls.append(
            ("style", parsed_summary.style, requested_style)
        ),
    )
    monkeypatch.setattr(
        main_module,
        "validate_max_words",
        lambda parsed_summary, max_words: calls.append(("words", max_words)),
    )
    monkeypatch.setattr(main_module, "count_summary_words", lambda parsed_summary: 9)
    monkeypatch.setattr(
        main_module,
        "write_summary_json",
        lambda parsed_summary, output_path: calls.append(
            ("write", parsed_summary.title, output_path)
        )
        or output_path,
    )

    main_module.main()

    stdout = capsys.readouterr().out
    assert "RENDERED USER PROMPT" in stdout
    assert "VALIDATED SUMMARY" in stdout
    assert "Summary JSON saved to:" in stdout
    assert '"style": "bullets"' in stdout
    assert "Word count: 9" in stdout
    assert [call[0] for call in calls] == [
        "document",
        "template",
        "prompt",
        "system",
        "client",
        "summarize",
        "parse",
        "style",
        "words",
        "write",
    ]


def test_main_stops_after_document_loading_failure(main_module, monkeypatch):
    downstream_calls = []

    monkeypatch.setattr(
        main_module,
        "load_and_validate_document",
        lambda path: (_ for _ in ()).throw(FileNotFoundError("missing document")),
    )
    monkeypatch.setattr(
        main_module,
        "load_prompt_user_template",
        lambda style, version: downstream_calls.append("template"),
    )
    monkeypatch.setattr(
        main_module,
        "build_prompt_contract",
        lambda *args, **kwargs: downstream_calls.append("prompt"),
    )
    monkeypatch.setattr(
        main_module, "load_system_prompr", lambda: downstream_calls.append("system")
    )
    monkeypatch.setattr(
        main_module, "create_client_groq", lambda: downstream_calls.append("client")
    )

    with pytest.raises(FileNotFoundError, match="missing document"):
        main_module.main()

    assert downstream_calls == []


def test_main_propagates_prompt_rendering_value_error(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module, "load_and_validate_document", lambda path: "Loaded document"
    )
    monkeypatch.setattr(
        main_module,
        "load_prompt_user_template",
        lambda style, version: "Prompt template",
    )
    monkeypatch.setattr(
        main_module,
        "build_prompt_contract",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("render failed")),
    )

    with pytest.raises(ValueError, match="render failed"):
        main_module.main()


def test_main_propagates_summary_parsing_error(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module, "load_and_validate_document", lambda path: "Loaded document"
    )
    monkeypatch.setattr(
        main_module,
        "load_prompt_user_template",
        lambda style, version: "Prompt template",
    )
    monkeypatch.setattr(
        main_module,
        "build_prompt_contract",
        lambda *args, **kwargs: types.SimpleNamespace(
            rendered_prompt="Rendered prompt", example_output_keys=()
        ),
    )
    monkeypatch.setattr(main_module, "load_system_prompr", lambda: "System prompt")
    monkeypatch.setattr(main_module, "create_client_groq", lambda: object())
    monkeypatch.setattr(
        main_module,
        "summarize_document",
        lambda *args, **kwargs: types.SimpleNamespace(
            text="not json", input_tokens=None, output_tokens=None
        ),
    )
    monkeypatch.setattr(
        main_module.SummaryParsingError,
        "parse_summary_response",
        staticmethod(
            lambda response, **kwargs: (_ for _ in ()).throw(
                main_module.SummaryParsingError("invalid response")
            )
        ),
    )

    with pytest.raises(main_module.SummaryParsingError, match="invalid response"):
        main_module.main()


def test_main_does_not_write_json_when_style_validation_fails(
    main_module, monkeypatch, valid_summary_payload
):
    summary = importlib.import_module("schema").SummaryOutput.model_validate(
        valid_summary_payload
    )
    write_calls = []

    monkeypatch.setattr(
        main_module, "load_and_validate_document", lambda path: "Loaded document"
    )
    monkeypatch.setattr(
        main_module,
        "load_prompt_user_template",
        lambda style, version: "Prompt template",
    )
    monkeypatch.setattr(
        main_module,
        "build_prompt_contract",
        lambda *args, **kwargs: types.SimpleNamespace(
            rendered_prompt="Rendered prompt", example_output_keys=()
        ),
    )
    monkeypatch.setattr(main_module, "load_system_prompr", lambda: "System prompt")
    monkeypatch.setattr(main_module, "create_client_groq", lambda: object())
    monkeypatch.setattr(
        main_module,
        "summarize_document",
        lambda *args, **kwargs: types.SimpleNamespace(
            text='{"title":"unused"}', input_tokens=None, output_tokens=None
        ),
    )
    monkeypatch.setattr(
        main_module.SummaryParsingError,
        "parse_summary_response",
        staticmethod(lambda response, **kwargs: summary),
    )
    monkeypatch.setattr(
        main_module,
        "validate_request_style",
        lambda parsed_summary, requested_style: (_ for _ in ()).throw(
            ValueError("wrong style")
        ),
    )
    monkeypatch.setattr(
        main_module,
        "write_summary_json",
        lambda parsed_summary, output_path: write_calls.append(output_path),
    )

    with pytest.raises(ValueError, match="wrong style"):
        main_module.main()

    assert write_calls == []
