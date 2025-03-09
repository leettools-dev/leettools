import os

from leettools.common.i18n.translator import Translator, _


def test_translator_singleton():
    """Test that Translator maintains singleton pattern"""
    translator1 = Translator()
    translator2 = Translator()
    assert translator1 is translator2


def test_get_translator_default():
    """Test get_translator returns default language translator when no language specified"""
    translator = Translator()
    translate_func = translator.get_translator()
    assert callable(translate_func)
    # Default language should be 'en'
    assert translator.default_language == "en"


def test_get_translator_caching():
    """Test that translators are properly cached"""
    translator = Translator()

    # Get translator for 'en' twice
    translator1 = translator.get_translator("en")
    translator2 = translator.get_translator("en")

    # Should return the exact same function object (cached)
    assert translator1 is translator2
    assert "en" in translator.translation_cache


def test_get_translator_fallback():
    """Test fallback to default language for non-existent language"""
    translator = Translator()

    # Request non-existent language
    translate_func = translator.get_translator("non-existent-lang")
    assert callable(translate_func)
    # Should fall back to default language
    assert "en" in translator.translation_cache


def test_global_underscore_function():
    """Test the global _ function works"""
    # The global _ function should return a callable
    assert callable(_)
    # Should be able to translate strings
    result = _("test_string")
    assert isinstance(result, str)


def test_translator_with_different_languages():
    """Test translator with different languages"""
    translator = Translator()

    en_translator = translator.get_translator("en")
    # Get another language if available, otherwise use 'en' again for testing
    other_lang = (
        "es" if os.path.exists(os.path.join(translator.locales_dir, "es")) else "en"
    )
    other_translator = translator.get_translator(other_lang)

    assert callable(en_translator)
    assert callable(other_translator)

    # If using same language, should be same function object
    if other_lang == "en":
        assert en_translator is other_translator
    else:
        assert en_translator is not other_translator


def test_translator_none_language():
    """Test translator behavior when None is passed as language"""
    translator = Translator()
    translate_func = translator.get_translator(None)
    assert callable(translate_func)
    assert "en" in translator.translation_cache  # Should use default language


def test_translation_cache_initialization():
    """Test that translation cache is properly initialized"""
    translator = Translator()
    assert hasattr(translator, "translation_cache")
    assert isinstance(translator.translation_cache, dict)
    assert len(translator.translation_cache) == 1  # start with the default language


def test_locales_directory_structure():
    """Test that the locales directory structure is correct"""
    translator = Translator()
    assert os.path.exists(translator.locales_dir)
    # Check if at least the default language directory exists
    default_lang_path = os.path.join(
        translator.locales_dir, translator.default_language
    )
    assert os.path.exists(default_lang_path)
