import re


REASONING_TAG_RE = re.compile(
    r"<\s*(?P<closing>/?)\s*"
    r"(?P<tag>think|reasoning|analysis)\b[^>]*>",
    re.IGNORECASE,
)


def parse_think_setting(value):
    normalized = value.strip().casefold()

    if normalized in {"false", "0", "no", "off"}:
        return False

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"low", "medium", "high"}:
        return normalized

    raise ValueError(
        "OLLAMA_THINK must be true, false, low, medium, or high"
    )


def clean_model_response(text):
    clean_parts = []
    hidden_depth = 0
    cursor = 0

    for match in REASONING_TAG_RE.finditer(text):
        is_closing = bool(match.group("closing"))

        if hidden_depth == 0 and not is_closing:
            clean_parts.append(text[cursor:match.start()])

        if is_closing:
            if hidden_depth:
                hidden_depth -= 1
            else:
                # Some model templates omit the opening <think> tag but still
                # emit </think> between the reasoning trace and final answer.
                clean_parts.clear()
        else:
            hidden_depth += 1

        cursor = match.end()

    if hidden_depth == 0:
        clean_parts.append(text[cursor:])

    return "".join(clean_parts).strip()


def strip_nick_prefix(text, nick):
    prefix_re = re.compile(
        rf"^(?:\s*{re.escape(nick)}\s*[:,]\s*)+",
        re.IGNORECASE,
    )
    return "\n".join(
        prefix_re.sub("", line)
        for line in text.splitlines()
    ).strip()
