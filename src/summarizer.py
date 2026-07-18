from urllib import response

from groq import Groq 

def summarize_document(client: Groq, system_promt: str, user_promt: str, model_name: str) -> str:

    if not system_promt.strip():
        raise ValueError("System prompt cannot be empty")
    
    if not user_promt.strip():
        raise ValueError("User prompt cannot be empty")
     
    response= client.chat.completions.create(
        model= model_name,

        messages=[
            {"role": "system", "content": system_promt},
            {"role": "user", "content": user_promt}
        ],

        temperature= 0.0
    )

    summary = response.choices[0].message.content

    if not summary:
        raise ValueError("The model returned an empty response.")
    
    return summary.strip()