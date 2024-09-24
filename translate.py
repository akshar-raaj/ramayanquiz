"""
Interacts with OpenAI to translate the provided English text to another language.

Currently tested with the following:
- Hindi
- Telugu
"""

from openai import OpenAI
from constants import CHATGPT_MODEL


def translate(english_text: str, translate_to: str = 'Hindi'):
    print(f"Translating {english_text} to {translate_to}")
    client = OpenAI()
    try:
        completion = client.chat.completions.create(
            model=CHATGPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"Translate the following text to {translate_to}: {english_text}"
                }
            ]
        )
    except Exception:
        print("Error in making request to OpenAI")
        return
    try:
        content = completion.choices[0].message.content
        return content
    except Exception:
        print("Error in parsing OpenAI result")
        return
    print(f"Translated {english_text} to {translate_to}")
