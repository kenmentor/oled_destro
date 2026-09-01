"""
Audio Buffer Module

Collects raw PCM 16-bit audio chunks in memory and assembles them
into a valid WAV file.

Provides an alternative to the TTSEngine's disk-based WAV assembly.
Useful when you want to buffer all audio in RAM first, then write
once to disk.

Usage:
    buffer = AudioBuffer(sample_rate=24000)
    buffer.add_chunk(audio_bytes_1)
    buffer.add_chunk(audio_bytes_2)
    buffer.save_to_file("output.wav")
"""

import struct
import wave


class AudioBuffer:
    def __init__(self, sample_rate=24000, channels=1, sample_width=2):
        """
        Initialize the audio buffer.

        Args:
            sample_rate:    Audio sample rate in Hz (default 24000).
            channels:       Number of audio channels (default 1 = mono).
            sample_width:   Bytes per sample (default 2 = 16-bit).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self._chunks = []

    def add_chunk(self, audio_bytes):
        """
        Append raw PCM audio bytes to the buffer.

        Args:
            audio_bytes: Raw PCM 16-bit audio bytes.
        """
        self._chunks.append(audio_bytes)

    def clear(self):
        """Remove all buffered audio data."""
        self._chunks = []

    def total_bytes(self):
        """Return total size of buffered audio in bytes."""
        return sum(len(chunk) for chunk in self._chunks)

    def chunk_count(self):
        """Return the number of buffered chunks."""
        return len(self._chunks)

    def get_all_bytes(self):
        """Return all buffered audio as a single bytes object."""
        return b"".join(self._chunks)

    def save_to_file(self, filepath):
        """
        Write all buffered audio to a valid WAV file.

        Args:
            filepath: Full path where the WAV file will be written.
        """
        all_audio = self.get_all_bytes()

        with wave.open(filepath, "wb") as wav_file:
            wav_file.setparams(
                (self.channels, self.sample_width, self.sample_rate, 0, "NONE", "not compressed")
            )
            wav_file.writeframes(all_audio)

    def save_to_file_append(self, filepath):
        """
        Append buffered audio to an existing WAV file, updating the header.

        This is useful when building a large WAV file incrementally.

        Args:
            filepath: Full path to the WAV file.
        """
        all_audio = self.get_all_bytes()
        if not all_audio:
            return

        with open(filepath, "ab") as f:
            f.write(all_audio)

        file_size = self._get_file_size(filepath)
        with open(filepath, "r+b") as f:
            f.seek(4)
            f.write(struct.pack("<I", file_size - 8))
            f.seek(40)
            f.write(struct.pack("<I", file_size - 44))

        self.clear()

    @staticmethod
    def _get_file_size(filepath):
        import os
        return os.path.getsize(filepath)
