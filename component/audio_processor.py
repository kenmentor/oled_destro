import io
import os
import struct
import uuid
from modules.DataBase import DB

database = DB("audios")


class StreamingWavWriter:
    """Write a WAV file incrementally, supporting live playback.

    The header declares a large dataSize so QMediaPlayer/FFmpeg plays
    from the first byte written, reading as data appears on disk.
    On close(), the header is rewritten with the actual sizes so the
    file is valid for archival / later replay.
    """

    _PENDING_SIZE = 0x7FFFFFFF  # ~2 GiB placeholder in the header

    def __init__(self, path, sample_rate=24000, bit_depth=16, channels=1):
        self.path = os.path.abspath(path)
        self._sample_rate = sample_rate
        self._bit_depth = bit_depth
        self._channels = channels
        self._pcm_bytes_written = 0
        self._closed = False

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        header = self._make_header(self._PENDING_SIZE)
        with open(self.path, "wb") as f:
            f.write(header)

    # -- public API ---------------------------------------------------------
    def append(self, pcm_bytes: bytes):
        if self._closed:
            return
        with open(self.path, "ab") as f:
            f.write(pcm_bytes)
        self._pcm_bytes_written += len(pcm_bytes)

    def finalize(self):
        """Rewrite the header with the actual byte counts and close."""
        if self._closed:
            return self.path
        self._closed = True
        with open(self.path, "r+b") as f:
            f.write(self._make_header(self._pcm_bytes_written))
        return self.path

    @property
    def has_data(self):
        return self._pcm_bytes_written > 0

    # -- header helpers -----------------------------------------------------
    def _make_header(self, pcm_data_size: int) -> bytes:
        h = bytearray(44)
        h[0:4] = b"RIFF"
        struct.pack_into("<I", h, 4, 36 + pcm_data_size)
        h[8:12] = b"WAVE"
        h[12:16] = b"fmt "
        struct.pack_into("<I", h, 16, 16)
        struct.pack_into("<H", h, 20, 1)
        struct.pack_into("<H", h, 22, self._channels)
        struct.pack_into("<I", h, 24, self._sample_rate)
        byte_rate = self._sample_rate * self._channels * (self._bit_depth // 8)
        struct.pack_into("<I", h, 28, byte_rate)
        block_align = self._channels * (self._bit_depth // 8)
        struct.pack_into("<H", h, 32, block_align)
        struct.pack_into("<H", h, 34, self._bit_depth)
        h[36:40] = b"data"
        struct.pack_into("<I", h, 40, pcm_data_size)
        return bytes(h)


class PCMAudioBuilder:
    def __init__(self, sample_rate=16000, bit_depth=16, channels=1):
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.channels = channels
        self._buffer = io.BytesIO()

    def append_chunk(self, pcm_bytes: bytes):
        self._buffer.write(pcm_bytes)

    def has_data(self) -> bool:
        return self._buffer.tell() > 0

    def _generate_wav_header(self, pcm_data_size: int) -> bytes:
        header = bytearray(44)
        header[0:4] = b"RIFF"
        struct.pack_into("<I", header, 4, 36 + pcm_data_size)
        header[8:12] = b"WAVE"
        header[12:16] = b"fmt "
        struct.pack_into("<I", header, 16, 16)
        struct.pack_into("<H", header, 20, 1)
        struct.pack_into("<H", header, 22, self.channels)
        struct.pack_into("<I", header, 24, self.sample_rate)
        byte_rate = int(self.sample_rate * self.channels * (self.bit_depth / 8))
        struct.pack_into("<I", header, 28, byte_rate)
        block_align = int(self.channels * (self.bit_depth / 8))
        struct.pack_into("<H", header, 32, block_align)
        struct.pack_into("<H", header, 34, self.bit_depth)
        header[36:40] = b"data"
        struct.pack_into("<I", header, 40, pcm_data_size)
        return bytes(header)

    def save_to_wav(self, output_filename: str = None):
        pcm_bytes = self._buffer.getvalue()
        pcm_size = len(pcm_bytes)
        if pcm_size == 0:
            return None
        if not output_filename:
            output_dir = os.path.join(os.getcwd(), "outputs")
            os.makedirs(output_dir, exist_ok=True)
            output_filename = os.path.join(output_dir, f"synth_{uuid.uuid4().hex[:12]}.wav")
        output_filename = os.path.abspath(output_filename)
        wav_header = self._generate_wav_header(pcm_size)
        with open(output_filename, "wb") as f:
            f.write(wav_header)
            f.write(pcm_bytes)
        database.add(output_filename)
        print(f"Successfully saved {output_filename} ({pcm_size} bytes of PCM data)")
        self._buffer.seek(0)
        self._buffer.truncate(0)
        return output_filename
