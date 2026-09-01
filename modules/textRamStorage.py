"""
Text RAM Storage Module

In-memory storage for extracted document text.
Replaces the old approach of writing text to a temporary file on disk.

Used by DocumentToText to hold the full extracted text and serve
chunks on demand without file I/O overhead.
"""


class TextRamStorage:
    def __init__(self):
        self._text = ""

    def write(self, text):
        """Store the full text content."""
        self._text = text

    def read(self):
        """Return the full text content."""
        return self._text

    def consume_chunk(self, max_chars=1000):
        """
        Extract a chunk of up to max_chars from the front of the stored text,
        then remove that chunk from storage.

        Returns:
            str: The extracted chunk, or an empty string if nothing remains.
        """
        if not self._text:
            return ""

        if len(self._text) <= max_chars:
            chunk = self._text
            self._text = ""
            return chunk

        split_at = self._text.rfind(" ", 0, max_chars)
        if split_at == -1:
            split_at = max_chars

        chunk = self._text[:split_at]
        self._text = self._text[split_at:].lstrip()
        return chunk

    def is_empty(self):
        return len(self._text) == 0

    def remaining_chars(self):
        return len(self._text)

    def clear(self):
        self._text = ""
