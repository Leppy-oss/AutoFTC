import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
system_prompt = os.getenv("SYSTEM_PROMPT")

client = Groq()
completion = client.chat.completions.create(
    model="meta-llama/llama-4-scout17b-16e-instruct",
    messages=[
        {
            "role": "system",
            "content": system_prompt
        }
    ]
)