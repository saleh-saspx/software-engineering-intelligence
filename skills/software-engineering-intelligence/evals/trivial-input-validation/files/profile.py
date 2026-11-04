"""User profile helpers."""


def parse_age(value: str) -> int:
    """Parse an age entered in the signup form."""
    age = int(value.strip())
    if age > 150:
        raise ValueError(f"age out of range: {age}")
    return age


def display_name(first: str, last: str) -> str:
    return f"{first.strip()} {last.strip()}".strip()
