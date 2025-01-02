import re
from typing import Optional

from leettools.common.logging import logger


def get_language(text: str) -> Optional[str]:
    """
    Detect the language of the given text.

    Currently use with caution since the results are not reliable. For example, if user
    already specified a search language, just use an extra inference step to translate
    the text to target language.

    Args:
    - text: The text to detect the language of.

    Returns:
    - The language code of the detected language, or None if the language could
        not be detected.
    """
    try:
        from langdetect import detect

        lan = detect(text)
        return lan
    except Exception as e:
        logger().error(f"Error detecting language for text {text}: {e}")
        return None


def normalize_lang_name(lang: str) -> str:
    if not lang:
        logger().warning(
            f"Specified lang is empty or null. Return the same value [{lang}]."
        )
        return lang

    lang = lang.lower()
    if lang == "en" or lang == "en-us" or lang == "english":
        lang = "English"
    elif lang == "zh" or lang == "zh-cn" or lang == "cn" or lang == "chinese":
        lang = "Chinese"
    elif lang == "es" or lang == "es-es" or lang == "spanish":
        lang = "Spanish"
    elif lang == "fr" or lang == "fr-fr" or lang == "french":
        lang = "French"
    elif lang == "de" or lang == "de-de" or lang == "german":
        lang = "German"
    elif lang == "it" or lang == "it-it" or lang == "italian":
        lang = "Italian"
    elif lang == "ja" or lang == "ja-jp" or lang == "japanese":
        lang = "Japanese"
    else:
        logger().warning(f"Unsupported language: {lang}. Use its original form.")
    return lang
