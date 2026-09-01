"""
Document-to-Text Module

Extracts text from PDF files using PyMuPDF (fitz) and pymupdf4llm,
converts to clean markdown, then chunks the text for TTS processing.

Key fixes from original version:
  - In-memory text storage: no more temp file I/O with fsync issues
  - get_all_chunks() returns a list of chunks (easier for sidecar protocol)
  - get_chunk() generator kept for backwards compatibility
  - Removed duplicate `import os` inside the class body
  - Text is stored in RAM, not written to text_file.txt
"""

import io
import re

import fitz

import os


class DocumentToText:
    def __init__(self, chunk_size=1000):
        """
        Initialize the document parser.

        Args:
            chunk_size: Maximum characters per text chunk (default 1000).
        """
        self.file_property = {
            "size": 0,
            "type": "",
            "char_length": 0,
            "page_length": 0,
        }
        self.chunk_size = chunk_size
        self.full_text = ""
        self.outputpath = os.path.join("output")

    
    def get_all_chunks(self):
        """
        Return all text chunks as a list.

        This is the preferred method for sidecar usage, as it gives
        a countable list for progress reporting.

        Returns:
            list[str]: List of text chunks, each up to chunk_size characters.
        """
        with open(self.outputpath, "r") as fs:
            self.full_text = fs.read()
        if not self.full_text:
            return []

        chunks = []
        remaining = self.full_text

        while remaining:
            if len(remaining) <= self.chunk_size:
                chunks.append(remaining)
                break

            # Find a word boundary to avoid splitting mid-word
            split_at = remaining.rfind(" ", 0, self.chunk_size)
            if split_at == -1:
                split_at = self.chunk_size

            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()

        return chunks

    def get_chunk(self):
        """
        Generator version of get_all_chunks (backwards compatible).

        Yields:
            str: Each text chunk, one at a time.
        """
        for chunk in self.get_all_chunks():
            yield chunk

    def filter_text(self, md_text):
        """
        Clean markdown text for TTS consumption.

        Removes citations, links, formatting symbols, and normalizes whitespace.

        Args:
            md_text: Raw markdown text from pymupdf4llm.

        Returns:
            str: Cleaned plain text suitable for TTS.
        """
        # Remove bracketed citations like [10], [11, 12]
        text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", md_text)

        # Remove image links and strip URLs from markdown links
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

        # Remove markdown formatting symbols
        text = re.sub(r"[#*_>]", "", text)

        # Handle en-dashes and em-dashes
        text = text.replace("\u2013", "-").replace("\u2014", " ")

        # Remove symbols that don't make sense in spoken text
        text = re.sub(r"[\\/|~^]", "", text)

        # Normalize whitespace (collapse multiple newlines into one)
        text = re.sub(r"\n{2,}", "\n", text)

        return text.strip()
