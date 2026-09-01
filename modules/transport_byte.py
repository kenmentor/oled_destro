"""
Transport Byte Module

Handles sending audio data from the sidecar to the Tauri frontend
via stdout using a JSON protocol.

In the original version, this used print() and raw bytes with a
0.5-second sleep between chunks. That approach:
  - Polluted stdout with non-JSON output
  - Wasted time with sleep delays
  - Did not provide chunk metadata

The new version sends JSON objects containing base64-encoded audio
chunks, sample rate, and chunk index.

Usage:
    transport = TransportByte()
    transport.send_chunk(audio_bytes, sample_rate=24000, chunk_index=0)

Output format (stdout):
    {"type": "audio_chunk", "chunk_index": 0, "sample_rate": 24000, "encoding": "pcm16_base64", "data": "<base64 string>"}
"""

import base64
import sys
import json


class TransportByte:
    def send_chunk(self, audio_bytes, sample_rate=24000, chunk_index=0):
        """
        Send an audio chunk to stdout as a JSON object.

        Args:
            audio_bytes: Raw PCM 16-bit audio bytes.
            sample_rate:  Audio sample rate in Hz.
            chunk_index:  Sequential index of this chunk.
        """
        encoded = base64.b64encode(audio_bytes).decode("utf-8")

        message = {
            "type": "audio_chunk",
            "chunk_index": chunk_index,
            "sample_rate": sample_rate,
            "encoding": "pcm16_base64",
            "byte_length": len(audio_bytes),
            "data": encoded,
        }

        line = json.dumps(message) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()
