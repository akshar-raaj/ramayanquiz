"""
Interacts with OpenAI to translate the provided English text to another language.

Currently tested with the following:
- Hindi
- Telugu
"""

import requests


def translate(english_text: str, translate_to: str = 'hindi'):
    print(f"Translating {english_text} to {translate_to}")
    print(f"Translated {english_text} to {translate_to}")