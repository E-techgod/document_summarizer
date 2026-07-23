from dataclasses import dataclass

from groq import Groq


@dataclass(frozen=True)
class SummarizationResult:
    """The model's reply plus the token usage reported by the provider."""
    text: str
    input_tokens: int | None
    output_tokens: int | None


def summarize_document(
    client: Groq,
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    temp: float = 0.0,
) -> SummarizationResult:

    if not system_prompt.strip():
        raise ValueError("System prompt cannot be empty")

    if not user_prompt.strip():
        raise ValueError("User prompt cannot be empty")

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temp,
    )

    summary = response.choices[0].message.content

    if not summary:
        raise ValueError("The model returned an empty response.")

    usage = getattr(response, "usage", None)

    return SummarizationResult(
        text=summary.strip(),
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
    )