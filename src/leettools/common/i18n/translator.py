import gettext
import os
import threading
from typing import Callable, Dict, Optional

from leettools.common.logging import logger
from leettools.common.singleton_meta import SingletonMeta

_script_dir = os.path.dirname(os.path.abspath(__file__))


class SingletonMetaTranslation(SingletonMeta):
    _lock: threading.Lock = threading.Lock()


class Translator(metaclass=SingletonMetaTranslation):
    def __init__(self):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            self.locales_dir = os.path.join(_script_dir, "locales")
            self.default_language = "en"
            self.translation_cache: Dict[str, gettext.NullTranslations] = {}

    def get_translator(self, lang: Optional[str] = None) -> Callable[[str], str]:
        if lang is None:
            lang = self.default_language

        if lang in self.translation_cache:
            logger().noop(f"Translator cache hit for language: {lang}", noop_lvl=4)
            return self.translation_cache[lang]

        locale_path = os.path.join(self.locales_dir, lang, "LC_MESSAGES", "messages.mo")
        if not os.path.exists(locale_path):
            logger().warning(
                f"Translation file not found for language: {lang}. "
                f"Using default language: {self.default_language}."
            )
            lang = self.default_language

        if lang not in self.translation_cache:
            logger().noop(f"Translator cache miss for language: {lang}", noop_lvl=3)
            translator: gettext.NullTranslations = gettext.translation(
                "messages",
                localedir=str(self.locales_dir),
                languages=[lang],
                fallback=True,
            )
            self.translation_cache[lang] = translator.gettext
            logger().noop(f"Translator cache set for language: {lang}", noop_lvl=3)
        else:
            logger().noop(f"Translator cache hit for language: {lang}", noop_lvl=3)

        return self.translation_cache[lang]


# Create a global _ function as a marker for the translator targets
def _(*args, **kwargs):
    # Get the default translator for intitial values
    translate = Translator().get_translator()
    return translate(*args, **kwargs)
