from typing import List, Optional

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.settings import SystemSettings


class Tokenizer:
    def __init__(self, settings: SystemSettings):
        self.settings = settings

    def token_count(self, text: str, model_name: Optional[str] = None) -> int:
        if model_name is None:
            model_name = self.settings.DEFAULT_INFERENCE_MODEL

        if model_name.startswith("gpt") or model_name.startswith("o1"):
            import tiktoken

            encoding = tiktoken.encoding_for_model(model_name)
            return len(encoding.encode(text))
        elif model_name.startswith("qwen"):
            # The tokenizer from Qwen models is really slow, so we don't use it now:
            # from dashscope import get_tokenizer
            # tokenizer = get_tokenizer(model_name)
            return len(text)
        elif model_name.startswith("deepseek"):
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-V3")
            tokens = tokenizer.tokenize(text)
            return len(tokens)
            # return len(text)
        elif model_name.startswith("llama"):
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained("unsloth/Llama-3.2-3B")
            tokens = tokenizer.tokenize(text)
            return len(tokens)
        else:
            logger().warning(
                f"Unknown model name: {model_name}, using text length as token count."
            )
            return len(text)

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
    print(tokenizer.token_count(text, "gpt-4o-mini"))

    text = "This is a test sentence; This is another test sentence."
    num_parts = 2
    parts = Tokenizer.split_text(text, num_parts)
    for part in parts:
        print(part)
