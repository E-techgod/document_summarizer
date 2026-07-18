import os
from groq import Groq
from dotenv import load_dotenv

def create_client_groq() -> Groq:
    load_dotenv()

    groq_api_key= os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY was not found. Add it to your .env file")
    
    return Groq(api_key=groq_api_key)