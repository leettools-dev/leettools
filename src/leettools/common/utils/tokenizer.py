from typing import List

from leettools.common import exceptions
from leettools.settings import SystemSettings


class Tokenizer:
    def __init__(self, settings: SystemSettings):
        self.settings = settings

    def est_token_count(self, text: str) -> int:
        """
        Estimate the token count of the text, since we do not want to import
        transformers in the common module.
        """
        import tiktoken

        # We use gpt-3.5 as the default model for estimating the token count
        model_name = "gpt-3.5"
        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding.encode(text))

    def split_text(self, text: str, num_parts: int) -> List[str]:
        words = text.split()  # Split the text into words
        if num_parts > len(words):
            raise exceptions.UnexpectedCaseException(
                f"Number of parts exceeds the number of words in the text: {num_parts} > {len(words)}.\n"
                f"{text}\n"
            )

        # Calculate the base size of each part
        part_size = len(words) // num_parts
        # Calculate how many parts need an extra word
        larger_parts = len(words) % num_parts

        parts = []
        index = 0
        for i in range(num_parts):
            # Each part will have the base size plus one extra word if needed
            current_part_size = part_size + (1 if i < larger_parts else 0)
            # Append the current part to the list
            parts.append(" ".join(words[index : index + current_part_size]))
            # Update the index to the start of the next part
            index += current_part_size

        return parts


if __name__ == "__main__":
    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()  # type: Context

    tokenizer = Tokenizer(context.settings)
    text = "This is a test sentence."
    print(tokenizer.est_token_count(text))

    text = "This is a test sentence; This is another test sentence."
    num_parts = 2
    parts = tokenizer.split_text(text, num_parts)
    for part in parts:
        print(part)
