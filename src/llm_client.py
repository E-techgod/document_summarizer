import os
from groq import Groq
from dotenv import load_dotenv

def load_client_groq() -> Groq:
    load_dotenv()

    groq_api_key= os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY was not found. Add it to your .env file")
    
    return Groq(groq_api_key)