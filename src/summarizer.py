from groq import Groq

def summarize_document(
    client: Groq,
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    temp: float = 0.0,
) -> str:

    if not system_prompt.strip():
        raise ValueError("System prompt cannot be empty")
    
    if not user_prompt.strip():
        raise ValueError("User prompt cannot be empty")
     
    response= client.chat.completions.create(
        model= model_name,

        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],

        temperature = temp
    )

    summary = response.choices[0].message.content # Raw API/Modle call 

    if not summary:
        raise ValueError("The model returned an empty response.")
    
    return summary.strip()
