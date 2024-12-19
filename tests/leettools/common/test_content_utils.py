from leettools.common.utils.content_utils import get_image_url


def test_get_image_url():
    # Test case 1: Valid image URL
    content = "This is an image: ![alt text](https://example.com/image.jpg)"
    expected_url = "https://example.com/image.jpg"
    assert get_image_url(content) == expected_url

    # Test case 2: No image URL
    content = "This is some text without an image URL"
    assert get_image_url(content) is None

    # Test case 3: Multiple image URLs, return the first one
    content = "This is an image: ![alt text](https://example.com/image1.jpg) and another image: ![alt text](https://example.com/image2.jpg)"
    expected_url = "https://example.com/image1.jpg"
    assert get_image_url(content) == expected_url

    # Test case 4: Case-insensitive matching
    content = "This is an image: ![alt text](https://example.com/IMAGE.jpg)"
    expected_url = "https://example.com/IMAGE.jpg"
    assert get_image_url(content) == expected_url

    # Test case 5: No content
    content = ""
    assert get_image_url(content) is None

    # Test case 6: No image URL, but other URLs present
    content = "This is a URL: https://example.com"
    assert get_image_url(content) is None

    # Test case 4: Case-insensitive matching
    content = "This is an image: ![alt text](IMAGE.jpg)"
    expected_url = "IMAGE.jpg"
    assert get_image_url(content) == expected_url
