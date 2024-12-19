import secrets
import string


def compute_checksum(first_9_chars: str) -> str:
    """Compute the 10th character based on the first 9 characters."""
    # For example, we can sum the ASCII values of the first 9 chars and compute mod 36
    # to get a character from the alphanumeric set (0-9, a-z).
    checksum_value = sum(ord(c) for c in first_9_chars) % 36
    if checksum_value < 10:
        # If the value is less than 10, return a digit
        return str(checksum_value)
    else:
        # Otherwise, return a lowercase letter
        return chr(checksum_value - 10 + ord("a"))


def generate_api_key(prefix: str = "leet", random_length: int = 54) -> str:
    """Generates an API key with a predefined prefix and a custom 10-character second prefix."""
    alphabet = string.ascii_letters + string.digits  # Letters and digits

    # Generate the first 9 characters for the second prefix
    first_9_chars = "".join(secrets.choice(alphabet) for _ in range(9))

    # Compute the 10th character as a checksum based on the first 9 characters
    checksum_char = compute_checksum(first_9_chars)

    # Second prefix consists of the first 9 random chars and the checksum char
    second_prefix = first_9_chars + checksum_char

    # Generate the remaining random characters to make the total length 64
    remaining_chars = "".join(secrets.choice(alphabet) for _ in range(random_length))

    # Combine all parts to form the full API key
    api_key = f"{prefix}-{second_prefix}-{remaining_chars}"

    return api_key
