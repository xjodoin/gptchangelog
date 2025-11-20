from functools import lru_cache
from typing import Any, List

from openai import OpenAI


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """
    Lazily instantiate and cache a singleton OpenAI client.
    The client automatically reads credentials from environment variables.
    """
    return OpenAI()


def _collect_text_from_output(output_items: Any) -> List[str]:
    texts: List[str] = []
    if not output_items:
        return texts

    for item in output_items:
        content_list = getattr(item, "content", None)
        if content_list is None and isinstance(item, dict):
            content_list = item.get("content")

        if not content_list:
            continue

        for content in content_list:
            text_obj = getattr(content, "text", None)
            if text_obj and hasattr(text_obj, "value") and text_obj.value:
                texts.append(text_obj.value)
                continue

            if isinstance(content, dict):
                text_data = content.get("text")
                if isinstance(text_data, dict) and text_data.get("value"):
                    texts.append(text_data["value"])
                    continue

                for key in ("value", "content", "text"):
                    value = content.get(key)
                    if isinstance(value, str):
                        texts.append(value)
                        break

    return texts


def extract_response_text(response: Any) -> str:
    """
    Normalize a Responses API payload into a plain text string.
    Falls back to stringifying the payload if no structured text is present.
    """
    if response is None:
        return ""

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text.strip()
    if isinstance(output_text, list):
        joined = "\n".join(part for part in output_text if isinstance(part, str))
        if joined.strip():
            return joined.strip()

    texts = _collect_text_from_output(getattr(response, "output", None))
    if texts:
        return "\n".join(texts).strip()

    if hasattr(response, "model_dump"):
        payload = response.model_dump()
        texts = _collect_text_from_output(payload.get("output"))  # type: ignore[arg-type]
        if texts:
            return "\n".join(texts).strip()

    return str(response).strip()
