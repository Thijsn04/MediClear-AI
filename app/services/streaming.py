"""
Progressive extraction of the ``explanation`` string from streaming JSON.

When a provider streams an analysis, the bytes arrive as a growing JSON object.
This helper watches the accumulating text and yields the newly available portion
of the ``explanation`` field, so the UI can render a live, human-readable stream
without waiting for the whole structured object to finish. It decodes the common
JSON string escapes and stops cleanly at the closing quote.
"""

from __future__ import annotations

_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}


class ExplanationStreamExtractor:
    """Feed accumulated text; get back newly decoded explanation characters."""

    def __init__(self, field: str = "explanation") -> None:
        self._needle = f'"{field}"'
        self._emitted = ""  # decoded explanation text emitted so far
        self._done = False

    @property
    def done(self) -> bool:
        return self._done

    def feed(self, accumulated: str) -> str:
        """Return the newly decodable explanation text since the last call."""
        if self._done:
            return ""
        decoded, done = self._decode(accumulated)
        self._done = done
        if len(decoded) <= len(self._emitted):
            return ""
        delta = decoded[len(self._emitted) :]
        self._emitted = decoded
        return delta

    def _decode(self, text: str) -> tuple[str, bool]:
        """Decode the explanation string value from ``text``; (value, complete)."""
        key_pos = text.find(self._needle)
        if key_pos == -1:
            return "", False
        # Find the ':' then the opening quote of the value.
        colon = text.find(":", key_pos + len(self._needle))
        if colon == -1:
            return "", False
        i = colon + 1
        while i < len(text) and text[i] in " \t\r\n":
            i += 1
        if i >= len(text) or text[i] != '"':
            return "", False
        i += 1  # past opening quote

        out: list[str] = []
        while i < len(text):
            ch = text[i]
            if ch == "\\":
                if i + 1 >= len(text):
                    break  # escape not fully arrived yet
                nxt = text[i + 1]
                if nxt == "u":
                    if i + 6 > len(text):
                        break  # unicode escape incomplete
                    try:
                        out.append(chr(int(text[i + 2 : i + 6], 16)))
                    except ValueError:
                        out.append(text[i + 2 : i + 6])
                    i += 6
                    continue
                out.append(_ESCAPES.get(nxt, nxt))
                i += 2
                continue
            if ch == '"':
                return "".join(out), True  # closing quote reached
            out.append(ch)
            i += 1
        return "".join(out), False
