import json
import os

from groq import Groq

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add GROQ_API_KEY=<your key> to .env "
                "(free key at https://console.groq.com/keys)."
            )
        _client = Groq(api_key=api_key)
    return _client


def generate_json(prompt: str, model: str = "openai/gpt-oss-120b") -> dict:
    """Ask Groq for a response and parse it as JSON. Raises on malformed output."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    text = response.choices[0].message.content.strip()
    return json.loads(text)
