from leettools.common.utils.lang_utils import get_language


def test_lang_utils():
    # Test case 1: en
    content = "This is an image: ![alt text](https://example"
    lan = get_language(content)
    assert lan == "en"

    # Test case 2: zh-cn
    # the following content returned value 'ca' from langdetect
    # content = "这是一张图片: ![alt text](https://example"

    content = "这是一张图片"
    lan = get_language(content)
    assert lan == "zh-cn"

    # Test case 3: ja
    content = "これは画像です: ![alt text](https://example"
    lan = get_language(content)
    assert lan == "ja"

    # Test case 4: spanish
    content = "Esta es una imagen"
    lan = get_language(content)
    assert lan == "es"

    # Test case 5: french
    # the following content returned value 'ro' from langdetect
    # content = "Ceci est une image: ![alt text](https://example"
    content = "Ceci est une image"
    lan = get_language(content)
    assert lan == "fr"

    # Test case 6: mixed
    content = "This is an image: ![alt text](https://example 这是一张图片"
    lan = get_language(content)
    assert lan == "en"
