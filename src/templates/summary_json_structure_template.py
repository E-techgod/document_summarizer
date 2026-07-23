JSON_OUTPUT_INSTRUCTIONS = """
Return only valid JSON.

Do not use Markdown code fences.
Do not add text before or after the JSON.
The "style" field is the summary format identifier, not the audience or tone.
Set "style" exactly to "{{ style }}". Do not use values like "casual", "beginner", or "technical tone".
Set "version" exactly to "{{ version }}".

Use exactly this structure:

{
  "title": "string",
  "style": "{{ style }}",
  "version": "{{ version }}",
  "overview": "string",
  "key_points": ["string"],
  "risks_or_limitations": ["string"]
}

The combined text in overview, key_points, and risks_or_limitations
must contain no more than {{ max_words }} words.
"""
