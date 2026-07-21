JSON_OUTPUT_INSTRUCTIONS = """
Return only valid JSON.

Do not use Markdown code fences.
Do not add text before or after the JSON.

Use exactly this structure:

{
  "title": "string",
  "style": "{{ style }}",
  "overview": "string",
  "key_points": ["string"],
  "risks_or_limitations": ["string"]
}

The combined text in overview, key_points, and risks_or_limitations
must contain no more than {{ max_words }} words.
"""
