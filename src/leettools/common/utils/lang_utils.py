
import re


def is_chinese(text: str) -> bool:
    # Check if the string contains any Chinese characters
    return any('\u4e00' <= char <= '\u9fff' for char in text)

def is_english(text: str) -> bool:
    # Check if the string contains any Chinese characters
    if is_chinese(text):
        return False
    
    return bool(re.search(r'[a-zA-Z]', text))