import re


def is_html(text: str) -> bool:
    return bool(re.search(r"<[a-zA-Z][^>]*>", text))
